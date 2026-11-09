# Audio and DSP (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

This note collects the design direction for the sound system: asset ingestion from middleware and DAWs, live and preprocessed pipelines, multi-channel output, 3D spatialization, the DSP component library, and the audio thread model. It starts from an external design review ([source](sources/audio-dsp-gemini-review.md)). Where the review is vague or doubtful, the claim is marked **unverified** and the open question is listed in section 8.

## 0. Current State in the Engine

- `Engine.SFX` has a `CoreModule` shell (`Audio`) with `setup`, `start`, `stop` and `destroy`. It registers importers only.
- Importers exist for WAV, FLAC and Vorbis (`Engine.SFX/Importer/`). Sound assets are defined in `Engine.Assets.Type/Audio/Sound.hpp`.
- There is no voice pool, mixer, bus graph, output device backend or DSP code yet.

Everything below is a target, not a description of existing code.

## 1. Goals and Constraints

- Play sound assets from prepared asset sets and raw files (middleware banks proposed out of scope, section 8), with one event-based entry point for game code.
- Native multi-channel output: stereo, 5.1, 7.1, 7.1.4 and higher-order Ambisonics. The bus layout is data, not code.
- Live (procedural) and preprocessed (baked) sounds use the same graph and the same parameters.
- No locks, no allocation and no blocking I/O on the audio thread.
- Game code changes sound through parameters and events. It never touches DSP internals.
- Competitive scale: thousands of requested voices, with most of them culled, virtualized or never rendered.

## 2. Ingestion Pipelines

Three input classes, each with a clear owner:

| Input | Format | Owner | Notes |
|-------|--------|-------|-------|
| Raw files | WAV, FLAC, Vorbis (existing importers) | Importer | Already in `Engine.SFX`. Source of truth for DAW stems. |
| DAW stems | Multi-track WAV plus JSON metadata | Asset cooker | Stems are WAV, so this is a metadata problem, not a format problem. |
| Middleware banks | Wwise `.bnk`/`.wem`, FMOD `.bank` | Bank parser | Proposed out of scope: licence forbids reverse engineering, no public spec (section 8). |

Design rules:

- **Cooker first.** Assets are converted at build time into the target format (Opus, ATRAC or PCM, chosen per platform for memory versus CPU). The runtime never decodes a format it cannot stream in real time.
- **Events map to engine triggers.** A middleware event ID resolves to a native sound event. Game code calls the native event, not the middleware API.
- **Streaming is asynchronous.** Media is read through a ring buffer on the I/O side. The audio thread only consumes filled buffers.
- **Stem sync.** Adaptive music layers (drums, bass, leads) start on one shared transport clock, sample-accurate. Beat matching uses the stem metadata, not wall-clock time.

## 3. Output Layout and Virtual Voices

- The bus graph is built from a layout description (channel count, speaker positions, bed and height channels). Changing the output layout does not change game code.
- Supported layouts: stereo, 5.1, 7.1, 7.1.4 (bed plus height), HOA up to order 5 (candidate; cost grows with order, so cap it per platform).
- **Virtual voices.** Priority-based culling decides which voices are rendered. Inaudible or distant voices are virtualized: they keep their playback position and become real again when they re-enter the audible set. Only the audible set costs CPU.
- Culling uses a perceptual score: distance attenuation, priority, loudness and bus budget. The exact formula is open (section 8).

## 4. 3D Spatialization

- **Binaural rendering (HRTF).** A universal HRTF is the baseline. Personalized HRTFs are an option that must be measured, not assumed. A hearing profile is only useful if it changes results in blind tests.
- **Doppler and traveling sound.** Fractional delay lines plus pitch shift for fast sources, using source velocity. Air absorption applies as a distance-dependent low-pass.
- **Occlusion, obstruction and blocking.** Ray or volume queries against the physics scene produce two values per voice: occlusion (direct path blocked) and obstruction (partly blocked). Each drives a low-pass and a dry/wet level. Results are smoothed over time so doors and corners do not click.
- **Reverb and early reflections.** A hybrid of algorithmic reverb and convolution. Geometry probes estimate room size and absorption. Early reflections come from the probe data, late tail from the room model.
- **Attenuators.** Distance curves (logarithmic, linear, custom spline) map to volume, low-pass cutoff and spread. Curves are assets, not code.

## 5. DSP Component Library

The graph is lock-free. Effects can sit on a voice, a bus or an auxiliary send.

| Component | Target behavior | Notes |
|-----------|-----------------|-------|
| Compressor | Feed-forward, threshold, ratio, attack, release, soft knee | Standard. Ship first. |
| Parametric EQ | Low shelf, peak, high shelf, notch | Biquad cascade in TDF-II, float state, FTZ/DAZ on the audio thread (section 8). Float64 state only if low-frequency tests show noise. |
| Limiter | Look-ahead true-peak limiter on master | Peak detection on a 4x oversampled signal (BS.1770 true peak, section 8). |
| Clipper | Soft or hard transient clipper | Pair with the limiter; define its place in the chain. |
| Side-chain and ducking | Envelope follower on a key bus, gain on target buses | Covers dialogue ducking and sound blocking. |
| MIDI processing | Parse MIDI events into synth parameters, pitch bend, musical transitions | Needed for live synthesis and adaptive music. |
| Dynamic mixing | Crossfade stems or variants by RTPC (health, RPM, intensity) | RTPCs are parameters on the command queue (section 7). |
| Anti-high-ringing | Adaptive high-frequency resonance control after compression or distortion | **Unverified**: the term is not standard and the review gives no algorithm. Needs a definition before design. |
| Echo and delay | Tempo-synced feedback delay, damping filter, ping-pong spread | Tempo sync reads the transport clock from section 2. |

Order of work: compressor, EQ, limiter and clipper, ducking, delay. Spatial and procedural components come after the bus graph works.

## 6. Live and Preprocessed Pipelines

- **Preprocessed.** Pre-rendered stems, baked reverb tails and packaged banks. Lowest CPU, largest disk footprint.
- **Live (procedural).** Physical modeling and granular nodes generate variation at runtime: wind, engine, fluid, footsteps. Lowest disk footprint, highest CPU.
- Both feed the same bus graph. A sound asset chooses its source type, not the mixing path.
- Budget rule: each voice reports its estimated CPU cost. The scheduler culls live voices first when the budget is exceeded.

## 7. Threading and Command Queues

1. **Thread isolation.** Audio renders on a dedicated high-priority thread, separate from game logic and render.
2. **Command queue.** Game code sends position changes, RTPC values and event triggers through a lock-free single-producer, single-consumer queue into the audio thread. One queue per game thread that emits audio commands, or a multi-producer queue with a clear cost.
3. **Memory.** Fixed pools, allocated at startup. No `malloc`/`free` inside the render callback.
4. **Parameter smoothing.** Every parameter that can jump (volume, cutoff, pan) is smoothed on the audio thread. Hard steps produce clicks.

This matches the existing engine direction of explicit ownership across threads, but it must be checked against the scheduler's task model before any code.

## 8. Decisions Needed and Claims to Verify

**Decisions needed**

1. First output backend: SDL3 (proposed, see below), and whether it runs as a `CoreModule` next to `Audio`.
2. Middleware banks: proposed out of scope (see below). A native event system comes first.
3. Voice culling formula: which inputs, how they are weighted, and the per-platform voice budget.
4. Bus graph description format: code, asset, or both.
5. Steam Audio for spatialization: adopt, or build in-house.

**Claims checked (review 2026-11-02)**

- **"Embody Immerse" (partly true).** The product exists and builds a personalized HRTF in the cloud from an ear photo. Its SOFA files are encrypted and not usable outside its own tools ([Steinberg FAQ](https://helpcenter.steinberg.de/hc/en-us/articles/360014590020-Immerse-with-VST-AmbiDecoder-FAQ)). Not usable as an engine HRTF source. Personalization stays research; the baseline is a generic SOFA HRTF.
- **Biquad "prevents numerical underflow" with TDF-II (wrong reason).** TDF-II is the usual floating-point choice because its intermediate sums stay closer in magnitude ([CMSIS-DSP](https://arm-software.github.io/CMSIS_5/DSP/html/group__BiquadCascadeDF2T.html)). It does not prevent underflow. Denormals are handled separately: flush-to-zero and denormals-are-zero set on the audio thread (MXCSR FTZ/DAZ on x86, FPCR.FZ on ARM64). Set them at audio-thread start and test with a decaying tail.
- **"Zero inter-sample clipping" from a limiter (needs oversampling).** True-peak measurement in ITU-R BS.1770 uses 4x oversampling at 44.1/48 kHz ([AES summary](https://aes.org/resources/audio-topics/loudness-project/learn-more/)). A true-peak limiter has to detect peaks on an oversampled signal. Target: 4x detection, ceiling around -1 dBTP.
- **Anti-high-ringing.** Still undefined (section 5). Dropped until someone can name an algorithm.
- **Parsing `.bnk`/`.wem` directly (out of scope).** The Audiokinetic SDK agreement forbids reverse engineering the "Wwise Technology" ([agreement, §2.2.3](https://www.audiokinetic.com/download/documents/License_Agreements/Audiokinetic_SDK_Agreement_v2_2023-05-17.pdf)). No official public spec exists, only community tools. The FMOD EULA text was not retrieved. Treat middleware banks as out of scope unless legal review says otherwise; import DAW stems and raw files instead.

**Build-or-buy candidates (review 2026-11-02)**

- **Output backend: SDL3.** SDL3 is already vendored (`vendor/sdl`). It has `SDL_AudioStream` with callbacks and channel maps for mono through 8 channels (5.1 and 7.1) ([SDL3 audio](https://wiki.libsdl.org/SDL3/CategoryAudio)). 7.1.4 (12 channels) is not documented. Use SDL3 for the first milestone and write a WASAPI backend only for layouts above 8 channels.
- **Spatialization: Steam Audio.** Open source under Apache 2.0 since v4.5.2 (February 2024) ([repo](https://github.com/ValveSoftware/steam-audio)). Covers HRTF rendering (a SOFA subset), occlusion, transmission, reflections, baked reverb and pathing. That is most of section 4. Evaluate it before designing section 4 in-house. If adopted, the bounding-volume portals ([bounding-volumes.md](bounding-volumes.md)) feed its pathing instead of a custom propagator.
- **Reference design for rooms and portals:** Wwise Spatial Audio (rooms, portals, diffraction mapped to obstruction) ([overview](https://blog.audiokinetic.com/rooms-and-portals-with-wwise-spatial-audio/)). Use it to compare designs only.

## 9. Next Steps

- Decide the open items in section 8 (issues first, ADRs when accepted).
- Smallest end-to-end slice: play one imported WAV through SDL3 output with one gain stage. This proves the audio thread, command queue and voice lifetime before any DSP.
- Evaluate Steam Audio on that slice (one HRTF voice) before designing section 4.
- Then build the bus graph with one compressor, then add EQ, limiter and ducking.
- Write the cooker input format for stems (WAV plus JSON metadata) as a short spec.

## 10. Brainstorm Progress (2026-11-03)

**Status**: brainstorm in progress, no design approved. Items marked *vision* describe where the engine is heading, not code that exists today.

### Direction set by the owner

- **Own engine, not middleware.** The owner previously built DSP, mixers, channels, a Butterworth band compressor/EQ and trigonometric distance attenuation; that code is lost and will be rebuilt. FMOD, Wwise, Steam Audio, miniaudio and SoLoud serve as references only.
- **Native output.** SDL3 is expected to be dropped (*vision*). First backend: Windows Core Audio (WASAPI). 7.1.4 and audio objects on Windows need Windows Sonic (`ISpatialAudioClient`), a later step. macOS Core Audio would be a separate backend.
- **Users.** Scene sound and editor feedback sounds. First milestone: a spatial scene sound, not an editor ping.
- **Sample rate configurable.** 44.1/48 kHz are common; 96 kHz is a real target (owner's setup). Internal rate should match the device to avoid WASAPI shared-mode resampling.
- **Signal representation.** Packets between DSP nodes carry their domain (time domain vs FFT). Nodes declare commutativity so the graph compiler can reorder chains and minimise FFT/IFFT conversions. (Note, unverified as design rule: linear time-invariant nodes commute; nonlinear nodes such as compressor, clipper and limiter are reorder barriers.)
- **Execution via command buffers and pools.** Decided: record once per graph change, replay per block, with caching and reuse of recorded (sub-)buffers. The current render command path is a naive implementation that will be replaced (*vision*), so audio takes ideas from it, not its structure.
- **Threading.** No single game thread: the engine runs cooperative fiber tasks; platform event pumping and blocking IO run on dedicated threads. The current fiber task model is a placeholder; a real scheduler with task-graph dependencies (possibly EEVDF-like) is *vision*. The audio design must not depend on today's scheduler internals. Open guess: the device callback needs its own real-time thread outside the fiber scheduler.
- **Scene integration.** An audio SceneSystem maps pushed components to internal models, following the [actor archetype](actor-archetypes-design.md) pattern. A shared BVH / spatial query service for all systems is *vision* ([bounding volumes](bounding-volumes.md)).
- **Mixing.** Multiple mixer banks: group sub-mixes feed further mixers up to a master.
- **First DSP scope, every category once:** multiband compressor, EQ, low-/high-pass, clipper/limiter, spatializer, attenuators, synthesizer (sine). Extend later.
- **Loaders.** Reuse existing importers, but loader architecture and loader chains will be reworked for the new storage system (*vision*).
- **Observability.** Processing metrics are required (research: measure worst-case block time, not average). Observability is its own engine-wide topic, brainstormed separately; the current `Profiler`/`Stopwatch` will be dropped without direct replacement. The audio design leaves a hook only.
- **Game events and controls** need an intentional, designed integration.
- **Editor composition UI** with graphics and controls, likely after the MSDF/reflow UI rework (*vision*).

### Code check (2026-11-03)

- Importers: WAV, FLAC, Vorbis only. **No Opus importer** and no Opus vendor library. Vendored: `dr_libs`, `ogg`, `vorbis`.
- Graphics command path to model on: `RenderCommandBufferBase` (virtual record API) → `RenderCommandBuffer` (linked commands in a monotonic arena, released all at once) → `RenderCommandTranslator` (visitor with state, can reuse a native batch) → Vulkan `VkNativeBatch` with pooled `AccelCommandBuffer`s. Only Vulkan secondary buffers exist; no sub-range reuse.
- Scene systems: `SceneSystem` hooks plus `SceneSystemTypeMappedRegistry` (component → model, model create/update/readback/destroy). Systems are a compile-time list per scene (`GameScene` = physics + render). Audio would be a third entry.
- Observability: only a JSON trace `Profiler` and `Stopwatch` (scoped macro compiled out). No counters or metrics registry.
- No BVH or shared spatial query service exists.

### Project split (agreed)

1. Audio runtime: DSP core and node set, command buffers, WASAPI backend, SceneSystem, metrics. Design doc next.
2. Game event and control integration.
3. Editor composition UI, after the MSDF/reflow rework.

### Research (2026-11-03)

Three sourced reports, each claim linked and unverified points flagged:

- [Middleware feature inventory](sources/audio-research-middleware.md): FMOD 2.03.15, Wwise 2025.1.12, Steam Audio 4.8.1, cross-product table, top AAA differentiators.
- [Creative tools and open libraries](sources/audio-research-tools-libs.md): FL Studio, Blender, Cinema 4D, miniaudio, SoLoud. Both libraries lock on or near the audio thread; copy ideas, not design.
- [Optimisation paths](sources/audio-research-optimisation.md): banks, codecs, baking, dynamic graphs and variants, clustering, threading. Lists the hooks to design in from day one (definition/media split, residency, sound instance vs voice, per-source sends, compiled flat graphs, lock-free queues, coarse job graph, worst-case timing).

## References

- Design review (Gemini, raw): [sources/audio-dsp-gemini-review.md](sources/audio-dsp-gemini-review.md)
- Existing importers: `src/Engine.SFX/Importer/` in the engine repository
- Related: [Actor system (exploration)](actor-system.md)
