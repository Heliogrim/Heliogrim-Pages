# Diagnostics (Design)

**Status**: design, accepted 2026-11-14 (draft 2026-11-13). Work chunk [W05.1](../plan/work/diagnostics-and-crash.md) (issue [#87](https://github.com/Heliogrim/Heliogrim-Engine/issues/87), system S05). Implementation is W05.2 (bundle plus ASL, built 2026-11-14, see section 10), W05.4 (ASL message wording) and W05.3 (storage, importers, serialisation, editor).

Markers: **Decided** = owner decision (the [work page](../plan/work/diagnostics-and-crash.md) Decisions table). **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

Failures are logged as strings, thrown as `std::runtime_error` or panic. Only the ASL compiler has a diagnostic type, and it carries a message and a line and column, nothing more. The engine wants diagnostics good enough to fix a problem from: a stable code that links to an explanation, every place involved, notes, and a fix the editor can apply with one click. One type serves every subsystem, so the editor, the log and a future language server render all of them the same way.

**Goals**

- One `Diagnostic` type in a new bottom bundle `Engine.Diagnostics`, used by every system's failure path.
- Stable codes (`ASL0042`) with a one-line summary and a docs page each; an unregistered code does not compile.
- Several locations per diagnostic (primary plus labelled secondaries), of four kinds: source span, asset, actor, byte offset in a blob.
- Fixes with text edits and an applicability level, so the editor offers a button only for safe fixes.
- A text renderer (golden-tested) and LSP 3.17 `Diagnostic` / `CodeAction` serialisation.
- A sink interface so compilers and importers can stream diagnostics to the log or an editor panel.

**Non-goals** (issue #87 "left for later"): an ASL language server, diagnostics over the network protocol, localised messages (S52), record-path fixes for binary assets (after S01).

**Anti-goals**

- Any cost on a hot path or a success path (**Decided**, Q05.1). Diagnostics live at system boundaries; inner code keeps small error enums and converts at the boundary.
- Wrapper towers at call sites (`Result<Optional<Result<...>>>`), or more than one way to propagate a failure (**Decided**, Q05.1: "shall not make interfaces over-complicated or un-ergonomic").
- A second diagnostic type next to the engine one. ASL's type becomes an alias, not a sibling.

## 2. What exists (checked 2026-11-13, `refactor/park-polling-waits` on top of `feat/wip`)

| Place | Today | Consequence for this design |
|---|---|---|
| `Engine.Accel.Lang/Ir/Diagnostic.hpp` | `struct Diagnostic { Severity; String message; u32 line, column; }`, `Diagnostics = Vector<Diagnostic>`; severities `eNote, eWarning, eError` | The seed. ASL already reports **many** diagnostics per failure, so multi-diagnostic results must stay one type, not a new wrapper. |
| ASL stage functions (`lex`, `parseModule`, `merge`, `lowerRegions`, `fixToggles`, ...) | `std::expected<T, Diagnostics>`; `typecheck` and `checkContract` return `Diagnostics` (empty = ok); `Module::warnings` keeps non-fatal ones | The migration swaps the element type only; signatures and the "empty list = ok" convention stay. About 170 emission sites in nine `.cpp` files. |
| ASL parser | Writes the module name into the message (`"in 'mod': "` + message, `Parser.cpp` `located`) | Message text stays as is during the migration (golden-identical); moving the module name into `Location` is a follow-up once the golden renderer exists. |
| ASL tokens | `Token { kind, text: StringView into the source, loc }` | A byte range is `text.data() - source.data()` and `text.size()`, so source spans come for free. |
| ASL tests | About 140 `.message` comparisons in 15 test files | Must keep passing unchanged: `message` stays a plain string field. |
| `Engine.Accel.Compile/Stage/StageIr.cpp` | Logs `warning.message` with `Logger::warn`, builds location-less failures (`"stage has no ir"`) | Needs a location-less diagnostic; becomes the first user of the log sink. |
| `Engine.Common/Expected.hpp` | `hg::Result<T, E>` over `tl::expected`, with `Expected` / `Unexpected` helpers | Is the `Result` in `Result<T, Diagnostic>`. No new result type. |
| Storage | `acq_error_type = Variant<AccessError, IllegalArgumentError, IllegalTypeError>`, `AccessError : std::runtime_error`; 23 `Result<..., std::runtime_error>` in headers | Inner error variants stay (internal enums, Q05.1); W05.3 converts them at the `StorageSystem` boundary. |
| Importers (`Engine.Resource.Import`) | Silent `return {}` on failure paths (work page W05.3) | W05.3 target. |

## 3. Layering

**Proposal** (resolves the tension noted on the work page):

```hg-diagram
flowchart BT
COM["Engine.Common"]
DIA["Engine.Diagnostics<br/>type, codes, renderer, LSP shape, sink interface"]
LOG["Engine.Logging<br/>LogSink"]
OBS["Engine.Observability (S04)"]
ASL["Engine.Accel.Lang"]
STO["Engine.Storage.*"]
EDI["Editor (S43 panel sink)"]
DIA --> COM
LOG --> DIA
OBS --> LOG
ASL --> DIA
STO --> DIA
EDI --> LOG
```

`Engine.Diagnostics` depends on `Engine.Common` only and has no sinks that write anywhere. `Engine.Logging` itself depends on `Engine.Common` only today, so adding `Engine.Diagnostics` beneath it makes no cycle. `Engine.Logging` gains a `LogSink` that renders a diagnostic and logs it at the matching level. Every bundle that reports diagnostics depends on `Engine.Diagnostics` directly. The editor panel sink comes with the S43 panel (W05.3).

## 4. Types

Namespace `hg::engine::diag`. Files: `Engine.Diagnostics/{Severity,Code,Location,Fix,Diagnostic,Sink,Render,Lsp}.hpp`, each with its `.cpp` where it has out-of-line code.

### 4.1 Severity

`enum class Severity : u8 { eHelp, eNote, eWarning, eError }`, ordered so `>= eWarning` reads naturally. **Proposal**: ASL's `eNote, eWarning, eError` map one to one; `eHelp` is new and maps to LSP `Hint`. No ASL or Accel code casts a severity to a number (checked), so the reordering is safe.

### 4.2 Code and registry

```cpp
struct DiagnosticCode {
    std::array<char, 4> domain;   // 3 or 4 upper-case letters, zero padded: "ASL", "SER", "STOR"
    u16 number;                   // 1..9999, rendered as 4 digits
};

struct DiagnosticCodeInfo {
    DiagnosticCode code;
    StringView key;               // kebab-case name used at call sites: "unmatched-brace"
    StringView summary;           // one line, shown in the code list
};
```

The docs slug is derived from the code (`asl/0002`, `slugOf(info)`), not stored, so it can never disagree with the number, and renaming a key never breaks a docs link.

Each reporting bundle owns one table and one accessor, in `<Bundle>/Diagnostic/Codes.hpp`:

```cpp
namespace hg::engine::accel::lang::codes {
    inline constexpr diag::DiagnosticCodeInfo table[] = {
        { { "ASL", 1 }, "unexpected-character", "unexpected character" },
        { { "ASL", 2 }, "unmatched-brace",      "unmatched closing brace" },
        // ...
    };
    consteval ref<const diag::DiagnosticCodeInfo> asl(StringView key_) { return diag::findCode(table, key_); }
}
// use: Diagnostic::error(codes::asl("unmatched-brace"), "unmatched '}'")
```

**Decided** (owner 2026-11-14, lookup refined from by-number to by-key the same day): call sites name a code by its key, not its number, so the call site says what went wrong and a reader never needs the table to decode `asl(42)`. `diag::findCode` is `consteval`; on a miss it calls a non-`constexpr` function (`unregisteredDiagnosticCode()`), so a misspelled or unregistered key is a **compile error** (exceptions are off, so no `throw`). That covers the issue's "a test fails if a code is used without a registry entry" at compile time. A `Diagnostic` stores `ptr<const DiagnosticCodeInfo>`, so it can only hold registered codes.

Tests (**Proposal**): each bundle's test checks its own table (domain spelled right, numbers unique and ascending, keys unique and kebab-case, summary non-empty). One aggregate test target, `Heliogrim-Engine.DiagnosticCodes.Test`, links every bundle with a table, checks domains are unique across bundles and writes `diagnostic-codes.json` (code, key, summary, slug) into the build directory. S64 turns that file into the site's code list and explanation stubs; this design only fixes the file's shape.

**Decided** (owner 2026-11-14): codes are per distinct failure kind, not per emission site, and there is **no placeholder or "unclassified" code**, also not during the migration. W05.2 groups ASL's ~170 sites into kinds (lexical, syntax, name resolution, type mismatch, borrow, stage validity, merge conflict, ...); a coarse kind may be split later with a new number. Numbers are never reused; keys may be renamed (call sites fail to compile until updated). ASL emits through a handful of helpers (`Parser::diagnostic`, the resolve warning lambda, the typecheck error helpers, `StageIr`'s `fail`), so those helpers take a code and each call site names one. Tests that build a diagnostic by hand use the builder with a real code.

**Proposal**: the aggregate test ships in W05.2 with the ASL table only; each W05.3 bundle adds its table to it when it migrates. The `consteval` miss trick is standard C++20 and is checked by hand once on both clang-cl and `cl` (a deliberately misspelled key must fail to compile); there is no runtime fallback.

**Proposal**: domains are three letters per reporting system, four only on a clash: `ASL` (shader language), `STO` (storage), `IMP` (importers), `SER` (serialisation), `EDT` (editor). The aggregate test owns the list.

### 4.3 Location

```cpp
struct NoLocation {};
struct SourceSpan { String file; u32 begin, end; u32 line, column; };   // byte offsets [begin, end); line and column 1-based, of `begin`
struct AssetPath  { String url; String recordPath; };                   // recordPath empty until S01 provides record paths
struct ActorPath  { u64 actor; String componentPath; };
struct ByteOffset { String blob; u64 offset, length; };
using Location = Variant<NoLocation, SourceSpan, AssetPath, ActorPath, ByteOffset>;
```

- Locations **own** their strings. A diagnostic regularly outlives the source buffer or asset that produced it (logged later, shown in the editor after the import job finished). The cost sits on the failure path only.
- **Proposal**: `column` counts bytes from the line start, a tab counts as one, matching ASL's existing `SourceLoc`. The byte range is what fixes and LSP use; line and column are for humans.
- `NoLocation` exists because boundaries such as `StageIr` ("stage has no ir") have nothing to point at. An ASL diagnostic with `line == 0` today becomes `NoLocation`.
- A `SourceSpan` with `begin == end` is a point: allowed where only a line and column are known (contract checks, resolve). Fixes need a real range, so a fix site must have its token.
- **Proposal**: for ASL, `SourceSpan::file` is the module name the parser already holds (`Parser::_name`); the lexer sees only a `StringView` and stays that way. The editor maps a module name to its asset when it renders.
- **Proposal**: `ActorPath::actor` is the raw actor guid or handle value as `u64`, so `Engine.Diagnostics` does not depend on the actor bundles; the editor resolves it. Builder's call if a better-typed handle is already in `Engine.Common`.

### 4.4 Fix

```cpp
enum class Applicability : u8 { eMachineApplicable, eMaybeIncorrect, eHasPlaceholders };
struct TextEdit { SourceSpan range; String replacement; };
struct Fix { String title; Vector<TextEdit> edits; Applicability applicability; };
```

**Decided** (Q05.2): text edits only in the first version (ASL source, text-form assets). The owner wants the edit kind to stay open for record edits. **Decided** (owner 2026-11-14): `edits` is a plain `Vector<TextEdit>` now; when S01 provides record paths, it becomes `Variant<Vector<TextEdit>, Vector<RecordEdit>>`. That change touches only `Fix`, its renderer and its LSP mapping, so a one-alternative variant today buys nothing.

The editor shows a fix button for `eMachineApplicable` only; `eMaybeIncorrect` is offered as a suggestion that needs a confirm; `eHasPlaceholders` is shown as text.

### 4.5 Diagnostic

```cpp
struct Label { Location at; String message; };

class Diagnostic {
public:
    struct Data {
        ptr<const DiagnosticCodeInfo> code;
        Severity severity;
        String message;
        Location primary;
        InlineVector<Label, 2> labels;
        Vector<String> notes;
        Vector<Fix> fixes;
    };

private:
    UniquePtr<Data> _data;   // one heap object per diagnostic; moved-from is empty
    // ...
};
using Diagnostics = Vector<Diagnostic>;
```

- **Cheap to move, deep to copy.** `sizeof(Diagnostic) == sizeof(void*)`; all content sits in one boxed `Data`, so carrying a `Diagnostic` in a `Result` adds one pointer and the success path never touches the box. **Decided** (owner 2026-11-14; changed from the work page's "move only" after the builder check): copying clones `Data`, because ASL copies whole modules including their warnings (`Regions.cpp` `Module out { mod_ }`); copies only happen where diagnostics already exist, so no hot path pays.
- **Builder**: `Diagnostic::error(code, message)`, `::warning`, `::note`, `::help` return a builder with `.at(Location)`, `.label(Location, message)`, `.note(message)`, `.fix(Fix)`; the builder converts implicitly to `Diagnostic` and to `hg::Unexpected<Diagnostic>`. Every builder function is out of line and marked cold, so failure-path code stays out of the caller's hot instruction stream.
- Read access by const accessors (`code()`, `severity()`, `message()`, `primary()`, `labels()`, `notes()`, `fixes()`). **Proposal**: `message()` returns the plain string, which keeps ASL's 140 test comparisons source-compatible after a one-token change (`.message` to `.message()`), done mechanically in W05.2.
- **Decided** (owner 2026-11-14): no arena. The work page said "arena string"; this design drops that because one allocation per failure is already off every hot path, and an arena adds a lifetime to manage. Revisit only if a measured failure storm (an import of thousands of broken assets) shows allocation cost.

### 4.6 Sink

```cpp
class DiagnosticSink {
public:
    virtual ~DiagnosticSink() = default;
    virtual void emit(Diagnostic&& diagnostic_) = 0;
};

class CollectingSink final : public DiagnosticSink { /* Diagnostics, hasErrors(), take() */ };
```

`LogSink` lives in `Engine.Logging` (renders one line per diagnostic, plus notes, and logs at the matching level). The editor panel sink is W05.3. Sinks are for **streaming** (warnings that do not fail the call, progress of a long import); the failure itself still travels in the `Result` (section 5).

## 5. Result convention

**Decided** (Q05.1): `Result<T, Diagnostic>` at system boundaries only.

- **Single failure**: `hg::Result<T, diag::Diagnostic>`.
- **Several failures** (compilers, validators): `hg::Result<T, diag::Diagnostics>`. Same type, a list as error; no new wrapper. ASL keeps its existing "returns `Diagnostics`, empty means ok" checkers (`typecheck`, `checkContract`).
- **Inner code** keeps its own small error enums or variants (`AccessError`, `IllegalTypeError`) and converts once at the boundary, where the location and code are known.
- **Proposal**: ASL keeps `std::expected` inside its stage functions (it uses it today and it is 16 bytes against 24 for `tl::expected` with a boxed error, measured below); the boundary rule names `hg::Result` for new APIs. W05.2 swaps only the error type in ASL.

**Decided** (owner 2026-11-14): **one propagation helper, no macro** (the alternative MSVC `cl` build has no statement expressions, and the S04 direction is macro-free). The owner asked for the name and wording to be checked; the result:

```cpp
auto mesh = loadMesh(path_);
if (not mesh) [[unlikely]] {
    return propagate(std::move(mesh), "while importing '{}'", path_);   // optional formatted note
}
use(*mesh);
```

`propagate(Result<U, E>&&, [fmt, args...])` returns `hg::Unexpected<E>` for `E` in {`Diagnostic`, `Diagnostics`}; with a note it appends the note to the diagnostic (for a list: to the last error). Propagating an empty `Diagnostics` is a precondition violation (an error list is never empty; "empty = ok" applies only to the checkers that return a bare list) and asserts. For `std::expected` call sites the standard `std::unexpected(std::move(r).error())` is already one line, so there is no second overload.

**Name check** (**Proposal**, refined 2026-11-14): `propagate` stays. It says what happens (the failure moves one level up, unchanged) and has no collision in `src/` (checked). Rejected: `forward` (clashes with `hg::forward`), `rethrow` (implies exceptions, which are off), `bail` (Rust's `bail!` creates a new error), `context` (names the note, not the act; the note is optional). The note argument is called *context* in the docs and parameter names (`context_`), following the established term for "what the caller was doing" (Rust `anyhow::Context`).

**Wording rules** (**Proposal**, for new messages; ASL keeps its text in W05.2 for the golden check, its wording is aligned in a later pass with new goldens):

- Message: starts lower-case, no trailing period, one sentence, names the thing in single quotes (`unmatched '}'`, `cannot borrow immutable 'a' as mutable`).
- Label: a short phrase about that place (`overlapping argument`, `first declared here`), no sentence.
- Context note: starts with `while` plus a gerund (`while importing 'rock.fbx'`, `while resolving stage 'fragment'`).
- Other notes: a full clause explaining why (`'shared' is reserved for region lowering`).
- Fix title: imperative, names the change (`make 'a' mutable`, `assign the default material`).

### 5.1 Measured: the success path is a plain value return

Throwaway check on clang-cl 22 (VS 18 toolset), `/O2 /EHs-c-`, function `Result<int> parse(int)` that fails with a boxed diagnostic for negative input:

| Variant | `sizeof` | Success path |
|---|---|---|
| `tl::expected<int, Diagnostic>` (today's `hg::Result`) | 24 | `test`, `js` (cold), `lea` (the work), two stores (value, has-value flag) into the caller's return slot, `ret`. No call, no allocation. |
| `std::expected<int, Diagnostic>` | 16 | same shape |
| propagating caller `twice(x) = parse(x) + 1` | 24 | call, test the flag, add, two stores, `ret`; the move of the error and the destructor call sit on the cold branch only |

The return goes through a caller-provided slot (the Win64 ABI does that for any type with a non-trivial destructor), as it does for any non-trivial return value. The only extra on the success path is the `/GS` stack cookie, caused by the temporary the failure branch builds in the frame; it disappears when the failure branch only calls an out-of-line builder that returns the finished `Unexpected` (section 4.5). W05.2 keeps the check as a disassembly note in the plan, not as a test.

## 6. Rendering

`String render(ref<const Diagnostic>, SourceLookup* sources_ = nullptr)` in `Engine.Diagnostics/Render.hpp`. `SourceLookup` is a one-function interface (`file → Optional<StringView>`).

Without source text:

```text
error[ASL0042]: '&mut' argument 'a' overlaps argument 'b'
  --> shader/forward.asl:12:9
  --> shader/forward.asl:12:14: overlapping argument
  = note: ...
  = help: <fix title>
```

With source text the primary and each `SourceSpan` label get a one-line snippet with a caret line (rustc style, no colours; the editor colours by severity). Other location kinds render as `--> asset <url>[#<record path>]`, `--> actor <id>/<component path>`, `--> blob <url> @ <offset>+<length>`.

Golden tests in `Engine.Diagnostics.Test` cover each location kind, labels, notes, fixes, with and without source. **Decided by the work page** for W05.2: ASL diagnostics render identical text before and after the migration; because ASL messages keep their text (section 2), the golden compares `message()`, and the new renderer gets its own golden files.

## 7. LSP shape

`Engine.Diagnostics/Lsp.hpp`: `String toLspJson(ref<const Diagnostic>)` and `String toLspCodeActionsJson(ref<const Diagnostic>)`, LSP 3.17.

| `Diagnostic` | LSP `Diagnostic` |
|---|---|
| primary `SourceSpan` | `range` (0-based line; `character` in UTF-8 bytes, the server must announce `positionEncoding: "utf-8"`); non-source primaries give `uri` from the asset or blob url and a 0:0 range |
| severity | `severity`: Error 1, Warning 2, Note 3 (Information), Help 4 (Hint) |
| code | `code: "ASL0042"`, `codeDescription.href`: site base plus `slug` |
| domain | `source`: lower-case domain (`"asl"`) |
| message plus notes | `message` (notes appended on new lines; LSP has no notes field) |
| labels with a `SourceSpan` | `relatedInformation[]` |
| fixes | `CodeAction { title, kind: "quickfix", diagnostics: [d], isPreferred: applicability == eMachineApplicable, edit: { changes: { uri: TextEdit[] } } }` |

**Proposal**: a small hand-written JSON writer inside `Lsp.cpp` (escaping plus objects and arrays, well under 100 lines), so the bottom bundle gains no vendor dependency. UTF-16 positions are a language-server concern (left for later); a server that cannot negotiate UTF-8 converts with the source text it already holds.

## 8. Migration order

Issue #87 order, with the work page's split:

| Step | Chunk | Bundle | Change | Done when |
|---|---|---|---|---|
| 1 | W05.2 | `Engine.Diagnostics` (new) | Types, builder, `propagate`, renderer, LSP, `CollectingSink`; tests | Goldens pass; `sizeof(Diagnostic) == sizeof(void*)` static assert |
| 2 | W05.2 | `Engine.Logging` | `LogSink` | A test logs one diagnostic per severity |
| 3 | W05.2 | `Engine.Accel.Lang`, `Engine.Accel.Compile` | `ir::Diagnostic` and `ir::Diagnostics` become aliases of the engine types; code table; every emission site gets a code and a `SourceSpan` from its token; `StageIr` logs through `LogSink` | All ASL and Accel tests pass with unchanged message text; one two-span diagnostic (the `'&mut' argument overlaps` case is the candidate) carries both spans; one fix applies in a test and the source recompiles clean (candidate: "cannot borrow immutable" with a fix that adds the mutability keyword, `eMachineApplicable`) |
| 4 | W05.2 | aggregate test | `Heliogrim-Engine.DiagnosticCodes.Test` and `diagnostic-codes.json` | JSON lists every ASL code |
| 5 | W05.3 | `Engine.Storage.*` | `StorageSystem` boundary converts `acq_error_type` / `pre_error_type` to `Diagnostic` with `AssetPath` or `ByteOffset` | A storage failure reaches the caller with a `STO` code |
| 6 | W05.3 | `Engine.Resource.Import` | Silent `return {}` paths return `Result<T, Diagnostics>`; mesh with a missing material slot gives an `AssetPath` diagnostic with a fix that assigns the default material | Issue #87's import acceptance test |
| 7 | W05.3 | `Engine.Serialization*` | Structure and layout failures at the archive boundary | Malformed archive gives `SER` diagnostic with `ByteOffset` |
| 8 | W05.3 (waits for S43) | Editor | Panel sink, fix button for `eMachineApplicable`, code links to the docs page | Issue #87's editor acceptance test |

The issue lists "importers" before "storage"; this design puts storage first because importers read through storage and should receive its diagnostics instead of inventing their own (**Decided**, owner 2026-11-14).

## 9. Left to the builder

- Exact file split inside `Engine.Diagnostics` and whether `Render` and `Lsp` share a helper for location text.
- How the ASL emission sites are grouped into codes (section 4.2 gives the rule, not the list).
- Wording of individual messages within the section 5 rules.
- Whether `propagate` formats with `std::format` or the logging bundle's formatter (it must not pull `Engine.Logging` into `Engine.Diagnostics`).
- The site base URL constant for `codeDescription.href`, as one constant beside the renderer.

## 10. As built (W05.2, 2026-11-14)

W05.2 implements sections 3 to 7 and migration rows 1 to 4 on `feat/diagnostics`. Where the build differs from the text above:

- `Diagnostic::Data::labels` is a `Vector<Label>`, not an `InlineVector`, because `InlineVector` has no copy constructor and section 4.5 requires a deep copy. The cost is one allocation per labelled diagnostic, and only on the failure path.
- ASL locations carry their byte range and their file. `ir::SourceLoc` gains `offset`, `length` and a `source` index, which the lexer fills. `ir::Module::sources` maps the index to a file name, merges remap it, and merge validation rejects an index out of range. A location inside an included module therefore names that module and keeps its range, and a fix applies there too.
- The ASL table has 67 codes, numbered in compiler phase order with the `internal-*` codes last. An `internal-*` code marks a compiler bug; its summary starts with `compiler bug:`, and the code test enforces this. Each code covers one failure kind. Numbers are frozen once the table is published.
- The LSP uri comes from `lspUriOf(diagnostic)`, which belongs in `PublishDiagnosticsParams`, because an LSP `Diagnostic` has no uri field.
- `StageIr` and `StageComposer` log through `LogSink`. Their old log prefixes became context notes (`while composing effect '<name>'`, `while checking module '<name>'`, `while checking the stage contract`).
- `propagate` formats with `std::format`. `codeDocsBase` sits beside the LSP mapping in `Lsp.hpp`.
- ASL messages are still byte-identical to the pre-migration text. Rewording them to the section 5 rules, with new golden tests, is chunk W05.4, which runs after W05.2 merges and before W05.3.
