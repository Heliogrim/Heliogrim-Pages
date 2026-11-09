# Work: Procedural Generation

**Systems** S33 · **Issues** [#113](https://github.com/Heliogrim/Heliogrim-Engine/issues/113) · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Procedural generation](../topics/procedural-generation.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| [Visual scripting work](visual-scripting-hmr.md) S47 | Graph IR compiled to C++ | Generators are the second graph-compiler client after scripts (or third after particles) |
| `Editor.GFX.Graphs` | Node definitions without a compiler | Point-data nodes are a new node family |
| [Storage work](storage-streaming.md) S40 | Cells stream on Background fibers | Generation runs inside cell streaming |
| [Terrain work](terrain.md) | Tiles, op-log deltas | Erosion bakes into tiles; runtime edits are deltas |
| [Particles and foliage work](particles-foliage.md) S25 | Instances derived from scatter | Scatter output contract |
| Deterministic math (S59) | Integer hashes, pinned trig | Authoritative generators use them |

## Architecture

- **Bundles**: new `Engine.World.Procedural` (generator contract, typed point data, seeds, cache) and `Engine.World.Procedural.Generators` (noise, scatter, roads, erosion); `Editor.Procedural` (graph authoring through S47, preview). Erosion runs in the worker role (S58).
- **Provides**: `Generator` contract; typed point sets, height and material deltas, spline networks, structure placements; content-hashed cache with generator versions.
- **Consumes**: cells (S40), terrain tiles (S27, S28), graph compiler (S47), Background lane (S02), worker role (S58), deterministic math (S59).

## Code design

| Type | Contract |
|---|---|
| `Generator` | Pure function `(worldSeed, CellCoord, GeneratorVersion, Inputs) -> Outputs`; same code on server and client; no state. |
| `CellSeed` | `hash(worldSeed, cell.x, cell.y, featureId)` with an integer hash (PCG or splitmix); never a sequential RNG across cells. |
| `PointSet` | Typed point data with attributes (position, normal, scale, tags); the common currency between nodes and consumers. |
| `GenGraph` | Nodes `Sample, Filter, Transform, Scatter, Spawn` declaring reads and writes; compiled by the S47 compiler to C++ for shipping, interpreted in the editor; until S47 exists generators are hand-written against `Generator`. |
| `GenCache` | Key `hash(inputs, version)`; stores outputs per cell; invalidated by a version bump. |
| `ErosionBake` | Offline worker-role pass over the whole terrain with border overlap; writes terrain tiles. |
| `ScatterRule` | Density, slope and height masks, exclusion zones; outputs `PointSet` consumed by foliage and props; hand-placed overrides stored separately. |
| `RoadNetwork` | Spline network from tensor fields or authored control points; emits terrain deltas and placements. |

Placement: `Engine.World.Procedural/{Generator,CellSeed,PointSet,GenCache}`, `Engine.World.Procedural.Generators/{Noise,Scatter,Roads,Erosion}`, `Editor.Procedural/`. Tests: bit-identical regeneration on two machines; seamless scatter across cell boundaries; version bump invalidates the cache.

## Work chunks

### W33.1 Procedural contract and scatter design · design · after W40.1

- **Goal**: `Generator`, seeds, `PointSet`, cache, scheduling inside cell streaming, the scatter rule contract for foliage, which generators are authoritative.
- **Output**: `architecture/procedural-design.md`; plan.
- **Questions**: Q33.1, Q33.2.

### W33.2 Implement contract, noise and scatter (hand-written generators) · execute · after W33.1, W40.2

- **Done when**: a cell regenerates bit-identically on two machines; a rock scatter crosses cell boundaries without seams.

### W33.3 Erosion bake in the worker role · execute · after W33.2, W27.2, W58.2

- **Done when**: an eroded 10 km² terrain bakes and loads as tiles.

### W33.4 Roads and structures · execute · after W33.2, W28.2

- **Done when**: a road network generates across cells and deforms terrain through the op log.

### W33.5 Graph authoring through the S47 compiler · execute · after W47.3, W33.2

- **Done when**: a scatter graph authored in the editor compiles to C++ and matches the hand-written generator's output.

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q33.1 | Which generator classes are authoritative (server and client identical) versus cosmetic? | W33.1 | Authoritative: terrain deltas, roads, structures, gameplay props; cosmetic: foliage detail and debris |
| Q33.2 | Wait for the S47 graph compiler before any graph authoring, or build a small interpreted point-data graph in the editor now? | W33.1 | Wait; hand-written generators until S47 |
