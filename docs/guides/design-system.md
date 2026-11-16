# Site Design System

How the docs site applies the [brand identity](brand-identity.md). The brand page wins on the mark, palette and colour rules; this page records only how the site implements them. Source of truth for the implementation: `docs/stylesheets/heliogrim.css`, `docs/javascripts/diagrams.js`, `overrides/main.html`, `docs/assets/`. Change those and this page together.

## Idea

The site reads like an engineering drawing set: bone-coloured paper in light mode, coal in dark mode, hairline rules, square corners. **Ember** is rare, as in the brand: the masthead rule, section markers, the active tab, primary buttons, index numbers. **Frost** is state: links, hover and focus, pressed toggles. Aligned with the brand on 2026-11-16 (owner choices: frost links, bone paper kept).

## Mark

The brand [mark](brand-identity.md#mark): `assets/brand/mark.svg` in the header, `assets/brand/mark-16.svg` as favicon. The masthead is coal in both modes, so the mark always sits on dark. `assets/dial.svg` is the landing illustration, coloured as the splash art: grey line work, ember eclipse, frost glint on the outer ring. Do not recolour, outline, or add effects.

## Colour

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| Paper `--md-default-bg-color` | `#f4f1ea` | n2 `#111113` | Page |
| Surface `--hg-surface` | `#ebe6db` | n4 `#1b1b1f` | Table heads, code, callouts, hover |
| Ink `--md-default-fg-color` | `#1b1917` | n12 `#ececee` | Text |
| Ink light | `#5f594f` | n10 `#9a9aa2` | Secondary text |
| Ink lighter | `#8a8378` | n9 `#75757e` | Muted text, closed and planned chips |
| Rule `--hg-rule` | `#d6d0c4` | n6 `#2e2e34` | Hairlines |
| Ember `--hg-ember` | `#ff6a1f` | `#ff6a1f` | Ember 500: accent fills and rules |
| Link `--md-typeset-a-color` | frost 700 `#115079` | frost 500 `#5cc8ff` | Text links (darker on paper for contrast, about 7.6:1) |
| State `--md-accent-fg-color` | frost 600 `#1f7cb5` | frost 300 `#b3e7ff` | Hover, focus, pressed toggles |
| Masthead | n1 `#0b0b0d` | n1 `#0b0b0d` | Header, both modes |

The light mode keeps the bone paper; the coal ramp is dark-only. Neutral names (n0 to n12) and ramps are on the [brand page](brand-identity.md#palette).

Status chips use the brand's semantic set: exploration warning yellow, design info frost, accepted success green, placeholder danger red, planned dashed grey, closed and summary muted. Dark mode uses the brand values (`#f2c94c`, `#5cc8ff`, `#3fbf7f`, `#f0555a`); light mode uses darker steps of the same hues (`#7a5f00`, `#115079`, `#1f7a4d`, `#b3261e`) for contrast on paper. Always paired with the word, never colour alone.

Diagrams: node fill is the surface, node borders are neutral (`#55555d` dark, `#8a8378` light), not ember.

## Type

| Role | Face | Use |
|------|------|-----|
| Display | Barlow Condensed 500 / 600 / 700 | Headings, tabs, buttons. Uppercase for H1, tabs, labels |
| Text | IBM Plex Sans 400 / 400i / 700 | Body |
| Mono | IBM Plex Mono 400 / 500 | Code, table heads, eyebrows, chips |

All three are SIL OFL 1.1 and served from `assets/fonts/`. Body text is set smaller than the theme default (`.78rem` base) because the faces are large on the x-height; tables are `.72rem`.

## Components

| Component | Markup |
|-----------|--------|
| Status chip | `<span class="hg-status exploration">exploration</span>` (also `design`, `accepted`, `planned`, `placeholder`, `closed`, `summary`) |
| Button | `<a class="hg-btn primary" href="...">Label</a>`, without `primary` for the outline form |
| Hero, flow, index rows | `.hg-hero`, `.hg-flow`, `.hg-index > .hg-row` (see `docs/index.md`) |
| Module cards | `.hg-modgrid > .hg-mod` (generated, see [Module map](../architecture/modules.md)) |
| Diagram | a ` ```hg-diagram ` fence with Mermaid source |
| Callout | standard admonitions: square, 3 px left rule, no icon |

Rules: no rounded corners, no shadows, no gradients except the hero grid, no emoji, no stock imagery.

## Layout and width

The default is **block** width (the theme grid, comfortable for reading). The switch in the header (hidden below 60 em) toggles **fluid**, which uses the whole browser width for wide tables and diagrams. The choice is kept in the browser (`localStorage` key `hg-width`) and applied before first paint by `overrides/main.html`.

## Loading without jumps

- The five fonts used above the fold are preloaded; faces use `font-display: block`, so text is invisible for a moment instead of re-flowing when a font arrives.
- Colour scheme and width mode are set before the body renders.
- Diagrams render after load; they sit in a bordered box so the jump is contained.

## Privacy and licences

No external requests: fonts, scripts and Mermaid are self-hosted, there is no analytics or embedded widget. Licences for every asset are listed under [Licenses](../legal/licenses.md). Anything new must be self-hostable and permissively licensed before it is added.
