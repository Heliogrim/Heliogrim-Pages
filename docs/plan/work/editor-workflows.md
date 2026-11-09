# Work: Editor Workflows: Picking and Gizmos, Actions v2, Asset Search, Test Automation

**Systems** S44, S45, S46, S54 · **Issues** [#124](https://github.com/Heliogrim/Heliogrim-Engine/issues/124), [#125](https://github.com/Heliogrim/Heliogrim-Engine/issues/125), [#126](https://github.com/Heliogrim/Heliogrim-Engine/issues/126), [#134](https://github.com/Heliogrim/Heliogrim-Engine/issues/134); absorbed #23, #45, #46, #47, #50 · **Track** D · **Milestone** M2 to M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Editor workflows](../topics/editor-workflows.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Viewport picking notes (memory, 2026-10-29) | CPU ray cast over per-object proxies with sorted hits and layer mask; flat SoA bounds first, dynamic AABB tree if the benchmark demands; separate from physics broadphase; ID buffer only as a refinement; old octree not resurrected | Gizmo question unanswered ("what is drawn on top, what is toggled"); day-one picking scope; richness levels; editor-only versus game debug |
| [Bounding volumes exploration](../../architecture/bounding-volumes.md) | Spatial query options and research leads | Benchmark (1k to 1M boxes, churn) never run (W44.0) |
| `Editor.Action` (`ActionManager`, `ActionLog`, `ActionDispatcher`, `DelegateAction`), test notes bugs 12 and 13 | Action log exists; `reapply` broken | Transactions replace the action classes |
| Uncommitted `Editor.Scene.Actions/SaveUniverse.*` in the engine checkout | A new action in flight | W45.1 reviews it |
| [Serialisation work](serialization-and-reflection.md) S01, S09 | Record paths, reflected fields | Deltas keyed by stable IDs |
| [Storage work](storage-streaming.md) S40 | Handle epochs | Deltas survive archetype relocation through handles |
| [Input work](input.md) | Gizmo capture context, recorder | S44 and S54 consumers |
| [Vector UI work](vector-ui-uikit.md) | Semantic tree | S54 asserts through it |
| [Quality work](quality-and-process.md) S26, S61 | GPU goldens, scene fixtures | S54 drives them from the editor |
| [DCC work](dcc-plugins-vcs.md) S49 | File watcher | Shared with S46 |

## Architecture

- **Bundles**: new `Engine.Scene.Query` (bounds query service, flat SoA bounds, later AABB tree), `Editor.Viewport.Picking`, `Editor.Viewport.Gizmos` (overlay pass fragments); `Editor.Action` rebuilt around `Transaction`; new `Editor.Search` (tag registry, reference graph, text index, query language) and `Engine.Filesystem.Watcher` (shared with S49); new `Editor.Automation` (driver, fixtures, test panel).
- **Provides**: pick and selection services, gizmos, transactional undo, asset search, workflow test driver.
- **Consumes**: render graph overlay (S14), input contexts (S39), serialisation (S01), reflection (S09), handles (S40), semantic tree (S43), trace (S04), goldens (S26), deterministic mode (S59), null device (S58).

## Code design

| Type | Contract |
|---|---|
| `BoundsQueryService` | `query(Ray or Frustum, LayerMask) -> sorted hit list`; backed by a flat SoA bounds array per scene fed like other scene systems; upgrade path to a dynamic AABB tree with fat boxes behind the same interface. |
| `PickLayer` | Bit mask per object class (geometry, light icon, audio icon, physics proxy, gizmo). |
| `GizmoOverlay` | Render graph fragment drawing handles, bounds and icons with depth options; `RichnessLevel` per system toggled in the editor; billboards for meshless objects are pickable through the same service. |
| `SelectionOutline` | Stencil or ID pass (#46); `InfiniteGrid` (#47); `MaterialPreview` (#50). |
| `Transaction` | `{ name, scope stack, deltas }`; `begin`, `commit`, `abort`; nested merge into parent; coalescing by key for continuous edits. |
| `Delta` | Reflection-based record change keyed by `ActorPath` or `AssetPath` (S05 `Location` types); structural kinds `Spawn, Destroy, Reparent`; never a pointer. |
| `AssetSession` | Per-asset history; save is an undo barrier for that asset only. |
| `ActionLog` | Serialised with S01; replayable; the recorder for S54. |
| `TagRegistry` | Typed tags published by importers; `ReferenceGraph`; `TextIndex` (SQLite FTS5 vendored, or in-house inverted index per Q46.1); `Query` language `type:`, `ref:`, `tag:`, free text. |
| `FileWatcher` | Platform watcher plus reconciliation scan; shared with S49. |
| `AutomationDriver` | Replays action log plus input recording against a fixture with fixed step and deterministic mode; asserts on state hashes, semantic queries, goldens; captures a trace per scenario. |
| `FixtureScope` | `Unit, Module, Scene, Workflow`; tags map to CI jobs (S61). |

Placement: `Engine.Scene.Query/BoundsQueryService`, `Editor.Viewport.Picking/`, `Editor.Viewport.Gizmos/`, `Editor.Action/{Transaction,Delta,AssetSession,ActionLog}`, `Editor.Search/`, `Engine.Filesystem.Watcher/`, `Editor.Automation/`. Tests: pick through translucent by cycling; light picked by icon; multi-object and asset undo together; log replays to the same hash; search latency over 100k assets; recorded workflow replays in CI.

## Work chunks

### W44.0 Bounds query benchmark · explore · ready

- **Goal**: run the benchmark from the notes (1k to 1M boxes, uniform and clustered, ray and frustum, 1 to 50% churn) for flat SoA versus a dynamic AABB tree; record the crossover.
- **Output**: results in `architecture/bounding-volumes.md`.

### W44.1 Finish the picking and gizmo brainstorm · explore · ready

- **Goal**: resume with the gizmo question, day-one picking scope, richness levels, editor-only versus game debug, order of the three projects.
- **Output**: `architecture/picking-gizmos-exploration.md`.
- **Questions**: Q44.1, Q44.2, Q44.3.

### W44.2 Picking, selection and gizmos design · design · after W44.0, W44.1, W39.1

- **Output**: `architecture/picking-gizmos-design.md`; plan.

### W44.3 Implement bounds query service and picking · execute · after W44.2

- **Done when**: an object is picked through a translucent one by cycling; a light is picked by its icon.

### W44.4 Implement gizmos, outline, grid, preview · execute · after W44.3, W14.2, W45.3

- **Done when**: gizmos move a selection with undo; #46, #47, #50 closed.

### W45.1 Actions v2 design · design · after W01.1, W09.1

- **Goal**: transactions, deltas by stable ID, coalescing, asset sessions, log serialisation and replay, migration of existing actions and the uncommitted `SaveUniverse` action, fix of the `reapply` bugs.
- **Output**: `architecture/editor-actions-design.md`; plan.
- **Questions**: Q45.1.

### W45.2 Implement transactions and deltas · execute · after W45.1, W01.2

- **Done when**: a multi-object transform and an asset edit undo and redo together; bugs 12 and 13 closed with tests.

### W45.3 Implement coalescing, asset sessions and log replay · execute · after W45.2

- **Done when**: the log replays to the same state hash.

### W46.1 Asset search design · design · after W09.1

- **Output**: `architecture/asset-search-design.md`; plan.
- **Questions**: Q46.1.

### W46.2 Implement tag registry, index, query and watcher · execute · after W46.1, W09.2

- **Done when**: `type:material tag:emissive` over 100k assets returns within the stated latency; a renamed file is found without a rebuild.

### W54.1 In-editor test automation design · design · after W45.1, W39.1, W59.1

- **Output**: `architecture/editor-automation-design.md`; plan.
- **Questions**: Q54.1.

### W54.2 Implement driver, fixtures and test panel · execute · after W54.1, W45.3, W39.4, W59.2, W58.2

- **Done when**: a recorded workflow (import, place, edit, save) replays in CI and fails on a deliberate regression.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q46.1 | In-house, no SQLite. Scale assumed: a few hundred tree types with variations, a few hundred rocks, each with colour, ARM, emissive and mask textures, so tens of thousands of asset records. Layout: (1) authored metadata (tags, display names) lives in the asset's text-form sidecar and is under version control; (2) an editor-only derived cache directory per project, ignored by version control (`.heliogrim/cache/`), holds the asset catalog (GUID, path, type, tags, dependencies, source hash, mtime) and the search index, both written with the engine serialiser, rebuilt from sources when missing or stale; (3) thumbnails and other derived data are content-addressed by source hash in the same cache with an LRU size budget, so an unchanged asset is never re-rendered and a cache wipe only costs time. Search is a trigram or prefix index over the catalog, in memory, incrementally updated by the file watcher. W46.1 designs this. Any editor database would have been editor-only; none is needed at this scale. |
| Q44.2 | Day-one picking: geometry, light icons and gizmo handles; audio and physics proxies through the richness toggles. |
| Q44.3 | Richness gizmos editor-only first; the overlay fragment is written so a game debug overlay can reuse it. |
| Q54.1 | First acceptance scenario for the test driver: import a glTF, place it, move it with a gizmo, save, reload, compare the hash. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q44.1 | Gizmos: what is drawn on top of a selected object by default (translate handles only, or translate, rotate, scale by mode), and what is toggleable (bounds, light radii, audio ranges, physics shapes)? | W44.2 | Mode-switched transform gizmo; toggles per system |
| Q44.2 | Day-one picking scope: geometry and light icons only, or also audio, physics proxies and gizmo handles? | W44.2 | Geometry, light icons, gizmo handles; audio and physics through richness toggles |
| Q44.3 | Are richness-level gizmos editor-only, or also a game debug overlay? | W44.2 | Editor-only first; the overlay fragment is reusable |
| Q45.1 | Asset edit policy: per-asset sessions (recommended) or a global history with save barriers? | W45.1 | Per-asset sessions |
| Q46.1 | SQLite FTS5 as a vendored platform library, or an in-house inverted index? | W46.1 | SQLite FTS5 |
| Q54.1 | Which first workflow is the acceptance scenario for the driver? | W54.1 | Import a glTF, place it, move it with a gizmo, save, reload, compare hash |
