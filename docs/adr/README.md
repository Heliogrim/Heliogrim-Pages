# Architecture Decision Records

ADRs are processed in the engine project. This repository documents them after they are accepted there; it does not originate them. Records are never rewritten; a newer ADR supersedes an older one and links to it.

## Accepted records

None yet. Records appear here, with the number assigned by the engine project, once processed.

## Placeholders

Drafts derived from exploration outcomes, kept so the pages have a place to land. They are **not** decisions until the engine project has processed them.

| Placeholder | Derived from | Status |
|-------------|--------------|--------|
| [Keep `ankerl::unordered_dense` for pointer sets](placeholder-pointer-sets.md) | [Pointer sets exploration](../architecture/pointer-sets-exploration.md) | <span class="hg-status placeholder">placeholder</span> |
| [Drop the JSON trace profiler, stopwatch and macros](placeholder-trace-profiler.md) | [Observability exploration](../architecture/observability-exploration.md) | <span class="hg-status placeholder">placeholder</span> |
| [Schema versioning on records](placeholder-record-schema-versioning.md) | [Serialisation work page](../plan/work/serialization-and-reflection.md) | <span class="hg-status placeholder">placeholder</span> |
| [Canonical text form as a YAML subset](placeholder-text-form-yaml.md) | [Serialisation work page](../plan/work/serialization-and-reflection.md) | <span class="hg-status placeholder">placeholder</span> |
| [Diagnostics at system boundaries](placeholder-diagnostics-at-boundaries.md) | [Diagnostics work page](../plan/work/diagnostics-and-crash.md) | <span class="hg-status placeholder">placeholder</span> |
| [IOCP first, DirectStorage-shaped interface](placeholder-io-backend-iocp-first.md) | [Storage work page](../plan/work/storage-streaming.md) | <span class="hg-status placeholder">placeholder</span> |
| [Explicit allocators with a debug-only hook](placeholder-explicit-allocators.md) | [Storage work page](../plan/work/storage-streaming.md) | <span class="hg-status placeholder">placeholder</span> |
| [Per-queue ownership, no single submit thread](placeholder-queue-ownership.md) | [Concurrency work page](../plan/work/concurrency-fibers.md) | <span class="hg-status placeholder">placeholder</span> |
| [In-house crash handler](placeholder-in-house-crash-handler.md) | [Diagnostics work page](../plan/work/diagnostics-and-crash.md) | <span class="hg-status placeholder">placeholder</span> |

How a record gets here: [Documenting an ADR](../guides/writing-adrs.md). The [template](template.md) mirrors the engine project's format.
