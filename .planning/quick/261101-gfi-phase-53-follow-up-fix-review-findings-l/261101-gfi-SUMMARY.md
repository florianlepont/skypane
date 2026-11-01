---
phase: quick-261101-gfi
plan: 01
subsystem: detection
tags: [review-fixes, csrf, fleet, locations]
requirements-completed: [LW-01, LW-03, LW-04, LW-06]
key-files:
  modified:
    - server/detection.py
    - server/poll_cycle.py
    - server/fleet_cycle.py
    - server/zone_fetch.py
    - server/fleet_db.py
    - companion/detection_actions.py
    - companion/console_locations.py
    - companion/pages/detection_page.py
    - companion/routes.py
completed: 2026-11-01
---

# Quick 261101-gfi: Phase 53 review follow-up Summary

Four low-severity Phase 53 review findings fixed, one commit each, full gate green.

## Commits

- 51b88552 fix(detection): LW-01 keep one fail-safe rule
- 9a1c1678 fix(fleet): LW-03 never gate a fetch of another zone
- 9e5d884e fix(locations): LW-04 refuse cross-owner device/location links
- 3bd5cdac fix(detection): LW-06 require the CSRF token on the detection and location forms
- 01e3c247 docs(53): record review fixes

## What changed

- LW-01: removed the dead `fail_safe` field and parameters from `DetectionSpec`; the detail page uses `detection_summary.is_fail_safe`. Spec tests assert display id/zone; the existing toast shown/hidden tests cover the page.
- LW-03: `ZoneFetch.zone_key` stamp (fleet and standalone fetch); `_select_from_zone` raises `StaleZone` before selecting; fleet records `stale_zone` (not busy/failed, exit status unchanged). New tests fail when the comparison is disabled.
- LW-04: `set_device_location_checked` refuses a location owned by a different user than the device owner (admins included); `scope_for` withholds the location name from non-admin non-owners. Tests for admin refusal, ownerless location, forged admin POST/edit, name leak.
- LW-06: `POST /detection` added to `CSRF_ROUTE_KEYS`; `csrf_field()` in both forms; test helpers post with the token; new missing-token, foreign-token and form-content tests.

## Deviations

1. [LW-04 scope] The Phase 55 admin Display picker listed every location and a Phase 55 test asserted "an admin may assign any location". Audit found no flow that needs a cross-owner link (callers: detection POST, Display picker; pairing, console frame edit and ownership transfer never assign one), so the picker now lists only the frame owner's and ownerless locations, and the Phase 55 tests were converted to the new rule.
2. [LW-03] Fleet tests that compared fetch results by identity now compare ignoring the stamp (`_unstamped`); one real-cycle test with a stub resolver unrelated to device settings strips the stamp.
3. [LW-06] test_access_matrix.py needed no change: its POST helper already sends the token for every route; test_csrf.py route-count assertion updated from 6 to 7.
4. No Phase 47 freeze command exists in scripts/ or workflows; confirmed instead that the diff touches nothing under hardware/, stub-server/, deploy/ or Phase 47 files.

## Verification

ruff, mypy, function-size (max 80), comment-history clean. Full gate: `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` 8136 passed, 8 skipped (root-permission skips), coverage gate unchanged and passing.

## Self-Check: PASSED
