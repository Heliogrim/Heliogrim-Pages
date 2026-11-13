# Work: Shadows and Global Illumination

**Systems** S19, S20 · **Issues** [#99](https://github.com/Heliogrim/Heliogrim-Engine/issues/99), [#100](https://github.com/Heliogrim/Heliogrim-Engine/issues/100) (To discuss) · **Track** B · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Shadows and GI](../topics/shadows-gi.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| `ShadowDirPass`, `shadowDir.vs.asl`, `lighting.brdf.asl` | A single directional map with a basic lookup | Replaced by CSM in W19.2 |
| IBL assets (`brdfLut`, `brdfIrrad`, `brdfPref`) | Static specular and diffuse environment | Becomes the fallback of the probe cache |
| [GPU-driven work](render-graph-gpu-driven.md) | Culling pipeline per view; Q15.2 deferred versus forward | CSM cascades are extra culling views; GI gather reads the G-buffer or the resolve output |
| [Materials work](materials-post.md) | `EmissiveSurfaceList` | GI light source for emissive |
| [Storage work](storage-streaming.md) S40 | Cells carry per-cell data | Probe volumes are per-cell payloads |
| Issue #100 status "To discuss" | The owner wants a conversation before design | W20.0 is that conversation's preparation |

## Architecture

- **Bundles**: new `Engine.Graphics.Shadow` (CSM, contact shadows, VSM page pool, ray-query tier) and `Engine.Graphics.GI` (scene representation for tracing, probe or cascade cache, screen-space gather, SSR). Shaders under `assets/shader/shadow/*` and `gi/*`.
- **Provides**: shadow terms for the lighting resolve and the transparent pass; diffuse and specular indirect lighting; per-cell probe payloads.
- **Consumes**: culling views (S15), compute and ray-query pipelines (S12), emissive list (S16), froxel volume for cloud shadows (S21), cell lifecycle (S40), harness (S26).

## Code design

| Type | Contract |
|---|---|
| `CascadeSet` | Four cascades, texel snapping, split scheme; each cascade is a culling view; PCF with optional PCSS; drives `ShadowAtlas`. |
| `ContactShadowPass` | Small screen-space ray march in compute. |
| `VirtualShadowMap` | Page table per light, need pass from screen depth, page pool, cache invalidation from the mirror's movement reports, cluster rendering into pages; local lights as cube or paraboloid pages. |
| `RayShadowTier` | Optional: ray-query one sample per pixel plus denoiser; gated by the minimum-spec flag. |
| `TraceScene` | The coarse scene representation for GI tracing: `GlobalSdf` (from meshlet bounds or voxelised geometry) or `RayQueryScene`; one interface, chosen per Q20.1. |
| `ProbeVolume` | Per-cell DDGI-style grid with visibility; update spread over frames by a ray budget; multi-bounce by feeding back irradiance; serialised with the cell. |
| `CascadeSpike` | Research prototype of sparse split radiance cascades behind the same `IndirectDiffuse` interface; adopted only on in-house measurement. |
| `ScreenSpaceReflections` | SSR with fallback to probe or cascade radiance; ray-traced reflections as the optional tier. |

Placement: `Engine.Graphics.Shadow/{CascadeSet,ContactShadowPass,VirtualShadowMap}`, `Engine.Graphics.GI/{TraceScene,ProbeVolume,Ssr}`. Tests: harness goldens for CSM and contact shadows; Cornell-box FLIP against a path-traced reference; probe survival across cell unload and reload.

## Work chunks

### W19.1 Shadows design · design · after W15.1

- **Goal**: VSM architecture as the target (Q19.1), CSM on the culling pipeline as the first step, contact shadows, ray-query tier (required hardware); replacement of `ShadowDirPass`.
- **Output**: `architecture/shadows-design.md`; plan.
- **Questions**: Q19.1.

### W19.2 Implement stable CSM and contact shadows · execute · after W19.1, W15.2

- **Done when**: reference scene passes CSM and contact shadow goldens.

### W19.3 Implement virtual shadow maps · execute · after W19.2, W18.2 (cluster rendering helps, not required)

- **Done when**: pixel-sharp sun shadows at 1 km within the page budget.

### W19.4 Ray-query shadow tier · execute · after W12.3, W19.2

- **Done when**: area-light shadows with a denoiser pass a golden on a capable GPU; skipped with a recorded reason elsewhere.

### W20.0 GI discussion brief · explore · ready (#100 is "To discuss")

- **Goal**: prepare the owner's discussion with hardware ray query as a required feature (Q12.2): compare probe grids (DDGI style), radiance cascades, ReSTIR-based GI, surfel GI, SDF plus surface-cache approaches (Lumen style) and hardware-traced probes on scalability to streamed cells, leak and lag behaviour, cost on the RTX 4070 and implementation cost; state for each what the trace scene is and how it interplays with virtual geometry and the micropolygon pipeline (sharp, precise edges, proxy versus cluster BVH); read the radiance cascades papers and the other recent papers in full, not abstracts. Probes are the probable target (Q20.2).
- **Output**: `architecture/gi-exploration.md` with a recommendation and the questions below answered or sharpened.
- **Questions**: Q20.1, Q20.2, Q20.3.

### W20.1 GI design · design · after W20.0 and the owner's decision, W16.1

- **Output**: `architecture/gi-design.md`; plan (diffuse first, then specular, then emissive injection).

### W20.2 Implement trace scene and diffuse probe cache · execute · after W20.1, W15.3

- **Done when**: Cornell-box test passes FLIP against the reference; a streamed cell carries probe data across unload and reload.

### W20.3 Implement SSR and specular fallback · execute · after W20.2

### W20.4 Emissive injection and multi-bounce · execute · after W20.2, W16.2

- **Done when**: a moving emissive object lights its surroundings in the golden test.

### W20.5 Cascade spike · explore · parallel to W20.2, only if W20.0 recommends it

- **Goal**: in-house measurement of split cascades against the probe path on the reference scene.

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q19.1 | Virtual shadow maps are required; cascaded shadow maps are only the first implementation on the way there. W19.3 is part of the shadows system's "done", not a later milestone. |
| Q20.2 | Probes are the probable target for diffuse GI. How they are built (grid, cascades, hardware traced, hybrid) is decided in W20.0 and W20.1, not here. |
| Q20.1, Q20.3 | Deferred to W20.0 with a widened brief (see the chunk goal): the owner wants a detailed comparison that accounts for hardware ray query being a required feature, the interplay with virtual geometry and the micropolygon pipeline (sharp, precise edges that an SDF loses), probe-based approaches, radiance cascades and other recent papers read in full. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q19.1 | Is VSM a must for M3 or can CSM plus contact shadows close M3 with VSM in M4? | W19.1 | CSM closes M3; VSM starts when S18 stage 1 ships |
| Q20.1 | Scene representation for tracing: global SDF, voxels, or ray queries (hardware dependent)? | W20.1 | Global SDF from meshlet bounds plus voxelised static geometry; ray queries as the tier |
| Q20.2 | Probe grid first with cascades as a spike, or cascades as the primary bet? | W20.1 | Probe grid first |
| Q20.3 | Is ray-traced GI a target tier at all for the first release, or only shadows and reflections? | W20.1 | Reflections and shadows only |
