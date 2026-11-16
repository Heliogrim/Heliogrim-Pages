# ADR-0010: Vendor recastnavigation for Navmesh Build and Queries

**Date**: 2026-11-09 (owner, Q37.1)
**Status**: accepted (recorded 2026-11-16)
**Source**: [#117](https://github.com/Heliogrim/Heliogrim-Engine/issues/117), [navmesh library fit](../architecture/navigation-exploration.md) (chunk W37.0)

## Context

Q37.1 asked for a comparison of navmesh libraries and an in-house builder before vendoring anything. The engine has no navigation code. The rules allow third-party code only for selected algorithms, under permissive licences, and never paid software.

## Decision

- Vendor `recastnavigation` (zlib): the Recast, Detour, DetourTileCache and DetourCrowd modules, with DebugUtils for the editor only.
    - Pin a `main` commit (`9f4ce64` at decision time), not the last tag (`v1.6.0`, 2023).
    - Compile with `DT_POLYREF64` under the engine's C++23 flags.
    - Integrate it like the other vendors: `CachedFetchContent_Declare` at the pinned commit, with local changes as git patch files in `vendor/recastnavigation/`. The vendor helpers apply them on every fetch or update (`PATCH_COMMAND git restore …` then `COMMAND git apply ../<name>.patch`), as for zlib, assimp, gli, spng, vorbis and vulkan-loader. One patch lifts upstream's `CXX_STANDARD 98` pin and its `/EHs-c-` override.
    - Keep each patch small and atomic, one concern per file.
- `Engine.Navigation` wraps it. Detour types, refs, filters and query objects stay inside the wrapper.
- In-house, because no option provides them: the tile hierarchy, flow-field tiles, the sparse voxel octree for flying and swimming agents, build scheduling on Background fibers, and tile serialisation in the cell package.
- No in-house voxeliser for now. The choice reopens only if a measured limit blocks a W37.2 or W37.3 "done when".
- First functional patch: the detail-mesh sample-distance cache from the performance pass (exploration section 10), shipped as `detail-sample-cache.patch`. It halves tile builds, and the tile data stays byte-identical to upstream. A hash test against unpatched upstream guards it.
- Tiled builds use layers partitioning unless W37.1 finds a quality case against it.

## Alternatives Considered

### In-house voxeliser, tile builder and queries

- **Pros**: designed around 64 m tiles, origin-relative coordinates and the scheduler.
- **Cons**: about 27k lines of hard geometry code that upstream took years to stabilise.
- **Why not**: no measured gap pays for it.

### Godot, O3DE, Polyanya, ports, volume libraries

- **Why not**: Godot and O3DE contribute engine wiring around unpatched Recast and nothing standalone. Polyanya is a query algorithm only. The ports are in other languages. The volume libraries are tied to Unreal.

## Consequences

### Positive

- A proven builder, queries and obstacle cache from day one.
- The work goes into what nobody provides: hierarchy, flow fields, volumes.

### Negative

- The library uses float coordinates, so the engine needs an origin per region.
- No threading model: we build the job layer ourselves.

### Risks

- Upstream has one active maintainer and no release since 2023. We track `main` and own our patches. If upstream stalls, the vendored copy becomes ours.
- Moving the pinned commit can break a patch. `git apply` then fails the fetch, so the break is loud and shows up at update time.
- Known open issues (#818 layered tile links, #826 crowd hashing far from the origin) need workarounds or local patches.
