---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 04
subsystem: companion
tags: [previews, hardware-profile, landscape, cache]
requires: []
provides:
  - "frame_preview_pixel_size(profile, size), chip_crop_box(profile), current_frame_preview_pixel_size(size)"
  - "profile-aware theme and frame preview rendering, signatures and cache names"
affects: [companion settings pages, preview routes]
key-files:
  created: [companion/test_theme_preview_profile.py]
  modified:
    - companion/theme_preview.py
    - companion/preview_images.py
    - companion/settings/theme.py
    - companion/settings/calendar.py
    - companion/settings/layout_picker.py
requirements: [HW2-04]
completed: 2026-11-14
---

# Phase 64 Plan 04: Profile-aware previews Summary

Theme and frame previews now render at the frame's hardware profile (800x480 landscape for the second type), with the profile key in cache names and signatures for non-legacy profiles only.

## Commits
- eca20b1: profile-aware helpers in theme_preview.py plus unit tests
- 5527291: routes and settings pages pass/use the device profile

## What changed
- Landscape frame previews reduce 800x480 by 2 (400x240, large) and 5 (160x96, small). A factor of 10 would leave an 80x48 thumbnail.
- Landscape chip crop box is (0, 90, 800, 390): exactly 8:3 like the 320x120 chip, keeps the aircraft and the flight text, drops the header strip. **Design decision: the owner should confirm this look in the companion walk-through (plan 64-15).**
- Legacy bytes, cache names, signatures and img sizes are unchanged: golden sha256 values were captured before the edit and are asserted in tests. Legacy callers do not even pass a profile kwarg to the render functions, so the existing monkeypatching tests are unmodified.
- Cache names add the registry profile key only for non-legacy profiles; a profile object that is not the registry's own is refused (path is None), so raw stored strings never reach a path (T-64-11). The cache bound now scales with the registry size.
- Settings pages use `theme_preview.current_frame_preview_pixel_size(size)`, which reads the device from the request scope and `device_scope.profile_for` (falls back to legacy, never raises). This avoids threading a device through a dozen render functions.

## Deviations from Plan
- **[Rule 1 - Bug] Portrait clone.** The first version keyed geometry on the legacy key, so the simulated clone `sim-ee02-clone` (1200x1600) got landscape reduction factors. Geometry (crop, factors, sizes) is now keyed on the canvas being 1200x1600; cache names still key on the legacy key. Test added.
- `frame_preview_src` did not get a profile parameter: it builds a URL, and the route resolves the profile from the device in scope, so a URL-carried profile would be pointless and untrusted input.

## Verification
- `pytest companion/test_theme_preview_profile.py test_preview_cache test_theme_preview_layout test_display_looks test_companion_app_02 test_audit3_fixes test_audit4_fixes test_config_page_05`: 276 passed.
- `pytest server/test_golden_render.py server/test_golden_giant_render.py`: 94 passed (legacy hashes identical).
- ruff, mypy, `scripts/check_comment_history.py check`: clean.
- `companion/test_battery_profile.py` could not be run: it fails at collection with a circular import (`companion.battery_chart` / `health_signals`) caused by another plan's uncommitted work in the shared tree, not by this plan. Not touched by this plan; re-run after the other plans land.

## Known Stubs
None.

## Self-Check: PASSED
