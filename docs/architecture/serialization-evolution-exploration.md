# Serializer Schema Evolution and VCS Integration (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md); the rest stays here or in issues.

**Origin**: distilled on 2026-11-04 from a Gemini conversation ([link](https://gemini.google.com/app/fe1b87947102a2ff)). The raw notes are not kept. The package layout PDF has not been shared. Section 1a rebuilds the layout from the source instead.

## 1. Current Format (as described by the owner)

- Key-value records. Each record carries a serializer type ID and a data size.
- Meta information uses `@`-prefixed symbols (type IDs, arch types, GUIDs).
- Packages have a fixed header with offsets and sizes for the compression appendix and the index table. The index table lists archive GUIDs with their size and offset.
- The index is read on boot. The engine discovers archives and builds a list of assets with their source locations.
- Packages may hold binaries (images, geometry, sound banks, bytecode) next to KV records.
- Packages carry CRC and SHA checksums, author, license, version and compression info.
- Project assets are split into single-reference assets (metadata package next to the file) and bundles (a package next to the directory or group).

## 1a. Current State in Engine (checked 2026-11-04)

Package container (`Engine.Resource.Package`, `Engine.Storage.Package`):

- `PackageHeader` (0x64 bytes, packed): magic bytes and magic version, endianness, `PackageVersion`, 16-byte GUID, compression, package and inflated size, then offset and size pairs for index, meta and compressed data.
- `PackageFooter` (0x18 bytes): an 8-byte CRC slot, reserved bytes, magic and endianness.
- Each index entry is a `PackageArchiveHeader` of 16 bytes: `ArchiveType` plus `ArchiveGuid`. The linker applies `ArchiveDeltaAdd` and `ArchiveDeltaReplace`.
- The CRC32 **is** written on store. `Processor.cpp` (around line 356) runs `Crc32` over the content in chunks before the footer. Open TODOs there: compression data is not recomputed, tail data is not restored, and the package size calculation is unverified when meta or compression is used. There is no SHA and no per-archive or per-record checksum.
- Versions: `PackageVersion` in the header and `ArchiveVersion` (a `u64` typedef) exist as slots but are not really used. **There is no schema versioning** for records or types, and no upcasters.

Record encoding (`Engine.Serialization/Structure`):

- Each slot is a 1-byte `StructureSlotType` followed by an 8-byte `s64` size, unless the type has a constant size (bool, integers, float, double). For those types the size is inferred from the type and not written.
- Skipping works for any known type tag. An **unknown type tag cannot be skipped**: if the type has an inferred size, the reader does not know how many bytes follow. Forward compatibility therefore holds for unknown keys, not for new slot types.
- Struct keys are full strings, each written as a string slot (1 + 8 header bytes plus the characters). `StructSlot::findRecord` finds a key by a linear scan that compares the strings.
- Meta keys live in `Engine.Serialization.Structures/Symbols.hpp`: `@type`, `@guid`, `@parent`, `@components`. Each `Symbol` holds a `type_id` hash and the string, but only the string is written. Used by `Level.Structured.cpp` and `Actor.Structured.cpp`.
- Not checked: whether a load and save cycle keeps keys that the native type does not know. Writing rebuilds the structure from the native object, so they are probably lost.

## 1b. Dense Encoding Ideas from MessagePack

[MessagePack](https://github.com/msgpack/msgpack/blob/master/spec.md) packs the type and small lengths or values into the first byte. Candidates to adopt, not decided:

- **Fix forms.** Positive fixint (0x00–0x7f) and negative fixint (0xe0–0xff) store small integers in a single byte. fixstr, fixarray and fixmap keep counts up to 31, 15 and 15 in the low bits. Most of our keys and small structs would drop from a 9-byte header to 1 byte.
- **Width-graded lengths.** `str8/16/32`, `bin8/16/32`, `array16/32` and `map16/32` replace our fixed 8-byte `s64` size with 1, 2 or 4 bytes. The rule: always use the smallest form.
- **Ext types.** `fixext 1/2/4/8/16` and `ext 8/16/32` carry a 1-byte type and raw bytes. This fits dense native payloads (vectors, matrices, GUIDs as fixext 16, packed arrays of PODs) written in native layout, and gives unknown types a length so they can be skipped.
- **Key interning.** Not from MessagePack. Write `Symbol::id` or a per-package string table index instead of the key string. This also turns `findRecord` into an integer compare.

Differences to keep in mind:

- MessagePack is big-endian. Our header records endianness, and "dense native format" means little-endian payloads. Adopt the tag scheme, not the byte order.
- Random access: MessagePack has no size for maps and arrays, only counts, so skipping one means walking it. Our slots carry byte sizes so a struct can be skipped in one seek. A hybrid keeps a byte size on containers and uses fix forms for leaves.

## 2. Evolution Rules Carried Forward

- **Size-skipping for forward compatibility.** An older reader that meets an unknown record skips it by its size.
- **Versioned upcasters for backward compatibility.** Chain `v1 -> v2 -> v3` to the current schema. Run them on record bytes or on native structs, decided per record type.
- **Never reuse a field ID or key.** Deprecate the old one and map it in an upcaster.
- **Each binary blob format has its own header version** at the start of its bytes.

## 3. Rules to Add (Not in the Source)

- **Preserve unknown records on round-trip.** If a tool loads a package, edits it and saves it, records the reader does not understand must be written back unchanged. Otherwise a newer field is silently dropped by an older editor. This matters for shared packages and store downloads.
- **Checksum per record**, not only per package. A skipped record must still be verifiable.
- **Every tag must be skippable.** Any type tag a reader may not know needs its length in the header (or a tag range defined as "length follows"). Today constant-size tags break this.
- **Schema version per type.** Neither records nor types carry a version today. Define where a type's schema version lives (per record, or once per type in the package's meta section) before writing upcasters.
- **Header version and record schema version are separate.** Define how a package-wide header bump relates to per-type schema versions before writing the upcaster registry.

## 4. VCS Strategy

- **Development:** a text manifest per package (canonical, sorted keys, fixed float formatting) plus content-addressed blobs. Commit the manifest to Git. Track blobs with Git LFS.
- **Cooked output** (the packed, compressed, checksummed `.pkg` files for shipping and the store) stays out of Git. It comes from the packer and is cached or fetched.
- **Binary diffs:** a `textconv` filter (dump tool) gives readable `git diff` output for binary packages. Merging binaries still needs manual resolution or a custom merge driver. Prefer the manifest route for anything that people edit by hand.

Corrections to the source:

- Content hashing deduplicates only byte-identical blobs. "Git LFS will never duplicate storage" overstates this. A changed blob is a new object.
- `textconv` is read-only. It does not help with merges.

## 5. Open Questions

- Canonical text form: key order, float round-trip precision, how `@`-symbols are written.
- Whether the manifest is JSON, YAML or the project's own text KV syntax.
- Migration path for existing `.pkg` files that have no manifest.
- Stable GUIDs when the same asset is imported twice. Who assigns them, and what happens on collision.
- Whether upcasters run lazily during the TOC walk or once at load.
- URL schemes (`file+project`, `file+editor`, `file+cache`) and `archive://<guid>`: resolution order, and what happens when an archive moves.

## 6. Related

- [Storage engine](storage-exploration.md): index table use, mutation compaction, fetch and mutate guards.
- [Observability](observability-exploration.md): stored capture format for trace diffing.
- [Actor system](actor-system.md): component layouts in `Engine.Serialization.Layouts`.
