# Engine Loop (Exploration)

**Status**: exploration. Nothing here is decided except where marked "owner". It is the design half of chunk W02.11 (stage access review and edge relaxation): the frame as the owner intends it, the data each stage needs, what other engines do, and the open choices. The agreed read and write sets go back into the [task graph design](task-graph-design.md) section 8 once the choices below are made.

**Origin**: owner conversation 2026-11-14. The owner walked through one tick as intended and asked for a data-dependency graph, research on how other engines structure their loop, the stages not modelled yet (animation and IK, network send and replication, audio in detail), and whether nodes can be skipped under overload to keep the simulation interval.

## 1. The frame today (checked on `feat/wip` `bf9a8a11`, 2026-11-14)

Seventeen stages, one strict chain (task graph design 8). All lanes critical except the two actor physics callback stages. Stubs: the three actor tick stages and both callback stages (`// TODO: Tick actor`).

| # | Stage | Reads | Writes |
|---|---|---|---|
| 1 | `::Core::TickBegin` | | `core::Timing` |
| 2 | `InputTick` | | `Input` |
| 3 | `ActorTickPrePhysics` (stub) | Timing, Input | `acs::Registry` |
| 4 | `SceneBroadcastPrePhysics` | Registry | `scene::SceneBase` |
| 5 | `SceneUpdatePrePhysics` | | SceneBase |
| 6 | `PhysicsTick` | Timing, SceneBase | `physics::PhysicsSceneSystem` |
| 7 | `PhysicsReadback` | SceneBase, PhysicsSceneSystem | Registry |
| 8, 9 | `ActorPhysicsOverlap`, `ActorPhysicsCollision` (stubs, normal lane) | PhysicsSceneSystem | Registry |
| 10 | `ActorTickPostPhysics` (stub) | Timing | Registry |
| 11, 12 | `SceneBroadcastPostPhysics`, `SceneUpdatePostPhysics` | Registry / none | SceneBase |
| 13 | `::Reflow::Tick` | | `reflow::WindowManager` |
| 14 | `RenderTick` | SceneBase, WindowManager | `graphics::scene::RenderSceneManager` |
| 15 | `ScenePostProcess` | | SceneBase |
| 16 | `ActorHousekeeping` | | Registry, SceneBase |
| 17 | `::Core::TickEnd` | | |

`RenderTick` selects the render targets from the `RenderSceneManager` and records each one (`RenderTickStage::tickTargets`); views read a render-side scene system (`render::RenderSceneSystem`) that the scene broadcast feeds. Physics steps Jolt on `JobSystemSingleThreaded` once per frame with the frame delta.

## 2. The intended frame (owner, 2026-11-14)

1. **Actor tick (pre physics)** is where user code runs. It needs timing, delta timing and the current user actions and input. It instructs changes: positions, physics, spawning and destroying models, sources for graphics, physics and audio, possibly network messages.
2. **Scene broadcast and update (pre physics)** propagate the user code's changes into the scene, update the scene representation and pre-act on changes.
3. **Physics tick** simulates from the latest state and the difference to the previous one. Physics events are queued, so no ghost events are handled.
4. **Physics readback** plays changes back into the scene (transforms) and perhaps owns the event queueing; the interface is open.
5. **Overlap and collision** unwind the physics event queue.
6. **Actor tick (post physics)** reacts once physics has settled.
7. **Scene broadcast and update (post physics)** propagate the changes into the scene systems and subscriptions.
8. **Graphics, UI and audio** react to the simulated changes. The scene tells Reflow the new bounds (in-world embedded UI screens), so the Reflow tick lays out and updates the UI.
9. **Render**, with an open question on where render command capture belongs (section 5).
10. **Post-processing**, which may hook into scene readbacks (for example graphics scene compaction).
11. **Housekeeping** handles actors and components.

Not modelled yet: animators and animator IK, network send and replication, audio in detail.

## 3. Data dependencies

The owner's order as data flow. Stages marked with a star do not exist; their placement follows section 4.

```hg-diagram
flowchart TB
    T["TickBegin<br/>Timing"] --> A1
    I["InputTick<br/>Input"] --> A1
    NR["*NetReceive<br/>remote state, RPCs"] --> A1
    A1["ActorTickPrePhysics<br/>user code: intents"] --> SB1["SceneBroadcast/UpdatePrePhysics"]
    SB1 --> AN["*AnimEval<br/>per character, parallel"]
    AN --> P["PhysicsTick<br/>fixed step, event queue"]
    SB1 --> P
    P --> R["PhysicsReadback<br/>transforms to scene"]
    R --> IK["*IK / pose fix-up"]
    R --> C["Overlap / Collision<br/>drain event queue"]
    C --> A2["ActorTickPostPhysics"]
    IK --> SB2
    A2 --> SB2["SceneBroadcast/UpdatePostPhysics<br/>world settled"]
    SB2 --> AU["*AudioUpdate<br/>listener, emitters"]
    SB2 --> NS["*NetSend<br/>replicate, flush"]
    SB2 --> RF["Reflow<br/>layout"]
    SB2 --> EX["*Extract<br/>render snapshot"]
    RF --> EX
    EX --> RN["Render<br/>views, record"]
    RN --> PP["ScenePostProcess"]
    PP --> HK["ActorHousekeeping"]
    AU --> HK
    NS --> HK
    HK --> TE["TickEnd"]
```

What the graph shows:

- Up to "world settled" the frame is a chain by necessity: each step consumes the previous one. Parallelism inside that chain comes from fan-out within a stage (per-actor ticks, per-character animation, Jolt's jobs through a `JPH::JobSystem` adapter, see the [lane policy exploration](lane-policy-exploration.md) 3.2), not from relaxing edges.
- After "world settled" the readers are independent: audio, network send, Reflow and render extraction read the settled world and write disjoint state. Today they are four links of the chain; this is where W02.11's edge relaxation pays.
- With one `SceneBase` key every scene stage conflicts with every other; finer keys are W02.12.

### 3.1 The loop by event

The same frame as events rather than data: when each part runs, which parts repeat, and which run on their own cadence. It combines the owner's order (section 2), the fixed-step split (5.1) and the decoupled graphics cycle (5.2a); the starred parts do not exist.

```hg-diagram
flowchart TB
    FB(["Frame begin<br/>TickBegin: wall time, frame delta"]) --> POLL["Poll<br/>InputTick: latch OS input once<br/>*NetReceive: drain packets"]
    POLL --> ACC{"Accumulator<br/>has a step due?<br/>(cap: max steps per frame)"}

    subgraph SIM ["Simulation step (fixed dt, 0..n per frame)"]
        direction TB
        S1["ActorTickPrePhysics<br/>user code, consumes latched input once"] --> S2["SceneBroadcast + Update<br/>ePrePhysics"]
        S2 --> S3["*AnimEval<br/>per character"]
        S3 --> S4["PhysicsTick<br/>queue contact events (step id)"]
        S4 --> S5["PhysicsReadback<br/>transforms to scene"]
        S5 --> S6["Overlap / Collision<br/>drain event queue"]
        S6 --> S7["ActorTickPostPhysics<br/>*IK fix-up"]
        S7 --> S8["SceneBroadcast + Update<br/>ePostPhysics"]
    end

    ACC -- "yes" --> S1
    S8 -- "emit patches (step id)" --> PQ[("Render patch queue<br/>coalesced per object")]
    S8 -- "*NetSend (server: per step)" --> NQ[("Outgoing packets")]
    S8 --> ACC
    ACC -- "no, or cap hit: sim time dilates" --> FR

    subgraph FRAME ["Frame work (once per frame)"]
        direction TB
        FR["Reflow<br/>layout from settled bounds"] --> AU["*AudioUpdate<br/>listener, emitters to mixer"]
        AU --> NC["*NetSend (client: per frame)"]
        NC --> HK["ScenePostProcess + ActorHousekeeping"]
    end

    HK --> FE(["Frame end<br/>TickEnd"])
    FE --> FB

    subgraph GFX ["Graphics cycle (own cadence, spans engine-loop stages)"]
        direction TB
        G0{"Previous cycle<br/>allows a new one?"} -- "yes" --> G1["Apply patch queue<br/>to the render replica"]
        G1 --> G2["Per view: offscreen targets first<br/>record (UI surfaces, viewports)"]
        G2 --> G3["Submit, present"]
        G3 --> G4["Retire: free replica objects<br/>removed in this cycle"]
        G4 --> G0
        G0 -- "no: skip this frame" --> G0
    end

    PQ -.-> G1
    FR -. "UI surfaces dirty" .-> G2
```

Two loops repeat inside a frame: the simulation step (0 to n times, bounded by the step cap) and, outside the engine loop, the graphics cycle, which starts when its previous cycle allows and reads only the patch queue and its own replica. The frame loop itself repeats per presented frame. Dropping a rendered frame under overload means the graphics cycle starts less often; the simulation steps keep their count until the cap, past which simulation time dilates.

How a graphics cycle overlaps the engine loop over time (illustrative durations, one cycle per frame here; under load a cycle may span more than one frame):

```hg-diagram
gantt
    dateFormat x
    axisFormat %L
    section Engine loop
    Frame N poll and sim steps       :a1, 0, 8ms
    Frame N frame work               :a2, after a1, 3ms
    Frame N+1 poll and sim steps     :a3, after a2, 8ms
    Frame N+1 frame work             :a4, after a3, 3ms
    section Graphics cycle
    Cycle N-1 record and submit      :g0, 0, 10ms
    Cycle N apply patches            :g1, after a2, 1ms
    Cycle N record and submit        :g2, after g1, 10ms
    section GPU
    Cycle N-1 GPU work               :p0, after g0, 9ms
    Cycle N GPU work                 :p1, after g2, 9ms
```

## 4. What other engines do

Research 2026-11-14 in two passes (frame structure; overload and timesteps). Primary sources only; each line is marked verified (read in the source) or unverified. Source list in section 9.

### 4.1 Order of the frame

- **Unreal Engine 5**: tick groups `TG_PrePhysics` (physics data one frame old), `TG_DuringPhysics` (work that tolerates a frame of lag), `TG_PostPhysics` (this frame's physics results), camera and timers, `TG_PostUpdateWork`, deferred spawns, then render. Groups are barriers; ticks in a group may run in parallel; `AddTickPrerequisite` adds an edge inside a group. [verified]
- **Unity 6**: physics runs after `FixedUpdate`, its trigger and collision callbacks inside the physics step; rendering after the update phases. The player loop is a replaceable tree of systems. [verified]
- **Godot 4**: `_physics_process` before each fixed physics step (60 Hz default); `_process` once per frame, not synchronised with physics. [verified]
- **Bevy**: `First`, `PreUpdate`, `StateTransition`, `RunFixedMainLoop` (the fixed schedule 0 to n times), `Update`, `PostUpdate`, `Last`; rendering in a separate sub-app. Systems run in parallel unless ordered. [verified]
- **Destiny** (Bungie, GDC 2015): the main loop as job chains; a runtime resource tracker checks that every read, write, create and destroy happens at a safe point in the frame. [verified, abstract only]

The shared order: input; gameplay before physics plus the animation physics must follow; the physics step; contact callbacks and post-physics gameplay; camera; late work; extract; render. Heliogrim's order (section 2) matches it.

### 4.2 Render behind the simulation

- **Unreal**: the render thread runs one or two frames behind the game thread; render state lives in mirrored scene proxies; dynamic data (bone transforms) is copied and handed over. [verified]
- **Bevy** `PipelinedRenderingPlugin`: frame N renders while frame N+1 simulates; extract (copy from the main world to the render world) is the only sync point. [verified]
- **Naughty Dog** (Gyrling, GDC 2015): game logic, render logic and GPU work on three different frames at once; a frame is data, not time: per-frame parameters (delta time, camera, skinning matrices, mesh list) in one of 16 rotating `FrameParams`; memory lifetime tied to frame completion with allocators tagged game-only, game-to-render, game-to-GPU, render-to-GPU. Frame time 25 ms to 15.5 ms in the talk. [verified, slides]

### 4.3 Animation and IK

- **Unreal**: an animated character ticks in `TG_PrePhysics` "in order for physics-simulated objects to follow and interact with it". Animation evaluation runs on workers that pull data (Property Access) and joins in one game-thread completion task that writes transforms, physics and notifies; root motion blocks the parallel path. Update rate optimisation and the Animation Budget Allocator lower the rate with distance. [verified]
- **Unreal IK Rig**: foot alignment as an additive layer on the incoming pose, limb IK last. Where its traces run relative to physics is not stated. [verified / unverified]
- **Unity**: `AnimatorUpdateMode.Normal` evaluates per frame, `Fixed` in the fixed loop to align with physics. The internal order (state machine, root motion, IK pass, transform write, before `LateUpdate`) only appears in a diagram. [verified / unverified]
- Two slots follow: evaluation before physics (what physics follows), fix-ups after (foot IK on settled collision). Per-character evaluation is the largest fan-out of the frame.

### 4.4 Network

- **Unreal**: an RPC is serialised immediately and sent "in the next net update at the end of the frame" [verified]; `TickDispatch` receives at the start of the frame, `TickFlush` replicates and flushes at the end [unverified, API text].
- **Unity Netcode for Entities**: receive before the ghost simulation; input gathered before the command send; the predicted simulation group runs at a fixed step and re-runs several times per frame on the client for rollback; the server's ghost send emits one packet per network update. [verified]
- Network brackets the frame: receive first, send last. An MMO client with prediction needs the fixed simulation part to be re-runnable.

### 4.5 Audio

- **Unreal Audio Mixer**: game thread, audio thread (what plays, with which parameters), audio render thread (all DSP and mixing), hardware callback thread; parameters (volume, pitch, position) are sent from the game; buffers are generated ahead of the hardware. [verified]
- **FMOD and Wwise**: set listener and emitter attributes, then one update or `RenderAudio` per frame. [unverified, docs did not render]
- Audio is a late reader: push after the final transforms, once per frame, through a queue to the mixer (Heliogrim's audio runtime design already puts the device on its own thread).

### 4.6 UI and render-to-texture

- **Unity URP**: every camera rendering into a texture renders before the cameras rendering to the screen. [verified]
- **Unity uGUI**: layout rebuilds are deferred to the end of the frame, just before rendering; `Canvas.willRenderCanvases` fires before canvas rendering. [verified]
- **Unreal**: widget components have a redraw time (0 = every frame) or manual redraw; scene captures can capture every frame or only on change [verified]; capture sort priority orders captures to resolve interdependencies [unverified].

### 4.7 Overload and timesteps

- **Fixed step with catch-up** (Fiedler, "Fix Your Timestep!", 2004): the renderer produces time, the simulation consumes it in fixed steps through an accumulator; render interpolates by `alpha = accumulator / dt`. Being behind makes the loop run more steps (the spiral of death); the fix is a cap on steps per frame, after which the simulation slows. [verified]
- **Unity**: zero, one or several fixed updates per frame (100 Hz at 40 fps: two or three per frame); `Time.maximumDeltaTime` (default 0.333 s) caps the advance per frame, and beyond it game time does not catch up with real time. UI should animate on unscaled time. [verified]
- **Godot**: `max_physics_steps_per_frame` 8 against the spiral of death; past it the game slows. Physics interpolation renders one to two ticks in the past; extrapolation is rejected because it can place objects inside walls. [verified]
- **Unreal**: max physics delta time makes physics artificially slow when smaller than the frame; substepping queues collision callbacks to the last substep, so one frame can deliver several callbacks for one contact. [verified]
- **Jolt**: collision steps per `Update` are accuracy substeps inside one call; the caller owns the accumulator. [verified]
- **EVE Online** time dilation (CCP, 2011, 2014): the server slows its game clock to keep its task queue short; timers players read off a watch are not dilated; a 10 % floor, past which work backs up. [verified]
- **What is shed first**: rendered frames, then simulation speed. Lower-priority work runs at a lower rate with interpolation (Unreal Animation Budget Allocator: a millisecond budget, significance ranking, hysteresis, never-skip flags). No engine found skips single nodes inside a simulation step. [verified]
- **Hazards**: one-shot input read in a loop of a different rate is missed or doubled (Unity Input System); several contact callbacks per frame under substepping; gameplay tied to wall-clock timers must not dilate. [verified]

## 5. Considerations

### 5.1 Two subgraphs at two rates

The research points to splitting the frame:

- **Simulation subgraph**, fixed step, may run 0 to n times per frame: input consume, network receive, actor tick, scene sync, animation evaluation, physics, readback, contact callbacks, post-physics tick, scene sync.
- **Frame subgraph**, once per presented frame: Reflow, extract and render, post-process, audio push, network send (open: per frame or per simulation step), housekeeping.

Catch-up is bounded by a step cap and a maximum frame delta; past the cap the simulation clock slows (dilation) instead of skipping nodes. A simulation step runs whole or not at all. Three clocks follow: simulation time (dilates), frame time (UI, editor, audio smoothing), wall-clock deadlines (never dilated). Input is latched once per frame and consumed by exactly one simulation step; contact events carry the step they belong to, so a repeated step never re-fires them.

This answers the owner's overload question: nodes of the simulation subgraph are never skipped; the frame subgraph thins first (render rate, distant animation through a budget), then simulation time slows. The headless and server role is the same loop without the frame subgraph.

### 5.1a Fixed or variable step: arguments (2026-11-14)

| For a fixed step | Against it |
|---|---|
| Trajectories, jumps and collisions do not depend on the frame rate; a variable step changes them with dt (Godot docs, 4.7) | Render interpolation becomes mandatory, with the previous state of every moving object kept and up to one step of extra visual latency (16.7 ms at 60 Hz) |
| Jolt is documented stable at 60 Hz with one collision step; a variable dt leaves that range on long frames | Patches carry their step id; teleports need an interpolation reset |
| Precondition for replay, lockstep or rollback and client re-simulation (not sufficient alone: FP settings and parallel order matter too) | New loop code: accumulator, step cap, dilation, input latched per frame, events tagged per step; `CompositePipeline` has no inner loop today |
| The server tick is the same loop without the frame work | Rate beats when display and simulation rates do not divide; camera and its input path usually stay per frame |
| Frames above the simulation rate run zero steps and only interpolate | A higher step rate multiplies simulation cost per second |
| Overload is predictable: the cap slows simulation time instead of growing dt until physics fails | |

**Movie and video output with a pacemaker.** The pacemaker sets the frame time to exactly 1/output fps, independent of render cost. With a fixed step the movie runs the same simulation as the session it was authored and previewed in; changing the output rate changes only the sampling; 60 Hz at 24 fps alternates two and three steps per output frame, deterministically (a multiple such as 120 Hz splits evenly). With a variable step at dt = 1/output fps the output rate becomes a parameter of the simulation (at 24 fps dt is 41.7 ms, different physics from the 60 Hz session, and Jolt needs more collision steps). Unreal's Movie Render Queue and Unity's Recorder use a fixed frame rate with temporal sub-sampling [unverified, not checked in this research].

**Deferred (owner, 2026-11-14): motion-blur sub-frames.** Sampling several sub-frames per output frame, by interpolation between steps or by a higher simulation rate, is kept in mind but not designed now: the implementation overhead does not pay for games and gameplay. Movie mode first means only a pacemaker replacing wall time for the accumulator.

### 5.1b What a 60 Hz fixed step does to the loop

- **Frames and steps.** At 120 fps with a 60 Hz simulation, about every other frame runs one simulation step and the frame between runs none. Both frames render: the first at interpolation fraction 0, the second at 0.5 between the previous and the current step, so motion is smooth at 120 fps. Without interpolation every second frame would repeat the previous image. At 30 fps each frame runs two steps; at 50 fps the count alternates between one and two.
- **Graph.** The stage graph splits into two graphs. The simulation graph (actor tick pre physics to scene sync post physics) is the loop body, run 0 to n times per frame; its inner edges stay as they are. The frame graph (poll, the step loop, flush, then Reflow, audio, network send, post-process, housekeeping) runs once per frame. Frame stages depend on the flush, not on simulation stages, so the two graphs never share an unordered pair and their keys are checked separately. Needs a loop in `CompositePipeline` (two graphs, or a repeating node), which does not exist.
- **Timing.** `core::Timing` splits into simulation time (fixed dt, step index, dilates past the cap) and frame time (variable delta, interpolation fraction). User code in the actor ticks reads the fixed dt; UI, editor and audio smoothing read frame time.
- **Input.** Latched once per frame and consumed by the first step of that frame; a frame with no step carries it to the next step, up to one step later (16.7 ms). Camera look and other latency-critical input stay per frame.
- **Change management** (scene layer exploration 7.2). The flush after the step loop coalesces the changes of 0 to n steps into one set per frame consumer. A frame with no step flushes nothing and only advances the interpolation fraction. Interpolation needs the previous and current transform of moving objects, so the render replica keeps two transform states and a transform patch carries its step id.
- **Depth.** The stages themselves barely change. The changes sit in the scheduler pipeline (loop), timing (two clocks), input (latch and consume), the render replica (two states, interpolation) and physics (fixed dt in `PhysicsTickStage` instead of the frame delta).

### 5.1c Per-frame user code, input and latency (owner questions, 2026-11-14)

The owner asked how user code outside the fixed step reads correct input (Unity's `Update` against `FixedUpdate`), and why a player on a fast machine should accept 16 ms or more of input lag in a shooter.

- **Two user-code slots, as in Unity.** A per-step tick (simulation: movement, physics, authoritative gameplay) and a per-frame tick (presentation: camera, aim display, UI, effects, animation blending that physics does not follow). The per-frame tick reads frame time and runs once per frame after the step loop; it must not write simulation state, or it re-introduces the variable step.
- **Input with two views, no lost or doubled edges.** Input events are queued with a timestamp. The per-frame view reports edges since the last frame (Unity's `WasPressedThisFrame` semantics). The per-step view hands each step the events whose timestamps fall inside that step's time window; events wait until a step consumes them, so a frame with no step carries them on and two steps in one frame split them by time. This removes the hazard documented for Unity's Input System (4.7) by construction.
- **Where the 16 ms comes from.** With a 60 Hz step, an action waits on average 8.3 ms and at worst 16.7 ms for the step that consumes it; interpolation shows a state up to one step old. Measures, cheapest first:
  1. *View on the frame, not the step.* Mouse look and the camera of the local player are applied per frame from the latest input and sampled as late as possible before render submit; view rotation never waits for a step. This removes the lag players feel most.
  2. *Timestamped actions inside the step.* A shot fired at time t inside a step is resolved with the view direction at t (from the per-frame view history), not the direction at the step boundary: sub-step precision without more steps. Valve's CS2 "sub-tick" is a public example [unverified, not checked in this research].
  3. *Local player not interpolated.* The locally controlled character renders its latest simulated state, remote and physics objects render interpolated.
  4. *Higher step rate per project.* The rate is configurable: 120 or 128 Hz halves the wait (4.2 ms average, 8.3 ms worst) at twice the simulation cost; a competitive shooter can choose it, a strategy game 30 Hz.
- **The larger share sits elsewhere.** End-to-end latency is dominated by frames in flight (CPU render pipelining, swapchain, GPU queue) and the display. The pipelined render of 5.2 adds a frame there; measures 1 and 3 keep the view path out of it by late sampling, and the number of frames in flight is the knob for the rest. A variable step would only save the step wait, not these frames.

### 5.1d Loop modes: time source × step mode (owner, 2026-11-14)

The owner decided to support both step modes, combined with both time sources, selectable per project; a compile flag only where a setting would cost at runtime.

| | Variable step | Fixed step |
|---|---|---|
| **Auto-pace** (wall clock; paced by W02.9) | One step per frame, dt = frame delta. Today's behaviour; not deterministic; no interpolation | 0 to n steps per frame from the accumulator, step cap, dilation, interpolation |
| **Pacemaker** (frame time set externally: movie render, replay, tests) | One step per frame, dt = 1/pacemaker rate. Deterministic; the output rate is a parameter of the simulation | Accumulator fed by the pacemaker. Deterministic; the simulation equals the authored session |

One loop carries all four. Variable step is the fixed-step loop with the step dt set to the frame delta and exactly one step per frame: interpolation fraction 1 (render the latest state), no previous transform state needed. The per-step and per-frame user-code slots, the two input views (5.1c) and the flush (5.1b) exist in every mode; in variable mode both tick slots run once per frame, so user code written for the fixed step also runs under a variable step.

**Setting or flag.** The mode costs one branch per frame and, in fixed mode, the previous transform state in the render replica; both are decided when the loop starts and allocated accordingly. No mode needs a compile flag. Proposed settings, next to `SchedulerConfigProperty::eWorkerCount` (`Engine.Config/Enums.hpp`), names for the design:

| Setting | Values | Changes when |
|---|---|---|
| Step mode | fixed, variable | At the start of a session (play session in the editor, game start): switching mid-session changes the simulation |
| Step rate | Hz, default 60 | Same |
| Max steps per frame | default from measurement (Godot uses 8) | Same |
| Time source | auto, pacemaker | At runtime: the accumulator only takes its delta from another source, so the editor can start a movie render or a replay without a restart |
| Pacemaker rate | output fps | With the time source |

Constraints between them: replay, lockstep and rollback need a deterministic mode (pacemaker with either step, or auto with fixed and timestamped input); client prediction needs the fixed step. The server role uses fixed with auto-pace.

### 5.2 Render on a snapshot (pipelining)

Split `RenderTick` into **Extract** (serial, reads the settled scene, copies what render needs) and **Render** (reads only the copy). Render of frame N then overlaps the simulation of frame N+1.

| Benefit | Cost |
|---|---|
| Frame time becomes the longer of simulation and render CPU work instead of their sum (Naughty Dog: 25 to 15.5 ms) | One more frame between input and photons on the CPU side (16.7 ms at 60 Hz); mitigated by sampling camera and input as late as possible in Extract |
| Render never reads live scene state, so its edges to the scene disappear from the graph and the conflict checks get simpler | Extract is a serial sync point; it must copy only what changed |
| Workers stay busy: render recording fills the gaps of the simulation chain | One copy of render state per frame in flight (double or triple buffered) |
| Natural fit for 5.1: render needs the last two simulation states for interpolation anyway | Destroyed objects and freed resources must outlive the frames still rendering them: deferred destruction by frame, lifetime-tagged allocation |
| Headless role simply drops Extract and Render | Editor tools (picking, gizmos) read render data one frame old |

Heliogrim already has half of an extract: views read `render::RenderSceneSystem`, which the scene broadcast feeds, not the live scene. What is missing is the per-frame copy, so that the broadcast for frame N+1 cannot change data the render of frame N still reads. The GPU already runs behind the CPU through the swapchain's frames in flight; pipelining adds the CPU render work to that overlap.

### 5.2a Owner direction: differential patches, a graphics cycle of its own (2026-11-14)

The owner's picture replaces a full Extract copy:

- **The scene already tells render what changed, by phase.** Scene broadcast and update run with `SceneBroadcastFlagBits::ePrePhysics` / `ePostPhysics` and `SceneUpdateFlagBits::ePrePhysics` / `ePostPhysics` (`ScenePipeline.cpp`). The render side reacts to those pushes and buffers them according to the flag.
- **The intended end state is a differential patch of what actually changed**, not a copy of the render state: it cuts backpressure and memory throughput.
- **Render already owns a replica.** Graphics data is replicated from the actor components into a render-system model, so render holds its data for as long as it needs it. The render graph can already hold resources of several frames with their links and symbols (owner; not checked here).
- **A graphics cycle spans engine-loop stages.** It starts when the previous one allows, applies the patches gathered so far, records and submits, and may run across the stages of the next simulation steps until the graphics cycle N+M begins. The graphics cycle is decoupled from the engine loop, not one frame behind it by construction.

Consequences to settle in the design (the owner expects gaps here):

1. **Patches are queued, not applied in place, while a cycle reads the model.** Broadcasts append patches to a queue; the graphics cycle applies the queue at its own start. The render model is then only written by the graphics cycle, and the scene's edge to render becomes a queue, not a shared key.
2. **Coalescing**: several simulation steps can run before the next graphics cycle; a patch for an object that a later step changes again is superseded, so only the last value per object and field is applied (pre-physics patches are mostly superseded by post-physics ones within a step).
3. **Removal is deferred**: an object destroyed while a cycle still records it stays alive until that cycle completes; the replica's lifetime, not the scene's, decides.
4. **Interpolation** (5.1): with a fixed simulation step the graphics cycle needs the last two simulation states of moving objects, so a transform patch carries the step it belongs to.
5. **What the editor reads** (picking, gizmos) comes from the replica, so it sees the state of the last applied patch set.

### 5.2b Scene as the change hub, jobs as dependencies, a central spatial index

Raised by the owner 2026-11-14, worked out in the [scene layer and spatial index exploration](scene-layer-exploration.md) (neutral comparison of five change-mediation schemes and four index options against ten scenarios). Points that bear on this page:

- **Today**: the scene already has a small structural change log (`SceneComponentQueue`, add and remove, committed at both broadcasts); value changes are polled, both systems' `broadcast()` are empty and neither `update()` reads the phase flags, so every model is walked twice per frame. `SceneWalker` and its culling filter do not execute. No spatial query exists; only Jolt's broadphase.
- **Defect found by reading** ([#187](https://github.com/Heliogrim/Heliogrim-Engine/issues/187)): a removed physics model is destroyed (`_body = None`) but never erased, because erase waits for `owner() == nullptr` and nothing nulls the owner; the next `update()` dereferences the empty body.
- **Coherent combinations**: an evolved status quo; a structural log plus change ticks plus extract of changed objects (Bevy's split; render pipelines only with a wait at extract); a central log with value-carrying patches into the replicas (5.2a's direction; the only one that carries a free-running graphics cycle, needs per-subscriber coalescing). The second is in practice a prefix of the third; all share four first steps (lifetime fix, handles in models, per-system keys, setters for component state).
- **Job-level dependencies** (Destiny's job chains): stages stay the checked contract; jobs link through the existing waitables (`JoinCounter`, `Signal`), which no stage uses yet.
- **Spatial index**: a sparse voxel DAG encodes static occupancy, not moving objects; a central index read-only between updates contradicts "no stale transforms while user code runs" unless enlarged boxes with an escaped-object list or updates between tick groups are added; a single index for everyone conflicts with Jolt's and the GPU's own structures. A query facade over Jolt is the smallest option but covers only objects with bodies.

### 5.2c Network send in the loop (2026-11-15)

The question "send per simulation step or at an own rate" does not fit the tiered sync of the [agent-sync exploration](agent-sync-exploration.md) (W56.0: T0 self predicted, T1 engaged with a per-client dynamic list and a floating cap, actions scheduled on start tick `t + d` with a floating `d`, T2 interpolated, T3 dead-reckoned, T4 not replicated). Three outgoing classes have three triggers:

| Outgoing | Trigger | Budget | Slot |
|---|---|---|---|
| `ActionEvent` (T1, T2) | AI or player decides | taken from `d`; waiting for the end of a 30 Hz step costs up to 33 ms | flushed right after the deciding stage, inside the step |
| T0 ack and correction | the client's input was consumed | RTT, visible as correction | end of the step that consumed it |
| T2, T3 state | the network cycle | interpolation buffer or none | not in the step |

Agreed with the owner (2026-11-15):

- **Change marks are step numbers, not bits** (A). A mark stores the step (more precisely the sync epoch, see 5.2d) that last changed it; a consumer keeps its own last-seen value and reads `mark > lastSeen`. No consumer clears marks, so render, the network replica and later consumers read them at their own cadence; a lost packet leaves the connection's baseline where it is, and the next delta covers the gap by itself. Precedents: Unity Entities chunk change versions, flecs table counters, Bevy per-component ticks. Known failure of all three: write access counts as a change, so marks are set only by real writes, and the encoder's compare against the baseline catches the rest (Unity Netcode does the same byte compare).
- **The dirty marks are the replication sync point.** The scene's change log feeds two replicas, render (5.2a) and network.
- **Network replica in the Iris shape** (B): the end-of-step patch copies and quantises changed replicated state into the network replica (quantise once, not per connection); per-connection send reads only the replica, on the network cycle and the affine network thread (S55). Running that send concurrently with the next step has no documented precedent; it follows from the step budget (estimate: 1,000 connections × 300 entities × ~100 ns ≈ 30 ms, the whole 30 Hz step). Open in W56.1: double buffer or copy-on-write per chunk, so the patch of step s+1 does not overwrite what the send of step s reads.
- **The step therefore has two fixed network points**: the action-event and T0-ack flush after their stage, and the replica patch at the end of the step. Everything else belongs to the network cycle.
- **Client**: an input goes out right after the step that latched it, with the last few inputs repeated against loss; a per-frame send would add up to a frame to T0.

Measured in the W56.0 prototype before they are decided (no source measures server CPU for either):

- **C, send on perceived error**: the server runs the client's extrapolator per entity and connection and sends when the client's predicted error exceeds a threshold in the observer's space (screen angle, not world distance); the bandwidth budget steers the threshold, so tiers T1 to T3 become bands of one metric. Nearest prior art: Dyconits (ICDCS 2021, per-subscriber inconsistency bounds, 49 to 85% less bandwidth at about 200 players, PDF not read), AntReckoning (2013, up to 32% less upload), Roberts et al. 2008 (a purely spatial threshold leaves absolute error unbounded, so a time bound is needed). No peer-reviewed screen-space threshold was found.
- **D, encode once per (entity, baseline step)**: every client that has the entity in its set and acked that baseline reuses the same bytes; no zones, the per-client sets stay as W56.0 defines them. Shipped forms: Unity Netcode pre-serialisation (cost paid even when not sent), Unreal `net.ShareSerializedData`, ReplicationGraph FastShared. Iris creates baselines at most every 60 frames by default; reading that as rationed shared baselines is an inference. Trade-off: fewer encodes against larger deltas from older baselines.

### 5.2d Where change marks live (proposal, 2026-11-15, awaiting owner)

Found in the code (`master`, 2026-11-15): archetype slots live in `ClusterRegion` chunks of 16 KiB, each slot `[component block][actor]`, with a live mask per chunk and `RelocationTable`/`relocate()` for moved slots; legacy component pools use `hybrid_storage` pages of 32 KB. Component state has no write choke point: `HierarchyComponent::getLocalTransform()` returns a mutable reference, and the universe transform is derived on read through the parent chain.

| Place | For | Against |
|---|---|---|
| In the component | No lookup on write; same cache line as the data | A scan touches every slot at full stride; changes every component's layout; ties ACS objects to replication |
| **Side array per chunk** (one `u32` per slot and change group, beside the live mask) | Dense scan (16 marks per cache line); per-chunk skip possible; moves with the slot through the existing relocation path | Needs a chunk lookup on write; a second shape for the legacy pools |
| A system subscribing to the scene | No ACS change | Still needs a call on every write; a hash insert per write instead of a store; one shared structure for all writers |

Suggested: the side array, written only by setters. Details:

1. **Setters are the precondition.** The mutable `getLocalTransform()` reference goes; this is the "setters for component state" first step of 5.2b. A write is a value store plus a relaxed atomic store of the current epoch: no read-modify-write, unlike a bit.
2. **Change groups, not fields**: transform, render state, replicated gameplay state; schemas name the group of each field. Field-level difference comes from the encoder's baseline compare.
3. **Epochs, not bare steps.** Within a step, the pre-physics and post-physics broadcasts both see writes stamped with step s. An epoch counter advanced at each sync point (pre-physics broadcast, readback, post-physics broadcast) separates them; the step of an epoch is a small table. Physics sets its last-seen to the readback epoch, so its own readback writes do not echo back into Jolt, while post-physics user writes (later epoch) still reach it.
4. **No chunk-level mark at first.** Writers would contend on one cache line per chunk. Scanning all slot marks costs about 3.2 MB per scan at 100k entities × 8 groups, roughly 0.2 ms; only the two patchers scan the whole scene. Per-connection compares run against the network replica, which carries the step stamps it was patched with.
5. **Hierarchy**: a child's universe transform changes when an ancestor moves, without a write to the child. See 5.2e: subtree epochs upward, world resolved per consumer replica.

#### 5.2e Hierarchy: how others propagate, and a proposal (2026-11-15, awaiting owner)

Research pass (subagent, primary source code where public):

| Engine | Propagation | Descendants | Parallel | Consumers | Evidence |
|---|---|---|---|---|---|
| Bevy 0.16 to 0.18 | Batched pass per frame; `Transform` local, `GlobalTransform` world | A changed entity marks a zero-sized `TransformTreeChanged` **up** to the root, stopping at already-marked ancestors; unchanged subtrees are skipped; world written with `set_if_neq` | Roots via `par_iter`, work-sharing queue, parallel up-marking | `Changed<GlobalTransform>` ticks | source read |
| Godot 4 | World computed lazily on read, cached | Eager recursive dirty push, no early-out (O(subtree) per write) | Atomic dirty bits in thread groups | Once-per-node change list flushed at fixed points, opt-in | source read |
| Unity GameObject | Hierarchy buffer per root | Change messages to children and parents | Jobs per root (advice: about 50 objects per root) | Interest registration (`TransformChangeDispatch`), `hasChanged` | blog, docs |
| Unity Entities 1.3 | `LocalToWorldSystem` once per frame | Recursive descent per root | Jobs per root; large single roots discouraged | Chunk versions (unverified) | docs |
| Unreal | Eager cached `ComponentToWorld` | Recursive `UpdateChildTransforms` | Render send `_Concurrent` at frame end | Render dirty list; transform update re-adds the primitive ("expensive") | unverified, secondary |
| O3DE, CRYENGINE, VRage 1 | Eager | Recursive push (bus, `InvalidateTM`, `UpdateChildren`); VRage keeps world in double, local in float, early-out on equal matrix | None | Events with why-flags | source read |
| flecs | `cascade` query, breadth-first | Order only | Built-in | Per-table counters | docs |
| Bitsquid | SoA block, index links, eager recursion | Deferred variant keeps a parent-before-child array, dirty nodes sorted to the tail | n/a | "What moved since last frame" list | designer's blog 2014 |

No peer-reviewed or GDC work (2018+) on parallel or GPU scene-graph propagation was found. The known costs are Bevy's overhead on fully dynamic scenes and its reparenting bugs.

Every engine turns an ancestor write into a change of each descendant's *world* value: eagerly (Unreal, O3DE, CRYENGINE, VRage), in a pass (Bevy, Unity Entities), or as a dirty push with lazy reads (Godot). The consumers then see a world-value change per descendant. Moving a ship with 500 crew costs 501 world updates, 501 render updates and, if world state is replicated, 501 network entries.

**Proposal: locals are the only scene truth, consumers resolve world in their own replica.**

1. **Subtree epoch upward** (Bevy's mark as a number): a write stamps the slot's local epoch and raises `subtreeEpoch` on each ancestor until one already holds the current epoch. Unlike a bit, it is never cleared, and each consumer prunes at its own `lastSeen`: a subtree with `subtreeEpoch <= lastSeen` is skipped whole. That fits several consumers with different cadences, which a bit does not. Concurrent raisers within one epoch all store the same value, so a relaxed load-compare-store is enough. Epochs only advance at sync points without writers. `std::atomic::fetch_max` is C++26, so it is not used.
2. **Network replicates local transforms plus the parent link.** The client resolves world itself. An attached child generates no traffic when its parent moves. This needs interest management to include ancestors of replicated children (they are almost always in range anyway).
3. **Render patches carry local transform and parent, and the render replica resolves world.** It does that in a parent-before-child ordered array of its own, the Bitsquid layout: the scene's archetype chunks cannot be ordered by hierarchy, but a replica owns its layout. The pass is linear and parallel per root or per depth level, and only subtrees with a newer epoch are walked. A further step is a GPU compute pass per depth level from local transforms plus parent indices. That has no primary evidence, so it is a prototype item with a CPU baseline.
4. **Physics resolves world only for its bodies.** Dynamic bodies are almost always roots; kinematic children (doors on ships) take the chain from the physics patcher's own resolve.
5. **Gameplay reads during the step stay derived on read** (today's behaviour, never stale). An optional per-slot world cache would be valid while no ancestor on the path has a newer local epoch than the cache. Checking that is a walk of depth loads instead of depth matrix multiplies; measure before adding it.
6. **Large worlds**: roots hold double precision relative to their cell, children float relative to the parent (VRage's split). A moving ship is then one double root and float crew, with no precision loss for its crew.

Costs: interest management must follow parent links. Every consumer that needs world has its own resolve pass, so resolve logic is shared code across replicas. Reparenting and slot reuse are where Bevy's bugs were, so they need tests from the first commit. Moving a large tree is cheap for the scene and the network, and is paid once in each replica's resolve.

#### 5.2f Local-only truth: reasoning (2026-11-15, noted by the owner, not decided)

All numbers below are estimates from assumed sizes (100k scene objects, 20% moving per step, mean depth 3, affine multiply about 30 ns scalar). None is measured.

**Maintenance**

- *For*: the scene holds one truth per object. There is no cached world value, so there is no local/world coherence bug class in the scene.
- *Against*: every consumer that needs world values has a resolve pass. That is only maintainable as **one shared resolve library** used by render, physics, network client and editor, over (local, parent index, order) arrays and tested once. The order maintenance (reparent, insert, remove) is the hard code in it.
- Debugging: the scene shows locals only, so a debug helper resolves world on demand.
- Gameplay world setters (`setWorldLocation`) need the inverse of the parent's world, which is a chain walk.

**Memory**

| Where | Added per object | At 100k |
|---|---|---|
| Scene | `subtreeEpoch` (4 B) on top of 5.2d's local epochs | 0.4 MB |
| Render replica | world affine (48 B), parent index and order slot (8 B), beside the local it already needs | 5.6 MB |
| Network replica | parent id instead of world; locals quantise tighter (a ship interior of ±256 m at 1 mm is 19 bits per axis, against the cell range for world) | smaller than world-based |

Today the scene caches no world value, so there is nothing to remove there.

**CPU**

- *Write*: a local store, an epoch store, and the upward stamp, which stops at the first ancestor already stamped this epoch. That is amortised O(1) per ancestor per epoch. Worst case is the first write of a deep leaf: depth × (load, maybe store), each step likely a cache miss into another chunk. Many children stamping one root: the first store wins and later writers only load an equal value, so the line stays shared.
- *Resolve per consumer*: 20k changed × 30 ns ≈ 0.6 ms per full consumer, parallel per root. Eager world-in-scene does the same multiplies once but then ships world patches. A moving ship with 500 crew is 501 patches eagerly and 1 patch + 501 multiplies here; multiplies are cheaper than patches (copy, queue, coalesce).
- *Fully dynamic scenes*: the upward stamp is pure overhead, which is Bevy's measured weakness. Mitigation: count stamped slots per epoch; above a threshold, consumers resolve everything without pruning and writers skip the stamp. Bevy's merged PR used 30%; whether the number fits here needs a measurement.
- *Gameplay reads*: derived on read costs depth multiplies per call. Code that reads one world transform many times per step pays that each time; the epoch-validated cache from 5.2e point 5 is the answer if measurements ask for it.

**Latency**

- There is no extra frame: each consumer resolves while applying its patches.
- **Interpolation gets more correct**: interpolating locals and resolving with the interpolated parent at the same render time keeps crew on a rotating ship on the ship. Interpolating world positions cuts chords through the rotation.
- **Timeline mismatch is the new risk**: a child's world value is only right if child and parent are resolved at the same time. On a client, a predicted T0 player standing in a T2-interpolated ship lives on two timelines (prediction runs ahead by RTT/2, interpolation runs behind by the buffer), and the player visibly slides on the deck.

**Expected pitfalls**

1. **Reparenting** keeps world by recomputing local against the new parent's world (resolve needed in the scene at that moment; repeated reparenting drifts numerically). Both the old and new ancestor chains get stamped. Replicas move the subtree in their order arrays. Parent link and local must arrive in one patch, or one frame teleports.
2. **Slot reuse and relocation**: parent links in replicas are handles, never pointers; the scene's pointer links follow `RelocationTable`. A removed parent with live children needs a defined structural order (reparent to the grandparent or remove the subtree).
3. **Cycles**: rejected at reparent (assert plus diagnostic).
4. **Partial interest**: a replicated child without its parent cannot resolve, so interest is closed over ancestors.
5. **Concurrency**: `subtreeEpoch` and the marks are written through `std::atomic_ref<u32>` relaxed; correctness relies on epochs advancing only at stage barriers without writers. Stating that barrier as an assertion in the epoch advance keeps it checked.
6. **Deep chains**: skeletons in the scene hierarchy would make depth 50 to 100. Bones stay in animation's pose buffers, so the scene hierarchy is for attachment only.

**Constraints for further work**

- **W56.1 replication**: replicate locals plus parent link; interest is the ancestor closure; quantisation ranges per parent. **The sync tier of a parent is at least the tier of any predicted child for that client**: a player on a ship makes the ship T0 or T1 for that player, so both run on one timeline.
- **W57 server mesh**: authority follows the root of an attachment tree; a handover moves the whole tree, and a ship crossing a cell boundary is one migration, not one per crew member.
- **Render (5.2a)**: the patch is (local, parent handle, epoch); the render replica owns the order and interpolates locals; camera-relative floats are taken after resolving roots in double.
- **Physics (W34)**: Jolt bodies live in one world frame. Bodies inside a moving frame (crew in a ship) need a physics space per moving frame or a kinematic parent with relative simulation; readback converts world to local (a no-op for roots).
- **Animation (S36)**: skeletons stay outside the scene hierarchy.
- **ACS**: setters only (5.2d); parent link as a stable handle.
- **Editor**: gizmos edit world values and convert to local.
- **Tests**: reparent, slot reuse, relocation, parent removal, and an equivalence property test (replica resolve equals the scene's derived `getUniverseTransform`) from the first commit.

#### 5.2g Nested frames in shipped space games (research 2026-11-15)

| System | Frame model | Precision | Nested frames | Transform replication | Known pitfalls | Evidence |
|---|---|---|---|---|---|---|
| Star Citizen | Zone tree: a host (planet, station, ship, transit car) is an entity in its parent zone, up to a root that never moves; world position is accumulated from hosts and "rarely used" | 64-bit positions, one root per system; GPU 32-bit camera-relative | Yes: planet > station or ship > interior > transit car; a physics grid per zone | Per Entity Aggregate (ship plus crew), culled by proximity; wire frame not published | Grid transitions, players falling out of a docked ship on a moving carrier (2021), overlapping grids flipping membership, "30k" | Roberts interviews and monthly reports read; the zone-host developer quote only from a repost |
| EVE Online | Flat solar-system frame; bubbles (the "grid") are interest sets, not frames | Doubles assumed (third-party docs) | None | Deterministic Destiny on server and client at 1 Hz; snapshot plus commands | Desync from iteration order over subsets and an unsent previous-tick velocity; pre-tick (interest, serialisation) dominates, simulation under 10% | CCP dev blogs read; wire format only from emulators |
| Space Engineers (VRage 1) | Dynamic physics clusters of 50 to 100 km; positions relative to the cluster centre; no object within 2 km of a border | f64 game, f32 physics | No | Not covered | Jittering grids | designer's blog 2014 |
| KSP | Floating origin plus Krakensbane (velocity frame) | f32 | No | Single-player | "Kraken" | search snippet only |

What this changes in 5.2f:

1. **The model has a shipped precedent.** Star Citizen keeps positions relative to a zone host and treats world as a rarely used accumulation, with 64-bit roots. Their recurring bugs sit at **membership changes**, not at resolving: grids overlapping, transitions between grids that are not parent and child, docked ships on moving carriers.
2. **Reparenting needs a membership rule with hysteresis.** CIG added a grid type that skips inside/outside checks so that overlapping grids stop flipping their entities; Space Engineers keeps a 2 km margin. Here: a frame change is proposed by a membership volume with an enter/exit band and applied as one atomic structural record (new parent, new local, epoch); a transition between non-parent/child frames goes through their common ancestor in that one record.
3. **The attachment tree is the unit of streaming, interest and authority**, like CIG's Entity Aggregate. This confirms the W57 constraint: a ship is never split from its crew.
4. **Interest can be separate from frames** (EVE's bubbles in a flat frame), and interest recompute costs more than the simulation there. The ancestor closure from 5.2f is an addition to the interest policy, not a replacement of the spatial interest query.
5. **Replicating local state avoids EVE's desync class** of deterministic commands over a subset of objects. It matches W56.0, which keeps determinism to action evaluation.
6. **Float bound for children**: an offset of 1 km in float resolves to about 0.06 mm, and 10 km to about 1 mm. A ship interior larger than about 10 km, or a deep chain of large offsets, needs a double intermediate frame. The engine checks the extent against that bound.

Not found: CIG's transform wire format or bandwidth, CCP's internal float type, nested frames in EVE.

#### 5.2h Making the pitfalls unrepresentable (2026-11-15, proposal)

Rule: the parent link, the local transform and the epoch marks are private to the hierarchy. The only writers are a small node API, and every structural operation produces exactly one structural record. Per pitfall from 5.2f and 5.2g:

| Pitfall | Enforcement | Strength |
|---|---|---|
| Write without a mark | The mutable `getLocalTransform()` goes; `setLocal(...)` stamps the epoch | Type: unrepresentable |
| Torn reparent (parent arrives without its local) | `reparent(node, newParent, Keep::eWorld \| Keep::eLocal)` is the only way to change a parent; it emits one record (parent handle, local, epoch); replicas apply records whole | Type: unrepresentable |
| Stale parent after slot reuse or relocation | Links are generational `Handle`s (the existing `HandleTable`), never pointers in replicas; a stale handle resolves to invalid, never to another object | Type: alias unrepresentable; invalid is handled |
| Orphans when a parent dies | `destroy(node, Children::eReparentToGrandparent \| eDestroySubtree)` with no default | Type: no orphan state |
| Cycles | `reparent` walks the new parent's ancestors (O(depth)) and fails with a diagnostic | Runtime, at one choke point |
| Epoch advanced while writers run | Advancing needs a barrier token that only the scheduler's stage barrier constructs | Type: capability |
| Skeleton bones as scene nodes | Bones are not a node type; attachment to a bone is a socket (see the skeleton research) | Type |
| Depth explosion | Depth limit checked in `reparent` | Runtime |
| Child extent beyond the float bound (5.2g point 6) | Checked at attach and on extent growth; a frame above the bound must be a double frame | Runtime |
| Predicted child on an interpolated parent | The interest policy derives the parent's tier as max(tier of its children) for that client; it is computed, never configured | By construction in one policy |
| Child arriving before its parent on a client | The encoder sends the ancestor closure in parent-first order; a client that still sees an unknown parent holds the child invisible until the parent arrives | Protocol order plus a defined pending state |

What cannot be made unrepresentable, and what ships covered by tests:

- **Membership flapping** between overlapping frames is policy: enter/exit bands and the common-ancestor transition. Tests: an object oscillating on a boundary, and nested and overlapping frames.
- **Numerical drift from repeated `Keep::eWorld` reparents** is bounded per operation but accumulates. Tests: N round trips stay under the error bound.
- **Performance cliffs** (fully dynamic scenes, deep first writes): measurements and the pruning threshold, not types.

Conclusion: shipping with these pitfalls is safe if the node API is the only writer from the first commit. Each item labelled "Type" disappears as a bug class. The runtime checks sit at one or two choke points. The rest is policy plus tests.

#### 5.2i Skeletons and sockets (research 2026-11-15)

| Engine | Bones as | Socket | Update order | Evidence |
|---|---|---|---|---|
| Unreal | Bone buffer in `USkeletalMeshComponent` | `AttachToComponent` + socket name (bone + offset, on the skeleton or the mesh); Keep Relative / Keep World / Snap | Animation in PrePhysics; a reader that ticks before its source copies last frame's pose, so tick prerequisites are needed; Leader Pose shares one buffer | docs; finalize → child update unverified |
| Unity, default | One GameObject per bone | Parent to the bone object | Animator writes transforms | not re-read |
| Unity, Optimize Game Objects | Internal skeleton | "Extra Transforms to Expose" | After the animator; matrix extraction multithreaded | docs |
| Latios Kinemation | Entities (exposed) or buffer (optimized) | A socket entity copies the bone's root-space transform; the skeleton does not know its sockets; "relatively costly" | In the transform group | author's docs |
| Godot 4 | Indices in `Skeleton3D` | `BoneAttachment3D` copies on `skeleton_updated`; its override mode conflicts with modifiers | Deferred, once per frame; modifiers after the mixer, pose rolled back after skinning | docs, design article |
| O3DE | EMotionFX actor | Entity + joint + offset | Undocumented; the open PR #20176 reads the bind pose for multiplayer-safe sockets, because network input runs before animation | docs, PR |
| Bevy | Entities | Child of a bone entity | Transform propagation | issue #17114: joints duplicated per mesh to the GPU; shared skeletons unsolved; `extract_skinned_meshes` 15 ms for 501 models (PR #4428) |
| ozz-animation | SoA local pose, depth-first parent array | Model-space joint × offset, after `LocalToModelJob` | User's job | docs, sample |

Network: O3DE replicates animation-graph state (active states, play times, seed), not poses. No engine documents pose replication.

Frontier work found:

- Learned Motion Matching (Holden et al., TOG 2020): networks replace the database. A memory drop from about 600 MB to 9 MB is cited only from an author tweet.
- GPU hierarchy propagation for 10k characters (arXiv 2505.06703, 2025, abstract only).

Not found: studio pipeline talks (Guerrilla, Ubisoft, Naughty Dog), UAF design documents, skeleton LOD papers.

Consequences (proposal):

1. **Skeletons stay out of the scene hierarchy.** This matches Unreal, Godot 4, ozz and the optimized modes of Unity and Kinemation; Bevy shows the cost of bone entities. The pose lives in animation-owned SoA buffers (local pose; model-space for skinning, hit boxes and sockets). Meshes on one skeleton share one buffer (Leader Pose).
2. **A socket is a pull** of (skeleton, bone, offset), read in model space after the pose is final, and multiplied by the skeleton owner's frame in the consumer's resolve. The skeleton does not track its sockets. In the scene, a node attached to a socket has its skeleton-owning node as parent plus a socket reference. Its local is the bone's model transform times the offset, written by one socket-sync stage.
3. **"Pose final" is a scheduler dependency**, declared as an edge into the socket-sync stage: Unreal's one-frame copy and Godot's override conflict are both ordering bugs. Socket-sync writes the attached node's local through the node API (5.2h), so the marks and patches of 5.2d apply unchanged.
4. **Two poses**: the presented pose (render, cosmetic sockets) and a server pose for gameplay (hit boxes, gameplay sockets). The server pose comes from the deterministic action evaluation of W56.0 or the bind pose. Animation state is replicated (state, play time, seed, action events), never bones.
5. **Overrides** (IK, ragdoll) are stages after evaluation in a fixed order. Attachments never write back into a pose.
6. **Budget and LOD** apply to pose buffers, through rate, skipping and interpolation (Unreal's budget allocator), not to scene nodes.

Effect on scene update handling: structural changes stay in `SceneComponentQueue`, stamped with the epoch and applied before value patches of the same epoch. `broadcast(flags)` becomes "epoch e is sealed": each subscriber scans marks newer than its last-seen value and builds its patches. `update(flags)` then stops polling every model twice per frame.

### 5.3 UI and scenes rendered into each other

Break the cycle per texture, not per system. Each view is its own render node: a scene viewport, a UI surface, an in-world screen. A UI surface that shows a scene viewport depends on that viewport's render; a scene that shows a UI texture depends on that surface's render. Offscreen nodes render before the nodes that sample them (as URP does). Only a real cycle, a surface that contains itself through others, samples the previous frame's texture, and that edge is declared as one frame late rather than hidden. Reflow needs sizes and bounds, not pixels, so layout never closes the loop. The editor's case (material preview, scene preview, modelling tool inside the UI) is a fan-in with no latency. Where render command capture lives follows from this: recording belongs to the render node of each view, so the UI's recording is the render node of a UI surface, not a step of the Reflow tick.

### 5.4 Checking the order

Bevy reports pairs of systems with conflicting access and no order, and can shuffle the order of unordered systems in tests to expose orderings that are only correct by chance. Heliogrim's builder already rejects conflicting access without an edge; a shuffled serial order in the scheduler tests would be the cheap second check, given that the state-hash harness is deferred (W02.6).

## 6. Open questions

| Question | Options | Suggested |
|---|---|---|
| Render on a snapshot of the settled frame (5.2)? | Same frame; pipelined with Extract | **Owner direction 2026-11-14 (5.2a)**: no full copy; the scene's phase-flagged broadcasts feed differential patches into the render replica, and the graphics cycle runs on its own cadence across engine-loop stages. Open: the patch queue, coalescing, deferred removal and interpolation details |
| Simulation at a fixed step, decoupled from the frame (5.1)? | Variable step per frame (today); fixed step with catch-up and interpolation | **Decided (owner, 2026-11-14)**: both, selectable per project with both time sources (5.1d); arguments in 5.1a, effect on the loop in 5.1b; motion-blur sub-frames deferred |
| Network send per simulation step or per frame? | Per step; own rate; per trigger | **Decided (owner, 2026-11-15, 5.2c)**: per trigger. Action events and T0 acks flush inside the step; state goes from a quantised network replica patched at the end of each step, on the network cycle; change marks are step numbers and double as the replication sync point. Send on perceived error (C) and encode once per baseline (D) are measured in the W56.0 prototype |
| Where do change marks live? | In the component; side array per chunk; subscribing system | Side array per chunk, epochs, setters only (5.2d); awaiting owner |
| Where does the physics event queue live: physics readback or a stage of its own? | | Readback fills it, the callback stages drain it |
| Animation: who owns pose evaluation and IK, and on which slots? | | Evaluation after the pre-physics scene sync, IK after readback |

## 7. Next

Once the owner answers section 6, W02.11 continues: the stage sets per stage are agreed and written into the task graph design 8, then the edges after "world settled" are relaxed one at a time with the builder's conflict check. Stages that do not exist yet (animation, audio push, network) get their slots in the graph as declarations only when their systems land.

## 8. Not covered

Measured costs (Extract size, render CPU time per view, the simulation step cost) are not known; the frame pacing question (W02.9) interacts with 5.1 and 5.2.

## 9. Sources

| Source | Org or author | Year, venue | Status |
|---|---|---|---|
| [Actor Ticking](https://dev.epicgames.com/documentation/en-us/unreal-engine/actor-ticking-in-unreal-engine) | Epic | UE5 docs | verified |
| [Threaded Rendering](https://dev.epicgames.com/documentation/en-us/unreal-engine/threaded-rendering-in-unreal-engine) | Epic | UE docs | verified |
| [UE5 Migration Guide (async physics)](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-migration-guide) | Epic | UE5 docs | verified |
| [Animation Optimization](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-optimization-in-unreal-engine) | Epic | UE5 docs | verified |
| [Animation Budget Allocator](https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-budget-allocator-in-unreal-engine) | Epic | UE5 docs | verified |
| [IK Rig](https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-in-unreal-engine) | Epic | UE5 docs | verified |
| [Remote Procedure Calls](https://dev.epicgames.com/documentation/unreal-engine/remote-procedure-calls-in-unreal-engine) | Epic | UE5 docs | verified |
| [UNetDriver API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UNetDriver) | Epic | UE5 API | unverified |
| [Audio Mixer Overview](https://dev.epicgames.com/documentation/en-us/unreal-engine/audio-mixer-overview-in-unreal-engine) | Epic | UE5 docs | verified |
| [Physics Settings](https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-settings-in-the-unreal-engine-project-settings), [Physics Sub-Stepping](https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-sub-stepping-in-unreal-engine) | Epic | UE5 docs | verified |
| [Widget Components](https://dev.epicgames.com/documentation/en-us/unreal-engine/widget-components?application_version=4.27), [SceneCaptureComponent](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SceneCaptureComponent?application_version=5.5) | Epic | UE 4.27, 5.5 docs | verified |
| [Event function execution order](https://docs.unity.com/en-us/engine/current/manual/scripting/managing-update-order/execution-order), [PlayerLoop](https://docs.unity.com/en-us/engine/current/script-reference/unityengine/lowlevel/playerloop) | Unity | Unity 6 | verified (text; diagram not read) |
| [Fixed updates](https://docs.unity.com/en-us/engine/current/manual/scripting/managing-time-and-frame-rate/fixed-updates), [Handling variation in time](https://docs.unity.com/en-us/engine/current/manual/scripting/managing-time-and-frame-rate/time-handling-variations), [Time.maximumDeltaTime](https://docs.unity.com/en-us/engine/current/script-reference/unityengine/time/maximumdeltatime) | Unity | Unity 6 | verified |
| [AnimatorUpdateMode](https://docs.unity.com/en-us/engine/current/script-reference/unityengine/animatorupdatemode) | Unity | Unity 6 API | verified |
| [Avoid missed or duplicate discrete events](https://docs.unity3d.com/Packages/com.unity.inputsystem@1.12/manual/timing-missed-duplicate-events.html) | Unity | Input System 1.12 | verified |
| [Netcode for Entities API](https://docs.unity3d.com/Packages/com.unity.netcode@1.10/api/Unity.NetCode.html) | Unity | package 1.10 | verified |
| [Rendering to a Render Texture (URP)](https://docs.unity.com/en-us/engine/current/manual/cameras/urp/multiple/rendering-to-a-render-texture), [uGUI Auto Layout](https://docs.unity3d.com/Packages/com.unity.ugui@2.0/manual/UIAutoLayout.html), [Canvas.willRenderCanvases](https://docs.unity.com/en-us/engine/current/script-reference/unityengine/canvas/willrendercanvases) | Unity | Unity 6, uGUI 2.0 | verified |
| [Idle and physics processing](https://docs.godotengine.org/en/stable/tutorials/scripting/idle_and_physics_processing.html), [Physics interpolation](https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_introduction.html), [ProjectSettings](https://docs.godotengine.org/en/stable/classes/class_projectsettings.html) | Godot | Godot 4 docs | verified |
| [Main schedule](https://docs.rs/bevy/latest/bevy/app/struct.Main.html), [PipelinedRenderingPlugin](https://docs.rs/bevy/latest/bevy/render/pipelined_rendering/struct.PipelinedRenderingPlugin.html), [ScheduleBuildSettings](https://docs.rs/bevy/latest/bevy/ecs/schedule/struct.ScheduleBuildSettings.html) | Bevy | docs.rs | verified |
| [Parallelizing the Naughty Dog Engine Using Fibers](https://www.gdcvault.com/play/1022186/Parallelizing-the-Naughty-Dog-Engine) | C. Gyrling, Naughty Dog | GDC 2015 | verified (slides) |
| [Multithreading the Entire Destiny Engine](https://www.gdcvault.com/play/1022164/Multithreading-the-Entire-Destiny) | B. Genova, Bungie | GDC 2015 | verified (abstract) |
| [Destiny's Multithreaded Rendering Architecture](https://advances.realtimerendering.com/destiny/gdc_2015/Tatarchuk_GDC_2015__Destiny_Renderer_web.pdf) | N. Tatarchuk, Bungie | GDC 2015 | unverified (not fetched) |
| [FrameGraph in Frostbite](https://www.gdcvault.com/play/1024612/FrameGraph-Extensible-Rendering-Architecture-in) | Y. O'Donnell, EA | GDC 2017 | verified (abstract) |
| [Overwatch Gameplay Architecture and Netcode](https://www.gdcvault.com/play/1024001/-Overwatch-Gameplay-Architecture-and) | T. Ford, Blizzard | GDC 2017 | verified (abstract) |
| [Fix Your Timestep!](https://gafferongames.com/post/fix_your_timestep/), [State Synchronization](https://gafferongames.com/post/state_synchronization/) | G. Fiedler | 2004, 2015, gafferongames.com | verified |
| [Jolt PhysicsSystem](https://jrouwe.github.io/JoltPhysics/class_physics_system.html) | J. Rouwe | Jolt docs | verified |
| [Introducing Time Dilation](https://www.eveonline.com/news/view/introducing-time-dilation-tidi), [What a HED-ache](https://www.eveonline.com/news/view/what-a-hed-ache) | CCP Veritas | 2011, 2014, CCP dev blog | verified |
| FMOD Studio API, Wwise `RenderAudio` | Firelight, Audiokinetic | SDK docs | unverified (did not render) |
| [Entities version numbers](https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/systems-version-numbers.html) | Unity | Entities 1.3 | verified |
| [Netcode optimizations](https://docs.unity3d.com/Packages/com.unity.netcode@1.3/manual/optimizations.html), [serialization costs](https://docs.unity3d.com/Packages/com.unity.netcode@1.8/manual/optimization/manage-serialization-costs.html), [ghost snapshots](https://docs.unity3d.com/Packages/com.unity.netcode@1.3/manual/ghost-snapshots.html) | Unity | Netcode 1.3, 1.8 | verified |
| [Queries, change detection](https://www.flecs.dev/flecs/Queries.html) | S. Mertens | flecs docs | verified |
| [change_detection](https://docs.rs/bevy_ecs/latest/bevy_ecs/change_detection/index.html) | Bevy | docs.rs | verified |
| [Components of Iris](https://dev.epicgames.com/documentation/en-us/unreal-engine/components-of-iris-in-unreal-engine), [network debugging cvars](https://dev.epicgames.com/documentation/en-us/unreal-engine/console-commands-for-network-debugging-in-unreal-engine) | Epic | UE5 docs | verified |
| [Snapshot Compression](https://gafferongames.com/post/snapshot_compression/) | G. Fiedler | gafferongames.com | verified |
| [bevy_transform systems.rs](https://github.com/bevyengine/bevy/blob/main/crates/bevy_transform/src/systems.rs), PRs [#17840](https://github.com/bevyengine/bevy/pull/17840), [#18589](https://github.com/bevyengine/bevy/pull/18589), [#22281](https://github.com/bevyengine/bevy/pull/22281) | Bevy | 0.16 to 0.18 | verified (source) |
| [node_3d.cpp](https://github.com/godotengine/godot/blob/master/scene/3d/node_3d.cpp) | Godot | 4.x master | verified (source) |
| [Optimizing the hierarchy](https://unity.com/blog/technology/best-practices-from-the-spotlight-team-optimizing-the-hierarchy), [Entities transforms](https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/transforms-concepts.html) | Unity | 2017 blog; Entities 1.3 | verified (text) |
| [TransformComponent.cpp](https://github.com/o3de/o3de/blob/development/Code/Framework/AzFramework/AzFramework/Components/TransformComponent.cpp) | O3DE | development | verified (source) |
| [MyPositionComponent.cs](https://github.com/KeenSoftwareHouse/SpaceEngineers/blob/master/Sources/VRage.Game/Entity/EntityComponents/MyPositionComponent.cs) | Keen Software House | VRage 1, archived | verified (source); VRage 2 not public |
| CRYENGINE `Entity.cpp` (Lumberyard CryLegacy copy) | Crytek | CRYENGINE 5 era | verified (mirror, not official repo) |
| [Building a data-oriented entity system, part 4](https://bitsquid.blogspot.com/2014/10/building-data-oriented-entity-system.html) | N. Frykholm | 2014, Bitsquid blog | verified |
| [ECS back and forth, part 4](https://skypjack.github.io/2019-06-25-ecs-baf-part-4/) | M. Caini (EnTT) | 2019 | verified |
| Unreal `USceneComponent` propagation | Epic | UE4/5 | unverified (API pages did not load) |
| [Skeletal mesh sockets](https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletal-mesh-sockets-in-unreal-engine), [Modular characters](https://dev.epicgames.com/documentation/unreal-engine/modular-characters-in-unreal-engine?application_version=5.1) | Epic | UE5 docs | verified |
| [FBX importer rig tab](https://docs.unity.com/en-us/engine/current/manual/assets-and-media/asset-types/models/importing/fbximporter-rig) | Unity | Unity 6 | verified |
| [Kinemation docs](https://github.com/Dreaming381/Latios-Framework-Documentation) | Dreaming381 (author) | Latios Framework | verified |
| [Skeleton3D](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html), [SkeletonModifier3D design](https://godotengine.org/article/design-of-the-skeleton-modifier-3d/), [BoneAttachment3D](https://docs.godotengine.org/en/stable/classes/class_boneattachment3d.html) | Godot | 4.x | verified |
| [O3DE Attachment](https://docs.o3de.org/docs/user-guide/components/reference/animation/attachment/), [PR #20176](https://github.com/o3de/o3de/pull/20176) | O3DE | docs; open PR | verified |
| [bevy #17114](https://github.com/bevyengine/bevy/issues/17114), [#4428](https://github.com/bevyengine/bevy/pull/4428), [#17818](https://github.com/bevyengine/bevy/pull/17818) | Bevy | issues/PRs | verified (pointers to source) |
| [ozz-animation runtime](https://guillaumeblanc.github.io/ozz-animation/documentation/animation_runtime/), [attach sample](https://guillaumeblanc.github.io/ozz-animation/samples/attach/) | G. Blanc | docs | verified |
| [Learned Motion Matching](https://dl.acm.org/doi/pdf/10.1145/3386569.3392440) | Holden et al. | TOG 39(4) 2020 | verified (abstract) |
| [Multi-crew interview](https://gamersnexus.net/gg/2019-star-citizen-multi-crew-interview-chris-roberts) | C. Roberts, Gamers Nexus | 2015-07-21 | verified |
| [Letter from the Chairman](https://robertsspaceindustries.com/en/comm-link/transmission/14839-Letter-From-The-Chairman), [Monthly Report Aug 2014](https://robertsspaceindustries.com/en/comm-link/transmission/14126-Monthly-Report-August-2014), [Sep 2020](https://robertsspaceindustries.com/en/comm-link/transmission/17813-Star-Citizen-Monthly-Report-September-2020), [Mar 2021](https://robertsspaceindustries.com/en/comm-link/transmission/18076-Star-Citizen-Monthly-Report-March-2021) | CIG | 2014 to 2021 | verified |
| [Object Container Streaming](https://starcitizen.tools/Object_Container_Streaming) (quotes from Jump Point 07-10), [Server Meshing Q&A](https://api.star-citizen.wiki/comm-links/18397) | CIG via wiki mirrors | 2019, 2021 | secondary |
| [Drakes of Destiny](https://www.eveonline.com/article/fixing-lag-drakes-of-destiny-part-1-1/), [Facing Destiny](https://www.eveonline.com/article/facing-destiny), [Grid Sizes & You](https://www.eveonline.com/article/grid-sizes-you) | CCP | 2009, 2010, 2015 dev blogs | verified |
| [Super-large worlds](https://blog.marekrosa.org/2014/12/space-engineers-super-large-worlds_17/) | M. Rosa, Keen Software House | 2014 | verified |
| [Dyconits](https://atlarge-research.com/pdfs/icdcs21-dyconit-paper.pdf) | Donkervliet, Cuijpers, Iosup | ICDCS 2021 | unverified (PDF unreadable, numbers from summaries) |
| [AntReckoning](https://inria.hal.science/inria-00616877) | Yahyavi et al. | NetGames 2011; Multimedia Systems 19(3) 2013 | unverified (secondary) |
| [Time-space threshold dead reckoning](https://files01.core.ac.uk/download/pdf/297027794.pdf) | Roberts et al. | Simulation 84(5) 2008 | unverified (secondary) |
