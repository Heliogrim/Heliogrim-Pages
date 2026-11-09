# Placeholder: Per-Queue Ownership, No Single Submit Thread

**Date**: pending (owner decision 2026-11-08, Q02.4)
**Status**: placeholder, not yet processed in the engine project
**Source**: [Concurrency work page](../plan/work/concurrency-fibers.md)

## Context

The affine-thread design asked whether Vulkan queue submission should become a dedicated service thread. Multi-threaded submission was one reason Vulkan was chosen.

## Decision

There is no single submit thread. Each `VkQueue` has exactly one owner at a time, and distinct queues submit concurrently from different threads or fibers. Graphics and present submit from the frame's submit stage on whichever fiber runs it. The transfer queue used for streaming uploads is owned by an affine thread fed by storage completions. Later work may split graphics submission across queues.

## Alternatives Considered

### One affine submit thread for all queues

- **Pros**: no queue locks anywhere.
- **Cons**: serialises all submission through one thread; gives up a capability the API was chosen for.

## Consequences

### Positive

- Streaming uploads and presentation run independent of frame fibers; recording stays fully parallel.

### Negative

- Queue ownership must be stated and asserted per queue.

### Risks

- A queue shared by two stages without a stated owner is a data race; the task graph's write sets must include queues.
