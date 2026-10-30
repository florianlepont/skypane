# Legacy shared-password fallback: removal task

## Trigger

Event-driven, not calendar-driven: start as soon as Auth0 sign-in is in
production and the administrator has signed in through it successfully. The
owner stamps a "remove by" date at go-live (this refines the roadmap's
"dated" wording). Remove by: ______ (to be filled at go-live).

Status 2026-10-30: the trigger is reached (Auth0 sign-in works in production and the administrator signed in through it). Step 1 is done in production: the owner set `SKYPANE_LEGACY_PASSWORD_LOGIN=0` and restarted the companion the same day; the login page no longer shows the shared-password block. The code removal (steps 2 to 5) is not done yet. To re-enable the fallback in an emergency, set the flag to `1` in `/opt/skypane/skypane.env` and restart `skypane-companion`.

Status 2026-10-30 (code removal): steps 2, 3 and 4 are done, plus the parts of step 6 this change covered: `companion/test_legacy_admin.py` is deleted, the legacy-access pill is gone from the shell, and the render baseline was regenerated and reviewed (besides the pill, the only differences are the `/login` page now showing the Auth0 card, the removed `/static/login-card.js` route and `POST /login` answering 404). Auth0 is now the only sign-in, and `main()` refuses to start without a complete Auth0 configuration. Step 5 is deliberately NOT done: the `sessions` schema and its CHECK (`'user'`, `'legacy-admin'`) are left untouched so a rollback or an old row is harmless. Old legacy rows are treated as invalid and deleted on lookup, and `PRINCIPAL_LEGACY_ADMIN` survives only as the persisted value. Rollout caveat: production `/opt/skypane/skypane.env` still holds `SKYPANE_COMPANION_PASSWORD` and `SKYPANE_LEGACY_PASSWORD_LOGIN=0`; both are now ignored (never fatal) by the companion, `activate.sh` and `provision.sh`.

## Steps

1. Set `SKYPANE_LEGACY_PASSWORD_LOGIN=0` in the production environment,
   restart the companion, and verify sign-in through Auth0 still works and
   `POST /login` answers 403 "Password sign-in is turned off". Existing
   legacy sessions are refused on their next request.
2. Delete the password form path: `_handle_login_post`, the legacy block in
   `companion/login_page.py`, `LOGIN_THROTTLE`, and `auth.password_ok`,
   `auth.configured_password`, `auth.LoginThrottle` and its helpers.
3. Delete the `configured_password` use in `validate_sign_in_config` and the
   flag handling (`auth.legacy_login_enabled`).
4. Remove `SKYPANE_COMPANION_PASSWORD` and `SKYPANE_LEGACY_PASSWORD_LOGIN`
   from `deploy/skypane.env.example` and `deploy/README.md`.
5. Remove the legacy-admin principal kind (`fleet_sessions.PRINCIPAL_LEGACY_ADMIN`,
   `access` handling) and the legacy branch of the `sessions` CHECK through a
   new expand-only migration.
6. Delete `companion/test_legacy_admin.py`, the legacy-access pill in the
   shell, and the render baseline entries that carry it; regenerate the
   baseline and review the diff.
