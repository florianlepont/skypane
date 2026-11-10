# Phase 61 Plan 105: Round 16 (chip counts, Location map as document content) Summary

Two separate commits: `1d0acb4e` (W172, chip counts) and `74f5d1ae` (W171, Location map plan B, revertable alone).

## W172 - counts removed from the filter chips (1d0acb4e)

- Flights chips are now "All / Departures / Arrivals" ("Tous / Départs / Arrivées"); Airlines collection chips and the shared `ui_filter` chip group lost their numbers too. `history_query.Result.chip_counts` is gone, `history_page` no longer renders counts, `list-filter.js` no longer repaints them, the `.filter-chip__count` / `.is-zero` CSS is removed. The empty-search state is unchanged in behaviour (it already keys off the rendered rows and `total`).
- Chips got `min-width: 44px` on the Airlines collection strip (without the number the label fell to a 29px hit area).
- Kept: the "N flights" / "N flights match" status line on Flights (screen-reader only, it is the information itself), the "N of M shown" line of the filter bar, the Audit "N entries" line, the pending counts of the Airlines/Health lists, "Notes (N)", "Other frames (N)" and the cluster title (disclosures and tooltips, not chips). Audit chips and the Users/Fleet strips never carried counts.
- Tests retargeted: chip labels are plain with no digits; counts asserted through the status line and the listed cards (50/40/10, 5/4/1, 49); a new 360px test (EN and FR) asserts the three chips fit on one row, uncut and 44px tall. Components page entry and its French text no longer say "with counts". Render baseline updated.

## W171 - Location map as document content on phones (74f5d1ae)

Below 960px:
- `.page-content` of the Location page is `position: relative; height: 100lvh; overflow: clip; padding: 0`; the place page/stage keep `100dvh`, so header, search row, chips, offer, sheet and the shared fixed tab bar sit exactly where they did (measured before/after at 390x844 and 360x740, both themes).
- `.place-map` is `position: absolute; inset: 0 0 auto; height: 100lvh` inside the stage (stage overflow is `visible` on phones; the page container clips). The map is therefore ordinary document content reaching the physical bottom, not a fixed layer.
- `body` (map ready, and while loading) is the tile ground colour; `html` stays the theme surface so theme tooling keeps working. `.place-boot` is `position: absolute`, ground colour, `100lvh`, and the app bar is absolute in the loading state as in the ready state.
- Desktop (>= 960px) unchanged: the map is still fixed (asserted).

Technique for the bottom: the container is exactly `100lvh` (the largest viewport, which spans to the physical bottom edge when the toolbar collapses) rather than `100lvh + env(safe-area-inset-bottom)`. The extra inset would make the document scroll by about 34px even with no toolbar and would be clipped by the container anyway; the leftover below the map (if any) is the ground-coloured body, not a flat band. When the toolbar is shown, lvh > dvh, so the document may scroll by that difference natively (standard iOS behaviour); nothing scrolls where lvh = dvh (desktop, tests).

Not verifiable without an iPhone. The effect (the map under Safari's bottom bar, no band) cannot be reproduced in headless Chromium, where lvh = dvh. One-line owner check: open Location in a Safari tab on the iPhone and look at the strip under the tab bar: it must be map, not a flat colour. If it is still a band, revert `74f5d1ae` alone.

Tests: new `companion/test_browser_place_document_map.py` (map absolute, inside the container, 0..window height, no document scroll, ground colour, floating-part positions vs the measured before values, pan by drag, wheel zoom, tap/drag of the pin, loading placeholder, desktop still fixed; 390 and 360, light and dark). The overhaul sweep's warm-fill rule now also exempts the Location body (the tile ground colour, as it already did the map box). Render baseline updated.

## Deviations

- [Rule 1] Airlines chips fell below 44px wide after the count went: fixed with `min-width: 44px` (same commit as W172).
- [Rule 3] The warm-fill sweep rule exempts the Location body behind the map (W171 commit).
- `html` background left at the theme surface (not the ground colour) because the `_set_ui_theme` helper requires the canvas to differ between themes; the ground colour is on `body`, which paints the full window height.
- Two untracked wheel files (`greenlet-*.whl`, `playwright-*.whl`) sit in the repo root from before this plan; they were not touched or committed.

## Gates and tests run

ruff, mypy, check_comment_history, check_function_size, `stub-server/test_phase47_freeze.py`; `companion/app.py` is 1486 lines, no JS file grew. Browser/unit files: see the hand-back. Full suite not run (cadence).
