# Fibers and Workers

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), 2026-11-16
**Modules**: `Engine.Scheduler` ([`CompScheduler`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/CompScheduler.cpp), [`Process/Schedule`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Process/Schedule.cpp), [`Worker/Worker`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Worker/Worker.cpp), [`Fiber/Fiber`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Fiber/Fiber.cpp), [`Fiber/FiberPool`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Fiber/FiberPool.cpp), [`Fiber/Park`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Fiber/Park.cpp), [`Task/Task`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Task/Task.hpp))
**Related**: [worker policy design](../../architecture/worker-policy-design.md) (PR [#181](https://github.com/Heliogrim/Heliogrim-Engine/pull/181)), [waitables design](../../architecture/scheduler-waitable-design.md) section 6.2 (the park handshake), [lane policy exploration](../../architecture/lane-policy-exploration.md), [fiber scheduler exploration](../../architecture/fiber-scheduler-exploration.md)

How a task gets from `exec` onto a worker, what the worker does with the fiber afterwards, and how idle workers park and wake. Part of the [fiber scheduler](index.md); waiting on things is on the [waitables page](waitables.md), the frame stages on the [task graph page](task-graph.md).

## Vocabulary

| Type | What it is |
|------|------------|
| `CompScheduler` | the engine's `Scheduler` module: owns the workers, the fiber pool, the `Schedule` and the `CompositePipeline` |
| `Schedule` | four FIFO work sets by priority, plus the park word (`_pushEpoch`) and a count of queued tasks (`_queued`) |
| `FifoWorkSet` | one set: a `Queue` of task pointers behind an `UnfairSpinLock` |
| `Worker` | one OS thread converted to a fiber, running `Worker::handle` |
| `TaskDelegate` | the base of every task: type, `TaskMask`, the attached fiber, an optional `TaskCtrl`, an optional `CancellationToken` |
| `Task`, `RepetitiveTask`, `BatchTask` | `void()`, `bool()` (repeat while it returns true) and `void(u32)` bodies in a `std::function` |
| `TaskMask` | priority: `eCritical`, `eHigher`, `eNormal`, `eLower` (`eAll` = every bit) |
| `Fiber` | control block: Win32 fiber handle, parent (the worker fiber to return to), task, schedule, `ParkNode`, cancellation token |
| `FiberPool` | ring buffer of reusable fibers, shared by all workers |
| `ParkNode` | the fiber's (or plain thread's) entry in a wait queue; its `state` decides who re-queues a parked task |

## Starting the workers

`CompScheduler::setup(workers_, reserve_)` creates the `Schedule` and the `CompositePipeline`, computes the worker count, constructs every worker with `TaskMask::eAll` and starts its thread. The engines pass two config values, both `0` (auto) unless code sets them:

```cpp
// Editor.Core/EditorEngine.cpp
_scheduler->setup(
	_config.getOrDefault<u32>(engine::cfg::SchedulerConfigProperty::eWorkerCount, 0u).value_or(0u),
	_config.getOrDefault<u32>(engine::cfg::SchedulerConfigProperty::eWorkerReserve, 0u).value_or(0u)
);
```

The auto count leaves a logarithmic share of the machine to everything else:

```cpp
static u32 effectiveReserve(const u32 logical_, const u32 reserve_) noexcept {
	return reserve_ != 0uL ? reserve_ : static_cast<u32>(std::bit_width(logical_) - 1) + hot_thread_count;
}

u32 scheduler::autoWorkerCount(const u32 logical_, const u32 reserve_) noexcept {
	const auto reserve = effectiveReserve(logical_, reserve_);
	return logical_ > reserve ? logical_ - reserve : 1uL;
}
```

| Logical threads | Reserve | Workers |
|---|---|---|
| 4 | 2 | 2 |
| 8 | 3 | 5 |
| 16 | 4 | 12 |
| 24 | 4 | 20 |
| 64 | 6 | 58 |

`hot_thread_count` is `0`: no engine thread outside the workers runs continuously yet. Precedence: a non-zero `workers_` wins over auto; the build macros `USE_WORKER_COUNT` and `USE_WORKER_RESERVE` override both. `setup` logs the result once, for example `Scheduler starts 20 workers (24 logical threads, reserve 4, source: auto)`. All workers run at normal OS priority.

## Submitting a task

Ways in, from lowest to highest level:

| Call | Where | Notes |
|------|-------|-------|
| `Scheduler::exec(task)` | `Scheduler.hpp` | pushes a `TaskDelegate` into the `Schedule` |
| `Scheduler::exec(task, token)` | `Scheduler.hpp` | stores a `CancellationToken` on the task first |
| `scheduler::exec(fn)` / `exec(task)` | `Engine.Scheduler/Async.hpp` | free functions over `Engine::getEngine()->getScheduler()` |
| `scheduler::execOnStage(fn, stage)` | `Engine.Scheduler/Async.hpp` | queues the task on a frame stage's slot; it runs when that stage is next dispatched ([task graph](task-graph.md)) |
| `hg::execute(fn)` | `Heliogrim/Async/Execute.hpp` | public surface; always `eNormal` |
| `hg::async(fn, mask)` | `Engine.Async/Future/Async.hpp` | returns a future, see [futures](futures.md) |

A task is made with `task::make_task(fn, mask)` (default `eNormal`), `make_repetitive_task` or `make_batch_task`, and is heap-allocated. The handle you get is a raw `non_owning_rptr<const TaskDelegate>`. **The task owns itself**: after its body runs, `TaskDelegate::delegate()` deletes it (or hands it to its `TaskCtrl`, which is how the frame runner keeps stage tasks). Never touch a task pointer after `exec`.

```cpp
s_->exec(
	task::make_task(
		[&] {
			++finished;
			counter.done();
		}
	)
);
```

Body types as built:

- `Task`: runs once, then deleted.
- `RepetitiveTask`: runs, and if the body returns `true` it is pushed again through `Engine::getEngine()->getScheduler()->exec(this)` (or its `TaskCtrl`); on `false` it is deleted.
- `BatchTask`: calls the body once with index `0`. The split into N batches is a `TODO`.

## Priorities and lanes

`Schedule::push` files a task by its mask; the highest set bit wins (`maskToPriority`), so a mask of `eAll` counts as critical. `Schedule::pop(mask, task)` starts at the worker's own priority and walks **down**, never up. Every worker is built with `eAll`, so every worker scans `eCritical`, `eHigher`, `eNormal`, `eLower` in that order and takes the first task it finds.

Frame stages choose a lane in their `StageDecl` (`eCritical`, `eNormal`, `eBackground`). At `finalize()` the runner maps the lane to a mask with `graph::toMask` (`eCritical` to `eCritical`, `eBackground` to `eLower`, otherwise `eNormal`) and every task dispatched for that stage gets the mask stamped over whatever it asked for:

```cpp
// CompositeSlot::dynamicEnqueue
// the lane is a property of the stage, so the slot stamps it over whatever the stage asked for
const_cast<ptr<task::TaskDelegate>>(task_)->mask() = _mask;
```

**Ageing.** After every completed stage, `CompositePipeline::complete` calls `Schedule::tick()`, which moves the whole content of each set one step up:

```cpp
void Schedule::tick() {
	transfer(task::TaskMask::eHigher, task::TaskMask::eCritical);
	transfer(task::TaskMask::eNormal, task::TaskMask::eHigher);
	transfer(task::TaskMask::eLower, task::TaskMask::eNormal);
}
```

So nothing pushes `eHigher` directly; it is reached only by ageing, and any queued task is critical a few stage completions after it was queued, where it sits next to the next frame stage. The lane exploration plans to remove this; it is still the behaviour today.

## The worker loop

`Worker::handle` is the whole worker. Trimmed to the essentials (asserts and the debug hook removed):

```cpp
while (not worker->_interrupt.load(std::memory_order::acquire)) [[likely]] {
	// Load the epoch before the pop, so a push ordered after the pop moves it and the wait returns
	const auto epoch { schedule->epoch() };
	task = nullptr;

	if (schedule->pop(mask, task)) {
		// Cascade: wake one peer for the work left behind
		if (schedule->queued() > 0) {
			schedule->wakeOne();
		}

		launcher.self = task->fiber();
		if (launcher.self == nullptr) {
			launcher.self = pool.acquire();
			launcher.self->task = task;
			launcher.self->schedule = schedule;
			launcher.self->cancellation = fiber::CancellationToken { task->cancellation() };
			const_cast<ptr<task::TaskDelegate>>(task)->fiber() = launcher.self;
		}

		launcher.self->parent = fiber;
		launcher();                         // SwitchToFiber; returns when the fiber yields

		if (launcher.self->task != nullptr) {
			// Plain yield reschedules; a parked fiber is requeued by unpark, or here if unpark already ran
			auto& st = launcher.self->parkNode.state;
			if (st.load(std::memory_order::relaxed) == ParkNode::State::eIdle) {
				schedule->push(std::move(task));
			} else if (st.exchange(ParkNode::State::eParked, std::memory_order::acq_rel) == ParkNode::State::eWoken) {
				schedule->push(std::move(task));
			}
		} else {
			launcher.self->cancellation.reset();
			pool.release(std::move(launcher.self));
		}

	} else {
		if (worker->_interrupt.load(std::memory_order::acquire)) {
			break;
		}
		schedule->waitForWork(epoch);
	}
}
```

After the switch returns there are three cases:

| Fiber state after the switch | Meaning | Worker action |
|---|---|---|
| `task == nullptr` | the body finished (the launch pad clears `task` and yields) | release the fiber to the pool |
| `task != nullptr`, node `eIdle` | plain `yield()` | push the task back |
| `task != nullptr`, node armed | the fiber parked on a waitable | exchange the node to `eParked`; if the completer already set `eWoken`, push the task back now, otherwise leave it to `unpark` |

The last row is the park handshake. The completer side lives in `scheduler::unpark` (`Fiber/Park.cpp`); both sides use one atomic exchange on the same word, so exactly one of them re-queues the task. Details on the [waitables page](waitables.md#parking).

## Fibers

- **Creation**: `FiberPool::acquire` first tries the ring buffer (`acquireReuse`), then `new Fiber` with `CreateFiber(default_fiber_stack_size(), &FiberLaunchPad::launch, fiber)`. `default_fiber_stack_size()` is 4096 bytes on MSVC; Win32 takes that as the initial commit, the reserve is the executable default.
- **Running**: `FiberLaunchPad::launch` loops: run `task->delegate()`, set `task = nullptr`, `yield()` back to the parent. When the fiber is reused for the next task, the loop runs again.
- **Suspended**: a task that yields or parks keeps its fiber (`TaskDelegate::fiber()`); the next pop of that task switches to the same fiber, on whichever worker popped it. **A fiber can resume on a different OS thread.**
- **Release**: `FiberPool::release` puts the fiber back into the ring, or destroys it if the ring is full or another thread is releasing at that moment. The ring holds `hardware_concurrency() * 4` fibers.
- **Who am I**: `fiber::self::current()` returns the running task's `Fiber`, or `nullptr` on a plain thread and on a worker's own root fiber (it was converted with `ConvertThreadToFiber(nullptr)`). The waitables use this to choose the fiber or the thread path.

## Park and wake

Idle workers park in the kernel on `Schedule::_pushEpoch` with `WaitOnAddress`. The rules from the worker policy design, as built in `Schedule.cpp`:

```cpp
bool Schedule::push(const non_owning_rptr<const task::TaskDelegate> task_) {
	const auto mask = task_->mask();
	const u64 priorityIdx = maskToPriority(mask);

	// Count first: a worker may pop right after the insert, and its fetch_sub must not wrap below zero.
	_queued.fetch_add(1uLL, std::memory_order::acq_rel);
	if (not _workSets[priorityIdx]->push(task_)) {
		_queued.fetch_sub(1uLL, std::memory_order::acq_rel);
		return false;
	}

	_pushEpoch.fetch_add(1uL, std::memory_order::release);
	if (not thread::self::isWorker()) {
		wakeOne();
	}
	return true;
}
```

- **Every push bumps the epoch.** A worker loads the epoch **before** its pop and waits only while the epoch is unchanged, so a push that lands between the pop and the wait makes the wait return at once.
- **Only pushes from non-worker threads wake** (`WakeByAddressSingle`). A worker that pushes (a stage dispatch, a re-push after yield, an `unpark` on a worker, `exec` from a task) pops next itself.
- **The cascade.** A worker that pops and still sees `_queued > 0` wakes one peer before running its task. A fan-out of N tasks from one worker therefore wakes workers one by one, each paying for one wake.
- **Ageing transfers** bump the epoch but wake nobody; that is sound only because `tick()` runs on a worker (comment in `Schedule::transfer`).
- **Stop**: `CompScheduler::destroy` waits until every worker is `ready()`, calls `requestStop()` on all of them, then `Schedule::wakeAll()` (epoch bump plus `WakeByAddressAll`), then joins.

Measured effect (worker policy design, section 10): an idle editor went from 22.14 busy cores to 0.93 on a 24-thread machine; what remains is the unpaced frame chain.

## Cancellation

`Scheduler::exec(task, token)` attaches a `CancellationToken` (`Arci<const CancellationSource>`). The worker copies it into the fiber on first launch; inside the task, `fiber::self::cancellationRequested()` reads it. Cancellation is poll-only: nothing interrupts a running or parked task, and the task decides where to check.

## Debugging

| Symptom | Where to look |
|---------|---------------|
| `Failed to push task.` and a breakpoint (debug) | `CompScheduler::exec`: a work-set push failed; `FifoWorkSet::push` cannot fail today, so a custom work set is the suspect |
| A task never runs, every worker idle | the task is parked and its waitable was never completed (a promise kept alive, a `JoinCounter` short of a `done()`); check the waitable, not the worker |
| `Can not release spin lock, which belongs to other thread.` | an `UnfairSpinLock` was held across a yield or park and the fiber resumed on another worker |
| Assert `fiber != nullptr` in `self::yield` | `hg::yield()` called on a plain thread |
| CPU busy while idle | a fiber that waits by looping on `yield()` keeps one worker cycling; use a waitable |

`worker::debugPostSwitchHook` (debug builds, `Fiber/Park.hpp`) is called by every worker right after a fiber switches back; tests use it to force the park races.

## Limits and known issues

- **No lane policy.** Four sets plus ageing; `eHigher` exists only as an ageing step; nothing caps background work while the frame is busy.
- **No per-worker queues, no stealing.** All workers contend on the four spin locks of the global sets.
- **`delay` ignores its ticks** (`CompScheduler::delay` calls `exec`). `hg::delay` is `todo_panic`; `hg::sleep` sleeps the OS thread in debug and is `todo_panic` in release.
- **`execOnStages(begin, end)` ignores `end`** and queues on `begin` (a `TODO`).
- **`BatchTask` is not split**; the body runs once with index 0.
- **`CompScheduler::wait()`** joins the worker threads; it returns only after the workers were stopped.
- **POSIX**: the `ucontext` branches compile in places, but `fiber::self::current()` is `todo_panic` and `WaitOnAddress` is called unguarded.

## Changing it

Tests (`Heliogrim-Engine.Scheduler.Test`):

- `WorkerPolicy.cpp`: `AutoWorkerCountTable`, idle workers stop using CPU, `exec` wakes a parked worker, bursts from a plain thread, fan-out from a worker reaches parked peers, `unpark` from a plain thread, destroy with parked workers, and a stress run of bursts with parking.
- `Schedule.cpp`: pop walks down and never up, `tick` promotes every set and keeps FIFO order, push bumps epoch and queued, `waitForWork` returns on push and on a moved epoch, `transfer` bumps only when it moved tasks, `wakeAll` releases every waiter.
- `Park.cpp`: `fiber::self::current()` on threads and in tasks, the two orders of the park handshake (`UnparkBeforeWorkerParkedRunsOnce`, `UnparkAfterWorkerParkedRunsOnce`), plain yield still reschedules.
- `Cancellation.cpp`, `test.cpp` (`RuntimeTest.PrioritySorting` with one worker).
- Model: `Process/Schedule.tla` + `.cfg` covers push, pop, transfer, epoch, cascade and stop. It passes fully at 2 workers and 2 tasks. Any change to the order "load epoch, pop, wait" or to who wakes on push must be re-checked there; the design's mutations (epoch loaded after the pop, no wake in `wakeAll`, no cascade) must still fail.

Tests boot a minimal engine (`TestSchedulerEngine.hpp`, `structuredRuntimeTest`) because the free `exec` functions and futures go through `Engine::getEngine()`.

### Pitfalls

- **No thread identity across a suspension.** After `yield`, `await`, a contended `FiberMutex` or any park, the task may continue on another OS thread. `thread_local` values read before and after differ, `thread::self::getId()` changes, and `UnfairSpinLock` (owned by thread id) throws on release. Hold only ownerless locks (`SpinMutex`) and never across a suspension point.
- **Never block a worker.** A `std::mutex`, `std::condition_variable`, `Sleep` or blocking IO inside a task takes the whole worker out. Use the [waitables](waitables.md); put blocking third-party calls on an [affine thread](affine-threads.md).
- **Do not spin-wait on another task.** If every worker spins on a flag that a queued task would set, nothing runs that task. Parking is the only safe wait.
- **Task pointers are dead after `exec`.** The task deletes itself when it finishes, which can happen before `exec` returns.
- **Masks do not isolate.** Every worker takes every set; a mask is a priority, not a worker group. And until ageing goes, an `eLower` task does not stay low.
- **Wake rules depend on `isWorker()`.** Code that pushes from a new kind of thread gets a wake automatically; code that pushes from a worker relies on that worker popping next. Calling `Schedule::tick()` from a non-worker would need a `wakeOne` (see the comment in `Schedule::transfer`).
- **Small fiber stacks.** The commit is 4 KiB; deep recursion or large stack arrays in a task touch guard pages and grow the stack on the fly, and the reserve is fixed per fiber.
