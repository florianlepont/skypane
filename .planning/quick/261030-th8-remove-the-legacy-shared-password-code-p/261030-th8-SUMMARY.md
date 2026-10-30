---
phase: quick-261030-th8
plan: 01
subsystem: companion-auth
tags: [auth0, session, cleanup, deploy-docs]
requires: [Auth0 sign-in live in production, SKYPANE_LEGACY_PASSWORD_LOGIN=0 in production]
provides:
  - Auth0 as the only companion sign-in
  - startup refusal on an absent or partial Auth0 configuration
  - inert, self-deleting legacy-admin session rows
affects: [companion, server/fleet_sessions.py, test-support, deploy docs]
key-files:
  modified:
    - companion/auth.py
    - companion/app.py
    - companion/login_page.py
    - companion/sign_in.py
    - companion/sign_in_config.py
    - companion/routes.py
    - server/fleet_sessions.py
    - test-support/companion_app_server.py
    - deploy/skypane.env.example
    - deploy/README.md
    - companion/testdata/render_baseline.json
  created:
    - companion/test_sign_in_config.py
    - companion/test_client_address.py
  deleted:
    - companion/static/login-card.js
    - companion/test_legacy_admin.py
    - companion/test_login_throttle.py
metrics:
  tasks: 3
  completed: 2026-10-30
---

# Quick 261030-th8: Remove the legacy shared-password code path

The SkyPane companion now signs people in through Auth0 only. The password form, `POST /login`, the password throttle, the `SKYPANE_LEGACY_PASSWORD_LOGIN` switch, the legacy-admin principal and the "Legacy access" pill are gone from production code.

## What changed

- **Production code** (commit 5ae4e0a8). `auth.py` lost the password helpers, the flag and `LoginThrottle`. It keeps the session and cookie helpers, `client_ip` and `login_throttle_key`, which the Auth0 start throttle still uses.
- `app.py` lost `_handle_login_post`, the legacy branches in `_resolve_principal` and `_apply_principal`, the legacy-session helpers and `LOGIN_THROTTLE`.
- `routes.py` no longer has the `POST /login` route.
- `login_page.py` is now: heading, optional notice toast, Auth0 link, and the defensive "not configured" notice.
- `validate_sign_in_config` requires a complete Auth0 configuration, and `main()` exits 1 before binding the port otherwise. Messages name variables only.
- `server/fleet_sessions.lookup_session` returns `None` and deletes any row whose principal is not `user`. A read-only store still just returns `None`. `PRINCIPAL_LEGACY_ADMIN` remains only as the persisted value old rows may carry. The schema and its CHECK are untouched and there is no migration.
- **Dead assets.** `login-card.js` is deleted, together with its route, shell script tag and `LOGIN_CARD_SCRIPT_SRC`. The login page now carries no script. The password, reveal and legacy CSS rules and the unused French strings are removed.
- **Test mechanism** (commit a6465d73). `companion_app_server.login(server)` now writes a local admin plus an opaque session row straight into `<state_dir>/fleet.db` and returns the cookie. Both server classes start with a complete placeholder Auth0 environment (`default_auth0_env`). `browser_login` installs the cookie for Playwright pages.
- **New tests and deleted tests.** `test_legacy_admin.py` and `test_login_throttle.py` are deleted. Their still-true behaviour moved to `test_sign_in_config.py` and `test_client_address.py`. `test_sign_in_config.py` covers:
  - startup without or with partial Auth0 settings;
  - retired variables tolerated;
  - legacy rows refused and deleted with and without the old flag;
  - `POST /login` not routed, with no cookie and no sessions row.
- **Deploy docs and tests** (commit 0c3f8945). The env example and README drop both variables and say Auth0 is required, and the README gets an Upgrade note. `run-local-verify.sh` exports placeholder Auth0 settings. Added tests: docs mention the retired variables only in the Upgrade note, and `activate.sh` ignores them. `activate.sh` and `provision.sh` needed no change: `activate.sh` parses only the keys it needs with anchored regexes and `provision.sh` never reads the file's contents.
- **Notes** (commit f2bb1b59). `54-LEGACY-ADMIN-REMOVAL.md` has a status paragraph (steps 2, 3, 4 and part of 6 done, step 5 deliberately not done). `54-HANDOFF.md` has one added line (D.5).

## Render baseline diff review

The baseline file lives at `companion/testdata/render_baseline.json`, not `companion/render_baseline.json` as the plan listed. I regenerated it once with `test-support/companion_render_snapshot.py --write` and compared it with the old file programmatically.

- Every authenticated page differs only by the removal of the `Legacy access` / `Ancien acces` pill (`span.banner__pill`). I verified by stripping the pill from the old body and getting an exact match.
- The plan expected the pill to be the only diff. It was not, and the other differences all follow directly from the removal:
  - the four `/login` page entries (en/fr, light/dark) now show the Auth0 card instead of the password form;
  - the `GET /static/login-card.js` entry is gone because the route is deleted;
  - the `POST /login` unauthenticated sample went from 401 to 404.

## Deviations from Plan

1. **[Rule 3 - Blocking] Browser and HTTP tests drove the password form.** Many browser tests logged in through `#password`, so they needed a central replacement. Added `browser_login` and a port-to-state-dir registry in `companion_app_server`.
2. **[Rule 3 - Blocking] Default Auth0 env.** The public URL must be https, so the default uses `https://frame.example.test` rather than the server's loopback address.
3. **Deleted password-form tests** in `test_browser_ux_02.py` (reveal toggle, lockout countdown), `test_browser_auth0.py` (legacy block) and `test_companion_app_04.py`. The login-card layout test was rewritten for the sign-in link.
4. **`server/test_fleet_sessions.py::test_legacy_admin_session`** asserted that legacy rows authenticate, which is the opposite of the new rule. I replaced it with a rejected-and-deleted test, in a separate commit after the full-suite run found it.
5. **Logout tests.** Sign-out of a user principal with Auth0 configured answers with the 200 interstitial rather than 303. I updated `test_sessions_http.py` and `test_companion_app_04b.py` and dropped the old legacy-logout test.
6. **Coverage floor.** No floor change was needed, and the full suite reported no coverage failure.

## Rollout caveat (verbatim from the plan)

The production /opt/skypane/skypane.env still holds SKYPANE_COMPANION_PASSWORD and SKYPANE_LEGACY_PASSWORD_LOGIN=0. After this change both are unknown variables and must be tolerated (ignored, never fatal) by the companion, activate.sh and provision.sh. The Auth0 variables (SKYPANE_AUTH0_DOMAIN / _CLIENT_ID / _CLIENT_SECRET, plus SKYPANE_COMPANION_PUBLIC_URL as already required) are already set in production because Auth0 is live; a deploy of this code without them would make the companion refuse to start.

## Verification

- ruff, mypy, the function-size gate and the comment-history guard all pass.
- Full suite `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`: 5627 passed, 8 skipped (all root-only), 1 failed. The failure was `server/test_fleet_sessions.py::test_legacy_admin_session` (item 4 above), now fixed and passing alone. I did not rerun the full suite after that one-test change.
- Non-root run as `nobody`: 346 passed.
- `stub-server/test_phase47_freeze.py`: 21 passed.
- `deploy/tests`: 235 passed, 1 skipped.
- `git diff` shows no change to `firmware`, `stub-server`, `server/fleet_db.py` or `measured_fields_freeze.json`.

## Known Stubs

None.

## Self-Check: PASSED

The commits 5ae4e0a8, a6465d73, 0c3f8945 and f2bb1b59 exist, plus the fleet_sessions test fix. The created and deleted files match the list above.
