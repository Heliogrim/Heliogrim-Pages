# Propose a Change

Decisions are made in the engine project; this repository takes exploration requests and docs fixes.

<a class="hg-btn primary" href="https://github.com/Heliogrim/Heliogrim-Pages/issues/new?template=exploration-request.yml">Request an exploration</a>
<a class="hg-btn" href="https://github.com/Heliogrim/Heliogrim-Engine/issues/new/choose">Propose a decision (engine project)</a>
<a class="hg-btn" href="https://github.com/Heliogrim/Heliogrim-Pages/issues/new?template=docs-issue.yml">Report a docs error</a>

## Which one

- **Decision (ADR).** Raise it in the engine project, which processes ADRs. Once accepted there, it is documented here; see [Documenting an ADR](../guides/writing-adrs.md).
- **Exploration.** You have a question or an outside claim worth checking against the engine before anyone commits. See [Writing an exploration](../guides/writing-explorations.md).
- **Docs error.** A wrong statement, a dead link, a stale status. For small fixes, use **Edit this page** and open a pull request directly.

## Pull requests

1. Fork or branch, then preview with `mkdocs serve` ([how](../guides/docs-workflow.md)).
2. Make `mkdocs build --strict` pass.
3. Name the commit `docs(scope): summary`.
4. Link the issue where the discussion happened.
