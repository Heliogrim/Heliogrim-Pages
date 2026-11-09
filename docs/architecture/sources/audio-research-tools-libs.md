# Audio research: creative tools and open-source libraries

Research date: 2026-11-03. Read-only web research; every claim is from the first-party page linked next to it unless flagged.
Flags: **UNVERIFIED** means the page could not be read in full or the claim comes from a secondary source.

---

## Part A: Creative tools

### 1. FL Studio (Image-Line online manual, current online edition; the pages carry no version number. Patcher page references "FL Studio 2025" behaviour)

| Feature | Detail | Source |
|---|---|---|
| Mixer size | 500 insert tracks + 1 Current track + Master | [mixer.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/mixer.htm) |
| Inserts | 10 FX slots per track. Chain: FX slots -> built-in 3-band EQ / phase / stereo sep / vol / pan -> fader (post-FX) | same |
| Sends | Any insert can send to any other. Post-fader by default. Pre-fader via the Fruity Send plugin. Feedback loops are blocked | same, [Fruity Send](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Fruity%20Send.htm) |
| Sidechain | A sidechain is a send at 0% level that only sidechain-aware plugins hear; "All audio sends are ALSO sidechain sends" | [mixer.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/mixer.htm) |
| "Current" track | Receives whatever track is selected; meant for analysers (Wave Candy, Edison) | same |
| Clipping | Only the Master (or a track sent directly to an ASIO output) can clip; inserts are float | same |
| PDC | Automatic PDC tracks plugin latency incl. routing, multi-I/O and sidechains. Manual offsets in ms / samples / beats. Per-plugin stored latency override for plugins that misreport. Live-input bypass ("When recording or not playing"); always applied on render | [mixer_trackprops.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/mixer_trackprops.htm) |
| Plugin hosting | Windows: 32/64-bit VST 1/2, VST3, CLAP, native FL format. macOS adds AU | [plugins_supported.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins_supported.htm) |
| Wrapper options | Per-plugin: fixed-size buffers, "Allow threaded processing", "Allow smart disable", bridging | [wrapper.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/wrapper.htm) (option names from search snippet; **UNVERIFIED** in full) |
| Patcher | Modular graph inside one FX/instrument slot. Typed ports: yellow = audio, red = parameter/automation, green = events/MIDI. Modules at the same depth from the input are "processed at the same time (multithreaded)"; deeper columns run in order. Automatic latency compensation inside. Optional per-module CPU and latency view. Control Surfaces = custom UI bound to parameter ports; Formula Controller adds logic | [Patcher.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Patcher.htm) |
| Automation clips | Clip-based, not pattern-bound. 11 segment curve types (Single/Double curve, Alt variants, Hold, Stairs, Smooth stairs, Pulse, Wave, Half sine, Smooth) with draggable tension. LFO mode layered over the envelope (multiply or add). MIN/MAX output rescale. Can be note-triggered | [playlist_automationclip.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/playlist_automationclip.htm) |
| Audio-driven control | Fruity Peak Controller: envelope follower (base, vol -200..200 %, tension, decay) + LFO; outputs Peak / LFO / Peak+LFO, linkable to any parameter. Negative vol = ducking. Formula Controller: math expressions. X-Y Controller | [Fruity Peak Controller](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Fruity%20Peak%20Controller.htm), [effects_plugins.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/effects_plugins.htm) |
| Visualisation | Wave Candy: oscilloscope, scrolling spectrogram, peak meter (Peak, PPM, RMS, VU, Leq(A), ITU-R BS.1770), vectorscope. Also Spectroman, dB Meter | [Wave Candy](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins/Wave%20Candy.htm) |

Native effects by category ([effects_plugins.htm](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/effects_plugins.htm)):
- **Dynamics:** Fruity Limiter (single-band compressor/limiter/maximiser), Fruity Compressor, Fruity Multiband Compressor (3 bands), Maximus (multiband maximiser), Emphasis, Soft Clipper, Transient Processor, Transmitter, Low Lifter, Soundgoodizer.
- **EQ:** Parametric EQ 2, EQUO (graphic EQ), 7-band, Bass Boost; Fruity Convolver can act as a phase-linear EQ.
- **Reverb:** Fruity Convolver (convolution), Reeverb 2, LuxeVerb (algorithmic), Edison convolution (offline).
- **Delay:** Delay 2/3 (tempo-synced), Delay Bank, Multiband Delay, Gross Beat (time/volume manipulation).
- **Filters:** Love Philter, Free Filter (SVF), Vocoder, Vocodex.
- **Modulation:** chorus, flanger, phaser variants.
- **Distortion:** WaveShaper (custom curves), Squeeze (bit reduction), Distructor.
- **Tools:** Frequency Shifter, Frequency Splitter (2–3 bands), Pitch Shifter (pitch + formant), Pitcher, Newtone, Stereo Shaper (M/S), Spreader, Fruity Center (DC removal), Tuner.

**What translates to a game engine / editor**
- Bus graph with any-to-any sends, explicit pre/post-fader choice and cycle rejection. Sidechain = zero-gain send that only key inputs consume; this is the model for ducking music under dialogue.
- Latency compensation across the bus graph. This matters if lookahead limiters, FFT or convolution reverbs sit on some buses but not others.
- Patcher-style typed-port graph (audio / control / event) as the editor's DSP-graph authoring UI. Its depth-column parallelism is a simple scheduling rule worth copying for multi-core mixing.
- Automation curve types + tension + LFO overlay map directly onto RTPC curves in an editor.
- Peak Controller = runtime envelope follower bound to any parameter (sidechain ducking, gameplay reacting to loudness).
- A "Current track" analyser = an editor probe that attaches meters/scopes to the selected bus; BS.1770 loudness meter for the master.
- Plugin hosting (VST3/CLAP) is an editor-only concern; not needed at runtime.

### 2. Blender (Manual 5.2 LTS; one strip page reports 5.4, updated 2026-11-02)

| Feature | Detail | Source |
|---|---|---|
| Speaker object | Sound data-block (Cache = decode to RAM; Mono required for 3D/pan), Mute, Volume, Pitch. Distance: Volume Min/Max, Attenuation, Max Distance, Distance Reference. Cone: inner/outer angle, Outer Cone Volume, linear interpolation between cones | [speaker.html](https://docs.blender.org/manual/en/latest/render/output/audio/speaker.html) |
| Scene audio | Distance Model: Inverse / Linear / Exponential, each plain or Clamped (OpenAL semantics). Doppler Speed (343.3 m/s default), Doppler Factor. Update Animation Cache | [scene properties](https://docs.blender.org/manual/en/latest/scene_layout/scene/properties.html) |
| VSE sound strips | Per-strip volume (animatable with a curve overlay on the strip), offset, Mono mixdown, Pan (stereo -1..1; for >2 speakers the value ×90° is an angle and wraps), Preserve Pitch on speed change, waveform display with clipping shown in red, RAM caching. Overlapping strips auto-mix | [strip_properties.html](https://docs.blender.org/manual/en/dev/video_editing/edit/montage/strips/strip_properties.html), [sound.html](https://docs.blender.org/manual/en/latest/video_editing/edit/montage/strips/sound.html) |
| Strip modifiers | Pitch (semitones+cents or ratio, formant preservation, quality High / Fast / Consistent for animated pitch), Echo (delay, feedback, mix), Sound Equalizer (35 Hz–20 kHz, ±35 dB per the 4.0 manual) | [pitch.html](https://docs.blender.org/manual/en/latest/video_editing/edit/montage/modifiers/pitch.html), [echo.html](https://docs.blender.org/manual/en/latest/video_editing/edit/montage/modifiers/echo.html) (echo from search snippet, **UNVERIFIED**), [4.0 modifiers](https://docs.blender.org/manual/en/4.0/editors/video_sequencer/sequencer/sidebar/modifiers.html) |
| Bake sound to F-curve | Graph Editor > Channel > Sound to Samples: band-pass (lowest/highest frequency), envelope "hull" with attack/release, threshold, accumulate/additive, square output with threshold. Then Samples to Keys to edit | [graph editor channels](https://docs.blender.org/manual/en/latest/editors/graph_editor/channels/editing.html) |
| Audaspace | Apache-2.0 C++ library (v1.10.0 per docs site). Input/output devices with 3D audio, file I/O, LP/HP filters, delay, reverse, fade, generators, channel/format/rate "respecification" (float32 internally), simple and non-linear sequencing | [audaspace.github.io](https://audaspace.github.io/), [repo](https://github.com/audaspace/audaspace) |

Not confirmed on first-party pages, so **UNVERIFIED**: Audaspace backend list (WASAPI / PulseAudio / CoreAudio / OpenAL / SDL / JACK), HRTF, convolution, dynamic music. Neither the docs front page nor the README lists them.

**What translates**
- Speaker-object parameter set (min/max volume clamps, reference/max distance, cones) is a sensible baseline component.
- "Sound to Samples" = offline analysis that bakes an envelope into an animation curve. Doing this at import time drives animation cheaply with no runtime FFT.
- Waveform on timeline clips with clipping highlighted, and volume curves drawn over the waveform: good editor UX for a sequencer/cinematics track.
- Quality modes for pitch shifting (render vs preview vs animated) are a useful pattern for an editor preview path vs a shipping path.

### 3. Cinema 4D (Maxon help; versions R21, S22, R23, R25 and the current 2027 help, per page)

| Feature | Detail | Source |
|---|---|---|
| Sound Effector (MoGraph) | Loads a sound file, shows a live per-frame amplitude/frequency graph. Any number of **Probes** (rectangles over frequency × loudness). Distribution: Iterate / Distribute / Blend across clones. Sampling: Peak / Average / Step (Step spreads the spectrum profile across clones). Per-probe Decay, Strength (negative inverts), Clamp, Colour/gradient. Log/linear frequency display blend | [R23 Effector tab](https://help.maxon.net/c4d/r23/en-us/Content/html/OESOUND-ID_MG_BASEEFFECTOR_GROUPEFFECTOR.html), [R25 overview](https://help.maxon.net/c4d/r25/en-us/Content/html/OESOUND.html) |
| Sound Field | "converts frequency ranges of audio files into Field values", mixable with other fields/modifier layers on effectors and deformers (2027 help) | [FSOUND.html](https://help.maxon.net/c4d/en-us/Content/html/FSOUND.html) |
| Sound tracks | Timeline Sound tracks with keyable Volume and Balance, curves visible in Dope Sheet | search snippet of [Key Properties](https://help.maxon.net/c4d/2023/en-us/Content/html/CKPLA-ID_CKEY_PROPERTIES.html), **UNVERIFIED** |
| 2D Sound Rendering | Mixes Timeline Sound tracks (volume/balance) into one 16-bit 44 kHz stereo WAV; range Document / Preview / Render | [S22 10829](https://help.maxon.net/c4d/s22/us/html/10829.html) |
| 3D Sound Rendering | One mono 16-bit 44.1 kHz WAV per Microphone object. Volume and pitch from positions/velocities of speakers, cameras and microphones; optional Doppler. Stereo needs two mics, combined in an external editor | [S22 10830](https://help.maxon.net/c4d/s22/us/html/10830.html), [R21 de](https://help.maxon.net/c4d/r21/de/html/10830.html) |
| XPresso Sound node | Exists under XPresso > General | [GVSOUND](https://help.maxon.net/c4d/en-us/Content/html/GVSOUND-ID_GVPROPERTIES.html). Ports **UNVERIFIED** (page body not readable) |

Whether 3D Sound Rendering and Speaker/Microphone objects still ship in the 2026/2027 releases is **UNVERIFIED**; the latest page found is S22.

**What translates**
- The probe-on-spectrum UI is the best idea here for **audio-driven gameplay/VFX**: the designer draws rectangles on a live spectrogram, and each rectangle becomes a 0..1 control signal with decay/clamp/invert. The runtime needs only per-bus band energies, e.g. from an analyser node.
- Exposing audio analysis as a generic "field" (scalar source) that composes with other procedural inputs, instead of a special-case effector.
- Offline "render what microphone X hears" is equivalent to an engine's offline bounce from an arbitrary listener; useful for cinematics and regression tests of spatialisation.

---

## Part B: Open-source libraries

### 4. miniaudio (v0.11.26, 2026-10-31)

**Licence:** public domain or MIT-0, your choice ([README](https://github.com/mackron/miniaudio)). C, single file pair (`miniaudio.c` / `.h`), no dependencies. ABI is not stable between versions ([manual §1](https://miniaud.io/docs/manual/index.html)).

**Maintenance** ([CHANGES.md](https://raw.githubusercontent.com/mackron/miniaudio/master/CHANGES.md)): v0.11.22 2025-02-24, v0.11.23 2025-09-11, v0.11.24 2026-01-17, v0.11.25 2026-03-04, v0.11.26 2026-10-31. 0.11.26 is mostly fixes: sound end cut-off, volume smoothing races, scheduled node start times, races in async resource loading/teardown touching freed memory, and duplex resampling ring-buffer overflow. Active single maintainer (David Reid). The repo showed 3 open issues at time of reading ([repo](https://github.com/mackron/miniaudio)).

**Backends** in default priority order: WASAPI, DirectSound, WinMM, Core Audio, sndio, audio(4), OSS, PulseAudio, ALSA, JACK, AAudio, OpenSL ES, Web Audio, Custom, Null ([manual §15](https://miniaud.io/docs/manual/index.html)). A custom backend can be plugged in without modifying the library.

**WASAPI details**
- Loopback capture is WASAPI-only ([manual §1.1](https://miniaud.io/docs/manual/index.html)). Per-process include/exclude via `wasapi.loopbackProcessID` + `loopbackProcessExclude`.
- Shared mode by default; exclusive via `playback.shareMode = ma_share_mode_exclusive`. Exclusive mode returns an error if the native format is unsupported.
- Low latency: shared mode uses `IAudioClient3::InitializeSharedAudioStream`. That fails when `AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM` is set, so an app sample rate different from the device rate silently loses low-latency mode unless `wasapi.noAutoConvertSRC = true` makes miniaudio resample itself ([manual §15.1](https://miniaud.io/docs/manual/index.html)).
- Other config: `noDefaultQualitySRC`, `noHardwareOffloading` (IAudioClient2 offload, Win8+), `usage` (MMCSS / Avrt thread characteristics, e.g. pro-audio).
- Device change: "Automatic stream routing is ... explicitly enabled for WASAPI and Core Audio" ([manual §17](https://miniaud.io/docs/manual/index.html)). On a default device it follows the OS default switch; not supported in exclusive mode. Opt out with `noAutoStreamRouting`.
- Sourcing caveat: the exclusive-mode, offload, loopback-PID, usage and routing-follows-default details come from CHANGES.md search excerpts and generated bindings docs (e.g. [pkg.odin-lang.org](https://pkg.odin-lang.org/vendor/miniaudio/)). The `ma_device_config` declaration itself was not read in the 4 MB header, so treat these as **UNVERIFIED** at field level. A WASAPI reroute deadlock was reported in issue #1149 (tracker only, **UNVERIFIED**).
- `MA_COINIT_VALUE` defaults to `COINIT_MULTITHREADED`. There is a UWP path via `ActivateAudioInterfaceAsync` ([manual §2.1](https://miniaud.io/docs/manual/index.html)).

**Callback threading model** ([manual §1.1](https://miniaud.io/docs/manual/index.html), [header](https://raw.githubusercontent.com/mackron/miniaudio/master/miniaudio.h)): data flows through an async callback on a backend-owned thread. Never call device init/uninit/start/stop inside it (deadlock); signal another thread instead. Never process more than `frameCount` frames. Sound end-callbacks fire on the audio thread.

**Node graph** ([manual §7](https://miniaud.io/docs/manual/index.html))
- Nodes have N input buses and M output buses. Several outputs attached to one input are summed.
- Pull model from the endpoint, recursive. Always f32. Channel counts are fixed at init and must match across a connection.
- Per-output-bus volume. Node start/stop states can be scheduled on the global clock (one pending start + one stop). A global clock and per-node local clocks.
- Custom-node flags: PASSTHROUGH, CONTINUOUS_PROCESSING, ALLOW_NULL_INPUT, DIFFERENT_PROCESSING_RATES, SILENT_OUTPUT.
- Thread safety: only `ma_node_graph_read_pcm_frames()` is lock-free. Attach/detach use one spinlock per input and output bus. **Detach blocks until the audio thread is done with that bus**, which can take as long as processing the bus's whole upstream subtree. Advice is to detach leaves first.
- Attachment lists are forward-iterated singly-linked lists with head insertion, so an attach is "a single atomic assignment" from the reader's view.
- Single-threaded processing; no parallel graph evaluation mentioned.
- Filters as standalone DSP: `ma_biquad`, lpf/hpf/bpf (1st/2nd/Nth order), notch, peak, lo/hi shelf ([manual §11](https://miniaud.io/docs/manual/index.html)). Node wrappers (`ma_*_node`, `ma_delay_node`) exist in the header per common knowledge; **UNVERIFIED** this session.

**Engine / sound / spatializer** ([manual §5](https://miniaud.io/docs/manual/index.html))
- `ma_engine` = resource manager + node graph. It owns or borrows a device, or runs device-less via `ma_engine_read_pcm_frames()`. Several engines can share one resource manager.
- `ma_sound`: fire-and-forget or managed; volume, pan, pitch, fades, start/stop scheduled on engine time, looping, seek, end callback. `ma_sound_group` = submix with the same API.
- Spatializer "roughly on feature parity with OpenAL":
  - Attenuation none / inverse (default, = AL_INVERSE_DISTANCE_CLAMPED) / linear / exponential, with rolloff, min/max gain, min/max distance.
  - Cones on both sound and listener.
  - Doppler from velocities with a per-sound factor.
  - Multiple listeners: a sound uses the closest unless pinned. Relative or absolute positioning. OpenGL coordinates (−Z forward).
  - No HRTF or occlusion ("planned").
- Perf flags: `NO_PITCH` / `NO_SPATIALIZATION` skip stages. Matching sample rates avoids resampling.

**Resource manager** ([manual §6](https://miniaud.io/docs/manual/index.html))
- Load flags STREAM / DECODE / ASYNC / WAIT_INIT / LOOPING. Default: encoded data in memory, decoded on the fly.
- Refcounted by a 64-bit path hash, so collisions are possible.
- Decoding in 1-second pages. A stream holds 2 pages; the audio thread gets MA_BUSY on underrun. Seeks are async. Completion via fences/callbacks/polling.
- Job system: one job thread by default, or 0 threads with jobs pumped by the app (`ma_resource_manager_next_job` / `ma_job_process`), which suits an engine scheduler.
- MPMC fixed-capacity job queue: "not currently lock-free, and instead uses a spinlock". Slot allocation is lock-free with refcount ABA mitigation; per-object execution counters keep ordering. Posting signals a semaphore (mutex+condvar on POSIX), and **streams post page-load jobs from the audio thread**. Mitigation: non-blocking queue flag + app-driven job processing.
- SPSC lock-free ring buffers provided.
- Custom VFS (must be thread-safe) and custom decoder vtables.

**Assessment for a AAA engine**
- Strengths: permissive licence; best-in-class breadth of native backends with real WASAPI knowledge (IAudioClient3 low-latency pitfall, loopback, rerouting, MMCSS); clean device/engine/graph layering; device-less mode; app-pumped job processing; exceptionally active maintenance.
- Weaknesses for AAA:
  - Audio-thread work is not fully wait-free (spinlocks, semaphore posts from the audio thread on streams).
  - Detach blocks the caller for up to an upstream-subtree render.
  - Graph topology is mutated directly from game threads, not through a command queue.
  - Single-threaded graph evaluation.
  - Fixed channel counts per connection.
  - OpenAL-level spatialisation only.
  - No voice virtualisation / priority / concurrency limits.
  - C API with no ABI stability.
- **Copy:** the WASAPI flag set as a checklist for our native backend (shared low-latency via IAudioClient3 + own SRC; exclusive as an option; loopback; default-device rerouting outside the audio thread; MMCSS). Pull-model graph with per-bus gains. Fwd-list attachment with atomic head publish. Scheduled start/stop on a sample clock. Paged streaming with BUSY-on-underrun. Jobs pumped by the engine's own task system. Device-less render for offline bounce/tests.
- **Avoid:** blocking detach and spinlocks on the audio path (use a command queue + deferred deletion/epoch reclamation). Semaphore posts from the RT thread. Path-hash identity (use asset GUIDs).

### 5. SoLoud (last release 20200207; last commit 2024-08-13)

**Licence:** zlib/libpng. Some bundled parts are Unlicense / CC0 / WTFPL / public domain ([solhsa.com/soloud](https://solhsa.com/soloud/), [repo](https://github.com/jarikomppa/soloud)). C++ core with many language bindings.

**Maintenance:**
- Latest tagged release **SoLoud 20200207** (7 Feb 2020; `SOLOUD_VERSION 202002`). It added JACK / Nosound / MiniAudio backends, Freeverb, the noise source, live filter-parameter query, FTZ/DAZ in audio threads, and `annexSound` ([releases](https://github.com/jarikomppa/soloud/releases)).
- Last commits 10–13 Aug 2024, e.g. "Flush to zero (FTZ) for ARM" ([commits](https://github.com/jarikomppa/soloud/commits/master)).
- 97 open issues and 24 open PRs at time of reading. Effectively dormant / low activity. Downstream forks (flutter_soloud etc.) carry their own fixes.

**Voice model** ([voicemanagement](https://solhsa.com/soloud/voicemanagement.html), [soloud.h](https://raw.githubusercontent.com/jarikomppa/soloud/master/include/soloud.h), [soloud.cpp](https://raw.githubusercontent.com/jarikomppa/soloud/master/src/core/soloud.cpp))
- `VOICE_COUNT 1024` virtual voices (hard limit 4095 by editing the header).
- `mMaxActiveVoices = 16` by default (`setMaxActiveVoiceCount`).
- Active set selection: "must tick" voices first (all buses are must-tick and protected), then the loudest by **set volume**, not by post-attenuation loudness per the page wording.
- Per-source inaudible behaviour: pause (default), kill, or keep ticking (e.g. speech).
- Voice groups: handles that apply one operation atomically to many voices (≤4095 groups; must be destroyed manually) ([voicegroups](https://solhsa.com/soloud/voicegroups.html)).
- Clocked play (`playClocked`) for sample-accurate starts within a buffer.

**Buses** ([mixbus](https://solhsa.com/soloud/mixbus.html))
- A bus is itself an audio source: volume, pan, filters, and 3D. Nestable. One instance per bus.
- `annexSound` moves a live voice to another bus.
- Visualisation: 256-bin FFT, 256-sample wave, per-channel approximate volume.
- Caveat: chaining buses adds resampler latency offsets (0 / 1 / more samples by resampler).
- Buses count against the active voice limit.

**Filters** ([filters](https://solhsa.com/soloud/filters.html), [soloud.h](https://raw.githubusercontent.com/jarikomppa/soloud/master/include/soloud.h))
- `FILTERS_PER_STREAM 8`.
- Filter/FilterInstance split; channel-planar buffers.
- Param 0 = wet/dry by convention. Faders per param (fade/oscillate). Parameter introspection (name/type/min/max) for generic editor UIs.
- Filters: BiquadResonant, Echo, Lofi, Flanger, DCRemoval, FFT, BassBoost, WaveShaper, Robotize, Freeverb.
- Mixing granularity `SAMPLE_GRANULARITY 512`.

**3D model** ([concepts3d](https://solhsa.com/soloud/concepts3d.html))
- 3D only alters pan and play speed.
- OpenAL clamped attenuation: inverse / linear / exponential with rolloff and min/max distance. OpenAL 1.1 Doppler with per-source factor. Speed of sound 343 by default.
- Optional distance delay (off by default).
- `AudioCollider` callback returns volume and can reposition the source; the example is one river ambience instead of many voices.
- Speaker gain = (dot(speaker, dir) + 1) / 2 for arbitrary layouts. The author concedes it is less clear than VBAP.
- Requires an explicit `update3dAudio()` call.

**Backends** ([backends](https://solhsa.com/soloud/backends.html)): SDL1/2 (primary, most tested), PortAudio, MiniAudio (bundled), WinMM, WASAPI ("Experimental"), XAudio2 ("Experimental"), ALSA, JACK, OSS, OpenAL (high latency), CoreAudio, OpenSL ES, Vita homebrew, Nosound, Null. Consoles are excluded for SDK licence reasons.

**Threading** ([backends](https://solhsa.com/soloud/backends.html), [soloud.cpp](https://raw.githubusercontent.com/jarikomppa/soloud/master/src/core/soloud.cpp))
- One global audio mutex. `mix_internal` holds it across faders, active-voice selection, the whole bus mix and global filters; clipping and visualisation run outside it.
- API calls from game threads take the same mutex, so the audio thread can block on game code (priority inversion).
- 3D data is kept outside the mutex.
- FTZ/DAZ set once on the mixing thread.

**Assessment for a AAA engine**
- Strengths: simple, readable design; the virtual-voice concept with inaudible-behaviour policy; voice groups for atomic multi-voice ops; clocked starts; filter parameter introspection; colliders for area sources; bus visualisation hooks; permissive licence.
- Weaknesses: global mutex around the entire mix; 16 active voices default; ranking by set volume; fixed 8 filters per stream; panning-only 3D (no HRTF/occlusion); WASAPI / XAudio2 marked experimental; no release in almost 7 years with a large open backlog.
- **Copy:** virtual voices with per-sound inaudible policy (pause / kill / keep-ticking); "protected / must-tick" flags; voice-group handles; clocked start; parameter metadata for auto-generated editor UIs; collider-style area/volume emitters; FTZ/DAZ on the mixer thread.
- **Avoid:** global mixer lock and synchronous API (use lock-free command queues + double-buffered parameter state); priority by authored volume (rank by estimated audibility after attenuation and occlusion, plus priority); fixed filter slots; speaker-dot panning (use VBAP/ambisonics); relying on it as a Windows output layer.

---

## Cross-cutting takeaways for Heliogrim
1. **Output backend:** write a native WASAPI backend using miniaudio's flag set as a requirements checklist: IAudioClient3 low-latency shared mode with our own SRC, optional exclusive mode, MMCSS, loopback for capture/tests, and default-device rerouting handled on a non-RT thread. Note: "Core Audio" in Windows terms is the MMDevice/WASAPI stack; macOS Core Audio is a separate later backend.
2. **Real-time discipline:** both libraries take locks touching the audio path (miniaudio spinlocks, blocking detach, semaphore posts; SoLoud's global mutex). Our design should use command queues, deferred frees and no blocking on the RT thread.
3. **Voice management:** SoLoud's virtual voices + inaudible policy + groups, ranked by audibility × priority, are not present in miniaudio.
4. **Graph:** miniaudio's pull graph + scheduled node states, plus FL Patcher's typed ports and depth-column parallelism, plus FL-style PDC for lookahead/FFT nodes.
5. **Editor:** RTPC curves with FL curve types/tension/LFO overlay; a "current bus" analyser with BS.1770 loudness; C4D spectrum probes as designer-authored control signals; Blender-style sound-to-curve baking at import; waveform + clip display on timelines.
