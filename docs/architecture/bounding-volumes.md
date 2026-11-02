# Bounding Volumes and Spatial Queries (Exploration)

**Status**: exploration. Nothing here decided. Accepted parts move to ADR in [`adr/`](../adr/README.md); rest stays here or in issues.

This note collects design direction for zone-like bounds shared by graphics, physics, audio and navigation: combined (CSG) shapes, inner/outer falloff curves, static versus dynamic zones, 2D MSDF ideas carried to 3D, navmesh modifier volumes and 3D spatial indexing for multi-layered terrain. It starts from an external design review ([source](sources/bounding-volumes-gemini-review.md)). Where the review is vague or doubtful, the claim is marked **unverified** and listed in section 7.

## 0. Current State in Engine

- `Aabb` in `Engine.GFX` (`Aabb.hpp`) and `Sphere` in `Engine.GFX/Geometry/`.
- `Bounding` in `Engine.Common/Math/Bounding.hpp`, with tests in `Engine.Common.Test/Bounding.cpp`.
- `FrustumCullingFilter` in `Engine.GFX.Render.Graph.Scene/Filter/` as the only spatial query consumer found in a graph query.
- `SparseTexture` exists, but no MSDF pipeline or distance-field baking was found.
- No zone volumes, attenuation curves, spatial hash, octree or BVH for gameplay or audio was found.
- Jolt Physics is vendored and wrapped in `Engine.PFX` (`PhysicsSystem`, `PhysicsLayer`). Jolt brings convex shapes, GJK/EPA, a broadphase and object layers. The physics column in section 7 should use those, not new code.

Everything below is target, not description of existing code.

## 1. Goals and Constraints

- One volume description usable by rendering, physics, audio and navigation, so authors place a zone once.
- Combined shapes (unions, intersections, smooth blends) without evaluating many explicit primitives per query.
- Each query returns a **weight** in `[0, 1]` with a defined inner (full effect) and outer (no effect) boundary.
- Static zones are cheap to query after baking. Dynamic zones (moving, growing, shrinking, added or removed at runtime) must update in time proportional to the changed region, not the whole world.
- Vertical separation is a first-class property. Two zones with the same XZ footprint on different floors or caves must not blend unless they are linked.
- No allocation and no blocking on audio or physics query threads.

## 2. Representation

Two families are candidates. Neither is chosen.

| Family | Good for | Weak for |
|---|---|---|
| **Implicit** (signed distance, CSG tree) | Smooth distance, blending, falloff, combined shapes | Exact polygon queries, large precomputed fields |
| **Explicit** (convex hulls, support mapping, BVH of primitives) | Exact containment, GJK/EPA contact, portals | Smooth blending, many shapes per query |

Candidate hybrid: a zone is an analytic CSG tree of convex primitives (sphere, box, convex hull) for exact containment and distance, plus an optional baked volume field for static zones. The tree gives the distance `d(P)`; the field replaces the tree when it is too deep to evaluate per query.

CSG operators on distances:

- Union: `min(d1, d2)`
- Intersection: `max(d1, d2)`
- Smooth union (polynomial or exponential smin): blend width `k` avoids hard seams in reverb or fluid boundaries. Exponential form `-(1/k) ln(e^{-k a} + e^{-k b})` is a standard smooth-min; verify numerically before use.

**Exactness (review 2026-11-02).** `min` and `max` of exact SDFs give only a bound in general ([Quilez, interior distance](https://iquilezles.org/articles/interiordistance/)). Union by `min` is exact outside but not inside. Intersection by `max` is exact inside, as precise as its inputs ([Bálint, CAD Journal 2023](https://www.cad-journal.net/files/vol_20/CAD_20(6)_2023_1154-1174.pdf)), and only a lower bound outside. A convex hull written as `max` over its face planes (`n·p - d`) is therefore exact **inside** and only a lower bound **outside** near edges and vertices. An earlier version of this note had this reversed. (Applying the theorem to polytopes is our inference, not a quoted result.)

Consequences:

- A lower bound is still safe for sphere tracing and for the "possibly relevant" outer check in section 3.
- A lower bound is **not** safe for falloff weights: `w` would rise too early near hull edges. Falloff on hulls needs the exact outside distance, either GJK distance against the point (Jolt provides it) or a baked field.

## 3. Falloff, Thresholds and Curves

Inner/outer model per zone, with `d` the signed distance (negative inside):

```
[Inside]  <-- r_inner -->  [Transition band]  <-- r_outer -->  [Outside]
d <= r_inner               r_inner < d < r_outer               d >= r_outer
w = 1                      w = curve(t)                        w = 0
```

- `t = (d - r_inner) / (r_outer - r_inner)`, clamped to `[0, 1]`.
- Curve is data, not code. Start with: linear (`1 - t`), smoothstep (`3t^2 - 2t^3`) and a small piecewise-cubic spline stored as coefficients. A baked LUT (for example 64 entries) is enough for audio and shader use.
- **Threshold mode**: a binary result (`d < r_inner`) for logic such as trigger enter/exit, with hysteresis (enter at `r_inner`, leave at `r_inner + h`) to stop flicker.
- **Mixing**: several zones contribute weights. Normalize weights only when the author asks for it; otherwise apply priority (highest priority wins a parameter, others blend into it).
- **Inner vs outer checks**: inner checks decide "fully in"; outer checks decide "possibly relevant" and gate further work. Use the outer check as the broad-phase cull.

Per-parameter attenuation (volume, low-pass cutoff, reverb send, gravity scale, navmesh cost) reads the same `w`. Each parameter has its own curve.

## 4. Static and Dynamic Zones

### Static (baked)

- Build a sparse grid or octree of the signed distance field at author time, with narrow-band storage near surfaces.
- Query is one or two texture or grid lookups plus trilinear interpolation.
- Store as a cooked asset (see the asset cooker idea in [audio-dsp.md](audio-dsp.md)); never bake at load time on the game thread.

### Dynamic (moving, growing, shrinking)

- Per-zone bounding box in a BVH with **refit** on change: update the leaf box, propagate bounds up. Good for translation and modest scaling. Rebuild only when the tree degrades (measured, not assumed).
- For shape changes that alter the field (explosion shockwave, growing hazard), recompute the field only inside the zone's dirty box. Update cost scales with the dirty box volume.
- Dirty-box updates are batched per frame and applied on a worker thread. Queries read the last published snapshot (double-buffered), never a half-updated field.

**Unverified**: the review proposes Jump Flooding (JFA) for local 3D field updates. JFA is well known for 2D and 3D distance transforms; its cost and quality for small, frequently changing dirty boxes is not measured here.

## 5. 2D MSDF Ideas in 3D

MSDF is a 2D technique: each texel stores per-channel distances so that sharp corners survive when a texture is sampled at low resolution. The review extends this to 3D "multi-channel" volumes. This is **unverified**: no standard 3D MSDF is established here. The parts worth carrying over are:

- Analytic evaluation in the shader with screen-space derivatives (`fwidth`) for anti-aliasing. This already matches 2D UI goals (see the UI MSDF work in the engine).
- Per-channel encoding of corner information only where a 2D glyph or decal needs it. For 3D zones, plain SDF plus analytic CSG is the default.

Open question: does 2D UI MSDF and 3D zone SDF share one bake tool and one shader library? Decide with a concrete shader prototype, not on paper.

## 6. Spatial Structures for Multi-Layered Terrain

2D spatial hashes conflate floors that share an XZ footprint (caves under bases, multi-story buildings, bridges).

- **3D grid or hashed 3D grid** keyed by `(x, y, z)` with a coarse vertical cell size. Simple, good for uniform density.
- **BVH over 3D boxes** for uneven density and dynamic zones. Preferred for zones; grid preferred for dense sampling (for example, sound emitters).
- **Layer mask** (32-bit) on every zone and every query. A query filters by mask before any distance work. Cheap and explicit.
- **Portals** between convex volumes (rooms, floors). Sound, visibility and physics-forces propagate only across open portals. This solves the audio occlusion problem across floors better than distance alone.

Layers and portals are complementary: layers say which zones may ever interact; portals say which connected regions currently do.

## 7. Subsystem Notes

| Subsystem | Representation | Evaluation | Notes |
|---|---|---|---|
| Graphics / UI | SDF or MSDF texture; analytic CSG | Pixel shader, `fwidth` | Resolution-independent edges |
| Physics | Jolt shapes (existing) | Jolt broadphase and narrowphase; zones as sensor bodies | Open question: zone layer mask versus Jolt object layers (section 8) |
| Audio | Zone CSG + portals | Listener distance, curve LUTs | Parameter updates at control rate (review says 60–100 Hz; **unverified**, must match the audio thread design). If Steam Audio is adopted ([audio-dsp.md](audio-dsp.md)), portals feed its pathing. |
| Navigation | Modifier volumes | Box overlap during tile rebuild | Dirty-flag affected tiles only; see below |

### NavMesh modifiers

Tile-based navmeshes (Detour-style tile cache with obstacles) already rebuild only dirty tiles. Zone modifiers (cost areas, blocked areas, height-limited areas) should map to:

- A modifier volume registers the tiles it overlaps and marks them dirty on move, grow or shrink.
- Falloff weights apply to area cost, not to the walkable surface itself. Walkability stays binary.
- Layer masks select which agents see which modifiers (for example, a crawling agent in a cave layer).

## 8. Open Questions

- Which representation is the source of truth for authors: CSG tree, mesh, or both with cooked fields?
- Maximum CSG depth per query before the baked field must be used. Needs measurement.
- Hysteresis width default, and whether hysteresis belongs to the zone or the query.
- Dirty-box update budget per frame on the target platforms.
- Whether JFA or a simpler brute-force local distance transform wins for small dirty boxes.
- Whether portals are authored, generated from geometry, or both.
- Whether the navmesh modifier layer can reuse the zone layer mask or needs its own.
- Whether zones are Jolt sensor bodies (reusing its broadphase) or a separate BVH. Reusing Jolt removes a structure but ties zone queries to the physics update and its threads.
- Large-world coordinates: the engine vision targets very large worlds. Decide whether zone positions are double or cell-relative float before baking any field.

## 9. Next Steps

- Write a small CPU prototype: sphere and box primitives, smooth union, inner/outer curve, and a 3-zone test in `Engine.Common.Test` style. Include a test that shows the hull-distance lower bound near an edge. No renderer work yet.
- Measure one static baked field and one refit BVH on a synthetic scene with 10k zones.
- Decide the layer mask width and portal representation as issues; write an ADR once accepted.

## References

- Design review (Gemini, raw): [sources/bounding-volumes-gemini-review.md](sources/bounding-volumes-gemini-review.md)
- Existing bounds: `src/Engine.Common/Math/Bounding.hpp`, `src/Engine.GFX/Aabb.hpp`, `src/Engine.GFX/Geometry/Sphere.hpp`
- Related: [Audio and DSP (exploration)](audio-dsp.md), [Actor system (exploration)](actor-system.md)
