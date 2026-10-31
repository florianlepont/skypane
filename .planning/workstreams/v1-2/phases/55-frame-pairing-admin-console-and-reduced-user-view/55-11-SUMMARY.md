---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 11
subsystem: companion-console
tags: [lifecycle, reassign, retire, reactivate, audit-log, release-audit]
requires: [55-05, 55-09, 55-10]
provides:
  - companion/console_lifecycle.py (POST retire, reactivate, reassign; GET /audit; busy_guard)
  - companion/pages/audit_page.py (AuditEvent, AuditView, render, ACTION_LABELS)
  - companion/i18n_fr/admin_lifecycle.py
  - release.install and release.cancel audit rows
affects: [55-12, 55-13, 55-14]
tech-stack:
  added: []
  patterns:
    - a context-manager busy guard taking the in-process poll lock and the cross-process poll-cycle lock without waiting, injected into fleet_ops
    - audit page data assembled in the route module, markup in a pure page module
key-files:
  created:
    - companion/pages/audit_page.py
    - companion/i18n_fr/admin_lifecycle.py
    - companion/test_console_lifecycle.py
    - companion/test_console_audit_page.py
    - companion/test_browser_audit_page.py
  modified:
    - companion/console_lifecycle.py
    - companion/app.py
    - companion/static/style.css
    - companion/test_console_shell.py
    - companion/test_i18n.py
    - companion/test_route_table.py
    - companion/test_user_nav.py
    - companion/testdata/render_baseline.json
    - companion/testdata/update_page_one_type_golden.json
    - test-support/companion_render_snapshot.py
    - test-support/matrix_rows_lifecycle.py
key-decisions:
  - "Refusals before fleet_ops (unknown id, bad or disabled owner, same owner, busy) give an error flash and are not audited; the live-frame retire refusal is audited by fleet_ops as a denied row, not twice."
  - "A page past the last audit page falls back to the last page; any non-positive-integer page value falls back to page 1."
  - "A release audit row is written after the schedule or cancel result is known: ok for scheduled, cancelled or nothing-to-cancel, failed otherwise (including busy)."
requirements-completed: [AUTH-04, AUTH-05]
duration: ~1h30
completed: 2026-10-31
---

# Phase 55 Plan 11: Frame lifecycle actions and Audit log Summary

Admins can reassign, retire and re-activate frames from the Fleet list (live frame protected, wipes inside the fleet_ops transaction, poll-busy frames refused), and a read-only Audit log page lists events newest first with chips and pagination; release install and cancel now write audit rows.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | 351e930 | `handle_retire`, `handle_reactivate`, `handle_reassign`, `busy_guard`, three admin-only CSRF routes, flashes, matrix rows, French, 40 HTTP tests |
| 2 | 4cec9db | `audit_page`, `handle_audit_get`, release audit events in `app.py`, French, CSS block, baselines, browser tests, shell/route-table/nav test updates |

## Verification

- Full non-browser suite (`companion server test-support scripts stub-server -m "not browser"`), final run: 6091 passed, 7 skipped (the root-permission skips). An earlier run, before the baseline and nav test updates, had the expected failures in `test_route_table`, `test_render_baseline`, `test_update_page` and `test_user_nav`, plus one load-sensitive failure in `server/test_provider_rate.py` that passed alone and in the final run.
- Browser suite (`companion -m browser`, chromium symlink dir in the scratchpad): 567 passed, including the 2 new audit page tests (360 px: cards, no sideways scroll, chip and pager targets at least 44 px; 1280 px: 50 table rows, chips visible).
- As `nobody` (the five files from the brief, the suite guards and the two new test files): 461 passed, 4 skipped (the Chromium launch skips of the sandbox's 1243/1248 mismatch; no `requires_non_root` skips).
- `ruff check .`, `mypy` (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (814 functions): clean.
- `git diff` of `companion/app.py` touches only the `audit` import and the two update handlers (7 added lines).

## Behaviour proven by the tests

- Reassign of a non-live frame: every file kind (history.db, poll_state, calendar secret, overrides, rules, gallery) is gone, `device_config.json` is `{}`, name and location cleared, MAC, secret hash and token unchanged, ok audit row; the previous owner gets 404 on the frame page and the new owner 200 without the old name.
- Live frame: reassign changes only the owner (every root file except `fleet.db*` byte-identical); retire is refused with an error flash, nothing changes, a `device.retire` denied row exists.
- Retire keeps the directory and token, the owner loses access and the Account entry, the frame shows as Retired on Fleet; re-activate wipes the old directory and returns the row to pending without a code; re-activating a non-retired row changes nothing.
- Guards: unknown or malformed ids, empty, non-numeric, unknown, negative and injection-shaped owner values, a disabled owner, the same owner, a held in-process poll lock and a held cross-process `poll_cycle_lock` each leave database and files unchanged.
- Audit page: ordering by ts then id, 50 per page with Older/Newer, odd `page` values, chips filter (Failed shows failed and denied), counts, both empty states, failed claim row with Target "-" and neither the guess nor the code on the page, actor and target texts (System, Frame, email, frame name), generic label for an unknown key, escaped stored text, no form or button, single GET route under `/audit`, POST `/audit` the same 404 as an unknown path, user 404 and anonymous redirect, French text.

## Deviations from Plan

1. **[Rule 3 - Blocking] Existing tests described the skeleton state.** The route table now holds the lifecycle routes and the Audit page, so `test_console_shell.py` (aggregator, sub-nav and group expectations), `test_route_table.py` (sample middles), `test_user_nav.py` (sidebar group gained Audit log), `test_i18n.py` (allowlist: French "Action" equals the English) were updated. The shell tests' stand-in console pages are now placed ahead of the real routes so they keep testing the shell alone when plans 12 and 13 land.
2. **[Rule 3] Baselines regenerated.** `render_baseline.json` (44 pages gain the Audit log sidebar link, English and French; `/update` pages also gain the Audit log chip in the section sub-nav; four new unauthenticated entries: `GET /audit` and the three POSTs) and `update_page_one_type_golden.json` (checked by script: the only change in all 14 pages is the inserted Audit log chip). `companion_render_snapshot.py` gained the four paths.
3. **Small CSS block (`.audit-chips`, `.audit-pager`).** The existing `.section-subnav` chip row is hidden from 960 px, and the stylesheet had no 44 px "Older/Newer" link class, so a block of tokens-only rules was appended. No new token or accent consumer.
4. **Browser test file added** (`companion/test_browser_audit_page.py`, 2 tests); not listed in the plan.
5. **Release audit for a refused install.** A refused install (unknown version, busy) is recorded as `failed`; the plan said "outcome ok or failed matching the action result". The confirm step (no `confirm=yes`) writes no row.

## Notes for plans 12 to 14

- `console_lifecycle.AUDIT_PATH` and the frame action constants mirror `console_routes` (a test pins them equal, as in `console_pairing`).
- The audit action label table covers the user and location keys (`user.invite|role|disable|enable|unlink`, `location.add|update|delete`) that plans 12 and 13 must write; the target name lookup resolves `user` and `location` targets when `target_id` is the numeric row id, and shows the raw id otherwise.
- Shell tests: new console pages should not need further edits there; update `test_route_table.py` sample middles and `companion_render_snapshot.py` paths for any new templated route, then regenerate with `PYTHONPATH=<repo>:<repo>/test-support python3 test-support/companion_render_snapshot.py --write`.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (T-55-11-01 to -07 covered by `test_console_lifecycle.py` and `test_console_audit_page.py`).

## Self-Check: PASSED

Files present: companion/console_lifecycle.py, companion/pages/audit_page.py, companion/i18n_fr/admin_lifecycle.py, companion/test_console_lifecycle.py, companion/test_console_audit_page.py, companion/test_browser_audit_page.py. Commits 351e930 and 4cec9db exist.
