---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 05
subsystem: ui
tags: [companion, display, quiet-hours, swatches, browser-tests]
requires:
  - phase: 44-04
    provides: Display content hierarchy.
provides:
  - Dithered (light) fields and bands drawn as a stipple, distinct from solid swatches.
  - Quiet hours led by presets and native time fields, with the ring as a secondary picture.
  - Browser checks in EN/FR at 1280/390/360 px for swatches, preview containment, keyboard, save feedback.
affects: [companion-display]
key-files:
  modified:
    - companion/settings/quiet_hours.py
    - companion/settings/theme.py
    - companion/static/style.css
    - companion/test_browser_ux_03.py
    - companion/test_browser_ux_04.py
    - companion/test_config_page_01.py
    - companion/test_config_page_02.py
    - companion/testdata/render_baseline.json
requirements-completed: [CMP-03, CMP-04]
metrics:
  completed: 2026-10-03
status: complete
---

# Phase 44 Plan 05: Display swatches and Quiet hours Summary

Swatches now render the theme metadata (dithered stipple, band colour/dither), the preview image is contained, and Quiet hours leads with presets and native time fields.

## Task Commits

1. Task 1 Quiet hours: `1145dd19`
2. Task 2 swatches/preview/tests: `a9cd59f2`

## Accomplishments

- `theme.py` marks dithered fields/bands (`palette-swatch--dithered`); a band is drawn when it differs in colour or dithering (so `band_blue_field` and `band_blue_light` read correctly). CSS draws the stipple from the panel white and adds a hairline so white swatches are visible.
- Preview image gets `object-fit: contain`; no script change was needed (`theme-preview.js` already syncs to the checked chip and the no-JS output is complete).
- Quiet hours order is now caption, presets, Start/End fields, then ring and readout; names, validation and no-JS submission unchanged.
- New browser tests: swatch distinction, preview containment/keyboard/focus/save confirmation (EN+FR, 3 widths), quiet-hours order/preset/save.

## Deviations from Plan

- [Rule 3] `companion/settings/theme.py` was edited (not listed) because the swatch markup is produced there.
- [Rule 1] Updated existing locks (`test_config_page_01/02`) for the new swatch markup and card order; regenerated `render_baseline.json` (8 lines).
- The screenshot showed the preview was not visibly clipped at the tested seed; containment is enforced and tested rather than a visible bug fixed.

## Known Stubs

None.

## Self-Check: PASSED

Commits `1145dd19`, `a9cd59f2` present; full suite 3480 passed, ruff, mypy, comment-history and function-size gates green.
