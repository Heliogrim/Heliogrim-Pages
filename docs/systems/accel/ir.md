# Accel IR and Passes

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`d0c66b4a`](https://github.com/Heliogrim/Heliogrim-Engine/tree/d0c66b4a10d9f2e1395b4f134044fa228f330ea4), 2026-11-08
**Module**: `Engine.Accel.Lang`, namespace `hg::engine::accel::lang::ir`, folder [`src/Engine.Accel.Lang/Ir`](https://github.com/Heliogrim/Heliogrim-Engine/tree/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir)

The IR is what a parsed [ASL](asl.md) module becomes, and what every step between parsing and GLSL emission reads and writes. This page describes the data model, then each pass in the order the compiler runs them. Part of the [Accel shader toolchain](index.md).

## Data model

One `ir::Module` per source module (and later per merged stage). It is a plain value type: copyable, comparable by content, no pointers.

```cpp
struct Module {
	String name;
	EntryKind entry;              // eVertex, eTessCtrl, eTessEval, eGeometry, eFragment, eCompute
	EntryAttributes attributes;   // local_size, early_fragment_tests, geometry/tess settings
	Vector<Toggle> toggles;
	Vector<TypeDesc> types;       // type table
	Vector<BindingDecl> bindings; // @input / @output / workgroup
	Vector<ConstantDecl> constants;
	Vector<FunctionDecl> functions;
	Vector<Expr> exprs;           // expression arena
	Vector<Stmt> stmts;           // statement arena
	Diagnostics warnings;         // non-fatal, not hashed
};
```

### Arenas and index handles

Function bodies are an AST stored in two flat arenas, `exprs` and `stmts`. Nodes point at each other with typed 32-bit indices (`ExprRef`, `StmtRef`, `TypeRef`, `BindingRef`, `FunctionRef`, `ConstantRef`); `~0` means "unset". Because nothing is a pointer, a module can be copied, two modules can be appended (shift every ref by an offset), and a pass can rebuild the arenas while keeping the meaning.

```hg-diagram
flowchart LR
    subgraph F["functions"]
        F0["[0] main()<br/>body = stmt 0"]
    end
    subgraph S["stmts"]
        S0["[0] eBlock<br/>children = 1"]
        S1["[1] eAssign<br/>lhs = expr 0, rhs = expr 1"]
    end
    subgraph E["exprs"]
        E0["[0] eNameRef 'color'<br/>binding = 2"]
        E1["[1] eConstruct f32vec4<br/>operands = 2, 3"]
        E2["[2] eNameRef 'src'<br/>local"]
        E3["[3] eLiteral '1.0'"]
    end
    subgraph B["bindings"]
        B2["[2] @output 'color'"]
    end
    F0 --> S0 --> S1
    S1 --> E0
    S1 --> E1
    E1 --> E2
    E1 --> E3
    E0 --> B2
```

The picture is `color = f32vec4(src, 1.0);` from the post-processing shader. `Expr` and `Stmt` are flat tagged structs: one `kind`, and only the members that kind uses are meaningful (see the comments in [`Ir/Module.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Module.hpp)).

| Arena | Kinds |
|-------|-------|
| `ExprKind` | literal, name ref, call, field (incl. swizzle), index, unary, binary, construct, builtin, ternary, range (`base[lo .. hi]`) |
| `StmtKind` | declare local, declare ref (alias), assign (`=`, `+=`, ...), expression, return, block, when, if, for, while, break, continue, discard |
| `TypeKind` | scalar, vector, matrix, array, struct, texture, sampler, image, region |

Every node keeps a `SourceLoc` for diagnostics; locations are never part of the content hash.

### Conditions and toggles

A `Toggle` is a name, its value list and a default. Declarations and `when` statements carry a `Condition` tree (`eTrue`, `eEquals`, `eNot`, `eAnd`, `eOr`). A `ToggleSet` is a sorted list of `(toggle, value)` pairs. `findUncovered` enumerates the combinations and returns the first one no arm covers; that is how "no body for 'F' at A=x, B=y" is found.

### The legacy bridge: `lang::Intermediate`

The older parts of the engine (module builder, pipeline compiler, effects) speak `lang::Intermediate`: a `Language` (dialect plus GLSL text blocks) and a `Representation` (variables with `SymbolId`, linkage and Vulkan location annotations). The IR rides along inside it as `smr<const ir::Module> ir`. Loading an `.asl` file fills only `ir`; after composition, `lowerToIntermediate` fills `lang` and `rep` from the resolved module so the older code keeps working.

## The passes, in order

```hg-diagram
flowchart LR
    A["parse +<br/>typecheck"] --> B["merge"] --> C["fix +<br/>resolve toggles"] --> E["slice"] --> F["interface"] --> G["contracts"] --> H["layout"] --> D["lower<br/>regions"] --> I["emit GLSL<br/>+ lower"]
```

Each pass takes a module by `const` reference and returns a new one (or diagnostics), so a pass can be tested alone with a hand-written input.

### parseModule

[`Ir/Parser.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Parser.hpp)

```cpp
using ModuleResolver = FnRef<Opt<String>(StringView name_)>;

std::expected<Module, Diagnostics> parseModule(
	StringView name_, StringView source_, EntryKind entry_, ModuleResolver includes_);
```

The lexer and a hand-written recursive-descent parser build the arenas. `#include <x>` asks the resolver for the source of `x` and parses it into the same module first. Parsing does not stop at the first error. `typecheck` then types every expression, infers `let` types, resolves overloaded calls by exact parameter types, and enforces the mutability, reference and loop rules from the [language page](asl.md).

### merge

[`Ir/Merge.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Merge.hpp)

An `EffectProfile` injects library modules into every stage it compiles (for example the mesh-type bodies of `spec/defined.static.asl`). `merge` combines them with the stage module, profile modules first and the shader last:

- **Functions** by signature. Bodies under the same `@when` condition are the same variant; a second body is an error unless the earlier one is `@redefine (allow = true)`. Satisfied forward declarations disappear.
- **Bindings** by id. The same id collapses into one binding (conditions OR-ed) if type, mode, class, direction and `implicit` agree; anything else is an error naming both modules.
- **Toggles** by name, if value list and default agree.
- **Types** structurally, so `f32vec4` from two modules is one type.

```c
// profile module (merged first)
@redefine (allow = true) fn Albedo() -> f32vec3 { return f32vec3(1.0); }

// shader module (merged last): replaces the body, allowed by @redefine
// (its bindings albedo, albedo_sampler and the uv input are declared as usual)
fn Albedo() -> f32vec3 { return sample(albedo, albedo_sampler, uv).rgb; }
```

Merge holds no state and is deterministic for the same input order. It replaced the old text concatenation in `StageComposer` (preamble + macros + module text + shader text).

### fixToggles and resolveToggles

[`Ir/Resolve.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Resolve.hpp)

`fixToggles` picks one value per declared toggle from the `ToggleSources` (pass, profile, material, default; first wins and conflicts are warnings). `resolveToggles` then produces the module for exactly that combination:

- declarations whose condition is false are dropped;
- a `when` statement becomes its active arm;
- calls and binding uses re-resolve against what survives;
- the arenas are rebuilt by `compact` so they hold only the surviving code.

For `brdf/gbuffer.vs.asl` at `PassContext = DepthOnly`, the three `@output` declarations and the material `main` vanish; the result is a module with one `main` that writes `position`.

### lowerRegions: borrows become index math

[`Ir/Regions.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Regions.hpp)

GLSL has no pointers or slices, so region borrows are rewritten into offsets. This runs last, inside `lowerToIntermediate` right before the GLSL emitter, so every earlier pass (and the content hash) sees the borrows as written. A local region becomes two constants; a function that takes a region is cloned per call site root.

=== "ASL"

    ```c
    workgroup scratch: u32[256];

    fn fill(v: &mut u32[], value: u32) {
    	for (let i: u32 = 0u; i < len(v); i += 1u) {
    		v[i] = value;
    	}
    }

    @compute (local_size = [32, 1, 1])
    fn main() {
    	const b: u32 = local_invocation_index * 8u;
    	{
    		let r = &mut scratch[b .. b + 8u];
    		r[1u] = 5u;
    	}
    	fill(scratch[0u .. 8u], 0u);
    }
    ```

=== "Emitted GLSL"

    ```glsl
    #version 460

    layout(std430) buffer;
    layout(local_size_x = 32, local_size_y = 1, local_size_z = 1) in;

    shared uint scratch[256];

    void fill__r0(const in uint v__off, const in uint v__end, const in uint value);

    void main()
    {
    	const uint b = (gl_LocalInvocationIndex * 8u);
    	{
    		const uint r__off = b;
    		const uint r__len = ((b + 8u) - r__off);
    		scratch[(r__off + 1u)] = 5u;
    	}
    	fill__r0(0u, 8u, 0u);
    }

    void fill__r0(const in uint v__off, const in uint v__end, const in uint value)
    {
    	const uint v__len = (v__end - v__off);
    	for (uint i = 0u; (i < v__len); i += 1u)
    	{
    		scratch[(v__off + i)] = value;
    	}
    }
    ```

The right tab is the emitter's actual output for the left tab (checked 2026-11-08). The region-taking `fill` is replaced by `fill__r0`, one copy per callee and region root, which takes the region as `[off, end)`. `len(v)` becomes `v__len`. A nested region (`&mut r[2u .. 4u]`) adds its offset to the parent's. The inner `{ }` is needed: while `r` is live, the call's `scratch[0u .. 8u]` might overlap it and is rejected (see [region rules](asl.md#compute-workgroup-memory-and-region-borrows)).

### slice

[`Ir/Slice.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Slice.hpp)

A pass rarely needs everything a shader can produce. `slice(mod, requiredOutputIds)` keeps only what the required outputs depend on, using a def-use walk over the function bodies:

- outputs not in the list are dropped with the statements writing them; builtins (`position`, `frag_depth`) always stay;
- a statement is live if it writes a kept output, a builtin or a non-local, or if its expressions call a function that might; a local definition is live if a live statement reads it;
- functions survive if `main` reaches them from live code; bindings survive if live code touches them.

Example, sliced to `["a"]`:

```c
@input (mode = forward, id = "uv") f32vec3 uv;
@input (mode = bind, id = "tex", class = texture) texture2darray tex;
@input (mode = bind, id = "tex-sampler", class = sampler) sampler smp;
@output (mode = forward, id = "a") f32vec4 a;
@output (mode = forward, id = "b") f32vec4 b;

fn helper() -> f32vec4 { return sample(tex, smp, uv); }

fn main() {
	a = f32vec4(1.0);
	b = helper();   // dropped with output b, helper and the tex, tex-sampler, uv bindings
}
```

The slice is conservative. A function that passes anything by `&mut`, whether to a user function or to a builtin like `sample_sparse(..., value)`, counts as "may write a kept target", even when the written place is a local. A statement calling it stays live, and so does the output it writes. For the same module with `fn helper() -> f32vec4 { let v = f32vec4(0.0); let c = sample_sparse(tex, smp, uv, v); return v; }`, the slice keeps `b` and all its bindings. In the shipped shaders this means slicing `brdf/gbuffer.fs.asl` (at `PassContext = Material`) to `["brdf-albedo"]` keeps every output and every function, because all three samplers use `sample_sparse`. Sound, but no saving.

An empty list keeps the module as it is. Slicing comes after toggle resolution because unresolved `@when` variants can name the wrong function.

### computeInterface

[`Ir/Interface.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Interface.hpp)

Lists every binding of the resolved, sliced module as an `InterfaceEntry` (id, type, mode, class, direction, implicit, arrayed, patch, and a module-independent `typeName`), sorted inputs first, then by id. Implicit outputs are entries too. This list is what tests assert and what the layout and contract checks read.

### checkContract and checkStageChain

[`Ir/Contract.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Contract.hpp)

```hg-diagram
flowchart LR
    VS["vertex interface<br/>out: world-position f32vec4"] -- "checkStageChain<br/>id + type must match" --> FS["fragment interface<br/>in: world-position f32vec4"]
    MAT["material bindings<br/>material.albedo, ..."] -- "checkContract" --> FS
    PASS["pass StageContract<br/>provides / requires"] -- "checkContract" --> FS
```

- `checkContract`: every bind input must have a class and be provided by the material or the pass; every requirement of the pass must be met by some shader output.
- `checkStageChain`: every forward input of stage N+1 must match a non-implicit forward output of stage N by id and type. Extra outputs are fine; vertex inputs are attributes and not checked.

Intended rule (battle plan S11): when the pass and the shader disagree, the shader interface is the contract and the pass gets the diagnostic. Today the compiler builds the pass side as "provides every bind input, requires nothing" (see [compiler integration](compiler.md#limits)), so only a missing bind class and unknown target symbols fail. Since W11.4 (`1cc9e75c`, after the verified commit) entries carry their declaration span and contract and stage-chain errors label both sides; see [compiler integration](compiler.md#limits) for the declared contract.

### assignLayout and assignPipelineLayout

[`Ir/Layout.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Layout.hpp)

This is where every number comes from. `assignPipelineLayout` runs one layout over the union of all stages, so an id used by vertex and fragment stage has the same slot in both.

| Output | Rule |
|--------|------|
| Descriptor slots | set 0, ordered by class (uniform, storage, texture, sampler) then id, packed from binding 0 |
| Push ranges | packed in id order, offsets aligned to `max(alignment, 4)`, size = std430 size rounded to 4 |
| Input locations | ascending from 0 in id order; a matrix takes one per column, an array one per element. A stage directly behind another IR stage instead reads each input at the location its producer writes it |
| Output locations | numbered in interface (id) order, each taking its location count |
| Spec constant ids | distinct spec ids sorted, from 0, once per pipeline |

The layout can also **reuse** slots of existing layouts so shaders share descriptor set layouts. It trades three configurable costs:

```cpp
struct LayoutWeights {
	float unusedSlotCost = 1.0f;  // per binding number skipped to line up with an existing layout
	float extraLayoutCost = 4.0f; // per binding that gets a new number instead of reusing one
	float extraSetCost = 8.0f;    // for opening another descriptor set
};
```

A slot of an existing layout with the same class and structural type is reused if `unusedSlotCost * skipped < extraLayoutCost`. Example: an existing layout has `camera` (uniform, `f32mat4`) at binding 3; a new shader with a structurally equal uniform reuses binding 3 and skips 0..2 (cost 3 < 4). Had it been at binding 5, skipping 5 numbers costs more than a new binding, so it gets binding 0 instead. Output is deterministic for the same entries and weights, whatever their order.

std430 rules used for blocks and push ranges: `vec3` is 12 bytes aligned to 16, `mat4` is 64 bytes, array stride is the element size rounded to its alignment, structs are not rounded to `vec4` (unlike std140).

### Uniformity and analysis

[`Ir/Uniformity.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Uniformity.hpp), [`Ir/Analysis.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Analysis.hpp)

`analyzeUniformity` marks per statement whether it may run under lane-dependent control (a condition built from a per-lane builtin such as `local_invocation_id`, a forward input, a user function result, or anything assigned from those; uniform, push and storage block reads with uniform indices count as uniform) and per function whether it needs uniform control (contains `barrier`, directly or through calls). The typechecker uses it for the barrier error and the derivative warnings. `usageOf` and `reachableFunctions` give per-function call and read/write sets; slicing and merge build on them.

### compact

[`Ir/Compact.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Compact.hpp)

The shared back half of `resolveToggles` and `slice`: given which functions, bindings, constants and statements survive, it rebuilds the arenas in one canonical order (pre-order per body, functions in order). Equal surviving code gives equal arenas whatever was dropped, which keeps content hashes stable.

## Variants and caching

[`Ir/Variant.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Variant.hpp)

```cpp
struct VariantKey {
	u64 mod;     // contentHash(module): name, entry, toggles, declarations, reachable code
	u64 toggles; // sorted toggle values
	u64 outputs; // sorted required output ids
};
```

`contentHash` is a streaming FNV-1a over the module's content. Types are hashed by structure, never by arena index, and unreachable arena nodes are never visited, so two equal modules hash equal even if their arenas differ. This replaces the old `HashedState` keys, which hashed object addresses and profile names and collided or missed.

| Cache | Key | Value |
|-------|-----|-------|
| `VariantCache` | `VariantKey` | `Resolved`: resolved + sliced module, interface, key |
| `PipelineLayoutCache` | `Vector<VariantKey>` (stages in order) | `ResolvedPipeline`: stages, per-stage layouts, lowered intermediates |

Both build outside the lock; if two threads build the same key, the first result is kept and returned to both. A null build result is not cached, so a failing variant is retried (and reported) on the next request.

## Testing a pass

Every pass is a free function over values, so a test is "parse, run, compare":

```cpp
TEST(IrSliceTest, DropsUnrequestedOutput) {
	const auto mod = parse(
		"@output (mode = forward, id = \"a\") f32 a;\n"
		"@output (mode = forward, id = \"b\") f32 b;\n"
		"fn main() { a = 1.0; b = 2.0; }\n");
	const auto sliced = slice(mod, std::array { String { "a" } });
	const auto entries = computeInterface(sliced);
	ASSERT_EQ(entries.size(), 1uz);
	EXPECT_EQ(entries[0].id, "a");
}
```

(Illustrative; the real tests live in `src/Engine.Accel.Lang.Test/Ir*Test.cpp`.)
