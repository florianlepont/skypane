# Wave 3 (F4 fleet tiles, F6 add-illustration dialog): summary

Branch: phase-68-plan-55-redesign. Variants F4 A, F6 A. Not pushed.

Commits: 2d0f9484 (F4), 15eaadba (F6).

## What changed

### F4, frame page tiles (`/fleet?frame=...`)
- State: Connection | Battery side by side, then Firmware full width (`fleet-tiles--rows`,
  `fleet-tiles__span`, `fleet-tile--wide`). The connection tile shows "Last check-in" and
  "Next wake" as two label/value blocks (`fleet-stats`) instead of two text lines.
- Settings: the glass group is gone; the Settings section holds the save form with two full-width
  tiles (`console_fleet_view._tiles_block`).
  - Wake interval tile: one control in minutes (1 to 60, step 1): a number field, - / + buttons,
    5/15/30/60 shortcuts, the value as the tile headline and a "Default" tag when it equals the
    deployed default (`SKYPANE_SLEEP_S`), hint "1 to 60 min, in 1 min steps. Default: N min.".
    More room than the mockup/state tiles: tile padding `--space-lg` (state tiles `--space-md`),
    larger gaps between heading, caption and controls, a 58 % control column from 440 px.
  - Diagnostic LED tile: wide tile, same switch, same quick-switch form and ids (default on).
- The posted field stays `wake_interval_s` (= minutes x 60, 60 to 3600, a hidden field kept in sync
  by `value-controls.js`). Without a script the number field itself posts `wake_interval_min` and
  `form_post.resolve_wake_interval` converts it (the step buttons and shortcuts are script-gated).
  An interval already on disk that is not a whole minute keeps its exact seconds until the minutes
  change.
- Removed: the seconds field, the unit/"· N min" readout, the range slider (`wake_slider_html`,
  `WAKE_SLIDER_*`, gated `data-value-control` for the wake interval). Quiet-hours dial untouched.
- EN/FR: new ids `display.wake_interval_minutes_input`, `..._unit_min`, `display.wake_minutes_value`,
  `..._default_tag`, `..._range_hint`, `..._default_hint`, `..._shortcuts`, `..._decrease`,
  `..._increase`; removed the orphans `display.wake_interval_seconds`, `..._unit`,
  `..._slider`, `display.uses_server_default`.

### F6, add-illustration dialog (Airlines editor)
- Dialog reads: one-line title "Add an illustration", subtitle "Airline" or "Airline · A333", the
  aircraft type (a fixed chip when opened from a type row; a select, shown first, when opened for
  an airline without artwork), one drop zone with preview, a compact constraint list
  (Transparent PNG / At least 1200 px wide / Landscape), then an action row Cancel / Upload at the
  end. Upload (a shared `btn--primary`, re-attached to the form by `form=`) stays disabled until a
  file is chosen or dropped; Close/Save show for the other dialog modes.
- A type row's "Add artwork" (type without its own picture) now opens that dialog with the type
  fixed (`data-view-panel-fixed-type`; the upload address already carries `default_type`). Without
  a script the old plain upload form stays on the row (hidden by `.js .airlines-act-nojs`).
  "Change artwork" is unchanged (immediate upload).
- The "..." menu now sits on the line of the artwork button (the label's global bottom margin was
  pushing the button up 4 px); the type-row buttons are 44 px.
- EN/FR: `airlines.cancel`, `airlines.constraint_transparent_png`, `..._min_width`,
  `..._landscape`. French upload button reads "Téléverser" (existing id `airlines.table_upload`).

## Decisions to review
- F4: the mockup's single "Wake interval" tile text ("Par défaut" tag) is driven by the real
  deployed default, not a fixed 15 min. With no deployed default no tag and no "Default:" hint show.
- F4: the 13 rows of the mockup's parameter table are all kept (header, anchors, sidebar, the four
  state facts, battery tile, firmware states/link, wake interval, LED, save bar, Access). The
  gauge sentences (`wake_gauges_html`) stay in code unrendered, as before.
- F4: the Settings tiles are plain tiles, so the `/device` settings page's "card title" role no
  longer applies to them; `test_browser_ux_04` now checks the two tile labels instead.
- F4: the measured step count of the "change the refresh interval" journey (U4c) dropped from 4 to
  3 (the field is reachable without a scroll); `MEASURED["U4c"]` updated.
- F6: only the type-row "Add artwork" and the existing Known-by-name "Add" button open the dialog;
  the in-page resolve step (no script) keeps its own form with its in-form Upload button.
- F6: the F6 mockup's "Replace" button inside the preview and the size/format badge were not built;
  the native file input stays the "choose a file" control next to the drop zone.
- F6: menu labels were already the short ones, left as is.

## Tests and gates
- Rewritten (not skipped or loosened): slider tests (`test_browser_ux_quiet_wake`, config page 01/03/05,
  companion_app 03/04b/05), tile grid/heading tests, LED switch selectors, upload-form markup tests,
  keyboard-order test of the drop zone (type first now), resolve button tests.
- New: `companion/test_browser_fleet_wake_tile.py` (9, tile fit at 360/1280 EN/FR, steppers,
  shortcuts, Default tag, Cancel restore, save as seconds, no-script save) and
  `companion/test_browser_airline_add_illustration.py` (11: fixed chip, select first, actions row,
  Upload waits, menu alignment, no-script form).
- ruff, mypy, `check_function_size.py check --max 80 server stub-server` (none over 80),
  `check_comment_history.py check`: clean. `companion/app.py` 1491 lines; `value-controls.js` 858,
  `panel-lookup.js` about 910.
- Full `companion test-support scripts` run (after F6, before its last test fixes): 11935 passed,
  3 skipped, 9 failed; the failures were `test_render_baseline` (needs the orchestrator's baseline),
  two flaky toast timing tests (pass alone), and the ones fixed afterwards
  (`test_suite_guards` G12 import, `test_browser_resolve_buttons` shared `btn` class,
  `test_browser_ux_02` visible Close). The fixed files were re-run green; no full re-run after them.

## Not done
- `render_baseline.json` not regenerated (orchestrator, end of plan); `test_render_baseline` fails
  until then.
- The components page and the sketch skill do not yet show the new Settings tiles or the
  add-illustration dialog layout.
- F6 preview-internal "Replace" button and format badge (see above).
