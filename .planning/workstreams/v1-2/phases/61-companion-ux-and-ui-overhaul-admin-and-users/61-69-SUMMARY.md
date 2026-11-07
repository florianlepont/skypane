# Phase 61 Plan 69: Location map opens on the airport, numbered clusters, runway badge in the corner Summary

The Location map now opens centred on the frame's airport (zoom 12) even when no place is saved, groups airports into numbered bubbles while zoomed out, keeps the followed airport as an always-visible individual pin, and the runway cards' "Current" badge straddles the card's top-right edge so it never covers the designator at 360 px.

**Requirements:** owner decision D42 P05; audit findings F05, F10, F11

## What changed

- `companion/static/place-map.js`: opens on the followed airport at zoom 12 when there is no saved pin (saved pin behaviour unchanged); plain-JS grid clustering (64 px cells in world pixels of the current zoom, clustering up to zoom 11, none above); every airport is either one pin or counted in exactly one bubble; the followed airport is always an individual pin with a raised z-index and its label; tapping a bubble zooms to its bounds (at least one level in, at most 12). Rebuilt through the existing keyed diff on `moveend zoomend`, so panning does not recreate markers. No library, no network, CSP unchanged.
- "Show all of France" (`#place-france`, in the map tools beside the locate button, 44 px, bilingual "Voir toute la France") returns to the fit-France view (zoom 5).
- `companion/pages/place_page.py`, `companion/i18n_fr/detection.py`: the button, bubble title string; `CATALOGUE_ZOOM` 13 -> 12.
- `companion/static/style.css`: `.place-cluster` bubble (36 px mark in an even 44 px box, tokens only), `.place-france`, runway badge as a pill straddling the card's top-right edge (the phone chip row got top padding so it is not clipped); selected badge uses tokens in both themes.
- The dark-theme ORY label chip (own surface) from the earlier plan is kept.

## Tests

New `companion/test_browser_place_clusters.py` (6 tests): opens centred on ORY at zoom >= 12 with no bubbles; zoomed out (EN/FR) bubbles show numbers >= 2 and bubbles + pins equal the catalogue size, ORY pin visible, labelled, >= 44 px, owns its centre; tapping a bubble raises the zoom, and the followed pin stays visible and tappable at every wheel zoom level (about the pin) and after Show all of France; the "Current" badge does not overlap the designator at 360 px in EN and FR.

Adapted in place: `test_browser_place_pins.py` (reaches a pin via Show all of France), `test_browser_overhaul_steps.py` (L4 taps away from the airport pin that now sits at the map centre; L1-pin measured 4 = Show all of France added), `test_place_page.py` (data-zoom 12), `61-STEP-COUNTS.md` (L1-pin 4).

## Deviations

- Show all of France is a page button in the existing map tools (not a Leaflet control: bottom Leaflet controls sit under the phone sheet).
- L1-pin is now 4 steps (same as L1) because the map no longer starts zoomed out.
- Render baseline regenerated: no change (the Location page is not in it); no digest or golden moved.

Screenshots: `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots69/` (open, badge, france; EN/FR 360 and desktop). Tiles are the flat grey test tile.

## Known Stubs

None.
