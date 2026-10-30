# Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Invited users sign in with Auth0 (authorization code + PKCE), get a server-side session, and every companion route enforces a minimum role and device ownership (default-deny). Requirements: AUTH-01, AUTH-02, AUTH-03, AUTH-06.

Split by the Phase 51 dependency:
- **Delivered now (independent of 51):** the OIDC client, the fake Auth0, invite-only account linking, sessions in `fleet.db`, the legacy-admin fallback, the default-deny route table with a minimum role per route, the ownership gate as a reusable function, and the route x role x owner matrix test over every route that exists today (plus a registered device-scoped test route family for the owner dimension).
- **Completed after Phase 51:** the real per-device routes (`/d/<id>/...`) and the full matrix rows for them. The gate and the matrix harness are built so Phase 51 only adds rows.
- Out of scope: pairing and admin console (Phase 55), per-device config (51), any change to what the live frame receives or how it authenticates (Phase 47 freeze). No production deploy.

</domain>

<decisions>
## Implementation Decisions

### Fixed by the owner before discussion (do not reopen)
- **D-01:** Auth0 accounts, invite-only (sign-up disabled in the tenant AND refused in the app: a verified login for an unknown `sub`/email creates no row and no session). An admin creates users (fleet CLI; web management is Phase 55).
- **D-02:** Authorization code + PKCE (S256) with `state` and `nonce`; no new dependency (stdlib + Pillow + requests); no local JWT signature verification, the ID token comes straight from the token endpoint over TLS. Checked: `state`, `nonce`, `iss`, `aud`, `exp`.
- **D-03:** The Auth0 `sub` is linked once to the invited local user (via verified email), then matched on `sub` only. Role (`admin`/`user`) is stored locally and never read from Auth0.
- **D-04:** Frames keep authenticating with MAC + secret, independent of Auth0. Nothing in this phase changes what the live frame receives (Phase 48 freeze test stays green).
- **D-05:** Tenant in Europe; the whole flow is tested against a local fake Auth0 on loopback (pytest-socket guard), failure modes included. No real external service during tests. Domain, client id and client secret are read from systemd `EnvironmentFile` variables; never in the repo.
- **D-06:** Every route is default-deny with a minimum role; a user gets 404 for another user's device; a route x role x owner matrix test proves it.

### Legacy-admin fallback (AUTH-02)
- **D-07:** The shared password stays as a named `legacy-admin` principal, throttled (existing `LoginThrottle`), constant-time compared, logged on every use, flagged in the UI. It never maps to a `user`-role principal and sessions never depend on the password (no HMAC key derived from it).
- **D-08 (owner, 2026-10-30):** Removal is **event-driven**: the fallback is removed as soon as the Auth0 sign-in is in production. This is not a calendar date; the removal task in the repo carries that trigger, and a "remove by" date is stamped by the owner at go-live. Surface this to the owner at the end (the roadmap wording says "dated").
- **D-09:** Behind a flag `SKYPANE_LEGACY_PASSWORD_LOGIN`. Default stays enabled so the current deployment behaves as today until Auth0 is configured; a test proves flag off yields a refusal on the password form.

### Sessions
- **D-10 (owner):** Sessions are stored server-side in `fleet.db` (random 256-bit id, only a hash stored), absolute lifetime 30 days, idle timeout 7 days, rotated on login, deleted on logout. A disabled user is cut off on the next request.

### What a `user` role sees before Phase 51
- **D-11 (owner):** All current (global) pages are admin-only. A signed-in `user` sees an "Account" page only (identity, language, theme, sign out) plus an empty-state message that their frames will appear once available. No leak of the owner's frame. Legacy-admin and `admin` see everything as today. The Phase 55 reduced view replaces the empty state.

### Sign-out
- **D-12 (owner):** Sign out ends the SkyPane session and also redirects through Auth0 `/v2/logout` with a fixed `returnTo`. The return URL must be listed in the tenant's "Allowed Logout URLs" (owner step, documented in deploy docs). Local session is destroyed even if the Auth0 hop fails.

### Claude's Discretion
- Module layout (`companion/oidc.py`, session store, principal type, route access annotations in `companion/routes.py`), env var names, fake Auth0 location (`test-support/`), pre-login cookie design (SameSite=Lax; fixed redirect URI; same-site relative `return_to` whitelist), CSRF approach, bilingual strings in `companion/i18n_fr/`, how the matrix test enumerates routes, plan split and waves.
- Account-linking rules: require `email_verified`; exact issuer with trailing slash; skew tolerance small.
- Login page layout under the sketch-findings design system (legacy password as a secondary, flagged option).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone planning
- `.planning/workstreams/v1-2/ROADMAP.md` — Phase 54 goal and success criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — AUTH-01..03, AUTH-06
- `.planning/workstreams/v1-2/STATE.md` — project decisions
- `.planning/workstreams/v1-2/research/SUMMARY.md`, `STACK.md` (Auth0 specifics), `ARCHITECTURE.md` (S5, users table, sub linking), `PITFALLS.md` (C1-C3, C6-C9, M7-M9, m4-m6)
- `.planning/workstreams/v1-2/phases/48-fleet-data-model-roles-and-live-frame-migration/48-CONTEXT.md` — users table, `(iss, sub)` column, role stored locally, CLI users

### Code
- `companion/auth.py` — current shared-password session gate, `LoginThrottle`, cookie helpers
- `companion/routes.py` — the single route table (`auth_required` bool to become minimum role)
- `companion/app.py` — `Handler._dispatch()`, login/logout handlers
- `companion/login_page.py` — login UI
- `server/fleet_db.py` — fleet.db schema, users, devices, owner
- `stub-server/fleet_cli.py` — user administration CLI
- `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json` — freeze test that must stay green
- `deploy/README.md`, `deploy/skypane.env.example` — env var and systemd conventions
- `COMPLIANCE.md`, `.claude/CLAUDE.md` — conventions
- `.claude/skills/sketch-findings-skypane/SKILL.md` — design system for any UI

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `companion/auth.py` `LoginThrottle`, `client_ip`, `parse_cookies`, `secure_cookie_flag`, `post_origin_ok`.
- `server/fleet_db.py` users/devices/owner API; `transaction()`; `PRAGMA user_version` migrations.
- `server/http_fetch.pinned_request` (or `requests`) for the token call.
- Companion app-server fixtures (`companion/conftest.py`, `test-support/companion_app_server.py`).

### Established Patterns
- One route table, `Route(method, matcher, handler, auth_required)`; behaviour-over-source tests; comment-history guard; function size <= 80.
- `companion/auth.py` is stdlib-only and must not import sqlite3 or `server/`; session persistence therefore needs a sibling module.

### Integration Points
- `Handler._dispatch()` gate, login/logout handlers, fleet.db migration to add a sessions table, deploy env docs.

</code_context>

<specifics>
## Specific Ideas

Manual real-tenant smoke test (wrong `code_verifier` rejected, login works) is a documented owner step, not CI.

</specifics>

<deferred>
## Deferred Ideas

- Per-device routes `/d/<id>` and their matrix rows — after Phase 51.
- Pairing, admin console, web user management — Phase 55.
- "View as user" (AUTH-07) — later.

</deferred>

---

*Phase: 54-Auth0 Sign-In, Local Roles and Default-Deny Access*
*Context gathered: 2026-10-30*
