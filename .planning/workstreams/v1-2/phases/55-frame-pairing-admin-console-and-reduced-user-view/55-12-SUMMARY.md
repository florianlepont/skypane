---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 12
subsystem: companion-console
tags: [users, invite, roles, disable, unlink, guards, audit]
requires: [55-02, 55-09, 55-11]
provides:
  - companion/pages/users_page.py (UserRow, UsersView, render)
  - companion/console_users.py (GET /users; POST invite, role, disable, enable, unlink)
  - companion/i18n_fr/admin_users.py
  - audit keys user.invite, user.role, user.disable, user.enable, user.unlink (numeric target_id)
affects: [55-13, 55-14]
tech-stack:
  added: []
  patterns:
    - one BEGIN IMMEDIATE transaction per action holding the guarded write and its audit row; a guard refusal rolls back and writes a standalone denied row
key-files:
  created:
    - companion/pages/users_page.py
    - companion/i18n_fr/admin_users.py
    - companion/test_console_users.py
  modified:
    - companion/console_users.py
    - test-support/matrix_rows_users.py
    - test-support/companion_render_snapshot.py
    - companion/test_route_table.py
    - companion/test_i18n.py
    - companion/test_console_shell.py
    - companion/test_user_nav.py
    - companion/testdata/render_baseline.json
    - companion/testdata/update_page_one_type_golden.json
key-decisions:
  - "Saving an unchanged role, or enabling an enabled user, is a success flash with no change and no audit row."
  - "Unlink is done inline in the handler (clear iss/sub, delete sessions) because fleet_sessions.unlink_identity opens its own transaction and could not share the audit row's."
  - "The own row of the only active administrator shows both lines (This is you. and the last-administrator line)."
requirements-completed: [AUTH-05]
duration: ~2h
completed: 2026-10-31
---

# Phase 55 Plan 12: Users page and actions Summary

Admins manage users from `/users`: invite (email and role, no mail sent), change role, disable and enable, unlink identity, with the last-active-admin and self-action guards enforced inside one transaction per action and every action audited.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 and 2 (code) | 0d4aff3 | `users_page`, `console_users` (GET plus five CSRF POST routes), French strings, matrix rows, route-table sample, render baselines, shell and nav test updates |
| 1 and 2 (tests) | 94c4c3a | 51 HTTP tests in `companion/test_console_users.py` |

The page and the handlers were written together, so the code for both tasks is one commit (same approach as plans 05 and 10); the tests are their own commit.

## Verification

- Full non-browser suite (`companion server test-support scripts stub-server -m "not browser"`): 6194 passed, 7 skipped (the root-permission skips). An earlier run before the shell, nav and golden updates had 5 expected failures (`test_console_shell` x3, `test_user_nav`, `test_update_page` golden), all fixed.
- Browser suite (`companion -m browser`, chromium symlink dir in the scratchpad): 567 passed (no Users-specific browser tests were added; the plan has none).
- As `nobody` (the five brief files, the suite guards and `test_console_users.py`): 438 passed, 4 skipped (the Chromium 1243/1248 launch skips of the sandbox; no `requires_non_root` skips).
- `ruff check .`, `mypy` (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (814 functions): clean.
- Targeted: `test_console_users`, `test_access_matrix`, `test_i18n`, `test_route_table`, `test_render_baseline`, `test_update_page`, `test_console_shell`, `test_user_nav`, `server/test_fleet_schema3`: 1164 passed.

## Behaviour proven by the tests

- Page: every user with email, signed-in line, role badge, status (Active, Disabled, Invited), frame count; card stack and table; own row has no Disable or demote and shows "This is you."; the only active admin shows the last-administrator line; Enable only on disabled rows, Disable only on active ones, Unlink only with a linked identity; every form has the CSRF field and an `/users/...` path; no `<dialog>`, no `confirm(`; no issuer, subject or session token in the markup; the one accent primary is "Send invitation"; user principal 404, anonymous redirect.
- Invite: creates an active unlinked user and one `user.invite` row; invalid email, unknown role and a case-insensitive duplicate are field errors that change nothing; through the fake Auth0 the invited email signs in and links, a stranger does not.
- Role: promotion without confirm, demotion with another admin present, effective on the demoted admin's next request; audit detail holds only `from` and `to`; unchanged or unknown role changes nothing.
- Disable and enable: sessions deleted in the same transaction, next request refused; enable restores sign-in; both audited.
- Guards: self demote or disable, and (via a stub handler, since no HTTP actor can reach it) the last active admin demoted or disabled by another actor, change nothing, show "Action refused" with the guard-specific detail, and write a denied audit row. Two threads over real HTTP, each admin acting on the other (demote, then disable): exactly one change, one active admin left.
- Unlink: clears iss/sub and sessions, next Auth0 sign-in re-links, audited; a user with no identity gets an error flash and no audit row.
- Ids: non-digit, over-long, negative, unknown and `invite` middles touch nothing; non-admin 404, anonymous redirect, missing CSRF 403 for all six POST routes, with no state or audit change.

## Deviations from Plan

1. **[Rule 3 - Blocking] Existing tests described the pre-Users state.** The Users route now exists, so `test_console_shell.py` (aggregator, sub-nav-without-pages and group tests) and `test_user_nav.py` (sidebar group now Fleet, Users, Audit log, Releases) were updated; `test_i18n.py` allowlist gained `admin_users.actions` (French "Actions" equals English). The brief expected these to need no edits; they did.
2. **[Rule 3] Baselines regenerated.** `render_baseline.json`: 44 pages gain the Users sidebar link (and `/update` pages the Users chip), checked by script that every one of the 44 differences is exactly that inserted link or chip; six new unauthenticated entries (`GET /users` and the five POSTs). `update_page_one_type_golden.json`: 12 of 14 pages gain the Users chip, checked by script that nothing else changed. `companion_render_snapshot.py` gained the paths.
3. **Last-admin guard at HTTP level.** An active administrator acting on the only active administrator is always that administrator, so the self guard fires first over HTTP; the last-admin refusal is reachable only by a race (covered by the two-thread tests) and is covered deterministically with a small stub handler calling the real handlers against a real database.
4. **Unlink inlined.** See key decisions; same effect as the fleet CLI's `users unlink-identity` and `fleet_sessions.unlink_identity`.

## Notes for owner and plan 13/14

- "Signed in" shows the newest live session time. Sessions are deleted on disable and unlink and pruned on expiry, so such users read "Never signed in" although they have signed in before. The spec offers only the two texts and no last-login column exists.
- Unlinking your own identity is allowed (you are signed out and re-linked at next sign-in).
- The invite pre-registers the email only; Auth0 sign-ups must stay disabled (owner checklist), otherwise nothing else prevents an uninvited sign-in beyond the existing invite-only check.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (T-55-12-01 to -06 covered by `test_console_users.py`).

## Self-Check: PASSED

Files present: companion/pages/users_page.py, companion/console_users.py, companion/i18n_fr/admin_users.py, companion/test_console_users.py. Commits 0d4aff3 and 94c4c3a exist.
