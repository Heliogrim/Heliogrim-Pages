# Work: Render Graph v2, GPU-Driven Renderer, Large-World Coordinates

**Systems** S07, S14, S15 · **Issues** [#89](https://github.com/Heliogrim/Heliogrim-Engine/issues/89), [#94](https://github.com/Heliogrim/Heliogrim-Engine/issues/94), [#95](https://github.com/Heliogrim/Heliogrim-Engine/issues/95) · **Track** B · **Milestone** M2
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Render graph v2, GPU-driven rendering and large world](../topics/render-graph-gpu-driven.md).

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Render graph system page](../../systems/render-graph.md) | Placeholder only | W14.0 writes the "as is" page before the v2 design |
| [Engine vision note](../vision.md) and memory (2026-10-31) | Double world positions and camera-relative rendering are required by the MMO target; float ulp at 10 km is about 1 mm (jitter claim overstated) | Rebasing threshold decided by measurement, not by the claim |
| [Bounding volumes exploration](../../architecture/bounding-volumes.md) | Options for CPU spatial queries | GPU culling owns its own bounds; CPU bounds stay for picking (S44) and interest |
| [Actor archetypes design](../../architecture/actor-archetypes-design.md) | Scene mirror from archetype components | The render scene becomes GPU tables fed by the mirror |
| Viewport and gizmo notes (memory) | Large-world coordinates affect picking and gizmos | S44 works in camera-relative space |
| [Accel Lang work](accel-lang.md) | `InterfaceDesc` per entry point | Pass declarations consume it (W14.1) |

## Architecture

- **Bundles**: `Engine.GFX.RenderGraph` (+`.Compile`) evolve into v2 in place (declarations, compile cache, derived barriers, aliasing, queues). `Engine.GFX.Render.Subpass/Impl` is superseded by declarative passes in a new `Engine.GFX.Render.Passes`. New `Engine.GFX.Scene.Gpu` (instance, material, geometry, light tables, upload rings) and `Engine.GFX.Render.Culling` (frustum, HZB, meshlet culling, indirect argument generation), `Engine.GFX.Render.Visibility` (visibility pass, classification, resolve). `Engine.Math` split out of `Engine.Common` with `dvec3` and `WorldPosition`. `Engine.Driver.Vulkan` gains bindless layout, timeline semaphores, multi-queue.
- **Layer**: L3 rendering, `Engine.Math` in L1.
- **Provides**: pass declaration API, compiled frame graph, GPU-resident scene, indirect draw pipeline, visibility buffer; `WorldPosition` for every system.
- **Consumes**: `InterfaceDesc` (S11), pipeline kinds (S12), `Waitable` for fences (S02), spans (S04), cell origin (S40), material requirements (S16).

```hg-diagram
flowchart LR
    MIR["Scene mirror<br/>components to models"] --> TAB["GPU tables<br/>instances, materials, geometry, lights"]
    TAB --> CULL["Culling<br/>frustum, HZB, meshlets → indirect args"]
    CULL --> VIS["Visibility pass<br/>{instance, triangle}"]
    VIS --> CLS["Classification<br/>tiles per material"] --> RESV["Resolve<br/>barycentrics, derivatives, shade"]
    DECL["Pass declarations<br/>+ InterfaceDesc"] --> CMP["Graph compile<br/>cull, order, barriers, alias, queues"] --> EXE["Record per pass on fibers → submit"]
```

## Code design

| Type | Contract |
|---|---|
| `PassDecl` | `{ name, kind, module: ref<InterfaceDesc>, extraUses (indirect args, readback), flags { asyncHint, persistent } }`; inputs and outputs come from the interface, never from hand-written lists. |
| `GraphBuilder` | Collects `PassDecl`s and resource declarations; `compile(hash) -> ref<CompiledGraph>` cached by graph hash; culling of unused passes, topological order, synchronization2 barriers and layout transitions, transient aliasing by lifetime interval in a pooled heap, queue assignment with ownership transfers. Errors are `Diagnostic`s naming the passes. |
| `CompiledGraph::execute` | Records each pass on a fiber into its own command buffer, submits in order; timeline semaphores complete into waitables for cross-queue and cross-frame waits. |
| `GpuSceneTables` | SoA buffers: `Instance { cameraRelativeTransform: mat4x3f, cellId, materialIndex, geometryIndex, flags }`, `MaterialEntry { paramOffset, featureBits }`, `GeometryEntry { meshletRange, bounds, cone }`, `Light`. Persistent mapped upload rings; dirty ranges from the mirror. |
| `CullingPipeline` | Instance frustum and HZB pass, meshlet cone and bounds pass, indirect argument buffer; two-pass occlusion with the previous frame's HZB. |
| `VisibilityBuffer` | `R32G32_UINT` or 64-bit `{ instance id, triangle id }`; classification pass bins pixels into per-material tile lists; resolve per permutation computes barycentrics and analytic derivatives. Deferred or forward output per Q15.2. |
| `BindlessSet` | One descriptor set with runtime arrays for sampled images, storage buffers, samplers; `nonuniformEXT` indexing expressed in ASL. |
| `WorldPosition` | `dvec3`; `Transform { WorldPosition translation; quatf rotation; vec3f scale }`; `getUniverseTransform` folds translation in double. |
| `CameraOrigin` | Current render origin (double); the mirror rebuilds camera-relative floats when the camera moves beyond the threshold from Q07.1; aligned to cell origins (S40). |

Placement: `Engine.GFX.RenderGraph/{PassDecl,GraphBuilder,CompiledGraph}`, `Engine.GFX.Scene.Gpu/Tables.hpp`, `Engine.GFX.Render.Culling/`, `Engine.GFX.Render.Visibility/`, `Engine.Math/{DVec3,WorldPosition,Transform}.hpp`. Tests: graph compile tests without a device (barrier derivation on fixtures), harness tests for culling and visibility, a 100 km origin test.

## Work chunks

### W14.0 Write the render graph "as is" system page · explore · ready

- **Goal**: read `Engine.GFX.RenderGraph` and `.Compile`, the subpass implementations and `VkRCmdTranslator`; describe the lifecycle with source links; list what v2 keeps.
- **Output**: `systems/render-graph.md` filled from the template.

### W07.1 Large-world coordinates design · design · ready

- **Goal**: `Engine.Math` split, `WorldPosition`, `Transform` change, `getUniverseTransform`, camera-relative scene, rebasing policy, a fixed-origin project mode for small-scale games (Q07.1), consumers list (physics, audio, navigation, picking, gizmos).
- **Inputs**: `HierarchyComponent`, `Engine.Math.Test`, UE5 LWC docs (verified).
- **Output**: `architecture/large-world-design.md`; plan.
- **Questions**: Q07.1, Q07.2.

### W07.2 Implement double world positions · execute · after W07.1

- **Done when**: a test world 100 km from the origin renders without jitter; transforms fold translation in double; `Engine.Math` is its own bundle.

### W14.1 Render graph v2 design · design · after W14.0, W11.2 (interface shape)

- **Goal**: declaration API, compile and cache, barrier derivation with synchronization2, aliasing, queue assignment, fiber recording, editor versus game composition fragments.
- **Output**: `architecture/render-graph-v2-design.md`; plan.
- **Questions**: Q14.1, Q14.2.

### W14.2 Implement render graph v2 and migrate existing passes · execute · after W14.1, W11.3

- **Done when**: the existing passes run as declarations; validation layer reports no synchronisation errors; transient memory drops measurably.

### W15.0 Decide the GPU minimum spec · explore · ready

- **Goal**: record the feature matrix for the decided minimum spec (RDNA3 and Ada Lovelace, mesh shaders and ray query required, Q12.2 and Q15.1) in #95 and on the site; no optional tiers.
- **Questions**: Q12.2, Q15.1.

### W15.1 GPU-driven renderer design · design · after W14.1, W07.1, W15.0

- **Goal**: GPU tables and upload rings, culling pipeline, visibility buffer, classification and resolve (geometry-effect variants before the visibility pass, Q15.2), bindless set, the mirror's dirty tracking, feedback buffer slot for S17.
- **Output**: `architecture/gpu-driven-design.md`; plan.
- **Questions**: Q15.2, Q15.3.

### W15.2 Implement GPU tables, culling and indirect draws · execute · after W15.1, W14.2, W07.2

- **Done when**: a 1M-instance scene is culled and drawn by indirect draws; CPU submission time is near constant in instance count.

### W15.3 Implement visibility buffer and material resolve · execute · after W15.2, W16.1 (material table layout)

- **Done when**: ten material permutations resolve from the visibility buffer and match the forward reference in the harness.

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q15.1 | Baseline GPU is the RTX 4070. Frame budget stays the proposed 16.6 ms at 1440p until the owner states otherwise. |
| Q12.2 | Shared with S12: RDNA3 and Ada Lovelace class, mesh shaders and ray query required. W15.0 records the feature matrix against that class only. |
| Q07.1 | Per-cell origin once S40 exists, fixed 1 km threshold until then. Large-world adoption is the primary focus, but small-scale games must run without the overhead: the design includes a fixed-origin project mode in which rebasing never triggers and the camera-relative path costs nothing beyond the double-precision storage. |
| Q07.2 | Per-region offset first; the Jolt double-precision build is evaluated in W34.0. |
| Q14.1 | Hint-only in the render graph v2 that W14.2 implements: passes declare queue affinity and the graph derives the barriers, but everything submits on the graphics queue. Async compute is enabled after a measurement, with no API change. Intended async-compute work once enabled: GI probe updates, SSAO and SSR denoise, particle simulation, next-frame cluster culling, VSM page allocation, froxel integration, light culling and atmosphere LUTs, overlapped with the shadow and depth passes that leave ALUs idle. |
| Q14.2 | One primary command buffer per pass, recorded in parallel on fibers and submitted in graph order. Secondaries only if a single pass needs parallel recording inside one render pass instance, which dynamic rendering makes rare. |
| Q15.3 | Visibility buffer as 2x32 for the hardware raster path; the 64-bit atomic path arrives with the software rasteriser in S18. |

| Q15.2 | Resolve the visibility buffer into a thin G-buffer through material-classified resolve passes; transparency and exotic BRDFs forward. Two additions from the owner: materials with tessellation, displacement or other geometry effects need a separate geometry variant that runs before the visibility buffer is written; and W16.1 analyses whether materials can be merged, up to uber-shaders per material class, to cut control and dispatch overhead in the resolve. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q07.1 | Rebasing threshold: fixed distance (e.g. 1 km) or per-cell origin aligned with S40's cell grid? | W07.1 | Per-cell origin once S40 exists; fixed 1 km until then |
| Q07.2 | Jolt: double-precision build or per-region base offset? (shared with S34) | W07.1, W34.1 | Per-region offset first; Jolt double build evaluated in W34.0 |
| Q14.1 | Async compute from the first version or hint-only later? | W14.1 | Hint-only; queue assignment designed in, enabled after measurement |
| Q14.2 | Recording granularity: one primary command buffer per pass, or secondaries merged per queue? | W14.1 | Primary per pass; measure |
| Q15.1 | Baseline GPU for budgets: name a concrete card and a frame budget. | W15.0 | RTX 2070 or RX 6600 class, 16.6 ms at 1440p |
| Q15.2 | Visibility buffer resolve into a G-buffer (deferred) or shade directly (forward from VB)? Decides S16, S20, S22 shapes. | W15.1 | Resolve into a thin G-buffer; transparency stays forward |
| Q15.3 | Visibility buffer format: 64-bit atomics required (software raster later) or 2x32 now and 64-bit only for S18? | W15.1 | 2x32 for hardware raster; 64-bit path added in S18 |
