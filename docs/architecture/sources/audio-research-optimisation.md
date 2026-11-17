# Game audio optimisation landscape — research for Heliogrim audio engine

Date: 2026-11-03. Scope: architecture headroom for an MMO-scale engine (thousands of requested voices, most culled/virtualised), Windows/WASAPI first, own DSP/mixer/spatialisation.

## Source status legend

- **FETCHED**: primary doc/paper text was read (directly, or extracted from the PDF).
- **SNIPPET**: the primary page blocked automated fetching (Audiokinetic returns 403; FMOD doc pages render empty; INRIA returns 403). The claim comes from search-engine excerpts of that official page. Treat it as **UNVERIFIED** until someone reads it in a browser.
- **UNVERIFIED**: my own knowledge or derivation, not backed by a fetched source.

Measurements from other engines are **non-transferable**: they use different codec implementations, hardware and mixers. Use them only for ordering and orders of magnitude.

---

## 1. Soundbanks and packaging

### What the engines do

- **Unreal Audio Stream Caching** (UE4.25+/UE5 docs, FETCHED)
  - At cook time, compressed audio is stripped from `USoundWave` and placed at the end of the `.pak`.
  - Audio is split into chunks of at most **256 KB**. A global LRU cache holds them under a hard cap, `Max Cache Size`. The cap excludes headers and "retained" sounds.
  - Epic's guidance: 32 MB (128 chunks) is "normal" for 32 voices. Each playing sound pins its next chunk, which can evict primed sounds.
  - `MinimumCacheUsage` trades chunk count against small-asset efficiency. Unadjusted, many 64 KB sounds use only 8 MB of a 32 MB cache.
  - Per-asset/per-class loading behaviour: `RetainOnLoad` (first chunk pinned), `PrimeOnLoad` (first chunk loaded, evictable), `LoadOnDemand`, `ForceInline`.
  - There is an explicit `PrimeSoundForPlayback` API.
  - "Blowing the cache" happens when every slot is playing or loading. The documented remedies are a bigger cache, fewer retained sounds, a lower voice limit, or dropping requests.
  - Reads go through async I/O at BelowNormal priority, the same as geometry streaming.
  - Epic's stated philosophy: latency problems are easier to handle than memory problems, especially in open worlds. A loaded asset no longer guarantees it can play immediately.
- **Wwise SoundBanks + streaming** (SNIPPET/UNVERIFIED: official 2015.1 user guide via mirror, Audiokinetic blog)
  - Banks hold structure/metadata plus in-memory media. Streamed media are separate files.
  - "Zero Latency" stores the first *Prefetch length* ms of a streamed file in the bank, so playback starts immediately while the rest is fetched.
  - Audiokinetic's guidance: short, image-synced one-shots (gunshots, impacts, footsteps) should **not** stream.
  - A 2015 community issue shows the failure mode: auto-defined banks excluded media, so the prefetch was empty and caused starvation.
  - Prefetch too short gives starvation; too long wastes memory.
- **FMOD Studio banks** (SNIPPET from FMOD 2.00 Studio API Guide and low-level overview)
  - Bank metadata loads separately from sample data.
  - Sample data loading options:
    - automatic on event instance (lowest memory);
    - `EventDescription::loadSampleData` for frequently played events (avoids reload churn);
    - `Bank::loadSampleData` (highest memory).
  - Loads are reference-counted at both bank and event level. Data unloads only when both counts reach zero.
  - Advanced settings include a byte budget of sample data to *retain after unuse*, to avoid repeated I/O, and a flag to decompress on load.
- **Unity AudioClip load types** (Unity 6 manual, FETCHED)
  - **Decompress On Load**: no runtime decode cost, but Vorbis uses "about ten times" more memory and ADPCM "about 3.5 times".
  - **Compressed In Memory**: decoded on the mixer thread; "slight" overhead, especially for Vorbis.
  - **Streaming**: decoded on a separate streaming thread, with "approximately 200KB" overhead per streaming clip even with no data loaded.
  - Also offers Preload / Load-in-Background with an explicit `LoadAudioData`/`UnloadAudioData`.

### When it pays off

- Bank splitting by level, zone or feature is how MMOs keep resident memory bounded.
- A chunked LRU cache (Unreal model) decouples "asset referenced" from "audio resident", which matters most for open worlds and MMO zones.
- Prefetch/retained heads cut perceived latency for long streamed sounds. Short, frequent one-shots stay fully resident.

### Architecture requirements (day one)

- **Asset/media split**: sound *definitions* (graph, params, references) are separate from *media* (encoded bytes). Media is addressed by ID plus chunk index, never by pointer from the definition.
- **Chunked media layout with a per-asset header**: codec, sample rate, channels, length, seek table, and a "head chunk" flag.
- A **residency policy enum** per asset, with inheritance from class/category: Retain / Prime / OnDemand / Inline.
- A **budgeted media cache service** with an LRU, pinning for in-flight voices, and look-ahead of the next chunk. It must return "not resident yet" to the voice, so a voice can start late, start silent, or be refused. This needs an explicit voice state.
- An **async I/O request API with priorities**, shared with the engine's asset streaming.
- **Packaging can come later**, provided the runtime reads media through a "container" abstraction (loose file, pak, bank). The initial packaging can be a dumb concatenation.

---

## 2. Codecs and decode cost

| Codec | Ratio | Relative decode cost | Notes / source |
|---|---|---|---|
| PCM | 1:1 | ~0 | Unity, FMOD, UE glossary (FETCHED/SNIPPET) |
| ADPCM | ~3.5:1 (Unity/FMOD), "up to 4:1" (UE) | cheap | Unity: "CPU usage is much lower than MP3/Vorbis" (FETCHED). FMOD's branch-free FADPCM is "many times faster than standard ADPCM" (SNIPPET). |
| Vorbis | ~10:1 typical | **1.5–3x ADPCM**; Q10 costs 2x Q0 | Audiokinetic codec guide / CPU blog (SNIPPET, Wwise's own decoder, ~2017–2021) |
| Opus | best quality per bit | **5–10x ADPCM**; 2018 note: 4–5x Wwise Vorbis | Audiokinetic (SNIPPET). Advice: sounds <200 ms should use Vorbis or ADPCM. Opus needs no seek table, but seeking costs more CPU and I/O. |
| Bink Audio / RAD Audio (UE) | "perceptually lossless 10:1" | "closer to ADPCM than MP3 or Vorbis" | UE docs (SNIPPET of official page). Used in Apex Legends with 80–100 simultaneous voices. |
| HW decoders (XMA, ATRAC9, console Opus/Vorbis HW) | — | offloaded | Audiokinetic: "don't assume those codecs cost nothing" (SNIPPET). Not relevant to Windows-first. |

**Opus specifics** (RFC 6716, RFC 7845; FETCHED)

- Frames are 2.5–60 ms (20 ms recommended), bitrate 6–510 kbit/s.
- CELT always runs internally at 48 kHz.
- Algorithmic delay is 5–65.2 ms.
- After a seek, an implementation **SHOULD decode and discard ≥3840 samples (80 ms) pre-roll** for decoder convergence.
- **Implication:** random-access starts and loop points with Opus cost an extra ~80 ms of decode. That is exactly why Wwise reports the extra seek cost.

**Per-instance decoder memory** (FMOD 1.03-era `FMOD_ADVANCEDSETTINGS`, FETCHED but **old, ~2014**)

| Codec | Bytes per instance |
|---|---|
| Vorbis | 23,256 |
| MPEG | 30,528 |
| CELT | 25,408 |
| XMA | 14,836 |
| AT9 | 8,720 |
| ADPCM | 3,128 |

- FMOD pre-allocates a fixed pool of N codec instances per format at init, which caps both CPU and memory.
- FSB Vorbis shares codebooks across sounds ("saving megabytes" vs individual .ogg files; SNIPPET).

**Seek-table granularity** (UNVERIFIED, general)

- Stream-head prefetch and virtual-voice "seek restart" both need random access.
- ADPCM/PCM are trivially seekable: fixed block size.
- Vorbis and Opus need a seek table: packet index every N ms, plus Opus pre-roll.
- Coarser tables mean less memory and more wasted decode on seek. Pick N relative to the chunk size (e.g. one entry per chunk plus intra-chunk entries).

**When it pays off**

- Per-asset codec choice is the single largest memory and CPU lever.
- ADPCM suits dense short SFX (footsteps, impacts).
- Vorbis suits medium-length assets and music.
- Opus suits long dialogue/music where memory or disk size dominates and seeking is rare.
- PCM suits tiny, ultra-frequent, or heavily pitch-modulated sounds.

**Architecture requirements**

- A **codec plug-in interface** with:
  - `decode(block)` into the engine float format;
  - `seek(sample)` that reports pre-roll needed;
  - declared state size;
  - a "cost class" hint used for voice budgeting.
- **Bounded decoder-state pools per codec**, allocated at init.
- **Decode location must be choosable**: on the mixer thread (Compressed-in-Memory), on worker jobs ahead of the mixer, or at load (Decompress-on-Load). The voice must therefore consume from a small ring of decoded blocks rather than calling the decoder inline.
- **Codec and sample rate are per-platform cook settings**, not source settings.

---

## 3. Pre-processing and baking

### Baked wave acoustics — Microsoft Triton / Project Acoustics (FETCHED)

**Raghuvanshi & Snyder, "Parametric Wave Field Coding for Precomputed Sound Propagation"** (ACM TOG 33(4) / SIGGRAPH 2014; PDF text extracted)

- **What is baked:** wave simulation up to **500 Hz**.
- **How it is encoded:** the 7D IR field is reduced to **4 one-byte perceptual parameters**: direct loudness, early-reflection loudness, early decay time, late reverb time. The result is a 6D, time-invariant field with spatial compression of typically 4–8x.
- **Probe spacing:** listener spacing typically 2–4 m horizontal, 1.6 m vertical.
- **Memory:** whole game maps fit in under 54 MB. In one scene, 56 TB of raw data compressed to 41 MB. Size scales with surface area, not volume.
- **Runtime decode:** about **100 µs per source**, on the game thread. Decompressed slices are held in a 1 MB global cache.
- **Bake compute:** done on a 140-machine cluster, "comparable to light baking".
- **Rendering:**
  - Six fixed **canonical filters** are applied as **bus effects**.
  - Per-source work is reduced from convolution to "six scale-and-sum operations".
  - In game-audio terms: CFs are effects on buses, and per-source scale factors are bus **send values**.
  - The filters run via partitioned FFT convolution in an XAudio2 APO, inside UE3.

**Follow-up: "Parametric Directional Coding"** (Raghuvanshi & Snyder, ACM TOG 37(4), SIGGRAPH 2018; SNIPPET of ACM/MSR abstract)

- Adds arrival direction, still at ~100 MB for large scenes.
- Its "filtering cost is largely insensitive to the number of sound sources".
- A 2020 TOG follow-up (Chaitanya et al., "reciprocal wave field coding") adds directional sources and listeners. Not read.

### Steam Audio (Programmer's Guide, FETCHED; no timing numbers given)

- **Baked reflections:**
  - Probes are placed on the floor, e.g. at 2 m spacing and 1.5 m height.
  - Probes are grouped into **probe batches**, which are the load/unload unit.
  - Bake variations: static source, static listener, dynamic.
  - Bake parameters are far higher than real-time settings (e.g. 32768 rays and 64 bounces baked, vs 4096 rays real-time).
- **Baked pathing:** produces an Ambisonic sound field rendered by a path effect.
- **Listener-centric reverb:** a source placed at the listener gives reverb whose cost is "independent of the number of sources".
- **Real-time reflections** carry "a significant CPU usage cost". Simulation runs on separate threads, and outputs are fetched on the game/update thread.
- **Ray backends:** built-in, Embree, Radeon Rays (GPU, contends with graphics), or custom callbacks.

### Real-time geometric propagation with clustering (FETCHED)

**Schissler & Manocha, "Interactive Sound Propagation and Rendering for Large Multi-Source Scenes"** (ACM TOG, 2016; 4-core PC)

- **Clustering:** occlusion-aware source clustering gave 200 sources → 95 clusters (2.1x reduction), and 52 clusters when clustering at the listener (3.8x). Clustering took 0.2 ms.
- **Hybrid rendering:**
  - Only paths with a Doppler shift above **20 cents** (a psychoacoustic threshold) get interpolated delay lines.
  - All other paths go into non-uniformly partitioned convolution.
  - The threshold scales with CPU load.
- **SIMD layout:** 4 log-spaced frequency bands, chosen to fit 4-wide SIMD.
- **Diffuse cache:** reuses energy across frames with a 2 s time constant.

### Loudness normalisation (FETCHED)

- EBU R 128 targets **−23 LUFS** programme loudness, measured per ITU-R BS.1770.
- Gating: the relative gate was changed to −10 LU in v2.0.
- Tolerance: ±0.5 LU since v3.0.
- Revisions: v4.0 (2020) and v5.0 (2023).
- The true-peak limit and current tolerance are in the PDF, not read.
- Console-specific targets (e.g. Sony ASWG) are **UNVERIFIED**, not fetched.
- **For games:** measure integrated loudness and true peak offline at import and store them as asset metadata. Apply a normalisation gain at runtime. This costs nothing at runtime and makes mix buses predictable.

### Pre-rendered variants

UNVERIFIED as a practice: no primary measurement found. Commonly done for expensive offline chains, e.g. baking variations of a granular or procedural patch to N wav files. It trades memory for zero synthesis CPU.

### Architecture requirements

- An **offline asset pipeline stage** ("audio cook") with metadata output: loudness, peak, seek table, codec, variant set.
- **Spatial acoustic data as a streamable, zone-partitioned asset**: probe batches tied to world partition cells, each loaded and unloaded as a whole batch.
- A **query API returning a small parameter vector per source–listener pair**: occlusion, wet/dry, decay, direction. This feeds the voice's send levels and filters.
- **Sends to shared reverb/"canonical filter" buses are a first-class mixer concept.** This is the key hook, because it makes reverb cost per-bus, not per-source.

---

## 4. Dynamic pipelines and derivatives (DSP graph "permutations")

### Unreal MetaSounds (UE docs, FETCHED)

- **Compilation:** each graph is converted to an "optimized static, non-virtual C++ object". Nodes pass data by reference. There is no interpreted bytecode.
- **Rendering:** instances render asynchronously and in parallel ("each MetaSound is its own audio rendering engine"), using the same task architecture as async decoding.
- **Timing:** triggers are sample-accurate. Control and block rate is set by `au.MetaSound.BlockRate`, default 100 blocks/s according to a third-party source (**UNVERIFIED**).
- **Presets:** derivative graphs that reference a base graph and override inputs. Base edits propagate to every preset.
- **MetaSound Pages** (Experimental):
  - Per-platform or quality **graph variants or input-default variants**.
  - Can be excluded from cook per platform, with ordered fallback.
  - Selected before an instance starts, never swapped live.
- **Operator pool / cache:** `FOperatorPool` holds pre-built, reusable graph operator instances. `PrecacheMetaSound(source, N)` builds N operators asynchronously. Purpose: avoid build cost at play time.

### Faust (official compiler docs, FETCHED)

- **Modes:**
  - Scalar mode is one sample loop.
  - `-vec` splits computation into simpler loops over vectors (default vector size 32) to aid auto-vectorisation.
  - `-omp` and `-sch` (work-stealing scheduler) parallelise vector loops.
- **Measured:** an RMS example went from 129 to 360 MB/s (x2.8) in vector mode.
- **Benchmark tooling:** `faustbench` / `faustbench-llvm` search option space per DSP.
  - Letz's published sweep shows the best vector size varies per program: e.g. peak at `-vs 128`–`512`, falling at 1024.
  - The scheduler "performs worse for simple programs".
- libfaust offers in-process LLVM JIT (docs mention only an embedded compiler; JIT details not read).

### Procedural and parameter-driven variation

- Farnell, *Designing Sound* (MIT Press, 2010) is the standard reference. Book not read; **UNVERIFIED** detail.
- Fournel (GDC 2010/2011 slides; PDF text not extractable; SNIPPET): procedural audio has "CPU cost higher and/or non linear" than sample playback. The main use is fighting repetition (footsteps, impacts).
- Raghuvanshi & Lin, "Symphony" (I3D 2006, SNIPPET): priority-based quality scaling of modal synthesis gave "up to an order of magnitude" speed-up. Hundreds of sounding objects used 10% CPU, on 2006 hardware (old; ordering only).
- Cheap variation (pitch, volume, filter randomisation, random container selection) costs essentially nothing beyond SRC. UNVERIFIED as a measurement, but structurally obvious: a gain plus a resampler ratio.

### Caching rendered variants vs live synthesis (UNVERIFIED; trade-off reasoning)

- Live synthesis gives unbounded variation at CPU cost, and its cost can be shed via LOD.
- Cached renders cost memory. They are fine for short, frequent sounds whose control inputs are quantisable.

### Block size and vectorisation (FETCHED: Supernova thesis, Schissler)

- Blechmann notes "typical block sizes are 64–2048". Vectorisable nodes are more efficient at block sizes that are multiples of the SIMD width.
- Schissler chose 4 frequency bands *because* of 4-wide SIMD.
- Steam Audio auto-selects SSE/AVX and warns that AVX-512 can trigger frequency throttling.

### Architecture requirements

- A **graph description → compiled instance split**:
  - An immutable "graph asset" compiled once into a flat, topologically ordered node array with pre-sized buffers.
  - Per-voice instances that are just state blocks.
  - This is the "shader vs material instance" analogue.
- A **derivative model**:
  - Preset = base graph + parameter overrides.
  - Variant/page = alternate graph per quality tier, chosen at instance creation.
  - Cache compiled graphs by (graph hash, variant key).
- An **instance pool with async prewarm**, like the MetaSound operator pool, so voice start never allocates or compiles on the audio thread.
- A **fixed internal block size** (power of two, multiple of the SIMD width) with a **separate control rate**. Parameter changes are **sample-timestamped events** within a block.
- **Deinterleaved (planar) float buffers** throughout, aligned to 32/64 bytes.

---

## 5. Voice-level optimisation

### Virtual voices (FETCHED Unreal API; SNIPPET Wwise; FMOD UNVERIFIED)

- **Unreal `EVirtualizationMode`** (applies when a sound is stopped by concurrency, priority or channel limits):
  - **PlayWhenSilent**: keeps a voice and keeps playing.
  - **Restart**: a looping sound restarts on realisation.
  - **SeekRestart** (experimental): fully virtual, with playback time tracked so it seeks to the right position on realisation.
- **Wwise:** virtual voice behaviours are continue-to-play, kill, send-to-virtual, and play-from-beginning / play-from-elapsed-time. Also a "below threshold" volume (SNIPPET).
- **FMOD** separates total (virtual) channel count from real software channels, and has a vol-0-becomes-virtual flag (UNVERIFIED, doc pages not readable).

### Perceptual culling and clustering (FETCHED abstracts / derived papers)

**Tsingos, Gallo, Drettakis, "Perceptual audio rendering of complex virtual environments"** (SIGGRAPH 2004)

- Pipeline:
  1. Estimate per-source loudness.
  2. Remove inaudible (masked) sources ("auditory culling").
  3. Cluster the remainder into a **fixed budget of clusters**, each represented by an **impostor source**.
  4. Spatialise only the impostors.
- Result: >10x the source count of contemporary consumer 3D hardware with minimal quality loss. A pilot study found quality and localisation impairment limited and largely insensitive to cluster budget.
- Full paper not fetched (INRIA 403).

**Moeck et al., "Progressive perceptual audio rendering of complex scenes"** (I3D 2007; SNIPPET of paper text)

- 1815 moving sources rendered in real time using **15% of the frequency coefficients** (progressive frequency-domain premix) and **~12 clusters on average**.
- Requires pre-computed per-asset spectral and loudness descriptors.

**Schissler & Manocha 2016** (FETCHED; see section 3)

- Adds occlusion-aware clustering: sources in different rooms are never merged.
- Clustering is cheap (0.2 ms for 200 sources).

### HRTF cost reduction

- **Per-source binaural** (Steam Audio, FETCHED): one binaural effect per source. Nearest-neighbour HRTF lookup is cheapest but can produce audible switching; bilinear (4-direction) interpolation is smoother.
- **Ambisonics as an intermediate bus** (Steam Audio FETCHED: order N uses (N+1)² channels; rotation via listener orientation; binaural or speaker decode).
  - Sources are encoded into an SH bus at the cost of (N+1)² gains each.
  - **One** binaural decode per listener (2·(N+1)² convolutions) then makes HRTF cost independent of source count.
  - Derivation is UNVERIFIED as a measurement, but follows from the structure. Resonance Audio markets this for "spatial audio at scale" without numbers (FETCHED).
- **Low-order quality fixes:** Zaunschirm, Schörkhuber & Höldrich (JASA 143(6), 2018) and MagLS (DAGA 2018) improve low-order binaural decoding through HRIR time alignment, allowing lower SH orders. Abstract-level only.
- **Partitioned convolution:**
  - Wefers, *Partitioned convolution algorithms for real-time auralization* (RWTH dissertation 2014, published 2015) covers uniformly and non-uniformly partitioned convolution, filter networks and time-varying filters. PDF text not obtained.
  - Triton (FETCHED) uses partitioned FFT convolution and notes that "increasing the partition size reduces per-sample cost but increases latency".
  - Schissler uses non-uniform partitioning, with later partitions updated at slower rates.

### Level of detail for audio (synthesis of the above)

- The ladder: full graph → simplified page/variant → cheaper codec path → clustered impostor / panned mono → virtual (time-tracked) → culled.
- Driven by a per-frame audibility score: gain × attenuation × occlusion × priority, compared against a masking estimate.

### Architecture requirements

- **Voice ≠ playing instance:**
  - A *sound instance* (logical, cheap, thousands) has position, params, priority and play time.
  - A *voice* (physical, budgeted) owns a decoder and graph state.
  - The virtualiser maps instances to voices each update.
- **Per-instance playback clock** that advances while virtual, for SeekRestart, plus the codec seek API.
- An **audibility estimator** with a cheap per-instance loudness proxy from offline metadata (per-asset loudness from section 3, optionally a band envelope). This is what makes masking and culling possible later.
- **Spatialisation is a stage behind an interface**, so per-source binaural, panning, cluster-impostor and Ambisonic-bus encoders are interchangeable.
- **Bus graph supports multichannel buses** of arbitrary channel count, so SH buses work.
- **Concurrency groups / limits** per category, with steal policies.

---

## 6. Threading and latency

### Latency budgets at 48 kHz (arithmetic)

| Block size | Latency |
|---|---|
| 64 | 1.33 ms |
| 128 | 2.67 ms |
| 256 | 5.33 ms |
| 480 | 10 ms |
| 512 | 10.67 ms |
| 1024 | 21.3 ms |

### Windows (Microsoft Learn "Low Latency Audio", updated 2025, FETCHED)

- Default shared-mode WASAPI buffer is ~10 ms.
- `IAudioClient3::GetSharedModeEnginePeriod` and `InitializeSharedAudioStream` allow smaller periods: any multiple of the fundamental period within [min, max].
- The inbox HDAudio driver supports 128–480 samples (2.66–10 ms at 48 kHz).
- The Win10+ engine adds ~1.3 ms render latency.
- One app requesting small buffers switches every client on that endpoint and mode.
- Microsoft recommends the Real-Time Work Queue API (tag MMCSS "Audio"/"Pro Audio") for audio work items instead of your own threads.
- Lower latency costs power: wake-ups go from every 10 ms to every 1 ms.
- `AUDCLNT_STREAMOPTIONS_MATCH_FORMAT` avoids engine resampling; raw mode bypasses OEM processing.
- **For a game, 10 ms (480 frames) default with an optional ~5 ms is a reasonable target** (UNVERIFIED as a recommendation).

### Parallel DSP graph execution

**Wwise 2022.1 job manager** (SNIPPET of Audiokinetic blog)

- The engine calls a host-provided `fnRequestJobWorker` callback, up to `uMaxActiveWorkers`.
- Workers drain many jobs internally. In one example, 23 jobs ran with only 4 worker requests.
- The voice phase parallelises widely. The bus phase was "too narrow" for 3 workers.
- **Lesson:** per-voice work parallelises well, and the bus tree is the serial bottleneck.

**Blechmann, Supernova** (TU Wien MSc thesis 2011; LAC 2010; ICMC 2011; FETCHED thesis text)

- **Measurement setup:** Core i7 920, real-time Linux. Deadline is 1.3 ms for 64 samples at 48 kHz. Worst-case latency was measured with histograms, not throughput.
- **Parallel groups:**
  - Near-linear speedup when dispatch overhead is low.
  - Many tiny nodes are dominated by dispatch and queue contention.
  - Sequential parallel groups cost O(n²) activation; a barrier node fixes it.
  - Idle threads busy-wait when the graph is too narrow (3 threads ≈ 2 threads for 4 heavy synths).
  - Worst case was ≈20 µs above average.
- **Real-time rules:**
  - Lock-free queues and stacks.
  - Memory pools with lock-free free-lists for deferred frees.
  - No blocking allocation on DSP threads.
- **Prior art:** Letz et al. (2010) proposed a work-stealing scheduler for this (Faust `-sch`).

**Schissler & Manocha** (FETCHED)

- Two audio-rendering threads, each with a small pool.
- Propagation threads merge results asynchronously into the renderer.

**Steam Audio** (FETCHED): blocking simulation calls go on their own thread, with results fetched on the update thread.

### Architecture requirements

- **Three-tier split:**
  1. **Game/update thread**: instance logic, virtualisation, 3D params, ~30–60 Hz.
  2. **Audio render callback**: hard real-time. No locks, allocation or I/O.
  3. **Workers**: decode-ahead, streaming I/O completion, graph compile, propagation queries, parallel voice jobs.
- **Lock-free SPSC/MPSC command queues** carry timestamped commands from game to audio. Return queues carry finished-voice notifications and deferred frees.
- **Render graph scheduled as a DAG of jobs per block:**
  - Wide voice phase, then a bus phase in topological levels.
  - Must run single-threaded first, but be expressed so a job system can take it later.
  - Coarse granularity (per voice or voice batch, not per node) avoids Supernova-style dispatch overhead.
- **Device-period-independent internal block:** the mixer renders N internal blocks per device callback, or uses a FIFO, so WASAPI period changes don't change DSP behaviour.
- **Per-block worst-case timing instrumentation** (histograms), since the deadline is what matters.

---

## Summary: day-one hooks vs later additions

**Must exist from day one** (retrofitting is expensive):

1. Definition/media split; chunked media with headers and seek tables; residency policy enum.
2. Async media cache service with budget and pinning, and a voice state for "media not ready".
3. Codec plug-in interface (decode, seek with pre-roll, state size, cost hint) plus bounded per-codec state pools.
4. Decoded-block ring between decoder and voice, so decode can move between mixer, worker and load time.
5. Sound instance vs physical voice separation, with a virtual playback clock and an audibility score.
6. Offline cook step that emits metadata (loudness, peak, seek table, codec, per-platform settings).
7. Bus graph with arbitrary channel counts and per-source **sends** to shared buses (needed for Triton-style canonical filters, shared reverb, and the Ambisonic bus).
8. Spatialiser interface (stage abstraction).
9. Compiled-graph vs instance-state split; preset/variant keys; instance pool with prewarm; fixed planar SIMD-friendly block size; sample-timestamped parameter events.
10. Lock-free game→audio command queue; deferred-free return queue; no alloc/lock on the render thread.
11. Render work expressed as a DAG of coarse jobs (voice phase, then bus levels), even if executed serially at first.
12. Worst-case block timing instrumentation.

**Can be added later** if the hooks exist:

- Real bank packaging and splitting tools.
- Prefetch-length tuning.
- Additional codecs (Opus, ADPCM variants).
- Decompress-on-load policy.
- Perceptual masking and clustering (Tsingos/Moeck/Schissler).
- Ambisonic binaural decoder (including MagLS-style quality fixes).
- Partitioned convolution reverb.
- Baked acoustics (probe batches tied to world partition).
- Real-time propagation.
- Graph quality pages.
- JIT/Faust-style graph compilation.
- Procedural synthesis LOD.
- Multi-threaded graph execution.
- Low-latency WASAPI (IAudioClient3) mode.
- Loudness-normalised mixing presets.

## Gaps and open verification items

- Audiokinetic pages (codec guide, CPU guidelines, 2022.1 job manager, voice optimisation) were not fetchable (403). Their numbers come from search excerpts only.
- FMOD docs (virtual voices, memory management, banks) were not readable by the fetch tool. Statements are from 2.00 guide excerpts and an old 1.03 mirror.
- Tsingos 2004 and Moeck 2007 full texts were not read (INRIA 403). Only abstracts and teaser numbers.
- Wefers thesis full text was not read, so no partitioned-convolution cost numbers are included.
- No first-party measurement of Ambisonic-vs-per-source binaural cost; the scaling statement is derived.
- No measured study comparing procedural vs sampled playback CPU in a modern game engine was found.
- All codec cost ratios are engine-specific (Wwise decoders) and pre-2022. Benchmark our own decoders.
