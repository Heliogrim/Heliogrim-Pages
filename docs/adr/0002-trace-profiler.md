# ADR-0002: Drop the JSON Trace Profiler, Stopwatch and Macros

**Date**: 2026-11-04 (owner, session notes of 2026-11-03)
**Status**: accepted (recorded 2026-11-16)
**Source**: [#86](https://github.com/Heliogrim/Heliogrim-Engine/issues/86), [observability exploration](../architecture/observability-exploration.md)

## Context

The engine has a JSON trace profiler with a stopwatch and macro front end. It is not fiber-aware, and fibers migrate between threads. The audio design keeps only a hook for profiling.

## Decision

We drop the existing profiler, stopwatch and macros. Observability is built from the ground up on a fiber-aware span API; its design stays in the observability exploration until decided.

## Alternatives Considered

### Keep and extend the JSON trace profiler

- **Pros**: exists today.
- **Cons**: no fiber identity; macro-based API.
- **Why not**: extending it would carry its limits into the new design.

## Consequences

### Positive

- One profiling design, shaped by fibers from the start.

### Negative

- No built-in profiling until the replacement lands (S04). The old code stays in `Engine.Common/Profiling` until then; its removal is part of W04.1.

### Risks

- The replacement depends on fiber identity in the scheduler (S02); delays there delay profiling.
