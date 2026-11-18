# Cross-object mutation semantics in parallel engines (desk research, 2026-11-18)

Labels: **[verified]** = read in the primary source during this session. **[summary]** = a secondary write-up of a primary source, or a primary source paraphrased by a search summary. **[unverified]** = from memory or forum posts, not traced.
Grounding: actor-system.md §4 (dynamic resolver, sort key (source handle, per-source counter), cap semantics) and §8.4 (no ordering guarantee); engine-loop-exploration.md §5.2k (per-thread buffers, one sorted batch per step, gameplay drains it, impulse accumulator).

## 1. Engine survey

| Engine | How user code mutates another object | Execution context / order guarantee |
|---|---|---|
| **Unity MonoBehaviour** | Direct member calls, effective immediately | One main thread. Script Execution Order sorts *classes* by integer; unlisted scripts run in "Default Time", "after any scripts with negative values and before any scripts with positive values". The order between instances of the same class is not configurable [verified] |
| **Unity Jobs / Entities** | Jobs write only their declared NativeContainers. Structural or cross-entity changes go through `EntityCommandBuffer`, with `ParallelWriter` in parallel jobs | Recording order is "non-deterministic because they depend on job scheduling". Each command takes an int sort key; "Unity always plays back commands with larger sort keys after commands with smaller sort keys". "If the recorded sort keys are independent from the scheduling, then the sorting makes the playback order deterministic". The recommended key is `ChunkIndexInQuery`. Playback is single-threaded. The docs say determinism "can have an impact on performance" [verified]. Tie-break for equal keys across threads: [unverified] |
| **Unreal Actor/Component Tick, Blueprint** | Direct calls, effective immediately | Tick groups run strictly in sequence: "Each tick group will finish ... before the next tick group begins". No order within a group. `AddTickPrerequisiteActor/Component` is the only way to sequence ticks within a group [verified]. Ticks run on the game thread by default. With `bRunOnAnyThread` they run "in parallel with the game thread"; UObject access is then unsafe, and Epic Japan (CEDEC 2021) shows the resulting data races and fixes them with prerequisites [summary] |
| **Unreal Mass** | `Context.Defer()` returns an `FMassCommandBuffer` (AddTag, RemoveFragment, DestroyEntity, `PushCommand<>`). Direct entity-manager mutation inside `ForEachEntityChunk` is UB | Processors are ordered by `ExecuteInGroup/Before/After` and run on the task system unless `bRequiresGameThreadExecution` [summary]. Flush point and ordering of the flush: not found in official docs [unverified]. UE 5.7 batches observer calls during the flush [summary, third party] |
| **Unreal Chaos async physics** | `AsyncPhysicsTickComponent`, or `Chaos::TSimCallbackObject<Input,Output>` with input and output structs marshalled between the game thread and the physics thread | Epic staff say AsyncPhysicsTick still runs on the game thread once per physics step. Custom sim callbacks run on the physics thread and write through `GetPhysicsThreadAPI()` [summary, forum + 3rd-party] |
| **Godot** | Direct calls on the main thread. From workers: `call_deferred` / `set_deferred`, because "Interacting with the active scene tree is **not** thread-safe" | Deferred calls run at idle time, "mainly at the end of process and physics frames". Calls deferred from the same thread run in the same order they were deferred. They are drained "until there are none left", so a deferred call that defers itself recurses without end [verified]. No cross-thread order is stated |
| **Bevy** | `Commands` (deferred), `&mut World` exclusive systems, `World::trigger` (immediate), `Commands::trigger` (deferred), component hooks | Commands are "applied in sequence when the `ApplyDeferred` system runs". `auto_insert_apply_deferred` adds sync points between systems that are ordered and have deferred params. `ambiguity_detection` can log, warn on, or error on "systems with conflicting access but indeterminate order". Observers run when their trigger is applied, and nested triggers are evaluated recursively "until there are no commands left" [verified]. The cross-system order of `ApplyDeferred` (system index order): [unverified] |
| **flecs** | Outside `progress()`, writes are immediate. Inside, the world is readonly and add/remove/set "are enqueued as commands". Writes to queried fields are immediate | Each thread has its own stage (command queue). A table is sliced per thread, so "the same entity is always processed by the same thread, until the next sync point". Sync points are inserted where a later system reads what an `[out]` system writes. Immediate systems are single-threaded [verified]. `flecs_stage_merge` flushes stages in ascending index order `for (i = 0; i < count; i ++)` [verified in src/stage.c]. Consequence: deterministic only for a fixed thread count [inference] |
| **O3DE / Lumberyard** (shares CRYENGINE heritage) | EBus: synchronous events (dispatched "with no latency", a return value is possible) or queued events "from various threads for safe execution on another thread" | The default bus is single-threaded (`NullMutex`, asserts under multithreaded use). Mutex, shared or lockless dispatch are opt-in [verified]. Order of the queue: FIFO in the queue [unverified]. CRYENGINE entity update: game thread [unverified] |
| **VRage (Space Engineers)** | Mods use `MyAPIGateway.Utilities.InvokeOnGameThread`, a queue "processed at the beginning of each tick". Engine code uses `MySandboxGame.Invoke` | Mod `UpdateBeforeSimulation` and similar methods ran on the main thread (guide circa 2017). Newer builds have `MyParallelEntityUpdateOrchestrator`, so mod callbacks can fire from parallel paths [summary: Keen forum guide + crash logs] |
| **Snowdrop (Massive)** | No public talk found on gameplay mutation rules | Interview: systems are built on a task scheduler with dependencies. GDC 2024 (Avatar FoP): 13 short-task and 13 long-task threads; "~60% executing NPC graph", fixed by moving logic into gameplay systems, which can need "fine-grained locking" [summary]. That suggests a lock-based design, not deferral [inference] |
| **Roblox Parallel Luau** | Desynchronized phase: reads only; writes need `task.synchronize()`. Per-member tags: Unsafe / Read Parallel / **Local Safe** ("usable within the same Actor; other actors may only read") / Safe | "Scripts that are part of the same actor always execute sequentially". The engine "detects and blocks" unsafe accesses at runtime. The docs show a re-check after synchronizing (`hitPart.Parent`) so two actors do not destroy the same part, i.e. user-level ghost handling [verified] |
| **Overwatch ECS** (GDC 2017, Ford) | Systems hold behaviour and no state. Side effects are recorded in singleton components and carried out by one later system ("deferment") | Fixed system order on a deterministic simulation [summary from talk listing + translations; deferment details unverified] |
| **Factorio** | Engine-internal threads (belts, FFF #364): threads may not wake inserters directly; they append wake requests, and "the main thread ... wakes up the entities in a deterministic way based on the group update order number" | The groups are partitioned so that no two groups interact. FFF #415: a desync caused by the CPU core count. FFF #421: electric-network threading was abandoned because it was memory-bound [verified #364, summary #415/#421] |

## 2. Language/API enforcement and per-sender order

- **Readonly views plus write interfaces.** Roblox enforces this per member at runtime. flecs uses readonly world mode plus stages. Bevy enforces it at the type level (`Query<&T>` versus `Commands`), and the scheduler derives conflicts from access sets. Unity Jobs check `[ReadOnly]` NativeContainers with safety handles in the editor [summary].
- **Actor frameworks.** Erlang guarantees order only between a *pair* of processes. Relaying A→B→C loses it, and messages may be dropped on a node disconnect (Niskanen, Armstrong, Hebert on erlang-questions) [summary]. CAF does not guarantee order in distributed settings. Local mailboxes are FIFO, but high-priority messages go to a separate queue, and skipped messages are handled later, so processing order can differ from arrival order [summary]. Orleans runs single-threaded turns per grain and is non-reentrant by default. Cycles deadlock, and Orleans reports them as timeouts. `[Reentrant]`, `[AlwaysInterleave]`, `[ReadOnly]` and `AllowCallChainReentrancy` relax this [verified].
- **"A writes B.x several times, then calls B.f()".** Per-sender order holds when all of A's intents to B go into **one ordered channel** (Erlang pair FIFO, Godot same-thread deferred order, Unity ECB within one key, a flecs stage) and are applied in that order. A sort on `(target?, source, seq)` keeps it. A sort on `(kind, …)` (§5.2k's physics sort) does **not** keep it for mixed kinds. Calls that B.f() makes into C are new intents with source B, so they apply in the next micro-cycle; order across hops is not transitive (Hebert, CAF paper).
- **Costs.**
  - Latency: one barrier, which means the end of the stage in Bevy and flecs, and the next frame for Godot idle and VRage.
  - Memory: one record per write (opcode, target handle, payload; closures are worse).
  - Single-threaded playback: Unity and flecs both say so.
  - No read-your-writes: flecs documents `has → add → has` returning false inside a system [verified]. Bevy documents queues that are never flushed, which leave entities "allocated but never spawned" [verified].
- **Ergonomics complaints.** You cannot see your own writes. Spawned entities are placeholders until playback (Unity deferred entities). Debugging loses the call stack at playback. Recursion is unbounded without a cap: Godot drains "until none left", Bevy flushes observers recursively [verified].

## 3. Deterministic application across parallel producers

- **Unity ECB**: a scheduling-independent sort key, sorted at playback [verified].
- **Factorio**: per-thread request lists, merged on the main thread by a static group order number [verified].
- **flecs**: a fixed entity→thread slice plus merge in stage index order; deterministic only for a fixed worker count [verified code + inference].
- **Bevy**: no claim about cross-system order. It offers ambiguity detection instead [verified].
- **Erlang**: per pair only.
- None of the surveyed engines documents a key made of *source handle + per-source counter* that stays independent of worker count. The closest is Unity's `ChunkIndexInQuery`, which changes when chunks are rearranged. That validates the §4.3 caveat.

## 4. Candidate models for Heliogrim

**(a) Deep-readonly cross-access plus a recorded intent interface, applied at the resolver barrier.**
- How it works:
  - `other.read()` returns a const view.
  - `other.mutate()` returns a proxy whose calls record `(target handle, source handle, source seq, micro-cycle, op)` into a thread-local buffer.
  - The barrier validates generations (dropping ghosts), sorts by `(target, source, seq)` and applies.
  - The per-target groups can be applied in parallel.
- Pros:
  - Deterministic regardless of worker count.
  - Ghost-free.
  - Matches §4.2 and the §5.2k pattern.
  - Per-sender order holds by construction.
- Cons:
  - No read-your-writes on other actors.
  - One micro-cycle of latency per hop.
  - Record memory.
  - Every mutating member needs a recordable form, which means codegen or a reflection opcode per method.
  - Conflicting writers from different sources resolve by sort order (last writer by key wins). That is deterministic but arbitrary, so commutative channels (the impulse accumulator) are the better fit where possible.

**(b) Events only.** The target owns all of its writes and reacts to typed events in its own tick.
- Pros:
  - Simplest invariants.
  - The target controls validation.
  - Fits networking (action events).
- Cons:
  - A call becomes event plus handler: verbose, a stringly or variant-heavy API, a latency of one tick per hop, and no return values.
  - Ordering still needs the same sort key, so it is (a) without the API sugar.

**(c) Immediate writes only on your own actor/archetype slot, plus declared access sets checked by the task graph.**
- How it works: a tick may write its own components freely. Cross-actor writes need a declared write set, and the builder serialises conflicting tasks, like Bevy access sets, flecs `[out]` and Unreal prerequisites.
- Pros:
  - Zero latency.
  - No buffers.
  - Familiar Unity/Unreal feel inside one actor, like Roblox "Local Safe".
- Cons:
  - Cross-actor writes on dynamic targets (whoever I hit) cannot be declared statically.
  - Serialising them destroys parallelism.
  - Nondeterminism remains unless the builder fixes the order (Bevy only *detects* ambiguity).
  - Ghosts are possible.

**Recommended blend [inference]:**
- Use (c) for the own slot.
- Use (a) for every cross-actor write.
- Use commutative accumulator channels (§5.2k impulses) where an op commutes; they need no sort.
- Use (b) for the physics, network and audio fan-out that already exists.

**C++23 enforcement mechanisms and their holes**

| Mechanism | Enforces | Hole |
|---|---|---|
| `const T&` / `ref<const T>` view | No direct member writes | `mutable` members, `const_cast`, shallow const: `T*` members stay mutable through a const object |
| Proxy view type exposing only const getters | Deep const for the members it exposes | Getters that return raw pointers or refs to nested non-const data. Maintenance cost per type |
| `std::experimental::propagate_const` (LFTS v2, not in std C++23) | Deep const through pointer members | Not standard (libstdc++ ships it; MSVC STL does not [unverified]). Each pointer member must be wrapped |
| Deducing `this` (`template<class Self> auto get(this Self&& self)`) | One accessor yields a const or non-const result depending on the view | Only follows the constness of the view; no help if the view is non-const |
| Access token / passkey (`MutateToken` constructible only by the scheduler for the own slot) | Mutating API callable only with a token | Tokens can be stored or leaked unless they are non-copyable and scope-bound. Escapes via globals |
| Debug runtime checks (thread-local "current actor", generation and epoch asserts on write) | Catches what the type system misses (`const_cast`, pointers) | Debug-only cost. Coverage-dependent |

Practical note: no C++ mechanism closes `const_cast` or `mutable`. Use type-level views for the common path, a review lens or clang-tidy rule for `const_cast` and `mutable` in components, and debug write-guards (owner-actor check), the same layered approach Unity uses with its job safety handles.

## References

| Topic | URL | Label |
|---|---|---|
| Unity ECB playback + sort keys | https://docs.unity3d.com/Packages/com.unity.entities@1.3/manual/systems-entity-command-buffer-playback.html | verified |
| Unity Script Execution Order | https://docs.unity.com/en-us/engine/current/manual/unity-editor/editor-settings-reference/comp-manager-group/class-mono-manager | verified |
| Unreal actor ticking | https://dev.epicgames.com/documentation/en-us/unreal-engine/actor-ticking-in-unreal-engine | verified |
| Unreal FTickFunction bRunOnAnyThread | https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/FTickFunction ; https://voithos.io/articles/fancier-ticking-in-unreal/ ; https://www.docswell.com/s/EpicGamesJapan/5QMWWK-UE4_CEDECKYUSHU2021_MultiThread | summary |
| Unreal Mass processors / Defer | https://github.com/Megafunk/MassSample/blob/main/README.md ; https://www.yawlighthouse.com/blog/ue-mass-processors/ | summary |
| Unreal async physics tick | https://forums.unrealengine.com/t/is-async-physics-tick-really-async/2353151 ; https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UActorComponent/AsyncPhysicsTickComponent | summary |
| Godot thread-safe APIs | https://docs.godotengine.org/en/stable/tutorials/performance/thread_safe_apis.html | verified |
| Godot Object.call_deferred | https://docs.godotengine.org/en/stable/classes/class_object.html | verified |
| Bevy Commands | https://docs.rs/bevy/latest/bevy/ecs/system/struct.Commands.html | verified |
| Bevy ScheduleBuildSettings (ambiguity, apply_deferred) | https://docs.rs/bevy/latest/bevy/ecs/schedule/struct.ScheduleBuildSettings.html | verified |
| Bevy Observer | https://docs.rs/bevy/latest/bevy/ecs/observer/struct.Observer.html | verified |
| flecs Systems (staging, sync points) | https://www.flecs.dev/flecs/Systems.html | verified |
| flecs stage merge | https://github.com/SanderMertens/flecs/blob/master/src/stage.c | verified |
| O3DE EBus in depth | https://docs.o3de.org/docs/user-guide/programming/messaging/ebus-design/ | verified |
| Space Engineers parallel modding | https://forum.keenswh.com/threads/parallel-modding-guide.7396636/ ; https://github.com/KeenSoftwareHouse/SpaceEngineers/blob/master/Sources/Sandbox.Game/MySandboxGame.cs | summary |
| Snowdrop GDC 2024 | https://media.gdcvault.com/gdc2024/Slides/GDC+slide+presentations/Simmons_Joshua_Upgrading_the_Snowdrop.pdf ; https://www.tomshardware.com/reviews/multi-core-cpu-scaling-directx-11,4768-7.html | summary |
| Roblox Parallel Luau | https://create.roblox.com/docs/scripting/multithreading | verified |
| Overwatch GDC 2017 | https://gdcvault.com/play/1024001/-Overwatch-Gameplay-Architecture-and | summary |
| Factorio FFF #364 / #415 / #421 | https://factorio.com/blog/post/fff-364 ; https://www.factorio.com/blog/post/fff-415 ; https://www.factorio.com/blog/post/fff-421 | verified / summary / summary |
| Erlang pair ordering | http://erlang.org/pipermail/erlang-questions/2017-September/093666.html ; http://erlang.org/pipermail/erlang-questions/2017-January/091505.html | summary |
| CAF ordering | https://actor-framework.readthedocs.io/en/0.17.5/MessagePassing.html ; https://arxiv.org/pdf/1810.00401 | summary |
| Orleans request scheduling | https://learn.microsoft.com/en-us/dotnet/orleans/grains/request-scheduling | verified |

Not checked: the Unity ECB tie-break for equal keys, the Mass flush point, Bevy's cross-system `ApplyDeferred` order, Overwatch deferment details from the video itself, CRYENGINE entity threading, and MSVC `propagate_const`.
