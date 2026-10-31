---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 06
subsystem: companion-tests
tags: [auth, idor, reduced-user-view, ssrf, real-handlers]
requires: [55-01, 55-04]
provides:
  - test-support/provisioned_fleet.py (provision_fleet, device_dir, mark_checked_in)
  - companion/test_user_view_http.py (real-handler HTTP layer of the access matrix and reduced view)
affects: []
tech-stack:
  added: []
  patterns:
    - one in-process companion per test, no stubbed routes, real session rows
    - owner-device GET routes taken from routes.ROUTES so a new route needs a declared sample path
key-files:
  created:
    - test-support/provisioned_fleet.py
    - companion/test_user_view_http.py
  modified: []
key-decisions:
  - "Rig is function-scoped: Handler.args is a class attribute, so a second in-process server would re-point a long-lived one."
requirements-completed: [AUTH-05]
duration: ~1h
completed: 2026-10-31
---

# Phase 55 Plan 06: Reduced user view and IDOR over real handlers Summary

The access matrix and reduced user view are now proved over real HTTP: provisioned frames with real directories, real session cookies, no handler stubs. 66 tests, all passing; no production code changed.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | d1f2225 | `provision_fleet` (admin, users A/B/frameless, 3 provisioned frames, live row, pending and retired rows); page and derived-image access for owner, other user and admin; un-prefixed form admin-only; live-frame real-id URLs; selector; pending/retired ids |
| 2 | a7bb1e2 | crafted settings POST, user content reductions, quick toggles, zero-frame user, calendar private-address rejection |

## Verification

- `pytest companion/test_user_view_http.py companion/test_access_matrix.py -n 4 --no-cov`: 866 passed.
- `companion/test_suite_guards.py`: 161 passed. ruff (companion, test-support): clean. mypy: 26 files, no issues. `check_comment_history.py check`: exit 0. `check_function_size.py check --max 80 server stub-server`: 796 functions, none over.
- Parametrization over `routes.ROUTES` (GET, `OWNER_DEVICE`); `test_every_owner_device_get_route_has_a_sample` fails if a route is added without a sample path.
- Browser tests not involved (HTTP only).

## Behaviour proved

- Owner 200 (or the legacy redirect into `/devices/<id>/...`) on each user-reachable page and derived image; another user gets a 404 byte-identical to the unknown-path 404; admin 200; un-prefixed forms 404 for users and 200 for admin; `/device`, `/update`, `/runway-image/..` 404 for users in both forms.
- Crafted POST (`wake_interval_s`, `led_enabled`, `tracked_runway`, `scope=all`) saves the quiet-hours change and leaves the three admin-only keys in `device_config.json` identical (read before and after); same POST to another user's frame is a 404 and the file is byte-identical.
- User Display/Home/Health markup: no runway, wake-interval or LED control, no Refresh trigger, none of the platform Health rows (checked against admin markup with a check-in and source fault recorded so the absence is meaningful); no `/fleet`, `/users`, `/audit`, `/update`, `/device` link; admin still has `/update` and `/device`.
- Quick display and quiet-hours toggle the stored value and return to the same frame; `/quick/led` is 404 for a user.
- Calendar connect with loopback, private, link-local, `localhost`, `webcal://` loopback and plain-http targets is rejected (`calendar_error=invalid`), no secret file is created, and the transport is never called (the real transport is replaced by a recorder, so nothing can reach a socket).

## Deviations from Plan

1. **Function-scoped rig instead of module-scoped.** `InProcessAppServer` sets `Handler.args` on the class; a second in-process server (the live-frame variant) re-pointed the first at another state directory and produced a false failure. One fresh rig per test avoids it.
2. **Foreign `?device=` 404 is compared with the 404 for an id that exists nowhere, not with the unknown-path 404.** That 404 is rendered after the request scope is set, so it carries the user's own tab bar; it is byte-identical for a foreign, live, pending and nonexistent id, which is what prevents an existence oracle.
3. **Health platform-row assertions need a check-in** (a frame never seen shows only an empty state), so `mark_checked_in` was added to the fixture module and used there.
4. Plan Test 5 asserts "the page shows the existing rejection state" by following the redirect and finding the invalid-link message.

## Notes for the owner (not patched, outside this plan's files)

- **Calendar URL via the combined settings form is stored unvalidated.** `POST /devices/<id>/settings` with `calendar_url=https://127.0.0.1/x.ics` (or even `http://127.0.0.1/...`) persists the URL to `calendar_url.secret`; the dedicated connect route rejects before saving. The SSRF gate holds at fetch time (the follow-up refresh and the poll loop both call the gate; tests assert no transport call for eight private targets through this route too), so there is no outbound request, but a user can leave a private URL stored. Consider routing the combined form through `connect_calendar_url` or rejecting at save.
- The user-facing `/devices/<id>/display?device=<foreign>` 404 differs from the generic unknown-path 404 only by navigation chrome; no id information leaks.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register (T-55-06-01 to -04 covered; see the note above for T-55-06-03).

## Self-Check: PASSED

Files present: `test-support/provisioned_fleet.py`, `companion/test_user_view_http.py`. Commits d1f2225 and a7bb1e2 exist.
