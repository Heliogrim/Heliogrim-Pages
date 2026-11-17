# Actors and Components

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip`, 2026-11-16. Not on `master` yet.
**Modules** (see the [module map](../architecture/modules.md)): `Heliogrim` (public API: [`Actor/Actor`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Heliogrim/Actor/Actor.hpp), [`Actor/Archetype/*`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032/src/Heliogrim/Actor/Archetype), [`Component/HierarchyComponent`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Heliogrim/Component/HierarchyComponent.hpp)), `Engine.ACS` ([`Registry`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.ACS/Registry.hpp), `Archetype/`, `Cluster/`, `Handle/`, `Housekeeping`), `Engine.ACS.Schedule` (actor stages), `Engine.Level` ([`Level`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Level/Level.hpp)), `Engine.Core` (`Universe`), `Engine.Scene.Game` (`SceneComponentQueue`).
**Related**: [Sealed actor archetypes (design)](../architecture/actor-archetypes-design.md), [Actor system (exploration)](../architecture/actor-system.md), PR [#81](https://github.com/Heliogrim/Heliogrim-Engine/pull/81) (archetypes), PRs [#176](https://github.com/Heliogrim/Heliogrim-Engine/pull/176) and [#177](https://github.com/Heliogrim/Heliogrim-Engine/pull/177) (scene removal fixes), PR [#76](https://github.com/Heliogrim/Heliogrim-Engine/pull/76) (`Arci<T>`).

## Purpose

An actor is a thing in the world: a guid, a label and a tree of components. Components are `HierarchyComponent`s; the ones that derive from `SceneComponent` are mirrored into scene systems (render, physics).

There are two kinds of actor:

- **Archetype actors** (sealed). The C++ class declares a fixed component tree as a template layout. Actor and components live in one slot of a cluster region; slots of the same archetype are packed in 16 KiB chunks. Components are reached by name at compile time (`get<"geometry">()`). References survive relocation through generational handles. `StaticGeometryActor`, `BoxShapeGeometryActor` and `SphereShapeGeometryActor` are archetypes.
- **Dynamic actors**. The older path: the actor lives in a per-type `Pool`, every component in its own per-type pool, and the actor holds a `CompactSet` of component pointers. Components are added at runtime with `addComponent`. `CameraActor`, the light actors and every `CreateActor()` actor are dynamic.

What the system does not do yet: run actor ticks, compact regions, move a sealed actor out of its cluster when it needs an extra component, or clone actors. See [Limits](#limits-and-known-issues).

## Where it sits

```hg-diagram
flowchart LR
    USER["Game / editor code<br/>CreateActor, SpawnActor(s)"]
    REG["Engine.ACS Registry<br/>pools, cluster regions, handles"]
    LVL["core::Level<br/>owns actors, one space"]
    UNI["core::Universe<br/>levels + scene"]
    Q["SceneComponentQueue<br/>(GameScene register context)"]
    SYS["Scene systems<br/>render, physics"]
    HK["ActorHousekeeping stage<br/>releases, reclaim, relocation barrier"]
    USER -->|"create"| REG
    USER -->|"addActor"| LVL
    LVL -->|"moveActor into level space"| REG
    UNI -->|"commitLevel"| LVL
    LVL -->|"registerComponents"| Q
    Q -->|"commit on broadcast"| SYS
    HK --> REG
    HK -->|"relocate(table)"| SYS
```

The `Registry` (reached through `Engine::getEngine()->getActors()->getRegistry()`) allocates and frees. A `Level` owns the actors that are mounted in it. A `Universe` owns levels (as [`Arci<Level>`](https://github.com/Heliogrim/Heliogrim-Engine/pull/76), the intrusive refcount; `Level` derives from `ArcFromThis<Level>`) and one scene. Components reach the scene through the scene's register context, a queue that is applied when the scene broadcasts.

## Vocabulary

| Type | What it is |
|------|------------|
| `Actor` | base class of every actor; guid, label, root component, owning level and universe |
| `InheritArchetype<Derived, Base>` | base for an archetype actor: `InheritMeta` plus `actorClass()` and `get<"path">()` |
| `ActorLayout`, `Slot`, `Count`, `Children` | the compile-time component tree of an archetype ([`Archetype/Layout.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.ACS/Archetype/Layout.hpp)) |
| `Extend`, `At`, `Override`, `Overridable` | derive a layout from a base layout |
| `ActorClass` / `TypedActorClass<T>` | everything captured from the templates: meta class, slot shape (`ClusterDesc`), offsets, `ArchetypeOps`, layout hash |
| `ArchetypeOps` | type-erased function pointers over spans of slots: `construct`, `destroy`, `relocate`, `tick`, `serialize`, `hydrate`, `dumpLayout`, `loadLayout` |
| `ClusterRegion` | slots of one archetype in one space, in chunks |
| `Handle` | 64 bit `(space, generation, index)` |
| `ActorRef<T>`, `ComponentRef<T>` | handle plus cached pointer, re-resolved once per epoch |
| `VolatileActor<T>` | owning pointer to an actor that is not mounted; destroys the actor when dropped |

## How it works

### Declaring an archetype

The layout nests slots; the nesting is the parent hierarchy, and the single top-level slot is the root component. From [`BoxShapeGeometryActor.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Heliogrim/Actor/Geometry/BoxShapeGeometryActor.hpp):

```cpp
class BoxShapeGeometryActor :
	public InheritArchetype<BoxShapeGeometryActor, Actor> {
public:
	using this_type = BoxShapeGeometryActor;
	constexpr static type_id typeId { "BoxShapeGeometryActor"_typeId };

	using layout = engine::acs::ActorLayout<
		engine::acs::Slot<"collision", BoxShapeCollisionComponent, engine::acs::Children<
			engine::acs::Slot<"geometry", BoxShapeGeometryComponent>>>>;
	// ...
};
```

Rules the templates enforce with `static_assert`:

- `ActorLayout` takes exactly one root slot, and the root cannot be an array.
- Slot options are `Count<N>` (1 to 65535, default 1) and `Children<Slot...>`, at most one of each, in any order. Names are non-empty and contain no `/`.
- Every slot type must derive from `HierarchyComponent` and be constructible from `(ComponentGuid, CachedActorPointer, ptr<HierarchyComponent> parent)`.
- A name may appear twice in different branches; `get<"x">()` then fails as ambiguous and you write the path (`get<"body/camera">()`). Two slots with the same full path fail to compile.

`get<"name">()` returns `Type&` for a single slot and a fixed-size view for a `Count<N>` slot. A slot inside an array is reached through its element: `get<"wheels">()[i].get<"hub">()`. Each access compiles to "actor address minus a constant".

Derived archetypes are always a separate archetype. From the test archetypes in [`Heliogrim.Test/TestArchetypes.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Heliogrim.Test/TestArchetypes.hpp):

```cpp
class TestTank :
	public InheritArchetype<TestTank, TestBody> {
public:
	using this_type = TestTank;
	constexpr static type_id typeId { "TestTank"_typeId };

	using layout = Extend<TestBody::layout, Slot<"turret", TurretStub>>;
	// ...
};
```

`Extend` places added slots in front of the base block (`[added slots][base block][actor]`), so every base slot keeps its distance to the actor and a plain, non-template function of the base (such as `TestBody::touchCamera`) stays correct for the derived class. `Override<"path", NewType>` replaces a slot's type with a derived type. If that moves any base slot, `Extend` fails with "Override changes a base slot's actor-relative offset: the base must provide deducing-this bodies (Overridable)". The base then wraps its layout in `Overridable<...>` and writes its logic as `void tick(this auto& self)` in an `.inl.hpp` (see `TestOverridable` / `TestOverrider`).

### Defining an archetype: one `.cpp`

All heavy template work happens in exactly one translation unit per archetype. It includes `ArchetypeDefinition.inl.hpp` and explicitly instantiates the base. From [`StaticGeometryActor.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Heliogrim/Actor/Geometry/StaticGeometryActor.cpp):

```cpp
#include "StaticGeometryActor.hpp"

#include "../Archetype/ArchetypeDefinition.inl.hpp"
#include "../../Component/Scene/Geometry/StaticGeometryComponent.Layout.hpp"

using namespace hg;

StaticGeometryActor::StaticGeometryActor(cref<ActorInitializer> initializer_) :
	InheritArchetype(initializer_) {}

nmpt<StaticGeometryComponent> StaticGeometryActor::getStaticGeometryComponent() noexcept {
	return &get<"geometry">();
}

template class hg::InheritArchetype<StaticGeometryActor, Actor>;
```

The explicit instantiation defines `actorClass()`, a `constinit` function-local static built by `ActorClass::make<T>()`. A missing instantiation line or a missing include is a link error, not a runtime one. The component `.Layout.hpp` includes are needed because `make` also generates the layout dump: every slot type that is not trivially copyable needs an `access::Layout<T>` specialisation visible here.

### Registration

`RegisterActorClass` adds a class to the runtime lookup used by `FindActorClass(type_id)`. It is idempotent and returns `false` for `nullptr` or when another class already holds the type id. Template paths (`CreateActor<T>()`, `T::actorClass()`) do not need it. The editor registers its archetypes at boot in [`Editor.Boot/Boot/ActorInit.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Editor.Boot/Boot/ActorInit.cpp):

```cpp
void editor::boot::initActorClasses(_In_ [[maybe_unused]] ref<engine::ActorModule> module_) {
	std::ignore = RegisterActorClass<StaticGeometryActor>();
	std::ignore = RegisterActorClass<BoxShapeGeometryActor>();
	std::ignore = RegisterActorClass<SphereShapeGeometryActor>();
}
```

Loading a level file uses a separate table: the serialization module's actor schemes. An archetype that should load from a level also needs `module_.addActorScheme(T::typeId, MakeArchetypeFnSet(&T::actorClass()))` (see `Editor.Boot/Boot/SerializationInit.cpp`). `Engine.Level` cannot resolve actor classes itself, so the scheme carries the class pointer.

### Slot memory

```hg-diagram
flowchart LR
    subgraph SLOT["one slot (stride bytes)"]
        direction LR
        PAD["front padding"] --> TUR["turret<br/>(added by Extend)"] --> BASE["base block:<br/>body, wheels[4] + hubs, camera"] --> ACT["actor object<br/>at actorOffset"]
    end
```

`LayoutInfo<Layout, Actor>` computes everything at compile time: entry offsets (parents before children, in tree order), `actor_offset` (the end of the component block), `slot_stride`, the minimum component alignment and a start bitmap. Alignment padding goes in front, so an entry's distance to the actor depends only on the layout.

A `ClusterRegion` hands out raw slots; it never constructs anything. Chunks are `max(16 KiB, stride rounded up to 4 KiB)`, aligned to at least a cache line, with a live mask, a retired mask, one handle per slot and counters (`live`, `capacity`, `holes`, `churn`) that no policy reads yet. There is one region per archetype per space, and one space per `Level` (acquired with the first archetype actor) plus the global detached space `0`.

`ArchetypeOps::construct` builds components in entry order with a new `ComponentGuid`, an owner pointer and the parent pointer, then the actor with an `ActorInitializer` whose `_archetype` is set. `Actor`'s constructor uses that to find its root component (entry 0) in front of itself. `destroy` runs the actor destructor first, then components children-first.

`Actor::getComponents()` returns a `ComponentRange`. For an archetype actor it walks the class's shared offset table from the slot base; `contains(ptr)` is a range check plus one bitmap test. For a dynamic actor it walks the `CompactSet`.

### Handles, references and the epoch

```cpp
// Generational handle; bit layout (msb to lsb): 12 bit space | 20 bit generation | 32 bit index.
```

Each space has a paged `HandleTable` (4096 entries per page). Releasing a handle bumps its generation, so a stale handle resolves to `nullptr`, never to another actor. An index that reaches the last generation is retired, and a reused space id starts its generations above every earlier one.

`ActorRef<T>::of(actor)` looks up the actor's handle; `get()` returns `Opt<ref<T>>` and re-resolves through the registry only when the global `Epoch` changed since the last call. `ComponentRef<T>` stores the owner's handle plus the component's byte offset from the actor; `get()` checks that the offset is a real component offset of the actor's class. Both return `None` for dynamic actors, because those have no handle.

The epoch is bumped by every archetype move (`moveActor`), every archetype destroy, every `releaseSpace`, and by housekeeping when slots were reclaimed or moved.

### Lifecycle

```hg-diagram
sequenceDiagram
    participant U as Caller
    participant R as Registry
    participant L as Level
    participant Q as SceneComponentQueue
    participant S as Scene systems
    participant H as ActorHousekeeping
    U->>R: CreateActor<T>() (detached space)
    U->>U: configure via get<"...">()
    U->>L: addActor(VolatileActor)
    L->>R: moveActor(actor, level.space())
    R-->>L: new address (old slot retired, epoch bumped)
    L->>Q: registerComponents (add per component)
    Note over Q,S: GameScene::broadcast commits the queue
    Q->>S: add(meta, batch)
    U->>L: removeActor(actor)
    L->>Q: unregisterComponents (remove per component)
    L->>R: moveActor(actor, detachedSpace)
    U->>R: drop VolatileActor: destroy now, retire slot
    H->>R: housekeep: barrier moves, commit releases, reclaim slots
    H->>S: relocate(table) per moved chunk
```

**Create.** `CreateActor<T>()` on an archetype allocates one slot in the detached space and runs `construct`. It does not touch any scene. `CreateActor(class_, SerializedActor)` first checks that the record has the type, guid, label and components keys and the right type id, then creates and hydrates; a rejected record never holds a slot.

**Mount.** `Level::addActor` relocates an archetype actor from another space into the level's region (`ops.relocate`, then `retire` on the old slot), inserts it into the level's actor set, sets its level and, if the level is committed to a universe, registers its components. It returns the new address. `hg::Universe::addActor` does the same on the root level and returns `ActorRef::of(...)`.

**Spawn.** `SpawnActors(class_, count, init, universe, level = None)` allocates directly in the level's space, so mounting needs no move. Construction is batched per contiguous run of slots; `init(actor, index)` runs per actor before it is mounted; scene registration stays per component. `SpawnActor(class_, universe)` is `SpawnActors` with one actor on the root level.

**Register.** Components are not added to scene systems directly. `Actor::registerComponents` calls `IComponentRegisterContext::add` per component (archetype entries are already ordered parent before child). For a `GameScene` the context is its `SceneComponentQueue`, which keeps only `SceneComponent`s, groups them by meta class under a `SpinMutex`, and applies removals then additions in `commitChanges`, called from `GameScene::broadcast` and the queue's destructor. `Universe::commitLevel` registers all actors of a level added later.

**Unmount.** `Level::removeActor` unregisters the components (queued), drops the actor from the level and moves an archetype actor to the detached space, so it outlives the level. It returns the actor as `VolatileActor`. `hg::Universe::dropActor` removes and destroys in one step.

**Destroy.** Dropping a `VolatileActor` calls `VolatileActor<Actor>::destroy`, which asserts (debug only) that the actor is not in a universe. An archetype actor is destroyed at once: destructors run, the handle is released and the slot is *retired*, not freed, so a raw pointer taken earlier in the frame never aliases a new occupant. A dynamic actor hands each component to `Housekeeping` for deferred release and erases the actor from its pool at once.

**Housekeeping.** `ActorHousekeepingStage` runs after `ScenePostProcess` and `ActorTickPostPhysics`, on the critical lane, writing `Registry` and `SceneBase`. It calls `Registry::housekeep`:

1. `RelocationBarrier::apply()`: queued chunk moves, highest chunk first per region; returns one `RelocationTable` per move.
2. `Housekeeping::commit()`: releases pending dynamic components from their pools, then `reclaimSlots()` makes retired slots claimable and frees chunks left empty.
3. Each table goes to every scene system of every live universe via `SceneSystemBase::relocate(table)`. The render and physics systems remap their models' owner pointers with `RelocationTable::lookup`.
4. The epoch is bumped if anything was reclaimed or moved.

**Shutdown.** `core::Universe::~Universe` uncommits every level (queues component removals). `Level::~Level` destroys every actor it still owns and releases its space, which frees the chunks and handle pages as a whole. `Registry::~Registry` commits housekeeping one last time.

### Relocation

Only one producer exists: `Registry::debugMoveRequest(space, class, chunk)` builds a `MoveRequest` that empties one chunk into the region's other chunks; `registry.relocation().enqueue(request)` queues it for the next housekeeping. `ops.relocate` memcpy's the slot when every slot type is `relocatable_v` (the default for every type), else move-constructs the non-relocatable components. It then move-constructs the actor's label and component set over their byte copies, and re-stamps every component's owner and parent pointer from the layout instead of offsetting them.

Mount and unmount moves (`moveActor`) do not go through the barrier and produce no table: they happen while the actor is not registered with any scene.

## Walkthrough: define and spawn an actor

1. Header: derive from `InheritArchetype<MyActor, Actor>`, declare `typeId`, `using layout = ActorLayout<...>` and a constructor taking `cref<ActorInitializer>`. Include only `Layout.hpp`, `InheritArchetype.hpp` and the component headers.
2. Source: include `ArchetypeDefinition.inl.hpp` and the component `.Layout.hpp` files, define the constructor (forward to `InheritArchetype(initializer_)`), and end with `template class hg::InheritArchetype<MyActor, Actor>;`.
3. Reconfigure CMake if the files are new (bundles are globbed).
4. If the actor is loaded from data or found by type id, call `RegisterActorClass<MyActor>()` and add an actor scheme at boot.
5. Spawn. The editor's geometry spawn, from [`Editor.Scene.Actions/SpawnGeometryActor.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Editor.Scene.Actions/SpawnGeometryActor.cpp), creates detached, configures, then mounts:

```cpp
auto volatileActor = CreateActor<StaticGeometryActor>();
auto* const component = &volatileActor->get<"geometry">();

/* Configure components */

const auto meshQuery = Heliogrim::assets().find<StaticGeometryAssetHandle>(assetGuid_);
::hg::assertrt(meshQuery.flags & AssetDatabaseResultType::eSuccess);
component->setStaticGeometry(meshQuery.value);
// ... material

volatileActor->getRootComponent()->getLocalTransform().location() = location_;
auto actorRef = universe.addActor(VolatileActor<> { ::hg::move(volatileActor) });
```

For many actors, spawn straight into the level and configure in the callback (from [`Heliogrim.Test/ArchetypeSpawn.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Heliogrim.Test/ArchetypeSpawn.cpp)):

```cpp
auto actors = hg::await(
	SpawnActors(
		&Body::actorClass(),
		count,
		[](ref<Actor> actor_, const size_t index_) {
			static_cast<ref<Body>>(actor_).get<"body">().mass = index_;
		},
		_universe
	)
).value();
```

Keep the returned `ActorRef`s, not pointers. To despawn, resolve the ref and pass the pointer to `universe.dropActor(...)`.

## Pitfalls

- **Pointers die at mount.** `addActor` moves a detached archetype actor. The `VolatileActor`, and every component pointer taken before the call, point at a retired slot afterwards. Use the returned pointer or `ActorRef`.
- **Refs to detached actors never resolve.** `ActorRef::get()` returns `None` for a detached-space handle by design, and the handle changes on mount. Take the ref after mounting.
- **`Universe::addActor` returns `None` for dynamic actors.** They have no handle. Editor code that spawns lights or cameras keeps the guid and looks the actor up in its pool instead.
- **No runtime component changes on archetypes.** `addComponent`, `removeComponents` and `destroyComponent` panic on a sealed actor in every build type (`rejectSealed`), until de-optimisation exists.
- **Raw pointers are valid for one frame phase.** Housekeeping may reclaim, and a barrier move may relocate, any slot. Cache an `ActorRef` / `ComponentRef` across frames. There is no debug check that catches a stale raw pointer.
- **Self-pointers break relocation.** `relocatable_v<T>` is true for every type unless specialised to `std::false_type`. A component that stores its own address, or registers it elsewhere, must opt out, or it is memcpy'd.
- **Scene removals are by address.** The queue may apply a removal after the slot was retired, or after its chunk was freed by housekeeping. A scene system's `remove` must match by address and never dereference the component or its owner (the fix in [#176](https://github.com/Heliogrim/Heliogrim-Engine/pull/176)).
- **Single inheritance only.** Construction and type-erased offsets assume the `HierarchyComponent` subobject sits at offset 0 of each component and `Actor` at offset 0 of the archetype (`shortcut:` in `ArchetypeDefinition.inl.hpp`, checked by `assertd`).
- **Not thread-safe.** `ClusterRegion`, `HandleTable` and the registry's archetype paths take no lock. Only the scene queue and the dynamic-component release list are locked. Spawn, mount and destroy from one place at a time, outside the housekeeping stage.
- **Teardown order.** A component release that arrives while `Housekeeping::commit` runs trips a debug assert ("teardown overlaps the housekeeping stage"). The scheduler must stop after the modules that own actors.

## Debugging

- `registry.handleOf(actor)` gives the handle; `handle.space()` tells detached (`0`) from mounted. `registry.resolve(handle)` and `resolveComponent(handle, offset)` show whether a ref should resolve.
- `actor.getArchetype()` is `nullptr` for a dynamic actor.
- `registry.region(space, class)->stats(chunk)` and `chunkCount()` show live slots, holes and churn per chunk; `forEachChunk` walks the live masks.
- `registry.forEachSpan<T>(fn)` visits every live component of type `T` (or derived, when `T` has its own meta class) as strided `ComponentSpan`s across all levels, detached actors excluded.
- A `layout_hash` mismatch makes `loadLayout` return `false`; a missing key makes `CreateActor(class, serialized)` return a null actor instead of crashing.
- "Tried to register actor components in a mismatching scene." is logged when an actor already bound to one universe is registered with another.

## Limits and known issues

- **Ticks do not run.** `ops.tick` is generated when the archetype (or a base) has `tick()`, but `ActorTickStage` only reads `getComponents()` (`// TODO: Tick actor`); nothing calls it.
- **No compaction.** The barrier and tables work end to end, but the only move producer is `debugMoveRequest`, used by tests.
- **`CloneActorInto` is `todo_panic`.** `removeComponents<T>()` without an argument is too.
- **Chunks come from the global heap** (`operator new`), not a page allocator, so freed chunks do not return to the OS. A `shortcut:` notes this.
- **Linear scans.** Finding a free chunk scans the region, and `locate` (behind `handleOf`, `ActorRef::of`, `moveActor`, destroy) scans every space. Both are `shortcut:`s for a few hundred chunks / a few dozen spaces.
- **20 bit generations.** An index is retired after about one million reuses; long sessions with heavy churn on one level will leak indices slowly.
- **Components still hold `CachedActorPointer`**, a guid plus raw pointer, re-stamped on relocation; it was not replaced by `ActorRef`.
- **Scene registration is per component**, not per span, even for batch spawns.
- **Dynamic actors** keep the old pools, guid lookup and component-by-component release.

## Changing it

- Layout rules: `Engine.ACS/Archetype/Layout.hpp` (user templates) and `LayoutInfo.hpp` (offsets, paths, `Extend` / `Override` checks). Name lookup for `get`: `Heliogrim/Actor/Archetype/InheritArchetype.hpp`.
- Generated operations: `ActorClass::make` in `ArchetypeDefinition.inl.hpp`; serialization in `ArchetypeStructured.inl.hpp` (records keyed by slot path such as `body/wheels/2/hub`) and `ArchetypeLayout.inl.hpp` (binary dump with `ActorRef` / `ComponentRef` fixups). A new field that affects layout must go into `layout_hash`.
- Storage and references: `Engine.ACS/Cluster/*`, `Engine.ACS/Handle/*`, and the archetype section of `Registry.cpp`. Mount, unmount and spawn: `Engine.Level/Level.cpp` and the free functions at the end of `Heliogrim/Actor/Actor.cpp`.
- A new scene system that stores component or owner pointers must override `SceneSystemBase::relocate(table)`.
- Tests: `Heliogrim-Engine.ACS.Test` (layout offsets, `Extend`, cluster region, handle table, pool) and `Heliogrim-Heliogrim.Test` (archetype access, spawn and batch spawn, relocation through the barrier, structured and layout serialization, `ComponentRange` and its benchmark against `CompactSet`, the `SceneComponentQueue` stress test).
