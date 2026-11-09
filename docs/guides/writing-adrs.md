# Documenting an ADR

ADRs are processed in the **engine project**: discussion, acceptance and numbering happen there. This repository documents the accepted result. Do not write an ADR here and treat it as decided.

## Steps

1. **Decide in the engine project.** The proposal, its discussion and its acceptance follow that project's process. The engine project assigns the number and the date.
2. **Copy the record here.** Name the file `NNNN-short-title.md` with the engine project's number. The [template](../adr/template.md) mirrors the expected format; keep the *Source* link to the engine issue or pull request.
3. **Register it.** Replace the matching placeholder, if any, add a row to the [ADR index](../adr/README.md) and an entry under *Decisions* in `mkdocs.yml`, and append a line to the [timeline](../architecture/timeline.md) log.
4. **Link the exploration** that led to it. The exploration stays as the record of rejected options.

## Placeholders

When an exploration reaches an outcome that should become an ADR, a page named `placeholder-*.md` may hold the draft. It carries a warning banner, no number and no acceptance date, and is replaced by the real record.

## Rules

- Records are never rewritten here. A change of decision is a new record in the engine project; mark the old one `superseded by ADR-NNNN` and link both ways.
- Do not alter the content of a processed record when copying it.
