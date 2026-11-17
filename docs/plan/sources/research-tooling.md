# Research: shader IR, hot reload, build, plugins, crash handling

**Status**: <span class="hg-status summary">sources</span>. Collected 2026-11-07 by a research agent for the battle plan. Claims are marked verified or unverified; nothing here is a decision.

**Method note (updated 2026-11-07)**: A second pass opened or searched the primary pages for most remaining sources; results are in "Verification pass (2026-11-07)" at the end. Inline `unverified` markers in sections 1-7 below are the first-pass state; the verification section supersedes them. Papers were checked at abstract/landing level only (ACM DL returned 403 to the fetcher, so bibliographic data came from search results quoting ACM DL / IEEE pages). First-pass note: only pages actually opened that session were `verified` (11 fetches: Slang user-guide TOC, Crashpad design, LLVM ORCv2, Vulkan GPL proposal, Unreal plugins, Live++ docs (first 100k chars), MiniDumpWriteDump, Git LFS spec, Godot export; one Godot GDExtension page and one Vulkan URL variant were attempted, GDExtension returned content only as noted below). Everything else is `unverified` recall from training knowledge and must be opened before being cited. Papers were not opened.

---

## 1. Shader languages and IRs

- Slang: generics + interfaces with associated types, generic value params, extensions adding conformances, variadic generics. `verified` (user-guide TOC, https://shader-slang.org/slang/user-guide/).
- Slang modules with access control, plus "link-time specialization" (link-time constants/types) and precompiled modules via API. `verified` (TOC only, no mechanism details).
- Slang `fwd_diff` / `bwd_diff` automatic differentiation with differentiable type system, usable with generics. `verified` (TOC).
- Slang `DescriptorHandle` for bindless access; specialization constants documented per target (SPIR-V, Metal, WGSL, GLSL). `verified` (TOC).
- Slang design rationale: interfaces/generics + "parameter blocks" to match shader parameter frequency to descriptor sets, shader components for permutation avoidance. `unverified` (He et al. SIGGRAPH 2018).
- SPIR-V: binary SSA module, capability/extension declared up front, decorations, structured control flow with merge instructions; SPIRV-Tools provides validator, optimizer (inlining, DCE, SROA, CCP, spec-constant folding, legalization for HLSL), and linker. `unverified`.
- SPIR-V linking (`spirv-link`, LinkageAttributes Import/Export) is the basis for separate compilation of modules. `unverified`.
- DXC: HLSL 202x templates (C++-like) and SPIR-V backend for Vulkan; `-spirv` path maintained by Microsoft/Google. `unverified`.
- WGSL: deliberately restricted, uniformity analysis is a normative spec feature (diagnoses derivatives/barriers in non-uniform control flow). `unverified`.
- MLIR: SPIR-V dialect exists upstream in LLVM; dialect-based progressive lowering. `unverified`. MLIR paper: Lattner et al., "MLIR: Scaling Compiler Infrastructure for Domain Specific Computation", CGO 2021. `unverified`.
- Halide: algorithm/schedule separation (Ragan-Kelley et al., PLDI 2013). Relevant as a model for keeping "what" apart from "how" (tiling, vectorize) in a shader IR. `unverified`.
- Rust GPU / rust-gpu: Rust to SPIR-V via rustc codegen backend; traits as the generics mechanism. `unverified`.

**Key sources**
- He, Y., Fatahalian, K., Foley, T. "Slang: language mechanisms for extensible real-time shading systems", ACM TOG (SIGGRAPH) 2018. `unverified` (not opened).
- Slang User Guide, Shader-Slang / Khronos project, https://shader-slang.org/slang/user-guide/. `verified` (TOC).
- SPIR-V Specification, Khronos, https://registry.khronos.org/SPIR-V/. `unverified`.
- SPIRV-Tools, Khronos, https://github.com/KhronosGroup/SPIRV-Tools. `unverified`.
- WGSL spec, W3C GPU for the Web WG, https://www.w3.org/TR/WGSL/. `unverified`.

**Applicability to Heliogrim**
- Slang is the closest prior art for ASL semantics (interfaces, modules, link-time specialization); cheaper to study its model than to re-derive one.
- SPIR-V direct emission later: keep ASL IR SSA-structured with structured control flow so GLSL and SPIR-V back ends share one lowering.
- Uniformity analysis belongs in IR passes (WGSL treats it as a language rule), needed before mesh/compute barrier correctness checks.
- Link-time specialization maps to the existing Engine.Accel.Compile effect/profile split.
- Considering Slang as backend/oracle instead of own emitter is a build-vs-adopt question; not evaluated here.

**Open risks / measure**
- Open the Slang paper and the link-time specialization chapter before relying on any claim above.
- Measure emitted GLSL vs. SPIR-V pass-through compile time and SPIR-V Tools optimizer gain on real engine shaders.
- Raytracing/mesh stage coverage in the IR is untested.

---

## 2. Automated optimization / JIT

- Vulkan `VK_EXT_graphics_pipeline_library`: four library parts (vertex input interface, pre-rasterization shaders, fragment shader, fragment output interface), linked via `VkPipelineLibraryCreateInfoKHR`. `verified` (https://docs.vulkan.org/features/latest/features/proposals/VK_EXT_graphics_pipeline_library.html, fetched earlier at a working URL variant).
- Fast linking is roughly cost of recording a command (`graphicsPipelineLibraryFastLinking`), but fast-linked pipelines can be much slower at runtime ("as bad as 50% penalty in the general case"). `verified`.
- Recommended pattern: compile libraries early, fast-link, optimize with `LINK_TIME_OPTIMIZATION_BIT` on a worker thread, swap in. `verified`.
- Specialization constants must be supplied with the shader stage, not at link time. `verified`.
- Permutation strategy (UE shader permutation talks, Slang shader components): reduce count via static analysis of used permutations, cooking only referenced ones, and runtime specialization constants for cheap switches. `unverified`.
- LLVM ORCv2: LLJIT / LLLazyJIT, JITDylib symbol tables, COFF linking, removable code via ResourceTracker. `verified` (https://llvm.org/docs/ORCv2.html; license not stated on that page).
- LLVM is Apache-2.0 with LLVM exceptions. `unverified`. Binary size for an embedded LLVM JIT is tens of MB (unverified, no number sourced).
- asmjit (zlib license) is an x86/ARM assembler-level JIT, small footprint; Cranelift (Apache-2.0) is Rust-only, awkward from C++. `unverified`.

**Key sources**
- Khronos, "VK_EXT_graphics_pipeline_library" proposal, Vulkan docs, 2022+. `verified`.
- LLVM Project, "ORCv2", llvm.org docs. `verified`.
- Epic Games, shader permutation material (GDC/Unreal Fest talks). `unverified`, not located.

**Applicability to Heliogrim**
- GPL maps naturally onto the effect/stage-derivate split; only worthwhile if pipeline hitches are measured.
- Specialization constants are a per-stage choice; plan the ASL IR so spec-constant uses are explicit and foldable.
- CPU JIT is probably not needed: hot reload (section 3) covers the iteration case. Defer LLVM unless scripting/ASL-on-CPU is wanted.

**Open risks / measure**
- Driver support/FastLinking flags across target GPUs.
- Pipeline-cache hit rate and first-use stall times on a cold cache.
- Real permutation counts from current material/effect system.

---

## 3. Hot module reload for C++

- Live++: Broker + Agent + Bridge; recompiles changed TUs using compiler command lines recovered from PDB, links a patch DLL, loads into live process; swaps code atomically at instruction level. `verified` (https://liveplusplus.tech/docs/documentation.html, Molecular Matters).
- Requirements: `/Z7` or `/Zi`, `/Gm-`, `/FUNCTIONPADMIN`, `/OPT:NOREF /OPT:NOICF`, `/DEBUG:FULL`; clang needs `-fms-hotpatch -ffunction-sections -gcodeview -mno-constructor-aliases`; LTCG/LTO/WPO unsupported. `verified`. Directly relevant: engine builds with clang-cl.
- Structural changes (layout, vtable) are not migrated; user must serialize/destroy/recreate in prepatch/postpatch hooks; stack objects cannot be migrated. `verified`.
- Synchronized agent applies patches at a frame boundary. `verified`.
- Executing functions on the stack keep old code until re-entered. `verified`.
- Live++ is commercial. Licensing terms `unverified`.
- cr.h (Fungos): single-header DLL swap with state in a user-defined struct preserved across reloads; plugin must keep state in host-provided memory. `unverified`.
- RuntimeCompiledC++ (Jackson): compiles source at runtime into a DLL, uses object constructors/serialization (`IObject`) to migrate state. `unverified`.
- Unreal Live Coding: Live++ integration. `unverified` (docs not opened).
- Dynamic software updating: Ksplice (Arnold & Kaashoek, EuroSys 2009), Kitsune (Hayden et al., OOPSLA 2012) use state-transformation functions at update points. `unverified`, not opened.
- State survival needs: stable ABI at module boundary, allocation from engine-owned (not module-owned) heap, no raw vtable pointers/function pointers held across unload, reflection/serialization of component data for migrate-by-serialize.

**Key sources**
- Molecular Matters, Live++ documentation, https://liveplusplus.tech/docs/documentation.html. `verified` (first ~100k of 116k chars).
- Hayden et al., "Kitsune: efficient, general-purpose dynamic software updating for C", OOPSLA 2012. `unverified`.
- Arnold, Kaashoek, "Ksplice: automatic rebootless kernel updates", EuroSys 2009. `unverified`.
- cr.h, https://github.com/fungos/cr; RuntimeCompiledC++, https://github.com/RuntimeCompiledCPlusPlus/RuntimeCompiledCPlusPlus. `unverified`.

**Applicability to Heliogrim**
- Two tiers: function-patching (Live++-style) for inner loop; DLL swap with reflection-driven serialize/restore for structural changes. They need different engine support.
- Check current CMake flags against Live++ requirements (/OPT:NOICF, function padding); unity builds were closed already, which is a precondition Live++ likes.
- Engine reflection and actor/component serialization double as the migration format; hot reload becomes a consumer of existing serialization.
- Allocator ownership: game DLL must not own memory outliving the DLL.

**Open risks / measure**
- Live++ license cost/terms; whether the editor can run with Live++ and vendor libs lacking PDBs.
- Reload latency on real game module; correctness with `Rc`/atomic intrusive types holding vtables of unloaded code.
- Thread-local storage and global initializers across reload (listed as Live++ limitations; detail not read).

---

## 4. Game-project build and deployment

- Godot: engine ships as export templates (prebuilt binaries); a project is data plus `export_presets.cfg`; export produces executable+data or PCK/ZIP only; CLI `--export-release`. `verified` (https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html).
- Godot: resource selection modes, dot-folders excluded, credentials kept in a separate non-VCS file. `verified`.
- Unreal: UBT/UAT, `.uproject` plus Target.cs; cook, stage, package, pak. `unverified` (only the plugin page was opened).
- Unity: Player build pipeline, Addressables/AssetBundles, IL2CPP. `unverified`.
- O3DE: project via `project.json`, engine registered by `engine.json`, gems enabled per project, Asset Processor does incremental asset building. `unverified`.
- CMake SDK export: `install(EXPORT)`, `find_package` config files, relocatable packages. `unverified` (CMake docs not opened).
- Reproducible builds: `/Brepro` for MSVC/lld-link, `SOURCE_DATE_EPOCH`-style fixed timestamps. `unverified`.
- Windows code signing: Authenticode via signtool, Azure Trusted Signing / EV certificates. `unverified`.

**Key sources**
- Godot Docs, "Exporting projects", Godot Engine. `verified`.
- Epic Games, UnrealBuildTool / Unreal Automation Tool docs. `unverified`, not opened.
- O3DE documentation, Linux Foundation. `unverified`, not opened.

**Applicability to Heliogrim**
- Godot's split (engine = template, project = data+preset) is the simplest model: a prebuilt engine runtime plus project package.
- With hot reload, the game code lives in a module built by CMake against an exported engine SDK; shipping builds link it statically or ship as DLL.
- A cooked-asset step with content-hash caching gives incremental cooking; the asset-location work from the 2026-10-28 checkpoint is the prerequisite.
- Defer signing/reproducibility until a distributable exists; note `/Brepro` is low-cost.

**Open risks / measure**
- Engine SDK export with ~60 bundles: CMake target export hygiene (vendored dependencies, include dirs).
- Cook time for the current asset set and invalidation granularity.
- Unity/Unreal/O3DE claims above must be opened before citing.

---

## 5. Plugin systems

- Unreal `.uplugin`: JSON descriptor, only `FileVersion` required, `Modules` entries with Name/Type/LoadingPhase, `CanContainContent`, dependencies on other plugins that may only point at same or higher level. `verified` (https://dev.epicgames.com/documentation/en-us/unreal-engine/plugins-in-unreal-engine).
- Unreal module types: Runtime, RuntimeNoCommandlet, Developer, Editor, EditorNoCommandlet, Program; Developer never loads in shipping. `verified`.
- Unreal loading phase values beyond Default were not shown on that page. `verified` gap (PreDefault, PostEngineInit etc. are `unverified` recall).
- Crashpad is a good example of a C++ client library with stable per-module data struct (`CrashpadInfo` with magic/size/version). `verified` (see section 6); a pattern for versioned structs across modules.
- Godot GDExtension: C ABI header, extensions loaded as shared libraries, hot reload support in editor. `unverified` (fetch of the GDExtension page was not used for claims).
- O3DE gems: modules with descriptors, enabled per project. `unverified`.
- VS Code: out-of-process extension host, manifest `package.json` with activation events. JetBrains: `plugin.xml` extension points. `unverified`.
- ABI strategies: C ABI boundary with function-pointer tables, version + size at table head, COM-like interface IDs with QueryInterface. `unverified` as sources, widely used practice.

**Key sources**
- Epic Games, "Plugins in Unreal Engine". `verified`.
- Godot Docs, GDExtension. `unverified`.
- Microsoft, COM / Component Object Model docs. `unverified`.

**Applicability to Heliogrim**
- A descriptor with module type (runtime/editor/developer) and loading phase maps cleanly to the existing Editor.* vs Engine.* bundle split.
- Plugins crossing a DLL boundary need a versioned C-ABI vtable; `Rc`/`Arci` handle types would need a stable layout or must stay inside a module.
- Editor-only plugins can be stricter (same compiler, same CRT) than shipping runtime plugins.

**Open risks / measure**
- Decide whether plugins must be built with the same toolchain (simple) or support third-party binaries (needs C ABI).
- Verify Unreal loading phase list and GDExtension compatibility rules before copying.

---

## 6. Crash handling and diagnostics

- Crashpad: out-of-process handler, minimal code in crashed process; handler snapshots modules/threads/memory and writes minidump to a database, optionally uploads. `verified` (https://chromium.googlesource.com/crashpad/crashpad/+/HEAD/doc/overview_design.md).
- Windows client registration via named pipe or handle inheritance; client UnhandledExceptionFilter signals the handler; stack-smashed crashes, in-thread handled exceptions and summary terminations may yield no report. `verified`.
- Database holds client ID, upload-enabled bit, pending dumps; bounded by count and size; upload is Breakpad-protocol MIME multipart, throttled to one per hour, failed uploads not retried. `verified`.
- Crashpad supports annotations (crash keys), custom minidump streams, address-range capture. `verified`. Dumps may hold sensitive data; embedder must obtain and honor consent. `verified`.
- MiniDumpWriteDump: Microsoft says call from a separate process if possible (loader deadlock risk), else a dedicated thread; calling-thread stack may be invalid unless exception info is passed; DbgHelp is single-threaded. `verified` (https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/nf-minidumpapiset-minidumpwritedump).
- Sentry Native (wraps Crashpad/Breakpad/inproc backends), symbol upload, grouping by stack fingerprint. `unverified`.
- WER: LocalDumps registry keys for per-app dump collection. `unverified`.
- Deterministic crash IDs: hash of normalized top frames (module+function, excluding addresses). `unverified`; design suggestion only.
- Diagnostics with fix info: Rust compiler structured diagnostics (spans, labels, suggestions with applicability), clang `FixItHint`, Elm friendly errors, LSP `Diagnostic` + `CodeAction` with `WorkspaceEdit`. `unverified` (specs not opened).

**Key sources**
- Crashpad Overview Design, Chromium project (Google). `verified`.
- "MiniDumpWriteDump function", Microsoft Learn. `verified`.
- Language Server Protocol spec, Microsoft, https://microsoft.github.io/language-server-protocol/. `unverified`.
- rustc dev guide, "Diagnostics". `unverified`.

**Applicability to Heliogrim**
- Use Crashpad-style out-of-process handler; do not call MiniDumpWriteDump inside the crashing process except as fallback.
- Hot reload interacts: dumps must record loaded patch/DLL versions and PDB identity so symbolization works.
- For ASL compiler diagnostics, adopt span + label + suggested-edit structure now; it costs little and later maps to LSP CodeAction for editor and shader tooling.
- Upload/consent policy is a product decision; default off.

**Open risks / measure**
- Crashpad as vendored dependency size and build integration with the existing CMake vendor layout.
- Behavior of handler with GPU-driver crashes and TDR (not researched).
- Symbol server storage cost.

---

## 7. VCS integration in editors

- Git LFS: tracked files replaced by text pointers (`version`, `oid sha256:<hex>`, `size`), under 1024 bytes, canonical encoding; objects stored by SHA-256 in sharded local path; clean/smudge filters; upload on pre-push; `.gitattributes` selects files. `verified` (https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md).
- Git LFS locking API: not covered by the fetched page (lives in `docs/api/locking.md`). `unverified`.
- Unreal source control providers (Perforce, Git, Plastic/Unity Version Control) via an editor provider interface; check-out/lock on edit for binary uasset. `unverified`.
- Binary asset diff/merge: text manifest + content-addressed blobs is the design the LFS pointer format already demonstrates. `verified` (as format; the editor-diff idea is a design suggestion).
- Git partial clone (`--filter=blob:none`) and sparse checkout for large repos. `unverified`, Git docs not opened.

**Key sources**
- Git LFS specification, git-lfs project, GitHub. `verified`.
- Git documentation: partial-clone, sparse-checkout. `unverified`.
- Perforce Helix Core docs, Unreal Source Control docs. `unverified`.

**Applicability to Heliogrim**
- If assets are already content-addressed in the asset-location work, an LFS-compatible pointer is nearly free and avoids a custom store.
- Editor needs a provider interface with: status, checkout/lock, revert, submit; Git+LFS first.
- Keep serialized asset metadata as text (diffable) and payloads as blobs.

**Open risks / measure**
- LFS lock semantics and hosting limits (not read).
- Repo size of `assets/**` and clone time; whether sparse/partial clone is needed.

---

## Verification pass (2026-11-07)

Status key: V-full = page opened, relevant text read; V-abs = abstract/landing page or search-quoted official page; U = still unverified.

1. Slang paper: V-abs. He, Fatahalian, Foley (Yong He CMU, Kayvon Fatahalian Stanford, Tim Foley NVIDIA), ACM TOG 37(4), Art. 141, pp. 1-13, SIGGRAPH 2018, DOI 10.1145/3197517.3201380. Abstract: generics with interface constraints, associated types, interface/structure extensions added to HLSL (Slang); Falcor rearchitected, simpler and faster than HLSL original. Source: search results quoting https://dl.acm.org/doi/10.1145/3197517.3201380 (direct fetch 403). Slide-listed features (secondary): ParameterBlock, global generic parameters, module import. Claim in section 1 about "parameter blocks" and "shader components" is only partly supported: the paper abstract does not name them; treat "shader components" as U.
   Slang user guide, link-time specialization: V-full. https://shader-slang.org/slang/user-guide/link-time-specialization.html. `extern static const` / `export static const` for link-time constants; `extern struct X : IFoo;` / `export struct X : IFoo = Impl;` for types (name and conformance must match); defaults allowed; precompiled `.slang-module`, `IModule::serialize`, `isBinaryModuleUpToDate`; three-step model precompile, link, generate code.
2. Live++ pricing: V-full. https://liveplusplus.tech/pricing.html. Trial 30 days free; Windows Individual EUR 11.90/month or 119/year (private funds); Business EUR 19.90/month or 199/year; per seat, excl. VAT; consoles via sales; Studio/Enterprise on request. (Prices are as of fetch; recheck before budgeting.)
   Live++ limitations: V-full. https://liveplusplus.tech/docs/documentation.html (after char 100000). New thread-local variables unsupported (existing TLS works); with Clang, new globals/statics needing dynamic initializers unsupported (initializer not run in patches); mutable globals keep original instance; const data is reintroduced; debuggers cannot show globals after reload without the context operator; stack functions need re-entry. Section 3 risk "detail not read" is now resolved.
3. Unreal plugin loading phases: V-abs. https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Projects/ELoadingPhase__Type (via search): EarliestPossible, PostConfigInit, PostSplashScreen, PreEarlyLoadingScreen, PreLoadingScreen, PreDefault, Default, PostDefault, PostEngineInit, None, Max. The plugins page itself lists only module Type values and shows `Default` (confirmed). Unreal Live Coding: V-full. https://dev.epicgames.com/documentation/en-us/unreal-engine/using-live-coding-to-recompile-unreal-engine-applications-at-runtime. Live++ integration, Ctrl+Alt+F11, not for consoles/mobile, object reinstancing for structural changes, constructor default changes in .cpp do not propagate.
4. UE 5.0 release notes: V-abs (search-quoted, direct fetch returned empty ToC). https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5.0-release-notes : "Removed underlying framework and support for the Blueprint nativization feature". Engine macro text: "Blueprint Nativization has been removed as a supported feature." UE 4.26 deprecation note: U (a secondary source said deprecated in 4.27; not confirmed from a primary page, do not cite a version).
5. Godot GDExtension: V-abs (search summary of docs, direct fetch 404 on one URL). https://docs.godotengine.org/en/latest/engine_details/engine_api/gdextension/what_is_gdextension.html : C API (`gdextension_interface.h`), `.gdextension` file, `reloadable` flag for editor auto-reload, experimental label, earlier-targeted extensions work on later minor versions not vice versa. Hot reload arrived in 4.2 dev (not 4.0). VisualScript removal: V-abs https://godotengine.org/article/godot-4-will-discontinue-visual-scripting/ (removed from 4.0; about 0.5% of users used it as primary tool per survey; moved to godot-visual-script repo).
6. Kitsune: V-abs. Hayden, Smith, Denchev, Hicks, Foster, OOPSLA 2012, pp. 249-264, DOI 10.1145/2384616.2384635; whole-program update, state-transformation specs. Correction: the earlier text implies "update points" and state-transformation functions; true, but Kitsune generates transformers from simple specs. Ksplice: V-abs. Arnold, Kaashoek, EuroSys 2009, pp. 187-198, DOI 10.1145/1519065.1519085; operates at object-code layer. Correction: Ksplice does not use programmer-written state-transformation functions in the common case (it needs no new code unless data semantics change), so "both use state-transformation functions at update points" in section 3 is wrong for Ksplice.
7. cr.h: V-full. https://github.com/fungos/cr (Danny Grein, MIT). State via `CR_STATE` section tagging, not a user-defined struct; also `userdata` pointer; rollback on crash; host and plugin must share dynamic CRT; designed for C, riskier with C++. Correction to section 3 wording. RuntimeCompiledC++: V-full. https://github.com/RuntimeCompiledCPlusPlus/RuntimeCompiledCPlusPlus : zlib license, in-memory serialization, Windows MSVC / Linux / macOS, CMake build, dev-time use. `IObject` naming is U.
8. LLVM license: V-full. https://llvm.org/LICENSE.txt : Apache-2.0 with LLVM Exceptions (plus legacy NCSA license). asmjit: V-full. https://github.com/asmjit/asmjit : zlib, X86/X64 and AArch64, Petr Kobalicek. MLIR SPIR-V dialect: V-abs. https://mlir.llvm.org/docs/Dialects/SPIR-V/ : IR for transformations first, same semantic level as spec, structured control flow via regions. MLIR paper: V-abs. Lattner et al., CGO 2021 (IEEE/ACM), pp. 2-14, DOI 10.1109/CGO51591.2021.9370308. Cranelift claim and LLVM binary size: U.
9. UBT: V-abs. https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-build-tool-in-unreal-engine : modules with .build.cs, DLL by default, monolithic option; Target.cs details live on a separate page, not read. UAT: V-abs. https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-automation-tool-for-unreal-engine : automation host, BuildGraph; BuildCookRun/cook/stage/package not on that page, so U. O3DE: V-abs via search of https://docs.o3de.org/docs/user-guide/project-config/ : project.json (project_name, engine, engine_api_dependencies, external_subdirectories), engine.json (engine_name, version, api_versions, gem_names), registry in o3de_manifest.json; "Asset Processor incremental" U. CMake install(EXPORT): V-full. https://cmake.org/cmake/help/latest/command/install.html : generates import file; not a package config itself (write `<pkg>-config.cmake` that includes it); CMake 4.3 adds install(PACKAGE_INFO) emitting .cps. `/Brepro`: CORRECTION, no official learn.microsoft.com page found; flag is undocumented (Developer Community ticket "Document /Brepro flag" cited by third parties); behavior (content hash instead of timestamp, also lib.exe) is from community sources only, so V-abs at best; pair with `/PDBALTPATH`, `/pathmap`. Trusted Signing: CORRECTION, now named Artifact Signing, https://learn.microsoft.com/en-us/azure/artifact-signing/overview (V-full): managed signing, HSM-backed, Basic and Premium SKUs, public/private trust.
10. Sentry Native backends: V-full. https://docs.sentry.io/platforms/native/configuration/backends/ : crashpad (default Win/macOS/Linux, out-of-process), native (out-of-process, since 0.13.2), breakpad and inproc (in-process; report uploaded next launch), none. Correction: backends are crashpad/native/breakpad/inproc, not just three. WER LocalDumps: V-full. https://learn.microsoft.com/en-us/windows/win32/wer/collecting-user-mode-dumps : HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps, DumpFolder, DumpCount (10), DumpType (0 custom, 1 mini, 2 full), per-app subkeys, needs admin, off by default.
11. LSP 3.17: V-full for Diagnostic (range, severity, code, codeDescription, source, message, tags, relatedInformation, data) and CodeAction (title, kind, diagnostics, isPreferred, edit WorkspaceEdit, command; must set edit and/or command) at https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/. rustc dev guide: V-full. https://rustc-dev-guide.rust-lang.org/diagnostics.html : primary/secondary labeled spans, `span_suggestion`, Applicability MachineApplicable / HasPlaceholders / MaybeIncorrect / Unspecified. clang InternalsManual: V-full (first 100k chars). https://clang.llvm.org/docs/InternalsManual.html : tblgen diagnostic IDs, severities NOTE/REMARK/WARNING/EXTENSION/EXTWARN/ERROR, FixItHint insertion/removal/replacement.
12. Git LFS locking: V-full. https://github.com/git-lfs/git-lfs/blob/main/docs/api/locking.md : POST/GET /locks, /locks/verify, /locks/:id/unlock; 409 on conflict; single-branch first version. Git partial clone: V-full. https://git-scm.com/docs/partial-clone (filter, promisor remotes, `--filter=blob:none`). Sparse-checkout: V-full. https://git-scm.com/docs/git-sparse-checkout (cone mode default, non-cone deprecated, marked experimental). Unreal Source Control: V-abs. https://dev.epicgames.com/documentation/en-us/unreal-engine/source-control-in-unreal-engine : CORRECTION, page says Perforce and SVN supported by default; Git and Plastic are not listed there, so that part of section 7 stays U. Check-out locks asset.
13. SPIRV-Tools: V-full. https://github.com/KhronosGroup/SPIRV-Tools : 67 optimizer transforms incl. inlining, DCE, CCP, spec-constant folding, loop passes, `-O`/`-Os`; validator is one-sided; spirv-link still in development (library vs executable); Apache-2.0. Correction: SROA and "legalization for HLSL" were not seen in the README pass list excerpt; U. SPIR-V registry: V-abs. https://registry.khronos.org/SPIR-V/ : unified spec, 1.6 latest with revisions, GLSL.std.450 ext set. WGSL: V-abs. https://www.w3.org/TR/WGSL/ : section 15.2 Uniformity; `derivative_uniformity` and `subgroup_uniformity` diagnostics default to error; W3C Candidate Recommendation Draft.

Still unverified: Slang "shader components", DXC HLSL 202x/-spirv, spirv-link LinkageAttributes detail, Halide, rust-gpu, UE 4.26 deprecation note, UE BuildCookRun, Git/Plastic in Unreal, O3DE Asset Processor, Cranelift, LLVM binary size, Unity, VS Code/JetBrains, COM, deterministic crash ID idea (design suggestion), Epic permutation talks.

---

## Source status summary
- Second pass (2026-11-07): see "Verification pass" above; most items in the list below are now V-full or V-abs. Corrections made: Ksplice (no state-transformation functions), cr.h (CR_STATE sections), Trusted Signing (renamed Artifact Signing), /Brepro (undocumented), Unreal source control (Perforce/SVN only listed), Sentry backends (four plus none).
- First pass, opened and relied on: Slang user guide TOC, Crashpad overview design, LLVM ORCv2, Vulkan GPL proposal, Unreal plugins page, Live++ docs, MiniDumpWriteDump, Git LFS spec, Godot export docs.
- Named but not opened in the first pass (see verification pass for current status; remaining unverified items are listed there): Slang SIGGRAPH 2018, SPIR-V spec, SPIRV-Tools, WGSL, MLIR CGO 2021, Halide PLDI 2013, Kitsune OOPSLA 2012, Ksplice EuroSys 2009, cr.h, RuntimeCompiledC++, Sentry Native, LSP spec, Unreal UBT/UAT, O3DE gems, GDExtension.
