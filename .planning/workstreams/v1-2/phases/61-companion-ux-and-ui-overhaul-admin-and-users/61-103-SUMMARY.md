---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 103
subsystem: companion-ui
tags: [w169, location-map, safari-tint, temporary-variants]
key-files:
  modified:
    - companion/static/style.css
    - companion/static/place-card.js
    - companion/test_browser_ux_helpers.py
    - companion/test_browser_location_full_bleed.py
    - companion/test_browser_remaining_audit_fixes.py
    - companion/testdata/render_baseline.json
  created:
    - companion/test_browser_location_bands.py
metrics:
  completed: 2026-11-09
---

# Phase 61 Plan 103: Location bars tinted with the tile ground colour (W169) Summary

On a phone in a browser tab the Location page now paints the OpenStreetMap tile ground colour (the light land colour, declared once as `--color-map-ground: #F2EFE9` in the theme-independent `:root` block, the same in both themes) behind the map and along both screen edges, instead of the dark theme colour. Four temporary variants can be compared on the device with a `?bands=` query.

## What changed

- `style.css`: `html` and `body` take `--color-map-ground` (the sky gradient is dropped on that page); a: two `position: fixed` strips, full width, `pointer-events: none`, `z-index: 1` (below the header and tab bar), 12px plus the safe-area inset tall (top and bottom); c: 1px strips. Only at phone widths, only in `display-mode: browser`, only while the map runs.
- `place-card.js`: `bandsVariant()` reads `bands` from the address (a, b, c, off; anything else is a), sets `data-bands` on `<html>` (a fixed attribute value, the query text is never written to the page), and points both `theme-color` tags at the ground colour (light in both themes) for a, b and c. `off` leaves the tags and the page untouched. The CSS rules require `[data-bands]`, so without the script nothing changes.
- Dark-theme overlays: the header, search row, mode chips, sheet and tab bar keep their own surfaces (the search row is opaque; the tab bar is 86% opaque); the tests assert both.

## TEMPORARY variants (remove after the owner picks one)

| `?bands=` | Behaviour |
|-----------|-----------|
| (none) or `a` | ground colour behind the map + 12px fixed strips at both edges (default) |
| `b` | ground colour behind the map only, no strips |
| `c` | ground colour behind the map + 1px full-bleed strips |
| `off` | no tint: the previous dark look, for comparison |

URLs to try on the iPhone (Safari tab, not the Home Screen app; replace the host and add your device prefix if the app serves the page under `/devices/<id>/`): `/detection?mode=position&bands=a`, `/detection?mode=position&bands=b`, `/detection?mode=position&bands=c`, `/detection?mode=position&bands=off`. Removal: delete `bandsVariant()` and the `c` / `off` handling in `place-card.js` and the `data-bands` selectors in `style.css`, keeping the chosen variant.

## Honest limits

No iPhone was available. Whether Safari (iOS 26) tints its bars from the page background, from fixed strips of a given size, or from neither is Safari's behaviour and is NOT verified. The tests check geometry, colours, meta tags and the variant switch in Chromium only. The Home Screen web-app mode cannot be emulated in Chromium (`display-mode` is not an emulatable media feature): the test makes the page script see that mode (so it does nothing) and the CSS is gated by `display-mode: browser`; the CSS gate itself is not exercised by a test.

Probable remaining contributor (not changed here, needs an owner decision): the app bar on the Location page has a fade (`.site-header::before`, the theme canvas colour at 85% fading out over the top of the screen, z-index 15). In the dark theme that is a dark gradient over the light tiles at the very top, above the strip, and the screenshots in `scratchpad/shots103/` (dark, 390px) show it: the top of the page still looks dark under the header while the bottom strip is the light ground. If the owner's top band stays dark with every variant, the fade is the cause; the options are a lighter/shorter fade or none on phones in browser mode (the dark logo/frame-button readability then needs its own surface).

## Deviations from Plan

- [Rule 3 - Blocking] `_set_ui_theme` (shared test helper) proved the override reached the page by comparing the painted canvas in both themes; the tinted Location page deliberately paints the same canvas in both, so the helper now compares the theme's `--color-canvas` token instead of the painted canvas (text colour is still compared, the painted canvas is still returned and checked to settle). The override-reaching check is not weaker.
- Existing pixel tests of the map's edge rows (`test_browser_location_full_bleed`) and the strip test (`test_browser_remaining_audit_fixes`) were retargeted in place to the new colour, size and the dark top fade (the top strip is covered by computed style in the new test file).

## Tests

New `companion/test_browser_location_bands.py`: per variant at 390 and 360, both schemes: strip geometry/colour/pointer-events, html/body background, meta tags, forced safe-area insets, map fills the window, header/search/tab bar clear the insets and own their hit-test centres, unknown or hostile `bands` values fall back to a without reflection, a wide screen and the (simulated) web-app mode are unaffected.

## Known Stubs

None.

## Threat Flags

None (client-side read of a query value restricted to four fixed outcomes).
