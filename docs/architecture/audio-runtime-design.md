# Audio Runtime (Design)

**Status**: design draft, not approved. Agreed in the design conversation of 2026-11-03 (log: [audio-dsp.md, section 10](audio-dsp.md#10-brainstorm-progress-2026-11-03)).

Markers: **Decided** = agreed by the owner. **Builder's call** = left to the implementer. **Proposal** = suggested in this document, not yet confirmed. *Vision* = engine direction that does not exist in code today.

## 1. Intent

Heliogrim has no sound playback. `Engine.SFX` only registers WAV, FLAC and Vorbis importers. The owner has built DSP, mixers, a Butterworth band compressor/EQ and trigonometric spatial attenuation before; that code is lost. This design rebuilds an engine-owned audio runtime: our own DSP, mixers, voices and spatialization, with a native output backend.

The first audible goal is a spatial scene sound: an emitter in the scene that pans and fades as the listener moves. The runtime must also make DSP chains and mixer banks easy to rearrange, because exploring spatial sound, environments and DSP pipelines is a goal in itself.

This is project 1 of 3. Project 2 is the designed integration with game events and controls. Project 3 is the editor composition UI, after the MSDF/reflow UI rework (*vision*).

## 2. Goals

1. **Decided.** Our own DSP graph, mixers, voices and spatialization. No middleware. FMOD, Wwise, Steam Audio, miniaudio and SoLoud are references ([research](sources/audio-research-middleware.md), [libraries](sources/audio-research-tools-libs.md)).
2. **Decided.** Native output through Windows Core Audio (WASAPI). SDL3 is not used for audio.
3. **Decided.** Sample rate follows the device: 44.1, 48 and 96 kHz must work.
4. **Decided.** Every connection between DSP nodes carries its signal domain (time domain or frequency domain). Nodes declare whether they commute, so the graph compiler can reorder chains to reduce FFT/IFFT conversions. Domain handling is proven in the first scope.
5. **Decided.** Graphs execute as recorded command buffers from pools. Buffers are recorded once per graph change and replayed every block, with caching and reuse of recorded (sub-)buffers.
6. **Decided.** Mixer banks nest: group sub-mixes feed further banks up to a master.
7. **Decided.** The first DSP scope covers every category once: multiband compressor, EQ, low-pass and high-pass, clipper and limiter, spatializer, attenuators, synthesizer (sine), plus one frequency-domain node (section 8).
8. **Decided.** An audio scene system maps pushed components to internal models, like physics.
9. Hooks for later work are in place from the start (section 11), so banks, streaming, codecs, clustering, HRTF and baked acoustics do not need a redesign ([optimisation research](sources/audio-research-optimisation.md)).

## 3. Non-goals

- Game event and control integration beyond a minimal play/stop/set-parameter API (project 2).
- Editor composition UI (project 3).
- Observability and metrics. **Decided**: its own engine-wide topic, brainstormed separately. The existing `Profiler`/`Stopwatch` will be dropped. This design only leaves a hook (section 10).
- Streaming from disk, sound banks, Opus (no importer or vendor library exists today), HRTF, Ambisonics, reverb, occlusion, music, Windows Sonic / 7.1.4 objects, macOS Core Audio.
- Middleware bank formats (licence, see [audio-dsp.md section 8](audio-dsp.md#8-decisions-needed-and-claims-to-verify)).

## 4. Anti-goals

- Locks, allocation, blocking I/O or fiber yields on the device thread. An audible dropout is a failure even if the output is otherwise correct.
- Locks taken by the audio thread to connect or disconnect nodes (miniaudio does this) or one global mix lock (SoLoud does this).
- Building on today's scheduler internals or today's render command path. Both are naive placeholders that will be replaced (*vision*). The audio runtime takes ideas from them, not their structure.
- Ranking voices by their set volume instead of their audible level.

## 5. Constraints

- C++26, engine conventions: bundles under `src/`, static/object libraries per bundle, tests in `<Bundle>.Test` with GoogleTest.
- Threading: there is no game thread. Engine work runs as cooperative fiber tasks (`Engine.Scheduler`, worker groups Critical / IO / All). The scheduler will be replaced by one with task-graph dependencies, possibly EEVDF-like (*vision*). Audio may only assume "tasks can be submitted and may depend on each other".
- Scenes list their systems at compile time: `GameScene : Scene<PhysicsSceneSystem, RenderSceneSystem>` (`Engine.Scene.Game/GameScene.hpp`).
- Importers and loader chains will be reworked with the new storage system (*vision*). Audio uses the existing importers through a narrow media interface so the rework does not reach into the runtime.
- No shared BVH or spatial query service exists (*vision*). Milestone 1 does not need one.

## 6. Architecture Overview

```
fiber tasks (scene update, gameplay, compile, decode)
    |  lock-free command queue (positions, params, play/stop, graph swaps)
    v
device thread (real-time, outside the fiber scheduler)
    per block: drain commands -> control step -> replay command buffers -> write device
    |  lock-free return queue (finished instances, retired graphs/buffers, readbacks)
    v
fiber tasks (free memory, publish readbacks)
```

- **Decided** (proposed, not objected): the device thread is a dedicated real-time thread outside the fiber scheduler. Fiber tasks talk to it only through the two queues.
- **Proposal**: one multi-producer queue into the device thread, since commands come from any fiber worker. **Builder's call**: queue implementation (bounded MPSC ring or per-worker SPSC rings merged on drain), as long as pushing never blocks and a full queue is reported, not waited on.
- The device thread never frees memory. Anything it retires goes to the return queue.

## 7. Signal Model

### 7.1 Blocks

- Signals are planar `float32` buffers of a fixed internal block size, independent of the WASAPI period.
- **Proposal**: block size chosen for about 5 ms (256 frames at 48 kHz, 512 at 96 kHz), configurable. **Builder's call**: alignment for SIMD.
- The internal sample rate equals the device's mix rate, to avoid WASAPI shared-mode resampling (which also disables low-latency mode).

### 7.2 Domains

Every node port declares a domain:

| Domain | Payload | Parameters |
|---|---|---|
| `Time` | planar samples per channel | channel count |
| `Spectral` | complex bins per channel per frame | frame size N, hop H, window |

- **Decided**: domain is part of the port type. A connection between ports of different domains is legal in the graph description; the compiler inserts the conversion node (STFT analysis or overlap-add synthesis).
- Spectral frames do not align with blocks. The analysis node buffers input across blocks and emits zero or more frames per block; the synthesis node does overlap-add and emits exactly one block. **Builder's call**: N and H defaults (proposal: N = 1024, H = N/4, sqrt-Hann analysis and synthesis windows).
- Every node reports its latency in samples. A conversion pair adds N - H samples. **Proposal**: when parallel paths inside one bank have different latencies, the compiler inserts delay compensation, as DAWs do. Across banks, compensation is a builder's call for the first scope.

### 7.3 Commutativity and reordering

- **Decided**: nodes declare whether they commute with neighbours. **Proposal** for the rule: a node is reorderable if it is linear and time-invariant (gain, EQ, low/high-pass, FFT EQ, spatializer gain stage). Nonlinear nodes (compressor, clipper, limiter) are barriers.
- The compiler reorders only within a run of reorderable nodes between barriers, and only to group same-domain nodes so fewer conversions are needed. It never moves a node across a barrier, a send, or a mix point.
- **Proposal**: parameter changes inside a block make "time-invariant" approximate. Smoothed parameter changes are treated as commuting; the error is limited to the smoothing window. Flag this in tests (section 12) rather than forbid it.
- The compiler must be able to report the original and the reordered chain, so the editor (project 3) and tests can show what changed.

## 8. DSP Node Set (first scope)

Each node: one header/source pair, parameters described by name, type, range and default (so the editor and game parameters can bind to them later), per-instance state separate from the node definition.

| Node | Category | Behaviour | Domain | Reorderable |
|---|---|---|---|---|
| Sine oscillator | synthesizer | phase accumulator (double phase), frequency, amplitude | Time | n/a (source) |
| Gain | utility | linear gain with smoothing | Time | yes |
| Low-pass / high-pass | filter | Butterworth, 2nd order biquad, cascade for higher order; TDF-II, float state | Time | yes |
| Parametric EQ | EQ | bands: low shelf, peak, high shelf, notch (biquad cascade) | Time | yes |
| FFT EQ | EQ (frequency domain) | per-bin gain from a curve; proves domain handling | Spectral | yes |
| Multiband compressor | dynamics | 3 bands via Linkwitz-Riley 4th-order crossovers (cascaded Butterworth), per-band feed-forward compressor (threshold, ratio, attack, release, soft knee), sum | Time | no (barrier) |
| Clipper | dynamics | soft (cubic or tanh) and hard modes | Time | no |
| Limiter | dynamics | look-ahead, true-peak detection on 4x oversampled signal, ceiling default -1 dBTP | Time | no |
| Attenuator | spatial | distance curves: inverse, linear, exponential, custom spline (LUT); inner/outer radius as in [bounding volumes](bounding-volumes.md#3-falloff-thresholds-and-curves) | Time | yes |
| Spatializer | spatial | listener-relative azimuth/elevation, constant-power pan (sin/cos) to stereo; behind an interface that later takes VBAP, HRTF, Ambisonic encoders | Time | gain stage yes |

- **Decided**: denormals are flushed (FTZ/DAZ on x86, FPCR.FZ on ARM64), set when the device thread starts.
- **Builder's call**: oversampling for the clipper (aliasing) and the filter design for the limiter's 4x oversampler.
- Extending the set (delay, reverb, ducking, convolution) is later work; the categories are covered once.

## 9. Graph Description, Compilation and Command Buffers

### 9.1 Graph description

- **Proposal**: the graph is plain data: mixer banks, each with input buses, node chains, sends and one output bus; banks connect to other banks up to the master. Voice chains are templates referenced by sound definitions.
- In milestone 1 graphs are built in code. The data form must be serializable later, because the editor (project 3) creates and edits it.

### 9.2 Compilation

- A compile step, run as a fiber task, turns one bank's description into: the reordered node list, inserted conversions and delay compensation, buffer assignments (reusing buffers whose lifetimes do not overlap), and a recorded command buffer.
- **Decided**: record once per graph change, replay every block. A bank that did not change keeps its recorded buffer.
- **Proposal** for reuse ("derivatives"): a voice chain template compiles once into a buffer that addresses its state through a per-voice base offset. Every voice of that template replays the same buffer with its own state block. Variants (different parameters, same structure) share the buffer; only structural changes create a new one.
- Swapping in a recompiled bank: the compiled result is published through the command queue and swapped at a block boundary. The old buffer goes back through the return queue. **Builder's call**: whether to crossfade on swap.

### 9.3 Command buffers

- Commands are small structs (process node with state X on buffers A to B, mix-add, convert domain, send with gain, copy, clear) stored contiguously in an arena from a pool. Execution is a linear walk; no virtual call per sample, one dispatch per command per block.
- Taken from the graphics path as ideas: a recording API separate from execution, arena-allocated commands released all at once, pooled buffers, keeping referenced resources alive with the buffer. Not taken: the linked-list storage and per-frame re-recording.
- Per block, execution reads a parameter table (slot per node parameter) and sample-timestamped parameter events from the command queue. Recorded buffers never contain parameter values that change at runtime.
- Execution order: voice buffers, then bank buffers in dependency order to the master. **Proposal**: expressed as a graph of coarse jobs (voice phase, then bank levels) even though milestone 1 runs it single-threaded on the device thread.

## 10. Voices, Scene and Device

### 10.1 Sound instances and voices

- `play` returns a handle to a **sound instance**: cheap, no audio-thread allocation, thousands allowed.
- Each control step scores instances by audibility (gain x distance attenuation x priority weight) and gives the top N a **real voice** (budget configurable). The rest are **virtual**: their playback clock advances, nothing is rendered. Promotion starts at the virtual clock position with a short fade-in.
- **Builder's call**: the exact score and the per-sound "when inaudible" policy (pause, stop, keep running virtual), with keep-running-virtual as the default.

### 10.2 Scene integration

- **Proposal**: `AudioSceneSystem` becomes the third system in `GameScene`, built on `SceneSystemTypeMappedRegistry` like `PhysicsSceneSystem`. Components: an emitter (sound reference, attenuation and spatializer settings) and a listener. Models push transform and parameter changes into the command queue on update.
- **Proposal**: one active listener in milestone 1. Multi-listener (split-screen) is a known weak spot in FMOD and Wwise and stays an open question.

### 10.3 Device backend

- An interface with: enumerate devices, open with requested format (rate, channels, layout), start, stop, report the actual mix format, and device-lost/default-changed events.
- **Decided**: WASAPI shared mode first, event-driven. A null device renders offline into memory at any rate, for tests and offline bounces.
- **Proposal**: the WASAPI backend lives in a platform support bundle (`Support.<Name>.Windows` per the project convention). **Builder's call**: bundle names and the split of `Engine.SFX` into runtime and DSP bundles.
- Following the user's default-device change and exclusive mode are later work.

### 10.4 Media

- Milestone 1 decodes a whole asset to float at load through the existing importers (WAV via dr_libs, FLAC, Vorbis), on a fiber task, never on the device thread.
- Hook: voices read media through an interface addressed by media id and chunk index, with a residency setting of which only "resident" is implemented. Voices have an explicit "media not ready" state.

### 10.5 Observability hook

- The device thread records per-block execution time into a fixed-size buffer readable through the return queue. Nothing else until the observability design exists.

## 11. Hooks for Later Work

Kept in the data model now so later work does not need a redesign: definition vs media split with chunk addressing and residency; codec interface; sound instance vs voice; per-source sends to shared buses (shared reverb, Ambisonic bus, baked acoustics); spatializer interface; coarse job graph; any channel count per bus; cook-time metadata slot (loudness, peak, seek table).

## 12. Testing

- Everything below runs on the null device, offline, in a `.Test` bundle.
- Per node: a sine through low-pass/high-pass is attenuated by the expected amount at test frequencies; EQ band gains at centre frequency; FFT EQ matches the equivalent time-domain gain within tolerance; compressor gain reduction matches its ratio above threshold; limiter output never exceeds the ceiling on 4x oversampled peaks; denormal test with a decaying tail stays fast (no denormal stall).
- Compiler: given chains with mixed domains, the reordered chain has the expected (minimal) number of conversions, never crosses a barrier, and renders the same output as the unreordered chain within tolerance.
- Command buffers: an unchanged bank is not re-recorded; two voices of one template share one buffer.
- Instances: with budget N and N+k instances, exactly N render and the virtual ones keep their clock.
- Device thread: no allocation during replay (allocation hook or counting allocator in tests).

## 13. Milestones

1. **Offline core.** Signal model, node interface, sine, gain, low/high-pass, FFT EQ, compiler with domain conversion and reordering, command buffers and pools, null device, tests. Proves domain handling first.
2. **Audible.** WASAPI backend, device thread, command and return queues. A sine through the master is heard at 44.1, 48 and 96 kHz.
3. **Scene sound** (first user-visible goal). `AudioSceneSystem`, emitter and listener, resident WAV playback, attenuator, spatializer, instances and voices.
4. **Full first DSP scope.** Parametric EQ, multiband compressor, clipper, limiter, nested mixer banks, sends, voice-template buffer reuse.

## 14. Open Questions

- Delay compensation across banks.
- Multi-listener support.
- Whether reorder of smoothed (time-varying) gains is acceptable, or reorder only nodes with constant parameters.
- Where the graph description lives as an asset, once the editor exists.
- How the device thread maps onto the future scheduler (it stays outside it in this design).

## References

- Exploration and brainstorm log: [audio-dsp.md](audio-dsp.md)
- Research: [middleware](sources/audio-research-middleware.md), [tools and libraries](sources/audio-research-tools-libs.md), [optimisation](sources/audio-research-optimisation.md)
- Related: [bounding volumes](bounding-volumes.md), [actor archetypes](actor-archetypes-design.md)
- Code: `src/Engine.SFX/`, `src/Engine.Scene/SceneSystem.hpp`, `src/Engine.Scene.Support/SceneSystemTypeMappedRegistry.hpp`, `src/Engine.Physics.Scene/PhysicsSceneSystem.cpp`, `src/Engine.GFX.Render.Command/`
