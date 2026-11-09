# Placeholder: Diagnostics at System Boundaries

**Date**: pending (owner decision 2026-11-08, Q05.1 and Q05.2)
**Status**: placeholder, not yet processed in the engine project
**Source**: [Diagnostics work page](../plan/work/diagnostics-and-crash.md)

## Context

Failure paths across storage, importers, serialisation and the shader compiler return empty values or ad hoc error enums. A shared `Diagnostic` type with codes, locations and optional fixes is planned. The question was how far `Result<T, Diagnostic>` reaches.

## Decision

`Result<T, Diagnostic>` is the convention at system boundaries only. Internal code keeps small error enums and converts at the boundary. The convention must not affect hot paths in any way, and must not make interfaces over-complicated or un-ergonomic: one propagation helper, no nested wrappers, a success path that compiles to a plain value return. Fixes attached to diagnostics carry text edits in the first version; record edits follow once the serialiser provides record paths.

## Alternatives Considered

### `Result<T, Diagnostic>` everywhere

- **Pros**: one error type.
- **Cons**: a heap-allocating diagnostic in inner loops; every internal call site changes.
- **Why not**: the owner excluded any hot-path effect.

## Consequences

### Positive

- Every boundary failure names a code, a location and a message a human can act on; the editor can render and apply fixes.

### Negative

- Two error vocabularies (internal enums, boundary diagnostics) and a conversion at each boundary.

### Risks

- The boundary set must be listed explicitly in the design, or the convention leaks inward.
