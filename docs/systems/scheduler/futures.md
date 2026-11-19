# Promise and Future

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), 2026-11-16; lanes, scheduling of continuations, the wait boost, limits and tests re-checked at [`fd5affa5`](https://github.com/Heliogrim/Heliogrim-Engine/tree/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab), 2026-11-19
**Modules**: `Engine.Async` ([`Future/Promise`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Future/Promise.hpp), [`Future/Future`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Future/Future.hpp), [`Future/FutureState`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Future/FutureState.hpp), [`Future/Schedule`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Future/Schedule.hpp), [`Future/Async`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Future/Async.hpp), [`Future/Send`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Future/Send.hpp), [`Future/Broken`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Future/Broken.hpp)), re-exported by `Heliogrim/Async/Future.hpp`
**Related**: [promise and future design](../../architecture/promise-future-design.md), [waitables design](../../architecture/scheduler-waitable-design.md) section 8, [lane policy design](../../architecture/lane-policy-design.md) section 7 (wait boost), [lanes and priority](lanes.md)

A producer makes a promise and resolves, rejects or drops it; a consumer holds the future and awaits it or chains work onto it. Part of the [fiber scheduler](index.md); the future completes through a [`Signal`](waitables.md#signal).

## Purpose

`Promise<T, E>` and `Future<T, E>` hand one value (or one error) from one task to another without blocking a worker:

- One shared state per promise, reference-counted with `Arci`; no `std::function`, no `std::shared_ptr`.
- Failure is in the type: `await` returns `Result<T, Fail<E>>`.
- A promise destroyed while pending is **broken**; the future reports it instead of hanging.
- Continuations (`then`) always run as scheduler tasks, never on the resolver's stack, so a 10,000-link chain does not grow the stack. The one exception is the engine's own forwarding step for a continuation that returns a future (see [lanes and the wait boost](#lanes-and-the-wait-boost)).
- Every continuation has a lane, fixed when `then()` is called; awaiting a future from a higher lane raises the task that produces it.

Not supported: shared (copyable) futures, `when_all` / `when_any` over futures, timed waits, exception capture, choosing an executor per `then`.

## Vocabulary

| Type | What it is |
|------|------------|
| `Promise<T, E = Broken>` | move-only producer handle; `future()`, `resolve`, `reject`, `isPending` |
| `Future<T, E = Broken>` | move-only consumer handle; `isReady`, `then`, consumed by `await` |
| `FutureState<T, E>` | the shared block: a `Signal done`, the slot, the continuation arbitration word, the continuation (`UniqueFn`), a `Lane`, the `producer` cell (the continuation that fills this state; null for promise and ready states) and the `contCell` (the cell of the stored continuation; null marks the inline forwarder) |
| `BoostCell` | scheduler object linking a producing task to whoever waits for its result ([lanes](lanes.md#wait-boost)) |
| `Pending`, `Resolved<T>`, `Failed<E>` | the alternatives of the slot (`Variant`) |
| `Broken` | fixed marker with a `reason`: `eDropped` or `eRejected` |
| `Fail<E>` | `Broken` when `E` is `Broken`, otherwise `Variant<E, Broken>` |
| `Send<T>` | concept every carried value must satisfy |

## Using it

**Run work and get its result**, the common case. `hg::async(fn, lane)` (lane defaults to `eInherit`) runs `fn` as a task and returns a future of its result:

```cpp
// Heliogrim/Universe/Universe.cpp
Future<Universe> hg::CreateUniverse() noexcept {
	return hg::async(
		[]() {
			auto defaultScene = make_uptr<engine::scene::GameScene>();
			defaultScene->prepare();
			// ...
			return Universe { std::move(universe) };
		}
	);
}
```

What `fn` returns decides the future: a plain `U` gives `Future<U, Broken>`, a `Result<U, E>` gives `Future<U, E>`, a `Future<U, E>` is flattened into `Future<U, E>`. `async` is literally `Future<void>::ready(lane_).then(fn_)`, so it costs one queue hop like any `then`.

**Produce a value from anywhere** (a task, an affine thread, a callback):

```cpp
Promise<int, std::string> promise {};
auto future = promise.future();     // exactly once
// later, on any thread or fiber:
promise.resolve(42);                 // or promise.reject(std::string { "bad" });
```

**Consume it**:

```cpp
auto result = await(std::move(future));   // Result<int, Variant<std::string, Broken>>
if (not result.has_value()) {
	if (result.error().is<Broken>()) { /* dropped or rejected without a typed error */ }
}
```

`await` parks the calling fiber (or blocks a plain thread) on the state's `Signal`, then moves the value out. It consumes the future.

**Chain**: `std::move(future).then(fn)` consumes the future and returns a new one. From `Engine.Async.Test/Future.cpp`, a continuation that maps to a typed error:

```cpp
Promise<int> promise {};
auto mapped = promise.future().then(
	[](int) -> Result<int, std::string> { return Unexpected<std::string> { "bad" }; }
);
promise.resolve(1);
auto result = await(std::move(mapped));
// result.error().as<std::string>() == "bad"
```

| `fn` returns | Result of `then` |
|---|---|
| `U` | `Future<U, E>` |
| `Result<U, E2>` | `Future<U, E2>`; compiles only if `E2` is `E`, is constructible from `E`, or `E` is `Broken` |
| `Future<U, E2>` | `Future<U, E2>`, settled when the inner future settles |

If the upstream failed, `fn` is skipped and the error is converted and passed on; that also happens in a scheduled task, not inline.

**Already have the value**: `Future<T>::ready(value)` and `Future<void>::ready()` make a settled future with no task.

## How it works

```hg-diagram
sequenceDiagram
    participant P as Promise (producer)
    participant S as FutureState
    participant C as then() caller
    participant Q as Scheduler
    par producer
        P->>S: emplace slot, done.set(), exchange contState to eClaimed
    and consumer
        C->>S: store cont, exchange contState to eStored
    end
    alt producer saw eStored
        P->>Q: execBoostable(make_task(cont, lane), cell)
    else consumer saw eClaimed
        C->>Q: execBoostable(make_task(cont, lane), cell)
    end
    Q->>S: task runs cont(predecessor state)
    Note over S: cont fills the successor's slot and completes it
```

The arbitration is two functions in [`Future/Schedule.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Async/Future/Schedule.hpp):

```cpp
template <typename T_, typename E_>
void complete(ref<const Arci<FutureState<T_, E_>>> state_) {
	state_->done.set();
	if (state_->contState.exchange(eClaimed, std::memory_order::acq_rel) == eStored) {
		scheduleContinuation(Arci<FutureState<T_, E_>> { state_ });
	}
}

// cell_ is the cell the continuation produces into; nullptr marks the engine's forwarder, which runs inline.
template <typename T_, typename E_>
void store(
	ref<const Arci<FutureState<T_, E_>>> state_,
	mref<Arci<::hg::engine::scheduler::BoostCell>> cell_,
	std::type_identity_t<UniqueFn<void(ref<FutureState<T_, E_>>)>>&& cont_
) {
	state_->contCell = std::move(cell_);
	state_->cont = std::move(cont_);

	if (state_->contState.exchange(eStored, std::memory_order::acq_rel) == eClaimed) {
		scheduleContinuation(Arci<FutureState<T_, E_>> { state_ });
	}
}
```

Exactly one side sees the other's value, so the continuation is scheduled once. `scheduleContinuation` makes a task in the state's `lane`, stores the task pointer in the cell and pushes it with `Engine::getEngine()->getScheduler()->execBoostable(task, cell)`, without resolving the lane again; the task holds an `Arci` to the state until it has run. With no cell (the forwarder) it runs the continuation inline instead.

Details that matter when you change it:

- `then` creates the successor state and stores **on the predecessor** a callable that captures `fn` and an `Arci` to the successor. A chain of n plain links is n + 1 states and n tasks.
- The successor's lane is the lower of the predecessor's lane and the lane resolved at the `then()` call; the continuation task runs in it. Details below.
- `Promise::finish` (resolve, reject, or the destructor's drop) marks the handle finished, calls `complete`, and releases its reference only if the future was already taken, so `future()` after `resolve()` still works.
- `Future::ready(state)` starts the state at `eClaimed`, so a `then` on it schedules itself at once.
- The continuation is a `UniqueFn<void(ref<FutureState>), 64>`: inline storage, no heap fallback. A capture that does not fit has no matching constructor and fails to compile.

## Lanes and the wait boost

A future's continuation runs in a [lane](lanes.md). The lane is chosen when the chain is built, not when the value arrives, because the completing thread (often the IO thread) says nothing about who wants the result.

| Call | Lane of the new state |
|---|---|
| `Promise<T, E>()` | `eFrame`, the neutral value of "lower of"; never used to queue anything |
| `Future<void>::ready(lane)`, so `hg::async(fn, lane)` | `resolveLane(lane)` in the calling context |
| `std::move(f).then(fn)` | `lower(f's lane, resolveLane(eInherit))`: the lower of the predecessor and the caller |

So a chain built on a Background task stays Background even if a Frame task resolves the promise (`FutureLane.ContinuationKeepsLaneResolvedAtThen`), and `async` from a plain thread is Interactive.

**Boost on await.** `then()` gives the successor a `BoostCell` (`producer`) whose `dependsOn` is the predecessor's cell; promise and ready states have no cell. `await` on a fiber, with a producer present and the state not done, links the awaiting task's own cell to that producer and calls `boost(producer, resolveLane(eInherit))` before it parks. The boost raises every cell up the chain and moves a queued producer into the waiter's lane; a running producer moves at its next `checkpoint()`. `await` from a plain thread or on a promise-filled future only waits. Mechanism and limits: [lanes, wait boost](lanes.md#wait-boost).

**Inline forwarding.** When `fn` returns a future, the step that moves the inner result into the outer state is the one continuation stored without a cell (`detail::storeInline`). It runs inline where the inner state completes, through an iterative trampoline (`detail::runInline`, a thread-local queue), so a deep chain of futures returning futures does not grow the stack and never waits in a lower lane. It links the outer cell to the inner producer and boosts the inner producer only if a waiter has already raised the outer cell. User continuations never run inline.

## The Send constraint

```cpp
// Types opt out by declaring a public `not_send` alias; a raw ptr<void> carries no ownership information.
template <typename T_>
inline constexpr bool is_send_v = not requires { typename T_::not_send; } && not std::is_same_v<std::remove_cv_t<T_>, ptr<void>>;
```

The check sits on the creation points: `Promise()` (`requires Send<T_>`), `Future::ready` and the successor type inside `then` (`static_assert(Send<U>, "future values must be Send")`). Naming `Future<T>` with an incomplete `T` in a declaration stays legal. Today `RefCounted` and `RefCountedIntrusive` (`Rc<T>`) declare `not_send`; `Arci`, `uptr` and plain values are `Send`.

The check is opt-out and shallow: a struct that contains an `Rc<T>` member is `Send` unless it declares `not_send` itself.

## Debugging

| Symptom | Where to look |
|---------|---------------|
| `await` returns `Broken { eDropped }` | the promise was destroyed without `resolve` or `reject`; find its owner's lifetime |
| `static_assert` "future values must be Send" | the continuation returns a type with `not_send`; return an `Arci` or a value instead |
| `static_assert` "continuation error type must be constructible from the upstream error" | a `Result<U, E2>` continuation whose `E2` cannot hold the upstream `E` |
| no viable conversion to `UniqueFn` inside `then` | the lambda's captures exceed the inline storage; move large captures into an `Arci` or `uptr` |
| assert in `Promise::future` | `future()` called twice |
| assert in `resolve` / `reject` | the promise was finished already |
| assert `not thread::self::isAffine()` from `await` | an affine thread awaited a future; resolve a promise from the affine thread instead and await elsewhere |

## Limits and known issues

- **Continuations need a live scheduler.** `complete` calls `Engine::getEngine()->getScheduler()->exec` with no shutdown check. A promise resolved after the scheduler was destroyed is not safe.
- **No boost through a `Promise`.** A promise-filled future has no producer cell, so awaiting it raises nothing; an IO request's urgency is its IO queue priority. Its continuations still get the lane resolved at `then()`.
- **Boost search cost.** A boost finds a queued producer with a linear search of its lane; behind a deep Background queue an `await` from Frame can cost milliseconds ([lanes](lanes.md#limits-and-known-issues)).
- **`reject(Broken)` takes any reason.** With the default `E`, the caller passes the `Broken` value, so `eDropped` can also be passed by hand; the tests pass `eRejected`.
- **One consumer.** `then` and `await` consume the future; a second consumer needs its own promise.

## Changing it

Tests in `Heliogrim-Engine.Async.Test`, `Future.cpp`: resolve and await in both orders (thread and fiber), dropped and rejected promises, `void`, `ready`, value moved once, state freed after both handles, `then` before and after resolve and after a drop, `ThenNeverOnResolverStack`, `ChainOfTenThousandLinks` and `BrokenChainOfTenThousandLinks`, error mapping and skipping, flattening (including a dropped inner promise), the `async` forms, the `Send` static checks, and `FutureLane` (lane kept from `then()`, `async` from a plain thread is Interactive). `FutureBoost.cpp`: a queued producer boosted by a Frame waiter behind a flood, a chain scheduled in the waiter's lane, a nested wait, a flattened promise future without a lower-lane hop, no producer is a no-op, a deep flatten chain without recursion, flatten raising the inner producer only under a waiter, one run under racing boosts.

Model: `Engine.Async/Future/FutureState.tla` + `.cfg` (K = 3: a promise state, two `then` links, each possibly through an inner future) checks that every continuation runs once and only after both its value and its `then`, and that the chain completes; the forwarder on an inner state runs inline as a trampoline. A change to `complete`, `store` or the order of `done.set()` and the exchange must be re-checked there. The boost itself is modelled in `Engine.Scheduler/Process/BoostCell.tla` ([lanes](lanes.md#verification)).

### Pitfalls

- **A value type must not suspend in its move constructor or destructor** (owner rule Q02.20). When a continuation returns a future, the forwarding step moves and destroys values inline on the completing thread, which may be the IO thread. Constructors and destructors do not take part in concurrent execution: no `await`, no lock that can park, no `checkpoint()` there. Debug builds assert; release builds would lose completions.
- **The lane is fixed at `then()`.** Building a chain from a Background task and awaiting it from Frame works (the await boosts it), but a chain nobody awaits stays in the lane it was built in.
- **`then` and `await` need `std::move`.** Both consume the future (`then` is `&&`-qualified); using the moved-from future afterwards asserts.
- **Your continuations never run inline** (only the engine's forwarder does). Code that resolves and then expects the continuation's side effect before the next line is wrong, even if `then` was registered first.
- **Affine threads resolve, they do not await.** `await` parks on a `Signal`, which asserts on an affine thread; the platform and IO threads hand results over by resolving a promise.
- **Keep the promise alive until you resolve it.** Moving it into a lambda that is never called breaks it with `eDropped`, which is better than a hang but still a bug.
- **Capture size is a compile-time limit** of 64 bytes for `fn` plus one `Arci`; prefer capturing handles over large values.
- **`Send` is shallow.** It catches `Rc<T>` and `ptr<void>` directly, not when they hide inside your own struct; declare `using not_send = void;` on such types.
