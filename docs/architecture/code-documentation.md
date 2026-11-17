# Code Documentation (Exploration)

**Status**: exploration. Nothing here is decided. Accepted parts move to an ADR in [`adr/`](../adr/README.md), processed in the engine project.

**Date**: 2026-11-05.

## Constraint

The engine source stays free of documentation-tool annotations. Doxygen, and other tools including tree-sitter based ones, were tried on this code base and produced nothing usable (owner's report; the attempts are not reproduced here). The code itself is the primary reference; the site adds orientation, not a mirror of every file.

## What is needed

1. **Orientation**: which modules exist, how they relate, where a system starts.
2. **Searchable**: a reader can find a type or a concept from the site search.
3. **Consumable**: a short page per system, not a generated page per symbol.

## Options

| # | Option | Annotations | Accuracy on this code | Status |
|---|--------|-------------|-----------------------|--------|
| A | [Module map](modules.md) generated from the CMake targets | none | exact, it reads the build's own declarations | **done** |
| B | Hand-written [system pages](../systems/index.md) with permalinks to the verified commit | none | as good as the author, and dated | started, three stubs |
| C | Compiler-accurate symbol index from `compile_commands.json` (for example `clang-doc` from LLVM, or a script on the clang AST) | none | **unverified**: it parses like the compiler, which the heuristic tools do not, but template-heavy code and MSVC-only constructs may still fail | spike needed |
| D | Rely on GitHub code navigation and search, link with permalinks | none | **unverified** for this code base | free to try |
| E | A self-hosted code search service | none | exact text search, no semantics | heavy, not proposed |

Options A and B cost nothing in the engine. C is the only route to a symbol-level reference.

## Proposed change

1. Keep A running: regenerate the module map in CI from a pinned engine commit (today it is run by hand with `tools/gen_modules.py`).
2. Write B for the systems readers ask about first, starting with the render graph.
3. Run a time-boxed spike on C against three modules of different style (for example `Engine.Common`, `Engine.ACS`, `Engine.Graphics.RenderGraph`). It passes only if the output names the right types, members and base classes for a fixed sample of symbols, with no change to the engine source. If it fails, the symbol level is dropped and the code stays the reference.

## Decisions needed

- Whether a symbol-level reference is wanted at all, or the module map plus system pages is enough.
- Where the pinned engine commit comes from for CI (a ref in this repository, or the engine's default branch).
- Whether publishing excerpts or generated output of the engine source is acceptable while the engine repository carries no `LICENSE` file.
