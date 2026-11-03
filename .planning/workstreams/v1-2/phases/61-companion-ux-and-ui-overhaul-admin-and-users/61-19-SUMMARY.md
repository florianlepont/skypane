---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 19
subsystem: companion
tags: [admin-frame-rule, redirects, fleet-menu, frame-notice]
requires: [61-17]
provides: [device_scope.personal_frames_for, device_scope.has_fleet_rows, device_scope.foreign_frame_owner_email, administrator frame redirect, frame-notice strip]
key-files:
  created:
    - companion/test_admin_personal_scope.py
    - companion/test_browser_admin_personal_scope.py
  modified:
    - companion/device_scope.py
    - companion/app.py
    - companion/ui_shell.py
    - companion/pages/fleet_page.py
    - companion/i18n_fr/admin_fleet.py
    - companion/i18n_fr/nav.py
    - companion/static/style.css
    - test-support/matrix_rows_landing.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 19: Administrator personal space follows the frame rule

An administrator's un-prefixed Home, Flights, Detection, Display and Airlines pages now 303 to the same page of their default own or co-managed frame (account page when they have none), every frame with a fleet row is addressed by `/devices/<id>/`, Fleet leads to the Console frame pages, and a Viewing-owner strip marks a foreign frame.

## Commit

- 7171bc8: all three tasks together, one green commit (as the plan requires). The summary follows in its own docs commit.

## What changed

- **device_scope.** `personal_frames_for` (owned or co-managed, fleet rows only), `default_frame_for` now works for every principal, `has_fleet_rows`, `foreign_frame_owner_email`. `_unprefixed` is true only for the synthetic live entry (`id == "live"`), so `current_prefix`, `selector_value`, `target_path` and `scoped` prefix the served frame whenever it has a fleet row.
- **Redirect.** `_frame_page_redirect` serves both roles and keeps the query (`parse_qsl` + `urlencode`). `_dispatch` runs it for an administrator after the access gate, before `_dispatch_for_device`. No frame and a migrated fleet gives `/account`; no fleet rows keeps serving the frame as before. An administrator's `?device=` switch is left to the device dispatcher (one hop, unknown value still 404). The user path is unchanged except that the query is now kept.
- **Console frame pages** (`/health`, `/device`, `/airlines/manage`) still resolve un-prefixed for an administrator (not in the redirect set).
- **Fleet.** Name links to `/devices/<id>/health`; row menu is Health, Device, Open personal view, Manage access, Reassign, Retire (Retire not for the served frame); "Open frame" and its French string are removed. EN/FR strings added.
- **Notice.** `ui_shell.frame_notice_html` (`.frame-notice`, 14px, secondary background, min 44px, wraps; email escaped) next to the switcher slot; absent for own/co-managed frames, users, co-managers and Console frame pages (`page_shell(console_page=...)`, set from `_CONSOLE_FRAME_ROUTES`). A frame with no owner shows no strip.

## Existing tests updated in place (found by running the suite; 95 failed on the first run)

test_access_matrix (administrator cells now expect 303 to /account; demoted-admin test uses /health), test_airline_manage_routes, test_browser_detection, test_browser_fleet_dialogs, test_browser_fleet_page, test_co_managers, test_co_managers_page, test_console_fleet_page, test_console_shell, test_detection_page, test_device_actions (also the warm-up request), test_device_dispatch, test_device_links, test_device_pages, test_device_routes (the "single-device fleet never mentions a prefix" crawl became "addresses its frame by its own id"), test_device_scope, test_device_scope_owner, test_device_selector, test_device_settings, test_display_detection_card, test_landing, test_location_picker, test_poll_removal, test_user_view_http, matrix_rows_landing (`ADMIN_FRAMELESS_TARGET`). The remaining files in the plan's list needed no change. Intent was kept in each; the un-prefixed POST routes are still exercised, only their redirect Locations now carry the frame id.

## Deviations from Plan

1. **[Rule 1] Fixture warm-up requests.** Several fixtures warmed up with an un-prefixed `GET /display`, which now only redirects; the warm-up moved to the prefixed URL (otherwise first-request side effects broke snapshot tests).
2. **Notice scope.** `/airlines/manage` shares the Airlines nav slug, so the Console exclusion is by route (`console_page`) rather than by slug.
3. **Baselines.** `render_baseline.json` regenerated: no diff (unauthenticated pages only). Sign-in digests and goldens unchanged.

## Gates

- ruff, mypy (28 modules), `check_comment_history.py`, `check_function_size.py` (none over 80): clean. `stub-server/test_phase47_freeze.py`: 21 passed, unchanged.
- Full `companion test-support stub-server -n auto`: 6722 passed, 4 skipped (pre-existing), 1 failed (`test_browser_fleet_dialogs::test_pair_a_frame_in_four_actions`, a real break: it looked for the old name-link target). Fixed, then that file passed 3 times in a row alone. No full re-run after that one-line test edit.
- New browser tests (Chromium, not skipped) run 3 times in a row green.

## Known Stubs

None.

## Threat Flags

None. T-61-19-01 (query re-encoded, hostile `//`, CR/LF, backslash tested), -02 (email shown to administrators only, escaped; user and co-manager tested), -03 (stranger 404 unchanged), -04 (no device-protocol code touched) are covered.

## Self-Check: PASSED
