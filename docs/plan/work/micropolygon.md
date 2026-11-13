# Work: Micropolygon and Virtualised Geometry

**Systems** S18 · **Issues** [#98](https://github.com/Heliogrim/Heliogrim-Engine/issues/98), [#82](https://github.com/Heliogrim/Heliogrim-Engine/issues/82) · **Track** B · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Micropolygon](../topics/micropolygon.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| [Micropoly system page](../../systems/micropoly-renderer.md) | Placeholder | Filled after stage 1 ships |
| Region borrows spec (#82, see [Accel Lang work](accel-lang.md) W11.1) | Scratchpad layout: per-lane workgroup slots split into index and vertex sub-sections, shared helpers | The software rasteriser (stage 3) is its consumer |
| [GPU-driven work](render-graph-gpu-driven.md) | Visibility buffer, culling pipeline, bindless | Stage 1 is "meshlets through S15"; S18 adds DAG, software raster, streaming |
| [Storage work](storage-streaming.md) | Residency manager, chunk size | Page size tied to the chunk size (Q18.3) |
| Engine vision note | Virtualised geometry needs compute and mesh stages, sparse and bindless resources, indirect dispatch | All covered by S11, S12, S15 prerequisites |

## Architecture

- **Bundles**: `Engine.Graphics.Geometry` grows into `Engine.Graphics.Geometry.Cluster` (meshlet and DAG formats, page layout, runtime selection) and `Editor.Graphics.Geometry.Build` (import-time meshlet build, DAG build on Background fibers, runs in the worker role). Rasterisers live in `Engine.Graphics.Render.Visibility` (hardware path) and a new `Engine.Graphics.Render.SoftwareRaster`.
- **Provides**: cluster geometry asset format, per-frame cluster selection, software rasteriser into the visibility buffer, page requests to residency.
- **Consumes**: culling and visibility (S15), virtual texture feedback plumbing (S17), residency (S03), ASL region borrows (S11), worker role (S58).

## Code design

| Type | Contract |
|---|---|
| `Meshlet` | About 128 triangles, local index buffer, bounds and cone; built at import by meshoptimizer (vendored algorithm) or an in-house builder per Q18.1. |
| `ClusterDag` | Nodes `{ meshlets, parent group, error, bounds }`; groups with locked boundary edges; built offline by simplification per level; serialised as pages. |
| `GeometryPage` | Fixed-size page (Q18.3) of clusters with a header; a pinned coarse page per asset; pages are the residency unit. |
| `ClusterSelect` | Compute pass: traverses the DAG by projected error against the view; emits clusters into a hardware list or a software list by screen size. |
| `SoftwareRaster` | Compute rasteriser for pixel-sized clusters writing 64-bit `{ depth, id }` with atomics into the visibility buffer; scratchpad layout from #82. |
| `MeshShaderPath` | Optional mid-size path behind the S12 mesh pipeline and the minimum-spec flag. |
| `PageFeedback` | Page requests emitted by `ClusterSelect` for missing children; served through `ResidencyManager`. |

Placement: `Engine.Graphics.Geometry.Cluster/{Meshlet,ClusterDag,GeometryPage,ClusterSelect}`, `Engine.Graphics.Render.SoftwareRaster/`, `Editor.Graphics.Geometry.Build/`. Tests: harness equality between software and hardware paths; DAG build determinism on fixtures; streaming fly-through as a scene fixture.

## Work chunks

### W18.1 Stage 1 design: meshlets and page format · design · after W15.1

- **Goal**: comparison table of meshlet builder options (Q18.1); meshlet build at import, page format, hardware raster through S15's culling, measurement plan per stage on the baseline GPU.
- **Output**: `architecture/micropolygon-design.md` part 1; plan.
- **Questions**: Q18.1, Q18.3.

### W18.2 Implement stage 1 · execute · after W18.1, W15.2

- **Done when**: 10k instances of a 1M-triangle asset render through meshlets with GPU culling in budget; system page written.

### W18.3 Stage 2 design: DAG and LOD selection · design · after W18.2 measured

- **Output**: design part 2; plan.

### W18.4 Implement DAG build and selection · execute · after W18.3, W58 worker role (builds can run in the editor meanwhile)

- **Done when**: crack-free LOD transitions in the golden video test; DAG build time per asset recorded.

### W18.5 Stage 3 design: software rasteriser · design · after W18.4, W11.1 (borrows)

- **Output**: design part 3; plan.
- **Questions**: Q18.2.

### W18.6 Implement software rasteriser and the mesh-shader path · execute · after W18.5, W12.3

- **Done when**: a 100M-source-triangle scene renders at pixel-sized clusters; the visibility resolve matches the hardware path in the harness.

### W18.7 Stage 4: page streaming · execute · after W18.6, W17.2, W03.4

- **Done when**: the same scene streams from a cold cache during a fly-through without a frame above budget.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q18.1 | Start with a vendored meshlet builder. W18.1 first produces a comprehensive comparison of the options (meshoptimizer, DirectXMesh, METIS-based graph partitioning, an in-house builder) with pros, cons, licence and maintenance state for each, and picks from that table. |
| Q18.2 | Mesh shaders are a required feature (Q12.2), so the mesh-shader path is the baseline cluster raster path and the compute path is not a fallback tier. |
| Q18.3 | Geometry page is 128 KiB, two storage chunks, as an explained `inline constexpr static` (see the constants rule on the quality page). |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q18.1 | meshoptimizer vendored (algorithm library, zlib licence) or in-house meshlet builder? | W18.1 | Vendor meshoptimizer for the builder; simplification in-house in stage 2 if its simplifier proves insufficient |
| Q18.2 | Mesh shaders: required, optional, or skipped for compute everywhere? | W18.5 | Optional; compute path is the baseline |
| Q18.3 | Page size: equal to the storage chunk (64 KiB) or a multiple (e.g. 128 KiB)? | W18.1 | 128 KiB, two storage chunks |
