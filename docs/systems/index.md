# Systems

How each engine system works, written for someone who has to change it. Explorations argue what *could* be built; system pages describe what *is* built, and say which engine commit they were checked against.

| System | Status | Modules |
|--------|--------|---------|
| [Accel shader toolchain](accel/index.md): [ASL](accel/asl.md), [IR and passes](accel/ir.md), [compiler](accel/compiler.md) | <span class="hg-status design">experimental</span> | `Engine.Accel.Lang`, `Engine.Accel.Compile` |
| [Render graph](render-graph.md) | <span class="hg-status planned">planned page</span> | `Engine.Graphics.RenderGraph`, `Engine.Graphics.RenderGraph.Compile` |
| [Micropoly renderer](micropoly-renderer.md) | <span class="hg-status planned">planned</span> | none in the engine yet |
| [Animation pipeline](animation-pipeline.md) | <span class="hg-status planned">planned</span> | none in the engine yet |

Statuses: <span class="hg-status accepted">implemented</span> written and checked against the code · <span class="hg-status design">experimental</span> exists but changes often · <span class="hg-status planned">planned</span> page or system not there yet.

New pages start from the [page template](template.md) and are added to this table, to `nav` in `mkdocs.yml`, and to the [timeline](../architecture/timeline.md) log. Overview of all modules: [module map](../architecture/modules.md).
