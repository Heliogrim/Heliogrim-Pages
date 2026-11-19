# Accel Compiler Integration

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`d0c66b4a`](https://github.com/Heliogrim/Heliogrim-Engine/tree/d0c66b4a10d9f2e1395b4f134044fa228f330ea4), 2026-11-08
**Modules**: `Engine.Accel.Compile` ([`Stage/StageIr`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Compile/Stage/StageIr.hpp), [`Stage/StageComposer`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Compile/Stage/StageComposer.cpp), [`EffectCompiler`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Compile/EffectCompiler.cpp), [`Module/SpirvCompiler`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Compile/Module/SpirvCompiler.cpp)), `Engine.Accel.Lang` ([`Emitter/GlslEmitter`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Emitter/GlslEmitter.hpp), [`Ir/Lower`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Lower.hpp))

How an `.asl` file becomes a Vulkan pipeline: who calls what, which caches are hit, and where to look when it fails. Part of the [Accel shader toolchain](index.md); the passes themselves are on the [IR page](ir.md).

## Vocabulary

| Type | What it is |
|------|------------|
| `AccelerationEffect` | an ordered list of `Stage`s (vertex, fragment, ...) with a name and guid |
| `Stage` | one shader stage; holds a `lang::Intermediate` whose `ir` member is the parsed `.asl` module |
| `EffectProfile` | pass-wide context: profile modules injected into every stage, and the toggle values the profile fixes |
| `EffectSpecification` | the pass kind and fixed-function state, plus `targetSymbols()`: the output ids the pass needs |
| `EffectCompileRequest` | effect + profile + specification |
| `StageDerivat` | one compiled stage: the resolved intermediate and, later, its SPIR-V module |
| `BindLayout` | descriptor sets and push ranges of the pipeline, built from the IR layout |

## Step 1: load the shader

A pass builds its effect at setup. Today the loader is a helper, `makeIrIntermediate` (`Engine.Graphics.Render.Subpass/Impl/__tmp_helper.hpp`), which reads the file below `assets/shader/`, resolves `#include`s the same way and stores the parsed module:

```cpp
auto vertexStage = make_smr<Stage>(StageFlagBits::eVertex);
auto fragmentStage = make_smr<Stage>(StageFlagBits::eFragment);

vertexStage->setIntermediate(
	makeIrIntermediate(R"(postprocessing/pp.vs.asl)", lang::ir::EntryKind::eVertex));
fragmentStage->setIntermediate(
	makeIrIntermediate(R"(postprocessing/pp.fs.asl)", lang::ir::EntryKind::eFragment));

return make_smr<AccelerationEffect>(
	std::move(guid), "test-pp-effect",
	std::vector { std::move(vertexStage), std::move(fragmentStage) });
```

Vertex buffer layout is C++ data, not shader data, so a vertex stage may pass `vertexOffsets_` (id to byte offset) and `vertexFormats_` (id to `vk::Format`, for example 8-bit normalised data read as `f32vec4`). They travel as `VkBindLocation` annotations on the intermediate and win over the shader's type.

## Step 2: compile the effect

```hg-diagram
sequenceDiagram
    participant Pass as Render pass
    participant EC as EffectCompiler
    participant SC as StageComposer
    participant IR as StageIr / ir passes
    participant MB as VkModuleBuilder
    participant SP as SpirvCompiler (glslang)
    participant PC as VkPipelineCompiler
    Pass->>EC: compile(effect, profile, spec)
    EC->>EC: PassBuilder builds the pass object
    EC->>SC: compose(profile, spec, pass)
    SC->>IR: composePipelineIr(stages)
    IR->>IR: per stage: VariantCache.getOrCreate (merge, toggles, slice, contract)
    IR->>IR: PipelineLayoutCache.getOrCreate (layout, regions, emit GLSL, lower)
    IR-->>SC: StageDerivat per stage
    SC->>SC: appendBindLayout, pass.setBindingLayout
    SC-->>EC: StageDerivats
    loop each stage
        EC->>MB: build ModuleSource (GLSL text blocks)
        EC->>SP: compile to SPIR-V
    end
    EC->>PC: compile(spec, pass, stages, modules)
    PC-->>Pass: VkGraphicsPipeline
```

`StageComposer::compose` refuses an effect if any stage has no `ir` ("legacy text stages are not supported"). An empty result from `compose` makes `EffectCompiler::compile` return `eFailed`; the diagnostics are already logged.

## Step 3: inside composePipelineIr

For each stage, `resolveStageIr` builds or fetches a `Resolved` variant:

1. Collect the profile modules that carry `ir` (text-only profile modules are skipped with a warning) and the stage module.
2. `merge` them, profile modules first.
3. `checkStageValidity`: no builtin the stage does not have.
4. `fixToggles` with the profile's toggle values, then `resolveToggles`.
5. Check that every target symbol is an output of the stage (otherwise slicing would silently keep nothing), then `slice`. Target symbols apply to the **last** stage only (the export stage); earlier stages keep all outputs because the next stage may read them.
6. `computeInterface` and `checkContract`.

The variant key is computed from the input before any of this, so a cache hit skips all six steps.

Then, for the pipeline as a whole (cached in `PipelineLayoutCache` by the stages' variant keys):

1. `checkStageChain` over adjacent IR stages.
2. `assignPipelineLayout`: one slot per id across all stages. `assignPipelineSpecConstants`: one `constant_id` numbering.
3. Inputs of a stage directly behind another take the producer's output locations.
4. `lowerToIntermediate` per stage: `lowerRegions`, `GlslEmitter::emit`, and a fresh legacy `Representation` (one variable per interface entry with `SymbolId`, linkage and location annotations).

Finally `appendBindLayout` turns the layout into a `BindLayout`: one group per descriptor set, slots sorted by binding, push ranges carrying the flags of the stages that use them. The pipeline compiler numbers bindings by position, so a gap inside a set is an error.

## Step 4: GLSL and SPIR-V

`GlslEmitter::emit` writes one text block of Vulkan GLSL 460 per stage. All numbers come from the layout. This is the actual output for `postprocessing/pp.fs.asl` (checked 2026-11-08), abridged only where marked:

```glsl
#version 460

layout(std430) buffer;

layout(location = 0) out vec4 color;
layout(set = 0, binding = 0) uniform texture2D color_image;
layout(set = 0, binding = 1) uniform sampler color_sampler;
layout(location = 0) in vec2 local_uv;

const float PI = 3.1415926535897932384626433832795;
const float EXPOSURE = 4.5;

float saturate(const in float x);
vec3 saturate(const in vec3 x);
// ... prototypes of every other function from shared/math.asl and shared/tonemap.asl

// ... their bodies (saturate, random, hammersley, importanceSample, tonemapAces)

vec3 tonemapUncharted2(const in vec3 src)
{
	const float A = 0.15;
	const float B = 0.50;
	const float C = 0.10;
	const float D = 0.20;
	const float E = 0.02;
	const float F = 0.30;
	return ((((src * ((A * src) + (C * B))) + (D * E)) / ((src * ((A * src) + B)) + (D * F))) - (E / F));
}

void main()
{
	vec3 src = texture(sampler2D(color_image, color_sampler), local_uv).rgb;
	src = tonemapUncharted2((src * EXPOSURE));
	src = (src * (1.0 / tonemapUncharted2(vec3(11.2))));
	src = pow(src, vec3((1.0 / 2.2)));
	color = vec4(src, 1.0);
}
```

Things to notice: interface declarations are emitted sorted by id (`color`, `color-tex-0`, `color-tex-0-sampler`, `local-uv`), not in source order. Every function is written as a prototype first. `sample(t, s, uv)` becomes `texture(sampler2D(t, s), uv)`. Every binary operation gets parentheses. The unused library functions are still emitted, because this pass has no target symbols and an empty list does not slice. They are dead code for glslang to remove.

Besides the text, the emitter returns `GlslRequirements`: the `#extension` lines it enabled and the Vulkan features the stage needs (`shaderInt8`, `shaderFloat16`, 8/16-bit storage access, ...). Only types that actually occur trigger them.

`VkModuleBuilder` copies the text blocks into a `ModuleSource`; `SpirvCompiler` hands them to glslang (`TShader`, `TProgram`, target SPIR-V for Vulkan) and returns `SpirvByteCode`. `VkPipelineCompiler` creates the `VkShaderModule`s and the graphics pipeline.

`IrSpirvGateTest` (in `Heliogrim-Engine.Accel.Compile.Test`) is the guard on the emitter: it emits representative modules (vertex sampling, depth-only fragment, light loops with aliases, toggle variants per mesh type and pass context) and requires glslang to accept them.

## Caches and their keys

```hg-diagram
flowchart LR
    REQ["compose request"] --> K1["VariantKey per stage<br/>(content hash, toggles, outputs)"]
    K1 --> VC{"VariantCache hit?"}
    VC -- "no" --> R["merge, resolve, slice, contract"] --> VC2["store Resolved"]
    VC -- "yes" --> K2["pipeline key = stage keys in order"]
    VC2 --> K2
    K2 --> PCH{"PipelineLayoutCache hit?"}
    PCH -- "no" --> L["layout, regions, emit, lower"] --> PC2["store ResolvedPipeline"]
    PCH -- "yes" --> OUT["copy lowered intermediates into StageDerivats"]
    PC2 --> OUT
```

Both caches live in the `StageComposer`, so every effect compiled through one composer shares them. `StageComposerIrTest.SecondComposeHitsCache`, `SecondPipelineComposeHitsLayoutCache` and `PipelineHitResolvesNoStage` pin this behaviour. SPIR-V compilation is not cached here yet.

## Debugging

| Symptom | Where to look |
|---------|---------------|
| `Failed to compose ir stage: <message> (<line>:<col>)` in the log | the diagnostic names the module and the toggle combination; reproduce it in a `Lang.Test` with the same source |
| `Failed to lay out ir stages: ...` | `appendBindLayout`: a set with a gap, or the same id with another class or type in two stages |
| `target symbol 'x' is not an output of the stage` | the pass's `EffectSpecification::targetSymbols()` names an id the last stage does not output for that toggle combination |
| `... has no ir intermediate` | a stage was set up with GLSL text; load it with `makeIrIntermediate` |
| glslang error at SPIR-V compile | an emitter bug: add the construct to `IrSpirvGateTest` |
| Warnings about implicit derivatives | expected in `brdf/gbuffer.fs.asl` and the shadow PCF loops; see [uniformity](asl.md#control-flow) |

Module warnings (from parse and typecheck) never fail a compose; they are logged from the input modules because `merge` drops them.

## Limits

- **Only profile toggles are fed.** `resolveStageIr` passes empty pass and material toggle sources; the precedence rules are implemented in `fixToggles` but nothing supplies those values yet.
- **Inert pass contract.** The pass side is built as "provides every bind input, requires nothing". Hooking the render-graph declarations (`declareInputs`, `declareOutputs`) into `StageContract` is open. Since W11.4 (`1cc9e75c`, after the verified commit) a specification can declare a contract through `EffectSpecification::stageContract()` and `resolveStageIr` checks it (`ASL0075`, `ASL0076`); none declares one yet, render-graph wiring is W14.
- **Graphics only.** `VkPipelineCompiler` builds graphics pipelines; compute, geometry and tessellation modules emit and pass glslang but have no pipeline creation.
- **Legacy loader.** `makeIrIntermediate` is a temporary helper reading files directly; `Engine.Accel.Loader` (`EffectLoader`, `EffectCache`) does not know about `.asl` yet.
- **Leftover TODOs** in `EffectCompiler::compile` describe the old design (text composition, symbol aliasing as a "temporary solution"); they predate the IR and are not a plan.
