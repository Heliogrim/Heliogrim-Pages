# Task Graph and Frame Runner

**Status**: <span class="hg-status accepted">implemented</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip`, 2026-11-16. Built in PR [#175](https://github.com/Heliogrim/Heliogrim-Engine/pull/175).
**Modules** (see the [module map](../../architecture/modules.md)): `Engine.Scheduler` ([`Graph/StageDecl`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Graph/StageDecl.hpp), [`Graph/AccessResources`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Graph/AccessResources.hpp), [`Graph/TaskGraph`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Graph/TaskGraph.cpp), [`Pipeline/CompositePipeline`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Pipeline/CompositePipeline.cpp), [`Pipeline/Composite/CompositeSlot`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Pipeline/Composite/CompositeSlot.cpp)), plus the stage bundles `Engine.Core.Schedule`, `Engine.Input.Schedule`, `Engine.ACS.Schedule`, `Engine.Scene.Schedule`, `Engine.Physics.Schedule`, `Engine.Reflow.Schedule`, `Engine.Graphics.Schedule`
**Related**: [task graph design](../../architecture/task-graph-design.md) (the reasoning), [lane policy exploration](../../architecture/lane-policy-exploration.md), [engine loop exploration](../../architecture/engine-loop-exploration.md) (open proposals for the frame, none built), [engine stop teardown exploration](../../architecture/engine-stop-teardown-exploration.md), issue [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84). Scheduler pages: [overview](index.md), [fibers and workers](fibers-and-workers.md), [waitables](waitables.md), [futures](futures.md), [affine threads](affine-threads.md).

## Purpose

Every frame runs a fixed set of stages: timing, input, actor ticks, scene, physics, UI layout, render, housekeeping. Each stage declares what state it reads and writes, which lane it runs in, and which stages it must follow or precede. At setup a builder turns the declarations into one graph and rejects unknown names, cycles and pairs of stages that may overlap while touching the same state. A counting runner then starts every stage whose predecessors finished, on any number of workers.

What it deliberately does not do: derive an order from the read and write sets (edges are authoritative; the sets only check), order tasks inside a stage (that is a [`JoinCounter`](waitables.md)), or change the graph while a frame runs. It does not check that a stage touches only what it declares.

## Where it sits

```hg-diagram
flowchart LR
    MOD["Modules<br/>(Graphics, Input, Physics, Reflow setup;<br/>engine setupCorePipelines)"] -->|"addPipeline"| CP["CompositePipeline"]
    SP["StagePipeline::mount"] -->|"registerStage"| CP
    CP -->|"decl() of every PipelineStage"| B["graph::build"]
    B -->|"Graph or GraphError"| CP
    CP -->|"one CompositeSlot per node"| SL["CompositeSlot<br/>static + dynamic tasks"]
    SL -->|"push, lane mask stamped"| SCH["Schedule<br/>(work sets)"]
    SCH --> WK["workers"]
    WK -->|"last task signal: complete()"| CP
```

`CompScheduler::finalize()` calls `CompositePipeline::setup()`. The engines' `start()` calls `CompositePipeline::start()` and their `stop()` calls `CompositePipeline::stop()`, both from an `exec`'d task, so `stop()` parks a fiber, not a thread.

## How it works

### Declaring a stage

```cpp
class AccessKey final {               // only AccessKey::of<T>(), at compile time
public:
	AccessKey() = delete;
	template <AccessResource Type_>
	[[nodiscard]] static consteval AccessKey of() noexcept;
	[[nodiscard]] constexpr type_id id() const noexcept;
};

enum class Lane : u8 { eCritical, eNormal, eBackground };

struct StageDecl {
	string_view name;
	std::span<const AccessKey> reads;
	std::span<const AccessKey> writes;
	Lane lane = Lane::eNormal;
	std::span<const string_view> after;
	std::span<const string_view> before;
};
```

Trimmed from [`StageDecl.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Graph/StageDecl.hpp). Every `PipelineStage` implements `decl() const noexcept`.

- **Access keys** come from a closed set. `AccessKey::of<T>()` compiles only for a `T` with an explicit `access_resource<T>` specialisation in `AccessResources.hpp`, which forward-declares the roots: `Input`, `acs::Registry`, `core::Timing`, `graphics::scene::RenderSceneManager`, `physics::PhysicsSceneSystem`, `reflow::WindowManager`, `scene::SceneBase`. Specialisations do not inherit, so a derived type (a `GameScene`) does not compile; declare its root. There is no empty key and no key from a raw `type_id`.
- **`after`** names stages this one must follow; **`before`** names stages that must follow it. `x before y` is the same edge as `y after x`. An optional pipeline uses `before` to carry the edges that need it, so they vanish when it is not mounted.
- **`lane`** picks the work set: `graph::toMask` maps `eCritical` to `TaskMask::eCritical`, `eNormal` to `eNormal`, `eBackground` to `eLower`.

A real declaration, from [`RenderTickStage.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Schedule/RenderTickStage.cpp#L125-L143):

```cpp
namespace {
	static constexpr graph::AccessKey Reads[] = {
		graph::AccessKey::of<engine::scene::SceneBase>(), graph::AccessKey::of<engine::reflow::WindowManager>()
	};
	static constexpr graph::AccessKey Writes[] = { graph::AccessKey::of<engine::graphics::scene::RenderSceneManager>() };
}

graph::StageDecl RenderTickStage::decl() const noexcept {
	static const string_view after[] = { engine::scene::schedule::ScenePipeline::SceneUpdatePostPhysics };
	static const string_view before[] = { engine::scene::schedule::ScenePipeline::ScenePostProcess };
	return {
		.name = engine::graphics::schedule::RenderScenePipeline::RenderTick,
		.reads = Reads,
		.writes = Writes,
		.lane = graph::Lane::eCritical,
		.after = after,
		.before = before
	};
}
```

Key arrays are namespace-scope `static constexpr` (`of` is `consteval`). Name arrays are function-local `static const`: the stage name constants are dynamically initialised `inline` strings in other translation units, and a namespace-scope array built from them would race static initialisation.

### The frame today

Seventeen stages in the editor; sixteen in the game engine, which mounts no Reflow. With the declared edges the frame is one strict chain, so nothing in the engine frame fans out yet and the conflict check finds no unordered pair.

| # | Stage | Lane | Reads | Writes | Declared edges |
|---|-------|------|-------|--------|----------------|
| 1 | `::Core::TickBegin` | critical | | `Timing` | |
| 2 | `InputTick` | critical | | `Input` | after 1 |
| 3 | `ActorTickPrePhysics` (stub) | critical | `Timing`, `Input` | `Registry` | after 1, 2 |
| 4 | `SceneBroadcastPrePhysics` | critical | `Registry` | `SceneBase` | after 1, 2, 3 |
| 5 | `SceneUpdatePrePhysics` | critical | | `SceneBase` | after 4 |
| 6 | `PhysicsTick` | critical | `Timing`, `SceneBase` | `PhysicsSceneSystem` | after 1, 5 |
| 7 | `PhysicsReadback` | critical | `SceneBase`, `PhysicsSceneSystem` | `Registry` | after 6 |
| 8 | `ActorPhysicsOverlap` (stub) | normal | `PhysicsSceneSystem` | `Registry` | after 7, 3 |
| 9 | `ActorPhysicsCollision` (stub) | normal | `PhysicsSceneSystem` | `Registry` | after 7, 8 |
| 10 | `ActorTickPostPhysics` (stub) | critical | `Timing` | `Registry` | after 7, 9 |
| 11 | `SceneBroadcastPostPhysics` | critical | `Registry` | `SceneBase` | after 6, 10, 5 |
| 12 | `SceneUpdatePostPhysics` | critical | | `SceneBase` | after 11 |
| 13 | `::Reflow::Tick` (editor only) | critical | | `WindowManager` | after 12, **before 14** |
| 14 | `RenderTick` | critical | `SceneBase`, `WindowManager` | `RenderSceneManager` | after 12, **before 15** |
| 15 | `ScenePostProcess` | critical | | `SceneBase` | after 12 |
| 16 | `ActorHousekeeping` | critical | | `Registry`, `SceneBase` | after 15, 10 |
| 17 | `::Core::TickEnd` (`EmptyPipelineStage`) | critical | | | after 15, 16 |

Read from each stage's `decl()`. `SceneBroadcastStage` and `SceneUpdateStage` are one class each, registered twice; the pre/post flag in their options picks name and edges. `TickEnd` has no class of its own: `CorePipeline::mount` registers an `EmptyPipelineStage` with the declaration passed in.

Pipelines and who adds them: `GameEngine` and `EditorEngine::setupCorePipelines` add Core, Actor and Scene; `Graphics`, `Input`, `Physics` and `Reflow` add theirs in their own `setup`.

### The builder

```cpp
struct GraphError {
	enum class Kind : u8 { eUnknownStage, eDuplicateStage, eLaneMismatch, eCycle, eConflict };
	Kind kind;
	Vector<string> stages;   // the cycle in edge order, the two conflicting stages, or the one offender
	Opt<AccessKey> key;
};

struct Graph {
	struct Node { string name; Lane lane; u16 predecessors; Vector<u16> successors; };
	Vector<Node> nodes;
	Vector<u16> order;
};

[[nodiscard]] Result<Graph, GraphError> build(std::span<const StageDecl> decls_);
```

`graph::build` ([`TaskGraph.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Graph/TaskGraph.cpp)) is a pure function. Steps, in order; the first error returns:

1. Index names. A repeated name is `eDuplicateStage`.
2. Resolve every `after` and `before` into one edge set (a `std::bitset<128>` row per node). An unknown name on either side is `eUnknownStage`.
3. Kahn's topological sort, ties broken by stage name, so `order` does not depend on registration order. Leftover nodes are a cycle: the builder walks remaining predecessors until a node repeats and reports that cycle in edge order as `eCycle`.
4. Reachability per node, in reverse topological order.
5. For every pair with no path either way: a key one writes and the other reads or writes is `eConflict`, with both names and the key. Read-read overlap is fine.
6. Transitive reduction: drop `a → c` when a successor of `a` reaches `c`. `predecessors` and `successors` are counted on the reduced set.

What a pass proves: no two stages that may run at the same time touch the same declared state. It does not prove the declared order is the right one, nor that the declarations are complete. More than 128 stages hits `assertrt`.

`eLaneMismatch` comes from `CompositePipeline::setup`, not from `build`: two pipelines may register the same stage name (the stage is ref-counted), and setup merges their declarations into one node (union of reads, writes, `after`, `before`). A lane mismatch between them is an error.

### The runner

`CompositePipeline` owns the graph, one `CompositeSlot` per node and the per-frame counters.

```hg-diagram
sequenceDiagram
    participant W as worker (any)
    participant S as CompositeSlot
    participant P as CompositePipeline
    P->>P: startFrame: pending[i] = predecessors, remaining = N
    P->>S: dispatch(root): dynamicDispatch, submit()
    S->>W: push static + dynamic tasks (lane mask)
    W->>S: onComplete per task (_signals acq_rel)
    S->>P: complete(slot) on the last signal
    P->>P: pending[succ] fetch_sub acq_rel, == 1 dispatches succ
    P->>P: remaining fetch_sub acq_rel
    alt remaining was 1
        P->>P: stopping ? set stop bit : startFrame()
    end
    P->>P: schedule->tick() (ageing)
```

- **`setup()`** mounts every pipeline, merges declarations by stage identifier, calls `build` (on error: log and `assertrt`), binds each node to its slot and stamps the slot's lane mask.
- **`start()`** calls `staticDispatch` on every stage once. Static tasks (repetitive tasks, for example the timing update) stay in the slot and are re-pushed every frame. Then it starts the first frame.
- **Frame start** resets `pending` per node and `remaining` to the node count, then dispatches every node with no predecessors. It runs only on the completion that ended the previous frame, when nothing is in flight, so the stores are relaxed; pushing the first task publishes them.
- **Dispatch** calls `dynamicDispatch` on the node's stages, then `CompositeSlot::submit()`: under the slot's spin mutex it counts every task as one signal, then pushes them. An empty stage pushes one dummy task, so `complete()` never runs inline in the dispatcher (that would recurse through consecutive empty nodes on a fiber stack).
- **Completion**: the task signal that reaches zero calls `complete()`. It decrements `pending` of each successor and dispatches the one that reached zero, then decrements `remaining`. The call that takes `remaining` to zero ends the frame: under stop it sets `stoppedBit` in `_activeCalls`, otherwise it starts the next frame. Every decrement is `acq_rel`, so a successor sees what its predecessors wrote on other workers.
- **`stop()`** sets `_stopping` and waits on the `_stopped` signal. The frame in flight runs to its end. `_activeCalls` counts runner calls inside `complete()`; the last one to leave after the stop bit is set fires `_stopped`, so once `stop()` returns no worker is inside the runner and the pipeline may be destroyed.
- **Serial mode**: `setMaxInFlight(1)` dispatches nodes one at a time in `order`. Only 0 (unbounded) and 1 are accepted (`assertrt`, marked `shortcut:` in source), and only while no frame runs. Nothing in the engine sets it today.
- **Dynamic tasks**: `scheduler::execOnStage(task, stage)` ends in `CompositePipeline::pushTask`, which queues the task on the stage's slot. It runs inside that stage's node on the stage's next dispatch, so the graph orders it like the stage itself. No engine code calls it yet.

### Lanes and ageing

The slot stamps its lane mask on every task it enqueues (`staticEnqueue`, `dynamicEnqueue`), overwriting whatever the stage asked for. A task that yields or parks is re-pushed with its own `mask()`, so the lane survives.

Ageing is still on: `complete()` calls `Schedule::tick()` after every finished stage, which moves every queued task one work set up. A background task therefore reaches the critical set within a few stages. The [lane policy exploration](../../architecture/lane-policy-exploration.md) proposes removing ageing; that is not built.

## Adding a stage

1. If the stage touches state no key covers, add one `access_resource` specialisation to `AccessResources.hpp` for the root type (never for a type and one of its bases). Tests register tag types in their own translation unit instead.
2. Derive from `PipelineStage`; implement `staticDispatch` (tasks created once and repeated every frame), `dynamicDispatch` (tasks per frame, deleted after completion) and `decl()`.
3. In `decl()`, use the stage's own name constant, `static constexpr` key arrays, function-local `static const` name arrays, and edges to existing stages. If your pipeline is optional, put edges that other stages need on your side with `before`.
4. Register it in your `StagePipeline::mount` with `register_.registerStage(...)`, keep the returned handle, and remove it in `dismount`.
5. Add it to `makeFrame` in [`Engine.Scheduler.Test/TaskGraph.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler.Test/TaskGraph.cpp) and update the expected order in `EngineFrameBuilds` (and `GameFrameWithoutReflowBuilds` if it is not editor-only).

Pitfalls:

- **The runner names a node by its stage identifier, not by `decl().name`.** `setup()` takes `stageIdentifier().value` as the node name and ignores the name in the declaration; the builder tests use `decl().name`. Keep both the same constant.
- **A missing edge plus a shared key fails at startup**, with an `assertrt` and a log line. Add the edge; do not drop the key.
- **A missing key passes silently.** Nothing checks that a stage's tasks touch only declared state.
- **One `SceneBase` key covers the scene graph and every scene system** except `PhysicsSceneSystem`. A stage that reaches physics through the scene declares both.
- **Never call `stop()` from a stage body**: it would park the stage's fiber on the stop signal of the frame it belongs to.
- **Never wait inside a stage on a later stage**: in serial mode the later stage is never dispatched.

## Debugging

| Symptom | Where to look |
|---------|---------------|
| `Failed to build the stage graph. (kind: N, stages: ..., key: K)` then an assert at startup | `kind` is the `GraphError::Kind` value (0 unknown, 1 duplicate, 2 lane mismatch, 3 cycle, 4 conflict); `key` is the raw `type_id` value of the access key, not a name |
| a stage never runs | its predecessors never complete; check that each of them reaches its last task signal |
| editor stop hangs | the frame in flight never ends (a stage task waits on something only `stop` would release) |
| a frame order question | build the declarations in a test and read `Graph::order`; ties are broken by name |

## Limits and known issues

- **The frame is a strict chain.** No edge has been relaxed, so the frame never fans out; parallelism inside the engine frame waits for edge relaxation (W02.11) and the scene key split (W02.12).
- **Ageing is unchanged** (`Schedule::tick()` per completion). 15 of 17 stages are critical.
- **Batch tasks count as one signal**; `BatchTask` has no part count.
- **`start()` after `stop()` calls `staticDispatch` again** and the slot keeps the earlier static tasks, so a real stage's repetitive tasks would run twice per frame. The engines start once; the restart test (`StopAndRestartTwice`) uses dynamic tasks only. Read from source, not observed.
- **Universe contexts**: the scene stages (`SceneBroadcastStage`, `SceneUpdateStage`, `ScenePostProcessStage`) create one static task per universe context that exists at `start()` and do not see contexts added later. The physics and actor stages walk the contexts inside their task every frame.
- **`GraphError` is not a `Diagnostic`.** The log prints numbers for kind and key.
- **Headless roles**: without Graphics, `RenderTick` is gone and nothing paces the frame.
- **Teardown**: stop tasks are not graph nodes, so access keys do not order them against frame stages ([stop teardown exploration](../../architecture/engine-stop-teardown-exploration.md)).

## Changing it

- Builder tests (pure, no scheduler): `TaskGraph` and `TaskGraphTest` in [`Engine.Scheduler.Test/TaskGraph.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler.Test/TaskGraph.cpp): unknown names on both sides, duplicates, cycle order, `before` equals reversed `after`, conflicts (write-write, read-write, none for read-read or ordered pairs), transitive reduction, registration-order independence, 128 stages, the 17-stage editor frame and the 16-stage game frame. Compile-time checks there pin the key rules (no derived, unregistered or `const` type; no default or `type_id` construction).
- Runner tests: [`Engine.Scheduler.Test/CompositePipeline.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler.Test/CompositePipeline.cpp), through `TestSchedulerEngine`: diamond with both branches in flight (one worker, by parking), diamond on two workers, an 8-wide fan-out for 2,000 frames on four workers, serial mode in `order`, empty stage through its dummy task, two frames, stop after the in-flight frame, stop and restart, `pushTask` runs next frame, lane mask stamping, plus registration and merge tests. All in target `Heliogrim-Engine.Scheduler.Test`.
- Model: [`CompositePipeline.tla`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Scheduler/Pipeline/CompositePipeline.tla) and `.cfg` beside the source: three workers on a diamond plus an empty node, checking no double dispatch, `remaining` never below the unfinished count, no runner call after the stop release, frame progress and stop return. The header lists five mutations that must fail and what the model folds (serial mode and `tick()` are not modelled; memory orders are argued by hand, Relacy pending). Any change to `complete`, `startFrame`, `dispatch`, `stop` or `CompositeSlot::onComplete` updates the model.
- The game engine frame can only be checked by the builder test; no executable runs `GameEngine`.
