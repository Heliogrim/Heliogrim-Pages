# Writing an Exploration

An exploration collects options and evidence for a system before anyone commits to a design. It is allowed to be wrong; it is not allowed to be vague about what was checked.

## Lifecycle

1. **Exploration**: open questions, claims from outside sources, problems found. Status line: `exploration. Nothing here is decided.`
2. **Design**: one direction chosen. Move or copy it to a page named `*-design.md` with an approval date.
3. **Decision**: the accepted part becomes an [ADR](writing-adrs.md) in the same commit. The exploration stays as the record of rejected options.
4. **Closed**: if the work is abandoned, mark the status `closed`, state the result in one sentence, and keep the page.

## Structure

The existing pages share one shape. Reuse it:

| Section | Content |
|---------|---------|
| Status line | State, and where accepted parts go |
| Current state in the engine | What the source does today, with the check date |
| Claim | What the outside source or proposal says |
| Checked | What you verified, and how |
| Problems found | Where the claim fails or is unmeasured |
| Proposed change | The smallest next step |
| Decisions needed | Questions with an owner, not open-ended ones |

## Rules

- Measure before you design. A claim from a blog post is a claim, not evidence.
- Give dates for every check against the source; the engine moves.
- Put long research under `sources/` and link it.
- Add the page to `nav` and the [architecture index](../architecture/index.md), and add a row to the [timeline](../architecture/timeline.md) log.
