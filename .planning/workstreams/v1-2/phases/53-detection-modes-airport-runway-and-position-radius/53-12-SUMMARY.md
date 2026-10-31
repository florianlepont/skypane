---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 12
subsystem: companion-tests
tags: [tests, detection, display]
requires: [53-09]
key-files:
  modified:
    - companion/test_companion_app_04.py
    - companion/test_user_health.py
    - companion/test_user_view_http.py
requirements-completed: [DET-01]
completed: 2026-10-31
---

# Phase 53 Plan 12: Re-point the remaining tests to the Detection card Summary

The five non-browser tests that asserted the removed Display Runway card now assert the new behaviour, and the whole non-browser companion suite is green.

## Commits

- fef3728 re-point Display tests to the Detection card and ignored tracked_runway

## Per-file outcome

- `test_companion_app_04.py`: the scoped-save test posts `tracked_runway=06-24` from the Device scope and asserts the stored value is unchanged (value read before the post); the page-split test asserts Display and Device carry no `tracked_runway` field and Display shows the Detection card. All other assertions kept.
- `test_user_health.py` (en, fr): the removed `RUNWAY_GROUP_HEADING_ID` check became a Detection-card presence check; the admin Display page now asserts no `tracked_runway` field and a Detection card. The ADMIN_ONLY field loop is kept.
- `test_user_view_http.py`: the admin Display page asserts no `tracked_runway` field and a Detection card; user-side absence checks kept.
- `test_airline_sheet`, `test_companion_app_05`, `test_device_dispatch`, `test_device_pages`, `test_display_looks`, `test_freshness_token`, `test_user_view`, `test_view_pages_01/02`: no change needed (they only seed `tracked_runway` as data and pass).
- Test-support helpers (`companion_render_snapshot.py`, `efficiency_probe.py`, `provisioned_fleet.py`): only seed `tracked_runway` into device_config storage; no change. Regenerating the render baseline (`PYTHONPATH=. ... --write`) leaves no diff.

## Verification

- `pytest companion -m "not browser" -n auto`: 3812 passed, 3 skipped (root-permission skips), 0 failed.
- `pytest test-support companion/test_render_baseline.py stub-server/test_phase47_freeze.py`: 233 passed.
- ruff clean, mypy clean (28 files), function-size gate (905 functions, none over 80), comment-history check exit 0. `git diff stub-server/` empty.

## Deviations from Plan

None of substance. Task 2 needed no file change, so it has no commit. The snapshot script needs `PYTHONPATH=.` when run directly.

## Known Stubs

None.

## Self-Check: PASSED

Commit fef3728 present. STATE.md and ROADMAP.md were not touched.
