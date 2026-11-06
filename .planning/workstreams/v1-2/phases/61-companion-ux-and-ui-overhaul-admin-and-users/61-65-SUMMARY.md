# Phase 61 Plan 65: Location page, full-bleed map, compact panel, airport pins, tap to place, suggestions Summary

The Location and detection page now lets the map dominate on a phone: it runs under the status bar and the app bar (with a soft fade behind the bar), the bottom sheet is at most 28% of the viewport, every airport of France is drawn as a tappable pin in Airport mode, a tap on the map places the pin in My position mode (with a hint until placed), and typing in the search field lists matching airports instantly from the page's own catalogue while addresses are looked up only on submit and listed in the same suggestion list.

**Requirements:** W65, W66, W67, W68, W69 (owner feedback round 6)

## Root cause of the missing airport pins (W66)

The 61-41/61-50 dots were drawn, but invisible:

1. The mark (`.place-dot__mark`) is a `span` inside a Leaflet marker box. The library's own marker rule forces that box to `display: block`, so the page's `display: flex` on `.place-dot` never applied and the span stayed `display: inline`: its 12x12 size was ignored and only a 4x19 px sliver of its white border painted (measured). The existing test only measured the 44 px hit box, never the mark.
2. A zoom floor (`DOT_MIN_ZOOM = 8`) hid every dot at the overview zoom (5), and at an airport's zoom (13) only the airports in view were drawn, the followed one under the pin.
3. The script read its airports from the list anchors, which the server filters when the URL has `?q=`.

Fixed: the mark is `display: block; position: absolute` and centred; no zoom floor; the whole catalogue (about 20 KB, 272 rows) rides on `#place-map` as `data-airports`, independent of the list filter; a browser test asserts the marks are at least 10 px and the hit boxes at least 44 px.

## What changed

- `companion/static/style.css`: `--place-top` (52 px + safe area on a phone, 0 on desktop) moves every floating part below the bar; the app bar floats (`position: absolute`) over the map with a `::before` fade of `--color-canvas` (85% to transparent, 24 px below the bar; a radial glow at the top right on desktop); sheet capped at 28dvh; 64 px runway chips (name, "Runway N" pill, length/surface only in the title and for assistive technology, sideways scroll beyond three runways); one-line airport header with ellipsis; one-row radius; the follow offer is its button on a phone; the status line is read aloud, not shown; no glass box behind the two mode chips; the suggestion list is a glass panel of 52 px rows with an active-row outline; pin marks, IATA labels (from zoom 6, hover, always for the followed airport) and the bigger accent mark for the followed airport.
- `companion/static/place-map.js`: catalogue from `data-airports`; pins for every airport in Airport mode only (none in My position mode, so a tap always places the pin); a pin or a suggestion navigates through a `data-detection-nav` link built from `data-airport-url`, so the form guard carries mode and radius exactly like the list; combobox/listbox suggestions (2+ characters, up to 6, exact code, code prefix, name or municipality prefix, word prefix, any part; arrow keys wrap, Enter, first Escape closes the list and keeps the text); address results (up to 5) in the same list; choosing one switches to My position and places the pin; the tap hint hides once a pin exists; the chosen runway chip scrolls into view.
- `companion/pages/place_page.py`: `data-airports`, `data-airport-url`, the tap hint element, the runway chip title; `companion/i18n_fr/detection.py`: "Touchez la carte pour placer le point", "Aéroport".
- `COMPLIANCE.md` (Nominatim): typing lists airports from the local catalogue only; addresses on submit only.
- `61-UI-SPEC.md` section 9.0c, `61-STEP-COUNTS.md` (L1-pin).

No new route, no CSP change (connect-src stays self plus Nominatim, tiles on this page only), no change to the POST form, fields or access rules. `companion/app.py` untouched.

## Step counts

L1 4, L2 4, L3 5, L4 3 unchanged (measured by the existing tests, which pass). New L1-pin: Location tab, tap the airport's pin, Save = 3, one better than L1.

## Tests

Adapted in place, none weakened:
- `test_browser_place_page.py`: the sheet bound is 28% (was 40%), the map must start at the viewport top and the search field below the app bar, runway chips at most 72 px tall.
- `test_browser_place_map.py`: `_tap_map` first chooses My position (Airport mode now draws tappable pins, so a bare tap there may select an airport); the circle test taps in My position, then checks the circle is gone in Airport mode and back in My position; the dot test renamed `test_airport_pins_choosing_one_follows_its_link`.
- `test_browser_overhaul_steps.py`: `L1-pin` measurement added.

Removed: `test_no_dots_show_at_the_overview_zoom` (it pinned the behaviour the owner rejected; replaced by the fresh-page pin test).

New `companion/test_browser_place_pins.py` (6 tests): at least 100 pins on a fresh 390x844 page with round marks and 44 px hit boxes, tapping one selects it (URL, mode, hidden field, chosen line, chips, followed pin) with no geocoder request; My position (EN/FR, 360 px, no overflow) has no pins, shows the hint, a tap places pin, circle and fields; typing "ory" lists Paris-Orly first with zero geocoder requests, 52 px rows, combobox/listbox roles, arrows, Escape, Enter picks; a submitted "Lyon" (FR) sends exactly one request, lists the two results, choosing one switches to My position and places the pin; the map starts at the top under a gradient-faded bar.

## Deviations

- A bare tap on the map in Airport mode still places the pin as before (not changed); with 44 px pins it may select an airport instead, which is the intended meaning of a tap near a pin.
- Cancel stays beside the full-width Save (the shared dirty bar), not removed.
- Screenshots: `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots65/` (before-* and after-*, phone 390x844 and desktop 1280x900, light and dark, airport with pins, position, suggestions open). Tiles are the flat grey test tile.

## Known Stubs

None.

## Self-Check

Gates and the full-suite result are in the final report.
