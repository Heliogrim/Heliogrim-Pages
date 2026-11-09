# Work: Serialisation, Reflection, VCS-Friendly Formats

**Systems** S01, S09, S41 · **Issues** [#83](https://github.com/Heliogrim/Heliogrim-Engine/issues/83), [#91](https://github.com/Heliogrim/Heliogrim-Engine/issues/91), [#121](https://github.com/Heliogrim/Heliogrim-Engine/issues/121); absorbed #3 to #9 · **Track** A, C · **Milestone** M1 to M2
**Status**: <span class="hg-status summary">plan</span>. Work breakdown for [Serialisation, reflection and VCS-friendly formats](../topics/serialization-and-reflection.md).

## Cross-reference

| Existing page | What it already settles | Still open or in tension |
|---|---|---|
| [Serialization evolution exploration](../../architecture/serialization-evolution-exploration.md) | Current encoding (1-byte tag + 8-byte size, constant-size tags unskippable, string keys, `@` symbols); package header and footer; rules to add (round trip, per-record checksum, every tag skippable, schema version per type, header version separate from schema version); MessagePack-style dense ideas; VCS strategy (manifest + LFS blobs, cooked out of Git) | Text form syntax; lazy vs eager upcast; GUID assignment on duplicate import; migration of existing `.pkg`; URL resolution order |
| [Actor archetypes design](../../architecture/actor-archetypes-design.md) | Generated serialisation keyed by slot path with a layout hash; no-macro, no-self-registration reflection rule | Layout hash becomes one input of the schema version; reflection v2 must keep the explicit module-init rule |
| [Actor system exploration](../../architecture/actor-system.md) | Causality and serialisation sections | Nothing blocking |
| [Scripting native codegen exploration](../../architecture/scripting-native-codegen-exploration.md) | Needs a reflection backend; C++26 reflection unavailable | S09 is that backend; no language reflection |
| [Storage exploration](../../architecture/storage-exploration.md) | Package index use | S41 content addressing changes the index to hash keys |

## Architecture

- **Bundles**: `Engine.Serialization` (+`.Structures`, `.Layouts`) extended in place: `SchemaVersion`, record headers, skip and preserve, upcaster tables, text writer and reader. `Engine.Reflect` extended: hashed type identity, attributes, functions, enums. `Engine.Crypto` gains SHA-256 (and BLAKE3 if measured). New `Engine.Resource.Package.Content` (content-addressed blob store, manifest).
- **Layer**: L2 services. Remove `Engine.Serialization` including `Heliogrim` (layer violation on the modules page).
- **Provides**: versioned records, skippable unknown records, per-record checksums, canonical text form, upcasters; stable `TypeId`, field attributes, function reflection; blob store and manifest with LFS pointers.
- **Consumes**: `Diagnostic` (S05) for corruption and version reports; hash function (`Engine.Crypto`).

## Code design

| Type | Contract |
|---|---|
| `SchemaVersion` | `u16` per type, declared next to `access::Structure<T>` and `access::Layout<T>` as a static member; generated archetype serialisation derives it from the layout hash plus an explicit bump counter. |
| `RecordHeader` | `{ type id: u64 hash, version: u16, length: u32 or varint, checksum: u32 }` on top-level records only (asset, actor). Every record is skippable by `length`; constant-size leaf tags remain inside records, never at record level. Nested reflected types carry a `u16` version in their struct slot; value structs carry nothing (decision Q01.1). |
| `OpaqueRecord` | Bytes of a record the reader could not interpret, kept on the native object's side table and re-emitted on save (round-trip rule). |
| `Upcaster<T>` | Table of `(from, to, fn(RecordView) -> Result<RecordView, Diagnostic>)` chained to the current version at load; eager by default, lazy for types flagged `LargeRecord`. No downgrade. |
| `TextWriter` / `TextReader` | Canonical YAML subset emitted and parsed through the vendored `ryml` (decision Q01.3): block style only, sorted keys, scalars typed by the schema and never guessed, numbers formatted by the engine with `std::to_chars` and passed as plain scalars, binary as base64 or a blob hash, `@` symbols as `@name`, unknown keys kept as opaque subtrees for round trip; byte-identical on re-save. W01.4 first verifies that the `ryml` emitter is deterministic under these rules; if not, fall back to an own grammar. |
| `DenseEncoding` | Behind a format flag; MessagePack-style fix forms, interned keys per archive, native-layout `Layout` payloads; adopted only after W01.3 measures size and speed. |
| `TypeId` | Content hash of the fully qualified name plus the field layout; equal across processes and DLL reloads; `TypedMetaClass` keeps its address for fast paths but identity compares by hash. |
| `FieldMeta` | `{ name, type id, offset, attributes: span<Attribute> }`; `Attribute` is a small tagged value (editor display, replication policy, serialisation policy). |
| `FunctionMeta` | `{ name, signature type ids, invoker: fn(void* self, span<Arg>) -> Result<Value, Diagnostic> }` for visual scripting (S47) and the test driver (S54). |
| `EnumMeta` | Names and values with attributes. |
| `BlobStore` | `put(bytes) -> Hash`, `get(Hash)`, sharded path; `Manifest` maps asset GUID to blob hashes and record metadata in the canonical text form; `LfsPointer` emission for blobs under version control. |

Placement: `Engine.Serialization/Schema/{SchemaVersion,RecordHeader,Upcaster}.hpp`, `Engine.Serialization/Text/{Writer,Reader}.{hpp,cpp}`, `Engine.Reflect/{TypeId,FieldMeta,FunctionMeta,EnumMeta}.hpp`, `Engine.Resource.Package.Content/{BlobStore,Manifest,LfsPointer}`. Fixtures: `Engine.Serialization.Test/fixtures/v<N>/` one file per serialised type.

## Work chunks

### W01.1 Schema versioning and record format design · design · ready

- **Goal**: record header, skip and preserve, checksums, upcaster table, where a type's version lives, relation to package header version, migration of existing packages.
- **Inputs**: exploration sections 1a, 2, 3; `Engine.Serialization/Structure`, `Processor.cpp` CRC code, archetype generated serialisation (PR #81).
- **Output**: `architecture/serialization-design.md`; plan with the fixture scheme.
- **Questions**: Q01.1, Q01.2.

### W01.2 Implement versioned records, skip, checksums, upcasters, fixtures · execute · after W01.1

- **Done when**: version-N record loads at N+1 with unknown fields preserved byte for byte; a flipped byte is reported with its record path; version-N fixtures exist for every serialised type.

### W01.3 Dense encoding benchmark · explore · after W01.2

- **Goal**: measure MessagePack-style fix forms, key interning and native-layout payloads against the 9-byte-per-key form on real packages.
- **Output**: results section in the exploration; adopt or close.

### W01.4 Canonical text form · design+plan · after W01.1

- **Goal**: syntax, float formatting, symbol writing, text for VCS assets and binary for packages, editor save path.
- **Output**: section in `serialization-design.md`; plan.
- **Questions**: Q01.3.

### W01.5 Implement text form · execute · after W01.4, W01.2

- **Done when**: an asset saved twice is byte-identical and diffs line by line in Git.

### W09.1 Reflection v2 design · design · ready

- **Goal**: hashed `TypeId`, field attributes, functions, enums, module-init registration, fix and test the transitive `inherits` query. Function reflection covers non-overloaded functions only (Q09.1); the design states how console commands with varying parameter sets are expressed.
- **Inputs**: `Engine.Reflect` (`TypedMetaClass`, `InheritMeta`), #80 registration rule, scripting native codegen exploration (reflection backend needs), replication needs (S56).
- **Output**: `architecture/reflection-design.md`; plan.
- **Questions**: Q09.1, Q09.2.

### W09.2 Implement reflection v2 · execute · after W09.1

- **Done when**: a type's identity is equal in two processes and after a DLL reload in a test; property panel reads attributes; `inherits` transitivity test passes.

### W41.1 Content-addressed packages and manifest design · design · after W01.4, W03.5 (chunk size)

- **Goal**: blob store, manifest, LFS pointers, cooked packages out of Git, hash choice, migration path.
- **Output**: `architecture/content-packages-design.md`; plan.
- **Questions**: Q41.1, Q41.2.

### W41.2 Implement blob store, manifest, LFS pointers · execute · after W41.1, W01.5

- **Done when**: an asset's blob is an LFS pointer in a test repository; a package is rebuilt from manifest plus blob store.

## Decisions (2026-11-08)

| ID | Decision |
|---|---|
| Q01.2 | Upcasters per type by choice; record bytes by default, native structs where a type opts in. |
| Q01.3 | Canonical YAML subset through the vendored `ryml`, schema-typed scalars, deterministic emitter rules (see code design). Own grammar only if the emitter cannot be made deterministic. |
| Q09.2 | Closed attribute set first, safe and strict in-engine types. Plugin compatibility is kept in mind for later, not built now. |
| Q01.1 | Required for evolution: type identity plus schema version, as Kubernetes' `apiVersion` and `kind` do. Top-level records (asset, actor) carry both: binary `u64` type hash plus `u16` version, text `schema: hg/Actor@3`. Nested reflected types (components, material layers) carry only a `u16` version inside their struct slot, the type being implied by the parent's field schema; plain value structs (vectors, colours, transforms) carry nothing. Length and checksum are separate concerns and exist only on top-level records: length for skipping unknown records and round-trip preservation, checksum for corruption reports with a record path. No per-package type table. Cost: about 16 bytes per top-level record, 2 bytes per nested reflected instance. |
| Q09.1 | No overload or template reflection. Visual scripting nodes are an instruction set, each node binds one reflected function. Native C++ in the same binary uses overloads as a language feature and does not need reflection for it. Console commands with varying parameter sets are reflected as one function with defaulted or `span<Value>` arguments, or as separately named commands; the reflection table never resolves overloads. |

Batch 1 closed for this page. [ADR placeholders](../../adr/README.md): record schema versioning, text form.

## Questions for the owner

| ID | Question | Blocks | Suggested default |
|---|---|---|---|
| Q01.1 | Where does a type's schema version live: in every record header, or once per type in the package meta section with records carrying only the type id? | W01.1 | Per record header (self-describing records survive copy-paste between packages) |
| Q01.2 | Upcasters operate on record bytes, on native structs, or per type by choice? | W01.1 | Per type by choice, default record bytes |
| Q01.3 | Text form syntax: the project's own key-value syntax, JSON or YAML? | W01.4 | Project key-value with a strict grammar (deterministic, comments allowed) |
| Q09.1 | Does function reflection need to cover overloads and templates in v2, or free functions and non-overloaded members only? | W09.1 | Non-overloaded members and free functions |
| Q09.2 | Attributes as a closed enum set or an open string-keyed map? | W09.1 | Closed set with an extension slot for plugins |
| Q41.1 | Hash: SHA-256 only (LFS compatible) or BLAKE3 internally with SHA-256 for pointers? | W41.1 | SHA-256 only until a measurement shows hashing on the critical path |
| Q41.2 | GUID assignment on duplicate import of the same source: new GUID, same GUID with a diagnostic, or user choice? | W41.1 | Same GUID keyed by source path hash, diagnostic on collision |
