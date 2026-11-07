# Phase 61 Plan 77: Airlines page, More sheet, Fleet summary rows Summary

Owner decisions D45 (D-A, D-G, D-B): a calmer "Compagnies" / "Airlines" collection page, a More sheet that continues the tab bar (pages, separator, settings) over a dimmed and blurred page, and a Fleet page on desktop made of summary rows that open dialogs.

## What changed

- **D-A Airlines collection:** the page and the sidebar / More label are "Compagnies" (FR) and "Airlines" (EN); the title keeps the standard `.page-title` size (a test compares it with the Flights title at 360 and 1280). The progress is one line: count, a thin bar, the next goal and a compact "1/5" badge pill (the star icon, with a tooltip and a visually hidden list that spell every badge out; the five round badge icons are gone). The control bar is sticky (glass-solid fill, 8px padding, top offset with the safe area). Cards are larger and calmer: 2 columns on a phone, 3 from 700px (the 4-column step at 1280 is gone), the name, then one line "Seen 36 times · Regular" with the rarity in words and colour; the "New" pill sits on the picture and only while it applies; an airline not seen yet is dimmed (card fill and picture) and carries its name only. The unlock animation, the sheet per card, filters, sort, legend and links are unchanged.
- **D-G More sheet:** the sheet is now, top to bottom: the pages that do not fit the bar as rows with an icon tile (Airlines, or Audit log for the Console), a separator, then the settings block (theme, language, the Account row, Sign out). The page behind is dimmed and blurred by a `body::after` scrim (55% text colour, 8px blur) that covers the whole viewport above every page layer (sticky bars, the unsaved-changes bar) and under the tab bar, which is raised to sit above it while the sheet is open. `modal.js` now also closes the sheet on Escape or a tap outside it (`details.tab-bar__more` joined the menu selector).
- **D-B Fleet desktop (from 960px):** the selected frame shows State plus one group of summary rows (icon, label over value, chevron): Device and version, Version history, Wake interval, Access, Other frames (when there are any). Each row is a plain `#id` link to a `dialog.modal` (opaque, centred, sticky action row); with script it opens as a modal, without it the `:target` card shows. The settings dialog has Save and Cancel; Cancel resets the form and closes the dialog; leaving the dialog with Escape or the close button hands over to the page's unsaved-changes bar, which keeps working. Access reuses the existing Manage access dialog; Other frames gets its own dialog (the row menus inside still open the pair / re-activate dialogs). Below 960px the same dialogs render as plain blocks (`display: contents`, head and actions hidden), so the phone sub-tabs and their groups are unchanged; `?frame=` and `?view=system` and the redirects are untouched. New module `companion/fleet_summary.py` holds the rows and the dialog wrapper; `update_page` gained `update_parts` / `render_parts` so the device card and the version list can be placed separately (its output for the standalone page is byte for byte the same).

## Tests

- New `companion/test_browser_fleet_rows.py` (17 tests): rows, chevrons, 44px, labels EN/FR, opaque centred dialogs at 960 and 1280 in both themes, Save persists, Cancel restores and closes, the unsaved bar after leaving the dialog, the Other frames dialog, the no-script row link and the page Save bar, phone keeps tabs and shows no row, `?frame=` / `?view=system`.
- `companion/test_browser_more_sheet.py`: order pages, separator, settings (360/390, EN/FR); airlines first on a personal page; the scrim hit-tests every point of the viewport outside the sheet and the bar (360/390, both themes, `/fleet` and `/airlines`), is at least 40% opaque and blurred, and a tap outside closes the sheet.
- `companion/test_browser_airline_collection.py`: title size equals the Flights title; sticky bar; the New pill on the picture; one-line progress; 3 columns; unseen card carries only its name; pill and rarity colours.
- New `test-support/fleet_rows_support.py` (`open_dialog`, `close_dialog`) for the browser tests that reach a Fleet group from 960px.
- Updated in place (they pinned the old structure): airline page tests, nav label tests (EN "Airlines", FR "Compagnies"), i18n and status-page tests, Fleet tab / page / dialogs / blocks / groups / dirty-bar tests, the update-page browser tests (open the device or versions dialog first; a longer seed note so the dialog still cuts it; a key press before the focus-ring check), toasts, motion, LED switch, contrast edges, ux_01 / ux_04. The sign-in digests and `render_baseline.json` were regenerated.

Screenshots: scratchpad `shots77/` (airlines desktop / phone FR and dark, More sheet FR and dark, Fleet desktop, dialogs, Fleet phone).

## Deviations from Plan

- **Dialog Save is a plain button** (`data-modal-submit`, handled in `modal.js` with `form.requestSubmit()`), not a submit control: the page keeps exactly one submit-shaped control per settings form (a guard test requires it), so without script the page's own Save bar is the way to save. With script the dialog Save and the bar both work.
- The LED stays inside the Settings dialog (no direct switch on the summary row, unlike the mockup), because its instant-toggle form is tied to the settings group.
- On a phone the version list is now its own group under the device group (it used to share one group); the section label of that group is hidden, the card keeps its own "Versions" heading.
- The `.modal` input and button rules exclude `.fleet-dialog--inline` (`:where()`, no specificity change) so the phone page keeps its control sizes; the same declarations are applied to those dialogs from 960px.
- Two Fleet browser tests changed their viewport or flow rather than their assertions: the docked bar test uses a 520px-high desktop (the page no longer scrolls on a tall screen, so the bar follows the content instead of sticking to the viewport foot); the ux_01 / ux_04 settings-form tests open the dialog and leave it before using the bar.

## Known Stubs

None.

## Self-Check: PASSED
