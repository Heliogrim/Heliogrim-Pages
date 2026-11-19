# Battle Plan

**Status**: <span class="hg-status summary">plan</span>. A working plan, not a decision record. Accepted parts move to an [ADR](../adr/README.md); designs move to `architecture/*-design.md`.

**Date**: 2026-11-07. Written against engine commit `d1aeb790` (branch `build/ankerl-v5-3-3`) and the pages on this site. Bundle sizes and file lists were checked in the source; behaviour claims cite the page that checked them.

## What this is

The owner's brief: evolve Heliogrim from an experimental Vulkan engine plus editor into a general-purpose, next-generation engine at an enterprise or military grade of design and code, with a specific target list (photorealistic real-time graphics, micropolygon geometry, open-world MMO scale, custom shader language, C++ hot reload, full editor tooling, networking, headless clusters, and more). Third-party code stays limited to platform integration, selected algorithms and standard codecs; the engine itself is written in the project.

This section turns that brief into a plan that survives sessions and people:

| Page | Answers |
|------|---------|
| [Vision](vision.md) | What "done" means per target, refined and extended, with the acceptance bar for each |
| [Target architecture](architecture.md) | Layers, process topologies, execution model and data flow the systems must fit |
| [Required modules](modules.md) | Every bundle the target needs, mapped to what exists today |
| [Gap analysis](gap-analysis.md) | Per target: what the engine has, what is missing, how far the distance is |
| [Systems to build](systems.md) | The catalog of systems with IDs, dependencies, track, milestone and issue |
| [Roadmap](roadmap.md) | Dependency line and milestones; which order the work can go in and why |
| [Progress board](progress.md) | Generated: per milestone and system, chunks done, in flight, ready and blocked, and how much code is on `master` |
| [Topics](topics/index.md) | One page per topic: research with sources, and guidance for building it here |
| [Sources](sources/index.md) | Raw research reports behind the topic pages |
| [Work packages](work/index.md) | Per topic: cross-reference with the explorations and designs, architecture and code design, chunks of work (explore, design, execute) with status, and the [questions](work/questions.md) for the owner in batches |

## How to read it

- System IDs (`S01` to `S64`) are stable. Issues, topic pages and the roadmap use them. The [systems catalog](systems.md) is the index.
- Milestones `M1` to `M6` are integration points, not dates. Tracks run in parallel; a milestone is reached when its listed systems pass their "done when" checks.
- Every claim about the engine names the check date. The engine moves; re-check before building on a claim older than a few weeks.
- Research pages mark each claim `verified` (the source was opened) or `unverified`. Unverified claims do not back decisions.

## Working rules this plan assumes

These come from the engine project's `CLAUDE.md`, `STYLE.md` and the owner's recorded preferences:

- The GitHub issue is the spec. Each system here has, or gets, an issue with "done when" and "covered now / left for later" sections.
- Measure before design. A system whose benefit rests on an unmeasured claim starts with a benchmark or a spike, listed in its issue.
- The stages from vision to code, branches, history and releases: [work and release workflow](../guides/work-and-release.md), [ADR-0012](../adr/0012-trunk-based-linear-history.md) to [ADR-0014](../adr/0014-security-policy.md).
- No ephemeral specs or plans on `master`. Designs live here; implementation plans stay untracked in the engine checkout.
- A problem found mid-change becomes its own issue; its fix is an atomic commit.
- Enterprise grade means: every public contract documented and tested, every failure path returns a diagnostic a human can act on, every subsystem observable, every change reviewable in isolation. [Quality and process](topics/quality-and-process.md) spells it out.

## Recovery

This plan was written by an autonomous run on 2026-11-07; the work packages were added by a second run on 2026-11-08. The state is the set of files under `docs/plan/`; the next thing to do is always a `ready` chunk in [work packages](work/index.md) or a question batch in [questions](work/questions.md). Issues [#83 to #145](https://github.com/Heliogrim/Heliogrim-Engine/issues?q=label%3Abattle-plan) carry the label `battle-plan` on the engine repository so they can be listed, reviewed or bulk-closed; the [systems catalog](systems.md) maps each system to its issue.
