# Architecture Decision Records

ADRs are processed in the engine project. This repository documents them after they are accepted there; it does not originate them. Records are never rewritten; a newer ADR supersedes an older one and links to it.

## Accepted records

None yet. Records appear here, with the number assigned by the engine project, once processed.

## Placeholders

Drafts derived from exploration outcomes, kept so the pages have a place to land. They are **not** decisions until the engine project has processed them.

The last column says where the decision stands in the engine, checked 2026-11-10 against the engine checkout and the battle-plan issue comments of that date.

| Placeholder | Derived from | Status | Engine (2026-11-10) |
|-------------|--------------|--------|---------------------|
| [Keep `ankerl::unordered_dense` for pointer sets](placeholder-pointer-sets.md) | [Pointer sets exploration](../architecture/pointer-sets-exploration.md) | <span class="hg-status placeholder">placeholder</span> | Status quo kept; nothing to change |
| [Drop the JSON trace profiler, stopwatch and macros](placeholder-trace-profiler.md) | [Observability exploration](../architecture/observability-exploration.md) | <span class="hg-status placeholder">placeholder</span> | Not done: `Engine.Common/Profiling/{Profiler,Stopwatch}` still present; removal belongs to W04.1 |
| [Schema versioning on records](placeholder-record-schema-versioning.md) | [Serialisation work page](../plan/work/serialization-and-reflection.md) | <span class="hg-status placeholder">placeholder</span> | Not started; design chunk W01.1 ready |
| [Canonical text form as a YAML subset](placeholder-text-form-yaml.md) | [Serialisation work page](../plan/work/serialization-and-reflection.md) | <span class="hg-status placeholder">placeholder</span> | Not started; W01.4 after W01.1 |
| [Diagnostics at system boundaries](placeholder-diagnostics-at-boundaries.md) | [Diagnostics work page](../plan/work/diagnostics-and-crash.md) | <span class="hg-status placeholder">placeholder</span> | Not started; design chunk W05.1 ready |
| [IOCP first, DirectStorage-shaped interface](placeholder-io-backend-iocp-first.md) | [Storage work page](../plan/work/storage-streaming.md) | <span class="hg-status placeholder">placeholder</span> | Designed ([storage design](../architecture/storage-design.md) section 2, W03.3); IOCP `IoThread` skeleton on engine branch `feat/affine-threads` (local); request path is the W03.4 plan, held behind W03.2 |
| [Explicit allocators with a debug-only hook](placeholder-explicit-allocators.md) | [Storage work page](../plan/work/storage-streaming.md) | <span class="hg-status placeholder">placeholder</span> | Not started; W08.1 after W04.1 |
| [Per-queue ownership, no single submit thread](placeholder-queue-ownership.md) | [Concurrency work page](../plan/work/concurrency-fibers.md) | <span class="hg-status placeholder">placeholder</span> | Applied in the [affine threads design](../architecture/affine-thread-design.md) and its execution on `feat/affine-threads` (W02.3, local): graphics submit stays on the frame stage, only the platform thread and the IO thread are affine |
| [In-house crash handler](placeholder-in-house-crash-handler.md) | [Diagnostics work page](../plan/work/diagnostics-and-crash.md) | <span class="hg-status placeholder">placeholder</span> | Not started; W06.1 ready |
| [SDL3 base input backend, native side channels](placeholder-input-backend-sdl3-base.md) | [Input backends exploration](../architecture/input-exploration.md) | <span class="hg-status placeholder">placeholder</span> | Not started; the SDL 3.2.22 to 3.4.x upgrade is task 1 of W39.1 |
| [Vendor recastnavigation for navmesh build and queries](placeholder-navmesh-recastnavigation.md) | [Navmesh library fit](../architecture/navigation-exploration.md) | <span class="hg-status placeholder">placeholder</span> | Nothing vendored; the detail-mesh sample cache patch is untracked in the engine checkout (`docs/superpowers/patches/`); vendoring is part of W37.2 |

How a record gets here: [Documenting an ADR](../guides/writing-adrs.md). The [template](template.md) mirrors the engine project's format.
