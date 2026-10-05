---
quick_id: 261004-sfl
subsystem: companion
tags: [tests, flake, airline-sheet]
key-files:
  modified:
    - companion/test_browser_airline_sheet.py
completed: 2026-10-04
---

# Quick 261004-sfl: scripts-blocked sheet click flake

Not a layout bug. After the `#airline-sheet` anchor jump (and after a refusal) the sheet sits
at the top of the viewport and the Save button is 241-322 px from the top, 300+ px above the
tab bar, at every phone height from 600 to 900; the page already reserves tab-bar padding. The
failure was the test clicking while the page was still settling; Playwright's retry scroll
then put the button under the fixed bar. The sheet tests now centre each target before
clicking, wait for load after the anchor navigation, and a new test measures the Save button
clear of the bar. No CSS change.

A second CI failure (the calendar sheet's Disconnect confirmation click) shows the same symptom.
At max scroll the lowest in-page content sits 71 px above the tab bar at 390x568 (the page
bottom padding is the 2xl space plus the 56 px bar), and CPU-throttled 6x with delayed assets
the Save button stayed at a fixed offset and always resolved to itself. The bar can only cover
a control in the alignment Playwright's click retry forces (block: end), which a real scroll
never produces. Centring before every click removes the retry path.
