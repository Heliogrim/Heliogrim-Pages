# Work: Accel Lang, Pipeline Kinds, Variant Cache, JIT

**Systems** S11, S12, S13, S60 · **Issues** [#82](https://github.com/Heliogrim/Heliogrim-Engine/issues/82), [#92](https://github.com/Heliogrim/Heliogrim-Engine/issues/92), [#78](https://github.com/Heliogrim/Heliogrim-Engine/issues/78), [#93](https://github.com/Heliogrim/Heliogrim-Engine/issues/93), [#140](https://github.com/Heliogrim/Heliogrim-Engine/issues/140), [#148](https://github.com/Heliogrim/Heliogrim-Engine/issues/148), [#202](https://github.com/Heliogrim/Heliogrim-Engine/issues/202) · **Track** B, E · **Milestone** M2, M6
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Accel Lang](../topics/accel-lang.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Accel IR milestones 1 and 2 (engine branches `feat/accel-ir`, `feat/accel-ir-coverage`, session notes 2026-11-07) | All engine shaders in `.asl`; all graphics stages plus compute in the IR; glslang-gated GLSL emitter; immutable-by-default references; SIMT loop rules; `IrSpirvGateTest.AllAssetsAreAsl` | Milestone 2 on `master` (checked 2026-11-13: `588f84a7` to `0a443b8a`); tests that read shader assets were replaced by inline sources (`b8ecfc8f`), so `AllAssetsAreAsl` is gone; GPU render never verified |
| Region borrows spec and plan (#82, untracked `docs/superpowers/{specs,plans}/2026-11-07-ir-region-borrows*.md`) | Done: PR [#156](https://github.com/Heliogrim/Heliogrim-Engine/pull/156) merged into `feat/wip` 2026-11-08, on `master`; #82 closed | GLSL vs SPIR-V lowering of borrows left open on purpose; the spec still lives only in the engine checkout (W11.0 design page) |
| Issue #148 | Three ASL-to-GLSL name-collision gaps (`_hg_ref` hoisting, reserved names) | Bug on the GLSL path; irrelevant once SPIR-V is primary, must still be fixed while GLSL is the oracle |
| Accel IR brainstorm (memory, 2026-10) | Goals: compute and mesh stages, sparse and bindless resources, indirect dispatch for virtualised geometry | Matches S12 and S15 prerequisites |
| [Render graph v2 work](render-graph-gpu-driven.md) | Pass declarations read inputs and outputs from the ASL interface | The interface export format is owned here (W11.3) |

The engine-side specs are untracked; W11.0 recorded them on the site as the [Accel Lang design](../../architecture/accel-lang-design.md) (2026-11-13).

## Architecture

- **Bundles**: `Engine.Accel.Lang` gains `Ir/Spirv/*` (emitter, capability analysis, debug info) and `Ir/Pass/*` (uniformity, borrow check, interface check). `Engine.Accel.Compile` learns per-kind compilation; `Engine.Accel.Pipeline` gains compute, mesh and task, ray-tracing and work-graph pipeline types; `Engine.Driver.Vulkan` gains the matching creation and dispatch. New `Engine.Accel.Cache` (variant keys, pipeline library cache, async compile). `Engine.Jit` only if W60.1 opens it.
- **Layer**: L3 rendering; `Engine.Accel.Lang` has no GPU dependency and stays testable without a device.
- **Provides**: SPIR-V modules with a validated interface description per entry point; pipelines of every kind; content-keyed variant and pipeline cache.
- **Consumes**: `Diagnostic` (S05; ASL is the first migration), `Waitable` and Background lane (S02) for async compile, storage (S03) for the disk cache, GPU harness (S26) for goldens.

## Code design

| Type | Contract |
|---|---|
| `SpirvEmitter` | Consumes the same lowered IR as `GlslEmitter`; emits structured SPIR-V with merge blocks; declares capabilities from `FeatureAnalysis`; optional `OpLine` and names in Profile builds. Output passes `spirv-val` in tests. |
| `FeatureAnalysis` | IR walk producing the set `{ Int64, Int64Atomics, Subgroup*, RuntimeDescriptorArray, NonUniform, MeshShading, RayQuery, ImageAtomics }`; a feature not in the device's capability flags is a diagnostic at compile time, not a driver error. |
| `UniformityPass` | Marks values uniform or divergent; a barrier or derivative in divergent control flow is a diagnostic with both locations. |
| `BorrowPass` | Region borrows per #82's spec: per-root helper specialisation, overlap rule for `let` borrows. |
| `InterfaceDesc` | Exported per entry point: `{ stage, inputs, outputs, resources (set, binding, kind, access), push constants, spec constants, workgroup size }`. Serialised next to the module; the render graph (S14) and `InterfaceCheck` consume it. The module interface is the contract; a pass declaration that disagrees is a diagnostic. |
| `PipelineKind` | `Graphics, Compute, Mesh (task optional), RayTracing (SBT layout from the interface), WorkGraph (reserved)`; `Accel.Pipeline` has one class per kind and one `Driver.Vulkan` creation path per kind. |
| `VariantKey` | Content hash of the merged module plus specialisation values plus target profile; replaces address-based `HashedState` for cache purposes. |
| `PipelineCache` | Disk cache keyed by `(VariantKey, driver id, device id)`; pipeline library parts; fast-link on first use, optimise on a Background task, swap. Hitch time recorded as a counter (S04). |
| `JitGate` | Not a type; a benchmark target that must show a win before `Engine.Jit` exists. |

Placement: `Engine.Accel.Lang/Ir/Spirv/`, `Engine.Accel.Lang/Ir/Pass/`, `Engine.Accel.Lang/Ir/Interface/InterfaceDesc.hpp` (extends the existing `interface` IR part), `Engine.Accel.Pipeline/{Compute,Mesh,RayTracing}Pipeline.hpp`, `Engine.Accel.Cache/`. Tests: SPIR-V goldens against the glslang oracle per shader asset; pass tests on small IR fixtures; harness tests per pipeline kind.

## Work chunks

### W11.0 Land milestone 2 and record ASL state on the site · execute · done 2026-11-13 (#148 fix merged via PR [#183](https://github.com/Heliogrim/Heliogrim-Engine/pull/183) into `feat/wip`; design page written)

- **Goal**: milestone 2 has landed (Q11.1); fix #148 on the GLSL path, write `architecture/accel-lang-design.md` from the engine-side specs so the IR shape, rules and the region-borrow spec live on the site.
- **Done when**: branch merged (done: on `feat/wip` and `master`); #148 closed (fix `cf89c70b` on `fix/asl-reserved-names`, reviewed and squashed, off `feat/wip`: the parser rejects GLSL reserved words, `gl_`, `_hg_` and the region suffixes at module scope; 469 Lang and 45 Compile tests pass; closes on merge); the design page exists with the IR part list and the borrow rules (done: [Accel Lang design](../../architecture/accel-lang-design.md)).
- **Left**: push and PR into `feat/wip` (owner). The remaining name collisions (GLSL builtin functions, `<binding>_block`, a local `f__r<k>`, extension type names; design page section 6) are left to W11.2 on purpose, not patched on the GLSL path.
- **Questions**: Q11.1.

### W11.1 Region borrows (#82) · execute · done 2026-11-08 (PR #156, on `master`; #82 closed)

- **Goal**: run the existing five-task plan by subagent-driven development on `feat/accel-ir-regions`.
- **Result**: commits `1a047450` (range borrows and region parameters) to `b6473e3e` (region helpers specialised per root), merged as PR [#156](https://github.com/Heliogrim/Heliogrim-Engine/pull/156) into `feat/wip`, now on `master`.
- **Done when**: the micropolygon scratchpad layout compiles and the borrow tests pass; GLSL oracle unchanged for shaders without borrows.

### W11.2 Direct SPIR-V backend design · design · done 2026-11-16 (design and plan accepted by the owner)

- **Goal**: emitter structure, capability analysis, `spirv-val` and `spirv-opt` in tests, debug info, the verification protocol (owner, 2026-11-14: the GLSL emitter and backend are removed once SPIR-V lands, no parity suite; correctness comes from the GPU harness tests against pre-computed values, which do not depend on the backend; DXIL not now), the Slang question. The emitter must make name conflicts unrepresentable: identity by result id, user names only as debug info, no generated name in a user-visible namespace (closes the collisions in [design page section 6](../../architecture/accel-lang-design.md#6-open)).
- **Language core (2026-11-16)**: ASL states the semantics GLSL used to supply: evaluation order, short-circuit and lazy ternary, implicit conversions, integer division, shift and overflow rules, reference meaning of `&mut` (pointer versus copy, per storage class), `discard` as `OpTerminateInvocation`, reserved names shrunk to ASL keywords; the IR gets typed literals and an operator enum. Language additions beyond that are W11.5.
- **Inputs**: [SPIR-V backend references](../sources/research-spirv-backend.md) (licence check and source list, 2026-11-14), IR parts list, SPIRV-Tools, Slang user guide (module and link-time specialisation chapters).
- **Output**: section in `accel-lang-design.md`; plan.
- **Result**: [Accel Lang design section 7](../../architecture/accel-lang-design.md#7-spir-v-backend) (owner approved the design 2026-11-16; builder check answered: fixed capability profile, per-pipeline interface numbers, `rep` adapter kept until W14.2). Plan untracked in the engine checkout: `docs/superpowers/plans/2026-11-16-spirv-backend.md` (ten tasks: typed literals and operator enum, explicit conversions, writer and validation, reference lowering, three emitter tasks, pipeline switch, glslang removal, `spirv-opt` measurement).
- **Questions**: Q11.2, Q11.3 (decided, refined 2026-11-14).
- **Order (owner, 2026-11-14)**: diagnostics go through the engine `Diagnostic` type from W05.2 (`feat/diagnostics`). The design includes verification on the GPU harness, so W26.1 and W26.2 come first.

### W11.3 Implement SPIR-V emitter, feature analysis, interface export · execute · code done 2026-11-16 (engine PR [#203](https://github.com/Heliogrim/Heliogrim-Engine/pull/203) into `feat/wip`)

- **Done when**: every engine shader compiles to SPIR-V, passes `spirv-val`, passes the GPU harness tests (W26.2; the same tests ran on the GLSL path before); `InterfaceDesc` is emitted per entry point; glslang and the GLSL emitter are removed ([design 7.8, 7.9](../../architecture/accel-lang-design.md#79-verification)).
- **Result**: eleven signed commits on `feat/wip` `273094ef` (head `a944c909`), including a separate `fix(accel)` commit for `while` bodies that were never typechecked ([#202](https://github.com/Heliogrim/Heliogrim-Engine/issues/202)). All Done-when items met: the 21 engine shaders and every fixture compile and validate, Gpu.Test 33/33 unchanged, `InterfaceDesc` per entry, glslang out of build and vendor. Lang 603, Compile 47 pass. Every task and the whole branch reviewed (`/review-branch`, six lenses, one fix wave).
- **Numbers for the PR** (Debug, 21 shaders, sum of min-of-5): GLSL path 143 ms compose plus 8549 ms glslang; SPIR-V path 252 ms compose including emit plus 90 ms `spirv-val` (Dev tier only). Module size 22374 words (glslang) to 21082 words. `spirv-opt` on the Build-tier output: performance recipe 17151 to 10786 words in 953 ms, size recipe 10681 words in 753 ms, all still valid; the Build tier stays without `spirv-opt` until the owner picks a list (design 7.7).
- **Open for the owner**: run `spirv-val` in the shipped Build tier or not (security lens; design 7.4 says no); Dev-tier `OpName` still names generated `$` locals (design 7.5 says generated names stay unnamed); style residue in `Ir/Spirv/*` (access-label order, blank lines after guards, definition order); release validation and the editor build stay as in W26.2.

### W11.4 Uniformity and interface check passes · execute · after W11.3

- **Done when**: a barrier in divergent flow and an interface mismatch with a pass declaration are diagnostics with both locations.

### W11.5 ASL language extensions after GLSL · design · after W11.2 (core semantics); each item before its first consumer

- **Goal**: the language room that opens once GLSL no longer sits between the IR and SPIR-V (owner, 2026-11-16: its own work package). W11.2 settles only the semantics the emitter cannot do without (evaluation order, conversions, integer rules, reference meaning of `&mut`, `discard`, reserved names shrunk to ASL keywords). The items below add to that core. None of them changes it, so each one is designed and implemented just before its first consumer, not upfront.
- **Items**:

| Item | Language addition | SPIR-V basis | First consumer |
|---|---|---|---|
| B1 | `switch` | `OpSwitch` | none; on demand after W11.3 |
| B2 | Statements that end a block (`emit_tasks`), task payload declaration, per-primitive outputs, mesh output counts | `SPV_EXT_mesh_shader` | W12.3, W18.6 |
| B3 | Ray query object, usable by reference only | `SPV_KHR_ray_query` | W12.3, W19.4 |
| B4 | Ray payloads, hit attributes, callable data, `terminate_ray` and `ignore_intersection` as block-ending statements, the six ray-tracing stage kinds | `SPV_KHR_ray_tracing` | the ray-tracing pipeline execute chunk that W12.1 cuts |
| B5 | `nonuniform` marking on descriptor indices | `NonUniform` decoration, descriptor indexing | W15.1 (`BindlessSet`) |
| B6 | Subgroup operations, with a stated reconvergence rule | `GroupNonUniform*`, maximal reconvergence | W15.2 (culling); guess, the W15.1 design names the first real user |
| B7 | Workgroup memory reuse across phases (a non-goal of the region-borrow design, [section 4](../../architecture/accel-lang-design.md#4-region-borrows)) | `WorkgroupMemoryExplicitLayoutKHR` | W18.5 |
| B8 | Buffer device addresses (typed pointers into buffers) | `PhysicalStorageBuffer64` | W15.1, if its GPU tables use them |
| B9 | User generics, specialised per use like the region helpers | none; resolved in the IR | none; on demand |

- **Not here**: work graphs stay an enum value (Q12.1); revisit when an EXT or KHR extension exists (only `VK_AMDX_shader_enqueue` as of 2026-11).
- **Output**: one section per item in `accel-lang-design.md`, written when the item's consumer is next; the implementation goes into the consumer's execute chunk or a small execute chunk of its own.
- **Done when**: never as a whole; each item is closed when its consumer runs on it.

### W11.6 Value-range analysis (Deep tier) · design · after W11.3

- **Goal** (owner, 2026-11-16): track the possible values of every scalar and vector component through swizzles, arithmetic, loops and calls, so an index into a bounded array or buffer that can leave its range is reported with the chain that produced it. Runs only in the Deep validation tier ([design 7.4](../../architecture/accel-lang-design.md#74-validation-tiers)), cached by content hash, never on the runtime compile path.
- **Output**: section in `accel-lang-design.md`; plan.
- **Done when**: an out-of-range index built from a swizzled, multiplied vector component is an error when proven and a warning with the chain when possible.

### W11.7 ISA measurement loop · explore · after W11.3

- **Goal**: per-variant ISA statistics (registers, instruction count, occupancy) of the engine shaders from an offline ISA compiler, plus RGP captures, as the gate for every IR-level optimisation (reference downgrades of design 7.3, the Q11.3 semantic passes, `spirv-opt` choices). The tool's licence is checked against the no-licensed-software rule first.
- **Output**: `architecture/accel-isa-measurement-exploration.md`; a repeatable measurement command.

### W12.1 Pipeline kinds design · design · after W11.2 (interfaces), W14.1 (graph nodes), W11.5 (B4 for ray tracing)

- **Goal**: compute, mesh and task, ray-tracing (SBT), work-graph placeholder across `Accel.Compile`, `Accel.Pipeline`, `Driver.Vulkan`; first consumers in order (sky LUT, particles, mesh test, ray-query shadow).
- **Output**: `architecture/pipeline-kinds-design.md`; plan.
- **Questions**: Q12.1, Q12.2 (shared with S15 minimum spec).

### W12.2 Implement compute and indirect dispatch · execute · after W12.1

- **Done when**: a compute pass (sky LUT) runs through the render graph with an indirect dispatch in a harness test.

### W12.3 Implement mesh and ray-query pipelines · execute · after W12.2, W15.0 (minimum spec), W11.5 (B2, B3)

- **Done when**: a mesh-shader test and a ray-query shadow test pass in the harness on a capable GPU and skip with a recorded reason on lavapipe.

### W13.1 Variant and pipeline cache design · design · after W11.3

- **Goal**: `VariantKey`, disk cache, pipeline library, async compile and swap, permutation control hook for S16, measurement of first-use hitches.
- **Owner, 2026-11-16**: shipped games compile variants at runtime; the permutation set between geometry, materials and effects cannot be known at cook time, since game code may change material assignments and parameters. While a variant compiles on the client, a generalised (uber) shader of the material class is served and swapped out when the variant is ready; the generalisation comes from W16.1's merge and uber-shader analysis. The compile path used at runtime is the minimal Build tier of W11.2; heavier checks never run there.
- **Output**: `architecture/pipeline-cache-design.md`; plan.
- **Questions**: Q13.1.

### W13.2 Implement the cache · execute · after W13.1, W02.2, W03.4

- **Done when**: a cold scene's pipelines come from disk on the second run; first-run hitch time is a counter.

### W60.1 JIT gate benchmark · explore · after S36 or S33 exists (a hot CPU candidate)

- **Goal**: measure runtime-specialised candidates (animation blend, procedural generator, replication encoder, and a data-layout re-compaction or graph re-optimisation case, Q60.1) against the compiled path; reopen S60 only on a clear win.
- **Questions**: Q60.1.

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q11.1 | The Accel IR milestone 2 has landed. W11.0 shrinks to recording the IR shape, rules and region-borrow spec on the site and fixing #148. |
| Q11.2 | Neither. Slang is not a dependency, not as an oracle and not as a backend; the shader toolchain is written in the project. Its module model remains reading material. Refined 2026-11-14 (owner): Slang may be read once its licence is checked, and other stable, correct references are searched as well; they inform the design only, nothing is copied one to one. |
| Q11.3 | No general optimiser of our own. `spirv-opt` plus the driver cover the generic passes; the project writes only engine-semantic IR passes: specialisation-constant folding into variants, dead-resource elimination, uniform-to-push-constant promotion, variant deduplication, and the uniformity, borrow and interface checks. Measured with RGP captures. Refined 2026-11-14 (owner): the first step relies on `spirv-opt` and the semantic passes only. Own optimisations (for example shader generalisation) may follow later, because `spirv-opt` lacks the semantic intent the IR carries; each one needs a measurement first. |
| Q12.1 | Reserve the work-graph pipeline kind as an enum value, no code. |
| Q12.2 | Minimum spec is RDNA3 and Ada Lovelace class. Mesh shaders and ray query are required features, together with descriptor indexing and 64-bit atomics. If a backport to older hardware is ever needed, it is done later as its own work; no optional tiers are designed in now. |
| Q13.1 | Pipeline library: design for it now, implement after a measured first-use hitch. |
| Q60.1 | S60 closes now with the gate recorded; it reopens on evidence from W60.1. Scope note from the owner: the JIT idea also covered runtime data restructuring and graph optimisation, for example re-compacting data layouts or re-optimising a graph for the shape in use, so W60.1 includes a data-layout candidate next to the code candidates. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q11.1 | May the milestone 2 branch be pushed and opened as a PR now, or does GPU render verification come first? | W11.0 | Push now; GPU verification is W26.2's first job |
| Q11.2 | Slang: oracle only, candidate backend, or neither? | W11.2 | Neither as a dependency; its module model is reading material for `@when` and link-time specialisation |
| Q11.3 | Own optimiser passes beyond `spirv-opt`, or `spirv-opt` plus the three semantic passes (uniformity, borrows, interface) only? | W11.2 | `spirv-opt` plus semantic passes; revisit with measurements |
| Q12.1 | Work graphs: reserve the kind now or ignore until the Vulkan extension is stable? | W12.1 | Reserve the enum value, no code |
| Q12.2 | GPU minimum spec (shared with S15): descriptor indexing and 64-bit atomics required; mesh shaders and ray query optional? | W12.1, W15.0 | Yes to that split; baseline named as RDNA2 and Turing class |
| Q13.1 | Pipeline library: adopt now or only after a measured first-use hitch on a real scene? | W13.1 | Design for it, implement after the measurement |
| Q60.1 | Keep S60 open at all, or close it now and reopen on evidence? | W60.1 | Close now with the gate recorded; reopen on evidence |
