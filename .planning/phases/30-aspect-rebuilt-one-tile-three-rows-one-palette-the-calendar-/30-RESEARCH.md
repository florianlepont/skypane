# Phase 30: Aspect rebuilt — one tile, three rows, one palette, the calendar absorbed — Research

**Researched:** 2026-09-22
**Domain:** Server-rendered HTML/CSS/JS refactor of an existing Python settings page (no new
libraries, no new endpoints) — a structural rebuild of two existing cards into one, replacing a
radiogroup+JS-collapse mechanism with a native `<details name="...">` accordion.
**Confidence:** HIGH — every citation below was re-read directly against the code in this worktree
today (2026-09-22, post-Phase-29), not carried forward from ROADMAP's Phase-28-era text.

---

## Summary

This phase has **no discuss-phase / no CONTEXT.md** — the 30-UI-SPEC.md (developer-approved,
6/6 dimensions, sourced from the winning `/gsd-sketch` 006 Variant A) is this phase's structural
and copy contract and already resolves nearly every design question a normal discuss-phase would
raise. This RESEARCH.md's job is narrower and more mechanical: **verify every code citation the
UI-SPEC and ROADMAP make against the CURRENT tree**, and surface the parts neither document
worked out in full — principally the `theme-preview.js` rewrite shape and the two
registries/instruments the plan must touch precisely (`_NO_JS_CONTROL_REGISTRY`,
`_display_page_height()`).

Every builder function, constant, and CSS class the UI-SPEC names was re-confirmed present at the
line numbers below, in the current, post-Phase-29 tree. The `THEME_IDS`/`THEMES` registry facts
(18 themes, `departing_index == arriving_index` for all 18, 7 band themes, `band_blue_field`/
`band_red_field` have `departing_index == band_index`) were re-derived by importing
`server/device_config.py` directly, not re-typed from ROADMAP — all confirmed true today.

**The one area requiring genuine new design work, not just relocation:** `theme-preview.js`'s
current ~570 lines are built entirely around a `colour_usage` radiogroup driving JS-toggled panel
visibility, plus ~200 lines of scroll-snap-strip/pager/IntersectionObserver machinery for the
carousel. The new accordion design retires `colour_usage` as a concept outright (row visibility is
native `<details>` state) and retires the whole strip/pager/scroll-tracker block, but must ADD a
genuinely new interaction the old script never had: the preview following **hover/focus** over a
non-scrolling wrapping grid (old script only ever followed scroll position or a committed click).
This is flagged as the primary technical risk of the phase — see Architecture Patterns below.

**Primary recommendation:** Treat this as three sequenced workstreams — (1) Python: merge
`_frame_colours_card_html()` + `calendar_group()` into one `_aspect_card_html()` builder using
`<details name="aspect-rows">`, retire `_frame_colours_row_html()`/`_theme_carousel_html()`/the
`colour_usage` field and its panel-toggle markup, add a new small palette-chip renderer beside
(not replacing) `_theme_chip_grid_html()`; (2) CSS: delete the `.theme-carousel*` block and the
`.frame-colours__row`/`__list`/`__panel-legend`/`__usage-panel*` rules, add `.aspect-card`/
`.usage-row`/`.palette`/`.palette-chip` rules reusing existing tokens only; (3) JS: rewrite
`theme-preview.js`'s DOM-query surface from `.frame-colours` to the new wrapper, delete the
scroll-tracker/pager code, delete the `colour_usage`-driven `showUsage()`/panel-collapse logic
entirely (accordion is native), and add the new hover/focus-follow behaviour. Run
`_display_page_height()` before touching any markup, then again after, and report the delta
honestly.

---

## User Constraints

No CONTEXT.md exists for this phase (confirmed: `ls .planning/phases/30-.../├─CONTEXT.md` absent).
Per ROADMAP's own text and 30-UI-SPEC.md §0, **this is expected** — CFG-85 explicitly routes
structural decisions through a `/gsd-sketch` round instead of discuss-phase, and that round is
closed (Variant A/Accordion won, developer-approved 2026-09-22). The 30-UI-SPEC.md IS this
phase's locked-decision surface; treat every section in it as if it were a CONTEXT.md
`## Decisions` list. In particular:

- The accordion-vs-segments question is CLOSED. Do not re-litigate it.
- §6 of the UI-SPEC records one deliberate, approved departure from ROADMAP's own prose (no
  third "Gérer" wrapper around the calendar's connection block — build the flatter, sketch-approved
  shape). Follow the UI-SPEC's markup over ROADMAP's prose wherever they conflict.
- Nothing in this phase is "Claude's Discretion" in the CONTEXT.md sense — the UI-SPEC is
  exhaustive on copy, spacing, colour, typography, and structure. The genuine open engineering
  decision this research adds (not covered by the UI-SPEC, which is a design contract, not an
  implementation plan) is **how `theme-preview.js` is restructured** — see Architecture Patterns.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-85 | Aspect is one tile: live preview, three usage rows (Départs/Arrivées/Vols du calendrier, accordion, one open at a time), wrapping 18-theme palette under the open row (no strip/scrollbar/pagers/dots/disclosure), calendar's connection folded under its own row, "Règles par vol" as a secondary disclosure row; no-JS control contract holds; CSP untouched; no new script file/custom property/colour/family/size; every retired carousel rule grepped for a surviving consumer before deletion. | Structural/Markup Contract and Swatch Rendering Contract sections below map every retired class/function/constant to its current, re-verified location; No-JS Control Contract section identifies the exact `_NO_JS_CONTROL_REGISTRY` row that must be edited (not merely repointed — see Common Pitfalls). |
| CFG-86 | Display's page height at 390px is measured by the registered instrument before and after, reported against X6's 2,600px target, delta stated, target never restated to fit. | Validation Architecture section below identifies the exact instrument (`_display_page_height()`, `companion/test_browser_ux.py:2870`) and its guard preconditions, which the plan must update (the heading-id guard breaks once `FRAME_COLOURS_HEADING_ID`/"Frame colours" is renamed to "Aspect"). Environment Availability section flags that Playwright/Chromium are NOT currently installed in this worktree — the plan's Wave 0 must install them before either measurement can run. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Accordion open/close (one row at a time) | Browser (native HTML) | — | `<details name="aspect-rows">` — the browser's own grouped-`<details>` behaviour; zero script, zero server state needed per-request beyond which row starts `open` |
| Theme/colour selection (departures/arrivals/calendar/rules) | API/Backend (Python, form POST) | Browser (native radio) | Unchanged from today — four native radiogroups cross-submitting via `form="settings-form"`; `companion/pages/config_page.py`'s `handle_post()` validates and `server/device_config.py` persists |
| Live preview image | API/Backend (server-rendered PNG route) | Frontend enhancement (JS crossfade + hover-follow) | `THEME_PREVIEW_ROUTE_PREFIX` route renders the saved theme server-side (no-JS floor); `theme-preview.js` is a pure UX enhancement layered on top, never the source of truth |
| Palette swatch rendering (CSS-drawn shape) | Browser (CSS) | API/Backend (hex values) | `_palette_hex()` computes real ink hex server-side and emits it as an inline style; the browser paints the shape (solid vs. banded) via CSS only — no client-side colour logic |
| Calendar connection status/actions | API/Backend | Browser (native disclosure/confirm) | `calendar_group()`'s existing logic (status branches, connect/replace/disconnect forms) is relocated, not rewritten; the two-step disconnect confirm (native `confirm()` + server-rendered fallback page) stays exactly as-is |
| Page-height measurement (CFG-86) | Browser (Playwright-driven Chromium) | — | `_display_page_height()` in `companion/test_browser_ux.py` — a real rendered-DOM measurement, not a static estimate |

---

## Standard Stack

No new libraries. This phase is a pure refactor of existing, already-chosen technology:

| Technology | Current version in tree | Role in this phase |
|------------|--------------------------|---------------------|
| Python 3.11 (stdlib HTTP service) | `server/.venv` targets 3.11 | `companion/pages/config_page.py` — server-rendered HTML string builders, no template engine, no framework |
| Native HTML5 `<details>`/`<summary>` | — | The accordion mechanism itself; zero JS dependency for open/close by design |
| Vanilla ES5-subset JS (no build step) | — | `companion/static/theme-preview.js` — var-only, no arrow functions, no template literals (existing house style, enforced by `companion/test_companion_app.py`'s backtick-ban and script-count-pin checks) |
| Playwright (dev-only) | not currently installed in this worktree's Python 3.11 env (see Environment Availability) | `companion/test_browser_ux.py` — the only harness that can prove the no-JS-blocked round trip and measure CFG-86's page height |

**Installation:** none required for the Python/CSS/JS implementation itself. For running the
CFG-86 measurement and the browser-level no-JS checks:
```bash
pip install -r server/requirements-dev.txt
python -m playwright install chromium
```

**Version verification:** N/A — no third-party package versions are being chosen in this phase.

## Package Legitimacy Audit

Not applicable — this phase installs no new packages (Playwright is an existing dev dependency
already declared in `server/requirements-dev.txt`, merely not yet installed in this particular
worktree's environment).

---

## Architecture Patterns

### System Architecture Diagram

```
GET /display (authenticated)
        │
        ▼
companion/pages/config_page.py: render(ctx, scope=SCOPE_ALL/SCOPE_DISPLAY)
        │
        │  today: two separate calls, two separate <div class="page-section"> cards
        │  after this phase: ONE call, ONE <div class="page-section aspect-card">
        ▼
_aspect_card_html(ctx, current_theme_id, current_theme_arriving,
                   current_calendar_theme_id, calendar_status_fields...,
                   errors, submitted, state_dir)
        │
        ├─► live preview <img> ── src set server-side to THEME_PREVIEW_ROUTE_PREFIX + saved id
        │
        ├─► <details name="aspect-rows" open data-usage="departing">
        │       <summary> swatch + "Departures — {theme}"
        │       .palette (18 × palette-chip, native radios name="theme")
        │
        ├─► <details name="aspect-rows" data-usage="arriving">
        │       <summary> + leading "Same as departures" radio + .palette (name="theme_arriving")
        │
        ├─► <details name="aspect-rows" data-usage="calendar">
        │       <summary> + leading option + .palette (name="calendar_theme_id")
        │       + relocated calendar_group() status/connect/replace/disconnect/how-it-works,
        │         flattened directly into this <details> (UI-SPEC §6 — no extra "Gérer" wrapper)
        │
        └─► <details name="aspect-rows" usage-row--secondary> "Règles par vol"
                _rule_list_html() output
                nested <details class="rule-add"> → _rule_add_form_html() (UNCHANGED)
        │
        ▼
Every radio cross-submits via form="settings-form" (physical <form> is a SIBLING of this card,
unchanged design already used by both retiring cards) ──► POST /settings ──► handle_post()
        │
        ▼
server/device_config.py: save_device_config(theme=..., theme_arriving=..., calendar_theme_id=...)
        │  (normalise_calendar_theme_id / THEME_IDS membership check — unchanged by this phase)
        ▼
On next GET, the saved theme drives both the server-rendered preview <img> and which palette-chip
renders selected — the round trip this phase's own no-JS proof (CFG-85) exercises directly.

Client-side enhancement layer (companion/static/theme-preview.js), scripts optional:
  - crossfade the preview <img> on selection (existing FADE_CLASS mechanism, KEPT)
  - NEW: follow hover/focus over any palette-chip's data-preview-src, reverting to the
    open row's own checked selection on mouseout/blur (does not exist today in any form —
    the old file only ever followed SCROLL position, never hover/focus, because the old
    control was a scroll-snap strip, not a static wrapping grid)
  - DELETED: colour_usage-driven showUsage()/panel-collapse, pagers, scroll-tracker,
    IntersectionObserver block (all carousel-specific, ~230 of the file's 572 lines)
```

### Recommended Project Structure

No new files/directories. Everything lands in the three files already implicated:

```
companion/
├── pages/config_page.py     # _aspect_card_html() replaces _frame_colours_card_html()
│                             #   + absorbs calendar_group()'s card body (disconnect <form>
│                             #   sibling fragment concatenation pattern is UNCHANGED — see
│                             #   Common Pitfalls)
├── static/style.css          # .frame-colours*/.theme-carousel* rules deleted;
│                             #   .aspect-card/.usage-row*/.palette/.palette-chip* rules added
└── static/theme-preview.js   # rewritten in place — same file, same route, same CSP entry
```

### Pattern 1: One `<form>` outside the card, controls cross-submit via `form=` attribute

**What:** Both retiring cards (`_frame_colours_card_html()`, `calendar_group()`) already render
as **siblings** of `<form id="settings-form">`, not descendants — because both embed genuine
nested `<form>` elements of their own (the calendar connect/replace form, the rule-add form), and
HTML forbids a `<form>` inside a `<form>`. Every value-carrying control (`theme`, `theme_arriving`,
`calendar_theme_id`, `rule_theme_id`) instead carries a literal `form="settings-form"` attribute.
**When to use:** The merged `.aspect-card` MUST follow the identical pattern — it inherits both
source cards' nested-form obligations (calendar connect/replace, rule-add). Do not attempt to move
it inside the physical form; that would break the calendar/rule forms immediately.
**Example — confirmed current code:**
```python
# companion/pages/config_page.py:2338 (current _frame_colours_card_html return, to be replaced)
'<div class="page-section frame-colours" %s="%s">' ...
# companion/pages/config_page.py:5672-5693 (current render() call site — BOTH cards individually
# gated and _nested_wrapper_html()-wrapped; the merge must become ONE call, ONE gate — see
# Common Pitfalls re: screens.GROUP_THEME vs screens.GROUP_CALENDAR)
```

### Pattern 2: The calendar disconnect `<form>` is a separate sibling fragment, not nested markup

**What:** `calendar_group()` returns `card_html + disconnect_form_html` — two concatenated
strings, where `disconnect_form_html` is a wholly separate `<form id="calendar-disconnect-form">`
element (never nested inside `card_html`'s own div), because the visible Disconnect **button**
lives inside the card (reachable from inside the `.aspect-card`/inside the Calendar `<details>`)
but the `<form>` it submits to (`form="calendar-disconnect-form"`) must not be nested inside
whichever ancestor form structure the button sits in.
**When to use:** When flattening `calendar_group()`'s body into the Calendar `<details>` row,
keep this exact three-part shape: the button renders INSIDE the `<details>`, and the disconnect
`<form>` fragment is concatenated onto the overall `_aspect_card_html()` return value as a sibling
of the whole `.aspect-card` div (or, since `<details>` is not itself a `<form>`, the disconnect
form MAY legally live inside the `<details>` too — but matching the existing, already-proven
pattern rather than inventing a new one is the lower-risk choice).
**Example:**
```python
# companion/pages/config_page.py:4701-4734
card_html = ('<div class="page-section" ...>' ... '</div>') % (...)
...
return card_html + disconnect_form_html
```

### Pattern 3: `<details name="...">` grouped accordion — zero script needed

**What:** HTML5's grouped `<details name="group">` makes sibling `<details>` elements mutually
exclusive natively — opening one closes the others — in every current browser, with scripts
blocked or not. This is the mechanism the whole accordion depends on; it needs no JS listener, no
ARIA `aria-expanded` management beyond what `<summary>` already provides natively, and no
server-side "which panel is currently displayed" state at all (each row independently starts
`open` or not, per the UI-SPEC's markup order).
**When to use:** All four `aspect-rows` `<details>` elements, exactly as the UI-SPEC's Structural
Contract specifies (row 1 `open` by default, others closed).
**Anti-pattern to avoid:** Do NOT port forward the retiring `colour_usage` radiogroup +
`data-usage-panel-target` + JS `showUsage()`/collapse-class mechanism believing it is "compatible"
with the new accordion — it is a wholly different, now-redundant mechanism for the exact same
concern (which row is showing) and keeping both would mean two independent, driftable sources of
truth for the same UI state.

### Anti-Patterns to Avoid

- **Reviving the sketch's `<button aria-pressed>` "Same as departures" markup verbatim.** The
  UI-SPEC explicitly flags this (Structural Contract, "Comme les départs leading option"
  paragraph): the sketch's own button has no no-JS fallback. The real control must stay
  `_same_as_departures_chip_html()` — note the UI-SPEC's prose calls this `leading_chip_html`,
  which is actually just a *keyword argument name* on `_theme_chip_grid_html()`
  (`leading_chip_html=...`, confirmed at `companion/pages/config_page.py:2211`), not the function's
  own name. The function to reuse is `_same_as_departures_chip_html()` at line 2044.
- **Deleting `_theme_chip_grid_html()` or `_theme_chip_grid_html()`'s output wholesale.** It keeps
  one live, in-scope call site after this phase: the rule-add form's own compact grid (line ~4924,
  `_rule_add_form_html()`), which the UI-SPEC explicitly says stays untouched. Only the THREE
  carousel-wrapped call sites (departures/arrivals/calendar, inside `_frame_colours_card_html()`)
  are retired; the rule-add form's grid usage is NOT one of them.
- **Treating `.theme-chip` CSS as fully retired.** `.theme-chip--compact` (and its selected-state
  rules) stays live for the rule-add form's grid. Only the carousel-specific modifiers
  (`.theme-chip-grid--strip`, `.theme-carousel*`) and the big, non-compact `.theme-chip` (the
  320×120 photo-preview chip, used by the now-retired full-size departures grid) are candidates for
  deletion — grep for surviving consumers per-selector, not per-file, before deleting anything.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| One-open-at-a-time accordion | A JS click handler toggling `hidden`/`open` on sibling `<details>` | `<details name="aspect-rows">` (native, already the UI-SPEC's chosen mechanism) | Zero script, correct keyboard/AT behaviour for free, works identically with scripts blocked |
| Selected-swatch highlight | A new `:checked`-adjacent selector | The existing `:has(input:checked)` idiom `.theme-chip`/`.runway-card` already use (style.css ~3570-3679) | UI-SPEC's Color section explicitly names this as a re-keyed reuse, not a new mechanism — avoids a second, driftable selected-state implementation |
| Swatch shape rendering | A tiny inline SVG per theme, or a canvas draw | Plain CSS: solid `background` for plain/field themes, a `.swatch__band` absolutely-positioned strip for band themes (UI-SPEC's Swatch Rendering Contract, fully specified) | Already-computed real ink hex via `_palette_hex()`; CSS achieves the exact visual with zero new markup complexity |

**Key insight:** Nearly everything this phase needs already exists somewhere in the current
codebase in a slightly different shape (a different-sized chip, a different wrapper div, a
different script scope). The dominant risk is NOT "what do we build" — the UI-SPEC has already
answered that exhaustively — it is **mis-tracking which existing pieces to relocate verbatim vs.
which to genuinely rewrite**, especially inside `theme-preview.js` where the old and new
interaction models (scroll-tracking vs. hover-tracking) are structurally different enough that a
naive line-by-line edit will leave dead code paths (see Common Pitfalls).

---

## Swatch Rendering Contract (re-verified against live registry data)

Re-derived directly from `server/device_config.py` (not re-typed from the UI-SPEC or ROADMAP):

```python
>>> len(device_config.THEMES)
18
>>> all(t["departing_index"] == t["arriving_index"] for t in device_config.THEMES.values())
True
>>> [tid for tid, t in device_config.THEMES.items() if "band_index" in t]
['band_blue', 'band_blue_light', 'band_green_light', 'band_red', 'band_black',
 'band_blue_field', 'band_red_field']   # 7 of 18
>>> device_config.THEMES["band_blue_field"]["departing_index"] == device_config.THEMES["band_blue_field"]["band_index"]
True   # same for band_red_field — confirms UI-SPEC's "solid fill, not fake two-tone band" rule
```

`_palette_hex(index)` (`companion/pages/config_page.py:1598`) computes `#RRGGBB` from
`server/panel_format.PALETTE_RGB` — confirmed present, unchanged, safe to reuse verbatim for every
swatch (row-summary, palette-chip, rule-row).

---

## Structural/Markup Contract — re-verified function/constant inventory

Every name below was located and read directly in the current tree (2026-09-22, post-Phase-29).
Where the UI-SPEC's prose used an inexact name, the correction is noted.

| Name (UI-SPEC/ROADMAP citation) | Confirmed current location | Status / correction |
|---|---|---|
| `_frame_colours_card_html()` | `companion/pages/config_page.py:2135` | Present, unchanged shape (preview + 4-row `colour_usage` radiogroup + 4 usage panels). **Full replacement target.** |
| `_theme_carousel_html(grid_html, strip_id)` | `companion/pages/config_page.py:1782` | Present. **Retire entirely** — no consumer once the strip layout is gone. |
| `_theme_chip_grid_html(...)` | `companion/pages/config_page.py:1609` | Present. **Keep** — stays the renderer for the rule-add form's compact grid (its one remaining live call site after this phase). Do not delete or fork. |
| `calendar_group(...)` | `companion/pages/config_page.py:4459` | Present, full docstring re-read (4459-4574 + branches through 4734). Returns `card_html + disconnect_form_html` (two concatenated fragments — see Pattern 2). **Body relocates into the Calendar `<details>` row; the disconnect-form sibling-fragment pattern must be preserved.** |
| `_rule_add_form_html(errors=None, submitted=None)` | `companion/pages/config_page.py:4924` | Present, unchanged signature. **Reuse verbatim**, now nested one level deeper behind a new `<details class="rule-add">`. |
| `_rule_row_html(kind, value, theme_id)` / `_rule_list_html(rows)` | `companion/pages/config_page.py:5055` / `5113` | Present, unchanged. **Reuse verbatim.** |
| `_palette_hex(index)` | `companion/pages/config_page.py:1598` | Present, unchanged. **Reuse verbatim** for every swatch tier. |
| `_same_as_departures_chip_html(field_name, checked, radio_form_id=None)` | `companion/pages/config_page.py:2044` | Present. **This is the real function name** — the UI-SPEC's prose calls it `leading_chip_html`, which is actually the *keyword-argument name* `_theme_chip_grid_html()` accepts (confirmed at line 2211: `leading_chip_html=arrivals_leading_chip`), not this function's own name. Cite `_same_as_departures_chip_html()` in the plan, not `leading_chip_html`. |
| `_frame_colours_row_html(usage, checked, label, meta_text, dep_hex, arr_hex)` | `companion/pages/config_page.py:2083` | Present. **Retire entirely** — this IS the `colour_usage` 4-row radiogroup markup the accordion replaces. |
| `COLOUR_USAGES` / `COLOUR_USAGE_DEPARTURES/_ARRIVALS/_CALENDAR/_RULES` | `companion/pages/config_page.py:233-240` | Present. `COLOUR_USAGE_*` string constants (`"departures"`/`"arrivals"`/`"calendar"`/`"rules"`) stay useful as the `data-usage` attribute values the UI-SPEC's markup contract specifies for each `<details>` — reuse the constants, retire only the radiogroup markup built from them. |
| `FRAME_COLOURS_ROW_LABELS` | `companion/pages/config_page.py:243` | Present. **Reuse verbatim** — UI-SPEC's Copywriting Contract cites this correctly. |
| `FRAME_COLOURS_HEADING` / `FRAME_COLOURS_HEADING_ID` | `companion/pages/config_page.py:227-228` | Present, current values `"Frame colours"` / `"frame-colours-heading"`. **Both are replaced** — UI-SPEC's copy contract requires "Aspect" as the new heading. **The new heading id must be a NEW constant** (e.g. `ASPECT_HEADING_ID`) — see Common Pitfalls re: the CFG-86 instrument's guard reading `FRAME_COLOURS_HEADING_ID` by name. |
| `ASPECT_CAPTION_EXEMPTIONS` | `companion/pages/config_page.py:1342` | Present, currently `(DISPLAY_LOOK_INTRO, FRAME_COLOURS_CAPTION, CALENDAR_CAPTION, CALENDAR_URL_HINT)`. Its own header comment (lines 1336-1341) already states it "is EXPECTED TO BECOME EMPTY" once this phase lands. **This phase must remove `FRAME_COLOURS_CAPTION` and `CALENDAR_CAPTION` from the tuple** (both captions are deleted per UI-SPEC's Copywriting Contract) — `DISPLAY_LOOK_INTRO` and `CALENDAR_URL_HINT` are NOT touched by this phase and stay as the tuple's remaining two members (the tuple does NOT become empty this phase — ROADMAP/UI-SPEC's framing of "the day the tuple empties" refers to a still-later editorial pass on the Look intro and the URL hint, not this phase). |
| `THEME_CAROUSEL_STRIP_ID` / `_ARRIVALS` / `_CALENDAR` | `companion/pages/config_page.py:322/327/328` | Present. **Retire entirely** — no strip, no `id`-addressed scroll container in the new design. |
| `THEME_CAROUSEL_WRAPPER_ATTR = "data-theme-carousel"` | `companion/pages/config_page.py:334` | Present. **Retire** — see Common Pitfalls re: `_NO_JS_CONTROL_REGISTRY`. |
| `screens.GROUP_THEME` / `screens.GROUP_CALENDAR` | `companion/screens.py:27,33` | Present, both members of the single registered screen type's `everyday_groups` tuple (`companion/screens.py:86-87`) — **today, always both present together** (one screen type exists). The `render()` call site (`companion/pages/config_page.py:5672-5693`) currently gates the two cards on two SEPARATE `if screens.GROUP_THEME in groups` / `if screens.GROUP_CALENDAR in groups` conditions. **Merging into one card needs one merged gate** — see Common Pitfalls. |

---

## Common Pitfalls

### Pitfall 1: The CFG-86 measurement instrument's guard will silently break once the heading changes

**What goes wrong:** `_display_page_height()` (`companion/test_browser_ux.py:2870`) asserts the
fetched page is genuinely the authenticated Display page by checking
`document.getElementById(config_page.FRAME_COLOURS_HEADING_ID)` is truthy (probe defined at line
2858-2867, `headingId` argument passed at line 2896). Once `FRAME_COLOURS_HEADING`/
`FRAME_COLOURS_HEADING_ID` are renamed to "Aspect"/a new id constant, this guard raises
`AssertionError` on every call, and the ONE registered check that calls it
(`_displays_page_height_is_recorded_at_both_phone_widths()`, line 13500, registered at line 13540)
fails outright — not silently, but it blocks the CFG-86 measurement entirely until fixed.
**Why it happens:** The instrument hard-codes a reference to the exact constant this phase renames.
**How to avoid:** Update `_display_page_height()`'s call site (line 2896) and the probe's
`headingId` argument to whatever new heading-id constant this phase introduces (e.g.
`config_page.ASPECT_HEADING_ID`), in the SAME commit that renames the heading — do not leave a
window where the instrument is broken.
**Warning signs:** Running the browser harness after only the Python/CSS/JS work lands, before
touching `test_browser_ux.py`, will show this exact check FAILing with "carries no Frame colours
heading" — that is expected and must be fixed, not worked around by reverting the heading rename.

### Pitfall 2: `_NO_JS_CONTROL_REGISTRY`'s one relevant row must be REMOVED, not repointed

**What goes wrong:** The UI-SPEC's No-JS/Control Contract section (Floor #4) says "re-point the
registry rows at the new markup rather than deleting and re-adding" — but the actual current
registry (`companion/test_companion_app.py:960-1021`) contains exactly ONE row related to this
phase's scope: `"the theme carousel's two pagers (D5)"` (line 1013-1021), registered specifically
because the pagers are "the only part of this control that cannot work without a script" (comment
at line 1002-1008). `_NO_JS_CONTROL_REGISTRY` exists specifically to prove that every element
carrying a `.js`-gated wrapper attribute (`layout.JS_GATE_CLASS`) also has a corresponding native
input reachable when the gate is absent — i.e. it registers **JS-required affordances only**. The
new accordion design has explicitly ZERO `.js`-gated elements (UI-SPEC's own text: "There is
nothing to gate behind a `.js` class here"). Blindly "repointing" this row at, say, the palette
radios would be actively wrong — the palette radios were never JS-gated and registering them here
claims a JS-optionality property that was never at risk for them.
**Why it happens:** The UI-SPEC's generic phrasing ("re-point... rather than delete") was written
about the no-JS-floor DISCIPLINE broadly (several different registries/checks across the codebase
use this pattern for genuinely-relocated controls), not about this ONE row specifically — and this
row's whole reason for existing (pagers needing JS) evaporates in the new design.
**How to avoid:** DELETE the `"the theme carousel's two pagers (D5)"` row from
`_NO_JS_CONTROL_REGISTRY` outright (the pagers themselves and `THEME_CAROUSEL_WRAPPER_ATTR` are
both retired). Do not add a replacement row unless the plan introduces some new element genuinely
gated behind `layout.JS_GATE_CLASS` — nothing in the UI-SPEC's contract requires one.
**Warning signs:** If a plan task tries to "repoint" this row at palette markup, the
`_no_js_control_violation()` machine (line 7083) will either fail immediately (no
`THEME_CAROUSEL_WRAPPER_ATTR`-equivalent attribute exists on the new markup, "its group builder
emits no element carrying %s at all") or, worse, pass vacuously if repointed at something
accidentally still carrying a leftover attribute — both are wrong outcomes; deletion is correct.

### Pitfall 3: The two cards' screen-group gates must merge to ONE condition, not stay as two

**What goes wrong:** `render()`'s current Display-scope branch (`companion/pages/config_page.py:
5672-5693`) builds `frame_colours_section_html` gated on `if screens.GROUP_THEME in groups` and
`display_calendar_card_html` gated separately on `if screens.GROUP_CALENDAR in groups`. Today
these are always BOTH true or BOTH false (the one registered screen type's `everyday_groups`
tuple lists both together — `companion/screens.py:86-87`), so a naive merge that just concatenates
the two existing conditionals' *output* into one card, while still computing that output under two
separate `if` checks, will work today but silently reintroduces the possibility of a half-rendered
merged card the moment a second screen type is registered with only one of the two groups.
**Why it happens:** The registry (`companion/screens.py`) is deliberately designed for future
multi-screen-type extension (its own module docstring says so) — a correct merge should collapse
to ONE gate expression for the ONE merged card, not silently rely on today's coincidental pairing.
**How to avoid:** Gate the new `_aspect_card_html()` call site on a single condition (e.g.
`screens.GROUP_THEME in groups` alone, since `calendar_group()`'s absorption means
`GROUP_CALENDAR`'s only remaining Display-page consumer becomes this merged card too) — and
document in a code comment, as this codebase's convention requires, exactly which registry
invariant justifies collapsing two checks into one. `handle_post()`'s own separate validation
gating (`companion/pages/config_page.py:6167`, `6535` — `screens.GROUP_CALENDAR not in
scope_groups(...)` / `screens.GROUP_THEME not in in_scope`) is a SEPARATE concern (which POSTed
fields are validated) and is NOT part of this phase's scope — do not touch those two lines unless
the plan's own investigation finds a reason to.

### Pitfall 4: `theme-preview.js`'s hover/focus-follow behaviour has no existing precedent to copy

**What goes wrong:** The UI-SPEC's Preview Follow-Behaviour Contract says the preview must follow
"hover/focus the way it already follows scroll... re-keyed" — but re-reading the actual current
script (`companion/static/theme-preview.js`, full file re-read this session) shows the OLD
behaviour was scroll-position tracking (`makeScrollPreviewTracker()`, lines 490-543) and
click-to-select (the delegated `change` listener, lines 328-355) — **there is no existing
hover/focus-follow code to "re-key"**; it must be newly written. The old scroll-tracker used a
`settle()` function gated on `strip.scrollLeft !== lastScrollLeft` specifically because scroll
events fire continuously during a drag; a hover/focus tracker has a completely different event
shape (`mouseover`/`focusin` on individual chip labels, with a `mouseout`/`focusout` revert path
the old code never needed at all, since scrolling away from a chip has no equivalent "revert").
**Why it happens:** The UI-SPEC is a design CONTRACT (what the behaviour must look like to a
user), not an implementation plan — it correctly identifies the OLD mechanism as a precedent for
"preview shows something other than the saved/selected value, non-destructively," but the actual
DOM event wiring is genuinely new code, not a relocation.
**How to avoid:** Budget real design/implementation time for this specific piece. Suggested shape
(not mandated, but consistent with the file's existing conventions — ES5-only, delegated
listeners, no timers, reuses `applyPreviewSrc()` as the one write-sink): one delegated
`mouseover`/`focusin` listener on the card root reading `data-preview-src` off the hovered/focused
chip's `<label>` (mirroring the existing delegated `change` listener's chip-resolution logic at
lines 340-354), calling `applyPreviewSrc()`; a matching `mouseout`/`focusout` listener that calls
`applyPreviewSrc()` again with the OPEN row's own currently-checked chip's src (reusing
`checkedChipSrc()`, lines 234-250, re-scoped from "panel" to "currently-open `<details>`"). Delete
`panelForUsage()`/`departuresPanel()`/`effectiveSrcForUsage()`/`showUsage()`/`checkedUsage()`/
`COLLAPSED_PANEL_CLASS` and the entire pager/scroll-tracker block (lines 214-322 conceptually
replaced, lines 357-566 deleted outright) as part of the same rewrite — do not leave dead functions
behind that reference a `colour_usage` field or `.frame-colours__usage-panel*` class that no
longer exists in the rendered markup.

### Pitfall 5: `theme-preview.js`'s top-level selector guard must be updated or the whole script no-ops

**What goes wrong:** Line 87: `var card = document.querySelector(".frame-colours"); if (!card) {
return; }`. Once `.frame-colours` is renamed to `.aspect-card` (or whatever class the merged card
uses) in the Python/CSS work, this guard fails silently — the ENTIRE script becomes a no-op on
every page (no crossfade, no hover-follow, nothing), with no error, no console warning, and no
test failure unless a check specifically probes for the preview's dynamic behaviour.
**Why it happens:** This is the single load-bearing selector the whole file's `(function(){...})()`
IIFE is gated behind; it is easy to update every OTHER `.frame-colours`-scoped query in the file
while missing this one top-level guard since it doesn't visually resemble the rest of the
carousel-specific code being deleted.
**How to avoid:** Update this line in the SAME commit as the Python/CSS rename, and verify via the
existing crossfade check (`_the_live_preview_crossfade_settles_correct_through_its_own_listener()`,
`companion/test_browser_ux.py:5304`) and the chip-selection check
(`_selecting_a_theme_chip_answers_and_moves_no_layout_box()`, line 5012) both still pass — both
exercise this script's live behaviour end-to-end in a real browser and will catch a silently
no-op'd script immediately.

---

## Code Examples

### Existing crossfade mechanism to KEEP unchanged (theme-preview.js:98-212)

```javascript
// Source: companion/static/theme-preview.js — KEEP, re-scope only the top-level
// `.frame-colours` query (line 87) and any selector that assumes `.theme-chip`
// (chip selection listener, lines 328-355) needs to recognise the new, smaller
// `.palette-chip` markup instead/in addition.
var FADE_CLASS = "theme-live-preview__image--swapping";
var pendingSrc = preview.getAttribute("src");
function applyPreviewSrc(src) { /* ... unchanged crossfade logic ... */ }
```

### Existing chip-resolution idiom to REUSE for the new hover/focus listener (theme-preview.js:340-354)

```javascript
// Source: companion/static/theme-preview.js:340-354 — the existing pattern for
// "resolve data-preview-src off the event target's ancestor label" that the new
// hover/focus listener should mirror, not reinvent.
var chip = input.parentNode;
if (!chip || !chip.getAttribute) { return; }
var isThemeChip = chip.className && chip.className.indexOf("theme-chip") !== -1;
var src = chip.getAttribute("data-preview-src");
```

---

## State of the Art

| Old Approach | Current Approach (this phase) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Radiogroup (`colour_usage`) + JS class-toggle for row visibility | Native `<details name="...">` grouped accordion | This phase | Deletes an entire JS mechanism (`showUsage`, `panelForUsage`, `COLLAPSED_PANEL_CLASS`) with zero behavioural loss and a genuine no-JS improvement (today's no-JS floor already shows all 4 panels stacked; the new one does too, natively, without a Python-side "no hidden attribute" discipline to maintain) |
| Scroll-snap strip of 18 chips + 2 pagers + dot row + "see all" disclosure | Wrapping CSS grid of 18 smaller palette-chips, always fully visible | This phase | Removes ~230 lines of carousel-specific JS and ~6 CSS rule-blocks; the CFG-86 page-height reduction this phase is measured against depends primarily on this change (no more `+overflow-x` strip forcing every chip to stay a fixed compact width in a nowrap row) |
| `.theme-chip` (320×120 photo preview) per palette entry | `.palette-chip` (new, smaller, CSS-drawn shape, no `<img>`) | This phase | Eliminates 18 `theme-preview` route round-trips per open row that the photo-chip approach would have required; the UI-SPEC explicitly rejected per-chip photos for this reason |

**Deprecated/outdated in this codebase (as of this phase):** `.theme-carousel*`,
`.theme-chip-grid--strip`, `THEME_CAROUSEL_STRIP_ID*`, `THEME_CAROUSEL_WRAPPER_ATTR`,
`_theme_carousel_html()`, `_frame_colours_row_html()`, the `colour_usage` form field concept.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The merged Aspect card's screen-group gate should collapse to checking `screens.GROUP_THEME in groups` alone (dropping the separate `GROUP_CALENDAR` check for RENDERING purposes only, leaving `handle_post()`'s validation gates on both untouched). | Common Pitfalls (Pitfall 3) | If wrong, a future second screen type that supports theme-only or calendar-only could render a broken/half-populated merged card. Low near-term risk (only one screen type exists today, both groups always co-present), but the plan should state this collapse explicitly with a comment rather than leaving it implicit, so a future reader can find and revisit the assumption. |
| A2 | The `theme-preview.js` hover/focus-follow interaction (mouseover/focusin to preview, mouseout/focusout to revert to the open row's checked selection) is the right event shape — no existing code in this repo implements this exact pattern to copy from. | Common Pitfalls (Pitfall 4) | If the actual UX intent differs (e.g., hover should persist until a DIFFERENT chip is hovered, with no revert-on-mouseout at all, closer to how `:hover`-only CSS previews work elsewhere in the design system), the plan's Task for this piece should verify against the live sketch's behaviour (`.planning/sketches/006-.../index.html`) before finalizing, since the sketch is throwaway HTML and was not re-read line-by-line in this research pass for its own JS (if any). |

**If this table is empty:** N/A — see above.

---

## Open Questions

1. **Does the approved sketch (`006-aspect-tile-accordion-vs-segments`) contain any live
   hover/focus-preview JS the plan could crib from directly?**
   - What we know: The UI-SPEC cites the sketch's markup (lines 240-329) as ground truth for
     structure, and explicitly flags one piece of the sketch's markup (the leading-option button)
     as NOT shippable as-is.
   - What's unclear: Whether the sketch's own throwaway HTML includes any interactive JS for the
     hover-preview behaviour that a planner could inspect for the intended event shape, or whether
     the sketch was static-only (structure/CSS proof, no live preview wiring).
   - Recommendation: The planner should have the executing task open
     `.planning/sketches/006-aspect-tile-accordion-vs-segments/index.html` directly and check for
     a `<script>` block before writing the hover/focus listener from scratch — this research did
     not re-read that file (out of the specified `files_to_read` scope for this pass).

2. **What does the CFG-86 baseline number actually read RIGHT NOW, pre-Phase-30?**
   - What we know: The instrument (`_display_page_height()`) exists, is correctly guarded, and
     ROADMAP cites three historical numbers (3,743px/3,524px/3,556px) from PRIOR phases — none of
     which is a same-instrument, same-moment "before" reading for THIS phase, and one in-code
     comment (`test_browser_ux.py:13519-13524`) records a DIFFERENT historical number (4,276px at
     390px) for an even earlier baseline, illustrating how these numbers drift phase to phase.
   - What's unclear: The actual figure today, since Playwright/Chromium are not installed in this
     worktree (see Environment Availability) and this research did not install them to avoid a
     heavyweight, possibly network-dependent side effect during a research pass.
   - Recommendation: The plan's first task (or a dedicated Wave 0 step) must install
     Playwright+Chromium and run `_displays_page_height_is_recorded_at_both_phone_widths()` (or an
     equivalent standalone script driving `_display_page_height()`) BEFORE any markup changes, to
     get a genuine same-instrument "before" number — do not reuse any ROADMAP-cited historical
     figure as the "before" baseline for CFG-86's delta report.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Playwright (Python package) | `companion/test_browser_ux.py` — the CFG-86 measurement instrument and every no-JS-blocked browser check this phase's verification depends on | ✗ (confirmed: `python3 -c "import playwright"` raises `ModuleNotFoundError` in both the ambient `python3` and `server/.venv`) | — | `pip install -r server/requirements-dev.txt` |
| Chromium binary (Playwright-managed) | Same as above | ✗ (cannot check independently — package itself is absent) | — | `python -m playwright install chromium`, run after the pip install above |

**Missing dependencies with no fallback:** None — both gaps have a documented, one-command fix
already named in the harness's own skip-gate messages (`companion/test_browser_ux.py:22-29`). The
harness itself is designed to SKIP (exit 0) rather than fail red when these are absent, so the
regular test suite (`scripts/run_all_tests.py`) will not currently catch CFG-86 regressions or
no-JS regressions in this environment until the plan's Wave 0 installs both.

**Missing dependencies with fallback:** Both items above — install commands are standard and
already documented in-repo; no alternative measurement method exists or should be invented (the
UI-SPEC and CFG-86 both name this specific instrument as "the registered instrument").

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Custom `check(name, fn)` harnesses (no pytest) — `companion/test_companion_app.py` (string/markup-level), `companion/test_browser_ux.py` (Playwright-driven, real browser) |
| Config file | none — each file is a standalone script with a module-level `EXPECTED_CHECK_COUNT` pin and a `main()` returning 0/1 |
| Quick run command | `python companion/test_companion_app.py` (fast, no browser) |
| Full suite command | `python scripts/run_all_tests.py` (runs every harness including `test_browser_ux.py`, which self-skips if Playwright/Chromium are absent — see Environment Availability) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-85 | No-JS control contract holds for every relocated/new control | string-level (`_NO_JS_CONTROL_REGISTRY` machine) | `python companion/test_companion_app.py` | ✅ (existing check at `test_companion_app.py:7172`, registry to be edited per Pitfall 2) |
| CFG-85 | Real browser round trip: palette selection saves with scripts blocked, in both languages, at 360px | browser (Playwright) | `python companion/test_browser_ux.py` | ⚠️ Existing carousel-specific checks (`_the_theme_still_saves_with_scripts_blocked_through_the_carousel` etc., lines 13554-13935) must be REWRITTEN for the accordion shape — the behaviour they prove (scripts-blocked save) still needs proving, but through `<details open>` + palette grid markup, not the carousel's strip/pager markup |
| CFG-85 | Every retired CSS rule has no surviving consumer | static grep audit | manual `grep -rn "<selector>" companion/` per retired selector, or a small ad-hoc script | ❌ No existing automated check does this generically — the plan should either do it as a documented manual audit step per rule, or (better, matching this codebase's own convention of preferring machine-checked claims) write a small one-off verification script for the phase's SUMMARY, not a permanent new harness |
| CFG-86 | Page height at 390px measured before/after, delta reported | browser (Playwright), instrumented measurement | `python companion/test_browser_ux.py` (via `_displays_page_height_is_recorded_at_both_phone_widths`) | ✅ Existing instrument at `test_browser_ux.py:2870`, guard needs updating per Pitfall 1 |

### Sampling Rate
- **Per task commit:** `python companion/test_companion_app.py` (fast — no browser needed for the
  Python/CSS structural work)
- **Per wave merge:** `python scripts/run_all_tests.py` (full suite, once Playwright/Chromium are
  installed per Environment Availability)
- **Phase gate:** Full suite green, `EXPECTED_CHECK_COUNT` re-derived by RUNNING both harness files
  (not hand-incremented) after every carousel-specific check is retired and every accordion-shaped
  replacement check is added — matching ROADMAP's own "Carried discipline" note for this phase.

### Wave 0 Gaps
- [ ] Install Playwright + Chromium in this worktree's environment (`pip install -r
      server/requirements-dev.txt && python -m playwright install chromium`) — currently absent,
      blocks both the CFG-86 measurement and every no-JS browser-level proof this phase needs.
- [ ] Run `_displays_page_height_is_recorded_at_both_phone_widths()` (or an equivalent standalone
      invocation of `_display_page_height()`) against the CURRENT, unmodified tree to capture a
      genuine same-instrument "before" number for CFG-86, before any markup changes land (see Open
      Question 2 — no historical ROADMAP-cited number is a valid substitute).

*(No test-file-creation gaps: both harness files already exist and already cover this page; the
gap is environment setup and check-rewriting, not missing infrastructure.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Unchanged — this phase touches only the already-authenticated `/display` settings page; no auth surface is added or modified |
| V3 Session Management | no | Unchanged |
| V4 Access Control | no | Unchanged — same session-gated route, same handler |
| V5 Input Validation | yes (unchanged, relocated only) | `server/device_config.py`'s existing `THEME_IDS` membership checks for `theme`/`theme_arriving`/`calendar_theme_id`, and `colour_rules`'s existing rule-kind/value validation — this phase changes WHERE these fields render, never how they're validated server-side. No new field, no new validation logic is introduced. |
| V6 Cryptography | no | Unchanged — the calendar feed URL remains write-only, masked-display-only, exactly as today; no new secret handling |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Reflected/stored XSS via theme name, row label, or masked calendar URL | Tampering/Information Disclosure | Unchanged — `escape_html()` is already applied at every interpolation site in `_frame_colours_card_html()`/`calendar_group()`; the merged builder must preserve this discipline (100% of the existing escape_html() call sites relocate verbatim, no new raw string interpolation should be introduced for the new palette-chip/accordion markup) |
| CSRF on the theme/calendar POST | Tampering | Unchanged — this app's existing session-cookie + same-origin POST model is untouched; this phase adds no new POST endpoint |
| CSP regression (new inline script, new script-src source) | Tampering | Explicitly forbidden by the UI-SPEC's own Floor #5/#6 (CSP untouched, no new script file) — `theme-preview.js` is edited in place, served from the same already-allowlisted route |

---

## Sources

### Primary (HIGH confidence — read directly from the current tree, 2026-09-22)
- `companion/pages/config_page.py` (6,715 lines) — `_frame_colours_card_html()` (2135-2360),
  `calendar_group()` (4459-4734), `_theme_chip_grid_html()` (1609+), `_theme_carousel_html()`
  (1782+), `_same_as_departures_chip_html()` (2044-2080), `_frame_colours_row_html()`
  (2083-2113), `_palette_hex()` (1598-1606), `ASPECT_CAPTION_EXEMPTIONS` (1342-1347), `render()`'s
  Display-scope branch (5640-5696), constants block (227-334)
- `companion/static/style.css` (10,704 lines) — full `.frame-colours*` block (10072-10233), full
  `.theme-carousel*`/`.theme-chip-grid--strip` block (10244-10430), `.theme-chip` base block
  (3299-3830)
- `companion/static/theme-preview.js` (572 lines) — read in full
- `companion/test_browser_ux.py` (16,361 lines) — `_display_page_height()`/probe (2858-2925),
  `_displays_page_height_is_recorded_at_both_phone_widths()` (13500-13550), carousel-specific
  check function names (13554-15226 region)
- `companion/test_companion_app.py` (12,034 lines) — `_NO_JS_CONTROL_REGISTRY` (960-1055+),
  `_no_js_control_violation()`/`_no_js_control_contract_holds_for_every_registered_control()`
  (7083-7234)
- `server/device_config.py` (1,143 lines) — `THEMES` registry imported and inspected directly
  (18 themes, band-theme facts, `normalise_calendar_theme_id()` at 526, validation at 867-868)
- `companion/screens.py` (140 lines) — read in full; `GROUP_THEME`/`GROUP_CALENDAR` registration
- `companion/i18n_fr/display.py` (spot-checked 95-112) — French copy constants cross-checked
  against UI-SPEC's Copywriting Contract
- `.planning/phases/30-.../30-UI-SPEC.md` (387 lines) — read in full, this phase's structural/copy
  contract
- `.planning/ROADMAP.md` Phase 30 section (1458-1493) — read in full
- `.planning/STATE.md` — CFG-85/CFG-86 requirement text and coverage-ledger rows (grepped and
  read in context)
- `.planning/REQUIREMENTS.md` — CFG-85/CFG-86 full text confirmed present

### Secondary (MEDIUM confidence)
- `git log --oneline -- companion/pages/config_page.py` — confirmed Phase 29's two merged PRs
  (`5961ab7`, `f7aed16`) as the most recent touches before this phase, consistent with what the
  live file already shows (no undiscovered Phase 29 structural drift beyond the caption-exemption
  mechanism already re-read directly)

### Tertiary (LOW confidence)
- None used — every load-bearing claim in this document was verified against the live tree or the
  developer-approved UI-SPEC directly.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new technology; every citation re-verified in the live tree
- Architecture: HIGH — every builder/constant/CSS-class citation re-read directly, not carried
  from ROADMAP's Phase-28-era text; the one genuinely-new piece (hover/focus preview JS) is
  explicitly flagged as new design work rather than presented as a known pattern
- Pitfalls: HIGH — all five pitfalls are derived from direct code contradictions found this
  session (stale constant references, a registry row whose precondition no longer holds, a
  gate-merge edge case), not speculative

**Research date:** 2026-09-22
**Valid until:** Should be treated as valid only for planning THIS phase, executed promptly — any
further phase touching Display before Phase 30 executes would require re-verification (matching
the exact staleness pattern ROADMAP's own Phase-28-vs-Phase-29 drift already demonstrated once).
