# Work: Storage, Streaming, Memory, Virtual Textures, World Partition

**Systems** S03, S08, S17, S40 · **Issues** [#85](https://github.com/Heliogrim/Heliogrim-Engine/issues/85), [#90](https://github.com/Heliogrim/Heliogrim-Engine/issues/90), [#97](https://github.com/Heliogrim/Heliogrim-Engine/issues/97), [#120](https://github.com/Heliogrim/Heliogrim-Engine/issues/120); absorbed #24, #73, #80 · **Track** A, B, C · **Milestone** M1 to M2
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Storage and streaming](../topics/storage-streaming.md).

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Storage exploration](../../architecture/storage-exploration.md) | Current state (sync only, `queryAsync` is `todo_panic`, stack rebuilt per call); the order: stack reuse, then any async path, then batching after measurement; problems: io_uring is Linux-only, invalidate-after-commit, cached stacks owning handles, busy-wait, LBA sorting value | Stack cache key and eviction; mutation compaction rules; the package layout PDF was never shared |
| [Serialization evolution exploration](../../architecture/serialization-evolution-exploration.md) | Package header and footer layout, CRC on store, open TODOs in `Processor.cpp` | Content addressing is S41's; S03 only consumes chunk boundaries |
| [Actor archetypes design](../../architecture/actor-archetypes-design.md) | Regions per level; "streaming cell as handle space" left for later; epoch-based handle invalidation | S40 picks this up; cell activation must respect the frame-boundary rule of the design |
| [Bounding volumes exploration](../../architecture/bounding-volumes.md) | Spatial query options | The cell grid is a coarse spatial index; the fine index stays with S44 |
| [Pointer sets exploration](../../architecture/pointer-sets-exploration.md) (closed) | Keep ankerl for lookup tables | Stack cache uses ankerl maps |
| Issue #73 | Archive delta merge stream | Cell persistence writes deltas through it |
| Issue #24 | Shader read-operation URL bug | First bug to close with the resolved-stack reuse |

## Architecture

- **Bundles**: `Engine.Storage.*` keeps registries, actions, packages. New `Engine.Storage.Backend` (`IoBackend` interface, Windows IOCP implementation, generic thread-pool fallback) running on an `AffineThread` (S02). New `Engine.Resource.Residency` (budgets, priorities, eviction). New `Engine.Memory` (tracked allocators, arenas). New `Engine.Graphics.Texture.Virtual` (page tables, feedback, transcode). New `Engine.World.Partition` replacing `Engine.Level` as the actor container.
- **Layer**: storage, residency and memory in L2; virtual textures in L3 rendering; partition in L3 world.
- **Provides**: `IoRequest` submission with priorities and cancellation; residency budgets and eviction events; tagged allocation reports; virtual texture page service; cell grid (2D quadtree over fixed leaf cells, optional height layers per leaf; Q40.1, Q40.2), cell lifecycle, cell persistence.
- **Consumes**: `AffineThread` and `Waitable` (S02), `Diagnostic` (S05), spans and counters (S04), record headers and checksums (S01), `DoubleVec3` world positions (S07), feedback buffer from the material resolve pass (S15).

```hg-diagram
flowchart LR
    SYS["Requesters<br/>partition cells, VT feedback, audio banks, geometry pages"] --> RES["Residency<br/>budget per class, priority, eviction"]
    RES --> Q["IoQueue<br/>batch submit, tag cancel"]
    Q --> BE["IoBackend on AffineThread<br/>IOCP / thread pool / io_uring"]
    BE -->|FIFO completion| W["Waitable"]
    W --> DEC["Decode / transcode<br/>Background lane"] --> RES
```

## Code design

| Type | Contract |
|---|---|
| `ResolvedStage` / `ResolvedStack` | A stack is a chain of immutable `ResolvedStage` nodes, each `Arci`-counted and pointing at the stage below it (archive → package → file). `StackCache` caches per stage, keyed by the stage's own resolution input (resolver type, action type, the URL part it consumed); a new request reuses the longest cached prefix and resolves only the missing stages on top (decision Q03.1). A cache hit is always valid: a commit invalidates the mutated stage and every stage above it under the write lock; in-flight guards keep their chain alive. |
| `IoRequest` | `{ source: variant<FileRange, MemoryRange, CacheKey>, destination: variant<HostBuffer, GpuUpload>, priority: 4 levels, tag: u64, completion: Arci<Waitable> }`. |
| `IoQueue` | `submit(span<IoRequest>)`, `cancel(tag mask)`; FIFO completion per queue; a cancelled request never writes its buffer after cancellation is observed. |
| `IoBackend` | Interface implemented by `Iocp` (unbuffered, sector-aligned), `ThreadPoolPread` (fallback and tests), later `IoUring` and `DirectStorage`. Lives on an `AffineThread`. |
| `StorageSystem::queryAsync` | Returns `Future<Result<Blob, Diagnostic>>` backed by a waitable; `todo_panic` removed. |
| `ResidencyManager` | `Budget` per `ResourceClass` (textures, geometry pages, audio, navmesh tiles, cells); `request(key, priority, cost)`, `release`, `evict`; emits eviction events to S04 counters. |
| `TrackedAllocator` | `allocate(size, align, Tag)`; per-tag live and high-water counters; `Arena` per frame, per cell, per request; exceeding a budget emits a `Diagnostic`, never aborts. |
| `VirtualTexture` | Page table texture (software indirection first), `FeedbackBuffer` consumer, `PageRequest` priority from mip and screen coverage, pinned low-mip fallback, transcode task on the Background lane. `sparseResidency` evaluated behind a flag. |
| `CellCoord` | `{ i32 x, y, z? }` derived from `DoubleVec3` and the cell size from Q40.1. |
| `Cell` | Owns archetype regions, asset references, terrain and navmesh tile handles; states `Unloaded, Loading, Resident, Active, Unloading`; activation at a frame boundary; handles resolve to `None` while not active (epoch bump). |
| `Partition` | Cell grid, interest sources (viewers, server interest), priority by distance, budget through `ResidencyManager`; `Level` becomes a named `CellSet`. |
| `CellPackage` | One package per cell (S41), edits written as deltas through #73's merge stream. |

Placement: `Engine.Storage.Backend/{IoRequest,IoQueue,IoBackend,Iocp}.{hpp,cpp}`, `Engine.Storage.Action/StackCache.{hpp,cpp}`, `Engine.Resource.Residency/`, `Engine.Memory/`, `Engine.Graphics.Texture.Virtual/`, `Engine.World.Partition/{CellCoord,Cell,Partition,CellPackage}`. Tests per bundle; the 1,000-request test and the cancellation test live in `Engine.Storage.Backend.Test`; the fly-over test is a scene fixture (S61).

## Work chunks

### W03.1 Resolved-stack reuse · design+plan · done 2026-11-09

- **Result**: [storage design](../../architecture/storage-design.md) section 1; plan in the engine checkout `docs/superpowers/plans/2026-11-09-resolved-stack-reuse.md` (5 tasks). Finding: type-level chains were already cached; what is rebuilt per call is the runtime stage state, and overlapping queries on one package hit an assert. Stage key = (storage instance, resource type); query stages only; per-primary shared lock; one invalidation rule (the whole chain over the mutated primary); 512-entry bound as a stopgap; #24 reduces to routing `read_shader_file` through storage.

- **Goal**: cache resolved stacks per stage with prefix reuse and guard-safe lifetime (Q03.1); close #24 on the way. The design names, for each existing resolver, what its stage key is and which commits invalidate it.
- **Inputs**: `Engine.Storage.Action` (`StageResolutionFactory`, `ActionTypeResolutionCache`, `ResourceObjectStore`), exploration section 3.
- **Output**: short design section in `architecture/storage-design.md`; plan.
- **Questions**: Q03.1.

### W03.2 Implement stack cache · execute · done 2026-11-13 (merged into `feat/wip` by PR #169); editor check and #24 open

- **Result**: engine PR [#169](https://github.com/Heliogrim/Heliogrim-Engine/pull/169), branch `feat/storage-stack-cache` (13 signed commits, stacked on #165 `refactor/lock-types`), merged into `feat/wip` on 2026-11-13 (head `027985d2`, not yet on `master`). The 13th commit keeps every storage test file under a swept per-process scratch root; the storage suite holds 97 tests. Executed subagent-driven from `docs/superpowers/plans/2026-11-09-resolved-stack-reuse.md`, then reworked after the owner review and a six-lens branch review: removal completes before it returns, mutations invalidate on every exit, archive stages are built per query (a shared archive cursor gave wrong reads under concurrency), and storage tests went from 50 to 97 with bad paths first. Every commit builds and passes on its own. Deviations and shortcuts: [storage design](../../architecture/storage-design.md) 1.9. Open: the editor shader-load check (the editor does not build on the base branch, `EditorInit.cpp` `initDefaultUi`), so #24 stays open until the owner confirms; nested calls on one primary can deadlock (#166); relative `file+editor` URL resolution, the `pack(1)` header fix, "mutation callback `false` still commits" and "a query creates a missing file" are issue drafts for the owner.
- **Plan**: engine checkout `docs/superpowers/plans/2026-11-09-resolved-stack-reuse.md` (5 tasks).

- **Done when**: a query resolves its stack once per scheme; a mutation invalidates after commit; #24 closed with a test.

### W03.3 Async request path and IOCP backend · design · done 2026-11-09

- **Result**: [storage design](../../architecture/storage-design.md) section 2; plan in the engine checkout `docs/superpowers/plans/2026-11-09-async-storage-iocp.md` (5 tasks, runs after W03.2). Proposals open to the owner: priority per queue instead of per request (DirectStorage model, needed for FIFO per queue); buffered overlapped I/O first, unbuffered behind a flag after W03.5; `IoFileBlob` makes every `Blob::read` one park, so the parsers stay unchanged and sync `query` parks too; `WindowedBlob` with 8 MiB windows, per guard, keeps archive walks in memory; `kMaxInFlight = 64`; `StorageModule` owns the `IoSystem`, stopped next to `_platform->tidy()`; `GameEngine` never sets up storage today and stays on `LfsSyncBlob`.

- **Goal**: `IoRequest`, `IoQueue`, `IoBackend`, the IOCP implementation, the removal of `todo_panic` in `queryAsync` and `mutateAsync`. The interface is shaped so a DirectStorage backend drops in later (decision Q03.2): file range to host or GPU destination, batch submit, queue-level completion, a compression-format field per request.
- **Inputs**: `docs/packages.pdf` in the engine checkout (package layout; older than the code, the source is the reference where they differ).
- **Inputs from W02.3**: [affine threads design](../../architecture/affine-thread-design.md) section 12 (the fiber callback stays on the fiber, the IO thread moves byte ranges; header, index, archive batches; windowed fallback for large cell archives; in-flight budgets, coalescing and cancellation as the pressure levers) and the `IoThread` skeleton with its completion port.
- **Output**: `architecture/storage-design.md` main section; plan.
- **Questions**: Q03.2.

### W03.4 Implement async storage · execute · done 2026-11-16 (merged into `feat/wip` by [PR #180](https://github.com/Heliogrim/Heliogrim-Engine/pull/180)); editor run done

- **Result**: engine branch `feat/async-storage` (from `feat/wip` at `027985d2`): `IoSystem` with IOCP and blocking backends, four priority levels per queue, FIFO batch futures, tag cancellation through `CancelIoEx`, a draining `stop()`, `IoFileBlob` and `WindowedBlob` (8 MiB), local-file stages on the IO thread with a sync fallback, `StorageModule` ownership, `queryAsync`/`mutateAsync`. Tests: IO.Dispatcher 17, Storage 110, Storage.Package 7. A whole-branch review (six lenses) found two blockers from untrusted package ranges, both fixed (archive ranges are validated against the package size). Throughput (Debug, page-cached, 5900X): 64 KiB IOCP 3,855 vs blocking 4,299 MiB/s; 1 MiB 5,695 vs 5,158 MiB/s. This measures dispatch overhead, not the drive, so Q03.5 (in-flight cap) stays at 64 and moves to W03.5. As-built deviations: [storage design](../../architecture/storage-design.md) 2.10.
- **Result (head)**: `384baadc`. The final review's shutdown-ordering regression is fixed: `StorageModule::stopIo` now stops the IO thread first and then clears the stack cache, so queries that start after the stop resolve sync stages. A query already past the IO check can still cache an IO-backed stage after the clear (its reads come back empty); this is noted as a `shortcut:` in the code. The IOCP backend now registers each slot before it issues the read.
- **Merged**: PR #180 landed in `feat/wip` on 2026-11-16 (head `f9ee8b8f`, not yet on `master`).
- **Editor run**: done by the owner before the merge (2026-11-16).
- **Scope (owner, 2026-11-13)**: `StorageRegistry::removeProvider`/`removeRepository` keep their `todo_panic` for now; they are registry removal, not the request path, and nothing calls them. The "no `todo_panic` in storage" clause below covers the query and mutation path only.

- **Plan**: engine checkout `docs/superpowers/plans/2026-11-09-async-storage-iocp.md` (5 tasks), revised 2026-11-13 against the merged stack cache ([storage design](../../architecture/storage-design.md) 2.10: branch base `feat/wip`, archive stages already per query, no `IoFile` on `LocalFileStorage`, `FILE_SHARE_DELETE` and `OPEN_EXISTING` for reads, `InheritMeta` blobs, `Context::io`). Executed subagent-driven in the worktree `Heliogrim-CLion-wt/async-storage`; the editor start stays with the owner, next to the W03.2 editor check.

- **Done when**: 1,000 concurrent requests across three priorities complete through the IO thread with priorities honoured; cancellation observed; no `todo_panic` on the storage query and mutation path (registry removal excluded, see Scope).

### W03.5 Codec and chunking benchmark · explore · done 2026-11-17; owner ruled 2026-11-18 (see Decisions)

- **Result (codecs)**: the owner ran the 64 KiB codec benchmark ([storage exploration](../../architecture/storage-exploration.md) 6.2).
  - The corpus has no BCn textures: all 985 MiB are raw RGBA8, RGBA16F and RGBA32F, none supercompressed.
  - Ratios: zstd 19 reaches 1.60, libdeflate 12 1.58, GDeflate 12 1.58, zlib 9 1.53 and LZ4HC 1.29.
  - CPU cost to decode at the drive ceiling: zstd 19 about 10 cores, LZ4HC about 1, GDeflate on the CPU about 25.
  - Proposal for Q03.3: zstd per 64 KiB chunk, with the level chosen per asset class at cook time and raw storage for chunks that don't shrink; no second codec; no DirectStorage.
  - The bigger lever is BCn encoding at import (4 to 8 times smaller). It needs its own chunk, and the codec choice should be re-checked on a BCn corpus.

- **Result (drive half)**: [storage exploration](../../architecture/storage-exploration.md) section 6.
  - Samsung 970 NVMe, one IOCP thread, unbuffered: 64 KiB requests saturate at QD 8, at about 2.7 GiB/s. 256 KiB requests reach the 3.3 GiB/s ceiling at QD 4.
  - Buffered reads on a cold cache reach 713 MiB/s at QD 64, 3.8 times slower than unbuffered.
  - Proposals:
    - Q03.5: lower the cap to 32 requests, or a byte cap of about 4 MiB, because QD 64 only adds latency (p50 1.4 ms at 64 KiB).
    - Read package chunks unbuffered.
    - Keep the 64 KiB compression unit, but coalesce IO requests to at least 256 KiB.
    - No DirectStorage backend now: its GPU path is D3D12-only and zstd on GPU is still a preview. Revisit when `VK_EXT_memory_decompression` is on AMD and NVIDIA.
  - The codec tool is built: zlib 1.3.1, libdeflate, GDeflate, LZ4 1.10.0 and zstd 1.5.7, 16 to 256 KiB chunks. Spike folder: engine checkout `docs/superpowers/spikes/w03-5-codec-io/` (untracked).
  - The owner ran the codec benchmark, because it reads `assets/**`, which agents may not read. The owner also ran the chunk-size sweep (16 to 256 KiB). Going from 64 KiB to 256 KiB gains only 3% for zstd 19, and GDeflate stops improving at 64 KiB, so the 64 KiB unit stays.

- **Rulings (owner, 2026-11-18)**: see Decisions, rows Q03.3, Q03.5 and Q03.7 to Q03.10. Follow-up chunks: W03.6 and W03.7.

- **Goal**: measure no compression, zlib (vendored), LZ4, zstd and GDeflate (the format DirectStorage decompresses on the GPU; open specification, permissive reference implementation) on the project's assets at 64 KiB chunks; record each candidate's licence; decide the chunk size and whether DirectStorage PC's GPU decompression is worth a backend. Commercial codecs (Oodle) are out.
- **Output**: results in `architecture/storage-exploration.md`; answers Q03.3 by measurement.

### W03.6 IO tuning: package read path · execute · after W03.5

- **Goal**: the in-flight cap defaults to 32 and becomes a setting (kept as a constructor argument, read from config). Package chunks are read unbuffered (`FILE_FLAG_NO_BUFFERING`, sector-aligned buffers, offsets and lengths); metadata and editor files stay buffered. Adjacent wanted chunks coalesce into requests of about 256 KiB, never past what was requested (Q03.9). There is a byte budget in flight next to the 32-request cap.
- **Burst check (Q03.9)**: a mixed burst of bulk low-priority reads (start or level-load sized) with high-priority reads arriving during it, at byte budgets of 1, 2, 4 and 8 MiB. Record the burst makespan and the high-priority p50 and p99 per budget, then pick the default.
- **Later, own chunk if wanted**: a per-device auto-tune that grows the in-flight byte budget while throughput still rises and p50 latency stays under a target, and stops at the knee.
- **Done when**: the cap is configurable; a streamed package read is unbuffered; the W03.5 drive spike shows no throughput loss against its unbuffered numbers; the burst check has picked the default byte budget.

### W03.7 Texture import format and positional sub-region reads · design · after W03.5

- **Goal**: change the default texture import format, lossless while authoring in the editor (owner, Q03.10), with a block format (BCn) left to cook. Update the image loader and stream chain: today they rely on predictable tiling and memory layout to read a sub-region by reading only its byte ranges. With per-chunk compression and new formats, byte offsets are no longer computable, so the chain needs a positional reconstruction per format: an index from (mip, layer, tile) to chunk(s), with the compression chunk aligned to the tile so a sub-region read decodes only whole wanted chunks.
- **Output**: design section in `architecture/storage-exploration.md` or its own design page; plan.
- **Then**: re-check the codec on the new corpus (Q03.3 left the shipping codec open).

### W08.1 Memory model design · design · after W04.1

- **Goal**: tracked allocator, tags, arenas, budget diagnostics, reporting into spans and headless telemetry.
- **Inputs**: `pmr` arenas in render commands, `Engine.Common` allocators.
- **Output**: `architecture/memory-model-design.md`; plan.
- **Questions**: Q08.1.

### W08.2 Implement `Engine.Memory` and adopt in render commands, storage, cells · execute · after W08.1

- **Done when**: memory per subsystem is reported in the trace and in headless telemetry.

### W40.1 World partition design · design · after S01 W01.1, W03.3 (interfaces only)

- **Goal**: cell grid, cell lifecycle, activation barrier, handle epochs, persistence as package deltas, `Level` as cell set, editor cell view.
- **Inputs**: actor archetypes design, `Engine.Level`, #80 leftovers, #73.
- **Output**: `architecture/world-partition-design.md`; plan.
- **Questions**: Q40.1, Q40.2, Q40.3.

### W40.2 Implement cells, streaming and persistence · execute · after W40.1, W03.4, W01.2

- **Done when**: camera fly-over of a 10 km² grid loads and unloads cells within budget; `ActorRef` resolves to `None` while unloaded; a cell edit writes only its delta; server role activates cells without a GPU (S58 for the last item).

### W17.1 Virtual texture design · design · after W03.3, S15 W15.1 (feedback pass)

- **Goal**: page table, feedback, request priority, transcode, residency integration, software indirection first.
- **Output**: `architecture/virtual-texture-design.md`; plan.
- **Questions**: Q17.1.

### W17.2 Implement virtual texturing · execute · after W17.1, W03.4, W15.2

- **Done when**: a 16k virtual texture streams by feedback within the budget; evictions visible in the trace.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q03.2 | Applied in the [storage design](../../architecture/storage-design.md) section 2. IOCP first. The design and layout keep a DirectStorage backend in view, since it is part of the target architecture. |
| Q03.3 | Benchmark decides. Candidates must be legally clear and must include a codec DirectStorage can decompress on the GPU (GDeflate). |
| Q03.4 | A package layout PDF exists at `docs/packages.pdf` in the engine checkout; the code is probably more complete, so the source is the reference. |
| Q08.1 | Explicit allocators plus a debug-only global hook. |
| Q03.1 | Applied in the [storage design](../../architecture/storage-design.md) section 1.2: key = (storage instance, resource type). Not a flat key. Cache per resolver stage so a hit always yields a valid result and a request that resolves archive → package → file reuses an already cached package stage and only adds the missing resolver on top, never rebuilding from the ground up. See the `ResolvedStage` row in the code design. |
| Q40.3 | `Level` survives as a named cell set in the public API. |
| Q03.5 (2026-11-09) | In-flight cap 64 as the starting value, a constructor argument tuned by the W03.4 benchmark sweep (8 to 128). A slot reservation for high and realtime priority is added only if the priority test or the trace shows inversion. [Storage design](../../architecture/storage-design.md) 2.3. |
| Q03.6 (2026-11-09) | A dropped batch future never cancels. `IoRequest` carries an optional `Arci<void> keepAlive` that the batch holds until the request completes, so a dropped future with an owned buffer is safe. `IoFileBlob` leaves it empty. [Storage design](../../architecture/storage-design.md) 2.4. |
| Q40.2 (input) | World scope stated by the owner for the partition design: massive terrains; multi-layered terrain-scale tunnel systems; gigantic caves holding whole kingdoms; giant forests with villages inside trees; wide grasslands, swamps, volcanoes, mountain ranges and borders; wide oceans. The 2D versus 3D cell question (and the cell-size question Q40.1) is decided against this scope; pros and cons are in the conversation record of 2026-11-09. |
| Q40.1 | Recommendation accepted as the starting point: fixed leaf cells (256 m to start; forest and cave interiors decide the final size) under a quadtree used for streaming priority and server interest, with persistence and ownership at the leaf only. Empty leaves hold no package. The design must get the split right between extreme actor and asset density and wide open, loosely populated regions; the owner points at a VSBVH as the kind of structure that shines there. |
| Q03.3 (2026-11-18) | **LZ4HC 9 per 64 KiB chunk**, not the zstd proposal: about one core at full drive speed (ratio 1.29) and fast reads. The chunk table records the codec per chunk, so a later switch is a re-cook. DirectStorage, if it comes, needs GDeflate anyway. The codec for cook and shipping builds is searched later (W03.7 corpus). [Storage exploration](../../architecture/storage-exploration.md) 6.2. |
| Q03.5 (2026-11-18) | Default cap lowered from 64 to **32** and made a setting (W03.6). Measuring the drive at runtime to auto-adjust, for shipped games, is a candidate follow-up. |
| Q03.7 (2026-11-18) | Package chunks are read unbuffered; buffered reads stay for metadata and editor files. Decided on the measurement (cold buffered reads 3.8 times slower). |
| Q03.8 (2026-11-18) | No DirectStorage backend now; kept in view (GDeflate, `VK_EXT_memory_decompression`). |
| Q03.9 (2026-11-18) | Adjacent wanted chunks coalesce into requests of about 256 KiB. Never read more than was requested to make a request bigger: a 64 KiB request stays 64 KiB. A byte budget in flight (1 to 2 MiB proposed for this drive) next to the 32-request backstop. Owner caveat: higher latency is not automatically bad. In a burst (engine start, level load, cooking), 32 × 256 KiB finishes in about the same time as a shallow window (8 MiB at 3,311 against 3,272 MiB/s, about 0.03 ms apart), and a deep queue absorbs refill stalls on our side. So the budget is not fixed at the knee before W03.6 measures burst makespan against the latency of a high-priority request that arrives during the burst. |
| Q03.10 (2026-11-18) | Texture import default changes; lossless while authoring in the editor. The image loader and stream chain need a positional reconstruction per format for sub-region reads (W03.7). |
| Q40.2 | 2D columns with explicit, authored height layers (surface, cave levels), each with its own height band and packages; terrain and ocean stay on the 2D grid; streaming picks layers by player height and known connections. 3D cubes rejected for now. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q03.1 | Stack cache keyed by scheme and repository, by action type, or by both? | W03.1 | Both; the key is the triple above |
| Q03.2 | Windows path: IOCP now with DirectStorage as a later backend, or DirectStorage PC from the start? | W03.3 | IOCP first; DirectStorage after W03.5 shows a decompression win |
| Q03.3 | Codec: decided by the benchmark, or is zstd fixed by policy? | W03.5 | Let the benchmark decide between zstd and LZ4 |
| Q03.4 | Can the package layout PDF be shared, or is the source-derived layout (exploration 1a) the reference? | W03.3, W41.1 | Source-derived layout is the reference |
| Q08.1 | Is overriding global `operator new` acceptable for tracking, or do we track only through explicit allocators? | W08.1 | Explicit allocators plus a debug-only global hook |
| Q40.1 | Cell size and shape: fixed square cells (e.g. 256 m) or hierarchical from the start? | W40.1 | Fixed 256 m cells, hierarchy later (left for later in #120) |
| Q40.2 | Is a cell 2D (x, y with unbounded height) or 3D (also z) for caves and flight? | W40.1 | 2D with height layers from S28 later |
| Q40.3 | Does `Level` survive as a user-facing concept (named cell set) or is it removed from the public API? | W40.1 | Survives as a named cell set |
| Q17.1 | Software page-table indirection first, or `sparseResidency` from the start given the cube-map code works? | W17.1 | Software first; sparse behind a flag |
