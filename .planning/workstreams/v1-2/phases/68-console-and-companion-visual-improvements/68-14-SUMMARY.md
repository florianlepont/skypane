---
phase: 68-console-and-companion-visual-improvements
plan: 14
subsystem: companion
tags: [airlines-editor, dialogs, filter, i18n]
requires: ["68-01", "68-06"]
provides:
  - companion/pages/airline_rows.py (unidentified row, rename and name dialogs, filter chips)
affects: ["68-23"]
key-files:
  created: [companion/pages/airline_rows.py]
  modified:
    - companion/pages/airline_table.py
    - companion/pages/airlines_page.py
    - companion/static/style-airlines.css
    - companion/static/list-filter.js
    - companion/i18n_fr/airlines.py
requirements: [CON-01]
decisions:
  - "The approved mockup's OWNER-APPROVED block replaced the plan wording: Name it / Rename dialogs instead of Complete / Edit buttons, artwork per aircraft type."
  - "list-filter.js matches a chip against a space-separated list of kinds on a row (data-filter-kind), so one row can be both Seen and No artwork."
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 14: Airlines editor (R27 to R31) Summary

The Editor now follows the owner-approved mockup (`68-MOCKUP-editor.html`): an unidentified prefix is one compact row with a "Name it" button whose dialog (bottom sheet on a phone, centred card on desktop, through `ui_modal`) posts to the unchanged resolve route; Ignore and the aircraft-type field are gone; an airline's name is plain text with Rename (dialog), Reset to the original name and Delete my name in its "..." menu; the table column is the airline's default type (picture and code); each aircraft-type row has one upload entry (Add artwork or Change artwork) and a menu with Set as default type and Delete the artwork; the filter bar has five kind chips with counts.

## What was built

- `companion/pages/airline_rows.py` (new): the compact unidentified row with its name dialog, the rename dialog and menu entry, the filter kinds and chips. `airline_table.py` calls it; `airlines_page.py` shrank by one line (1287 to 1286).
- The aircraft-type row: `has_own` picture says "Own artwork" and offers "Change artwork", otherwise "Uses the default type's artwork" and "Add artwork". The menu lists Set (or Remove as) default type and Delete the artwork, the latter only when an uploaded picture exists (an item-less menu is not rendered).
- `list-filter.js` (979 lines): a row's `data-filter-kind` is a list; unchanged for single kinds.
- CSS in `style-airlines.css`: compact gap row, default-type cell, even padding of the "..." menu, column widths so "Last seen" no longer runs under the menu, five chips wrapping on a phone.
- EN and FR strings in `i18n_fr/airlines.py`; the ids of Ignore, the type select, Customise, Back to the default and the old artwork column are removed (no orphan French id).
- Routes, form field names, CSRF fields and access rules unchanged (`test_csrf`, `test_access_matrix` green).

### R30 and `has_builtin`

The owner's approved policy (decision 3) replaced plan policy A: one upload entry, no separate Customise or Back to the default, and "Delete the artwork" only when an uploaded picture exists (the type then shows the default type's picture again). `has_builtin` means a vendored PNG exists for the exact `{airline}-{type}` slot in `server/assets/icons/illustrations/`; for a type row it is a built-in picture for that type. It still feeds `has_own` (what the row says) but no longer drives a menu item.

### "Marchand" (R29)

The approved block lists it as still open and gives no answer, so nothing was built for it. It still needs the owner's answer.

## Design-system divergences

1. **No suggestion tag and no round check button.** The mockup shows a Suggestion tag with a proposed name and a check button; the OWNER-APPROVED block (item 5) says how the suggestion is produced (local list or AI service) is still undecided, and there is no source in the code. I built the closest compliant version: every unidentified row has "Name it" (a dialog with the known-names suggestions the field already had). The row has a place for it; nothing renders a suggestion.
2. **Aircraft seen on the unidentified row.** The mockup's second line lists the aircraft types seen; the unresolved-prefix data holds only the example callsign, count and last seen, so the row shows those.
3. **Amber "Unidentified" chip kept on the row.** Not in the mockup; kept because `test_browser_console_groups` (Phase 61) asserts it and it is the non-colour signal for the highlighted row. The row is slightly taller than the mockup (at most 130 px at 360 px).
4. **Segmented chips wrap on a phone** onto a second row (the shared segmented component; rules in `style-airlines.css` keyed on `.filter-bar--chips`) instead of the mockup's scrolling pill row; the existing chip component has no scrolling variant. Counts are in the chip text ("All (36)"), which Phase 61 had removed elsewhere; the owner's approved block asks for counts.
5. **"Known by name only" chip and block are not here.** They belong to plan 23 (D-15); this plan ships All, Unidentified, No artwork, Seen, Not seen yet.
6. **Rename only for built-in airlines.** An airline named by hand has Delete my name (sends the prefix back to the unidentified list) and no Rename, because the rename route is keyed by the built-in name. The mockup shows Rename on every row.
7. **Airline-level upload kept for airlines with no aircraft-type row.** Decision 1 says artwork belongs to types, but an airline with no type row would be a dead end, so its menu keeps "Change artwork".
8. **Default-type column shows the airline's own picture** when the default type has no picture of its own (so the cell is never empty), and "—" when no default type is set.
9. **A refused rename reopens the dialog** (`open` attribute, promoted to modal by `modal.js`) on that airline's row, instead of focusing an inline field.

## Walkthrough step count

`test_a8_rename_an_airline_in_the_editor` measured 3 steps; with the approved Rename dialog it is 5 (tap menu, tap Rename, type, Enter plus the opening tap on Editor). `MEASURED["A8"]` was changed from 3 to 5 in `test_browser_overhaul_steps.py`.

## Deviations from Plan

- **[Rule 4 / owner block overrides]** Complete, Edit, Rename buttons replaced by the mockup's Name it / Rename dialogs; the plan's `test_browser_resolve_buttons.py`, `test_health_resolve_dialog.py` and `test_browser_airline_helpers.py` needed no change (the resolve route is unchanged).
- **[Rule 1 - Bug]** My first pass dropped the `.airlines-art__upload` rule (no-script Upload button was 30 px); restored, covered by `test_without_scripts_every_artwork_upload_form_has_a_visible_44px_submit_button`.
- **[Rule 3]** Other test files that selected the old inline name input or `Same as the airline` were updated to the new markup: `test_airline_sheet.py`, `test_status_pages_05b/06/07.py`, `test_view_pages_02.py`, `test_browser_audit4_fixes.py`, `test_browser_ux_04.py`, `test_browser_flights_cards.py`, `test_browser_overhaul_steps.py`.
- Tasks 1 and 2 share most files, so they were committed together (`75226a87`); the TDD red commit was not made separately (tests were written with the code).
- Expansion speed: the type rows are already fetched lazily through `airline-types.js`, so no new mechanism was added; `test_opening_an_airline_among_the_full_list_is_quick` bounds the expansion at 1.5 s.

## Baselines touched

None written. `companion/testdata/render_baseline.json` was not regenerated, so `companion/test_render_baseline.py::test_rendered_pages_match_the_baseline` is red until plan 22 regenerates it. Measured: 16 of 76 page captures differ, on 4 pages: `/airlines` (new `style-airlines.css` hash and new `list-filter.js` hash) and `/fleet?view=system`, `/flights`, `/settings/calendar/disconnect` (only the new `list-filter.js` hash in their `<script>` tag). With the `?v=` hashes masked no capture differs in content. The Editor (`/airlines/manage`) is not in the baseline. The unauthenticated-routes baseline is unchanged. Golden hashes and `stub-server/test_phase47_freeze.py` are untouched and green.

## Gates

- `companion/pages/airlines_page.py`: 1286 lines (was 1287); `companion/static/list-filter.js`: 979 lines; `companion/app.py` untouched.
- `scripts/check_function_size.py check --max 80 server stub-server`: none over 80. `scripts/check_comment_history.py check`: clean. `ruff check .`: clean. `mypy`: only the 13 pre-existing PIL import errors of this environment.

## Test run

- Full `SKYPANE_REQUIRE_BROWSER=1 pytest companion stub-server/test_phase47_freeze.py -n 8` (27 min): 10808 passed, 3 skipped, 7 failed. Of the 7: `test_render_baseline` (expected, above), `test_browser_page_opening` x2, `test_browser_round11_fixes` x2, `test_view_pages_01` and `test_view_pages_03` were real consequences of this plan and are fixed (page-scoped filter-bar rule, stagger from a wrapper div, column widths, filter-bar markup assertion).
- An earlier interrupted full run also showed `test_browser_home_signature` (ring flourish) failing under load; it passes alone and is unrelated.
- Gate run after the fixes (i18n, structure_guards, suite_guards, csrf, post_origin, access_matrix, overhaul_sweep incl. `/airlines/manage` at 360 and 1280 px in EN and FR, airline table and editor browser tests, page_opening, view_pages_01/02/03, status_pages_05b/06, page_styles, stylesheet_structure, console_groups): 3727 passed; the one failure (`test_stylesheet_structure`, a selector declared twice in one media context) was fixed and re-run green.
- New or rewritten browser tests in `test_browser_airline_table.py`: dialog placement (sheet on phone, centred card on desktop), compact unidentified row at 360 px, no Ignore, chips with counts and kinds, menu padding and 44 px items, no overlap on expansion, expansion within 1.5 s with the full list, type menu per state, upload and delete of a type picture, default-type column, rename and refused-name dialog, no-script rename.
