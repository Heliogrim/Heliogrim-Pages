# Concurrency: Fibers, Task Graph and Thread Bridges

**Systems**: S02 (also #77 Arci) · **Track** A · **Milestone** M1
**Status**: <span class="hg-status summary">plan</span>. Research from [runtime](../sources/research-runtime.md) section 1 (EEVDF kernel docs and DirectStorage completion model verified; Gyrling, Chase-Lev and P1364 unverified). The [fiber scheduler exploration](../../architecture/fiber-scheduler-exploration.md) records the current scheduler's gaps and the coroutine bridge options.

## Target

Game loop and engine systems run as tasks with declared dependencies on a fiber scheduler. Blocking work lives on dedicated threads (storage IO, platform message pump, network sockets, audio device callback, GPU fence waits) and completes into the scheduler through waitables. No fiber ever blocks a worker. A deterministic mode produces identical results regardless of worker count.

## Current state (checked 2026-11-07)

- `Engine.Scheduler` (52 files): `CompScheduler`, workers masked Critical, IO and All, `FiberPool`, `Fiber`, `FiberLaunchPad`, `Awaitable` as a bare atomic flag, tick stages via `CompositePipeline` and `PipelineStage`. Waiting is polled; `waitOnAtomic` blocks the worker; no task dependencies; no fiber identity or context field.
- `Engine.Async`: promises and futures, SPSC ring buffer, spin lock (ownership bug noted in the test notes).
- `Engine.IO.Dispatcher`: 76 lines, a stub.
- Arci intrusive refcount uses a drain-wait protocol; #77 proposes a split-count protocol; this matters because waitables and wake lists hold references across threads.
- Scheduler tests: 14 live, the barrier-based runtime tests are fenced out with a stale API.

## Research summary

- Fiber job systems (Naughty Dog GDC 2015, unverified): one worker per core, jobs wait on counters by switching fibers; the cost is per-fiber stack memory, no TLS safety, and tooling blindness.
- Work stealing (Blumofe-Leiserson 1999, Chase-Lev 2005, Lê et al. PPoPP 2013 for weak memory orderings; unverified).
- EEVDF (verified, Linux 6.6 docs): eligibility by lag, earliest virtual deadline, slice requests; a usable fairness model for background streaming versus frame work.
- Fibers versus C++20 coroutines (P1364 metadata only): coroutines are stackless and composable with executors; fibers suspend from nested calls and need an assembly switch; both can share one worker pool.
- Thread-affinity bridging: DirectStorage's verified model (status array, fence or event, FIFO completion per queue) is the shape of a bridge: a fiber posts a request to an affine thread's queue and parks on a waitable; the completion resumes it by enqueuing it back.
- Deterministic scheduling needs fixed partitioning, ordered reductions, no float atomics, stable sorts.

## Guidance

### Design

- **Waitable**: `{ state, wake list }`; `await(w)` parks the current fiber and yields; `signal(w)` moves waiters to the ready queue of their lane. Timers, fences, IO completions, task completion and `Promise` all become waitables. #77's split-count `Arci` is the reference type for wake-list nodes.
- **Task graph**: a frame is built from stage declarations `{ name, reads, writes, lane, after }`; the builder derives edges from read and write sets (the explicit DAG the archetype design asked for) and schedules by topological order with parallel fan-out. Systems register stages; the graph is rebuilt only when registrations change.
- **Lanes**: Critical (frame), Normal, Background (streaming decode, navmesh builds, DAG builds), with a policy seam so an EEVDF-like lag model can replace FIFO per lane later if starvation is measured.
- **Affine services**: one abstraction `AffineThread { post(request), completion -> waitable }` used by storage IO, the Win32 pump, the audio device, Vulkan submit and network sockets. Nothing else may block.
- **Fiber context**: an identity, the current span (S04), the current task, and an allocator scope live in the fiber control block; `thread_local` is banned across suspension points (lint via a clang-tidy check or a debug assert that compares thread IDs across `await`).
- **Deterministic mode**: fixed worker count, fixed partitioning of parallel-for, reductions ordered by task ID, waitable completions replayed in recorded order (S59).
- **Coroutines**: offer a `co_await`-able adapter on waitables for leaf async (network, IO continuations) once the fiber path is solid; do not build the scheduler on coroutines.

### Order of work

1. Waitable plus wake list with `Arci` split-count; port `Promise`/`Future` and `Awaitable` onto it; fix `SpinLock`.
2. Affine thread with the IO dispatcher as the first client (S03 consumes it).
3. Task graph builder with read and write sets; migrate the tick pipeline stages; re-enable the fenced scheduler tests on the new API.
4. Lanes and priorities; measure fiber switch cost, stack sizes and guard-page cost on clang-cl.
5. Deterministic mode and the state-hash harness.

## Done when

- A fiber awaiting a file read yields the worker; throughput of a 1,000-read test matches the IO thread's capacity.
- A frame with physics, animation and scene-mirror stages runs them in parallel where their read and write sets allow, with the same state hash as serial execution.
- The deterministic mode gives identical hashes across 1, 4 and 16 workers.
- Tracy or the in-editor viewer shows fiber lanes (tooling check).

## Open decisions

- Fiber context location (stack top or control block), shared with S04.
- Whether Vulkan queue submit is an affine service or stays on the frame's last stage.
- Coroutine bridge model A or B from the exploration.
