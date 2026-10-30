---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 06
subsystem: auth
tags: [account, user-shell, default-deny, playwright, auth0, companion]
requires:
  - phase: 54-03
    provides: account_page markup, user shell, legacy pill, FR strings
  - phase: 54-04
    provides: Access annotation, decide(), per-request Principal
  - phase: 54-05
    provides: Auth0 start/callback/logout handlers and interstitial
provides:
  - GET /account (SIGNED_IN) rendering Identity, Preferences and the empty Frames card
  - Role-aware 404/403 pages (Back to Account / Back to sign in / Back to Home)
  - Theme and language POSTs that return a user to /account
  - Chromium proof of the cross-site sign-in/sign-out chain, both themes, 360px
affects: [54-07, 54-08, 54-09, 55]
tech-stack:
  added: []
  patterns:
    - "Fake Auth0 bound to 127.0.0.1 but advertised as localhost:<port> for a genuinely cross-site hop"
key-files:
  created:
    - companion/test_account_page.py
    - companion/test_browser_auth0.py
  modified:
    - companion/sign_in.py
    - companion/routes.py
    - companion/app.py
    - companion/login_page.py
    - companion/i18n_fr/account.py
    - companion/test_route_table.py
    - companion/testdata/render_baseline.json
    - test-support/companion_render_snapshot.py
key-decisions:
  - "A user principal's preference POSTs always return to /account; admins keep the NAV_TABS referer rule, plus /account"
  - "Legacy-admin has no email: the Email row shows an em dash and the Role row carries the legacy label"
  - "Error pages pick their onward link from the principal: user -> /account, anonymous -> /login, admin -> /"
requirements-completed: []
duration: 50min
completed: 2026-10-30
---

# Phase 54 Plan 06: Account route, user shell and cross-site browser proof Summary

A signed-in person now has an Account page (identity, preferences, empty Frames card, Sign out), a plain user sees nothing else (every global page is a 404 byte-identical to an unknown path), and Chromium confirms the Auth0 sign-in lands signed in across two different sites and that sign-out ends on the fixed login page.

## Tasks

1. `/account` route, role-aware error pages, preference redirects (d4ade6c)
   - `SignInMixin._handle_account_get` builds the Identity from the Principal and renders through `layout.page_shell` with slug `account` and no Health dot; `GET /account` is `SIGNED_IN` in routes.py; the route-table test lists it by hand.
   - `login_page.not_found_page` / `forbidden_page` take a `back` keyword (default Home); `Handler._back_target()` chooses Back to Account (user), Back to sign in to `/login` (no session) or Back to Home (admin, legacy admin). French "Retour au compte" added.
   - `_referring_tab` returns `/account` for a user always, and admits `/account` as a return target for admins.
   - 27 HTTP tests in `companion/test_account_page.py`: account for each principal, anonymous bare `/login` redirect, every admin GET and POST route answers a user with the unknown-path 404 body, user/anonymous/admin error shells, FR link, preference redirects for four referers, and an href audit (every user-page target is `/account`, a `/ui-*` or `/logout` action or a static asset; every user-nav link is a route a user may open).
2. Real-browser chain (54892d7)
   - `companion/test_browser_auth0.py`, 8 tests: invited user lands on `/account` with a single Strict HttpOnly `sp_session`; invited admin lands on `/` with the full nav; Sign out ends on the fixed `/login` and `/account` then redirects to `/login`; the legacy block is collapsed by default and the password form still signs in the legacy admin; an uninvited identity gets "No invitation found" with no cookie and no session row; login, refusal and Account have no horizontal overflow at 360px in light and dark and the Sign in link is at least 44px tall and full card width; a sign-in started from a link on another site lands signed in.

## Chromium observations (research assumptions A1, A7, A8)

- The app is on `127.0.0.1:<port>`, the fake provider is advertised as `localhost:<port>`, so the hop is cross-site.
- When the sign-in is started from the app's own login page, even a plain 303 landing worked (the redirect chain's initiator is the app, i.e. same-site), so that test alone cannot tell the two designs apart.
- When the sign-in is started from a link on another site, the temporary 303 variant FAILED (the browser withheld the Strict cookie on the redirected `/account`, which bounced to `/login`; test timed out waiting for `/account`), and the 200 meta-refresh interstitial PASSED. The interstitial is therefore what makes the landing work. The 303 change was temporary and reverted (`companion/sign_in.py` is unchanged by this plan).
- With the interstitial, Chromium sends the Strict session cookie, so the documented fallback to SameSite=Lax was not needed and `test_auth0_cookies.py` is untouched.
- Sign-out through the interstitial to the fake's `/v2/logout` and back to the fixed `returnTo` works; the form-action CSP did not block it.

## Render baseline review

`test-support/companion_render_snapshot.py --write` was re-run once after adding `/account` to the unauthenticated GET samples. The diff to `companion/testdata/render_baseline.json` is exactly one added entry: `"GET /account": {"location": "/login", "status": 303}`. No page body changed (unauthenticated 404 bodies are not in the baseline; the baseline 404 page is captured with a legacy-admin session and still says Back to Home).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] companion_render_snapshot.py needed the new route**
- **Issue:** `test_route_table.py` indexes the baseline by route key; a new route without a sample would fail.
- **Fix:** Added `"/account"` to the unauthenticated GET sample list (a literal, the module cannot import it from app) and regenerated the single entry.
- **Commit:** d4ade6c

**2. [Plan wording] Extra test for the 303-vs-interstitial proof**
- The plan's landing test alone passed with both designs, so a test starting from another site was added to make the proof meaningful (see observations).

## Known Stubs

The Frames card is intentionally an empty state; a later phase replaces it with the user's frames.

## Threat Flags

None. T-54-06-01..04 are covered by the tests above.

## Verification

- `pytest companion server stub-server -n auto` with `SKYPANE_REQUIRE_BROWSER=1`: 4467 passed, 7 skipped (root permission skips).
- The root-skipped tests run as `nobody`: 354 passed.
- ruff, mypy, function-size (611 functions, none over 80) and comment-history clean; `stub-server/test_phase47_freeze.py` green; no change to `stub-server/byos_server.py`, firmware or `measured_fields_freeze.json`. Loopback only, no secrets.

## Self-Check: PASSED

companion/test_account_page.py and companion/test_browser_auth0.py exist; commits d4ade6c and 54892d7 are in git log.
