# ADR-0014: Security Policy: Private Reports, Latest Release Supported

**Date**: 2026-11-19 (owner, D6)
**Status**: accepted
**Source**: [work and release workflow](../guides/work-and-release.md#security)

## Context

The engine repository has no `SECURITY.md`, and private vulnerability reporting was switched off on 2026-11-18. With [forward-only releases](0013-versioned-forward-only-releases.md), a reporter needs to know which versions get fixed and where to report.

## Decision

- The engine repository gets a `SECURITY.md`. It says that only `master` and the latest release are supported, that fixes are not backported, and how to report.
- Vulnerabilities are reported privately through GitHub private vulnerability reporting, never in a public issue.
- A fix is prepared in the advisory's private fork, merged to `master` and shipped in the next release; the advisory names the fixing commit and release. A CVE is requested when a downstream user needs one.
- Response times are added to `SECURITY.md` later.

## Alternatives Considered

### Email-only reporting

- **Pros**: no GitHub dependency.
- **Cons**: no private fork, no advisory, no CVE workflow.
- **Why not**: GitHub's advisory flow covers all three.

## Consequences

### Positive

- Reporters have one private channel; fixes have a traceable record.

### Negative

- None beyond forward-only itself.

### Risks

- Until response times are written down, a reporter cannot tell when to expect an answer.
