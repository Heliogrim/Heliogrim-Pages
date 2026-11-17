# Glossary

Terms used across the architecture pages and the [battle plan](plan/index.md), in the sense Heliogrim uses them. Most entries started as explanations the owner asked for while answering the [question batches](plan/work/questions.md); the chunk W64.4 on the [quality and process page](plan/work/quality-and-process.md) turns them into hover definitions.

Entries are alphabetical. A term in *italics* inside a definition has its own entry.

## A to C

ACL
:   Animation Compression Library (MIT, header-only). Compresses animation clips; vendored if it builds cleanly under clang-cl (Q36.1).

Admission limit
:   A load-shedding policy: a *cell* that is full stops accepting new players instead of slowing down for everyone (Q57.1).

Affine thread
:   A thread owned by one subsystem that stays off the fiber scheduler and receives work through a direct-completion inbox. Used for the platform message loop, the IO thread and the audio device thread.

Agones
:   An open-source Kubernetes extension for game servers (GameServer resource, fleets, allocation, a server-side SDK). Mapped as an orchestration adapter later, not a dependency (Q58.1).

AgX
:   A filmic tone-mapping curve with a gentle highlight roll-off and desaturation. Heliogrim's game-view tonemapper; see *PBR Neutral* (Q23.1).

Async compute
:   Running compute work on a second GPU queue concurrently with graphics. Hint-only in the render graph; candidates are GI probes, denoise passes, particles, next-frame culling, VSM pages, froxels and light culling (Q14.1).

Authoritative
:   State the server owns and every client must agree on: it collides, persists or matters to gameplay. Opposite of *cosmetic*. Classification applies to the state, not to the generator that produced it (Q33.1).

Bounded effect volume
:   An authored box or convex region with a priority that tells weather, audio reverb, GI and physics "inside here, different rules". The `LayerVolume` type (Q29.1).

BRDF
:   Bidirectional Reflectance Distribution Function: the shader function that says how much light leaving a surface in the view direction came from each incoming direction. Heliogrim's `lighting.brdf.asl` implements the Disney principled parameterisation (Burley 2012), and the IBL lookup tables (`brdfLut`) precompute its integrals.

Cancellation token
:   A shared flag a task polls to learn that its result is no longer wanted; the fiber scheduler's cancellation model (Q02.1).

Cascade (ocean)
:   One FFT height field at one world scale. Four cascades at roughly 1 km, 250 m, 60 m and 15 m patch sizes cover swell to ripples without visible tiling (Q30.2).

Cascade (shadow)
:   One depth map in a cascaded shadow map (CSM), covering a slice of the view frustum. The current shadow implementation; *virtual shadow maps* replace it.

Cell
:   The unit of streaming, persistence and server ownership in the world partition: a fixed-size leaf (256 m to start) under a quadtree, as a 2D column with optional authored *height layers* (Q40.1, Q40.2).

Comb filtering
:   The hollow, metallic sound of a signal summed with a delayed copy of itself; the symptom *delay compensation* prevents.

Coroutines
:   C++20 stackless suspension: a function that `co_await`s is split by the compiler into a state machine and resumes where it left off. Planned as a second way to suspend beside *fibers*, awaiting the same waitables; not yet used in the engine.

Cosmetic
:   State a client may generate or vary locally without anyone caring about the difference (grass detail, pebbles, decals). May read *authoritative* state as input (Q33.1).

Crash handler
:   The in-house component that catches a crash, writes a minidump plus log tail and, in a later iteration, attaches it to a bug report. "Crashpad" was only a phrase for it (Q06.1).

## D to G

DAG
:   Directed acyclic graph: nodes with one-way edges and no cycles. The task pipeline, the render graph and the actor tick stages are all DAGs, so every pass declares its dependencies and the scheduler derives a valid order.

Delay compensation
:   Inserting matching delays on the shorter of two parallel audio paths when the longer one goes through a latency-adding effect (convolution reverb, lookahead limiter, linear-phase EQ), so the signals re-align at the bus. Within a bank in milestone 4, across banks later (Q38.3).

Deterministic
:   Produces bit-identical results for identical inputs. Scope (a): only with the same binary. Scope (b): across machines built with the same compiler. Heliogrim requires (b) only for action evaluation in the simulation bundles (Q59.1).

DirectStorage
:   Microsoft's storage API that streams compressed data to the GPU and decompresses it there (GDeflate). The IOCP backend is shaped so a DirectStorage backend can slot in later (Q03.2).

Dual Contouring
:   A voxel surface extraction that places one vertex per cell at the position best fitting the stored edge normals, so sharp carved edges survive. Chosen for the terrain voxel overlay over *Surface Nets* (Q28.1).

Dual quaternion skinning
:   Blends bone transforms as dual quaternions instead of matrices, which keeps volume at twisted joints (no candy-wrapper collapse). A per-asset option beside *linear blend skinning* (Q36.2).

Engaged tier (T1)
:   The sync tier for entities the player is interacting with: current target, melee attackers, projectiles aimed at or by the player. Predicted at full fidelity under a floating cap that starts at 32 (Q56.4). See [agent sync](architecture/agent-sync-exploration.md).

Eulerian solver
:   A fluid solver that stores velocity and density on a fixed grid. The smoke, fire and dust scope of the fluids bundle (Q31.2).

Fiber
:   A user-space thread of execution the scheduler switches between without the kernel. Every engine task and coroutine runs on one; waiting parks the fiber instead of blocking a thread.

FiberMutex
:   A mutex that parks the waiting fiber rather than spinning or blocking the thread; the shared-read variant must not starve writers (Q02.2).

First-party module
:   A module the game developer built and signed into their game, including store plugins they compiled. The only kind a shipped game loads; player-authored native modules are out of scope (Q48.2).

FLIP
:   Two meanings. In fluids: a hybrid particle-grid liquid solver (Fluid Implicit Particle), the local 3D liquid scope. In testing: NVIDIA's perceptual image difference metric used per rendering test (Q62.3).

Froxel
:   A frustum-aligned voxel: the view frustum sliced into a 3D grid for volumetric lighting and fog. The froxel far plane (2 km) is where per-froxel fog stops and the analytic horizon model takes over (Q21.1).

FSR
:   AMD FidelityFX Super Resolution, the only upscaler Heliogrim plans; free and vendor-neutral (Q23.2).

G-buffer, thin
:   A deferred-shading geometry buffer kept to the minimum attributes, with material-classified resolve passes that shade each material class separately (Q15.2).

GDeflate
:   A GPU-friendly Deflate variant DirectStorage can decompress on the GPU; a mandatory candidate in the codec benchmark (Q03.3).

## H to M

Height layer
:   A named vertical band inside a *cell* column (surface, cave level 1, cave level 2) with its own packages, so a player underground does not stream the city above (Q40.2).

Horizon (volumetrics)
:   The distance to which fog and clouds are modelled, 32 km; beyond the *froxel* far plane it uses analytic, not voxelised, scattering (Q21.1).

IR / IL
:   Intermediate representation or intermediate language: the compiler's in-between form between source and target code, built so passes can analyse and rewrite it. See *IR (accel)* for the shader compiler's own IR; *SPIR-V* is the IL it emits.

IOCP
:   Windows I/O completion ports; the first asynchronous storage backend (Q03.2).

IR (accel)
:   The engine's shader intermediate representation. Milestone 2 has landed; passes carry engine semantics only, there is no general optimiser (Q11.1, Q11.3).

Kinematic proxy
:   A capsule or box the server moves by its own controller and collides only against the world, not through the solver. The default server body for actors, with full rigid bodies opt-in or switched in by the adaptive tiers (Q34.2).

Lavapipe
:   Mesa's software Vulkan implementation; runs small rendering tests on GitHub-hosted CI runners (Q62.1).

Linear blend skinning
:   The standard skinning that averages bone matrices per vertex; fast, but collapses volume at twisted joints. See *dual quaternion skinning*.

Lock-step action evaluation
:   The owner's phrase for synchronised combat: realised as server-scheduled action events on a shared tick timeline, not as a lock-step simulation of the whole range. Only the action's timeline and hit windows must be *deterministic*.

Material layer set
:   The fixed list of material layers (base, coat, sheen, emissive and so on) a surface can stack in the first version; an open, authored layer stack comes later behind a designed seam (Q16.1).

Meshlet
:   A small cluster of triangles (typically up to 64 vertices, 124 triangles) that mesh shaders and GPU culling operate on; the micropolygon pipeline's unit of work.

Metered run
:   A recorded, checkpointed gameplay run replayed after a change (shader, material, optimisation) and compared against tolerance bands, not bit-for-bit (Q04.3).

MF2
:   MessageFormat 2, the ICU standard for localised message syntax still settling; Heliogrim's in-house Fluent-like subset stays compatible with it (Q52.1).

Motion matching
:   Locomotion by searching a database of captured motion every few frames for the segment that best matches the current pose and desired trajectory, instead of hand-built state machines. After the first version (Q36.3).

## N to R

Navmesh
:   A navigation mesh: walkable polygons agents path over, built per tile from the terrain and colliders. Library choice per the comparison in W37.0 (Q37.1).

OIT
:   Order-independent transparency: blending transparent surfaces correctly without sorting them back to front. Candidates are weighted blended (McGuire and Bavoil 2013) and moment-based (Münstermann et al. 2018); system S22, after S15.

Origin rebasing
:   Shifting the floating-point origin to the active *cell* so large worlds keep precision; a fixed-origin project mode serves small games (Q07.1).

OTLP
:   OpenTelemetry Protocol, the default export format for engine metrics, client role first (Q04.4).

PBR Neutral
:   Khronos' neutral tone mapper that preserves authored colours; the asset-verification view, switchable against *AgX* (Q23.1).

Perfetto
:   Google's trace viewer; the engine's own trace format converts to it (Q04.1).

Pipeline library
:   A Vulkan object that caches compiled pipeline stages so variants link quickly; designed now for the material variant explosion (Q13.1).

Prediction (client)
:   Running the local actor's simulation ahead of the server and reconciling when the server disagrees; scope is the local actor and its mount, tier T0 (Q56.1).

Probe (GI)
:   A point that stores incoming light (irradiance, often as spherical harmonics or octahedral maps) for interpolation by nearby surfaces; the probable GI target (Q20.2).

QUIC
:   The UDP-based transport under HTTP/3. In Heliogrim it serves authentication, OAuth and web services only, never game-critical transfer (Q55.2).

Quadtree (partition)
:   The hierarchy over fixed leaf *cells* that streaming priority and server interest query; persistence and ownership stay at the leaf (Q40.1).

Radiance cascades
:   A recent GI technique that stores radiance at several spatial and angular resolutions; in the widened GI brief of W20.0 (Q20.1).

Ray query
:   Inline ray tracing from any shader stage without a separate ray-tracing pipeline; required by the minimum spec (Q12.2).

Record header
:   The prefix of a top-level serialised record: u64 type hash, u16 version, length and checksum. Nested reflected types carry only a version; value structs carry nothing (Q01.1).

Result at boundaries
:   `Result<T, Diagnostic>` returned only at subsystem boundaries, never on hot paths (Q05.1).

RGP
:   Radeon GPU Profiler; the engine labels passes with `VK_EXT_debug_utils` so RGP captures read well (Q04.1).

RTPC
:   Real-Time Parameter Control, Wwise's name for a named float the game drives; Heliogrim calls it a parameter (Q38.4).

## S to Z

Scheduled-start delay (`d`)
:   The time the server adds to an NPC action's start tick so every client in range receives it before it starts and plays the wind-up on the same tick. Floats per *cell* from the 90th-percentile one-way delay, clamped to 40 to 100 ms (Q56.2).

SDF / MSDF
:   A signed distance field stores, per texel, the distance to the nearest edge, so a shader reconstructs a sharp edge at any resolution; a multi-channel SDF stores three distances so corners survive too. The planned text and *vector UI* canvas; plain 3D SDFs serve zone volumes.

Semantic tree
:   The accessibility and automation view of the UI: widget roles, names, states and relations, independent of pixels. Shipped before the Windows UI Automation provider (Q43.1).

Slang
:   A shading language and compiler with generics and modules. Not used; Heliogrim compiles its own *IR* (Q11.2).

Sparse residency
:   A Vulkan feature where an image or buffer is bound to memory in pages, and only the pages in use are resident. Used for streamed texture mips today and the page pool behind *virtual shadow maps*.

SPIR-V
:   Khronos' binary shader IL that Vulkan consumes. ASL compiles through its own *IR* to SPIR-V directly; the glslang-gated GLSL path is the fallback (S11).

Stack cache (resolver)
:   Caching per resolver stage so a request that resolves archive, package, then file reuses the cached package stage and only adds the missing resolver on top (Q03.1).

Surface Nets
:   A voxel surface extraction that averages edge crossings per cell; simpler and faster than *Dual Contouring* but rounds every edge.

SVDAG
:   Sparse voxel directed acyclic graph: a sparse voxel octree whose identical subtrees are merged into one shared node, cutting memory by orders of magnitude for static scenes. A candidate structure for the shared spatial scene service beside a BVH.

Switch, state, event (audio)
:   An event starts, stops or modifies sounds; a state is a named enum, scopable to a game object; a switch (footstep surface) is a state read by the event. Parameters are named floats (Q38.4).

Tick-rate degradation
:   A load-shedding policy: an overloaded *cell* simulates fewer ticks per second at unchanged wall-clock time. The baseline, with *admission limits* (Q57.1).

Tier (sync)
:   One of five replication fidelities per entity per connection: T0 self, T1 *engaged*, T2 perceptive (interpolated), T3 distant (reduced rate), T4 outside interest.

Time dilation
:   A load-shedding policy where the cell's simulated time runs slower than real time for everyone in it; not the baseline (Q57.1).

Transvoxel
:   A seam scheme that stitches voxel meshes of neighbouring LOD levels without cracks.

Uber-shader
:   One shader that covers many material variants through branches or specialisation constants; W16.1 analyses when merging variants into one pays off (Q15.2).

Upcaster
:   A per-type function that converts a serialised record from an older version to the current one on load; bytes-level by default (Q01.2).

Vector UI
:   The canvas that draws UI primitives (boxes, rounded boxes, lines, text, icons, paths) from commands rather than textures (Q42.2).

Virtual geometry
:   Cluster-based geometry streaming and LOD selection at *meshlet* granularity, so detail is chosen per screen region; the micropolygon pipeline.

Virtual shadow maps (VSM)
:   Shadow maps stored as sparse 128 KiB pages allocated only where the screen needs them, giving uniform high resolution at any distance. Required; CSM is the first step (Q19.1, Q18.3).

Visibility buffer
:   A render target storing only triangle and instance IDs (2 × 32 bits) per pixel; material shading happens in a later pass that reads it (Q15.3).

VSBVH
:   The owner's term for a bounding volume hierarchy suited to very uneven density; named as the kind of structure the partition's dense-versus-sparse split should favour (Q40.1). Definition to be settled in W40.1.

XPBD
:   Extended Position Based Dynamics, a GPU-friendly constraint solver; the later crowd-scale cloth tier (Q35.1).

YAML subset, canonical
:   The text serialisation form: block style, sorted keys, schema-typed scalars, engine-formatted numbers, emitted through vendored ryml (Q01.3).
