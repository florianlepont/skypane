---
phase: 65-photo-storage-privacy-and-quotas
plan: 05
subsystem: storage
tags: [photos, privacy, sweep, cli, companion]
requires: [65-01, 65-02, 65-03]
provides:
  - fleet_cli photos sweep (counts only)
  - post-removal photo sweep in fleet_cli devices remove and the byos mirror
  - guarded photo sweep at companion start
affects: []
key-files:
  created:
    - stub-server/test_fleet_cli_photos.py
    - companion/test_photo_sweep_startup.py
  modified:
    - stub-server/fleet_cli.py
    - stub-server/byos_server.py
    - companion/app.py
requirements-completed: []
duration: 15min
completed: 2026-11-10
---

# Phase 65 Plan 05: Remaining deletion entry points and sweep triggers Summary

Removing a frame by MAC (fleet CLI or the byos mirror) now sweeps the photo tree after the commit, `fleet_cli photos sweep` prints counts only, and the companion sweeps once before it starts serving, never failing to start because of it. No timer, unit, route or poll-loop change.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. CLI sweep and cleanup after frame removal | 38dcb7c | `photos sweep` verb; `byos_server.sweep_photos_quietly` used by `devices remove` and by `mirror_to_fleet` for op "remove" |
| 2. Companion start sweep | aad40e1 | `_sweep_photos_at_start` after the fleet.db sanity check, before the socket is created |

## Deviations from Plan

**1. [Interface choice] Shared helper.** The guarded post-removal sweep is one small public function in `byos_server` (`sweep_photos_quietly`), reused by the CLI, instead of two copies of the try/except. The sweep runs in the mirror function after the transaction block, so `_apply_mirror` and the mirror's error-name contract are unchanged.

**2. [Interface choice] Failure line.** The startup helper catches the companion's existing `_STORE_ERRORS` (including `FleetDbError`) and prints the fixed line `companion: photo sweep at start did not finish`.

**3. Test approach.** The app-server fixture runs the real `main()` in a subprocess, so the orphan-cleanup test uses it directly; failure injection (not possible across a process) calls `_sweep_photos_at_start` in-process with `photo_purge.sweep` monkeypatched.

Tests were written together with the code, not as separate failing commits.

## Verification

- `pytest stub-server/test_fleet_cli_photos.py stub-server/test_fleet_cli.py`: 39 passed. `pytest stub-server`: 360 passed, 1 skipped (root ignores directory permission bits).
- `pytest companion/test_photo_sweep_startup.py companion/test_app_server_start.py companion/test_suite_guards.py companion/test_app_server_fixture.py`: all passed.
- ruff clean, mypy clean (54 files), function-size gate clean (1166 functions, none over 80), comment-history check clean.

## Known Stubs

None.

## Threat Flags

None. T-65-23 (both removal callers sweep, tested), T-65-24 (errors swallowed with a fixed line, injected-failure test), T-65-25 (CLI prints integers only, output-shape test asserts no id, name or path).

## Self-Check: PASSED
