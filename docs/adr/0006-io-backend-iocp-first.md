# ADR-0006: IOCP First, DirectStorage-Shaped Interface

**Date**: 2026-11-08 (owner, Q03.2 and Q03.3)
**Status**: accepted (recorded 2026-11-16)
**Source**: [#85](https://github.com/Heliogrim/Heliogrim-Engine/issues/85), [storage design](../architecture/storage-design.md) section 2, implementation PR [#180](https://github.com/Heliogrim/Heliogrim-Engine/pull/180) (open)

## Context

Async storage has no backend; `queryAsync` panics. DirectStorage is part of the target architecture, but its benefit on this project's assets is unmeasured.

## Decision

The first Windows backend is IOCP with unbuffered, sector-aligned reads on an affine thread. The `IoRequest` and `IoBackend` interfaces are shaped so a DirectStorage backend drops in later: file range to host or GPU destination, batch submit, queue-level completion, a compression format per request. The codec is chosen by benchmark among legally clear candidates that include a format DirectStorage decompresses on the GPU (GDeflate); commercial codecs are out.

## Alternatives Considered

### DirectStorage from the start

- **Pros**: one backend.
- **Cons**: an unmeasured dependency on the critical path; no fallback for tests and non-Windows.
- **Why not**: measure first.

## Consequences

### Positive

- A thread-pool fallback serves tests; the DirectStorage backend is additive.

### Negative

- Two backends to keep in step once DirectStorage lands.

### Risks

- If the benchmark shows GPU decompression is the only win, the IOCP backend becomes a fallback only.
