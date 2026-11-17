# Research: world, weather, fluids, terrain

**Status**: <span class="hg-status summary">sources</span>. Collected 2026-11-07 by a research agent for the battle plan. Claims are marked verified or unverified; nothing here is a decision.

## Verification caveat (read first)

The first pass was from recall. A verification pass on 2026-11-07 (see the last section) opened abstract/landing/course pages (no full texts, PDFs skipped) and confirmed bibliographic data (title, authors, venue, year) for nearly all cited papers. Status levels: `verified (abstract/landing page)` = bibliographic data and abstract checked; **technique descriptions and all claims in the "State of the art" bullets remain `unverified` unless stated**, because no full text was read and no timings were collected. Corrections made in place: Sea of Thieves (SIGGRAPH 2018 Talk, not GDC), Niagara (GDC 2018 talk, speaker), Hillaire 2016 venue, Koschier author list, Nanite foliage version, Frostbite terrain title. Numbers (ms, resolutions) are deliberately omitted; the only figure found is Schneider 2015's stated 2 ms GPU budget (course page, hardware not stated there). Everything must still be re-measured on Heliogrim's target tier.

Hardware assumption flag (applies to all): published timings are mostly on PS4/XB1-class or desktop 2015-2023 GPUs with async compute; Heliogrim's Vulkan target tier is not stated here and every timing must be re-measured on it.

---

## 1. Volumetric weather and sky

State of the art (all unverified):
- Sky/atmosphere: precomputed transmittance + multi-scattering LUTs, per-frame small sky-view LUT, camera-aligned aerial-perspective froxel volume (Hillaire 2020). Works from ground to space, cheap enough for fully dynamic time of day.
- Hillaire 2016 (Frostbite) is the earlier production system: physically based sky, clouds, and a unified volumetric framework (scattering/extinction volumes, froxel integration) that also feeds fog and particles.
- Clouds: raymarched density from tiled low-res 3D Perlin-Worley shapes + 3D curl/detail noise, a 2D weather map (coverage/type/precipitation), height-gradient by cloud type, temporal reprojection with quarter-res update (Schneider 2015 Horizon Zero Dawn; 2017 update with improved lighting, powder term, ambient).
- Nubis3 (2023, Guerrilla, Schneider): voxel-based, authored/simulated cloud volumes with improved performance and artist control; talk content for Nubis3 is recalled only roughly.
- Froxel volumetric fog: camera-frustum-aligned 3D texture, inject lights/shadows/media, integrate front to back, apply at composite (Wronski 2014 AC4; Hillaire 2015 Frostbite). Typical depth slices exponentially distributed; temporal jitter + reprojection.
- Precipitation: mostly screen/camera-local particle shells or GPU-instanced streaks plus a top-down depth/heightmap "precipitation occlusion" map around the camera so rain does not fall indoors; wetness driven by material parameters (roughness/darkening) and puddle masks.
- Wind: low-res global or cascaded vector field (noise + gust + storm vectors) sampled by foliage, cloth, particles, ocean; shipped games usually drive it by a scalar weather state + noise rather than fluid sim.
- Weather state machines in shipped games: authored states with blend weights and transitions (e.g. clear/overcast/rain/storm) driving cloud coverage, fog, wind, wetness, audio; open-world titles often use region-based weather maps. Specific shipped-game details: unverified, no source recalled with confidence.

Key sources (all unverified):
1. Hillaire, "Physically Based Sky, Atmosphere & Cloud Rendering in Frostbite", SIGGRAPH 2016, **Physically Based Shading in Theory and Practice course** (corrected: not Advances). https://www.ea.com/frostbite/news/physically-based-sky-atmosphere-and-cloud-rendering. verified (landing page: title/venue; cost figures not read).
2. Hillaire, "A Scalable and Production Ready Sky and Atmosphere Rendering Technique", EGSR 2020, Computer Graphics Forum 39(4), pp. 13-22, DOI 10.1111/cgf.14050. verified (abstract/landing page). Abstract states: no high-dimensional LUTs, new multiple-scattering approximation, scales from mobile to high-end PC, also useful for path tracing; timings not read (PDF skipped). https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.14050 ; https://sebh.github.io/publications/
3. Schneider, "The Real-Time Volumetric Cloudscapes of Horizon Zero Dawn", SIGGRAPH 2015 Advances course; Schneider, "Nubis: Authoring Real-Time Volumetric Cloudscapes with the Decima Engine", SIGGRAPH 2017; Schneider, "Nubis3: Methods (and madness) to model and render immersive real-time voxel-based clouds", SIGGRAPH 2023. verified (course pages): titles/speaker (Andrew Schneider, Guerrilla) match; 2015 title uses "Horizon: Zero Dawn" and the page states a 2 ms GPU budget (hardware not stated on the page); 2017 page lists weather simulation and Perlin-Worley noise generation; 2023 page confirms title and speaker only, abstract not read, so the "voxel-based, authored/simulated" description stays unverified. https://advances.realtimerendering.com/s2015/ , /s2017/ , /s2023/index.html
4. Wronski, "Volumetric Fog: Unified compute shader based solution to atmospheric scattering", SIGGRAPH 2014. Hillaire, "Towards Unified and Physically-Based Volumetric Lighting in Frostbite", SIGGRAPH 2015 Advances (title confirmed on the course page; gist there: cascaded extinction volume, particle voxelization, volumetric shadow map). Wronski: speaker/title/venue verified (Ubisoft Montreal, Advances Part II, Assassin's Creed IV); the course page says the talk analyses console performance but gives no numbers.
5. Bruneton & Neyret, "Precomputed Atmospheric Scattering", EGSR 2008; Bruneton, "A Qualitative and Quantitative Evaluation of 8 Clear Sky Models", IEEE TVCG 2017 (reference quality baseline).

Applicability to Heliogrim:
- Sky LUT pipeline is a good fit for the custom shader IR: small compute passes, fixed-size resources, no scene dependency; start here.
- Froxel volume doubles as shared infrastructure for fog, local volumetrics, particle lighting (topic 6) and underwater/ocean fog.
- Weather as a replicated, low-bandwidth state (seed + state + transition time) is MMO-friendly; the render side derives everything from it deterministically.
- Wind field as a server-authoritative scalar/vector function of (position, time, state) lets ocean (topic 3), sails and foliage agree.
- Clouds should be a shaded-by-time-of-day effect with a hard budget; consider quarter-res + reprojection from day one.

Open risks / measure:
- Cloud raymarch cost at target resolution, and shadow of clouds on ocean/terrain.
- LUT update cadence under fast time-of-day changes.
- Froxel memory with large view distance and many lights.
- Precipitation occlusion map cost and coherence with live terrain edits.

---

## 2. Volumetric fluids

State of the art (all unverified):
- FLIP/PIC hybrid: grid pressure solve + particle advection (Zhu & Bridson, "Animating Sand as a Fluid", SIGGRAPH 2005, introduced FLIP to graphics). APIC (Jiang et al., "The Affine Particle-In-Cell Method", SIGGRAPH 2015) reduces dissipation by storing affine velocity per particle; MPM (Stomakhin 2013) shares the transfer structure.
- PBF (Macklin & Müller, "Position Based Fluids", SIGGRAPH 2013): density constraints, GPU friendly, unconditionally stable, widely used for real-time (NVIDIA FleX lineage). Incompressibility is approximate.
- SPH survey: Koschier, Bender, Solenthaler, Teschner (verified four authors), "Smoothed Particle Hydrodynamics Techniques for the Physics Based Simulation of Fluids and Solids", Eurographics 2019 tutorial / STAR; follow-up 2022 version. Covers DFSPH, IISPH, boundary handling, neighborhood search.
- Eulerian smoke: Stam, "Stable Fluids", SIGGRAPH 1999, semi-Lagrangian advection + projection; remains the basis of GPU smoke. Dense grids scale cubically; sparse structures (OpenVDB, Museth 2013, ACM TOG; NanoVDB, Museth 2021, SIGGRAPH Talk, GPU read-only VDB) are used for storage/rendering rather than real-time solve.
- Engine products: Unreal Niagara Fluids (2D/3D grid gas, shallow-water) and Unity-ecosystem GPU fluid products (Zibra Liquids/Smoke, particle+grid on GPU). Both are bounded-domain, local effects; claims about their internals are unverified.
- Realistic for real-time at scale: local bounded-domain volumes (explosions, smoke, a splash) and particle liquids at roughly 10^5-10^6 particles; not world-scale water. World-scale water is height-field/FFT (topic 3) with local particle/grid inserts for splashes and wakes.
- Deterministic gameplay proxy: fluid visuals are client-only; gameplay queries (water height, flow, buoyancy, wind) use an analytic/low-res CPU field that the server can also evaluate. Specific shipped examples: unverified.

Key sources (unverified): Stam 1999; Zhu & Bridson 2005; Macklin & Müller 2013; Jiang et al. 2015; Koschier et al. 2019 (Eurographics tutorial) and 2022 follow-up; Museth 2013 "VDB: High-resolution sparse volumes with dynamic topology" (ACM TOG 32(3)); Museth 2021 "NanoVDB" (SIGGRAPH 2021 Talks); Bridson, "Fluid Simulation for Computer Graphics", CRC (book, not paper).

Applicability:
- Do not plan world-scale volumetric fluid; plan bounded-domain GPU effects as a particle/compute-stage feature on top of the topic 6 system.
- Keep gameplay water on the deterministic analytic path (topic 3); fluids are cosmetic coupling.
- A sparse brick/pool allocator (NanoVDB-like) is a generally useful GPU data structure for smoke, fog volumes and SDFs.
- Bounded 2D shallow-water grids are a cheap, plausible way to do local interactive water (wakes near ship, rivers).

Open risks / measure:
- Pressure-solve iteration counts vs. frame budget on target GPU; neighbor search cost for PBF/SPH.
- Memory of 3D grids at useful resolution; multi-GPU/low-end fallback.
- Divergence between client visuals and server proxy being visible to players.

---

## 3. Ocean

State of the art (all unverified):
- Tessendorf, "Simulating Ocean Water", SIGGRAPH 2001 course notes: spectral (Phillips/JONSWAP-type) height field evolved in frequency space by dispersion relation, inverse FFT per frame; choppy displacement via horizontal derivative FFT.
- Cascades: 3-4 FFT tiles at different world scales summed to avoid visible tiling; foam from Jacobian of the displacement (fold detection), accumulated and decayed.
- Gerstner waves: sum of a few analytic trochoidal waves, cheap, exactly evaluable on CPU/server with the same code as the shader; poorer visual realism, repeats.
- Sea of Thieves (Rare): **corrected**. "The Technical Art of Sea of Thieves" is a SIGGRAPH 2018 Talk (Talks-Sketches, 2 pages) by Nigel Ang, Andrew Catling, Francesco Cifariello Ciardi, Valentine Kozin, not a GDC 2018 talk and not Hamilton/Seifert. Per its abstract, the ocean is an implementation of Tessendorf's FFT technique (not a Gerstner sum as previously stated here); the talk also covers clouds without raymarching, rope physics and GPU surface fluid for incidental water. The CPU/ship-physics claim is unverified (not in the abstract). A separate GDC talk was not located. verified (abstract/landing page).
- Other shipped: Assassin's Creed IV/Black Flag (FFT ocean, Ubisoft talks), Horizon Forbidden West / Death Stranding water: details unverified.
- Deterministic server evaluation: the cleanest approach is an analytic sum (Gerstner or a small number of spectral components evaluated directly, no FFT) as a pure function of (x, y, t, seed); FFT on the client is then visual detail layered on top and not authoritative.
- Buoyancy: sample water height at several hull points (or voxelized hull) and apply spring/damping + displaced volume force; Gerstner horizontal displacement requires an iterative inverse to find height at a world xy.
- Shoreline: attenuate wave amplitude by depth, depth-based foam, depth-based refraction/colour; shallow-water-equation sim near shore is optional.
- Wakes/foam: height/foam decal texture advected around the camera or ships (render-to-texture, scrolling window), or a local shallow-water grid.
- Ocean/terrain coupling: shared depth/heightmap to clip ocean and drive shoreline effects; the terrain clipmap (topic 4) can supply depth.

Key sources (unverified): Tessendorf 2001; Phillips 1957 / Hasselmann et al. JONSWAP 1973 (spectra); Fournier & Reeves 1986 (Gerstner in graphics); Jeschke, Skrivan, Müller-Fischer, Chentanez, Macklin & Wojtan (not only Jeschke & Wojtan), "Water Surface Wavelets", SIGGRAPH 2018 (ACM TOG 37(4), art. 94); Jeschke et al. "Making Procedural Water Waves Boundary-aware", SCA 2020; Gamper, "Ocean Surface Generation and Rendering", thesis ETH 2018 (unverified existence); Ang et al., SIGGRAPH 2018 Talk, DOI 10.1145/3214745.3214820 (see above); Tessendorf notes verified as SIGGRAPH course notes (revised across 2001-2004 editions; hosted at jtessen.people.clemson.edu), Jeschke et al. author list corrected below; Kellomäki, "Rigid Body Dynamics of Boats / Water Interaction", GDC Vault (unverified).

Applicability:
- Split into authoritative analytic wave function (shared C++/shader IR source, deterministic floating point policy) and cosmetic FFT cascades.
- Put wave params into replicated weather state (wind speed/direction -> spectrum).
- Buoyancy sampling API should be a gameplay-layer service independent of rendering.
- Foam/wakes: window-scrolled render target keyed on player/ship, with wind field input.
- FFT is a clean compute workload; test the shader language/IR on it early (shared-memory butterflies).

Open risks / measure:
- Cross-platform floating-point determinism between server C++ and GPU shader results (only the analytic path needs to agree to within gameplay tolerance, not bitwise).
- FFT cascade cost vs. resolution; tiling visibility at distance.
- Wave height query throughput for many ships/objects on server tick.
- Shoreline wave breaking and terrain coupling are open-ended.

---

## 4. Terrain

State of the art (all unverified):
- Geometry clipmaps: Losasso & Hoppe, "Geometry Clipmaps: Terrain Rendering Using Nested Regular Grids", SIGGRAPH 2004; Asirvatham & Hoppe, "Terrain Rendering Using GPU-Based Geometry Clipmaps", GPU Gems 2 (2005). Nested rings of regular grids, heightmap in vertex texture, incremental toroidal updates.
- CDLOD: Strugar, "Continuous Distance-Dependent Level of Detail for Rendering Heightmaps", JGT 14(4) 2009. Quadtree over heightmap, per-vertex morph, simple GPU implementation.
- Virtual texturing for terrain: clipmap-style or sparse (Barrett, "Sparse Virtual Textures", GDC 2008; Mittring/Crytek, Far Cry 4 / UE Runtime Virtual Texture) for blended materials, decals, and baked splat results.
- Voxel / non-heightfield terrain: Marching Cubes (Lorensen & Cline 1987), Dual Contouring (Ju, Losasso, Schaefer, Warren, SIGGRAPH 2002), Transvoxel (Lengyel, PhD thesis 2010, seams between LODs), Surface Nets (Gibson 1998), Manifold Dual Contouring (Schaefer, Ju, Warren, 2007). Voxel terrain gives caves/overhangs and easy edits, costs memory and meshing time and has LOD seam complexity.
- Layered heightfields for multi-level (bridges, caves, interiors): stack of height intervals per cell (Bærentzen et al. style layered height fields; details unverified). Cheaper than voxels, limited topology.
- Live editing: edit height/material tiles via GPU compute (brush stamps, craters), propagate to physics heightfield and to clipmap/VT caches; dirty-tile invalidation.
- UE5: Landscape (component/section heightmap tiles with LOD) plus World Partition (grid-based cell streaming, one-file-per-actor) and Nanite Landscape in later 5.x; Far Cry / Dunia and Frostbite terrain details (tile/quadtree heightmap with virtual texture) are only partially recalled: unverified. No source opened for any.
- Streaming at MMO scale: tile grid keyed by integer cell coords, server owns authoritative height; clients stream from CDN/pak; edits as a replicated delta log per tile.

Key sources (unverified): Losasso & Hoppe 2004; Asirvatham & Hoppe 2005; Strugar 2009; Ju et al. 2002; Lengyel, "Voxel-Based Terrain for Real-Time Virtual Simulations", PhD thesis UC Davis 2010; Schaefer et al. 2007; Barrett 2008; Epic UE5 documentation for World Partition/Landscape; Frostbite terrain: Andersson, "Terrain Rendering in Frostbite Using Procedural Shader Splatting", SIGGRAPH 2007 course "Advanced Real-Time Rendering in 3D Graphics and Games" (title verified); Far Cry 5 terrain talk (GDC, details unverified).

Applicability:
- Recommend evaluating heightfield clipmap/CDLOD tile system as the base (matches ocean coupling, physics heightfield, edit tiles) with a separate voxel/mesh overlay system for caves/overhangs rather than a global voxel world.
- Tile = replication/streaming/edit unit; define it before choosing LOD scheme.
- Edit log (brush op + seed + tile) replicable and reproducible on the server; GPU edits must match the CPU authoritative result or be corrected.
- Terrain depth/height tiles feed ocean shoreline, precipitation occlusion, particle collisions.

Open risks / measure:
- Seam handling between heightfield and voxel overlays.
- Edit throughput and latency from server to clients; physics rebuild cost.
- Memory for high-res heightmaps and VT at long view distances; page fault behaviour.
- Collision/walkability on layered heightfields.

---

## 5. Foliage

State of the art (all unverified):
- UE Nanite Foliage: shown at the UE 5.6 keynote but not shipped in 5.6; shipped as **Experimental in UE 5.7** (Nanite Voxels for distant canopies, Nanite Assemblies, Nanite Skinning for wind instead of WPO, plus Procedural Vegetation Editor). Source: Epic 5.7 announcement and secondary write-ups (Tom Looman), seen via search snippets only; Epic documentation pages not opened. Status after 5.7 (5.8 is out) not checked.
- Classic: GPU instancing + billboard/impostor LODs (octahedral impostors, Brucks/Ryan Brucks UE impostor baker; Neubelt & Pettineo, "Crafting a Next-Gen Material Pipeline"? unrelated; skip), hierarchical instance culling on GPU.
- Volumetric/aggregate leaves: far LODs treat foliage as a volume with directional density/BRDF (aggregate appearance modelling; Loubet & Neyret "Hybrid mesh-volume LoDs for all-scale pre-filtering of complex 3D assets", EG 2017; Loubet & Neyret "A new microflake model with microscopic self-shadowing for accurate volume downsampling", EG 2018). Stochastic LOD blending and "Stochastic LOD transitions" reduce popping.
- Wind animation: vertex-shader hierarchical bending (trunk/branch/leaf) driven by the global wind field; Crytek/GPU Gems 3 "Vegetation Procedural Animation and Shading in Crysis" (Sousa, GPU Gems 3, 2007) is the standard reference.
- Lighting: translucency (thin-leaf transmission), per-tree AO baked, shadows from cascaded maps or virtual shadow maps; overdraw of alpha-tested leaves is the dominant cost.
- LOD transitions: dithered (screen-door) cross-fade, temporal AA hides it; alpha-to-coverage for masked geometry.

Key sources (unverified): Sousa 2007 (GPU Gems 3 ch.16); Loubet & Neyret 2017, 2018; Epic Nanite docs and Karis, "A Deep Dive into Nanite Virtualized Geometry", SIGGRAPH 2021 (Advances); Epic 5.x release notes on Nanite foliage; Crassin et al. "GigaVoxels" 2009 (volumetric background).

Applicability:
- Foliage rendering needs visibility-buffer-friendly masked raster and GPU culling first; impostors as the cheap fallback before any volumetric LOD.
- Wind field from topic 1 should be a bound resource sampled in the vertex stage.
- Spawn from PCG (topic 7) with deterministic seeds; instance data is derivable, not stored.
- Volumetric LOD is research-grade; defer.

Open risks / measure:
- Overdraw/ALU of masked leaf raster at density; shadow cost.
- Impostor memory and atlas management; LOD pop visibility.
- Instance count vs. culling cost at MMO view distances.

---

## 6. GPU particles at Niagara scale

State of the art (all unverified):
- Niagara (Epic): GDC 2018 session "Programmable VFX with Unreal Engine's Niagara", speaker Wyeth Johnson (Lead Technical Artist), March 21 2018; Shaun Kime (an architect of the tool) joined only for Q&A per a transcript. Shawn McGrath was wrong. Source: search snippets of Epic's GDC 2018 page and the talk recording, not opened in full. The architecture description below is unverified. Data model: emitters composed of modules in ordered stages (spawn, update, event handlers, simulation stages for grid/particle iteration); attributes in typed SoA data sets; GPU emitters run as compute with indirect dispatch and instance counts read back via GPU counters; data interfaces expose scene queries (depth buffer, SDF, skeletal mesh, grids).
- Unity VFX Graph: node graph compiled to compute shaders; particle capacity fixed per system, dead-list/alive-list management, GPU events, SDF generation via Visual Effect SDF Bake tools.
- Simulation: fixed-capacity SoA buffers, dead-list for allocation, indirect draw; sorting by bitonic or radix sort for alpha-blended particles; tile-based or froxel-based lighting for particles.
- Collisions: depth-buffer collision (screen-space, view-dependent artifacts) and global SDF/distance field collisions (UE Global Distance Field, Karis/Wright), plus heightfield collision against terrain tiles.
- Particle lighting: per-particle lit (vertex or pixel) using clustered lights; volumetric particle lighting via froxel injection; "Lighting particles" Wihlidal / Frostbite particle lighting talks: details unverified.
- Rendering: soft particles using depth, half-res rendering for overdraw-heavy effects, motion vectors for TAA.

Key sources (unverified): Lutz & Epic, "Niagara" GDC 2018/2019 talks (GDC Vault, unchecked); Unity VFX Graph docs; Lutz, "Everything you need to know about particles" (unverified); Hillaire 2015 (froxel lighting for particles); Kenny, Cunningham: no entries as exact reference recalled; Latta, "Building a Million-Particle System", Gamasutra 2004 (historic, GPU particle origin).

Applicability:
- Particle system is the most natural first consumer of the custom shader IR's compute path: define SoA attribute sets, dead-list, indirect args as IR-level concepts.
- Emitter graph data model: modules with declared attribute reads/writes enable dependency ordering and compile-time fusion.
- Determinism: cosmetic particles are client-only; gameplay-affecting particles (e.g. projectiles) are simulated on the CPU.
- Collision data providers (depth, SDF, terrain tile) should be pluggable "data interfaces".

Open risks / measure:
- Sort cost vs. particle count; overdraw cost.
- Depth-buffer collision correctness with TAA / disocclusion.
- Compile-time of generated compute permutations; GPU memory pooling.

---

## 7. Procedural generation

State of the art (all unverified):
- WFC: Gumin, "WaveFunctionCollapse" (GitHub, 2016, software, not a paper); Karth & Smith, "WaveFunctionCollapse is Constraint Solving in the Wild", FDG 2017. Local constraint propagation; global coherence is not guaranteed, and large-world use is chunked with boundary constraints.
- Hydraulic erosion: Mei, Decaudin, Hu, "Fast Hydraulic Erosion Simulation and Visualization on GPU", Pacific Graphics 2007 (grid pipe model); Jákó, "Fast Hydraulic and Thermal Erosion on the GPU", CESCG 2011; Musgrave et al. 1989. Erosion is global/iterative, so for tiled worlds it is baked offline or run with border overlap; determinism needs fixed-order integer or carefully ordered float arithmetic.
- Noise: Perlin, "Improving Noise", SIGGRAPH 2002; simplex noise (Perlin 2001; patent concerns historically; OpenSimplex alternatives); Worley 1996 cellular; gradient noise with integer hash is deterministic from (seed, coords).
- Vegetation: L-systems (Prusinkiewicz & Lindenmayer, "The Algorithmic Beauty of Plants", 1990); space colonization (Runions, Lane, Prusinkiewicz, "Modeling Trees with a Space Colonization Algorithm", Eurographics Workshop on Natural Phenomena 2007).
- Roads/cities: Parish & Müller, "Procedural Modeling of Cities", SIGGRAPH 2001 (L-system roads + lot subdivision + building grammars); later: Chen et al. "Interactive Procedural Street Modeling", SIGGRAPH 2008 (tensor fields).
- UE5 PCG framework: node graph operating on typed point/spatial data with attributes, hierarchical generation grids, runtime generation tied to World Partition; details are from product docs recalled, unverified.
- Determinism / seeds for networked worlds: derive per-cell seeds by hashing (world seed, cell coords, feature id); never share a single sequential RNG across cells; integer hashes (e.g. PCG, xxhash, splitmix) for portability; avoid float transcendental functions in authoritative generation or pin the implementation (own sin/exp).

Key sources (unverified): Gumin 2016; Karth & Smith 2017; Mei et al. 2007; Jákó 2011; Perlin 2002; Prusinkiewicz & Lindenmayer 1990; Runions et al. 2007; Parish & Müller 2001; Chen et al. 2008; O'Neill, "PCG: A Family of Simple Fast Space-Efficient Statistically Good Algorithms for Random Number Generation", Harvey Mudd tech report 2014; Jarzynski & Olano, "Hash Functions for GPU Rendering", JCGT 9(3) 2020, pp. 21-38 (verified; benchmarks GPU hashes by TestU01 BigCrush failures and render time; recommends PCG variants; exact timings/hardware not read). O'Neill's PCG is a Harvey Mudd tech report HMC-CS-2014-0905, never formally journal-published.

Applicability:
- Adopt "pure function of (seed, cell, version)" as the generation contract; the same generator runs on server (authoritative) and optionally on clients.
- A typed point-data graph (PCG-like) fits the engine's ACS/IR style; run on CPU fibers first, GPU later.
- Erosion belongs in an offline/baked pipeline; runtime edits are then deltas (topic 4).
- Generator versioning: any algorithm change invalidates cached output; store generator version with each tile.

Open risks / measure:
- Cross-platform float determinism in generation; seams at cell boundaries (erosion, WFC, roads).
- Generation latency per tile on fiber workers vs. streaming speed.
- Authoring workflow/tooling cost for graph-based generation.

---

## Cross-cutting recommendations (unverified inputs)

- Shared "world fields" service: wind, water height, terrain height, weather state as pure functions of (position, time, replicated state), evaluated identically (within tolerance) on server, CPU gameplay, and shader IR.
- Shared GPU infrastructure that pays off across topics: froxel volume (fog, particles, underwater), global/local SDF or depth providers (particle collision, shoreline), indirect-dispatch compute graph.
- Verification backlog: open every cited source, record which numbers are measured on which hardware, flip claims to `verified`.

---

## Verification pass (2026-11-07)

Method: web search plus landing/abstract/course pages. No PDFs or full texts read, so no timings or hardware figures were collected except where noted. Status `V-abs` = verified (abstract/landing page); `V-course` = verified (course/index page); `UNV` = still unverified.

| # | Source | Status | URL / note |
|---|--------|--------|-----------|
| 1 | Hillaire EGSR 2020, CGF 39(4) pp.13-22 | V-abs | https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.14050 ; sebh.github.io/publications/ lists it; diglib.eg.org returned 403 |
| 2a | Hillaire 2016 Frostbite sky/cloud | V-course | Venue corrected to "Physically Based Shading in Theory and Practice" course. https://www.ea.com/frostbite/news/physically-based-sky-atmosphere-and-cloud-rendering |
| 2b | Hillaire 2015 volumetric lighting | V-course | Title as cited is correct on https://advances.realtimerendering.com/s2015/index.html ; sebh page lists it as "Physically-based and Unified Volumetric Rendering in Frostbite" (EA landing page title differs; EA URL 404 as guessed) |
| 2c | Wronski 2014 volumetric fog | V-course | https://advances.realtimerendering.com/s2014/index.html (Part II, Ubisoft Montreal; no perf numbers on page) |
| 3 | Schneider 2015 / 2017 / 2023 | V-course | s2015, s2017, s2023 index pages; 2015 page states 2 ms GPU budget; Nubis3 abstract not read (page truncated) |
| 4a | Tessendorf, Simulating Ocean Water | V-abs | Course notes (revised 2001-2004 editions) https://jtessen.people.clemson.edu/reports/papers_files/coursenotes2002.pdf (located via search, not opened) |
| 4b | Sea of Thieves | V-abs, CORRECTED | SIGGRAPH 2018 Talk by Ang, Catling, Cifariello Ciardi, Kozin. https://dl.acm.org/doi/10.1145/3214745.3214820 . No GDC 2018 talk found; claim of Gerstner sum contradicted (FFT per abstract) |
| 4c | Water Surface Wavelets, TOG 37(4) | V-abs, CORRECTED | 6 authors (Jeschke, Skrivan, Müller-Fischer, Chentanez, Macklin, Wojtan). DOI 10.1145/3197517.3201336 ; https://research-explorer.ista.ac.at/record/134 |
| 5a | Losasso & Hoppe 2004, TOG 23(3) | V-abs | https://hhoppe.com/proj/geomclipmap/ . Stated data: 40 GB US heightmap, 60 fps interactive flight (hardware not read) |
| 5b | Asirvatham & Hoppe, GPU Gems 2 ch.2 | V-abs | https://hhoppe.com/proj/gpugcm/ |
| 5c | Strugar CDLOD, JGT 14(4) pp.57-74 | V-abs | DOI 10.1080/2151237X.2009.10129287 (via dblp/search) |
| 6a | Ju et al. 2002, TOG 21(3) pp.339-346 | V-abs | https://dl.acm.org/doi/10.1145/566570.566586 |
| 6b | Lengyel PhD, UC Davis 2010 | V-abs | https://transvoxel.org/ (PDF not opened) |
| 6c | Schaefer, Ju, Warren, Manifold DC, IEEE TVCG 13(3) 2007 | V-abs | https://doi.org/10.1109/TVCG.2007.1012 |
| 7a | Mei, Decaudin, Hu, PG 2007 | V-abs | https://hal.science/inria-00402079 (DOI sources disagree: PG.2007.15 vs .27) |
| 7b | Jákó (with Szirmay-Kalos), CESCG 2011 | V-abs | http://old.cescg.org/CESCG-2011/papers/TUBudapest-Jako-Balazs.pdf (non-peer-reviewed seminar; reports GPU vs CPU ms/iteration, not read) |
| 7c | Parish & Müller, SIGGRAPH 2001, pp.301-308 | V-abs | https://history.siggraph.org/learning/procedural-modeling-of-cities-by-parish-and-muller/ |
| 7d | Karth & Smith, FDG 2017 | V-abs | https://dl.acm.org/doi/10.1145/3102071.3110566 |
| 7e | O'Neill PCG, HMC-CS-2014-0905 | V-abs | https://www.cs.hmc.edu/tr/hmc-cs-2014-0905.pdf (tech report, never journal-published) |
| 7f | Jarzynski & Olano, JCGT 9(3) 2020 | V-abs | https://jcgt.org/published/0009/03/02/ ; exists, shaky flag cleared |
| 8a | Zhu & Bridson 2005, TOG 24(3) | V-abs | https://www.cs.ubc.ca/~rbridson/docs/zhu-siggraph05-sandfluid.pdf |
| 8b | Macklin & Müller, PBF, TOG 32(4) | V-abs | https://mmacklin.com/pbf_sig_preprint.pdf |
| 8c | Jiang et al., APIC, TOG 34(4) | V-abs | DOI 10.1145/2766996 ; https://disneyanimation.com/publications/the-affine-particle-in-cell-method/ |
| 8d | Koschier et al. EG 2019 tutorial | V-abs, CORRECTED | 4 authors; arXiv 2009.06944 ; DOI 10.2312/egt.20191035 . 2022 follow-up is the CGF survey "A Survey on SPH Methods in Computer Graphics" 41(2) (named in search results only) |
| 8e | Museth VDB 2013 / NanoVDB 2021 | V-abs | DOI 10.1145/2487228.2487235 ; https://dl.acm.org/doi/10.1145/3450623.3464653 |
| 9a | Sousa, GPU Gems 3 ch.16 | V-abs | https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis |
| 9b | Loubet & Neyret EG 2017 | V-abs | CGF 36(2) pp.431-442, DOI 10.1111/cgf.13138 (bibliographic data via search; abstract not opened) |
| 9c | Nanite foliage | PARTIAL | Experimental in UE 5.7 (not 5.6). Based on Epic 5.7 announcement snippets + third-party write-ups; Epic docs not opened |
| 10a | Niagara GDC talk | PARTIAL, CORRECTED | "Programmable VFX with Unreal Engine's Niagara", GDC 2018, Wyeth Johnson. Search snippets only; GDC Vault page not opened |
| 10b | Unity VFX Graph | PARTIAL | Unity manual 6000.2 "Choosing your particle system": VFX Graph simulates millions of particles on GPU, requires compute shaders; capacity fixed per asset (forum-sourced). https://docs.unity3d.com/6000.2/Documentation/Manual/ChoosingYourParticleSystem.html |
| - | Frostbite terrain (Andersson 2007) | V-abs, CORRECTED | Title confirmed; course "Advanced Real-Time Rendering in 3D Graphics and Games", pp.38-58. https://www.ea.com/frostbite/news/terrain-rendering-in-frostbite-using-procedural-shader-splatting |

Still UNV: all section-level technique claims (cloud pipeline details, precipitation/wind/weather practice, shipped-game claims such as AC4/Horizon/Death Stranding/Far Cry, UE5 Landscape/World Partition/PCG, layered heightfields, Niagara internals), Bruneton & Neyret 2008 and Bruneton 2017, Phillips/JONSWAP/Fournier & Reeves, Jeschke 2020 boundary-aware waves, Gamper thesis, Kellomäki, Barrett 2008, Stam 1999, Stomakhin MPM, Karis Nanite 2021, Crassin GigaVoxels, Chen 2008, Runions 2007, Perlin/Worley/Gumin, Latta 2004, Musgrave 1989. Reason: not in the priority list for this pass, not searched. Reasons for no performance figures: abstracts rarely state them and full-text PDFs were deliberately skipped.
