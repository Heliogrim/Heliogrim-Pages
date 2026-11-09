# Ocean and Fluid Dynamics

**Systems**: S30, S31 · **Track** C · **Milestone** M3 to M4
**Status**: <span class="hg-status summary">plan</span>. Research from [world](../sources/research-world.md) sections 2 and 3 (bibliographic data verified on 2026-11-07 from abstracts and landing pages; technique claims and numbers still unverified).

## Target

- **Ocean**: a massive ocean for terrain effects, sailing and shipping. An authoritative, deterministic, CPU-evaluable height function shared by server, gameplay and shader; FFT cascades for visual detail; foam from the displacement Jacobian; shoreline attenuation and depth effects; buoyancy sampling; wakes; coupling with terrain depth and weather wind.
- **Fluid dynamics**: convincing volumetric fluids as bounded-domain GPU effects (smoke, splashes, local water) with surface extraction, and cheap deterministic CPU proxies for gameplay queries.

## Current state (checked 2026-11-07)

- Nothing. The owner's vision notes already separate server-side deterministic height (Gerstner sums) from GPU FFT visuals.

## Research summary (all unverified)

- Ocean: Tessendorf 2001 spectral height field with dispersion evolved in frequency space and an inverse FFT per frame; choppy horizontal displacement; three to four cascades at different world scales; foam from the Jacobian fold detection. Gerstner sums (Fournier and Reeves 1986) are exactly evaluable on CPU and GPU with the same code. Sea of Thieves ("The Technical Art of Sea of Thieves", SIGGRAPH 2018 Talk, Ang, Catling, Cifariello Ciardi, Kozin; abstract verified) uses Tessendorf's FFT technique, not a Gerstner sum as earlier recalled; whether its ship physics samples the same field on the CPU is not stated in the abstract. Buoyancy samples hull points and applies spring, damping and displaced volume; Gerstner horizontal displacement needs an iterative inverse. Shoreline: amplitude attenuation by depth, depth-based foam and colour; boundary-aware wavelets (Jeschke et al. 2018, 2020) as a lead.
- Fluids: FLIP (Zhu and Bridson 2005), APIC (Jiang et al. 2015), PBF (Macklin and Müller 2013), SPH survey (Koschier et al. 2019, 2022), Stable Fluids (Stam 1999), sparse grids (OpenVDB 2013, NanoVDB 2021). Real-time at scale means bounded domains and 10^5 to 10^6 particles; world water stays a height field with local inserts; gameplay queries use an analytic or low-resolution CPU field the server can evaluate too.

## Guidance

### S30 Ocean

- Two layers with one parameter source:
  - **Authoritative layer**: an analytic sum (Gerstner or a small spectral component set) as a pure function of `(x, y, t, seed, wind state)` in `Engine.World.Ocean`, compiled from one source into C++ (double world positions, strict FP) and into ASL; server and client agree within a gameplay tolerance, not bitwise.
  - **Cosmetic layer**: FFT cascades on the GPU (a clean compute workload and an early test of shared-memory butterflies in ASL), foam accumulation, shoreline and depth from the terrain height service (S27), wakes and ship foam in a camera-windowed render target.
- Wave parameters derive from the replicated weather state (S32); wind speed and direction select the spectrum.
- Buoyancy service: `sampleWater(WorldPosition)` on the CPU for Jolt bodies (S34), independent of rendering; throughput measured for many ships on a server tick.
- Underwater: fog from the froxel volume (S21), caustics as a later extra.

### S31 Fluid dynamics

- Bounded-domain GPU solver as a simulation stage of the particle system (S24): PBF liquids for splashes and small pools, a Stable-Fluids grid for smoke with a sparse brick allocator (NanoVDB-like, also useful for SDFs and fog media); surface extraction by screen-space fluid rendering or a marching-cubes pass for small volumes.
- Local interactive water (rivers, wakes near ships): bounded 2D shallow-water grids coupled to the ocean height at their borders.
- Gameplay proxy: flow and depth as low-resolution CPU fields the server evaluates; visuals are client-only.

## Done when

- Ocean: server and client height samples at 10k random points and times agree within the stated tolerance; a ship floats and sails under wind from the weather state; the cascade rendering, foam and shoreline pass golden images; FFT cost per frame is recorded.
- Fluids: a splash volume interacts with the ocean surface and a smoke volume with wind; the particle budget holds; a river's flow field drives a floating object identically on server and client.

## Open decisions

- Gerstner versus direct spectral components for the authoritative layer (precision and cost per sample).
- Cascade count and resolution for the target view distance.
- Whether fluids ship as part of S24 or as their own bundle.
