# Work: Vector Canvas and Uikit

**Systems** S42, S43 · **Issues** [#122](https://github.com/Heliogrim/Heliogrim-Engine/issues/122), [#123](https://github.com/Heliogrim/Heliogrim-Engine/issues/123); absorbed #10 to #17, #22, #25 to #37, #39, #41, #43, #44, #74 · **Track** D · **Milestone** M3 (start when S12 exists)
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Vector UI and uikit](../topics/vector-ui-uikit.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Viewport and MSDF notes (memory, 2026-10-29) | Canvas is an all-shape 2D renderer; tiled compute rationale; failure criteria (slower than today, cannot draw all elements, no quality gain); acceptance: current UI on both paths with frame times and diff; animation goals and the notification-card benchmark; backdrop effects need a backdrop pass | Brainstorm paused before design; nothing built |
| Issues #11 to #17, #26, #41 | Primitive list, icon atlas, text shaping | Become the canvas command set |
| Issues #10, #22, #39, #43, #44, #74 | Invalidation, data provisioning, contexts | S43 layout protocol and invalidation |
| Issues #25, #27 to #37 | Widget list | S43 widget set |
| Modules page layer violation | Reflow includes `GFX` and `Render.Scene` | The canvas backend absorbs the dependency |
| [Localisation work](localization.md) | Font fallback, ICU size | `TextService` is shared |
| [Editor workflows work](editor-workflows.md) S54 | Semantic tree drives tests | Defined here |

Uncommitted editor work in the engine checkout (`Editor.UI/Widget/Input/*`, `MainEditorView`) touches S43's widget set; W43.1 reviews it before planning.

## Architecture

- **Bundles**: new `Engine.Canvas` (command interface, scene encoding, animation values) with backends `Engine.Canvas.Render.Quads` (instanced SDF quads) and `Engine.Canvas.Render.Tiled` (compute binning, coarse and fine) and `Engine.Canvas.Text` (`TextService` over HarfBuzz, FreeType, Unicode algorithms; glyph caches). `Engine.Reflow` draws through `Engine.Canvas` only; `Engine.Reflow.Uikit` completes molecules and organisms; new `Engine.Reflow.Semantics` (semantic tree, UI Automation provider).
- **Provides**: 2D drawing for editor, in-game UI and world planes; shaped text; animations; widget set; semantic tree.
- **Consumes**: compute pipelines (S12), render graph fragments (S14), input contexts (S39), reflection for bindings (S09), localisation (S52).

## Code design

| Type | Contract |
|---|---|
| `CanvasCommand` | `{ Shape (box, rounded box, line, circle, arc, triangle, path), Style (fill, stroke, shadow, glow, opacity), Transform, Clip, LayerEffect (backdrop blur), TextRun, Icon }`; encoded into a per-frame command stream; no vertex buffers built by callers. |
| `CanvasBackend` | Interface over the command stream; `QuadBackend` (baseline) and `TiledBackend` (compute) selected by config; both must pass the same golden set. |
| `AnimatedValue<T>` | Curve, duration, transition; the canvas re-encodes commands per frame; ties to Reflow invalidation with repaint boundaries. |
| `TextService` | `itemise`, `shape`, `break`, `fallback`; glyph cache classes: hinted bitmap for small editor text, MSDF for large and in-world text; fonts and fallback chains from S52. |
| `IconAtlas` | #26; MSDF icons in one atlas. |
| `LayoutProtocol` | Constraints down, sizes up; explicit invalidation with repaint boundaries; stable node identity. |
| Widgets | Inputs (#27 to #36), lists and trees with virtualisation, tables, tabs, docking, dialogs, menus (#37), notifications, tooltips; built from atoms; theme tokens (#74). |
| `SemanticNode` | `{ role, name, state, actions }` per widget; feeds UI Automation, the test driver (S54), localisation tooling. |
| `Observable<T>` | #22; signal model with stability-based skipping. |

Placement: `Engine.Canvas/{CanvasCommand,CanvasBackend,AnimatedValue}`, `Engine.Canvas.Render.Quads/`, `Engine.Canvas.Render.Tiled/`, `Engine.Canvas.Text/TextService`, `Engine.Reflow.Semantics/`. Tests: canvas goldens through the GPU harness; shaping samples (Arabic, Devanagari); notification-card benchmark on both backends; 100k-row list scroll; screen reader smoke test.

## Work chunks

### W42.0 Finish the canvas brainstorm · explore · ready

- **Goal**: resume the paused brainstorm with the recorded answers: day-one primitive scope, backdrop effects, animation API, acceptance scenario; confirm the Slug licence status before any outline path; estimate ICU and HarfBuzz footprint.
- **Output**: `architecture/canvas-exploration.md`.
- **Questions**: Q42.1, Q42.2.

### W42.1 Canvas design · design · after W42.0, W12.2

- **Goal**: command interface, primitive set checked against issues #12 to #17 (Q42.2), two backends, text service, glyph caches, animation values, Reflow integration and the `GFX` dependency move.
- **Output**: `architecture/canvas-design.md`; plan (quad backend first, text service second, tiled backend third).

### W42.2 Implement canvas with the quad backend and migrate Reflow · execute · after W42.1

- **Done when**: the editor draws every widget through the canvas on the quad backend; Reflow no longer includes `GFX`.

### W42.3 Implement the text service · execute · after W42.2

- **Done when**: Arabic and Devanagari samples render correctly; small text uses hinted bitmaps, large text MSDF.

### W42.4 Implement the tiled compute backend and run the acceptance comparison · execute · after W42.2

- **Done when**: both backends render the current UI; frame times and a visual diff are recorded; the compute path ships or is closed by the failure criteria.

### W42.5 Animation values and the notification-card benchmark · execute · after W42.2

### W43.0 Review uncommitted editor widget work · explore · ready

- **Goal**: read the uncommitted `Editor.UI/Widget/Input/*` and `MainEditorView` files in the engine checkout; decide what moves into uikit and what is editor-specific.
- **Output**: a short note in `architecture/uikit-exploration.md` and a recommendation per file.

### W43.1 Uikit design · design · after W43.0, W42.1

- **Goal**: layout protocol and invalidation (#39, #43, #10: today prefetch and compute run over every widget on both axes every frame), stable identity, widget set, theming tokens, semantic tree, accessibility, data provisioning (#22).
- **Output**: `architecture/uikit-design.md`; plan grouped by issue cluster.
- **Questions**: Q43.1.

### W43.2 Implement invalidation protocol and inputs (#27 to #36) · execute · in progress (runtime core done 2026-11-19, [PR #205](https://github.com/Heliogrim/Heliogrim-Engine/pull/205) merged into `feat/wip`, `c1b79c8d`; inputs open)

- **Done when**: an unchanged frame lays out no widget (#10), render-version propagation stops early (#43), and the input widgets are uikit components.
- **Result (runtime core, 2026-11-18)**: [uikit design](../../architecture/uikit-design.md) migration step 1. Nine signed commits on `feat/reflow-runtime-core`, rebase-merged into `feat/wip` on 2026-11-19 (nine commits on `1cc9e75c`, head `c1b79c8d`); #10 and #43 closed:
    - **Subtree skipping:** an `eSubtreePending` bit lets prefetch and compute skip clean subtrees.
    - **Layout boundary:** a `BoxLayout` with absolute `min == max` on both axes stops upward propagation.
    - **Phase-typed attributes:** `ReflowPhase` lives in `Engine.Reflow`, and `AttributeOwnerLink` plus `AttributeBatch` mark the owning widget.
    - **Render-version early exit:** propagation stops at the first ancestor that already has the version. When the u16 tick wraps, every widget's versions reset, so the tree renders fully once every 2^16 ticks.
    - **Numbers (Debug, live editor):** the idle reflow tick is ~1.1 ms on the base and 60 to 90 µs on the branch, with 0 layout calls in idle frames. What remains is the O(n) ticker walk.
    - **Tests:** Engine.Reflow.Test 86 pass, 1 skip that is older than the branch.
    - **Still open:** the input widgets (#27 to #36) are not uikit components yet. Leaf writes (`get<>().update()`, `DataWatcher`) still mark by hand, which is a `shortcut:` until the step 2 bindings. Asset-browser scroll is broken on the base too (#204).

### W43.3 Implement lists, trees, tables, docking, dialogs, menus, notifications · execute · after W43.2

- **Done when**: a 100k-row asset list scrolls at full frame rate; all widget issues closed.

### W43.4 Semantic tree and UI Automation provider · execute · after W43.2

- **Done when**: a screen reader reads the main panels; a workflow test drives a dialog through the tree.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q42.1 | HarfBuzz, FreeType and ICU are acceptable text vendors, ICU with trimmed data. The design chunk records each licence (HarfBuzz old-MIT, FreeType FTL with its attribution clause or GPLv2, ICU Unicode licence) and each limitation (binary size, data trimming, platform builds) before adoption. |
| Q42.2 | Full primitive list for day one, paths last; W42.1 first checks GitHub issues #12 to #17 for what each primitive is actually needed for and trims nothing without that check. |
| Q43.1 | Semantic tree first, the Windows UI Automation provider planned as a later chunk; the design plans for it, but it is not a priority right now. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q42.1 | Is HarfBuzz plus FreeType plus ICU acceptable as vendored platform libraries for text (size estimate from W42.0)? | W42.1 | Yes; ICU reduced to break iteration data |
| Q42.2 | Day-one primitive scope: the full #12 to #17 list, or boxes, rounded boxes, lines, text and icons first? | W42.1 | Full list; paths last |
| Q43.1 | Accessibility: Windows UI Automation provider in the first release, or the semantic tree only (automation and localisation) with the provider later? | W43.1 | Semantic tree first; provider in a later chunk |
