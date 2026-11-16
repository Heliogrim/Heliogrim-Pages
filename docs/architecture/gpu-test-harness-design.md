# GPU test harness design

**Status**: <span class="hg-status summary">design</span>. W26.1 ([quality and process](../plan/work/quality-and-process.md)), written 2026-11-14 from an owner conversation. It replaces the October 2026 harness spec and plan, which are untracked in the engine checkout (`docs/superpowers/specs/2026-10-27-gpu-render-test-harness-design.md`, `docs/superpowers/plans/2026-10-28-gpu-render-test-harness.md`), and the S26 description in the battle plan. This page is revised in place as the harness grows, across several work packages.

## 1. Intent

Getting the BRDF, lighting and shading functions right has been the costliest rendering work. Each small tweak to a function needed an end-to-end run, with intermediate values pushed into the screen's color buffer just to see them. The harness replaces that loop. A test feeds a shader function controlled inputs on a small raster, runs it on the GPU, reads the values back, and checks them against values worked out in advance. When values differ, the report shows where, by how much, and what the edit changed compared with the last run.

The same harness later carries compute shader tests (offloaded or parallelised work checked against a CPU implementation), whole-pipeline checks, and work-graph setups. It is also the acceptance check for the direct SPIR-V backend (W11.3).

## 2. Goals

- **Function tier (first build)**: a shading function runs over a raster of controlled inputs, one input combination per texel. The output is read back as floats and checked against a contract (section 4).
- **Compute tier**: a compute shader runs on controlled inputs. Its output is checked against a CPU implementation of the same algorithm, or against values computed by hand.
- **Pipeline tier**: whole-pipeline checks. Day-one candidates from October: a flat triangle checked for color, depth and stencil, then the existing shaders (`brdf`, `gbuffer`, `predepth`, `sky`, `ui`).
- **Work-graph tier**: allowed for in the design, not built (Q12.1 reserves the pipeline kind; the Vulkan extension is not stable).
- **Diff report** for every run (section 5).
- **Backend independence**: tests are ASL, and expectations are values. The same tests run on the current GLSL path and, after W11.3, on SPIR-V. There is no parity suite between the two backends (owner, 2026-11-14: the GLSL path is removed once SPIR-V lands; no DXIL now).
- **Headless**: no window, no surface, no swapchain.
- **Own test bundle**, excluded from `Heliogrim-AllTests`, runnable locally on a dedicated GPU, and later in CI.

## 3. Rules and anti-goals (owner)

The October rules still hold:

- **Proof the GPU ran**: the target holds a known clear value before the run, and the run must change at least one value. "Never ran" and "ran but wrote nothing" both fail.
- **No leaks**: every Vulkan object and allocator section is released. The validation layer is the leak check; a run without the validation layer fails loudly.
- **No skip**: a machine without a suitable GPU or driver fails with a clear message. It never skips silently.
- **No repo assets, except shared shader functions**: a test's own wrapper shader is `constexpr` text in the test. It may `#include` the engine's shared function libraries (`shared/*.asl`, for example `shared/pbr.asl`), so the test checks the real function being tuned, not a copy (owner, 2026-11-14). Whole effects are never included, and neither are binary or generated assets.
    - The include goes through the parser's `ModuleResolver`. Today the resolver reads `assets/shader/`. Where shaders end up is part of the open asset location and distribution question: if they move into distributed packages (imp), only the resolver changes, not the tests.
    - Intended side effect: a project's own tests that include engine shader functions fail when an engine update changes those functions. That is the point.
    - The rule may loosen further for very large shaders or editor-built shaders.

The harness has failed, even if it technically works, when any of these happens (owner, 2026-11-14):

- **False failures**: a test fails although the shader is right.
- **Debugging the harness**: time goes into the harness instead of the shader. It has to be robust.
- **Slow runs**: a test run takes too long for the iteration loop. Starting target (owner, 2026-11-14): a single function test under 1 s and the whole bundle under 30 s, in Debug on the owner's machine. Revisited after the first tests. If a run misses the target, the options in order are one device per suite (6.2), a compile cache, and validation outside Debug.
- **Hard to write or read**: writing a test needs much boilerplate, or a test is hard to understand.

## 4. Contracts

A test states its expected values together with how close is close enough. That pair is the **contract**.

- **One contract for every implementation**: a software GPU such as lavapipe must meet the same contract as real hardware (owner, 2026-11-14). There are no baselines per implementation. If lavapipe misses a contract, either the contract is tighter than the Vulkan precision rules allow or the shader relies on precision it should not. Both need a person to look; the harness never adjusts a contract by itself.
- **Expected values** are worked out in advance for the raster's flat inputs, either by hand or by a CPU implementation written next to the test. A CPU reference is an honest second implementation, never generated from the shader. (Builder's call.)
- **Epsilon** is the default: every texel must lie within an absolute or relative error of its expected value. Q26.1 (thresholds per test or global) resolves as: per test, with a global default.
- **Comparison kernels** cover outputs where a flat epsilon asks the wrong question, for example a gradient whose absolute error drifts across the raster while its shape is what matters. A kernel looks at a window of output texels and the matching window of expected values, and returns pass or fail plus a measured value. (Builder's calls:)
    - kernels run on the CPU, on the read-back floats;
    - built in: absolute epsilon, relative epsilon, monotonic order along an axis, slope within an epsilon;
    - a test can pass its own C++ function.
- **Test helpers in shaders** may map an internal value into a known output range, for example depth into a color channel, so that an internal value can be checked without a full pipeline.

## 5. Report

The report is plain data, independent of gtest. The test writes it as `<test>.report.yaml` into `gpu-results/` next to the test executable, and a failing gtest assertion prints its text. Later the editor shows the same data when shaders and shader graphs are built there (owner, 2026-11-14). The editor view is not part of this design (section 8).

Owner's reading order:

1. **Result**: pass or fail per contract check, and the number of failing texels or windows.
2. **Diff against the expectation**: where and by how much the output misses the contract, as a map over the input raster plus summary numbers (maximum error and where it occurs, mean error).
3. **Diff against the previous run**: the change compared with the values of the last stored run, shown even when both runs pass. (Builder's call: the test keeps the values of its last passing run next to its results; they are not committed.)
4. **Inputs behind a failing or changed texel**: the harness generated the input raster, so it lists those inputs at no extra cost. Explaining what happened *inside* the function, through intermediate values, is the expensive part and belongs to the probe work (section 8).

The report must let a person, or an agent reading the file, reason about why a change came out the way it did without running the test again.

## 6. How it gets made

### 6.1 Decided

- **Runner**: gtest, in a new bundle with its own target, excluded from `Heliogrim-AllTests`.
- **Shader input**: ASL source text in the test, compiled through `Engine.Accel.Lang` and `Engine.Accel.Compile`. It may include `shared/*.asl` (section 3). There are no GLSL tests.
- **Included bindings**: an included library may declare `@input` bindings (for example `lighting.brdf.asl`). The plan checks whether slicing drops the bindings a test does not use. If it does not, the harness supplies placeholder descriptors.
    - Result (W26.2, 2026-11-15): slicing does not drop them today. Slicing by target symbol is not reachable: `SimpleEffectSpecification` takes owning `smr<const lang::Symbol>`, the effect's exports are non-owning and carry an empty `symbolName`, `StageIr` slices by name, and `EffectCompiler.cpp:52` asserts object identity; no production pass names targets either. The harness therefore compiles with an empty target list. A test that includes `lighting.brdf.asl` compiles (with an `ASL0045` warning at line 152) and then aborts in `VkRCmdTranslator` before submit, most likely the descriptor commit assert, so the unused bindings still need descriptors. Open for the owner: fix target naming in the engine, or build placeholder descriptors. Tests that include only `shared/math.asl` and `shared/pbr.asl` are unaffected. Tracked as [#192](https://github.com/Heliogrim/Heliogrim-Engine/issues/192); compiler-stage diagnostics in the report as [#191](https://github.com/Heliogrim/Heliogrim-Engine/issues/191). Harness PR: [#193](https://github.com/Heliogrim/Heliogrim-Engine/pull/193).
- **Leak check**: the validation layer, with no allocator counters in production code.
- **Production path unchanged**: every new headless parameter defaults to today's behaviour.

### 6.2 Builder's calls (not yet confirmed by the owner)

- **The function tier runs as a fragment shader on one triangle that covers the whole target**, an `R32G32B32A32_SFLOAT` image the size of the input raster (32×32 to 64×64). There is no window or screen. The triangle is larger than the target and clipped to it, so the fragment shader runs exactly once per texel, and the texel coordinate selects that texel's inputs. Compute pipelines cannot run yet: `VkPipelineCompiler::linkStages` and `linkVk` for `VkComputePipeline` return without creating a pipeline (checked 2026-11-14, `Engine.Accel.Compile/Pass/VkPipelineCompiler.cpp`). The fragment path is what the existing graphics pipeline supports, and it is where shading functions run in practice. The compute tier waits for compute pipeline creation, which is W12.2's work; the harness takes it from there and does not build it.
- **Input raster**: inputs arrive per texel from the texel coordinate (for example roughness along x, N·H along y) or from a small input buffer. Rasters are small, 32×32 to 64×64.
- **Device per test**: the validation layer reports leaked device objects only at `vkDestroyDevice`, so every test creates and destroys its own instance and device. Cost is measured early against the slow-runs anti-goal. If one device per test is too slow, the fallback is one device per test suite, with leak reports attributed to the suite. Measured 2026-11-15 (W26.2, Debug, AMD Radeon RX 9070 XT, three runs): a device-only test takes about 100-130 ms, a function test 540-940 ms, and the 32-test bundle 5.8 s. Both targets hold, so the fallbacks are not needed.
- **No-GPU message**: `no GPU with these capabilities found`. The env var `HELIOGRIM_TEST_GPU` (case-insensitive substring of the device name) selects a GPU; a value that matches nothing fails loudly.
- **Ergonomics**: a function test is the ASL text, the input raster, the expectation (values or a CPU function) and the contract, with no Vulkan objects in sight. The October plan named about 100 lines of effect, pass, profile and spec setup as the boilerplate the helper must hide.

### 6.3 Findings from the code that still stand

These are the October plan's corrections, re-checked where marked. The bundle names changed since October: `Engine.GFX` is now `Engine.Graphics`.

- The validation layer is enabled only under `_DEBUG` (`Engine.Graphics/Application/Application.cpp`; re-checked 2026-11-14). The fixture fails when `VK_LAYER_KHRONOS_validation` is not active.
- The accel compile and pass code finds the device through `Engine::getEngine()->getGraphics()->getCurrentDevice()` (`VkModuleCompiler`, `VkCompiledModule`, `VkPipelineCompiler`, `VkAccelerationPassFactory`, `VkGraphicsPass`, `VkGraphicsPipeline`; re-checked 2026-11-14). Headless therefore needs a test engine that owns a `Graphics`, plus a headless setup on `Graphics`, `Application` and `Device`.
- Not re-checked:
    - no-GPU device setup carries on with a null physical device;
    - instance failure calls `exit(-1)`;
    - `VkNativeBatch::commitAndDispose()` does not wait for the queue;
    - depth and stencil state come from fragment-stage symbols, and the stencil operations are limited (`eKeep`/`eReplace`, reference hard-wired to 0).

## 7. Work packages

| Chunk | Scope |
|---|---|
| W26.1 | This design and a plan for W26.2. |
| W26.2 | First build: headless path, test bundle, function tier on the fragment path, epsilon and kernel contracts, report items 1 to 4. A first set of shading-function tests (a BRDF term at least). The October triangle, depth and stencil tests as the pipeline tier's first checks, if they fit. Rescoped from "five baseline shaders match goldens". |
| W26.3 | CI on lavapipe with the same contracts. |
| later | Compute tier, once compute pipelines exist (W12.2). Pipeline tier with the existing shaders. Work-graph tier when the extension is stable. |
| W26.4 | Shader performance analysis adapter (split out 2026-11-14). |
| later | Probes: capture a value inside a shader and show it over a raster (section 8). |

## 8. Left for later (owner, 2026-11-14)

- **Probes**: capturing an intermediate value inside a shader (for example a BRDF's D, G and F terms before they are combined) is the same ability the editor's shader graph needs for a preview on each node. It is built once, as part of the shader toolchain, and used by both the harness report and the node previews. Its own work package, next to the material graph work ([W47.4](../plan/work/visual-scripting-hmr.md), [W16.1](../plan/work/materials-post.md)).
- **Editor view of the report**: reads the same report data.
- **Performance analysis**: W26.4.
- **Image comparison for the pipeline tier**: FLIP with one reference and one threshold per test, valid everywhere. Rasterisation at triangle edges can differ between implementations, so pipeline tests either avoid edge texels or the contract masks them. Decided when the pipeline tier is built.

## 9. Left to the builder

- The exact API of the test helper, the contract types and the report format (it only has to be plain data that a program can read).
- How the bundle is wired into CMake and excluded from CPU-only runs.
- How the run waits for the GPU (a blocking submit is fine).
- Whether `Device`, `Application` and `Graphics` get a headless mode or a test-only variant, as long as the production path stays unchanged.
