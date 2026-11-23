# Phase 68 Plan 47: System as a full page, compact tiles Summary

The System view (`/fleet?view=system`) no longer renders the frames list: no left column, no phone chips, no Add a frame button, no back link. It is a full-width page opened by the standard page header (`h1.page-title` "System" plus the purpose line), like Users and Audit. The six System tiles are compact.

## Changes
- `companion/console_fleet_view.py`, `companion/console_pairing.py`: System renders its content directly (no split, no Fleet dialogs/empty state); the console page supplies the System title and purpose. Fleet view of frames unchanged.
- `companion/pages/fleet_tiles.py`: System tiles are `compact`: chevron at the end of the label row (hidden "Details" word kept in the accessible name), one-line muted line with a plain-text `title`.
- `style-admin.css`: compact System tiles, 2 columns on phones, 3 from 960px (3x2 at most), 44px target, state word wraps instead of being cut. `style.css`: removed the `.fleet-split`-scoped System cascade rules (the page-level System rules already there apply; cascade is header, tiles, blocks).

## Tests run
Every companion/test_*.py that is not browser, plus all files from the pinned list (console_fleet_view, fleet_page, fleet_tiles, fleet_frames_list, health_page, system_html, system_cards, view=system, SYSTEM_HREF, fleet-split, fleet-blocks--system; test_companion_app_04, page_opening, console_groups, system_tiles, browser_fleet_*, overhaul_*, nav, render_baseline, stylesheet/suite/structure guards, i18n): 9035 passed, 3 skipped (root permission bits, pre-existing). Earlier pinned run (before final test adaptations) had 17 failures, all listed below and fixed. ruff, mypy, function-size, comment-history clean; companion/app.py 1497 lines. render_baseline.json regenerated once.

## Tests adapted (new intended behaviour)
- `companion/test_console_fleet_view.py::test_the_system_view_shows_the_platform_wide_blocks`: h1 is `page-title`; asserts no list/switch/add button instead of "no current list mark".
- `companion/test_browser_small_fit_fixes.py::test_the_system_cards_fill_the_page_column`: column is `main` (no `.fleet-split__main`).
- `companion/test_system_tiles.py` (`_tiles` regex): meta span may carry a `title` attribute.
- `companion/test_browser_system_tiles.py`: state word looked up in `.fleet-tile__icon` (the chevron also has a hidden word).

## Captures
Scratchpad p47/{before,after}: system-{phone 390,desktop 1440}-{en,fr}-{light,dark}.png (whole page) and tiles-* (tile row only).

## Deviations
None.
