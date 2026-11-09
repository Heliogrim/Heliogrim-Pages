# Scheduler Waitables, Parking and Fiber Sync Primitives (Design)

**Status**: design, draft 2026-11-08 (work chunk [W02.1](../plan/work/concurrency-fibers.md), issues [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84), [#157](https://github.com/Heliogrim/Heliogrim-Engine/issues/157), [#77](https://github.com/Heliogrim/Heliogrim-Engine/issues/77)). Builds on the [fiber scheduler exploration](fiber-scheduler-exploration.md) and the owner decisions on the [concurrency work page](../plan/work/concurrency-fibers.md#decisions-2026-11-08). The implementation plan lives untracked in the engine checkout (`docs/superpowers/plans/2026-11-08-scheduler-waitables.md`).

Markers: **Decided** = owner decision on the work page. **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

A fiber that waits today is polled: the worker pops it, asks the awaitable whether it is ready, and pushes it back. Code that cannot express a poll blocks the worker thread outright (`waitOnAtomic`, `Future::get`, `std::mutex`). Every battle-plan system that waits on IO, GPU fences, the audio device or the network needs the opposite: a fiber parks on a completion and the completer wakes it, no worker ever blocks, and the primitives work the same from a plain thread.

This design fixes waiting only (**Decided**, Q02.2): the global per-priority FIFO stays, there are no per-worker queues, no lanes and no task graph. Those are W02.3 to W02.6 and depend on the contract defined here.

## 2. State of the inputs (checked 2026-11-08)

| Input | Work page assumed | Found in the engine |
|---|---|---|
| #77 split-count `Arci` | a prerequisite to design | landed on master 2026-11-01 (`5ea82a6d`, `ce8b3db3`), `Arci<const T>` and `View` included; weak-memory verification still open, issue not closed |
| `SpinLock` ownership bug | to be fixed in W02.2 | fixed: `unlock()` resets `_owns` (`Engine.Async/Primitive/SpinLock.hpp`) |
| `Future::wait` blocks workers | a live stall | latent: production code reaches futures only through `hg::await(ptr<await_signal_sub_type>)`, which polls; only `Engine.Async.Test` calls the blocking `get()` |
| 77 call sites in 30 files | | 52 lines in 23 files match the wait helpers; the classes are listed in section 9 |
| `FiberPool` | | grows without bound when empty (`acquireNew`), frees fibers that do not fit back into the ring |
| `Engine.Async` | | links `Engine.Scheduler`; `Engine.Scheduler` links only `Engine.Common` |

Consequence: this chunk does not design `Arci`; it uses it. The "SpinLock fix" in W02.2's goal is already done and drops out.

## 3. Goals

1. `await(w)` from a fiber parks the fiber and costs the worker nothing until `w` completes. From a plain thread it blocks that thread with `atomic::wait`.
2. One completion path for everything: task completion, `Promise`, IO completion, platform callbacks and the editor's action signals all become a `Waitable`.
3. A join counter with the creator guard, so N children can be awaited as one.
4. Fiber-safe mutex and shared mutex with no OS-thread ownership, parking on contention, writer-preferring without starving either side (#157).
5. A cooperative cancellation token reachable from inside a task (**Decided**, Q02.1).
6. Every existing wait call site has a named replacement (section 9).

## 4. Non-goals

- Lanes, lane policy, per-worker queues, work stealing (W02.5, measured first).
- `AffineThread` (W02.3), the task graph (W02.4), deterministic mode (W02.6), the coroutine bridge (W02.7).
- Timed waits and withdrawing a parked waiter (section 6.5 explains why they are excluded and what adding them costs).
- Fiber identity for observability beyond what parking needs. The context slot is reserved as one field (section 7).
- Changing task ownership. `TaskDelegate` stays self-deleting and raw-referenced; nothing in this design holds a task from another thread (section 6.2).
- Lock-free wake lists. Section 6.3 explains why a spin-guarded queue is the first version.

## 5. Anti-goals

- No `thread_local` state that a fiber reads across a suspension point. `fiber::self::current()` reads the fiber's own data, not thread storage.
- No primitive that records an OS thread id as owner (`UnfairSpinLock` stays confined to the scheduler queue, where no suspension occurs).
- No API that forces callers to know whether they run on a fiber. `await`, `FiberMutex::lock` and `JoinCounter::wait` decide internally.
- No polling path left in the worker loop after migration.

## 6. The contract

### 6.1 Terms

- **Waiter**: a fiber or a plain thread that wants to be resumed when something happens.
- **Park**: the waiter stops running and does not occupy a worker (fiber) or spins down into `atomic::wait` (thread).
- **Unpark**: the completer makes the waiter runnable again: the fiber's task goes back into its priority FIFO through `Schedule::push`, or the thread's flag is set and notified.
- **One-shot**: completes once, stays completed; late waiters return inline (`Event`, `JoinCounter`, `Promise` state).
- **Reusable**: a gate that opens and closes repeatedly; a woken waiter must re-check its predicate (`FiberMutex`, `FiberSharedMutex`).

### 6.2 Park node and the wake handshake (**Proposal**)

Every waiter carries exactly one intrusive `ParkNode`:

```cpp
struct ParkNode {
    // eIdle: not waiting (a plain yield or running). eArmed: pushed into a queue, not yet switched out.
    enum class State : u8 { eIdle, eArmed, eParked, eWoken };
    std::atomic<State> state { State::eIdle };
    ParkNode* next = nullptr;
    // Who to resume: a fiber (its task is re-queued) or a thread (flag + notify).
    ptr<fiber::Fiber> fiber = nullptr;     // null for a thread waiter
    std::atomic<u32> threadFlag { 0 };     // used only when fiber == nullptr
};
```

- For a fiber the node is **embedded in the `Fiber` control block**. A fiber awaits one thing at a time, so one node suffices, the memory is pool-owned and stable, and nothing has to be allocated or reference-counted on the wait path. This is why `Task` does not need `Arci`: no list ever points at a task, only at a fiber, and a fiber is never freed while parked (the pool only frees fibers that are released back to it).
- For a thread the node is a `thread_local ParkNode` of that plain thread. Plain threads never migrate, so the thread-local rule in section 5 does not apply, and the node outlives every wait, which lets `unpark` touch it after the waiter has already returned (a stack node would be freed between the completer's `store` and its `notify_one`). Only worker threads are ever converted to fibers (`Worker.cpp:110`), so a null `self::current()` reliably means "plain thread".

The race to close is "woken before actually switched out": a completer must not re-queue a fiber whose stack is still running. The handshake:

1. Fiber side, inside `park()`: set own node to `eArmed`, push it onto the primitive's queue, then `Fiber::yield()` back to the worker.
2. Worker side, when `SwitchToFiber` returns and the task is still attached (that is, the fiber suspended rather than finished): if `node.state.load(relaxed) == eIdle` this was a plain `yield()`, the node is in no queue and nobody can race on it: push the task back into the schedule as today. Otherwise `prev = node.state.exchange(eParked, acq_rel)`. If `prev == eWoken` the completer came first: push the task back into the schedule now. Otherwise do nothing; the fiber is parked.
3. Completer side, in `unpark(node)`: `prev = node.state.exchange(eWoken, acq_rel)`. If `prev == eParked` push the fiber's task into the schedule. If `prev == eArmed` do nothing; step 2 will push it. The completer must read `node.next` **before** calling `unpark`, because a woken fiber may re-park and overwrite `next` at once.
4. When the fiber is popped again and switched in, `park()` returns. It resets the node to `eIdle` before returning (the node is in no queue at that point).

Thread side: `park()` loops `threadFlag.wait(0)` until `unpark` sets it to 1 (release) and `notify_one()`s; `park()` resets the flag to 0 before the next push. Steps 2 and 3 collapse to the flag.

The worker loop therefore **pushes a suspended task back only when it did not park**. `Worker::handle` replaces the "reschedule suspended task" branch with step 2.

Exactly one of the worker (step 2) and the completer (step 3) observes the other's state, because both use a single RMW on the same word. No fiber is ever in a queue and running at the same time, and no wake is lost.

### 6.3 ParkQueue (**Proposal**, shape corrected 2026-11-08 in W02.2)

```cpp
class ParkQueue {              // intrusive FIFO of ParkNode, guarded by an atomic_flag spin lock
    std::atomic_flag _lck;     // Engine.Scheduler cannot include Engine.Async, so not SpinMutex
    ParkNode* _head = nullptr;
    ParkNode* _tail = nullptr;
public:
    void push(ref<ParkNode>);              // O(1), self-locking
    ptr<ParkNode> popOne();                // O(1), FIFO, self-locking
    ptr<ParkNode> takeAll();               // O(1) splice, self-locking; caller walks the list
    bool empty() const;
    // Runs fn under the lock with a Locked view whose push/popOne/takeAll/empty do NOT re-lock,
    // so a primitive can re-check its predicate and push in one critical section.
    template <typename Fn> decltype(auto) locked(Fn&& fn);
};
```

The first draft had `locked` without the view; re-checking and then calling the self-locking `push` inside it would have deadlocked. The review of the implementation caught it.

The lock is `concurrent::SpinMutex` + `SpinLock` (ownerless, header-only), held for a handful of instructions and never across a suspension. Why not the lock-free intrusive stack from the exploration: the one-shot and the reusable primitives need different list semantics (close-with-sentinel versus wake-one in FIFO order), and the reusable case needs a predicate re-check under the same lock to avoid lost wakeups without node withdrawal (section 6.5). One guarded queue serves both and has no ABA surface. W02.0's experiment 5 measures polling against this queue; a lock-free push for the one-shot case is a later optimisation only if that measurement shows the lock on the wait path.

### 6.4 One-shot: `Event` and `JoinCounter`

```cpp
class Event {                          // Waitable, one-shot
    std::atomic<u32> _state { 0 };     // 0 pending, 1 completed
    ParkQueue _waiters;
public:
    bool isSet() const noexcept;       // acquire
    void set() noexcept;               // exactly once; asserts in debug on a second call
    void wait();                       // park until set; inline return if already set
};
```

`set()`: under the queue lock set a `_closed` flag and `takeAll()`; release the lock; **then** `_state.store(1, release)`; then `unpark` each node (reading `next` first). `wait()`: fast path `_state.load(acquire) == 1` returns. Slow path, under the queue lock: if `_closed`, do not push; else push the node. Release the lock; if pushed, park; if not, spin on `_state.load(acquire)` until it is 1 (the setter's store is imminent) and return.

Two invariants come out of this ordering (corrected 2026-11-08 during implementation review, W02.2):

- **No lost wakeup**: `_closed` and the queue change together under the lock, so a waiter either pushes before the drain or sees the closed flag.
- **Destruction safety**: the setter's `_state` store is its last access to the `Event`. A waiter that observed `isSet()` or returned from `wait()` may destroy the object at once; a stack-allocated `JoinCounter` whose creator returns right after `wait()` is therefore safe even while the last child is still inside `set()`. The first draft stored `_state` before draining the queue and had a use-after-free window there. Nodes are waiter-owned, so unparking them after the store touches no event memory.

```cpp
class JoinCounter {                    // Waitable, one-shot, completes when the count reaches zero
    std::atomic<u32> _pending;
    Event _done;
public:
    explicit JoinCounter(u32 children_);  // initialises to children_ + 1 (creator guard)
    void add(u32 n_ = 1) noexcept;        // before the matching children are started
    void done() noexcept;                 // fetch_sub(1, acq_rel); last one calls _done.set()
    void wait();                          // creator: done() for its own guard, then _done.wait()
};
```

The guard (`N + 1`) means the counter cannot reach zero while the creator is still registering children. `wait()` on the creator consumes the guard first.

`when_any` is not part of this chunk (**Proposal**): no call site needs it (section 9) and it is the only pattern that forces a node into several queues at once, which brings back heap nodes and reference counting. It returns with the task graph if a stage needs it.

### 6.5 Reusable: `FiberMutex` and `FiberSharedMutex` (#157)

Placement `Engine.Async/Primitive/FiberMutex.hpp`, `FiberSharedMutex.hpp`. Std-compatible names (`lock`, `try_lock`, `unlock`, `lock_shared`, `try_lock_shared`, `unlock_shared`) so `std::scoped_lock`, `std::unique_lock` and `std::shared_lock` work.

`FiberMutex` word: `std::atomic<u32>` with `eLocked = 1`, `eContended = 2`. Invariant: `eContended` is set exactly when the queue is non-empty, and both only change under the queue lock.

- `lock()`: CAS `w -> w | eLocked` for any `w` without `eLocked` (acquire; the contended bit is preserved, never cleared by an acquirer). On failure spin a bounded number of iterations (**Builder's call**, start at 32 with a pause instruction) retrying. Then the slow path, under the queue lock: re-read `w`; if `eLocked` is clear, CAS `w -> w | eLocked` and return on success; else CAS `w -> w | eContended`. If either CAS fails the word moved: release the queue lock and restart from the top (a `fetch_or` here could set `eContended` on an unlocked word and park forever). On success push own node, release the queue lock, `park()`, then restart from the top.
- `unlock()`: `prev = word.exchange(0, release)`. If `prev & eContended`: take the queue lock, `node = popOne()`; if the queue is still non-empty, `word.fetch_or(eContended)` (a barger may already hold `eLocked`, so a store is wrong); release the queue lock; `unpark(node)`.

This is a parking-lot mutex with a per-object queue instead of a global hash table. A woken waiter competes with bargers and may park again; FIFO wake order bounds how long it loses.

`FiberSharedMutex` word: `std::atomic<u32>` with bit 31 `eWriter`, bit 30 `eWriterWaiting`, bits 0..29 reader count. Two queues: `_readers`, `_writers`. **Ownership is handed off** to parked waiters: a woken reader or writer returns holding the lock without retrying. That is what makes the batch claim below true. All changes to `eWriterWaiting`, all pops and all handoffs happen under the queue lock.

- `lock_shared()`: `prev = fetch_add(1, acquire)`; if `prev` has neither writer bit, done. Otherwise `unlock_shared()` the transient count (this may wake a writer, see below) and take the slow path under the queue lock: re-read; if no writer bit is set, `fetch_add(1)` and return; else push onto `_readers`, release the lock, `park()`, return (handed off).
- `lock()`: CAS `0 -> eWriter`. Slow path under the queue lock: `prev = fetch_or(eWriterWaiting)`; if `prev` has no readers and no writer, the last reader left between the fast path and here and saw no waiting bit, so take the lock now: CAS `prev | eWriterWaiting -> eWriter | (waiting if _writers non-empty)`, return. Else push onto `_writers`, release the lock, `park()`, return (handed off, `eWriter` already set for us).
- `unlock_shared()`: `prev = fetch_sub(1, acq_rel)`; if `prev` had reader count 1 and `eWriterWaiting`: under the queue lock re-check that the reader count is 0 and `eWriter` is clear (a transient fast-path reader may be in flight; whichever `fetch_sub` reaches 0 takes this path); if so, pop one writer, `fetch_or(eWriter)`, clear `eWriterWaiting` if `_writers` is now empty, release the lock, `unpark(writer)`.
- `unlock()` (writer): under the queue lock, if `_readers` is non-empty take all `n` of them and hand off: `fetch_sub(eWriter - n)` (atomically clears the writer bit and admits `n` readers; `eWriterWaiting` stays as it is, so new fast-path readers keep backing off while writers are queued), release the lock, unpark the batch. Else if `_writers` is non-empty pop one, leave `eWriter` set (handed off), clear `eWriterWaiting` if the queue is now empty, release the lock, unpark it. Else `fetch_and(~eWriter)`.

Fairness: a writer that arrives while readers hold sets `eWriterWaiting`, so later readers park; when the writer releases, every parked reader is admitted in one batch by handoff and no reader starves. A writer waits for at most one reader batch, so no writer starves. This is the bounded reader admission the owner asked for (**Decided**, Q02.2). Fast-path readers and the fast-path writer CAS may barge only when no writer bit is set, so a queued writer is never overtaken by late readers.

Both primitives are usable from plain threads: `park()` falls back to the flag wait.

**Timed waits and withdrawal are excluded** because they need to remove a node from a queue it may concurrently be popped from, which forces either a per-node generation tag with a deferred-free scheme or a global parking lot. Nothing on the migration list needs a timeout. When one appears, add `try_lock_for` with a generation word in `ParkNode` and let `unpark` ignore a node whose generation moved on.

### 6.6 Cancellation token (**Decided** Q02.1, shape is a **Proposal**)

```cpp
class CancellationSource : public ArcFromThis<CancellationSource> {
    std::atomic<bool> _requested { false };
public:
    void cancel() noexcept;                       // release
    bool isCancellationRequested() const noexcept; // acquire
};
using CancellationToken = Arci<const CancellationSource>;
```

A task may be started with a token (`exec(task, token)` overload; default none). The token is stored in the fiber context (section 7) while the task runs; `fiber::self::cancellationRequested()` reads it. Cancellation is cooperative only: a parked fiber stays parked until its waitable completes, and the task checks the token when it resumes. Error propagation through the join counter waits for `Diagnostic` (W05.1) and the task graph (W02.4).

### 6.7 Memory orderings

| Operation | Order | Why |
|---|---|---|
| `Event::_state` set / check | release / acquire | publishes everything the completer wrote before `set()` to the waiter |
| `ParkNode::state` exchanges | acq_rel | both sides must see each other's prior writes (task fields, the node's `fiber`) |
| `JoinCounter::_pending` | acq_rel on `fetch_sub` | the last child's writes become visible to the creator; standard counter rule |
| Mutex word CAS | acquire on lock, release on unlock | normal mutex semantics |
| `ParkQueue` lock | `SpinMutex` acquire / release | protects the list and the contended bit together |
| Thread flag | `store(1, release)` + `notify_one`; `wait(0)` + `load(acquire)` | standard `atomic::wait` protocol |

None of these is marked unverified: they are textbook; the only subtle part is the handshake in 6.2, which uses a single RMW per side.

## 7. Fiber control block changes

```cpp
struct Fiber {
    handle_type handle, parent;
    non_owning_rptr<const task::TaskDelegate> task;
    ptr<Schedule> schedule;                // set by the worker when it attaches a task; unpark pushes here
    ParkNode parkNode;                     // replaces FiberAwaitable awaiter
    CancellationToken cancellation;        // null unless the task was started with one
};
```

`unpark` takes only the node: the fiber knows its schedule, so tests and tools that run their own `Schedule` work without a global.

- `FiberAwaitable`, `IsAwaitableSignal*`, `await_signal`, `await_signal_call` and `self::await(mref<FiberAwaitable>)` are removed after migration. The polled `bool()` member-call awaitable has no user outside the scheduler.
- `fiber::self::current() -> ptr<Fiber>`: `IsThreadAFiber() ? static_cast<ptr<Fiber>>(GetFiberData()) : nullptr`. The worker's root fiber was created by `ConvertThreadToFiber(nullptr)`, so it also reports null; null means "not inside a task", which is the thread path. This is the real thread-or-fiber check `waitOnAtomic` lacks today. POSIX stays `todo_panic`.
- `fiber::park()` and `scheduler::unpark(ref<ParkNode>)` live in `Engine.Scheduler/Fiber/Park.{hpp,cpp}`. `unpark` pushes `node.fiber->task` through the schedule the worker uses; the fiber keeps its task pointer while parked, so the task is found without a lookup. `Schedule::push` takes the existing `UnfairSpinLock`; `unpark` is called from fibers, but holds no lock across a suspension, so the thread-id ownership is sound there.
- The pool is unchanged in this chunk, but parked fibers now hold their stacks. Section 11 records the budget risk for W02.0.

## 8. Public surface (`Heliogrim/Async`)

> Amended 2026-11-08: the `Future`/`future_state` rows below are superseded by the [promise and future rework](promise-future-design.md), which replaces the type instead of porting it. The `Event` and `JoinCounter` rows and the deprecation of the atomic-flag `await` stand.

| Today | After | Compatibility |
|---|---|---|
| `hg::await(ptr<await_signal_sub_type>)` | `hg::await(ref<Event>)`, `hg::await(ref<JoinCounter>)` | old overload kept one release as `[[deprecated]]`, body polls with `yield()` as today |
| `hg::await(Future<T>&&) -> T` | same signature; body awaits the state's `Event` | unchanged for callers |
| `hg::Future<T>::operator ptr<await_signal_sub_type>` | `Future<T>::event() -> ref<Event>` | the conversion operator is removed with the old `await` |
| `hg::yield()` | unchanged | |
| `concurrent::future_state` (`std::mutex` + `condition_variable` + `atomic_flag`) | `Event _done;` replaces all three; `wait()` is `_done.wait()`; `signal()` returns `ref<Event>` | `future::get`, `join`, `ready` keep their names |
| `Action::operator ptr<await_signal_sub_type>` (editor) | `Action::finished() -> ref<Event>`; `_finished` becomes `Event` | `ActionDispatcher` calls `await(action.finished())` |
| `io::Dispatcher::operator() -> smr<await_signal_type>` | `-> Arci<Event>` | the dispatcher is a stub; its sole caller shape changes with it |

`Event` and `JoinCounter` are declared in `Engine.Scheduler/Waitable/{Event,JoinCounter}.hpp`, which include only `<atomic>`, `Engine.Common` and `Park.hpp`. `Heliogrim/Async/Waitable.hpp` re-exports them under `hg::` as **`hg::Signal`** and `hg::JoinCounter`: `hg::Event` is already taken by `Engine.Event` (found 2026-11-09 in W02.2), and "await the signal" reads well.

## 9. Migration list

Every current wait class, its sites and its replacement. Each row becomes one task group in the plan, with a test.

| Class | Sites | Replacement |
|---|---|---|
| **A. Spin-yield loops** `while (!cond) fiber::self::yield()` | `Engine.GFX/Swapchain/VkSwapchain.cpp` (2, ring buffer full/empty), `Engine.Scheduler/Pipeline/CompositePipeline.cpp:69` (stop flag, has the `TODO: waitOnAtomic`) | Swapchain: keep the yield loop (it waits on the presentation engine, a bounded spin is correct there) and mark it `shortcut:` until W02.3 gives presentation an affine seam. CompositePipeline: `Event _stopped`; the last stage sets it; `stop()` awaits it |
| **B. Atomic-flag signals** `await_signal`, `hg::await(ptr<await_signal_sub_type>)` | `Engine.GFX/Surface/Surface.cpp:73`, `Editor.Action/Log/ActionDispatcher.cpp` (3), `Editor.Boot/Boot/AssetInit.cpp:453`, `Engine.Reflow/Window/WindowManager.cpp` (2), `Editor.Assets.Actions/UnknownImport.cpp:140`, `Editor.Action/Action/{Action,SimpleAction,AutoImportAction}` conversion operators | `await(future)` or `await(action.finished())` per section 8 |
| **C. Thread-blocking atomic waits** `waitOnAtomic`, `waitUntilAtomic` | `Editor.Core/EditorEngine.cpp` (12), `Engine.Core.Game/GameEngine.cpp` (11), `Engine.Pedantic.Resource/ExclusiveResource.hpp:83`, `Engine.Resource/Manage/UniqueResource.hpp:47`, `Engine.Storage.Action/Access/ExclusiveIoResource.hpp`, `Engine.Scheduler.Test/test.cpp` | Engine lifecycle counters (`setupCounter`, `moduleCount`, `next`): each phase knows its child count before starting any child (`getCoreModuleCount()`, 1 for the sub-module task) and the counters are reset between phases, so each phase gets a fresh `JoinCounter(n)` or `Event`; no `add()` and no reset API. Awaited from the main thread (thread path). The three `ExclusiveResource`-style acquire loops: `FiberMutex` replaces the `atomic_flag` + `waitOnAtomic` pair. `waitOnAtomic` / `waitUntilAtomic` are then deleted |
| **D. Blocking future waits** `concurrent::future::get/join` | `Engine.Async.Test/Promise.cpp` (4), no production site | `future_state` on `Event` (section 8); tests keep calling `get()` and gain a fiber-side test |
| **E. Promise bodies as tasks** `make_task(promise)` | `Engine.Scheduler/Async.hpp`, `Engine.Scheduler.Test/test.cpp:98`, platform and importer promises | unchanged; completion calls `Event::set()` through `future_state::complete()` |
| **F. OS mutexes reachable from tasks** | `UnfairSpinLock` in `Engine.GFX/Command/{CommandPool,CommandBuffer}`, `Engine.Driver.Vulkan/VkCmdMgr.cpp`; `SpinMutex` shortcut in `Engine.Accel.Lang/Ir/Variant.hpp` | `FiberMutex` for the command pool and buffer, `FiberSharedMutex` for the variant caches (closes the `shortcut:` from PR #156). `FifoWorkSet` keeps `UnfairSpinLock` (no suspension inside) |
| **G. Worker loop** | `Engine.Scheduler/Worker/Worker.cpp:150-200` | handshake step 2 replaces "reschedule suspended task"; the `awaiter.ready()` poll is gone; the idle branch stays as is (idle strategy is W02.5) |

Not in the list: `thread::self::yield()` in `WinPlatform.cpp:323` and `CompScheduler.cpp` run on plain threads and stay.

## 10. Tests

In `Engine.Scheduler.Test`:

- Handshake race: a test hook in `Worker` (debug-only callback after `SwitchToFiber` returns) lets the test call `set()` between the fiber's push and the worker's step 2, and separately after step 2; both orders must resume the task exactly once.
- Worker availability: with 2 workers, park 1,000 tasks on one `Event`, then run an unrelated task and assert it completes before the event is set; set the event and assert all 1,000 complete.
- `JoinCounter`: N children plus creator guard; a child finishing before `add()` of the next one never completes the counter early.
- Thread path: the main test thread awaits an `Event` set from a task; `FiberMutex` locked from a thread and a fiber alternately.
- `FiberMutex`: 8 fibers increment a counter under the lock 10,000 times each with yields inside the critical section (forces migration while holding); result exact; no `UnfairSpinLock`-style throw.
- `FiberSharedMutex`: steady readers (never empty) plus one writer; the writer acquires within one reader batch; readers arriving after the writer parked are admitted only after it.
- Stale barrier tests behind `#if FALSE` are not ported here (they are W02.4's stage API).

In `Engine.Async.Test`: `Promise.cpp` unchanged and passing; a new case awaits a future from inside a task.

## 11. Risks and open items

- **Fiber stack budget**: parked fibers hold their stacks. `FiberPool` grows without bound and the stack commit size question is Q02.3 (W02.0). This design does not cap the pool; W02.0 must produce the number and W02.2 adds the cap with a diagnostic once it exists. Until then a workload that parks tens of thousands of fibers is a memory hazard.
- **Pool exhaustion deadlock**: a waitable that only a scheduler task can complete, awaited by every available fiber, deadlocks only if the pool is capped. With the current unbounded pool it degrades to memory growth. The cap and this rule must land together.
- **Spin bound before parking** is unmeasured; W02.0 experiment 1 (switch cost) gives the number that makes the bound rational.
- **#77 memory orders** are marked unverified in the Arci header; this design relies on Arci only for `CancellationToken` and `Dispatcher` results, never on the wait path.
- **Swapchain spin** stays a `shortcut:` until the presentation path has an affine seam (W02.3).

## 12. Decisions made in this document (for review)

1. Park node embedded in the fiber, one per fiber; no heap wake nodes, no `Arci<Task>` (6.2).
2. One spin-guarded `ParkQueue` for one-shot and reusable primitives; lock-free list deferred behind W02.0 experiment 5 (6.3).
3. `when_any`, timed waits and node withdrawal out of scope; the extension path is named (6.4, 6.5).
4. `FiberSharedMutex` wake policy: reader batch first, then one writer; writer-waiting bit blocks new readers (6.5).
5. Cancellation is a token in the fiber context with cooperative checks only; no interruption of a parked wait (6.6).
6. Old `hg::await(ptr<await_signal_sub_type>)` deprecated for one release, implemented by polling as today (8).
7. Swapchain yield loops stay, marked `shortcut:` (9.A).

Builder check (2026-11-08, independent reviewer reading this page cold) found four protocol holes, all folded in above: plain `yield()` needs the `eIdle` state or the worker drops the task (6.2); `FiberMutex::unlock` must re-set `eContended` when waiters remain and the slow path must restart on a failed CAS (6.5); `FiberSharedMutex` needs handoff, a re-check in the writer slow path and a defined owner of `eWriterWaiting` (6.5); thread nodes cannot live on the stack and `next` must be read before `unpark` (6.2). Its three questions (per-phase counters, which schedule `unpark` uses, converted non-worker threads) are answered in 9.C, 7 and 6.2.
