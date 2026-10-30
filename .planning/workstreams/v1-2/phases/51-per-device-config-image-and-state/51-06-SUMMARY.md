---
phase: 51-per-device-config-image-and-state
plan: 06
subsystem: companion
tags: [dispatch, device-scope, poll-now, settings, isolation]
requires: [51-01, 51-02, 51-05]
provides:
  - Device-aware Handler._dispatch (explicit Device on RouteMatch, per-request scope, history scope on the device directory)
  - build_page_context(handler, device) with ctx.device and ctx.root_state_dir
  - Per-device poll-now (lock, cooldown, hardware refusal, flash keys)
  - Per-device settings POST and quick switches with prefix-aware return paths
  - routes.UNMIGRATED_DEVICE_POSTS temporary guard (removed by the next plan)
affects: [51-07 action POST handlers, UI plans]
key-files:
  created: [companion/test_device_dispatch.py, companion/test_device_poll.py, companion/test_device_settings.py, companion/test_device_helpers.py]
  modified: [companion/app.py, companion/routes.py, companion/page_context.py, companion/health_signals.py, companion/pages/health_page.py, companion/pages/__init__.py, companion/device_scope.py, companion/flash.py, companion/i18n_fr/common.py, server/poll_cycle.py, server/test_firmware_reconcile.py, companion/test_companion_app_02.py, companion/test_companion_app_05.py]
requirements-completed: []
duration: 95min
completed: 2026-10-30
---

# Phase 51 Plan 06: Device-aware companion dispatch, poll-now and settings Summary

A request under `/devices/<id>/` now reads and writes only that device's directory: the dispatcher resolves an explicit `Device` after the session gate, and pages, images, poll-now, settings and quick switches all take it as an argument. The live frame's un-prefixed URLs and HTML are unchanged (committed baselines untouched).

FLT-01 / FLT-02 are intentionally NOT marked complete (they stay pending until phase verification).

## Commits
- a0e48e6 feat(51-06): device-aware dispatch, page context, GET handlers and poll-now
- 6c0e6ee test(51-06): per-device poll-now isolation, lock, cooldown and refusal
- 672caf0 test(51-06): per-device settings and quick-switch isolation, return paths

## What changed
- `_dispatch`: Origin gate, `routes.match`, session gate, then device resolution (`find_device` for a prefix, `load_devices` otherwise), `set_request_scope` once, handler run inside `history_db.connection_scope(device.state_dir)`. Login and static routes run with no device and no fleet.db read. An unknown id is the 404 page.
- `build_page_context(handler, device)`: `state_dir` is the device directory; `root_state_dir` carries the root for the one global input (`fleet_status.json`), plumbed through new optional `fleet_root` arguments on `health_signals`, `safe_health_signals`, `compute_health_state`.
- GET handlers (gallery, illustration, theme and frame previews) take the device; the three legacy redirects keep the prefix; toast Undo forms and links go through `device_scope.scoped`.
- `_handle_poll_now(device)`: refuses unsupported hardware (303 plus never-auto-hiding warning, no filesystem access), else per-device lock and cooldown, `run_once(state_dir=device.state_dir, ...)` with no `caddy_log`, `FLASH_KEY_POLL_TRIGGERED` for the live frame and the new `device_poll_done` (names the device) otherwise.
- `_handle_settings_post(device)` and `_handle_quick_toggle(device, ...)`; `_referring_tab` is prefix-aware; `return_to` is matched after stripping only the current device's own prefix (`device_scope.strip_current_prefix`), so a foreign prefix or arbitrary path falls back to the device's default page. Theme and language POSTs keep the Referer's own well-formed device prefix.
- Temporary guard `routes.UNMIGRATED_DEVICE_POSTS` (the nine action POSTs) answers 404 under a device prefix before any handler runs. The next plan removes it.
- `_POLL_LOCK` removed from `app.py`; the calendar-sync block uses the device's lock.

## Deviations from Plan

**1. [Rule 1/3 - Bug found by the isolation test] firmware/ directory created in a device directory**
- The poll isolation test showed `run_once` creating `firmware/` inside a device directory through the global firmware reconcile step.
- Fix: `run_once(..., reconcile_firmware=True)` explicit parameter (default keeps the timer and live behaviour); the companion passes `reconcile_firmware=device.is_live`. Regression test `test_reconcile_can_be_skipped_for_a_per_device_directory` in `server/test_firmware_reconcile.py`.
- Files: `server/poll_cycle.py`, `server/test_firmware_reconcile.py`.

**2. [Rule 3 - blocking] Existing tests that named the removed constant or the closed message set**
- `companion/test_companion_app_05.py`: the lock accessor lines now use `device_scope.poll_lock_for(server.state_dir)` (the plan asked for this); `companion/test_poll_now_lock.py` only uses the cross-process file lock and needed no change.
- `companion/test_companion_app_02.py`: the "no runtime placeholder" check lists the deliberately interpolated flash keys; `device_poll_done` carries `{device}` per the UI copy, so it was added to that tuple (not in the plan's file list).
- Comments naming `_POLL_LOCK` in `companion/auth.py`, `companion/pages/config_page.py` and `companion/settings/rules.py` were reworded (comment-only).

**3. [Process] Commit granularity**
The three tasks share `app.py`, `routes.py` and `flash.py` (dispatch, poll-now and settings edits interleave in the same hunks and `app.py` imports the new flash keys), so the code landed in one feature commit and the two tasks' test files in two follow-up commits instead of three code-plus-test commits.

**4. [Test support] Added `companion/test_device_helpers.py`** (a `*_helpers.py` with `__test__ = False`, as the suite guards require) holding the shared fleet-app setup and a snapshot function. It hashes SQLite files by logical content and skips WAL/SHM sidecars and the `devices/` subtree: the main database file is rewritten whenever SQLite checkpoints, possibly after a response is sent, which made byte-level snapshots flaky under load.

## Notes for the next plans
- The first request that resolves a device creates `fleet.db-wal` and `fleet.db-shm` in the root (read-only fleet.db connection on a WAL database). Take isolation snapshots after a warm-up request, or use `test_device_helpers.snapshot`.
- Until 51-07, device-prefixed action POSTs (airlines, rules, calendar, illustration) are refused by the guard; un-prefixed ones still act on the root. The calendar-connect handler in `post_actions.py` still serialises under its own module lock rather than the live frame's per-device poll lock, so in-process mutual exclusion with poll-now for the live frame is currently the cross-process `calendar_rules` flock only. 51-07 should move it onto `device_scope.poll_lock_for`.
- Pages on a device still render un-prefixed form actions and nav links (UI plans): posting those forms from a device page hits the live frame's routes today.
- Browser (Playwright) tests were skipped locally: Chromium is not installed in this environment.

## Verification
- `pytest companion server stub-server test-support scripts -n auto`: 4170 passed, 547 skipped (browser tests)
- `companion/test_render_baseline.py`, `companion/test_route_table.py` green, `companion/testdata` untouched
- `stub-server/test_phase47_freeze.py` and `test_image_negotiation.py` unmodified and passing
- `ruff check .` clean; `server/.venv/bin/mypy` clean; `scripts/check_comment_history.py check` clean; `scripts/check_function_size.py check --max 80 server stub-server` none over 80; `companion/app.py` 1385 lines (ceiling 1500)
- Isolation tests run repeatedly under `-n 6` (8 consecutive green runs)

## Threat model coverage
T-51-23 (snapshot tests for dev_b, landscape and live after settings, quick, poll and refused POSTs), T-51-24 (404 after the session gate; unauthenticated redirect identical for known and unknown ids), T-51-25 (return_to and Referer whitelist tests), T-51-26 (Origin gate still first; `test_post_origin.py` green), T-51-27 (in-process spy: `caddy_log` never passed).

## Known Stubs
None.

## Self-Check: PASSED
