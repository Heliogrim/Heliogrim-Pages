# Work: Ocean and Fluids

**Systems** S30, S31 · **Issues** [#110](https://github.com/Heliogrim/Heliogrim-Engine/issues/110), [#111](https://github.com/Heliogrim/Heliogrim-Engine/issues/111) (To discuss) · **Track** C · **Milestone** M3 to M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Ocean and fluids](../topics/ocean-fluids.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Engine vision note (2026-10-31) | Server-authoritative sailing: CPU-evaluable deterministic height; GPU FFT for visuals only | Matches the two-layer design; Gerstner versus spectral components still open (Q30.1) |
| [Volumetrics work](volumetrics-weather.md) | `WindField` and `WeatherState` | Spectrum parameters derive from them |
| [Terrain work](terrain.md) | `HeightQueryService` | Shoreline depth and attenuation |
| [Physics work](physics-cloth.md) | Jolt bodies, double positions | Buoyancy service consumer |
| [Particles work](particles-foliage.md) | `SimStage` infrastructure | Fluids as simulation stages (Q31.1) |
| Issue #111 status "To discuss" | Owner wants a conversation on fluids | W31.0 prepares it |
| Deterministic math (S59) | In-tree deterministic `sin`, `exp` | Authoritative height uses it |

## Architecture

- **Bundles**: new `Engine.World.Ocean` (authoritative height function, spectrum parameters, buoyancy service) and `Engine.GFX.Render.Ocean` (FFT cascades, foam, shoreline, wakes, surface shading). Fluids: `Engine.VFX.Fluids` as simulation stages of S24, or its own bundle per Q31.1.
- **Provides**: `sampleWater(WorldPosition, time)` on the CPU; ocean surface rendering; local fluid volumes and 2D shallow-water inserts; CPU proxy fields for gameplay.
- **Consumes**: weather and wind (S32), terrain height (S27), compute pipelines (S12), froxel (S21), Jolt (S34), particles (S24), deterministic math (S59).

## Code design

| Type | Contract |
|---|---|
| `WaveFunction` | One source compiled to C++ (double positions, strict FP, deterministic trig) and to ASL: `height(x, y, t, seed, windState)`; Gerstner sum or small spectral component set per Q30.1; server and client agree within a gameplay tolerance. |
| `OceanParams` | Derived from `WeatherState` (wind speed and direction select the spectrum); replicated through the weather state, not separately. |
| `BuoyancyService` | `sampleWater(WorldPosition) -> { height, normal, velocity }` for Jolt bodies; hull sampling helper; throughput measured for many ships per server tick. |
| `FftCascades` | Three to four cascades at world scales in ASL compute (shared-memory butterflies); displacement, normals, Jacobian foam; cascade count per Q30.2. |
| `ShorelinePass` | Depth from `HeightQueryService`; amplitude attenuation, foam and colour by depth. |
| `WakeTarget` | Camera-windowed render target for wakes and ship foam. |
| `FluidVolume` | Bounded domain; PBF liquid or Stable-Fluids smoke on a sparse brick grid; surface extraction by screen-space fluid rendering or marching cubes. |
| `ShallowWaterInsert` | Bounded 2D grid coupled to the ocean height at its border (rivers, near-ship water). |
| `FlowProxy` | Low-resolution CPU flow and depth field the server evaluates; drives floating objects identically on both sides. |

Placement: `Engine.World.Ocean/{WaveFunction,OceanParams,BuoyancyService}`, `Engine.GFX.Render.Ocean/{FftCascades,ShorelinePass,WakeTarget}`, `Engine.VFX.Fluids/{FluidVolume,ShallowWaterInsert,FlowProxy}`. Tests: 10k-point server and client agreement; ship floats under wind; cascade goldens; FFT cost counter.

## Work chunks

### W30.0 Authoritative wave function spike · explore · after W07.2

- **Goal**: implement Gerstner and a small spectral set as one source, measure precision and cost per sample on CPU in double and on GPU; decide Q30.1 by numbers.
- **Output**: `architecture/ocean-exploration.md`.

### W30.1 Ocean design · design · after W30.0, W32.1, W21.1

- **Output**: `architecture/ocean-design.md`; plan.
- **Questions**: Q30.2.

### W30.2 Implement authoritative height and buoyancy · execute · after W30.1, W34.2

- **Done when**: server and client samples agree within tolerance at 10k points and times; a ship floats and sails under wind.

### W30.3 Implement FFT cascades, foam, shoreline, wakes · execute · after W30.2, W12.2, W27.2

- **Done when**: cascade, foam and shoreline goldens pass; FFT cost per frame recorded.

### W31.0 Fluids discussion brief · explore · ready (#111 is "To discuss")

- **Goal**: prepare the owner's conversation: scope (splashes, smoke, local water), technique per scope, cost at the target budget, the CPU proxy contract; recommend bundle placement.
- **Output**: `architecture/fluids-exploration.md`.
- **Questions**: Q31.1, Q31.2.

### W31.1 Fluids design · design · after W31.0 and the owner's decision, W24.2

### W31.2 Implement a splash volume and a smoke volume · execute · after W31.1

- **Done when**: a splash interacts with the ocean surface and smoke with wind within the particle budget.

### W31.3 Shallow-water inserts and flow proxy · execute · after W31.2, W30.2

- **Done when**: a river's flow drives a floating object identically on server and client.

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q30.1 | Gerstner sum or direct spectral components for the authoritative layer? | W30.1 (W30.0 informs) | Gerstner with a bounded component count unless the spike shows a spectral set is cheaper at equal agreement |
| Q30.2 | Cascade count and resolution for the target view distance? | W30.1 | Four cascades at 256² until measured |
| Q31.1 | Fluids inside `Engine.VFX` (S24 stages) or their own bundle? | W31.1 | Inside `Engine.VFX` as `Fluids` sub-bundle |
| Q31.2 | Which fluid scope is in the first release: splashes, smoke, local water, all three? | W31.1 | Splashes and smoke; local water with S31.3 |
