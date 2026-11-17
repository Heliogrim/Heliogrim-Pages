# Sealed Actor Archetypes (Design)

**Status**: design, approved 2026-11-03. Agreed in a design conversation on 2026-11-02 (log: [actor-system.md, section 8](actor-system.md#8-brainstorm-log-2026-11-02)). Accepted decisions move to ADRs after implementation proves them.

Markers: **Decided** = agreed by the team. **Builder's call** = left to the implementer. **Proposal** = suggested in this document, not yet confirmed by the team.

## 1. Intent

Heliogrim targets anything from a few hundred to millions of actors (procedural worlds, a single-shard MMO vision without layering or instancing). Today every component lives in its own per-type pool and actors hold pointers to them. Iterating one actor's components chases pointers across memory, and nothing ticks yet.

This design makes C++-declared actor types into **sealed archetypes**: a fixed component structure, known at compile time, allocated as one contiguous block per actor in clusters of same-archetype actors. It also finishes the actor creation API (`RegisterActorClass`, `CreateActor`, `SpawnActor`) on top of it, and lays down the handle and relocation model that later work (de-optimization, compaction, shape clusters, spatial service) builds on.

## 2. Goals

1. An actor class declares its component structure (types, counts, parent hierarchy, names) through a template layout. The engine derives memory layout, construction, destruction, relocation and serialization from it.
2. Actor and its archetype components live in **one cluster slot**; slots of one archetype are packed in chunks with a fixed stride.
3. Components are resolved by name at compile time (`get<"wheels">()[i].get<"hub">()`); no manual indices, no runtime lookup on the hot path.
4. Derived actor classes are allowed and are **always a different archetype** from their base (they may differ in size and behaviour).
5. `ActorClass` exists only for registered archetypes, carries everything captured from the templates, and is the input to `CreateActor` / `SpawnActor`.
6. Batch spawning N actors of one archetype is the core path.
7. Every storage reports components as **spans** `(base, count, stride)` per component type.
8. Stable references across relocation: typed handles with cached pointers.

## 3. Non-goals (this design)

Designed later, with only their interfaces reserved here:

- **De-optimization**: moving a sealed actor out of its cluster when a component is added at runtime (section 9 reserves the hooks).
- **Compaction policy**: the weighted function deciding when to recompact cluster regions.
- **Shape clusters**: detecting common runtime shapes of dynamic actors and promoting them to clusters.
- **Unified traversal** across clusters, shape clusters and type pools beyond the span interface defined here.
- **Transform caching and propagation passes**, and DAG read/write declarations for stages.
- **Spatial scene system** (shared BVH/SVDAG service for render, physics, audio).
- Procedural diff/patch persistence (game-author choice; engine default later).
- C++20 modules (section 12).

## 4. Anti-goals

- No macros in the user-facing API.
- No ordering guarantee is introduced or implied: traversal, events, invocation and memory order are unspecified (**Decided**). Nothing may depend on slot order.
- No virtual call or offset-table load on the hot path for archetype component access.
- No reliance on self-registering static objects (the engine links static libraries; unreferenced object files are dropped).
- No string data for slot names in release binaries unless something uses it at runtime.
- No compile-time blow-up in files that merely *use* an archetype.

## 5. Constraints

- Toolchain: C++23 (`CMAKE_CXX_STANDARD 23`), clang-cl and MSVC, CMake ≥ 4.3.1, Ninja. No static reflection (P2996) on these compilers; do not depend on it. Deducing this (C++23) is available on both but must be compile-checked with the project's versions.
- Existing code to build on: `Engine.ACS` (`Registry`, `Pool`, `hybrid_storage`, `Housekeeping`), `Heliogrim/Actor/Actor.{hpp,cpp}`, `ActorInitializer`, `CachedActorPointer`, `HierarchyComponent` (`_parent`, `_localTransform`, `_boundaries`), `InheritMeta` / `TypedMetaClass`, `access::Structure` / `access::Layout` serialization, `Engine.ACS.Schedule` stages.
- Existing archetype candidates: `StaticGeometryActor`, `BoxShapeGeometryActor`, `SphereShapeGeometryActor`.

## 6. Declaring an archetype

### 6.1 Layout template (**Decided**)

```cpp
using VehicleLayout = ActorLayout<
    Slot<"body", StaticGeometryComponent, Children<
        Slot<"wheels", WheelComponent, Count<4>, Children<
            Slot<"hub", HubComponent>>>,
        Slot<"camera", CameraComponent>>>>;
```

- `Slot<Name, Type, Options...>`; options are tag types matched by kind, not position: `Count<N>` (fixed array, default 1) and `Children<Slot...>` (the explicit child marker).
- The nesting **is** the component parent hierarchy. The first top-level slot is the root component (**Proposal**: exactly one top-level slot is allowed, matching today's single root component).
- Names are a compile-time `fixed_string`. They are used in `consteval` lookup only; verify with a release build that no slot-name strings appear in the binary (except in the serialization file, section 10).
- A fixed count per type is the only form. Variable counts are not allowed in a sealed archetype (**Decided**); such actors are dynamic actors.
- Name lookup: one fold expression over a `constexpr` table computed once per layout (not a recursive per-call search like `StyleAttributes::namedIndex`). Paths for disambiguation: `get<"body/camera">()` (**Proposal**; duplicate names at different depths are otherwise a compile error).

### 6.2 Access

```cpp
get<"camera">()                 // CameraComponent&
get<"wheels">()                 // std::span<WheelComponent, 4> (or equivalent fixed-size view)
get<"wheels">()[i].get<"hub">() // HubComponent& of wheel i
```

`get` compiles to "actor address plus a constant". The element-level `get` on an array member resolves relative to that element's sub-block, so callers never compute nested indices.

### 6.3 Actor class and inheritance (**Decided**)

```cpp
class Vehicle : public InheritArchetype<Vehicle, Actor> {
public:
    using layout = VehicleLayout;
    void tick();                       // plain function in Vehicle.cpp
};

class Tank : public InheritArchetype<Tank, Vehicle> {
public:
    using layout = Extend<Vehicle::layout,
        Slot<"turret", TurretComponent>>;
};
```

- `InheritArchetype<Derived, Base, Rest...>` derives from `InheritMeta<Derived, Base, Rest...>` and adds the archetype machinery, so non-actor classes do not pay for it.
- `Extend<BaseLayout, Slots...>` appends slots (top level or as `Children` of an existing named slot). `Override<"camera", ZoomCamera>` replaces a base slot's type with a derived component type.
- **Slot block before the actor** (**Proposal**, required by 6.4): in a cluster slot, components sit at negative offsets from the actor object; a derived archetype's added components go further in front. Base slot offsets therefore stay constant under actor-field additions and appended slots.

### 6.4 Plain bodies by default, deducing this when overriding (**Decided**)

- If a derived layout keeps every base slot at the same offset (append-only, or an override of equal size and alignment), base-class logic is a **plain non-template function** in the base `.cpp`. It stays correct for all derived archetypes.
- If an `Override` changes a base slot's offset, `Extend` fails with a `static_assert` naming the slot and stating that the base must provide deducing-this bodies.
- A base that wants to allow such overrides writes its logic as `void tick(this auto& self)` in `Vehicle.inl.hpp` (never in public headers). `get` then resolves against the concrete layout. A derived class forwards with `self.Vehicle::tick()`; a `final` derived class may use a plain `void tick()` calling `this->Vehicle::tick()`. Every overridable level provides an `.inl.hpp` that includes its base's `.inl.hpp` first, even when empty, so the chain never breaks.
- The engine detects at compile time whether a base is overridable (**Builder's call** on mechanism, for example a marker in the layout or a trait), so the `static_assert` can name the fix.

### 6.5 Registration and ActorClass (**Decided**)

```cpp
// Tank.cpp
#include <Heliogrim/Actor/ArchetypeDefinition.inl.hpp>
template class InheritArchetype<Tank, Vehicle>;   // one line per archetype
```

- `InheritArchetype` declares `static const TypedActorClass<Derived>& actorClass() noexcept;`. Its single definition lives in `ArchetypeDefinition.inl.hpp`, as a `constinit` function-local static built by `ActorClass::make<Derived>()`.
- The explicit instantiation in one `.cpp` per archetype is where every heavy instantiation happens: layout computation, `ArchetypeOps`, serialization. Other files see only declarations. A missing line or a missing `.inl` include is a link error.
- The typed return (`TypedActorClass<T>`) is checked by the archetype concept: a class deriving with plain `InheritMeta` would inherit its parent's `actorClass()` and fail the check at compile time.
- `ActorClass` becomes its own type (today it is an alias of `MetaClass`). It holds the `MetaClass`, the layout descriptor (slot size, alignment, stride, slot roles and offsets for type-erased users, layout hash) and `ArchetypeOps`. Its constructor is private to the archetype machinery.
- `ArchetypeOps`: function pointers over spans: `construct(span, init)`, `destroy(span)`, `relocate(src, dst, count)`, `tick(span)` per declared hook, `serialize` / `hydrate`, `dumpLayout` / `loadLayout`. One indirect call per span, never per actor.
- Tick hooks are discovered from the type (whether `Derived` declares the hook), not by comparing virtual member-function pointers, which is unspecified ([expr.eq]/5.3).
- **Runtime lookup** (by type id or name, for deserialization, editor and data-driven spawn) returns `None` until a module calls `RegisterActorClass(Tank::actorClass())` in its setup. Template paths (`CreateActor<Tank>()`) reach `Tank::actorClass()` directly and do not need the lookup.
- `Reflect::SubstitudeActorClass` is removed or reduced to forward to `actorClass()` (**Builder's call**).

## 7. Memory: clusters

- One **cluster region** per archetype: a list of chunks. A chunk holds `n` slots of the archetype's stride.
- Slot: `[component block][actor object]`, with component offsets negative from the actor.
- Chunk size: **Builder's call**, measured (start at 16 KiB or one page multiple; large archetypes may need larger chunks). Chunk memory comes from a page allocator so whole chunks can be returned.
- Per chunk: live mask or free list, live count, and the counters needed later by compaction (live/capacity, holes, churn). Only the counters are added now; no policy.
- Parent links between components of one slot are stored as offsets within the slot (**Proposal**), so moving a whole slot needs no pointer fixups for internal links. Today's `HierarchyComponent::_parent` raw pointer must become slot-relative for archetype components or be fixed up on relocation (**Builder's call**, but relocation must work).
- Today's per-type `Pool`s and `hybrid_storage` stay for dynamic actors and non-archetype components.

### 7.0 Component enumeration (**Decided**)

`Actor::getComponents()` stops being a stored `CompactSet` for archetype actors and becomes a range computed from the archetype layout; dynamic actors keep their `CompactSet`. Requirements: at least as fast as `CompactSet` (linear in-cache-line search for small sets, hash lookup above the threshold, linear walk for traversal), and `std::ranges` compatible.

**Proposal**:

- Archetypes: a `constexpr` sorted table of slot offsets (`u32`, of each component's `HierarchyComponent` subobject) shared by all instances in the `ActorClass`. Traversal yields `slotBase + offset`.
- `contains(ptr)`: range check `[slotBase, actor)` plus one bit test in a `constexpr` bitmap of valid start offsets at minimum component alignment (a 1 KiB block at 16-byte alignment is one `u64`). O(1), no search.
- One iterator type for both kinds: `(base, const uintptr_t* entry)`, dereferencing to `base + *entry`. Archetype: `base = slotBase`, entries = offset table. Dynamic: `base = 0`, entries = the `CompactSet`'s stored pointers. `contains` branches once on archetype vs dynamic.
- The range models `random_access_range`, `sized_range` and `view`. `std::ranges::contains` works but is linear; engine code calls the member `contains()`.
- Benchmark against today's `CompactSet` for 1, 4, 16 and 64 components (traversal and `contains`) before migrating callers.

### 7.1 Moving slots (**Decided**)

- Trait `hg::relocatable<T>` in `Engine.Common/Meta/Relocatable.hpp`: true by default for archetype components and actors; a type holding self-pointers or registering its own address elsewhere opts out. C++26 has no standard trivial relocation (P2786 was removed), so this is an engine contract, as in other engines. Byte-copying polymorphic objects is formally undefined; the engine accepts that for opted-in types and the compile checks in section 13 cover both compilers.
- **The move path is the layout scheme** (**Decided**, team insight): the layout descriptor already splits a slot into runs that are memcpy-able and members that need their layout function. `ArchetypeOps::relocate(src, dst, count)` is generated from that same descriptor, going directly from source to destination memory (no intermediate stream): memcpy for relocatable runs, the type's layout load/store or move-construct for the rest, then the relocation table fixes outside references. Layout dump/load (section 10) and relocation share one description, so a type that serializes correctly by layout also moves correctly.
- Full de-materialize/re-materialize (dump to a stream, load elsewhere) stays a valid fallback, for example across processes, but is slower than the direct path and is not used for in-memory compaction.

## 8. Handles and references (**Proposal**, accepted direction)

- **Handle**: 64-bit `(space, index, generation)`. A space is a streaming unit (world cell, procedural chunk) with a paged handle table that is freed as a whole when the space unloads. Generation mismatch resolves to "gone", never to another actor. Exact bit split: **Builder's call**, documented.
- **Space = `core::Level` for now** (**Decided**). `Universe` owns no actors; `Universe::addActor` / `removeActor` forward to the root level, and `core::Level` owns actors (`DenseSet<owner_ptr<Actor>> _actors`). Cluster regions are per archetype **per level**, so unloading a level frees whole chunks and its handle pages. A streaming cell may replace `Level` as the space later.
- **Unmounted actors** (**Proposal**): `SpawnActor` and batch spawn take a level (default: root level) and allocate directly there. `CreateActor` without a level allocates in one global *detached* space; `addActor` relocates the actor into the level's region immediately (safe: an unmounted actor is not registered with any scene, and `addActor` already returns the new `ptr<Actor>`).
- `ActorGuid` / `ComponentGuid` stay the persistent identity for serialization and editor. A handle maps to the guid and back.
- `ActorRef<T>` / `ComponentRef<T>`: handle + cached pointer + relocation epoch. On dereference with a stale epoch, re-resolve through the handle table. `CachedActorPointer` becomes `ActorRef<Actor>` (it was meant for this).
- Raw `ptr<T>` to actors and components are valid only within one frame phase. Debug builds may catch stale use by epoch checks.

## 9. Relocation barrier (interfaces only)

- All moves (later: compaction, de-optimization, shape promotion) are queued during the frame and applied at one barrier: after `ActorHousekeeping`, before the next scene broadcast.
- Applying moves produces a **relocation table** of `(old address, new address)` pairs sorted by old address, then bumps the global epoch.
- Base hooks: `HierarchyComponent` and scene-system models (`RenderSceneSystemModel` and the physics equivalent) get a `relocate(table)` entry point, so each system rebinds its `owner()` pointers in one batch pass.
- This design implements the barrier and the table for **one** producer: none yet beyond tests. A test-only "move chunk" operation proves the mechanism end to end.

## 10. Serialization

- **Structured** (`access::Structure`): `ActorClass::make<T>()` generates serialize and hydrate for archetype slots. Each slot is a named record keyed by its **string slot path** (for example `body/wheels/2/hub`; **Decided**: readable and robust, so developers and tools can traverse serialized structs, for example for analytics) containing the component's existing `access::Structure` output. Hydrate writes into the known slot. This replaces hand-written code such as the guid-matching loop in `StaticGeometryActor.Structured.cpp`. Archetype slots need no stored parent index. Extra (de-optimized) components keep today's generic component sequence.
- **Layout** (`access::Layout`): a `constexpr` layout hash over slot types, offsets, sizes, counts and each component's layout version. A span dump is: header with hash, then per slot either memcpy (trivially copyable components) or the component's layout function, then a fixup table for `ActorRef` / `ComponentRef` fields. Mismatched hash on load fails cleanly.
- Format versioning and migration across layout changes: out of scope; mismatch is an error for now.
- **Existing serialized actors are dropped** (**Decided**): current data is derived from the editor's `UniverseInit` and is regenerated after migration. No legacy hydrate path or converter.

## 11. API to finish

| Function | Today | Target |
|---|---|---|
| `RegisterActorClass(ptr<const ActorClass>)` | `todo_panic` | Adds to runtime lookup; idempotent |
| `RegisterActorClass<T>()` | forwards | `RegisterActorClass(&T::actorClass())` |
| `CreateActor<T>()` / `CreateActor(class_)` | per-type pool | allocates a cluster slot, runs `construct` |
| `CreateActor(class_, serialized_)` | `todo_panic` | slot + `hydrate` |
| `SpawnActor(class_, universe_)` and serialized overload | `todo_panic` | create + register components with the universe scene |
| `CloneActorInto` | `todo_panic` | out of scope unless trivial via serialize/hydrate (**Builder's call**) |
| new: batch spawn | none | `SpawnActors(class_, count, init, universe_)`; single spawn is N=1 |
| `Destroy` | releases components | `destroy` on slot, frees slot at housekeeping |

- **Adding a component to a sealed actor at runtime** is rejected (`assertrt`) until de-optimization exists (**Proposal**, follows from the decided "runtime add = de-optimize"). No hybrid actor in this design. The "extra components" path in section 10 only applies after de-optimization.
- **Scene registration stays per component** (`IComponentRegisterContext::add`) in this design (**Proposal**). Batch spawn is batched in allocation and construction only; span-based scene registration belongs with the spatial-service and scene-system work. Only `relocate(table)` is added to scene-system models.
- `ActorInitializer::createComponent` remains for dynamic actors. For archetypes, components are constructed in place by `construct`; initial values come from the actor constructor or an init callback (**Builder's call**).
- `StaticGeometryActor`, `BoxShapeGeometryActor` and `SphereShapeGeometryActor` are migrated to archetypes as the first users.

## 12. Future: C++20 modules

The `.inl.hpp` chain (6.4) exists only because template bodies must be visible where derived archetypes instantiate them. Module interfaces would provide that without textual includes. A module migration branch exists but needs large restructuring (cyclic dependencies). The build tool is no longer the blocker: the minimum is now CMake 4.3.1, which supports C++20 modules with Ninja. When modules land, replace `.inl.hpp` files with module interface partitions and revisit section 6.4.

## 13. Verification

- Compile checks on clang-cl and MSVC: deducing this with explicit instantiation; `constinit` function-local static; `fixed_string` NTTP; explicit instantiation of `InheritArchetype` alongside `InheritMeta` constructors.
- Tests (`Engine.ACS.Test` or new `Heliogrim.Test` bundle, gtest):
    - layout offsets and sizes for nested, array and extended layouts; `static_assert` fires for an offset-changing override (compile-fail test or documented manual check);
    - `get` paths resolve to the expected component addresses;
    - create, batch spawn and destroy; slot reuse; handle generation invalidates stale refs;
    - span report matches live components for a type, including multiple same-type slots;
    - relocation via the test-only chunk move: `ActorRef` refreshes, parent links stay valid, a mock scene model rebinds;
    - structured round trip and layout round trip of a migrated `StaticGeometryActor`; layout hash mismatch fails.
- Release binary check: slot-name strings appear only through the structured serializer (instantiated in the archetype's defining `.cpp`), not from `get<…>` use.
- Compile-time budget: `-ftime-trace` on an archetype with about 10 slots; record the numbers in the PR.

## 14. Left to the builder

Chunk size, handle bit split, `CloneActorInto`, archetype init-value mechanism, the overridable-base detection mechanism, test bundle placement, and the exact names of helper types, as long as the decided behaviour holds.
