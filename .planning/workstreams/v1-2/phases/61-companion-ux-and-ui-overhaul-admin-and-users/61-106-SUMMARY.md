# Phase 61 Plan 106: Compact Location sheet on phones (W175 / D53) Summary

On phones the Location airport card is one compact card of about 123px (was about 170px plus a 100px save strip): the first row is the airport name (one line, ellipsis, the full name as tooltip) with its codes under it and, only while something is unsaved, Cancel and Save at the right; the second row is the three runway chips in one 46px row. No separate unsaved-changes strip covers the map. At 390x844 the clear map between the mode chips and the card is 55.6% of the window height (was about 47% with a pending change). Desktop (>= 960px) is unchanged.

## What changed

- The shared Save bar is not forked. `ui_save_bar.save_bar_html(..., inline=True)` adds `dirty-bar--inline`; below 960px that modifier makes the bar static, surface-less, with compact buttons and a message that is read aloud (still the live `role="status"` line dirty-state.js writes) but not drawn. The Location page passes `inline=True` (`detection_page.dirty_bar_html`), and places the bar in the sheet's grid cell (top right) with CSS; the bar stays a child of `.place-panel`, so tracked fields, the unsaved guard, Enter/Escape and Cancel behaviour in dirty-state.js are untouched.
- Airport mode: name row has a reserved right padding while the bar shows (`--place-actions-w`, sized for the French wording); the municipality is a separate `place-chosen__town` span hidden on phones; chips are 46px with a smaller "Current" tab and the check mark moved to the chip corner.
- My-position mode: no pin icon or hint line when a pin exists; coordinates row carries the same actions; radius is one grid row (label, slider, number input).
- The old rule that lifted the sheet above the separate bar is removed.
- The Location page container now lets the stage shrink by whatever sits above it in the flow (`max-height: 100dvh` instead of a fixed `100dvh`). Without this the in-card actions would be pushed off screen by the out-of-area warning toast (the card was already partly off screen in that state).
- Components page: new state "Save bar, inline in a card (phones)" (EN/FR) and a catalogue note in the sketch-findings skill.
- Render baseline regenerated.

## Tests

- New `companion/test_browser_place_compact_sheet.py` (390x844 and 360x740, light and dark, EN and FR): airport mode with a pending runway change (actions inside the card, one-line name with title, codes whole, chips in one row of 44-52px and uncut, card height <= 135px, no overlap with tab bar, map tools or pin, clear map share >= 55% at 390x844 and >= 47% at 360x740 where the fixed top and bottom parts leave less), position mode with a pin and a changed radius (coordinates row plus radius row, actions in the card, no overlaps), and Cancel restoring the saved runway.
- Updated in place: `test_browser_place_page` (sheet floats just above the tab bar; save bar inside the sheet), `test_browser_place_sheet` (bar inside the card above the tab bar), `test_browser_save_bar` (phone Location bar is the compact in-card form: geometry equality with the fleet bar is skipped for it, order/text/size/role checks kept), `test_browser_place_document_map` (sheet positions of the compact sheet), `test_browser_contrast_edges` (header is one line with a tooltip, codes whole), `test_browser_round11_fixes` (card is the opaque surface on phones), `test_detection_page` (visible text compared with white space collapsed; bar carries the inline modifier).

## Deviations

- [Rule 1] The out-of-area warning toast pushed the card off screen on phones; fixed with the `max-height: 100dvh` change above.
- The phone 360x740 clear-map share cannot reach 55% (the header, search and chips, tab bar and card alone take more); it is asserted at 47%.

## Not done

No iPhone check; full suite and `run-all-tests.sh` not run (cadence); no ROADMAP/STATE/REQUIREMENTS edits.

## Self-Check: PASSED
