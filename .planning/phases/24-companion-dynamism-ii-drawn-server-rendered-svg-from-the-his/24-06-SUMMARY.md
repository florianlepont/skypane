---
phase: 24-companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
plan: 06
subsystem: companion-web
tags: [drawing, svg, time-domain, home, quiet-hours, paris-day]
requires: ["24-01", "24-04"]
provides:
  - "draw.percent_time(): the phase's only TIME-domain scale"
  - "draw.day_band(): a day drawn at its real width, reporting what it collapsed"
  - "home_page._day_band_html(): D13's band on Home"
affects: ["companion/pages/home_page.py", "companion/draw.py", "companion/static/style.css"]
tech-stack:
  added: []
  patterns:
    - "a time scale that REJECTS rather than clamps, because clamping an instant invents data"
    - "an emitter that returns its own collapsed count so the caller can caption truthfully"
    - "a CSS-only value asserted from a browser because no Python constant can guard it"
key-files:
  created: []
  modified:
    - companion/draw.py
    - companion/static/style.css
    - companion/pages/home_page.py
    - companion/i18n_fr/home.py
    - companion/test_view_pages.py
    - companion/test_browser_ux.py
decisions:
  - "detections are NOT plotted (24-RESEARCH.md open decision 5), honoured as scoped"
  - "the collapse rule compares against the LAST KEPT mark, for the FLOOR and not the ceiling"
  - "DAY_BAND_MIN_MARK_SPACING_PERCENT re-derived 1.2 -> 1.5 from a MEASURED 278px band"
  - "the quiet-hours window comes from quiet_hours_status()'s own derivation one level down"
metrics:
  duration: one session (resumed after a container restart)
  completed: 2026-09-14
---

# Phase 24 Plan 06: D13's Home Day Timeline Summary

A 24-hour Paris-day band on Home — one mark per check-in, the quiet-hours
window shaded across midnight as two spans — drawn from the phase's only
time-domain scale, which rejects out-of-day instants rather than clamping
them and reports every mark it had to collapse so the caption can never
claim a count the drawing does not show.

## Recovery note: task 1's mutation evidence was re-run, not inherited

A container restart killed the previous executor mid-mutation-test. Its
task-1 GREEN implementation survived staged; its mutation evidence did
not, and its SUMMARY was never written. **Every mutation recorded below
was run by this executor on this tree.** Nothing is reported second-hand.

The restart also left the worktree carrying an injected defect (the
wrap-around window mutated to one inverted span). It was reverted with
`git checkout-index -f --` against the staged tree before anything else,
and the restored tree was verified at the sandbox baseline before task 1
was committed. That is the second time in this phase the stage-before-you-
mutate discipline was what made recovery possible rather than guesswork.

## The decision that mattered most

**The collapse rule compares each position against the LAST KEPT mark,
not against its immediate predecessor — and the reason recorded in the
code for that was wrong.**

The original docstring claimed a predecessor comparison "would let a
dense run walk across the band a sub-minimum step at a time and emit a
mark at every one of them", breaching T-24-06-C's element-count ceiling.
Mutation M4 disproved it: positions are sorted, so a gap of at least the
minimum to the immediate predecessor is also a gap of at least the
minimum to every earlier mark. **The ceiling holds under either rule.**

What does not hold is the floor. At a cadence finer than the minimum
spacing every consecutive gap is under the minimum, so a predecessor
comparison keeps the first position and never keeps another. Measured on
the mutant: a day of 1 440 check-ins drew **one mark at 0.00%** and an
empty band after it — the device rendered as having died at midnight —
while `collapsed` dutifully reported 1 439 and all four of this band's
checks stayed green. The correct rule draws 66 marks from 0.00% to
99.31%.

All four original checks were CEILINGS. The whole class of "the band
shows too little" defects was unmeasured. The docstring now states the
real reason and the check asserts the floor: no interior gap and no
unmarked tail at the band's end may reach the minimum spacing, both exact
consequences of the greedy rule rather than chosen tolerances.

## Mutations, with quoted failure messages

Every new or strengthened check was reverted and proven to fail.

### Task 1 — the scale and the emitter (re-run after the restart)

| # | Mutation | Result |
|---|----------|--------|
| M1 | `percent_x()` substituted for `percent_time()` in mark placement | RED |
| M2 | out-of-day instants clamped instead of rejected | RED |
| M3 | wrapping window returns `[(end, start)]` — one inverted span | RED |
| M4 | collapse compares predecessor, not last kept | **SURVIVED** → fixed |
| M5 | collapsed count omits unplaceable instants | RED |
| M6 | `DRAWING_BAND_MARK_CLASS` dropped from `DRAWING_CLASSES` | RED |
| M7 | mark-centring transform removed | RED |
| M8 | `.drawing-band-mark` rule deleted from style.css | RED |

**M1** — `with 2 instants on the band, the 08:00 check-in is drawn at 0.00% instead of 33.33% — that is an INDEX position, not a time position (under draw.percent_x() it would sit at 0.00%)`

**M2** — `expected an instant outside the day to be rejected, got 0.0 for 1755999999 — clamping it would invent a check-in at an edge of the band`

**M3** — `expected a 22:00-07:00 window to shade TWO spans on a one-day band, got 1 — one span from 22:00 back to 07:00 has a negative width, and the obvious repair (swap them) shades the whole DAY and leaves the night clear, which looks entirely plausible`

**M5** — `expected 2 marks and 3 unplaceable instants reported, got 2 and 0`

**M6** — `the band's class 'drawing-band-mark' is not in draw.DRAWING_CLASSES, so the guard that every emitted class resolves to a real selector cannot see it — a class that exists in Python and nowhere in CSS paints nothing at all`

**M7** — `expected every mark centred on its instant, got '<rect class="drawing-band-mark" x="0.00%" y="0" width="2" height="100%"/>'`

**M8** (caught by 24-01's own guard in `test_companion_app.py`) — `companion/draw.py can emit class 'drawing-band-mark' and companion/static/style.css carries no selector for it — a class that exists in Python and nowhere in CSS paints NOTHING at all, and nothing else in this codebase would notice`

**M4 after the fix** — `at a 60s cadence the kept marks stop at 0.00% while the instants run to 99.93% — a tail of 99.93% carrying 1439 check-ins drew nothing, though the greedy rule keeps anything a full 1.20% past the last kept mark. The band would say the device stopped checking in`

### Task 2 — the band on Home

| # | Mutation | Result |
|---|----------|--------|
| M9 | bucket by the UTC date instead of the Paris day | RED |
| M10 | `day_seconds` hardcoded to 86400 | RED |
| M11 | (bad mutation — it MOVED the read rather than duplicating it) | survived, discarded |
| M11b | the builder makes its own read as well as the one passed down | RED |
| M12 | the section omitted when the day holds no check-ins | RED |
| M13 | the `quiet_hours_enabled` flag ignored | RED |
| M14 | the caption says "today" instead of naming the day | RED |
| M15 | the caption never admits a collapse | **SURVIVED** → fixed |
| M16 | the caption always admits a collapse (the mirror) | RED |

**M9** — `expected exactly ONE of the three check-ins on the 2026-08-27 Paris band, got 0 — under a UTC date bucket the 22:30Z check-in (Paris 00:30 today) drops off and the 2026-08-27T22:30Z one (Paris 00:30 TOMORROW) appears instead, which is the same count from the wrong rows`

**M10** — `on the 25-hour Paris day 2026-10-25 the 12:00 check-in belongs at 52.00% of the band, got 54.17% — a hardcoded 86400 puts it at 54.17% and leaves an hour of the band unreachable`

**M11b** — `expected render() to make exactly 3 history.db reads — the 2 it made before this plan (recent flights, latest battery) plus the band's one — got 4. 'One read, reused' is measured here, not assumed`

**M12** — `expected the band section to survive a day with no check-ins — an absent section reads as an unbuilt feature, an empty band reads as no activity, and those are different statements`

**M13** — `expected zero shaded spans with quiet hours disabled, got ['<rect class="drawing-band-span" x="0.00%" y="0" width="29.17%" height="100%"/>', '<rect class="drawing-band-span" x="95.83%" y="0" width="4.17%" height="100%"/>']`

**M14** — `expected the caption to name the Paris day it draws, got '…<p class="text-label">3 check-ins on today.</p></section>'`

**M15 after the fix** — `the band drew 17 marks for 300 check-ins and its caption did not say they were merged — the drawing dropping marks silently and the caption printing a total are the two halves of one lie (T-24-06-B)`

**M16** — `the band collapsed nothing (3 marks for 3 check-ins) yet its caption said marks were merged — a caption that always admits a collapse tells the reader nothing and is untrue on every sparse day`

### Task 3 — the measurements

Task 3 adds **only measurement**, so it has no RED phase. Saying that
plainly rather than manufacturing one: its checks passed on their first
run against an already-correct implementation, and their value is
demonstrated by the mutations below, not by a staged failure.

| # | Mutation | Result |
|---|----------|--------|
| M17 | `.drawing-band-mark` declares no fill (SVG default) | RED |
| M18 | the frame takes the span's full token strength (40% → 100%) | RED |
| M19 | `--drawing-canvas-height: 24px` removed from `.day-band` | **SURVIVED** → fixed |
| M20 | `.day-band__hours` loses `display: flex` | RED |
| M20b | `.day-band__hours` loses `justify-content: space-between` only | RED |
| M21 | marks emitted 1px wide while draw.py declares 2 | RED |
| M22 | `DAY_BAND_MIN_MARK_SPACING_PERCENT` back to its wrong 1.2 draft | RED |
| M23 | the span painted in the marks' own `currentColor` | RED |

**M17** — `in light the band's mark resolves ('fill',) to the SVG default ('rgb(0, 0, 0)') — it inherited no colour at all and is black in both themes` (and, with scripts blocked: `with scripts blocked, in dark: the band's mark resolves ('fill',) to the SVG default`)

**M18** — `in light the shaded span (#DFD7C8) and the band's own surface (#DFD7C8) differ by only 1.000:1, under this check's 1.15:1 floor — quiet hours would be shaded and invisible, which is the whole of what the span is for`

**M20 / M20b** — `in en the 24:00 label ends at 167.47, not the canvas's own right edge 319.00`

**M21** — `in en at 360px mark 0 renders 1.00px wide, under the 2px draw.py declares — a mark thinner than the ink it asks for is a mark the reader cannot see`

**M22** — `in en the canvas measures 278.00px, so draw.py's 1.20% minimum spacing is 3.34px centre to centre — under the 4px two 2px marks need to keep a clear pixel between them. The constant's derivation and this layout have drifted apart`

**M23** — `in light a mark (#17191F) over the shaded span (#17191F) is 1.000:1, under this check's 4.50:1 floor — most of a night's check-ins land inside that span, and currentColor is what is meant to keep them readable there`

**M19 after the fix** — `in en the band's canvas is 160.00px tall, not the 24.00px .day-band declares — at .drawing__canvas's own 160px default the day renders as a block rather than a band, which overflows nothing and shows up nowhere else`

## Checks that failed the vacuity question, and what was done

Three, one per task.

1. **M4 (task 1).** Four checks, all ceilings; the "band shows too little"
   defect class entirely unmeasured. Fixed by asserting the FLOOR — no
   interior gap and no unmarked tail may reach the minimum spacing — and
   by correcting the docstring, whose recorded rationale was false.
   Strengthened an existing check, so the count did not move.

2. **M15 (task 2).** No check seeded a day dense enough to trigger a
   collapse, so T-24-06-B's page half — the caption admitting a merge —
   was documented and unmeasured. Fixed by seeding a 300-check-in day and
   asserting the merge sentence appears there **and does not appear** on
   the sparse day (M16 is that second direction). Strengthened an existing
   check; the count did not move.

3. **M19 (task 3).** `--drawing-canvas-height: 24px` on `.day-band` is
   load-bearing and was invisible to every check: removing it overflows
   nothing, moves no mark, changes no colour, and silently takes
   `.drawing__canvas`'s 160px default — the day rendering as a 6.7x
   taller block. This is 24-05's `grid-column: 1 / -1` finding repeating
   exactly. The property is **not** inert; the checks were blind. Fixed by
   asserting the canvas's rendered height.

Also recorded: **M11 was a bad mutation of mine**, not a surviving one. It
moved the single read into the call expression rather than duplicating it,
so the read count was correctly still 3. Replaced with M11b, which
genuinely adds a second read and reddens.

## Plan assumptions that turned out wrong

Three, all recorded rather than quietly adjusted.

1. **`device_config.quiet_hours_status()` cannot be the window's source.**
   The plan's binding constraint names it. It returns
   `(seconds_remaining, end_hm)` — an *activity* status answering "are
   quiet hours on right now and when do they end". The band needs the
   window's two ENDS whether or not it is currently active, which that
   accessor cannot give. `_quiet_hours_window()` reuses that accessor's
   own derivation one level down — the `is True` enabled test and
   `normalise_quiet_hours_time()` — rather than inventing a second path.
   No time literal appears in the new code.

2. **The named Paris/UTC boundary case cannot occur.** The plan's
   acceptance criterion asks for "a check-in at 23:30 Paris on a date
   whose UTC instant falls on the next day". Europe/Paris is UTC+1/+2 and
   so is never *behind* UTC: 23:30 Paris is 21:30Z or 22:30Z on the *same*
   UTC date. The implemented and asserted case is the mirror, which is the
   same defect from the other side — 00:30 Paris is 22:30Z on the
   *previous* day — and the check pins both directions at once, so a UTC
   bucket both drops today's 00:30 and picks up tomorrow's.

3. **The band is 278px wide at the 360px floor, not ~330px.** The plan
   states ~330px twice and Task 1's constant did its arithmetic against
   it. Measured in Chromium: **278.00px**. Every figure derived from the
   estimate was wrong with it — 1.2% of 278px is 3.34px centre to centre,
   not the 4px the derivation set out to buy. Corrected below.

## Properties found inert

**None.** M19 looked like an inert property and is not one — it is
load-bearing and was unmeasured. Nothing added by this plan was deleted
as inert.

## Corrections made during execution

- **`DAY_BAND_MIN_MARK_SPACING_PERCENT` 1.2 → 1.5.** Re-derived from the
  measured 278px: 4 / 278 = 1.4388%, rounded **UP** (not down, as the
  first draft did) because this is a floor on legibility and rounding down
  would permit exactly what the constant exists to prevent. Consequences,
  all re-measured by running: two marks at the minimum sit 4.17px apart
  with 2.17px of clear ground; the element-count ceiling is 67 marks and
  not 84 (T-24-06-C); the finest resolvable interval on a 24-hour day is
  ~22 minutes, not ~17. The browser check now re-derives the constant from
  the canvas's measured width, so the estimate and the layout cannot drift
  apart again.
- The `day_band()` docstring's dense-day figures re-measured: 1 440
  check-ins draw 66 marks from 0.00% to 99.31% (was recorded as 80 marks
  to 98.75% under the old constant).
- The unreadable-database case is exercised by placing a **directory**
  where `history.db` belongs, not by `chmod`. This container runs as root,
  where a 0o500 state dir is not read-only at all — the same reason the
  four WR-11 baseline checks fail here and pass in CI. sqlite cannot open
  a directory whoever you are, so the check measures the same degradation
  in both environments.
- Task 3's two checks own an **isolated `Harness()`**. The shared fixture
  seeds `device_health` only for the 40 days before `SEED_BASE_TS`, so on
  any real wall clock the band's own Paris day holds not one mark to
  measure; adding today's rows to `seed_state_dir()` would have handed
  24-05's battery chart a 41st day bucket it does not expect.

## Measurements recorded

Resolved paint, both themes (six values, none the SVG default):

| Shape | Light | Dark |
|-------|-------|------|
| `.drawing-band` (frame) | `color(srgb 0.87451 0.843137 0.784314 / 0.4)` | `color(srgb 0.164706 0.188235 0.25098 / 0.4)` |
| `.drawing-band-span` | `rgb(223, 215, 200)` | `rgb(42, 48, 64)` |
| `.drawing-band-mark` | `rgb(23, 25, 31)` | `rgb(241, 243, 246)` |
| card behind it | `rgb(255, 255, 255)` | `rgb(21, 25, 34)` |

Composited contrast (shipped values against the check's floors):

| Pair | Light | Dark | Floor |
|------|-------|------|-------|
| frame vs card | 1.148:1 | 1.106:1 | 1.05 |
| span vs the band's own surface | 1.246:1 | 1.208:1 | 1.15 |
| mark vs the shaded span it crosses | 12.292:1 | 11.842:1 | 4.50 |

Geometry at the 360px floor (identical in English and French):

- canvas **278.00 x 24.00px**; without `--drawing-canvas-height` it is
  278.00 x **160.00px**
- marks **2.00 x 24.00px** each, all five inside the canvas
- shaded spans 81.09px and 11.59px, both inside the canvas
- body overflow: **PASS** in both languages, at 360px
- scripts blocked: 1 frame, 2 spans, 5 marks, all still painting
  dark-mode tokens

## Threat register

| Threat | Disposition | Where it is asserted |
|--------|-------------|----------------------|
| T-24-06-A | mitigated | `percent_time()` rejects rather than clamps; unparseable instants are dropped, not positioned (M2) |
| T-24-06-B | mitigated | the emitter returns `collapsed`; the caption is asserted against it in both directions (M15, M16) |
| T-24-06-C | mitigated | 67-mark ceiling bounded by the band's width, asserted at 60s and 1s cadences (and now its floor too, M4) |
| T-24-06-D | mitigated | `_safe_query()` at every read; asserted with `history.db` unreadable (M12 neighbour) |
| T-24-06-SC | n/a | this plan installed zero packages in any ecosystem |

No new security surface was introduced: the band is server-rendered SVG
over data already read, with no new route, no new input and no script.

## Scope honoured

Detections are **not** plotted (24-RESEARCH.md open decision 5). Two mark
vocabularies in 278px is unreadable, and that remains a decision to be
recorded rather than a quiet addition.

No requirement was ticked. `STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md`
are untouched, as 24-01…24-05 each left them; CFG-39…CFG-45 belong to the
closing plan.

## Re-derived check counts, obtained by RUNNING

| Harness | Before | After |
|---------|--------|-------|
| `test_view_pages.py` | 154 | **161** (+4 task 1, +3 task 2) |
| `test_browser_ux.py` | 59 | **61** (+2 task 3) |
| `test_companion_app.py` | 300 | 300 (unchanged) |
| `test_status_pages.py` | 291 | 291 (unchanged — this plan does not touch Health) |
| `test_i18n.py` | 24 | 24 (unchanged) |
| `test_config_page.py` | 240 | 240 (unchanged) |
| `test_contrast_check.py` | 43 | 43 (unchanged) |

The two strengthening fixes (M4's floor, M15's collapse caption) moved no
count: both hardened existing checks rather than adding new ones.

## Final state

`./scripts/run-all-tests.sh` → the failing set is **exactly** the 5
sandbox baseline names, verified by NAME, with no sixth:

1. `POST /airlines/resolve redirects with the manual_save_failed flash key … (WR-11)`
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)`
3. `add_entry() returns ADD_FAILED (never raises) … read-only … (WR-11)`
4. `delete_entry() returns False (never raises) … read-only … (WR-11)`
5. `anomaly_active() runs on every page render and must never raise …`

Neither intermittent failure recorded in `deferred-items.md` (the 0.19px
reminder-ceiling overshoot, the pre-transition crossfade sample) appeared
in any run, clean or mutated.

`ruff check .` clean throughout.

## Commits

| Commit | Task | Message |
|--------|------|---------|
| `2760f0c` | 1 RED | `test(24-06): failing checks for a time-domain scale and a day band` (inherited from the killed executor) |
| `c0686bb` | 1 GREEN | `feat(24-06): a time-domain scale, and the day drawn at its real width` |
| `2fea55d` | 2 RED | `test(24-06): failing checks for the day band on Home` |
| `6c7a8a2` | 2 GREEN | `feat(24-06): Home shows the day the frame has had` |
| `390c13a` | 3 | `test(24-06): the day band measured at 360px, both themes, scripts blocked` |

Nothing is pushed; the orchestrator pushes. No model identifier appears in
any artifact outside the sanctioned commit trailer.

## Self-Check: PASSED

All six modified files present, all five commits resolve, and
`STATE.md` / `ROADMAP.md` / `REQUIREMENTS.md` are unmodified.
