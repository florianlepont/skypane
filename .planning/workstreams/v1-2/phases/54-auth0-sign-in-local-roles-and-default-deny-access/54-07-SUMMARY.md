---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 07
subsystem: auth
tags: [legacy-admin, startup-validation, audit, sessions, companion]
requires:
  - phase: 54-04
    provides: server-side sessions, legacy-admin principal, legacy flag helper
  - phase: 54-05
    provides: Auth0 sign-in handlers and password_off error kind
provides:
  - Flagged shared-password login (403 when off, audit lines, throttle kept)
  - validate_sign_in_config fail-closed startup rules
  - auth.py without the stateless password-derived token API
affects: [54-08, 54-09]
tech-stack:
  added: []
  patterns:
    - "Startup refuses a half-configured sign-in setup, naming variables only"
key-files:
  created:
    - companion/sign_in_config.py
    - companion/test_legacy_admin.py
    - .planning/workstreams/v1-2/phases/54-auth0-sign-in-local-roles-and-default-deny-access/54-LEGACY-ADMIN-REMOVAL.md
  modified:
    - companion/app.py
    - companion/auth.py
    - companion/login_page.py
    - companion/test_companion_app_01.py
key-decisions:
  - "validate_sign_in_config lives in companion/sign_in_config.py: app.py would otherwise cross the 1500-line file ceiling"
  - "auth.configured_password takes an optional environ so startup validation reuses it"
  - "Only a success and a lockout transition are audited; the lockout line prints once, on the failure that arms it"
requirements-completed: []
duration: 40min
completed: 2026-10-30
---

# Phase 54 Plan 07: Legacy-admin flag, audit, fail-closed startup Summary

The shared password is now a flagged, throttled, audited legacy-admin fallback, the companion refuses unsafe sign-in configurations at startup, and the password-derived token machinery is deleted.

## Tasks

1. Flag behaviour, audit lines, startup rules (4569690)
   - With SKYPANE_LEGACY_PASSWORD_LOGIN=0, POST /login answers 403 "Password sign-in is turned off" before reading the form; password_ok and every throttle method are proven not called, and repeated POSTs never lock the bucket. Existing legacy sessions are refused on the next request.
   - One audit line per success (`legacy_login_success principal=legacy-admin bucket=<ip>`) and per lockout; the submitted password never appears (captured stdout test).
   - `validate_sign_in_config(environ)` rejects an invalid flag value, a missing password while the flag is on, a partial Auth0 set (names missing variables only), and a setup with no usable method. Subprocess tests cover each case plus the two that must start.
   - A session survives a restart with a different password; signatures keyed from either password are refused.
2. Token API deletion and test rewrite (5119d08)
   - Removed `_PROCESS_SALT`, `_signing_key`, `_REVOKED`, `revoke`, `is_revoked`, `issue_session_token`, `verify_session_token`, `SESSION_TTL_S`; module docstring describes the opaque-token model.
   - Section 1 of test_companion_app_01.py now tests token entropy and uniqueness, hash determinism, 30-day cookie Max-Age, constant-time compare, non-string input, and asserts the retired names are absent.
   - 54-LEGACY-ADMIN-REMOVAL.md records the event-driven trigger and removal steps.

## Deviations from Plan

**1. [Rule 3 - Blocking] Startup validation moved to companion/sign_in_config.py**
- **Found during:** full suite (test_structure_guards line ceiling)
- **Issue:** app.py reached 1512 lines, over the 1500 ceiling.
- **Fix:** moved SignInConfigError and validate_sign_in_config to a new module; app.main() calls it.
- **Commit:** 5119d08

**2. [Rule 1 - Bug] "Not configured" notice overrode the password-off notice**
- **Found during:** Task 1 test
- **Issue:** login_page replaced any notice with "Sign-in is not configured" when neither method was on, so the 403 page lost its message.
- **Fix:** the not-configured notice applies only when no other notice is given.
- **Files modified:** companion/login_page.py
- **Commit:** 4569690

No baseline regeneration was needed (render baseline unchanged).

## Verification

- Full suite `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`: 5055 passed, 1 failed (the line ceiling above, fixed afterwards); the affected modules, freeze test (stub-server/test_phase47_freeze.py) and the non-root run (353 passed) are green after the fix. The full suite was not re-run end to end after the final move.
- ruff, mypy, function-size (611 functions, none over 80) and comment-history gates pass.
- No change to stub-server/byos_server.py, firmware or measured_fields_freeze.json.

## Known Stubs

None.

## Self-Check: PASSED

Files and commits 4569690, 5119d08 exist.
