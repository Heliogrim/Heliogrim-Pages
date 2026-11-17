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

## 6. Codec, Chunk and Drive Measurements (W03.5, 2026-11-17)

**Status**: the drive half is measured. The codec half is built but not run (see 6.2). The proposals below are not decided.

### 6.1 Drive: queue depth and unbuffered reads

**Setup.** Samsung 970 NVMe (C:), Ryzen 9 5900X, Windows 11 26300. One IO thread on IOCP, harvesting 64 completions per `GetQueuedCompletionStatusEx`, as the engine's `IoSystem` does. The test file is 4 GiB of incompressible data. Reads are random and request-aligned, 2 s per point, clang-cl `/O2`. Spike source: engine checkout `docs/superpowers/spikes/w03-5-codec-io/` (untracked).

Unbuffered (`FILE_FLAG_NO_BUFFERING`), MiB/s, with p50 latency in µs:

| Request | QD 1 | QD 2 | QD 4 | QD 8 | QD 16 | QD 32 | QD 64 | QD 128 |
|---|---|---|---|---|---|---|---|---|
| 64 KiB | 599 (100) | 1,135 (103) | 1,996 (120) | 2,562 (179) | 2,612 (350) | 2,725 (711) | 2,689 (1,430) | 2,760 (2,895) |
| 256 KiB | 1,434 (170) | 2,977 (164) | 3,272 (293) | 3,323 (584) | 3,315 (1,169) | 3,311 (2,333) | 3,324 (4,676) | 2,858 (9,407) |
| 1 MiB | 1,850 (434) | 2,769 (588) | 2,848 (1,173) | 3,155 (2,344) | 3,371 (4,688) | 3,306 (9,376) | 3,311 (16,935) | 3,387 (31,774) |

Buffered overlapped reads with a cold cache, 64 KiB, each block read once: 181, 380 and 713 MiB/s at QD 1, 8 and 64. At QD 64 the p99 is 36 ms.

Findings:

- A 64 KiB request saturates the drive at QD 8 and tops out near 2.7 GiB/s, about 43k IOPS. A 256 KiB request reaches the drive ceiling of about 3.3 GiB/s at QD 4.
- Past saturation, extra depth adds only latency. At 64 KiB, p50 is 0.35 ms at QD 16 and 1.4 ms at QD 64. A 256 KiB request at QD 128 loses throughput.
- On cold data, buffered reads run 3.8 times slower than unbuffered ones at QD 64. W03.4 measured buffered reads only with the data already in the page cache (3.8 to 5.7 GiB/s), so that number says nothing about the drive.

Proposals for the owner:

- **Q03.5 (in-flight cap).** The current cap of 64 is deeper than this drive needs. A high-priority request admitted behind a full window waits for that window to drain: about 1.4 ms at 64 KiB, or 4.7 ms at 256 KiB. Proposal: a cap of 32 requests, or better a byte cap of about 4 MiB in flight per device. That gives full throughput at every request size above and keeps p50 under 1.2 ms. Suggested default: 32 requests, keeping the constructor argument.
- **Unbuffered reads for package chunks.** Use `FILE_FLAG_NO_BUFFERING` with sector-aligned buffers, offsets and lengths for streamed package data. Keep buffered reads for small metadata and editor files, where a warm cache pays. This is the measurement that [storage design](storage-design.md) section 2 deferred to W03.5. Implementing it needs its own chunk.
- **Chunk size against request size.** Keep the compression unit at 64 KiB. That is the GDeflate tile size and the per-region limit of `VK_EXT_memory_decompression`, and DirectStorage's GPU zstd is tuned for 256 KB or less. IO requests should be at least 256 KiB, made by coalescing adjacent chunks (section 2). Reading 64 KiB chunks one request at a time caps this drive at about 2.7 GiB/s.

Not measured: the SATA SSD (X:, which holds the checkout), more than one IO thread, the engine's own `IoSystem` in Release, and the effect of the drive's write cache on reads.

### 6.2 Codecs: not run yet

The tool `codecbench` is built. It cuts each file into chunks (16 to 256 KiB) and compresses every chunk on its own. A chunk that does not shrink is stored raw. The tool verifies every round trip and reports the ratio per class (ktx, ktx2, other), the compression speed per thread, and decode speed on 1 and 12 threads. Configurations: none; zlib 1, 6 and 9; libdeflate 6 and 12; GDeflate 1, 6, 9 and 12; LZ4, LZ4HC 9 and 12; zstd 1, 3, 9 and 19.

**Why it did not run.** The benchmark reads the bytes of `assets/**`, and the project instructions forbid agents to read that folder. Auto mode refused the run. The owner either runs `build.sh` in the spike folder or allows the read; the run takes minutes.

What is known without reading the content: the corpus is 986 MiB. Of that, 597 MiB is KTX2 (10 files), 386 MiB is KTX (23 files), and under 2 MiB is meshes and fonts. The tool also prints each KTX2 `supercompressionScheme`. If the KTX2 files already use zstd or Basis supercompression, a package codec on top gains almost nothing on them.

Desk evidence on BCn data (cbloom 2020, Oodle test set, measured by the source): zstd-22 reaches 1.70:1, zlib-9 1.64:1 and LZ4HC 1.55:1. Rate-distortion-optimised (RDO) encoding multiplies these by about 1.65. BC7 without RDO compresses by under 10%. Microsoft's GACL (preview) claims up to 50% better zstd ratios through BCn bit shuffling, but the decoder undoes the shuffle only for BC1, BC3, BC4 and BC5 today. The likely conclusion for this corpus: texture encoding (RDO, stream splitting) matters more than the choice of codec. The run must confirm this.

| Candidate | Version measured | Licence (from source) |
|---|---|---|
| zlib | 1.3.1 (vendored) | zlib |
| libdeflate | DirectStorage fork 8ba9502 | MIT; GDeflate parts Apache-2.0 |
| GDeflate | microsoft/DirectStorage 303a7d2 | Apache-2.0 (SPDX header); repository MIT |
| LZ4 | 1.10.0 | BSD-2-Clause (library) |
| zstd | 1.5.7 | BSD-3-Clause or GPLv2, dual |
| DirectStorage runtime | not used | headers MIT; redistributable DLL under its own NuGet `LICENSE.txt` (not read) |

### 6.3 DirectStorage PC: provisional answer

Desk research (agent, 2026-11-17). Vendor claims are marked as such.

- DirectStorage PC stable is 1.3.0 (2025-06). Version 1.4 adds zstd on CPU and GPU but is still a preview (preview2, 2026-06-16). Microsoft labels its GPU zstd shaders "not for production". Optimised drivers are promised for the second half of 2026 (vendor claim).
- The GPU path is D3D12-only. The only Vulkan route is importing a D3D12 heap through `VK_KHR_external_memory_win32`, and no shipped engine is known to do it. The Vulkan-native route is `VK_EXT_memory_decompression` (promoted from the NV extension), which supports GDeflate only, with 64 KiB regions. Which drivers ship it is unknown.
- Shipped GPU decompression has a stutter record on RTX 40. In Spider-Man 2 on an RTX 4090, turning DirectStorage off raised 1% lows by 18 to 25% (Tom's Hardware, 2026-03-27). Ratchet & Clank users report frame-time spikes that went away with the CPU fallback.
- The drive ceiling measured in 6.1 is 3.3 GiB/s. On the CPU, the decoders run at a few GB/s per core (unmeasured here until 6.2 runs). Keeping up with the drive should cost a few cores on the Background lane.

Provisional answer: **no DirectStorage backend now.** Revisit when 6.2 shows CPU decode cost above budget, or when `VK_EXT_memory_decompression` ships on both AMD and NVIDIA. If GDeflate lands close to zstd on ratio in 6.2, choosing it keeps the GPU path open through the Vulkan extension, without D3D12.
