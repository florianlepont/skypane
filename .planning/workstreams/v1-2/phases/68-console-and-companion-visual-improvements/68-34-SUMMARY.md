---
phase: 68-console-and-companion-visual-improvements
plan: 34
subsystem: companion
tags: [more-sheet, tab-bar, navigation, pills, render-baseline]
requires: ["68-24", "68-10"]
provides:
  - "Visible 44x5 grab handle, as drawn in the approved mockup (D-11)"
  - "Tapping the active tab scrolls to the top without reloading (D-13)"
  - "Space-switch segment reads My frames / Mes cadres"
  - "Home time zone link and quiet-hours note read Location / Lieu with a 44 px tap area"
  - "credits_page.py and settings/calendar.py build pills with ui_components.pill_html (D-14)"
affects: ["68-25"]
key-files:
  modified:
    - companion/static/style.css
    - companion/static/motion.js
    - companion/ui_components.py
    - companion/ui_nav.py
    - companion/credits_page.py
    - companion/settings/calendar.py
    - companion/settings/quiet_hours.py
    - companion/i18n_fr/nav.py
    - companion/i18n_fr/display.py
    - companion/testdata/render_baseline.json
decisions:
  - "D-09: the approved block says the tablet width is already fine (bar and sheet capped at 460 px, centred); no change, existing tablet-cap tests kept."
  - "D-11: the approved block says the handle is kept as is; the mockup draws it 44x5, the build had 40x4, so it is now 44x5. It stays decorative (aria-hidden); keyboard close is Escape and the More cell, screen reader close is the More summary, both already tested."
  - "D-13: a plain click on the active tab whose link is the open URL scrolls to the top (smooth, instant with reduced motion); on a sub-page of the tab the link still navigates."
  - "Message id display.location_and_detection_title renamed display.location_title (EN Location, FR Lieu); nav.my_frame removed, the segment uses nav.my_frames."
  - "pill_html gains extra_class and dot_class so the calendar status pill keeps its dot and its page hook while using the catalogue helper."
metrics:
  completed: 2026-11-19
---

# Phase 68 Plan 34: More sheet, active tab tap, pills Summary

Second half of the shell changes from `68-MOCKUP-shell-audit.html`, plus two owner decisions given after plan 24.

## What was built

- Grab handle 44x5 (was 40x4), colour and place unchanged.
- `motion.js` (1107 lines): active-tab tap scrolls to the top; other tabs navigate as before.
- Space switch: the desktop segment now reads My frames / Mes cadres (same message as the Console More row). Its French label overflowed the 92 px sidebar segment by 1 px, so `.dashboard-sidebar .space-switch` gets inline padding of 4 px (was 8 px).
- Quiet-hours note and Home time zone link read Location / Lieu. `.quiet-timezone-note a::after` is now centred and at least 44 px wide and tall (was 39 px in French). The existing browser test `test_the_home_dialog_note_is_a_44px_link_to_the_location_page` (EN and FR, 360 and 1280, light and dark) asserts the 44 px hit area and now passes with the shorter names.
- D-14: credits attribution pill and calendar status pill use `ui_components.pill_html`.
- R34: plan 24 found no CSS cause for the space-switch jump; nothing carried.
- Open pull requests: the GitHub MCP tools were not available to this executor; `gh api repos/florianlepont/skypane/pulls` shows two open PRs: #482 (docs for the rear enclosure) and #481 (dependabot playwright bump in /server). None touches `ui_shell.py`, `style.css`, `credits_page.py` or `settings/calendar.py`. (`ui_shell.py` itself needed no change.)

## R10 (Safari / web app dim and blur)

Checked: the scrim rule declares `-webkit-backdrop-filter: blur(8px)` and `backdrop-filter: blur(8px)` (asserted on the served stylesheet; Chromium computes only the standard property); with the sheet open the scrim is fixed, non-transparent and blurred in a browser tab and with `navigator.standalone` forced true (Home Screen app class `web-app`); the site has no web manifest, so there is no `display-mode: standalone` to check (iOS standalone is detected by `navigator.standalone`). `:has()` is the only trigger of the scrim; Safari 15.4+ supports it, no fallback class added (the approved block records no Safari failure).
Not verifiable here (open item for the owner's device check, plan 32): real Safari and a real iPhone Home Screen app rendering of the dim and blur, including the zones under the status bar and bottom toolbar.

## Baseline diff

68 entries, only: stylesheet `?v=`, `motion.js` `?v=`, "My frame"/"Mon cadre" to "My frames"/"Mes cadres" (32 each), and the quiet-hours note link text on 2 entries. The grab handle markup did not change.

## Deviations from Plan

- Plan test 2 asked for an accessible name and a 44 px grab area on the handle. The approved mockup says "kept as is" and the 44 px is the mockup's pill width; a tap area over the pill would steal taps from the Account row below it, so the handle stays decorative. [Rule 4 avoided: no structural change.]
- [Rule 1] French "Mes cadres" overflowed the sidebar segment by 1 px; fixed in `style.css`.

## Open owner decisions

1. The French tab bar still reads "Airlines" (not translated); not touched here.
2. The More sheet shows a wider empty gap above Sign out than between other blocks (pre-existing, same in the before captures).

## Design-system divergences

None from the approved mockup. Phone More sheet compared side by side with the mockup (same rows, same handle 44x5, centred labels, opaque round controls, 44 px targets), EN and FR, light and dark; tablet (820) shows the sheet capped at 460 px and centred as approved. No explanatory line was added.

## Captures

In `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p34/`: `mock_shell_NN_x_{en,fr}_{light,dark}_full.png` (mockup), `before_*` (HEAD before this plan) and `after_*` for home, flights, airlines, style, location, fleet, account at phone 390 (`ph`), tablet 820 (`tb`) and desktop 1280 (`dk`), EN and FR, light and dark, plus `*_home-more_*` and `*_fleet-more_*` at `ph` and `tb` (More sheet open).

## Verification

`SKYPANE_REQUIRE_BROWSER=1` with `server/.venv/bin/python`: more sheet, more panel, tab bar (tablet cap, float, roles), hit area, nav, space switch, time zone and quiet hours, calendar, components, French fit, contrast edges, i18n, structure and suite guards, access matrix, render baseline, golden renders, `stub-server/test_phase47_freeze.py`: 3122 passed in the first run, the 2 failures (French sidebar segment) fixed and re-run green. ruff, mypy, function size (max 80), comment history clean; `app.py` 1490 lines; `motion.js` 1107 lines.

## Self-Check: PASSED
