# Game-Project Build System, Packaging and Headless Roles

**Systems**: S53, S58 · **Track** D, E · **Milestone** M2, M4
**Status**: <span class="hg-status summary">plan</span>. Research from [tooling](../sources/research-tooling.md) section 4 (Godot export docs verified) and [runtime](../sources/research-runtime.md) section 5 (Agones docs verified).

## Target

- **Game-project build system**: a project folder with a descriptor builds to shippable, signed artifacts per platform with cooked content; incremental cooking by content hash; an exported engine SDK for game modules and plugins; reproducible builds.
- **Headless and cluster roles**: one binary runs as editor, client, dedicated server, worker or cluster node by configuration; servers run with a null render device and no window or audio; a health, ready and shutdown contract for orchestration; telemetry export.

## Current state (checked 2026-11-07)

- CMake with globbed bundles, `MakeLibraryProject.cmake`, test discovery; the editor target; `Heliogrim-Project-Template` beside the engine; vendored libraries build from `vendor/<name>/CMakeLists.txt`. No cook step, no export, no signing.
- `Heliogrim.Main` and `Editor.Main` are separate entries; `GameEngine` in `Engine.Core.Game` pulls `GFX`, `Input`, `Network`, `PFX`, `SFX`, `Platform.Win32`; no role selection, no null device.

## Research summary

- Godot (verified): the engine ships as prebuilt export templates; a project is data plus an export preset; export produces an executable plus data or a PCK that pairs with any compatible executable; credentials in a non-VCS file.
- Unreal (unverified): UBT and UAT, project and target files, cook, stage, package, pak; plugin descriptors (verified elsewhere). O3DE registers engines and projects by JSON with gems per project. CMake `install(EXPORT)` for SDKs (docs verified); `/Brepro` for reproducible builds (community sources only, no official Microsoft page found); Authenticode signing through Azure Artifact Signing (renamed from Trusted Signing; page verified).
- Agones (verified): Kubernetes CRDs for game servers, fleets, autoscalers and allocation with a C++ SDK; it targets session-based servers, so a long-lived single-shard cluster may fit plain StatefulSets better (not researched).
- Headless in Unreal (`-nullrhi`), Unity and Godot (`--headless`) are compositions of the same engine, not forks (unverified).

## Guidance

### S53 Game-project build system

- Project descriptor (text, S41): name, engine version, modules (game C++ modules built against the SDK), plugins, content roots, platforms and presets, localisation settings.
- Engine SDK: `install(EXPORT)` of the public bundles with include directories and vendored dependencies resolved; the SDK is what game modules and plugins compile against; CI builds the template project against it on every change (hygiene test for the ~60 bundles).
- Cook: importers produce runtime formats into a content-addressed cache (S41); packaging assembles cells (S40) and global packages; incremental by hash; the worker role (S58) runs cooks in parallel; shader variants (S13) are cooked for the target set.
- Package: executable (engine runtime plus statically linked or DLL game modules), packages, localisation tables, crash handler, symbol upload to the store (S06); `/Brepro` from the start; Authenticode signing as a configured step; a data-only package for patches.
- CLI first (`heliogrim build --project --preset`), editor UI on top.

### S58 Headless and cluster roles

- Role selection in `Engine.Config`; systems query capability flags (`hasGpu`, `hasWindow`, `hasAudio`, `hasNetwork`); `Engine.Core.Game` stops including the platform backend and GFX directly, the role composition adds them.
- Null render device in `Engine.Driver.Vulkan` (no instance, no swapchain) or a lavapipe device for server-side rendering tasks; the scene systems run without a render model when `hasGpu` is false.
- Server loop: fixed tick, no presentation, replication and persistence stages; worker loop: pulls jobs (cook, bake, navmesh, DAG build) from a coordinator; cluster node: server plus mesh membership (S57).
- Orchestration contract: ready, health, allocated, shutdown callbacks mapped to Agones' SDK or to a plain Kubernetes probe; OpenTelemetry metrics and spans export (S04).
- A Linux build of the server and worker roles is the first non-Windows target (enables TSan in CI too).

## Done when

- `heliogrim build` on the template project produces a signed Windows package that runs on a clean machine; a second build with no changes is byte-identical; a content change recooks only its dependents.
- The server role runs a headless simulation of the reference scene in CI and reports health; a worker cooks the template project's content in parallel; memory and startup time are recorded.
- The template project builds against the exported SDK in CI.

## Open decisions

- Static versus DLL game modules in shipping builds (HMR implies DLL in development).
- Agones versus plain Kubernetes for the single-shard cluster.
- Linux server target date.
