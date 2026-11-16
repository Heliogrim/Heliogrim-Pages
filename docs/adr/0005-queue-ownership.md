# ADR-0005: Per-Queue Ownership, No Single Submit Thread

**Date**: 2026-11-08 (owner, Q02.4)
**Status**: accepted (recorded 2026-11-16)
**Source**: [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84), [affine threads design](../architecture/affine-thread-design.md), applied in PRs [#159](https://github.com/Heliogrim/Heliogrim-Engine/pull/159) and [#164](https://github.com/Heliogrim/Heliogrim-Engine/pull/164)

## Context

The affine-thread design asked whether Vulkan queue submission should become a dedicated service thread. Multi-threaded submission was one reason Vulkan was chosen.

## Decision

There is no single submit thread. Each `VkQueue` has exactly one owner at a time, and distinct queues submit concurrently from different threads or fibers. Graphics and present submit from the frame's submit stage on whichever fiber runs it. The transfer queue used for streaming uploads is owned by an affine thread fed by storage completions. Later work may split graphics submission across queues.

## Alternatives Considered

### One affine submit thread for all queues

- **Pros**: no queue locks anywhere.
- **Cons**: serialises all submission through one thread; gives up a capability the API was chosen for.
- **Why not**: the cost is paid on every frame, and the race it prevents is better caught by declared queue ownership.

## Consequences

### Positive

- Streaming uploads and presentation run independent of frame fibers; recording stays fully parallel.

### Negative

- Queue ownership must be stated and asserted per queue.

### Risks

- A queue shared by two stages without a stated owner is a data race; the task graph's write sets must include queues.
