# Scripting Runtime and User Code (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

**Origin**: distilled on 2026-11-04 from a Gemini conversation about WASM and C# ([link](https://gemini.google.com/app/13214d48359e938b)). The raw notes are not kept. Claims were not re-verified in this pass.

## 0. Current State in Engine (checked 2026-11-04)

- No scripting runtime exists: no .NET hosting (`hostfxr`, `nethost`), no Mono and no WASM runtime, in either `src` or `vendor`.
- Fibers are Win32 fibers (`CreateFiber`, `ConvertThreadToFiber` in `Engine.Scheduler`). `Fiber` holds `handle`, `parent`, `task` and one `FiberAwaitable`. The awaitable is an `std::atomic_flag` signal or a `bool await()` call, and carries no metadata.
- A C# awaiter would map onto `fiber::await(FiberAwaitable)`. "Yield with metadata" (section 2) needs a new field on `Fiber` or on the awaitable.

## 1. Direction

- C++23 is first-class for engine and game code.
- **C# is the favoured scripting language**, embedded in process.
- WASM is a poor fit for the in-process, highly concurrent core. The conversation concluded that its FFI cost and duplicated data structures outweigh its isolation. Keep WASM as a possible route for untrusted third-party mods only, decided later.

- **Update 2026-11-04**: a second conversation narrowed the visual-scripting route to generated native C++ (graph, IR, C++ emitter, module swap or JIT in the editor, LTO in shipping). That is the owner's favoured direction for visual scripts; see [Scripting by native code generation](scripting-native-codegen-exploration.md). Whether C# stays for programmer scripting is open. Sections below describe the C# route only.

## 2. Ideas Carried Forward

- **Custom awaitables and an async method builder** map C# `await` onto fiber suspension. User code never blocks an OS thread on a mutex, futex or spinlock.
- **Yield with metadata.** An awaiter passes what it waits on (an event name or ID) to the C++ side. That gives a live "fiber X waits on event Y" graph for dependency and event resolution.
- **Token-scoped component access.** Scripts get a context object valid only for the current tick window. Access outside the window fails a check in debug and profile builds.
- **Pipeline-phase guard.** Each component chunk has a state (unlocked, exclusively locked, script executing). Access outside the script phase is diagnosed.
- **Roslyn analyzers** enforce declared read and write sets (`[Reads]`, `[Writes]`), ban blocking APIs in gameplay assemblies, and flag references that escape a tick.
- **HMR at yield boundaries.** Reload assemblies only where a fiber is suspended at an awaitable, never mid-method.
- **Pure systems** (one component, no side effects) can be scheduled in parallel. The profiler reports contention, and can mark scripts safe for the fiber pool.

## 3. Problems to Resolve Before Design

- **Native AOT and HMR conflict.** The conversation recommended both Native AOT and `AssemblyLoadContext` reloads. Native AOT does not load new assemblies at runtime or unload them. Pick one: a JIT runtime with HMR, or Native AOT for shipping. Decide per build profile.
- **"Stack-friendly" async is overstated.** A C# async method that suspends still allocates its state machine on the heap, unless the builder pools it. Measure allocations per yield.
- **Every yield pins a `GCHandle`** in the sketch. That is one allocation and handle per yield. Use a pooled handle table.
- **BCL `Task` escapes the fiber model.** `Task.Run`, `Task.Delay` and similar APIs use the .NET thread pool. Ban them with the analyzer and add a runtime check that continuations resume on a fiber.
- **Analyzers prove only declared fields.** A Roslyn check can verify reads and writes to declared components. It cannot prove the absence of side effects through called methods. Limit the "parallel-safe" claim to what the analyzer can see.
- **WASM browser constraints.** The COOP and COEP header requirement applies to browsers, not to native hosts such as Wasmtime. The source mixes the two. The FFI-cost argument still stands for in-process use.
- **`emscripten_stack_get_current` is not a fiber API.** Do not plan on it.

## 4. Open Questions

- Which .NET version and runtime model (JIT or Native AOT) for editor and game.
- Whether the editor and the game share one managed runtime.
- Access token and time-window checks: which ones stay in release builds, and which are debug-only.
- Whether node graphs compile to C# or run in their own interpreter. The metrics and replay ideas depend on this.
- Mod sandbox: WASM, a separate process, or trusted-only C#.

## 5. Related

- [Actor system](actor-system.md): tick stages and the component model.
- [Observability](observability-exploration.md): invocation spans and VM boundary probes.
- [Pointer sets](pointer-sets-exploration.md): lookup structures for component references.
