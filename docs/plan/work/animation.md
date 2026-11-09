# Work: Animation

**Systems** S36 · **Issues** [#116](https://github.com/Heliogrim/Heliogrim-Engine/issues/116) · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Animation](../topics/animation.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| [Animation pipeline system page](../../systems/animation-pipeline.md) | Placeholder | Filled after W36.2 |
| `assets/shader/template/defined.skeletal.asl`, assimp import in `Editor.GFX.Loader` | A skinned vertex path and skeleton import exist | Skinning moves to a compute pre-skin pass into GPU geometry tables |
| [DCC work](dcc-plugins-vcs.md) S49 | glTF 2.0 brings skins, morphs, animations | Asset formats for skeleton and morphs are defined here, consumed by the importer |
| [Reflection work](serialization-and-reflection.md) S09 | Attributes and functions | Blend graph parameters are reflected properties |
| [Visual scripting work](visual-scripting-hmr.md) S47 | Graph compiler | Blend graph compiles to a flat node program through it later |
| [Physics work](physics-cloth.md) | Ragdolls and cloth after evaluation | Order inside the frame task graph |
| [Networking work](networking-mmo.md) S56 | Server-authoritative movement | Root motion reconciled through the character controller |

## Architecture

- **Bundles**: new `Engine.Animation` (assets, pose buffers, node program, evaluation tasks, LOD), `Engine.Animation.Compression` (ACL wrapper or in-house), `Engine.GFX.Render.Skinning` (compute pre-skin and morph pass), `Editor.Animation` (blend graph authoring, preview, retarget tool).
- **Provides**: per-instance poses, skinned geometry in GPU tables, root motion deltas, bone transforms for ragdolls and cloth colliders.
- **Consumes**: fiber scheduler (S02), reflection (S09), GPU geometry tables (S15), glTF import (S49), physics (S34, S35), graph compiler (S47, later), replication (S56, later).

## Code design

| Type | Contract |
|---|---|
| `Skeleton` | Bone hierarchy, rest pose, retarget profile; asset. |
| `AnimationClip` | Compressed tracks (ACL per Q36.1); `sample(t, PoseBuffer&)`; root motion track extracted at import. |
| `MorphTargetSet` | Sparse vertex deltas per target; weights in the pose state. |
| `PoseBuffer` | Per-instance local transforms plus morph weights; arena allocated per frame. |
| `NodeProgram` | Flat array of nodes `{ ClipSample, Blend, Additive, Inertialise, TwoBoneIk, Fabrik, MorphWeights, MotionMatch (optional) }` over pose buffers; pure functions; compiled from `BlendGraph` (S47 later; hand-built programs first). |
| `AnimationSystem : SceneSystem` | Batches instances per archetype; evaluation as parallel tasks; writes bone matrices and morph weights to GPU buffers; LOD policy by distance and screen size (update rate, bone culling, shared poses). |
| `Inertialiser` | Default transition: decaying offset from the previous pose; cross-fade only when authored. |
| `MotionDatabase` | Feature database built at import; optional node; after the baseline exists. |
| `SkinningPass` | Compute: linear blend or dual quaternion per asset, morph deltas applied, output into the GPU geometry tables so visibility buffer and shadows see one geometry path. |
| `Retargeter` | Rest-pose mapping between skeletons with bone name map and chain rules. |

Placement: `Engine.Animation/{Skeleton,AnimationClip,MorphTargetSet,PoseBuffer,NodeProgram,AnimationSystem,Inertialiser}`, `Engine.Animation.Compression/`, `Engine.GFX.Render.Skinning/SkinningPass`, `Editor.Animation/`. Tests: locomotion blend with inertialised transitions golden; 1,000-instance crowd budget; Blender and Maya clips identical; retarget test; skinned geometry through the visibility buffer.

## Work chunks

### W36.0 ACL build fit · explore · ready

- **Goal**: build ACL with clang-cl 22 under the vendor rules; measure decompression on a sample clip; decide vendor or in-house (Q36.1).
- **Output**: `architecture/animation-exploration.md`.

### W36.1 Animation system design · design · after W36.0, W09.1, W15.1

- **Goal**: assets, pose buffers, node program, evaluation scheduling, LOD, skinning pass, root motion, retargeting, DCC import contract.
- **Output**: `architecture/animation-design.md`; plan.
- **Questions**: Q36.2, Q36.3.

### W36.2 Implement assets, clip sampling, blend and inertialise, skinning pass · execute · after W36.1, W15.2, W49.2 (glTF skins)

- **Done when**: a character blends locomotion with inertialised transitions; skinned geometry renders through the visibility buffer and casts shadows.

### W36.3 Implement IK, morph targets, LOD, retargeting · execute · after W36.2

- **Done when**: two-bone IK on feet, morph-driven face, 1,000-instance crowd within budget, a retargeted clip runs on a second skeleton.

### W36.4 Motion matching node · execute · after W36.3 (Q36.3: after the first release)

### W36.5 Blend graph authoring through the S47 compiler · execute · after W47.3, W36.3

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q36.1 | Vendor ACL (Animation Compression Library, MIT, header-only) for clip compression if W36.0 builds it cleanly under clang-cl. |
| Q36.2 | Dual quaternion skinning as a per-asset option from the start, same skinning pass behind a flag. |
| Q36.3 | Motion matching after the first version, once clip sampling, blending and inertialisation exist. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q36.1 | ACL vendored (MIT, header-only) or in-house compression? | W36.1 | Vendor ACL if W36.0 builds cleanly |
| Q36.2 | Dual quaternion skinning as a per-asset option in the first version, or linear blend only? | W36.1 | Per-asset option from the start (same pass) |
| Q36.3 | Motion matching in the first release or after? | W36.1 | After |
