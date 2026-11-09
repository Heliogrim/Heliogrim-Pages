# Work: DCC Live Link, Plugins, VCS

**Systems** S49, S50, S51 · **Issues** [#129](https://github.com/Heliogrim/Heliogrim-Engine/issues/129), [#130](https://github.com/Heliogrim/Heliogrim-Engine/issues/130), [#131](https://github.com/Heliogrim/Heliogrim-Engine/issues/131) · **Track** D · **Milestone** M3 to M4
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [DCC, plugins, VCS](../topics/dcc-plugins-vcs.md).

## Cross-reference

| Existing input | What it already settles | Still open or in tension |
|---|---|---|
| `Editor.GFX.Loader` (assimp), `AutoImportAction`, issue #146 (archive kind problem in the import action) | Import exists with a known defect | The translator pipeline replaces the action's internals; #146 is folded into W49.1 |
| [Serialisation work](serialization-and-reflection.md) S41 | Text manifest, LFS pointers, blob store | VCS diff and lock targets |
| [Reflection work](serialization-and-reflection.md) S09 | Module-init registration | Plugins register through it |
| [Editor workflows work](editor-workflows.md) S46 | File watcher shared | `Engine.Filesystem.Watcher` owned there, consumed here |
| [Animation work](animation.md) | Asset formats for skeleton and morphs | glTF translator fills them |
| [Build work](build-and-deploy.md) S53 | Engine SDK | Same-toolchain plugins link against it |
| [Hot reload work](visual-scripting-hmr.md) | Module boundary | Editor plugins may hot reload later (Godot's `reloadable` flag as precedent) |

## Architecture

- **Bundles**: new `Editor.Import` (`Translator`, `Pipeline`, `Factory`, sidecar settings, reimport), `Editor.Import.Gltf`, `Editor.Import.Fbx` (ufbx), `Editor.Livelink` (socket service, Blender add-on in `tools/blender`), new `Engine.Plugin` (descriptor, discovery, phases, C-ABI table) and `Editor.Plugin` (editor registration), new `Editor.VCS` (`VcsProvider`, Git and LFS implementation, status in the asset browser).
- **Provides**: deterministic, GUID-preserving import; live transforms and animation; plugin loading; VCS status, lock, diff, submit.
- **Consumes**: Background fibers (S02), diagnostics (S05), watcher (S46), residency for hot swap (S03), physics shapes (S34), SDK (S53), manifest and LFS pointers (S41), canvas and uikit for panels (S42, S43).

## Code design

| Type | Contract |
|---|---|
| `Translator` | Format to `NeutralScene` (nodes, meshes, skins, morphs, animations, materials, cameras); glTF 2.0 first, FBX via ufbx, OBJ; USD later. |
| `ImportPipeline` | Ordered, user-extensible steps over `NeutralScene` with `ImportSettings` sidecar (text, S41); diagnostics per step. |
| `AssetFactory` | Produces engine assets with stable GUIDs; reimport replaces content and keeps GUID, sidecar settings and user overrides; dependent-asset diagnostics on skeleton or morph changes. |
| `ReimportPolicy` | Watcher events debounced with stable-size checks; GPU resources and Jolt shapes hot-swap through residency and the physics scene system. |
| `LivelinkService` | Local socket; messages for transforms, camera, animation; applied as non-undoable preview state; Blender add-on first. |
| `PluginDescriptor` | Text (S41 format): name, version, modules `{ type Runtime, Editor, Developer; phase }`, dependencies, content flag; discovery in engine, project and user folders. |
| `PluginLoader` | Phases aligned with boot (before modules, after core, after editor UI); same-toolchain tier links against the SDK; binary tier crosses `PluginAbiTable { magic, size, version, fn pointers }` and never passes `Rc` or `Arci`. Version mismatch is a diagnostic. |
| `SamplePlugin` | One panel and one importer; a CI target. |
| `VcsProvider` | `status`, `lock`, `unlock`, `revert`, `diff`, `submit`; `GitLfsProvider` first using the LFS locking API; binary merge refused with a diagnostic naming both versions. |

Placement: `Editor.Import/{Translator,ImportPipeline,AssetFactory,ReimportPolicy}`, `Editor.Import.Gltf/`, `Editor.Import.Fbx/`, `Editor.Livelink/`, `tools/blender/heliogrim_livelink/`, `Engine.Plugin/{PluginDescriptor,PluginLoader,PluginAbiTable}`, `Editor.VCS/{VcsProvider,GitLfsProvider}`. Tests: Blender save refresh within the stated time; sample plugin load and version rejection; LFS lock on edit; text diff opens.

## Work chunks

### W49.1 Import pipeline design · design · after W05.1, W36.1 (asset formats; can run with a draft)

- **Goal**: translator, pipeline, factory, sidecars, reimport policy, watcher use, hot swap, closing #146; assimp format audit (keep, drop) and the editor-only rule for format libraries; the runtime representation per asset type agreed with W53.1 (Q49.1).
- **Output**: `architecture/import-pipeline-design.md`; plan.
- **Questions**: Q49.1.

### W49.2 Implement glTF translator, pipeline, factory, reimport · execute · after W49.1, W46.2 (watcher)

- **Done when**: saving a glTF refreshes mesh, skeleton and animation with GUIDs kept; #146 closed.

### W49.3 FBX through ufbx and OBJ · execute · after W49.2

### W49.4 Blender live link · execute · after W49.2

- **Done when**: a live-linked camera moves the viewport; transforms stream for look development.

### W50.1 Plugin system design · design · after W09.1, W53.1

- **Goal**: plugin package shape (source plus assets, built locally against the installed engine, user-editable), discovery and load in editor and game, dependency and version rules; the layering keeps room for a C-ABI tier without building it (Q50.1).
- **Output**: `architecture/plugin-system-design.md`; plan.
- **Questions**: Q50.1 (decided).

### W50.2 Implement descriptor, discovery, phases, same-toolchain tier, sample plugin · execute · after W50.1, W53.2

- **Done when**: the sample plugin loads in editor and game and is rejected on version mismatch with a diagnostic.

### W50.3 Binary C-ABI tier · execute · after W50.2, only if Q50.1 says first release

### W51.1 VCS integration design · design · after W41.1

- **Output**: `architecture/vcs-integration-design.md`; plan.
- **Questions**: Q51.1 (decided: not now).

### W51.2 Implement Git and LFS provider, status, lock, diff · execute · after W51.1, W41.2, W43.3 (asset browser)

- **Done when**: the asset browser shows Git status; editing a binary asset takes an LFS lock; a text asset diff opens.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q49.1 | FBX through `ufbx` only; no Autodesk SDK. glTF stays the primary interchange format. The vendored assimp has its own FBX reader under BSD-3, so licensing is not the problem; its FBX coverage (animation, newer binary versions) and speed are. W49.1 states whether assimp stays for any format once the own glTF translator and `ufbx` cover the importer's use, or is dropped. |
| Q49.1 (addendum) | Format libraries (assimp, `ufbx`, image and audio decoders) are editor-only dependencies; the runtime never links them. W49.1 audits which of assimp's formats the project needs and which can go. Distribution builds cook every source asset into one unified runtime representation per asset type and use case (the `CookStep` of [build and deploy](build-and-deploy.md), content-addressed through S41); W49.1 and W53.1 state the runtime format per asset type together so import and cook agree. |
| Q51.1 | Perforce is not mandatory right away; the provider API leaves room for a Perforce provider later. |
| Q50.1 | Same-toolchain plugins only; no binary C-ABI table is built, the layering merely leaves room for one. The owner's model: plugins reach the user through a store or shop inside the editor as source packages (code plus assets) that are compiled locally against the installed engine, and the user is free to edit the pulled code. W50.1 designs the package shape and local build; the store flow is a later editor chunk. |

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q49.1 | FBX: ufbx only, or also the Autodesk SDK (licence) for compatibility? | W49.1 | ufbx only |
| Q50.1 | Binary C-ABI plugin tier in the first release, or same-toolchain only? | W50.1 | Same-toolchain only; the ABI table is designed, not built |
| Q51.1 | Perforce provider planned at all? | W51.1 | Not planned; provider API leaves room |
