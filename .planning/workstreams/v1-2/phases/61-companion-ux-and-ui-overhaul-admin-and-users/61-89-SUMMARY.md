# Phase 61 Plan 89: One SaveBar component Summary

Owner item W147 (audit findings F04 and F21): every page with unsaved changes now shows the same floating Cancel and Save bar, from one server helper, one stylesheet block and one script behaviour.

## What changed

- **Server helper:** new `companion/ui_save_bar.py` (`save_bar_html`). Two modes share one structure (message, Cancel, Save):
  - tracked: bound to a `data-dirty-form` form; visible in the markup so Save works with scripts blocked, hidden at init by `dirty-state.js`, optional carried (`data-dirty-carried`) state; used by the settings pages (Departures, Arrivals, Calendar, Fleet settings through `config_page.docked_dirty_bar_html`) and the Location page (`detection_page.dirty_bar_html`).
  - page: for form pages that are the edit (new/edit special look, calendar connection): always shown, Cancel is a link, the message is the page title (`personalisation_cards._bar_html`).
  Markup: `div.dirty-bar[role=region][aria-label]`, message `span.dirty-bar__message` (`role=status` on the tracked bar, where the script writes it), Cancel then Save in DOM order (the visual order no longer relies on CSS `order`, so tab order matches).
- **Words:** Save / Enregistrer and Cancel / Annuler on every page (the "Save location", "Create look", "Connect", "Replace" labels are gone). Message: "Unsaved changes" / "Modifications non enregistrées"; only when several areas changed it adds the areas: "Unsaved changes: Detection, Place" (a new string `display.unsaved_changes_in`). The old "X changed" / "X and Y changed" / "N unsaved changes" connector strings and their `data-dirty-*` attributes were removed (now three attributes: `data-dirty-several`, `data-dirty-saving`, `data-dirty-initial-text`), fixing F21.
- **CSS:** one `.dirty-bar` block. Phone: `position: fixed`, full width less the margins, docked above the tab bar, message line over two equal buttons. From 960 px: docked to the foot of the main content column, same width as the cards (`min(1344px, 100% - sidebar - gutters)`), one row (message, Cancel, Save). `--save-bar-h` (78 px wide, 110 px on a phone) is a token used for page clearance and by the Location map (`--place-bar-h` now reads it; the map's own controls ride above the bar on a wide screen, the sheet above it on a phone). The message is clipped to one line so the height never depends on its words. Entrance reuses the finite `skypane-bar-arrive`; reduced motion is zeroed by the global override. Removed: `.dirty-bar--docked`, `.form-bar*`, the Location-only absolute variant, the per-breakpoint fixed rules and the per-variant button/count rules.
- **JS:** `dirty-state.js` writes one message (initial text for 0 or 1 area, lead-in plus the list for several); the `data-dirty-generic` branch and the connector words are gone.
- Tokens only, no inline style or script, one rule per selector per context.

## Tests

New `companion/test_browser_save_bar.py` (8 = 390/1280 x EN/FR x light/dark): opens every page that can raise the bar (Departures, Arrivals, new and edit special look, calendar connection, Location, Fleet settings), measures the bar and asserts identical width, height, left/right and distance from the bottom across the pages, Cancel before Save with the same labels, 44 px targets, role=region with a label, the one message on the tracked pages, no horizontal overflow, phone width = viewport less the margins and, on a wide screen, docked right of the sidebar.

Updated in place (not weakened; the subject changed): `test_config_page_03` (rule count and one position rule), `test_status_pages_07` (geometry now in the one base rule plus the wide-screen docking), `test_config_page_05` (Cancel/Save grid areas instead of `order`), `test_config_page_02` and `test_companion_app_02` (new attribute set and literals), `test_config_page_04`, `test_config_page_03` aspect copy, `test_calendar_connection`, `test_device_links`, `test_personalisation_special_looks`, `test_detection_page`, `test_place_page`, `test_detection_position` (selectors `.dirty-bar`/`.dirty-bar__cancel`, label "Save"/"Enregistrer"), browser: `test_browser_detection` (single-area message, plus a new test for the several-areas message), `test_browser_ux_03`, `test_browser_ux_04`, `test_browser_display_looks`, `test_browser_calendar_connect`. No test was deleted. Render baseline regenerated.

Screenshots: scratchpad `shots89/` (one per page, 390 and 1280).

## Deviations from Plan

- The exit is not animated (the bar hides instantly, as before); entrance is the one shared finite animation. A discrete display transition for the exit would make `hidden` lag behind the property tests read.
- Form pages (special look new/edit, calendar connection) keep the page title as their message (the page is the edit, nothing is "unsaved"); structure, size and position are identical.
- The calendar connection page's "Connect"/"Replace" button reads Save as the plan's label rule requires; the pending "Checking..." label is unchanged.

## Known Stubs

None.
