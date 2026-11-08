---
phase: 61
plan: 91
subsystem: companion Personalisation
tags: [calendar, special-looks, look-picker, no-js, owner-W145, owner-W148, owner-W153]
key-files:
  modified:
    - companion/settings/theme.py
    - companion/settings/rules.py
    - companion/static/style.css
    - companion/static/theme-preview.js
    - companion/i18n_fr/look.py
    - companion/testdata/render_baseline.json
  created:
    - companion/test_browser_personalisation_fixes.py
---

# Phase 61 Plan 91: Personalisation UI fixes Summary

The Calendar look popover is no longer clipped on desktop, the picture caption is gone, the special look rows give their text the width on a phone, and the script-only "Customise look" button no longer shows without scripts.

## What changed

- Calendar (W148, F01, F25): `.special-list` lost its `overflow: hidden` (it clipped the absolutely positioned look popover); the dead 1200px `.look-sheet--calendar` placement rule (left over from the three-column card) is removed, so the popover opens under its row on desktop and as a bottom sheet on phones. The script scrolls the popover into view on desktop. While "Same as departures" is on, the sheet shows a one-line explanation (`look.follows_departures_note`, EN/FR) instead of unexplained greyed controls; the Calendar tab shows only its own content (connect row and calendar look row).
- Caption (W145, F06): the "Departures / Plain paper" caption under the Departures and Arrivals pictures is removed (the picture keeps its alt text with the look). The phone picture is now centred at 56% width (the caption column beside it is gone).
- No jump (F23): the colour row's reason line reserves its two lines beside the page (>= 700px), and an empty colour value keeps its line, so choosing a background no longer moves the rows. On a phone the reservation is off (it costs 44px above the tab bar; the existing fit-one-screen test pins that).
- Special looks rows (W153, F12): row = picture left, text column (kind badge on its own line, `white-space: nowrap`; name and key; look summary) taking the width, and a new `.special-row__actions` group. On a phone the two actions sit side by side under the text (44px targets); from 700px they stay at the right of the row.
- No JS: the dead "Customise look" button (hidden attribute overridden by its own display) is removed from the markup with its CSS and FR string; the native radio cards are the no-script way in.
- New special look form: changing the kind clears the Value field (and its validity state), so an Airline key does not stay once the kind is Flight. Suggestion chips: already ordered newest first per kind and filtered to the selected kind (the audit note S5 was an assertion about which chip is first, not a defect); no change.

## Tests

- New `companion/test_browser_personalisation_fixes.py` (35 tests): Calendar tab at 1280/1440/390, EN/FR, light/dark (own content inside the list, popover fully visible by hit-testing its corners, explanation note, close); no caption at 360/1280 on both views; no control movement when choosing backgrounds; row text >= 120px at 360/390 EN/FR light/dark, badge on one line, no word broken across lines (Range rects), actions >= 44px under the text and owning their centre; long names ("Gendarmerie Nationale", "French Air Force"); no-JS no visible opener buttons; kind switch clears the key.
- Pinned tests updated in place: `test_display_looks.py`, `test_personalisation_page.py`, `test_config_page_03.py` (read the look back from the picture alt, no "Customise look" word), `test_browser_display_looks.py` (alt read-back, centred picture instead of caption beside it).
- Render baseline regenerated (`companion/testdata/render_baseline.json`). Screenshots in `scratchpad/shots91/` (`before_*`, `after_*`, `final_*`).

## Deviations

- The colour reason space is reserved on desktop only (see above); the phone keeps the collapsing reason because of the fit-above-tab-bar test.
- The stripe row's reason (last row) can still appear below the picker; nothing under it moves, so the test pins only the rows above it.
- Phone tap-to-zoom (F24) not added; the 56% centred picture is the polish.

## Known Stubs

None.
