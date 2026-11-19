# Fibers and Workers

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), 2026-11-16; worker setup, submission, lanes, the worker loop, park and wake, limits and tests re-checked at [`fd5affa5`](https://github.com/Heliogrim/Heliogrim-Engine/tree/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab), 2026-11-19
**Modules**: `Engine.Scheduler` ([`CompScheduler`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/CompScheduler.cpp), [`Process/Schedule`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Process/Schedule.cpp), [`Worker/Worker`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Worker/Worker.cpp), [`Fiber/Fiber`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Fiber/Fiber.cpp), [`Fiber/FiberPool`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Fiber/FiberPool.cpp), [`Fiber/Park`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Fiber/Park.cpp), [`Task/Task`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Task/Task.hpp))
**Related**: [worker policy design](../../architecture/worker-policy-design.md) (PR [#181](https://github.com/Heliogrim/Heliogrim-Engine/pull/181)), [waitables design](../../architecture/scheduler-waitable-design.md) section 6.2 (the park handshake), [lane policy design](../../architecture/lane-policy-design.md) (PR [#208](https://github.com/Heliogrim/Heliogrim-Engine/pull/208)), [lanes and priority](lanes.md), [fiber scheduler exploration](../../architecture/fiber-scheduler-exploration.md)

How a task gets from `exec` onto a worker, what the worker does with the fiber afterwards, and how idle workers park and wake. Part of the [fiber scheduler](index.md); waiting on things is on the [waitables page](waitables.md), the frame stages on the [task graph page](task-graph.md).

## Vocabulary

| Type | What it is |
|------|------------|
| `CompScheduler` | the engine's `Scheduler` module: owns the workers, the fiber pool, the `Schedule` and the `CompositePipeline` |
| `Schedule` | three FIFO work sets, one per lane, plus the park word (`_pushEpoch`), a queued depth per lane (`_depth`) and the lane policy state (floors, reserve, running counts; see [lanes](lanes.md)) |
| `FifoWorkSet` | one set: a `Deque` of task pointers behind an `UnfairSpinLock`; besides `push` and `pop` it can `erase` one entry for the wait boost |
| `Worker` | one OS thread converted to a fiber, running `Worker::handle` |
| `TaskDelegate` | the base of every task: type, `Lane`, the attached fiber, an optional `TaskCtrl`, an optional `CancellationToken`, plus `queuedAt` (Frame wait metric) and `boostCell` (written by `pushBoostable`) |
| `Task`, `RepetitiveTask`, `BatchTask` | `void()`, `bool()` (repeat while it returns true) and `void(u32)` bodies in a `std::function` |
| `Lane` | `eFrame`, `eInteractive`, `eBackground`, highest first; `eInherit` is a request resolved at creation and never queued ([lanes](lanes.md)) |
| `Fiber` | control block: Win32 fiber handle, parent (the worker fiber to return to), task, schedule, bound `BoostCell` (`boost`), `ParkNode`, cancellation token, `sliceStart` |
| `FiberPool` | ring buffer of reusable fibers, shared by all workers |
| `ParkNode` | the fiber's (or plain thread's) entry in a wait queue; its `state` decides who re-queues a parked task |

## Starting the workers

`CompScheduler::setup(workers_, reserve_, lanes_)` creates the `Schedule` and the `CompositePipeline`, computes the worker count, sets the schedule up with the count and the lane policy, constructs every worker over the shared schedule and starts its thread. Workers have no mask; every worker takes every lane. The engines pass two config values, both `0` (auto) unless code sets them, and the lane policy read by `LanePolicyConfig::fromConfig` ([lanes](lanes.md#configuration)):

```cpp
// Editor.Core/EditorEngine.cpp
_scheduler->setup(
	_config.getOrDefault<u32>(engine::cfg::SchedulerConfigProperty::eWorkerCount, 0u).value_or(0u),
	_config.getOrDefault<u32>(engine::cfg::SchedulerConfigProperty::eWorkerReserve, 0u).value_or(0u),
	engine::scheduler::LanePolicyConfig::fromConfig(_config)
);
```

`eWorkerReserve` is the share of the machine left to other threads; it is not the Frame reserve of the lane policy (`eLaneReserve`).

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
| `Scheduler::exec(task)` | `Scheduler.hpp` | resolves the task's lane (`resolveLane`), then pushes it into the `Schedule` |
| `Scheduler::execResolved(task)` | `Scheduler.hpp` | pushes with the lane the task already has |
| `Scheduler::execBoostable(task, cell)` | `Scheduler.hpp` | pushes in the higher of the task's and the cell's lane; used by future continuations ([lanes](lanes.md#wait-boost)) |
| `Scheduler::exec(task, token)` | `Scheduler.hpp` | stores a `CancellationToken` on the task first |
| `scheduler::exec(fn)` / `exec(task)` | `Engine.Scheduler/Async.hpp` | free functions over `Engine::getEngine()->getScheduler()` |
| `scheduler::execOnStage(fn, stage)` | `Engine.Scheduler/Async.hpp` | queues the task on a frame stage's slot; it runs when that stage is next dispatched ([task graph](task-graph.md)) |
| `hg::execute(fn)` | `Heliogrim/Async/Execute.hpp` | public surface; always `eInherit` |
| `hg::async(fn, lane)` | `Engine.Async/Future/Async.hpp` | returns a future, see [futures](futures.md) |

A task is made with `task::make_task(fn, lane)` (default `eInherit`), `make_repetitive_task` or `make_batch_task`, and is heap-allocated. `exec` resolves `eInherit` to the caller's lane: a child inherits its parent's lane and may go lower, never higher; a plain thread gets `eInteractive` ([lanes](lanes.md#using-it)). The handle you get is a raw `non_owning_rptr<const TaskDelegate>`. **The task owns itself**: after its body runs, `TaskDelegate::delegate()` deletes it (or hands it to its `TaskCtrl`, which is how the frame runner keeps stage tasks). Never touch a task pointer after `exec`.

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

## Lanes

`Schedule::push` files a task in the work set of its lane (the enum value is the index; `eInherit` asserts). `Schedule::pop(now, task, lane)` takes a floor turn of a lower lane if one is due, else Frame, else a lower lane if the Frame reserve leaves a worker for it, and returns the lane it counted. Every worker takes every lane. Nothing ages: a queued task stays in its lane until it runs or a wait boost moves it. The policy (floors, reserve, slices, boost) is on its own page, [lanes and priority](lanes.md).

Every frame stage is Frame. `StageDecl` has no lane; the slot stamps `eFrame` on every task it enqueues:

```cpp
// CompositeSlot::dynamicEnqueue
// every stage is Frame, so the slot stamps it over whatever the stage asked for
const_cast<ptr<task::TaskDelegate>>(task_)->lane() = Lane::eFrame;
```

## The worker loop

`Worker::handle` ([`Worker.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Worker/Worker.cpp)) is the whole worker. Trimmed to the essentials (asserts and the debug hook removed):

```cpp
while (not worker->_interrupt.load(std::memory_order::acquire)) [[likely]] {
	// Load the epoch before the pop, so a push ordered after the pop moves it and the wait returns
	const auto epoch { schedule->epoch() };
	task = nullptr;

	if (schedule->pop(std::chrono::steady_clock::now(), task, lane)) {
		// Cascade: wake one peer for the work left behind
		if (schedule->queued() > 0) {
			schedule->wakeOne();
		}

		launcher.self = task->fiber();
		if (launcher.self == nullptr) {
			launcher.self = pool.acquire();
			launcher.self->task = task;
			launcher.self->boost = nullptr;
			launcher.self->schedule = schedule;
			launcher.self->cancellation = fiber::CancellationToken { task->cancellation() };
			const_cast<ptr<task::TaskDelegate>>(task)->fiber() = launcher.self;
		}

		launcher.self->parent = fiber;
		const auto launchedAt = std::chrono::steady_clock::now();
		launcher.self->sliceStart = launchedAt;
		launcher();                         // SwitchToFiber; returns when the fiber yields
		schedule->leave(lane);              // the lane pop counted, not the task's current one
		if (lane != Lane::eFrame) {
			const auto ran = std::chrono::steady_clock::now() - launchedAt;
			schedule->noteRun(lane, static_cast<u64>(std::chrono::duration_cast<std::chrono::microseconds>(ran).count()));
		}

		if (launcher.self->task != nullptr) {
			// Plain yield reschedules; a parked fiber is requeued by unpark, or here if unpark already ran
			auto& st = launcher.self->parkNode.state;
			if (st.load(std::memory_order::relaxed) == ParkNode::State::eIdle) {
				(void)schedule->pushBoostable(task, launcher.self->boost);
			} else if (st.exchange(ParkNode::State::eParked, std::memory_order::acq_rel) == ParkNode::State::eWoken) {
				(void)schedule->pushBoostable(task, launcher.self->boost);
			}
		} else {
			launcher.self->cancellation.reset();
			launcher.self->boost = nullptr;
			pool.release(std::move(launcher.self));
		}

	} else {
		if (worker->_interrupt.load(std::memory_order::acquire)) {
			break;
		}
		// bounded while lower work is queued: a floor only falls due for a worker that pops
		schedule->waitForWork(epoch, schedule->parkTimeoutMillis(std::chrono::steady_clock::now()));
	}
}
```

After the switch returns there are three cases:

| Fiber state after the switch | Meaning | Worker action |
|---|---|---|
| `task == nullptr` | the body finished (the launch pad clears `task` and yields) | release the fiber to the pool |
| `task != nullptr`, node `eIdle` | plain `yield()` or a `checkpoint()` yield | push the task back |
| `task != nullptr`, node armed | the fiber parked on a waitable | exchange the node to `eParked`; if the completer already set `eWoken`, push the task back now, otherwise leave it to `unpark` |

The last row is the park handshake. The completer side lives in `scheduler::unpark` (`Fiber/Park.cpp`); both sides use one atomic exchange on the same word, so exactly one of them re-queues the task. Details on the [waitables page](waitables.md#parking).

Both re-queue paths (here and in `unpark`) use `pushBoostable(task, fiber->boost)`: the task goes back in the higher of its own lane and the lane of the `BoostCell` bound to its fiber, so a producer that was boosted while it ran or was parked comes back in the raised lane ([wait boost](lanes.md#wait-boost)).

## Fibers

- **Creation**: `FiberPool::acquire` first tries the ring buffer (`acquireReuse`), then `new Fiber` with `CreateFiber(default_fiber_stack_size(), &FiberLaunchPad::launch, fiber)`. `default_fiber_stack_size()` is 4096 bytes on MSVC; Win32 takes that as the initial commit, the reserve is the executable default.
- **Running**: `FiberLaunchPad::launch` loops: run `task->delegate()`, set `task = nullptr`, `yield()` back to the parent. When the fiber is reused for the next task, the loop runs again.
- **Suspended**: a task that yields or parks keeps its fiber (`TaskDelegate::fiber()`); the next pop of that task switches to the same fiber, on whichever worker popped it. **A fiber can resume on a different OS thread.**
- **Release**: `FiberPool::release` puts the fiber back into the ring, or destroys it if the ring is full or another thread is releasing at that moment. The ring holds `hardware_concurrency() * 4` fibers.
- **Who am I**: `fiber::self::current()` returns the running task's `Fiber`, or `nullptr` on a plain thread and on a worker's own root fiber (it was converted with `ConvertThreadToFiber(nullptr)`). The waitables use this to choose the fiber or the thread path.

## Park and wake

Idle workers park in the kernel on `Schedule::_pushEpoch` with `WaitOnAddress`. The rules from the worker policy design, as built in [`Schedule.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Process/Schedule.cpp):

```cpp
bool Schedule::push(const non_owning_rptr<const task::TaskDelegate> task_) {

	const auto lane = task_->lane();
	::hg::assertd(lane != Lane::eInherit);
	const u64 laneIdx = static_cast<u64>(lane);

	if (lane == Lane::eFrame) {
		task_->queuedAt = std::chrono::steady_clock::now();
	}

	// Count first: a worker may pop right after the insert, and its fetch_sub must not wrap below zero.
	// seq_cst: rollFrame reads the lower depth after its reserve store; see pop's lower step.
	const auto depth = _depth[laneIdx].fetch_add(1uLL, std::memory_order::seq_cst) + 1uLL;
	if (lane == Lane::eFrame) {
		raiseTo(_framePeak, static_cast<u32>(depth) + _frameRunning.load(std::memory_order::relaxed));
	}

	if (not _workSets[laneIdx]->push(task_)) {
		_depth[laneIdx].fetch_sub(1uLL, std::memory_order::acq_rel);
		return false;
	}

	_pushEpoch.fetch_add(1uL, std::memory_order::release);
	if (not thread::self::isWorker() || (lane == Lane::eFrame && _config.wakeOnFramePush)) {
		wakeOne();
	}
	return true;
}
```

- **Every push bumps the epoch.** A worker loads the epoch **before** its pop and waits only while the epoch is unchanged, so a push that lands between the pop and the wait makes the wait return at once.
- **Only pushes from non-worker threads wake** (`WakeByAddressSingle`). A worker that pushes (a stage dispatch, a re-push after yield, an `unpark` on a worker, `exec` from a task) pops next itself. Exception: with `LanePolicyConfig::wakeOnFramePush` (off by default) a Frame push from a worker also wakes one.
- **The cascade.** A worker that pops and still sees work queued in any lane (`queued()` sums the lanes) wakes one peer before running its task. A fan-out of N tasks from one worker therefore wakes workers one by one, each paying for one wake. A new wake rule is chunk W02.15 ([concurrency and fibers](../../plan/work/concurrency-fibers.md)).
- **Bounded park.** A worker whose pop failed while lower-lane work is queued (held back by the Frame reserve) parks only until the next floor of such a lane is due, at least 1 ms; otherwise it parks without a timeout ([lanes](lanes.md#parking-with-a-floor-due)).
- **Reserve drop.** When `rollFrame` or `resetReserve` lowers the Frame reserve while lower work is queued, they bump the epoch and wake one worker; the cascade wakes the rest.
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

- **No preemption.** A lower-lane task gives its worker back only at `hg::checkpoint()`, and nothing in the engine calls it yet; the other lane limits are on [lanes](lanes.md#limits-and-known-issues).
- **No per-worker queues, no stealing.** All workers contend on the three spin locks of the global lane sets; the wait boost's `promote` holds a lower lane's lock for a linear search.
- **`delay` ignores its ticks** (`CompScheduler::delay` calls `exec`). `hg::delay` is `todo_panic`; `hg::sleep` sleeps the OS thread in debug and is `todo_panic` in release.
- **`execOnStages(begin, end)` ignores `end`** and queues on `begin` (a `TODO`).
- **`BatchTask` is not split**; the body runs once with index 0.
- **`CompScheduler::wait()`** joins the worker threads; it returns only after the workers were stopped.
- **POSIX**: the `ucontext` branches compile in places, but `fiber::self::current()` is `todo_panic` and `WaitOnAddress` is called unguarded.

## Changing it

Tests (`Heliogrim-Engine.Scheduler.Test`):

- `WorkerPolicy.cpp`: `AutoWorkerCountTable`, idle workers stop using CPU, `exec` wakes a parked worker, bursts from a plain thread, fan-out from a worker reaches parked peers, `unpark` from a plain thread, destroy with parked workers, and a stress run of bursts with parking.
- `Schedule.cpp`: pop order Frame, Interactive, Background, FIFO inside a lane, nothing promoted by time, `queued()` counts every lane, push bumps epoch and queued, `waitForWork` returns on push and on a moved epoch, `wakeAll` releases every waiter.
- `Park.cpp`: `fiber::self::current()` on threads and in tasks, the two orders of the park handshake (`UnparkBeforeWorkerParkedRunsOnce`, `UnparkAfterWorkerParkedRunsOnce`), plain yield still reschedules.
- `Cancellation.cpp`, `test.cpp` (`RuntimeTest.PrioritySorting`: Interactive before Background with one worker).
- Lane policy tests (`LanePolicy.cpp`, `LaneResolution.cpp`, `LaneSlice.cpp`, `LaneBoost.cpp`) are listed on [lanes](lanes.md#verification).
- Model: [`Process/Schedule.tla`](https://github.com/Heliogrim/Heliogrim-Engine/blob/fd5affa5b5d9fcb81dafbb1b8ef3fbeedfb87fab/src/Engine.Scheduler/Process/Schedule.tla) + `.cfg` covers push, pop with floor, Frame and reserve claim, leave, roll, epoch, bounded park, cascade and stop, with a Frame and one lower lane. Safety and the drain liveness pass at 2 workers. Any change to the order "load epoch, pop, wait" or to who wakes on push must be re-checked there; the eight mutations in its header (among them epoch loaded after the pop, no wake in `wakeAll`, no cascade) must still fail, except (g), which passes by design.

Tests boot a minimal engine (`TestSchedulerEngine.hpp`, `structuredRuntimeTest`) because the free `exec` functions and futures go through `Engine::getEngine()`.

### Pitfalls

- **No thread identity across a suspension.** After `yield`, `await`, a contended `FiberMutex` or any park, the task may continue on another OS thread. `thread_local` values read before and after differ, `thread::self::getId()` changes, and `UnfairSpinLock` (owned by thread id) throws on release. Hold only ownerless locks (`SpinMutex`) and never across a suspension point.
- **Never block a worker.** A `std::mutex`, `std::condition_variable`, `Sleep` or blocking IO inside a task takes the whole worker out. Use the [waitables](waitables.md); put blocking third-party calls on an [affine thread](affine-threads.md).
- **Do not spin-wait on another task.** If every worker spins on a flag that a queued task would set, nothing runs that task. Parking is the only safe wait.
- **Task pointers are dead after `exec`.** The task deletes itself when it finishes, which can happen before `exec` returns.
- **Lanes do not isolate.** Every worker takes every lane; a lane is a priority, not a worker group. The Frame reserve limits how many workers are inside lower-lane work, it does not pin workers to Frame.
- **Wake rules depend on `isWorker()`.** Code that pushes from a new kind of thread gets a wake automatically; code that pushes from a worker relies on that worker popping next. Code that changes what a parked worker may take without a push (as `rollFrame` lowering the reserve does) must bump the epoch and wake one itself.
- **Small fiber stacks.** The commit is 4 KiB; deep recursion or large stack arrays in a task touch guard pages and grow the stack on the fly, and the reserve is fixed per fiber.
