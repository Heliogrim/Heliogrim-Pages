# Work: Input v2

**Systems** S39 · **Issues** [#119](https://github.com/Heliogrim/Heliogrim-Engine/issues/119) · **Track** C · **Milestone** M2
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Input](../topics/input.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| `Engine.Input`, `Support.Input.Win32`, `Editor.UI.Service::InputService` | Event classes, drag and drop, a schedule stage, editor binding lists | Direct include of the Win32 backend is a layer violation; `InputService` becomes a context |
| Audio brainstorm memory | SDL3 likely dropped later for native drivers | Native Win32 input behind `Engine.Platform` (Q39.1) |
| [Input backends exploration](../../architecture/input-exploration.md) (W39.0) | SDL3 base plus native capability side channels (accepted); Windows numbers; per-platform gaps | SDL 3.4 upgrade; Apple main-thread pump; hardware end-to-end latency run |
| [Concurrency work](concurrency-fibers.md) | Platform pump as an affine thread | Events drained at the Input stage |
| [Editor workflows work](editor-workflows.md) S44, S54 | Gizmo capture contexts; recording for replay | Contexts and the recorder are defined here |
| [Vector UI work](vector-ui-uikit.md) S43 | Focus and hover layer | Pushes the UI context |
| [Reflection work](serialization-and-reflection.md) S09 | Reflected assets | Actions and contexts are assets |
| [Terrain work](terrain.md) | Brushes with pressure | `Axis3D` plus pressure value type |

## Architecture

- **Bundles**: `Engine.Input` extended with `Action`, `Context`, `Arbiter`, `Recorder`; raw backends move behind `Engine.Platform` (`Support.Input.Win32` registered, not included; SDL3 as the current backend). `Engine.Input.Schedule` keeps the stage.
- **Provides**: action values per consumer, context stack or set with consumption, recording and injection.
- **Consumes**: affine pump (S02), reflection (S09), uikit focus (S43), editor tools (S44), replay (S59), test driver (S54).

## Code design

| Type | Contract |
|---|---|
| `RawEvent` | Device-tagged event with timestamp: key, mouse, wheel, gamepad, pen (pressure, tilt, proximity), touch (fingers, gestures), text and IME. |
| `InputAction` | Asset: `{ name, ValueType { Bool, Axis1, Axis2, Axis3 }, modifiers, triggers }`; states `Started, Ongoing, Triggered, Completed, Cancelled`. |
| `Modifier` | Negate, swizzle, dead zone, smoothing, scale; pure functions on values. |
| `Trigger` | Tap, hold, chord, pulse; small state machines. |
| `InputContext` | Asset: `{ priority, mappings: raw → action, consumePolicy }`; pushed and removed at runtime by UI focus, editor viewport hover or capture, gizmo drag, gameplay. |
| `Arbiter` | Resolves per action across active contexts by priority; consumption is per action, so a text field eats typing while the gamepad still reaches gameplay. Stack or prioritised set per Q39.2. |
| `ActionStream` | Per-frame resolved action values delivered at the Input stage to consumers through subscription. |
| `Recorder` | Records raw events at the backend boundary and actions at the arbiter boundary with timestamps; `Injector` replays either. |
| `RemapPreset` | Per platform and per user; serialised with S01. |

Placement: `Engine.Input/{RawEvent,InputAction,Modifier,Trigger,InputContext,Arbiter,ActionStream,Recorder}`, `Engine.Platform/InputBackend.hpp` with `Support.Input.Win32` and the SDL backend registering. Tests: arbitration scenarios (text field versus camera), pen and touch through actions, recorded session replay to an identical action stream.

## Work chunks

### W39.1 Input v2 design · design · ready

- **Goal**: layers, actions, contexts, arbitration, assets, recording, the backend registration through `Engine.Platform`, migration of `InputService` and existing bindings.
- **Inputs**: `Engine.Input`, `Editor.UI.Service`, Enhanced Input and SDL3 models (verified landing pages), [input exploration](../../architecture/input-exploration.md) section 7 (capability sources, source timestamps and sample batches, own key enums, thread-safe intake, Apple main thread). The SDL 3.4.x upgrade is a prerequisite task in the W39.1 plan.
- **Output**: `architecture/input-v2-design.md`; plan.
- **Questions**: Q39.1, Q39.2.

### W39.2 Implement actions, contexts, arbiter and backend registration · execute · after W39.1

- **Done when**: editor, viewport, gizmo drag placeholder and a game scene coexist with correct consumption; typing never moves the camera; the layer violation is gone.

### W39.3 Implement gamepad, pen, touch and remap presets · execute · after W39.2

- **Done when**: a gamepad, a pen with pressure and a touch pinch drive actions through the same path.

### W39.4 Implement recorder and injector · execute · after W39.2

- **Done when**: a recorded editor session replays to the same action stream in a test.

### W39.0 Native backend spike · explore · done 2026-11-09

- **Goal**: compare SDL3 against native input backends per platform (Win32 raw input, macOS and iOS through the system frameworks, Wayland, optionally X11) on latency, device coverage (gamepad, pen, touch), event fidelity and maintenance cost; decide the backend strategy for full platform coverage (Q39.1).
- **Output**: [Input backends exploration](../../architecture/input-exploration.md) with numbers and the per-platform recommendation; W39.1 designs the backend interface against it.
- **Result (accepted 2026-11-09, [ADR-0011](../../adr/0011-input-backend-sdl3-base.md))**: SDL3 stays the base backend everywhere (window, pump, keyboard, gamepads, lifecycle), upgraded to 3.4.x first; native code enters as capability side channels where evidence shows a gain (Windows: raw mouse deltas in absolute mode, pen history, `WM_POINTER` touch and pinch; iPadOS: coalesced and predicted touches, Pencil squeeze; Wayland: tablet pads and gestures). Keyboard and relative mouse showed no SDL overhead on Windows (0.3 ms and 0.08 ms p50, injected input); full native backends would cost 15–30k lines per platform.

## Decisions (2026-11-09)

| ID | Decision |
|---|---|
| Q39.1 | Not simply SDL3. Spike the difference (W39.0) with the goal of native integration for Win32, iOS, macOS, Wayland and maybe X11, so the engine reaches full platform coverage without a middle layer where it does not pay off. **Resolved by W39.0 (2026-11-09)**: SDL3 (3.4.x) stays the base backend on every platform; native code only as capability side channels with evidence (Windows raw mouse in absolute mode, pen history, `WM_POINTER` touch now; iPadOS and Wayland with their ports; none on X11). See the [exploration](../../architecture/input-exploration.md) section 6 and the [ADR-0011](../../adr/0011-input-backend-sdl3-base.md). |
| Q39.2 | Prioritised set of contexts. Known downsides accepted: priorities form a shared namespace that must be named constants, not magic numbers (Q18.3 rule); a modal context must say explicitly that it consumes everything; debugging needs an inspector that lists the active contexts by priority. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q39.1 | Stay on SDL3 for raw input now and add native Win32 later, or go native in this system? | W39.1 | SDL3 now behind the backend interface; native later as its own chunk |
| Q39.2 | Contexts as a strict stack (top consumes first) or a prioritised set (Unreal style)? | W39.1 | Prioritised set; the editor pushes with explicit priorities |
