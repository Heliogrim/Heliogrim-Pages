# Pointer Sets for Small and Medium Datasets (Exploration)

**Status**: closed (2026-11-04). Decision: keep `ankerl::unordered_dense`; the custom container was dropped. Kept for the record. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

**Origin**: distilled on 2026-11-04 from a Gemini conversation ([link](https://gemini.google.com/app/9844111e326b8588)), then revised against the vendored ankerl v4.5.0 source. Benchmark numbers from the source are not used. Measure on our own data.

## 1. Question and Priority

Build a pointer or `uintptr_t` set that beats `ankerl::unordered_dense` (v4.5.0, vendored in `vendor/ankerl`) on contains, insert, erase and traversal, while keeping `values()`-style contiguous traversal. It must work at `constexpr` and `constinit` for small inline capacities.

This is the most prioritized experiment in the exploration set. Its result feeds the running parity work on `feat/actor-archetypes` (see section 4). The comparison decides which implementation we keep, so the criteria in section 5 are fixed before measuring.

## 2. Baseline Facts (checked against the vendored source)

- `DenseSet` (`src/Engine.Common/Collection/DenseSet.hpp`) is an alias for `ankerl::unordered_dense::set`. `CompactSet` (`Set.hpp`) and `DenseMap` are aliases of the same family.
- ankerl stores values in a contiguous `std::vector` and keeps a separate index of 32-bit slots with fingerprints. Erase swaps the last value into the hole, so iteration order changes on erase.
- The default hash for `T*` is **wyhash-mixed** (`hash<T*>` in `unordered_dense.h`), not identity. The earlier advice to replace it with an identity hash is therefore a hypothesis to measure, not a fix. Our baseline already pays for mixing.
- Callers use ankerl-only `values()` (`Universe.cpp:62`, `Actor.hpp:299`). A replacement must provide it or those call sites change.
- About 110 source files reference `DenseSet`, `CompactSet` or `DenseMap`. Changing an alias changes all of them.

## 3. Proposed Design (candidate "PtrSet")

Working name, not final. Targets `T` that are trivially copyable and at most 8 bytes (pointers, `uintptr_t`).

- **Storage.** A dense value array, either inline (`std::array<T, Inline>` plus a size) or heap-backed through an allocator. The inline case has no `reinterpret_cast`, so it is `constexpr` without `std::launder` tricks.
- **Small mode** (size at or below the threshold). No index. Contains scans the value array with SIMD. AVX2 when `__AVX2__` is defined, otherwise SSE2 with two 32-bit compares per 64-bit value (SSE2 has no 64-bit compare). Under `if consteval` the scan is a plain loop.
- **Large mode.** A power-of-two open-addressing index of `uint32_t` slots (value index plus one, zero means empty). Parallel 8-bit fingerprints are probed 16 at a time with SSE2 (`pcmpeqb` plus `movemask`). Hash: one multiply by a 64-bit odd constant, with high bits as fingerprint and low bits as bucket index.
- **Erase.** Swap-remove in the value array, and backward-shift deletion in the index. No tombstones.
- **Mode switch with hysteresis.** Build the index above 64 entries and drop it below 32. Without a gap, a set that oscillates around the threshold rebuilds constantly.
- **Traversal.** A pointer walk over the value array. Iterators are plain pointers.
- **Compatibility.** Provide `values()`, `contains`, `insert`, `erase`, `find`, `begin`, `end`, `size`, `empty`, `reserve`, `clear`, matching what callers use.

## 4. Relation to the Running Parity Work

- The parity work is on `feat/actor-archetypes` (worktree `X:/Dev/C++/Heliogrim-CLion-wt/actor-archetypes`). Its goal is to match ankerl on CRUD and traversal.
- No set CRUD or traversal benchmark exists yet. `src/Performance.Test/TransformBenchmark.cpp` is the only benchmark in that worktree.
- The parity implementation itself was not found in either worktree. The owner needs to point to the branch or the uncommitted files before the comparison can run.
- Expected outcome, to verify: the candidate beats the parity work on traversal and small-N contains. The parity work may stay the simplest maintainable option for CRUD at large N. Both are kept in the comparison, not one dismissed in advance.

## 5. Experiment Plan

**P0. Harness.** Add a disabled-by-default perf test in `src/Performance.Test/`, following `TransformBenchmark.cpp` (`--gtest_also_run_disabled_tests`). Workloads: contains hit and miss, insert, erase, full traversal. Sizes 4, 8, 16, 32, 56, 64, 256, 4096, 65536. Pointer sources: a strided pool allocator and `malloc`. Implementations: ankerl v4.5.0 (baseline), the parity work, PtrSet.

**P1. Candidate.** Implement PtrSet as a standalone type in `Engine.Common/Collection`, with unit tests for every operation and for mode switching at the threshold boundaries. No changes to existing aliases.

**P2. Decision.** Compare on the same machine and build profile (Profile, not Debug; the existing benchmark note warns about Debug numbers). Criteria, fixed now:
- Adopt PtrSet only if it is at least 1.2x faster than ankerl on at least two workloads at the sizes that matter, and no workload regresses by more than 5 percent.
- Keep the parity work if it is within 5 percent of PtrSet on CRUD at large N and is simpler to maintain.
- Otherwise keep ankerl.

**P3. DenseSet extension (only after P2 picks PtrSet).** Add inline capacity. Two options to decide in brainstorming:
- (a) A new type, `InlineDenseSet<T, Inline, ...>`. The 4-parameter `DenseSet` alias stays unchanged. Lower risk, two types to keep.
- (b) A fifth defaulted parameter on `DenseSet`. One name, but the alias is no longer the same type as ankerl's, and `CompactSet` and `DenseMap` need the same treatment.

For `constinit`, a global must use the inline form. A heap-backed set cannot be `constinit`, because transient allocations must be freed before compilation ends.

**Superseded (2026-11-04): the custom container was dropped and `ankerl::unordered_dense` stays.** Measured on this machine, the inline linear scan beat ankerl only on small mixed-order misses (about 0.3 ns at N=4). Ankerl won hits and dependent-chain latency at every size. Cold-cache misses cost about 15 ns more than ankerl at N=8. Ankerl's layout can be tuned upstream, and the caller can prefetch, so the custom code was not worth its maintenance. The record below is kept for reference.

Earlier plan, for reference: one template, storage selects the mode. `hg::DenseSet<Type_, Storage_, Hash_, Equal_, Allocator_>` in `Engine.Common/Collection/DenseSet.hpp` replaces the ankerl alias. `Storage_ = void` is heap storage with an index, and `std::array<Type_, N>` (or `InlineArray<Type_, N>`) is inline storage with linear lookups only. `CompactSet` is an alias with its existing parameter order. No second data structure is added. Benchmarks are still pending (P0), so the performance claims above are unmeasured.

**Benchmark result (2026-11-04, RelWithDebInfo, median of 5, ns/op, pointer keys):**

| n | ankerl hit | heap hit | inline-linear hit | ankerl miss | heap miss | inline-linear miss |
|---|---|---|---|---|---|---|
| 4 | 2.8 | 4.0 | 5.9 | 5.1 | 3.4 | 5.5 |
| 8 | 3.2 | 3.1 | 7.5 | 4.7 | 2.9 | 7.8 |
| 16 | 3.2 | 3.0 | 7.8 | 4.2 | 4.0 | 10.4 |
| 32 | 2.8 | 3.5 | 11.4 | 4.9 | 3.1 | 16.9 |
| 64 | 4.3 | — | 17.9 | 6.3 | — | 28.6 |

- **Heap threshold: none.** The index beats the SSE2 linear scan at every size measured, so the heap linear path was removed. Heap erase is still slower than ankerl (about 17 to 29 ns against 13 to 16 ns). The cause is recomputing the hash in `bucket_of`; carrying the bucket from `locate` is the fix, not yet done.
- **Inline linear vs ankerl:** linear ties ankerl on miss at n=4 and loses above that. Build and erase are far faster inline (5 to 18 ns against 53 to 146 ns build), since inline does no allocation or hashing.
- **Crossover to revisit:** the SSE2 scan is limited by 64-bit compares built from 32-bit halves. An AVX2 path (`_mm256_cmpeq_epi64`) could move the crossover. It needs a runtime dispatch or a project flag, which is a decision for brainstorming.

## 6. Risks

- The SIMD path is compiled out silently unless the build enables AVX2 (`/arch:AVX2` or `-mavx2`) under clang-cl. Confirm the project flags before reading any SIMD result.
- Pool-allocated pointers have a regular stride. A weak hash with power-of-two masks clusters them. The wyhash-style mix above is chosen for that reason, and P0 must include the strided pool workload.
- Swapping erase changes iteration order. Callers that rely on stable order break. Check the call sites before P3.
- An early-exit `std::ranges::find` is usually not auto-vectorized. Only the explicit SIMD path is expected to be fast. Check the disassembly in P2.

## 7. Open Questions

- Threshold values (32 and 64) are guesses. Find the crossover per element size.
- Whether erase is needed on all uses, or insert-only sets can use a simpler layout.
- Whether a stable-iteration-order option is worth its cost for any caller.

## 8. Related

- [Storage engine](storage-exploration.md): resolved-stack caches are a candidate use.
- [Actor system](actor-system.md): component and actor reference sets.
