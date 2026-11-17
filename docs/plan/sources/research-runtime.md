# Research: scheduling, streaming, open world, networking

**Status**: <span class="hg-status summary">sources</span>. Collected 2026-11-07 by a research agent for the battle plan. Claims are marked verified or unverified; nothing here is a decision.

## Method and caveat

Two passes. Pass 1 (2026-11-07) opened 8 pages. Pass 2 (same day, see "Verification pass" at the end) opened landing pages, abstracts or docs for most remaining sources; inline markers below were updated where pass 2 changed them. Markers: `verified (full text)`, `verified (abstract/landing page)` (bibliographic data and abstract only, body claims not checked), `unverified`. Bibliographic data for ACM/Semantic Scholar entries came from search-result summaries, not from the publisher page itself, and is marked as such. Re-open before quoting any number. No forum/blog-only claims are used as evidence. Where a source is an author's own site (Fiedler) it is treated as primary for his own work.

Opened this run (verified):
- RFC 9000, Iyengar and Thomson (eds.), IETF, May 2021, https://www.rfc-editor.org/rfc/rfc9000.html (abstract only; first 100k of 447k chars read).
- Fiedler, "Floating Point Determinism", gafferongames.com, 2010, https://gafferongames.com/post/floating_point_determinism/
- Fiedler, "Snapshot Compression", gafferongames.com, Jan 2015, https://gafferongames.com/post/snapshot_compression/
- Microsoft, "DirectStorage Overview" (Xbox GDK, Xbox Series only), Microsoft Learn, updated 2026, https://learn.microsoft.com/en-us/gaming/gdk/_content/gc/system/overviews/directstorage/directstorage-overview
- Epic Games, "Large World Coordinates Rendering in Unreal Engine 5", UE docs, https://dev.epicgames.com/documentation/en-us/unreal-engine/large-world-coordinates-rendering-in-unreal-engine-5
- Linux kernel docs, "EEVDF Scheduler", https://docs.kernel.org/scheduler/sched-eevdf.html
- Agones docs index (v1.62.0), https://agones.dev/site/docs/
- Nishanov, WG21 P1364 (2018-11-25 PDF), https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1364r0.pdf : only metadata/references extractable; body NOT read. Treat its conclusions as unverified.

---

## 1. Fiber and job schedulers

State of the art
- Fiber-based job systems (Naughty Dog, Gyrling GDC 2015): a fixed worker thread per core, each running fibers; a job that waits on a counter switches fibers instead of blocking the thread. Counter-based dependencies. verified (abstract/landing page) for title, speaker, org, year: GDC Vault, "Parallelizing the Naughty Dog Engine Using Fibers", Christian Gyrling, Naughty Dog, GDC 2015, https://gdcvault.com/play/1022186. The page describes the fiber job system, frame-centric design, memory allocation patterns and lock handling used to reach 60 fps for The Last of Us Remastered on PS4. The "worker thread per core" and "counter" details above are NOT on the landing page (slides/video not opened): unverified.
- Fiber benefit is writing "blocking-looking" code on a non-blocking scheduler; cost is stack memory per fiber, no TLS safety, and no OS awareness (profilers, debuggers, TLS, thread-affine APIs). unverified.
- Bungie (Destiny): talks describe a job system with task graphs and explicit dependencies. unverified; exact talk title and year not confirmed (GDC Vault, Bungie, ~2015).
- Frostbite: frame graph / task graph model ("FrameGraph: Extensible Rendering Architecture in Frostbite", O'Donnell, GDC 2017) is rendering-side dependency scheduling rather than a general scheduler. unverified.
- Work stealing: Blumofe and Leiserson, "Scheduling Multithreaded Computations by Work Stealing", JACM 1999 (expected time T1/P + O(T_inf) for fully strict computations; JACM 46(5), 720-748). verified (abstract/landing page; via search summary of ACM DL doi 10.1145/324133.324234). Chase and Lev (Sun Microsystems), "Dynamic Circular Work-Stealing Deque", SPAA 2005, pp. 21-28, doi 10.1145/1073970.1073974: lock-free deque in a growable cyclic array, owner push/pop at bottom, thieves CAS at top; builds on ABP. verified (abstract/landing page; via search summary, ACM page itself not opened). Lê, Pop, Cohen, Zappa Nardelli, "Correct and Efficient Work-Stealing for Weak Memory Models", PPoPP 2013, pp. 69-80: C11-atomics implementation and proof of the Chase-Lev deque. verified (abstract/landing page; via dblp/search summary). Note: the authors list an errata for the paper, and a blog (Wingo, 2022) reports a bug in the paper's code that is not in Chase-Lev; check the errata before copying orderings. "Matters for ARM, less for x86" is unverified.
- EEVDF: Stoica and Abdel-Wahab, 1995 (earliest eligible virtual deadline first). Linux 6.6 replaced CFS; eligibility by lag >= 0, pick earliest virtual deadline, tasks can request slice length via `sched_setattr()`, sleeping tasks keep lag decaying via deferred dequeue. verified (kernel docs). Relevance is as a fairness/latency model for a user-space scheduler, not as something we run.
- C++ coroutines vs fibers: coroutines are stackless, compiler-transformed, allocation per frame (elidable), composable with executors (P2300 std::execution), no per-task stack. Fibers are stackful, can suspend from nested calls, need a context-switch asm layer (Boost.Context). P1364 "Fibers under the magnifying glass" (Nishanov, 2018) is a critique of fibers for standardization; references Go/Rust green-thread retreats and Boost.Context. Metadata/reference list verified; pass 2 re-fetched the PDF (10 pages, Word-generated, author contact gorn@microsoft.com, created 2018-11-25) but the body is Flate-compressed and not extractable by the fetch tool, so conclusions remain unverified (it appears to be a WG21 paper; embedded links cover Go, Rust green-thread removal, Boost.Context/Fiber, Win32 fibers, UMS).
- Windows specifics: Win32 Fibers exist (ConvertThreadToFiber); UMS (user-mode scheduling) is deprecated from Windows 11 (unverified). Custom asm switch (Boost.Context style) is the common route.
- Thread-affinity bridging: IO completion threads, window/message pump, GPU submit threads, audio threads must stay OS threads. Pattern: a fiber posts a request to a queue owned by the affine thread and parks on a counter/event; completion handler resumes it by enqueuing it back to the job system. DirectStorage already works this way (status array, fence, event notification; completion is FIFO per queue). verified (DirectStorage doc).
- Deterministic lockstep scheduling: a deterministic sim needs job results independent of worker count/steal order: fixed partitioning, fixed reduction order, no float atomics, stable sort. unverified as practice; see section 6.

Applicability to Heliogrim
- Planned model (fibers + dedicated IO/pump threads) matches shipped precedent; the risk is tooling and thread-affine APIs, not throughput.
- Define a single "affine service" abstraction: request queue to a pinned thread, completion = counter decrement that resumes waiters. Reuse for IO, Vulkan queue submit, platform pump, audio.
- Evaluate stackless coroutines for leaf-level async (IO continuations, network) and fibers only where deep-stack blocking is needed; both can sit on the same worker pool.
- Keep a scheduling-policy seam (FIFO per priority now; deadline/lag-aware later) so EEVDF-like fairness for background streaming vs frame jobs can be tried.
- Fibers must not hold thread_local state or Vulkan/COM thread-affine objects across switch points; needs a lint/assert strategy.

Open risks / measure
- Fiber switch cost vs coroutine resume on clang-cl/Windows; stack size distribution; cost of stack guard pages.
- Debugger/profiler visibility (Tracy fiber support, VS/CLion stack view) before committing.
- Work-stealing deque correctness under TSan-equivalent testing on Windows (no TSan with clang-cl in many setups: verify).
- Priority inversion between frame jobs and IO-completion resumes.
- Whether deterministic mode needs a separate scheduler configuration (single-thread or fixed partition).

---

## 2. Asset streaming

State of the art
- DirectStorage (Xbox GDK doc, verified): batched queues, lock-free; design goal 50,000 requests/s at <=10% of one core; hardware decompression (zlib, BCPACK, swizzle on Xbox); priorities real-time/high/normal/low with ~10x weighted round-robin; best-effort cancellation via 64-bit tag mask (`tag & mask == value`); FIFO completion notification via status array/fence/event; do not throttle queue depth, submit everything; read-size sweet spot 32 to 64 KiB on NVMe, prefer many parallel requests over one huge one above 512 KiB when decompressing; default 32 MiB staging buffer; minimum guarantee 2.0 GB/s over 250 ms (console). Caveat: this page is the Xbox variant; the PC API differs (GPU decompression via compute, GDeflate).
- DirectStorage on PC and GDeflate: verified (landing page) at https://github.com/microsoft/DirectStorage: repo ships a GDeflate reference implementation (codec + samples), BulkLoadDemo (GPU decompression and custom CPU decompression), GpuDecompressionBenchmark (compares GPU vs CPU bandwidth and CPU usage on your machine), an experimental zstd GPU-decompression reference ("under active development, not for production"); read-only API; MIT; samples need VS 2022. The README gives NO Windows version list and no benchmark numbers (only the motivation that fast storage can deliver "multiple gigabytes a second of small (eg 64kb) data reads"). Secondary sources (news summaries of the DirectX Developer Blog post of 2022-11-07, blog itself not opened): DirectStorage 1.1 added GPU decompression; needs DX12 + Shader Model 6.0 GPU; Windows 10 1909+ or Windows 11 (Win11 has the better storage stack); sample 5.65 GB in 0.8 s GPU vs 2.36 s CPU (hardware not stated, treat as unverified). The Xbox GDK page itself says it covers Xbox Series X|S only and points to aka.ms/directstorage for desktop. The original desktop Learn pages were not opened (guessed URL 404).
- Windows IOCP / overlapped IO: standard completion model; unbuffered IO needs sector alignment (verified indirectly: doc says Win32 asynchronous reads needed 4 KiB alignment). Learn.microsoft.com "I/O Completion Ports". unverified (page not opened).
- io_uring: Axboe, "Efficient IO with io_uring", 2019, https://kernel.dk/io_uring.pdf. unverified. Linux-only; relevant for the headless/Linux server target. verified (abstract/landing page, via search): PDF "Efficient IO with io_uring", version 0.4 dated 2019-10-15 (first announced April 2019, Linux 5.1); covers io_uring_setup, fixed buffers, IOPOLL, SQPOLL. The URL kernel.dk/io_uring.pdf has been reported 404 at times (liburing issue); a Wayback copy exists. Windows analogue is IoRing, `ioringapi.h`. CORRECTION: Microsoft Learn lists minimum client/server "Windows Build 22000" (Windows 11 21H2), not 22H2. verified (Learn header page): submission queue + completion queue, functions include BuildIoRingReadFile, BuildIoRingRegisterBuffers/FileHandles, BuildIoRingCancelRequest, SubmitIoRing, PopIoRingCompletion, SetIoRingCompletionEvent, QueryIoRingCapabilities. Header page lists no write op in this index (BuildIoRingReadFile only); per-function pages not opened.
- Unreal: IoStore / Zen (Epic): container files with chunk IDs, offset-sorted reads, on-demand streaming, Zen Store for editor/cook cache. unverified (Epic docs and Unreal Fest talks; exact page not opened).
- Nanite streaming: cluster-DAG pages streamed on demand, fixed-size pages, GPU requests residency feedback. Karis, Stubbe, Wihlidal, "A Deep Dive into Nanite Virtualized Geometry", SIGGRAPH 2021 (Advances in Real-Time Rendering). unverified.
- Sparse / virtual textures: Mittring, "Advanced Virtual Texture Topics", SIGGRAPH 2008 (CryEngine 3). Barrett, "Sparse Virtual Textures", GDC 2008. van Waveren, "id Tech 5 Challenges", SIGGRAPH 2009. Chajdas et al., "Subdivision Surfaces/ Virtual texturing", 2010 (title not confirmed). All unverified. Vulkan `sparseBinding`/`sparseResidency` features provide hardware paths but tile-update cost and queue sync are real.
- Residency/LRU budgets: feedback-buffer-driven requests, per-frame upload budget, LRU or clock eviction with a pinned low-mip fallback. unverified (common to all VT talks).
- mmap vs explicit IO: Crotty, Leis, Pavlo, "Are You Sure You Want to Use MMAP in Your Database Management System?", CIDR 2022 (Chaminade, Jan 9-12), p13. verified (abstract/landing page, via search; https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf, benchmarks at github.com/viktorleis/mmapbench): abstract says mmap has severe correctness and performance issues, several DBMSs abandoned it, and Linux page cache/mmap cannot reach the bandwidth of modern (PCIe 5.0-class) NVMe. The specific list "page-fault stalls, TLB shootdowns, no IO error control" is from recall of the body, unverified here. Applies to a game: faults on a fiber worker block the whole thread.
- Compression: Oodle Kraken/Mermaid/Selkie (RAD Game Tools): decode speed high, ratio between zlib and LZMA; vendor benchmarks only. zstd (Collet, Meta; RFC 8878): verified (landing page) README table, lzbench in-memory, Silesia corpus, Core i7-9700K @ 4.9 GHz, Ubuntu 24.04, gcc 14.2.0: zstd 1.5.7 -1 ratio 2.896, 510 MB/s compress, 1550 MB/s decompress; lz4 1.10.0 2.101, 675 / 3850 MB/s; zlib 1.3.1 -1 2.743, 105 / 390; brotli 1.1.0 -1 2.883, 290 / 425; zstd --fast=4 2.146, 665 / 2050. Vendor-stated, single machine. Oodle (RAD/Epic public page radgametools.com/oodlecompressors.htm), vendor-stated only: Kraken "3-5x faster [decode] than zlib with way more compression", Mermaid "5-10x faster than zlib", Selkie "faster than LZ4 but with better compression"; no hardware or corpus given in text. Must be measured on our own asset mix.
- Cache tiers: memory -> local disk cache -> remote (CDN/object store) with content-addressed chunks (Unreal Zen/DDC, Steam depot chunking pattern). unverified.

Applicability to Heliogrim
- Design the IO layer around a DirectStorage-shaped interface even on the fallback backend: batch queues, per-queue priority, tag-mask cancellation, in-order completion notifications, memory-sourced decompression queue. The verified doc gives a concrete API shape.
- Content-addressed, chunked asset packages sized to 64 KiB multiples, with the compression unit chosen so decompression parallelises (many requests, not one big one).
- Backends: Windows (DirectStorage with IOCP fallback), Linux headless (io_uring), generic (thread pool + pread). Keep the backend behind the affine-thread seam from section 1.
- Residency manager as a first-class service with explicit budgets (disk->RAM->VRAM), pinned fallback mip/LOD, hard cap on speculative loads (doc explicitly recommends hard limits).
- Avoid mmap as the primary path; allow it for read-only tool/editor use only.

Open risks / measure
- PC DirectStorage vs plain overlapped IO throughput on target NVMe and SATA; GPU decompression cost against the frame budget (async compute contention).
- Codec choice: compression ratio vs decode MB/s per core vs license (Oodle is commercial). Measure zstd, LZ4, GDeflate on real Heliogrim assets.
- Cancellation races: freeing buffers only after a later FIFO notification (verified rule).
- Streaming hitching in the editor: asset import pipeline vs runtime format.
- Remote cache latency and integrity (hash verification cost).

---

## 3. Open world / MMO single shard

State of the art
- EVE Online: single-shard universe, but each solar system is served by one node; heavy systems get dedicated nodes; Time Dilation (introduced 2011, "TiDi") slows simulation to keep a fight consistent rather than shed load. Stackless Python for cooperative tasklets. unverified (CCP dev blogs and GDC/Fanfest talks; those are partly blog sources: treat as weak until a talk with slides is found).
- Improbable SpatialOS: workers with authority per entity, a runtime that manages entity components and interest ("checkout") radius, authority delegation among workers. unverified; docs now archived/retired, so confirm availability.
- Dual Universe (Novaquark): single-shard claim with a custom server using voxel construct grids and cell-based distribution. unverified (talk titles not confirmed).
- Star Citizen server meshing (CIG, CitizenCon talks): dynamic mesh of game servers handing entity authority across a replication layer ("Replication Layer" + "Entity Graph"), ongoing, rollout partial. unverified; marketing-adjacent, discount.
- Interest management: Boulanger, Kienzle, Verbrugge, "Comparing Interest Management Algorithms for Massively Multiplayer Games", NetGames 2006 NetGames '06 (5th ACM SIGCOMM workshop, Singapore, Oct 2006), doi 10.1145/1230040.1230069. verified (abstract/landing page, via search summary): compares interest management algorithms on measurements from a real MMOG (McGill's Mammoth framework) using human and generated players; reports obstacle-aware algorithms cut update messages by up to a factor of 6, and cheap tile-based algorithms approximate ideal visibility-based IM. The "grid/cell, aura, hybrid" taxonomy is from recall, unverified. The factor-6 figure is from a secondary summary of the abstract; confirm on ACM.
- Spatial partition + handover: static grid/tiles with ghost/overlap zones; authority migration on boundary crossing with a transactional state transfer. unverified (common in literature). Bharambe, Pang, Seshan (CMU), "Colyseus: A Distributed Architecture for Online Multiplayer Games", NSDI '06, pp. 155-168: verified (abstract/landing page, via search): exploits weak consistency and predictable workload, game-object manager with a DHT location service, aimed at FPS games. It is a distributed-object/replica design, not a ghost-zone grid handover.
- Large-world coordinates, verified from Epic docs: UE5 uses double-precision on CPU and emulated double on GPU (DoubleFloat: pairs of floats, "High" and "Low"); legacy tile+offset (tile 256k) had precision loss near boundaries; recommended practice is converting to camera-relative "translated world space" as early as possible so plain floats suffice; LWC math in materials is slower than float and camera-relative origin restores speed.
- Persistence/DB: write-behind to a transactional store, per-region snapshot + event journal, authoritative game state in memory. unverified (EVE uses SQL Server per public statements; not opened).

Applicability to Heliogrim
- Large world: use double (or int64 sector + float local) for CPU-side world positions; render camera-relative in floats. UE5's guidance supports camera-relative rendering over emulating double on GPU where avoidable.
- Cell grid with overlap ghost zones and explicit authority tokens per entity fits the existing ACS/actor model; define authority as data on the entity, not on the process.
- Interest management should be a replaceable policy (grid default, aura/priority later) fed by the same spatial index used for streaming residency, so streaming and replication share one query.
- Single-shard at scale needs a load-shedding story decided early: time dilation (EVE-style), instance splitting, or tick-rate degradation.
- Persistence: journal + snapshot per cell; design entity serialization to double as migration payload.

Open risks / measure
- Cost of an authority handover under load (latency, state size, duplicate-actor windows).
- Hot spots: unbounded density in one cell breaks any partition; need admission/limits.
- Double vs int64+float precision in physics broadphase, nav, and audio.
- Interest management CPU per tick vs entity count (measure at 10k/100k/1M entities).
- Evidence quality: CCP/CIG/Novaquark claims are largely talk/marketing; replace with measured data from our own prototypes.

---

## 4. Realtime networking

State of the art
- Snapshot interpolation + delta compression (Fiedler, verified): 901 cubes at 60 Hz, absolute 321 bits/cube = 17.37 Mbps; smallest-three quaternion 128->29 bits; bounded position 96->50 bits; delta against the last acked baseline (about 1 RTT old); idle steady state ~15 kbps (mostly headers); final delta-coded cube ~26 bits position, ~23 bits orientation; a context-aware arithmetic coder beat bit-packing by ~25% (credit Giesen). The target was 256 kbps.
- Fiedler, "Networked Physics" GDC 2015 and gafferongames.com series (snapshot interpolation, state synchronization). Series page structure verified only for snapshot compression; other parts unverified.
- Overwatch (Tim Ford, "Overwatch Gameplay Architecture and Netcode", GDC 2017): ECS-based, command frames, client prediction with input buffering, server-side lag compensation. Numbers (server 60 Hz tick) unverified. https://gdcvault.com/play/1024001 : verified (abstract/landing page, via search): GDC 2017, Timothy Ford, Blizzard, Programming track, free. Official overview: ECS architecture, networked simulation that "leverages determinism to achieve responsiveness and precision". CAVEAT: community commentary (GitHub issue, HN) says Overwatch is not deterministic in the fighting-game sense; floats are quantized so mispredictions are rare. Treat "deterministic" as marketing-adjacent until the video is watched. Command frames/input buffering/lag compensation details remain unverified.
- Halo: Reach (Bungie, "I Shot You First: Networking the Gameplay of HALO: REACH", David Aldridge, GDC 2011, https://gdcvault.com/play/1014346): talk existence, speaker, org, year verified (landing page, via search). Body claims (prioritised replication under a bandwidth budget, priority accumulators) unverified.
- Quake 3 delta snapshots (Q3 network model; Fabien Sanglard code review, plus id source): delta against last acked snapshot with field-change bitmasks. unverified (not opened; Sanglard is a blog, use id source for primary).
- Rollback netcode (GGPO, Cannon): predict remote input, rewind and resimulate on mismatch; requires deterministic fast resim. unverified.
- QUIC: RFC 9000 (verified abstract): flow-controlled streams, low-latency connection establishment, connection migration, built-in security. Companion RFCs: 9001 (TLS), 9002 (loss/CC), 9221 (DATAGRAM extension, unreliable datagrams over QUIC). HTTP/3 RFC 9114, HTTP/2 RFC 9113, WebTransport (IETF draft + W3C). Pass 2 verified (abstract/landing page, rfc-editor.org; body not read): RFC 9001 "Using TLS to Secure QUIC" (Thomson, Turner eds., May 2021); RFC 9002 "QUIC Loss Detection and Congestion Control" (Iyengar, Swett eds., Fastly/Google, May 2021; NewReno-style controller); RFC 9221 "An Unreliable Datagram Extension to QUIC" (Pauly, Kinnear, Schinazi, Mar 2022); RFC 9113 "HTTP/2" (Thomson, Benfield eds., Jun 2022; obsoletes 7540 and 8740); RFC 9114 "HTTP/3" (Bishop ed., Akamai, Jun 2022). WebTransport not checked: unverified.
- DTLS 1.3: RFC 9147 (Rescorla, Tschofenig, Modadugu, Apr 2022, obsoletes RFC 6347): verified (abstract/landing page); abstract notes equivalent guarantees to TLS 1.3 except order protection/non-replayability.
- Custom UDP layers: netcode (Fiedler, github.com/mas-bandwidth/netcode; "secure client/server protocol for multiplayer games built on top of UDP"; connect tokens, libsodium encryption/signing, replay and amplification protection, fixed client slots; netcode 1.02 standard; BSD-3) and yojimbo (github.com/mas-bandwidth/yojimbo; C++, single-threaded, unreliable-unordered and reliable-ordered messages, blocks attached to reliable messages, fragmentation, connect tokens, aimed at <=100 players, README says "stable and production ready"). verified (landing page/README). Org is now `mas-bandwidth` (older `networkprotocol` URLs may redirect). netcode.io site itself not opened.
- Anti-cheat basics: server-authoritative state, input validation, encrypted + authenticated packets, replay protection; client integrity is a separate (platform) problem. unverified.
- Bandwidth/tick numbers from shipped games (Overwatch 60 Hz, CS2 sub-tick, Valorant 128 Hz servers, Fortnite 30 Hz default): unverified; vendor/dev statements, verify per-game before use.

Applicability to Heliogrim
- Two protocol families as planned: HTTP stack (HTTP/2, HTTP/3 over QUIC) for control/asset/API; custom UDP protocol for the realtime channel. Consider QUIC DATAGRAM (RFC 9221) and WebTransport as a possible alternative to a fully custom UDP layer, at the cost of control over congestion behaviour and per-packet overhead.
- Replication design: acked-baseline delta snapshots with quantisation and per-entity priority/accumulator budgets (Fiedler + Halo Reach pattern). Quantisation ranges belong in component schemas, not the transport.
- Separate reliable-ordered (commands, spawns) from unreliable (state) channels; keep message encoding schema-driven so server and client share one definition.
- Security from day one: authenticated, encrypted packets with connect tokens; do not bolt on later.
- Rollback only if the game genre needs it; it forces determinism (section 6) and a resimulatable state split.

Open risks / measure
- Per-entity bytes/tick and CPU for delta encoding at target interest sizes.
- QUIC library choice (msquic, quiche, ngtcp2, lsquic) vs writing UDP layer: license, Windows IOCP behaviour, footprint. Not researched here.
- NAT traversal, MTU (~1200 byte safe payload for QUIC initial), loss/jitter profiles.
- DTLS vs custom AEAD (ChaCha20-Poly1305/AES-GCM) cost and replay window handling.
- Tick-rate vs scale: single shard with 1000s of visible entities may force sub-60 Hz and tiered rates.

---

## 5. Headless / server / cluster mode

State of the art
- Unreal: dedicated server via a separate `<Project>Server.Target.cs` build target ("Development Server" config; cook with Build Target = Server): verified (landing page, UE 5.8 "Setting Up Dedicated Servers in Unreal Engine"). That page says a headless server "does not render any visuals" by being a Server build and does NOT mention `-server`, `-nullrhi` or `-unattended` (it links to a Command-Line Arguments page). Those flags and commandlets: unverified.
- Unity: Dedicated Server build target / headless mode, Netcode for Entities server world. unverified.
- Godot: `--headless` is documented as "Enable headless mode (`--display-driver headless --audio-driver Dummy`). Useful for servers and with `--script`"; mandatory for export on systems without GPU access. verified (Godot stable CLI docs). Dedicated-server export presets: unverified.
- Agones (verified, docs v1.62.0): Kubernetes library for hosting/scaling dedicated game servers. CRDs: GameServer, Fleet, FleetAutoscaler; GameServerAllocation to claim a ready server; Allocator Service and multi-cluster allocation; health checking; counters and lists; Windows game server support; SDKs for Unreal, Unity, C++, Go, C#, Node.js, Rust, Python plus REST.
- Worker nodes for cooking/baking: Unreal Horde (distributed build/automation, agents, pools; Epic open-sourced), UBA (Unreal Build Accelerator), Incredibuild (commercial). unverified.
- Observability: OpenTelemetry (CNCF) traces/metrics/logs with OTLP; game fleets also need per-tick histograms and per-region metrics. verified (landing page, https://opentelemetry.io/docs/specs/otel/, spec v1.62.0): API (context, baggage, tracing, metrics, logs), SDK, data spec (semantic conventions, OTLP). Game-specific histogram advice is our inference.

Applicability to Heliogrim
- Headless should be a build-time/runtime composition of existing bundles (no RHI, no window, no audio) rather than a fork. The layering in ARCHITECTURE.md decides feasibility; check that nothing in Engine.Core pulls in GFX.
- A server process mode must expose a health/ready/shutdown contract that maps cleanly onto Agones SDK calls (ready, health ping, allocated, shutdown). Even for a single-shard design, workers (cell servers, cook workers) benefit from the same contract.
- Cook/bake jobs as stateless workers pulling work from a coordinator, results into content-addressed cache (same cache tiers as section 2).
- Instrument with OpenTelemetry-compatible spans/metrics from the start; the scheduler (section 1) is the natural place for job-level tracing.

Open risks / measure
- Dependencies on Vulkan/GLFW/OS window in non-GFX bundles.
- Memory footprint and startup time of a headless worker (cold start matters for autoscaling).
- Agones fit for a single-shard cluster whose servers are long-lived and stateful (Agones is aimed at session-based servers); an own orchestrator or plain Kubernetes StatefulSets may fit better. Not researched.
- Windows containers/hosting limits vs Linux for servers; cross-platform build burden.

---

## 6. Determinism and replay

State of the art
- Fiedler, "Floating Point Determinism" (verified): same compiler, same build settings, same ISA is the baseline; debug vs release or a newer compiler can break replays; use strict FP modes (`/fp:strict`, `-fp-model strict`); x87 control word must be pinned and re-asserted each tick since external DLLs (Direct3D, drivers) can change it; SSE preferred over x87; FMA contraction and approximate reciprocal/rsqrt differ across architectures; transcendentals and libm are not reproducible across vendors/implementations (Battlezone 2 fix: wrapped calls in non-optimized single-precision code); beware physics solvers with CPU-speed-dependent iteration counts and implementation-defined integer modulo.
- Physics engines (verified, docs pages). Rapier (rapier.rs determinism guide): locally deterministic by default (same machine, same Rapier version, same Rust compiler, same insertion order); the `enhanced-determinism` feature gives cross-platform identical results ONLY if targets comply with IEEE 754-2008 and the app uses nalgebra `ComplexField` transcendental functions instead of std ones; it is incompatible with `simd8`; `parallel` is compatible and independent of thread count. CORRECTION: earlier text said "software libm-style math"; the guide frames it as IEEE 754 compliance plus nalgebra math for inputs. Jolt (jrouwe.github.io/JoltPhysics, Deterministic Simulation): same binary + same call order is deterministic, AMD vs Intel irrelevant; CMake `CROSS_PLATFORM_DETERMINISTIC` costs "roughly 8%" (vendor-stated) and removes dependence on compiler, OS, architecture, word size; requires `-ffp-model=precise` / `/fp:precise`, `-ffp-contract=off`, consistent rounding and DAZ/FTZ, and Jolt's own Sin/Cos/QuickSort/Hash instead of std equivalents; broadphase queries, contact/activation callbacks and GetActiveBodies order are NOT deterministic across threads; CI checks 14 configurations; Samples "Check Determinism" feature is "less tested".
- Deterministic scheduling: results independent of thread count requires fixed work partition and ordered reductions. unverified as practice.
- Replays: Unreal Replay System (UE 5.8 docs "Using the Replay System in Unreal Engine", verified landing page): `DemoNetDriver` reads replicated data like a NetDriver and hands it to a Replay Streamer; any replicating project is compatible; dedicated servers record via `AGameMode::bHandleDedicatedServerReplays`, else `StartRecordingReplay`/`demorec`; playback `PlayReplay`/`demoplay`, `GotoTimeInSeconds`; replays survive added/removed replicated properties since 4.13, custom `NetSerialize` needs manual versioning via `EngineNetVer`/`GameNetVer`. Overwatch replays: client-side re-simulation with the server's recorded data, per the GDC 2017 talk. unverified.
- Test automation: replay or recorded input as regression tests, with state-hash checks per tick to find the first divergence. unverified (common practice, source to be found).

Applicability to Heliogrim
- Decide determinism scope explicitly: (a) same-binary replay only (cheap, achievable per Fiedler), (b) cross-machine same-compiler, (c) cross-platform bit-exact (expensive, constrains math and physics). Network rollback needs (b) at least; MMO server authority needs none.
- Simulation state must be separable from presentation state, with a per-tick state hash exposed for tests.
- Build flags: pin FP model for sim bundles, ban `/fp:fast` there, audit libm usage (sin/cos/pow) and replace with in-tree implementations if (b) or (c) is a goal.
- Replay by recording the network/command stream gives test automation and debug repro for free if the replication format is stable and versioned.

Open risks / measure
- clang-cl vs MSVC differences, auto-vectorisation reordering, FMA contraction defaults on clang (`-ffp-contract`) : measure divergence with a state-hash harness across debug/release and across CPUs (Intel vs AMD).
- Cost of strict FP on sim hot paths.
- Third-party vendored libraries (physics, math) that use fast-math or intrinsics.
- Replay format versioning across engine revisions (old replays break).

---

## Source reliability summary

- Verified (full text or substantial docs): Fiedler (two articles), DirectStorage Xbox GDK doc, UE5 LWC doc, Linux EEVDF doc, Agones docs index, Jolt determinism section, Rapier determinism guide, zstd README table, Godot `--headless`, UE replay and dedicated-server pages, DirectStorage GitHub README.
- Verified (abstract/landing page only; body claims not checked): RFC 9000/9001/9002/9113/9114/9147/9221, Gyrling GDC 2015, Blumofe-Leiserson, Chase-Lev, Lê et al., Axboe io_uring paper, IoRing header page, Crotty et al. mmap, Boulanger et al., Colyseus, Ford GDC 2017, Aldridge GDC 2011, netcode/yojimbo READMEs, OpenTelemetry spec index, Oodle vendor page.
- Still unverified: P1364 conclusions (PDF body not extractable), Gyrling slide contents, Overwatch tick rate and replay claims, Halo Reach talk body, desktop DirectStorage Learn pages and Windows version list (only secondary sources), UE `-nullrhi`/`-server`, Unity, WebTransport, EVE/SpatialOS/Dual Universe/Star Citizen, Nanite/VT/IoStore papers and docs, Bungie job-system talk, Frostbite FrameGraph, UMS deprecation, quantified bandwidth/tick numbers of shipped games.
- Corrections made in pass 2: IoRing minimum is Windows build 22000 (not 22H2); Rapier enhanced-determinism relies on IEEE 754 compliance plus nalgebra math, not software libm; Overwatch "determinism" is contested by community commentary; Lê et al. has errata; Unreal dedicated-server docs do not mention `-nullrhi`.
- Weak-evidence areas (marketing or blog-grade): EVE, Star Citizen, Dual Universe architecture claims; Fanfest/CitizenCon talks should be located as video + slides before citing.

---

## Verification pass (2026-11-07)

Status key: FT = full text / substantial doc read; AB = abstract or landing page only; UN = still unverified.

| # | Source | Status | URL | Notes |
|---|---|---|---|---|
| 1 | Gyrling, Naughty Dog fibers, GDC 2015 | AB | https://gdcvault.com/play/1022186 | Title, speaker, org, year confirmed; slides not opened |
| 2a | Blumofe, Leiserson, JACM 46(5) 1999 | AB | https://dl.acm.org/doi/10.1145/324133.324234 | T1/P + O(T_inf), fully strict computations |
| 2b | Chase, Lev, SPAA 2005 | AB | https://dl.acm.org/doi/10.1145/1073970.1073974 | via search summary |
| 2c | Lê et al., PPoPP 2013 | AB | https://dblp.org/rec/conf/ppopp/LePCN13 | errata exists |
| 3 | Nishanov P1364R0 | UN | https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1364r0.pdf | PDF body compressed, unreadable by tool |
| 4a | DirectStorage GitHub | AB | https://github.com/microsoft/DirectStorage | GDeflate, GPU decompression samples, no versions or numbers |
| 4b | DirectStorage Xbox GDK overview | FT | https://learn.microsoft.com/en-us/gaming/gdk/_content/gc/system/overviews/directstorage/directstorage-overview | Xbox Series X\|S only (page says so) |
| 4c | DirectStorage 1.1 PC requirements and 5.65 GB sample | UN | (secondary news summaries of the DirectX blog, 2022-11-07) | blog not opened |
| 5a | IoRing `ioringapi.h` | AB | https://learn.microsoft.com/en-us/windows/win32/api/ioringapi/ | min build 22000 (correction) |
| 5b | Axboe io_uring paper | AB | https://www.kernel.dk/io_uring.pdf | v0.4, 2019-10-15; PDF not opened, URL sometimes 404 |
| 6 | Crotty, Leis, Pavlo, CIDR 2022 | AB | https://www.cidrdb.org/cidr2022/papers/p13-crotty.pdf | abstract via search |
| 7a | zstd README benchmark | FT | https://github.com/facebook/zstd | i7-9700K 4.9 GHz, Silesia, lzbench; vendor-stated |
| 7b | Oodle Kraken/Mermaid/Selkie | AB | https://www.radgametools.com/oodlecompressors.htm | vendor-stated, no test conditions |
| 8 | RFC 9113, 9114, 9221, 9147, 9001, 9002 | AB | https://www.rfc-editor.org/rfc/rfc9113.html (and 9114, 9221, 9147, 9001, 9002) | titles, authors, dates, abstracts confirmed |
| 9a | Ford, Overwatch GDC 2017 | AB | https://www.gdcvault.com/play/1024001/-Overwatch-Gameplay-Architecture-and | determinism claim contested |
| 9b | Aldridge, "I Shot You First", GDC 2011 | AB | https://gdcvault.com/play/1014346/I-Shot-You-First-Networking | |
| 10a | Boulanger et al., NetGames 2006 | AB | https://dl.acm.org/doi/10.1145/1230040.1230069 | |
| 10b | Bharambe et al., Colyseus NSDI 2006 | AB | https://www.usenix.org/legacy/event/nsdi06/tech/full_papers/bharambe/bharambe.pdf | |
| 11a | Jolt determinism docs | FT | https://jrouwe.github.io/JoltPhysics/ | ~8% cost vendor-stated |
| 11b | Rapier determinism guide | FT | https://rapier.rs/docs/user_guides/rust/determinism/ | correction on libm |
| 12a | netcode, yojimbo | AB | https://github.com/mas-bandwidth/netcode , https://github.com/mas-bandwidth/yojimbo | READMEs |
| 12b | Unreal Replay System | AB | https://dev.epicgames.com/documentation/en-us/unreal-engine/using-the-replay-system-in-unreal-engine | UE 5.8 docs |
| 12c | Unreal dedicated servers | AB | https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-dedicated-servers-in-unreal-engine | `-nullrhi` not mentioned: UN |
| 12d | Godot `--headless` | FT | https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html | |
| 13 | OpenTelemetry spec | AB | https://opentelemetry.io/docs/specs/otel/ | v1.62.0 |

Caveats: bibliographic data for ACM/dblp/Semantic Scholar entries came through search-result summaries, not the publisher pages. No measurement in this file was reproduced; all numbers are quoted as stated by their source and carry the stated hardware where given.
