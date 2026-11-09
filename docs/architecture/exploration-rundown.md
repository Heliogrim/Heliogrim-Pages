# Exploration Rundown (First Pass)

**Status**: working summary for brainstorming. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md).

**Date**: 2026-11-04. Covers the five exploration pages written from Gemini conversations (sections 2.1 to 2.5) and the two added later that day (table rows 4b and 4c), checked against the source and the vendored libraries where noted. Engine code was not re-checked beyond what is cited.

## 1. Priorities

| # | Topic | Priority | Why now | Page |
|---|---|---|---|---|
| 1 | Pointer sets | **Closed: keep ankerl** (2026-11-04) | Custom container dropped after measurement; no maintenance burden | [pointer-sets-exploration.md](pointer-sets-exploration.md) |
| 2 | Storage engine | P2, design | All I/O synchronous; resolver stack rebuilt per call; async paths are `todo_panic` | [storage-exploration.md](storage-exploration.md) |
| 3 | Serializer evolution and VCS | P1, design | No schema versioning at all; unknown slot types not skippable; 9-byte headers on every key | [serialization-evolution-exploration.md](serialization-evolution-exploration.md) |
| 4 | Scripting runtime (C#) | P3, decision | Native AOT vs HMR must be chosen before any script work | [scripting-runtime-exploration.md](scripting-runtime-exploration.md) |
| 4b | Scripting by native codegen (added 2026-11-04) | P3, decision | Owner-favoured route for visual scripts: graph IR to C++; needs reflection backend, module-swap experiment; C++26 DIS failed, no clang reflection | [scripting-native-codegen-exploration.md](scripting-native-codegen-exploration.md) |
| 4c | Fiber scheduler iteration (added 2026-11-04) | P1, design | Waiting is polled, `waitOnAtomic` blocks workers, no task dependencies; prerequisite for storage, scripting and spans | [fiber-scheduler-exploration.md](fiber-scheduler-exploration.md) |
| 5 | Observability and profiling | P3, design | Profiler, stopwatch and macros dropped (decided 2026-11-04); built from the ground up | [observability-exploration.md](observability-exploration.md) |

## 2. Per-Topic Summary

### 2.1 Pointer sets (closed 2026-11-04)

- **Claim.** A small-N pointer set can beat ankerl on contains and traversal using a dense array with SIMD scan below a threshold and a fingerprinted index above it.
- **Checked.** ankerl's default `T*` hash is wyhash-mixed, so "use an identity hash" is not a fix for the baseline. `values()` is used by callers and must be kept. About 110 files depend on the aliases.
- **Proposed change.** Build PtrSet as a standalone type with a harness first (P0), then P1 and P2 as defined in the page. Decide later whether DenseSet gets inline storage as a new type or a fifth parameter.
- **Decisions needed.** Owner of the parity implementation (not found in either worktree). Threshold values. Acceptable regression limits. Whether erase order may change.

### 2.2 Storage engine (P2)

- **Claim.** Dedicated I/O threads, io_uring batching with LBA coalescing, hardware decompression and NVMe-to-GPU DMA give maximum throughput. Fetch and mutate stay as the general API; a fluent pipeline builder compiles to the same core.
- **Checked against the code (as described by the owner).** Guards and mutation compaction exist. Stack caching exists. The 2026-11-04 page records that the Windows backend is missing.
- **Problems found.**
  - io_uring is Linux-only. The engine targets Windows first, so IOCP or overlapped I/O needs a design.
  - The source's mutation order invalidates the cache before commit. A concurrent fetch can re-cache old data. Fix: invalidate after commit under the write lock.
  - Cached stacks hold file handles that in-flight guards may still use.
  - Intel IAA is on Xeon server parts only, not desktop. GPUDirect Storage is NVIDIA-only.
  - LBA sorting helps only within one file. Queue depth probably matters more on NVMe.
- **Proposed change.** Write a Windows backend design and a benchmark for coalescing before any io_uring work. Keep the fetch and mutate API as the first target; the pipeline builder comes after.
- **Decisions needed.** Target hardware matrix. Whether coalescing is worth building before it is measured. Who owns the Windows backend.

### 2.3 Serializer evolution and VCS (P1)

- **Claim.** Size-skipping gives forward compatibility; versioned upcasters give backward compatibility; a text manifest plus content-addressed blobs suits Git; cooked packages stay out of Git.
- **Checked.** The owner's current package format (fixed header offsets, index table with archive GUIDs, URL schemes) is consistent with the advice. The package layout PDF was not provided.
- **Problems found.**
  - Missing rule: records the reader does not understand must survive a load-edit-save round trip. Without it, an older editor silently drops newer fields.
  - Checksums are per package in the current design. Per-record checksums are needed for skipped records.
  - "Git LFS never duplicates storage" overstates content hashing. A changed blob is a new object.
  - `textconv` helps `git diff` only; it does not help merges.
- **Proposed change.** Add the round-trip rule and per-record checksums to the format spec. Draft the canonical text form. Wait for the PDF before fixing index and TOC details.
- **Decisions needed.** Manifest format (JSON, YAML, or the project's own text KV). Whether upcasters run lazily or at load. How GUIDs are assigned for duplicate imports.

### 2.4 Scripting runtime (P3)

- **Claim.** Embedded C# (favoured) with custom awaitables maps `await` onto fiber suspension, so user code never blocks an OS thread. Scoped access tokens and Roslyn analyzers enforce time windows and declared read/write sets. WASM is a poor fit for in-process use.
- **Problems found.**
  - Native AOT cannot load or unload assemblies at runtime. The source recommends both AOT and AssemblyLoadContext HMR. One must go, per build profile.
  - "Stack-friendly" async is overstated. A suspending async method still allocates its state machine unless the builder pools it.
  - A `GCHandle` per yield is an allocation and a pin per yield. Pool the handles.
  - BCL `Task` and the thread pool bypass the fiber model. Ban them in analyzers and check at runtime.
  - Analyzers can prove only declared fields, not side effects through calls.
  - The COOP/COEP header argument applies to browsers, not native Wasmtime.
- **Proposed change.** Decide JIT versus AOT first. Prototype the awaiter with one yield path and measure allocations per yield before designing the analyzers.
- **Decisions needed.** .NET runtime model. Whether editor and game share one runtime. Mod sandbox (WASM, a separate process, or trusted C# only).

### 2.5 Observability and profiling (P3)

- **Claim.** A fiber-aware span design with a macro-free API, lock-free per-lane ring buffers, a single-branch inactive gate, and tiered builds (Retail, Playtest, Profile). Export to OpenTelemetry for servers.
- **Checked.** Session notes (2026-11-03): the current JSON trace profiler is to be dropped, and the audio design keeps only a hook. The source's sketches do not compile as written (compile-time name metadata uses a runtime parameter).
- **Problems found.**
  - Spans toggled mid-scope can unbalance. Use a depth counter or per-span token.
  - `__rdtsc` must be wrapped per compiler.
  - The "sub-nanosecond overhead" and tool comparisons rely on a blog post, not a primary source. Measure our own overhead.
- **Proposed change.** Define the span API and the ring buffer contract first, with a micro-benchmark of the inactive gate. Leave OTel for later.
- **Decisions needed.** Where the fiber-local context lives (stack or control block). Buffer overflow policy. Whether the metered-run mode is in scope.

## 3. Cross-Cutting Themes

- **Fiber-aware everywhere.** Storage resume, script yields and profiler spans all need the fiber identity, and fibers migrate between threads. One shared fiber-context definition would serve all three. Today `Fiber` has no identity or context field, and `FiberAwaitable` is a bare `atomic_flag`; neither can be awaited on an I/O completion without polling.
- **Measure before design.** Four of five pages hold claims the source did not measure. The pointer-set harness is the first one to exist.
- **Keep the decision trail.** Each accepted outcome goes to an ADR; the exploration pages stay as the record of options rejected.

## 4. Proposed Order of Work

Revised 2026-11-04 after checking each page against the source (each page now has a "Current state in engine" section).

1. Serializer: schema versioning per type, skippable tags, dense encoding (MessagePack-style fix forms, ext payloads in native layout, key interning), round-trip rule and per-record checksums. Nothing of the versioning exists yet; package and archive version slots are unused.
2. Shared fiber context and fiber-suspending await on an external completion. Prerequisite for async storage, C# awaiters and fiber-aware spans.
3. Storage: reuse resolved stacks instead of rebuilding them per call, then a first async query path on (2). Windows batching backend and coalescing stay vision until measured.
4. Observability from the ground up (old profiler dropped): span API on the fiber context, ring buffer contract, gate micro-benchmark.
5. Scripting JIT versus AOT decision. No runtime exists; nothing blocks on it until (2) is in place.

Section 2 summaries predate this check; the per-page "current state" sections take precedence.

## 5. Brainstorm Agenda

- Pointer-set thresholds and whether to keep erase order.
- Inline DenseSet: new type or fifth parameter.
- Runtime model for C# (JIT or AOT) and the mod sandbox.
- Windows storage backend: IOCP or overlapped I/O, and the batching rule.
- Shared fiber-context definition across storage, scripting and profiling.
- Fiber scheduler: `Waitable` and wake lists first, then dependencies; coroutine bridge model (A or B); EEVDF only for a background lane if starvation is measured. See [fiber-scheduler-exploration.md](fiber-scheduler-exploration.md).
- Native codegen: reflection backend on clang-cl, module swap versus in-process JIT, and whether C# stays alongside.
