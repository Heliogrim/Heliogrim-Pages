# Research Sources

Raw reports written by research agents on 2026-11-07 for the battle plan, followed by a verification pass the same day. Each report marks every claim by what was opened: `verified (full text)`, `verified (abstract/landing page)`, search-summary only (`[S]` or "(search)"), or `unverified`. The topic pages summarise them; decisions must cite claims verified from an opened page.

| Report | Covers | State after the verification pass |
|--------|--------|-----------------------------------|
| [Rendering core](research-rendering.md) | GPU-driven, visibility buffer, meshlets, render graphs, shadows, GI, OIT, materials, post | Bibliographic data confirmed for nearly all sources; Vulkan and FSR pages read in full; JCGT entries rest on listings; corrections: FrameGraph single speaker, MBOIT venue, Kuth claims |
| [World, weather, fluids, terrain](research-world.md) | Sky and clouds, fluids, ocean, terrain, foliage, particles, procedural generation | Bibliographic data confirmed from abstracts and course pages; corrections: Sea of Thieves uses FFT (SIGGRAPH 2018 talk), Niagara talk title and speaker, Hillaire 2016 venue, Nanite foliage version |
| [Shader IR, hot reload, build, plugins, crash](research-tooling.md) | Slang, SPIR-V, pipeline library, ORC JIT, Live++, Godot export, Unreal plugins, Crashpad, minidumps, Git LFS | Most docs pages read in full (Live++ pricing and limits, LFS locking, LSP, SPIRV-Tools, CMake export); corrections: cr.h state model, Ksplice and Kitsune, Artifact Signing rename |
| [Scheduling, streaming, open world, networking](research-runtime.md) | Fibers, DirectStorage, large world, MMO architecture, QUIC, snapshots, headless, determinism | RFC numbers, zstd table, Jolt and Rapier determinism docs confirmed; corrections: IoRing minimum build, Rapier determinism mechanism; MMO architecture claims still weak |
| [Physics, animation, navigation, DCC, input](research-simulation.md) | Jolt, cloth, animation, ACL, interchange, Recast, Enhanced Input, SDL3 | Jolt figures, ACL measurements, glTF and Detour sources read in full; corrections: PBD venue, Büttner venue, ORCA citation |
| [UI, editor, tooling, quality](research-editor-quality.md) | Vector UI, frameworks, undo, visual scripting, test automation, search, localisation, diagnostics, standards | Most tool and standards pages read; corrections: Slug library is proprietary (patent dedication unconfirmed), ICU MessageFormat 2 still a technical preview, Vello crate layout, libFuzzer maintenance mode |

## What is still open

Technique descriptions and performance numbers inside paper bodies were not read in most cases (abstract-level verification only). Items that still need a hand check before they back a decision:

1. Slug patent dedication (author blog and reference-shader repo).
2. Nishanov P1364 conclusions (PDF unreadable to the agents).
3. JCGT bodies: DDGI, WBOIT, Visibility Buffer (page fetches returned empty).
4. Epic documentation pages that returned empty: Slate, Automation, Localization Dashboard, UE 5.0 release notes body, dedicated server flags.
5. MMO architecture talks (EVE, SpatialOS, Star Citizen, Dual Universe): still marketing or blog grade.
6. Slide decks not opened: Gyrling 2015, O'Donnell 2017, Karis 2021, Schneider 2015 to 2023, Hillaire 2016.

Tracked as [#145](https://github.com/Heliogrim/Heliogrim-Engine/issues/145) on the engine repository.
