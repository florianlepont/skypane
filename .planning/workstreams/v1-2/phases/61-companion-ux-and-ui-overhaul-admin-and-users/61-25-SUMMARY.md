---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 25
subsystem: companion
tags: [location-page, no-script, detection, map-contract]
requires: [61-20, 61-24]
provides: [companion/pages/place_page.py, map data contract, no-script save_place path]
key-files:
  created:
    - companion/pages/place_page.py
    - companion/test_place_page.py
    - companion/test_browser_place_page.py
  modified:
    - companion/pages/detection_page.py
    - companion/detection_actions.py
    - companion/routes.py
    - companion/app.py
    - companion/i18n_fr/detection.py
    - companion/static/style.css
    - companion/test_detection_page.py
    - companion/test_detection_position.py
    - companion/test_browser_detection.py
    - companion/test_config_page_05.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 25: Location and detection page

`/detection` is now the server-rendered Location and detection page (status, place, French airports, What to follow, details, save bar) and saves a place with scripts blocked and both map hosts aborted. Single commit 98429c8 (both tasks, as the plan says).

## What changed

- `place_page.render(ctx, query, errors, submitted, place)`, built from one function per card. `detection_page.py` is reduced to shared constants, messages, query parsing and the save bar (`dirty_bar_html(carried, save_text)`); its saved-locations rendering and old two-mode page are deleted, with their French strings.
- Map data contract exactly as specified (`div#place-map` with data-lat/lon/zoom/mode/airport/radius-km, airport anchors with data-icao/lat/lon/name, control ids, `place-status`, script-gate classes, fallback text, `details#details` always open in markup).
- Airports: all 272 as anchors sorted by municipality with a `list-filter.js` filter and a GET `?q=` narrowing; `?airport=` selects server-side (an unknown code is ignored; wins over a carried `mode`; first runway or the saved one preselected; pin, label prefilled from the airport unless it already is the stored place). Legacy Orly ids show as LFPO and post back unchanged.
- `detection_actions._rerender(handler, ctx, device, errors, form, status)` renders `place_page` for every refusal (400 for save_place, 200 for the older actions) with the map policy; new `frame_place()` reads `fleet_db.frame_position` (hides a foreign-owned row from a non-admin, tolerates sqlite errors). `place_errors_html` from 61-20 is gone; field errors now sit beside real controls, older-form errors are listed above the cards.
- CSS: additive `.place-*` rules (single column, 24rem + flexible column from 960px, js-gate display via `--js-gate-display`); removed the dead detection-result, panel and location-form rules. 12 new EN/FR strings under `detection.*` ids (the i18n area rule requires an existing module name, so not `place.*`).

## Tests

New `test_place_page.py` (37: order, FR, data contract, controls, one csrf form, no saved-locations UI, legacy runway, hostile text, both save modes, 400 refusals with aria-invalid/describedby, escaped echo, toast EN/FR, exact policy headers on refused save_detection/save_location/save_place) and `test_browser_place_page.py` (11: scripts-off with both hosts aborted and no request to either; layout at 360/1280 x EN/FR x light/dark with hit-testing, card order, two columns, no overflow; no-script layout). Waits for `document.getAnimations()` to finish and for a control to own its centre before measuring. `test_detection_page.py`, `test_detection_position.py`, `test_browser_detection.py`, `test_config_page_05.py` updated in place for the new structure (removed assertions are only for removed subjects: bearing line, 20-row cap sentence, saved-locations list/form/edit link, hidden-panel rule, Back to Display link). New browser file ran 3x green.

## Gates

ruff, mypy (29), comment-history, function size (none over 80), Phase 47 freeze (21 passed): clean. `render_baseline.json`, sign-in digests: unchanged (the Detection page is not pinned). Full `companion test-support stub-server -n auto --no-cov`: 7007 passed, 4 skipped (root permission bits), 10 failed, all in `companion/test_browser_space_switch.py` (a file I did not touch; it had a concurrent edit in the tree). Re-run alone: 24 passed, so load flake.

## Deviations

1. `render` has no `flash_place` parameter (the toast takes the place from page_context, as 61-20 built it) and gains `place`.
2. The old summary rows (text on the frame, when nothing is in range) are kept in the status card so existing tests stay valid.
3. Airport list rows use their own `.place-airport` styling, not `entity-row` (its 960px column grid does not fit a 24rem column).
4. i18n ids use the `detection.` prefix (stable-shape test).
5. Radius sits in What to follow only (one control, id `place-radius`), not repeated in details.
6. `icon-locate` is not yet in the sprite; `icon_html` renders nothing for it until the map plan adds it.

## Notes for 61-26

The Nominatim `fetch` must use `referrerPolicy: 'origin'`. The script should add `map-ready` to the html element and close `#details`. Airport anchors carry `data-detection-nav`; dirty-state.js then appends live mode/radius to their href (server lets the picked airport win over mode).

## Known Stubs

Map, search and locate controls are gated containers only (wired by the next plan); the fallback explanation shows until `map-ready`.

## Self-Check: PASSED
