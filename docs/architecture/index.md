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

## Explorations

| Page | Status | Scope |
|------|--------|-------|
| [Actor system](actor-system.md) | <span class="hg-status exploration">exploration</span> | Archetype storage, dispatch, causality, serialization |
| [Audio and DSP](audio-dsp.md) | <span class="hg-status exploration">exploration</span> | Middleware, DAW ingestion, live and baked processing |
| [Bounding volumes](bounding-volumes.md) | <span class="hg-status exploration">exploration</span> | Spatial queries |
| [Fiber scheduler iteration](fiber-scheduler-exploration.md) | <span class="hg-status exploration">exploration</span> | Waiting, wake lists, task dependencies |
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
