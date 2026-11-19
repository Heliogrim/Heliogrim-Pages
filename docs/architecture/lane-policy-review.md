# Scheduler Lanes and Priority (Owner Review)

**Status**: review sheet, 2026-11-18. Work chunk [W02.14](../plan/work/concurrency-fibers.md), issue [#84](https://github.com/Heliogrim/Heliogrim-Engine/issues/84), draft PR [#208](https://github.com/Heliogrim/Heliogrim-Engine/pull/208) into `feat/wip` (ten signed commits: nine plan tasks and a profiling workload that was added after the reviews and is itself unreviewed). The [design](lane-policy-design.md) was built on `feat/lane-policy` in one autonomous run while the owner was away. This page lists what the owner has to decide, every ruling that was made on the owner's behalf during the run, and what is left to do. Nothing here is decided by the owner yet. Revise a ruling by writing the new decision into its row; the row says what code it touches.

Sources: the [design](lane-policy-design.md) (sections 15.1 to 15.6 hold the numbers), the [prior-art record](lane-policy-exploration.md) section 6, the plan `docs/superpowers/plans/2026-11-18-lane-policy.md` and the run ledger `.superpowers/sdd/2026-11-18-lane-policy/progress.md` in the engine checkout (both untracked).

## 1. Decisions for the owner

Each has a suggested default. "Measured" refers to the Debug build on the 5900X; see design 15.

| ID | Question | What is known | Suggested default |
|---|---|---|---|
| Q02.11 | The reserve is clamped to `workers - 1`. On 3 workers the fan-out bound (completion p99 within 1.5 times idle) fails under lower work that never yields: 1.41 ms against 1.23 ms. Lift the clamp to all workers, or accept? | Lifting it leaves lower work only its floor turns on small machines (8 ms and 100 ms periods); not measured. Accepting means the bound depends on `checkpoint()` in long tasks | Accept for now; measure the lifted clamp once long tasks call `checkpoint()` (Q02.15) |
| Q02.12 | Frame wait limit default: 100 µs or 250 µs? | At 100 µs the wait trigger lifts the reserve to 19 of 20 workers under flood. 250 µs: about 20 % more Background throughput on 20 workers, no measured frame cost, three runs. No effect on 3 workers | 250 µs |
| Q02.13 | The wait trigger adds one worker per observed wait with no limit per frame. Cap it? | Reviewer suggestion: at most one raise per frame, or cap at the observed fan-out peak plus one. Fixed reserve 8 (the benchmark's fan-out width) gave 32 % more Background throughput at a slightly worse non-cooperating pickup | One raise per frame; re-measure with Q02.12 |
| Q02.14 | Wake-up at a fan-out is a chain: a worker that pops wakes one peer, which pops and wakes one, and so on, so N helpers arrive after N hops. Wake two per pop (a tree, N helpers after about log2 N hops), or wake `min(k, parked)` at a push of k tasks? | Owner note 2026-11-18. Kernel wake is 5 to 10 µs per hop. Measured fan-out pickup p99 for 8 children on 20 idle workers: 103 to 240 µs. A wake at every Frame push from a worker (`wakeOnFramePush`, off) did not lower pickup beyond the spread in one run per point but lowered the per-frame maximum Frame wait at p99 from about 160 to 220 µs down to 29 to 49 µs. Rayon wakes `min(k, sleepers)` directly; Tokio and Go chain through spinning workers. An extra wake is a spurious return in `Schedule.tla`; a changed wake rule needs the model re-run. While only reserve-blocked lower work is queued, each pop already costs one futile wake | Explore as chunk W02.15: two wakes per pop while two or more tasks are queued, against direct `min(k, parked)`, measured on fan-out pickup |
| Q02.15 | Nothing in the engine calls `hg::checkpoint()`. Which long tasks get it first? | Until they do, every lower-lane task is a non-cooperating one and the reserve is the only protection. Debug builds log the first overrun per lane; the owner's editor run lists the offenders | Importers and shader compiles first, one issue per offender from the editor run |
| Q02.16 | The boost finds a queued producer by a linear search of its lane under the lane lock. Replace it? | Await overhead behind 1,000 queued Background tasks: 39 to 81 µs. Behind 100,000: 1.8 to 3.0 ms on 3 workers; 1.9, 18.2 and 27.6 ms in three runs on 20. Cause likely, not isolated. Swift and libdispatch enqueue a duplicate entry instead; that needs tasks that outlive their queue entries (ours delete themselves) | Leave; keep Background queues shallow through producer throttling (storage work); revisit with task reference counting. Profile first (W02.16) |
| Q02.17 | Lower-lane work pushed from inside a running task wakes nobody until that task returns (worker policy rule from W02.8). Wake on every worker push? | A peer parked without a timeout sleeps on it. Bounded to about one slice when the pusher cooperates. Belongs with Q02.14 | Decide together with Q02.14 |
| Q02.18 | A reserve older than 250 ms falls back to its minimum (added in the fix wave so a stalled pipeline does not keep the lower lanes capped). A single frame longer than 250 ms then loses its reserve while its demand peaks, and a wait-trigger raise is discarded too. Fix or drop the rule? | One-line fix known: refresh the staleness clock when the wait trigger raises the reserve | Apply the fix |
| Q02.19 | The bounded park uses a millisecond timeout. If Windows rounds waits to its 15.6 ms tick, the 8 ms Interactive floor overshoots. Raise the timer resolution engine-wide? | A 5 ms floor was served after 5.2 to 5.8 ms on the owner's machine | Document; no `timeBeginPeriod` until a machine shows the overshoot |
| Q02.20 | A future's value type must not suspend in its move constructor or destructor: the forwarding step of a continuation that returns a future runs them inline on the completing thread (possibly the IO thread). Debug builds assert; release builds would lose completions. Accept the rule? | No engine type does this today | Accept; add it to the futures system page |
| Q02.21 | A boosted task entering Frame counts as Frame demand and can lift the reserve for the 8-frame window. Intended? | It is Frame work a stage waits for | Yes, state it in the design |
| Q02.22 | `Schedule.tla` did not finish: liveness under a racing stop, liveness with a rising reserve, 3 workers. Invest in a smaller model or accept? | Safety is complete in all of them; 2 workers complete with eight mutations | Accept; revisit when the wake rule changes (Q02.14) |

**Owner decisions, 2026-11-19** (design 15.7):

| ID | Decision | State |
|---|---|---|
| Q02.11 | As suggested: keep `workers - 1`, measure the lifted clamp after `checkpoint()` adoption | no change |
| Q02.12 | 250 µs for now | applied |
| Q02.13 | No cap for now. Measure again with the 250 µs limit; if a cap is needed, cap at the observed fan-out peak plus one. No multi-frame approximation (no one raise per frame) | open, measure (W02.16) |
| Q02.14 | k known: wake `min(k, parked)`; k unknown: wake two while tasks are still queued. Counted ramp-up for batches and fan-outs, faster ramp-up for task streams. Separate work package | W02.15 |
| Q02.15 | Check where to integrate first; does not block the implementation or the PR | open |
| Q02.16 | Profile first. Lane-lock contention grows with the worker count; a lock-free FIFO work set is a candidate, decided by measurement only | open, W02.16 |
| Q02.17 | As suggested: together with Q02.14 | open, W02.15 |
| Q02.18 | As suggested: a wait-trigger raise refreshes the staleness clock. A 250 ms frame is a stalled process | applied |
| Q02.19 | As suggested: documented, no `timeBeginPeriod` | documented |
| Q02.20 | As suggested: constructors and destructors do not take part in concurrent execution | futures page |
| Q02.21 | As suggested and designed | design 15.7 |
| Q02.22 | As suggested: accept, revisit with the wake rule change | no change |

Also for the owner, not questions:

- The two engines read the lane configuration with the same duplicated block (`GameEngine.cpp`, `EditorEngine.cpp`); the scheduler bundle does not link the config bundle.
- On `feat/wip` before this branch: `Engine.Storage.Test/AsyncStorageTest.cpp(72)` does not compile; `FifoWorkSet.hpp`, `CompositeSlot.hpp` and `FiberPool.hpp` include `Engine.Async` from `Engine.Scheduler`.
- Only clang-cl was built. No MSVC `cl` build, no Release build.

## 2. Rulings made during the run

In the order they were made. "Cost if wrong" is what reverting it takes or what it leaves exposed.

### 2.1 Design level (change what the engine does)

| # | Ruling | Why | Cost if wrong | Where |
|---|---|---|---|---|
| R1 | The exploration's caps "while Frame work is queued" became a Frame reserve that holds while frames run, sized by peak Frame demand over 8 frames, clamped to 1 and `workers - 1` (owner agreed the direction 2026-11-18; window and clamps are mine) | With Frame popped first the queue-tied cap is always 0 and never protects a fan-out | Q02.11, Q02.13 | design 6.4, `Schedule::rollFrame` |
| R2 | The reserve also rises by one on an observed Frame wait above 100 µs (prior-art pass) | Adaptive runtimes size from a delay signal, not a count | Over-reserves on wide machines: Q02.12, Q02.13 | design 6.4, `Schedule::pop` |
| R3 | Bounded park: a worker whose pop failed while lower work is queued parks only until the earliest floor is due (at least 1 ms) | Reserved workers slept through a floor while the others ran long lower tasks; the floor's time guarantee did not hold | One wake per floor period per blocked worker; Q02.19 | design 6.2, `Schedule::parkTimeoutMillis`, `Worker::handle` |
| R4 | The wait trigger runs only when the reserve is demand-sized | A fixed reserve is the owner's pin | One condition | `Schedule::pop` |
| R5 | `pop` hands back the lane it counted; the worker passes that to `leave` and the run accounting | `promote` changes a queued task's lane; reading it after the pop would unbalance the counters | Signature differs from the plan | `Schedule::pop`, `Worker::handle` |
| R6 | The roll's wake when the reserve drops is recorded as a latency measure, not as needed for progress | The clamp always leaves one worker for lower work; the model shows no liveness loss without the wake | A design claim only | design 10, `Schedule.tla` header |
| R7 | `pushBoostable` takes a counted reference to the cell before the push; `Fiber::boost` stays uncounted | The pushed task can finish on another worker and release the cell: use after free in the first build | One atomic increment and decrement per boosted re-queue | design 7.3, `Schedule::pushBoostable` |
| R8 | The cell's link lock is an atomic-flag spin | `Engine.Scheduler` must not include `Engine.Async` | None | `BoostCell.hpp` |
| R9 | Accepted from the implementer: `promote(task, to, cell)` with the cell as an extra argument; a running producer whose cell was raised yields at its next checkpoint; a boost from a plain thread without a schedule raises cells and promotes nothing | The first closes two boosts to different lanes while the task is briefly in no queue; the second re-queues the producer in the raised lane at once (it goes to the tail) | The plan's signatures differ | design 7.2, 7.3 |
| R10 | `await` from a plain thread does not boost | No fiber and no schedule there; the waiter would only be Interactive | A Background producer awaited by a plain thread stays Background | design 7.2, `await` in `Future.hpp` |
| R11 | Inline forwarding is iterative (a thread-local trampoline); the forwarder clears the outer cell's link before completing the outer state | Futures returning futures recursed once per level: stack overflow at 100,000 levels | A thread-local on a path that must not suspend: Q02.20 | design 7.1, `Future/Schedule.hpp` |
| R12 | In a continuation that returns a future, the inner work is raised only when a waiter is present | "Nothing is raised without a waiter" is the design's rule; the plan's wording contradicted it | A Frame chain's inner Background work stays Background until awaited | design 7.1, `Future.hpp` |
| R13 | A cell's lane records waiter urgency only and starts at Background; `then()` does not seed it with the continuation's lane (supersedes the first form of R12) | Seeded, a Frame chain made a Frame waiter's raise a no-op and the walk stopped before what the chain depended on | Changes what `BoostCell::lane` means | design 7.1, `Future.hpp`, `BoostCell.hpp` |
| R14 | The trampoline asserts in debug builds that it ends on the thread it started on; no hook into the scheduler's park | A value type that suspends in its move or destructor would lose later completions silently | Release builds still hang if the rule is broken: Q02.20 | design 15.6, `Future/Schedule.hpp` |
| R15 | A reserve older than `reserveStaleMillis = 250` counts as its minimum; a stopped pipeline resets the reserve | The reserve is only resized at a frame start, so a stalled or stopped pipeline kept the lower lanes capped | Q02.18 | design 15.6, `Schedule::effectiveReserve`, `Schedule::resetReserve` |
| R16 | The wait trigger and the wake rules were not changed in the fix wave | Both are tuned or owner-decided (W02.8) behaviour with measured alternatives | Q02.12 to Q02.14, Q02.17 stay open | none |
| R17 | `boostMaxHops` 16 to 1,024, no assert at the cap | An awaited chain of nested futures longer than 16 is a legitimate program; cycles already end at the first unchanged raise | A corrupted link chain is walked for 1,024 hops | `BoostCell.hpp` |
| R18 | Slice, floors and wait limit are clamped to at least 1 where the schedule is set up | A floor of 0 inverted the lanes; a slice of 0 yielded at every checkpoint | None | `Schedule::setup` |
| R19 | A destroyed cell poisons its lane in debug builds and the re-queue asserts on it | Makes a use of a released cell likely to fail loudly | Catches a removed counted reference in about 1 run of 5 | `BoostCell.cpp`, `Schedule::pushBoostable` |

### 2.2 Measurement and defaults

| # | Ruling | Why | Cost if wrong |
|---|---|---|---|
| R20 | Flooded baseline runs are capped at 60 s (about 125 frames); every percentile line prints its sample count | A full flooded run took about 15 minutes on the old scheduler | The baseline's flooded p99 rests on few frames |
| R21 | With the owner away, defaults come from the sweep by the stated bounds: the value that meets the bounds on both worker counts and gives the most Background throughput; within the run-to-run spread the starting value stays; if a bound fails everywhere, no further tuning | A rule had to exist before the numbers did | Any default can be re-picked from design 15.2 |
| R22 | No default changed, although a literal reading of R21 picks a fixed reserve of 8 on 20 workers | Sweep points were single runs under a large spread; a fixed 8 hard-codes the benchmark's fan-out width | Background throughput on wide machines until Q02.12 is decided |
| R23 | The boost's cost is reported as await latency minus the producer's run; no engine instrumentation | Keeps measurement code out of the engine | The search itself is not isolated: Q02.16, W02.16 |
| R24 | The review finding "Interactive work collapses to floor rate because Frame is popped first" was set aside as refuted | Under flood with the frame running, Background completes 185 tasks per second on 3 workers and over 1,000 on 20, against a floor rate of 10 | If a real engine frame keeps its Frame queue non-empty far more than the benchmark's chain does, the concern returns; the editor run would show it |

### 2.3 Process

| # | Ruling | Cost if wrong |
|---|---|---|
| R25 | The branch starts from the `feat/wip` head of the day (`fcc3d774`), not the hash the plan named | None |
| R26 | Task 4 could touch `Task.hpp` although its file list omitted it; the Task 6 model got an extra mutation and a reachable reserve rise so its cap invariant can fail; the roll's wake was not forced to look necessary in the model | None |
| R27 | The pop policy task ran on Opus instead of Sonnet; research ran on Sonnet (owner rule: no Fable for research) | Tokens |
| R28 | The run's scratch report on the sweep had loose wording; it was corrected here and in design 15, not in the scratch file | None |
| R29 | The fix wave's fixups were re-cut with git so each lands in the commit that owns its lines, then folded; the final tree is identical to the reviewed one | Intermediate commits were not built one by one |

## 3. Deferred findings (not fixed, by review task)

Minor unless marked. Each is one line in the run ledger with its file and line.

- **Benchmark**: frame time starts at stage 0's start, so stage 0's own queue wait is excluded; `getenv` deprecation warnings; function-local statics for stage names.
- **Lanes**: `NothingIsPromotedByTime` is close to a tautology; a `using Lane` alias sits in namespace `hg`; unsigned-against-signed comparisons in the schedule tests.
- **Resolution**: one line over 140 columns in `Future.hpp`; no test for `ready(eFrame)` from a plain thread; `exec` re-resolves an already resolved task (idempotent, wants a comment).
- **Pop policy**: one futile cascade wake per pop while only reserve-blocked lower work is queued (Q02.14); `framePeak` can overcount by concurrent pops; `ChainGivesReserveOne` passes without the feature; no test for `Scheduler::queued(Lane)`; `StaleReserveFallsBackToTheMinimum` is timing-dependent; the clamp test does not cover the wait limit.
- **Slices**: new atomics sit unaligned beside `_reserve` (false sharing, worth a look under W02.16); the debug overrun warning prints the lane index; the 5 ms start bound may flake on a loaded machine.
- **Model**: header wording ("starves" should read "can, under adversarial scheduling"); the stale-load argument about a skipped wake is unchecked; mutation (c) was not re-run after the roll became fair; the `verifying-concurrency` skill's queue row for `Schedule` is stale.
- **Boost**: recursive destruction of a long dependency chain; a floor turn can be spent on a lane a promote just emptied; a stale task address can promote one unrelated task once (accepted in the design).
- **Futures**: `ContinuationRunsExactlyOnceUnderRacingBoosts` races only by chance; pending forwarders are left behind if a forwarder throws; a 20 ms sleep in `NoProducerIsNoOp`.

## 4. Left to do

In order. A new session can start at step 1 from this page, the design's section 15 and the PR.

1. `/review-branch origin/feat/wip..HEAD 84` on `feat/lane-policy` (the lenses; not run in the autonomous session). Fixes go in as fixups onto the commit that owns the line.
2. Owner decisions Q02.11 to Q02.22 above; apply the accepted ones (Q02.12 and Q02.18 are one-line changes).
3. Profile with the workload `LaneFloodBenchmark.DISABLED_Profile` in `Performance.Test` (W02.16); see the PR for the command.
4. Owner editor run in Debug: frame time idle and during an asset import; every logged overrun becomes an issue (Q02.15).
5. `graphify update .` on the branch, then mark the PR ready and merge it into `feat/wip`.
6. After the merge: the scheduler system page (lanes section), the ADR for Q02.8 with the decisions taken here, deletion of the worktree, the run workspace and the ref `backup/lane-policy-prefold`.
7. Follow-up chunks: W02.15 (wake-up fan-out), W02.16 (profile and optimise).
