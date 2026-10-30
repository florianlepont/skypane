---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 08
subsystem: auth
tags: [access-matrix, default-deny, idor, byos, sessions, tests]
requires:
  - phase: 54-04
    provides: access.decide, server-side sessions, Route/Access table
  - phase: 54-06
    provides: Account route and signed-in policy
provides:
  - Hand-written route x principal policy table with a completeness forcing function
  - HTTP matrix over recording stubs plus a test-only /d/<id>/_probe owner family
  - AUTH-06 proof that frame and companion credentials never cross
affects: [54-09, device-routes phase]
tech-stack:
  added: []
  patterns:
    - "Matrix harness: replace routes.ROUTES with recording stubs; real routes only append a ROUTE_POLICY row"
key-files:
  created:
    - companion/test_access_matrix.py
    - test-support/access_matrix_support.py
    - stub-server/test_auth_independence.py
  modified: []
key-decisions:
  - "Sessions for the matrix come from real flows (Auth0 fake for user/other/admin, password for legacy-admin) on one module-scoped in-process server; only the disabled/deleted/expired/demoted variants are seeded directly"
  - "Policy table is keyed by (method, path template) with literal strings; static assets take their public rows from static_files.STATIC_ROUTES"
requirements-completed: []
duration: 35min
completed: 2026-10-30
---

# Phase 54 Plan 08: Default-deny matrix and frame-auth independence Summary

A hand-written route x principal table (654 test cells) proves default-deny over every route in `routes.ROUTES` and a test-only device-scoped probe family proves the owner dimension; a second file proves frame authentication is untouched by Auth0 and sessions. No production code changed.

## What was built

- `companion/test_access_matrix.py`: `ROUTE_POLICY` (public / signed-in / admin-only per route, independent of `route.access`), pure `access.decide` layer, completeness test that names the route missing a row, HTTP layer, probe family, session-state variants, and the user-404 shell check (no Health link or admin nav).
- `test-support/access_matrix_support.py`: `seed_matrix_fleet`, `session_cookie_for`, `stub_routes`, `probe_routes`, `Recorder`.
- `stub-server/test_auth_independence.py`: device content and frame poll byte-identical after sign-in, linking, unlinking, disabling and session deletion; session cookie refused by byos; device token, secret and secret hash refused (as cookie or bearer) by companion routes; frame auth works with Auth0 stopped or unconfigured.

## Verification

- Completeness check: a dummy `GET /d/{}/x` route added to `routes.ROUTES` in a scratch run (not committed) made the completeness test fail with `routes with no expectation row ... [('GET', '/d/{}/x')]`.
- ruff, mypy, function-size gate (611 functions, none over 80), comment-history check pass; `test_phase47_freeze.py`, `test_fleet_auth.py` and `test_suite_guards.py` green.
- `git diff` shows no change to `stub-server/byos_server.py`, `measured_fields_freeze.json` or `firmware/`.

## Deviations from Plan

None - plan executed as written. A run cut off by an API rate limit was restarted from the first task; nothing had been committed.

## Known Stubs

None.

## Commits

- c7ea2d86 test(54-08): prove default-deny across every route, principal and device owner
- 9bc03a84 test(54-08): prove frame authentication is independent of Auth0 and sessions
