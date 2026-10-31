---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 10
subsystem: companion-console
tags: [fleet, pairing, claim, throttle, audit, register]
requires: [55-05, 55-09]
provides:
  - companion/pages/fleet_page.py (FleetRow, FleetView, render)
  - companion/console_pairing.py (GET /fleet, POST /fleet/register, POST /fleet/pair, SESSION_THROTTLE, GLOBAL_THROTTLE)
  - companion/i18n_fr/admin_fleet.py
  - test-support/fleet_console_support.py (seed and request helpers for console tests)
affects: [55-11, 55-14]
tech-stack:
  added: []
  patterns:
    - console modules that load while the navigation imports (route modules, console_flash, fleet_page) import companion.ui_components and companion.layout only on use
    - a console page body may be a callable, resolved after the request language is set
key-files:
  created:
    - companion/pages/fleet_page.py
    - companion/i18n_fr/admin_fleet.py
    - companion/test_console_fleet_page.py
    - companion/test_console_pairing.py
    - companion/test_browser_fleet_page.py
    - test-support/fleet_console_support.py
  modified:
    - companion/console_pairing.py
    - companion/console_flash.py
    - companion/app.py
    - test-support/matrix_rows_pairing.py
    - test-support/companion_render_snapshot.py
    - companion/testdata/render_baseline.json
    - companion/testdata/update_page_one_type_golden.json
    - companion/test_console_shell.py
    - companion/test_user_nav.py
    - companion/test_i18n.py
    - companion/test_csrf.py
    - companion/test_browser_update.py
key-decisions:
  - "Pair and reassign forms use the form field `owner_user_id`; the claim code field is `code`; register fields are `mac`, `secret_sha256`, `hardware_type`."
  - "A refused claim re-renders the Fleet page with HTTP 200 (identical for wrong, expired, used, malformed); a throttled claim is 429; missing fields are 400 and are not counted."
  - "The owner is checked active before any code is evaluated, so a guess with a bad owner never reaches the scan."
  - "The register form never echoes the hash field back on error (a refused paste may be a secret)."
requirements-completed: [AUTH-04, AUTH-05]
duration: ~2h
completed: 2026-10-31
---

# Phase 55 Plan 10: Fleet page, register and pair handlers Summary

The admin Fleet page (live, pending and retired frames with owner, hardware, last seen, battery, firmware, status and row-action confirm blocks, plus the Pair and Register cards) and the register and pairing-claim handlers, with per-session and global lockouts and audit rows that never hold the guess.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 and 2 (code) | 146509c | `fleet_page`, `console_pairing` (GET, register, pair, throttles), French strings, matrix rows, support module, Fleet page tests, baseline and test updates |
| 2 (tests) | 7434038 | 23 HTTP tests for register and pair |
| follow-up | 71bb343 | 44px touch targets via the existing `.update-actions` row, browser tests, More-sheet test update |

The handlers were written together with the page module, so the code for both tasks is in 146509c (same approach as plan 05); the pairing tests are their own commit.

## Verification

- Full non-browser suite (`companion server test-support scripts stub-server -m "not browser"`): 5981 passed, 7 skipped (the root-permission skips).
- As `nobody` (the five files from the brief plus the suite guards): 391 passed, 4 skipped. The 4 skips are Chromium launch skips (the sandbox's 1243/1248 mismatch; no `requires_non_root` skips remain). The same files under root skip the 7 permission tests; none fail as `nobody`.
- Browser suite (`companion -m browser`, chromium symlink dir in the scratchpad): 558 passed, 4 failed before the fix to `test_browser_update.py` (admin More sheet now has 4 links); the 4 pass after it, and the 3 new Fleet browser tests pass (360 px: no sideways scroll, cards shown, table hidden, every control at least 44 px; 1280 px: table with 4 rows, cards hidden).
- `ruff check .`, `mypy` (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (814 functions): clean.
- The concurrent-claim test (two real HTTP requests, barrier) passed on repeated runs.

## Deviations from Plan

1. **[Rule 3 - Blocking] Import cycle.** `companion.layout` imports `ui_nav`, which imports `console_routes`, which imports `console_pairing`; registering flash keys at import and importing `ui_components` or `account_page` at module level all hit a partially initialised module. Fixes: `console_flash` imports `ui_components` only when it renders a toast (it is a leaf now); `fleet_page` and `console_pairing` import `ui_components` and `console_routes` on use; `fleet_page` declares its own "Unnamed frame" message instead of importing `account_page`. `console_pairing` keeps the three path literals (`/fleet`, `/fleet/register`, `/fleet/pair`) because `console_routes` cannot be imported at module level; a test pins them equal to the `console_routes` constants.
2. **[Rule 3] `Handler._console_page` gained `status=200` and accepts a callable body.** Needed for the 400 and 429 re-renders, and so the body is built after the request language is set (otherwise the page rendered in English under a French request).
3. **[Rule 1] Tests that described the 55-09 skeleton state were updated** because the Fleet route now exists: `test_console_shell.py` (aggregator, group, phone bar, tampered-flash path moved to `/audit`), `test_user_nav.py` (sidebar group now has Fleet and Releases), `test_csrf.py` (flagged set is the six legacy routes plus the console POST routes), `test_browser_update.py` (admin More sheet holds Airlines, Health, Device, Update).
4. **[Rule 3] Baselines regenerated.** `render_baseline.json` (44 pages gain the sidebar Fleet link and the phone Admin tab that replaces Airlines; plus three new unauthenticated entries), `update_page_one_type_golden.json` (checked: every change is only the inserted section sub-nav, EN and FR), and the snapshot module's unauthenticated route list gained `/fleet`, `/fleet/register`, `/fleet/pair`.
5. **[Rule 3] French catalogue module is `admin_fleet`**, so message ids use the `admin_fleet.` area (a guard requires the area to match a catalogue module). Flash keys stay `fleet.paired`, `fleet.registered`, `fleet.register_duplicate`. `admin_fleet.actions` ("Actions") is in the unchanged-in-French allowlist of `test_i18n.py`.
6. **Touch targets without new CSS.** The global button is 30 px (36 px on phones); the stylesheet has no class giving a generic form button 44 px, so the claim, register and confirm buttons sit in the existing `.update-actions` row (its rule is the install-button 44 px floor). No CSS was edited.
7. **Added a browser test file** (`companion/test_browser_fleet_page.py`, 3 tests) and a shared support module (`test-support/fleet_console_support.py`); neither was listed. The plan 14 browser verification can extend them.
8. **Confirm "Keep frame" is a link to `/fleet`** rather than a second `<summary>`: a second summary is invalid HTML and only a reload closes a `<details>` without script.

## Notes for plans 11 to 14

- Row-action forms post to `FRAME_ACTION_PREFIX + <id> + /retire | /reactivate | /reassign`; the id is the device id for retire and reassign and the pending id for reactivate; the reassign form field is `owner_user_id` (the select lists every active user, including the current owner). Plan 11 implements the handlers.
- Each action form is rendered twice (phone cards and desktop table, hidden by CSS); element ids carry a `c-` or `t-` prefix to stay unique.
- The throttles are in memory and per process: a companion restart clears every count and lockout.
- `test-support/fleet_console_support.py` has `seed_fleet`, `issue_code`, `admin_cookie`, `post` (adds the CSRF token) and `dump_database_text` for later console tests.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (T-55-10-01 to -07 covered by `test_console_pairing.py` and `test_console_fleet_page.py`).

## Self-Check: PASSED

Files present: companion/pages/fleet_page.py, companion/console_pairing.py, companion/i18n_fr/admin_fleet.py, companion/test_console_fleet_page.py, companion/test_console_pairing.py, companion/test_browser_fleet_page.py, test-support/fleet_console_support.py. Commits 146509c, 7434038, 71bb343 exist.
