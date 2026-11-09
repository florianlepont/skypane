---
phase: 62-plane-screen-redesign
plan: 08
subsystem: render
tags: [status-screens, giant-lettering, icons, landscape]
requires: [62-06]
provides:
  - "giant.status.build_status(kind, size, *, quiet_hours_until, source_fault, battery_low, runway_id, flat)"
  - "giant.icons.icon_mask(kind, height)"
  - "layout.build_canvas draws hold states with the calm screens for giant layouts"
  - "pairing_image.render_retired_image draws the calm retired screen"
key-files:
  created:
    - server/plane/render/giant/icons.py
    - server/plane/render/giant/status.py
    - server/test_giant_status.py
  modified:
    - server/plane/render/layout.py
    - server/pairing_image.py
    - server/test_pairing_image.py
    - server/test_giant_dispatch.py
    - server/test_poll_loop.py
    - server/test_pipeline_e2e.py
key-decisions:
  - "Icons reuse the production glyph drawers unchanged through a coordinate-scaling draw proxy at 4x supersampling, reduced and thresholded to a binary mask"
  - "Body texts are the existing style constants (display off reads 'Switched off from the companion page.' / 'Turn it back on there anytime.', not the mock's wording)"
  - "Watching headline derives from the runway id (default gives RUNWAY / 3; 06-24 gives RUNWAY / 06/24)"
requirements-completed: [PSR-07]
completed: 2026-11-09
---

# Phase 62 Plan 08: Calm status screens Summary

The seven non-flight screens (watching, quiet hours, display off, battery empty, no connection, updating, retired) now share one calm layout in portrait and landscape, wired into `build_canvas` for giant layouts and into the retired image.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Scaled icons and calm builders | fc0bf00 | `giant/icons.py`, `giant/status.py`, `test_giant_status.py` |
| 2 Wire hold states and retired | abb63a6 (layout.py and pairing_image.py, committed by the orchestrator as a wip commit mid-run), 9c57977 (tests) | dispatch, retired screen, updated pins |

## Design

Portrait (1200x1600, geometry scaled by width): 110 px margin, icon 120 px tall at (110, 120), label Inter Bold 52 px at y 262, two Anton lines in slots between y 380 and 1180 (max 330 px, shrunk per line to fit the width, ink flush left at the margin, whole words), body Inter Bold 40 px from y 1290 with 58 px steps. This is the geometry of `MOCK_ICON=calm`.

Landscape (800x480, designed here, same calm look in one column): margin 6.9% of the short side (33 px), icon 12.5% (60 px) top-left, label 22 px under it, two Anton lines in a slot from 150 to 379 px (font about 91 px, so lettering fills the left half of the width and leaves the right side empty), body 20 px with 28 px steps ending at the bottom margin. Everything is fractions of the height, so other landscape sizes work.

Colours: watching is white with black ink; the other six use the dithered dark field (black toward white at 0.4) with white ink. No theme colour or band. `flat=True` gives a black field with no dither (exactly black and white), for the firmware masks in plan 09. `battery_empty` ignores every argument but the size. Battery-low glyph and source-fault badge are drawn on watching, quiet hours and display off in the screen's ink (portrait through the existing glyph functions, landscape through `landscape_card`).

Icons: the production drawers (runway, moon, power, empty battery, alert, updating) run against a scaling `ImageDraw` proxy at 4x the target size, are box-reduced and thresholded at 128, so edges are clean and the mask is pure ink (legal palette). Cost: all 14 screens render in about one second.

Hold dispatch: for a giant layout id, states battery_empty, display_off, quiet_hours and empty (or no flight) draw `giant.status` at the profile size (or 1200x1600 without a profile); classic, `layout=None` and sizes the family does not support keep the legacy builders and bytes. Retired: landscape profiles get the landscape variant at their own size; portrait profiles the 1200x1600 screen scaled to fit as before. The pairing screen is untouched (hash 3e5d41f5... unchanged; a dedicated test pins it).

## Render comparison

Rendered to `/tmp/claude-0/-home-user-skypane/2e32b3fc-5099-5923-b87b-8baec7f1d443/scratchpad/status-62-08/`: `p-sheet.png`, `l-sheet.png` and per-screen `p-<kind>.png`, `l-<kind>.png`. Against `status-screens-calm.png` the portrait screens match in layout (margins, icon, label, lettering sizes, body position). Visible differences: body text is Inter Bold from the existing copy, so display off reads "Switched off from the companion page. / Turn it back on there anytime." instead of the mock's line; icons are crisper (supersampled) and the power icon is a little larger; the dither is the production 0.4 pattern (the mock used a smoother grey). In landscape the white body text on the dither is the least legible element (same as the existing landscape hold screens).

## Deviations from Plan

**1. [Rule 3 - Blocking] Existing tests pinned the old hold bytes.** `test_giant_dispatch.py::test_hold_screens_ignore_the_layout` asserted the opposite of this plan and is replaced by `test_hold_screens_follow_the_layout_family`. `test_poll_loop.py` (quiet hours, display off x2, battery empty x3) and `test_pipeline_e2e.py` compared panel.bin against `build_canvas(None, state)` and now pass `layout=screen_layouts.DEFAULT_LAYOUT_ID`, as the poll cycle does. The retired golden hash in `test_pairing_image.py` is updated to 7222f198...3f04 (the plan expects this).

**2. Retired screen keeps no `_RETIRED_LABEL/_RETIRED_BODY` in pairing_image.py**; the copy lives in `giant.status.RETIRED_BODY_LINES` (no other users).

## Live-frame impact

A frame on a giant layout (the default is B) shows the calm hold screens from the first poll cycle after deploy; a battery-empty frame repaints once because its bytes changed. Frames on "classic" are unchanged.

## Verification

ruff clean, mypy (31 files) clean, function-size gate (none over 80), comment-history clean. Full `server` + `stub-server` pytest: 3397 passed, 4 skipped. Golden suite and `test_render.py` green with the baseline files untouched. No Phase 47/47.1, hardware/ or firmware files touched; `state.advance-plan` not called.

## Known Stubs

None.

## Self-Check: PASSED

Files exist; commits fc0bf00, abb63a6 and 9c57977 present.
