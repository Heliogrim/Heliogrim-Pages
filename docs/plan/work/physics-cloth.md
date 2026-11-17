# Work: Physics v2 and Cloth

**Systems** S34, S35 · **Issues** [#114](https://github.com/Heliogrim/Heliogrim-Engine/issues/114), [#115](https://github.com/Heliogrim/Heliogrim-Engine/issues/115) · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Physics and cloth](../topics/physics-cloth.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| `Engine.Physics`, `Engine.Physics.Scene(.Model)`, `Engine.Physics.Schedule` | Jolt init, `SceneSystem` with registry, box and sphere models, a stage | Everything else is new; the `SceneSystem` pattern is kept |
| Jolt vendored config (shared lib, determinism off, 16 layer bits, debug renderer on) | Build shape | Two build-option decisions become ADRs (W34.0) |
| [Large-world work](render-graph-gpu-driven.md) Q07.2 | Double build or base offset | Topic page recommends `JPH_DOUBLE_PRECISION` on; W34.0 measures |
| [Concurrency work](concurrency-fibers.md) | Critical-lane fan-out, no callbacks from foreign threads | Jolt `JobSystem` bridge |
| [Bounding volumes exploration](../../architecture/bounding-volumes.md) | Spatial query options | Jolt queries become the scene query service; picking (S44) uses it |
| [Animation work](animation.md) | Skeleton drives ragdolls and cloth colliders | Order: evaluate, then ragdoll and cloth |
| [Networking work](networking-mmo.md) S57 | Cell authority and handover | One `PhysicsSystem` per cell group on the server |
| [Agent-sync exploration](../../architecture/agent-sync-exploration.md) (W56.0) | The tiered sync strategy needs no physics determinism; client corrections come from reconciliation | Adaptive body tiers (Q34.2) stay independent of the sync tiers |

## Architecture

- **Bundles**: `Engine.Physics` becomes the Jolt wrapper layer (`Engine.Physics.Jolt`: job bridge, shape factory, double positions); `Engine.Physics.Scene` extended (shapes, constraints, characters, vehicles, ragdolls, queries); new `Engine.Physics.Cloth` (Jolt soft bodies first, GPU XPBD later); `Engine.Physics.Schedule` keeps the stage.
- **Provides**: full rigid-body surface as components, character controller, vehicles, scene query service (ray, shape cast, overlap), per-cell-group physics systems, deterministic profile, cloth.
- **Consumes**: fiber scheduler (S02), `WorldPosition` (S07), terrain heightfields (S27), cells (S40), skeleton poses (S36), state-hash harness (S59), replication (S56, later).

## Code design

| Type | Contract |
|---|---|
| `FiberJobSystem : JPH::JobSystem` | Fan-out on the Critical lane; barrier as a `JoinCounter`; Jolt callbacks enqueue events into the owning ACS stage, never touch components from Jolt's threads. |
| `PhysicsWorld` | One `JPH::PhysicsSystem` per cell group (server) or per loaded set (client); base offset per world; bodies never shared across worlds; handover is explicit (S57). |
| `ShapeFactory` | Convex, mesh, heightfield (per terrain tile), compound from asset data; cached by content hash. |
| Components | `RigidBodyComponent`, `ConstraintComponent`, `CharacterComponent`, `VehicleComponent`, `RagdollComponent` as archetype components mirrored by `PhysicsSceneSystem`. |
| `PhysicsQueryService` | `rayCast`, `shapeCast`, `overlap` over the active worlds; registered on the scene; picking and audio occlusion use it. Broadphase queries are documented non-deterministic. |
| `DeterministicProfile` | Build profile: `CROSS_PLATFORM_DETERMINISTIC` on, strict FP, clang-tidy bans on `std::sort` and std trig in physics bundles. |
| `ClothComponent` | Jolt soft body after skinning against capsule colliders bound to bones; LOD tiers by iterations and particle count; far cloth vertex-skinned; never feeds gameplay. |
| `GpuCloth` | Later compute XPBD stage on S24 infrastructure; same component interface. |

Placement: `Engine.Physics.Jolt/{FiberJobSystem,PhysicsWorld,ShapeFactory}`, `Engine.Physics.Scene/{Components,PhysicsQueryService}`, `Engine.Physics.Cloth/`. Tests: deterministic profile hash replay; 100 km body; 10k sleeping bodies; cloth cape at 60 Hz; 100 cloth instances budget.

## Work chunks

### W34.0 Jolt build-option decisions and job-bridge spike · explore · after W02.2

- **Goal**: measure `JPH_DOUBLE_PRECISION` and `CROSS_PLATFORM_DETERMINISTIC` cost on a test scene; prototype `FiberJobSystem`; draft two ADRs.
- **Output**: `architecture/physics-exploration.md` with numbers; ADR placeholders.
- **Questions**: Q34.1 (answered by numbers unless the owner overrides).

### W34.1 Physics v2 design · design · after W34.0, W07.1, W40.1

- **Goal**: wrapper layer, worlds per cell group, components, shape factory, query service, deterministic profile, server scope with the adaptive body tiers (Q34.2).
- **Output**: `architecture/physics-v2-design.md`; plan (shapes and queries first, then characters, vehicles, ragdolls).
- **Questions**: Q34.2, Q34.3.

### W34.2 Implement job bridge, shapes, queries, double positions · execute · after W34.1, W07.2

- **Done when**: Jolt update runs on fibers with the fan-out visible in the trace; no callback touches ACS from a Jolt thread; a body 100 km out simulates cleanly; query service serves picking.

### W34.3 Implement characters, vehicles, ragdolls, heightfields · execute · after W34.2, W27.2, W36.3 (ragdolls)

- **Done when**: the test scene simulates all four; 10k sleeping bodies cost near zero.

### W34.4 Deterministic profile and replay hash · execute · after W34.2, W59.2

- **Done when**: a physics scene replays with identical hashes in the deterministic profile.

### W35.1 Cloth design · design · after W34.2, W36.2

- **Output**: `architecture/cloth-design.md`; plan.
- **Questions**: Q35.1.

### W35.2 Implement Jolt soft-body cloth with LOD · execute · after W35.1

- **Done when**: a cape collides with its character at 60 Hz; 100 instances within budget.

### W35.3 GPU XPBD cloth · execute · after W35.2, W24.2 (later; Q35.1 keeps it out of the first release)

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q34.1 | Accept `JPH_DOUBLE_PRECISION` if the measured cost is at or below 10%. The owner notes that if Jolt becomes a problem later, it may be changed or replaced; the wrapper layer in W34.1 is the seam for that. |
| Q34.3 | Split builds per role: the Jolt debug renderer is compiled only into roles with a GPU. |
| Q34.2 | Design for level 3 (adaptive body tier per actor: full body near players or during game events such as a siege, kinematic proxy or frozen far away; the wrapper switches tiers without gameplay code noticing) and implement level 2 first (proxies by default, full bodies opt-in for vehicles, debris and physics puzzles). W34.1 designs and spikes the tier switch. |
| Q35.1 | Not a first-release target. Jolt soft bodies with LOD first (W35.2); GPU XPBD cloth stays the later chunk W35.3. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q34.1 | Accept `JPH_DOUBLE_PRECISION` on for all roles if the measured cost is at or below 10%? | W34.1 | Yes |
| Q34.2 | Server-side physics scope at MMO density: full rigid bodies for all actors, or kinematic proxies for most with full bodies for vehicles and debris? | W34.1 | Kinematic proxies by default; full bodies opt-in per archetype |
| Q34.3 | Keep the Vulkan debug renderer build of Jolt in the server role, or split builds per role? | W34.1 | Split: debug renderer only in editor and client builds |
| Q35.1 | Is crowd-scale cloth (hundreds on screen) a first-release target, deciding whether GPU cloth is planned now? | W35.1 | No; Jolt soft bodies only |
