# Work: Visual Scripting Compiler and C++ Hot Module Reload

**Systems** S47, S48 · **Issues** [#127](https://github.com/Heliogrim/Heliogrim-Engine/issues/127), [#128](https://github.com/Heliogrim/Heliogrim-Engine/issues/128) · **Track** D · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Visual scripting and hot reload](../topics/visual-scripting-hmr.md).

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Scripting by native codegen exploration](../../architecture/scripting-native-codegen-exploration.md) | Direction: graph → typed IR → checks → C++ emitter → native; stateless kernels over component state; no bytecode VM on this path; C++26 reflection not available on clang-cl; reflection backend is new work (S09); ORC JIT latency unverified | C# alongside or dropped; out-of-process module swap versus in-process JIT; reflection backend mechanism; shipping needs scripts at all; where phase and effect declarations live; mod story |
| [Scripting runtime exploration](../../architecture/scripting-runtime-exploration.md) | Embedded C# problems (AOT versus HMR, allocations per yield, BCL `Task` bypasses fibers) | Vision page lists a managed runtime as a non-goal for now; W47.0 records that as the decision proposal |
| Live++ documentation (verified in the research pass) | Flags needed; structural changes not migrated; pre and post patch hooks; pricing | Licence versus in-house patcher (Q48.1) |
| [Reflection work](serialization-and-reflection.md) S09 | Hashed `TypeId`, functions, attributes | Required for both systems |
| [Serialisation work](serialization-and-reflection.md) S01 | Upcasters | Migration format for tier 2 |
| [Memory model](storage-streaming.md) S08 | Engine owns allocators | DLL never owns memory that outlives it |
| [Build work](build-and-deploy.md) S53 | Engine SDK export, module layout | Game modules are DLLs in development |
| [Particles](particles-foliage.md), [animation](animation.md), [procedural](procedural-generation.md), [materials](materials-post.md) | Each wants the graph compiler | Emitter order: C++ first, ASL second, node programs third |

## Architecture

- **Bundles**: new `Engine.Graph.Ir` (typed graph IR, validation, lowering), `Engine.Graph.Emit.Cpp`, `Engine.Graph.Emit.Asl`, `Engine.Graph.Interp` (editor iteration), `Editor.Graphs` (authoring on `Editor.GFX.Graphs` node definitions, source map navigation). New `Engine.HotReload` (module registry, patch tier integration, swap tier migration) and a `HotReload` build profile in CMake.
- **Provides**: compile graphs to C++ or ASL with source maps; interpret graphs; reload game modules with state preserved.
- **Consumes**: reflection (S09), diagnostics (S05), serialisation (S01), memory (S08), SDK and module layout (S53), archetype relocation barrier (#80), crash annotations (S06), replay barrier (S59).

## Code design

| Type | Contract |
|---|---|
| `GraphIr` | Typed nodes with exec and data pins; `validate() -> Diagnostics on node spans`; type inference; lowering to a structured typed IR with explicit effects (reads, writes, phase). |
| `CppEmitter` | Deterministic output (sorted iteration, stable IDs, fixed formatting), `#line` mapping to node IDs; generated files are write-only inside the game module; output passes clang-tidy. |
| `AslEmitter` | Materials to ASL modules consumed by S11. |
| `NodeProgramEmitter` | Flat node programs for particles (S24) and animation (S36). |
| `Interpreter` | Executes the same lowered IR in the editor for immediate feedback; must match emitted C++ on a fixture. |
| `ModuleDescriptor` | A game module: DLL built against the SDK; `moduleInit` registers types with content-hash identities; engine holds module code only through re-resolvable handles. |
| `PatchTier` | Function patching with the `HotReload` flag set (`-fms-hotpatch`, function sections, CodeView, no LTO); Live++ or in-house patcher per Q48.1. |
| `SwapTier` | On structural change: serialise all instances of module-owned types (S01) to a migration buffer, unload, load, re-register, run upcasters, hydrate; archetype regions relocate through the #80 barrier; a diagnostic per unmappable field. |
| `ReloadBarrier` | Frame-boundary point where swaps happen; replay (S59) and crash annotations (S06) record it. |

Placement: `Engine.Graph.Ir/`, `Engine.Graph.Emit.Cpp/`, `Engine.Graph.Emit.Asl/`, `Engine.Graph.Interp/`, `Editor.Graphs/`, `Engine.HotReload/`, `cmake/HotReloadProfile.cmake`. Tests: emitter goldens; interpreter equality; reload latency measurement; layout-change migration fixture.

## Work chunks

### W47.0 Close the scripting decisions · explore · ready

- **Goal**: record the decision proposals from both explorations: no managed runtime for now (vision non-goal), native codegen as the path, interpreter for iteration, reflection through S09 not language reflection; answer the exploration's open questions or route them to the owner.
- **Output**: decision section appended to both explorations; ADR placeholder "visual scripts compile to C++".
- **Questions**: Q47.1, Q47.2 (both decided, see Decisions).

### W47.1 Graph IR design · design · after W47.0, W09.1, W05.1

- **Goal**: IR, validation, effects and phases, lowering, emitter contracts, interpreter, source maps, build integration.
- **Output**: `architecture/graph-compiler-design.md`; plan (IR and interpreter first, C++ emitter second, ASL third, node programs fourth).

### W47.2 Implement IR, validation and interpreter · execute · after W47.1

- **Done when**: a fixture graph validates with node-span diagnostics and runs in the interpreter.

### W47.3 Implement the C++ emitter with source maps · execute · after W47.2, W53.2 (module layout)

- **Done when**: emitted C++ passes clang-tidy, runs identically to the interpreter, and a runtime diagnostic maps back to its node.

### W47.4 Implement the ASL emitter for material graphs · execute · after W47.2, W16.2

- **Done when**: a material graph emits ASL that compiles through S11 and renders.

### W48.0 HMR tier spike · explore · after W53.1 (module layout decided)

- **Goal**: set the `HotReload` flags on a test module; build a minimal in-house patch step (no Live++, Q48.1); measure reload latency; confirm what breaks (TLS, globals, stack objects).
- **Output**: `architecture/hot-reload-exploration.md` with numbers.
- **Questions**: Q48.1.

### W48.1 Hot reload design · design · after W48.0, W09.1, W01.1, W08.1

- **Output**: `architecture/hot-reload-design.md`; plan (module boundary first, patch tier second, swap tier third).
- **Questions**: Q48.2 (decided: first-party modules only).

### W48.2 Implement module boundary and patch tier · execute · after W48.1, W53.2, W09.2

- **Done when**: a changed function reloads in the running editor within the stated latency with no state loss.

### W48.3 Implement swap tier with migration · execute · after W48.2, W01.2

- **Done when**: a changed component layout reloads with instances migrated and a diagnostic for unmapped fields.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q48.1 | No licensed or paid software. In-house patcher only; Live++ is out, including the trial. W48.0 measures the in-house patch step alone. |
| Q47.1 | Confirmed for now: no C# or other managed runtime in the plan horizon; visual scripts compile to C++ (W47.0 writes the ADR placeholder). |
| Q47.2 | Interpreter is editor-only for now; emitted C++ is mandatory for a shipped build. |
| Q48.2 | First-party only: a shipped game loads only modules the game developer built and signed (including store plugins compiled into the game). Player-authored native modules are out of scope; if player content ever comes, it is data mods plus a sandboxed addon layer, decided later. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q47.1 | Confirm: no embedded C# or other managed runtime in the plan horizon; visual scripts compile to C++ only? | W47.0 | Confirm |
| Q47.2 | Does shipping include the interpreter, or is emitted C++ mandatory for a shipped build? | W47.1 | Emitted C++ mandatory; interpreter is editor-only |
| Q48.1 | Live++ licence (about EUR 12 to 20 per month per seat) acceptable, or in-house patcher only? | W48.1 | Evaluate the trial in W48.0; licence if the in-house step costs more than two weeks |
| Q48.2 | Mod story: are user-authored native modules in scope, or only first-party game modules? | W48.1 | First-party only; mods are a later decision |
