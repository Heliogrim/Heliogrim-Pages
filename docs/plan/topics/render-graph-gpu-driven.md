# Render Graph v2, GPU-Driven Rendering and Large-World Coordinates

**Systems**: S07, S14, S15 · **Track** B · **Milestone** M2
**Status**: <span class="hg-status summary">plan</span>. Research from [rendering](../sources/research-rendering.md) sections 1 and 3 (unverified) and [runtime](../sources/research-runtime.md) section 3 (UE5 large-world docs verified).

## Target

A GPU-driven pipeline: the render scene is GPU-resident (instance, material and geometry tables), culling and draw generation run on the GPU (frustum, two-pass occlusion with the previous frame's HZB, meshlet cone and cluster culling), draws are indirect, and a visibility buffer defers material evaluation. The render graph declares passes; barriers, layout transitions and transient memory aliasing are derived from the ASL interfaces of the passes. World positions are double on the CPU and camera-relative floats on the GPU.

## Current state (checked 2026-11-07)

- `Engine.GFX.RenderGraph` (102 files, 6.2k lines) with a compile step; `Engine.GFX.Render.Subpass/Impl`: `DepthPrePass`, `MatTestPass`, `PostProcessPass`, `ShadowDirPass`, `SkyBoxPass`, `TriTestPass`, `VisualizePass`, plus mesh capture interfaces. Passes are hand-wired and record per object.
- `Engine.GFX.Render.Command`: `RenderCommandBuffer` with intrusive commands in a `pmr` arena, translated by `VkRCmdTranslator` into Vulkan secondary command buffers from per-queue pools (spinlock). No sub-range reuse.
- `Engine.GFX.Scene` and `Engine.Render.Scene`: CPU-side scene mirror with models per component type.
- `Engine.Driver.Vulkan` (1.9k lines): single queue family in practice; no bindless descriptor layout; no timeline semaphores noted.
- Transforms are float; `HierarchyComponent::getUniverseTransform` folds the chain in float.

## Research summary

- GPU-driven pipelines (Haar and Aaltonen 2015; Wihlidal 2016; unverified): cluster culling with multi-draw-indirect, two-phase occlusion with the previous HZB.
- Visibility buffer (Burns and Hunt 2013; Schied and Dachsbacher 2015; Engel 2021 to 2023; unverified): triangle and instance IDs per pixel; attribute fetch and shading deferred to a compute or full-screen pass; needs bindless, 64-bit or two-by-32-bit targets, analytic derivatives for texture filtering.
- Frame graphs (O'Donnell GDC 2017, single speaker; Unreal RDG; listing verified, slides not read): declare, compile (cull, order, derive barriers, alias transient memory by lifetime), execute; async compute scheduling is usually hint based; Vulkan synchronization2 simplifies barrier derivation.
- Large-world coordinates (verified): UE5 keeps doubles on the CPU and converts to camera-relative translated world space as early as possible so shaders stay float; the old tile-plus-offset scheme lost precision at boundaries; LWC math in shaders is slower than float.

## Guidance

### S14 Render graph v2

- Pass declaration: `{ name, kind (graphics, compute, transfer, present), shader module (ASL), inputs, outputs, flags (async hint, persistent) }`. Inputs and outputs are read from the ASL interface (S11 exports them), so a hand-written mismatch is impossible; extra uses (indirect args, readbacks) are declared explicitly.
- Compile per frame but cache by a graph hash: culling of unused passes, topological order, barrier and layout derivation with synchronization2, transient aliasing by lifetime intervals in a pooled heap, queue assignment from hints with ownership transfers inserted.
- Execution records each pass on a fiber into its own primary command buffer (or a secondary per pass), then submits in order; timeline semaphores for cross-queue and cross-frame waits that complete into waitables (S02).
- Materials feed pass enablement through back-propagation (S16): the graph is composed by code with feature flags (the default pipeline), not edited in a UI.
- Editor composition (viewport widget inside a Reflow window) differs from game composition (3D primary, UI planes); keep UI embedding and colour correction as graph fragments.

### S15 GPU-driven renderer

- GPU tables: instances (transform as camera-relative float plus a cell-relative double on the CPU side), materials (parameter block offsets, feature bits), geometry (meshlet ranges, bounds, cones), lights. Updated by the scene mirror through persistent mapped upload rings.
- Culling pipeline: instance frustum and HZB test, meshlet cone and bounds test, indirect draw or dispatch argument generation; two-pass occlusion.
- Visibility pass writes `{ instance id, triangle id }`; a material classification pass bins pixels per material (tile lists); a resolve pass per material permutation computes barycentrics and analytic derivatives and shades into the G-buffer or directly.
- Bindless: one descriptor set with runtime arrays for textures, buffers and samplers; `nonuniformEXT` indexing; the IR must express it (S11).
- GPU minimum spec: decide it in this system's issue (descriptor indexing and 64-bit atomics are required; mesh shaders and ray query are optional with compute fallbacks).

### S07 Large-world coordinates

- `Engine.Math` gets `dvec3` and a `WorldPosition` type; transforms store a double translation and float rotation and scale; `getUniverseTransform` folds in double for translation.
- The render scene stores camera-relative float positions and rebuilds them when the camera origin moves by more than a threshold (origin rebasing per cell, S40).
- Physics (S34, Jolt double build or per-region base offset), audio and navigation read `WorldPosition`; the editor's gizmos (S44) operate in camera-relative space.

## Done when

- A 1M-instance test scene is culled and drawn by indirect draws from GPU tables; CPU time per frame for draw submission is near constant in instance count.
- Barriers and aliasing are derived; the validation layer reports no synchronisation errors across the test suite; transient memory drops measurably versus dedicated allocations.
- The visibility buffer resolves a scene with ten material permutations and matches the forward reference in the GPU harness.
- A test world 100 km from the origin renders without jitter; physics and audio positions match the render within tolerance.

## Open decisions

- Async compute from day one or hint-only later.
- Visibility buffer resolve into a G-buffer (deferred shading) or shading directly (forward from VB); the transparency and GI designs depend on it.
- Origin rebasing threshold and its interaction with streaming cells.
