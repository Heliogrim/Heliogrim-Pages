# Fiber Scheduler Iteration (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

**Origin**: owner request on 2026-11-04 after the scripting pages. Three goals: (1) keep stackful `yield`/`await` callable from any function, (2) add standard `co_await`/`co_yield`/`co_return` on top of the same fibers, (3) fix dependency handling in the work sets. EEVDF was raised earlier as a scheduling idea. Checked against the source and a first research pass (sections 0 and 3). Items marked *unverified* have no primary source yet.

## 0. Current State in Engine (checked 2026-11-04)

- **Fiber**: `Fiber{handle, parent, task, awaiter}` over Win32 fibers (`CreateFiber`, `SwitchToFiber`). `self::yield()` and `self::await()` find the fiber through `GetFiberData()`, so any function at any depth can suspend without a coroutine signature. A POSIX `ucontext` branch exists but `self::*` is `todo_panic` there.
- **Awaitable** (`FiberAwaitable`): either a pointer to a `std::atomic_flag` or a polled `bool()` member call. No identity, no metadata, no wait list.
- **Worker loop** (`Worker::handle`): pops a task, takes its fiber (or one from `FiberPool`), checks `awaiter.ready()`, switches in. If the task is still suspended it is pushed back into the queue. A waiting task is therefore **polled on every pop**; nothing is woken. When idle the loop spins (the idle yield is commented out).
- **Migration**: a suspended fiber is resumed by whichever worker pops its task. Fibers already move between threads, so TLS hazards apply today.
- **Blocking helpers**: `waitOnAtomic` / `waitUntilAtomic` have the "thread or fiber" check hard-coded to `false`, so inside a task they block the worker thread with `atomic::wait`. `Engine.Async` `Future`/`Promise` block on `std::condition_variable`. Both stall a worker.
- **Work sets**: `Schedule` holds one FIFO per priority (`eCritical`, `eHigher`, `eNormal`, `eLower`, `eIO`) behind an `UnfairSpinLock`. No per-worker queue and no stealing. `Schedule::tick` moves tasks upward between priorities (aging). A worker pops from its own mask level downward.
- **Dependencies**: none at task level. No counter, no `when_all`, no continuation list. Dependencies exist only between pipeline stages (`CompositePipeline`, `requiredGeneration`, with a `TODO: increment generations`).
- **Stack size**: `default_fiber_stack_size()` returns 4096 on MSVC. Intended as the commit size passed to `CreateFiber`; reserve size is the default (1 MB per Microsoft docs). Not verified that this is intended.
- **C++ coroutines**: not used anywhere in `src`.
- **Usage**: about 77 call sites of yield/await/wait helpers across 30 files (engine, editor, storage, public `Heliogrim/Async`).

## 1. Direction (Goals)

1. **Keep stackful suspension.** `yield()` / `await(x)` from deep call stacks stays the core feature. It is the property coroutines cannot give without function-coloring every caller.
2. **Add standard coroutines** as a second way to suspend, interoperating with fibers in both directions.
3. **Replace polling with waiting on events.** A suspended unit parks on a waitable and is woken by the completer.
4. **Dependencies as first-class scheduler concepts**, not only between stages.
5. **Scheduling policy** (strict lanes, stealing, maybe vtime for background) decided on measurements.

## 2. Ideas Carried Forward

- **One waitable abstraction** (event, counter, completion) that both fibers and coroutine awaiters park on. It carries an identity, so the scheduler and profiler can show "X waits on Y". This also is the "yield with metadata" idea from the [scripting runtime](scripting-runtime-exploration.md) page.
- **Counter with continuation list** (Naughty Dog style): an intrusive node with an atomic pending count and a lock-free list of waiters. The last decrement releases the waiters. Completion closes the list with a sentinel so late waiters run inline.
- **Creator guard**: initialize a join counter to N+1 and drop the extra one after registering all children. Avoids completing before registration is done.
- **External completion as an event task** (IO, GPU fence): the completer triggers it; no thread sits blocked in a worker.
- **Ref-counted or generation-tagged nodes** for lifetime, so stale waiters cannot touch a recycled node.
- **Make the thread-versus-fiber check real** in `waitOnAtomic` and friends, and route `Future::wait` through the same park path inside tasks.
- **Pin option** for rare waits that must resume on the same thread (FiberTaskingLib offers this for `WaitGroup::Wait` and fiber mutexes).

## 3. Findings From Research

### 3.1 Coroutines next to fibers

| Claim | Verdict | Evidence |
|---|---|---|
| `std::execution` (P2300) and `std::execution::task` (P3552) are in the C++26 draft | Confirmed on cppreference (self-described incomplete) | [cppreference C++26](https://en.cppreference.com/w/cpp/26) |
| The failed DIS ballot affects `std::execution` | Only by sharing the draft | Failure attributed to Contracts; [P4388R0](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2026/p4388r0.pdf) concerns Contracts only. Tally reported 12 of 20 yes ([train-it](https://train-it.eu/blog/cpp26-contracts-the-ballot-result/)). Outcome of the 16-21 Nov meeting unknown. |
| A shipping standard library has senders | No (cppreference columns empty; [STL #4768](https://github.com/microsoft/STL/issues/4768) lists P2300R10 unimplemented, possibly stale) | libstdc++ and libc++ status unverified |
| stdexec is usable on our toolchain | Partly | [stdexec](https://github.com/NVIDIA/stdexec) experimental; MSVC 14.43+ and Clang 16+ listed; clang-cl not stated. [beman.execution](https://github.com/bemanproject/execution) implements P2300R10, not production-ready. |
| Compilers can cache a TLS address across `co_await` | Confirmed as a bug class | [LLVM #47179](https://github.com/llvm/llvm-project/issues/47179), [#57260](https://github.com/llvm/llvm-project/issues/57260), [#111257](https://github.com/llvm/llvm-project/issues/111257). Fix status in clang 22.1.3 unverified. |
| Fibers have the same TLS hazard | Confirmed | [P1364R0](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1364r0.pdf) 2.3; MSVC `/GT` fiber-safe TLS existed. |
| Win32 fiber switch is slower than an asm switch | Indicative only | [Boost.Context perf](https://www.boost.org/doc/libs/release/libs/context/doc/html/context/performance.html): fcontext 9 ns, Windows fiber 49 ns, on old Linux Xeon hardware (platform of the fiber row ambiguous). Measure locally. |
| Fibers are a bad idea per the standards committee | One-sided | P1364R0 "DO NOT USE FIBERS" (Nishanov, 2018) is advocacy by a coroutine author; responses exist ([P1520R0](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1520r0.pdf), unreadable in this pass). Its TLS argument stands. |
| P3552 tasks stay on a scheduler | Confirmed | `affine_on` reschedules the task onto its start scheduler; TLS cannot carry context, the environment does ([P3552R3](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2025/p3552r3.html)). |

Microsoft docs ([Fibers](https://learn.microsoft.com/en-us/windows/win32/procthread/fibers), [CreateFiberEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createfiberex)): TLS belongs to the thread, FLS to the fiber; `DeleteFiber` on the running fiber exits the thread; default reserve 1 MB; `FIBER_FLAG_FLOAT_SWITCH` documented for x86 only. **Not verified**: SEH and C++ exception state across switches, guard-page behavior of fibers, coroutine frame elision (`coro_await_elidable`), Folly/Seastar/UE/oneTBB interop designs.

### 3.2 Scheduling policy (EEVDF)

- **Definition**: lag, request, virtual eligible time and deadline; pick the eligible request with the earliest virtual deadline ([Stoica and Abdel-Wahab, TR-95-22](https://people.eecs.berkeley.edu/~istoica/papers/eevdf-tr-95.pdf)). Lag bound `-r_max < lag < max(r_max, q)` was read from extracted text only.
- **Linux**: eligible means lag >= 0; slice acts as latency-nice; lag decays on sleep through deferred dequeue ([kernel doc](https://docs.kernel.org/scheduler/sched-eevdf.html), [LWN](https://lwn.net/Articles/925371/)). Release history 6.7 to 6.17 not verified.
- **User space**: Skyloft (SOSP'24) implements EEVDF in a user-space framework and beats its CFS on schbench, but with timer-interrupt preemption on a tuned Sapphire Rapids server ([paper](https://madsys.cs.tsinghua.edu.cn/publication/skyloft-a-general-high-efficient-scheduling-framework-in-user-space/SOSP24-Jia.pdf)). Not transferable to a Windows desktop or a frame loop.
- **Game loops**: no study found for EEVDF in frame scheduling. A game-job patent text argues EDF fits poorly because job order varies per frame (weak source).
- **Assessment (inference)**: our tasks are cooperative, so the slice becomes an estimated run length and the lag bound degrades to the longest run-to-yield. Frame work is deadline and critical-path driven, not share driven; strict priority lanes plus dependency counters plus stealing already express that. EEVDF-style vtime could help the background lane (IO decode, shader compile, import) so one stream cannot starve the others. Verdict: **overkill for the frame lane, plausible for background, only after a measured starvation problem.**

### 3.3 Dependencies and waiting

- **Unreal Tasks** ([docs](https://dev.epicgames.com/documentation/en-us/unreal-engine/tasks-systems-in-unreal-engine)): prerequisites gate start; nested tasks gate completion without blocking a worker; pipes serialize; `FTaskEvent` is a body-less trigger; handles are ref-counted. Busy-waiting (running unrelated tasks while waiting) deprecated in UE 5.5 for spin, circular waits, stutter and stack growth, replaced by oversubscription.
- **Taskflow** ([conditional tasking](https://taskflow.github.io/taskflow/ConditionalTasking.html)): atomic join counter per task; cycles only through weak edges; a task reachable by strong and weak edges can run concurrently with itself (undefined behavior); a strong back-edge hangs silently.
- **oneTBB** ([spec](https://oneapi-spec.uxlfoundation.org/specifications/oneapi/v1.3-rev-1/elements/onetbb/source/task_scheduler)): a waiting thread may run unrelated tasks; avoid long blocking; producer-consumer patterns unsafe. Resumable tasks can resume on another thread (a deadlock report exists, issue #1822, unresolved in what was read).
- **Practice (partly unverified)**: park the continuation, do not help-steal while waiting; detect cycles in debug and add a watchdog dump; counters with `N+1` creator guard; `when_any` via exactly-once CAS; cancellation token with error propagation (least covered); boost the prerequisite on priority inversion; generation tags against ABA.

## 4. Problems to Resolve Before Design

- **Polling cost and fairness.** Every pop re-checks every suspended task; many waiters make the queue churn. Replacing it with wake lists changes the queue contract (a parked task is not in the queue).
- **Fiber stack overflow behavior.** A 4 KB commit size with default reserve relies on guard-page growth; deep call stacks and exceptions are unverified on `CreateFiber`.
- **TLS audit.** List every `thread_local` and every library using TLS (allocators, `std::error_code`, function statics) reachable from a task. Needed for fibers today and for coroutines tomorrow. Check clang 22.1.3 for TLS address caching across `co_await`.
- **Exceptions across switches.** Unverified on Windows; needs a test that throws inside a fiber after a migration.
- **Resumption affinity.** A coroutine awaiting a fiber event: where does its continuation run? Options: the completer's thread (stack depth risk), a worker queue (cost), or the scheduler of the task (P3552 style).
- **Stackful inside stackless.** A coroutine body calling `fiber::self::yield()` suspends the whole worker fiber the coroutine is currently resumed on. This is legal only if every coroutine runs on a fiber; decide that rule early.
- **Fiber identity.** `Fiber` has no id or context; storage, profiler spans and script awaiters all want one (see [Exploration rundown](exploration-rundown.md), cross-cutting themes).
- **Lifetime of tasks.** `TaskDelegate` is referenced by raw pointer and the fiber pointer is stored inside it; a wait list needs defined ownership.
- **Public API.** `Heliogrim/Async` exposes `Future`, `Await`, `AwaitSignal`, `Yield`; changes need a compatibility plan.

## 5. Candidate Architectures (Tradeoffs)

- **A. Coroutine task type whose awaiter parks the current fiber.** Smallest change; fiber code untouched; a fiber awaiting a coroutine is easy. The reverse (coroutine awaiting a fiber event) needs a completion hook, and coroutines need a fiber worker to run on.
- **B. Coroutine frames and fibers as schedulable units behind one `Waitable`.** Both kinds enqueue to the same workers and wait on the same counters and events. Closest to the sender/scheduler model, so later mapping to P2300/P3552 stays open. Most design work; coroutines inherit the TLS hazard.
- **C. Replace Win32 fibers with an assembly switch.** Possibly several times cheaper per switch (dated, ambiguous numbers). No help for interop; takes on SEH, unwinding, TEB stack-limit and guard-page handling. Only if profiling shows switch cost matters.

Lean (medium-low confidence): **B, reached through A.** Borrow scheduler, affinity and completion concepts from P2300 without depending on a library. Do the TLS audit either way. Treat C as an optimization behind a profile.

## 6. Proposed Order of Work

1. **Waitable and wake lists**: counter plus continuation list, a real thread-or-fiber check in `waitOnAtomic`, `Future::wait` routed through park. Removes polling and worker stalls. Smallest valuable step; no coroutine needed.
2. **Task dependencies**: prerequisites, join counters, `when_all`, external event tasks, cycle watchdog in debug. Then connect pipeline stages to it.
3. **Fiber identity and context** (shared with storage, scripting, observability).
4. **Coroutine bridge (A)**: a task type awaitable from fibers, with `co_await` on a `Waitable`. Includes the TLS audit and a clang-cl 22 check of caching, exceptions and frame allocation.
5. **Queue structure**: per-worker queues with stealing and priority lanes, measured against the single spin-locked FIFO.
6. **Background-lane vtime** only if starvation shows up.

## 7. First Experiments

1. Microbenchmark on this machine: `SwitchToFiber` round trip, a hand-written asm switch, coroutine resume with symmetric transfer, `atomic::wait` park/wake. Hardware stated in the result.
2. Throw an exception and read a `thread_local` after a fiber migrates between two workers.
3. Compile a minimal coroutine with a TLS read around `co_await` on clang-cl 22.1.3 at `/O2` and inspect for a cached TLS address.
4. Prototype the `Waitable` with one consumer (`Future::wait`) and count worker stalls before and after.
5. Throughput test of N suspended tasks with the polling worker versus wake lists.

## 8. Open Questions

- Do all coroutines run on fibers, or are some plain worker-thread coroutines.
- Where a coroutine continuation resumes after a fiber event completes.
- Is stack depth in fibers bounded by policy, and what is the real stack size intended.
- Per-worker queues and stealing, or keep the global lane structure and fix only waiting.
- Cancellation model and error propagation across dependencies.
- Whether the POSIX branch matters at all (it is `todo_panic`).
- Whether `std::execution` becomes the long-term vocabulary after the 16-21 Nov WG21 outcome.

## 9. Not Researched Yet

Folly fibers/coro interop, Seastar, cppcoro, libunifex; SEH and exception state across `SwitchToFiber`; HALO and `coro_await_elidable` on clang-cl; `FlsAlloc` details; the Naughty Dog talk in full; Linux EEVDF changes after 6.6; cancellation designs; modern measurements of coroutine resume versus fiber switch.

## 10. Related

- [Scripting runtime](scripting-runtime-exploration.md): C# awaiters map onto the same waitable.
- [Scripting by native code generation](scripting-native-codegen-exploration.md): suspended work across a module reload.
- [Actor system](actor-system.md): tick stages.
- [Storage engine](storage-exploration.md): async paths that resume on I/O completion.
- [Observability](observability-exploration.md): fiber-aware spans.
- [Exploration rundown](exploration-rundown.md)
