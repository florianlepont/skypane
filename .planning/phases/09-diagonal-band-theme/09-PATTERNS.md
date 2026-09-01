# Phase 9: Diagonal band theme - Pattern Map

**Mapped:** 2026-09-01
**Files analyzed:** 3 (all modified, no new files)
**Analogs found:** 3 / 3 (all analogs are the file's own current production code, since this phase ports validated spike code into the same production module)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `server/plane/render.py` (new `draw_diagonal_band()` + edits to `draw_top_labels()`/`draw_main_text_block()`/`draw_previous_text_block()`/`_build_active_canvas()`) | render/drawing function (transform: flight+theme data -> "P"-mode canvas pixels) | transform | itself — existing `draw_top_labels()`, `draw_main_text_block()`, `draw_previous_text_block()`, `_build_active_canvas()` in the same file | exact (same file, same functions being extended, not replaced) |
| `server/device_config.py` (new `THEMES["band-*"]` entries, `band_id` field if needed) | config/registry (CRUD-like: static lookup table) | CRUD (read-only lookup) | itself — existing `THEMES` dict entries (`"blue_light"`, `"black"`, etc.) | exact |
| `server/plane/dither.py` (likely unchanged — `dithered_state_background()` reused as-is for the dithered band fill) | utility (image transform) | transform | itself — `dithered_state_background()` already does exactly what the band's "light" colours need | exact (no new function anticipated; flag as "verify during planning" below) |

No new files are created. This phase is a pure port-and-integrate of `.planning/spikes/003-diagonal-band-theme/explore_full_composition.py`'s monkeypatches into the three permanent functions they patched.

## Pattern Assignments

### `server/plane/render.py` — new `draw_diagonal_band(canvas, band_idx, dithered=False)`

**Analog (spike source, to port verbatim with prod names):** `.planning/spikes/003-diagonal-band-theme/explore_full_composition.py` lines 66-102 (`draw_reference_band()` + the `BAND_*_FRAC` constants + `make_patched_new_canvas()`/`_TRUE_ORIG_NEW_CANVAS` monkeypatch scaffolding).

**Final confirmed geometry (round 15, spike README "Results" — use these numbers, not any earlier round's):**
```python
BAND_SHIFT_FRAC = 0.0
BAND_TOP_LEFT_FRAC = 0.5818 + BAND_SHIFT_FRAC
BAND_TOP_RIGHT_FRAC = 0.8523 + BAND_SHIFT_FRAC
BAND_BOT_LEFT_FRAC = max(0.0, 0.0742 + BAND_SHIFT_FRAC)
BAND_BOT_RIGHT_FRAC = 0.4772 + BAND_SHIFT_FRAC


def draw_diagonal_band(canvas, band_idx, dithered=False):
    w, h = canvas.size
    poly = [
        (BAND_TOP_LEFT_FRAC * w, 0), (BAND_TOP_RIGHT_FRAC * w, 0),
        (BAND_BOT_RIGHT_FRAC * w, h), (BAND_BOT_LEFT_FRAC * w, h),
    ]
    if dithered:
        band_fill = dither.dithered_state_background(band_idx)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        canvas.paste(band_fill, (0, 0), mask)
    else:
        ImageDraw.Draw(canvas).polygon(poly, fill=band_idx)
```

**Landing spot:** call this directly inside `_build_active_canvas()` (render.py lines 1447-1568), immediately after `canvas = dither.dithered_state_background(bg_idx) if theme_dithered else pf.new_canvas(bg_idx)` (line 1488) and before `draw_top_labels(...)` (line 1499) — the spike's monkeypatch of `pf.new_canvas` exists only because the spike could not edit `render.py`; production has no such constraint, so this becomes a direct function call, not a monkeypatch. Gate the call on the active theme being one of the new band themes (see device_config.py section below) — every existing theme must render byte-identical to today, so `draw_diagonal_band()` must only ever be invoked when `theme_id` is one of the 5 new band themes.

**`dithered` param reuses the existing helper verbatim** — `dither.dithered_state_background(band_idx)` (`server/plane/dither.py` lines 54-96) is called with no changes; this is the same function `_build_active_canvas()` already calls for `theme_dithered` themes, just applied to a polygon-masked region instead of the full canvas via the `Image.paste(..., mask)` idiom.

**5 band colours (from confirmed spike candidates, round 15):** `blue-dithered` (`pf.IDX_BLUE`, dithered=True), `blue-flat` (`pf.IDX_BLUE`, dithered=False), `green-dithered` (`pf.IDX_GREEN`, dithered=True), `red-flat` (`pf.IDX_RED`, dithered=False), `black-flat` (`pf.IDX_BLACK`, dithered=False).

---

### `server/plane/render.py` — `draw_top_labels()` (existing function, edit in place)

**Current production (analog):** `server/plane/render.py` lines 720-772 — draws `STATE_LABEL_TEXT[state]` top-left and `runway_tag_text(runway_id)` top-right as two separate tracked runs via `draw_tracked_text()`/`_tracked_text_width()`/`_tracked_text_bbox()`, both already using `LABEL_TRACKING_PX`.

**Spike replacement to port (round 11, final):** `.planning/spikes/003-diagonal-band-theme/explore_full_composition.py` lines 105-137 (`_MERGED_LABEL_DIRECTION` dict + `patched_draw_top_labels()`):
```python
_MERGED_LABEL_DIRECTION = {
    render.runway_config.STATE_DEPARTING: "FROM",
    render.runway_config.STATE_ARRIVING: "TO",
}

def patched_draw_top_labels(canvas, state, ink_idx, bg_idx, weight, runway_id=None):
    ...
    direction = _MERGED_LABEL_DIRECTION[state]
    full_tag = render.runway_tag_text(runway_id)
    airport_code, _sep, runway_part = full_tag.partition(" · ")

    merged_text = "%s %s %s" % (render.STATE_LABEL_TEXT[state], direction, airport_code)
    render.draw_tracked_text(draw, (render.MARGIN, render.MARGIN), merged_text, label_font, ink_idx, render.LABEL_TRACKING_PX)

    tag_w = render._tracked_text_width(tag_font, runway_part, render.LABEL_TRACKING_PX)
    tag_x = render.WIDTH - render.MARGIN - tag_w
    render.draw_tracked_text(draw, (tag_x, render.MARGIN), runway_part, tag_font, ink_idx, render.LABEL_TRACKING_PX)
```

**Important scope note:** the spike's docstring/README trail shows this merged-label idea was explored (round 7) and explicitly **reverted** (round 9-11: "un-merge the top labels... keep 'ORY' merged into the top-left label... but keep a SHORTER separate tag on the right — 'RWY 3' alone"). The *actual* final, developer-confirmed behaviour (round 11, carried through round 15) is the **split tag**, not the merged whole tag. Port `full_tag.partition(" · ")` (splitting airport code left, "RWY 3" right) as **two separate `draw_tracked_text()` calls**, not one merged string — this is a materially different function body than `patched_draw_top_labels()`'s naive single-string version shown above. Since the spike script's actual function body was never updated after round 11 (the README documents the round-11 fix conceptually, `explore_full_composition.py`'s `patched_draw_top_labels()` on lines 122-137 already reflects the split, not the merge — re-read: line 130 does `airport_code, _sep, runway_part = full_tag.partition(" · ")`, and draws `merged_text` = state label + direction + airport code on the LEFT, `runway_part` ("RWY 3") on the RIGHT as its own tracked run). So the code excerpt above **is already the round-11 split-tag version** — "merged_text" is a slightly misleading variable name (it merges the state label + airport code, not the whole tag) but the function is correct. Use it as-is; add `_assert_within_canvas()` calls on both bboxes matching the existing production function's guard-rail discipline (lines 764-771), which the spike version omits.

**Note:** this changes `draw_top_labels()`'s copy for every band theme's state label (e.g. "DEPARTING FROM ORY" instead of "DEPARTING"). Confirm during planning whether this new copy applies ONLY to band themes or all themes — the spike ran it only against band-theme candidates, and the ROADMAP goal text says the split top-label tag is part of "this new dedicated theme," implying band-theme-only. If theme-scoped, `draw_top_labels()` needs a branch (or a caller-level dispatch) keyed on `theme_id`/`is_band_theme`, not a blanket rewrite of the function for all 11 existing themes.

---

### `server/plane/render.py` — `draw_main_text_block()` (existing function, edit in place / theme-conditional)

**Current production (analog):** `server/plane/render.py` lines 1224-1280 — two centred lines (`_flight_line1_text()`, `_flight_line2_text()`), anchored `MAIN_TEXT_GAP_PX` below `main_placement.content[3]`, `anchor="ma"`, fonts via `_role_fit_text_size()`.

**Spike replacement to port (round 15, final):** `.planning/spikes/003-diagonal-band-theme/explore_full_composition.py` lines 140-309 — the whole three-tier hierarchy block:
- `FLIGHT_NUMBER_FONT = (render.PT_SERIF_BOLD, 56, 700)`, `ROUTE_LINE_FONT = (render.PT_SERIF_REGULAR, 22, 400)`, `AIRLINE_LINE_FONT = (render.PT_SERIF_REGULAR, 20, 400)`, `DASH_W = 24`, `DASH_GAP = 10` (lines 152-156).
- `_band_center_x(canvas_y, w)` (lines 200-211) — trapezoid centreline interpolation, reused for text centring.
- `patched_draw_main_text_block()` (lines 223-309) — tier-split logic reusing `render._flight_line1_text()`/`_flight_line2_text()` **verbatim** (never re-derive content), ink follows the band's own contrast colour (`IDX_WHITE` when `_CURRENT_BAND_IDX == pf.IDX_BLACK`, else `ink_idx` unchanged) — this is round 13's fix, mandatory to port or `black-flat` renders fully invisible text.
- **Critical bug fix to preserve when porting:** `center_x` must be computed **once**, at the block's top (`y = main_placement.content[3] + MAIN_TEXT_GAP_PX`), and reused for every line — round 12 introduced a per-line recompute bug (staggered columns since the band is a trapezoid whose centreline shifts across the block's height), fixed in round 15. Port the fixed version (lines 283-284: `y = ...`, `center_x = _band_center_x(y, render.WIDTH)`, computed once before the `if number_text:` / `if tracked_text:` blocks).
- Position/anchor: **unchanged from real production** — `main_placement.content[3] + MAIN_TEXT_GAP_PX`, i.e. below the illustration (round 8+11's final call, NOT round 5's `_fuselage_visual_top_y()` above-illustration anchor, which was a round-2/5-9 workaround since superseded and should NOT be ported).

**Vertical anchor: do NOT port `_fuselage_visual_top_y()`.** The README's Results section confirms round 11 (the final, un-merged/split-tag geometry) needs no above-illustration anchor — text sits below the illustration using the real, unmodified `draw_main_text_block()` anchor expression. Only the horizontal centring (`_band_center_x`) and the tier-split/ink-swap logic are new; the vertical anchor line is identical to what's already in production (line 1263: `top_y = main_placement.content[3] + MAIN_TEXT_GAP_PX`).

**This function's new behaviour is band-theme-scoped**, not universal — every other theme should keep exactly today's centred two-line block. Plan for a conditional (e.g. `if device_config.theme_is_band(theme_id): <new logic> else: <existing logic>`) rather than replacing the function body outright, since 11 non-band themes must render byte-identical to today.

---

### `server/plane/render.py` — `draw_previous_text_block()` (existing function, edit in place / theme-conditional)

**Current production (analog):** `server/plane/render.py` lines 1283-1350 — two right-aligned lines, anchored below `prev_placement.content[3]`, `anchor="ra"`.

**Spike replacement to port (round 6, unchanged through round 15):** `.planning/spikes/003-diagonal-band-theme/explore_full_composition.py` lines 312-377 (`PREV_NUMBER_FONT = (render.PT_SERIF_BOLD, 32, 700)`, `PREV_ROUTE_FONT`, `PREV_AIRLINE_FONT`, `PREV_DASH_W/GAP`, `patched_draw_previous_text_block()`). Mirrors the main card's tier-split logic exactly but right-aligned, ~57% scale of the main card's fonts, **position unchanged** from today's production anchor (`prev_placement.content[3] + PREVIOUS_TEXT_GAP_PX`, right-aligned at `prev_placement.content[2] - PREVIOUS_TEXT_LEFT_OFFSET_PX`) — confirmed clear of the band at every round from 6 onward (band's rightmost extent ~45% width vs. this card's ~89% width text).

**No ink-swap needed here** — the spike never applies `_CURRENT_BAND_IDX` logic to the previous card, because the band never reaches this card's position; production port can therefore skip the black-band special case for this function specifically (verify during planning that this is actually true given production's real band geometry, not just the spike's).

---

### `server/device_config.py` — `THEMES` dict (existing registry, add entries)

**Analog:** `server/device_config.py` lines 104-193 — existing `THEMES` entries, e.g.:
```python
"blue_light": {
    "departing_index": IDX_BLUE,
    "arriving_index": IDX_BLUE,
    "ink_index": IDX_WHITE,
    "label": "Blue Light",
    "dithered": True,
    "weight": "bold",
},
```

**New entries needed:** one dedicated band theme per the ROADMAP goal ("A new dedicated theme... adding a diagonal decorative trapezoid band... in 5 colours"). Two possible shapes to resolve during planning:
1. **One theme id** (e.g. `"band"`) whose band colour is a NEW dimension the existing `THEMES` shape doesn't have (needs a `band_index`/`band_dithered` field pair, since the band colour is independent of the base White background this phase's spike always used) — the base canvas stays White (`departing_index`/`arriving_index` = `IDX_WHITE`) in every candidate; only the band's colour varies. This is closer to what the spike actually did (`new_canvas(bg_index)` always called with White in `TEST_FLIGHT`/`build_canvas(..., theme_id="white")` — band colour was a monkeypatch parameter, never a `THEMES` field at all).
2. **Five separate theme ids** (`"band_blue"`, `"band_blue_light"`, `"band_green_light"`, `"band_red"`, `"band_black"`), each a full `THEMES` entry with `departing_index`/`arriving_index` = `IDX_WHITE` (base stays White per the spike) plus new `band_index`/`band_dithered` fields, matching the existing one-entry-per-colour-variant convention already used for `yellow`/`yellow_light`, `red`/`red_light`, etc.

**Recommendation for planner:** shape 2 matches this registry's established convention (each selectable visual variant is its own dict entry, `THEME_IDS = tuple(THEMES)` auto-derives the CFG-01 picker list) more closely than inventing a nested "band colour picker within a theme." Needs `band_index` (an `IDX_*` constant) and `band_dithered` (bool) fields per entry, read by the new `draw_diagonal_band()` call site in `_build_active_canvas()`. `ink_index` for the 4 non-black band colours stays `IDX_BLACK` (matches White base + round-13 spike finding that blue/green/red keep black text legible); the black band's text ink swap (`IDX_WHITE`) is NOT a per-theme `ink_index` change — it must be a per-band-region ink override inside `draw_main_text_block()`/`draw_previous_text_block()` (see round 13's `_CURRENT_BAND_IDX` pattern above), since the base canvas ink stays Black everywhere else on the panel (e.g. top labels, safe outside the band).

**Follow the module's explicit registry-extension convention** stated in its own header comment (lines 20-24: "Adding a theme... append one entry to THEMES keyed by [id]... every presentation accessor below derive[s] from THEMES itself") and its discipline of never writing a bare palette integer (always reference `panel_format.IDX_*`).

## Shared Patterns

### Band-theme detection / dispatch
No existing helper does this (`device_config.py` has `theme_dithered()`/`theme_weight()`/`theme_background_index()`/`theme_ink_index()` accessors, lines 350-389, but nothing for "is this theme a band theme" or "what's this theme's band colour"). Plan should add a `theme_band_index(theme_id)` / `theme_band_dithered(theme_id)` accessor pair mirroring the existing `theme_dithered()`/`theme_weight()` pattern (`server/device_config.py` lines 374-389):
```python
def theme_dithered(theme_id):
    return THEMES[theme_id]["dithered"]

def theme_weight(theme_id):
    return THEMES[theme_id]["weight"]
```
Apply to all render.py, `draw_top_labels()`, `draw_main_text_block()`, `draw_previous_text_block()` call sites needing to know "is this a band theme, and if so what colour/dithered."

### Never re-derive flight-identifier content
Every text-block patch in the spike (`patched_draw_main_text_block()`, `patched_draw_previous_text_block()`) calls the real, unmodified `render._flight_line1_text()`/`render._flight_line2_text()` and only restyles/splits their output — this is round 4's explicit fix for a real regression (inventing a `"{origin} — {destination}"` line that doesn't exist in production's four-tier content ladder). Any production port MUST preserve this discipline: call the existing private helpers verbatim, never fork new content logic.

### Palette guard rail — no change needed
`_assert_legal_palette()` (`server/plane/render.py` lines 1417-1445) already validates "every index anywhere on the panel is one of the 6 legal Spectra 6 indices, and bg_idx is the most common index" — this passed for all 5 band candidates in the spike unmodified, called directly (not reimplemented). No changes needed to this function; it already covers the new band region since the band is drawn with legal `IDX_*` values before the dominance check runs.

### On-glass verification requirement (D-13 precedent)
Per this project's established discipline (referenced throughout the spike README and `render.py`'s own module docstring, e.g. D-13's "no info drops silently" and the standing "every visual/typography change needs a real on-glass check before being considered final"), this phase's plan set must include a blocking on-glass verification plan, matching every prior visual-theme phase (Phase 3's 03-04, Phase 7, Phase 8's plan 08-06).

## No Analog Found

None — every file this phase touches already exists in production and has a direct, in-file analog (the function itself, pre-band-theme). No new files or genuinely novel roles are introduced.

## Metadata

**Analog search scope:** `server/plane/render.py`, `server/device_config.py`, `server/plane/dither.py`, `server/panel_format.py`, `.planning/spikes/003-diagonal-band-theme/`
**Files scanned:** 4 production files (read in full or targeted ranges) + 1 spike script (read in full) + spike README (read in full)
**Pattern extraction date:** 2026-09-01
