# Storage Engine (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

**Origin**: distilled on 2026-11-04 from a Gemini conversation ([link](https://gemini.google.com/app/350ae0724dcc30cd)). The raw notes are not kept. Claims were not re-verified against the engine source or the hardware in this pass.

## 1. Current Engine Behaviour (as described by the owner)

- Storage exposes `fetch`, `fetchAsync`, `mutate` and `mutateAsync`. They take a callback and a storage object that unifies memory, files, blobs, virtual packages and virtual archives.
- Template types drive a multi-level resolver stack. For example `Archives -> Package -> File`. Each level hands the next level a provisioned interface.
- Fetch and mutate guards each hold a resource lock, the provisioned interface and a cleanup function. Errors unwind in reverse order.
- Mutations are buffered in the guard. On normal scope exit they are compacted and applied to the underlying sequence. The lock is released afterwards.
- Stack resolution is cached. Mutations invalidate affected cached stacks.
- Loaders for graphics and assets receive `Blob` views, which are staged into Vulkan staging buffers and copied into sparse images.
- Locations are URLs with schemes such as `file+project`, `file+editor`, `file+cache`. Archives are addressed as `archive://<guid>`. Mount points resolve the URLs.

## 1a. Current State in Engine (checked 2026-11-04)

Section 1 mixes the existing code with the vision. What exists:

- `StorageSystem` (`Engine.Storage.System`) exposes `query` and `mutate` for blobs, packages and archives, each through a `fetchQuery` or `fetchMutation` guard (`IoQueryGuard`, `IoMutationGuard`). The code says `query`, not `fetch`.
- `queryAsync` and `mutateAsync` exist as signatures returning `Future<Result<...>>`. Their bodies are `todo_panic()`.
- All file I/O is synchronous. `LfsSyncBlob` wraps a `std::fstream`. There are no I/O threads. `Engine.IO.Dispatcher` is a stub.
- The resolver stack (`Engine.Storage.Action`: static and dynamic stages, `StageResolutionFactory`, `ActionTypeResolutionCache`) is **rebuilt on every call**. `ResourceObjectStore` can hold resolved objects with their dependencies, but stacks are not reused across calls. Stack caching, cache invalidation and the coalescing ideas are vision, not code.
- URL schemes in `Engine.Storage.Registry/Url/Scheme.hpp`: `file`, `file+project`, `file+editor`, `file+runtime`, `file+cache`, `archive`, `mem`, `package`. Each maps to a repository (Project, Editor read-only, Runtime, Cache, Archive, Memory, Package).

Consequence for ordering: the first missing piece is not a Windows batching backend. It is (1) reusing resolved stacks, and (2) any async path at all, where a query suspends the calling fiber until an I/O completion arrives. Batching and coalescing come after both and need measurement.

## 2. Direction Agreed in the Conversation

- **Two front ends, one engine.** Keep `fetch` and `mutate` for general and scripted I/O, and add a fluent pipeline builder for streaming (for example sparse texture mips). The builder compiles down to the same core primitives. It does not get its own engine.
- **Fiber integration.** A fiber that waits on I/O suspends. The I/O thread never calls into the fiber scheduler directly. It posts the completion to a thread-safe inbox that the scheduler drains.
- **Dedicated I/O threads.** Requests are coalesced per batch (sorted by offset, adjacent ranges merged) before submission.

## 3. Problems to Resolve Before Design

- **io_uring is Linux-only.** The engine targets Windows first (`win32` in the environment). The design needs a Windows backend, most likely IOCP or overlapped I/O, behind the same interface. The io_uring sketches apply to the Linux backend only.
- **Invalidate-before-commit race.** The sketch calls `invalidate_prefix` and then runs the mutation. A fetch that runs between the two can re-cache pre-mutation data. Invalidate after commit, while still holding the write lock.
- **Cache entries own file handles.** A cached `shared_ptr<ResolvedStack>` may hold a handle that an in-flight fetch guard still uses. Invalidation must not close a handle that a live guard holds. Use refcounts or an epoch.
- **Busy-wait in the sketch.** `std::this_thread::yield()` in the I/O loop burns a core when idle. Use an event or futex wait that the submit path signals.
- **LBA sorting helps only within one file.** Packages map logical offsets to file offsets, so sorting by offset is meaningful only inside one package. On NVMe, queue depth usually matters more than ordering. Benchmark before building coalescing.
- **Intel IAA availability.** The source says "server-grade or high-end desktop". IAA is on Intel Xeon server parts only. Check the target hardware matrix before planning on it.
- **Direct NVMe to VRAM.** GPUDirect Storage is NVIDIA-specific. Vulkan has no generic equivalent. Plan on host bounce buffers now. Treat a direct path as a per-vendor later option.
- **Unsourced performance claims.** The throughput and latency gains in the source are not sourced. Measure before relying on them.

## 4. Open Questions

- The package layout PDF has not been shared yet. The index and TOC details depend on it (see [serialization evolution](serialization-evolution-exploration.md)).
- Stack cache size and eviction policy.
- Whether stack resolution should be keyed by path, by type, or by both.
- Mutation compaction rules: merge, sort and deduplicate, and what counts as a conflict.
- What a Windows backend needs for the same batching and coalescing.

## 5. Related

- [Serialization evolution](serialization-evolution-exploration.md): package layout, index tables, URL schemes.
- [Observability](observability-exploration.md): I/O latency histograms and queue-wait spans.
- [Pointer sets](pointer-sets-exploration.md): lookup structures for resolved-stack caches.
