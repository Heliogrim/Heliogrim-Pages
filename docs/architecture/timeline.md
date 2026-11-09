# Timeline

Order of work and what depends on what, taken from the [rundown](exploration-rundown.md) (section 4, revised 2026-11-04). It is an ordering, not a schedule: no page commits to dates for delivery.

## Order and dependencies

```hg-diagram
flowchart LR
    FIB["2 Fiber context<br/>suspending await"]
    STO["3 Storage<br/>stack reuse, async query"]
    OBS["4 Observability<br/>span API, ring buffer"]
    SCR["5 Scripting<br/>JIT vs AOT decision"]
    FIB --> STO
    FIB --> OBS
    FIB --> SCR
```

Item 1, the serializer, has no dependency on the others and is not drawn.

| # | Work | Blocked by | Unblocks | Page |
|---|------|------------|----------|------|
| 1 | Serializer: per-type schema versions, skippable tags, round-trip rule, per-record checksums | nothing | Safe format evolution, Git-friendly packages | [Serializer evolution](serialization-evolution-exploration.md) |
| 2 | Shared fiber context and fiber-suspending await on an external completion | nothing | Async storage, C# awaiters, fiber-aware spans | [Fiber scheduler](fiber-scheduler-exploration.md) |
| 3 | Storage: reuse resolved stacks, then a first async query path | 2 (async part) | Windows batching backend, once measured | [Storage](storage-exploration.md) |
| 4 | Observability from the ground up | 2 | Profiling in Playtest and Profile builds | [Observability](observability-exploration.md) |
| 5 | Scripting runtime decision | 2 (nothing blocks the decision itself) | Visual scripting by native codegen | [Scripting](scripting-runtime-exploration.md), [native codegen](scripting-native-codegen-exploration.md) |

Closed: pointer sets (keep ankerl, 2026-11-04).

## Log

| Date | Event |
|------|-------|
| 2026-10-28 | Documentation repository created |
| 2026-11-02 | Actor system checked against the engine source |
| 2026-11-03 | Actor system exploration, sealed actor archetypes design, audio and DSP exploration, bounding volumes exploration added |
| 2026-11-04 | Pointer sets closed ([ADR placeholder](../adr/placeholder-pointer-sets.md)). Profiler dropped ([ADR placeholder](../adr/placeholder-trace-profiler.md)). Scripting by native codegen, fiber scheduler and the rundown added |
| 2026-11-05 | Documentation site redesigned, contribution paths and legal pages added; module map generated, systems section started, code documentation exploration opened |
| 2026-11-06 | [Gap analysis](gap-analysis.md) against commercial engines and enterprise documentation added; rundown headings aligned with its priority table |
| 2026-11-07 | [Battle plan](../plan/index.md) section added: vision, target architecture, required modules, engine gap analysis, systems catalog (S01 to S64), roadmap (M1 to M6), 27 topic pages and six research reports; matching `battle-plan` issues opened on the engine repository |
| 2026-11-08 | [Work packages](../plan/work/index.md) added: 27 pages cross-referencing the battle plan with the explorations and designs, with architecture and code design per topic, 232 chunks (explore, design, execute; 33 ready) and 125 [owner questions](../plan/work/questions.md) in six batches. [Accel shader toolchain](../systems/accel/index.md) system pages added (ASL language, IR and passes, compiler integration), checked against engine PR #156 head `d0c66b4a` |
| 2026-11-08 | Question batches 1 (foundations, 22), 2 (quality, process, vendor policy, 20) and 3 (rendering baseline, 30) answered by the owner; decisions on the work pages, seven [ADR placeholders](../adr/README.md) added |
| 2026-11-08 | W02.1 done: [Scheduler waitables design](scheduler-waitable-design.md) drafted and builder-checked (park handshake, event, join counter, fiber mutexes, cancellation token, migration list); implementation plan in the engine checkout; W02.2 and W02.3 become ready. Follow-up the same day: [Promise and future rework](promise-future-design.md) drafted on the owner's request, with its own plan |
| 2026-11-09 | W39.0 done: [Input backends exploration](input-exploration.md) (SDL3 versus native per platform). Proposal: SDL3 stays the base backend (upgrade 3.2.22 to 3.4.x), native capability side channels only where evidence shows a gain (Windows raw mouse in absolute mode, pen history, pointer touch; iPadOS coalesced touches and Pencil; Wayland tablet pads and gestures); Windows spike on injected input showed no SDL overhead for keyboard and relative mouse. Accepted by the owner the same day: exploration closed, ADR [placeholder](../adr/placeholder-input-backend-sdl3-base.md), Q39.1 resolved; W39.1 ready |

!!! note "Keeping this page current"
    Append a row to the log in the same pull request that changes a status or records an ADR.
