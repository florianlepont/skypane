# Legacy shared-password fallback: removal task

## Trigger

Event-driven, not calendar-driven: start as soon as Auth0 sign-in is in
production and the administrator has signed in through it successfully. The
owner stamps a "remove by" date at go-live (this refines the roadmap's
"dated" wording). Remove by: ______ (to be filled at go-live).

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
