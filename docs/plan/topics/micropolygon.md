# Micropolygon and Virtualised Geometry

**Systems**: S18 (and #82 for the scratchpad borrows) · **Track** B · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Research from [rendering](../sources/research-rendering.md) section 2 (existence of DGF, Kuth et al., Mlakar et al. seen on search results; details unverified). The [micropoly system page](../../systems/micropoly-renderer.md) is a placeholder.

## Target

Cluster-DAG geometry with error-driven LOD, page streaming, software rasterisation for pixel-sized triangles and hardware or mesh-shader rasterisation for larger ones, output into the visibility buffer. Scenes with hundreds of millions of source triangles stream and render at pixel-sized detail within the frame budget on the baseline GPU.

## Current state (checked 2026-11-07)

- `Engine.GFX.Geometry`: 46 lines. `StaticGeometryStructure` asset exists. No meshlets, no DAG, no pages.
- #82 describes the micropolygon scratchpad in workgroup shared memory (per-lane index and vertex sub-sections written through shared helpers), which drives the region-borrow feature in ASL.
- Import goes through assimp into static geometry; no offline processing stage beyond that.

## Research summary

- Nanite (Karis, Stubbe, Wihlidal SIGGRAPH 2021; unverified): about 128 triangles per cluster, hierarchical DAG with crack-free group boundaries, error metric per node, streamed pages, hardware raster for large and compute software raster for tiny triangles with 64-bit atomics, visibility buffer output. Quoted data rates about 9 B per triangle in memory and 5.6 B on disk (via the DGF paper summary, unverified).
- Compressed meshlets: Kuth et al. (arXiv 2404.06359, abstract verified: 0.59 ms for 15.5M triangles on an RX 7900 XTX; the "VMV best paper" and 9.5 bits per triangle claims are not confirmed), DGF (AMD, HPG 2024) and Mlakar et al. (CGF 43(1) 2024) decompress in mesh shaders (listings seen, bodies not read).
- `VK_EXT_mesh_shader` (2022) on Turing+, RDNA2+, Arc; a compute fallback keeps portability. meshoptimizer is the reference meshlet builder.
- The report's recommendation: a first target of static meshlets plus GPU culling; defer DAG and streaming until measured; the streaming and page residency work is the largest engineering cost.

## Guidance

- **Stage 1, meshlets**: import-time meshlet build (meshoptimizer as a vendored algorithm library is within the vendor policy; otherwise an in-house builder) into a geometry page format; GPU culling and indirect draw through S15; hardware raster into the visibility buffer. This alone removes per-object CPU cost and gives cluster culling.
- **Stage 2, DAG and LOD**: offline cluster grouping and simplification into a DAG with a conservative error metric; the GPU selects clusters per frame by projected error; crack-free boundaries by locked group edges. Build runs on Background fibers in the worker role (S58) and the editor's import pipeline.
- **Stage 3, software raster**: a compute rasteriser for clusters whose triangles are pixel-sized, writing 64-bit `{ depth, id }` with atomics; the scratchpad layout from #82; a mesh-shader path for mid-size clusters where available.
- **Stage 4, streaming**: pages requested by the culling pass (feedback), served by the residency manager (S03, S17); a pinned coarse LOD per asset so nothing disappears.
- Materials: resolved from the visibility buffer (S15); displacement and masked materials need a "programmable raster" path later (foliage, S25).
- Measure at every stage on the baseline GPU: cluster cull cost, software versus hardware raster crossover, page residency hit rate, DAG build time on the project's assets.

## Done when

- Stage 1: a scene of 10k instances of a 1M-triangle asset renders through meshlets with GPU culling in budget.
- Stage 3: a 100M-source-triangle scene renders at pixel-sized clusters with the software rasteriser; the visibility buffer resolve matches the hardware path in the harness.
- Stage 4: the same scene streams from a cold cache while the camera flies through it without a frame above budget.

## Open decisions

- meshoptimizer vendored or an in-house builder.
- Mesh shaders required, optional, or skipped in favour of compute everywhere.
- Page size and its relation to the storage chunk size (S03).
