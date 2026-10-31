---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 06
subsystem: companion
tags: [detection, companion, route-policy, i18n, runway-search]
requires: [53-05]
provides:
  - companion/pages/detection_page.py (render, parse_query, DETECTION_ROUTE, PAGE_TITLE)
  - companion/detection_actions.py (handle_post for action=save_detection, runway branch)
  - companion/i18n_fr/detection.py (French for the page)
  - GET and POST /detection as OWNER_DEVICE routes, also under /devices/<id>/detection
affects: [53-07]
key-files:
  created:
    - companion/pages/detection_page.py
    - companion/detection_actions.py
    - companion/i18n_fr/detection.py
    - companion/test_detection_page.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/flash.py
    - companion/static/style.css
    - companion/test_access_matrix.py
    - companion/test_route_table.py
    - companion/test_device_routes.py
    - companion/testdata/render_baseline.json
    - test-support/companion_render_snapshot.py
requirements-completed: [DET-01]
completed: 2026-10-31
---

# Phase 53 Plan 06: Detection route and the runway half of the Detection page Summary

Owners and admins can now search airports, pick a runway and save it on `/detection` with scripts disabled; everyone else gets 404, and the Orly runways keep storing the legacy id.

## Commits

- b1a24d0 route, access policy, matrix/route-table/baseline updates, page module, runway POST, French strings
- dbfa502 stylesheet additions and the HTTP behaviour tests

## Behaviour

- `GET` and `POST /detection` are `OWNER_DEVICE` routes (also under `/devices/<id>`). Anonymous goes to sign-in, the owner and an admin reach the handler, another user's device and unknown or malformed ids answer 404. The un-prefixed form stays admin-only like every device-scoped route. Default-deny is unchanged.
- Without JavaScript: the Current setting card shows the saved setting (legacy Orly shows `Runway 07/25 ...`, pill `Runway 3`, `ORY · RWY 3`, `Watching Runway 3`; a stored LFPG 08L/26R shows `CDG · 08L/26R`); `?q=` lists matching airports as links (accent and case insensitive, 20 max, live count region always present, singular/plural/none/capped wordings); `?airport=` shows one `.runway-card` per runway with the real designator, bearing, length and surface; the saved runway is preselected and carries the Current badge; a single-runway airport is preselected; unknown airport is a 200 page state. GETs never write (tested by comparing config bytes).
- `POST` validates mode, airport and runway against the catalogue on the server and re-renders at 200 with the exact inline error and nothing written. Success is a 303 to the scoped page with the "Detection saved" pending-tone flash. LFPO 07/25, 06/24, 02/20 store `tracked_runway` `3`, `06-24`, `02-20` and no `detection` key; any other runway stores one `detection` object, both through `server.detection.apply_runway_selection`. The Origin gate (403) runs before routing.
- The search term is control-character stripped, capped at 60 characters and escaped everywhere it is echoed; it never reaches a redirect or path.
- Display stays the active nav item on `/detection` (a child-page parent map in `app.py`, no tab added, `ui_nav.py` untouched).
- All page strings are `detection.*` messages with French in `companion/i18n_fr/detection.py`; the frame text rows are English with `lang="en"`; no "NM" text anywhere (tested EN and FR).

## Verification

- `pytest companion/test_detection_page.py` 55 passed (search, cards, POST, rejections, 404 matrix, Origin, escaping, French, no NM).
- Plan verify set (access matrix, route table, render baseline, device routes, i18n, suite/structure guards, contrast): green.
- `pytest companion -m "not browser" --ignore-glob='companion/test_browser_*'`: 3740 passed, 3 skipped (root permission bits).
- `stub-server/test_phase47_freeze.py` 21 passed. ruff clean, mypy clean (28 files), function-size gate (905 functions, none over 80), comment-history check exit 0.
- `grep -c "@supports selector(:has(\*))" companion/static/style.css` is still 1. No `required` attribute on detection-form controls.
- Browser tests (Playwright): the project suite skips locally because Playwright wants chromium build 1248 and `/opt/pw-browsers` holds 1243, so the existing browser tests were not run. As a substitute an ad hoc probe (not committed) drove the pre-installed headless shell 1243 with JavaScript off at 360 and 1280 px: no horizontal overflow, Search button 44 px tall with a non-accent background while the dirty-bar Save is accent, result rows and mode segments at least 44 px, runway cards 278x94, and `?mode=position` hides the runway panel. No browser test was added in this plan.

## Deviations from Plan

**1. [Rule 3 - Blocking] Files outside the plan's list**
- `companion/flash.py` (new `detection_saved` flash key, text and pending tone), `companion/test_device_routes.py` (explicit device-scoped list and count 26 -> 28) and `test-support/companion_render_snapshot.py` (sample lists, so the baseline can record the two new route keys; `DETECTION_ROUTE` alias added to `app.py`). Baseline diff is exactly the two new keys, `GET /detection` and `POST /detection`.

**2. [Rule 3 - Blocking] Task split differs from the plan**
- Task 1's commit also contains the full page, actions and French modules because `app.py` imports them; the stylesheet and the behaviour tests are the second commit.

**3. [Design] Third `:has()` rule**
- Besides the two panel-hiding rules, one rule inside the existing `@supports` block shows the checked mode's panel (`display: block`), because the server marks the inactive panel `hidden` after a round trip and the attribute would otherwise keep a client-side mode switch from revealing it. Still one `@supports` block.

**4. [Design] Small stylesheet extras within the contract's items**
- A `.detection-link` 44 px rule for the back and Change airport links (spec spacing section), `.runway-card__detail` block lines, and the mode-segment wrap rule keyed on the radio-label structure (`.detection-modes .theme-form input[type="radio"] + label`) since these are labels, not `.theme-option` buttons. No new colour, property, keyframes or reduce block.

**5. [Interim] Position mode**
- `mode=position` posts re-render with the mode error until the position branch lands. A stored position setting renders the legacy Orly values with the "No usable location" docked warning, because the page has no location lookup yet; `render()` already accepts `location_name` and then shows `Aircraft within N km of <name>`, `NEARBY · N KM`, `Watching Within N km` (covered by a direct render test). The position panel is a labelled container with no controls.
- The page loads `dirty-state.js` unchanged. The `data-detection-nav` hooks are in the markup; the leave-guard and carried-values edit to that script belongs to the next plan, so until then a search after an unsaved edit raises the browser leave prompt.

## Known Stubs

- `companion/pages/detection_page.py` `position_panel_html` renders no controls and the POST rejects `mode=position`; both are completed by the next plan (position panel, location form, leave-guard).

## Threat Flags

None beyond the plan's threat register: T-53-25 (matrix and 404 tests), T-53-26 (foreign Origin returns 403, nothing written), T-53-27 (server catalogue validation), T-53-28 (escaping and cap tests), T-53-29 (GET leaves config bytes unchanged), T-53-30 (query field/length caps, 20-row cap).

## Self-Check: PASSED

Files exist (detection_page.py, detection_actions.py, i18n_fr/detection.py, test_detection_page.py); commits b1a24d0 and dbfa502 present. STATE.md and ROADMAP.md were not touched.
