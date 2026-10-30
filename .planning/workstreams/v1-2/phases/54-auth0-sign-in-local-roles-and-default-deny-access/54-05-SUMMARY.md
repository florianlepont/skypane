---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 05
subsystem: auth
tags: [auth0, oidc, pkce, sessions, invite-only, companion]
requires:
  - phase: 54-01
    provides: fleet_sessions.resolve_login / create_session / delete_session
  - phase: 54-02
    provides: oidc.py (config, PKCE, token exchange, claim validation, AttemptTable) and the loopback FakeAuth0
  - phase: 54-03
    provides: login_page sign-in, error, not-invited and interstitial pages
  - phase: 54-04
    provides: Principal, decide(), Handler._fleet_conn / _principal
provides:
  - companion/sign_in.py SignInMixin with GET /login/auth0, GET /callback, POST /logout
  - sp_oidc Lax pre-login cookie helpers in auth.py
  - login_via_auth0 / begin_auth0 / auth0_env test helpers and auth0_rig fixtures
affects: [54-06, 54-07, 54-08]
tech-stack:
  added: []
  patterns:
    - "Callback order: attempt, provider error, state, token exchange, claims, invited-user resolution, session"
    - "200 interstitial with meta refresh instead of 303 for Strict-cookie survival"
key-files:
  created:
    - companion/sign_in.py
    - companion/test_auth0_login.py
    - companion/test_auth0_cookies.py
  modified:
    - companion/app.py
    - companion/auth.py
    - companion/routes.py
    - companion/conftest.py
    - companion/test_route_table.py
    - test-support/companion_app_server.py
key-decisions:
  - "Auth0 settings are read from os.environ per request, so in-process tests change only the environment"
  - "send_html gained set_cookies so a response can carry the session and the cleared pre-login cookie together"
  - "Handler gained _clock() and _next_route_of() so the mixin never imports companion.app"
requirements-completed: []
duration: 60min
completed: 2026-10-30
---

# Phase 54 Plan 05: Auth0 sign-in, callback and sign-out Summary

An invited person now signs in through Auth0 authorization code + PKCE (S256) with state and nonce held server-side, lands through a 200 meta-refresh interstitial, and signs out through an Auth0 hop; every failure is a generic page with no session and no durable write.

## Tasks

1. SignInMixin handlers, routes and cookie helpers (a3c9beb)
   - `/login/auth0` and `/callback` are PUBLIC routes; the route-table expectation lists exactly them.
   - The old `_handle_logout_post` was removed from app.py; sign_in.py's version deletes the session first, then returns an interstitial to Auth0 `/v2/logout` for a user principal with Auth0 configured, else a 303 to `/login`.
   - The login page now receives `auth0_enabled` and `legacy_enabled`.
   - Logs carry reason codes and numeric user ids only.
2. login_via_auth0 helper and failure-mode suite (99aeca7)
   - 50 tests across `test_auth0_login.py` and `test_auth0_cookies.py`: both roles, rotation, 13 broken-token/provider cases, state mismatch (token endpoint never called), missing and expired attempts, single use, replayed code, wrong verifier, slow token endpoint, four uninvited variants with identical 403 bodies, link race, `next` whitelist and open-redirect table, cookie attributes from real Set-Cookie bytes, authorize URL contents, logout variants, and a log-capture check on subprocess output.

## Verification

- `pytest companion server stub-server -n auto` (SKYPANE_REQUIRE_BROWSER=1): 4431 passed, 7 skipped (root-permission skips).
- ruff, mypy, function-size (max 80), comment-history all clean; `stub-server/test_phase47_freeze.py` green; no change to `stub-server/byos_server.py`, firmware or `measured_fields_freeze.json`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Shared fixtures added to companion/conftest.py**
- **Found during:** Task 2
- **Issue:** Both new test modules need the same server-plus-fake wiring; conftest.py is not in the plan's file list.
- **Fix:** Added `Auth0Rig`, `auth0_rig` (in-process) and `auth0_subprocess_rig` there, following the repo's shared-fixture convention.
- **Files modified:** companion/conftest.py
- **Commit:** 99aeca7

**2. [Rule 3 - Blocking] http_request_full / apply_env in the test-support server module**
- **Issue:** `http_request` collapses repeated Set-Cookie headers into a dict, and the callback sets two cookies; `InProcessAppServer` had no way to change environment per test.
- **Fix:** Added `http_request_full`, `named_cookie`, `set_cookie_headers` and `InProcessAppServer.apply_env` (restored on stop); `login()` untouched.
- **Commit:** 99aeca7

## Known Stubs

None. `home_for()` sends a user to `/account`, which has no route until plan 06; the sign-in interstitial points there already (404 until then). With the legacy flag off, POST /login still creates a legacy session that the next request refuses (plan 07 adds the 403).

## Threat Flags

None beyond the plan's threat model.

## Self-Check: PASSED

Files companion/sign_in.py, companion/test_auth0_login.py, companion/test_auth0_cookies.py exist; commits a3c9beb and 99aeca7 exist.
