# Phase 61 Plan 62: Flights filter and rows, collection control bar, compact Personalisation Summary

Owner round 6 (W57 to W60, real iPhone screenshots of the deployed refined design) is answered: the Flights direction filter is a true single-line centred control level with its search button, each Flights row has one lead control (the render thumbnail) instead of a chip plus an image button, the Airline collection's four stacked controls are one two-line bar with a sort menu, and the whole Personalisation look picker fits one phone screen above the tab bar.

## What changed

- **W57 segmented filters** (`style.css`, shared `.filter-bar__chips` / `.filter-chip`). The track is 44px with an inset edge and no padding; each segment is a 44px label (the target) holding a pill inset 3px; the pill is a centred flex row (both axes, `text-align: center`) with label then count on ONE line ("Tous 45"). The collapsed search button is the same 44px on the same centre line. Audit log chips keep their old 46px pill (`.audit-chips`). Fits at 360px in French.
- **W58 Flights rows** (`history_page.py`, `style.css`). One lead element per row: `a.history-card__thumb` (44px target, the existing `/gallery/` link and lightbox trigger, same accessible name) holding a 40px rounded thumbnail of the archived render with an 18px rotated plane glyph on its corner; with no render the 40px plane chip (not a control). The separate image button is removed. The label wraps (callsign never breaks, route moves under it as a unit) and the detail wraps to two lines, so "KEF"/"Corsair · A330-9..." stay readable at 390px.
- **W60 Airline collection bar** (`airline_collection_page.py`, `ui_base.py`, `style.css`, `i18n_fr/airlines.py`). Line 1: filter field (flex 1), sort as a 44px icon button (`icon-sort`, name "Sort by: {current}") opening a `<details class="row-menu collection-sort">` panel of radio rows with a tick (Most seen, Rarest, Latest, A to Z), and the legend info button; line 2: the segmented filter (scrolls sideways if needed). From 700px everything is one line. Script: radios carry `data-autosubmit`; no script: the visible Apply button sends the choice. New "Rarest" order (fewest sightings among seen airlines first, unseen last); FR "Les plus rares".
- **W59 Personalisation** (`style.css`). Swatches drawn 32px inside 44px targets (ring hugs the swatch, hit area via negative row margin so the 44px box is kept); background and band segmented controls are 40px with 44px option targets (pill drawn by `::before`); phone preview 5.25rem (84px); tighter picker, foot and section spacing. Save ends 134 to 152px above the tab bar on 390x844 and 30px above it on 360x740 (room for one more wrapped line if another font is wider).

## Tests

New: `test_the_flights_filter_bar_shares_one_height_with_its_search_button` and the extended centring test (360/390/1440, EN/FR, 1px on both axes, now also `.look-seg__option` and the collection/Flights segments) in `test_browser_segment_centring.py`; `test_the_whole_look_picker_fits_one_phone_screen_above_the_tab_bar` (390x844 and 360x740, EN/FR) in `test_browser_personalisation.py`; sort-menu, line-one/line-two geometry and Rarest assertions in the collection tests.

Updated in place (none weakened, none removed): `test_flights_cards` (thumbnail lead; chip lead without a picture), `test_view_pages_03` (the old pin "label and detail ellipsise on one line" is replaced by the new rule the owner asked for: label wraps, callsign and route nowrap, detail clamps to two lines), `test_browser_flights_cards` (thumbnail selector, unclipped label/detail, at most one control per row, range-based centring), `test_browser_airline_collection` and `test_airline_collection_page` (sort menu instead of select), `test_companion_app_01` (52 icons), `test_sign_in_surfaces` digests, `render_baseline.json` regenerated deliberately. Flaky `test_browser_auth0::test_a_cancelled_sign_in_is_calm_and_offers_sign_in` fixed at the root: `_geometry_ok` now waits for every linked stylesheet to be loaded and for each control's computed `min-height` to be its styled 44px before measuring (the assertion itself is unchanged, no tolerance).

## Step counts

Unchanged (U4a/b/c 3, V1 2 and 1); see `61-STEP-COUNTS.md`. UI-SPEC revision 5 added.

## Deviations

- The thumbnail is the archived render the lightbox opens (the only illustration a Flights row has), not the airline artwork.
- `.look-dot:has(input:checked)` keeps a small `cursor: default` declaration so the existing stylesheet test that requires the live-checked rule still holds; the ring itself moved to `::before`.

## Screenshots

`/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots62/` (`flights|collection|personalisation-phone-{light,dark}-fr-{before,after}.png`, 390x844, French).

## Verification

ruff, mypy, comment-history, function-size and `test_phase47_freeze` green; `companion/app.py` unchanged (1473 lines). Full suite `companion test-support stub-server -n 4`: 8419 passed, 4 skipped (root-permission skips), 0 failed (a first run showed 16 failures, all fixed: swatch hit areas, chip overflow at 360px, three pinned tests).
