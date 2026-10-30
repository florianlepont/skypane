---
phase: 51-per-device-config-image-and-state
plan: 07
subsystem: companion
tags: [post-actions, device-scope, isolation, calendar, illustration]
requires: [51-06]
provides:
  - Explicit-Device airline, illustration, colour-rule and calendar POST handlers
  - Per-device lock for calendar connect
  - Isolation tests for every action POST
affects: [UI plans]
key-files:
  created: [companion/test_device_actions.py]
  modified: [companion/post_actions.py, companion/app.py, companion/routes.py, companion/test_device_dispatch.py]
requirements-completed: []
completed: 2026-10-30
---

# Phase 51 Plan 07: Explicit-device action POST handlers Summary

All nine remaining device-scoped POST handlers now take the request's `Device` and touch only `device.state_dir`. `companion/post_actions.py` contains no `self.args.state_dir` and no module-level lock. FLT-01 / FLT-02 are intentionally NOT marked complete (pending phase verification).

## Commits
- ece6393 feat(51-07): explicit device argument for airline, illustration, rule and calendar actions
- d738909 test(51-07): isolation tests for every device-scoped action POST

## What changed
- `post_actions.py`: `_handle_illustration_replace`, `_handle_manual_resolve_post`, `_handle_airline_rename_post`, `_handle_airline_rename_reset_post`, `_handle_manual_resolution_delete`, `_handle_rule_add_post`, `_handle_rule_delete`, `_handle_calendar_disconnect_post`, `_handle_calendar_connect_post` take `device`. A new `_scoped_redirect` wraps every redirect target in `device_scope.scoped()` (the rename and calendar-sheet redirect helpers use it through the request scope). The illustration allow-list is computed from the target device's own directory.
- Calendar connect takes `device_scope.poll_lock_for(device.state_dir)` non-blocking; when busy it redirects with the existing `calendar_sync_deferred` flash and fetches nothing. Another device's held lock does not defer it. `_POLL_LOCK` and `import threading` are gone.
- `app.py`: `_handle_rule_delete_post(device, middle)` forwards the device; the temporary guard in `_dispatch_for_device` is removed.
- `routes.py`: lambdas pass `m.device`; `UNMIGRATED_DEVICE_POSTS` removed.
- `test_device_dispatch.py`: `test_unmigrated_device_posts_refused` and its route tuple removed (replaced by `test_device_actions.py`).

## Remaining `self.args.state_dir` sites in companion/app.py (root-scoped by design)
- 639 `page_context`: fallback to the live frame when no device is in scope
- 661 `_not_found_page`, 674 `_forbidden_page`: error pages render for the live frame/root
- 968 `_dispatch`: login/static routes with no device, history scope on the root
- 980 `_dispatch_for_device`: root lookup into fleet.db that resolves the device
- 1251, 1252, 1259 (`_handle_update_install_post`/Update page), 1261, 1309 (`_handle_update_cancel_post`): Update handlers are root-scoped (firmware registry and install state are fleet-wide)

No device-scoped handler reads the global directory.

## Tests
`companion/test_device_actions.py` (20 tests): one snapshot-equality isolation test per handler (dev_b, live and the other device unchanged), live un-prefixed variants for upload, resolve and calendar connect, per-device illustration allow-list (key resolvable only in dev_b is 404 under dev_a), resolve-dialog return route keeps the prefix, malformed rule-delete path 404 (4 shapes), calendar connect/disconnect isolation, lock independence and own-lock deferral. Calendar connect cases run the app in-process to stub the transport.

## Verification
- `pytest companion server stub-server test-support scripts -n auto`: 4182 passed, 547 skipped (browser tests; Chromium not installed; root-permission skips)
- `stub-server/test_phase47_freeze.py` and `test_image_negotiation.py` unmodified and passing
- `ruff check .` clean; `server/.venv/bin/mypy` clean; `check_comment_history.py check` clean; `check_function_size.py check --max 80 server stub-server` none over 80; `companion/app.py` 1383 lines (ceiling 1500)

## Deviations from Plan
- Commit granularity: the two tasks share `post_actions.py`, `routes.py` and `app.py` hunks, so the code landed in one feat commit and the tests in one test commit.
- `_rename_redirect` / `_calendar_sheet_redirect` keep their signatures (no `device` parameter): they scope through the per-request device scope, which the dispatcher sets, rather than an extra argument.
- The existing calendar-connect handler had no lock usage (the old module lock was unused there), so the non-blocking per-device acquire with a deferred flash is new behaviour; the un-prefixed live path is covered by the existing tests, which still pass.

## Threat model coverage
T-51-29 (snapshot equality per handler), T-51-30 (per-device allow-list before any path is built), T-51-31 (unchanged safe-fetch path, secret in the device directory), T-51-32 (redirects built from fixed routes through `scoped()`).

## Known Stubs
None.

## Self-Check: PASSED
