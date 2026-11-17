# Work: Networking Transport, Replication, Server Mesh, Determinism and Replay

**Systems** S55, S56, S57, S59 · **Issues** [#135](https://github.com/Heliogrim/Heliogrim-Engine/issues/135), [#136](https://github.com/Heliogrim/Heliogrim-Engine/issues/136), [#137](https://github.com/Heliogrim/Heliogrim-Engine/issues/137) (To discuss), [#139](https://github.com/Heliogrim/Heliogrim-Engine/issues/139) · **Track** E · **Milestone** M3 (S59), M5, M6
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Networking and MMO](../topics/networking-mmo.md). The research behind S57 is the weakest in the plan; its chunks are prototypes before designs.

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Engine vision note | Single-shard MMO, no layering; Gemini's "lock-free state migration" and layering claims rejected as unsourced | S57 prototypes before design |
| [Concurrency work](concurrency-fibers.md) | Deterministic mode in the scheduler; affine network thread | S59 record and replay sit on W02.6, deferred 2026-11-13: the deterministic mode is planned with W59.1; only simulation state opts into a hash |
| [Storage work](storage-streaming.md) S40 | Cells, spatial index | Interest management and authority units |
| [Serialisation work](serialization-and-reflection.md) S01, S09 | Versioned records, replication attributes | Migration payload and schema source |
| [Physics work](physics-cloth.md) | Deterministic profile, worlds per cell group | Rollback tests and handover |
| [Agent-sync exploration](../../architecture/agent-sync-exploration.md) (W56.0) | Five sync tiers; "lock-step action evaluation" as server-scheduled action events; only action evaluation deterministic; no per-client server resimulation | Q56.2 to Q56.4; loopback prototype after W55.3 |
| [Build work](build-and-deploy.md) S58 | Server and cluster roles, orchestration contract | Nodes are cluster roles |
| [Procedural](procedural-generation.md), [ocean](ocean-fluids.md) | Deterministic math set | Owned by S59 |
| `Engine.Network` (48 lines), `Engine.Crypto` (CRC32) | Nothing to keep | New bundles |

## Architecture

- **Bundles**: `Engine.Network` rebuilt (sockets on an affine thread, `Transport` API), `Engine.Network.Quic` (vetted library wrapper: msquic, quiche or ngtcp2), `Engine.Network.Http` (HTTP/2 and HTTP/3 client, small server), `Engine.Network.Realtime` (custom UDP protocol), `Engine.Crypto` extended (AEAD, hashes). New `Engine.Replication` (scene system, schemas, snapshots, interest, prediction), `Engine.Cluster` (membership, authority, handover, persistence adapters), `Engine.Replay` (deterministic math set, state hashes, record and playback), `Engine.Determinism` as the strict-FP build profile and lint set.
- **Provides**: transport and HTTP; replicated state with prediction; multi-node authority; deterministic mode and replays.
- **Consumes**: scheduler and affine threads (S02), cells (S40), serialisation and reflection (S01, S09), physics determinism (S34), roles (S58), diagnostics (S05), trace (S04).

## Code design

| Type | Contract |
|---|---|
| `Transport` | One API over QUIC streams and the real-time UDP channel: `connect`, `send(channel, bytes)`, completions into waitables; sockets live on the network `AffineThread`. |
| `QuicSession` | Wrapper over the chosen library; TLS 1.3 built in; HTTP/3 and HTTP/2 clients on top; a small server for tooling. |
| `RealtimeChannel` | Connect tokens, AEAD (ChaCha20-Poly1305 or AES-GCM), replay protection, reliable-ordered and unreliable sub-channels, fragmentation, MTU discovery around 1,200 bytes; no unauthenticated packet is processed. QUIC datagrams (RFC 9221) as a measured alternative. |
| `ReplicationSystem : SceneSystem` | Mirrors components with replication attributes into a network model; `Schema` per type with quantisation ranges and priority per field, derived from reflection. |
| `SnapshotEncoder` | Acked-baseline deltas, per-entity priority accumulators under a bandwidth budget, smallest-three quaternions, bit packing then an arithmetic coder measured; shared by server and client. |
| `InterestPolicy` | Interface; grid default over the S40 spatial index; aura and priority later. Output per connection and entity: a `SyncTier` (T0 self, T1 engaged, T2 perceptive, T3 distant, T4 outside interest) per the [agent-sync exploration](../../architecture/agent-sync-exploration.md). T1 is chosen by interaction first (aggro, target, projectile) then distance, with hysteresis and a per-client cap (Q56.4). |
| `ActionEvent` | `{ actor, action id, start tick, parameters, seed }`; a replicated message class beside snapshots. The server schedules each combat action at `t + d` (Q56.2, Q56.3) so clients in range start it on the same tick; late remote-player actions start offset into the wind-up. Action evaluation (timeline, hit windows) is the only deterministic slice. |
| `Prediction` | T0: input buffering and reconciliation for the local actor and its mount, corrections smoothed over 100 to 250 ms. T1: short-horizon movement prediction (last input for players, replicated intent for agents) with bubble resimulation of entities near a correction. T2 and T3: interpolation and extrapolation. Tier switches smoothed. Server: capped lag compensation with a victim veto, hitbox history only, no per-client resimulation. |
| `Authority` | Data on the entity `{ ownerNode, lease }`; transfer is a transaction. |
| `CellHandover` | Overlap-zone ghosts read-only on neighbours; migration of serialised entity state (S01); duplicate-actor window measured. |
| `CellPersistence` | Journal plus periodic snapshot per cell through storage. |
| `LoadShedding` | Decided in W57.1: time dilation per cell, tick-rate degradation or admission limits. |
| `DeterminismScope` | ADR: (a) same-binary replay, (b) same-compiler cross-machine, (c) cross-platform bit-exact (not planned). |
| `DeterministicMath` | In-tree `sin`, `cos`, `exp`, `sqrt` for authoritative bundles; clang-tidy bans libm there; strict FP, no contraction. |
| `StateHash` | Per tick per simulation system; `Replay` records inputs, waitable completions and packets; playback asserts hashes and names the first divergent system. |

Placement: `Engine.Network/{Transport,Socket}`, `Engine.Network.Quic/`, `Engine.Network.Http/`, `Engine.Network.Realtime/`, `Engine.Replication/{ReplicationSystem,Schema,SnapshotEncoder,InterestPolicy,Prediction,Authority}`, `Engine.Cluster/{CellHandover,CellPersistence}`, `Engine.Replay/{DeterministicMath,StateHash,Replay}`. Tests: QUIC connect and HTTP/3 fetch; bytes per entity per tick at 1k, 10k, 100k entities; two-node handover without hitch; replay hash equality; deliberate FMA difference caught.

## Work chunks

### W59.0 Determinism scope decision · explore · ready

- **Goal**: write the ADR draft for scope (a), (b) or (c) with the costs each implies on the toolchain and the simulation bundles; list the bundles that must be deterministic. List combat action evaluation as its own deterministic slice: the W56.0 strategy needs scope (b) for it only, not for physics, animation or pathfinding.
- **Output**: ADR placeholder; section in `architecture/determinism-exploration.md`.
- **Questions**: Q59.1.

### W59.1 Replay design · design · after W59.0 (takes over the deterministic mode from W02.6, deferred 2026-11-13)

- **Goal**: deterministic math set, strict-FP profile and lint, state hash contract per system, record format (S01), playback and divergence report.
- **Output**: `architecture/replay-design.md`; plan.

### W59.2 Implement deterministic math, hashes, record and playback · execute · after W59.1

- **Done when**: a recorded session replays to identical hashes on the same binary; a deliberate FMA difference is caught.

### W55.0 QUIC library evaluation · explore · after W02.3

- **Goal**: msquic, quiche, ngtcp2 on licence, clang-cl build, IOCP behaviour, footprint; connect and fetch a file in a spike.
- **Output**: `architecture/transport-exploration.md`; answers Q55.1.

### W55.1 Transport design · design · after W55.0

- **Output**: `architecture/transport-design.md`; plan (sockets and QUIC first, HTTP second, real-time channel third).
- **Questions**: Q55.2.

### W55.2 Implement sockets, QUIC, HTTP/2 and HTTP/3 clients · execute · after W55.1, W02.2

- **Done when**: a client connects over QUIC and fetches an asset over HTTP/3 from a test server.

### W55.3 Implement the real-time UDP channel · execute · after W55.2

- **Done when**: authenticated reliable and unreliable channels pass loss and reorder tests; QUIC datagram comparison recorded.

### W56.0 Agent and player synchronisation strategy spike · explore · desk study done 2026-11-09; loopback prototype after W55.3

- **Result**: [agent-sync exploration](../../architecture/agent-sync-exploration.md). Recommends tiers T0 self (predicted), T1 engaged (capped, predicted, bubble resimulation), T2 perceptive (interpolated), T3 distant (reduced rate), T4 outside interest. "Lock-step action evaluation" becomes server-scheduled `ActionEvent`s on a shared tick timeline; only action evaluation must be deterministic (scope (b) for that slice). Three owner points open on that page (scheduled delay `d`, high-RTT players, T1 cap).

- **Goal**: work out the tiered strategy the owner asked for in Q37.2: client prediction with soft reconciliation, lock-step action evaluation for every agent and player inside the perceptive effective range, interpolation or coarser replication by distance; the perceived reaction latency per tier, the determinism each tier needs (ties to Q59.1), the cost per connected player; compare against pure server-authoritative agents.
- **Output**: `architecture/agent-sync-exploration.md` with the tier table and a recommendation; W56.1 and W37.1 read it.
- **Questions**: Q37.2 (decided as a spike), Q56.1.

### W56.1 Replication design · design · after W55.1, W56.0, W09.1, W40.1

- **Output**: `architecture/replication-design.md`; plan (schemas and snapshots first, interest and sync tiers second, action events and prediction third).
- **Input**: the tier table and recommendation in the [agent-sync exploration](../../architecture/agent-sync-exploration.md).
- **Questions**: Q56.1 to Q56.4.

### W56.2 Implement schemas, snapshots and interest · execute · after W56.1, W55.3, W40.2

- **Done when**: interest-managed snapshots flow; bytes per entity per tick recorded at 1k, 10k, 100k entities.

### W56.3 Implement prediction, reconciliation, lag compensation · execute · after W56.2, W34.2

### W57.0 Two-node handover prototype · explore · after W56.2, W58.2 (#137 is "To discuss")

- **Goal**: two server nodes, one shared cell boundary, a moving actor handed over under load; measure the duplicate window and the client-visible effect; prepare the owner's discussion with the numbers.
- **Output**: `architecture/server-mesh-exploration.md`.
- **Questions**: Q57.1, Q57.2.

### W57.1 Server mesh design · design · after W57.0 and the owner's decision

- **Goal**: authority and handover between nodes, dynamic sharding and node cooperation on cells and hyper-cell regions by player density (Q56.2), load shedding with the W57.0 measurements of dynamic cell splitting and cooperative buffering nodes (Q57.1), persistence journal (Q57.2).
- **Output**: `architecture/server-mesh-design.md`; plan.
- **Questions**: Q57.1, Q57.2 (both decided, see Decisions).

### W57.2 Implement authority, handover, persistence · execute · after W57.1

- **Done when**: two nodes hand over a moving actor with no visible hitch; a node crash recovers the cell from journal plus snapshot.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q55.1 | A C QUIC library under MIT or BSD is acceptable if it is frequently maintained, has a security reporting process in place, and is openly and widely adopted. The transport chunk checks these three criteria per candidate (for example msquic, ngtcp2, lsquic) before picking. |
| Q59.1 | (b) same compiler across machines for the simulation bundles, (a) same binary elsewhere. The agent-sync exploration narrows the (b) slice to action evaluation (combat resolution functions and action curves); physics, animation and pathfinding stay at (a). |
| Q55.2 | Custom UDP protocol first for the real-time channel. QUIC, HTTP/3, HTTP/2 and the web protocols exist for built-in support of OAuth, authentication, web statistics and similar services; they were never meant for game-critical transfer. |
| Q56.1 | Prediction scope: local actor and its mount (tier T0), for now. |
| Q56.2 | Scheduled-start delay `d` per cell from the 90th-percentile one-way delay of clients in range, clamped to 40 to 100 ms, as a floating value that adapts at runtime. The owner expects dynamic sharding and dynamic cooperation of server nodes on cells and hyper-cell regions driven by player density and other factors; W56.1 and W57.1 plan for that. Mass battles are the benchmark: reliability, effectiveness and perceived smoothness and sharpness must be measured there (W56.0 prototype, W57.0). |
| Q56.3 | Players whose link exceeds the cap see late actions; `d` never grows for everyone in range. In dense areas a growing `d` would stress the system and degrade gameplay for the whole group. |
| Q56.4 | Engaged-tier (T1) cap starts at 32 predicted non-local entities per client, as an adjustable floating value tuned by the prototype and at runtime. |
| Q57.1 | Tick-rate degradation with admission limits as the baseline. Two further candidates need measurement in W57.0 before W57.1 decides: splitting the overloaded cell dynamically into sub-cells, and cooperative nodes that buffer load for a hot cell. |
| Q57.2 | Own journal files through the storage system; an external database adapter interface is reserved. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q59.1 | Determinism scope: (a) same binary only, or (b) same compiler across machines (needed for rollback or lockstep)? | W59.1 | (b) for simulation bundles, (a) elsewhere |
| Q55.1 | QUIC library: is a C library under MIT or BSD (msquic, ngtcp2) acceptable as a platform-integration vendor? | W55.1 | Yes; W55.0 picks |
| Q55.2 | Real-time channel: build the custom UDP protocol first, or QUIC datagrams first with custom as the fallback? | W55.1 | Custom UDP first |
| Q56.1 | Prediction scope: local player actor only, or also vehicles and mounts? | W56.1 | Local actor and its mount |
| Q56.2 | Scheduled-start delay `d` for action events: one value per cell, or per client group? | W56.1 | Per cell, from the 90th-percentile one-way delay of clients in range, clamped to 40 to 100 ms |
| Q56.3 | Clients whose delay exceeds `d`: they see late actions, or `d` grows for everyone in range? | W56.1 | They see late actions; `d` never exceeds the cap |
| Q56.4 | Engaged-tier cap: how many predicted non-local entities per client? | W56.1 | 32, adjusted by the W56.0 prototype |
| Q57.1 | Load shedding policy: time dilation per cell, tick-rate degradation, or admission limits? | W57.1 | Tick-rate degradation with admission limits |
| Q57.2 | Persistence store: own journal files through storage, or an external database adapter from the start? | W57.1 | Own journal through storage; adapter interface reserved |
