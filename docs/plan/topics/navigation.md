# Navigation at Open-World Scale

**Systems**: S37 · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Research from [simulation](../sources/research-simulation.md) section 5 (Recast README verified; the rest unverified).

## Target

A navigation system for an MMO open world: tiled navmesh streamed with world-partition cells, hierarchical queries for long paths, crowd steering, volumes for flying and swimming agents, awareness of multi-level terrain (caves, bridges), dynamic obstacles, and a cost model cheap enough for servers with thousands of agents.

## Current state (checked 2026-11-07)

- Nothing.

## Research summary

- Recast and Detour (verified README): zlib licence, C++98, no dependencies; Recast voxelises and builds single or tiled navmeshes; Detour queries; DetourTileCache for streaming large and open worlds with dynamic obstacles; DetourCrowd for steering; used by Unity, Unreal, Godot and O3DE; sliced queries exist (unverified detail).
- Hierarchical pathfinding (HPA* 2004; HNA* Pelechano and Fuentes 2016), flow fields for large unit counts (Supreme Commander 2), ORCA (van den Berg et al. 2011), sparse voxel octrees for flight (Brewer 2017). Unverified.
- Server cost: tiles only around active players; sliced queries spread over ticks.

## Guidance

- **Vendor Recast and Detour** (algorithm library within the policy) rather than writing a voxeliser; wrap them behind `Engine.Navigation` so the tile format, queries and crowd are engine types and Detour stays replaceable.
- **Tiles**: navmesh tile size equals the terrain tile (S27) and divides the world-partition cell (S40); tiles are built on Background fibers from terrain tiles, the voxel overlay (S28) and static geometry; stored in the cell package; rebuilt from dirty tiles on terrain edits and swapped at a frame boundary.
- **Multi-level**: one navmesh layer per terrain height layer; links between layers at authored or detected connections (stairs, ladders, cave mouths); queries carry an agent class that selects layers and link types.
- **Hierarchy**: an abstract graph over tiles (portal nodes) for long-distance planning; detailed Detour paths within a tile window; path requests are sliced and budgeted per tick on the server.
- **Crowds**: DetourCrowd (ORCA-style) for groups; flow fields per cell for large counts (sieges, migrations); both consume the same navmesh.
- **Volumes**: a sparse voxel octree per cell for flying and swimming agents; the ocean surface (S30) is a dynamic ceiling or floor.
- **Dynamic obstacles**: DetourTileCache obstacles for doors, vehicles and physics debris; large changes fall back to tile rebuilds.
- **Positions**: tile coordinates are cell-local floats over double world positions (S07); origin rebasing never touches navmesh data.

## Done when

- A 10 km² world streams navmesh tiles with its cells; 1,000 server agents path and steer within the stated per-tick budget.
- A terrain edit rebuilds the affected tiles within a stated latency and agents re-plan.
- An agent walks from the surface into a cave through a layer link; a flying agent paths through a voxel volume.

## Open decisions

- Recast and Detour vendored versus in-house (the policy allows selected algorithm libraries; this one qualifies).
- Server authority: agents simulate on the server only, or clients predict NPC movement.
