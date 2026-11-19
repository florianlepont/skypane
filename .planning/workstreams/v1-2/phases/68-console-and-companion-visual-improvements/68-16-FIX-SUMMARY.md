# Phase 68 Plan 16 Fix Summary

Versions list (Fleet "Device and version" block and /update): the status chip now sits on the
version's own line, 8 px to its right, on every row and for every chip.

## Cause

Each row put its notes label ("Notes (2)" and a chevron) on the right of the row for rows without a
Roll back action. That column took about 90 px, so at 360 px (and at 390 px in French) the version and
a wide chip ("Plus recente") no longer fitted and the chip wrapped under the version while a narrower
chip ("En cours") stayed beside it.

## Changes

- Every row counts its notes, with the disclosure chevron, on its own line under the date (rows with a
  Roll back action already did). The version line has the full row width on every row.
- Roll back stays at the right edge of its row; the notes count starts at the same x on every row.
- Removed the "For <hardware>" line under "Device and version" (Fleet and /update, EN and FR) and its
  `.update-for` rule. The confirmation page keeps its own note, so the i18n id stays in use.
- Measured at 360, 390 and 1280 px, EN and FR: chip gap 8 px and vertical offset about 0 on all rows.
  It fits on one line at 360 px in both languages, so no fallback rule was needed.
- New `companion/test_browser_version_rows.py` (6 cases) measures chip x/y against the version text
  on Newest and Running rows, the Roll back right edge and the notes position.
- `update_page_one_type_golden.json` regenerated (row markup changed). `render_baseline.json` untouched.

## Deviations from the plan

- The notes label moved from the right of the row to under the date (visible change on rows without an
  action); the plan had it on the right.

## Design-system divergences

- Notes disclosure: the chevron is now beside the "Notes (n)" text on the third line rather than at the
  row's right edge, which the approved mockup shows. Needed so the chevron and the chip line do not
  depend on whether the row has a Roll back action.

## Pre-existing failures (not touched)

- `test_render_baseline.py::test_rendered_pages_match_the_baseline` differs on `/airlines|en|dark`
  (stylesheet version hash), and `test_browser_console_groups.py` airlines-table header font size
  (13px vs 12px). Neither involves the update page.
- `mypy` reports missing PIL stubs in this environment.
