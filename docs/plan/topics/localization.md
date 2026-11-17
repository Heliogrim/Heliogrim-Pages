# Localisation

**Systems**: S52 · **Track** D · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Research from [UI, editor, tooling, quality](../sources/research-editor-quality.md) section 7 (all unverified).

## Target

Good localisation support: messages with plurals, gender and ordinals from CLDR data; string tables with stable keys; a gather, translate and compile pipeline; pseudo-localisation in the editor and in UI tests; per-run font fallback and right-to-left layout through the text service; locale-aware collation and formatting in the editor and in games.

## Current state (checked 2026-11-07)

- Nothing. UI strings are literals in editor code.

## Research summary (all unverified)

- ICU provides CLDR locale data, formatting, collation, break iterators and normalisation; plural categories come from CLDR plural rules (UTS #35). MessageFormat 2.0 was declared stable in CLDR 47 (March 2025, search summary) but ICU's C++ implementation was still a technical preview as of ICU 78 and the ICU user guide page is stale (verified 2026-11-07), so a C++ MF2 dependency is not production-ready today; Mozilla Fluent influenced it; gettext is mature but weak on complex grammar.
- Unreal's pipeline: gather text from source and assets, manifest and archive, PO or XLIFF export, compile to a runtime format; string tables for shared keys.
- Pseudo-localisation (accents, 30 to 40% expansion, brackets, mirrored RTL) finds hard-coded strings and layout breaks before translators exist.
- Font fallback per script and bidi mirroring feed back into UI layout.

## Guidance

- `Engine.Localization` with a typed `Text` value (`{ key, namespace, arguments }`) that the uikit renders; string concatenation in UI code is a clang-tidy violation once the kit exists.
- Message syntax: ICU's C++ MessageFormat 2 is still a technical preview (ICU 78), so the default expectation is an in-house Fluent-like subset over CLDR plural rules with MF2 syntax compatibility as a design goal; the decision is recorded as an ADR after a two-day spike that rechecks ICU's status.
- CLDR data through ICU (platform-integration vendor) or a trimmed extract; measure the footprint; collation and number and date formatting come from the same source.
- Pipeline: gather (reflection over `Text` literals and asset strings, S09), manifest in the canonical text form (S41), PO or XLIFF export for translators, compile to a binary table in packages (S53); the editor shows untranslated and stale keys.
- Pseudo-locale shipped in the editor and used by the workflow tests (S54); RTL mirroring through the uikit's layout protocol; font fallback chains per script in the text service (S42).

## Done when

- The editor runs in a pseudo-locale with no visible untranslated string and no clipped layout in the golden workflow test.
- A plural message renders correctly in English, Polish, Arabic (RTL, mirrored layout) and Japanese (fallback font).
- A game project gathers, exports, imports and compiles translations from the command line.

## Open decisions

- MessageFormat 2 versus an in-house Fluent-like syntax.
- ICU full versus trimmed data.
