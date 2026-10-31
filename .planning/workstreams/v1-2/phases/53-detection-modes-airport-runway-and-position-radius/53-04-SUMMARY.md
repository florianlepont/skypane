---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 04
subsystem: detection
tags: [device-config, expand-only, selection-api]
requires: [53-03]
provides:
  - server/device_config.py (normalise_detection, CLEAR_DETECTION, twelfth loaded key "detection", three-state save)
  - server/detection.py (validate_runway_selection, validate_radius_km, apply_runway_selection, apply_position_selection, current_selection)
affects: [53-05]
key-files:
  modified:
    - server/device_config.py
    - server/detection.py
    - server/test_runway_config.py
    - server/test_retired_notifications.py
    - server/test_config_history.py
  created:
    - server/test_detection_settings.py
requirements-completed: [DET-01, DET-03]
completed: 2026-10-31
---

# Phase 53 Plan 04: Detection setting storage and selection API Summary

The `detection` key is stored expand-only (written only when set, like `timezone`), and `server/detection.py` gives the page one validated read/write API in which Orly runways keep the legacy `tracked_runway` id.

## Commits

- 04db706 detection key in device_config with three-state save
- 36548cf selection validation and apply helpers in detection

## Behaviour

- `normalise_detection` is shape-only (ICAO and designator regexes, real int radius), returns a fresh dict of known keys or None, never raises; `device_config` still imports neither `airports` nor `detection`.
- `save_device_config(detection=...)`: None carries forward, `CLEAR_DETECTION` removes the key, an object sets it; a bad shape raises ValueError before any write (pre-existing file stays byte-identical, tested).
- `apply_runway_selection` for LFPO 07/25, 06/24, 02/20 writes `tracked_runway` 3, 06-24, 02-20 and clears `detection`; saving an unchanged legacy setting leaves the file bytes identical (tested). Any other runway writes one detection object and leaves `tracked_runway` alone. `apply_position_selection` stores only `{mode, radius_km}`.
- Error codes: "airport", "runway", "radius". All apply paths validate first and write once.
- Rollback note (T-53-18, accepted): the previous release keeps running on `tracked_runway`; a save by that release drops the `detection` key and the device returns to its last Orly runway.

## Tests examined for the twelfth key

Changed: `server/test_retired_notifications.py` (key count 12), `server/test_config_history.py` (seven whole-dict assertions and three fixture dicts gained `"detection": None`). Examined and unchanged: `server/test_state_writers.py`, `server/test_poll_loop.py`, `server/test_calendar_rules.py`, `server/test_enrich.py`, `server/test_poll_cycle_profile.py`, `stub-server/test_wake_interval_delivery.py`, and the companion tests that call `load_device_config` (they assert individual keys). `server/test_detection_spec.py` needed no change.

## Verification

- `pytest server stub-server/test_phase47_freeze.py -n auto`: 2234 passed, 3 skipped (root permission tests); includes `test_orly_replay.py` and the unmodified Phase 47 freeze test.
- ruff clean, mypy clean (28 files), function-size gate passes (902 functions), comment-history check passes.

## Deviations from Plan

None. `server/test_detection_spec.py` was listed in the plan but needed no edit.

## Known Stubs

None.

## Self-Check: PASSED
