# Tokens and theming

Source of truth: `companion/static/style.css` (`:root`, the `prefers-color-scheme: dark`
block, and the explicit `html[data-ui-theme="light"|"dark"]` blocks). A token change
means editing all of those blocks, so keep them equal. Area sheets
(`style-home.css`, `-flights.css`, `-place.css`, `-airlines.css`, `-display.css`,
`-admin.css`, `-c-console.css`, `-c-lists.css`) are linked per page by `page_styles.py`
and use tokens first; the deliberate bypasses are listed under Known exceptions at the end
of this file (`style-place.css` forced light ink over the light OSM tiles is the main one). One selector is declared once per
media context across the sheets (`test_stylesheet_structure.py`).

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
| `--color-status-ok-text` (the Copied label only) | `#15803D` | `#4ADE80` |
| `--color-status-warn` | `#D97706` | `#FBBF24` |
| `--color-status-error` | `#BE123C` | `#FB7185` |
| `--color-switch-off` | `#7C8799` | `#6B7589` |
| rarity inks occasional / rare | `#0F766E` / `#6D28D9` | `#5EEAD4` / `#C4B5FD` |
| `--rarity-tint` (fill of a rarity pill: the ink mixed into the card) | 10% | 28% |
| `--color-yellow-tile-edge` (3px edge of the light-yellow look tile on screen) | `#7A6D1D` | `#D9C24A` |
| `--color-map-ground` (what the map shows under and between tiles) | `#F2EFE9` | `#16140F` |

`--color-map-ground`, `--map-control-bg` and `--map-control-edge` are the one family whose
Auto-dark values are set in `style-place.css` (an `@media (prefers-color-scheme: dark)` block on
`html:not([data-ui-theme="light"])`), not in the four blocks of `style.css`; the values equal the
explicit Dark block. The explicit Light and Dark values and the `:root` default stay in `style.css`.

**Tokens with one value in every theme** (defined once in `:root`, not repeated per theme):
`--color-image-backdrop` (`#FFFFFF`, behind artwork), `--color-scrim` (black at 50%),
`--color-overlay-icon` and `--color-overlay-text` (ink at 55% / 70%, over pictures),
`--color-control-border-subtle` (ink at 9%),
`--shadow-control`, `--shadow-control-hover`, `--color-shadow-strong`, `--shadow-toast-docked`,
`--shadow-toast-float`.

**Other `:root` tokens not tabled here:** `--weight-title` 700, `--weight-semibold` 600,
`--weight-regular` 400; `--bar-border`, `--bar-sheen`, `--shadow-card`, `--shadow-card-hover`,
`--picture-placeholder`, `--color-switch-thumb`, `--color-switch-thumb-on`, `--color-frame-bezel`,
`--color-frame-bezel-hi`; the motion tokens (`--motion-spin` 700ms, `--motion-press` 90ms and the rest,
see `motion.md`). Theme-varying ones follow the four-block rule.

**Secondary ink** is not a token of its own: it is the text colour at 70%
(`color-mix(in srgb, var(--color-text) 70%, transparent)`), the same value as `--seg-idle-fg`.
Muted lines, the first-visit hint, the 404 caption and idle segments use it. A label on a tinted
panel (the opened Audit event) uses 80% to keep 4.5:1.

The yellow tile edge exists only on screen: the panel's yellow is too close to white to show the
tile's shape in the picker; the panel palette is untouched. Whether the yellow reads on the real
panel is an owner check.

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
| `--color-control-wash` (hover fill of row buttons) | `rgba(23,25,31,.045)` | `rgba(241,243,246,.08)` |
| `--bar-bg` (tab bar, sheets) | white .66 | `rgba(20,24,34,.86)` |
| `--pop-bg` (popovers) | white .90 | `rgba(28,34,45,.92)` |

The hover wash is a hint, not a boundary (no 3:1 claimed). Measured on painted pixels: the step
between resting and hovered fill is 1.09:1 in Light (white card, `#F5F5F5` on `#FFFFFF`) and
1.22:1 to 1.25:1 in Dark on the real surfaces (`#1C222D` card, `#151922` popover, `#262C37`
table header); the former single Light-shaped value gave 1.01:1 in Dark, no visible hover.

Shared geometry: `--glass-blur` 22px, `--glass-saturate` 165%, `--shadow-glass` (inset
highlight plus two soft layers), `--bar-shadow`, `--bar-sheet-shadow`, `--shadow-pop`.

Rules:
- A group, a free-content card (`.page-section`), a table wrapper and a segmented track
  share one glass look. A glass surface never sits inside another one. A card does not lift
  on hover; only an action reacts.
- The glass `backdrop-filter` declarations live inside the one `@supports
  ((-webkit-backdrop-filter: blur(1px)) or (backdrop-filter: blur(1px)))` block at the end
  of `style.css`. `backdrop-filter` also appears outside it: the More sheet's page scrim
  (`blur(8px)`, z-index 44, `style.css`), two 8px scrims on the Location page (`style-place.css`,
  `--place-lead` and `--place-tail`) and the Location sidebar's `blur(26px) saturate(200%)`
  (`style-place.css`, a frosted panel over the map). Outside the block each surface keeps its solid fill. Repeated cards and
  tracks take fill, edge and shadow without blur (a backdrop-filter traps fixed or absolute
  descendants and costs a layer). The tab bar and More sheet are opaque (`--glass-solid`); the scrim behind an open More sheet blurs 8px.
- Dialogs are not glass: an opaque surface over a dimmed page.
- The old "at most six blurred elements per page" budget is guidance only: the test that
  held it is gone and the More sheet added a scrim blur on every page. Keep blur to bars, sheets,
  dialogs, popovers and the sidebar.

## Radii, shadows

`--radius-control` 14px (buttons, inputs, tracks), `--radius-card` 22px (groups, cards,
tables), `--radius-sheet` 28px (top corners of phone sheets and dialogs), `--radius-pill`
32px (pills, switches, floating bars), `--radius-chip` 9px (the 32px icon chip in a row),
`--radius-frame-pic` 5px (the drawn portrait frame, never a capsule). Three small component radii
are named by their pixel value: `--radius-8` (check box, empty-state labels), `--radius-10` (Airlines tips,
the code popover, the gap prefix, icon hover), `--radius-12` (thumbnails, missing-illustration slots).
Circles use 50%. All radius tokens are theme-free: declared once in `:root`.

## Type

System sans only, nothing downloaded: `--font-ui` (SF Pro Text, Segoe UI, Roboto...),
`--font-display` (SF Pro Display...; titles), `--font-mono` (identifiers only: callsign,
ICAO24, firmware version). No `--font-serif`. No uppercase section-label voice, and tracking is
only the page title's -0.03em plus the exceptions below.

| Role | Token / size | Weight |
|------|--------------|--------|
| Page title (the one `h1`) | `--font-page-title-size` clamp 30-34px phone, 40-44px from 960px; `--tracking-title` -0.03em, line-height 1.08 | 700 |
| Sub-page / section title | `--font-heading-size` 22px | 600 |
| Card title | `--font-card-title-size` 17px | 600 |
| Section label over a group | `--font-caption-size` 13px, secondary ink | 600 |
| Body | `--font-body-size` 16px | 400 |
| Secondary (`.btn`, labels) | `--font-label-size` 15px | 600 for buttons |
| Caption | `--font-caption-size` 13px, secondary ink: first-visit hint, 404 caption, tile meta, hints under controls | 400 |
| Tab label / chart axis | 11px (tab label, the narrow Personalisation nav links, Home statistics hours and bar labels) / 12px (`.drawing-axis-label`); no 10px size exists | |

Other sizes in use that have no token: 14px (12 declarations), 12px (7), 11px (4), and display
numerals from 24px to 56px (Home statistics figure, battery gauge value, admin counters).
They are listed under Known exceptions.

**Tracking and case in use.** Headings (`h1`-`h3`, `.text-heading`, card and group titles) carry
-0.01em; display numerals carry -0.02em to -0.04em (`.home-flight__call`, `.home-stats__big`,
`.battery-gauge__value b`); the splash caption +0.02em. Uppercase with tracking
appears twice: the More sheet's preference label (`.tab-bar__prefs .section-label`, 0.06em) and the
pairing-code field (`.pair-card input.mono`, 26px, 0.18em, an identifier read off the frame).

The generic `.title-action__text` is `--title-size` 28px, 48px from 700px and 24px below 380px;
Home overrides it to 32px phone, 44px from 700px (`.home-state .title-action`), alone
(the info "i" is a 28px opaque disc inside a 44px hit area). Wall-clock times use `.time-value` (UI face,
tabular numerals); mono is for identifiers.

## Spacing, layout

Spacing tokens `--space-xs..3xl` = 4, 8, 16, 24, 32, 48, 64px, plus four in-between steps named by
their pixel value, because the t-shirt scale has no free step between its values: `--space-6`,
`--space-10`, `--space-12`, `--space-14` (6, 10, 12, 14px, for dense chips, pills, menu rows, toast and
modal fields). All spacing tokens are theme-free: declared once in `:root`. Sibling-card gap
`--space-lg`. Minimum width 360px (320px is out of contract; keep the 320px tab-bar fit
that is measured). Breakpoints: phone below 960px (`959.98px` in media queries), desktop
from 960px; also `700px`, `70rem` (Airlines and list sheets), `79.5rem` (Users table). Further
component-local queries exist: 600px (`599.98px`), 1000px, 1200px (`1199px`), 1280px, 480px
(`479.98px`), `379.98px`, `359.98px`, `40rem`, `30rem`, `29rem`, `26rem`, `23.75rem`; the 959px /
959.98px and 699px / 699.98px pairs are one boundary written two ways.

Spacing is token-first, not token-only: the scan (`scan_token_bypass.py`) lists 60 spacing literals
above 3px that stay literal (see Known exceptions); every repeated value sits on a token.

Safe areas: `--safe-top/right/bottom/left` (every shell sets `viewport-fit=cover`); fixed
bars, sheets, dialogs and toasts pad themselves with them. Floating tab bar tokens:
`--tab-bar-h` 68px, `--tab-bar-gap` 6px, `--tab-bar-side` 8px, `--tab-bar-pad` 2px,
`--tab-bar-max` 460px (the widest the bar and its More sheet grow on a tablet).
`--save-bar-h` is one 44px row plus padding. `--keyboard-inset` is set by `modal.js` on an open
dialog to the height the on-screen keyboard covers (0px otherwise); a phone sheet is anchored to
it and its `max-height` subtracts it.

Segmented contract: `--seg-edge`, `--seg-selected-bg` (accent), `--seg-selected-fg`,
`--seg-idle-fg`. They are the only place the segmented look changes.

## Dark and light

- Three states: Auto (`color-scheme: light dark`, follows the OS), Light, Dark. An explicit
  choice is the `ui_theme` cookie rendered as `html[data-ui-theme]` (`ui_nav.ui_theme_from_cookie`).
- `theme-color` meta: two tags with `prefers-color-scheme` media, Light `#E7EEF7` (`--sky-top`)
  and Dark `#12151D`; an explicit theme makes both tags carry that colour
  (`ui_base.theme_color_meta`). While the More sheet is open, `modal.js` rewrites the
  tags to the dimmed ground and restores them on close.
- **Dark map:** in Dark and in Auto-dark the Location page's one OpenStreetMap tile layer is
  inverted and turned back to its hues (`filter: invert(1) hue-rotate(180deg) brightness(.9)
  contrast(.95)` on `.leaflet-tile-pane`) so roads, runways and labels read on a dark ground;
  `--color-map-ground` and the map control colours (`--map-control-bg`, `--map-control-edge`) take
  their dark values. Light keeps the plain tiles. Over the dark map the app bar keeps the page's own
  dark colours; over the light map it takes the light palette.
- The favicon is graphite with a night-mode variant.
- Tests: `companion/test_sky_contrast.py` (every sky stop, both cascades),
  `companion/test_contrast_check.py`, `companion/test_stylesheet_structure.py`.

## iOS Home Screen web app

There is no manifest and no `apple-mobile-web-app-*` meta. `splash-boot.js` adds
`html.web-app` when `navigator.standalone === true` (before first paint). In that mode
`--app-bar-drop` is 24px below 960px so the phone app bar (logo, wordmark, frame button)
clears the frost iOS draws below the status bar (open WebKit bug); everything placed under the
bar adds it too, including the Location page's floating parts. History:
`.planning/debug/resolved/home-screen-app-wordmark-blur.md`.

## Known exceptions

Each is a deliberate bypass of a token or rule above. A new token would widen the scale, so the
literal stays; a change here is a visible change and belongs to a design decision.

- **Radii off the scale.** Three declarations use 6px (`.airlines-type`), 16px (`.battery-status`)
  or 18px (`.splash__panel`), and the Home chart bar uses `8px 8px 4px 4px`. Mapping them to a
  token would move pixels. A pill written as `999px` (`.upload-type-chip`) also stays: `--radius-pill`
  would change its computed radius. New components use the scale.
- **Font sizes with no token.** 11, 12 and 14px text and the display numerals (24px to 56px) are
  literal: each is a one-off size for a dense label or a number that is the content of a card.
  `.fleet-chip` and `.fleet-anchor` are among them.
- **Spacing off the scale.** One-off values with no repeat stay literal: 5, 7, 13, 18, 20, 22, 30,
  33, 46 and 52px (optical alignment of a picture, the table cell, the filter search input, the
  compact modal). New layout uses `--space-*`.
- **Spacing as geometry.** Negative hit-area insets and centring offsets (-4 to -48px), the 240px
  sidebar width, map pin sizes, the Save bar offset beside the fleet column and every `calc()` sized
  to a fixed width stay literal. Four `calc()` indents are the width of a dot or icon, not a step:
  8px (`.update-item__notes`), 12px (`li.entity-row`), 14px (`.home-state__dot`) and 32px
  (`.health-row__body`); they equal a token's value by accident and the scan reports them.
- **Light palette copied into `style-place.css`.** 11 light-palette literals (forced light ink over the
  light OSM tiles) and 3 dark map literals duplicate values of `style.css`. A Light palette change must
  be repeated there by hand.
- **Inline styles.** Three inline custom properties carry computed values (`--upload-preview-ratio`
  on the Airlines upload preview, `--seg` on the two route-bar segments) and the scripts write 44 run-time
  styles (geometry and gestures). No inline colour or spacing.
