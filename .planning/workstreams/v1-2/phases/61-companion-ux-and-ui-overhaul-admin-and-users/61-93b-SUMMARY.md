# Phase 61 Plan 93b: Location map under the iPhone status bar Summary

**Finding: the stylesheet already paints the phone map from y=0 to the window bottom; the dark bands in the iPhone capture are Safari's own chrome. The one change that can give the owner a full-bleed map on iPhone is the Home Screen web-app mode, now enabled.**

## Investigation

- `viewport-fit=cover` is present on every shell. `.map-ready .place-map` is `position: fixed; inset: 0; min-height: 100lvh`; the header floats (`position: absolute; top: 0`) padded by `--safe-top`; the search, chips and sheet start at `--place-top = 52px + --safe-top`. No opaque band or ancestor transform exists.
- The capture is consistent with `env(safe-area-inset-top)` being 0 and the layout viewport itself starting below the status bar (the header logo and search sit at the same y either way). A normal Safari tab does not let page content under its status bar or toolbars, so a fixed map cannot reach them. This is browser behaviour, not a CSS layout fault.
- With the insets forced to 59px / 34px in Chromium at 390x844 and 360x..., the map box is top 0 to window bottom, left/right edge to edge, and the header, search field and tab bar clear the insets, in both themes; screenshot rows 0, 2 and the last rows show map pixels, not the page floor.

## Change

- `companion/ui_base.py`: every shell carries `mobile-web-app-capable`, `apple-mobile-web-app-capable` and `apple-mobile-web-app-status-bar-style=black-translucent`. A page added to the Home Screen then runs without browser bars and the map paints under the status bar and home indicator, controls offset by the (then non-zero) safe-area insets. No CSS change; desktop unchanged.
- Tests: `companion/test_browser_location_full_bleed.py` (new; map box, inset clearance, edge pixels; 360/390, light/dark, plus desktop); `test_shell_meta.py` asserts the status-bar meta on every shell. Render baseline, sign-in digests updated.

## Not verifiable without a real device

- Whether iOS 26 Safari (a normal tab, not the Home Screen app) ever lets a fixed map render under its status bar or bottom toolbar: Chromium cannot emulate this, and no CSS available here is known to force it. If the owner still sees bands in a Safari tab, Home Screen install is the supported route. The black-translucent behaviour itself is also device-only; only the CSS side with forced insets was measured.

## Deviations

None. Artefacts: scratchpad/shots93b/phone_light.png, phone_dark.png (forced insets).
