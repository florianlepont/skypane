---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 05
subsystem: companion-ui
tags: [svg, drawing, area-chart, battery, threshold, themes, no-js, css, i18n]

requires:
  - phase: 24-01
    provides: "companion/battery.py's LOW_BATTERY_DISPLAY_MV / LOW_BATTERY_DISPLAY_PERCENT — the COMPANION's charting threshold, derived from the same ratio battery_percent() returns"
  - phase: 24-01
    provides: "companion/draw.py's two canvas schemes (percent_canvas / unit_canvas), read and deliberately not used here — see the geometry experiment"
  - phase: 24-02
    provides: "companion/test_browser_ux.py's _set_ui_theme(), _computed_paint() and _assert_no_page_overflow()"
  - phase: 24-04
    provides: "the precedent that a drawing and the number printed beside it must come from ONE value, and that a class's CSS omissions can be mechanism"
  - phase: 06.5/260902-ep7
    provides: "battery_sparkline_svg()'s no-viewBox percentage scheme, its wrapper grid, its n-1 <line> segments and its roving-tabindex keyboard path"
provides:
  - "health_page.sparkline_point_y() — the chart's y placement, promoted out of a closure so marks, the area's baseline, the threshold and the harness all place a level with one function"
  - "the area under the trend line: SPARKLINE_AREA_LAYER_CLASS (a nested viewBox'd <svg>) + SPARKLINE_AREA_CLASS (the polygon)"
  - "the marked current reading: SPARKLINE_MARK_CLASS, _SPARKLINE_MARK_RADIUS_PX, and the density rule's written-down exception"
  - "the drawn low-battery threshold: SPARKLINE_THRESHOLD_CLASS, plus its legend (SPARKLINE_LEGEND_ROW_CLASS / SPARKLINE_LEGEND_CLASS / SPARKLINE_LEGEND_SWATCH_CLASS) in both languages"
  - "companion/test_status_pages.py's _css_without_comments() helper"
  - "the composite-over-the-card measurement idiom for a translucent fill, using the app's own contrast_ratio()"
affects: [24-06, 24-08, 24-09]

tech-stack:
  added: []
  patterns:
    - "A NESTED <svg> with its own viewBox + preserveAspectRatio=none is how a percentage-scheme drawing gains an element that percentages cannot express, without the outer canvas changing coordinate system"
    - "An area under a line closes at the SCALE's floor, never the canvas edge — closing at the edge adds the vertical inset to every reading as a constant"
    - "A translucent fill is measured as a COMPOSITE over its own background, not as a resolved fill: 'painted but invisible' is invisible to a paint reader"
    - "A reference line's label is a LEGEND in its own row, not a third axis tick: a space-between column can only place a third label at the middle, and a legend claims no position so it cannot claim a wrong one"
    - "A mark that must survive a suppression rule gets its own class rather than a modifier on the suppressed one, so 'suppress the dots' and 'keep the mark' cannot become the same instruction"
    - "For every CSS property added, mutate it and require a named check to fail; delete the ones that do not"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/i18n_fr/health.py
    - companion/test_status_pages.py
    - companion/test_browser_ux.py

key-decisions:
  - "The area's geometry was resolved by experiment: a nested <svg> carrying viewBox='0 0 100 100' + preserveAspectRatio='none', chosen over a sibling <polygon> (percentages are illegal in a points list) and per-segment quadrilaterals (only <rect> takes percentage geometry, and a trapezoid is not a rect). The outer canvas still carries no viewBox."
  - "No <linearGradient>. It is only referenceable as url(#id), which battery_sparkline_svg()'s own D-09 no-external-reference guarantee forbids outright. A flat translucent currentColor fill keeps that guarantee unweakened; CFG-45's 'fade' is met as 'translucent, derived from the line's own colour' and not as a gradient."
  - "The area closes at sparkline_point_y(SPARKLINE_Y_MIN_MV), the level the '3000 mV' label names, not at the canvas edge."
  - "The mark carries SPARKLINE_MARK_CLASS, not a modifier on SPARKLINE_DOT_CLASS — that IS the density rule's exception, expressed so it cannot be read as a contradiction."
  - "The threshold's label is a legend in its own full-width grid row, because .sparkline__y's space-between can only place a third label at 50% while the threshold sits at 59.25%, and pinning it to its real level needs an inline style attribute this codebase's drawing vocabulary refuses."
  - "The legend is NOT aria-hidden, unlike every axis label: those are hidden because every point already announces its value, and nothing anywhere announces where 'low' starts."
  - "`flex: none` on the legend's swatch was written, measured to be inert, and deleted."

patterns-established:
  - "Pattern: nested-viewBox escape hatch — a percentage-scheme canvas can host a user-unit sub-drawing without either scheme leaking into the other"
  - "Pattern: composite-and-contrast — measure a translucent fill's visibility through companion/contrast_check.contrast_ratio() against the element's own resolved background"
  - "Pattern: an inert-property hunt as part of mutation testing — every CSS declaration added must have a mutation that turns a named check red"

requirements-completed: []

duration: 59min
completed: 2026-09-14
---

# Phase 24 Plan 05: D8's Battery Chart — Area, Marked Reading, Threshold Summary

**Health's battery chart gained a filled area (drawn in a nested viewBox'd `<svg>`, because percentages are illegal in a `points` list and the outer canvas's no-viewBox scheme was not available to trade away), a marked current reading exempt from the density rule, and a low-battery threshold read from `companion/battery.py` and labelled by meaning — all three derived from the one filtered pair list, with the coordinate scheme, the keyboard path, the two-point floor and the no-external-reference guarantee intact.**

## Performance

- **Duration:** 59 min
- **Started:** 2026-09-14T02:06:49Z
- **Completed:** 2026-09-14T03:05:57Z
- **Tasks:** 3 of 3
- **Files modified:** 5

## The decision that mattered most

**Refusing the gradient.** CFG-45 asks for "a translucent fade", and the
obvious implementation is a `<linearGradient>` with two `currentColor`
stops. It is only referenceable as `fill="url(#id)"`, and
`battery_sparkline_svg()` carries a standing, directly-asserted guarantee
that its return value contains no `url(` at all — checked verbatim by
`_sparkline_has_no_external_reference()` (`companion/test_status_pages.py`),
which forbids the substring outright rather than forbidding external
schemes. The plan anticipated this and permitted the flat fill; what made
it the right call rather than merely the permitted one is that the
alternative was relaxing a security-shaped assertion for decoration, and
the property CFG-45 actually names — "derived from the line's own colour,
so it is correct in dark mode by the same mechanism the line already is" —
is fully delivered by `fill: currentColor` + `fill-opacity`. Measured:
the area, the line and the mark resolve to the identical ink in both
themes, and all three move when the theme does.

The runner-up, and the one that took the most reading: the threshold's
label is a **legend**, not a third Y-axis tick. `.sparkline__y` is a flex
column with `justify-content: space-between`, so a third label lands at
50% of the canvas; the threshold sits at **59.25%**. A label naming a
level it does not sit beside is a chart that lies, and the only way to
pin it to its real level is an inline `style` attribute, which
`companion/draw.py`'s `REFUSED_ATTRIBUTES` refuses by name. A legend
claims no position, so it cannot claim a wrong one — and its swatch
carries the same token and the same 1px height as the drawn rect, so the
connection is made by colour rather than by proximity, and that equality
is asserted in the browser.

## The area-geometry experiment: honest outcome

The plan named three candidates and allowed "no area" as an honest
result. **Candidate (a) was reached and shipped.** What was tried, in
order:

| Candidate | Outcome |
|---|---|
| (b) sibling `<polygon>`/`<path>` in the outer scheme | **Ruled out without building.** Percentages are not permitted in a `points` list or a `d` string — the identical rule this function's docstring already records as why the line is `n-1` `<line>` segments rather than one polyline. |
| (b') one quadrilateral per segment | **Ruled out without building.** Nothing but `<rect>` accepts percentage geometry, and a trapezoid is not a rect. |
| (a) nested `<svg>` with `viewBox="0 0 100 100"` + `preserveAspectRatio="none"` | **Shipped.** A nested svg establishes its own viewport; with that viewBox and that preserveAspectRatio, user unit N maps to exactly N% of the same box *in each axis independently*, so a plain user-unit polygon lands on the coordinates the outer scheme's percentages already produce. |
| (c) no area | Not needed. |

**The browser observation that settled it** (Chromium, 360px viewport,
seeded 40-day series, before anything was built on it):

```
canvas = {x: 89.03, y: 782.86, w: 229.97, h: 160,    bottom: 942.86}
layer  = {x: 89.03, y: 789.23, w: 229.97, h: 147.63, bottom: 936.86}
poly   = {x: 89.03, y: 789.23, w: 229.97, h: 147.63, bottom: 936.86}
topmost trend segment y = 789.23      (identical to the polygon's top)
polygon bottom 936.86 = canvas top + 154.0px = 96.25% of 160px
```

Three things settled at once: the layer's box equals the canvas's box in
x and width to 0.01px (both come from the single
`.battery-trend-section svg:not(.icon)` declaration — which is why the
layer deliberately gets **no CSS rule of its own**, and a harness check
asserts none exists); the polygon's top edge coincides exactly with the
highest trend segment; and its baseline sits on the axis minimum's own
level rather than the canvas edge. Stroke widths, marker radii and hit
radii were unchanged by Task 1 — the pre-existing radius pin
(`r="3"` x5, `r="8"` x5) stayed green through it untouched.

## Accomplishments

**Task 1 — the area.** A `<polygon class="sparkline-area">` inside
`<svg class="sparkline__area" viewBox="0 0 100 100"
preserveAspectRatio="none" aria-hidden="true">`, emitted first in
document order (SVG paints in document order, so an area emitted after
the line would cover it — asserted by index comparison, not by reading
the comment). `_point_y()` was promoted to a module-level
`sparkline_point_y()`, behaviour unchanged, so the area's baseline, the
threshold and the harness all place a level with the same arithmetic the
readings do.

**Task 2 — the mark and the threshold.** The newest *plotted* point gets
`SPARKLINE_MARK_CLASS` at `_SPARKLINE_MARK_RADIUS_PX = 5` from the final
iteration of the existing loop — the same element, one class and one
radius different, never a second circle appended afterwards. `is_latest`
now feeds both the mark and the roving `tabindex`, so the marked point
and the Tab stop are the same point by construction. The threshold is a
full-width `<rect>` at `sparkline_point_y(battery.LOW_BATTERY_DISPLAY_MV)`
in `var(--color-status-warn)`, suppressed entirely (line *and* label)
when the value falls outside `[SPARKLINE_Y_MIN_MV, SPARKLINE_Y_MAX_MV]`.

**Task 3 — measured, not read.** Eight resolved paint values, an area
visibility measurement done as a composite, the 360px floor in both
languages, and the scripts-blocked render.

## The eight resolved paint values (four shapes x two themes)

Read through `_computed_paint()` after the cascade has run, on `/health`
at 360px:

| Shape | light | dark |
|---|---|---|
| `.sparkline-area` fill | `rgb(23, 25, 31)` @ `fill-opacity 0.14` | `rgb(241, 243, 246)` @ `fill-opacity 0.14` |
| `.sparkline-line` stroke | `rgb(23, 25, 31)` | `rgb(241, 243, 246)` |
| `.sparkline-mark` fill | `rgb(23, 25, 31)` | `rgb(241, 243, 246)` |
| `.sparkline-threshold` fill | `rgb(217, 119, 6)` | `rgb(251, 191, 36)` |

None is the SVG default. The area, line and mark share one ink in each
theme (all `currentColor` — that *is* the CFG-45 mechanism); the
threshold deliberately does not (a judgement painted in the data's own
colour is not a judgement anyone can read). All four move with the theme.
The legend's swatch resolves to the threshold's fill exactly, in both
themes.

**Area visibility, measured as a composite.** A resolved `fill` cannot
see "painted but invisible", which is this feature's specific failure
mode, so the resolved fill is composited over the card's own resolved
background at the resolved alpha and run through the app's own
`contrast_check.contrast_ratio()`:

| theme | card | composite | ratio |
|---|---|---|---|
| light | `#FFFFFF` | `#DFDFE0` | **1.3317:1** |
| dark | `rgb(21, 25, 34)` | `#343840` | **1.4955:1** |

The check's floor is **1.20:1**, deliberately not WCAG's 3:1 (that figure
is for a UI component a user must find and identify; at 3:1 this would be
a block of ink). The floor is first missed between `fill-opacity` 0.08
(1.173 light) and 0.09 (1.202 light), so it bites at roughly two thirds
of the shipped 0.14 rather than sitting decoratively below it.

**360px floor, both languages** (`_assert_no_page_overflow`, strict
`scrollWidth > clientWidth`, no tolerance):

| surface | result |
|---|---|
| `/health` in en @360 | PASS — `documentElement.scrollWidth` 360 against clientWidth 360 |
| `/health` in fr @360 | PASS — 360 against 360 |

**Threshold label vs axis labels at 360px in French:** no box overlap
against any of the four axis labels. Measured boxes: legend
`{x: 41, y: 973.36, w: 161, h: 12}` in its own grid row
`{y: 962.86, h: 24}`; the nearest axis labels are the X pair at
`y: 946.86, bottom: 958.86`. The legend stays inside its card
(`right 202` against the card's `right 319`) at `font-size: 10px`.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — Bug] A CSS declaration whose comment claimed a property it
measurably did not have**
- **Found during:** Task 3, mutation M16
- **Issue:** `.sparkline-swatch { flex: none }` shipped with a comment
  claiming it stopped the swatch shrinking on French's tighter line.
  Removing it produced **no failure in any check, in either language** —
  at 360px the legend's line is 161px inside a 278px row, so there is no
  overflow to shrink against. This is exactly the "documented property
  that is measurably inert" defect 24-04 found four of.
- **Fix:** Deleted the declaration; rewrote the comment to record the
  measurement and why the property is gone rather than kept "just in case".
- **Files modified:** `companion/static/style.css`
- **Commit:** `76addb2`

**2. [Rule 1 — Bug] A load-bearing CSS property that no check could see**
- **Found during:** Task 3, mutation M17
- **Issue:** `.sparkline__legend { grid-column: 1 / -1 }` is genuinely
  load-bearing — with `grid-column: auto` the legend claims the
  auto-sized Y-label column and the canvas drops from **229.97px to
  109.00px** inside the same 278px grid. It overflows nothing, so
  **every assertion in the first version of the check stayed green.**
- **Fix:** Added a canvas-share-of-grid assertion (floor 0.70; shipped
  0.827, mutated 0.39) and rewrote the CSS comment to state the measured
  numbers and that the first check could not see them.
- **Files modified:** `companion/test_browser_ux.py`,
  `companion/static/style.css`
- **Commit:** `76addb2`

**3. [Rule 2 — scope] `companion/static/style.css` edited in Task 3**
- Task 3's declared `<files>` is `companion/test_browser_ux.py` alone.
  Deviations 1 and 2 required touching `style.css`, which is this plan's
  own file (`files_modified`), so there is no ownership conflict — but it
  is recorded rather than passed over.

### Existing checks retargeted in place (no count contribution)

Both were necessary consequences of the mark not being a cosmetic dot,
and both are *sharper* than what they replace. They were written into the
Task 2 **test** commit, before the implementation, so the RED phase
covered them:

1. `_sparkline_svg_has_per_point_interactive_markup` — "3 cosmetic dots"
   became "2 dots + 1 mark", which is what "every point is drawn" always
   meant. The old form would also have been satisfied by three dots and
   no mark at all.
2. The no-scale-factor check's radius pin — `r="3"` x5 / `r="8"` x5
   became `r="3"` x4 / `r="5"` x1 / `r="8"` x5, now expressed through
   `health_page._SPARKLINE_*_RADIUS_PX` rather than literals. The
   property it pins (every radius is an absolute pixel value no container
   width can scale, and no tap target shrank) is unchanged.

## Mutation testing

Every new check reverted and proven to fail. Fourteen mutations run; the
implementation was restored from the staged tree with
`git checkout-index -f --` between each (never `git checkout --`).

### Task 1 — the area (`companion/test_status_pages.py`)

| # | Mutation | Quoted failure |
|---|---|---|
| M1 | area emitted after the line segments | `expected the area layer to be emitted BEFORE the first trend-line segment` |
| M2 | baseline at the canvas edge (`y=100`) | `expected the area's two baseline corners at the axis minimum's own y (96.25%), got (100.0, 100.0) and (0.0, 100.0)` |
| M3 | `preserveAspectRatio` dropped from the nested layer | `expected the nested area layer to carry preserveAspectRatio="none" — without it the polygon's user units do not map onto the outer scheme's percentages; got '<svg class="sparkline__area" viewBox="0 0 100 100" aria-hidden="true">'` |
| M4 | `fill: #17191F` instead of `currentColor` | `expected '.sparkline-area' to fill with currentColor — the area's colour must be the LINE's own colour, so dark mode is correct by the same mechanism; got '\n  fill: #17191F;\n  fill-opacity: 0.14;\n'` |
| M5 | a `.sparkline__area { height: 100% }` rule added | `expected NO '.sparkline__area' rule in style.css — the area layer's box must come from the one '.battery-trend-section svg:not(.icon)' height declaration, not a second one` |

### Task 2 — the mark and the threshold (`companion/test_status_pages.py`)

| # | Mutation | Quoted failure |
|---|---|---|
| M6 | mark derived from the RAW rows (`ts == rows[0]['ts']`) | `expected exactly one marked point, got 0` |
| M7 | mark suppressed by the density rule (`is_latest and not dense`) | `expected the marked point to SURVIVE the density rule — it is not a cosmetic dot, and marking the current reading is the whole reason it is drawn` |
| M8 | threshold placed by its own arithmetic instead of `_point_y()` | `expected the threshold at sparkline_point_y(battery.LOW_BATTERY_DISPLAY_MV) = y="59.25%", got ' x="0" y="60.00%" width="100%" height="1" aria-hidden="true"' — a threshold with its own arithmetic drifts from the readings by the vertical inset` |
| M9 | `threshold_mv = 3480` re-typed in the page module | `found the literal 3480 in health_page.py — the threshold's value must be READ from companion/battery.py, never re-typed beside the chart that draws it` |
| M10 | out-of-range guard weakened to `threshold_mv > 0` | `expected NO threshold drawn for an out-of-range value (2900) — the clamp would pin it to the axis edge, where it reads as a threshold AT the chart floor` |
| M11 | legend given `aria-hidden="true"` like the axis labels | `expected the threshold legend NOT to be aria-hidden — the axis labels are hidden because every point already announces its value, and nothing announces this one` |
| M12 | swatch painted `var(--color-border)` instead of the threshold's token | `expected the legend's swatch to be painted with the SAME token as the drawn line, so the legend cannot come to describe a colour the chart does not use` |

### Task 3 — the browser measurements (`companion/test_browser_ux.py`)

| # | Mutation | Quoted failure |
|---|---|---|
| M13 | `fill-opacity: 0.02` (the plan's own near-invisible case) | `in light the area composites to #FAFAFB over the card's #FFFFFF for a contrast of 1.043:1, under this check's 1.20:1 floor — at that opacity the area is painted and invisible, which is the exact failure mode of this feature` |
| M14 | threshold `fill: currentColor` | `in light the threshold resolves to the trend line's own ink ('rgb(23, 25, 31)') — a judgement painted in the data's colour is not a judgement anyone can read` |
| M15 | `.sparkline-legend { display: inline }` | `in en at 360px the legend's swatch measures 0.00x11.00, not the 12x1 it declares — an inline <span> ignores width/height, so this is what proves the legend's flex context is doing something` |
| M16 | `flex: none` removed from the swatch | **NO FAILURE — see Deviation 1. The declaration was deleted.** |
| M17 | `grid-column: auto` on the legend's row | **NO FAILURE against the check as first written — see Deviation 2.** |
| M17b | same mutation, after the canvas-share assertion was added | `in en at 360px the chart's canvas is 109.00px of its 278.00px grid (0.39) — the legend has claimed the auto-sized Y-label column and squeezed the drawing, which overflows nothing and so shows up nowhere else` |
| M18 | `.sparkline-area { fill: #808080 }` | `in light the area ('rgb(128, 128, 128)'), the line ('rgb(23, 25, 31)') and the mark ('rgb(23, 25, 31)') are three different inks — all three are meant to be currentColor, which is what makes dark mode correct by construction rather than by a second colour value` |
| M19 | `.sparkline-mark` rule renamed away (falls to the SVG default) | `in light the chart's mark resolves fill to the SVG default ('rgb(0, 0, 0)') — it inherited no colour at all` **and** `with scripts blocked, in dark: the chart's mark resolves ('fill',) to the SVG default` |

## Checks that failed the vacuity question, and what was done

**1. The area-visibility check, as first conceived.** "The area's fill is
not the SVG default" would have been green at `fill-opacity: 0.001`. A
resolved paint reader cannot see a translucent fill's actual visibility
at all. Replaced with the composite-and-contrast measurement above, whose
floor was then *located* by sweeping alpha rather than asserted: it bites
between 0.08 and 0.09.

**2. The threshold-label overlap check.** Because the legend sits in its
own full-width grid row, "no overlap with the axis labels" is structural
— it cannot fail as long as the row exists. This was recognised rather
than papered over: the box comparison is kept (it keeps measuring the
right property if the row is ever traded for the absolute positioning a
third axis tick would have needed), and the check was **strengthened**
with two measurements that are not structural — the swatch's real 12x1
box (which an inline `<span>` cannot produce; M15 proves it) and the
canvas's share of the grid (M17b proves it). The overlap assertion alone
would have been the weakest thing in this plan.

**3. `grid-column: 1 / -1`.** Covered above as Deviation 2 — the property
was load-bearing and the check could not see it. Found by mutating every
CSS declaration added, which is the only reason it was found at all.

## Criteria that did not evaluate as predicted

**Task 3 had no RED phase, and could not have had one.** It is marked
`tdd="true"` but its `<files>` is the harness alone: it adds no
behaviour, only measurement of behaviour Tasks 1 and 2 already shipped.
Both new checks passed on first run. This is recorded rather than
disguised — the RED evidence for Task 3 is the mutation set (M13-M19),
and two of those mutations produced no failure at all, which is precisely
the value a mutation set has that a first-run red does not.

**The mark hangs 5px outside the canvas at `cx=100%`.** Measured:
`mark {x: 314, right: 324}` against the canvas's `right: 319` at 360px.
This is not new — `_point_x()` spans edge to edge, so the pre-existing
cosmetic dot already overhung by 3px and the hit target by 8px at the
same coordinate. The card's own padding absorbs all three (card right
edge 335 at 360px), and that is now asserted as "the mark's ink stays
inside the card" rather than "inside the canvas", with the reason stated
in the check. Worth knowing for 24-09's sweep.

## Plan assumptions that turned out wrong

**1. "a `<linearGradient>` referenced by `url(#id)` is an internal
reference, not an external one — but confirm the existing check's exact
wording."** The plan's no-JS-floor block flagged this correctly as
something to confirm, and the confirmation went the other way: the check
is a literal `for forbidden in ("url(", "<image", "<script")` substring
scan. There is no scheme analysis to appeal to. The plan's stated
fallback (flat translucent fill, and say why) was taken.

**2. "Draw the threshold as a filled `<rect>` ... Label it with a
`<span>` in the existing grid."** Both were done, but the plan's implied
reading of "the existing grid" as the Y-label column does not survive
contact with `.sparkline__y`'s `space-between`: a third label lands at
50% and the threshold is at 59.25%. The label is a legend in a new
full-width row of the same grid instead.

**3. `companion/draw.py` offers no primitive that fits.** The plan's
`read_first` asked. `percent_canvas()` emits no viewBox (that is its
whole contract) and `unit_canvas()` emits intrinsic `width`/`height`
attributes for an aspect-locked mark, which is wrong for a layer that
must stretch to its parent's box. `draw.py` is not in this plan's
`files_modified` and was not touched; the nested layer is emitted inline
in `health_page.py` with the reasoning recorded there.

## Re-derived check counts (obtained by RUNNING, never arithmetic)

| harness | before | after | delta |
|---|---|---|---|
| `companion/test_status_pages.py` | 288 | **291** | +3 (Task 1 x1, Task 2 x2) |
| `companion/test_browser_ux.py` | 57 | **59** | +2 (Task 3) |
| `companion/test_companion_app.py` | 300 | 300 | unchanged |
| `companion/test_view_pages.py` | 154 | 154 | unchanged (this plan does not touch Home) |
| `companion/test_i18n.py` | 24 | 24 | unchanged |
| `companion/test_contrast_check.py` | 43 | 43 | unchanged (the threshold spends the already-pinned `STATUS_WARN_ON_CARD_PAIRS`) |

Final passing state: status-pages 290/291, browser-ux 59/59,
companion-app 298/300, view-pages 154/154, i18n 24/24, contrast 43/43.

## Full-suite result

`./scripts/run-all-tests.sh` — 22 harnesses, 166.0s. Failing checks,
**by name**, exactly the five sandbox baseline:

1. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key ... (WR-11)`
2. `POST /airlines/resolve redirects with the manual_save_failed flash key ... (WR-11)`
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created ... (WR-11)`
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write ... (WR-11)`
5. `anomaly_active() runs on every page render and must never raise ...`

No sixth. `ruff check .` clean.

Two *further* failures were seen only inside mutation runs, never in a
clean run (both clean browser-ux runs were 59/59), and neither touches
the battery chart: a 0.19px overshoot of B10's 48px reminder ceiling, and
a theme-crossfade sample that landed before the transition started. Both
read as boundary/timing flakes, both are logged to
`deferred-items.md` in this phase directory, and neither was fixed —
out of scope.

## What this plan deliberately did NOT do

- No requirement ticked. CFG-39..CFG-45 belong to the closing plan;
  `STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md` are untouched, as
  24-01..24-04 each left them.
- `companion/pages/home_page.py` untouched — 24-06 owns it in wave 4.
- The ring gauge untouched — 24-04 shipped it.
- What the chart PLOTS is unchanged: the 90-day Paris-day daily-average
  primary series and its raw-readings fallback (260902-l0b) are out of
  scope and were not altered.
- `companion/draw.py` untouched.
- The `@keyframes` count (4) and the `@supports selector(:has(*))` count
  (1) in `style.css` are unchanged; the stray-comment-terminator guard
  stayed green throughout (every new comment is inside a block comment).

## Self-Check: PASSED
