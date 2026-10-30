---
phase: 54
slug: auth0-sign-in-local-roles-and-default-deny-access
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-30
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. The requirement-to-test map lives in `54-RESEARCH.md` § Validation Architecture; the per-task map below is filled by the plans.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 + xdist + cov + pytest-socket (loopback only) + pytest-playwright |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `server/.venv/bin/python -m pytest companion/test_oidc.py companion/test_access.py server/test_fleet_sessions.py -x -q -p no:cacheprovider` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Other gates** | ruff, mypy, `scripts/check_function_size.py check --max 80 server stub-server`, `scripts/check_comment_history.py check` |
| **Estimated runtime** | ~300 seconds full, ~15 seconds quick |

## Sampling Rate

- **After every task commit:** quick command for the touched module plus ruff and mypy
- **After every plan wave:** full suite
- **Before verify-work:** full suite green, Phase 48 freeze test green
- **Max feedback latency:** 30 seconds (quick)

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 1 | AUTH-01, AUTH-02, AUTH-06 | v2 schema upgrades in place; concurrent upgrade safe; deploy migration applies it; owner lookup selects owner only | unit | `server/.venv/bin/python -m pytest server/test_fleet_db.py server/test_fleet_migrate.py stub-server/test_phase47_freeze.py stub-server/test_fleet_auth.py deploy/tests/test_backup.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-01-02 | 01 | 1 | AUTH-01, AUTH-02 | hash-only sessions, 30 d / 7 d expiry, disabled cut-off; no insert path; link once then match on sub | unit | `server/.venv/bin/python -m pytest server/test_fleet_sessions.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-01-03 | 01 | 1 | AUTH-01, AUTH-02 | unlink-identity re-invite path; disable ends sessions | unit | `server/.venv/bin/python -m pytest stub-server/test_fleet_cli.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-02-01 | 02 | 1 | AUTH-01 | PKCE, config all-or-nothing, claim checks (iss/aud/azp/nonce/exp/iat/alg/sub), hardened token call, bounded attempt table | unit | `server/.venv/bin/python -m pytest companion/test_oidc.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-02-02 | 02 | 1 | AUTH-01, AUTH-06 | fake Auth0 enforces PKCE, single-use code, redirect_uri, logout allow-list; failure knobs | unit | `server/.venv/bin/python -m pytest test-support/test_fake_auth0.py companion/test_oidc.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-03-01 | 03 | 1 | AUTH-01, AUTH-02 | Sign in is a GET link; legacy block only when flag on; refusal/error/interstitial pages generic, escaped, EN+FR | unit | `server/.venv/bin/python -m pytest companion/test_sign_in_surfaces.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-03-02 | 03 | 1 | AUTH-02, AUTH-03 | user shell shows only Account, no health; legacy pill only for legacy-admin; default output byte-identical | unit | `server/.venv/bin/python -m pytest companion/test_sign_in_surfaces.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-04-01 | 04 | 2 | AUTH-03 | Route without Access cannot exist; decide ALLOW/LOGIN/NOT_FOUND; ownership gate rejects hostile ids | unit | `server/.venv/bin/python -m pytest companion/test_access.py companion/test_route_table.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-04-02 | 04 | 2 | AUTH-02, AUTH-03 | server-side principal per request; rotation; logout deletes row; flag-off and disabled cut-off; 503 fail-closed; static assets never open fleet.db | integration | `server/.venv/bin/python -m pytest companion/test_sessions_http.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-04-03 | 04 | 2 | AUTH-02, AUTH-03 | baseline regenerated deliberately, only the pill fragment differs; whole suite green | integration | `./scripts/run-all-tests.sh` | ❌ W0 | ⬜ pending |
| 54-05-01 | 05 | 3 | AUTH-01 | start/callback/logout handlers behind public routes; callback order state-before-exchange | integration | `server/.venv/bin/python -m pytest companion/test_route_table.py companion/test_sessions_http.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-05-02 | 05 | 3 | AUTH-01 | happy path, every failure mode, invite-only refusals, link race, next whitelist, cookie attributes, logout hop, no secret in logs | integration | `server/.venv/bin/python -m pytest companion/test_auth0_login.py companion/test_auth0_cookies.py -x -q -p no:cacheprovider -n auto` | ❌ W0 | ⬜ pending |
| 54-06-01 | 06 | 4 | AUTH-03 | Account route; users get 404 everywhere else; theme/lang return to /account; user shell links reachable only | integration | `server/.venv/bin/python -m pytest companion/test_account_page.py companion/test_route_table.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-06-02 | 06 | 4 | AUTH-01 | cross-site sign-in and sign-out in Chromium, both themes, 360px | browser | `server/.venv/bin/python -m pytest companion/test_browser_auth0.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-07-01 | 07 | 5 | AUTH-02 | flag unset/1/0 semantics, throttle, audit lines, fail-closed startup, restart independence | integration | `server/.venv/bin/python -m pytest companion/test_legacy_admin.py companion/test_app_server_start.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-07-02 | 07 | 5 | AUTH-02, AUTH-06 | stateless token API deleted, Section 1 tests rewritten, removal task recorded | integration | `./scripts/run-all-tests.sh` | ❌ W0 | ⬜ pending |
| 54-08-01 | 08 | 5 | AUTH-03 | route x role x owner matrix, probe family, completeness, session-state variants | integration | `server/.venv/bin/python -m pytest companion/test_access_matrix.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-08-02 | 08 | 5 | AUTH-06 | frame auth independent of Auth0 and sessions; credentials do not cross | integration | `server/.venv/bin/python -m pytest stub-server/test_auth_independence.py stub-server/test_phase47_freeze.py stub-server/test_fleet_auth.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-09-01 | 09 | 6 | AUTH-01 | Caddy query redaction on the companion block; env example placeholders | unit | `server/.venv/bin/python -m pytest deploy/tests/test_caddyfile.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-09-02 | 09 | 6 | AUTH-01, AUTH-02 | README owner steps, smoke test, rollback and removal notes | unit | `server/.venv/bin/python -m pytest deploy/tests/test_docs.py -x -q -p no:cacheprovider` | ❌ W0 | ⬜ pending |
| 54-09-03 | 09 | 6 | AUTH-01..03, AUTH-06 | handoff record, roadmap/state limited to Phase 54 lines, final full suite | integration | `./scripts/run-all-tests.sh` | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] `test-support/fake_auth0.py` + `test-support/test_fake_auth0.py`
- [ ] `companion/test_oidc.py`, `test_auth0_login.py`, `test_auth0_cookies.py`, `test_browser_auth0.py`, `test_legacy_admin.py`, `test_sessions_http.py`, `test_access_matrix.py`, `test_account_page.py`; `server/test_fleet_sessions.py`
- [ ] Rewrite Section 1 of `companion/test_companion_app_01.py`; update `test_route_table.py`

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-tenant smoke test: login works, wrong `code_verifier` rejected, sign-out returns to the allowed URL | AUTH-01 | Needs the owner's real Auth0 tenant; tests never leave loopback | Owner step after merge, documented in `deploy/README.md` |
| Caddy `/callback` query redaction | AUTH-01 | Caddy is not installed in CI | Validate `caddy validate` on the VPS |

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] No 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
