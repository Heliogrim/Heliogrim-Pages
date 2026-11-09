# Research: physics, animation, navigation, DCC, input

**Status**: <span class="hg-status summary">sources</span>. Collected 2026-11-07 by a research agent for the battle plan. Claims are marked verified or unverified; nothing here is a decision.

**Method note**: First pass (2026-11-07): Jolt docs, ACL README, Recast README, UE Enhanced Input docs, UE Interchange landing page, SDL3 events page, Unity Input System landing page were fetched. Second pass (same day, see "Verification pass" at the end): bibliographic data of most papers/talks checked via ACM DL / Springer / ScienceDirect / GDC Vault / author-site search results and fetched pages. Status words: `verified (full text)` = page body read; `verified (abstract/landing page)` = title/authors/venue/year/abstract confirmed, body not read; `unverified` = not confirmed, reason given. A search-result snippet of a primary page counts as landing-page level only. No blog/forum claims used for facts, except where marked as context.

---

## 1. Rigid-body physics: quality, precision, determinism, scale

- Jolt solves with a Sequential Impulse solver with warm starting (Catto lineage), velocity constraints iterated per island, then a position solver for drift; large islands split (LargeIslandSplitter) for parallel solve; soft bodies use XPBD; symplectic Euler integrator. `verified` (Jolt docs).
- Islands = dynamic bodies connected by contact/constraint; whole island sleeps when at rest; removing a body does not wake neighbours; sleep tuned by `mTimeBeforeSleep`, `mPointVelocitySleepThreshold`. `verified`.
- Continuous collision: default Discrete; `LinearCast` does extra CastShape and "time-steals" (moves back to hit point, waits next step); fast-rotating long objects can still miss since rotation is applied fully before the cast. `verified`.
- Determinism: same binary + same call order => deterministic. Cross-platform needs CMake `CROSS_PLATFORM_DETERMINISTIC` (~8% slower; docs say holds across MSVC/clang/gcc/emscripten, x86/ARM/RISC-V/etc.). App code must avoid `std::sort`, `std::hash`, `std::push_heap`, std trig; set precise FP mode, no FP contraction. Docs note cross-platform is less tested. Broadphase queries are NOT deterministic. `verified`.
- Large worlds: float build accurate to ~5 km from origin; `JPH_DOUBLE_PRECISION` stores positions as doubles (5-10% slower); queries take a base offset; broadphase stays float (resolution ~1 m at 10,000 km, perf not quality loss). Velocities/rotations are floats. Serialized shape format depends on `JPH_DOUBLE_PRECISION`. `verified`.
- Bodies/constraints cannot be shared between PhysicsSystems (only Shapes); Factory/allocators global. `RestoreState` fails if bodies added/removed between snapshots. `verified`.
- Thread model: `PhysicsSystem::Update` fans out via a JobSystem; callbacks fire from multiple threads in non-deterministic order. `verified`. (Fits a fiber scheduler only through a custom JobSystem adapter; adapter design not researched.)
- Solver literature (XPBD, Small Steps, Rouwe GDC 2022 now `verified (abstract/landing page)`, see Verification pass; the rest `unverified`, open before citing): Catto "Iterative Dynamics with Temporal Coherence" GDC 2005 and "Solver2D / Soft Step" (Box2D v3 blog by Catto, 2024; blog only, treat as secondary); Macklin, Müller, Chentanez "XPBD: Position-Based Simulation of Compliant Constrained Dynamics", MIG 2016 (PDF `matthias-research.github.io/pages/publications/XPBD.pdf`, fetched but binary); Macklin et al. "Small Steps in Physics Simulation", SCA 2019 (substepping beats iterations); Stewart/Trinkle and Anitescu LCP/TGS background; Rouwe, "Architecting Jolt Physics for Horizon Forbidden West", GDC 2022 (slides/video).
- Reference engines (`unverified`): PhysX 5 (NVIDIA docs; TGS solver, GPU rigid bodies, BSD-3), Havok (proprietary, deterministic option, Havok docs).
- MMO-scale (`unverified`, no primary source collected): common approach is one PhysicsSystem per zone/shard with server authority, islands/sleeping to keep cost proportional to active bodies, and snapshot/rollback via determinism (Jolt `SaveState`). Needs a GDC/Eurographics source before relying on it.

**Applicability to Heliogrim**
- Jolt is already vendored; its docs confirm double-precision and determinism flags, both compile-time and global (ABI-affecting). Decide once, early: `JPH_DOUBLE_PRECISION` for MMO-scale worlds vs. per-region origin rebasing with float.
- Cross-platform determinism only matters if lockstep/rollback or client-side prediction replay is planned; otherwise server-authoritative state sync makes it optional.
- One PhysicsSystem per world shard/region maps onto the "no shared bodies" constraint; cross-shard interaction must be explicit.
- Job system adapter onto the fiber scheduler is the main integration surface.
- Soft bodies in Jolt (XPBD) are a possible cloth fallback (see section 2).

**Risks / measure**
- Cost of double precision and CROSS_PLATFORM_DETERMINISTIC on Heliogrim scenes (docs say 5-10% / ~8%, confirmed as docs statements; still measure on Heliogrim scenes).
- Fiber JobSystem overhead vs Jolt's own pool; callback thread-safety against ACS.
- Body count and island-size distribution in MMO-style crowds; sleep behaviour with streaming.
- Origin rebasing interaction with streaming and navmesh tiles.

---

## 2. Cloth and soft bodies

Items are `unverified` unless noted (see Verification pass for the upgraded ones).
- Müller, Heidelberger, Hennix, Ratcliff, "Position Based Dynamics": author page lists it as VRIPhys 2006 (PDF posBasedDyn.pdf); the earlier "J. Visual Communication and Image Representation 2007" attribution is journal-version metadata not confirmed here. `verified (abstract/landing page)` for authors/title/VRIPhys 2006.
- Macklin et al. XPBD 2016 (see sec. 1): abstract opens "We address the long-standing problem of iteration count and time step dependent constraint stiffness in position-based dynamics (PBD)". `verified (abstract/landing page)`.
- Macklin, Müller, Chentanez, Kim, "Unified Particle Physics for Real-Time Applications", ACM TOG 33(4), 153, 2014 (SIGGRAPH 2014; FleX). `verified (abstract/landing page)`.
- Strain limiting: Provot "Deformation constraints in a mass-spring model", 1995; Thomaszewski et al. "Continuum-based strain limiting", Eurographics 2009.
- Shipped engines: UE Chaos Cloth (Epic docs, dev.epicgames.com; XPBD-based, since UE5), NvCloth (NVIDIA, GitHub NVIDIAGameWorks/NvCloth, GPU DX11 solver, deprecated-ish). Check current maintenance status before reuse.
- Collision with characters: capsule/sphere proxies approximating the skeleton are the usual approach; self-collision is the expensive part. LOD: reduce solver iterations/particle count, bake to skinning beyond distance.
- Jolt soft bodies (XPBD, `verified` mention in docs) support vertex/edge/volume constraints and collision; cloth quality vs a dedicated solver not measured.

**Applicability**
- Option A: reuse Jolt soft bodies (no new dependency, shares collision world, CPU). Option B: own XPBD solver on GPU (Vulkan compute; fits GFX stack, complex). Option C: Chaos/NvCloth-like external (licence/maintenance risk).
- Cloth belongs in the animation pipeline as a post-skinning pass; needs a bone-driven collider set.
- LOD tiers: full sim near, simplified sim mid, baked/vertex-skinned far.

**Risks / measure**
- Jolt soft body cost per instance and character-collider fidelity; max cloth count per frame at MMO crowd density.
- GPU readback/latency if cloth results feed gameplay (should not).
- Determinism: GPU cloth is non-deterministic; keep out of server logic.

---

## 3. Animation systems

- ACL (Animation Compression Library, N. Frechette, MIT): C++11 header-only; priorities in order: minimize artifacts, fast decompression, small memory; allocator/assert hooks; CI on Windows VS2022/2026 x86/x64/ARM64, Linux GCC14+/Clang22+, macOS, WASM; UE plugin bundled with the engine (README, re-fetched: "distributed with a more recent version as part of each engine release since UE 5.13"; the number is as printed in the README, not cross-checked against Epic release notes). Perf docs are `docs/{cmu,paragon,fight_scene,decompression}_performance.md` (numbers in Verification pass). `verified (full text)` (README and perf docs).
- Motion matching: Clavet, "Motion Matching and The Road to Next-Gen Animation", GDC 2016 (Ubisoft Montreal, For Honor) `verified (abstract/landing page)`; Büttner, "Machine Learning for Motion Synthesis and Character Control (in Games)" is an I3D 2019 keynote, NOT GDC 2019 (corrected); Holden, Kanoun, Perepichka, Popa, "Learned Motion Matching", ACM TOG 39(4) / SIGGRAPH 2020: abstract states final model needs no animation data or matching metadata in memory (`verified (abstract/landing page)`; "trades memory for compute" is the agent's reading, not an abstract quote).
- Inertialization: D. Bollo, "Inertialization: High-Performance Animation Transitions in 'Gears of War'", GDC 2018 (The Coalition) `verified (abstract/landing page)`: transitions as a post-process, no need to evaluate source and target states during a transition. Earlier SIGGRAPH 2017 talk "High Performance Animation in Gears of War 4" exists. Offset-decay detail (spring/polynomial) `unverified`.
- Blend trees / state machines remain the baseline for gameplay-driven animation; motion matching is data-heavy (large mocap database, tagging, pose/trajectory features) and harder to author-debug. `unverified` (general knowledge).
- Morph targets / blendshapes: GPU-applied sparse deltas (compute or vertex fetch); corrective shapes driven by joint angles (pose-space deformation, Lewis, Cordner, Fong, SIGGRAPH 2000, pp. 165-172 `verified (abstract/landing page)`; RBF PSD variants `unverified`).
- IK: two-bone analytic; FABRIK (Aristidou & Lasenby, Graphical Models 73(5), 2011, pp. 243-260 `verified (abstract/landing page)`); full-body IK (e.g., Unreal Control Rig/FBIK, docs) `unverified`.
- Retargeting: skeleton-to-skeleton mapping with rest-pose alignment (UE IK Retargeter docs; Unity Humanoid avatars). `unverified`.
- Skinning: LBS baseline; dual quaternion skinning, Kavan, Collins, Zara, O'Sullivan, "Skinning with Dual Quaternions", I3D 2007, pp. 39-46 (`verified (abstract/landing page)`: abstract says LBS "has some serious drawbacks that require artist intervention" and presents a GPU-friendly dual-quaternion algorithm). Candy-wrapper fix, extra cost and bulging claims `unverified` (not in abstract).

**Applicability**
- Adopt ACL for clip storage (MIT, header-only, allocator hooks match engine style) rather than own compression; measure on Heliogrim's own clips.
- Pipeline order suggestion for the plan: skeleton + clip playback + blend graph + inertialization first; motion matching later as an optional graph node over the same pose buffer.
- Inertialization pairs well with state machines and removes cross-fade double evaluation, important for MMO crowd cost.
- Morph/corrective shapes must be part of the asset format from day one (sparse delta storage) because DCC import (section 4) feeds it.
- Animation LOD (update rate, skeleton bone culling) is essential for MMO crowds; no source collected, must be measured.

**Risks / measure**
- Per-character animation CPU/GPU cost at crowd scale; ACL decompression cost per bone on target CPUs.
- Motion-matching database memory and mocap licensing/authoring pipeline.
- Root motion vs server-authoritative movement reconciliation.
- DQS vs LBS visual need per asset class.

---

## 4. DCC interchange and live-link

- UE Interchange: "file format agnostic, asynchronous, customizable, and can be used at runtime" with a customizable pipeline stack (Blueprint or Python). Landing page does not detail translators/factories/formats/reimport. `verified (abstract/landing page)`. Translators (format -> intermediary node graph), pipelines (orchestrate import; stack in Project Settings > Engine > Interchange; Blueprint/C++/Python), factories (assets from nodes), reimport remembers pipeline stack: `verified (full text)` on the "Importing Assets Using Interchange" page per search excerpt only, so treat as landing level.
- glTF 2.0: Khronos spec 2.0.1 (2021-10-11) `verified (full text)` for TOC-level coverage: skins (3.7.3), morph targets (3.7.2.2), animations (3.11, step/linear/slerp/cubic spline), PBR metallic-roughness (3.9.2); spec body does not list KHR_materials. Extension registry README (KhronosGroup/glTF extensions) lists ratified KHR_materials_*: anisotropy, clearcoat, dispersion, emissive_strength, ior, iridescence, sheen, specular, transmission, unlit, variants, volume; in progress: diffuse_transmission (RC), subsurface (draft); pbrSpecularGlossiness archived. `verified (full text)`.
- FBX: Autodesk FBX SDK is free but proprietary (not open source; EULA; forum-quoted commercial-use clause with a required attribution statement); Autodesk developer page: Windows, macOS, iOS, Linux. Exact current EULA text not read. `verified (abstract/landing page)`. ufbx: README says single-source-file FBX loader in portable C (compiles as C++), dual-licensed MIT or Unlicense (public domain), aims at feature parity with the FBX SDK, supports skinning and blend shapes. `verified (full text)` (README). assimp `unverified`.
- OpenUSD (repo `PixarAnimationStudios/OpenUSD`, confirmed correct): README describes USD as "an efficient, scalable system for authoring, reading, and streaming" time-sampled scene data; built/tested on Linux, macOS, Windows (x64, ARM64); licence file not read (a LICENSE.txt exists). `verified (abstract/landing page)`. Layered composition/Hydra/dependency footprint claims `unverified`.
- Blender: Python API (`bpy`); `bpy.app.handlers.save_post` runs "on saving a blend file (after)", one argument: the file being saved (`verified (full text)`, docs page); Blender also exports glTF natively (`unverified`). Live-link plugins (e.g., Omniverse Connectors, "Unreal Live Link for Blender") are vendor/third-party; `unverified`.
- Maya/3ds Max: C++ and Python plugin SDKs can push over local socket; USD support in both. `unverified`.
- "Save in tool = refresh in engine": simplest robust mechanism is file watching (Windows `ReadDirectoryChangesW`) on exported source files + debounce + background reimport via the asset pipeline, preserving asset GUID and user overrides. Sidecar import settings are needed for stable reimport. Design inference, not a sourced claim.

**Applicability**
- Primary format candidate glTF 2.0 (open, covers mesh/skin/morph/anim/PBR); FBX via ufbx or SDK as compat path; USD as later scene-level interchange.
- Import pipeline modelled on Interchange: translator (format -> neutral graph) / pipeline (settings, user-extensible) / factory (engine asset). Heliogrim already has asset GUID infrastructure; reimport must keep GUIDs.
- Live refresh via file watch needs incremental asset rebuild and hot swap of GPU resources and Jolt shapes.

**Risks / measure**
- FBX SDK licence/platform; assimp skinning/animation fidelity; USD dependency weight (build time, matches the compile-time concerns already traced).
- Reimport latency for large assets; partial-write files during DCC save (need debounce/stable-size check).
- Morph/skeleton changes breaking existing animation assets on reimport.

---

## 5. Navigation at scale

- Recast & Detour (M. Mononen, zlib licence): Recast voxelizes triangle meshes and builds navmesh (single or tiled); Detour is runtime pathfinding/queries; DetourTileCache provides streaming for "large levels and open-world games" and dynamic obstacles; DetourCrowd does agent movement/avoidance; README says it powers Unity, Unreal, Godot, O3DE; C++98-compatible, no dependencies. `verified` (README).
- Tiled navmesh enables re-baking and hierarchical planning (README statement). `verified`.
- Hierarchical: Botea, Müller, Schaeffer "Near Optimal Hierarchical Path-Finding (HPA*)", Journal of Game Development 1(1), 2004 (page range cited variously, pp. 7-28 most common) `verified (abstract/landing page)`; Pelechano & Fuentes, HNA*, Computers & Graphics 59, pp. 68-78, 2016: abstract says up to 7.7 times faster than A* on the initial NavMesh (their measurement) `verified (abstract/landing page)`.
- Flow fields: Elijah Emerson (Gas Powered Games, Supreme Commander 2), "Crowd Pathfinding and Steering Using Flow Field Tiles", Game AI Pro (2013), ch. 23, pp. 307-316; the earlier attribution to "E. Pinter" is dropped; GDC 2011 talk not checked. `verified (abstract/landing page)`.
- Crowd avoidance: van den Berg, Guy, Lin, Manocha, "Reciprocal n-Body Collision Avoidance", Robotics Research (14th ISRR), Springer Tracts in Advanced Robotics vol. 70, 2011, pp. 3-19 (the 2009 date is the symposium year; ORCA name not checked in abstract). `verified (abstract/landing page)`.
- 3D/flying: Brewer, "3D Flight Navigation Using Sparse Voxel Octrees", Game AI Pro 3, ch. 21, 2017, pp. 265-274 (Digital Extremes) `verified (abstract/landing page)`; Hechenberger "Navigation volumes" not collected.
- UE navmesh tiles / "Navigation at scale" talks: not located; needs a concrete GDC/UE docs source. `unverified`.
- Server-side cost: Detour sliceable queries confirmed in `DetourNavMeshQuery.h`: `initSlicedFindPath`, `updateSlicedFindPath(const int maxIter, int* doneIters)`, `finalizeSlicedFindPath(...)` (+ `finalizeSlicedFindPathPartial`). `verified (full text)` (header). "Server needs tiles only around active players" is design inference.

**Applicability**
- Detour/Recast/TileCache are zlib-licensed and C++ and fit the vendor model; tile size must align with the world streaming cell size.
- Flying agents and multi-level (bridges, interiors) need a separate representation (SVO or navmesh layers); decide per agent class.
- Crowd steering: DetourCrowd (RVO-like) for small groups; flow fields for large unit counts; MMO NPC counts likely favour sparse per-agent path + local avoidance.

**Risks / measure**
- Tile build time and memory per km^2; dynamic obstacle rebuild latency; tile streaming hitch.
- Server CPU budget per nav query at peak concurrency (sliced queries).
- Interaction with origin rebasing (tile coordinates in double or region-local).

---

## 6. Input systems

- UE Enhanced Input: Input Actions (data assets, value types bool/Axis1D/2D/3D; states Started/Ongoing/Triggered/Completed/Canceled), Input Mapping Contexts added/removed at runtime with priority (highest priority context wins when several map the same action), Modifiers (pre-process raw value: negate, swizzle, dead zone, smoothing) and Triggers (explicit/implicit/blocker; tap, hold, chord); Player Mappable Input Configs for remapping presets; per-platform context redirects; `InjectInputForAction` and `showdebug enhancedinput` for testing/debug. `verified`.
- Unity Input System: replaces the Input Manager, supports any device, has an Input Actions editor; landing page does not cover action maps, control schemes or InputEventTrace record/replay. Now: action map = named collection of actions enabled/disabled together; control schemes bind device types to subsets of bindings (Concepts/ActionsEditor pages, v1.5-1.16); `InputEventTrace` "lets you record input events for later processing", save/load/`Replay()` (API page 1.11.2). `verified (full text)` for InputEventTrace, `verified (abstract/landing page)` for action maps/control schemes (search excerpts of manual pages).
- SDL3: single event queue with categories Gamepad (axis/button/touchpad/sensor/cap-sense), Keyboard (+text input/IME), Mouse, Pen (axis/button/motion/proximity/touch), Touch (finger, pinch); `SDL_AddEventWatch`, `SDL_SetEventFilter`, `SDL_PushEvent` for injection. Page does not describe cross-device unification. `verified`.
- Editor vs game vs UI arbitration: not sourced. Pattern from Enhanced Input (priority-ordered contexts that can consume) is the closest verified model.
- Record/replay for tests: Enhanced Input injection and SDL `SDL_PushEvent` provide the injection point; recording would be a log of raw events with timestamps (design inference).
- Accessibility remapping: Enhanced Input player-mappable configs `verified`; Game Accessibility Guidelines is a secondary reference, not collected.
- Brush/sculpt/pen inputs: SDL3 pen events expose pressure/axes (`verified (full text)`: SDL_PenAxis = PRESSURE 0..1, XTILT/YTILT -90..90 deg, DISTANCE 0..1, ROTATION -180..179.9, SLIDER 0..1, TANGENTIAL_PRESSURE; unsupported axes report zero).

**Applicability**
- Layered model: raw device events (SDL3) -> device-agnostic action layer (actions with value types, modifiers, triggers) -> context stack with priorities and consumption (editor viewport, gizmo, UI, game).
- Keep raw-event injection as the test seam: record/replay at the SDL event boundary and at the action boundary.
- Pen pressure and touch gestures fit action value types (Axis1D/2D/3D) without special cases.
- Remapping configs as serialized assets, aligned with the asset system.

**Risks / measure**
- Latency of event -> action -> gameplay across the fiber scheduler (must be bounded).
- UI vs viewport focus arbitration in the editor (existing code behaviour to audit, not researched here).
- Device hot-plug and IME/text input interplay with action contexts.

---

## Source index (state)

| Source | Org / venue / year | State |
|---|---|---|
| Jolt Physics docs, jrouwe.github.io/JoltPhysics | J. Rouwe | verified |
| ACL README, github.com/nfrechette/acl | N. Frechette, MIT | verified (no numbers) |
| Recast Navigation README | M. Mononen et al., zlib | verified |
| UE Enhanced Input docs | Epic Games | verified |
| UE Interchange overview | Epic Games | verified (landing only) |
| SDL3 CategoryEvents | libsdl.org | verified |
| Unity Input System 1.11 manual landing | Unity | verified (landing only) |
| XPBD, MIG 2016 | Macklin, Müller, Chentanez | verified (abstract/landing page) |
| PBD (VRIPhys 2006, not 2007); Small Steps SCA 2019; Unified Particle Physics TOG 2014 | Müller et al.; Macklin et al. | verified (abstract/landing page) |
| Rouwe GDC 2022 | Guerrilla / GDC Vault | verified (abstract/landing page) |
| Clavet GDC 2016; Learned MM TOG 2020; Bollo GDC 2018 | Ubisoft; Holden et al.; The Coalition | verified (abstract/landing page) |
| Büttner 2019 | Ubisoft, I3D 2019 keynote (not GDC) | corrected; slides URL seen, not opened |
| DQS I3D 2007; FABRIK 2011; PSD SIGGRAPH 2000 | Kavan; Aristidou; Lewis | verified (abstract/landing page) |
| ACL perf docs | N. Frechette | verified (full text) |
| glTF 2.0.1 spec; extension registry | Khronos | verified (full text, TOC-level) |
| FBX SDK; ufbx; OpenUSD README; Blender save_post | Autodesk; ufbx; Pixar; Blender | landing / full text, see Verification pass |
| Interchange sub-pages | Epic | partial (search excerpts) |
| Detour sliced query header; HPA*; HNA*; ORCA; Brewer SVO; Emerson flow fields | various | verified (full text) header; others abstract/landing page |
| Unity action maps / control schemes / InputEventTrace; SDL3 PenAxis | Unity; libsdl.org | verified |

Still not obtained: any primary source for MMO-scale physics sharding, UE navmesh-at-scale talks, ACL ratio comparison against other codecs, PhysX/Havok/Chaos/NvCloth docs, Catto GDC 2005, Provot/Thomaszewski, assimp. First items for a follow-up pass.

---

## Verification pass (2026-11-07)

Status per source. "abs" = verified (abstract/landing page); "full" = verified (full text).

**Physics**
- XPBD, Macklin/Müller/Chentanez, MIG '16 (9th Int. Conf. on Motion in Games, Burlingame), pp. 49-54, doi 10.1145/2994258.2994272: abs. https://dl.acm.org/doi/10.1145/2994258.2994272 (ACM page itself returned 403; data from search result of that page and bibliographic indexes). The "stiffness independent of iteration/timestep" claim matches the abstract's opening sentence.
- PBD, Müller/Heidelberger/Hennix/Ratcliff: abs, CORRECTED to VRIPhys 2006 (author page). https://matthias-research.github.io/pages/publications/publications.html
- Small Steps in Physics Simulation, Macklin, Storey, Lu, Terdiman, Chentanez, Jeschke, Müller, SCA '19, doi 10.1145/3309486.3340247: abs. Abstract: n substeps with one XPBD iteration each beat one large step with n iterations on constraint error and damping. https://diglib.eg.org/items/322424d5-a24f-490a-a6bb-542233852032 , https://mmacklin.com/smallsteps.pdf
- Unified Particle Physics, Macklin/Müller/Chentanez/Kim, TOG 33(4), art. 153, 2014: abs. https://dl.acm.org/doi/10.1145/2601097.2601152
- Rouwe, "Architecting Jolt Physics for 'Horizon Forbidden West'", GDC 2022 (25 Mar): abs. Vault summary: switched from a commercial engine, saved memory and executable size, doubled simulation frequency at less CPU time; talk covers lock-free broadphase and lock-free island building; slides state Sequential Impulse and symplectic Euler. https://gdcvault.com/play/1027560/Architecting-Jolt-Physics-for-Horizon
- Jolt docs https://jrouwe.github.io/JoltPhysics/ : full. Quotes: CROSS_PLATFORM_DETERMINISTIC "will make the library approximately 8% slower"; double precision "the simulation runs 5-10% slower in double precision mode compared to float precision mode"; "If all simulation takes place within roughly 5 km from the origin, floating point precision is accurate enough." All three claims in sections 1/risks confirmed as docs statements (not independent measurements).

**Animation**
- Clavet GDC 2016, Ubisoft Montreal: abs. Vault summary: finds frame in mocap database matching current pose and desired future plan, short blend. https://www.gdcvault.com/play/1023280/Motion-Matching-and-The-Road
- Büttner: CORRECTED, I3D 2019 keynote, slides https://i3dsymposium.org/2019/keynotes/I3D2019_keynote_MichaelButtner.pdf (via search results; not opened); no GDC Vault entry found.
- Learned Motion Matching, TOG 39(4), art. 53, 2020, doi 10.1145/3386569.3392440: abs. https://dl.acm.org/doi/10.1145/3386569.3392440
- Bollo GDC 2018: abs. https://www.gdcvault.com/play/1025331/Inertialization-High-Performance-Animation-Transitions
- ACL: full. README https://github.com/nfrechette/acl : C++11 headers, MIT, "since UE 5.13" as printed. Docs (develop branch): CMU database, 2534 clips at 24 FPS, raw 1429.38 MB; v2.1.0 compressed 65.66 MB, ratio 21.77:1, max error 0.0495 cm, 99th percentile 0.0089 cm, 99.96% samples under threshold (v2.0.0 19.81:1; v1.3.0 20.13:1); error measured 3 cm from each bone, threshold 0.01 cm. Decompression (v2.1.0 doc, iPad Pro, cold cache, median `decompress_pose`): 104_30 0.910 us, Trooper_1 2.304 us, Trooper_Main 28.837 us (forward). Platforms Ryzen 2950X, Pixel 7, iPad Pro. Docs: https://github.com/nfrechette/acl/blob/develop/docs/cmu_performance.md , .../decompression_performance.md
- DQS: abs. https://doi.org/10.1145/1230100.1230107 ; FABRIK: abs. https://www.sciencedirect.com/science/article/abs/pii/S1524070311000178 ; PSD: abs. https://doi.org/10.1145/344779.344862

**DCC**
- glTF: full (TOC-level) https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html ; extensions https://github.com/KhronosGroup/glTF/blob/main/extensions/README.md
- FBX SDK: abs https://aps.autodesk.com/developer/overview/fbx-sdk ; ufbx: full https://github.com/ufbx/ufbx ; OpenUSD: abs https://github.com/PixarAnimationStudios/OpenUSD
- Interchange: partial https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine (translators/pipelines/factories confirmed via search excerpt; the framework landing page itself names only pipelines). Blender save_post: full https://docs.blender.org/api/current/bpy.app.handlers.html

**Navigation**
- Recast README: full https://github.com/recastnavigation/recastnavigation (zlib; TileCache "Navmesh streaming. Useful for large levels and open-world games"; Crowd; C++98). Detour header: full https://raw.githubusercontent.com/recastnavigation/recastnavigation/main/Detour/Include/DetourNavMeshQuery.h
- HPA*: abs https://webdocs.cs.ualberta.ca/~games/pathfind/ ; HNA*: abs https://www.sciencedirect.com/science/article/abs/pii/S0097849316300668 ; ORCA: abs https://link.springer.com/chapter/10.1007/978-3-642-19457-3_1 ; Brewer: abs http://www.gameaipro.com/GameAIPro3/GameAIPro3_Chapter21_3D_Flight_Navigation_Using_Sparse_Voxel_Octrees.pdf ; Emerson: abs http://www.gameaipro.com/GameAIPro/GameAIPro_Chapter23_Crowd_Pathfinding_and_Steering_Using_Flow_Field_Tiles.pdf (chapter PDFs listed in search results, not opened)

**Input**
- Unity manual pages and InputEventTrace: https://docs.unity3d.com/Packages/com.unity.inputsystem@1.11/api/UnityEngine.InputSystem.LowLevel.InputEventTrace.html (full); the direct 1.11 ActionMaps.html/ControlSchemes.html URLs return 404, concepts taken from https://docs.unity3d.com/Packages/com.unity.inputsystem@1.5/manual/Concepts.html (abs).
- SDL3 pen axes: full https://wiki.libsdl.org/SDL3/SDL_PenAxis

**Still unverified**: MMO physics sharding, Catto/Box2D v3, PhysX/Havok docs, Provot, Thomaszewski, Chaos Cloth, NvCloth, UE navmesh at scale, assimp, UE retargeting/Control Rig docs, Unity humanoid, Game Accessibility Guidelines, Hechenberger; all because not searched in this pass (or no primary page located).
