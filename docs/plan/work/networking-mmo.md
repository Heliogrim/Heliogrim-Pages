# Work: Networking Transport, Replication, Server Mesh, Determinism and Replay

**Systems** S55, S56, S57, S59 · **Issues** [#135](https://github.com/Heliogrim/Heliogrim-Engine/issues/135), [#136](https://github.com/Heliogrim/Heliogrim-Engine/issues/136), [#137](https://github.com/Heliogrim/Heliogrim-Engine/issues/137) (To discuss), [#139](https://github.com/Heliogrim/Heliogrim-Engine/issues/139) · **Track** E · **Milestone** M3 (S59), M5, M6
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Networking and MMO](../topics/networking-mmo.md). The research behind S57 is the weakest in the plan; its chunks are prototypes before designs.

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| Engine vision note | Single-shard MMO, no layering; Gemini's "lock-free state migration" and layering claims rejected as unsourced | S57 prototypes before design |
| [Concurrency work](concurrency-fibers.md) | Deterministic mode in the scheduler; affine network thread | S59 record and replay sit on W02.6 |
| [Storage work](storage-streaming.md) S40 | Cells, spatial index | Interest management and authority units |
| [Serialisation work](serialization-and-reflection.md) S01, S09 | Versioned records, replication attributes | Migration payload and schema source |
| [Physics work](physics-cloth.md) | Deterministic profile, worlds per cell group | Rollback tests and handover |
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
| `InterestPolicy` | Interface; grid default over the S40 spatial index; aura and priority later. |
| `Prediction` | Input buffering and reconciliation for the local actor; interpolation for others; server lag compensation. |
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

- **Goal**: write the ADR draft for scope (a), (b) or (c) with the costs each implies on the toolchain and the simulation bundles; list the bundles that must be deterministic.
- **Output**: ADR placeholder; section in `architecture/determinism-exploration.md`.
- **Questions**: Q59.1.

### W59.1 Replay design · design · after W59.0, W02.6

- **Goal**: deterministic math set, strict-FP profile and lint, state hash contract per system, record format (S01), playback and divergence report.
- **Output**: `architecture/replay-design.md`; plan.

### W59.2 Implement deterministic math, hashes, record and playback · execute · after W59.1, W02.6

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

### W56.1 Replication design · design · after W55.1, W09.1, W40.1

- **Output**: `architecture/replication-design.md`; plan (schemas and snapshots first, interest second, prediction third).
- **Questions**: Q56.1.

### W56.2 Implement schemas, snapshots and interest · execute · after W56.1, W55.3, W40.2

- **Done when**: interest-managed snapshots flow; bytes per entity per tick recorded at 1k, 10k, 100k entities.

### W56.3 Implement prediction, reconciliation, lag compensation · execute · after W56.2, W34.2

### W57.0 Two-node handover prototype · explore · after W56.2, W58.2 (#137 is "To discuss")

- **Goal**: two server nodes, one shared cell boundary, a moving actor handed over under load; measure the duplicate window and the client-visible effect; prepare the owner's discussion with the numbers.
- **Output**: `architecture/server-mesh-exploration.md`.
- **Questions**: Q57.1, Q57.2.

### W57.1 Server mesh design · design · after W57.0 and the owner's decision

### W57.2 Implement authority, handover, persistence · execute · after W57.1

- **Done when**: two nodes hand over a moving actor with no visible hitch; a node crash recovers the cell from journal plus snapshot.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q55.1 | A C QUIC library under MIT or BSD is acceptable if it is frequently maintained, has a security reporting process in place, and is openly and widely adopted. The transport chunk checks these three criteria per candidate (for example msquic, ngtcp2, lsquic) before picking. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q59.1 | Determinism scope: (a) same binary only, or (b) same compiler across machines (needed for rollback or lockstep)? | W59.1 | (b) for simulation bundles, (a) elsewhere |
| Q55.1 | QUIC library: is a C library under MIT or BSD (msquic, ngtcp2) acceptable as a platform-integration vendor? | W55.1 | Yes; W55.0 picks |
| Q55.2 | Real-time channel: build the custom UDP protocol first, or QUIC datagrams first with custom as the fallback? | W55.1 | Custom UDP first |
| Q56.1 | Prediction scope: local player actor only, or also vehicles and mounts? | W56.1 | Local actor and its mount |
| Q57.1 | Load shedding policy: time dilation per cell, tick-rate degradation, or admission limits? | W57.1 | Tick-rate degradation with admission limits |
| Q57.2 | Persistence store: own journal files through storage, or an external database adapter from the start? | W57.1 | Own journal through storage; adapter interface reserved |
