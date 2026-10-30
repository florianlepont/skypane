# Phase 54 handoff

Phase 54 delivers sign-in, local roles, sessions and the default-deny gate
without any production deploy. This document records what must still be done
after the device-scoped routes exist, the owner's go-live checklist, and the
points the owner needs to know.

Related: [legacy-admin removal task](54-LEGACY-ADMIN-REMOVAL.md),
[`deploy/README.md`](../../../../../deploy/README.md) section "Sign-in (Auth0)",
`companion/test_access_matrix.py`.

## A. Completed after the device-scoped routes exist (Phase 51)

- Every real `/d/<id>/...` route is registered with `Access(USER, "device")`.
  It receives an already-authorized device id from `access.authorized_device_id`
  and never queries `devices` directly.
- Each such route, and each per-device derived resource (images, history,
  battery charts, firmware status), gets one row in the expectation table of
  `companion/test_access_matrix.py`. The completeness test fails until it does.
- The probe family (`/d/<id>/_probe`) stays a test-only harness. Remove it or
  keep it as a canary once real rows exist.
- Re-run the HTTP layer of the matrix with the real handlers for those routes.
- The user's Account page "Frames" empty state is replaced by the reduced view
  in the pairing/admin phase.
- Per-session CSRF tokens are revisited before destructive admin actions land.
- Co-management (see section D) extends `access.authorized_device_id`, which
  takes the owner as input.

## B. Owner go-live checklist (nothing is deployed by this phase)

1. Configure the Auth0 tenant: Regular Web Application, Allowed Callback URL
   `https://<companion host>/callback`, Allowed Logout URL
   `https://<companion host>/login`, sign-ups disabled, no social connections.
2. Set `SKYPANE_AUTH0_DOMAIN`, `SKYPANE_AUTH0_CLIENT_ID` and
   `SKYPANE_AUTH0_CLIENT_SECRET` in `skypane.env` and restart the companion.
3. Create the first admin with `fleet_cli users add` and sign in as that user.
4. Run the real-tenant smoke test: sign in, a wrong `code_verifier` is
   rejected, sign out returns to the allowed logout URL and the next sign-in
   prompts for credentials.
5. Run `caddy validate` on the VPS (done by `activate.sh`) and check that a
   real `/callback` line in `journalctl -u caddy` shows no query values. The
   redaction is asserted as text only in the repository tests.
6. Confirm in the deploy dry-run output that `fleet.db` upgraded from schema 1
   to 2, and that Health shows no fleet fault once the new release is live.
7. Keep rollback in mind: the previous release's byos refuses a schema 2 file.
   The frame keeps working from the legacy files, and Health shows a fleet
   fault until the new release is live again.
8. Set `SKYPANE_LEGACY_PASSWORD_LOGIN=0` and execute the removal task in
   `54-LEGACY-ADMIN-REMOVAL.md`, stamping the "remove by" date.

## C. Surfaced to the owner

- Legacy-admin removal is event-driven (as soon as Auth0 sign-in is in
  production), not calendar-dated as the roadmap wording says. The owner
  stamps a date at go-live.
- Role denial returns 404, like an unknown path.
- There is no per-session CSRF token in this phase.
- A `users unlink-identity` CLI verb was added for people who lost their
  Auth0 account.
- The redirect and `returnTo` URLs derive from `SKYPANE_COMPANION_HOST`
  (or `SKYPANE_COMPANION_PUBLIC_URL`), never from the Host header.
- Backups now contain the `sessions` table (hashes only); a restore brings
  back unexpired sessions.

## D. Owner notes

1. **Removal trigger.** The roadmap says "dated"; the real trigger is the
   Auth0 go-live. The owner stamps the date then.
2. **Co-management.** A device has exactly one owner and a user can own
   several devices. On 2026-10-30 the owner asked for co-management: an owner
   plus co-managers, where both an admin and the owner can add a co-manager.
   This is not in Phase 54 and is being added as a separate new phase. The
   ownership gate `access.authorized_device_id` takes the owner as input, so
   co-management extends that one function.
3. **Co-managing before Phases 51 and 55.** Until those phases land, a
   `user`-role sign-in only sees the Account page. To co-manage today, the
   owner's friend must be created as `admin` with the fleet CLI. Caveat: an
   admin sees the whole fleet.
4. **Playwright in this sandbox.** The repo's Playwright expects
   `chromium_headless_shell-1248` while 1243 is installed here; a symlink
   outside the repo fixed it locally. CI is unaffected.
