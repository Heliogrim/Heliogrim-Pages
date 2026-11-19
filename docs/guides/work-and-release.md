# Work and Release Workflow

**Status**: <span class="hg-status accepted">guide</span>, partly open. Accepted by the owner on 2026-11-19: branches and history ([ADR-0012](../adr/0012-trunk-based-linear-history.md)), releases and versions ([ADR-0013](../adr/0013-versioned-forward-only-releases.md)), security policy ([ADR-0014](../adr/0014-security-policy.md)). Still open: [D7, D8, D10 to D12](#owner-decisions).
**Date**: 2026-11-19. GitHub settings checked on 2026-11-18 against the GitHub API for `Heliogrim/Heliogrim-Engine` and `Heliogrim/Heliogrim-Pages`; GitHub behaviour checked against docs.github.com, and CRA points against the Commission's CRA pages and secondary summaries, on 2026-11-19. Not legal advice. Statements not checked are marked *unverified*.

This page says how an idea becomes code on the default branch, and what "released" means. It builds on the [battle plan](../plan/index.md) (vision, systems, milestones), the [work packages](../plan/work/index.md) (chunks and their kinds), [writing an exploration](writing-explorations.md) and [writing an ADR](writing-adrs.md); where those pages already say something, this page links them and does not repeat them. The [progress board](../plan/progress.md) shows where each system and milestone stands.

## From vision to code

Every system goes through the same stages. A stage may be skipped when its question is already answered (a small system needs no research report), never reordered. Bugs and small tasks skip straight to an issue and a pull request; the stages exist for systems.

| Stage | Answers | Artifact | Leaves the stage when |
|---|---|---|---|
| **Vision** | What "done" means for a target | [Vision](../plan/vision.md) | The owner states the target and its acceptance bar |
| **Topic** | Which systems the target needs, in what order | [Topic page](../plan/topics/index.md), a row in the [systems catalog](../plan/systems.md) with milestone, a `battle-plan` issue on the engine | The system has an ID, a milestone and an issue with "done when" |
| **Research** | What others do and what is known | [Sources](../plan/sources/index.md), `architecture/sources/`; each claim marked `verified` or `unverified` | Never on its own: research informs, it does not decide |
| **Exploration** | What is true in our engine, with evidence | `explore` chunk, `architecture/<topic>-exploration.md`, numbers with hardware stated; open points become Q ids on the [questions page](../plan/work/questions.md) | The owner answers the questions; a cross-cutting answer becomes an [ADR](../adr/README.md) |
| **Design** | How we build it | `design` chunk, `architecture/<topic>-design.md`, builder-checked | The owner accepts it; the page's Status line says so |
| **Planning** | In which atomic steps | `execute` chunks on the work page; the implementation plan stays untracked in the engine checkout | Each execute chunk has inputs and a "done when" |
| **Execution** | The code | Engine branch, pull request into the default branch, system page from the [template](../systems/template.md) | The pull request is merged |
| **Milestone** | Whether the milestone's systems pass their "done when" | [Roadmap](../plan/roadmap.md) records the commit | Every listed system passes on one commit of the default branch |

Who decides: the owner closes exploration, design and milestone. An agent session or contributor may do any chunk, and states the assumption when it uses a suggested default instead of an answer.

### Chunk status grammar

The [progress board](../plan/progress.md) is generated from chunk headings, so headings follow one form:

```text
### W<system>.<n> <title> · <kind> · <status>
```

`<kind>` is `explore`, `design`, `design+plan`, `execute`, or a `+` combination. `<status>` starts with one of these words; anything after them is free text (dates, PR links, notes):

| Status starts with | Board shows |
|---|---|
| `ready` | ○ ready |
| `after W..`, `needs Q..`, `parallel to` | · blocked; an `after` whose chunks are all done counts as ready |
| `in progress`, `continuous` | ◐ in flight |
| `in review`, or `code done` followed by an open PR | ◐ in flight |
| `done`, `code done`, `desk study done` | ● done |
| `deferred` | – deferred |

Write where the code is: `on master` once it is on the default branch. While `feat/wip` exists, `into feat/wip` marks code that is merged but not landed; the board counts the two separately.

## Branches and pull requests

Accepted as [ADR-0012](../adr/0012-trunk-based-linear-history.md):

- The default branch is the only long-lived branch. Every change reaches it through a pull request. The engine's default branch stays `master` for now; renaming it to `main` comes later.
- Branch names: `<type>/<slug>` with the commit types (`feat/`, `fix/`, `refactor/`, `docs/`, `build/`, `test/`). No issue or PR numbers in branch names; those go in the PR.
- Stacked work: the next PR targets the previous PR's branch. When the lower PR merges and its branch is deleted, GitHub retargets the stacked PR to the default branch *(unverified)*.
- Commits follow conventional commits. A change that breaks a public API, a stored format or a build option carries `!` (`feat(storage)!: ...`) and a `BREAKING CHANGE:` footer saying what to do. Strongly recommended, not enforced; the release notes are built from it.
- Unfinished systems: whether a system lands behind a switch is decided per case. The default mechanism is open as [D10](#unfinished-systems-default-switch).

### Unfinished systems: default switch

Proposal for D10, not checked against the engine's current CMake options:

- **Default: a build-time feature switch.** One CMake helper, `hg_feature(<NAME> DEFAULT OFF DOC "...")`, declares the option `HELIOGRIM_FEATURE_<NAME>` and generates a `constexpr bool` in one header, so code uses `if constexpr` rather than scattered `#ifdef`s. The off path is the old code; the switch is removed when the system ships.
- **Runtime switch only when both paths must run in one build**, for example to measure them against each other (the lane policy's A/B runs). It is a setting, not a define.
- **CI builds once with every feature on**, so code behind a default-off switch does not rot.

### Retiring `feat/wip`

On 2026-11-18 `feat/wip` is 414 commits ahead of `master` and 18 behind, and the latest 100 commits on it show as *unsigned* on GitHub, while `master` requires signed commits. The [quality work page](../plan/work/quality-and-process.md) also records that `Heliogrim-Editor` did not build on `feat/wip` on 2026-11-16. Order of work:

1. No new PRs into `feat/wip`; open PRs (#176) are retargeted to `master` after step 4.
2. Fix the signing gap (see [signed commits](#signed-commits-and-rebase-merges)): commits whose signature GitHub cannot verify are refused by `master`.
3. Make `feat/wip` build and pass (editor included) on top of `master`.
4. Land it with a local rebase and push, then delete the branch.
5. Rewrite `into feat/wip` statuses on the work pages to `on master`; the board's "Landed" column must then show everything under `master`.

## History and merging

Accepted as [ADR-0012](../adr/0012-trunk-based-linear-history.md): linear history, no merge commits.

| Pull request | Lands as |
|---|---|
| Curated atomic commits, each builds and passes | Rebase, landed locally (below) so signatures survive |
| Work-in-progress commits, outside contributions | Squash merge on GitHub |

### Signed commits and rebase merges

What GitHub does (checked against GitHub's docs on 2026-11-19):

- **Rebase and merge on GitHub** always rewrites the committer and the SHAs, and GitHub cannot sign the new commits, because it does not have the committer's key. GitHub's own advice is to rebase locally and push to the base branch.
- **Squash merge on GitHub** produces a commit GitHub signs itself, but unsigned commits on the head branch can still block it.
- **Required signed commits** let you push local commits to the branch when they are signed and verified.

So a rebase merge on GitHub and signed commits on `master` cannot be combined. Options (D8):

| Option | How | Cost |
|---|---|---|
| **A. Land locally** (recommended) | Rebase the branch onto `master` with signed commits, then `git push origin <branch>:master` as a fast-forward. GitHub marks the PR merged when its head commit reaches the base *(unverified; check on the first landing)*. A small script checks approval, green checks and fast-forward before it pushes. | Needs bypass of the PR rule for whoever lands (the owner has it; `enforce_admins` is off). The rule is enforced by the script, not by GitHub. |
| B. Merge queue | GitHub's queue picks the merge method itself | Cannot keep your signatures either; not useful here |
| C. Drop required signatures | GitHub's rebase merge button works | Commits on `master` are unsigned; weakens the supply-chain record the CRA asks for |

Also part of D8: the commits on `feat/wip` show as unsigned on GitHub, even though they were made as signed commits. The likely cause is that the signing key is not registered on the GitHub account *(unverified)*. Register the key, then check one commit with `gh api repos/Heliogrim/Heliogrim-Engine/commits/<sha> --jq .commit.verification`.

## Releases

Accepted as [ADR-0013](../adr/0013-versioned-forward-only-releases.md):

- **Versions**: Semantic Versioning 2.0.0, tags `vMAJOR.MINOR.PATCH`, pre-releases `-rc.N`. While the major is `0`, a minor bump may break. Each build embeds version, commit and configuration (from `git describe`, for example `0.2.0-dev.14+g1a2b3c4` for an untagged build); the crash handler (S06), logs and the editor's about box report it. The existing tag `v0.1.7-dev.483` is a lightweight tag on an old commit; it stays.
- **Next version** follows from the commits since the last tag: `fix` bumps the patch, `feat` the minor, `!` the major (the minor while the major is `0`). Release notes are generated from the same commits; git-cliff does this without a bot *(tool not evaluated)*.
- **Milestones are releases**: the tag goes on the commit where the milestone's checks passed, and the [roadmap](../plan/roadmap.md) records it. Releases between milestones are allowed.
- **Pipeline**: pushing a signed tag `v*` runs the release workflow: build, all test suites, package, SBOM, checksums, a draft GitHub release with the assets, then publish. Immutability starts at publication, so the draft holds every asset first.
- **Immutable**: the engine's "Release Tags" ruleset already covers every tag. It forbids creation, update and deletion for everyone except the bypass roles, and requires signed tags (checked 2026-11-18). Switch on GitHub immutable releases for the repository too: a published release's tag and assets then cannot be changed or deleted, the tag name is never reusable, and GitHub adds a release attestation.
- **Consumers** pin a commit hash or a release tag.
- **Support**: `master` and the latest release. Fixes land on `master` and ship in the next release; no release branches or backports.
- **Data**: stored formats migrate forward ([ADR-0003](../adr/0003-record-schema-versioning.md)). Each format states its direct-load window (how many versions back); older data goes through a chained, multi-step migration. The window per format is D11.

**Revisit when** any of these becomes true; then add release branches `release/vX.Y` cut from the release tag. Fixes land on `master` first and are cherry-picked with `git cherry-pick -x`; nothing is fixed on a release branch alone. The pipeline already runs from a tag on any branch, so nothing else changes.

1. Heliogrim, or a product built on it, is placed on the EU market in a commercial activity (see [CRA readiness](#cyber-resilience-act-readiness)).
2. Someone outside the project ships on Heliogrim and asks for a support period.

## Security

Accepted as [ADR-0014](../adr/0014-security-policy.md). To do in the engine repository:

- Add `SECURITY.md`: supported versions (`master`, latest release), private reporting, no backports. Response times are added later.
- Switch on private vulnerability reporting (off on 2026-11-18).
- Fixes go through the advisory's private fork, then `master`, then the next release; the advisory names commit and release.
- Vendored third-party code (recastnavigation, Jolt, SDL and others) is listed with its pinned version, because Dependabot does not see vendored C++ *(unverified)*. That list is the source of the SBOM.

## Legal

### License (D7, open)

The requirements: anyone may contribute freely, and commercial terms stay possible later. The first requirement is about the inbound terms (what contributors grant). The second is about who can relicense. Both hold only if the project collects broad rights from every contributor from the first outside contribution on: a **CLA** that grants a license to the project, including the right to relicense, without assigning copyright. A DCO sign-off is not enough, because it grants no relicensing right. Without a CLA, each contributor keeps their code under the project license, and the project can never offer other terms for it.

Candidate outbound licenses, all combined with the CLA:

| Option | Others may | Commercial lever later | Fit for a game engine |
|---|---|---|---|
| **Apache-2.0** (permissive, patent grant) | Use, change and ship, closed or open, free | Only new versions under new terms, services, paid add-ons | High; Godot (MIT), O3DE (Apache-2.0) and Bevy (MIT or Apache-2.0) do this *(unverified)* |
| **MPL-2.0** (file-level copyleft) | Use in closed games; changes to engine files must be published | A commercial license that drops the publish duty, e.g. for console code under NDA | Good; game code stays closed |
| GPL-3.0 or AGPL-3.0 (strong copyleft) | Use only if the whole game is under the GPL | Dual licensing as Qt does | Poor: console SDKs under NDA cannot ship under the GPL, so games need the commercial license |
| Source-available, e.g. BSL 1.1 or a royalty EULA | Read and change; commercial use under the owner's terms; BSL turns into open source after a set time | Built in from day one | Not open source; fewer outside contributors |

Recommendation: decide with a lawyer before the first outside pull request is accepted. Keep the CLA in place whichever license is chosen. MPL-2.0 plus a CLA matches both requirements best. Apache-2.0 plus a CLA if adoption matters more than a commercial lever. The docs site text is a separate choice (for example CC BY 4.0, see the [licenses page](../legal/licenses.md)).

### Cyber Resilience Act readiness

What the CRA says, as summarised by the Commission and secondary sources (checked 2026-11-19, not legal advice):

- It applies to products made available on the EU market in a commercial activity. Open-source software that its manufacturer does not monetise is not a commercial activity. Contributors to someone else's open-source project are out of scope.
- An open-source software steward has a light regime: a cybersecurity policy, cooperation with authorities, reporting actively exploited vulnerabilities. A steward is a legal person that supports open-source software meant for commercial use on a sustained basis.
- A manufacturer must handle vulnerabilities for a support period of at least five years, or the expected use time if that is shorter. Where technically feasible, security updates come separately from functionality updates. Each security update stays available for ten years, and the manufacturer keeps an SBOM of at least the top-level dependencies. Reporting duties apply from 11 September 2026; the vulnerability-handling duties from 11 December 2027.
- A game studio shipping a game on Heliogrim is the manufacturer of that game, and must handle the vulnerabilities in the components it integrates.

#### Continuous releases and backports

Not every build is a release in the CRA's sense. Internal CI builds, such as several bundles a day kept in an artifact store, are not placed on the market; only versions delivered to users are. An update that does not substantially modify the product belongs to the version already on the market and runs under that version's support period.

The CRA does not require backports in general. Article 13(10) lets a manufacturer that has placed later, substantially modified versions on the market fix vulnerabilities only in the latest version. The condition is that users of earlier versions get the latest version free of charge and do not incur additional costs to adjust the hardware and software environment they use it in. The Commission's draft guidance (2026) gives frequently released enterprise software as an example. Three things remain:

- The relief covers only vulnerability remediation (Annex I Part II point 2). The disclosure policy, SBOM and reporting still apply to every version, and users who stay on an old version must be told where technically feasible that it gets no more fixes.
- For an engine, the environment the user must adjust includes their game code. A breaking API change forces work on every studio, so it is arguably an "additional cost". How the guidance defines that term could not be read in full on 2026-11-19. The safe reading: within one major version there are no breaking changes, and only a new major can need a backport.
- "Security updates separate from functionality updates, where technically feasible" still applies to the latest version. With continuous releases, a fix found while `master` holds unreleased features ships as a patch release from the latest tag. A short-lived `hotfix/vX.Y.Z` branch is created on demand from that tag, gets the cherry-picked fix (`-x`), is tagged and deleted. The next regular release from `master` carries the fix anyway.

So forward-only stays the model once the CRA applies. It changes to: forward-only within a major, security fixes as patch releases on the latest release, backports only to an older major that is still inside its support period. Majors must therefore be rare. The free-upgrade condition also binds D7: commercial terms must give licensees newer versions within the support period without a new fee.

What that means here: once Heliogrim is monetised, for example through a commercial license, Heliogrim is a product and the project is its manufacturer. Studios will then ask for security-only updates over a support period. To avoid a second setup later, build now what costs little and is needed either way:

| Build now | Why |
|---|---|
| SemVer tags with a patch slot, a pipeline that runs from a tag on any branch, cherry-pick with `-x` | A hotfix or an old major's branch is one new branch, not a new process |
| No breaking change without `!` and a major (or, before 1.0, a minor) bump | The Article 13(10) free-upgrade condition depends on knowing which upgrades cost users work |
| SBOM in every release, from the vendored-components list | Required for manufacturers; studios need it for their own products |
| Immutable releases, assets never deleted | Covers the ten-year availability of security updates |
| `SECURITY.md`, private reporting, advisories | The policy a steward or manufacturer must have |
| Signed commits and tags, release attestations | Lets anyone verify which source a release came from |

Left for when it applies (D12): the legal entity, the support period per release line, the reporting process to ENISA, and the technical documentation.

## CI and validation

| Repository | Rules on the default branch (2026-11-18) | Recommended |
|---|---|---|
| Engine | PR with review, linear history, signed commits, no force push; admins may bypass; no required checks; no workflows | Add the S62 build and test workflow ([W62.1](../plan/work/quality-and-process.md)) as a required check on every PR; until then the PR states which builds and suites the author ran |
| Pages | No protection | PR required, linear history, required check `mkdocs build --strict` (the `Pages` workflow already runs it on PRs) |

CI on every pull request is the default, as in any enterprise setup. What it tests is the PR's head commit, or the merge result with the base. A PR that lands as a rebase of several commits puts every intermediate commit on `master`, and CI never built those. Each such commit must build, so that `git bisect` and reverting single commits work. Ways to cover the gap:

- **Author check** (default): before landing, `git rebase --exec "<build and unit tests>" master` runs the check on every commit. The landing script can run it.
- **CI per commit**: a job builds each commit of the PR (build only, tests on the head). Expensive for long PRs; worth it once CI caches objects (S62 uses sccache).
- **Squash**: one commit, nothing to cover; loses the atomic commits.

### Bisect guarantee starts at a cutoff

Nothing so far guaranteed that every commit on `master` or `feat/wip` builds, so old history cannot be bisected reliably and is not repaired. The guarantee starts at a cutoff commit, the first commit on `master` after `feat/wip` lands, which the roadmap records as "bisectable from `<sha>`":

- From the cutoff on, every commit on `master` **builds** (checked at landing with `rebase --exec`). Tests are required at the head of each PR only; a commit in the middle may fail a test, but never the build.
- Before the cutoff, `git bisect skip` steps over commits that do not build; `git bisect start <bad> <cutoff>` keeps searches after the cutoff.
- `feat/wip` lands as it is, without repairing its 414 commits; its commits come before the cutoff.

## Owner decisions

| ID | Decision | State |
|---|---|---|
| D1 | Integration model | Accepted 2026-11-19, [ADR-0012](../adr/0012-trunk-based-linear-history.md); rename to `main` later |
| D2 | Rename `master` to `main` | Deferred |
| D3 | History | Accepted 2026-11-19, [ADR-0012](../adr/0012-trunk-based-linear-history.md) |
| D4 | Release model | Accepted 2026-11-19 with versions, tag pipeline and assets, [ADR-0013](../adr/0013-versioned-forward-only-releases.md) |
| D5 | Milestone marker | Accepted 2026-11-19: milestones are release tags, [ADR-0013](../adr/0013-versioned-forward-only-releases.md) |
| D6 | Security policy | Accepted 2026-11-19, [ADR-0014](../adr/0014-security-policy.md); response times later |
| D7 | License and contribution terms | Open; recommendation: CLA now, MPL-2.0 or Apache-2.0 after legal advice |
| D8 | Keeping signatures with rebase landing | Open; recommendation: option A, land locally with a checking script; register the signing key |
| D9 | Per-commit check | Proposal: every commit builds from a cutoff after `feat/wip` lands; tests at PR head; checked at landing with `rebase --exec` |
| D10 | Default switch for unfinished systems | Open; proposal: build-time `hg_feature`, runtime setting only for A/B, CI with all on |
| D11 | Direct-load window per stored format | Open; set per format in its design |
| D12 | CRA manufacturer setup (entity, support period, reporting) | Deferred until Heliogrim is monetised; the cheap parts are built now |
