# Fiber Scheduler

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip`, 2026-11-16; the lane model (schedule, priorities, limits) re-checked at [`fd5affa5`](https://github.com/Heliogrim/Heliogrim-Engine/tree/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab), 2026-11-19. Not on `master` yet.
**Modules** (see the [module map](../../architecture/modules.md)): `Engine.Scheduler` (workers, fibers, the schedule, waitables, the frame runner), `Engine.Async` (fiber mutexes, lock types, promise and future), `Heliogrim/Async` (the public `hg::` surface).
**Related**: [fiber scheduler exploration](../../architecture/fiber-scheduler-exploration.md), [waitables design](../../architecture/scheduler-waitable-design.md), [promise and future design](../../architecture/promise-future-design.md), [worker policy design](../../architecture/worker-policy-design.md), [lane policy exploration](../../architecture/lane-policy-exploration.md), [lane policy design](../../architecture/lane-policy-design.md); PRs [#159](https://github.com/Heliogrim/Heliogrim-Engine/pull/159), [#165](https://github.com/Heliogrim/Heliogrim-Engine/pull/165), [#181](https://github.com/Heliogrim/Heliogrim-Engine/pull/181), [#185](https://github.com/Heliogrim/Heliogrim-Engine/pull/185).

This part has seven pages:

| Page | Read it when you want to |
|------|--------------------------|
| This overview | know what the scheduler is for and how the pieces fit |
| [Fibers and workers](fibers-and-workers.md) | submit a task, understand how a worker runs, parks and wakes, or change the worker count |
| [Lanes and priority](lanes.md) | choose a lane, make a long task cooperate with `checkpoint()`, understand the floor, the Frame reserve and the wait boost, or tune them |
| [Waitables and locks](waitables.md) | wait for something from a task without blocking a worker: `Signal`, `JoinCounter`, `FiberMutex`, `FiberSharedMutex`, the lock types |
| [Promise and future](futures.md) | hand a value from one task to another, chain work with `then`, or use `hg::async` / `hg::await` |
| [Affine threads](affine-threads.md) | run work that must stay on one OS thread (platform, IO) |
| [Task graph](task-graph.md) | declare a frame stage, or follow how the frame runner orders and dispatches stages |

## Purpose

The engine runs almost all of its work as small tasks on a fixed set of worker threads. Every task runs on a fiber, so any function at any call depth can suspend itself (`hg::yield`, `hg::await`, a contended `FiberMutex`) without a coroutine signature, and the worker that ran it is free for other tasks at once.

The scheduler core provides:

- **Workers**: one OS thread per worker, converted to a fiber, each looping "pop a task, switch to its fiber, handle the result". Idle workers park in the kernel and use no CPU.
- **The schedule**: three global FIFO sets, one per lane (`Frame`, `Interactive`, `Background`), shared by every worker. Frame goes first; a floor per lower lane and a Frame reserve decide when lower work runs ([lanes](lanes.md)). No per-worker queues, no work stealing, no ageing.
- **Fibers**: a pool of Win32 fibers. A task keeps its fiber while it is suspended and gets it back when it is resumed, possibly on another worker thread.
- **Parking**: a waiter (fiber or plain thread) hangs its `ParkNode` on a waitable and stops; the completer puts it back into the schedule. No waiter is polled.
- **Waitables and locks**: `Signal`, `JoinCounter`, `FiberMutex`, `FiberSharedMutex`, built on parking, usable from fibers and plain threads alike.
- **Promise and future**: one shared state, continuations scheduled as tasks, failure in the type.

What it deliberately does not do: preempt a task, run a task on a chosen thread (that is an [affine thread](affine-threads.md)), time out a wait, or withdraw a parked waiter. A task that blocks the OS thread (a `std::mutex`, a blocking syscall) blocks its whole worker.

## Where it sits

```hg-diagram
flowchart LR
    ENG["Editor / game engine<br/>(EditorEngine, GameEngine)"]
    CFG["Engine.Config<br/>SchedulerConfigProperty"]
    CODE["Engine and editor code<br/>exec, hg::async, await"]
    STG["Frame stages<br/>(*.Schedule bundles)"]
    AFF["Affine threads<br/>(platform, IO)"]
    subgraph SCHED ["Engine.Scheduler + Engine.Async"]
        CS["CompScheduler<br/>setup, exec, destroy"]
        SC["Schedule<br/>3 lane FIFOs, epoch"]
        WK["Workers<br/>N threads as fibers"]
        FP["FiberPool"]
        WT["Waitables, mutexes,<br/>FutureState"]
        CP["CompositePipeline<br/>(task graph runner)"]
    end
    CFG --> ENG --> CS
    CODE -->|"exec / make_task"| CS --> SC
    STG --> CP -->|"stage tasks"| SC
    AFF -->|"unpark, resolve"| WT
    SC --> WK
    FP --> WK
    WK -->|"park / unpark"| WT
    WT -->|"push resumed task"| SC
```

The engine creates a `CompScheduler` and calls `setup(workers, reserve, lanes)` during `init` with two config values and the `LanePolicyConfig` (`EditorEngine.cpp`, `GameEngine.cpp`), and later `finalize()`, which builds the frame runner's stage graph from the registered stages. From then on everything pushes into one `Schedule`: plain `exec` calls, the frame runner ([task graph](task-graph.md)) for each stage, `then` continuations of futures, and `unpark` for every waiter that is resumed. `destroy()` stops and joins the workers at shutdown.

## The big picture

```hg-diagram
flowchart TD
    PUSH["Schedule::push(task)<br/>queued +1, epoch +1,<br/>wake one if pusher is not a worker"] --> SETS[("eFrame | eInteractive | eBackground")]
    SETS --> POP{"worker: pop<br/>floor turn, Frame,<br/>lower within the reserve"}
    POP -- "nothing takeable" --> PARK["WaitOnAddress(epoch),<br/>bounded by the next floor"]
    PARK --> POP
    POP -- "task" --> CAS["more queued?<br/>wake one peer (cascade)"]
    CAS --> RUN["switch to the task's fiber"]
    RUN --> R{"fiber came back"}
    R -- "task finished" --> REL["fiber back to the pool"]
    R -- "plain yield" --> PUSH
    R -- "parked on a waitable" --> WAIT["fiber waits in a ParkQueue"]
    WAIT -- "unpark by completer" --> PUSH
```

Three rules carry the design:

1. **One global queue per lane.** Every worker takes every lane: Frame first, the lower lanes on their floor or within the workers the Frame reserve leaves. A resumed task goes back through the same `push` as a new one, in its own lane or a lane a boost raised it to. Nothing ages.
2. **A waiting task is not in the queue.** It sits in the waitable's `ParkQueue` until the completer unparks it. One atomic exchange on the `ParkNode` decides whether the completer or the worker re-queues it, so a wake can never be lost or doubled.
3. **Wakes are cheap and rare.** A push from a worker never wakes anyone, because that worker pops next. A worker that pops and sees more queued work wakes one peer. Only pushes from outside the workers wake directly.

## A first example

From [`Engine.Scheduler.Test/Waitable.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler.Test/Waitable.cpp), trimmed (the test's watchdog is left out): the test thread starts three tasks and waits for all of them with a join counter.

```cpp
engine::scheduler::JoinCounter counter { 3 };
std::atomic<u32> finished { 0 };

for (u32 i = 0; i < 3; ++i) {
	s_->exec(
		task::make_task(
			[&] {
				++finished;
				counter.done();
			}
		)
	);
}
counter.wait();
```

The same `counter.wait()` called from inside a task would park that task's fiber instead of blocking a thread; the caller does not need to know which case it is in. The future form of the same idea, from [`Engine.Async.Test/Future.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async.Test/Future.cpp):

```cpp
auto f = async([] { return 7; });
EXPECT_EQ(await(std::move(f)).value(), 7);
```

## Verification

The scheduler's atomics are model-checked with TLA+; each model sits beside its source as `<Name>.tla` + `.cfg`:

| Model | Checks |
|-------|--------|
| `Engine.Scheduler/Process/Schedule.tla` | worker park and wake over a Frame and a lower lane: no lost wake-up, Frame first, one floor turn per period, the reserve cap holds, every task runs, the lower lane progresses under endless Frame work, the cascade wakes a parked peer, stop terminates (see [lanes](lanes.md#verification)) |
| `Engine.Scheduler/Process/BoostCell.tla` | a wait boost racing the producer's yield and re-push: a boosted producer is never left queued below the waiter's lane, and an unrelated task at a reused address is never promoted |
| `Engine.Scheduler/Waitable/Signal.tla` | `Signal` with the park handshake: no lost wake-up, when the object may be destroyed |
| `Engine.Scheduler/Waitable/JoinCounter.tla` | set exactly once, only after every child, creator returns |
| `Engine.Async/Primitive/FiberMutex.tla` | mutual exclusion, no lost wake-up |
| `Engine.Async/Primitive/FiberSharedMutex.tla` | exclusion, word and queue invariants, handoff, no lost wake-up |
| `Engine.Async/Future/FutureState.tla` | each continuation runs once and only after both value and `then`, chains complete |
| `Engine.Scheduler/Pipeline/CompositePipeline.tla` | the frame runner's stop protocol (see [task graph](task-graph.md)) |

Unit and stress tests live in `Heliogrim-Engine.Scheduler.Test` and `Heliogrim-Engine.Async.Test`; each page lists the ones that pin its part. Relacy and TSan runs are not set up.

## Limits and known issues

- **Windows only.** `fiber::self::current()` is `todo_panic` on POSIX and `Schedule::waitForWork` calls `WaitOnAddress` unguarded; the `ucontext` branches in `Fiber.cpp` and `Worker.cpp` do not make a working scheduler.
- **Lower lanes depend on cooperation.** No task is preempted. A lower-lane task gives its worker back only at `hg::checkpoint()`, and nothing in the engine calls it yet; until then the Frame reserve is the only protection, and one worker always stays open to lower work (the reserve is at most `workers - 1`). Details and the other lane limits on [lanes](lanes.md#limits-and-known-issues).
- **`delay` does not delay.** `CompScheduler::delay` ignores the tick count and runs the task now; `hg::delay` is `todo_panic`.
- **Unbounded fiber pool.** Parked fibers keep their stacks and the pool creates new fibers whenever reuse fails. A workload that parks tens of thousands of tasks grows memory without a diagnostic.
- **Engine global.** `scheduler::exec`, `hg::execute`, `hg::async` and every future continuation reach the scheduler through `Engine::getEngine()`. Tests therefore boot a small test engine (`TestSchedulerEngine.hpp`).
