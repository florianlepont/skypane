---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 18
subsystem: server
tags: [fleet-db, locations, frame-position, poll-parity]
requires: []
provides: [fleet_db.save_frame_position, fleet_db.frame_position]
key-files:
  created:
    - server/test_fleet_frame_position.py
    - server/test_poll_position_parity.py
  modified:
    - server/fleet_db.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 18: Frame position storage Summary

`fleet_db.save_frame_position` stores a frame's own position as a private `locations` row (copy-on-write for shared or foreign-owned rows), `frame_position` reads it back, and parity tests pin what the live poll reads. No schema change, no read-path edit.

## Commits

- d365693: save_frame_position and frame_position, with 16 tests.
- 89bd5f9: poll-position parity and schema-unchanged tests.

## What changed

- `save_frame_position(conn, device_id, label, latitude, longitude, timezone, actor_user_id, is_admin) -> (location_id, changed)`: validates first (label trimmed, blank becomes "Frame position", at most 60 characters, no control characters; coordinates rounded to 4 decimals; `_validate_location`), then in one `_atomic` transaction: the actor must own, co-manage or administer the frame (PermissionError otherwise), then
  - no row: insert a private row owned by the frame's owner and link it through `set_device_location_checked`;
  - row used only by this frame and owned by the frame's owner: update in place, or return `(id, False)` writing nothing when values are equal;
  - otherwise (shared, other owner, NULL owner): insert a new private row and link only this frame.
- `frame_position(conn, device_id)`: id, name, latitude, longitude, timezone and `shared`, or None.
- Parity tests use literal zone keys captured from the unchanged read path (legacy Orly runway 3, LFPG runway, position mode with and without a location), sibling isolation, runway mode ignoring a saved position, read-only connection visibility, and the schema (sqlite_master, user_version, `locations` columns, `devices.location_id`) identical before and after saves.

## Deviations from Plan

None in substance. One addition: the in-place and unchanged paths also enforce the acting user's right to manage the frame (the plan only named the link path for that), so an unchanged save by a stranger is refused rather than silently succeeding (T-61-18-03).

## Gates

- ruff, mypy (28 modules), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`: clean.
- `stub-server/test_phase47_freeze.py`: 21 passed, unchanged.
- `test_fleet_frame_position.py`, `test_poll_position_parity.py`, `test_fleet_db.py`, `test_fleet_cycle.py`, `test_detection_spec.py`: green.
- No edit to stub-server/, hardware/, fleet_cycle.py, detection.py, poll_cycle.py.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
