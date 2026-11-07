# Phase 61 Plan 79: Location sheet and Special looks / Calendar pages Summary

Owner decisions D-E and D-H: the Location page opens on My position with a reworked sheet, a floating Save/Cancel bar and the map behind the glass sidebar and tab bar; "New special look", "Edit special look" and "Connect / Edit calendar" are full pages with a floating Cancel / Save bar instead of dialogs.

## What changed

### D-E Location (`companion/pages/place_page.py`, `static/place-map.js`, `static/style.css`)
- **My position first.** The switch lists My position, then Airport (each with an icon, shown with the map only). A plain visit opens on My position when the frame has no saved `detection` setting; a frame with a saved detection (airport or position) opens on its saved mode; `?mode=` and `?airport=` still decide (links and no-JS behaviour unchanged).
- **Sheet rework.** One inner padding (20px, `--place-pad`); the airport name is a heading with its codes under it and the runway heading is a small label; the pin has a readout (`#place-coords`, "48,7262 N · 2,3652 E", decimal comma in French, updated by the map script, plus "Touchez la carte pour le déplacer"); the radius is a tidy row (label, number) over the slider and a 2 / 15 / 28 km scale; the nearest-airport suggestion is a card with an icon, the sentence and a 44px button (desktop only).
- **Mobile (<700px) My position:** the suggestion is not shown, the readout is one compact row, the scale is dropped; the sheet stays within 28dvh (it scrolls inside when it must, like before).
- **Floating bar.** The Save/Cancel bar leaves the sheet and is the Fleet page's docked unsaved-changes bar (`dirty-bar--docked`): above the tab bar on a phone, at the foot of the card's column on a wide screen, shown only when something changed (dirty-state.js unchanged). The sheet lifts above it on a phone. Without scripts the bar is a normal sticky Save button in the page.
- **Map behind the chrome.** The map is `position: fixed` over the whole window (`overflow: clip`, never a scroll container, so focusing a zoom button cannot slide the page): behind the frosted sidebar from 960px (sidebar `z-index` and the tab-bar glass tokens) and behind the glass tab bar on a phone (the bar's solid underlay is transparent on this page only). 61-65 / 61-69 behaviours (app bar scrim, clusters, pins, tap to place, typed suggestions, address on submit only) are unchanged; `coveredBy()` already measured the card and the sheet from their own boxes.

### D-H Special looks and Calendar pages
- **Routes** (server-rendered, deep-linkable, no modal): `/display/special-looks/new`, `/display/special-looks/edit?rule_kind=&rule_key=`, `/display/calendar/connect`. They are Display views (Display tab, Personalisation navigation marks Special looks / Calendar), registered in the route table, policy table and render baseline.
- **Layout:** picture on the left (the look, departing, large), options in a card on the right, one column on a phone (picture beside its caption), a back link to the list and the floating bar (Cancel link back to the list, Create look / Save / Connect / Replace button with `form=`). New classes `form-view`, `form-page*`, `form-bar*`.
- **Special look form:** same fields (`rule_kind`, `rule_key`, `rule_theme_id`), same route (`/settings/rules/add`), same validation and flashes; the three-choice picker and the recent-key chips work in the page (`theme-preview.js` reworked: the old details/dialog wiring is gone). **Edit** posts to the same add route (it replaces an existing rule): the key is shown as fixed text plus hidden fields, the rule's look is preselected, each list row has an Edit link. An unknown or hostile `rule_kind`/`rule_key` shows the new-look page.
- **Calendar connection page:** same field (`calendar_url`), same route (`/settings/calendar/connect`), CSRF and access rules; masked host only (the full link is never in the page); a refused link returns to this page with the inline error (`?calendar_error=`); the pending "Checking…" label is the only script left (`calendar-sheet.js` became `calendar-connect.js`, 20 lines). Disconnect is the standard confirm dialog (`ui_modal`, same pattern as Remove a special look) posting `confirm=yes` to the unchanged route; the server confirmation page stays behind it for a bare POST.
- **Removed (dead code):** the `Manage` dialog, the `?calendar=manage` open flag and its page-context field (replaced by `rule_edit`), the in-sheet disconnect confirmation script, the "Add a special look" details/dialog markup, `special-add__*`/`calendar-sheet__*`/`calendar-danger` CSS (the add row keeps `special-add__summary`/`__plus` as a link), `display.add_rule` (FR key).
- The calendar row's own look chooser (the look sheet on the Calendar list) is unchanged.

## Tests
- New `companion/test_browser_place_sheet.py` (11 tests, run 3 times in a row): My position first and default, saved airport still opens on Airport, no suggestion and sheet <= 28dvh at 360/390, suggestion on desktop, floating bar appears/saves/cancels at 390 and 1280 (position above the tab bar / under the card), readout EN/FR, map behind the sidebar (hit test owns the sidebar, blur) and behind the tab bar (transparent underlay, glass), no-script Save stays a plain sticky button.
- `test_browser_display_looks.py`: new special look page posts a rule (Cancel returns to the list, no dialog), edit page replaces a rule, new page fits a phone with the bar above the tab bar. `test_browser_calendar_sheet.py` became `test_browser_calendar_connect.py` (page reached by link, usable in both themes and languages with the bar above the tab bar, replace round trip, refused replace returns with the error, pending label, disconnect dialog, scripts blocked, signed-out POST). `test_calendar_sheet.py` became `test_calendar_connection.py`.
- `test_personalisation_special_looks.py`: new, edit, French, hostile edit parameters, fixed key, preselected look.
- Updated in place (they pinned the old structure): access matrix, route table, device routes, device links, CSRF, poll removal, user health, config page 03/04/04b/05, companion app 04/05, detection/place page (default mode), editorial caption floor (the privacy hint moved to the connection page), place layout tests (map whole window, sheet floats above the bars, card 400px), detection/place/pins/clusters/overhaul tests that start in Airport mode now ask for `?mode=runway`, accordion test (two look disclosures, rule radios on the new page), one-toast-one-sheet (the calendar dialog is now the disconnect confirmation), render baseline.
- Step count L1-pin is 5 (was 4): the page opens on My position, so the airport pins need the Airport tab; recorded in `61-STEP-COUNTS.md` and `MEASURED`.

Screenshots: scratchpad `shots79/` (`E_pos_*`, `E_airport_*`, `H_*`; phone and desktop, light and dark, French).

## Deviations from Plan
- **Default mode:** "My position is the default mode on open" is applied to frames with no saved `detection` setting only. A frame that follows an airport or a saved position opens on what it follows (opening a following frame on a different mode would show a setting it does not have). Note the live frame that still carries only the legacy `tracked_runway` has no `detection` key and therefore opens on My position, with no pin, until a place is chosen; nothing is saved by looking.
- **Calendar page content:** the page holds the link form, the masked host and Disconnect, with the calendar flights' picture; the look of calendar flights stays chosen on the Calendar list row (its own look sheet), because it saves through the settings form, a different POST than the connect route (one page cannot honestly have one Save for two routes).
- **Edit special look** had no existing route: it reuses the add route, which already replaces.
- **Bar fill:** the Location Save bar is solid (`--glass-solid`), not translucent as in the mockup, so its labels read over any map picture in both themes.
- The status line ("Repère placé à ...") is read aloud only on desktop too (the readout replaces it).

## Known Stubs
None.

## Self-Check: PASSED
