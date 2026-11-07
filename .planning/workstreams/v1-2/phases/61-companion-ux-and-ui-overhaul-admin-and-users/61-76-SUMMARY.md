# Phase 61 Plan 76: Round 8 straight fixes Summary

The owner's round 8 fixes that needed no decision (W72, W73, W74, W77, W78, W79, W83, W85, W89, W90, W92, W95, W96, W97, W106, W107, W110, W111): opaque dialogs with a sticky Save, a Flights search clear of the frame button, a tidy Location sheet, a stable tab bar, and smaller wording and layout fixes.

## What changed

- **W72:** the Home empty-state tips use a comma (FR in `i18n_fr/home.py`, EN in `pages/home_notice.py`).
- **W73/W106/W107 (dialogs):** `.lightbox`, `dialog.modal` and `.calendar-sheet` left the translucent glass tier; they keep their solid `--color-dominant` surface, radius and shadow over the dimmed backdrop. This also removes the `backdrop-filter` blur that painted a half-transparent band under the Flights picture. `.modal__actions` is sticky at the foot of the dialog on an opaque strip (it carries the bottom padding and the safe area), so Save shows without scrolling at 390x844 and 360x740 while the body scrolls above it.
- **W74:** from 960px the Flights search is part of the title row (after the title, clear of the frame button, 360px wide) and wraps under the title when the row is too narrow, instead of an absolutely positioned box under the button.
- **W77/W78/W79:** the Location card over the map is opaque (`--glass-solid`); `.place-mode` no longer inherits the global label bottom margin (that was the vertical offset of the Airport / My position thumb); the runway check mark is a small outlined badge on the card corner (never over the text), the length/surface text is centred and balanced; the runway heading has a gap under the airport name and codes.
- **W83:** `.personalisation-look` (Departures and Arrivals) joins the card entrance rule used by Special looks and Calendar.
- **W85:** "Main colour" / "Couleur principale", "White" / "Blanc"; a diagonal band option with no theme for the combination is not displayed at all, and with nothing left to choose the whole group is hidden (no explanation text remains). "Bande diagonale" unchanged.
- **W89:** Account frame rows have more vertical padding; the hardware line shows for administrators only (a co-managed frame still shows "Shared by").
- **W90:** the Manage access empty state sits in the same group as the owner row with the group's inner padding.
- **W92:** the add co-manager, invite and pairing code fields carry `autocomplete="off"`, `data-1p-ignore`, `data-lpignore="true"`, `data-bwignore="true"`, `data-form-type="other"`.
- **W95:** "Réinitialiser la connexion" / "Reset sign-in", a tooltip on the menu item and a clearer flash text; behaviour unchanged.
- **W96:** the Users self row keeps its role as a plain value; the explanation is a tooltip and a visually hidden description (the "You" pill marks the row); the frames cell does not wrap on desktop.
- **W97:** "Name it" is a 32px pill drawn inside a 44px target; on a phone its grid column sizes to it; the desktop menu column is wider.
- **W110:** the Fleet sub-tab label fills its segment (the selected pill sizes to the segment); the admin first tab-bar cell is 71px so "Mon cadre" fits.
- **W111:** `.tab-bar` has its own view-transition name (`skypane-tab-bar`) and an opaque `--glass-solid` fill under the glass layer, painted from the first frame.

## Tests

New `companion/test_browser_round8_fixes.py` (34 tests, 4 parallel runs green): dialog opacity and Save reachable without scrolling (390, 360, 1280, both themes); Flights search clear of the frame button and title at 960/1100/1280/1440; runway card text inside and centred with no check overlap, mode track symmetric, opaque card, heading gap (960/1280/1440, EN/FR, both themes); Fleet thumb width, tab bar label fit, solid fill and transition name; picture dialog has no blur and the whole viewport (tab bar zone included) is dimmed; Name it pill height and centring; Users self row and frames cell; Personalisation look views animate; autocomplete attributes.

Updated in place (they pinned the old structure): look picker test (options not offered), Users/Account/parity/i18n tests, motion-entrance selector pins, glass tier pins (dialogs no longer glass), `test_ui_modal` (sticky action row carries the safe-area padding), foundations safe-area test, surfaces audit (`.place-card` is opaque), view-transition name list, Flights title-row geometry, display-looks 44px loops skip options that are not offered. Render baseline updated.

Screenshots: scratchpad `shots76/` (place, quiet, access, fleet, flights, airlines).

## Deviations from Plan

- W92: the field name `email` is kept (the server reads it and many tests post it); autofill is blocked with the autocomplete and password-manager attributes instead of a rename.
- W111: the glass tier was kept; the bar gets a solid underlay and a transition name rather than being re-skinned.
- W78: the "offset" was a vertical one (a global label margin), not a horizontal one.
- Runway length/surface text stays one string (a test pins "4,209 m · Asphalt"); it is centred and balanced.

## Known Stubs

None.

## Self-Check: PASSED
