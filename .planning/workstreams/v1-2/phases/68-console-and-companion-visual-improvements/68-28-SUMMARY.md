---
phase: 68-console-and-companion-visual-improvements
plan: 28
subsystem: companion
tags: [users, dialogs, auth0, invitation, i18n, modal]
requirements: [CON-01]
key-files:
  created:
    - companion/test_console_users_invitation.py
    - companion/test_browser_users_invitation.py
  modified:
    - companion/auth0_management.py
    - companion/console_users.py
    - companion/pages/users_page.py
    - companion/ui_modal.py
    - companion/ui_components.py
    - companion/app.py
    - companion/static/modal.js
    - companion/static/copy-button.js
    - companion/static/style.css
    - companion/static/style-admin.css
    - companion/i18n_fr/admin_users.py
    - companion/i18n_fr/admin_lifecycle.py
    - companion/pages/audit_page.py
    - deploy/skypane.env.example
    - deploy/README.md
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-21
---

# Phase 68 Plan 28: Users dialogs and automatic Auth0 invitation Summary

The Users dialogs are built from the owner-approved mock `68-MOCKUP-users.html`: a short invite sheet (labelled address, one Administrator checkbox, Cancel and Invite) that stays above the phone keyboard, even-margin role and delete confirmations, and an "Invitation ready" dialog that shows an Auth0 password-change link once (never stored, logged, flashed or put in an address). A failure keeps the local invite and offers a retry through the same route; a second invite of a person who has not signed in yet renews the link for 24 hours instead of 5 days.

## Commits

- d6e6d917 feat(68-28): Auth0 invitation client takes the link lifetime, validates the ticket URL and connection id
- 5788ff8f feat(68-28): Users dialogs and automatic Auth0 invitation
- 11834176 fix(68-28): keep the shared sprite and golden shell hashes, pill via catalogue helper
- 211f84e0 chore(68-28): regenerate the render baseline (stylesheet version hashes only)
- the SUMMARY commit (this file), last commit of the branch

Plan tasks 1 and 2 are in one commit (5788ff8f): the invite form's role field (a checkbox now) and `handle_invite` are one contract, so splitting them would leave a broken intermediate commit. Task 3 is the baseline commit plus the gates run below.

## What changed

Auth0 client (`companion/auth0_management.py`), owner decisions 1 to 6:

- `create_invitation(environ, email, result_url, ttl_sec, post)`: the caller chooses the lifetime (`FIRST_TICKET_TTL_SECONDS` 432000 for a new person, `RENEWED_TICKET_TTL_SECONDS` 86400 for a renewal; anything else but a positive int is refused with `bad_ttl`).
- `SKYPANE_AUTH0_DB_CONNECTION_ID` shape is checked (`con_` + 16 letters or digits). Missing gives `user_exists_connection_id_missing`, malformed gives `connection_id_invalid`; both fail closed before any ticket call.
- The address is lowercased before every call. The returned ticket URL is shown only when it is https (plain http only for the loopback test provider behind the existing test flag), has no credentials, whitespace or control characters, is at most 2048 characters and its host (and port) is the configured Auth0 domain or `SKYPANE_AUTH0_CUSTOM_DOMAIN`; otherwise the result is `ticket_url_rejected` and the text is never returned.
- HTTP 429 at any step is `rate_limited`; 400/401/403 stay `token_failed`, `create_failed`, `ticket_failed` (audit only).
- The create-user payload is exactly `email, connection, email_verified=false, verify_email=false, password`; the ticket payload is `user_id` or `email + connection_id`, `result_url`, `ttl_sec`, `mark_email_as_verified`. Both sets are pinned by tests. Only the scopes `create:users` and `create:user_tickets` are used.

Handler (`companion/console_users.py`):

- `POST /users/invite` (same route, no new route): validate, local `add_user` + `user.invite` audit row in one transaction (unchanged), then the Auth0 call, then a second audit row `user.invitation` with outcome `ok` or `failed` and a detail of `renewed`, `ttl_sec` or the reason code (never the link).
- An unticked Administrator box posts no role, which means a plain user. A forged role value is still a field error.
- A duplicate address of someone who has not signed in yet (enabled, no identity, no session) is a renewal: same route, role untouched, link valid 24 hours. A signed-in or disabled person keeps the existing "already invited" refusal.
- Success: HTTP 200 in the POST response (no redirect, no flash), `Cache-Control: no-store`, `Pragma: no-cache`, `Referrer-Policy: no-referrer`. The response is sent by `_send_one_time_html`; `companion/app.py` gained one line (a `referrer_policy` class attribute that `_send_hardening_headers` reads), so the default stays `same-origin` for every other page.
- Failure: the person stays invited, the dialog says so and why in one generic sentence per kind (busy: "Try again in a moment"; not set up; connection id missing, naming `SKYPANE_AUTH0_DB_CONNECTION_ID`; generic), with a Try again button for busy and generic and none where only a server setting can fix it.
- Result URL and the "open this address" text come from the validated Host header (`_app_url`, unchanged); a hostile Host gives no address and no call.

Dialogs (`ui_modal.py`, `users_page.py`, `style.css`, `style-admin.css`, `modal.js`, `copy-button.js`):

- `ui_modal.dialog_html(variant="compact"|"compact-top")` adds a modifier class (`modal--compact`, `modal--top`) to those dialogs only: title alone in the head, 14 px between every block, two buttons in one row (dismiss first), the phone sheet with a 44 px grabber. Fleet, quiet hours and the leave dialog keep their computed spacing (tested).
- `ui_modal.result_dialog_html` is the open outcome dialog; `once` makes `modal.js` remove it from the page when closed and `data-modal-return` puts `/users` in the address bar, so a reload never posts again.
- `modal.js`: `visualViewport` resize and scroll set `--keyboard-inset` on open compact sheets (gated at 80 px so browser chrome is not mistaken for a keyboard) and a focused field is scrolled into view. 697 lines.
- `copy-button.js`: the fallback textarea joins the open dialog (the rest of the page is inert under a modal).
- Invite dialog: no explanatory paragraph, the labelled address field first, an Administrator checkbox (unchecked) whose native input covers the 48 px line (hit area 44 px or more), "Cancel" and "Invite". The role-change and delete confirmations drop the subtitle and the close cross and use the mock sentence.
- Row menu: "Send a new invitation" (paper-plane glyph, drawn inline) for a person who has not signed in; Reset sign-in for one who has; Delete user. The copy-invitation column (button, column, CSS) is gone. The signed-in administrator's role is calm grey regular text.
- Status badges are built by `ui_components.pill_html` (new `attrs` argument, same markup).
- French strings in `i18n_fr/admin_users.py` and `admin_lifecycle.py`; orphan ids removed (the manual copy message, the purpose paragraph, the owner-rule sentence, the invited flash); `test_i18n.py` green.

Deployment (`deploy/skypane.env.example`, `deploy/README.md`, `deploy/tests/test_env_example_mgmt.py`): `SKYPANE_AUTH0_DB_CONNECTION_ID` is documented as required for a new invitation to a person who already has an Auth0 account (what it is, where to find it: Authentication > Database > the connection; placeholder only), and the optional `SKYPANE_AUTH0_CUSTOM_DOMAIN`.

## Fidelity check (mock vs built)

Mock captures (each mock's own box, 390 px phone and 1440 px desktop, EN and FR, light and dark): `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p28/mock/` (36 images, `<state>-<phone|desktop>-<lang>-<theme>.png`).
Built captures (full page, plus a `-view` viewport image for every dialog state, 320 / 390 / 1440, EN and FR, light and dark): `.../scratchpad/p28/built/` (184 images). States: `users`, `invite`, `menu`, `role-confirm`, `delete-confirm`, `ready` (link shown once), `failed` (with retry), `invite-keyboard` (phone, visual viewport at 60%).
The dialogs were compared by eye against the mock at 390 and 1440 (EN light first, then the rest) and their gaps are asserted by browser tests (14 px between title, content and buttons, at 360 and 1280, EN and FR). The mock has no 320 px frame, no failure dialog and no keyboard state.

## Design-system divergences

The `sketch-findings-skypane` skill could not be loaded (no Skill tool in this environment); I read `.claude/skills/sketch-findings-skypane/SKILL.md` and `references/components.md` directly and used the mock's tokens and the existing CSS tokens.

Dialogs, built vs the mock:

1. Dialog radius is the token `--radius-card` (22 px), the mock draws 24 px; the dialog title is the shared `text-heading` (22 px, 600) where the mock draws 20 px bold.
2. The Copy button is 44 px tall (the 44 px target rule and `_assert_hit_target`), the mock draws 40 px; the link strip is therefore 56 px tall instead of 54.
3. The solid "Delete user" button uses `--color-on-accent` for its text (white in light, near-black in dark) because white on the dark theme's pink is under 4.5:1; the mock draws white in both. The solid fill itself follows the mock (the design system's `btn--danger` is an outline); it applies to compact dialogs only.
4. The hint under the link is longer than the mock's ("It is shown only once. They choose their password and sign in."): owner decision 4 adds that the link is a secret, how long it lasts and the address to open after choosing a password. It does not say the link is single-use.
5. The copied message is the whole invitation (link, validity, address to open, sign-in e-mail), not the bare link, so the administrator can paste one message. The strip shows the real link, cut with an ellipsis like the mock.
6. The email field shows its focus ring when the dialog opens (the first field takes focus so the phone keyboard opens, as the plan asks); the mock draws no focus. Done in the result dialog is the initial focus (Enter never repeats an action).
7. The failure dialog and the keyboard state are not drawn in the mock: the failure dialog follows the "Invitation ready" pattern (title, one paragraph, Done and Try again).
8. The 8px-grid rule is bypassed on purpose in the compact block (14 px gaps, 20 px padding, 10 px button gap, 26 px box, 33 px sheet top) to match the mock's literal values.
9. The Administrator checkbox is a custom-drawn 26 px box with a transparent native input over the whole 48 px line (a plain native checkbox is under the 44 px hit-area test).
10. No close cross in the compact dialogs (as drawn); Cancel, Esc and the backdrop dismiss.
11. Reset sign-in is not shown for a person who has never signed in (the mock draws it on those rows); it would only answer "nothing to unlink". Delete and Send a new invitation are shown.
12. The Delete confirmation lost its two extra sentences (sessions closed, audit log keeps the address, the owner-of-a-frame rule) as the mock's single sentence says; an owner of a frame is still refused, with the existing error toast.
13. French wording from the mock: "Garder utilisateur" (was "Laisser utilisateur") and the delete sentence "...Cette action est définitive."; the demote confirmation is not drawn, its keep label became "Garder administrateur" to match.

Page-level differences I found while comparing and did not change (outside the dialogs this plan owns; need an owner decision):

14. Phone header: the mock has a small square "+" button beside the title; the built page keeps the shared full-width "+ Invite a user" bar.
15. Phone list: the mock is one card with a divider per person showing "Role · frames" as text and no role control; the built page has one card per person with a role select, the switch, frames and last sign-in.
16. Desktop role select: the mock draws a compact bordered chip with a chevron; the built page keeps the grey native select.
17. The mock's sidebar order and items ("My frames / Console", no System item) and its sample times ("just now") differ from the real shell.

## Deviations from plan

- `companion/app.py` changed by one line (a `referrer_policy` class attribute, now 1497 lines of 1500), although the plan said no `app.py` change: the one-time response must send `Referrer-Policy: no-referrer` and the hardening headers are sent from there.
- A new `user.invitation` audit action with its label (EN and FR) records the Auth0 outcome in a second row; the plan's wording allowed one row, but the first row is written before the call.
- `FLASH_INVITED` and its strings were removed: a successful invite shows the dialog, a failed one the failure dialog, so the flash had no use.
- New optional `SKYPANE_AUTH0_CUSTOM_DOMAIN` (owner decision 3: "or a custom domain configured for it").
- New test files (`test_console_users_invitation.py`, `test_browser_users_invitation.py`) and a shared `invitation_auth0` fixture in `companion/conftest.py`; the plan listed edits to existing files only.
- A first version added an `icon-send` sprite symbol; it changed every page's golden shell hash (`test_sign_in_surfaces`), so it was replaced by an inline SVG (the same reason plan 27 used one). `ui_components.pill_html` gained an `attrs` argument for the D-14 pill replacement.
- Tests that used the invite flash as a toast source (`test_browser_motion_sheets`, `test_browser_one_toast_one_sheet`) now use a confirmed role change; `test_browser_fleet_users_fixes` waits out the first toast before the second switch click (the shorter cards, without the copy row, put the last card under the docked toast on a short page).
- Open pull requests checked: #503 (airlines editor; it also regenerates `render_baseline.json`, so whichever merges second regenerates) and dependabot #481 (`server/requirements-dev.*`) touch none of the Users files. Phase 64's earlier edits to `ui_modal.py` and `style-admin.css` were merged and are in the base.

## Tests

- New: `companion/test_console_users_invitation.py` (22 tests: first invite, link shown once and in no database table, file, log, header, cookie or later page; planted secrets in no output; lowercase address and 5 days; renewal for 24 hours and role untouched; refusals for signed-in and disabled; failure keeps the invite and offers retry; 429 "try again in a moment"; 400/401/403 generic with the code only in the audit; not configured; missing and malformed connection id; foreign ticket host never shown; hostile Host header) and `companion/test_browser_users_invitation.py` (38 tests: keyboard-safe sheet with an emulated keyboard, short viewport, gaps, hit targets, 320/390/1440, EN/FR, light/dark, copy, selection fallback, Done removes the link, no-script card, retry, contrast, other dialogs unchanged).
- Extended: `test_auth0_management.py` (72 tests: lifetime parameter, 429, ticket-URL validation, connection-id shape, exact payload fields, custom domain), `test_ui_modal.py`, `test_csrf.py` (tokenless and cross-origin invite creates nothing and calls nothing), `deploy/tests/test_env_example_mgmt.py`.
- Updated for the new dialogs: `test_console_users.py`, the users/fleet/motion/toast/console/overhaul browser tests, `test_browser_delete_user_remove_frame.py`.
- Gates: ruff clean, mypy clean (47 files), `check_function_size.py check --max 80 server stub-server` clean, `check_comment_history.py check` exit 0, `companion/app.py` 1497 lines, largest script `place-map.js` 1227 (`modal.js` 697), no orphan i18n ids, `test_phase47_freeze.py` and the access tests (`test_access.py`, `test_access_matrix.py`) green.
- Render baseline: regenerated once (`PYTHONPATH=. test-support/companion_render_snapshot.py --write`); 68 captures changed, every one only in the `?v=` stylesheet hash (checked field by field); no markup changed in any golden page.
- Final run on the committed tree (`SKYPANE_REQUIRE_BROWSER=1`, `scripts/run-all-tests.sh` with `SKYPANE_TEST_GROUP=core`, 4 shards): 2402 passed 4 skipped, 2650 passed, 4573 passed, 2748 passed 3 skipped = 12373 passed, 0 failed (the 7 skips are tests that need a non-root user). Then 30 browser files touching users, dialogs, modals, sheets, toasts, motion, console, overhaul and French fit (`test_browser_*users*`, `*dialog*`, `*modal*`, `*motion*`, `*sheet*`, `*toast*`, `*overhaul*`, `*console*`, `*french_fit*`, `*delete_user*`, `*leave*`; `-n 4`): 1347 passed, 0 failed. The earlier full run (core plus all six browser shards) had failed in 5 places, all fixed before the final run: a flaky assertion of mine (a CSRF token containing "403"), the golden shell hashes (the sprite symbol, removed), the Components catalogue test (new helper exempted), the delete confirmation test (old sentence) and the baseline (regenerated).

## Owner checklist for the first real invitation

1. Auth0 scopes: the machine-to-machine application is authorised for the Management API with exactly `create:users` and `create:user_tickets` (nothing else; the client asks for no more).
2. Server environment (`/opt/skypane/skypane.env`, never committed): `SKYPANE_AUTH0_MGMT_CLIENT_ID`, `SKYPANE_AUTH0_MGMT_CLIENT_SECRET`, `SKYPANE_AUTH0_DB_CONNECTION` (the connection name), `SKYPANE_AUTH0_DB_CONNECTION_ID` (`con_` + 16 letters or digits; Authentication > Database > the connection), and `SKYPANE_AUTH0_CUSTOM_DOMAIN` only if the tenant uses a custom domain (the link is shown only on the tenant or that domain). Then restart `skypane-companion`.
3. URL allowed: the invitation sends the SkyPane address (the request's validated host) as `result_url`. Check in the Auth0 application settings that this address is accepted (for example in Allowed Callback URLs); if Auth0 refuses it the dialog shows the generic failure and the audit row says `ticket_failed`. Auth0 only honours the redirect after the password is set on classic Universal Login, so the dialog also tells you to give the person the address to open.
4. At the first invitation, with an address you own: the dialog shows a link on your tenant domain and "it expires in 5 days"; do not open it as the administrator test unless you mean to use it; Copy gives one message with the link and the address; Done removes the link, and reloading `/users` shows nothing; the audit log shows "User invited" and "Invitation link". Open the link in a private window, choose a password, check where Auth0 lands you, then sign in at the SkyPane address: the row turns Active. Then use the row menu "Send a new invitation" on a second never-signed-in test person: the text says 24 hours and a new link works (this is the path that needs the connection id). Unplug the connection id once to see the message.

## Owner decisions needed

1. Page-level differences 14 to 17 above (phone header button, phone card layout without a role control, role select style, sidebar): build them or keep the current page?
2. Reset sign-in on a never-signed-in row (the mock draws it, I left it out as it can only fail): keep it out?
3. The failure dialog wording and layout (not drawn in the mock), and whether the not-set-up and connection-id messages may name `SKYPANE_AUTH0_DB_CONNECTION_ID`.
4. The keyboard lift applies to the compact dialogs only; extend it to every bottom sheet?
5. Retry after a failed first attempt is a renewal (24 hours): the local row exists, so the page cannot tell whether Auth0 created the account. Acceptable?
6. Optional `SKYPANE_AUTH0_CUSTOM_DOMAIN`: keep, or require the tenant domain only?
7. Dialog radius and title size follow the tokens (22 px, 22 px/600) instead of the mock's 24 px and 20 px bold: accept or match the mock literally?
