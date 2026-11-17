# Accel Lang: Shader Language, IR, Pipeline Kinds, Variant Cache, JIT

**Systems**: S11, S12, S13, S60 (issues #78, #82) · **Track** B, E · **Milestone** M2, M6
**Status**: <span class="hg-status summary">plan</span>. Research from [tooling](../sources/research-tooling.md) sections 1 and 2 (Slang user guide TOC, Vulkan graphics pipeline library proposal and LLVM ORCv2 verified) and [rendering](../sources/research-rendering.md) cross-cutting prerequisites.

## Target

ASL is the only shader source in the engine. Its IR compiles directly to SPIR-V for graphics, compute, mesh and task, ray-tracing and (when the Vulkan extension lands) work-graph stages. Interface contracts between shaders and passes are checked without a GPU. Variants are specialised and cached automatically. A measured gate decides whether runtime specialisation on the CPU (JIT) is worth building.

## Current state (checked 2026-11-07)

- `Engine.Accel.Lang` (56 files, 7.3k lines): lexer, parser, IR (module, layout, lower, merge, resolve, slice, variant, analysis, compact, condition, contract, interface, builtin), `Dialect.hpp`, GLSL emitter gated by glslang, diagnostics. Milestone 2 on `feat/accel-ir-coverage` moved every engine shader to `.asl` (brdf, depth, post-processing, shadow, skybox, ui, visualize, shared libraries) with all graphics stages plus compute, immutable-by-default references and SIMT loop rules.
- Open: #82 region borrows for the micropolygon scratchpad; #78 finish the migration and support mesh, tessellation, compute and ray-tracing stages end to end.
- `Engine.Accel.Compile`, `.Pipeline`, `.Pass`, `.Command`, `.Storage`, `.Loader`, `.Effect`: graphics pipelines only; effect profiles and specifications; `HashedState` keys are address and name based (variant cache keys must be content based).
- Requirement back-propagation from materials into pass enablement is designed in a brainstorm, not built.

## Research summary

- Slang (user guide incl. the link-time specialisation chapter verified; paper abstract verified: He, Fatahalian, Foley, ACM TOG 37(4) 2018, DOI 10.1145/3197517.3201380): generics and interfaces with associated types, modules with access control, link-time specialisation with precompiled modules, automatic differentiation, `DescriptorHandle` for bindless, specialisation constants per target. The paper's "shader components" mechanism remains unverified.
- SPIR-V: SSA with structured control flow and merge instructions; SPIRV-Tools provides validator, optimiser (inlining, DCE, SROA, constant propagation, spec-constant folding) and linker with import/export linkage. Unverified in this pass, well established.
- WGSL makes uniformity analysis a normative language rule; MLIR has an upstream SPIR-V dialect. Unverified.
- Graphics pipeline library (verified): four library parts, fast linking is cheap but fast-linked pipelines can run up to 50% slower; recommended pattern is fast-link then optimise on a worker and swap; specialisation constants belong to the shader stage, not link time.
- LLVM ORCv2 (verified): lazy JIT, JITDylibs, COFF linking, removable code. Binary size and licence unverified; CPU JIT is likely unnecessary while hot reload (S48) covers iteration.
- Rendering prerequisites for the IR (rendering report): 64-bit integers and atomics, subgroup operations, runtime descriptor arrays with `nonuniformEXT`, indirect dispatch, mesh and task stages with per-primitive outputs, ray query (optional), structured buffers, image atomics.

## Guidance

### S11 Direct SPIR-V backend and optimiser

- Keep the IR SSA-structured with explicit merge blocks so the GLSL emitter and the SPIR-V emitter share one lowering; the GLSL path stays as the glslang-gated oracle in tests until the SPIR-V path passes the same golden set, then becomes test-only.
- Emit SPIR-V with capabilities declared from an IR feature analysis; validate with `spirv-val` in the test harness; run `spirv-opt` as the first optimiser and measure which passes matter before writing in-house passes.
- Passes to own: uniformity analysis (barrier and derivative correctness in mesh and compute), region borrow checking (#82), spec-constant folding points, interface contract checking against pass declarations (the "which side wins" question: the module interface is the contract; a pass that disagrees is a diagnostic).
- Debug info: `OpLine` and names in Profile builds so RenderDoc shows ASL source.
- Study Slang's module and link-time specialisation model before extending ASL's `@when` blocks; decide explicitly whether Slang is an oracle only or could become a backend (build-versus-adopt, no decision here).

### S12 All pipeline kinds

- `Accel.Pipeline` gains compute, mesh and task, ray-tracing (shader binding table layout as an IR interface) and a placeholder for work graphs. The driver gets the matching pipeline creation and dispatch commands; the render graph (S14) learns compute and indirect nodes.
- First consumers in order: a compute pass (sky LUT, S21), the particle simulation (S24), a mesh-shader test (S18 prerequisite), a ray-query shadow (S19 optional tier).

### S13 Variant and pipeline cache

- Variant keys are content hashes of the merged module plus the specialisation values; `HashedState` is replaced for this purpose.
- Pipeline library parts cached on disk keyed by driver and device IDs; fast-link on first use, optimise on a Background fiber, swap. Adopt only after measuring first-use hitches on real scenes.
- Permutation control: materials declare features; back-propagation (S16) computes which permutations a scene needs; cook only those.

### S60 Automated optimisation and JIT

- Gate: a benchmark that shows a measurable win from runtime specialisation of a hot CPU path (candidates: animation blend evaluation, procedural generators, replication encoders). Without a win the system is closed with a record.
- If opened: ORCv2 with removable code, limited to generated code (visual scripts, S47), never hand-written engine code.

## Done when

- Every engine shader compiles ASL to SPIR-V, passes `spirv-val`, and renders identically to the glslang path in the GPU harness.
- A compute, a mesh and a ray-query pipeline each run a harness test; the render graph schedules an indirect dispatch.
- An ASL interface mismatch with a pass declaration is a diagnostic with both locations.
- A cold scene's pipelines are served from the disk cache on second run; first-run hitch time is recorded.

## Open decisions

- Slang as oracle, backend or neither.
- Whether to own an optimiser beyond `spirv-opt`.
- Ray-tracing and mesh shaders on the minimum-spec GPU (ties to S15).
