---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 08
subsystem: companion
tags: [users, dialogs, entity-list, console]
requires: [61-02, 61-03, 61-04]
provides: [Users page as an entity list with Invite and Manage user dialogs]
key-files:
  created:
    - companion/test_browser_users_page.py
  modified:
    - companion/pages/users_page.py
    - companion/console_users.py
    - companion/ui_modal.py
    - companion/app.py
    - companion/console_pairing.py
    - companion/static/style.css
    - companion/i18n_fr/admin_users.py
    - companion/test_console_users.py
    - companion/test_browser_console.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 08: Users list and dialogs Summary

`/users` is one `ul.entity-list` (sans email that wraps, "Role · n frames" plus "· You", Invited only for never-signed-in accounts, Disabled pill, a 44px "Manage user" button). "+ Invite a user" opens a dialog (role defaults to User, submit "Invite user"); "Manage user" opens one dialog per user with Role, Access and Sign-in forms posting to the unchanged routes.

## Commit

- fab623a: page, handlers, FR strings, CSS, modal helper, updated unit tests and new browser flows (single commit; the tasks only stay green together).

## What changed

- `users_page.py` rewritten: list rows, invite dialog (`dlg-invite-user`, field errors through `ui_modal.field_error_html`), per-user Manage dialog (`dlg-user-<id>`). Guard sentences ("This is you.", "The last active administrator cannot be changed.") replace the role and disable controls inside the dialog. Unlink appears only for linked identities; Enable replaces Disable for disabled users. Disable and Unlink buttons are destructive.
- `console_users.py`: header action passed to the page shell; a refused invite re-renders `/users` at 400 with the dialog open (`open_invite_dialog`). Success toast now "Invited" / "Tell {email} to sign in with this address." (FR "Invitation enregistrée" / "Dites à {email} de se connecter avec cette adresse.").
- `ui_modal.py`: `sections_dialog_html` (a dialog of several independent forms, since `dialog_html` wraps exactly one form) and an `aria_label` option on `trigger_html`.
- `style.css`: `a.entity-row__button`, `.modal__section`.
- FR catalog: new keys added, orphaned table/disclosure keys removed.
- Owner ledger rows 4 and 11: defaults applied (one dialog per user, "Invite user").

## Deviations from Plan

1. **[Rule 1 - Bug] Header action was translated before the request language was known.** `_console_page` received an already-built string, so `/users` and `/fleet` showed the English button in French. `action_html` may now be a callable resolved after `page_context()`; both Users and Fleet pass the callable.
2. **[Rule 3] Files outside the frontmatter:** `ui_modal.py` (multi-form dialog helper; needed because the Manage dialog has three forms), `app.py`, `console_pairing.py` (item 1), `style.css`, `test_browser_console.py` (touch-target and no-script steps, and the "dialogs only where planned" guard now allows `/users`).
3. **Refused user actions are not re-rendered.** Role/disable/enable/unlink refusals keep their existing redirect-with-flash behaviour (status codes unchanged, as the plan requires); only invite re-renders with its dialog open.
4. Task commits merged into one commit (code, tests and strings depend on each other).
5. Purpose line kept as the existing string.

## Gates

ruff, mypy (28 files), check_comment_history, check_function_size (922 functions), freeze test (21 passed). Full companion + test-support + freeze suite: 5855 passed, 3 skipped (root-permission tests). Browser tests (users page + console): 41 passed, none skipped. `render_baseline.json` regenerated: no change.

## Known Stubs

None.

## Threat Flags

None. ADMIN_ONLY rows, csrf and last-admin/self guards are untouched and their tests pass; emails are escaped (test with a hostile address).

## Self-Check: PASSED
