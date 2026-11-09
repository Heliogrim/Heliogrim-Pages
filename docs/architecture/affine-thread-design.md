# Affine Threads (Design)

**Status**: design, draft 2026-11-09 (work chunk [W02.3](../plan/work/concurrency-fibers.md), issue [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84)). Builds on the [scheduler waitables design](scheduler-waitable-design.md) and the [promise and future rework](promise-future-design.md), both as built on engine PR #159. The implementation plan lives untracked in the engine checkout (`docs/superpowers/plans/2026-11-09-affine-threads.md`).

Markers: **Decided** = owner decision (work page or the W02.3 conversation of 2026-11-09). **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

Some work must run on one particular OS thread: Win32 window and OLE calls on the thread that owns the windows, IO completions on the thread that waits on the completion port, audio on the device thread. Today the only such thread, the platform thread, is a hand-rolled `std::thread` that spins (`SDL_PollEvent`, drain, `std::this_thread::yield()`), drops work when its ring buffer is full, and stops draining while a modal loop (`DoDragDrop`, a dialog, a window move) runs. There is no IO thread at all: blob reads run `std::fstream` on the fiber that asks and block its worker.

An `AffineThread` is the one seam for all of them: fibers hand work over with `post`, get a `Future`, and park on it; the affine thread completes the work and wakes the fiber directly.

## 2. State of the inputs (checked 2026-11-09)

| Input | Found in the engine |
|---|---|
| Platform thread | `WinPlatform` (`Support.Platform.Win32`): `std::thread`, `OleInitialize`, loop of `SDL_PollEvent` + `SignaledQueue` drain + `thread::self::yield()` (`std::this_thread::yield`), so one core spins while the engine runs |
| `SignaledQueue` | `Engine.Scheduler/Task`, ring buffer of `UniqueFn<void(), 128>` under a `std::mutex` + condvar; used only by `WinPlatform` and through `Platform::platformQueue()` |
| Posters | `WinPlatform::makeNativeWindow`, `destroyNativeWindow` (spin while the ring is full; after `finalize` they skip the push and the future fails with `eDropped`), the import file dialog in `Editor.Assets.Actions/UnknownImport.cpp` and `Win32DragDropSender::dispatchDragDrop` (ignore a failed push, so the work is lost) |
| Teardown | `EditorEngine::stop` (`Editor.Core/EditorEngine.cpp:382-384`) and `GameEngine::stop` (`Engine.Core.Game/GameEngine.cpp:322-324`) both run `_resources->destroy()`, `_scheduler->destroy()`, then `_platform->tidy()`: the platform thread outlives the scheduler, and anything it completes or `exec`s during its final drain lands in a destroyed scheduler. Setup is the mirror: `_platform->setup()` before `_scheduler->setup()` |
| OLE and drop targets | `WinPlatform::setup` calls `OleInitialize` on the calling (main) thread, the platform thread calls it again; `Input::captureWindow` runs inside the `makeNativeWindow` item, so `RegisterDragDrop` and the drop callbacks are on the platform thread already |
| Drag sender | `sendDragFiles` / `sendDragText` already refuse a second drag while `_cur` is set; `QueryContinueDrag` cancels on Escape and drops on a key-state change; `DoDragDrop` runs inside a platform-queue item |
| SDL | 3.2.22; `SDL_AddEventWatch`, `SDL_PeepEvents`, `SDL_WaitEventTimeout` and `SDL_SetWindowsMessageHook` are available |
| Modals | File dialogs work. `DoDragDrop` never worked reliably; during any modal loop the platform queue and SDL events are not drained |
| `Engine.IO.Dispatcher` | stub, never constructed, nothing calls it; `_io_()` would dereference null |
| File IO | synchronous `std::fstream` (`LfsSyncBlob`), on the calling fiber |
| `StorageSystem::queryAsync` / `mutateAsync` | declared for blob, package and archive; all `todo_panic()` (W03.3 removes them) |
| Layering | `Future` lives in `Engine.Async`, which links `Engine.Scheduler`. `Engine.Platform` includes `Engine.Async` headers but links only `Engine.Common`; `Support.Platform.Win32` links `Engine.Common` and `Engine.Platform`; `Engine.IO.Dispatcher` already links `Engine.Async`. `Engine.Async`'s continuation path (`Future/Schedule.hpp`) reaches `Engine::getEngine()->getScheduler()`, so `then` continuations need a live engine. `SignaledQueue` (in `Engine.Scheduler`) includes `Engine.Async/Collection/RingBuffer.hpp`, a layering inversion that deleting it removes |

## 3. Goals

1. One `AffineThread` type: an owned OS thread, an inbox, a waker, `post(fn) -> Future`.
2. No spinning: an idle affine thread sleeps in the OS primitive it already waits on.
3. No lost work: `post` never fails silently; after `stop` it fails loudly as `Broken::eRejected`.
4. The platform thread keeps draining its inbox and SDL events while a modal loop runs, so `DoDragDrop` works and a window can be created during a drag.
5. An IO thread skeleton on an IO completion port that W03.3 builds the storage backend on.
6. The per-queue ownership rule for Vulkan submission (Q02.4) is written down (section 11).

## 4. Non-goals

- The storage request path: `IoRequest`, `IoQueue`, `IoBackend`, IOCP file reads, `queryAsync`/`mutateAsync`, DirectStorage, batching and coalescing. All W03.3/W03.4; section 12 hands over what this conversation settled for them.
- The audio device thread (audio runtime design, its own lock-free queues), sockets, the streaming transfer queue owner. They are later clients of the same type.
- Replacing `Engine.IO.Dispatcher`. It stays untouched until W03.3 replaces it.
- Deterministic resume order (W02.6).

## 5. Anti-goals

- A second scheduler. An affine thread runs closures in FIFO order, nothing more: no priorities, no fibers, no awaiting.
- Backpressure that only moves the queue (section 8).
- A per-thread message pump per apartment. One STA, one pump (section 9).

## 6. Contract

**Decided**: completion is direct. An affine thread resolves the `Promise`, which calls `Signal::set` and pushes the parked fiber onto the scheduler queue. There is no completion inbox drained by workers: it would add a hop and latency, and its only benefit (a reproducible resume order) belongs to deterministic mode.

**Decided**: a real-time thread (the audio device callback) never calls `Signal::set`, because that takes the park-queue spin lock a worker may hold. It hands results to a non-real-time partner through a lock-free SPSC or SPMC queue, and the partner completes.

Interface (**Proposal**; names may be adjusted to `STYLE.md`), in `Engine.Async/Affine/AffineThread.{hpp,cpp}`:

```cpp
namespace hg::engine::async {
	class AffineThread final {
	public:
		explicit AffineThread(string name_, mref<Waker> waker_);
		~AffineThread();                     // asserts the thread was stopped and joined

		// Starts the OS thread and runs loop_(*this) on it. The loop returns once
		// stopping() is true and drain() has emptied the inbox.
		void start(mref<UniqueFn<void(ref<AffineThread>)>> loop_);
		void stop();                         // close the inbox, wake, join

		template <typename Fn_> requires Send<Fn_>
		[[nodiscard]] Future<std::invoke_result_t<Fn_>> post(Fn_&& fn_);
		template <typename Fn_> requires Send<Fn_>
		void postDetached(Fn_&& fn_);

		// Called by the loop on the owning thread: runs every queued item, FIFO.
		void drain();
		[[nodiscard]] bool stopping() const noexcept;
		[[nodiscard]] bool isCurrent() const noexcept;
		[[nodiscard]] static ptr<AffineThread> current() noexcept;   // null on any other thread
	};
}
```

- The plan adds `setWaker(waker_)`, called on the affine thread once its window or port exists, because those handles are created on the thread itself; the constructor's waker may then be empty.
- `Waker` is a small callable set by the client: how to make the loop return from its OS wait. The platform thread posts a window message, the IO thread posts a completion packet (sections 9, 10). It is called from any thread, so it must be cheap and lock-free from the caller's view.
- `post` always enqueues, also when called from the affine thread itself, so FIFO holds. (**Proposal**, changes what was said in conversation, "run inline when already on the thread": inline execution would jump the queue, and a self-post that is then awaited is already forbidden by the next rule.)
- `post` after `stop` returns a future already failed with `Broken{eRejected}`; `postDetached` after `stop` destroys the item unrun (its captures are released) and logs once per thread at warning level. Items queued before `stop` still run: `stop` closes, the loop drains to empty, then returns.
- `post` before `start` is legal: the item waits in the inbox, and the loop drains once right after its waker is ready, so a wake lost before the window or port existed cannot stall the inbox.
- `stop` on the affine thread itself asserts (it would join itself).
- **Proposal** (from the builder check, checked against the code): affine threads stop before the scheduler is destroyed. In `EditorEngine::stop` and `GameEngine::stop`, `_platform->tidy()` (which stops the platform thread, then runs `SDL_Quit` and the undestroyed-window check) moves before `_resources->destroy()`. The final drain completes promises and may `exec` (the quit handler does), which needs a live scheduler. Windows are destroyed by module destroy, which runs earlier in `stop`, so the window check still holds. No new `Platform` virtual is needed.
- An item that throws: the exception is caught in `drain`, logged, and the item's future fails with `Broken{eDropped}` (the promise is destroyed unresolved). The affine thread keeps running.
- `Send` is checked at the post call, the same creation-point rule as `async` and `then`.

**Rule: work on an affine thread never awaits.** It may block in its own OS calls (a modal dialog, `DoDragDrop`, `GetQueuedCompletionStatusEx`), never on a fiber result, since nothing would make progress for the affine thread meanwhile. `AffineThread` marks its OS thread in `Engine.Scheduler` (`thread::self` gets an affine flag, a `thread_local` on a plain thread, so not subject to fiber migration); `Signal::wait` (and so `JoinCounter::wait` and `Future` awaits) on a marked thread `assertd`. **Proposal**: `FiberMutex` and `FiberSharedMutex` stay allowed on affine threads. Their critical sections are short and do not wait on a result; the assert therefore sits in `Signal::wait`, not in `park()`.

## 7. Inbox

**Proposal**: an intrusive multi-producer, single-consumer list with take-all.

- A node holds the `UniqueFn<void(), 128>` and a `next` pointer. `post` allocates one node; the posting rates here (window calls, dialogs, IO submissions) make that negligible.
- Push is a CAS loop on the head. A push that turns the head from empty to non-empty calls the waker; later pushes do not. That coalesces wakes with no extra flag.
- `drain` exchanges the head for empty, reverses the taken list into FIFO order and appends it to a member `pending` list, then pops and runs items from `pending` one by one, and repeats until both are empty. No lock is held while an item runs, so an item may itself run a modal loop that re-enters `drain` (section 9). Because the unrun remainder lives in the member, a nested `drain` finishes it before taking newer items, and FIFO holds across nesting. `pending` is touched only by the owning thread.
- Closing uses a tag bit in the head: `stop` sets it; a push that sees the bit fails (the `eRejected` path); `drain` keeps the bit when it takes the list.
- The ABA problem does not arise: the only pop is take-all by the single consumer.

**Builder's call**: node allocation (plain `new` or a small free list), the exact tag encoding.

## 8. Pressure

**Decided** (conversation): parking a producer when the inbox is full only moves the queue to the scheduler side, and costs a fiber stack per waiting item instead of a 128-byte closure. The inbox therefore has no bound and `post` never blocks.

The real levers sit where the work comes from, and are W03.3/W03.4's: in-flight budgets per client (at most N requests outstanding, the next one issued on completion), coalescing adjacent and duplicate ranges, cancellation of stale requests through the cancellation tokens, priorities at submission. The affine thread itself stays cheap per item by design: the IO thread submits and harvests while the device queue holds the real backlog; the platform thread's load is small.

`AffineThread` keeps a depth counter. Crossing a threshold (**Proposal**: 1,024 queued items) logs one warning per crossing, like the fiber pool budget diagnostic; the warning re-arms only once the depth falls to 512 or below, so a backlog hovering at the threshold does not log on every push (as built). A deep inbox is a symptom to investigate, not to hide.

## 9. Platform thread

**Decided**: one STA thread does everything Win32 and OLE: `OleInitialize`, SDL windows, `RegisterDragDrop`, `DoDragDrop`, file dialogs. A second apartment would need its own pump and `AttachThreadInput`, which is what made earlier attempts messy.

**Proposal**: drain through the Windows message queue, the one thing every modal loop keeps dispatching.

- On start, the platform thread calls `OleInitialize` and creates a message-only window (`HWND_MESSAGE`) with its own window procedure.
- The waker is `PostMessage(hwnd, WM_APP_DRAIN)`. The window procedure handles `WM_APP_DRAIN` by calling `drain()`. Inside `DoDragDrop` or a dialog, the modal loop dispatches that message, so posted work runs during the modal.
- `SDL_PollEvent` pumps Win32 messages itself, so it dispatches `WM_APP_DRAIN` too and runs items such as `SDL_CreateWindow` re-entrantly inside SDL's pump. **Measured** (spike, 2026-11-09): SDL dispatches our posted messages (15 of 15); creating and destroying an SDL window inside such a nested drain worked; the window move loop starts inside SDL's dispatch, so every drain during a move is nested in `SDL_PollEvent`. **Decision** (ruling during plan execution, open to the owner): no guard; re-entrant draining inside SDL's pump is allowed. A guard would stop all draining during a window move.
- **Measured**: `DoDragDrop`'s modal loop waits for input only. Posted messages and `WM_TIMER` stay queued until a mouse or keyboard message arrives; with the mouse held still, nothing drains and `QueryContinueDrag` is not called. A posted `WM_MOUSEMOVE` to the OLE capture window wakes both. **Decision** (ruling, open to the owner): while a drag is active, the platform waker also posts `WM_MOUSEMOVE` (at the current cursor position) to the drag's capture window, which the drag sender records from its first `QueryContinueDrag` and clears when `DoDragDrop` returns. Fallback if it misbehaves on real hardware: drop the nudge and accept that posted work waits for the next mouse move during a drag.
- **Measured**: a modal message box (stand-in for the file dialog) drains on every post; `SDL_AddEventWatch` is called synchronously inside the move loop. **Decision**: SDL events are translated in an event-watch callback on the platform thread, so input keeps flowing during a window move; the loop's own `SDL_PollEvent` only pumps.
- Nested modals: an item may open a modal inside another modal (Windows allows it). `Win32DragDropSender` refuses a second drag while one is active. A window destroyed while a drag started from it is still running is not handled in this chunk (known gap, logged).
- **Proposal**: a drag in progress is cancelled when stopping (`QueryContinueDrag` returns `DRAGDROP_S_CANCEL` once `stopping()` is true; the stop wake carries the mouse-move nudge, so `QueryContinueDrag` runs). An open file dialog is not closed; `stop` waits until the user closes it, and logs that it is waiting.
- The idle loop blocks in the OS until there is input or a posted message (**Builder's call**: `SDL_WaitEvent` or `MsgWaitForMultipleObjectsEx(QS_ALLINPUT)` followed by the SDL poll; both wake on the posted message), handles SDL events as today, then checks `stopping()`.
- During `DoDragDrop` OLE holds the mouse capture, so the editor's own windows see no mouse moves; the drag reaches the editor through the drop target's `DragEnter`/`DragOver`/`Drop`, which already run on the platform thread.
- `Platform::platformQueue()` is replaced by `Platform::platformThread() -> ref<AffineThread>`. `SignaledQueue` is deleted.
- SDL initialisation stays where it is today (`WinPlatform::setup` on the calling thread); moving it is not part of this chunk.

Shutdown: `WinPlatform::tidy` calls `stop()`, which wakes the loop, drains, and joins. The current check for undestroyed windows stays.

## 10. IO thread skeleton

**Proposal**: `Engine.IO.Dispatcher` gains `IoThread` (Windows only, like the rest of the engine):

- On start it creates an IO completion port with concurrency 1. The waker posts a packet with a reserved completion key (`PostQueuedCompletionStatus`).
- The loop waits in `GetQueuedCompletionStatusEx` (up to 64 entries per call). The wake key calls `drain()`; any other key is reserved for W03.3's backend and asserts in this chunk.
- Exposes the port handle so W03.3 can associate file handles with it.
- Not wired into engine startup in this chunk: nothing posts to it yet. W03.3 decides ownership (engine module or storage system) and replaces the `Dispatcher` stub. This chunk proves the IOCP waker and the shutdown path with tests.

## 11. Vulkan queue ownership (Q02.4)

**Decided**: there is no single submit thread; multi-threaded submission stays a capability. Each `VkQueue` has one owner at a time (external synchronisation per queue, never a global submit lock); distinct queues submit concurrently from different threads or fibers. Graphics and present submit from the frame's submit stage on whichever fiber runs it. The transfer queue for streaming uploads is owned by an `AffineThread` fed by storage completions (W03.4 or W17/W18 stands it up). S14 may later split graphics submission across queues.

## 12. Handed to W03.3 (from the W02.3 conversation)

Recorded here and as inputs on the W03.3 chunk, so they are not lost:

- The fiber callback of `queryAsync`/`mutateAsync` stays on the fiber (parsing, iterating, building objects is CPU work that should spread over the workers). The IO thread only moves bytes: a fiber hands over a byte range or a batch of ranges, parks once, and wakes when all are resident.
- Package reads jump: header, then index, then archives. Expected cost per package load: one handover for the header (with a speculative window that often covers the index), one for the index if needed, one per batch of archive ranges.
- Archive walks jump inside the archive. Once the archive range is resident, walking is in memory.
- Large archives (cell and level archives listing all actors and their component hierarchies) may be too big to pin whole; they fall back to a windowed `Blob::read` that fetches a fixed window on a miss (one park per window). Bulk binary (micropolygon pages, 8K textures) is paged by W17 and W18.7, never loaded as a whole archive.
- Writes use the same path: the fiber fills a buffer and hands over "write this range".
- The buffer belongs to the guard for the callback's duration; no cross-query cache in the first version.
- Pressure relief lives in the request path: in-flight budgets per client, coalescing, cancellation, priorities (section 8).
- Storage guards stay held while a fiber is parked; they must be fiber-aware (`ExclusiveIoResource` is on `FiberMutex` since PR #159; W03.3 checks the others).

## 13. Migration

| Site | Change |
|---|---|
| `WinPlatform` | owns an `AffineThread`, message window, loop as in section 9 |
| `Platform::platformQueue()` | becomes `platformThread()` |
| `WinPlatform::makeNativeWindow`, `destroyNativeWindow` | `post`, returning its future; the spin-until-pushed loops go |
| `UnknownImport` file dialog | `postDetached` with the existing promise inside (the typed error stays) |
| `Win32DragDropSender::dispatchDragDrop` | `postDetached` |
| `SignaledQueue` | deleted, not moved |
| `EditorEngine::stop`, `GameEngine::stop` | `_platform->tidy()` moves before `_resources->destroy()` (section 6) |
| CMake | `Engine.Platform` and `Support.Platform.Win32` link `Engine.Async` |

## 14. Done when

- An idle editor's platform thread uses no CPU (it sleeps in the OS wait).
- `post` from 8 fibers × 1,000 items completes all in order per producer; `post` after `stop` fails with `eRejected`; items queued before `stop` run.
- `await` on an affine thread asserts in debug.
- In the editor: a drag started from the editor runs `DoDragDrop` to completion, a window created by a post during the drag appears before the drag ends, and the editor's drop target receives the drag.
- `IoThread` wakes on post, drains, and stops cleanly, under test (tests use plain `Promise`/`Future` without `then`, which needs a live engine).
- Editor shutdown with the platform stopped before the scheduler exits cleanly.
- `SignaledQueue` and the `yield` loop are gone.

## 14a. As built (W02.3 execution, 2026-11-09)

Engine branch `feat/affine-threads` (off `feat/scheduler-waitables`), six plan tasks, each reviewed, plus a whole-branch review (verdict: mergeable). Contracts settled during implementation:

- **Loop shape** (binding for every client): after `setWaker`, `for (;;) { drain(); if (stopping()) { drain(); return; } <OS wait> }`. Checking `stopping()` only after a drain closes the lost wake against a `stop()` racing a late `setWaker`; the inbox RMWs (push CAS, take-all, close) are `acq_rel` for the same reason.
- `stop()` is idempotent and thread-safe; every caller returns only after the thread was joined. `start()` must happen-before any `stop()` on another thread and is not allowed after `stop()`. Destroy an `AffineThread` only after every in-flight `post` returned.
- `setWaker` asserts it runs on the owning thread; old wakers are kept until destruction, so a producer mid-call never races a swap.
- Platform thread: message-only window, `MsgWaitForMultipleObjectsEx(QS_ALLINPUT, MWMO_INPUTAVAILABLE)` idle wait, SDL events translated in an `SDL_AddEventWatch` callback; events SDL pushes from another thread are re-posted to the platform thread. No SDL-pump guard. During `DoDragDrop` the waker also posts a `WM_MOUSEMOVE` (logical buttons, same bits as the drag's baseline) to the capture window found through `GetGUIThreadInfo`.
- `IoThread`: the completion port lives until the destructor, so a late wake after `stop()` never reaches a closed or recycled handle.
- Measured: editor process CPU at idle 56.8 s → 27.0 s per 30 s. Editor exit code unchanged (`0x80000003`, a pre-existing breakpoint from shader modules destroyed late).
- Not yet observed with real input: the drag nudge, the import dialog and live resize on the new loop (owner checks).

## 15. Left to the builder

Node allocation and tag encoding (section 7); the idle wait call and the modal SDL mechanism, after the spike (section 9); file and class names within `STYLE.md`; whether `Waker` is a `UniqueFn` or a function pointer plus context.
