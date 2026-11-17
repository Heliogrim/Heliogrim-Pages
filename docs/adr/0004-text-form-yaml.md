# ADR-0004: Canonical Text Form as a YAML Subset

**Date**: 2026-11-08 (owner, Q01.3)
**Status**: accepted (recorded 2026-11-16)
**Source**: [#83](https://github.com/Heliogrim/Heliogrim-Engine/issues/83), [serialisation work page](../plan/work/serialization-and-reflection.md)

## Context

Assets under version control need a text form that diffs line by line and re-saves byte-identically. The project vendors `ryml` already and has its own structured binary serialiser.

## Decision

The text form is a canonical YAML subset read and written through `ryml`: block style only, sorted keys, scalars typed by the schema and never guessed, numbers formatted by the engine and passed as plain scalars, binary as base64 or a blob hash, symbols as `@name`, unknown keys preserved as opaque subtrees. An own grammar is adopted only if the `ryml` emitter cannot be made deterministic under these rules; that check is the first step of the text-form design chunk.

## Alternatives Considered

### Own key-value grammar

- **Pros**: full control, one-to-one with the slot model.
- **Cons**: a parser and writer to maintain, no editor tooling.
- **Why not**: the vendored library already provides both ends.

### JSON

- **Pros**: strictest grammar, widest tooling, also supported by `ryml`.
- **Cons**: no comments, 64-bit integers do not survive many tools, the trailing-comma rule makes diffs touch the previous line.
- **Why not**: diffs and hand edits are the reason the text form exists, and JSON is worse at both.

## Consequences

### Positive

- No new dependency; comments allowed; one key per line diffs well.

### Negative

- YAML's implicit typing must be disabled by always typing from the schema; a reader that guesses types is a bug.

### Risks

- Emitter determinism is unverified until the design chunk runs its check.
