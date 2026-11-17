# Working on These Docs

## Preview locally

The site needs MkDocs and the Material theme at the version pinned in `requirements.txt`. With `uv`, nothing has to be installed globally:

```powershell
uvx --with mkdocs-material==9.5.50 mkdocs serve
```

The site opens at `http://127.0.0.1:8000` and reloads on save.

!!! warning "A bare `mkdocs` tool is not enough"
    `uv tool install mkdocs` installs MkDocs without Material, and the build stops with `Unrecognised theme name: 'material'`. Install the theme with it: `uv tool install mkdocs --with mkdocs-material==9.5.50`.

## Check before you push

```powershell
uvx --with mkdocs-material==9.5.50 mkdocs build --strict
```

CI runs the same command. `--strict` turns warnings, such as a broken link or an anchor that does not exist, into failures, so nothing broken is published.

## Where things go

| Content | Location |
|---------|----------|
| Explorations, designs, summaries | `docs/architecture/` |
| Raw research behind a page | `docs/architecture/sources/` |
| Accepted decisions | `docs/adr/` |
| How-to documents | `docs/guides/` |
| Contribution paths | `docs/contribute/` |

New pages must be added to `nav` in `mkdocs.yml`.

## Conventions

- Start each architecture page with a `**Status**:` line. Use `<span class="hg-status exploration">exploration</span>` chips only in index tables.
- Say what was checked against the source, and on which date.
- Commit messages follow `docs(scope): summary`, for example `docs(architecture): add storage exploration`.
- Specs for changes in flight belong in engine repository issues, not here.

## Publishing

Every push to `main` runs `.github/workflows/pages.yml`: build with `--strict`, upload, deploy to GitHub Pages. The repository's Pages source must be set to *GitHub Actions* (Settings, Pages).
