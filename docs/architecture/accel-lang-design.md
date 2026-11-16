# Accel Lang (Design)

**Status**: design record, written 2026-11-13, section 7 (SPIR-V backend, [W11.2](../plan/work/accel-lang.md)) added 2026-11-16 (work chunk [W11.0](../plan/work/accel-lang.md), issues [#82](https://github.com/Heliogrim/Heliogrim-Engine/issues/82), [#148](https://github.com/Heliogrim/Heliogrim-Engine/issues/148)). It moves the two engine-side specs onto the site: the Accel IR design (2026-10-28, milestones 1 and 2) and the region-borrow design (2026-11-07, PR [#156](https://github.com/Heliogrim/Heliogrim-Engine/pull/156)). Both milestones are on `master` and `feat/wip`. How the code works today is on the system pages [ASL Language](../systems/accel/asl.md) and [Accel IR and Passes](../systems/accel/ir.md); this page holds the intent, the rules and who decided them.

Markers: **Decided** = owner decision (spec review answers or the work page Decisions table). **Builder's call** = left to the implementer and taken as built; the owner may revisit it.

## 1. Intent

Before the IR, adding one shader meant stating the same thing five times: the shader text, hand-written IR annotations (`DepthPrePass.cpp`), the composed material, the render-graph subpass and the provisioning of resources. Resource identity, types and bindings lived in the author's head, and a mismatch showed up as a runtime crash (about 20 crashes after one forgotten annotation). The IR in `Engine.Accel.Lang` carries all of it, so each layer declares only what it knows, and a mismatch fails in a test without a GPU.

**Anti-goals**: a fast path that parses, assembles text or rebuilds IR at runtime; binding numbers or locations written by hand; any GPU in the contract tests.

## 2. Layers and rules

| Rule | Marker |
|---|---|
| **Shader/IR** is a shared resource holding code and interface (needs and provides, with types). **Material** is an instance with concrete bindings, constants and context. **Render-graph stage** names the outputs it requires and supplies context; each pass resolves only what it needs (a depth pass keeps morphing and drops lighting). | Decided |
| **Binding identity** is a string id (`"camera"`, `"material.albedo"`). Set, binding and location numbers are assigned after merge by the layout pass, never authored. Same id with different types fails the merge, naming both modules; within a stage, equal ids collapse into one binding. | Decided |
| **Forward declarations** state a needed signature; at merge every declaration needs exactly one body. `@redefine (allow = true)` lets a later module replace that one function; the last body wins. | Decided |
| **Toggles** are declared by the module offering them with a closed value set; `@when` applies to a block or one declaration. Exhaustiveness is checked and the error names the missing combination. The pass or profile value wins over a material; a conflicting material value is a diagnostic. | Decided |
| **Resolve order**: fix toggles, resolve toggled constructs, slice by required outputs, compute the interface, assign layout, check contracts. Required outputs come from `EffectSpecification::targetSymbols()`. | Decided |
| **Layout** trades unused slots against extra layouts and sets with a weighting function (configurable weights), deterministic for equal input. Set and binding numbers may differ from the old hand-written ones. | Decided |
| **Variant cache keys are content-based**: module, toggle values and output set. The address- and name-based `HashedState` keys must not be reused for variants (an `EffectProfile` hashes only its name). | Decided; type `VariantKey` in W13.1 |
| **Function bodies are an AST** in flat arenas, because slicing needs a call graph and def-use. | Builder's call, as built |
| **GLSL is emitted** into the existing glslang path today. W11.2 replaces it with direct SPIR-V and removes GLSL and glslang ([section 7](#7-spir-v-backend)); there is no GLSL oracle. | Decided (2026-11-14, 2026-11-16); Q11.2: Slang is neither oracle nor backend |
| **Optimisation**: no general optimiser of our own; `spirv-opt` plus the driver, and only engine-semantic passes (specialisation folding, dead-resource elimination, uniform-to-push promotion, variant dedup, the uniformity, borrow and interface checks). | Decided (Q11.3) |

## 3. IR part list

One `ir::Module` per source module, later per merged stage. It is a plain value: copyable, comparable by content, no pointers. Field-level detail is on [Accel IR and Passes](../systems/accel/ir.md#data-model).

| Part | Holds |
|---|---|
| `name`, `entry` | Module name; `EntryKind` (vertex, tess control, tess eval, geometry, fragment, compute). The kind list stays open for mesh, task, ray tracing and a reserved work-graph value (Q12.1). |
| `attributes` | `local_size`, `early_fragment_tests`, geometry and tessellation settings. |
| `toggles` | Name, value list and default; declarations and `when` statements carry a `Condition` tree. |
| `types` | Type table: scalar, vector, matrix, array, struct, texture, sampler, image, region. |
| `bindings` | `@input`, `@output` and `workgroup` declarations, with id, class, mode, access and packing. |
| `constants` | Module-scope `const`; a spec id makes it a specialisation constant. |
| `functions` | Name, parameters (value, `&`, `&mut`, region), return type, optional body, `@redefine` flag, condition. |
| `exprs`, `stmts` | Flat arenas joined by typed 32-bit refs (`~0` = unset). Every node keeps a `SourceLoc`, which is never part of the content hash. |
| `warnings` | Non-fatal diagnostics, not hashed. |

Pass order: parse and typecheck, merge, fix and resolve toggles, slice, interface, contracts, layout, lower regions, emit GLSL. After W11.3: the last two become lower references, lower to SPIR-V form, write SPIR-V (section 7.5). Each pass takes a module by `const` reference and returns a new one or diagnostics, so each one can be tested alone.

## 4. Region borrows

**Why**: shaders need several live views into one block of memory: kernel reads at neighbouring offsets, colour blending, and the micropolygon scratchpad, where each lane splits its chunk into an index part and a vertex part and writes both through shared helpers. The old rule rejected a call whenever a `&mut` argument's root name appeared in another argument, and never checked `let` borrows against each other.

| Rule | Marker |
|---|---|
| `&mut a[lo .. hi]` and `&a[lo .. hi]` borrow a half-open range of any array (sized, trailing storage-buffer array, workgroup). A region can be indexed, sub-borrowed and measured with `len(r)`. Region parameters are spelled `&mut T[]` and `&T[]`. | Decided |
| **Disjointness by construction**: two places are disjoint when their paths split at different struct fields, different constant indices, or ranges whose shared bound is the same expression (`[0 .. n]` and `[n .. size]`). Anything unprovable overlaps and is rejected, with a message naming both places. | Decided |
| A shared bound counts only when built from names that cannot change between the two borrows: `const` locals, parameters, module and spec constants, literals, read-only builtins. `let` locals are mutable and do not count. | Decided |
| **`let` borrows** get the same check by lexical scope, with no flow analysis. A re-borrow rooted in a live alias is derived from it and is not a conflict. | Decided |
| Functions with region parameters are **specialised once per distinct root**, not per call, by an IR pass before any backend. Inside, a region is root + offset + length passed by value. | Decided |
| Read-only regions are included; a `&mut` region may be read freely; two reads never conflict. | Builder's call, as built |
| Lowering runs last, right before emission, so every earlier pass and the content hash see the borrows as written. Runtime bounds are evaluated once, at the borrow. | As built |
| **Not covered**: phase-based reuse of workgroup memory, work-graph records, runtime bounds checks, cross-lane races (the allocator and the barrier analysis own those), arithmetic proofs (`i` against `i + 1`). | Non-goals; the design keeps the first two possible |

## 5. Reserved names

A user name never collides with GLSL or a name the compiler generates; the parser rejects it at its token ([#148](https://github.com/Heliogrim/Heliogrim-Engine/issues/148), branch `fix/asl-reserved-names`). Names are not renamed on output, so a name stays the same in every backend and in diagnostics.

- Prefix `_hg_` (emitter temporaries such as `_hg_ref<k>`), on every declared name.
- GLSL 4.60 keywords and reserved words, the Vulkan GLSL type and qualifier words, `gl_*`, the vector, matrix, sampler, image and texture type spellings, and `texture` (the emitter calls it, and a variable of that name would hide it).
- Region-lowering suffixes: locals ending in `__off`, `__len`, `__end` or `__i<k>`, functions ending in `__r<k>`. Locals, parameters and functions are checked by the typechecker; module-scope constants, bindings, workgroup variables and struct names by the parser, against both the local suffixes and `__r<k>`, since they share the GLSL global scope with the generated functions.

## 6. Open

| Point | Where it goes |
|---|---|
| Borrow lowering on the GLSL path versus in a SPIR-V emitter (left open on purpose). | Settled by W11.2: borrows become root + access path references ([7.3](#73-references)) |
| GPU render of the migrated shaders never verified. | W26.2 |
| `InterfaceDesc` export for the render graph. | W11.3 |
| `HashedState` is still address- and name-based in `Engine.Accel.Storage`. | W13.1 (`VariantKey`) |
| Name collisions the reserved-name check does not catch: a user name equal to a GLSL builtin function (`max`, `textureLod`; only `texture` is reserved), a `<binding>_block` type name against a user struct, a local or parameter `f__r<k>` hiding the generated region function, the int8/16/64 and float16 extension type names. Until W11.3 lands each one surfaces as a glslang gate failure. | Settled by W11.2 ([7.5](#75-emitter)): everything is identified by result id, names are debug info only, so a collision cannot be expressed. W11.3 implements it. |

## 7. SPIR-V backend

Work chunk [W11.2](../plan/work/accel-lang.md), issue [#92](https://github.com/Heliogrim/Heliogrim-Engine/issues/92), written 2026-11-16 from the owner's brainstorm the same day. W11.3 implements sections 7.1 to 7.9; the later iterations are listed in 7.10. Reading material: [SPIR-V backend references](../plan/sources/research-spirv-backend.md). Nothing is copied from another compiler (Q11.2).

### 7.1 Intent

The owner gives three reasons (Decided):

1. **SPIR-V blocks the roadmap.** Compute, mesh and task, ray query, subgroups, descriptor indexing, the interface export for the render graph and the variant cache all need a backend that can express them.
2. **glslang goes, it does not step aside.** No new feature or fix is built on the GLSL path. W11.3 ends with glslang, `SpirvCompiler`, `GlslEmitter` and `GlslRequirements` out of the build, not with two backends side by side.
3. **One translation instead of four.** Today: ASL text, ASL IR, GLSL text, glslang AST, SPIR-V. After: ASL text, ASL IR, SPIR-V words. Shaders are compiled at runtime in shipped games (variants on demand, [W13.1](../plan/work/accel-lang.md)), so this latency is player-visible.

**Goals**: SPIR-V 1.6 for Vulkan 1.3 (the target glslang uses today) emitted straight from the IR for all six entry kinds the IR has (vertex, tessellation control and evaluation, geometry, fragment, compute); every compile error a `Diagnostic`; `spirv-val` on every module in tests; names and line info for RenderDoc.

**Non-goals**: new pipeline kinds (W12), new language features beyond 7.2 (W11.5), DXIL, an own general optimiser (Q11.3), a structurizer (the IR has only structured control flow).

**Anti-goals**: a GLSL-shaped middle layer under the SPIR-V path, such as string names that carry meaning, text that is emitted and parsed again, or emitter output that depends on a name not colliding.

### 7.2 Language core

GLSL used to supply these meanings; ASL now states them. Every rule holds in every backend.

| Rule | Marker |
|---|---|
| **Conversions are explicit.** No implicit conversion between any two numeric types, including widening (`u16` to `u32`, `f16` to `f32`) and signed to unsigned. A mixed operation (`f32 * s32`, `u32 + s32`) is an error whose help line names the conversion to write. Vector with scalar of the same component type stays legal. | Decided |
| **Value conversion is `T(x)`**, with `T` any scalar or vector type name (`f32(i)`, `u32vec2(uv)`); component-wise for vectors. `u32(b)` maps `bool` to 0 or 1; a number never converts to `bool` (write `x != 0u`). | Decided |
| **Rounding follows GLSL and Vulkan**: float to integer truncates toward zero; integer to float and float to narrower float round to nearest even; a float out of the integer range (or NaN) gives an undefined value. Same width signed and unsigned keep the bits; widening extends by the source's signedness. | Decided (GLSL default) |
| **Bit reinterpretation is `bitcast<T>(x)`**, equal size required. The `<T>` spelling is shared with future user generics (W11.5 B9). | Decided |
| **Literals take their type from context**: `let a : f32 = 1` is legal, `let b : u8 = 300` and `let c : s32 = 1.5` are errors. Suffixes stay for literals without context. | Decided |
| **Evaluation order** is left to right for operands and call arguments. `&&` and `\|\|` short-circuit. The ternary evaluates one side only. | Builder's call (owner may revisit) |
| **Signed integer overflow wraps** (SPIR-V does; GLSL never defined it). Integer division by zero and shifts by at least the bit width give an undefined value, as in SPIR-V. | Builder's call |
| **`discard`** ends the invocation (`OpTerminateInvocation`, the GLSL meaning). A demote statement may be added later as its own word. | Builder's call |
| **Reserved names shrink** to ASL keywords, ASL type spellings and ASL builtin names. The GLSL words, `gl_*`, `_hg_` and the region suffixes of section 5 are released when W11.3 deletes the GLSL emitter. | Builder's call; follows from 7.5 |

### 7.3 References

The owner chose real reference semantics for `&` and `&mut` (Decided, 2026-11-16). Parameters and `let` borrows behave alike.

- **A reference is a root plus an access path.** The root is a binding, a workgroup variable, a module-scope variable or a local. The path is a list of field and index steps: `&mut lights.data[i].colour` is root `lights`, path `.data [i] .colour`. Region borrows (section 4) are the same thing with a range step.
- **Global roots** (bindings, workgroup, module scope): the callee is specialised once per distinct root and constant path prefix, as region helpers are today. Dynamic indices in the path become `u32` value parameters. Every access inside rebuilds the address from the root with one `OpAccessChain`, so a write is visible at once through any other access, including the global name. No pointer crosses a call.
- **Local roots**: passed as a pointer to the whole `Function` variable plus the path's dynamic indices. If that pointer form turns out not to be legal under Vulkan's logical addressing rules (the rule was not read in W11.2; W11.3 checks it first), a local root is copied in and out instead. That is not observable: the callee cannot name the caller's local, and the borrow rules forbid a second alias.
- **No variable-pointers feature** is required by this scheme.
- **Downgrades** (allowed rewrites, each ships only after a measurement shows a gain, W11.7): an `&mut` never written becomes `&` (the Dev tier also hints "`mut` not needed"); an `&` whose root region is not written during the call may become one load into a value. The borrow check already proves that no overlapping write exists.
- **Code size** grows with distinct roots per function; W11.3 records the module sizes of the engine shaders before and after.

### 7.4 Validation tiers

Shaders compile at runtime in shipped games, so the compile path splits by cost (Decided, 2026-11-16).

| Tier | Runs | Contains |
|---|---|---|
| **Build** | every compile, including a player's machine | parse, typecheck (incl. borrow rules), merge, resolve, slice, interface, layout, reference lowering, emit; only checks needed to emit valid SPIR-V |
| **Dev** | editor, tests, Debug builds | Build plus uniformity, contract and stage-chain checks, `spirv-val` on the output, names and line info |
| **Deep** | on demand in the editor (Background task), CI | Dev plus value-range analysis (W11.6) and sweeps over all toggle combinations |

The tier is a compile option, not a build-time switch; Deep results are cached by module content hash. Today's contract and uniformity checks run inside `resolveStageIr` and typecheck; W11.3 moves them behind the Dev tier only if the Build-tier compile time shows they matter (builder measures, then decides).

### 7.5 Emitter

- **Shape**: three steps, each testable alone. (1) *Reference lowering* replaces region lowering (7.3) and leaves an IR without borrows. (2) *SPIR-V lowering* turns the tree IR into a function-scoped form: every local becomes an `OpVariable` in the `Function` storage class declared in the entry block; `if` becomes a selection with a merge block; `for` and `while` become loops with merge and continue blocks; `break`, `continue`, `return` and `discard` become branches or terminators; short-circuit and ternary with side effects become branches, otherwise `OpSelect`. (3) *Writing* assigns result ids and writes words in the module layout order the SPIR-V spec requires. Lowering and writing stay apart so the writer has no ASL knowledge.
- **Identity is by result id.** `OpName` and `OpMemberName` carry user names in the Dev tier only; no emitted name is ever looked up, so a collision cannot occur. Generated helpers get no name at all.
- **One module per entry point**, matching one `ir::Module` per stage. Pipelines that combine several entry points (ray tracing, work graphs) combine modules at pipeline level (W12).
- **Storage classes instead of qualifiers**: `Input`, `Output`, `Uniform` (uniform blocks), `StorageBuffer`, `UniformConstant` (textures, samplers, images), `PushConstant`, `Workgroup`, `Private`, `Function`. A later kind adds classes (task payload, ray payload, node payload) without changing this mapping.
- **Explicit layout**: block member `Offset`, `ArrayStride` and `MatrixStride` come from the layout pass (std140 for uniform blocks, std430 for storage blocks and push constants, as emitted today), together with `DescriptorSet`, `Binding`, `Location`, `Block`, `NonWritable` and `NonReadable`. glslang computed the offsets until now; the layout pass now owns them.
- **Specialisation constants**: `OpSpecConstant*` with `SpecId` from `Layout::specConstants`.
- **Builtins**: the builtin table maps each entry to a SPIR-V form (a `BuiltIn` decorated variable, a `GLSL.std.450` instruction, or a core opcode) and to the capability and extension it needs. The `glsl` name column goes away.
- **Capabilities** come from a feature walk over the IR (types used, builtins used, storage classes), not from a list the author writes. The target is a fixed profile, not the running device: Vulkan 1.3 plus the minimum-spec feature set of Q12.2 (RDNA3 and Ada class: mesh shaders, ray query, descriptor indexing, 64-bit atomics). A feature outside that profile is a diagnostic naming the construct. A device below the minimum spec is rejected once at startup, never per shader, so the device is not part of the variant key.
- **Interface numbers are per pipeline.** `InterfaceDesc` per entry point carries the string ids, types, access and stage-local facts (workgroup size, spec constant ids by name); set, binding, location and spec id numbers live in the pipeline layout record that `assignPipelineLayout` produces today, since one entry point gets different numbers in different pipelines (section 2, layout rule). W11.3 keeps both in memory on the compiled result; serialising them belongs to the cache (W13.1).
- **Statements that end a block** are one general mechanism in lowering and writing (`discard` first; the mesh and ray-tracing terminators in W11.5 reuse it).
- **IR changes needed by the emitter**: literals hold typed values (not source text); unary and binary operators are an enum (not text). Both keep `SourceLoc` and stay out of the content hash as before.
- **Enumerants** (opcodes, decorations, storage classes) come from the vendored SPIRV-Headers C++ header, not from hand-written numbers. The grammar JSON is not needed for this cut.

### 7.6 Diagnostics and debug info

- Every error is an engine `Diagnostic` (W05.2) with an ASL code and a source span. The emitter does not expect user errors: anything it rejects is a missed check earlier and is reported as an internal error naming the module and the IR node's `SourceLoc`.
- `spirv-val` messages in the Dev tier are internal errors too; they mean an emitter bug, never a user bug. Tests fail on them.
- Dev tier: `OpString` with the source module name, `OpSource`, `OpLine` per statement, `OpName` for user names. RenderDoc then shows ASL lines. `NonSemantic.Shader.DebugInfo` (local variables, scopes) is a later iteration.

### 7.7 Optimisation and SPIRV-Tools

- SPIRV-Tools (vendored, `vulkan-sdk-1.4.321.0`) is linked directly: `spvtools::SpirvTools` for validation in the Dev tier and tests, `spvtools::Optimizer` for optimisation.
- The `spirv-opt` pass list is chosen by measurement (#92 asks for the compile time and the gain on the engine shaders in the PR). Until measured, the Build tier runs no `spirv-opt` passes and the driver optimises; W11.3 records compile time with none, the performance recipe, and a short list.
- Engine-semantic passes (Q11.3) and the downgrades of 7.3 come later and are gated by W11.7's numbers.
- What reaches the GPU's ISA is mostly the information the module carries, since drivers inline calls: uniformity (scalar registers, scalar loads on AMD), `NonWritable` and absent aliasing, alignment, `NonUniform`. The borrow and uniformity analyses are therefore optimisation input, not only checks.

### 7.8 What is removed

glslang (vendor, CMake and link), `SpirvCompiler` and the `Spirv*` option headers under `Engine.Accel.Compile/Module/Spirv/`, `GlslEmitter` and `GlslRequirements`, `Dialect::eVulkanGlsl460`, the GLSL text path in `VkModuleBuilder::transpile`, the GLSL-specific diagnostic codes (ASL0063 `unsupported-target`, ASL0064 `no-glsl-form`) and the GLSL-text assertions in the Lang and Compile tests (they check the SPIR-V result instead: disassembly or a reflection of the module). The `rep` symbol readers are not migrated in W11.3 (owner, 2026-11-16): bind elements in `StageIr`, vertex formats in `VkPipelineCompiler`, `SymbolId`-based resource binding in render commands and the material parameter pairing keep working through a small adapter that builds the symbol table from the interface and the pipeline layout record. The adapter exists already: the second half of `lowerToIntermediate` builds the `rep` symbols from `computeInterface` and the layout, so it stays and only loses the GLSL text. The adapter carries a `shortcut:` comment and is deleted when render graph v2 (W14.2) replaces resource binding.

`VkModuleBuilder` today maps only vertex and fragment to a target stage; all six entry kinds map after W11.3. Pipeline creation for compute stays W12.2.

### 7.9 Verification

No GLSL parity suite (owner, 2026-11-14). W11.3 is done when:

- every engine shader under `assets/shader/**` and every Lang and Compile test fixture compiles to SPIR-V and passes `spirv-val`;
- the GPU harness tests (W26.2) pass unchanged on the SPIR-V path; their expected values do not depend on the backend;
- `InterfaceDesc` is emitted per entry point;
- glslang is out of the build;
- the PR records the compile time per shader against the glslang path (measured before the removal), the `spirv-opt` results of 7.7 and the module sizes of 7.3.

### 7.10 Later iterations

| Chunk | What |
|---|---|
| W11.4 | Interface check against pass declarations with both locations; uniformity already exists (`Ir/Uniformity.cpp`). |
| W11.5 | Language extensions: `switch`, mesh, ray query, ray tracing, `nonuniform`, subgroups, workgroup reuse, buffer addresses, generics, each before its first consumer. Per-value uniformity (needed by `nonuniform` and subgroups) arrives with them. |
| W11.6 | Value-range analysis in the Deep tier: intervals per vector component through swizzles, arithmetic, loops and calls; an index proven out of range is an error, a possible one a warning that shows the chain; runtime-sized arrays need a declared bound. Also lets the borrow check prove more disjointness (the arithmetic-proofs non-goal of section 4). |
| W11.7 | ISA measurement loop: per-variant registers, instruction count and occupancy from an offline ISA compiler (tool and its licence to be checked against the no-licensed-software rule), plus RGP captures; gates every optimisation above. |
| W12.x | Compute, mesh and task, ray tracing pipeline kinds; work graphs stay an enum value (Q12.1). |

### 7.11 Left to the builder

Explicit-conversion fixes in the engine shaders (expected to be few: the typechecker adapts only untyped literals today); builtin memory semantics (atomics, `barrier`) and `bool` and 8-bit block members keep their present meaning; the order of the W11.3 tasks; how tests assert on SPIR-V (disassembly text, a small reflection, or both); the internal shape of the lowered form; whether the Dev-tier checks move or stay where they run now (7.4); the `spirv-opt` short list (7.7).

## Sources

- Engine checkout, untracked: `docs/superpowers/specs/2026-10-28-accel-ir-design.md`, `docs/superpowers/specs/2026-11-07-ir-region-borrows-design.md`, plans `2026-10-28-accel-ir.md`, `2026-11-07-accel-ir-coverage.md`, `2026-11-07-ir-region-borrows.md`.
- Engine source: `src/Engine.Accel.Lang/Ir/{Module,Regions,Typecheck,Parser}.*`.
