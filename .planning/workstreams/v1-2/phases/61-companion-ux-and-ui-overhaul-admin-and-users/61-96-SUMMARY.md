---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 96
subsystem: companion-ui
tags: [switch, airlines-table, sort-menu, look-picker, calendar-look, place-search, save-bar, firmware-table]
key-files:
  created:
    - companion/test_browser_round11_fixes.py
  modified:
    - companion/static/style.css
    - companion/static/place-card.js
    - companion/static/place-map.js
    - companion/ui_filter.py
    - companion/pages/airline_collection_page.py
    - companion/pages/history_page.py
    - companion/pages/personalisation_cards.py
    - companion/pages/config_page.py
    - companion/pages/place_page.py
    - companion/pages/update_page.py
    - companion/settings/calendar.py
    - companion/settings/theme.py
    - companion/ui_base.py
    - companion/layout.py
    - companion/routes.py
    - companion/i18n_fr/detection.py
    - companion/i18n_fr/update.py
metrics:
  completed: 2026-11-08
---

# Phase 61 Plan 96: Round 11 production feedback (W156-W163) Summary

Eight owner findings fixed: the Users Active switch is a whole switch again, the Airlines type rows line up with the airline rows, the Flights sort is the collection's sort menu, the look picker's segmented controls are centred, the Calendar look is a page of its own, the Location search is one grouped list, the shared save bar is opaque, and the Fleet firmware table has a column per fact.

## W162 Users Active switch

Cause (measured): the switch track is a 52px block inside a flex `button.switch` whose width is `min-width: 44px`. In the narrow Users column the track was a flex item and shrank to 36px while the knob still translated 20px, so the knob left the track and the on/off look differed with the column. `.switch__track` is now `flex: none`. The markup was already the standard component (same classes as the Frame strip and Device switches), so every switch benefits. Colours are the existing switch tokens (on: accent track with the on-knob token, off: grey track with the light knob).

## W163 Airlines type rows

Two causes. (1) The empty action cell of a type row matched `.airlines-cell--act:empty { display: none }`, which also applied in the table layout, so the menu cell slid one column left and the last column showed a bare block. On the table layout the empty action and prefixes cells now stay `table-cell`. (2) The artwork cell's state word ("Utilise celle de la compagnie") is wider than the 17% artwork column and overflowed onto the views count: on the table layout the word stays for assistive technology (clipped, not `display: none`) and the dimmed thumbnail says the rest. Card layout (below 70rem): the type row's grid now has the airline row's three columns (the type row has no prefixes cell in the grid, which had opened a fourth implicit column that pushed its menu 32px left), the artwork gets its own line and the views count its own line. The views column is 10% wide so "N vues" no longer touches the next column.

## W156 Flights sort

`ui_filter.sort_menu_html()` is now the one sort component (icon menu with radio rows and a tick); the Airlines collection and the Flights list both call it. Flights keeps `?sort=`, the radios carry `form=` and the existing in-place refresh (`data-flights-auto`), the menu closes with the swap and focus returns to its button; with scripts blocked the radios plus the Apply button submit the form. The old `.history-sort` select CSS is gone.

## W157 Look segments

The track was 40px high holding 44px options, so the options overflowed and sat off-centre vertically (measured: option top at -6px from the track). The track is now 46px (1px border around a 44px row) and the pill is inset 4px, so label, swatch and pill are centred in equal cells.

## W158 Calendar look page

`/display/calendar-look` (`DISPLAY_CALENDAR_LOOK_ROUTE`, device-scoped, owner access, in the route table, the access matrix and the render snapshot) is a form page of the Calendar view: back link, the picture, the same picker as Departures/Arrivals (with the "Same as departures" switch; the native radio table without scripts), the floating Cancel / Save bar titled "Calendar flights look" / "Allure des vols du calendrier". It posts to the settings route with only `calendar_theme_id` and returns to the Calendar list; a rejected value is redrawn on that page. The Calendar list row is now a plain link ("Change"), with no sheet, opener or radios; the popover is gone from the calendar. Departures and Arrivals never used a popover (inline picker), special looks keep their own pages.

## W159 One location search

While a place or address is typed, the airport matches (instant, from the page's catalogue) are joined after a 700 ms pause by the search service's suggestions in the same list under "Airports" / "Aéroports" and "Places and addresses" / "Lieux et adresses" headings. At most one request every `data-search-lock-ms` and one at a time; answers are cached by query; Escape, arrow keys, Enter on an active option and a submitted search behave as before; without scripts the plain form is unchanged. The code is in `place-card.js` (247 lines); `place-map.js` only exposes three functions (1486 lines). Tests answer the search host with `page.route` (existing `Hosts` rig).

## W160 Save bar

The shared `.dirty-bar` left the translucent-glass group (0.09 alpha white in dark mode over a pale map) and takes `--glass-solid`, opaque in both themes, with the standard border and glass shadow. Contrast of message, Cancel and Save text against their surfaces is asserted at 4.5:1 or more on the Location page in both themes at 1280 and 360.

## W161 Fleet firmware table

Columns Version, State (Running badge, Newer, Earlier), Released (age with the full date under it) and the action; the running row is tinted with a left accent edge; notes stay a disclosure under the version; Install and Roll back buttons share one width and column; on a phone each row is a two-line card (version and state, age and button).

## Deviations from Plan

- Calendar look page offers the colour picker and the native table, like the Departures/Arrivals views, not the special look form's own axes host.
- The all-views render (`view=None`, served by no route) now appends the calendar look controls to the Calendar card so the existing whole-page audits (every registered theme as a radio, the three live pictures) still cover the calendar look.
- Tests updated in place because their subject moved: `test_config_page_01/03/04/05` (calendar controls are located by `calendar_look_segment()`; the all-views render has three large pictures), `test_display_looks` (the calendar radios are on the look page; the Calendar list has no sheet), `test_personalisation_page` (a rejected calendar value redraws the look page), `test_access_matrix`, `test_device_routes`, `test_route_table` (the new route), `test_update_page` and `test_browser_fleet_sections` (State column), `test_browser_flights_*` (the sort is a menu), `test_view_pages_01/02` (the sort menu is the only details/summary), `test_sky_contrast` (the save bar is the one opaque overlay: stricter), `test_browser_place_search` (a name, a request now also happens once the typing pauses).
- Nominatim's usage policy discourages autocomplete; the pause and the one-request-per-1.5-s lock are the mitigation.

## Known Stubs

None.

## Verification

See the hand-back for the exact test list. Screenshots (before/after) are in the scratchpad `shots96/` folder.
