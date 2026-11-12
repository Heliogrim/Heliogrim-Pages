# Task Graph (Design)

**Status**: design, draft 2026-11-11, independently reviewed 2026-11-12 (work chunk [W02.4](../plan/work/concurrency-fibers.md), issue [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84)). Builds on the [scheduler waitables design](scheduler-waitable-design.md) (as built, PR #159) and the [affine threads design](affine-thread-design.md) (as built, PR #164). The implementation plan lives untracked in the engine checkout (`docs/superpowers/plans/2026-11-11-task-graph.md`); W02.5 executes it.

Markers: **Decided** = owner decision (work page Decisions table or the question batches). **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

Every frame runs a fixed set of stages (timing, input, actor ticks, scene mirror, physics, UI layout, render, housekeeping). Today their order is spread over seven `StagePipeline` classes: each pipeline chains its own stages into a total order and names cross-pipeline requirements by string, and `CompositePipeline` turns that into one list with a hand-rolled readiness check marked `TODO` in four places. Nothing says *what* a stage touches, so nothing can tell whether two stages may overlap, and nothing reports a missing edge: a wrong order runs silently.

The task graph replaces that with declarations: a stage says what it reads, what it writes, which lane it runs in and which stages it must follow. The builder derives a frame graph once, checks it (unknown names, cycles, two stages that touch the same state with no order between them) and reports what it found. The runner fans out every stage whose predecessors finished. This is the explicit stage DAG the [actor archetypes design](actor-archetypes-design.md) asks for, and the hook the actor system's per-stage component dispatch plugs into.

## 2. State of the inputs (checked 2026-11-11)

| Input | Found in the engine |
|---|---|
| `CompositePipeline` (`Engine.Scheduler/Pipeline`) | Stages keyed by string, ref-counted when two pipelines register the same name. `resolve()` turns `StagePipeline::declareDependencies` (explicit cross-pipeline requirements) and `orderedStages` (one chain per pipeline) into one insertion order, then runs it with per-stage `generation` and `requiredGeneration` counters. `complete()` scans forward and dispatches every ready stage, so fan-out exists, but the frame restart (`++compIter == end`) is marked "fast forward quickfix", `optimizeDependencies()` is empty, and `pushTask()` (dynamic enqueue onto a stage) logs "Not Implemented" |
| `CompositeSlot` | One per stage. Static tasks are enqueued once at `prepareSlots()` (`staticDispatch`) and re-pushed every frame; dynamic tasks are enqueued by `dispatch()` each frame and deleted on completion. A batch task counts as one signal (`TODO`), an empty stage pushes a dummy task to guarantee progress. `submit()` counts every signal before it pushes the first task, so a fast task cannot complete the stage early; `onComplete` decrements with `release` only (`CompositeSlot.cpp:92`), which is enough on one worker and not on two |
| `StagePipeline` | `mount` registers stages, `declareDependencies` names requirements by string, `dismount` removes them; `isSkippable()` is implemented by every pipeline as `false` and read by nothing |
| `PipelineStage` | `staticDispatch` (repetitive tasks, one per universe context in the scene stages) and `dynamicDispatch` (empty or `TODO` everywhere) |
| Registration | `GameEngine::setupCorePipelines` and `EditorEngine::setupCorePipelines` add Core, Actor and Scene; `Graphics`, `Input` and `Physics` add their pipeline in their own `setup`. `Reflow` adds its pipeline from the `Reflow` submodule's `setup` (`Engine.Reflow/Reflow.cpp:53`), and that submodule is installed by the editor boot only (`Editor.Boot/Editor.cpp:33`); `Heliogrim.Main` (a library holding `main_impl()` for `GameEngine`; checked 2026-11-12: no executable target links it, no test constructs `GameEngine`, and the library itself does not compile, `Heliogrim.Main.cpp:32` initialises `auto*` from `nmpt<Engine>`; the game engine has never been run) installs no Reflow. So the editor mounts seven pipelines, 17 stages; the game engine mounts six, 16 stages, and its `RenderScenePipeline::declareDependencies` asserts on the missing `Reflow::Tick` (`RenderScenePipeline.cpp:33`, `assertrt(... reflowTick != None)`): the game frame cannot pass `CompositePipeline::setup()` as built. Read from source, not observed. `start()` and `stop()` are both called from an `exec`'d task (`GameEngine.cpp:168-170, 267-269`, `EditorEngine.cpp:220-222, 323-325`), so `stop()` parks a fiber on a worker, never a plain thread |
| Tick drive | `complete()` calls `_schedule->tick()` (priority ageing) after every stage, marked "change location" |
| `Schedule` | Four priority work sets (`eCritical`, `eHigher`, `eNormal`, `eLower`) behind the `ScheduleWorkSet` interface, `FifoWorkSet` the only implementation. `push` picks the set from the task's own immutable `mask()` (`Task.hpp:78`), and every stage task is created with the default `eNormal`. `pop(mask)` walks from the worker's own priority downward (`Schedule.cpp:73-83`), so a set is served only while every set above it is empty. `tick()` promotes every queued task one set upward (Lower → Normal → Higher → Critical, `Schedule.cpp:26-30`) and is called after every stage, so within one frame everything queued ends in the critical set. A task that yields, or parks and is woken, is re-pushed with its own `mask()` (`Worker.cpp:189-191`, `Park.cpp:46`): the set a task was pushed to is not remembered |
| Workers | `CompScheduler::setup` overrides its argument with `workers_ = 1uL` (`CompScheduler.cpp:41`) before either count branch runs: every engine and every test runs **one** `eAll` worker. The Critical/IO/All masks exist in the worker code but only one worker is ever built. "Two stages in flight" today means two fibers interleaved by parking on one thread |
| `BatchTask` | Carries one `function<void(u32)>`, `invoke()` runs it once with `0`, completion signals once (`Task.cpp:67-83, 182-185`); there is no part count. The slot's "count the batch size" `TODO` is a stub, not a half-built feature |
| Waitables | `Signal`, `JoinCounter`, `ParkQueue`, `FiberMutex`, `FiberSharedMutex`, cancellation token: as built on PR #159. `CompositePipeline::stop()` already waits on a `Signal` |
| `Scheduler::execOnStage` / `execOnStages` | Declared on the module interface, implemented by `CompScheduler`, called by nothing outside the scheduler |
| Fiber stacks | A stage task completes on its own fiber: `delegate()` calls `ctrl()->onComplete` (`Task.cpp:30-55`), which runs `CompositePipeline::complete` and the next dispatch on that fiber's stack. Stack commit is the open Q02.3 (4 KB today) |
| Tests | `Engine.Scheduler.Test/CompositePipeline.cpp` covers registration, ref counting and mount/dismount (10 tests) with a `TestPipeline` helper; no test runs a frame. The fenced tests W02.2 handed to this chunk are the `#if FALSE` blocks in `test.cpp`: the barrier runtime tests (lines 83-607) and `PriorityShifting` (658-720). Both use the removed `ScheduleStageBarriers` task arguments, not stages; `PrioritySorting` (609) is live and covers the sort across sets |
| Keys | `hg::type_id` (`Engine.Common/Meta/TypeId.hpp`) is the engine's type identity; `refl::ctid<T>()` (`Engine.Reflect/Compile/TypeId.hpp:9`) is `consteval` and yields it for any type, complete or not, and the archetype design will use it for component types. The scene stages act on `scene::SceneBase` (`Scene` is a template); the render stage touches `graphics::scene::RenderSceneManager`. Stage names are `static const inline string` members (`CorePipeline.hpp:16`), dynamically initialised, not `constexpr` |
| Diagnostics | No `Diagnostic` type yet (W05.1 is ready, not done). `Result<T, E>` (`Engine.Common/Expected.hpp`) is the engine's result type |
| Layering debt from W02.2 | `Engine.Async/Future/Schedule.hpp:15` reaches `Engine::getEngine()->getScheduler()->exec(...)` to hop a continuation; the waitables design (10a) assigns the seam fix to this chunk |

## 3. Goals

1. One declaration per stage: `{ name, reads, writes, lane, after }`. No more string lookups of other pipelines' stages spread over `declareDependencies`.
2. A builder that reports, at setup, every unknown name, every cycle and every pair of stages that may overlap while touching the same state. A wrong frame order is a startup error, not a race.
3. A runner that starts every stage whose predecessors finished, in the stage's lane, with an in-flight bound of one stage for the serial check that W02.5 and W02.6 need. Its counters are correct on any worker count, not only the one worker that exists today.
4. The actor archetype dispatch fits without a second mechanism: a stage's tasks are whatever its `PipelineStage` enqueues, and component types are valid access keys.
5. Every existing stage migrated with its sets written down (section 8), behaviour unchanged.

## 4. Non-goals

- Per-task dependencies inside a stage (that is `JoinCounter`, as built).
- Lane policies beyond FIFO (**Decided** Q02.2: FIFO until the full fiber feature set exists and is measured; W02.0 produces the numbers).
- Deterministic mode, state hash harness (W02.6), replay (S59).
- Work stealing or per-worker queues (W02.0, then W02.5 behind measurement).
- Making actor ticks do anything (actor system milestone 0).
- Stages that change while the frame runs; the graph is rebuilt between frames only.
- Ageing and lane policy changes (`Schedule::tick()` placement, which sets promote). This chunk keeps today's ageing verbatim; W02.5 "lanes" changes it behind a measurement (6.4, Q02.8).

## 5. Anti-goals

- No frame order that depends on module registration order. Two stages with no declared order and a shared write are an error, never "whichever was registered first".
- No stage declaration through strings for things that have a type. Access keys are `type_id`s.
- No second task type, no new allocator, no new bundle (section 7.1).

## 6. Contract

### 6.1 Declaration (**Proposal**)

```cpp
namespace hg::engine::scheduler::graph {
	using StageName = string_view;        // the existing stage identifier constants
	using AccessKey = hg::type_id;        // the type of the state touched

	enum class Lane : u8 { eCritical, eNormal, eBackground };

	struct StageDecl {
		StageName name;
		std::span<const AccessKey> reads;
		std::span<const AccessKey> writes;
		Lane lane = Lane::eNormal;
		std::span<const StageName> after;
		std::span<const StageName> before;
	};
}
```

- `reads` and `writes` name the state the stage's tasks touch; a key in `writes` need not be repeated in `reads`. A key stands for one whole piece of state: when a sub-part gets its own key (section 8: `PhysicsSceneSystem` inside `Scene`), every stage that touches the sub-part declares the sub-part's key and the stages that touch the whole keep the whole key; a stage that reaches the sub-part through the whole declares both. Otherwise the conflict check sees two keys and no overlap.
- `after` lists stage names the stage must follow; `before` lists stage names that must follow it. A `before` edge is the same edge declared from the other end, so a pipeline that is not always mounted (Reflow is installed by the editor boot only, Graphics will be absent in a headless role, section 2) carries its own edges and takes them with it when it is absent. Without `before`, `RenderTick after Reflow::Tick` lives in the Graphics pipeline and the game engine fails at setup, as it does today. These edges are authoritative: the sets never add an edge, they only check for missing ones (6.2). Reason: deriving an order from sets needs a tie-break, and every tie-break is registration order, which anti-goal 1 forbids. This deviates from the wording of #84 and the topic page ("the builder derives edges from read and write sets"); the check is what those pages want from the derivation, without the tie-break.
- `lane` picks the `Schedule` work set the stage's tasks are pushed to (6.4).
- A `PipelineStage` provides its declaration through one new virtual, `decl() -> StageDecl`. The key spans point at `static constexpr` arrays (`refl::ctid` is `consteval`); the name spans point at function-local `static const` arrays inside `decl()`, because the stage name constants are dynamically initialised `inline` strings in other translation units (section 2) and a namespace-scope array built from them would race static initialisation. `StagePipeline::declareDependencies` and `_orderedStages` are removed; `mount` and `dismount` stay as the registration unit.
- Two pipelines registering the same stage name (ref-counted today, tested by `DuplicateRegistrationSharesStage`) produce one node whose declaration is the union of their reads, writes, `after` and `before`; a lane mismatch is an error.

### 6.2 Builder (**Proposal**)

```cpp
struct GraphError {
	enum class Kind : u8 { eUnknownStage, eDuplicateStage, eLaneMismatch, eCycle, eConflict };
	Kind kind;
	Vector<string> stages;   // the cycle in order, the two conflicting stages, or the one offender
};

[[nodiscard]] Result<Graph, GraphError> build(std::span<const StageDecl> decls_);
```

Build steps, in order; the first error returns.

1. Index names; a repeated name is `eDuplicateStage` (the union of 6.1 happens before build, in `CompositePipeline`, so a duplicate here is a bug).
2. Resolve every `after` and `before` name; unknown is `eUnknownStage` on either side. A `before` entry `x before y` becomes the edge `x → y`, the same as `y after x`; from here on there is one edge set.
3. Topological sort (Kahn). Ties are broken by stage name so the order is the same whatever the registration order. Remaining nodes form a cycle: report it as `eCycle` with the nodes of one cycle in edge order.
4. Reachability: one bitset per node (`std::bitset<128>`; `registerStage` already asserts the slot index is at most 127). `reach[a]` holds every node after `a`, transitively.
5. Conflict check: for every unordered pair `(a, b)` with neither `reach[a][b]` nor `reach[b][a]`: if `writes(a) ∩ (reads(b) ∪ writes(b)) ≠ ∅` or the mirror, report `eConflict` with both names and the key. Read-read overlap is fine.
6. Transitive reduction on the edge set (drop `a → c` when some `b ∈ successors(a)`, `b ≠ c`, has `reach[b][c]`; `reach` is computed in step 4, before any edge is dropped). This is the empty `optimizeDependencies()` done; it only shrinks the per-frame counting work and never changes the order.
7. Emit `Graph { nodes: Vector<Node { name, lane, predecessors: u16, successors: Vector<u16> }>, order: Vector<u16> }`. The builder knows no slots; the runner maps a node to its slot through the registered stage (`registerStage` assigns slots, `CompositePipeline.cpp:100-112`). `predecessors` and `successors` are both counted on the reduced edge set of step 6; a count from the unreduced set would leave a node waiting for a decrement that never comes.

What the check proves, and what it does not: a pass means no two stages that may overlap touch the same declared state. It does not mean the declared order is the right one (`RenderTick before SceneUpdatePostPhysics` passes as readily as the reverse), and it does not mean the declarations are complete: a stage that touches state it did not declare passes. The order is the author's; the declarations are checked by the W02.6 state-hash harness, which is why every relaxation in W02.5 runs serial against parallel.

`GraphError` converts to a `Diagnostic` with one function once W05.1 lands; until then `CompositePipeline::setup()` logs it and asserts. Today the cross-pipeline lookups `assertrt` and the resolver throws `std::runtime_error("")` (`CompositePipeline.cpp:391, 584`); no caller catches it, so the throw goes.

### 6.3 Runner (**Proposal**)

`CompositePipeline` keeps its name and public surface (`setup`, `start`, `stop`, `destroy`, `addPipeline`, `removePipeline`, the `StageRegister` interface) and replaces its body:

- `setup()`: mount every pipeline, collect `decl()` from every `PipelineStage`, merge by name (6.1), `build`, keep the `Graph`; create one `CompositeSlot` per node as today.
- `start()`: `staticDispatch` once per stage into its slot, as today (`prepareSlots`). Behaviour unchanged: the scene stages create one repetitive task per universe context that exists at start, and a context added later gets none. That gap is older than this design and belongs to the universe and actor work; it is noted in section 11.
- Frame start: every node's `pending` counter is reset to its predecessor count, `remaining` is set to the node count, and every node with zero predecessors is dispatched. The reset runs on the worker that completed the last node of the previous frame, when no other node is in flight, so it needs no lock.
- Dispatch of a node: `dynamicDispatch` into its slot, then `submit()` pushes the slot's tasks, each stamped with the node's lane mask (6.4). A node with no tasks keeps pushing today's dummy task. Reason: completion runs on the completing task's fiber (section 2), so an inline completion would recurse `complete → dispatch → complete` through every consecutive empty node on a fiber stack whose commit is the open Q02.3, and a graph of only empty nodes would never return to the worker loop; the dummy is the yield point that keeps `complete` one level deep. One extra task per frame for `TickEnd` is the price.
- Completion of a slot (last task signal): for every successor, decrement `pending`; zero dispatches it. Decrement `remaining`; zero is the frame end: if stopping, set the stop signal, else start the next frame. Completion runs on whichever worker finished the last task, so `pending` and `remaining` are atomics and a successor is dispatched by exactly the decrement that reached zero; the frame restart happens on the one completion that reached zero `remaining`. Every completion decrement (`_signals`, `pending`, `remaining`) is `acq_rel`: the decrement that reaches zero runs the successor, which reads what every predecessor task wrote on other workers. Today's `release` (`CompositeSlot.cpp:92`) is a one-worker artefact and goes. The order inside `complete` is successors first, then `remaining`: a node's successors cannot complete before it, so `remaining` cannot reach zero early either way, but the successor-first order keeps the frame-end branch the last thing a frame does.
- Ageing: `_schedule->tick()` stays where it is, after every completion (non-goal; 6.4 says why).
- `stop()`: sets `_stopping`, waits on `_stopped` as today. The frame-end branch reads `_stopping` once; a `stop()` that lands after that read waits for one more frame. Both engines call `stop()` from an `exec`'d task (section 2), so the wait parks a fiber and the worker keeps running the frame.
- `maxInFlight` (**Proposal**): a runner setting, default unbounded, set to 1 by the W02.5 serial-versus-parallel check and by W02.6. With 1, dispatch pulls the next ready node in topological order instead of fanning out.
- Batch tasks keep counting as one signal: `BatchTask` has no part count (section 2), and adding one touches `Task`, `Worker` and the completion path, which is a separate, model-checked change. The slot's `TODO` comment goes; a batch is one task until the task model grows.
- `pushTask` (dynamic enqueue through `Scheduler::execOnStage`) enqueues into the slot's dynamic list under the slot's existing spin mutex, for the stage's next dispatch; `submit()` counts and pushes under the same mutex, so a task lands either in this dispatch or the next, never half-counted. If the stage is in flight the task runs next frame. No caller exists today; the behaviour is defined so the first one has a contract.

No new waitable is needed: the counters are plain atomics (`pending`, `remaining`, the slot's signal count), reset per frame, never waited on; `stop()` keeps its `Signal`.

**Workers (Proposal, for the owner)**: the `workers_ = 1uL` override in `CompScheduler::setup` means nothing has ever run on two workers. With one worker, fan-out is fiber interleaving and the W02.5 "parallel where the sets allow" check measures nothing. W02.5 lifts the override (auto count by default, the existing `USE_WORKER_COUNT` path to force a number, 1 for the serial check) as its own task with a reentrancy pass over `dispatch`, `complete`, `submit` and `stop`, and runs the editor on it. Until the owner says yes, the plan keeps that task last and the editor default at 1. Recorded as follow-up question Q02.7 on the work page. The runner above is written for N workers regardless, so lifting the override later changes no runner code, only the test engine's worker count.

### 6.4 Lanes (**Proposal**)

| Lane | `Schedule` work set | Who |
|---|---|---|
| `eCritical` | `TaskMask::eCritical` | Frame stages on the critical path: timing, input, physics, render, housekeeping |
| `eNormal` | `TaskMask::eNormal` | Frame stages off the critical path, `exec`'d engine work |
| `eBackground` | `TaskMask::eLower` | Streaming decode, navmesh builds, imports; never a frame stage |

How a task reaches the set: `Schedule::push(task)` reads the task's mask, and stage tasks are all created `eNormal`. A push overload that takes the set as an argument does not work: a task that yields or parks is re-pushed with `task->mask()` (`Worker.cpp:189-191`, `Park.cpp:46`), so the lane would be lost at the first yield. **Proposal**: the lane is stamped on the task. `TaskDelegate::_mask` loses its `const` and gains a setter (the public `Heliogrim/Async/Task.hpp:87` already exposes `ref<TaskMask> mask()`); `CompositeSlot::staticEnqueue` and `dynamicEnqueue` set it to the node's lane mask, so every push of that task, first or re-push, lands in the lane's set. `Schedule::push` is unchanged. Tasks created elsewhere (`exec`) keep the mask they were made with. The mapping `Lane → TaskMask` lives in one function.

Ageing: `Schedule::tick()` promotes every set one step upward after every stage, so today a background task is critical after three stages and the lanes are labels that pick the starting set. **This chunk keeps that** (non-goal 7; Goal 5 says behaviour unchanged). The first draft of this page proposed `tick()` once per frame and no promotion of `eLower`. Checked against `Schedule::pop` (section 2) on the one worker that exists, that proposal does this: `complete` refills the critical set inline before the worker's next `pop`, so with a strict chain (section 8) the worker never sees an empty critical set between stages. An `eNormal` `exec`'d task (every editor action, asset load, and the engines' own `start()` and `stop()`) would then run only after two frame-start promotions, and an `eLower` task would never run until a stage task parks. That is not a label change; it is the editor's responsiveness. The change belongs to W02.5 "lanes" with a measurement and a second worker, recorded as Q02.8 on the work page; it is also in tension with Q02.2 (keep the global per-priority FIFO, measure before changing the queue policy).

The policy seam is the existing `ScheduleWorkSet` interface: a lag-aware policy for the background lane replaces `FifoWorkSet` for that one set and nothing else changes. `Lane` is the public word; `TaskMask` stays the internal one.

### 6.5 Archetype fit

The actor system wants component hooks scheduled per stage (actor-system section 3) and asks who declares read and write sets (its decision 3, open). This design supports both answers: an `ActorTickStage` declares `writes = { type_id<acs::Registry> }` today; when hooks register per component type, the stage's declaration can carry the union of the registered component types' keys (computed at mount, the spans then point at a `Vector` owned by the stage), and the conflict check (6.2 step 5) tells the two actor stages apart from the scene mirror at the component level. The relocation barrier (archetype section 9) is the `ActorHousekeeping` stage: it writes `Registry` and every scene system, so any stage that reads components and is unordered against it is reported.

## 7. Placement and tests

### 7.1 Placement (**Proposal**, deviates from the work page)

The work page places the builder in a new bundle `Engine.Scheduler.Graph`. That bundle would need `Engine.Scheduler` (tasks, `Schedule`, slots) and `CompScheduler` would need it back: a cycle. The builder goes in `Engine.Scheduler/Graph/{StageDecl.hpp, TaskGraph.{hpp,cpp}}` and the runner stays in `Engine.Scheduler/Pipeline/CompositePipeline.{hpp,cpp}`; `Composite/CompositeStage.hpp`, `CompositeDependency.hpp` and `StageDependency.hpp` are deleted. Tests go in `Engine.Scheduler.Test/TaskGraph.cpp` (builder, no engine) and the existing `CompositePipeline.cpp` (runner, through `TestSchedulerEngine`).

### 7.2 Tests

Builder (pure, no scheduler): unknown name in `after` and in `before`; duplicate; cycle of three reported in order; `x before y` builds the same graph as `y after x`; conflict on write-write and on read-write; no conflict on read-read; transitive reduction drops the redundant edge and `predecessors` matches `successors`; same `order` for two registration orders of the same declarations; 128 stages build; the seventeen rows of section 8 build, and the sixteen without Reflow build (the game engine's frame).

Runner (through `TestSchedulerEngine`, one worker, so "in flight" means interleaved fibers): a diamond `A → {B, C} → D` runs B and C with both in flight (B parks on a `Signal` that C sets, so the frame only completes if C was dispatched while B was parked); `maxInFlight = 1` runs the same graph in `order` (plain bodies: B waiting on C would deadlock in serial mode); two frames run back to back and each stage ran twice (the test thread calls `stop()` after D's second run; a body cannot, it would park its own fiber on the stop signal); `stop()` returns after the frame that was in flight and the test orders "stop requested" before "B released" through a flag the test polls (`isStopping()`), or the test is racy; `pushTask` during a stage's flight runs the task in the next frame (`Scheduler::execOnStage` reaches only the scheduler's own pipeline, `CompScheduler.cpp:192`, not a pipeline a test constructs); `tick()` still promotes every set (pins today's ageing, replaces the fenced `PriorityShifting`). Two runner checks are deterministic only without a worker and run on a bare `Schedule`, popped by hand (`CompScheduler::setup` starts an `eAll` worker that would steal the task): an empty stage queues exactly its dummy and does not complete inline (its successor is not queued until the dummy ran); a task enqueued into a stage declared `eBackground` carries `mask() == eLower` and is popped from the `eLower` set.

Fenced tests (W02.2 handed them here): the `#if FALSE` barrier runtime tests ordered tasks between named barriers; the runner tests above are their port, stage for barrier. `PriorityShifting` is replaced by the `tick()` test. Both blocks are deleted in the plan, each replacement named in the commit.

Engine: no test constructs `GameEngine` or `EditorEngine`, so this is a manual check the owner runs (editor starts, ticks, stays up, stops), as for W02.2 and W02.3; `Engine.Scheduler.Test` stays green (38 at PR #164, plus the above). The game engine cannot be checked by running: `Heliogrim.Main` is a library no executable links (section 2). Its sixteen-stage frame is pinned by the builder test (`GameFrameWithoutReflowBuilds`); that today's resolver asserts on it is read from `RenderScenePipeline.cpp:33`, not observed. A runnable game executable is the owner's call (section 11).

### 7.3 Model (**Decided**: the repository rule for atomics in `Engine.Scheduler`)

The runner's `pending` and `remaining` counters are a counting protocol across workers, so the `verifying-concurrency` skill applies: `CompositePipeline.tla` + `.cfg` beside `CompositePipeline.cpp`, PlusCal, one label per atomic step of `dispatch`, `complete` and the frame restart, N workers taking any ready node. Checks: no node dispatched twice in one frame, `remaining` reaches zero only after every node completed and is never below the count of unfinished nodes (a node marks itself done before its `remaining` decrement, so equality is false in that window and `>=` is the invariant), a frame that started completes or the pipeline stops (`~>` under weak fairness; the frame-end reset is its own label after the decrement, or `remaining = 0` is never a state and the property holds only through `stopped`), `CHECK_DEADLOCK TRUE` with the stopped state as the only terminal state; N = 3 workers on the diamond plus one empty node. Mutation: dispatching on a separate read of `pending` after the decrement (two workers both see zero) must fail the first invariant; resetting the counters before the last decrement must fail the second. Tier 2b (Relacy) stays pending like every other row of the skill's queue; the memory orders are marked unverified there. The stress test of tier 1 only exercises interleavings once the one-worker override is lifted, so it ships with that task.

## 8. Migration: every stage with its sets

Names are the existing constants. Lanes and edges keep today's order exactly; the "could relax" column names edges this design did not verify and leaves in place. Keys are `refl::ctid<T>()` of the named types; `scene::Scene` below means `scene::SceneBase`, `graphics::SceneManager` means `graphics::scene::RenderSceneManager`. Key rule (6.1): `Scene` covers the scene graph and every scene system; `PhysicsSceneSystem` is the one system with its own key because the physics stages mutate only it, and a stage that reaches it through the scene declares `Scene` as a read as well.

Sets of the live stages were read from their source (`TickTimingStage`, `InputTickStage`, the scene stages, the physics stages, `ReflowFlowStage`, `RenderTickStage`, `ActorHousekeepingStage`). The actor tick and physics-callback stages are stubs (`// TODO: Tick actor`, `[] static { return true; }`): their rows declare the sets the actor system's milestone 0 will need, so the order protects them from day one; nothing in them touches that state yet.

| Stage | Pipeline | Lane | Reads | Writes | Edges (today's, kept) | Could relax (unverified) |
|---|---|---|---|---|---|---|
| `::Core::TickBegin` (`TickTimingStage`) | Core | Critical | | `core::Timing` | | |
| `InputTick` (`InputTickStage`) | Input | Critical | | `input::Input` | after TickBegin | |
| `ActorTickPrePhysics` | Actor | Critical | `core::Timing`, `input::Input` | `acs::Registry` | after TickBegin, InputTick | |
| `SceneBroadcastPrePhysics` | Scene | Critical | `acs::Registry` | `scene::Scene` | after TickBegin, InputTick, ActorTickPrePhysics | |
| `SceneUpdatePrePhysics` | Scene | Critical | | `scene::Scene` | after SceneBroadcastPrePhysics | |
| `PhysicsTick` | Physics | Critical | `core::Timing`, `scene::Scene` | `physics::PhysicsSceneSystem` | after TickBegin, SceneUpdatePrePhysics | |
| `PhysicsReadback` | Physics | Critical | `scene::Scene`, `physics::PhysicsSceneSystem` | `acs::Registry` | after PhysicsTick | |
| `ActorPhysicsOverlap` | Actor | Normal | `physics::PhysicsSceneSystem` | `acs::Registry` | after PhysicsReadback, ActorTickPrePhysics | |
| `ActorPhysicsCollision` | Actor | Normal | `physics::PhysicsSceneSystem` | `acs::Registry` | after PhysicsReadback, ActorPhysicsOverlap | Overlap and Collision both write the registry; the chain stays until the actor system says the sets are disjoint |
| `ActorTickPostPhysics` | Actor | Critical | `core::Timing` | `acs::Registry` | after PhysicsReadback, ActorPhysicsCollision | |
| `SceneBroadcastPostPhysics` | Scene | Critical | `acs::Registry` | `scene::Scene` | after PhysicsTick, ActorTickPostPhysics, SceneUpdatePrePhysics | |
| `SceneUpdatePostPhysics` | Scene | Critical | | `scene::Scene` | after SceneBroadcastPostPhysics | |
| `::Reflow::Tick` (`ReflowFlowStage`) | Reflow | Critical | | `reflow::WindowManager` | after SceneUpdatePostPhysics; **before RenderTick** | Reflow reads no scene state and no timing that this chunk could find; W02.5 may drop the `after` edge after a check of the UI widgets that mirror scene data |
| `RenderTick` (`RenderTickStage`) | Graphics | Critical | `scene::Scene`, `reflow::WindowManager` | `graphics::SceneManager` | after SceneUpdatePostPhysics; **before ScenePostProcess** | |
| `ScenePostProcess` | Scene | Critical | | `scene::Scene` | after SceneUpdatePostPhysics | |
| `ActorHousekeeping` | Actor | Critical | | `acs::Registry`, `scene::Scene` | after ScenePostProcess, ActorTickPostPhysics | |
| `::Core::TickEnd` (`EmptyPipelineStage`) | Core | Critical | | | after ScenePostProcess, ActorHousekeeping | The "guarantee tick end is latest" hotfix is no longer load-bearing: the frame ends when every node completed (6.3) |

Two edges changed ends, not direction: `RenderTick after Reflow::Tick` became `Reflow::Tick before RenderTick`, and `ScenePostProcess after RenderTick` became `RenderTick before ScenePostProcess`, so the optional pipelines (Reflow, Graphics) own the edges that need them. The graph with all seven pipelines is identical to today's; with Reflow absent (the game engine, section 2) it builds, where today's resolver asserts. The Core pipeline's own `TickBegin → TickEnd` chain edge is implied transitively and not listed.

Observations from the table, for W02.5:

- With the kept edges the frame is a strict chain: every node has exactly one ready successor, so the engine frame never fans out and only the synthetic diamond test does. The conflict check is therefore vacuous on the migrated frame (no unordered pair exists) and earns its keep only when an edge is relaxed. Parallelism comes from relaxing edges the sets prove safe, one at a time, with the serial hash check. The first candidates: `Reflow::Tick after SceneUpdatePostPhysics` (Reflow touches no scene key, so it could run from `TickBegin` alongside the actor and physics chain) and `InputTick after TickBegin` (Input reads no timing).
- `Scene` is one key for all scene systems. Splitting it per system (`RenderSceneSystem`, `PhysicsSceneSystem`, later audio) is the first relaxation worth trying: broadcast and update already pass flags per phase. The key rule above applies to every split.
- `isSkippable()` is removed; nothing reads it.

## 9. Layering seam (handed over from W02.2, section 10a)

`Engine.Async/Future/Schedule.hpp` hops continuations through `Engine::getEngine()->getScheduler()->exec`. Checked here: the fiber control block carries `ptr<Schedule> schedule`, so a `then` called on a fiber could capture it. But completions also come from affine threads (platform, IO) and from plain threads in tests, where no fiber exists, so the engine fallback stays and with it the `Engine.Core` include. A handle on the state would move the lookup without cutting the layer. **Proposal**: deferred; the cut needs `Engine.Async` to receive a scheduler handle at construction, which is W10 (layering) work. The `Engine.Accel.Lang → Engine.Async` link (for `FiberSharedMutex`) stays for the same reason.

## 10. Done when

- `TaskGraph::build` tests pass for every error kind, for `before`, and for order stability.
- The seventeen stages of section 8 are declared through `decl()`; `declareDependencies`, `_orderedStages`, `isSkippable`, `CompositeStage`, `CompositeDependency` and `StageDependency` are gone; the `#if FALSE` blocks in `test.cpp` are gone with their replacements named.
- The editor runs the migrated frame; the sixteen-stage game frame builds (`GameFrameWithoutReflowBuilds`); `Engine.Scheduler.Test`, `Heliogrim.Test` and the editor action tests stay green.
- `CompositePipeline.tla` passes at N = 3 with both mutations failing, and the skill's queue table has its row (section 7.3).
- `maxInFlight = 1` reproduces today's serial order; the diamond test shows two stages in flight.
- A task enqueued into a background stage carries the `eLower` mask; `tick()` behaves as today.
- Every completion decrement is `acq_rel`; no runner code changes when the worker count changes.
- Owner's manual editor run on the migrated frame; with the worker override lifted only if Q02.7 is answered yes.

## 11. Left to the builder and known gaps

- Exact span storage for `decl()` within the rule of 6.1 (function-local statics for names; a `Vector` on the stage when the keys are computed at mount).
- Bitset width if the 128-stage assert is lifted (a `Vector<u64>` row per node).
- Log format of `GraphError` until `Diagnostic` exists.
- Not this chunk: ageing and lane policy (Q02.8, W02.5); scene stages only see universe contexts that exist at `start()` (section 6.3); a batch task has no part count (section 2); `RenderTickStage` keeps a function-local `static` ring buffer that the conflict check cannot see (fine while there is one render task); `start()` after `stop()` would enqueue the static tasks a second time (`prepareSlots` has no guard), as today.
- Open for the owner: a headless role (S58) without Graphics drops `RenderTick`, which is the only stage that holds the frame against the GPU; nothing in this design paces a frame without it. Not a regression, but the first headless run will spin.
- Open for the owner: no executable links `Heliogrim.Main`, nothing constructs `GameEngine`, and `Heliogrim.Main` does not compile (section 2), so "the game engine starts" cannot be a check of this chunk. Fixing the one line and adding a game executable target is a separate chunk.

## 12. Decisions made in this document (for review)

1. `after` edges are authoritative; sets only check (6.1). No order is ever derived from registration order.
2. Access keys are `type_id`s; one key per touched state type, `Scene` kept as one key for now (6.1, 8).
3. Conflicts, cycles and unknown names are startup errors through `Result<Graph, GraphError>` (6.2).
4. Topological ties break by name (6.2 step 3).
5. The builder lives inside `Engine.Scheduler`, not a new bundle (7.1).
6. `maxInFlight` is the serial switch W02.5 and W02.6 use (6.3).
7. Lanes map onto the existing priority work sets by stamping the task's mask at slot enqueue, because re-push after yield or park reads `task->mask()`; ageing is unchanged in this chunk and goes to W02.5 behind Q02.8 (6.4).
8. Batch tasks stay one signal; no part count in this chunk (6.3).
9. Today's edges are kept verbatim in the migration; two change the declaring end (`before`) so optional pipelines own them; relaxations belong to W02.5 (8).
10. The `Future::then` scheduler seam is deferred to the layering work; a fallback would keep the include (9).
11. Lifting the one-worker override is a W02.5 task gated on Q02.7 (6.3).
12. `StageDecl` carries `before` as well as `after`; both resolve to one edge set, unknown names on either side are errors (6.1, 6.2).
13. The dummy task for an empty stage stays: completion runs on the completing fiber and must not recurse (6.3).
14. Every completion decrement is `acq_rel`; the runner is written for N workers from the start (6.3).
15. The runner's counters get a TLA+ model beside the source, mutation-checked, per the repository rule; Relacy stays pending as for every primitive; the stress test ships with the worker-override task (7.3).
16. The game engine is not a check of this chunk: `Heliogrim.Main` is an unlinked library that does not compile; the sixteen-stage frame is pinned by a builder test instead (2, 7.2).
