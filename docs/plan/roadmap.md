# Roadmap: Dependency Line and Milestones

**Status**: <span class="hg-status summary">plan</span>. An ordering, not a schedule. Milestones are integration points reached when their systems pass their "done when" checks. Tracks run in parallel where the dependency line allows; the line is the constraint, the milestone grouping is the recommendation. Where each milestone stands: [progress board](progress.md).

## The dependency line

```hg-diagram
flowchart LR
    subgraph M1["M1 Trustworthy core"]
        S01["S01 Serialisation versions"]
        S02["S02 Scheduler v2"]
        S03["S03 Async storage"]
        S04["S04 Observability"]
        S05["S05 Diagnostics"]
        S06["S06 Crash"]
        S26["S26 GPU harness"]
        S62["S62 CI gates"]
        S63["S63 Standard"]
    end
    subgraph M2["M2 Render and world core"]
        S11["S11 ASL SPIR-V"]
        S12["S12 Pipeline kinds"]
        S13["S13 Variant cache"]
        S14["S14 Render graph v2"]
        S15["S15 GPU-driven"]
        S07["S07 Large world"]
        S09["S09 Reflection v2"]
        S40["S40 World partition"]
        S17["S17 Virtual textures"]
        S16["S16 Materials v2"]
        S39["S39 Input v2"]
        S45["S45 Actions v2"]
        S58["S58 Headless"]
    end
    subgraph M3["M3 A beautiful world"]
        S18["S18 Micropoly"]
        S19["S19 Shadows"]
        S20["S20 GI"]
        S21["S21 Volumetrics"]
        S22["S22 Transparency"]
        S23["S23 Post"]
        S24["S24 Particles"]
        S27["S27 Terrain v1"]
        S30["S30 Ocean"]
        S32["S32 Weather"]
        S42["S42 Canvas"]
        S43["S43 Uikit"]
        S44["S44 Picking"]
        S46["S46 Search"]
        S59["S59 Replay"]
    end
    subgraph M4["M4 Living world and tools"]
        S28["S28 Terrain v2"]
        S31["S31 Fluids"]
        S33["S33 Procedural"]
        S34["S34 Physics v2"]
        S36["S36 Animation"]
        S37["S37 Navigation"]
        S38["S38 Audio"]
        S47["S47 Visual scripting"]
        S48["S48 HMR"]
        S50["S50 Plugins"]
        S53["S53 Build system"]
        S54["S54 Test automation"]
    end
    subgraph M5["M5 Connected"]
        S55["S55 Transport"]
        S56["S56 Replication"]
    end
    subgraph M6["M6 Single shard"]
        S57["S57 Server mesh"]
        S60["S60 JIT"]
    end
    S02 --> S03 --> S17
    S02 --> S04 --> S06
    S01 --> S40
    S03 --> S40
    S11 --> S12 --> S13 --> S16
    S11 --> S14 --> S15
    S12 --> S15
    S07 --> S15
    S15 --> S18
    S15 --> S19
    S15 --> S20
    S16 --> S20
    S12 --> S21 --> S32
    S14 --> S23
    S12 --> S24 --> S31
    S40 --> S27 --> S28
    S17 --> S27
    S32 --> S30
    S12 --> S42 --> S43
    S39 --> S44
    S09 --> S46
    S09 --> S48 --> S47
    S09 --> S50
    S02 --> S34 --> S28
    S09 --> S36
    S40 --> S37 --> S28
    S02 --> S38
    S01 --> S45 --> S54
    S59 --> S54
    S02 --> S59
    S02 --> S55 --> S56 --> S57
    S40 --> S56
    S58 --> S57
    S13 --> S60
```

## Milestones

### M1: Trustworthy core

The smallest set that makes every later change safe. All items are near or mid distance on existing code.

| Systems | Done when |
|---------|-----------|
| S01 | A record written by version N loads in N+1 with unknown fields preserved through a save; a corrupted record is reported with its path |
| S02 | A task awaits an IO completion without blocking a worker; a frame task graph with declared dependencies runs in parallel; the deterministic mode gives identical state hashes across runs |
| S03 | 1,000 concurrent asset requests complete through the IO thread with priorities honoured and cancellation observed; no `todo_panic` remains in storage |
| S04, S06 | A span trace of one frame opens in the profiler view; a crash on a fiber yields a dump with the fiber stack and a crash ID |
| S05 | ASL, importers and storage return `Diagnostic` values; the editor shows one with a fix action |
| S26, S62, S63 | CI builds, runs all tests including one GPU golden test, runs clang-tidy and ASan, and blocks on a performance band |
| S08, S10 | Memory per subsystem is reported; clean editor build time is recorded against the 2026-11-07 trace |

### M2: Render and world core

The pivot. Everything photoreal or large-scale depends on it.

| Systems | Done when |
|---------|-----------|
| S11, S12, S13 | Every engine shader compiles ASL to SPIR-V without glslang; a compute, mesh and ray-query pipeline each run a harness test; a scene's pipelines are cached on disk and compiled asynchronously |
| S14, S15 | A 1M-instance scene is culled and drawn through indirect draws from GPU tables with barriers and aliasing derived from pass declarations; the visibility buffer resolves materials |
| S07 | A test world 100 km from the origin renders without jitter; physics and audio read double positions |
| S09, S40 | Actors live in streaming cells; cells load and unload under the budget while the camera moves; reflection survives a module reload in a test |
| S16, S17 | A layered material with emissive renders; a 16k virtual texture streams by feedback within the budget |
| S39, S45, S58 | Input contexts arbitrate editor, UI and game; an edit is a transaction that undoes across objects; the server role runs a headless simulation in CI |

### M3: A beautiful world

| Systems | Done when |
|---------|-----------|
| S18 | A 100M-source-triangle scene streams and renders at pixel-sized clusters in the frame budget on the baseline GPU |
| S19, S20, S22, S23 | A reference scene passes golden images for shadows, GI, transparency and post against reference renders |
| S21, S32 | Sky and clouds follow a weather state across a day cycle; fog interacts with lights and transparency |
| S24 | 1M GPU particles with collisions and sorting in budget |
| S27, S30 | A 10 km² terrain with ocean streams and renders; server height queries match the shader within tolerance |
| S42, S43, S44, S46 | The editor draws every widget through the canvas; text is shaped; objects are picked and moved with gizmos; assets are found by tag and text |
| S59 | A recorded session replays to identical state hashes |

### M4: Living world and tools

| Systems | Done when |
|---------|-----------|
| S28, S29 | A terrain edit updates render, physics and navigation within a frame; a cave layer has its own weather and audio volume |
| S31, S33 | A fluid volume interacts with the ocean; a procedural tile regenerates identically from its seed |
| S34, S35, S36, S37, S38 | Characters animate with inertialised transitions and cloth; navigate a streamed navmesh; sound follows the design |
| S47, S48 | A visual script compiles to C++ and hot-reloads with state preserved |
| S50, S51, S52, S53, S54 | A sample plugin loads; the editor shows VCS status; a pseudo-locale runs; a project packages to a signed artifact; a workflow test replays in the editor |

### M5: Connected

| Systems | Done when |
|---------|-----------|
| S55, S56 | A client connects over QUIC, receives interest-managed snapshots, predicts and reconciles; HTTP/2 and HTTP/3 clients fetch from a test server |

### M6: Single shard

| Systems | Done when |
|---------|-----------|
| S57, S60 | Two server nodes hand over an actor without a visible hitch on the client; a measured JIT gate shows a win or is closed |

## Sequencing advice

1. **Start M1 in full before any M2 item**, except S11 which has no foundation dependency and is already in progress. The three foundations (S01, S02, S03) are the cheapest high-leverage work in the plan.
2. **Within M2, S14 and S15 before S16 and S17**: materials and virtual textures are easier to design against the GPU-driven scene than to retrofit.
3. **Start S42 (canvas) as early as the compute pipeline (S12) exists**; the editor's quality gates everything a human sees, and the uikit issues (#27 to #36) wait on it.
4. **Defer S18 (micropolygons) until S15 ships and is measured**; its streaming cost is the largest unknown in the rendering track.
5. **Do not start S57 until S56 is measured on a two-node prototype**; the MMO claims in the research are the least verified.
6. **Keep M1's quality gates running**: every later milestone adds golden tests and performance bands to CI rather than its own process.

## Risks to the line

| Risk | Effect | Mitigation |
|------|--------|------------|
| Scheduler v2 changes the shape of every system | M2 items built on the old scheduler get rewritten | Finish S02 first; design its waitable API with S03 and S38 as the first consumers |
| Direct SPIR-V backend takes longer than expected | S12 to S16 wait | Keep the glslang-gated path as the fallback; S12 can start on it |
| GPU minimum spec undecided | Mesh shaders, ray queries, 64-bit atomics may be unavailable | Decide the baseline in S15's issue; every GPU feature has a compute fallback or is optional |
| Research claims unverified | A system is designed on a wrong number | Each issue starts with a spike or benchmark; the [sources](sources/index.md) list what to re-open |
| Single owner | Parallel tracks stall | Milestones are small; a track can pause without blocking others except through the line above |
