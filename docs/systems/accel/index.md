# Accel Shader Toolchain

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`d0c66b4a`](https://github.com/Heliogrim/Heliogrim-Engine/tree/d0c66b4a10d9f2e1395b4f134044fa228f330ea4), the head of PR [#156](https://github.com/Heliogrim/Heliogrim-Engine/pull/156) (`feat/accel-ir-regions` into `feat/wip`), 2026-11-08. Not on `master` yet.
**Modules** (see the [module map](../../architecture/modules.md)): `Engine.Accel.Lang` (ASL front-end, IR, passes, GLSL emitter), `Engine.Accel.Compile` (stage composition, layout, SPIR-V), with `Engine.Accel.Pipeline`, `Engine.Accel.Effect` and `Engine.Accel.Pass` as consumers.
**Related**: [Accel Lang topic](../../plan/topics/accel-lang.md) (battle plan S11/S12), [Accel Lang work packages](../../plan/work/accel-lang.md), issues [#78](https://github.com/Heliogrim/Heliogrim-Engine/issues/78) (migration, all stages) and [#82](https://github.com/Heliogrim/Heliogrim-Engine/issues/82) (region borrows).

This part has four pages:

| Page | Read it when you want to |
|------|--------------------------|
| This overview | know what the toolchain is for and how the pieces fit |
| [ASL language](asl.md) | write or read a `.asl` shader |
| [IR and passes](ir.md) | understand or change what happens between parse and emit |
| [Compiler integration](compiler.md) | follow a shader from an effect to a Vulkan pipeline, or debug a failed compose |

## Purpose

Before this work, one shader was described five times: the GLSL text, hand-built `lang::Variable` annotations in C++ (for example in `DepthPrePass.cpp`), the composed material, the render-graph subpass and the bound resources. Set and binding numbers lived in people's heads, and a single forgotten annotation turned into a GPU crash at runtime.

The Accel toolchain makes the shader source the single place that states a shader's interface:

- **ASL** (Accel Shading Language, `.asl`) is the only shader source. Inputs, outputs and bindings carry string ids; nobody writes a set, binding, location or `constant_id` number.
- **The IR** (`hg::engine::accel::lang::ir::Module`) holds the parsed module: types, bindings, constants, toggles and function bodies as a small AST.
- **Passes** over the IR merge profile modules into the shader, pick one toggle combination, cut away code the pass does not need, compute the interface, lay out descriptors and check contracts. All of this runs on the CPU and is covered by unit tests, so interface mistakes fail in `Heliogrim-Engine.Accel.Lang.Test`, not on a GPU.
- **The GLSL emitter** writes Vulkan GLSL 460 from the resolved IR; glslang compiles it to SPIR-V.

What it deliberately does not do yet: emit SPIR-V directly, optimise, build compute, mesh or ray-tracing pipelines on the Vulkan side, or feed material requirements back into the render graph. See [Limits](#limits-and-known-issues).

## Where it sits

```hg-diagram
flowchart LR
    ASL["assets/shader/**/*.asl"]
    PASS["Render passes and effects<br/>(Engine.GFX.Render.*)"]
    PROF["EffectProfile<br/>(profile modules, toggles)"]
    SPEC["EffectSpecification<br/>(target symbols)"]
    LANG["Engine.Accel.Lang<br/>parse, IR passes, emit GLSL"]
    COMP["Engine.Accel.Compile<br/>compose, layout, glslang"]
    PIPE["Engine.Accel.Pipeline<br/>VkGraphicsPipeline, BindLayout"]
    GPU["Vulkan driver"]
    ASL --> PASS
    PASS -->|"makeIrIntermediate"| LANG
    PROF --> COMP
    SPEC --> COMP
    LANG --> COMP
    COMP --> PIPE
    PIPE --> GPU
```

Render passes load their `.asl` files at setup (a helper `makeIrIntermediate` parses the file and stores the IR module in a `lang::Intermediate`). An `EffectCompileRequest` (effect, profile, specification) then goes through `EffectCompiler::compile`, which uses `StageComposer` to resolve and lay out all stages together, and finally builds SPIR-V modules and the Vulkan pipeline.

## The pipeline in one picture

Every arrow below is a function in `Engine.Accel.Lang/Ir` or `Engine.Accel.Compile/Stage`. The [IR page](ir.md) walks through each step with an example.

```hg-diagram
flowchart TD
    SRC[".asl text"] --> P["parseModule<br/>lexer, parser, #include, typecheck"]
    PM["profile modules (.asl)"] --> M
    P --> M["merge<br/>profile modules first, shader last"]
    M --> FT["fixToggles<br/>pass > profile > material > default"]
    FT --> RT["resolveToggles<br/>drop inactive @when code"]
    RT --> SL["slice<br/>keep what required outputs need"]
    SL --> IF["computeInterface"]
    IF --> CC["checkContract, checkStageChain"]
    CC --> LY["assignPipelineLayout<br/>set, binding, location, push, spec ids"]
    LY --> RG["lowerRegions<br/>borrows become index math"]
    RG --> EM["GlslEmitter::emit<br/>Vulkan GLSL 460"]
    EM --> GL["glslang (SpirvCompiler)<br/>SPIR-V"]
    GL --> VK["VkPipelineCompiler<br/>VkGraphicsPipeline"]
    VC[("VariantCache")] -.-> FT
    PC[("PipelineLayoutCache")] -.-> LY
```

Two caches keep the hot path cheap. A resolved stage is cached by a content hash of (module, toggle values, required outputs); a laid-out pipeline is cached by the ordered keys of its stages. A cache hit computes one key and does one hash lookup: no parsing, merging or text assembly at runtime.

## A first example

The post-processing fragment shader, as it ships in `assets/shader/postprocessing/pp.fs.asl`:

```c
#include <shared/math.asl>
#include <shared/tonemap.asl>

const EXPOSURE: f32 = 4.5;

@input (mode = forward, id = "local-uv") f32vec2 local_uv;

@input (mode = bind, id = "color-tex-0", class = texture) texture2d color_image;
@input (mode = bind, id = "color-tex-0-sampler", class = sampler) sampler color_sampler;

@output (mode = forward, id = "color") f32vec4 color;

fn main() {
	let src = sample(color_image, color_sampler, local_uv).rgb;

	// HDR tonemapping
	src = tonemapUncharted2(src * EXPOSURE);
	src = src * (1.0 / tonemapUncharted2(f32vec3(11.2)));

	// Gamma correction
	src = pow(src, f32vec3(1.0 / 2.2));

	color = f32vec4(src, 1.0);
}
```

Nothing in the file says "set 0, binding 1" or "location 0". The layout pass derives them: the texture gets set 0 binding 0, the sampler binding 1 (classes are ordered uniform, storage, texture, sampler, then by id), `local-uv` gets input location 0 and `color` output location 0. The pass that uses the shader never repeats any of it; it refers to `"color-tex-0"` by id.

## Shader inventory

All 34 shader files under `assets/shader` are `.asl`; the legacy GLSL shaders and `shared/__macros__.glsl` were deleted. The assets live in a separate checkout, so no engine test reads them any more (the asset-reading tests were dropped in `d0c66b4a`).

| Folder | Files | Used by |
|--------|-------|---------|
| `brdf/` | forward BRDF, G-buffer pair, irradiance, prefilter, LUT generators, cube generator | `BrdfBase`, `TmpBrdf*Pass` |
| `depth/` | pre-depth pair | `DepthPrePass` |
| `shadow/` | directional shadow pair | `TmpDirectionalShadowPass` |
| `postprocessing/` | full-screen pair | `PostProcessPass` |
| `skybox/`, `ui/`, `visualize/`, `test/` | one pair each | `Skybox`, `UIBase`, `Visualize`, `TriTestPass` and `__Test__Renderer` |
| `shared/` | `math`, `pbr`, `lighting.brdf`, `tonemap` libraries | included by the above |
| `spec/`, `template/` | mesh-type contracts and authoring templates | valid modules with tests, not loaded by any pass |

## Limits and known issues

- **Never rendered on a GPU after the migration.** Unit tests and the glslang gate prove the emitted GLSL compiles; rendering equivalence waits for the GPU render test harness.
- **Graphics pipelines only on the Vulkan side.** The IR, emitter and SPIR-V gate cover compute, geometry and tessellation, but `VkPipelineCompiler` builds graphics pipelines only. Mesh, task, ray-tracing and work-graph entries do not exist in the IR yet ([#78](https://github.com/Heliogrim/Heliogrim-Engine/issues/78)).
- **GLSL is the only backend.** No direct SPIR-V emitter, no optimiser, no `OpLine` debug info. Generated identifiers can collide with GLSL names ([#148](https://github.com/Heliogrim/Heliogrim-Engine/issues/148)).
- **Contracts are inert on the pass side.** The stage contract is built as "offers every bind input, requires nothing", so only a missing bind class and unknown target symbols fail today.
- **One descriptor set.** The IR has no update-frequency annotation, so every binding starts in set 0, grouped by class (a `shortcut:` in `Layout.hpp`).
- **Legacy bridge.** After emission, every stage is lowered back into the old `lang::Representation` (variables with `SymbolId`/linkage annotations) because the module builder and pipeline compiler still read it.
- **Caches serialise hits.** `VariantCache` and `PipelineLayoutCache` take an exclusive fiber-safe spin lock per lookup until `Engine.Async` gets a shared lock.

## Changing it

- Language change (syntax, type, builtin): start at `Ir/Lexer.cpp`, `Ir/Parser.cpp`, `Ir/Parser.Body.cpp`, `Ir/Typecheck.cpp`, `Ir/Builtin.hpp`, then the emitter. Every new IR field must go into `contentHash` (`Ir/Variant.cpp`) and the arena remaps in `Ir/Merge.cpp` and `Ir/Compact.cpp`; every new statement kind must be walked by `Analysis`, `Slice`, `Compact`, `Resolve` and the emitter.
- Tests: `Heliogrim-Engine.Accel.Lang.Test` (parser, typecheck, merge, resolve, slice, layout, regions, uniformity, variants, lowering) and `Heliogrim-Engine.Accel.Compile.Test` (stage composition, caches, layout across stages, vertex formats, and `IrSpirvGateTest`, which runs emitted GLSL through glslang).
- Parser and typecheck never assert or throw on bad input; they return located diagnostics. Keep it that way.
