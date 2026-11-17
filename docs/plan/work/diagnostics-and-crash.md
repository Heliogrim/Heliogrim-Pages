# Work: Diagnostics, Observability, Crash Handling

**Systems** S04, S05, S06 · **Issues** [#86](https://github.com/Heliogrim/Heliogrim-Engine/issues/86), [#87](https://github.com/Heliogrim/Heliogrim-Engine/issues/87), [#88](https://github.com/Heliogrim/Heliogrim-Engine/issues/88) · **Track** A · **Milestone** M1
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Diagnostics, observability and crash handling](../topics/diagnostics-and-crash.md).

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Observability exploration](../../architecture/observability-exploration.md) | Goals (spans, histograms, memory, GPU timestamps, OTel), design points (fiber-local context, per-lane SPSC rings, inactive gate, rdtsc, macro-free API), the compile problems in the source sketches, three build tiers | Context location; buffer overflow policy; metered-run mode; capture format; which metrics go to OTLP |
| [ADR placeholder: drop trace profiler](../../adr/0002-trace-profiler.md) | Drop the old profiler, stopwatch and macros; no direct replacement | Not yet removed: `Engine.Common/Profiling` and its macro still have 15 users (checked 2026-11-10); S04 is the replacement and W04.1 removes them |
| [Fiber scheduler exploration](../../architecture/fiber-scheduler-exploration.md) | `FiberContext` in the control block is the likely home of the current span | Owned by S02 W02.1; S04 consumes it |
| [Audio runtime design](../../architecture/audio-runtime-design.md) | Keeps only a profiling hook | The hook must be the S04 span API |
| `Engine.Accel.Lang/Ir/Diagnostic.hpp` | A working diagnostic with spans for ASL | Becomes the first migration to the engine-wide type, not a second type |

Tension: the topic page puts `Engine.Diagnostics` below `Engine.Logging`; the exploration treats logging as a span sink. Resolution proposed here: `Engine.Diagnostics` (type only, no sinks) at the bottom; `Engine.Logging` depends on it and renders diagnostics; `Engine.Observability` depends on both.

## Architecture

- **Bundles**: new `Engine.Diagnostics` (type, codes, sink interface, LSP-shaped serialisation), new `Engine.Observability` (spans, counters, ring buffers, trace writer, OTLP exporter behind a flag), new `Engine.Crash` plus `Support.Crash.Win32` (handler process, client, annotations). `Engine.Logging` keeps spdlog as a sink.
- **Layer**: L2 services; `Engine.Diagnostics` has no engine dependency besides `Engine.Common`.
- **Provides**: `Diagnostic`, `Result<T, Diagnostic>` convention, `DiagnosticSink`; `Span`, `Counter`, trace file; crash client API and annotations.
- **Consumes**: `FiberContext` (S02), `Engine.Config` for tiers, S53 for symbol upload (later).

## Code design

| Type | Contract |
|---|---|
| `DiagnosticCode` | `{ domain: 3 or 4 letters, number: u16 }` (`ASL0042`, `SER0007`). Registered in a constexpr table per bundle with a one-line summary and a docs slug; the table is exported to the site (S64). Unknown codes fail a test. |
| `Location` | Variant: `SourceSpan { file, line, col range }`, `AssetPath { url, record path }`, `ActorPath { handle, component path }`, `ByteOffset { blob id, offset, length }`. |
| `Diagnostic` | `{ code, severity, message: arena string, primary: Location, labels: InlineVector<Label, 2>, notes, fixes }`. Constructed through a builder; the success path of `Result<T, Diagnostic>` allocates nothing. Move only. Superseded by the [design](../../architecture/diagnostics-design.md) 4.5: one boxed `Data`, deep copy (ASL copies modules with warnings), no arena. |
| `Fix` | `{ title, edits: variant<TextEdit[], RecordEdit[]>, applicability: MachineApplicable / MaybeIncorrect / HasPlaceholders }`. |
| `DiagnosticSink` | `emit(Diagnostic&&)`; implementations: collecting sink (compiler, importer), log sink, editor panel sink. |
| `Span` | `{ id, parent, name: static string, lane, begin, end }`. `ScopedSpan` RAII with a token so capture toggles mid-scope stay balanced. Inactive gate: one relaxed load, `[[unlikely]]` branch. Name metadata through a string-literal NTTP or `consteval`, checked on clang-cl (the exploration's compile problem). |
| `TraceRing` | Per-worker SPSC ring, pre-allocated at init; overflow policy from Q04.2; drained by a Background-lane task into the trace writer. |
| `Counter<T>`, `Gauge<T>`, `Histogram` | Registered once by static id; relaxed stores; histograms aggregated off the hot path. |
| `TraceWriter` | Binary frame-tagged file; reader in the editor and in CI (percentiles). OTLP exporter is a separate target behind a build flag. |
| `CrashClient` | `start(handler path, database path)`, `annotate(key, value)`, `registerFiberStacks(span<StackRange>)`. In-process code is the filter plus the pipe handshake. |
| `CrashId` | Hash of normalised top frames (module + function, no addresses). |

Placement: `Engine.Diagnostics/{Code,Location,Diagnostic,Sink}.hpp`, `Engine.Observability/{Span,Counter,TraceRing,TraceWriter}.hpp`, `Engine.Crash/Client.hpp`, `Support.Crash.Win32/Handler.cpp` (separate executable target `Heliogrim-CrashHandler`). Tests: golden-rendered diagnostics; a span balance test under toggling capture; a deliberate crash test that asserts the symbolised stack.

## Work chunks

### W05.1 Diagnostic type and code registry · design · done 2026-11-13 (accepted by the owner 2026-11-14)

- **Goal**: finalise `Diagnostic`, `Location`, `Fix`, code registry, LSP-shaped serialisation, the `Result<T, Diagnostic>` convention and the migration order (ASL, storage, importers, serialisation, editor). Constraint from Q05.1: boundary APIs only, no effect on hot paths (show the success path compiles to a plain value return), and the call-site ergonomics stay simple (one `try`-style propagation helper, no nested wrappers).
- **Inputs**: `Engine.Accel.Lang/Ir/Diagnostic.hpp`, `Engine.Common` `Result`, Rust and LSP 3.17 diagnostic models (abstract level is enough).
- **Output**: [Diagnostics design](../../architecture/diagnostics-design.md) (draft, builder-checked); plan `docs/superpowers/plans/2026-11-13-diagnostics-and-asl-migration.md` in the engine checkout, 7 tasks for W05.2 plus a W05.3 outline (storage, importers, serialisation, editor). Success path measured on clang-cl: compare, two stores, return; no call or allocation. Deviations from the code design above: `Diagnostic` copies deeply, no arena string, `Fix::edits` a plain text-edit list until S01 adds record edits, storage migrates before importers.
- **Questions**: Q05.1, Q05.2 (both decided).

### W05.2 Implement `Engine.Diagnostics` and migrate ASL · execute · done 2026-11-15 (PR [#188](https://github.com/Heliogrim/Heliogrim-Engine/pull/188) merged into `feat/wip` `c80f3569`)

- **Done when**: ASL compiler returns engine `Diagnostic`s with identical rendered text (golden); code table generated; one ASL fix applies and recompiles in a test.
- **Result (2026-11-14)**: nine signed commits on `feat/diagnostics`, one concern per commit, scoped by bundle: the diagnostic type, codes and `propagate`; text rendering; LSP JSON; the collecting sink; `feat(logging)` `LogSink`; the ASL migration; byte ranges and source files in ASL locations; two spans and the mutability fix; the aggregate code test. New bundles `Engine.Diagnostics`, `Engine.Diagnostics.Test`, `Engine.DiagnosticCodes.Test`. The ASL table has 67 codes, `ASL0001` to `ASL0067`, numbered in compiler phase order with the `internal-*` codes (compiler bugs) last. Each code covers one failure kind and has a plain-language summary; there is no placeholder code, and a misspelled key does not compile (checked on clang-cl only). ASL messages are byte-identical. Tests: Accel.Lang 483, Accel.Compile 45, Diagnostics 28, DiagnosticCodes 2, all pass. The `'&mut'` overlap diagnostic carries both argument spans (label `overlaps the '&mut' argument`). "cannot borrow immutable" offers `declare '<name>' with 'let'` (machine-applicable), which applies and recompiles clean in a test, inside included modules too.
- **Deviations from the design**: `Diagnostic::Data::labels` is a `Vector`, since `InlineVector` cannot be copied. `ir::SourceLoc` gains a byte range and a source index filled by the lexer. `ir::Module::sources` maps the index to the file name, so a location in an included module names its own file and keeps its range; merges remap the index, and merge validation rejects an index out of range. The LSP uri comes from `lspUriOf`, because an LSP `Diagnostic` has no uri field. StageIr and StageComposer log through `LogSink` with `while ...` context notes instead of the old prefixes.
- **Open**: the misspelled-key compile failure is unchecked on `cl`. `Heliogrim-AllTests` does not build on `feat/wip` itself (`Editor.UI.Init/EditorInit.cpp:40`, undeclared `initDefaultUi`); this branch does not touch that file.

### W05.4 Reword ASL messages to the diagnostic wording rules · execute · done 2026-11-16 (PR [#190](https://github.com/Heliogrim/Heliogrim-Engine/pull/190) merged into `feat/wip`; carets split out as [#189](https://github.com/Heliogrim/Heliogrim-Engine/issues/189)); before W05.3

- **Plan (2026-11-15)**: `docs/superpowers/plans/2026-11-15-asl-message-wording.md` in the engine checkout (untracked), six tasks: four rewording commits by compiler phase, with their test updates; code summaries and one golden render per code; then the branch gate. Calls the plan makes within the section 5 rules: type names are quoted; a second sentence becomes a note; the parser's `in '<module>': ` prefix is dropped, because every span now names its file; `lane`, `wave` and `lowering` are replaced in messages and in the ASL0045 summary; the `internal-*` codes have no golden, since no source reaches them, and a coverage test fails if any other code has none. Branch `refactor/asl-message-wording` off `feat/wip`.
- **Result (2026-11-15)**: seven signed commits off `feat/wip` `c80f3569`, scoped by bundle. Four reword ASL messages by compiler phase; one rewords the ASL0045 summary; two are tests, a shared module source lookup and one golden render for each of the 64 codes that are not `internal-*`. Messages follow the section 5 rules. Names, keys and type names are quoted. A second sentence became a note, for example `GLSL has no 8-bit stage interface variables`. The parser's `in '<module>': ` prefix is gone, since each span names its file. `lane`, `wave`, `lowering` and `derivat` are gone from user text. A test helper, `expectWording`, checks the rules on every diagnostic a test inspects. A coverage test fails if a code has no golden. Tests: Accel.Lang 490, Accel.Compile 45, Diagnostics 28, DiagnosticCodes 2, and every commit passes on its own. The per-task reviews and the six-lens branch review were all fixed into their origin commits.
- **Open**:
  - Several annotation names in parser messages are still unquoted (`@spec`, `@when`, `@tess_ctrl`, ...), so siblings disagree. The review found this after the one fix wave; the owner decides.
  - Some carets point at the wrong token (`break` and `discard` on `;`, the range and array-size spans). This is a span defect, not wording; the goldens pin it as it is.
  - `Heliogrim-Editor` and `Heliogrim-AllTests` still fail on `feat/wip` itself (`EditorInit.cpp:40`).

- **Done when**: every ASL message follows the [design](../../architecture/diagnostics-design.md) section 5 wording rules (lower-case, no trailing period, names in single quotes, no compiler jargon such as `ir`, lanes or waves); new golden tests pin the rendered text of each code; the code docs (S64) and the editor only ever show the final wording.
- **Why now**: W05.2 kept the old messages byte-identical so the migration could be checked against the old output. Rewording before W05.3 means storage and importer diagnostics follow the rules from the start.

### W05.3 Migrate storage, importers, serialisation; editor rendering · execute · after W05.2, S43 panel (editor part may wait)

- **Done when**: storage and importer failure paths return diagnostics (no silent `return {}`), the editor shows one import diagnostic with a fix button.

### W04.1 Span API, fiber context and ring buffer contract · design · after W02.1 (context location)

- **Goal**: span API without macros, inactive gate, ring buffer and overflow policy, trace file format, tiers.
- **Inputs**: exploration sections 2 to 4; `FiberContext` from W02.1; a micro-benchmark of the gate on this machine (part of the chunk).
- **Output**: `architecture/observability-design.md` with measured gate and span cost; plan.
- **Questions**: Q04.1, Q04.2, Q04.3.

### W04.2 Implement spans, counters, trace writer, viewer import · execute · after W04.1, W02.2

- **Done when**: a frame trace with fiber lanes opens in the chosen viewer; CI computes frame-time percentiles from the file; the audio design's hook compiles against the API.

### W04.3 OTLP export and server metrics · design+plan · after W04.2, S58

- **Goal**: metric selection and cost; exporter behind a flag.
- **Questions**: Q04.4.

### W06.1 Crash handler prototype · explore · ready

- **Goal**: prototype the in-house handler (Q06.1): a second process, pipe handshake, `MiniDumpWriteDump`, local dump database, symbol store layout; measure handler size and dump time; prototype the fiber stack registration with `MiniDumpWriteDump` from a second process.
- **Output**: `architecture/crash-handling-exploration.md` with the prototype's result and a recommendation.
- **Questions**: Q06.1, Q06.2.

### W06.2 Crash handling design and implementation plan · design · after W06.1, W04.1 (log ring)

- **Output**: `architecture/crash-handling-design.md`; plan.

### W06.3 Implement handler, client, annotations, crash ID, test · execute · after W06.2

- **Done when**: a deliberate crash on a fiber yields a dump whose symbolised stack names the test function; crash ID stable across two runs.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q05.1 | `Result<T, Diagnostic>` at system boundaries only. It shall not affect hot paths in any way, and it shall not make interfaces over-complicated or un-ergonomic. |
| Q04.1 | Own binary trace format plus a Perfetto converter; in-editor viewer waits for S43. The owner also profiles with Radeon Developer Panel (RGP) and AMD uProf, so spans should also be emitted as `VK_EXT_debug_utils` labels so RGP captures show the engine's stage names. |
| Q04.2 | Overwrite oldest with a dropped-count counter. |
| Q04.4 | First OTLP metrics: frame time percentiles, cell count, memory per subsystem, request queue depth. Server and node infrastructure is design-only until the client runs; W04.3 stays behind S58. |
| Q04.3 | Metered runs belong to S59, not S04. Scope as the owner states it: pre-determined, pre-coded or recorded runs with a deterministic time source, checkpointed, compared within tolerance bands rather than bit-perfect, for end-to-end visual and performance regression checks (for example repeating a fixed run after a shader or material change). S04 contributes the trace file and percentiles, S26 the image comparison, S61 the scene fixtures. |
| Q05.2 | Fixes carry text edits in the first version (ASL source, text-form assets). The `Fix` edit variant stays open for record edits once S01 provides record paths. |
| Q06.2 | Crash dumps stay in a local database. Next iteration attaches them to the project's bug and crash reports (issue flow); an upload path is a possible later step, so the design keeps the seam. |
| Q06.1 | In-house crash handler. "Crashpad" in earlier notes was a generic phrase for the need, not Google's library; nothing is vendored. [ADR placeholder](../../adr/0008-in-house-crash-handler.md). |

Batches 1 and 2 closed for this page. [ADR placeholders](../../adr/README.md): diagnostics at boundaries, in-house crash handler.

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q05.1 | Does `Result<T, Diagnostic>` replace `Engine.Common` `Result<T, E>` everywhere, or only at system boundaries (internal code keeps small error enums)? | W05.1 | Boundaries only; internal enums convert at the boundary |
| Q05.2 | Should diagnostics carry a fix for assets as record edits (needs S01 record paths) in the first version, or text edits only? | W05.1 | Text edits first; record edits after S01's record path exists |
| Q04.1 | Trace viewer: in-editor only, or also Perfetto or Tracy file export? | W04.1 | Write our binary format plus a Perfetto JSON converter in tools; in-editor viewer waits for S43 |
| Q04.2 | Ring overflow policy: drop newest, overwrite oldest, or stall the producer in Profile tier? | W04.1 | Overwrite oldest with a dropped-count counter |
| Q04.3 | Is the metered-run mode (deterministic time source for regression tests) in scope for S04 or for S59? | W04.1 | S59 |
| Q04.4 | Which metrics must reach OTLP for servers in the first cut? | W04.3 | Frame time percentiles, cell count, memory per subsystem, request queue depth |
| Q06.1 | Is Crashpad acceptable as a vendored dependency under the "platform integration" rule? | W06.1 | Yes if its build fits CMake without depcot; otherwise in-house |
| Q06.2 | Crash upload: local database only forever, or plan the consent and upload path now? | W06.1 | Local only; design leaves an upload seam |
