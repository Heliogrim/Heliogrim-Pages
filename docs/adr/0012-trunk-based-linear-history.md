# ADR-0012: Trunk-Based Development with Linear History

**Date**: 2026-11-19 (owner, D1 and D3)
**Status**: accepted
**Source**: [work and release workflow](../guides/work-and-release.md)

## Context

Engine work ran through a long-lived integration branch, `feat/wip`, while `master` stayed far behind (414 commits ahead, 18 behind on 2026-11-18). `master` already requires pull requests, linear history and signed commits. With one maintainer and agent sessions producing many atomic commits, the open questions were where work lands, and whether history stays linear or becomes semi-linear (a merge commit per pull request).

## Decision

- The default branch is the only long-lived branch. Every change reaches it through a pull request; `feat/wip` is retired. Renaming `master` to `main` is deferred.
- Work branches are named `<type>/<slug>` with the conventional-commit types. Issue and PR numbers never go into branch names.
- Stacked pull requests are allowed: the next PR targets the previous PR's branch.
- Whether an unfinished system lands behind a switch is decided per case; the engine provides one default switch mechanism for it ([D10](../guides/work-and-release.md#owner-decisions)).
- Commits follow conventional commits. A breaking change carries `!` and a `BREAKING CHANGE:` footer; this is strongly recommended, not enforced.
- History stays linear. A pull request of atomic commits that each build and pass lands as a rebase; any other pull request is squashed. Merge commits are not used.

## Alternatives Considered

### Long-lived integration branch (`feat/wip`)

- **Pros**: unfinished work does not touch `master`.
- **Cons**: integration happens once, late and large; commits on it were not signed; the editor did not build on it for a while; "done" meant two different things.
- **Why not**: the cost lands at the end, all at once.

### Semi-linear history

- **Pros**: `git log --first-parent` groups commits by pull request.
- **Cons**: needs merge commits allowed and the linear-history rule dropped; GitHub has no button for it, so each merge is done by hand.
- **Why not**: with one maintainer and atomic commits the grouping does not pay for the extra steps. Revisit when several people merge in parallel.

## Consequences

### Positive

- One meaning of "landed": on `master`. The [progress board](../plan/progress.md) counts it directly.
- Every commit on `master` is a reviewable, revertable step; `git bisect` works.

### Negative

- GitHub's rebase merge cannot keep commit signatures (verified in GitHub's merge-method docs on 2026-11-18), so atomic-commit PRs land by a local rebase and push ([D8](../guides/work-and-release.md#signed-commits-and-rebase-merges)).

### Risks

- Unfinished systems on `master` must not break the default build; that depends on the switch mechanism (D10) and CI (S62).
