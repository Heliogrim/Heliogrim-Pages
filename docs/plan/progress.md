# Progress Board

**Status**: <span class="hg-status summary">generated</span> from the [systems catalog](systems.md), the [roadmap](roadmap.md) and the chunk headings on the [work pages](work/index.md). Do not edit by hand; run `python -I tools/gen_progress.py` (CI runs it before every build). A chunk counts as its heading says, except that an `after` chunk whose listed chunks are all done counts as ready.

Legend per chunk, in page order (hover a dot for its id): <span class="hg-chunk done" title="done"></span> done · <span class="hg-chunk flight" title="in flight"></span> in progress or in review · <span class="hg-chunk ready" title="ready"></span> ready · <span class="hg-chunk blocked" title="blocked"></span> blocked (after or needs) · <span class="hg-chunk deferred" title="deferred"></span> deferred. **Landed** counts execute chunks whose code is on `master` and, separately, only on the `feat/wip` integration branch.

## Milestones

| Milestone | Systems | Chunks done | | In flight | Ready | Landed on `master` / `feat/wip` |
|---|---|---|---|---|---|---|
| [M1 Trustworthy core](#m1) | 13 | 20 / 62 | `▰▰▰▱▱▱▱▱▱▱` | 7 | 14 | 0 / 11 |
| [M2 Render and world core](#m2) | 14 | 6 / 44 | `▰▱▱▱▱▱▱▱▱▱` | 0 | 10 | 1 / 3 |
| [M3 A beautiful world](#m3) | 17 | 0 / 70 | `▱▱▱▱▱▱▱▱▱▱` | 1 | 6 | 0 / 0 |
| [M4 Living world and tools](#m4) | 16 | 1 / 68 | `▱▱▱▱▱▱▱▱▱▱` | 0 | 6 | 0 / 0 |
| [M5 Connected](#m5) | 2 | 1 / 8 | `▰▱▱▱▱▱▱▱▱▱` | 0 | 1 | 0 / 0 |
| [M6 Single shard](#m6) | 2 | 0 / 4 | `▱▱▱▱▱▱▱▱▱▱` | 0 | 0 | 0 / 0 |

## M1

Trustworthy core. Done when: see the [roadmap](roadmap.md#m1-trustworthy-core).

| System | Track | Done | | Explore | Design | Execute | Landed | Now |
|---|---|---|---|---|---|---|---|---|
| S01 Serialisation versions | A | 0 / 5 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W01.3 blocked"></span> | <span class="hg-chunk ready" title="W01.1 ready"></span><span class="hg-chunk blocked" title="W01.4 blocked"></span> | <span class="hg-chunk blocked" title="W01.2 blocked"></span><span class="hg-chunk blocked" title="W01.5 blocked"></span> | – | ready: [W01.1](work/serialization-and-reflection.md) |
| S02 Scheduler v2 | A | 9 / 19 | `▰▰▰▱▱▱` | <span class="hg-chunk ready" title="W02.0 ready"></span><span class="hg-chunk blocked" title="W02.7 blocked"></span><span class="hg-chunk ready" title="W02.9 ready"></span><span class="hg-chunk done" title="W02.13 done"></span> | <span class="hg-chunk done" title="W02.1 done"></span><span class="hg-chunk done" title="W02.4 done"></span><span class="hg-chunk deferred" title="W02.6 deferred"></span><span class="hg-chunk flight" title="W02.18 in flight"></span> | <span class="hg-chunk done" title="W02.2 done"></span><span class="hg-chunk done" title="W02.3 done"></span><span class="hg-chunk done" title="W02.5 done"></span><span class="hg-chunk done" title="W02.8 done"></span><span class="hg-chunk done" title="W02.10 done"></span><span class="hg-chunk flight" title="W02.11 in flight"></span><span class="hg-chunk blocked" title="W02.12 blocked"></span><span class="hg-chunk done" title="W02.14 done"></span><span class="hg-chunk flight" title="W02.17 in flight"></span><span class="hg-chunk ready" title="W02.15 ready"></span><span class="hg-chunk ready" title="W02.16 ready"></span> | 0 / 5 | in flight: [W02.11](work/concurrency-fibers.md), [W02.17](work/concurrency-fibers.md), [W02.18](work/concurrency-fibers.md) |
| S03 Async storage | A | 5 / 7 | `▰▰▰▰▱▱` | <span class="hg-chunk done" title="W03.5 done"></span> | <span class="hg-chunk done" title="W03.1 done"></span><span class="hg-chunk done" title="W03.3 done"></span><span class="hg-chunk ready" title="W03.7 ready"></span> | <span class="hg-chunk done" title="W03.2 done"></span><span class="hg-chunk done" title="W03.4 done"></span><span class="hg-chunk ready" title="W03.6 ready"></span> | 0 / 2 | ready: [W03.6](work/storage-streaming.md), [W03.7](work/storage-streaming.md) |
| S04 Observability | A | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W04.1 ready"></span><span class="hg-chunk blocked" title="W04.3 blocked"></span> | <span class="hg-chunk blocked" title="W04.2 blocked"></span> | – | ready: [W04.1](work/diagnostics-and-crash.md) |
| S05 Diagnostics | A | 3 / 4 | `▰▰▰▰▱▱` | – | <span class="hg-chunk done" title="W05.1 done"></span> | <span class="hg-chunk done" title="W05.2 done"></span><span class="hg-chunk done" title="W05.4 done"></span><span class="hg-chunk ready" title="W05.3 ready"></span> | 0 / 2 | ready: [W05.3](work/diagnostics-and-crash.md) |
| S06 Crash | A | 0 / 3 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W06.1 ready"></span> | <span class="hg-chunk blocked" title="W06.2 blocked"></span> | <span class="hg-chunk blocked" title="W06.3 blocked"></span> | – | ready: [W06.1](work/diagnostics-and-crash.md) |
| S08 Memory model | A | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W08.1 blocked"></span> | <span class="hg-chunk blocked" title="W08.2 blocked"></span> | – | blocked |
| S10 Build speed and module structure | A | 1 / 3 | `▰▰▱▱▱▱` | <span class="hg-chunk blocked" title="W10.2 blocked"></span> | – | <span class="hg-chunk flight" title="W10.1 in flight"></span><span class="hg-chunk done" title="W10.3 done"></span> | 0 / 1 | in flight: [W10.1](work/quality-and-process.md) |
| S26 GPU harness | B | 2 / 4 | `▰▰▰▱▱▱` | – | <span class="hg-chunk done" title="W26.1 done"></span> | <span class="hg-chunk done" title="W26.2 done"></span><span class="hg-chunk blocked" title="W26.3 blocked"></span><span class="hg-chunk ready" title="W26.4 ready"></span> | 0 / 1 | ready: [W26.4](work/quality-and-process.md) |
| S61 Test suite expansion | F | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W61.2 blocked"></span> | <span class="hg-chunk flight" title="W61.1 in flight"></span><span class="hg-chunk blocked" title="W61.3 blocked"></span> | – | in flight: [W61.1](work/quality-and-process.md) |
| S62 CI gates | F | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W62.1 ready"></span> | <span class="hg-chunk blocked" title="W62.2 blocked"></span><span class="hg-chunk blocked" title="W62.3 blocked"></span> | – | ready: [W62.1](work/quality-and-process.md) |
| S63 Standard | F | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W63.1 ready"></span> | <span class="hg-chunk blocked" title="W63.2 blocked"></span> | – | ready: [W63.1](work/quality-and-process.md) |
| S64 Documentation system | F | 0 / 4 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W64.1 ready"></span> | – | <span class="hg-chunk blocked" title="W64.2 blocked"></span><span class="hg-chunk flight" title="W64.3 in flight"></span><span class="hg-chunk flight" title="W64.4 in flight"></span> | – | in flight: [W64.3](work/quality-and-process.md), [W64.4](work/quality-and-process.md) |

## M2

Render and world core. Done when: see the [roadmap](roadmap.md#m2-render-and-world-core).

| System | Track | Done | | Explore | Design | Execute | Landed | Now |
|---|---|---|---|---|---|---|---|---|
| S07 Large world | A | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W07.1 ready"></span> | <span class="hg-chunk blocked" title="W07.2 blocked"></span> | – | ready: [W07.1](work/render-graph-gpu-driven.md) |
| S09 Reflection v2 | A | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W09.1 ready"></span> | <span class="hg-chunk blocked" title="W09.2 blocked"></span> | – | ready: [W09.1](work/serialization-and-reflection.md) |
| S11 ASL SPIR-V | B | 5 / 8 | `▰▰▰▰▱▱` | <span class="hg-chunk ready" title="W11.7 ready"></span> | <span class="hg-chunk done" title="W11.2 done"></span><span class="hg-chunk ready" title="W11.5 ready"></span><span class="hg-chunk ready" title="W11.6 ready"></span> | <span class="hg-chunk done" title="W11.0 done"></span><span class="hg-chunk done" title="W11.1 done"></span><span class="hg-chunk done" title="W11.3 done"></span><span class="hg-chunk done" title="W11.4 done"></span> | 1 / 3 | ready: [W11.5](work/accel-lang.md), [W11.6](work/accel-lang.md), [W11.7](work/accel-lang.md) |
| S12 Pipeline kinds | B | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W12.1 blocked"></span> | <span class="hg-chunk blocked" title="W12.2 blocked"></span><span class="hg-chunk blocked" title="W12.3 blocked"></span> | – | blocked |
| S13 Variant cache | B | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W13.1 ready"></span> | <span class="hg-chunk blocked" title="W13.2 blocked"></span> | – | ready: [W13.1](work/accel-lang.md) |
| S14 Render graph v2 | B | 0 / 3 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W14.0 ready"></span> | <span class="hg-chunk blocked" title="W14.1 blocked"></span> | <span class="hg-chunk blocked" title="W14.2 blocked"></span> | – | ready: [W14.0](work/render-graph-gpu-driven.md) |
| S15 GPU-driven | B | 0 / 4 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W15.0 ready"></span> | <span class="hg-chunk blocked" title="W15.1 blocked"></span> | <span class="hg-chunk blocked" title="W15.2 blocked"></span><span class="hg-chunk blocked" title="W15.3 blocked"></span> | – | ready: [W15.0](work/render-graph-gpu-driven.md) |
| S16 Materials v2 | B | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W16.1 blocked"></span> | <span class="hg-chunk blocked" title="W16.2 blocked"></span> | – | blocked |
| S17 Virtual textures | B | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W17.1 blocked"></span> | <span class="hg-chunk blocked" title="W17.2 blocked"></span> | – | blocked |
| S39 Input v2 | C | 1 / 5 | `▰▱▱▱▱▱` | <span class="hg-chunk done" title="W39.0 done"></span> | <span class="hg-chunk ready" title="W39.1 ready"></span> | <span class="hg-chunk blocked" title="W39.2 blocked"></span><span class="hg-chunk blocked" title="W39.3 blocked"></span><span class="hg-chunk blocked" title="W39.4 blocked"></span> | – | ready: [W39.1](work/input.md) |
| S40 World partition | C | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W40.1 blocked"></span> | <span class="hg-chunk blocked" title="W40.2 blocked"></span> | – | blocked |
| S41 Content-addressed packages and VCS-friendly asset formats | C | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W41.1 blocked"></span> | <span class="hg-chunk blocked" title="W41.2 blocked"></span> | – | blocked |
| S45 Actions v2 | D | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W45.1 blocked"></span> | <span class="hg-chunk blocked" title="W45.2 blocked"></span><span class="hg-chunk blocked" title="W45.3 blocked"></span> | – | blocked |
| S58 Headless | E | 0 / 4 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W58.1 ready"></span> | <span class="hg-chunk blocked" title="W58.2 blocked"></span><span class="hg-chunk blocked" title="W58.3 blocked"></span><span class="hg-chunk blocked" title="W58.4 blocked"></span> | – | ready: [W58.1](work/build-and-deploy.md) |

## M3

A beautiful world. Done when: see the [roadmap](roadmap.md#m3-a-beautiful-world).

| System | Track | Done | | Explore | Design | Execute | Landed | Now |
|---|---|---|---|---|---|---|---|---|
| S18 Micropoly | B | 0 / 7 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W18.1 blocked"></span><span class="hg-chunk blocked" title="W18.3 blocked"></span><span class="hg-chunk blocked" title="W18.5 blocked"></span> | <span class="hg-chunk blocked" title="W18.2 blocked"></span><span class="hg-chunk blocked" title="W18.4 blocked"></span><span class="hg-chunk blocked" title="W18.6 blocked"></span><span class="hg-chunk blocked" title="W18.7 blocked"></span> | – | blocked |
| S19 Shadows | B | 0 / 4 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W19.1 blocked"></span> | <span class="hg-chunk blocked" title="W19.2 blocked"></span><span class="hg-chunk blocked" title="W19.3 blocked"></span><span class="hg-chunk blocked" title="W19.4 blocked"></span> | – | blocked |
| S20 GI | B | 0 / 6 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W20.0 ready"></span><span class="hg-chunk blocked" title="W20.5 blocked"></span> | <span class="hg-chunk blocked" title="W20.1 blocked"></span> | <span class="hg-chunk blocked" title="W20.2 blocked"></span><span class="hg-chunk blocked" title="W20.3 blocked"></span><span class="hg-chunk blocked" title="W20.4 blocked"></span> | – | ready: [W20.0](work/shadows-gi.md) |
| S21 Volumetrics | B | 0 / 5 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W21.0 blocked"></span> | <span class="hg-chunk blocked" title="W21.1 blocked"></span> | <span class="hg-chunk blocked" title="W21.2 blocked"></span><span class="hg-chunk blocked" title="W21.3 blocked"></span><span class="hg-chunk blocked" title="W21.4 blocked"></span> | – | blocked |
| S22 Transparency | B | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W22.1 blocked"></span> | <span class="hg-chunk blocked" title="W22.2 blocked"></span> | – | blocked |
| S23 Post | B | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W23.1 blocked"></span> | <span class="hg-chunk blocked" title="W23.2 blocked"></span><span class="hg-chunk blocked" title="W23.3 blocked"></span> | – | blocked |
| S24 Particles | B | 0 / 4 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W24.1 blocked"></span> | <span class="hg-chunk blocked" title="W24.2 blocked"></span><span class="hg-chunk blocked" title="W24.3 blocked"></span><span class="hg-chunk blocked" title="W24.4 blocked"></span> | – | blocked |
| S25 Foliage | B | 0 / 4 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W25.4 blocked"></span> | <span class="hg-chunk blocked" title="W25.1 blocked"></span> | <span class="hg-chunk blocked" title="W25.2 blocked"></span><span class="hg-chunk blocked" title="W25.3 blocked"></span> | – | blocked |
| S27 Terrain v1 | C | 0 / 3 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W27.0 blocked"></span> | <span class="hg-chunk blocked" title="W27.1 blocked"></span> | <span class="hg-chunk blocked" title="W27.2 blocked"></span> | – | blocked |
| S30 Ocean | C | 0 / 4 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W30.0 blocked"></span> | <span class="hg-chunk blocked" title="W30.1 blocked"></span> | <span class="hg-chunk blocked" title="W30.2 blocked"></span><span class="hg-chunk blocked" title="W30.3 blocked"></span> | – | blocked |
| S32 Weather | C | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W32.1 blocked"></span> | <span class="hg-chunk blocked" title="W32.2 blocked"></span><span class="hg-chunk blocked" title="W32.3 blocked"></span> | – | blocked |
| S42 Canvas | D | 0 / 6 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W42.0 ready"></span> | <span class="hg-chunk blocked" title="W42.1 blocked"></span> | <span class="hg-chunk blocked" title="W42.2 blocked"></span><span class="hg-chunk blocked" title="W42.3 blocked"></span><span class="hg-chunk blocked" title="W42.4 blocked"></span><span class="hg-chunk blocked" title="W42.5 blocked"></span> | – | ready: [W42.0](work/vector-ui-uikit.md) |
| S43 Uikit | D | 0 / 5 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W43.0 ready"></span> | <span class="hg-chunk blocked" title="W43.1 blocked"></span> | <span class="hg-chunk flight" title="W43.2 in flight"></span><span class="hg-chunk blocked" title="W43.3 blocked"></span><span class="hg-chunk blocked" title="W43.4 blocked"></span> | – | in flight: [W43.2](work/vector-ui-uikit.md) |
| S44 Picking | D | 0 / 5 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W44.0 ready"></span><span class="hg-chunk ready" title="W44.1 ready"></span> | <span class="hg-chunk blocked" title="W44.2 blocked"></span> | <span class="hg-chunk blocked" title="W44.3 blocked"></span><span class="hg-chunk blocked" title="W44.4 blocked"></span> | – | ready: [W44.0](work/editor-workflows.md), [W44.1](work/editor-workflows.md) |
| S46 Search | D | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W46.1 blocked"></span> | <span class="hg-chunk blocked" title="W46.2 blocked"></span> | – | blocked |
| S49 DCC live link | D | 0 / 4 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W49.1 blocked"></span> | <span class="hg-chunk blocked" title="W49.2 blocked"></span><span class="hg-chunk blocked" title="W49.3 blocked"></span><span class="hg-chunk blocked" title="W49.4 blocked"></span> | – | blocked |
| S59 Replay | E | 0 / 3 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W59.0 ready"></span> | <span class="hg-chunk blocked" title="W59.1 blocked"></span> | <span class="hg-chunk blocked" title="W59.2 blocked"></span> | – | ready: [W59.0](work/networking-mmo.md) |

## M4

Living world and tools. Done when: see the [roadmap](roadmap.md#m4-living-world-and-tools).

| System | Track | Done | | Explore | Design | Execute | Landed | Now |
|---|---|---|---|---|---|---|---|---|
| S28 Terrain v2 | C | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W28.1 blocked"></span> | <span class="hg-chunk blocked" title="W28.2 blocked"></span><span class="hg-chunk blocked" title="W28.3 blocked"></span> | – | blocked |
| S29 Multi-level bounded effects | C | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W29.1 blocked"></span> | <span class="hg-chunk blocked" title="W29.2 blocked"></span> | – | blocked |
| S31 Fluids | C | 0 / 6 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W31.0 ready"></span><span class="hg-chunk blocked" title="W31.4 blocked"></span> | <span class="hg-chunk blocked" title="W31.1 blocked"></span> | <span class="hg-chunk blocked" title="W31.2 blocked"></span><span class="hg-chunk blocked" title="W31.3 blocked"></span><span class="hg-chunk blocked" title="W31.5 blocked"></span> | – | ready: [W31.0](work/ocean-fluids.md) |
| S33 Procedural | C | 0 / 5 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W33.1 blocked"></span> | <span class="hg-chunk blocked" title="W33.2 blocked"></span><span class="hg-chunk blocked" title="W33.3 blocked"></span><span class="hg-chunk blocked" title="W33.4 blocked"></span><span class="hg-chunk blocked" title="W33.5 blocked"></span> | – | blocked |
| S34 Physics v2 | C | 0 / 5 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W34.0 ready"></span> | <span class="hg-chunk blocked" title="W34.1 blocked"></span> | <span class="hg-chunk blocked" title="W34.2 blocked"></span><span class="hg-chunk blocked" title="W34.3 blocked"></span><span class="hg-chunk blocked" title="W34.4 blocked"></span> | – | ready: [W34.0](work/physics-cloth.md) |
| S35 Cloth and soft body | C | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W35.1 blocked"></span> | <span class="hg-chunk blocked" title="W35.2 blocked"></span><span class="hg-chunk blocked" title="W35.3 blocked"></span> | – | blocked |
| S36 Animation | C | 0 / 6 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W36.0 ready"></span> | <span class="hg-chunk blocked" title="W36.1 blocked"></span> | <span class="hg-chunk blocked" title="W36.2 blocked"></span><span class="hg-chunk blocked" title="W36.3 blocked"></span><span class="hg-chunk blocked" title="W36.4 blocked"></span><span class="hg-chunk blocked" title="W36.5 blocked"></span> | – | ready: [W36.0](work/animation.md) |
| S37 Navigation | C | 1 / 5 | `▰▱▱▱▱▱` | <span class="hg-chunk done" title="W37.0 done"></span> | <span class="hg-chunk blocked" title="W37.1 blocked"></span> | <span class="hg-chunk blocked" title="W37.2 blocked"></span><span class="hg-chunk blocked" title="W37.3 blocked"></span><span class="hg-chunk blocked" title="W37.4 blocked"></span> | – | blocked |
| S38 Audio | C | 0 / 8 | `▱▱▱▱▱▱` | – | <span class="hg-chunk ready" title="W38.0 ready"></span><span class="hg-chunk blocked" title="W38.5 blocked"></span> | <span class="hg-chunk blocked" title="W38.1 blocked"></span><span class="hg-chunk blocked" title="W38.2 blocked"></span><span class="hg-chunk blocked" title="W38.3 blocked"></span><span class="hg-chunk blocked" title="W38.4 blocked"></span><span class="hg-chunk blocked" title="W38.6 blocked"></span><span class="hg-chunk blocked" title="W38.7 blocked"></span> | – | ready: [W38.0](work/audio.md) |
| S47 Visual scripting | D | 0 / 5 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W47.0 ready"></span> | <span class="hg-chunk blocked" title="W47.1 blocked"></span> | <span class="hg-chunk blocked" title="W47.2 blocked"></span><span class="hg-chunk blocked" title="W47.3 blocked"></span><span class="hg-chunk blocked" title="W47.4 blocked"></span> | – | ready: [W47.0](work/visual-scripting-hmr.md) |
| S48 HMR | D | 0 / 4 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W48.0 blocked"></span> | <span class="hg-chunk blocked" title="W48.1 blocked"></span> | <span class="hg-chunk blocked" title="W48.2 blocked"></span><span class="hg-chunk blocked" title="W48.3 blocked"></span> | – | blocked |
| S50 Plugins | D | 0 / 3 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W50.1 blocked"></span> | <span class="hg-chunk blocked" title="W50.2 blocked"></span><span class="hg-chunk blocked" title="W50.3 blocked"></span> | – | blocked |
| S51 VCS integration | D | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W51.1 blocked"></span> | <span class="hg-chunk blocked" title="W51.2 blocked"></span> | – | blocked |
| S52 Localisation | D | 0 / 4 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W52.0 ready"></span> | <span class="hg-chunk blocked" title="W52.1 blocked"></span> | <span class="hg-chunk blocked" title="W52.2 blocked"></span><span class="hg-chunk blocked" title="W52.3 blocked"></span> | – | ready: [W52.0](work/localization.md) |
| S53 Build system | D | 0 / 5 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W53.1 blocked"></span> | <span class="hg-chunk blocked" title="W53.2 blocked"></span><span class="hg-chunk blocked" title="W53.3 blocked"></span><span class="hg-chunk blocked" title="W53.4 blocked"></span><span class="hg-chunk blocked" title="W53.5 blocked"></span> | – | blocked |
| S54 Test automation | D | 0 / 2 | `▱▱▱▱▱▱` | – | <span class="hg-chunk blocked" title="W54.1 blocked"></span> | <span class="hg-chunk blocked" title="W54.2 blocked"></span> | – | blocked |

## M5

Connected. Done when: see the [roadmap](roadmap.md#m5-connected).

| System | Track | Done | | Explore | Design | Execute | Landed | Now |
|---|---|---|---|---|---|---|---|---|
| S55 Transport | E | 0 / 4 | `▱▱▱▱▱▱` | <span class="hg-chunk ready" title="W55.0 ready"></span> | <span class="hg-chunk blocked" title="W55.1 blocked"></span> | <span class="hg-chunk blocked" title="W55.2 blocked"></span><span class="hg-chunk blocked" title="W55.3 blocked"></span> | – | ready: [W55.0](work/networking-mmo.md) |
| S56 Replication | E | 1 / 4 | `▰▰▱▱▱▱` | <span class="hg-chunk done" title="W56.0 done"></span> | <span class="hg-chunk blocked" title="W56.1 blocked"></span> | <span class="hg-chunk blocked" title="W56.2 blocked"></span><span class="hg-chunk blocked" title="W56.3 blocked"></span> | – | blocked |

## M6

Single shard. Done when: see the [roadmap](roadmap.md#m6-single-shard).

| System | Track | Done | | Explore | Design | Execute | Landed | Now |
|---|---|---|---|---|---|---|---|---|
| S57 Server mesh | E | 0 / 3 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W57.0 blocked"></span> | <span class="hg-chunk blocked" title="W57.1 blocked"></span> | <span class="hg-chunk blocked" title="W57.2 blocked"></span> | – | blocked |
| S60 JIT | E | 0 / 1 | `▱▱▱▱▱▱` | <span class="hg-chunk blocked" title="W60.1 blocked"></span> | – | – | – | blocked |

Tracks: **A** foundation · **B** shading and rendering · **C** world and simulation · **D** editor and tooling · **E** runtime at scale · **F** quality and process.
