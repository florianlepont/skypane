---
quick_id: 261005-hrw
status: complete
branch: claude/health-rows
---

# 261005-hrw summary: Health as one card of rows

## What changed

- `companion/health_rows.py` (new): generic row, group band, card, facts and ring components. The
  state icon is one of four shapes with a visually hidden state word; a warn or error row renders
  open.
- `companion/pages/health_page.py`: one builder per row (`_connection_row`, `_battery_row`,
  `_flight_data_row`, `_sources_row`, `_identification_row`, `_backup_row`); `render()` emits the
  anomaly toasts, the rows card, then the unchanged "Compagnies non identifiées" card. The tile
  builders and their `device_html` / `pipeline_html` / `corroboration_html` fragments are gone;
  `compute_health_state()` now also returns the raw `inputs` and `next_wake_clock`.
- `companion/health_sections.py`: regularity block removed (follow-up: grid, key, captions and their messages gone); day band, resolution-rate
  tile and statistics card removed.
- `companion/static/style.css`: rows card CSS; the 760 px cap and the `.status-page` tile rules
  removed; one elevation rule on the page.
- `ui_nav.py` / `freshness.js`: the Health swap region is each row's summary.
- i18n: new row strings, orphaned strings removed, FR catalogue updated.
- Tests: status-page structure tests re-pointed at rows; browser drawing tests open the rows by
  keyboard first; new browser test for one width and aligned columns (6 widths); render baseline
  regenerated (only the four Health entries changed).

## Notes

- `.battery-trend-section` card chrome, its status modifiers and `.page-section--ok|warn|error`
  are now unused by Health (the chart wrapper is the card-less `--embedded` variant); the rules and
  their pins were left in place.
- `draw.day_band()` stays in the shared module (its own unit tests remain) but no page draws it.
- Battery row: no range caption (still retired).
