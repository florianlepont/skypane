---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
verified: 2026-10-30T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Real Auth0 tenant smoke test"
    expected: "Invited user signs in; a wrong code_verifier is rejected; sign-out returns to the allowed logout URL and the next sign-in prompts for credentials; an uninvited Auth0 account gets the not-invited page"
    why_human: "Real external tenant; CI only uses the loopback fake Auth0"
  - test: "caddy validate on the VPS and a real /callback line in journalctl -u caddy"
    expected: "Config validates; no code/state query values logged"
    why_human: "Redaction is asserted as text only in the repo tests; needs the production Caddy"
  - test: "Stamp the legacy-admin 'remove by' date at go-live"
    expected: "54-LEGACY-ADMIN-REMOVAL.md carries a date; SKYPANE_LEGACY_PASSWORD_LOGIN=0 set and removal executed"
    why_human: "Event-driven trigger (D-08); the date is the owner's decision at go-live"
---

# Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access - Verification

**Goal:** Invited users can sign in with Auth0, and every route enforces a minimum role and device ownership.
**Status:** passed. Verified as `human_needed` on 2026-10-30 (no code gaps, owner go-live items remaining); the owner completed those items on 2026-10-30 and 2026-10-31 (see "Real-tenant verification" and "Owner production tests, 2026-10-31" below) and closed the phase on 2026-10-31. One requirement stays open and is carried to Phase 55: the real per-device rows of the route x role x owner matrix (AUTH-03), see "Not achievable until Phase 51" below.

## Targeted tests (run by the verifier)

`pytest companion/test_oidc.py companion/test_auth0_login.py companion/test_access_matrix.py companion/test_legacy_admin.py stub-server/test_auth_independence.py stub-server/test_phase47_freeze.py -n0 --no-cov` gave 812 passed in 59 s. `check_function_size.py check --max 80 server stub-server` scanned 618 functions, none over 80. `check_comment_history.py check` and `ruff check` are clean. No TBD/FIXME/XXX in the phase's new modules.

## Success criteria

| # | Criterion | Status | Evidence in code |
|---|-----------|--------|------------------|
| 1 | Admin-created user signs in with Auth0; state, nonce, iss, aud, exp checked; sub linked once then matched on sub; uninvited cannot create an account | VERIFIED | `companion/oidc.py`: PKCE S256, `validate_id_token` checks alg!=none, `iss == cfg.issuer`, `aud`/`azp`, `exp` (leeway 60 s), `iat`, constant-time nonce; `companion/sign_in.py` `_verified_claims` checks the attempt (single-use pop, 10 min TTL), provider error, state via `hmac.compare_digest`, then token exchange. `server/fleet_sessions.resolve_login`: stored (iss, sub) wins; otherwise link only on a verified email for an enabled, still-unlinked row (`UPDATE ... WHERE iss IS NULL AND sub IS NULL`). No code path inserts a user; unknown gives a 403 not-invited page, no row and no session. Role is read from local `users`, never from claims. |
| 2 | Shared password is a flagged, throttled legacy-admin fallback with a removal task; sessions don't depend on it | VERIFIED | `app._handle_login_post`: flag `SKYPANE_LEGACY_PASSWORD_LOGIN` (403 when off), `LOGIN_THROTTLE`, `auth.password_ok` (`hmac.compare_digest`), audit log line, legacy session is a random-token row in `fleet.db` (`PRINCIPAL_LEGACY_ADMIN`, always `admin`, never `user`); `_resolve_principal` re-checks the flag each request. `auth.py` no longer derives any token from the password. Removal task: `54-LEGACY-ADMIN-REMOVAL.md` (six steps, event-driven trigger). |
| 3 | Route x role x owner matrix proves default-deny; a user gets 404 for another user's device | VERIFIED, with Phase 51 limit | `routes.Route.__new__` refuses a route without a valid `Access`. `Handler._dispatch` is the single gate (`access.decide`: anonymous -> LOGIN, role below minimum or non-owner -> NOT_FOUND). `test_access_matrix.py` parametrizes over `routes.ROUTES`, fails if a route lacks a policy row or a row lacks a route, and checks foreign-device, unknown-device and malformed-id requests give a byte-identical 404, plus disabled, deleted-user, expired, demoted and legacy-flag-off sessions. The device dimension is proven on a test-only `/d/<id>/_probe` family (asserted absent from the production table). |
| 4 | Frames authenticate with MAC+secret independently of Auth0; whole flow tested against local fake Auth0 with failure modes | VERIFIED | `stub-server/test_auth_independence.py` passes; `test-support/fake_auth0.py` (loopback, failure knobs) with `test_fake_auth0.py`, `test_oidc.py`, `test_auth0_login.py`, `test_browser_auth0.py`. |

## Not achievable until Phase 51 (stated in 54-HANDOFF.md section A)

- No real `/d/<id>/...` routes exist. Ownership is enforced and tested through `access.authorized_device_id` and the probe family only. The criterion "a user gets 404 for another user's device" is proven at the gate and on the harness, not on a real device page.
- The matrix has no rows for real per-device routes or derived resources (images, history, battery, firmware status). The completeness test will fail until Phase 51 adds them, which is the intended tripwire.
- A `user`-role principal sees only `/account` (empty Frames state), per D-11. The reduced view arrives with Phase 55.
- Co-management (owner request of 2026-10-30) is not in this phase and extends `authorized_device_id` later.

54-HANDOFF.md confirmed: section A (Phase 51 work), section B (eight go-live steps: tenant config, env vars, first admin via CLI, real-tenant smoke test, caddy validate and log check, fleet.db schema 1 to 2 and rollback caveat, legacy flag off and removal), section C/D (event-driven removal vs "dated" wording, 404 on role denial, no per-session CSRF token, co-management).

## Freeze and out-of-scope check

`git diff 3a0b60e7..HEAD` and `git log 3a0b60e7..HEAD` over `stub-server/byos_server.py`, `firmware/` and `stub-server/measured_fields_freeze.json` are empty. No phase-54-tagged commit touches those paths. Phase 54 did change `server/fleet_db.py` and `server/fleet_migrate.py` (schema v2 with a `sessions` table) and `stub-server/fleet_cli.py` (`users unlink-identity`); these are fleet-store changes, not image/render or frame-protocol code, and `test_phase47_freeze.py` passes.

## Notes and warnings (non-blocking)

- Deliberate deviations, all documented: removal is event-driven rather than dated (D-08); role denial returns 404 rather than 403; no per-session CSRF token (SameSite cookies plus the existing Origin gate); rollback to the previous release is blocked by the schema-2 `fleet.db`.
- Redaction of the `/callback` query in the Caddy log is covered by text tests only.
- The Playwright browser mismatch noted in the handoff is a local-sandbox issue.

## Real-tenant verification (owner, 2026-10-30, EU tenant, production)

Deployed `af9e8521` to production at 20:27 UTC (deploy log: backup, `fleet.db` schema 1 -> 2, Caddy config valid, health probe passed). Auth0 variables set and the companion restarted at 20:33 UTC. Results, as reported by the owner and read from the deploy and Caddy logs:

- Sign-in through Auth0 works; the invited admin was linked and landed signed in. Only the `skypane-users` database connection is enabled for the application (the shared tenant's other database connection and the social connections are off); the "Sign up" link no longer shows.
- Sign-out returns to `/login` and Auth0 asks for credentials again (the Auth0 session ended).
- A token request with a wrong `code_verifier` was rejected by Auth0: `invalid_grant`, "Failed to verify code verifier". PKCE is enforced for this Regular Web Application.
- Caddy journal: 2 `/callback` lines, 0 containing `code=` (redaction works on a real request).

The owner then turned the shared-password fallback off (`SKYPANE_LEGACY_PASSWORD_LOGIN=0`); the login page no longer shows it. Still open: removing the legacy code (see `54-LEGACY-ADMIN-REMOVAL.md`, steps 2 to 5) and the per-device route rows after Phase 51.

## Owner production tests, 2026-10-31

Run by the owner on the production companion, as reported by the owner in conversation and, where noted, read from server logs:

| # | Test | Result |
|---|------|--------|
| 1 | An invited user with the role `user` signs in | Passed. Lands on the Account page with the empty frames state; no admin pages in the navigation; opening the Health and Update pages by address gives the not-found page. |
| 2 | A verified Auth0 account that was not invited | Passed. Gets the "no invitation found" page and no session. `users list` afterwards showed the same invited users and no new one. |
| 3 | Sign-in and sign-out on an iPhone (Safari, private tab) | Passed. |
| 4 | Session survives `systemctl restart skypane-companion`; sign-out ends it | Passed. Still signed in after the restart; after sign-out, back and reload return to the sign-in page. |
| 5 | The live frame is not disturbed | Passed. Health page: the frame connects normally, no fleet fault. `journalctl -u skypane-byos` shows regular wakes with `GET /device/v1/display` then `GET /img/<hash>.bin`, no 401, 403 or 5xx; the wake gap moves from about 15 min to 60 min at the 11:10 UTC wake, matching the owner's change of the interval to 3600 s. No error on the frame. |
| 6 | `fleet_cli users unlink-identity` | Passed. The command printed `unlinked <email>`; the user stayed in `users list`; the open session was ended (reload returned to sign-in); signing in again with the same Auth0 account linked it again. |

Finding, not a failure: an invited user whose Auth0 email is not verified is refused on first sign-in (`unverified_email`) but sees the "no invitation found" page. Observed with an account created by hand in the Auth0 dashboard; it signed in once the address was verified. Tracked as SEED-011, together with SEED-012 (invite from the admin companion also creating the Auth0 account).

## Closure (owner, 2026-10-31)

- The three human items of the 2026-10-30 verification are done: the real-tenant smoke test, the Caddy check (0 `/callback` lines with `code=`), and the legacy-admin fallback, which is off in production (`SKYPANE_LEGACY_PASSWORD_LOGIN=0`) with the shared-password path removed (see `54-HANDOFF.md`, D.5).
- Carried to Phase 55: the real `/d/<id>/...` route rows and derived resources of the access matrix (AUTH-03), and the reduced user view, as listed in `54-HANDOFF.md` section A. AUTH-03 stays Pending until they exist.
