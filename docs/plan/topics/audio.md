# Audio

**Systems**: S38 · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. The research for this topic was done in November 2026 and lives in the [audio and DSP exploration](../../architecture/audio-dsp.md) with its [sources](../../architecture/sources/audio-research-middleware.md); the [audio runtime design](../../architecture/audio-runtime-design.md) is drafted and not yet approved. This page places it in the plan.

## Target

A fully integrated sound engine written in the project: a scene system mapping sound components to voices, a compiled DSP graph with domain tags (time versus frequency) and commutativity-driven reordering, hierarchical mixer banks, a spatialiser, a native Windows backend (WASAPI shared-mode event thread; Windows Sonic for 7.1.4 and objects), configurable sample rate (44.1, 48, 96 kHz), bank and streaming support, lock-free command and return queues, observability metrics, game-event integration, and an editor UI for graph composition after the canvas (S42).

## Current state (checked 2026-11-07)

- `Engine.Audio`: WAV, FLAC and Vorbis importers, `Audio` and `AudioFormat` types. No playback, device or DSP. Opus is not supported (the design wants it).
- The runtime design draft covers: instance to control step (audibility score, real and virtual voices), voice with a compiled per-voice chain, bus graph, device thread outside fibers, null device for offline tests, milestone 1 as an in-memory WAV emitter with camera listener, pan and distance, master bus, WASAPI.

## Guidance

- Finish the design's builder check and approval, then plan it as its own project in three steps as agreed: (1) runtime, (2) game-event and control integration, (3) editor UI after the canvas.
- Dependencies on this plan: the device thread is an affine service of the scheduler (S02); command buffers follow the block-recording decision (record once per graph change, replay per block with a per-block parameter table); the sound scene system reads `WorldPosition` (S07) and `LayerVolume` reverb regions (S29); banks stream through the residency manager (S03); observability metrics go through S04; loaders are reworked with storage.
- Keep the DSP node set from the design for the first scope (multiband compressor, EQ, low and high pass, limiter, spatialiser, attenuators, sine synth, one FFT-domain node to prove domain tags).
- Determinism: audio is client-only; the server never evaluates DSP, but audibility and occlusion queries use the shared bounds service (S44) so gameplay logic can reason about hearing.

## Done when

- The design's milestone 1 plays a scene sound that pans and fades with the camera through WASAPI; the null device runs the same graph in a test and the output is golden-compared.
- The first-scope DSP set runs in a compiled graph with a frequency-domain node reordered by the compiler.
- A cave layer applies its reverb volume; a weather state changes wind and rain beds.

## Open decisions

- Those listed in the design draft (threading versus scheduler, bus graph format, voice budget, archetype integration, editor tooling).
