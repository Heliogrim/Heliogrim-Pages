# Observability and Profiling (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

**Origin**: distilled on 2026-11-04 from a Gemini conversation ([link](https://gemini.google.com/app/66851357c03056b2)). The raw notes are not kept. Claims were not re-verified against the engine source in this pass unless marked.

**Scope**: observability is a separate topic from the audio design. The audio design keeps only a hook.

**Current state (checked 2026-11-04)**: `Engine.Common/Profiling` holds `Profiler` (records name, start, end, thread) and `Stopwatch`, used through `SCOPED_STOPWATCH` macros in about 15 files, mostly GFX start-up. The session start in `Editor.Main` is commented out. **Decision (owner, 2026-11-04): drop the profiler, stopwatch and their macros without a direct replacement. Observability is planned and built from the ground up.** Fibers carry no identity or context slot today. The only thread identity is a `thread_local` in `Engine.Scheduler/Thread`. Win32 fibers own their stacks, so the fiber-local context most likely belongs in the `Fiber` control block (open question in section 4).

## 1. Goals

- Timings for operations, histograms (p99, p99.9), gauges and counters.
- Memory: arena live bytes versus reserved, high-water marks, fragmentation, instrumented allocation and free.
- Fiber-aware spans. Attribute time to the fiber, not the OS thread, because fibers migrate between threads.
- Source locations through `std::source_location`, resolved to static metadata.
- GPU timestamps (Vulkan, D3D12) correlated with CPU submission points. Offline shader statistics (register pressure, occupancy).
- Optional sampling (perf_event EBS or IBS) with a map from sampled instruction pointers to the active fiber.
- Custom probes, metrics and reports, including computed metrics and threshold triggers (for example "p99 tick time above 16.6 ms for 50 consecutive ticks").
- Export as OpenTelemetry metrics for game-server monitoring, flushed by a background fiber.
- VM and node-graph invocation spans, pin-value snapshots and replay (shared with the scripting exploration).
- Three tiers: Retail (no tracing, atomic counters only), Playtest (sampling, high-water marks), Profile (full zones and allocation tracking). Build configs Debug, Profile, Release.

## 2. Design Points Carried Forward

- **Fiber-local context** instead of OS TLS. Open question: store it in the fiber stack allocation or in the control block. The choice affects migration.
- **Per-lane lock-free SPSC ring buffers**, drained by a background thread or fiber. The hot path never allocates. All buffers are pre-allocated at init.
- **Inactive gate**: one relaxed atomic flag checked on span entry, marked `[[unlikely]]`. When no capture runs, a span costs one predictable branch.
- **Timestamps**: `rdtsc` on x86, converted to nanoseconds in the background. Calibrate the TSC frequency once at startup.
- **Memory ordering**: relaxed for counters, acquire and release only at synchronization points.
- **Macro-free API** is a user requirement. The source sketches use `consteval` and `std::source_location` for this.

## 3. Problems in the Source Sketches

These must be fixed before any of the code is adopted.

- **Compile-time name metadata does not compile as written.** `constexpr ProfileMetadata meta{name, loc};` uses a constructor parameter, which is not a constant expression. Compile-time strings need a template parameter (a string literal as a class-type non-type template parameter) or a `consteval` immediate function. Check with clang-cl.
- **`constexpr explicit` on a span constructor that calls non-constexpr functions** has no effect and should be removed. The constructor is runtime-only.
- **`__rdtsc` is compiler-specific.** Wrap it in one function. Use the intrinsic from `<intrin.h>` on MSVC and clang-cl.
- **Gate toggled mid-span.** The span stores `active_` at construction. If capture starts or stops while a span is open, `end_span` may be skipped or unmatched. Use a per-lane depth counter or a per-span token.
- **Source weakness.** The "sub-nanosecond overhead" claim for Tracy is cited only to a blog post. That does not meet our research-source standard (primary papers or our own benchmarks). Measure our own overhead instead.
- **Tool comparison** (Tracy, OTel C++, hdrhistogram, Perfetto) is from the model's memory and was not checked against primary sources.

## 4. Open Questions

- Where the fiber-local context lives, and how it moves on migration.
- Capture start and stop without restart: how large the pre-allocated buffers must be, and what happens when they fill up (drop, overwrite or block).
- The metered-run mode for regression tests needs a deterministic time source. That depends on the scheduler's clock.
- Which metrics go to OTLP, and what each costs. HDR histograms should stay off the hot path.
- Stored capture format for diffing. It overlaps with the serializer work in [serialization-evolution-exploration.md](serialization-evolution-exploration.md).

## 5. Related

- [Actor system](actor-system.md): tick stages that spans will wrap.
- [Serialization evolution](serialization-evolution-exploration.md): storage format for captures.
- [Scripting runtime](scripting-runtime-exploration.md): invocation spans for user code.
