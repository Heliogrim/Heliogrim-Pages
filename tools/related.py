"""List the pages related to a docs page: links out, links in, shared work/question ids, keyword hits.

Usage: python tools/related.py docs/architecture/engine-loop-exploration.md [keyword ...]
Agents run this before editing a page so cross-referenced discussions are not missed.
"""
import re
import sys
from collections import Counter
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
LINK = re.compile(r"\]\(([^)#\s]+\.md)")
IDS = re.compile(r"\b[WQ]\d+\.\d+\b")


def rel(p):
    return p.relative_to(DOCS).as_posix()


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    target = Path(argv[1]).resolve()
    keywords = [k.lower() for k in argv[2:]]
    pages = {p.resolve(): p.read_text(encoding="utf-8") for p in DOCS.rglob("*.md")}
    if target not in pages:
        sys.exit(f"not a docs page: {argv[1]}")

    def links(p):
        return {(p.parent / m).resolve() for m in LINK.findall(pages[p])} & pages.keys()

    out = links(target)
    inbound = {p for p in pages if p != target and target in links(p)}
    ids = set(IDS.findall(pages[target]))
    shared = Counter()
    for p, text in pages.items():
        if p != target:
            n = len(ids & set(IDS.findall(text)))
            if n:
                shared[p] = n
    hits = Counter()
    for p, text in pages.items():
        if p != target and keywords:
            low = text.lower()
            n = sum(low.count(k) for k in keywords)
            if n:
                hits[p] = n

    print(f"# {rel(target)}")
    print(f"\n## Links out ({len(out)})")
    for p in sorted(out):
        print(" ", rel(p))
    print(f"\n## Linked from ({len(inbound)})")
    for p in sorted(inbound):
        print(" ", rel(p))
    print(f"\n## Shares work/question ids ({len(ids)} ids on this page), top 15")
    for p, n in shared.most_common(15):
        print(f"  {n:3}  {rel(p)}")
    if keywords:
        print(f"\n## Keyword hits for {keywords}, top 15")
        for p, n in hits.most_common(15):
            print(f"  {n:3}  {rel(p)}")


if __name__ == "__main__":
    main(sys.argv)
