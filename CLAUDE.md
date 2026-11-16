# Heliogrim Pages: agent rules

MkDocs Material site. Conventions, layout and the build check are in `docs/guides/docs-workflow.md`; read it first.

## Find related pages before you write or answer

Topics cross over: an engine-loop or update-sync question touches the agent-sync exploration and the networking plan, the scene layer touches replication, and so on. A page's own text is never the whole picture.

Before editing a page, or answering a design question about one:

1. Run `python tools/related.py <page> [keywords ...]`. It lists links out, links in, pages sharing W/Q ids, and keyword hits.
2. Read every page in "Links out" and "Linked from" that is on the same topic, and the top pages by shared ids. At minimum read their Status line and the sections that mention the ids or keywords.
3. If you are a subagent given a list of "pages to read", treat it as a starting point, not the limit. Run step 1 anyway.
4. When your text contradicts or refines another page, link it and say which one wins, or flag the conflict to the owner. Never restate a topic as if no other page exists.
5. When you add a link to page B from page A, check whether B should link back.

## Before you finish

`uvx --with mkdocs-material==9.5.50 mkdocs build --strict` must pass.
