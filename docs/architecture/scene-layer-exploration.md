# Scene Layer and Spatial Index (Exploration)

**Status**: exploration. Technical revision and comparison; nothing here is a decision.

**Origin**: owner request 2026-11-14 during W02.11 (see the [engine loop exploration](engine-loop-exploration.md) 5.2a): how the scene should mediate changes between systems (render, physics, audio, network, UI, user code, editor), whether a central spatial index ("SVBVH") fits, and at what cost. Written by a research agent briefed with the engine facts, ten scenarios and the criteria, without either side's preference; primary sources only.

Conventions:

- Engine code was read at `origin/feat/wip`, which resolved to `eb700a82` on 2026-11-14. Paths are relative to `X:\Dev\C++\Heliogrim-CLion`. "By reading" means the code was read, not built or run.
- External claims are marked **[verified]** (read in the source by me) or **[unverified]**. Where only part of a source could be read, the mark says which part.
- Pages docs are cited as context, not as decisions.
- No benchmark from another engine is treated as transferable. Where a number is quoted, its setup is named.

---

## 1. Current state in the engine

### 1.1 Scene and scene systems

- `Scene<Systems...>` holds its systems in a tuple plus a dense pointer array. `broadcast`, `update` and `postprocess` loop over the systems serially, and `add`/`remove` fan out to every system (`src/Engine.Scene/Scene.hpp:239-276`).
- `SceneSystemBase` has `prepare/cleanup`, `broadcast/update/postprocess(flags)`, `add/remove(MetaClass, span)`, `clear` and `relocate(RelocationTable)` (`src/Engine.Scene/SceneSystem.hpp:29-61`).
- Two scene types exist: `GameScene = Scene<PhysicsSceneSystem, RenderSceneSystem>` (`src/Engine.Scene.Game/GameScene.hpp:11-13`) and `PreviewScene = Scene<RenderSceneSystem>` (`src/Engine.Scene.Preview/PreviewScene.hpp:7-9`).
- There is no audio, network or spatial scene system. `Engine.Audio` contains the module and importers only; `Engine.Network` is an empty module (`src/Engine.Network/Network.hpp`).

### 1.2 Structural changes already go through a queue

- `SceneComponentQueue` keeps two maps `MetaClass -> Vector<ptr<SceneComponent>>` (create, remove) under a `SpinMutex` (`src/Engine.Scene.Game/SceneComponentQueue.hpp:50-53`).
- Producers are `Actor::scheduleComponentRegister/Removal` (`src/Heliogrim/Actor/Actor.cpp:118-124`), `Level::addActor` (`src/Engine.Level/Level.cpp:92-95`) and `Universe::commitLevel` (`src/Engine.Core/Universe.cpp:35-42`).
- `GameScene::broadcast` commits the queue at both broadcast phases, removes before adds, then calls the systems (`src/Engine.Scene.Game/GameScene.cpp:6-9`, `SceneComponentQueue.hpp:56-93`).
- So the engine already has a small structural change log: add and remove only, raw pointers, one implicit consumer set, no cursor, no step id, no bound.

### 1.3 Value changes are polled

- Both systems' `broadcast()` are empty (`src/Engine.Render.Scene/RenderSceneSystem.cpp:38`, `src/Engine.Physics.Scene/PhysicsSceneSystem.cpp:62`). The phase flags reach the systems but neither `update()` reads them.
- `RenderSceneSystem::update` walks every model of every type and calls `model.update` (`RenderSceneSystem.cpp:40-54`). `StaticGeometryModel::update` compares the geometry handle and each material against the component, then rewrites the instance transform unconditionally: the guard is `static bool isDirty = true`. It maps and unmaps the buffer page per model (`src/Engine.Graphics.Scene.Model/StaticGeometryModel.cpp:80-144`).
- `PhysicsSceneSystem::update` calls `SetPositionAndRotationWhenChanged` for every model (`PhysicsSceneSystem.cpp:64-68`, `src/Engine.Physics.Scene.Model/BoxShapeCollisionModel.cpp:65-77`).
- `SceneUpdateStage` is mounted twice per frame, pre and post physics (`src/Engine.Scene.Schedule/ScenePipeline.cpp:36-49`). Both full walks therefore run twice per frame, and the post-physics walk pushes back to Jolt the transform that readback just copied out.
- `PhysicsSceneSystem::readback` writes the body transform into every owning component, with no filter for static or sleeping bodies (`PhysicsSceneSystem.cpp:70-74`, `BoxShapeCollisionModel.cpp:79-87`).
- Per-frame cost today is proportional to the number of models, not to the number of changes.

### 1.4 Lifetime

- Models hold a raw `nmpt<SceneComponent> _owner` (`src/Engine.Render.Scene/RenderSceneSystemModel.hpp:42`, `src/Engine.Physics.Scene/PhysicsSceneSystemModel.hpp:43`). `relocate` rebinds it at `ActorHousekeeping` (`src/Engine.ACS.Schedule/ActorHousekeepingStage.cpp:33-45`).
- Render removal is a scan of all models against the batch; the code comments it as naive (`RenderSceneSystem.cpp:87-105`). It marks the model deleted, and `postprocess` erases it. `ScenePostProcess` runs after `RenderTick` in the same frame (`src/Engine.Graphics.Schedule/RenderTickStage.cpp:131-141`). This is only safe because render runs inside the frame.
- Likely defect, by reading: `PhysicsSceneSystem::postprocess` erases models whose `owner() == nullptr` (`PhysicsSceneSystem.cpp:76-84`), but nothing in `Engine.Physics.Scene*` sets `_owner` to null (a `git grep` for `_owner` finds only the constructor and `relocate`). Destroyed physics models would then never be erased, and the next `update()` would dereference `_body`, which `destroy` set to `None` (`BoxShapeCollisionModel.cpp:65-77, 100-110`). Not confirmed by a run.
- Component memory is released through `Registry::releaseActorComponent -> Housekeeping::storePendingRelease` (`src/Engine.ACS/Registry.cpp:32-34`). Whether a removal queued after the last broadcast of a frame can be committed after that release was not traced.
- Generational handles exist: `acs::Handle` with 12-bit space, 20-bit generation and 32-bit index, plus a global `Epoch` (`src/Engine.ACS/Handle/Handle.hpp`, `Epoch.hpp`). The scene systems do not use them.

### 1.5 Render replica

- The replica is partial. Models copy the transform into GPU instance memory and hold resource handles, but they also dereference the live component: `capture()` reads `_owner->getUniverseMatrix()` (`StaticGeometryModel.cpp:156-158`).
- Passes iterate the registry directly every frame without culling, for example `MatTestPass.cpp:139-140` and `TmpDirectionalShadowPass.cpp:176, 484`. `Engine.Reflow/Widget/Viewport.cpp:260` reads camera models the same way.
- `RenderTick` declares reads of `SceneBase` and `WindowManager` and a write of `RenderSceneManager` (`RenderTickStage.cpp:122-141`).
- Render graph across frames, partly checked: `RenderTarget` keeps one `RenderPass` per in-flight slot (`otfCount` 1 or 2), reuses it across frames and gates it by a per-pass fence (`src/Engine.Graphics/RenderTarget.cpp:290, 315-331, 396-403`). `SymbolFlagBits` has only `eTransient`; every predefined symbol uses `eUndefined` with `eGlobal` scope (`src/Engine.Graphics.RenderGraph/Symbol/Symbol.hpp:40-43`, `src/Engine.Graphics.Render.Predefined/Symbols/*.cpp`). A grep found no history or previous-frame mechanism. State is retained per in-flight slot, not as an N-frame history. `RenderPass` and `Renderer` internals were not read.

### 1.6 SceneWalker: prototype, not used

- `SceneWalker::operator()(SceneView)` only updates the walk filters; the traversal calls are commented out (`src/Engine.Graphics.Render.Graph.Scene/SceneWalker.cpp:61-114`). `stream()` is protected and has no caller.
- `FrustumCullingFilter::operator()` returns `false`; its body is commented out (`Filter/FrustumCulling.cpp:11-24`).
- The only use site, `DepthPrePass::iterate`, sits inside a block comment (`src/Engine.Graphics.Render.Subpass/Impl/DepthPrePass.cpp:68-85`).
- `src/Engine.Scene/Storage/SceneNodeStorage.hpp` (1823 lines) has no user at this ref.
- Reusable from it: the split into walk filters (node-level cull with a checksum), hook filters (per-model type filter) and a batched `stream` over model spans. That is the shape of a filtered subscription, but none of it executes.

### 1.7 Transforms and spatial queries

- `HierarchyComponent::getUniverseTransform/Matrix` accumulate up the parent chain on every call (`src/Heliogrim/Component/HierarchyComponent.cpp:187-233`). There is no cache and no dirty flag, so the result is never stale. The cost is O(depth) per call, and setters produce no notification.
- Some component state is public and bypasses any setter. `BoxShapeCollisionModel` reads `origin->extent` directly (`BoxShapeCollisionModel.cpp:30-32`).
- No spatial query exists. `git grep` finds no `NarrowPhaseQuery`, `BroadPhaseQuery`, `CastRay`, ray cast or picking code under `src`. The only structures are Jolt's internal broadphase and flat model vectors.

### 1.8 Frame and task graph

- Access keys form a closed set of seven types; one `SceneBase` key covers the scene and all systems, and `PhysicsSceneSystem` has its own (`src/Engine.Scheduler/Graph/AccessResources.hpp`).
- The builder rejects unordered pairs with write/read or write/write overlap (`src/Engine.Scheduler/Graph/TaskGraph.cpp:148-168`). The frame is a strict chain today (Pages `task-graph-design.md` section 8).
- `CompositePipeline` restarts the whole graph when the last node completes (`src/Engine.Scheduler/Pipeline/CompositePipeline.cpp:276-285, 309-328`). There is no sub-graph loop, so "0..n fixed steps per frame" has no carrier yet.
- Completion is per stage, through `pending` counters per node. `JoinCounter` and `Signal` exist (`src/Engine.Scheduler/Waitable/`) but no stage uses them.
- Each scene stage statically dispatches one repetitive task per universe context; `dynamicDispatch` is empty in all of them.
- Physics steps once per frame with the frame delta on `JPH::JobSystemSingleThreaded` and builds a 10 MB temp allocator per tick (`src/Engine.Physics.Schedule/PhysicsTickStage.cpp:28-51`).
- The three actor tick stages and both physics callback stages are stubs (`src/Engine.ACS.Schedule/ActorTickStagePrePhysics.cpp:42-47`, `ActorPhysicsStageOverlap.cpp:21-23`).

---

## 2. What the sources say

**Bevy change detection** (docs.rs, bevy 0.20.1)

- A component records the tick when it was added and when it was last mutably dereferenced. [verified]
- `Changed<T>`: "simply mutably dereferencing a component is considered a change"; values are not compared. [verified]
- `Changed<T>` is not an archetype filter: a query matching a million entities iterates all of them even if none changed. [verified]
- Changes older than `MAX_CHANGE_AGE` (3,258,167,296 ticks) are no longer detected; a periodic scan clamps ticks. [verified]
- Removal is not covered by ticks. `RemovedComponents<T>` works like a message reader over a buffer that `App::update` clears. [verified] That a system running less often than the clear misses removals is my inference, not stated on the page.
- Lifecycle hooks and observers (`Add`, `Insert`, `Discard`, `Remove`, `Despawn`) exist; `Remove` runs before the data is gone. [verified]

**Bevy pipelined rendering and extract** (docs.rs)

- Rendering of frame N runs while frame N+1 simulates. Extract copies main-world data to the render world on the main thread, and it runs again only when both the main schedule and the render schedule have finished. [verified]
- The extract schedule "should be kept as short as possible". [verified]
- How the retained render world maps and despawns entities was not on the pages read. [unverified]

**Unity Entities** (manual 1.3)

- Each chunk stores, per component type, the global version at the last writable access. "This doesn't guarantee that anything has changed, only that it might have changed." [verified]
- Change filters work on whole chunks and only check whether a system that declared write access ran. Hence the advice to declare read-only access wherever possible. [verified]
- Versions are 32-bit, wrap, and are compared by signed difference. [verified]
- Netcode for Entities ghost optimisation pages: not reachable (404). [unverified]

**Unreal Engine**

- Threaded Rendering: the render thread is "a frame or two behind the game thread". Game and render sides own separate objects (`UPrimitiveComponent` and `FPrimitiveSceneProxy`), and neither may touch the other's memory. [verified]
- Updates travel as render commands enqueued from the game thread; dynamic data is copied per frame and ownership passes to the render thread. [verified]
- Destruction is gated by a render command fence (`BeginDestroy`, `IsReadyForFinishDestroy`) or deferred cleanup. [verified]
- The game thread blocks at the end of each tick until the render thread is within one or two frames. [verified] This is producer-side backpressure.
- Actor Ticking: tick groups are barriers; `TG_PrePhysics` sees physics data "one frame old"; prerequisites add edges inside a group; actors in the same group may tick in parallel. [verified]
- MassEntity overview: fragments, archetypes, chunks; composition changes go through a command buffer "batch-processed at the end of the current processing batch". The page says nothing on change detection, observers or threading. [verified]

**Flecs** (flecs.dev manuals)

- Observers run "when the operation that triggered the observer happens, on the thread where the operation is executed"; with deferred operations, at sync points. [verified]
- "A basic event queue is always going to outperform observers" for simple cases; hooks are much cheaper than observers; processing events on multiple threads is listed as something observers do not do easily. [verified]
- `OnSet` does not fire when a system writes a component directly, unless `modified` is called. [verified]
- Ordering between several observers is not specified in the part read (first 100k characters). [verified absence]
- Query change detection is per table and only for cached queries. Iterating a table with inout/out terms marks it dirty unless the iteration is skipped. [verified from the code comments of that section; its prose was not in the fetched range]

**Bungie, GDC 2015**

- Genova, "Multithreading the Entire Destiny Engine": almost the whole engine as a job graph; a resource tracking system "verifies at runtime that all data accesses (reads, writes, creations and destructions) are valid" and happen at safe times in the frame. [verified, abstract only]
- Tatarchuk, "Destiny's Multithreaded Rendering Architecture": [verified, abstract only]. The slide deck is 25 MB and could not be fetched, so its extract, frame-packet and visibility details are [unverified] and not used below.

**Gyrling, "Parallelizing the Naughty Dog Engine Using Fibers", GDC 2015** (slides, text extracted)

- Jobs wait only through counters: `WaitForCounter` parks the fiber on the counter's wait list. [verified]
- A frame is "a piece of data", not a length of time. `FrameParams` holds per-frame state (frame number, delta time, camera, skinning matrices, mesh list); each stage works on a unique instance without locks; 16 instances rotate. [verified]
- `HasFrameCompleted(frameNumber)` decides when memory consumed by a later stage may be freed. [verified]
- Tagged heap of 2 MiB blocks, freed per tag; lifetimes named game, game-to-render, game-to-GPU, render-to-GPU. [verified]
- Frame time 25 ms to 15.5 ms on PS4 for that title. [verified; not transferable]

**Jolt Physics** (architecture docs)

- The broadphase is one quad tree per broadphase layer; keep the layer count low. [verified]
- Moving a body expands the nodes above it lock-free; a tight tree is rebuilt in the background during the next step and swapped. Bodies cannot be added or removed during the step. [verified]
- Adding bodies one at a time gives an inefficient broadphase; batch adds (`AddBodiesPrepare` may run on a background thread, `AddBodiesFinalize` adds atomically) or `OptimizeBroadPhase` are the remedy. [verified]
- The body interface has a locking variant (hashed mutex array) and a no-lock variant. During `PhysicsSystem::Update` bodies cannot be read or written. Contact callbacks run on several threads and may only read. [verified]
- A narrow phase query takes a consistent snapshot of a body under a short lock. Broadphase results are body IDs, which stay safe across steps; IDs carry a sequence number. [verified]
- The docs do not state whether queries may run concurrently with `Update`. [verified absence]
- Determinism needs the same order of modifying API calls and the same binary; cross-platform determinism costs about 8 %. Broadphase query results are not deterministic in order. [verified]
- `SaveState/RestoreState` cover what the step modifies; adding or removing bodies between snapshots must be undone by hand. [verified]
- Float builds are fine within about 5 km; double precision costs 5 to 10 %. The broadphase stays in floats. [verified]

**Box2D v3 and Catto**

- Box2D v3 docs: body move, sensor and contact events are buffered and exposed as contiguous arrays after the step. Polling all bodies "is inefficient". Event data must be read right after the step and may reference destroyed shapes. [verified]
- Read-only operations, including ray casts, are safe from several threads outside the step; nothing may be read or written during the step. [verified]
- Catto, "Dynamic Bounding Volume Hierarchies", GDC 2019 (slides, text extracted): a dynamic AABB tree serves moving objects, creation and destruction, and streaming. Leaves hold enlarged AABBs and are updated only when the tight box leaves the enlarged one. Insertion uses the surface area heuristic with branch and bound. Sorted insertion order degrades incremental trees; rotations mitigate it. The motivating scene has about 9000 collision objects. [verified]

**BVH update literature**

- Kopta et al., I3D 2012: refit-only trees can degrade quickly. Refit plus tree rotations in the same bottom-up pass adds little cost, parallelises with the refit, and matched or beat the alternatives in five of six scenes. For "extremely degenerate" animation (BART) a rebuild or a rebuild heuristic is advised. [verified] Setup: triangle-level BVHs for ray tracing, up to 1.6 M triangles, 8-core Xeon X5550. It transfers to object-level game queries only as a qualitative ordering.
- Rebuild-per-frame (Wald 2007), asynchronous rebuild (Ize et al. 2007) and rebuild-on-degradation (Lauterbach et al. 2006) are known to me only through Kopta's related-work section. [unverified directly]
- Meister et al. 2021, the BVH survey that would say whether Kopta is superseded, returned 403. [unverified]

**Kämpe, Sintorn, Assarsson, "High Resolution Sparse Voxel DAGs", SIGGRAPH 2013**

- A DAG merges identical subtrees of a sparse voxel octree of a binary voxel grid; node count drops by one to three orders of magnitude. [verified]
- Geometry only: "We do not attempt to compress material or reflectance properties". [verified]
- "Our focus has not been on dynamic scenes which would require real-time compression." [verified]
- Demonstrated for hard shadows, soft shadows and ambient occlusion by ray tracing. [verified]
- Later work on editing compressed DAGs exists (Careil et al. 2020) but was not read. [unverified]

**Fiedler** (gafferongames.com)

- State Synchronization: each packet carries a bounded subset of objects, chosen by a per-object priority accumulator that persists across frames. Sent objects reset to zero; unsent ones stay first in line. The bandwidth cap is adjustable. Packets are built from current state; no queue of changes is described. [verified]
- Snapshot Compression: deltas are encoded against a baseline snapshot the receiver has acked, roughly one RTT old, with one "not changed" bit per object. The article does not say how long baselines must be kept. [verified]

---

## 3. The solutions

Scenario numbers follow the task: (1) user code mutates, (2) 0..n steps and multi-rate consumers, (3) slow consumer bound, (4) destroy while referenced, (5) replication and re-simulation, (6) async producers, (7) fresh spatial queries, (8) headless, (9) recomposable pipelines and access keys, (10) job-level dependencies.

### S0 Status quo: CRUD fan-out plus phase-flagged polling

**Mechanism.** Structural changes are queued and fanned out to every system at broadcast. Every system then re-reads every model's component at each `update` (section 1).

| # | Handling |
|---|---|
| 1 | Spawn and destroy are deferred to the next broadcast. Value changes are found by polling, so no setter discipline is needed. Only fields a model explicitly compares are picked up. |
| 2 | Polling is tied to stage executions: n steps cost 2n full walks per system. A consumer on its own cadence is not possible, because `update` writes the models the passes read under one `SceneBase` key. |
| 3 | Bounded. Value changes are level-triggered and nothing queues. Only the structural queue grows if broadcast stops. |
| 4 | Mark and erase in `postprocess` of the same frame. Unsafe once any consumer outlives the frame; raw `_owner` pointers. |
| 5 | A replication system would be one more poller over all components per step, with no "changed since tick" information. Polling is idempotent, so re-simulation produces no ghost events. |
| 6 | The queue is thread-safe for add and remove. Value writes from outside the frame race with stages; no key covers them. |
| 7 | Transforms are computed on demand, never stale. Jolt is stale between the tick and `SceneUpdatePrePhysics`. No query API exists. |
| 8 | The system list is a template argument, so a server scene type without render is a new alias. Each scene type hard-codes its list. |
| 9 | One key for everything. `Scene::update` calls all systems inside one task, so per-system keys cannot help until that loop is split. |
| 10 | None. |

**Criteria.**

- Performance: cost proportional to object count, twice per frame, per system. Memory traffic is all transforms every frame. No contention only because everything is serial; it blocks the post-settle fan-out the engine-loop page wants.
- Correctness: no ghost events and no ordering problem, since it is state-based. Lifetime holds only for same-frame consumers.
- Future-proofing: does not scale to "hundreds to multiple millions of objects" (Pages `actor-system.md` 8.4) and has no path to a decoupled graphics cycle.
- Maintainability: least code. A new component type needs one `addTypeMapping` line and a model class. A new system must implement the whole polling loop.
- Fit: it is the code.

### S1 Central change log on the scene

**Mechanism.** Mutations append records `{handle, component type, kind, field mask, phase, step}` to a scene-owned log. Subscribers register a filter and drain at their own point. Three sub-choices decide most of the properties:

- **Record content.** *Id-only* records mean the consumer reads the live component when it drains, so the drain must happen at a sync point. *Value-carrying* records are true patches and can be applied while the simulation continues.
- **Retention.** *Shared log with cursors*: one append per change, trimmed to the slowest cursor. *Per-subscriber coalesced dirty sets*: each matching subscriber gets a set keyed by handle and field, with last value winning.
- **Append path.** One shared tail, or per-worker buffers merged at a sync point in a defined order.

| # | Handling |
|---|---|
| 1 | Captured once at the setter. Every mutation must pass a capturing setter; public fields (section 1.7) and direct writes through component references escape it. |
| 2 | The step id is in the record. A consumer that runs every step drains every step; a slow consumer drains a coalesced batch. Interpolation needs the last two values, so either the record or the replica keeps the previous one. |
| 3 | Shared log with cursors: unbounded while a cursor stalls, unless "cursor too old, resynchronise from state" is defined. Coalesced dirty sets: bounded by live objects times tracked fields, plus pending removes. |
| 4 | A remove record is terminal for a handle and must carry what the consumer needs to release its replica, not a component pointer. The handle generation separates remove from re-add on a reused index. The replica's lifetime belongs to the consumer. |
| 5 | Supplies "what changed this step" directly. One cursor per connection does not scale to thousands of connections. Re-simulated steps append again; consumers must be idempotent per `(handle, field, step)` or the log must be truncated on rollback. |
| 6 | Async producers append to an inbox merged at a sync point, as the component queue does today. |
| 7 | The log does not freshen any index. A spatial consumer is stale between its drains unless it drains synchronously (section 5). |
| 8 | Absent subscribers cost nothing at drain. Capture is still paid unless the setter checks a per-type subscriber mask. |
| 9 | The log is one resource: tick stages write it, consumers read it and write only their own replica. Consumers are then pairwise conflict-free. A consumer outside the frame graph needs a hand-over stage that seals a segment, because a per-frame key cannot describe it. |
| 10 | A log partitioned by space or cell can expose one `Signal` per sealed partition. Access keys are types, not instances, so the builder cannot check per-partition overlap. |

**Criteria.**

- Performance: per-frame cost follows the number of changes, not objects. One append is a few tens of bytes; coalescing adds a hash or sparse-set lookup per subscriber. A shared tail is a serialisation point on 24 threads; per-worker buffers remove it at the price of a merge. Bulk producers dominate traffic: physics readback emits one transform change per moving body per step. Box2D publishes such bulk results as a contiguous array from the producer [verified]; the equivalent here is a "bulk segment" record kind.
- Correctness: the richest hazard set. Record order across workers, remove and add coalescing, rollback duplicates and missed captures all need rules and tests. Deterministic only if the merge order is defined, for example sorted by handle.
- Future-proofing: suits a decoupled graphics cycle, GPU dirty ranges and streaming (batch add of a cell is one record kind). For replication it supplies the dirty set; per-connection selection stays state-based.
- Maintainability: the most new engine code (log, filters, coalescing, cursors or sets, sealing). A new component type needs capture in its setters and a field mask. Debuggability is good, because the log can be dumped and replayed. Flecs' statement that a basic event queue outperforms observers [verified] supports queues over callbacks, not this design specifically.
- Fit: extends `SceneComponentQueue` (structural log) and matches the owner direction in Pages `engine-loop-exploration.md` 5.2a. SceneWalker's filter split is reusable as subscription filters. The polling model classes become patch appliers.

### S2 Per-component change detection

**Mechanism.** Each component, or each chunk and component-type pair, stores the tick of its last write. Each consumer remembers the tick of its last run and scans.

| # | Handling |
|---|---|
| 1 | The write stamps a tick. Bevy stamps on mutable dereference, enforced by the borrow checker [verified]. C++ has no equivalent, so stamping needs setters or mutable-access wrappers. Over-reporting is normal: both Bevy and Unity state that the mark does not prove a value changed [verified]. |
| 2 | Its strongest scenario. Every consumer compares against its own last tick, so cadences are independent and changes are coalesced by construction. No step history is kept. |
| 3 | Bounded by construction: a few bytes per component or per chunk, no queue. |
| 4 | Its gap. Ticks live on the component and removal destroys them. Bevy adds a message buffer for removals, cleared every update [verified]. A structural log is therefore needed anyway. |
| 5 | "Changed since the acked baseline tick" is one compare and fits delta-against-baseline replication [verified]. Cost is a scan of the relevant set per send unless chunk versions prune. Re-simulation re-stamps: false positives cost bandwidth, not correctness. |
| 6 | An async writer needs a defined tick and a sync point; a stamp from outside the frame races with scanning consumers. |
| 7 | No contribution. |
| 8 | A missing consumer costs nothing; the stamp remains. |
| 9 | Ticks are part of component storage, so they sit under the existing `acs::Registry` key and need no new key. Consumers are readers of `Registry` and conflict with every stage that writes it. |
| 10 | Chunk versions allow one job per chunk, but there is no completion signal per chunk. |

**Criteria.**

- Performance: capture is one store, the cheapest of all. Consumer cost is a scan. Per-component ticks cost O(matching components) per consumer run even when nothing changed (Bevy [verified]). Per-chunk versions cost O(chunks) with whole-chunk false positives (Unity [verified]). No queues means no memory traffic besides the scan, and no cross-thread contention except false sharing of tick arrays under parallel writers.
- Correctness: no ordering and no duplicates, because it is state-based. Hazards are tick wrap (both engines carry explicit handling [verified]), missed removals, and writes that bypass stamping.
- Future-proofing: scan cost at millions of objects must be measured. It works unchanged on a server. Alone it cannot feed a consumer that runs concurrently with the simulation, because the consumer reads live components.
- Maintainability: little engine code, but every component write path must stamp. Debuggability is weak: a tick says when, not what or who.
- Fit: components sit in type pools and archetype slots, and Pages `actor-system.md` 8.5 already agrees on spans `(base, count, stride)` per component type, the natural unit for chunk versions. Replaces `static bool isDirty` directly.

### S3 Push into per-system replicas at a sync point

**Mechanism.** Each system owns a replica holding only what it needs. At a sync point the scene side copies into it; afterwards the consumer works on the replica alone. Three variants appear in the sources:

- **Extract-all** copies everything relevant at each sync.
- **Extract-changed** needs S1 or S2 to know what to copy.
- **Command push** (Unreal) enqueues value-carrying updates at change time into the consumer's queue [verified]. That is S1 with one value-carrying queue per consumer.

Naughty Dog's `FrameParams` is extract into rotating immutable per-frame packets, with lifetimes tied to stage completion [verified]. The current models are an in-place, polled, twice-per-frame extract.

| # | Handling |
|---|---|
| 1 | Extract-all needs no setter discipline. Changes become visible to the consumer at the next sync point only. |
| 2 | Extract runs when the consumer can accept a new state, so simulation steps in between are coalesced by omission. Bevy lets extract wait for both sides [verified], which makes one side idle. A free-running consumer needs a second replica buffer or value-carrying patches. |
| 3 | Bounded: replica size follows live objects times buffers. The bound is paid by blocking (Unreal blocks the game thread [verified]; Bevy waits) or by extra buffers. |
| 4 | The consumer owns replica lifetime and frees after its in-flight work, by fence (Unreal [verified]) or stage-completion counters (Naughty Dog [verified]). Extract-all cannot see removals without sweeping the replica or receiving a remove list. |
| 5 | One network replica (the `ReplicationSystem : SceneSystem` of Pages `networking-mmo.md`) plus per-connection acked baselines. Extract-all per server step is O(replicated objects). |
| 6 | No contribution; async producers still need a point to write components. |
| 7 | A replica is stale between syncs by definition. For the physics replica, user code that moves an actor and then queries Jolt sees the old pose; Unreal documents that staleness for its pre-physics group [verified]. Freshness needs write-through for that one consumer. |
| 8 | Dropping a system drops its extract stage and replica. |
| 9 | The best expressibility. The extract stage reads scene keys and writes the replica key; the consumer touches only the replica key. Extracts of different systems are mutually read-only on the scene and can run in parallel. |
| 10 | Extract can be partitioned per view or cell with a `JoinCounter` per partition. The checkability limit of S1 row 10 applies. |

**Criteria.**

- Performance: extract-all is O(objects) of copy traffic at a serial sync point; Bevy's own guidance is to keep it short [verified]. Extract-changed moves the cost to the number of changes. Replicas give each consumer its own cache-friendly layout (the planned `GpuSceneTables`, Jolt bodies).
- Correctness: the cleanest isolation. The consumer cannot observe a half-updated scene, and determinism of the simulation does not depend on the consumer. The hazard is the sync point: anything not copied does not exist for the consumer.
- Future-proofing: this is the form GPU-driven rendering needs. A physics-engine replacement touches one replica. Extract-all does not survive MMO object counts with several steps per frame.
- Maintainability: one model class per component type and system, which is the current cost. Access keys become simple. Replicas are easy to test in isolation.
- Fit: the highest. `RenderSceneSystemModel` and `PhysicsSceneSystemModel` are replicas already. What is missing is the removal of live `_owner` reads after sync, a single sync point instead of two polls, and consumer-owned lifetime.

### S4 Observers and immediate callbacks

**Mechanism.** A mutation synchronously invokes registered callbacks on the mutating thread.

| # | Handling |
|---|---|
| 1 | Consumers learn of the change at once. With per-actor parallel ticks, callbacks run on many workers. Each consumer must be thread-safe or queue internally, which is S1 rebuilt per consumer. Jolt's locking body interface could take such calls outside `Update` [verified]; GPU instance buffers cannot without their own lock. |
| 2 | Callbacks fire per mutation, not per consumer cadence. A slow consumer has to buffer and coalesce on its own. |
| 3 | Unbounded unless every consumer coalesces. |
| 4 | A pre-removal callback still sees the data (Bevy `Remove` [verified]). In-flight consumers still need deferred release. |
| 5 | Re-simulation re-fires every callback; suppressing ghost events needs a replay flag in every observer. Order between observers is not specified in Flecs [verified absence] and depends on worker timing under parallel ticks. |
| 6 | The callback runs on the async producer's thread, outside any stage. |
| 7 | The only solution that can keep a derived index exactly fresh, by writing through. The index is then written during the tick stage. |
| 8 | No observers registered means one empty-list check per mutation. |
| 9 | The worst case. A tick stage that writes `Registry` now writes every observer's state. Its declaration must be the union of all observers' keys (Pages `task-graph-design.md` 6.5 allows computed unions), which orders it against every consumer. If the union is omitted, the check is silently wrong. |
| 10 | None. |

**Criteria.**

- Performance: no polling and no queue for one consumer and serial producers. Under parallel producers, contention moves into each consumer. Flecs rates observers below queues, hooks and systems for bulk work [verified].
- Correctness: re-entrancy (a callback mutates and triggers further callbacks), ordering and duplicates under re-simulation; non-deterministic under parallel ticks.
- Future-proofing: poor as the primary path at scale; fine for low-frequency consumers.
- Maintainability: small mechanism, hard to debug because control flow is inverted and callbacks run in the middle of user code. Access keys cannot describe it without over-declaring.
- Fit: the editor already has a reactive layer (`Editor.UI.Rx`). Observers suit editor tools and UI, where changes are rare and consumers run on one thread. `SceneSystemBase::add/remove` at commit time is already a batched, deferred callback.

---

## 4. Comparison

One line of reasoning per cell.

| Criterion | S0 status quo | S1 change log | S2 change ticks | S3 replicas at sync | S4 observers |
|---|---|---|---|---|---|
| Cost per change | None at write; found by polling | One append plus coalescing per subscriber | One tick store, the cheapest | None at write (extract-all) or as S1/S2 | One call per observer, inline |
| Cost per frame | O(objects), twice per system | O(changes) | O(components or chunks scanned) per consumer | O(objects) extract-all; O(changes) extract-changed | O(changes), on the producer's thread |
| Backpressure and bound | Bounded, nothing queues | Bounded only with coalesced sets or a resync rule | Bounded by construction | Bounded by blocking or extra buffers | Unbounded unless each consumer coalesces |
| Many-core behaviour | Serial under one key | Append point contended unless per-worker; consumers parallel | No shared structure; scans parallel per chunk | Sync point serial; consumers fully parallel after it | Contention inside every consumer |
| Stage parallelism | Blocks it | Consumers conflict-free among themselves | Consumers are `Registry` readers | Best: scene edges vanish after extract | Worst: ticks conflict with all consumers |
| Stale reads | None for transforms; Jolt stale until update | Consumer stale until drain | Consumer stale until scan | Stale between syncs, by definition | None |
| Ordering and duplicates | None (state-based) | Needs merge order and rollback rules | None (state-based); over-reports | None at sync; command push has ordering | Unspecified order; re-fires on re-simulation |
| Destroyed objects | Same-frame only | Terminal remove record; consumer-owned lifetime | Not covered; needs a remove list | Consumer-owned; needs a remove list or sweep | Pre-removal callback; in-flight users unresolved |
| Determinism | Yes | With a defined merge order | Yes | Yes | No under parallel ticks |
| MMO-scale counts | No | Yes if change rate is well below object count | Scan cost must be measured | Only as extract-changed | Not as the primary path |
| Server and replication | Poll per step | Supplies the dirty set; selection stays state-based | Baseline-tick compare fits acked deltas | One network replica plus baselines | Per-connection observers not viable |
| Decoupled graphics cycle | No | Yes with value-carrying records | Not alone | Yes, its original purpose | Only by queueing inside render |
| Engine code | Least | Most | Little, but every write path stamps | Moderate; mostly exists | Little |
| Adding a component type | Mapping plus model | Setter capture, field mask, model | Stamp in setters, model | Mapping plus model | Emit in setters |
| Debuggability | Simple, opaque cost | Log can be dumped and replayed | A tick does not say what or who | Replicas inspectable in isolation | Inverted control flow |
| Access-key expressibility | One coarse key | Log key plus one per replica; off-frame consumer needs a seal stage | Covered by `Registry` | One key per replica, cleanest | Union keys or a wrong check |
| Fit and migration | Is the code | Extends `SceneComponentQueue`; models become appliers | Replaces `isDirty`; needs a tick field or column | Models are replicas already | Fits `Editor.UI.Rx` |

**Who wins where.**

- Cost per change: S2.
- Cost per frame at low change rates: S1 and extract-changed S3.
- Bounded memory under a slow consumer: S2 by construction, then state-based S3. S1 only in its coalesced form.
- Stage parallelism and access-key clarity: S3.
- Freshness for immediate readers: S4 and on-demand computation. No deferred scheme gives it.
- Destroyed-object lifetime: S1 and S3, because the consumer owns its replica and removal is an explicit record.
- Determinism and absence of ghost events: the state-based ones, S0, S2 and S3.
- Least new code: S0, then S2.
- Debuggability: S1.
- S4 wins no criterion as a primary mechanism. It wins freshness and editor fit as a secondary one.

No single solution wins lifetime, bound and cost together. S2 has no removals. S1 is unbounded in its simple form. Extract-all S3 is O(objects).

---

## 5. Spatial index

### 5.1 What exists and what the consumers need

- Only Jolt's broadphase exists today (section 1.7).
- Planned consumers want different things:
  - Physics: fat boxes, pair finding, layers.
  - GPU culling: tight bounds on the GPU. Pages `render-graph-gpu-driven.md` states that GPU culling owns its bounds and CPU bounds stay for picking and interest.
  - Replication: interest management as a grid over the storage cells (Pages `networking-mmo.md`, `InterestPolicy`).
  - Audio: emitter culling and occlusion against static geometry.
  - Gameplay, AI, picking: ray, overlap and frustum queries.
- A sparse voxel DAG is a static, binary-occupancy structure built by offline reduction, shown for shadow and occlusion rays [verified]. It suits visibility and occlusion against static world geometry. It is not an index of moving objects and has no part in mediating state changes. In an "SVBVH" hybrid the two halves have different update models: the BVH over dynamic objects is incremental, the voxel part is baked or rebuilt per region.

### 5.2 SP0: each system keeps its own structure

- **Scenario 7.** Gameplay queries go to Jolt's narrow phase query.
  - Freshness needs user-code transform writes to reach Jolt before the query, through the locking body interface, which is legal outside `Update` [verified]. This is a write-through for one consumer.
  - Jolt's broadphase tolerates it: bounds widen until the next maintenance update [verified].
  - Objects without a body (audio emitters, render-only meshes for picking, zones) are invisible unless added as sensor bodies or extra layers, and Jolt advises few layers [verified]. Pages `bounding-volumes.md` section 8 lists this as open.
  - Broadphase results come in non-deterministic order [verified], so authoritative gameplay must sort them.
- **Scenario 8.** A server has Jolt, so queries work headless. Picking is an editor concern.
- **Scenario 9.** Queries are reads of the `PhysicsSceneSystem` key. A tick stage that writes through to Jolt becomes a writer of that key and is ordered against every physics reader. That holds today because the chain is strict. No queries are possible during `PhysicsTick` [verified].
- **Criteria.** No new structure and the least code. Query semantics, precision and determinism are Jolt's. A physics-engine replacement changes the gameplay query API unless a facade is put in front. Each system pays only for what it uses.
- **Restriction imposed.** Everything queryable must be a physics object.

### 5.3 SP1: one central index that everyone reads

- **As a replacement** for the others it conflicts with two fixed points. Jolt maintains its own broadphase; whether it can be driven from an external tree was not checked [unverified]. GPU culling needs bounds resident on the GPU.
- **As an addition** written in place, every transform write is an index write.
- **Scenario 7.** Fresh if written through at mutation time. It is then written during the tick stage, by many workers once ticks fan out. That needs a concurrent tree (Jolt's lock-free expansion shows the cost and shape of one [verified]) or serial ticks.
- **Scenario 8.** Works headless.
- **Scenario 9.** One key written by every mover and read by every querier. The builder would order all of them, serialising the frame around the index.
- **Criteria.** One structure to maintain and debug, but it must satisfy fat-box pair finding, tight-box culling and gameplay queries at once. Catto's enlarged boxes [verified] and render culling's tight boxes are opposing requirements on the same leaves.
- **Restriction imposed.** All systems share one update policy and one precision model.

### 5.4 SP2: central index as derived data, read-only between updates, specialised structures kept

- **Mechanism.** The index consumes transform, bounds, add and remove changes (from S1 records or an S2 scan) in one update stage and is immutable otherwise. Jolt's broadphase and the GPU bounds stay.
- **Scenario 7 is the conflict.** "Read-only between updates" and "must not see stale transforms while user code runs" (Pages `actor-system.md` 8.6) contradict each other. Three ways to reconcile them:
  1. *Overlay.* Leaves hold enlarged boxes [verified as a technique]. The broadphase result is conservative as long as an object stays inside its enlarged box, and the exact test reads the live transform. Only objects that escaped their box, or were spawned, since the last update are missed; they go into an "escaped" list that queries scan linearly. Results are fresh, the tree stays immutable, and the cost is the escaped-list length per stage. Reading another actor's live transform while its tick writes it is a data race under parallel ticks, whatever the index.
  2. *Sub-stage updates.* Refit between tick groups, as Unreal's group barriers allow [verified]. Fresh at group granularity, with more update stages.
  3. *Defined staleness.* Queries see the last update, as Unreal documents for pre-physics [verified]. This breaks the stated requirement.
- **Scenario 8.** Lives in the scene layer, so it works headless. Interest management could read it instead of a separate grid.
- **Scenario 9.** The cleanest of the three: one `SpatialIndex` key, one writer stage, any number of parallel readers. Adding or removing render, audio or network does not change its edges.
- **Criteria.**
  - A moved object updates up to three structures (central, Jolt, GPU bounds).
  - Memory is a further copy of bounds plus about two nodes per object.
  - Refit with rotations is the update of record for coherent motion; rebuild or rebuild-on-degradation is for incoherent change [verified for ray-traced triangles, ordering only].
  - Streaming in a cell is a batch insert, the case where sorted single inserts degrade a tree [verified, Catto; Jolt gives the same advice].
  - Engine-agnostic, so a physics replacement does not touch gameplay queries.
- **Restriction imposed.** Consumers needing exact freshness must use the overlay or go to the owning system. The index holds bounds only, so exact shape tests still need Jolt shapes or render geometry.

### 5.5 Further options from the sources

- **SP3: central query interface, no central structure.** A scene-level query API implemented by Jolt, with non-physics objects in extra layers or as sensors. Same structures as SP0 and engine-agnostic for callers. It inherits Jolt's locking and layer limits, and query availability is tied to the physics step.
- **SP4: per-cell grid for coarse queries.** Interest management and emitter culling need "who is near", not rays. A grid keyed by streaming cell is already implied by the networking plan. It can coexist with SP0 or SP3 and makes a central BVH unnecessary for those two consumers.

### 5.6 Against the criteria

| | SP0 own structures | SP1 one central | SP2 derived central plus specialised | SP3 facade over Jolt |
|---|---|---|---|---|
| Fresh queries in user code (7) | By write-through to Jolt | By write-through; contended | Only with overlay or sub-stage updates | As SP0 |
| Headless (8) | Yes | Yes | Yes | Yes |
| Access keys (9) | Queries read the physics key; ticks become physics writers | Everything conflicts on one key | One key, one writer stage, parallel readers | As SP0 |
| Update cost per moved object | One or two structures | One, concurrent | Up to three | One or two |
| Code to own | None | Concurrent dynamic tree | Dynamic tree, overlay, update stage | Thin API |
| Physics replacement | Query API changes | Unaffected | Unaffected | Facade reimplemented |
| Non-physics queryables | Not covered | Covered | Covered | Covered through layers or sensors |

---

## 6. Combinations

### 6.1 Coherent

**C-A: evolved status quo.** S0 for structure, a real dirty mark on the model or component, per-system keys, SP0 or SP3.

- Removes the O(objects) transform rewrite and the single key. Render stays inside the frame.
- Does not reach a decoupled graphics cycle or replication.

**C-B: structural log plus change ticks plus extract-changed.** A small S1 for structure, S2 for values, S3 replicas, SP0 or SP3.

- Add, remove, reparent and asset swaps are rare, order-sensitive and must not be lost. They go through a log; `SceneComponentQueue` grows handles, a step id and per-consumer retention.
- Transforms and parameters are frequent and last-value-wins. They get ticks: bounded, coalesced by nature.
- Each system's extract stage scans ticks and drains the structural log into its replica.
- This is Bevy's split (ticks for values, messages for removals, extract for render) [verified per part].
- Render can only pipeline with a wait at extract, as Bevy does. A free-running graphics cycle is not covered.

**C-C: central log with value-carrying patches into replicas.** S1 feeding S3 in command-push form, SP2 fed by the same log.

- The owner direction of Pages `engine-loop-exploration.md` 5.2a.
- Covers the free-running graphics cycle, interpolation (patches carry the step) and a server that mounts only the subscribers it has.
- Needs per-subscriber coalescing for scenario 3. Replication selects per connection from state [verified, Fiedler], with the log only marking what is dirty.

**C-D: C-B or C-C plus S4 restricted to editor and UI.** Observers on the editor side only, fed at a sync point from the same change source. No engine stage's access declaration is affected.

### 6.2 Not coherent

- **S4 as the primary path with parallel actor ticks and meaningful access checks.** The tick stage's write set becomes the union of all observers, or the check is wrong.
- **S2 alone with a consumer that runs concurrently with the simulation.** The consumer must read live components.
- **S1 with id-only records and such a consumer.** Same race; id-only records require a drain at a sync point.
- **S1 as a shared log with cursors and a bandwidth-limited consumer.** Violates scenario 3 unless a resync fallback exists.
- **Extract-all S3 per fixed step at MMO object counts.** The sync point becomes O(objects) times steps.
- **SP1 as sole structure with Jolt and GPU-driven culling.** Both keep their own.
- **SP2 "read-only between updates" with the freshness requirement and no overlay or sub-stage update.**
- **A SVDAG as the shared dynamic index.** It encodes static binary occupancy [verified].

### 6.3 Migration from the current code

Steps 1 to 4 are common to all three combinations.

1. **Fix lifetime first.** Make physics model erase work (section 1.4). Trace a removal queued late in the frame against component release. *Risk:* none of the later steps is testable while destroyed models linger.
2. **Models identify their component by `acs::Handle`**, not only by raw pointer. *Risk:* the 20-bit generation wrap is already noted as a shortcut in `Handle.hpp`.
3. **Split `Scene::update` per system and give each system its own access key.** Stop running both walks in both phases, using the flags the stages already pass. *Risk:* with the chain relaxed, undeclared access surfaces, and the state-hash check is deferred (Pages `task-graph-design.md` 6.2).
4. **Route component mutation through setters.** Public fields such as `extent` (section 1.7) break S1 and S2 alike. *Risk:* API churn in `Heliogrim/Component/**`.

**C-A after 1 to 4**

5. Replace `static bool isDirty` with a per-component or per-model mark set by the setters; `update` skips clean models.
6. Add a scene query facade over Jolt (SP3).

*Risk:* low. It leaves scenarios 2, 4 (beyond the frame) and 5 open.

**C-B after 1 to 4**

5. Add a change tick per `SceneComponent`, or per span, and a scene step counter. Systems keep a last-seen tick.
6. Extend `SceneComponentQueue`: handles and a step id in the records, retention per consumer until each has drained.
7. Turn `update` into extract stages (one per system, reading `Registry`, writing the replica key). Remove `_owner` reads after extract, starting with `capture`.
8. Move replica erase from `ScenePostProcess` to the consumer, gated by its in-flight frames; the per-pass fence in `RenderTarget` is the existing hook.

*Risks:* scan cost at high object counts is unmeasured; tick wrap; missed stamps are silent.

**C-C after 1 to 4**

5. Generalise the queue into the log: record kinds for transform and parameter changes, phase and step, per-worker append buffers merged at broadcast in handle order.
6. Add subscriptions with filters (the SceneWalker filter split is the template) and per-subscriber coalesced sets.
7. Render becomes the first subscriber: models apply patches and stop reading `_owner`; a seal stage hands a segment to the graphics cycle.
8. Physics becomes the second subscriber. Readback publishes moved bodies as one bulk segment instead of writing each component and re-detecting it.
9. Add the central index as a third subscriber (SP2), with the overlay, once query consumers exist.
10. The fixed-step loop is a prerequisite for the multi-rate tests (section 1.8: the pipeline has no sub-graph loop).

*Risks:* the most new code before any benefit; rollback and duplicate rules must exist before replication uses it; the off-frame consumer is not checked by access keys.

C-B is a prefix of C-C in practice. Steps 5 to 8 of C-B stay valid if value-carrying patches are added later for the render subscriber only.

---

## 7. Open questions

| Question | What would decide it |
|---|---|
| What fraction of objects changes per step in the target scenes? | A synthetic scene on the existing models with counters for moved and changed components per step. Below a few percent favours S1 or extract-changed; near all favours a scan or a bulk segment. |
| Is a tick scan affordable at 1 M components per consumer? | A micro-benchmark on the archetype spans (per-component tick against per-span version) on the 24-thread machine and on 2 to 3 workers. |
| Must the graphics cycle run free of the frame, or is extract-with-wait enough? | The measured ratio of simulation step time to render CPU time. If render CPU is the larger and variable, a free-running cycle (C-C) pays; otherwise extract-with-wait (C-B) is simpler. |
| Do transform patches need values or only ids? | Follows from the previous row: values only for a subscriber that applies them off the sync point. |
| How is a subscriber's backlog bounded? | A decision between coalesced sets and "resync from state"; test with a stalled subscriber for 10,000 steps and a flat memory curve. |
| What does re-simulation do to change records? | The prediction scope (Pages `networking-mmo.md` Q56.1: local actor and mount). If only a few entities re-simulate, tagging their records by step and letting consumers ignore replays suffices. |
| Which consumers need spatial queries that Jolt cannot answer? | A list of queryables without bodies and their query rates. If short, SP3 with sensors is enough; if large or wanted during the physics step, SP2. |
| Is the overlay's escaped list short in practice? | Count per tick stage, in a moving-crowd scene, the objects that leave an enlarged box of a given margin. |
| Refit with rotations, or rebuild on degradation, for the central index? | Tree cost (SAH) over time under streaming and mass movement at object level. The ray-tracing results give the ordering only. |
| Can a custom broadphase be supplied to Jolt? | Read `vendor/jolt/include/Jolt/Physics/Collision/BroadPhase/`; not done here. Decides whether SP1 is possible at all. |
| Can access keys describe partitions (scenario 10)? | Whether a stage may declare `Key<Type, PartitionId>`. Without it, job-level dependencies across stages are legal only between stages that share no key. |
| How does the pipeline run 0..n steps? | A sub-graph loop in `CompositePipeline` or two pipelines; prerequisite for testing scenario 2 with any solution. |
| Where do setters stamp or append under parallel actor ticks? | Whether a tick may write only its own actor's components. If yes, per-worker buffers or plain stores suffice; if not, cross-actor writes need a deferral rule first. |

### 7.1 Owner answers (2026-11-14)

1. **Change rate per step**: no single figure. The target spans level streaming (thousands of objects in and out), terrain events (eruptions, floods, landslides: mass terrain updates, many moving and transforming objects), battles with hundreds to thousands of equipped characters and projectiles, and silent scenes (grassland, mountains) where almost nothing changes. The owner asks whether an **adaptive strategy** fits best.
2. **Tick scan at a million components**: undecided. The ACS is built for dense storage and fast memory walks, but it is open whether coalesced update batches (accepting a small number of false positives that are updated without a change) beat each system walking the component streams of every actor every frame.
3. **Free-running graphics cycle versus extract with a wait**: no numbers. The GPU may also take asynchronous compute work (effects, physics, audio, other jobs), so CPU and GPU work may mix.
4. **Subscribers falling behind**: with the simulation subgraph and the frame work (engine loop exploration 3.1 and 5.1) there are two groups, and only the frame group can fall behind. The inner simulation loop has to be broken once per frame to drain and flush the change stream into the frame group's systems.

### 7.2 What the answers change

- **Adaptive granularity (answers 1 and 2) is one mechanism, not two.** Producers set a dirty mark at the granularity of the ACS storage chunk (a span of components of one type), not per component and not per object record. A consumer walks only dirty chunks, sequentially, and treats every component of a dirty chunk as changed: the false positives of answer 2, bounded by the chunk size. A silent scene costs one bit test per chunk; a battle or a landslide degrades to a sequential walk of the affected chunks, which is the dense case the ACS is built for. Structural changes (streaming in and out, spawn and destroy) stay records, batched per streaming cell or per frame, so streaming arrives as bulk segments. What still needs measuring is the chunk size and the cost of one dirty walk against a full walk per system; the micro-benchmark row above covers it.
- **The bound on a falling-behind consumer (answer 4) is the coalescing at the flush, not a cursor.** The simulation steps of one frame accumulate into one coalesced set per frame consumer (last value per object and field, structural records in order), flushed once after the inner loop. Its size is bounded by the number of changed objects, not by the number of steps; a shared log with per-subscriber cursors is not needed for the frame group. Two cases keep the same bound: a graphics cycle that spans several frames merges further flushes into its pending set until it starts; network replication selects from state per connection and does not queue changes. Asynchronous work posts its changes into the next flush.
- **Answer 3 keeps both render paths open.** Patches carry values (so a free-running cycle stays possible), while the first implementation hands the flushed set over with a wait; the measurement decides later. GPU compute jobs for physics, audio or effects are further consumers of the same flush.

---

## 8. Sources

| Title | Author / org | Year | Venue | URL | Status |
|---|---|---|---|---|---|
| `bevy::ecs::change_detection`, `Changed`, `MAX_CHANGE_AGE` | Bevy | 2026 (0.20.1) | docs.rs | https://docs.rs/bevy/latest/bevy/ecs/change_detection/index.html , https://docs.rs/bevy/latest/bevy/ecs/query/struct.Changed.html | verified |
| `RemovedComponents`, `bevy::ecs::lifecycle` | Bevy | 2026 | docs.rs | https://docs.rs/bevy/latest/bevy/ecs/lifecycle/index.html | verified (first 100k characters) |
| `PipelinedRenderingPlugin`, `ExtractSchedule` | Bevy | 2026 | docs.rs | https://docs.rs/bevy/latest/bevy/render/pipelined_rendering/struct.PipelinedRenderingPlugin.html , https://docs.rs/bevy/latest/bevy/render/struct.ExtractSchedule.html | verified |
| `bevy::render::sync_world` | Bevy | 2026 | docs.rs | https://docs.rs/bevy/latest/bevy/render/sync_world/index.html | unverified (index only, no behaviour text) |
| Version numbers; EntityQuery filters | Unity | Entities 1.3 | package manual | https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/systems-version-numbers.html , https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/systems-entityquery-filters.html | verified |
| Netcode for Entities, ghost optimisation | Unity | 1.10 | package manual | https://docs.unity3d.com/Packages/com.unity.netcode@1.10/manual/optimizations.html | unverified (index only; subpage 404) |
| Threaded Rendering | Epic Games | UE docs | dev.epicgames.com | https://dev.epicgames.com/documentation/en-us/unreal-engine/threaded-rendering-in-unreal-engine | verified |
| Actor Ticking | Epic Games | UE5 docs | dev.epicgames.com | https://dev.epicgames.com/documentation/en-us/unreal-engine/actor-ticking-in-unreal-engine | verified |
| MassEntity Overview | Epic Games | UE5 docs | dev.epicgames.com | https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-mass-entity-in-unreal-engine | verified |
| Observers Manual | S. Mertens, Flecs | current | flecs.dev | https://www.flecs.dev/flecs/ObserversManual.html | verified (first 100k characters) |
| Queries Manual, change detection | S. Mertens, Flecs | current | flecs.dev | https://www.flecs.dev/flecs/Queries.html | verified in part (code comments; prose not read) |
| Multithreading the Entire Destiny Engine | B. Genova, Bungie | 2015 | GDC Vault | https://www.gdcvault.com/play/1022164/Multithreading-the-Entire-Destiny | verified (abstract only) |
| Destiny's Multithreaded Rendering Architecture | N. Tatarchuk, Bungie | 2015 | GDC, advances.realtimerendering.com | https://advances.realtimerendering.com/destiny/gdc_2015/index.html | verified (abstract only); slides unverified |
| Parallelizing the Naughty Dog Engine Using Fibers | C. Gyrling, Naughty Dog | 2015 | GDC, media.gdcvault.com | https://media.gdcvault.com/gdc2015/presentations/Gyrling_Christian_Parallelizing_The_Naughty.pdf | verified (slide text) |
| Jolt Physics architecture documentation | J. Rouwe | current | jrouwe.github.io | https://jrouwe.github.io/JoltPhysics/index.html | verified |
| Box2D v3 Simulation; Foundation (multithreading) | E. Catto | v3.2 | box2d.org | https://box2d.org/documentation/md_simulation.html , https://box2d.org/documentation/md_foundation.html | verified (simulation: first 100k characters) |
| Box2D v3 Collision, dynamic tree | E. Catto | v3.2 | box2d.org | https://box2d.org/documentation/md_collision.html | verified |
| Dynamic Bounding Volume Hierarchies | E. Catto, Blizzard | 2019 | GDC, box2d.org | https://box2d.org/files/ErinCatto_DynamicBVH_GDC2019.pdf | verified (slide text) |
| Fast, Effective BVH Updates for Animated Scenes | Kopta, Ize, Spjut, Brunvand, Davis, Kensler | 2012 | I3D | https://hwrt.cs.utah.edu/papers/hwrt_rotations.pdf | verified; ray-tracing setup, superseding work not checked |
| Wald 2007; Ize et al. 2007; Lauterbach et al. 2006; Wald et al. 2008 | various | 2006-2008 | IRT, EGPGV, C&G | cited through Kopta et al. | unverified directly |
| A Survey on Bounding Volume Hierarchies for Ray Tracing | Meister et al. | 2021 | Eurographics STAR | https://diglib.eg.org/handle/10.1111/cgf142662 | unverified (403) |
| High Resolution Sparse Voxel DAGs | Kämpe, Sintorn, Assarsson | 2013 | SIGGRAPH / ACM TOG | https://www.cse.chalmers.se/~uffe/HighResolutionSparseVoxelDAGs.pdf | verified |
| Interactively Modifying Compressed Sparse Voxel Representations | Careil, Billeter, Eisemann | 2020 | Eurographics | not fetched | unverified |
| State Synchronization | G. Fiedler | 2015 | gafferongames.com | https://gafferongames.com/post/state_synchronization/ | verified |
| Snapshot Compression | G. Fiedler | 2015 | gafferongames.com | https://gafferongames.com/post/snapshot_compression/ | verified |

Project pages read as context: `X:\Dev\__\Heliogrim-Pages\docs\architecture\engine-loop-exploration.md` (in full), `task-graph-design.md` (sections 6 and 8), `lane-policy-exploration.md` (sections 1 to 3), `actor-system.md` (section 8), `bounding-volumes.md` (in full), and `docs\plan\work\networking-mmo.md` and `render-graph-gpu-driven.md` (in full).

Not read: `actor-archetypes-design.md`, `audio-runtime-design.md`, `storage-design.md`, `physics-cloth.md`, `editor-workflows.md`. Statements about audio and storage requirements above come from the pages that reference them, not from those pages.

Method note: three PDFs (Gyrling, Kopta, Kämpe) and the Catto slides were read by text extraction from the copies the fetch tool cached. Nothing was built or run, and no repository file was changed.
