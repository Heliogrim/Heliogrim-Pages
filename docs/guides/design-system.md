# Site Design System

How the docs site applies the [brand identity](brand-identity.md). The brand page wins on the mark, palette and colour rules; this page records only how the site implements them. Source of truth for the implementation: `docs/stylesheets/heliogrim.css`, `docs/javascripts/diagrams.js`, `overrides/main.html`, `docs/assets/`. Change those and this page together.

## Idea

The site reads like an engineering drawing set: bone-coloured paper in light mode, warm obsidian in dark mode, hairline rules, square corners. **Frost** is the rare accent: the masthead rule, section markers, the active tab, primary buttons, index numbers. **Ember** is state: links, hover and focus, pressed toggles. This flips the brand's roles (ember rare, frost state) on purpose: the owner chose it for the site on 2026-11-16, and it applies to the site only; the editor follows the [brand rules](brand-identity.md#rules). The site also keeps its warm neutrals (bone paper, obsidian) instead of the brand's cool coal ramp: the owner found the coal dark mode lost the site's feel (2026-11-16).

## Mark

The brand [mark](brand-identity.md#mark): `assets/brand/mark.svg` in the header, `assets/brand/mark-16.svg` as favicon. The masthead is obsidian in both modes, so the mark always sits on dark. `assets/dial.svg` is the landing illustration, coloured as the splash art: grey line work, ember eclipse, frost glint on the outer ring. Do not recolour, outline, or add effects.

## Colour

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| Paper `--md-default-bg-color` | `#f4f1ea` | `#12100e` | Page |
| Surface `--hg-surface` | `#ebe6db` | `#1b1815` | Table heads, code, callouts, hover |
| Ink `--md-default-fg-color` | `#1b1917` | `#ece6da` | Text |
| Ink light | `#5f594f` | `#aaa397` | Secondary text |
| Ink lighter | `#8a8378` | `#756f65` | Muted text, closed and planned chips |
| Rule `--hg-rule` | `#d6d0c4` | `#2e2a25` | Hairlines |
| Accent `--hg-accent` | frost 600 `#1f7cb5` | frost 500 `#5cc8ff` | Accent fills, markers, index numbers (darker on paper for contrast); hover frost 700 / 400. The masthead rule and active tab are frost 500 in both modes, on the obsidian masthead |
| Link `--md-typeset-a-color` | ember 600 `#b5390d` | ember 400 `#ff8a4a` | Text links (darker on paper for contrast) |
| State `--md-accent-fg-color` | ember 700 `#7a2609` | ember 300 `#ffab7a` | Hover, focus, pressed toggles |
| Masthead | `#14110f` | `#14110f` | Header, both modes |

The neutrals are warm in both modes; the brand's coal ramp (n0 to n12, [brand page](brand-identity.md#palette)) is for the engine and editor.

Status chips use the brand's semantic set: exploration warning yellow, design info frost, accepted success green, placeholder danger red, planned dashed grey, closed and summary muted. Dark mode uses the brand values (`#f2c94c`, `#5cc8ff`, `#3fbf7f`, `#f0555a`); light mode uses darker steps of the same hues (`#7a5f00`, `#115079`, `#1f7a4d`, `#b3261e`) for contrast on paper. Always paired with the word, never colour alone.

Diagrams: node fill is the surface, node borders are neutral (`#756f65` dark, `#8a8378` light), not ember.

## Type

| Role | Face | Use |
|------|------|-----|
| Wordmark | IBM Plex Sans 300, caps, tracking 0.42 em | Site title in the header ([wordmark A](brand-identity.md#wordmarks)) |
| Display | Barlow Condensed 500 / 600 / 700 | Headings, tabs, buttons. Uppercase for H1, tabs, labels |
| Text | IBM Plex Sans 300 / 400 / 400i / 700 | Body (300 only for the wordmark) |
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
