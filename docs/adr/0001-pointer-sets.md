# ADR-0001: Keep `ankerl::unordered_dense` for Pointer Sets

**Date**: 2026-11-04 (owner; exploration closed)
**Status**: accepted (recorded 2026-11-16)
**Source**: [Pointer sets exploration](../architecture/pointer-sets-exploration.md)

## Context

The exploration proposed a custom pointer set for small and medium sizes: a dense array with a SIMD scan below a threshold and a fingerprinted index above it. The comparison criteria were fixed before measuring.

## Decision

We keep `ankerl::unordered_dense` as the pointer set. The custom container is dropped.

## Alternatives Considered

### Custom `PtrSet`

- **Pros**: the inline linear scan beat ankerl on small mixed-order misses, about 0.3 ns at N=4.
- **Cons**: ankerl won hits and dependent-chain latency at every size. Cold-cache misses cost about 15 ns more than ankerl at N=8.
- **Why not**: the gain was too narrow to justify a maintenance burden. Ankerl's layout can be tuned upstream, and callers can prefetch.

## Consequences

### Positive

- No new container to maintain; about 110 files keep their current aliases.

### Negative

- Small-N misses stay slightly slower than the best case measured.

### Risks

- The measurements come from one machine. Revisit only with a profile showing pointer-set lookups on a hot path.
