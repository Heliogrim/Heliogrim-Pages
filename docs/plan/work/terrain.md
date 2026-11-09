# Work: Terrain, Multi-Level Layers, Deformation, Bounded Effects

**Systems** S27, S28, S29 · **Issues** [#107](https://github.com/Heliogrim/Heliogrim-Engine/issues/107), [#108](https://github.com/Heliogrim/Heliogrim-Engine/issues/108), [#109](https://github.com/Heliogrim/Heliogrim-Engine/issues/109) · **Track** C · **Milestone** M3 to M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Terrain](../topics/terrain.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| `docs/ideas.md` (engine, early notes) | "Cave system / multi-layer heightmaps", "environment painting with automatic instantiation" | Both are S28 and S33 targets |
| Jolt heightfield shape (vendored, unused) | Physics representation exists | Per-tile shapes, double base offset (S34) |
| [Storage work](storage-streaming.md) Q40.1 | Cell size decided with tile sizes | Q27.1 fixes the tile size; the cell holds N tiles |
| [Volumetrics work](volumetrics-weather.md) | Froxel respects `LayerVolume` | S29 owns `LayerVolume`; W29.1 before W21.3's layer part |
| [Navigation work](navigation.md) | Navmesh tile equals terrain tile; one layer per height layer | Shared tile grid and dirty-tile protocol |
| [Editor workflows work](editor-workflows.md) S45 | Undo as the inverse of the op log | Brush ops are transactions |
| Engine vision note | 60 px/cm budget does not apply to terrain maps | Terrain textures tile or are procedural; no unique texel terrain |

## Architecture

- **Bundles**: new `Engine.World.Terrain` (tiles, height layers, materials, height query service, edit op log) and `Engine.World.Terrain.Voxel` (overlay meshing), `Engine.GFX.Render.Terrain` (LOD selection, patch instances), `Editor.Terrain` (sculpt and paint tools as actions). `Engine.World.Volume` for `LayerVolume` (S29).
- **Provides**: `sampleHeight(WorldPosition)` and `activeVolume(WorldPosition)` query services; terrain patches as GPU instances; authoritative tile data for server and physics; the edit op log.
- **Consumes**: cells (S40), double positions (S07), virtual textures (S17), GPU-driven renderer (S15), Jolt heightfields (S34), navmesh rebuild hook (S37), actions (S45), replication (S56, later).

## Code design

| Type | Contract |
|---|---|
| `TerrainTile` | Fixed size (Q27.1); `HeightLayer[]` each a 16-bit or float height grid with mips; material weight pages in a virtual texture; serialised in the cell package. |
| `TileLod` | Clipmap rings or CDLOD quadtree chosen by the W27.0 prototype; emits patch instances into `GpuSceneTables`. |
| `HeightQueryService` | `sampleHeight(WorldPosition, layer selector) -> Opt<double>` from authoritative CPU tiles; identical sampling rule to the shader; registered on the scene; used by physics, audio, foliage, ocean shoreline, navigation. |
| `TerrainMaterial` | ASL material reading layer weights from the VT; splat painting writes VT pages through actions. |
| `HeightLayerStack` | Per tile intervals `{ floor, ceiling }` per layer (ground, cave floor, cave ceiling); layer links for navigation. |
| `VoxelOverlay` | Separate tiles aligned to terrain tiles; Dual Contouring with Transvoxel seams (or Surface Nets per Q28.1); meshed on Background fibers; participates in the visibility buffer as geometry. |
| `BrushOp` | `{ tool, params, seed, tileSet, timestamp, author }` appended to a per-tile `OpLog`; server applies to CPU tiles, clients apply on GPU and verify by per-tile hash; inverse op for undo. |
| `DirtyTileSet` | Collected per frame; physics heightfield and navmesh rebuilds on Background fibers, swapped at a frame boundary. |
| `LayerVolume` | Region bound to a terrain layer or an authored volume with priority; `activeVolume(WorldPosition) -> VolumeParams` with blend over a transition distance; consumers: weather, audio reverb, GI probe volumes, physics (gravity, water). |

Placement: `Engine.World.Terrain/{TerrainTile,HeightLayerStack,HeightQueryService,BrushOp,OpLog}`, `Engine.World.Terrain.Voxel/`, `Engine.GFX.Render.Terrain/TileLod`, `Engine.World.Volume/LayerVolume`, `Editor.Terrain/`. Tests: `sampleHeight` versus rendered surface at 10k points; op-log hash agreement; cave fixture walk-through.

## Work chunks

### W27.0 LOD prototype: clipmap versus CDLOD · explore · after W15.2

- **Goal**: one tile set rendered both ways through the GPU-driven path; measure cost and visibility-buffer fit; pick one.
- **Output**: `architecture/terrain-exploration.md` with numbers.

### W27.1 Terrain v1 design · design · after W40.1, W17.1, W27.0

- **Goal**: tile format, LOD, materials on VT, height query service, Jolt heightfield per tile, streaming per cell, editor painting through actions.
- **Output**: `architecture/terrain-design.md` part 1; plan.
- **Questions**: Q27.1, Q27.2.

### W27.2 Implement terrain v1 · execute · after W27.1, W40.2, W17.2, W15.2

- **Done when**: a 10 km² terrain streams and renders with four layers; `sampleHeight` matches within tolerance at 10k points; a character walks on it through Jolt heightfields (S34 basic shapes needed).

### W28.1 Terrain v2 design: layers, voxel overlay, op log · design · after W27.2, W34.1, W45.1

- **Output**: design part 2; plan.
- **Questions**: Q28.1, Q28.2.

### W28.2 Implement height layer stack and op log with editor sculpting · execute · after W28.1

- **Done when**: a brush edit updates render, physics and navigation within one frame and matches the server hash (navigation part when S37 exists).

### W28.3 Implement voxel overlay · execute · after W28.2

- **Done when**: a cave with an overhang is sculpted and walked through.

### W29.1 Bounded effect volumes design · design · after W27.1 (can start on authored volumes before layers)

- **Goal**: `LayerVolume`, priorities, blending, query service, consumer contracts for weather, audio, GI, physics.
- **Output**: `architecture/bounded-volumes-design.md`; plan.
- **Questions**: Q29.1.

### W29.2 Implement volumes and the first two consumers (weather, audio reverb) · execute · after W29.1, W32.2, W38.x reverb

- **Done when**: a cave layer has its own weather and reverb; the entrance blends.

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q28.2 | Terrain v2 may ship before navigation consumes height layers. |
| Q27.1 | 64 m tiles at 1 m height spacing (65x65 samples), 4x4 tiles per 256 m leaf cell; the tile matches the navmesh tile. Finer detail comes from displacement and the voxel overlay, not from the height field. |
| Q27.2 | 16-bit heights with per-tile min and max, plus a per-tile float32 fallback flag for extreme relief (tall cliffs) so terracing never shows. |
| Q28.1 | Dual Contouring (Hermite data, sharp carved edges for cave architecture) with Transvoxel-style LOD seams; a fix-up pass for self-intersections is part of the design. |
| Q29.1 | Authored volumes first; derivation from voxel caves follows once S28 exists. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q27.1 | Terrain tile size and resolution (with cell size Q40.1 and navmesh tile)? | W27.1 | 64 m tiles at 1 m height spacing; 4x4 tiles per 256 m cell |
| Q27.2 | Height storage: 16-bit fixed with per-tile range, or float32? | W27.1 | 16-bit with per-tile range; float32 only for the authoritative server copy if precision tests fail |
| Q28.1 | Voxel overlay: Dual Contouring with Transvoxel seams, or Surface Nets? | W28.1 | Dual Contouring |
| Q28.2 | Does terrain v2 ship before navigation can consume layers, or must S37 and S28 land together? | W28.1 | v2 may ship first; navigation consumes layers when it lands |
| Q29.1 | Are authored volumes (no terrain layer) enough for the first consumers so S29 can start before S28? | W29.1 | Yes |
