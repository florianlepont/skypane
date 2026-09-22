# Phase 30: Aspect rebuilt — Pattern Map

**Mapped:** 2026-09-22
**Files analyzed:** 3 (all modified, zero new files — pure refactor per RESEARCH.md)
**Analogs found:** 3 / 3 (every target file is its own best analog — this is a relocate/rewrite-in-place phase, not new-file-from-template)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `companion/pages/config_page.py` — new `_aspect_card_html()` (replaces `_frame_colours_card_html()` at line 2135, absorbs `calendar_group()` at line 4459) | controller/view-builder (server-rendered HTML string builder) | request-response (CRUD form state → HTML) | itself: `_frame_colours_card_html()` (2135) + `calendar_group()` (4459) — both being merged, not an external analog | exact (self-merge) |
| `companion/pages/config_page.py` — new small palette-chip renderer (sits beside `_theme_chip_grid_html()`) | component (HTML fragment builder) | transform (hex → CSS shape) | `_theme_chip_grid_html()` (1609) + `.theme-chip`/`:has(input:checked)` CSS idiom (style.css 3560-3694) | role-match, smaller sibling of an existing chip renderer |
| `companion/static/style.css` — delete `.frame-colours*`/`.theme-carousel*`, add `.aspect-card`/`.usage-row*`/`.palette`/`.palette-chip*` | config/style (CSS rules) | transform | `.history-card__summary`/`::before` (4863-4899) for the `<details>` summary idiom; `.theme-chip:has(input:checked)` block (3560-3694) for selection state; global `summary`/`summary::before` chevron (5334-5389) | exact (native `<details>` summary idiom already shipped) |
| `companion/static/theme-preview.js` — rewrite in place (delete scroll-tracker/pager block, add hover/focus-follow) | utility/frontend-enhancement (event-driven) | event-driven | itself, pre-refactor (572 lines, full file already read in RESEARCH.md) — `applyPreviewSrc()`/crossfade (98-212, KEEP), chip-resolution idiom (340-354, mirror for new listener) | exact (in-place rewrite of the one script this app has for this purpose) |
| `companion/test_companion_app.py` — `_NO_JS_CONTROL_REGISTRY` edit (delete the pagers row, 960-1021) | test | request-response (string-level assertion) | itself — registry machine at 7083 | exact |
| `companion/test_browser_ux.py` — `_display_page_height()` guard (2858-2925) + carousel-specific checks (13554-13935) rewrite | test | browser/event-driven (Playwright) | itself — `_displays_page_height_is_recorded_at_both_phone_widths()` (13500-13550) | exact |
| `companion/i18n_fr/display.py` — new `ASPECT_HEADING_ID`/heading string, retire `FRAME_COLOURS_HEADING`/`FRAME_COLOURS_CAPTION`/`CALENDAR_CAPTION` | config (i18n constants) | CRUD (string table) | existing `FRAME_COLOURS_ROW_LABELS`/`SAME_AS_DEPARTURES_LABEL` etc. (display.py lines 100-107) | exact |

## Pattern Assignments

### `_aspect_card_html()` — merges `_frame_colours_card_html()` + `calendar_group()`

**Analogs:** `companion/pages/config_page.py:2135` (`_frame_colours_card_html`) and `:4459` (`calendar_group`)

**Form-outside-card pattern (must preserve):**
```python
# companion/pages/config_page.py:2338 — current card returns a <div class="page-section ...">
# that is a SIBLING of <form id="settings-form">, never a descendant, because it contains its
# own nested <form> elements (calendar connect/replace, rule-add). Every value-carrying control
# instead carries form="settings-form" literally on the <input>.
'<div class="page-section frame-colours" %s="%s">' ...
```
Apply identically to the new merged `.aspect-card` — do not nest it inside the physical form.

**Disconnect-form sibling-fragment pattern (must preserve):**
```python
# companion/pages/config_page.py:4701-4734
card_html = ('<div class="page-section" ...>' ... '</div>') % (...)
...
return card_html + disconnect_form_html   # two concatenated top-level strings
```
When flattening `calendar_group()`'s body into the Calendar `<details>` row, keep this exact
three-part shape: the Disconnect **button** renders inside the `<details>`; the `<form
id="calendar-disconnect-form">` it targets stays a separate fragment.

**Screen-group gate to collapse (Pitfall 3, RESEARCH.md):**
```python
# companion/pages/config_page.py:5672-5693 — TODAY: two separate `if` gates
if screens.GROUP_THEME in groups: frame_colours_section_html = _frame_colours_card_html(...)
if screens.GROUP_CALENDAR in groups: display_calendar_card_html = calendar_group(...)
# AFTER: ONE gate for the merged card (screens.GROUP_THEME in groups), with a code comment
# documenting the collapse rationale. handle_post()'s separate validation gates (6167, 6535)
# are NOT touched.
```

**Error handling / validation pattern:** unchanged — `escape_html()` at every interpolation site
(100% of existing call sites relocate verbatim); `THEME_IDS` membership check stays in
`server/device_config.py`, never duplicated client-side.

---

### New palette-chip renderer (small, CSS-drawn, no `<img>`)

**Analog:** `_theme_chip_grid_html()` (`companion/pages/config_page.py:1609-1656+`) — the existing
chip-grid renderer, kept unmodified as the compact rule-add form's renderer; the new palette-chip
is a second, smaller sibling function, NOT a fork of this one.

**Imports/helper pattern:**
```python
# companion/pages/config_page.py:1598-1606 — reuse verbatim for every swatch tier
def _palette_hex(index):
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    return "#%02X%02X%02X" % (r, g, b)
```

**Selectable-card hidden-radio idiom to mirror** (same shape as `_theme_chip_grid_html`'s existing
chips: a `<label>` wrapping a hidden native `<input type="radio">`, `name=` one of `theme` /
`theme_arriving` / `calendar_theme_id` / `rule_theme_id`, `form="settings-form"`, plus a swatch
element and a caption). Selected-state CSS reuses the `:has(input:checked)` mechanism below —
do not invent a second selected-state mechanism.

**Band-vs-plain swatch fill logic** — new code, no existing analog (first CSS-drawn, non-photo
swatch in the app); spec is exhaustive in UI-SPEC's "Swatch Rendering Contract" — solid
`background` for plain/field themes, `.swatch__band` absolutely-positioned strip (`top: 33%;
height: 34%`) for the other band themes, derived from `_palette_hex(departing_index)` /
`_palette_hex(band_index)`.

---

### `style.css` — `.aspect-card` / `.usage-row*` / `.palette` / `.palette-chip*`

**Analog 1 — `<details><summary>` disclosure idiom with a trailing/leading chevron:**
```css
/* companion/static/style.css:4863-4886 — .history-card__summary / ::before */
.history-card__summary {
  margin: calc(var(--space-md) * -1);
  padding: var(--space-md);
  align-items: center;
  color: inherit;
  min-height: 0;
}
.history-card__summary::before {
  order: 1;
  margin-right: 0;
  margin-left: var(--space-md);
  color: var(--color-accent);
}
```
```css
/* companion/static/style.css:5334-5389 — the GLOBAL summary rule every <details> in the app
   inherits, including the accordion's usage-row <summary> (per UI-SPEC: "the existing shared
   <summary> chevron mechanism... reuse the existing shared <summary>::before mechanism") */
summary {
  cursor: pointer;
  min-height: 44px;
  display: flex;
  align-items: center;
  color: var(--color-accent);
}
summary::before {
  content: "";
  flex: none;
  width: 6px;
  height: 6px;
  margin-right: var(--space-sm);
  border-right: 2px solid currentColor;
  /* ...border-bottom, rotate 45deg/-45deg on [open], see file for full rule */
}
```
The usage-row `<summary>` should use the global rule as-is (44px floor met directly, per UI-SPEC's
Touch Targets table) — do NOT reimplement a second chevron; only add row-specific padding
(`var(--space-md) 0`) and content layout (swatch + label text) around it, matching
`.history-card__summary`'s override-only-what-differs style.

**Analog 2 — selected-state `:has(input:checked)` idiom (re-key for `.palette-chip`):**
```css
/* companion/static/style.css:3560-3609 — @supports selector(:has(*)) block, .theme-chip */
@supports selector(:has(*)) {
  .theme-chip:has(input:checked) {
    border-color: var(--color-accent);
    box-shadow: inset 0 0 0 2px var(--color-accent);
    transform: scale(1.02);
  }
  .theme-chip:has(input:checked) .theme-chip__body {
    background: color-mix(in srgb, var(--color-accent) 12%, transparent);
  }
  .theme-chip:has(input:checked) .theme-chip__check {
    display: inline-flex;
  }
}
```
Add an equivalent `.palette-chip:has(input:checked)` block (border + check-glyph + background
wash — same three consequences, smaller box). This is the exact selector style.css's header
comment (line 45) already documents as the live-state pattern for selectable cards; extend the
header comment's selector list with `.palette-chip` rather than duplicating the accent-use entry
(per UI-SPEC Color section item 1).

**Deletion targets (grep each before removing, per RESEARCH.md Pattern 3 anti-pattern note):**
`.theme-carousel*` (style.css 10244-10430), `.frame-colours*` (10072-10233), `.theme-chip-grid--strip`.
Keep `.theme-chip` base block (3299-3830) and `.theme-chip--compact` — still consumed by the
rule-add form's grid.

---

### `theme-preview.js` — rewrite in place

**Analog:** the file's own pre-refactor state (full 572 lines already read in RESEARCH.md).

**Keep verbatim — crossfade mechanism** (`companion/static/theme-preview.js:98-212`):
```javascript
var FADE_CLASS = "theme-live-preview__image--swapping";
var pendingSrc = preview.getAttribute("src");
function applyPreviewSrc(src) { /* unchanged crossfade logic */ }
```

**Mirror, don't reinvent — chip-resolution idiom for the new hover/focus listener**
(`theme-preview.js:340-354`):
```javascript
var chip = input.parentNode;
if (!chip || !chip.getAttribute) { return; }
var isThemeChip = chip.className && chip.className.indexOf("theme-chip") !== -1;
var src = chip.getAttribute("data-preview-src");
```
New hover/focus listener should read `data-preview-src` the same way, delegated on
`mouseover`/`focusin` at the card root, reverting via `mouseout`/`focusout` to the open row's own
currently-checked chip's src (reuse `checkedChipSrc()`, 234-250, re-scoped from "panel" to
"currently-open `<details>`").

**Load-bearing guard to update (Pitfall 5) — top-level selector:**
```javascript
// theme-preview.js:87 — TODAY
var card = document.querySelector(".frame-colours");
if (!card) { return; }
// AFTER: re-scope to whatever wrapper class the merged card uses (e.g. ".aspect-card")
// Miss this line and the ENTIRE script silently no-ops with zero error/console warning.
```

**Delete outright:** `panelForUsage()`/`departuresPanel()`/`effectiveSrcForUsage()`/`showUsage()`/
`checkedUsage()`/`COLLAPSED_PANEL_CLASS`, and the scroll-tracker/pager block
(`makeScrollPreviewTracker()`, 490-543, plus the surrounding pager/IntersectionObserver code,
lines ~214-566 per RESEARCH.md's Pitfall 4 line-range estimate) — all `colour_usage`-driven, now
dead the instant `<details name="aspect-rows">` replaces the radiogroup.

---

## Shared Patterns

### Native `<details name="...">` grouped accordion — zero script
**Source:** HTML5 spec, first use in this app (no in-repo prior instance of the `name=` grouping
attribute; the closest existing single-`<details>` disclosures are `.history-card__details`,
`calendar-url-disclosure`, and the plain `<details><summary>...</summary>...</details>` idiom used
~8 times in `config_page.py`, e.g. lines 2291, 4276, 4695).
**Apply to:** all four `aspect-rows` `<details>` elements. Row 1 (`departing`) ships `open`; rows
2-4 do not. No JS listener, no `aria-expanded` management beyond native `<summary>` behaviour.

### Selected-card `:has(input:checked)` idiom
**Source:** `companion/static/style.css:3560-3694` (`.theme-chip`, `.runway-card`)
**Apply to:** `.palette-chip` (new, smaller) — same three-property consequence set (border, check
glyph, background wash), never a second/different selected-state mechanism.

### `escape_html()` at every interpolation site
**Source:** existing discipline throughout `_frame_colours_card_html()`/`calendar_group()`
**Apply to:** every new/relocated string interpolation in `_aspect_card_html()` and the new
palette-chip renderer — no raw string interpolation introduced for new markup.

### `form="settings-form"` cross-submit + sibling-form pattern
**Source:** `companion/pages/config_page.py:2338`, `4701-4734` (see Pattern Assignments above)
**Apply to:** `_aspect_card_html()`'s overall return shape — must stay a sibling of `<form
id="settings-form">`, with the calendar disconnect form kept as its own fragment.

## No Analog Found

| File/Piece | Role | Data Flow | Reason |
|---|---|---|---|
| `theme-preview.js` hover/focus-follow listener | utility (event-driven) | event-driven | No existing code in this repo implements hover/focus-driven preview swap — the old script only ever tracked scroll position or committed clicks (RESEARCH.md Pitfall 4/Assumption A2). Executor should check `.planning/sketches/006-aspect-tile-accordion-vs-segments/index.html` for any throwaway `<script>` block before writing from scratch (RESEARCH.md Open Question 1) — not yet confirmed to exist. |
| Band-swatch CSS shape (`.swatch__band` positioned strip inside a chip 44-64px square) | component/CSS | transform | First CSS-drawn (non-photo) themed swatch in the app; UI-SPEC's Swatch Rendering Contract is the sole spec, fully self-contained, no existing analog needed beyond `_palette_hex()`'s hex math. |

## Metadata

**Analog search scope:** `companion/pages/config_page.py`, `companion/static/style.css`,
`companion/static/theme-preview.js`, `companion/test_companion_app.py`,
`companion/test_browser_ux.py`, `companion/i18n_fr/display.py` — all read/grepped directly in this
worktree, 2026-09-22, cross-checked against 30-RESEARCH.md's own line citations (all confirmed
current in this session's independent greps).
**Files scanned:** 6 direct reads/greps this session, plus full inventory already verified in
30-RESEARCH.md (which this pattern map treats as pre-verified ground truth for line numbers).
**Pattern extraction date:** 2026-09-22
