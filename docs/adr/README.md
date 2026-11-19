# Architecture Decision Records

This repository is the home of the engine's ADRs. A record is written when the owner accepts a decision, usually as the answer to a work-package question or the acceptance of a design. Records are never rewritten; a newer ADR supersedes an older one and links to it. How far each decision is built is tracked on the [work packages](../plan/work/index.md), not here.

## Records

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-pointer-sets.md) | Keep `ankerl::unordered_dense` for pointer sets | <span class="hg-status accepted">accepted</span> | 2026-11-04 |
| [0002](0002-trace-profiler.md) | Drop the JSON trace profiler, stopwatch and macros | <span class="hg-status accepted">accepted</span> | 2026-11-04 |
| [0003](0003-record-schema-versioning.md) | Schema versioning on records | <span class="hg-status accepted">accepted</span> | 2026-11-08 |
| [0004](0004-text-form-yaml.md) | Canonical text form as a YAML subset | <span class="hg-status accepted">accepted</span> | 2026-11-08 |
| [0005](0005-queue-ownership.md) | Per-queue ownership, no single submit thread | <span class="hg-status accepted">accepted</span> | 2026-11-08 |
| [0006](0006-io-backend-iocp-first.md) | IOCP first, DirectStorage-shaped interface | <span class="hg-status accepted">accepted</span> | 2026-11-08 |
| [0007](0007-diagnostics-at-boundaries.md) | Diagnostics at system boundaries | <span class="hg-status accepted">accepted</span> | 2026-11-08 |
| [0008](0008-in-house-crash-handler.md) | In-house crash handler | <span class="hg-status accepted">accepted</span> | 2026-11-08 |
| [0009](0009-explicit-allocators.md) | Explicit allocators with a debug-only global hook | <span class="hg-status accepted">accepted</span> | 2026-11-08 |
| [0010](0010-navmesh-recastnavigation.md) | Vendor recastnavigation for navmesh build and queries | <span class="hg-status accepted">accepted</span> | 2026-11-09 |
| [0011](0011-input-backend-sdl3-base.md) | SDL3 as base input backend, native capability side channels | <span class="hg-status accepted">accepted</span> | 2026-11-09 |
| [0012](0012-trunk-based-linear-history.md) | Trunk-based development with linear history | <span class="hg-status accepted">accepted</span> | 2026-11-19 |
| [0013](0013-versioned-forward-only-releases.md) | Versioned, forward-only releases from immutable tags | <span class="hg-status accepted">accepted</span> | 2026-11-19 |
| [0014](0014-security-policy.md) | Security policy: private reports, latest release supported | <span class="hg-status accepted">accepted</span> | 2026-11-19 |

Records 0001 to 0011 were decided between 2026-11-04 and 2026-11-09 and recorded on 2026-11-16; the date column is the decision date.

How a record gets here: [Writing an ADR](../guides/writing-adrs.md). Start from the [template](template.md).
