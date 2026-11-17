# Phase 61 Plan 126: Redesign of the "Device and version" panel Summary

**The Fleet device panel now opens with what the frame runs and one state chip, shows a single update card with one Install button, and lists versions as a flat list whose rows open their release notes.**

## What changed

Display only: the install and revert POST forms, confirmations, anti-forgery fields, no-script behaviour, admin-only access, the frame protocol and the firmware offer data are untouched. The standalone `/update` page keeps its own markup.

1. **Summary and state chip** (`bfae2e04`): label "On the frame" / "Sur le cadre", installed version large in monospace, "Installed ... ago" and the model on the next line, a chip on the right (Update available, Up to date, or the scheduled / installing / failed state). The separate Model row is gone. `ui_components.pill_html` gained status tones (`ok`, `info`, `warn`), catalogued on the Components page (`components_page.py`, `test_components_page.py`, FR strings).
2. **Single update card** (`2158acc6`): version and release age, the release title without a trailing "(DRAFT ...)" tag (the full text stays in the notes), one primary "Install fw-vX" button, full width at 360 px. The offered release's history row no longer repeats a button; the card exists only while an update is offered.
3. **Flat history** (`e315ccf9`): no table and no card inside the card; per row a status dot, version in monospace, date, age and notes count, an Installed or Newest chip, and a text-style (ghost) "Revenir" button that keeps its 44 px target. In-flight states (scheduled, installing, failed) keep their existing card.
4. **Notes disclosure** (`83da6125`): the row itself is a native `<details>` (dot, version, date line, chip, chevron); Enter and Space work, it works with scripts blocked, and the action stays outside the summary. Rows without notes keep the chevron's room so chips share one edge.
5. **Pinned tests updated** (`7dc2cd13`): `test_update_page.py`, `test_browser_update.py`, `test_browser_fleet_sections.py`, `test_browser_round11_fixes.py`, `test_browser_console_groups.py`, render baseline.

New browser tests: `companion/test_browser_firmware_panel.py` (360/1280, EN/FR, light/dark; 5 versions with one installed and one offered, plus a no-update case and a single-version case), written red first at each step.

## Deviations

- A newer-but-not-offered release (intermediate version) keeps a quiet text-style "Install" in its row; only the offered release loses the duplicate.
- Commits 2-4 leave the old table-pinning tests red until commit 5, as the plan orders (tests updated in step 5).
- Removed the now-unused table message ids (`update.col_*`, `state_older`, `col_action`) and the table CSS; renamed `update.state_newer` to `update.state_newest` ("Newest" / "Plus récente").
- Notes count on the row's second line reuses the existing "Notes (n)" string.

## Known unrelated failure

`companion/test_device_routes.py::TestPrefixCrawl::test_global_targets_are_never_prefixed` (3 `/display` variants) fails identically on the branch tip before this plan (verified on a clean export of HEAD); not touched.

## Gates run

ruff, mypy, check_comment_history, check_function_size (max 80), `stub-server/test_phase47_freeze.py`, render snapshot regenerated, `companion/app.py` 1493 lines. Tests: test_stylesheet_structure, test_stylesheet_load_order, test_components_page, test_companion_app_02, test_page_structure, test_browser_ux_02, test_i18n, test_sign_in_surfaces, test_suite_guards, test_update_page, test_update_actions, test_console_audit_page, test_access_matrix, test_csrf, test_browser_update, test_browser_fleet_sections, test_browser_round11_fixes, test_browser_console_groups, test_browser_firmware_panel (2907 passed in one run). Modified browser tests were stressed with 4 parallel processes, zero failures. Full suite not run locally (cadence).

## Screenshots

`/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/firmware-panel/shots/`: `panel-360-fr-light.png`, `panel-360-fr-dark.png`, `panel-1280-fr-light.png`, `panel-1280-fr-dark.png`.

## Self-Check: PASSED
