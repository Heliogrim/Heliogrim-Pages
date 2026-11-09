# Particles and Foliage

**Systems**: S24, S25 · **Track** B · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Research from [world](../sources/research-world.md) sections 5 and 6 (all unverified).

## Target

- **Particles at Niagara scale**: GPU-simulated emitters authored as graphs with modules in ordered stages, typed attribute sets, simulation stages over grids and particles, collisions against depth, distance fields and terrain, sorting, lighting from the froxel volume, indirect draws. Gameplay-relevant particles stay on the CPU.
- **Foliage**: instanced and impostored at distance, masked or programmable raster near, wind from the shared field, LOD transitions without popping, and near-camera aggregates where measurement shows a win.

## Current state (checked 2026-11-07)

- No particle system. No foliage system. Instancing exists only as per-object draws through the current passes.

## Research summary (all unverified)

- Particles: Niagara and VFX Graph use fixed-capacity SoA attribute buffers, dead and alive lists, indirect dispatch and draw, bitonic or radix sort for blended particles, depth-buffer and global-SDF collisions, froxel or clustered lighting, soft particles, half-resolution rendering for overdraw-heavy effects, motion vectors for TAA. Emitter graphs compile to compute.
- Foliage: GPU instancing with octahedral impostors; hierarchical instance culling; Nanite foliage (UE 5.x, programmable raster for masked and world-position-offset materials; assemblies and voxel far LOD in later versions, status unverified); wind as hierarchical vertex bending (Sousa, GPU Gems 3, 2007); dithered LOD cross-fade under TAA; overdraw of alpha-tested leaves dominates cost; volumetric aggregate LOD (Loubet and Neyret 2017, 2018) is research grade.

## Guidance

### S24 Particle system

- Data model: an emitter asset is a graph of modules; each module declares the attributes it reads and writes, so the compiler orders modules, fuses them into compute stages and allocates SoA buffers. This is the same compile shape as the visual-scripting compiler (S47); share the graph IR.
- Runtime: fixed-capacity pools with dead lists; indirect dispatch for spawn, update and render; counters read back only for debugging; a sort stage only for emitters that declare blending.
- Data interfaces: depth buffer, global distance field (shared with GI, S20), terrain height tiles (S27), wind field (S32), skeletal mesh surfaces (S36); each is a pluggable provider with a declared ASL interface.
- Lighting: sample the froxel volume (S21) per particle or per vertex; shadow receiving from CSM or VSM.
- Determinism: cosmetic particles are client-only and non-deterministic; particles that affect gameplay (projectiles) are CPU actors.

### S25 Foliage

- Instances are derived from procedural scatter (S33) with deterministic seeds; stored instance data only for hand-placed overrides.
- Rendering: GPU culling and masked raster through S15; impostors beyond a distance; near-camera leaf geometry through the micropolygon path with a programmable-raster extension for masked and bent vertices.
- Wind: sample the GPU wind field in the vertex stage with hierarchical bending; the same field drives the ocean and cloth.
- LOD: dithered cross-fade under TAA; measure overdraw per density tier on the baseline GPU before considering aggregate volumes; if adopted, aggregates come from offline voxelisation of the tree asset.

## Done when

- One million GPU particles with depth collisions, sorting and froxel lighting render in budget; an emitter graph change recompiles without restarting the editor.
- A forest of 100k trees with impostors beyond 300 m, masked leaves near the camera and wind renders in budget; no visible LOD pop under TAA in the golden video test.

## Open decisions

- Shared graph IR with S47 from the start or a particle-specific IR first.
- Aggregate leaf LOD: spike or skip.
