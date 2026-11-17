---
quick_id: 261115-l7p
status: complete
commits: [449ad858, 985f62c0]
---

# Quick task 261115-l7p: Fleet "Other frames" row menu no longer clipped

## Root cause

`.group` (`companion/static/style.css`) sets `overflow: hidden` for the card's rounded corners. The
Fleet "Other frames" section is one `ul.group.fleet-group` holding the entity list, so the row menu
popover (`.row-menu__panel`, absolutely positioned below the toggle) of the last row extended past the
card's bottom edge and was cut off. Nothing else clipped it.

## Change

- `companion/static/style-admin.css`: `.fleet-block--others > .group { overflow: visible; }`. The rows
  paint no background, so the rounded clip was not needed there.
- `companion/test_browser_row_menu_reach.py` (new, 8 cases): opens the last Other frames row menu
  (retired frame, Re-activate) at desktop 1280 and phone 390, English and French, light and dark, and
  asserts the centre and corners of each option are inside the viewport and hit by `elementFromPoint`.
  Only the window scrolls (scrollIntoView on the option would scroll the clipping ancestor and hide
  the bug). It failed on all cases before the fix, and passes after.

## Shared callers

The fix is scoped to the Other frames group; the shared `.row-menu` rules are untouched. Other users of
the row menu (Users table, Airline table/collection, Components page, `ui_entity_list.row_menu_html`
elsewhere) are unchanged and their browser tests pass. The Fleet "Frames" list is the frame menu,
not this row menu. The menu of this section has one option per row (Re-activate, Pair frame or Personal
view).

## Verification

- New test: 8 passed (failed before the fix).
- 681 passed: new test, `test_browser_fleet_*`, `test_browser_users_page`, `test_browser_console*`,
  `test_browser_airline_table`, `test_browser_components_page`, `test_browser_contrast_edges`,
  `test_console_*`, `test_ui_entity_list`, `test_health_fleet_status`, `test_companion_app_04`.
- ruff on the new test: clean. Comment-history guard: clean.
- No golden changed (`companion/testdata` untouched).

## Deviations

None. The first test draft passed falsely because scrollIntoView scrolled the clipping group; fixed
before the test commit was recorded as red.
