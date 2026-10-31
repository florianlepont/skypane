---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 03
subsystem: detection
tags: [position-mode, rounding, france-bounds]
requires: [53-02]
provides:
  - server/plane/detect.py (position_candidates, detection_mode dispatch, POSITION_MODE)
  - server/detection.py (position_zone, validate_position, km_to_nm, inside_france, round_coordinate, RADIUS_KM_MIN/MAX, position branch of spec_for)
affects: [53-05]
key-files:
  created:
    - server/test_position_rounding.py
  modified:
    - server/plane/detect.py
    - server/detection.py
    - server/test_plane_detection.py
    - server/test_detection_spec.py
requirements-completed: [DET-03]
completed: 2026-10-31
---

# Phase 53 Plan 03: Position-mode detection Summary

Position mode selects airborne aircraft (0 to 10,000 ft) within a whole-kilometre radius (4 to 28) of the device location, with the centre rounded to 2 decimals at the single `position_zone` choke point.

## Commits

- ba84d5c feat: position candidates and detection_mode dispatch
- eeb4a98 feat: position-mode spec with bounds and one rounding choke point

## Notes

- `runway_candidates` delegates only when `detection_mode == "position"`; `filter_in_geofence` is untouched. `_effective_runway_id` returns the display id unchanged for position documents so `selected_runway` is `position:<km>`.
- Radius edge comparison carries a 1e-6 m float slack; 1 m beyond is rejected.
- `radius_nm` in `server/detection.py` appears only as the geofence/zone document key (lines 142-151, 236, 242); stored config reads and writes use `radius_km` only.
- Bad radius (bool, float, str, outside 4..28), missing/out-of-France/non-finite location all give the legacy "3" spec with `fail_safe` True; `spec_for` never raises for these.
- Provider URL guard test: URLs contain `/lat/48.86/lon/2.35/dist/4.86` and `/point/48.86/2.35/4.86`; no unrounded coordinate in URLs, stdout, stderr or log capture; adsbdb URL has no coordinates. Two nearby devices share one zone key and one fetch pass.

## Verification

- `pytest server stub-server/test_phase47_freeze.py -n auto`: 2171 passed, 3 skipped (root permission tests); includes the Orly replay.
- ruff clean, mypy clean (28 files), function-size gate passes, comment-history check passes, no plan/decision IDs in `server/detection.py`.

## Deviations from Plan

None.

## Known Stubs

None.

## Self-Check: PASSED
