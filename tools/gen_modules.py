#!/usr/bin/env python3
"""Generate docs/architecture/modules.md from the CMake targets.

Usage: python -I tools/gen_modules.py <engine checkout> [output]

Reads make_library_project / make_app_project / make_test_project blocks in src/*/CMakeLists.txt.
Nothing is annotated in the engine: groups come from LIB_FOLDER, edges from LIBRARIES.
shortcut: regex parse of the project macros, breaks if the macros change shape, then adapt BLOCK.
"""
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

BLOCK = re.compile(r"make_(library|app|test)_project\s*\((.*?)\n\s*\)", re.S)
NAME = re.compile(r"(?:LIB|APP|TEST)_NAME\s+(\S+)")
FOLDER = re.compile(r'(?:LIB|APP)_FOLDER\s+"(?:\$\{IDE_FOLDER\})?([^"]*)"')
DEP = re.compile(r"::([A-Za-z0-9_.]+)")


INC = re.compile(r'^\s*#\s*include\s*[<"]([A-Za-z0-9_.]+)/', re.M)


def includes(root: Path, name: str, known):
    """Modules whose headers this module includes, read from #include <Module/...> lines."""
    found = set()
    for f in (root / "src" / name).rglob("*"):
        if f.suffix in (".hpp", ".cpp", ".inl", ".h", ".c", ".ixx"):
            found |= set(INC.findall(f.read_text(encoding="utf8", errors="replace")))
    return sorted((found & known) - {name})


def parse(root: Path):
    mods = {}
    for cm in sorted((root / "src").glob("*/CMakeLists.txt")):
        for kind, body in BLOCK.findall(cm.read_text(encoding="utf8", errors="replace")):
            n = NAME.search(body)
            if not n:
                continue
            f = FOLDER.search(body)
            libs = body.split("LIBRARIES", 1)[1] if "LIBRARIES" in body else ""
            mods[n.group(1).strip("\"")] = dict(
                kind=kind,
                group=(f.group(1).strip("/") if f else "") or "Root",
                deps=sorted(set(DEP.findall(libs)) - {n.group(1).strip("\"")}),
            )
    known = set(mods)
    for k, v in mods.items():
        v["inc"] = includes(root, k, known) if (root / "src" / k).is_dir() else []
    return mods


def main():
    root = Path(sys.argv[1])
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/architecture/modules.md")
    mods = parse(root)
    sha = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%h %cs"], capture_output=True, text=True).stdout.strip()
    prod = {k: v for k, v in mods.items() if v["kind"] != "test"}
    tests = [k for k, v in mods.items() if v["kind"] == "test"]
    groups = defaultdict(list)
    for k, v in prod.items():
        groups[v["group"]].append(k)

    edges = defaultdict(int)
    for k, v in prod.items():
        for d in v["inc"]:
            if d in prod and prod[d]["group"] != v["group"]:
                edges[(v["group"], prod[d]["group"])] += 1
    label = lambda g: "No IDE folder" if g == "Root" else g
    slug = lambda g: re.sub(r"[^a-z0-9 -]", "", label(g).lower()).replace(" ", "-")
    short = lambda n: n.split(".", 1)[1] if "." in n else n
    # Union of what the source includes and what CMake declares; Engine.Common is everywhere, so it is left out.
    uses = lambda k: sorted((set(prod[k]["inc"]) | set(prod[k]["deps"])) - {"Engine.Common", k})
    chip = lambda g: f'<a href="#{slug(g)}">{label(g)}</a>'

    L = ["# Module Map", "",
         f'<span class="hg-status summary">generated</span> from the CMake targets and `#include` lines at commit `{sha}`. Do not edit by hand; run `python -I tools/gen_modules.py <engine checkout>`.', "",
         f"{len(prod)} modules in {len(groups)} groups, plus {len(tests)} test targets. A group is the IDE folder a module is filed under in CMake. Pick a group to see its modules and what each one uses.", "",
         '<div class="hg-modgrid">']
    for g in sorted(groups):
        ms = sorted(groups[g])
        gt = sorted({b for (a, b), n in edges.items() if a == g and b != "Root"}, key=lambda b: -edges[(g, b)])[:3]
        more = f'<i>+{len(ms) - 6} more</i>' if len(ms) > 6 else ""
        L.append(f'<a class="hg-mod" href="#{slug(g)}"><b>{label(g)}</b><em>{len(ms)}</em>'
                 f'<span>{" ".join(f"<code>{short(m)}</code>" for m in ms[:6])} {more}</span>'
                 f'<small>{"uses " + ", ".join(label(x) for x in gt) if gt else "no other group"}</small></a>')
    L += ["</div>", "",
          "A drawn layering diagram is not generated: a graph of every link was unreadable (tried 2026-11-05). It needs a curated diagram by someone who knows the intended layers.", "",
          "## Groups", ""]
    for g in sorted(groups):
        tgt = [b for (a, b), n in sorted(edges.items(), key=lambda x: -x[1]) if a == g]
        L += [f"### {label(g)}", "",
              f'<p class="hg-uses">Reaches into: {" ".join(chip(b) for b in tgt) if tgt else "no other group"}</p>', "",
              "| Module | Uses |", "|--------|------|"]
        for k in sorted(groups[g]):
            u = uses(k)
            L.append(f"| `{k}`{' (app)' if prod[k]['kind'] == 'app' else ''} | {', '.join('`' + short(x) + '`' for x in u) if u else '-'} |")
        L.append("")
    L += ["## Notes", "", "- *Uses* merges what the headers include with what CMake declares; the two disagree in places because CMake under-declares.",
          "- `Common` is used by nearly everything and is not repeated.", f"- Test targets: {', '.join('`' + t + '`' for t in sorted(tests))}.", ""]
    out.write_text("\n".join(L) + "\n", encoding="utf8", newline="\n")
    print(f"{len(prod)} modules, {len(groups)} groups, {len(edges)} edges -> {out}")


if __name__ == "__main__":
    main()
