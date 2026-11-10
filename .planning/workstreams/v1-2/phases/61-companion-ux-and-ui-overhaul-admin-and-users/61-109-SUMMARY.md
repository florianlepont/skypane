---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 109
subsystem: companion
tags: [audit-4, performance, caches, css-split, place-search, splash]
requires: [61-108]
provides: [audit-4 performance findings R01-R28 (D54)]
key-files:
  created:
    - companion/page_styles.py
    - companion/pages/airline_types_fragment.py
    - companion/static/place-search.js
    - companion/static/place-start.js
    - companion/static/style-home.css
    - companion/static/style-flights.css
    - companion/static/style-airlines.css
    - companion/static/style-place.css
    - companion/static/style-display.css
    - companion/static/style-admin.css
    - companion/test_page_styles.py
    - companion/test_browser_place_search_gate.py
    - companion/test_static_assets_404.py
  modified:
    - companion/history_cache.py
    - companion/history_query.py
    - companion/airline_collection.py
    - companion/pages/airlines_page.py
    - companion/pages/airline_table.py
    - companion/pages/place_page.py
    - companion/routes.py
    - companion/static_files.py
    - companion/static/style.css
    - companion/static/airline-types.js
    - companion/static/splash-boot.js
    - companion/static/place-map.js
    - companion/static/place-card.js
    - companion/static/place-airport-list.js
    - companion/ui_shell.py
    - companion/prefs.py
    - companion/app.py
decisions:
  - "The history cache computes a key once for concurrent requests (per-key lock, 32 entries, least recently used) and caches the airline collection and each Flights filter/sort view per history version"
  - "The airline editor does not inline the aircraft-type rows: airline-types.js fetches /airlines/manage?types=<n> when a chevron first opens; ?types=all stays for no-JS"
  - "Every address-search request goes through window.skypaneSearchGate (place-search.js); a submit cancels a suggestion of another query, a newer suggestion waits its turn"
  - "The Location page links place-start.js only; it loads Leaflet, the gate, place-map.js and place-card.js after the first paint, and place-airport-list.js when idle"
  - "style.css is the core sheet; rules only one page family uses sit in style-<area>.css; a page links core plus its area sheets (page_styles.py); an unnamed route links every area sheet, error pages and out-of-request renders link core alone"
  - "An unknown asset-like path (.ico .png .js .css .map .json .txt ...) answers an empty 404 cacheable for 300 s; a page path keeps the HTML 404"
---

# Phase 61 Plan 109: Audit 4 performance findings (D54)

Every STILL-OPEN or NEW finding of `PERF4.json` was read with its evidence and either fixed, shown to
be already met, or documented with the reason it is not implemented. The splash duration is unchanged.

## Result per finding

| # | Result | Test |
|---|---|---|
| R01 | Done. `place-search.js` is the one gate: one request in flight, at least the lock (1500 ms from `data-search-lock-ms`) between starts, one answer cache keyed by the lower-cased query, shared by `place-card.js` (suggestions) and `place-map.js` (submit). An Enter on a query that is in flight, waiting or cached reuses it; a submit of another query cancels the in-flight suggestion with an `AbortController`; a newer suggestion waits (the existing "never two at once" test still holds); a submit bumps a round counter so a late suggestion answer does not overwrite the submit's results | `test_browser_place_search_gate.py` (page `fetch` wrapped to time and overlap each request: suggestion + Enter on the same text = 1 request, max 1 in flight; suggestion then a different submit = max 1 in flight, 1 aborted, >= 1000 ms start to start); `test_browser_place_search.py`, `test_browser_place_search_loading.py` unchanged and green |
| R02 | Done. `airline_collection.airline_collection()` and the new `collection_across()` (the editor merges every frame) cache `(entries, summary)` per history signature and rename-registry digest in `history_cache`; only the New pill (the one clock-dependent field) is recomputed per request. Flights caches each `(q, kind, sort)` view next to the folded history | `test_history_cache.py` (collection built once per history and renames, New pill re-judged at a later time; a Flights filter computed once per history and search) |
| R03 | Done. `history_cache.cached()` / `cached_many()` take a per-key lock: the first requester runs the loader, concurrent ones wait for its result. Not done: the optional incremental fold (extending the cached fold by rows with a higher id) and warming the cache from the poller (a separate process; the fold of a miss still costs 120-150 ms) | `test_history_cache.py::test_concurrent_requests_after_a_write_share_one_computation` |
| R04 | Verified fixed by the audit; nothing to do | - |
| R05 | Done. The editor table no longer inlines `<template class="airlines-types">`; each group with rows carries `data-types-src` (`/airlines/manage?types=<n>`, administrator only, bare fragment, `no-store`, device scope preserved). `airline-types.js` fetches it on the first expand and on load for a group rendered open; a failed request retries on the next toggle. `?types=all` (the `<noscript>` link) still renders every row. HTML 742,365 -> 158,715 B raw (22.4 -> 13.1 KB gz) | `test_airline_manage_routes.py` (fragment body, 404 for owner/co-manager/out-of-range, 303 anonymous, `?types=all`), `test_browser_perf_remaining.py::test_the_editor_opens_an_airlines_types_on_demand_...` (no template, exactly one request, rows appear, filter finds a type) |
| R06 | Verified fixed | - |
| R07 | Partly done. `place-start.js` is the only map script the page links; after two animation frames and an idle callback it loads Leaflet, the gate, `place-map.js` and `place-card.js` in order, and the 272 airport rows are built by `place-airport-list.js` when idle after that (rows hidden at creation if text was already typed). FCP 536 -> 436 ms (phone, CPU x4). Not changed: the 131 ms evaluation of `place-map.js` itself and TBT (81-93 ms before, 88 after): splitting its marker/cluster code from the suggest code means editing `place-map.js` (1486/1500 lines); the work now runs after the first paint instead of before it | `test_place_map_assets.py` (starter linked, deferred; library before glue named in `data-*-src`), `test_page_scripts.py`, all `test_browser_place_*` green |
| R08, R09 | Verified fixed | - |
| R10 | Not changed (documented). Thumbnails and Display previews are already `loading="lazy" decoding="async" fetchpriority="low"` (R10's second half); the first screenful of Display stays eager. `content-visibility: auto` needs a server-known height: a collection card's height depends on how its airline name wraps, and a skipped card with a wrong `contain-intrinsic-size` moves the scroll position (the failure of the earlier Flights attempt). The 17 requests at load are Chrome's lazy-load margin on a fast link | - |
| R11, R12, R13 | Verified fixed / verified | - |
| R14 | Done, with a smaller gain than the 20-25 KB gz estimated. See "Stylesheet split" | `test_page_styles.py`, `test_stylesheet_structure.py`, `test_structure_guards.py`, the served-CSS tests via `served_stylesheet()`; computed-style comparison below |
| R15 | Not changed (documented). Only one of the card list and the table is visible (the other is `display: none`, so it is neither laid out nor painted); the cost is parse and style matching of 2,077 nodes. A single markup would rewrite two renderers and their tests, and `content-visibility` on cards has the height problem of R10. `Load more` (491 KB for `more=3`) is the only case that grows | - |
| R16, R19, R21 | Optional in the audit (opaque look sheet on phones, versioned illustration URLs, pagination of /fleet and /users beyond ~25 rows); not done. R21 measured 84 ms for 60 devices | - |
| R17 | Already met, no code. `_render_tab()` computes the token from `stat()` calls, one small `SELECT` and the health snapshot and answers a matching freshness tick with a bodiless 304 before `render()` runs (`test_freshness_token.py`); the 10-19 ms per poll in the audit is `page_context()` plus that token, not a render. Airlines and the editor do not poll (no `data-refresh-token`), so they never make this request. Left alone on purpose: the forced full refresh every 7th tick, the safety net for any input the token misses (a test pins it) | - |
| R18 | Done, with a deliberately narrow scope. `static_files.looks_like_asset()` / `send_asset_not_found()`: an unmatched path with a known asset extension that is under `/static/` or a single segment (`/favicon.ico`, `/robots.txt`, `/static/sw.js`, `/preview.png`) answers an empty 404 with `Cache-Control: public, max-age=300` (20,919 B HTML before). Two-segment and device-scoped file routes (`/illustration/x.png`, `/runway-image/x.png`, `/devices/<id>/static/...`) keep the page 404 on purpose: a refused admin-only route answers that page, and an absent one must stay indistinguishable from it (`test_access_matrix.py`, `test_user_view_http.py` pin this and stay unchanged). Two tests that pinned the HTML body of `/preview.png` now pin the empty body | `test_static_assets_404.py`, `test_companion_app_02.py`, `test_companion_app_04b.py` |
| R20 | Verified fixed | - |
| R22 | Done. `splash-boot.js` injects `<link rel="preload" as="script">` for `splash.js` as soon as the gate passes, so the request overlaps parsing; the script is still downloaded once; duration and `HARD_CAP_MS` unchanged | `test_browser_splash.py::test_the_splash_script_is_preloaded_and_fetched_once` |
| R23 | Not changed (documented). `no-store` is the sign-out guarantee (`page_cache.py`): a page that may be restored from the back/forward cache is shown without a request, so `private, no-cache` needs a `pageshow` (persisted) check against the session before it is safe, and only Chromium benefits (WebKit restores regardless). Owner action for the transfer part: Caddy `encode zstd gzip` (deploy/Caddyfile:53) has no brotli (needs a Caddy build with the brotli module or pre-compressed assets), and the upstream is HTTP/1.0 per request; both are deploy changes | - |
| R24, R26, R27 | Verified | - |
| R25 | Already met. The page opening animates the header and at most five blocks with the shared fade and rise (opacity + transform only, never rows, tables or `#main-content`), `#main-content` is not a view-transition group, and the keyframe properties are asserted. The audit's table confirms those choices; no change | `test_browser_page_opening.py` (6 animated elements on tall pages, 8 otherwise, no row, only opacity/transform, 360 and 1280) |
| R28 | Covered by R03 (single flight): four tabs hovering the same page after a flight now share one computation | see R03 |

## Stylesheet split (R14)

`style.css` (409 KB source, 264,689 B served) is now the core sheet plus six area sheets, cut by a script
(kept outside the repo) that:

1. parses the stylesheet into top-level rules and the rules inside `@media`/`@container`/`@layer` blocks
   (`@supports` blocks and `prefers-reduced-motion` blocks stay whole in core: tests count them, and
   they hold the overrides that win over earlier rules);
2. gives a rule to an area only when every class or id of each of its selectors is rendered, in the
   Python and JavaScript sources, by that area's page modules alone (reverse import closure from each
   page's entry modules, shared hubs such as `layout` and `ui_*` count for every area; a class never
   found in the sources is core);
3. keeps a selector's rules together (a selector split across sheets goes to core);
4. moves a rule back to core when a later core rule of equal or higher specificity declares an
   overlapping property on an element that can carry both classes (class co-occurrence read from the
   rendered pages of three seeds at two widths), so the original order of the cascade cannot flip.

Pages link `style.css` then their area sheets (`page_styles.areas_for(path)`, device prefix stripped):

| Path | Area sheets |
|---|---|
| `/` | home |
| `/flights`, `/history` | flights |
| `/airlines`, `/airlines/manage` | airlines |
| `/detection` | place (then Leaflet's own sheet) |
| `/display*`, `/settings` | display |
| `/fleet` | display, admin |
| `/account`, `/users`, `/audit`, `/locations`, `/update`, `/pair-frame`, `/frame/name`, `/credits` | admin |
| any other path (e.g. `/components`) | every area sheet |
| error pages (no active tab), a document rendered outside a request, the sign-in shell | core only |

Sheets are served by the existing pipeline (`minify_css`, `?v=` immutable URLs). Served bytes (gzip):
core 21,992 B, home 1,878, flights 1,054, airlines 3,378, place 5,318, display 4,586, admin 5,690.

**Verification of the cascade.** The computed style of every element and its `::before`/`::after`
(custom properties excluded) was compared between the commit before this plan and this plan's tree: 24
routes (all Display views, Location with the map up, Flights, Airlines, the editor with every type row,
Account, Fleet and System, Users, Audit, Locations, Components, Credits, Update, Pair a frame, Home) x 360
and 1280 px x light and dark, same frozen clock and fixture. The first split differed on 67 pages (glass
fill and shadow of collection cards, audit list, users table, fleet blocks losing 24 px of margin); the
co-occurrence rule above removed all of them. What remains is animation phase noise (an SVG
`stroke-dashoffset`, an image's `is-loading` class) and one `pointer-events` value on the map while its
tiles load. Hover, focus, open dialogs and the other media states were not compared this way (the browser
suites cover them).

Not reached: the audit asked for 20-25 KB gz less on a cold load; the measured saving is 10-14 KB gz per
page. 127 KB of source (the `:root` tokens, element and attribute rules, the tab bar, toast, filter bar,
lightbox, health rows, glass blocks, ...) is used by every page family or by a class the sources only
compose at run time, so it stays in core.

## Measurements (same fixture as the audit: 18,041 events, 52 airlines, 62 devices; before = the commit before this plan)

Server CPU per request (cache hit, median of 20; `/proc` CPU, robust to sandbox load):

| Route | CPU ms before -> after | HTML raw before -> after | HTML gz before -> after |
|---|---|---|---|
| Home | 7.0 -> 9.0 | 38,945 -> 39,014 | 7,382 -> 7,399 |
| Flights | 18.5 -> 15.5 | 146,992 -> 147,064 | 12,700 -> 12,713 |
| Flights `more=3` | 39.5 -> 37.5 | 496,093 -> 496,165 | 28,699 -> 28,713 |
| Flights `q=afr` | 44.5 -> 14.5 | 114,808 -> 114,880 | 9,584 -> 9,599 |
| Airlines | 40.0 -> 15.5 | 182,570 -> 182,643 | 13,153 -> 13,169 |
| Airline editor | 75.0 -> 35.0 | 742,365 -> 158,715 | 22,448 -> 13,082 |
| Location | 11.5 -> 11.5 | 79,095 -> 79,240 | 19,236 -> 19,297 |
| Display | 12.5 -> 12.5 | 96,695 -> 96,767 | 10,561 -> 10,581 |
| Fleet | 22.0 -> 23.0 | 68,996 -> 69,138 | 11,550 -> 11,583 |

After a new flight (median of 5): first Flights request 130 -> 120 ms, Airlines 120-160 -> 140, editor
160-200 -> 150. Four simultaneous Flights requests right after a new flight: **13,260 ms CPU / 8,709 ms
wall -> 250 ms / 206 ms** (a sandbox GIL convoy made the "before" figure far worse than the audit's 640 ms;
it reproduced on a second run). Four different history pages: 2,160 -> 1,045 ms CPU.

Cold load, phone 390x844 DPR 3, CPU x4, Fast 4G, median of 3 (sandbox load makes FCP/LCP +-60 ms and
TBT +-40 ms):

| Page | Requests | Stylesheet gz | FCP ms | LCP ms | TBT ms |
|---|---|---|---|---|---|
| Home | 18 -> 19 | 38,948 -> 25,328 | 532 -> 512 | 1,016 -> 972 | 9-37 -> 54 |
| Flights | 18 -> 19 | 38,948 -> 24,800 | 584 -> 444 | 844 -> 772 | 52-75 -> 9 |
| Airlines | 31 -> 32 | 38,948 -> 27,016 | 608 -> 512 | 1,092 -> 924 | 21-44 -> 26 |
| Editor | 24 -> 25 | 38,948 -> 27,016 | 804 -> 488 | 1,284 -> 944 | 22 -> 22 |
| Location | 31 -> 34 | 42,470 -> 32,331 | 536 -> 436 | 1,636 -> 1,480 | 81-93 -> 88 |
| Display | 27 -> 28 | 38,948 -> 27,957 | 596 -> 484 | 740 -> 600 | 27-29 -> 24 |
| Account | 14 -> 15 | 38,948 -> 29,090 | 520 -> 416 | 924 -> 820 | 1-4 -> 0 |

Raw numbers: `scratchpad/shots109/measure_before.json`, `measure_after.json`; fixture and scripts
`boot2.py`, `measure.py`, the classifier `split_css.py`, the comparison scripts `capture_full.py`,
`capture_styles.py`, `cmpfull.py` in the same folder.

## Deviations from Plan

- **[Rule 3 - Blocking]** Tests that pinned the old structure were updated in place, with the same
  assertions on the new shape: `served_stylesheet()` (test-support) now returns the core sheet followed
  by every area sheet (`served_core_stylesheet()` returns the core alone) so rule-level checks see the
  whole stylesheet; `test_structure_guards.py` names the four sheets over the 1,500-line ceiling in
  `TRACKED_FILE_EXCEPTIONS` with a reason each (the core sheet keeps its entry); `test_page_scripts.py`,
  `test_place_map_assets.py` (the starter replaces three linked scripts), `test_companion_app_03.py`
  (26 deferred scripts: `place-search.js` and `place-start.js` joined `SHELL_SCRIPT_ORDER`),
  `test_companion_app_04.py` (ambient spenders compared sorted: the rules sit in different sheets),
  `test_status_pages_05b.py` (the base `.airlines-table` rule is the one outside any media block),
  `test_console_users.py` / `test_co_managers_page.py` (read the whole stylesheet through the helper),
  `test_companion_app_02.py` / `test_companion_app_04b.py` (`/preview.png`, a single-segment path, is an empty 404),
  `test_airline_sheet.py`, `test_status_pages_05b.py`, `test_status_pages_07.py` (render the editor with
  `?types=all`), `test_browser_perf_remaining.py` (fetch on expand).
- `companion/app.py`: +3 lines (1491 of 1500): `prefs.set_request_path()` in `_dispatch` and the
  asset-404 branch. A first, wider version (every 404 of a file-like path empty) broke the
  "a refused route is indistinguishable from an absent one" tests in `test_access_matrix.py` and
  `test_user_view_http.py`; it was narrowed rather than those tests changed.
- The render baseline (`companion/testdata/render_baseline.json`) was regenerated: served pages now link
  their area sheets; the error-page and shell digests in `test_sign_in_surfaces.py` did not move.

## Not done (exactly)

- R03: incremental fold of a cache miss and cache warming from the poller.
- R07: the evaluation cost of `place-map.js` (131 ms at x4) and the Location TBT; only its position
  (after the first paint) changed.
- R10, R15: no `content-visibility` / single Flights markup (reasons above).
- R14: 10-14 KB gz saved per cold page, not 20-25 KB.
- R16, R19, R21, R26: optional items of the audit.
- R17: forced full refresh every 7th tick kept on purpose.
- R23: not changed; needs a product decision (bfcache and sign-out) and, for compression, a Caddy change
  (brotli module or pre-compressed assets) which is the owner's deploy action.

## Tests run

ruff (`companion server test-support scripts`), mypy, `check_comment_history.py`, `check_function_size.py
--max 80 server stub-server`, `stub-server/test_phase47_freeze.py`; all `companion/test_browser_*.py`
(112 files) together with `test_page_scripts.py`, `test_companion_app_0*.py`, `test_stylesheet_structure.py`,
`test_suite_guards.py`, `test_structure_guards.py`, `test_sign_in_surfaces.py`, `test_render_baseline.py`,
`test_components_page.py`: 3,574 passed, 2 skipped (root ignores permission bits), 0 failed; then every
non-browser file of `companion/` and `test-support/` (7,023 passed, 3 skipped, plus the one new asset-404 test fixed and re-run green) after the last code change; the new and changed browser files (`place_search_gate`, `splash`,
`perf_remaining`) 3 times in a row at `-n 4`.

## Self-Check: PASSED
