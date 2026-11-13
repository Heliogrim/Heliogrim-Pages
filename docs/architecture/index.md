# Architecture

Overview documents for the engine and editor systems. Exploration notes are not decisions; accepted parts move to [`adr/`](../adr/README.md). Start with the [rundown](exploration-rundown.md) for priorities, or the [timeline](timeline.md) for order of work.

<span class="hg-status exploration">exploration</span> options and evidence, nothing decided · <span class="hg-status design">design</span> a chosen direction · <span class="hg-status closed">closed</span> kept for the record · <span class="hg-status summary">summary</span> cross-cutting overview

## Designs

| Page | Status | Scope |
|------|--------|-------|
| [Sealed actor archetypes](actor-archetypes-design.md) | <span class="hg-status design">design</span> approved 2026-11-03 | Actor storage and dispatch |
| [Audio runtime](audio-runtime-design.md) | <span class="hg-status design">design</span> draft | Sound runtime; follows the audio exploration |
| [Scheduler waitables](scheduler-waitable-design.md) | <span class="hg-status design">design</span> draft 2026-11-08 | Parking, events, join counter, fiber mutexes; follows the fiber scheduler exploration |
| [Promise and future](promise-future-design.md) | <span class="hg-status design">design</span> draft 2026-11-08 | Move-only promise and future over the scheduler event, task-scheduled chaining, Send constraint |
| [Affine threads](affine-thread-design.md) | <span class="hg-status design">design</span> draft 2026-11-09 | One owned-thread seam for the platform pump and IO: inbox, OS waker, `post` returning a future, modal-safe drain |
| [Task graph](task-graph-design.md) | <span class="hg-status design">design</span> draft 2026-11-11, reviewed 2026-11-12 | Declared stages `{ name, reads, writes, lane, after, before }`, a checked builder (cycles, conflicts), a counting runner with a TLA+ model, lanes stamped on the task; every frame stage with its sets |
| [Storage](storage-design.md) | <span class="hg-status design">design</span> draft 2026-11-09 | Resolved-stack reuse (per-stage cache, invalidation after commit) and the async path: IOCP `IoSystem` with DirectStorage-shaped batches, fibers park per read, windowed archive residency |
| [Accel Lang](accel-lang-design.md) | <span class="hg-status design">design</span> record 2026-11-13 | Intent, layer and binding rules, IR part list, region-borrow rules and reserved names of the shader toolchain, moved from the engine-side specs |

## Explorations

| Page | Status | Scope |
|------|--------|-------|
| [Actor system](actor-system.md) | <span class="hg-status exploration">exploration</span> | Archetype storage, dispatch, causality, serialization |
| [Agent and player sync](agent-sync-exploration.md) | <span class="hg-status exploration">exploration</span> 2026-11-09 | Tiered prediction, scheduled actions, cost per player (W56.0 desk study) |
| [Audio and DSP](audio-dsp.md) | <span class="hg-status exploration">exploration</span> | Middleware, DAW ingestion, live and baked processing |
| [Bounding volumes](bounding-volumes.md) | <span class="hg-status exploration">exploration</span> | Spatial queries |
| [Engine stop teardown](engine-stop-teardown-exploration.md) | <span class="hg-status exploration">exploration</span> 2026-11-13 | Stop vs. in-flight frames: ownership retire, stage-owned teardown (#178) |
| [Fiber scheduler iteration](fiber-scheduler-exploration.md) | <span class="hg-status exploration">exploration</span> | Waiting, wake lists, task dependencies |
| [Input backends](input-exploration.md) | <span class="hg-status closed">closed</span> 2026-11-09 | Result: SDL3 base, native capability side channels, ADR [placeholder](../adr/placeholder-input-backend-sdl3-base.md) |
| [Navmesh library fit](navigation-exploration.md) | <span class="hg-status closed">closed</span> 2026-11-09 | Result: vendor recastnavigation, ADR [placeholder](../adr/placeholder-navmesh-recastnavigation.md); detail-mesh patch halves tile builds with byte-identical output |
| [Observability and profiling](observability-exploration.md) | <span class="hg-status exploration">exploration</span> | Fiber-aware spans, ring buffers, tiered builds |
| [Code documentation](code-documentation.md) | <span class="hg-status exploration">exploration</span> | Symbol-level reference without annotations in the engine |
| [Pointer sets](pointer-sets-exploration.md) | <span class="hg-status closed">closed</span> 2026-11-04 | Result: keep ankerl, ADR [placeholder](../adr/placeholder-pointer-sets.md) |
| [Scripting by native codegen](scripting-native-codegen-exploration.md) | <span class="hg-status exploration">exploration</span> | Graph IR to C++ |
| [Scripting runtime](scripting-runtime-exploration.md) | <span class="hg-status exploration">exploration</span> | Embedded C# and fiber awaiters |
| [Serializer evolution and VCS](serialization-evolution-exploration.md) | <span class="hg-status exploration">exploration</span> | Schema versioning, Git-friendly text form |
| [Storage engine](storage-exploration.md) | <span class="hg-status exploration">exploration</span> | Async I/O, batching, Windows backend |

## Overviews

| Page | Status | Scope |
|------|--------|-------|
| [Module map](modules.md) | <span class="hg-status summary">generated</span> | Modules, groups and links, from the engine's CMake targets |
| [Exploration rundown](exploration-rundown.md) | <span class="hg-status summary">summary</span> | Priorities and open decisions across the explorations |
| [Timeline](timeline.md) | <span class="hg-status summary">summary</span> | Order of work, dependencies, dated log |
| [Gap analysis](gap-analysis.md) | <span class="hg-status summary">summary</span> | What the docs and the engine lack next to commercial engines |
| [Battle plan](../plan/index.md) | <span class="hg-status summary">plan</span> | Vision, target architecture, systems catalog, roadmap and per-topic research and guidance |

Raw research behind some pages lives under *Sources* in the navigation.
