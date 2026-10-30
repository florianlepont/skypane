---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
reviewed: 2026-10-30T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - companion/oidc.py
  - companion/sign_in.py
  - companion/sign_in_config.py
  - companion/access.py
  - companion/app.py
  - companion/auth.py
  - companion/routes.py
  - companion/login_page.py
  - server/fleet_db.py
  - server/fleet_sessions.py
  - server/fleet_migrate.py
  - stub-server/fleet_cli.py
  - deploy/Caddyfile
  - deploy/README.md
findings:
  critical: 0
  warning: 6
  info: 5
  total: 11
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2026-10-30
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

I found no auth bypass, open redirect, session fixation or account-takeover path in the normal writable deployment. These checks hold:

- **Claim checks:** `iss` is an exact match including the trailing slash. `aud` accepts a string or a list. `azp` is enforced when `aud` has several entries or `azp` is present. `exp` and `iat` use a 60 s leeway. `alg` of `none` is refused. The nonce comparison is constant-time. `sub` must be a non-empty string of at most 255 characters.
- **Login flow:** state and PKCE are bound to a one-use, TTL'd, capacity-bounded attempt. That attempt is tied to the browser by an HttpOnly `Lax` cookie scoped to `/callback`.
- **Linking:** it requires `email_verified is True`. It is a conditional `UPDATE ... WHERE iss IS NULL AND sub IS NULL AND disabled = 0` inside `BEGIN IMMEDIATE`, so the race is closed. The role is read only from `users`, never from Auth0.
- **Sessions:** the token is regenerated on every login, and the old session row is deleted in the same transaction. Only the sha256 is stored.
- **Dispatch gate:** `Route.__new__` refuses a route without an `Access`. Store errors answer 503, never allow.
- **Legacy password:** the compare uses `hmac.compare_digest`. It is skipped entirely when the legacy flag is off.
- **Secrets:** the client secret is `repr=False`. No log line carries a code, token or claim value.

The weaknesses are in the degraded read-only path, in operational lifecycle (revocation, pruning, DoS of the pre-login table), and in a few robustness gaps.

## Warnings

### WR-01: Immutable read-only fallback can serve a revoked, disabled or demoted session

**File:** `companion/app.py:571-583` (with `server/fleet_db.py:221-243`)
**Issue:** `_fleet_conn()` falls back to `connect_readonly(..., immutable=True)` whenever `fleet_db.connect` raises `OperationalError` and `os.access(state_dir, W_OK)` is false. `fleet.db` runs in WAL mode. `immutable=1` makes SQLite ignore the `-wal` and `-shm` files and read only the main database file.

Failure scenario: the state dir becomes unwritable after startup. Examples are a systemd `ReadWritePaths` mistake, a read-only remount, or a permission change. Before that, an admin ran `fleet_cli users disable` (or `unlink-identity`), which deleted the session rows. Those deletes sit in the WAL and are not yet checkpointed. Every request then opens the stale main file, where the disabled user's session row still exists with `disabled = 0` and the old role. That session passes `lookup_session` and is treated as live. Sessions created since the last checkpoint are invisible, which fails closed. Revocations and demotions are invisible, which fails open.

In a normal writable deployment the fallback is not reachable, because `main()` opens `fleet.db` at startup and `os.access` is true. But `os.access` is evaluated at request time and uses the real UID. The fallback is silent: nothing is logged, so the operator never learns that revocation has stopped working.

**Fix:**
1. In the fallback, refuse to serve when a non-empty `fleet.db-wal` exists. Re-raise, which gives a 503, instead of reading stale data.
2. Log once when the fallback engages.
3. Keep `immutable=1` only for a database with no pending WAL.

```python
wal = fleet_db.fleet_db_path(self.args.state_dir) + "-wal"
if os.path.exists(wal) and os.path.getsize(wal) > 0:
    raise
```

**Fixed in cecf15e0**.

### WR-02: Read-only fallback turns an expired session into a 503

**File:** `server/fleet_sessions.py:93-99`
**Issue:** `lookup_session` calls `delete_session` for an expired, idle-expired or orphaned row. In the read-only connection that raises `sqlite3.OperationalError`, and the touch `UPDATE` is guarded but these `DELETE`s are not. `_dispatch` maps the error to a 503. A user holding a stale cookie then sees "unavailable" on every gated route instead of being sent to login. It is also inconsistent with the touch path, which does swallow the error.
**Fix:** In `lookup_session`, wrap the cleanup deletes in the same `try/except sqlite3.OperationalError: pass`. Return `None` regardless.

**Fixed in 24c5e294**.

### WR-03: Legacy-admin sessions survive a password change and revive when the flag is re-enabled

**File:** `companion/auth.py:1-9`, `companion/app.py:603-620`
**Issue:** The old session value was derived from the password, so changing `SKYPANE_COMPANION_PASSWORD` invalidated every session. Sessions are now independent random tokens (see the `auth.py` docstring: "a session outlives ... a password change"). If the shared password is compromised and the owner rotates it, an attacker's existing legacy-admin session stays valid for up to 30 days. Only turning the legacy flag off ends them.

Setting the flag to `0` hides legacy rows without deleting them. Setting it back to `1` makes any unexpired legacy-admin row valid again.
**Fix:**
- On companion start, or when the legacy flag is off, run `DELETE FROM sessions WHERE principal = 'legacy-admin'`.
- Store a fingerprint of the configured password (HMAC of a fixed label, keyed by the password) on the session row or in `meta`. Delete the legacy sessions when it changes.
- At minimum, document that rotating the password does not log anyone out.

**Fixed in 6272713c** (revival only; sessions deliberately stay independent of the shared password).

### WR-04: Unauthenticated `/login/auth0` can evict legitimate in-flight sign-ins

**File:** `companion/oidc.py:376-387`, `companion/sign_in.py:68-84`
**Issue:** `AttemptTable.create` is reachable without authentication and without a throttle. At capacity (4096) it evicts the oldest attempts first (`popitem(last=False)`). An attacker who issues 4096 GETs to `/login/auth0` within 10 minutes removes every real user's pending attempt. Their `/callback` then fails with "expired", so sign-in is denied for the attacker's chosen duration, at the cost of about 7 requests per second.
**Fix:**
- Rate-limit attempt creation per client IP, reusing `LoginThrottle` and `login_throttle_key`.
- Cap attempts per source. Alternatively, refuse new attempts at capacity (503) rather than evicting existing ones.

**Fixed in b7844c44**.

### WR-05: `IntegrityError` and other sqlite errors during linking are not distinguished, and linking runs before role verification

**File:** `companion/sign_in.py:142-149, 161-171`
**Issue:** `resolve_login` links the identity and commits first. `_land_signed_in` then re-reads the role and may refuse (role `None`). The user stays linked even though sign-in reported a failure. If a store error hits `_land_signed_in` after the commit, the identity is already bound with no session. This is not exploitable, because the link is made only for a verified email. It does mean a failed login has a durable side effect, which contradicts the docstring ("no durable write" on failure).
**Fix:** Create the session in the same transaction as linking. Alternatively, update the docstring to say that linking is committed before session creation.

**Fixed in 062fdf95**.

### WR-06: Sessions are never pruned in production

**File:** `server/fleet_sessions.py:132-137`
**Issue:** `prune_expired` has no non-test caller. Rows are removed only when that exact token is presented again. Abandoned sessions (closed tabs, lost devices, legacy sessions after the flag goes off) accumulate in `sessions` and are carried through backups (the README notes that restores bring back unexpired sessions). Growth is slow, but the table is unbounded, and a restored backup resurrects stale-but-unexpired sessions.
**Fix:** Call `prune_expired` under a transaction at companion startup and at most once per N minutes (for example inside `create_session`). The sessions table is small, so the cost is trivial.

**Fixed in f2d41212**.

## Info

### IN-01: Session-clock inconsistency (`_now()` vs `self._clock()`)

**File:** `companion/app.py:612-613` vs `companion/sign_in.py:146,177`
**Issue:** `_resolve_principal` and `_start_legacy_session` use the module `_now()`. The sign-in path uses the overridable `self._clock()`. A test or an operator-level clock override moves only half of the system, for example a session created at fake time T that is never found at real time.
**Fix:** Use `self._clock()` everywhere.

### IN-02: Legacy-login audit line logs the client IP bucket

**File:** `companion/app.py` (`_handle_login_post`, the `legacy_login_success` and `legacy_login_lockout` prints)
**Issue:** The line prints the throttle key, which is the client IP or /64, to journald. It is probably wanted for audit. It is still personal data, and it is not covered by the "reason codes and numeric ids only" claim in `sign_in.py`.
**Fix:** Keep it deliberately and document it in the privacy notes, or hash the key.

### IN-03: Auth0 domain is not normalized to lower case

**File:** `companion/oidc.py:111-127`
**Issue:** `iss` is compared exactly against `https://<domain>/`. A domain configured with upper case (`Tenant.EU.auth0.com`) never matches Auth0's lower-case `iss`. Every login then fails with the same generic `token_iss` page. This fails closed, but it is hard to diagnose.
**Fix:** `domain = values[ENV_DOMAIN].lower()`.

### IN-04: Logout with an invalid or expired cookie leaves the cookie in the browser

**File:** `companion/sign_in.py:193-220`, `companion/routes.py` (`/logout` is `SIGNED_IN`)
**Issue:** When the session is no longer valid, the dispatch gate answers `LOGIN` (a 303) before `_handle_logout_post` runs. The stale `sp_session` cookie is not cleared. This is harmless because the cookie is dead server-side. It is untidy, and the user keeps re-sending a dead cookie.
**Fix:** Make `/logout` `PUBLIC` and let the handler clear the cookie. It already tolerates a missing principal.

### IN-05: Pre-link email trust and no `__Host-` cookie prefix (design notes)

**File:** `server/fleet_sessions.py:175-198`, `companion/auth.py:105-117`
**Issue:**
- An invited but unlinked row is claimable by whoever first proves control of that email at the tenant. This is safe only while the tenant has sign-ups disabled and no social connections. The README states this, but nothing in the code enforces it. A `unlink-identity` run opens the same window again.
- The session cookie has no `__Host-` prefix, so a same-site sibling subdomain could plant or overwrite it. The prefix would also guarantee `Secure` and `Path=/`.

**Fix:** Keep the tenant-hardening step in the deploy checklist and in the smoke test. Consider renaming the cookie to `__Host-sp_session`, which is possible only when `Secure` is always on.

---

_Reviewed: 2026-10-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
