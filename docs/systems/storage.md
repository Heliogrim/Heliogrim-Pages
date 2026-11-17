# Storage

**Status**: <span class="hg-status accepted">implemented</span> for synchronous reads and writes, and since PR [#180](https://github.com/Heliogrim/Heliogrim-Engine/pull/180) (merged into `feat/wip` 2026-11-16, `f9ee8b8f`) for async reads and writes on an IOCP thread. The sections below were verified at `273094ef` and still describe the sync path; the async path is summarised under Limits and in [storage design](../architecture/storage-design.md) 2.11.
**Verified against**: engine commit [`273094ef`](https://github.com/Heliogrim/Heliogrim-Engine/tree/273094efc25f0c71471360f2170e6ad19275c032), the head of `feat/wip`, 2026-11-16. Not on `master` yet.
**Modules** (see the [module map](../architecture/modules.md)): `Engine.Storage` (module), `Engine.Storage.Registry` (URLs, storages, repositories, providers), `Engine.Storage.System` (`StorageSystem`, request and query API), `Engine.Storage.Action` (actions, guards, stack cache), `Engine.Storage.Boot` (the resolvers that open blobs, packages and archives), `Engine.Storage.Package` (package read, write and commit), with `Engine.Resource.Blob`, `Engine.Resource.Package` and `Engine.Resource.Archive` as the data types.
**Related**: [storage design](../architecture/storage-design.md) (sections 1.9 and 2.11 are the as-built notes), [storage exploration](../architecture/storage-exploration.md), [storage work page](../plan/work/storage-streaming.md), PRs [#169](https://github.com/Heliogrim/Heliogrim-Engine/pull/169) (stack cache, merged) and [#180](https://github.com/Heliogrim/Heliogrim-Engine/pull/180) (async IOCP path, merged), issues [#24](https://github.com/Heliogrim/Heliogrim-Engine/issues/24) and [#166](https://github.com/Heliogrim/Heliogrim-Engine/issues/166).

## Purpose

Every byte the engine reads from or writes to a file, a memory block, a package or an archive goes through one system. A caller names a location as a URL, gets an `IStorage` object for it, and then runs a callback against the typed resource behind it: a `Blob`, a `ReadonlyPackage`, a `StorageReadonlyArchive` and so on. The system opens what is needed underneath (file, then package, then archive), keeps the parts that are safe to share in a cache, and orders readers against writers per underlying file or memory block.

What it does not do at this commit: asynchronous I/O (every read blocks the calling worker), byte caching, budgets, file watching, or streaming. `queryAsync` and `mutateAsync` abort when called. See [Limits](#limits-and-known-issues).

## Where it sits

```hg-diagram
flowchart LR
    BOOT["Editor.Boot<br/>initStorage: repositories per config path"]
    ASSET["Asset indexing<br/>(Editor.Boot/AssetInit)"]
    LOAD["Resource loaders<br/>(SourceLoader, transformers)"]
    SHADER["read_shader_file<br/>(Render.Subpass)"]
    LEVEL["Level load / save<br/>(Editor.Scene.Actions)"]
    SYS["StorageSystem<br/>request*, query, mutate"]
    REG["StorageRegistry<br/>URL to IStorage"]
    RES["StorageActionResolver<br/>type chain to action factory"]
    CACHE[("StackCache<br/>resolved stages + per-primary locks")]
    DATA["Blob / Package / Archive<br/>(Engine.Resource.*)"]
    BOOT --> REG
    ASSET --> SYS
    LOAD --> SYS
    SHADER --> SYS
    LEVEL --> SYS
    SYS --> REG
    SYS --> RES
    SYS --> CACHE
    CACHE --> DATA
```

`StorageModule` ([`Engine.Storage/StorageModule.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage/StorageModule.cpp)) owns the registry, the resolver and the system. `setup` registers the memory and package providers and installs the resolvers. File repositories are not part of `setup`: the editor adds them in `editor::boot::initStorage` ([`Editor.Boot/Boot/StorageInit.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Editor.Boot/Boot/StorageInit.cpp)) from the config paths. `GameEngine` constructs the module but never calls `setup`, so the game runtime has no working storage today.

## Vocabulary

| Type | What it is |
|------|------------|
| `IStorage` | One addressable unit: a file, a memory block, a package or an archive. Primary storages (`LocalFileStorage`, `MemoryStorage`) hold bytes; secondary storages (`PackageStorage`, `ArchiveStorage`, both `ISecondaryStorage`) name a backing storage through `getBacking()`. |
| `StorageUrl` | A variant of `FileUrl` (scheme + normalised path), `ArchiveUrl` (archive guid), `PackageUrl` (guid), `MemoryUrl` (guid) and `RfclUrl` (scheme + free text). |
| `IStorageRepository` | Owns the storages of one or more URL schemes and creates them from a `StorageDescriptor`. |
| `IStorageProvider` | Owns repositories of one kind (local files, memory, packages). The registry owns the providers. |
| `StorageRegistry` | Maps a URL to its `IStorage` by asking the repositories registered for the URL's scheme. |
| `StorageActionResolver` | Maps a chain of storage types and a target resource type to a factory that builds a `Query` or `Mutation`. |
| `Query`, `Mutation` | One action over one chain: `prepare` (walk the backing storages), `acquire` (open the stages), `exec` (run the callback), `release`, `cleanup`. |
| `IoQueryGuard`, `IoMutationGuard` | What `query` and `mutate` call through: they wrap the callback and hand the action to `ExtendedStorageSystem::execQuery` / `execMutation`. |
| `ResolvedStage` | One opened stage of a chain (open blob, parsed package, archive view), `Arci`-counted, pointing at the stage below it. |
| `StackCache` | Resolved stages keyed by `(storage, accessor type)`, plus one `FiberSharedMutex` per primary storage. |

## URLs and schemes

The schemes are string constants in [`Url/Scheme.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.Registry/Url/Scheme.hpp). Which repository answers them:

| Scheme | URL type | Repository | Registered by |
|--------|----------|------------|---------------|
| `file+project` | `FileUrl` | `ProjectFileSystemRepository` (also answers `file`) | editor `initStorage`, base = project base path |
| `file+editor` | `FileUrl` | `EditorReadOnlyRepository` (also answers `file`) | editor `initStorage`, base = editor path |
| `file+cache` | `FileUrl` | `CacheFileSystemRepository` (only `file+cache`) | editor `initStorage`, twice: project and editor cache path |
| `file+runtime` | `FileUrl` | `RuntimeFileSystemRepository` (also answers `file`) | `initRuntimeStorage`, not called by the editor boot |
| `mem` | `MemoryUrl` | `MemoryRepository` | `StorageRegistry::setup` |
| `package` | `PackageUrl` | `PackageSystemRepository` | `StorageRegistry::setup` |
| `archive` | `ArchiveUrl` | `ArchiveSystemRepository` | `StorageRegistry::setup` |

A file URL carries an absolute path. The repositories key their storages by that path; the "base path" they are created with is not used to resolve relative paths (only the project repository looks at it, see below). `FileUrl::encode()` prints `<scheme>://<path>`, `ArchiveUrl::encode()` prints `archive://<guid>`.

Lookups walk the repositories in registration order. The editor registers, in this order: memory, archive, package (from `setup`), then project cache, project, editor cache, editor. The first repository that lists the scheme and returns a storage wins.

## How it works

### 1. Get a storage

`StorageSystem` hands out storages through `requestStorage`, `requestPackage` and `requestArchive` ([`StorageSystem.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.System/StorageSystem.cpp)):

- `requestStorage({ .fileUrl = url })` returns the known `LocalFileStorage` for the URL, or inserts a new one through the registry. Creating the storage opens nothing.
- `requestPackage({ .storage = fileOrMemoryStorage })` returns the package that already refers to that blob storage. Otherwise it queries the blob: an empty blob becomes a new package with a random guid; a non-empty blob must be a package (`assertrt(package::isPackageBlob(blob_))`), and the package guid plus one `ArchiveStorage` per linked archive are registered from its header and linker.
- `requestPackage({ .fileUrl = url })` does the same from a file URL but never reads the file: a file without a known package gets a new package storage with a random guid.
- `requestArchive(archiveUrl, { .package = ... })` returns or registers the archive in that package.

`findPackage`, `findArchive`, `hasStorage`, `enumArchivesFromPackage` and the two `removeStorage` overloads for file and memory URLs complete the set that is implemented.

### 2. Run a query or a mutation

```cpp
auto query(_In_ mref<Arci<IStorage>> storage_, auto&& fn_) const noexcept -> Result<
	std::invoke_result_t<decltype(fn_), ref<const resource::Blob>>, query_blob_error
> {
	query_blob_guard guard = fetchQuery(::hg::move(storage_));
	return std::invoke(guard, std::forward<decltype(fn_)>(fn_));
}
```

There are three `query` and three `mutate` overloads, one per storage kind. The callback parameter decides what you get:

| Call | Storage | Callback receives |
|------|---------|-------------------|
| `query` | `Arci<IStorage>` (file or memory) | `ref<const resource::Blob>` |
| `query` | `Arci<PackageStorage>` | `ref<const resource::ReadonlyPackage>` |
| `query` | `Arci<ArchiveStorage>` | `ref<resource::StorageReadonlyArchive>` (not `const`: it has a read cursor) |
| `mutate` | `Arci<IStorage>` (memory only) | `ref<resource::Blob>` |
| `mutate` | `Arci<PackageStorage>` | `ref<resource::ReadWritePackage>` |
| `mutate` | `Arci<ArchiveStorage>` | `ref<resource::Archive>` |

The result is `Result<R, error>` where `R` is whatever the callback returns. The error is a variant of `std::invalid_argument`, `std::out_of_range`, `std::runtime_error`, `AccessError`, `IllegalArgumentError` and `IllegalTypeError`.

### 3. Resolve the chain type

`fetchQuery` builds an `ActionTypeInfo`: the target resource type and the storage type of each stage, from the requested storage down its `getBacking()` chain. An archive in a package in a file gives `(ArchiveStorage, PackageStorage, LocalFileStorage)`.

`StorageActionResolver::resolveQuery` looks that signature up in `ActionTypeResolutionCache`. `initActionResolver` ([`Engine.Storage.Boot/Action/ActionResolverInit.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.Boot/Action/ActionResolverInit.cpp)) registers every chain the engine uses as a static action (`QueryStaticGen<Stages...>`, `MutationStaticGen<Stages...>`):

| Target | Chain (top to bottom) | Resolvers |
|--------|-----------------------|-----------|
| blob | file | `LfsBlob` |
| blob | memory | `MemBlob` |
| package | package, file / package, memory | `BlobPack` over `LfsBlob` / `MemBlob` |
| archive | archive, package, file / archive, package, memory | `PackArchive` over `BlobPack` over the blob |
| archive (query) | archive, memory | `BlobArchive` over `MemBlob` |

A signature with no registered chain falls back to `buildQuery` / `buildMutation`, which composes a dynamic action (`QueryDynamicGen`, `MutationDynamicGen`) from registered stage factories. No production path relies on that today. If neither works, `fetchQuery` fails `assertrt(factory.has_value())`: an unsupported chain crashes, it does not return an error.

### 4. Lock, acquire, run, release

`execQuery` ([`Details/ExtendedStorageSystem.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.System/Details/ExtendedStorageSystem.cpp)) runs the whole action under the shared lock of the chain's primary storage:

```cpp
const auto stackLock = concurrent::SharedLock { context.stacks.lockOf(query_.primary()) };
if (query_.primary()->isRetired()) {
	return Unexpected { IoQueryGuard<void>::error_type { retiredError() } };
}

auto acqResult = query_.acquire(context);
if (not acqResult.has_value()) {
	return Unexpected { IoQueryGuard<void>::error_type { ::hg::move(acqResult).error() } };
}
const auto release = ReleaseOnExit { .action = query_, .context = context };

auto execResult = query_.exec(::hg::move(queryFn_));
```

`execMutation` takes the same lock exclusively and declares an `InvalidateOnExit` guard after it. Whatever happens in acquire, exec or the commit, the primary's cached chains are dropped before the lock opens.

```hg-diagram
sequenceDiagram
    participant C as Caller
    participant S as StorageSystem
    participant R as StorageActionResolver
    participant X as ExtendedStorageSystem
    participant K as StackCache
    participant B as Resolvers (Boot)
    C->>S: query(archiveStorage, fn)
    S->>R: resolveQuery(ActionTypeInfo)
    R-->>S: factory (QueryStaticGen)
    S->>S: prepare: walk getBacking() to the primary
    S->>X: execQuery(query, fn)
    X->>K: lockOf(primary), shared lock
    X->>K: find stage keys, top down
    loop each missing stage, bottom up
        X->>B: acqFn(ctx, storage, below.access)
        B-->>X: accessor
        X->>K: insert (shared stages only)
    end
    X->>C: fn(resource)
    X->>X: release: drop the chain top
    X->>K: unlock
```

### 5. The stack cache

`acquire` in `QueryStaticGen` ([`Action/QueryStaticGen.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.Action/Action/QueryStaticGen.hpp)) scans the chain from the top for the highest cached stage. Everything below a hit is reused. The stages above it are built bottom-up, each from the accessor of the stage below, and each new stage is inserted unless it is per query:

```cpp
node->primary = below_ != nullptr ? below_->primary : stage.storage.get();
node->shared = not CursorResource<stage_resource_type<Idx_>> && (below_ == nullptr || below_->shared);
node->below = ::hg::move(below_);

// Note: First insert wins; a concurrent reader may have resolved the same stage.
below_ = node->shared ? ctx_.stacks.insert(::hg::move(node)) : ::hg::move(node);
```

Rules that follow from the code ([`Store/StackCache.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.Action/Store/StackCache.cpp), [`Store/ResolvedStage.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.Action/Store/ResolvedStage.hpp)):

- **Key** = `StageKey { const IStorage* storage; type_id resource; }`. On the static path `resource` is the id of `Rc<IoResourceAccessor<T>>`, so `T` and `const T` never share a node. The dynamic path keys by the resource's own type id, so static and dynamic chains never share nodes either.
- **Shared**: blob and package stages. **Per query**: an archive stage (any resource with `seek`/`tell`, see `CursorResource`) and anything above it. Concurrent readers of one archive each get their own cursor over the shared package.
- **First insert wins.** Two fibers that miss the same key both build it; the second `insert` returns the first node and its own is dropped.
- **Bound**: `max_entries = 512`. At the bound, `insert` evicts the least recently used entry that nobody else holds (`ref_count() == 1`). Held entries are never evicted, so the map can exceed 512 while guards hold chains.
- **Invalidation**: `invalidateFrom(primary)` drops every entry whose chain bottoms out at `primary`. A guard that still holds a dropped chain keeps it alive through `Arci`.
- **Locks**: `lockOf(primary)` creates one `FiberSharedMutex` per primary on first use and never frees it.
- Mutation stages are never cached. Mutation resolvers still use `Context::objectStore` and `Context::accessStore`, which assert if one storage is acquired twice at once; the exclusive lock prevents that for one primary.

So, for `archive A` in a package in a file: the first query opens the file (one `LfsSyncBlob`), parses the package (header, linker, footer) and builds the archive view, and caches the first two. A second query of `A`, or any query of archive `B` in the same package, builds only the archive view. A package mutation then drops both cached stages, and the next query reopens the file.

`StackCacheIntegration.RepeatedQueryResolvesOnce` pins this: the second query makes zero insert attempts and the cache holds two entries.

### 6. Removal

`removeStorage(FileUrl)` and `removeStorage(MemoryUrl)` take the primary's exclusive lock (running actions drain), re-check that the URL still names the same storage, unregister it, mark it retired and invalidate its chains. A query or mutation that holds the old `Arci` and locks afterwards gets `AccessError { "Storage was removed from the storage system." }`. Removal asserts that no package or archive refers to the storage (`assertrt(collector.empty())`): removing a file that backs a registered package crashes.

### 7. Blobs and packages underneath

- `LfsSyncBlob` ([`Engine.Resource.Blob/File/LfsSyncBlob.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Resource.Blob/File/LfsSyncBlob.cpp)) wraps one `std::fstream`. `read`, `write`, `trim` and `size` each take a `FiberMutex`, clear the stream state, and seek. It opens read-write, falls back to read-only (then `write` and `trim` assert), and **creates the file and its parent directories if the path does not exist**.
- `ByteSpanBlob` serves memory storages. Its `size()` is the touched byte count, not the capacity.
- `BlobPack` parses a `ReadonlyPackage` from the blob below it (`reconstruct_readonly_package`), or makes an empty one if the blob is empty. The mutation side builds a `ReadWritePackage`; its release stage commits staged linker changes with `package::commit_package_changes`.
- `PackArchive` builds a `StorageReadonlyArchive` at `sizeof(PackageHeader) + linked.data.offset` with the linked size and type. An archive guid the package does not link fails the query with `AccessError { "Requested archive does not exist within package." }`.

## Reading files: walkthroughs

### Read a whole file

`readTextViaStorage` ([`Engine.Storage.System/ReadText.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Storage.System/ReadText.cpp)) is the shortest complete example:

```cpp
// Note: Only absolute paths to regular files resolve in storage repositories.
if (not native.is_absolute() || not std::filesystem::is_regular_file(native)) {
	return None;
}

auto url = FileUrl { scheme_, fs::Path { absolutePath_ } };
auto requested = system_.requestStorage({ .fileUrl = ::hg::move(url) });
// Note: An unknown scheme yields a null storage instead of an error.
if (not requested.has_value() || requested.value() == nullptr) {
	return None;
}

auto store = ::hg::move(requested).value().into<IStorage>();
const auto queried = system_.query(
	::hg::move(store),
	[&text](_In_ ref<const resource::Blob> blob_) {
		auto bytes = String(static_cast<size_t>(blob_.size()), '\0');
		const auto got = blob_.read(0, std::span { reinterpret_cast<ptr<_::byte>>(bytes.data()), bytes.size() });
		bytes.resize(got.size());
		text = Some(::hg::move(bytes));
	}
);
```

(Abridged: the real function also returns early on a negative size.) The three checks are each there for a reason: the existence check stops `LfsSyncBlob` from creating an empty file; the absolute check is needed because repositories do not resolve relative paths; the null check covers a scheme that no repository answers.

### Read archives in a package

The editor's asset indexing ([`Editor.Boot/Boot/AssetInit.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Editor.Boot/Boot/AssetInit.cpp)) shows the package path: `requestStorage` for a `file+project` URL, a blob `query` with `package::isPackageBlob`, `requestPackage({ .storage = ... })`, then on a scheduler task `enumArchivesFromPackage` and one archive `query` each:

```cpp
storeSys->query(::hg::move(archive), [&storageUrl](_In_ ref<resource::StorageReadonlyArchive> archive_) {
	if (archive_.type() != resource::ArchiveType::eSerializedStructure) {
		return;
	}
	auto structured = serialization::StructuredArchive { archive_ };
	// ...
});
```

### Write an archive into a package

`addArchiveToPackage(package, archive)` mutates the package: it adds a linker entry with a random `ArchiveGuid` and stages an `ArchiveDeltaAdd`; the package stage's release commits it, and the new `ArchiveStorage` is registered. To replace content, mutate the package and stage an `ArchiveDeltaReplace` on the linked entry, as `StackCacheIntegration::rewriteArchive` does.

### How resources load

Graphics loaders get their bytes through `SourceLoader` ([`Engine.Resource/Loader/SourceLoader/SourceLoader.cpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Resource/Loader/SourceLoader/SourceLoader.cpp)). For texture, static geometry and font assets it takes the asset's first `file` source URL, checks the file exists, and returns a pair `(StorageSystem&, Arci<IStorage>)` from `registry->getStorageByUrl`. Transformers (`StaticGeometryTransformer`, the `Ktx`, `Png`, `Jpeg`, ... texture transformers) then call `src.first.query(src.second, ...)` and copy the blob into memory. A missing file gives a null storage and a logged error; the transformers still pass that null storage to `query`, which does not check for it.

### How shaders are read

Render passes load `.asl` files with `makeIrIntermediate` ([`Engine.Graphics.Render.Subpass/Impl/__tmp_helper.hpp`](https://github.com/Heliogrim/Heliogrim-Engine/blob/273094efc25f0c71471360f2170e6ad19275c032/src/Engine.Graphics.Render.Subpass/Impl/__tmp_helper.hpp); see [Accel compiler integration](accel/compiler.md#step-1-load-the-shader)). Its `read_shader_file` builds two candidates, `<project asset path>/shader/<name>` under `file+project` and `<editor asset path>/shader/<name>` under `file+editor`, and reads the first that `readTextViaStorage` returns:

```cpp
for (const auto& [scheme, base] : checks) {
	// Note: Includes are module-controlled input; never resolve outside the shader base.
	const auto candidate = (base / name_).lexically_normal();
	const auto relative = candidate.lexically_relative(base);
	if (name_.is_absolute() || relative.empty() || *relative.begin() == "..") {
		continue;
	}

	auto text = storage::readTextViaStorage(system, scheme, fs::Path { candidate });
	if (text.has_value()) {
		return ::hg::move(text).value();
	}
}

::hg::breakpoint();
return {};
```

`#include` names go through the same function, so an include cannot escape the shader roots. Every shader file therefore becomes a cached blob stage with an open handle. A shader found in neither root hits `breakpoint()` and returns an empty string, which `makeIrIntermediate` turns into a parse failure (`assert(parsed.has_value())`).

## Adding a storage kind

There is no plug-in point; a new kind touches every layer. In order:

1. **Storage class** in `Engine.Storage.Registry/Storage`: derive `InheritMeta<X, IStorage>` for a primary, or `InheritMeta<X, ISecondaryStorage>` with `getBacking()` for a layer over another storage.
2. **URL and scheme**: a scheme constant in `Url/Scheme.hpp`, a URL class, and the URL as a `StorageUrl` alternative; a descriptor in `Options/` and as a `StorageDescriptor` alternative.
3. **Repository and provider**: implement `IStorageRepository` (put the new scheme **first** in `getUrlScheme()`, see pitfalls) and register it with `addProvider` / `addRepository`.
4. **Resolvers** in `Engine.Storage.Boot/Action`: a query `acqFn` that returns its accessor through `acquireSharedReadonly` and keeps nothing in `Context`, and a mutation `acqFn`/`relFn` pair (the existing ones use `ExclusiveIoResource` plus `Context::objectStore`/`accessStore`). If the resource has a read cursor, give it `seek`/`tell` so the cache treats it as per query.
5. **Chains**: register every chain the kind appears in, in `initActionResolver`, with an `ActionTypeInfo` whose stages list storage, resource and input types top to bottom. Register queries with `QueryStaticGen` and mutations with `MutationStaticGen`.
6. **Entry point**: `fetchQuery(Arci<IStorage>)` only builds signatures for `MemoryStorage` and `LocalFileStorage` (`switchType`), and `fetchMutation(Arci<IStorage>)` assumes `MemoryStorage`. A new primary needs a case there; a new secondary needs its own `fetchQuery`/`fetchMutation` and `query`/`mutate` overloads in `StorageSystem`.
7. **Tests** in `Engine.Storage.Test`: copy `MutationIntegrationFixture` (it sets up a registry, a resolver and a system over a scratch directory) and add a type-resolution test next to `QueryTypeResolution.cpp`.

## Pitfalls

- **Never call storage from inside a storage callback on the same primary.** The callback runs under the primary's `FiberSharedMutex`. A nested query re-takes it on the same fiber and deadlocks once a writer waits; a mutation nested in a query deadlocks at once ([#166](https://github.com/Heliogrim/Heliogrim-Engine/issues/166), `shortcut:` in `execQuery`). Copy what you need out of the callback, return, then make the next call.
- **`queryAsync` and `mutateAsync` abort.** All six bodies are `::hg::todo_panic()`. Wrap a sync `query` in `hg::async` instead, as `AssetInit` does.
- **Querying a missing file creates it.** `LfsSyncBlob`'s constructor creates the file and its directories. Check existence first, like `readTextViaStorage` and `SourceLoader`.
- **Relative file URLs do not resolve.** Repositories key by the exact normalised path. Build absolute paths from the config (`eLocalAssetPath`, `eLocalBasePath`).
- **`hasStorage` and `insert` only see a repository's first scheme.** Both loops `break` after the first entry of `getUrlScheme()`. `hasStorage(FileUrl{ FileScheme, ... })` is always false, and `requestStorage` with a plain `file` URL returns a null storage unless a repository's `getStorageByUrl` creates it. `findStorageByUrl` and `getStorageByUrl` check every scheme.
- **One file, two storages.** A file requested as `file+project` and as `file+editor` becomes two `LocalFileStorage` objects in two repositories, so two cached chains and two open handles, and they do not order against each other.
- **Plain `file` URLs land in the project repository in the editor.** `ProjectFileSystemRepository::getStorageByUrl` creates a storage for any existing path in editor builds, through a `const_cast` the code itself flags as unsafe under concurrency. `registry->getStorageByUrl` panics when nothing matches.
- **The mutation callback's return value does not stop the commit.** Staged linker changes are committed whatever the callback returns (`MutationCallbackReturningFalseInvalidatesAndKeepsData`). Only stage changes you mean to keep.
- **Blob mutation is memory only.** `fetchMutation(Arci<IStorage>)` asserts `MemoryStorage` in debug and builds a memory signature regardless. Files are written through package mutations.
- **Unsupported chains crash.** `fetchQuery`/`fetchMutation` `assertrt` on a missing factory and on a failed `prepare`, although `query` is declared `noexcept` and returns a `Result`.
- **Cached files stay open.** A cached `LfsSyncBlob` keeps its `fstream` until eviction or invalidation. An external tool that saves the file by atomic replace can fail while the engine runs, and changes made outside the engine are only seen because each read seeks the live file (`RewrittenFileIsReadFresh`); a package parsed from it stays stale until a mutation or removal invalidates it.
- **Declared but not defined.** `addStorage`, `addPackage`, `removePackage`, `addArchive`, `removeArchive`, `removeStorage` for archive and package URLs, `replaceArchiveInPackage`, `removeArchiveFromPackage`, the memory `requestStorage` overloads, the located `requestPackage` overloads, all `requestArchive` overloads except `(ArchiveUrl, RequestArchivePackageUrlOptions)`, and `addArchiveToPackage(package, Arci<ArchiveStorage>)` have no body. Calling one is a link error.

## Debugging

The storage bundles log almost nothing; failures are asserts or `Result` errors.

| Symptom | Where to look |
|---------|---------------|
| `assertrt(factory.has_value())` in `fetchQuery` / `fetchMutation` | the chain is not registered in `initActionResolver`, or the storage's backing chain is not what you think (print `getBacking()` down to the primary) |
| `IllegalTypeError "Encountered primary storage while populating query stack."` | a dynamic action found a primary storage before the end of the expected chain |
| `AccessError "Storage was removed from the storage system."` | the storage was removed while you held its `Arci`; request it again |
| `AccessError "Requested archive does not exist within package."` | the `ArchiveStorage` names a guid the package linker does not have (stale registration, or the package file was replaced) |
| Assert in `ResourceAccessStore::add` | two mutation stages for one storage at once; mutations should only run under the primary's exclusive lock |
| Hang in a query or mutation | a nested storage call on the same primary (#166), or a removal waiting for a long-running callback |
| Shader load hits `breakpoint()` | the file is under neither `<project asset path>/shader` nor `<editor asset path>/shader`, or the name contains `..` or is absolute |
| `requestStorage` succeeds with a null storage | no repository answers the scheme, or the scheme is not the repository's first one |

To look into the cache from a test, `StackCacheIntegration.cpp` reads `StorageSystem::_context` through a derived struct and counts `StackCache::insertAttempts()`: a hit makes no insert attempts.

## Limits and known issues

- **Async path not re-verified here.** Since [PR #180](https://github.com/Heliogrim/Heliogrim-Engine/pull/180) (`f9ee8b8f`), `StorageModule` owns an `IoSystem` (`Engine.IO.Dispatcher`) on the IO thread: local-file stages use `IoFileBlob` (one fiber park per read or write) while it runs and `LfsSyncBlob` after `stopIo()`; large archive ranges stream through `WindowedBlob` (8 MiB); `queryAsync`/`mutateAsync` run the call as a scheduler task. A query racing `stopIo` can still cache an IO-backed stage whose reads come back empty (`shortcut:` in `StorageModule::stopIo`).
- **No game runtime storage.** `GameEngine` never calls `StorageModule::setup`.
- **Shader reads go through storage but are untested in the editor.** `ShaderReadTest` covers `readTextViaStorage`; the editor shader-load check for [#24](https://github.com/Heliogrim/Heliogrim-Engine/issues/24) was still open when #169 merged.
- **Count bound, not a budget.** 512 entries, LRU over unheld entries, `O(n)` scan on eviction (`shortcut:` in `StackCache::insert`).
- **Per-primary mutexes leak** (one per storage ever locked, `shortcut:` in `lockOf`).
- **Stacked removal is missing.** Removing a file or memory storage that backs a package asserts.
- **`StorageActionResolver::invalidateQuery` / `invalidateMutation`** are `todo_panic`. Nothing calls them; type chains do not change at runtime.
- **The archive-over-memory "mutation" chain is registered as a query.** `initActionResolver` registers `staticArchMem2ArchMut` with `QueryStaticGen`, so it lands in the query table with target `StorageReadWriteArchive`; `mutate(ArchiveStorage)` over a bare memory storage has no static chain.
- **No mutation compaction.** Each mutation commits its own staged deltas; there is no merge or ordering of concurrent intents beyond the exclusive lock.

## Changing it

- **Start at** `StorageSystem.hpp` for the API, `Details/ExtendedStorageSystem.cpp` for locking and invalidation, `Action/QueryStaticGen.hpp` and `Store/StackCache.cpp` for the cache, `Engine.Storage.Boot/Action/*` for what each stage opens.
- **Tests**: `Heliogrim-Engine.Storage.Test` (97 tests: `StackCacheTest` unit tests, `StackCacheIntegration` for prefix reuse, invalidation, removal races and concurrent readers, `ShaderReadTest`, `LfsSyncBlobTest`, `RegistryNegativePaths`, type resolution) and `Heliogrim-Engine.Storage.Package.Test`. Test files live under a per-process scratch root that is swept at start and exit.
- **Keep** invalidation inside the exclusive lock and after the commit; a query must never cache pre-commit bytes. Keep cursor resources out of the cache. Keep every new scope-guard declared after the lock it depends on, so it runs before the lock opens.
- **Concurrency changes** to `StackCache` or the per-primary locks follow the `verifying-concurrency` workflow in the engine repository.
