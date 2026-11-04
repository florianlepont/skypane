# Phase 61 Plan 41: Location and detection rebuilt as sketch V1 Summary

The Location and detection page is now a full-page map with a floating mode switch (Airport / My position) and search, one panel (bottom sheet on a phone, a card at the left of the map from 960px), coordinates and time zone as a small read-only line, and the map recentring on the uncovered part. The no-script form is unchanged in fields, route, validation and access.

**Requirements:** D28 (D18, D19, D20 behaviours kept)

## What changed

- `companion/pages/place_page.py`: the five cards are gone. Markup is `.place-stage` holding `#place-map`, `.place-float` (mode switch radios `place-mode-runway` / `place-mode-area`, the search form, the results list), the round locate button and `.place-panel` (airport filter and list, chosen airport with runway cards, radius block, nearest-airport offer, notice, status line, the `#details` disclosure whose summary is the read-only "lat · lon · time zone" line, and a closed "Saved setting and map credits" disclosure). The same fields, ids, POST form (`action=save_place`) and `?airport=` / `?q=` GET navigations as before. The "settings" tile does not exist any more.
- `companion/static/place-map.js`: the ready class is set before the map is built (the library measures the stage), the zoom control sits at the top right and the credit at the bottom right (desktop) or top left under the controls (phone), `centreOn` puts every placed pin in the part of the map the panel does not cover (card width on desktop; floating controls and sheet on a phone), the derived line and a pointer-only radius range follow the fields, and a mode change re-centres.
- `companion/static/style.css`: the old place layout CSS is replaced (tokens only, no colour literals); the mode switch, stage, float, sheet and card rules, the focus-driven airport list, the privacy line that floats without moving the layout.
- `companion/static/dirty-state.js`: a section label shared by several wrappers is named once (the mode switch and the follow block are both the "Detection" section).
- `companion/i18n_fr/detection.py`: new and changed strings (Airport / My position, mode switch label, search placeholder, more/credits title, area heading); unused ones removed.
- Docs: `61-UI-SPEC.md` section 9.0 (revision 3 wording, 9.1 marked history), `61-STEP-COUNTS.md`, `61-TRACEABILITY.md`.

## Step counts (honest)

L1 5 to 4, L2 5 to 4, L3 6 to 5, L4 4 to 3: all meet their targets now. L4 taps the part of the map nothing floats over. A6 (2 against 1) is still missed.

## Tests

Adapted in place, none weakened: card-order and French-label tests in `test_place_page.py`, container checks in `test_place_map_assets.py`, radiogroup check in `test_detection_page.py`; browser layout tests now measure the stage/sheet/card geometry, 44 px targets in both modes at 360 and 1280 px, both themes and languages, with and without scripts; the map tap tests use the clear part of the map (`CLEAR_BOX` in `test-support/place_map_support.py`); the airport dot test picks a dot in the clear part; the detection browser tests flip to Airport mode before using the airport filter and to My position before the radius; `MEASURED` step counts updated. `render_baseline.json` and sign-in surface digests regenerated deliberately.

## Deviations

- The Save bar stays the existing dirty bar (floating above the tab bar) instead of buttons inside the sheet: same Save/Cancel behaviour, tests and no-script path. On a phone the sheet gets extra bottom padding while the bar shows.
- In My-position mode the airport filter is not shown (sketch v1b shows only the radius); the mode switch is one tap away, and the "Follow <airport>" offer under the pin still works.
- The radius keeps its number field (keyboard path) and gains a range slider that is pointer-only (`aria-hidden`, `tabindex=-1`), no big "15 km" readout.
- The phone has no drag handle (it would imply a gesture that does not exist).

## Known Stubs

None.

## Self-Check

See the final report for the gates run.
