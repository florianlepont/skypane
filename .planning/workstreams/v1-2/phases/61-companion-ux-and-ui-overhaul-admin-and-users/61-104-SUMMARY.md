---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 104
subsystem: companion-ui
tags: [w170, w152, location-map, iphone]
metrics:
  completed: 2026-11-10
---

# Phase 61 Plan 104: Revert the iPhone tint experiments, fix the fixed map's own background (W170) Summary

The tint experiments (61-99 strips and theme-color rewriting, 61-103 variants, 61-93b Home Screen meta) are removed; the one change kept is the fixed map container background, which is now the light tile ground colour.

## Hypothesis (NOT verified: no iPhone available)

iOS 26 Safari tints its top and bottom bars from fixed elements that touch the screen edges. On the Location page the only such element was `#place-map` (`position: fixed; inset: 0`), whose background was the theme canvas colour (dark in the dark theme) although the visible tiles are light. Other pages have no fixed edge element, so their bars take the page background and look full bleed. Fix attempted here: `.map-ready .place-map` takes `--color-map-ground` (#F2EFE9, theme independent). Whether this removes the bands on a device can only be checked on an iPhone. W152 is therefore NOT closed as a platform limit; the ledger's earlier W170 wording saying so is corrected (a "Superseded" line is added to Round 15 of 61-OWNER-VALIDATION.md).

## Removed

- 61-99 / 61-103: the `.place-stage::before/::after` edge strips, the `html`/`body` ground background, `?bands=` and `data-bands` logic, `wireBarTint` and the theme-color meta rewriting (place-card.js), `test_browser_location_bands.py`. The `_set_ui_theme` helper change is reverted (it compared the painted canvas; the tinted html/body was the only reason for the token comparison). Tests retargeted: full-bleed, remaining-audit-fixes (strip tests removed with the strips), place-boot, overhaul sweep warm-fill rule (now skips only `#place-map`).
- 61-93b: `WEB_APP_META` (mobile-web-app-capable, apple-mobile-web-app-capable, status-bar-style black-translucent) in `ui_base.py` and its assertion in `test_shell_meta.py`. Adding the site to the Home Screen behaves as a plain Safari shortcut as before.
- `display-mode: standalone`: no rule exists in the stylesheet or scripts (grep), so nothing remained that could move the tab bar; the tab-bar jump came from the web-app meta tags (standalone mode), now gone.
- Kept: 61-88 full-bleed map CSS, safe-area handling that predates 61-93b, search loading row, label clearance, nearest-airport offer, radius.

## Edge scan (fixed/absolute elements and pseudo-elements touching the top or bottom edge)

- `#place-map`: now the ground colour (changed).
- `.site-header::before` (app bar fade, canvas colour 85% to transparent, dark in the dark theme) started at y=0: it now starts `--space-xs` (4px) below the top edge, so no dark surface touches it; the logo and frame button stay readable on the fade.
- `.tab-bar`: a floating pill with a gap below it, does not touch the edge. `.place-panel`: transparent.
- `.place-boot` (loading placeholder, fixed, both edges, `--color-secondary`, theme dark): NOT changed. It exists only before the map is ready (the loading flash); recolouring it light would put the dark-theme skeleton shapes on a light ground. If the device still shows dark bands during loading, this is the next candidate.
- Splash overlay: only during the splash; hidden otherwise.

## Tests

New in `test_browser_location_full_bleed.py` (390/360, light/dark): the fixed map box is `rgb(242, 239, 233)` and touches both edges; a geometry/colour scan finds no dark opaque or gradient fixed/absolute element or pseudo-element touching the edges (verified to fail with the old fade). Existing layout tests kept (map fills the window, header/search/tab bar clear forced insets). Screenshots (390x844, 360x740, both themes): scratchpad/shots104/.

Render baseline and sign-in digests (nf, nf2, forb, shell) updated for the removed meta tags.
