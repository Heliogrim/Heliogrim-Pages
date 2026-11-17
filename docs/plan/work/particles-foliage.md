# Work: Particles and Foliage

**Systems** S24, S25 · **Issues** [#104](https://github.com/Heliogrim/Heliogrim-Engine/issues/104), [#105](https://github.com/Heliogrim/Heliogrim-Engine/issues/105) · **Track** B · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Particles and foliage](../topics/particles-foliage.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| [Visual scripting work](visual-scripting-hmr.md) S47 | Graph IR with type check and ASL emitter | Emitter graphs want the same IR; the topic leaves "shared from the start or particle-specific first" open (Q24.1) |
| `Editor.Graphics.Graphs` (82 node definition files, no compiler) | Node vocabulary exists | Emitter modules can reuse node definitions once S47 compiles them |
| [Volumetrics work](volumetrics-weather.md) | Froxel volume and wind field service | Lighting and wind providers for both systems |
| [GI work](shadows-gi.md) | Global SDF as `TraceScene` | Collision provider for particles |
| [Micropolygon work](micropolygon.md) | Programmable raster extension for masked and bent vertices is "later" | Near-camera foliage depends on it; impostors and masked raster through S15 do not |
| [Procedural generation work](procedural-generation.md) | Deterministic scatter | Foliage instances are derived, not stored |

## Architecture

- **Bundles**: new `Engine.Physics.Particles` naming conflict: `Engine.Physics` is physics today; use `Engine.VFX` (emitter assets, compiled stages, pools, sort, render) and `Engine.World.Foliage` (instance derivation, impostor baking, LOD policy) plus `Engine.Graphics.Render.Foliage` (masked raster integration, impostor draw). Editor authoring in `Editor.Graphics.Graphs` through S47.
- **Provides**: GPU particle simulation and rendering; foliage instance sets with impostors, wind and LOD.
- **Consumes**: compute and indirect (S12), render graph (S14), culling and visibility (S15), froxel and wind (S21, S32), SDF (S20), terrain height tiles (S27), skeletal surfaces (S36), scatter (S33), graph IR (S47).

## Code design

| Type | Contract |
|---|---|
| `EmitterAsset` | Graph of `Module`s; each module declares read and write attribute sets; the compiler orders, fuses into `SimStage`s and allocates SoA `AttributeBuffer`s; emits ASL compute. |
| `ParticlePool` | Fixed capacity, SoA, alive and dead lists, indirect dispatch for spawn, update and render; counters read back only for debugging. |
| `DataInterface` | Pluggable provider with a declared ASL interface: `Depth`, `GlobalSdf`, `TerrainHeight`, `WindField`, `SkeletalSurface`. |
| `SortStage` | Radix sort only for emitters declaring blending. |
| `ParticleRender` | Indirect draw, soft particles, half-resolution option, motion vectors, froxel lighting per particle or vertex, shadow receive. |
| `FoliageInstanceSet` | Derived per cell from scatter rules and seed; overrides stored only for hand placement; feeds `GpuSceneTables` as instances. |
| `ImpostorBaker` | Octahedral impostor atlas per foliage asset, baked at import or in the worker role. |
| `FoliageLod` | Distance tiers: impostor, masked raster, near micropolygon path; dithered cross-fade under TAA; overdraw measured per density tier. |
| `WindBending` | Vertex-stage hierarchical bending sampling `WindFieldTexture`. |

Placement: `Engine.VFX/{EmitterAsset,SimStage,ParticlePool,DataInterface,SortStage}`, `Engine.Graphics.Render.Particles/`, `Engine.World.Foliage/{FoliageInstanceSet,ImpostorBaker,FoliageLod}`, `Engine.Graphics.Render.Foliage/`. Tests: 1M-particle budget scenario; emitter recompile without restart; 100k-tree forest budget and golden video.

## Work chunks

### W24.1 Particle system design · design · after W12.2, W47.1 (graph IR shape) or Q24.1 answered

- **Goal**: emitter asset and compile model, pools, stages, data interfaces, rendering, determinism rule (cosmetic only).
- **Output**: `architecture/particles-design.md`; plan.
- **Questions**: Q24.1, Q24.2.

### W24.2 Implement pools, stages and a fixed emitter · execute · after W24.1, W14.2

- **Done when**: 1M particles with depth collision and sorting run in budget with a hand-written stage set.

### W24.3 Implement emitter graph compilation · execute · after W24.2, W47.3 (ASL emitter)

- **Done when**: an emitter graph change recompiles without restarting the editor.

### W24.4 Froxel lighting, SDF collisions, skeletal surfaces · execute · after W24.2, W21.3, W20.2

### W25.1 Foliage design · design · after W15.1, W33.1 (scatter contract)

- **Goal**: instance derivation, impostors, LOD tiers, wind, overdraw measurement plan; the aggregate seam in the LOD chain (Q25.1).
- **Output**: `architecture/foliage-design.md`; plan.
- **Questions**: Q25.1.

### W25.2 Implement instances, impostors and wind · execute · after W25.1, W15.2, W32.2

- **Done when**: 100k trees with impostors beyond 300 m and wind render in budget.

### W25.3 Masked near-camera raster and LOD cross-fade · execute · after W25.2, W23.2 (TAA)

- **Done when**: no visible LOD pop in the golden video; overdraw per tier recorded.

### W25.4 Aggregate leaf LOD spike · explore · after W25.3

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q24.2 | The owner will rename `Engine.PFX` to `Engine.Physics` and `Engine.GFX` to `Engine.Graphics`. Following that spelled-out convention, particles are proposed as `Engine.Particles` (not `Engine.VFX`), foliage as `Engine.Foliage` with the render integration under `Engine.Graphics.Render.Foliage`. Confirmed by the owner. The rename itself is chunk W10.3 on the [quality page](quality-and-process.md); pages keep current names until it lands. |
| Q24.1 | Particle-specific stage compiler over the shared node definitions first; migrate to the S47 IR when it exists. |
| Q25.1 | Skip aggregate leaf LOD in the first version but plan for it: foliage overdraw is certain. W25.1 designs the aggregate seam (where the LOD chain hands over to a volumetric representation), W25.4 is scheduled, not conditional. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q24.1 | Share the S47 graph IR from the start (couples S24 to S47's schedule) or a particle-specific stage compiler first? | W24.1 | Particle-specific `SimStage` compiler over the shared node definitions; migrate to the S47 IR when it exists |
| Q24.2 | Bundle name: `Engine.VFX` (new) given `Engine.Physics` is physics? | W24.1 | `Engine.VFX` |
| Q25.1 | Aggregate (volumetric) leaf LOD: spike or skip for the first release? | W25.1 | Skip; revisit with overdraw numbers |
