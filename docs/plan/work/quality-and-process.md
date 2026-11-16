# Work: Quality and Process

**Systems** S10, S26, S61, S62, S63, S64 · **Issues** [#75](https://github.com/Heliogrim/Heliogrim-Engine/issues/75), [#106](https://github.com/Heliogrim/Heliogrim-Engine/issues/106), [#141](https://github.com/Heliogrim/Heliogrim-Engine/issues/141), [#142](https://github.com/Heliogrim/Heliogrim-Engine/issues/142), [#143](https://github.com/Heliogrim/Heliogrim-Engine/issues/143), [#144](https://github.com/Heliogrim/Heliogrim-Engine/issues/144), [#38](https://github.com/Heliogrim/Heliogrim-Engine/issues/38) · **Track** F · **Milestone** M1 onward
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Quality and process](../topics/quality-and-process.md).

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Code documentation exploration](../../architecture/code-documentation.md) | `clang-doc` spike proposed; no annotations in the engine | Spike not run (W64.1) |
| [Systems template](../../systems/template.md) | Shape of a system page with a verified commit | Each shipped system adds one (W64.3) |
| GPU harness design (approved October 2026, session notes; not on this site) | One device per test, validation layer as leak check | Needs a page before implementation (W26.1 writes it from the notes) |
| Test notes 2026-10 (engine checkout, untracked) | 25 logged production bugs; 12 fixed, 2 not bugs (ledger in W61.1, 2026-11-13) | 11 still open or partly open, none filed as issues yet (W61.1) |
| C++ modules analysis (session note 2026-11-07, not on this site) | Per-bundle modules estimated at 4 to 8 person-months; a 49-bundle header SCC blocks per-bundle modules; PCH untried | W10.1 starts with header diet and PCH, not modules; W10.2 records the analysis on this site |
| Compile-time trace 2026-11-07 (#75) | Parsing 94%; `vkinc.hpp`, `Path.hpp`, `<chrono>` top | Baseline for W10.1 |

## Architecture

- Not a runtime system. Artefacts: `STANDARD.md`, `.clang-tidy`, PR template, CI workflows, `Engine.Graphics.Test.Harness` (new test-support bundle), test scope tags, docs reference generation.
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

### W26.1 GPU harness design page · design · done (design and W26.2 plan accepted by the owner 2026-11-15)

- **Goal**: write the approved October design down (device per test, validation as leak check, FLIP comparison, per-implementation goldens, lavapipe in CI).
- **Result (2026-11-14)**: [GPU test harness design](../../architecture/gpu-test-harness-design.md), from an owner conversation. It replaces the October spec. The function tier comes first; one contract for every implementation (no baselines per implementation); epsilon or comparison kernels; a report independent of gtest; shared shader functions may be included; target 1 s per test and 30 s per bundle. Q26.1: per test, with a global default. W26.4 and the shared probe mechanism split out.
- **Result (2026-11-15)**: W26.2 plan, seven tasks (contracts, report with previous-run store, headless device and fixture, float target and readback, function tier entry point, `shared/pbr.asl` tests with the included-bindings check, timing). Untracked in the engine checkout: `docs/superpowers/plans/2026-11-15-gpu-function-harness.md`. Code checks for the design's open points: slicing drops unused `@input` bindings only when the spec names its target symbols, so the harness names `color` (`TmpBrdfLutPass` names none and keeps all); `shared/pbr.asl` declares no bindings; headless keeps the instance and device extension lists unchanged and only adds a selection branch that checks features and the float format, honours `HELIOGRIM_TEST_GPU`, and throws. The October triangle, depth and stencil checks are left out of W26.2.
- **Output**: `architecture/gpu-test-harness-design.md`; plan.
- **Questions**: Q26.1.

### W26.2 Implement the harness and the five baseline shader tests · execute · in review (PR [#193](https://github.com/Heliogrim/Heliogrim-Engine/pull/193) into `feat/wip`, 2026-11-16; part of [#106](https://github.com/Heliogrim/Heliogrim-Engine/issues/106))

- **Done when** (rescoped 2026-11-14, see the design section 7): the function tier runs a first set of shading-function tests (a BRDF term at least) against contracts, and the report shows the result, both diffs and the failing inputs. The October triangle, depth and stencil checks are included if they fit.
- **Result (2026-11-15)**: plan executed off `feat/wip` (`c80f3569`) in ten signed commits (head `af48c2d9`) on `feat/gpu-function-harness` (worktree `Heliogrim-CLion-wt/gpu-function-harness`), after the owner accepted the design and plan. New bundle `Engine.Graphics.Gpu.Test` (excluded from `Heliogrim-AllTests`, ctest label `gpu`): contracts (epsilon, relative, monotonic, slope, custom kernels), a YAML report with the previous passing run, a headless device per test with the validation layer as leak check, an RGBA32F target with readback, and `runFunction`. `shared/pbr.asl` checks pass for `ndfGgx`, `geoSchlickSmith`, `fresnelSchlick` and `disneyDiffuse` against CPU references from the cited papers (max error 3.6e-6 relative for GGX, 6e-8 absolute for the rest), and a changed exponent fails with its texels and inputs listed. Production change: `Application::setup(bool headless_ = false)`, a headless branch in `Device::setup()` that checks features and the float format, honours `HELIOGRIM_TEST_GPU` and throws `no GPU with these capabilities found`, and `Graphics::setupHeadless`/`destroyHeadless`. Timing (Debug, RX 9070 XT): function tests 540-940 ms, bundle 5.8 s for 32 tests (33 after the review fixes). `/review-branch` ran; its fixes are one extra commit on top, not folded into the original commits.
- **Result (2026-11-16)**: a second fix wave (no throwing wait in teardown destructors, device rollback releases queues and allocator first, the extra device holders were its own queues and allocator) and a second `/review-branch`, whose accepted findings were fixed. All fixes are folded into their original commits: nine signed commits, head `c2c7ac87`, not pushed. Gpu.Test 33/33. Filed: [#192](https://github.com/Heliogrim/Heliogrim-Engine/issues/192) included `@input` bindings are not sliced (design 6.1), [#191](https://github.com/Heliogrim/Heliogrim-Engine/issues/191) compiler-stage diagnostics reach only the log.
- **PR (2026-11-16)**: rebased onto `feat/wip` `404c9e7d` (W05.4 lowercased the ASL messages; the include-guard test now matches `unknown include '<name>'`), nine signed commits, head `b219aaaa`, pushed as `feat/gpu-function-harness` and opened as [#193](https://github.com/Heliogrim/Heliogrim-Engine/pull/193). Gpu.Test 33/33, Graphics.Test 9/9. The owner's style and order wave (member and definition order, call-argument layout, guard blank lines, unused includes) is folded into the same nine commits, head `04b5b2d9`.
- **Open for the owner**: (1) the GPU tests need the validation layer and debug utils, which `Application` enables only in Debug, so the bundle fails in Release; (2) `Heliogrim-Editor` does not build on `feat/wip` (`EditorInit.cpp:40`, `initDefaultUi` undeclared); the owner runs the editor and fixes it centrally, until then the production device path is unchecked in the editor; (3) the deferred review items in the untracked `docs/superpowers/reviews/2026-11-1{5,6}-feat-gpu-function-harness.md` (in the worktree); (4) the design's 6.2 builder's calls; (5) review and merge of #193.

### W26.3 Harness in CI on lavapipe · execute · after W26.2, W62.2

- **Done when**: the five tests pass in CI with lavapipe goldens.

### W26.4 Shader performance analysis adapter · design+plan+execute · after W26.2 (added 2026-11-14)

- **Goal**: measure and optimise shader implementations, for example new shading functions written for materials, on the dispatches the harness already describes. Mainly a tool for the editor, not a gtest check. It needs GPU timing queries, readback, and pipeline state and ISA statistics from the driver (owner, 2026-11-14, split out of W26.1 to keep that scope small).
- **Inputs**: the GPU harness design (W26.1): a test describes its dispatch, so timing can later wrap the same dispatch without rewriting the test. The Q11.3 measurement rule: own shader optimisations need numbers first.
- **Open**: which driver interfaces provide the statistics (for example `VK_KHR_pipeline_executable_properties`, vendor tools), where the editor shows results, and how measurements stay stable enough to compare.

### W61.1 Logged bugs to issues and fixes · execute · in progress (12 of 25 fixed, 2 not bugs; no issues filed yet, checked 2026-11-13)

- **Goal**: convert the 25 logged bugs in the test notes into issues; fix the cheap ones as atomic commits with tests.
- **Done when**: every logged bug that is still open has an issue; fixed ones are closed by commits with tests.
- **Ledger** (checked against `master` `f0c0c6b1` on 2026-11-13; numbers are the test-note numbers; "unverified" means read, not compiled):

| # | Bug | State | Evidence |
|---|---|---|---|
| L1 | Murmur3 `x86_32` read blocks out of bounds | fixed | `3b0f8270`, `Murmur3.x86_32CanonicalVectors` enabled |
| L2 | `Engine.Common/{Collection/,}RingBuffer.hpp` do not compile, included nowhere | open | delete both; the live ring buffer is `Engine.Async/Collection/RingBuffer.hpp` |
| L3 | `Integral128.hpp` specialises `std::is_integral` and `std::is_unsigned` (clang error), unused | open | delete or drop the `std` specialisations |
| L4 | `Subject<T&>::peek()` returns a reference to the stored pointer | open | `Editor.UI.Rx/Subject.hpp:49` |
| L5 | `SpinLock::unlock` keeps `_owns` set | fixed | `b163b9af` |
| L6 | `Pool::destroy` dangling instance; `Pool` members that do not compile when instantiated | destroy fixed (`ffe914a6`), compile part unverified | `Storage.hpp` now includes `<algorithm>` |
| L7 | `Rci` copy-assign does not compile | open | `RefCountedIntrusive.hpp:139` assigns an `mpt`, whose copy-assign is deleted |
| L8 | `Modules::removeSubModule` always false; cycle check only direct | removal fixed (`bf729813`); transitive cycle open | `DISABLED_TransitiveOrderCycleIsRejected` |
| L9 | Flex `padding.z`, single-child space-between, X grow uses `max` where Y uses `min` | padding and space-between fixed (`81561084`); grow asymmetry open | `Engine.Reflow/Algorithm/Flex.hpp:224` vs `:238` |
| L10 | `AssetRegistry::getAssetByGuid` crashes on an unknown guid | not a bug | by contract; `findAssetByGuid` is the safe call |
| L11 | `Representation` copy asserts `mainEntry == nullptr`, deep copy TODO | symbol names fixed (`3f2a97e8`); deep copy open | `Engine.Accel.Lang/Representation.cpp:15-27` |
| L12 | `ActionLog::reapply` can never yield | fixed | 2026-10-27 batch |
| L13 | `ActionManager::reapply` inverted null check | fixed | 2026-10-27 batch |
| L14 | `setRelativeLocationAndRotator` drops location for children | fixed | contract documented (universe-space pose) |
| L15 | `Guid` ordering dereferences bytes as a pointer | fixed | `41e5a432` |
| L16 | `Bounding::intersectsAaBb(point)` unsatisfiable | fixed | 2026-10-27 batch |
| L17 | Bounding sphere tests use `r1²+r2²` | fixed | 2026-10-27 batch |
| L18 | `Bounding(center, extent)` leaves `extentLength` 0 | fixed | 2026-10-27 batch |
| L19 | `Rotator` roll, `inversed()`, quaternion round trip | fixed | 2026-10-27 batch |
| L20 | `InlineAutoArray::erase` does not compile, corrupts data | fixed | 2026-10-27 batch |
| L21 | `CompositePipeline::registerStage` appends before duplicate check | not a bug | dedup lives elsewhere |
| L22 | `TypedMetaClass::inherits` misses grand-bases | open | `DISABLED_ThreeLevelTransitiveInherit` |
| L23 | `StructSlot::hasRecordSlot("")` true on an empty struct | open | `DISABLED_EmptyStructRejectsEmptyIdentifier` |
| L24 | `InputVec<T>::prepare()` does not compile; `uikit::Text` crashes without a font | Text fixed (`59f7cfe1`); `InputVec` open | `make_sptr<InputFloat>()` has no default constructor (`InputVec.hpp:70`) |
| L25 | `Arci` concurrent copy and move-assign on one slot | fixed | split-count protocol `5ea82a6d` on `master`; #77 still open, can close |

- **Open bug issues in the tracker** (synced 2026-11-13; none of them came from the test notes), each owned by the work page of its system:

| Issue | Bug | System, page |
|---|---|---|
| [#24](https://github.com/Heliogrim/Heliogrim-Engine/issues/24) | Shader read fails on a local URL | S03, [storage](storage-streaming.md); fixed in PR #169 (`929c763b`), closes when it lands |
| [#44](https://github.com/Heliogrim/Heliogrim-Engine/issues/44) | Missing style or re-render with a hover layer over the viewport | S42, [vector UI](vector-ui-uikit.md) |
| [#148](https://github.com/Heliogrim/Heliogrim-Engine/issues/148) | GLSL emission: user names collide with keywords and generated identifiers | S11, [accel](accel-lang.md) W11.0 |
| [#154](https://github.com/Heliogrim/Heliogrim-Engine/issues/154) | `Resource<T>` never releases its owned value (body empty) | S03, [storage](storage-streaming.md) |
| [#158](https://github.com/Heliogrim/Heliogrim-Engine/issues/158), [#160](https://github.com/Heliogrim/Heliogrim-Engine/issues/160), [#161](https://github.com/Heliogrim/Heliogrim-Engine/issues/161), [#162](https://github.com/Heliogrim/Heliogrim-Engine/issues/162) | Editor stop ordering: universes torn down while the pipeline ticks; Input destroyed before the platform thread stops; stop waits silently on a file dialog; stop during drag start hangs | S02, [concurrency](concurrency-fibers.md) (stop sequence proposal #150) |
| [#163](https://github.com/Heliogrim/Heliogrim-Engine/issues/163) | Editor exit hits a debug breakpoint after 36 shader modules are destroyed late | S12, [accel](accel-lang.md) |
| [#166](https://github.com/Heliogrim/Heliogrim-Engine/issues/166) | Nested storage call on the same primary can deadlock | S03, [storage](storage-streaming.md) |
| [#170](https://github.com/Heliogrim/Heliogrim-Engine/issues/170) | `CompileMap`/`CompileHashMap::find` reports missing keys as found above 56 entries | S09, [serialisation and reflection](serialization-and-reflection.md) |
| [#171](https://github.com/Heliogrim/Heliogrim-Engine/issues/171) | `Path::name()` truncates wide characters, can produce separators | S03, [storage](storage-streaming.md) |
| [#174](https://github.com/Heliogrim/Heliogrim-Engine/issues/174) | `Signal` destroy rule lets a waiter free it while another is inside `wait()` | S02, [concurrency](concurrency-fibers.md) |

- **Next**: file issues for the open L rows (L2 and L3 can be one "delete dead headers" issue), then fix the cheap ones: L2, L3, L9 grow, L22, L23, L8 cycle.

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

### W64.4 Glossary with hover terms on the Pages site · execute · page seeded 2026-11-09, hover terms open

- **Status**: `docs/glossary.md` exists with about 80 entries recovered from the question batches and is in the nav; the hover definitions, the dotted underline and the term links are still to do.

- **Goal**: a glossary page for engine and plan terms (the owner has asked for several in the question batches: fiber, affine thread, cell, froxel, cascade, tier, `d`, metered run, and the gap-analysis list); terms in page text link to it and show a short definition on hover, marked with a subtle coloured dotted underline rather than a loud highlight. Material for MkDocs ships this through the `abbr` extension plus an auto-appended abbreviations snippet, so the chunk checks that path first before any custom JavaScript.
- **Output**: `docs/glossary.md`, the abbreviation snippet, the underline style in `stylesheets/heliogrim.css`, nav entry.
- **Done when**: every term the owner asked about in batches 1 to 6 resolves on hover from at least one plan page.

- **Rule**: every execute chunk that ships a system ends with a system page from the template, verified against the commit.

### W10.1 Header diet and PCH · execute · code done 2026-11-10 (PR [#168](https://github.com/Heliogrim/Heliogrim-Engine/pull/168), merged into `feat/wip` 2026-11-11), build-time number open

- **Goal**: `vkinc.hpp`, `Path.hpp`, `Asset.hpp` diet; precompiled headers per bundle group; record clean editor build time against the 2026-11-07 trace.
- **Done when**: clean editor build time drops and the number is in the system page; no behaviour change.
- **Scope change**: PCH is out, by owner decision 2026-11-08 (cross-bundle include web). `Path.hpp` keeps `<filesystem>` and `Timing.hpp` keeps `<chrono>`. The vkFwd firewall rounds 1 and 2 were already in history.
- **Result**: 12 signed commits on branch `refactor/header-diet` (PR #168), stacked on W10.3 (#167):
    - `Engine.Common/Algo` gains small constexpr function objects (`FindIf`, `CountOf`, `LowerBound`, `CopyTo`, `TransformTo`, `Merge`) in place of `<algorithm>`/`<ranges>` in widely included headers. Each is a plain loop over `begin()`/`end()` with no standard header beyond `<cstddef>`.
    - The compile-time reflect containers (`Sort.hpp`, `Map.hpp`, `HashMap.hpp`) and `Path.hpp` use them, `Math/Convertion.hpp` uses the existing `math::clamp`, and none of them include `<algorithm>`/`<ranges>`. This takes `<algorithm>` off the `TypedMetaClass` chain.
    - `Asserts.hpp` no longer includes `<stdexcept>`.
    - The ACS and level guid generators are defined in their header's own TU (`ACS/Traits.cpp`, `Level/LevelGuid.cpp`), so `<chrono>` and `<atomic>` leave `ACS/Traits.hpp` and `LevelGuid.hpp`.
    - `panic_stacktrace` is non-template and defined out of line, so `<stacktrace>` leaves `Panic.hpp`, which reaches about 635 TUs.
    - `FontAsset.hpp` no longer includes the resource loader.
    - `get_memory_type` moves from `vkinc.hpp` to its own `Memory/MemoryType.{hpp,cpp}`.
    - The Jolt profiler is off in Debug.
    - Logger formats through one `vformat` call.
    - `Widget.hpp` forward-declares `ReflowCommandBuffer`.

    Each commit fixes the files that had relied on the include it removed. Editor and all tests build, and 29 of 29 suites pass.
- **Open**: the clean build time is not measured yet. sccache makes a rebuild time meaningless. A replay of each own TU without the cache (12 in parallel) was stopped because the machine ran out of memory, so the number for the system page still has to be measured.

### W10.2 C++ modules decision · explore · after W10.1

- **Goal**: with the header SCC reduced by W10.1, re-estimate per-bundle modules; decide go or close.
- **Questions**: Q10.1.

### W10.3 Rename `Engine.PFX` to `Engine.Physics` and `Engine.GFX` to `Engine.Graphics` · execute · done 2026-11-10 (PR [#167](https://github.com/Heliogrim/Heliogrim-Engine/pull/167), merged into `feat/wip` 2026-11-11)

- **Goal**: owner decision (Q24.2, 2026-11-09): spelled-out bundle names. Rename the directories, CMake targets, include paths and namespaces in one mechanical pass; new bundles follow the convention (`Engine.Particles`, `Engine.Foliage`, `Engine.Graphics.Render.Foliage`).
- **Done when**: the build and all tests pass with no `Engine.GFX` or `Engine.PFX` left in `src/`; `ARCHITECTURE.md` and the module map on this site use the new names. Until then the work pages keep the current names.
- **Result**: six signed commits on branch `refactor/spelled-out-bundle-names` (PR #167), stacked on `refactor/lock-types` (#165): `Engine.PFX` → `Engine.Physics`, `Engine.GFX*` → `Engine.Graphics*` (17 bundles), `Editor.GFX*` → `Editor.Graphics*` (4 bundles), namespaces `hg::engine::gfx` / `hg::editor::gfx` → `::graphics`, and `Engine.SFX` → `Engine.Audio` with `hg::engine::sfx` → `::audio` and `SfxMaterial` → `AudioMaterial`. Another commit spells out the remaining short forms: `GfxMaterial*` → `GraphicsMaterial*`, `PfxMaterial` → `PhysicsMaterial` (types, files, asset type ids), the `"::Gfx::RenderScenePipeline"` stage id, and parameter names. The owner chose this over keeping the stored ids (2026-11-10), while renaming still needs no migration path; any material already stored under an old type id does not load until it is re-saved. Editor and all tests build, and 29 of 29 suites pass with the same counts as the base. The [module map](../../architecture/modules.md) is regenerated at `b6887c17`; `ARCHITECTURE.md` is updated in the worktree, because it is still untracked in the engine. The render graph `ctid` ids change, but they are runtime-only. The other work pages and `ARCHITECTURE.md` switched to the new names on 2026-11-11, after the merge.

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
