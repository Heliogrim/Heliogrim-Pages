# Work: Volumetric Sky, Clouds, Fog, Weather

**Systems** S21, S32 · **Issues** [#101](https://github.com/Heliogrim/Heliogrim-Engine/issues/101), [#112](https://github.com/Heliogrim/Heliogrim-Engine/issues/112) · **Track** B, C · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Volumetrics and weather](../topics/volumetrics-weather.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| `SkyBoxPass`, `sky.vs.asl`, `sky.fs.asl` | Static sky | Replaced by the LUT sky in W21.2 |
| Engine vision note | Server-authoritative sailing needs CPU-evaluable deterministic fields | The wind field service is a pure function of position, time and state on both sides |
| [Accel Lang work](accel-lang.md) W12.2 | Sky LUT is the first compute consumer | W21.2 and W12.2 are the same first milestone |
| [Terrain work](terrain.md) S29 | Bounded effect volumes per layer | Froxel integration respects layer volumes; owned by S29, consumed here |
| [Networking work](networking-mmo.md) | Replication of small state | Weather state is the first replicated non-actor structure |

## Architecture

- **Bundles**: new `Engine.GFX.Volumetric` (atmosphere LUTs, aerial perspective, froxel volume, clouds, cloud shadow map) and new `Engine.World.Weather` (state, transitions, regions, wind field service, precipitation occlusion, wetness parameters). Weather sits in L3 world and exposes a query service; rendering reads it through the service, not the other way round.
- **Provides**: sky and aerial perspective, shared froxel volume, cloud shadows; `WeatherState` per region, `WindField` CPU and GPU, precipitation occlusion map, wetness inputs for materials.
- **Consumes**: compute pipelines (S12), render graph (S14), cells and layers (S40, S29), replication (S56, later), terrain height for occlusion (S27), flow maps (S33, optional).

## Code design

| Type | Contract |
|---|---|
| `AtmosphereLuts` | Transmittance, multiple scattering, sky-view LUTs (Hillaire 2020 shape); recomputed on parameter change; small compute passes. |
| `FroxelVolume` | Frustum-aligned 3D texture with media and light injection, front-to-back integration, temporal jitter and reprojection; slice distribution from Q21.1; read by transparency, particles, underwater; respects `LayerVolume` bounds (S29). |
| `CloudPass` | Quarter-resolution raymarch with temporal reprojection, weather map from `WeatherState`, height gradients per type; technique chosen in W21.0. `CloudShadowMap` projects transmittance onto terrain and ocean. |
| `WeatherState` | `{ seed, stateId, transitionStart, targetState, regionId }`; small, replicated; every derived quantity is a deterministic function of it and time. |
| `WeatherRegion` | Terrain tile or authored volume per Q32.1; a region map resolves position to state. |
| `WindField` | `sample(WorldPosition, time) -> vec3` as a pure CPU function; `WindFieldTexture` on the GPU built from the same noise and state; a tolerance test compares both at 1,000 points. Query service registered on the scene. |
| `PrecipitationOcclusion` | Top-down depth around each viewer from terrain and static geometry; dirty-tile invalidation from terrain edits (S28). |
| `WetnessParams` | Accumulation per material from precipitation and occlusion; puddle masks from flow maps when S33 bakes them. |

Placement: `Engine.GFX.Volumetric/{AtmosphereLuts,FroxelVolume,CloudPass,CloudShadowMap}`, `Engine.World.Weather/{WeatherState,WeatherRegion,WindField,PrecipitationOcclusion}`. Tests: LUT goldens; day-cycle golden video; wind CPU and GPU agreement; rain under a roof fixture.

## Work chunks

### W21.0 Cloud technique spike · explore · after W12.2

- **Goal**: prototype Horizon-style raymarch against a voxel-authored volume at quarter resolution; measure cost at the target view distance; read Hillaire 2020 in full (the research pass could not fetch the PDF).
- **Output**: `architecture/volumetrics-exploration.md` with numbers; answers Q21.2.

### W21.1 Sky, froxel and clouds design · design · after W14.1, W21.0 (clouds part can lag)

- **Goal**: LUT pipeline, froxel contract (the shared interface for S22, S24, S30), cloud pass, cloud shadows, layer-volume respect.
- **Output**: `architecture/volumetrics-design.md`; plan.
- **Questions**: Q21.1.

### W21.2 Implement atmosphere LUTs and sky · execute · after W21.1, W12.2

- **Done when**: sky follows time of day; `SkyBoxPass` removed; LUT goldens pass.

### W21.3 Implement froxel fog · execute · after W21.2

- **Done when**: fog interacts with lights; transparency reads the volume (S22 test).

### W21.4 Implement clouds and cloud shadows · execute · after W21.3, W32.2 (weather map)

- **Done when**: the day-cycle golden video passes within the budget recorded in #101.

### W32.1 Weather simulation design · design · after W21.1 (froxel interface), W40.1 (regions)

- **Goal**: state structure, regions, transitions, wind field service on CPU and GPU, precipitation occlusion, wetness, replication shape.
- **Output**: `architecture/weather-design.md`; plan.
- **Questions**: Q32.1, Q32.2.

### W32.2 Implement weather state, regions and wind field · execute · after W32.1

- **Done when**: server and client wind samples agree within tolerance at 1,000 points; a transition from clear to storm drives the sky.

### W32.3 Implement precipitation occlusion and wetness · execute · after W32.2, W27.2 (terrain height)

- **Done when**: rain stops under a roof; a cave layer shows no precipitation (needs S29 for the layer part).

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q21.2 | Both paths are likely needed in the end: procedural clouds for projects that will not author volumes, authored volumes for projects that want the artistic control. The spike decides the first implementation; the renderer keeps a density-source seam so the two are interchangeable. Authoring itself stays in DCC tools (Houdini is the industry standard and not worth competing with) and enters through VDB import (NanoVDB reader, permissive licence) in a later chunk; no in-editor cloud sculpting. |
| Q21.1 | 32 km horizon for clouds and aerial perspective, 2 km froxel far plane with exponential slices. Defaults for now. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q21.1 | Target view distance for fog and clouds (sets froxel resolution and slice distribution)? | W21.1 | 32 km horizon, froxel far plane 2 km with exponential slices |
| Q21.2 | Cloud technique: decided by the spike, or is authored voxel content (Nubis3 style) a product requirement? | W21.0 | Spike decides; raymarch is the expected winner |
| Q32.1 | Weather regions: terrain tiles or authored volumes? | W32.1 | Authored volumes with a tile-sized default grid |
| Q32.2 | Is weather server-authoritative from the first version (replicated state), or client-local until S56 exists? | W32.1 | Structure is replication-ready; local driver until S56 |
