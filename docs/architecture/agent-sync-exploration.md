# Agent and Player Synchronisation (Exploration)

**Status**: <span class="hg-status exploration">exploration</span>. Nothing here is decided. This is the desk-study half of spike W56.0 on the [networking work page](../plan/work/networking-mmo.md). The loopback prototype half waits for the real-time channel (W55.3). Accepted parts move into the [replication design](../plan/work/networking-mmo.md) (W56.1), the [navigation design](../plan/work/navigation.md) (W37.1) and an ADR.

**Origin**: written 2026-11-09 from the owner's answer to Q37.2 and two research passes. Evidence levels are marked per source: **[full]** primary text read, **[abstract]** abstract, author page or official docs page only, **[secondary]** a citing paper, write-up or search excerpt, **[unverified]** recalled but not confirmed. Most paper PDFs and all talk videos were unreadable or unwatched in this pass. Any number below without **[full]** is a pointer, not a measurement.

## 1. The question

Q37.2 rejected server-only agents with interpolated poses. The 100 to 200 ms visible reaction latency is too slow for snappy, partly fast-paced combat. The owner asked for a tiered strategy with three parts:

- client prediction with soft reconciliation;
- lock-step action evaluation for every agent and player inside the perceptive effective range;
- cheaper replication by distance.

This page works out what each tier is, the latency each tier shows the player, the determinism each tier needs, and the cost per connected player. It then compares the result against pure server authority.

Assumptions (no owner answer yet; stated so they can be rejected):

- RTT 50 to 150 ms in the target region. Server tick 30 Hz, client simulation tick 60 Hz.
- Q56.1 uses its suggested default: the local actor and its mount are predicted.
- Q59.1 uses its suggested default: scope (b) for simulation bundles, (a) elsewhere. Section 5 narrows what "simulation bundle" must mean here.

## 2. Evidence

### 2.1 Latency people notice

| Source | What it says | Level |
|---|---|---|
| Claypool and Claypool, CACM 49(11), 2006 | Precision-deadline model. Rough thresholds: first-person avatar about 100 ms, third-person avatar about 500 ms, omnipresent about 1,000 ms. The 500 ms third-person figure comes from tab-target EverQuest 2 melee. | [abstract] |
| Claypool et al., moving-target selection, MMM 2017, TOMM 2018, MMSys 2019 | Selection time rises steeply with delay and target speed; roughly 4x worse over 50 to 300 ms. | [abstract] |
| Long and Gutwin, 2018 | Fast targets suffer from about 50 ms; slow targets tolerate about 150 ms. | [secondary] |
| Raaen and Grønli, NIK 2014 (survey) | The common "100 ms" figure is inconsistent across studies; the fastest games need less. | [abstract] |
| Cronin et al., TSS, 2002 and 2004 | Rollbacks under 100 ms went unnoticed by most players (informal test). | [abstract] |
| Bettner and Terrano, GDC 2001 (Age of Empires) | 250 ms command latency unnoticed in an RTS; jitter felt worse than a steady 500 ms. | [full] |
| Schmid and Halbhuber, 2023 | Fighting games need frame-exact input, but small latency variation did not change performance. | [abstract] |

Reading for this genre: action melee behaves like the first-person and fast-target rows, not like the third-person row. Budget about 50 ms for anything the player triggers or must react to, and up to about 100 ms for corrections the player only sees. No peer-reviewed study of action melee (combo or dodge) latency was found. **This is the evidence gap the loopback prototype must close.**

### 2.2 Techniques

The Liu, Xu and Claypool survey (ACM Computing Surveys 54(11s), 2022, [abstract]) sorts more than 80 papers into four groups:

- **feedback**: concealment, exposure;
- **prediction**: self-prediction, prediction of others by interpolation or extrapolation, speculative execution;
- **time manipulation**: incoming delay (local lag), outgoing delay, time warp;
- **world adjustment**: control assistance, attribute scaling.

What industry calls lag compensation is time warp in this taxonomy. Each part of the owner's request maps onto it:

| Owner's term | Taxonomy | Origin and key property |
|---|---|---|
| Client prediction with soft reconciliation | Self-prediction plus smoothed correction | Bernier, Valve, GDC 2001 [secondary]; Overwatch, GDC 2017 [secondary]: the client runs ahead by RTT/2 plus one command frame and replays unacked inputs on correction. |
| Lock-step action evaluation in range | Incoming delay plus time warp | Bucket synchronisation (Diot and Gautier, IEEE Network 1999, [abstract]); local lag and timewarp (Mauve et al., IEEE Trans. Multimedia 2004, [abstract]); Trailing State Synchronization (Cronin et al., [abstract]). All three need deterministic replay of operations. |
| Cheaper replication by distance | Interpolation, extrapolation, relevance and priority | DIS dead reckoning (IEEE 1278.1: send on error over a threshold, heartbeat otherwise, [secondary]); Pantel and Wolf, NetGames 2002: first-order extrapolation often beats second-order ([abstract]). |

Classic lock-step adds the full delay to the player's own input: 200 ms turns in Age of Empires [full]. This genre cannot afford that. "Lock-step" here therefore has to mean that remote actions are evaluated on a shared tick timeline. It cannot mean that local input waits.

### 2.3 Shipped precedents

| System | How tiers or the predicted set are chosen | Determinism | Level |
|---|---|---|---|
| Photon Quantum | Every client runs the full simulation. "Prediction culling" predicts only entities inside a sphere or view; culled entities advance on verified frames only. | Strict; one RNG stream per cullable entity | [abstract] official docs |
| Unity Netcode for Entities | Ghosts are interpolated by default; predicted or owner-predicted on demand. Prediction switching by radius around the controlled character. Timeline jumps can exceed 2x ping and are smoothed by a lerp over a set duration. Importance per tile times ticks since last send fills the packet. Irrelevant ghosts despawn. | None; predicted fields are backed up and restored | [abstract] official docs |
| Unreal Chaos networked physics | Predictive interpolation (cheap) or resimulation. Experimental physics replication LOD switches between them by distance to focal points; bubble resim replays only objects near a desync. | "Good enough that one resim does not trigger another" | [abstract] overview docs; LOD details [secondary] |
| Unreal Mover / Network Prediction | Only the autonomous proxy is predicted; simulated proxies are interpolated. | Not required | [abstract] |
| Unreal Iris | Per-object float priority from prioritiser objects (sphere, owner boost); relevancy is a filter. | n/a | [abstract] |
| For Honor (Ubisoft) | Peer-to-peer deterministic simulation with rollback: 8 players, about 100 NPCs, "8 times the gameplay in a single frame". The soldier crowd runs inside the deterministic simulation; duel-capable fighters use a separate replicated decision system. | Strict for the crowd; desync bugs named as the main cost | [abstract] GDC 2017 and 2019 |
| Rocket League | Predicts all cars and the ball and resimulates the whole world on correction; physics state replicated because Bullet drifts. 6 to 8 bodies only. | Not deterministic | [secondary] |
| Mortal Kombat / Injustice 2 | Rollback of up to 8 frames in 16 ms; typically 1 to 3 frames. | Strict | [abstract] |
| EVE Online | Time dilation down to about 10% under overload, per node. Not prediction; a safety valve. | n/a | [secondary] dev blog |
| New World (AWS) | 7 hub servers per world, more than 7,000 AI and 2,500 players; no combat netcode published. | unknown | [secondary] marketing-grade |

No source publishes server CPU per player for rewind or resimulation. The standard server-authoritative designs (Unity, Unreal, Overwatch) do not resimulate per client on the server. Rewind is confined to hit queries; resimulation is a client cost.

## 3. The insight that makes the middle tier cheap

An NPC's reaction time is a design value. Players expect roughly human reaction: a telegraphed wind-up and a decision delay. The proposal is to spend part of that delay on the network instead of showing it.

The server decides an action at tick `t` and stamps it with a start tick `t + d`, where `d` covers the one-way delay plus jitter for every client in range (`d` around 50 to 90 ms at 100 ms RTT). Every client in range receives the action event before `t + d` and starts it on the same tick. The wind-up, the hit window and the recovery then run on one shared timeline on every machine. That is lock-step on actions, not on the whole simulation. It is incoming delay (local lag) applied only to remote decisions.

- **NPC actions** show no network latency at all when `d` covers the link. The cost is that the NPC's reaction to a player grows by `RTT/2 + d`, about 100 to 140 ms at 100 ms RTT. That fits inside a designed reaction time of 200 ms or more if the AI's own think delay is shortened by the same amount. *Inference, not sourced; the prototype must confirm it feels right.*
- **Remote players' actions** cannot be scheduled ahead: the player pressed the button already. Their action event arrives about `RTT/2 + d_server` late. The receiving client starts the action time-shifted: it skips or compresses the first frames of the wind-up so that the hit window lands on the server tick. The cost is a slightly shorter visible telegraph on remote players. Fighting-game rollback does the same, within its 1 to 3 frame typical depth.
- **Hit resolution** stays on the server against the shared action timeline. Lag compensation is capped. A victim veto (Lee and Chang, MMSys 2018, [abstract]: 94% fewer "shot behind cover" cases) keeps "hit after I dodged" rare.

What must be deterministic is small: given `(action id, start tick, parameters, seed, the actor's start pose)`, the action timeline and its hit windows must evaluate identically on every machine. That is the combat resolution functions and the action curves. It is not physics, not animation blending, not pathfinding.

## 4. Tier table

| Tier | Who | Selection | Client does | Perceived latency (100 ms RTT) | Determinism needed |
|---|---|---|---|---|---|
| **T0 Self** | Local actor and its mount (Q56.1 default) | Always | Predicts from local input; buffers inputs; reconciles to server state by replaying unacked inputs; smooths corrections over 100 to 250 ms and snaps only above a distance threshold | 0 ms for own actions; corrections usually below the ~100 ms notice level | None bit-exact; the "one correction must not trigger another" bar |
| **T1 Engaged** | Current target, attackers in melee or near-ranged reach, projectiles aimed at or fired by the player; mounts the player is fighting | Interaction first (aggro, target, threat), then distance; hysteresis band; hard cap per client (starting point 16 to 32, to be measured) | Actions on the shared timeline (section 3); short-horizon movement prediction (other players: repeat last input; NPCs: continue the replicated intent, such as a path segment or a dash target); rollback only of T1 entities near a correction (bubble resimulation) | NPC actions 0 ms; remote player actions shown on time with a shortened wind-up; movement corrections ≤ about 100 ms | Action evaluation (section 3); per-entity RNG streams, not a shared RNG |
| **T2 Perceptive** | Everything inside the perceptive effective range that is not engaged | Distance or view inside the interest set | Interpolates poses at full rate; starts action events on their start tick so animations and sounds line up | Poses: one interpolation buffer (about 2 ticks, 33 to 66 ms) behind the server; actions on time | Action evaluation only, for presentation (no gameplay effect on the client) |
| **T3 Distant** | Visible beyond the perceptive range | Priority accumulator under the bandwidth budget | Lower update rate; first-order extrapolation with error threshold plus heartbeat (DIS style); actions as coarse state ("attacking") | Hundreds of ms; not noticed at distance (assumption) | None |
| **T4 Outside interest** | Everything else | Interest policy | Not replicated | n/a | None |

Transitions between tiers follow Unity and Unreal practice. They need hysteresis, and the switch is smoothed because a predicted and an interpolated timeline differ by up to two times ping. Promotion to T1 happens when interaction starts: aggro, targeting, or a projectile launch. It does not happen on distance alone, so a crowd walking past does not fill the cap.

## 5. Cost per connected player

| Where | T0 | T1 | T2 | T3 |
|---|---|---|---|---|
| Server CPU | Input buffer, validation | Hitbox history ring (about 250 ms) behind a broadphase that bounds each entity's recent movement (Overwatch style, [secondary]); action scheduling | Interest and priority | Priority accumulator |
| Server bandwidth | Acks, corrections | Action events (a few bytes each) plus short intents; replaces pose streams for actions | Snapshots at full rate | Snapshots at reduced rate |
| Client CPU | Replay of unacked inputs (≈ RTT / tick + 1 steps, about 7 at 60 Hz and 100 ms) | `N_T1 × rollback depth × step cost`; at a cap of 32 and depth 7 that is about 224 entity steps per correction, so bubble resimulation keeps it bounded | Interpolation | Extrapolation |

The server never resimulates per client. That keeps the server cost per player close to a plain server-authoritative design. The new server-side costs are the action scheduler and the hitbox history.

On determinism, scope (b) from Q59.1 is needed only for the action evaluation functions. Those are small, pure and testable by state hash. Movement, physics and animation stay non-deterministic and are corrected by reconciliation. This is the main difference from For Honor and Photon Quantum, whose whole-simulation determinism produced their dominant bug class.

## 6. Comparison with pure server authority

| | Server-only, interpolated (rejected default) | Tiered (this page) |
|---|---|---|
| NPC attack visible after the server decides it | RTT/2 + interpolation buffer, about 100 to 150 ms | 0 ms (scheduled start), when `d` covers the link |
| NPC reaction to a player action | RTT + interpolation + AI think time | RTT/2 + `d` + AI think time, with think time shortened to compensate |
| Own action feedback | 0 ms if the local actor is predicted, RTT otherwise | 0 ms |
| Remote player action | RTT/2 + interpolation, late hit window | On time with a shortened wind-up |
| Server CPU | Baseline | Baseline plus scheduler plus hitbox history |
| Determinism | None | Action evaluation only |
| Engineering risk | Low | Medium: tier switching, smoothing, the cap, an action timeline format |

## 7. Recommendation

1. Adopt four replicated tiers (T0 to T3) plus T4, with **action scheduling on a shared tick timeline** as the meaning of "lock-step action evaluation". Do not run a lock-step or rollback simulation of the whole perceptive range.
2. Make combat actions data with a start tick: `ActionEvent { actor, action id, start tick, parameters, seed }`. Their evaluation is the only state that has to be deterministic. Scope (b) applies to that slice.
3. Bound T1 by interaction first, with a per-client cap, hysteresis and bubble resimulation; T2 and T3 by the interest policy and priority accumulators already in the replication plan.
4. Keep the server free of per-client resimulation; cap lag compensation and add a victim veto.
5. Keep EVE-style time dilation per cell as the overload valve. That decision belongs to Q57.1.

### Consequences for other chunks

- **W56.1 replication design**: add `ActionEvent` as a replicated message class beside snapshots; add a `SyncTier` per entity per connection to `InterestPolicy` output; prediction switching with smoothing in `Prediction`.
- **W37.1 navigation design**: agent state must replicate *intent* (current path segment, target, speed) in addition to pose, so T1 can continue movement. AI decisions go out as scheduled actions.
- **W59.0 determinism scope**: list action evaluation as a deterministic slice in its own right, separate from physics and the whole simulation.
- **W34.1 physics**: no physics determinism is required by this strategy; the adaptive body tiers stay independent.
- **Animation (S36)**: actions need start-offset playback (begin mid-wind-up) and per-action hit-window data.

## 8. Prototype (after W55.3)

Loopback on one machine with injected delay, jitter and loss (50, 100, 150 ms RTT; 10 ms jitter; 1% loss). Measure:

1. visible error and correction count for T0 at each RTT;
2. NPC attack start error against the server timeline for a range of `d`;
3. remote player hit-window alignment and visible wind-up shortening;
4. client resimulation cost against the T1 cap (16, 32, 64);
5. a blind A/B by the owner: server-only against tiered, the same encounter, latency fixed.

Numbers go into this page with the hardware stated.

## 9. Open points for the owner (Batch 6 on the [questions page](../plan/work/questions.md))

- **Q56.2 Scheduled-start delay `d`**: one value per cell, or per client group (worst link in range)? Default suggestion: per cell, from the 90th-percentile one-way delay of clients in range, clamped to 40 to 100 ms.
- **Q56.3 Players with high RTT**: when `d` would exceed the cap, do those players see late NPC actions (fair to everyone else) or does `d` grow for everyone in range? Default suggestion: they see late actions; `d` never exceeds the cap.
- **Q56.4 T1 cap**: start at 32 predicted non-local entities per client; adjust from the prototype.

## Sources

- Liu, Xu, Claypool, *A Survey and Taxonomy of Latency Compensation Techniques for Network Computer Games*, ACM Computing Surveys 54(11s), 2022, [doi:10.1145/3519023](https://dl.acm.org/doi/10.1145/3519023); [taxonomy pages](https://web.cs.wpi.edu/~claypool/papers/lag-taxonomy/LatencyCompensation.html)
- Mauve, Vogel, Hilt, Effelsberg, *Local-Lag and Timewarp*, IEEE Trans. Multimedia 6(1), 2004 ([listing](https://www.researchgate.net/publication/3424171_Local-Lag_and_Timewarp_Providing_Consistency_for_Replicated_Continuous_Applications))
- Cronin, Filstrup, Kurc, Jamin, *Trailing State Synchronization*, Multimedia Tools and Applications 23, 2004 ([Springer](https://link.springer.com/article/10.1023/B:MTAP.0000026839.31028.9f))
- Diot, Gautier, *A distributed architecture for multiplayer interactive applications on the Internet*, IEEE Network 13(4), 1999 ([ACM](https://dl.acm.org/doi/10.1109/65.777437))
- Bettner, Terrano, *1500 Archers on a 28.8*, GDC 2001 ([text](https://www.gamedeveloper.com/programming/1500-archers-on-a-28-8-network-programming-in-age-of-empires-and-beyond))
- Claypool, Claypool, *Latency and Player Actions in Online Games*, CACM 49(11), 2006 ([page](http://web.cs.wpi.edu/~claypool/papers/precision-deadline/)); Claypool et al., delay and moving targets ([page](http://web.cs.wpi.edu/~claypool/papers/delay-motion/))
- Raaen, Grønli, NIK 2014 ([article](https://www.ntnu.no/ojs/index.php/nikt/article/view/5252)); Schmid, Halbhuber, 2023 ([PDF](https://epub.uni-regensburg.de/55003/1/schmid_halbhuber_latency_variation_2023.pdf))
- Pantel, Wolf, *On the suitability of dead reckoning schemes for games*, NetGames 2002 ([ACM](https://dl.acm.org/doi/10.1145/566500.566512)); IEEE 1278.1 dead reckoning ([open-dis summary](https://github.com/open-dis/dis-tutorial/wiki/Dead-Reckoning))
- Bernier, *Latency Compensating Methods in Client/Server In-game Protocol Design and Optimization*, GDC 2001 ([PDF](https://www.gamedevs.org/uploads/latency-compensation-in-client-server-protocols.pdf)); Lee, Chang, *advanced lag compensation*, MMSys 2018 ([ACM](https://dl.acm.org/doi/10.1145/3204949.3204971))
- Photon Quantum: [prediction culling](https://doc.photonengine.com/quantum/current/manual/prediction-culling), [frames](https://doc.photonengine.com/quantum/current/manual/frames)
- Unity Netcode for Entities: [prediction switching](https://docs.unity3d.com/Packages/com.unity.netcode@1.10/manual/prediction-switching.html), [ghost optimisation](https://docs.unity3d.com/Packages/com.unity.netcode@1.9/manual/optimization/optimize-ghosts.html)
- Unreal: [networked physics](https://dev.epicgames.com/documentation/en-us/unreal-engine/networked-physics-overview), [Mover examples](https://dev.epicgames.com/documentation/en-us/unreal-engine/mover-examples-in-unreal-engine), [Iris prioritisation](https://dev.epicgames.com/documentation/en-us/unreal-engine/iris-prioritization-in-unreal-engine)
- GDC Vault: [Overwatch 2017](https://www.gdcvault.com/play/1024001/), [Rocket League 2018](https://www.gdcvault.com/play/1024972/), [For Honor AI 2017](https://www.gdcvault.com/play/1024035/), [For Honor 2019](https://www.gdcvault.com/play/1026322/), [Mortal Kombat rollback 2018](https://gdcvault.com/play/1025021/), [Halo: Reach 2011](https://gdcvault.com/play/1014346/)
- EVE [time dilation](https://www.eveonline.com/news/view/time-dilation-hows-that-going) [secondary]; New World [AWS blog](https://aws.amazon.com/blogs/gametech/the-unique-architecture-behind-amazon-games-seamless-mmo-new-world) [secondary, marketing-grade]

Not read in this pass: the talk videos, the Rocket League slides, the Valve developer wiki page, the Korean NDC talks, the Albion Online talk. Bernier's exact wording and the Mauve experiment values come from excerpts.
