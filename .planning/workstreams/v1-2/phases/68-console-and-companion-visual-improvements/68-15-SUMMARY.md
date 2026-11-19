---
phase: 68-console-and-companion-visual-improvements
plan: 15
subsystem: companion
tags: [location, place-map, dark-map, icon-button, i18n]
requires: ["68-01", "68-09"]
provides:
  - Location page without the visible "position found" text (R07), dark map (R08), round icon France button (R09)
affects: ["68-32"]
key-files:
  modified:
    - companion/pages/place_page.py
    - companion/ui_components.py
    - companion/i18n_fr/detection.py
    - companion/static/place-map-search.js
    - companion/static/style-place.css
    - companion/test_browser_location_polish.py
    - companion/test_browser_place_map.py
    - companion/test_browser_place_document_map.py
requirements: [CON-01]
decisions:
  - "The OWNER-APPROVED block of the mockup replaced the plan wording: mode button My position is renamed By position (Par position); only Show all of France becomes an icon button; the locate button was already round and icon-only."
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 15: Location page (R07 to R09) Summary

After "Use my position" no visible text reports the position: the pin moves and the visually hidden `role="status"` line (`place-status`) says it in English or French; the "looking for your position" note is cleared. Errors keep their visible message. "Show all of France" is a round 44 px icon button (globe) named by `aria-label` and tooltip. In the dark theme and in Auto-dark the OpenStreetMap tile pane is inverted into a dark map. The mode button "My position" is now "By position" (FR "Par position"). The hand-built runway-card pill uses `pill_html` (D-14).

## Design-system divergences

- Dark map is a CSS filter (`invert(1) hue-rotate(180deg) brightness(.9) contrast(.95)`) on the one tile pane, with `--color-map-ground` overridden to `#16140F` (the filtered land colour, measured) in `style-place.css` only; `style.css` is untouched. No new tile source.
- The phone app bar over the map used the light palette in both themes because the tiles were light; over the dark map it now keeps the dark theme's own colours (11 custom properties reset to `inherit` in two dark blocks of `style-place.css`). Without it ink and map were both dark (contrast 1.37).
- The runway overlay was not recoloured: the "runway line" is the OSM tile's own drawing, which the filter makes light on dark; the drawn overlays (pin, radius circle) already use `--color-accent`, ivory in dark (contrast with the dark ground is asserted at 3:1 or more).
- `icon_button_html` gained an optional `extra_class` argument (default unchanged output) so the page's hook classes stay.
- Existing tests that pinned a light ground or an identical app bar in both themes were changed to the new owner-approved behaviour.

## Deviations from Plan

None beyond the above. Tests were written alongside the code in each commit rather than as separate failing commits.

## Verification

- Place and gate tests: 713 passed (`SKYPANE_REQUIRE_BROWSER=1`, `test_browser_place_*`, `test_browser_location_*`, `test_place_page`, `test_i18n`, `test_structure_guards`, `test_suite_guards`, `test_detection_page`).
- ruff, `check_comment_history.py`, `check_function_size.py check --max 80 server stub-server` pass. `place-map.js` is unchanged at 1227 lines; `app.py` 1493 lines. `mypy` reports 13 existing errors (missing PIL stubs), none in touched files.
- Render baseline: the Place page is not captured. `test_render_baseline.py` fails on the `/airlines` pages (stylesheet and `list-filter.js` hashes changed by plan 14); this predates this plan. The baseline was not regenerated.
- The map under the iPhone status bar in standalone mode is checked by the owner in plan 32.

## Known Stubs

None.

## Self-Check: PASSED
