# Lanes and Priority

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`fd5affa5`](https://github.com/Heliogrim/Heliogrim-Engine/tree/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab), the head of `feat/wip`, 2026-11-19. Built in PR [#208](https://github.com/Heliogrim/Heliogrim-Engine/pull/208). Not on `master` yet.
**Modules**: `Engine.Scheduler` ([`Lane`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Lane.cpp), [`LanePolicyConfig`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/LanePolicyConfig.hpp), [`Process/Schedule`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Process/Schedule.cpp), [`Process/BoostCell`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Process/BoostCell.cpp), [`Process/WorkSet/FifoWorkSet`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Process/WorkSet/FifoWorkSet.cpp), [`Worker/Worker`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Worker/Worker.cpp), [`Fiber/Fiber`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Fiber/Fiber.cpp)), `Engine.Async` ([`Future/Future`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Async/Future/Future.hpp), [`Future/Schedule`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Async/Future/Schedule.hpp)), `Heliogrim/Async` (`Yield.hpp`)
**Related**: [lane policy design](../../architecture/lane-policy-design.md) (sections 4 to 7; results in 15, owner decisions in 15.7), [owner review](../../architecture/lane-policy-review.md), [lane policy exploration](../../architecture/lane-policy-exploration.md), [worker policy design](../../architecture/worker-policy-design.md), work chunks W02.14 (done), W02.15 and W02.16 in [concurrency and fibers](../../plan/work/concurrency-fibers.md). Scheduler pages: [overview](index.md), [fibers and workers](fibers-and-workers.md), [futures](futures.md), [task graph](task-graph.md).

Which task a worker takes next, and how waiting on a lower-priority task pulls it up. Part of the [fiber scheduler](index.md); the worker loop itself is on [fibers and workers](fibers-and-workers.md).

## Purpose

The frame must not wait for background work, and background work must still make progress. Every task has a lane; the schedule keeps one FIFO per lane and pops by a fixed order with three additions: a **floor** per lower lane so it is never starved, a **Frame reserve** that keeps enough workers off the lower lanes for the frame's fan-outs, and a **wait boost** that raises a lower task when a higher one awaits its future. A long lower-lane task gives its worker back at **checkpoints**.

What it deliberately does not do: preempt a task (a task that never calls `checkpoint()` keeps its worker until it returns), age queued work (a queued Background task stays Background), boost through locks (a Frame task waiting for a `FiberMutex` held by Background work is not boosted), or add workers when the lower lanes are stuck.

## Vocabulary

| Name | What it is |
|------|------------|
| `scheduler::Lane` | `eFrame`, `eInteractive`, `eBackground`, plus `eInherit`. Order is priority: `eFrame` = 0 is the highest. `eInherit` is a request, never a queue |
| `higher(a, b)`, `lower(a, b)` | the higher or lower of two lanes (by enum order) |
| `resolveLane(requested)` | turns a request into the lane a new task gets in the calling context; never returns `eInherit` |
| Effective lane | the higher of the running task's own lane and the lane of the `BoostCell` bound to its fiber (`fiber::self::effectiveLane()`) |
| Floor | per lower lane: if the lane has queued work and has not started a task for this long, the next pop takes it, ignoring Frame and the reserve |
| Frame reserve | number of workers kept off the lower lanes; at most `workers - reserve` workers run lower-lane work at once, floor turns aside |
| Slice | how long a lower-lane task runs before `checkpoint()` yields |
| `BoostCell` | the link between a producing task and whoever waits for its result: a lane that only rises, the producing task pointer, and what the producer waits for (`dependsOn`) |
| `LanePolicyConfig` | slice, floors, reserve, wait limit and the Frame-push wake switch |

| Lane | Runs | Where it comes from |
|---|---|---|
| `eFrame` | every task graph stage, what stages spawn, what Frame tasks await | only the pipeline stamps it; the rest arrives by inheritance or boost |
| `eInteractive` | work a person waits for outside the frame; anything pushed from a plain thread without a lane | the default off the workers |
| `eBackground` | bulk work that may fall behind | explicit only |

## Using it

Pass a lane when the work is less urgent than the code that creates it; otherwise leave the default `eInherit`. Long work calls `hg::checkpoint()` between steps.

```cpp
// a Background import step that cooperates
scheduler::exec(
	task::make_task(
		[] {
			for (auto& chunk : chunks) {
				decode(chunk);
				hg::checkpoint();   // yields once the slice is used; no-op in Frame
			}
		},
		Lane::eBackground
	)
);

// a Frame stage that needs the result now: await boosts the producer into Frame
auto result = await(hg::async([] { return loadIndex(); }, Lane::eBackground));
```

Rules at creation (`resolveLane`, [`Lane.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Lane.cpp)):

| Caller | `eInherit` | Explicit lane |
|---|---|---|
| A running task (fiber) | the task's effective lane | the lower of the request and the effective lane |
| Plain thread, affine thread, worker root fiber | `eInteractive` | the request; `eFrame` becomes `eInteractive` |

- A child may go lower than its parent, never higher. Only the pipeline creates Frame work from nothing: `CompositeSlot::staticEnqueue` and `dynamicEnqueue` stamp `eFrame` over whatever the stage task asked for.
- `Scheduler::exec` resolves. `execResolved` pushes the lane the task already has, `execBoostable` pushes in the higher of the task's lane and a cell's lane (futures use it).
- `make_task`, `make_repetitive_task`, `make_batch_task`, `hg::execute` and `hg::async` default to `eInherit`.
- Futures resolve the lane in `then()`, on the thread that builds the chain, not on the thread that completes it: the successor's lane is `lower(predecessor lane, resolveLane(eInherit))`. A promise state starts at `eFrame`, the neutral value of "lower of". See [futures](futures.md#lanes-and-the-wait-boost).

## How it works

### Pop order

`Schedule` holds three `FifoWorkSet`s (index = lane), a queued depth per lane, the last start time per lower lane, a count of workers in lower-lane work (`_lowerRunning`) and one in Frame work (`_frameRunning`). A worker reads `steady_clock` once and calls `pop(now, task, lane)`:

```hg-diagram
flowchart TD
    START["pop(now)"] --> FL{"Interactive, then Background:<br/>queued and now - lastStart >= floor?"}
    FL -- "yes, CAS on lastStart wins" --> TF["take one task of that lane<br/>(ignores Frame and reserve)"]
    FL -- "no" --> FR{"Frame queued?"}
    FR -- "yes" --> TFR["take Frame task<br/>wait trigger check"]
    FR -- "no" --> LW{"lower work queued and<br/>lowerRunning < workers - reserve?"}
    LW -- "yes, CAS claim" --> TL["take Interactive, else Background<br/>lastStart = now"]
    LW -- "no" --> PARK["pop fails: park until a push,<br/>at most until the next floor is due"]
```

1. **Floor turns.** For Interactive, then Background: if the lane has queued work and `now - lastStart >= floor`, a compare-and-swap moves `lastStart` to `now`. The winner pops one task of that lane. If the lane emptied in between, the turn is spent and the pop falls through. `lastStart` only moves forward, so a worker with an older `now` cannot reopen a period.
2. **Frame.** Uncapped. The worker counts itself in `_frameRunning` and checks the wait trigger (below).
3. **Lower lanes within the reserve.** If lower work is queued, the worker claims a slot with a compare-and-swap on `_lowerRunning` against `workers - effectiveReserve(now)`, then takes Interactive before Background and raises that lane's `lastStart` to `now`.

When the fiber returns (finished, yielded or parked) the worker calls `leave(lane)` with the lane it was counted under, not the task's current lane: a boost may have changed the latter.

The floor clock starts at `Schedule::setup`, so the first floor turn is due one period later.

### Parking with a floor due

A floor needs a worker that pops; there is no timer thread. A worker whose pop failed asks `parkTimeoutMillis(now)`: with lower work queued, the time until the earliest floor of such a lane is due, rounded up to whole milliseconds and at least 1; with no lower work queued, `parkForever` (`INFINITE`). It then parks with `waitForWork(epoch, timeout)`. This keeps workers held back by the reserve from sleeping through a floor.

### Frame reserve

The reserve is sized by demand unless `eLaneReserve` fixes it:

- **Demand.** Every Frame push raises `_framePeak` to Frame depth plus Frame running. A parent parked on its join does not count; its children do.
- **Roll.** `CompositePipeline::startFrame` calls `Schedule::rollFrame()`: the peak of the frame that ended goes into a ring of the last `reserveWindowFrames` = 8 frames, and the reserve becomes `clamp(max of the ring, 1, workers - 1)`. A roll also resets `frameWaitMaxMicros` and stamps the staleness clock. If the reserve dropped while lower work is queued, the roll bumps the push epoch and wakes one worker.
- **Wait trigger.** A worker that pops a Frame task which waited longer than `frameWaitLimitMicros` (push to pop, stamped in `queuedAt`) while `_lowerRunning > 0` raises the reserve by one at once (capped at `workers - 1`), records it as the frame's peak so the ring keeps it, and refreshes the staleness clock (owner decision Q02.18).
- **Staleness.** A demand reserve not rolled or raised for `reserveStaleMillis` = 250 ms counts as its minimum (1, or 0 on one worker): a stalled or stopped pipeline must not keep the lower lanes capped. `CompositePipeline::stop()` calls `resetReserve()`, which forgets the ring.
- **Fixed.** `eLaneReserve` above 0 fixes the reserve at `min(value, workers - 1)`; it never goes stale and the wait trigger does not touch it.
- **One worker**: the reserve is 0. Before the first frame and without a pipeline (tests, tools) it is 1.

A boosted task that enters Frame counts as Frame demand like any other (owner decision Q02.21).

### Slices and checkpoints

The worker stamps `Fiber::sliceStart` before each launch or resume. `fiber::self::checkpoint()` (public: `hg::checkpoint()`):

| Situation | Result |
|---|---|
| not on a task fiber | no-op |
| effective lane higher than the task's own lane (a boost arrived) | yields at once; the re-push queues it in the raised lane |
| effective lane is Frame | no-op |
| lower lane, `now - sliceStart >= slice` | yields; the task goes to the tail of its lane |

When a lower-lane fiber returns, the worker calls `noteRun(lane, micros)`: it keeps the per-lane maximum, and a run longer than twice the slice counts as an overrun. Debug builds log the first overrun of each lane once per `Schedule`.

### Wait boost

```cpp
// Engine.Scheduler/Process/BoostCell.hpp, trimmed
struct BoostCell : public ArcFromThis<BoostCell> {
	std::atomic<Lane> lane { Lane::eBackground };              // waiter urgency, only ever raised
	std::atomic<ptr<const task::TaskDelegate>> task { nullptr }; // the producer while it exists; compared, never dereferenced
	mutable std::atomic_flag linkLock {};
	Arci<BoostCell> dependsOn { nullptr };                     // what the producer waits for now
};
```

- `then()` gives each successor state a cell (`producer`) whose `dependsOn` is the predecessor's cell. Promise states and `ready` states have none, so a boost stops there.
- When a continuation is scheduled, its task pointer goes into the cell and the task is pushed with `execBoostable`. While it runs, the cell is bound to its fiber (`bindBoost`); when it ends, `cell->task` and the binding are cleared.
- `await(future)` on a fiber, when the state has a producer and is not done: links the awaiting task's own cell (if any) to the producer, then calls `boost(producer, resolveLane(eInherit))`, then parks. From a plain thread `await` does not boost.
- `boost(cell, lane)` walks the chain: raise the cell (stop if it already was at the lane or above, so a cycle ends); if it has a task, `Schedule::promote(task, lane, cell)`; follow `dependsOn`. At most `boostMaxHops` = 1,024 cells.
- `promote` searches the work sets below the target lane. `FifoWorkSet::erase` matches the address **and** the entry's `boostCell`, so an unrelated task that reuses a finished producer's address is never moved. The found entry is re-pushed with `pushBoostable`.
- `pushBoostable(task, cell)` pushes at `higher(task lane, cell lane)`, then re-reads the cell and promotes again if it rose meanwhile. The worker's re-push after a yield or park and `unpark` both go through it with the fiber's bound cell.
- A **running** producer is not in a queue, so `promote` finds nothing. Its next `checkpoint()` sees the raised effective lane and yields; the re-push queues it in the raised lane.
- Children and awaits of a boosted task read the effective lane, so they carry the boost on.
- Boosts are never withdrawn.
- A continuation that returns a future: its forwarding step (move the inner result into the outer state) runs inline where the inner state completes, through an iterative trampoline (`detail::runInline`). It links the outer cell to the inner producer and boosts the inner one only if a waiter already raised the outer cell above Background.

Every store-then-load pair that races a waiter's raise-then-read is `seq_cst`; the reasoning is in the design section 7.2 and the comments in `Schedule::pushBoostable` and `BoostCell.cpp`.

### Wake rules

Unchanged from the [worker policy](fibers-and-workers.md#park-and-wake): a push from a non-worker wakes one parked worker; a worker that pops and sees work left wakes one peer (the cascade). Two additions: with `wakeOnFramePush` a Frame push from a worker also wakes one, and a roll that lowers the reserve while lower work is queued wakes one. The owner's new wake rule (wake `min(k, parked)` when k is known, two otherwise) is chunk W02.15 and not built.

## Configuration

`LanePolicyConfig::fromConfig(config)` reads `SchedulerConfigProperty` keys; `GameEngine` and `EditorEngine` pass the result to `CompScheduler::setup`. A missing or mismatching value falls back to the default.

| Key | Field | Default | Unit |
|---|---|---|---|
| `eLaneSlice` | `sliceMicros` | 1000 | µs |
| `eInteractiveFloor` | `interactiveFloorMicros` | 8000 | µs |
| `eBackgroundFloor` | `backgroundFloorMicros` | 100000 | µs |
| `eLaneReserve` | `reserve` | 0 (by demand) | workers |
| `eFrameWaitLimit` | `frameWaitLimitMicros` | 250 | µs |
| `eWakeOnFramePush` | `wakeOnFramePush` | `false` | bool |

`Schedule::setup` clamps slice, both floors and the wait limit to at least 1: a floor of 0 would make every pop a floor turn, a slice of 0 would yield at every checkpoint. The defaults are the design's starting values; the sweep in design section 15 changed none except the wait limit (250 µs, owner decision Q02.12).

## Verification

Tests, all in `Heliogrim-Engine.Scheduler.Test` unless noted:

| File | Pins |
|---|---|
| `Schedule.cpp` (`LaneSchedule`) | pop order Frame, Interactive, Background; FIFO in a lane; nothing is promoted by time; `queued()` sums every lane |
| `LaneResolution.cpp` | plain thread gets Interactive and cannot request Frame; children inherit and may only go lower; a stage child is Frame; `higher` |
| `LanePolicy.cpp` | floor once per period under Frame load, one turn per equal `now`, none for a stale `now`, Interactive before Background, emptied lane falls through; reserve cap, fixed reserve clamp, 1 before the first roll, peak sizing, parked parent not counted, chain gives 1, fan-out forgotten after the window, staleness and its refresh by the wait trigger, fixed reserve never stale, `resetReserve`; wait trigger raises and does not without lower work; `queued(Lane)`; `wakeOnFramePush`; reserved worker parks and the floor still serves; shrinking reserve wakes; fan-out starts despite stuck lower lanes; park timeout forever or to the earliest floor |
| `LaneSlice.cpp` | checkpoint yields after the slice in a lower lane, never in Frame, no-op off a fiber; overrun counted only beyond two slices; Frame starts within a slice under lower load |
| `LaneBoost.cpp` | `promote` moves, never lowers, ignores absent tasks and foreign cells; `pushBoostable` uses the raised lane; yielded and running producers; dependency walk, second boost no-op, cycle ends, chain longer than 16; link after boost; children of a boosted producer inherit; destroy during boost; cell owned only by the task survives re-push |
| `CompositePipeline.cpp` | `EnqueueStampsFrameLane` |
| `test.cpp` | `RuntimeTest.PrioritySorting`: Interactive before Background on one worker |
| `Engine.Async.Test/FutureBoost.cpp` | queued producer boosted by a Frame waiter behind a flood, chain scheduled in the waiter's lane, nested wait, flattened promise future without a lower-lane hop, no producer is a no-op, deep flatten without recursion, flatten raises the inner producer only under a waiter, one run under racing boosts |
| `Engine.Async.Test/Future.cpp` (`FutureLane`) | a continuation keeps the lane resolved at `then()`; `async` from a plain thread is Interactive |

Models (TLA+, beside the source, sequential consistency only):

| Model | Checks |
|---|---|
| [`Process/Schedule.tla`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Process/Schedule.tla) + `.cfg` | push, pop with floor, Frame and reserve claim, leave, roll, bounded park, cascade, stop. Invariants `NoLostWakeup`, `FrameFirst`, `OneFloorTurn`, `ReserveHeld`; liveness `EveryTaskRuns`, `StopTerminates` (under drain only), `CascadeWakes`, `LowerProgress`. One lower lane stands for both. 2 workers complete; 3 workers and some liveness runs did not finish (owner decision Q02.22: accepted). Eight mutations listed in the header |
| [`Process/BoostCell.tla`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Process/BoostCell.tla) + `.cfg` | a boost racing the producer's yield and re-push, with a recycler that reuses the producer's address. `BoostHolds` (a boosted, unfinished producer is never queued below the waiter's lane at a quiescent point), `NoForeignPromote`. Three mutations. Cell lifetime is not modelled |

## Debugging

| Want to see | Where |
|---|---|
| A lower task that does not checkpoint | debug log `A lower-lane task ran {} us without a checkpoint (lane {}, slice {} us).`, once per lane per `Schedule`; lane is the index (1 Interactive, 2 Background). Counters: `Schedule::overruns(lane)`, `maxRunMicros(lane)` |
| How long Frame tasks wait | `Schedule::frameWaitMaxMicros()`: longest push-to-pop wait of a Frame task since the last roll |
| Queue depth per lane | `Scheduler::queued(Lane)` on the module, `Schedule::queued(Lane)` |
| The reserve | `Schedule::reserve()` (stored) and `effectiveReserve(now)` (after the staleness rule) |
| Policy under load | `LaneFloodBenchmark` in `Performance.Test` (below) |

`Performance.Test/LaneFloodBenchmark.cpp` (all `DISABLED_`, run with `--gtest_also_run_disabled_tests --gtest_filter=LaneFloodBenchmark.*`): a 15-stage chained `CompositePipeline` of 200 µs stages, 8 of them fanning out 8 children, under a Background flood of 5 ms tasks (four per worker), plus an Interactive probe every 50 ms.

| Test | Does |
|---|---|
| `DISABLED_Flood` | frame time, fan-out pickup and completion, Frame wait, probe latency, Background throughput, overruns; idle and under both floods |
| `DISABLED_PromoteScan` | a Frame task awaits a Background `async` behind `HG_BENCH_BACKLOG` (default 100,000) queued Background tasks |
| `DISABLED_Profile` | a steady mixed load for a sampling profiler; prints its pid before the timed part |

| Variable | Effect |
|---|---|
| `HG_BENCH_WORKERS` | worker count, 0 or unset = auto |
| `HG_BENCH_FLOOD_COOPERATES` | `Flood` only: unset = both flood kinds, 1 = cooperating only, 0 = non-cooperating only |
| `HG_BENCH_SLICE`, `HG_BENCH_FLOOR_I`, `HG_BENCH_FLOOR_B`, `HG_BENCH_RESERVE`, `HG_BENCH_FRAME_WAIT`, `HG_BENCH_WAKE_ON_FRAME_PUSH` | the `LanePolicyConfig` fields; unset = default |
| `HG_BENCH_BACKLOG` | trivial Background tasks queued up front (`PromoteScan` default 100,000, `Profile` default 0) |
| `HG_PROFILE_SECONDS` | `Profile` run time, default 30, 1 to 3600 |
| `HG_PROFILE_FLOOD` | `none`, `coop` (default) or `noncoop` |
| `HG_PROFILE_BOOST_EVERY` | every n-th frame awaits a 100 µs Background producer; default 4, 0 = off |
| `HG_PROFILE_ATTACH_SECONDS` | pause before the timed part, for attaching a profiler; default 0 |

Only a Debug configuration is built by default, so the numbers compare before and after on one machine; they are not absolute. The measured results are in design section 15.

## Limits and known issues

- **Reserve clamp on small machines.** The reserve is at most `workers - 1`, so one worker can always enter lower work. On 3 workers a lower task that never yields holds that worker for its whole run, and fan-out completion under a non-cooperating flood missed the design's bound by 15 % (design 15.1). Kept by the owner (Q02.11) until long tasks call `checkpoint()`.
- **Nothing in the engine calls `checkpoint()` yet.** Until long tasks do, every lower-lane task is non-cooperating and the reserve is the only protection; which tasks get it first is open (Q02.15).
- **`promote` searches linearly** in each lower work set under its spin lock. Awaiting a producer behind 100,000 queued Background tasks cost 1.8 to 27.6 ms in the Debug benchmark (design 15.3). Profiling first, chunk W02.16 (Q02.16).
- **Wake-up at a fan-out is a chain** of one wake per pop, so N helpers arrive after N hops; lower-lane work pushed from a running task wakes nobody until that task returns. The new wake rule is chunk W02.15.
- **The bounded park waits in whole milliseconds.** Where Windows rounds waits to its 15.6 ms tick, the 8 ms Interactive floor overshoots. No `timeBeginPeriod` (Q02.19).
- **The wait trigger has no cap**; under flood it can lift the reserve far above the fan-out width on a wide machine (19 of 20 at a 100 µs limit). Open in W02.16 (Q02.13).
- **No boost through locks** and none through `Signal` or `JoinCounter` (they have no producer; join children inherit the waiter's lane anyway).
- **Floor turns ignore the reserve**, by design: each costs Frame at most one worker for one slice per lane per period.
- **Windows only**, as the rest of the scheduler (`WaitOnAddress` with a timeout).

## Changing it

- Pop order, reserve or wake changes: update `Process/Schedule.tla` and keep its mutations failing. The wake rule change of W02.15 needs the model re-run (Q02.22).
- Boost, `promote`, `pushBoostable` or `FifoWorkSet::erase` changes: update `Process/BoostCell.tla`; mutation (c) (erase by address only) must still fail `NoForeignPromote`.
- A new work set type must implement `erase(task, cell)` with the same match on the entry's `boostCell`.
- A new config value: add it to `SchedulerConfigProperty`, `LanePolicyConfig` and `fromConfig`, clamp it in `Schedule::setup` if 0 breaks the policy, and add the `HG_BENCH_*` knob in `lanesFromEnv`.
- Rerun `LaneFloodBenchmark` before and after on the same machine.

### Pitfalls

- **Do not request `eFrame` to go faster.** Off a fiber it becomes Interactive; on a fiber it is clamped to the caller's lane. Only the pipeline and boosts make Frame work.
- **A lane is fixed when the task or `then()` is created**, not when it runs. A continuation built on a Background task stays Background even if a Frame task resolves the promise; awaiting it is what raises it.
- **Do not checkpoint while holding a lock.** A Background holder that yields keeps a Frame waiter behind it at the floor rate; there is no boost through locks.
- **`leave` uses the counted lane.** Code that changes a running task's lane must not touch the running counters; `pop` returns the lane it counted for that reason.
- **A future's value type must not suspend in its move constructor or destructor** (owner rule Q02.20); see [futures](futures.md#pitfalls).
