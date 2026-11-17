# System Page Template

Copy this structure for a new page under `systems/`. Delete a section only if it truly does not apply.

```markdown
# <System name>

**Status**: implemented | experimental | planned
**Verified against**: engine commit `<hash>`, <date>
**Modules**: `Module.A`, `Module.B` (see the [module map](../architecture/modules.md))
**Related**: exploration or design pages, ADRs once they exist

## Purpose
What problem the system solves, in two or three sentences, and what it deliberately does not do.

## Where it sits
A diagram: what feeds the system and what consumes its output.

## How it works
The data flow and the per-frame or per-load lifecycle. Name the key types and link their source files at the verified commit.

## Configuration
Options, defaults and where they are set.

## Debugging
How to see what the system is doing: logs, capture tools, common failure signs.

## Limits and known issues
What is missing, slow or fragile today. Link the issues.

## Changing it
Where to start, what tests exist, what else breaks.
```

Rules: describe the code as it is, not as intended. Anything intended belongs in an [exploration](../guides/writing-explorations.md). Code links use permalinks to the verified commit, not `main`.
