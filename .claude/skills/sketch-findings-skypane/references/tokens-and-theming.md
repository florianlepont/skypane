# Tokens and theming

Source of truth: `companion/static/style.css` (`:root`, the `prefers-color-scheme: dark`
block, and the explicit `html[data-ui-theme="light"|"dark"]` blocks). A token change
means editing all of those blocks, so keep them equal. Area sheets
(`style-home.css`, `-flights.css`, `-place.css`, `-airlines.css`, `-display.css`,
`-admin.css`, `-c-console.css`, `-c-lists.css`) are linked per page by `page_styles.py`
and use tokens only; the one deliberate exception is `style-place.css` (forced light ink
over the light OSM tiles, a copy of the light palette).

No colour literal outside a `--` declaration in the shared stylesheets.

## Colour

| Token | Light | Dark |
|-------|-------|------|
| `--color-canvas` | `#F1F3F6` | `#161A24` |
| `--color-dominant` (card fill fallback) | `#FFFFFF` | `#151922` |
| `--color-secondary` (cool tint) | `#E9EEF5` | `#1C222D` |
| `--color-border` | `#DAE1EB` | `#2A3040` |
| `--color-text` | `#17191F` | `#F1F3F6` |
| `--color-accent` (graphite / ivory) | `#1F2430` | `#F2EFE9` |
| `--color-accent-hover` | `#343B4D` | `#E2DED5` |
| `--color-on-accent` | `#FFFFFF` | `#14171F` |
| `--color-status-ok` | `#16A34A` | `#4ADE80` |
| `--color-status-warn` | `#D97706` | `#FBBF24` |
| `--color-status-error` | `#BE123C` | `#FB7185` |
| `--color-switch-off` | `#7C8799` | `#6B7589` |
| rarity inks occasional / rare | `#0F766E` / `#6D28D9` | `#5EEAD4` / `#C4B5FD` |

The accent is neutral on purpose: it can never be mistaken for a status colour. Primary
buttons, the selected segmented pill, links, the focus ring and the on state of a switch
use it, and in Dark they invert to ivory with a dark label. There is no terracotta, no
warm beige and no serif left, except the toast `pending` tone (see Toast tokens).

Toast tokens (inverse slab: dark on light pages, light on dark pages): `--color-toast-bg`
`#1D2028` / `#E9ECF1`, `--color-toast-fg` `#F4F1EC` / `#151922`, and five tone inks
`-success -info -warning -error -pending`. `-pending` is `#FF9A70` (Light page) and
`#B13F16` (Dark page): the only orange in the app, kept for contrast on the slab. Design
debt, see SKILL.md.

## Sky and glass

One background per theme, painted on `<html>` (no fixed layer, no script, no time-of-day
skies). `--color-canvas` is the floor colour; `--sky-top` is the flat colour under the
gradient so a browser that tints its bars from the root reads the gradient's first stop.

| Token | Light | Dark |
|-------|-------|------|
| `--sky-top / -mid / -bottom` | `#E7EEF7 / #F1F3F6 / #EDF1F6` | `#12151D / #161A24 / #1A1F2B` |
| `--glass-bg` | `rgba(255,255,255,.72)` | `rgba(255,255,255,.09)` |
| `--glass-border` / `--glass-highlight` | white .85 / .9 | white .16 / .18 |
| `--glass-solid` (opaque fallback) | `#FFFFFF` | `#1C222D` |
| `--glass-hairline` (row separators) | ink .10 | white .10 |
| `--bar-bg` (tab bar, sheets) | white .66 | `rgba(20,24,34,.86)` |
| `--pop-bg` (popovers) | white .90 | `rgba(28,34,45,.92)` |

Shared geometry: `--glass-blur` 22px, `--glass-saturate` 165%, `--shadow-glass` (inset
highlight plus two soft layers), `--bar-shadow`, `--bar-sheet-shadow`, `--shadow-pop`.

Rules:
- A group, a free-content card (`.page-section`), a table wrapper and a segmented track
  share one glass look. A glass surface never sits inside another one. A card does not lift
  on hover; only an action reacts.
- The glass `backdrop-filter` declarations live inside the one `@supports
  ((-webkit-backdrop-filter: blur(1px)) or (backdrop-filter: blur(1px)))` block at the end
  of `style.css`; the one exception is the More sheet's page scrim (`blur(8px)`, z-index 44).
  Outside the block each surface keeps its solid fill. Repeated cards and
  tracks take fill, edge and shadow without blur (a backdrop-filter traps fixed or absolute
  descendants and costs a layer). The tab bar and More sheet are opaque (`--glass-solid`); the scrim behind an open More sheet blurs 8px.
- Dialogs are not glass: an opaque surface over a dimmed page.
- The old "at most six blurred elements per page" budget is guidance only: the test that
  held it is gone and round 35 added a scrim blur on every page. Keep blur to bars, sheets,
  dialogs, popovers and the sidebar.

## Radii, shadows

`--radius-control` 14px (buttons, inputs, tracks), `--radius-card` 22px (groups, cards,
tables), `--radius-sheet` 28px (top corners of phone sheets and dialogs), `--radius-pill`
32px (pills, switches, floating bars), `--radius-chip` 9px (the 32px icon chip in a row),
`--radius-frame-pic` 5px (the drawn portrait frame, never a capsule). Circles use 50%.

## Type

System sans only, nothing downloaded: `--font-ui` (SF Pro Text, Segoe UI, Roboto...),
`--font-display` (SF Pro Display...; titles), `--font-mono` (identifiers only: callsign,
ICAO24, firmware version). No `--font-serif`, no uppercase label voice, no tracking except
the page title.

| Role | Token / size | Weight |
|------|--------------|--------|
| Page title (the one `h1`) | `--font-page-title-size` clamp 30-34px phone, 40-44px from 960px; `--tracking-title` -0.03em, line-height 1.08 | 700 |
| Sub-page / section title | `--font-heading-size` 22px | 600 |
| Card title | `--font-card-title-size` 17px | 600 |
| Section label over a group | `--font-caption-size` 13px, secondary ink | 600 |
| Body | `--font-body-size` 16px | 400 |
| Secondary (`.btn`, labels) | `--font-label-size` 15px | 600 for buttons |
| Caption | `--font-caption-size` 13px | 400 |
| Tab label / chart axis | 11px / 10px (the only sub-scale sizes) | |

Home's title (`.title-action__text`) is `--title-size` 28px phone, 24px under 380px, 48px from
960px, with one rename icon link beside it. Wall-clock times use `.time-value` (UI face,
tabular numerals); mono is for identifiers.

## Spacing, layout

Spacing tokens `--space-xs..3xl` = 4, 8, 16, 24, 32, 48, 64px. Sibling-card gap
`--space-lg`. Minimum width 360px (320px is out of contract; keep the 320px tab-bar fit
that is measured). Breakpoints: phone below 960px (`959.98px` in media queries), desktop
from 960px; also `700px`, `70rem` (Airlines and list sheets), `79.5rem` (Users table).

Safe areas: `--safe-top/right/bottom/left` (every shell sets `viewport-fit=cover`); fixed
bars, sheets, dialogs and toasts pad themselves with them. Floating tab bar tokens:
`--tab-bar-h` 68px, `--tab-bar-gap` 6px, `--tab-bar-side` 8px, `--tab-bar-pad` 2px.
`--save-bar-h` is one 44px row plus padding. `--color-map-ground` `#F2EFE9` is the OSM land
colour (light tiles in both themes).

Segmented contract: `--seg-edge`, `--seg-selected-bg` (accent), `--seg-selected-fg`,
`--seg-idle-fg`. They are the only place the segmented look changes.

## Dark and light

- Three states: Auto (`color-scheme: light dark`, follows the OS), Light, Dark. An explicit
  choice is the `ui_theme` cookie rendered as `html[data-ui-theme]` (`ui_nav.ui_theme_from_cookie`).
- `theme-color` meta: two tags with `prefers-color-scheme` media, Light `#E7EEF7` (`--sky-top`)
  and Dark `#12151D`; an explicit theme makes both tags carry that colour
  (`ui_base.theme_color_meta`). While the More sheet is open, `modal.js` rewrites the
  tags to the dimmed ground and restores them on close.
- The Place page forces the light palette on the brand and frame button over the map
  (`style-place.css`), in both themes.
- The favicon is graphite with a night-mode variant (round 27).
- Tests: `companion/test_sky_contrast.py` (every sky stop, both cascades),
  `companion/test_contrast_check.py`, `companion/test_stylesheet_structure.py`.

## iOS Home Screen web app

There is no manifest and no `apple-mobile-web-app-*` meta. `splash-boot.js` adds
`html.web-app` when `navigator.standalone === true` (before first paint). In that mode
`--app-bar-drop` is 24px below 960px so the phone app bar (logo, wordmark, frame button)
clears the frost iOS draws below the status bar (open WebKit bug); everything placed under the
bar adds it too, including the Place page's floating parts. History:
`.planning/debug/resolved/home-screen-app-wordmark-blur.md`.
