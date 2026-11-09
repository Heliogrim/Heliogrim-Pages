# Terrain: Heightfield Tiles, Multi-Level Layers, Live Deformation, Bounded Effects

**Systems**: S27, S28, S29 · **Track** C · **Milestone** M3 to M4
**Status**: <span class="hg-status summary">plan</span>. Research from [world](../sources/research-world.md) section 4 (all unverified).

## Target

- **Terrain v1**: heightfield tiles with clipmap or CDLOD level of detail, material layers blended through virtual textures, a height query service shared by physics, audio, foliage, ocean and navigation, streamed per world-partition cell.
- **Terrain v2**: multi-y-level terrain through layered heightfields plus a voxel overlay for caves and overhangs; live deformation and editing in the editor and at runtime, replicated as a brush-operation log per tile, applied to render, physics and navigation within a frame.
- **Bounded effects**: weather, audio, lighting and physics regions bound to a terrain layer or volume, not to a global height.

## Current state (checked 2026-11-07)

- No terrain system. The owner's early requirement notes (`docs/ideas.md`) list "cave system / multi-layer heightmaps" and "environment painting with automatic instantiation".
- Jolt is vendored and has a heightfield shape (not yet used).

## Research summary (all unverified)

- Heightfield LOD: geometry clipmaps (Losasso and Hoppe 2004; GPU clipmaps, Asirvatham and Hoppe 2005) with nested rings and toroidal updates; CDLOD (Strugar 2009) with a quadtree and per-vertex morphing.
- Terrain virtual texturing (Barrett 2008; Mittring 2008; UE runtime virtual texture) for blended materials, decals and baked splats.
- Non-heightfield terrain: Marching Cubes, Dual Contouring (Ju et al. 2002), Transvoxel (Lengyel 2010) for LOD seams, Surface Nets, Manifold DC; caves and overhangs at the cost of memory, meshing time and seam complexity. Layered heightfields (stacks of height intervals per cell) are cheaper with limited topology.
- Live editing: GPU brush stamps on height and material tiles, propagation to physics heightfields and LOD or VT caches, dirty-tile invalidation.
- World tiling in shipped engines (UE5 World Partition and Landscape; Frostbite; Dunia) is only partially recalled.
- MMO scale: integer-keyed tile grid, server-authoritative height, edits as a replicated delta log per tile.

## Guidance

### S27 Terrain v1

- Tile is the unit: streaming (S40 cell holds N tiles), replication, editing and physics. Tile size is decided together with the cell size and the navmesh tile size (S37).
- Height data: 16-bit or float height tiles with mip chains; GPU clipmap rings or a CDLOD quadtree selected per tile (prototype both on one tile set, keep the one that measures better with the visibility buffer).
- Materials: layer weights in a virtual texture (S17) blended in a terrain material compiled from ASL; splat painting writes the VT pages through the editor action system (S45).
- Height query service: `sampleHeight(WorldPosition)` on the CPU from the authoritative tile data (double world, S07), identical to what the shader reads; registered as a scene query service for physics (Jolt heightfield shapes per tile), audio, foliage placement and the ocean shoreline.
- Rendering through S15: terrain tiles are instances with meshlet-like patches so culling and the visibility buffer apply.

### S28 Terrain v2

- Multi-level: each tile may hold several height layers (ground, cave floor, cave ceiling) as a stack of intervals; the voxel overlay (Dual Contouring with Transvoxel seams) covers overhangs and arbitrary caves where a layered heightfield cannot; the overlay is a separate mesh system with its own tiles aligned to terrain tiles.
- Edits: a brush op `{ tool, parameters, seed, tile set, timestamp }` appended to a per-tile log; the server applies it to the authoritative CPU tiles, clients apply the same op on the GPU and verify against the CPU result by hash per tile; physics heightfields and navmesh tiles (S37) are rebuilt from dirty tiles on Background fibers and swapped at a frame boundary.
- Editor sculpting and runtime deformation (craters, digging) use the same op log; undo is the log's inverse (S45).

### S29 Bounded effects

- A `LayerVolume` is a region bound to a terrain layer (or an authored volume) with priorities; weather (S32), audio (S38), lighting (GI probe volumes, S20) and physics (gravity, water) query the active volume by position through the same query service as height.
- Transitions between volumes blend parameters over a distance; a cave entrance crossfades weather and reverb.

## Done when

- v1: a 10 km² terrain streams and renders with four material layers; `sampleHeight` matches the rendered surface within tolerance at 10k random points; a character walks on it through Jolt heightfields.
- v2: a brush edit updates render, physics and navigation within one frame on the client and matches the server hash; a cave with an overhang is sculpted and walked through.
- Bounded effects: a cave layer has its own weather, reverb and GI volume; the transition at the entrance blends.

## Open decisions

- Clipmap versus CDLOD after the prototype.
- Tile size (with S40 and S37).
- Voxel overlay representation (Dual Contouring versus Surface Nets) and whether terrain v2 ships before navigation (S37) can consume it.
