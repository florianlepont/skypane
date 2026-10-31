---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 04
subsystem: companion-access
tags: [auth, ownership, routes, access-matrix, account]
requires: [55-01, 55-02]
provides:
  - routes.OWNER_DEVICE (Access(USER, "device")) on the user-reachable frame routes
  - app._effective_access: prefixed form decided on the URL id, un-prefixed form admin-only
  - device_scope.load_devices_for / selector_value, principal-aware prefix and referring tab
  - Account page "Your frames" list
affects: [55-06]
tech-stack:
  added: []
  patterns:
    - access.decide stays pure; the dispatcher chooses the (Access, captured) pair per route form
    - a user's live frame is only ever addressed by its real id
key-files:
  created:
    - companion/test_device_scope_owner.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/device_scope.py
    - companion/device_dispatch.py
    - companion/ui_shell.py
    - companion/sign_in.py
    - companion/pages/account_page.py
    - companion/i18n_fr/account.py
    - companion/test_access_matrix.py
    - test-support/access_matrix_support.py
    - companion/test_account_page.py
    - companion/test_route_table.py
    - companion/test_user_nav.py
key-decisions:
  - "access.py is untouched: authorized_device_id keeps its owner-as-input shape."
  - "Un-prefixed device routes are admin-only through _effective_access, so a user can never fall through to the live frame."
requirements-completed: [AUTH-05]
duration: ~1h
completed: 2026-10-31
---

# Phase 55 Plan 04: Owner device routes Summary

Owners now reach their own frames' pages under `/devices/<id>/...`; another user gets the same 404 as an unknown path, an admin reaches every frame, and the un-prefixed form (the live frame) stays admin-only. Selector, prefix, redirects and the new Account frames list are confined to the caller's own frames.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | 132bca3 | `Device.owner_user_id`, `load_devices_for`, user-always-prefixed URLs and selector values, `switch_target` refusing `live`/foreign ids, user `_referring_tab`, empty scope when a user has no frames |
| 2 | 7aad8c9 | `OWNER_DEVICE` on 24 routes, `_effective_access` in `_dispatch`, matrix owner-device kind plus `UNPREFIXED_OUTCOMES`, three matrix assertions rewritten, `stub_routes` via `_replace` |
| 3 | 3b603f6 | Account "Your frames" card from the caller's own frames, French strings |

## Verification

- Matrix (`test_access_matrix.py`, `test_access.py`, `test_device_routes.py`): 928 passed after the flip (every route x anonymous/owner/other/admin, both forms, stubbed handlers; unknown and malformed ids; admin-only device routes refuse the owner in both forms; probe family unchanged).
- Real-handler HTTP tests (`test_device_scope_owner.py`): owner 200 on own frame, other user body byte-equal to the unknown-path 404, anonymous 303, un-prefixed `/`, `/display`, `/flights`, `/health`, `/airlines` 404 for a user and 200 for admin, theme POST returns to the frame page the user came from, a frameless user lands on `/account`.
- `git diff` of `companion/access.py` across the plan: empty.
- ruff, mypy (25 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (780 functions, none over): clean.
- Full non-browser suite (`pytest companion server test-support scripts -m "not browser" -n 4 --no-cov`): 5344 passed, 6 skipped (root-permission skips, pre-existing).

## Deviations from Plan

1. **[Rule 3 - Blocking] `companion/ui_shell.py` modified** (not listed): the selector option value was `LIVE_ID if device.is_live else device.id`; it now calls `device_scope.selector_value(device)` so a user never gets the literal `live`.
2. **[Rule 1 - Tests encoding the old shape]** Plan 01/54 tests that assumed the frame routes were closed were rewritten with intent kept: `test_route_table.py` (non-admin routes may now be `OWNER_DEVICE`, which must be device-scoped; plus an exact-set test that only `/device` and LED stay admin-only in the device-scoped set), `test_account_page.py` (a user is refused admin routes and the un-prefixed form of device routes), `test_user_nav.py` (the three "no reachable page" cases now close the pages explicitly with a monkeypatch).
3. **User referring tab:** a Referer of `/account` keeps the user on `/account` (a theme or language switch there should not jump to a frame), rather than the first frame's Home. Every other non-owned or non-user-page Referer goes to the first owned frame's Home, else `/account`.
4. **Unnamed frames on Account:** the device scope names an unnamed frame by its id, so the Account row shows "Unnamed frame" (French "Cadre sans nom") instead, because the spec forbids showing ids. Found by a test that checks the id appears only in the Open href.
5. **Plan verification path:** `companion/test_device_poll.py` named in Task 1 does not exist; the other listed test files were run.
6. Task 1's commit contains HTTP tests in `test_device_scope_owner.py` that need Task 2's routes; they only pass from Task 2 on (the tree is green at the end of each of Tasks 2 and 3).

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model; T-55-04-01 to -05 are covered by the matrix rows, the owner-filter tests and the `_referring_tab` cases (foreign id, unknown id, `..`, protocol-relative Referer).

## Notes for the owner / later plans

- Plan 06 can reuse `test_device_scope_owner.py`'s HTTP fixtures to prove the reduced views over the real handlers.
- `/devices/<id>/` for an admin and an id that exists in no row is a 404 (the ownership gate needs a row), unchanged.
- A user who owns the live frame is served at `/devices/<real id>/...`; the un-prefixed live frame remains admin-only.

## Self-Check: PASSED

Commits 132bca3, 7aad8c9, 3b603f6 exist; `companion/test_device_scope_owner.py` present.
