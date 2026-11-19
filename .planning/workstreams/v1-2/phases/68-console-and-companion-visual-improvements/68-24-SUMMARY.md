---
phase: 68-console-and-companion-visual-improvements
plan: 24
subsystem: companion
tags: [navigation, naming, tab-bar, sidebar, render-baseline]
requires: ["68-23", "68-10"]
provides:
  - "One personal page table feeds the sidebar and the phone bar (R04)"
  - "Same page names in tab, sidebar and page title: Flights / Vols, Location / Lieu (D-08)"
  - "Console More row back to the personal space reads My frames / Mes cadres (R34, D-30)"
affects: ["68-34"]
key-files:
  modified:
    - companion/ui_nav.py
    - companion/ui_base.py
    - companion/layout.py
    - companion/i18n_fr/nav.py
    - companion/pages/history_page.py
    - companion/pages/place_page.py
    - companion/pages/components_page.py
    - companion/testdata/render_baseline.json
decisions:
  - "Order approved in the mockup (Home, Flights, Airlines, Style, Location) is the old bar order; the sidebar followed another order, so it now follows the bar."
  - "The short-label table (NAV_SHORT_LABELS) and its two French ids are removed: with the same name everywhere they had no purpose."
  - "Only the Console More row says My frames; the desktop space switch segment still says My frame."
metrics:
  completed: 2026-11-19
---

# Phase 68 Plan 24: Navigation order, names and console label Summary

R04, D-08, R34 and D-30 built as approved in the header of `68-MOCKUP-shell-audit.html`. Phase 64 changed `ui_nav.py`, the nav tests and `style.css` (merged on main); the open pull request re-check could not be run here (no GitHub access in this executor), so the orchestrator must run it before merging.

## What was built

- `ui_nav.py`: the two page tuples are replaced by one `_PERSONAL_PAGES` table used by the sidebar and the bar. The sidebar now reads Home, Flights, Airlines, Style, Location (it was Home, Flights, Location, Style, Airlines). Entry sets per role are unchanged.
- Names: `nav.flight_history` is now "Flights" / "Vols" and `nav.detection` "Location" / "Lieu". Ids are stable; the tab, the sidebar and the page titles (`history_page.py`, `place_page.py`) share these messages. `nav.flights_short` and `nav.detection_short` (and `NAV_SHORT_LABELS`, also exported from `layout.py`) are removed, so no orphan French id remains. Airlines is unchanged; `nav.locations` was not re-added.
- Console More row: new id `nav.my_frames` ("My frames" / "Mes cadres"), used only by the Console to personal shortcut row.
- Editor title: it already reads "Airline editor" (`AIRLINE_EDITOR_LABEL`, singular) in the sidebar, bar-adjacent title and document title; nothing to change.
- Scroll and bar position: no jump was found. The new browser test opens the Console More sheet scrolled to the bottom, taps the row, and asserts that the bar box equals the one of a page opened directly and that `scrollY` is 0 (390 px, EN and FR). No CSS cause, so nothing is handed to plan 34 for this.
- Tests updated for the new names and order (`test_nav_personal_console`, `test_browser_tab_bar_roles`, `test_nav_spaces`, `test_user_nav`, `test_browser_nav_spaces`, `test_console_shell`, `test_space_switch`, `test_browser_more_sheet`, `test_browser_more_panel_redesign`, view and status page tests, and the Location tests). Added: bar labels equal sidebar labels in the same order (EN and FR, admin and owner); Flights label and title EN/FR; My frames row label EN/FR; space switch bar and scroll test.

## Baseline diff

`companion/testdata/render_baseline.json`: 64 entries changed, 0 stylesheet `?v=` changes. The only differences are the strings "Flight history" to "Flights", "Historique des vols" to "Vols", "Location and detection" to "Location", "Lieu et détection" to "Lieu", "My frame" to "My frames" and "Mon cadre" to "Mes cadres" (nav links, page title, document title, console row).

## Deviations from Plan

- [Rule 3] The quiet-hours dialog note and the Home time zone link still read "Location and detection" / "Lieu et détection". Shortening the French link to "Lieu" makes its tap area 39 px wide, under the 44 px floor (`.quiet-timezone-note a::after` in `style.css`, owned by plan 34), and the sweep tests failed. I kept the old link text. Plan 34 can widen the hit area and then rename the link (message id `display.location_and_detection_title`).

## Open owner decisions

1. Desktop space switch segment: still "My frame" / "Mon cadre" (only the Console More row was approved as "My frames").
2. Quiet-hours note link text (see above): old name kept until the hit area is fixed.
3. Components catalogue "Page names" table: its tab and page columns are now identical.

## Design-system divergences

None from the approved mockup. Phone More sheet and desktop sidebar compared side by side with the mockup (EN and FR, light and dark): same row, same order, same labels. Text centring, opaque round buttons and 44 px targets are untouched by this plan.

## Captures

In `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p24/`: `mock_shell_NN_x_{en,fr}_{light,dark}_full.png` (mockup figures), `before_*` (code at the previous commit) and `after_*` for home, flights, airlines, style, location, fleet, account at phone 390 (`ph`) and desktop 1280 (`dk`), EN and FR, light and dark, plus `*_fleet-more_ph_*` and `*_home-more_ph_*` (More sheet open).

## Verification

Browser tests with `SKYPANE_REQUIRE_BROWSER=1` on all changed test files plus guards: 4350 passed; the only failure left is the known `test_config_page_05` one. `test_i18n`, structure and suite guards, access matrix, French fit, render baseline: 2418 passed. ruff, mypy, function size (max 80), comment history clean; `app.py` is 1490 lines; `stub-server/test_phase47_freeze.py` green.

## Self-Check: PASSED
