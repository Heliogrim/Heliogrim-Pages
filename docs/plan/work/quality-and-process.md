# Work: Quality and Process

**Systems** S10, S26, S61, S62, S63, S64 · **Issues** [#75](https://github.com/Heliogrim/Heliogrim-Engine/issues/75), [#106](https://github.com/Heliogrim/Heliogrim-Engine/issues/106), [#141](https://github.com/Heliogrim/Heliogrim-Engine/issues/141), [#142](https://github.com/Heliogrim/Heliogrim-Engine/issues/142), [#143](https://github.com/Heliogrim/Heliogrim-Engine/issues/143), [#144](https://github.com/Heliogrim/Heliogrim-Engine/issues/144), [#38](https://github.com/Heliogrim/Heliogrim-Engine/issues/38) · **Track** F · **Milestone** M1 onward
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Quality and process](../topics/quality-and-process.md).

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Code documentation exploration](../../architecture/code-documentation.md) | `clang-doc` spike proposed; no annotations in the engine | Spike not run (W64.1) |
| [Systems template](../../systems/template.md) | Shape of a system page with a verified commit | Each shipped system adds one (W64.3) |
| GPU harness design (approved October 2026, session notes; not on this site) | One device per test, validation layer as leak check | Needs a page before implementation (W26.1 writes it from the notes) |
| Test notes 2026-10 (engine checkout, untracked) | 25 logged production bugs, several unfixed | W61.1 converts them to issues |
| C++ modules analysis (session note 2026-11-07, not on this site) | Per-bundle modules estimated at 4 to 8 person-months; a 49-bundle header SCC blocks per-bundle modules; PCH untried | W10.1 starts with header diet and PCH, not modules; W10.2 records the analysis on this site |
| Compile-time trace 2026-11-07 (#75) | Parsing 94%; `vkinc.hpp`, `Path.hpp`, `<chrono>` top | Baseline for W10.1 |

## Architecture

- Not a runtime system. Artefacts: `STANDARD.md`, `.clang-tidy`, PR template, CI workflows, `Engine.GFX.Test.Harness` (new test-support bundle), test scope tags, docs reference generation.
- **Provides**: gates every other work chunk relies on; the GPU harness is the acceptance tool for track B.
- **Consumes**: S58 null device and Linux target for TSan (later); S59 state hash for scene fixtures; S45 and S39 for workflow fixtures.

## Code design

| Artefact | Contract |
|---|---|
| `STANDARD.md` | Ownership (`ptr<T>`, `Rc`, `Arci`, `ref<const T>`), error model (`Result<T, Diagnostic>` at boundaries), threading model (fiber-callable, affine-only, any), forbidden constructs, determinism rules for simulation bundles, contract-comment block (Purpose, Ownership, Thread context, Failure). |
| `.clang-tidy` | `bugprone-*`, `cert-*`, `cppcoreguidelines-owning-memory`, `performance-*`; baseline file so existing violations do not block; a project check for `ptr<T>` discipline later. |
| `GpuTestFixture` | gtest fixture: creates a device (lavapipe in CI, real GPU locally), compiles an ASL effect through `Accel.Compile`, renders to a 64x64 target, reads back, compares with FLIP against `goldens/<implementation>/<test>.png`; validation layer messages fail the test. |
| Test scope tags | gtest name prefixes or labels `unit`, `module`, `scene`, `gpu`, `workflow`; CTest labels map to CI jobs. |
| `SceneFixture` | Headless world, fixed asset set, fixed step, state hash per tick (needs S59 hash function and S58 null device). |
| CI workflows | `build-test.yml` (clang-cl Debug + RelWithDebInfo, unit + module), `nightly.yml` (ASan+UBSan, libFuzzer per loader, gpu goldens on lavapipe, performance bands), `tidy.yml` (changed files against baseline), `docs.yml` (reference generation to Pages). |
| Performance bands | Percentile comparison against a same-machine baseline stored per runner class; band width from Q62.2. |

## Work chunks

### W63.1 Write `STANDARD.md` and `.clang-tidy` baseline · design+plan · ready

- **Goal**: the written standard, the clang-tidy profile with a baseline, the PR template checklist.
- **Inputs**: `STYLE.md`, test notes, MISRA C++:2023 and Core Guidelines as reading lists, the ownership rules recorded in memory (explicit const on handled types, `Opt` semantics).
- **Output**: draft `STANDARD.md` and `.clang-tidy` in the engine checkout on a branch (text only, no code changes); a short decision page `architecture/coding-standard-design.md` listing the rules and their rationale.
- **Questions**: Q63.1, Q63.2.

### W63.2 Contract comments on L1 and L2 public types · execute · after W63.1

- **Done when**: every public type in `Engine.Common`, `Engine.Scheduler`, `Engine.Serialization`, `Engine.Storage.*` has the contract block; clang-tidy passes on those bundles without baseline entries.

### W62.1 CI design · design+plan · ready (#38 is the issue)

- **Goal**: job matrix, caching (sccache, asset cache), runner class, nightly layout, how bands are stored, the workstation evidence report format and its validation job (Q62.1).
- **Output**: `architecture/ci-design.md`; plan with the workflow files.
- **Questions**: Q62.1, Q62.2, Q62.3.

### W62.2 Implement build and test workflows · execute · after W62.1

- **Done when**: a PR builds editor and all tests on clang-cl and runs `unit` and `module`; tidy on changed files blocks on a violation.

### W62.3 Nightly sanitizers, fuzzing, performance bands · execute · after W62.2, W26.3 (for gpu job)

- **Done when**: nightly runs ASan+UBSan over all tests, libFuzzer over every loader for a fixed budget, and a performance scenario regresses and blocks with numbers in the log.

### W26.1 GPU harness design page · design · ready

- **Goal**: write the approved October design down (device per test, validation as leak check, FLIP comparison, per-implementation goldens, lavapipe in CI).
- **Output**: `architecture/gpu-test-harness-design.md`; plan.
- **Questions**: Q26.1.

### W26.2 Implement the harness and the five baseline shader tests · execute · after W26.1

- **Done when**: `brdf`, `gbuffer`, `predepth`, `sky`, `ui` render at 64x64 and match goldens locally.

### W26.3 Harness in CI on lavapipe · execute · after W26.2, W62.2

- **Done when**: the five tests pass in CI with lavapipe goldens.

### W61.1 Logged bugs to issues and fixes · execute · ready

- **Goal**: convert the 25 logged bugs in the test notes into issues; fix the cheap ones (Flex grow asymmetry, `TypedMetaClass::inherits` transitivity, `SpinLock` ownership, `Arci` shared-slot race where #77 does not cover it) as atomic commits with tests.
- **Done when**: every logged bug has an issue; fixed ones are closed by commits with tests.

### W61.2 Scope tags and scene fixtures · design+plan · after W59 hash, W58 null device (design can start now)

- **Output**: section in `ci-design.md`; plan for tagging the 28 test executables and the first scene fixture.

### W61.3 Loader fuzzing targets · execute · after W62.2

- **Done when**: libFuzzer targets exist for the package reader, archive reader, structure reader, ASL front end, image and audio importers.

### W64.1 Run the `clang-doc` spike · explore · ready

- **Goal**: generate a reference for two bundles with `clang-doc` on clang-cl 22; judge output quality, build time and site integration; compare with Doxygen plus a theme only if `clang-doc` fails.
- **Output**: results in `architecture/code-documentation.md`; recommendation.
- **Questions**: Q64.1.

### W64.2 Reference generation into Pages · execute · after W64.1, W62.2

- **Done when**: the reference section on the site is generated from the engine in CI.

### W64.3 System page per shipped system · execute · continuous

- **Rule**: every execute chunk that ships a system ends with a system page from the template, verified against the commit.

### W10.1 Header diet and PCH · execute · ready (#75 is the spec)

- **Goal**: `vkinc.hpp`, `Path.hpp`, `Asset.hpp` diet; precompiled headers per bundle group; record clean editor build time against the 2026-11-07 trace.
- **Done when**: clean editor build time drops and the number is in the system page; no behaviour change.

### W10.2 C++ modules decision · explore · after W10.1

- **Goal**: with the header SCC reduced by W10.1, re-estimate per-bundle modules; decide go or close.
- **Questions**: Q10.1.

### W10.3 Rename `Engine.PFX` to `Engine.Physics` and `Engine.GFX` to `Engine.Graphics` · execute · ready

- **Goal**: owner decision (Q24.2, 2026-11-09): spelled-out bundle names. Rename the directories, CMake targets, include paths and namespaces in one mechanical pass; new bundles follow the convention (`Engine.Particles`, `Engine.Foliage`, `Engine.Graphics.Render.Foliage`).
- **Done when**: the build and all tests pass with no `Engine.GFX` or `Engine.PFX` left in `src/`; `ARCHITECTURE.md` and the module map on this site use the new names. Until then the work pages keep the current names.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q63.1 | MISRA C++:2023 is a reading list, not a compliance claim. |
| Q63.2 | Exceptions banned in `Engine.*`; allowed in `Editor.*` tooling and in tests. |
| Q62.2 | Performance band p95 within 10%; first scenarios: transform update, IO 1,000-request, scheduler fan-out. |
| Q62.3 | clang-tidy plus CodeQL; no paid analyzer. |
| Q26.1 | FLIP threshold per test, with a global default. |
| Q64.1 | Doxygen is acceptable as a fallback to `clang-doc`, but only if it needs no additional annotations, macros or comment conventions in the source. The code stays as it is; the tool adapts. |
| Q10.1 | C++ modules migration is not a goal; W10.2 closes it unless W10.1 halves the estimate. |
| Q62.1 | GitHub-hosted runners with lavapipe for unit and small automated tests, without stressing the runners. Evidence that needs a real GPU (performance, driver behaviour, image quality at scale) is produced on a developer workstation with the local fixture and benchmark tools and attached to the issue or ticket; W62.1 defines that evidence format and the CI job that validates an attached report. No self-hosted GPU runner for now. |
| Rule (Q18.3) | Magic numbers and constants are `inline constexpr static` with a one-line explanation of where the value comes from. Anything that is a setting rather than a constant gets a config entry instead. Applies to page sizes, chunk sizes, thresholds and budgets across all systems. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q63.1 | Is MISRA C++:2023 a reading list only, or must the hardened bundles claim compliance with a deviation record? | W63.1 | Reading list; no compliance claim |
| Q63.2 | Exceptions: banned in engine code (status quo by convention?) or allowed in tooling bundles? | W63.1 | Banned in `Engine.*`, allowed in `Editor.*` tooling and tests |
| Q62.1 | Runners: GitHub-hosted Windows runners only, or a self-hosted machine with a GPU for the gpu job? | W62.1 | GitHub-hosted plus lavapipe; self-hosted GPU later |
| Q62.2 | Performance band width (e.g. p95 within 10% of baseline) and which scenarios count first? | W62.1 | p95 within 10%; scenarios: transform benchmark, 1,000-request IO test, scheduler fan-out |
| Q62.3 | Paid analyzer (PVS-Studio, Coverity) or clang-tidy plus CodeQL only? | W62.1 | clang-tidy plus CodeQL |
| Q26.1 | FLIP thresholds per test, or one global threshold? | W26.1 | Per test with a global default |
| Q64.1 | Is Doxygen acceptable as a fallback if `clang-doc` output is poor, given the no-annotation rule? | W64.1 | Yes, without annotations, as a fallback only |
| Q10.1 | Is a C++ modules migration still a goal after the 4 to 8 person-month estimate? | W10.2 | No; close unless W10.1 changes the estimate by a factor of two |
