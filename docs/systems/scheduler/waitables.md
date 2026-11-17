# Waitables and Locks

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), 2026-11-16
**Modules**: `Engine.Scheduler` ([`Fiber/Park`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Fiber/Park.cpp), [`Waitable/ParkQueue`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Waitable/ParkQueue.hpp), [`Waitable/Signal`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Waitable/Signal.cpp), [`Waitable/JoinCounter`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Waitable/JoinCounter.cpp)), `Engine.Async` ([`Primitive/FiberMutex`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Primitive/FiberMutex.cpp), [`Primitive/FiberSharedMutex`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Primitive/FiberSharedMutex.cpp), [`Primitive/SpinLock`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Primitive/SpinLock.hpp), [`Lock/UniqueLock`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Lock/UniqueLock.hpp), [`Lock/SharedLock`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Lock/SharedLock.hpp)), `Heliogrim/Async` (`Await.hpp`, `Waitable.hpp`)
**Related**: [waitables design](../../architecture/scheduler-waitable-design.md) (PRs [#159](https://github.com/Heliogrim/Heliogrim-Engine/pull/159), [#165](https://github.com/Heliogrim/Heliogrim-Engine/pull/165); section 13 is PR [#185](https://github.com/Heliogrim/Heliogrim-Engine/pull/185)), [promise and future design](../../architecture/promise-future-design.md)

How a task waits without holding a worker, and which primitive to pick. Part of the [fiber scheduler](index.md); the worker side of the handshake is on [fibers and workers](fibers-and-workers.md#the-worker-loop).

## Which one to use

| You need to | Use | Header |
|-------------|-----|--------|
| wait until one thing has happened once | `Signal` (`hg::Signal`) | `Engine.Scheduler/Waitable/Signal.hpp` |
| wait until N tasks have finished | `JoinCounter` (`hg::JoinCounter`) | `Engine.Scheduler/Waitable/JoinCounter.hpp` |
| wait for a value or an error from another task | `Future` / `Promise` ([futures](futures.md)) | `Engine.Async/Future/*.hpp`, `Heliogrim/Async/Future.hpp` |
| guard state that a task may hold across a suspension, or for long | `FiberMutex` | `Engine.Async/Primitive/FiberMutex.hpp` |
| the same, with many readers | `FiberSharedMutex` | `Engine.Async/Primitive/FiberSharedMutex.hpp` |
| guard a few instructions, never suspending inside | `concurrent::SpinMutex` + `SpinLock` | `Engine.Async/Primitive/SpinLock.hpp` |
| RAII around any of the mutexes | `concurrent::UniqueLock`, `concurrent::SharedLock` | `Engine.Async/Lock/*.hpp` |

All parking primitives work from a fiber and from a plain thread; the caller does not say which. Avoid `std::mutex`, `std::condition_variable` and `UnfairSpinLock` in code that may run on a fiber (see [Pitfalls](#pitfalls)).

## Parking

Every waiter owns one `ParkNode`:

```cpp
struct ParkNode {
	enum class State : u8 {
		eIdle,
		eArmed,
		eParked,
		eWoken
	};

	std::atomic<State> state { State::eIdle };
	ptr<ParkNode> next = nullptr;
	ptr<fiber::Fiber> fiber = nullptr;
	std::atomic<u32> threadFlag { 0 };
};
```

`currentParkNode()` returns the node embedded in the running fiber, or a `thread_local` node on a plain thread (plain threads never migrate, so the node stays valid). A primitive uses it in three steps: arm the node (`eArmed`), push it onto its `ParkQueue` under the queue lock, then call `park(node)`.

- **Fiber**: `park` yields to the worker. The worker sees the armed node and exchanges it to `eParked`. The completer calls `unpark(node)`, which exchanges it to `eWoken`. Whoever sees the other's value pushes the task back into the schedule: the completer if it found `eParked`, the worker if it found `eWoken`. One atomic exchange per side, so the task is re-queued exactly once and never while its fiber is still running.
- **Thread**: `park` waits on `threadFlag` with `atomic::wait`; `unpark` stores 1 and calls `notify_one`.

```cpp
void hg::engine::scheduler::unpark(ref<ParkNode> node_) noexcept {
	if (node_.fiber == nullptr) {
		node_.threadFlag.store(1, std::memory_order::release);
		node_.threadFlag.notify_one();
		return;
	}

	const auto prev = node_.state.exchange(ParkNode::State::eWoken, std::memory_order::acq_rel);
	if (prev == ParkNode::State::eParked) {
		node_.fiber->schedule->push(node_.fiber->task);
	}
}
```

`ParkQueue` is an intrusive FIFO of nodes behind an `atomic_flag` spin lock, held for a few instructions and never across a suspension. Its `locked(fn)` runs `fn` under the lock with a `Locked` view, so a primitive can re-check its predicate and push in one critical section.

A parked fiber keeps its stack and occupies no worker. `Signal.ThousandParkedTasksKeepWorkersFree` parks 1,000 tasks on one signal and checks that an unrelated task still runs.

## Signal

A one-shot: `set()` once, every current and later `wait()` returns.

```cpp
class Signal {
public:
	[[nodiscard]] bool isSet() const noexcept;
	void set() noexcept;
	void wait();
	// Re-arms the one-shot; must not run concurrently with set() or wait(),
	// and only while no waiter is queued.
	void reset() noexcept;
};
```

`set()` closes the queue and takes every waiter under the lock, then stores the set state, then unparks the waiters (reading each `next` first). The state store is the setter's last access to the object. `wait()` returns at once if set; otherwise it pushes its node unless the queue is already closed, in which case it spins briefly until the setter's store lands.

Lifetime rule (from the header, checked by `Signal.tla`): a `Signal` may be destroyed only once **every** waiter has returned from `wait()`, the same rule as `std::latch`. In practice the owner destroys it after its own `wait()`, never a waiter that shares it.

`Signal` is what `CompositePipeline::stop()` parks on and what every `FutureState` completes through.

## JoinCounter

Fork-join over a `Signal`. The constructor sets the count to `children + 1`; the extra one is the creator's guard, so children that finish early cannot complete the counter while the creator is still starting more.

```cpp
JoinCounter::JoinCounter(const u32 children_) noexcept :
	_pending(children_ + 1) {}

void JoinCounter::done() noexcept {
	const auto prev = _pending.fetch_sub(1, std::memory_order_acq_rel);
	::hg::assertd(prev != 0);
	if (prev == 1) {
		_done.set();
	}
}

void JoinCounter::wait() {
	::hg::assertd(not _waited);
	_waited = true;
	done();
	_done.wait();
}
```

- Each child calls `done()` exactly once.
- `add(n)` raises the count; call it **before** the matching children start.
- `wait()` is the creator's call and runs once: it drops the guard, then waits. Other parties can poll `isDone()`.

`hg::await(ref<JoinCounter>)` and `hg::await(ref<Signal>)` in `Heliogrim/Async/Await.hpp` are the same as calling `wait()`.

## FiberMutex

An exclusive mutex that spins up to 32 times with `_mm_pause`, then parks. The word holds `eLocked` and `eContended`; `eContended` is set exactly when the wait queue is non-empty, and both change only under the queue lock.

- `lock()`: bounded spin on `try_lock`, then under the queue lock re-check; take it if free, else set `eContended` with a CAS (a failed CAS restarts, so the bit is never set on a free mutex), push the node, park. A woken waiter loops back to the top and competes again; the mutex does not hand off.
- `unlock()`: exchange the word to 0; if it was contended, pop one waiter under the queue lock, re-set `eContended` if more remain, unpark it.

The mutex is not fair (a running task can barge past a woken one), not recursive, and has no owner, so it may be unlocked on a different OS thread from the one that locked it, which happens whenever the holder migrates.

## FiberSharedMutex

Reader/writer mutex with two queues and **ownership handoff**: a parked reader or writer that is woken already holds the lock.

- Word: bit 31 `eWriter`, bit 30 `eWriterWaiting`, bits 0 to 29 the reader count.
- A writer that has to wait sets `eWriterWaiting`; new readers then go to the slow path and queue behind it.
- `unlock()` (writer) alternates between the queues: if readers are queued and either no writer is queued or a writer was served last, the whole reader batch is admitted in one `fetch_sub`; otherwise one writer is handed the lock.
- The last reader out, with `eWriterWaiting` set, hands the lock to the first queued writer.

```cpp
// unlock(): alternate between the queues so neither side starves under a steady stream of the other.
if (not readers_.empty() && (writers_.empty() || not _readersLast)) {
	_readersLast = true;
	batch = readers_.takeAll();
	// ... count n
	// Clears eWriter and admits the whole batch in one step; eWriterWaiting stays.
	_word.fetch_sub(eWriter - n, std::memory_order::acq_rel);
	return;
}
```

There is no upgrade: a task holding the shared lock that calls `lock()` deadlocks with itself.

Usage, from the Accel variant cache (`Engine.Accel.Lang/Ir/Variant.cpp`):

```cpp
smr<const Resolved> VariantCache::find(ref<const VariantKey> key_) const noexcept {
	const concurrent::SharedLock lock { _lck };
	const auto iter = _entries.find(key_);
	return iter != _entries.end() ? iter->second : smr<const Resolved> {};
}
```

Both fiber mutexes carry Clang thread-safety attributes (`HG_CAPABILITY`, `HG_ACQUIRE`, ...); the clang build warns on unlocked access to guarded fields.

## Lock types and spin locks

- `UniqueLock<M>` and `SharedLock<M>` are drop-ins for `std::unique_lock` / `std::shared_lock` without including `<mutex>`: `defer_lock`, `try_to_lock`, `adopt_lock`, move, `release`, `swap`, CTAD (`UniqueLock lock { mtx }`). Misuse (locking twice, unlocking unowned) calls `hg::breakpoint()`, which traps in debug builds and does nothing in release.
- `SpinMutex` is `std::atomic_flag`; `SpinLock` is its RAII guard. Ownerless, so safe across threads, but it spins: never park or yield while holding it. Misuse throws `std::runtime_error`.
- `UnfairSpinLock` records the OS thread id as owner and throws if another thread releases it. It guards the schedule's work sets, where nothing suspends. Do not use it in task code.

## Debugging

| Symptom | Where to look |
|---------|---------------|
| Assert in `Signal::wait` on `not thread::self::isAffine()` | an [affine thread](affine-threads.md) tried to park on a `Signal`; affine threads must not block on scheduler work |
| Assert `_state == 0` in `Signal::set` | a second `set()` without `reset()` |
| Assert `locked_.empty()` in `Signal::reset` | `reset()` while a waiter is still queued |
| Assert `not _waited` in `JoinCounter::wait` | `wait()` called twice, or by a second party |
| Assert `prev != 0` in `JoinCounter::done` | more `done()` calls than children plus guard |
| A task hangs in `wait()` forever | a child never called `done()`, or `add()` came after a child already finished |

The debug-only `worker::debugPostSwitchHook` lets a test run code between the fiber's yield and the worker's handshake step; `Park.cpp` in the tests uses it to force both orders.

## Limits and known issues

- **No timeouts and no withdrawal.** A parked waiter stays until it is unparked; there is no `try_lock_for`, no `wait_for`, and cancellation does not wake a parked task.
- **No `when_any`.** A node can be in one queue at a time.
- **Unbounded fiber memory.** Every parked task holds a fiber stack; nothing caps the pool.
- **`FiberMutex` does not hand off**, so a woken waiter can lose to a barger and park again; FIFO wake order bounds how often.

## Changing it

Tests:

- `Heliogrim-Engine.Scheduler.Test`, `Waitable.cpp`: `ParkQueue` order, splice, locked push, concurrent push and pop; `Signal` inline wait, reset, thread waiting for a task, 1,000 parked tasks, set-and-destroy race; `JoinCounter` completion, guard, child finishing before the next `add`; `AffineFlag.SignalWaitOnAffineThreadAsserts`; `PublicAwait.EventOverloadParksTask`. `Park.cpp`: both handshake orders and plain yield.
- `Heliogrim-Engine.Async.Test`: `FiberMutex.cpp` (eight fibers counting exactly, thread and fiber alternating, three waiters all wake), `FiberSharedMutex.cpp` (readers overlap, writer excludes readers, writer acquires under steady reads, late readers wait behind a writer, two queued writers, reader batch holds before the next writer), `Lock.cpp` (typed tests over both lock types), `SpinLock.cpp`.
- Models beside the sources: `Signal.tla`, `JoinCounter.tla`, `FiberMutex.tla`, `FiberSharedMutex.tla`. Any change to a primitive's atomics follows the `verifying-concurrency` skill: update the model, re-run TLC, and check that the documented mutations still fail.

### Pitfalls

- **Read `next` before `unpark`.** A woken fiber can re-park at once and overwrite its node's `next`. Every primitive walks its list this way; a new primitive must too.
- **Arm, push, then park, in that order, with the push under the queue lock** together with the predicate re-check. Pushing outside the lock, or checking the predicate after releasing it, loses wake-ups.
- **One wait per waiter at a time.** A fiber has one `ParkNode`; a thread has one `thread_local` node. Nested waits from inside a primitive's callback are not possible.
- **`Signal` lifetime is the latch rule**, not "after my `wait()` returned". If several tasks wait on a stack `Signal`, the owner must outlive all of them.
- **`JoinCounter::wait()` belongs to the creator.** It consumes the guard; a second waiter would underflow the count.
- **Do not hold a spin lock across a suspension.** If the holder parks and every worker spins on that lock, nothing resumes the holder.
- **Affine threads do not park on `Signal`** (debug assert). `FiberMutex` has no such assert; on an affine thread it blocks that thread.
- **No reentrancy.** Neither fiber mutex is recursive, and `FiberSharedMutex` has no shared-to-exclusive upgrade.
