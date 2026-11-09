# Work: Concurrency, Fibers, Task Graph

**Systems** S02 (absorbs #77) · **Issues** [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84), [#77](https://github.com/Heliogrim/Heliogrim-Engine/issues/77) · **Track** A · **Milestone** M1
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for the topic [Concurrency](../topics/concurrency-fibers.md). Nothing here is decided; designs produced by these chunks land in `architecture/*-design.md`, decisions in `adr/`.

## Cross-reference

| Existing page | What it already settles | Still open or in tension with the plan |
|---|---|---|
| [Fiber scheduler exploration](../../architecture/fiber-scheduler-exploration.md) | Current state (polled waits, no identity, no dependencies); candidate architectures A, B, C with the lean "B reached through A"; order of work (waitables, dependencies, identity, coroutine bridge, queues, vtime); five first experiments | Which candidate; coroutine resume affinity; stackful-inside-stackless rule; cancellation model; per-worker queues or global lanes |
| [Observability exploration](../../architecture/observability-exploration.md) | Needs a fiber-local context slot; prefers the control block | Shared context layout (owned here) |
| [Storage exploration](../../architecture/storage-exploration.md) | IO thread never calls the scheduler; posts completions to an inbox | The inbox is the waitable signal path; owned here as the affine-thread contract |
| [Actor archetypes design](../../architecture/actor-archetypes-design.md) | Asks for explicit stage DAG dependencies | The task graph builder is the answer; stage registration API must fit the archetype dispatch |
| [Audio runtime design](../../architecture/audio-runtime-design.md) | Device callback on its own thread, lock-free queues to the engine | First non-IO client of the affine-thread seam |
| Issue #77 | Split-count `Arci` protocol | Landed on master 2026-11-01 (checked by W02.1); weak-memory verification still open; the waitable design does not use `Arci` on the wait path |

Consistency: the topic page, the exploration and #84 agree on the order of work. The exploration's experiments 1 to 5 are the content of W02.0 and were never run.

## Architecture

- **Bundles**: `Engine.Scheduler` keeps workers, fibers and lanes. New sub-bundle `Engine.Scheduler.Graph` (task graph builder, stage registry). `Engine.Async` is rebuilt on waitables, not replaced. `Engine.IO.Dispatcher` becomes the first `AffineThread` client (owned by S03).
- **Layer**: L2 services. Nothing above L2 touches `Fiber` directly; systems register stages and await waitables through `Heliogrim/Async`.
- **Provides**: `Waitable`, `TaskGraph`, lanes, `AffineThread`, fiber context, deterministic mode switch.
- **Consumes**: `Arci` split count (`Engine.Common/Managed`), config for worker count and determinism (`Engine.Config`), span hook from S04 (a function pointer or a null object until S04 exists).

```hg-diagram
flowchart LR
    AT["AffineThread<br/>(IO, pump, audio, net, submit)"] -->|complete| W["Waitable<br/>state + wake list"]
    W -->|wake| L["Lanes<br/>Critical / Normal / Background"]
    TG["TaskGraph<br/>stages {reads, writes, lane, after}"] -->|ready tasks| L
    L --> WK["Workers<br/>fibers with context"]
    WK -->|await| W
```

## Code design

Contracts, in the project's style (`ptr<T>` non-owning, `ref<const T>` for structs, `Opt`, `Result`):

| Type | Contract |
|---|---|
| `Waitable` | Intrusive, `Arci`-counted. `state: atomic<u32>` (pending count or flag), `waiters: WakeList`. `signal()` moves all waiters to their lane's ready queue; `complete()` closes the list with a sentinel so late `await` returns inline. Never blocks. |
| `WakeList` | Lock-free intrusive push, single drain by the completer. Node = `{ task: Arci<Task>, lane, generation }`. Generation tag defends against recycled nodes. |
| `await(ref<Waitable>)` | From a fiber: park current fiber on the list, switch out. From a plain thread: `atomic::wait`. The thread-or-fiber check is real (today hard-coded `false`). |
| `JoinCounter : Waitable` | Pending count initialised to `N + 1`; creator drops the extra after registering children (creator guard). `when_all` is a join counter; `when_any` is exactly-once CAS on a shared slot. |
| `Task` | Owns its fiber while suspended, its lane, priority, `Opt<ptr<Span>>`, cancellation token. Referenced by `Arci`, never raw. |
| `FiberContext` | Lives in the fiber control block: `id`, `current task`, `current span`, `allocator scope`. Accessed through `fiber::self::context()`, never `thread_local`. |
| `AffineThread` | `post(Request) -> Arci<Waitable>`; owns one OS thread, an MPSC inbox and a FIFO completion queue. Completion only calls `Waitable::signal`. |
| `StageDecl` | `{ name, reads: span<TypeId>, writes: span<TypeId>, lane, after: span<StageId> }`. `TaskGraph::build(span<StageDecl>) -> Result<Graph, Diagnostic>`; diagnostic on a cycle or a write-write conflict without `after`. Rebuilt only when registrations change. |
| `Lane` | Three queues, FIFO per lane, policy seam `LanePolicy` so an EEVDF-style policy can replace FIFO for Background later. |
| `DeterministicMode` | Config flag: fixed worker count, fixed parallel-for partitioning, reductions ordered by task id, waitable completions delivered in recorded order (S59 feeds the order). |
| `Heliogrim/Async` | `Future`, `Await`, `AwaitSignal`, `Yield` keep their names; bodies route through `await`. One deprecation cycle for signature changes. |
| `FiberMutex`, `FiberSharedMutex` | Built on `Waitable`; a parked fiber never blocks its worker. The shared mutex is writer-preferring with a bounded reader admission so neither side starves (decision Q02.2). |

Placement: `Engine.Scheduler/Waitable.{hpp,cpp}`, `Engine.Scheduler/Fiber/Context.hpp`, `Engine.Scheduler/Affine/AffineThread.{hpp,cpp}`, `Engine.Scheduler.Graph/{StageDecl,TaskGraph}.{hpp,cpp}`. Tests in `Engine.Scheduler.Test` (re-enable the fenced barrier tests on the new API) and `Engine.Scheduler.Graph.Test`.

Rules that come with it: `thread_local` is banned across suspension points (debug assert compares thread ids across `await`; clang-tidy check later under S63). No fiber blocks a worker; `waitOnAtomic` inside a task is a bug once W02.1 lands.

## Work chunks

### W02.0 Measure the scheduler primitives · explore · ready

- **Goal**: run the exploration's five experiments on this machine so W02.1 and W02.3 design on numbers.
- **Inputs**: exploration section 7; `Engine.Scheduler/Fiber`, `Worker::handle`, `default_fiber_stack_size()`.
- **Output**: a results section appended to the exploration (hardware stated): fiber switch cost (Win32 vs. asm sketch), `atomic::wait` park/wake, coroutine resume, exception and `thread_local` after migration, TLS address caching across `co_await` on clang-cl 22, polling vs. wake-list throughput for N suspended tasks, real stack commit and guard-page behaviour at 4 KB.
- **Done when**: each of the five experiments has a number or a "could not run" with the reason; the stack-size question (Q02.3) is answered by measurement, including the memory held by N live fibers so the design can cap the fiber pool with a budget diagnostic instead of growing without bound.
- **Questions**: Q02.3.

### W02.1 Waitable, wake lists and `Arci` split count · design · done 2026-11-08

- **Goal**: design the waitable contract and the lifetime model, including #77; the fiber sync primitives (`FiberMutex`, `FiberSharedMutex` without starvation) and the cancellation token belong to the same contract.
- **Inputs**: this page's code design, exploration sections 2 and 3.3, #77, `Engine.Async` `Future`/`Promise`, `SpinLock` ownership bug (test notes).
- **Output**: [Scheduler waitables design](../../architecture/scheduler-waitable-design.md) (draft, builder-checked); plan `docs/superpowers/plans/2026-11-08-scheduler-waitables.md` in the engine checkout, 14 tasks. Deviations from the code design above, with reasons in the page: park node embedded in the fiber instead of `Arci<Task>` wake nodes; one spin-guarded park queue instead of a lock-free wake list (lock-free deferred behind W02.0 experiment 5); `when_any`, timed waits and generation tags out of scope. Found on the way: #77 landed on master 2026-11-01 and the `SpinLock` ownership bug is already fixed, so both drop out of W02.2.
- **Done when**: the design names every call site class (yield, await, waitOnAtomic, Future::wait) and its replacement; the plan has one task per migration group with a test.
- **Questions**: Q02.1, Q02.2 (both decided).

### W02.2 Implement waitables and port `Engine.Async` · execute · done 2026-11-09 (branch `feat/scheduler-waitables`, unmerged)

- **Result**: 23 plan tasks (14 waitables, 9 promise/future, plus the thread-safety annotations) on 38 commits off master `29f62ce6`, each task reviewed by a fresh reviewer, final whole-branch review "mergeable after one must-fix", which landed. Every test executable is green (scheduler 36, async 56, accel 465, Heliogrim 68, editor action 14, resource 8, pedantic 9, GFX 9, common 277); the editor builds and starts. Two commits await the owner's GPG unlock; the PR is the owner's call. Contracts added during implementation are recorded in the design's section 10a. Owner follow-ups from the reviews (not blockers): a throwing editor action now sets the signal but reports a success-shaped result; `Engine.Accel.Lang` links `Engine.Async` (layering debt vs #157); unbaselined Vulkan validation output on editor stdout; pre-existing `WindowManager` invalid-renderer use-after-move.

- **Goal**: run the W02.1 plan: `ParkNode`/`ParkQueue`, `Signal`, `JoinCounter`, the real thread-or-fiber check, `FiberMutex`, `FiberSharedMutex` (#157), cancellation token, migration of all wait call sites. `SpinLock` fix and #77 are already on master. The `Future`/`Promise` part is the [promise and future rework](../../architecture/promise-future-design.md) (owner request 2026-11-08: no promise-as-task, no `std::function`/`shared_ptr`, task-scheduled type-safe chaining, `Broken` marker, `Send` constraint); its plan `docs/superpowers/plans/2026-11-08-promise-future.md` interleaves with the waitables plan as stated in both files.
- **Done when**: no worker stalls in the 1,000-suspended-task test; `Heliogrim/Async` behaviour unchanged for callers; `waitOnAtomic`, `FiberAwaitable` and the `UnfairSpinLock` users outside the scheduler queue are gone. The fenced barrier tests move to W02.4 (they need the stage API).

### W02.3 Affine thread seam · design+plan+execute · done 2026-11-09 (branch `feat/affine-threads`, 5 signed commits on top of PR #159, unpushed)

- **Goal**: one `AffineThread` abstraction for IO, Win32 pump, audio device, the streaming transfer queue, sockets. Graphics submission is not affine (Q02.4); the design states the per-queue ownership rule instead.
- **Inputs**: DirectStorage completion model (verified), audio runtime design thread section, `Engine.IO.Dispatcher` stub, `Support.Input.Win32` pump.
- **Output**: section in the waitable design or its own `affine-thread-design.md`; plan with the IO dispatcher as first client (handed to S03's W03.2).
- **Questions**: Q02.4 (answered, see decisions).
- **Result**: [Affine threads design](../../architecture/affine-thread-design.md) (builder-checked, inputs re-checked against the engine source); plan `docs/superpowers/plans/2026-11-09-affine-threads.md` in the engine checkout, 6 tasks on `feat/affine-threads` (affine flag, `AffineThread` core, a spike on message-window draining under SDL and modal loops, the platform thread migration, the shutdown order fix, an IOCP `IoThread` skeleton). Decided in the conversation: completion is direct (`Signal::set`), real-time threads hand over through lock-free queues; no inbox bound, since parking producers only moves the queue (pressure relief belongs to W03.3's request path); one STA platform thread drained through a message-only window so `DoDragDrop` and dialogs keep draining. Found on the way: the platform thread outlives the scheduler at shutdown in both engines, and two posters dropped their work silently when the queue was full. The storage access pattern settled here (header, index, archive batches, windowed fallback) is handed to W03.3.
- **Executed** (same day, subagent-driven, owner away): all six plan tasks on `feat/affine-threads`, each reviewed, whole-branch review "mergeable". The spike ran as an automated harness: posted-message draining works inside a message box, the window-move loop and SDL's own pump; `DoDragDrop` only wakes on input, so the waker nudges the drag with a mouse move. Editor idle CPU 56.8 s → 27.0 s per 30 s. Suites: Scheduler 38, Async 67, Heliogrim 68, Editor Action 14, IO Dispatcher 4. Still to see with real input: a drag from the editor, a window created during a drag, live resize, the import dialog. Contracts in the design's section 14a.

### W02.4 Task graph builder and stage migration · design · ready (W02.2 done)

- **Goal**: `StageDecl` with read and write sets, builder, cycle diagnostics; migrate `CompositePipeline` stages; fit the archetype dispatch's stage model.
- **Inputs**: actor archetypes design (dispatch and stage sections), `Engine.Core.Schedule`, `Engine.ACS.Schedule`, `Engine.GFX.Schedule`, `Engine.Physics.Schedule`.
- **Output**: `architecture/task-graph-design.md`, plan.
- **Done when**: the design lists every existing pipeline stage with its read and write sets.

### W02.5 Implement task graph and lanes · execute · after W02.4

- **Done when**: physics, animation placeholder and scene-mirror stages run in parallel where sets allow with the same state hash as serial; lanes exist with the policy seam; switch cost and stack numbers from W02.0 recorded in the system page.

### W02.6 Deterministic mode and state-hash harness · design+plan · after W02.5

- **Goal**: config switch, fixed partitioning, ordered reductions, recorded completion order; the hash harness S59 and S61 reuse.
- **Output**: design section plus plan; S59 owns record and replay.
- **Done when**: identical hashes across 1, 4 and 16 workers on a scene fixture (needs S58 null device or a GPU-free fixture).

### W02.7 Coroutine bridge · explore · after W02.2, W02.0

- **Goal**: decide candidate A or B with the TLS audit done; prototype a `co_await`-able adapter on `Waitable`.
- **Output**: exploration section update with the decision proposal and an ADR draft.
- **Questions**: Q02.5, Q02.6.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q02.1 | Cancellation token per task with cooperative checks. |
| Q02.2 | Keep the global per-priority FIFO and fix waiting first. FIFO is safe because of the ready checks and re-scheduling; a better queue algorithm is measured only after the full fiber feature set is designed and available: yielding, coroutine adoption, awaiting, future and promise, fiber sync primitives including a shared-read exclusive-write mutex without starvation, dependency handling through the task graph. |
| Q02.3 | Measure (W02.0). Whatever the stack size, the number of live fibers must be bounded so fibers cannot eat the memory budget. |
| Q02.5 | All coroutines run on fibers. |
| Q02.6 | `std::execution` vocabulary does not matter for the public API now. |
| Q02.4 | No single submit thread. Multi-threaded submission was a reason for choosing Vulkan and stays a capability. Rule: each `VkQueue` has one owner at a time (external synchronisation per queue, never a global submit lock); distinct queues submit concurrently from different threads or fibers. Graphics and present submit from the frame's submit stage on whichever fiber runs it; the transfer queue for streaming uploads is owned by an `AffineThread` fed by storage completions. S14 may later split graphics submission across queues. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q02.1 | Cancellation: token per task with cooperative checks, or no cancellation in v2? | W02.1 | Token with cooperative checks; errors propagate through the join counter as the first `Diagnostic` |
| Q02.2 | Keep the global per-priority FIFO (fix waiting only) or move to per-worker queues with stealing in the same step? | W02.1 | Fix waiting first; queues in W02.5 behind a measurement |
| Q02.3 | Intended fiber stack size: is 4 KB commit with 1 MB reserve the intent, and is stack depth bounded by policy? | W02.0 result interpretation | Measure; set commit to 64 KB if guard-page growth proves unreliable |
| Q02.4 | Is Vulkan queue submit an affine service, or does it stay on the frame's last stage? | W02.3 | Affine service for presentation and transfer queues; graphics submit stays on the frame stage until S14 |
| Q02.5 | Do all coroutines run on fibers, or may some run on plain worker threads? | W02.7 | All on fibers (rule from the exploration), revisit with P2300 outcome |
| Q02.6 | Does `std::execution` vocabulary matter for the public API now? | W02.7 | No; borrow concepts, no dependency |
