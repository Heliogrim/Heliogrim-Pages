# Input System

**Systems**: S39 · **Track** C · **Milestone** M2
**Status**: <span class="hg-status summary">plan</span>. Research from [simulation](../sources/research-simulation.md) section 6 (Unreal Enhanced Input, SDL3 events and the Unity Input System landing pages verified).

## Target

One input system that integrates UI, the editor, in-game controls and asset-augmentation tools (brushes, sculpting, pen pressure): raw device events, a device-agnostic action layer with value types, modifiers and triggers, a priority-ordered context stack with consumption that arbitrates between UI, editor viewport, gizmos and gameplay, remappable configurations as assets, and recording and injection for tests.

## Current state (checked 2026-11-07)

- `Engine.Input`: event classes (keyboard, mouse move and wheel, drag and drop sender, receiver and object), a schedule stage, `Support.Input.Win32` backend included directly. `Editor.UI.Service` has an `InputService` with binding lists (tested). No actions, contexts, modifiers, gamepad, pen or touch; no recording.
- SDL is vendored (window and events) with a plan to go native later.

## Research summary

- Unreal Enhanced Input (verified): input actions as data assets with value types (bool, axis 1D, 2D, 3D) and states (started, ongoing, triggered, completed, cancelled); mapping contexts added and removed at runtime with priorities, highest wins when several map the same action; modifiers (negate, swizzle, dead zone, smoothing) and triggers (tap, hold, chord); player-mappable configurations; `InjectInputForAction` for tests; debug display.
- SDL3 (verified): one event queue for gamepad, keyboard with text input and IME, mouse, pen (pressure, axes, proximity) and touch (fingers, pinch); event watchers and filters; `SDL_PushEvent` for injection.
- Editor versus game versus UI arbitration has no sourced model; the context stack with consumption is the closest verified pattern.

## Guidance

- **Layers**: raw events (SDL3 now, native Win32 later behind `Engine.Platform`, which removes the direct `Support.Input.Win32` include) → device-agnostic actions (`InputAction { name, value type, modifiers, triggers }`) → contexts (`InputContext { priority, mappings, consume policy }`) → consumers (uikit focus, editor tools, gizmos, gameplay components).
- **Arbitration**: the uikit's focused widget and hover layer push a context; the editor viewport pushes a tool context when hovered or captured; gizmos push a capture context during a drag; gameplay contexts sit below. Consumption is per action, so a UI text field consumes typing while gameplay still reads the gamepad.
- **Value types** cover pen pressure, tilt and touch gestures without special cases; asset-augmentation tools (terrain brushes, S28; splat painting, S27) bind to `Axis3D` plus pressure.
- **Assets**: actions and mapping contexts are serialised assets with reflection (S09); remapping presets per platform and per user.
- **Testing**: record raw events with timestamps at the SDL boundary and actions at the action boundary; inject either in tests (S54) and in replays (S59).
- **Scheduling**: the platform pump is an affine thread (S02); events are drained at the frame's Input stage; latency from event to gameplay is bounded and measured.

## Done when

- The editor, its viewport, a gizmo drag and a running game scene coexist with correct consumption; typing in a text field never moves the camera.
- A gamepad, a pen with pressure and touch pinch drive actions through the same path.
- A recorded editor session replays its input to the same action stream in a test.

## Open decisions

- Native Win32 input versus staying on SDL3 (ties to the platform decision in the audio brainstorm).
- Whether contexts are a stack or a prioritised set (Unreal uses a set).
