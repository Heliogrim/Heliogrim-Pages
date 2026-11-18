# Iterating same-type components in sealed archetype clusters: desk research

Date: 2026-11-18. Scope: actor-archetypes-design.md §2, §6, §7 (slot = `[component block][actor object]`, chunks of n slots, per-type spans `(base, count, stride)`).
Tags: **[verified]** = primary source read (text extracted from the vendor PDF or official doc). **[summary]** = search snippet or secondary source only. **[unverified]** = inference or no source. **[inference]** = my reasoning from verified facts.

---

## 1. Leap-frog passes vs per-slot micro-loops vs gather

### 1.1 What the prefetchers do (vendor text)

**Intel (Sandy Bridge-class L1/L2 prefetchers; the text is unchanged in later cores' sections)**
- L1 prefetch triggers only if "the prefetched data is within the same 4K byte page as the load instruction that triggered it" and "not many other load misses are in progress". *Opt. Ref. Manual Vol. 2 (356477), §2.1.7 Data Prefetching, "Data Prefetch to L1 Data Cache".* [verified]
- **IP-based stride prefetcher**: tracks individual load instructions, prefetches current address + stride, "forward or backward and can detect strides of up to 2K bytes". *Same section.* [verified]
- The IP prefetcher "uses only the lower 8 bits of the address to distinguish" a load; loops larger than 256 B can alias loads. *Vol. 1 (248966-051), §3.7.2 Hardware Prefetching for First-Level Data Cache.* [verified] (The manual says "address"; in context it means the load's instruction address.)
- **L2 streamer**: watches ascending or descending L1 request sequences. "Prefetched cache lines must be in the same 4K page". It runs "up to 20 lines ahead", "Detects and maintains up to 32 streams … For each 4K byte page … one forward and one backward stream". *Vol. 2 §2.1.7, "Data Prefetch to the L2 and Last Level Cache".* [verified]
- **Spatial prefetcher**: completes each L2 fill to its 128-byte-aligned line pair. *Same section.* [verified]
- General rules: the prefetcher "requires a couple misses before it starts"; it "will not prefetch across a 4-KByte page boundary"; it works best when "strides of two successive cache misses remain less than the trigger threshold distance and close to 64 bytes". There is a start-up penalty on short arrays. *Vol. 1 §9.5.2 Hardware Prefetch.* [verified]
- Newer cores: the **Next-Page Prefetcher** (since Ivy Bridge) and Redwood Cove's **LLC Page Prefetcher**. LLCPP issues prefetches "two pages ahead" and tries to bring the whole 4 KB page into the LLC. It is "effective when streaming through memory over a buffer greater than 8KB". *Vol. 1 §2.1.1.6 LLC Page Prefetcher.* [verified] Golden Cove/Lion Cove L1 prefetch internals beyond this are not documented in the manual. [unverified]
- Cache sizes: Golden Cove and later P-cores have a 48 KB L1D. *Vol. 1 §2.4.1 lists "50% increase in size of the L1 data cache".* [summary]

**AMD Zen 4** (*Software Optimization Guide for the AMD Zen4 Microarchitecture, 57647 rev 1.00, §2.12.1 Prefetching of Data*) [verified]
- Five prefetchers. **L1 Stream** (sequential lines, ascending or descending). **L1 Stride** ("memory access history of individual instructions … each access is a constant distance from the previous"). **L1 Region** ("access for a given instruction tends to be followed by a consistent pattern of other accesses within a localized region"). **L2 Stream**. **L2 Up/Down** (next or previous line).
- L1 prefetchers fill both L1D and L2; L2 prefetchers fill L2 only.
- L1D is 32 KB, 8-way. L2 is 1 MB, 8-way. *§2.x cache sections.*
- AMD publishes **no** maximum stride, page-boundary rule or stream count. [verified absence in 57647 §2.12.1]
- The GDC 2024 Ryzen talk (Ken Mitchell, slide 25) shows two loads in one AoS loop each getting their own stride stream (`a[i].x1`, `a[i].x2` with a 256 B gap): "stride prefetch 0 / 1". [verified]

**AMD Zen 5** (Hot Chips 2024, Cohen/Subramony): "New 2D stride prefetcher also improves stream and region prefetchers". L1D is 48 KB 12-way; L2 is 1 MB 16-way. [verified slide text] How the 2D stride prefetcher works is not public. Zen 5 SOG 58455 not read. [unverified]

### 1.2 What this means for the three iteration shapes [inference]

Setup: `VehicleLayout` with 4 wheels, slot stride S, chunk C = 16 KiB, n = C/S slots.

| Factor | k leap-frog passes (stride S, base offset i) | Per-slot micro-loop over k contiguous | Gather (index list) |
|---|---|---|---|
| Prefetcher fit | One load IP, constant stride S within a pass. The Intel IP stride prefetcher needs S ≤ 2 KB. Retrains at every pass start, because the base jumps back. Short passes (small n) lose the training cost: Intel says it needs "a couple misses" | Sequential lines within the slot, then a jump of S. Matches the stream prefetchers if S is small. Matches the AMD stride prefetcher per instruction and the region prefetcher ("consistent pattern … within a localized region") | Defeats both stride and stream prefetchers unless indices are sorted. Only useful for sparse subsets |
| Page boundary | 16 KiB = 4 pages. Each pass restarts at most 4 page streams. For S > 4 KB the streamer cannot follow at all | Same 4 pages, crossed once | n/a |
| Lines touched | Same set in total. But if several same-type components share a 64 B line (16 B components: 4 wheels = 1 line), each pass re-touches the same line k times | Each line touched once | Same as micro-loop if sorted |
| Code | One loop body, k = runtime span count. Vectorizes across slots (stride S becomes gather, or scalar) | Inner loop of fixed k; unrolls fully for small k. Vectorizes across the k elements if they are contiguous | — |

- **Chunk fits in L1 (16 KiB < 32/48 KB L1D):** after the first pass the chunk is L1-resident, so k passes cost about k × (n loads at L1 latency) plus loop overhead. That is close to the micro-loop. Leap-frog **loses** only through the re-touch of shared lines (cheap in L1) and per-pass loop overhead, which matters for small n. It **can win** when the per-type work is a separate kernel per pass (different code per index i, or SIMD across slots with masks). [inference]
- **Chunk not in L1 but in L2 (cold chunk, streaming over many chunks):** leap-frog **loses** whenever k same-type components share lines. Pass 1 pulls the line; by pass k it may have been evicted only if the working set between passes exceeds L1. For one 16 KiB chunk it does not, so the loss stays small. The loss grows when chunks are larger than L1 (large archetypes, §7 "large archetypes may need larger chunks"), or when passes are run over all chunks before moving to the next index (pass-major order). Then each line is fetched from L2/LLC/DRAM k times: **k× bandwidth**. [inference]
- **Rule of thumb to test:** iterate **chunk-major** (all k passes on one chunk, then the next chunk), never pass-major across the whole region. With chunk-major order and C ≤ L1D/2, leap-frog and micro-loop should be within noise. With pass-major order, or C > L1D, the micro-loop wins by up to k× on bandwidth-bound kernels. [unverified; this is what the benchmark in §4 must confirm]
- **Stride limit:** slots > 2 KB disable the Intel L1 IP stride prefetcher for leap-frog passes. Slots > 4 KB put each slot on its own page, and the L2 streamer cannot follow a leap-frog pass. The micro-loop still streams within the slot. [verified limits; inference on consequence]
- **AMD:** with no published limits, measure instead. The Zen 5 "2D stride" prefetcher (stride inside a stride) is the hardware match for "micro-loop inside slot stride". This is suggestive only. [summary]

### 1.3 Design consequence [inference]
The span `(base, count, stride)` describes one leap-frog pass. A same-type array of k in a slot is a **2-D span**: `(base, outerStride = S, outerCount = n, innerStride = sizeof(T) or element block, innerCount = k)`. Reporting k separate 1-D spans loses the information a micro-loop needs. Consider a 2-D span form (or `count = n*k` with a documented inner run) before callers start depending on k separate spans.

Note on §6.2: `get<"wheels">()[i].get<"hub">()` resolves relative to the *element sub-block*. If every wheel element carries its hub (`[Wheel0 Hub0][Wheel1 Hub1]…`), the wheels are **not** contiguous: the inner stride is `sizeof(Wheel)+sizeof(Hub)` plus padding. A type-grouped in-slot layout (`[Wheel0..3][Hub0..3]`) makes the inner run dense and keeps `get` a constant offset (`wheelsBase + i*sizeof(Wheel)`, `hubsBase + i*sizeof(Hub)`). See §2.

---

## 2. In-slot layout for N components of the same type: what engines do

None of the surveyed engines stores an entity as one AoS slot. All of them store per-type SoA columns per chunk or table. "N of the same type on one entity" is handled one of four ways:

| Engine | Storage unit | N of same type on one entity | Layout of those N |
|---|---|---|---|
| **Unity Entities 1.x** | Archetype chunk, "Each chunk consists of 16 KiB". "A chunk contains an array for each component type … The arrays of a chunk are tightly packed" [verified] | One component per type. N of a type → `DynamicBuffer<T>` (`IBufferElementData`) [verified] | **Dense per entity, inside the chunk.** Inline capacity defaults to "the number of elements that fit within 128 bytes" and is overridable with `[InternalBufferCapacity]`. Past capacity, "Unity allocates memory outside the chunk and copies"; it "never moves the data back into the chunk", and the inline space stays wasted. Advice: capacity 0 if the size varies a lot [verified] |
| **Unreal Mass** | Archetype chunk, `UE::Mass::ChunkSize` 128 KB ("128 bytes per line and 1024 cache lines"), "pseudo-struct-of-arrays" per fragment [summary: community MassSample README + Quod Soler blog; Epic docs not found] | One fragment per type per entity [inference from "unique combination of fragments"]. Per-chunk data → `FMassChunkFragment`; shared data → `FMassSharedFragment` / `FMassConstSharedFragment` (one value per chunk group) [summary] | N instances → separate entities or an array inside a fragment (heap) [unverified] |
| **flecs v4** | Tables (archetypes), one column per id | Pairs: "a component *can* be added multiple times, as long as the pair is unique", e.g. `e.set<Position>(first, …)`, `e.set<Position>(second, …)`. Pairs are "treated the same way as regular component ids"; "a table type may have multiple occurrences of a relationship" [verified] | **One column per pair**, each dense across entities [inference from "same as regular component ids"]. Wildcard `(Likes, *)` "may return multiple results for each instance": that is k passes, one per column, each over a dense column. Fragmentation warning; `DontFragment` / `Sparse` traits move data out of tables ("trade in query speed for … add/remove speed") [verified] |
| **Bevy 0.16** | Archetype tables (column per component) | One component per type. Hierarchy: `ChildOf(Entity)` on the child and `Children` on the parent; "The current system is one-to-many" [verified] | N wheels → N child **entities**, each in its own table row. The `Children` target holds the entity list (heap) [summary on storage] |
| **EnTT** | Sparse-set pool per type; owning groups "rearrange pools" so owned components are "a bunch of packed arrays … all sorted identically" [verified] | One instance per pool. Named storages: "create multiple pools of the same type" (`registry.storage<velocity>("other"_hs)`) [verified] | N named pools = N dense arrays, each iterated separately: k passes over dense arrays [inference] |

**Takeaways [inference]**
- The SoA engines (flecs pairs, EnTT named pools) give "k passes", but each pass runs over a **dense** array (stride = `sizeof(T)`), not slot stride. The prefetcher cost of our leap-frog does not arise there.
- The engine closest to our sealed slot is Unity's `DynamicBuffer` with inline capacity: **N same-type elements dense-packed per entity** inside chunk storage. That is the micro-loop shape. Unity shows the failure mode too: overflow is permanent and leaves dead space. Our fixed `Count<N>` has no overflow, so it avoids this.
- No surveyed engine scatters same-type components in declaration order. The evidence favours **type-grouped dense runs inside the slot** (wheels together, hubs together) over element sub-blocks. The cost is that `get<"wheels">()[i].get<"hub">()` becomes `hubsBase + i*sizeof(Hub)`. That is still a compile-time constant per `i`, so it still meets anti-goal "no offset-table load".

---

## 3. Actors with many components: collections and instanced geometry

| Engine | Mechanism | What happens to per-object identity | Promotion / demotion |
|---|---|---|---|
| **Unreal: Packed Level Actor** | Static meshes of a Level Instance are "combined to create a single Blueprint Actor that is optimized for rendering"; meshes used repeatedly are grouped into ISM per unique mesh asset (*Level Instancing* and *ISM Component* docs) [summary of official pages] | Gone: the PLA holds only ISM/HISM components (static meshes only). "Break" turns them back into individual static mesh actors [summary] | Editor-time, manual. No thresholds [summary] |
| **Unreal 5.5 / 5.6** | 5.5: a cell transformer gathers "immutable (unreferenced and static mobility) meshes under a single actor and multiple ISM components" [summary: Epic forum staff post]. 5.6 **FastGeoStreaming** (experimental): static geometry that "does not impact gameplay" becomes `FastGeoContainer` (not an `AActor`) and `FastGeoComponent` (not a `UPrimitiveComponent`) [summary: release notes via OC3D and Puget, Epic API page] | Gone at runtime: no actor or component objects; traces cannot report Actor/Component [summary] | Cook/stream-time, eligibility rule = immutable and unreferenced. No runtime demotion documented [summary] |
| **Snowdrop (Avatar, GDC 2024, Simmons)** | "Static Mesh System": "Individual objects are too inefficient. So, take objects at stream time and pack them into groups. Throw away the graph object, or don't create it in the first place. Utilize GPU driven culling (on top of CPU culling)". Scatter instances stored in **SoA**, "17 bytes per-instance" (type index, half scale, fixed-point position, packed quaternion) for 70M objects in 58,000 sectors [verified slides] | Thrown away | **Demotion on demand**: "Destruction is tricky, but rare. Dynamically re-create the full object when destruction is triggered" [verified] |
| **Unity: static batching** | "Combines multiple static meshes into one vertex buffer and one index buffer, using coordinates in world space", ≤ 64,000 vertices per batch. Objects sharing a mesh get a copy each, so it costs extra CPU memory [summary: Unity 6 manual snippet] | Objects remain, but the geometry is frozen | Build-time flag ("static") [summary] |
| **Unity: Entities Graphics** | "Processed entities are added to batches. Unity renders the batches using the SRP Batcher" [verified]. BatchRendererGroup and per-chunk upload details are not on the pages read [unverified] | Entities stay entities | — |
| **Godot MultiMesh** | "A single draw primitive that can draw up to millions of objects"; per-instance transform plus `INSTANCE_CUSTOM`; "no screen or frustum culling possible for individual instances"; workaround "several MultiMeshes for different areas" [verified] | Instances are only buffer entries | Manual, spatial split |

**Promotion/demotion thresholds or hysteresis:** none published by any of these engines. All of them decide at authoring or stream time, by eligibility (static mobility, unreferenced, no gameplay logic). The only runtime path is Snowdrop's one-way demotion on destruction. [verified absence in the sources read; a wider search may find more]

**Recommendation for a "collection actor" of many immutable static-geometry components [inference]**
- The industry pattern is clear: such content **does not stay a per-actor component set**. It is extracted into per-mesh dense instance pools (transform + mesh/material id, SoA, compact encodings like Snowdrop's 17 B) owned by a container that is not a per-component object. Rendering iterates the pools. The actor, if one is kept, holds one handle to its range.
- So "de-optimize into per-type dense pools" is the right call for this content. "Micro-loops over dense-packed components in a shape cluster" fits small fixed k (vehicles, k ≤ ~16). A collection with k in the hundreds is a per-mesh instance pool problem. That falls outside sealed archetypes, and `Count<N>` is the wrong tool for it.
- Demotion: copy Snowdrop. Re-materialize a full actor or component only on a mutating event (destruction, edit). Make it one-way per instance and rebuild the pool lazily. Use per-chunk churn counters (§7 already reserves them) as the input for any later re-pack policy. Hysteresis values would be our own invention, and the benchmark must justify them.

---

## 4. Benchmark matrix

Harness: Google Benchmark in a `Heliogrim-<Bundle>.Test`-style target, Release build. Pin to one P-core. Run on at least one Intel (Golden/Raptor Cove or newer) and one AMD (Zen 4/5) machine. Note: prefetchers can be switched off through MSR 0x1A4 on Intel and BIOS options on AMD (not required, but useful for attribution).

**Factors**
| Factor | Levels |
|---|---|
| Component size `sizeof(T)` | 16, 64, 256 B (plus 48 B: not a line divisor, so it straddles lines) |
| k (same-type count per slot) | 1, 2, 4, 16, 64 |
| Other bytes in slot (actor object + unrelated components) | 0, 256, 2048 B → slot stride S spans ~16 B … >4 KB. Include S just under and over 2 KB and 4 KB |
| In-slot layout | type-grouped dense run vs element sub-block (`[Wheel Hub]×k`) |
| Iteration shape | (a) leap-frog, chunk-major; (b) leap-frog, pass-major across region; (c) per-slot micro-loop (k compile-time and runtime); (d) gather via sorted index list; (e) baseline: dense SoA array of the same total elements |
| Chunk size | 16 KiB, 64 KiB, 2 MiB (large page if available) |
| Residency | hot (region ≤ ½ L1D), L2-resident (≤ ½ L2), LLC, DRAM-streaming (region ≥ 4× LLC). Flush or thrash between reps for the cold cases |
| Kernel | read-only reduce (sum a float field), read-modify-write (integrate position), touch-one-field-of-large-T (8 B of a 256 B component) |
| Live occupancy | 100 %, 50 % random holes (live mask), to see the skip cost |

That is a full factorial of ~5×4×3×2×5×3×4×3×2. Prune it: first run sizes × k × shape × residency at 16 KiB, read-only, 100 % live. Expand only where the shapes differ by > 5 %.

**Report per cell**
- ns per component element and **bytes/cycle against the dense-SoA baseline (e)**. Express the result as "x of ideal".
- Hardware counters: L1D misses, L2 misses, LLC misses, L1/L2 HW-prefetch requests issued and useful (Intel: `L1D.REPLACEMENT`, `L2_RQSTS.*`, `OFFCORE_REQUESTS`; AMD uProf "L2 Hit/Miss from HWPF"), DTLB misses. Collect them via VTune/uProf or PMU wrappers.
- Lines fetched / unique lines touched (detects the k× re-fetch from §1.2).
- Median and p95 over ≥ 30 reps, CPU model and microcode, prefetcher MSR state, page size.

**Decision outputs**
1. Default in-slot layout (type-grouped vs element sub-block).
2. Whether the span API needs a 2-D form, or whether k 1-D spans in chunk-major order are within 5 % of the micro-loop.
3. Chunk-size rule versus slot stride (for example, stride ≤ 2 KB keeps 16 KiB; larger strides move to a larger chunk or a huge page).
4. Threshold k above which an archetype member array should leave the slot for a dense pool (input for §3 and for the shape-cluster design).

---

## References

| # | Source | URL | Read |
|---|---|---|---|
| R1 | Intel 64 and IA-32 Architectures Optimization Reference Manual Vol. 1, 248966-051: §2.1.1.6 LLC Page Prefetcher; §3.7.2/3.7.3 HW prefetching L1/L2; §9.5.2 Hardware Prefetch | https://cdrdv2-public.intel.com/930021/248966-051-optimization-reference-manual-vol1.pdf | verified (text extracted) |
| R2 | Intel Optimization Reference Manual Vol. 2 (earlier generations), 356477: §2.1.7 Data Prefetching (Sandy Bridge) | https://cdrdv2-public.intel.com/821614/356477-Software-Optimization-Manual_V2.pdf | verified |
| R3 | AMD Software Optimization Guide for Zen4, 57647 rev 1.00: §2.12.1 Prefetching of Data; cache sections | https://www.numberworld.org/blogs/2024_8_7_zen5_avx512_teardown/57647_zen4_sog.pdf (mirror; AMD original at amd.com) | verified |
| R4 | K. Mitchell, AMD Ryzen Processor Software Optimization, GDC 2024 (slides 22–25) | https://gpuopen.com/download/GDC2024_AMD_Ryzen_Processor_Software_Optimization.pdf | verified |
| R5 | B. Cohen, M. Subramony, "Next Generation Zen 5 Core", Hot Chips 2024 | https://hc2024.hotchips.org/assets/program/conference/day2/24_HC2024.AMD.Cohen.Subramony.final.pdf | verified |
| R6 | Intel E-core HW prefetch control whitepaper | https://intel.github.io/optimization-zone/hardware/HWPrefetchTuning/ | summary |
| R7 | Unity Entities 1.3: Archetypes concepts | https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/concepts-archetypes.html | verified |
| R8 | Unity Entities 1.3: Dynamic buffers intro; set capacity | https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/components-buffer-introducing.html , …/components-buffer-set-capacity.html | verified |
| R9 | Unity Entities Graphics 1.3 overview | https://docs.unity3d.com/Packages/com.unity.entities.graphics@1.3/manual/overview.html | verified |
| R10 | Unity manual: static batching | https://docs.unity3d.com/Manual/DrawCallBatching.html | summary |
| R11 | Mass community sample (Megafunk) README | https://github.com/Megafunk/MassSample | verified (secondary, not Epic) |
| R12 | Quod Soler, Entities and Fragments in Mass | https://www.quodsoler.com/blog/understanding-entities-and-fragments-in-unreal-engine-mass | summary |
| R13 | flecs Relationships manual | https://www.flecs.dev/flecs/Relationships.html | verified |
| R14 | flecs Component Traits (Sparse, DontFragment) | https://www.flecs.dev/flecs/ComponentTraits.html | verified |
| R15 | Bevy 0.16 release notes (Relationships) | https://bevy.org/news/bevy-0-16/ | verified |
| R16 | EnTT wiki: Entity Component System (groups, named storage) | https://github.com/skypjack/entt/wiki/Entity-Component-System | verified (first 100k chars) |
| R17 | Epic: Level Instancing (Packed Level Actor) | https://dev.epicgames.com/documentation/unreal-engine/level-instancing-in-unreal-engine | summary |
| R18 | Epic: Instanced Static Mesh Component | https://dev.epicgames.com/documentation/unreal-engine/instanced-static-mesh-component-in-unreal-engine | summary |
| R19 | Epic forum: Level Instance vs PLA vs ISM/HISM (5.5 immutable gathering, 5.6 FastGeo) | https://forums.unrealengine.com/t/when-to-use-level-instance-packed-level-actor-or-ism-hism-in-ue5/2681508 | summary |
| R20 | FastGeoStreaming API / UE 5.6 coverage | https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/FastGeoStreaming/FFastGeoStreamingModule , https://overclock3d.net/news/software/unreal-engine-5-6-fixes-critical-performance-issues/ | summary |
| R21 | J. Simmons, "Upgrading the Snowdrop Engine for the Massive World of Avatar", GDC 2024 slides | https://media.gdcvault.com/gdc2024/Slides/GDC+slide+presentations/Simmons_Joshua_Upgrading_the_Snowdrop.pdf | verified |
| R22 | Godot docs: Optimization using MultiMeshes | https://docs.godotengine.org/en/stable/tutorials/performance/using_multimesh.html | verified |

Corrections found while tracing:
- A search snippet claimed Snowdrop stores "9 bytes per instance". The slides say **17 bytes**: it adds an 8-byte packed quaternion (R21).
- A search snippet attributed the "three independent L1 prefetchers" text to Golden Cove. Its context (24→32 KB L1D) points to an E-core section. That claim is not used here.

Not done: Zen 5 SOG 58455 prefetch section; Epic Mass official docs; Unity BRG internals; any measurement on real hardware.
