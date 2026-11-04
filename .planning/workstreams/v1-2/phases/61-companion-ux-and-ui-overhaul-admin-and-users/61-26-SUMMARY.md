---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 26
subsystem: companion
tags: [leaflet, map, geolocation, nominatim, location-page]
requires: [61-24, 61-25]
provides: [companion/static/place-map.js, map interaction of the Location and detection page, test-support/place_map_support.py]
key-files:
  created:
    - companion/static/place-map.js
    - companion/test_place_map_assets.py
    - companion/test_browser_place_map.py
    - companion/test_browser_place_search.py
    - test-support/place_map_support.py
  modified:
    - companion/pages/place_page.py
    - companion/static/style.css
    - companion/static_files.py
    - companion/ui_shell.py
    - companion/ui_base.py
    - companion/layout.py
    - companion/app.py
    - companion/i18n_fr/detection.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 26: Map interaction of the Location and detection page

`/detection` now runs a real OpenStreetMap map (vendored Leaflet 1.9.4 plus first-party `place-map.js`) with a draggable accent pin, an area circle, airport dots, search by city or address, "Use my position" and the nearest-airport offer. The page still saves with the library blocked, with scripts off and with both map hosts aborted.

## What changed

- **place-map.js** (one ES5 IIFE, no language in it): tile URL as one constant, tile layer with `referrerPolicy: 'origin'`, attribution `(c) OpenStreetMap contributors` inside the map (prefix removed), 44 px zoom buttons, tap or click drops/moves the pin, dragging adjusts it, latitude/longitude fields follow (4 decimals, `input` events fired so the dirty bar reacts) and the pin follows edits of the fields, status line "Pin placed at ...". Circle in area mode follows the radius and the mode radios. Airport dots from zoom 8 (12 px mark, 44 px hit box) built only for airports in view. After 4 `tileerror` with no `tileload` the notice shows inside the card. `map-ready` is added to the html element only once the map runs and the fields card closes (it stays open when a field has an error). With the library missing or throwing, the map container is hidden, `map-ready` is absent, the fallback explanation and the open details card remain.
- **Search**: submit only; min 3, max 120 characters; one GET to Nominatim (`format=jsonv2`, `q`, `countrycodes=fr`, `limit=5`, `accept-language` en/fr), `credentials: 'omit'`, `referrerPolicy: 'origin'`, no custom headers; one in flight, 1.5 s lock (the single timer), in-memory repeats, no retry. Rows built with `textContent`; coordinates parsed and range-checked; a hostile answer proves nothing executes. No-result and failure sentences per the spec.
- **Use my position**: `getCurrentPosition` only on tap (`enableHighAccuracy:false, timeout:10000, maximumAge:60000`), busy label, success sentence with the accuracy, denied/unavailable/timeout sentences, button hidden without `navigator.geolocation`.
- **Nearest airport**: haversine over the anchor data, within 3 km a line and a "Follow NAME" button (hidden when that airport already is the followed runway).
- **Wiring**: `place_page` renders the strings as `data-t-*` attributes plus the search limits, the results/notice/nearest containers and a label span in the locate button. Leaflet's stylesheet is linked after `style.css` on this page only (`page_shell(styles=...)`); `LEAFLET_SCRIPT_SRC` and `PLACE_MAP_SCRIPT_SRC` are in `SHELL_SCRIPT_ORDER`, not in `GLOBAL_PAGE_SCRIPTS`; the page's scripts and styles live in `place_page.PAGE_SCRIPTS` / `PAGE_STYLES`. `icon-pin` added to the sprite (47 glyphs). CSS is additive and token-based (no filter on tiles, no new size, weight, keyframes or duration; accent list in the stylesheet header names the pin and circle).
- **Tests**: `test-support/place_map_support.py` routes the tile host (fixed 256x256 PNG) and Nominatim (canned jsonv2, abort, 429, 503) through `page.route`, records request headers, and shares seed/probe helpers. `test_browser_place_map.py` (28), `test_browser_place_search.py` (12), `test_place_map_assets.py` (16 non-browser).

## Deviations from Plan

1. **[Rule 3 - Blocking] Choosing an airport (list, dot, "Follow NAME") navigates** to the server's `?airport=` page instead of flying in place. The runway cards, the label and the pin for an airport are server-rendered and the plan forbids any fetch outside the search submit, so the new document opens at the airport at zoom 13 in runway mode with the runway list. The dot and the nearest-airport button click the airport's existing `data-detection-nav` anchor (which carries mode and radius). Tests assert that end state.
2. **Locate button placement**: under the search field on both widths (the top-right overlay on desktop was not built).
3. **`styles=` argument and `place_page.PAGE_SCRIPTS`**: `companion/app.py` sat exactly at the 1500-line ceiling, so the route's scripts and style live in `place_page.py` and `app.py` shrank by two lines.
4. **Older tests updated in place** (their subject changed): `test_browser_place_page.py` (map hosts routed, waits for `map-ready`, opens the now-closed coordinates card), `test_browser_detection.py`, `test_browser_empty_state_scale.py`, `test_browser_ux_01.py`, `test_browser_ux_03.py` (route both map hosts: their pages now request tiles), sprite counts 46 to 47 and the all-scripts count 16 to 18 in `test_companion_app_01.py` / `test_companion_app_03.py`, the three sign-in digests (only the new sprite symbol moved; verified by stripping it and getting the old digest), `render_baseline.json` (44 page digests, sprite only; the Detection page is not pinned), and `HOOKS` in `test_page_scripts.py`.
5. The search results list carries `aria-live="polite"`; the "Type at least 3 characters" sentence is an added string (EN/FR) for a too-short submit.
6. `icon-locate` was already in the sprite (the 61-25 note was stale); only `icon-pin` was added.

## Gates

ruff, mypy (29 modules), comment-history, function size (931, none over 80), Phase 47 freeze (21 passed): clean. Full `companion test-support stub-server -n auto --no-cov` after the last code commit: 7088 passed, 4 skipped, 1 failed (`test_browser_auth0.py::test_uninvited_page_offers_another_account_and_the_way_back`, a file not touched here: `a.login-signin` measured 17 px under load; re-run alone twice, 15 passed, so a load flake). New browser files run 3 times in a row green (`place_map` + `place_search` + `place_page`: 51 passed each time). Mutation check: switching both referrer policies to `same-origin` fails the Referer tests.

## Known Stubs

None.

## Self-Check: PASSED
