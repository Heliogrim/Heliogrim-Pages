# Work: Audio

**Systems** S38 · **Issues** [#118](https://github.com/Heliogrim/Heliogrim-Engine/issues/118) · **Track** C · **Milestone** M4 (milestones 1 and 2 of the design can run earlier)
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Audio](../topics/audio.md). This topic is the furthest along: an exploration and a design draft exist.

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Audio runtime design](../../architecture/audio-runtime-design.md) (draft, not approved) | Intent, goals, anti-goals, signal model with domain tags and commutativity, first-scope DSP node set, graph compilation and block-recorded command buffers, instances versus voices, scene integration as a `SceneSystem`, WASAPI device thread outside fibers, null device, media hooks, test plan, four milestones | Section 14: delay compensation, multi-listener, reorder of smoothed gains, graph asset location, device thread versus future scheduler. Builder check outcome not recorded. Not in the nav. |
| [Audio and DSP exploration](../../architecture/audio-dsp.md) | Research digest (middleware, tools, optimisation), owner corrections | Closed by the design once approved |
| Audio brainstorm memory (2026-11-03) | Owner decisions: own system, scene sound first, configurable rates incl. 96 kHz, block recording with cached sub-buffers, first scope includes one frequency-domain node, observability only as a hook, split into runtime, game-event integration, editor UI after the canvas | Nothing contradicting the plan |
| [Concurrency work](concurrency-fibers.md) W02.3 | `AffineThread` seam | Resolves design question "device thread versus scheduler": the device thread is an affine service, its callback never enters the scheduler |
| [Storage work](storage-streaming.md) | Residency manager | Bank streaming and the "media not ready" voice state |
| [Terrain work](terrain.md) S29 | `LayerVolume` | Reverb regions |
| [Volumetrics work](volumetrics-weather.md) S32 | Weather state | Wind and rain beds |
| [Vector UI work](vector-ui-uikit.md) S42 | Canvas | Graph editor UI waits for it |

## Architecture

- **Bundles** (from the design): `Engine.SFX` keeps importers and adds `Engine.SFX.Dsp` (signal model, nodes, compiler, command buffers), `Engine.SFX.Runtime` (instances, voices, buses, device interface, null device), `Support.Audio.Wasapi` (device thread), `Engine.SFX.Scene` (`AudioSceneSystem`), later `Editor.Audio` (graph composition, mixer view).
- **Provides**: scene sound, mixer banks, DSP graph, device output; audibility queries for gameplay.
- **Consumes**: `AffineThread` (S02), `WorldPosition` (S07), residency (S03), `LayerVolume` (S29), `WeatherState` (S32), bounds query service (S44), spans hook (S04), canvas (S42) for the editor.

## Code design

The design page holds the code design. Additions that the battle plan requires, to fold in during W38.0:

| Addition | Contract |
|---|---|
| Device thread as `AffineThread` client | The WASAPI event thread is created through the S02 seam; command and return queues stay lock-free; nothing in the callback touches the scheduler. |
| `MediaResidency` | The "resident only" hook binds to `ResidencyManager` class `Audio`; chunk requests go through `IoQueue`. |
| `ReverbRegionProvider` | Reads `activeVolume(WorldPosition)` from S29 and selects the bus send. |
| `WeatherBedProvider` | Reads `WeatherState` and drives wind and rain bed parameters. |
| `AudibilityQuery` | Uses the shared bounds and physics query services for occlusion; exposed to gameplay without DSP. |
| Observability hook | The per-block timing buffer becomes S04 counters once W04.2 exists. |

## Work chunks

### W38.0 Close the design: builder check, open questions, approval · design · ready

- **Goal**: run (or re-run) the builder check on the design page; answer section 14 with the battle-plan resolutions above; mark proposals as owner-approved or changed; state the bank-compiled versus live-mixing split (Q38.1); add the page to the nav; write the ADR placeholders for the two decisions already made (block recording, domain-tagged signal model).
- **Output**: approved `audio-runtime-design.md`; untracked plan for design milestones 1 and 2.
- **Questions**: Q38.1, Q38.2, Q38.3.

### W38.1 Implement design milestone 1 (offline core) · execute · after W38.0

- **Done when**: nodes, compiler with reordering, command buffers and pools, null device, all design section 12 tests pass.

### W38.2 Implement design milestone 2 (audible, WASAPI) · execute · after W38.1, W02.3

- **Done when**: a sine through the master is heard at 44.1, 48 and 96 kHz; device thread runs as an affine service.

### W38.3 Implement design milestone 3 (scene sound) · execute · after W38.2, W07.2

- **Done when**: a scene sound pans and fades with the camera; the null device golden-compares the same graph.

### W38.4 Implement design milestone 4 (full first DSP scope, banks, sends) · execute · after W38.3

### W38.5 Game-event and control integration design · design · after W38.3, W09.1

- **Goal**: the second project from the split: events, parameters, states, switches as reflected assets; control from gameplay and the editor.
- **Output**: `architecture/audio-events-design.md`; plan.
- **Questions**: Q38.4.

### W38.6 Implement events, reverb regions, weather beds, bank streaming · execute · after W38.5, W29.2, W32.2, W03.4

- **Done when**: a cave layer applies its reverb; a weather state changes wind and rain beds; banks stream through residency.

### W38.7 Editor audio UI design and implementation · design then execute · after W42.3, W43.2

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q38.2 | Constant-parameter nodes only are reorderable in the first version; optimiser passes that handle smoothed gains can be added later. |
| Q38.1 | Approved: one listener in milestone 1; the device thread outside the fiber scheduler (an affine thread with lock-free queues, as planned in Batch 1); graph data compiled per bank, with the caveat that live mixing and reaction must stay possible, so W38.0 states the split between what is compiled into a bank and what stays live; `AudioSceneSystem` as the third system in the game scene is explicitly encouraged. Multi-listener means several hearing points (split-screen, editor preview), not speaker layout, and stays a hook. The graph description is an asset; W38.0 settles only its granularity (own asset type, compiled into banks at cook). |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q38.1 | Approve the design's proposals as written (one listener in milestone 1, device thread outside fibers, graph as data compiled per bank, `AudioSceneSystem` third in `GameScene`)? | W38.0 | Approve; multi-listener stays a hook |
| Q38.2 | Reordering of nodes with smoothed (time-varying) gains: allowed, or only constant-parameter nodes reorder? | W38.0 | Constant-parameter nodes only in the first version |
| Q38.3 | Delay compensation across banks: in scope for milestone 4 or later? | W38.0 | Later, with a measured latency report in milestone 4 |
| Q38.4 | Event model: Wwise-style events, switches, states and RTPCs, or a smaller event plus parameter set? | W38.5 | Events plus parameters plus states; switches as a parameter kind |
