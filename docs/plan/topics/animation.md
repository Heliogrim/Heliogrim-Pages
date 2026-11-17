# Animation

**Systems**: S36 · **Track** C · **Milestone** M4
**Status**: <span class="hg-status summary">plan</span>. Research from [simulation](../sources/research-simulation.md) section 3 (ACL README verified; the rest unverified). The [animation pipeline system page](../../systems/animation-pipeline.md) is a placeholder.

## Target

A skeletal animation pipeline: clips with compression, a blend graph with state machines, inertialised transitions, motion matching as an optional node, IK (two-bone, FABRIK, full-body), retargeting, morph targets with corrective shapes, GPU skinning (linear blend and dual quaternion), animation LOD for crowds, and clean import from Blender, Maya and 3ds Max (S49).

## Current state (checked 2026-11-07)

- A skeletal vertex path exists in `assets/shader/template/defined.skeletal.asl`; assimp import brings skeletons in through `Editor.Graphics.Loader`. No runtime animation system, no clips, no blending.

## Research summary

- ACL (README and performance docs verified): MIT, header-only C++11, allocator and assert hooks; on the CMU database v2.1.0 reaches about 21.8:1 (1,429 MB raw to 66 MB) with a 0.05 cm max error; `decompress_pose` medians on an iPad of about 0.9, 2.3 and 28.8 µs for three clips; bundled with Unreal.
- Motion matching (Clavet GDC 2016; Büttner, I3D 2019 keynote, not GDC; Holden et al. TOG 2020 learned matching; abstracts verified, bodies not read): data heavy, strong for locomotion, harder to author and debug than state machines.
- Inertialisation (Bollo GDC 2018; unverified): transitions as a decaying offset from the previous pose, so only the target is evaluated; pairs well with state machines and cuts crowd cost.
- Morph targets as sparse GPU deltas; pose-space deformation (Lewis et al. 2000) for correctives. IK: two-bone analytic, FABRIK (Aristidou and Lasenby 2011), full-body solvers. Dual quaternion skinning (Kavan et al. I3D 2007).

## Guidance

- **Assets**: `Skeleton`, `AnimationClip` (ACL compressed; vendored as an algorithm library within the vendor policy, or an in-house equivalent if ACL's build does not fit), `MorphTargetSet` (sparse deltas), `BlendGraph`, `MotionDatabase`. Morph and skeleton data in the asset format from the first version because DCC import feeds them.
- **Evaluation**: a pose buffer per instance; graph nodes are pure functions over pose buffers (clip sample, blend, additive, inertialise, IK, morph weights); the graph compiles to a flat node program (shared graph compiler with S47 later). Evaluation runs as parallel tasks per instance on the fiber scheduler, batched per archetype.
- **Transitions**: inertialisation by default; cross-fade only where authored.
- **Motion matching**: an optional node over the same pose buffer with a feature database built at import; evaluate after the baseline pipeline exists.
- **Skinning**: a compute pre-skin pass writing skinned vertices into the GPU geometry tables (S15) so the visibility buffer and shadows see one geometry path; dual quaternion as a per-asset option; morph targets applied in the same pass.
- **LOD**: update rate by distance and screen size, bone culling, far instances share poses; essential at MMO crowd density.
- **Ragdoll and cloth**: skeleton drives Jolt ragdolls (S34) and cloth colliders (S35) after evaluation.
- **Root motion**: extracted from clips and reconciled with server-authoritative movement (S56) through the character controller.
- **DCC**: glTF 2.0 brings skins, morphs and animations; retargeting maps rest poses between skeletons (S49).

## Done when

- A character blends locomotion with inertialised transitions, two-bone IK on feet and a morph-driven face; a crowd of 1,000 instances animates within the stated budget with LOD.
- Clips imported from Blender and Maya play identically; a retargeted clip runs on a second skeleton.
- Skinned geometry renders through the visibility buffer and casts shadows.

## Open decisions

- ACL vendored or in-house compression.
- Motion matching in the first version or after.
