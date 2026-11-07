# Phase 61 Plan 88: Location full-bleed, loading state and in-place airport pick Summary

Owner decision D47 R9-7 (W122, W123, W124): the Location page's first moments and its airport pick, in one commit.

## What changed

- **W124, full-bleed on a phone:** the map box is `min-height: 100lvh` (the largest viewport, so it also runs under the browser's toolbars and the bottom safe area, which a box sized to the smallest viewport leaves uncovered) and carries the placeholder colour itself; with the map running, `<html>` takes the same colour (`--color-secondary`), no sky gradient and `overscroll-behavior: none`, so no pale page can show above, below or on a bounce. The app bar still floats over the map with its soft scrim; the sheet and the Save bar still sit above the tab bar.
- **W122, loading state:** `companion/pages/place_page.py` renders `div.place-boot` first in the stage: a thin progress bar (one finite 2 s growth that holds at 92%), shapes of the search field, the two mode chips and the sheet with the existing finite `.is-loading` shimmer (6 iterations), and the loading note with the bounded spinner (the 61-82 note, same words). The head script `splash-boot.js` now puts `js-early` on `<html>` before the first paint whenever scripts run; `html.js-early:not(.map-ready)` shows the loading state and hides the plain form, the explanation and the page header; the state is hidden again as soon as `map-ready` is set. With scripts blocked `js-early` never exists, so the form stays fully usable and the loading state never shows. A 6 s cap in the head script, and `place-map.js` when the library is missing or the map fails, remove `js-early`, so a page whose map never starts falls back to the plain form instead of loading forever. Desktop keeps the sidebar column clear and shows the card's shape at the left (z-index below the page so the sidebar and app bar stay on top). Accent fill of the bar only exists under the early class (the no-script accent-budget probe reads computed styles).
- **W123, airport pick in place:** `chooseAirport` (suggestions, typed airport code or name, airport pin, nearest-airport offer) no longer navigates. It switches to Airport mode, moves the pin, the label and the coordinates, flies the map to the airport, fetches the page's own `?airport=` URL (same server data and validation, same-origin) and swaps the new `#place-runways` group (airport header, runway cards, hidden `airport` field, hint) for the one rendered; dots are redrawn (the followed airport is highlighted), the form guard counts the differences (Save appears, saved result unchanged until Save), the address is updated with `history.replaceState` (`?airport=..&mode=runway&radius_km=..`, as the page's own navigation produced), the search field is cleared, the status line names the airport. Cancel after a pick restores the opened runway group, the opened address, the pin and the fields in place. If the fetch fails or the browser lacks `fetch`/`DOMParser`, the old page navigation runs. The plain form (list links, GET filter, POST save) is unchanged.
- `#place-runways` (`display: contents`) wraps the runway group in the markup; no new strings (the existing "Loading the map…" / "Chargement de la carte…" is reused).

## Tests

New `companion/test_browser_place_boot.py` (17): map rect covers the viewport and `elementsFromPoint` at the corners and bottom edge hits the map, html colour equals the map colour, no document scroll, bottom-corner pixels are not the page's sky colours (390 and 360, light and dark); loading state present at first paint with the map script held (phone and desktop, light and dark, no infinite animation), French note, gone after ready, absent and plain form complete with scripts blocked, plain form returns when the script never answers; airport pick from suggestions (phone and desktop) and from a pin: no document request, window marker survives, loading state never reappears, cards/fields/mode/address/Save update; fallback navigation when the fetch fails; radius kept, leave guard armed, Cancel restores in place.
Updated in place: `test_browser_place_map.py` (the follow offer picks in place), `test_browser_detection.py` (the carried-state and bfcache tests still exercise the page-local navigation, now through the airport list's own link, since the map's picks no longer navigate).

Screenshots: scratchpad `shots88/` (loading 390 and 1280, light and dark; loaded phone; picked 390 and 1280; phone full-bleed 360 and 390, light and dark).

## Deviations from Plan

- The iOS toolbar grey band cannot be reproduced in headless Chromium; the fix follows the stated causes (box sized to the small viewport, page colour differing from the map) and the tests pin the geometry and colours, not a device.
- The progress bar is a finite CSS growth (no real progress events): the motion budget requires durations from the motion tokens.

## Known Stubs

None.
