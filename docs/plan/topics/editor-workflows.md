# Editor Workflows: Picking and Gizmos, Actions and Undo, Asset Search, Test Automation

**Systems**: S44, S45, S46, S54 (issues #23, #45, #46, #47, #50) · **Track** D · **Milestone** M2 to M4
**Status**: <span class="hg-status summary">plan</span>. Research from [UI, editor, tooling, quality](../sources/research-editor-quality.md) sections 3, 5 and 6 (all unverified) and the 2026-10-29 session notes on picking.

## Target

- **Picking and gizmos**: pick objects from the rendered scene by ray cast against per-object proxies with layers and a hit list; selection outline; transform gizmos; toggleable bounds and richness levels per system (lights, physics, audio); icons for meshless objects.
- **Actions v2**: every edit is a transaction with a name; nestable scopes; coalescing of continuous edits; multi-object and asset edits undo together; the action log is replayable and pointer-free.
- **Asset search**: a typed tag and reference registry plus a text index with a query language, incremental on file change, rebuildable.
- **Test automation in the editor**: replay recorded sessions (actions plus input), fixtures at unit, scene and workflow scope, profile capture, golden comparisons, all runnable from the editor and from CI.

## Current state (checked 2026-11-07)

- No picking, no gizmos (#23, #46, #47 open). Bounds exist in `Engine.Common` (`Bounding`) with bugs fixed in October; the old octree was dropped.
- `Editor.Action`: `ActionManager`, `ActionLog`, `ActionDispatcher`, `DelegateAction`, import actions; the `reapply` path is broken (bug 12 and 13 in the test notes); no transactions, no coalescing.
- `AssetRegistry` finds by GUID, type and URL; no tags, references or text index.
- No automation driver; no fixture scopes beyond gtest.

## Research summary (all unverified)

- Undo: Unreal's scoped transactions with `Modify()` deltas through reflection; Unity's record and collapse; Blender's memfile global undo plus mode-specific undo types; delta for frequent edits, snapshots for structural ones; asset edits need an explicit policy (barrier at save or per-asset sessions); CRDT and OT are leads only, requiring stable IDs and no pointer identity.
- Test automation: Unreal's functional tests, screenshot comparison and Gauntlet; replay with fixed step, seeded RNG and state hashes; golden tests starting with CPU artefacts, FLIP for GPU frames; noise-aware performance bands; lavapipe baselines.
- Search: Unreal's asset registry with tags from importers; Unity Search's providers and query language; SQLite FTS5 as the lowest-maintenance embedded index; watcher plus reconciliation scans.

## Guidance

### S44 Picking, selection, gizmos

- Picking by CPU ray cast over a scene query service (`query(ray | frustum, layer mask)`) backed by a flat SoA bounds array per scene first, upgraded to a dynamic AABB tree with fat boxes if the benchmark from the notes (1k to 1M boxes, churn) demands it; separate from the physics broadphase; fed like other scene systems. An ID-buffer pass is a later refinement for cutout accuracy.
- Gizmos drawn as an overlay pass in the render graph with depth options; richness levels toggled per system; light and audio icons as billboards that are pickable through the same service.
- Selection outline (#46) through a stencil or ID pass; infinite grid (#47); material preview sphere (#50).

### S45 Editor actions v2

- `Transaction { name, scope stack, deltas }` with begin, commit and abort; nested transactions merge into their parent; continuous edits (gizmo drags, sliders) coalesce by key within a transaction.
- Deltas are reflection-based record changes keyed by stable IDs (actor handle plus component path, asset GUID plus record path), never pointers; structural changes (spawn, destroy, reparent) are explicit delta kinds; archetype relocation is handled by the handle layer.
- Asset edits: per-asset sessions with their own history; saving an asset is an undo barrier for that asset only.
- The log is serialised with S01 and replayable; it is the recorder for S54. Fix the `reapply` bugs on the way.

### S46 Asset search engine

- Importers publish typed tags (type, dimensions, material slots, skeleton, references); the registry stores them and the reference graph; a text index (SQLite FTS5 as a vendored platform library, or an in-house inverted index if the dependency is refused) covers names, paths and tags; the query language mirrors the UI filters (`type:`, `ref:`, `tag:`).
- A file watcher (shared with S49) plus a reconciliation scan keep it incremental; the index lives in the project cache and is rebuildable; interactive latency is the acceptance measure.

### S54 In-editor test automation

- Driver: replays an action log (S45) and an input recording (S39) against a scene fixture with a fixed step and a deterministic scheduler mode (S59); asserts on state hashes, semantic-tree queries (S43) and golden images (S26).
- Fixture scopes: unit (pure), module (service with fakes), scene (headless world), workflow (editor UI driven); each tagged and budgeted.
- Profile capture: the trace (S04) is recorded per scenario; percentiles are compared with bands in CI.
- The editor exposes a test panel to record, run and inspect; CI runs the same driver headless.

## Done when

- An object is picked through a translucent one by cycling the hit list; a light is picked by its icon; gizmos move a selection with undo.
- A multi-object transform and an asset edit undo and redo together; the action log replays to the same state hash.
- A search for `type:material tag:emissive` over 100k assets returns within the stated latency; a renamed file is found without a rebuild.
- A recorded editor workflow (import, place, edit, save) replays in CI and fails on a deliberate regression.

## Open decisions

- ID-buffer refinement timing.
- SQLite as a vendored dependency versus an in-house index.
- Day-one picking scope and gizmo richness levels (the questions left open in the 2026-10-29 brainstorm).
