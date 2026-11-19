# Scheduler Lanes and Priority (Design)

**Status**: design, accepted by the owner on 2026-11-18 as the starting point to iterate on (work chunk [W02.14](../plan/work/concurrency-fibers.md), issue [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84)). Built on `feat/lane-policy` the same day; results and what changed while building are in section 15, the open points in 15.5. Implements the direction of the [lane policy exploration](lane-policy-exploration.md) section 3 (agreed 2026-11-13, decision Q02.8) on top of the [worker policy](worker-policy-design.md), the [waitables](scheduler-waitable-design.md) and the [task graph](task-graph-design.md) as built.

Markers: **Decided** = owner decision (exploration or work page Decisions table). **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

The frame is what ships. Today every task that is not a frame stage is queued as `eNormal` and lifted into the critical set within two stage completions by `Schedule::tick()`, where it sits ahead of the next frame stage. A burst of imports or shader compiles therefore delays the frame, and nothing lets a caller say "this may wait".

This chunk gives the scheduler three lanes by deadline, makes a task's lane follow from who spawned it, removes ageing, and adds the three mechanisms that keep the lower lanes honest without ageing: a time floor so nothing starves, cooperative slices so a busy worker returns to the frame within about a millisecond, and a wait boost so work the frame really waits for runs at frame priority.

## 2. State and inputs (checked 2026-11-18 on `origin/feat/wip` `f9ee8b8f`)

- `Schedule` (`Engine.Scheduler/Process/Schedule.{hpp,cpp}`): four `FifoWorkSet`s (one spin lock each), one `_queued` count, the push epoch workers park on. `pop` walks the sets downward from the worker's mask. `tick()` transfers each set one step up; its only caller is the end of `CompositePipeline::complete` (`CompositePipeline.cpp:299`).
- `Worker::handle` pops, wakes one peer if work is left (cascade), runs the task's fiber, and re-pushes the task when the fiber yielded or was unparked in the meantime. Every worker is constructed with `TaskMask::eAll`.
- A task's set is `TaskDelegate::_mask`, written at construction (`make_task(fn, mask = eNormal)`) and overwritten by `CompositeSlot::{static,dynamic}Enqueue` with the stage's lane (`graph::toMask(StageDecl::lane)`).
- `unpark` pushes `fiber->task` from whichever thread signals (`Fiber/Park.cpp`).
- Futures: `FutureState` carries `mask` (default `eNormal`), copied from predecessor to successor in `then()`. A continuation is a fresh task made in `detail::scheduleContinuation` when the predecessor completes, on the completing thread. `await(Future)` parks on `state->done`; the state does not know the task that will fill it.
- Callers: no caller outside the scheduler and its tests passes a mask other than `eNormal` or, in the stage files, `eCritical` (which the slot overwrites anyway). No engine code calls `hg::await` on a future from a stage yet; no stage fans out.
- `hg::yield()` re-queues the calling task at the tail of its set. There is no time budget.
- Wake latency of a parked worker: 5 to 10 µs p50 (worker policy design section 3, 5900X).

## 3. Goals, non-goals, anti-goals

**Goals** (exploration section 2, **Decided**): Frame work gets every free worker; nothing starves; correct from 1 worker to 20; fan-out inside a stage runs at frame priority without the stage saying so; under overload background falls behind, never the frame.

**Non-goals**

- The Jolt `JPH::JobSystem` adapter. Inheritance (section 5) is what makes it correct when the physics chunk writes it; nothing here assumes Jolt.
- Throttling of background producers. The schedule exposes the queued depth per lane (section 9); using it belongs to the producers (storage W03.x).
- Converting existing long tasks to slices. This chunk provides the checkpoint call and the overrun counter and reports which tasks overrun in an editor run; each offender is its owner's follow-up.
- Priority inheritance through `FiberMutex` and `FiberSharedMutex` (section 7.5).
- Fairness inside a lane. Each lane stays one FIFO (decision Q02.2).

**Anti-goals**

- Any path that moves work into Frame by time or by count.
- A per-worker rotation or stride, which lets turns align.
- A second place that decides a lane: the lane is resolved once, where the task or continuation is created.

## 4. Lanes

```cpp
// Engine.Scheduler/Lane.hpp
enum class Lane : u8 { eFrame, eInteractive, eBackground, eInherit };
```

| Lane | Runs | Source |
|---|---|---|
| `eFrame` | Task graph stages, everything they spawn, everything they await | Only the pipeline creates Frame work; the rest arrives by inheritance or boost |
| `eInteractive` | Work a person waits for outside the frame: editor actions, module start and stop, anything spawned from a plain thread without a lane | Default off the workers |
| `eBackground` | Bulk work that may fall behind | Explicit only |

`eInherit` is the default argument of every task and future factory and never reaches a queue.

- **Decided**: three lanes, `eHigher` gone.
- **Proposal 4.1**: `TaskMask` is deleted, not aliased. `graph::Lane` (`eCritical`, `eNormal`, `eBackground`) is replaced by `scheduler::Lane`. The worker's mask and the `mask_` parameter of `pop` go with it; since W02.8 every worker takes every set.
- **Proposal 4.2**: every stage is Frame; `StageDecl::lane` and `graph::toMask` are removed. A stage in a lower lane would gate the end of the frame on the floor (the frame ends when all stages have run), which is never wanted. The two stages declared `eNormal` today (the actor physics callback stubs) become Frame like the other 13.

## 5. Lane resolution

One function decides, at the point a task or a continuation is created:

```cpp
// Engine.Scheduler/Lane.hpp
[[nodiscard]] Lane resolveLane(Lane requested_) noexcept;
```

| Caller | `eInherit` | Explicit lane |
|---|---|---|
| Fiber (a running task) | the task's effective lane (section 7.3) | the lower of the request and the effective lane |
| Plain thread, affine thread, worker root | `eInteractive` | the request; `eFrame` becomes `eInteractive` |

- **Decided**: inherit on spawn, lower only, never higher; `exec` without a lane is Interactive off the workers.
- `Scheduler::exec(task)` resolves and pushes. `hg::execute`, `hg::async`, `make_task` and its siblings default to `eInherit`.
- Futures resolve in `then()` (and `Future<void>::ready(lane)`), on the thread that builds the chain, and store the result in `FutureState::lane`. The continuation task is pushed with that lane as is, through a second entry `Scheduler::execResolved(task)`, because the completing thread (often the IO thread) says nothing about who wants the result. **Proposal 5.1**: today the successor copies the predecessor's mask; it now takes the lower of the predecessor's lane and the lane resolved at `then()`.
- The pipeline (`CompositeSlot::submit`), the worker's re-push and `unpark` call `Schedule::push` directly with the lane the task already has. Slots stamp `eFrame`.

## 6. Worker allocation

### 6.1 The pop order

`Schedule` holds three FIFOs and, per lane, the queued depth; for the two lower lanes also the time a task of that lane last started, one shared count of workers currently inside lower-lane work, and the Frame demand that sizes the reserve (6.4).

```
push(task):
  if lane(task) = Frame: raise framePeak to depth[Frame] + frameRunning   # after the depth was counted
  ...

pop(now):
  for lane in (Interactive, Background):            # floor
    seen = lastStart[lane]
    if depth[lane] > 0 and now - seen >= floor[lane]      # signed; a stale `now` fails it
       and CAS(lastStart[lane], seen, now):
      if take(lane): lowerRunning += 1; return task
  if take(Frame): frameRunning += 1; return task     # rule 1
  if lowerRunning < workers - reserve:               # 6.4, reserve sized by rollFrame()
    for lane in (Interactive, Background):
      if take(lane): raise lastStart[lane] to now; lowerRunning += 1; return task
  return none
```

The worker decrements `lowerRunning` or `frameRunning` when the fiber returns to it (finished, yielded or parked). `now` is read once per pop by the worker (`steady_clock`, about 25 ns) and passed in, so tests drive the floor with their own clock (**Proposal 6.1**). `lastStart` only moves forward (a compare-and-swap to the later value), so a worker holding an older `now` cannot reopen a period.

- **Decided**: Frame first and uncapped; the lower lanes take the workers Frame leaves.
- The wake protocol of the worker policy is unchanged: a push off the workers wakes one, a pop that leaves work behind wakes one. Ageing's epoch bump goes with `tick`. A worker that skips lower work because of the reserve parks like one that found nothing; it is woken by the next push or cascade, or by a roll that lowers the reserve (6.4).

### 6.2 Floor

A lower lane with queued work whose last start is at least its floor ago gets the next popping worker for one task run (one slice, if the task keeps its checkpoints). The compare-and-swap on `lastStart` makes the turn exclusive: at most one floor turn per lane per floor interval, up to the skew between two workers' clock reads. A floor therefore costs Frame at most one worker-slice per lane per period on any worker count, and it ignores the reserve.

- No timer thread: a floor needs a worker to pop. If every worker sits in a Frame task longer than the floor, the lane waits for the first one to return. Workers held back by the reserve would otherwise sleep through a floor that falls due while the others are inside long lower tasks, so a worker whose pop failed while a lower lane has queued work parks only until the earliest such floor is due (millisecond granularity, at least 1 ms) and pops again; with no lower work queued it parks without a timeout as before (found in the Task 4 review, 2026-11-18).
- Starting values (**Proposal 6.3**, swept in section 11): Interactive 8 ms, Background 100 ms. At a 1 ms slice that is at most 13.5 % of one worker for both lanes together, and only while Frame is saturated.
- Serial mode (one worker) runs the same code with a reserve of 0.

### 6.3 Slices

```cpp
// Heliogrim/Async/Yield.hpp
void checkpoint();   // yields when the calling task is in a lower lane and has used its slice
```

- The worker stamps `Fiber::sliceStart = now` when it launches or resumes a fiber. `checkpoint()` returns at once for an effective lane of Frame (section 7.3); otherwise it reads the clock and calls `yield()` once `slice` has passed. The task is re-pushed at the tail of its lane and the worker pops by the order above.
- Starting value (**Proposal 6.4**): slice 1 ms. One clock read per call; long tasks call it per step (per asset, per mip, per chunk), not per element.
- **Overrun**: when a lower-lane fiber returns to the worker after more than twice the slice, the worker adds to `Schedule::overruns(lane)` and keeps the per-lane maximum. The worker notes the lane before it launches the fiber, because a finished task has deleted itself by the time the fiber returns. In debug builds the first overrun per run of each lane is logged with the run time. This is how a missing checkpoint is noticed (exploration section 5).
- Work that cannot yield (a blocking third-party call) belongs on an affine thread. **Decided.**

### 6.4 Frame reserve (**Decided** in direction by the owner 2026-11-18; the mechanism is **Proposal 6.2**)

Exploration rule 2 capped the lower lanes "while Frame work is queued". With one global Frame queue and rule 1 that test almost never fires: on a chain of stages the worker that completes a stage pushes the successor and pops it itself, so the Frame queue is empty nearly all the time although a frame is always in flight. A cap tied to the queue would bite only at the instant of a fan-out, when the other workers are already inside lower work.

Owner, 2026-11-18: workers stuck in the lower lanes are the problem to solve. Lower work that does not cooperate stalls every fan-out of the frame, at every stage that has one, and the loss multiplies (stages × fan-out width × time until a worker comes back). The time until a fan-out is picked up and done is a success metric of the policy (section 11).

So the cap holds before the fan-out arrives. The schedule keeps a **Frame reserve**: the number of workers that Frame may have at once without waiting for anyone, counting the ones already running Frame work. At most `workers - reserve` workers are inside lower-lane work at any time, except for floor turns; the others run Frame work or are parked and wake in 5 to 10 µs.

**Sized by demand.** A fixed number cannot fit a frame that is a strict chain and one that fans out 8 wide, nor 3 workers and 20. The reserve follows what the frame asked for:

- Frame demand = Frame tasks queued + Frame tasks running. `push` of a Frame task raises `framePeak` to the current demand (a compare-and-swap to the larger value). A parent parked on its join does not count; its children do.
- `CompositePipeline::startFrame` calls `Schedule::rollFrame()`: the peak of the frame that ended goes into a ring of the last 8 frames (**Proposal**, constant `reserveWindowFrames`), and `reserve = clamp(max of the ring, 1, workers - 1)`. A stage that fans out only every few frames keeps its reserve; a fan-out that stops releases it after 8 frames.
- When a roll lowers the reserve while lower work is queued, it bumps the push epoch and wakes one worker; the cascade wakes the rest. Without it, workers that parked because of the reserve would sleep on runnable work.
- The upper clamp leaves one worker to the lower lanes whenever the Frame queue is empty, so a small machine keeps the editor's own actions moving at more than floor rate. On one worker the reserve is 0.
- Before the first frame and without a pipeline (tests, tools) the reserve is 1.

| Frame shape | 20 workers: reserve, lower-lane workers | 3 workers: reserve, lower-lane workers |
|---|---|---|
| Strict chain | 1, up to 19 | 1, up to 2 |
| Fan-out 4 wide | 4, up to 16 | 2, up to 1 |
| Fan-out 8 wide | 8, up to 12 | 2, up to 1 |
| Fan-out 32 wide | 19, up to 1 | 2, up to 1 |

What it costs: reserved workers idle during the narrow parts of the frame. That is "background falls behind, never the frame" (**Decided**, exploration 3.5). What it bounds: a fan-out no wider than the reserve is picked up at wake latency whether or not the lower lanes cooperate; a wider one waits for the excess only.

- **Wait trigger** (added after the prior-art pass, [exploration](lane-policy-exploration.md) 6.2): the peak count predicts, it does not observe. `push` stamps a Frame task with the time; a worker that pops a Frame task which waited longer than `frameWaitLimit` (default 250 µs, owner 2026-11-19; start value was 100 µs) while `lowerRunning > 0` raises the reserve by one at once and records that value as the frame's peak, so the ring holds it for the window. The reserve thus goes up immediately on a peak or on an observed wait and comes down only when 8 frames in a row needed less. `Schedule::frameWaitMax()` exposes the longest Frame wait since the last roll.
- **Wake at a Frame push** (same pass, 6.3): `LanePolicyConfig::wakeOnFramePush` makes a Frame push from a worker wake one parked worker, so k children wake up to k helpers directly instead of through the cascade. An extra wake cannot lose work in the park protocol (a spurious return is already part of the model), so `Schedule.tla` needs no new case. Off to start; the default is whichever gives the lower fan-out pickup p99 in the sweep.
- Config key `eLaneReserve`: 0 selects the demand-sized reserve (default); a value above 0 fixes it (clamped to `workers - 1`), for comparison and for a machine where the owner wants to pin it.
- Wake-up of the reserved workers at a fan-out is the existing cascade: the pushing worker wakes one peer when it pops, each woken worker wakes the next. For 8 children that is a chain of up to 7 wakes. The benchmark reports pickup latency separately so this shows; the wake protocol is not changed here. If the chain turns out to be the limit, waking on a worker push is a worker policy change with its own model update.

## 7. Wait boost

### 7.1 What a waitable knows

`Signal` and `JoinCounter` stay as they are: they have no producer. Join waits need none, since children inherit the waiter's lane. The producer is named one level up, where a producing task exists: a future whose value comes from a continuation. The link between the two is a small scheduler object:

```cpp
// Engine.Scheduler/Process/BoostCell.hpp, Arci-counted
struct BoostCell {
    std::atomic<Lane> lane;                               // waiter urgency; starts at eBackground, only ever raised
    std::atomic<ptr<const task::TaskDelegate>> task;      // the producing task while it exists; compared, never dereferenced
    SpinLock linkLock;
    Arci<BoostCell> dependsOn;                            // what this producer is waiting for now; guarded by linkLock
};
```

- `then()` creates the cell of the successor state: `next->producer = cell`, `cell->dependsOn = prev->producer`. The cell's `lane` records only what waiters asked for and starts at Background, the lowest lane, meaning "no waiter yet"; the continuation's own lane stays on the task, and it is queued in the higher of the two. (The first build seeded the cell with the continuation's lane; a chain built in Frame then started at Frame, a Frame waiter's raise changed nothing, and the walk stopped before it reached what the chain depended on. Found in the Task 8 review, 2026-11-18.)
- `detail::scheduleContinuation(prev)` makes the continuation task, stores it in `cell->task`, clears `dependsOn`, and hands both to `Schedule::pushBoostable(task, cell)`. When the task starts it binds the cell to its fiber (`fiber::self::bindBoost(cell)`); when it ends it clears `cell->task` and the binding before the task deletes itself.
- A continuation that returns a future sets `cell->dependsOn` to that future's cell (null for a promise-filled one) and boosts it only if its own lane was raised above the lane it was created with: without a waiter nothing moves (a Frame chain that returns `async(work, eBackground)` leaves `work` in Background until someone awaits the chain). The forwarding step that copies the inner result into the outer state (`Future.hpp:172-178`) runs inline on the completing thread instead of as a task of its own: it is engine code that moves one slot and completes the outer state, and as a task it would sit in a lower lane with nothing to boost it. User continuations still never run inline.
- `await` inside a producer sets the producer's `dependsOn` to the awaited future's cell for the duration of the wait.
- Inline forwarding is iterative: a forwarder reached while its thread is already forwarding is queued on a thread-local list and run by the outermost one, so a chain of futures returning futures (a retry loop written as `ready().then([]{ return loop(n - 1); })`) does not grow the stack. The forwarder never suspends, which is what makes the thread-local safe here. It clears the outer cell's `dependsOn` before completing the outer state, so finished cells do not chain. When the consumer has dropped the outer future, the forwarder is its last owner and the value's destructor runs on the completing thread (found in the Task 8 review, 2026-11-18).
- Futures filled by a `Promise` (IO completions, hand-made promises) have no cell; a boost stops there. An IO request's urgency is its IO queue priority (storage design 2). Their `FutureState::lane` is `eFrame`, the neutral value of "the lower of" in 5.1, and is never used to queue anything: a continuation's lane is its cell's.

### 7.2 Boost

`await(Future)` calls `boost(state->producer, resolveLane(eInherit))` before it parks.

```
boost(cell, lane):
  for hop in 1..boostMaxHops (16):
    if not cell: return
    if not raise(cell.lane, lane): return      # compare-and-swap to the higher lane; already there: someone else walked on
    if t = cell.task: schedule.promote(t, lane)
    cell = copy of cell.dependsOn under linkLock
```

- The walk ends at the first cell that is already at the lane or above: whoever raised it walked the rest. That bounds repeated awaits of the same future to one compare, and makes a cycle of waits terminate. The hop cap is a second guard, as in the kernel walks ([exploration](lane-policy-exploration.md) 6.1); reaching it is asserted in debug builds.
- Whoever links a dependency escalates it: after storing `dependsOn` (in `await` and in the future-returning branch) the linker reads its own cell's lane and calls `boost(dependency, thatLane)`. A boost that passed before the link was stored is thereby carried on.
- A boost is never withdrawn, also when the waiter is gone. Swift behaves the same.

```cpp
// Schedule
void pushBoostable(task, ptr<BoostCell> cell);   // push in the higher of task lane and cell lane, then re-read the cell lane and promote if it rose
bool promote(task, Lane to);                     // under the lower lanes' locks: if `task` is queued below `to`, move it to the tail of `to`
```

- **Decided** (exploration 3.3): the queued producer moves to the waiter's lane. `promote` searches the Interactive and Background FIFOs for the pointer and moves the entry; the work sets change from `std::queue` to a container that can erase from the middle (**Builder's call**). The search is linear in the lane's depth, under its spin lock, once per boost.
- The pointer in `cell.task` is only compared against queue entries, which are alive by definition. If the producer finished and a new task was allocated at the same address between the load and the search, one unrelated lower-lane task runs once in the waiter's lane. That is accepted: it is bounded by one task per such race and breaks nothing.
- **A producer that already ran** is covered by the same call. If it yielded at a checkpoint or was unparked, it sits in a lower FIFO and `promote` moves it. If it is on a worker, the search finds nothing, and its next re-push sees the raised lane (7.3). If it is parked in an `await` of its own, the walk follows `dependsOn` to what it waits for.
- **Chains**: the walk raises every cell it passes. A predecessor that is not complete has no task yet; its cell's `dependsOn` leads upstream, and when it completes, `scheduleContinuation` pushes the successor in the raised lane.
- **Ordering**: three store-then-load pairs face the waiter's raise-then-read and need sequentially consistent ordering, so that at least one side sees the other: the push followed by the re-read of the lane in `pushBoostable` against raise followed by search; the store of `cell.task` or `dependsOn` followed by a read of the own lane against raise followed by the read of the link. Both sides seeing each other gives a second `promote` that finds nothing.
- The worker of a waiter that parks pops next and takes the promoted task or an older peer of that lane.

### 7.3 Effective lane

A task's lane is read through its fiber: effective lane = the higher of `task->lane()` and the lane of the cell bound to the fiber (`Fiber::boost`, a `ptr<BoostCell>`, null by default, cleared when the task ends).

- The worker's re-push and `unpark` push through `pushBoostable(task, fiber->boost)`. After the park handshake exactly one side pushes, so the write of `task->lane()` to the effective lane there has a single owner.
- Ownership: `Fiber::boost` is not counted. The bound task keeps its cell alive while it runs or is parked, but once the task is pushed another worker may run it to its end and release the cell. `pushBoostable` therefore takes a counted reference before the push and uses only that afterwards (found in the Task 7 review, 2026-11-18).
- A running producer whose cell was raised yields at its next `checkpoint()` even inside its slice, so it re-queues in the raised lane at once; it goes to the tail of that lane.
- `resolveLane` and `checkpoint` read the effective lane, so a boosted producer's children and its own awaits carry the boost on, and it stops slicing once it is Frame.

### 7.4 Cost

One `BoostCell` allocation per continuation, one linear search per boost. **Builder's call**: embedding the cell in `FutureState` through a non-template base if the allocation shows in the future benchmarks.

### 7.5 Limit: locks

A Frame task that waits for a `FiberMutex` held by a Background task is not boosted; the holder progresses at the Background floor. No engine code holds a fiber mutex across a checkpoint today, and the rule "no checkpoint while holding a lock" keeps it that way; the debug build asserts it if the lock types can count holds per fiber cheaply (**Builder's call**). `promote` would serve a lock-holder boost too; that is its own chunk if the rule proves too tight.

## 8. Removal and migration

- Deleted: `Schedule::tick`, `Schedule::transfer`, `ScheduleWorkSet::transfer`, `FifoWorkSet::transfer`, the call in `CompositePipeline::complete`, `TaskMask.hpp`, `graph::toMask`, `StageDecl::lane`, `Worker::mask`.
- Renamed mechanically: `mask` accessors and parameters become `lane`; the stage files drop their `TaskMask::eCritical` argument (the slot stamps it); `EditorEngine.cpp`, `GameEngine.cpp` and `Heliogrim/Async` drop `eNormal` and inherit.
- Tests that pin ageing (`Engine.Scheduler.Test/Schedule.cpp`, two cases in `CompositePipeline.cpp`) are replaced by lane tests (section 10).

## 9. Observability and config

- `Schedule::queued(Lane)`, `Schedule::overruns(Lane)`, `Schedule::maxRun(Lane)`, `Schedule::frameWaitMax()`, `Schedule::reserve()`; `Scheduler::queued(Lane)` on the module interface for producers. **Decided**: depth per lane is exposed; throttling is the producer's.
- `SchedulerConfigProperty` gains `eLaneSlice`, `eInteractiveFloor`, `eBackgroundFloor`, `eFrameWaitLimit` (microseconds), `eLaneReserve` (workers; 0 = sized by demand) and `eWakeOnFramePush` (bool), read where the worker count is read. Defaults live beside `default_worker_reserve`.

## 10. Verification

**Tests** (`Engine.Scheduler.Test`, `Engine.Async.Test`):

| Test | Shows |
|---|---|
| Pop order | Frame before Interactive before Background; FIFO inside a lane |
| Floor | With Frame never empty and a test clock, a Background task starts once per floor period; several poppers with the same `now` get one turn; a popper with an older `now` gets none |
| Reserve, cap | With a reserve of 2 on 3 workers and Frame empty, one worker takes lower work and the next pop does not; the floor still admits a lower task when the reserve blocks it |
| Reserve, sizing | A frame whose stage pushes 8 Frame children gives a reserve of 8 on 20 workers and 2 on 3 after the roll; a strict chain gives 1; a fan-out that stops is forgotten after 8 rolls; one worker gives 0 |
| Reserve, shrink | Workers parked by the reserve with lower work queued run it after the roll that lowers the reserve |
| Fan-out under a stuck flood | With every worker outside the reserve inside a lower task that never yields, a fan-out no wider than the reserve has all its children started without waiting for any of them |
| Resolution | Child of a Frame task is Frame; an explicit lower lane holds; an explicit higher lane is clamped; a plain thread gets Interactive; a continuation completed by a plain thread keeps the lane resolved at `then()` |
| Checkpoint | Yields after the slice in a lower lane, never in Frame; an overrun is counted |
| Boost, queued | A Frame fiber awaits a Background future queued behind 1,000 Background tasks and returns before they drain |
| Boost, yielded | A Background producer that has yielded at a checkpoint and sits behind the flood is awaited from Frame and finishes before the flood |
| Boost, running | A running Background producer whose future is awaited from Frame re-queues in Frame at its next checkpoint |
| Boost, chain | `a.then(b).then(c)` awaited from Frame with `a` not yet complete: `b` and `c` are scheduled in Frame |
| Boost, nested wait | A Background producer parked on its own Background future is awaited from Frame: the inner producer is promoted |
| Boost, flattened | `async([]{ return promiseFuture; })` in Background awaited from Frame: after the promise is filled from a plain thread the waiter returns without a lower-lane hop |
| Reserve, wait trigger | A Frame task that waited longer than `frameWaitLimit` while lower work was running raises the reserve by one at its pop; without lower work running it does not |
| Boost, walk end | A second boost of an already raised cell does no `promote`; a cycle of two cells terminates; a boost that arrives before a dependency is linked reaches the dependency through the linker |
| No ageing | A queued Background task stays Background across frames |

**Models** (`verifying-concurrency` skill):

- `Schedule.tla` loses `transfer`, `lock1` and mutation (d); gains a Frame and a lower set, the per-lane depth, the lower-running count, the reserve as a variable that a roll process moves between 0 and 1 (bump and wake when it drops), and the floor as a due flag set by a clock process and claimed by compare-and-swap. New invariants `FrameFirst` (a worker takes lower work only after seeing Frame empty or holding the floor claim) and `OneFloorTurn` (one claim per raising of the due flag); new liveness `LowerProgress` (with a Frame task that re-pushes itself forever, the lower task still runs). Mutations: no floor (fails `LowerProgress`), floor without the compare-and-swap (fails `OneFloorTurn`), lower set popped first (fails `FrameFirst`), a lower-slot claim without compare-and-swap (fails `ReserveHeld`). Dropping the wake when the reserve drops fails no liveness property at a reserve the code can reach: the reserve is clamped to `workers - 1`, so one worker may always take lower work, and it pops again when its task returns. That wake therefore buys latency (a parked worker is told at once that it may now take lower work), not progress; the model says so and does not claim it necessary (Task 6 review, 2026-11-18). New invariant `ReserveHeld` (never more than `N - reserve` workers in lower work beyond floor turns, judged against the reserve each worker read). The existing four properties and mutations (a) to (c) stay.
- `BoostCell.tla` beside the header: one producer task (queued, running, yielding, finishing), one cell, one waiter. Property: once `boost` has returned and the producer has not finished, the producer is never queued below the waiter's lane at a quiescent point. Mutations: the re-read after the push dropped from `pushBoostable` (fails), the raise moved after the search (fails).

## 11. Measurement

Hardware and build as in the worker policy design (5900X, clang-cl). A benchmark in `Performance.Test` drives the real `CompositePipeline`:

- Frame: 15 chained stages of 200 µs spin, 8 of them fanning out 8 children of 200 µs joined by a `JoinCounter`.
- **Fan-out latency** (owner, 2026-11-18: a success metric of the policy): per fan-out, the time from the push of the first child until the last child has started (pickup) and until the join returns (completion).
- Flood, cooperating: a thread keeps four tasks per worker queued, each 5 ms of spin with a checkpoint every 100 µs. Before the change these are `eNormal` `exec`s, as all such work is today.
- Flood, not cooperating: the same tasks without a checkpoint. This is the worst case the owner named: every worker outside the reserve is stuck for a whole task, at every fan-out of the frame.
- Probe: every 50 ms one Interactive task of 2 ms; latency from push to completion.
- Reported for 3 workers and the auto count (20), idle and under each flood: frame time p50, p99 and maximum over 2,000 frames; fan-out pickup and completion latency p50 and p99; Frame queue wait (push to start) p99 and maximum; Background tasks completed per second; probe latency p50 and p99; overruns.

Order: the benchmark is the first task and records the baseline before any other change; the last task reruns it and sweeps slice {0.5, 1, 2} ms, Interactive floor {4, 8, 16} ms, Background floor {50, 100, 250} ms the reserve as demand-sized against fixed {1, 2, 4, 8}, the Frame wait limit {50, 100, 250} µs and the wake at a Frame push on and off. One more run awaits a Background future from a Frame stage behind 100,000 queued Background tasks and reports the time `promote` holds the lane lock. A fixed 1 is the policy without a reserve (the chain's own worker is the one), so it is the comparison that shows what the reserve buys and what it costs the backlog. The defaults are whatever the sweep supports; the numbers above are where it starts.

**Bound for "done when"** (**Proposal 11.1**): on the benchmark frame, flooded frame time p99 is at most the idle p99 plus two slices plus the largest overrun seen, on both worker counts, at the chosen defaults; Background starts at least one task per Background floor under flood. Fan-out completion p99 under either flood, cooperating or not, is at most 1.5 times the idle p99 on both worker counts (the factor is this document's proposal; the metric is the owner's). In general the frame pays at most one slice plus overrun per point where it needs a worker beyond the reserve, and one worker-slice per floor turn. The owner's editor run afterwards lists the tasks that overrun.

## 12. Left to the builder

The file split inside `Engine.Scheduler/Process`; whether `ScheduleWorkSet` keeps its virtual base with one implementation; the work set container; how `lastStart` is packed; the name of `execResolved`; the test clock's shape; the layout of the benchmark; whether the debug hold-count assert of 7.5 is cheap enough.

## 13. Decisions made in this document (for review)

| # | Call | Kind |
|---|---|---|
| 4.1 | `TaskMask` deleted, one `scheduler::Lane` with `eInherit`; worker mask gone | Proposal |
| 4.2 | Every stage is Frame; `StageDecl::lane` removed | Proposal |
| 5.1 | Futures resolve their lane in `then()`, lower of predecessor and caller; continuations pushed without re-resolving | Proposal |
| 6.1 | `pop` takes the time as a parameter | Proposal |
| 6.2 | The cap holds while frames run, not only while the Frame queue is non-empty: a Frame reserve bounds the workers in lower-lane work | **Decided** in direction (owner, 2026-11-18) |
| 6.2 | The reserve is sized by the peak Frame demand of the last 8 frames, clamped to 1 and `workers - 1`; `eLaneReserve` above 0 fixes it; a roll that lowers it wakes a worker | Proposal |
| 6.4 | The cascade stays the only wake at a fan-out pushed from a worker; pickup latency is measured to show whether that holds | Proposal |
| 6.3, 6.4 | Start values: slice 1 ms, floors 8 ms and 100 ms; final values from the sweep | Proposal |
| 7.1, 7.2 | Boost through a `BoostCell` on future continuations; the queued producer is moved by `promote` | Proposal |
| 7.1 | The forwarding step of a continuation that returns a future runs inline on the completing thread | Proposal, changes "never inline" for this engine-internal step only |
| 7.2 | A stale task pointer may promote one unrelated task once | Proposal |
| 7.3 | Effective lane through the fiber, so a running producer is boosted at its next re-push | Proposal, extends the exploration |
| 7.5 | No boost through fiber mutexes; rule and optional assert instead | Proposal |
| 6.4 | Reserve also rises by one on an observed Frame wait above 100 µs; direct wake at a Frame push is a switch decided by measurement | Proposal, from the prior-art pass |
| 7.2 | Boost walk ends at an already raised cell, 16 hops at most; the linker escalates a new dependency; boosts are never withdrawn | Proposal, from the prior-art pass |
| 11.1 | Frame bound on the benchmark: idle p99 plus two slices plus the largest overrun | Proposal |

Builder check (2026-11-18, against the engine source): found that a continuation returning a future and a producer that had already yielded were not boosted by the first draft's claim scheme, and that the floor's compare could reopen a period with a stale clock read; section 7 was rewritten around `promote` and 6.1 corrected. Its remaining question, what the caps were meant to bound, was answered by the owner the same day (6.4). The demand-sized reserve was written after the check and has not been checked by a second reader.

## 14. Prior-art pass (2026-11-18)

Run before execution at the owner's request; the record with sources and their verification state is the [exploration](lane-policy-exploration.md) section 6. No severe finding: lanes, floor, slices, reserve and boost each have a counterpart in a runtime whose source was read. Changes it caused here:

| Change | Where | Evidence |
|---|---|---|
| The boost walk ends when a hop raises nothing, and has a hop cap | 7.2 | Swift `escalateStatus`, XNU turnstiles, Linux rt-mutex |
| A dependency is escalated when it is linked | 7.2 | Swift escalates at record publish |
| Boosts are never withdrawn, stated as a decision | 7.2 | Swift |
| The reserve also rises on an observed Frame wait; Frame queue wait is reported | 6.4, 9, 11 | Go `sysmon`, .NET gate thread (delay signals, raise in steps, damped fall) |
| Direct wake at a Frame push as a measured switch | 6.4, 11 | Rayon wakes `min(k, sleepers)`; Tokio and Go chain through spinners |
| The scan of `promote` is measured against a deep Background queue | 11 | Swift and libdispatch avoid the search with a duplicate entry |

Considered and not taken:

- **Duplicate entry instead of `promote`** (Swift's stealer). Needs a task that outlives its queue entries; the engine's tasks delete themselves when they finish. Revisit if the scan shows in the measurement, together with task reference counting.
- **A flag set by a timer instead of a clock read in `checkpoint()`** (Seastar, Go). The read is about 25 ns once per work step; a flag needs a timer thread. Revisit if `checkpoint` shows in a profile.
- **A stall report while a task is stuck** (Seastar). The overrun counter reports only after the task returns. A watcher needs its own thread; left as a follow-up chunk.
- **Adding workers when lower work blocks** (Go, .NET, Unreal oversubscription). Tokio rejected it for stutter; the reserve bounds the damage without it.

## 15. Results (2026-11-18, as built on `feat/lane-policy`)

Measured with `LaneFloodBenchmark` in `Performance.Test` (section 11), Debug build, Ryzen 9 5900X, clang-cl. Debug numbers compare before and after on this machine; they are not absolute. Starting values are the defaults; no default was changed by the sweep.

### 15.1 Frame and fan-out under a background flood

Median of three runs. "Before" is the scheduler with task masks and ageing (the baseline of the first task, flooded runs capped at 60 s, about 125 frames).

| | 3 workers: frame p50 | 3 workers: fan-out completion p99 | 20 workers: frame p50 | 20 workers: fan-out completion p99 |
|---|---|---|---|---|
| Idle | 7.99 ms | 818 µs | 5.15 ms | 340 µs |
| Cooperating flood | 9.43 ms | 1,019 µs | 5.44 ms | 349 µs |
| Non-cooperating flood | 9.44 ms | 1,413 µs | 5.43 ms | 354 µs |
| Before, flooded | 475 ms | 36.5 ms | 452 ms | 31.6 ms |

Bounds of 11.1:

| Bound | 3 workers | 20 workers |
|---|---|---|
| Frame p99 under flood within idle p99 + two slices + largest overrun | holds | holds |
| Background starts work every Background floor | holds (185 tasks/s under the cooperating flood) | holds (1,054 to 1,846 tasks/s) |
| Fan-out completion p99 within 1.5 times idle | holds for the cooperating flood (1,019 against 1,228 µs); **fails for the non-cooperating flood** (1,413 µs, 15 % over) at every swept value | holds against the idle measured on this branch (limit 510 µs); against the baseline's idle (288 µs, limit 432 µs) one non-cooperating run of three fails at 463 µs. Idle itself varies from 324 to 454 µs between runs |

The miss on 3 workers follows from the upper clamp of the reserve (`workers - 1`, section 6.4): the third worker is allowed into lower work, and a task that never yields holds it for its 5 ms. Fixed reserves of 2, 4 and 8 give the same rows there. A clamp at all workers, which would leave lower work only its floor turns on a small machine, was not measured.

### 15.2 What the reserve buys and costs

- Without it (fixed 1, the chain's own worker): 20 workers under the cooperating flood go from a 5.4 ms to a 9.4 ms frame and from 349 to 911 µs fan-out completion; 3 workers under the non-cooperating flood go to a 15.3 ms frame and 3,415 µs.
- It costs Background throughput against fixed 1: 41 % on 3 workers, 49 to 71 % across runs on 20.
- **The wait trigger over-reserves on a wide machine.** At the starting wait limit of 100 µs the reserve reaches 19 of 20 workers under flood, more than twice the fan-out width of 8. Alternatives, three runs each in one session, against the starting values on 20 workers:

| Alternative | Background throughput | Fan-out pickup p99, non-cooperating | Frame p99, non-cooperating | Reserve maximum |
|---|---|---|---|---|
| Starting values | 1,802 tasks/s | 117 µs | 5.75 ms | 19 |
| Wait limit 250 µs | +19 to 21 % | 121 µs | within the starting values' range | 13 to 19 |
| Wait trigger off (limit 100 ms) | +20 to 22 % | 236 µs | 6.42 ms, outside the range; completion p99 453 µs | 10 |
| Fixed reserve 8 | +32 to 33 % | 214 µs | 6.04 ms, overlapping the range; completion p99 424 µs | 8 |

On 3 workers the four are the same to within about 1.5 %, since the reserve is clamped to 2. A wait limit of 250 µs is the candidate for the default: about a fifth more Background throughput at no measured cost to the frame. It is left to the owner; a single sweep was not taken as enough to change a default.

- Wake at a Frame push (6.4) does not lower fan-out pickup beyond the run-to-run spread, so it stays off. It does lower the per-frame maximum Frame wait at p99, from about 160 to 220 µs down to 29 to 49 µs (one run per point).

### 15.3 Cost of the boost's queue search

A Frame task awaits a Background `async` queued behind other Background tasks. Overhead is the await latency minus the producer's own 100 µs run, so it includes the search, the promote, the pickup and the waiter's park and resume. Three runs each.

| Background tasks queued ahead | 3 workers | 20 workers |
|---|---|---|
| 1,000 | 39, 49, 76 µs | 68, 70, 81 µs |
| 100,000 | 1.8, 2.6, 3.0 ms | 1.9, 18.2, 27.6 ms |

The cost grows with the queue depth. The code makes the cause likely: `promote` finds the entry with a linear search of the lane's queue under its lock, and a just-queued producer sits at the tail. The benchmark does not isolate it (two depths, Debug build), and contention with workers popping from the same queue on 20 workers is a guess. For a shallow backlog the boost is cheap; for a deep one it costs the waiting frame milliseconds. The alternative from the prior-art pass (section 14, a duplicate entry instead of a search) becomes worth its price if deep Background queues are expected, which is what the storage work's throttling is meant to prevent.

### 15.4 What changed against this document while building

| Change | Where | Why |
|---|---|---|
| Bounded park: a worker whose pop failed while lower work is queued parks only until the earliest floor is due | 6.2 | Reserved workers slept through a floor while the others ran long lower tasks |
| `pop` hands back the lane it counted | 6.1 | `promote` changes a queued task's lane; the running counters must use the lane that was counted |
| The roll's wake when the reserve drops is a latency measure, not needed for progress | 10 | The reserve clamp always leaves one worker for lower work; the model shows no liveness loss without the wake |
| `pushBoostable` holds a counted reference to the cell across the push | 7.3 | The pushed task can finish on another worker and release the cell (use after free in the first build) |
| A running producer whose cell was raised yields at its next checkpoint | 7.3 | It re-queues in the raised lane at once |
| Inline forwarding is iterative; the forwarder clears the outer cell's link | 7.1 | Futures returning futures recursed once per level (stack overflow at 100,000 levels in the first build) |
| A cell's lane records waiter urgency only and starts at Background | 7.1 | Seeded with the continuation's lane, a Frame chain made a Frame waiter's raise a no-op and the walk stopped at once |
| `await` from a plain thread does not boost | 7.2 | No fiber and no schedule at hand there |
| `promote` takes the cell as well | 7.2 | Two boosts to different lanes while the task is briefly in no queue |

Models (sequential consistency only): `Schedule.tla` passes at 2 workers in the drain and run-forever configurations (2.3 million and 0.8 million distinct states); seven mutations fail the property they should, and dropping the roll's wake fails nothing at a reachable reserve. Liveness under a racing stop, liveness with a rising reserve, and 3 workers did not finish. `BoostCell.tla` and the updated `FutureState.tla` pass with their mutations failing; neither models object lifetime.

### 15.5 Open

- The fan-out bound on small machines under lower work that does not yield (15.1): raise the clamp, or accept and rely on `checkpoint()` in every long task.
- The wait limit default (15.2).
- The boost's search cost behind deep queues (15.3).
- Nothing in the engine calls `checkpoint()` yet: until the long tasks do, every lower-lane task is a non-cooperating one, and the reserve is the only protection.
- A boost walk stops after 1,024 hops (raised from 16 in the fix wave, 15.6).
- Wake-up at a fan-out is a chain of one wake per pop, so N helpers arrive after N hops; waking two per pop (a tree) or `min(k, parked)` at a push of k is to be explored (owner note 2026-11-18, chunk W02.15). The same chunk covers lower-lane work pushed from a running task, which wakes nobody until that task returns.
- All owner decisions and every ruling of the run are listed for review in the [owner review](lane-policy-review.md).
- The bounded park uses a millisecond timeout; on a system that rounds waits to its 15.6 ms tick the 8 ms Interactive floor can overshoot.
- The owner's editor run (frame time idle and during an import, logged overruns) has not happened.

### 15.6 Whole-branch review and its fix wave

One reviewer read the branch as a whole after the nine tasks; one fix wave followed, then a scoped re-review. Folded into the commits that own the code:

| Fix | Why |
|---|---|
| The inline forwarding asserts in debug builds that it ends on the thread it started on | A value type whose move or destructor suspends would move the fiber to another worker and leave the first thread's marker set, losing later completions. Rule: a future's value type must not suspend in its move constructor or destructor |
| A reserve older than 250 ms (`reserveStaleMillis`) counts as its minimum; a stopped pipeline resets it | The reserve is only resized at a frame start, so a stalled or stopped pipeline kept the lower lanes capped |
| Slice, floors and wait limit are clamped to at least 1 where the schedule is set up | A floor of 0 turned every pop into a floor turn; a slice of 0 yielded at every checkpoint |
| `boostMaxHops` is 1,024 and reaching it no longer asserts | An awaited chain of nested futures longer than 16 is a legitimate program; cycles already end at the first unchanged raise |
| A destroyed cell poisons its lane in debug builds and the re-queue asserts on it | Makes a use of a released cell likely to fail loudly |

Checked and found not to hold: the concern that Interactive and Background work would run only at floor rate because Frame is popped first. Under flood with the frame running, Background completes 185 tasks per second on 3 workers and over 1,000 on 20, against a floor rate of 10; on a chain of stages the Frame queue is empty nearly always.

Left open by that review, in addition to 15.5: after 250 ms without a frame start the stale rule also discards a raise made by the wait trigger, so a single frame longer than that falls back to the minimum reserve while its demand peaks (refreshing the staleness clock on a wait-trigger raise would close it); a boosted task counts as Frame demand and can lift the reserve for the window; the two engines read the lane configuration with the same duplicated block, since the scheduler bundle does not link the config bundle.

### 15.7 Owner decisions (2026-11-19)

From the [owner review](lane-policy-review.md) Q02.11 to Q02.22; applied on `feat/lane-policy` unless marked open.

- **Reserve clamp** (Q02.11): stays at `workers - 1`; the lifted clamp is measured once long tasks call `checkpoint()`.
- **Wait limit** (Q02.12): default 250 µs for now.
- **Stale reserve** (Q02.18): a wait-trigger raise refreshes the staleness clock, so a single frame longer than `reserveStaleMillis` keeps its reserve. A frame time of 250 ms is a stalled process, not a frame to tune for.
- **Boost into Frame** (Q02.21): intended. A boosted task in the Frame lane is Frame work a stage waits for, so it counts as Frame demand and can lift the reserve for the window.
- **Timer resolution** (Q02.19): documented, no `timeBeginPeriod`. The bounded park waits in milliseconds; where the system rounds waits to its 15.6 ms tick, the 8 ms Interactive floor overshoots. Revisit when a machine shows it (a 5 ms floor was served after 5.2 to 5.8 ms on the owner's machine).
- **Value types of futures** (Q02.20): a value type must not suspend in its move constructor or destructor; constructors and destructors do not take part in concurrent execution. Stated on the futures system page.
- **Model** (Q02.22): `Schedule.tla` stays at its completed scope (safety everywhere, 2 workers with eight mutations); revisit with the wake rule change.
- **Wake rule** (Q02.14 with Q02.17, open, chunk W02.15): when the number k of tasks made runnable is known, wake `min(k, parked)`; when it is not, wake two while tasks are still queued. Batches and fan-outs ramp up by count, task streams ramp up faster than the chain of one wake per pop. Needs the model re-run.
- **checkpoint() adoption** (Q02.15, open): where to integrate first is checked separately; it does not block this chunk.
- **Boost search** (Q02.16, open, chunk W02.16): profile first. Lock contention on the lane lock grows with the worker count, so a lock-free FIFO work set is a candidate, but only with measurements: lock-free or wait-free is not faster than a light lock by itself.
- **Wait trigger cap** (Q02.13, open).
