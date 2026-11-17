# Phase 61 Plan 121: More panel blur coverage Summary

While the More sheet is open, the Location map's lead and tail (the parts above and below the window that iOS draws under the status bar and the toolbar) now carry the same dim and blur as the fixed scrim. Not confirmed on an iPhone.

## Commit

- `310507e0` fix(61-121): dim and blur the Location map above and below the page behind the More sheet

## Cause

The scrim is `body:has(.tab-bar__more[open])::after`, fixed, `inset: 0`, `z-index: 44`: it covers the layout viewport exactly (verified on Home, Flights and Location at 360 and 390, EN/FR, light/dark, forced 59px/34px insets; it is the topmost thing at y=2 and y=innerHeight-2). On an iPhone the Location map is document content that runs 80px above and 80px below the page (`place-lead`); iOS shows that document part under the status bar and a tab's toolbar, and a fixed box is not painted there. So only the middle band was blurred. Hypothesis from geometry; the strip the owner measured (about 140px) is larger than the 80px lead, so part of it may be Safari's own chrome zone (see below).

## Change

`companion/static/style-place.css`: with `place-lead` and the sheet open, `.page-content:has(.place-stage)::before` (height `--place-lead`) and `::after` (height `--place-tail`) are absolute, `z-index: 1`, same colour and `blur(8px)` as the scrim. Nothing is painted when the sheet is closed, on other pages, or in browsers without the lead; the closed-panel top-edge work of the earlier Location plans is untouched.

## Tests

`companion/test_browser_more_scrim_cover.py` (new, 34 cases): every page (Home, Flights, Location) at 360/390, EN/FR, both themes: scrim fixed, blurred, window-sized, topmost at the first and last rows; Location with the iPhone flag: the scrim plus the two layers leave no part of the map undimmed, layers carry blur, and none exist once the sheet closes; at 1280 there is no scrim. The Location case was red first (8 failures), then green; the file ran 3 times in a row with no failure. Render baseline regenerated.

## Tests run

ruff, mypy, check_comment_history, check_function_size, phase47 freeze, test_stylesheet_structure (a duplicate-selector failure from my first draft was fixed), test_stylesheet_load_order, test_components_page, test_browser_ux_02, test_sign_in_surfaces, test_suite_guards, test_browser_more_sheet, test_browser_place_document_map, test_browser_location_full_bleed, test_browser_web_app_bar, test_browser_page_opening, test_browser_flights_search_more.

## Not verified / if still seen

If the owner still sees a sharp strip of about 140px at the top, the lead (80px) is shorter than the zone iOS shows; raise `--place-lead`/`--place-tail` (they only matter on the Location page) or extend the layers. Only a device can confirm. Console row not touched.
