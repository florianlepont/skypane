---
phase: 52-fleet-poll-cycle-zones-and-request-budget
plan: 02
subsystem: poll-budget
tags: [adsb, zones, corroboration, fleet]
requires: []
provides:
  - "server/plane/detect.py: select_from_provider_results (pure selection over fetched lists)"
  - "server/fleet_zones.py: Zone, ZoneEntry, zone_from_geofence, order_zones, device_is_active, INACTIVE_AFTER_S"
affects: [52-03, 52-04]
key-files:
  created:
    - server/fleet_zones.py
    - server/test_fleet_zones.py
  modified:
    - server/plane/detect.py
    - server/test_plane_detection.py
requirements-completed: [FLT-03]
completed: 2026-10-30
---

# Phase 52 Plan 02: Shared selection and zone rules Summary

Fetch is split from selection in `detect.py` so devices in one zone select from one shared fetch result with unchanged corroboration, and a pure `fleet_zones` module owns exact-pair zone keys, serving order and the 7-day inactivity rule.

## Commits
- 67051b5: split fetch from selection in detect (Task 1)
- dd90427: fleet_zones module, tests and this summary (Task 2)

## Verification
- test_fleet_zones, test_plane_detection, test_poll_efficiency, test_provider_rate, stub-server/test_phase47_freeze: all pass (no pre-existing assertion edited)
- ruff, mypy (detect.py, fleet_zones.py), function-size gate, comment-history guard clean

## Deviations from Plan
None. `poll_current_aircraft` was reduced to a fetch helper (`_fetch_providers`) plus one `select_from_provider_results` call. `fleet_zones.py` was not added to the `[tool.mypy]` module list (pyproject.toml untouched).

## Decisions
- `ZoneEntry(zone, has_live)` is a frozen dataclass; duplicate entries collapse, live if any entry is live.
- Zone coordinates are normalised so -0.0 and 0.0 share a key; bool and non-numeric inputs are rejected.
- Inactivity uses the last check-in, else the creation time; a device with neither is inactive.

## Known Stubs
None.

## Self-Check: PASSED
