# Serialisation, Reflection and VCS-Friendly Formats

**Systems**: S01, S09, S41 · **Track** A, C · **Milestone** M1 to M2
**Status**: <span class="hg-status summary">plan</span>. Research from [tooling](../sources/research-tooling.md) section 7 (Git LFS spec verified) and the [serializer evolution exploration](../../architecture/serialization-evolution-exploration.md).

## Target

- Every serialised record carries a schema version per type; unknown fields survive a load-edit-save round trip; corrupted records are detected per record and reported with their path.
- Editable assets have a canonical text form that diffs and merges in Git; payloads are content-addressed blobs compatible with Git LFS pointers.
- One reflection model with type identity stable across module reloads, fields with attributes, functions, enums; it feeds serialisation, hot reload, visual scripting, property panels and asset search.

## Current state (checked 2026-11-07)

- `Engine.Serialization` (81 files): structured (`access::Structure<T>`) and layout (`access::Layout<T>`) serialisers, `X.Structured.cpp` and `X.Layout.{hpp,cpp}` split per `STYLE.md`; generated serialisation for archetypes (PR #81) keyed by slot path with a layout hash. No per-type schema version; package and archive version slots unused; unknown slot types cannot be skipped; 9-byte headers per key.
- `Engine.Reflect` (27 files): `TypedMetaClass`, `InheritMeta`, reflection utils; transitive inheritance queries were suspect in the test notes; no function or attribute reflection; type identity is address based.
- Packages: fixed header offsets, index table with archive GUIDs, URL schemes; per-package checksums only.
- Component serialisation issues #3 to #9 are open; archetype generated serialisation covers their data.

## Research summary

- Git LFS pointer (verified): a text file with `version`, `oid sha256:<hex>`, `size`; objects stored by SHA-256 in a sharded path; clean and smudge filters; `.gitattributes` selects files. A content-addressed asset store can emit these pointers for free.
- The exploration's findings: size-skipping for forward compatibility, versioned upcasters for backward compatibility, a text manifest plus content-addressed blobs for Git, round-trip preservation of unknown records, per-record checksums; `textconv` helps diff only, not merge.
- Hot reload (tooling report, Live++ verified): structural changes are not migrated by the patcher; the engine must serialise, destroy and recreate; reflection and serialisation are the migration format.

## Guidance

### S01 Serialisation schema versioning

- Add `SchemaVersion` to `access::Structure<T>` and `access::Layout<T>`; records write `{ type id, version, length, checksum }` headers so a reader can skip and preserve unknown records as opaque bytes and re-emit them on save.
- Upcasters: a per-type table `version N -> N+1` run at load; lazily where the record is large (geometry), eagerly elsewhere. Downgrade is unsupported by design.
- Dense encoding from the exploration: MessagePack-style fixed forms, interned keys per archive, native-layout payloads for `Layout` records. Measure size and speed against the current 9-byte-per-key form before adopting.
- Canonical text form: a deterministic key order, stable float formatting, one record per line block; the editor saves text for assets under version control and binary in packages.
- Tests: version N fixtures stored in the repository; loading each fixture under N+1 is a test per type.

### S09 Reflection v2

- Type identity becomes a content hash of the type's name and layout, not an address; stable across DLL reloads and across processes (replication needs it too).
- Add fields with attributes (editor display, replication policy, serialisation policy), functions with signatures (visual scripting and the test driver call them), enum metadata.
- Keep the no-macro, no-self-registration rule from #80: registration happens from explicit module init functions that a plugin or game module exports.
- Fix the transitive inheritance query and cover it with a test.

### S41 Content-addressed packages and VCS-friendly formats

- Blobs keyed by SHA-256 (or BLAKE3, measured) in `Engine.Crypto`; a package index maps asset GUID to blob hashes; a manifest is the canonical text form.
- LFS-compatible pointers for blobs under version control; the editor's VCS provider (S51) uses them.
- Cooked packages are not in Git; the build (S53) produces them from the manifest and the blob store.

## Done when

- A record written at version N loads at N+1 with unknown fields preserved through a save; a flipped byte is reported with its record path.
- A reflection query for a type gives the same identity in two processes and after a module reload in a test.
- An asset saved as text diffs line by line in Git; its blob is an LFS pointer.

## Open decisions

- Manifest syntax (project text key-value, JSON, YAML).
- Lazy versus eager upcasting default.
- Hash function (SHA-256 for compatibility with LFS, BLAKE3 for speed; LFS requires SHA-256 for its pointer).
