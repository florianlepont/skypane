# Phase 61 Plan 58: User pages on the grouped-list components Summary

Flights, Account, Airline collection, Personalisation and Location now use the glass tier and the group/row components of plans 61-56/57. Flights and Account are rebuilt as groups of rows; the collection, the Personalisation bar and Location are aligned in place. Not every item of the plan was reached (see "Not done").

## What changed

- **Flights (phone list).** `history_page` builds one glass group per Paris day (section label Today / Yesterday / date) with one `ui_groups.row` per flight: plane chip rotated by direction, callsign and route codes (home end muted), "airline - aircraft" detail, live age over the clock at the right, the 44px picture action beside the row. Direction is shown by the chip and spoken in a visually hidden label. The segmented filter is unchanged (glass track, graphite pill, centred counts); `list-filter.js` hides a day group (`data-filter-day-group`) when its last row is filtered out; the hairline is drawn between visible rows only. Empty and unavailable states are one panel group. The desktop table is kept. `freshness.js` and `ui_nav` swap region is now `.history-cards`. `flight_card.py` lost the boarding-pass helpers (art, stub, route, when) and the FR string `flights.no_illustration`; `ui_groups.group` gained `attrs`, `ui_groups.row` gained `lead_html`.
- **Account.** My frames group (CSS frame picture, name, hardware/owner line, status dot and last-seen word, chevron; Manage access / Leave frame as the row's link line, at the right from 640px; Add a frame as the last row with the accent chip), Identity value rows (ellipsis), Preferences rows with the existing `/ui-lang` and `/ui-theme` forms as the trailing segmented control (graphite selected pill), Sign out as its own group, one danger row (same form and CSRF). Empty account keeps the empty state in a panel group. `pair_frame_page.secondary_link_html` removed (replaced by the row).
- **Airline collection.** Neutral artwork plate, name 15px/600, coloured top borders removed (rarity stays the pill), detail-sheet facts as 54px rows.
- **Personalisation.** The view bar is separate glass pills with the graphite selected pill (thumb kept), horizontally scrollable.
- **Location.** Sheet and mode pills use the solid glass fill; new test that the bottom sheet clears the floating tab bar at 360x640 and 390x844 (it already did; no fix needed).

## Tests

Updated in place (none weakened): `test_flights_cards`, `test_view_pages_03`, `test_browser_flights_cards` (probe now row geometry, new flat day group and centred segment test), `test_browser_ux_01`, `test_account_page`, `test_user_pairing`, `test_browser_airline_collection` (facts rows stack: spacing >= 54px replaces the two-column assertion). New: `test_browser_place_page::test_the_bottom_sheet_clears_the_floating_tab_bar`. `render_baseline.json` regenerated.

Removed tests, with reasons: the tear-line notch test, the artwork plate / "No illustration" tests and the route-track (plane between codes, direction label under it) assertions: the boarding-pass card they describe no longer exists.

## Deviations / Not done

- Personalisation Look (preview hero plus one picker group) already matched the mockups after the pill bar change. Calendar: the look-of-calendar-flights row now clears the Choose calendar button (sibling selector, medium spacing).
- Not migrated, remaining for a later pass: the Special looks rule rows (they keep their Remove buttons, no chevron rows), the Update/Releases view, the quiet-hours dialog, the other dialogs/sheets and flash toasts (they already sit on the glass tier). The Airline collection grid is aligned in place, not rebuilt as a group.
- The Flights desktop view keeps the data table (not rows).
- Dialogs keep the existing sheet radius (`--radius-pill`, 32px) rather than a new 28px token (the three-radius scale).
- Location sheet is not translucent in Dark: a translucent fill over a light map tile failed contrast.
- Row-value contrast tests over the glass were not added specifically for the new rows; existing sweep and contrast tests cover the shared tokens.

## Screenshots

`/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots58/` (`<page>-{phone,desk}-{light,dark}-{before,after}.png`; `flightsdata-*` uses a seeded history).

## Verification

ruff, mypy, comment-history, function-size and `test_phase47_freeze` green; `companion/app.py` unchanged (1473 lines). Full suite: see the report.
