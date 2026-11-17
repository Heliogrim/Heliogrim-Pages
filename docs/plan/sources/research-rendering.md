# Research: rendering core

**Status**: <span class="hg-status summary">sources</span>. Collected 2026-11-07 by a research agent for the battle plan. Claims are marked verified or unverified; nothing here is a decision.

**Method caveat.** Web fetch of JCGT/arXiv pages was unreliable in this session (empty or wrong pages). Only items tagged `verified` were read from an opened page. Everything tagged `unverified` comes from search-result summaries or from the agent's prior knowledge and must be re-opened before it is cited in a decision. Hardware numbers are deliberately omitted where not read. Slides and talks marked unverified are listed by title, authors, venue and year as pointers; URLs are the canonical landing pages as best known.

Legend: `verified` = page opened this session. `unverified` = summary only / recalled.

## 1. GPU-driven rendering, visibility buffer, deferred texturing

State of the art:
- Cluster-based GPU culling (frustum, occlusion via previous-frame HZB, two-pass) with multi-draw-indirect is the baseline for AAA engines. `unverified`
- Visibility buffer stores triangle/instance IDs per pixel, defers attribute fetch and shading; reduces overdraw bandwidth, simplifies MSAA-free shading. `unverified`
- Cost shifts to attribute interpolation and material evaluation in a compute/fullscreen pass; needs bindless resources and material binning (tile or per-material indirect dispatch). `unverified`
- Two-phase occlusion culling (cull with last frame's HZB, draw, rebuild HZB, re-test the rejected) is the standard fix for disocclusion. `unverified`
- Work graphs (D3D12) are not available in Vulkan 1.3 core; `VK_AMDX_shader_enqueue` is provisional. `unverified`

Sources:
- Haar, Aaltonen (both Ubisoft). "GPU-Driven Rendering Pipelines". SIGGRAPH 2015 Advances in Real-Time Rendering in Games course, Part II (Assassin's Creed Unity pipeline, then RedLynx clean-slate pipeline using async compute, indirect dispatch, multidraw). https://advances.realtimerendering.com/s2015/ . Timings/hardware not read (slides PDF not opened). `verified (abstract/landing page)` (via search summary of the course page)
- Burns, Hunt. "The Visibility Buffer: A Cache-Friendly Approach to Deferred Shading". JCGT 2(2), Aug 2013, pp. 55-69. https://jcgt.org/published/0002/02/04/ . Bandwidth numbers not read. `verified (abstract/landing page)` (bibliographic data via search; JCGT page fetch returned empty)
- Schied, Dachsbacher. "Deferred Attribute Interpolation for Memory-Efficient Deferred Shading". HPG 2015. Measured: memory/bandwidth with MSAA. `unverified`
- Wihlidal. "Optimizing the Graphics Pipeline with Compute". GDC 2016 (Frostbite). `unverified`
- Engel (Confetti). "Triangle Visibility Buffer 2.0". Conference talk and The Forge open source, 2021-2023. `unverified`

Applicability to Heliogrim:
- Visibility buffer needs only: 64-bit or 2x32 R-target, bindless buffers (Vulkan 1.2 descriptor indexing, available) and compute shading; all expressible in an SPIR-V-targeting IR if the IR supports runtime-sized descriptor arrays and `nonuniformEXT`.
- Material binning by material ID is a natural fit for the existing effect/pipeline compile model: one compute permutation per effect.
- CPU role shrinks to scene/instance upload; fibers are only useful for the upload and culling-data job, not draw submission.
- Decide early whether the IR must express indirect dispatch and atomics on structured buffers; these are prerequisites.

Open risks / measure:
- Bandwidth and shading cost of VB vs classic deferred on target (non-console) GPUs, including 2x32 vs 64-bit atomic support (`shaderImageInt64Atomics`, hardware assumption).
- Derivative computation in compute (analytic UV gradients) vs quad-based; texture filtering quality.
- Alpha-tested geometry cost in the visibility pass.

## 2. Virtualized geometry, meshlets, mesh shaders

State of the art:
- Nanite: hierarchical cluster DAG (about 128 triangles per cluster), error-driven LOD with crack-free grouping, streaming of pages, hardware raster for large triangles and software compute raster for tiny ones, visibility buffer output. `unverified` (SIGGRAPH 2021, Karis, Stubbe, Wihlidal)
- Nanite quoted data rates: about 9 B/tri in memory, 5.6 B/tri on disk (per DGF paper summary). `unverified`
- DGF (AMD, HPG 2024): dense geometry format for meshlets, hardware-friendly, ray-tracing compatible random access; compression comparable to Nanite. `unverified`
- Kuth et al., "Towards Practical Meshlet Compression" (arXiv 2024; VMV 2024 and best-paper status not confirmed): GPU mesh shader decompression, 16:1 index-buffer compression versus vertex pipeline, crack-free quantization; journal extension "Real-time meshlet decompression" (Computers & Graphics 131, 2025) reports 9.5 bits per triangle with generalized triangle strips. `unverified`
- Mlakar, Steinberger, Schmalstieg. "End-to-End Compressed Meshlet Rendering". Computer Graphics Forum 43(1), 2024. Same compressed format in storage and GPU memory, decoded in mesh shaders; compared against commonly used compressed meshlet formats. The "laced wires smallest memory" and "Nanite-style" claims were not confirmed by the abstract. `unverified` (details), paper verified
- Mesh shaders are standardised as `VK_EXT_mesh_shader` (2022); available on NVIDIA Turing+, AMD RDNA2+, Intel Arc. Hardware assumption. `unverified`
- Open source references: meshoptimizer (Arseny Kapoulkine, meshlet builder and cone culling), Nanite-like clones (e.g. Nabla, The Forge) of varying quality. `unverified`

Sources:
- Karis, Stubbe, Wihlidal (all Epic). "A Deep Dive into Nanite Virtualized Geometry". SIGGRAPH 2021 "Advances in Real-Time Rendering in Games" course, Part I, 10 Aug 2021. https://advances.realtimerendering.com/s2021/ . Slides PDF is 16 MB, not opened; the per-triangle byte figures above remain unchecked. `verified (abstract/landing page)`
- Kuth, Oberberger, Kawala, Reitter, Michel, Chajdas, Meyer. "Towards Practical Meshlet Compression". arXiv 2404.06359 (v1 9 Apr 2024, v2 13 Aug 2024), 8 pages. Measured (abstract): 16:1 index-buffer compression vs vertex pipeline; 15.5 M triangles decompress and render in 0.59 ms on AMD Radeon RX 7900 XTX. VMV 2024 venue not stated on arXiv page. `verified (abstract/landing page)`
- Mlakar, Steinberger, Schmalstieg. "End-to-End Compressed Meshlet Rendering". CGF 43(1), e15002, Jan 2024, doi 10.1111/cgf.15002 (open access). `verified (abstract/landing page)` (via search summary)
- Barczak, Benthin, McAllister (AMD). "DGF: A Dense, Hardware-Friendly Geometry Format for Lossily Compressing Meshlets with Arbitrary Topologies". PACMCGIT 7(3), Art. 46, Aug 2024, doi 10.1145/3675383; 128-byte blocks, up to 64 positions/64 triangles per block. `verified (abstract/landing page)` (via search summary)
- Khronos. `VK_EXT_mesh_shader`: device extension #329, revision 1 (2022-03-08), ratified; contributors NVIDIA, Valve, Intel, ARM, Qualcomm, Igalia, AMD. Page states no hardware requirements, so the GPU list above is not confirmed by it. https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_mesh_shader.html . `verified (full text)` (refpage)

Applicability to Heliogrim:
- Cluster DAG builder is an offline/import-time job: a natural fit for fibers and the asset pipeline (asset type `StaticGeometry` already exists in `Engine.Assets.Type`).
- Software rasterization of small triangles is a compute shader with 64-bit atomics; needs IR support for `uint64` and image/buffer atomics.
- Mesh shaders require the IR to model task/mesh stages and per-primitive outputs; compute-based fallback keeps portability.
- A minimal first target: static meshlets plus GPU culling, deferring the DAG/streaming part.

Open risks / measure:
- Cluster DAG build time and quality on the project's real assets; LOD error metric correctness.
- Software raster vs hardware raster crossover on target GPUs.
- Streaming and page residency complexity (largest engineering cost); decide scope before committing.
- Mesh shader availability on the minimum-spec GPU.

## 3. Render graphs / frame graphs

State of the art:
- Declarative pass setup, compile phase (cull unused passes, resolve dependencies, derive barriers/layout transitions, alias transient memory), execute phase. `unverified`
- Transient resource aliasing via lifetime intervals is the main memory win (Frostbite reported large savings). `unverified`
- Async compute scheduling requires queue-ownership transfer and cross-queue sync; the automatic scheduling problem is hard, most engines use hints. `unverified`
- Vulkan synchronization2 (core in 1.3) simplifies barrier derivation. `unverified`
- Open implementations: Granite (Hans-Kristian Arntzen) render graph, Unreal RDG (documented in UE docs), Diligent, Themaister blog describes barrier derivation. Pointers only. `unverified`

Sources:
- O'Donnell (Yuriy; Frostbite/EA, sole speaker per GDC Vault; "Barczak" in the original report is not supported). "FrameGraph: Extensible Rendering Architecture in Frostbite". GDC 2017. https://www.gdcvault.com/play/1024612/FrameGraph-Extensible-Rendering-Architecture-in . Slides (SlideShare, DICE): frame graph, transient resource system, async compute, automated ESRAM aliasing; no numbers read. `verified (abstract/landing page)`
- Epic. "Render Dependency Graph (RDG)" documentation. https://dev.epicgames.com/documentation/ . `unverified`
- Khronos. "Synchronization Examples" Vulkan Guide / synchronization2 proposal. `unverified`

Applicability to Heliogrim:
- Graph declaration maps well onto existing effect/pipeline compile abstractions: passes declare resource usage; the IR's reflection (bindings, stage usage) can feed automatic barrier derivation.
- The graph compile step is CPU work and fits a fiber job; recording per-pass command buffers in parallel fibers is the main CPU win.
- Start with single queue + aliasing; async compute later as an opt-in per-pass hint.
- Resource usage declarations should be derived from shader reflection to avoid mismatches.

Open risks / measure:
- Barrier count and GPU idle with auto-derived vs hand-tuned barriers.
- Aliasing correctness under resize/format changes.
- Graph rebuild cost per frame vs caching.

## 4. Shadows

State of the art:
- Virtual shadow maps (UE5): very large virtual resolution (16k x 16k per light), page-based allocation driven by screen-space need, cached across frames, per-page invalidation. `unverified`
- Cascaded shadow maps remain the baseline for sun light; stable cascades, texel snapping, PCF/PCSS filtering. `unverified`
- Hardware ray-traced shadows with 1 spp plus temporal/spatial denoise (e.g. NVIDIA SVGF, NRD) for soft area-light shadows. `unverified`
- Screen-space contact shadows (short ray march in depth buffer) fix near-contact leaks cheaply. `unverified`

Sources:
- Epic. "Virtual Shadow Maps" documentation, UE5. https://dev.epicgames.com/documentation/ . Also Karis et al., "Lumen and Nanite" talks, SIGGRAPH 2021/2022. `unverified`
- Schied, Kaplanyan, Wyman, Patney, Chaitanya, Burgess, Liu, Dachsbacher, Lefohn, Salvi. "Spatiotemporal Variance-Guided Filtering: Real-Time Reconstruction for Path-Traced Global Illumination". HPG 2017, doi 10.1145/3105762.3105770, HPG 2017 best paper. Measured (abstract): about 10 ms at 1920x1080 on "modern graphics hardware" (GPU model not read), 1 path per pixel. `verified (abstract/landing page)`
- Dundr (NVIDIA). "NRD" project documentation. `unverified`
- Dimitrov. "Cascaded Shadow Maps". NVIDIA white paper, 2007. `unverified`

Applicability to Heliogrim:
- Start with stable CSM + PCF; the pass is cheap in a render graph and trivially expressed in the IR.
- VSM needs a visibility/page feedback pass and compute page allocation; depends on the GPU-driven pipeline (topic 1) and a cluster renderer to be affordable.
- RT shadows need `VK_KHR_ray_query`; make it optional.
- Contact shadows are a small compute shader, good early win.

Open risks / measure:
- Page-pool memory budget and invalidation cost for dynamic scenes.
- Denoiser quality and cost; RT availability on min-spec.

## 5. Global illumination, multi-bounce

State of the art:
- Lumen (UE5): screen-space probes + radiance cache, SDF/mesh-card tracing, software or hardware RT, lots of heuristics. `unverified` (Wright et al., SIGGRAPH 2022)
- DDGI (Majercik et al. JCGT 8(2), 2019): irradiance probe grid updated with ray tracing, visibility-aware filtering, multi-bounce from probe feedback. `unverified`
- ReSTIR DI (Bitterli et al., SIGGRAPH 2020), ReSTIR GI (Ouyang et al., HPG 2021), ReSTIR PT (Lin et al., SIGGRAPH 2022): resampled importance sampling with temporal/spatial reuse; large variance reduction at high cost, requires RT. `unverified`
- Radiance cascades: Sannikov 2023, Path of Exile 2 uses it for screen-space illumination (game claim not re-checked). Never submitted to a journal (README says it uses the JCGT template but was not published there); PDF on GitHub (https://github.com/Raikiri/RadianceCascadesPaper). `verified (abstract/landing page)` (repo README read; PDF and year not shown on page)
- Holographic Radiance Cascades for 2D GI. Freeman, Sannikov, Margel. arXiv 2505.02041, submitted 4 May 2025, 9 pages. Claimed visually indistinguishable from 2D reference; 1.85 ms at 512x512 and 7.67 ms at 1024x1024 on an RTX 3080 Laptop GPU. 2D only. `verified (abstract/landing page)`
- Split Radiance Cascades: real-time GI via sparse radiance probes. Freeman, Sannikov, Pitt-Francis. arXiv 2607.20384, v1 22 Jul 2026, v2 11 Oct 2026, 13 pages. Extends RC to 3D world space with sparse hashmap probes plus "ray splitting". ID and date confirmed to exist. `verified (abstract/landing page)`
- Surfel GI: EA SEED "Global Illumination Based on Surfels", SIGGRAPH 2021 (Halen, Wright et al.), used in Frostbite. `unverified`
- Neural radiance caching: Müller et al. "Real-time Neural Radiance Caching for Path Tracing", SIGGRAPH 2021. Needs tensor-core-class hardware for real time. `unverified`

Sources (primary):
- Majercik, Guertin, Nowrouzezahrai, McGuire. "Dynamic Diffuse Global Illumination with Ray-Traced Irradiance Fields". JCGT 8(2), 2019. https://jcgt.org/published/0008/02/01/ . Abstract: visibility-aware moment-based interpolant, ray-traced probe update; published 6 May 2019, pp. 1-30; no hardware figures in the abstract. `verified (abstract/landing page)` (NVIDIA Research page via search; JCGT fetch still empty)
- Bitterli, Wyman, Pharr, Shirley, Lefohn, Jarosz. "Spatiotemporal reservoir resampling for real-time ray tracing with dynamic direct lighting". ACM TOG 39(4), Art. 148, SIGGRAPH 2020, doi 10.1145/3386569.3392481. Measured (per search summary of paper): 3.4 M dynamic emissive triangles in under 50 ms per frame at 1920x1080; GPU model not read. `verified (abstract/landing page)`
- Ouyang, Liu, Kettunen, Pharr, Pantaleoni (NVIDIA). "ReSTIR GI: Path Resampling for Real-Time Path Tracing". CGF 40(8), 17-29, 2021 (HPG 2021 issue), doi 10.1111/cgf.14378. MSE improvement 9.3x to 166x at 1 spp. `verified (abstract/landing page)`
- Lin, Kettunen, Bitterli, Pantaleoni, Yuksel, Wyman. "Generalized Resampled Importance Sampling". SIGGRAPH 2022. `unverified`
- Sannikov. "Radiance Cascades". 2023 (GitHub PDF). see above.
- Freeman et al. arXiv 2505.02041 and 2607.20384. see above.

Applicability to Heliogrim:
- Most hardware-agnostic candidates: probe grids (DDGI-like, optionally with SW tracing against a coarse SDF/voxel scene) and radiance cascades in screen space. Neither needs RT hardware.
- ReSTIR/NRC need ray queries or tensor hardware: treat as optional high tier.
- All are compute-heavy and rely on RW structured buffers, atomics and wave ops; check IR coverage of subgroup operations.
- Emissive geometry as GI light source implies an emissive light list or injection into probes (see topic 7).
- Choose by scene type: if the target is large open worlds (MMO vision, unverified), a world-space cache (probes/surfels/split RC) scales better than screen-space.

Open risks / measure:
- Light leaking and temporal lag of probe GI; update budget per frame.
- Screen-space RC misses off-screen light; measure artefacts on camera motion.
- Split RC is a very recent paper (2026), no independent implementations known; treat as research.
- Memory of world-space caches in streamed worlds.

## 6. Transparency / OIT

State of the art:
- Weighted blended OIT (McGuire, Bavoil, JCGT 2(2), 2013): single pass, fixed memory, approximate; quality depends on weight function. Title/venue verified; MSAA claim `unverified`
- Moment-based OIT (Münstermann, Krumpen, Klein, Peters, PACMCGIT/I3D 2018 "Moment-Based Order-Independent Transparency"): few moments per pixel, fixed memory, higher quality than WBOIT. `unverified`
- Per-pixel linked lists / A-buffer: exact, but unbounded memory and atomics; used where layer counts are small. `unverified`
- Hybrid: sorted/depth-peeled front layers for glass plus WBOIT for particles; shipped engines commonly sort per object and use WBOIT-like for particles. `unverified`
- Visibility-buffer or Nanite pipelines still shade opaque only; transparency stays forward-rendered. `unverified`

Sources:
- McGuire, Bavoil. "Weighted Blended Order-Independent Transparency". JCGT 2(2), 18 Dec 2013, pp. 122-141. https://jcgt.org/published/0002/02/09/ . `verified (abstract/landing page)` (via Semantic Scholar abstract; JCGT fetch empty)
- Münstermann, Krumpen, Klein, Peters. "Moment-Based Order-Independent Transparency". Venue correction: Proc. ACM Comput. Graph. Interact. Tech. 1(1), Art. 7, 2018 (presented at I3D 2018, not HPG), doi 10.1145/3203206; author version https://momentsingraphics.de/I3D2018.html . `verified (abstract/landing page)`
- Yang et al. "Real-time Concurrent Linked List Construction on the GPU". EGSR 2010. `unverified`
- Peters, Klein. "Moment Shadow Mapping". I3D 2015 (basis of MBOIT). `unverified`

Applicability to Heliogrim:
- WBOIT is two attachments plus a composite pass: tiny to implement and expressible in plain blend state.
- MBOIT needs extra moment render targets and floating-point atomics-free additive blend; feasible.
- Per-pixel lists need atomic counters and a sort pass in compute: IR must support them; keep as later option.
- Material system must expose a blend/transparency class per effect.

Open risks / measure:
- Visual quality on glass and layered UI-in-world; weight function tuning.
- Interaction with TAA/upscaling (transparent motion vectors).

## 7. Materials and emissive

State of the art:
- Disney principled BRDF (Burley, SIGGRAPH 2012 course "Physically Based Shading at Disney") remains the de-facto parameterisation, glTF `KHR_materials_*` extensions follow it. `unverified`
- Layering: Weidlich-Wilkie "Arbitrarily Layered Micro-Facet Surfaces" (GRAPHITE 2007); Belcour "Efficient Rendering of Layered Materials using an Atomic Decomposition with Statistical Operators" (SIGGRAPH 2018); Autodesk Standard Surface and OpenPBR (ASWF, 2023-2024) as interchange specs. `unverified`
- Recent work on layered material evaluation (including positionless/"position-free" layering, Guo et al. SIGGRAPH Asia 2018 and later) was not verified here; exact title and venue for 2023+ papers unresolved. `unverified`
- Emissive as GI source: needs light sampling of emissive triangles (ReSTIR/NEE) or probe injection; emissive textures complicate importance sampling. `unverified`
- Material graphs compile to shaders (UE Substrate is the shipped layered system). `unverified`

Sources:
- Burley. "Physically Based Shading at Disney". SIGGRAPH 2012 course "Practical Physically Based Shading in Film and Game Production", notes v3 https://blog.selfshadow.com/publications/s2012-shading-course/burley/s2012_pbs_disney_brdf_notes_v3.pdf ; 2014 addendum exists (clearcoat GTR). `verified (abstract/landing page)`
- Weidlich, Wilkie. GRAPHITE 2007. `unverified`
- Belcour. "Efficient Rendering of Layered Materials using an Atomic Decomposition with Statistical Operators". ACM TOG 37(4), Art. 73, July 2018 (SIGGRAPH), doi 10.1145/3197517.3201289 (DOI from search, not opened). `verified (abstract/landing page)` (via search summary; no direct page opened)
- Academy Software Foundation. OpenPBR Surface specification. Repo https://github.com/AcademySoftwareFoundation/OpenPBR (subproject of MaterialX, Apache-2.0, no tagged release); spec https://academysoftwarefoundation.github.io/OpenPBR/ (spec page itself not opened). `verified (abstract/landing page)`

Applicability to Heliogrim:
- The existing material prototype/effect split in `Engine.Graphics.Material` is compatible with a layered parameter model; the IR gets the layering as compile-time composition (function inlining), not runtime branches.
- Choose a small fixed layer count (base + clearcoat + sheen optional) for real-time; full arbitrary layering is unnecessary for v1.
- Emissive: store emissive intensity separately so GI can consume it (probe injection or emissive light list).
- Adopt glTF/OpenPBR parameter naming for import interoperability.

Open risks / measure:
- Permutation explosion with layers; shader compile time.
- Energy conservation between layers under cheap approximations.
- Emissive light-list size and update cost.

## 8. Post-processing, tone mapping, HDR, upscaling

State of the art:
- Khronos PBR Neutral: input linear Rec.709, small Fresnel offset (F90 = 0.04), highlight compression above Ks = 0.76 with desaturation Kd = 0.15, no hue shifts, analytic inverse, output clamped to [0,1]; designed so base colour is preserved for 0.08-0.8 channels; no gamut mapping, sRGB output only for now. `verified` (https://github.com/KhronosGroup/ToneMapping/tree/main/PBR_Neutral , read this session; release year not stated on the page)
- ACES (RRT+ODT) is widespread but has hue skew; fitted approximations (Narkowicz, Hill) are common. `unverified`
- AgX (Troy Sobotka; in Blender 4.0): neutral display transform with desaturated highlights. `unverified`
- HDR output on Windows: scRGB (`VK_FORMAT_R16G16B16A16_SFLOAT` with `VK_COLOR_SPACE_EXTENDED_SRGB_LINEAR_EXT`) or HDR10 (`A2B10G10R10` + `VK_COLOR_SPACE_HDR10_ST2084_EXT`); requires `VK_EXT_swapchain_colorspace`. Windows tooling: Auto HDR and SDR white level handling are OS dependent. `unverified`
- Temporal upscaling: TAAU, UE TSR, FSR 2/3 (open, cross-vendor), DLSS (NVIDIA only), XeSS (cross-vendor). All need motion vectors, jittered projection, depth, and exposure. `unverified`
- Colour grading via 3D LUT (32^3 or 64^3), applied after tone mapping or in a log space. `unverified`

Sources:
- Khronos. "PBR Neutral Tone Mapper". https://github.com/KhronosGroup/ToneMapping . `verified`
- AMD GPUOpen. "FidelityFX Super Resolution 2" page. https://gpuopen.com/fidelityfx-super-resolution-2/ . Requires depth, color, velocity at render resolution; reactive mask and exposure optional; DX12 and Vulkan; MIT licence, v2.2.2; page says FSR 3/4 supersede it. Measured: Quality mode 4K under 1.3 ms on RX 6800 XT (under 1.9 ms RX 6700 XT, under 2.4 ms RX 5700 XT); Ryzen 9 5900X, Win 11, DX12. Jitter not mentioned on the page. `verified (full text)`
- Karis. "High Quality Temporal Supersampling". SIGGRAPH 2014 Advances. `unverified`
- Khronos. Vulkan `VK_EXT_swapchain_colorspace`: instance extension #105, revision 5, depends on VK_KHR_surface; adds EXTENDED_SRGB_LINEAR_EXT, HDR10_ST2084_EXT and others; no OETF applied for non-sRGB spaces. https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_swapchain_colorspace.html . `verified (full text)`. `VK_EXT_hdr_metadata` `unverified`
- Narkowicz. "ACES Filmic Tone Mapping Curve". 2016 (blog, pointer only). `unverified`

Applicability to Heliogrim:
- A post-process chain of fullscreen/compute passes in the render graph is straightforward; tone mapping is a pure function, easy in the IR.
- Pick PBR Neutral or AgX for default (no ACES licensing/appearance baggage); keep the curve behind a stable effect so it is swappable.
- Swapchain format choice must be a runtime capability query; support SDR sRGB fallback.
- Upscaling: design the pipeline to produce motion vectors and jitter from day one even if no upscaler is integrated; FSR is the portable first integration. Integration needs a vendor SDK in a Vulkan context (build and licensing check).

Open risks / measure:
- HDR swapchain behaviour on the target Windows versions and drivers; paper-white calibration.
- Motion-vector correctness for skinned/transparent objects.
- Ghosting and image quality with TAA vs upscalers on UI and particles.

## Cross-cutting prerequisites for the IR
- 64-bit integer and atomics, subgroup ops, bindless / runtime arrays, indirect dispatch, mesh/task stages, ray query (optional), structured buffers. Each rendering topic above depends on a subset; list them before IR design freezes.

## Source reliability summary
- Verified (first pass): Khronos PBR Neutral README.
- Verified (2026-11-07 pass, abstract/landing level unless noted): all bibliographic entries in the Verification pass section below. Full text opened only for the Vulkan refpages and the FSR 2 page. Treat design claims (state-of-the-art bullets, byte rates, hardware lists) as still `unverified` unless a source line above says otherwise.
- Still unverified: Weidlich-Wilkie, Karis TAA, Wihlidal, Engel, Schied-Dachsbacher, Lumen/surfel/NRC, UE docs, NRD, Narkowicz, VK_EXT_hdr_metadata. JCGT page fetches returned empty twice; JCGT entries were confirmed via search summaries instead.

## Verification pass (2026-11-07)

Level key: full = page opened and read; abstract = landing page or abstract (fetched, or via search summary where noted).

| Source | Status | URL |
|---|---|---|
| Nanite deep dive (Karis, Stubbe, Wihlidal) | abstract | https://advances.realtimerendering.com/s2021/index.html |
| FrameGraph (O'Donnell only; author corrected) | abstract | https://www.gdcvault.com/play/1024612/FrameGraph-Extensible-Rendering-Architecture-in |
| DDGI (Majercik et al.) | abstract (search) | https://research.nvidia.com/publication/2019-05_dynamic-diffuse-global-illumination-ray-traced-irradiance-fields |
| Radiance Cascades (Sannikov) | abstract (repo README) | https://github.com/Raikiri/RadianceCascadesPaper |
| Holographic RC, arXiv 2505.02041 | abstract (fetched) | https://arxiv.org/abs/2505.02041 |
| Split RC, arXiv 2607.20384 (exists, 22 Jul 2026) | abstract (fetched) | https://arxiv.org/abs/2607.20384 |
| WBOIT (McGuire, Bavoil) | abstract (search) | https://jcgt.org/published/0002/02/09/ |
| Visibility Buffer (Burns, Hunt) | abstract (search) | https://jcgt.org/published/0002/02/04/ |
| GPU-Driven Rendering Pipelines (Haar, Aaltonen) | abstract (search of course page) | https://advances.realtimerendering.com/s2015/ |
| MBOIT (venue corrected to PACMCGIT 1(1) / I3D 2018) | abstract (search) | https://dl.acm.org/doi/10.1145/3203206 |
| Kuth et al., arXiv 2404.06359 | abstract (fetched) | https://arxiv.org/abs/2404.06359 |
| DGF (Barczak et al.) | abstract (search) | https://dl.acm.org/doi/10.1145/3675383 |
| Mlakar et al. (CGF 43(1)) | abstract (search) | https://doi.org/10.1111/cgf.15002 |
| SVGF (Schied et al.) | abstract (search) | https://research.nvidia.com/labs/rtr/publication/schied2017spatiotemporal |
| ReSTIR (Bitterli et al.) | abstract (search) | https://doi.org/10.1145/3386569.3392481 |
| ReSTIR GI (Ouyang et al.; authors fully listed) | abstract (search) | https://doi.org/10.1111/cgf.14378 |
| Burley 2012 | abstract (search) | https://blog.selfshadow.com/publications/s2012-shading-course/ |
| Belcour 2018 | abstract (search) | https://doi.org/10.1145/3197517.3201289 |
| OpenPBR | abstract (repo README) | https://academysoftwarefoundation.github.io/OpenPBR/ |
| VK_EXT_mesh_shader | full (refpage) | https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_mesh_shader.html |
| VK_EXT_swapchain_colorspace | full (refpage) | https://docs.vulkan.org/refpages/latest/refpages/source/VK_EXT_swapchain_colorspace.html |
| AMD FSR 2 | full (page) | https://gpuopen.com/fidelityfx-super-resolution-2/ |

Corrections made: FrameGraph is a single-speaker talk (O'Donnell); MBOIT is PACMCGIT 1(1) presented at I3D 2018, not HPG; Kuth VMV 2024 / best-paper claim not confirmed (arXiv only); Mlakar is CGF 43(1) and its "laced wires" claim is unconfirmed; mesh-shader GPU support list is not on the Vulkan page; ReSTIR GI authors are Ouyang, Liu, Kettunen, Pharr, Pantaleoni.

Not verified: all state-of-the-art design claims (Nanite bytes per triangle, Frostbite aliasing savings, etc.), since slide decks and PDFs were not opened; JCGT hosts returned empty pages so JCGT entries rest on search summaries; sources listed under "Still unverified" above.
