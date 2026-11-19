#!/usr/bin/env python3
"""Generate docs/plan/progress.md: systems by milestone with chunk progress.

Usage: python -I tools/gen_progress.py [output]

Reads the systems catalog (docs/plan/systems.md), short names from the roadmap diagram
and every chunk heading `### W<sys>.<n> <title> · <kind> · <status>` on docs/plan/work/*.md.
The status grammar is in docs/guides/work-and-release.md; unknown statuses print a warning.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

PLAN = Path("docs/plan")
SYSTEM = re.compile(r"^\| (S\d\d) \| ([^|]+)\| (M\d)[^|]*\|", re.M)
SHORT = re.compile(r'(S\d\d)\["S\d\d ([^"]+)"\]')
CHUNK = re.compile(r"^### (W(\d\d)\.\d+) (.+?) · ([^·]+?) · (.+)$", re.M)
TRACK = re.compile(r"^## Track ([A-F]): (.+)$", re.M)
MILESTONES = {"M1": "Trustworthy core", "M2": "Render and world core", "M3": "A beautiful world",
              "M4": "Living world and tools", "M5": "Connected", "M6": "Single shard"}

# First match wins; order matters ("code done ... open" is review, not done).
STATES = [
    ("deferred", re.compile(r"^deferred")),
    ("review", re.compile(r"in review|^code done.*\bopen\b")),
    ("active", re.compile(r"^(in progress|continuous|page seeded)")),
    ("done", re.compile(r"^(done|code done|desk study done)")),
    ("ready", re.compile(r"^ready")),
    ("blocked", re.compile(r"^(after|needs|parallel)")),
]
LABEL = {"done": "done", "review": "in flight", "active": "in flight", "ready": "ready", "blocked": "blocked", "deferred": "deferred"}


def dot(st, wid=""):
    # One CSS dot per chunk (heliogrim.css .hg-chunk): unicode glyphs differ in size per font.
    cls = "flight" if st in ("review", "active") else st
    title = f"{wid} {LABEL[st]}".strip()
    return f'<span class="hg-chunk {cls}" title="{title}"></span>'


def state(status):
    s = status.lower()
    for name, rx in STATES:
        if rx.search(s):
            return name
    print(f"warning: unknown chunk status: {status}", file=sys.stderr)
    return "blocked"


def landing(status):
    """Where an execute chunk's code is: master, the feat/wip integration branch, or nowhere yet."""
    if "master" in status:
        return "master"
    if "feat/wip" in status:
        return "wip"
    return ""


def phase(kind):
    return "execute" if "execute" in kind else "design" if "design" in kind or "plan" in kind else "explore"


def load():
    text = (PLAN / "systems.md").read_text(encoding="utf8")
    short = dict(SHORT.findall((PLAN / "roadmap.md").read_text(encoding="utf8")))
    tracks, systems = {}, {}
    for block in re.split(r"(?=^## )", text, flags=re.M):
        t = TRACK.match(block)
        for sid, desc, ms in SYSTEM.findall(block):
            name = short.get(sid) or re.split(r"[:,(]", desc)[0].strip()
            systems[sid] = dict(name=name, ms=ms, track=t.group(1) if t else "?", chunks=[])
        if t:
            tracks[t.group(1)] = t.group(2)
    for page in sorted((PLAN / "work").glob("*.md")):
        for wid, sys_no, title, kind, status in CHUNK.findall(page.read_text(encoding="utf8")):
            sid = "S" + sys_no
            if sid not in systems:
                print(f"warning: {wid} on {page.name} has no system {sid}", file=sys.stderr)
                continue
            systems[sid]["chunks"].append(dict(id=wid, page=page.name, kind=phase(kind.strip()),
                                               state=state(status.strip()), land=landing(status), status=status))
    # "after W.." whose chunks are all done is ready, even if its heading was not updated yet.
    done = {c["id"] for s in systems.values() for c in s["chunks"] if c["state"] == "done"}
    for c in (c for s in systems.values() for c in s["chunks"]):
        deps = re.findall(r"W\d\d\.\d+", c["status"])
        if c["state"] == "blocked" and c["status"].startswith("after") and "Q" not in c["status"] and deps and set(deps) <= done:
            c["state"] = "ready"
    return tracks, systems


def bar(done, total, width=10):
    n = round(width * done / total) if total else 0
    return "▰" * n + "▱" * (width - n)


def cell(chunks, kind):
    c = [x for x in chunks if x["kind"] == kind]
    if not c:
        return "–"
    return "".join(dot(x["state"], x["id"]) for x in c)


def now(chunks):
    for states in (("review", "active"), ("ready",)):
        hit = [x for x in chunks if x["state"] in states]
        if hit:
            label = "in flight" if "review" in states else "ready"
            ids = ", ".join(f"[{x['id']}](work/{x['page']})" for x in hit[:3]) + (" …" if len(hit) > 3 else "")
            return f"{label}: {ids}"
    if chunks and all(x["state"] in ("done", "deferred") for x in chunks):
        return "complete"
    return "blocked" if chunks else "no chunks"


def render(tracks, systems):
    out = [
        "# Progress Board",
        "",
        '**Status**: <span class="hg-status summary">generated</span> from the [systems catalog](systems.md), '
        "the [roadmap](roadmap.md) and the chunk headings on the [work pages](work/index.md). "
        "Do not edit by hand; run `python -I tools/gen_progress.py` (CI runs it before every build). "
        "A chunk counts as its heading says, except that an `after` chunk whose listed chunks are all done counts as ready.",
        "",
        f"Legend per chunk, in page order (hover a dot for its id): {dot('done')} done · {dot('active')} in progress or in review · "
        f"{dot('ready')} ready · {dot('blocked')} blocked (after or needs) · {dot('deferred')} deferred. "
        "**Landed** counts execute chunks whose code is on `master` and, separately, only on the `feat/wip` integration branch.",
        "",
        "## Milestones",
        "",
        "| Milestone | Systems | Chunks done | | In flight | Ready | Landed on `master` / `feat/wip` |",
        "|---|---|---|---|---|---|---|",
    ]
    by_ms = defaultdict(list)
    for sid, s in sorted(systems.items()):
        by_ms[s["ms"]].append((sid, s))
    for ms, rows in sorted(by_ms.items()):
        ch = [c for _, s in rows for c in s["chunks"]]
        done = sum(c["state"] == "done" for c in ch)
        out.append(
            f"| [{ms} {MILESTONES.get(ms, '')}](#{ms.lower()}) | {len(rows)} | {done} / {len(ch)} | `{bar(done, len(ch))}` "
            f"| {sum(c['state'] in ('review', 'active') for c in ch)} | {sum(c['state'] == 'ready' for c in ch)} "
            f"| {sum(c['land'] == 'master' and c['kind'] == 'execute' and c['state'] == 'done' for c in ch)} / "
            f"{sum(c['land'] == 'wip' and c['kind'] == 'execute' and c['state'] == 'done' for c in ch)} |")
    for ms, rows in sorted(by_ms.items()):
        out += ["", f"## {ms}", "", f"{MILESTONES.get(ms, '')}. Done when: see the [roadmap](roadmap.md#{ms.lower()}-{MILESTONES.get(ms, '').lower().replace(' ', '-')}).", "",
                "| System | Track | Done | | Explore | Design | Execute | Landed | Now |",
                "|---|---|---|---|---|---|---|---|---|"]
        for sid, s in rows:
            ch = s["chunks"]
            done = sum(c["state"] == "done" for c in ch)
            ex = [c for c in ch if c["kind"] == "execute" and c["state"] == "done"]
            landed = " / ".join(str(sum(c["land"] == k for c in ex)) for k in ("master", "wip")) if ex else "–"
            out.append(f"| {sid} {s['name']} | {s['track']} | {done} / {len(ch)} | `{bar(done, len(ch), 6)}` "
                       f"| {cell(ch, 'explore')} | {cell(ch, 'design')} | {cell(ch, 'execute')} | {landed} | {now(ch)} |")
    out += ["", "Tracks: " + " · ".join(f"**{k}** {v.lower()}" for k, v in sorted(tracks.items())) + ".", ""]
    return "\n".join(out)


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else PLAN / "progress.md")
    tracks, systems = load()
    out.write_text(render(tracks, systems), encoding="utf8", newline="\n")
    print(f"wrote {out}: {len(systems)} systems, {sum(len(s['chunks']) for s in systems.values())} chunks")


if __name__ == "__main__":
    main()
