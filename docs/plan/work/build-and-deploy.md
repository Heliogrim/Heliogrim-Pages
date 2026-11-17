# Work: Game-Project Build System and Headless Roles

**Systems** S53, S58 · **Issues** [#133](https://github.com/Heliogrim/Heliogrim-Engine/issues/133), [#138](https://github.com/Heliogrim/Heliogrim-Engine/issues/138) · **Track** D, E · **Milestone** M2 (S58), M4 (S53)
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Build system, packaging, headless roles](../topics/build-and-deploy.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| `cmake/MakeLibraryProject.cmake`, globbed bundles, `Heliogrim-Project-Template` beside the engine | Bundle build and a template | No SDK export, cook, package, sign |
| `Heliogrim.Main`, `Editor.Main`, `GameEngine` in `Engine.Core.Game` | Two entries; game engine pulls GFX, Input, Network, PFX, SFX, Win32 directly | Role composition replaces direct includes; also a layer fix from the modules page |
| [Target architecture](../architecture.md) section 3 | Role table with root modules, device and threads | This page implements it |
| [Quality work](quality-and-process.md) S62 | CI jobs; Linux job for TSan | Linux server target is the first non-Windows build (Q58.2) |
| [Hot reload work](visual-scripting-hmr.md) | DLL modules in development | Static versus DLL in shipping (Q53.1) |
| [Crash work](diagnostics-and-crash.md) S06 | Symbol store upload | Package step uploads PDBs |
| [Observability work](diagnostics-and-crash.md) S04 | OTLP export | Cluster node telemetry |
| [Networking work](networking-mmo.md) S57 | Orchestration | Agones versus StatefulSets (Q58.1) |

## Architecture

- **Bundles**: `Engine.Config` gains `ProcessRole` and `Capabilities`; `Engine.Core.Game` becomes orchestration (role compositions in `Heliogrim.Roles/{Client,Server,Worker,Cluster}`); `Engine.Driver.Vulkan` gains `NullDevice`; new `Engine.Orchestration` (ready, health, allocated, shutdown contract). Build tooling: `cmake/HeliogrimSdk.cmake` (`install(EXPORT)`), `tools/heliogrim-build` CLI (descriptor, cook, package, sign), `Editor.Build` (UI over the CLI).
- **Provides**: one binary with role selection; headless simulation; SDK; reproducible signed packages; incremental cook.
- **Consumes**: content-addressed cache (S41), cells (S40), shader variant cook (S13), symbol store (S06), telemetry (S04), game modules (S48, S50), localisation compile (S52).

## Code design

| Type | Contract |
|---|---|
| `ProcessRole` | `Editor, Client, Server, Worker, Cluster` from `Engine.Config`; chosen at start. |
| `Capabilities` | `{ hasGpu, hasWindow, hasAudio, hasNetwork }`; systems query these, never the role name; headless is the absence of window and GPU. |
| `RoleComposition` | Per role: enabled root modules and threads; `Engine.Core.Game` stops including platform and GFX directly. |
| `NullDevice` | `Engine.Driver.Vulkan` device without instance or swapchain; scene systems skip render models when `hasGpu` is false; lavapipe optional for server-side rendering jobs. |
| `ServerLoop` | Fixed tick, no presentation, replication and persistence stages. `WorkerLoop`: pulls cook, bake, navmesh and DAG jobs from a coordinator. `ClusterLoop`: server plus mesh membership (S57). |
| `OrchestrationContract` | `ready`, `health`, `allocated`, `shutdown` callbacks mapped to Agones SDK or plain Kubernetes probes; OTLP export of spans and metrics. |
| `ProjectDescriptor` | Text (S41): name, engine version, modules, plugins, content roots, platforms and presets, localisation settings. |
| `EngineSdk` | `install(EXPORT)` of public bundles with includes and resolved vendored dependencies; the template project builds against it in CI. |
| `CookStep` | Importers to runtime formats into the content-addressed cache; incremental by hash; parallel through the worker role; shader variants for the target set; cells assembled into packages. |
| `PackageStep` | Executable plus modules (static or DLL per Q53.1), packages, localisation tables, crash handler, PDB upload; `/Brepro`; Authenticode signing as a configured step; data-only patch package. |

Placement: `Engine.Config/{ProcessRole,Capabilities}`, `Heliogrim.Roles/`, `Engine.Driver.Vulkan/NullDevice`, `Engine.Orchestration/`, `cmake/HeliogrimSdk.cmake`, `tools/heliogrim-build/`, `Editor.Build/`. Tests: headless reference scene in CI with health reporting; template project against the SDK in CI; byte-identical rebuild; dependent-only recook.

## Work chunks

### W58.1 Roles and capabilities design · design · ready

- **Goal**: role selection, capability flags, role compositions, null device, server and worker loops, orchestration contract, the `Engine.Core.Game` layer fix, Linux target plan.
- **Output**: `architecture/process-roles-design.md`; plan.
- **Questions**: Q58.1, Q58.2 (both decided, see Decisions).

### W58.2 Implement roles, capabilities, null device and server loop · execute · after W58.1

- **Done when**: the server role runs a headless simulation of the reference scene in CI and reports health; `Engine.Core.Game` no longer includes GFX or the platform backend.

### W58.3 Worker role and coordinator · execute · after W58.2, W02.5

- **Done when**: a worker cooks the template project's content in parallel.

### W58.4 Linux build of server and worker roles · execute · after W58.2

- **Done when**: the server role builds and runs the headless scene on Linux in CI; TSan job enabled (S62).

### W53.1 Build system design · design · after W41.1, W58.1

- **Goal**: descriptor, SDK export, cook, package, sign (pluggable signer and the guided CA workflow, Q53.2), module layout (static game code, DLL path for runtimes and third-party dependencies, Q53.1), CLI shape, editor UI later; the unified runtime representation per asset type and use case that the cook emits, agreed with W49.1 (format libraries stay editor-only, Q49.1).
- **Output**: `architecture/game-build-design.md`; plan.
- **Questions**: Q53.1, Q53.2.

### W53.2 Implement SDK export and the template project CI check · execute · after W53.1

- **Done when**: the template project builds against the exported SDK in CI on every engine change.

### W53.3 Implement cook and package CLI · execute · after W53.2, W41.2, W40.2, W13.2

- **Done when**: `heliogrim build` produces a Windows package that runs on a clean machine; a no-change rebuild is byte-identical; a content change recooks only dependents.

### W53.4 Signing, symbol upload, patch packages · execute · after W53.3, W06.3

### W53.5 Editor build UI · execute · after W53.3, W43.3
## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q53.1 | Game modules static in shipping, DLL in development. Shipping still has to load DLLs: allocators, the C++ runtime and third-party libraries a game developer pulls in (SQLite or any other framework, tool or utility), so the module layout keeps a DLL path for dependencies even when game code links statically. |
| Q53.2 | Signing is required at some point and is the game developer's authority: obtaining a certificate from a public CA or running an own CA is their job, the engine provides tooling and infrastructure. Default is a local certificate workflow with a pluggable signer, plus a guided user flow that leads a game developer from an unsigned build to artifacts signed with a publicly accepted CA or their own CA. |
| Q58.1 | Plain Kubernetes probes and StatefulSets for the single shard now; an Agones mapping as an adapter later. The orchestration contract stays an adapter, so Kubernetes is the first target, not a hard dependency. |
| Q58.2 | A Linux toolchain (clang on Ubuntu) enters CI as soon as W58.2 lands; no earlier date. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q58.1 | Orchestration target: Agones (session servers) or plain Kubernetes StatefulSets for the single shard? | W58.1 | Plain probes now; Agones mapping as an adapter later |
| Q58.2 | Linux server target: when is a Linux toolchain acceptable in CI (clang on Ubuntu)? | W58.1, W62.1 | As soon as W58.2 lands; no earlier date |
| Q53.1 | Game modules in shipping: statically linked or DLLs? | W53.1 | Static in shipping, DLL in development |
| Q53.2 | Signing: Azure Artifact Signing or a local certificate workflow? | W53.1 | Local certificate workflow with a pluggable signer |
