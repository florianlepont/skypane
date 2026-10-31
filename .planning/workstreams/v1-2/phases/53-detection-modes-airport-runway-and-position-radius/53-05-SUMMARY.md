---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 05
subsystem: detection
tags: [fleet-cycle, poll-cycle, render-tag, pipeline-equality]
requires: [53-04]
provides:
  - server/fleet_cycle.py (detection_resolver, FleetDevice.location)
  - server/poll_cycle.py (CycleContext.location and spec, run_once location keyword)
  - server/plane/render/style.py (runway_tag_text / empty_heading_text delegate to detection)
  - server/fleet_db.py (device_coordinates)
affects: [53-06, 53-08]
key-files:
  created:
    - server/test_detection_pipeline.py
  modified:
    - server/fleet_cycle.py
    - server/fleet_db.py
    - server/poll_cycle.py
    - server/plane/render/style.py
    - server/test_fleet_cycle.py
    - server/test_render.py
    - server/test_render_landscape_card.py
requirements-completed: [DET-01, DET-02, DET-03]
completed: 2026-10-31
---

# Phase 53 Plan 05: Detection spec wired into the fleet cycle, poll cycle and frame tag Summary

Each device now polls, selects and labels from its own `detection.spec_for` result; the live Orly frame is observably identical on the generated-document path and the kill-switch (legacy file) path.

## Commits

- 578f505 per-device resolver and device location in the fleet cycle
- 2244efe poll cycle selects from the device's own detection spec
- 9b0c03d frame tag and empty heading follow the detection display id

## Behaviour

- `detection_resolver(geofence_path)` is the default `run_fleet` resolver. It loads each device's config and returns the spec's zone and document; nothing is cached per run. Two LFPG devices on 08L/26R and 08R/26L share one zone group and one fetch, and each device's own cycle builds its own spec. Neighbouring position devices (48.8566,2.3522 and 48.8601,2.3500, 9 km) share one rounded zone. `geofence_resolver` and its tests are unchanged.
- `FleetDevice.location` comes from the device's own `devices.location_id` row, read on the existing read-only connection (an unreadable location table gives None, never a lost device). `run_device` passes `location=` only when it is not None.
- `load_cycle_context` builds the spec once; `tracked_runway_id` is the spec's display id. `detect_flight`, `_select_from_zone` and `_fetch_standalone` use the spec's document and zone; `detect_flight` no longer calls `detect.load_geofence` (the file is read only inside `spec_for` under the kill switch).
- `style.runway_tag_text` and `empty_heading_text` delegate to `detection.tag_text` / `empty_heading` (non-string ids degrade to the Orly default). Results: `CDG · 08L/26R`, `NEARBY · 9 KM`, `Watching Runway 08L/26R`, `Watching Within 9 km`; Orly texts unchanged.

## Key proof (T-53-24)

`server/test_detection_pipeline.py::test_pipeline_generic_equals_legacy[3|06-24|02-20]` runs `run_once` with the same snapshot on a generic-path state dir and a `SKYPANE_LEGACY_ORLY_GEOFENCE=1` state dir: same selected flight (minus `seen_pos`), equal `cycle_result`, equal published `panel.bin` SHA-256, equal `poll_state` keys. A no-aircraft variant checks the same for the empty frame. Also present: `test_pipeline_cdg_runway_isolation`, `test_pipeline_position_selects_lowest`, `test_pipeline_position_adds_no_new_poll_state`, `test_pipeline_position_failsafe` (no location and outside France both give `tracked_runway == "3"`), and a run with the legacy geofence file missing.

## Verification

- `pytest server stub-server -n auto`: 2595 passed, 4 skipped (root permission-bit tests).
- Plan commands: `test_detection_pipeline.py test_poll_cycle_steps.py test_pipeline_e2e.py test_orly_replay.py stub-server/test_phase47_freeze.py` 89 passed; render/golden set 435 passed; fleet set green. No golden file regenerated, `git diff` on `stub-server/` and `hardware/` empty.
- Companion non-browser tests (`pytest companion -m "not browser" --ignore-glob='companion/test_browser_*'`): 3644 passed, 3 skipped.
- ruff clean, mypy clean (28 files), function-size gate passes (905 functions), comment-history check passes, no `ORY · RWY 3` literal in `server/plane/render/*.py`.

## Deviations from Plan

**1. [Rule 3 - Blocking] `server/fleet_db.py` touched (not in the plan's file list)**
- `list_devices` carries no coordinates and `get_location` needs a location id the row does not expose, so a small read-only `device_coordinates(conn)` join was added and used by `_fleet_rows` on the same connection.

**2. [Ordering] `run_once` location keyword added in the first commit**
- The fleet commit passes `location=` to real cycles for devices that have a location, so `run_once` and `CycleContext.location` were added there to keep that commit green; the spec arrived in the second commit.

**3. [Test] Level-cruiser poll_state keys**
- A level cruiser creates no confirmed state, so its poll_state has fewer keys than an arrival. The test asserts equality for a descending position-mode arrival against a runway arrival, and a subset for the cruiser.

No catalogue tag was too wide in portrait or landscape (checked for the longest catalogue tag by character length and `position:28`). No existing test needed weakening.

## Known Stubs

None.

## Self-Check: PASSED
