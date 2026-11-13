# Systems to Build

**Status**: <span class="hg-status summary">plan</span>. The catalog. IDs are stable; everything else on this site refers to them. Each row names its track, the milestone it belongs to, what blocks it, the topic page with research and guidance, and the issue that is or becomes its spec.

Tracks: **A** foundation · **B** shading and rendering · **C** world and simulation · **D** editor and tooling · **E** runtime at scale · **F** quality and process. Milestones are defined on the [roadmap](roadmap.md).

Issue column: existing issues are linked by number; `new` means an issue is created from this plan (label `battle-plan`); after creation the number replaces `new`.

## Track A: foundation

| ID | System | Milestone | Blocked by | Topic | Issue |
|----|--------|-----------|------------|-------|-------|
| S01 | Serialisation schema versioning, skippable records, per-record checksums, canonical text form | M1 | none | [serialization-and-reflection](topics/serialization-and-reflection.md) | [#83](https://github.com/Heliogrim/Heliogrim-Engine/issues/83) |
| S02 | Fiber scheduler v2: waitables, task graph with declared dependencies, priority lanes, thread bridges, deterministic mode | M1 | none | [concurrency-fibers](topics/concurrency-fibers.md) | [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84) |
| S03 | Async storage and streaming backend: request queue with priorities and cancellation, IOCP and DirectStorage, resolved-stack reuse, residency budgets | M1 | S02 | [storage-streaming](topics/storage-streaming.md) | [#85](https://github.com/Heliogrim/Heliogrim-Engine/issues/85) |
| S04 | Observability: fiber-aware spans, counters, ring-buffer trace, export | M1 | S02 | [diagnostics-and-crash](topics/diagnostics-and-crash.md) | [#86](https://github.com/Heliogrim/Heliogrim-Engine/issues/86) |
| S05 | Diagnostics framework: `Diagnostic` type with codes, spans, notes and fixes; result integration; editor rendering | M1 | none | [diagnostics-and-crash](topics/diagnostics-and-crash.md) | [#87](https://github.com/Heliogrim/Heliogrim-Engine/issues/87) |
| S06 | Crash handling: out-of-process minidumps, fiber stacks, crash IDs, symbol store, log ring | M1 | S04 | [diagnostics-and-crash](topics/diagnostics-and-crash.md) | [#88](https://github.com/Heliogrim/Heliogrim-Engine/issues/88) |
| S07 | Large-world coordinates: double world positions, camera-relative render scene, origin rebasing | M2 | none | [render-graph-gpu-driven](topics/render-graph-gpu-driven.md) | [#89](https://github.com/Heliogrim/Heliogrim-Engine/issues/89) |
| S08 | Memory model: tracked allocators, per-subsystem budgets and arenas, reporting | M1 | S04 | [storage-streaming](topics/storage-streaming.md) | [#90](https://github.com/Heliogrim/Heliogrim-Engine/issues/90) |
| S09 | Reflection v2: stable type identity across module reloads, attributes, functions, enum metadata | M2 | none | [serialization-and-reflection](topics/serialization-and-reflection.md) | [#91](https://github.com/Heliogrim/Heliogrim-Engine/issues/91) |
| S10 | Build speed and module structure | M1 | none | [quality-and-process](topics/quality-and-process.md) | [#75](https://github.com/Heliogrim/Heliogrim-Engine/issues/75) |

## Track B: shading and rendering

| ID | System | Milestone | Blocked by | Topic | Issue |
|----|--------|-----------|------------|-------|-------|
| S11 | ASL direct SPIR-V backend and optimiser passes; region borrows | M2 | none | [accel-lang](topics/accel-lang.md) | [#82](https://github.com/Heliogrim/Heliogrim-Engine/issues/82), [#92](https://github.com/Heliogrim/Heliogrim-Engine/issues/92) |
| S12 | All pipeline kinds: compute, mesh, ray-tracing, work graphs through Accel.Compile and the driver | M2 | S11 (partial) | [accel-lang](topics/accel-lang.md) | [#78](https://github.com/Heliogrim/Heliogrim-Engine/issues/78) |
| S13 | Shader variant and pipeline cache: specialisation, pipeline library, disk cache, async compile | M2 | S12 | [accel-lang](topics/accel-lang.md) | [#93](https://github.com/Heliogrim/Heliogrim-Engine/issues/93) |
| S14 | Render graph v2: declarative passes, barriers and aliasing derived from shader interfaces, async compute, multi-queue | M2 | S11 | [render-graph-gpu-driven](topics/render-graph-gpu-driven.md) | [#94](https://github.com/Heliogrim/Heliogrim-Engine/issues/94) |
| S15 | GPU-driven renderer: bindless, GPU instance/material/geometry tables, meshlet culling, indirect draw, visibility buffer, material resolve | M2 | S12, S14, S07 | [render-graph-gpu-driven](topics/render-graph-gpu-driven.md) | [#95](https://github.com/Heliogrim/Heliogrim-Engine/issues/95) |
| S16 | Material system v2: layered materials, emissive, requirement back-propagation into pass enablement | M2 | S13, S14 | [materials-post](topics/materials-post.md) | [#96](https://github.com/Heliogrim/Heliogrim-Engine/issues/96) |
| S17 | Virtual texturing and texture streaming: page tables, feedback, residency, transcoding | M2 | S03, S15 | [storage-streaming](topics/storage-streaming.md) | [#97](https://github.com/Heliogrim/Heliogrim-Engine/issues/97) |
| S18 | Micropolygon geometry pipeline: cluster DAG build, pages, streaming, software and mesh-shader rasterisation | M3 | S15, S17 | [micropolygon](topics/micropolygon.md) | [#98](https://github.com/Heliogrim/Heliogrim-Engine/issues/98) |
| S19 | Shadows: stable CSM with contact shadows first, virtual shadow maps on the GPU-driven pipeline, optional ray-query shadows | M3 | S15 | [shadows-gi](topics/shadows-gi.md) | [#99](https://github.com/Heliogrim/Heliogrim-Engine/issues/99) |
| S20 | Global illumination: multi-bounce diffuse (probe or cascade based), reflections, emissive contribution; ray-traced tier optional | M3 | S15, S16 | [shadows-gi](topics/shadows-gi.md) | [#100](https://github.com/Heliogrim/Heliogrim-Engine/issues/100) |
| S21 | Volumetric sky, atmosphere, clouds and froxel fog | M3 | S12, S14 | [volumetrics-weather](topics/volumetrics-weather.md) | [#101](https://github.com/Heliogrim/Heliogrim-Engine/issues/101) |
| S22 | Transparency: OIT, refraction, interaction with fog and GI | M3 | S15 | [materials-post](topics/materials-post.md) | [#102](https://github.com/Heliogrim/Heliogrim-Engine/issues/102) |
| S23 | Post-processing: HDR output, tone mapping, grading, bloom, DoF, motion blur, temporal upscaling with jitter and motion vectors | M3 | S14 | [materials-post](topics/materials-post.md) | [#103](https://github.com/Heliogrim/Heliogrim-Engine/issues/103) |
| S24 | Particle system: GPU emitters, graph authoring, simulation stages, collisions, sorting, lighting | M3 | S12, S14 | [particles-foliage](topics/particles-foliage.md) | [#104](https://github.com/Heliogrim/Heliogrim-Engine/issues/104) |
| S25 | Foliage: instancing, impostors, wind, near-camera aggregates | M3 | S15, S32 | [particles-foliage](topics/particles-foliage.md) | [#105](https://github.com/Heliogrim/Heliogrim-Engine/issues/105) |
| S26 | GPU render test harness: headless device, golden images with perceptual diff | M1 | none | [quality-and-process](topics/quality-and-process.md) | [#106](https://github.com/Heliogrim/Heliogrim-Engine/issues/106) |

## Track C: world and simulation

| ID | System | Milestone | Blocked by | Topic | Issue |
|----|--------|-----------|------------|-------|-------|
| S27 | Terrain v1: heightfield tiles, clipmap or CDLOD LOD, material layers on virtual textures, height query service | M3 | S07, S17, S40 | [terrain](topics/terrain.md) | [#107](https://github.com/Heliogrim/Heliogrim-Engine/issues/107) |
| S28 | Terrain v2: layered heightfields and voxel overlay for caves and overhangs; live deformation as a replicated brush-op log | M4 | S27, S34, S37 | [terrain](topics/terrain.md) | [#108](https://github.com/Heliogrim/Heliogrim-Engine/issues/108) |
| S29 | Multi-level bounded effects: volumes bound to terrain layers for weather, audio, lighting, physics | M4 | S28 | [terrain](topics/terrain.md) | [#109](https://github.com/Heliogrim/Heliogrim-Engine/issues/109) |
| S30 | Ocean: analytic authoritative height, FFT cascades, foam, shoreline, buoyancy, wakes | M3 | S07, S12, S32 | [ocean-fluids](topics/ocean-fluids.md) | [#110](https://github.com/Heliogrim/Heliogrim-Engine/issues/110) |
| S31 | Fluid dynamics: bounded GPU grid or particle fluids with surface extraction, CPU proxies | M4 | S12, S24 | [ocean-fluids](topics/ocean-fluids.md) | [#111](https://github.com/Heliogrim/Heliogrim-Engine/issues/111) |
| S32 | Weather simulation: state, wind field service, precipitation; drives S21, S25, S30 | M3 | S21 | [volumetrics-weather](topics/volumetrics-weather.md) | [#112](https://github.com/Heliogrim/Heliogrim-Engine/issues/112) |
| S33 | Procedural generation: deterministic graph generators, erosion baking, scatter, roads | M4 | S27, S47 (authoring UI) | [procedural-generation](topics/procedural-generation.md) | [#113](https://github.com/Heliogrim/Heliogrim-Engine/issues/113) |
| S34 | Physics v2: full Jolt surface, determinism and precision decisions, fiber job bridge, characters, vehicles, server islands | M4 | S02, S07 | [physics-cloth](topics/physics-cloth.md) | [#114](https://github.com/Heliogrim/Heliogrim-Engine/issues/114) |
| S35 | Cloth and soft body (XPBD) | M4 | S34, S36 | [physics-cloth](topics/physics-cloth.md) | [#115](https://github.com/Heliogrim/Heliogrim-Engine/issues/115) |
| S36 | Animation system: clips, compression, blend graph, inertialisation, motion matching, IK, retargeting, morph targets, GPU skinning | M4 | S09, S49 | [animation](topics/animation.md) | [#116](https://github.com/Heliogrim/Heliogrim-Engine/issues/116) |
| S37 | Navigation: tiled streamed navmesh, hierarchical queries, crowds, 3D volumes, multi-level terrain | M4 | S40, S27 | [navigation](topics/navigation.md) | [#117](https://github.com/Heliogrim/Heliogrim-Engine/issues/117) |
| S38 | Audio runtime per design, game-event integration, editor UI | M4 | S02 | [audio](topics/audio.md) | [#118](https://github.com/Heliogrim/Heliogrim-Engine/issues/118) |
| S39 | Input v2: contexts, actions, modifiers, triggers, arbitration across UI, editor and game, recording and replay | M2 | none | [input](topics/input.md) | [#119](https://github.com/Heliogrim/Heliogrim-Engine/issues/119) |
| S40 | World partition: streaming cells as archetype handle space, actor and asset streaming, persistence | M2 | S01, S03 | [storage-streaming](topics/storage-streaming.md) | [#120](https://github.com/Heliogrim/Heliogrim-Engine/issues/120) |
| S41 | Content-addressed packages and VCS-friendly asset formats | M2 | S01 | [serialization-and-reflection](topics/serialization-and-reflection.md) | [#121](https://github.com/Heliogrim/Heliogrim-Engine/issues/121) |

## Track D: editor and tooling

| ID | System | Milestone | Blocked by | Topic | Issue |
|----|--------|-----------|------------|-------|-------|
| S42 | Vector canvas: SDF/MSDF renderer, path rasterisation, text shaping service | M3 | S12 | [vector-ui-uikit](topics/vector-ui-uikit.md) | [#11](https://github.com/Heliogrim/Heliogrim-Engine/issues/11), [#41](https://github.com/Heliogrim/Heliogrim-Engine/issues/41), [#122](https://github.com/Heliogrim/Heliogrim-Engine/issues/122) |
| S43 | Uikit completion: inputs, lists, trees, docking, dialogs, animation, accessibility tree | M3 | S42 | [vector-ui-uikit](topics/vector-ui-uikit.md) | [#27](https://github.com/Heliogrim/Heliogrim-Engine/issues/27), [#123](https://github.com/Heliogrim/Heliogrim-Engine/issues/123) |
| S44 | Viewport picking, selection, gizmos | M3 | S39 | [editor-workflows](topics/editor-workflows.md) | [#23](https://github.com/Heliogrim/Heliogrim-Engine/issues/23), [#46](https://github.com/Heliogrim/Heliogrim-Engine/issues/46), [#124](https://github.com/Heliogrim/Heliogrim-Engine/issues/124) |
| S45 | Editor actions v2: transactions, coalescing, multi-object and asset edits, replayable log | M2 | S01 | [editor-workflows](topics/editor-workflows.md) | [#125](https://github.com/Heliogrim/Heliogrim-Engine/issues/125) |
| S46 | Asset search engine: tag registry, text index, query language, watcher | M3 | S09 | [editor-workflows](topics/editor-workflows.md) | [#126](https://github.com/Heliogrim/Heliogrim-Engine/issues/126) |
| S47 | Visual scripting compiler: graph IR, type check, C++ and ASL emitters, source maps | M4 | S09, S48 | [visual-scripting-hmr](topics/visual-scripting-hmr.md) | [#127](https://github.com/Heliogrim/Heliogrim-Engine/issues/127) |
| S48 | C++ hot module reload: module boundaries, reflection-driven state migration, build integration | M4 | S09, S08 | [visual-scripting-hmr](topics/visual-scripting-hmr.md) | [#128](https://github.com/Heliogrim/Heliogrim-Engine/issues/128) |
| S49 | DCC live link: glTF 2.0 importer, watcher-driven reimport, Blender bridge, transform and animation stream | M3 | S36 (animation part) | [dcc-plugins-vcs](topics/dcc-plugins-vcs.md) | [#129](https://github.com/Heliogrim/Heliogrim-Engine/issues/129) |
| S50 | Plugin system: descriptors, discovery, load phases, versioned C-ABI boundary | M4 | S09 | [dcc-plugins-vcs](topics/dcc-plugins-vcs.md) | [#130](https://github.com/Heliogrim/Heliogrim-Engine/issues/130) |
| S51 | VCS integration: provider API, Git and LFS, locking, status and diff in the editor | M4 | S41 | [dcc-plugins-vcs](topics/dcc-plugins-vcs.md) | [#131](https://github.com/Heliogrim/Heliogrim-Engine/issues/131) |
| S52 | Localisation: ICU formatting and plurals, string tables, gather and compile, pseudo-locale, font fallback | M4 | S42 | [localization](topics/localization.md) | [#132](https://github.com/Heliogrim/Heliogrim-Engine/issues/132) |
| S53 | Game-project build system: project descriptor, cook, package, sign, SDK export | M4 | S41 | [build-and-deploy](topics/build-and-deploy.md) | [#133](https://github.com/Heliogrim/Heliogrim-Engine/issues/133) |
| S54 | In-editor test automation: replay driver, fixtures at unit, scene and workflow scope, profile capture | M4 | S45, S39, S59 | [editor-workflows](topics/editor-workflows.md) | [#134](https://github.com/Heliogrim/Heliogrim-Engine/issues/134) |

## Track E: runtime at scale

| ID | System | Milestone | Blocked by | Topic | Issue |
|----|--------|-----------|------------|-------|-------|
| S55 | Networking transport: sockets, TLS, QUIC and HTTP/3, HTTP/2, HTTPS, custom reliable UDP channel | M5 | S02 | [networking-mmo](topics/networking-mmo.md) | [#135](https://github.com/Heliogrim/Heliogrim-Engine/issues/135) |
| S56 | Replication: snapshots, delta compression, interest management, authority transfer, prediction and reconciliation | M5 | S55, S40 | [networking-mmo](topics/networking-mmo.md) | [#136](https://github.com/Heliogrim/Heliogrim-Engine/issues/136) |
| S57 | MMO server mesh: spatial authority, seamless handover, persistence adapters | M6 | S56, S58 | [networking-mmo](topics/networking-mmo.md) | [#137](https://github.com/Heliogrim/Heliogrim-Engine/issues/137) |
| S58 | Headless and cluster roles: role selection, null render device, capability flags, orchestration hooks, telemetry export | M2 | S04 | [build-and-deploy](topics/build-and-deploy.md) | [#138](https://github.com/Heliogrim/Heliogrim-Engine/issues/138) |
| S59 | Determinism and replay: fixed-step deterministic mode, strict FP build, replay record and playback | M3 | S02 | [networking-mmo](topics/networking-mmo.md) | [#139](https://github.com/Heliogrim/Heliogrim-Engine/issues/139) |
| S60 | Automated optimisation and JIT: measured gate, shader specialisation, CPU specialisation candidates | M6 | S13 | [accel-lang](topics/accel-lang.md) | [#140](https://github.com/Heliogrim/Heliogrim-Engine/issues/140) |

## Track F: quality and process

| ID | System | Milestone | Blocked by | Topic | Issue |
|----|--------|-----------|------------|-------|-------|
| S61 | Test suite expansion: module and scene fixtures, editor workflow tests, loader fuzzing | M1 onward | S26, S54 | [quality-and-process](topics/quality-and-process.md) | [#141](https://github.com/Heliogrim/Heliogrim-Engine/issues/141) |
| S62 | CI gates: build matrix, sanitizers, clang-tidy, performance regression bands | M1 | #38 | [quality-and-process](topics/quality-and-process.md) | [#38](https://github.com/Heliogrim/Heliogrim-Engine/issues/38), [#142](https://github.com/Heliogrim/Heliogrim-Engine/issues/142) |
| S63 | Coding standard and quality bar: written standard, review checklist, contract comments | M1 | none | [quality-and-process](topics/quality-and-process.md) | [#143](https://github.com/Heliogrim/Heliogrim-Engine/issues/143) |
| S64 | Documentation system: reference generation, system pages per shipped system | M1 onward | none | [quality-and-process](topics/quality-and-process.md) | [#144](https://github.com/Heliogrim/Heliogrim-Engine/issues/144) |

## Progress (checked 2026-11-10)

Every battle-plan issue carries a comment "Battle-plan sync from Heliogrim-Pages (2026-11-10)" with its chunk statuses, decisions and engine state; this table is the same state per system. Systems not listed have no chunk started. Chunk detail lives on the [work pages](work/index.md).

| ID | Chunks done | Engine state |
|----|-------------|--------------|
| S02 | W02.1, W02.2, W02.3 | W02.2 in PR [#159](https://github.com/Heliogrim/Heliogrim-Engine/pull/159) (`feat/scheduler-waitables` into `feat/wip`, merged into `feat/wip` 2026-11-11, closes #157 once `feat/wip` reaches `master`). W02.3 in PR [#164](https://github.com/Heliogrim/Heliogrim-Engine/pull/164), merged into #159 2026-11-11. Found on the way: #160 to #163; real-input checks (drag, resize, dialog) still owed. W02.4 done 2026-11-11; W02.5 plan half in PR [#175](https://github.com/Heliogrim/Heliogrim-Engine/pull/175) into `feat/wip` (task graph runs the frame, auto worker count), its relaxation half blocked behind W02.8 and W02.6 (2026-11-13). Next: W02.8, W02.6, W02.0 |
| S03 | W03.1, W03.2, W03.3 | W03.2 in PR [#169](https://github.com/Heliogrim/Heliogrim-Engine/pull/169), merged into `feat/wip` 2026-11-13; editor shader-load check and #24 with the owner. W03.4 in progress on `feat/async-storage` from `feat/wip` (plan `docs/superpowers/plans/2026-11-09-async-storage-iocp.md`, untracked). Q03.5 and Q03.6 decided |
| S10 | none | W10.3 code done 2026-11-10: spelled-out bundle names (`Engine.Physics`, `Engine.Graphics*`, `Editor.Graphics*`, `Engine.Audio`) in PR #167, merged into `feat/wip` 2026-11-11. W10.1 code done 2026-11-10: header diet without PCH in stacked PR #168, merged into `feat/wip` 2026-11-11; clean build-time number open. Both unmerged |
| S11 | W11.1 region borrows (#82) | Milestone 2 and the region borrows (PR [#156](https://github.com/Heliogrim/Heliogrim-Engine/pull/156)) are on `master` (checked 2026-11-13). W11.0 code done 2026-11-13: #148 fix on `fix/asl-reserved-names` (unpushed), [design page](../architecture/accel-lang-design.md) written |
| S37 | W37.0 | Nothing vendored. Detail-mesh sample cache patch and spike source untracked under `docs/superpowers/patches/`. Owner call open: offer the patch upstream. W37.1 waits on W27.1, W40.1 |
| S39 | W39.0 | No engine change. SDL 3.2.22 to 3.4.x upgrade is task 1 of the W39.1 plan |
| S56 | W56.0 (desk study) | No engine change. Prototype half waits on W55.3 |
| S64 | W64.4 (seeded) | [Glossary](../glossary.md) with about 130 terms; hover terms open |

## Existing issues absorbed by systems

| Issue | System |
|-------|--------|
| #3 to #9 component serialisation | S01 (generated serialisation from #80 covers archetype components) |
| #10, #22, #39, #43, #44, #74 Reflow invalidation and contexts | S42, S43 |
| #11 to #17 2D SDF primitives | S42 |
| #23, #46, #47, #50 gizmos, outline, grid, material preview | S44 |
| #24 shader read-operation URL bug | S03 |
| #25 to #36 widgets | S43 |
| #26 icon atlas | S42 |
| #41 text measuring and shaping | S42 |
| #45 hierarchy actions | S45 |
| #73 archive delta merge stream | S03 |
| #75 build speed | S10 |
| #77 Arci split-count protocol | S02 (foundation for waitables) |
| #78, #82 Accel IR | S11, S12 |
| #80 sealed actor archetypes | S40 (streaming cell as handle space) |
| #148 GLSL name collisions | S11 (W11.0) |
| #150, #158, #160, #161, #162 engine and editor stop ordering | S02 |
| #154 `Resource<T>` never releases, #166 nested storage deadlock, #171 `Path::name()` wide characters | S03 |
| #163 shader modules destroyed late on editor exit | S12 |
| #170 `CompileMap` find above 56 entries | S09 |
| #174 `Signal` destroy rule | S02 |

Open bug issues and the 25 logged test-note bugs are tracked together in the W61.1 ledger on the [quality work page](work/quality-and-process.md) (synced 2026-11-13).
