---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 05
subsystem: companion
tags: [routing, landing, access-matrix]
requires: []
provides:
  - access.home_for(principal, frame_id) role landing
  - device_scope.default_frame_for(root, principal)
  - 303 from a user's un-prefixed frame pages to their default frame
affects: [companion/app.py, companion/sign_in.py, companion/login_page.py]
key-files:
  created: [companion/test_landing.py, test-support/matrix_rows_landing.py]
  modified: [companion/access.py, companion/device_scope.py, companion/app.py, companion/sign_in.py, companion/login_page.py]
decisions:
  - "Ledger rows 10 and 13 default: redirect yes, first frame by name casefold then id"
metrics:
  tasks: 3
  completed: 2026-11-03
---

# Phase 61 Plan 05: Landing and un-prefixed redirects Summary

Admin lands on /fleet, a user on the Home of their first frame (name casefold, id tie-break), a user without a frame on /account; a user's un-prefixed frame pages 303 to the same page under that frame, and /login while signed in 303s to the role landing.

## Commits
- 087e79c feat(61-05): role landing and un-prefixed frame page redirect (tasks 1 and 2, entangled)
- affad6f test(61-05): access-matrix rows for the landing redirects (task 3)

## What changed
- `access.home_for(principal, frame_id=None)`: admin `/fleet`, user `/devices/<id>/` or `/account`; access.py stays free of fleet lookups.
- `device_scope.default_frame_for`: first of owned plus co-managed frames; None for admin or no principal.
- `Handler._landing_for`, `_default_frame`, `_frame_page_redirect` (app.py); redirect only for GET, the six pages, a user principal with a frame; target built from the user's own frame list and the matched route path. Anyone else keeps the 404.
- sign_in `_landing_target`: validated `next` wins (user with a frame or admin); a user without a frame always goes to /account. Labels: Continue to Fleet / Home / Account (reuses existing `nav.fleet`, `nav.home`, `account.account` catalog keys, so FR exists already).
- 404/403 pages: `home_route` for a user with a frame (Back to Home goes to the frame Home); a user without a frame sees Back to Account.
- Matrix: `matrix_rows_landing.py` (no new routes; lists redirect pages and /login roles) registered in test_access_matrix, with rows for user 303 per page, frameless 404, anonymous login redirect, signed-in /login, foreign frame 404. test_landing.py holds the freeze-style checks (a) and (b) of UI-SPEC assertion 13.

## Deviations
- Pinned tests moved deliberately (old behaviour was 404 or old landing): test_auth0_login (admin lands /fleet), test_browser_auth0, test_device_scope_owner, test_detection_page, test_user_view_http (users get 303 on the six pages; other un-prefixed templates still 404), test_access::test_home_for.
- test_co_manager_access and test_co_managers compared a stranger's 404 with the co-manager's unknown-path 404; the onward link now depends on the caller, so the reference 404 is now taken as the same caller (the invariant, identical to an unknown path for that caller, is kept).
- Tasks 1 and 2 share one commit because the code is entangled.

## Known stubs
None.

## Self-Check: PASSED
Gates: ruff, mypy (28 modules), check_comment_history, check_function_size, test_phase47_freeze (21 passed), companion + test-support suite with -n auto: 5724 passed, 3 skipped (three pre-existing root-permission skips, no browser skips).
