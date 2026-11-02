# Actor System (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

This note collects the design direction for the actor and component system: archetype storage, component dispatch, causality within a frame, and serialization. It starts from an external design review and the team's follow-up notes. Where the review and our notes disagree, both positions are stated.

## 0. Current State in the Engine

Checked against the engine source on 2026-11-02.

- **Actor ticks do not run.** `ActorTickStagePrePhysics::staticDispatch` (`Engine.ACS.Schedule/`) loops over every actor of every level and only reads `getComponents()`, marked `// TODO: Tick actor`. `dynamicDispatch` is empty. The stages (pre-physics, overlap, collision, post-physics, housekeeping) and their DAG dependencies on input, physics readback and scene post-process already exist in `ActorPipeline.cpp`.
- **Storage is per-type pools, not per-actor objects.** `Engine.ACS/Registry` keeps one `Pool<ComponentGuid, T>` per component type and one per actor type (`hybrid_storage` pages in `Storage.hpp`). An actor holds a `CompactSet<ptr<HierarchyComponent>>` and a root component.
- **Identity is a GUID.** `ActorGuid` and `ComponentGuid` are plain `Guid`s. There are no generational `(index, generation)` handles.
- **Deferred release exists.** `Housekeeping` collects pending component releases and applies them in `commit()`, which runs in the `ActorHousekeeping` stage after scene post-process. This is the start of a "mutate at a barrier" model.
- **Layout serialization exists.** `Engine.Serialization.Layouts` (`LayoutManager`, per-type layouts) sits next to structured serialization (`Engine.Serialization.Structures`). Components declare both with `ACCESS_LAYOUT` and `ACCESS_STRUCTURE`.

Consequence: "sequential actor ticks are the bottleneck" (section 1) is a target, not a measurement. Nothing ticks yet, so nothing can be measured.

## 1. Goals and Constraints

- Actors are hierarchies of spatial and logical components.
- Actors with the same signature (sealed or archetype) share dense memory chunks. Example: static geometry, which has fixed size and needs no extra allocation.
- Render, physics, animation and sound logic is mostly embedded as components. Scene systems map components to internal representations (graphics, physics, ...).
- Users add component types, sealed actor types and custom queries, mutations and events without touching engine internals.
- Ticks run through the global DAG task pipeline, with pre-physics and post-physics stages. Scene cycles are broadcast, update and post-process.
- Actor ticks must be able to run concurrently. Today they do not run at all (section 0). The team expects sequential ticks to be the main bottleneck. This must be measured once ticks run.
- Events must not produce ghost effects. Example: an enemy dies from a hit, and a damage event later in the same frame hits the dead enemy.
- Serialization must be fast in bulk, both for actor state and for components.
- Hot reload is wanted but unresolved (see section 6).

## 2. Storage: Archetype Chunks

Actors are grouped by signature (the set of component types). Each group lives in contiguous chunks (16 KB target, to be confirmed by measurement). Sealed types such as static geometry get a fixed signature and a `Static` chunk flag. Systems can then batch those chunks without checking for mutation.

Hierarchies:

- **Logical**: parent and child references stored as generational handles `(index, generation)`.
- **Spatial**: transforms stored in flat arrays ordered by breadth-first index, so propagation is a linear pass. This is a candidate, not a decision. The layout must be checked against actual access patterns.

Open: how chunk migration (signature change) interacts with handles held by in-flight events.

### 2.1 Review: archetypes versus the existing pools

The engine already has per-type pools (section 0), which behave like a sparse-set ECS. Moving to archetype chunks is a trade, not a pure gain:

| | Archetype chunks | Per-type pools (current) |
|---|---|---|
| Iterating over several component types together | Fast, linear within a chunk | Needs a join across pools |
| Adding or removing a component | Moves the whole entity to another chunk; may allocate or free chunks | Insert or remove in one pool |
| Concurrency | Structural changes force sync points | Changes stay local to one pool |

Sources: Unity Entities calls structural changes "resource-intensive", main-thread only, and the main cause of sync points ([docs](https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/concepts-structural-changes.html)). The flecs author describes the same trade and mitigates it with an archetype graph and sparse, non-fragmenting components ([flecs 4.1](https://ajmmertens.medium.com/flecs-4-1-is-out-fab4f32e36f6)).

Challenge: the goal list asks for sealed static actors **and** user-extensible component sets. Sealed actors fit archetypes. Actors that gain and lose components often (status effects, gameplay tags) fit pools. A hybrid is likely: archetype chunks for sealed or rarely changing signatures, plus pool or sparse storage for components that change often. Decide by measurement once ticks run.

Note: P2786 (trivial relocatability), which would have made chunk moves cheap and standard, was removed from C++26 at Kona in November 2025 and is deferred ([trip report](https://herbsutter.com/2025/11/10/trip-report-november-2025-iso-c-standards-meeting-kona-usa/)). Chunk moves must rely on the engine's own type traits.

## 3. Component Dispatch: Override Detection

Proposal from the team: components derive from a base (`LogicComponent` or `SceneComponent`). The base declares overridable hooks for sequential and concurrent execution. At registration, template metaprogramming checks which hooks the derived type overrides:

```cpp
template <auto BaseFn, typename Derived, auto DerivedFnPtr>
constexpr bool overrides = (DerivedFnPtr != BaseFn);
// used as: overrides<&Base::OnTick, Derived, &Derived::OnTick>
```

Intended behaviour:

- Hook not overridden (pointer equals base): the component is excluded from that execution stage at runtime. No dispatch cost.
- Hook overridden: the component is scheduled for that stage on the DAG.

**Review: this does not work for virtual hooks.** [expr.eq]/5.3: "If either is a pointer to a virtual member function, the result is unspecified" ([draft](https://eel.is/c++draft/expr.eq)). If `OnTick` is virtual, the comparison cannot be relied on, in a constant expression or anywhere else.

What does work: for a member `Fn` that is not redeclared in `Derived`, `&Derived::Fn` has type `R (Base::*)(...)`. The type names the class that declares the member ([expr.unary.op]/3.1, [draft](https://eel.is/c++draft/expr.unary.op)). So detect the override from the **type**, not the value:

```cpp
template <typename Derived>
constexpr bool overrides_tick =
    not std::is_same_v<decltype(&Derived::OnTick), decltype(&LogicComponent::OnTick)>;
```

This needs non-virtual hooks (called through a registration-time thunk, CRTP style) or a hook that is unique per derived class. It also misses overloads and templates, which a `requires` check on the hook signature can cover. Prototype and compile-check on clang-cl and MSVC before adopting.

Remaining points to verify:
- Override detection is per binary. Components in a DLL that is hot-reloaded need re-registration after reload, so this check is per registration, not a global fact.
- A derived type that overrides a hook and only calls `Base::Fn` still counts as overridden. That is acceptable: it costs a dispatch, not correctness.

Open: whether concurrent and sequential hooks are one virtual with a policy tag or two separate hooks. Two hooks are easier to detect.

## 4. Causality Within a Frame

### 4.1 What the external review proposed

Read, compute, barrier and validate, then mutate. Each emitted event carries a generational handle. Events for dead handles are dropped at the barrier. This removes ghost events caused by death in the same frame.

### 4.2 Where the team's notes add to it

A fixed three-phase frame is not enough. User code can react to an event, which requires a mutation, which may need a readback and another compute pass, and this can repeat. A single barrier per frame cannot express that.

Proposed direction: a **dynamic resolver** that runs micro-cycles until quiescence:

1. Read and compute. Emit commands into thread-local buffers.
2. Barrier. Validate handles, order commands deterministically, and apply mutations.
3. If mutations produced new events, start another micro-cycle.

Constraints to decide:

- **Termination**: a hard cap on micro-cycles per frame, with a defined behaviour when it is hit (defer to next frame, or error). Cycles in user logic must not hang the frame.
- **Ordering**: every event needs a stable sort key within a micro-cycle (for example source handle, then emission index), so results do not depend on thread timing.
- **Validity**: handles stay generational, and each event also records the micro-cycle it was emitted in, so a readback can be checked against the state it was based on.
- **Scheduling cost**: the number of micro-cycles should be known early. A dependency analysis of user code (read and write sets per component type) may give a static upper bound. Where it cannot, the dynamic resolver takes over.

Open: whether read and write sets are declared by the user or inferred from the hooks' template signatures.

### 4.3 Review

- **Start from what exists.** `Housekeeping` already defers component releases to a fixed stage. The first step toward the resolver is generalizing that queue to a command buffer (spawn, destroy, add and remove component, events), applied at one barrier per frame. Micro-cycles come after a single barrier works and shows real cascades.
- **Generational handles are a prerequisite**, and the engine has none (section 0). GUIDs can stay for serialization and editor identity. Runtime handles for events and commands need an index plus a generation, mapped to the GUID.
- **Determinism caveat.** A stable sort key gives reproducible ordering only if the sort key itself is stable. Emission index per thread-local buffer depends on how work is split across workers. Use the source handle plus a per-source counter, not the per-thread index.
- **Cap semantics.** Deferring leftover commands to the next frame turns a logic cycle into a silent one-frame delay. Default to an assert in debug and a deferral plus a counter in release, so the problem is visible.

## 5. Serialization

Two systems exist and stay separate (both exist in code: `Engine.Serialization.Structures` and `Engine.Serialization.Layouts`; the notes below are about extending them, not creating them):

- **Structured serialization**: binary key-value records with typed validation. Used for assets, editor data and anything that must survive engine versions. Slower, but checkable.
- **Layout serialization**: native layouts computed per type, written as raw memory streams with no embedded type information. Used for chunk dumps and bulk transfer. Fast, but only valid when the layout matches.

Implications:

- Layout streams need a **layout hash** (type set, offsets, sizes, version) in the header. Loading with a mismatched hash must fail, not reinterpret memory.
- Handles inside layout streams cannot be raw indices across sessions. The review proposes content-addressable UUIDs mapped on save and restored to runtime handles on load. For layout streams this needs a fixup table written next to the chunk data, so the bulk copy stays a memcpy plus one pass over the fixup table.
- Structured records can carry UUIDs directly.

Open: whether layout streams are only for internal caches (rebuilt on mismatch) or also used as a save format.

## 6. Hot Reload

The review proposes separating data from behaviour:

- Actor data lives in archetype chunks owned by the core runtime, which is not hot-reloaded.
- User logic lives in plugin libraries (`.dll` or `.so`) and is reached through a stable C-style function table.
- Systems receive raw spans of chunk data, not user-owned objects.

Consequences to resolve:

- Component layouts are part of the data. A layout change in a plugin is a data migration, not a code swap. This needs the layout hash (section 5) to detect it.
- Hooks registered from a DLL must be unregistered before unload, and their override checks (section 3) redone on reload.
- Plain function-pointer tables avoid C++ name mangling and vtable layout issues across recompiles. The cost is a manual ABI surface.

HMR is not in scope for the first milestone. This section records the direction only.

## 7. Decisions Needed

0. First milestone: make actor ticks run at all (sequentially, through the existing stages), with a benchmark scene. Everything else is measured against that.
1. Concurrent and sequential hook shape (one virtual with policy, or two hooks). Constrained by section 3: value comparison of virtual member pointers is unspecified.
2. Micro-cycle cap and overflow behaviour.
3. Who declares read and write sets: the user or the template signatures.
4. Storage: archetype chunks, current pools, or a hybrid (section 2.1). Chunk size and spatial transform layout, measured against real access patterns.
5. Layout streams: cache only, or save format too.
6. Runtime handle scheme (index plus generation) next to the existing GUIDs.

When any of these is decided, record it as an ADR and link it back here.

## 8. Brainstorm Log (2026-11-02)

Working notes from a design conversation. **Team** marks what the team stated; **Proposal** marks suggestions not yet agreed. Nothing here is an ADR.

### 8.1 Sealed archetypes

- **Team**: actors come in sealed archetypes. Existing candidates: `StaticGeometryActor`, `BoxShapeGeometryActor`. Users may derive from an archetype; a derived class is **never** the same archetype, because it may differ in size and behaviour.
- **Team**: components of a sealed archetype are allocated next to the actor in one cluster slot, with one stride per archetype, so actor and components share cache lines and pages.
- **Team**: a sealed archetype has a **fixed** count per component type (for example 4 wheels). A variable count is not allowed in a sealed archetype.
- **Team**: adding a component to a sealed actor at runtime **de-optimizes** it (like V8 shapes going to dictionary mode). The actor leaves the archetype cluster and becomes a dynamically composed actor whose components live in component-type pools.
- **Team**: actors that are not C++ archetypes use component-type pools (exist today) or **shape clusters**: common runtime shapes detected and promoted to cluster allocation, driven by memory and backpressure analysis.
- Code today: per-type actor pools already separate derived classes. `RegisterActorClass`, `SpawnActor`, `CreateActor(serialized)` and `CloneActorInto` are `todo_panic()`. Components are created in the actor constructor via `ActorInitializer::createComponent` into type pools; nothing is co-located yet.

### 8.2 Pointer model and relocation

- **Team**: `CachedActorPointer` is meant for this (stable id plus cached address), even though it does not implement refresh yet. `AssetHandle` / `TypedAssetHandle` is a similar shape. Wants a solid type-system representation.
- **Team**: component base classes (`LogicComponent`, `SceneComponent`, `HierarchyComponent`) may get cluster-memory hooks. Scene-system models (for example `RenderSceneSystemModel`) get relocation functions; pointers are mass-rebuilt in the (pre-)broadcast phase.
- **Proposal**: typed `ActorRef<T>` / `ComponentRef<T>` = handle + cached pointer + relocation epoch; refresh on stale epoch. Relocation only at one barrier; a sorted `(old → new)` relocation table is applied by every system in one batch pass. Raw pointers are valid within one phase.
- **Proposal**: parent links inside one cluster slot as offsets, so whole-slot moves need no fixups.

### 8.3 Compaction

- **Team**: memory and cluster regions are instrumented. The engine recompacts on its own, without user CRUD, driven by a weighted function deciding when and how.
- **Proposal**: per-region counters (live/capacity, holes, churn, access heat, memory pressure); score = benefit (wasted bytes × heat, freeable pages) − cost (bytes moved, reference fixups); hysteresis; incremental under a per-frame budget at the barrier. The same machinery promotes shape clusters.

### 8.4 Scale and order

- **Team**: general-purpose engine, from hundreds to multiple millions of objects; procedural generation; the MMO vision (no layering, no instancing) means very many handles.
- **Team**: **no ordering guarantee** for actor and component events, traversal, invocation or memory order.
- **Team**: diff/patch for procedural sections is engine-provided, likely default, but the game author chooses per use case.
- **Proposal**: 64-bit handles `(space, index, generation)`; a space is a streaming unit (cell, procedural chunk) with a paged handle table freed as a whole; batch spawn is the core path (`SpawnActor` = N=1).

### 8.5 Traversal

- **Team (agreed)**: every storage reports **spans** `(base, count, stride)` per component type; compaction works on the same base and stride.
- **Team**: primary users are engine systems, but game code may run mass queries ("all components of type T"); expose something like the scene storages' `forEach` / `remove` with `FnRef` callbacks.
- **Proposal**: a component type → storages index; `forEach<T>(FnRef)` per element and `forEachSpan<T>(FnRef)` per span; parallel by span; derived component types included unless a sealed-exact flag is set; span lists valid for one phase. Several same-type components in an archetype = one span per member offset; each has a **role** (member name), which also identifies archetype components for serialization.

### 8.6 Transforms

- **Team (agreed)**: hybrid. Local transform stays authoritative in the component (`HierarchyComponent::_localTransform` today). A spatial service owns derived data (world transform, world bounds, index).
- **Team**: derived data must be correct whenever user code runs, because physics, animation and graphics need it. `getUniverseTransform()` is the first call a game author makes; **it must not return stale data**.
- **Team**: pipelines and sub-system order can be rebuilt and recomposed, so every pass needs explicit dependencies for the pipeline/stage DAG.
- **Team idea**: a spatial scene system (or service interface) that render and physics systems reference, holding an optimized SVDAG/BVH/sparse structure, instead of each system building its own via the scene-system CRUD overloads and model remapping.

### 8.7 Archetype declaration (open)

- **Team**: a helper template (recursive, likely a trait of the actor class) models the component type and instance hierarchy. It resolves instantiated components on the actor ergonomically, by name, with no manual indices for nested arrays. Reference: `Engine.Reflow.Attributes/Style/StyleAttributes.hpp` (named attributes resolved from tuples at compile time). Must support inheritance, extension and overrides.
- **Team**: no static reflection (P2996) yet on clang-cl or MSVC; do not depend on it.
- **Team**: children are marked with an explicit marker type, for example `Slot<"wheels", WheelComponent, Count<4>, Children<Slot<"hub", HubComponent>>>`. Access `get<"wheels">()[i].get<"hub">()`. Slot names must not be emitted into the binary unless needed (**Proposal**: names only used in `consteval` lookup; verify by searching a release binary).
- **Proposal**: the component block sits **before** the actor object in the cluster slot (negative offsets from `this`), so actor-class derivation and appended slots keep base offsets constant.
- **Team (agreed)**: base-class logic uses C++23 deducing this (`this auto& self`), so `get` resolves against the concrete archetype layout at compile time. No offset table on the hot path. Overrides of any size are allowed.
- **Team (agreed)**: option (1). Base bodies live in an implementation header (`Vehicle.inl.hpp`), never in public headers. A derived class forwards with `self.Vehicle::tick()` (a `final` class can use a plain `void tick()` with `this->Vehicle::tick()`) and keeps its body in its .cpp, which includes the base `.inl.hpp`. Non-final derived classes explicitly instantiate for themselves.
- **Team**: earlier attempt (not in current code): a struct of function pointers (tick, create, destroy, mutate) built by metaprogramming and instantiated with the component pool. **Proposal**: `RegisterActorClass<T>()` builds `ArchetypeOps` per archetype with span-wide entries (`tick`, `create`, `destroy`, `relocate`, `serialize`); dispatch is one indirect call per span.
- **Team (agreed, supersedes "deducing this everywhere")**: solution 1. Plain bodies by default (base offsets stay constant because the component block sits before the actor). Deducing this plus `.inl.hpp` only for bases that allow size-changing overrides, enforced by a `static_assert` in `Extend`. No macros: `InheritArchetype<Derived, Base>` CRTP plus one explicit instantiation line per archetype. `ActorClass` only resolvable after registration.
- **Team**: C++20 modules would remove the `.inl.hpp` chain. A migration branch exists but needs large restructuring (cyclic dependencies). Revisit when modules land.
- Design document: [actor-archetypes-design.md](actor-archetypes-design.md).
- **Proposal**: a per-archetype offset table remains only for type-erased paths (editor, serialization, DLL/hot-reload boundaries), possibly via a non-template body plus a generated view shim.

## References

- External design review on archetype ECS, fiber scheduling and HMR (kept in the team's notes; not copied here).
- Related engine documents: [architecture index](index.md).
