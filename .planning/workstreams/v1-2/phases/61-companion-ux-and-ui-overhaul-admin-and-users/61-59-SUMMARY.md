# Phase 61 Plan 59: Console pages on the grouped-list components Summary

The Console Fleet blocks, the Users table and cards, the Airline editor table, the Audit log list, the error-page onward link and the sheet radius now follow the glass tier and graphite tokens of plans 61-55 to 61-58. Several items of the brief were only partly reached (see "Not done").

## What changed

- **Fleet.** `console_fleet_view._block` renders each of State, Device and version, Settings and Access (and the System view) as a `ui_groups.group`: `h2.section-label` above one glass `ul.group.fleet-group`. Model is a real `ui_groups.row`; the health rows (native `<details>`), version cards, settings form (wake interval, LED switch, dirty bar) and the access list/add form are `li.fleet-group__item` content. Inside a fleet group the embedded cards (`page-section`, `update-cta`, `theme-status`, `data-card`, `health-rows`, docked toast) lose surface, border and shadow and are separated by `--glass-hairline`, so nothing nests. Two columns from 1000px, stacked on a phone, no horizontal overflow at 360px in French. No app.py change (1473 lines).
- **Users.** The wrapper section has no surface; the table (from 70rem) is the one glass table (12px / 600 / no-uppercase header, rows at least 56px, glass hairlines); phone cards are the glass tier (solid base outside `@supports`); the role select no longer clips "Administrateur" at 390px.
- **Airline editor.** Glass hairlines, 12px header, 56px rows, sub-rows on a 5% ink tint, neutral artwork plates, amber tint plus an amber "Unidentified" chip (`.airlines-gap-chip`, replaces the `<em>`), and the "Name it" link no longer wraps or clips at the right edge.
- **Audit log.** The phone list is one glass group (`ul.audit-cards`); the global `.data-table th` is 12px/600 with glass hairlines and the Flights/Audit table cells are at least 56px.
- **Sheets.** New `--radius-sheet` (28px) for the top corners of the phone bottom sheets and dialogs (three previous uses of `--radius-pill`).
- **Error pages.** `login_page._back_link_html` renders one onward row in a glass group (`.error-actions`) instead of a text link. The login card already used the shared tokens, is script-free and its CSP is untouched.
- **Special looks.** Hairlines and the kind tag retoned (no chevron: a rule row opens nothing, it keeps its Remove button).
- `data-card__label` is 12px to match the table header (existing test pins them equal).

## Tests

New `companion/test_browser_console_groups.py` (34 cases): Fleet blocks are one labelled glass group each with no nested group or card surface and a Model row of at least 54px (360/1280 x EN/FR x both themes, no overflow); Users and Airline editor header 12px/600/no-uppercase and rows at least 56px; the amber chip; Users, Airline editor and Audit fit 360px in EN/FR and both themes; the Audit phone list is one glass group. Run 3 times in a row with zero failures.

Updated in place (none weakened): `test_browser_console_fleet_view` and `test_console_fleet_view` (block headings are now `h2.section-label`), `test_browser_overhaul_steps` (A7 locator), `test_browser_overhaul_sweep` (the radius-scale surface audit skips surfaces inside a `.group`, which are flattened on purpose), `test_landing` (404 back link is a row), `test_sign_in_surfaces` (404/403 digests regenerated deliberately), `test_ui_modal` and `test_browser_foundations` (28px sheet radius and the new token), `testdata/render_baseline.json` regenerated. No test removed.

## Deviations / Not done

- **Fleet Access** keeps the existing co-manager list markup (flattened to rows by CSS) rather than `ui_groups.row` rows with the manage actions as trailing controls; the owner/co-manager Remove forms and Add form are unchanged. Model is the only true row; State rows are the existing health rows. The System view is a single group, not one group per topic (ADS-B sources, backups, anomalies, pipeline stay as the health rows and sections they were).
- Special looks rows were not rebuilt as group rows with a chevron; the Releases/Update view, the quiet-hours dialog and other dialogs only inherit the glass tier and the 28px radius; Airline collection detail sheet facts were not converted (61-58 already aligned them); Flights desktop table got only the new header style and row height; the Users "..." menu is unchanged.
- Dialogs on desktop (centred) keep the card radius; 28px applies to the phone bottom sheets.
- Login and the 404/403/503 pages: only the 404/403 onward row changed; the 503 and the interstitial are untouched.
- "Other frames" panel at the bottom of Fleet still has generous top padding.
- Before screenshots of Fleet were produced from a detached worktree of HEAD (removed afterwards).

## Screenshots

`/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots59/` (`<page>-{phone,desk}-{light,dark}-{en,fr}-{before,after}.png`; French only in Light; `login`, `credits` and `notfound` have `a1`/`after` only).

## Verification

ruff, mypy, comment-history, function-size (931 functions, none over 80) and `test_phase47_freeze` green. Full suite result: see the report.
