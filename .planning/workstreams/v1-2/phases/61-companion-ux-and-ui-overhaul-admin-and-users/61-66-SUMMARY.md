# Phase 61 Plan 66: Fleet save bar, old bookmarks, 404 page, wording sweep, airline table Summary

The Fleet settings save bar is docked at the bottom of the viewport (sticky inside the content column, above the tab bar on a phone) and says "Unsaved changes" with Cancel and Save; old personal-page bookmarks reach their new page for every signed-in role; the 404 page has a real primary button and names the administrator-only case; plural, frame-name, validation-message and title inconsistencies are fixed; the airline editor no longer clips names.

**Requirements:** D42 (P01, P02 in part, P11, P12), audit findings F01, F02 (part), F13, F15, F16, F17, F18, F21, F25.

## What changed

- **P01 / F01**: the bar was rendered inside the Fleet glass group, whose `backdrop-filter` makes it the containing block of a `position: fixed` bar (it was squeezed and offscreen). `config_page` now renders the embedded settings without the bar and `console_fleet_view.frame_html` appends `config_page.docked_dirty_bar_html()` after the blocks. `.dirty-bar--docked` is `position: sticky`, as wide as the column, grid layout (text, Cancel, Save; 44 px buttons), bottom offset above the tab bar on a phone. `dirty-state.js` writes the fixed "Unsaved changes" text for a bar carrying `data-dirty-generic`; the save label is the short "Save"/"Enregistrer".
- **F16**: the wake interval card has one visible label (the heading); the number label is read aloud only; the unit reads "seconds"/"secondes" followed by a live "· 10 min" ("· 10 mn" in French) through the existing value-controls readout; the number spinner is hidden.
- **P02 (part)**: `/settings`, `/history`, `/preview`, `/display/screen` now move a signed-in non-administrator to the page that replaced them under their default frame (account page when they have none). New `companion/legacy_pages.py`; the administrator keeps the route's own redirect. System view: the duplicated topic caption is visually hidden (still names the group).
- **P12 / F13**: the error pages' onward link is a primary button (`error-home-button`). For a signed-in non-admin the 404 page says "This page doesn't exist, or it is reserved for administrators." (EN/FR).
- **P11 / F17 F21 F25**: plural-aware "1 airline spotted" / "1 compagnie repérée" (zero is singular in French); the live frame's default name is translated in the Fleet heading like the frame button; translated validation messages (`ui_base.validation_attrs`, handled in `submit-guard.js`) on the invite email, co-manager email/person, reassign owner, pairing code and airline name fields; the document title carries the frame's name on every device page for every role ("Home - Orly frame - SkyPane").
- **F18**: airline table at 70rem+: wider name column, ellipsis on the name input, `nowrap` on Views / Last seen / menu cells.

## Deviations from Plan

**1. [Rule 4 - scope, needs your decision] /health, /device, /update are NOT redirected to /fleet.** Implemented and measured: redirecting them breaks about 230 existing tests in 50 files that pin those pages as served (freshness ETag and refresh token on /health, the resolve dialog "on Health", health empty states and drawings, update browser flows, device-link and nav crawls, i18n sweeps). Several pin features that do not exist on the Fleet page (live refresh token for the Health page), so they cannot be re-pointed without building them or deleting the tests. The patch is saved at `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/p02_fleet_redirect_for_health_device_update.patch` (routes.py and fleet_moves.py; keeps `?frame=` and `flash`, falls back to the Update page when a firmware type has no frame). It needs its own plan (retire the pages and re-home or drop their tests).

**2. [Rule 4 - security invariant kept] The 404 page for a non-admin is one uniform sentence**, not an "administrators only" message shown only for admin routes. The access matrix pins that a denied route is byte-identical to an unknown path, and over 200 matrix cells rely on it. A route-specific message would reveal which paths exist. Every refusal a signed-in non-admin gets (unknown path, another person's frame, administrator page) now carries the same sentence naming both cases.

**3. [Rule 1] Admin legacy bookmarks unchanged**: an administrator reaching `/settings` etc. is still redirected by the route to the served frame's page (not moved to Account), to avoid changing admin behaviour.

**4. Titles**: only device-scoped pages carry the frame name; the Fleet console page title ("Fleet") was left as is.

Existing tests updated in place (not weakened): access matrix legacy rows and landing/user-view/account/device-selector/device-dispatch expectations for the redirects and titles; sign-in surface error-page digests; wake interval markup pins (hidden label, translated unit, one readout); test_personal_space_parity ("1 compagnie sur"); render baseline regenerated.

## Tests added

`test_browser_fleet_dirty_bar.py` (390x844 and 1280x900, EN/FR: bar inside the viewport, above the tab bar, column width, text, 44 px buttons, no card covered at page end, Cancel; wake card label/unit/minutes), `test_legacy_redirects.py`, `test_console_wording_sweep.py` (titles, FR frame name), `test_browser_form_validation_messages.py`, plural tests in `test_airline_collection_page.py`, `test_browser_airline_table.py` (1280x900 no clipped name, counts on one line). New browser tests were run 4 times in parallel: no failures.

## Verification

Full companion + test-support + stub-server suite with `-n auto`: 8485 passed, 4 skipped (root permission skips), 0 failed. ruff, mypy, comment-history, function-size (931 functions, none over 80) and `stub-server/test_phase47_freeze.py` green. `companion/app.py` is 1470 lines.

Screenshots: `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots66/` (before-* and final-*, phone 390 and desktop 1280, EN and FR).

## Known Stubs

None.

## Self-Check: PASSED
