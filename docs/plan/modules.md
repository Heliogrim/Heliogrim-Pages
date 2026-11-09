# Required Modules

**Status**: <span class="hg-status summary">plan</span>. The bundles the [target architecture](architecture.md) needs, mapped to the bundles that exist. File and line counts were taken from the source on 2026-11-07 (`src/<Bundle>/**`, headers and sources only); they grade size, not quality. The generated [module map](../architecture/modules.md) has the include graph.

Legend: <span class="hg-status accepted">exists</span> usable as is · <span class="hg-status design">partial</span> exists, needs the listed work · <span class="hg-status planned">missing</span> no bundle yet · <span class="hg-status closed">replace</span> exists but will be superseded.

## Foundation

| Target bundle | Today | State | Work |
|---------------|-------|-------|------|
| `Engine.Common` | 118 files, 13.1k lines | <span class="hg-status accepted">exists</span> | Keep; dead code noted in test notes (`RingBuffer`, `Integral128`, `InlineVector`) to remove |
| `Engine.Math` (own bundle) | inside `Engine.Common`; `Engine.Math.Test` exists | <span class="hg-status design">partial</span> | Split out; add double-precision vector types for world space (S07), SIMD paths measured |
| `Engine.Asserts`, `Engine.Logging` | small | <span class="hg-status design">partial</span> | Logging becomes a sink of the diagnostics and observability services (S04, S05) |
| `Engine.Diagnostics` | none | <span class="hg-status planned">missing</span> | `Diagnostic` type, codes registry, result integration (S05) |
| `Engine.Observability` | profiler dropped | <span class="hg-status planned">missing</span> | Spans, counters, ring buffer, export (S04) |
| `Engine.Crash` | none | <span class="hg-status planned">missing</span> | Out-of-process dump handler, crash IDs (S06) |
| `Engine.Memory` | allocators scattered (`pmr` arenas in render commands) | <span class="hg-status planned">missing</span> | Tracked allocators, budgets, per-subsystem arenas (S08) |
| `Engine.Reflect` (+`.Utils`) | 27 files, 2.2k lines | <span class="hg-status design">partial</span> | Stable type identity across reloads, attributes, functions (S09) |
| `Engine.Config`, `Engine.Env`, `Engine.Platform` | small | <span class="hg-status design">partial</span> | Process role selection, capability flags (S58) |
| `Engine.Crypto` | CRC32 only | <span class="hg-status design">partial</span> | SHA-256 / BLAKE3 for content addressing, TLS via a vetted library (S41, S55) |
| `Engine.Filesystem` | Path/Url, pulls `<filesystem>` into 253 TUs | <span class="hg-status design">partial</span> | Header diet (build-speed issue #75); file watcher (S49) |

## Scheduling and IO

| Target bundle | Today | State | Work |
|---------------|-------|-------|------|
| `Engine.Scheduler` | 52 files, 5.0k lines; fibers, workers, tick stages; polled waits | <span class="hg-status design">partial</span> | Waitables, task graph with dependencies, priorities, deterministic mode (S02) |
| `Engine.Async` | promises, ring buffer, spin lock | <span class="hg-status design">partial</span> | Rebuild on waitables; `SpinLock` bug noted in test notes |
| `Engine.IO.Dispatcher` | 2 files | <span class="hg-status design">partial</span> | IO thread pool with IOCP / DirectStorage completion into waitables (S03) |
| `Engine.Storage.*` (6 bundles) | registries, actions, packages; synchronous | <span class="hg-status design">partial</span> | Async request path, resolved-stack reuse, content addressing (S03, S41) |
| `Engine.Resource.*` (8 bundles) | load/store pipelines, archives, packages; `Import`, `Load`, `Save` are stubs (9 to 82 lines) | <span class="hg-status design">partial</span> | Residency and budgets, priorities, cancellation (S03, S17) |
| `Engine.Assets.*` (3 bundles) | registry, typed assets | <span class="hg-status design">partial</span> | Tags, references, index feed for search (S46); remove reach-into of GFX/Reflow/SFX (layer rule) |
| `Engine.Serialization.*` (3 bundles) | 81 files, 5.2k lines; structured and layout serialisers; no versions | <span class="hg-status design">partial</span> | Schema versions, skippable records, checksums, text form (S01) |

## Simulation and world

| Target bundle | Today | State | Work |
|---------------|-------|-------|------|
| `Engine.ACS` (+`.Schedule`) | 3.9k lines; sealed archetypes in PR #81 | <span class="hg-status design">partial</span> | Finish #80 leftovers: compaction, unified traversal, streaming cell as handle space (S40) |
| `Engine.Scene.*` (6 bundles) | `SceneSystem` pattern, type-mapped registries | <span class="hg-status accepted">exists</span> | Add query services (bounds, height, wind) (S44, S27, S32) |
| `Engine.Level` | 296 lines; `Level` as handle space | <span class="hg-status closed">replace</span> | `Engine.World.Partition`: cells, streaming, persistence (S40) |
| `Engine.World.Terrain` | none | <span class="hg-status planned">missing</span> | Heightfield tiles, clipmap/CDLOD, materials, edits, layers, voxel overlay (S27, S28, S29) |
| `Engine.World.Ocean` | none | <span class="hg-status planned">missing</span> | Spectrum, FFT cascades, analytic authoritative height, buoyancy (S30) |
| `Engine.World.Weather` | none | <span class="hg-status planned">missing</span> | Weather state, wind field, precipitation; feeds sky/clouds (S32) |
| `Engine.World.Procedural` | none | <span class="hg-status planned">missing</span> | Graph-based generators, seeds, erosion, scatter (S33) |
| `Engine.Fluids` | none | <span class="hg-status planned">missing</span> | GPU grid/particle fluids and CPU proxies (S31) |
| `Engine.PFX`, `Engine.Physics.*` (3 bundles) | Jolt init, two shape models, schedule stage | <span class="hg-status design">partial</span> | Full Jolt surface, determinism, double precision, characters, vehicles, islands (S34); cloth (S35) |
| `Engine.Animation` | none (skeletal vertex path exists in `defined.skeletal.asl`) | <span class="hg-status planned">missing</span> | Clips, compression, blend graph, inertialisation, motion matching, IK, morphs (S36) |
| `Engine.Navigation` | none | <span class="hg-status planned">missing</span> | Tiled navmesh, crowds, volumes (S37) |
| `Engine.SFX` | importers only | <span class="hg-status design">partial</span> | Audio runtime per design (S38) |
| `Engine.Input` (+`.Schedule`, `Support.Input.Win32`) | events, drag-drop, Win32 backend | <span class="hg-status design">partial</span> | Contexts, actions, arbitration, recording (S39) |

## Rendering

| Target bundle | Today | State | Work |
|---------------|-------|-------|------|
| `Engine.Driver.Vulkan` | 1.9k lines | <span class="hg-status design">partial</span> | Bindless descriptors, timeline semaphores, multi-queue, pipeline library, null device (S14, S15, S58) |
| `Engine.Accel.Lang` | 56 files, 7.3k lines; ASL parser, IR, GLSL emitter (glslang-gated) | <span class="hg-status design">partial</span> | SPIR-V backend, optimiser passes, region borrows (#82) (S11) |
| `Engine.Accel.Compile`, `.Pipeline`, `.Pass`, `.Command`, `.Storage`, `.Loader`, `.Effect` | graphics pipelines only | <span class="hg-status design">partial</span> | Compute, mesh, ray-tracing, work-graph pipelines (#78) (S12); variant cache (S13) |
| `Engine.GFX` | 183 files, 18.7k lines | <span class="hg-status design">partial</span> | Trim to device and resource layer; split `vkinc.hpp` cost (#75) |
| `Engine.GFX.RenderGraph` (+`.Compile`) | 6.2k lines | <span class="hg-status design">partial</span> | Derived barriers, aliasing, async compute (S14) |
| `Engine.GFX.Render.*` (5 bundles) | hand-wired passes (`DepthPrePass`, `MatTestPass`, `PostProcessPass`, ...) | <span class="hg-status closed">replace</span> | Declarative passes on the GPU-driven scene (S15) |
| `Engine.GFX.Scene` (+`.Model`), `Engine.Render.Scene*` | CPU-side scene mirror | <span class="hg-status design">partial</span> | GPU-resident instance/material/geometry tables (S15) |
| `Engine.GFX.Material` | prototypes, effects, parameter storage | <span class="hg-status design">partial</span> | Layered materials, emissive, requirement back-propagation (S16) |
| `Engine.GFX.Geometry` | 46 lines | <span class="hg-status planned">missing</span> | Cluster DAG, meshlets, pages (S18) |
| `Engine.GFX.Texture.Virtual` | sparse cube-map code exists (#42) | <span class="hg-status planned">missing</span> | Page tables, feedback, residency (S17) |
| `Engine.GFX.Shadow`, `.GI`, `.Volumetric`, `.Transparency`, `.Post`, `.Particles`, `.Foliage` | none (shadow and post shaders exist as assets) | <span class="hg-status planned">missing</span> | S19 to S25 |
| `Engine.GFX.Glow` | 796 lines, purpose unclear | <span class="hg-status design">partial</span> | Audit; fold into post or remove |

## UI and editor

| Target bundle | Today | State | Work |
|---------------|-------|-------|------|
| `Engine.Reflow` (+`.Attributes`, `.Schedule`, `.Theming`, `.Render`) | 8.7k + 1.2k lines | <span class="hg-status design">partial</span> | Canvas backend, invalidation (#39, #43), text service (S42); drop `GFX` dependency behind the canvas interface |
| `Engine.Reflow.Uikit` | 4.0k lines, atoms and layouts; molecules and organisms are forward declarations only | <span class="hg-status design">partial</span> | Full widget set (#27 to #36), lists, trees, docking, animation (S43) |
| `Engine.Canvas` | none | <span class="hg-status planned">missing</span> | SDF/MSDF compute renderer, path rasteriser, text shaping (S42) |
| `Engine.Localization` | none | <span class="hg-status planned">missing</span> | ICU, string tables, pseudo-locale (S52) |
| `Editor.Action` (+`.Assets.Actions`, `.Scene.Actions`) | 1.4k lines, action log, delegate and import actions | <span class="hg-status design">partial</span> | Transactions, multi-object, asset edits, replay (S45) |
| `Editor.UI*` (9 bundles) | panels, services, views, theme | <span class="hg-status design">partial</span> | Rebuilt on uikit; picking and gizmos (S44) |
| `Editor.GFX.Graphs` | 82 files, 2.1k lines of node definitions, no compiler | <span class="hg-status design">partial</span> | Graph IR to ASL / C++ emitters (S47) |
| `Editor.Search` | none | <span class="hg-status planned">missing</span> | Asset index and query (S46) |
| `Editor.Automation` | none | <span class="hg-status planned">missing</span> | Replay driver, fixtures, profile capture (S54) |
| `Editor.Livelink` | none | <span class="hg-status planned">missing</span> | DCC bridges, watcher-driven reimport (S49) |
| `Editor.VCS` | none | <span class="hg-status planned">missing</span> | Git/LFS provider, locks, diff (S51) |
| `Engine.Plugin` | none | <span class="hg-status planned">missing</span> | Descriptor, load phases, C-ABI table (S50) |
| `Engine.HotReload` | none | <span class="hg-status planned">missing</span> | Module swap with reflection-driven state migration (S48) |

## Network and scale

| Target bundle | Today | State | Work |
|---------------|-------|-------|------|
| `Engine.Network` | 48 lines | <span class="hg-status planned">missing</span> | Transport: sockets, QUIC/HTTP3, HTTP/2, TLS, custom UDP (S55) |
| `Engine.Replication` | none | <span class="hg-status planned">missing</span> | Snapshots, interest, authority (S56) |
| `Engine.Cluster` | none | <span class="hg-status planned">missing</span> | Mesh membership, handover, persistence adapters (S57) |
| `Engine.Replay` | none | <span class="hg-status planned">missing</span> | Deterministic record and replay (S59) |
| `Engine.Jit` | none | <span class="hg-status planned">missing</span> | Deferred; measured gate first (S60) |

## Build and process

| Target | Today | State | Work |
|--------|-------|-------|------|
| Game-project build (`Heliogrim-Project-Template` exists beside the engine) | CMake globbed bundles, editor target | <span class="hg-status design">partial</span> | Project descriptor, cook, package, sign, SDK export (S53) |
| Test bundles | 28 test executables, ~600 tests (test notes, 2026-10) | <span class="hg-status design">partial</span> | GPU harness, workflow tests, fuzzing, sanitizers in CI (S61, S62) |
| CI | GitHub migration open (#38) | <span class="hg-status planned">missing</span> | Build, test, analysis and performance gates (S62) |
| Documentation | this site; `clang-doc` spike open ([code documentation](../architecture/code-documentation.md)) | <span class="hg-status design">partial</span> | Reference generation, system pages per shipped system (S64) |

## Layer violations to remove

From the generated module map (commit `c50d343`, re-checked by bundle name on 2026-11-07):

- `Engine.Assets.Type` includes `GFX`, `GFX.Material`, `Reflow`, `SFX`, `Level`: typed assets should be data plus serialisation; system-specific resource creation moves to the owning system's loader.
- `Engine.Reflow` includes `GFX`, `GFX.Scene`, `Render.Scene`: the UI must draw through a canvas interface implemented by the renderer.
- `Engine.Serialization` and `Engine.Scene.Game` include `Heliogrim`: a service layer must not include the public surface above it.
- `Engine.Input` includes `Support.Input.Win32` directly: backends should register through `Engine.Platform`.
- `Engine.Core` includes `ACS`, `Level`, `Scene`: core becomes orchestration only; the world bundle owns level and scene lifetime.

Each move is a refactor issue of its own, scheduled with the system that benefits (see [systems](systems.md)).
