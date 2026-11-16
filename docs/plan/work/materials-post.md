# Work: Materials v2, Transparency, Post-Processing

**Systems** S16, S22, S23 · **Issues** [#96](https://github.com/Heliogrim/Heliogrim-Engine/issues/96), [#102](https://github.com/Heliogrim/Heliogrim-Engine/issues/102), [#103](https://github.com/Heliogrim/Heliogrim-Engine/issues/103) · **Track** B · **Milestone** M2 to M3
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Materials, transparency and post](../topics/materials-post.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Requirement back-propagation brainstorm (session notes) | Materials export requirements; the graph enables passes from the union | Not written on the site; W16.1 records it |
| `Engine.Graphics.Material` (`EffectUsagePattern` ctx, dyn, static; dyn is a stub) | Binding frequency classes exist in name | The dyn class becomes the per-instance block |
| [Visual scripting work](visual-scripting-hmr.md) | Material graphs compile to ASL through S47's compiler | Until then materials are ASL plus parameter sets |
| [GPU-driven work](render-graph-gpu-driven.md) Q15.2 | Deferred versus forward-from-VB decides the shading entry point | Blocks W16.1 and W22.1 |

## Architecture

- **Bundles**: `Engine.Graphics.Material` extended (layer model, requirements, parameter blocks). New `Engine.Graphics.Transparency` (OIT targets, composite, refraction copy) and `Engine.Graphics.Post` (chain fragments, LUTs, exposure, output transform). All shaders in ASL under `assets/shader/material/*`, `transparency/*`, `post/*`.
- **Provides**: material model and parameter blocks mapped to the GPU material table; `Requirements` per prototype; OIT and refraction passes; a post chain with jitter and motion vectors from the first version.
- **Consumes**: visibility resolve (S15), pipeline cache (S13), froxel volume (S21), probes (S20), swapchain colour-space query (`Engine.Driver.Vulkan`).

## Code design

| Type | Contract |
|---|---|
| `MaterialModel` | Base layer (metal-roughness, specular control), optional `Clearcoat`, `Sheen`, `Subsurface`, `Emissive { colour, nits }`, `TransparencyClass { Opaque, Masked, Blend, Oit }`, `Displacement`. Layers compose at ASL compile time through `@when` features; no runtime branches. |
| `ParameterBlock` | Typed, per update frequency (`PerMaterial`, `PerInstance`); names follow glTF and OpenPBR; mapped to `MaterialEntry.paramOffset` in the GPU table. |
| `Requirements` | Bit set exported per `MaterialEffect`: `{ Lights, ShadowMaps, GiProbes, RefractionBuffer, EmissiveList, Froxel }`; `MaterialPrototype::requirements()` is the union; `GraphBuilder` reads the scene-wide union to enable passes. |
| `EmissiveSurfaceList` | Built by the classification pass for materials with `Emissive`; consumed by S20 probe updates. |
| `OitPass` | Weighted blended first (accumulation and revealage targets plus composite); `MomentOit` as the upgrade behind the same interface. |
| `RefractionPass` | Sorted forward pass sampling a copy of the opaque colour buffer; writes transparent motion vectors. |
| `PostChain` | Ordered fragments: `Exposure (histogram)`, `Bloom`, `DepthOfField`, `MotionBlur`, `Temporal (TAA or upscaler)`, `ToneMap`, `Grade (3D LUT, log space)`, `OutputTransform (sRGB, scRGB, HDR10)`, `UiComposite`. Each is a `PassDecl`; jitter and motion vectors exist from the first version. |
| `ToneMapOp` | `PbrNeutral`, `AgX`, `Aces` behind one effect interface; default from Q23.1. |

Placement: `Engine.Graphics.Material/{MaterialModel,ParameterBlock,Requirements}.hpp`, `Engine.Graphics.Transparency/`, `Engine.Graphics.Post/`. Tests: harness goldens against a path-traced reference for a layered material; glass, smoke and water scene under camera motion; SDR and HDR output goldens.

## Work chunks

### W16.1 Material system v2 design · design · after W15.1 (table layout, Q15.2)

- **Goal**: layer model with the open-stack seam (Q16.1), parameter blocks, requirement export and back-propagation, emissive list, importer mapping onto the engine's canonical parameters (Q16.2), geometry-effect variants, and the material merge and uber-shader analysis (Q15.2).
- **Output**: `architecture/material-v2-design.md` (also records the back-propagation brainstorm); plan.
- **Questions**: Q16.1, Q16.2.

### W16.2 Implement materials v2 · execute · after W16.1, W15.3, W13.2

- **Done when**: a layered material with clearcoat and emissive renders in the harness and matches the reference within tolerance; pass enablement follows the requirement union.

### W22.1 Transparency design · design · after W16.1, W21.1 (froxel interface)

- **Goal**: OIT choice protocol (weighted blended first, measured), refraction path, fog and GI application, motion vectors.
- **Output**: `architecture/transparency-design.md`; plan.
- **Questions**: Q22.1.

### W22.2 Implement OIT and refraction · execute · after W22.1, W16.2

- **Done when**: glass, smoke and water render without sorting artefacts under camera motion.

### W23.1 Post chain design · design · after W14.1

- **Goal**: fragments, exposure, LUT grading, output transform by swapchain capability, upscaler seam (FSR first), HDR swapchain on Windows.
- **Output**: `architecture/post-processing-design.md`; plan.
- **Questions**: Q23.1, Q23.2.

### W23.2 Implement post chain v1 (exposure, bloom, TAA, tone map, grade, output) · execute · after W23.1, W14.2

- **Done when**: post goldens pass; SDR and HDR output verified on one display each.

### W23.3 Depth of field, motion blur, upscaler integration · execute · after W23.2

- **Done when**: FSR runs through the seam without pipeline changes; DoF and motion blur goldens pass.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q23.2 | Plan the upscaler seam but do not focus on it: relying on an upscaler means something upstream went wrong. FSR is the only free option worth integrating; no other vendor SDK. |

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q16.2 | The engine defines its own canonical parameter set, derived from its layer model. Importers map glTF (and later other formats) onto it, and the editor curates the result; OpenPBR is the reference for parameter semantics and naming where the engine has no reason to differ. Neither external vocabulary is the engine's internal one. |
| Q22.1 | Moment-based OIT only if weighted blended fails the quality bar set in the design. |

| Q16.1 | Fixed layer set now; the open layer stack is a planned later feature, so the layer model and the material table keep a seam for it. |
| Q23.1 | AgX (filmic) as the game view default; Khronos PBR Neutral for asset verification. The asset preview can switch between the two. Changeable later. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q16.1 | Fixed layer set (base, clearcoat, sheen, subsurface) or an open layer stack from the start (Substrate style)? | W16.1 | Fixed set; open stack is a later ASL feature |
| Q16.2 | Importer naming: glTF names as the canonical parameter names, OpenPBR names, or both with a mapping table? | W16.1 | glTF canonical, OpenPBR mapping table |
| Q22.1 | Is moment-based OIT a planned upgrade or only if weighted blended fails a stated quality bar? | W22.1 | Only on failure of the bar set in the design |
| Q23.1 | Default tone map: PBR Neutral or AgX? | W23.1 | PBR Neutral default, AgX and ACES options |
| Q23.2 | Vendor upscaler SDKs (DLSS, XeSS) acceptable as vendored integrations, or FSR only? | W23.1 | FSR only until a product asks |
