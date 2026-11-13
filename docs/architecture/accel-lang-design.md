# Accel Lang (Design)

**Status**: design record, written 2026-11-13 (work chunk [W11.0](../plan/work/accel-lang.md), issues [#82](https://github.com/Heliogrim/Heliogrim-Engine/issues/82), [#148](https://github.com/Heliogrim/Heliogrim-Engine/issues/148)). It moves the two engine-side specs onto the site: the Accel IR design (2026-10-28, milestones 1 and 2) and the region-borrow design (2026-11-07, PR [#156](https://github.com/Heliogrim/Heliogrim-Engine/pull/156)). Both milestones are on `master` and `feat/wip`. How the code works today is on the system pages [ASL Language](../systems/accel/asl.md) and [Accel IR and Passes](../systems/accel/ir.md); this page holds the intent, the rules and who decided them.

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
| **GLSL is emitted** into the existing glslang path; direct SPIR-V is W11.2. GLSL stays the oracle until then. | Builder's call; Q11.2: Slang is neither oracle nor backend |
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

Pass order: parse and typecheck, merge, fix and resolve toggles, slice, interface, contracts, layout, lower regions, emit GLSL. Each pass takes a module by `const` reference and returns a new one or diagnostics, so each one can be tested alone.

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
| Borrow lowering on the GLSL path versus in a SPIR-V emitter (left open on purpose). | W11.2 |
| GPU render of the migrated shaders never verified. | W26.2 |
| `InterfaceDesc` export for the render graph. | W11.3 |
| `HashedState` is still address- and name-based in `Engine.Accel.Storage`. | W13.1 (`VariantKey`) |
| Name collisions the reserved-name check does not catch: a user name equal to a GLSL builtin function (`max`, `textureLod`; only `texture` is reserved), a `<binding>_block` type name against a user struct, a local or parameter `f__r<k>` hiding the generated region function, the int8/16/64 and float16 extension type names. Until W11.2 each one surfaces as a glslang gate failure. | W11.2: the GLSL intermediate is replaced. The SPIR-V backend identifies everything by result id and keeps names only as debug info, so a collision cannot be expressed at all (make incorrect states unrepresentable), not just detected. |

## Sources

- Engine checkout, untracked: `docs/superpowers/specs/2026-10-28-accel-ir-design.md`, `docs/superpowers/specs/2026-11-07-ir-region-borrows-design.md`, plans `2026-10-28-accel-ir.md`, `2026-11-07-accel-ir-coverage.md`, `2026-11-07-ir-region-borrows.md`.
- Engine source: `src/Engine.Accel.Lang/Ir/{Module,Regions,Typecheck,Parser}.*`.
