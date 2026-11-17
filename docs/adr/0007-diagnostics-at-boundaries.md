# ADR-0007: Diagnostics at System Boundaries

**Date**: 2026-11-08 (owner, Q05.1 and Q05.2; design accepted 2026-11-14)
**Status**: accepted (recorded 2026-11-16)
**Source**: [#87](https://github.com/Heliogrim/Heliogrim-Engine/issues/87), [diagnostics design](../architecture/diagnostics-design.md) section 5, built in PR [#188](https://github.com/Heliogrim/Heliogrim-Engine/pull/188)

## Context

Failure paths across storage, importers, serialisation and the shader compiler return empty values or ad hoc error enums. A shared `Diagnostic` type with codes, locations and optional fixes was planned. The question was how far `Result<T, Diagnostic>` reaches.

## Decision

`hg::Result<T, Diagnostic>` (or `Result<T, Diagnostics>` for compilers and validators) is the convention at system boundaries only. Internal code keeps small error enums and converts once at the boundary, where code and location are known. Failures move up through one helper, `propagate`, with no macro and no nested wrappers, and the success path compiles to a plain value return. Fixes carry text edits in the first version; record edits follow once the serialiser provides record paths.

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

- The convention leaks inward unless each migration names its boundary. The design lists the migration order (section 8); only ASL and `Engine.Accel.Compile` are migrated so far.
