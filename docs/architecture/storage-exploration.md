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

**Status**: drive, codec and chunk-size runs are measured. Owner rulings of 2026-11-18 are on the [storage work page](../plan/work/storage-streaming.md) (Decisions): LZ4HC 9 per 64 KiB chunk, not the zstd proposal below; cap 32 as a setting; request size still open.

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

### 6.2 Codecs at 64 KiB chunks

**Setup.** The tool `codecbench` cuts each file into independent 64 KiB chunks and compresses each chunk on its own. A chunk that does not shrink is stored raw. Every round trip is verified. Compression runs on 24 threads. Decoding is timed on 1 thread (best of 2) and on 12 threads, from memory and excluding IO. The owner ran it on 2026-11-17 over `assets/**`: 106 files, 985 MiB, clang-cl `/O2`, 5900X.

**The corpus has no block-compressed textures.** Every texture is raw:

- KTX2 (597 MiB): RGBA8 UNORM (3 files), R16 SFLOAT (4), RGBA16 SFLOAT (2) and RGBA32 SFLOAT (1). None uses supercompression.
- KTX (386 MiB): sRGB8 alpha8 (12 files), RGBA8 (2), R16F (4), RGBA16F (4) and RGBA32F (1).

So the desk numbers for BCn data (cbloom: zstd-22 1.70, zlib-9 1.64, LZ4HC 1.55, about ×1.65 with RDO) do not describe this corpus.

| Codec | Ratio | Compress MiB/s per thread | Decode MiB/s, 1 thread | Decode MiB/s, 12 threads | Cores to decode at the 3.3 GiB/s drive ceiling |
|---|---|---|---|---|---|
| none | 1.00 | n/a | n/a | n/a | 0 |
| LZ4 | 1.16 | 140 | 3,930 | 25,238 | 1.0 |
| LZ4HC 9 | 1.29 | 31 | 4,036 | 24,497 | 1.1 |
| LZ4HC 12 | 1.29 | 15 | 3,885 | 20,928 | 1.1 |
| zstd 1 | 1.40 | 127 | 1,152 | 7,781 | 4.1 |
| zstd 3 | 1.47 | 79 | 956 | 6,417 | 5.2 |
| zstd 9 | 1.54 | 25 | 814 | 5,202 | 6.4 |
| zstd 19 | **1.60** | 3.6 | 555 | 3,583 | 9.7 |
| zlib 6 (vendored) | 1.53 | 5.4 | 308 | 2,433 | 16.8 |
| zlib 9 (vendored) | 1.53 | 5.0 | 303 | 2,550 | 17.1 |
| libdeflate 6 | 1.54 | 47 | 448 | 3,738 | 11.6 |
| libdeflate 12 | 1.58 | 9.8 | 437 | 3,780 | 12.2 |
| GDeflate 6 (CPU) | 1.53 | 21 | 220 | 1,810 | 23.5 |
| GDeflate 12 (CPU) | 1.58 | 4.5 | 217 | 1,789 | 24.6 |

The last column is the drive rate (3,300 MiB/s compressed) times the ratio, divided by the single-thread decode speed. It is the CPU cost of streaming at full drive speed. The ratios by class are close to each other: KTX 1.59 and KTX2 1.61 with zstd 19. The 1.7 MiB of meshes and fonts reaches 2.4 but does not move the total.

Findings:

- **On this corpus, the codec is not the main lever; texture encoding is.** Raw RGBA8 and RGBA16F compress only 1.3 to 1.6 times with any codec. Encoding them to BC7 or BC6H at import would shrink them 4 times, or 8 times for BC1 and BC4, before any codec runs. Decide the codec again on a BCn corpus, after the texture import pipeline encodes block formats.
- **zstd gives the best ratio and an ordinary decode cost.** Level 19 at cook time reaches 1.60, and decoding does not get slower as the level rises (555 against 1,152 MiB/s for level 1 on this float-heavy data). One codec with a cook-time level covers the whole range from LZ4-like speed to deflate-like size.
- **LZ4HC is the cheap option**: 1.29 for about one core at full drive speed.
- **Deflate is dominated.** zlib is slower than libdeflate at the same ratio. On the CPU, GDeflate decodes at half the speed of libdeflate at the same ratio. GDeflate pays off only with a GPU decoder (6.3).

Proposal for **Q03.3**:
- Use **zstd per 64 KiB chunk**. The level is chosen per asset class at cook time, 19 by default. A chunk that does not shrink is stored raw, which needs a flag per chunk.
- Decode on the Background lane.
- No second codec until a BCn corpus shows that one is needed. Measured trade-off: LZ4HC costs a ninth of the CPU at 0.8 times the ratio.
- Neither vendored zlib nor GDeflate goes in the package path.
- The texture import pipeline (BCn encoding) belongs on its own chunk. It saves more than any codec choice.

**Chunk size**: the owner ran the sweep on 2026-11-17. The table gives the ratio over the whole corpus.

| Codec | 16 KiB | 32 KiB | 64 KiB | 128 KiB | 256 KiB |
|---|---|---|---|---|---|
| zstd 19 | 1.56 | 1.58 | 1.60 | 1.63 | 1.65 |
| zstd 3 | 1.45 | 1.45 | 1.47 | 1.49 | 1.54 |
| libdeflate 12 | 1.53 | 1.56 | 1.58 | 1.59 | 1.60 |
| GDeflate 12 | 1.50 | 1.54 | 1.58 | 1.58 | 1.58 |
| LZ4HC 12 | 1.17 | 1.23 | 1.29 | 1.34 | 1.37 |

- From 64 KiB to 256 KiB, zstd 19 gains 3%.
- GDeflate stops improving at 64 KiB, its internal tile size.
- Decode speed per thread barely changes with chunk size.
- Plain LZ4 stores about 12% of chunks raw at 128 KiB and above (they don't shrink). LZ4HC does not have this problem.

**Proposal**: keep the 64 KiB compression unit. Larger chunks would gain about 3% in size, but every partial read would decode more data, and the GPU decode limits would be lost.

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
- The drive ceiling measured in 6.1 is 3.3 GiB/s. On the CPU (6.2), zstd 19 needs about 10 cores to keep up with the drive at that rate, and LZ4HC needs about one. Streaming rarely runs at the drive ceiling for long, so the realistic cost is a fraction of this.
- GDeflate matches zstd's ratio closely (1.58 against 1.60), but its CPU fallback decodes 2.5 times slower than zstd.

Answer: **no DirectStorage backend now.** Revisit when a BCn corpus shows that CPU decode costs more than the frame budget allows, or when `VK_EXT_memory_decompression` ships on both AMD and NVIDIA. GDeflate is the only format that extension decodes. A later switch costs only a re-cook if the chunk table records the codec per chunk; the package design should include that field.
