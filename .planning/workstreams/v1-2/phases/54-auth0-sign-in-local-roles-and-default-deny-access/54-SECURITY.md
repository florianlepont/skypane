---
phase: 54
slug: auth0-sign-in-local-roles-and-default-deny-access
asvs_level: not declared in config (audited as L2)
threats_total: 65
threats_open: 0
threats_closed: 65
unregistered_flags: 0
---

# Phase 54 Security Verification

Audit date 2026-10-30. Read-only: no source files edited, nothing committed.
Method: each declared mitigation located in code (file:line) and tied to a test.
Test results were taken from the plan summaries (4467 passed); tests were not re-run.

Result: 0 open threats. Four non-blocking observations are listed at the end.

## Threat Register

### Plan 01: sessions and identity linking (server/fleet_sessions.py, server/fleet_db.py)

| ID | Disp | Code evidence | Test evidence | Status |
|----|------|---------------|---------------|--------|
| T-54-01-01 | mitigate | `_link_by_email` fleet_sessions.py:~178: UPDATE `WHERE ... iss IS NULL AND sub IS NULL AND disabled = 0`, `rowcount != 1` refused; `resolve_login` requires `email_verified is True`; no INSERT into users anywhere in the module; `UNIQUE (iss, sub)` fleet_db.py:92 | test_fleet_sessions.py:135 (links once), :144 (refusals insert nothing), :186 (concurrent links, one winner) | CLOSED |
| T-54-01-02 | mitigate | `_by_identity` matches (iss, sub) first; `_link_by_email` returns `email_linked_other` if iss/sub set | test_fleet_sessions.py:129, :168 | CLOSED |
| T-54-01-03 | mitigate | `create_session` stores only the `id_hash` argument; sign_in.py:~158 passes `auth.hash_session_token(token)` (auth.py:76, sha256); deploy/README.md:658-664 documents that backups carry session hashes | test_fleet_sessions.py:37; companion/test_sessions_http.py:50 | CLOSED |
| T-54-01-04 | mitigate | `create_session(replace_hash=...)` DELETE then INSERT inside one `fleet_db.transaction` | test_fleet_sessions.py:109; test_sessions_http.py:59; test_auth0_login.py:80 | CLOSED |
| T-54-01-05 | mitigate | `lookup_session` joins `users` on every call and reads role and disabled fresh; session row holds neither | test_fleet_sessions.py:89, :101; test_access_matrix.py:397, :408, :440 | CLOSED |
| T-54-01-06 | mitigate | fleet_db.py `migrate_schema`: `BEGIN IMMEDIATE`, then `schema_version(conn) > index` re-read inside the lock | test_fleet_db.py:376 (concurrent upgrades both end at v2) | CLOSED |
| T-54-01-07 | accept | deploy/README.md:658-664 ("Schema v2 and rollback"); `FleetDbTooNew` raised at fleet_db.py:163 | test_fleet_auth cited by plan | CLOSED (documented) |
| T-54-01-SC | accept | No new dependency (requirements unchanged) | n/a | CLOSED |

### Plan 02: OIDC primitives (companion/oidc.py)

| ID | Disp | Code evidence | Test evidence | Status |
|----|------|---------------|---------------|--------|
| T-54-02-01 | mitigate | `validate_id_token` oidc.py:~245: exact `iss == cfg.issuer` (trailing slash), `_check_audience` (aud, azp), `_check_times` (exp, iat, 60 s leeway), `_check_nonce` with `hmac.compare_digest`; `alg: none` refused; token comes only from `exchange_code`'s response | test_oidc.py:153, :191, :205, :215, :222 | CLOSED |
| T-54-02-02 | mitigate | `requests_post` oidc.py:~330-345: `session.trust_env = False`, `session.verify = True`, `verify=True`, `allow_redirects=False`; scheme https unless loopback AND `SKYPANE_AUTH0_ALLOW_INSECURE_LOOPBACK=1` (`_domain_scheme`); domain only from env | test_oidc.py:92, :97, :102, :406 (redirect not followed) | CLOSED |
| T-54-02-03 | mitigate | `TOKEN_CONNECT_TIMEOUT` 3.05, `TOKEN_READ_TIMEOUT` 10, `TOKEN_TOTAL_DEADLINE` 15, `TOKEN_MAX_BYTES` 64 KiB enforced in `_read_capped` | test_oidc.py:387, :397; test_auth0_login.py:200 | CLOSED |
| T-54-02-04 | mitigate | `SignInError` carries a reason code only; no body, code or token in any message | test_oidc.py:268 (no body leak), :115 (repr hides secret) | CLOSED |
| T-54-02-05 | mitigate | `AttemptTable`: capacity 4096, TTL 600 s, oldest evicted, lock-protected | test_oidc.py:298, :309, :316, :321 | CLOSED |
| T-54-02-06 | mitigate | `Auth0Config.from_env` raises `Auth0ConfigError` naming variables only on a partial set | test_oidc.py:73; test_legacy_admin.py:170 | CLOSED |
| T-54-02-SC | accept | `requests` already hash-locked; no new package | n/a | CLOSED |

### Plan 03: sign-in surfaces (companion/login_page.py, ui_shell)

| ID | Disp | Code evidence | Test evidence | Status |
|----|------|---------------|---------------|--------|
| T-54-03-01 | mitigate | `layout.escape_html` for dynamic text; `sign_in_error_page` takes a closed set of kinds; provider `error_description` is never read (sign_in.py:~108 raises a fixed `provider_error`) | test_sign_in_surfaces.py:143, :154, :185 | CLOSED |
| T-54-03-02 | mitigate | One `not_invited_page`, used for every refusal (sign_in.py:~85); no email echoed | test_sign_in_surfaces.py:114; test_auth0_login.py:219 | CLOSED |
| T-54-03-03 | mitigate | User shell has one Account link, no Health dot, no tab bar | test_sign_in_surfaces.py:320, :339; test_access_matrix.py:293 | CLOSED |
| T-54-03-04 | mitigate | Sign-in is a plain GET link (`a.login-signin`) | test_sign_in_surfaces.py:42-48 (`_has_form_ancestor` false), :77 | CLOSED |
| T-54-03-05 | mitigate | `interstitial_page` login_page.py:~423-433 refuses non-local, non-http(s) targets and escapes the attribute; callers pass fixed paths or `oidc.logout_url(cfg)` | test_sign_in_surfaces.py:167, :185 | CLOSED |
| T-54-03-SC | accept | No package | n/a | CLOSED |

### Plan 04: default-deny access and sessions (companion/access.py, routes.py, app.py)

| ID | Disp | Code evidence | Test evidence | Status |
|----|------|---------------|---------------|--------|
| T-54-04-01 | mitigate | `Route.__new__` raises `TypeError` without a valid `Access` (routes.py:~50-60); `_dispatch` app.py:1049-1075 is the single gate; unknown path gets 404 | test_route_table.py:75, :91, :101, :116, :121, :126; test_access_matrix.py:144, :160 | CLOSED |
| T-54-04-02 | mitigate | `DEVICE_ID_RE` validated before `owner_lookup` (access.py:~32-50); owner match or admin; foreign and unknown both give NOT_FOUND, the same 404 as an unknown path | test_access.py:45, :51, :66, :80; test_access_matrix.py:311-357 | CLOSED (see observation 1) |
| T-54-04-03 | mitigate | `session_set_cookie_header` auth.py:105: HttpOnly, Secure (default on), SameSite=Strict; hash-only storage; rotation; `_handle_logout_post` deletes the row first (sign_in.py:~190) | test_sessions_http.py:50, :59, :70, :135; test_auth0_cookies.py:54 | CLOSED |
| T-54-04-04 | mitigate | `_resolve_principal` app.py:~606-620 reads fresh each request and re-checks the legacy flag | test_sessions_http.py:81, :99; test_access_matrix.py:397, :428, :440 | CLOSED |
| T-54-04-05 | mitigate | `_dispatch` catches `_STORE_ERRORS` and answers 503 (app.py:~1068-1070); never ALLOW or redirect | test_sessions_http.py:145 | CLOSED |
| T-54-04-06 | mitigate | `_health_alert_for_admin` app.py:774: returns None unless role is admin | test_access_matrix.py:293; test_account_page.py:141 | CLOSED |
| T-54-04-07 | mitigate | `TOUCH_INTERVAL_S = 300` in `lookup_session` | test_fleet_sessions.py:76 | CLOSED |
| T-54-04-08 | accept | `post_origin_ok` is the first statement of `_dispatch` for POST (app.py:1057); SameSite=Strict; comment at routes.py:~175 records the no-token decision | test_post_origin.py, test_browser_origin.py | CLOSED (documented in code; see observation 2) |
| T-54-04-SC | accept | No package | n/a | CLOSED |

### Plan 05: sign-in flow (companion/sign_in.py, auth.py)

| ID | Disp | Code evidence | Test evidence | Status |
|----|------|---------------|---------------|--------|
| T-54-05-01 | mitigate | Attempt bound to an HttpOnly Lax cookie (auth.py:130); `AttemptTable.pop` consumes it; `hmac.compare_digest` on state (sign_in.py:~113); PKCE S256 (`new_pkce`) | test_auth0_login.py:124, :133, :153, :166, :181; test_auth0_cookies.py:25 | CLOSED |
| T-54-05-02 | mitigate | `_verified_claims` calls `validate_id_token` before `_resolve_invited` (sign_in.py:~76-85, ~118) | test_oidc.py:191; test_auth0_login.py:114 | CLOSED |
| T-54-05-03 | mitigate | `resolve_login` has no INSERT; a refusal returns the shared 403 and creates no session | test_auth0_login.py:114, :219, :240 | CLOSED |
| T-54-05-04 | mitigate | `_validated_next_route` app.py:352 is an exact NAV_TABS membership test; redirect_uri and returnTo derive from config (`Auth0Config.redirect_uri`, `return_to`), never the Host header | test_auth0_login.py:265, :279, :289; test_oidc.py:131, :143 | CLOSED |
| T-54-05-05 | mitigate | `_log` prints reason codes and numeric user ids only; `log_message` app.py:1418 strips the query; interstitial has `<meta name="referrer" content="no-referrer">` (login_page.py:406); Caddy query filter | test_auth0_cookies.py:80, :89 (captured-output check for codes, secret, emails, subs, "eyJ") | CLOSED |
| T-54-05-06 | mitigate | `_land_signed_in` answers a 200 interstitial with meta refresh; rotates the session | test_browser_auth0.py:61, :163 | CLOSED |
| T-54-05-07 | mitigate | Start is a GET; logout hop is a 200 interstitial (sign_in.py:~205) | test_sign_in_surfaces.py:42; test_auth0_login.py:325 | CLOSED |
| T-54-05-08 | mitigate | Bounded `AttemptTable`; token-call limits (see 02-03, 02-05) | test_oidc.py:309, :387, :397 | CLOSED |
| T-54-05-SC | accept | No package | n/a | CLOSED |

### Plan 06: user shell and Account (companion/pages/account_page.py, app.py)

| ID | Disp | Code evidence | Test evidence | Status |
|----|------|---------------|---------------|--------|
| T-54-06-01 | mitigate | Every admin route is `ADMIN_ONLY` (routes.py); `_handle_account_get` reads only the principal and cookies (sign_in.py:~225) | test_account_page.py:123 (every admin GET), :133 (admin POSTs change nothing); test_sessions_http.py:166 | CLOSED |
| T-54-06-02 | mitigate | `decide` returns a single NOT_FOUND outcome; the dot is admin-only | test_account_page.py:123 (byte-identical to an unknown path); test_access_matrix.py:293 | CLOSED |
| T-54-06-03 | mitigate | `home_for` returns `/account` for a user; admin target via `_next_route_of` (exact membership) | test_auth0_login.py:279, :289; test_account_page.py:177 | CLOSED |
| T-54-06-04 | mitigate | Interstitial landing; Strict cookie proven in Chromium across a cross-site hop; fallback not needed (54-06-SUMMARY.md:64) | test_browser_auth0.py:163 | CLOSED (see observation 3) |
| T-54-06-SC | accept | No package | n/a | CLOSED |

### Plan 07: legacy password fallback (companion/app.py, auth.py, sign_in_config.py)

| ID | Disp | Code evidence | Test evidence | Status |
|----|------|---------------|---------------|--------|
| T-54-07-01 | mitigate | `LOGIN_THROTTLE` and the 429 lockout (app.py:~1100-1115); `auth.password_ok`; audit lines at success and lockout; flag off returns 403 before any processing | test_legacy_admin.py:59, :92, :104, :113 | CLOSED |
| T-54-07-02 | mitigate | `legacy_login_enabled` auth.py:81 accepts only unset, "1" or "0"; `validate_sign_in_config` aborts startup (`sys.exit(1)`, app.py:~1459); `_legacy_login_on` fails closed (False) on a bad value at runtime | test_legacy_admin.py:147; test_sessions_http.py:81, :92 | CLOSED |
| T-54-07-03 | mitigate | Sessions are random ids (`new_session_token`) with a server-side hash | test_legacy_admin.py:198 (survives a restart with a different password); test_access_matrix.py:452 | CLOSED |
| T-54-07-04 | mitigate | `_resolve_principal` maps a legacy session to `Principal(KIND_LEGACY_ADMIN, None, None, ADMIN)`; no code builds a USER principal from the password | test_legacy_admin.py:40 | CLOSED |
| T-54-07-05 | mitigate | `SignInConfigError` and `Auth0ConfigError` name variables only; audit lines carry the bucket and event only | test_legacy_admin.py:113, :147-181 | CLOSED |
| T-54-07-06 | mitigate | `legacy_login_success` and `legacy_login_lockout` print lines (app.py:~1108-1114); legacy pill in the UI | test_legacy_admin.py:113; test_sign_in_surfaces.py:351 | CLOSED |
| T-54-07-SC | accept | No package | n/a | CLOSED |

### Plan 08: access matrix tests

| ID | Disp | Evidence | Status |
|----|------|----------|--------|
| T-54-08-01 | mitigate | test_access_matrix.py:144 (every route has a row, every row a route), :160 (a dummy route without a row is reported) | CLOSED |
| T-54-08-02 | mitigate | test_access_matrix.py:311, :329, :342, :357 (probe family: owner, foreign, unknown, malformed) | CLOSED |
| T-54-08-03 | mitigate | test_access_matrix.py:452; stub-server/test_auth_independence.py:120, :149 | CLOSED |
| T-54-08-04 | mitigate | `stubbed` fixture test_access_matrix.py:256 replaces handlers with a recorder; :281 asserts the recorded calls | CLOSED |
| T-54-08-05 | mitigate | test_access_matrix.py:397, :408, :420, :428, :440 | CLOSED |
| T-54-08-SC | accept | No package | CLOSED |

### Plan 09: deploy and docs

| ID | Disp | Evidence | Status |
|----|------|----------|--------|
| T-54-09-01 | mitigate | deploy/Caddyfile:62-77 deletes `code`, `state` and `error_description` from `request>uri`; deploy/tests/test_caddyfile.py:191; no-referrer interstitial; deploy/README.md "Log redaction" and 54-HANDOFF.md:40 hold the VPS validation step | CLOSED |
| T-54-09-02 | mitigate | deploy/skypane.env.example:77-84 holds placeholders only; the committed env file is the example only (`git ls-files` shows no other .env); test_caddyfile.py:226; deploy/tests/test_docs.py:139 | CLOSED |
| T-54-09-03 | mitigate | deploy/README.md:606 (disable sign-ups, no social connection); the app refuses uninvited identities (no INSERT path) | CLOSED |
| T-54-09-04 | mitigate | deploy/README.md:605 (exact Allowed Logout URL); `return_to` fixed by config (oidc.py `return_to`) | CLOSED |
| T-54-09-05 | mitigate | 54-LEGACY-ADMIN-REMOVAL.md (trigger, steps, "remove by" blank to stamp at go-live); deploy/README.md "Legacy password fallback" | CLOSED |
| T-54-09-06 | accept | deploy/README.md:658-664 caveat and Health fault | CLOSED (documented) |
| T-54-09-07 | accept | deploy/README.md:663 ("Backups now contain the sessions table (hashes only)") | CLOSED (documented) |
| T-54-09-SC | accept | No package | CLOSED |

## Cross-cutting checks requested

| Check | Result | Evidence |
|-------|--------|----------|
| No secrets in the repo | PASS | The only tracked env file is deploy/skypane.env.example. Auth0 values are `<your-tenant>.eu.auth0.com`, `<auth0-client-id>`, `<auth0-client-secret>`. `SKYPANE_COMPANION_PASSWORD=replace-with-a-long-random-secret` is a placeholder. README uses placeholders only. A grep for `client_secret` outside the venv, planning docs and tests finds only the env name in oidc.py:34, the README placeholder and the env example. |
| Auth0 values only from environment | PASS | `Auth0Config.from_env(os.environ)` is the only source of domain, client id and secret. Redirect and logout URLs come from `SKYPANE_COMPANION_HOST` or `SKYPANE_COMPANION_PUBLIC_URL`, never the Host header. The insecure-loopback flag is only commented out in the example (test_caddyfile.py:240). |
| Tokens, codes and state never logged | PASS | sign_in.py `_log` calls print reason codes, numeric ids and the exception type name. `_config_unavailable` prints `Auth0ConfigError` text, which names variables only. `log_message` prints method and path only. The Caddy filter drops the code and state. test_auth0_cookies.py:89 asserts the captured stdout has no code, secret, email, sub or JWT. |
| TLS verify on for the token call | PASS | oidc.py:336-341 sets `session.verify = True` and `verify=True`. `trust_env=False` means a `REQUESTS_CA_BUNDLE` or `CURL_CA_BUNDLE` env value cannot weaken it. The scheme is https unless the loopback test flag is on. There is no `verify=False` anywhere in non-test code. |

## Accepted Risks Log

| ID | Risk | Where documented |
|----|------|------------------|
| T-54-01-07 | Old release refuses schema v2 and serves from legacy files | deploy/README.md "Schema v2 and rollback" |
| T-54-04-08 | No per-session CSRF token; relies on SameSite=Strict plus the Origin and Sec-Fetch-Site gate | app.py:1043-1049 comments; routes.py comment above QUICK_LED |
| T-54-09-06 | Rollback shows a Health fault until the new release is live | deploy/README.md |
| T-54-09-07 | Backups carry unexpired session hashes | deploy/README.md |

## Unregistered Flags

None. The 54-05 and 54-06 summaries say "None"; the other summaries do not raise any flag.

## Observations (non-blocking, no threat opened)

1. **IDOR coverage is primitive-level only.** No production route currently declares `device_arg`. The ownership gate (`authorized_device_id`) is proven only through unit tests and the test-only probe routes (test_access_matrix.py:168 confirms the probes are not in the production table). The first phase that adds a device-scoped route must set `device_arg`, or the route falls back to the plain role check.
2. **CSRF is accepted, not mitigated.** State-changing admin POSTs rely on SameSite=Strict plus the Origin check. This matches the declared acceptance. Per-session tokens are deferred to the phase that adds admin actions.
3. **T-54-06-04 test scope.** The plan asked for proof "on two different sites". test_browser_auth0.py:163 covers one cross-site origin (127.0.0.1 against localhost). It passes, and the Lax fallback was not needed. If the deployment topology puts Auth0 and the companion on different registrable domains, the real-tenant smoke test in deploy/README.md should confirm it.
4. **ID-token signature not verified locally.** Claims are validated and the token is read only from the TLS back-channel token response. This is documented in the oidc.py docstring and is acceptable for the code flow, since the token never passes through the browser. It relies on the TLS verification confirmed above.
