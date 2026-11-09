# Research: UI, editor, tooling, quality

**Status**: <span class="hg-status summary">sources</span>. Collected 2026-11-07 by a research agent for the battle plan. Claims are marked verified or unverified; nothing here is a decision.

## Method caveat (read first)

The first pass fetched nothing. A second pass on 2026-11-07 (see "Verification pass" at the end) opened primary pages where reachable. Body text below is still the first-pass prose; where the pass contradicted or sharpened it, the claim is corrected inline, otherwise the marker alone changed. Table rows keep their marker; the per-source status in the final section is authoritative. Numbers (perf, ratios) are still omitted. Several doc sites (Epic, ACM, Microsoft pseudo-localization) returned empty or blocked pages; those stay `[U]`. No forum/Reddit-only claims are used.

Marker legend: `[V-full]` = full page text opened. `[V-abs]` = abstract/landing page opened. `[S]` = only corroborated via web-search result summaries, page itself not opened (treat as likely, re-open before citing). `[U]` = unverified (reason given).

---

## 1. Vector UI rendering and text

### Summary
- SDF text: Green (Valve) showed a single-channel distance field sampled bilinearly with an alpha threshold gives sharp magnification from low-res textures. Weakness: rounds sharp corners. `[U]`
- MSDF: Chlumsky's thesis encodes three channels with per-edge-colour distances; the median of three restores corners. msdfgen is the reference implementation; msdf-atlas-gen builds atlases. Known artefacts at self-intersections/overlaps; needs contour preprocessing. `[U]`
- Loop-Blinn: render quadratic/cubic Bezier regions as triangles with implicit-function pixel shader tests; needs triangulation and cubic classification; no native high-quality AA without extra work. `[U]`
- Slug (Lengyel, JCGT 2017): evaluates winding coverage per pixel directly from glyph outline curves stored in textures, with band acceleration; no atlas of rasterised glyphs, resolution independent. Licence/patent (corrected): the Slug *Library* (sluglibrary.com) is still a proprietary commercial product, static lib with full source per licence, $1500 single-engineer licence, company pricing on request; that page says nothing about patents. `[V-full]` Separately, Lengyel's blog "A Decade of Slug" (terathon.com/blog/decade-slug.html) reportedly dedicates US patent 10,373,352 to the public domain effective 2026-03-17 and publishes reference vertex/pixel shaders (dynamic dilation, improved pixel shader) under MIT at github.com/EricLengyel/Slug, credit required in distributed software. `[S]` (blog/repo not opened; confirm before relying on it). The algorithm is therefore free to implement; the library licence is not what frees it.
- Pathfinder (Mozilla/Servo, P. Walton): GPU tile-based rasteriser for fonts and SVG paths, versions v1-v3. Corrected: the GitHub page shows no archived banner (1,752 commits, dual Apache-2.0/MIT, "Pathfinder 3", README says "under heavy development and is incomplete"); activity recency not visible, so "inactive" is unconfirmed. Modes: compute "D3D11" and hardware "D3D9". `[V-full]`
- Vello (Linebender, Raph Levien): compute-shader 2D renderer; scene encoding, parallel prefix-sum style stages, per-tile command lists (binning, coarse, fine raster). Corrected from README: the repo now hosts three renderers; the original compute-centric `vello` is "experimental" for compute-capable GPUs and lives under `research/`; `vello_cpu` (multithreaded, SIMD) is "the most mature choice"; the GPU hybrid renderer is `vello_gpu` (CPU path preprocessing, GPU raster/composite, WebGL2 and wgpu backends without compute), both on a "Sparse Strips architecture" (`vello_common`); Apache-2.0/MIT. The README does not describe binning/coarse/fine stages (deferred to ARCHITECTURE.md, not opened). `[V-full]` Primary doc is repo docs plus Levien's writing and thesis work (author blog, treat as secondary). Needs compute, robust sub-group/atomic behaviour, so driver variance is the main risk. `[U]`
- Skia Ganesh (older GPU backend, immediate pipeline per draw) vs Graphite (newer, explicit Vulkan/Metal/Dawn-oriented, pre-compiled pipelines, recording/painter's-order with depth). Impeller (Flutter): precompiled shaders to avoid runtime jank, tessellation on CPU for paths with analytic fallbacks. `[U]`
- Tiled compute rasterisation: split into tiles, bin path segments per tile, accumulate coverage per tile; trade off complexity vs fixed-function MSAA paths. Lead for further reading: Li et al., "GPU-accelerated path rendering" (Kilgard & Bolz, SIGGRAPH Asia 2012, NV_path_rendering "stencil then cover"). `[U]`
- Shaping/layout: HarfBuzz does shaping (OpenType GSUB/GPOS), FreeType does outline loading/hinting/rasterisation, UAX #9 bidi, UAX #14 line breaking, UAX #29 grapheme/word segmentation, UAX #24 scripts. Segmentation order: itemise by script/bidi level/font, then shape, then break. ICU provides break iterators; alternatives: unicode-bidi / SheenBidi, libunibreak. `[U]`
- Glyph cache choices: bitmap atlas per size (crisp, hinted, memory per size), SDF/MSDF atlas (one size, scalable, soft small sizes), direct outline (Slug-like; most scalable, higher per-pixel cost). Small body text generally favours hinted bitmap/LCD; large/animated/3D favours distance fields or direct outlines. `[U]`

### Key sources
| Title | Authors/org | Venue, year | URL | Measured | Status |
|---|---|---|---|---|---|
| Improved Alpha-Tested Magnification for Vector Textures and Special Effects | C. Green, Valve | SIGGRAPH 2007 course notes | https://steamcdn-a.akamaihd.net/apps/valve/2007/SIGGRAPH2007_AlphaTestedMagnification.pdf | quality of magnified 64x64 fields | `[U]` |
| Shape Decomposition for Multi-channel Distance Fields | V. Chlumsky | MSc thesis, CTU Prague, 2015 | https://github.com/Chlumsky/msdfgen (MIT; thesis at github.com/Chlumsky/msdfgen/files/3050967/thesis.pdf; msdf-atlas-gen companion) | corner fidelity vs SDF | `[V-full]` |
| GPU-Centered Font Rendering Directly from Glyph Outlines | E. Lengyel | JCGT 6(2), 2017 | https://jcgt.org/published/0006/02/02/ (JCGT 6(2), pp. 31-47, June 2017; fetch returned empty, details via search) | pixel shader coverage, texture footprint | `[S]` |
| Resolution Independent Curve Rendering using Programmable Graphics Hardware | C. Loop, J. Blinn | ACM TOG 24(3) / SIGGRAPH 2005 | https://dl.acm.org/doi/10.1145/1073204.1073303 | curve-in-triangle approach | `[U]` |
| Pathfinder | P. Walton / Mozilla Servo | GitHub, 2016-2019 | https://github.com/servo/pathfinder | GPU tile rasteriser | `[V-full]` |
| Vello | Linebender | GitHub docs, 2022-2026 | https://github.com/linebender/vello | compute + sparse-strips renderers | `[V-full]` |
| Skia Graphite / Ganesh | Google | skia.org docs | https://skia.org/docs/ | backend architecture | `[U]` |
| Impeller | Flutter team | docs.flutter.dev | https://docs.flutter.dev/perf/impeller | jank elimination via precompiled shaders | `[U]` |
| Unicode UAX #9, #14, #29 | Unicode Consortium | standards, current | https://www.unicode.org/reports/tr9/ , /tr14/ , /tr29/ | normative algorithms | `[U]` |
| HarfBuzz manual; FreeType docs | HarfBuzz / FreeType projects | docs | https://harfbuzz.github.io/ ; https://freetype.org/freetype2/docs/ | API | `[U]` |

### Applicability to Heliogrim
- A hybrid is the likely target: MSDF atlas for icons/large labels/in-world UI, bitmap or direct outline for small editor text, a path renderer for vector widgets. Decide per primitive class, not globally.
- Reflow's Vulkan renderer can reuse its own draw lists; a compute path (Vello-like) is a later tier gated on measured need.
- Shaping stack should be HarfBuzz + FreeType + ICU/UAX libraries behind one text-service interface so localisation (topic 7) and bidi get tested once.
- Atlas packing and SDF generation can be offline for engine fonts and runtime for user fonts; msdfgen is a build-time dependency candidate.
- Check licences (msdfgen MIT, HarfBuzz MIT-style, FreeType FTL/GPL dual, ICU Unicode licence) against project policy.

### Open risks / to measure
- Frame cost of MSDF vs bitmap at editor text sizes; readability at 9-12 px at 100-200% DPI.
- MSDF overlap artefacts on real fonts (variable fonts, CJK); atlas memory with large CJK sets.
- Compute rasteriser portability across Vulkan drivers (NVIDIA/AMD/Intel/lavapipe).
- Slug patent/licence status: confirm on the primary page.
- Subpixel positioning and animation stability of distance-field text.

---

## 2. UI frameworks as references

### Summary
- Flutter: three trees (Widget immutable config, Element lifecycle/identity, RenderObject layout+paint). Layout protocol: constraints go down, sizes go up, parent sets position ("Understanding constraints"). `[V-full]` Repaint boundaries are NOT mentioned on the architectural overview page (first-pass claim unsupported there; the overview defers to the "Inside Flutter" whitepaper). `[U]`
- Declarative UI with state (SwiftUI, Jetpack Compose): UI = f(state); Compose uses a compiler plugin with slot table and positional memoisation; recomposition skips unchanged inputs by stability. Phases page: composition, layout, drawing; state reads are tracked per phase and unchanged composables are skipped. Slot table and compiler plugin not on that page; stability page not opened. `[V-full]` (phases only)
- Qt Quick scene graph: retained node tree rendered on a dedicated render thread, batching of geometry/material nodes; separation of QML object tree from scene graph nodes. `[U]`
- Dear ImGui: immediate mode, no retained widget tree, IDs derived from labels/stack; cheap to write, hard for accessibility, layout needs multiple passes, and persistent state is user-managed. Muratori's IMGUI talk (2005) is the origin reference. `[U]`
- Unreal Slate: retained-mode C++ declarative syntax (SNew/SAssignNew), Invalidation Panel/global invalidation to avoid per-frame layout, Retainer Box to cache widget subtree to render target at reduced rate. `[U]` (Slate docs not opened; Epic doc pages returned empty bodies)
- Accessibility: Windows UI Automation (providers expose control patterns; tree must exist for screen readers and test tools). AccessKit is a cross-platform accessibility schema/adapter (Rust, C bindings) aimed at custom-drawn UIs. `[U]`
- Games: WCAG 2.2 gives contrast (4.5:1 text, 3:1 large/UI), target size, focus visibility; Game Accessibility Guidelines and Xbox Accessibility Guidelines are game-specific. `[U]`
- A semantic tree separate from the render tree is the common enabler of accessibility, automation (topic 5) and localisation tooling. `[U]`

### Key sources
| Title | Org | Year | URL | Status |
|---|---|---|---|---|
| Flutter architectural overview; Understanding constraints | Flutter team | docs | https://docs.flutter.dev/resources/architectural-overview ; https://docs.flutter.dev/ui/layout/constraints | `[U]` |
| Jetpack Compose docs (phases, stability) | Google | docs | https://developer.android.com/develop/ui/compose | `[U]` |
| Qt Quick Scene Graph | Qt Company | docs | https://doc.qt.io/qt-6/qtquick-visualcanvas-scenegraph.html | `[U]` |
| Dear ImGui README/FAQ; Muratori "Immediate-Mode Graphical User Interfaces" | Cornut; Muratori | 2005 talk, repo | https://github.com/ocornut/imgui | `[U]` |
| Slate UI Framework, Invalidation, Retainer Box | Epic Games | docs | https://dev.epicgames.com/documentation/en-us/unreal-engine/slate-user-interface-programming-framework-for-unreal-engine | `[U]` |
| UI Automation Overview | Microsoft | Learn | https://learn.microsoft.com/windows/win32/winauto/entry-uiauto-win32 | `[U]` |
| WCAG 2.2 | W3C | 2023 Rec | https://www.w3.org/TR/WCAG22/ | `[U]` |
| AccessKit | AccessKit project | GitHub | https://github.com/AccessKit/accesskit | `[U]` |

### Applicability to Heliogrim
- Keep Reflow retained with explicit invalidation (Slate/Flutter style); give nodes stable identity so state, animation and automation survive rebuilds.
- Adopt constraints-down/sizes-up layout as the protocol; it is easy to test in isolation (golden layout tests).
- Maintain a semantic tree that can feed UIA/AccessKit and the editor test driver from one source.
- Define a state-binding story (observable or signal) early; Compose-style stability/skipping is a lead if rebuild cost shows up.

### Open risks / to measure
- Cost of full-tree layout in large panels (asset browser with 100k items): need virtualisation.
- Whether AccessKit's C API is viable in a C++23/Windows build vs hand-written UIA providers.
- Input latency of retained UI under heavy invalidation.

---

## 3. Editor undo/redo and action workflows

### Summary
- Command pattern (GoF 1994) with do/undo pairs; alternative is state snapshot (memento) or delta. Production editors mix both. `[U]`
- Unreal: `FScopedTransaction` groups edits; objects call `Modify()` before change to record a delta into the transaction buffer (UTransactor); redo via the same buffer. Property-level transacted changes depend on UPROPERTY reflection. `[U]`
- Unity: `Undo.RecordObject`, `Undo.RegisterCreatedObjectUndo`, `Undo.CollapseUndoOperations`, undo groups; snapshot diff of serialised object state. `[U]`
- Blender: global undo via memfile (full state diff) plus mode-specific undo (edit mesh, sculpt) via an undo-type system with step push/decode; developer docs describe `UndoType` callbacks. `[U]`
- Reflection/serialisation-based snapshot diffing gives broad coverage cheaply but costs memory and cannot undo external effects (GPU resources, files). `[U]`
- Multi-object edits: one transaction contains many sub-changes; atomicity and nested-transaction semantics (merge into parent) must be explicit. `[U]`
- Asset edits: undo across asset save/reload and reimport is the hard case; typical answers are (a) asset edit sessions with own history, (b) treat save as an undo barrier, (c) keep snapshot of source until commit. `[U]`
- Collaboration: OT (Ellis & Gibbs 1989) and CRDTs (Shapiro et al. 2011; Automerge, Yjs) are leads; Kleppmann et al. "Local-first software" (Onward! 2019) frames requirements. Collaborative undo is selective/per-user undo, much harder than single-user. `[U]`

### Key sources
| Title | Authors/org | Year | URL | Status |
|---|---|---|---|---|
| Design Patterns (Command, Memento) | Gamma et al. | 1994 | book | `[U]` |
| Transactions / FScopedTransaction API reference | Epic Games | docs | https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/UnrealEd/FScopedTransaction | `[U]` |
| Undo class scripting reference | Unity | docs | https://docs.unity3d.com/ScriptReference/Undo.html | `[U]` |
| Blender developer docs, Undo System | Blender Foundation | docs | https://developer.blender.org/docs/features/core/undo/ (old code_layout path 404s; live URL found via search) | `[S]` stateful vs differential steps, `UndoType`, memfile |
| Concurrency control in groupware systems | C. Ellis, S. Gibbs | SIGMOD 1989 | https://dl.acm.org/doi/10.1145/67544.66963 | `[U]` |
| Conflict-free Replicated Data Types | Shapiro, Preguica, Baquero, Zawirski | SSS 2011 / INRIA RR-7687 | https://inria.hal.science/inria-00609399 | `[U]` |
| Local-first software | Kleppmann et al. | Onward! 2019 | https://www.inkandswitch.com/local-first/ | `[U]` |

### Applicability to Heliogrim
- Editor actions (existing Editor.Action) should be transactional: begin/commit/abort scopes, nestable, with a name for the history UI.
- Prefer command deltas for high-frequency edits (gizmo drags coalesced by key) and snapshots for coarse structural ops.
- Define an explicit policy for asset-side undo (barrier vs session) before building import workflows.
- Make every action replayable: this doubles as the editor test recorder (topic 5).
- Collaboration: only keep the serialised-delta format CRDT-friendly (stable IDs, no pointer identity); do not build it now.

### Open risks / to measure
- Memory footprint of N undo steps with large scenes (snapshot vs delta).
- Undo correctness across actor/archetype structural moves (component storage relocation).
- Coalescing rules for continuous edits; consistency under multi-window editing.

---

## 4. Visual scripting emitting native code

### Summary
- Unreal Blueprint nativization (convert BP to C++ at cook) was removed in 5.0: the 5.0 release notes say "Removed underlying framework and support for the Blueprint nativization feature and all related code modules" `[S]` (page body came back empty; quote via search). Deprecation release is 4.27 per search results, not 4.26 as first written (`[U]`, conflicting). Epic's motives are not in the release notes; forum reasons are community speculation. Commonly reported issues: build-time cost, fragility/coherence bugs with hot reload and cooked-vs-editor behaviour divergence, and that profiled gains were smaller than expected. Replacement direction: improve the Blueprint VM. Verify against 5.0 release notes. `[U]`
- Unity Visual Scripting (Bolt, integrated 2021): graph interpreted/with AOT-friendly reflection; can generate C# via "Generate" for Ahead-of-Time (IL2CPP) needs. `[U]`
- Godot VisualScript was deprecated and removed from core in 4.0 (moved to extension), Primary post is "Godot 4.0 will discontinue VisualScript" (Aug 2022), not the "sets sail" article (which never mentions VisualScript). Stated reasons per search summary: low utility without high-level components, poor documentation, lack of feedback; code moved to a separate repo, possible GDExtension later. The "citing maintenance cost versus GDScript" and "0.5% usage" figures are not from the primary post. `[S]`
- Graph IR: dataflow graphs (pure nodes, order by dependency) vs control-flow graphs (exec pins). Blueprint and most engine tools mix both: exec pins sequence side effects, data pins are demand-evaluated. Literature: Johnston et al., "Advances in Dataflow Programming Languages" (ACM CSUR 2004). `[U]`
- Lowering strategy: graph -> typed IR (SSA-like) -> C++ text; sea-of-nodes (Click & Paleczny 1995) is a reference for graph-based IR but is overkill for emission; plain structured lowering is simpler. `[U]`
- Deterministic codegen: stable node IDs, sorted iteration, no pointer/hash-order dependence, fixed formatting, reproducible-builds guidance (reproducible-builds.org). `[U]`
- Source maps for debugging: `#line` directives map generated C++ to graph node IDs for debugger/diagnostics; JS source-map spec (ECMA-426) is a model for a sidecar map. `[U]`
- Round-trip hazards: editing generated code is unsupported; keep it write-only and regenerate. `[U]`

### Key sources
| Title | Org/authors | Year | URL | Status |
|---|---|---|---|---|
| Unreal Engine 5.0 release notes (nativization removal) | Epic Games | 2022 | https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-0-release-notes | `[U]` |
| Unity Visual Scripting manual | Unity | docs | https://docs.unity3d.com/Packages/com.unity.visualscripting@latest | `[U]` |
| Godot 4.0 changelog / VisualScript removal | Godot Foundation | 2023 | https://godotengine.org/article/godot-4-will-discontinue-visual-scripting/ (sets-sail article does not cover it) | `[S]` |
| Advances in Dataflow Programming Languages | Johnston, Hanna, Millar | ACM CSUR 36(1), 2004 | https://dl.acm.org/doi/10.1145/1013208.1013209 | `[U]` |
| A Simple Graph-Based Intermediate Representation | Click, Paleczny | IR workshop 1995 | https://www.oracle.com/technetwork/java/javase/tech/c2-ir95-150110.pdf | `[U]` |
| Reproducible Builds docs | reproducible-builds.org | ongoing | https://reproducible-builds.org/docs/ | `[U]` |
| Source map format specification (ECMA-426) | Ecma TC39-TG4 | 1st ed.; live draft dated 2026-10-20 | https://tc39.es/ecma426/ | `[V-abs]` |

### Applicability to Heliogrim
- Treat emission as a compiler: graph -> validated typed IR -> C++ via a small printer; reuse the diagnostics system (topic 8) with node-ID spans.
- Cheaper alternative to nativisation to evaluate: an interpreted/bytecode path for iteration plus emission only for shipping; Blueprint history argues against making emitted code mandatory.
- Make output deterministic and diffable so generated files can be golden-tested.
- Accel IR work (shader IR) already in repo notes could share graph/IR infrastructure; unverified overlap.

### Open risks / to measure
- Build-time impact of generated C++ per graph; incremental rebuild behaviour with Ninja.
- Debugger story: `#line` fidelity under clang-cl/PDB.
- ABI/hot-reload interaction between generated and hand-written modules.

---

## 5. Test automation for engines and editors

### Summary
- (Epic automation/Gauntlet/screenshot pages returned empty bodies; all `[U]` here.) Unreal Automation: unit/feature tests via macros (`IMPLEMENT_SIMPLE_AUTOMATION_TEST`), Functional Tests as actors in maps, screenshot comparison tool with per-platform ground truth, Gauntlet for launching/running multi-process sessions on devices and collecting results. `[U]`
- Unity Test Framework (NUnit): Edit Mode and Play Mode tests, async/coroutine tests, platform runs. `[U]`
- Godot GUT (and gdUnit4): script-level unit testing with doubles; lightweight. `[U]`
- Deterministic replay: record input + fixed timestep + seeded RNG + frozen asset set; replay produces identical state hashes. Hazards: floating-point differences across compilers/drivers, thread scheduling, unordered containers. `[U]`
- Golden images: compare with perceptual metrics. SSIM (Wang et al., IEEE TIP 2004) and FLIP (Andersson et al., HPG 2020, NVIDIA) approximate perceived difference; FLIP is designed for rendered, alternating images and ships a C++/CUDA/Python reference. `[U]`
- Profile capture in CI: record frame-time distributions per scenario (p50/p95/p99), compare with tolerance bands relative to a baseline from the same machine class; noisy hardware needs statistical tests, not fixed thresholds. `[U]`
- Fixture scopes: unit (pure), module (service with fakes), scene (loaded world, headless), editor-workflow (UI driven via semantic tree + action replay). Each scope has a cost budget. `[U]`
- GPU tests in CI: Mesa lavapipe (CPU Vulkan, conformant implementation) and Google SwiftShader give headless Vulkan; results differ from real GPUs so goldens need per-implementation baselines or tolerance. `[U]`

### Key sources
| Title | Authors/org | Year | URL | Status |
|---|---|---|---|---|
| Automation System Overview; Gauntlet; Functional Testing; Screenshot Comparison | Epic Games | docs | https://dev.epicgames.com/documentation/en-us/unreal-engine/automation-system-in-unreal-engine | `[U]` |
| Unity Test Framework manual | Unity | docs | https://docs.unity3d.com/Packages/com.unity.test-framework@latest | `[U]` |
| GUT | bitwes | GitHub | https://github.com/bitwes/Gut | `[U]` |
| FLIP: A Difference Evaluator for Alternating Images | Andersson, Nilsson, Akenine-Moller et al. (NVIDIA) | PACMCGIT (HPG) 2020 | https://research.nvidia.com/publication/2020-07_FLIP (old slug 404s; DOI 10.1145/3406183; authors also Oskarsson, Astrom, Fairchild; PACMCGIT 3(2), 15:1-15:23) | `[S]` |
| Image Quality Assessment: From Error Visibility to Structural Similarity | Wang, Bovik, Sheikh, Simoncelli | IEEE TIP 2004 | https://doi.org/10.1109/TIP.2003.819861 (IEEE TIP 13(4), 600-612, April 2004) | `[S]` |
| Lavapipe (Mesa docs) | Mesa | docs | https://docs.mesa3d.org/drivers/lavapipe.html (404; no standalone page found) | `[U]` Vulkan 1.3 conformant per Igalia Vulkanised 2025 talk `[S]` |
| SwiftShader | Google | GitHub | https://github.com/google/swiftshader (Vulkan 1.3 conformance submission #717, Apache-2.0, "not an official Google product") | `[V-full]` |

### Applicability to Heliogrim
- Record/replay = serialized action stream (topic 3) + fixed-step clock; add state-hash checkpoints for divergence detection.
- Golden tests: start with deterministic CPU-side artefacts (layout dumps, draw lists, SDF atlases) before pixel comparison; add FLIP for GPU frames with lavapipe baselines.
- Tag tests by scope so CI can gate cheap scopes per commit and run workflow scopes nightly.
- Perf gates: per-scenario budgets stored in repo, compared with noise-aware thresholds.

### Open risks / to measure
- Run-to-run variance of frame time on the CI machine; needed sample count.
- lavapipe feature coverage vs engine requirements (extensions, descriptor indexing, compute).
- Cross-compiler floating-point determinism (clang-cl vs MSVC cl).

---

## 6. Editor asset search

### Summary
- Unreal Asset Registry: in-memory database of asset metadata (path, class, tags from `GetAssetRegistryTags`), built by scanning, with a cache and cooked-asset registry; async scan with events. `[U]`
- Unity Search: pluggable providers, indexers (persistent index on disk), query language with filters (`t:`, `ref:`), expressions and `p:` property queries. `[U]`
- Full-text engines: Lucene-style inverted index with segments and merging; Tantivy (Rust) is a modern Lucene-like reference with BM25, segments, mmap. SQLite FTS5 gives embedded inverted index with BM25, prefix and trigram tokenisers, easy transactions. `[U]`
- Fuzzy/substring matching for names: trigram index, or fzf-style scoring, are common for file pickers. `[U]`
- Incremental indexing: OS file watchers (ReadDirectoryChangesW on Windows) plus periodic reconciliation, since watcher events can be dropped or coalesced; content-hash keyed entries avoid reindex. `[U]`
- Tags as typed key-value metadata extracted by importers makes search a database query rather than ad-hoc code. `[U]`

### Key sources
| Title | Org | URL | Status |
|---|---|---|---|
| Asset Registry | Epic Games | https://dev.epicgames.com/documentation/en-us/unreal-engine/asset-registry-in-unreal-engine | `[U]` |
| Unity Search (Search overview, query syntax) | Unity | https://docs.unity3d.com/Manual/search-overview.html | `[U]` |
| SQLite FTS5 Extension | SQLite | https://www.sqlite.org/fts5.html | `[U]` |
| Tantivy | Quickwit | https://github.com/quickwit-oss/tantivy | `[U]` |
| Introduction to Information Retrieval (inverted index, BM25) | Manning, Raghavan, Schutze | Cambridge UP 2008 | https://nlp.stanford.edu/IR-book/ | `[U]` |
| ReadDirectoryChangesW | Microsoft | https://learn.microsoft.com/windows/win32/api/winbase/nf-winbase-readdirectorychangesw | `[U]` |

### Applicability to Heliogrim
- Tight need: metadata registry first (tags, deps, types), text search second; SQLite with FTS5 is the lowest-maintenance embedded option (container replacement bar applies: maintenance counts).
- Index lives under project cache, rebuildable from assets; never source of truth.
- Importers publish tags; search queries use the same tag schema as UI filters.
- Watcher + reconciliation scan; hash-keyed.

### Open risks / to measure
- Cold scan time at 100k-1M assets; index size on disk; query latency target (interactive, <50 ms to be validated).
- Watcher loss under bulk operations (git checkout).
- Tokenisation of CJK/camelCase names.

---

## 7. Localization

### Summary
- ICU provides locale data (from Unicode CLDR), formatting, collation (UCA/UTS #10), break iterators, normalisation. Plural categories (zero/one/two/few/many/other) per language come from CLDR (UTS #35 Part 3). `[U]`
- MessageFormat 2.0 (MF2): Unicode standard developed in CLDR/ICU; declared stable in CLDR 47 (released 2025-03-13; stability policy normative; only `:string`, `:number`, `:integer` default functions stable) `[S]` via CLDR 47 release note and Unicode blog snippets. ICU: `icu::message2::MessageFormatter` (C++) and `com.ibm.icu.message2` shipped as TECH PREVIEW in ICU 76; C++ still tech preview in ICU 77/78 and behind the spec (CLDR 47 level in ICU 78, CLDR 49 later) `[S]`. The ICU user guide MF2 page itself (opened) says "Technical Preview", cites ICU 75.1 and LDML 45, and says functions will change; it is stale relative to CLDR 47. C++ is available but not stable API. `[V-full]` (user guide) `[S]` (CLDR/ICU status)
- Mozilla Fluent: asymmetric localisation; messages, terms, attributes, selectors with plural/gender handled in translation not code; influenced MF2. `[U]`
- gettext: PO/MO catalogs, msgid keyed by source string, ngettext plurals; mature tooling, weaker for complex grammar. `[U]`
- Unreal: Localization Dashboard: gather (scan source/assets for FText) -> manifest/archive -> translate (PO/XLIFF export) -> compile to .locres; FText with namespace/key; String Tables for shared keys. `[U]`
- String table design: stable keys over source-text keys; context and plural metadata; ICU-style arguments typed; avoid concatenation. `[U]`
- Font fallback chains per script, bidi (UAX #9) mirroring for RTL layout, and shaping per script feed back into UI layout (topic 1/2). `[U]`
- Pseudo-localisation (accented, expanded ~30-40%, bracketed, mirrored RTL) finds hard-coded strings, truncation and layout breaks before translators exist; Microsoft and Android document it. `[U]`

### Key sources
| Title | Org | URL | Status |
|---|---|---|---|
| UTS #35 LDML (plural rules Part 3; MessageFormat Part 9) | Unicode Consortium | https://www.unicode.org/reports/tr35/ | `[U]` |
| ICU User Guide, MessageFormat 2 | Unicode / ICU | https://unicode-org.github.io/icu/userguide/format_parse/messages/ | `[U]` |
| UTS #10 Unicode Collation Algorithm | Unicode | https://www.unicode.org/reports/tr10/ | `[U]` |
| Project Fluent | Mozilla | https://projectfluent.org/ | `[U]` |
| GNU gettext manual | GNU | https://www.gnu.org/software/gettext/manual/ | `[U]` |
| Localization Dashboard / Text Localization | Epic Games | https://dev.epicgames.com/documentation/en-us/unreal-engine/localization-dashboard-in-unreal-engine | `[U]` |
| Pseudo-localization | Microsoft Learn; Android developer docs | https://learn.microsoft.com/globalization/localization/pseudo-localization | `[U]` |

### Applicability to Heliogrim
- Depend on CLDR data (via ICU or a trimmed extract) for plurals/collation rather than hand-rolling; ICU size is the cost to measure.
- Choose a message syntax early (MF2 vs Fluent-like); keep the runtime API a typed-argument `Text` object and avoid string concat in the UI kit.
- Reflow text service must support per-run font fallback and RTL layout mirroring.
- Ship a pseudo-locale in the editor and run it in UI tests (links to topic 5).

### Open risks / to measure
- ICU binary/data footprint and licence; MF2 library maturity in C++.
- Layout overflow under expansion; CJK atlas sizes.
- Translator workflow: format choice vs available tooling (XLIFF/PO).

---

## 8. Diagnostics, standards, and quality gates

### Summary
- Rust diagnostics: structured primary/secondary spans, labels, notes/help, machine-applicable suggestions with applicability levels, error codes (E0xxx) with long explanations (`--explain`). Elm's error messages are the human-tone reference. clang: fix-it hints, notes, caret diagnostics, `-fdiagnostics-format`, `-Wno` groups. `[U]`
- LSP 3.17 `CodeAction` (kind quickfix, edit, diagnostics linkage) and `Diagnostic` (code, codeDescription, relatedInformation, tags, data field for fix payload) are a ready transport for editor-side fix information. `[U]`
- OpenTelemetry Logs Data Model: structured records with severity, body, attributes, trace/span correlation; useful for log schema even without OTel runtime. `[U]`
- MISRA C++:2023 (published Oct 2023, 179 guidelines, basis ISO 14882:2017, merge with AUTOSAR announced Jan 2019 `[S]`; MISRA's own page not opened): merged successor of MISRA C++:2008 and AUTOSAR C++14, aligned with C++17; rule categories (required/advisory), decidable vs undecidable. AUTOSAR C++14 guidelines (2019) cover C++14. JSF AV C++ (Lockheed Martin, 2005) is C++03, aerospace, dated. SEI CERT C++ is security-focused. C++ Core Guidelines (Stroustrup, Sutter) is the modern, tool-supported set (GSL, clang-tidy cppcoreguidelines-*). `[U]`
- Applicable subset for a game engine: ownership/lifetime, no UB-prone casts, bounded integer arithmetic at trust boundaries, no unchecked array access in parsers, const-correctness, avoid dynamic allocation in hot paths is not required by MISRA but by perf. Not applicable: blanket ban on exceptions/dynamic memory/recursion, which conflict with engine design; adopt as per-module profiles. Project is C++23 so MISRA 2023 (C++17) maps imperfectly. `[U]`
- Static analysis: clang-tidy (bugprone, cert, cppcoreguidelines, performance), clang Static Analyzer, PVS-Studio, Coverity (free for OSS), CodeQL; combine, track baselines to avoid noise. `[U]`
- Sanitizers: ASan docs list Windows 8.1+ as supported but "not as well supported as the other ports"; leak detection not supported off Linux/macOS. `[V-abs]` UBSan/TSan Windows status was not on that page, still `[U]`.
- Fuzzing: libFuzzer (LLVM) in-process coverage-guided `[V-full]`; docs say it is now maintenance-only (authors moved to Centipede; bug fixes only) and on Windows needs ASan, no `/MD`, no `/INCREMENTAL` or `/DEBUG` link. OSS-Fuzz as infra; targets are parsers/loaders (asset formats, serialization, shader front-end, localization message parser). Structure-aware fuzzing (libprotobuf-mutator) for grammars. `[U]`
- DO-178C-style traceability: requirement -> design -> code -> test links, structural coverage (MC/DC at DAL A), tool qualification (DO-330). Cheap subset: trace issue -> test -> commit, coverage per module, no unexplained dead code. `[U]`

### Key sources
| Title | Org/authors | Year | URL | Status |
|---|---|---|---|---|
| Rustc dev guide: Diagnostics; Error index | Rust project | docs | https://rustc-dev-guide.rust-lang.org/diagnostics.html ; https://doc.rust-lang.org/error_codes/ | `[U]` |
| Compiler Errors for Humans | E. Czaplicki | 2015 (author blog; secondary) | https://elm-lang.org/news/compiler-errors-for-humans | `[U]` |
| Clang diagnostics, fix-it hints | LLVM | docs | https://clang.llvm.org/docs/InternalsManual.html#the-diagnostics-subsystem | `[U]` |
| Language Server Protocol 3.17 | Microsoft | 2022 | https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/ | `[U]` |
| OpenTelemetry Logs Data Model | CNCF OpenTelemetry | spec | https://opentelemetry.io/docs/specs/otel/logs/data-model/ | `[U]` |
| MISRA C++:2023 | MISRA Consortium | 2023 | https://misra.org.uk/ (paid doc) | `[U]` |
| AUTOSAR Guidelines for the use of the C++14 language in critical and safety-related systems | AUTOSAR | 2019 | https://www.autosar.org/standards/adaptive-platform | `[U]` |
| JSF Air Vehicle C++ Coding Standards | Lockheed Martin | 2005 | https://www.stroustrup.com/JSF-AV-rules.pdf | `[U]` |
| SEI CERT C++ Coding Standard | CMU SEI | 2016 | https://wiki.sei.cmu.edu/confluence/pages/viewpage.action?pageId=88046682 | `[U]` |
| C++ Core Guidelines | Stroustrup, Sutter | living | https://isocpp.github.io/CppCoreGuidelines/ | `[U]` |
| libFuzzer; AddressSanitizer; UBSan | LLVM | docs | https://llvm.org/docs/LibFuzzer.html ; https://clang.llvm.org/docs/AddressSanitizer.html | `[U]` |
| DO-178C Software Considerations in Airborne Systems | RTCA | 2011 | https://www.rtca.org/ (paid) | `[U]` |

### Applicability to Heliogrim
- Define one `Diagnostic` type: code, severity, primary span + labels, notes, ordered fix suggestions with applicability; serialise to LSP shape so editor UI, CLI and codegen (topic 4) share it. Registry of codes with explanations as docs pages.
- Adopt C++ Core Guidelines + CERT C++ via clang-tidy profiles; treat MISRA C++:2023 as a reading list for hardened modules (parsers, serialization, networking) rather than a full compliance target.
- CI matrix: clang-cl ASan+UBSan test runs; separate Linux job for TSan/MSan if a Linux build exists; libFuzzer targets for each loader/deserializer.
- Lightweight traceability: issue "Done when" -> test names -> commit; coverage reports per bundle.
- Structured logging schema with stable event IDs, compatible with OTel attributes.

### Open risks / to measure
- clang-tidy runtime on the full tree (unity build interplay); baseline noise count.
- ASan on Windows with custom allocators and vendored libs.
- Fuzz harness maintenance cost vs bug yield; coverage achievable per loader.
- MISRA C++:2023 licensing (paid) and C++23 gap.

---

## Cross-cutting leads
- One semantic/action/diagnostic backbone (actions replayable, diagnostics structured, UI tree introspectable) serves topics 2, 3, 5, 8 together.
- Remaining before citing: Slug patent dedication (open terathon.com/blog/decade-slug.html), Epic doc pages, Slate, ICU footprint, AccessKit C API fit in practice.

## Verification pass (2026-11-07)
- `[V-full]`: sluglibrary.com (proprietary, $1500 solo, no patent statement); github.com/linebender/vello; github.com/servo/pathfinder (not archived on page); github.com/Chlumsky/msdfgen; docs.flutter.dev/resources/architectural-overview and /ui/layout/constraints; developer.android.com/develop/ui/compose/phases; github.com/google/swiftshader; sqlite.org/fts5.html (4 tokenizers, bm25 k1=1.2 b=0.75); github.com/quickwit-oss/tantivy (MIT, BM25, mmap); dev.epicgames.com asset-registry-in-unreal-engine; projectfluent.org (Mozilla research project, Syntax 1.0 April 2019); llvm.org/docs/LibFuzzer.html; github.com/AccessKit/accesskit (Rust, C bindings, Win/mac/Linux/Android/iOS); rustc-dev-guide diagnostics; opentelemetry.io logs data-model (Stable); unicode-org.github.io/icu/userguide/format_parse/messages/mf2.html.
- `[V-abs]`: tc39.es/ecma426 (draft 2026-10-20); dev.epicgames.com API FScopedTransaction; docs.unity.com Undo (docs.unity3d.com redirects; RecordObject, RegisterCreatedObjectUndo, CollapseUndoOperations present); Unity Search overview (6.6; providers, indexing, textual queries); UTS #35 Part 3 Numbers (CLDR 49, six plural categories); UTS #10 (v18.0.0, 2026-08-31); gnu.org gettext manual (PO/MO, msgid_plural); WCAG 2.2 (Rec 2024-12-12; 1.4.3 4.5:1, large 3:1; 1.4.11 3:1); clang AddressSanitizer.html; learn.microsoft.com UI Automation overview; LSP 3.17 Diagnostic fields (CodeAction section not reached); isocpp C++ Core Guidelines (Stroustrup, Sutter; modified 2026-06-14).
- `[S]` (search summaries only): JCGT 6(2) Lengyel; Slug patent dedication 2026-03-17 and MIT reference shaders; CLDR 47 stable (2025-03-13) and ICU 76+ tech preview; FLIP (DOI 10.1145/3406183); SSIM (IEEE TIP 13(4) 600-612); Blender developer.blender.org/docs/features/core/undo/; UE 5.0 notes nativization removal; Godot "will discontinue VisualScript" post; Johnston et al. CSUR 36(1) 1-34; MISRA C++:2023 (Oct 2023, C++17, 179 guidelines); lavapipe Vulkan 1.3 conformant.
- `[U]` with reason: Green 2007 Valve PDF (compressed stream unreadable); Slate/Invalidation/Retainer, Unreal Automation/Gauntlet/Screenshot, Localization Dashboard, UE 5.0 notes body (Epic pages returned empty); Microsoft pseudo-localization (404); Mesa lavapipe.html (404); AUTOSAR C++14 (listed nowhere on adaptive-platform page); SEI CERT C++, JSF, DO-178C, Qt, ImGui, Skia, Impeller page, Compose stability, Click/Paleczny (not fetched, budget); UBSan/TSan Windows status; CodeAction fields; Unity Visual Scripting, GUT.
- Corrections: Slug library is not public domain (only the patent, per blog); Pathfinder "archived" unconfirmed; Vello "Hybrid" is `vello_gpu`, CPU variant most mature, binning/coarse/fine not in README; Flutter overview has no repaint boundaries; nativization deprecation 4.27 not 4.26; Godot source is the "discontinue VisualScript" post; MF2 is spec-stable but ICU C++ stays tech preview; Blender and lavapipe URLs fixed; libFuzzer is maintenance-only.
