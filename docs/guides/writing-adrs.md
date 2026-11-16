# Writing an ADR

ADRs live in this repository. A record states one decision the owner accepted, the alternatives rejected, and the consequences. It is short: about a page, with the context in at most ten lines.

## When

Write the record in the same commit that records the decision: the answer to a work-package question, the acceptance of a design, or the closing of an exploration with a result. A decision still under discussion stays on its work page or design page; it does not get a file here.

## Steps

1. **Number it.** Take the next free number in the [ADR index](../adr/README.md). Name the file `NNNN-short-title.md`.
2. **Fill the [template](../adr/template.md).** *Date* is the decision date, *Status* is `accepted`, and *Source* links the battle-plan issue and the design or work page that holds the discussion. Use only what was actually decided.
3. **Register it.** Add a row to the [ADR index](../adr/README.md), an entry under *Decisions* in `mkdocs.yml`, and a row to the [timeline](../architecture/timeline.md) log.
4. **Link it back.** The exploration, design or work page that led to it links the record; the exploration stays as the record of rejected options.

## Rules

- Records are never rewritten. A change of decision is a new record; mark the old one `superseded by ADR-NNNN`, link both ways, and add a timeline row.
- Corrections that do not change the decision (a broken link, a typo) are fine.
- Do not record trivial decisions (naming, formatting).
- "We just picked it" is not a rationale: every alternative names why it lost.
