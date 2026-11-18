# Vision

**Status**: <span class="hg-status summary">plan</span>. The owner's target list (2026-11-07), refined into checkable outcomes and extended where a target implies another. Nothing here is a decision; each target points at the systems that deliver it.

## The engine in one paragraph

Heliogrim is a general-purpose engine and editor for games that are large, dense and alive: open worlds up to a single-shard MMO, photoreal or stylised, with weather, oceans, deformable multi-level terrain and crowds, built by teams that write C++ and expect the tools to keep up with them. The quality target is that of a high-end, next-generation single-player game (models, textures, simulation and gameplay), delivered while the same world runs as an MMO (owner, 2026-11-18). The engine is written in the project; third parties supply platform access (Vulkan, OS), a few proven algorithms (ankerl, Jolt) and standard codecs (PNG, KTX, FLAC, Ogg, glTF/FBX). Quality is the product: a failure anywhere returns a diagnostic that names the fix.

## Acceptance bars

Each target below has an outcome a reviewer can check. "Systems" refers to the [catalog](systems.md).

### Foundation and quality

| Target | Outcome that counts as reached | Systems |
|--------|-------------------------------|---------|
| Enterprise/military grade design and code | A written standard (subset of C++ Core Guidelines, MISRA C++:2023 where it applies) enforced by clang-tidy in CI; sanitizers and static analysis gate every PR; every public type has a contract comment and a test; no `todo_panic` on a shipped path | S61, S62, S63, S64 |
| Extremely good diagnostics with fix information | One error model engine-wide: code, message, source span or asset path, notes, suggested fix; the editor renders them with a "fix" action where one exists; diagnostics are tested like code | S05 |
| Good crash handlers | A crash on any thread or fiber writes a minidump with fiber stacks, a stable crash ID and the last log ring; symbolised offline; reproduced in a test | S06 |
| Highly parallel fiber execution | Game loop and engine systems run as tasks with declared dependencies on a fiber scheduler; blocking work (IO, platform pump, audio device) lives on dedicated threads with explicit bridges; no worker blocks on a fiber wait | S02 |
| Flawless streaming from disk, memory, cache | Asset loads never stall the game loop; residency is budgeted and observable; a cold load of a 10 km² test world shows no hitch above the frame budget | S03, S17, S40 |
| Test suite for engine, editor and workflows | Unit, module, scene and editor-workflow fixtures; GPU golden-image tests in CI; workflow tests drive the editor through its action API | S61 |
| Headless mode | One binary runs as client, editor, dedicated server, worker or cluster node, selected by configuration; servers run with a null render device | S58 |
| Automated optimisation / JIT | Shader variants are specialised and cached automatically; hot CPU paths can be specialised at runtime behind a measured gate | S13, S60 |

### Shading and rendering

| Target | Outcome | Systems |
|--------|---------|---------|
| Custom shader language and IR (ASL) | Every shader in the engine is ASL; the IR targets SPIR-V directly for graphics, compute, mesh, ray-tracing and work-graph stages; optimiser passes and interface checks run without a GPU | S11, S12 |
| Next-gen photoreal and fantasy graphics | Layered PBR materials, emissive surfaces that light the scene, multi-bounce GI with reflections, sharp shadows, volumetric sky and fog, HDR output with filmic or ACES/AgX tone mapping; a stylised look is a material and post stack, not a different renderer | S16, S19, S20, S21, S23 |
| Real-time rendering | A GPU-driven pipeline (visibility buffer, meshlet culling, indirect draws) holds a frame budget set per project on a stated hardware baseline | S14, S15 |
| Massive geometry (micropolygon) | Cluster-DAG geometry with software and mesh-shader rasterisation; scenes with hundreds of millions of source triangles stream and render at pixel-sized detail | S18 |
| Transparency and semi-transparency | Order-independent transparency for glass, water, smoke; refraction; correct with fog, GI and shadows | S22 |
| Volumetric weather | Sky, atmosphere, clouds and fog from one physically based model driven by a weather state that changes over time and space | S21, S32 |
| Volumetric fluids | Real-time grid or particle fluids for local effects, with a cheap deterministic proxy for gameplay | S31 |
| Particles at Niagara scale | GPU-simulated emitters authored as graphs, with simulation stages, collisions, lighting and sorting | S24 |
| Foliage | Instanced and impostored at distance, aggregate or volumetric leaves near the camera, wind and LOD without popping | S25 |
| Video effects | Colour grading, HDR, bloom, depth of field, motion blur, temporal upscaling, blending modes, all in the same post graph | S23 |

### World and simulation

| Target | Outcome | Systems |
|--------|---------|---------|
| Big open world up to MMO | World partition cells stream actors and assets; double-precision world positions with camera-relative rendering; a single shard scales out across server nodes with seamless handover | S07, S40, S57 |
| Live terrain deformation and editing | Terrain edits in editor and at runtime apply to the GPU heightfield, physics and navigation within one frame | S28 |
| Multi-y-level terrain | Layered heightfields plus voxel volumes for caves and overhangs, authored and streamed per cell | S28 |
| Multi-y-level bounded effects | Weather, audio, lighting and physics regions bound to a terrain layer or volume, not to a global height | S29 |
| Massive ocean | FFT ocean with cascades, shoreline and buoyancy, CPU-evaluable deterministic height for server-side sailing | S30 |
| Convincing fluid dynamics | See volumetric fluids; plus water-surface interaction with the ocean and rivers | S31 |
| Procedural generation | Deterministic, seed-driven graph-based generation (terrain, scatter, roads, structures) usable offline and at runtime | S33 |
| Physics quality and precision | Jolt integrated fully: shapes, constraints, characters, vehicles, deterministic mode, large-world precision; server simulation islands | S34 |
| Cloth | XPBD cloth with character collision and LOD | S35 |
| Animation with morphing and DCC integration | Skeletal pipeline with compression, blend graphs, inertialised transitions, motion matching, morph targets, IK and retargeting; imports from Blender, Maya, 3ds Max | S36, S49 |
| Navigation at MMO scale | Tiled, streamed, hierarchical navmesh; crowds; volumes for flying agents; multi-level terrain aware; cheap enough for servers | S37 |
| Fully integrated sound engine | The audio runtime [design](../architecture/audio-runtime-design.md) built, integrated with game events and the editor | S38 |
| Dynamic weather | A simulation that drives S21, wind for foliage, precipitation for terrain and ocean | S32 |

### Editor and tooling

| Target | Outcome | Systems |
|--------|---------|---------|
| Input system across UI, editor, game, asset augmentation | Contexts, actions, modifiers and triggers; one arbitration model for UI, editor tools and gameplay; recording and replay | S39 |
| Vectorised UI rendering | SDF/MSDF canvas with text shaping; all widgets drawn through it; animations without geometry rebuilds | S42 |
| Uikit for whole applications | A complete, themed, accessible widget set with layout, lists, trees, docking, dialogs, menus | S43 |
| Editor action workflows with undo/redo | Every edit is a transaction; multi-object and asset edits undo together; the action log drives test replay | S45 |
| Editor asset search engine | Indexed search over assets with tags, types, references and full text; incremental on file change | S46 |
| Visual coding that emits C++ | Graphs compile to readable C++ with source maps, built like hand-written code | S47 |
| HMR for C++ game development | Game modules reload in the editor and in a running game with state preserved | S48 |
| Real-time content-tool integration | Save in Blender/Maya/Max refreshes the asset in the engine within seconds; live link for transforms and animation | S49 |
| Plugins for editor and engine | Versioned plugin interface, load phases, discovery, a sample plugin in the repository | S50 |
| VCS integration | Status, diff, lock and commit from the editor; VCS-friendly asset formats | S51 |
| Localisation | ICU-based message formatting, plural rules, string tables, pseudo-localisation, font fallback | S52 |
| Game-project build system | A project folder builds to a shippable, signed artifact per platform with cooked content | S53 |
| In-editor test automation | Replay recorded sessions, capture profiles, fixtures at unit, scene and workflow scope, from the editor | S54 |

### Scale

| Target | Outcome | Systems |
|--------|---------|---------|
| Comprehensive networking | HTTPS, HTTP/2 and HTTP/3 clients and servers; a custom reliable-unreliable UDP protocol with encryption for real-time state | S55 |
| Replication | Snapshots with delta compression, interest management, authority transfer | S56 |
| MMO server | Spatial server mesh with persistence and handover | S57 |
| Determinism and replay | Deterministic simulation mode; recorded replays usable for tests and for netcode debugging | S59 |

## Extensions the targets imply

Targets the brief does not list but the listed ones cannot be reached without:

- **Reflection v2** (S09): hot reload, serialisation, visual scripting, property panels and the asset search all need one reflection model with stable type identities across module reloads.
- **Memory model** (S08): streaming, GPU-driven rendering and headless servers need per-subsystem budgets and tracked allocators.
- **World partition** (S40): streaming, MMO and terrain all need a cell structure that replaces `Level` as the actor handle space (left for later in the archetype design).
- **Shader variant and pipeline cache** (S13): the material system, GI and micropolygon pipelines multiply permutations; without a managed cache the first frame of every scene stalls.
- **Documentation system** (S64): enterprise grade is not reached if the reference lives in people's heads.

## Non-goals for now

- Consoles and mobile. Windows desktop first, Linux server second. Vulkan only.
- C# or another managed scripting runtime. Visual scripting emits C++ ([exploration](../architecture/scripting-native-codegen-exploration.md)); a managed runtime stays a separate decision.
- A non-code render-graph editor for end users. The default pipeline is composed in code.
- Economy, NPC behaviour and other game-layer systems above the engine.
