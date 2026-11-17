# Systems

How each engine system works, written for someone who has to change it. Explorations argue what *could* be built; system pages describe what *is* built, and say which engine commit they were checked against.

| System | Status | Modules |
|--------|--------|---------|
| [Accel shader toolchain](accel/index.md): [ASL](accel/asl.md), [IR and passes](accel/ir.md), [compiler](accel/compiler.md) | <span class="hg-status design">experimental</span> | `Engine.Accel.Lang`, `Engine.Accel.Compile` |
| [Scheduler](scheduler/index.md): [fibers and workers](scheduler/fibers-and-workers.md), [waitables](scheduler/waitables.md), [futures](scheduler/futures.md), [affine threads](scheduler/affine-threads.md), [task graph](scheduler/task-graph.md) | <span class="hg-status accepted">implemented</span> | `Engine.Scheduler`, `Engine.Async`, `Heliogrim/Async` |
| [Storage](storage.md) | <span class="hg-status accepted">implemented</span> (sync and async IOCP, [#180](https://github.com/Heliogrim/Heliogrim-Engine/pull/180) merged) | `Engine.Storage*` |
| [Diagnostics](diagnostics.md) | <span class="hg-status design">experimental</span> | `Engine.Diagnostics`, `Engine.Logging` |
| [Actors](actors.md) | <span class="hg-status design">experimental</span> | `Heliogrim` (public actor API), `Engine.ACS`, `Engine.Level`, `Engine.Scene.Game` |
| [Render graph](render-graph.md) | <span class="hg-status design">experimental</span> | `Engine.Graphics.RenderGraph`, `Engine.Graphics.RenderGraph.Compile` |
| [GPU test harness](gpu-test-harness.md) | <span class="hg-status design">experimental</span> | `Engine.Graphics.Gpu.Test` |
| [Micropoly renderer](micropoly-renderer.md) | <span class="hg-status planned">planned</span> | none in the engine yet |
| [Animation pipeline](animation-pipeline.md) | <span class="hg-status planned">planned</span> | none in the engine yet |

Statuses: <span class="hg-status accepted">implemented</span> written and checked against the code · <span class="hg-status design">experimental</span> exists but changes often · <span class="hg-status planned">planned</span> page or system not there yet.

New pages start from the [page template](template.md) and are added to this table, to `nav` in `mkdocs.yml`, and to the [timeline](../architecture/timeline.md) log. Overview of all modules: [module map](../architecture/modules.md).
