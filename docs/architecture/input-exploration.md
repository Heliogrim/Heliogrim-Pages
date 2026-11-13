# Input Backends (Exploration)

**Status**: <span class="hg-status closed">closed</span> 2026-11-09. Answers chunk [W39.0](../plan/work/input.md) for decision Q39.1 (SDL3 or native input per platform). The owner accepted the recommendation in section 6 on 2026-11-09; it is recorded as ADR [placeholder](../adr/placeholder-input-backend-sdl3-base.md). [W39.1](../plan/work/input.md) designs the backend interface against section 7.
**Origin**: 2026-11-09. Engine code read on branch `feat/affine-threads`. Platform research was done by three read-only research passes. They read the SDL source (`release-3.2.x`, `release-3.4.x`, `main`), the SDL wiki, Microsoft Learn, Apple developer documentation, wayland-protocols and peer-reviewed latency papers (sources in section 8). The Windows numbers in section 3 come from a throwaway spike on the owner's workstation. No engine code was changed.

## 1. Question

Q39.1 was decided as: not simply SDL3; integrate natively on Win32, iOS, macOS, Wayland and maybe X11 wherever a middle layer does not pay off. This page measures where native pays off, per platform and per capability: latency, device coverage (gamepad, pen, touch), event fidelity (timestamps, coalesced samples, IME) and maintenance cost.

## 2. Current engine state (checked 2026-11-09)

- SDL 3.2.22 (`vendor/sdl`, tag `release-3.2.22`) owns the following:
    - window creation (`SDL_CreateWindow` in `WinPlatform::makeNativeWindow`)
    - the message pump (`SDL_PollEvent` on the platform affine thread)
    - event translation (`SDL_AddEventWatch` → `WinPlatform::translateEvent`)
    - the Vulkan surface (`SDL_Vulkan_CreateSurface` in `Engine.Graphics/Surface/Surface.cpp`)
- Events translated today: quit, resize, close request, key up/down, mouse motion, buttons and wheel.
- Not translated:
    - text input and IME
    - gamepad, pen and touch (`SDL_INIT_VIDEO` only; no gamepad subsystem)
- Drag and drop is already native (OLE, `Support.Input.Win32`). SDL's drop events are disabled.
- SDL types leak past the platform layer:
    - `Editor.UI/Widget/InputBindingProvider.cpp` matches `SDL_KMOD_CTRL` and `SDL_KMOD_SHIFT`.
    - `AssetBrowserView.cpp` compares against the literal SDL button value `1`.
    - `Engine.Input/Input.cpp` includes `Support.Input.Win32` directly (the layer violation #119 names).
- SDL is now an old line. 3.4.0 shipped on 2026-01-01; 3.4.20 on 2026-11-03.

## 3. Measurements (Windows)

**Setup.**
- Hardware: AMD Ryzen 9 5900X, Windows 11 Pro build 26300, SDL 3.2.22 RelWithDebInfo, clang-cl `/O2`.
- Input: injected with `SendInput` (1 px relative mouse move, or the F13 key). The same thread sends and receives; the clock is QPC.
- Variants: a native window (Raw Input registered with `RIDEV_INPUTSINK`) and an SDL window (event watch).
- Pump modes: `[poll]` busy-pumps; `[wait]` blocks in `MsgWaitForMultipleObjectsEx` or `SDL_WaitEventTimeout`, which is how the platform thread runs.
- Size: 1000 samples per row; a 50 ms timeout drops a sample.

**What this measures.** Injected input skips the USB and HID driver stack. The numbers therefore isolate the part the backend choice controls: OS queue → application callback. They are not end-to-end latency.

| Path | n | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| Native `WM_INPUT` mouse [poll] | 1000 | 208 µs | 320 µs | 755 µs | 9.0 ms |
| Native `WM_INPUT` mouse [wait] | 1000 | 208 µs | 345 µs | 778 µs | 3.5 ms |
| SDL3 relative motion (raw-input thread) [poll] | 1000 | 77 µs | 158 µs | 363 µs | 0.8 ms |
| SDL3 relative motion (raw-input thread) [wait] | 1000 | 77 µs | 154 µs | 330 µs | 0.9 ms |
| Native `WM_KEYDOWN` [poll] | 1000 | 335 µs | 469 µs | 1.06 ms | 2.4 ms |
| Native `WM_KEYDOWN` [wait] | 864 | 331 µs | 385 µs | 641 µs | 1.1 ms |
| SDL3 `KEY_DOWN` [poll] | 1000 | 289 µs | 435 µs | 807 µs | 1.2 ms |
| SDL3 `KEY_DOWN` [wait] | 1000 | 289 µs | 485 µs | 1.49 ms | 3.0 ms |
| Native `WM_MOUSEMOVE` (cursor path) [poll] | 878 | 7.0 ms | 16.7 ms | 17.6 ms | 49.6 ms |
| Native `WM_MOUSEMOVE` (cursor path) [wait] | 920 | 16.5 ms | 16.9 ms | 17.9 ms | 34.0 ms |
| SDL3 absolute motion (cursor path) [poll] | 663 | 4.9 ms | 8.1 ms | 32.7 ms | 47.4 ms |

**Reading.**
- **Keyboard: SDL and native are equivalent** (about 0.3 ms p50 either way). SDL adds no measurable cost.
- **Relative mouse: SDL beats the naive native window.** SDL 3.2 reads raw input on its own `THREAD_PRIORITY_TIME_CRITICAL` thread with `GetRawInputBuffer` batching. The event watch fires on that thread without waiting for the main pump. A native backend only matches this by doing the same: its own raw-input thread.
    - Inferred from the numbers and the SDL source, not traced: event-watch callbacks run on SDL's raw-input thread. `WinPlatform::eventWatch` already re-posts to the platform thread, so this is safe today. The new backend must keep its buffer thread-safe.
- **Absolute cursor motion is slow and timer-quantised for both**: p50 of 5–16 ms, clustered at about 16.6 ms in wait mode.
    - Cause: Windows synthesises `WM_MOUSEMOVE` lazily from the cursor position. This is an OS property, not an SDL one.
    - The SDL `[wait]` row timed out on most samples (n = 50) and is left out as unreliable.
    - Consequence: editor tools that need high-rate pointer data (brush strokes, gizmo drags) must read raw deltas or pointer history, not cursor messages. That holds whatever library sits on top.
- The spike's SDL timestamp-accuracy probe returned no samples; event timestamp quality comes from the source reading in section 4.
- For scale: end-to-end mouse latency on desktop systems measures 50–83 ms (Casiez et al., UIST 2015). Touch measures 48–276 ms and is dominated by the display (Casiez et al., UIST 2017). The backend's sub-millisecond share is not the lever for #119's "event-to-gameplay latency". Pump placement, the Input stage drain point and the render queue are.

## 4. Findings per platform

### Windows (SDL 3.2 source; 3.4 noted)

| Area | SDL3 | Native gain | Native cost |
|---|---|---|---|
| Keyboard | Adequate. Raw keyboard is behind `SDL_HINT_WINDOWS_RAW_KEYBOARD` (default off); 3.4.4 adds an input-sink hint | Control over `RIDEV_NOLEGACY`; QPC stamp at poll | Low (1–2k LOC) but must redo scancode, E0/E1 prefixes, layouts and the text interplay |
| Mouse, relative | Adequate. Dedicated raw thread, batching, synthetic ns stamps spread over each batch | None measurable (section 3) | Low |
| Mouse, absolute (editor) | Partial. Cursor path is coalesced and quantised (section 3) | Raw deltas at the full polling rate next to the cursor | Low–medium |
| Pen | Partial. `WM_POINTER` pressure, tilt, rotation, barrel, eraser and proximity; no `GetPointerPenInfoHistory`, so coalesced samples are lost; distance is declared but never sent | Full-rate pen history for brushes and sculpting | Medium (about 1k LOC) |
| Touch and gestures | Partial. `WM_TOUCH` fingers with pressure fixed at 1.0; no Windows pinch emitter found (unverified, fetch truncated) | `WM_POINTER` touch and pinch, or DirectManipulation | Medium |
| Gamepad | Best available: HIDAPI drivers (PS3/4/5, Switch, Xbox, Steam and more), XInput, mapping database; 3.4 adds GameInput sensors | GameInput µs timestamps and impulse triggers (already in SDL 3.4) | Very high: about 25k LOC plus monthly device churn |
| IME | Mostly. IMM32 only, with composition, candidates (capped at 10) and app-drawn UI by hint | TSF: reconversion and a full text store | High (3–5k LOC); #119 defers IME edge cases |
| Timestamps | ms for messages (`GetMessageTime`); synthetic ns for raw input | None: `RAWINPUTHEADER` has no device timestamp, so poll time plus QPC is the ceiling | — |

### macOS

- **Keyboard and mouse.**
    - SDL uses `NSEvent` only.
    - Relative mode uses `CGAssociateMouseAndMouseCursorPosition(NO)` plus event deltas.
    - Timestamps are NSEvent seconds since boot, rebased onto SDL's ns clock.
    - Native GCMouse gives raw deltas on a queue of our choice (macOS 11+): about 200 lines, optional.
- **Gamepads.**
    - SDL gives Xbox, PlayStation and Switch pads to HIDAPI over IOKit.
    - DualSense adaptive triggers work through hand-packed effect bytes.
    - A native GCDualSenseAdaptiveTrigger plus CoreHaptics gives typed modes and richer haptics. Optional.
- **Tablets.** Covered (pressure, tilt, rotation, tangential pressure, eraser, proximity, buttons).
- **Trackpad.**
    - Pinch exists only from 3.4.
    - No rotate gesture in either version.
- **IME.** SDL's `NSTextInputClient` is weak: no candidate list, `firstRect` ignores the range, `characterIndexForPoint` returns 0. Fine for game chat, not for editor text fields.
- **Hard constraint.** AppKit event handling must run on the process main thread, whether we use SDL or native code. On macOS the engine's platform affine thread therefore has to be the main thread. See section 7.

### iOS and iPadOS

- **Lifecycle.**
    - TN3187: the UIScene lifecycle becomes mandatory in the major release after iOS 26 when building with the latest SDK.
    - SDL 3.2 only has an app delegate. **SDL 3.4+ is required for any iOS build** (it adds `SDLUIKitSceneDelegate`).
- **Pen.**
    - SDL exposes pressure, tilt, hover distance (16.1+), hover angles (16.4+) and barrel roll (17.5+).
    - Missing:
        - `coalescedTouches` (up to 240 Hz)
        - `predictedTouches`
        - Pencil squeeze (`UIPencilInteraction`)
        - per-touch hover timestamps (SDL sends 0)
- **Gamepads.** GameController only; no adaptive triggers through SDL.
- **Native cost.**
    - A thin layer of UIView-subclass hooks, a GameController trigger path and Pencil interaction is about 1–3k lines of Objective-C++.
    - Replacing SDL's UIKit backend (about 5.8k lines plus lifecycle) is not worth it.

### Wayland

- **SDL already covers most protocols.**
    - Keyboard and pointer: xkbcommon, `axis_value120`, relative-pointer, pointer-constraints, input-timestamps (ns where offered), cursor-shape, keyboard-shortcuts-inhibit.
    - Window management: xdg-shell, xdg-decoration with libdecor fallback, fractional-scale with viewporter, xdg-activation, color-management.
- **Gaps for an editor.**
    - Tablet pads are ignored. The pen wheel is a stub, and extra stylus buttons are dropped.
    - Pinch is scale-only (no translation or rotation) and 3.4+ only. No swipe or hold gestures.
    - Kinetic scroll start/stop (`axis_source`, `axis_stop`) is not forwarded.
- **Timestamps.** input-timestamps-v1 is supported only by Weston. Mutter, KWin, Sway and Hyprland lack it, so every backend gets ms timestamps.
- **Native window cost.** About 240 KB of configure, resize and scale state machine. GNOME has no xdg-decoration, so we would need libdecor or our own title bar. High cost, small gain.
- **Narrow native side channel.** Tablet pads, gestures and kinetic scroll could be bound on SDL's `wl_display`, or contributed upstream. Whether a second listener can share SDL's dispatch queue is unverified and needs a prototype.

### X11

- **Distribution trend.**
    - Ubuntu 25.10 and Fedora 43 dropped the GNOME Xorg session.
    - KDE Plasma 6.8 (2026-10-14) is Wayland-only; the 6.6 LTS keeps X11 until early 2029.
- **Remaining audience.** Ubuntu 24.04 LTS and Xfce, MATE and Cinnamon sessions.
- **SDL coverage.** SDL's X11 backend already has XInput2, valuator-based pen and touch. XWayland covers the rest.
- **Native gain.** Negligible, for a shrinking audience.

### Gamepads, all platforms

SDL's stack has these layers:

- HIDAPI per-vendor drivers (about 1.1 MB of C on `main`)
- the controller mapping database
- Steam Input cooperation (ignore-devices hint)
- per-platform fallbacks (XInput, GameController, evdev)

Each new controller generation adds work, which is most of what SDL's monthly releases contain. No platform showed a native gain that justifies this; the only candidates are typed trigger and haptics APIs on Apple.

## 5. Maintenance comparison

| Backend | SDL size (approx.) | Native replacement | Verdict |
|---|---|---|---|
| Windows video and input | 15–17k LOC (`src/video/windows`) | Window, pump, keyboard, mouse, pen, touch, IME | Capability side channels only |
| macOS (cocoa) | about 9k lines | Plus main-thread lifecycle | Keep SDL |
| iOS (uikit) | about 5.8k lines plus scene lifecycle | Owning UIApplicationMain and scenes | Keep SDL 3.4+ |
| Wayland | about 18k lines | Plus decorations and protocol churn (text-input replacements in wayland-protocols 1.46) | Keep SDL |
| X11 | about 20k lines | For a shrinking audience | Keep SDL |
| Gamepads | 25–30k LOC plus device churn | — | Keep SDL |

SDL is zlib-licensed, so no binary attribution is needed. It complies with the "no licensed or paid software" rule (Batch 2).

## 6. Recommendation (accepted 2026-11-09)

**Strategy: SDL3 is the base backend on every platform. It keeps window ownership, the pump, keyboard, gamepads and the lifecycle. Native code comes in as capability side channels, only where the evidence shows a gain.**

This meets the Q39.1 intent (no middle layer *where it does not pay off*). The measurements and the source reading show the middle layer costs nothing for keyboard, relative mouse and gamepads, and that replacing it costs 15–30k lines per platform. Native pays off only in narrow, additive places:

| Platform | Stays on SDL | Native side channel (priority order) |
|---|---|---|
| All | Upgrade 3.2.22 → 3.4.x first: pinch, UIScene, raw-keyboard input sink, pen fixes, GameInput sensors | — |
| Windows | Window, pump, keyboard (raw hint on), relative mouse, gamepads, IME (IMM32) | 1. Raw mouse deltas in absolute mode for editor tools. 2. Pen history (`GetPointerPenInfoHistory`). 3. `WM_POINTER` touch and pinch. Later: TSF |
| macOS | Everything | Optional: GCDualSense triggers and CoreHaptics; full `NSTextInputClient` only if the editor ships on macOS |
| iOS / iPadOS | Everything (3.4+ required) | Coalesced and predicted touches, Pencil squeeze, GameController triggers |
| Wayland | Everything | Tablet pads, swipe and hold, pinch rotation, kinetic-scroll stop; prototype the shared `wl_display` first, or upstream to SDL |
| X11 | Everything | None |

Only Windows is a target today, so the near-term native work is Windows items 1–3. They belong to W39.3 (pen and touch) and to the editor tools (S44). The other platforms' side channels wait for those ports.

Alternative not recommended: full native backends per platform. That means about 70–90k lines of window, pump, IME and gamepad code to reach parity, plus ongoing protocol and device churn. The only gain is control over details the table above already reaches through side channels.

## 7. Consequences for W39.1 (backend interface)

- **Capabilities, not one monolithic backend.** `Engine.Platform` registers input sources per capability: keyboard, pointer, raw pointer delta, pen, touch, gesture, gamepad, text/IME. On each platform a capability is served by SDL or by a native side channel, chosen at registration. `Support.Input.Win32` registers; nothing includes it.
- **Window ownership stays with SDL.** Native channels attach through SDL window properties (HWND, NSWindow/UIView, `wl_display`). The SDL window is the single owner.
- **`RawEvent` carries a source timestamp with its resolution** (ms message time, synthetic ns raw batch, µs GameInput) and may carry a **sample batch** (coalesced pen or touch samples, raw mouse batches). Actions must not assume one sample per frame.
- **Own key, scancode, modifier and button enums.** They replace `SDL_KMOD_*` and literal button numbers in `Editor.UI` and the asset browser.
- **Thread-safe intake.** SDL may deliver on its raw-input thread (section 3). The intake buffer stays thread-safe, and the Input stage drains it.
- **Apple main thread.** On macOS and iOS the platform affine thread must be the process main thread. That is an addition to the [affine thread design](affine-thread-design.md) when a port starts; not needed on Windows.
- **Latency measurement for #119.** Measure from the source timestamp to the Input stage drain, and to action delivery. The backend's share is below 1 ms (section 3), so pump wake-up and frame pacing are what to watch.

## 8. Open items and sources

**Not verified**:
- SDL event timestamp accuracy (the spike probe failed)
- whether GameInput is compiled into stock (non-GDK) SDL builds
- Windows pinch emission in SDL 3.4
- iOS HIDAPI DualSense support
- whether a Wayland side channel can share SDL's queue
- NSEvent behaviour with mice above 1 kHz

All LOC figures are estimates from byte counts. The native pen-history gain needs a real pen to quantify. The spike used injected input only, so a hardware click-to-photon run is the follow-up if end-to-end numbers are wanted (see the S59 evidence rules).

**Sources**:
- SDL source and wiki:
    - [SDL_windowsrawinput.c](https://github.com/libsdl-org/SDL/blob/release-3.2.x/src/video/windows/SDL_windowsrawinput.c), [SDL_windowsevents.c](https://github.com/libsdl-org/SDL/blob/release-3.2.x/src/video/windows/SDL_windowsevents.c), [SDL_windowskeyboard.c](https://github.com/libsdl-org/SDL/blob/release-3.2.x/src/video/windows/SDL_windowskeyboard.c)
    - [SDL_cocoaevents.m](https://github.com/libsdl-org/SDL/blob/release-3.2.x/src/video/cocoa/SDL_cocoaevents.m), [SDL_uikitpen.m](https://github.com/libsdl-org/SDL/blob/release-3.2.x/src/video/uikit/SDL_uikitpen.m)
    - [SDL_waylandevents.c](https://github.com/libsdl-org/SDL/blob/main/src/video/wayland/SDL_waylandevents.c), [joystick/hidapi](https://github.com/libsdl-org/SDL/tree/main/src/joystick/hidapi)
    - [releases](https://github.com/libsdl-org/SDL/releases), [README-main-functions](https://wiki.libsdl.org/SDL3/README-main-functions)
- Microsoft: [GetMessageTime](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getmessagetime), [GameInput FAQ](https://learn.microsoft.com/en-us/gaming/gdk/docs/features/common/input/overviews/input-faq), [IGameInputReading::GetTimestamp](https://learn.microsoft.com/en-us/gaming/gdk/docs/reference/input/gameinput/interfaces/igameinputreading/methods/igameinputreading_gettimestamp)
- Apple: [NSEvent.timestamp](https://developer.apple.com/documentation/appkit/nsevent/timestamp), [coalescedTouches](https://developer.apple.com/documentation/uikit/uievent/coalescedtouches(for:)), [GCDualSenseAdaptiveTrigger](https://developer.apple.com/documentation/gamecontroller/gcdualsenseadaptivetrigger), [TN3187 UIScene life cycle](https://developer.apple.com/documentation/technotes/tn3187-migrating-to-the-uikit-scene-based-life-cycle), [Thread Safety Summary](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Multithreading/ThreadSafetySummary/ThreadSafetySummary.html)
- Wayland and Linux:
    - protocols: [tablet-v2](https://wayland.app/protocols/tablet-v2), [pointer-gestures](https://wayland.app/protocols/pointer-gestures-unstable-v1), [input-timestamps](https://wayland.app/protocols/input-timestamps-unstable-v1), [xdg-decoration](https://wayland.app/protocols/xdg-decoration-unstable-v1), [text-input-v3](https://wayland.app/protocols/text-input-unstable-v3)
    - [kernel gamepad spec](https://docs.kernel.org/input/gamepad.html)
    - X11 retirement: [Ubuntu 25.10 notes](https://documentation.ubuntu.com/release-notes/25.10/), [Fedora WaylandOnlyGNOME](https://fedoraproject.org/wiki/Changes/WaylandOnlyGNOME), [KDE, 2025-11-26](https://blogs.kde.org/2025/11/26/going-all-in-on-a-wayland-future/)
- Latency:
    - Casiez et al., "Looking through the eye of the mouse", UIST 2015 ([PDF](https://direction.bordeaux.inria.fr/~roussel/publications/2015-UIST-mouse-based-lagmeter.pdf))
    - Casiez et al., "Characterizing latency in touch and button-equipped interactive systems", UIST 2017
    - Wimmer et al., CHI 2019 ([ACM](https://dl.acm.org/doi/fullHtml/10.1145/3290605.3300650))
    - NVIDIA [system latency guide](https://www.nvidia.com/en-us/geforce/guides/system-latency-optimization-guide/) (vendor document, not peer-reviewed)
