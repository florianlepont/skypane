# Phase 61 Plan 44: Console Airlines editor as a table

Owner decision D33 (refined) and feedback W20 (mockup E3): the Airlines editor (`/airlines/manage`) is one table with the name edited in place, read-only prefixes, a click-to-replace artwork thumbnail, views, last seen, a reduced "..." menu and an expand chevron per airline. The user-facing Airline collection (`/airlines`, plan 61-40) is untouched.

- **New module `companion/pages/airline_table.py`:** one `<tbody>` per airline. Name cell: a form posting to the existing rename route (`data-autosubmit` saves on change; without script a visible "Save" button), plain text for owner-named airlines (no prefix to rename by). Prefixes read-only. Artwork cell: the thumbnail is the label of a file input posting to the existing illustration upload route (on change with script, an "Upload" button without); an owner-named airline still without artwork keeps its link into the existing add-artwork step. Views and Last seen come from the frame's own `runway_events` via `airline_collection` (read only; `AirlineEntry` gained `type_counts`).
- **"..." menu** (native `<details class="row-menu">`, Escape closes via modal.js): only "Reset to the original name" (the rename reset, or the manual name delete for an owner-named airline; present only when there is something to reset) and "Enlarge the artwork" (the shared lightbox, a real link to the picture without script; it carries the manual-name state so a superseded name keeps its note in the dialog).
- **Chevron:** native `<details>` in the first cell; `tbody:has(details[open])` reveals one sub-row per aircraft type seen (type code and model name, views). A type with an artwork slot of its own (the curated aircraft variants, the only keys the upload route accepts) shows its thumbnail with "Replace"; any other type says "Uses the airline's artwork". Curated variants never seen are listed with 0 views so no existing per-type upload capability is lost.
- **Unidentified prefixes:** highlighted rows (warn-tinted via tokens) at the top with a "Name it" link into the existing resolve flow (dialog with script, `?resolve=` section without); the gap strip and cards are gone.
- **Layout:** block cards below 70rem (360 px: name and menu on top, prefixes/views, artwork/last seen), a real table from 70rem; 44 px targets; tokens only; both themes.
- **Removed:** the airline sheet dialog (name, reset, type tabs), the no-script `?sheet=` section, the old list/row/sheet CSS and the sheet markup helpers in `airline_sheet.py`. `?sheet=<key>` now only puts focus in that row's name field after a refused name (the rename route's redirect is unchanged).
- **Strings:** new `airlines.col_*`, `table_*`, `name_it*`, `row_menu_aria`, `reset_original_name`, `enlarge_artwork`, `views_*`, `table_purpose`, `gap_caption` etc. in EN (source) and FR (`companion/i18n_fr/airlines.py`); orphaned sheet strings removed.

## Tests

Adapted in place (none weakened): `test_airline_sheet.py` (render tests now on the row form, menu and refusal focus; all route tests kept), `test_status_pages_04/05b/06/07.py`, `test_view_pages_02/03.py`, `test_health_resolve_dialog.py`, `test_browser_airline_editor.py`, `test_browser_overhaul_steps.py` (A8 now 3), `test_browser_overhaul_sweep.py` (a labelled file input is a hit-tested target, like radios), `test_browser_ux_01.py`, `test_browser_ux_04.py`. The two browser files whose whole subject was the removed sheet (`test_browser_airline_list.py`, `test_browser_airline_sheet.py`) are replaced by `test_browser_airline_table.py` (geometry and 44 px in 360/1280 x EN/FR x both themes, chevron by mouse and keyboard, rename on change and reset from the menu, refused name focus, uploads for an airline and a type, menu items and Escape, Enlarge, filter by name/type/prefix, gap row and Name it, needs-artwork step, resolve dialog focus, no-script chevron/Save/Upload). `companion/testdata/render_baseline.json` regenerated.

## Deviations / notes

- "Reset to the original name" appears only when an owner name exists (rename override or manual name); an airline with neither has no reset item (and no menu when it also has no artwork).
- The upload route only accepts curated keys, so a seen type without a curated variant shows "Uses the airline's artwork" without a Replace (no backend action invented).
- A one-line `section-caption` ("Rename in place, click artwork to replace it, expand for aircraft.") is always shown (a second one for unidentified rows); the site-wide caption floor test counted the removed sheet captions.
- The dialog's replace form and `panel-lookup.js`'s sheet/type-switcher code are still present (the script tolerates their absence); pruning the dead script branches is left for a cleanup.
- Step counts: A8 4 -> 3; no editor flow got longer (`61-STEP-COUNTS.md`).

## Self-Check: see the final report for the gate and suite results.
