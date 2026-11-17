# GPU Test Harness

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip` after PR [#193](https://github.com/Heliogrim/Heliogrim-Engine/pull/193), 2026-11-16. Not on `master` yet.
**Modules** (see the [module map](../architecture/modules.md)): `Engine.Graphics.Gpu.Test` (the harness and its tests, folder [`src/Engine.Graphics.Gpu.Test`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test)), `Engine.Graphics` (the headless setup in [`Graphics`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics/Graphics.cpp), [`Application`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics/Application/Application.cpp) and [`Device`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics/Device/Device.cpp)), with `Engine.Accel.*` and `Engine.Driver.Vulkan` as the code under test.
**Related**: [GPU test harness design](../architecture/gpu-test-harness-design.md) (W26.1), [quality and process work packages](../plan/work/quality-and-process.md) (W26.2 done, W26.3 open), [Accel shader toolchain](accel/index.md), issues [#191](https://github.com/Heliogrim/Heliogrim-Engine/issues/191) (compiler diagnostics in the report) and [#192](https://github.com/Heliogrim/Heliogrim-Engine/issues/192) (included bindings are not sliced).

## Purpose

Shading functions such as GGX or Schlick Fresnel used to be checked by running the whole renderer and pushing intermediate values into the screen. The harness checks one function in isolation. A test writes a small ASL fragment shader that calls the function once per texel, the harness draws it into a float image on a real GPU, reads the floats back and compares them with values computed on the CPU. The result is a pass or fail per check plus a report that says where, by how much, and with which inputs the output missed.

Every test brings up its own Vulkan instance and device with the validation layer, and any validation warning or error fails the test. That makes the validation layer the leak check.

What it does not do today: compute shaders (the engine cannot build compute pipelines yet), whole-pipeline or image comparisons, probes inside a function, and Release builds. See [Limits](#limits-and-known-issues).

## Where it sits

```hg-diagram
flowchart LR
    T["gtest TEST_F<br/>(Test/*.cpp)"]
    F["GpuTest fixture<br/>HeadlessEngine + ValidationCapture"]
    G["Graphics::setupHeadless<br/>instance, device, factories"]
    RF["runFunction<br/>(FunctionTier)"]
    AC["Engine.Accel.Lang / Compile<br/>parse, compose, glslang, pipeline"]
    DRV["Engine.Driver.Vulkan<br/>VkRCmdTranslator"]
    TGT["FunctionTarget<br/>RGBA32F image, readback"]
    CON["Contract kernels<br/>(CPU)"]
    REP["Report<br/>text + gpu-results/*.yaml"]
    SH[("assets/shader/shared/*.asl")]
    T --> F --> G
    T --> RF
    SH -->|"#include"| RF
    RF --> AC
    RF --> DRV
    RF --> TGT
    TGT -->|"Raster"| CON
    CON --> REP
```

The harness reuses the production compile and draw path: the same `parseModule`, `EffectCompiler`, `VkAccelerationPassFactory`, `RenderCommandBuffer` and `VkRCmdTranslator` the renderer uses. Only instance and device setup have a headless branch, and every new parameter defaults to the old behaviour.

## How it works

### Files

| File | What it holds |
|------|---------------|
| [`Harness/HeadlessEngine.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/HeadlessEngine.hpp) | an `Engine` with only a `Graphics` module; every other module getter returns `nullptr` |
| [`Harness/GpuTest.{hpp,cpp}`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/GpuTest.cpp) | the gtest fixture: device per test, validation check in `TearDown` |
| [`Harness/ValidationCapture.{hpp,cpp}`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/ValidationCapture.cpp) | a `VkDebugUtilsMessengerEXT` that stores warning and error messages |
| [`Harness/FunctionTarget.{hpp,cpp}`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/FunctionTarget.cpp) | the `R32G32B32A32_SFLOAT` target: clear, read back into a `Raster` |
| [`Harness/FunctionTier.{hpp,cpp}`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/FunctionTier.cpp) | `FunctionTestDesc` and `runFunction`: the one entry point a function test calls |
| [`Harness/Contract.{hpp,cpp}`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/Contract.cpp) | `Contract`, `Kernel`, `CheckResult` and the four built-in kernels |
| [`Harness/Report.{hpp,cpp}`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/Report.cpp) | `Report`, `makeReport`, and `store::` (YAML report, previous-run file) |
| [`Harness/Raster.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Harness/Raster.hpp) | `Raster`: an extent and row-major `fvec4` texels, row 0 on top |
| `Test/*.cpp` | `DeviceTest` (device, leak, GPU selection), `ReadbackTest`, `ContractTest`, `ReportTest` (CPU only), `FunctionTierTest` (harness behaviour), `PbrTest` (the real checks) |

### Headless setup in Engine.Graphics

`Graphics::setupHeadless(onInstance_)` creates only the instance, the device, its queues and the buffer and texture factories: no window, surface, swapchain, caches, pools, loaders or renderer.

1. `Application::setup(true)` creates the instance with the same layer and extension lists as production. On failure it rethrows instead of calling `exit(-1)`.
2. `onInstance_` runs with the new instance. The fixture uses it to attach the validation messenger before the device exists.
3. `Device::setup()` takes the headless branch, `selectHeadless`. A physical device qualifies when it has the engine's device extensions (`VK_KHR_swapchain`, `VK_KHR_multiview`, `VK_KHR_separate_depth_stencil_layouts`), Vulkan 1.2, the features `shaderInt8`, `separateDepthStencilLayouts` and `multiview`, and `R32G32B32A32_SFLOAT` with color-attachment and transfer-source support in optimal tiling. A discrete GPU wins; otherwise the first match is taken.
4. If `HELIOGRIM_TEST_GPU` is set, only devices whose name contains the value (case-insensitive) are considered. No match, or no qualifying device at all, throws `std::runtime_error("no GPU with these capabilities found")`.
5. The headless device is created without device layers (the loader warns about them, and the capture would count the warning). A failure after `vkCreateDevice` rolls back the queues, the allocator and the device before the exception leaves.

`Graphics::destroyHeadless(beforeInstance_)` waits on all three queues with the C `vkQueueWaitIdle` (the vk-hpp wrapper throws after a device loss and would skip teardown), destroys the factories and the device, calls `beforeInstance_`, destroys the instance, and finally throws `std::logic_error("Device still had N holder(s) after destroy.")` if anything else still held the `sptr<Device>`.

### Fixture lifecycle

```hg-diagram
sequenceDiagram
    participant GT as gtest
    participant F as GpuTest
    participant E as HeadlessEngine
    participant G as Graphics
    participant V as ValidationCapture
    GT->>F: SetUp()
    F->>F: validationLayerAvailable()? else FAIL "validation layer not active"
    F->>E: make_uptr (becomes Engine::getEngine())
    F->>E: preInit, init, postInit
    E->>G: setupHeadless(onInstance)
    G->>V: onInstance: create messenger
    G->>G: select and create device
    GT->>F: test body (device(), runFunction, ...)
    GT->>F: TearDown()
    F->>E: shutdown, exit (teardownDevice)
    E->>G: destroyHeadless(beforeInstance)
    G->>G: wait queues, destroy device (leak messages arrive here)
    G->>V: beforeInstance: release messenger
    G->>G: destroy instance
    F->>F: EXPECT messages().empty(), print them
```

Points that matter when writing a test:

- **One device per test.** The validation layer reports leaked device objects at `vkDestroyDevice`, so a device that lives longer than a test would hide leaks. Measured during W26.2 (Debug, RX 9070 XT): a device-only test about 100-130 ms, a function test 540-940 ms, the bundle about 6 s.
- **The engine is global.** Constructing `HeadlessEngine` sets `Engine::getEngine()`. The accel compile and pass code finds the device through `Engine::getEngine()->getGraphics()->getCurrentDevice()`, which is why a test engine is needed at all.
- **Any warning fails.** The messenger captures severities warning and error, of types general, validation and performance. `TearDown` lists every message under the failed `EXPECT_TRUE`.
- **`teardownDevice()`** can be called from the test body to force the leak report early; it is idempotent, and `validation()` still returns the captured messages afterwards. `GpuTest.LeakIsDetected` does this and then calls `validation().clear()` so the expected leak does not fail the test.
- A setup failure (`no GPU ...`, instance or device creation) is reported by `FAIL()` in `SetUp`; gtest then skips the body but still runs `TearDown`.

### The function tier

`runFunction(device, desc)` is the whole API for a function test. A `FunctionTestDesc` holds:

| Field | Meaning | Default |
|-------|---------|---------|
| `name` | report and previous-run file name, for example `"Pbr.NdfGgx"` | none |
| `fragmentAsl` | ASL fragment shader text | none |
| `extent` | raster size in texels | 32×32 |
| `expected` | `fvec4(u32 x, u32 y)`: the expected texel | none |
| `inputs` | `String(u32 x, u32 y)`: a description of the inputs at a texel, printed for failing or changed texels | none |
| `contract` | list of kernels | `absEpsilon(1e-5)` on all four channels |

What `runFunction` does, in order:

```hg-diagram
flowchart TD
    A["FunctionTarget(extent)<br/>clear to sentinel -4096"] --> B["expected raster from desc.expected<br/>loadPrevious(name)"]
    B --> C["parseStage: cover vertex shader + desc.fragmentAsl<br/>includes below HG_TEST_SHADER_ROOT"]
    C --> D["buildGraphicsPass(color in, color out)<br/>EffectCompiler::compile, no target symbols"]
    D -->|"pipeline == nullptr"| X["read target; single check 'compile' fails<br/>notes = parse diagnostics"]
    D --> E["draw: 3 vertices, one triangle<br/>RenderCommandBuffer -> VkRCmdTranslator -> submit, waitIdle"]
    E --> F["read target into Raster"]
    F --> G["checks = gpu-ran + contract kernels"]
    G --> H["makeReport; writeReport (always)<br/>savePassing (on pass)"]
    X --> H
```

- **One fragment per texel.** The harness supplies the vertex shader: a single triangle with corners (-1,-1), (3,-1), (-1,3), clipped to the target. The fragment shader reads its texel from the builtin `frag_coord`; `frag_coord.xy` is the texel centre, `(x + 0.5, y + 0.5)`, with row 0 on top.
- **Output contract.** The shader must declare `@output (mode = forward, id = "color") f32vec4 color;`. The pass is built with the target as both input and output, so the render pass loads the sentinel clear instead of clearing again.
- **Proof the GPU ran.** The target is cleared to `sentinel` (`-4096.0`) first. The `gpu-ran` check passes when at least one texel differs from the sentinel in any channel. It does not check that every texel was written; the contract does that.
- **Includes.** `#include <shared/pbr.asl>` resolves below `HG_TEST_SHADER_ROOT`, which CMake sets to `${CMAKE_SOURCE_DIR}/assets/shader`. An absolute path or one that leaves the root resolves to nothing and the parser reports `unknown include '<name>'`.
- **No target symbols.** The specification passes an empty target list, so nothing is sliced: every function and binding an include declares stays in the shader (see [#192](https://github.com/Heliogrim/Heliogrim-Engine/issues/192)).

### Worked example: `Pbr.NdfGgx`

From [`Test/PbrTest.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Gpu.Test/Test/PbrTest.cpp). The test checks `ndfGgx` from `shared/pbr.asl` over a 64×64 raster: roughness along x, N·H along y.

**1. Fixture.** A test suite is an empty subclass of `GpuTest`:

```cpp
class Pbr :
	public GpuTest {};

// Enough texels per axis to resolve the shape of each lobe; matches the 64-step input sweeps.
inline constexpr static u32 side = 64uL;
inline constexpr static math::uivec2 extent { side, side };

// Lowest swept roughness; keeps the GGX lobe resolvable on a 64-texel raster and the epsilon guard inactive.
inline constexpr static f64 minRough = 0.05;
```

**2. Input mapping on the CPU side.** The helpers compute the same input the shader computes from `frag_coord`, at the texel centre:

```cpp
[[nodiscard]] f64 centre(const u32 i_) {
	return (static_cast<f64>(i_) + 0.5) / static_cast<f64>(side);
}

[[nodiscard]] f64 roughAt(const u32 i_) {
	return minRough + (1.0 - minRough) * centre(i_);
}

[[nodiscard]] math::fvec4 scalar(const f64 value_) {
	return math::fvec4 { static_cast<f32>(value_), 0.F, 0.F, 1.F };
}
```

**3. An independent CPU reference.** It is written from the paper, not copied from the shader, and computed in `f64`:

```cpp
// Walter et al. 2007, eq. 33 with alpha = rough^2 (Burley 2012 remapping, as the shader states).
[[nodiscard]] f64 ggx(const f64 ndh_, const f64 rough_) {
	const auto alpha2 = std::pow(rough_, 4.0);
	const auto cos2 = ndh_ * ndh_;
	const auto tan2 = (1.0 - cos2) / cos2;
	const auto term = alpha2 + tan2;
	return ndh_ <= 0.0 ? 0.0 : alpha2 / (pi * cos2 * cos2 * term * term);
}
```

The shader uses the form `ap2 / (PI * ((ndh² (ap2 - 1) + 1)²))`; the reference uses the tangent form. Two different formulas that agree are the check.

**4. The test.** Wrapper shader, expectation, input description and contract in one call:

```cpp
TEST_F(Pbr, NdfGgx) {

	const auto report = runFunction(
		device(),
		FunctionTestDesc {
			.name = "Pbr.NdfGgx",
			.fragmentAsl = R"(
#include <shared/math.asl>
#include <shared/pbr.asl>

@output (mode = forward, id = "color") f32vec4 color;

fn main() {
	let rough = 0.05 + 0.95 * frag_coord.x / 64.0;
	let ndh = frag_coord.y / 64.0;
	color = f32vec4(ndfGgx(ndh, rough), 0.0, 0.0, 1.0);
}
)",
			.extent = extent,
			.expected = [](const u32 x_, const u32 y_) { return scalar(ggx(centre(y_), roughAt(x_))); },
			.inputs = [](const u32 x_, const u32 y_) { return pair("rough", roughAt(x_), "ndh", centre(y_)); },
			.contract = Contract { { relEpsilon(1e-4F, 1), monotonic(Axis::eY, 0, Order::eIncreasing) } }
		}
	);

	EXPECT_TRUE(report.passed()) << report.text();
}
```

Things to notice:

- `shared/pbr.asl` needs `PI` from `shared/math.asl`, so `math.asl` is included first.
- The shader divides by the literal `64.0`. It must equal `side`; nothing checks that the two agree.
- The result goes into `.x`; the other channels are constants. The contract passes `channels_ = 1`, so only channel 0 is compared.
- GGX spans several orders of magnitude over the raster, so the contract is relative (`relEpsilon(1e-4)`), plus a shape check: the lobe must not decrease towards N·H = 1 (`monotonic` along y).
- The assertion prints `report.text()`, so a failure shows the checks, the error summary and the inputs at failing texels.

`Pbr.ChangedFunctionFails` is the negative control: a local Fresnel copy with exponent 4 instead of 5 must fail `absEpsilon` and list `(0, 0) ct=0.007812 f0=0.04 f90=1` among the inputs. A new kind of check deserves the same kind of control.

### Contracts and tolerances

A `Contract` is a list of `Kernel`s, each `std::function<CheckResult(actual, expected)>` over the whole raster. `check()` first compares extents and texel counts; a mismatch returns a single failed `extent` result and no kernel runs.

| Kernel | Fails a texel when | `measured` |
|--------|--------------------|------------|
| `absEpsilon(eps, channels = 4)` | `|a - e| > eps` in any of the first `channels`, or either value is not finite | max error |
| `relEpsilon(eps, channels = 4)` | `|a - e| / max(|e|, 1e-6) > eps`, or not finite | max relative error |
| `monotonic(axis, channel, order)` | the next texel along `axis` breaks the order, or either is not finite; uses `actual` only | failing count |
| `slopeEpsilon(axis, channel, eps)` | the step along `axis` differs from the expected step by more than `eps`, or not finite | max step error |
| your own lambda | whatever it returns | yours |

- `defaultAbsEpsilon` is `1e-5`. The W26.2 run measured 3.6e-6 relative error for GGX and about 6e-8 absolute for the other PBR terms, so the defaults leave head room on the reference GPU. The same contract is meant to hold on every implementation, lavapipe included; the harness never loosens it per device.
- Non-finite values always fail, but they do not raise `measured`. A NaN-only failure shows `failing > 0` with `measured 0`.
- Each result lists at most `listCap` (32) failing texels; `failing` is the full count. `monotonic` lists the second texel of a broken pair, `slopeEpsilon` the first.
- With the default `channels_ = 4`, the alpha and unused channels are compared too. Write constants into them that the expectation repeats, as `scalar()` does, or pass `channels_ = 1`.

### Readback

`FunctionTarget` builds a device-local `R32G32B32A32_SFLOAT` image with color-attachment, transfer-source and transfer-destination usage. It rests in `eColorAttachmentOptimal` between operations.

- `clear(value)` records a transfer clear and transitions back to the attachment layout.
- `read()` creates a host-visible, host-coherent staging buffer, copies the image with tightly packed rows, adds a transfer-to-host barrier, transitions the image back and copies the mapped memory into a `Raster`.
- Both submit one command buffer and block with `submitWait`. The staging buffer and the command buffer are released on every path, including throws.

The raster is exactly what the GPU wrote: no conversion, no gamma. `ReadbackTest` checks a clear round trip, including an odd 33×17 extent with a second target alive.

### Report

`makeReport` turns the checks into a `Report`:

1. `checks`: `gpu-ran` first, then the contract's results in order (or a single `compile` result).
2. `vsExpected`: max error, where, and mean, using the largest absolute error over all four channels of a texel; plus `errorMap`, the absolute error per channel.
3. `vsPrevious` and `changedTexels`: the same summary against the last **passing** run of this test name, and the number of texels that differ at all (bit-exact). Missing when no run is stored or the extent changed.
4. `inputs`: the `desc.inputs` text for each listed texel, failing texels from all checks first, then changed texels, at most 32.

`report.text()` prints `notes` (parse diagnostics), one `PASS`/`FAIL` line per check, both summaries and the input lines. The shape of the text for `Pbr.ChangedFunctionFails` (64×64, so `gpu-ran` measures 4096 written texels; other values elided):

```text
PASS gpu-ran: failing 0, measured 4096
FAIL absEpsilon: failing ..., measured ...
PASS monotonic: failing 0, measured 0
FAIL slopeEpsilon: failing ..., measured ...
vs expected: max ... at (0, 0), mean ...
vs previous: no stored run
(0, 0) ct=0.007812 f0=0.04 f90=1
...
```

Files in `gpu-results/`, next to the test executable (found through `GetModuleFileNameW` on Windows, the current directory elsewhere):

| File | Written | Content |
|------|---------|---------|
| `<name>.report.yaml` | every run | `test`, `passed`, `width`, `height`, `checks`, `vsExpected`, `vsPrevious` and `changedTexels` when present, `inputs`, `errorMap` (one row of max-channel errors per raster row) |
| `<name>.last.f32` | only on pass | two `u32` (width, height) then the raw `fvec4` texels |

Both are written to a `.tmp` file and renamed, so a failed write never leaves a truncated file. Neither is committed.

## Running it

Build and run (Debug only, see below):

```powershell
rtk cmake --build .\cmake-build-debug-visual-studio-clang --target Heliogrim-Engine.Graphics.Gpu.Test -j 7
rtk .\dist\Debug\amd64-windows\Heliogrim-Engine.Graphics.Gpu.Test.exe --gtest_color=no
rtk .\dist\Debug\amd64-windows\Heliogrim-Engine.Graphics.Gpu.Test.exe --gtest_color=no --gtest_filter=Pbr.*
```

- The bundle is built with `EXCLUDE_FROM_ALL_TESTS`: it is **not** part of `Heliogrim-AllTests`. Build its target by name.
- ctest gets the label `gpu`, and tests are discovered with `DISCOVERY_MODE PRE_TEST`, so building never runs the executable. A machine without a GPU skips the bundle with `ctest -LE gpu`.
- Set `HELIOGRIM_TEST_GPU=<part of the device name>` to pick a GPU on a machine with several.
- The executable reads shared shader files from `assets/shader/` of the source tree configured into it (`HG_TEST_SHADER_ROOT` is an absolute path). The assets are a separate checkout; without them every include fails.

Requirements:

- A Vulkan 1.2 device and driver with the features listed under [headless setup](#headless-setup-in-enginegraphics), including `VK_KHR_swapchain` (the extension list is shared with production, even though no swapchain is made).
- The Vulkan SDK's `VK_LAYER_KHRONOS_validation`, `VK_LAYER_KHRONOS_synchronization2` and `VK_LAYER_KHRONOS_shader_object`. `Application` requests all three in Debug without checking they exist, so a missing one fails instance creation (headless rethrows the error into `SetUp`).
- A **Debug** build. `Application` enables the validation layers and `VK_EXT_debug_utils` only under `_DEBUG`.

## Debugging

| Symptom | Cause and where to look |
|---------|-------------------------|
| `validation layer not active` from `SetUp` | the layer is not installed, or this is a Release build (the layer may be installed but `VK_EXT_debug_utils` is not enabled, so the messenger cannot be created) |
| `no GPU with these capabilities found` | no device passes `supportsHeadless`, or `HELIOGRIM_TEST_GPU` matches no device name |
| `FAIL compile` with `error[ASL....]` in the notes | a parse or typecheck error in `fragmentAsl` or an include |
| `FAIL compile` with only `effect compile failed; the composer logged its diagnostics` | the error came from composition (merge, contract, layout) or glslang; it is in the console log only ([#191](https://github.com/Heliogrim/Heliogrim-Engine/issues/191)) |
| `unknown include '<name>'` | the path is absolute, leaves `assets/shader`, or the file is missing |
| `FAIL gpu-ran` | nothing was drawn, or every texel holds exactly `-4096` |
| test passes its checks but fails in `TearDown` with validation messages | a validation warning or a leaked Vulkan object; the messages are printed under the failed expectation |
| `Device still had N holder(s) after destroy.` | something still holds the `sptr<Device>` at teardown, for example a `FunctionTarget` or a copy of `device()` kept in a fixture member or a static |
| abort inside `VkRCmdTranslator` before submit | most likely an included library declares `@input` bindings that have no descriptors ([#192](https://github.com/Heliogrim/Heliogrim-Engine/issues/192)) |
| `vs previous` shows unexpected changes | the stored run is the last *passing* run of that name; delete `gpu-results/<name>.last.f32` to reset |

The YAML report is the place to read a failure in detail: `errorMap` shows the error over the whole raster, which makes a wrong axis or an off-by-half-texel input mapping obvious at a glance.

## Limits and known issues

- **Debug only.** In Release the validation layers and `VK_EXT_debug_utils` are not enabled, so every fixture test fails in `SetUp`. This is on purpose (no validation means no leak check), but there is no Release story yet.
- **Included `@input` bindings break the draw.** With no target symbols nothing is sliced, so a library such as `shared/lighting.brdf.asl` brings its bindings along without descriptors; the test aborts before submit. Today only `shared/math.asl` and `shared/pbr.asl` are safe ([#192](https://github.com/Heliogrim/Heliogrim-Engine/issues/192)).
- **Compiler-stage diagnostics are not in the report**, only in the log ([#191](https://github.com/Heliogrim/Heliogrim-Engine/issues/191)).
- **Fragment path only.** No compute tier (the engine has no compute pipeline creation), no pipeline tier, no image comparison, no probes inside a function.
- **No CI.** W26.3 (lavapipe in CI with the same contracts) is not done; the contracts are only proven on the owner's AMD RX 9070 XT.
- **The bundle depends on assets outside the repository** through an absolute include root fixed at configure time.
- **Test names are file names.** Two tests with the same `name` share a report and a previous run. `FunctionTier.IncludeOutsideRootFails` reuses one name inside a loop on purpose.
- **Leaks at instance destruction are not captured.** The messenger is released just before `vkDestroyInstance`, so only messages up to `vkDestroyDevice` count.
- **Writing exactly `-4096` everywhere looks like no write.** `FunctionTier.UnwrittenTargetFails` writes the sentinel for exactly this reason; its comment notes that using `discard` instead would need the demote-to-helper device feature.

## Changing it

- **A new function test**: copy the `PbrTest.cpp` pattern. Keep the wrapper shader in the test as text, compute the expectation from an independent CPU implementation at texel centres, pick an absolute or relative epsilon by the function's range, add a shape kernel where the shape matters, and pass `report.text()` to the assertion. Add a negative control for a new kind of check.
- **A new kernel**: add it to `Contract.{hpp,cpp}` next to the others, return a `CheckResult` with a unique `name`, fail on non-finite values, cap the listed texels with `listCap`, and cover it in `ContractTest` (CPU only, no device).
- **Report format**: `Report.hpp` and `store::writeReport`; `ReportTest` pins the text, the YAML and the previous-run file without a device. The YAML is meant to be read by programs and agents, so keep keys stable.
- **Headless setup**: the production path must stay unchanged. `Graphics::setupHeadless`/`destroyHeadless`, `Application::setup(bool)` and the `headless()` branches in `Device::setup()` are the only headless code. `DeviceTest` covers device bring-up, leak detection and the `HELIOGRIM_TEST_GPU` failure.
- **Device requirements**: `supportsHeadless` in `Device.cpp` is the gate. When a shader under test needs another device feature (the emitter reports them in `GlslRequirements`, for example `shaderFloat16`), check that the device creation enables it and add it to the gate, so a device without it fails with the clear message instead of a validation error.
- After adding a file to the bundle, reconfigure CMake: sources are globbed per directory.
