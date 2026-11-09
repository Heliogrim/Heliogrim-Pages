# Questions for the Owner

**Status**: <span class="hg-status summary">plan</span>. All 125 questions from the [work pages](index.md), grouped into batches that one conversation can clear. Each row names the chunk it blocks and the default a session uses if the question stays open. Answers go back into the work page and, where they decide architecture, into an ADR placeholder.

## Batch 1: Foundations (unblocks M1 design chunks)

**Closed 2026-11-08.** All 22 answered; decisions are in the "Decisions" section of each work page (concurrency, serialisation, diagnostics, storage). Architecture-level outcomes have [ADR placeholders](../../adr/README.md).

| ID | Question | Default | Blocks |
|---|---|---|---|
| Q02.1 | Cancellation: token per task with cooperative checks, or none in v2? | Token with cooperative checks | W02.1 |
| Q02.2 | Keep the global per-priority FIFO and fix waiting only, or per-worker queues with stealing in the same step? | Fix waiting first | W02.1 |
| Q02.3 | Intended fiber stack size (4 KB commit, 1 MB reserve) and is depth bounded by policy? | Measure; 64 KB commit if guard pages prove unreliable | W02.0 |
| Q02.4 | Is Vulkan queue submit an affine service or the frame's last stage? | Affine for present and transfer; graphics submit stays until S14 | W02.3 |
| Q02.5 | Do all coroutines run on fibers? | Yes | W02.7 |
| Q02.6 | Does `std::execution` vocabulary matter for the public API now? | No | W02.7 |
| Q01.1 | Schema version per record header, or once per type in package meta? | Per record header | W01.1 |
| Q01.2 | Upcasters on record bytes, native structs, or per type by choice? | Per type, default bytes | W01.1 |
| Q01.3 | Text form syntax: project key-value, JSON or YAML? | Project key-value with a strict grammar | W01.4 |
| Q09.1 | Function reflection: overloads and templates, or non-overloaded members and free functions only? | Non-overloaded members and free functions | W09.1 |
| Q09.2 | Attributes: closed enum set or open string-keyed map? | Closed set with a plugin extension slot | W09.1 |
| Q05.1 | `Result<T, Diagnostic>` everywhere, or at system boundaries only? | Boundaries only | W05.1 |
| Q05.2 | Fixes for assets as record edits in v1, or text edits only? | Text edits first | W05.1 |
| Q04.1 | Trace viewer: in-editor only, or also Perfetto or Tracy export? | Own format plus Perfetto converter | W04.1 |
| Q04.2 | Ring overflow: drop newest, overwrite oldest, or stall in Profile tier? | Overwrite oldest with a drop counter | W04.1 |
| Q04.3 | Metered-run mode in S04 or S59? | S59 | W04.1 |
| Q04.4 | First OTLP metrics for servers? | Frame percentiles, cell count, memory per subsystem, queue depth | W04.3 |
| Q03.1 | Stack cache key: scheme and repository, action type, or both? | Both | W03.1 |
| Q03.2 | Windows IO: IOCP now, DirectStorage later, or DirectStorage from the start? | IOCP first | W03.3 |
| Q03.3 | Codec by benchmark, or zstd by policy? | Benchmark decides | W03.5 |
| Q03.4 | Can the package layout PDF be shared, or is the source-derived layout the reference? | Source-derived | W03.3, W41.1 |
| Q08.1 | Override global `operator new` for tracking, or explicit allocators only? | Explicit plus debug-only hook | W08.1 |

## Batch 2: Quality, process, vendor policy

**Closed 2026-11-08.** All 20 answered; decisions are in the "Decisions" section of each work page. Notable: no licensed or paid software (Q48.1), in-house crash handler (Q06.1), in-house asset index and derived cache (Q46.1), vendor comparisons required before picking meshlet and navmesh libraries (Q18.1, Q37.1).

| ID | Question | Default | Blocks |
|---|---|---|---|
| Q63.1 | MISRA C++:2023 reading list only, or compliance claim with deviations for hardened bundles? | Reading list | W63.1 |
| Q63.2 | Exceptions banned in `Engine.*`, allowed in `Editor.*` tooling and tests? | Yes | W63.1 |
| Q62.1 | GitHub-hosted runners with lavapipe only, or a self-hosted GPU runner? | Hosted plus lavapipe | W62.1 |
| Q62.2 | Performance band width and first scenarios? | p95 within 10%; transform, IO 1,000-request, scheduler fan-out | W62.1 |
| Q62.3 | Paid analyzer or clang-tidy plus CodeQL? | clang-tidy plus CodeQL | W62.1 |
| Q26.1 | FLIP threshold per test or global? | Per test with a global default | W26.1 |
| Q64.1 | Doxygen acceptable as a fallback to `clang-doc`? | Yes, without annotations | W64.1 |
| Q10.1 | Is a C++ modules migration still a goal after the 4 to 8 person-month estimate? | No, close unless W10.1 halves it | W10.2 |
| Q06.1 | Crashpad acceptable as a vendored dependency? | Yes if its build fits CMake | W06.1 |
| Q06.2 | Crash upload path now or local database only? | Local only, upload seam reserved | W06.1 |
| Q18.1 | meshoptimizer vendored or in-house builder? | Vendor | W18.1 |
| Q36.1 | ACL vendored or in-house compression? | Vendor if W36.0 builds cleanly | W36.1 |
| Q37.1 | Recast and Detour vendored or in-house voxeliser? | Vendor, wrapped | W37.1 |
| Q46.1 | SQLite FTS5 vendored or in-house inverted index? | SQLite FTS5 | W46.1 |
| Q42.1 | HarfBuzz, FreeType, ICU acceptable as text vendors? | Yes, ICU trimmed | W42.1 |
| Q52.2 | ICU full or trimmed data? | Trimmed | W52.1 |
| Q49.1 | FBX through ufbx only, or also the Autodesk SDK? | ufbx only | W49.1 |
| Q48.1 | Live++ licence acceptable, or in-house patcher only? | Trial in W48.0; licence if in-house costs over two weeks | W48.1 |
| Q55.1 | A C QUIC library under MIT or BSD acceptable? | Yes | W55.1 |
| Q23.2 | Vendor upscaler SDKs beyond FSR? | FSR only | W23.1 |

## Batch 3: Rendering baseline

**Closed 2026-11-09.** All 30 answered or deferred; decisions are in the "Decisions" section of each work page. Notable: minimum spec RDNA3 and Ada Lovelace with mesh shaders and ray query required, baseline RTX 4070 (Q12.2, Q15.1); VSM required (Q19.1); GI questions Q20.1 and Q20.3 deferred to the widened W20.0 brief; spelled-out bundle names, chunk W10.3 (Q24.2); AgX game view, PBR Neutral asset check (Q23.1).

| ID | Question | Default | Blocks |
|---|---|---|---|
| Q11.1 | Push and PR the Accel IR milestone 2 branch now, or GPU verification first? | Push now | W11.0 |
| Q11.2 | Slang: oracle, backend, or neither? | Neither as a dependency | W11.2 |
| Q11.3 | Own optimiser beyond `spirv-opt` plus the three semantic passes? | No | W11.2 |
| Q12.1 | Reserve a work-graph pipeline kind now? | Enum value only | W12.1 |
| Q12.2 | Minimum spec split: descriptor indexing and 64-bit atomics required; mesh shaders and ray query optional? | Yes; RDNA2 and Turing class | W12.1, W15.0 |
| Q13.1 | Pipeline library now or after a measured hitch? | Design now, implement after measurement | W13.1 |
| Q60.1 | Keep S60 (JIT) open or close until evidence? | Close with the gate recorded | W60.1 |
| Q07.1 | Rebasing threshold: fixed distance or per-cell origin? | Per cell once S40 exists; 1 km until then | W07.1 |
| Q07.2 | Jolt double build or per-region offset? | Offset first; double evaluated in W34.0 | W07.1, W34.1 |
| Q14.1 | Async compute from the first version or hint-only? | Hint-only | W14.1 |
| Q14.2 | One primary command buffer per pass, or secondaries merged per queue? | Primary per pass | W14.1 |
| Q15.1 | Baseline GPU and frame budget? | RTX 2070 or RX 6600 class, 16.6 ms at 1440p | W15.0 |
| Q15.2 | Visibility buffer into a G-buffer, or shade directly? | Thin G-buffer; transparency forward | W15.1 |
| Q15.3 | Visibility buffer 64-bit now or 2x32 until S18? | 2x32 now | W15.1 |
| Q16.1 | Fixed layer set or open layer stack? | Fixed set | W16.1 |
| Q16.2 | glTF, OpenPBR, or both as canonical parameter names? | glTF canonical, OpenPBR mapping | W16.1 |
| Q22.1 | Moment OIT planned or only on failure of weighted blended? | On failure only | W22.1 |
| Q23.1 | Default tone map: PBR Neutral or AgX? | PBR Neutral | W23.1 |
| Q18.2 | Mesh shaders required, optional, or skipped? | Optional | W18.5 |
| Q18.3 | Geometry page size relative to the storage chunk? | 128 KiB | W18.1 |
| Q19.1 | VSM required for M3, or CSM closes M3? | CSM closes M3 | W19.1 |
| Q20.1 | Trace scene: global SDF, voxels, or ray queries? | SDF plus voxelised static; ray queries as tier | W20.1 |
| Q20.2 | Probe grid first, or cascades as the primary bet? | Probe grid | W20.1 |
| Q20.3 | Ray-traced GI a target tier in the first release? | No; reflections and shadows only | W20.1 |
| Q21.1 | Target view distance for fog and clouds? | 32 km horizon, 2 km froxel far plane | W21.1 |
| Q21.2 | Cloud technique by spike, or voxel authoring a product requirement? | Spike decides | W21.0 |
| Q24.1 | Share the S47 graph IR from the start or a particle-specific stage compiler first? | Particle-specific first | W24.1 |
| Q24.2 | Bundle name `Engine.VFX` for particles? | Yes | W24.1 |
| Q25.1 | Aggregate leaf LOD: spike or skip? | Skip | W25.1 |

## Batch 4: World

| ID | Question | Default | Blocks |
|---|---|---|---|
| Q40.1 | Cell size: fixed 256 m or hierarchical from the start? | Fixed 256 m | W40.1 |
| Q40.2 | Cells 2D or 3D? | 2D with S28 height layers | W40.1 |
| Q40.3 | Does `Level` survive as a named cell set in the public API? | Yes | W40.1 |
| Q17.1 | Software page-table indirection first, or `sparseResidency` from the start? | Software first | W17.1 |
| Q27.1 | Terrain tile size and resolution? | 64 m at 1 m spacing; 4x4 per cell | W27.1 |
| Q27.2 | Height storage 16-bit with per-tile range or float32? | 16-bit | W27.1 |
| Q28.1 | Voxel overlay: Dual Contouring or Surface Nets? | Dual Contouring | W28.1 |
| Q28.2 | May terrain v2 ship before navigation consumes layers? | Yes | W28.1 |
| Q29.1 | Authored volumes enough for the first consumers before S28? | Yes | W29.1 |
| Q32.1 | Weather regions: terrain tiles or authored volumes? | Authored volumes with a tile grid default | W32.1 |
| Q32.2 | Weather server-authoritative from v1, or client-local until S56? | Replication-ready, local driver | W32.1 |
| Q30.1 | Gerstner or spectral components for the authoritative layer? | Gerstner unless the spike says otherwise | W30.1 |
| Q30.2 | Cascade count and resolution? | Four at 256² until measured | W30.1 |
| Q31.1 | Fluids inside `Engine.VFX` or own bundle? | Inside `Engine.VFX` | W31.1 |
| Q31.2 | Fluid scope in the first release? | Splashes and smoke | W31.1 |
| Q33.1 | Which generators are authoritative versus cosmetic? | Terrain deltas, roads, structures, gameplay props authoritative | W33.1 |
| Q33.2 | Wait for S47 before graph authoring, or a small interpreted graph now? | Wait | W33.1 |
| Q34.1 | Accept `JPH_DOUBLE_PRECISION` if cost is at or below 10%? | Yes | W34.1 |
| Q34.2 | Server physics at MMO density: full bodies or kinematic proxies by default? | Proxies by default | W34.1 |
| Q34.3 | Jolt debug renderer build in the server role? | Split builds per role | W34.1 |
| Q35.1 | Crowd-scale cloth in the first release? | No | W35.1 |
| Q36.2 | Dual quaternion skinning as a per-asset option in v1? | Yes | W36.1 |
| Q36.3 | Motion matching in the first release? | After | W36.1 |
| Q37.2 | Clients predict NPC movement, or server only? | Server only | W37.1 |
| Q38.1 | Approve the audio design proposals as written? | Approve | W38.0 |
| Q38.2 | Reorder nodes with smoothed gains, or constant-parameter nodes only? | Constant only | W38.0 |
| Q38.3 | Delay compensation across banks in milestone 4 or later? | Later | W38.0 |
| Q38.4 | Event model: Wwise-style full set, or events plus parameters plus states? | Events, parameters, states | W38.5 |

## Batch 5: Editor and tooling

| ID | Question | Default | Blocks |
|---|---|---|---|
| Q39.1 | SDL3 now with native Win32 later, or native in this system? | SDL3 now | W39.1 |
| Q39.2 | Contexts as a strict stack or a prioritised set? | Prioritised set | W39.1 |
| Q42.2 | Day-one primitive scope: full #12 to #17 list or a subset? | Full list, paths last | W42.1 |
| Q43.1 | UI Automation provider in the first release, or semantic tree only? | Semantic tree first | W43.1 |
| Q44.1 | What is drawn on a selected object by default and what is toggleable? | Mode-switched transform gizmo; toggles per system | W44.2 |
| Q44.2 | Day-one picking scope? | Geometry, light icons, gizmo handles | W44.2 |
| Q44.3 | Richness gizmos editor-only or also game debug? | Editor-only first | W44.2 |
| Q45.1 | Asset edits: per-asset sessions or global history with barriers? | Per-asset sessions | W45.1 |
| Q54.1 | First workflow acceptance scenario for the test driver? | Import glTF, place, gizmo move, save, reload, hash | W54.1 |
| Q47.1 | Confirm no managed scripting runtime in the plan horizon? | Confirm | W47.0 |
| Q47.2 | Does shipping include the interpreter? | No; emitted C++ mandatory | W47.1 |
| Q48.2 | User-authored native modules (mods) in scope? | First-party only | W48.1 |
| Q50.1 | Binary C-ABI plugin tier in the first release? | Same-toolchain only | W50.1 |
| Q51.1 | Perforce provider planned? | Not planned | W51.1 |
| Q52.1 | In-house Fluent-like message syntax now, or wait for ICU MF2? | In-house now | W52.1 |
| Q53.1 | Game modules static or DLL in shipping? | Static in shipping, DLL in development | W53.1 |
| Q53.2 | Azure Artifact Signing or a local certificate workflow? | Local with a pluggable signer | W53.1 |

## Batch 6: Scale and determinism

| ID | Question | Default | Blocks |
|---|---|---|---|
| Q58.1 | Agones or plain Kubernetes StatefulSets? | Plain probes now, Agones adapter later | W58.1 |
| Q58.2 | When is a Linux toolchain acceptable in CI? | As soon as W58.2 lands | W58.1, W62.1 |
| Q59.1 | Determinism scope: (a) same binary, or (b) same compiler across machines? | (b) for simulation bundles | W59.1 |
| Q55.2 | Custom UDP first, or QUIC datagrams first? | Custom UDP first | W55.1 |
| Q56.1 | Prediction scope: local actor only, or also vehicles and mounts? | Local actor and its mount | W56.1 |
| Q57.1 | Load shedding: time dilation, tick-rate degradation, or admission limits? | Tick-rate degradation with admission limits | W57.1 |
| Q57.2 | Persistence: own journal through storage, or external database adapter from the start? | Own journal, adapter reserved | W57.1 |

## How to answer

Reply per batch with the ID and one line each; "default" accepts the suggested default. The session that picks up the next chunk folds the answers into the work page and, for architecture decisions, drafts the ADR placeholder.
