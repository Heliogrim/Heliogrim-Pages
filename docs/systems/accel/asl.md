# ASL Language

**Status**: <span class="hg-status design">experimental</span>
**Verified against**: engine commit [`d0c66b4a`](https://github.com/Heliogrim/Heliogrim-Engine/tree/d0c66b4a10d9f2e1395b4f134044fa228f330ea4), 2026-11-08
**Source of truth**: [`Ir/Lexer.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Lexer.cpp), [`Ir/Parser.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Parser.cpp), [`Ir/Parser.Body.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Parser.Body.cpp), [`Ir/Typecheck.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Typecheck.cpp), [`Ir/Builtin.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/d0c66b4a10d9f2e1395b4f134044fa228f330ea4/src/Engine.Accel.Lang/Ir/Builtin.hpp)

ASL (Accel Shading Language) is the engine's shader language. It reads like GLSL with Rust-style declarations. One `.asl` file is one **module**; a module with `fn main` is a shader stage, a module without one is a library. Part of the [Accel shader toolchain](index.md).

!!! note "What ASL is for"
    ASL exists so that a shader states its own interface. You name every input, output and binding with a string id; the toolchain assigns set, binding, location and `constant_id` numbers. You never write a number for any of them.

## Module structure

A module is, in order:

1. `#include <path>` lines (must come before any declaration).
2. Declarations, in any order: toggles, constants, structs, bindings, `workgroup` variables and functions.

```c
#include <shared/math.asl>                         // 1. includes first

toggle Shadows : { Off, Pcf } = Pcf;               // toggle
const EXPOSURE: f32 = 4.5;                         // module constant
struct Light { f32vec4 position; f32vec4 color; }; // struct

@input (mode = bind, id = "lights", class = storage) block lights { Light[] items; };
@output (mode = forward, id = "color") f32vec4 color;

fn shade(l: &Light) -> f32vec3 { return l.color.rgb * EXPOSURE; }  // function
fn main() { color = f32vec4(shade(lights.items[0u]), 1.0); }      // entry point
```

`#include` is module-level, not textual: the included module is parsed into the same result before the includer, each module at most once per parse. The stage kind (vertex, fragment, ...) is not written in the file; the loader passes it to `parseModule`, and the file name convention is `name.vs.asl`, `name.fs.asl`.

## Types

| Kind | Spelling | Notes |
|------|----------|-------|
| Scalar | `f16`, `f32`, `f64`, `s8` to `s64`, `u8` to `u64`, `bool` | `s` = signed, `u` = unsigned; the number is the bit width |
| Vector | `f32vec3`, `u32vec2`, `s16vec4`, ... | 2 to 4 components |
| Matrix | `f32mat4`, `f32mat4x3` | float only; `matCxR` = C columns, R rows |
| Array | `T[4]`, `T[]` | `T[]` (unsized) only as the last member of a storage block |
| Struct | `struct Name { T a; U b; };` | |
| Texture | `texture1d`, `texture2d`, `texture2darray`, `texture3d`, `texturecube` | sampled with a separate `sampler` |
| Sampler | `sampler` | |
| Storage image | `image2d<rgba8>` | formats `rgba8`, `rgba16f`, `r32f`, `r32ui` |

There are **no implicit numeric conversions**. An untyped literal adapts to its context (`0` compared to an `f32` is `0.0`), but `s32 * f32` is an error. Types narrower or wider than 32 bits make the emitter enable the matching GLSL extension and report the Vulkan feature they need (for example `shaderInt8`, `storageBuffer16BitAccess`).

## Inputs, outputs and bindings

Every interface variable carries an annotation. `mode` says how the value arrives:

- `mode = forward`: passed between stages (vertex attributes, varyings, fragment outputs). Gets a location.
- `mode = bind`: a resource bound through a descriptor or push constant. Needs a `class`.

```c
// stage-to-stage values
@input  (mode = forward, id = "local-uv") f32vec2 local_uv;
@output (mode = forward, id = "color")    f32vec4 color;

// descriptor resources
@input (mode = bind, id = "material.albedo",         class = texture) texture2darray mat_albedo;
@input (mode = bind, id = "material.albedo-sampler", class = sampler) sampler mat_albedo_sampler;

// a bound block: anonymous struct type, used as camera.vp
@input (mode = bind, id = "camera", class = uniform) block camera { f32mat4 vp; };

// writable storage buffer
@input (mode = bind, id = "buf", class = storage, access = read_write) block buf { u32[] data; };

// push constants
@input (mode = bind, id = "draw", class = push) block draw { u32 cascade; };
```

| Key | Values | Meaning |
|-----|--------|---------|
| `mode` | `forward`, `bind` | see above |
| `id` | string | identity across modules, stages, passes and materials |
| `class` | `uniform`, `storage`, `texture`, `sampler`, `push`, `image` | descriptor kind (bind only) |
| `access` | `read`, `write`, `read_write` | storage and image bindings; default `read` |
| `packing` | `std140`, `std430` | block layout |
| `patch` | `true` | per-patch value between tessellation stages |

**The `id` is the identity**, not the variable name. Two modules may name the variable differently; if the ids match, they are the same resource. The same id with a different type in two modules of one stage is a merge error naming both.

`implicit` marks an output with no GLSL variable behind it. The depth-only fragment shader uses it to declare that it produces `depth` (written by fixed-function hardware), so the pass can require it:

```c
@output (mode = forward, id = "depth") implicit f32 depth;

@fragment (early_fragment_tests = true)
fn main() {
}
```

Geometry and tessellation inputs are written as unsized arrays, one element per vertex: `@input (mode = forward, id = "world-pos") f32vec4[] p;`.

## Constants and specialisation constants

```c
const EXPOSURE: f32 = 4.5;                                   // must be a constant expression
@spec (id = "sample-count") const SAMPLE_COUNT: u32 = 1024u; // Vulkan specialisation constant
```

A `@spec` constant gets its `constant_id` from the layout pass, numbered once per pipeline from the sorted spec ids. Inside functions, `const` is an immutable local whose initialiser may be any expression.

## Functions

```c
fn saturate(v: f32vec3) -> f32vec3 {
	return clamp(v, 0.0, 1.0);
}

fn GetWorldNormal() -> f32vec4;   // forward declaration: a body must come from another module
```

- **Overloads** are allowed and resolved by exact parameter types; there are no generics.
- **Forward declarations** state a signature the module needs. After merging, every declared function needs exactly one body per toggle combination; the error names the function and the missing combination.
- **`@redefine (allow = true)`** on a function lets a later module replace its body (last one wins). Without it, a second body is an error.

### Parameters and references

Everything is immutable unless you say otherwise.

| Parameter | Meaning | Emitted GLSL |
|-----------|---------|--------------|
| `x: T` | immutable value | `const in T x` |
| `x: &T` | immutable reference | `const in T x` |
| `x: &mut T` | mutable reference | `inout T x` |

Locals:

```c
struct Light { f32vec4 position; f32vec4 color; };
@input (mode = bind, id = "lights", class = storage) block lights { Light[] items; };
@input (mode = bind, id = "out", class = storage, access = read_write) block out_data { f32vec4[] values; };

fn main() {
	let i: u32 = 0u;
	let v = f32vec3(1.0);

	let a = 1.0;            // mutable, type inferred
	let b: u32 = 0u;        // mutable, typed
	f32vec3 c = f32vec3(0); // GLSL-style typed local, mutable
	const n = normalize(v); // immutable; any initialiser

	let L = &lights.items[i];         // read-only alias: no copy
	let o = &mut out_data.values[i];  // writable alias (index the member, not the block)
	o = L.color;
}
```

A local reference is an **alias**, not a variable: the emitter replaces every use with the place expression and hoists a non-constant index into a `const` temporary at the alias point. `let L = &lights.items[i]; L.color` therefore costs no copy of the struct.

Rules that keep references safe without lifetimes:

- references exist only as parameters and locals: no reference returns, no references in structs;
- an alias cannot be re-bound; `const l = &mut x;` is an error;
- you cannot assign through `&`, to a read-only binding, a constant or a read-only builtin;
- a `&mut` argument may not share its root with another argument of the same call (`F(a, a)` is an error), because GLSL `inout` copies in and out and aliasing would change the result.

## Control flow

`if`/`else`, `for`, `while`, `break`, `continue`, `return`, `discard` and the ternary `c ? a : b` work as in GLSL, with two rules for GPU execution:

!!! warning "Loops must have a real exit condition"
    On SIMT hardware, a `break` under a lane-dependent condition only masks that lane; the wave stays in the loop until every active lane has left. `while (true)` and `for (;;)` are rejected: write a bounded condition.

```c
// rejected: lanes that never reach break keep the whole wave looping
while (true) { if (done) { break; } }

// accepted: bounded
let minLod = 1.0;
while (!sparse_resident(code) && minLod < 14.0) {
	code = sample_sparse_clamp(tex, smp, uv, minLod, value);
	minLod += 1.0;
}
```

The **uniformity analysis** marks every statement as running under uniform or lane-dependent control:

- `barrier()` under lane-dependent control (directly or inside a called function) is an **error**: lanes that skip it deadlock the workgroup.
- Derivatives (`dFdx`, `fwidth`), implicit-LOD `sample` and `sample_sparse*` under lane-dependent control are **warnings**: GLSL leaves their result undefined. The sparse retry loops in `brdf/gbuffer.fs.asl` trigger this warning on purpose; the file says so in a comment.

## Toggles and `@when`

A toggle is a named switch with a closed set of values and a default. `@when` makes a declaration, a block of declarations or a statement depend on toggle values. The toolchain resolves one combination per variant; code that is not active does not exist in that variant, including its bindings.

```c
#include <spec/defined.static.asl>   // declares VertexOutputPosition, VertexWorldPosition, ...
#include <spec/defined.skeletal.asl>

toggle PassContext : { DepthOnly, Material } = Material;

@when (PassContext == Material) {
	@output (mode = forward, id = "world-position") f32vec4 world_position;

	fn main() {
		position = VertexOutputPosition();
		world_position = VertexWorldPosition();
	}
}

@when (PassContext == DepthOnly)
fn main() {
	position = VertexOutputPosition();
}
```

Conditions combine with `&&`, `||`, `!`, `any(...)`, `all(...)` and `none(...)`.

Values are fixed from four sources, strongest first: **pass > profile > material > module default**. A weaker source that disagrees with a stronger one is a warning and the stronger value wins; an unknown toggle or a value outside the declared set is an error.

Exhaustiveness is checked for code that is actually used. `spec/defined.asl` declares `fn GetWorldNormal() -> f32vec4;` next to `toggle MeshType : { Static, Skeletal }`. If a shader includes it and calls `GetWorldNormal()`, but only `defined.static.asl` is merged in, resolving `MeshType = Skeletal` fails with `no body for 'GetWorldNormal()' at MeshType=Skeletal`. A forward declaration nobody calls needs no body. Calling a function that no included module declares fails earlier, at parse: `Unknown function 'GetWorldNormal'.`

## Stage attributes

Execution attributes go on `fn main`. An attribute that does not fit the stage is an error.

```c
@compute (local_size = [8, 8, 1])
@geometry (input = triangles, output = triangle_strip, max_vertices = 3, invocations = 1)
@tess_ctrl (output_vertices = 3)
@tess_eval (domain = triangles, spacing = equal, winding = ccw)
@fragment (early_fragment_tests = true)
```

## Compute: workgroup memory and region borrows

A module-scope `workgroup` variable is shared by the workgroup (GLSL `shared`):

```c
workgroup tile: f32[64];

@compute (local_size = [64, 1, 1])
fn main() {
	tile[local_invocation_index] = 1.0;
	barrier();
}
```

**Region borrows** hand out windows of a buffer or workgroup array, for example one slice of a scratchpad per thread. A region parameter is `&mut T[]`; a region is made with `base[lo .. hi]`; `len(r)` is its length.

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
		let r = &mut scratch[b .. b + 8u];   // this lane's window
		r[1u] = 5u;                          // writes scratch[b + 1u]
	}
	fill(scratch[0u .. 8u], 0u);             // pass a region to a function
}
```

A borrow stays live until the end of its block. Without the inner `{ }`, the `fill` call is rejected: `'&mut' argument 'scratch[0u .. 8u]' overlaps live borrow 'scratch[b .. (b + 8u)]' of call to 'fill'`. `b .. b + 8u` and `0u .. 8u` may overlap, and the checker cannot prove otherwise.

Rules:

- the root must be a storage buffer or a `workgroup` array; a local or parameter array is an error;
- the root itself may not carry a runtime index (`buf.data[i][0 .. 4]` is rejected);
- while a region is live, other borrows of the same root must be provably disjoint (different fields, constant indices, non-intersecting constant ranges, or ranges where one's `hi` is literally the other's `lo`); anything unprovable counts as an overlap;
- names ending in the suffixes the lowering generates (`__off`, `__len`, `__end`, `__i<k>`, and `__r<k>` for functions) and names starting with `_hg_` are reserved.

The [IR page](ir.md#lowerregions-borrows-become-index-math) shows what this lowers to.

## Builtins

Builtin variables use readable names and map to GLSL:

| ASL | GLSL | Stages |
|-----|------|--------|
| `position` | `gl_Position` | vertex, geometry, tessellation |
| `frag_coord`, `front_facing`, `frag_depth` | `gl_FragCoord`, `gl_FrontFacing`, `gl_FragDepth` | fragment |
| `vertex_index`, `instance_index`, `view_index` | `gl_VertexIndex`, ... | vertex |
| `global_invocation_id`, `local_invocation_id`, `local_invocation_index`, `workgroup_id`, `num_workgroups` | `gl_GlobalInvocationID`, ... | compute |
| `tess_level_outer`, `tess_level_inner`, `tess_coord`, `patch_vertices`, `invocation_id`, `primitive_id`, `layer` | `gl_TessLevelOuter`, ... | geometry, tessellation |

Builtin functions: GLSL math (`abs`, `clamp`, `mix`, `smoothstep`, `pow`, `dot`, `cross`, `normalize`, `reflect`, `inverse`, ...), derivatives, sampling (`sample`, `sample_lod`, `sample_sparse`, `sample_sparse_clamp`, `sparse_resident`, `texture_size`), images (`image_load`, `image_store`, `image_size`), atomics (`atomic_add`, `atomic_min`, ..., `atomic_comp_swap`), `barrier`, `memory_barrier_shared`, and `emit_vertex`/`end_primitive` for geometry. Using a builtin the stage does not have is an error on the merged stage.

## Errors you will meet

Diagnostics carry the file, line and column of the offending token. Parsing continues after an error, so one run reports all of them.

| Message (shortened) | Cause |
|---------------------|-------|
| `Unknown function 'F'.` | a call to a function no included module declares |
| `no body for 'F()' at A=x` | a called function has no body for that toggle combination |
| `overlapping bodies for 'F' at ...` | two `@when` bodies are active at once |
| `cannot assign through immutable reference 'x'` | write through a `&T` parameter or alias |
| `cannot take '&mut' into a 'const' alias` | `const l = &mut x;` |
| `'&mut' argument 'a' overlaps argument 'a' of call to 'F'` | two arguments of one call share a root |
| `'&mut' argument '...' overlaps live borrow '...' of call to 'F'` | passing a region that may overlap a live borrow |
| `cannot index type block { ... }` | indexing a block instead of its array member (`buf[i]` instead of `buf.data[i]`) |
| `loop condition is constant; ...` | `while (true)` / `for (;;)` |
| `'barrier' under lane-dependent control; ...` | barrier inside a lane-dependent branch |
| `'...' uses implicit derivatives under lane-dependent control; ...` | warning: derivative or implicit-LOD sample in a lane-dependent branch or loop |
| `... must be rooted in a buffer or workgroup array` | region over a local array |
| `... shadows the root of live region '...'` | a local, or a parameter of a region-taking function, named like the root of a live region (reported by region lowering) |
