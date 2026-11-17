# Affine Threads

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip`, 2026-11-16. Built in PR [#164](https://github.com/Heliogrim/Heliogrim-Engine/pull/164).
**Modules** (see the [module map](../../architecture/modules.md)): `Engine.Async` ([`Affine/AffineThread`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Affine/AffineThread.hpp)), `Support.Platform.Win32` ([`WinPlatform`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Support.Platform.Win32/WinPlatform.cpp)), `Engine.IO.Dispatcher` ([`IoThread`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.IO.Dispatcher/IoThread.cpp)), `Engine.Scheduler` (the affine flag in [`Thread/Thread`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Thread/Thread.hpp))
**Related**: [affine threads design](../../architecture/affine-thread-design.md) (the reasoning and the measurements), [engine stop teardown exploration](../../architecture/engine-stop-teardown-exploration.md), issue [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84). Scheduler pages: [overview](index.md), [fibers and workers](fibers-and-workers.md), [waitables](waitables.md), [futures](futures.md).

## Purpose

Some work must run on one particular OS thread: Win32 window and OLE calls on the thread that owns the windows, IO completions on the thread that waits on the completion port. Fibers cannot do this, because a fiber may resume on any worker.

An `AffineThread` is the one seam for such work. It owns one OS thread with an inbox. Any thread hands work over with `post`, gets a [`Future`](futures.md) back and may park on it. The affine thread runs the work in FIFO order and resolves the promise, which wakes the parked fiber directly.

What it deliberately is not: a second scheduler. There are no priorities, no fibers and no awaiting on an affine thread. The inbox has no bound and `post` never blocks.

## Where it sits

```hg-diagram
flowchart LR
    F["fiber on a worker"] -->|"post(fn) -> Future"| IN["inbox<br/>(lock-free MPSC list)"]
    T["any plain thread"] -->|"postDetached(fn)"| IN
    IN -->|"empty -> non-empty:<br/>waker()"| W["OS wait<br/>(message queue / IOCP)"]
    W --> L["loop: drain()"]
    L -->|"runs fn, resolves Promise"| S["Signal::set<br/>fiber back on a worker queue"]
```

Two affine threads exist in the code today:

| Thread | Owner | Waits in | Waker | Running in the engine |
|--------|-------|----------|-------|----------------------|
| `Platform Thread` | `WinPlatform`, reached through `Platform::platformThread()` | `MsgWaitForMultipleObjectsEx(QS_ALLINPUT)` | `PostMessageW(hwnd, WM_APP_DRAIN)` to a message-only window | yes, from `WinPlatform::setup` |
| `IO Thread` | `io::IoThread` | `GetQueuedCompletionStatusEx`, up to 64 entries | `PostQueuedCompletionStatus` with `IoThread::wake_key` | no: nothing constructs it outside its tests |

Both start at OS priority `thread::priority::eHigh`.

Posters today: `WinPlatform::makeNativeWindow` and `destroyNativeWindow` (`post`), the import file dialog in `Editor.Assets.Actions/UnknownImport.cpp` (`post(...).then(...)`), `Win32DragDropSender::dispatchDragDrop` (`postDetached`), and `WinPlatform::eventWatch` for SDL events pushed from another thread (`postDetached`).

## How it works

### The interface

```cpp
// Called from any thread to make the loop return from its OS wait.
using AffineWaker = std::move_only_function<void() const>;

class AffineThread final {
public:
	AffineThread(string name_, mref<AffineWaker> waker_,
		scheduler::thread::priority priority_ = scheduler::thread::priority::eNormal);

	void start(mref<UniqueFn<void(ref<AffineThread>)>> loop_);
	void drain();                       // owning thread only
	[[nodiscard]] bool stopping() const noexcept;
	void stop();                        // idempotent, thread-safe, joins

	template <typename Fn_> requires Send<std::remove_cvref_t<Fn_>>
	[[nodiscard]] Future<std::invoke_result_t<std::decay_t<Fn_>>> post(Fn_&& fn_);
	template <typename Fn_> requires Send<std::remove_cvref_t<Fn_>>
	void postDetached(Fn_&& fn_);

	void setWaker(mref<AffineWaker> waker_); // owning thread only
	[[nodiscard]] u64 depth() const noexcept;
	[[nodiscard]] static ptr<AffineThread> current() noexcept; // null on any other thread
	[[nodiscard]] bool isCurrent() const noexcept;
};
```

Trimmed from [`AffineThread.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Affine/AffineThread.hpp). Both built clients pass an empty waker to the constructor and call `setWaker` from inside the loop, because the window or completion port the waker needs is created on the affine thread itself.

### The loop contract

The client writes the loop; `start` runs it on the new thread. Every loop has exactly this shape:

```cpp
for (;;) {
	self_.drain();
	if (self_.stopping()) {
		self_.drain();
		return;
	}
	os_wait();
}
```

`stopping()` is checked only after a drain. That closes the lost wake when `stop()` races a late `setWaker`: either the wake reaches the new waker, or the loop sees the closed inbox on its next check. `start` also sets the thread name, the OS priority, the scheduler's affine flag and `current()`.

### The inbox

[`AffineThread.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async/Affine/AffineThread.cpp) keeps an intrusive multi-producer, single-consumer list in one atomic word, `_head`. Each item is a `UniqueFn<void(), 128>` in a heap node.

- **Push** is a CAS loop that prepends a node. Only the push that turns the head from empty to non-empty calls the waker; later pushes find the loop already signalled.
- **Close** is bit 0 of the head (`closed_bit`; nodes are aligned, so the bit is free). `stop()` sets it. A push that sees it destroys its node and fails.
- **Drain** takes the whole list with one `fetch_and(closed_bit)`, reverses it into FIFO order and stores it in the member `_pending`. It then runs items one by one. New items are taken only once `_pending` is empty.

No lock is held while an item runs. An item may therefore run a modal loop that dispatches the drain message and re-enters `drain()`. The nested drain finishes `_pending` first, so FIFO holds across nesting.

The push CAS, the take-all and the close are `acq_rel`: the comments in the source name the store-buffer race against `setWaker` that a `release` CAS would allow.

### post, rejection and errors

`post` wraps the callable and a `Promise` into one item. The item resolves the promise with the callable's result.

| Situation | Result |
|-----------|--------|
| `post` before `start` | queued; runs after the loop's first drain |
| `post` after `stop` | the future is already failed with `Broken::Reason::eRejected` |
| `postDetached` after `stop` | the item is destroyed unrun (its captures are released); one warning per thread |
| item throws | logged as an error; the destroyed closure drops its promise, so the future fails as dropped; the thread keeps running |
| items queued before `stop` | run: `stop` closes, the loop drains to empty, then returns |

`post` always enqueues, also when called on the affine thread itself.

### Never await on an affine thread

`start` marks the OS thread with `thread::self::markAffine(true)`. `Signal::wait` begins with:

```cpp
::hg::assertd(not thread::self::isAffine());
```

`JoinCounter::wait` and `await(Future)` (which waits on the future state's `Signal`) go through the same path. Work on an affine thread may block in its own OS calls (a file dialog, `DoDragDrop`, the completion port), never on a fiber result: nothing would make progress for the affine thread meanwhile. The assert is debug only.

### The platform thread

`WinPlatform::setupThread` starts the loop. On the platform thread it:

1. calls `OleInitialize` (the thread is the one STA for windows, drag and drop and dialogs);
2. creates a message-only window (`HWND_MESSAGE`) whose window procedure calls `AffineThread::current()->drain()` on `WM_APP_DRAIN`;
3. sets the waker: post `WM_APP_DRAIN`, and while a drag is active also nudge the drag (below);
4. registers `WinPlatform::eventWatch` with `SDL_AddEventWatch`;
5. loops: drain, check `stopping()`, `MsgWaitForMultipleObjectsEx(..., QS_ALLINPUT, MWMO_INPUTAVAILABLE)`, then `SDL_PollEvent` until empty. The poll only pumps; the event watch already translated the events.

Because modal loops (`DoDragDrop`, file dialogs, the window move loop) keep dispatching Windows messages, `WM_APP_DRAIN` reaches the drain window during a modal and posted work runs there. `SDL_PollEvent` dispatches it too, so drains also run nested inside SDL's pump. There is no guard against that; it is intended.

`eventWatch` runs on whichever thread SDL pushes from. On the platform thread it translates the event at once. From another thread it re-posts the input and window events it handles with `postDetached`, boxed in a `uptr<SDL_Event>` because the event does not fit the 128-byte item.

**Drag nudge.** `DoDragDrop`'s modal loop wakes only on input, so posted messages wait while the mouse is still. While `platform::dragActive()` is true (set around `DoDragDrop` in `Win32DragDropSender::startDragDrop`), the waker also finds the capture window through `GetGUIThreadInfo` and posts it a `WM_MOUSEMOVE` at the current cursor, with the same button and modifier bits the drag recorded as its baseline. `QueryContinueDrag` cancels the drag once `AffineThread::current()->stopping()` is true.

On exit the loop removes the event watch, sets an empty waker (a late `stop()` wake must not post to a destroyed handle), destroys the window and calls `OleUninitialize`.

### The IO thread skeleton

`IoThread::start` creates a completion port with concurrency 1 and starts the loop. The waker posts a packet with `wake_key`; the loop asserts that every packet carries that key. `port()` exposes the handle for a future storage backend. The port stays open until the destructor, so a late wake from a producer after `stop()` never reaches a closed handle.

### Shutdown order

`EditorEngine::shutdown` and `GameEngine::shutdown` call `_platform->tidy()` before `_resources->destroy()` and `_scheduler->destroy()` ([`EditorEngine.cpp:386-391`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Editor.Core/EditorEngine.cpp#L386-L391)). The platform thread's final drain resolves promises and may call `scheduler::exec` (the SDL quit event does), so the scheduler must still run. `WinPlatform::tidy` stops the thread, reports undestroyed windows (with a debug breakpoint) and calls `SDL_Quit`.

## Using it

Illustrative:

```cpp
// From a fiber: create a window on the platform thread and park until it exists.
auto future = platform->makeNativeWindow("Viewport", extent);
auto result = await(std::move(future)); // Result<uptr<NativeWindow>, Fail<...>>

// Fire and forget, from any thread:
platform->platformThread().postDetached([] { /* Win32 or OLE call */ });
```

- Capture by value what must outlive the call site. `makeNativeWindow` copies its `string_view` title into a `std::string` for this reason.
- A callable that captures more than 128 bytes must box its payload (see `eventWatch`).
- `then` continuations hop through `Engine::getEngine()->getScheduler()`, so they need a live engine. Tests use plain `Promise`/`Future` without `then`.
- For a new affine thread: construct with an empty waker, create the OS object inside the loop, `setWaker`, then follow the loop contract verbatim. Stop it before the scheduler is destroyed.

## Debugging

| Symptom | Where to look |
|---------|---------------|
| `Affine thread '<name>' inbox crossed 1024 queued items.` | a producer outruns the thread; the warning re-arms once the depth falls to 512. `depth()` gives the current count |
| `Affine thread '<name>' is stopped; detached item destroyed unrun.` | a `postDetached` after `stop`; logged once per thread |
| `Affine thread '<name>' item threw: ...` | the item's exception; its future fails as dropped |
| debug assert in `Signal::wait` | something awaited on an affine thread; move the wait to a fiber or chain it with `then` |
| debug assert in `stop` | `stop()` called from the affine thread itself (it would join itself) |
| future failed with `eRejected` | posted after `stop`; `UnknownImport` treats it as a cancelled selection |
| posted work stalls during a drag | the nudge did not reach the capture window; check `dragActive()` and `GetGUIThreadInfo` |

The threads are named (`SetThreadDescription`), so they show as `Platform Thread` and `IO Thread` in a debugger.

## Limits and known issues

- **The IO thread is not wired.** `IoThread` is tested but nothing in the engine starts it. File reads still run on the calling fiber.
- **No bound on the inbox.** By design (pressure belongs to the producers); the depth warning is the only signal.
- **Await is caught only in debug.** In release, a wait on an affine thread deadlocks instead of asserting.
- **Not observed with real input** at the time of the design's as-built record: the drag nudge, the import dialog and live resize on the new loop. The design records them as owner checks.
- **Window destroyed during its own drag** is not handled (design section 9).
- **Events from inside `SDL_CreateWindow`** precede the window's registration and are dropped (comment in `makeNativeWindow`).
- **Teardown races with frames** (R1 to R5 in the [stop teardown exploration](../../architecture/engine-stop-teardown-exploration.md)) are outside this seam.

## Changing it

- Tests: `Heliogrim-Engine.Async.Test` ([`Engine.Async.Test/AffineThread.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Async.Test/AffineThread.cpp): FIFO per producer from many threads, stop runs queued items then rejects, post before start, throwing item, nested drain keeps FIFO, late waker, stop before the waker is set, concurrent stop waits for the join, depth warning once per crossing, stop from itself asserts, priority). `Heliogrim-Engine.IO.Dispatcher.Test` ([`IoThread.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.IO.Dispatcher.Test/IoThread.cpp): post wakes and resolves, clean stop, double stop, foreign key asserts). `Heliogrim-Engine.Scheduler.Test` (`Waitable.cpp`: the affine flag is per thread, `Signal::wait` asserts on a marked thread).
- The platform loop, the drag nudge and modal draining have no automated test; check them in the editor (open a file dialog, drag an asset out, move and resize a window).
- The inbox is an atomic protocol in `Engine.Async`, so the repository's concurrency verification rule (TLA+ model beside the source, Relacy, stress test) applies to changes. There is no `AffineThread.tla` beside the source at this commit.
- Never reorder `_platform->tidy()` after `_scheduler->destroy()`, and never let a client loop check `stopping()` before its first drain.
- Keep every waker ever set alive (`_wakers`) until destruction: a producer may still be calling an older one.
