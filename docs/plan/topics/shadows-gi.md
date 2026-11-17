# Shadows and Global Illumination

**Systems**: S19, S20 · **Track** B · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Research from [rendering](../sources/research-rendering.md) sections 4 and 5 (existence of the radiance cascade papers seen on search results; everything else unverified).

## Target

- **Shadows**: precise and sharp. Stable cascaded shadow maps with contact shadows as the baseline; virtual shadow maps once the GPU-driven pipeline exists; optional ray-query shadows with denoising for area lights.
- **Global illumination**: multi-bounce diffuse GI and reflections that work in large streamed worlds without ray-tracing hardware, with a ray-traced tier where available; emissive surfaces contribute.

## Current state (checked 2026-11-07)

- `ShadowDirPass` with `shadowDir.vs.asl` renders a single directional shadow map; no cascades, no filtering beyond the basic lookup in `lighting.brdf.asl`.
- IBL from prefiltered cube maps (`brdfIrrad`, `brdfPref`, `brdfLut`); no dynamic GI, no reflections beyond IBL.

## Research summary

- Shadows (unverified): virtual shadow maps (UE5) with 16k virtual resolution per light, page allocation driven by screen need, cached pages with invalidation; stable CSM with texel snapping and PCF or PCSS remains the baseline; ray-traced shadows at one sample per pixel with SVGF (Schied et al. HPG 2017) or NRD denoising; screen-space contact shadows fix near-contact leaks cheaply.
- GI candidates (unverified unless noted): Lumen (SIGGRAPH 2022) with screen probes, a radiance cache and SDF or card tracing; DDGI (Majercik et al. JCGT 2019) irradiance probe grids with visibility; ReSTIR DI, GI and PT (2020 to 2022) need ray tracing; radiance cascades (Sannikov 2023, GitHub README verified; Path of Exile 2 use is a repo claim) with 2D holographic cascades (arXiv 2505.02041, May 2025, abstract verified: 1.85 ms at 512² and 7.67 ms at 1024² on an RTX 3080 Laptop) and 3D sparse "split" cascades (arXiv 2607.20384, submitted 22 July 2026, revised October 2026, abstract verified, very new); surfel GI (EA SEED 2021); neural radiance caching (Müller 2021) needs tensor hardware.
- The report's reading: for large open worlds a world-space cache (probes, surfels or sparse cascades) scales better than screen space; probe GI has leaking and temporal lag to budget; split cascades have no independent implementation yet.

## Guidance

### S19 Shadows

1. Stable CSM (four cascades, texel snapping, PCF, optional PCSS) driven by the GPU culling pipeline so each cascade draws only visible clusters; contact shadows as a small compute pass. This replaces `ShadowDirPass`.
2. Virtual shadow maps once S15 is in: a page table per light, page requests from a screen-space need pass, cached pages invalidated by moving instances (the scene mirror reports movement), cluster rendering into pages.
3. Ray-query shadows for area lights as an optional tier with a denoiser; the pipeline kinds come from S12.
- Local lights: cube or dual-paraboloid maps in the VSM page pool; spot lights as single pages.

### S20 Global illumination

- Architecture: a world-space cache plus a screen-space gather, so streaming cells can carry baked or warmed cache data.
  - Diffuse: start with a DDGI-style probe volume per cell with visibility, updated by tracing against a coarse scene representation (a global SDF built from meshlet bounds or voxelised geometry, or ray queries where available); multi-bounce by feeding probe irradiance back into the next update. Evaluate split radiance cascades as a research spike in parallel; adopt only after an in-house measurement.
  - Specular: screen-space reflections with a fallback to probe or cascade radiance; ray-traced reflections as the optional tier.
  - Emissive: the emissive surface list (S16) is injected into probe updates as light sources.
- Budgets: probe updates spread over frames with a per-frame ray budget; the trace viewer shows it.
- Stylised rendering: the same GI feeds a different material and post response; no separate renderer.

## Done when

- Shadows: the reference scene passes golden images for CSM and contact shadows; VSM shows pixel-sharp sun shadows at 1 km view distance within the page budget.
- GI: a Cornell-box-style test and the reference scene pass FLIP against a path-traced reference within a stated tolerance; a moving emissive object lights its surroundings; a streamed cell carries its probe data across unload and reload.

## Open decisions

- Scene representation for tracing (global SDF, voxels, ray queries).
- Probe grid versus sparse cascades after the spike.
- Ray-tracing tier on the minimum spec.
