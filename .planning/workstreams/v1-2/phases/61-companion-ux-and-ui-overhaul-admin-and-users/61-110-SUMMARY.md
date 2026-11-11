# Phase 61 Plan 110: Remaining audit-4 performance points (D55) Summary

Fixed Flights card height with `content-visibility`, bfcache-eligible pages with a session re-check on restore,
the Location map script split in two, and two component stylesheets linked only by the page families that use
them. Home's cold CSS is 16.0 KB gz smaller than before 61-109 (target 20 KB: not reached, see R14).

## Commits

- `11be4228` deterministic Flights card height with content-visibility (R10, R15)
- `cc24c4d6` bfcache-eligible pages with a session re-check on restore (R23)
- `c9f60bc5` Location map script split (R07)
- `230c08b4` component stylesheets (R14)

## Items

### 1. R10 + R15: Flights cards

Each card is now one fixed height: the label block is two reserved lines (airline, then route; a line is
reserved when a flight has no route), the detail is one line, all cut with an ellipsis; the height is
`--history-card-height` (tokens and unitless line heights only), set on `.row__main` and declared as
`contain-intrinsic-block-size` with `content-visibility: auto` on `li.history-card`. Same height at every
width and in either language, so the Load more scroll test passes unchanged.

Visual change, deliberate: a long airline name used to wrap to a second line ("Some Very Long Charter /
Operator Name Limited"); it is now cut with an ellipsis, and a card is about 1 px taller on a phone. Screenshots
before/after at 360/390/1280, light/dark: `scratchpad/shots110/shots/flights_{base,after}_*.png`. 1280 px is
pixel-identical (the table is shown there); 360 and 390 differ only by that.
I did not merge card and table into one markup (two renderers and their tests): the DOM stays at 2,079 nodes;
the saving is the skipped layout and paint of off-screen cards, not fewer nodes.

Test: `companion/test_browser_flights_card_height.py` (360, 390, 768, 1280 x EN and FR, long and short airline
names, a long route, a missing route): card height equals the declared intrinsic size, one height for all
cards, nothing overflows. `test_view_pages_03.py` updated in place (the detail line is single-line ellipsis
now instead of a two-line clamp).

### 2. R23: back/forward cache

Policy (`companion/page_cache.py`): an HTML page is `Cache-Control: private, no-cache` + `Vary: Cookie`
instead of `no-store` when it is a 200, sets no cookie, is a plain navigation (not a prefetch), carries
session-guard.js, and the browser already ran that script (it left the `sp_restore=1` cookie). Everything
else, including the first visit and any browser without scripts, stays `no-store`. No `unload` handler exists.

On `pageshow` with `persisted` set, the restore code now in `session-guard.js` (no new script tag, so no extra
request): hides the whole document at once (`visibility: hidden`), POSTs the page's own anti-forgery token to the
new `POST /session/check` (signed-in route, CSRF-checked, 204, never cached), then reveals on 204 and on any other
answer, a network error or 8 s without an answer goes to `/login?next=<page>&expired=1`. The token is derived from
the session, so another account or a new session fails it.

Security trade-off: `no-store` guaranteed that no copy of a page survives sign-out. `no-cache` lets the browser
keep the page in memory (bfcache) and, for history navigations that bypass bfcache, possibly in its private HTTP
cache. Mitigation: bfcache restores never display before the server confirms the session; the HTTP-cache entry is
keyed by `Vary: Cookie`, so after sign-out (cookie cleared), a new session or another account it never matches;
ordinary loads revalidate. Residual risk: a history navigation answered from the private HTTP cache without
bfcache runs no script check beyond the normal page scripts (the cookie key is the guard); the freshness poll and
session-guard still end an expired session on the first request.
Real iOS Safari bfcache cannot be verified headless: tests simulate `pageshow` with `persisted` in Chromium.
Chromium's bfcache is also not exercised end to end in headless runs.

Tests: `companion/test_browser_page_restore.py` (8): persisted pageshow with a valid session reveals; a page not
restored is untouched; after sign-out a restore stays hidden until the check answers and ends on the sign-in
page with the expired notice; a restored page of another session is refused; Back after sign-out never shows the
private page; the header policy (cacheable only after the script ran, `no-store` without it, no cookie set);
`/session/check` answers 204 to the page token only and is never cached. Route table, access matrix, CSRF key
count and the render baseline cover the new route; prefetch and freshness tests unchanged and green.

### 3. R07: Location map script

`place-map.js` 1,486 -> 1,066 lines; new `place-map-search.js` (496 lines: search box, airport and address
suggestions, "use my position"). `place-start.js` loads leaflet, place-search, place-map, place-map-search,
place-card, in order, after first paint (`data-map-search-src`). place-map.js hands its helpers over as
`window.skypanePlaceMapCore` once the map is up; no map, no search wiring (the plain form stays). Behaviour and
tests unchanged (all place browser tests green).

Measured honestly: Location TBT at phone x4 did not improve (46 ms -> 59 ms, run-to-run noise about +-15 ms):
the long task is `start()` building the map, not parsing the search code. The split keeps files under the
1,500-line ceiling and moves search code off the first frame, nothing more.

### 4. R14: component stylesheets

After 61-109 (core + six area sheets) the remaining shared core was analysed against the rendered DOM of 31
routes x 3 seeds x 2 widths (plus the scripts each page loads): a rule moves out of core only when it
cannot match on Home, any core-only page (sign-in, error pages, Credits, anything that links core alone) or
anywhere the corpus never shows it, and only when moving it after core cannot flip the cascade (for every pair
of overlapping, co-occurring, equal-specificity rules the original order is kept, also against rules inside
`@supports`/`prefers-*` blocks). Result: `style-c-console.css` (display, admin, place pages; 2,617 B gz) and
`style-c-lists.css` (flights, airlines, display, admin; 1,802 B gz), linked after core and before the area sheets,
by `page_styles.py` (`_COMPONENT_FAMILIES`); versioned URLs and the minify pipeline are unchanged; unnamed paths
still link every sheet. Home links neither sheet.


| Page (cold CSS, gz bytes) | Before 61-109 | After 61-109 (before this plan) | Now |
|---|---|---|---|
| Home (core + home) | 38,948 | 25,328 | 22,922 |
| Flights (core + c-lists + flights) | 38,948 | 24,800 | 24,240 |
| Airlines (core + c-lists + airlines) | 38,948 | 27,016 | 26,412 |
| Display (core + both + display) | 38,948 | 27,957 | 29,970 |
| Account (core + both + admin) | 38,948 | 29,090 | 31,103 |

Trade-off to state plainly: the moved rules compress worse in their own files (about 3.9x, against 6.3x inside
core), so a page that needs both component sheets (Display, Account, Fleet) now downloads about 2 KB gz more and
two more requests than after 61-109; Home saves 2.4 KB, Flights 0.6 KB, Airlines 0.6 KB, Location (console
sheet only) a little. If those pages matter more than Home, revert `230c08b4` alone (independent of the other
commits).

Target not reached: Home is 16.0 KB gz below the pre-61-109 sheet (was 13.6), not 20 KB. Reason: of 159 KB of
rule text in core, 85 KB matches elements Home renders (tokens, tab bar, glass blocks, tiles, toast, health
rows and the like), about 29 KB is needed by core-only pages (sign-in, error pages, Credits), 15 KB matches
nothing in the corpus (runtime-only state classes, kept in core); the rest, 17 KB minified (4.4 KB gz as
separate files, 2.4 KB gz saved from core), is what moved. Going further means giving error and sign-in pages their own component links or
deleting rules the corpus cannot prove unused; both are riskier than this plan's remit.

Verification: computed style of every element and pseudo-element (custom properties excluded) compared
between the commit before this change and the working tree, 25 routes (every Display view, Location with the
map up, Flights, Airlines, the editor with all rows, Account, Fleet and System, Users, Audit, Locations,
Components, Credits, Update, Pair a frame, Frame name, Settings, Home) x 360 dark and 1280 light: no difference
except animation phase (`stroke-dashoffset` on Home) and an image `is-loading` state (Flights). The first split
differed on Airlines cards, editor tables and Credits headings; the causes were rules inside `@supports` blocks
(now part of the cascade check) and pages that link core alone (Credits, now pinned to core). Hover, focus and
dialog states are covered by the browser suites (whole companion + test-support run, below).
`test_page_styles.py` updated in place for the new link sets (plus a test that Home links no component sheet);
stylesheet structure tests pass unchanged (they read the whole served stylesheet).

### 5. Brotli

Not touched (`deploy/` untouched). Owner action: Caddy's `encode zstd gzip` (deploy/Caddyfile) has no brotli.
Either build Caddy with the brotli encoder module (`xcaddy build --with github.com/dunglas/caddy-cbrotli`) and use
`encode br zstd gzip`, or serve pre-compressed `.br` files with `file_server { precompressed br gzip }` for
`/static/*`. Expected gain: about 15-20% smaller CSS and JS than gzip on a cold load.

## Measurements (audit fixture: 18,041 events, phone 390x844, CPU x4, Fast 4G, median of 3, headless Chromium)

Base = `1ca6151b` (after 61-109), after = this plan; routes of the default device.

| Page | Requests | Total raw bytes | FCP ms | LCP ms | TBT ms | Long tasks |
|---|---|---|---|---|---|---|
| Home | 18 -> 18 | 298,266 -> 283,935 | 468 -> 476 | 1,028 -> 964 | 0 -> 0 | 0 -> 0 |
| Flights | 18 -> 19 | 418,352 -> 411,301 | 532 -> 536 | 692 -> 608 | 0 -> 0 | 1 (75 ms) -> 0 |
| Location | 33 -> 35 | 577,034 -> 574,722 | 496 -> 500 | 1,740 -> 1,776 | 46 -> 59 | 2 -> 2 |
| Airlines | 31 -> 32 | 599,502 -> 592,173 | 596 -> 548 | 1,056 -> 1,000 | 0 -> 0 | 0 -> 0 |
| Account | 14 -> 16 | 279,857 -> 282,817 | 432 -> 436 | 872 -> 856 | 0 -> 0 | 0 -> 0 |

Wins: Home and Airlines carry less CSS, Flights loses its 75 ms long task. Account carries two more sheets
(+3 KB raw, +2 KB gz): it uses both. Location is unchanged within noise. Timings are the sandbox's and vary by
+-40 ms between runs.

## Gates and tests run

- Whole `companion` + `test-support` suite after the CSS split with `-n 6`: 9,982 passed, 4 failed (all fixed
  since, see below), 3 skipped (root-only permission tests, unrelated to changed routes: read, none exercises
  `/session/check`, the stylesheets or the scripts).
- After the fixes (route table, access matrix, CSRF, place assets, sign-in surfaces digests, render
  baseline): `test_route_table`, `test_place_map_assets`, `test_sign_in_surfaces`, `test_access_matrix`,
  `test_page_styles`, `test_stylesheet_structure`, `test_structure_guards`, `test_suite_guards`: green.
- New browser tests (`test_browser_page_restore`, `test_browser_flights_card_height`) plus
  `test_browser_place_search` stressed in 4 parallel processes: 4 x 33 passed.
- ruff, mypy (44 modules), `check_comment_history.py`, `check_function_size.py` (1,066 functions, none over 80),
  `stub-server/test_phase47_freeze.py` (21 passed): green. `companion/app.py` 1,491 lines; every JS file under
  1,500 lines.
- `scripts/run-all-tests.sh` (coverage gate) was not run; CI does.

## Deviations from Plan

- The page-restore code lives in `session-guard.js` instead of a new `page-restore.js`: a new script tag changes
  the 17-script ceiling and the pinned script-count tests and costs a request on every page.
- The first full run found two failures from item 2 that targeted runs had missed (`test_route_table`,
  render baseline lacked `POST /session/check`); fixed in `230c08b4` (in place, not weakened).

## Known stubs

None.

## Self-Check: PASSED

Commits `11be4228`, `cc24c4d6`, `c9f60bc5`, `230c08b4` exist; new files
(`companion/static/place-map-search.js`, `style-c-console.css`, `style-c-lists.css`,
`companion/test_browser_page_restore.py`, `companion/test_browser_flights_card_height.py`) exist.
