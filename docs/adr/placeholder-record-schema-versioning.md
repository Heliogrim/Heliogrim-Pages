# Placeholder: Schema Versioning on Records

**Date**: pending (owner decision 2026-11-08, Q01.1 and Q01.2)
**Status**: placeholder, not yet processed in the engine project
**Source**: [Serialisation work page](../plan/work/serialization-and-reflection.md), [Serialization evolution exploration](../architecture/serialization-evolution-exploration.md)

## Context

The serialiser writes a type byte and a size per slot, with no type identity and no schema version. A record cannot be skipped when unknown, cannot be checked for corruption, and cannot be migrated when its type changes shape. The question was what the minimum per-record information is, and where it lives.

## Decision

Top-level records (one asset, one actor) carry a header: type id as a 64-bit hash, schema version as a 16-bit integer, length, checksum. In the text form the first two are one field, `schema: hg/Actor@3`, after the Kubernetes `apiVersion` and `kind` pattern. Nested reflected types (components, material layers) carry only a 16-bit version inside their slot; the type is implied by the parent's field schema. Plain value structs carry nothing. Upcasters run per type, on record bytes by default, on native structs where a type opts in.

## Alternatives Considered

### Version once per type in the package meta section

- **Pros**: saves two bytes per record.
- **Cons**: a record copied out of its package is no longer self-describing; an exported record must carry a slice of the table.
- **Why not**: the inline 16-bit version is simpler and costs little.

### Full header on every struct, nested included

- **Pros**: uniform.
- **Cons**: about 16 bytes per component, sampler or layer instance; the owner rejected this cost.

## Consequences

### Positive

- Records survive copy-paste between packages; unknown records are skipped and preserved byte for byte; a flipped byte is reported with its record path.

### Negative

- About 16 bytes per top-level record and 2 bytes per nested reflected instance; existing packages need a one-time migration.

### Risks

- The type hash must be stable across processes and DLL reloads; it depends on the reflection v2 `TypeId` (S09).
