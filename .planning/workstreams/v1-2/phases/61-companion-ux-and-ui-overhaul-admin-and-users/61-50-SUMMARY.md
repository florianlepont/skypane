# Phase 61 Plan 50: Location page rebuilt to mockups L1-L3 Summary

The Location and detection page is now usable on a phone and big on a desktop: the map fills the page (edge to edge between the slim app bar and the tab bar, the whole content area on desktop), one floating search field takes an airport code, an airport name or an address, the mode chips sit under it, and a compact bottom sheet (never above 40% of the viewport) or a 360px card carries the airport and its runways in three columns or the radius, with Cancel and Save inside. The round locate button works, the coordinates line and the saved-settings disclosure are gone, and the map credits sit behind a discreet round "i".

**Requirements:** D36 (W25, W40-W45)

## What changed

- `companion/pages/place_page.py`: new structure `.place-stage` > `#place-map`, `.place-float` (the one search form and its results) and `.place-panel` (an overlay holding `.place-card` = mode switch + `.place-sheet`, the "i" button with its credits popover, and the locate button with its message pill). The airport filter and list stay in the markup (the no-script page uses them; the map reads the list's anchors, which now carry `data-iata`); the dirty bar (Cancel / Save) moved inside the sheet. Removed: the summary line, the "Saved setting and map credits" disclosure, the empty-state line, the old status card. `#details` is kept (same fields, ids, POST route and validation) with a "Back to the map" link.
- `companion/static/place-map.js`: a submitted search that equals an airport's ICAO or IATA code or whole name (case, accents, spaces folded) opens that airport's page from the page's own list, no request; anything else uses the existing Nominatim-on-submit flow. The locate button now switches to My position, places the pin, draws the circle, recentres, and reports in a visible pill on the map (and the status line); refusal, error and timeout show a short message, with a guard that frees the button if a browser never answers. The "i" popover (Escape or an outside tap closes it) replaces the library's attribution strip. `coveredBy` uses the search field and chips (top) and the sheet (bottom) on a phone and the card on desktop; a sheet that changes height only moves the pin if it would end up under it. Notes (no result, failed, too short) go after 8 s and never block taps; Escape or a map tap closes a result list. Removed the derived-line and details-toggle code.
- `companion/static/style.css`: the place layout block rewritten (tokens only). The page content becomes a flex column of `100dvh - 52px - 57px - safe-area` on a phone, so a docked warning shrinks the map and never pushes the sheet under the tab bar; on desktop it is `100dvh` and takes back the shell's column gap to meet the sidebar. Chips on a phone, segmented switch inside the card on desktop; runway cards three to a row; sticky Cancel / Save in the sheet. `#details` shows over the map only when targeted or when a refused save has an error in it. W41: `.filter-chip` has `min-width: min-content`, so the Departures / Arrivals / All count tabs no longer clip a label ("DEPARTU...") and their text is centred.
- `companion/i18n_fr/detection.py`: search label, placeholder, help, no-result and failed sentences changed; "Back to the map" added; the saved-settings title and the empty-state strings removed.
- `COMPLIANCE.md`: the OpenStreetMap section records the "i" popover (owner decision) and flags that the tile policy's "visible attribution" wording should be re-read at the next terms check.
- Docs: `61-UI-SPEC.md` section 9.0b, `61-STEP-COUNTS.md` (L1 and L2 text), `61-TRACEABILITY.md`.

## Step counts

L1 4, L2 4, L3 5, L4 3: unchanged against the 61-41 values (L1 now types the code in the one field and taps Search; L2 also switches the mode). No row got worse.

## Tests

Adapted in place, none weakened: `test_place_page.py`, `test_detection_page.py`, `test_detection_position.py`, `test_display_detection_card.py` (the removed summary text is replaced by what the page still shows: chosen airport and codes, checked runway card, the place fields' values; the removal itself is asserted), `test_empty_state_scale.py` (the Location page has no empty state of its own; its filter "no match" state is measured instead), `test_browser_place_map.py` (details reached by their `#details` target, the credits popover, controls list, locate), `test_browser_place_page.py` (geometry for sheet / card at 360x844, 360x640, 390x844, 1280; sheet at most 40% of the viewport, no page scroll, map between the bars, three-column runway cards, search separate from the card, label centring), `test_browser_place_search.py` (airport code or name selects the airport without a request, other text is looked up), `test_browser_detection.py`, `test_browser_overhaul_steps.py`, `test-support/place_map_support.py`. New: locate tests at 360 and 1280 with a mocked geolocation (context geolocation and permission) proving the pin, the mode switch, the circle, the message and the pin in the clear part of the map, and a refusal test; `test_browser_segment_centring.py` (label boxes against segment boxes on the flights, airlines, Personalisation and account pages at 360 and 1280 in both languages).

## Deviations

- W43: the cause of "does nothing" could not be reproduced headless (the existing mocked-geolocation test already passed). Likely causes were a result that placed the pin without a visible change (the mode stayed Airport) and a message buried in the sheet; both are fixed, with the extra timeout guard. Real-device confirmation by the owner is still needed (iOS needs HTTPS and the permission prompt).
- The credit is behind a one-tap "i" as the owner asked; `COMPLIANCE.md` used to say "not hidden behind a toggle" and now records this decision and the re-check.
- No zoom buttons on a phone (pinch zooms); they stay on desktop. Cancel and Save appear when something changed (the dirty bar), not permanently.
- The no-script column keeps the airport filter, list and open details block; the "Details" block is the same `#details` element, not a new one.
- `companion/app.py` untouched (1473 lines).

## Known Stubs

None.

## Self-Check

See the final report for the gates and the full-suite result.
