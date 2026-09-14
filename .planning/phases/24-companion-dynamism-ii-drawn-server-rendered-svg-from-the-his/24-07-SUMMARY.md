---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 07
subsystem: ui
tags: [svg, health, check-in, staleness, accessibility, i18n, contrast]

requires:
  - phase: 24-03
    provides: "history_db.check_in_gaps() and wake.classify_check_in_gap() — the observed gap reader and the ONE application of device_staleness_thresholds() to those gaps"
  - phase: 24-01
    provides: "companion/draw.py's geometry vocabulary, escaping contract and unit/percentage scheme split; the shared .drawing* CSS block"
  - phase: 24-02
    provides: "companion/test_browser_ux.py's _set_ui_theme(), _computed_paint(), _assert_no_page_overflow() and _no_js_page()"
  - phase: 24-05 / 24-06
    provides: "the measured-not-estimated discipline, and the floor-not-only-ceiling lesson the bounded grid is built on"
provides:
  - "draw.regularity_grid() — a bounded grid of square cells with a fourth, honest 'no observation' state"
  - "draw.cell_class() / draw.CELL_STATE_CLASSES — the classifier's four verdicts as four paint classes, with anything unrecognised falling to absence"
  - "Health's 'Check-in regularity' card: 30 Paris days, a three-clause caption, a four-state key"
  - "layout.duration_text() — the third reading of the app's one s/m/h/d ladder"
  - "companion/wake.py re-exports classify_check_in_gap() and the CHECK_IN_* vocabulary"
affects: [24-08, 24-09]

tech-stack:
  added: []
  patterns:
    - "A drawing's element count bounded by its own geometry, keeping the NEWEST buckets and reporting how many it dropped, so a caption can stay honest"
    - "One `color`-only modifier class painting both an SVG cell (fill: currentColor) and an HTML legend swatch (background: currentColor), so a key cannot disagree with what it explains"
    - "A calendar window walked by date.toordinal()/fromordinal(), so a page that must contain no duration arithmetic can still name its own days"
    - "Mutate every CSS declaration you add: two were found inert and deleted with the measurement recorded in their place"

key-files:
  created: []
  modified:
    - companion/draw.py
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/i18n_fr/health.py
    - companion/layout.py
    - companion/wake.py
    - companion/test_status_pages.py
    - companion/test_browser_ux.py
    - companion/test_contrast_check.py

key-decisions:
  - "A day is judged by its LONGEST observed gap, and the cell's title names that duration — an average would hide the one six-hour hole a reader opens this page for"
  - "The no-observation cell is produced by the classifier itself (a gap of None answers CHECK_IN_UNKNOWN), so no branch on this page decides any cell's colour"
  - "Labels are HTML spans outside the canvas, so the viewBox-containment question does not arise for text; the cells' own ink is measured against the viewBox anyway"
  - "Ten columns of 25.10px is the most the measured 278px card holds above WCAG 2.5.8's 24px target size — the bucket count comes down, never the cell size"
  - "The gap read is made in render(), not in _read_health_inputs(), because the nav dot has no use for it and never will"
  - "The card is a plain .page-section, matching the Screen section's own precedent, not the page-section--nested modifier three checks pin the count of"

patterns-established:
  - "Bounded drawing: keep the newest, report the dropped count, and read the axis labels past what was dropped"
  - "Inert-declaration protocol: mutate, and if nothing fails either add the assertion or delete the declaration AND write the measurement where it stood"

requirements-completed: []

duration: 195min
completed: 2026-09-14
---

# Phase 24 Plan 07: D20's check-in regularity grid

**Health now draws 30 days of observed check-in regularity — four states including an honest "no record" — judged entirely by 24-03's classifier, under a caption whose three clauses each say what the picture is not claiming.**

## Performance

- **Duration:** ~195 min
- **Tasks:** 3/3
- **Files modified:** 9 (three of them — `companion/layout.py`, `companion/wake.py`, `companion/test_contrast_check.py` — not in the plan's `files_modified`; see Deviations)

## Commits

| Commit | Gate | What |
|---|---|---|
| `dbca90a` | RED | failing checks for the grid emitter |
| `4ed6266` | GREEN | `draw.regularity_grid()`, the four cell classes, the wake shim, the status-separation contrast checks |
| `5da01fb` | RED | failing checks for the Health section and its caption |
| `3e2db1c` | GREEN | the section, the caption, the key, the French catalogue, `layout.duration_text()` |
| `051dc36` | — | the browser measurements (no RED phase — see below) |
| `972f351` | docs | the two refused words talked around in the source that explains refusing them |

**Task 3 has no RED phase, and that is stated plainly rather than manufactured.** It adds only measurement: every assertion in it was written against an implementation that already existed and passed on the commit that introduced it. What proves those checks are not vacuous is the mutation table below — fourteen of them, each reverted, each quoted.

---

## The decision that mattered most

**A day the record says nothing about is classified, not branched on.**

The obvious implementation of a four-state grid is three verdicts plus an `if not observed: state = "no record"`. That line is where the defect would have lived: it is a second place deciding what a cell means, sitting beside the one place the plan says must decide it, and it is invisible to any check that only compares the three real verdicts against the classifier.

`wake.classify_check_in_gap(None, cadence)` already answers `CHECK_IN_UNKNOWN` — 24-03 built that for an undatable span, and it is exactly right for an unobserved day too. So `_check_in_regularity_cells()` looks up each day's longest gap, gets `None` for a day with no rows, and hands that to the classifier like any other value. **There is no branch anywhere on this page that decides a cell's colour.** The check that would have caught the alternative reads the page's builders off their compiled `co_names`: `classify_check_in_gap` must be there, and none of the four threshold constants may be.

The same decision shapes the emitter's side. `draw.cell_class()` falls to the **no-observation** class for anything it does not recognise — not to `None` (a cell has no neutral; it will be painted something), and not to on-cadence or missing. Falling to on-cadence would report health from a value nobody recognised; falling to missing would accuse the device on the same. M1 below is that fallback direction, proven.

---

## Mutations, with their quoted failure messages

Every check was reverted and proven to fail. The tree was staged before each mutation and restored with `git checkout-index -f --`; `git show --name-only` after each commit.

### Task 1 — the emitter

**M1 — an unrecognised verdict falls to on-cadence** instead of to absence:

> FAIL draw.cell_class() maps the classifier's four verdicts to four DISTINCT classes … - cell_class(None) returned 'drawing-cell--on-cadence' — an unrecognised verdict must fall to the no-observation class 'drawing-cell--none', never to a verdict the data does not support

**M2 — a cell with no title emits silently** instead of raising:

> FAIL … - expected a ValueError for a cell built with title None — a silent cell is a coloured verdict with nothing naming what it judged

**M3 — one more column than fits** (`grid_columns()` + 1):

> FAIL the regularity grid sizes its cells DOWN from the measured 278px card width … - at the measured 278px card width, 11 columns give a 22.55px cell — under the 24px minimum. The bucket count must come DOWN, never the cell size

**M4 — the bounded grid keeps the OLDEST buckets** (`supplied[:capacity]`):

> FAIL the regularity grid's element count is bounded by its own geometry … - the last cell is 'day 059', not the newest bucket supplied — a bounded grid that keeps the OLDEST cells draws a window that has already ended

**M5 — whole-pixel cell sizes** (`int()` around `grid_cell_size()`). **This mutation SURVIVED the first time it was run**, and finding that is the most useful thing Task 1 did — see "A check that failed the vacuity question" below. After the missing floor assertion was added:

> FAIL … - the last column's right edge is at 277.00 against a 278.00px canvas — the grid does not reach its own right edge, so the label row beneath it (which measures itself against the card, not against this arithmetic) names a column that is not there

**M6 — rename `CHECK_IN_MISSING`'s value in `server/wake.py`.** Exactly the two checks that should:

> FAIL draw.cell_class() … - expected four DISTINCT cell classes for the four states, got ['drawing-cell--on-cadence', 'drawing-cell--late', 'drawing-cell--none', 'drawing-cell--none'] — two states painted by one class cannot be told apart

> FAIL draw.CELL_STATE_CLASSES is keyed on EXACTLY wake.classify_check_in_gap()'s own four CHECK_IN_* values … - draw.CELL_STATE_CLASSES is keyed on ['late', 'missing', 'on_cadence', 'unknown'], the classifier's vocabulary is ['late', 'no_check_in', 'on_cadence', 'unknown'] — a verdict wake.classify_check_in_gap() returns that this table does not carry paints as no observation at all

### Task 2 — the section and its caption

**M7/M8/M9 — each caption clause removed in turn.** Three mutations, three failures, one per clause, exactly as the plan required:

> FAIL CLAUSE 1 … - the caption does not carry its first clause 'Each cell is one day of observed check-in regularity, oldest first.'

> FAIL CLAUSE 2 — Health's regularity caption names the cadence the grid was judged against … (the check failed on its own named clause)

> FAIL CLAUSE 3 … - the caption does not carry its third clause 'A day with no record is not proof the frame did not wake: a log rotation this server missed leaves exactly the same gap.'

**M10 — a silently assumed default cadence** for a deployment that has none:

> FAIL with a config yielding no cadence at all, Health's regularity caption says the grid is judged against the fallback staleness floors and does NOT name a configured value … - with no determinable cadence the caption must name the fallback floors

**M11 — a day judged by its MILDEST gap** (`>` becomes `<` in the per-day maximum):

> FAIL every cell's verdict equals wake.classify_check_in_gap()'s own output for that day's longest observed gap …

**M12 — the empty deployment renders no section at all:**

> FAIL with no observations at all the regularity section still renders … - a deployment with no check-ins renders no regularity section at all — an absent section is a worse answer than an honest empty one

(plus the retargeted heading-count check, which caught the disappearing `<h2>` as a second, independent signal.)

**M13 — the roadmap's own name restored as the heading.** Two failures:

> FAIL CLAUSE 1 … - the heading is the roadmap's own superseded phrasing

> FAIL the rendered Health page contains neither 'honoured' nor 'punctual' … - the EN-rendered Health page contains …

### Task 3 — the browser measurements

**M14 — two cell states pointed at the same token:**

> in light the drawing-cell--late cell (#16A34A) and the drawing-cell--on-cadence cell (#16A34A) are dE76 0.0 apart, under the app's own MIN_SIGNAL_PERCEPTUAL_DISTANCE (28.0) — four states that read as three

**M15 — the viewBox shrunk so it no longer contains its own ink** (the enlargement mutation's equivalent, since this drawing has no SVG text to enlarge):

> in en a cell inks (0.00, 56.20)-(25.10, 81.30), outside the 278.00x68.75 viewBox

**M16 — `width: max-content` removed from the wrapper:**

> at 1280px the grid's wrapper is 830.00px against a 278.00px canvas — the label row is spread across a width the cells do not occupy

**M17 — `max-width: 100%` removed from both rules:**

> at 320px the canvas is 278.00px inside a 238.00px card

**M18 — `height: auto` removed:**

> at 320px the canvas renders 238.00x81.30, an aspect of 2.928 against the viewBox's own 3.419 — the cells are no longer square

**M20 — `.drawing-cell { fill: currentColor }` removed.** Two failures, one per check:

> in light the drawing-cell--missing cell resolves ('fill',) to the SVG default ('rgb(0, 0, 0)') — it inherited no colour at all and is black in both themes

> with scripts blocked, in dark: the drawing-cell--missing cell resolves ('fill',) to the SVG default

**M21 — the key item is no longer a flex box:**

> in en a key swatch renders 0.00x17.00, not the 12px square it declares — a swatch a flex line squeezed to nothing explains nothing

**M22 — the scale row's clear ground removed:**

> in en the date labels sit 0.00px under the canvas, not the 4px of clear ground the scale row declares

**M23 — the key item's own gap removed:**

> in en a key swatch and its word are 0.00px apart, not the 4px the key declares

**M24 — `flex-wrap: wrap` removed from the key:**

> in fr a key swatch renders 9.03x12.00, not the 12px square it declares

**M25 — the key's `margin-top` removed:**

> in en the key sits 0.00px under the drawing, not the 8px it declares

**M26 — the key's item gap removed:**

> at 1280px two of the key's labelled swatches are 0.00px apart, not the 16px the key declares — four states running together read as one sentence

**M28 — `justify-content: space-between` removed from the scale row:**

> in en the newest date label ends at 103.86 against a canvas right edge of 319.00 — the labels and the cells are placed by two scales

### Two mutations that SURVIVED — the inert declarations

**M19 — `flex: none` removed from `.check-in-key__swatch`:** `browser-ux: 63/63 checks pass`.
**M27 — `align-items: center` removed from `.check-in-key__item`:** `browser-ux: 63/63 checks pass`, **twice** — once before and once after a new assertion measuring the swatch's centre against its word's centre was added specifically to try to catch it.

Both were **deleted, with the measurement written where they stood**, per the standing rule. The reasons are worth recording because they are not the same:

- `flex: none` is inert *because of a sibling declaration*: `flex-wrap: wrap` on the key means no line ever has to take width from a swatch. M24 proves the dependency — remove the wrap and a French swatch is immediately squeezed from 12.00 to 9.03px. So the property is real; the declaration protecting it is redundant while the wrap holds, and the wrap is measured.
- `align-items: center` is inert *because of a coincidence of two sizes*: the swatch is 12px tall and `.drawing-axis-label`'s line box is 10px × 1.2 = 12px, so cross-start and centre are the same place. The new centring assertion is kept anyway — it is not vacuous, it pins a real property, it simply is not sensitive to this declaration today. The day either size moves, it is what says so, and the CSS comment records that chain.

**That is four properties found inert in this phase and two more here — six.** Treating it as the expected case was right.

---

## A check that failed the vacuity question, and what was done

**M5 survived the first time it was run, and the reason was that my own containment assertion was a ceiling.**

Task 1's geometry check asserted every cell is *inside* the viewBox (`x + w <= box_w`). That is a ceiling. A whole-pixel cell size — 25px instead of 25.10 — puts ten cells and nine gaps at 277px inside a 278px canvas, which satisfies every containment assertion in the check and is still wrong: the HTML label row beneath the canvas sizes itself from the **card**, not from the emitter's arithmetic, so the "newest day" label would sit one pixel past the last column it names. One scale places the cells and the labels, and a ceiling cannot see that.

The floor assertion was added (`the last column's right edge must equal the canvas width`), M5 re-run, and it fails naming both numbers. **This is the third consecutive plan in this phase where the ceiling was green and the floor was the defect** — 24-06's collapse rule, 24-06's own re-derivation, and now this.

A second check was rewritten for the mirror problem: the first draft of the "no interval arithmetic" scan failed against a **correct** implementation, because `_check_in_regularity_cells()`'s docstring explained why it does not use a duration type — using that type's name to say so. The prose was changed, never the check, following 24-03's own precedent for exactly this. Three further comments (in `health_page.py`, `i18n_fr/health.py` and, pre-existing, twice in `draw.py`) were reworded in commit `972f351` for the same reason.

---

## Criteria that did not evaluate as predicted

1. **The plan expected this to be the phase's SVG-text drawing.** CFG-45 named it "the one that owes the viewBox-containment proof by real measurement". Task 1 chose HTML spans outside the canvas instead — the established mechanism, and the one that makes the containment question not arise for text at all. The cells' own ink is still measured against the viewBox (M15 proves that measurement works), so the proof is a real measurement rather than a skip, it simply is not a proof about text. **The decision and its consequence are recorded here because the plan asked for them not to be left implicit.**
2. **Three existing checks pin `page-section--nested`'s count and order**, and a fourth pins Health's `<h2>` count. The first three were left untouched by rendering this card as a plain `.page-section` — which is not designing around a check: the Screen section's *existing* full-width card (battery trend) carries its own class rather than that modifier, so following the precedent already inside the section was the right call on its merits. The heading-count check was genuinely retargeted in place, 4 → 5 in both fixtures, with its own half (no heading carries a glyph) untouched.
3. **`grep -c '3600\|60 \* \|timedelta'` over the new page code is 0**, as the plan required, with no justified hits. `_cutoff_iso()` is called from `render()` to bound the DB read, but it is a pre-existing display-window helper and is not inside either builder the check scans.
4. **`companion/test_contrast_check.py` needed a genuinely new pair set, and it was not the one the plan expected.** The plan asked whether a status colour on the card background is a new pair; it is not (error-on-every-surface and warn-on-card are already pinned). What *is* new is **status vs status**: the grid is the first surface in this app where all three appear side by side with nothing but colour between them, and nothing anywhere pinned that. Six checks added (three pairs × two themes); the closest pair at the shipped palette is light warn/error at dE76 55.3.

---

## Plan assumptions that turned out wrong

1. **`files_modified` was incomplete, in the same way 24-03's was.** Three files not listed were modified: `companion/wake.py` (the re-export the executor prompt flagged, and the only way to reach one classifier), `companion/layout.py` (`duration_text()` — the caption has to name a cadence and this app had two ways to say "5 minutes ago"/"in 5 minutes" and none to say "5 minutes"), and `companion/test_contrast_check.py` (which Task 1's own action text explicitly authorises). Wave 5 is this plan alone, so no ownership was violated — but the list was wrong.
2. **The plan's `<interfaces>` says the caption must agree with the reader's "cannot know" docstring paragraph.** It does, and the wording was taken from it — but that paragraph names *two* things the reader cannot know (the lost log range, and that "no rows in this window" cannot be told from "the ingest did not run"). The caption carries the first, because it is the one a reader would otherwise misread as a device fault. The second is the same sentence from the server's side and would not change what a reader does.
3. **The fixture cost of "all four states" was under-estimated by the plan's own framing.** Because a day is judged by its longest gap *including the one from the previous day's last check-in*, a day cannot read "on cadence" unless it is covered end to end — the browser fixture therefore seeds three full days at a 10-minute cadence (432 rows), not a handful of check-ins. That is a property of the drawing, not of the harness.

---

## Re-derived check counts (obtained by RUNNING, never by arithmetic)

| Harness | Before | After | Delta |
|---|---|---|---|
| `companion/test_status_pages.py` | 291 | **302** | +4 (Task 1), +7 (Task 2) |
| `companion/test_browser_ux.py` | 61 | **63** | +2 (Task 3) |
| `companion/test_contrast_check.py` | 43 | **49** | +6 (Task 1) |
| `companion/test_view_pages.py` | 161 | **161** | unchanged |
| `companion/test_companion_app.py` | 300 | **300** | unchanged |
| `companion/test_config_page.py` | 240 | **240** | unchanged |
| `companion/test_i18n.py` | 24 | **24** | unchanged |
| `server/test_config_history.py` | 87 | **87** | unchanged |
| `server/test_poll_loop.py` | 99 | **99** | unchanged |

The deferred-script pin stays at 14: this plan adds no script, and the grid is complete with scripts blocked (measured).

---

## Threat model

| Threat ID | Disposition | How it landed |
|---|---|---|
| T-24-07-A (a grid accusing the device of wakes it may not have missed) | mitigated | the fourth state is produced by the classifier itself and is a distinct class, asserted never to be the on-cadence or missing one; the caption's third clause has its own check and its own mutation; the vocabulary is "observed" throughout, with the refused words grep-pinned absent from both rendered languages |
| T-24-07-B (timestamps interpolated into `<title>`) | mitigated | every title goes through `draw.escape()` via `_attrs()`; the emitter has no exception path, and a missing title raises rather than emitting an empty one |
| T-24-07-C (the grid exposes the device's activity pattern) | accepted, unchanged | session-gated page, same pattern already on Health's readings table |
| T-24-07-D (an unbounded cell count) | mitigated | bounded at `grid_columns() × GRID_MAX_ROWS` by the drawing's own geometry, never by the caller's window; asserted at both ends (the count, and that the cells kept are the newest) |
| T-24-07-SC (package installs) | n/a | zero packages installed in any ecosystem |

No **Threat Flags**: no new endpoint, auth path, file-access pattern or schema change. The `wake_epochs` table remains read by nothing — `grep -rn 'wake_epochs' companion/` is still empty, and 24-03's check that pins it still passes.

---

## Known stubs

None. The grid renders real data in every state including absence, and the empty deployment is a rendered case rather than a placeholder.

---

## Verification

`./scripts/run-all-tests.sh` — the failing set is **exactly the 5 baseline checks, by name**:

| # | Harness | Check |
|---|---|---|
| 1 | `server/test_manual_resolutions.py` | `add_entry()` returns ADD_FAILED … read-only parent directory (WR-11) |
| 2 | `server/test_manual_resolutions.py` | `delete_entry()` returns False … read-only mid-write (WR-11) |
| 3 | `companion/test_companion_app.py` | POST /airlines/resolve … `manual_save_failed` flash key (WR-11) |
| 4 | `companion/test_companion_app.py` | POST …/delete … `manual_delete_failed` flash key (WR-11) |
| 5 | `companion/test_status_pages.py` | `anomaly_active()` … non-existent state_dir |

No sixth. Neither of the two intermittents `deferred-items.md` records appeared in any run, including the fourteen mutation runs.

`ruff check .` — **All checks passed!**

Final greps:

- `grep -ci 'honoured\|punctual'` over the rendered EN and FR Health pages → `0`, `0` (asserted by a check, not only by hand)
- `grep -c '3600\|60 \* \|timedelta'` over both new page builders → `0` (asserted off `inspect.getsource`)
- `grep -rn 'wake_epochs' companion/` → nothing
- `companion/static/style.css` stray comment terminators → 0, `@keyframes` still exactly 4, `@supports selector(:has(*))` still exactly 1 (all pinned by existing checks, all green)

## Self-Check: PASSED

All nine modified files exist on disk. All six commits (`dbca90a`, `4ed6266`, `5da01fb`, `3e2db1c`, `051dc36`, `972f351`) are present in the repository history.
