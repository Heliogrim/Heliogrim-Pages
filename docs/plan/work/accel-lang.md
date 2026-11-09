# Work: Accel Lang, Pipeline Kinds, Variant Cache, JIT

**Systems** S11, S12, S13, S60 · **Issues** [#82](https://github.com/Heliogrim/Heliogrim-Engine/issues/82), [#92](https://github.com/Heliogrim/Heliogrim-Engine/issues/92), [#78](https://github.com/Heliogrim/Heliogrim-Engine/issues/78), [#93](https://github.com/Heliogrim/Heliogrim-Engine/issues/93), [#140](https://github.com/Heliogrim/Heliogrim-Engine/issues/140), [#148](https://github.com/Heliogrim/Heliogrim-Engine/issues/148) · **Track** B, E · **Milestone** M2, M6
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Accel Lang](../topics/accel-lang.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Accel IR milestones 1 and 2 (engine branches `feat/accel-ir`, `feat/accel-ir-coverage`, session notes 2026-11-07) | All engine shaders in `.asl`; all graphics stages plus compute in the IR; glslang-gated GLSL emitter; immutable-by-default references; SIMT loop rules; `IrSpirvGateTest.AllAssetsAreAsl` | Milestone 2 branch not pushed or merged; GPU render never verified; editor build on master broken by two unrelated functions |
| Region borrows spec and plan (#82, untracked `docs/superpowers/{specs,plans}/2026-11-07-ir-region-borrows*.md` in the coverage worktree) | Five-task plan ready; helpers specialised per root in the IR (backend neutral); `let` borrows share the overlap rule | Not started; GLSL vs SPIR-V lowering of borrows left open on purpose |
| Issue #148 | Three ASL-to-GLSL name-collision gaps (`_hg_ref` hoisting, reserved names) | Bug on the GLSL path; irrelevant once SPIR-V is primary, must still be fixed while GLSL is the oracle |
| Accel IR brainstorm (memory, 2026-10) | Goals: compute and mesh stages, sparse and bindless resources, indirect dispatch for virtualised geometry | Matches S12 and S15 prerequisites |
| [Render graph v2 work](render-graph-gpu-driven.md) | Pass declarations read inputs and outputs from the ASL interface | The interface export format is owned here (W11.3) |

No exploration page exists for ASL on this site. The engine-side specs are untracked; W11.0 records the state on the site so the plan survives the worktree.

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

### W11.0 Land milestone 2 and record ASL state on the site · execute · ready

- **Goal**: milestone 2 has landed (Q11.1); fix #148 on the GLSL path, write `architecture/accel-lang-design.md` from the engine-side specs so the IR shape, rules and the region-borrow spec live on the site.
- **Done when**: branch merged; #148 closed; the design page exists with the IR part list and the borrow rules.
- **Questions**: Q11.1.

### W11.1 Region borrows (#82) · execute · ready (plan exists)

- **Goal**: run the existing five-task plan by subagent-driven development on `feat/accel-ir-regions`.
- **Done when**: the micropolygon scratchpad layout compiles and the borrow tests pass; GLSL oracle unchanged for shaders without borrows.

### W11.2 Direct SPIR-V backend design · design · after W11.0

- **Goal**: emitter structure, capability analysis, `spirv-val` and `spirv-opt` in tests, debug info, the oracle protocol (GLSL path becomes test-only after parity), the Slang question.
- **Inputs**: IR parts list, SPIRV-Tools, Slang user guide (module and link-time specialisation chapters).
- **Output**: section in `accel-lang-design.md`; plan.
- **Questions**: Q11.2, Q11.3.

### W11.3 Implement SPIR-V emitter, feature analysis, interface export · execute · after W11.2

- **Done when**: every engine shader compiles to SPIR-V, passes `spirv-val`, renders identically to the GLSL path in the harness; `InterfaceDesc` is emitted per entry point.

### W11.4 Uniformity and interface check passes · execute · after W11.3

- **Done when**: a barrier in divergent flow and an interface mismatch with a pass declaration are diagnostics with both locations.

### W12.1 Pipeline kinds design · design · after W11.2 (interfaces), W14.1 (graph nodes)

- **Goal**: compute, mesh and task, ray-tracing (SBT), work-graph placeholder across `Accel.Compile`, `Accel.Pipeline`, `Driver.Vulkan`; first consumers in order (sky LUT, particles, mesh test, ray-query shadow).
- **Output**: `architecture/pipeline-kinds-design.md`; plan.
- **Questions**: Q12.1, Q12.2 (shared with S15 minimum spec).

### W12.2 Implement compute and indirect dispatch · execute · after W12.1

- **Done when**: a compute pass (sky LUT) runs through the render graph with an indirect dispatch in a harness test.

### W12.3 Implement mesh and ray-query pipelines · execute · after W12.2, W15.0 (minimum spec)

- **Done when**: a mesh-shader test and a ray-query shadow test pass in the harness on a capable GPU and skip with a recorded reason on lavapipe.

### W13.1 Variant and pipeline cache design · design · after W11.3

- **Goal**: `VariantKey`, disk cache, pipeline library, async compile and swap, permutation control hook for S16, measurement of first-use hitches.
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
| Q11.2 | Neither. Slang is not a dependency, not as an oracle and not as a backend; the shader toolchain is written in the project. Its module model remains reading material. |
| Q12.1 | Reserve the work-graph pipeline kind as an enum value, no code. |
| Q12.2 | Minimum spec is RDNA3 and Ada Lovelace class. Mesh shaders and ray query are required features, together with descriptor indexing and 64-bit atomics. If a backport to older hardware is ever needed, it is done later as its own work; no optional tiers are designed in now. |
| Q13.1 | Pipeline library: design for it now, implement after a measured first-use hitch. |

| Q11.3 | No general optimiser of our own. `spirv-opt` plus the driver cover the generic passes; the project writes only engine-semantic IR passes: specialisation-constant folding into variants, dead-resource elimination, uniform-to-push-constant promotion, variant deduplication, and the uniformity, borrow and interface checks. Measured with RGP captures. |
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
