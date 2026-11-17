# Diagnostics, Observability and Crash Handling

**Systems**: S04, S05, S06 · **Track** A · **Milestone** M1
**Status**: <span class="hg-status summary">plan</span>. Research from [tooling](../sources/research-tooling.md) section 6 (Crashpad and MiniDumpWriteDump pages verified) and [editor and quality](../sources/research-editor-quality.md) section 8 (unverified). The [observability exploration](../../architecture/observability-exploration.md) holds the span design discussion.

## Target

- **Diagnostics with fix information**: one `Diagnostic` type used by the ASL compiler, importers, storage, serialisation, networking and the editor. A diagnostic has a stable code, severity, a primary location (source span, asset path, actor path or packet offset), labelled secondary locations, notes, and zero or more suggested fixes with an applicability level. The editor renders diagnostics with a fix button where the fix is machine-applicable. Codes have explanation pages on this site.
- **Observability**: fiber-aware spans with a near-zero inactive gate, counters, a lock-free per-lane ring buffer, export to a trace viewer and to OpenTelemetry for servers.
- **Crash handling**: an out-of-process handler writes a minidump with all threads, the fiber stacks of the crashing worker, the last log ring, loaded module and patch identities, and a deterministic crash ID. Dumps symbolise offline against a symbol store.

## Current state (checked 2026-11-07)

- `Engine.Accel.Lang/Ir/Diagnostic.hpp` exists for the ASL compiler. `Engine.Common` has a `Result` type. Logging goes through `Engine.Logging` (spdlog vendored) as strings.
- The JSON trace profiler, stopwatch and macros were dropped (ADR placeholder); nothing replaced them.
- No crash handler. No symbol store. No structured log schema.

## Research summary

- Rust's diagnostics model (primary and secondary spans, labels, notes, suggestions with applicability, error codes with long explanations) and clang's fix-it hints are the references; LSP 3.17 `Diagnostic` plus `CodeAction` with `WorkspaceEdit` is a ready transport for editor-side fixes. All unverified in this pass but well known.
- Crashpad (verified): out-of-process handler with minimal code in the crashed process, bounded local database, annotations (crash keys), custom streams, upload throttled to one per hour, embedder must handle consent.
- `MiniDumpWriteDump` (verified): Microsoft advises calling it from a separate process because of loader-lock deadlock risk; DbgHelp is single-threaded.
- Dumps from hot-reloaded builds must record patch and PDB identities or symbolisation fails (tooling report, design inference).
- OpenTelemetry's log data model (severity, body, attributes, trace and span correlation) is a usable schema even without the OTel runtime.
- Span pitfalls from the exploration: spans toggled mid-scope unbalance (use a depth counter or token); `__rdtsc` must be wrapped per compiler; measure our own gate overhead instead of trusting blog numbers.

## Guidance

### S05 Diagnostics framework

- Define `Diagnostic` in a new `Engine.Diagnostics` bundle below `Engine.Logging`: `{ code: DiagnosticCode, severity, message, primary: Location, labels: [Location + text], notes: [text], fixes: [Fix { title, edits, applicability }] }`. `Location` is a variant: source span (file, line, column range), asset path plus record path, actor handle plus component path, byte offset in a blob.
- `DiagnosticCode` is a namespaced identifier (`ASL0042`, `SER0007`) registered in a table with a one-line summary and a link to the explanation page. The table is generated into the docs.
- Fallible APIs return `Result<T, Diagnostic>`; `Diagnostic` is cheap to construct (arena-backed strings, no allocation on the success path). A `DiagnosticSink` collects many (compiler, importer) and is also the bridge to the log.
- Migrate the ASL compiler first (it already has spans), then importers and storage, then the editor's property panels. Serialise diagnostics in LSP shape so a future ASL language server costs nothing extra.
- Fixes: `edits` are text edits for source and record edits for assets; applicability is `MachineApplicable`, `MaybeIncorrect`, `HasPlaceholders`. The editor offers a button only for the first.
- Tests: a diagnostic's rendered text is golden-tested; a fix is tested by applying it and recompiling.

### S04 Observability

- Fiber context carries the current span; spans are `Span { id, parent, name (static), start, end, lane }` written to a per-worker ring buffer; inactive gate is one relaxed load and a branch.
- Counters are typed and registered once; frames are tagged so a trace viewer can align lanes.
- Export: a binary trace file for the in-editor viewer and for CI (frame-time percentiles are computed from it), and an OTLP exporter for server roles.
- Build tiers: Retail (spans compiled out except coarse ones), Playtest (spans on, sampling), Profile (everything).

### S06 Crash handling

- Vendor Crashpad under the vendor rules (platform integration) or write a thin equivalent: a handler process started at boot, a named-pipe registration, a client filter that signals it. Do not call `MiniDumpWriteDump` in-process except as a last-resort fallback.
- Annotations: engine version, loaded modules and hot-reload patch identities, process role, current scene, last diagnostic codes, the last N log records from the ring.
- Fiber stacks: the handler walks the current fiber's stack from the worker's saved context; register fiber stack ranges with the handler so the walker accepts them.
- Crash ID: hash of normalised top frames (module and function names, no addresses). Symbol store: PDBs keyed by GUID and age, uploaded by the build (S53).
- Consent and upload are product decisions; default off; local database only.

## Done when

- `Result<T, Diagnostic>` is returned by ASL, storage and importers; the editor shows a diagnostic with a working fix for one ASL error and one import error.
- The docs site lists every diagnostic code with an explanation page.
- A frame trace from the editor opens in the trace viewer with fiber lanes.
- A deliberate crash on a fiber in a test produces a dump whose symbolised stack names the test function.

## Open decisions

- Crashpad as a vendor dependency versus an in-house handler (size, build integration).
- Trace viewer: in-editor only, or also a Perfetto or Tracy export.
- Where the fiber-local context lives (stack top or control block), shared with the scheduler decision in [concurrency](concurrency-fibers.md).
