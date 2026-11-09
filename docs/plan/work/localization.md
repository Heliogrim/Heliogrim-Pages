# Work: Localisation

**Systems** S52 · **Issues** [#132](https://github.com/Heliogrim/Heliogrim-Engine/issues/132) · **Track** D · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Localisation](../topics/localization.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| [Vector UI work](vector-ui-uikit.md) | `TextService` with fallback chains; ICU footprint question shared (Q42.1) | Font fallback and RTL live in the canvas; this system supplies data |
| Research pass (2026-11-07) | ICU C++ MessageFormat 2 still a technical preview as of ICU 78 | Decides the syntax question by default (Q52.1) |
| [Reflection work](serialization-and-reflection.md) S09 | Gather through reflection over `Text` literals | Gather tool input |
| [Serialisation work](serialization-and-reflection.md) S41 | Canonical text manifest | Localisation manifest format |
| [Build work](build-and-deploy.md) S53 | Cook step | Compiles tables into packages |
| [Editor workflows work](editor-workflows.md) S54 | Workflow tests | Pseudo-locale golden test |

## Architecture

- **Bundles**: new `Engine.Localization` (`Text`, `Locale`, message formatting, string tables, runtime table loader), `Editor.Localization` (gather, stale and untranslated view, pseudo-locale toggle), `tools/loc` CLI (gather, export, import, compile).
- **Provides**: `Text` values rendered by uikit; plural, gender and ordinal formatting; collation and number and date formatting; pseudo-locale.
- **Consumes**: ICU or trimmed CLDR data, text service (S42), reflection (S09), manifest format (S41), cook (S53), uikit layout mirroring (S43).

## Code design

| Type | Contract |
|---|---|
| `Text` | `{ key, namespace, arguments }`; never a raw string in UI code (clang-tidy rule once the kit exists). |
| `MessageFormatter` | In-house Fluent-like subset over CLDR plural rules with MF2 syntax compatibility as a goal; swap to ICU MF2 when it leaves preview (Q52.1). |
| `StringTable` | Stable keys per namespace; source language plus translations; binary runtime form in packages. |
| `LocaleData` | Plural rules, collation, number and date formats from ICU (platform-integration vendor) or a trimmed extract (Q52.2). |
| `Gather` | Reflection over `Text` literals and asset strings → manifest (canonical text form); PO or XLIFF export and import; compile to binary tables. |
| `PseudoLocale` | Accents, 30 to 40% expansion, brackets, mirrored RTL; shipped in the editor; used by workflow tests. |
| Fallback and RTL | Font fallback chains per script in `TextService`; bidi mirroring through the uikit layout protocol. |

Placement: `Engine.Localization/{Text,MessageFormatter,StringTable,LocaleData,PseudoLocale}`, `Editor.Localization/`, `tools/loc/`. Tests: plural rendering in English, Polish, Arabic (RTL), Japanese (fallback font); pseudo-locale editor golden; CLI round trip.

## Work chunks

### W52.0 ICU status and footprint spike · explore · ready (two days)

- **Goal**: recheck ICU MF2 status and measure the footprint of full ICU versus a trimmed data build on clang-cl; decide Q52.1 and Q52.2 by evidence.
- **Output**: `architecture/localization-exploration.md`; ADR placeholder for the message syntax.

### W52.1 Localisation design · design · after W52.0, W42.1

- **Output**: `architecture/localization-design.md`; plan.

### W52.2 Implement `Text`, formatter, string tables, pseudo-locale · execute · after W52.1, W42.3

- **Done when**: a plural message renders correctly in the four test languages; the editor runs in the pseudo-locale.

### W52.3 Gather, export, import, compile CLI and editor views · execute · after W52.2, W09.2, W53.2

- **Done when**: the template project gathers, exports, imports and compiles translations from the command line; the pseudo-locale workflow test shows no untranslated string.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q52.2 | ICU with trimmed data. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q52.1 | Message syntax: in-house Fluent-like subset now with MF2 compatibility, or wait for ICU MF2? | W52.1 | In-house subset now |
| Q52.2 | ICU full or trimmed data (shared with Q42.1)? | W52.1 | Trimmed; measured in W52.0 |
