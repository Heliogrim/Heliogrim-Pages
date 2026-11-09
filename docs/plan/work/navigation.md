# Work: Navigation

**Systems** S37 · **Issues** [#117](https://github.com/Heliogrim/Heliogrim-Engine/issues/117) · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Navigation](../topics/navigation.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| [Terrain work](terrain.md) | Tile grid, height layers, dirty-tile protocol | Navmesh tile equals terrain tile; one layer per height layer |
| [Storage work](storage-streaming.md) S40 | Cells and packages | Navmesh tiles stored in the cell package |
| [Ocean work](ocean-fluids.md) | Surface height | Dynamic ceiling or floor for volumes |
| [Physics work](physics-cloth.md) | Query service | Dynamic obstacles from physics bodies |
| [Networking work](networking-mmo.md) | Server authority | Agents simulate on the server (Q37.2) |
| Vendor policy (vision page) | Selected algorithm libraries allowed | Recast and Detour qualify (Q37.1) |

## Architecture

- **Bundles**: new `Engine.Navigation` (engine tile format, queries, crowd, volumes, hierarchy; wraps Recast and Detour), `Engine.Navigation.Build` (tile builds on Background fibers), `Editor.Navigation` (visualisation, link authoring).
- **Provides**: path queries with agent class, crowd steering, flow fields, flight volumes, tile rebuild on terrain edits.
- **Consumes**: terrain tiles and layers (S27, S28), cells (S40), static geometry, physics bodies (S34), ocean height (S30), scheduler lanes (S02), replication (S56, later).

## Code design

| Type | Contract |
|---|---|
| `NavTile` | Engine-owned tile keyed by `(TileCoord, layer)`; Detour data inside; built from terrain layer, voxel overlay and static geometry; serialised in the cell package. |
| `NavBuildJob` | Background-lane task per dirty tile; swap at a frame boundary. |
| `AgentClass` | Radius, height, step, allowed layers and link types; selects navmesh layer and links. |
| `LayerLink` | Authored or detected connection between layers (stairs, ladders, cave mouths). |
| `PathQuery` | Sliced, budgeted per tick; hierarchical: portal graph over tiles for long distance, Detour within a tile window. |
| `Crowd` | DetourCrowd (ORCA style) for groups; `FlowField` per cell for large counts; both over the same navmesh. |
| `FlightVolume` | Sparse voxel octree per cell for flying and swimming agents; ocean surface as a dynamic bound. |
| `DynamicObstacle` | DetourTileCache obstacles for doors, vehicles, debris; large changes rebuild tiles. |
| Coordinates | Tile-local floats over double world positions; rebasing never touches navmesh data. |

Placement: `Engine.Navigation/{NavTile,AgentClass,LayerLink,PathQuery,Crowd,FlowField,FlightVolume}`, `Engine.Navigation.Build/NavBuildJob`, `Editor.Navigation/`. Tests: 10 km² streaming with 1,000 server agents per-tick budget; edit-to-replan latency; cave link walk; flight volume path.

## Work chunks

### W37.0 Recast and Detour build fit · explore · ready

- **Goal**: comparison table of navmesh library options and the in-house path (Q37.1), then build the pick with clang-cl 22 under the vendor rules; confirm sliced queries and TileCache behaviour on a sample; record licence.
- **Output**: `architecture/navigation-exploration.md`.

### W37.1 Navigation design · design · after W37.0, W27.1, W40.1

- **Goal**: tile contract, layers and links, hierarchy, crowd and flow fields, volumes, dynamic obstacles, server budgets.
- **Output**: `architecture/navigation-design.md`; plan.
- **Questions**: Q37.1, Q37.2.

### W37.2 Implement tiles, builds, queries and crowd · execute · after W37.1, W27.2, W40.2

- **Done when**: a 10 km² world streams navmesh tiles with its cells; 1,000 server agents path and steer within budget.

### W37.3 Terrain edit rebuilds and layer links · execute · after W37.2, W28.2

- **Done when**: an edit rebuilds affected tiles within the stated latency; an agent walks from surface into a cave through a link.

### W37.4 Flight volumes and flow fields · execute · after W37.2

- **Done when**: a flying agent paths through a voxel volume; a flow field moves a large group.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q37.1 | Start with a vendored navmesh library. W37.0 first produces a comprehensive comparison of the options (Recast and Detour, alternatives, an in-house voxeliser and tile builder) with pros, cons, licence and maintenance state for each, and picks from that table. The pick is wrapped behind engine types. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q37.1 | Vendor Recast and Detour (zlib) or write the voxeliser in-house? | W37.1 | Vendor, wrapped behind engine types |
| Q37.2 | Do clients predict NPC movement, or do agents simulate on the server only with replicated poses? | W37.1 | Server only; clients interpolate |
