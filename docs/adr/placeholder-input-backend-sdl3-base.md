# Placeholder: SDL3 as Base Input Backend, Native Capability Side Channels

**Date**: pending (exploration closed 2026-11-09)
**Status**: placeholder, not yet processed in the engine project
**Source**: [Input backends exploration](../architecture/input-exploration.md), chunk W39.0, question Q39.1

## Context

Q39.1 asked for native input integration on Win32, iOS, macOS, Wayland and maybe X11 wherever SDL3 as a middle layer does not pay off. The exploration measured Windows, using injected input on a Ryzen 9 5900X, and read the SDL, Apple, Microsoft and Wayland sources for every platform.

## Decision

- SDL3 is the base input backend on every platform. It owns:
    - the window and the event pump
    - keyboard and relative mouse
    - gamepads
    - text input and IME (IMM32 on Windows)
    - the app lifecycle
- The engine moves from SDL 3.2.22 to 3.4.x before W39.1 is implemented. 3.4 is required for iOS (UIScene).
- Native code enters only as capability side channels. They attach to the SDL-owned window, and each one is justified by a measured or documented gain:
    - **Windows** (now): raw mouse deltas while the cursor is visible, pen history (`GetPointerPenInfoHistory`), and `WM_POINTER` touch and pinch. TSF later.
    - **iPadOS** (with the port): coalesced and predicted touches, Pencil squeeze, GameController adaptive triggers.
    - **Wayland** (with the port): tablet pads, swipe and hold gestures, pinch rotation, kinetic-scroll stop. Prototype sharing SDL's `wl_display` first, or upstream the changes to SDL.
    - **macOS**: optional only (DualSense and CoreHaptics; a full `NSTextInputClient` if the editor ships there).
    - **X11**: none.
- `Engine.Platform` registers input sources per capability. `Support.Input.Win32` registers; nothing includes it. Engine code uses its own key, modifier and button enums, not SDL's.

## Alternatives Considered

### Full native backend per platform

- **Pros**:
    - Full control over window, pump and event details.
    - No third-party layer.
- **Cons**:
    - Roughly 15–30k lines per platform to reach parity.
    - Gamepads add 25–30k lines plus monthly device churn.
    - Wayland text-input and decoration protocols keep changing.
- **Why not**: SDL showed no measurable latency cost:
    - Keyboard is about 0.3 ms p50 with SDL or native.
    - SDL's relative mouse reached 77 µs against 208 µs for a naive native `WM_INPUT` window.
    - The real gaps are narrow and additive, so side channels reach them.

### SDL3 only

- **Why not**: SDL leaves editor-relevant gaps:
    - pen history on Windows
    - coalesced touches on iPadOS
    - tablet pads and gestures on Wayland
    - absolute mouse at full polling rate

## Consequences

### Positive

- One window owner per platform.
- Gamepad and device churn stays upstream.
- New platforms start working on day one through SDL.

### Negative

- Two code paths per capability where a side channel exists, so the backend interface must make the source explicit.
- SDL upgrades become routine maintenance.

### Risks

- The Windows numbers use injected input on one machine. A hardware end-to-end run (S59 evidence rules) is still open.
- On Apple the platform affine thread must be the process main thread. This must land in the affine-thread design before a macOS or iOS port.
