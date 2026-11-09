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

- **Bundles**: `Engine.Storage.*` keeps registries, actions, packages. New `Engine.Storage.Backend` (`IoBackend` interface, Windows IOCP implementation, generic thread-pool fallback) running on an `AffineThread` (S02). New `Engine.Resource.Residency` (budgets, priorities, eviction). New `Engine.Memory` (tracked allocators, arenas). New `Engine.GFX.Texture.Virtual` (page tables, feedback, transcode). New `Engine.World.Partition` replacing `Engine.Level` as the actor container.
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

Placement: `Engine.Storage.Backend/{IoRequest,IoQueue,IoBackend,Iocp}.{hpp,cpp}`, `Engine.Storage.Action/StackCache.{hpp,cpp}`, `Engine.Resource.Residency/`, `Engine.Memory/`, `Engine.GFX.Texture.Virtual/`, `Engine.World.Partition/{CellCoord,Cell,Partition,CellPackage}`. Tests per bundle; the 1,000-request test and the cancellation test live in `Engine.Storage.Backend.Test`; the fly-over test is a scene fixture (S61).

## Work chunks

### W03.1 Resolved-stack reuse · design+plan · ready

- **Goal**: cache resolved stacks per stage with prefix reuse and guard-safe lifetime (Q03.1); close #24 on the way. The design names, for each existing resolver, what its stage key is and which commits invalidate it.
- **Inputs**: `Engine.Storage.Action` (`StageResolutionFactory`, `ActionTypeResolutionCache`, `ResourceObjectStore`), exploration section 3.
- **Output**: short design section in `architecture/storage-design.md`; plan.
- **Questions**: Q03.1.

### W03.2 Implement stack cache · execute · after W03.1

- **Done when**: a query resolves its stack once per scheme; a mutation invalidates after commit; #24 closed with a test.

### W03.3 Async request path and IOCP backend · design · ready (W02.3 done)

- **Goal**: `IoRequest`, `IoQueue`, `IoBackend`, the IOCP implementation, the removal of `todo_panic` in `queryAsync` and `mutateAsync`. The interface is shaped so a DirectStorage backend drops in later (decision Q03.2): file range to host or GPU destination, batch submit, queue-level completion, a compression-format field per request.
- **Inputs**: `docs/packages.pdf` in the engine checkout (package layout; older than the code, the source is the reference where they differ).
- **Inputs from W02.3**: [affine threads design](../../architecture/affine-thread-design.md) section 12 (the fiber callback stays on the fiber, the IO thread moves byte ranges; header, index, archive batches; windowed fallback for large cell archives; in-flight budgets, coalescing and cancellation as the pressure levers) and the `IoThread` skeleton with its completion port.
- **Output**: `architecture/storage-design.md` main section; plan.
- **Questions**: Q03.2.

### W03.4 Implement async storage · execute · after W03.3, W02.2

- **Done when**: 1,000 concurrent requests across three priorities complete through the IO thread with priorities honoured; cancellation observed; no `todo_panic` in storage.

### W03.5 Codec and chunking benchmark · explore · ready

- **Goal**: measure no compression, zlib (vendored), LZ4, zstd and GDeflate (the format DirectStorage decompresses on the GPU; open specification, permissive reference implementation) on the project's assets at 64 KiB chunks; record each candidate's licence; decide the chunk size and whether DirectStorage PC's GPU decompression is worth a backend. Commercial codecs (Oodle) are out.
- **Output**: results in `architecture/storage-exploration.md`; answers Q03.3 by measurement.

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
| Q03.2 | IOCP first. The design and layout keep a DirectStorage backend in view, since it is part of the target architecture. |
| Q03.3 | Benchmark decides. Candidates must be legally clear and must include a codec DirectStorage can decompress on the GPU (GDeflate). |
| Q03.4 | A package layout PDF exists at `docs/packages.pdf` in the engine checkout; the code is probably more complete, so the source is the reference. |
| Q08.1 | Explicit allocators plus a debug-only global hook. |
| Q03.1 | Not a flat key. Cache per resolver stage so a hit always yields a valid result and a request that resolves archive → package → file reuses an already cached package stage and only adds the missing resolver on top, never rebuilding from the ground up. See the `ResolvedStage` row in the code design. |
| Q40.3 | `Level` survives as a named cell set in the public API. |
| Q40.2 (input) | World scope stated by the owner for the partition design: massive terrains; multi-layered terrain-scale tunnel systems; gigantic caves holding whole kingdoms; giant forests with villages inside trees; wide grasslands, swamps, volcanoes, mountain ranges and borders; wide oceans. The 2D versus 3D cell question (and the cell-size question Q40.1) is decided against this scope; pros and cons are in the conversation record of 2026-11-09. |
| Q40.1 | Recommendation accepted as the starting point: fixed leaf cells (256 m to start; forest and cave interiors decide the final size) under a quadtree used for streaming priority and server interest, with persistence and ownership at the leaf only. Empty leaves hold no package. The design must get the split right between extreme actor and asset density and wide open, loosely populated regions; the owner points at a VSBVH as the kind of structure that shines there. |
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
