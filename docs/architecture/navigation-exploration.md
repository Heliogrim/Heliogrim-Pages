# Navmesh Library Fit (Exploration)

**Status**: <span class="hg-status closed">closed</span> 2026-11-09. Answers chunk [W37.0](../plan/work/navigation.md) for decision Q37.1 (which navmesh library, or an in-house builder). The owner accepted section 6 on 2026-11-09; it is recorded as ADR [placeholder](../adr/placeholder-navmesh-recastnavigation.md). The owner then asked for a performance pass, which is section 10. [W37.1](../plan/work/navigation.md) designs against sections 7 and 10.
**Origin**: 2026-11-09. One read-only research pass covered the options in section 3: repositories, headers, release pages, papers and engine documentation (sources in section 9). The build and the numbers in sections 4 and 5 come from a throwaway spike in the session scratchpad on the owner's workstation. Engine checked on branch `feat/affine-threads` (HEAD `a9242621`). No engine code was changed.

## 1. Question

Q37.1 was decided as: start with a vendored navmesh library, but first compare the options (Recast and Detour, alternatives, an in-house voxeliser and tile builder) on pros, cons, licence and maintenance, and pick from that table. W37.0 adds three checks: the pick builds with clang-cl 22 under the vendor rules, sliced queries and TileCache behave on a sample, and the licence is recorded.

## 2. Current engine state (checked 2026-11-09)

- The engine has no navigation code: no bundle, no vendored library, nothing in the code graph.
- Vendored libraries follow the Jolt pattern: `vendor/<name>/CMakeLists.txt` pulls a pinned tag through `CachedFetchContent_Declare` and exports an `External::` target.
- Vendor rules (Batch 2): no licensed or paid software; third-party code only for platform integration, selected algorithms and standard codecs; comparison tables come before picking a navmesh library.

## 3. Options

Excluded up front, because they are paid or proprietary: Havok AI, PathEngine, Kythera, xaitment. Unreal's Recast fork also ships under the Epic EULA. It counts here as evidence of what a large engine changed, not as code we can take.

Evidence marks: **V** means verified in a header, README, source or release page. **U** means unverified (search summary only).

| Option | Licence | Maintenance (checked 2026-11-09) | What it covers for us | What it costs or risks |
|---|---|---|---|---|
| **recastnavigation** (Recast, Detour, DetourTileCache, DetourCrowd) | zlib (V) | Last tag `v1.6.0` from 2023-05-21. `main` has 367 commits since; 46 commits since 2025-11, the last on 2026-02-27 (`9f4ce64`, a large-world crash fix). One active maintainer (V) | Voxeliser and tile builder, tiled Detour navmesh, height layers, sliced A\*, TileCache obstacles (cylinder, box, rotated box), crowd steering (V). No 3D volumes; they are on its roadmap (V) | Floats only. No threading model; that is a roadmap item (V). Small API surface, C++98 style. About 27k lines in total: Recast 10.5k, Detour 9.2k, TileCache 3.5k, Crowd 4.2k (counted) |
| **Godot navigation** | MIT | Active | Vendors Recast 1.6.0 unpatched. Does not use Detour; queries, maps and regions are Godot's own code. Avoidance uses RVO2 (V) | Nothing standalone to reuse. Shows that the Recast builder can be paired with a query layer of your own |
| **Unreal's Recast fork** | Epic EULA, unusable | n/a | World-partitioned navmesh (experimental): streamed chunks, a fixed tile pool, rebuilds limited to the loaded area (V). Double precision via `dtReal` (U) | Evidence only |
| **O3DE RecastNavigation gem** | Apache-2.0 / MIT | Active | Upstream 1.6.0 with `DT_POLYREF64` on; async tile updates; no crowd (V) | Nothing to take beyond the 64-bit reference choice |
| **Polyanya** (Cui, Harabor, Grastien, IJCAI 2017, pp. 496–502) | Original C++ is MIT, but its Fade2D triangulator needs a commercial licence (V). The Rust port `vleue/polyanya` is MIT/Apache-2.0 (V) | Research code; the Rust port is active | Optimal any-angle search over convex polygons (V) | A query algorithm only: no builder, no tiles, no streaming. Could run later over Detour polygons |
| **Ports**: rerecast (Rust), DotRecast (C#), recast4j (Java) | MIT/Apache-2.0, zlib, zlib (V) | rerecast active; oxidized_navigation archived 2025-11-14 (V) | rerecast builds only, no queries. recast4j adds multithreaded builds and a "dynamic voxel" navmesh with obstacles (V) | Wrong languages. recast4j's dynamic-voxel module is worth reading for W37.3 |
| **Hierarchy, flow-field and voxel-octree libraries** (uesvon, AeonixNavigation, Nav3D, HNA-Algorithm) | MIT or zlib (V) | Aeonix and Nav3D active; the others stale | Nav3D implements Brewer's sparse voxel octree (Game AI Pro 3, ch. 21) (V) | All are tied to Unreal or are demos. No maintained, standalone, permissive C++ library exists for hierarchical navmesh search, flow-field tiles or voxel-octree pathfinding |
| **In-house** voxeliser, tile builder and queries | ours | ours | Everything, designed around 64 m tiles, 256 m cells, origin-relative coordinates and the fiber scheduler | Roughly 27k lines to match Recast and Detour alone. The robust parts (span merging, region partitioning, contour simplification, tile-border stitching) took upstream years of fixes. No measured gap would justify the rewrite; the owner's bar for replacing vendored code is a clear common-case win worth maintaining |

## 4. Build fit (clang-cl 22)

**Setup.**
- Source: `recastnavigation` `main` at `9f4ce64` (2026-02-27).
- Compiler: clang-cl 22.1.3 (Visual Studio 18 toolchain), Ninja, RelWithDebInfo (`/O2 /Ob1`), `RECASTNAVIGATION_DT_POLYREF64=ON`.
- Flags: `/clang:-std=c++23 /W4`.

**Findings.**
- **The upstream targets pin `CXX_STANDARD 98`**, so `CMAKE_CXX_STANDARD=23` does not reach them; the spike forced C++23 through the flags. On MSVC-style compilers upstream also replaces `/EHsc` with `/EHs-c-` and defines `_HAS_EXCEPTIONS=0`. The fix is a patch to the upstream `CMakeLists.txt` files. The vendor helpers already apply git patches on fetch and update (`PATCH_COMMAND git restore …` then `COMMAND git apply ../<name>.patch`, as for zlib, assimp, gli, spng, vorbis and vulkan-loader), so the upstream build can be used with engine flags.
- **It builds clean as C++23.** The libraries (Recast, Detour, DetourTileCache, DetourCrowd, DebugUtils) took 11 s on 22 jobs. The only warnings were 14 `-Wunused-parameter`; there were no errors.
- **The upstream tests pass.** 32 of 33 Catch2 test cases pass (3,823 assertions). The 33rd aborts only because Catch2's `SKIP` needs exceptions, which upstream turns off; it is a harness artefact, not a library failure.
- **Licence**: zlib, "Copyright (c) 2009 Mikko Mononen". Binaries need no attribution; altered sources must be marked as altered. FastLZ (used by the demo as the TileCache compressor) is MIT and lives in `RecastDemo/Contrib`, not in the libraries.

## 5. Measurements

**Setup.**
- Hardware: AMD Ryzen 9 5900X (12 cores, 24 threads), 32 GB, Windows 11 Pro build 26300. Libraries as in section 4; spike `/O2`.
- Scene: a synthetic 1,024 m × 1,024 m terrain (1 m grid, rolling hills, 2.1 M triangles) with 300 pillars (4 × 4 × 10 m) and one deck 30 m up as a second layer.
- Agent: radius 0.5 m, height 2 m, climb 0.5 m, slope 45°.
- Tiles: 64 m (the terrain tile).
    - Solo path: cell 0.25 m (256 cells per tile), cell height 0.2 m, watershed regions.
    - TileCache path: cell 0.32 m (200 cells), because a TileCache layer stores its width in an `unsigned char` (see below).
- Two runs; the table shows run 2, and run 1 was within 15 %.

**Caveat.** The terrain is smooth, so the solo navmesh averages only 12 polygons per tile. Real content (rocks, buildings, foliage collision) will raise the polygon count, the memory, and the query iterations. Treat memory and query numbers as lower bounds; build times are less sensitive, because voxelisation cost follows the cell count, not the polygon count.

| Measure | Result |
|---|---|
| Solo tile build (rasterise to Detour data), 1 thread | p50 42 ms, p99 148 ms per 64 m tile; 14.4 s per km² |
| Same, 24 threads | 1.42 s per km² (10.1× speed-up); about 15 s for 10 km² by extrapolation |
| Detour tile data | 1.16 MB per km² (3,071 polygons); `addTile` for all 256 tiles 0.4 ms |
| Sliced A\*, random pairs up to 1.4 km | iterations p50 135, p99 2,346; time p50 15 µs, p99 231 µs; 110 ns per iteration; no partial results at 65,535 nodes |
| Sliced A\*, pairs within 64 m | iterations p50 5, p99 22; time p50 1 µs, p99 2 µs |
| DetourCrowd tick (20 Hz), 25 / 250 agents | p50 0.05 / 0.72 ms, p99 0.09 / 1.03 ms |
| DetourCrowd tick, 1,000 agents spread over 1 km² / packed within 120 m | p50 2.5 / 3.1 ms, p99 4.0 / 4.2 ms |
| TileCache layer build (rasterise + layers), 24 threads | 185 ms per km²; 542 layers in 256 tiles (at most 4 per tile) |
| TileCache layer data | 3.2 MB per km² with FastLZ (62 MB per km² uncompressed) |
| Navmesh from TileCache layers, 1 thread | 114 ms per km² (about 0.2 ms per layer) |
| TileCache obstacle edit | 200 cylinders, 201 `update()` calls, 51 ms total; one layer rebuild per call, p50 0.33 ms, p99 0.51 ms |

**What the numbers say.**
- **Edits.** An obstacle edit through TileCache costs about 0.3 ms per touched layer. That is about 130 times cheaper than re-voxelising a tile (42 ms). Terrain edits change geometry, so they still need the re-voxelise path for the touched tiles: tens of milliseconds per tile on one Background fiber. That is well inside a "replan within a second" target; W37.3 states the budget.
- **Server path budget.** Suppose 1,000 agents each replan a long path once per second at a 20 Hz tick. That is 50 queries per tick, about 0.75 ms at p50; one long p99 query costs 0.23 ms. Sliced queries with a per-tick iteration budget (for example 64 iterations per step, as in the spike) keep the tail bounded.
- **Crowd.** The old header advice (25 agents for 0.5 ms) is out of date on this CPU: 1,000 agents cost about 3 µs each per tick. A crowd instance is single-threaded, so the design should give each region its own crowd instance. Flow fields stay the plan for large groups. The spike did not check that every agent reached its target.

## 6. Recommendation

1. **Vendor `recastnavigation`** pinned to a `main` commit (currently `9f4ce64`), not the 2023 tag: `main` carries the large-world crash fix and the assert fix.
    - Modules: Recast, Detour, DetourTileCache, DetourCrowd. DebugUtils for the editor only.
    - `DT_POLYREF64` on: 16 salt, 28 tile and 20 polygon bits. A 10 km² world at 64 m tiles with several layers would strain the 32-bit split.
    - Integrate it like the other vendors: `vendor/recastnavigation/CMakeLists.txt` with `CachedFetchContent_Declare` at the pinned commit, and local changes as git patch files beside it. The helpers apply them on every fetch or update. One patch lifts the C++98 pin and the exception override, so the engine's C++23 flags apply.
    - Keep each patch small and atomic, one concern per file.
2. **Wrap everything behind `Engine.Navigation` types.** Detour data stays inside `NavTile`; refs, filters and query objects never leave the wrapper.
3. **Write these in-house**, because no option provides them:
    - the tile hierarchy (an HPA\*/HNA\*-style portal graph per 256 m cell)
    - flow-field tiles (Emerson, Game AI Pro ch. 23, 2013)
    - the sparse voxel octree for flying and swimming agents (Brewer, Game AI Pro 3 ch. 21, 2017)
    - the build scheduling on Background fibers
    - the tile serialisation in the cell package
4. **Do not write an in-house voxeliser now.** Nothing in the comparison or the numbers shows a gap that pays for about 27k lines of hard geometry code. Reopen this only if a measured limit (section 7) blocks a W37.2 or W37.3 "done when".
5. **Polyanya** (any-angle search) is a candidate query layer for later, through the MIT Rust algorithm reimplemented in C++. It is not needed for W37.2.

## 7. Constraints W37.1 must design around

| Constraint | Source | Consequence |
|---|---|---|
| A TileCache layer's width and height are `unsigned char` (at most 255 cells; `layer->width = w - 2·border`) | `DetourTileCacheBuilder.h`, `RecastLayers.cpp` (V) | A 64 m TileCache tile needs a cell size of at least 0.251 m. Choose between cell 0.32 m (200 cells, used in the spike) and 32 m TileCache sub-tiles at 0.25 m (four per terrain tile). "Navmesh tile equals terrain tile" holds only with the first |
| `dtNavMeshParams::orig` and all coordinates are `float` | `DetourNavMesh.h` (V) | Tile-local floats over double world positions, as the code design already says. One `dtNavMesh` per streaming region with its own origin, or one world mesh with a fixed origin. Open issue #826: signed-integer overflow in `dtProximityGrid::hashPos2` far from the origin (V) |
| Layered tiles link only when all of a column's layers come from one `rcBuildHeightfieldLayers` call | Open issue #818 (V) | Build cave layers as whole tile columns. A cave that spans tiles must be built in every tile it touches |
| One sliced search per `dtNavMeshQuery` object; `addTile` and `removeTile` mutate the mesh | `DetourNavMeshQuery.h`, `DetourNavMesh.h` (V) | A pool of query objects, one per worker. Tile swaps happen at a frame boundary (already in the `NavBuildJob` contract) |
| Each `dtTileCache::update()` call rebuilds one layer and scans all obstacle slots; 64 queued requests at most | `DetourTileCache.cpp` (V); 129 queue-full retries in the spike | Drive `update` from a budgeted task. Size `maxObstacles` to what is live, not the worst case. Large changes go to a tile rebuild, as planned |
| Span height 13 bits (8,191 cells per column); 63 area IDs in Recast, 64 in Detour; at most 65,535 search nodes; 6 neighbours per crowd agent | headers (V) | At 0.2 m cell height a tile column covers 1,638 m vertically, which is enough. Area IDs must cover agent classes and effect volumes together |
| No threading inside the library | roadmap (V) | Tile builds are independent; each needs its own `rcContext`. The spike scaled 10.1× on 24 threads |

## 8. Open points for the owner

- Section 6 was accepted on 2026-11-09 (ADR [placeholder](../adr/placeholder-navmesh-recastnavigation.md)).
- Whether to offer the detail-mesh patch from section 10 upstream. It is outward-facing, so the owner decides.
- The tile-size choice in section 7, row 1, is left to W37.1. The suggested default is cell 0.32 m at 64 m tiles, so the navmesh tile stays equal to the terrain tile; the spike showed no quality problem at that cell size on open terrain.
- The TileCache compressor should come from the codec decision (W03.5). FastLZ is only the demo's choice. The spike's 20:1 ratio is on smooth terrain.

## 9. Sources

- recastnavigation, `main` at `9f4ce64`: <https://github.com/recastnavigation/recastnavigation> (README, `CHANGELOG.md`, `Docs/_99_Roadmap.md`, `Docs/_2_BuildingAndIntegrating.md`, `CMakeLists.txt`, headers `DetourNavMesh.h`, `DetourNavMeshQuery.h`, `DetourTileCache.h`, `DetourTileCacheBuilder.h`, `DetourCrowd.h`, `Recast.h`; sources `DetourTileCache.cpp`, `RecastLayers.cpp`). Issues [#818](https://github.com/recastnavigation/recastnavigation/issues/818), [#826](https://github.com/recastnavigation/recastnavigation/issues/826); PR [#796](https://github.com/recastnavigation/recastnavigation/pull/796).
- Godot: <https://raw.githubusercontent.com/godotengine/godot/master/thirdparty/README.md>, <https://github.com/godotengine/godot/tree/master/modules/navigation_3d/3d>.
- Unreal: <https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partitioned-navigation-mesh> (the `dtReal` double claim is U).
- O3DE: <https://raw.githubusercontent.com/o3de/o3de/development/Gems/RecastNavigation/3rdParty/FindRecastNavigation.cmake>, <https://docs.o3de.org/docs/user-guide/interactivity/navigation-and-pathfinding/recast-navigation/>.
- Polyanya: Cui, Harabor, Grastien, "Compromise-free Pathfinding on a Navigation Mesh", IJCAI 2017, <https://www.ijcai.org/proceedings/2017/0070.pdf>; <https://bitbucket.org/dharabor/pathfinding/raw/master/anyangle/polyanya/README.md>; <https://github.com/vleue/polyanya>.
- Ports: <https://github.com/janhohenheim/rerecast>, <https://github.com/TheGrimsey/oxidized_navigation>, <https://github.com/ikpil/DotRecast>, <https://github.com/recast4j/recast4j>.
- Volumes and hierarchy: <https://github.com/midgen/uesvon>, <https://github.com/midgen/AeonixNavigation>, <https://github.com/darbycostello/Nav3D>, <https://github.com/educharlie/HNA-Algorithm>.
- Game AI Pro chapters: Brewer, ch. 21 of Game AI Pro 3 (2017), <http://www.gameaipro.com/GameAIPro3/GameAIPro3_Chapter21_3D_Flight_Navigation_Using_Sparse_Voxel_Octrees.pdf>. Emerson, ch. 23 of Game AI Pro (2013), <http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter23_Crowd_Pathfinding_and_Steering_Using_Flow_Field_Tiles.pdf>. "Precomputed Pathfinding for Large and Detailed Worlds on MMO Servers", ch. 20 of Game AI Pro (2013), <http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter20_Precomputed_Pathfinding_for_Large_and_Detailed_Worlds_on_MMO_Servers.pdf>; read it before W37.1 sets the server path budget.
- Not checked: the code change in #796, recast4j's last commit date, and the HNA\* paper's venue (the research page gives Computers & Graphics 59, 2016).

## 10. Performance pass (2026-11-09)

The owner found the section 5 build times high and the 2023 release date suspicious, and asked whether a faster solution exists, or whether the build can be optimised without losing quality. A second read-only research pass looked for faster methods, and a second spike profiled each build stage.

### 10.1 Maintenance (the 2023 release)

Upstream has not tagged a release since `v1.6.0` (2023-05-21). The work continues on `main`:

- 46 commits since 2025-11, the last on 2026-02-27.
- Mostly by one maintainer.
- The work covers the demo, CMake, tests and two large-world crash fixes.

Releases are therefore a poor signal. The real risk is one maintainer, and the ADR records it: we pin a `main` commit and own our patches.

### 10.2 Is 42 ms per tile high?

- **It follows from the tile size.** A 64 m tile at 0.25 m cells has 256² cells. Epic recommends 32 to 128 cells per side for tiles that rebuild at runtime (verified, Epic documentation), so our tiles are 4 to 64 times that area.
- **No faster method at Recast's quality was found.**
    - GPU voxelisation loses on terrain. Brodén and Bohlin (BTH MSc thesis, 2017; i5-4670K and RX 480) measured the GPU at 115 % to 163 % of CPU time on a game level. It won only on a dense mesh, where triangles are small relative to the voxels (verified, full text).
    - Other GPU navmesh work builds different structures: NEOGEN (Computers & Graphics, 2013) and GPU Voronoi navmeshes (MIG 2014).
    - No engine or studio publishes per-tile or per-km² build times.

### 10.3 Where the time goes

**Setup.**
- Libraries rebuilt as Release (`/O2 /Ob2 /arch:AVX2`).
- Same scene and agent as section 5.
- 64 m tiles; one thread for the per-stage split.
- Quality is checked against the baseline on 400 fixed query pairs: polygon count, tile bytes, path success, total straight-path length and a hash of all tile data.

**Per-stage split, upstream, watershed, 0.25 m cells (43.7 ms per tile):**

| Stage | ms per tile | Share |
|---|---|---|
| Rasterise, filter, compact, erode | 5.7 | 13 % |
| Distance field + watershed regions | 4.1 | 9 % |
| Contours and polygon mesh | 0.4 | 1 % |
| **Detail mesh** | **33.3** | **76 %** |

**Cause.** The detail mesh refines each polygon's height by greedily inserting the worst height sample. After every insertion, upstream rebuilds the whole Delaunay triangulation and re-measures every remaining sample against every triangle. The source marks this with `TODO: Incremental add instead of full rebuild`. Large, flat-ish terrain polygons hit the 127-vertex cap, so the loop runs about 127 times per polygon.

**What did not matter.**
- A per-thread bump arena through `rcAllocSetCustom` (peak 5.9 MB per thread) changed nothing. The allocator is not the bottleneck.
- Scaling from 12 to 24 threads gains only about 1.5×, with per-tile time rising under load. That fits SMT sharing and all-core clocks on a 12-core part rather than contention; on 12 threads the speed-up is 7×.

### 10.4 Detail-mesh patch (spike)

**What it does.** The patch caches each sample's distance to the triangulation. After a rebuild it diffs the triangle set by ordered vertex triple:

- Samples inside a removed triangle are measured again in full.
- All other samples only fold in the added triangles.

That is exactly what the full scan computes, so the output cannot change. About 80 lines in `RecastMeshDetail.cpp`, no API change.

| Variant (watershed, 0.25 m cells) | 1 thread, ms per tile | 24 threads, s per km² | Tile data |
|---|---|---|---|
| Upstream | 43.7 | 1.01 | hash `435c10b6…` |
| Patched | 20.1 | 0.50 | hash `435c10b6…`, **byte-identical** |

**What remains in the patched detail stage** (9.9 ms):
- 3.0 ms is the full Delaunay rebuild. The incremental insertion that upstream's TODO names would remove most of it.
- 5.5 ms is the remaining sample scan. Bucketing samples by triangle would cut it.

Both keep the output equivalent but are larger changes. They are W37.2 candidates, not needed now.

### 10.5 Options that trade quality (patched build)

| Variant | 1 thread, ms per tile | 24 threads, s per km² | Polygons | Path length vs baseline |
|---|---|---|---|---|
| Watershed, 0.25 m (reference) | 20.1 | 0.50 | 3,071 | ±0 % |
| Monotone, 0.25 m | 18.5 | 0.41 | 2,541 | +0.01 % |
| Layers, 0.25 m | 16.7 | 0.43 | 2,300 | +0.02 % |
| Watershed, 0.32 m (the TileCache cell size from section 7) | 13.7 | 0.32 | 2,519 | +0.52 %, one more path found |
| Watershed, 0.5 m | 5.9 | 0.13 | 2,774 | +0.76 % |

- **Layers partitioning** is the one near-free choice. Upstream calls it a good fit for tiled meshes, and it avoids watershed's overlap corner cases. Paths stayed within 0.02 %, and `findPath` got faster because there are fewer polygons.
- **Monotone** is fast but documented to produce long, thin polygons; avoid it.
- **Coarser cells** pay in path length and in narrow passages.
- **Without detail samples** (`detailSampleDist = 0`) the spike crashed, on unpatched upstream as well. Not investigated, and not a recommendation: dropping the samples gives up height accuracy.

### 10.6 Further options from research, not measured

- **Terrain straight into the heightfield** with `rcAddSpan`, rasterising only props. The API is public, and a maintainer confirmed in issue #341 that this works. It saves part of the 5.7 ms rasterise stage. Quality is unmeasured: the spans must match triangle rasterisation, which the tile-hash check can verify.
- **Sorting triangles top-down before rasterising.** An issue author measured 20 s → 13 s on about 3 million triangles (issue #332, hardware not stated). Zero quality cost.
- **Crowd avoidance across threads.** `dtCrowd::update` is single-threaded. After neighbour gathering, avoidance is independent per agent. ORCA (van den Berg et al., ISRR 2009, Springer STAR vol. 70, 2011) scaled nearly linearly on 8 cores. ClearPath (Guy et al., SCA 2009) reached about 4 µs per agent on a 2009 core. Our 3 µs per agent on Zen 3 is in that range, so the gain comes from threading, not from another algorithm. GPU ORCA only wins above about 2,000 agents (Charlton et al., arXiv 2019).

### 10.7 Recommendation for W37.1 and W37.2

1. **Carry the detail-mesh cache patch** as a vendor patch file (`vendor/recastnavigation/detail-sample-cache.patch`, about 70 changed lines), applied on fetch by the existing helpers like the zlib and assimp patches. It halves tile builds and leaves the output byte-identical.
    - W37.2 adds a test that compares tile hashes against unpatched upstream on a fixed scene, so the patch stays honest.
    - Moving the pinned commit means re-applying the patch. A conflict fails the fetch loudly instead of drifting silently.
    - Offering the patch upstream is the owner's call.
2. **Use layers partitioning** for tiled builds unless W37.1 finds a quality case against it.
3. **Treat incremental Delaunay, terrain via `rcAddSpan`, and threaded crowd avoidance as W37.2 measurement tasks**, each gated by the same output or path-length check.
4. **Expected result**: about 0.4–0.5 s per km² on the 5900X at 0.25 m cells. That is roughly 5 s for the 10 km² test world, with no quality loss against upstream.

**Sources for this section**:
- Brodén and Bohlin 2017: <https://www.diva-portal.org/smash/get/diva2:1104795/FULLTEXT02.pdf>
- Epic tile guidance: <https://dev.epicgames.com/documentation/en-us/unreal-engine/optimizing-navigation-mesh-generation-speed-in-unreal-engine>
- recastnavigation issues [#332](https://github.com/recastnavigation/recastnavigation/issues/332) and [#341](https://github.com/recastnavigation/recastnavigation/issues/341), PR [#467](https://github.com/recastnavigation/recastnavigation/pull/467)
- ORCA: <https://gamma.cs.unc.edu/ORCA/publications/ORCA.pdf>
- ClearPath TR09-006: <http://www.cs.unc.edu/techreports/09-006.pdf>
- Charlton et al. 2019: <https://arxiv.org/html/1908.10107v1>
- NEOGEN: <https://dl.acm.org/doi/abs/10.1016/j.cag.2013.03.004>
- Upstream partitioning notes: `RecastDemo/Source/Sample_SoloMesh.cpp`

The patch (against `9f4ce64`) and the spike source are kept untracked in the engine checkout under `docs/superpowers/patches/` until W37.2 moves the patch into `vendor/recastnavigation/`.
