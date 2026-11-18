# Scheduler Lanes and Priority (Exploration)

**Status**: exploration. The direction in section 3 was agreed with the owner on 2026-11-13 (chunk W02.13, closes Q02.8); the numbers in it (caps, T, slice length) are placeholders for the follow-up chunk W02.14 to measure. Accepted parts move to a design page and an ADR.

**Origin**: W02.13 was set up to measure today's ageing (Q02.8). The owner widened it: before the task graph, waits were polled, so jobs had to rotate through the queues to re-check their ready flag, and ageing kept them moving. With waitables (W02.2), the task graph (W02.5) and parked workers (W02.8) the queues hold only runnable work, so the engine can have a real lane policy. Goal set by the owner: the highest-priority work gets the most attention at all times, nothing starves, and the policy adapts from 2 to 3 workers up to 20.

## 1. Current state (checked on `master` `7f33eae5`, 2026-11-13)

- **Sets**: four FIFO work sets, `eCritical`, `eHigher`, `eNormal`, `eLower` (`Engine.Scheduler/Process/Schedule.cpp`). A worker pops from the highest non-empty set (`Schedule::pop`), every worker takes every set (W02.8).
- **Ageing**: `Schedule::tick()` moves every set one step up (`eHigher → eCritical`, `eNormal → eHigher`, `eLower → eNormal`). It runs after every finished stage (`CompositePipeline.cpp:304`), about 15 times per frame, so an `eNormal` task is critical two stage completions after it was queued.
- **Frame stages**: lane from `StageDecl::lane`, mapped by `graph::toMask` (`eCritical → eCritical`, `eNormal → eNormal`, `eBackground → eLower`). 13 of 15 stages are critical (tick timing, input, actor ticks pre and post physics, physics tick and readback, the three scene stages, `ReflowFlow`, render tick, actor housekeeping, the core end stage); the two actor physics callback stages (both stubs) are normal; none are background.
- **Everything else**: `exec`, `delay` and the `Heliogrim/Async` helpers default to `eNormal`; no caller outside the scheduler chooses another set. Nothing pushes `eHigher` or `eLower`; `eHigher` is reached only by ageing, `eLower` stays empty.
- **Fan-out inside a stage**: none today. Physics runs Jolt on `JobSystemSingleThreaded` (`PhysicsTickStage.cpp:35`). A stage that called `exec` for a batch would put its children in `eNormal`, below the critical parent that waits for them.
- **Not on workers**: audio mixes on its own device thread (audio runtime design); platform and IO run on affine threads (W02.3).

What ageing does today is lift every queued task into the critical set within one frame, where it sits ahead of the next frame stage. Under load, background work can therefore delay the frame; at idle (20 parked workers, a frame that is a strict chain) any task gets a worker within the wake latency, whatever its set.

## 2. Requirements (owner, 2026-11-13)

1. The frame is what ships: framerate wins over everything not pulled into the frame.
2. The highest-priority work gets the most attention at all times. No rotation scheme may let all workers pick background at once (no avalanche).
3. Nothing starves, including background, which may stay low priority.
4. Works on 2 to 3 workers (6 or 8 logical threads minus the reserve and the hot threads) as well as on 20.
5. Fan-out and join inside a frame function (a physics batch, an intercepted or replaced physics job system) run at the frame's priority.
6. Under overload, background falls behind; tasks marked background accept generous stalls by definition.

## 3. Direction

### 3.1 Lanes by deadline

| Lane | What runs there | Deadline |
|---|---|---|
| Frame | Task graph stages and everything they spawn or await | This frame |
| Interactive | Work someone waits for that is not the frame: editor actions, an asset the user just opened, module start and stop | Human-noticeable, not frame-bound |
| Background | Bulk work: streaming, imports, shader compiles, saves | Generous; may fall behind |

The four `TaskMask` sets collapse onto three lanes; `eHigher` goes away. The `Lane` enum in `StageDecl` already has these three values.

### 3.2 Inheritance, no promotion into Frame

- A task spawned from a worker inherits its parent's lane. It may be pushed lower explicitly, never higher. A fan-out and join inside a frame stage therefore runs in Frame without the stage naming a lane.
- `exec` without a lane: inherit on a worker; Interactive from a plain thread (my call, today everything defaults to `eNormal`).
- Nothing is promoted by time. `Schedule::tick()` ageing is removed.
- Physics: Jolt takes any `JPH::JobSystem` (`CreateJob`, `CreateBarrier`, `WaitForJobs`, `QueueJob(s)`, `GetMaxConcurrency`, `vendor/jolt/include/Jolt/Core/JobSystem.h`), so an adapter onto the scheduler runs Jolt's jobs as Frame children of the physics stage, waiting on a join counter. A replacement physics engine uses the same seam. Owner: Jolt may be replaced or intercepted; the seam must not assume Jolt.

### 3.3 Wait boost

When a task awaits a waitable whose producer is a queued task in a lower lane, the producer moves to the waiter's lane and ignores that lane's cap. Anything the frame really needs (an asset load a stage awaits) therefore becomes Frame work; nothing else does. This is priority inheritance on await; it needs the waitable to know its producing task, which today it does not (W02.1 design: parking is per fiber, the waitable holds no producer).

### 3.4 Worker allocation

Four rules; together they keep Frame first, stay work-conserving, and bound starvation on any worker count.

1. **Frame first, uncapped.** A free worker takes Frame work whenever any is queued.
2. **Caps only under contention.** While Frame work is queued, the lower lanes are capped by the number of workers currently running them: one shared counter per lane, not a per-worker stride, so workers cannot all reach a "background turn" together (requirement 2). Caps are counts rounded down and may be 0 (on 3 workers both are 0). While Frame is empty, between frames or because the frame is light, every worker takes Interactive and then Background work without a cap. A drained frame therefore hands all spare capacity to the backlog.
3. **Time-based floor.** A lower lane with queued work that has not started a task for T gets the next free worker for one slice, even under contention. Independent of the worker count; takes at most one worker per lane from Frame per T. Placeholder T: one frame (about 16 ms) for Interactive, longer for Background.
4. **Slices.** Interactive and Background tasks yield at step boundaries after about 1 ms of work (cheap on fibers: the task is re-pushed with its lane and the worker checks Frame first). A frame that starts while every worker is busy with lower-lane work waits at most one slice for its first worker. Work that cannot yield (a blocking third-party call) runs on an affine thread, not a worker.

Serial mode (`USE_WORKER_COUNT` 1) keeps rule 1 and the floor; caps are 0.

### 3.5 Overload

When background demand exceeds the time the frame leaves free, no ordering helps; one side gives. Decided: **background falls behind, never the frame**. The schedule exposes queued depth per lane; producers of background work (streaming, imports) throttle against it. The throttling belongs to the producing systems (storage W03.x), not the scheduler. Frame pacing (W02.9) leaves predictable idle windows that the uncapped rule 2 turns into background throughput.

## 4. Alternatives set aside

| Alternative | Why not |
|---|---|
| Keep ageing, tune the rate | Promoted bulk work lands ahead of the next frame stage; violates requirement 1. Ageing was the polling era's way of moving waiting jobs |
| Weighted round-robin per worker (stride counter on each worker) | Workers' turns can align, so all of them pick background at once (requirement 2) |
| Fixed fraction caps (N/4, N/8) | Round to 0 or waste workers on small machines; idle the backlog while the frame is drained |
| EEVDF-style virtual time across lanes | Gives Frame a share, not priority. Stays possible inside a lane through the `LanePolicy` seam (code design), e.g. for fairness between background producers |
| Preemption of lower-lane tasks | Fibers cannot be preempted; cooperative slices give the same bound with a yield per step |

## 5. Open for the follow-up (W02.14)

- **Measure before and after**: frame time with and without a background flood, on 3 workers and on the auto count; how far background falls behind; the frame-start delay at slice boundaries.
- **Numbers**: the caps under contention, T per lane, the slice length.
- **Wait boost mechanics**: how a waitable names its producer; boosting a task already running (it keeps its worker, so only queued producers move); chains of awaits.
- **Slice discipline**: how a long task marks its step boundaries (`yield` with a budget check), and how a violation is noticed (a debug counter of slices over budget).
- **Model**: the allocation rules change the pop path that `Schedule.tla` checks; the model gains lanes, the per-lane counters and the floor.
- **Migration**: `TaskMask` to lanes for every `exec` caller, `graph::toMask` replaced, `Schedule::tick` and its call removed.

## 6. Prior art (2026-11-18, for the design)

Research run for [the design](lane-policy-design.md) before execution, by three read-only research agents. **Read** = the primary source was fetched and read; **recalled** = stated from memory, not verified, and not to be cited as evidence. PDFs could not be read by the fetch tool, so the papers and the GDC slide decks are all recalled. No severe finding; the changes it caused are in the design's section 14.

### 6.1 Priority escalation on await

| System | What it does | Source |
|---|---|---|
| Swift concurrency | Awaiting a task escalates it and its children, permanently; never lowered. Automatic only for structured tasks; continuations are not escalated ("we don't know who will resume the continuation"). A queued task is not searched for: the runtime enqueues a second "stealer" job at the higher priority and the task's status word decides which copy runs. A running task gets a thread override that ends when it suspends. A task that publishes a new dependency escalates it at publish time with its current priority. Escalation returns early when the stored priority is already high enough | SE-0304 (2021), SE-0462 (2025), `stdlib/public/Concurrency/TaskStatus.cpp` (read, files truncated at about 100k characters) |
| libdispatch | Override QoS is a maximum in the queue state; a new override on an enqueued queue "redrives" a new stealer; `dispatch_block_wait` boosts the queue or overrides the running thread | `swift-corelibs-libdispatch/src/queue.c` (read, first 100k of 240k characters) |
| XNU turnstiles | Inheritance is a chain walk that stops early when nothing changed and is capped by `turnstile_max_hop`; a running owner ends the walk | `osfmk/kern/turnstile.c` (read, truncated) |
| Linux rt-mutex | Chain walk with at most two locks held and a maximum depth; boosts and de-boosts (on unlock, on a waiter leaving) | kernel.org `locking/rt-mutex-design` (read) |
| Tokio, Seastar, Unreal Tasks | No priority inheritance. Seastar scheduling groups are share-based; Unreal 5.5 replaced busy-waiting by oversubscription (standby threads woken during a wait) | Tokio scheduler article 2019, Seastar tutorial, Epic Tasks System page (read) |
| Sha, Rajkumar, Lehoczky 1990; Naughty Dog GDC 2015; Unreal task retraction; proxy execution | Not obtained | recalled or not checked |

What it means here: raising on await, following the chain, never lowering, stopping at a value nobody produces, and applying the raise to a running producer at its next scheduling point all match Swift and the kernels. Two things the draft lacked are standard: the walk ends when a hop changes nothing (which also makes a cycle terminate) and has a depth cap; a dependency is escalated when it is linked. One thing differs: Swift and libdispatch enqueue a duplicate instead of moving the queued entry. The engine's tasks delete themselves after running and are not reference counted, so a stale duplicate would dangle; the design keeps the move and measures its scan.

### 6.2 Keeping capacity for high-priority work

| System | What it does | Source |
|---|---|---|
| Go runtime | No priorities. `sysmon` preempts a goroutine after 10 ms judged by an unchanged `schedtick`, and retakes a processor stuck in a syscall after two observations when work is queued; signals are observed non-progress and queue state | `runtime/proc.go` (read) |
| .NET thread pool | A gate thread every 500 ms injects one thread when work is outstanding and nothing was dequeued for a threshold; signal is dequeue delay plus CPU use | `PortableThreadPool.GateThread.cs` (read) |
| Java ForkJoinPool | Compensation threads for declared blocking; `minimumRunnable` defaults to 1 "to ensure liveness" | SE 21 javadoc (read) |
| Windows thread pool | Callers mark long waits so the pool adds threads; the advice for priority isolation is a separate pool | Microsoft Learn (read) |
| Unreal Tasks | Five priorities, oversubscription during waits. The foreground and background worker split (background workers take only background priorities) is recalled, not read | Epic Tasks System page (read for the first sentence only) |
| Unity jobs | Worker count setting; no priorities or reservation on the page read | Unity scripting reference (read) |
| Shenango NSDI 2019, Caladan OSDI 2020, Arachne OSDI 2018, Concord SOSP 2023 | Core allocation for latency-critical work from a queueing-delay signal with short hysteresis; compiler-inserted cooperative preemption | recalled, PDFs unreadable |

What it means here: holding capacity back for the urgent class is established (a minimum runnable count, separate pools, and, recalled, Unreal's worker split). No source that was read sizes it by a count of runnable tasks; the ones that adapt use a delay or non-progress signal, raise in steps and damp the way down. The owner's metric (time until a fan-out is picked up) is a delay as well. The design therefore adds a wait-time trigger beside the peak count, and reports the Frame queue wait.

### 6.3 Wake-up, slices, tasks that do not yield

| System | What it does | Source |
|---|---|---|
| Tokio | Notifies on push only when no worker is "searching"; a woken searcher that finds work notifies the next; at most half the workers search. Chosen against a "thundering herd". Cooperative budget of 128 operations per task per tick, a counter, no clock; blocking detection with thread injection was rejected for "stuttering" | scheduler article 2019, coop article 2020, docs (read) |
| Go | `wakep` wakes one when a processor is idle and none is spinning; the last spinner to find work wakes a replacement | `runtime/proc.go` (read) |
| Rayon | A push of k jobs wakes up to `min(k, sleepers)` directly; idle workers yield 32 rounds before sleeping | `rayon-core/src/sleep/README.md`, `mod.rs` (read) |
| Seastar | `need_preempt()` is two relaxed loads against a flag set by a timer, no clock read; a stall detector reports "Reactor stalled for N ms" with a backtrace and adds no capacity. The 500 µs quota and 25 ms threshold are recalled | `preempt.hh`, `reactor.cc` (read) |
| BWoS OSDI 2023, any measurement of chained against direct wakes | Not obtained | not checked |

What it means here: a wake-one chain is what Tokio and Go do, but their hops run through spinning workers; the engine's hops are kernel parks of 5 to 10 µs each, so 8 children reach their last worker after up to 7 hops. Rayon wakes directly. Nothing read measures the difference, so the design makes the direct wake a switch and measures it. A 1 ms slice lies between Seastar's quota and Go's 10 ms. The runtimes read use a flag or a counter for the yield check, not a clock; at one call per work step the clock read is kept, and a timer-set flag is the known replacement if it shows. Reporting a stalled task while it is stuck (Seastar) is better than counting it afterwards; that is left as a follow-up.
