# Editor UI and UX (Exploration)

**Status**: exploration. Nothing here is decided except the brand identity, which the owner accepted on 2026-11-16 and which lives in [Brand identity](../guides/brand-identity.md). The layout and interaction notes below are owner preferences from the same brainstorm, not a design yet. Accepted parts move to a design page and, where needed, an ADR.

**Origin**: owner brainstorm of 2026-11-16 (engine session, visual companion mockups). The editor is the test bench for engine work, and building its UI is too expensive: every view is hand-assembled in C++, there are no reusable parts, no design guide and no SDF rendering. The brainstorm paused before the question of how UI gets written; that and the work-package split are open.

## Why

The editor is used today to check:

- that the renderer still works after shader-toolchain changes: a populated scene with light and shadows and a free camera,
- that asset imports progress: started with buttons and drag-and-drop, followed in the log,
- that assets still load.

The hand-written UI does this. What fails is the way UI is made: maintenance cost, writing complexity, missing SDF/MSDF, no design guide, no ready-made elements, and therefore no design or UX iteration.

## Current state in the engine (checked 2026-11-16, `feat/async-storage`)

- **Construction** is imperative C++. `initEditor` (`Editor.UI.Init/EditorInit.cpp`) builds a reflow window and calls `initDefaultUi`. The layout is a chain of lambdas in `Editor.UI.View/Scene/SceneEditorView.cpp` (168 lines) placing cards from MVC panel triples in `Editor.UI.Panel` (asset browser view 412 lines, scene hierarchy 368, properties 82). About 1.1k lines of hand-written construction in total, all of it attribute calls of the form `update<attr::BoxLayout::minHeight>({eAbsolute, 36.F})`.
- **The editor does not build at HEAD of the branch without uncommitted changes**: `EditorInit.cpp:40` calls `initDefaultUi`, whose definition exists only in the working tree. This matches the W26.2 note that `Heliogrim-Editor` does not build on `feat/wip`. The working tree also holds throwaway parts (a context-menu experiment, 640×480 window, an `n` key spawning debug actors) and a default-font GUID change.
- **Widget graph**: `Engine.Reflow` (about 8.7k lines) with `Widget`, `CompoundWidget`, `LeafWidget`, a layout protocol of virtuals (`prefetchSizing`, `computeSizing`, `applyLayout`, `render(ReflowCommandBuffer*)`) driven by `ReflowEngine`, and events in `Engine.Reflow/Event`. 73 TODO, FIXME or Temporary markers across `Reflow*` and `Editor.UI*`.
- **Uikit**: `Engine.Reflow.Uikit` (about 4k lines) holds atoms (Text, Paint, Image, box layouts, ThemeProvider), two molecules (Stack, VScrollBox), an empty organism folder, and `makeButton` and `makeCard` factories. Editor-level widgets (Breadcrumb, Collapse, Menu, the Input family) live in `Editor.UI/Widget`.
- **Theming**: `Theme` maps class-name strings to attribute sets. The only tokens are a 7-colour palette and semantic colours in `Editor.UI.Theme/EditorTheme.cpp`. Spacing, type scale and radii are hard-coded at call sites.
- **Text and shapes**: FreeType bitmap atlas per pixel size; the command buffer emits CPU-built geometry (lines, triangles, quads, arcs, text, images). MSDF is scaffolding only: empty sub-pass slots, `makeUiMsdfEffect()` returns `nullptr`, no msdfgen. No rounded-rect or SDF primitives.
- **No declarative form**: no markup or data files; `MenuBuilder` and the two factories are the only builders.

## Owner preferences (2026-11-16)

Mockups, self-contained HTML: [layout](../assets/editor-ui/layout-v2.html), [interaction](../assets/editor-ui/interaction-v3.html), [in-place tools and menu density](../assets/editor-ui/inplace-v4.html). The identity preview is under [Brand identity](../guides/brand-identity.md).

**Shell**

- Header bar: File, Edit, Actions, View, Settings; an all-action search in the middle on a shortcut (Ctrl K) that finds actions, assets and scene objects; play.
- Document tabs: each open asset is a tab with its own editor, tools and quick actions; tabs tear out into separate OS windows (material preview on a second screen, a graph debugger next to the running scene). Double-click opens or focuses; create from the asset browser's Create menu, the tab bar's `+`, or the search.
- Panels are islands on a dark base, in the JetBrains island style; collapsed panels become quiet edge strips. Users can dock, collapse and float every panel. Default: hierarchy left (collapsible), viewport centre, properties right, asset browser bottom.
- Status footer for long-running work, plus toasts for save, asset build, shader compilation and imports.
- No mode rail on the left (rejected).

**Content**

- Asset browser: breadcrumb in the header, a type and tag filter tree on the left, text search with filters (`t:Material weave`).
- Asset tiles: portrait, preview on the tile colour (transparent background), a type icon bottom left, quick-edit or lock top right, one ellipsized title row; hover shows a card with type, path, size, users, modified and tags. Folders use the same tile. Previews come from a preview service that renders on demand and caches.
- Filters and search on content panels (hierarchy, asset browser, later skeletons and animation).

**Feel**

- Clean and modern; room to breathe but dense enough to avoid scrolling; good contrast; nesting levels visible where intended.
- Hover is a quiet background lift (about 120 ms). Cursor changes per element: pointer on buttons, tabs and tiles, I-beam in text fields, horizontal scrub on number fields, resize on splitters, grab on tab and panel headers, not-allowed when disabled.
- Context menus in the HeroUI direction at the v4 density: 26 px rows, 4 px padding, 10 px outer and 6 px item radius, icon, label and shortcut, destructive item in red.

**In-scene editing**

- Things that live in the scene (landscape first) are edited in place in the scene tab, not in their own tab. Selecting and entering edit swaps the viewport toolbar and the properties panel; Esc leaves.
- Landscape toolbar: grouped icon buttons with tooltips: Shape (sculpt, smooth, flatten, ramp, erosion, holes), Surface (texture layers; painting counts as texturing), Populate (foliage brush, place asset, erase).
- Foliage and procedural placement need their own work: placement lists with parameters, placement groups, chance and random sets, and custom rules as node graphs.

**Other editors named**: modelling, sculpting, texturing, skeleton animation, sequencer, node graphs for programming, materials, textures, videos, sounds, SFX mixers. Audio needs live graphs (attenuation while placing sounds), clip markers, and frequency views for multi-band compressors and equalisers.

## Fit with existing work

| Owner need | Existing chunk | Note |
|------------|----------------|------|
| SDF/MSDF shapes and text | [W42.0 to W42.3](../plan/work/vector-ui-uikit.md) | W42.0 brainstorm ready; canvas replaces today's command-buffer geometry |
| "Reflow command buffer revision" | W42.2 | Canvas with quad backend; Reflow stops including `GFX` |
| Widget graph refinement | W43.1, W43.2 | Layout protocol, invalidation, identity, theme tokens |
| Reusable elements | W43.0, W43.2, W43.3 | Inputs, lists, trees, docking, menus, notifications |
| Editor as test bench | [W54.1, W54.2](../plan/work/editor-workflows.md) | Automated; does not cover a stable manual bench now |

**Not covered by any chunk**: a stable editor bench now (the build break above), the design guide and prototypes (identity is done; tokens, components and patterns are not), UX flow (shell, tabs, windows, docking beyond one line in W43.3), and the cost of writing UI (no declarative form or builder layer).

## Proposed split (not agreed)

1. **Bench now**: commit a clean `initDefaultUi` without the throwaway parts so the editor builds; no new UI.
2. **Design guide and prototypes**: tokens (spacing, radii, type scale, palette from the identity), component specs (tile, menu, toast, toolbar, tabs, island, hover card) and UX flows, iterated as browser prototypes. Needs no canvas, so it can start now and gives W42.1 and W43.1 concrete targets.
3. **Existing W42 and W43 chain**, fed by step 2.

## Decisions needed

| Question | Owner |
|----------|-------|
| How should UI be written: C++ builder layer, declarative files, or authored in the editor itself? (asked when the brainstorm paused) | Owner |
| Editor font: IBM Plex Sans (matches the site) or Inter | Owner |
| UI icon set: Lucide, Tabler or Phosphor | Owner |
| Is the three-step split right, and which chunk ids do the new steps get? | Owner |
| Which scene content is edited in place beyond landscape and foliage (splines, volumes, nav areas)? | Owner |
