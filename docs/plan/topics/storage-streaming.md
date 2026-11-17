# Storage, Streaming, Virtual Textures and World Partition

**Systems**: S03, S08, S17, S40 · **Track** A, B, C · **Milestone** M1 to M2
**Status**: <span class="hg-status summary">plan</span>. Research from [runtime](../sources/research-runtime.md) sections 2 and 3 (DirectStorage Xbox doc and UE5 large-world docs verified; the rest unverified). The [storage exploration](../../architecture/storage-exploration.md) records the Windows backend gap.

## Target

"Flawless streaming from disk, memory or cache": asset loads never stall the game loop; every resource class has a budget and a residency policy; requests carry priority and can be cancelled; a cold load of a 10 km² test world shows no hitch above the frame budget. World partition cells stream actors and assets together, and become the archetype handle space.

## Current state (checked 2026-11-07)

- `Engine.Storage.*`: registries, actions (fetch and mutate with guards), packages with archive deltas (#73), boot. All I/O is synchronous; async paths are `todo_panic`; the resolver stack is rebuilt per call.
- `Engine.Resource.*`: load and store pipelines, archives, blobs, packages; `Import`, `Load`, `Save` are stubs. No residency manager, no budgets, no cancellation.
- Sparse cube-map textures exist (#42 fixed a mip-tail bug), so `sparseResidency` is already used in one place.
- `Level` (296 lines) is the actor handle space; archetype regions are per level (PR #81). No streaming cells.
- Allocations: `pmr` arenas in render commands, otherwise global; no tracking.

## Research summary

- DirectStorage (verified, Xbox doc): batched lock-free queues; 50,000 requests per second at under 10% of one core; four priorities with about 10:1 weighting; best-effort cancellation via tag masks; FIFO completion notification per queue; submit everything, do not throttle; 32 to 64 KiB reads saturate NVMe; above 512 KiB with decompression prefer many parallel requests; free buffers only after a later notification. The PC variant adds GPU decompression (GDeflate), unverified.
- Windows IOCP and overlapped IO need sector-aligned unbuffered reads; io_uring is the Linux analogue for servers.
- Virtual textures (Mittring 2008, Barrett 2008, van Waveren 2009; unverified): feedback-driven page requests, per-frame upload budget, LRU or clock eviction, a pinned low-mip fallback.
- mmap as a primary path is argued against (Crotty et al. CIDR 2022, unverified): page faults stall the faulting thread, which on a fiber worker stalls every fiber on it.
- Compression: Oodle (commercial, vendor-stated numbers only), zstd and LZ4 (zstd README table verified: lzbench on Silesia, i7-9700K; zstd 1.5.7 level 1 about 1550 MB/s decompress at ratio 2.9, LZ4 about 3850 MB/s at ratio 2.1), GDeflate (DirectStorage PC README confirms GPU decompression; numbers unverified). Measure on our own assets regardless.
- Large-world coordinates (verified, UE5 docs): double on CPU, camera-relative "translated world space" early so shaders use floats; the old 256k tile-plus-offset scheme lost precision at tile boundaries.

## Guidance

### S03 Async storage and streaming backend

- API shape copied from DirectStorage even on the fallback backend: `Request { source (file, memory, cache), range, destination (buffer, GPU upload), priority, tag }`, batch submit, per-queue FIFO completion into a waitable (S02), cancellation by tag mask, memory-sourced decompression queue.
- Backends: Windows IOCP with unbuffered aligned reads first (measurable today), DirectStorage PC when the GPU decompression path is worth it, io_uring for Linux servers, a thread pool with `pread` as the generic fallback. All sit behind the affine-thread seam.
- Resolver stacks are resolved once per URL scheme and cached with their file handles under a lifetime that guards in-flight requests (the exploration's hazard).
- Package layout: content-addressed chunks in 64 KiB multiples; the compression unit equals the chunk so decompression parallelises.
- Residency manager (`Engine.Resource.Residency`): budgets per class (textures, geometry pages, audio, navmesh tiles, actor cells), request priority from distance and screen size, a hard cap on speculative loads, eviction events visible in S04.

### S08 Memory model

- Tracked allocator interface with tags per subsystem; arenas per frame, per cell, per request. Budgets are configuration; exceeding one is a diagnostic, not a crash. Reports feed the profiler and the headless telemetry.

### S17 Virtual texturing and texture streaming

- Page table per virtual texture, feedback buffer written by the material resolve pass (S15), page requests prioritised by mip and screen coverage, transcoding on Background-lane fibers, upload through the residency budget. Start with software indirection (page table texture) and evaluate `sparseResidency` once measured; the cube-map code shows the driver path works.

### S40 World partition

- A cell grid keyed by integer coordinates on double world positions (S07); each cell owns archetype regions (the "streaming cell as handle space" left for later in #80), its asset references and its navmesh and terrain tiles.
- Cells load through S03 with priority from distance to any active viewer or server interest; actors in a loading cell are not visible to systems until the cell is activated at a frame boundary.
- Persistence: a cell is a package; edits are deltas on it (#73's merge stream applies).
- Replaces `Level` as the actor container; `Level` becomes a set of cells with a name.

## Done when

- 1,000 concurrent requests across three priorities complete through the IO thread; a cancelled tag never writes its buffer after cancellation is observed; no `todo_panic` remains in storage.
- A 16k virtual texture streams by feedback within a set budget; evictions are visible in the trace.
- A camera flying across a 10 km² cell grid loads and unloads cells without a frame above budget on the baseline machine.
- Memory per subsystem is reported in the profiler and in headless telemetry.

## Open decisions

- Codec choice after a benchmark on the project's assets.
- Cell size (ties to terrain tiles, navmesh tiles and interest management).
- Whether DirectStorage PC is adopted or IOCP stays the Windows path.
