---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
fixed_at: 2026-10-30T00:00:00Z
review_path: .planning/workstreams/v1-2/phases/54-auth0-sign-in-local-roles-and-default-deny-access/54-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 54: Code Review Fix Report

**Source review:** 54-REVIEW.md (warnings WR-01 to WR-06; Info items out of scope)
**Branch:** milestone/v1.2-phase-54-auth0 (one commit per finding, not pushed)

## Fixed Issues

### WR-01: Immutable read-only fallback can serve a revoked session
**Commits:** cecf15e0, 175d9512 (fallback moved into `fleet_db.connect_readonly_fallback` to keep `companion/app.py` under the 1500-line ceiling)
**Files:** `companion/app.py`, `server/fleet_db.py`, `companion/test_sessions_http.py`
The read-only fallback in `_fleet_conn` now re-raises (503) when `fleet.db-wal` exists and is non-empty (or cannot be inspected), and prints one log line (no secrets) each time the fallback engages or is refused. Tests: fallback reads and logs; pending WAL answers 503; empty WAL still reads.

### WR-02: Read-only fallback turns an expired session into a 503
**Commit:** 24c5e294
**Files:** `server/fleet_sessions.py`, `server/test_fleet_sessions.py`
Dead-session cleanup in `lookup_session` goes through a best-effort `discard_session` that swallows `sqlite3.OperationalError`, like the idle touch. A stale cookie on a read-only store reads as no session. Test: expired and idle sessions return None on an immutable store.

### WR-03: Legacy-admin sessions revive when the flag is re-enabled
**Commits:** 6272713c, 760faf5c (access-matrix test updated)
**Files:** `companion/app.py`, `companion/test_sessions_http.py`, `server/fleet_sessions.py`
Per the owner's decision, sessions stay independent of the shared password; a password change does not end them (covered by a test). When a legacy-admin session is presented while the legacy flag is cleanly off, its row is deleted (writable store only), so re-enabling the flag does not revive it. A malformed flag still only fails closed and deletes nothing. The existing test that expected revival was changed to expect the new behaviour. Human check suggested: this is a behavioural change to session lifecycle.

### WR-04: Unauthenticated `/login/auth0` can evict in-flight sign-ins
**Commit:** b7844c44
**Files:** `companion/oidc.py`, `companion/sign_in.py`, `test-support/companion_app_server.py`, `companion/test_auth0_login.py`
New `oidc.StartThrottle`: bounded per-client (same key as the login throttle, IPv6 collapsed to /64) sliding window, 30 starts per 60 s. Over the limit the start answers 429 with the generic "Sign-in is not available right now" page and no cookie. A plain `LoginThrottle` was not reused because it does not decay below its limit, which would punish ordinary users over time. `InProcessAppServer` resets the throttle so test servers do not share state.

### WR-05: Linking runs before session creation
**Commit:** 062fdf95
**Files:** `server/fleet_sessions.py`, `companion/sign_in.py`, `server/test_fleet_sessions.py`, `companion/test_auth0_login.py`
New `fleet_sessions.sign_in_user` resolves/links the identity and stores the session (with rotation) in one `BEGIN IMMEDIATE` transaction. The callback creates the session token before resolution and `_land_signed_in` no longer writes. Tests: rollback of the link when the session insert fails (unit and HTTP), refused login writes nothing.

### WR-06: Sessions are never pruned
**Commit:** f2d41212
**Files:** `server/fleet_sessions.py`, `server/test_fleet_sessions.py`
Session creation (password login and Auth0 sign-in) calls `prune_expired` inside its transaction, at most once per `PRUNE_INTERVAL_S` (1 hour) per process; a backwards clock counts as due. No `fleet_cli` startup prune, as requested.

## Skipped Issues

None.

---

_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
