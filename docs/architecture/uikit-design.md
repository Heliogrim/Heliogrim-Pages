# Reflow and Uikit Runtime (Design)

**Status**: design accepted by the owner 2026-11-16 (second revision, same day); the phase list may be adapted during implementation. The design half of [W43.1](../plan/work/vector-ui-uikit.md): how UI is written, styled, fed with data, animated, virtualised, routed and placed in the world. Drawing (canvas, text, MSDF) stays in W42.

**Origin**: owner brainstorm of 2026-11-16, continuing the [editor UI exploration](editor-ui-exploration.md). The first revision covered authoring and data only; the owner widened it to the whole runtime and set polling as the default for data. Decisions marked **(owner)** were made in the brainstorm; **(proposed)** marks the author's calls, open to change on review. Research: section [Evidence](#evidence).

## Why

Building UI is too expensive and the runtime does too much work:

- A panel is hundreds of lines of imperative calls; attribute sets are addressed by tuple position (`std::get<0>(attr).update<attr::BoxLayout::minHeight>(…)`, where 0 means Box and 1 means Flex).
- `ReflowEngine` runs prefetch and compute over every widget on both axes every frame; only finalisation skips clean subtrees. Rendering re-records the whole window once per dirty region (`Engine.Reflow.Render/ReflowPass.cpp`).
- Themes are class-name string maps whose values are copied into widgets; one state wins at a time.
- Events bubble only, ignore clipping, and drag-and-drop calls only `drop`.
- There is no animation, no transform, no virtualisation (`TreeView` builds one widget per item), and in-scene UI is one window per scene with no placement.

## Goals

- Compose UI from uikit components by declaring a tree of widgets and attributes **(owner)**. Editor UI is C++ and compiled; project UI (HUDs, menus, launchers) is composed in the editor without code and shows changes live **(owner)**.
- Address attributes by named slot, never by access path **(owner)**.
- **Bind and forget**: a developer binds a value and never writes push, notify or invalidation code. Polling at a declared rate is the default; Reflow makes it cheap **(owner)**.
- Contexts across subtrees for theming, user state, menus and input scopes ([#74](https://github.com/Heliogrim/Heliogrim-Engine/issues/74)) **(owner)**.
- Motion: transforms, motion graphs and morphing on UI elements without large subtree invalidations **(owner)**.
- Virtualised lists, trees and grids over large data **(owner)**.
- UI rendered into the scene, with 3D interaction **(owner)**.
- A complete event model: hover, drag-and-drop, context actions **(owner)**.
- Unchanged UI costs nothing per frame; work scales with what changed and what is visible.

## Anti-goals: the React problems

The owner's list of what fails in React at enterprise scale, and the rule in this design that prevents each **(owner list, rules proposed)**:

| Problem | Rule here |
|---------|-----------|
| Big data updates invalidate massive trees | Components build once; nothing re-renders. A change reaches only the attributes that read it (section 4) |
| Memoisation everywhere | Not needed: there is no re-render to skip. Derived values are cached by their inputs automatically |
| Contexts invalidate too many elements | Contexts hold cells, and readers subscribe to the field they read, not the context (section 5) |
| Contexts are hard to track | Every context read is recorded; the inspector shows provider, readers and changes (section 11) |
| Piping data between external state and the UI | Sources adapt external state in place (polled, versioned) without copying it into a UI store (section 4) |
| Imprecise invalidation | Each attribute declares the phase it affects; a change marks only that phase (section 1) |
| Massive numbers of widgets | Virtualisation by extent, so only visible items exist; layout skips clean subtrees (sections 1, 7) |
| Value vs reference identity | Identity is an explicit `key`; equality decides change. Re-creating an equal object changes nothing (section 4) |
| Transition handling | Mount, unmount and layout transitions are part of the runtime, not user code (section 8) |
| Background rendering | Hidden and off-screen surfaces do no work; expensive derivations run as scheduler tasks and land at the evaluation point (section 10) |
| Virtualised lists show empty space while scrolling | Placeholders of the predicted size, a per-frame materialisation budget and overscan (section 7) |
| Type safety | Typed slots, typed sources, typed payloads; an invalid slot or binding fails to compile |
| Data piping across the application (RxJS-style) | Typed pipe operators over sources (section 4) |

Also anti-goals: two UI systems (editor and project UI share everything), and uikit components that hard-code the Heliogrim identity (the editor's look is its theme).

## Constraints

- C++23 on clang-cl and MSVC, no modules. Designated initialisers carry the declarative syntax.
- UI reads engine state at one point in the frame: the reflow stage, ordered by the task graph after every stage that writes scene and actor state. When a render replica exists ([engine loop 5.2a](engine-loop-exploration.md)), reads move there; the interfaces do not change.
- `Engine.Reflect` knows type identity only, not fields. Schemas and source paths are registered explicitly until S09 reflection exists.
- Performance gates (accepted by the owner, 2026-11-16): idle editor UI under 0.3 ms CPU per frame; no heap allocation per frame in steady state; one transform change costs work proportional to visible rows, not scene size. A recompile target was dropped **(owner)**.

## Design

### 1. Phases and invalidation

Each frame, the reflow stage runs these phases per surface, and each has its own dirty flag **(proposed)**:

| Phase | Work | Dirtied by |
|-------|------|-----------|
| Bind | Evaluate due bindings, advance animations | Time, rates, signals |
| Structure | Mount or unmount children (`ForEach`, `Show`, virtualised windows) | Keyed collection changes |
| Layout | Constraints down, sizes up | Layout attributes: sizes, padding, gap, flex, font size |
| Paint | Record draw commands | Paint attributes: colour, border, image, text content without size change |
| Compose | Apply transform, opacity, clip and effects to recorded layers | Transform channels |

Rules:

- **Every attribute declares its phase** in its type. Setting it marks that phase on the widget; nobody calls `markAsPending` by hand. Theme and token changes mark layout when they change spacing or size tokens and paint when they change only colours; today every theme change marks layout because paddings and gaps can change **(owner)**, and that stays the conservative fallback.
- **Layout skips clean subtrees.** A node whose constraints are unchanged and whose subtree is clean reuses its cached size (#10). A **layout boundary** (a node with a fixed or externally determined size, such as a panel, a list cell of fixed extent or a scroll viewport) stops propagation upward.
- **Paint is cached per repaint boundary.** Panels, list items and animated layers record into their own command lists; only dirty boundaries re-record. Render-version propagation stops at the first ancestor already marked (#43).
- **Compose never touches layout or paint.** Moving, scaling, fading or clipping a boundary re-composes cached commands.

Done when an unchanged frame lays out no widget and records no command; this is W43.2's acceptance.

### 2. Attributes

Keep the named slot (`NamedAttribute<"minHeight", T>`) and its compile-time lookup **(owner)**; remove the positional grouping **(proposed)**:

- A component's attribute set is **one flat named set**, composed from reusable groups (Box, Flex, Text, Paint). The group is an implementation detail: `widget.set<attr::minHeight>(36)` and `Button { .minHeight = 36 }` work without knowing which group holds the slot. Duplicate names across groups fail to compile.
- Each slot carries: value type, default, phase (section 1), whether it can be animated, and an equality.
- The registered schema per component (slot name, type, default, phase, member pointer into the builder aggregate) drives the composer's property panel, serialisation of project UI and the inspector. It is declared once, next to the builder.

### 3. Style

A slot's value resolves through a cascade, last wins **(proposed)**:

1. **Tokens**: palette, spacing, radii, type scale, motion durations and curves. The editor's tokens are the [brand identity](../guides/brand-identity.md); a project brings its own.
2. **Component style**: which tokens a component uses.
3. **Variant**: `primary`, `danger`, `compact`.
4. **States**: hover, pressed, focused, selected, dragging, disabled. **States combine** with a fixed precedence per slot (disabled overrides hover; selected and hover can both apply) instead of today's single winner.
5. **Context overrides**: a subtree can override tokens (a dense table, a warning banner).
6. **Instance override**: sparse slots on one node.
7. **Binding or animation**: a bound or animated slot sits on top.

Style keys are typed slots, not class-name strings. Resolved values are computed and cached per (component, variant, state set, context override version); widgets do not copy theme values into themselves. Switching theme invalidates the cache, and the phase rule in section 1 decides what gets marked.

### 4. Data: sources and bindings

Every bound slot reads a `Source<T>`. **Polling is the default** **(owner)**; Reflow keeps it cheap:

| Adapter | When the value is read | Use |
|---------|------------------------|-----|
| `poll(fn, rate)` (default) | At a declared rate (every frame, 30 Hz, 4 Hz, 1 Hz); default rate per slot kind | Anything; no cooperation from the owner of the data |
| `Versioned<T>` (fast path) | When a change counter moved | Systems that already count changes (scene, assets) |
| `Signal<T>` (fast path) | When set | UI state, editor models |
| `computed(fn, inputs…)` | When an input changed | Derived values; cached, so no manual memoisation |

What keeps polling cheap **(proposed)**:

- **Only visible bindings are evaluated**: not in a collapsed panel, a background tab, a hidden window or outside a virtualised window. Resuming reads once.
- **Equality gate before invalidation**: a polled value that compares equal marks nothing. Identity is never compared by address; a re-created equal value is "unchanged".
- **Phase-precise**: a changed value marks only the phase of the slot it feeds.
- **Spread over frames**: due bindings with the same rate are distributed across frames, so a 4 Hz group does not spike one frame.
- **Measured**: the inspector shows each binding's rate, cost and change frequency, so a hot binding can be moved to a fast path when it matters.

**Pipes**: typed operators over sources, in the spirit of RxJS but evaluated inside the bind phase: `map`, `filter`, `combine`, `distinct`, `throttle`, `debounce`, `format`. Example: `bind(poll(&Queue::size, 4_hz) | map(percentOf(capacity)) | format("{:.0f} %"))`.

**Collections**: a list binds to a `ListSource<T>` that exposes `count()`, `key(i)`, `item(i)` and a version, and optionally change ranges (inserted, removed, moved, changed). Large data is never copied into the UI. Without change ranges, only the visible window is diffed by key.

**Project UI** names sources by path (`"player.health"`). Projects expose sources explicitly (`exposeSource(path, source)`) until reflection exists; unresolved paths are diagnostics at mount.

`DataWatcher` becomes the polling scheduler; `Editor.UI.Rx` subjects map onto `Signal`.

### 5. Contexts

A context is a typed value provided to a subtree ([#74](https://github.com/Heliogrim/Heliogrim-Engine/issues/74)) **(proposed)**:

- A provider holds **cells**, not values. A reader reads a field through the context and subscribes to that field only; changing another field notifies nobody.
- Nearest-provider lookup is resolved at mount and cached per widget; moving a widget re-resolves it. No subtree walk on change.
- `staticContext` for values that never change after mount (the window, the services); reads are free and untracked.
- Theming, the context-menu scope, input and shortcut scopes, and selection become tree contexts instead of global services with focus push and pop.
- Every read is recorded with its reader, so the inspector can answer "who reads this, who provides it, what changed".

### 6. Structure, identity, authoring

As in the first revision **(owner agreed)**:

- One **description tree** produced by C++ builders (editor) and by assets (project UI). Mounting turns it into widgets. Components build **once**; dynamic parts come only from structural nodes and bindings.
- Structural nodes: `ForEach(source, key, item)`, `Show(source, node)`, `Switch`. They reconcile by key and mount only what changed.
- Addressing: `.ref = &slot` (typed handle, C++), `.name` plus `find<T>(name)` (assets, tests), `.key` (identity in lists, keeps state and animations alive).
- In assets, handlers are action ids and bindings are source paths; in C++, either a callable or an id.

```cpp
auto sceneHierarchy(ref<SceneHierarchyModel> model_) -> Desc {
    return Island { .title = "Scene" } (
        SearchField { .placeholder = "Filter…", .value = bind(model_.filter) },
        TreeView {
            .items   = model_.visibleNodes,                 // ListSource<SceneNode>
            .extent  = Extent::fixed(22),
            .item    = [](ref<const SceneNode> node_) {
                return TreeRow { .icon = iconFor(node_), .label = bind(node_.name) };
            },
            .context = ActionContext::SceneSelection,
            .drop    = DropTarget<AssetRef> { .onDrop = placeIntoScene },
            .ref     = &model_.treeRef
        }
    );
}
```

### 7. Virtualisation

Lists, trees (flattened), tile grids and tables share one virtualiser **(proposed)**:

- **Anchor**: first visible item index plus pixel offset. Scroll position never depends on knowing every item's size.
- **Extent modes**: `fixed(px)` (offset is index × extent), `perIndex(fn)` (prefix sums, rebuilt when the version moves), `estimated(px)` (measured sizes cached by key; when a measurement differs, the anchor is kept and positions below it shift, so content under the cursor does not jump). Grids: fixed cell size and column count from width.
- **Materialisation**: an overscan window above and below; widgets are pooled by item type and rebound to new items, with item state kept by key, not on the pooled widget.
- **No empty space**: if more items enter the window than the per-frame budget can build, the rest are drawn as placeholders of their predicted extent and built over the next frames, nearest to the viewport first.
- Only materialised items have bindings, layout and paint; a million-row source costs as much as the visible rows.

### 8. Animation and motion

**(proposed)**:

- **Animated values**: any slot marked animatable can be driven by a timeline (duration, curve from tokens) or a spring. An animation marks only its slot's phase each frame.
- **Transform and opacity channels**: every repaint boundary has translate, scale, rotate, skew, opacity and clip channels applied in compose. Animating them never touches layout or paint; hit testing uses the same transform (section 9).
- **Layout transitions** (a panel resizing, a list reordering, an element moving to another parent): the runtime lays out the target state once, then animates each moved boundary's transform from its old to its new rectangle (FLIP), with scale correction for children, corner radii and borders. One layout, not one per frame.
- **Morphing and shared elements**: two elements with the same transition key across a structure change (an asset tile opening into a tab, a toast collapsing into the status bar) animate between their rectangles and styles.
- **Enter and exit**: `ForEach` and `Show` keep an unmounting child alive until its exit animation finishes; enter animations start from a declared state.
- **Motion graphs**: a component can declare named states and transitions (state machine), each transition with its channels and curves; inputs are bindings or events. The same graph format serves editor and project UI.
- Animations advance in the bind phase with the frame time and stop costing anything when settled.

### 9. Events and input

**(proposed)**:

- **Hit path**: computed once per pointer event from the root, respecting clip rectangles and inverting each boundary's transform. World panels (section 10) enter the same path after a ray hit.
- **Routing**: tunnel from root to target, then bubble back. A handler returns a reply as data: `handled`, `capture pointer`, `release capture`, `focus`, `begin drag`. The router applies replies; handlers never mutate routing state.
- **Pointer capture** keeps events with the capturing widget during drags and slider scrubs.
- **Hover, pressed, focused** are states set by the router; visuals come from style (section 3), cursor shape from the component default with instance override. `onHover` is for behaviour only.
- **Drag and drop**: drag starts after a distance threshold. `DragSource<T>` declares payload and preview; `DropTarget<T>` declares `accept` (payload and position: into, before, after), `onEnter`, `onOver`, `onLeave`, `onDrop` and feedback. Only targets whose `T` matches are asked. Payloads are values, so drags work across OS windows.
- **Focus and keyboard**: a focus scope per surface, tab order from structure with overrides, arrow-key navigation inside lists and grids, focus ring from style.
- **Actions**: one registry feeds context menus, the Ctrl K palette, toolbars and shortcuts. A widget declares `ActionContext`; menus are built from the actions of the contexts on the hit path. Execution and undo belong to [Actions v2 (W45.1)](../plan/work/editor-workflows.md); key routing to the input work (S39).

### 10. Surfaces, in-scene UI and background work

**(proposed)**:

- A **surface** hosts one UI tree: an OS window, an overlay on a viewport, or a **world panel**. A scene can hold any number of world panels (today: one `UISceneModel`, first one wins).
- A world panel has a transform in the scene, a size in panel pixels and a pixels-per-unit. Two draw modes: **direct** (UI commands drawn in the scene pass, depth-tested; sharp and lit consistently) and **texture** (rendered to a texture and cached; for screens and distant panels that change rarely).
- **Input**: a ray from the cursor, a controller or a VR pointer hits the panel's plane, converts to panel pixels and enters the normal router (section 9). Focus and capture work the same.
- **Background work**: surfaces that are hidden, minimised or out of view skip all phases. `computed` sources marked expensive run as scheduler tasks and publish their result at the next bind phase. Per-frame budgets apply to materialisation, structure changes and texture panel refresh.

### 11. Tooling

**(proposed)**: an inspector panel (editor) and overlay showing per surface: phases run and their cost, dirty boundaries flashing, bindings with rate and change frequency, context providers and readers, and virtualiser windows. It answers "why did this update" without a debugger.

## Settled after the builder check (2026-11-16)

A reviewer read this revision as a builder would. Answered from the brainstorm: OS file drops into the editor already exist and stay (the owner imports assets by dragging files in). Calls made by the author, for review:

| Gap | Call |
|-----|------|
| Paint caching and compose on today's flat vertex buffer would be thrown away by the canvas | Migration step 1 covers layout only (#10, #43, layout boundaries, phase-typed attributes). Paint caching per boundary and compose channels arrive with or after the canvas (W42.2); until then a changed boundary repaints its region as today |
| Recording happens in `ReflowPass` on the render side, reading the live tree | Paint records in the reflow stage into per-boundary command lists, double-buffered and handed to the render pass, which reads lists only and never the widget tree. This lands with the canvas; until then today's split stays |
| Polled sources read arbitrary engine state, but the task graph relaxes order by declared access | The reflow stage declares that it reads all engine state and stays ordered after every writer. Per-source access keys are a later refinement, if the measured cost of that ordering matters |
| Live editing of project UI: re-mount or in-place patch | Re-mount the edited subtree. Keyed state (expansion, scroll, selection) lives in a per-surface store keyed by path and `key`, not in widgets, so it survives re-mounts; running animations restart |
| Drag across "OS windows" | Between engine windows: in scope (step 3). Into the editor from the OS (file drops): kept, routed as a `DragSource<FileList>` from outside. Out to other applications: later; payload types then need an external format |

## Migration

1. **Runtime core** (W43.2): phase flags and phase-typed attributes, layout skipping and layout boundaries (#10), render-version early exit (#43). Existing widgets keep working; their attributes get phases. Paint caching and compose follow the canvas (see above).
2. **Authoring and data**: flat named attribute sets, the cascade (with an adapter so existing atoms read resolved styles), description tree and mount, sources with polling and pipes, contexts, the action registry; scene hierarchy rewritten as the proof.
3. **Events**: hit path with clip and transforms, tunnel and bubble, replies, full drag and drop.
4. **Virtualisation and animation**: virtualiser with the asset browser and hierarchy; channels, timelines, FLIP layout transitions, enter and exit.
5. **Surfaces**: in-game overlays and world panels in texture mode with ray input; then the asset form of descriptions and the project-UI composer (after S01 serialisation); direct drawing in the scene pass last.

Each step lands on today's Reflow drawing; the canvas (W42.2) replaces drawing underneath without changing this layer.

## Evidence

Research of 2026-11-16, primary sources where marked; the full notes are in the session record and should move to `sources/` with the next revision.

- Unreal Slate's architecture tenets prefer polling for developer time ("A programmer's time is expensive; CPUs are fast and cheap", [Slate architecture](https://dev.epicgames.com/documentation/en-us/unreal-engine/understanding-the-slate-ui-architecture-in-unreal-engine)); UMG's optimisation guide warns that bound attributes poll every frame ([UMG optimisation](https://dev.epicgames.com/documentation/en-us/unreal-engine/optimization-guidelines-for-umg-in-unreal-engine)); Epic later added invalidation boxes, global invalidation and the MVVM viewmodel plugin ([invalidation](https://dev.epicgames.com/documentation/en-us/unreal-engine/invalidation-in-slate-and-umg-for-unreal-engine), [viewmodel](https://dev.epicgames.com/documentation/en-us/unreal-engine/umg-viewmodel-for-unreal-engine)). This design keeps polling as the developer default and puts the invalidation work inside the runtime. The owner's phrasing "compute is cheap, game dev time is not" was not found verbatim.
- React re-renders every context consumer on change, and `memo` does not prevent it ([useContext](https://react.dev/reference/react/useContext)). Fine-grained signals (Solid, Preact, Angular) and Compose's tracked `CompositionLocal` subscribe at the read site ([Solid](https://docs.solidjs.com/concepts/intro-to-reactivity), [Compose locals](https://developer.android.com/develop/ui/compose/compositionlocal)).
- Compose tracks reads per phase, so a read in placement or draw does not recompose ([Compose phases](https://developer.android.com/develop/ui/compose/phases)); FLIP and Motion layout animations solve layout once and interpolate transforms ([FLIP](https://aerotwist.com/blog/flip-your-animations/), [Motion](https://motion.dev/docs/react-layout-animations)); Flutter's `RepaintBoundary` caches subtrees ([Flutter](https://api.flutter.dev/flutter/widgets/RepaintBoundary-class.html)).
- Virtualisation: Flutter's `itemExtent` and dead reckoning with scroll correction ([ListView](https://api.flutter.dev/flutter/widgets/ListView-class.html), [RenderSliverList](https://api.flutter.dev/flutter/rendering/RenderSliverList-class.html)); Compose's index plus offset anchor ([lists](https://developer.android.com/develop/ui/compose/lists)); WPF's recycling pitfalls ([WPF](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/advanced/optimizing-performance-controls)).
- Events: WPF tunnel and bubble ([routed events](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/events/routed-events-overview)), Slate's `FReply` as data ([FReply](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/SlateCore/FReply)), Flutter hit testing through inverse paint transforms ([hit test](https://api.flutter.dev/flutter/rendering/BoxHitTestResult/addWithPaintTransform.html)).
- World UI: Unreal's widget component and interaction component ([widget interaction](https://dev.epicgames.com/documentation/en-us/unreal-engine/umg-widget-interaction-components-in-unreal-engine)), Unity's world-space UI Toolkit ([Unity](https://docs.unity3d.com/6000.2/Documentation/Manual/ui-systems/create-world-space-ui.html)). No primary measurement of direct versus texture cost was found.

## Out of scope

The canvas, text shaping and MSDF (W42); the widget catalogue (W43.3); the semantic tree and accessibility (W43.4, Q43.1); the project-UI composer tool; editor shell layout, docking and tabs; the design guide's component specs.

## Left to the builder

- Builder mechanics, as long as the example in section 6 reads about that way.
- Storage of descriptions, mounted state, subscriptions and caches.
- Default polling rates per slot kind, and the spreading scheme.
- Asset format for descriptions (follow S01).
- The motion-graph file format.

## Owner decisions (2026-11-16)

| Question | Decision |
|----------|----------|
| Phases as in section 1, attributes typed by phase | Agreed; adapt the phase list if implementation shows a need |
| Migration order | Agreed |
| Surfaces and world panels | Editor UI rendering comes first: the UI is the primary surface and the game is a viewport inside it. In-game use of Reflow (overlays and world panels) starts with **texture mode only**: the UI renders to an intermediate texture that the scene samples. Direct drawing in the scene pass is a later step |
