# Gap Analysis: Engine Against the Targets

**Status**: <span class="hg-status summary">plan</span>. Per target: what the engine has, what is missing, and how far away it is. Checked against the source on 2026-11-07 (bundle file lists and sizes, the test notes from 2026-10, and the explorations on this site). The earlier [documentation gap analysis](../architecture/gap-analysis.md) covers this site; this page covers the code.

Distance: **near** a bounded change on existing code · **mid** a new subsystem on existing foundations · **far** new subsystem plus foundation changes · **research** the approach itself must be chosen by measurement first.

## Foundation and quality

| Target | Has | Missing | Distance |
|--------|-----|---------|----------|
| Enterprise-grade code | `STYLE.md`, clang-format, ReSharper rules, 28 test executables, review workflow (issue = spec) | A written coding standard with tooling (clang-tidy profile), sanitizer and static-analysis gates, CI at all (#38 open), contract comments on public types, removal of `todo_panic` paths (storage async, `RegisterActorClass` before #81) and the 25 logged production bugs | mid |
| Diagnostics with fix info | `Engine.Accel.Lang/Ir/Diagnostic.hpp` (ASL compiler), `Result` type in Common, logging | An engine-wide `Diagnostic` type with codes and fixes; adoption by importers, storage, serialisation, editor | mid |
| Crash handlers | none | Out-of-process minidump handler, fiber-aware stacks, crash IDs, symbol store | mid |
| Fiber parallelism | `Engine.Scheduler` fibers, workers, tick stages, `FiberAwaitable` as a flag; `IO.Dispatcher` stub | Waitables, task dependencies, priorities, IO/platform bridges, deterministic mode ([exploration](../architecture/fiber-scheduler-exploration.md)) | mid |
| Flawless streaming | Storage registries, archives, packages, resource load/store pipelines, sparse textures for cube maps | Async request path (all sync today), residency budgets, priorities, cancellation, Windows batching backend, page-level streaming for textures and geometry | far |
| Test suite | ~600 unit tests, `Performance.Test`, GPU harness design approved but not built | GPU golden tests, scene fixtures, editor workflow tests, fuzzing of loaders, test runs in CI | mid |
| Headless mode | `Heliogrim.Main` and `Editor.Main` entries; `GameEngine` | Role selection, null render device, capability flags, server loop without window | mid |
| JIT / automated optimisation | none | Variant cache first; CPU JIT deferred | research |

## Shading and rendering

| Target | Has | Missing | Distance |
|--------|-----|---------|----------|
| ASL language and IR | Parser, IR (module, layout, lower, merge, resolve, slice, variant, analysis), GLSL emitter gated by glslang, all engine shaders in `.asl` (milestone 2 on `feat/accel-ir-coverage`), `Dialect.hpp` | Direct SPIR-V backend, optimiser passes, region borrows (#82), uniformity analysis, debug info, compile-time interface contracts enforced against passes | mid |
| All pipeline kinds | `Accel.Pipeline` graphics only; IR supports compute stage | Compute, mesh, ray-tracing and work-graph pipelines through `Accel.Compile` and the driver (#78) | mid |
| Photoreal materials and lighting | PBR BRDF shaders (`lighting.brdf.asl`, `pbr.asl`), IBL generation (`brdfLut`, `brdfIrrad`, `brdfPref`), G-buffer pass, directional shadow pass, sky pass, material prototypes and parameter storage | Layered materials, emissive feeding GI, GI itself, VSM, volumetrics, HDR output, post stack beyond a tonemap | far |
| Real-time GPU-driven rendering | Render graph with compile step, command translation to Vulkan, scene mirror with models | Bindless descriptors, GPU instance tables, indirect draws, meshlet culling, visibility buffer, derived barriers, aliasing, async compute | far |
| Micropolygon geometry | `Engine.GFX.Geometry` (46 lines), static geometry asset structure | Everything: cluster DAG build, pages, streaming, software rasteriser, mesh-shader path, material resolve from visibility buffer | far |
| Transparency | blend state in pipelines | OIT, refraction, fog/GI interaction | mid (after S15) |
| Volumetric weather | sky shader | Atmosphere LUTs, froxel fog, clouds, weather state | far |
| Volumetric fluids | none | GPU grid or particle fluids, surface extraction, CPU proxy | research |
| Particles (Niagara scale) | none | GPU emitters, graph authoring, stages, collisions, sorting | far |
| Foliage | none | Instancing, impostors, wind, near-camera aggregates | far |
| Video effects | `PostProcessPass`, `tonemap.asl` | Grading LUTs, bloom, DoF, motion blur, HDR swapchain, temporal upscaling | mid |
| Animation morphing | none | Morph targets, inertialisation, blend graph | far (part of S36) |
| Cloth | none | XPBD cloth, collision, LOD | far |

## World and simulation

| Target | Has | Missing | Distance |
|--------|-----|---------|----------|
| Open world, MMO | `Level` (296 lines), sealed archetypes per level (PR #81), float transforms | World partition cells, streaming, double world positions, camera-relative render, server mesh, handover, persistence | far |
| Live terrain deformation | none | Terrain itself first | far |
| Multi-y-level terrain | none | Layered heightfields, voxel overlay | far |
| Multi-y-level bounded effects | none | Volumes bound to layers; region queries | mid (after terrain) |
| Massive ocean | none | Spectrum, FFT cascades, analytic authoritative height, buoyancy, shore | far |
| Fluid dynamics | none | see volumetric fluids | research |
| Procedural generation | none | Graph generators, deterministic seeds, erosion, scatter | far |
| Physics quality | Jolt vendored (shared build, determinism off), `PhysicsSceneSystem`, box and sphere models, schedule stage | Full shape and constraint surface, characters, vehicles, deterministic build decision, double precision decision, job-system bridge to fibers, server islands | mid |
| Animation + DCC | assimp import (`Editor.GFX.Loader`), skeletal vertex shader | Runtime animation system, compression, blend, IK, retargeting, morphs, glTF/USD pipeline, live link | far |
| Navigation | none | Recast/Detour-class navmesh with tiles, crowds, volumes | far |
| Sound engine | importers; [runtime design](../architecture/audio-runtime-design.md) drafted | Runtime, device backend, DSP graph, scene system, game-event integration, editor UI | mid |
| Dynamic weather | none | State simulation, wind field, precipitation | mid (after volumetrics) |

## Editor and tooling

| Target | Has | Missing | Distance |
|--------|-----|---------|----------|
| Input across UI, editor, game | Event classes, drag-drop, Win32 backend, input service in editor | Contexts, actions, modifiers, arbitration, recording, gamepad | mid |
| Vectorised UI | Reflow layout and widgets, bitmap-font text as CPU geometry, issues #11 to #17 for SDF primitives | Canvas renderer (SDF/MSDF compute or instanced quads), text shaping, animation | far |
| Uikit | Atoms and layouts (4k lines); molecules and organisms declared only | Inputs (#27 to #36), lists, trees, docking, dialogs, accessibility tree | mid |
| Undo/redo workflows | `ActionManager`, `ActionLog`, delegate and import actions; `reapply` broken | Transactions, coalescing, multi-object, asset edits, replay from the log | mid |
| Asset search engine | `AssetRegistry` with GUID and type lookups | Index, tags, references, full text, query language, watcher | mid |
| Visual coding to C++ | `Editor.GFX.Graphs` node definitions (82 files), no compiler; [exploration](../architecture/scripting-native-codegen-exploration.md) | Graph IR, type checker, C++ and ASL emitters, build integration, debugging source maps | far |
| HMR for C++ | none; build flags not set for patching | Module boundaries, reflection-driven state migration, build integration | far |
| DCC live link | assimp import | glTF 2.0 importer, watcher, GUID-preserving reimport, Blender add-on, transform/animation live link | mid |
| Plugins | none | Descriptor, discovery, load phases, C-ABI boundary | mid |
| VCS integration | none; [serializer exploration](../architecture/serialization-evolution-exploration.md) proposes text manifests | Provider API, Git/LFS, locking, status in the editor | mid |
| Localisation | none | ICU, string tables, gather/compile tooling, pseudo-locale, font fallback | mid |
| Game-project build system | `Heliogrim-Project-Template` beside the engine, CMake macros | Project descriptor, cook, package, sign, SDK export, platform presets | mid |
| In-editor test automation | none | Replay driver on the action log and input recording, fixtures, profile capture | mid (after S45, S39) |

## Scale

| Target | Has | Missing | Distance |
|--------|-----|---------|----------|
| Networking (HTTPS, HTTP/2, HTTP/3, custom) | `Engine.Network` 48 lines, `Engine.Crypto` CRC32 | Everything; TLS and QUIC need a vetted library (the brief allows platform integration vendors) | far |
| Replication | none | Snapshots, deltas, interest, authority | far |
| MMO server | none | Spatial mesh, handover, persistence | research |
| Determinism and replay | none | Deterministic scheduler mode, strict FP build, replay format | mid (after S02) |

## Cross-cutting findings

1. **Three foundations block most targets**: the scheduler (S02), async storage (S03) and serialisation versioning (S01). Nothing in the world, rendering or scale tracks reaches "flawless" without them. They are also the smallest items on this page.
2. **The rendering track has a solid base in ASL and the render graph** but no GPU-driven scene. S14 and S15 are the pivot: micropolygons, VSM, GI, particles and foliage all assume them.
3. **World systems are all missing** and all need the partition (S40) and double coordinates (S07) first. Terrain, ocean and weather also share a wind field and a height query service; build those as services, not inside one system.
4. **Editor targets are mid-distance** because Reflow, actions and the asset registry exist. The canvas (S42) is the one far item and gates the rest of the editor's polish.
5. **Scale targets are the furthest** and the least researched. Transport and replication can start after S02; the server mesh is research until a prototype measures handover.
6. **Quality is the cheapest lever**: a coding standard, CI gates and the GPU harness are mid-distance and make every other item safer.
