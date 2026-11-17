# Render Graph

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip`, 2026-11-16. Not on `master` yet.
**Modules** (see the [module map](../architecture/modules.md)): `Engine.Graphics.RenderGraph` (nodes, builder, symbols, runtime passes), `Engine.Graphics.RenderGraph.Compile` (compile graph to runtime graph), with `Engine.Graphics.Render` (renderer, render pass), `Engine.Graphics.Render.Command` (recorded commands), `Engine.Graphics.Render.Subpass` (the pass implementations), `Engine.Graphics.Render.Predefined` (shared symbols and effects) and `Engine.Graphics.Render.Graph.Scene` (scene walker). The Vulkan side of command translation lives in `Engine.Driver.Vulkan`.
**Related**: [Accel compiler integration](accel/compiler.md) (how a pass gets its pipeline), [GPU test harness](gpu-test-harness.md) (records commands without a graph), [Render graph v2 topic](../plan/topics/render-graph-gpu-driven.md) and [work packages](../plan/work/render-graph-gpu-driven.md) (W14.0 is this page), issue [#94](https://github.com/Heliogrim/Heliogrim-Engine/issues/94).

All code links below point at the verified commit.

## Purpose

The render graph decides which subpasses run in a frame, in which order, and how they find the textures and buffers they share. A renderer is described once as a **compile graph**. Each in-flight frame gets its own **runtime graph** compiled from it, with its own subpass objects. Every frame the runtime graph is walked three times: iterate (gather work), resolve (compile pipelines), execute (record and submit).

Resources are shared by name, not by edges. A subpass looks up a **symbol** such as `scene::color` in a **symbol context** and gets a `SymbolizedResource` that holds a type-erased pointer and a list of semaphores.

What it does not do today: derive barriers, alias memory, cull unused passes, reorder passes, run passes in parallel or on other queues, or check that a pass's inputs are produced by an earlier pass. The graph is a fixed linear list built in C++; every pass records, submits and waits for its own command buffer. See [Limits](#limits-and-known-issues).

## Where it sits

```hg-diagram
flowchart LR
    TICK["RenderTickStage<br/>(Engine.Graphics.Schedule)"]
    RT["RenderTarget<br/>(Engine.Graphics)"]
    REN["Renderer<br/>(Engine.Graphics.Render)"]
    CG["CompileGraph"]
    RGC["RenderGraphCompiler<br/>(RenderGraph.Compile)"]
    RP["RenderPass<br/>RuntimeGraph + SymbolContext"]
    SP["SubPass implementations<br/>(Render.Subpass, Reflow.Render)"]
    SCN["SceneView / RenderSceneSystem<br/>(Engine.Graphics.Scene)"]
    ACC["EffectCompiler<br/>(Engine.Accel.Compile)"]
    CMD["RenderCommandBuffer<br/>(Render.Command)"]
    VK["VkRCmdTranslator, VkNativeBatch<br/>(Engine.Driver.Vulkan)"]
    TICK --> RT
    RT -->|"allocate, update"| REN
    REN --> CG
    CG --> RGC --> RP
    RT -->|"scene::view, scene::color"| RP
    RP -->|"iterate, resolve, execute"| SP
    SCN --> SP
    SP -->|"resolve"| ACC
    SP -->|"execute"| CMD --> VK
```

The scheduler's render tick drives every `RenderTarget`. A target owns one `RenderPass` per in-flight frame, each created by a `Renderer` from its compile graph. The target binds the scene view and the output texture into the pass as symbols. Subpasses read the render-side scene mirror through the scene view, compile their effects through Accel, and record commands that the Vulkan driver layer translates and submits.

## How it works

### Two graph types, one node model

[`CompileGraph`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/CompileGraph.hpp) and [`RuntimeGraph`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/RuntimeGraph.hpp) have the same shape: a begin `AnchorNode` and an end `AnchorNode`. A new graph is the minimal graph `begin -> end`. The compile graph also holds a set of **expected provisions**: the symbols the graph promises to produce (today always `scene::color`).

Nodes form a linked structure. Forward links are owning (`smr<Node>`), backward links are non-owning (`nmpt<const Node>`). Every node carries an `Auxiliary`, a set of components (`AnchorComponent`, `BarrierComponent`, `ProviderComponent`) that only carry names and provision sets.

| Node | Links | Role |
|------|-------|------|
| `AnchorNode` | one next, one prev | begin and end of a graph |
| `BarrierNode` | one next, one prev | a named marker; does nothing at runtime |
| `SLNode` | one next, one prev | base of single-link runtime nodes |
| `SubPassNode<T>` | via `SLNode` | owns one `SubPass` of type `T` and forwards iterate, resolve, execute to it |
| `ProviderNode` | one next, one prev | holds a `ProviderComponent`; no runtime work |
| `DivergeNode` | many next, one prev | fan-out; visits every child |
| `ConvergeNode`, `BinNode` | one next, many prev | fan-in |
| `SelectorNode` | many next with a bit mask each, one prev | masked fan-out (see [Limits](#limits-and-known-issues)) |
| `CompileSubPassNode` | one next, one prev | compile-time placeholder; holds a builder function that creates a `SubPassNode<T>` |
| `CompileBinNode` | none | compiles to a `BinNode` |

A runtime node implements three methods from [`RuntimeNode`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Node/RuntimeNode.hpp): `iterate`, `resolve`, `execute`, each returning an `IterationResult` flag set. A compile node implements `compile(CompilePassContext) -> uptr<RuntimeNode>`. Only `SubPassNode<T>` does real work; every other runtime node returns `eNone` from all three.

Traversal is a double-dispatch visitor. `Node::accept(visitor)` calls `visitor(*this)` with the concrete type; [`Visitor`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Visitor/Visitor.hpp) forwards every typed overload to `operator()(cref<Node>)` unless a subclass overrides it. `traverse` visits the successors, `rtraverse` the predecessors.

### Building a compile graph

There is no declarative builder. A renderer subclass writes its graph in C++ with [`Builder::insertNode`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Builder/Builder.cpp), which splices a node between two existing nodes `from` and `to`. This is the editor's graph, from [`EditorRenderer.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Editor.Render/Renderer/EditorRenderer.cpp), with the other passes cut where marked:

```cpp
auto graph = make_uptr<graph::CompileGraph>();
graph->addExpectedProvision(graph::Provision { makeSceneColorSymbol() });

const nmpt<graph::Node> begin = graph->begin().get();
const nmpt<graph::Node> end = graph->end().get();

nmpt<graph::Node> cursor = begin;

auto beforeBarrier = make_smr<graph::BarrierNode>();
auto beginPass = make_smr<graph::CompileSubPassNode>();
auto uiPass = make_smr<graph::CompileSubPassNode>();
// ... endPass, afterBarrier

uiPass->setSubPassBuilder(
	[](cref<graph::CompilePassContext> ctx_) -> uptr<graph::SubPassNodeBase> {
		auto node = ctx_.getGraphNodeAllocator()
			->allocate<graph::SubPassNode<engine::reflow::render::ReflowPass>>();
		return node;
	}
);
// ... builders for beginPass and endPass

nmpt<graph::Node> nextCursor = beforeBarrier.get();
graph = graph::Builder::insertNode(std::move(graph), cursor, end, std::move(beforeBarrier));

cursor = std::exchange(nextCursor, beginPass.get());
graph = graph::Builder::insertNode(std::move(graph), cursor, end, std::move(beginPass));

cursor = std::exchange(nextCursor, uiPass.get());
graph = graph::Builder::insertNode(std::move(graph), cursor, end, std::move(uiPass));
// ... endPass, afterBarrier the same way
```

`insertNode` runs a [`BuilderVisitor`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Builder/BuilderVisitor.cpp) from the graph's begin. It finds `from` by address and `to` as a direct successor, then calls `LinkNodes` twice: `from -> node` and `node -> to`. `LinkNodes` uses a backward-link visitor on the successor and a forward-link visitor on the predecessor, so each node type sets its own `prev`/`next` fields. Each insert walks the graph from the start; building is quadratic in the node count, which does not matter at a dozen nodes.

Pitfalls:

- `to` must be the **current** successor of `from`. The renderers always pass `end` and move the cursor to the node they just inserted, which keeps the list linear.
- `Builder::eraseNode` calls `todo_panic()`. Nodes cannot be removed.
- The subpass builder is a `std::function` called once per runtime graph. Capture nothing that is frame-specific.

### Compiling to a runtime graph

[`RenderGraphCompiler`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph.Compile/RenderGraphCompiler.cpp) takes a `CompileRequest { graph, targetSymbols }`:

1. Return `nullptr` if `targetSymbols` is empty.
2. For every target symbol, look for an expected provision with the same scope and name. If one is missing, call `hg::breakpoint()` and return `nullptr`.
3. Create an empty `RuntimeGraph` and run a [`CompileVisitor`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph.Compile/CompileVisitor.cpp) **backwards** from the compile graph's end anchor.

The visitor visits each node, inserts its runtime counterpart directly after the runtime graph's begin anchor, then follows `rtraverse` to the predecessor. Walking backwards while always inserting at the front yields the forward order. Plain runtime nodes are re-created as fresh, empty nodes of the same type (names in barrier components are lost). A `CompileNode` is compiled with a new `CompilePassContext`, and its result is inserted. A `SubPassNodeBase` in a compile graph hits `assert(false)`: subpasses must be wrapped in a `CompileSubPassNode`.

The compiled runtime graph for the editor looks like this:

```hg-diagram
flowchart LR
    B["Anchor (runtime begin)"] --> A1["Anchor (copy of compile begin)"] --> X1["Barrier"] --> P1["SubPassNode&lt;DummyProvider&gt;"] --> P2["SubPassNode&lt;ReflowPass&gt;"] --> P3["SubPassNode&lt;TmpEndPass&gt;"] --> X2["Barrier"] --> A2["Anchor (copy of compile end)"] --> E["Anchor (runtime end)"]
```

`CompilePassContext` gives the builder a [`GraphNodeAllocator`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Memory/GraphNodeAllocator.hpp). It placement-constructs the node in memory from a `std::pmr` resource and hands it out as a plain `uptr`, which frees it with `delete`. This only works because the resource is a proxy for `new_delete_resource()`. `getSceneView()` returns null.

[`Renderer::makeDefaultRuntimeGraph`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render/Renderer.cpp) passes every expected provision as a target, so step 2 always succeeds for a graph that declares one. A compile graph with **no** expected provision compiles to `nullptr`, and the `RenderPass` gets a null graph that crashes on the first update.

### Symbols and the symbol context

A [`Symbol`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Symbol/Symbol.hpp) is flags, a scope (`eGlobal`, `eMaterial`, `eLocal`, `eEffectInternal`, `eUserDefined` plus a layer string), a name and a `Description`. `Engine.Graphics.Render.Predefined` makes the shared ones, each as a function-local static:

```cpp
smr<const graph::Symbol> engine::render::makeSceneColorSymbol() {
    static auto obj = make_smr<graph::Symbol>(
        graph::SymbolFlagBits::eUndefined,
        graph::SymbolScope {
            .type = graph::SymbolScopeType::eGlobal,
            .layer = ""
        },
        "scene::color",
        makeColorBufferDescription()
    );
    return obj;
}
```

| Function | Name | Description |
|----------|------|-------------|
| `makeSceneColorSymbol` | `scene::color` | 2D texture, `B8G8R8A8Unorm`, one layer |
| `makeSceneDepthSymbol` | `scene::depth` | 2D texture, `D32Sfloat`, one layer |
| `makeSceneViewSymbol` | `scene::view` | `SceneViewDescription` |
| `makeBrdfLutSymbol`, `makeBrdfPrefilterSymbol`, `makeBrdfIrradianceSymbol`, `makeDirectionalShadowSymbol` | image-based lighting and shadow inputs | texture descriptions |
| `makeSkyboxTextureSymbol`, `makeSceneCameraSymbol`, `makeSceneStencilSymbol`, `makeDeferredNormalSymbol`, `makeDeferredPositionSymbol` | defined, not used by any running pass | |

A [`TextureDescription`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Relation/TextureDescription.hpp) holds type, format, layer count and an active-mip mask, each with a matching mode (`eIgnored`, `eCovariant`, `eInvariant`). `isValidObject` checks only the `eInvariant` values.

The [`SymbolContext`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Symbol/SymbolContext.cpp) maps symbols to [`SymbolizedResource`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.RenderGraph/Symbol/SymbolizedResource.hpp)s:

```cpp
class SymbolizedResource {
public:
	bool owned : 1/* Whether the resource is NOT owned by the context */ = false;
	bool transient : 1/* Currently unused */ = false;

	smr<const Symbol> symbol = nullptr;
	void* data = nullptr;

	// Warning: Temporary -> May be offloaded into a transition chaining layer
	Vector<void*> barriers;
	// ...
};
```

| Call | Effect |
|------|--------|
| `exportSymbol(symbol)` | allocate a context-owned resource with `data == nullptr`; asserts the symbol is new |
| `exposeSymbol(symbol, resource)` | register a resource the caller owns (`owned == true` by convention) |
| `getExportSymbol(symbol)`, `getImportSymbol(symbol)` | the same lookup: this context, then parents |
| `eraseExportSymbol` | delete a context-owned resource; fails unless `data == nullptr` |
| `eraseExposedSymbol(symbol)` | unregister an externally owned resource |
| `registerExposeSymbol`, `registerExportSymbol`, `registerImportSymbol` | the first records the observer in a list nobody reads; the other two return `false` and do nothing |

On a resource, `create<T>`, `load<T>`, `store<T>` and `destroy<T>` heap-allocate, cast, assign and delete `data` as a `T`. The type is not stored; `load<T>` with the wrong `T` is undefined behaviour. The optional second template argument checks that the symbol's description has that dynamic type.

Pitfalls:

- **Symbols are keyed by pointer.** The context's map compares `smr::get()`. A second `Symbol` object with the same name is a different key. Always use the `make*Symbol()` functions; never build a symbol inline for lookup. Only `RenderGraphCompiler` compares by scope and name.
- **One flat context per render pass.** `RenderPassState` holds one root `SymbolContext`; every subpass sees the same one. `SubPassNode` passes it on with `static_cast<cref<ScopedSymbolContext>>`, but no `ScopedSymbolContext` object is ever created, and `_parent` is never set.
- **Destruction asserts.** The context destructor asserts `data == nullptr` for every context-owned resource. Unbind what you bound before the pass dies.
- **Inverted value check, latent.** `create` and `store` with a validation type return failure when `isValidObject` returns **true**. It never fires today because `HasValueValidation` is false for the `smr<...>` types every caller uses; it will fire as soon as someone stores a raw pointer type.

### The renderer and its render passes

[`Renderer`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render/Renderer.hpp) owns the compile graph. `Renderer::allocate()` compiles a fresh runtime graph and wraps it in a [`RenderPass`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render/RenderPass.cpp) with a local cache and allocator. `RenderPass` holds the runtime graph, a `RenderPassState` (scene view, bound targets, the symbol context), and a fence slot.

Two renderers exist, both registered by name in `Graphics`:

| Name | Class | Registered in | Used by | Graph |
|------|-------|---------------|---------|-------|
| `Test-Renderer` | [`TestRenderer`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render/__Test__Renderer.cpp) | `Graphics::setup` | the editor scene viewport | see [the engine's graph](#the-graph-the-engine-runs) |
| `Editor-Renderer` | [`EditorRenderer`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Editor.Render/Renderer/EditorRenderer.cpp) | `editor::boot::initRender` | the editor main window | `DummyProvider`, `ReflowPass`, `TmpEndPass(ePresentSrcKHR)` |

A target binds its inputs as symbols. `RenderPass::changeSceneView` exports `scene::view` and stores the `smr<const SceneView>`. `RenderPass::bindTarget` checks the texture against the symbol's `TextureDescription`, refuses to rebind an already bound symbol (logs `Tried to bind target ... while implicit rebinding is not allowed.`), exports the symbol and stores the texture as `smr<TextureLikeObject>`. `unbindTarget` reverses it; call it before binding a new swapchain image.

### Per-frame lifecycle

```hg-diagram
sequenceDiagram
    participant Tick as RenderTickStage
    participant RT as RenderTarget
    participant R as Renderer
    participant RP as RenderPass
    participant SP as SubPass (each, in order)
    participant VK as VkNativeBatch
    Tick->>RT: next()
    RT->>RT: wait fence, acquire swapchain image
    RT->>RP: changeSceneView / unbind + bindTarget(scene::color)
    Tick->>RT: update()
    RT->>RP: addTargetWaitSignal(scene::color, image ready)
    RT->>R: update(pass)
    R->>SP: IterationPass: iterate(symbols)
    R->>SP: ResolvePass: resolve()
    R->>RP: reallocate (no-op)
    RT->>RP: operator()()
    RP->>SP: ExecutionPass: execute(symbols)
    SP->>VK: translate, commitAndDispose (submit + wait)
    Tick->>RT: finish()
    RT->>RT: present, waiting on scene::color barriers
```

[`RenderTickStage::invokeRenderTarget`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Schedule/RenderTickStage.cpp) runs `next()`, `update()` and `finish()` on each target selected by the `RenderSceneManager`. [`RenderTarget`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics/RenderTarget.cpp) keeps one or two render passes (two when "on the flight" is set) and alternates between them.

`Renderer::updateIncremental` runs two visitors, then `RenderPass::operator()` runs the third:

```cpp
graph::IterationPass iterationPass { symbolContext };
auto iteration = iterationPass.visitor();
pass_->_graph->update(iteration);

graph::ResolvePass resolvePass { symbolContext };
auto resolve = resolvePass.visitor();
pass_->_graph->update(resolve);
```

All three visitors share one pattern: `operator()(cref<Node>)` pushes the node into a queue, and the outermost call drains it. Each step calls the node's phase method, then `traverse` to enqueue the successors. The walk is breadth-first from the begin anchor with no visited set. The returned `IterationResult` is ignored.

What the subpasses do in each phase, by convention:

| Phase | Typical work |
|-------|--------------|
| `iterate(symbols)` | build the `AccelerationEffect` and `GraphicsPass` once; read `scene::view` and collect models from the render scene |
| `resolve()` | compile the pipeline once, while `_compiled.flag == eUnknown` (see [compiler integration](accel/compiler.md#step-2-compile-the-effect)) |
| `execute(symbols)` | look up textures, rebuild the framebuffer if the target changed, record a `RenderCommandBuffer`, translate, submit |

### Synchronisation: the semaphore chain

There is no barrier derivation. Passes chain binary semaphores through `SymbolizedResource::barriers` on the resource they write. From [`PostProcessPass::execute`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render.Subpass/Impl/PostProcessPass.cpp):

```cpp
batch->_tmpWaits.append_range(
	reinterpret_cast<Vector<VkSemaphore>&>(sceneColorRes->barriers)
);
for (auto i = batch->_tmpWaitFlags.size(); i < batch->_tmpWaits.size(); ++i) {
	batch->_tmpWaitFlags.emplace_back(VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);
}
batch->_tmpSignals.push_back(_tmpSignal);

sceneColorRes->barriers.clear();
sceneColorRes->barriers.emplace_back(_tmpSignal.operator VkSemaphore());
```

The target seeds `scene::color` with the swapchain's image-available semaphore. Each pass waits on what is there, signals its own semaphore and leaves only that one. `RenderTarget::finish` presents while waiting on whatever is left. Image layout transitions are written by hand inside `lambda` commands (`DummyProvider` moves `scene::color` from `eUndefined` to `eColorAttachmentOptimal`; `TmpEndPass` moves it to its target layout).

`VkNativeBatch::commit` also creates a fence, submits, and **waits for the fence** before returning (marked `Warning: Dummy`). Every pass therefore runs CPU-synchronously, so the semaphore chain mostly documents intent.

### Commands and translation to Vulkan

A subpass records into a [`RenderCommandBuffer`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render.Command/RenderCommandBuffer.cpp): a singly linked list of `RenderCommand` objects placed in `std::pmr::monotonic_buffer_resource` pages by `RenderCommandAllocator`. Each command calls back into a [`RenderCommandTranslator`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render.Command/RenderCommandTranslator.hpp) with its own type (double dispatch again). The only translator is [`VkRCmdTranslator`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Driver.Vulkan/VkRCmdTranslator.cpp); it records into one `AccelCommandBuffer` from the graphics queue's pool and collects bindings in a scoped resource table.

| Recording call | Vulkan effect |
|----------------|---------------|
| `begin()`, `end()` | begin and end the command buffer |
| `beginAccelPass({ pass, framebuffer })`, `endAccelPass()` | `vkCmdBeginRenderPass`, `vkCmdEndRenderPass` |
| `beginSubPass()`, `endSubPass()` | nothing |
| `nextSubPass()` | `vkCmdNextSubpass` (inline) |
| `bindGraphicsPipeline(p)` | bind pipeline; makes it the active pipeline of the resource table |
| `bindComputePipeline(p)` | records, but translation asserts the pipeline is a `VkGraphicsPipeline` |
| `bindTexture`, `bindTextureSampler`, `bindStorage`, `bindUniform` (by `SymbolId`) | stored in the resource table, written at the next draw |
| `bindIndexBuffer`, `bindVertexBuffer` | `vkCmdBindIndexBuffer`, `vkCmdBindVertexBuffers` (binding 0) |
| `drawMesh`, `drawMeshIdx`, `drawStaticMesh(Idx)` | commit descriptor sets if dirty for the active layout; draw with counts **times 3** (triangles assumed) |
| `drawDispatch(instances, firstInstance, vertices, firstVertex)` | always commit descriptor sets; draw with the raw counts |
| `lambda(fn)` | call `fn(AccelCommandBuffer&)` directly: the escape hatch for barriers, copies, push constants |
| `bindStaticMesh`, `bindSkeletalMesh`, `drawSkeletalMesh`, `bind(ResourceTable)`, `attach` | no-ops on the Vulkan side |

Resource ids are the shader's binding ids as `lang::SymbolId`. A pass walks the compiled pipeline's binding layout and binds by id, for example `"color-tex-0"` in `PostProcessPass`. Which id lands in which set and binding is decided by the [Accel layout pass](accel/ir.md), not by the graph.

The translator returns a `NativeBatch`. Passes cast it to `VkNativeBatch`, add the wait and signal semaphores, and call `commitAndDispose()`.

### The scene mirror

Subpasses reach the render-side scene through the `scene::view` symbol:

```cpp
auto sceneViewRes = symCtx_.getImportSymbol(makeSceneViewSymbol());
auto sceneView = sceneViewRes->load<smr<const graphics::scene::SceneView>>();

const auto sys = sceneView->getRenderSceneSystem();
sys->getRegistry().forEach<graphics::scene::StaticGeometryModel>(/* ... */);
```

`MatTestPass` batches `StaticGeometryModel`s by material effect this way and binds the scene resource pool's instance, light and shadow buffers. `TmpDirectionalShadowPass` picks up the `DirectionalLightModel`.

[`SceneWalker`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render.Graph.Scene/SceneWalker.cpp) in `Engine.Graphics.Render.Graph.Scene` was meant to do this with walk filters (`FrustumCullingFilter`) and hook filters (`ModelTypeFilter`). It is not used: its traversal calls are commented out, `FrustumCullingFilter::operator()` always returns `false`, and the only caller is a commented-out block in `DepthPrePass::iterate`. There is no culling.

### The graph the engine runs

`TestRenderer::makeCompileGraph` builds the scene graph. Passes marked "off" are created but their insert lines are commented out.

| # | Pass | Reads | Writes | Notes |
|---|------|-------|--------|-------|
| 1 | `TmpBrdfLutPass` | | `BrdfLut` (exposed) | 512x512 `R16G16Sfloat`; renders once, later frames only re-expose the texture |
| 2 | `TmpBrdfPrefPass` | `scene::view` | `BrdfPrefilter` (exposed) | |
| 3 | `TmpBrdfIrradPass` | `scene::view` | `BrdfIrradiance` (exposed) | |
| 4 | `DummyProvider` | `scene::color` | `scene::depth` (exposed) | creates the depth texture at the colour extent; transitions colour to attachment layout |
| 5 | `DepthPrePass` | `scene::depth` | `scene::depth` | begins its render pass and binds the pipeline; the draw is commented out |
| 6 | `SkyBoxPass` | `scene::view`, `scene::depth` | `scene::color` | |
| 7 | `TmpDirectionalShadowPass` | `scene::view` | `DirectionalShadow` (exposed) | 2048x2048 `D32Sfloat` array, one layer per cascade |
| 8 | `MatTestPass` | `scene::view`, `scene::depth`, BRDF and shadow symbols | `scene::color` | forward material pass over static geometry |
| 9 | `TmpEndPass(eShaderReadOnlyOptimal)` | `scene::color` | `scene::color` | final layout so the UI can sample the viewport |
| off | `TriTestPass`, `PostProcessPass`, `Visualize`, `ReflowPass` | | | |

A barrier node sits before pass 1 and after pass 9. Order in the table is execution order; nothing else enforces that a reader comes after its writer.

## Configuration

There is none beyond code. The renderer name is chosen by whoever creates the target: `Viewport::setViewportTarget("Test-Renderer", ...)` in the editor scene panel, `WindowManager::requestWindow(..., "Editor-Renderer", ...)` in `EditorInit`. The number of render passes per target (one or two) comes from the target's on-the-flight setting.

## Debugging

| Symptom | Where to look |
|---------|---------------|
| Debugger stops in `RenderGraphCompiler::operator()` | a target symbol is not an expected provision of the compile graph |
| Crash in `Renderer::update` on a new renderer | the compile graph has no expected provision, so the runtime graph is null |
| `assert(_compiled.pipeline)` in a pass's `execute` | the effect failed to compile in `resolve`; the reason is logged by the Accel compiler. The flag is now `eFailed` and the pass never retries |
| `Tried to bind target ... while implicit rebinding is not allowed.` | `bindTarget` without `unbindTarget` first |
| Null dereference after `getImportSymbol` | the producing pass runs later, or never exposes the symbol; exposed symbols only exist after the producer's first `execute` |
| `Tried to erase resource as export symbol, while subject is externaly owned.` or `invalid data state` | `eraseExportSymbol` on an exposed resource, or before `destroy<T>()` |
| Wrong image or validation layer layout errors | check the hand-written barriers in each pass's `lambda`; the graph tracks no layouts |

`DebugVisitor` (`Engine.Graphics.RenderGraph/Debug`) logs every node with its address. Nothing calls it except `test_graph_process` in the bundle's `test.cpp`, which is itself never called. To use it, construct one and pass it to `graph->update(visitor)`. No Vulkan debug labels are emitted, so in RenderDoc each pass shows up as its own submit.

## Limits and known issues

- **Linear and fixed.** The two renderers build a straight list. `Builder::eraseNode` panics. Pass order is the only dependency mechanism.
- **Selector visits nothing.** `SelectorNode::traverse` tests each child's mask against a local empty mask, so no child is ever visited.
- **Fan-in runs twice.** The phase visitors keep no visited set. Behind a `DivergeNode`, a `ConvergeNode` and everything after it run once per incoming branch.
- **Declarations are dead.** `SubPass::setup` calls `declareOutputs`, `declareTransforms` and `declareInputs`, but the graph never calls `setup` (`//_subpass.setup();` in `SubPassNode`). `TmpDirectionalShadowPass` calls its own `setup` lazily from `iterate`. The registrations would be inert anyway (`registerImportSymbol` and `registerExportSymbol` return `false`), so the [Accel pass contract](accel/compiler.md#limits) has nothing to read.
- **No resource management.** No transient resources, no aliasing, no barrier or layout tracking. Each pass creates its textures, framebuffers and semaphores itself. `RenderPass::alloc`, `realloc` and `free` are stubs that return `true`. `RuntimeGraph::aggregateProvisions` and `aggregateRequirements` return empty lists. `InjectGraphRegistry` is an empty class.
- **One submit and one CPU wait per pass.** `VkNativeBatch::commit` waits on a fence after every submit. A frame with nine passes stalls the CPU nine times.
- **Graphics queue only.** No compute pipelines, no async compute, no second queue.
- **Per-pass-instance pipelines.** Each runtime graph owns new subpass objects, so a target with two in-flight passes builds every effect and pipeline twice.
- **`destroy()` assumes `execute()` ran.** Several passes dereference their framebuffer, sampler or texture in `destroy()` without a null check; destroying a pass that never executed can crash.
- **Downcast.** `SubPassNode` treats the root `SymbolContext` as a `ScopedSymbolContext`. It works because the derived class adds no members, but it is undefined behaviour.

The planned replacement (declared passes, derived barriers, aliasing, async compute) is S14, tracked in [#94](https://github.com/Heliogrim/Heliogrim-Engine/issues/94) and the [render graph v2 work packages](../plan/work/render-graph-gpu-driven.md).

## Changing it

### Add a subpass

1. Create `Impl/MyPass.{hpp,cpp}` in `Engine.Graphics.Render.Subpass` (a new file needs a CMake reconfigure). Derive from `SubPass`, or from `MeshSubPass` for geometry.
2. Implement the three phases. Follow `PostProcessPass` as the smallest full example:
   - `iterate`: build the effect once with `makeIrIntermediate` and the pass with `VkAccelerationPassFactory::buildGraphicsPass`.
   - `resolve`: compile once while `_compiled.flag == EffectCompileResultFlag::eUnknown`.
   - `execute`: look up resources with the `make*Symbol()` functions, rebuild the framebuffer when the bound texture changed, record, translate with `VkRCmdTranslator`, chain the semaphore of the resource you write, `commitAndDispose()`.
3. If the pass produces a resource others read, keep a `SymbolizedResource` member, set `symbol` and `owned = true`, `create<T>` it on first use and `store<T>` later, then `eraseExposedSymbol` and `exposeSymbol` it each frame (see `TmpBrdfLutPass` or `DummyProvider`). A new shared symbol goes into `Engine.Graphics.Render.Predefined/Symbols` as a function-local static.
4. Release everything in `destroy()`. `SubPassNode`'s destructor calls it. Null-check members that `execute` creates.
5. Insert the pass into a renderer's `makeCompileGraph` with a `CompileSubPassNode` whose builder allocates `SubPassNode<MyPass>`. Place it after every pass whose output it reads.

### Add a node type or a phase

A new node type needs: the class (`Node/Runtime` or `Node/Compile`), a forward declaration in `__fwd.hpp`, a `Visitor` overload, and handling in `BuilderVisitor`, `BLinkVisitor`, `FLinkVisitor`, `CompileVisitor` and `DebugVisitor`. Missing overloads fall back to `operator()(cref<Node>)`, which in the link visitors means the link is silently not set.

### Tests

`Heliogrim-Engine.Graphics.RenderGraph.Test` (`Graph.cpp`) covers only the minimal graphs: default begin-to-end links, forward and reverse visits, provision and requirement de-duplication, and the anchor component. The builder, the compiler, the symbol context and every subpass are untested. The [GPU test harness](gpu-test-harness.md) records `RenderCommandBuffer`s through `VkRCmdTranslator` without a graph, which makes it the place for a pass-level test. Rendering is otherwise checked only by running the editor.
