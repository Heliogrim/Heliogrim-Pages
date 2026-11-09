# Vector UI Rendering and Uikit

**Systems**: S42, S43 (issues #11 to #17, #26, #27 to #36, #41, #10, #22, #39, #43, #44, #74) · **Track** D · **Milestone** M3
**Status**: <span class="hg-status summary">plan</span>. Research from [UI, editor, tooling, quality](../sources/research-editor-quality.md) sections 1 and 2 (all unverified). The owner's requirements for the canvas are recorded in the 2026-10-29 session notes (tiled compute, animation goals, failure criteria).

## Target

- **Canvas**: all 2D drawing (boxes, rounded boxes, lines, circles, arcs, triangles, paths, shadows, glow, translucency, icons, text) through one SDF and MSDF renderer with shaped text, usable for the editor, in-game UI and UI on planes in the world; animations of shape parameters without geometry rebuilds; a portable instanced-quad baseline and a tiled compute path measured against it.
- **Uikit**: a complete, themed, accessible widget set (inputs, lists, trees, tables, docking, dialogs, menus, notifications) on Reflow, with virtualised lists, a semantic tree for accessibility and test automation, and a state-binding story.

## Current state (checked 2026-11-07)

- `Engine.Reflow` (89 files) with attributes, schedule, theming and a Vulkan `Reflow.Render` (1.2k lines) that draws bitmap-font text as CPU-generated geometry; invalidation issues #39, #43, #44, #10; contexts #74; data provisioning #22.
- `Engine.Reflow.Uikit` (32 files): atoms (image, layouts: box, grid, flex, scroll) and themes; molecules and organisms are forward declarations only; widget issues #25, #27 to #36 open; text shaping #41; icon atlas #26.
- `Editor.UI*` builds panels on these with its own services (input, context menu #37, property).
- Reflow includes `GFX` and `Render.Scene` directly (layer violation).

## Research summary (all unverified)

- Text: SDF (Green 2007) rounds corners; MSDF (Chlumský 2015, msdfgen) restores them with overlap artefacts to preprocess; Slug (Lengyel JCGT 2017) renders from outlines; the Slug library itself is proprietary (sluglibrary.com verified on 2026-11-07: about USD 1,500 per engineer, source included) and the patent dedication to the public domain (reported effective March 2026, with MIT reference shaders on the author's GitHub) rests on search summaries only and must be confirmed before use; small body text favours hinted bitmaps, large and animated text favours distance fields.
- Vector paths: Loop-Blinn 2005; Pathfinder (inactive; "archived" not confirmed) and Vello (Linebender; README verified: the original compute `vello` crate is experimental under `research/`, `vello_gpu` is the hybrid renderer and `vello_cpu` the most mature) as design references; Skia Graphite and Flutter Impeller precompile pipelines to avoid jank.
- Shaping: HarfBuzz, FreeType, UAX #9 bidi, #14 line breaking, #29 segmentation; ICU break iterators; itemise, shape, then break.
- Frameworks: Flutter's constraints-down, sizes-up layout protocol and repaint boundaries; Slate's invalidation panels and retainer boxes; Compose's stability-based skipping; Windows UI Automation and AccessKit for accessibility; WCAG 2.2 contrast and target sizes.

## Guidance

### S42 Vector canvas

- `Engine.Canvas` below Reflow with one command interface (`draw(shape, style, transform)`, paths, text runs, clip, layer effects) and two backends behind it: instanced SDF quads (baseline, portable) and a tiled compute rasteriser (Vello-style binning, coarse and fine stages; MSDF evaluation in-shader; shape-type batching). The acceptance test from the session notes: the current editor UI on both paths with frame times and a visual diff; the compute path ships only if it wins.
- Text service: HarfBuzz plus FreeType plus the Unicode algorithms behind `TextService { itemise, shape, break, fallback }`; glyph cache per class (hinted bitmap for small editor text, MSDF for large and in-world text); localisation (S52) depends on it.
- Backdrop effects (blur, glassmorphism) need a backdrop sample pass, not an SDF; a layer effect in the command interface.
- Animation: shape and style parameters are animatable values with curves and transitions; the canvas re-encodes commands, never rebuilds vertex buffers; first animations from the notes (progress, sliding panels, colour transitions, notification cards) are the benchmark scenario.
- Reflow draws through the canvas interface only; the `GFX` dependency moves into the backend, which also lets a headless build render UI to an image for tests.

### S43 Uikit completion

- Layout protocol: constraints down, sizes up (already close to Reflow's prefetch and compute phases); explicit invalidation (#39, #43) with repaint boundaries; stable node identity for state and animation.
- Widgets: the open input issues (#27 to #36), lists and trees with virtualisation, tables, tabs, docking, dialogs, menus (#37), notifications, tooltips; molecules and organisms built from the atoms; theming through tokens (#74 contexts).
- Semantic tree: every widget exposes role, name, state and actions; it feeds a UI Automation provider, the editor test driver (S54) and the localisation tooling.
- Accessibility: contrast and focus visibility from WCAG 2.2; keyboard navigation everywhere; screen-reader exposure through the semantic tree.
- Data provisioning (#22): observable values with a signal model and stability-based skipping.

## Done when

- The editor renders every widget through the canvas; text is shaped (Arabic and Devanagari samples render correctly); the notification-card benchmark animates at the stated budget on both backends with the measured comparison recorded.
- All widget issues #25 to #36 are closed by uikit components; a 100k-row asset list scrolls at full frame rate.
- A screen reader reads the editor's main panels; a workflow test drives a dialog through the semantic tree.

## Open decisions

- Slug licence status before any outline-based text path.
- Compute path shipped or kept as research after the measurement.
- ICU dependency size (shared with S52).
