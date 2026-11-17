# Worker Policy (Design)

**Status**: design, draft 2026-11-13 (work chunk [W02.8](../plan/work/concurrency-fibers.md), issue [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84)). Builds on the [task graph design](task-graph-design.md) (as built on `feat/task-graph`, PR #175, which lifted the one-worker override) and the [affine threads design](affine-thread-design.md) (as built, PR #164). Decision Q02.9 on the work page is the brief; the measurements in section 3 were taken in the brainstorm with the owner, and the owner chose the park policy of section 6 from them.

Markers: **Decided** = owner decision (work page Decisions table or this chunk's brainstorm). **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

Since PR #175 the scheduler starts `hardware_concurrency() - 1` workers (23 on the owner's Ryzen 9 5900X) and every idle worker spins on `Schedule::pop` without pause (`Worker.cpp`, the `yield` is commented out). The owner's experience with the editor open: the whole machine stutters; power draw, heat and clock throttling rise; CPU latency for every other process gets worse; background services and the engine's own background work slow down. The cause is spinning that achieves nothing.

This chunk makes an idle engine look idle to the OS. Idle workers park in the kernel and are woken by work, the worker count leaves room for the rest of the system and comes from config, the unused IO worker split and the unenforced critical split go, and the threads that must react quickly (platform, IO) get OS priority instead of reserved cores.

## 2. State of the inputs (checked 2026-11-13 on `feat/task-graph` `e644ebe6`)

- `CompScheduler::setup(u32 workers_)`: `USE_WORKER_COUNT` (build-time) forces the count; `0` means auto, `max(hardware_concurrency() - 1, 1)`. Then `log2(n)` workers get mask `eCritical` (for `n > 4`) and `log8(n)` get `eIO` (for `n > 8`); the rest `eAll`. On 23 workers: 4 critical, 1 IO, 18 all.
- `Schedule::pop(mask, task)` starts at `maskToPriority(mask)` and walks every lower set; `FifoWorkSet::pop` ignores the mask. So a critical worker takes any task, and an `eIO` worker (`maskToPriority(eIO)` falls to the default, normal) takes every normal and lower task. Nothing pushes an `eIO` task; `TaskMask::eIO` is used only by `CompScheduler.cpp:83` and `TaskMaskValues`.
- `Worker::start` raises critical workers to `THREAD_PRIORITY_HIGHEST`; the others stay normal.
- The worker loop (`Worker::handle`): `pop`, run the fiber, re-push a yielded task or let `unpark` re-push a parked one; on an empty pop it loops again at once. Stop sets a `volatile bool` the loop polls.
- Every push goes through `Schedule::push`: `CompScheduler::exec`, `CompositeSlot::submit` (one push per task of a stage), the worker's re-push of a yielded task, `Park.cpp`'s unpark. `Schedule::tick()` moves tasks between sets via `ScheduleWorkSet::transfer`, which never makes work appear when every set was empty.
- Engine threads outside the workers: the editor's main thread sleeps on an `atomic_flag` from `start()` to shutdown (`Editor.Main.cpp`); the platform thread (`WinPlatform`, an `AffineThread`) blocks in its message wait; the IO thread (`IoThread`, an `AffineThread`) blocks on its completion port. Render submission runs on fibers. **No non-worker engine thread runs hot today**; the audio device thread will be the first (audio runtime design).
- `AffineThread` owns a `std::thread` and names it; it never sets a priority. `thread::Thread::setPriority` maps `eTimeCritical/eHigh/eNormal/eLow` to `THREAD_PRIORITY_TIME_CRITICAL/HIGHEST/NORMAL/LOWEST`.
- `Engine.Config`: keys are enums or strings, values `bool, u32, f32, StringView, String`; providers are filled programmatically at boot (`Editor.Boot/Boot/ConfigInit.cpp`). `EditorEngine::preInit` initialises config before `init()` calls `_scheduler->setup(Scheduler::auto_worker_count)`, so a config value can reach `setup`. No config file or command-line source exists.

## 3. Measurements (2026-11-13, Ryzen 9 5900X, 12 cores / 24 logical, two CCDs: logical 0 to 11 and 12 to 23, Windows 11, clang-cl `/O2`)

Throwaway benchmarks (W02.0 experiment 2 territory), one-way latency from the waker's store to the sleeper's first instruction, TSC-timed. Load = threads spinning on arithmetic at normal priority.

**Primitive versus load** (µs, p50 / p99):

| Primitive | Idle | 12 busy threads | 24 busy threads |
|---|---|---|---|
| spin (`_mm_pause`) | 0.05 / 0.2 | 0.07 / 6 | 0.2 / **4,500** |
| `SwitchToThread` | 0.15 / 1 | 0.2 / 24 | **3,700 / 24,000** |
| `WaitOnAddress` | 5–7 / 12–26 | 6–10 / 9–17 | 4–5 / 7–9 |
| Event (`SetEvent`) | 5–7 / 9–25 | 6–8 / 9–13 | 5 / 8–13 |

Notify with nobody waiting: `WakeByAddressSingle` 2.1 ns, `atomic::notify_one` 2.3 ns (the MSVC STL routes it to the same call), `SetEvent` 267 ns.

**Placement** (waker pinned to logical 0; µs, p50 / p99): spin 0.04 / 0.06 (SMT sibling), 0.06 / 0.07 (same CCD), 0.20 / 0.49 (other CCD); park 4.3 / 12, 4.7 / 24–34, 5.7 / 7.

**One push, K parked waiters** (µs, p50 of first / last woken, p99 of last): K = 2: 5 / 6.5 (12); K = 4: 5 / 9.4 (16–22); K = 11: 5 / 20 (27–34); K = 18: 5 / 30 (40–60). `WakeByAddressAll` is no faster than K single wakes: the kernel wakes serially, about 1.4 µs per extra waiter, on the waker's time.

**Gate counter** (a shared atomic each idle worker would update to claim a spinner slot): 15 to 40 ns per idle transition.

Reading:

1. Parking is affordable: about 5 to 10 µs to wake, p99 10 to 25 µs, against a frame of 0.5 to 11 ms (owner: 90 to 700 FPS today, 1,200 to 2,000 FPS expected once UI command and layout caching land).
2. Under oversubscription the kernel wait is the only primitive that stays bounded; spinning and yielding blow up to milliseconds because spinners are preempted. Parking plus a reserve is what removes the stutter.
3. `SwitchToThread` is unusable as an intermediate step.
4. Notifying with no waiter costs nothing, so a push may always notify; no "is anyone parked" bookkeeping is needed.
5. CCD placement is noise for parking (about 1 µs); worker placement stays topology-blind.
6. Waking many workers from one thread is a serial cost on that thread.

Not measured: wake latency under the engine's real load, and the cost of the first wake after a long idle on a laptop power plan. The latter is a builder check on the owner's machine only if section 10's numbers look off.

## 4. Goals

1. An idle editor's worker threads use near-zero CPU, apart from the one worker that runs the frame chain. The frame is never paced: `CompositePipeline` starts the next frame when the last node completes and the swapchain prefers mailbox, so one worker (and the GPU) runs frames back to back even when nothing changes. Pacing is not this chunk (**Decided**: its own work package with an exploration, W02.9). The target here is that the other workers stop costing anything.
2. Frame time while working is no worse than on `feat/task-graph` with spinning workers.
3. The default worker count leaves room for the rest of the system, is stated with its derivation, and can be set from config.
4. No `eIO` worker, no critical worker split.
5. Latency-critical affine threads (platform, IO; audio when it exists) run at raised OS priority.
6. The park/wake protocol is model-checked (repository rule for atomics in `Engine.Scheduler`).

## 5. Non-goals and anti-goals

Non-goals: a spinner budget (section 6.4); queue policy changes, work stealing, per-worker queues (Q02.2: measure first); ageing (Q02.8, measured after this chunk on parked workers); core pinning or CCD-aware placement (section 3, reading 5); MMCSS registration (belongs to the audio device thread, S38); a config file format; frame pacing (W02.9); the fibers that still wait by polling with `fiber::self::yield()` (`hg::await` in `Heliogrim/Async/Await.cpp`, `CompositePipeline::stop`, release `VkSwapchain::acquireNext`): each keeps one worker cycling while it waits, never parked. **Decided**: a W02.2 follow-up, its own work package (W02.10).

Anti-goals: the engine itself stutters because a parked worker is slow to return (a wake on the frame's critical path where today there is none); a push pays for waking every worker; a worker sleeps through `stop()`; a lost wake-up that leaves ready work queued with every worker parked.

## 6. Park and wake (**Decided** by the owner 2026-11-13: park immediately, cascade wakes, no spinner budget)

### 6.1 State

`Schedule` gains one `std::atomic<u32> _pushEpoch` on its own cache line. It is the parking word: workers park on it, pushes bump it. Nothing else is shared.

### 6.2 Worker side

In `Worker::handle`, replacing the empty-pop branch:

```text
loop:
    e = schedule.epoch()                 // acquire load, BEFORE the pop
    if schedule.pop(mask, task):         // pop decrements _queued
        if schedule.queued() > 0: schedule.wakeOne()   // cascade (6.3)
        run task as today
    else if not interrupt:
        WaitOnAddress(&_pushEpoch, &e)   // returns at once if the epoch moved since the load
```

Why no wake is lost: the load happens before the pop, and the pop and every push serialise on the work set's lock. If the push's insert is ordered before the pop, the pop finds the task. If it is ordered after, the worker's epoch load happened before the pusher's increment (lock release → acquire carries it), so the worker read the old epoch; `WaitOnAddress` compares against the current value atomically with registering the waiter and returns immediately, or the pusher's wake finds the registered waiter. A spurious return of `WaitOnAddress` only costs one loop iteration. The model in section 9 checks exactly this, with the lock abstracted to its order.

### 6.3 Push side and the cascade

`Schedule` keeps one more atomic, `_queued` (tasks in all sets), incremented by every insert and decremented by every successful pop (builder check, 2026-11-13: without it a worker cannot tell whether waking a peer is useful).

**Push from outside the workers** (`exec` from the platform or main thread, affine completions, a test thread): insert, `_queued` up (as built: `_queued` up **before** the insert, section 10), `_pushEpoch.fetch_add(1, release)`, `WakeByAddressSingle(&_pushEpoch)`. With nobody parked the wake is 2 ns.

**Push from a worker** (the frame runner's `dispatch` → `CompositeSlot::submit`, the worker loop's re-push of a yielded task, `unpark` called on a worker, `exec` from a task): insert, `_queued` up, epoch bump, **no wake**. Reason (builder check): the completing worker returns to its loop and pops next, usually the very task it pushed; a wake there finds an empty queue, parks again, and at hundreds to thousands of frames times seventeen stages that is thousands of wasted context switches per second. The test is the existing thread-or-fiber check (W02.2): a push made on a fiber is a worker push (**builder's call** on the exact predicate).

**The cascade**: a worker that pops a task successfully reads `_queued` after its pop; if it is non-zero it calls `wakeOne()` before running the task. This is the one rule that turns queued work into awake workers:

- A strict chain (the frame today, task graph design 8): the completing worker pushes the successor quietly, pops it, sees `_queued == 0`, wakes nobody. No kernel call per stage.
- A fan-out of N tasks from a worker: the worker pops one, sees N − 1 queued, wakes one; that one pops, sees N − 2, wakes the next; the chain stops when the queue is empty. Each wake is paid by a different worker, never N by one.
- A yielded task re-pushed by its own worker: popped again by that worker or another awake one; no wake unless other work is queued.
- At most one wasted wake per burst (the last woken worker can find the queue drained by an awake one).

Cost: two uncontended-to-moderately-contended RMWs per task (`_queued` up and down, section 3's counter measurement: 15 to 40 ns) and the epoch bump on push.

### 6.4 No spinner budget (**Decided**)

Keeping one or two workers spinning for 10 to 20 µs was proposed and dropped. The owner doubted the bookkeeping would pay; the measurements say the bookkeeping is cheap (15 to 40 ns) but the spinning is not: it saves one 5 µs wake per fan-out and burns a core for every idle gap, at frame rates where the gaps between frames are shorter than any useful spin. The owner's point stands for the general case: the more workers, the likelier a worker is already awake or about to finish when a task arrives. A spinner budget can be added later in `Worker::handle` only if a measurement shows fan-out stalls; nothing in this design blocks it.

### 6.5 Stop

Today the interrupt flag is a `volatile bool` on the worker thread's own stack, reached through `_interrupt_ptr`, and `Worker::stop()` sets it and joins; `CompScheduler::destroy` stops workers one at a time (its only caller). With parked workers that join would hang. **Proposal**: the flag becomes an `std::atomic<bool>` member of `Worker`; `Worker::stop()` splits into `requestStop()` (set the flag) and the existing `join()`; `CompScheduler::destroy` requests every stop, calls `Schedule::wakeAll()` (bump the epoch, `WakeByAddressAll`), then joins every worker. A worker re-checks the flag after every return from the wait.

### 6.6 Ageing transfers

`Schedule::tick()` runs after every slot completion and moves tasks one set upward (`transfer`), each set behind its own spin lock, while `pop` walks the sets from critical down. A worker can find set 0 empty, lose the race to a transfer that moves a task from set 1 into set 0, find sets 1 to 3 empty and park (builder check). Liveness survives (`tick`'s caller is a worker that pops again), but a parallel slot is lost. **Proposal**: `transfer` bumps the epoch when it moved at least one task (no wake): a worker that loaded the epoch before the transfer then returns from `WaitOnAddress` at once and pops again. `tick` itself is unchanged (Q02.8 is out of scope).

### 6.7 What stays

The fiber park path (`Park.cpp`'s unpark re-push) goes through `Schedule::push` and follows 6.3: from a worker it is quiet, from an affine thread it wakes. Affine completions reach workers the same way.

## 7. Worker count and masks

### 7.1 Count (**Decided** by the owner 2026-11-13: logical processors, a logarithmic system reserve, config)

```text
auto    = max(logical - reserve, 1)
reserve = floor(log2(logical)) + hot
```

`floor(log2(logical))` is the share left to the OS, the IDE and background services, which grows slowly with the machine (owner). `hot` is the number of engine threads outside the workers that run continuously, added on top, because the logarithmic share is for the rest of the system, not for the engine's own threads. Today `hot = 0`: the editor's main thread sleeps from `start()` to shutdown, and the platform and IO threads block in their waits (section 2). The audio device thread (S38) will be the first; its chunk raises `hot` by one where it starts the thread. **Proposal**: `hot` is a constant in `CompScheduler.cpp` (`0`) with that comment, not a config key.

| Logical | Reserve | Workers |
|---|---|---|
| 4 | 2 | 2 |
| 8 | 3 | 5 |
| 16 | 4 | 12 |
| 24 (5900X) | 4 | **20** |
| 32 | 5 | 27 |
| 64 | 6 | 58 |

`floor` rather than `round` (**Proposal**): on the 5900X `log2(24) = 4.58`, so `round` would give 19 workers; the difference is one thread and `floor` is `std::bit_width(logical) - 1`, no floating point.

Precedence (**Decided**): the config keys set the count and the reserve; build-time macros override both for tests and specific builds: `USE_WORKER_COUNT` (exists) forces the count, a new `USE_WORKER_RESERVE` forces the reserve. `1` stays the serial check (task graph `maxInFlight`, W02.6).

### 7.2 Masks

Every worker takes `eAll`. The critical and IO splits go: the critical split was never enforced (`FifoWorkSet::pop` ignores the mask) and its only effect was raised priority on four workers; the IO split had no `eIO` tasks. `TaskMask::eIO` is deleted with its `TaskMaskValues` entry. Lanes keep working as before: they choose the work set, and `Schedule::pop` walks sets from critical down for every worker.

### 7.3 Priority

Workers run at normal priority, all of them (today four run at `HIGHEST`). **Proposal**: `AffineThread::start` takes a `thread::priority` (default `eNormal`) and sets it on its own thread right after naming it. The platform thread starts at `eHigh` (input and window messages; it blocks most of the time, so a raised priority costs nothing when idle). The IO thread starts at `eHigh` (completions unpark fibers on the critical path of streaming). The audio device thread (S38) will use MMCSS, not this enum. The priority mapping moves from `Thread.cpp`'s file-local `set_priority` to a free function in `Engine.Scheduler/Thread/Thread.hpp` that takes a native handle, so `AffineThread` (in `Engine.Async`, which already links `Engine.Scheduler`) can call it on `std::thread::native_handle()`; **builder's call** whether to call it from inside the thread with `GetCurrentThread()` instead.

## 8. Config (**Decided**: the count comes from `Engine.Config`)

New `enum class SchedulerConfigProperty { eWorkerCount, eWorkerReserve }` in `Engine.Config/Enums.hpp`, both `u32`, `0` meaning auto. Initialised at boot by both engines' config init with `0` (the editor in `Editor.Boot/Boot/ConfigInit.cpp`). `CompScheduler::setup` changes from `setup(u32 workers_)` to `setup(u32 workers_, u32 reserve_)`; the engines read the two keys (`getOrDefault<u32>`) and pass them. `Scheduler::auto_worker_count` stays `0`. The auto formula lives in one function, `scheduler::autoWorkerCount(logical, reserve)`, pure and unit-tested; a `reserve` of `0` means the default of 7.1.

Override source (**Decided**): the config entries are the source; no config file exists yet, so until one does they hold `0` (auto) unless code sets them. The build-time macros of 7.1 are the override for tests and specific builds. No environment variables.

## 9. Model (**Decided**: the repository rule for atomics in `Engine.Scheduler`)

`Schedule.tla` + `.cfg` beside `Schedule.cpp`, PlusCal, following the `verifying-concurrency` skill: N workers each looping load epoch → pop (walking two sets, each set's lock modelled as an atomic insert or pop on that set) → park on epoch; one external pusher (insert, bump, wake) and worker pushes (insert, bump, no wake); the `_queued` counter and the cascade; one ager that transfers set 1 into set 0 and bumps the epoch; `WaitOnAddress` modelled as an atomic compare-and-enqueue, `WakeByAddressSingle` as dequeue-one, spurious returns allowed; `wakeAll` on stop. Two sets are enough to expose the transfer race of 6.6; four add states, not behaviours. Checks: no lost wake-up (if a task is queued and every non-stopped worker is parked, some wake is pending: expressed as "queued tasks are eventually popped" under weak fairness); stop terminates (every worker eventually exits after `wakeAll`); `CHECK_DEADLOCK TRUE` with "all workers exited" as the only terminal state. N = 3 workers, 3 tasks (as built: complete only at N = 2 workers, 2 tasks, and the transfer mutation passes; section 10). Mutations that must fail: load the epoch after the pop instead of before; drop the wake in `wakeAll`; drop the cascade (a fan-out from a worker then never reaches a parked worker: checked as "while two tasks are queued and a worker is parked, some worker eventually runs a second task in parallel" or, if that is not expressible cleanly, as the weaker "every queued task is eventually popped", **builder's call**); drop the epoch bump in `transfer`. Tier 2b (Relacy) stays pending like the skill's other rows.

## 10. Measuring the result

Before and after, on the owner's machine, editor started and left idle on the default scene for 30 s:

- **Idle CPU**: total CPU time of the worker threads over 30 s (thread times from the process, as W02.3 measured the platform thread; a small script or `Get-Process` thread times, **builder's call**). Today's expectation: about 23 cores busy (22 spinning plus the frame chain); target about one core, the frame chain (goal 1).
- **Frame time**: frames per 30 s while idle and while orbiting the viewport, from the frame counter the editor shows or by counting `TickEnd` completions (**builder's call**); no regression beyond noise.
- **Default count**: logged once at `setup` (`IM_CORE_LOG`: logical, reserve, workers, source).

**Result (2026-11-13, owner's 5900X, Debug editor, default scene, process CPU time over 30 s after a 10 s settle)**: before (`feat/task-graph` plus the owner's uncommitted tree) **22.14 busy cores**, 41 threads; after (`feat/worker-policy`) **0.93 busy cores**, 38 threads, log line `Scheduler starts 20 workers (24 logical threads, reserve 4, source: auto)`. Goal 1 met: what remains is the unpaced frame chain (W02.9). Frame rate not measured (owner chose CPU only). Process time rather than per-worker thread time: the difference is the whole spin, so the finer split was not needed.

**Builder findings against this design (execution, 2026-11-13)**:
- `_queued` goes up **before** the work-set insert, not after (6.3 says "insert, `_queued` up"): otherwise a racing pop can decrement first and wrap the `u64`, and the cascade fires spurious wakes. A failed insert undoes the increment.
- 6.6 holds only because `tick()` runs on the completing worker: `transfer` bumps the epoch after the set lock is released and wakes nobody, so a worker already parked is not woken. The worker that ticks pops the moved task itself (or cascades if more moved); a non-worker ager would need a `wakeOne`. Commented in `Schedule::transfer`. This is also why the "no transfer bump" mutation of section 9 does not fail.
- Model bound: `Schedule.tla` passes completely at N = 2 workers, 2 tasks (587,726 distinct states, stop racing queued work included); N = 3 full runs were stopped after 7 to 9 min with a growing queue, and an invariants-only N = 3 run found no violation in 139.4 M distinct states before its 15 min cap. Mutations: epoch after pop fails `NoLostWakeup`, no wake in `wakeAll` fails `StopTerminates`, no cascade fails `CascadeWakes`, no transfer bump passes (above).
- `Config::getOrDefault` could not be instantiated (it called a nonexistent `get<T>`); repaired, and the engines read both keys through it.

## 11. Placement and tests

- `Engine.Scheduler/Process/Schedule.{hpp,cpp}`: epoch, `_queued`, `push` (wakes only off-worker), `wakeOne`, `wakeAll`, `waitForWork(epoch)` (the `WaitOnAddress` call, so the Win32 include stays in one `.cpp`).
- `Engine.Scheduler/Worker/Worker.{hpp,cpp}`: loop change, atomic interrupt.
- `Engine.Scheduler/CompScheduler.{hpp,cpp}`: count, masks, stop order. `autoWorkerCount` in `CompScheduler.cpp` or beside it.
- `Engine.Scheduler/Task/TaskMask.hpp`: `eIO` gone.
- `Engine.Scheduler/Process/WorkSet/*`: nothing; `transfer`'s epoch bump sits in `Schedule::transfer`.
- `Engine.Async/Affine/AffineThread.{hpp,cpp}`, `Support.Platform.Win32/WinPlatform.cpp`, `Engine.IO.Dispatcher/IoThread.cpp`: priority.
- `Engine.Config/Enums.hpp`, `Editor.Boot/Boot/ConfigInit.cpp`, `Editor.Core/EditorEngine.cpp` (and `Heliogrim.Main`'s engine, which does not compile, task graph design 11: edit it alongside, unverified).
- Tests in `Engine.Scheduler.Test`: `autoWorkerCount` table (the rows of 7.1 plus 1 and 2 logical, which floor at 1 worker; reserve override); a worker parks (its thread's CPU time stops growing over 100 ms with an empty schedule, or a hook counts waits; **builder's call**) and wakes on `exec`; a burst of 64 tasks pushed from the test thread to 4 parked workers all complete; `stop` returns with every worker parked; the existing 68 stay green, including the runner tests on N workers. Stress: 10,000 short tasks pushed from 2 threads into 8 workers that park between bursts, all complete, repeated 50 times.

## 12. Left to the builder and open for the owner

- Answered by the owner 2026-11-13: idle target and pacing (goal 1, W02.9), yield-polling waits (W02.10), override source (8), reserve (7.1).
- Builder's call: the exact idle-CPU and frame-time method (section 10); where the priority mapping is applied (7.3); how a test detects a parked worker (11).
- Not this chunk: ageing (Q02.8), a spinner budget, the audio thread's MMCSS, a config file, the game executable.

## 13. Decisions made in this document (for review)

1. Idle workers park immediately on one epoch word with `WaitOnAddress`; no spinning, no yield step (6, owner).
2. A push always bumps the epoch; only pushes from outside the workers wake; a worker that pops while more work is queued wakes one peer (6.3).
3. Stop requests every worker's stop, wakes all, then joins (6.5).
4. An ageing transfer bumps the epoch (6.6).
5. Auto count `max(logical - (floor(log2(logical)) + hot), 1)`, `hot = 0` today; config keys, build-time macros override (7.1, owner).
6. Every worker takes every set; `eIO` deleted; workers at normal priority (7.2, 7.3).
7. Platform and IO affine threads start at `eHigh` (7.3).
8. Two `u32` config keys, `0` = auto; no environment variables (8, owner).
9. `Schedule.tla` checks the park/wake protocol (9).
