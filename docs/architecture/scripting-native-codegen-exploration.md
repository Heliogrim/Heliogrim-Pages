# Scripting by Native Code Generation (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

**Origin**: distilled on 2026-11-04 from a Gemini conversation about scripting architecture ([link](https://gemini.google.com/app/1ad9330118d3e4f5)). The raw notes are not kept. Claims were checked against the source and by a first research pass (section 4). Items marked *unverified* have no primary source yet.

**Owner leaning**: the generative C++ approach (section 1) is the favoured direction. It narrows [Scripting runtime](scripting-runtime-exploration.md), which favoured embedded C#; how the two relate is open (section 6).

## 0. Current State in Engine (checked 2026-11-04)

- **Toolchain**: clang-cl 22.1.3 (VS 2026 bundled LLVM), C++23, MSVC STL. No C++26 features in use.
- **No coroutines, no generators**: no `co_await`, `co_yield`, `<coroutine>` or `<generator>` in `src`. Concurrency is Win32 fibers in `Engine.Scheduler` (see the scripting runtime page), not C++ coroutine frames.
- **No dynamic code loading**: no `LoadLibrary`, `dlopen` or plugin boundary. Game code is linked into the executable. HMR has nothing to build on yet.
- **Reflection is type identity only**: `Engine.Reflect` offers `TypeId`, `MetaClass`, inheritance queries and a type switch. There is no member, field or function enumeration, no annotations, no invoke. "Reflection and introspection metadata" from the conversation does not exist.
- **Phases exist as stage ordering only**: `Engine.ACS.Schedule` defines named stages (`ActorTickPrePhysics`, `Physics::Overlap`, `Collision`, `PostPhysics`, `ActorHousekeeping`) on `StagePipeline` with `StageDependency`. Stages order work; they declare no read or write sets, so there is no hazard tracking and no mutation barrier or command buffer for actors. `ActorTickStage` is still a `TODO`.
- **A node graph and a text emitter already exist, for shaders**: `Editor.Graphics.Graphs` has a typed node graph (math, input, output, sub-graph nodes) and `Engine.Accel.Lang` has `Emitter`, `Dialect`, a parser, an IR with `Analysis`, `Contract`, `Lower` and a `GlslEmitter`. That is a working precedent for "graph, then IR, then emitted text", and the shape the C++ emitter would take. It targets GLSL, not C++.

## 1. Direction (Owner Leaning)

Visual scripts are a visual syntax for native code, not a runtime language:

`node graph -> typed graph IR -> checks (DAG, effects, phases) -> C++ emitter -> native`

- **Editor**: emitted C++ goes to a compile-and-swap path (out-of-process compile to a module, or in-process JIT), swapping a function table.
- **Shipping**: the same emitted source is compiled with the rest of the engine, with LTO.
- **Logic is stateless kernels over component state.** State lives in engine storage, so a reload replaces code only.
- **No second runtime and no bytecode VM** on this path. A VM stays a possible fallback tier only (section 3).

## 2. Ideas Carried Forward

- **Graph IR is the real product.** Verification, effect checking and emission all hang off one typed IR. Reuse the `Engine.Accel.Lang` structure (IR, analysis, lowering, emitters) rather than invent another.
- **Side-effect classes per node** (pure read, local mutation, structural command), checked at graph-edit time. Structural commands go to a command buffer flushed at a phase barrier. Needs read/write set declarations on stages first (section 0).
- **Stateless kernels plus external state** as the HMR contract. A reload swaps code, never data.
- **Reload only at safe points.** No kernel on any fiber stack or suspended coroutine while a module is replaced.
- **Batched execution over component chunks** for numeric logic: iterate a slice, not one entity at a time.
- **Narrow introspection seam** (a field list with names and types) so a later `std::meta` backend replaces a generator without touching the graph compiler.
- **Headless deterministic run** of generated kernels for unit tests.

## 3. Claims Against Source and Research

| Claim | Verdict | Note |
|---|---|---|
| Engine fibers use C++23 coroutines | Refuted | Win32 fibers; no coroutines in `src`. |
| A reflection system exposes functions, fields and annotations | Refuted for engine | Only type identity exists. Reflection backend is new work. |
| Phases and a mutation barrier exist to build on | Partly | Named stages exist; no read/write declarations, no command buffers. |
| C++26 is finalized | Refuted | The ISO DIS ballot closed 2026-10-23 as disapproved. Contracts were the main objection. The 2026-11-16 WG21 meeting may change or remove them. Sources: [Fertig](https://andreasfertig.com/blog/2026/11/cpp26-dis-failed-how-does-cpp-survive/) (secondary), [Train-IT](https://train-it.eu/blog/cpp26-contracts-the-ballot-result/), [Sutter trip report](https://herbsutter.com/2026/03/29/c26-is-done-trip-report-march-2026-iso-c-standards-meeting-london-croydon-uk/). |
| GCC 16 has reflection, contracts, `template for` | Confirmed | [GCC 16 changes](https://gcc.gnu.org/gcc-16/changes.html): P2996, P3394, P3096, P2900, P1306. Reflection needs `-freflection`. |
| Clang has reflection or contracts | Refuted | [cxx_status](https://clang.llvm.org/cxx_status.html): no reflection, no contracts. `template for` partial in Clang 23, `#embed` Clang 24. The Bloomberg fork is experimental and not for production. |
| MSVC has no `std::meta` | Confirmed (by absence) | No P2996, P2900 or P1306 row in the [conformance table](https://learn.microsoft.com/en-us/cpp/overview/visual-cpp-language-conformance), updated 2026-10-16. |
| Contracts give compile-time verification and branch elimination | Refuted | Semantics are ignore, observe, enforce, quick-enforce; nothing is proven statically, and the predicate may be evaluated zero or several times ([cppreference](https://en.cppreference.com/w/cpp/language/contracts), from P2900R14). |
| Switch to C++26 takes "days" behind an interface | Unverified | The interface only works if it exposes plain data (fields, names, types). Splicing and code injection have no C++23 equivalent. No Clang release date for reflection, so clang-cl has no path soon. |
| `std::generator` is usable | Partly | In MSVC STL since 19.43; no `__clang__` gate in the STL source, not verified on clang-cl. Test on our toolchain. |
| ORC JIT compiles "in milliseconds" | Unverified, doubtful | No latency data found. Parsing engine headers dominates a small TU, so PCH or modules decide. |
| JIT on Windows works (COFF, SEH, debug info) | Partly | JITLink rates COFF x86-64 "Usable", below ELF and MachO ([docs](https://llvm.org/docs/JITLink.html)). SEH registration exists in the ORC runtime ([D130479](https://reviews.llvm.org/D130479)), untested here. No evidence of CodeView or PDB for JIT'd code, so debugging is likely to need extra work. |
| Out-of-process compile plus module swap is viable | Confirmed | Live++ patches from recompiled objects; structural changes (class layout, vtables) are not migrated; LTO/LTCG unsupported; stack objects not migrated ([Live++ docs](https://liveplusplus.tech/docs/documentation.html)). Unreal Live Coding is Live++-based and says large structural edits often crash without reinstancing. |
| A compiler flattens a graph into SIMD loops across entities | Partly | Only for numeric SoA loops without aliasing, early exits or gather. Burst needs `[NoAlias]` and a branch-free loop ([Burst](https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/optimization-loop-vectorization.html)). Bevy added an explicit contiguous iterator to get vectorization. No evidence for branchy gameplay logic. |
| Computed goto cuts mispredictions by up to 50% | Folklore | Rohou et al., CGO 2015: on Haswell-class CPUs indirect prediction is no longer critical (abstract only read). CPython 3.14 tail-call interpreter gains 3-5%. Irrelevant for the first tier. |
| Verse effects let the runtime run blocks in parallel because the compiler proves disjointness | Partly | The [effects page](https://verselang.github.io/book/13_effects/) states functions without `<writes>` can run in parallel without locks. [Concurrency](https://verselang.github.io/book/14_concurrency/) is cooperative and abstracts threading away. Nothing found that proves disjointness of data. |
| Mach, Bevy and AAA R&D "abandoned runtime translation" | Unsupported | Mach is Zig, Bevy is Rust; neither tells anything about visual script translation. Probably invented framing. |
| Blueprint nativization is prior art that worked | Refuted | Removed in UE 5.0 ([release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5.0-release-notes?application_version=5.0)). No official reason found; the maintenance-cost explanation is unverified. This is the closest prior art and must be understood before committing. |

## 4. Problems to Resolve Before Design

- **Reflection backend must exist first.** Without field enumeration the emitter cannot map nodes to engine types. Options: a generator step, macro registration, or waiting for `std::meta` (GCC only today). Pick a backend that survives on clang-cl.
- **Suspended work across a reload.** A coroutine frame holds raw resume and destroy pointers into its module; a fiber stack holds return addresses. Unloading the module leaves them dangling. Inference from the LLVM coroutine docs, no primary source on hot reload. Mitigations: drain before swap, keep suspendable code in a never-reloaded module, or serialize and restart.
- **vtables, RTTI, statics across reload.** Live++ treats vtable and layout changes as structural. Static initializers in swapped code are a known gap with Clang. Kernels should be free functions without statics or virtuals.
- **Layout change of component state.** The stateless-kernel contract breaks when a component struct changes. Needs a migration or a reload-forbidden rule.
- **Debuggability.** The conversation promised native breakpoints in generated code. With in-process JIT on Windows this is unproven. An out-of-process module with normal PDBs avoids it.
- **LTO and hot patching exclude each other.** The AOT path gets LTO, the editor path cannot.
- **Cost of the toolchain.** Embedding LLVM plus Clang is large and unmeasured here. A separately invoked clang-cl is cheaper to start with.
- **Verification is a graph pass, not a contract feature.** Effect, phase and DAG checks run on the graph IR (plain code or SMT). Running CBMC or the Clang analyzer on emitted C++ is possible but noisy. Contracts are runtime checks at best.
- **Gaming the benchmark.** Blueprint nativization was dropped; the speed-up must be measured on real gameplay graphs, not on math nodes.

## 5. First Experiments

1. Hand-write one emitted kernel for one component and swap it through a module on clang-cl. Measure compile-and-link latency with and without PCH.
2. Prototype the graph IR for a tiny node set by extending the `Engine.Accel.Lang` shape, with a C++ emitter beside `GlslEmitter`.
3. Add read/write set declarations to one stage pipeline and a command buffer for structural changes (shared with the actor system work).
4. Test `std::generator` and a simple coroutine on clang-cl 22 with the MSVC STL.
5. List what is needed from a reflection seam: fields, names, types, annotations.

## 6. Open Questions

- C# alongside, or dropped? If kept, it takes the role of programmer scripting and external users, while visual scripts emit C++. See [Scripting runtime](scripting-runtime-exploration.md).
- Out-of-process module swap or in-process JIT for the editor.
- Reflection backend until clang-cl has `std::meta`: generator, macros, or a GCC-only pipeline step.
- Does shipping need user-authored scripts at all, or only editor-time graphs baked into the build.
- Where the phase and effect declarations live: stage, system or node.
- Mod story: native code from untrusted users is not sandboxable; a separate route is needed.
- Wait for the 2026-11-16 WG21 outcome before relying on contracts.

## 7. Not Researched Yet

Flax, Stride, IL2CPP; flecs, EnTT and Mass measurements; RTTI identity across reload; Live++ patching internals and stack handling; `[[clang::musttail]]` limits on Windows x64; embedded LLVM size and latency; clang-cl coroutine bugs (only issue reports found, no primary source).

## 8. Related

- [Scripting runtime](scripting-runtime-exploration.md): C# route, fiber awaiters, analyzers.
- [Actor system](actor-system.md): tick stages and component model.
- [Observability](observability-exploration.md): spans around kernel invocation.
