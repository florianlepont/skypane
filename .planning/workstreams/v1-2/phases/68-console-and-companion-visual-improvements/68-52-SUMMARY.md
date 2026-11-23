# Phase 68 Plan 52: Owner feedback of 2026-11-23 Summary

Three owner items: Home flight card on desktop, foreign-frame banner and space switch in consultation mode, default type only for a type with a livery.

Captures (separate images): `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p52/{before,after}/`
(`home-{1280,1440,1920}-{en,fr}-{light,dark}.png`, `notice-{phone,desktop}-{en,fr}-{home,flights}.png`, `notice-scrolled-*`, after only: `notice-*-place.png`).

## Commits

| Item | Commit |
| ---- | ------ |
| 2. Banner at the very top, no space switch while consulting | 30d90b21 |
| 3. Default type only with a livery | 10ea0b36 |
| 1. Home flight card on desktop | 54023e5e |
| Render baseline regenerated once | final docs commit |

## 1. Home flight card, desktop

Before: at 1280/1440/1920 px the card spanned the whole column with a 168 px portrait at the left and an empty white area. After (>= 960 px): the card is `align-self: flex-start`, `width: min(100%, 36rem)`, 24 px padding and gap, a 208 px portrait (280 px landscape) and a 28 px callsign; the pills, statistics and strip keep the column width. Below 960 px nothing changed (phone and the 700 to 959 px layout are as before). Test: `test_the_flight_card_hugs_its_content_on_a_wide_screen` (1280/1440/1920, EN/FR) fails before, plus `test_the_flight_card_still_spans_the_column_on_a_phone` (360, 390).

## 2. Consultation mode (administrator on another person's frame)

Reproduced: on desktop the banner sat inside the main column, 48 px under the top and beside the sidebar; on phone it sat under the app bar (logo and frame chip); the "My frames | Console" pill stayed in the sidebar and the More panel kept its space row.

- The notice now renders as the first block of the body, before the shell, `position: sticky; top: 0`, full width, padded for the status bar / notch (`--safe-top`, `--app-bar-drop`), z-index above the sidebar and app bar. `--notice-h` (one line) keeps the desktop sticky sidebar clear below it. Location (map) page: the app bar laid over the map starts under the banner because the shell is its positioning context; the old per-page notice overrides in `style-place.css` are removed.
- `page_shell` computes the notice once; when present the sidebar space switch is not rendered and `_tab_bar_html(consulting=True)` drops the More panel's space row. Console pages and the administrator's own / co-managed frames are unchanged (switch present, no banner).
- Kept: Back to Fleet (`/fleet?frame=<id>`), eye icon, accent slab, texts (OWNER-APPROVED block unchanged). The frame-switch chip is kept (the mockup does not show it either way and existing tests rely on it); flag below.

Tests: HTTP (`test_admin_personal_scope.py`: notice is a direct child of body before the shell, no switch / space row while consulting, switch still present on own frame and Console), browser (`test_browser_admin_personal_scope.py::test_the_notice_is_flush_to_the_top_and_no_space_switch_is_offered`, 360/1280, EN/FR: top 0, full width, first block, over the sidebar, no visible switch, stays at 0 after scrolling). All fail before the change.

### Existing tests adapted to the new behaviour

- `test_console_shell.py` (two tests): the administrator on the owner's frame has no space row in More.
- `test_nav_personal_console.py`: admin More sheet on a foreign frame is Account alone; unused constant removed.
- `test_space_switch.py`: the two "My frames current" cases on the owner's frame removed (that state is covered by `test_nav_spaces.py` on `space_switch_html` and by the browser files below).
- `test_browser_overhaul_sweep.py::test_an_administrators_personal_page_equals_a_users`: admin has the notice and no switch.
- `test-support/nav_spaces_support.py::own_frame_home` now opens the administrator's own frame (`live_id`, it previously opened the owner's frame, despite its name); this keeps `test_browser_nav_spaces`, `test_browser_space_switch`, `test_browser_tab_bar_roles`, `test_browser_nav_alignment` testing the switch on a page that has one.

## 3. Default type needs a livery

A type has a livery when its artwork (built in or fleet-wide upload) exists for that airline: new `illustrations.type_artwork_keys` / `has_type_livery` (variant or shape slot, plus the lower-cased designator slot of curated pictures such as ATR72 / A330).

- Menu: "Set as default type" is offered only when the type has a livery; otherwise the type has no menu at all (the Editor's menus never show disabled items, so no new string and no orphan). "Remove as the default type" stays on the current default even without a livery.
- Server: `airline.default_type` with a type lacking a livery returns `FLASH_KEY_DEFAULT_TYPE_FAILED`, writes nothing, no audit row. Clearing (empty type) is always allowed.
- Deletion: today (before the change) deleting the artwork of the default type left a dangling default (star pill on a row with no picture, the airline row showing the code with the airline picture). Now `handle_artwork_delete` clears the default when no picture (built in or upload) is left for that type; the default is kept while a built-in picture remains.
- Pre-existing defaults without a livery: not changed. They keep their star and can be removed from the menu. Not measured on production data (no access); a one-off scan of `airline_default_types.json` against the illustration directories would list them.
- Not changed: naming an airline through the lookup panel with a `default_type` (`post_actions._record_resolution` and the upload `?default_type=` path) still stores the type directly, so a freshly named airline can get a default before it has a type picture. See owner decisions.

Tests: `test_airline_editor.py` (refused POST writes nothing and is not audited; built-in and uploaded accepted; clearing allowed; deleting the default's artwork clears it; kept while a built-in remains), `test_browser_airline_table.py::test_only_a_type_with_a_picture_offers_to_be_the_default` (360/1280, EN/FR) and two existing browser tests updated (a type with no picture has no menu; deleting the default's artwork leaves no default). Seeded default in the existing editor test now has the artwork it needs.

## Follow-up decisions (owner, same day)

**Frame-switch chip removed while consulting.** `page_shell` renders no frame menu when the notice is shown; the banner's Back to Fleet is the only way out. Tests adapted: `test_device_selector.py::test_single_device_consulted_by_an_administrator_has_no_frame_selector` (was "lists one frame and the add row" on a foreign frame), `test_browser_admin_personal_scope.py` (frame name no longer read from the chip; new assertion that no `.frame-menu` exists). Captures: `scratchpad/p52/after2/`.

**Livery rule is central.** `airline_default_types.set_default_type` refuses (`SET_REJECTED`, nothing written) a type with no picture; clearing is always allowed. Every path obeys it: the row menu action, the naming/resolve flow (refused default gives the existing failure flash, the name is still saved) and the upload flow. Order of operations: the upload stores the file first and passes it as `livery_key`, so a first upload of a type set as default in the same request is accepted (`test_a_valid_aircraft_type_becomes_the_default_type_of_the_airline`, `test_a_picture_stored_in_the_same_request_counts_through_livery_key`). Existing tests that stored a default without a picture now create the picture first (`test_airline_default_types.py`, `test_fleet_airline_names.py`, the inline naming test split in two).

**Default type is now a function: tier 2b.** `select_illustration`: exact airline+type, airline picture, **default type's picture (`{airline}-{slug}`, built in or fleet override)**, generic by shape, universal. The default file is read once per change (cached by mtime and size, never raises, unreadable or invalid = no default). Example: Acme Air has A320 and B737 pictures, no airline picture, default A320: a flight on an E190 showed the generic Embraer before, now `acme-air-a320.png`. Note: the frame image can change for airlines that already have a default type with a picture and no airline-level picture. Tests: tier order, removed picture falls through, invalid file changes nothing, mtime re-read (`test_illustrations.py`); the golden renders and `test_giant_compose` / `test_orly_replay` are unchanged and green.

**Menu wording.** "Set as default type" / "Remove as the default type" became "Use as the airline's default picture" / "Stop using as the airline's default picture" (FR "Utiliser comme image par défaut de la compagnie" / "Ne plus utiliser comme image par défaut de la compagnie"); the row pill still reads "Default type".

**Migration of existing defaults without a livery** (`server/plane/fleet_default_types.py`, called by `fleet_migrate.migrate` after the names and artwork merges; deploy/activate.sh unchanged). Defaults are fleet-wide (`airline_default_types.json` at the fleet root; per-frame files are frozen copies and untouched), so there are no per-frame conflicts. Each cleared entry is first appended to `airline_default_types_cleared.json` (airline key, type, source, time), then cleared, then `airline_default_types_migration.json` is written; both files are in the backup include list. Only a run that clears something writes anything; once the marker exists later runs do nothing. Log lines:

- dry run: `airline default types: would clear N` then one `airline default types: would clear <key>: <type>` per entry
- real run: `airline default types: cleared N` and the same per-entry lines
- otherwise: `airline default types: nothing to do`

The dry run judges the fleet root before the same run's merges (a picture or default still pending in the per-frame merge is not counted). After deploy: check the log lines, open the Editor to see the cleared airlines without a default, and read the archive file to restore an entry on purpose (upload the type's picture first). Tests: `server/test_fleet_default_types.py`, `server/test_fleet_migrate.py::test_default_types_without_a_picture_are_cleared_once`, `deploy/tests/test_default_types_migration_log.py`, `deploy/tests/test_backup.py`.

## Verification

Server + companion + deploy non-browser: 11473 passed, 7 skipped (one timing test, `test_status_pages_01::test_battery_trend_timestamps_show_concise_format`, failed once under load and passes alone). Targeted browser files (admin scope, airline table, Home, nav, switch, frame menu, page opening, overhaul sweep, device selector, Home cards): 1235 passed. ruff, mypy, function-size, comment-history clean. `render_baseline.json` regenerated, no change.

## Owner decisions needed

None open. Sidebar clearance under the banner assumes a one-line banner; a banner wrapped on two lines on desktop (very long address) overlaps the top of the sticky sidebar only while scrolling.
