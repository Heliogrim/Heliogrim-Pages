# Brand Identity

**Status**: accepted by the owner on 2026-11-16 (editor UI brainstorm). This is the source of truth for the Heliogrim mark, palette, wordmarks and splash. It does not apply to the docs web site: the site was aligned on 2026-11-16 and reverted to its original [site design system](design-system.md) on 2026-11-17 (owner), which wins for the site (see [Site redesign brief](#site-redesign-brief)).

**Preview**: [identity-preview.html](../assets/brand/identity-preview.html) shows everything on this page in one place: splash, title bar, app icon, mark sizes, wordmarks, UI icon style and palette. The editor UI mockups behind it are listed in the [editor UI exploration](../architecture/editor-ui-exploration.md).

## Idea

Fire and ice over coal. The name splits into *Helio*, the sun, and *grim*, the dark; the mark is an eclipse. The Norse frame fits too: Muspelheim's fire and Niflheim's ice, the realm Hel rules. Coal is the ground, ember is the brand and the one action that matters, and frost is state: what is selected, focused or in progress. If everything glows, nothing does.

## Mark

The docs-site eclipse (a crescent in a ring), refined. It has no ticks at any size; with ticks it read as a clock.

| Part | Specification (64-unit master) |
|------|-------------------------------|
| Crescent | Ember disc, radius 0.68 × ring radius, linear gradient `#ff5a0f` (bottom left) to `#ff8a4a` (top right). The shadow disc sits at (+0.30 R, −0.25 R) from the centre, radius 0.80 R |
| Ring | Grey `#9a9aa2` hairline at 14 % opacity, radius `c − 1 − w/2`, width 1.25 px from 48 px up and 1 px below |
| Glint | Over the ring: frost, brightest at the top right (`#9fe0ff` at 88 %), falling to `#5cc8ff` at 22 % by 35 % of the ring and to nothing by 55 % |
| 16 px | Ring width 1.5 px, hairline at 20 %, glint 1.7 px |

Files: [`assets/brand/mark.svg`](../assets/brand/mark.svg) (master) and [`assets/brand/mark-16.svg`](../assets/brand/mark-16.svg) (small sizes). Each size is drawn on its own pixel grid, not scaled from the master; generate the sizes from the formula above.

Rejected on the way, so they are not proposed again: an H or rune letter mark (one variant read like Unreal Engine's), a wolf head, the wolf devouring the sun, a crystal shard, a gate, a full-strength frost ring ("too aggressive"), and tick variants.

## Wordmarks

| Variant | Setting | Use |
|---------|---------|-----|
| A | `HELIOGRIM`, light (300), caps, tracking 0.42 em, mark to the left | Splash, title bar, headers |
| D | `HELIOGRIM` at 500 weight, caps, tracking 0.24 em, stacked over `ENGINE · EDITOR` at 0.38 × size, tracking 0.5 em, in n9 | Documents, installer, About box |

The face is still open: IBM Plex Sans (matches the site) or Inter, compared later. The previews use the system font.

## Palette

### Coal neutrals

| n0 | n1 | n2 | n3 | n4 | n5 | n6 | n7 | n8 | n9 | n10 | n11 | n12 |
|----|----|----|----|----|----|----|----|----|----|-----|-----|-----|
| `#060607` | `#0b0b0d` | `#111113` | `#151518` | `#1b1b1f` | `#232328` | `#2e2e34` | `#3d3d44` | `#55555d` | `#75757e` | `#9a9aa2` | `#c4c4ca` | `#ececee` |

Bases n0 to n2, surfaces n3 to n5, borders n6 and n7, decoration and disabled n8, secondary text n9 and n10, primary text n11 and n12.

### Accents

| Ramp | 900 | 800 | 700 | 600 | 500 | 400 | 300 | 200 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|
| Ember | `#2a0e05` | `#4d1907` | `#7a2609` | `#b5390d` | `#ff6a1f` | `#ff8a4a` | `#ffab7a` | `#ffd3b8` |
| Frost | `#06202f` | `#0b3550` | `#115079` | `#1f7cb5` | `#5cc8ff` | `#86d7ff` | `#b3e7ff` | `#daf3ff` |

Ember 500 is within a hair of the site's `#ff6a1a`; the site value can move to `#ff6a1f` in the redesign.

### Semantic, axes, data

| Group | Values |
|-------|--------|
| Semantic | success `#3fbf7f`, warning `#f2c94c`, danger `#f0555a`, info `#5cc8ff` |
| Axes | X `#f0564f`, Y `#7cc24f`, Z `#4a8ff0` |
| Data (charts, profiler, audio bands, node pin types) | `#ff6a1f`, `#5cc8ff`, `#e2b84a`, `#3fbf7f`, `#a78bfa`, `#f472b6`, `#2dd4bf`, `#94a3b8` |

### Rules

- **Ember is rare**: the mark, one primary button per view, the active tab line, play. Never selection.
- **Frost is state**: selected rows, focus rings, progress, links, drop targets.
- **Warnings are yellow**, so they never read as ember. Errors and destructive actions are red. Status colour is always paired with a word or icon.
- **Contrast** (on n3): n12 text about 15:1, n10 about 7:1, ember 500 about 6:1. n8 is decoration only, never text.
- **Frost in the mark stays subtle**: a glint, never a full ring.

## Splash

Layout A, 16:9 application window, not a landing page:

- Left third: the lockup (mark plus wordmark A, `EDITOR` below), on calm coal.
- Right: art. In the preview, the large dial from [`assets/dial.svg`](../assets/dial.svg) as faint grey line work, an ember eclipse at its centre and the frost glint on its ring, over an ember glow from below and a frost haze from above.
- Footer: load status (`Compiling shaders · 112 / 340`), version and branch, scene and graphics API, and a thin progress bar in dimmed frost (`#5cc8ff` at 60 %).

The footer makes the splash useful on the test bench. The final art, the editor icon and the trailer are to be produced in Heliogrim and video tools; the preview fixes layout, rules and mood only.

## UI icons

16-px grid, 1.4 px stroke, round joins, `currentColor`. The preview's icons are placeholders. Pick a licensed set in this style (Lucide ISC, Tabler MIT or Phosphor MIT) before any icon ships.

## Site redesign brief

**Reverted on 2026-11-17 (owner)**: the site went back to its original [design system](design-system.md); the table below is kept as a record. What the docs site needed in order to follow this identity. Done on 2026-11-16; the owner kept the bone paper and flipped the roles on the site: frost is the rare accent, ember marks links and state (the editor keeps the rules above). The [site design system](design-system.md) has the resulting tokens.

| Area | Site (original, current again) | Target (done, then reverted) |
|------|-------------|---------------|
| Logo, favicon | All-ember crescent, ring and four ticks | Mark above: no ticks, grey hairline with frost glint (`mark.svg`, `mark-16.svg`) |
| Dark mode | Obsidian `#12100e`, warm surfaces `#1b1815`, rule `#2e2a25` | Kept warm (owner): the coal dark mode lost the site's feel, so the site keeps obsidian; coal is for the engine and editor |
| Accent | Ember `#ff6a1a` | Site flips the roles (owner): frost 500 is the rare accent, ember 500 to 700 marks links and state |
| Links, selection, focus | Ember-derived link colours | Ember for links and focus, frost for the accent (owner; the site's flip of the brand roles) |
| Light mode | Bone paper `#f4f1ea` | Keep the bone paper (owner); the masthead stays coal, so the mark needs no light fallback |
| Status chips | Amber, teal, green, grey, red | Map to the semantic set; keep the word in every chip |
| Masthead | `#14110f` | Kept `#14110f` with the warm neutrals |
| Type | Barlow Condensed, IBM Plex Sans and Mono | Header title set as wordmark A in IBM Plex Sans 300; the rest unchanged unless the editor font decision picks Inter |
| Landing illustration | `dial.svg` in ember and warm grey | Same dial, coloured as in the splash |

Constraints that stay: square corners and no shadows on the site (the editor uses rounded islands; the site does not have to), self-hosted assets, OFL fonts, no external requests.
