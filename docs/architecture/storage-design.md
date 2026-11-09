# Storage (Design)

**Status**: design, draft 2026-11-09. Section 1 is work chunk [W03.1](../plan/work/storage-streaming.md) (issue [#85](https://github.com/Heliogrim/Heliogrim-Engine/issues/85), absorbs [#24](https://github.com/Heliogrim/Heliogrim-Engine/issues/24)). Section 2 is work chunk [W03.3](../plan/work/storage-streaming.md) (same issue): the async request path and the IOCP backend. Builds on the [storage exploration](storage-exploration.md) and the [affine threads design](affine-thread-design.md) (sections 8, 10, 12, 14a). The implementation plans live untracked in the engine checkout (`docs/superpowers/plans/2026-11-09-resolved-stack-reuse.md`, `docs/superpowers/plans/2026-11-09-async-storage-iocp.md`).

Markers: **Decided** = owner decision (the [work page](../plan/work/storage-streaming.md) Decisions table). **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Resolved-stack reuse

### 1.1 What the code does today (checked 2026-11-09, branch `feat/affine-threads`)

The exploration says "the resolver stack is rebuilt on every call". The check splits that claim in two:

- **The type-level chain is already cached.** `StorageActionResolver::resolveQuery` and `resolveMutation` look up an `ActionResolutionFactory` in `ActionTypeResolutionCache`, keyed by `ActionTypeInfo` (target resource plus the storage type of each stage), and build one only on a miss. This part needs no work. Its `invalidateQuery` and `invalidateMutation` are `todo_panic` but nothing calls them, and nothing needs to: types do not change at runtime.
- **The runtime stage state is rebuilt on every call.** `StorageSystem::fetchQuery` builds a fresh `QueryDynamicGen`. `acquire` runs every stage's `acqFn` from the primary storage up: `LfsBlob` opens a new `std::fstream` (`LfsSyncBlob`), `BlobPack` re-parses the package header, linker and footer from that blob, `PackArchive` builds a `StorageReadonlyArchive` view at the linked offset. Each stage registers its object in `Context::objectStore` and its lock-holding `ExclusiveIoResource` in `Context::accessStore`, both keyed by the `IStorage`. `release` drops both again. Nothing survives the call.
- **Overlapping calls on one chain fail.** `StorageSystem` owns a single `Context` without a lock, and `ResourceAccessStore::add` asserts that the storage key is absent. Two queries that overlap in time on the same storage, or on two archives of the same package (both acquire the package stage), hit that assert. Today this does not show because all storage I/O runs synchronously, one call at a time.
- **The per-call `ExclusiveIoResource` locks never contend**, because each call creates its own. They protect nothing across calls.
- `Access/SharedReadIoResource.hpp` exists as an empty file, added in the working tree but not committed.

So "reuse the resolved stack" means: keep the stage objects (open blob, parsed package, archive view) alive across calls, share them between concurrent readers, and drop them when a commit makes them stale.

### 1.2 Stage key per resolver

**Decided** (Q03.1): cache per resolver stage, reuse the longest cached prefix, never a flat key. **Proposal** for the key: `StageKey { const IStorage* storage; type_id resource; }`.

- *The URL part a stage consumed* is the `IStorage` instance. The registry maps one URL to one storage (`file+editor://shader/x.asl` → `LocalFileStorage`, `package://<guid>` → `PackageStorage`, `archive://<guid>` → `ArchiveStorage`), so the storage's identity is the consumed URL part, already resolved.
- *The resolver type* is fixed by the storage type plus the resource type (`StageTypeInfo { storage, resource }`).
- *The action type* is folded into the resource type: a query yields `const LfsSyncBlob`, `const ReadonlyPackage`, `StorageReadonlyArchive`; a mutation yields the read-write types.

| Resolver (`Engine.Storage.Boot/Action`) | Query stage key | Cached object | Below it |
|---|---|---|---|
| `LfsBlob` | (`LocalFileStorage`, `const LfsSyncBlob`) | open `LfsSyncBlob` | nothing (primary) |
| `MemBlob` | (`MemoryStorage`, `const ByteSpanBlob`) | blob view over the memory | nothing (primary) |
| `BlobPack` | (`PackageStorage`, `const ReadonlyPackage`) | parsed package (header, linker, footer) | the blob stage of the backing file or memory |
| `PackArchive` | (`ArchiveStorage`, `StorageReadonlyArchive`) | archive view (offset, size, type) | the package stage |
| `BlobArchive` | (`ArchiveStorage`, `StorageReadonlyArchive`) | archive view over a whole blob | the blob stage |

**Proposal**: only query stages are cached. Mutation stages are rare, exclusive and short-lived; they keep being built per call. That keeps the read-write types out of the cache and keeps the change to the read path.

### 1.3 Structure

```hg-diagram
flowchart LR
    G["IoQueryGuard"] -->|Arci| A["ResolvedStage<br/>archive view"]
    A -->|Arci below| P["ResolvedStage<br/>parsed package"]
    P -->|Arci below| B["ResolvedStage<br/>open blob"]
    C["StackCache<br/>StageKey → Arci&lt;ResolvedStage&gt;"] -.-> A
    C -.-> P
    C -.-> B
```

- **`ResolvedStage`** (`Engine.Storage.Action/Store/ResolvedStage.hpp`): `{ StageKey key; Arci<IStorage> storage; meta::WithType<Rc<IoResourceAccessorBase>> access; Arci<ResolvedStage> below; }`. Immutable after creation, `Arci`-counted. It keeps the stage below it alive, so a chain stays whole for as long as anyone holds its top.
- **`StackCache`** (`Engine.Storage.Action/Store/StackCache.{hpp,cpp}`), owned by `StorageSystem` in place of `Context`'s two stores for queries: `find(StageKey) -> Opt<Arci<ResolvedStage>>`, `insert(Arci<ResolvedStage>)`, `invalidateFrom(const IStorage* primary)`. The map is a `DenseMap` (ankerl, per the pointer sets exploration) under a `concurrent::SpinMutex` taken through a `SpinLock` guard, held only for lookups and inserts, never across I/O.
- **Lookup with prefix reuse**: `QueryDynamicGen::acquire` walks the chain from the top. On a hit it stops. On a miss it recurses to the stage below, then runs only this stage's `acqFn` with the below stage's access as input and inserts the result. A request for archive `A` in package `P` after any earlier query of `P` resolves only the archive stage. Two fibers that miss the same key at once may both build it; the second `insert` returns the first entry and drops its own (**Builder's call** whether to dedupe more cleverly; correctness only needs "first insert wins").
- **Query `acqFn` and `relFn`**: the query `acqFn` of each resolver stops touching `Context::objectStore` and `accessStore` and returns its accessor. A query `relFn` no longer drops anything; releasing a guard drops its `Arci` to the top stage.

### 1.4 Locking and lifetime

- **Proposal**: one `FiberSharedMutex` per primary storage (the bottom of a chain), kept in the `StackCache` next to the entries. A query guard holds it shared from acquire to release. A mutation holds it exclusively from acquire through commit and invalidation. A commit therefore never runs while a reader is inside the chain, and a reader never sees a half-written package.
- **Invalidate after commit, under the write lock** (exploration section 3; decided in the work page code design). A mutation runs: lock exclusive → acquire read-write stages (uncached) → exec → release (the package or archive `relFn` commits) → `invalidateFrom(primary)` → unlock. A query that waits on the lock then misses and rebuilds from the committed bytes. A query can no longer re-cache pre-commit data, because it cannot run between the commit and the invalidation.
- **Invalidation rule, one for all resolvers**: a commit invalidates every cached stage whose chain bottoms out at the mutated primary storage. That is "the mutated stage and every stage above it" with the mutated stage taken as the lowest stage written. Per resolver: a blob mutation invalidates the blob stage and any package and archive stages parsed from it; a package mutation invalidates the package, its blob stage and all its archives (the linker may move every offset); an archive mutation commits through its package, so the same set. Rebuilding a blob stage costs one file open, which is cheaper than reasoning about which offsets moved.
- **Cached handles held by live guards** (exploration problem 3): invalidation only removes entries from the map. A guard that still holds the chain keeps its objects alive through `Arci`; the handle closes when the last holder lets go. With the shared lock this cannot happen across a commit anyway, so no epoch counter is needed.
- **Concurrent readers on one blob**: `LfsSyncBlob` reads through one `std::fstream` with a seek position, so two readers sharing a cached blob stage race on the position. **Proposal**: `LfsSyncBlob::read` holds a `FiberMutex` around its seek and read. W03.3 replaces the stream with positional overlapped reads, which need no lock; the mutex goes then.
- `SharedReadIoResource` (the empty stub) becomes the access resource of cached query stages: `acquireReadonly` hands out accessors without an exclusive lock, since the per-storage shared mutex already orders readers against writers. **Builder's call** whether to fill the stub or reuse `ExclusiveIoResource` with the lock skipped; the stub is the clearer name.

### 1.5 Size bound

Every cached blob stage of a local file holds an open file handle. The editor auto-indexes every asset file, so an unbounded cache would hold thousands of handles. **Proposal**: a count bound, `StackCache::kMaxEntries = 512`, evicting the least recently used entry that no guard holds (`Arci` use count of one, the cache's own). Entries held by a guard are never evicted. This is a stopgap: W03.3 and the residency manager (S03 code design) own real budgets.

`StorageSystem::removeStorage` calls `invalidateFrom` for the removed storage, so a removed file never keeps a cached handle.

### 1.6 Issue #24

The hard-coded path in #24 is gone: `read_shader_file` (`Engine.GFX.Render.Subpass/Impl/__tmp_helper.hpp`) now looks up `shader/<name>` under the project and editor asset paths from the config. What is left is that shaders bypass storage: the helper opens a `std::ifstream` itself. **Proposal**: `read_shader_file` queries `file+project://shader/<name>`, then `file+editor://shader/<name>`, through `StorageSystem::requestStorage` and `query`, and returns the blob's bytes. Shaders then hit the stack cache like any asset, the same reader works for packaged builds once shaders move into archives, and a test pins it. The `R:\...` paths in `Engine.GFX.RenderGraph/test.cpp` belong to a test that is not built; they stay out of scope.

### 1.7 Tests (`Engine.Storage.Test`)

| Test | Proves |
|---|---|
| `StackCacheFixture.RepeatedQueryResolvesOnce` | two queries of one archive build each stage once (count `acqFn` calls through a test resolver) |
| `StackCacheFixture.ArchiveReusesPackagePrefix` | a query of archive `B` after archive `A` in the same package builds only the archive stage |
| `StackCacheFixture.MutationInvalidatesAfterCommit` | after a package mutation, the next query sees the new archive and rebuilds the package stage |
| `StackCacheFixture.GuardKeepsInvalidatedChainAlive` | a chain taken out of the cache stays valid while its holder lives |
| `StackCacheFixture.OverlappingQueriesShareStages` | two guards on archives of one package at the same time; no assert, one package stage |
| `StackCacheFixture.EvictsOnlyUnheldEntries` | at the bound, an unheld entry goes, a held one stays |
| `StackCacheFixture.RemoveStorageDropsEntries` | `removeStorage` leaves no cached stage for that storage |
| `ShaderReadTest.ResolvesThroughStorage` | `read_shader_file` returns the bytes of a shader under the editor asset path via storage (closes #24) |

### 1.8 Left for later

- Async acquisition and batched reads (W03.3); the `FiberMutex` in `LfsSyncBlob` goes with it.
- Budgets by resource class instead of a count bound (residency manager).
- Caching mutation stages.
- Mutation compaction rules (exploration open question); unchanged by this section.

## 2. Async request path and IOCP backend

### 2.1 What the code does today (checked 2026-11-09, branch `feat/affine-threads`)

- All six `queryAsync` and `mutateAsync` overloads in `StorageSystem.hpp` are `todo_panic`, and nothing calls them.
- File I/O is `LfsSyncBlob`: one `std::fstream` per blob, opened in its constructor, read with seek plus read. A read blocks the worker that runs it.
- Parsers read in small pieces. `package::readHeader`, `readLinker` and the footer check do one `Blob::read` each. `StorageReadonlyArchive` reads every serialised value with its own `Blob::read` call at `_baseOffset + _cursor`. If every `Blob::read` became a request, walking an archive would park the fiber once per field.
- `Engine.IO.Dispatcher` holds the `IoThread` skeleton from W02.3. It creates a completion port with concurrency 1, its waker posts `wake_key`, the loop calls `GetQueuedCompletionStatusEx` for up to 64 entries, and it asserts on any other key. Nothing starts it yet. The old `Dispatcher` class next to it is a stub, and nothing references it.
- `Future<T, E>` and `Promise<T, E>` exist, and `await(Future)` returns `Result<T, Fail<E>>`. `await` parks a fiber on a worker and blocks a plain thread on an atomic wait. On an affine thread it asserts. Storage locks are fiber-aware: `ExclusiveIoResource` uses `FiberMutex`, and no `std::mutex` is left in `Engine.Storage.*`, `Engine.Resource.*` or `Engine.Assets.*`. That settles the check handed over in affine design section 12.
- Package layout: `docs/packages.pdf` (January 2023) matches the code's section order: header, index, meta, body, compression data, footer. Per **Decided** Q03.4, the code is the reference where the two differ. Archives sit at `sizeof(PackageHeader) + linked.data.offset`, and the footer is the last `sizeof(PackageFooter)` bytes.

### 2.2 Shape

```hg-diagram
flowchart LR
    F["Fiber<br/>queryAsync / Blob::read"] -->|submit batch| Q["IoQueue<br/>priority, FIFO batches"]
    Q -->|post| T["IoThread<br/>issue up to budget"]
    T -->|ReadFile / WriteFile overlapped| OS["Windows IOCP"]
    OS -->|completion packet| T
    T -->|resolve batch promise| F
```

The fiber does the CPU work: parsing, walking archives, building objects. The IO thread only moves byte ranges, and it never runs a callback (affine design section 12). The interface follows DirectStorage (**Decided** Q03.2): file ranges, batch submit, FIFO completion per queue, cancellation by tag, and a compression field.

| Type (`Engine.IO.Dispatcher`) | Contract |
|---|---|
| `IoFile` | An overlapped file handle associated with the port, `Arci`-counted, closed by its last holder. `IoSystem::open(path, IoOpenMode)` returns `Future<Arci<IoFile>, IoError>` and runs `CreateFileW` on the IO thread, since an open can block (network shares, antivirus). |
| `IoRequest` | `{ IoOp op (eRead, eWrite); Arci<IoFile> file; u64 offset; std::span<_::byte> buffer; IoCompression compression = eNone; u64 tag = 0; Arci<void> keepAlive = {}; }`. `buffer` must stay alive until the batch future resolves. A non-empty `keepAlive` is held by the batch until the request completes (**Decided** Q03.6, section 2.4). |
| `IoCompletion` | `{ IoStatus status (eDone, eShort, eCancelled, eFailed); u32 bytes; u32 osError; }`, one per request, in request order. |
| `IoQueue` | Created by `IoSystem::createQueue(IoPriority)`. `submit(Vector<IoRequest>) -> Future<Vector<IoCompletion>>` gives one future per batch. `cancel(u64 mask, u64 value)` cancels every request whose `tag & mask == value`. Batch futures of one queue resolve in submission order. |
| `IoSystem` | Owns the `IoThread`, the backend and the in-flight budget: `start()`, `stop()`, `open`, `createQueue`. |
| `IoBackend` | `issue(slot)`, `cancel(slot)`, `harvest(OVERLAPPED_ENTRY)`. `IocpBackend` issues overlapped `ReadFile` / `WriteFile`. `BlockingBackend` runs the same calls synchronously on the IO thread; it serves as the fallback, the test double and the throughput baseline. |

- **Priority belongs to the queue, not the request** (**Proposal**, deviating from the work page's `IoRequest` row). DirectStorage puts priority on the queue, and FIFO completion per queue only makes sense if one queue has one priority. The four levels stay **Decided**: `IoPriority { eLow, eNormal, eHigh, eRealtime }`.
- **Destination is host memory only** in this chunk. The GPU destination (W17, W18), a memory source and a cache-key source get added as variant alternatives later. A caller that builds a host request does not change when they arrive.
- **Compression**: only `eNone` is accepted. Any other value fails the request with `eFailed` until W03.5 picks a codec.

### 2.3 The IO thread loop

- `submit` posts the batch to the IO thread (`AffineThread::postDetached`) and returns the batch future. The fiber then decides whether to `await` it.
- On the IO thread, each queue keeps a FIFO of pending requests. While `inFlight < kMaxInFlight`, the thread issues the next request from the highest-priority non-empty queue. Within one priority level it takes queues round-robin. **Decided** (Q03.5): `kMaxInFlight = 64` as the starting value, measured and retuned in the W03.4 benchmark.

Why there is a cap, and why 64:

- **Priority only applies to requests that are still pending.** Once a request is issued to the OS it cannot be reordered or preempted. If the IO thread issued everything at once, a high-priority read submitted a moment later would queue behind every low-priority read already in the drive. The cap is the size of that non-preemptible window. A small cap keeps priorities responsive, and a large cap keeps the drive busy.
- **The drive needs some depth to reach its throughput.** NVMe drives reach full random-read throughput only with several requests outstanding. Small reads need tens, and large sequential reads need only a few. This document has not measured where the curve flattens on the target drives; 64 is the usual order of magnitude for one submitting thread.
- **64 matches the skeleton's harvest size.** `IoThread` collects up to 64 completions per `GetQueuedCompletionStatusEx` call, so with a cap of 64 one wake can harvest every outstanding request.
- **A higher cap costs no memory, only priority response.** Buffers belong to the caller, and a slot is one `OVERLAPPED` plus bookkeeping.
- **Decided** (Q03.5), **only if measurements show inversion**: reserve part of the budget for `eHigh` and `eRealtime`, for example low and normal together may hold at most 48 of the 64 slots. A high-priority read then always finds a free slot without waiting for a low-priority read to finish.
- Each issued request owns a slot that embeds its `OVERLAPPED`. The completion key is the slot's backend tag, and `wake_key` stays reserved. A harvested completion fills in the request's `IoCompletion`, frees the slot and issues the next pending request. When the last request of a batch finishes, the batch is marked done. The queue then resolves done batches from its front only, so batch futures resolve in FIFO order.
- `FILE_SKIP_COMPLETION_PORT_ON_SUCCESS` and handling a synchronous success inline: **Builder's call**.
- **Buffered overlapped I/O first** (**Proposal**). The work page asks for unbuffered, sector-aligned reads. But `FILE_FLAG_NO_BUFFERING` needs the offset, size and buffer address all aligned to the sector size, while package and archive ranges are arbitrary. Unbuffered I/O would therefore need bounce buffers or outward rounding. That code is only worth it once W03.5's numbers show a gain, so the open mode keeps a `eUnbuffered` flag that later work can turn on.
- **Pressure**: the in-flight budget is the only bound. Like the inbox, a submit never blocks (affine design section 8). Pending depth goes into a counter for S04.

### 2.4 Cancellation

`cancel(mask, value)` posts to the IO thread. Matching requests that were never issued complete as `eCancelled` immediately. For matching requests already issued, the thread calls `CancelIoEx(file, &slot.overlapped)`, and their completion still arrives through the port: as `eCancelled` on `ERROR_OPERATION_ABORTED`, or as `eDone` if the read won the race.

**Contract**: once a batch future has resolved, the OS writes nothing more into that batch's buffers. "Cancellation observed" means the future resolved. That is the only point where the guarantee can hold, because an issued overlapped read writes until its completion packet arrives. **Dropping the future does not cancel the batch.** If a caller destroys the batch future without awaiting it, the requests keep running to completion and their results are discarded. The reasons:

- **Cancelling on drop cannot make the buffer safe at the moment of the drop.** `CancelIoEx` only asks the OS to stop. An issued read can still write into its buffer until its completion packet arrives, which is some time after the drop. For a drop to be safe, the future's destructor would have to wait for that packet. A destructor that waits would park the fiber invisibly in the middle of scope cleanup, and on an affine thread it would hit the `await` assert.
- **The buffer is what matters, not the future.** The real hazard is a caller that drops the future and then frees or reuses the buffer while the OS is still writing into it. With or without cancel-on-drop, the buffer must stay alive until the batch completes.
- **A drop is the wrong place to signal intent.** Cancellation has its own explicit call, `cancel(mask, value)`. Futures are also moved and dropped in ordinary code (for example a `then` chain that ignores the result), and a side effect hidden in the destructor would surprise there.

So the rule is: the caller keeps every `buffer` alive until the batch future resolves. To cancel, call `cancel` and then await the future. The batch holds its own references to its `IoFile`s, so the files stay open while the batch runs. The IO thread keeps each batch until it completes. In debug builds, `IoSystem::stop` asserts if a batch would be destroyed unresolved.

**Decided** (Q03.6): the plain rule above is a lifetime contract that the compiler cannot check, so a caller that breaks it corrupts memory. Therefore `IoRequest` carries an optional owner of its buffer (`Arci<void> keepAlive`), held by the batch until the request completes. A dropped future with an owned buffer is then always safe, at the cost of one reference count per request. `IoFileBlob` would not use it, because it awaits every read; prefetch and streaming clients would.

### 2.5 Blobs over the IO thread

- **`IoFileBlob : Blob`** (`Engine.Resource.Blob/File/IoFileBlob.{hpp,cpp}`) holds an `Arci<IoFile>` and a queue. `read` and `write` submit one request and `await` it. On a fiber that parks the fiber, not the worker. `trim` posts `SetFileInformationByHandle` to the IO thread. `size` is read once (`GetFileSizeEx`, on the IO thread) at construction, then kept current by writes past the end and by `trim`; `Blob::size` is `noexcept` and must not park. All existing parsers keep working unchanged: every `Blob::read` costs one park.
- **Package parse cost**: three parks (header, index, footer), paid once per cached package stage (section 1). **Proposal**: no speculative window in the first version. Affine design section 12 expected one, but W03.1 already makes the parse a one-time cost. Add it if the trace shows package opens on a hot path.
- **`WindowedBlob : Blob`** (`Engine.Resource.Blob/WindowedBlob.{hpp,cpp}`) wraps a source blob, a base offset, a size and a window size. It is created per guard. The first read fetches the window that contains the offset; reads inside that window are memory copies, and a miss fetches the next window (one park each). **Proposal**: `kArchiveWindow = 8 MiB`. Any archive up to that size is resident after one park, so walking it touches only memory (affine design section 12). A larger archive (cell and level archives) streams window by window. Bulk binary data (micropolygon pages, 8K textures) never goes through this path; W17 and W18 page it.
- **Where the residency lives**: the `PackArchive` and `BlobArchive` query stages build `StorageReadonlyArchive` over a `WindowedBlob`, one per accessor. The cached stage from section 1 keeps only the linked range (offset, size, type). Bytes are therefore never cached across queries (affine design section 12, "no cross-query cache in the first version"). Byte caching belongs to the residency manager.
- **Which blob a stage uses**: once `IoSystem` runs, the `LfsBlob` query and mutation stages build an `IoFileBlob`. `LfsSyncBlob` stays for tools and tests that run without the IO thread. The `FiberMutex` from W03.2 task 1 then guards only that sync path.
- **Writes take the same path** (affine design section 12): `IoFileBlob::write` submits an `eWrite` request, so a package commit parks its fiber instead of blocking a worker.
- **Affine threads never call storage.** `await` already asserts there. The platform thread, the IO thread and the audio device thread must post such work to a fiber. The editor import already runs outside the input tick (commit `8f5b27cc`).

### 2.6 `queryAsync` and `mutateAsync`

Each overload becomes `async([storage, fn] { guard = fetchQuery(storage); return guard(fn); })`. The whole body runs as a scheduler task, and its blob reads park that fiber. The overloads return `Future<Result<R, async_..._error>>` as they are declared today. The `todo_panic` calls are removed. The sync `query` and `mutate` use the same blobs: on a fiber they park, and on a plain thread (boot, tests) they block that thread. No separate async stage machinery is needed.

### 2.7 Ownership and shutdown

- `StorageModule` (`Engine.Storage`) owns the `IoSystem` (**Proposal**). Storage is the only client in this chunk, and the module already exists in both engines. The audio and transfer-queue clients (affine design section 11) can take a reference later.
- `IoSystem::start` runs in `StorageModule::setup`, before `boot::initStorage` indexes any asset. `GameEngine` never calls `_storage.setup` today (checked 2026-11-09), so the game runtime keeps the `LfsSyncBlob` path until it does; wiring storage into the game engine is not part of this chunk. `stopIo()` on a never-started `IoSystem` is a no-op. `EditorEngine::stop` and `GameEngine::stop` call `_storage.stopIo()` next to `_platform->tidy()`: after every module has been destroyed, and before `_resources->destroy()` and `_scheduler->destroy()`. The IO thread's final drain resolves promises, and that needs a live scheduler (affine design section 6).
- Stop order inside `IoSystem::stop`: cancel all requests → keep the loop running until every in-flight slot has completed → stop the affine thread. In-flight buffers therefore never outlive their batch.
- The `Dispatcher` stub (`Engine.IO.Dispatcher/Dispatcher.{hpp,cpp}`) is deleted.

### 2.8 Tests

| Test (`Engine.IO.Dispatcher.Test` unless noted) | Proves |
|---|---|
| `IoSystemTest.ReadBatchReturnsBytes` | a batch of 16 reads at mixed offsets fills each buffer with the file's pattern; completions come back in request order |
| `IoSystemTest.WriteThenReadRoundTrips` | an `eWrite` batch, then an `eRead`, returns the written bytes |
| `IoSystemTest.ShortReadAtEndOfFile` | a read past EOF gives `eShort` with the right `bytes` |
| `IoSystemTest.BatchesResolveFifoPerQueue` | three batches on one queue resolve in submission order, even when the first is the largest |
| `IoSystemTest.ThousandRequestsHonourPriority` | 1,000 requests over three queues (low, normal, high) submitted at once: the mean completion rank of high < normal < low; a probe fiber keeps running during the run (no worker blocked) |
| `IoSystemTest.CancelledBufferUntouchedAfterResolve` | 64 large reads into sentinel buffers, cancelled by tag: after the future resolves, the buffers of `eCancelled` requests still hold the sentinel 50 ms later |
| `IoSystemTest.StopDrainsInFlight` | `stop()` with requests in flight returns after all of them complete; no completion arrives afterwards |
| `IoSystemTest.BlockingBackendMatchesIocp` | the same batch on both backends gives identical bytes and statuses |
| `WindowedBlobTest.SmallRangeIsOnePark` (`Engine.Storage.Test`) | an archive range below the window size triggers exactly one source read |
| `WindowedBlobTest.LargeRangeStreamsWindows` | a 20 MiB range read end to end triggers three source reads |
| `AsyncStorageTest.QueryAsyncReadsArchive` (`Engine.Storage.Test`) | `queryAsync` of an archive in a file-backed package returns the archive's bytes; no `todo_panic` is reachable in `Engine.Storage.*` |
| `AsyncStorageTest.MutateAsyncCommits` | `mutateAsync` adds an archive; a following query sees it |

Measurement (in the PR, not in a test): IOCP versus `BlockingBackend` throughput on the developer NVMe for 64 KiB and 1 MiB random reads, with the hardware stated (issue #85 done-when).

### 2.9 Left for later

- Unbuffered aligned I/O (behind `eUnbuffered`), a speculative header window, coalescing of adjacent ranges. All three need W03.5's measurements first; the exploration says queue depth matters more than ordering on NVMe.
- Codecs, GPU destinations, DirectStorage, io_uring, the remote cache tier.
- Per-client in-flight budgets beyond the per-system `kMaxInFlight`; the residency manager owns those.
- Byte caching across queries (residency manager).
