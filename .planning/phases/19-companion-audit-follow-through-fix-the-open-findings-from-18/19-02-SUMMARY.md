---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 02
subsystem: auth
tags: [hmac, session-tokens, cookies, login-throttle, revocation, stdlib-only]

# Dependency graph
requires:
  - phase: 06
    provides: companion/auth.py's original shared-password session gate (LoginThrottle, stateless HMAC tokens, cookie builders)
provides:
  - "A self-releasing login lockout (LoginThrottle.record_failure() resets the failure counter once its window has elapsed)"
  - "Session tokens signed with a per-process derived key (HMAC-as-KDF) instead of the raw shared password"
  - "A pruned, lock-guarded in-memory revocation set (auth.revoke()/auth.is_revoked()) consulted from the single _is_authenticated() predicate"
  - "POST /logout revokes the presented token server-side, closing the cookie-replay-after-Sign-out hole"
  - "A nanosecond-resolution session-token expiry field, preventing same-second token collisions now that identity-based revocation exists"
  - "An explicit, fail-closed SKYPANE_COMPANION_INSECURE_COOKIES=1 opt-out for the Secure cookie flag, for plain-http LAN/dev runs"
affects: [19-04, any future plan touching companion/auth.py or companion/app.py's do_POST()/_is_authenticated()]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HMAC-as-KDF: hmac.new(configured_password(), _PROCESS_SALT, hashlib.sha256).digest() as a signing key, never the raw password directly"
    - "Revocation set pruned by its own embedded expiry on every access (revoke()/is_revoked()), guarded by threading.Lock(), mirroring app.py's _POLL_LOCK"
    - "Read-fresh-per-call env flag with fail-closed semantics (secure_cookie_flag()), mirroring configured_password()'s os.environ.get() idiom"

key-files:
  created: []
  modified:
    - companion/auth.py
    - companion/app.py
    - deploy/skypane.env.example
    - companion/test_companion_app.py

key-decisions:
  - "LoginThrottle.record_failure() resets self._failures to 0 only when the previous window has fully elapsed AND the counter was already saturated - never touches locked_out()/record_success()/seconds_remaining()"
  - "The revocation set lives in companion/auth.py (not app.py), per the orchestrator's own resolution recorded in 19-RESEARCH.md"
  - "_is_authenticated() is the single, sole call site for the new auth.is_revoked() check - never duplicated at any of the 9+ require_session() call sites"
  - "Switched issue_session_token()'s embedded expiry from second- to nanosecond-resolution (time.time_ns()) - a deviation not in the plan text, needed because identity-keyed revocation exposed that two logins in the same wall-clock second previously produced byte-identical tokens, so revoking one could silently revoke a different, still-legitimate session"
  - "Named the Secure-flag helper auth.secure_cookie_flag() (no leading underscore) rather than a Python-private name, since companion/app.py's _handle_theme_post() needs to call it too, and no precedent exists in this codebase for cross-module access to underscore-prefixed names"

requirements-completed: [CFG-01, CFG-03]

# Metrics
duration: 17min
completed: 2026-09-11
---

# Phase 19 Plan 02: Auth Hardening — Lockout, Signing Key, Revocation, Secure Cookie Summary

**Self-releasing login lockout, HMAC-as-KDF session signing with a per-process salt, server-side Sign-out revocation, and a fail-closed dev-only Secure-cookie opt-out — closing A-32/A-33/A-34 from the phase 18 audit.**

## Performance

- **Duration:** ~17 min (first task commit to last)
- **Started:** 2026-09-11T06:51:28Z (worktree base commit)
- **Completed:** 2026-09-11T07:07:44Z
- **Tasks:** 3/3
- **Files modified:** 4

## Accomplishments
- A lockout now needs five fresh failures per window, never permanent (A-32/D-15)
- Session tokens are signed with a key derived from the shared password and a per-process random salt, not the raw password (A-33/D-16)
- Sign out revokes the presented token server-side; replaying the same cookie after logout is now rejected (A-33/D-16)
- The Secure cookie flag is on by default, droppable only via an explicit, fail-closed dev-only env var (A-34/D-17)
- Discovered and fixed a same-second token-collision hazard that the revocation feature itself introduced (see Deviations)

## Task Commits

Each task was committed atomically:

1. **Task 1: Make the login lockout self-releasing (D-15)** - `bed57d8` (fix)
2. **Task 2: Derive the signing key and revoke tokens on Sign out (D-16)** - `e6de821` (fix)
3. **Task 3: Make the Secure cookie flag explicitly opt-out-able (D-17)** - `8156183` (fix)

**Plan metadata:** committed as part of this SUMMARY's own commit (worktree mode - orchestrator handles STATE.md/ROADMAP.md centrally after merge)

## Files Created/Modified
- `companion/auth.py` - `LoginThrottle.record_failure()` window-reset fix; `_PROCESS_SALT`/`_signing_key()` HMAC-as-KDF; `_REVOKED`/`_REVOKED_LOCK`/`revoke()`/`is_revoked()`/`_prune_revoked_locked()`; nanosecond-resolution token expiry; `secure_cookie_flag()` and its use in both cookie builders
- `companion/app.py` - `_is_authenticated()` now consults `auth.is_revoked()`; the `LOGOUT_ROUTE` branch of `do_POST()` calls `auth.revoke()` on the presented token before clearing the cookie; `_handle_theme_post()`'s cookie routed through `auth.secure_cookie_flag()`
- `deploy/skypane.env.example` - documents `SKYPANE_COMPANION_INSECURE_COOKIES`, commented out, as never-set-in-production
- `companion/test_companion_app.py` - 9 new checks across the three tasks (2 lockout-release checks, 4 signing-key/revocation checks, 3 Secure-cookie-opt-out checks); `EXPECTED_CHECK_COUNT` re-derived from 192 to 201 across three appended assignments; updated the stale `_tab_refused_after_logout` comment that had claimed a resent cookie "would still verify, by design" (no longer true post-D-16)

## Decisions Made
- Per-IP login throttling stays deferred (19-CONTEXT.md Deferred Ideas) - the global `LoginThrottle` counter is the correct scope for one shared household password; documented in the class docstring
- The revocation set lives in `companion/auth.py`, matching the orchestrator's resolution in 19-RESEARCH.md, modeled on `LoginThrottle`'s own "process-global, not per-session" framing and guarded by a `threading.Lock()` mirroring `app.py`'s `_POLL_LOCK`
- `secure_cookie_flag()` was named without a leading underscore (deviating from the plan's "private helper" wording) because `companion/app.py`'s `_handle_theme_post()` needs to call it cross-module, and this codebase has no precedent for reaching into another module's underscore-prefixed names

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Same-second session-token collision made revocation revoke the wrong session**
- **Found during:** Task 2 (Derive the signing key and revoke tokens on Sign out)
- **Issue:** `issue_session_token()`'s expiry field was second-resolution (`int(time.time()) + SESSION_TTL_S`). Since tokens are a pure function of `(expiry, signing_key)`, two `issue_session_token()` calls landing in the same wall-clock second produced byte-identical token strings. Once identity-keyed revocation existed, this meant revoking one session's token on Sign out could silently revoke a *different*, still-legitimate session that happened to be issued in the same second — confirmed directly (`issue_session_token()` called twice in a tight loop returned the identical string) and observed as a real cascade of ~20 failing checks later in `companion/test_companion_app.py` once a post-logout re-login collided with the just-revoked token.
- **Fix:** Switched the embedded expiry to nanosecond resolution (`time.time_ns()` in `issue_session_token()`/`verify_session_token()`; `revoke()`/`_prune_revoked_locked()` updated to match), keeping the existing `"<int>.<hex>"` two-field token shape and every existing round-trip/forged-token check's behavior unchanged - only the unit of the integer changed, not the format.
- **Files modified:** `companion/auth.py`
- **Verification:** Full harness re-run went from ~20 unrelated cascading failures to exactly the two documented pre-existing root-sandbox failures; `companion/test_companion_app.py` reports 199/201 (later 201 total after Task 3), both fails being the documented WR-11 read-only-state-dir cases
- **Committed in:** `e6de821` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — without this fix, the revocation feature added by this same task would have a real (if narrow) production risk of one session's Sign out invalidating an unrelated concurrent session, and the test suite would fail non-deterministically depending on execution speed. No scope creep beyond the two functions (`issue_session_token()`/`verify_session_token()`) and their two direct consumers (`revoke()`/`_prune_revoked_locked()`) this task was already modifying.

## Issues Encountered
None beyond the deviation above.

## User Setup Required

None - no external service configuration required. `SKYPANE_COMPANION_INSECURE_COOKIES` is an optional, commented-out, dev-only opt-out documented in `deploy/skypane.env.example`; it must never be set on the production VPS.

## Self-Check: PASSED

- FOUND: companion/auth.py
- FOUND: companion/app.py
- FOUND: deploy/skypane.env.example
- FOUND: companion/test_companion_app.py
- FOUND commit bed57d8
- FOUND commit e6de821
- FOUND commit 8156183

## Next Phase Readiness
- A-32/A-33/A-34 are closed; `companion/auth.py`'s public `issue_session_token()`/`verify_session_token()` contract shape is unchanged (only the expiry field's unit changed, transparently to callers)
- 19-04 (which adds the `require_session()` gate to the `/logout` branch and the CSP/hardening-header work) can build directly on this plan's `LOGOUT_ROUTE` revoke-call placement without further changes to that branch's revoke logic
- No blockers for subsequent phase-19 plans

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 02*
*Completed: 2026-09-11*
