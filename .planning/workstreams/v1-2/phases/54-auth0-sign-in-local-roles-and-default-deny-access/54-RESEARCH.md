# Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access - Research

**Researched:** 2026-10-30
**Domain:** Hand-written OIDC authorization-code + PKCE client, server-side sessions in SQLite, default-deny route table, in a stdlib `ThreadingHTTPServer` app
**Confidence:** MEDIUM-HIGH (codebase facts HIGH, read directly; OIDC/Caddy/Auth0 behaviours MEDIUM, from docs fetched today; browser cookie-chain behaviour MEDIUM until the Playwright test proves it)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fixed by the owner before discussion (do not reopen)**
- **D-01:** Auth0 accounts, invite-only (sign-up disabled in the tenant AND refused in the app: a verified login for an unknown `sub`/email creates no row and no session). An admin creates users (fleet CLI; web management is Phase 55).
- **D-02:** Authorization code + PKCE (S256) with `state` and `nonce`; no new dependency (stdlib + Pillow + requests); no local JWT signature verification, the ID token comes straight from the token endpoint over TLS. Checked: `state`, `nonce`, `iss`, `aud`, `exp`.
- **D-03:** The Auth0 `sub` is linked once to the invited local user (via verified email), then matched on `sub` only. Role (`admin`/`user`) is stored locally and never read from Auth0.
- **D-04:** Frames keep authenticating with MAC + secret, independent of Auth0. Nothing in this phase changes what the live frame receives (Phase 48 freeze test stays green).
- **D-05:** Tenant in Europe; the whole flow is tested against a local fake Auth0 on loopback (pytest-socket guard), failure modes included. No real external service during tests. Domain, client id and client secret are read from systemd `EnvironmentFile` variables; never in the repo.
- **D-06:** Every route is default-deny with a minimum role; a user gets 404 for another user's device; a route x role x owner matrix test proves it.

**Legacy-admin fallback (AUTH-02)**
- **D-07:** The shared password stays as a named `legacy-admin` principal, throttled (existing `LoginThrottle`), constant-time compared, logged on every use, flagged in the UI. It never maps to a `user`-role principal and sessions never depend on the password (no HMAC key derived from it).
- **D-08 (owner, 2026-10-30):** Removal is **event-driven**: the fallback is removed as soon as the Auth0 sign-in is in production. This is not a calendar date; the removal task in the repo carries that trigger, and a "remove by" date is stamped by the owner at go-live. Surface this to the owner at the end (the roadmap wording says "dated").
- **D-09:** Behind a flag `SKYPANE_LEGACY_PASSWORD_LOGIN`. Default stays enabled so the current deployment behaves as today until Auth0 is configured; a test proves flag off yields a refusal on the password form.

**Sessions**
- **D-10 (owner):** Sessions are stored server-side in `fleet.db` (random 256-bit id, only a hash stored), absolute lifetime 30 days, idle timeout 7 days, rotated on login, deleted on logout. A disabled user is cut off on the next request.

**What a `user` role sees before Phase 51**
- **D-11 (owner):** All current (global) pages are admin-only. A signed-in `user` sees an "Account" page only (identity, language, theme, sign out) plus an empty-state message that their frames will appear once available. No leak of the owner's frame. Legacy-admin and `admin` see everything as today. The Phase 55 reduced view replaces the empty state.

**Sign-out**
- **D-12 (owner):** Sign out ends the SkyPane session and also redirects through Auth0 `/v2/logout` with a fixed `returnTo`. The return URL must be listed in the tenant's "Allowed Logout URLs" (owner step, documented in deploy docs). Local session is destroyed even if the Auth0 hop fails.

### Claude's Discretion
- Module layout (`companion/oidc.py`, session store, principal type, route access annotations in `companion/routes.py`), env var names, fake Auth0 location (`test-support/`), pre-login cookie design (SameSite=Lax; fixed redirect URI; same-site relative `return_to` whitelist), CSRF approach, bilingual strings in `companion/i18n_fr/`, how the matrix test enumerates routes, plan split and waves.
- Account-linking rules: require `email_verified`; exact issuer with trailing slash; skew tolerance small.
- Login page layout under the sketch-findings design system (legacy password as a secondary, flagged option).

### Deferred Ideas (OUT OF SCOPE)
- Per-device routes `/d/<id>` and their matrix rows - after Phase 51.
- Pairing, admin console, web user management - Phase 55.
- "View as user" (AUTH-07) - later.

Phase split (from CONTEXT domain): delivered now = OIDC client, fake Auth0, invite-only linking, sessions in `fleet.db`, legacy-admin fallback, default-deny table with minimum role, ownership gate as a reusable function, matrix test over today's routes plus a registered device-scoped test route family. Completed after Phase 51 = real `/d/<id>/...` routes and their matrix rows. No production deploy.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Auth0 sign-in (code + PKCE, no new dependency), state/nonce/iss/aud/exp checked, sign-up closed in the app, `sub` linked once to an admin-created local user then matched on `sub` | Sections "OIDC details", "Account linking", "Fake Auth0", "fleet.db migration v2" |
| AUTH-02 | Shared password kept as flagged, throttled `legacy-admin` fallback behind a flag with removal task; sessions no longer depend on the password | Sections "Current auth flow", "Legacy-admin", "Sessions" |
| AUTH-03 | Every route default-deny with a minimum role; user sees only own devices (404 otherwise); route x role x owner matrix test | Sections "Access annotation and default-deny", "Matrix test", "Phase 51 split" |
| AUTH-06 | Frames keep MAC+secret auth independent of Auth0; Auth0 replaced by a local fake in tests | Sections "Frame auth untouched", "Fake Auth0" |
</phase_requirements>

## Summary

The companion today has exactly one auth mechanism: a stateless `expiry.signature` cookie whose HMAC key is derived from `SKYPANE_COMPANION_PASSWORD` plus a per-process salt, with a process-local revocation set (`companion/auth.py:23-99,134-171`). One predicate, `Handler._is_authenticated()` (`companion/app.py:547-553`), feeds `require_session()`, `_handle_login_get`, and the 404/403 page health-dot logic. The gate runs in one place, `Handler._dispatch()` (`app.py:938-954`), driven by `Route.auth_required`, a bool (`companion/routes.py:28`). Everything that must change is therefore concentrated in four files (`auth.py`, `routes.py`, `app.py`, `login_page.py`) plus `fleet_db.py` for storage; roughly 80 test modules touch the password login path, but they go through the shared `login()` helper (`test-support/companion_app_server.py:105-120`) and keep working as long as the legacy password login stays the default.

The design that fits every locked decision: (1) replace the bool with an `Access(min_role, device_arg)` annotation validated at import (default-deny: a Route cannot be constructed without one); (2) a `Principal` resolved per request from an opaque server-side session (cookie holds a random 256-bit token, `fleet.db` holds `sha256(token)`), with role and `disabled` read from `users` on every request; (3) a pure `decide()` function used by `_dispatch` that returns ALLOW / LOGIN / NOT_FOUND, which the matrix test exercises both as a pure function over every route and over real HTTP with stubbed handlers; (4) `companion/oidc.py` holding the pure OIDC pieces (PKCE, authorize URL, claim checks, token exchange through an injected HTTP callable), an in-memory bounded pre-login attempt table, and `server/fleet_sessions.py` holding all SQLite session/linking code (so `companion/auth.py` stays stdlib-only with no sqlite3); (5) a loopback fake Auth0 in `test-support/` with failure knobs, driven from both subprocess and in-process app servers and from Playwright.

Four findings change the plan materially and are not obvious from CONTEXT: (a) `server.http_fetch.pinned_request` is https-only and refuses non-public addresses, so it cannot reach the loopback fake; use `requests` with `trust_env=False` for the token call. (b) `form-action 'self'` in the app CSP (`app.py:~70`) makes Chromium block a 303 redirect to an external origin after a form POST; both the Auth0 hand-off at logout and the callback landing must use a 200 interstitial with `<meta http-equiv="refresh">`, which also solves the SameSite=Strict-after-cross-site-redirect problem. (c) `fleet_migrate.migrate()` returns "nothing to do" for an already-migrated v1 database (`needs_write` is false), so schema v2 would never be applied by `deploy/activate.sh` unless that logic learns about pending schema steps; also `fleet_db.migrate_schema` reads the version before taking the write lock, so two processes upgrading at once can fail. (d) Bumping `user_version` to 2 means the previous release's byos (`SCHEMA_VERSION=1`) refuses the file as too new and falls back to the legacy files; the frame still works, but the Health page will show a fleet fault until the new release is live. Everything is doable now except real `/d/<id>` routes; the harness for them is built here.

**Primary recommendation:** Build in this order: fleet.db v2 + session store, then `Access`/`Principal`/`decide()` with the legacy-admin login moved onto server-side sessions (keeps all 80 existing test modules green), then `oidc.py` + fake Auth0 + callback/logout handlers, then the Account page and login-page changes, then the matrix test and deploy docs/Caddy redaction.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sign-in orchestration (authorize redirect, callback, token exchange, claim checks) | API / Backend (companion process) | Browser (follows redirects only) | Secrets (client secret, verifier, nonce) must stay server-side |
| Session storage and lookup | Database / Storage (`fleet.db`, `sessions` table) | API / Backend (cookie parse, hash) | D-10; survives restarts; cut-off on disable |
| Role and ownership enforcement | API / Backend (`Handler._dispatch` + pure `decide()`) | Database (owner column) | Never trusted from cookie/UI (PITFALLS C4) |
| Pre-login attempt state (state, nonce, verifier, next) | API / Backend (in-memory bounded table) | Browser (opaque Lax cookie id) | Single process, 10 min TTL; a restart merely aborts an in-flight login |
| Account page / login page UI | Frontend Server (server-rendered HTML in the companion) | Browser (CSS/JS static) | App is fully server-rendered |
| Auth0 logout hand-off and callback landing | Browser (meta-refresh navigation) | API / Backend (200 interstitial) | Avoids `form-action` and Strict-cookie redirect-chain pitfalls |
| TLS, log redaction of `/callback` query | CDN / Static tier = Caddy | — | Caddy terminates TLS and writes the access log |
| Frame authentication | API / Backend (byos process, `stub-server/byos_server.py`) | Database (`devices`) | Unchanged; independent of Auth0 and of sessions |

## Standard Stack

No new dependencies. Everything is stdlib plus packages already hash-locked in `server/requirements.txt`.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`hashlib`, `hmac`, `secrets`, `base64`, `json`, `urllib.parse`, `sqlite3`, `http.server`) | 3.14 prod / 3.13 local venv | PKCE, claim checks, session hashing, storage | Owner constraint D-02 [CITED: CONTEXT.md] |
| `requests` | already locked in `server/requirements.txt` | Token-endpoint POST (TLS verify on, timeouts) | Already a dependency; `pinned_request` cannot reach loopback (see Pitfall 1) [VERIFIED: codebase, `server/http_fetch.py:320-346`] |
| `server/fleet_db.py` | schema v1 -> v2 | Users, new `sessions` table | Existing leaf module with `user_version` migrations [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest, pytest-xdist, pytest-socket, pytest-playwright | locked | Tests, fake Auth0 on loopback, redirect-chain browser test | All new tests [VERIFIED: `pyproject.toml` addopts lines 43-56] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` for token exchange | `server.http_fetch.pinned_request` | Pinned request is https-only and refuses non-public IPs, so the loopback fake is unreachable; would need a test-only branch (rejected by M7: no `if TEST` branch) |
| In-memory pre-login table | Pre-login rows in `fleet.db` | DB survives restart but adds a table, writes for unauthenticated traffic, and cleanup; in-memory is bounded, matches the existing `LoginThrottle` precedent, and a restart only aborts a login in flight |
| Authlib / PyJWT | — | Ruled out by owner (D-02) |

**Installation:** none.

**Version verification:** no new package is introduced, so no registry lookup applies.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none new) | — | — | — | — | not run | No new external package; `requests` is already hash-locked in `server/requirements.txt` |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Current Auth Flow (question 1)

Every dependency on the shared password, with line refs. All of these change or are consciously kept.

| Where | What it does | Phase 54 action |
|-------|--------------|-----------------|
| `companion/auth.py:23` `PASSWORD_ENV_VAR`, `109-120` `configured_password()` | Raises `AuthNotConfigured` when unset | Keep, but only required when the legacy flag is on |
| `auth.py:34-47` `_PROCESS_SALT`, `_signing_key()` | Session HMAC key derived from the password | **Delete** (D-07: no key derived from the password) |
| `auth.py:49-99` `_REVOKED`, `revoke()`, `is_revoked()` | In-memory revocation set | **Delete** (server-side sessions replace it) |
| `auth.py:134-171` `issue_session_token()`, `verify_session_token()` | Stateless token | **Delete** |
| `auth.py:185-207` `session_set_cookie_header()`, `logout_set_cookie_header()` | `HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=SESSION_TTL_S (12 h)` | Keep shape; Max-Age becomes the 30-day absolute lifetime; value is the opaque token |
| `auth.py:123-131` `password_ok()` | Constant-time compare | Keep (legacy path only) |
| `auth.py:264-352` `LoginThrottle`, `login_throttle_key()` | Per-IP failure throttle | Keep, reuse for legacy password |
| `app.py:240` `LOGIN_THROTTLE` | Process-global instance | Keep |
| `app.py:547-553` `_is_authenticated()` | verify + not revoked | Replace with `_principal()` (cached per request, reset at the top of `_dispatch`) |
| `app.py:555-570` `require_session()` | 303 to `/login?next=` using `_validated_next_route` (exact NAV_TABS membership, `app.py:336-343`) | Keep behaviour for anonymous; callers move into `decide()` |
| `app.py:643-675` `_not_found_page()` / `_forbidden_page()` | Compute Health nav dot when `_is_authenticated()` | **Must only do so for admin/legacy-admin** (Pitfall 5: a `user` would see global health severity) |
| `app.py:888-898` `_handle_login_get` | Redirect home if authenticated | Redirect by role (user -> `/account`) |
| `app.py:900-909` `_handle_logout_post` | `auth.revoke` + clear cookie | Delete session row, clear cookie, return interstitial to Auth0 `/v2/logout` (D-12) |
| `app.py:966-990` `_handle_login_post` | throttle -> `password_ok` -> `issue_session_token` | Gate on flag; create server-side `legacy-admin` session; log every success |
| `app.py:1304-1310` `main()` | Exits 1 if the password is unset (fails closed) | New fail-closed rule: refuse to start unless at least one login method is usable, and refuse a half-configured Auth0 |
| `app.py:1267-1272` `log_message` | Logs method + path only, no query | Already safe for `/callback?code=` in the app log |
| `test-support/companion_app_server.py:24,168-221,320-346` | `TEST_PASSWORD`, `AppServer` sets the env var, `InProcessAppServer` sets/restores it | Keep; add `env_overrides` use for Auth0 variables |
| `companion/test_companion_app_01.py` "Section 1: companion/auth.py" (lines ~75-300, ~15 tests, uses `auth._REVOKED`, `issue_session_token`, `verify_session_token`) | Tests the stateless token API | **Rewrite** (they assert the retired mechanism) |
| 31 call sites in that file; 80 modules import `companion_app_server`/`login(` | Password login via HTTP | Unchanged if the password path stays default |
| `deploy/skypane.env.example`, `deploy/README.md` (~lines 223-232), `scripts/run-local-verify.sh:4` | Document / set the password | Document new variables; password stays |
| `test-support/companion_render_snapshot.py` + `companion/testdata/render_baseline.json` | Committed baseline of authenticated pages (logged in with the password) and of every route's unauthenticated response | New routes need baseline entries; a legacy-admin UI flag changes authenticated pages. Regenerate deliberately (`companion_render_snapshot` CLI) and review the diff |
| `companion/test_route_table.py:60-96,111-141` | Uses `r.auth_required`; `_SAMPLE_MIDDLE[matcher]` raises KeyError for a new PrefixSuffix route; `baseline[key]` KeyError for a new gated route | Update to `access`; this KeyError behaviour is a useful forcing function, keep it |

Current `ROUTES` inventory (`routes.py:84-201`): GET = `/login`, 18 static assets, 7 tabs (`/`, display, device, flights, health, airlines, update), 3 fixed redirects (`/settings`, `/history`, `/preview`), 5 prefix image routes (`/gallery/`, runway, illustration, theme-preview, frame-preview); POST = `/login`, `/settings`, `/poll-now`, 3 `/quick/*`, `/ui-theme`, `/ui-lang`, `/logout`, 3 airline routes + manual-delete prefix, illustration replace, rules add/delete, 2 calendar, 2 update.

## Access Annotation and Default-Deny (question 2)

**Replace** `Route = namedtuple("Route", "method matcher handler auth_required")` (`routes.py:28`) with a four-field type whose last field is `access`.

```python
# companion/routes.py  (sketch; Source: codebase pattern, no external API)
ANONYMOUS, USER, ADMIN = "anonymous", "user", "admin"      # rank 0 < 1 < 2
Access = collections.namedtuple("Access", "min_role device_arg")

PUBLIC = Access(ANONYMOUS, None)         # login, callback, static assets
SIGNED_IN = Access(USER, None)           # account page, logout, ui-theme, ui-lang
ADMIN_ONLY = Access(ADMIN, None)         # every current global page and mutation
# Phase 51: Access(USER, device_arg="device_id")  -> ownership gate applies

class Route(collections.namedtuple("Route", "method matcher handler access")):
    def __new__(cls, method, matcher, handler, access):
        if not isinstance(access, Access) or access.min_role not in (ANONYMOUS, USER, ADMIN):
            raise TypeError("every route needs an explicit Access annotation")
        return super().__new__(cls, method, matcher, handler, access)
```

- Default-deny at the type level: `Route(...)` without a valid `Access` raises at import time, so a route can never register without a policy. Passing `True/False` (the old values) also fails. This is stronger than a unit test alone.
- Classification of today's routes: `PUBLIC` = GET/POST `/login`, the 18 static GETs, new GET `/login/auth0`, new GET `/callback`. `SIGNED_IN` = new GET `/account`, POST `/logout`, POST `/ui-theme`, POST `/ui-lang`. **Everything else `ADMIN_ONLY`** (D-11). Legacy-admin has role `admin`.
- Device scoping: `device_arg` names what the matcher captured (`RouteMatch.captured`, `routes.py:204-223`). `/d/<id>/display` fits the existing `PrefixSuffix("/d/", "/display")` shape (captured = the id). Phase 51 only adds `Route`s with `Access(USER, "device")` plus matrix rows. The id must be validated by regex (`^d_[0-9a-f]{8}$`, the `add_device` format in `fleet_db.py:398-410`) before any lookup, otherwise a captured value containing `/` could reach the DB layer.
- The gate is one pure function in a new `companion/access.py` (no I/O except an injected device-owner lookup):

```python
def decide(principal, access, captured, owner_lookup):
    """-> ALLOW | LOGIN | NOT_FOUND. Never raises on hostile input."""
    if access.min_role == ANONYMOUS:
        return ALLOW
    if principal is None:
        return LOGIN                     # 303 /login[?next=] exactly as today
    if RANK[principal.role] < RANK[access.min_role]:
        return NOT_FOUND                 # authenticated but not allowed
    if access.device_arg is None:
        return ALLOW
    if principal.role == ADMIN:          # explicit admin bypass
        return ALLOW if owner_lookup(captured) is not None else NOT_FOUND
    owner = owner_lookup(captured)       # None for unknown / malformed id
    return ALLOW if owner is not None and owner == principal.user_id else NOT_FOUND
```

- **Denied-as-404 (recommendation, Claude's discretion):** an authenticated principal that lacks the role gets the same 404 page an unknown path gets, so there is one denial outcome, no route-existence oracle, and the matrix has three outcomes (login redirect / 404 / reached). Anonymous keeps today's 303 so the committed baseline still holds.
- `Principal = namedtuple("Principal", "kind user_id email role")` with `kind in {"user", "legacy-admin"}`. A single accessor `device_for(principal, device_id)` (admin: any existing device; user: owner match; else None) is the only function Phase 51 handlers may use to load a device. Add `fleet_db.get_device_owner(conn, device_id)` that selects only `owner_user_id` (never token/secret columns).
- `_dispatch` (`app.py:938-954`) becomes: origin gate -> `routes.match` -> `decide` -> handler. Reset the cached principal at the top of `_dispatch` (do not rely on one Handler instance per request; the handler uses `BaseHTTPRequestHandler` defaults, HTTP/1.0 close-per-request, but do not depend on it).
- Resolve the principal lazily and only when `access.min_role != ANONYMOUS` or a page needs it, so the 18 static assets never open `fleet.db` (the same property `test_request_connections.py` proves for `history.db`).

## Matrix Test (question 2, continued)

Two layers, both enumerating `routes.ROUTES` at runtime (allowed by the behaviour-over-source rule: runtime objects, real HTTP, never source text; same style as `companion/test_route_table.py`).

1. **Pure layer (fast, exhaustive, includes allowed rows).** Parametrize `routes.ROUTES` (plus the injected probe family below) x principals `{anonymous, user-owner, user-other, admin, legacy-admin, disabled-user}` and call `access.decide()` directly; assert against an **independent hand-written expectation table in the test file** keyed by `(method, matcher)`. A completeness test asserts the table's key set equals the set of all route keys (so adding a route forces a human to state its policy, mirroring the existing `_SAMPLE_MIDDLE` KeyError trick). Do not derive the expectation from `route.access` alone: that would be a tautology.
2. **HTTP layer (proves the wiring).** Use `InProcessAppServer` (`companion_app_server.py:301-346`; a subprocess cannot be monkeypatched). Replace every route's handler with a recording stub by monkeypatching `routes.ROUTES` (`match()` reads the module global at call time, `routes.py:204-223`), so "allowed" rows return 200 `reached` and execute no real side effect (real `/poll-now`, `/settings`, update install must not run). Then assert per cell: anonymous -> 303 `/login...`; wrong role -> 404 and the stub NOT called; allowed -> stub called. Sessions are obtained through the real flows (real fake-Auth0 login for user/admin, password for legacy-admin) so the session store is exercised too.
3. **Owner dimension now.** Register a test-only device-scoped family in the test (monkeypatched, never in the production table): `Route("GET", PrefixSuffix("/d/", "/_probe"), stub, Access(USER, "device"))` and a POST sibling. Seed `fleet.db` with two users and two devices; assert owner -> reached, other user -> 404 identical body to an unknown id (no existence oracle), admin -> reached, unknown/malformed id -> 404, anonymous -> 303.
4. Also assert: disabled user's existing session is refused on the next request; legacy session dies when the flag is turned off; a session for a deleted/absent user row is refused.

Keep the existing `test_route_table.py` real-handler anonymous test (it proves real handlers are also gated); update `r.auth_required` -> `r.access.min_role == ANONYMOUS`.

## fleet.db Migration v2 (question 3)

**Facts** [VERIFIED: codebase]
- `users` already has `email UNIQUE COLLATE NOCASE`, `role`, `disabled`, `iss`, `sub`, `created_at`, `UNIQUE (iss, sub)` (`fleet_db.py:82-93`). **No `email_verified` column is needed**: verification is checked from the ID token at link time and never stored. No users migration is required for AUTH-01.
- Migrations are a tuple `MIGRATIONS` (`fleet_db.py:120`), `SCHEMA_VERSION = len(MIGRATIONS)`, each applied in `BEGIN IMMEDIATE` with the version bump (`153-172`). Expand-only rule: add tables/nullable columns only.

**v2 schema (recommended)**
```sql
CREATE TABLE sessions (
  id_hash      TEXT PRIMARY KEY,                       -- sha256 hex of the 256-bit cookie token
  user_id      INTEGER REFERENCES users(id),           -- NULL only for the legacy-admin principal
  principal    TEXT NOT NULL CHECK (principal IN ('user','legacy-admin')),
  created_at   INTEGER NOT NULL,                       -- epoch seconds
  last_seen_at INTEGER NOT NULL,
  expires_at   INTEGER NOT NULL,                       -- created_at + 30 d
  CHECK ((principal = 'user') = (user_id IS NOT NULL))
);
CREATE INDEX sessions_user    ON sessions(user_id);
CREATE INDEX sessions_expires ON sessions(expires_at);
```
Integer epoch seconds (not the ISO strings used elsewhere in `fleet_db`) because lifetime/idle checks are arithmetic; inject the clock for tests (PITFALLS m5). Optional nullable `users.linked_at TEXT` is not required.

**Gotchas the plan must handle**
1. **Previous release vs v2.** Old byos has `SCHEMA_VERSION = 1`; `connect_readonly` raises `FleetDbTooNew` on a v2 file (`fleet_db.py:145-150, 199-212`), byos maps that to `STATUS_FAULT` and serves from the legacy files (`byos_server.py:337-360`; already covered by `stub-server/test_fleet_auth.py:~170`, which sets `user_version = SCHEMA_VERSION + 1`). So the live frame keeps working on rollback, but Health shows a fleet fault and `deploy/README.md` ("rolling back to the previous release works", ~line 300) needs one honest sentence about it. Accept, document, do not hide. (Alternative of a separate `sessions.db` would avoid this but contradicts locked D-10.)
2. **Deploy never applies v2.** `fleet_migrate.plan_migration` sets `needs_write = bool(actions) or not snapshot.marker` and `migrate()` returns "nothing to do" for an already-migrated database (`fleet_migrate.py:~190-200, 343-360`). `deploy/activate.sh:237-280` runs dry-run then real migration as `skypane` before the swap. Add "schema_version < SCHEMA_VERSION" as a reason to write (dry-run line: `would upgrade fleet.db schema 1 -> 2`), so the upgrade happens pre-swap, as `skypane`, after the backup. Otherwise the first `fleet_db.connect()` from the companion/CLI performs it, which contradicts the README statement "The migration never runs at service start".
3. **Concurrent upgrade race.** `migrate_schema` reads `schema_version` **before** `BEGIN IMMEDIATE` (`fleet_db.py:158-172`). Two processes (companion + byos + CLI) can both read 1; the second then re-runs `CREATE TABLE sessions` and fails. Fix: re-read `user_version` inside the transaction and skip if already applied. Add a test with two threads/connections.
4. **Companion on an absent `fleet.db`** (dev, every test state dir): the companion must be able to create it. Call `fleet_db.connect(state_dir)` once in `main()` and per request through the session store. A fresh file has no `migrated_v1` marker so byos treats it as `absent` and keeps the legacy path (`byos_server.py:350-351`), and a later `fleet_migrate` run works on it (`_snapshot_from` handles schema != 0).
5. **Freeze and backup tests.** `stub-server/test_phase47_freeze.py` replays a poll across `fleet_migrate.main(...)` and compares a logical dump after re-run (idempotence); v2 adds an empty table, still idempotent. `deploy/tests/test_backup.py:~403` asserts restored `schema_version == SCHEMA_VERSION` (auto-follows). The backup archive will now contain `sessions` (hashes only, never raw tokens); a restore resurrects unexpired sessions. Acceptable; note it in README. `PRAGMA user_version` is also asserted absent from `history_db.py` (`server/test_config_history.py:~1342`), unaffected.
6. Add `fleet_db` functions (annotated; `server/fleet_db.py` is in the mypy list) or a sibling `server/fleet_sessions.py` (add to `[tool.mypy] files`): `create_session`, `lookup_session` (JOIN `users`; returns role/disabled), `touch_session`, `delete_session`, `delete_sessions_for_user`, `prune_expired`, `link_identity`, `get_user_by_identity`, `get_device_owner`. Function-size gate (max 80) applies to `server/` and `stub-server/` only (`ci.yml:112`); keep `companion/` functions small anyway.

## Where Session Code Lives (question 6)

- `companion/auth.py` docstring and the project rule: stdlib-only, must not import `sqlite3` or `server/`. No test enforces this mechanically for `auth.py` (the import-purity test at `companion/test_companion_app_03.py:1251` is for `battery.py`), but keep it: `auth.py` keeps cookie parsing/headers, `password_ok`, `LoginThrottle`, `post_origin_ok`, and gains pure helpers `new_session_token()` (`secrets.token_urlsafe(32)`) and `hash_session_token()` (`sha256` hex).
- SQLite code: `server/fleet_sessions.py` (or inside `fleet_db.py`, which already hosts user CRUD). It is a leaf module like `fleet_db`. `companion/app.py` already imports many `server.*` modules (`app.py:36-44`), so the app layer may use it.
- `companion/oidc.py`: pure functions (verifier/challenge, authorize URL, `validate_id_token`, `exchange_code(post=...)` with the HTTP callable injected, `AttemptTable`). No sqlite, no Handler.
- `companion/access.py`: `Principal`, `RANK`, `decide`, `device_for`.
- Handler glue for callback/logout/account: a mixin like `post_actions.SettingsActionsMixin` (`app.py:437`) in a new `companion/sign_in.py`, to keep `app.py` (1328 lines) from growing.

## OIDC Details to Hand-Write (question 4)

All HTTP-visible values come from env (D-05): `SKYPANE_AUTH0_DOMAIN` (host[:port], e.g. `<tenant>.eu.auth0.com` or a custom domain), `SKYPANE_AUTH0_CLIENT_ID`, `SKYPANE_AUTH0_CLIENT_SECRET`. Redirect URI and returnTo derive from the already-present `SKYPANE_COMPANION_HOST` (`deploy/skypane.env.example`): `https://<host>/callback`, `https://<host>/login`. Optional `SKYPANE_COMPANION_PUBLIC_URL` override for tests/dev. Never derive from the `Host` header (PITFALLS C8). Scheme is `https` unless a test-only flag (suggested `SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK=1`, same pattern as `SKYPANE_COMPANION_INSECURE_COOKIES`, `auth.py:32,174-182`) is set **and** the host is loopback.

**Authorize request** (GET `https://{domain}/authorize`) [CITED: .planning/workstreams/v1-2/research/STACK.md, Auth0 docs fetched at milestone research]: `response_type=code`, `client_id`, `redirect_uri` (fixed constant), `scope=openid email` (drop `profile`: less PII; `email` + `email_verified` are what linking needs), `state`, `nonce`, `code_challenge`, `code_challenge_method=S256`. No `audience`, no `offline_access`, no `screen_hint`.

**PKCE:** verifier = `base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=")` (43 chars); challenge = `base64url(sha256(verifier))` unpadded. State `secrets.token_urlsafe(32)`, nonce likewise.

**Start route** `GET /login/auth0` (public). GET is deliberate: a navigation, not a form submission, so `form-action 'self'` does not apply to the redirect to Auth0. It only creates a bounded in-memory attempt (max ~4096 entries, 10 min TTL, oldest evicted), so there is no meaningful state change; mutation of durable state happens only in the callback. Response: 303 to Auth0 + `Set-Cookie: sp_oidc=<attempt_id>; HttpOnly; Secure; SameSite=Lax; Path=/callback; Max-Age=600` (the `Secure` flag via `auth.secure_cookie_flag()`). The attempt record holds state, nonce, verifier, validated `next`, created_at. `next` is validated with the existing `_validated_next_route` (exact NAV_TABS membership), which is stricter than the regex in PITFALLS C8.

**Callback** `GET /callback` (public), in this fixed order, each failure a generic 400 page and nothing durable written, the attempt always consumed (`pop`) on first use: (1) cookie present and attempt exists and not expired; (2) `error` param absent; (3) `state` equals stored (`hmac.compare_digest`); (4) token exchange; (5) claim checks; (6) resolve local user (below); (7) create session; (8) respond. Always clear `sp_oidc`.

**Token exchange:** `POST https://{domain}/oauth/token`, form body `grant_type=authorization_code&client_id&client_secret&code&code_verifier&redirect_uri`. Use a `requests.Session()` with `trust_env = False` (no proxy/netrc surprises), `timeout=(3.05, 10)`, `allow_redirects=False`, `verify=True` (never False), `stream=True` and read at most ~64 KiB with a small total-time check (requests' timeouts do not bound a slow drip; mirror the idea in `server/http_fetch.py:80`). Non-200, non-JSON, missing `id_token`: fail. Never log the response body, `code`, tokens or the client secret. Ignore `access_token`. Read the ID token only from this response body.

**Claim checks** (`validate_id_token`, OIDC Core 3.1.3.7; signature skipped because the token arrives directly from the token endpoint over TLS [CITED: openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation, via STACK.md]): three dot-separated parts; header and payload base64url-decode to JSON objects; header `alg` must not be `none`; `iss == "https://{domain}/"` exactly (trailing slash; compare the full string); `aud` is the client id as a string, or a list containing it, and if a list with more than one entry (or `azp` present) `azp == client_id`; `exp` numeric (reject `bool`) and `> now - leeway` with leeway 60 s; `iat` numeric and `<= now + leeway`; `nonce` equals stored (`compare_digest`); `sub` non-empty string, length capped (<= 255); for linking `email` string and `email_verified is True` (strict boolean). Inject `now` for tests.

**Account linking / invite-only** (in `fleet_sessions`, one `BEGIN IMMEDIATE` transaction):
1. `SELECT ... WHERE iss = ? AND sub = ?` found: refuse if `disabled`, else sign in. Email is not consulted again (D-03).
2. Not found: require verified email; find the user by normalized email with `iss IS NULL AND sub IS NULL AND disabled = 0`; `UPDATE users SET iss=?, sub=? WHERE id=? AND sub IS NULL` and require `rowcount == 1` (race-safe; `UNIQUE(iss, sub)` is the backstop).
3. Else refuse. Unknown email, unverified email, email already linked to a different `sub`, and disabled user all show the same generic "not invited" page; the reason code goes to the server log without PII. **No row is ever inserted and no session is created** (D-01).
4. Recommend a small `fleet_cli.py users unlink-identity --email E` (clears `iss`,`sub`) so a user who loses their Auth0 account can be re-invited; without it that lockout needs hand-edited SQL. Also have `users disable` call `delete_sessions_for_user` (belt and braces; the per-request `disabled` check is the real control).

**Landing after callback (SameSite pitfall, known issue).** `sp_session` is `SameSite=Strict`. The callback is a cross-site top-level navigation from Auth0; a 303 to `/` continues the same redirect chain, which Chromium treats as cross-site, so the Strict cookie is withheld and the user bounces to `/login` [CITED: STACK.md "Avoid" table; MEDIUM]. Fix: respond to the callback with a **200 interstitial** carrying `Set-Cookie: sp_session=...` plus `<meta name="referrer" content="no-referrer">`, `<meta http-equiv="refresh" content="0;url=/account|/">` and a visible fallback `<a>` link (no inline script: CSP is `script-src 'self'`; meta refresh is not blocked by that CSP). The refresh is a new same-site navigation, so Strict is sent. Keep the session cookie Strict. If the Playwright test (below) shows otherwise, fall back to `SameSite=Lax` for `sp_session` only (every state-changing route is POST with the Origin/Sec-Fetch-Site gate, `auth.py:363-398`). The `no-referrer` meta keeps `?code=&state=` out of the `Referer` header of the next request, which Caddy would otherwise log (the app sends `Referrer-Policy: same-origin`, `app.py:455`, which still sends the full same-origin URL).

**Sign-out** (D-12). Auth0 documents `GET https://{domain}/v2/logout?client_id=...&returnTo=<url-encoded>`; with `client_id` present the `returnTo` must be in the **application's** Allowed Logout URLs (exact match, query strings must match exactly) [CITED: auth0.com/docs/authenticate/login/logout/redirect-users-after-logout]. Auth0's current main page documents RP-initiated `end_session_endpoint` for tenants created on/after 2023-11-14 [CITED: auth0.com/docs/authenticate/login/logout/log-users-out-of-auth0]; `/v2/logout` is the owner-locked choice and its legacy reference page returned 404 when fetched, so the manual real-tenant smoke test must include sign-out (MEDIUM). Flow: `POST /logout` (min role user): delete the session row and clear the cookie **first**, then return a 200 interstitial with meta refresh to the Auth0 URL (not a 303: `form-action 'self'` makes Chromium cancel a redirect to a foreign origin after a form POST [CITED: Mozilla bug 1646559, Phabricator commit, w3c/webappsec-csp#8 via web search]). For a `legacy-admin` session or when Auth0 is unconfigured, 303 to `/login` as today. `returnTo` = `https://<companion host>/login`. An Auth0 hop failure cannot undo the local logout.

**Caddy redaction** [CITED: caddyserver.com/docs/caddyfile/directives/log]. The `format filter` encoder supports `request>uri query { delete <key> | replace <key> <v> | hash <key> }` and `wrap json`; it applies to the whole log block, not to one path. The companion site block currently logs to stdout in JSON (`deploy/Caddyfile`, second block). Recommended change:
```
log {
    output stdout
    format filter {
        wrap json
        request>uri query {
            delete code
            delete state
            delete error_description
        }
    }
}
```
`deploy/tests/test_caddyfile.py` parses site blocks by brace depth (lines ~29-34) and must keep passing; add an assertion that the rendered companion block contains the redaction. Verify syntax with `caddy validate` on the VPS or in CI if available (`caddy` is not installed in this sandbox; unverified here).

**Legacy-admin.** `SKYPANE_LEGACY_PASSWORD_LOGIN`: unset or `1` = enabled (today's behaviour), `0` = disabled, **any other value = refuse to start** (a typo must not leave a backdoor on). Flag off: GET `/login` does not render the password form; POST `/login` answers 403 without calling `password_ok` or touching the throttle. Flag on: throttle -> `password_ok` -> create a `legacy-admin` session -> `print` an audit line on every success and every lockout (IP bucket, never the password). Legacy sessions are re-checked against the flag on every request, so turning the flag off cuts them immediately. Show a persistent "legacy sign-in" indicator (Account page and Health row at minimum; if placed in the shared shell, regenerate `render_baseline.json` deliberately). D-08: the removal task is event-driven ("when Auth0 sign-in is in production"); put the trigger text in the removal task and report to the owner that the roadmap's "dated" wording is now event-driven.

**Startup rule (`main()`).** Fail closed: legacy enabled requires the password; Auth0 variables are all-or-nothing (partial set = exit 1 naming the missing variables, never values); at least one method must be usable.

## Sessions (D-10 specifics)

- Cookie value = `secrets.token_urlsafe(32)`; DB stores `sha256(token)` hex only. Rotation: login always issues a new token and deletes any session whose cookie accompanied the login request. Logout deletes the row. Lookup is one JOIN against `users` giving `role` and `disabled`; absent/expired/idle/disabled all return "no principal".
- Absolute lifetime 30 d (`expires_at`), idle 7 d (`now - last_seen_at > 7 d` -> delete and refuse). **Throttle `last_seen_at` writes** (e.g. only when older than 5 minutes): `companion/static/freshness.js` polls pages periodically, so an unconditional write per request would hammer SQLite for no benefit at a 7-day granularity.
- Per request: open `fleet_db.connect(state_dir)` lazily (mirror `history_db.connection_scope` used by `do_GET`/`do_POST`, `app.py:923-932,1256-1263`), close at the end. Any `sqlite3.Error`/`FleetDbError` while resolving a principal: answer 503 for gated routes rather than redirecting to `/login` (which would loop); fail closed, never "allow".
- `Set-Cookie` attributes unchanged: `HttpOnly; Secure (unless the dev opt-out); SameSite=Strict; Path=/; Max-Age=2592000`.
- CSRF (Claude's discretion): keep `SameSite=Strict` + the existing Origin/Sec-Fetch-Site gate (`auth.py:363-398`); do **not** add per-session CSRF tokens in this phase. Adding tokens means editing every form across ~7 page modules and changes the committed render baseline wholesale, for no new exposure in this phase (the only new multi-user surface is the Account page, whose actions are sign-out and cosmetic preferences). Record it as an Open Question: Phase 55 adds destructive admin actions and should revisit.

## Fake Auth0 Design (question 5)

New `test-support/fake_auth0.py` (stdlib `ThreadingHTTPServer` on `127.0.0.1:0` in a daemon thread, same pattern as `InProcessAppServer`; no pytest import). Works against both the subprocess `AppServer` (the child's own network guard allows loopback and loopback DNS names, `skypane_test_support.py:132-149`) and `InProcessAppServer`.

Endpoints
- `GET /authorize`: checks `response_type=code`, `client_id`, exact `redirect_uri` against the registered one, `code_challenge_method=S256`, `state`, `nonce`, `scope` contains `openid`; records `code -> {challenge, nonce, redirect_uri, identity}`; 302 to `redirect_uri?code=..&state=..`. The test picks who logs in with `fake.next_login(sub=, email=, email_verified=)`.
- `POST /oauth/token`: checks `grant_type`, `client_id`/`client_secret` (post), `redirect_uri`, **PKCE** (`sha256(code_verifier)` equals stored challenge via `compare_digest`), single-use codes (replay -> 400 `invalid_grant`), returns JSON `{id_token, access_token, token_type: "Bearer", expires_in}`. The `id_token` has header `{"alg":"RS256","typ":"JWT"}` and a junk signature, proving production never depends on the signature.
- `GET /v2/logout`: records `client_id`, `returnTo`; 302 to `returnTo` only if it is in the fake's allowed list, otherwise a 400 page (mirrors the real allow-list behaviour).
- `fake.calls`: ordered log of requests (assert, for example, that the token endpoint was **not** called after a state mismatch).

Failure knobs (each a test): `claims(iss=, aud=, azp=, nonce=, exp=, iat=, sub=None)` overrides/removals; `email_verified=False`; `redirect_state=<other>`; `redirect_error="access_denied"`; `token_status=500`; `token_body="not json"`; `omit_id_token`; `token_delay_s` (to hit the 10 s read timeout, use a short `SKYPANE` test timeout env or a patched constant); `alg="none"`; `reuse_code`; `wrong_redirect_uri`. The app's issuer is built from `SKYPANE_AUTH0_DOMAIN=127.0.0.1:<port>` so the production code path is the tested one (no `if TEST` branch; M7).

Browser test (Playwright, `companion/conftest.py` `new_context` guard allows `127.0.0.1`, `localhost`, `::1`): ports are ignored by "site", so `127.0.0.1:A` and `127.0.0.1:B` are **same-site** and would not reproduce the SameSite chain problem. Make the page reach the fake as `localhost:<fake-port>` (set `SKYPANE_AUTH0_DOMAIN=localhost:<port>` and the app at `127.0.0.1:<port>`; `localhost` vs `127.0.0.1` are different sites). The fake listens on `127.0.0.1`; `requests` falls back from `::1` to `127.0.0.1`. The test then asserts: login lands on the signed-in page (not `/login`) with the session cookie present, then sign-out ends on the `returnTo` page. Write it first against a plain 303 landing to see it fail (MEDIUM-confidence behaviour proven by test), then switch to the interstitial.

Extend `AppServer`/`InProcessAppServer` with Auth0 helpers (`login_via_auth0(server, fake, ...)` returning the cookie, a non-following client that performs the two hops by hand) in `companion_app_server.py`, beside `login()`.

## Frame Auth Untouched (AUTH-06)

`stub-server/byos_server.py` is not modified in behaviour. Frames authenticate by MAC + secret hash (+ token) from `fleet.db`/legacy files (`byos_server.py:304-460`); no session or Auth0 code is imported there. Proof tests: `stub-server/test_phase47_freeze.py` and `test_fleet_auth.py` stay green; add one assertion that `devices`/`registry_view` content is unchanged after creating sessions and linking identities, and that a session cookie does not authenticate a byos request (and a device token does not authenticate a companion route; M9). Only the schema version changes (see migration gotcha 1).

## companion read/write of fleet.db today (question 7)

- Today the companion **never opens** `fleet.db`; it only reads `fleet_status.json` through `fleet_db.read_status` (`companion/health_signals.py:520-524`). byos uses `connect_readonly` for reads and `connect(create=False)` for token writes and mirroring (`byos_server.py:375-450`); `fleet_cli` and `fleet_migrate` use `connect`.
- After this phase the companion is a third writer. SQLite WAL handles it (busy timeout 5 s, `fleet_db.py:57,138-143`); keep each write transaction tiny (`BEGIN IMMEDIATE`).
- Permissions: `skypane-companion.service` runs `User=skypane`, `ReadWritePaths=/opt/skypane/state`, `UMask=0027`. `fleet.db` is created 0600 by `fleet_db.connect` (`fleet_db.py:175-196`) and owned by `skypane` because migration and CLI run as `skypane` (`activate.sh:258,270`; README uses `sudo -u skypane`). The companion can therefore read and write it, and `-wal`/`-shm` files inherit the file's mode. Failure mode to document: an operator running `fleet_cli` as root leaves a root-owned `fleet.db` (or its `-wal`) that the companion cannot write; sessions would fail closed with 503. Add a README line.
- Secrets: `skypane.env` is `root:root 0600` and loaded by systemd (`provision.sh:104-108`); the client secret goes there, never in the repo. Health page may show "Auth0 configured: yes/no" only (M8).

## Phase 51 Split (question 8)

| Work | Now | After Phase 51 |
|------|-----|----------------|
| OIDC client, callback, logout, fake Auth0, linking, sessions, legacy fallback, Account page | yes | — |
| `Access` annotation, `decide()`, `device_for()`, `get_device_owner` | yes | — |
| Matrix harness (pure + HTTP layers), probe family `/d/<id>/_probe` with two users/two devices | yes | — |
| Real `/d/<id>/...` routes (display, history, health, poll, config...) | no | add `Route(..., Access(USER, "device"))` + matrix rows |
| Per-device derived resources (images, history, battery charts, firmware status; PITFALLS C5) | no | each gets a row; none may query `devices` directly |
| Reduced user view, pairing, admin console | no | Phase 55 |

Build so Phase 51 only appends rows: the expectation table in the matrix test keys on `(method, matcher)` and the completeness test will fail until each new route is listed. Interface contract to state in the plan: device-scoped handlers receive an already-authorized device (the gate resolves it) and never call `fleet_db` for devices themselves.

## Architecture Patterns

### System Architecture Diagram

```
Browser ──GET /login/auth0──> companion ──(AttemptTable: state,nonce,verifier,next)
   ^                              │ 303 + Set-Cookie sp_oidc (Lax, Path=/callback)
   │                              v
   │                       Auth0 /authorize ──(user logs in)── 302 ──> Browser
   │                                                                      │
   └──GET /callback?code&state (Lax cookie sent)──────────────────────────┘
        companion: pop attempt -> state ok? -> POST /oauth/token (requests, TLS, timeouts)
                   -> validate_id_token -> link/lookup user (fleet.db, one txn)
                   -> create session row (hash) -> 200 interstitial + Set-Cookie sp_session (Strict)
        Browser: meta refresh -> GET /account|/ (same-site, Strict cookie sent)

Every other request:
   Cookie sp_session -> sha256 -> sessions JOIN users (disabled? idle? expired? legacy flag?)
        -> Principal|None -> routes.match -> decide(principal, route.access, captured, owner_lookup)
        -> ALLOW: handler | LOGIN: 303 /login[?next] | NOT_FOUND: 404 page

POST /logout: delete session row + clear cookie -> 200 interstitial -> meta refresh -> Auth0 /v2/logout?client_id&returnTo -> /login
Frame: MAC+secret -> byos (unchanged, no sessions, no Auth0)
```

### Recommended Project Structure
```
companion/
  auth.py          # + new_session_token / hash_session_token; token/revocation code removed
  oidc.py          # pure OIDC: PKCE, authorize URL, validate_id_token, exchange_code, AttemptTable
  access.py        # Principal, RANK, decide(), device_for()
  sign_in.py       # Handler mixin: /login/auth0, /callback, /logout, /account
  routes.py        # Access, Route (validated), PUBLIC/SIGNED_IN/ADMIN_ONLY
  login_page.py    # Auth0 button + secondary legacy password form; account page markup
  i18n_fr/         # FR strings for every new literal
server/
  fleet_db.py      # migration v2 + race fix; get_device_owner
  fleet_sessions.py# session + linking SQL (typed; add to [tool.mypy] files)
  fleet_migrate.py # schema-pending counts as needs_write
stub-server/fleet_cli.py   # users unlink-identity; disable also drops sessions
test-support/fake_auth0.py # fake IdP + knobs; helpers in companion_app_server.py
deploy/            # skypane.env.example, README (Auth0 owner steps), Caddyfile redaction, test_caddyfile
```

### Anti-Patterns to Avoid
- Deriving anything from the password for sessions (D-07). Reading role from the cookie/token/Auth0 (C4). Matching users by email after the first link (C2). `verify=False` anywhere. Putting an `if TEST` branch in production code instead of config (M7). Letting any handler query `devices` directly (C5). Redirecting 303 to a foreign origin after a form POST (CSP `form-action`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Random ids / PKCE verifier | custom PRNG | `secrets.token_urlsafe` / `token_bytes` | CSPRNG |
| Constant-time compare (state, nonce, password) | `==` | `hmac.compare_digest` | Timing |
| Cookie parsing | regex | existing `auth.parse_cookies` | Already hardened (`auth.py:210-222`) |
| Login throttling | new counter | existing `LoginThrottle` | Bounded, IPv6-/64 aware (`auth.py:249-352`) |
| Origin/Fetch-Metadata POST gate | new check | existing `post_origin_ok` | Already first statement of `_dispatch` |
| Schema versioning | ad-hoc `ALTER` at startup | `fleet_db.MIGRATIONS` + `migrate_schema` | Atomic with version bump |
| Next-URL safety | regex/prefix check | existing `_validated_next_route` (exact set membership) | Stricter than any regex |
| JWT signature verification | RSA code | not needed (token from token endpoint over TLS) | Owner decision D-02; hand-rolled RSA is error-prone |

**Key insight:** the risky parts are glue and ordering (state before exchange, claims before linking, linking before session, attempt consumed once), not primitives; keep each step a small pure function with an injected clock and HTTP callable.

## Common Pitfalls

### Pitfall 1: `pinned_request` cannot reach the fake (or a loopback dev Auth0)
**What goes wrong:** Reusing `server.http_fetch.pinned_request` (suggested in STACK.md) fails: https-only and `resolve_public_addresses` refuses loopback (`http_fetch.py:320-346`). **Avoid:** `requests` with `trust_env=False`, https enforced except an explicit loopback-only test flag.

### Pitfall 2: Strict session cookie lost after the Auth0 redirect
**What goes wrong:** 303 from `/callback` to `/` is a cross-site chain; Chromium withholds the Strict cookie and the user lands on `/login`. **Avoid:** 200 interstitial + meta refresh; prove with a Playwright test using a different host name (`localhost` vs `127.0.0.1`), because same-host different-port is same-site and hides the bug.

### Pitfall 3: `form-action 'self'` blocks redirects to Auth0 after a POST
**What goes wrong:** `POST /logout` answering 303 to Auth0 is cancelled by Chromium. **Avoid:** interstitial with meta refresh; start login with a GET link, not a form.

### Pitfall 4: v2 schema never applied / applied twice
See migration gotchas 2 and 3: make `fleet_migrate` upgrade pending schema steps; re-check `user_version` inside the transaction.

### Pitfall 5: Information leaks through the shared 404/403 pages
`_not_found_page()` and `_forbidden_page()` (`app.py:643-675`) compute the Health nav dot for any authenticated caller; for a `user` that leaks fleet health, and "Back to Home" (`/`) is itself a 404 for them. Restrict the health read to admin/legacy-admin and point a `user` at `/account`. Add a test that a `user` 404 body contains no health dot and no admin nav.

### Pitfall 6: Theme/lang POST returns to the wrong page for a user
`_referring_tab()` (`app.py:826-833`) only accepts NAV_TABS paths, else `/` (admin-only -> 404 for a user). Add the account route to the allowed set (or have `_handle_theme_post/_handle_lang_post` use the principal's home). Likewise the post-login destination for a `user` is `/account`, ignoring an admin-only `next`.

### Pitfall 7: Fixture and baseline fallout
Retiring the token API breaks ~15 tests in `test_companion_app_01.py` (rewrite, do not weaken) and any test touching `auth._REVOKED`. New routes need entries in `render_baseline.json` (`test_route_table.py` indexes it by route key). Every test state dir now also gets a `fleet.db` (check tests that list state-dir contents: `test_status_pages_01/03`, `test_view_pages_04`, `test_companion_app_04b/05`, `test_preview_cache`, `test_display_looks`, `test_browser_policy`).

### Pitfall 8: Writes on every request
Unthrottled `last_seen_at` updates plus the freshness poll create constant WAL writes. Update at most every few minutes.

### Pitfall 9: Partial configuration silently enabling a weak mode
Typo in `SKYPANE_LEGACY_PASSWORD_LOGIN` or one missing Auth0 variable must stop startup with a clear message (variable names only).

### Pitfall 10: Logs
Caddy logs query strings (`code`, `state`) and the follow-up `Referer`; app `log_message` is already query-free (`app.py:1267-1272`). Add the Caddy filter and the `no-referrer` meta; never print tokens, codes or the client secret; print user ids and reason codes only.

## Code Examples

### PKCE and authorize URL
```python
# Source: RFC 7636 section 4 / Auth0 PKCE docs (as recorded in research/STACK.md)
def new_pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge

def authorize_url(cfg, state, nonce, challenge):
    query = urllib.parse.urlencode({
        "response_type": "code", "client_id": cfg.client_id,
        "redirect_uri": cfg.redirect_uri, "scope": "openid email",
        "state": state, "nonce": nonce,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    return "%s/authorize?%s" % (cfg.base_url, query)
```

### Token exchange (injected callable keeps unit tests socket-free)
```python
def exchange_code(cfg, code, verifier, post):
    resp = post(cfg.base_url + "/oauth/token", data={
        "grant_type": "authorization_code", "client_id": cfg.client_id,
        "client_secret": cfg.client_secret, "code": code,
        "code_verifier": verifier, "redirect_uri": cfg.redirect_uri})
    if resp.status != 200:
        raise SignInError("token_status_%d" % resp.status)   # never include the body
    doc = resp.json_capped(64 * 1024)
    token = doc.get("id_token") if isinstance(doc, dict) else None
    if not isinstance(token, str):
        raise SignInError("no_id_token")
    return token
```

### Interstitial landing (no inline script; CSP-safe)
```python
def landing_page(target):
    safe = layout.escape_html(target)
    return ('<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer">'
            '<meta http-equiv="refresh" content="0;url=%s"><title>SkyPane</title>'
            '<p><a href="%s">Continue</a></p>' % (safe, safe))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/v2/logout` as the sole logout | RP-initiated `end_session_endpoint` default on tenants created on/after 2023-11-14 | 2023-11-14 | Owner locked `/v2/logout`; include sign-out in the manual real-tenant smoke test; keep the URL builder isolated so switching is a one-function change |
| Implicit/hybrid flows | Code + PKCE, even for confidential clients (RFC 9700) | 2025 | Matches D-02 |

**Deprecated/outdated:** shared-password stateless cookie (this phase retires it); `plain` PKCE method.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Chromium sends a Strict cookie on a meta-refresh navigation that follows a cross-site callback response, while it withholds it on a direct 303 chain | OIDC / Landing | Login bounces to `/login`; fallback is `SameSite=Lax` for `sp_session` (documented). Prove with the Playwright test |
| A2 | Auth0 Regular Web App honours `code_challenge` and rejects a wrong `code_verifier` (STACK.md already marks MEDIUM) | OIDC | Manual smoke test is the gate; fallback Native app type |
| A3 | `/v2/logout?client_id&returnTo` still works on a tenant created after 2023-11-14 | Sign-out | Sign-out leaves Auth0 SSO session alive; switch the URL builder to `end_session_endpoint` / `post_logout_redirect_uri` |
| A4 | Caddy `format filter { wrap json; request>uri query { delete ... } }` renders as written in the deployed Caddy version | Caddy | Redaction silently absent; validate on the VPS (`caddy validate`) |
| A5 | Denying an authenticated-but-unauthorised request with 404 (not 403) is acceptable to the owner | Access annotation | UX/wording only; matrix has one extra outcome if 403 is chosen |
| A6 | Skipping per-session CSRF tokens this phase is acceptable | Sessions | Weaker defence in depth for Phase 55's admin actions; revisit there |
| A7 | Chromium resolves `localhost` to loopback so the browser test can reach a fake bound to `127.0.0.1` | Fake Auth0 | Bind the fake on `::1` as well or use a `*.localhost` name |
| A8 | `requests` falls back from `::1` to `127.0.0.1` for `localhost` | Fake Auth0 | Use `127.0.0.1` for the server-side leg via a separate config knob |

## Open Questions

1. **Per-session CSRF token now or in Phase 55?** Recommendation: defer; keep Strict + Origin gate (A6). Owner/planner to confirm.
2. **Where should the "legacy sign-in" flag be shown?** Shared shell (all pages; forces a baseline regeneration) vs Account and Health only. Recommend Account + Health row to keep the diff small; D-07 says "flagged in the UI" and either satisfies it.
3. **Companion public URL source:** derive from `SKYPANE_COMPANION_HOST` (no new variable) with an optional override. Confirm at plan time.
4. **403 vs 404 for role denial** (A5).
5. **Event-driven removal wording (D-08):** the roadmap success criterion says "dated removal task". Surface to the owner at the end that it is event-driven, with the date stamped at go-live.
6. **`users unlink-identity` CLI verb** is outside the strict requirement text but prevents a permanent lockout; recommended, small.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | yes | 3.13.17 (sandbox), venv 3.13 (`server/.venv`), prod 3.14 | — |
| pytest toolchain + Playwright Chromium | tests, redirect-chain test | venv present (`server/.venv/bin`); Chromium not probed here | — | CI requires it (`_browser_required`, `companion/conftest.py:108-116`) |
| Caddy | validating the log-filter syntax | no (`command -v caddy` empty) | — | validate on the VPS during deploy; pure-text assertion in `test_caddyfile.py` |
| Real Auth0 tenant | manual smoke test only | not contacted (by instruction) | — | owner step, documented, not CI |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 + pytest-xdist + pytest-cov + pytest-socket (loopback only) + pytest-playwright |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, addopts lines 43-56; `--disable-socket --allow-hosts=127.0.0.1,::1,localhost`) |
| Quick run command | `server/.venv/bin/python -m pytest companion/test_oidc.py companion/test_access.py server/test_fleet_sessions.py -x -q -p no:cacheprovider` |
| Full suite command | `./scripts/run-all-tests.sh` (wraps `pytest -n auto --cov`) |
| Other gates | `server/.venv/bin/ruff check .`, `server/.venv/bin/mypy`, `scripts/check_function_size.py check --max 80 server stub-server`, `scripts/check_comment_history.py check` (no phase/decision IDs in comments) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | PKCE/authorize URL shape; claim checks (iss trailing slash, aud str/list, azp, exp+leeway, iat, nonce, sub cap, alg none, bool exp) | unit | `pytest companion/test_oidc.py -x` | no, Wave 0 |
| AUTH-01 | Full login against fake Auth0: happy path, wrong iss/aud/nonce, expired, missing sub, state mismatch, replayed state/code, `error` param, token 500/garbage/no id_token/timeouts, bad verifier, unverified email: each yields no session cookie and no DB row | integration (subprocess + fake) | `pytest companion/test_auth0_login.py -x` | no, Wave 0 |
| AUTH-01 | Invite-only: unknown sub/email creates no `users` row and no session; link once; second login by `sub` only; same email with different `sub` refused; disabled user refused; link race (two concurrent callbacks, one wins) | unit + integration | `pytest server/test_fleet_sessions.py companion/test_auth0_login.py -x` | no, Wave 0 |
| AUTH-01 | Cookie attributes parsed from real `Set-Cookie` (pre-login Lax/HttpOnly/Secure/Path=/callback; session Strict/HttpOnly/Secure); open-redirect table for `next` | integration | `pytest companion/test_auth0_cookies.py -x` | no, Wave 0 |
| AUTH-01 | Real Chromium: login across `localhost`/`127.0.0.1` lands signed in; sign-out ends at `returnTo` | browser | `pytest companion/test_browser_auth0.py -x` | no, Wave 0 |
| AUTH-02 | Flag unset/1 = password works; 0 = POST `/login` 403 and no throttle/password call; invalid value exits non-zero; throttle lockout; audit line printed; legacy session dies when flag turned off; no key derived from password (restart-independent: sessions survive an app restart, token not verifiable with password) | integration | `pytest companion/test_legacy_admin.py -x` | no, Wave 0 |
| AUTH-02 | Sessions: 256-bit id, only hash stored, rotation on login, deleted on logout, 30 d absolute, 7 d idle (injected clock), disabled cut off next request, `last_seen_at` write throttle | unit + integration | `pytest server/test_fleet_sessions.py companion/test_sessions_http.py -x` | no, Wave 0 |
| AUTH-02 | Rewritten replacement for the retired token tests | unit | `pytest companion/test_companion_app_01.py -x` | yes (rewrite Section 1) |
| AUTH-03 | Route x role x owner matrix, pure layer and HTTP layer (stub handlers), probe `/d/<id>/_probe` family, completeness vs ROUTES, user 404 body equals unknown-path 404 and has no health dot | unit + integration | `pytest companion/test_access_matrix.py -x` | no, Wave 0 |
| AUTH-03 | `Route` without `Access` cannot be constructed; public set is exactly login, callback, login/auth0 and static assets | unit | `pytest companion/test_route_table.py -x` | yes (update) |
| AUTH-03 | Account page: identity, language, theme, sign out, empty-state; EN and FR strings; theme/lang POST returns to `/account` | integration | `pytest companion/test_account_page.py -x` | no, Wave 0 |
| AUTH-06 | Freeze and fleet auth unchanged; frame request unaffected by sessions; session cookie does not authenticate byos; device token does not authenticate companion | integration | `pytest stub-server/test_phase47_freeze.py stub-server/test_fleet_auth.py -x` | yes (+ new assertions) |
| AUTH-06 | Fake Auth0 itself: PKCE enforcement, single-use code, redirect_uri exact match, logout allow-list | unit | `pytest test-support/test_fake_auth0.py -x` | no, Wave 0 |
| Migration | v1 -> v2 in place; idempotent; two-connection upgrade race; `fleet_migrate` applies pending schema and dry-run reports it; too-new refusal still works; backup/restore round trip at v2 | unit | `pytest server/test_fleet_db.py server/test_fleet_migrate.py deploy/tests/test_backup.py -x` | yes (extend) |
| Deploy | Caddy companion block carries the query redaction; env example documents the new variables | unit | `pytest deploy/tests/test_caddyfile.py deploy/tests/test_docs.py -x` | yes (extend) |

### Sampling Rate
- **Per task commit:** the quick run command for the touched module plus `ruff` and `mypy`.
- **Per wave merge:** `./scripts/run-all-tests.sh`.
- **Phase gate:** full suite green (including Playwright), function-size and comment-history gates, `render_baseline.json` regenerated only deliberately, then `/gsd:verify-work`. Manual owner step after merge: real-tenant smoke test (login, wrong `code_verifier` rejected, sign-out returns to the allowed URL).

### Wave 0 Gaps
- [ ] `test-support/fake_auth0.py` and `test-support/test_fake_auth0.py` (+ helpers in `companion_app_server.py`).
- [ ] `companion/test_oidc.py`, `test_auth0_login.py`, `test_auth0_cookies.py`, `test_browser_auth0.py`, `test_legacy_admin.py`, `test_sessions_http.py`, `test_access_matrix.py`, `test_account_page.py`; `server/test_fleet_sessions.py`.
- [ ] Rewrite Section 1 of `companion/test_companion_app_01.py`; update `test_route_table.py`; regenerate `render_baseline.json`.
- [ ] Add new typed modules to `[tool.mypy] files`; no framework install needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Auth0 code + PKCE, invite-only linking on verified email then `sub`; legacy password throttled, constant-time, flagged |
| V3 Session Management | yes | 256-bit opaque id, hash stored, rotation, absolute + idle expiry, server-side delete on logout, HttpOnly/Secure/SameSite=Strict |
| V4 Access Control | yes | `Access` annotation, default-deny at construction, `decide()`, 404 for foreign devices, matrix test |
| V5 Input Validation | yes | Exact-match `next`, device-id regex, capped token response, capped `sub`, strict claim types |
| V6 Cryptography | yes | `secrets`, `hashlib`, `hmac.compare_digest`; no hand-rolled crypto; TLS verification on |
| V7 Error handling / logging | yes | Generic failure pages, reason codes only in logs, no codes/tokens/secrets logged, Caddy query redaction |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Login CSRF / code injection | Spoofing | `state` bound to a Lax pre-login cookie + server-side attempt, single use, PKCE |
| Token substitution (other client/tenant) | Spoofing | `iss`, `aud`, `azp`, `nonce` checks; token only from token endpoint |
| Account takeover via email | Elevation | Link only on `email_verified is True` to an uninvited-`sub` row; match on `sub` afterwards; refuse if already linked to another `sub` |
| Open sign-up | Elevation | No insert path in the callback; tenant sign-up also disabled (owner step) |
| Session fixation / theft | Spoofing | New id on login, hash-only storage, Strict+HttpOnly+Secure |
| Role escalation / IDOR | Elevation | Role from DB per request; single device accessor; 404 for foreign |
| Open redirect | Tampering | Fixed `redirect_uri`/`returnTo`; `next` exact-membership |
| Shared-password backdoor | Elevation | Flag, throttle, audit, startup refuses typos, event-driven removal |
| Secret leakage in logs | Info disclosure | Caddy `query delete`, `no-referrer`, no body logging, client secret only in `skypane.env` 0600 |
| SSRF via Auth0 domain | Tampering | Domain only from operator env; no redirects followed; no proxy env |
| Slow-drip token response | DoS | connect/read timeouts + capped read + total-time check |

## Sources

### Primary (HIGH confidence)
- Codebase read directly: `companion/auth.py`, `app.py`, `routes.py`, `login_page.py`, `conftest.py`, `test-support/companion_app_server.py`, `server/fleet_db.py`, `fleet_migrate.py`, `server/http_fetch.py`, `stub-server/fleet_cli.py`, `byos_server.py` (fleet bridge), `test_phase47_freeze.py`, `deploy/*` (service, env example, Caddyfile, README, activate.sh), `pyproject.toml`, `scripts/*`, `.github/workflows/ci.yml`.
- `.planning/workstreams/v1-2/research/STACK.md` and `PITFALLS.md` (Auth0/OIDC specifics, C1-C9, M7-M9, m2, m4-m6) and `54-CONTEXT.md`.

### Secondary (MEDIUM confidence)
- Caddy `log` directive docs, fetched today: https://caddyserver.com/docs/caddyfile/directives/log (filter encoder, `query` actions; per-path filtering not documented).
- Auth0 "Redirect users after logout", fetched today: https://auth0.com/docs/authenticate/login/logout/redirect-users-after-logout (`/v2/logout`, `returnTo`, `client_id`, Allowed Logout URLs at application vs tenant level).
- Auth0 "Log users out of Auth0", fetched today: https://auth0.com/docs/authenticate/login/logout/log-users-out-of-auth0 (RP-initiated logout, `end_session_endpoint` default for tenants from 2023-11-14, exact-match allow list).

### Tertiary (LOW confidence)
- Web search on Chromium enforcing CSP `form-action` on redirects after a form POST (Mozilla bug https://bugzilla.mozilla.org/show_bug.cgi?id=1646559, Phabricator OAuth commit, https://github.com/w3c/webappsec-csp/issues/8): consistent, but browser behaviour; covered by the Playwright test.
- Auth0 legacy `/v2/logout` API reference URL returned 404 when fetched; behaviour on post-2023 tenants unverified.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new packages; reuse verified in code.
- Architecture: HIGH for codebase integration points (read directly); MEDIUM for browser redirect-chain behaviour (A1) until the browser test runs.
- Pitfalls: HIGH for the codebase-derived ones (migration, `pinned_request`, health leak, baseline fallout); MEDIUM for Auth0/Caddy specifics.

**Research date:** 2026-10-30
**Valid until:** 2026-11-30 (Auth0 logout behaviour and Caddy syntax are the fast-moving parts; re-check at the real-tenant smoke test)
