---
phase: quick-260923-gaf
plan: 01
subsystem: battery-estimate
tags: [companion, server, battery, discharge-curve, piecewise-interpolation, seed-006]

requires:
  - phase: 05-low-battery-indicator
    provides: DEVICE-05's completed discharge run (hardware/BATTERY-RUN.md's Discharge Trend section) — this plan's data source
provides:
  - "companion/battery.py's BATTERY_DISCHARGE_CURVE: a 14-knot piecewise millivolt-to-percent lookup replacing the linear 4.2V-full/3.3V-empty estimate"
  - "server/poll_loop.py's byte-identical private copy (_NOTIFY_BATTERY_DISCHARGE_CURVE), with a parity check enforcing agreement"
  - "LOW_BATTERY_DISPLAY_MV derived by inverting the curve (3540 mV, 20%)"
  - "battery_life_estimate()'s FALLING branch projecting in state-of-charge space instead of straight-line millivolts"
  - "SEED-006 closed fulfilled; hardware/BATTERY-RUN.md item 1 and the sketch-findings-skypane skill updated to describe the curve"
affects: [companion-battery-life-card, companion-health-chart, server-notify]

tech-stack:
  added: []
  patterns:
    - "Piecewise lookup table with strict-monotonic knots, walked by 'first segment whose upper bound is at or above the value' and inverted by the same walk over the percent column"
    - "D-27 duplicate-homes parity proven non-vacuous by a mutation test (perturb one knot, assert failure, restore, assert pass) rather than merely asserted equal"

key-files:
  created: []
  modified:
    - companion/battery.py
    - server/poll_loop.py
    - companion/test_companion_app.py
    - server/test_poll_loop.py
    - companion/test_view_pages.py
    - companion/pages/health_page.py
    - companion/pages/config_page.py
    - companion/test_status_pages.py
    - companion/test_config_page.py
    - companion/test_browser_ux_health_drawings.py
    - .planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md
    - hardware/BATTERY-RUN.md
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/data-density.md

key-decisions:
  - "D-SEED006 (user, in chat): piecewise curve over an endpoints-only recalibration — the endpoints-only fix was rejected because it would read 3500 mV as ~48% against the ~15% DEVICE-05 actually observed there."

requirements-completed: [SEED-006, QUICK-260923-gaf]

duration: ~35min
completed: 2026-09-23
status: complete
---

# Quick 260923-gaf: Piecewise battery-percentage curve (SEED-006) Summary

**Replaced the linear 4.2V-full/3.3V-empty battery estimate with a 14-knot piecewise curve derived from DEVICE-05's measured discharge run, in both D-27 homes, with a mutation-proven parity check between them.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-23T12:21:45+02:00
- **Tasks:** 3/3
- **Files modified:** 14

## Accomplishments

- `companion/battery.py` now holds `BATTERY_DISCHARGE_CURVE`, a 14-knot table built from `hardware/BATTERY-RUN.md`'s Discharge Trend rows (percent = share of the run's remaining runtime), with `BATTERY_FULL_MV`/`BATTERY_EMPTY_MV` indexed from its end knots (4112/2946) instead of typed.
- `server/poll_loop.py`'s deliberately-duplicated (D-27) copy — `_NOTIFY_BATTERY_DISCHARGE_CURVE` — performs the identical operations in the identical order; a new harness check enforces table equality and output parity for every integer millivolt 2800-4400, a few non-integer floats, and a hostile input set (None, "", "x", True, NaN, ±inf).
- `LOW_BATTERY_DISPLAY_MV` is now derived by inverting the curve through a new `_curve_mv_at_percent()` helper (3540 mV, 20%) rather than computed off the old linear span (was 3480).
- `battery_life_estimate()`'s FALLING branch now projects remaining days in state-of-charge (fraction) space via `battery_fraction()`, rather than straight-line millivolt extrapolation to `BATTERY_EMPTY_MV` — validated against DEVICE-05 itself (a 2.64-day window projected 6.0 days remaining against 6.2 actual; millivolt extrapolation on the same window said ~21 days).
- All anchor values from the plan's context table were hand-verified against the implementation before writing tests: 4200→100, 4112→100, 4050→94, 4020→92, 4000→90, 3900→67, 3800→47, 3750→38, 3690→32, 3600→25, 3540→20, 3500→15, 3400→9, 3300→6, 3200→4, 3100→3, 3000→1, 2946→0, 2900→0.
- Every downstream comment that described the retired linear span (health_page.py's sparkline Y-range comment, config_page.py's "DEVICE-05 hasn't run" clause, two test fixture comments, the sketch-findings-skypane skill's estimator-facts bullets) was rewritten to describe the piecewise curve that now ships.
- SEED-006 is closed `fulfilled` following SEED-003's convention (commit 6565155); `hardware/BATTERY-RUN.md`'s Calibration & Follow-Up Findings item 1 records the outcome and the rejected endpoints-only alternative with its concrete 48%-vs-15% reasoning.

## Task Commits

Each task was committed atomically:

1. **Task 1: Piecewise curve in both homes, SoC-space life estimate, parity checks, and retargeted value tests** - `e3ce343` (feat)
2. **Task 2: Make downstream comments true again, extend the pages ban, run the full suite** - `93a75e7` (docs)
3. **Task 3: Close SEED-006, annotate BATTERY-RUN.md, and refresh the design-system skill's estimator facts** - `fb32d84` (docs)

_No separate plan-metadata commit — the orchestrator commits STATE.md/ROADMAP.md/this SUMMARY per the quick-task protocol._

## Files Created/Modified

- `companion/battery.py` - BATTERY_DISCHARGE_CURVE (14 knots), indexed FULL/EMPTY_MV, `_curve_mv_at_percent()`, NaN-refusing `battery_fraction()`/`battery_percent()`, SoC-space `battery_life_estimate()` FALLING branch
- `server/poll_loop.py` - `_NOTIFY_BATTERY_DISCHARGE_CURVE` (byte-identical table) and a rewritten `_battery_percent_estimate()` performing the same operations
- `companion/test_companion_app.py` - one-home scan widened to govern `*_DISCHARGE_CURVE` names and either endpoint pair; two new checks (curve well-formedness, D-27 parity); life-estimate check retargeted to SoC space + above-curve case; EXPECTED_CHECK_COUNT 317→319
- `server/test_poll_loop.py` - check #68 extended to assert the notification body's curve percentage and `_battery_percent_estimate(3400) == 9`
- `companion/test_view_pages.py` - Home/ring/clamp needles retargeted to curve values (38%, 32%, BATTERY_FULL/EMPTY_MV-qualified clamps); banned-token tuple extended with the curve's own name/endpoints
- `companion/pages/health_page.py` - sparkline Y-range comment rewritten (display window vs. curve, no more "agrees by construction")
- `companion/pages/config_page.py` - "DEVICE-05 hasn't run" clause corrected to "ran, but the per-wake/standing-leakage split is unresolved"
- `companion/test_status_pages.py` - health-ring fixture comment retargeted to 32%
- `companion/test_config_page.py` - banned-identifiers tuple gains `BATTERY_DISCHARGE_CURVE`
- `companion/test_browser_ux_health_drawings.py` - French legend example updated to 3540 mV
- `.planning/seeds/SEED-006-recalibrate-battery-percentage-constants.md` - status `fulfilled`, resolved_date, closing paragraph
- `hardware/BATTERY-RUN.md` - item 1's placeholder fixed and an Outcome paragraph appended
- `.claude/skills/sketch-findings-skypane/SKILL.md` / `references/data-density.md` - estimator-facts bullets updated (curve, derived display mV, parity check, 0.0024 ring disagreement)

## Decisions Made

- D-SEED006 (user, in chat, cited by the plan): ship the piecewise curve rather than an endpoints-only recalibration. The endpoints-only alternative was explicitly rejected in both SEED-006's closing note and BATTERY-RUN.md's outcome paragraph, with the concrete counter-example (3500 mV → ~48% under endpoints-only vs. ~15% actually observed).

## Deviations from Plan

None — plan executed exactly as written, including the mutation proof and the browser-harness investigation protocol below.

## Mutation Proof (non-vacuous parity check)

Per the plan's action item, the parity check was proven non-vacuous rather than merely written:

1. Temporarily changed one knot in `server/poll_loop.py`'s `_NOTIFY_BATTERY_DISCHARGE_CURVE` — `(3500, 15)` → `(3500, 16)`.
2. Re-ran `companion/test_companion_app.py`: dropped from 319/319 to **318/319**, with the new parity check failing and naming the exact cause: *"companion.battery.BATTERY_DISCHARGE_CURVE != poll_loop._NOTIFY_BATTERY_DISCHARGE_CURVE — the D-27 duplicate has drifted."*
3. Restored the original file byte-for-byte and re-ran: back to **319/319**.

## Final Check Counts

| Harness | Count |
|---|---|
| `companion/test_companion_app.py` | 319/319 |
| `server/test_poll_loop.py` | 99/99 (unchanged) |
| `companion/test_view_pages.py` | 169/169 (unchanged) |
| `companion/test_status_pages.py` | 316/316 (unchanged) |
| `companion/test_config_page.py` | 276/276 (unchanged) |
| `ruff check .` | clean |
| `./scripts/run-all-tests.sh` coverage gate | 93% total, pyproject's `fail_under = 83` cleared |

## Browser-Harness Flake Diagnosis

`./scripts/run-all-tests.sh` reported one failing harness: `companion/test_browser_ux.py` (73/75). Both failures are unrelated to battery/SEED-006:

1. `expected the typed value to be held by the field before any commit` (dirty-state leave-guard check, ~line 2223).
2. `expected the field to echo back the user's own rejected input '30', got '301800'` (wake-interval-s server-validation echo check, ~line 8234) — the field's prior `'1800'` content appears concatenated with the typed `'30'` rather than replaced.

Per the plan's protocol, this was investigated rather than dismissed:
- Re-ran `companion/test_browser_ux.py` standalone twice — identical 73/75 with the identical two failure messages both times (reproducible, not an intermittent flake).
- Created a throwaway detached `git worktree` at this quick task's own Task 1 commit (`e3ce343` — battery.py/poll_loop.py and their tests only, none of Task 2's comment-only edits) and re-ran the harness there: **the same two checks fail, byte-identically**, proving the failure predates this quick task entirely.
- Neither failing check's subject (the dirty-state bar, the wake-interval-s field) is touched anywhere in this quick task's diff.
- Logged in `.planning/quick/260923-gaf-seed-006-piecewise-battery-percentage-cu/deferred-items.md` per the SCOPE BOUNDARY rule (pre-existing, out-of-scope failures are not auto-fixed) rather than fixed here.

## Issues Encountered

None beyond the browser-harness investigation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Battery percentage everywhere in the companion (Home, Health, the ring gauges, the low-battery notification, the life-estimate card, the config battery sentence) now reflects DEVICE-05's real discharge curve rather than an assumed linear span.
- `companion/test_browser_ux.py`'s two pre-existing failures (dirty-state guard / wake-interval-s echo) remain open and are logged in `deferred-items.md` — worth a follow-up quick task or seed, unrelated to this one.

## Self-Check: PASSED

All 16 files listed in Files Created/Modified plus the two quick-task artifacts were confirmed present on disk, and all three task commits (`e3ce343`, `93a75e7`, `fb32d84`) were confirmed present in `git log --oneline --all`.

---
*Phase: quick-260923-gaf*
*Completed: 2026-09-23*
