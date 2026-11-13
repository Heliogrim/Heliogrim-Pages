# Materials, Emissive, Transparency and Post-Processing

**Systems**: S16, S22, S23 · **Track** B · **Milestone** M2 to M3
**Status**: <span class="hg-status summary">plan</span>. Research from [rendering](../sources/research-rendering.md) sections 6 to 8 (Khronos PBR Neutral verified; the rest unverified).

## Target

- **Materials v2**: layered physically based materials with a small fixed layer count, emissive as a first-class input that lights the scene through GI, parameter naming aligned with glTF and OpenPBR, requirement back-propagation into pass enablement. Photoreal and stylised looks are material and post choices on one renderer.
- **Transparency**: order-independent transparency for glass, water and smoke; refraction; correct interaction with fog, shadows and GI.
- **Post-processing ("video effects")**: HDR output, tone mapping, colour grading, bloom, depth of field, motion blur, temporal anti-aliasing and upscaling, blending modes, all as graph fragments.

## Current state (checked 2026-11-07)

- `Engine.Graphics.Material` (16 files): `Material`, `MaterialPrototype`, `MaterialEffect`, `EffectUsagePattern` (ctx, dyn, static bindings; dyn is a stub), `MaterialParameterStorageTable`, `MaterialFactory`. The PBR shaders (`lighting.brdf.asl`, `pbr.asl`, `gbuffer.fs.asl`) implement a single-layer metal-roughness model with IBL.
- `PostProcessPass` and `tonemap.asl` exist; no grading, bloom, DoF or motion blur; no HDR swapchain; no motion vectors.
- Blend state exists per pipeline; no OIT.

## Research summary

- Materials (unverified): Disney principled BRDF (Burley 2012) is the de-facto parameterisation; layering per Weidlich-Wilkie 2007 and Belcour 2018; OpenPBR (ASWF) and Autodesk Standard Surface as interchange specs; Unreal Substrate as a shipped layered system. Emissive as a GI source needs light sampling of emissive triangles or probe injection.
- Transparency (unverified): weighted blended OIT (McGuire and Bavoil 2013) is cheap and approximate; moment-based OIT (Münstermann et al., PACMCGIT 1(1), I3D 2018) is better at fixed memory; per-pixel linked lists are exact but unbounded; visibility-buffer pipelines keep transparency forward.
- Tone mapping: Khronos PBR Neutral (verified) has no hue shift, an analytic inverse and sRGB output only; ACES has hue skew; AgX is neutral with desaturated highlights. HDR output on Windows is scRGB or HDR10 via `VK_EXT_swapchain_colorspace` (unverified). Temporal upscaling (FSR 2 and 3, DLSS, XeSS) all need jittered projection, motion vectors, depth and exposure; AMD's FSR 2 page (verified) states under 1.3 ms for Quality mode at 4K on an RX 6800 XT.

## Guidance

### S16 Material system v2

- Material model: base layer (metal-roughness with specular control), optional clearcoat, optional sheen, optional subsurface approximation, emissive (colour and intensity in nits), transparency class (opaque, masked, blend, OIT), displacement for micropolygon and terrain. Layers compose at compile time in ASL (function inlining), never runtime branches.
- Parameters: typed blocks per update frequency (per material, per instance) mapped to the GPU material table (S15); naming follows glTF and OpenPBR so importers map one to one.
- Requirement back-propagation: each material effect exports requirements (lights, shadow maps, GI probes, refraction buffer); `MaterialPrototype` aggregates them; the render graph enables passes from the union (no translucent materials, no OIT passes; no emissive, no emissive light list).
- Emissive feeds GI (S20) through an emissive surface list built by the material classification pass.
- Material graphs in the editor (`Editor.Graphics.Graphs`) compile to ASL through the visual-scripting compiler (S47) once it exists; until then materials are ASL plus parameter sets.

### S22 Transparency

- Weighted blended OIT first (two targets and a composite pass), measured; moment-based OIT as the upgrade if glass quality demands it; per-object sorted forward for the few surfaces that need refraction, which samples a copy of the opaque colour buffer.
- Fog (S21) and GI (S20) are applied in the transparent forward pass from the shared froxel volume and probes. Transparent motion vectors are written for TAA.

### S23 Post-processing

- Chain as graph fragments: exposure (histogram), bloom, depth of field, motion blur, TAA or upscaler, tone map, colour grading (3D LUT in log space), output transform (sRGB, scRGB, HDR10 chosen by swapchain capability query), UI composite.
- Default tone map: PBR Neutral or AgX behind a stable effect interface; ACES available as an option.
- Produce jitter and motion vectors from the first version so an upscaler (FSR first, portable) can be integrated without pipeline changes.

## Done when

- A layered material with clearcoat and emissive renders in the GPU harness and matches a path-traced reference within a stated FLIP tolerance.
- A scene with glass, smoke and water renders without sorting artefacts under camera motion.
- The reference scene outputs correctly on an SDR and an HDR display; the post chain golden images pass.

## Open decisions

- Deferred G-buffer resolve or forward-from-visibility-buffer (shared with S15).
- OIT technique after the measurement.
- Upscaler vendor SDKs (licence and Vulkan support).
