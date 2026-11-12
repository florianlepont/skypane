# Phase 61 Plan 111: Airlines tabs, card picture, splash size, Location top edge Summary

Round 23 of the owner ledger (W176-W178 and the Location top band) closed in four separate commits; W179 only located.

## Commits

- `37cd571e` W177: Airlines tabs and sort switch the list in place
- `52086db9` W176: Airlines card picture uses the card's content width
- `50933d91` W178: opening splash frame at about 62 percent of its size
- `445bfcb2` Location top band: map top edge restored to the good build

## W177 Airlines tabs

Cause: the show chips and the sort radios carry `data-autosubmit`, and list-filter.js answered by `form.submit()`, a full GET navigation, so the page and its opening animation replayed. Flights avoids this with a fetch-and-swap block.

Fix (`companion/static/list-filter.js`, one marker `data-collection-form` on the form in `airline_collection_page.py`): a new block fetches the form's address, swaps the grid, the sheets and the empty cards (`.collection-grid, .collection-sheet, [data-filter-empty], [data-collection-empty]`) in place, finishes the entrance animations of the swapped nodes, keeps the sort menu's accessible name in step, and `pushState`s the address (Back reloads like Flights). The shared tab strip thumb already slides on `change`. Without fetch/DOMParser/history, or without scripts, the form still submits (the Apply button stays for no-JS). The first block of the file no longer caches the empty card and the Clear buttons (they are re-rendered by a swap): the Clear handler is now one delegated listener and the empty card is looked up fresh. `companion/test_view_pages_01.py::test_clear_control_is_wired...` was updated in place for that (delegated `closest("[data-filter-clear]")` instead of a per-button loop).

Test: `test_a_tab_change_swaps_the_list_in_place_without_reloading_or_replaying_the_opening` (360 and 1280, EN and FR): a window marker survives every tap, no `skypane-reveal-fade` animation starts, the checked chip, the card counts, the address and a card opening its sheet after the swap. Verified to fail (4 of 4) with the in-place block disabled.

## W176 Airlines card picture

Cause (git history: `86abdbbe` added `padding: var(--space-md)` to `.collection-card__art`): the card (padding, border) held a second tinted box (art, with its own padding and a 5 percent tint) and the picture also carried the placeholder tint, so three nested surfaces and the picture was 62 px of a 144 px card at 360. Now the art box has no padding or tint and the card image has no standing background (the tint stays on the sheet picture and on the loading skeleton). Picture width: 94 of 144 px at 360 (65 percent, was 43). The New pill moved from `top: space-sm` to `space-xs` so it stays inside the card's top padding, clear of the picture.

Test: `test_the_aircraft_picture_uses_the_cards_content_width_with_no_box_inside_the_card` (360, 390, 1280): picture inset equals the card padding on both sides, width >= 60 percent of the card, aspect ratio kept, art padding 0 and no tint behind picture or art. Replaces the test that required a 28 px inset and at most 82 percent. Screenshots: `scratchpad/shots111/before` and `after` (360, 390, 1280, light and dark).

## W178 splash frame

`.splash__frame` height was `min(46svh, 300px)` (225 x 300 max); it is now `var(--splash-frame-height)` = `min(29svh, 188px)` (62.7 percent), defined once on `.splash` and reused by the caption offset. Centring, 3:4 shape, timing (splash.js untouched, 1.5-2 s plan unchanged), tokens and reduced motion are unchanged. Test `test_the_animated_frame_is_a_small_centred_panel` (360, 390, 1280): 60-65 percent of the old height, 3:4, centred, caption just under it. Screenshots in `scratchpad/shots111/splash-before` and `splash-after`.

## Location top band (iPhone Safari tab)

Method: the top-edge chain of the Location page on a mobile 390x844 profile, rendered from three trees (the good build `75635805`, the round-19 merge `49e2e825` with the page opening, and HEAD), with every element touching the top 70 px, ancestors of the map (position, overflow, transform, filter, contain, will-change, view-transition-name, background), fixed elements, theme-color tags, html classes and scroll height, in both themes, then diffed.

Evidence:
- `75635805` and `49e2e825` are identical (the page opening, #334, changed nothing in this chain).
- HEAD differed in exactly one computed value: `main.page-content` `overflow` `clip` (good) against `visible`, plus the map box (`inset: calc(-1 * var(--safe-top))`, `height: calc(100lvh + var(--safe-top))`) added in `15bd834a` (#336). Theme-color tags (`#E7EEF7`/`#12151D`), html/body/map colours, the header fade, fixed elements (none at the top edge) and the splash were identical to the good build.
- The stylesheet split, the lazy map start and the page-opening rules do not change any of these values.

Fix: restore the good build's rules in `companion/static/style-place.css` (page container `overflow: clip`, map `inset: 0 0 auto; height: 100lvh`) and drop the safe-area offset. Test `test_the_phone_top_edge_is_the_map_from_the_first_pixel_with_nothing_else_painting_it` (360, 390, both themes, with a forced 59 px inset) pins the chain. It passes on the good build `75635805` (run there), fails on the previous HEAD and passes now.

What is verified: the computed top chain, colours and geometry equal the good build in headless Chromium. What only the owner's phone can confirm: that iOS 26 Safari paints no band again. Chromium cannot reproduce Safari's status bar sampling. This is a restoration of the one divergence found, not a proven mechanism; if the band persists, the next step is a Safari Web Inspector check on the device (the html colour behind the map is the page surface, `rgb(233, 238, 245)` light and `rgb(28, 34, 45)` dark, not the map ground `#F2EFE9`).

## W179 logo colour (not implemented)

The orange (accent `#B13F16`, the light-theme text-safe orange) lives in:
- `companion/static/favicon.svg`: the tab icon tile, `fill="#B13F16"` (white glyph)
- `companion/static/apple-touch-icon.png`: pre-rendered 180x180 PNG, fill rgb(177, 63, 22) = `#B13F16`, from `scripts/render_apple_touch_icon.py` line 26 (`<rect ... fill="#B13F16"/>`)
- `companion/test_brand_logo.py` line 104 asserts `#B13F16` in the favicon ("the tile is the accent colour"); `companion/test_contrast_check.py` pins `#B13F16`/`#FF8A5C`/`#E8622C` contrast values and `_SUPERSEDED_ACCENT`.
- Also orange, not a logo: `--color-toast-pending` `#B13F16` (light) and `#FF9A70` (dark) in `companion/static/style.css`.
- The in-page brand mark is not orange: `.logo-mark` uses `--color-text` and `.logo-accent` uses `--color-accent` (`#1F2430` light, `#F2EFE9` dark); the splash logo uses `--color-text`. Only the favicon and apple-touch icon still show orange.
- Documentation of the old accent: `.claude/skills/sketch-findings-skypane` references (not code).
To change the colour: edit the two icon files plus the script and the favicon assertion in `test_brand_logo.py`.

## Deviations

None needing a decision. One existing test was updated in place for the delegated Clear handler, and one (the #336 offset test and the picture inset test) was replaced because it pinned the behaviour this plan changes.

## Tests run

ruff (whole repo), mypy (44 files), `check_comment_history`, `check_function_size`, `stub-server/test_phase47_freeze.py` (21 passed), the render snapshot (`--write`), `test_sign_in_surfaces`, `test_suite_guards`, `test_view_pages_01/03`, `test_companion_app_01/02/03`, `test_status_pages_04`, `test_page_scripts`; browser: `test_browser_airline_collection` (44), `test_browser_motion_unlock`, `test_browser_page_opening`, `test_browser_flights_search_more`, `test_browser_flights_cards`, `test_browser_ux_01`, `test_browser_splash`, `test_browser_navigation_assist`, `test_browser_perf_quick_wins`, and the Location set (`location_full_bleed`, `location_polish`, `place_boot`, `place_compact_sheet`, `place_document_map`, `place_label_clearance`, `place_map`, `place_page`, `place_sheet`, `foundations`, `contrast_edges`, `surfaces`: 229 passed). The new browser tests were stressed with four parallel loops. The full suite was not run (cadence). `requires_non_root` tests were read: the two files carrying the marker do not touch the changed routes.
