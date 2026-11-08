---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 95
subsystem: companion-navigation
tags: [splash, prefetch, session-expiry, sign-in, caching]
key-files:
  created:
    - companion/next_route.py
    - companion/page_cache.py
    - companion/static/session-guard.js
    - companion/static/prefetch.js
    - companion/test_browser_navigation_assist.py
  modified:
    - companion/app.py
    - companion/static/splash-boot.js
    - companion/static/quick-switch.js
    - companion/static/freshness.js
    - companion/static/list-filter.js
    - companion/static/modal.js
    - companion/ui_shell.py
    - companion/ui_base.py
    - companion/layout.py
    - companion/static_files.py
    - companion/i18n_fr/common.py
metrics:
  completed: 2026-11-08
---

# Phase 61 Plan 95: Splash at every opening, page preloading, session-expiry feedback Summary

The splash plays at every opening of the site (once per browser session whatever the cache holds), navigation destinations are prefetched into a short private HTTP cache keyed by cookie, a request refused because the session ended shows a translated message and leads to `/login?next=<page>`, and the quiet-hours dialog shows the saved window when it opens again.

## 1. Opening splash (W154)

`splash-boot.js` no longer looks at the stylesheet's resource timing. The `sessionStorage` flag (try/catch, written before anything else) is the only gate: a new tab, the home-screen app or a bookmark opening is a new browser session and plays it; moving between pages in a tab does not. Design, duration (hard cap 3.2 s, `FORCE_DONE_MS` 1.9 s), reduced-motion behaviour, the lazy `splash.js` injection and the versioned immutable URLs are untouched. The sign-in card has no splash markup, so a session-expiry round trip never plays it (the flag is already set in that tab anyway). A page restored from the bfcache keeps what it showed; no replay (kept simple on purpose).

## 2. Preloading (W155) and the caching decision

HTML is `Cache-Control: no-store` and must stay so for every normal navigation (sign-out, other account, back button). Design chosen:

- `prefetch.js` (global script) fetches the targets of `.tab-bar`, `.sidebar-nav` and `.mobile-nav` links with a low-priority same-origin GET carrying `X-Requested-With: prefetch`, after load + 2.5 s on idle (`requestIdleCallback`), and at once (front of the queue) on `touchstart`, mouse `pointerover` and `focusin`. Skipped: the current page, other origins, links with a query or a fragment, `/login`, `/logout`, `/quick/*`, `/static/*`, downloads and `target=_blank`; Save-Data and 2G-class connections; hidden tabs. Two requests at most at once, eight queued at most, a page is not re-requested within 8 s. It never sends a POST. It does not rely on Speculation Rules (no iOS Safari support); none were added.
- `companion/page_cache.py`: only a 200 HTML answer to a request with that header and no `Set-Cookie` is `private, max-age=10` plus `Vary: Cookie`; every other answer stays `no-store`. The header cannot be added by a cross-site page without a CORS preflight the server never answers. `Vary: Cookie` keys the entry by the whole cookie header, so another account, a sign-out, a new session all miss it (the shared browser cache cannot leak across users).
- CSRF: the token is derived from the session token (`csrf-v1:` hash), stable for the whole session, so a prefetched page's token is valid when used.
- Staleness: any form POST (capture-phase `submit` listener) or confirmed quick switch rewrites a `sp_mut=<timestamp>` marker cookie (SameSite=Strict, JS-set, timestamp only), which changes the `Vary: Cookie` key so pages warmed before the change are not served after it. The freshness tick (conditional GET with its own `If-None-Match`, bypassing the cache) still corrects a page up to 10 s old after it opens.
- Measured in Chromium (scratch run, unguarded context): tap on a warmed tab opens with `transferSize 0, deliveryType "cache"`; after the marker cookie changes the same tap goes to the network.
- Not done: no JS in-memory HTML cache or document swapping (a plain navigation cannot consume it and swapping the document would break script lifecycle and the view transition).

## 3. Session-expiry feedback

`session-guard.js` (global) exposes `window.skypaneSession.report(response)`, `expire()`, `ending()`. A 401 expires directly; a 403, an opaque redirect or status 0 is confirmed against `/login` (200 only when signed out, `redirect: manual`), so an ordinary 403 keeps its own handling. On expiry the server-rendered, translated template (`data-session-expired-template`, "Session expired — sign in again." / "Session expirée — reconnectez-vous.") is cloned into the existing live toast region and, after 1.8 s, the browser goes to `/login?next=<encoded path+query>`. Wired into quick-switch (replaces the generic failure toast when the session ended), the freshness tick (no retry ladder when ended) and the Flights list view (a fetch redirected to `/login`; `giveUp` stands down).

`next` validation moved to `companion/next_route.py`: the path must equal a `NAV_TABS` route exactly; an optional query may only contain unreserved characters, `=&,:+-` and valid percent-escapes, at most 200 characters in total; a fragment, `;`, backslash, scheme, host or `//` rejects the whole value. `_redirect_to_login` now keeps the query (falling back to the bare path, then to plain `/login`), so `/login?next=%2Fflights%3Fsort%3Dairline` reaches the Auth0 start link and the callback, which validates again. app.py shrank to 1479 lines.

## 4. Quiet-hours dialog

`modal.js` resets the forms of a dialog when it closes (Close, Esc, backdrop) and fires `change` so the preset cards re-sync; reopening shows the saved window.

## Deviations from Plan

- `test_auth0_login.py::test_hostile_next_falls_back_to_the_default_landing` pinned `/health?x=1` as hostile (the old exact-match rule). It is now a positive case in its own test (`/health?x=1` is kept); `#frag` and `;` variants were added to the hostile list.
- `test_companion_app_03.py` script-count test updated in place (22 deferred scripts, 9 global); the three pinned digests in `test_sign_in_surfaces.py` and `testdata/render_baseline.json` regenerated (the shell gains two scripts and a template).
- The bfcache replay of the splash after a long absence was not implemented (keep simple).
- No Speculation Rules block.

## Known limitations

- The 10 s cache window exists in real browsers only; the Playwright route guard disables the browser cache, so the tests assert the request pattern and the response headers, and the cache hit was verified once in a scratch run.
- A prefetched page can be up to 10 s old when opened if the change happened on another device; the freshness tick repairs it.

## Verification

See the hand-back for the exact test list.
