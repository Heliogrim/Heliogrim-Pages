# Gap Analysis

**Status**: <span class="hg-status summary">summary</span>. Nothing here is decided. It lists what this site and the engine lack next to commercial engines (Unreal Engine 5, Unity 6, Godot 4, O3DE) and enterprise documentation. It does not claim that Heliogrim needs all of it.

**Date**: 2026-11-06. Based on this site's pages only. The engine source and engine repository were not re-checked for this page.

## 1. The landing page

A commercial engine's home page answers these questions on its first screen. [Home](../index.md) answers none of them yet:

| Question | State | Needs |
|----------|-------|-------|
| What is it, and who is it for? | The lede describes the docs, not the engine | Owner's pitch: genre, scale, how it differs |
| What does it look like? | One abstract SVG | Screenshots or captures of the engine and editor |
| How mature is it? | Not stated | A status line and a list of what runs today |
| Which platforms and hardware? | Windows-first is implied in the [storage](storage-exploration.md) page only | A support matrix |
| Under which license? | The engine repository has no `LICENSE` file | An owner decision |
| What comes next? | The [timeline](timeline.md) orders the work but names no milestones | Milestones, if the owner wants them public |

## 2. Documentation types

Grouped by the [Diátaxis](https://diataxis.fr/) categories:

| Type | State | What commercial engines provide |
|------|-------|---------------------------------|
| Tutorials | none | First project, first actor, first material |
| How-to guides | docs work only | Build, debug, profile, package, add a module |
| Reference | [module map](modules.md) only | API, build options, file formats, command-line flags |
| Explanation | strong: explorations and designs | The same, plus [system pages](../systems/index.md) for what is built |

Systems with neither a page nor an exploration: the renderer backend, the asset pipeline and cooking, the editor (undo, selection, tools), input, physics, UI, the platform layer, memory and allocators, resource streaming, the build options in `Options.cmake`, testing, and packaging.

## 3. Topics without an exploration

These are questions every commercial engine has answered. Some may be out of scope on purpose. The owner decides which ones are.

- Networking and replication
- Physics: middleware or in-house
- World streaming and partitioning
- GPU-driven culling and LOD, beyond the [micropoly](../systems/micropoly-renderer.md) stub
- Memory budgets per platform
- Determinism, for replays and lockstep
- Hot reload of C++ modules (partly covered in [native codegen](scripting-native-codegen-exploration.md))
- Localization and accessibility
- Crash reporting and telemetry
- Performance regression testing in CI

## 4. Project hygiene

Enterprise and open-source projects publish these. Check the engine repository before adding any here:

- `LICENSE`, `SECURITY.md`, a code of conduct, and a contribution sign-off (DCO or CLA)
- Governance: who accepts an ADR in the engine project
- Releases: version scheme, changelog, deprecation policy
- A supported toolchain, OS and GPU matrix
- A glossary for engine terms (fiber, archetype, lane, guard)
- Docs versioned per engine release, once releases exist

## 5. Refinement on this site

- [Getting started](../guides/getting-started.md) has never been run on a clean machine.
- System pages are stubs, and none carries a verified commit yet.
- No ADR is accepted, although two topics are closed. Processing the [placeholders](../adr/README.md) in the engine project starts the record.
- Several sources are labelled as Gemini reviews or conversations. Readers outside the project weigh such sources lower than primary ones. Each claim should state whether it was checked against a primary source or the code.
- Four of the five original explorations rest on claims nobody has measured (see the [rundown](exploration-rundown.md), section 3).

## 6. Research needed

| Item | Why | Owner |
|------|-----|-------|
| License | Blocks adoption, contributions and publishing code excerpts ([code documentation](code-documentation.md)) | engine owner |
| Feature baseline against UE5, Unity 6, Godot 4, O3DE | Separates deliberate gaps from missing work | open |
| Target hardware and OS matrix | Already open in [storage](storage-exploration.md) | open |
| clang-doc spike | The only route to a symbol-level reference | open |
| Benchmarks for the open claims | Measured numbers are what engine postmortems lead with | per exploration |
| Available media | The landing page needs screenshots that are true today | engine owner |
