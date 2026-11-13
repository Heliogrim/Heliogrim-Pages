# Engine Stop Teardown (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md).

**Origin**: editor stop crash [#178](https://github.com/Heliogrim/Heliogrim-Engine/issues/178) on 2026-11-13, on `feat/task-graph` with the #158 fixes merged. Related: [#150](https://github.com/Heliogrim/Heliogrim-Engine/issues/150) (stop phases between `TickEnd` and `TickBegin`), [#158](https://github.com/Heliogrim/Heliogrim-Engine/issues/158), [#160](https://github.com/Heliogrim/Heliogrim-Engine/issues/160).

## 0. Current state (checked 2026-11-13, `feat/task-graph` @ `7776f6ea`)

- `EditorEngine::stop()` and `GameEngine::stop()` run three phases as plain `scheduler::exec` tasks, each followed by a `Signal` wait: (1) sub-modules in reverse order plus universe removal, (2) core modules, (3) `CompositePipeline::stop()`. Frames keep running until phase 3. **The scheduler stops last, and this stays so**: module stops can spawn tasks and rely on frames (housekeeping).
- The stop tasks are not task-graph nodes, so the stage access keys (`AccessKey::of<WindowManager>()`, `...<SceneBase>()`, `...<RenderSceneManager>()`) do not order them against frame stages.
- `CompositePipeline::pushTask` (behind `scheduler::execOnStage`) queues a dynamic task on the stage's slot. It runs inside that stage's node in the next frame, so the graph orders it like the stage itself. Test: `CompositePipelineTest.ExecOnStageRunsNextFrame`.

## 1. What overlaps a running frame during stop

| # | Teardown (stop task) | Frame reader | Kind |
|---|---|---|---|
| R1 | `Reflow::stop` → `WindowManager::destroy` destroys windows and widget trees | `ReflowPass::execute` calls `wnd.render(&uiCmd)` on the live widget tree (`ReflowPass.cpp:220`), inside `RenderTickStage` | CPU data race on shared state |
| R2 | `Viewport::tidy` calls `_swapChain->destroy()` (`Viewport.cpp:124`) while `RenderTarget` still holds a strong `smr<Swapchain>` | in-flight `RenderTickStage::tickTargets` holds `smr<RenderTarget>`; `TmpEndPass` barriers on the freed image (the #178 trace) | explicit destroy of a ref-counted object |
| R3 | `RenderTarget::tidy` frees passes and fences without waiting for them | GPU work submitted in earlier frames | GPU lifetime |
| R4 | `UniverseRemoveEvent` hook: `unregisterScene` + `cleanupTargetsByScene` mutate `RenderSceneManager` (`Graphics.cpp:103-104`) | `selectInvokeTargets` iterates `_primaryTargets` | CPU data race on shared state |
| R5 | `Graphics::destroy` (shutdown) resets `_surfaceManager` before the queue `waitIdle` (`Graphics.cpp:238-245`) | GPU presents | GPU lifetime, separate bug |

Two different problems: **exclusion** (R1, R4: someone mutates state a frame stage reads) and **lifetime** (R2, R3, R5: someone frees what an in-flight task or the GPU still uses).

## 2. Options

### A. Frame-boundary queue (on hold)

**On hold** (owner, 2026-11-13, Q-ST1): considered alternative and possible fallback, not built. Revisit if D proves insufficient, e.g. for a system that cannot declare access keys.

A queue drained in `CompositePipeline::complete()` when `_remaining` reaches 0, before `startFrame()`. Stop phases run there.

- Pro: one rule, independent of declared keys, covers systems we do not manage.
- Con: a hard sync point; any runtime caller stalls the whole frame.
- Con: does not cover work that may cross frames (plain `exec` tasks, async IO, requests) or the GPU (R2, R3, R5 stay).
- Overhead (estimated, not measured): one atomic load and a branch per frame end; when non-empty, the jobs plus one dispatch hop.

### B. Stop the pipeline first

Rejected by owner 2026-11-13: module stops may spawn tasks and need frames.

### C. Retire, then reclaim (lifetime)

- Teardown unregisters and drops its reference; it never calls `destroy()` on a shared, ref-counted object. The last reference frees it (`~VkSwapchain` already calls `destroy()`).
- Owners of GPU work wait for their own completion before freeing (`RenderTarget::tidy` waits its passes' fences). A device-level deferred-deletion queue keyed on a GPU timeline value is the general form; not needed for #178.
- Pro: no sync point; works for tasks that cross frames; per-object cost only at teardown.
- Con: fixes lifetime only, not R1/R4.

### D. Stage-owned teardown (exclusion)

A module tears frame-visible state down **on its own stage** via `execOnStage` and waits for completion. The graph's access keys then serialise it only against stages that conflict (`WindowManager` writer vs. `RenderTick` reader); unrelated stages keep running.

- Pro: no new scheduler mechanism; exclusion is as narrow as the declared keys; a third-party module follows the same rule with its own stage.
- Con: correctness depends on correct keys, like every stage; a teardown touching state outside its stage's keys is a bug (R4 needs the `RenderTick` stage, which writes `RenderSceneManager`).
- Con: the stop task waits up to one frame per posted teardown.
- Overhead: none on the hot path; `CompositeSlot::submit` already locks the slot and drains its (empty) dynamic queue per node per frame. Per teardown: one locked push and one task.

## 3. Proposal (not decided)

C + D. Lifetime by ownership (C) handles cross-frame and GPU work without a sync point; exclusion by stage (D) handles shared CPU state with the existing graph keys. The pipeline still stops last. A (frame-boundary queue) is on hold as a documented fallback for systems that cannot declare keys.

Plan: engine checkout, untracked, `docs/superpowers/plans/2026-11-13-stop-teardown-ownership.md`.

## 4. Open questions

- **Q-ST1** (answered 2026-11-13): D is the rule for third-party modules; A is on hold as a considered alternative and fallback (section 2.A), not built now.
- **Q-ST2** (answered 2026-11-13, default): no general device deferred-deletion queue now; add it when a second owner needs it.
- **Q-ST3** (answered 2026-11-13, default): R5 (`Graphics::destroy` order) gets its own issue ([#179](https://github.com/Heliogrim/Heliogrim-Engine/issues/179)) and atomic commit, outside the #178 plan. `Surface::destroy` (`Surface.cpp:57-67`) also destroys its `smr` swapchain explicitly, same pattern as R2.
- **Q-ST4** (answered 2026-11-13, default): universe removal during stop moves onto a scene stage the same way, tracked in #158, not in #178.
