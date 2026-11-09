# Volumetric Sky, Clouds, Fog and Weather Simulation

**Systems**: S21, S32 · **Track** B, C · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Research from [world](../sources/research-world.md) section 1 (all unverified; the Hillaire 2020 PDF exceeded the fetch limit).

## Target

Sky, atmosphere, clouds and fog come from one physically based model driven by a weather state that changes over time and space and is replicated cheaply. Weather simulation drives wind for foliage, sails and particles, precipitation for terrain and ocean, and wetness for materials. Effects are bounded by terrain layers (S29) so a cave has its own weather.

## Current state (checked 2026-11-07)

- `SkyBoxPass` with `sky.vs.asl` and `sky.fs.asl` draws a static sky. No atmosphere, clouds, fog or weather state.

## Research summary (all unverified)

- Sky and atmosphere: Hillaire 2020 (EGSR) with small transmittance, multiple-scattering and sky-view LUTs plus a camera-aligned aerial-perspective froxel volume; fully dynamic time of day at low cost; Hillaire 2016 (Frostbite) as the earlier production system with a unified volumetric framework; Bruneton and Neyret 2008 as the precomputed reference.
- Clouds: Horizon Zero Dawn (Schneider 2015, 2017) raymarched Perlin-Worley density with a weather map, height gradients per cloud type, temporal reprojection at reduced resolution; Nubis3 (2023) voxel-based authored volumes.
- Froxel fog (Wronski 2014, Hillaire 2015): a frustum-aligned 3D texture with light and media injection, front-to-back integration, temporal jitter and reprojection. It doubles as the lighting volume for particles and underwater.
- Precipitation: camera-local particle shells and a top-down occlusion map so rain stops indoors; wetness as material parameters and puddle masks.
- Wind: a low-resolution vector field from noise, gusts and storm vectors sampled by foliage, cloth, particles and the ocean; shipped games drive it from a scalar weather state rather than a fluid simulation.
- Weather state: authored states with transitions driving coverage, fog, wind, wetness and audio; region-based maps in open-world titles.

## Guidance

### S21 Volumetric sky, atmosphere, clouds, fog

- Build the Hillaire 2020 LUT pipeline first: it is small compute passes with fixed resources, a clean first consumer of the compute pipeline (S12) and the render graph (S14).
- Froxel volume as shared infrastructure: fog, local volumetrics, cloud shadows, particle lighting (S24) and underwater (S30) all read it; transparency (S22) applies it.
- Clouds: quarter-resolution raymarch with temporal reprojection from day one; weather map from S32; cloud shadows onto terrain and ocean through a projected transmittance map; a hard time budget enforced by the trace.
- Bounded volumes: the froxel integration respects layer volumes (S29) so weather media stop at a cave ceiling.

### S32 Weather simulation

- State: a replicated, low-bandwidth structure `{ seed, state id, transition start, target state, region }` per region; clients derive sky, clouds, fog, wind, wetness and audio deterministically from it (MMO-friendly).
- Wind field service: a pure function of position, time and state on the CPU (server authoritative, used by sailing and gameplay) with a matching GPU field texture for foliage, particles and ocean spectra; both derived from the same noise and state so they agree within tolerance.
- Precipitation: occlusion map rendered top-down around each viewer from terrain and static geometry; coherence with live terrain edits (S28) through dirty-tile invalidation.
- Wetness and puddles: material parameters driven by precipitation accumulation and terrain flow maps (S33 can bake flow).

## Done when

- A day cycle with a weather transition from clear to storm runs with correct sky, cloud and fog changes; cloud shadows move over terrain and ocean; frame cost stays within the budget recorded in the issue.
- Rain stops under a roof; a cave layer shows no precipitation and its own fog.
- Server and client wind samples at 1,000 random points agree within the stated tolerance.

## Open decisions

- Cloud technique (Horizon-style raymarch versus voxel-authored Nubis3-style) after a spike.
- Froxel resolution and slice distribution for the target view distance.
- Whether weather regions are terrain tiles or authored volumes.
