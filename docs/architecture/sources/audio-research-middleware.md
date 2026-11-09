# Game Audio Middleware Feature Inventory: FMOD, Wwise, Steam Audio

Research date: 2026-11-03. Sources: official documentation only, read directly (not from search snippets).

| Product | Version documented | Primary source |
|---|---|---|
| FMOD Studio + FMOD Engine (Core/Studio API) | 2.03.15 (footer dated 2026-09-21) | https://www.fmod.com/docs/2.03/ (the page bodies are served from FMOD's docs CDN; the URLs below are the public ones) |
| Audiokinetic Wwise | 2025.1.12 (the current "edge" library). 2026.1.3 is Beta 3; its notable features are listed where relevant. | https://www.audiokinetic.com/en/public-library/2025.1.12_9287/ |
| Valve Steam Audio | 4.8.1 (latest GitHub release; the C API docs carry a "2017-2023" copyright footer) | https://valvesoftware.github.io/steam-audio/doc/capi/ and https://github.com/ValveSoftware/steam-audio |

Legend: **UNVERIFIED** means I could not confirm the claim in an official page during this research. It may still be true.

Abbreviations:
- FS = FMOD Studio manual, `https://www.fmod.com/docs/2.03/studio/<page>`
- FE = FMOD Engine manual, `https://www.fmod.com/docs/2.03/api/<page>`
- WH = Wwise Help, `https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=<id>`
- WS = Wwise SDK, `...?source=SDK&id=<id>.html`
- SA = Steam Audio C API, `https://valvesoftware.github.io/steam-audio/doc/capi/<page>`

---

## 1. FMOD Studio + FMOD Engine 2.03

### 1.1 Authoring and data model
- **Events** are built from:
  - one timeline parameter sheet (at most one per event);
  - parameter sheets for user or built-in parameters;
  - action sheets, in concurrent or consecutive mode.
  Source: [FS authoring-events.html](https://www.fmod.com/docs/2.03/studio/authoring-events.html), [FS parameters-reference.html](https://www.fmod.com/docs/2.03/studio/parameters-reference.html).
- **Instruments.** Source: [FS instrument-reference.html](https://www.fmod.com/docs/2.03/studio/instrument-reference.html).
  - Types:
    - Single.
    - Multi, a playlist container that acts as random/sequence.
    - Event, for nested or referenced events.
    - Scatterer, which spawns with randomized time, volume, pitch and 3D position.
    - Programmer, where the game supplies the sound through a callback.
    - Command, which starts or stops events and snapshots and sets parameters.
    - Silence.
    - Snapshot.
    - Plug-in synths, such as Le Sound AudioMotors2, AudioRain, AudioWeather and AudioWind.
    - Haptics, driven by Meta Haptics Studio files.
  - Playlist modes: Shuffle (no immediate repeat), Randomize, and three Sequential modes (play, global and instance scope). Play percentages weight the random picks.
  - Per-instrument options:
    - async/sync playback, cut, loop and play count, start offset;
    - trigger conditions: parameter ranges and labels, event state, a probability, AND/OR logic;
    - polyphony and stealing;
    - trigger delay, or quantization to bar/beat under the event tempo.
- **Parameters.** Source: [FS parameters-reference.html](https://www.fmod.com/docs/2.03/studio/parameters-reference.html).
  - User parameter types: continuous, discrete, or labeled.
  - Scope: global or local.
  - Options: "hold value during playback", velocity (auto-ramp), read-only, and seek speed through the seek modulator.
  - Built-in parameters: Distance, Distance (Normalized), Direction, Elevation, Event Cone Angle, Event Orientation, Speed (Relative), Speed (Absolute).
- **Modulators:** Random, AHDSR, LFO (tempo-syncable), Sidechain, Spectral Sidechain, Seek and Autopitch. Source: [FS modulator-reference.html](https://www.fmod.com/docs/2.03/studio/modulator-reference.html).
- **Snapshots:** overriding or blending, with intensity, a priority stack and snapshot groups. Source: [FS mixing.html](https://www.fmod.com/docs/2.03/studio/mixing.html).
- **Dialogue and localization:** audio tables combined with programmer instruments, and per-locale banks. Source: [FE studio-guide.html](https://www.fmod.com/docs/2.03/api/studio-guide.html).
- **Not present as a separate container type:**
  - Switch and blend containers do not exist. They are expressed through parameter sheets, conditions and automation.
  - States do not exist. Labeled parameters serve that role.

### 1.2 Runtime voice management
- **Core channel model.** Source: [FE managing-resources-in-the-core-api.html](https://www.fmod.com/docs/2.03/api/managing-resources-in-the-core-api.html).
  - `System::init(maxchannels)` sets the virtual channel count, suggested at 256–1024. Exceeding it steals a channel permanently.
  - `System::setSoftwareChannels` sets the real (audible) count, typically 32–128.
  - Channels move between real and virtual by audibility and priority.
- **Studio event macros.** Source: [FS event-macro-controls-reference.html](https://www.fmod.com/docs/2.03/studio/event-macro-controls-reference.html).
  - Max Instances: 1–64 or unlimited.
  - Stealing modes: Oldest, Furthest, Quietest, Virtualize, None.
  - Cooldown: 0 ms to 60 s.
  - Priority: Lowest to Highest. Highest never virtualizes, even with vol0virtual.
  - Persistent flag, pitch, Doppler with a 0–500% scale, and min/max distance.
- **Bus instance limiting:** Max instances with Oldest, Quietest, Furthest or Off stealing ([FS mixing.html](https://www.fmod.com/docs/2.03/studio/mixing.html)).
- **Streaming.** Source: [FE managing-resources](https://www.fmod.com/docs/2.03/api/managing-resources-in-the-core-api.html).
  - `FMOD_CREATESTREAM` uses a file thread plus a stream decode thread.
  - Stream buffer size is set with `System::setStreamBufferSize`.
  - Async reads go through `FMOD_FILE_ASYNCREAD_CALLBACK`, which supports deferred, prioritized reads.
  - Loads can be made non-blocking with `FMOD_NONBLOCKING`.
- **Hardware decoders (AT9/XMA/Opus) pin their decoder for the life of the channel**, so virtualization does not free them. `FMOD_ADVANCEDSETTINGS` caps the number of decoders per codec (same page).

### 1.3 Mixing
Source for this section unless noted: [FS mixing.html](https://www.fmod.com/docs/2.03/studio/mixing.html).
- **Bus types:**
  - Group buses forming a submix hierarchy.
  - Return buses fed by Send effects.
  - VCAs that scale outside the routing graph.
  - Port buses for platform outputs. Port types: Music, Copyright Music, Voice, Controller Speaker, Personal, Vibration, Auxiliary, VR Vibration.
- **Snapshots:** overriding or blending (additive dB), intensity, a priority stack, and snapshot instruments for game-triggered mixes.
- **Side-chain and ducking:**
  - The Sidechain effect feeds Compressor sidechain inputs.
  - Sidechain and Spectral Sidechain modulators can drive any property.
  - Source: [FS effect-reference.html](https://www.fmod.com/docs/2.03/studio/effect-reference.html), [FS modulator-reference.html](https://www.fmod.com/docs/2.03/studio/modulator-reference.html).
- **Loudness:**
  - The Loudness Meter effect reports Integrated LUFS, range and true peak in dBTP. Its target is -24 to -12 LUFS, default -23.
  - It is auto-bypassed in builds without live update.
  - No runtime HDR or auto-loudness system is documented. Mix dynamics rely on compressor, limiter, Multiband Dynamics and snapshots.
- **Core-level control** ([FE advanced-core-api-topics.html](https://www.fmod.com/docs/2.03/api/advanced-core-api-topics.html)):
  - Sample-accurate DSP clock: `ChannelControl::getDSPClock` and `setDelay` with 64-bit clocks.
  - Fade points (`addFadePoint`).
  - `setVolumeRamp`.

### 1.4 DSP effects shipped
- **Studio effects** ([FS effect-reference.html](https://www.fmod.com/docs/2.03/studio/effect-reference.html)): 3-EQ, Channel Mix, Chorus, Compressor (sidechain-able), Convolution Reverb, Delay, Distortion, Flanger, Gain, Limiter, Loudness Meter, Multiband EQ (5 bands), Object Spatializer, Panner, Parametric EQ (legacy), Pitch Shifter (FFT-based), Reverb (algorithmic), Send, Sidechain, Spatializer, Transceiver (32 channels).
- **Core `FMOD_DSP_TYPE`** ([FE effects-reference.html](https://www.fmod.com/docs/2.03/api/effects-reference.html)):
  - Everything above, plus Echo, Fader, FFT (spectrum, RMS, spectral centroid; can run on hardware), IT Echo, IT Lowpass, Normalize, Oscillator, Return, Tremolo, ObjectPan, Pan.
  - Deprecated lowpass and highpass variants remain.
  - New in 2.03: **Multiband Dynamics**, a 3-band effect with upward/downward compression and expansion ([FE welcome-whats-new-203.html](https://www.fmod.com/docs/2.03/api/welcome-whats-new-203.html)).
  - Removed in 2.03: envelope follower, VST, LADSPA, Winamp.
- **Convolution reverb limits** ([FS effect-reference](https://www.fmod.com/docs/2.03/studio/effect-reference.html)):
  - The impulse response must be 16-bit PCM at the output rate.
  - It cannot morph in real time; changing it means crossfading two instances.
  - Hardware convolution is available on XSX and PS5 since 2.02.xx ([FE what's new 2.03](https://www.fmod.com/docs/2.03/api/welcome-whats-new-203.html)).

### 1.5 Spatialization and environment
Source for this section unless noted: [FE spatializing-sounds-in-the-core-api.html](https://www.fmod.com/docs/2.03/api/spatializing-sounds-in-the-core-api.html).
- **Panning and attenuation:**
  - Rolloff curves: inverse (default), inverse tapered, linear, linear-squared, custom curve or callback.
  - `set3DSpread`, and `set3DLevel` to morph between 2D and 3D.
  - Height blend on the pan DSP.
  - Studio Spatializer: envelopment, 2D/3D mix, LFE send, min/max distance.
- **Doppler:** Global settings through `System::set3DSettings`. Studio exposes a per-event Doppler toggle and scale.
- **Multiple listeners:**
  - With more than one listener, Doppler is disabled and audio is panned mono to the middle.
  - Audibility uses the nearest listener.
- **Occlusion:** A raycast geometry engine (`System::createGeometry`, `Geometry::addPolygon`) occludes direct sound and can confine reverb ([FE advanced-core-api-topics.html](https://www.fmod.com/docs/2.03/api/advanced-core-api-topics.html)).
- **Reverb zones:**
  - `System::createReverb3D` creates spherical zones that morph into a single reverb from the listener position.
  - Up to 4 global reverb instances.
- **Object-based output:**
  - `FMOD_DSP_TYPE_OBJECTPAN` and the Object Spatializer send to WinSonic (Windows, Xbox), PS5 AudioOut, PS4 Audio3D and Apple PHASE.
  - When object voices run out, it falls back to the channel mix.
  - Nothing can be processed after the object panner.
- **Not in FMOD itself:**
  - Native HRTF, rooms/portals, diffraction and propagation are absent.
  - Binaural rendering comes from plug-ins: Resonance Audio (with first-order ambisonics through its Soundfield plug-in), Oculus/Meta, and Steam Audio.
- **Air absorption:** No built-in model. Users do it with automation or a plug-in. **UNVERIFIED** as a negative claim (no doc states its absence).

### 1.6 Music and interactive music
Source: [FS authoring-events.html](https://www.fmod.com/docs/2.03/studio/authoring-events.html).
- **Timeline logic markers:**
  - destination markers and regions;
  - loop regions;
  - magnet regions;
  - transition markers and regions, each with optional transition timelines;
  - sustain points (`keyOff`);
  - tempo markers (default 120 BPM, 4/4).
- **Transition rules:**
  - Quantization applies to transition and magnet regions.
  - Offset modes: None, Relative (bar-preserving), Inverted.
  - When several markers qualify, the topmost wins.
- **Stingers and stems:**
  - Stingers are built from command instruments or event instruments under quantized triggers. The manual does not use the word "stinger."
  - Stems are layered audio tracks automated by parameters.
- **Beat sync callbacks:** `TIMELINE_MARKER` and `TIMELINE_BEAT` ([FE studio-guide.html](https://www.fmod.com/docs/2.03/api/studio-guide.html)).

### 1.7 Asset pipeline and optimization
- **Banks.** Source: [FS getting-events-into-your-game.html](https://www.fmod.com/docs/2.03/studio/getting-events-into-your-game.html).
  - The master bank holds the mixer and must stay loaded.
  - The `.strings.bank` holds paths and GUIDs.
  - Events are assigned to banks manually.
  - Build split options: metadata+assets in one bank; separate `.assets.bank`; or a further split into `.streams.bank`.
  - Per-platform builds, with 4 KB alignment available for binary patching.
- **Recommended encoders per platform** (same page):

  | Platform | Encoder |
  |---|---|
  | Desktop | Vorbis |
  | PS5 | Opus |
  | PS4 | AT9 |
  | Xbox Series X\|S | Opus |
  | Xbox One | XMA |
  | Switch / mobile | FADPCM |

  Windows CPU benchmark: Vorbis about 6.9%, FADPCM about 3.1%, PCM about 1.6% for 64 voices ([FE platforms-win.html](https://www.fmod.com/docs/2.03/api/platforms-win.html)).
- **Per-asset overrides.** Source: [FS managing-assets.html](https://www.fmod.com/docs/2.03/studio/managing-assets.html).
  - Format, quality, and sample rate (Custom, Optimized for Size, or Preserved).
  - Loading mode: Compressed, Decompressed, or Streaming. Assets of 10 s or longer stream by default.
- **Runtime loading.** Source: [FE studio-guide.html](https://www.fmod.com/docs/2.03/api/studio-guide.html).
  - Bank loads can be sync or async (`LOAD_BANK_NONBLOCKING`).
  - Sample data loads are reference counted (`loadSampleData`) and asynchronous.
  - Recently used samples go to an idle pool (default 256 KB).
- **Memory:** `Memory_Initialize` takes a fixed pool or custom allocators. `FMOD_LOWMEM` and `Memory_GetStats` help reduce and size usage ([FE managing-resources](https://www.fmod.com/docs/2.03/api/managing-resources-in-the-core-api.html)).
- **Threading:** Studio uses an async command buffer processed by a Studio update thread. `FMOD_STUDIO_INIT_SYNCHRONOUS_UPDATE` is optional ([FE studio-guide](https://www.fmod.com/docs/2.03/api/studio-guide.html)).
- **Extensibility:** Plug-in APIs exist for DSP, codec and output ([FE advanced-core-api-topics](https://www.fmod.com/docs/2.03/api/advanced-core-api-topics.html)).

### 1.8 Tooling
Source: [FS profiling.html](https://www.fmod.com/docs/2.03/studio/profiling.html).
- **Live Update** connects Studio to the running game for live editing.
- **Profiler sessions** record:
  - CPU (mixer and update), memory (data and samples), and file I/O (sample, stream, bank);
  - levels (peak and RMS), voices including virtual, and instance counts;
  - per-instance lifespans with 3D attributes;
  - snapshot intensity;
  - a 3D view.
- **API capture and replay.** "Simulate" mode re-runs the captured API calls against the edited project without rebuilding banks.
- **Sandbox** for auditioning.
- **Scripting:** a JS scripting API and a scripting terminal. A Reaper integration is documented (FS TOC).
- **Standalone Core profiler tool:** **UNVERIFIED** in this pass. The Studio profiler page does not mention it.

### 1.9 Output
- **Speaker modes:** RAW, MONO, STEREO, QUAD, SURROUND (5.0), 5.1, 7.1, 7.1.4 ([FE core-api-common.html](https://www.fmod.com/docs/2.03/api/core-api-common.html)).
- **7.1.4 support:** needs WinSonic on Windows or PHASE on iOS. Other platforms fold down to 7.1 ([FE spatializing](https://www.fmod.com/docs/2.03/api/spatializing-sounds-in-the-core-api.html)).
- **Windows backends:** WASAPI (default), WinSonic (objects, Music and Passthrough ports), ASIO (not available on ARM64) ([FE platforms-win.html](https://www.fmod.com/docs/2.03/api/platforms-win.html)).
- **Platforms:** Windows, Mac, Linux, iOS, Android, OpenHarmony, UWP, HTML5. Consoles are covered in separate NDA docs ([FE platforms.html](https://www.fmod.com/docs/2.03/api/platforms.html)).
- **New in 2.03:** a Passthrough port that bypasses binauralization, and a VR Vibration port for PS VR2 Sense ([FE what's new 2.03](https://www.fmod.com/docs/2.03/api/welcome-whats-new-203.html)).

---

## 2. Audiokinetic Wwise 2025.1

### 2.1 Authoring and data model
- **Containers hierarchy.** In 2025.1 the Actor-Mixer and Interactive Music hierarchies were merged into "Containers", and the Actor-Mixer became the "Property Container" ([WS whatsnew_2025_1_new_features](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=whatsnew_2025_1_new_features.html)).
  - Object types ([WH building_actor_mixer_hierarchy_building_actor_mixer_hierarchy](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=building_actor_mixer_hierarchy_building_actor_mixer_hierarchy)):
    - Sound SFX and Sound Voice.
    - **Random**, **Sequence**, **Blend** (blend tracks with RTPC crossfades) and **Switch** containers.
    - Property Containers, Virtual Folders, Work Units.
  - In 2026.1 (beta), "Segment" becomes a shared timeline object for both sound and music ([WS whatsnew_2026_1_new_features](https://www.audiokinetic.com/en/public-library/2026.1.3_9276/?source=SDK&id=whatsnew_2026_1_new_features.html)).
- **Events** are action-based: Play, Stop, Pause, Mute, Set State and so on.
- **Dialogue Events** pick a line by matching argument paths. **External Sources** bind files at runtime ([WH glossary](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=glossary)).
- **Game Syncs** (same glossary):
  - **States**: global, with transition-time interpolation.
  - **Switches**: per game object.
  - **RTPCs**: Game Parameters mapped to properties with curves; they can also drive switches.
  - **Triggers**: launch stingers.
  - **Arguments**: used by dialogue.
- **Attenuation ShareSets** have curves for distance-driven volume, aux sends, LPF/HPF, spread, focus, and obstruction/occlusion/diffraction/transmission percentage ([WH defining_attenuation_curves_for_various_object_properties](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=defining_attenuation_curves_for_various_object_properties)).
- **Mixing snapshots** are expressed as **States on busses** (state-driven property offsets), not as a separate snapshot object ([WH working_with_states](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=working_with_states)).

### 2.2 Runtime voice management
Source for the main controls: [WH advanced_settings_tab_actor_mixer_objects](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=advanced_settings_tab_actor_mixer_objects).
- **Playback Limit**, per object or per bus:
  - Range 1–1000, default 50.
  - Scope: per Game object or Global.
  - When the limit is reached: Kill voice (with a short fade), or Use virtual voice settings.
  - On equal priority: Discard oldest or Discard newest.
  - Can be inherited from the parent or overridden ("Ignore Parent").
- **Priority** applies to playback and to voice selection. It can be offset by distance ([WH managing_priority](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=managing_priority)).
- **Volume Threshold** is set at project level. Voices below it take their virtual voice behavior.
- **Virtual voice behavior:** Continue to play, Kill voice, Send to virtual voice, or Kill if finite else virtual.
- **Return to physical voice:** Play from beginning, Play from elapsed time (not sample accurate), or Resume.
- **Event Limiting** was added in 2025.1 ([WS whatsnew 2025.1](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=whatsnew_2025_1_new_features.html)).
- **Streaming:**
  - Per-sound Stream flag, with **Zero Latency**: a prefetch head of the file kept in memory ([WH defining_playback_behavior_for_objects](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=defining_playback_behavior_for_objects)).
  - The Stream Manager I/O pool is set by `AkDeviceSettings::uIOMemorySize`, default 8 MB ([WS goingfurther_optimizingmempools](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=goingfurther_optimizingmempools.html)).
- **Memory:**
  - Memory arenas with `uMemReservedLimit`.
  - Out-of-memory has graceful outcomes: a bank load fails, a transition is skipped, or a lower-priority playback is stopped to make room (same page).

### 2.3 Mixing
- **Bus hierarchy** ([WH building_structure_of_output_busses](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=building_structure_of_output_busses)):
  - Main Audio Bus, Audio Busses and Auxiliary Busses.
  - **Secondary bus hierarchies** for other outputs: controller speaker, chat headset, DVR-bypass. These are duplicated per player through listener associations.
- **Aux sends** are user-defined (static) or game-defined (per game object through the API) ([WH glossary](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=glossary)).
- **Auto-ducking** is bus-to-bus, with a maximum ducking volume and recovery time ([WH audio_bus_property_editor](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=audio_bus_property_editor)).
- **Sidechaining** arrived in 2025.1 with Sidechain Mixes and the Sidechain Send/Receive effects ([WS whatsnew 2025.1](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=whatsnew_2025_1_new_features.html)).
- **HDR audio:**
  - It is a runtime system. Each HDR bus keeps a window positioned by the loudest sound, with a width equal to the volume threshold.
  - Controls: threshold, ratio and ballistics. Quieter sounds are ducked and can be culled.
  - Sources: [WH setting_dynamics_of_hdr](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=setting_dynamics_of_hdr), [WH glossary](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=glossary).
  - Ducking, HDR and voice adjustments are not available on aux busses ([WH building_structure_of_output_busses](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=building_structure_of_output_busses)).
- **Loudness normalization and make-up gain** are available per source or bus ([WH audio_bus_property_editor](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=audio_bus_property_editor)).
- **Mastering Suite** sits on the final device effect slot: Parametric EQ, Multiband Compressor, Master Volume and Limiter. ShareSets cover Headphones, HomeCinema, NightMode, SoundBar, TV and others, up to 7.1.4 ([WH mastering_suite_plug_in](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=mastering_suite_plug_in)).
- **Mixing Desk** and Mixing Sessions, plus control-surface support ([WH glossary](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=glossary)).

### 2.4 DSP effects shipped
Source: [WH effects](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=effects) and its child pages.
- **Effect plug-ins:** 3D Audio Bed Mixer, AK Channel Router, AK Convolution Reverb, AK Custom Panner, Compressor, Delay, Expander, Flanger, Gain, Guitar Distortion, Harmonizer, Matrix Reverb, Meter, Multiband Meter, Parametric EQ, Peak Limiter, Pitch Shifter, Recorder, Recorder (ADM, experimental), **Reflect** (early reflections), RoomVerb, Sidechain Send, Sidechain Receive, Stereo Delay, Tempest 3D AudioTech (PS5), Time Stretch, Tremolo, plus VST3 hosting in authoring.
- **Audio Device effects:** Mastering Suite.
- **Source plug-ins:** Audio Input, AK ASIO Input, External Source, Silence, Sine, Tone Generator, Synth One, SoundSeed Air Wind, SoundSeed Air Woosh, SoundSeed Grain, Impacter, Motion, Haptic Clip Player ([WH source_plug_ins](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=source_plug_ins)).
- **Certified partner plug-ins** include McDSP, Meta XR Audio, ReadSpeaker and GME voice chat (TOC of [WH effects](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=effects)).
- **Removed in 2026.1 (beta):** the Resonance Audio and Auro-3D plug-ins are being sunset ([WS whatsnew 2026.1](https://www.audiokinetic.com/en/public-library/2026.1.3_9276/?source=SDK&id=whatsnew_2026_1_new_features.html)).

### 2.5 Spatialization and environment
- **Positioning:**
  - Listener-relative routing, 3D spatialization (position or position+orientation), speaker panning, and 3D-positioned busses.
  - Attenuation curves, spread and focus, cones.
  - **Radial emitters** (inner/outer radius drives spread) ([WS spatial_audio_radial_emitters](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio_radial_emitters.html)).
- **Ambisonics:** first to fifth order busses. Ambisonic beds can be used alongside Audio Objects ([WH ambisonics_vs_audio_objects](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=ambisonics_vs_audio_objects)).
- **HRTF:** none built in. "No software Object binauralizer Effects are distributed with Wwise" (same page). Binaural rendering comes from the platform (Windows Sonic, Apple Spatial Audio, Tempest on PS5) or from partners (Meta XR Audio, Steam Audio for Wwise).
- **Doppler:** no built-in Doppler. The documented best practice is an RTPC on pitch driven by a game-computed relative speed ([WH rtpc_tips_best_practices](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=rtpc_tips_best_practices)).
- **Obstruction and occlusion:**
  - Game-supplied values (0–100%) map to project-wide curves for volume, LPF and HPF.
  - These can be replaced by Acoustics diffraction and transmission ([WS spatial_audio_concepts](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio_concepts.html)).
- **Wwise Acoustics (Spatial Audio) module**, a separate C++ library ([WS spatial_audio](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio.html)):
  - **Rooms and Portals:**
    - Room reverb is driven by game-defined aux sends.
    - Portal diffraction, transmission through walls, and **room coupling** (reverb of one room feeding the adjacent room).
    - Adjacent-room bleed, room containment priority, and room culling (2026.1).
    - Sources: [WS spatial_audio_roomsportals_apioverview](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio_roomsportals_apioverview.html), [WS spatial_audio_concepts](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio_concepts.html).
  - **Reverb Zones:** rooms without portals, with a parent room and a fuzzy transition region ([WS spatial_audio_roomsportals_reverbzones](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio_roomsportals_reverbzones.html)).
  - **Geometry API** ([WS spatial_audio_apigeometry_diffract](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio_apigeometry_diffract.html)):
    - Triangles with acoustic surfaces carrying absorption textures and a transmission loss.
    - Edge diffraction on the direct path and on reflections. It can replace game raycasts for obstruction.
    - Cost grows with geometry, so Audiokinetic recommends combining it with rooms and portals.
  - **Reflect plug-in:**
    - Image-source early reflections computed from geometry, rendered as a multi-tap filtered delay on an aux bus.
    - Acoustic textures and diffraction curves.
    - Source: [WH wwise_reflect_plug_in_effect](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=wwise_reflect_plug_in_effect).
  - **2025.1 additions:** dual-shelf filter, emitter clustering (experimental), dynamic load balancing, room distance behavior.
  - **2026.1 beta:** revised diffraction engine (experimental), reflection search-effort control.
  - Sources for these additions: [WS whatsnew 2025.1](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=whatsnew_2025_1_new_features.html), [2026.1](https://www.audiokinetic.com/en/public-library/2026.1.3_9276/?source=SDK&id=whatsnew_2026_1_new_features.html).
  - **Limitation:** Spatial Audio supports only one top-level listener ([WS spatial_audio](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=spatial_audio.html)).
- **Air absorption:** no physical model. Distance-driven LPF/HPF curves in attenuation are used instead.
- **Baked propagation:** not offered. Acoustics is runtime-geometric. **UNVERIFIED** as a negative claim.

### 2.6 Music and interactive music
- **Objects:**
  - Music Segment (multi-track) and Music Track (including Switch Music Tracks).
  - Music Playlist Container and Music Switch Container.
  - Entry and exit cues, custom cues, and pre-entry/post-exit regions.
  - Sources: [WH building_interactive_music_hierarchy_types_of_containers](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=building_interactive_music_hierarchy_types_of_containers), [WH glossary](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=glossary).
- **Transition matrix:** source/destination rules per pair ([WH setting_source_and_destination_properties](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=setting_source_and_destination_properties)).
  - Exit at: Immediate, Next Grid, Next Bar, Next Beat, Next Cue, Next Custom Cue (with name match), or Exit Cue.
  - Optional post-exit playback and fades.
  - Destination options: jump-to playlist item, sync to entry cue or same time, random custom cue.
  - Optional transition segments.
- **Stingers:** Triggers map to segments, with sync points and "don't repeat" timing ([WH using_stingers](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=using_stingers)).
- **MIDI:** MIDI tracks drive Synth One or sampler instruments ([WH working_with_midi](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=working_with_midi)).
- **Beat/bar/cue callbacks** are delivered to the game through `AkMusicSyncCallbackInfo` (SDK struct index).
- **Music voices** return from virtual from elapsed time ([WH advanced settings](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=advanced_settings_tab_actor_mixer_objects)).

### 2.7 Asset pipeline and optimization
- **SoundBanks** ([WH managing_soundbanks](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=managing_soundbanks)):
  - Init.bnk holds busses, states, switches, RTPCs and devices, and must be loaded first.
  - Content banks hold event and structure data and/or media.
  - All platforms are generated together.
- **Bank generation options** ([WH defining_soundbank_settings_for_project](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=defining_soundbank_settings_for_project)):
  - A header file mapping names to IDs.
  - Content files and SoundbanksInfo (XML/JSON) with max attenuation and estimated duration per event.
  - Loose/streamed media copy, a max bank size check, and pre/post generation steps.
  - Auto-defined SoundBanks.
- **File Packager** builds `.pck` packages ([WH managing_file_packages](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=managing_file_packages)).
- **DLC** support ([WH planning_dlc](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=planning_dlc)).
- **Conversion Settings ShareSets** ([WH creating_audio_conversion_settings_sharesets](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=creating_audio_conversion_settings_sharesets)):
  - Per platform: channels, sample rate, format and quality, plus SRC quality, DC-offset removal, dither and upmix.
  - Inherited down the hierarchy.
  - Software codecs: PCM, ADPCM, Vorbis, WEM Opus, all with full multichannel support.
  - Hardware codecs are platform-specific, such as XMA, ATRAC9 and hardware Opus. Their details are behind the NDA section of the docs.
  - Audiokinetic's codec guide gives per-platform decode-count tables ([official blog](https://www.audiokinetic.com/en/blog/a-guide-for-choosing-the-right-codec/)).
- **Import formats:** WAV and AMB (ambisonics), plus experimental **ADM** (Dolby Atmos master) with beds and dynamic objects ([WH what_media_files_are_supported](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=what_media_files_are_supported)).
- **Media Pool** (2025.1): a sound-library browser with metadata search and ML "Similar Sound Search" ([WS whatsnew 2025.1](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=whatsnew_2025_1_new_features.html)).
- **Prefetch and zero-latency streaming**, I/O pool and memory arenas: see 2.2.

### 2.8 Tooling
- **Profiler layout** ([WH exploring_game_profiling_views](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=exploring_game_profiling_views)):
  - **Capture Log** with a catalogued error list, including voice starvation, virtual voice limits and the 3D object limit.
  - **Advanced Profiler**: CPU, memory per category, bandwidth, voices and busses.
  - **Performance Monitor**.
- **Other views** ([WH analyzing_voices_voice_inspector](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=analyzing_voices_voice_inspector), [WH game_object_profiler_game_object_3d_viewer](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=game_object_profiler_game_object_3d_viewer)):
  - **Voice Inspector and Voices Graph**, which explain the volume contributions to each voice.
  - **Game Object 3D Viewer**, showing rooms, portals, diffraction and reflection paths.
  - **Audio Object 3D Viewer**.
- **Remote connection** to a PC or console, with editing while profiling ([WH connecting_to_local_remote_pc_or_game_console](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=connecting_to_local_remote_pc_or_game_console)).
- **Soundcaster** simulations ([WH creating_simulations](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=creating_simulations)).
- **Replay (2026.1 beta):** play back captured audio, or re-simulate the captured API calls against the current project.
- **Wwise Authoring API (WAAPI)** and WAQL for tool automation. Only an index-level mention was confirmed; the API pages were not read in depth.

### 2.9 Output
- **Windows** ([WS audio_output_platform](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=SDK&id=audio_output_platform.html)):
  - 48 kHz default, using the system device configuration.
  - With "Allow 3D Audio", the output is a **7.1.4 main mix, a stereo passthrough mix and discrete Audio Objects** (Windows Sonic / Dolby Atmos).
- **Mac and iOS:** Apple Spatial Audio.
- **Android:** spatial audio requires 5.1.4 or 7.1.4.
- **Channel configurations:** up to 7.1.4 and beyond (9.1, 10.1 and so on) on import, plus ambisonics up to 5th order ([WH what_media_files_are_supported](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=what_media_files_are_supported)).
- **Object-based pipeline:** Audio Objects are promoted to System Audio Objects at the device. The 3D Audio Bed Mixer controls the object count ([WH glossary](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=glossary), [WH ambisonics_vs_audio_objects](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=ambisonics_vs_audio_objects)).
- **Audio Device plug-ins:** System, Motion, AK ASIO Output, and secondary outputs (controller speaker, etc.) ([WH audio_device_plugins](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=audio_device_plugins)).
- **Motion and haptics:**
  - Motion source plug-in with rumble and generic haptics actuator configurations.
  - Haptic Clip Player.
  - Motion output device.
  - Source: [WH design_considerations_for_rumble_and_advanced_haptics](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=design_considerations_for_rumble_and_advanced_haptics).

---

## 3. Valve Steam Audio 4.8.1

Steam Audio is a spatial-acoustics SDK, not an authoring tool. It has no events, mixer, banks or music system. It plugs into Unity, Unreal 4.27+, FMOD Studio 2.0+ and Wwise 2023.1+.

- **License:** Apache-2.0.
- **Platforms:** Windows x86/x64, Linux x86/x64, macOS, Android (armv7/arm64/x86/x64), iOS.
- Source: [GitHub README](https://github.com/ValveSoftware/steam-audio).

### 3.1 Authoring and data model
- Not applicable. There is a C API (`phonon.h`) built from:
  - reference-counted objects (`IPLContext`, `IPLHRTF`, effects, `IPLScene`, `IPLSimulator`, `IPLSource`, `IPLProbeBatch`);
  - deinterleaved float buffers;
  - a custom allocator and a selectable SIMD level.
- Source: [SA guide.html](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html).
- Effects support tail queries (`GetTail`/`GetTailSize`) since 4.6.0 ([SA panning-effect.html](https://valvesoftware.github.io/steam-audio/doc/capi/panning-effect.html), [releases](https://github.com/ValveSoftware/steam-audio/releases)).

### 3.2 Runtime voice management
- None. `maxNumSources` caps simulated sources for reflections, and there is a TAN max-sources override ([SA guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html), [Unity settings](https://valvesoftware.github.io/steam-audio/doc/unity/settings.html)).

### 3.3 Mixing
- None, apart from `IPLReflectionMixer`, which sums reflection sound fields from all sources into one. It is optional for convolution and required for TAN ([SA reflections-effect.html](https://valvesoftware.github.io/steam-audio/doc/capi/reflections-effect.html)).

### 3.4 DSP effects shipped
All of these are spatial effects:
- Binaural.
- Panning: mono to a speaker layout.
- Virtual Surround: a speaker mix rendered binaurally, also usable as a cheap binaural mode.
- Ambisonics Encode, Panning, Binaural, Rotation and Decode.
- Direct: distance attenuation, 3-band air absorption, directivity, occlusion, and transmission (frequency-independent or frequency-dependent).
- Reflection: Convolution, Parametric (FDN), Hybrid, or TAN on the GPU.
- Path.

Sources: [SA guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html), [direct-effect](https://valvesoftware.github.io/steam-audio/doc/capi/direct-effect.html), [reflections-effect](https://valvesoftware.github.io/steam-audio/doc/capi/reflections-effect.html), [virtual-surround-effect](https://valvesoftware.github.io/steam-audio/doc/capi/virtual-surround-effect.html).

### 3.5 Spatialization and environment
- **HRTF** ([SA hrtf.html](https://valvesoftware.github.io/steam-audio/doc/capi/hrtf.html), [guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html)):
  - A built-in default HRTF, or **SOFA** loaded from a file or memory.
  - Only the SimpleFreeFieldHRIR convention is supported, with restrictions.
  - Normalization: None or RMS. A volume correction is available.
  - Interpolation: nearest or bilinear.
  - `spatialBlend` mixes spatialized and unspatialized audio.
- **Ambisonics** ([SA audio-buffers.html](https://valvesoftware.github.io/steam-audio/doc/capi/audio-buffers.html)):
  - Order N uses (N+1)² channels. N3D is the native format, with conversion to and from SN3D and FuMa.
  - Rotation can be world-locked or head-locked.
  - The maximum order is set by `maxOrder`. **UNVERIFIED:** no numeric cap is stated in the docs read.
- **Speaker layouts:** mono, stereo, quad, 5.1, 7.1, and custom. **There is no 7.1.4 preset** ([SA audio-buffers.html](https://valvesoftware.github.io/steam-audio/doc/capi/audio-buffers.html)).
- **Occlusion** ([SA simulation.html](https://valvesoftware.github.io/steam-audio/doc/capi/simulation.html)):
  - Raycast: a single ray.
  - Volumetric: a source sphere with sampled points, giving partial occlusion.
  - **Transmission** uses 3-band per-material values.
- **Materials:** 3-band absorption (400 Hz / 2.5 kHz / 15 kHz), scattering and 3-band transmission ([SA scene.html](https://valvesoftware.github.io/steam-audio/doc/capi/scene.html)).
- **Reflections and reverb** ([SA guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html), [Unity settings](https://valvesoftware.github.io/steam-audio/doc/unity/settings.html)):
  - Real-time ray-traced impulse responses, configured by rays, bounces, duration and ambisonic order.
  - **Baked** reflections stored in probes, for static sources or listener-centric reverb.
  - Source-space or listener-space reverb.
  - Hybrid crossover settings: transition time and overlap.
  - 4.7.0 added raw `IPLEnergyField`/`IPLImpulseResponse`/`IPLReconstructor` access and baked IR extraction ([releases](https://github.com/ValveSoftware/steam-audio/releases)).
- **Pathing** (propagation around corners) ([SA simulation.html](https://valvesoftware.github.io/steam-audio/doc/capi/simulation.html)):
  - Baked probe-to-probe visibility graph.
  - Runtime path search with optional validation against dynamic geometry and real-time alternate path finding.
  - Deviation models: UTD-based diffraction, or a callback.
  - Path directionality encoded as ambisonics.
- **Probes:** a uniform-floor generator. Probe batches are the unit of load, save and streaming ([SA guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html)).
- **Ray tracers:** Default (all platforms), Embree (x86 desktop), Radeon Rays (OpenCL CPU/GPU, Win64), or Custom callbacks with the lowest memory use ([SA scene.html](https://valvesoftware.github.io/steam-audio/doc/capi/scene.html)).
- **Dynamic geometry:** rigid-body instanced meshes, and serializable static meshes ([SA guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html)).
- **GPU:**
  - TrueAudio Next convolution.
  - Radeon Rays tracing.
  - AMD GPU compute-unit reservation, so audio work does not hurt frame rate.
  - Source: [Unity settings](https://valvesoftware.github.io/steam-audio/doc/unity/settings.html).
- **Not provided:**
  - Doppler (the host engine handles it).
  - Rooms/portals as an authoring abstraction (geometry and probes are used instead).

### 3.6 Music
Not applicable.

### 3.7 Asset pipeline
- Serialized scenes (`iplStaticMeshSave`/`Load`) and probe batches (`iplProbeBatchSave`/`Load`).
- Bake parameters: rays, bounces, duration, order, threads.
- Sources: [SA guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html), [Unity settings](https://valvesoftware.github.io/steam-audio/doc/unity/settings.html).

### 3.8 Tooling
- Validation mode with extra checks ([Unity settings](https://valvesoftware.github.io/steam-audio/doc/unity/settings.html)).
- Visualization and bake tools live in the Unity and Unreal integrations. No standalone profiler is documented.

### 3.9 Output
- Stereo binaural, speaker layouts up to 7.1 or custom, or an ambisonic sound field handed to the host.
- No device backends of its own.

---

## 4. Cross-product table

Y = yes, N = no, P = partial, or available through a plug-in, partner or host.

| Feature | FMOD 2.03 | Wwise 2025.1 | Steam Audio 4.8 |
|---|---|---|---|
| Event abstraction decoupled from code | Y | Y | N |
| Random / sequence containers | Y (Multi/Scatterer playlists) | Y | N |
| Switch container | P (parameter sheets + conditions) | Y | N |
| Blend container / parameter crossfade | Y (parameter sheets + automation) | Y | N |
| Global states | P (global labeled parameters) | Y (States) | N |
| Per-object parameters (RTPC) with curves | Y | Y | N |
| Modulators (LFO / ADSR / random / sidechain) | Y | Y (LFO, Envelope, Time modulators as RTPC inputs; [WH modulator_editor](https://www.audiokinetic.com/en/public-library/2025.1.12_9287/?source=Help&id=modulator_editor)) | N |
| Mix snapshots | Y (overriding/blending, intensity) | Y (States on busses) | N |
| Virtual voices with audibility-based promotion | Y | Y (threshold + behaviors) | N |
| Instance limits and stealing modes | Y (event and bus) | Y (object, bus, event; game-object or global scope) | N |
| Priority system | Y (5 levels) | Y (numeric, distance offset) | N |
| Streaming with prefetch / zero latency | P (streams; prefetch explicit only via loading modes) | Y (Zero Latency prefetch) | N |
| Bus hierarchy, sends/returns, VCAs | Y | Y (no VCA object; States/RTPC on busses) | N |
| Side-chain / auto-ducking | Y | Y (auto-ducking; sidechain since 2025.1) | N |
| HDR runtime mixing | N | Y | N |
| Loudness metering / normalization | P (meter only) | Y (meters + normalization + Mastering Suite) | N |
| Convolution reverb | Y (+ hardware on PS5/XSX) | Y | Y (simulated IRs) |
| Algorithmic reverb | Y | Y (RoomVerb, Matrix) | Y (parametric FDN) |
| Built-in HRTF | N (plug-ins) | N (platform or partner) | Y (+ SOFA) |
| Ambisonics bus/order | P (1st order via Resonance plug-in) | Y (1st–5th) | Y (order configurable) |
| Distance rolloff curves | Y | Y | Y (model + callback) |
| Doppler | Y | P (RTPC pattern) | N |
| Air absorption | N | P (curves) | Y (3-band physical) |
| Directivity / cones | Y (cone angle parameter) | Y (cones) | Y (dipole pattern) |
| Occlusion by geometry | Y (raycast geometry) | Y (Acoustics transmission) | Y (raycast + volumetric) |
| Obstruction / diffraction | N | Y (portal + geometric edge diffraction) | Y (pathing with UTD deviation) |
| Rooms / portals / room coupling | N | Y | N (probes/geometry instead) |
| Reverb zones | Y (sphere morph) | Y (Reverb Zones) | P (baked probes) |
| Geometric early reflections | N | Y (Reflect, image sources) | Y (ray-traced) |
| Baked propagation / probes | N | N (**UNVERIFIED** negative) | Y |
| GPU acceleration | N | N | Y (Radeon Rays, TAN) |
| Interactive music transitions with quantization | Y | Y (transition matrix) | N |
| Stingers / triggers | P (command instruments) | Y | N |
| Beat/bar callbacks | Y | Y | N |
| MIDI-driven music | N (**UNVERIFIED**) | Y | N |
| Banks with metadata/media split | Y | Y (Init + content + loose media + packages) | N |
| Per-platform codec settings | Y (Vorbis/FADPCM/Opus/XMA/AT9/PCM) | Y (PCM/ADPCM/Vorbis/Opus + hardware codecs) | N |
| Fixed memory pools / custom allocators | Y | Y (arenas, limits) | Y (allocator callbacks) |
| Async bank loading | Y | Y | P (probe batches) |
| Live profiler with remote connect | Y | Y | N |
| API capture / replay | Y | Y (Replay in 2026.1 beta) | N |
| Per-voice "why is this quiet" inspector | P (lifespans) | Y (Voice Inspector) | N |
| 3D debug view of acoustics | P (3D view) | Y (Game Object 3D Viewer) | P (engine integrations) |
| 7.1.4 output | Y (WinSonic/PHASE) | Y | N (custom layout only) |
| Object-based output (Windows Sonic/Atmos/PS5) | Y | Y (+ 3D Audio Bed Mixer) | N |
| Passthrough (non-binauralized) mix | Y (2.03) | Y | N |
| Secondary outputs (controller, headset) | Y (ports) | Y (secondary bus hierarchies) | N |
| Haptics routed as audio | Y (Haptics instrument, VR Vibration port) | Y (Motion, Haptic Clip Player) | N |
| ADM / Atmos master import | N (**UNVERIFIED**) | P (experimental) | N |
| Plug-in SDK | Y (DSP, codec, output) | Y | N (it is the plug-in) |
| Open source / license | Proprietary | Proprietary | Apache-2.0 |

---

## 5. Features that most differentiate AAA quality

1. **Audibility-driven virtual voices plus hierarchical limiting with priority.** Hundreds or thousands of logical sounds run on a CPU budget of tens of real voices without audible pops or lost loops. This is the backbone of any MMO-scale scene.
2. **Per-voice parameter curves over game state (RTPC), plus global states and snapshots.** Sound designers own behavior without code changes, and the mix reacts to gameplay context (combat, menus, dialogue).
3. **HDR or loudness-managed dynamic mixing, with auto-ducking and sidechain.** It keeps critical cues (dialogue, threats) intelligible in dense scenes. Wwise's HDR window also culls inaudible voices, saving CPU.
4. **Propagation modeling: rooms/portals, diffraction, transmission and room coupling.** Players hear sound arrive from the true path (a doorway, not through the wall). This is the most noticed "next-gen" spatial cue and is gameplay-relevant.
5. **Geometric early reflections plus convolution or hybrid reverb, with baked probes for static content.** It gives a sense of space and material, and baking makes physical accuracy affordable at runtime.
6. **HRTF binaural rendering with SOFA, plus an ambisonic intermediate bus.** Headphone players are the majority, and ambisonic beds make the cost per listener constant regardless of source count.
7. **Object-based output (Windows Sonic / Atmos / PS5 Tempest) with a 7.1.4 bed and a passthrough mix.** Platform-certified home-theater output, with clean non-diegetic UI and music.
8. **Interactive music with quantized transitions, stingers and beat callbacks.** Musical continuity across gameplay states is a hallmark of AAA scoring.
9. **Banks with metadata/media split, streaming with zero-latency prefetch, and per-platform codecs and fixed pools.** Predictable memory and I/O, fast patching, and no first-play latency on streamed sounds.
10. **A live remote profiler with voice inspection and API capture/replay.** Mix and perf bugs are found and fixed on the target device, which cuts iteration time on a large project.

---

## 6. Unverified or not checked
- Steam Audio maximum ambisonic order: no numeric cap appears in the docs read.
- FMOD standalone Core Profiler tool; FMOD MIDI music; FMOD ADM import.
- Whether Wwise has any baked propagation. 2026.1 features are beta and may change.
- Console-specific details (XMA, AT9, Tempest specifics, hardware decode counts) sit behind NDA sections in both FMOD and Wwise docs. Only public summaries were seen.
- WAAPI and WAQL were confirmed only at index level.
