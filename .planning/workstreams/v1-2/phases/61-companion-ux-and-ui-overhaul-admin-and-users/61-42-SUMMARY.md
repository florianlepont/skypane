# Phase 61 Plan 42: Console Fleet merges Fleet, Status, Version and Device Summary

Owner decisions W18 (refined), D31 and D30 (mockup C3): one Console Fleet view with the tile strip of every frame, a four-block detail view per frame and a System view. The Console navigation lost the Status, Version and Device entries.

- **Strip (`companion/console_fleet_view.py`):** every frame (problem-first order) as the D30 tile (picture, name, status dot, last-seen word, owner note, selected one outlined), an "Add a screen" tile (opens the pairing dialog) and a last "System" tile. Tiles are plain links `/fleet?frame=<id>` and `/fleet?view=system`; the selection is matched against the request scope's frame list only (an unknown value falls back to the first frame).
- **Frame detail, four blocks (two columns from 1000px, stacked on a phone):**
  - State: `health_page.frame_state_html` (unreachable notice, connection and battery rows, last detection row from the Health snapshot).
  - Device and version: model row plus the Update page content for the frame's hardware type (`update_page.render(..., embedded=True)`: running version, schedule/cancel forms, version history).
  - Settings: the Device page form (`config_page.render(..., SCOPE_DEVICE, embedded=True)`), same POST route (`/devices/<id>/settings`), validation and administrator-only rules.
  - Access: `co_managers_card.access_section_html` (owner, co-managers, add/remove forms) inline; field ids use an own prefix so the list's dialog does not duplicate them.
- **System view:** `health_page.system_html` (source fault, anomaly banner, flight data, ADS-B sources agreement, identification, backups, unresolved registry); its scripts load only on this view.
- **Health page refactor:** `_page_parts` shared by `render` (output unchanged), `frame_state_html` and `system_html`.
- **Navigation:** sidebar Fleet, Users, Airline editor, Audit log, Account; phone bar cells Fleet (carries the severity dot), Users, Airlines, Audit; More holds the space switch and Account. `/health`, `/device`, `/update` keep answering (forms still redirect there) and mark Fleet current. New short bar label `nav.airlines_short`.
- **Strings:** `admin_fleet.system_*`, `admin_fleet.block_*`, `admin_fleet.add_screen_first`, `nav.airlines_short` in `companion/i18n_fr/`.
- **Tests:** new `test_console_fleet_view.py`, `test_browser_console_fleet_view.py` (360/1280, EN/FR, both themes, 44px, link selection). Adapted in place: `test_device_links.py`, `test_update_page.py`, `test_sign_in_surfaces.py` (shell digest), `test_browser_update.py`, `test_browser_nav_spaces.py`, `test_browser_console_shell.py`, `test_browser_overhaul_steps.py`, `test_browser_overhaul_sweep.py` (list-page table rule now excludes the embedded blocks). `render_baseline.json` regenerated.
- **Docs:** `61-UI-SPEC.md` revision 3 note, `61-STEP-COUNTS.md`.

## Deviations / left for the owner

- Old routes were kept (not 303-redirected): `/health`, `/device`, `/update` and their form redirects (settings save, update install) still land on those pages, which no longer have a nav entry. Redirecting them into `/fleet?frame=<id>` (and returning there after a save) is not done.
- The frame list with row menus (reassign, retire, re-activate, pending and retired rows, Manage access dialog) stays below the blocks; it adds one scroll to A4, A5, A7 on a phone (step targets raised, see 61-STEP-COUNTS.md). Better: move those actions into the detail header or place the list above the blocks.
- "Current flight" is not shown in State (only last detection); the Health snapshot has no current flight.
- After an inline co-manager change the redirect is `/fleet?access=<id>`: it selects the frame and also reopens the list's dialog.
- The Health nav-dot live refresh (freshness.js, `a[href$="/health"]`) no longer finds a link; the dot on Fleet updates on navigation only.

## Self-Check: PASSED (see report for gate results)
