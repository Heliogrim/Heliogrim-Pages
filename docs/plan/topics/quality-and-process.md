# Quality and Process

**Systems**: S10, S26, S61, S62, S63, S64 · **Track** F · **Milestone** M1 onward
**Status**: <span class="hg-status summary">plan</span>. Research from [UI, editor, tooling, quality](../sources/research-editor-quality.md) section 8 (all claims there are unverified; see its caveat).

## Target

"Enterprise or military grade" is a measurable state, not a tone. For Heliogrim it means:

1. A written C++ standard with a tool that enforces it on every pull request.
2. Every public type and function carries a contract (preconditions, ownership, thread or fiber context) and at least one test.
3. Every failure path returns a [diagnostic](diagnostics-and-crash.md) a human can act on. No `todo_panic`, no silent `return {}` on a shipped path.
4. Sanitizers, static analysis, fuzzing of every loader and a performance band run in CI; a regression blocks the merge.
5. Traceability: issue "done when" items name the tests that prove them; the commit names the issue through the PR.
6. Documentation is generated for the public surface and written per shipped system.

## Current state (checked 2026-11-07)

- `STYLE.md`, `.clang-format` and `.resharper-format.xml` define formatting and layout rules. No clang-tidy configuration and no CI (#38 open).
- 28 test executables with roughly 600 tests (test notes 2026-10). Twenty-five production bugs logged in those notes, several unfixed (Flex grow asymmetry, `TypedMetaClass::inherits` transitivity, `Arci` race on a shared slot, `SpinLock` ownership).
- A GPU render test harness design was approved in October 2026 (one device per test, validation layer as leak check) but not built.
- `Performance.Test` holds a transform benchmark behind `DISABLED_` prefixes; no regression band.
- Build speed is traced (#75): parsing is 94% of a clean editor build; `vkinc.hpp`, `Path.hpp` and `Asset.hpp` are the top headers.

## Research summary

- Safety standards: MISRA C++:2023 merges MISRA 2008 and AUTOSAR C++14 and targets C++17; JSF AV is C++03 era; CERT C++ is security focused; the C++ Core Guidelines are the modern, tool-supported set. Blanket bans on exceptions, dynamic memory or recursion conflict with an engine; the applicable parts are ownership and lifetime, cast discipline, bounded arithmetic at trust boundaries, checked access in parsers.
- Static analysis: clang-tidy profiles (`bugprone-*`, `cert-*`, `cppcoreguidelines-*`, `performance-*`), clang Static Analyzer, PVS-Studio, Coverity, CodeQL. Baselines are required or the noise defeats the gate.
- Sanitizers: ASan and UBSan work with clang-cl on Windows with caveats; TSan needs a Linux job.
- Fuzzing: libFuzzer for in-process coverage-guided fuzzing of parsers and loaders (its docs, verified, say it is in maintenance mode; its authors moved to Centipede, which is a candidate to evaluate); structure-aware mutators for grammars (ASL).
- Golden tests: perceptual metrics (SSIM, IEEE TIP 2004; FLIP, Andersson et al., PACMCGIT 3(2) 2020, DOI 10.1145/3406183) rather than exact pixel match; lavapipe (Vulkan 1.3 conformant per search summaries) or SwiftShader (README verified) give headless Vulkan with per-implementation baselines.
- Performance gates: percentile bands against a same-machine baseline, never fixed thresholds.
- Traceability: a cheap subset of DO-178C is issue to test to commit plus coverage per bundle.

## Guidance

### S63 Coding standard and quality bar

- Write `STANDARD.md` beside `STYLE.md`: ownership (`ptr<T>` non-owning, `Rc`/`Arci` owning, `ref<const T>` for structs), error model (every fallible call returns `Result<T, Diagnostic>` or a documented panic), threading model (which functions may be called from a fiber, which from an affine thread), forbidden constructs (raw `new`, unchecked casts, `std::sort` in deterministic bundles).
- Encode as much as possible in `.clang-tidy`; start with `bugprone-*`, `cert-*`, `cppcoreguidelines-owning-memory`, `performance-*`; add project checks later for `ptr<T>` discipline.
- Contract comments: one block per public type with Purpose, Ownership, Thread context, Failure. Review checklist in the PR template.
- Treat MISRA C++:2023 as a reading list for the hardened bundles: `Engine.Serialization`, `Engine.Resource.Archive`, `Engine.Accel.Lang` front end, `Engine.Network`.

### S62 CI gates

- Build matrix: clang-cl Debug and RelWithDebInfo; a Linux clang job as soon as a headless target links (S58), for TSan.
- Jobs: configure, build editor and all tests, run tests, clang-tidy on changed files, ASan+UBSan test run nightly, libFuzzer targets for a fixed time per loader nightly, performance scenarios with percentile bands.
- Caches: sccache for objects, a content-addressed test asset cache. Build time is itself a tracked metric (S10).

### S26 GPU render test harness

- Build the approved design: each test owns a device, records a pipeline from ASL, renders to a small framebuffer, reads back, compares with FLIP against a baseline per implementation (lavapipe in CI, real GPUs locally).
- First tests: the existing shader assets (`brdf`, `gbuffer`, `predepth`, `sky`, `ui`) at 64x64. The harness becomes the acceptance tool for every rendering system in track B.

### S61 Test suite expansion

- Scope tags: `unit`, `module`, `scene`, `gpu`, `workflow`. CI runs `unit` and `module` per commit, the rest nightly.
- Scene fixtures: a headless world with a fixed asset set and a fixed step, state hash per tick (needs S59's hash and S58's null device).
- Workflow fixtures: the editor driven through the action log and input injection (S45, S39, S54).
- Fix the logged bugs as atomic commits with tests; they are the cheapest quality points on the board.

### S64 Documentation system

- Run the `clang-doc` spike ([code documentation](../../architecture/code-documentation.md)) and publish a reference section on this site.
- Every system that ships gets a system page from the [template](../../systems/template.md) with the verified commit.

### S10 Build speed

- Follow #75: header diet for `vkinc.hpp`, `Path.hpp` and `Asset.hpp` first (the trace shows parsing dominates), then precompiled headers per bundle group, then measure static library clusters. Do not spend time on link tuning (editor links in under four seconds).

## Done when

- A PR that introduces a `cppcoreguidelines-owning-memory` violation fails CI.
- The GPU harness renders the five baseline shaders in CI on lavapipe and matches goldens.
- A nightly job runs ASan+UBSan over all tests and libFuzzer over every loader for a fixed budget.
- A performance scenario regresses by more than its band and the PR is blocked with the numbers in the log.
- The reference section on this site is generated from the engine.

## Open decisions

- Whether to adopt a paid analyzer (PVS-Studio, Coverity) or stay with clang-tidy plus CodeQL.
- The Linux build target date (it gates TSan and the server role).
- Performance band width and the CI machine class.
