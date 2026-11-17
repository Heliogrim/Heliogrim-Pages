# Diagnostics

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip`, 2026-11-16. Not on `master` yet.
**Modules** (see the [module map](../architecture/modules.md)): `Engine.Diagnostics` (type, codes, renderer, LSP JSON, sinks, `propagate`), `Engine.Logging` (`LogSink`), with `Engine.Accel.Lang` and `Engine.Accel.Compile` as the only users so far. Tests: `Engine.Diagnostics.Test`, `Engine.DiagnosticCodes.Test`, and the diagnostic tests in `Engine.Accel.Lang.Test`.
**Related**: [Diagnostics design](../architecture/diagnostics-design.md) (accepted; section 5 has the wording rules), [work page](../plan/work/diagnostics-and-crash.md) (W05.2 PR [#188](https://github.com/Heliogrim/Heliogrim-Engine/pull/188), W05.4 PR [#190](https://github.com/Heliogrim/Heliogrim-Engine/pull/190)), issue [#87](https://github.com/Heliogrim/Heliogrim-Engine/issues/87), caret defects [#189](https://github.com/Heliogrim/Heliogrim-Engine/issues/189), [Accel compiler integration](accel/compiler.md).

## Purpose

A diagnostic is a failure report good enough to fix the problem from: a stable code that links to an explanation, every place involved, notes that explain why, and fixes an editor can apply. `Engine.Diagnostics` holds one `Diagnostic` type for every subsystem, so the log, the editor and a future language server show all of them the same way.

It is built for failure paths at system boundaries. A `Diagnostic` costs one pointer on the success path and one heap object when it is created. Inner code keeps its own small error enums and converts at the boundary.

What it does not do yet: only the ASL compiler (`Engine.Accel.Lang`) and the stage composer (`Engine.Accel.Compile`) report diagnostics. Storage, importers, serialisation and the editor panel (design migration rows 5 to 8, chunk W05.3) are not migrated. There is no language server; the LSP JSON is only produced, never sent.

## Where it sits

```hg-diagram
flowchart BT
    COM["Engine.Common<br/>Result, Unexpected, Variant"]
    ASR["Engine.Asserts"]
    DIA["Engine.Diagnostics<br/>Diagnostic, codes, render, LSP, CollectingSink, propagate"]
    LOG["Engine.Logging<br/>LogSink"]
    LANG["Engine.Accel.Lang<br/>ASL code table, ir::Diagnostic aliases"]
    COMP["Engine.Accel.Compile<br/>StageIr, StageComposer"]
    DIA --> COM
    DIA --> ASR
    LOG --> DIA
    LANG --> DIA
    COMP --> DIA
    COMP --> LOG
```

`Engine.Diagnostics` links `Engine.Common` and `Engine.Asserts` only ([`CMakeLists.txt`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Diagnostics/CMakeLists.txt)). It has no sink that writes anywhere. `Engine.Logging` sits above it and owns `LogSink`, so the bottom bundle never pulls in spdlog.

A diagnostic travels like this:

```hg-diagram
flowchart LR
    SITE["emission site<br/>Diagnostic::error(codes::asl(key), msg).at(span)"]
    RES["Result / std::expected<br/>error = Diagnostic or Diagnostics"]
    WARN["Module::warnings<br/>(non-fatal)"]
    CTX["caller adds a context note<br/>propagate(...) or addNote"]
    SINK["LogSink::emit"]
    TXT["render()"]
    LOGR["Logger::error / warn / info"]
    LSP["toLspJson()<br/>(tests only today)"]
    SITE --> RES --> CTX --> SINK
    SITE --> WARN --> SINK
    SINK --> TXT --> LOGR
    RES -.-> LSP
```

## How it works

Namespace `hg::engine::diag`, folder [`src/Engine.Diagnostics`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Diagnostics).

| Type | File | What it is |
|------|------|------------|
| `Severity` | `Severity.hpp` | `eHelp, eNote, eWarning, eError`, ordered so `>= eWarning` reads naturally |
| `DiagnosticCode`, `DiagnosticCodeInfo` | `Code.hpp` | domain plus number (`ASL0042`); info adds the kebab-case key and a one-line summary |
| `Location` | `Location.hpp` | `Variant<NoLocation, SourceSpan, AssetPath, ActorPath, ByteOffset>` |
| `Fix`, `TextEdit`, `Applicability` | `Fix.hpp` | a titled list of text edits with a safety level |
| `Diagnostic`, `Label`, `DiagnosticBuilder` | `Diagnostic.hpp` | the report, its secondary places, and the only way to fill one |
| `DiagnosticSink`, `CollectingSink` | `Sink.hpp` | streaming interface and an in-memory sink |
| `render`, `SourceLookup` | `Render.hpp` | plain-text rendering, with source snippets when given the text |
| `toLspJson`, `toLspCodeActionsJson`, `lspUriOf` | `Lsp.hpp` | LSP 3.17 JSON |
| `propagate` | `Propagate.hpp` | moves a failure one level up, with an optional context note |
| `LogSink` | `Engine.Logging/LogSink.hpp` | renders and logs at the matching level |

### Codes, looked up by key at compile time

A code is a domain of three or four upper-case letters and a number from 1 to 9999, shown as `ASL0042`. Each reporting bundle owns one `constexpr` table and one `consteval` accessor. ASL's lives in [`Engine.Accel.Lang/Diagnostic/Codes.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang/Diagnostic/Codes.hpp):

```cpp
inline constexpr diag::DiagnosticCodeInfo table[] = {
	{ { { { "ASL" } }, 1 }, "unexpected-character", "character starts no token" },
	// ...
	{ { { { "ASL" } }, 41 }, "borrow-conflict", "borrow overlaps a live borrow or another argument" },
	// ...
};

consteval ref<const diag::DiagnosticCodeInfo> asl(const StringView key_) {
	return diag::findCode(table, key_);
}
```

Call sites name the key, never the number: `codes::asl("borrow-conflict")`. [`findCode`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Diagnostics/Code.hpp) is `consteval`. On a miss it calls `unregisteredDiagnosticCode()`, which is declared but deliberately not `constexpr` (and never defined), so a misspelled or unregistered key fails to compile. There is no runtime fallback and no placeholder code. Because the accessor is `consteval`, the key must be a literal; you cannot look up a code from a runtime string.

`formatCode` gives `ASL0042`; `slugOf` derives the docs slug `asl/0042` from the code, so renaming a key never breaks a link. A `Diagnostic` stores a `ptr<const DiagnosticCodeInfo>` into the static table.

### Locations

```cpp
struct NoLocation {};
struct SourceSpan { String file; u32 begin, end; u32 line, column; }; // bytes [begin, end); line, column 1-based, of begin
struct AssetPath  { String url; String recordPath; };
struct ActorPath  { u64 actor; String componentPath; };
struct ByteOffset { String blob; u64 offset, length; };
using Location = Variant<NoLocation, SourceSpan, AssetPath, ActorPath, ByteOffset>;
```

Locations own their strings, because a diagnostic outlives the buffer it came from (it is logged later or shown after the job ended). A `SourceSpan` with `begin == end` is a point. The byte range is for fixes and LSP; line and column are for people. A column counts bytes, and a tab is one column. Only `SourceSpan` is produced today; the other kinds are rendered and tested but have no producer.

### Building a diagnostic

[`Diagnostic.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Diagnostics/Diagnostic.hpp) holds all content in one boxed `Data` (`UniquePtr<Data>`), so `sizeof(Diagnostic) == sizeof(void*)` (a `static_assert` in `DiagnosticTest.cpp` pins it). The four factories `error`, `warning`, `note` and `help` return a `DiagnosticBuilder`; `at`, `label`, `note` and `fix` chain on it:

```cpp
_diags.emplace_back(
	ir::Diagnostic::error(
		codes::asl("borrow-conflict"),
		"'&mut' argument '" + ir::describePlace(_mod, *mine) + "' overlaps argument '" + ir::describePlace(_mod, other) +
		"' of call to '" + name_ + "'"
	)
	.at(spanIn(_mod, _mod.exprs[operands_[index_].index].loc))
	.label(spanIn(_mod, _mod.exprs[operands_[j].index].loc), "overlaps the '&mut' argument")
);
```

(From [`Typecheck.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang/Ir/Typecheck.cpp), lightly reflowed.)

The builder converts to `Diagnostic`, to `Unexpected<Diagnostic>` and to `Result<T, Diagnostic>`, so `return Diagnostic::error(...).at(...);` works in a function returning `hg::Result<T, diag::Diagnostic>`. Every builder function and factory is out of line and `[[gnu::cold]]`.

Rules that bite:

- **Builder methods are `&&`-qualified.** A named builder must be moved before each call: `std::move(diagnostic).fix(...)` (see `deniedBorrow` in `Typecheck.cpp`).
- **Copy is deep, move is cheap.** Copying clones `Data`; ASL copies whole modules including their warnings, so this is needed. A moved-from or default-constructed `Diagnostic` is empty; every accessor (`code()`, `message()`, ...) and mutator (`addNote`, `setMessage`, `setPrimary`) asserts on an empty one. Check `empty()` first if you are not sure.
- **The primary defaults to `NoLocation`.** Forgetting `.at(...)` is not an error; the diagnostic just renders without a `-->` line.
- **The code must come from the table.** The factories take `ref<const DiagnosticCodeInfo>` and keep its address. A code info built on the stack would dangle; always go through the bundle's accessor.

### Fixes

```cpp
enum class Applicability : u8 { eMachineApplicable, eMaybeIncorrect, eHasPlaceholders };
struct TextEdit { SourceSpan range; String replacement; };
struct Fix { String title; Vector<TextEdit> edits; Applicability applicability; };
```

Only text edits exist; record edits for binary assets wait for record paths (S01). The engine has no code that applies a fix. The one fix in the codebase, `declare '<name>' with 'let'` for "cannot borrow immutable", is applied by a helper inside `IrDiagnosticTest.cpp` (edits sorted back to front by `begin`) and the result recompiles clean, also when the `const` sits in an included module (`BorrowImmutableInIncludeFixesTheInclude`).

### Result at boundaries, and `propagate`

The convention is `hg::Result<T, diag::Diagnostic>` for a single failure and `hg::Result<T, diag::Diagnostics>` for compilers and validators that report several. `Diagnostics` is `Vector<Diagnostic>`. ASL keeps `std::expected<T, Diagnostics>` in its stage functions, and its checkers (`typecheck`, `checkContract`, `checkStageChain`) return a bare `Diagnostics` where empty means ok.

[`Propagate.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Diagnostics/Propagate.hpp) is the one propagation helper. There is no macro.

```cpp
auto mesh = loadMesh(path_);
if (not mesh) [[unlikely]] {
	return propagate(std::move(mesh), "while importing '{}'", path_);
}
use(*mesh);
```

`propagate(Result<U, E>&&)` returns `Unexpected<E>` for `E` in {`Diagnostic`, `Diagnostics`}. With a format string it appends a context note, formatted with `std::format`; for a list the note goes to the **last** diagnostic only. It asserts that the result holds an error and that the error is not empty. It does not accept `std::expected`; there `std::unexpected(std::move(r).error())` is already one line. No engine code calls `propagate` yet; only `DiagnosticTest.cpp` does.

### Sinks

```cpp
class DiagnosticSink {
public:
	virtual ~DiagnosticSink() = default;
	virtual void emit(mref<Diagnostic> diagnostic_) = 0;
};
```

Sinks are for streaming: warnings that do not fail a call, progress of a long job. The failure itself still travels in the `Result`.

- `CollectingSink` keeps diagnostics in order, tracks `hasErrors()`, and `take()` hands them out and resets. It has no lock and no user outside its test.
- [`LogSink`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Logging/LogSink.cpp) renders the diagnostic **without** source text, strips the last newline and logs the whole multi-line text in one call: error to `Logger::error`, warning to `Logger::warn`, note and help to `Logger::info`. It is stateless, so callers create one on the stack where they need it.

### Text rendering

`String render(ref<const Diagnostic>, ptr<const SourceLookup> sources_ = nullptr)` in [`Render.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Diagnostics/Render.cpp). `SourceLookup` has one function, `Optional<StringView> find(StringView file_) const`. The order of lines is fixed: header, primary, labels with a location, labels without one (`  = <message>`), notes, fix titles as `help`.

The `borrow-conflict` golden from `IrDiagnosticGoldenTest.cpp`, rendered with source:

```text
error[ASL0041]: '&mut' argument 'x' overlaps argument 'x' of call to 'F'
  --> M:4:4
  |
4 | 	F(x, x);
  |    ^
  --> M:4:7: overlaps the '&mut' argument
  |
4 | 	F(x, x);
  |       ^
```

Without a `SourceLookup` the snippet lines disappear and only the `-->` lines stay. Other location kinds render as `--> asset <url>[#<record>]`, `--> actor <id>/<component>` and `--> blob <blob> @ <offset>+<length>`, without a snippet. The caret line starts at `column - 1` spaces and is as wide as the byte range (at least one, clipped to the line). If the file is not found or the line is past the end, the snippet is left out silently.

### LSP JSON

[`Lsp.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Diagnostics/Lsp.cpp) has its own small JSON writer, so the bottom bundle has no vendor dependency. Keys come in a fixed order, which makes the output golden-testable.

| `Diagnostic` | LSP 3.17 |
|---|---|
| primary `SourceSpan` | `range`: 0-based line, `character` in UTF-8 bytes; any other primary gives `0:0`-`0:0` |
| severity | `severity`: error 1, warning 2, note 3, help 4 |
| code | `code: "ASL0041"`, `codeDescription.href` = `codeDocsBase` + slug |
| domain | `source`: lower-case domain, `"asl"` |
| message and notes | `message`, notes appended on new lines |
| labels with a `SourceSpan` | `relatedInformation[]` (other labels are dropped) |
| fixes | `toLspCodeActionsJson`: one `quickfix` `CodeAction` per fix, `isPreferred` only for `eMachineApplicable`, edits grouped by file in first-seen order |

An LSP `Diagnostic` has no uri. `lspUriOf` gives the uri for the enclosing `PublishDiagnosticsParams`: the span's file, the asset url or the blob name, empty otherwise. `codeDocsBase` is `https://heliogrim.github.io/Heliogrim-Pages/reference/diagnostics/`.

## ASL and Accel.Compile

ASL was the first and is still the only migration. [`Ir/Diagnostic.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang/Ir/Diagnostic.hpp) makes `ir::Diagnostic`, `ir::Diagnostics`, `ir::Severity` and `ir::SourceSpan` aliases of the engine types; there is no second type.

**Spans.** The lexer fills `ir::SourceLoc` with line, column, a byte `offset` and `length`, and a `source` index. `Module::sources` maps the index to a file name, and merge remaps it. `ir::spanIn(mod, loc)` turns a location into a `SourceSpan` whose `file` is the module or include name, so a diagnostic inside an included module names that module and its own byte range. `pointAt(file, loc)` does the same for a known file name; the parser uses it with its module name.

**Emission helpers.** Almost every site goes through a few helpers that take a code:

| Where | Helper |
|-------|--------|
| [`Parser.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang/Ir/Parser.cpp) | `Parser::diagnostic(code, token, message)`, `error(code, token, message[, note])` |
| [`Typecheck.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang/Ir/Typecheck.cpp) | `error(code, message[, note])` at the current location; `deniedBorrow` adds the fix |
| [`StageIr.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Compile/Stage/StageIr.cpp) | `fail(code, message)`: one error at `NoLocation`, for failures with nothing to point at |

The lexer, merge, resolve, regions, layout, contract, lower and the GLSL emitter build diagnostics directly with the builder.

**Logging in the compiler.** Nothing in `Engine.Accel.Lang` logs. `Engine.Accel.Compile` does, through `LogSink`, and adds a context note first:

- `resolveStageIr` logs each input module's `warnings` with `while checking module '<name>'` (merge drops warnings, so they are read from the inputs), and contract warnings with `while checking the stage contract`.
- `StageComposer::compose` logs every error of a failed `composePipelineIr` with `while composing effect '<name>'` and returns an empty result.

## The ASL code table

67 codes, `ASL0001` to `ASL0067`, numbered in compiler phase order. Each code is one failure kind, not one emission site. Numbers are frozen once published; keys may be renamed (call sites then fail to compile until updated).

| Numbers | Phase |
|---------|-------|
| 0001-0008 | lexer, directives, includes |
| 0009-0016 | grammar, nesting, reserved names, annotations |
| 0017-0022 | toggles and `@when` variant bodies |
| 0023-0028 | declarations |
| 0029-0037 | names, types, calls, ranges |
| 0038-0042 | mutability, borrows, constants |
| 0043-0048 | control flow, uniformity, stage features, regions |
| 0049-0055 | merge and layout conflicts |
| 0056-0062 | bind classes, contracts, stage chain, vertex offsets |
| 0063-0064 | GLSL emission |
| 0065-0067 | `internal-*`: compiler bugs, summary starts with `compiler bug:` |

`internal-*` codes mark a state no shader source should reach (for example `StageIr`'s "stage has no shader code"). A user who sees one has found a compiler bug.

### Tests that guard the table and the wording

All in `Engine.Accel.Lang.Test`:

- `Codes.TableIsWellFormed` ([`CodesTest.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang.Test/CodesTest.cpp)): domain `ASL`, numbers 1, 2, 3, ... without gaps, keys unique and kebab-case, summaries non-empty, `internal-` key if and only if the summary starts with `compiler bug: `.
- `Codes.SummariesFollowWording`: summaries start lower-case, have no trailing period, and do not contain `lane`, `wave`, `derivat`, or the words `ir` and `lowering`.
- `IrDiagnosticGolden.EveryCode` ([`IrDiagnosticGoldenTest.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang.Test/IrDiagnosticGoldenTest.cpp)): one row per code with a source, a function that produces diagnostics, and the expected `render` output with source. It runs `expectWording` on the hit.
- `IrDiagnosticGolden.CoversEveryCode`: every non-`internal-*` code has exactly one golden row, `internal-*` codes have none, and the table has 64 rows. Adding a code without a golden fails here.
- `expectWording` ([`IrWording.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Accel.Lang.Test/IrWording.hpp)): message and labels start lower-case (a leading `GLSL` or `Vulkan`, or a quote, is allowed), nothing ends in a period, and a note that starts with `while` continues with a space.
- `IrDiagnosticTest.cpp`: the two-span overlap, the fix that recompiles, and that errors and merged nodes in included modules name their own file.

## diagnostic-codes.json

`Engine.DiagnosticCodes.Test` ([`CodesExportTest.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.DiagnosticCodes.Test/CodesExportTest.cpp)) is the aggregate over every bundle's table. It holds a list of table spans (only ASL today) and runs two tests:

- `DomainsUnique`: no two tables share a domain (it compares each table's first entry).
- `ExportWritesEveryCode`: writes `diagnostic-codes.json` into the **current working directory** of the test run, sorted by code, and checks that it holds one object per code.

```json
[{"code":"ASL0001","key":"unexpected-character","summary":"character starts no token","slug":"asl/0001"}, ...]
```

The file is the input for the site's code list and explanation pages (S64). Nothing consumes it yet, and no `reference/diagnostics/` pages exist, so the `codeDescription.href` links in LSP output lead nowhere today.

## Walkthrough: add a code, emit it, word it, test it

**1. Pick or add the code.** Reuse a code if the failure is the same kind as an existing one; codes are per kind, not per site. Otherwise append a row to the bundle's table with the next number. Never reuse or renumber. The key is kebab-case and says what went wrong. The summary is one lower-case line without a period that describes the kind, not one instance. A compiler-bug code starts its key with `internal-` and its summary with `compiler bug: `. The row below is a made-up example:

```cpp
{ { { { "ASL" } }, 68 }, "missing-entry-point", "module has no 'main' function" },
```

A new bundle gets its own `<Bundle>/Diagnostic/Codes.hpp` with a table and a `consteval` accessor like `codes::asl`, and its table goes into the `tables` array in `CodesExportTest.cpp` (and its library into that test's `CMakeLists.txt`). A four-letter domain cannot be written as a string literal (`"STOR"` needs five chars with its terminator, `domain` holds four); spell it as characters.

**2. Emit it.** Use the bundle's helper if there is one; otherwise the builder:

```cpp
return Diagnostic::error(codes::asl("missing-entry-point"), "module '" + mod_.name + "' has no 'main' function")
	.at(spanIn(mod_, loc_))
	.note("every stage module needs exactly one 'main'");
```

A secondary place is a `.label(span, "first declared here")`. A fix is `.fix(Fix { "add an empty 'main'", { TextEdit { span, "fn main() {}\n" } }, Applicability::eMaybeIncorrect })`; use `eMachineApplicable` only when applying it blind is always right, because the editor will offer it as a one-click button.

**3. Word it** ([design section 5](../architecture/diagnostics-design.md#5-result-convention)):

| Part | Rule | Example |
|------|------|---------|
| message | starts lower-case, no trailing period, one sentence, names things in single quotes, type names quoted | `cannot borrow immutable 'a' as mutable` |
| label | a short phrase about that place, not a sentence | `overlaps the '&mut' argument` |
| context note | `while` plus a gerund | `while composing effect 'pp'` |
| other note | a full clause that explains why; a second sentence of a message becomes a note | `GLSL has no 8-bit stage interface variables` |
| fix title | imperative, names the change | `declare 'a' with 'let'` |

No compiler jargon in user text: no `ir`, `lowering`, lanes, waves or derivats. Say "invocations", "compile step".

**4. Test it.** For ASL, add one row to the golden table in `IrDiagnosticGoldenTest.cpp`: the key, a minimal source, a producer (`parseD<...>`, `resolveD`, `mergeD`, ...) and the expected render. Run the test once with an empty expectation and copy the `ACTUAL[...]` text from the failure, after checking it by eye. `CoversEveryCode` checks the row count (`64uz`), so raise it. For a new bundle, add a table test like `CodesTest.cpp` and render goldens of your own; the generic renderer and LSP tests live in `Engine.Diagnostics.Test`.

```text
rtk cmake --build .\cmake-build-debug-visual-studio-clang --target Heliogrim-Engine.Accel.Lang.Test -j 7
rtk .\dist\Debug\amd64-windows\Heliogrim-Engine.Accel.Lang.Test.exe --gtest_color=no --gtest_filter=Codes.*:IrDiagnostic*:IrWording.*
rtk cmake --build .\cmake-build-debug-visual-studio-clang --target Heliogrim-Engine.DiagnosticCodes.Test -j 7
rtk .\dist\Debug\amd64-windows\Heliogrim-Engine.DiagnosticCodes.Test.exe --gtest_color=no
```

## Debugging

| Symptom | Cause |
|---------|-------|
| compile error "call to consteval function ... is not a constant expression", pointing at `unregisteredDiagnosticCode` | the key passed to `codes::asl(...)` is misspelled or not in the table |
| assertion in `Diagnostic::message()` or another accessor | the diagnostic is empty: moved from, or default-constructed |
| assertion in `propagate` | called on a success result, or on an empty `Diagnostics` list |
| log shows the diagnostic but no source line and caret | expected: `LogSink` renders without a `SourceLookup` |
| a warning from a shader is logged once, then never again | module warnings are logged inside the variant cache's build function, so a cache hit does not log them |
| the same error is logged on every compose | expected: a failing variant is not cached and is reported again |
| `Failed to lay out ir stages: <message>` without a code | `StageComposer` logs `appendBindLayout` clashes with `Logger::error` and the message only, not through `LogSink` |
| caret on the wrong token (`break`, `discard`, ranges, array sizes) | span defect [#189](https://github.com/Heliogrim/Heliogrim-Engine/issues/189); the goldens pin the current carets |
| caret looks shifted under tab-indented code | the snippet line keeps the tab, the caret line pads with spaces (a tab is one column); see `M:4:4` above |
| `codeDescription.href` 404s | no code pages are published yet (S64) |

## Limits and known issues

- **Only ASL is migrated.** Storage, importers, serialisation and the editor still log strings, throw or return `{}` (W05.3). `AssetPath`, `ActorPath` and `ByteOffset` have no producer; `CollectingSink` and `propagate` have no engine caller.
- **Not every compiler log is a diagnostic.** The layout clash in `StageComposer` and `"Ir stage skips profile '...' modules without ir"` in `StageIr` go to `Logger` directly.
- **Single-line LSP ranges.** `SourceSpan` has no end line, so the LSP range ends on the start line at `column + length` (a `shortcut:` in `Lsp.cpp`). Fix edits that span lines get the same treatment.
- **LSP uris are file names.** `SourceSpan::file` is the ASL module or include name (`M`, `shared/math.asl`), not a `file://` uri. A language server has to map it.
- **No fix applier in the engine.** Only a test helper applies edits.
- **Parser annotation names are not all quoted** (`@spec`, `@when`, `@tess_ctrl`, ...), so some sibling messages disagree on quoting; left open after W05.4.
- **The misspelled-key compile failure is checked on clang-cl only**, not on MSVC `cl`.
- **`LogSink` has no capture hook.** `LogSinkTest` only checks that each severity path runs; it cannot assert what was logged.
- **`labels` is a `Vector<Label>`**, not the `InlineVector<Label, 2>` of the design, because `InlineVector` cannot be copied (a `shortcut:` in `Diagnostic.hpp`). One extra allocation per labelled diagnostic, on the failure path only.

## Changing it

- The bundle is small: `Code`, `Diagnostic`, `Render`, `Lsp` and `Sink` each have a `.hpp` and `.cpp`; `Severity`, `Location`, `Fix` and `Propagate` are header-only. Keep it on `Engine.Common` and `Engine.Asserts` only; anything that writes (log, editor, file) belongs in a sink in a higher bundle.
- A new location kind touches `Location.hpp`, `appendLocation` in `Render.cpp`, `lspUriOf` and the range code in `Lsp.cpp`, and their tests (`Render.EachLocationKind`, `Lsp.AssetPrimary`).
- Record edits (after S01) change `Fix::edits` into a variant; that touches `Fix.hpp`, the fix line in `render` and `toLspCodeActionsJson` only.
- A change to the render format changes every golden in `Engine.Diagnostics.Test/RenderTest.cpp` and all 64 rows in `IrDiagnosticGoldenTest.cpp`. A change to the JSON changes `LspTest.cpp`.
- Rewording an ASL message changes its golden row and any `.message()` comparison in the other `Ir*Test.cpp` files; `expectWording` runs in most of them.
- Tests: `Heliogrim-Engine.Diagnostics.Test` (code format, builder, copy and move, `propagate`, render goldens, LSP, sinks, `LogSink` smoke test), `Heliogrim-Engine.DiagnosticCodes.Test` (domains, JSON export), and in `Heliogrim-Engine.Accel.Lang.Test`: `CodesTest`, `IrDiagnosticGoldenTest`, `IrDiagnosticTest`, `IrWordingTest`.
