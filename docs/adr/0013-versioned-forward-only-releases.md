# ADR-0013: Versioned, Forward-Only Releases from Immutable Tags

**Date**: 2026-11-19 (owner, D4 and D5)
**Status**: accepted
**Source**: [work and release workflow](../guides/work-and-release.md)

## Context

The engine needs a version to identify bug reports, crash dumps, runtime builds and the commit a game depends on. It is meant for distribution and for commercial games, so releases need assets and a stable identity. One maintainer cannot keep several release lines patched.

## Decision

- The engine has version numbers following Semantic Versioning 2.0.0. A release is an annotated, signed tag `vMAJOR.MINOR.PATCH` (pre-releases `-rc.N`). Every build embeds its version, commit and configuration; an untagged build reports `X.Y.Z-dev.N+g<sha>` from `git describe`.
- Pushing a release tag runs a pipeline that builds, tests and packages, then publishes a GitHub release with its assets. Milestones are releases: the tag goes on the commit where the milestone's "done when" checks passed, and the [roadmap](../plan/roadmap.md) records it.
- Tags and releases are immutable once created: the tag ruleset forbids update and deletion, and GitHub immutable releases lock the assets.
- Consumers pin a commit hash or a release tag.
- Only the latest release and `master` are supported. Fixes land on `master` and ship in the next release; there are no release branches and no backports until a [revisit trigger](../guides/work-and-release.md#releases) is met.
- Stored data migrates forward ([ADR-0003](0003-record-schema-versioning.md)). Direct loading is supported for a bounded window of older versions; older data goes through a multi-step migration path. The window is set per format.

## Alternatives Considered

### No versions, commit hashes only

- **Pros**: nothing to maintain.
- **Cons**: reports, crash dumps and dependency pins cannot name a version a human can compare.
- **Why not**: every distributed product needs a version.

### Maintained release branches with backports

- **Pros**: users get security fixes without new features (the CRA expects this for commercial products).
- **Cons**: every line multiplies CI, fixes and support questions.
- **Why not yet**: no product is on the market. The tag scheme, the pipeline and the "fix on `master` first, cherry-pick with `-x`" rule are chosen so that branches can be added later without a new setup.

## Consequences

### Positive

- A report, a dump and a pin all name the same version.
- Released assets cannot be swapped after publication.

### Negative

- A user who needs a fix must take the features released with it.

### Risks

- Once Heliogrim or a game built on it is placed on the EU market, the CRA support period (at least five years) applies. Article 13(10) keeps forward-only possible only while upgrades are free and cost users no adaptation, which limits breaking changes to rare majors; see [CRA readiness](../guides/work-and-release.md#continuous-releases-and-backports).
