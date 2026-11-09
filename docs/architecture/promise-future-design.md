# Promise and Future Rework (Design)

**Status**: design, draft 2026-11-08. Companion to the [scheduler waitables design](scheduler-waitable-design.md), which gives it the `Signal` it completes on. Agreed in the design conversation of 2026-11-08 (W02.1 follow-up on the [concurrency work page](../plan/work/concurrency-fibers.md)). Implementation plan untracked in the engine checkout (`docs/superpowers/plans/2026-11-08-promise-future.md`).

Markers: **Decided** = agreed by the owner. **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

The current `Engine.Async` promise is three things at once: a shared state, a chain of continuations, and a task body. `promise<T>` wraps a `std::function`, is itself convertible to `std::function<void()>` so `make_task(promise)` can run it, and every `then` allocates another `std::shared_ptr<promise_state>` holding another `std::function`. Continuations run on the completer's stack, so a long chain is a deep stack. `hg::Future` exists only to expose a wait signal over `concurrent::future`. The owner's verdict: not ergonomic, not cheap, and it takes thought every time to know whether a use is correct.

The rework makes the vocabulary match the words: **a producer makes a promise and resolves or breaks it; a consumer holds a future and awaits it.** One shared state block, no `std::function`, no `std::shared_ptr`, continuations scheduled as tasks instead of nested calls, failure visible in the type.

## 2. Goals (**Decided**)

1. Two move-only handles over one shared state: `Promise<T, E>` produces, `Future<T, E>` consumes.
2. A promise destroyed while pending is **broken**; `await` on its future reports that. Nothing is lost silently.
3. `await(future)` returns `Result<T, …>`; the common one-liner is `auto f = async([] { return load(); });`.
4. The promise is not a task. A task is code that happens to resolve a promise.
5. `then` chaining stays and is type-safe end to end. Resolving never runs a continuation on the resolver's stack.
6. Per-promise overhead is one allocation (the shared state) and zero `std::function`.
7. Some compile-time feedback on soundness: a `Send` constraint on the carried type and Clang thread-safety annotations on the fiber mutexes.

## 3. Non-goals

- Exception capture. A body that can fail returns a `Result`; the future never catches.
- `when_all` / `when_any` over futures (the `JoinCounter` covers the all case for tasks; a future combinator comes with the task graph if a stage needs it).
- Timed waits (same reason as the waitable design, section 6.5).
- Executor or scheduler parameters on `then`. Continuations run on the task scheduler with the resolver's priority mask.
- Replacing `Engine.Async/Collection/RingBuffer` or the spin locks.

## 4. Anti-goals

- No `std::function`, `std::shared_ptr`, `std::mutex` or `std::condition_variable` anywhere in the two headers.
- No recursion on resolve. Chain depth is bounded by the queue, never by the stack.
- No API that compiles when the value type cannot cross threads (section 8).
- No second future type for the public API: `hg::Future` **is** the type, `concurrent::future` goes away.

## 5. Failure model (**Proposal**)

```cpp
struct Broken { enum class Reason : u8 { eDropped, eRejected } reason; };
```

`Broken` is a fixed marker, never a payload. `eDropped`: the promise was destroyed unresolved. `eRejected`: the producer called `reject()` on a promise whose `E` is `Broken` (the default). When a producer has a real error to report it names it: `Promise<T, E>` / `Future<T, E>`, and `await` returns `Result<T, Variant<E, Broken>>` as `Result<T, Fail<E>>` where `Fail<Broken>` collapses to `Broken`. Once W05.1 lands `Diagnostic`, it becomes the usual `E`; the marker never grows.

`then` propagates `E` unchanged unless the continuation maps it (section 7.3).

## 6. Shared state

```cpp
struct Pending {};
template <typename T> struct Resolved { T value; };   // Resolved<void> is empty
template <typename E> struct Failed { Fail<E> error; };

template <typename T, typename E>
class FutureState : public ArcFromThis<FutureState<T, E>> {
    engine::scheduler::Signal _done;                       // from the waitable design
    Variant<Pending, Resolved<T>, Failed<E>> _slot;       // written once, before _done.set()
    std::atomic<u8> _contState { eNone };                 // eNone, eStored, eClaimed
    Continuation _cont;                                   // the successor's work, see 7.3
    task::TaskMask _mask;                                 // inherited by the continuation task
};
```

- Reference counted with `Arci` (#77, landed): exactly two owners while both handles live, one afterwards, zero frees it. `Arci` is used off the wait path only; the wait itself is `_done.wait()`.
- `_slot` is written exactly once by the producer, then `_done.set()` (release). Consumers read after `_done.isSet()` or `wait()` (acquire). The wrapper structs keep the alternatives distinct even when `E` is `Broken`, `T` is `void` or `T` happens to equal `E`; the `Variant` is the project's `Engine.Common/Variant.hpp`.
- `Continuation` is a move-only callable with fixed inline storage and no heap fallback: `void(ref<FutureState>)`, 64 bytes of storage including the `Arci` to the successor state (**Builder's call** on the exact size, but a `static_assert` must reject a larger capture rather than allocate). The project has only the non-owning `FnRef`, so this is the one new utility (`UniqueFn`).
- `_contState` arbitrates who schedules the continuation (section 7.3). A state created already resolved (`Future::ready`) starts at `eClaimed`, so a later `then` schedules itself.

## 7. API

### 7.1 Producer

```cpp
template <typename T, typename E = Broken>
class Promise {                                  // move-only
public:
    Promise();                                   // allocates the state
    ~Promise();                                  // pending -> breaks with eDropped
    [[nodiscard]] Future<T, E> future();         // exactly once; assertd on a second call
    void resolve(T&& value_) noexcept;           // exactly once, any thread or fiber
    void reject(E&& error_) noexcept;            // exactly once
    [[nodiscard]] bool isPending() const noexcept;
};
// void: handled by constrained members and `if constexpr` on the primary template (resolve() without a value,
// Future<void>::ready(), await -> Result<void, Fail<E>>), not by a separate specialisation (as built, W02.2).
```

`resolve` and `reject` store into `_slot`, call `_done.set()`, then run the continuation arbitration, exactly once per promise: the destructor's break path runs only when the promise never finished (a flag on the handle, not on the state, so a resolve followed by a late `then` cannot double-schedule). Both are `noexcept` and callable from an affine thread (platform queue, IO completion): `Signal::set` is thread-safe and `Scheduler::exec` is a spin-locked queue push with no thread affinity. A continuation scheduled after the scheduler has stopped is dropped with the queue; that is the existing behaviour of any task pushed late and is accepted here.

### 7.2 Consumer

```cpp
template <typename T, typename E = Broken>
class Future {                                   // move-only
public:
    [[nodiscard]] bool isReady() const noexcept; // _done.isSet()
    [[nodiscard]] static Future ready(T&& value_);   // already-resolved future, no task
    template <typename Fn> [[nodiscard]] auto then(Fn&& fn_) &&;   // section 7.3
};
template <typename T, typename E> [[nodiscard]] Result<T, Fail<E>> await(Future<T, E>&& future_);
```

`await` parks the fiber (or blocks the plain thread) through `_done.wait()`, then moves the value out. A `Future` is consumed by `await` or `then`; using it after is a debug assert (null state). There is no shared future: the one site that looked multi-consumer (`RenderTarget`) never awaits its transition future at all (section 9), so a copyable variant waits for a real consumer.

### 7.3 Chaining (**Decided** semantics, **Proposal** mechanics)

`std::move(f).then(fn)` where `fn` is callable with `T&&` (or nothing for `void`):

| `fn` returns | Resulting future |
|---|---|
| `U` | `Future<U, E>` |
| `Result<U, E2>` | `Future<U, E2>`; an `E` from upstream is carried only if `E2` is constructible from `E`, otherwise compile error |
| `Future<U, E2>` | `Future<U, E2>` (flattened: the continuation task registers a second continuation on the inner future's state that resolves the outer state; one extra state and one extra hop for this row) |

`then` creates the successor state and stores **in the predecessor's** `_cont` a callable capturing `fn` and `Arci<successor>`. When it runs it reads the predecessor's slot: a value calls `fn` and resolves the successor; upstream `Broken` or `E` skips `fn` and fails the successor. The successor's own `_cont` stays free for the next link. A chain of `n` plain links is `n + 1` states and `n` scheduled tasks. **Failure propagation also hops**: the skip path resolves the successor from inside the scheduled task, never inline, so a broken 10,000-link chain unwinds through the queue like a successful one.

Arbitration between resolver and `then`-caller with `_contState`:

- `then`: store `_cont`, then `prev = _contState.exchange(eStored, acq_rel)`. If `prev == eClaimed` the value already arrived: schedule the continuation task now.
- `resolve`/`reject`/break: after `_done.set()`, `prev = _contState.exchange(eClaimed, acq_rel)`. If `prev == eStored` schedule the continuation task now.

Exactly one side sees the other's state, so the continuation is scheduled once, and never on the resolver's stack: "schedule" is `Scheduler::exec(make_task(...))` with `_mask`, and the task holds its own `Arci` to the predecessor. A continuation registered after resolution therefore also costs one queue hop; this is deliberate so timing does not depend on the race.

### 7.4 Making futures

```cpp
template <typename Fn> [[nodiscard]] auto async(Fn&& fn_, task::TaskMask mask_ = eNormal) -> Future<T, E>;
```

`T, E` are deduced from `fn_`'s return: `U` gives `Future<U, Broken>`, `Result<U, E>` gives `Future<U, E>`, `Future<U, E>` is flattened. Implementation, as built (W02.2): `async(fn_, mask_)` is `Future<void>::ready(mask_).then(fn_)`, so there is one scheduling path, the body may be move-only (it lives in the `UniqueFn`), and the continuation task inherits `mask_`. One queue hop per call, like every `then`. `Future::ready(value)` covers the sites that today build a promise only to run it inline (`Actor.cpp`).

The scheduler-level `scheduler::async(std::function<Ty()>)` in `Engine.Scheduler/Async.hpp` is deleted; its two callers move to `hg::async`.

## 8. Soundness feedback (**Proposal**)

- **Send constraint**: `template <typename T> inline constexpr bool is_send_v = …;` consulted through a concept `Send<T>` at the **creation points** (`Promise`'s constructor, `Future::ready`, `then`'s successor type, hence `async`), not on the class templates. Naming `Future<T>` in a declaration must stay legal for an incomplete `T` (the engine's public API returns `Future<Opt<ActorRef<Actor>>>` with `ActorRef` forward-declared), and the trait needs a complete type; constraining the class would have broken that (found 2026-11-09 in W02.2). The guarantee is the same: a non-Send value can never be produced. Default `true`; opted out by specialising for types that must stay on one thread. The engine opts out `Rc<T>` and `RefCounted` handles (non-atomic counts), `ptr<void>` and any type that declares `using not_send = void;`. `Arci`, `uptr`, `nmpt` and values stay `Send`. An opt-in default would reject every current use on day one and the project has no reflection to derive it, so opt-out is the lazy sound choice; it still catches the two classes that bit this codebase (non-atomic ref counts and raw thread-affine handles).
- **Clang thread-safety annotations** on `FiberMutex` and `FiberSharedMutex` (`CAPABILITY`, `ACQUIRE`, `RELEASE`, `ACQUIRE_SHARED`, `TRY_ACQUIRE`) and `-Wthread-safety` on the clang-cl configuration. Fields guarded by them gain `GUARDED_BY`. Cheap, catches unlocked access at compile time, no effect on MSVC builds.
- Capture analysis (is this lambda safe to run elsewhere) is not expressible in C++ and waits for a clang-tidy check under S63.

## 9. Migration

| Today | Sites | After |
|---|---|---|
| Promise as task body, run inline: `p(); return Future{f}` | `Heliogrim/Actor/Actor.cpp` (5), `Heliogrim/Universe/{Universe,Level}.cpp` (3), `Heliogrim/Core/Session.cpp` | `Future<T>::ready(value)` or `hg::async(fn)` where the work was meant to be deferred |
| Promise as task body on the scheduler: `scheduler::async(std::function)` | `Engine.Scheduler/Async.hpp` (2 overloads) | `hg::async(fn, mask)`; the delayed overload becomes `hg::async(fn, delayTicks)` only if a caller exists, else dropped |
| Promise pushed to an affine queue and run there | `Support.Platform.Win32/WinPlatform.cpp` (2), `Engine.Scheduler/Task/SignaledQueue.hpp` | `SignaledQueue` stores `UniqueFn<void()>` instead of `std::function<void()>` (its only user is the platform); the queued callable captures the `Promise<uptr<NativeWindow>>` and the platform thread calls `resolve()` |
| Importers wrapping a finished value | `Engine.GFX/Importer/{Fbx,Font,Ktx}Importer.cpp`, `Engine.SFX` importers | `Future<T>::ready(value)` |
| Promise with `Result` as value | `Editor.Assets.Actions/UnknownImport.cpp` | `Promise<FileUrl, std::runtime_error>` and `await` returning `Result<FileUrl, Fail<std::runtime_error>>` |
| Promise stored in `uptr`, invoked later to release a keepalive | `Engine.GFX/RenderTarget.{hpp,cpp}` (8), `TransitionResult` consumers in `Engine.GFX.Scene/RenderSceneManager.cpp:61`, `Engine.Reflow/Widget/Viewport.cpp:277`, `Engine.Reflow/Window/WindowManager.cpp:327` | Every consumer discards the returned future (`[[maybe_unused]]`); the promise only delays the release of the previous scene view or swapchain until the invoke point. Replace with plain members `smr<const scene::SceneView> _previousSceneView`, `smr<Swapchain> _previousSwapchain` reset where the promise is invoked today, and drop the future from `TransitionResult`. No `Promise` at this site |
| `hg::Future` wrapper, `concurrent::future`, `nxpromise` | `Heliogrim/Async/Future.hpp`, `Engine.Async/Await/{Future,Promise}.hpp` | deleted; `Heliogrim/Async/Future.hpp` declares the new `Future`, `Promise`, `async`, `await` |
| Tests | `Engine.Async.Test/Promise.cpp`, `Engine.Scheduler.Test/test.cpp:89` | rewritten against the new API (section 10) |

Order relative to the waitable plan: this lands after its Task 4 (`Signal`) and replaces its Task 6.

## 10. Tests

`Engine.Async.Test/Future.cpp`:

- resolve then await, await then resolve (thread and fiber), value moved out exactly once.
- drop a pending promise: `await` returns `Broken{eDropped}`; `reject`: `eRejected` or the typed `E`.
- `then` registered before and after resolution both run exactly once and never on the resolver's stack (assert the continuation sees a different fiber or runs after `resolve` returned).
- chain of 10,000 `then` links resolves with a fixed stack high-water mark (the test fails today by overflowing).
- `Result`-returning continuation maps to the typed error; a `Broken` upstream skips the continuation.
- `then` on an already-ready future (`Future::ready`) runs once; `resolve` followed by a late `then` runs once and the promise destructor does not re-arbitrate.
- `Send`: `static_assert(!requires { Promise<Rc<int>>{}; })` style negative compile test via `requires`.
- `-Wthread-safety`: a test TU that unlocks a `FiberMutex` it never locked fails to compile under clang-cl (kept as a documented manual check, not a gtest).

## 11. Risks

- The inline `Continuation` storage size bounds captures; a chain that captures a large object must move it into an `Arci` first. The `static_assert` message says so.
- One queue hop per link makes very short chains slower than today's inline call. Acceptable by decision 2.5; measure only if a hot path grows a chain.
- Continuations scheduled after the scheduler stopped are dropped with the queue (7.1). The platform thread outlives the scheduler during shutdown, so a window promise resolved then loses its continuation; today no such continuation exists.
- `is_send_v` opt-out can be wrong by omission. The opted-out types declare it themselves, so the list is `grep not_send`.

## 12. Decisions made in this document (for review)

1. `Broken` is a fixed two-reason marker; typed errors go through `E` (5).
2. Continuation storage is inline, fixed size, no heap fallback (6).
3. Both `then` and `resolve` schedule through the task queue, for values and for failures; no inline fast path (7.3).
4. `Future` is move-only and there is no shared future; the render target keeps its keepalives as members instead (7.2, 9).
5. `Send` is opt-out, declared on the non-send types (8).
6. `scheduler::async` and `concurrent::future` are deleted rather than wrapped (7.4, 9).
7. `SignaledQueue` switches to the move-only callable (9).

Builder check (2026-11-08, cold reader) found and this revision fixed: one continuation slot used for two purposes (now the predecessor holds the successor's work); duplicate `Variant` alternatives for `E = Broken` and `T = void` (wrapper structs); `Future::ready` had to start claimed; the promise destructor had to be gated on the handle, not the state; flatten is `n + 1`; failure propagation had to hop too. Its three questions (exec from non-worker threads and after stop, `SignaledQueue` element type, render target consumers) are answered in 7.1 and 9.
