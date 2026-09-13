---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 10
subsystem: companion
tags: [display-page, device-page, geometry, theme-preview, i18n, css]
requires:
  - "22-05: quiet_hours_group()'s current shape (the retired on/off checkbox, the preset row)"
  - "22-08: the widened test_i18n.py scanner (app.py, attribute literals, JS fallbacks)"
  - "22-09: .filter-bar__meta (not consumed here — this plan's surfaces carry no filter bar)"
provides:
  - "one chip density across the whole Display page (.theme-chip--compact on every colour_usage grid)"
  - "data-current-label: a server-rendered, translated badge string the ::after rules read"
  - "form=\"notifications-test\": the cross-DOM form= idiom's fifth consumer"
  - "THEME_PREVIEW_CROP_BOX = (0, 390, 1200, 840) — caption-free, 8:3, pairwise-distinct"
  - ".field-inline-value: the sibling-value role B14 and B17 both use"
  - "a browser-level no-JS floor check for both settings pages"
affects:
  - "companion/pages/config_page.py"
  - "companion/theme_preview.py (every consumer of the served preview PNG)"
  - "companion/static/style.css"
tech-stack:
  added: []
  patterns:
    - "equal-specificity-plus-source-order to beat an earlier rule (B15, B17), never a specificity raise"
    - "a positive restore rule beside a :not()-scoped hover (B7/C3)"
    - "comment-filtered greps in CSS assertions, so justification prose survives a count"
key-files:
  created: []
  modified:
    - "companion/pages/config_page.py"
    - "companion/theme_preview.py"
    - "companion/static/style.css"
    - "companion/i18n_fr/display.py"
    - "companion/i18n_fr/calendar_group.py"
    - "companion/test_config_page.py"
    - "companion/test_companion_app.py"
    - "companion/test_browser_ux.py"
    - ".planning/REQUIREMENTS.md"
decisions:
  - "The swatch legend names departures/arrivals, not 22-UI-SPEC.md's prescribed 'Background · Ink' — the dots are departing_index/arriving_index and a theme's background is never drawn as a dot"
  - "B9 is fixed on .runway-card, not on .runway-row, because .runway-row has a second consumer (the quiet-hours preset row) that must keep wrapping"
  - "The wake-interval unit 's' is not routed through i18n.t(): it is the SI symbol, identical in French, and test_i18n.py rejects a catalogue value equal to its key by design"
metrics:
  tasks: 3
  commits: 4
  completed: 2026-09-13
---

# Phase 22 Plan 10: Display + Device geometry Summary

One chip density on Display, three runway cards that never orphan, a visible 24 h
time, a content-width Connect, a caption-free preview crop, and a Device page whose
controls share one left edge — with the "Current" badge translated through an
attribute and the no-JS floor asserted at this plan's own commit.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `e1837f4` | feat(22-10): one chip density on Display, a named swatch pair, and a translated Current badge |
| 2 | `a3f4e67` | fix(22-10): three runway cards on one line, a readable 24h time, a content-width Connect, and a crop that keeps its glyphs |
| 3 | `481bc8b` | fix(22-10): Send a test goes home to its card, and the wake-interval field lines up |
| 4 | `fb69206` | fix(22-10): the Calendar status detail gains a singular form |

Commit 4 is outside the plan's three tasks — see "Scope additions" below.

## Measurements

Every figure below is from a real Chromium tab against a real `companion/app.py`
subprocess seeded with 22-AUDIT.md's own fixture, measured before and after.

| What | Before | After | Target |
|---|---|---|---|
| Display page height, 1280px | 2674 px | **2389 px** | ≤ 2000 px — **NOT MET**, see below |
| Display page height, 390px | 4172 px | **3661 px** | ≤ 2600 px — **NOT MET**, see below |
| Departures chips | 160 × 108 | **104 × 72** | compact, like every other grid |
| Runway cards, 390px | 150×150, 150×150, **308×217** (2 + 1) | **96.7 / 98.7 / 96.7 × 142.25, one line** | three equal on one line |
| Runway cards, 1280px | 271.3 × 197.4 × 3 | 270.7 / 272.7 / 270.7 × 198.2 | unchanged |
| Segmented rule-kind control | 42 px tall, 28 px segments | **34 px tall, 28 px segments** | no 8 px tail |
| Connect calendar, 1280px | **830 × 30** | **133 × 30**, left edge 361 = its field's | ≤ 240 px, left-aligned |
| Connect calendar, 390px | 308 px | 141 px | content width |
| Wake-interval input | x=515, **w=448** | **x=361, w=96, h=44** | x=361, ≤ 120 px, 44 px kept |
| Notifications topic URL | x=361, w=448 | unchanged | the reference edge |
| "Send a test" | orphan between two cards | **inside the Notifications card**, x=361 | inside its card |
| Theme preview crop | (0, 420, 1200, 870), caption sliced | **(0, 390, 1200, 840)** | no partial glyph |
| Active segment, hovered | `rgb(150,54,16)` fill under `rgb(177,63,22)` text | **12 % accent wash under accent text** | readable |
| Label-voice legend | Iowan Old Style (serif) | **system sans (`--font-ui`)** | label voice, UI font |

### Crop distinctness re-measurement (required by the plan)

Mean RGB of the 320×120 served PNG, computed for **all 18 registered themes** at
both boxes. Metric: minimum per-channel-absolute-difference sum over all 153 pairs.

| Box | Duplicate means | Minimum separation | Closest pair |
|---|---|---|---|
| `(0, 420, 1200, 870)` (replaced) | none | 14.968 | `band_blue_light` / `band_green_light` |
| `(0, 390, 1200, 840)` (shipped) | **none** | **14.845** | `band_blue_light` / `band_green_light` |

The margin is essentially unchanged — this is not a newly-narrow box. Both
properties the constant's own comment requires survive: exact 8:3 (1200:450 against
THEME_PREVIEW_SIZE's 320:120) and pairwise-distinct mean RGB.

Ink bands measured in the 1200×1600 fixed-scene render: `70–84` top labels,
`489–792` main aircraft, `859–888` caption, `904–919` airline sub-caption,
`1122–1285` previous aircraft. `render.py` anchors the main text block at
`main_placement.content[3] + MAIN_TEXT_GAP_PX` = 847 for every theme, band themes
included, so 847 is the theme-independent ceiling. The shipped box ends at 840.

`THEME_PREVIEW_CACHE_VERSION` did **not** need bumping: `preview_signature()`
already folds `THEME_PREVIEW_CROP_BOX` into its digest, so the change is a clean
cache miss with no purge step.

### Touch-target confirmations (both required by the plan)

- **Runway cards (B9).** They get narrower: 96.7–98.7 px wide × 142.25 px tall at
  390 px. The hidden radio's register entry is *exempt by delegation* — the
  wrapping `.runway-card` `<label>` is the real activation target — and that label
  still clears 44 px in **both** axes by a wide margin. The entry holds. The
  browser check asserts `≥ 44 × 44` per card so a future narrowing fails loudly.
- **Wake-interval number input (B17).** The rule declares `width` and `min-width`
  and **no height at all**. `width` does not touch `min-height`, so the global
  `input, select` 44 px floor — the touch-target register's "kept" entry for
  `<input type="number">` (11-03-PLAN.md) — is untouched. Measured after the
  change: **44 px tall**. The test asserts the absence of any `height` declaration.

## Harness pins

| Harness | Old pin | New pin | Net |
|---|---|---|---|
| `companion/test_config_page.py` | 223 | **232** | +9 (4 Task 1, 2 Task 2, 2 Task 3, 1 scope addition) |
| `companion/test_companion_app.py` | 260 | **261** | +1 (the crop-geometry check) |
| `companion/test_browser_ux.py` | 7 | **9** | +2 (B9 at 390 px; the no-JS floor) |
| `companion/test_i18n.py` | 24 | 24 | 0 — new strings needed entries, not checks |

Every pin was re-derived by **running** the harness and reading its printed total,
never by arithmetic. Five existing assertions were retargeted in place with no net
count change (the departures grid's "plain class", the `content: "Current"`
literal, the time inputs' `form=` literal, and two `wake_interval_s` markup greps).

The new crop check was **negative-controlled**: with the replaced box restored it
fails with `ink band (859, 888) is cut by the crop box's 'bottom' edge`.

## Regression floor

`PYTHON=server/.venv/bin/python bash scripts/run-all-tests.sh` → 3 failing
harnesses, coverage **93 %** (≥ 83). The failing **check names** are exactly the
documented root-sandbox baseline — five, unchanged:

- `server/test_manual_resolutions.py` 21/23 — 2 × WR-11 read-only
- `companion/test_companion_app.py` 259/261 — 2 × WR-11 read-only
- `companion/test_status_pages.py` 251/252 — 1 × `anomaly_active()`

No new failure hiding inside an expected-failure set. `ruff check .` clean.

## Acceptance criteria that did not evaluate as predicted

Five. None was worked around; each is reported as found.

### 1. X6's page-height target is not met, and cannot be by this plan's scope

**Criterion (must_haves X6):** "the page measures at most 2000 px desktop and
2600 px on a phone". **Measured: 2389 px / 3661 px.**

The plan ships X6's *density* half and explicitly defers its other half — "grid
folded behind the big preview (dialog/drawer)" — to D5, Phase 23. The height target
was set against the audit's 2900 / 4250 baseline assuming **both** halves. Density
alone buys 285 px desktop and 511 px phone.

Desktop breakdown after the change: page header 86, Frame strip 248, form 30, three
section intros 36 each, **Frame colours card 718** (of which the live preview is 180
and the one expanded usage panel 303), Calendar card 362, Runway card 325, Quiet
hours card 273. Reaching 2000 px means removing ~390 px, which is the chip grid —
i.e. exactly the deferred half. There is no remaining density win inside this plan's
declared scope.

Recorded here, and in `CFG-30`'s traceability row, so the phase checker reads the
gap as a scope boundary rather than as a miss, and so Phase 23's D5 inherits the
number it has to close.

### 2. "The rules add-form is one left-aligned line" — it is one left-aligned ROW, laid out over three wrapped lines

**Measured at 1280 px, before:** children at x = 996, 1051, 361, 1113 — right-aligned,
"Add rule" far right. **After:** all four children at **x = 361**, the segmented
control and the value input sharing one line and centre-aligned to each other
(tops 940 / 935), the 18-chip grid on the next line, "Add rule" on the third.

The prescribed CSS contract is implemented verbatim (`display: flex`,
`gap: var(--space-sm)`, `align-items: center`, left-aligned). A literal single
visual line is not reachable: the compact chip grid is 18 × 104 px ≈ 2000 px of
intrinsic width, which cannot share an 830 px line with three other controls at any
viewport. Forcing it (`flex: 1 1 0` on the grid field) would make the row ~460 px
tall and float "Add rule" vertically in its middle — worse than the defect.

The audit's own measured defect (right-alignment, "Add rule" far right) is closed.

### 3. The plan's stated cause of that right-alignment was wrong

**Plan:** "Remove the auto left margin that pushes Add to the far right."
**Measured:** there is no `margin-left: auto` anywhere on this form, and never was
(`grep -n 'margin-left: auto' companion/static/style.css` returns seven hits, none
of them in a `.rule-add-form*` rule).

The real cause: `.rule-add-form--inline` never reset `.rule-add-form`'s own
`flex-direction: column`. In a **column** flex container the cross axis is
horizontal, so the modifier's `align-items: flex-end` aligned every child to the
**right** edge, each on its own line. `flex-direction: row` is the actual fix.
Recorded in the rule's own comment, because the next reader will otherwise look for
the margin the spec describes.

### 4. Half of B7/C3 already existed

**Plan:** "add an explicit hover rule for a non-active segment at the register's
4.5 per cent text wash, **and** a positive restore rule for the ACTIVE segment's
hover". The first already shipped:
`.theme-form .theme-option:not(.theme-option--active):hover` at 4.5 %, introduced
2026-09-02 by `quick-260902-qkm`, well before this phase. Only the active-segment
restore was missing, and only that was added. The test asserts both rules exist and
that the `:not()`-scoped one still precedes the restore.

### 5. B9's "equal within 1 px" fails on outer widths — because of T6, which 22-15 owns

**Measured at 390 px:** 96.66 / **98.67** / 96.67 px — a 2.02 px spread.

Cause, isolated by measurement: the saved card carries
`.runway-card--selected`'s **2 px** border against its siblings' 1 px. Under
`box-sizing: border-box` with a zero flex basis, that makes its used outer width
exactly 2 px larger. This is **T6** — "selection shifts layout by 2 px" — which
`22-15-PLAN.md` owns and closes by holding the border constant at 1 px and moving
the selection signal to `box-shadow: inset 0 0 0 2px`.

The browser check therefore asserts B9's 1 px equality on the cards'
**border-excluded** widths (which is what "three equal columns" means and what the
flex rule controls), and separately asserts that the only outer-width difference is
a border total of 2 px or 4 px. That is a **stated exception with the plan that
removes it**, written into the check's own comment: when 22-15 lands, the border
allowance is deleted and the two measurements converge. B9's own defect — the
orphan — is pinned by the equal tops, which no border width can mask.

## Deviations from plan

### 1. [Rule 1 — Bug] The swatch legend's prescribed copy names the wrong two values

**Found during:** Task 1. **Issue:** 22-UI-SPEC.md §2's X6 row prescribes the
literal legend copy `Background · Ink` / `Fond · Encre`. The two `.theme-chip__dot`
swatches are `_palette_hex(theme["departing_index"])` and
`_palette_hex(theme["arriving_index"])` — the ink a theme paints a **departure** and
an **arrival** in. A theme's background is never drawn as a dot, and its
`ink_index` (a real, separate `THEMES` key) is not drawn either. **Fix:** the legend
reads `Departures · Arrivals` / `Départs · Arrivées`, reusing the usage panels' own
labels so the legend and the panel the user is looking at name the same two things.
Shipping the spec's copy would have replaced two unexplained swatches with two
mislabelled ones — a worse defect than the one X6 reports, and the audit's own fix
column prescribes no copy at all. **Files:** `companion/pages/config_page.py`,
`companion/i18n_fr/display.py`. **Commit:** `e1837f4`. **Needs a §4 skill edit** —
see "For 22-16" below.

### 2. [Rule 1 — Bug] The `--selected` placeholder chip would have rendered an empty badge

**Found during:** Task 1, caught by this plan's own new test. **Issue:** T10 moves
the badge's text onto `data-current-label`, emitted where `--selected` is set. The
"Same as departures" placeholder chip (`_same_as_departures_chip_html()`) also
carries `--selected`, and is the **default** saved state for both Arrivals and
Calendar. Emitting the attribute only from `_theme_chip_grid_html()` would have
rendered `content: attr(...)` against a missing attribute — an empty badge on the
commonest saved value of all. **Fix:** the placeholder chip emits it too; the test
asserts the attribute is present on exactly the `--selected` elements and on no
others. **Commit:** `e1837f4`.

### 3. [Rule 3 — Blocking] `.runway-row` has a second consumer, so B9's prescribed mechanism could not be used

**Found during:** Task 2. **Issue:** 22-UI-SPEC.md §2's B9 row prescribes
`.runway-row { flex-wrap: nowrap }` below 960 px. That class is also worn by
`quiet_hours_group()`'s three-preset row, whose buttons carry long labels
("Night (23:00–07:00)") that must keep wrapping on a phone. **Fix:** B9 is closed on
`.runway-card` instead — `flex: 1 1 0; min-width: 0` makes three items whose
hypothetical main size is 0 structurally incapable of overflowing their line, at any
width, with no media query and no change to `.runway-row`. Desktop is a measured
no-op (271.3 px per card before and after). The test asserts `.runway-row` still
declares `wrap`, so the prescribed-but-wrong mechanism cannot be reintroduced.
**Commit:** `a3f4e67`.

### 4. [Rule 2 — Missing] The 320 px fallback was needed, and taken

**Found during:** Task 2. The plan provides for it: "if measurement finds the runway
number illegible at 320 px, the fallback is a vertical list below 360 px". Measured
at 320 px with three columns: cards 73–75 px wide and
`scrollWidth > clientWidth` on all three — `.runway-card__number`'s longest label
("Runway 3 (07/25)") paints past the card's own border. **Fix:** a
`@media (max-width: 359.98px)` block giving `.runway-card` a 100 % basis — the
audit's own vertical radio list, never a re-wrap. At 390 px (the audit's own
measurement viewport) the three columns are untouched and the label wraps cleanly
inside them. **Commit:** `a3f4e67`.

### 5. [Rule 3 — Blocking] The B17 width rule had to move to win

**Found during:** Task 3. **Issue:** the first placement of
`input[name="wake_interval_s"] { width: 8ch }` measured no effect — the input stayed
448 px. `.config-form input[type="number"]` at (0,2,1) with `width: 100%;
max-width: 28rem` (a Phase 18 audit fix) is both more specific and later. **Fix:**
the rule became `.config-form input[name="wake_interval_s"]` at **equal**
specificity, placed **immediately after** its competitor — this file's own
documented equal-specificity-plus-source-order mechanism (`.logout-form button`,
`.dirty-bar__cancel`), never a specificity raise. It also dropped the id selector it
briefly used: this stylesheet carries no id selector at all and should not gain its
first one here. The test asserts the source-order relationship, so the rule cannot
be moved back and silently lose. **Commit:** `481bc8b`.

## Scope additions

**`CALENDAR_STATUS_DETAIL_TEMPLATE`'s missing singular (commit `fb69206`).**
`"%d upcoming flights · checked %s"` read "1 upcoming flights" whenever the calendar
feed held exactly one. 22-08-PLAN.md found it while widening the i18n scanner and
deliberately left it, because that plan does not own
`companion/pages/config_page.py`. This plan's `files_modified` does, so it landed
here, following the file's own established singular/plural shape
(`FRAME_COLOURS_RULES_COUNT_SINGULAR`): singular at exactly 1, plural otherwise,
both forms in the French catalogue. It is one of the three siblings `CFG-29` is held
unchecked for; the other two are in `airlines_page.py` (22-11) and `health_page.py`
(22-12).

## Test exceptions

**Added: one, stated, with the plan that removes it.** The B9 browser check allows
the three cards' **outer** widths to differ by a border total of 2 px or 4 px,
because the selected card's 2 px border is T6 and T6 is `22-15-PLAN.md`'s. The
check's own comment names T6, names 22-15, and says the allowance is deleted when
22-15 lands. B9's 1 px equality is still asserted, on the border-excluded widths.

**Removed: none.**

**Two comment filters, both load-bearing rather than convenient.** The "Current"
assertion and the `.runway-card` basis assertion read only non-comment lines,
because both rules keep prose that quotes the literal being banned — the
pseudo-element's four-point justification (which 22-UI-SPEC.md §2's T10 row says is
unchanged) and the `SUPERSEDED` note recording why 150 px/140 px produced the
orphan. Deleting explanation to satisfy a grep is the defect the filters prevent.
Both mirror this plan's own acceptance criterion (`grep -v '^ *[*/]'`).

## Requirements

Neither `CFG-30` nor `CFG-31` was ticked. `CFG-30` is served by **nine** plans and
`CFG-31` by the whole 22-15/22-16 tail; ticking either here would claim work five
other plans still owe. Only the traceability rows were updated:

| Row | What was added |
|---|---|
| `CFG-30` | 22-10 landed X6's density half, B6, B7, B8, B9, B14, B15, B17 — and the explicit note that X6's page-height target is **not** met and cannot be by density alone |
| `CFG-31` | 22-10 landed C1's legend half, C3, T10 and T12; C1's compact `empty_state()` is 22-12's, the rest is 22-15/22-16 |
| `CFG-29` | 22-10 landed the Calendar status plural 22-08 could not own; the two remaining siblings are 22-11 and 22-12 |

## Notes for 22-16 (the design-system sweep)

1. **§4's X6 row needs one more edit than it lists.** Beside widening the
   compact-chip entry's usage sentence, the row's prescribed legend copy
   (`Background · Ink` / `Fond · Encre`) is **wrong for these swatches** and was not
   shipped. Record the shipped copy (`Departures · Arrivals` / `Départs · Arrivées`)
   and the reason, so the skill does not preserve a copy string the code
   deliberately contradicts.
2. **§2's B9 contract is unsafe as written.** `.runway-row { flex-wrap: nowrap }`
   would break `quiet_hours_group()`'s preset row, which shares that class. Record
   that B9 is closed on `.runway-card` (`flex: 1 1 0; min-width: 0`), and that
   `.runway-row` is a shared layout class with two consumers.
3. **§2's B9 measurement prediction was off.** The spec predicted ≈108.6 px per card
   at 390 px from a 342 px content column; the real content column is 308 px and the
   cards measure 96.7–98.7 px. The spec's "cards stay ≥108×≥100 px" sentence should
   become "≥96×≥140 px, which still clears the 44 px floor in both axes by
   delegation".
4. **§2's B7 row is half-stale.** The `:not()`-scoped 4.5 % hover it asks for has
   shipped since 2026-09-02 (`quick-260902-qkm`). Only the active-segment restore
   was new.
5. **`references/control-density.md`'s segmented-control entry.** The 28 px segment
   geometry is unchanged, but the control it sits in measured 34 px, not 42 px, from
   this plan forward — the global `label` margin is now reset inside
   `.theme-form input[type="radio"] + label`, exactly as `.theme-chip` already does.
6. **A live interaction between two audits.** `.config-form input[type="number"]`'s
   `width: 100%` exists (Phase 18) so "Uses server default" is not truncated to
   "Uses se". B17 narrows that same field to 96 px, so the locked placeholder
   truncates again **whenever no interval is stored**. B17 is the later, narrower
   decision and wins for this one field, but the trade is real and is recorded in
   the rule's own comment. If the phase wants the empty state readable, the
   information belongs in the section caption, which is a copy change no plan owns.
7. **§4's C1 row** can record that the legend's non-serif override landed as
   `font-family: var(--font-ui)` added to the existing
   `.frame-colours__panel-legend` rule — already later and already (0,1,0) against
   the shared selector's (0,0,1), so no new rule block was needed. Bare `legend`
   stays in the shared serif selector, verified by test.
8. **The `:has()` block count is still exactly one**, at the single
   `@supports selector(:has(*))` block. This plan opened none and added none.

## Self-Check: PASSED

- `companion/pages/config_page.py`, `companion/theme_preview.py`,
  `companion/static/style.css`, `companion/i18n_fr/display.py`,
  `companion/i18n_fr/calendar_group.py`, `companion/test_config_page.py`,
  `companion/test_companion_app.py`, `companion/test_browser_ux.py`,
  `.planning/REQUIREMENTS.md` — all present and modified.
- Commits `e1837f4`, `a3f4e67`, `481bc8b`, `fb69206` — all found in `git log`.
