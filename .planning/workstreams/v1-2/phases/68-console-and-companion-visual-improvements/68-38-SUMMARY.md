---
phase: 68-console-and-companion-visual-improvements
plan: 38
subsystem: companion
tags: [health-page, battery-card, chart, gauge, render-baseline]
key-files:
  created:
    - companion/battery_card.py
    - companion/test_battery_card.py
    - companion/test_browser_battery_card.py
  modified:
    - companion/battery_chart.py
    - companion/draw.py
    - companion/health_rows.py
    - companion/pages/health_page.py
    - companion/static/battery-trend.js
    - companion/static/style-admin.css
    - companion/static/style-c-console.css
    - companion/static/style.css
    - companion/i18n_fr/health.py
    - companion/testdata/battery_chart_baseline.json
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-20
---

# Phase 68 Plan 38: Health Battery card

The owner-approved redesign of the Battery row (`68-MOCKUP-battery.html`). The row stays one flat, always-open row of the Health rows card (no chevron on the row, same `#health-row-battery` id and `data-state`).

## What was built

- **Hero** (`battery_card.py`): a 270 degree gauge (`draw.arc_gauge`, new `tick_fraction`) with the percentage as hero and a tick at the 20 % mark (no label on it), green above and amber below; the status pill (icon + words) with the verdict; the voltage once; one "Last reading . date time . age" line (live relative age). The old header repeat ("77% . 3969 mV") and ring line are gone. The charging pill is in the row header, only when present.
- **Verdict**: the existing words ("Level looks normal", "Dropping faster than expected"); a reading under the low-battery mark (`battery.LOW_BATTERY_DISPLAY_MV`) says "Level is low" (new string, mock wording) with the warning icon, and the row's icon turns to the warning state (card only; the page-wide severity and the overview tile are unchanged).
- **Switch**: one segmented track, two 44 px radio segments (`role=radiogroup`/`radio`, `aria-checked`, roving tabindex, arrow keys move and select). Percentage is the default view; the voltage twin is server-rendered and hidden. Without script the control and the hover readout stay hidden and the percentage chart shows.
- **Chart** (`battery_chart.py`): no grey box, light grid with labels on the lines, faded area (a CSS mask), y-range fitted to the data (`_fit_axis`, steps of 100 mV / 20 %, never above 100 %), end marker with the latest value, three date ticks, 13-14 px text. The low-battery threshold is a dashed labelled line with the zone below tinted when the data comes within 1.5 steps of it; otherwise it is not drawn and a caption under the chart says it is below the range shown (new strings, EN and FR). Series unchanged: 90-day daily averages, fallback last readings; minimum two points (`CHART_MIN_POINTS`) as before.
- **Too little data**: dashed empty note ("Not enough readings for a curve yet", "A curve appears from 2 readings. N so far."); gauge, pill, voltage, last reading and the readings row are kept; no script.
- **Readings**: a 52 px full-width disclosure row with chevron and count ("View N readings", existing string); table Time, Voltage, Level (level = `battery.percent`, the shared estimate); newest row emphasised and tagged "Latest".
- Hover/keyboard readout kept (every point still reveals its reading), now in the chart's title row, empty and hidden until the script runs.

## Design-system divergences

1. Padding is 16 px (`--space-md`) on every section, not the mock's 20 px: the header icon and name must align with the other Health rows' icon and name columns (an existing alignment test), and the whole page uses the 16 px rhythm.
2. Header name is 16 px (mock 17 px): a row name must stay on one line at 20 px or less (existing rule).
3. No clock glyph before "Last reading": the sprite has no clock and the sprite is not extended (same rule as plan 37).
4. The row's head icon is the state icon (check/warning) like every Health row, not the mock's battery glyph in a green disc.
5. Chart caption is the existing string ("Last 3 months, daily average" / "Latest N readings"), not the mock's "Last 90 days / Daily averages" two lines. The readout sits where the mock's second line is.
6. Chart gradient: the fade is a CSS `mask-image` on the area layer, because markup may not carry `url()` gradients (draw.py contract); the end marker shows the last plotted point (the day's average on the 90-day series), which can differ by 1 % from the gauge (latest reading).
7. Chart labels are SVG `<text>` in the no-viewBox canvas (labels on the grid lines cannot be HTML spans without inline styles, which the CSP forbids); `draw.text` is new. The earlier "no SVG text" property no longer holds; labels have a card-colour halo.
8. No Percentage/Voltage control in the too-little-data state (nothing to switch), and no title row there.
9. The off-range caption follows the selected unit (the mock always printed the mV text); the date/time in "Last reading" uses the existing "20 Nov 15:59" form (no comma).
10. Chart height is one 192 px for all widths (mock 176/208).
11. Level column uses the shared curve (`battery.percent`), not the mock's linear estimate (the gauge, readings and chart all agree).

## Deviations from Plan

Tests that pinned the old card were rewritten (old fixed 3000-4200 axis, ring, voltage default, `aria-pressed`, retired range caption, seeded readout, byte baseline of the chart). `battery_chart_baseline.json` was regenerated for the new chart; `render_baseline.json` regenerated at the end (twice: once more after a last no-wrap fix to the readings table). Two shared-anatomy browser tests (row alignment, `test_fleet_state_rows_never_overlap`) now hold the Battery row to the icon and name columns only, since its verdict lives in the body.

## Tests and gates

New: `test_battery_card.py` (chart and card from markup), `test_browser_battery_card.py` (unit default, Level column, normal/low/charging/too-little-data, 44 px targets, no overflow at 320/390/1440, EN/FR, light/dark). Full suite (companion, stub-server, server, test-support, browser required): 15 527 passed before the final fixes, then the affected files re-run green (2 230 passed); `test_phase47_freeze`, access matrix and golden hashes green. ruff, mypy (46 files), function size (none over 80), comment history all clean; `companion/app.py` 1493 lines; largest JS 1227 (battery-trend.js about 250). Coverage floor not measured.

## Open questions for the owner

- Should a low reading also turn the overview tile and the page-wide severity (nav dot, banner) to warning? Today only the card does.
- The 90-day end label shows the day's average, not the latest reading; show the latest instead?
- Wanted back: the mock's two-line chart title and 20 px padding?
