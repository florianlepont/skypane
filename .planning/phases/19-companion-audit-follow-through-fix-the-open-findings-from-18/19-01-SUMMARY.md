---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 01
subsystem: ui
tags: [companion, health-page, accessibility, wcag, battery-estimate]

# Dependency graph
requires:
  - phase: 18-companion-audit-and-ux-refactor
    provides: the Health page's stat-tile grid, home_page.py's original battery_percent() and verdict-dict idiom, this plan builds on top of
provides:
  - companion/battery.py — a new shared, page-independent module owning BATTERY_FULL_MV/BATTERY_EMPTY_MV/battery_percent()
  - Health's battery readout and every sparkline point now show "≈ NN% · NNNN mV" (D-01/A-19)
  - Health's Device/Pipeline/Corroboration stat tiles each render a text verdict beside their status border colour (D-03/A-21, WCAG 1.4.1)
affects: [19-05, 19-06, 19-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared, page-independent module (companion/battery.py) as the fix for two page modules needing one estimate without importing each other"
    - "Verdict dict + '<p class=\"text-body widget-verdict\">' paragraph idiom, now used by both home_page.py and health_page.py"

key-files:
  created:
    - companion/battery.py
  modified:
    - companion/pages/home_page.py
    - companion/pages/health_page.py
    - companion/test_view_pages.py
    - companion/test_status_pages.py

key-decisions:
  - "D-01/A-19: battery_percent() moved verbatim into companion/battery.py, a stdlib-only module beside companion/auth.py/layout.py/screens.py, never inside companion/pages/ — this is what lets home_page.py and health_page.py share one estimate without either importing the other"
  - "D-01: the percentage change lands in health_page._battery_reading_parts() alone (not _battery_readout_block()), so the resting readout, every sparkline point's tooltip/aria-label/data-when attribute all carry the same estimate by construction, with zero change needed to companion/static/battery-trend.js"
  - "D-03/A-21: verdict text lives in three new dicts (DEVICE_STATE_TEXT/PIPELINE_STATE_TEXT/CORROBORATION_STATE_TEXT) modelled on home_page.py's own FRAME_STATE_TEXT/DATA_STATE_TEXT/BATTERY_STATE_TEXT; the Resolution-rate tile is a deliberate, documented exception (status=None, no status function exists for it, so no verdict word is invented)"

requirements-completed: [CFG-03]

# Metrics
duration: 17min
completed: 2026-09-11
---

# Phase 19 Plan 01: Health battery percentage + stat-tile text verdicts Summary

**Health now shows a shared "≈ NN% · NNNN mV" battery estimate (sourced from a new companion/battery.py) and every Device/Pipeline/Corroboration stat tile states its verdict in words, not just its border colour (D-01/D-03, WCAG 1.4.1).**

## Performance

- **Duration:** 17 min (2026-09-11T06:51:28Z start of phase execution → 2026-09-11T07:05:47Z last task commit)
- **Started:** 2026-09-11T06:56:57Z (Task 1 commit)
- **Completed:** 2026-09-11T07:05:47Z
- **Tasks:** 3/3 complete
- **Files modified:** 5 (1 new: companion/battery.py)

## Accomplishments
- Closed A-19 (D-01): a household member reading Health now sees the battery as a percentage ("≈ 62%") beside the millivolt figure, matching what Home already showed — and both pages now consume one shared estimate from `companion/battery.py`, with neither page module importing the other.
- Closed A-21 (D-03): Health's Device, Pipeline and Corroboration stat tiles each state their verdict in words ("Checking in normally", "A little behind", "Sources disagreed recently", etc.) beside their existing status-coloured border, meeting WCAG 1.4.1 (colour is never the sole carrier of the signal). The Resolution-rate tile is a deliberate, documented exception.
- Zero new CSS: both changes reuse existing classes (`battery-readout__value mono`, `widget-verdict`) and existing design tokens — no new selector, custom property or accent consumer was added.

## Task Commits

Each task was committed atomically:

1. **Task 1: Move battery_percent() into a shared companion/battery.py** - `605f778` (feat)
2. **Task 2: Show the battery percentage beside the millivolt readout on Health (D-01)** - `2976b87` (feat)
3. **Task 3: Give every Health stat tile a text verdict (D-03, WCAG 1.4.1)** - `2a76a73` (feat)

_No plan-metadata commit yet — SUMMARY.md and this plan's metadata commit follow this file's own creation, per worktree-mode instructions._

## Files Created/Modified
- `companion/battery.py` - New shared, page-independent module: `BATTERY_FULL_MV`/`BATTERY_EMPTY_MV`/`battery_percent()`, moved verbatim from home_page.py
- `companion/pages/home_page.py` - Imports `companion.battery as battery`; its own three moved names deleted; the one call site retargeted to `battery.battery_percent(...)`
- `companion/pages/health_page.py` - `_battery_reading_parts()` now returns `"≈ NN% · NNNN mV"` (falls back to bare `"NNNN mV"` when the estimate can't be computed); three new verdict dicts; `_device_section()`/`_pipeline_section()` prepend a verdict paragraph; `render()`'s Corroboration tile gains the same, keyed on the identical expression driving its status border
- `companion/test_view_pages.py` - Retargeted the existing `battery_percent` check onto `battery.battery_percent`; added two boundary checks (function gone from `home_page`, `companion/battery.py` never mentions the pages package or the server package); `EXPECTED_CHECK_COUNT` 65 → 67
- `companion/test_status_pages.py` - Added three checks for the percentage estimate (Task 2) and five checks for the stat-tile verdicts (Task 3); `EXPECTED_CHECK_COUNT` 163 → 171

## Decisions Made
- The estimate change lives entirely inside `_battery_reading_parts()`, never `_battery_readout_block()` or `companion/static/battery-trend.js` — this is what makes the resting readout and every chart point's tooltip/aria-label/data-when carry the same value by construction, per the plan's own explicit instruction.
- `_daily_reading_parts()` (the chart's daily-average series) was deliberately left untouched — the plan scoped the percentage change to `_battery_reading_parts()` only, and a daily average across many readings isn't the same "one reading's estimate" this task is about.
- The Corroboration tile's verdict is keyed on `"warn" if disagreement_warn else "ok"` — the exact same expression already passed as that tile's `status` argument — so the verdict word and the border colour can never disagree.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_battery_reading_parts()`'s millivolt formatting switched from `%d` to `%s` for the non-numeric fallback path**
- **Found during:** Task 2
- **Issue:** The plan's own Task 2 acceptance criteria and action text require a harness check that passes a non-numeric `mv` into `_battery_reading_parts()` and asserts the value text stays free of "≈" — but the original line `value = "%d mV" % mv` raises `TypeError` for a genuinely non-numeric `mv` (e.g. a string), which would make that exact check impossible to write without first fixing the formatting.
- **Fix:** Changed both branches (`pct is not None` and the fallback) to format `mv` with `%s` instead of `%d`. For every existing numeric `mv` value (always an `int` from the DB or test fixtures) this produces byte-identical output; it additionally tolerates a non-numeric `mv` without raising. The new Task 2 checks use `mv=0` (numeric, but `battery.battery_percent(0)` returns `None` per its own `<= 0` guard) as the concrete "no estimate" fixture, since it exercises the None-percentage path without depending on whether `%s` vs `%d` is the safer choice for a truly non-numeric input — both are now handled.
- **Files modified:** companion/pages/health_page.py
- **Verification:** `companion/test_status_pages.py` — 170/171 pass (the one documented pre-existing sandbox failure), including the three new percentage-estimate checks.
- **Committed in:** `2976b87` (Task 2 commit)

**2. [Rule 1 - Bug] Reworded `companion/battery.py`'s docstring to avoid an unintended match on the plan's own grep-based acceptance criterion**
- **Found during:** Task 1
- **Issue:** The plan's acceptance criteria run `grep -c "companion.pages" companion/battery.py` as a regex (where `.` matches any single character), expecting `0`. A docstring written in the natural, expected house style — explaining the boundary by name, e.g. "not inside `companion/pages/`" — incidentally matches that regex (the `/` and even a literal space both satisfy `.`), producing a nonzero count purely from prose, with no actual import.
- **Fix:** Reworded the docstring to describe the same boundary without ever placing "companion" immediately adjacent (within one character) to "pages" — e.g. "the pages package under companion" became "the per-tab pages package this companion service ships" / "the pages package". The substantive Python check added to `companion/test_view_pages.py` (`_battery_module_never_imports_pages_or_server`) uses literal Python substring containment (`"companion.pages" in source`), which correctly distinguishes real import statements from prose either way — this rewording was purely to satisfy the plan's own shell-level acceptance criterion, not a functional change.
- **Files modified:** companion/battery.py
- **Verification:** `grep -v '^#' companion/battery.py | grep -c "companion.pages"` outputs `0`; `companion/test_view_pages.py`'s boundary check passes.
- **Committed in:** `605f778` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - bug/acceptance-criteria fixes required to make the plan's own instructions internally consistent)
**Impact on plan:** Both fixes were necessary to satisfy the plan's own stated acceptance criteria and test instructions; neither changes the plan's intent or scope.

## Issues Encountered

- **home_page.py has only one `battery_percent()` call site, not two.** The plan's Task 1 `<read_first>`/`<interfaces>` sections and acceptance criteria (`grep -c "battery.battery_percent" companion/pages/home_page.py` expects `2`) describe "both call sites at lines ~191 and ~197" — but reading the live file (both before and after this task) shows exactly one actual call (`pct = battery_percent(reading["battery_mv"])` at line 191); line 197 only *consumes* the already-computed `pct_text` variable, it does not call the function a second time. This was retargeted as the single real call site it is; the acceptance criterion's expected count of `2` does not match the ground-truth code and is flagged here rather than silently "fixed" by duplicating a call for no functional reason. `grep -c "battery.battery_percent" companion/pages/home_page.py` currently outputs `1`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/battery.py` now exists as the shared estimate module Health's audit follow-through (D-01) needed; plans 19-05/19-06/19-09 (the other Health-page fixes in this phase's Wave) can build on it without re-deriving the boundary.
- The `widget-verdict` paragraph idiom is now proven in a second page module (health_page.py, after home_page.py); any future stat-tile-bearing page can copy the same three-line pattern (dict + prepended `<p class="text-body widget-verdict">`) rather than inventing a new one.
- No blockers. `scripts/run-all-tests.sh` run in full: only the five documented pre-existing root-sandbox failures (2 in `companion/test_companion_app.py`, 2 in `server/test_manual_resolutions.py`, 1 in `companion/test_status_pages.py` — all read-only-directory/`anomaly_active()` cases that fail identically on untouched main because this sandbox runs as root) appear; zero new failures.

## Self-Check: PASSED

All created/modified files verified present on disk (companion/battery.py, companion/pages/home_page.py, companion/pages/health_page.py, this SUMMARY.md); all three task commits (605f778, 2976b87, 2a76a73) verified present in git log.

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Completed: 2026-09-11*
