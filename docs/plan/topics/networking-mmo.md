# Networking, Replication, MMO Server Mesh, Determinism and Replay

**Systems**: S55, S56, S57, S59 · **Track** E · **Milestone** M3, M5, M6
**Status**: <span class="hg-status summary">plan</span>. Research from [runtime](../sources/research-runtime.md) sections 3, 4 and 6 (RFC 9000 abstract, Fiedler's snapshot compression and floating-point determinism articles, UE5 large-world docs verified; MMO architecture claims are the weakest evidence in the whole plan).

## Target

- **Transport**: HTTPS, HTTP/2 and HTTP/3 over QUIC for control, assets and services; a custom reliable-unreliable UDP protocol with authenticated encryption and connect tokens for real-time state; one API over both.
- **Replication**: server-authoritative state with acked-baseline delta snapshots, quantisation from component schemas, interest management as a replaceable policy, per-entity priority budgets, client prediction and reconciliation, authority transfer.
- **MMO server mesh**: a single shard partitioned into cells with overlap zones; entity authority as data; seamless handover between nodes; journal-plus-snapshot persistence per cell; a load-shedding policy decided early.
- **Determinism and replay**: an explicit determinism scope; a fixed-step deterministic mode with strict floating point; replays recorded from the command and replication stream, used by tests and for debugging.

## Current state (checked 2026-11-07)

- `Engine.Network`: 48 lines. `Engine.Crypto`: CRC32. No sockets, TLS, QUIC, replication or replay.
- Transforms are float; the scheduler is not deterministic; physics determinism is off.

## Research summary

- QUIC (RFC 9000, abstract verified): flow-controlled streams, low-latency establishment, connection migration, built-in TLS 1.3; companions RFC 9001, 9002, 9221 (unreliable datagrams), HTTP/3 RFC 9114, HTTP/2 RFC 9113, DTLS 1.3 RFC 9147 (unverified).
- Snapshot compression (Fiedler, verified): delta against the last acked baseline, bounded quantisation, smallest-three quaternions; 901 cubes from 17.4 Mbps to about 15 kbps idle against a 256 kbps target; an arithmetic coder beat bit packing by about 25%.
- Overwatch (GDC 2017), Halo Reach priority replication (GDC 2011), Quake 3 delta snapshots, GGPO rollback: unverified references.
- Large-world coordinates (verified): double on the CPU, camera-relative floats on the GPU.
- Interest management (Boulanger et al. 2006), overlap-zone handover (Colyseus NSDI 2006), EVE's one node per solar system with time dilation, SpatialOS worker authority, Star Citizen server meshing: all unverified and partly marketing-grade.
- Floating-point determinism (Fiedler, verified): same compiler, flags and ISA as the baseline; strict FP; x87 control word pinned; FMA contraction, approximate reciprocals and libm break cross-machine results; CPU-speed-dependent iteration counts break replays.
- Agones (verified) targets session servers; a stateful single shard may need its own orchestration.

## Guidance

### S55 Networking transport

- `Engine.Network` as sockets on an affine network thread (S02) with completions into waitables; TLS and QUIC through a vetted platform-integration library (msquic, quiche or ngtcp2 evaluated for licence, Windows IOCP behaviour and footprint); HTTP/2 and HTTP/3 clients and a small server for tooling; HTTPS for services.
- Real-time channel: a custom UDP protocol in-house (connect tokens, AEAD encryption with ChaCha20-Poly1305 or AES-GCM, replay protection, reliable-ordered and unreliable channels, fragmentation, MTU discovery around 1,200 bytes); QUIC datagrams (RFC 9221) evaluated as an alternative and kept as a fallback for restrictive networks.
- Security from the first version: no unauthenticated packet is processed; inputs are validated with diagnostics.

### S56 Replication

- Replication is a scene system mirroring components marked for replication (reflection attributes, S09) into a network model; schemas define quantisation ranges and priority per field.
- Snapshots: acked-baseline deltas with per-entity priority accumulators under a bandwidth budget; a schema-driven encoder shared by server and client; an arithmetic coder after bit packing is measured.
- Interest management: a policy interface (grid default; aura or priority later) fed by the same spatial index as streaming residency (S40), so streaming and replication share one query.
- Client prediction with input buffering and server reconciliation for the local actor; interpolation for others; lag compensation on the server.
- Authority is data on the entity (owner node, lease); transfer is a transaction between nodes (S57).

### S57 MMO server mesh

- Cells (S40) are the unit of authority; a node owns a set of cells; overlap zones ghost entities read-only on neighbours; handover is a transactional migration of the entity's serialised state (S01) with duplicate-actor windows measured.
- Persistence: journal plus periodic snapshot per cell through the storage layer; entity serialisation doubles as the migration payload.
- Load shedding decided up front: time dilation per cell (EVE-style), tick-rate degradation or admission limits per cell; hot spots are a known failure of any partition.
- Prototype first: two nodes, one shared cell boundary, handover under load; the research is too weak to design beyond that without measurements.

### S59 Determinism and replay

- Scope decision as an ADR: (a) same-binary replay (required for tests), (b) same-compiler cross-machine (required for rollback or lockstep), (c) cross-platform bit-exact (not planned).
- Simulation bundles compile with strict FP and no contraction; a clang-tidy check bans libm transcendentals there in favour of in-tree implementations (shared with S33 and S30); the scheduler's deterministic mode (S02) and Jolt's deterministic profile (S34) are enabled together.
- State hash per tick exposed by every simulation system; a replay records inputs, waitable completions and received packets; playback asserts hashes and reports the first divergent system.
- Replays are the recorder for netcode debugging and for workflow tests (S54).

## Done when

- A client connects over QUIC, fetches an asset over HTTP/3 and receives interest-managed snapshots on the UDP channel; bytes per entity per tick and encoder CPU are recorded at 1k, 10k and 100k entities.
- Two server nodes hand over a moving actor with no client-visible hitch; a node crash recovers the cell from journal plus snapshot.
- A recorded session replays to identical hashes across runs on the same binary; a deliberate FMA difference is caught by the hash harness.

## Open decisions

- QUIC library choice.
- Custom UDP versus QUIC datagrams after measurement.
- Determinism scope (a), (b) or (c).
- Orchestration (Agones versus StatefulSets).
