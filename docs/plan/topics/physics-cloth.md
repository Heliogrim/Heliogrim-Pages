# Physics and Cloth

**Systems**: S34, S35 · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Research from [simulation](../sources/research-simulation.md) sections 1 and 2 (Jolt documentation verified; solver literature unverified).

## Target

- **Physics v2**: Jolt integrated fully (shapes, constraints, characters, vehicles, heightfields, soft bodies), precision and determinism decided and configured, the job system bridged to the fiber scheduler, large-world positions, server simulation islands per cell, deterministic mode for replay.
- **Cloth and soft bodies**: XPBD cloth with character collision and LOD; cloth never feeds gameplay.

## Current state (checked 2026-11-07)

- Jolt vendored as a shared library with `CROSS_PLATFORM_DETERMINISTIC` off, `OBJECT_LAYER_BITS` 16, exceptions and RTTI off, Vulkan debug renderer on. `Engine.Physics` initialises it; `Engine.Physics.Scene` is a `SceneSystem` with a registry; `Engine.Physics.Scene.Model` has box and sphere collision models reading `getUniverseTransform`; `Engine.Physics.Schedule` has a stage. No characters, vehicles, constraints, heightfields or queries exposed.

## Research summary

- Jolt (verified): sequential impulse solver with warm starting and a position pass, island splitting for parallel solve, XPBD soft bodies, symplectic Euler; islands sleep as a whole; `LinearCast` continuous collision can miss fast-rotating long objects; same binary and call order give determinism, cross-platform needs the CMake option (about 8% slower per Jolt's own statement, less tested) plus application discipline (no `std::sort`, `std::hash`, std trig; precise FP, no contraction); broadphase queries are not deterministic; the float build is accurate to about 5 km from the origin; `JPH_DOUBLE_PRECISION` stores positions as doubles (5 to 10% slower), broadphase stays float; bodies and constraints cannot be shared between `PhysicsSystem` instances; `Update` fans out through a `JobSystem` interface with callbacks from multiple threads.
- Solver background: XPBD (Macklin et al. MIG 2016) and small steps beat iterations (SCA 2019) have verified abstracts; Catto 2005 and later, PhysX 5 TGS and Havok's deterministic option remain unverified.
- Cloth (abstracts verified 2026-11-07): PBD (Müller et al., VRIPhys 2006), XPBD (MIG 2016), Unified Particle Physics (TOG 2014), strain limiting (Provot 1995, Thomaszewski 2009), Chaos Cloth and NvCloth as shipped references; collision through capsule proxies on the skeleton; LOD by iteration and particle count, baked beyond distance.

## Guidance

### S34 Physics v2

- **Decide once, early**: `JPH_DOUBLE_PRECISION` on (the MMO world target and S07 make per-region rebasing more complex than the 5 to 10% cost), `CROSS_PLATFORM_DETERMINISTIC` off by default with a deterministic build profile that turns it on for replay and rollback tests (S59). Record both as ADRs.
- **Job bridge**: implement Jolt's `JobSystem` on the fiber scheduler (S02) with a Critical-lane fan-out; callbacks are queued into the ACS stage that owns the component, not applied from Jolt's threads.
- **Scene system**: extend `PhysicsSceneSystem` with the full shape set (convex, mesh, heightfield per terrain tile, compound), constraints, character controllers, vehicles, ragdolls (from the animation skeleton, S36), queries (ray, shape cast, overlap) exposed as a scene query service shared with picking (S44).
- **World and islands**: one `PhysicsSystem` per world-partition cell group on the server (bodies cannot be shared across systems, so cross-cell interaction is an explicit handover with the cell authority, S57); the client runs one system for its loaded cells; positions are doubles with Jolt's base offset for queries.
- **Determinism discipline**: physics bundles compile with strict FP; a clang-tidy check bans `std::sort` and std trig there; the state-hash harness (S59) runs the physics test scenes.

### S35 Cloth and soft body

- Start with Jolt soft bodies (XPBD) for cloth: no new dependency, shares the collision world, CPU cost measured per instance. A GPU XPBD solver as a compute stage (S24 infrastructure) is the upgrade if crowd-scale cloth is needed.
- Cloth runs after skinning in the animation pipeline (S36) against capsule colliders bound to bones; LOD tiers by distance; far cloth is vertex-skinned.
- Cloth results never feed gameplay or the server.

## Done when

- Characters, vehicles, ragdolls and heightfield terrain simulate in a test scene; 10k sleeping bodies cost near zero; a replay of a physics scene gives identical hashes in the deterministic profile.
- A body 100 km from the origin simulates without precision artefacts.
- Jolt's update runs on fibers and the trace shows the fan-out; no callback touches ACS from a Jolt thread.
- A cloth cape collides with its character at 60 Hz; 100 cloth instances stay within the stated budget.

## Open decisions

- Server-side physics scope at MMO density (full rigid bodies versus kinematic proxies for most actors).
- GPU cloth timing.
