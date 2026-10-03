---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 09
subsystem: ui
tags: [companion, health, battery-chart, i18n, accessibility]
requires:
  - phase: 44-08
    provides: Outcome-first Health content and revised signals.
provides:
  - Percentage and voltage battery chart views, both server-rendered from existing telemetry.
  - Keyboard, pointer and touch operable unit switch layered on a no-script voltage default.
  - Status content kept to a readable measure with the current result leading its detail.
affects: [companion-health]
tech-stack:
  added: []
  patterns: [Server-rendered twin views toggled by hidden attribute from the existing page-local script.]
key-files:
  created: []
  modified:
    - companion/battery_chart.py
    - companion/pages/health_page.py
    - companion/i18n_fr/health.py
    - companion/static/battery-trend.js
    - companion/static/style.css
    - companion/test_browser_ux_health_drawings.py
    - companion/test_status_pages_01.py
    - companion/test_status_pages_03.py
    - companion/test_status_pages_04.py
    - companion/test_status_pages_05b.py
    - companion/testdata/battery_chart_baseline.json
    - companion/testdata/render_baseline.json
key-decisions:
  - "Both units are rendered by the server (percentage via battery.battery_percent); the script only swaps visibility and never converts."
  - "Voltage stays the no-script default so the existing chart contract and tests keep their meaning; the control ships hidden and is revealed by the script."
  - "The readable measure applies to tiles, banner, chart and day band, not to the nested table sections that need the full column."
requirements-completed: [CMP-03, CMP-04]
metrics:
  completed: 2026-10-03
status: complete
---

# Phase 44 Plan 09: Status Battery Units and Layout Summary

Status now offers a Percentage/Voltage switch over the battery chart, drops the "Battery · 3 months" range label, keeps its tiles to a readable desktop width and sets the current result larger than its supporting detail.

## Reconciliation with earlier commits

- The daily activity band had already moved from Home to Health (adcd4218); this plan only verifies placement in browser tests (exactly one `.day-band`, outside the battery card) and adds no second data read.
- The raw-readings table stays behind its native disclosure (restored earlier); its summary is now muted, regular weight and label-sized rather than accent coloured.
- The heading text lost its `%d` month interpolation; the French catalogue key `health.battery_months` was replaced by `health.battery`.

## Tasks

1. Dual-unit chart data (ded7f89a): `battery_unit_chart()` builds the voltage view and a hidden percentage twin (0-100 axis, 20% threshold, `data-reading` text from `battery.battery_percent`), plus the hidden-until-script control. French strings added. Heading helpers, the chart byte baseline and the heading tests retargeted to the retired label; new served-markup tests cover the twin, control and French labels.
2. Unit switch and layout (19a8c314): `battery-trend.js` swaps views, keeps the readout in the shown unit and carries the revealed point across; CSS for the control, muted disclosure, `.status-page` measure (760 px at 960 px and up for non-nested blocks) and larger verdict. Browser coverage at 1280/390/360 px in EN/FR: switching by pointer, Enter and Space, visible focus, readout agreement, touch tap, no overflow, one day band, tab bar visible below 960 px, no-script default, readable width and verdict hierarchy. Render baseline regenerated (Health pages only).

## Deviations from Plan

- **[Rule 1 - Bug]** The first width constraint (whole page at 760 px) broke the French registry table and disclosure tables at 1280 px; the measure now excludes `.page-section--nested` blocks.
- Existing page-level tests that counted one chart now scope to the voltage view (the page carries two views); the existing 360 px chart check scopes its axis labels to the shown view.
- Voltage rather than percentage is the server default (see key decisions).

## Known Stubs

None.

## Verification

Full `./scripts/run-all-tests.sh` (Chromium required), ruff, mypy, comment-history check and function-size gate all green.

## Self-Check: PASSED
