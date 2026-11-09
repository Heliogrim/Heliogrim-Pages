# DCC Live Link, Plugins and VCS Integration

**Systems**: S49, S50, S51 · **Track** D · **Milestone** M3 to M4
**Status**: <span class="hg-status summary">plan</span>. Research from [simulation](../sources/research-simulation.md) section 4 (Unreal Interchange landing page verified) and [tooling](../sources/research-tooling.md) sections 5 and 7 (Unreal plugin descriptor and Git LFS specification verified).

## Target

- **DCC live link**: save in Blender, Maya or 3ds Max refreshes the asset in the engine within seconds with GUIDs and user overrides preserved; a live link streams transforms and animation for look development; an import pipeline modelled as translator, pipeline, factory.
- **Plugins**: a versioned plugin interface for engine and editor with descriptors, discovery, load phases and a C-ABI boundary for binary plugins; a sample plugin in the repository.
- **VCS**: status, diff, lock and commit from the editor through a provider API; Git with LFS first; VCS-friendly asset formats (S41).

## Current state (checked 2026-11-07)

- Import: assimp through `Editor.GFX.Loader` and `AutoImportAction`; GUIDs exist in the asset system; no watcher, no reimport policy, no glTF-specific path.
- No plugin system; no VCS integration.

## Research summary

- Unreal Interchange (landing verified): format-agnostic, asynchronous, customisable, runtime-usable; the translator, node graph, pipeline, factory structure is unverified detail.
- glTF 2.0 covers meshes, skins, morph targets, animations and PBR; FBX SDK licensing unverified, ufbx as an alternative; OpenUSD is heavy and scene-level. Blender's `save_post` handler can notify an external process; Maya and Max plugins can push over a local socket. File watching with debounce plus GUID-preserving reimport is the simplest robust mechanism (design inference).
- Unreal plugins (verified): JSON descriptor with modules of type Runtime, Developer, Editor and others, loading phases, dependencies pointing only to the same or higher level; Developer modules never load in shipping. A versioned C-ABI table with magic, size and version (as Crashpad's `CrashpadInfo`) is the stable boundary pattern.
- Git LFS (verified, including the locking API on 2026-11-07): canonical text pointers with SHA-256 OIDs; lock create, list and delete endpoints with force unlock. Unreal's source-control docs list Perforce and SVN providers; Git and Plastic are not on that page. Godot's GDExtension gained a `reloadable` flag for editor hot reload in the 4.2 development cycle.

## Guidance

### S49 DCC live link

- Import pipeline: `Translator` (format to a neutral scene graph: glTF 2.0 first, FBX through ufbx or the SDK as a compatibility path, OBJ, USD later), `Pipeline` (settings and user-extensible steps, stored as sidecar import settings), `Factory` (engine assets); asynchronous on Background fibers; diagnostics through S05.
- Reimport: GUID-preserving; sidecar settings and user overrides (material assignments, LOD settings) survive; a changed skeleton or morph set produces diagnostics for dependent assets.
- Watcher: `ReadDirectoryChangesW` behind `Engine.Filesystem` with debounce and stable-size checks (DCC tools write in several steps); shared with the asset search (S46).
- Live link: a small Blender add-on (Python) sending transforms, camera and animation over a local socket to an editor service; Maya and Max later through their SDKs; the editor applies them as non-undoable preview state.
- GPU resources and Jolt shapes hot-swap on reimport through the residency manager and the physics scene system.

### S50 Plugin system

- Descriptor (text, S41 format): name, version, modules with type (Runtime, Editor, Developer) and load phase, dependencies, content flag; discovery from engine, project and user plugin folders.
- Two tiers: same-toolchain plugins link C++ directly against the engine SDK (editor plugins, most engine extensions); binary plugins cross a versioned C-ABI table and never pass `Rc` or `Arci` handles across it.
- Load phases align with engine boot (before modules, after core, after editor UI); plugins register reflection (S09), actions (S45), panels (S43), importers (S49) and systems through explicit init functions. A sample plugin with one panel and one importer lives in the repository and is a CI target.

### S51 VCS integration

- `VcsProvider { status, checkout or lock, revert, diff, submit }` with Git plus LFS first (locking through the LFS API, to be read); status shown in the asset browser; locks on binary assets on edit.
- Diff of assets uses the canonical text form (S41); merge of binary payloads is refused with a diagnostic naming both versions.
- Partial and sparse checkout are documented for large projects, not built into the editor.

## Done when

- Saving a Blender file refreshes the mesh, skeleton and animation in the editor within the stated time with GUIDs kept; a live-linked camera moves the viewport.
- The sample plugin loads in the editor and the game, adds a panel and an importer, and is rejected with a diagnostic when its version is incompatible.
- The asset browser shows Git status; editing a binary asset takes an LFS lock; a text asset diff opens from the editor.

## Open decisions

- FBX through the SDK (licence) or ufbx only.
- Binary plugin tier in the first version or same-toolchain only.
- Perforce provider later or never.
