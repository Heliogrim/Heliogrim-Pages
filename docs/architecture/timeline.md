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
| 2026-11-09 | Question batch 4 (world, 25) answered by the owner; decisions on the work pages, three new spikes (W39.0 input backends, W31.4 next-generation gas solvers, W56.0 tiered agent synchronisation), fluids become their own bundle, partition set to a 2D quadtree over fixed leaf cells with authored height layers |
| 2026-11-09 | Question batch 5 (editor and tooling, 17) answered by the owner; decisions on the work pages: source plugins built locally, first-party modules only, no managed runtime, per-document undo streams, guided signing workflow |
| 2026-11-09 | Question batch 6 (scale and determinism, 10) answered by the owner; all six batches closed. Web protocols are for auth and services only, `d` and the T1 cap float at runtime, dynamic sharding by player density expected, dynamic cell splitting and cooperative nodes to be measured in W57.0. Glossary chunk W64.4 added |
| 2026-11-08 | W02.1 done: [Scheduler waitables design](scheduler-waitable-design.md) drafted and builder-checked (park handshake, event, join counter, fiber mutexes, cancellation token, migration list); implementation plan in the engine checkout; W02.2 and W02.3 become ready. Follow-up the same day: [Promise and future rework](promise-future-design.md) drafted on the owner's request, with its own plan |
| 2026-11-09 | W02.2 executed: both plans implemented on engine branch `feat/scheduler-waitables` (38 commits, all suites green, editor starts), every task and the whole branch reviewed; both design pages amended with the contracts found during implementation (park-queue `Locked` view, destruction-safe `Event::set`, `Event::reset`, `hg::Signal`, reader CAS admission, `Send` at creation points, `async` on `then`, dispatcher-owned action signal). W02.3 ready |
| 2026-11-09 | W02.3 done: [Affine threads design](affine-thread-design.md) (one owned-thread seam with direct completion, no inbox bound, a message-window drain so modal loops keep draining, the shutdown order fix, an IOCP thread skeleton), builder-checked and re-checked against the engine; 6-task plan in the engine checkout. W03.3 ready, with the storage access pattern from the same conversation as input |
| 2026-11-09 | W02.3 executed: affine threads, the platform thread on a message-window drain (modal-safe, no spinning: editor idle CPU roughly halved), the shutdown order fixed in both engines, an IOCP `IoThread` skeleton; six tasks reviewed and a whole-branch review on engine branch `feat/affine-threads`; real-input checks (drag, resize, dialog) left for the owner |
| 2026-11-09 | Scheduler waitable `Event` renamed `Signal` (`engine::scheduler::Signal`, matching the `hg::Signal` alias) to keep it apart from the `Engine.Event` emitter types; folded into PR #159 before it lands, design docs updated. |
| 2026-11-09 | W56.0 desk study: [Agent and player sync](agent-sync-exploration.md) answers Q37.2 with five tiers (self, engaged, perceptive, distant, outside interest) and server-scheduled action events as the meaning of "lock-step action evaluation"; only action evaluation needs determinism. Loopback prototype waits for W55.3. Findings folded into the networking, navigation, animation and physics work pages and the networking topic; owner points became Q56.2 to Q56.4 in Batch 6 |
| 2026-11-09 | W39.0 done: [Input backends exploration](input-exploration.md) (SDL3 versus native per platform). Proposal: SDL3 stays the base backend (upgrade 3.2.22 to 3.4.x), native capability side channels only where evidence shows a gain (Windows raw mouse in absolute mode, pen history, pointer touch; iPadOS coalesced touches and Pencil; Wayland tablet pads and gestures); Windows spike on injected input showed no SDL overhead for keyboard and relative mouse. Accepted by the owner the same day: exploration closed, ADR [placeholder](../adr/placeholder-input-backend-sdl3-base.md), Q39.1 resolved; W39.1 ready |
| 2026-11-09 | W37.0 done: [Navmesh library fit](navigation-exploration.md) compares recastnavigation, Godot, O3DE, Polyanya, ports, volume libraries and an in-house builder. Proposal: vendor recastnavigation (zlib) at a pinned `main` commit with 64-bit poly refs; hierarchy, flow fields, voxel octree and build scheduling in-house. Spike on a 5900X: builds clean as C++23 with clang-cl 22; 64 m tile voxelise p50 42 ms, 1.4 s per km² on 24 threads; long sliced paths p99 0.23 ms; 1,000-agent crowd 3 ms per tick; TileCache obstacle edit 0.3 ms per layer. TileCache layers cap at 255 cells, so 64 m tiles need a cell of at least 0.25 m. Awaits owner acceptance; W37.1 now waits only on W27.1 and W40.1 |
| 2026-11-09 | Owner accepted the W37.0 recommendation: [Navmesh library fit](navigation-exploration.md) closed, ADR [placeholder](../adr/placeholder-navmesh-recastnavigation.md), Q37.1 resolved. Performance pass (section 10): the detail mesh is 76 % of a 64 m tile build because upstream rebuilds the triangulation and rescans every sample per insertion; a sample-distance cache patch gives byte-identical tiles at 20 ms instead of 44 ms per tile (0.5 s per km² on 24 threads, 5900X). Layers partitioning is near-free; allocator arenas and GPU voxelisation do not help. Incremental Delaunay, terrain via rcAddSpan and threaded crowd avoidance move to W37.2 |
| 2026-11-09 | W03.1 done: [Storage design](storage-design.md) section 1, resolved-stack reuse. Engine check: type-level chains were already cached; the runtime stage state (open blob, parsed package, archive view) is rebuilt per call, and overlapping queries on one package hit an assert. Per-stage cache keyed by (storage instance, resource type) with prefix reuse, query stages only, one shared lock per primary storage, invalidation of the whole chain after commit under the write lock, 512-entry stopgap bound; #24 reduces to reading shaders through storage. 5-task plan in the engine checkout; W03.2 ready |
| 2026-11-09 | W03.3 done: [Storage design](storage-design.md) section 2, async request path and IOCP backend. `IoSystem` on the W02.3 `IoThread`: DirectStorage-shaped batches with one future each, priority per queue (four levels), FIFO batch resolution per queue, tag cancellation with "no buffer write after the future resolves", 64 requests in flight, buffered overlapped I/O first. `IoFileBlob` makes each `Blob::read` one fiber park, so parsers stay unchanged; `WindowedBlob` (8 MiB, per guard) keeps archive walks in memory; `queryAsync`/`mutateAsync` become scheduler tasks. `StorageModule` owns the system. 5-task plan in the engine checkout, runs after W03.2; W03.4 ready after W03.2 |
| 2026-11-09 | Q03.5 and Q03.6 decided (storage design 2.3, 2.4): IO in-flight cap 64 to start, tuned by the W03.4 benchmark, high-priority slot reservation only on evidence; a dropped batch future never cancels, and `IoRequest` gains an optional `keepAlive` buffer owner so dropping is safe |

!!! note "Keeping this page current"
    Append a row to the log in the same pull request that changes a status or records an ADR.
