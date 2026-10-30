---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 04
subsystem: auth
tags: [default-deny, sessions, access-control, sqlite, companion]
requires:
  - phase: 54-01
    provides: fleet.db sessions table, server/fleet_sessions.py
  - phase: 54-03
    provides: prefs.set_request_principal, legacy-access pill, user shell
provides:
  - Validated Access annotation on every Route (default-deny at construction)
  - companion/access.py: Principal, decide(), authorized_device_id(), home_for()
  - Per-request Principal from a server-side session; decide-driven _dispatch
  - Shared-password login on server-side legacy-admin sessions
affects: [54-05, 54-06, 54-07, 51]
tech-stack:
  added: []
  patterns:
    - "Route(...) raises TypeError without a valid Access"
    - "Lazy per-request fleet.db connection; static assets never open it"
    - "Store errors answer 503, never allow and never a login redirect"
key-files:
  created:
    - companion/access.py
    - companion/test_access.py
    - companion/test_sessions_http.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/auth.py
    - companion/login_page.py
    - companion/i18n_fr/common.py
    - companion/test_route_table.py
    - companion/testdata/render_baseline.json
    - companion/test_request_connections.py
    - companion/test_page_context.py
    - companion/test_freshness_token.py
    - test-support/efficiency_probe.py
key-decisions:
  - "Roles and Principal live in access.py (no routes import cycle); routes.py rebinds ANONYMOUS/USER/ADMIN"
  - "app._now() is the single clock for sessions so tests can move time without patching time.time"
  - "A malformed SKYPANE_LEGACY_PASSWORD_LOGIN value reads as off at request time (fail closed); startup refusal is plan 07"
  - "Logout answers 503 and keeps the cookie when the row cannot be deleted"
  - "Prefs principal kind for a user principal is its role (user/admin); legacy-admin keeps its own kind"
requirements-completed: []
duration: 55min
completed: 2026-10-30
---

# Phase 54 Plan 04: Default-deny access and server-side principal Summary

Every route now carries a validated minimum-role `Access`, one pure `decide()` returns ALLOW, LOGIN or NOT_FOUND, and the shared-password login creates a legacy-admin session row in fleet.db that is resolved into a Principal on every request.

## Tasks

1. Access annotation, validated Route, pure decide() and ownership gate (cd5a7b1)
   - `Route.__new__` raises TypeError for a bool, None, wrong type, unknown min_role or a missing field.
   - Classification: PUBLIC = GET/POST /login plus the static GETs; SIGNED_IN = POST /ui-theme, /ui-lang, /logout; all 31 other routes ADMIN_ONLY. The route-table test states these sets by hand.
   - `decide()` and `authorized_device_id()` validate ids against `^d_[0-9a-f]{8}$` before any lookup; admin reaches only existing devices; malformed or non-string ids never reach `owner_lookup`.
2. Server-side principal, decide-driven dispatch, session-backed login/logout, 503 fail-closed (c547f10)
   - Cookie = `secrets.token_urlsafe(32)`; fleet.db holds its sha256; login rotates (drops the session whose cookie came with the request); logout deletes the row first.
   - Role, disabled, expiry and idle are read fresh each request; legacy sessions are re-checked against `SKYPANE_LEGACY_PASSWORD_LOGIN` each request.
   - A user principal on an admin route gets the same 404 body as an unknown path; the Health dot is computed only for admin principals (404 and 403 pages).
   - sqlite/FleetDb/OS errors while resolving answer 503 with a fixed bilingual page; the login route still renders.
   - `main()` opens fleet.db once so the file exists and exits 1 if it cannot.
3. Render baseline regeneration and full-suite fallout (see below)

## Render baseline review

`companion/testdata/render_baseline.json` was regenerated once with `test-support/companion_render_snapshot.py --write`. Review used a throwaway script (scratchpad, not committed) comparing the old file from git against the new one:

- the `unauthenticated` map (56 routes: statuses and Location headers, 404 body samples) is byte-identical;
- the page key sets are identical (48 pages);
- 44 page entries differ, and for every one, deleting the single `<span class="banner__pill" ...>Legacy access</span>` (or its French form `Ancien accès`) from the new HTML reproduces the old HTML exactly. No other difference exists.

The change is therefore only the neutral legacy-access pill that the legacy-admin principal now renders on every authenticated page.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing tests broke because fleet.db is now a second SQLite connection**
- **Found during:** Task 2 full run
- **Issue:** Three fault-injection tests patch `sqlite3.connect` globally after login (so the session lookup itself failed with 503), and `efficiency_probe.count_db()` counted the new fleet.db connection against the one-connection-per-request history assertions.
- **Fix:** The three injectors pass fleet.db connects through (history.db is still faulted); `count_db()` does not count fleet.db connections, since those counts are about history.db. No assertion weakened.
- **Files:** companion/test_request_connections.py, companion/test_page_context.py, companion/test_freshness_token.py, test-support/efficiency_probe.py
- **Commit:** c547f10

**2. [Rule 2 - Missing critical functionality] 503 page needed a bilingual body**
- **Issue:** No existing page fit "session store unreadable".
- **Fix:** Added `login_page.unavailable_page` and French strings in `companion/i18n_fr/common.py`.
- **Commit:** c547f10

## Notes for later plans

- `access.home_for()` returns `/account` for a user principal, but no `/account` route exists yet; a signed-in user visiting /login is redirected to a 404 until the Account route lands.
- The stateless token functions (`issue_session_token`, `verify_session_token`, `revoke`, `is_revoked`) remain in auth.py unused by the request path; their tests still pass; removal is plan 07.
- Flag-off behaviour of the password form and POST /login (403) is not part of this plan: with the flag off a freshly created legacy session is refused on the next request.

## Verification

- `pytest companion server stub-server -n auto` including the Playwright browser tests (SKYPANE_REQUIRE_BROWSER=1): 4379 passed, 7 skipped (root-permission skips). `stub-server/test_phase47_freeze.py` green.
- ruff, mypy, function-size (611 functions, none over 80) and comment-history gates pass.
- No change to `stub-server/byos_server.py`, firmware or `measured_fields_freeze.json`. No secrets, no external network.

## Self-Check: PASSED

Files exist (access.py, test_access.py, test_sessions_http.py) and commits cd5a7b1, c547f10 and the baseline commit are in git log.
