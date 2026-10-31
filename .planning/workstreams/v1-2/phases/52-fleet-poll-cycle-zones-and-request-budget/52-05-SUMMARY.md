---
phase: 52-fleet-poll-cycle-zones-and-request-budget
plan: 05
subsystem: poll-budget
tags: [fleet, zones, deadline, isolation, poll-loop]
requires: ["52-01", "52-02", "52-03", "52-04"]
provides:
  - "server/fleet_cycle.py: run_fleet, FleetResult, DeviceOutcome, FLEET_START_DEADLINE_S, load_fleet, runnable_devices, plan_zones"
  - "server/poll_loop.py: main() serves the fleet; exit 1 only for a live-frame failure or busy lock"
affects: [52-06, 52-07]
key-files:
  created:
    - server/fleet_cycle.py
    - server/test_fleet_cycle.py
  modified:
    - server/poll_loop.py
    - server/test_poll_loop.py
    - server/test_import_boundaries.py
    - deploy/skypane-poll.service
requirements-completed: [FLT-03, FLT-04]
completed: 2026-10-30
---

# Phase 52 Plan 05: Fleet poll cycle Summary

The poll oneshot now serves every runnable device: devices come from fleet.db, are grouped by exact zone, each zone is fetched once through the shared request ledger, and each device runs its own cycle on its zone's result. With no readable fleet.db the fleet is the live frame alone, served from the state root as before.

## Commits
- daff86a: enumeration, activity/render/hold gating, zone grouping (Task 1)
- Task 2 commit: `run_fleet`, `poll_loop` rewiring, tests, unit comments

## What was built
- `load_fleet`: directories only via `device_dirs.resolve_state_dir`; bad `state_path`, symlinked, escaping or missing directory rows are skipped and logged. Live row maps to the root; a missing live row falls back to the root.
- `runnable_devices`: skips unrenderable hardware (profile geometry differs from `panel_format`) and devices inactive for 7 days (live frame exempt; last check-in from history.db `device_health`, falling back to `battery_state.json`).
- `plan_zones`: held devices (`peek_hold`) join no zone; unresolved devices are returned separately. Default resolver shares one geofence zone.
- `run_fleet`: live-frame zone first, then oldest-served; 25 s monotonic start deadline (also passed to `fetch_zone` as `deadline_at`); devices in a zone ordered live first then by `poll_state.json` mtime ascending; zone marked served only when a provider answered and a device ran; a fetcher that raises becomes an all-failed `ZoneFetch` (so `source_fault` is set for that zone only); runner exceptions and `PollBusy` are isolated per device; held devices run last with `ZoneFetch.not_fetched()`; only the live frame gets `reconcile_firmware` and the caddy log. A live frame whose zone cannot be resolved runs standalone (`zone_fetch=None`), exactly as before.
- `poll_loop.main`: calls `run_fleet(..., runner=run_once)`, prints one summary line plus one line per failed/busy device (ids and counts only); live failure prints the previous "cycle failed" line and traceback and exits 1.
- `deploy/skypane-poll.service`: comment-only change.

## Verification
- `pytest server stub-server/test_phase47_freeze.py -n auto`: 1633 passed, 3 skipped (root ignores permission bits), after the import-boundary test adaptation below
- ruff (repo), mypy (19 files, plus `mypy server/fleet_cycle.py` clean), function-size gate (724 functions, none over 80), comment-history guard: clean
- `git diff` of the poll unit contains only comment lines; no hardware/ or Phase 47 file touched

## Deviations from Plan

**1. [Rule 3 - Blocking] Import-boundary test adapted**
- `server/test_import_boundaries.py` asserted `poll_loop.PollBusy is poll_cycle.PollBusy`; `main()` no longer handles `PollBusy` itself (the fleet loop does), so the binding was dropped and the test now only checks `poll_loop.run_once`.

**2. Design notes**
- `poll_loop` hands its own `run_once` binding to `run_fleet` so tests that patch `poll_loop.run_once` keep working unchanged.
- `fleet_cycle.py` was not added to the `[tool.mypy]` module list (plan says existing list); it passes mypy when run directly.
- `FleetResult.requests` counts providers consulted (answered plus failed), not network calls.

## Known Stubs
None.

## Self-Check: PASSED
