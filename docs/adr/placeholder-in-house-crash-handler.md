# Placeholder: In-House Crash Handler

**Date**: pending (owner decision 2026-11-08, Q06.1 and Q06.2)
**Status**: placeholder, not yet processed in the engine project
**Source**: [Diagnostics work page](../plan/work/diagnostics-and-crash.md)

## Context

The engine has no crash handling. A crash on a fiber must produce a dump whose symbolised stack names the failing function, with annotations and a stable crash id. The word "crashpad" in earlier notes described the need, not Google's library.

## Decision

The crash handler is written in the project: a small second process that receives a pipe handshake from the engine, writes a minidump with `MiniDumpWriteDump` including registered fiber stacks, and stores it with annotations in a local database. Dumps stay local; the next iteration attaches them to the project's bug and crash reports, and an upload path is a possible later step, so the client keeps that seam.

## Alternatives Considered

### Vendor Google Crashpad

- **Pros**: proven handler, symbol upload, multi-platform.
- **Cons**: builds with GN and mini_chromium, CMake ports are community-maintained; a large dependency for a Windows-only need.
- **Why not**: the owner wants the in-house solution; the Windows handler is small.

## Consequences

### Positive

- No external dependency; the handler knows the engine's fibers and annotations directly.

### Negative

- Other platforms need their own handler when they arrive.

### Risks

- Stack walking across fiber stacks in a minidump needs the stack ranges registered before the crash; the W06.1 prototype verifies this first.
