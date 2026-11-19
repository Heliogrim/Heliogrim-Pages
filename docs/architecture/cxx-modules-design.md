# C++ Modules (Design)

**Status**: design, accepted by the owner 2026-11-19 (calls marked "my call" included). No issue yet. Spike branch `spike/cxx-modules` (commits `92b77864`, `89a2b147`, local only, throwaway), worktree `Heliogrim-CLion-wt/cxx-modules`. Earlier effort estimate: 2026-11-07 (4-8 person-months for a direct rewrite; superseded by the phased approach here).

Markers: **Decided** = owner decision in the brainstorm. **Proposal** = this document's call, open to correction. **Builder's call** = left to the implementer.

## 1. Intent

Clean editor builds are dominated by clang-cl's frontend: the 2026-11-07 trace measured parsing at about 94 % of CPU time (5105 s parse vs 327 s backend). The top costs are headers re-parsed by hundreds of translation units: `Engine.Graphics/vkinc.hpp` (vulkan.hpp, ~540 s over 141 TUs), `<memory>`, `<chrono>`, `Engine.Filesystem/Path.hpp`, `Engine.Assets.Type/Asset.hpp`. PCH was rejected (2026-11-08); header diet and forward-declaration firewalls (`__vkFwd.hpp`) have diminishing returns.

C++ named modules let each bundle be parsed once into a binary module interface (BMI) and imported cheaply everywhere else. The goal is to convert the engine progressively, starting with the most-included code, without a months-long rewrite before the first payoff.

## 2. Decisions

- **Decided**: re-enable CMake module support (`CMAKE_CXX_SCAN_FOR_MODULES ON`, `cmake/GlobalSettings.cmake`).
- **Decided**: toolchain is clang-cl only for now. The MSVC `cl` build dir (`cmake-build-debug`) does not have to keep working during phase 1. CMake, Ninja and clang-cl versions are not re-checked.
- **Decided**: a library project is also a named module; the module name is the `LIB_NAME` (`Engine.Common`, `Engine.Asserts`, ...).
- **Decided**: a new `make_library_sub_project` attaches a project to a root project made with `make_library_project`. The sub-project becomes part of the root's module; its declared libraries merge into the root's. Cycles between a root and its subs are allowed; cycles between separate modules are removed step by step.
- **Decided**: two phases. Phase 1 converts bundles with a **generated wrapper module** ("style A", section 4) and sweeps every consumer from `#include` to `import`. Phase 2 progressively **rebuilds** swept bundles into real named modules by editing the sources (`export` in source, partitions).
- **Decided**: no hand-replicated headers or hand-written export lists for engine bundles.
- **Decided**: first wave is Engine.Asserts (its own module; it includes nothing from other bundles except `Engine.Common/__macro.hpp`), Engine.Common, and a Vulkan module.
- **Decided**: vendored libraries get a maintainable "auto-convert to module" strategy, provided through the `add_managed_library` helpers.
- **Decided**: the new CMake code follows the conventions of `MakeLibraryProject.cmake`, `MakeTestProject.cmake`, `Managed.cmake`, `Options.cmake`, `Discover.cmake` (section 5.1).

## 3. Spike evidence

Measured 2026-11-18 on the spike (clang-cl 22, Debug, sccache bypassed, 3 runs each, one TU compiled alone).

| TU compiles ... | `#include` | `import` | BMI build (once) | BMI size |
|---|---|---|---|---|
| all Engine.Common + Asserts headers | 1.65 s | 0.41 s | 2.3 s + 0.55 s | 40 MB + 5.5 MB |
| Vulkan (`vkinc.hpp` vs `import vulkan`) | 1.9 s | 0.27 s | 5.35 s | 76 MB |

`clang-scan-deps` adds about 0.3 s per TU once scanning is on (on the order of 5 % of the 2026-11-07 parse total if applied to every TU).

Two ways to make a module out of existing headers were tested:

- **Style A, purview wrapper** (chosen). Own headers are `#include`d inside `export extern "C++" { ... }` after `export module X;`. Nothing is listed by hand. `extern "C++"` attaches the declarations to the global module, so they are the same entities a textual include declares.
    - include-then-import in one TU: **works**.
    - import-then-include: **fails** for namespace-scope variables (also `inline constexpr`), deduction guides, concepts and default arguments ("redefinition"). Classes and functions merge.
- **Style B, global-fragment wrapper**. Headers in the global module fragment, names exported with `export using`. Mixes in both orders (one concept in `Engine.Pedantic/Into/Into.hpp` still failed), but needs a per-name export list; `export using namespace hg;` does not export anything (tested). Upstream `vulkan.cppm` is this style and mixes cleanly in both orders.

Other findings:

- Headers that `#define` something (`__macro.hpp`, `GLM.hpp`, `SDL3.hpp`, `Sal.hpp`, `ThreadSafety.hpp`, `Math/MathDefaultDefine.hpp`) must stay textual and come first in the global module fragment, because they configure vendor headers (`GLM_ENABLE_EXPERIMENTAL`) and because modules cannot export macros.
- Excluding a header must also exclude every header that includes it: `Engine.Common/Inc.hpp` pulls `stdafx.h` and through it `Windows.h` into the purview, which breaks.
- An `import X;` that reaches the purview through an included header is an error, even if the same import was also placed before the export block. The guarded form works (section 4.3).
- Latent header bugs surfaced: `Collection/InlineVector.hpp:193` passed `val_` instead of `val_...` (fixed on the spike); `Collection/RingBuffer.hpp` names a nonexistent `hg::vector` (dead file, excluded on the spike).
- `vulkan.cppm` (headers 1.4.335) unconditionally does `export import std;` and its `:video` partition is declared as `vulkan_hpp:video`, so it is not usable as shipped. The adapter (section 6) keeps its export list and swaps the global fragment.

## 4. Phase 1: generated wrapper modules

### 4.1 What the generator writes

For a bundle with module support switched on, CMake generates `<build>/modules/<LIB_NAME>.cppm` at configure time:

```cpp
// Generated; do not edit.
module;
#define HG_MODULE_INTERFACE_UNIT
#include <Engine.Common/__macro.hpp>       // headers with #define, in file-set order
#include <Engine.Common/GLM.hpp>
#include <type_traits>                     // foreign <...> includes found in own headers
#include <tl/optional.hpp>
// ...
export module Engine.Common;
import Engine.Asserts;                     // imports found in own headers, hoisted

export extern "C++" {
#include "Engine.Common/Optional.hpp"      // every own header not excluded (quoted: clang-scan-deps
                                           // warns on angled purview includes and ignores -Wno)
// ...
}
```

Rules (all exercised on the spike except the import hoisting, which was probed by hand):

1. Own headers = the bundle's header file set plus the header sets of its sub-projects.
2. An own header that contains a `#define` goes to the global fragment, in front, and stays textual for consumers.
3. Every `#include <...>` in an own header that does not name an own bundle goes to the global fragment, so its include guard fires before the purview.
4. `MODULE_EXCLUDE` headers stay out of the module; the exclusion is closed over every own header that includes an excluded one.
5. `import X;` lines in own headers are hoisted after the module declaration; the headers themselves use the guarded form (4.3).
6. The generated file is only rewritten when its content changes (no rebuild churn on reconfigure).
7. The generated unit is compiled with `-Wno-include-angled-in-module-purview`; the purview includes are intentional.

### 4.2 Sweep per bundle

A bundle's module is switched on in the same change that sweeps its consumers. Because of the import-then-include restriction, after the sweep **no file outside the bundle may `#include` one of its module headers**:

- Every file except the module headers themselves replaces includes of module headers with `import <Bundle>;` (plain in `.cpp`, guarded in headers, 4.3). This includes the bundle's own `.cpp` files and its excluded headers: the interface is compiled in a separate provider target (5.4), so the bundle can import its own module. Only module headers keep including each other textually.
- `__macro.hpp` and other `#define` headers stay `#include`d where their macros are used.
- Excluded headers (rule 4) are not in the module, so consumers keep including them.

Done when the editor and `Heliogrim-AllTests` build and all test suites pass.

- **Decided**: the sweep is scripted (one-off script for the mechanical `#include` -> `import` rewrite, reviewed via `git diff`; edge cases by hand). This overrides the standing hand-edit rule for this sweep only. The script is not kept in the repo.

### 4.3 Imports in headers

Every `import` written into a header uses:

```cpp
#if not defined(HG_MODULE_INTERFACE_UNIT)
import Engine.Asserts;
#endif
```

The generator defines `HG_MODULE_INTERFACE_UNIT` as the first line of the global fragment and hoists the import after the module declaration. Defining it before the fragment (not just before the export block) also covers `#define` headers that import and therefore sit in the fragment, where imports are not allowed (`vkinc.hpp`). `.cpp` files use plain `import`. This keeps headers valid for both consumers and later generated modules.

### 4.4 Waves

1. **Engine.Asserts**: own module; drop its link to Engine.Common (it only uses `__macro.hpp`). `Pal.hpp` contains `#define`s, so it lands in the global fragment by rule 2.
2. **Engine.Common**, with **Engine.Pedantic** as sub-project (Common includes Pedantic and Pedantic includes Common). Proposed exclusions from the spike: `Math/Transform.hpp` (includes Engine.Serialization), `Profiling/Profiler.hpp` (includes Engine.Async, which reaches Engine.Scheduler), `Collection/RingBuffer.hpp` (dead), `stdafx.h` (Windows.h) and, by closure, `Inc.hpp` and `Math/Inc.hpp`.
3. **Vulkan** (section 6). `vkinc.hpp` keeps its name and its macros and imports the module itself, so its 38 includers are not swept.

Later waves follow the bundle include graph bottom-up (re-check the bundle SCC before each).

### 4.5 Standard library and vendor modules (wave 2, revised 2026-11-19)

**Why.** The first wave 2 attempt (Engine.Common alone) failed on payoff, not on correctness. A global fragment is not visible to importers, so every consumer lost the std and vendor names Common's headers used to bring in. Giving them back textually brought the cost back: one TU took 0.29 s with the import only, 1.75 s with the import plus the std/vendor headers it needs, and 1.66 s fully textual. Almost all of Common's cost is std and vendor headers.

**Spike (2026-11-19, clang-cl 22.1.3, MSVC STL 14.52, engine flags):**

| TU | time |
|---|---|
| 15 std headers + uses, textual | 1.45 s |
| same, `import std;` | 0.30 s |
| `std.ixx` BMI build (`-w`) | 3.3 s, 39 MB |
| all Common headers + std uses, textual | 1.94 s |
| `import std; import Engine.Common;` (Common BMI as built by wave 2), same uses | 0.67 s |
| `import std;` + tl/ankerl/glm included textually *before* the imports | 1.37 s |
| `import std; import vendor; import Engine.Common;` (generated vendor wrapper) | 0.66 s |
| only `import Engine.Common;` with `export import std; export import vendor; export import Engine.Asserts;` in Common | 0.66 s |

**Mixing rules found:**

- `std.ixx` (MSVC STL's purview-style module) mixes like style A: textual std headers **before** `import std;` merge; textual std headers **after** it fail (`redefinition of 'is_same_v'`).
- Allowed after an import: C headers (`<string.h>`, `<math.h>`, `<stddef.h>`, ...), `<Windows.h>`, SDL3, intrinsics, and the macro-only std headers `<cassert> <climits> <cfloat> <cstdarg> <cerrno> <version> <cstdint> <cstdio> <cstring> <cstdlib> <csignal>`. Not allowed: `<cmath>`, `<cstddef>`, every other C++ std header, and every C++ vendor header that includes them (glm, tl, ankerl, Jolt, ...).
- A BMI whose global fragment includes std textually mixes with `import std;` in both orders (Common's BMI, generated vendor wrappers).
- `export import` in a generated interface restores include semantics: importers see everything the module's headers used to bring in.

**Decided (owner, 2026-11-19)**: replace standard headers with `import std;` engine-wide in phase 1 (scripted mass replacement).

**Proposal (my call, from the spike):**

1. `std` (and `std.compat`) are built from the MSVC toolset's `modules/std.ixx` / `std.compat.ixx` in a provider like any module (5.4), first in `DEFAULT_MODULES`, warnings off. CMake's experimental `import std` support is not used (clang-cl with MSVC STL is not a supported pairing there; our provider is a few lines).
2. Header-only C++ vendors that engine headers include become generated style A wrappers (section 6, option 2): `tl.optional`, `tl.expected`, `ankerl.unordered_dense`, `std23.function_ref`, `glm`. Their global fragment includes the std headers they use, so the wrapper BMI mixes with `import std;`.
3. Hoisted imports in generated interfaces become `export import` (std, vendor modules, other engine modules). Consumers keep relying on what a bundle's headers exposed; phase 2 narrows this.
4. The sweep replaces every C++ std include in `src/**` with `import std;` (guarded in headers) and every include of a wrapped vendor with its module import. The macro-only std headers above stay textual. `<cmath>`/`<cstddef>` macros (`NAN`, `HUGE_VAL`, `offsetof`) come from `<math.h>`/`<stddef.h>`.
5. A C++ vendor header that is not wrapped (Jolt, assimp, spdlog, ryml, spirv-tools, gli, tinyexr, crcpp, gtest) must come before every import in its TU. In `.cpp` files the sweep moves it to the top of the include block. Test sources include gtest through `pch.h` first. Engine headers that include one (Physics/Jolt, test harness headers) are handled per case: wrap the vendor, or keep the header out of other bundles' paths.

## 5. CMake surface

### 5.1 Conventions to follow

From the existing helpers: plain `snake_case` verbs without project prefix (`make_library_project`, `add_managed_library`, `discover_and_hydrate_targets`); private helpers start with `_` or `__` (`_store_deferred_library_tuple`, `__prepare_link_libs`); argument parsing through `set(__single_var_options ...)`, `set(__multi_var_options ...)`, `cmake_parse_arguments(args "<flags>" ...)`; `message(FATAL_ERROR "... `NAME` ...")` with backticked names for wrong arguments; `#` comment separators between blocks; tabs; one file per concern under `cmake/` with `include_guard(GLOBAL)`; global state through `set_property(GLOBAL PROPERTY global_...)` and `_load_global_*` macros. The spike's `hg_generate_wrapper_module`/`hg_adapt_vendor_module` do not follow this and are renamed.

### 5.2 `make_library_project`

- **Proposal**: multi-value `MODULE_EXCLUDE`. Which bundles are modules is one ordered list, `DEFAULT_MODULES` in `cmake/CompileOptions.cmake` next to `DEFAULT_LIBRARIES` (replaces the earlier per-bundle `MODULE` flag: the central link needs the full list anyway). A bundle joins the list in its sweep change. After the last sweep generation becomes the default.
- **Proposal**: a bundle that has hand-written module units (`*.cppm`, phase 2) skips generation; the existing glob for `.ixx/.cppm/...` stays.

### 5.3 `make_library_sub_project`

```cmake
make_library_sub_project(
		LIB_NAME Engine.Pedantic
		SUB_OF Engine.Common
		LIBRARIES ${PROJECT_NAME}::Engine.Common
)
```

- **Proposal**: parameter name `SUB_OF` (owner offered `SUB_OF` or `ROOT`).
- Sources of the sub go into the root target; headers into the root's header file set and generated module; `LIBRARIES` are merged into the root's (minus the root itself).
- Existing references to the sub (`${PROJECT_NAME}::Engine.Pedantic` in other bundles and tests) keep resolving.
- **Proposal (planning)**: `${PROJECT_NAME}::<sub>` becomes an `ALIAS` of the root target; the merge and all interface generation run in one `cmake_language(DEFER DIRECTORY <root> CALL _finalize_module_interfaces)`, so directory order does not matter.

### 5.4 Reaching importers

All bundle links are `PRIVATE` and many bundles (most of the editor) link only the aggregate `Heliogrim` target, so the include path reaches everything while a BMI only reaches targets that link the module. CMake hands a BMI to an importer only through its link closure.

- **Proposal (my call)**: each module's interface is compiled in its own small provider target `<Name>.Module` (OBJECT, only the generated `.cppm`), and `make_library_project` / `make_test_project` / `make_executable_project` link every provider in `DEFAULT_MODULES` (except their own). This mirrors today's "every header is reachable" without touching ~120 CMakeLists, keeps the bundles' own objects from being linked twice (only the tiny provider object is linked more than once), and lets a bundle import its own module. Providers link only the providers of their hoisted imports, so no cycles. The list shrinks to explicit links in phase 2.
- Checked 2026-11-19: `$<COMPILE_ONLY:...>` does not hand BMIs to the consumer ("module not found"), so a real link is required.

### 5.5 Generator file

- **Proposal**: `cmake/MakeModuleInterface.cmake` with `make_module_interface(...)` (engine bundles) and the vendor adapter (section 6), included from the root `CMakeLists.txt` next to `MakeLibraryProject.cmake`.
- **Builder's call**: internal helper split, regex details.

## 6. Vendored libraries

- **Decided**: the strategy is provided through `add_managed_library` / the vendor `library_*_init` functions.
- **Proposal**: order of preference per library:
    1. upstream module interface where shipped (Vulkan-Hpp `vulkan.cppm`, glm `glm.cppm`), adapted: keep its export list, replace its global fragment with our configuration, drop `export import std;` and broken partition imports. Upstream lists are style B, so imports and includes of that library mix in both orders.
    2. otherwise a generated style A wrapper over the library's public headers, with the same rules as section 4.1. Caveat: other vendor headers that include the library textually (gli includes glm) then must not follow an import of it in one TU.
    3. otherwise stay a header.
- ~~**Proposal**: phase 1 converts Vulkan only.~~ **Revised 2026-11-19**: phase 1 converts Vulkan, glm, tl optional/expected, ankerl and function_ref (section 4.5). Jolt and the rest are decided per library; SDL3 is C and mixes freely.
- **Proposal, Vulkan configuration (revised in planning)**: `vkinc.hpp` stays the single configuration point. Its global fragment use: the provider `vulkan.Module` (created by `library_vulkan_headers_init` through the vendor helper) includes `vkinc.hpp` with `HG_MODULE_INTERFACE_UNIT` defined, which takes the full `vulkan.hpp` branch. Everywhere else `vkinc.hpp` keeps its macros, includes `vulkan_hpp_macros.hpp` and `vulkan_core.h` (the engine uses `VK_QUEUE_FAMILY_IGNORED`, `VK_NULL_HANDLE`, ...) and does `import vulkan;`. The BMI is built without a Vulkan platform; `Engine.Graphics/Application/Application.cpp` (the only `VK_IMPL_PLATFORM` user) keeps the textual path, which mixes safely with the style B export list. `__vkFwd.hpp` stays as a header. Module name `vulkan`.

## 7. Phase 2: rebuilding named modules

Once nothing outside a bundle includes its module headers, the bundle can be rewritten by hand: headers become partitions (`export module Engine.Common:Optional;`), `export` moves into the source, internals stop being visible. Consumers do not change (they already `import Engine.Common;`). Order and pace per bundle; each rebuild is its own change. Partitions must import each other acyclically, so header-level cycles inside a bundle (2026-11-07: two trivial 2-cycles) are resolved first.

Phase-2 checklist from phase 1:

- About 400 files see std and the vendor modules only through Engine.Common's `export import`. Wave 2 left out their own `import std;` because CMake 4.4 repeats `-fmodule-file` entries in module maps, which pushed sccache past the 32k Windows command line. Restore the explicit imports before Common's exports narrow.

## 8. Non-goals and anti-goals

- Non-goal: MSVC `cl` support in phase 1.
- ~~Non-goal for phase 1: `import std;`~~ **Revised 2026-11-19 (owner)**: wave 2 showed that importing Engine.Common alone saves nothing while consumers re-parse std and vendor headers textually, so `import std;` and the header-only vendor modules moved into phase 1 (section 4.5).
- Non-goal: header units (no CMake support).
- Non-goal: PCH (rejected 2026-11-08).
- Anti-goal: hand-maintained export lists or duplicated headers for engine code.
- Anti-goal: a phase-1 bundle that builds but whose consumers still `#include` it (no gain, ODR risk).

## 9. Measuring

Before wave 1 and after each wave: clean `Heliogrim-Editor` Debug build with `-ftime-trace` and ClangBuildAnalyzer (same setup as 2026-11-07, sccache off), comparing total frontend time, the top header list, and wall time. Report scan-deps time separately.

- **Proposal (my call)**: sccache stays on (`HELIOGRIM_USE_COMPILER_CACHE`). The wave 1 checkpoint also measures a second clean build with a warm cache, so cache misses on module units and importers show up. If sccache cannot cache them, losing those hits is accepted for module units only and recorded here; it is not a reason to turn the cache off globally.
- **Baseline (feat/wip fd5affa5, 2026-11-19)**: `frontend_s=2249.4 scan_s=0.0 wall_s=373 tus=1368` (clean `Heliogrim-Editor`, `-ftime-trace`, sccache off, `-j 7`, `-k 0`: only `Editor.UI.Init/EditorInit.cpp` failed, pre-existing, so the editor did not link).
- **Checkpoint (feat/cxx-modules 3f3e761d, 2026-11-19; std + header-only vendors + Asserts + Common + Vulkan)**: `frontend_s=1340.6 scan_s=202.2 wall_s=274 tus=1379`. Same setup as the baseline: clean `Heliogrim-Editor`, `-ftime-trace`, sccache off, `-j 7`, `-k 0`, and the same two pre-existing errors. Stopwatch 294 s, including the clean and trace summing.
    - Frontend is **-40.4 %**, so the 15 % checkpoint passes.
    - Frontend plus scan-deps is -31.4 %. Wall time is -26.5 % (373 s to 274 s).
    - The script's own `wall_s` printed 373: `.ninja_log` still held the baseline build's entries. 274 s is the span of the latest entry per output.
    - Verdict: continue.
- Wave 1 (Asserts alone) is expected to be roughly neutral or slightly slower overall (scanning cost on every TU, small gain); the first real gain is wave 2 (Common).
- **Decided, checkpoint**: after wave 2 + Vulkan, total frontend time of a clean `Heliogrim-Editor` Debug build must be at least **15 % lower** than the pre-wave-1 baseline. Below that, stop and rethink before further waves.

## 10. Risks

- Import-then-include is a hard error with style A; any missed include in the sweep shows up as a redefinition error far from its cause.
- Exporting internal-linkage names (non-inline namespace `constexpr` such as the limits in `Types.hpp` and `Math/__const.hpp`, anonymous namespaces in `Discard.hpp`, `Hash/Fnv-1a.hpp`, `Concurrent/SharedMemoryReference.hpp`, `Managed/AtomicRefCountedIntrusive.hpp`) compiled on the spike, but importers using them was not tested; they may need `inline` or a named namespace.
- BMIs are large (40-76 MB) and every importer reads them; disk and sccache behaviour on full builds is unmeasured.
- clangd / CLion support for module builds is uneven; editor tooling may degrade on converted bundles. **Decided**: accepted for phase 1; it is temporary until bundles are rebuilt in phase 2. No tooling gate.
- Scanning every TU adds about 0.3 s each.
