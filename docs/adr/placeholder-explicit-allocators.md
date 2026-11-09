# Placeholder: Explicit Allocators with a Debug-Only Global Hook

**Date**: pending (owner decision 2026-11-08, Q08.1)
**Status**: placeholder, not yet processed in the engine project
**Source**: [Storage work page](../plan/work/storage-streaming.md)

## Context

Memory per subsystem must be reported in traces and headless telemetry. The question was whether to override the global `operator new` or to route tracked allocations through explicit allocators.

## Decision

Explicit tagged allocators and arenas are the tracking mechanism. A global `operator new` hook exists in debug builds only, to find untagged allocations; it never ships in Playtest or Release tiers.

## Alternatives Considered

### Global `operator new` override everywhere

- **Pros**: nothing escapes tracking.
- **Cons**: no tag information without a thread-local context, which is banned across fiber suspension points; third-party allocations pollute the numbers.

## Consequences

### Positive

- Tags are explicit at the call site and survive fiber migration.

### Negative

- Adoption is incremental; untagged code shows as "other" until migrated.

### Risks

- Vendored libraries with their own allocation paths stay outside the report unless given an allocator.
