# Target Architecture

**Status**: <span class="hg-status summary">plan</span>. The shape the systems in this plan must fit. It extends the current layering (see [`ARCHITECTURE.md`](https://github.com/Heliogrim/Heliogrim-Engine/blob/master/ARCHITECTURE.md) in the engine and the generated [module map](../architecture/modules.md)); it does not describe what runs today. Checked against the source on 2026-11-07.

## 1. Principles

1. **One engine, many process roles.** The same bundles link into the editor, the game client, a dedicated server, a worker and a cluster node. A role is a configuration plus a set of enabled root modules, not a separate code base.
2. **Fibers for work, threads for waiting.** Engine and game logic run as tasks on a fiber scheduler with declared dependencies. Anything that blocks (disk, network sockets, the platform message pump, the audio device, GPU fences) runs on a dedicated thread and completes into the scheduler through a waitable. No fiber ever blocks a worker thread.
3. **Systems map pushed components to internal models.** The `SceneSystem` pattern (scene components are registered, a system builds and updates its own model) is the integration contract for rendering, physics, audio, navigation, picking and streaming. Systems do not reach into each other's models; they share query services.
4. **Everything is observable and diagnosable.** Each subsystem emits spans, counters and structured diagnostics through the same two interfaces. A failure returns a `Diagnostic` with a code and a fix hint; it never logs a string and continues.
5. **Data is versioned, content-addressed and VCS-friendly.** Every serialised record carries a schema version; packages are content-addressed; editable assets have a canonical text form.
6. **Determinism is a mode, not an accident.** Simulation code is written so that a deterministic build (fixed step, seeded RNG, strict FP, ordered reductions) is a configuration switch.
7. **The shader language is the only shader source.** ASL compiles through its own IR to SPIR-V. Materials, post effects, particles, UI and compute all go through it; the engine never embeds GLSL.

## 2. Layers

```hg-diagram
flowchart TB
    subgraph L5["Applications"]
        ED["Editor.* (tools, panels, actions)"]
        GM["Game project (user C++, plugins)"]
        SV["Server / worker roles"]
    end
    subgraph L4["Engine public surface"]
        HG["Heliogrim (public API, actor classes, glue)"]
    end
    subgraph L3["Domain systems"]
        GFX["Rendering: GFX, Accel, Render graph, Materials"]
        SIM["Simulation: ACS, Scene, Physics, Animation, Navigation, PFX"]
        WLD["World: Level/Partition, Terrain, Ocean, Weather, Procedural"]
        AUD["Audio"]
        NET["Network, Replication"]
        UI["Reflow, Uikit, Canvas"]
    end
    subgraph L2["Services"]
        RES["Assets, Resource, Storage, Streaming"]
        SER["Serialization, Reflect"]
        SCH["Scheduler, Async, IO dispatch"]
        OBS["Diagnostics, Logging, Observability, Crash"]
        INP["Input"]
    end
    subgraph L1["Foundation"]
        COM["Common, Math, Containers, Managed pointers"]
        PLT["Platform, Env, Config, Filesystem, Crypto"]
        DRV["Driver.Vulkan"]
    end
    L5 --> L4 --> L3 --> L2 --> L1
```

Rules between layers:

- A layer may include only layers below it. `Heliogrim` is the only public surface game code sees; editor code may use domain systems directly.
- Domain systems may not include each other. Cross-system needs go through a service in L2 or a query interface registered on the scene (bounds queries, height queries, wind field).
- `Driver.Vulkan` is included by rendering bundles only. No other layer names a Vulkan type.
- Tests are sibling bundles and may include anything.

The generated module map shows these rules are violated today in places (for example `Engine.Assets.Type` reaching into `GFX.Material`, `Reflow` and `SFX`, and `Engine.Reflow` depending on `GFX` and `Render.Scene`). The [modules page](modules.md) lists the moves.

## 3. Process roles

| Role | Root modules enabled | Render device | Threads besides workers |
|------|---------------------|---------------|-------------------------|
| Editor | all engine systems, editor UI, actions, importers, test driver | Vulkan | platform pump, IO, audio, file watcher |
| Game client | engine systems, game modules | Vulkan | platform pump, IO, audio, network |
| Dedicated server | simulation, world, navigation, network, replication, persistence | null device (no swapchain, no GPU; optional GPU for server-side baking) | IO, network, persistence |
| Worker | asset cooking, baking (lightmaps, navmesh, procedural), shader compilation | optional GPU | IO |
| Cluster node | server role plus mesh membership, handover, telemetry export | null device | IO, network, mesh control |

The role is chosen by configuration at start (`Engine.Config`), and every system checks capability flags (has GPU, has audio, has window) instead of the role name. Headless is the absence of window and GPU capabilities, nothing more.

## 4. Execution model

```hg-diagram
flowchart LR
    PUMP["Platform thread<br/>message pump, window events"] -->|events| INQ["Input queue"]
    IO["IO threads<br/>IOCP / DirectStorage"] -->|completions| WT["Waitables"]
    NETT["Network thread<br/>sockets, QUIC"] -->|packets| WT
    AUDT["Audio thread<br/>device callback"] <-->|lock-free queues| AUDS["Audio system"]
    GPU["GPU queues"] -->|fences| WT
    subgraph SCHED["Fiber scheduler (N workers)"]
        TG["Task graph per frame<br/>declared read/write sets"]
        TG --> S1["Input"] --> S2["Simulation stages<br/>(ACS, physics, animation, nav)"] --> S3["Scene mirror<br/>(systems update models)"] --> S4["Render graph compile + record"] --> S5["Submit"]
    end
    INQ --> S1
    WT --> TG
```

- A frame is a task graph. Stages declare what they read and write (the explicit DAG dependencies the archetype design asked for); the scheduler orders and parallelises them. Systems that are independent (audio update, navigation tile builds, streaming decode) run as tasks outside the frame-critical path with lower priority.
- Waiting is explicit: a task awaits a waitable (IO completion, fence, timer, another task) and the fiber yields; the worker picks up other work. The [fiber scheduler exploration](../architecture/fiber-scheduler-exploration.md) records the gaps in today's scheduler.
- A deterministic mode runs the same graph with a fixed step and a fixed worker count, with reductions ordered by task ID. Replay feeds recorded inputs and waitable completions in order.
- Long-running jobs (cooking, DAG building, navmesh baking) use the same scheduler in worker roles, with priority lanes so interactive work stays responsive in the editor.

## 5. Data flow

### Assets and streaming

```hg-diagram
flowchart LR
    SRC["Source files<br/>(DCC exports, images, audio)"] -->|import| AST["Asset database<br/>GUID, type, tags, references"]
    AST -->|cook| PKG["Packages<br/>content-addressed archives"]
    PKG -->|stream| RES["Resource residency<br/>budgets, LRU, priorities"]
    RES --> GPU["GPU resources<br/>virtual textures, geometry pages"]
    RES --> CPU["CPU resources<br/>meshes, animation, audio, navmesh tiles"]
    WATCH["File watcher"] -->|reimport| AST
```

- Import is deterministic and GUID-preserving; a reimport replaces content, never identity.
- Streaming is request-based with priorities and cancellation; requests are issued by systems (renderer feedback for virtual textures and geometry pages, world partition for cells, audio for banks) and fulfilled by the storage backend on IO threads.
- Residency is budgeted per resource class; eviction is observable.

### Scene and rendering

- Game state lives in actor archetypes per world-partition cell. Scene systems mirror components into models. The render scene is one such model; it is GPU-resident (instance, material and geometry tables) so the GPU-driven pipeline culls and draws without per-object CPU work.
- The render graph is compiled per frame from pass declarations and shader interfaces (ASL exports the resources a pass reads and writes); barriers and transient aliasing are derived, not written by hand. Material and feature requirements propagate up into pass enablement ([brainstorm](../architecture/exploration-rundown.md)).
- World positions are double on the CPU; the render scene stores camera-relative float positions rebuilt when the camera origin moves.

### Networking

- The server simulates authoritatively per cell; clients predict locally and reconcile against snapshots. Replication is a scene system like any other: it mirrors replicated components into a network model and emits deltas by interest.
- Transport is a separate layer (QUIC-based for sessions and HTTP, custom UDP for the real-time channel) with one API for both.

## 6. Cross-cutting services

| Service | Contract | Consumers |
|---------|----------|-----------|
| Diagnostics | `Diagnostic { code, severity, message, spans/paths, notes, fixes }`, result types carry it | every system, ASL compiler, importers, editor panels |
| Observability | spans with fiber context, counters, ring-buffer trace, export | profiler UI, CI gates, server telemetry |
| Reflection | type identity stable across module reloads, fields, attributes, functions | serialisation, HMR, visual scripting, property panels, asset search |
| Serialisation | versioned records, skippable unknown fields, text and binary forms | assets, levels, undo log, replication, replay |
| Query services | bounds queries (ray, frustum, overlap), height/wind/weather sampling | picking, physics, audio, foliage, ocean, navigation |
| Input | contexts, actions, arbitration between UI, editor tools and game | editor, uikit, game, test driver |

## 7. What changes relative to today

| Today (checked 2026-11-07) | Target |
|-----------------------------|--------|
| `Level` is the actor handle space; no streaming cells | World partition cells own archetype regions and stream |
| Scheduler ticks fibers with polling waits; no task dependencies | Task graph with waitables; IO and platform threads bridge in |
| Storage is synchronous; async paths are `todo_panic` ([storage exploration](../architecture/storage-exploration.md)) | Request-based async storage on IOCP or DirectStorage |
| Serialisation has no schema versions ([serialization exploration](../architecture/serialization-evolution-exploration.md)) | Versioned, skippable, text-form-capable |
| ASL emits GLSL gated by glslang; graphics pipelines only in `Accel.Pipeline` | ASL emits SPIR-V directly; all pipeline kinds |
| Render graph exists (`Engine.GFX.RenderGraph`, ~6k lines) but passes are hand-wired (`Render.Subpass/Impl`) | Declarative passes, derived barriers, aliasing, GPU-driven scene |
| Float world positions | Double world, camera-relative rendering |
| `Engine.Network`: 48 lines; `Engine.Crypto`: CRC32 only | Transport, replication, TLS/QUIC, hashing |
| `Engine.PFX` wraps Jolt init; two shape models | Full Jolt integration, deterministic mode, characters, vehicles |
| `Engine.SFX`: importers only (WAV, FLAC, Vorbis) | Audio runtime per [design](../architecture/audio-runtime-design.md) |
| Reflow draws text from a bitmap atlas as CPU geometry | SDF/MSDF canvas, shaped text |
| Editor actions: `ActionManager`, `ActionLog`, delegate and import actions; reapply path broken (bug 12 in test notes) | Transactional undo/redo across objects and assets |
| No crash handler, no diagnostics type, profiler dropped | Crashpad-style dumps, `Diagnostic`, spans |
