# Work Packages

**Status**: <span class="hg-status summary">plan</span>. The battle plan broken into chunks a single agent session can pick up. Written 2026-11-08 from the [systems catalog](../systems.md), the 27 [topic pages](../topics/index.md), the existing [explorations and designs](../../architecture/index.md) and the engine-side notes (Accel IR milestones, audio brainstorm, viewport and canvas requirements, test notes). Nothing here is a decision.

## What a chunk is

Every chunk has an ID `W<system>.<n>` (for example `W02.1` is the second chunk of S02), a kind, a status, inputs, an output and a "done when". One chunk is one session.

| Kind | What the session does | Skill to run | Output lands in |
|---|---|---|---|
| **explore** | Brainstorm, spike, benchmark or read the code; answer a question with evidence | `brainstorming`, research in subagents | `architecture/<topic>-exploration.md` (new section or new page), numbers with hardware stated |
| **design** | Choose a direction, write the code design, write the implementation plan | `brainstorming` (builder check), then `writing-plans` | `architecture/<topic>-design.md` on this site; the plan stays untracked in the engine checkout under `docs/superpowers/plans/` |
| **execute** | Run an existing plan task by task with tests | `subagent-driven-development` (or `executing-plans`) | Atomic commits on a `<type>/<slug>` branch, a PR linking the issue, a system page from the [template](../../systems/template.md) |

Statuses: **ready** nothing blocks it · **after W..** waits for those chunks · **needs Q..** waits for an owner answer (see [questions](questions.md)). A design chunk may start before its "after" chunks finish when only interface shapes are needed; the page says so.

## Picking up a chunk

1. Open the topic's work page below, read its cross-reference, architecture and code design sections, then the chunk.
2. Read the issue(s) in the page header; the issue is the spec, the work page is the breakdown.
3. Check the engine for drift: every "current state" claim on this site names its check date. Re-check anything older than a few weeks before building on it.
4. Apply the page's "Decisions" table where one exists; it overrides the code-design rows and the suggested defaults. If a listed question is still unanswered, use the suggested default and state the assumption in the output.
5. Finish by updating the chunk's status on its work page, adding a row to the [timeline](../../architecture/timeline.md), and writing the memory checkpoint.

Session prompt that works for any kind: *"Pick up `W<id>` from Heliogrim-Pages `docs/plan/work/<topic>.md`. Read the page's cross-reference, architecture, code design and Decisions sections, then the chunk and its issue. Follow the kind's skill. Do not mutate the engine unless the kind is execute; designs go on the Pages site, plans stay untracked in the engine checkout. Finish by updating the chunk status, the timeline and the memory checkpoint. Report the output path and the status change."*

## Ready now

31 chunks have no open dependency. Suggested order inside M1, by how much they unblock:

| Order | Chunk | Kind | Why first |
|---|---|---|---|
| 1 | [W02.0](concurrency-fibers.md), [W02.11](concurrency-fibers.md), [W02.14](concurrency-fibers.md) | explore, design+execute, design+plan+execute | The scheduler shapes storage, audio, observability, physics and replay; W02.5 closed at its plan half (PR #175), its rest split 2026-11-13 into W02.11 (stage access review, relaxation), W02.12 (scene key split, after W02.11), W02.13 (lanes, done 2026-11-13: lane policy exploration, implemented by W02.14) |
| 2 | [W01.1](serialization-and-reflection.md) | design | Serialisation versioning gates partition, actions, packages, hot reload |
| 3 | [W05.2](diagnostics-and-crash.md) | execute | Every later system returns `Diagnostic`; W05.1 done, [design](../../architecture/diagnostics-design.md) accepted 2026-11-14; W05.2 done (PR [#188](https://github.com/Heliogrim/Heliogrim-Engine/pull/188) merged 2026-11-15); W05.4 (ASL message wording) done (PR [#190](https://github.com/Heliogrim/Heliogrim-Engine/pull/190) merged 2026-11-16); W05.3 next |
| 4 | [W03.5](storage-streaming.md), [W03.4](storage-streaming.md) | explore, execute | W03.5 decides the codec; W03.4 done, PR #180 merged into `feat/wip` 2026-11-16 (editor run open; registry removal excluded); W03.5 also owns the in-flight cap (Q03.5) |
| 5 | [W63.1](quality-and-process.md), [W62.1](quality-and-process.md), [W61.1](quality-and-process.md), [W10.1](quality-and-process.md), [W64.1](quality-and-process.md) | mixed | Gates that make every other chunk safer; W61.1 has a bug ledger (12 of 25 fixed, none filed) and the tracker's open bug issues |
| 6 | [W11.3](accel-lang.md) | execute | Direct SPIR-V backend; code done 2026-11-16, engine PR [#203](https://github.com/Heliogrim/Heliogrim-Engine/pull/203) into `feat/wip` |
| 7 | [W09.1](serialization-and-reflection.md), [W07.1](render-graph-gpu-driven.md), [W14.0](render-graph-gpu-driven.md), [W15.0](render-graph-gpu-driven.md), [W58.1](build-and-deploy.md), [W39.1](input.md) | design, explore | M2 designs with no M1 dependency |
| 8 | [W38.0](audio.md) | design | The audio design is one builder check from approval |
| 9 | [W06.1](diagnostics-and-crash.md), [W36.0](animation.md), [W37.0](navigation.md) (done 2026-11-09), [W52.0](localization.md), [W44.0](editor-workflows.md) | explore | Vendor fit and benchmark spikes; each is a day or two |
| 10 | [W42.0](vector-ui-uikit.md), [W43.0](vector-ui-uikit.md), [W44.1](editor-workflows.md), [W47.0](visual-scripting-hmr.md), [W59.0](networking-mmo.md) | explore | Close paused brainstorms and record decisions |
| 11 | [W20.0](shadows-gi.md), [W31.0](ocean-fluids.md) | explore | Briefs for the two "To discuss" issues (#100, #111) |

## Pages by topic

| Work page | Systems | Chunks | Ready | Open questions |
|---|---|---|---|---|
| [Concurrency and fibers](concurrency-fibers.md) | S02 | W02.0 to W02.14 | W02.0, W02.9, W02.14 ready, W02.11 in progress (engine loop exploration), W02.10 done (PR #185 merged into `feat/wip`), W02.13 done (lane policy exploration), W02.12 after W02.11, W02.6 deferred (2026-11-13), W02.5 done (plan half merged via PR #175, rest split 2026-11-13; W02.1 to W02.4 done), W02.8 done (PR #181 merged into `feat/wip`) | Q02.1 to Q02.10 |
| [Diagnostics, observability, crash](diagnostics-and-crash.md) | S04, S05, S06 | W04.1 to W04.3, W05.1 to W05.4, W06.1 to W06.3 | W06.1, W05.3 (W05.1 done and accepted, W05.2 done 2026-11-14, W05.4 done 2026-11-16) | Q04.1 to Q04.4, Q05.1, Q05.2, Q06.1, Q06.2 |
| [Storage, memory, virtual textures, partition](storage-streaming.md) | S03, S08, S17, S40 | W03.1 to W03.5, W08.1, W08.2, W17.1, W17.2, W40.1, W40.2 | W03.5 (W03.1 to W03.4 done; W03.4 merged via PR #180 into `feat/wip`) | Q03.1 to Q03.4, Q08.1, Q17.1, Q40.1 to Q40.3 |
| [Serialisation, reflection, packages](serialization-and-reflection.md) | S01, S09, S41 | W01.1 to W01.5, W09.1, W09.2, W41.1, W41.2 | W01.1, W09.1 | Q01.1 to Q01.3, Q09.1, Q09.2, Q41.1, Q41.2 |
| [Quality and process](quality-and-process.md) | S10, S26, S61 to S64 | W10.1, W10.2, W26.1 to W26.4, W61.1 to W61.3, W62.1 to W62.3, W63.1, W63.2, W64.1 to W64.3 | W63.1, W62.1, W26.1, W61.1, W64.1 (W10.1 code done, W10.3 done) | Q10.1, Q26.1, Q62.1 to Q62.3, Q63.1, Q63.2, Q64.1 |
| [Accel Lang](accel-lang.md) | S11, S12, S13, S60 | W11.0 to W11.7, W12.1 to W12.3, W13.1, W13.2, W60.1 | W11.3 code done, PR #203 open (W11.0 to W11.2 done); W11.4 next | Q11.1 to Q11.3, Q12.1, Q12.2, Q13.1, Q60.1 |
| [Render graph, GPU-driven, large world](render-graph-gpu-driven.md) | S07, S14, S15 | W07.1, W07.2, W14.0 to W14.2, W15.0 to W15.3 | W14.0, W07.1, W15.0 | Q07.1, Q07.2, Q14.1, Q14.2, Q15.1 to Q15.3 |
| [Materials, transparency, post](materials-post.md) | S16, S22, S23 | W16.1, W16.2, W22.1, W22.2, W23.1 to W23.3 | none | Q16.1, Q16.2, Q22.1, Q23.1, Q23.2 |
| [Micropolygon](micropolygon.md) | S18 | W18.1 to W18.7 | none | Q18.1 to Q18.3 |
| [Shadows and GI](shadows-gi.md) | S19, S20 | W19.1 to W19.4, W20.0 to W20.5 | W20.0 | Q19.1, Q20.1 to Q20.3 |
| [Volumetrics and weather](volumetrics-weather.md) | S21, S32 | W21.0 to W21.4, W32.1 to W32.3 | none | Q21.1, Q21.2, Q32.1, Q32.2 |
| [Particles and foliage](particles-foliage.md) | S24, S25 | W24.1 to W24.4, W25.1 to W25.4 | none | Q24.1, Q24.2, Q25.1 |
| [Terrain and bounded effects](terrain.md) | S27, S28, S29 | W27.0 to W27.2, W28.1 to W28.3, W29.1, W29.2 | none | Q27.1, Q27.2, Q28.1, Q28.2, Q29.1 |
| [Ocean and fluids](ocean-fluids.md) | S30, S31 | W30.0 to W30.3, W31.0 to W31.3 | W31.0 | Q30.1, Q30.2, Q31.1, Q31.2 |
| [Procedural generation](procedural-generation.md) | S33 | W33.1 to W33.5 | none | Q33.1, Q33.2 |
| [Physics and cloth](physics-cloth.md) | S34, S35 | W34.0 to W34.4, W35.1 to W35.3 | none | Q34.1 to Q34.3, Q35.1 |
| [Animation](animation.md) | S36 | W36.0 to W36.5 | W36.0 | Q36.1 to Q36.3 |
| [Navigation](navigation.md) | S37 | W37.0 to W37.4 | none (W37.0 done) | Q37.1, Q37.2 |
| [Audio](audio.md) | S38 | W38.0 to W38.7 | W38.0 | Q38.1 to Q38.4 |
| [Input](input.md) | S39 | W39.0 to W39.4 | W39.1 (W39.0 done) | Q39.1, Q39.2 (decided) |
| [Vector canvas and uikit](vector-ui-uikit.md) | S42, S43 | W42.0 to W42.5, W43.0 to W43.4 | W42.0, W43.0 | Q42.1, Q42.2, Q43.1 |
| [Editor workflows](editor-workflows.md) | S44, S45, S46, S54 | W44.0 to W44.4, W45.1 to W45.3, W46.1, W46.2, W54.1, W54.2 | W44.0, W44.1 | Q44.1 to Q44.3, Q45.1, Q46.1, Q54.1 |
| [Visual scripting and hot reload](visual-scripting-hmr.md) | S47, S48 | W47.0 to W47.4, W48.0 to W48.3 | W47.0 | Q47.1, Q47.2, Q48.1, Q48.2 |
| [DCC, plugins, VCS](dcc-plugins-vcs.md) | S49, S50, S51 | W49.1 to W49.4, W50.1 to W50.3, W51.1, W51.2 | none | Q49.1, Q50.1, Q51.1 |
| [Localisation](localization.md) | S52 | W52.0 to W52.3 | W52.0 | Q52.1, Q52.2 |
| [Build and headless roles](build-and-deploy.md) | S53, S58 | W53.1 to W53.5, W58.1 to W58.4 | W58.1 | Q53.1, Q53.2, Q58.1, Q58.2 |
| [Networking, replication, mesh, replay](networking-mmo.md) | S55 to S57, S59 | W55.0 to W55.3, W56.1 to W56.3, W57.0 to W57.2, W59.0 to W59.2 | W59.0 (W56.0 desk study done) | Q55.1, Q55.2, Q56.1 to Q56.4, Q57.1, Q57.2, Q59.1 |

Totals: 241 chunks (about 52 explore, 72 design, 115 execute; W02.9 and W02.10 added 2026-11-13, W02.11 to W02.13 split from W02.5 the same day, W02.14 from W02.13, W26.4 split from W26.1 on 2026-11-14, W05.4 added the same day), 34 ready (W02.6 deferred, W02.10, W02.13, W05.1 and W05.2 done, W02.14 added), 132 owner questions (three added by W56.0, Q02.7 and Q02.8 by W02.4, Q02.9 and Q02.10 by W02.5). The [questions page](questions.md) groups the questions into batches so one conversation can clear many chunks.

## Cross-cutting findings from the cross-reference

Cross-cutting owner decision (2026-11-09): bundles get spelled-out names, `Engine.Physics` and `Engine.Graphics`, with `Engine.Particles` and `Engine.Foliage` for new ones (W10.3 on the [quality page](quality-and-process.md)). The rename landed in PR [#167](https://github.com/Heliogrim/Heliogrim-Engine/pull/167) (merged into `feat/wip` 2026-11-11); pages use the spelled-out names.


1. **Three paused brainstorms** hold requirements that the plan already uses but nobody closed: canvas and MSDF (W42.0), picking and gizmos (W44.1), audio design approval (W38.0). Closing them is cheap and removes the oldest open threads.
2. **Engine-side specs that are not on this site**: the Accel IR milestone 2 state and the region-borrow spec live in an untracked worktree. W11.0 records them here so the plan survives the worktree.
3. **Two explorations recommend experiments that were never run**: the scheduler's five experiments (W02.0) and the bounds benchmark (W44.0). Both decide designs the plan lists as "ready".
4. **The explorations and the plan agree on direction** for scheduler, storage, serialisation and observability; the only tension found is bundle layering between `Engine.Diagnostics`, `Engine.Logging` and `Engine.Observability`, resolved on the diagnostics page.
5. **Graph compiler demand**: particles, animation, procedural generation and materials all want S47's compiler. The pages decouple them with system-specific stage or node programs first, so no system waits on S47.
6. **Vendor decisions cluster**: crash handler, meshoptimizer, ACL, Recast and Detour, SQLite FTS5, HarfBuzz and FreeType and ICU, ufbx, a QUIC library, Live++. The questions page batches them so the vendor policy is applied once.
7. **"To discuss" issues** (#100 GI, #111 fluids, #137 server mesh, #140 JIT) each get an explore chunk that prepares the conversation with numbers instead of a design.
