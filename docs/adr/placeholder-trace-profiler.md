# Placeholder: Drop the JSON Trace Profiler, Stopwatch and Macros

**Date**: pending (noted 2026-11-04)
**Status**: placeholder, not yet processed in the engine project
**Source**: [Exploration rundown](../architecture/exploration-rundown.md), topic 5, and the [observability exploration](../architecture/observability-exploration.md)

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

- No built-in profiling until the replacement lands (order of work item 4 in the [timeline](../architecture/timeline.md)).

### Risks

- The replacement depends on the shared fiber context; delays there delay profiling.
