# Procedural Generation

**Systems**: S33 · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Research from [world](../sources/research-world.md) section 7 (all unverified).

## Target

Deterministic, seed-driven, graph-based generation for terrain detail, scatter (foliage, rocks, props), roads and structures, usable offline (baking) and at runtime (streaming cells), with identical results on server and clients for anything gameplay-relevant.

## Current state (checked 2026-11-07)

- Nothing. `Editor.GFX.Graphs` holds node definitions for material-style graphs without a compiler; the owner's notes mention "environment painting with automatic instantiation".

## Research summary (all unverified)

- Wave function collapse (Gumin 2016 software; Karth and Smith FDG 2017) as constraint solving; chunked with boundary constraints for large worlds.
- Hydraulic erosion on the GPU (Mei et al. 2007; Jákó 2011) is iterative and global; for tiled worlds it is baked offline or run with border overlap.
- Noise: Perlin 2002, simplex and OpenSimplex, Worley 1996; gradient noise with an integer hash is deterministic from seed and coordinates.
- Vegetation: L-systems (Prusinkiewicz and Lindenmayer 1990), space colonisation (Runions et al. 2007). Cities and roads: Parish and Müller 2001, Chen et al. 2008 tensor fields.
- UE5 PCG: a node graph over typed point data with attributes, hierarchical generation grids tied to world partition.
- Determinism: per-cell seeds hashed from world seed, cell coordinates and feature ID; never one sequential RNG across cells; integer hashes (PCG, splitmix, xxhash); avoid float transcendentals in authoritative generation or pin the implementation; generator version stored with each output.

## Guidance

- **Contract**: a generator is a pure function of `(world seed, cell coordinates, generator version, inputs)`; same code on server and client; outputs are typed point sets, height or material deltas, spline networks, or structure placements.
- **Graph**: a typed point-data graph (sample, filter, transform, scatter, spawn) with nodes that declare their reads and writes; compiled by the same graph compiler as visual scripting (S47) into C++ for shipping and interpreted in the editor for iteration. Until S47 exists, generators are hand-written C++ against the same interfaces.
- **Scheduling**: cell generation runs on Background fibers (S02) as part of cell streaming (S40) with latency measured against streaming speed; runtime results are cached by content hash with the generator version.
- **Erosion and other global passes**: offline in the worker role (S58) over the whole terrain with border overlap; the result is baked into terrain tiles; runtime edits are deltas (S28).
- **Scatter**: feeds foliage (S25) and props as derived instances; hand-placed overrides are stored, generated ones are not.
- **Math**: integer hashes for randomness; an in-tree deterministic `sin`, `exp` set for authoritative paths (shared with S59).

## Done when

- A cell regenerates bit-identically from its seed on two machines; a generator version bump invalidates cached output.
- A forest, a road network and a rock scatter are generated across cell boundaries without seams.
- An eroded 10 km² terrain is baked in the worker role and loads as tiles.

## Open decisions

- Graph compiler shared with S47 and S24 from the start.
- Which generators are authoritative (server) versus cosmetic (client).
