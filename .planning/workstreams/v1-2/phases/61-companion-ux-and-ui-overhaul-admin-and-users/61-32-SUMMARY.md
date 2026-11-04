---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 32
subsystem: companion
tags: [tests, step-counts, sweep, traceability, final-gate]
requires: [61-17, 61-18, 61-19, 61-20, 61-21, 61-22, 61-23, 61-24, 61-25, 61-26, 61-27, 61-28, 61-29, 61-30, 61-31, 61-33, 61-34]
provides: [revision 2 step-count record, revision 2 cross-page sweep, V/D/R traceability, full-suite gate]
key-files:
  modified:
    - companion/test_browser_overhaul_steps.py
    - companion/test_browser_overhaul_sweep.py
    - companion/static/style.css
    - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-STEP-COUNTS.md
    - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-TRACEABILITY.md
    - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-OWNER-DECISIONS.md
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 32: Revision 2 evidence and the final gate Summary

Measured the revision 2 step counts in Chromium (three targets missed, all on the Location page), extended the cross-page sweep to every new page and dialog and to the Home notification (455 cases), wrote the V0-V10 / D16-D25 / R1-R28 traceability with its deviations, and ran `./scripts/run-all-tests.sh` green: 10467 passed, 8 skipped, coverage 96.28% against the 93.0% floor.

## Commits

- 27dd5cc: step tests, sweep, the one product fix (filter chips) and `61-STEP-COUNTS.md`.
- The records commit (traceability, owner-decision ledger, this summary) follows.

## What changed

- **Step counts** (`companion/test_browser_overhaul_steps.py`): U4a, U4b (the old U4 tests, renamed), U4c, L1 to L4, S1, S2, A7, A8, V1 (phone and desktop) added. The revision 2 tests assert the exact measured value and print `STEP-COUNT <task> <n> (target <t>)` with ` MISSED` when over target; U2 with several frames now measures 2 (chip, then card). The map, tile host, Nominatim and geolocation are answered by the test (`Hosts`, context geolocation). `Steps.tap_point` counts a scroll when the tapped map point lies below the fold.
- **Sweep** (`companion/test_browser_overhaul_sweep.py`): 35 page and dialog cases (13 added: Flight history, Location and detection, Airline collection, Airline editor, Personalisation remove-special-look dialog, delete-resolution dialog, frame sheet, quiet-hours dialog for owner and administrator, co-manager Location), the Home notification (12 combinations of state, administrator presence and person, each at 360 and 1280 px, EN and FR, light and dark, plus a French comparison), and an administrator-versus-user comparison of the five personal pages (headings, navigation, controls at both widths; the space switch and the foreign-frame notice are the only difference). The forbidden-word list gained Health and Airline editor; the Locations 360 px test and the "Admin / Administration" word test are removed. Map hosts are routed in every case; pytest-socket stays on.
- **Records**: `61-STEP-COUNTS.md` (first-round table, superseded rows, revision 2 table, measured paths, honest notes), `61-TRACEABILITY.md` (V, D, R tables, sweep description and limits, deviations list, D9/D14/Locations lines marked superseded or removed), `61-OWNER-DECISIONS.md` (R2-1 to R2-20 statuses).

## Measured step counts (360 x 844)

U4a 3 (target 3), U4b 3 (3), U4c 3 (3), **L1 5 (target 4, missed)**, **L2 5 (target 4, missed)**, L3 6 (6), **L4 4 (target 3, missed)**, S1 1 (1), S2 2 (2), A7 1 (1), A8 5 (at least 5), V1 phone 2 (2), V1 desktop 1 (1). A6 stays at 2 (target 1 of the first round), U2 with several frames is 2. The three misses share one cause: on the phone the Location page puts the airport list, the Use my position button and the map at or below the fold (the airport filter about 640 px below it), so each needs the counted scroll. No product change was made to hit a number. L2 counts the browser permission prompt as one modelled step (the context grants it in advance).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Desktop filter chips of Flight history were 43 px high**
- **Found during:** Task 2 (the 1280 px 44 px check now covers all of `main`, not just list rows and page headers)
- **Issue:** `.filter-bar--chips .filter-chip__box` had `min-height: 42px` at 960 px and up; hit-testing measured 43 px.
- **Fix:** `min-height: 44px`. No other defect surfaced; every other new case passed on the first run.
- **Files modified:** `companion/static/style.css`
- **Commit:** 27dd5cc

### Other

- The 1280 px check in the sweep widened from "list and header" to the whole `main`. Not a loosening; existing cases all still pass.
- Sweep exemptions added to the untranslated-text comparison: catalogue names by element class (airlines in the collection and editor, airports in the Location list), and a short pattern for the frame's own heading "Watching Runway 3", airport code lines, "Ryanair" and "Confirmed" (the seeded history's pass state, a value the detector never writes). Each is data, not companion text.
- The orchestrator's note that "the Display page-title and nav label ids differ" could not be confirmed as two message ids: both the page title and the sidebar label use `nav.personalisation`; only the phone bar says "Style" (ledger R2-15). Recorded as such in the traceability.

## V/D/R items only partly met (all recorded in `61-TRACEABILITY.md`)

- R22: four cards on Personalisation, not five (D23).
- R23: L1, L2 and L4 miss their targets.
- V9 / plan 61-28: card titles keep the serif settings-card style instead of the spec's 16 px sans.
- Plan 61-30: Apply on the Airline collection is always visible (no auto-submit script).
- Plan 61-31: the Airline-editor page-height ceiling in `test_browser_ux_01` went from 3900 to 4100 px.
- A6 (Audit log) is two taps; U2 with several frames is two.
- Language, theme and Sign out stay in the gear panel and sidebar footer; "Name this airline" removed for everyone; no Edit on a special look; choosing an airport navigates; co-managers may save a place (R2-19); the three planner-raised rows R2-17 to R2-19 are "owner to confirm".

## Gates

- `./scripts/run-all-tests.sh` (browser tests required, not skipped): 10467 passed, 8 skipped, 0 failed, 14m12s; the 8 skips are root permission-bit tests (7) and one openssl backdating test, none a browser test. Coverage 96.28% (floor 93.0%, not moved).
- `ruff check .`, mypy (29 modules), `check_comment_history.py check`, `check_function_size.py` (931 functions, none over 80), `stub-server/test_phase47_freeze.py` (21 passed): clean.
- Sweep run 3 times in a row with `-n 6` (455 passed each); the steps module run 4 times in parallel processes (23 passed each); the filter-chip browser neighbours (audit, console, flights cards, collection, ux 01/02/04) 142 passed after the CSS change.
- `render_baseline.json`, sign-in digests and goldens did not need to move for the one-line CSS change (the full run passed unchanged).
- No edit to `stub-server/`, `hardware/` or any Phase 47 file.

## Known Stubs

None.

## Threat Flags

None. Tests only, plus one CSS minimum height.

## Self-Check: PASSED
