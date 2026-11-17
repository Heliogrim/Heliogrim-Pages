# Work: Navigation

**Systems** S37 · **Issues** [#117](https://github.com/Heliogrim/Heliogrim-Engine/issues/117) · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Navigation](../topics/navigation.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| [Navmesh library fit](../../architecture/navigation-exploration.md) (W37.0) | Pick accepted (Q37.1); recastnavigation builds clean as C++23 with clang-cl 22; build, query, crowd and TileCache numbers on a 5900X; detail-mesh patch halves builds with identical output; layers partitioning | TileCache 255-cell layer limit versus 64 m tiles; float origin per region; further build optimisations in W37.2 |
| [Terrain work](terrain.md) | Tile grid, height layers, dirty-tile protocol | Navmesh tile equals terrain tile; one layer per height layer |
| [Storage work](storage-streaming.md) S40 | Cells and packages | Navmesh tiles stored in the cell package |
| [Ocean work](ocean-fluids.md) | Surface height | Dynamic ceiling or floor for volumes |
| [Physics work](physics-cloth.md) | Query service | Dynamic obstacles from physics bodies |
| [Networking work](networking-mmo.md) | Server authority | Agents replicate intent and scheduled actions per the [W56.0 tiers](../../architecture/agent-sync-exploration.md) (Q37.2) |
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

### W37.0 Recast and Detour build fit · explore · done 2026-11-09

- **Result**: [navmesh library fit](../../architecture/navigation-exploration.md). Vendor `recastnavigation` at a pinned `main` commit with `DT_POLYREF64`; write the hierarchy, flow fields, voxel octree and build scheduling in-house. Accepted 2026-11-09 (Q37.1 resolved). The performance pass is in the exploration, section 10.

- **Goal**: comparison table of navmesh library options and the in-house path (Q37.1), then build the pick with clang-cl 22 under the vendor rules; confirm sliced queries and TileCache behaviour on a sample; record licence.
- **Output**: `architecture/navigation-exploration.md`.

### W37.1 Navigation design · design · after W27.1, W40.1

- **Goal**: design against the constraints in the [exploration](../../architecture/navigation-exploration.md) section 7. Cover the tile contract, layers and links, hierarchy, crowd and flow fields, volumes, dynamic obstacles, server budgets, agent state replicable per the W56.0 tiers: agents replicate intent (current path segment, target, speed) beside the pose so engaged-tier clients can continue movement, and AI decisions leave as server-scheduled `ActionEvent`s ([agent-sync exploration](../../architecture/agent-sync-exploration.md) section 7).
- **Output**: `architecture/navigation-design.md`; plan.
- **Questions**: Q37.1, Q37.2.

### W37.2 Implement tiles, builds, queries and crowd · execute · after W37.1, W27.2, W40.2

- **Done when**: a 10 km² world streams navmesh tiles with its cells; 1,000 server agents path and steer within budget.
- **Carries**: `vendor/recastnavigation/` integrated the way the other vendors are, with patches auto-applied on fetch: a CMake patch that lifts the C++98 and exception overrides, and the detail-mesh cache patch with a tile-hash test against unpatched upstream. After that come measurement tasks for incremental Delaunay, terrain via `rcAddSpan` and threaded crowd avoidance, each gated by output or path-length equality ([exploration](../../architecture/navigation-exploration.md) section 10.7). The patch and the spike source are untracked in the engine checkout under `docs/superpowers/patches/`.

### W37.3 Terrain edit rebuilds and layer links · execute · after W37.2, W28.2

- **Done when**: an edit rebuilds affected tiles within the stated latency; an agent walks from surface into a cave through a link.

### W37.4 Flight volumes and flow fields · execute · after W37.2

- **Done when**: a flying agent paths through a voxel volume; a flow field moves a large group.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q37.1 | Start with a vendored navmesh library. W37.0 first produces a comprehensive comparison of the options (Recast and Detour, alternatives, an in-house voxeliser and tile builder) with pros, cons, licence and maintenance state for each, and picks from that table. The pick is wrapped behind engine types. **Resolved by W37.0 (2026-11-09)**: vendor `recastnavigation` (zlib) pinned to a `main` commit, with an in-house hierarchy, flow fields and voxel octree ([exploration](../../architecture/navigation-exploration.md) section 6, [ADR-0010](../../adr/0010-navmesh-recastnavigation.md)). The owner asked for a performance pass before W37.2: faster alternatives, or optimisations that keep quality. |
| Q37.2 | Server-only simulation with 100 to 200 ms visible reaction latency is rejected: combat will be snappy and partly fast-paced. A tiered synchronisation strategy is expected (client prediction with soft reconciliation as one part, lock-step action evaluation for all agents and players inside the perceptive effective range as another, cheaper replication by distance). Spike W56.0 on the networking page works it out; W37.1 keeps the agent state shape open for those tiers. Desk study done 2026-11-09 ([agent-sync exploration](../../architecture/agent-sync-exploration.md)): agents replicate pose plus intent, decisions go out as scheduled action events, AI think time absorbs the scheduling delay. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q37.1 | Vendor Recast and Detour (zlib) or write the voxeliser in-house? | W37.1 | Vendor, wrapped behind engine types |
