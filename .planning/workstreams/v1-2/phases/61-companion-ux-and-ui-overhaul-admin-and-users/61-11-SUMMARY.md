---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 11
subsystem: companion
tags: [sign-in, auth0, messages, i18n]
requires: [61-05, 61-09]
provides:
  - unverified-email 403 page chosen from LoginOutcome.reason
  - reworded not-invited page with "Use another account" (prompt=login)
  - cancelled (provider_error) and throttled outcome pages
  - first-visit hint on the login card
  - welcome flash on the first identity link
key-files:
  created: [companion/test_sign_in_messages.py]
  modified: [companion/login_page.py, companion/sign_in.py, companion/oidc.py, companion/flash.py, companion/app.py, companion/i18n_fr/account.py, companion/i18n_fr/common.py, companion/test_auth0_login.py, companion/test_landing.py, companion/test_sign_in_surfaces.py, companion/test_browser_auth0.py, companion/testdata/render_baseline.json]
decisions:
  - "No pre-lookup email_verified check: sign_in maps outcome.reason ('unverified_email' -> own page, every other refusal -> same not-invited page); fleet_sessions untouched"
  - "First link derived from outcome.reason == 'linked'; no new storage"
  - "Three welcome tokens (welcome = frame Home, welcome_account, welcome_neutral) so the detail always fits the page; all whitelisted"
metrics:
  tasks: 3
  completed: 2026-11-03
---

# Phase 61 Plan 11: Sign-in messages Summary

Unverified-email refusals now show a "Confirm your email address" page picked from the sign-in outcome's reason, every sign-in failure ends with an action in EN and FR, and the first identity link lands with one welcome toast.

## Commits
- c596a7a feat(61-11): outcome pages, reason mapping, welcome flash, tests (tasks 1 and 2, entangled)
- e5279c6 test(61-11): browser flows (task 3)

## What changed
- `login_page`: `unverified_email_page`, reworded `not_invited_page` (primary "Use another account" to `/login/auth0?prompt=login`, link "Back to sign in"), tone-aware error table with new `provider_error` (info, 400) and `throttled` (warning, 429) kinds, first-visit hint on the plain card only.
- `sign_in`: `_resolve_invited` returns the whole `LoginOutcome`; `_refusal_page` maps `unverified_email` to its page and every other reason to the one not-invited page (reason still logged server side only). Only `prompt=login` is forwarded to the provider. `first_link` is `reason == "linked"`; the landing URL (and interstitial link) gets a whitelisted `flash=welcome*` token. Throttled start now answers 429 with its own page.
- `flash`: three welcome keys (info). Home reads them through page_context; Account and the console pages (Fleet) accept only these tokens.
- `oidc`: `KIND_PROVIDER_ERROR`, optional `prompt` on `authorize_url`.
- Which sign-ins are accepted is unchanged (`server/fleet_sessions.py` not touched). Test: a known linked identity with `email_verified` false still signs in.

## Deviations from Plan
- Browser tests went in `companion/test_browser_auth0.py` only; `companion/test_browser_ux_04.py` is a settings-page file with no sign-in content, so it was left alone.
- FR i18n strings for sign-in live in `companion/i18n_fr/account.py` (where the existing sign-in strings are) and the welcome strings in `common.py`.
- FR welcome detail uses a full stop instead of a semicolon ("...de votre cadre. Son point indique s'il est à jour.") because the FR catalog requires a no-break space before ";" and the toast guard compares the plain split text.
- Existing tests moved deliberately: `test_auth0_login.py` (landing target ignores the welcome token; the unverified identity left the "same 403" set because it now has its own page; throttled wording), `test_landing.py` (same token stripping), `test_sign_in_surfaces.py` (new wording), `companion/testdata/render_baseline.json` (login page hint line only: 4 lines).
- A `next` route or a user's deep link gets the neutral welcome line, not the Home line.
- No CSS change: the hint and help lines reuse `text-label section-caption`.

## Known Stubs
None.

## Self-Check: PASSED
