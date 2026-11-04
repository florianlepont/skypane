# Phase 61 Plan 45: Finish the Console Fleet merge Summary

Part A repaired the suite after the Fleet merge (plan 61-42); Part B moved the frame actions into the selected frame's detail header, made results return to the Fleet view and revived the Fleet nav dot refresh. The old GET redirects are the one item left.

## Part A (commit c39ef94, `fix(61-45)`)

The full suite after 61-42 had 23 failures (not 24): the walkthrough route matrix for `/health`, `/device`, `/update` (18, they now mark Fleet current), `test_navigation_omits_redundant_state...` (2, Fleet is the current entry; on a phone it is a bar cell, not in More), `test_invited_admin_lands_on_the_fleet_page...` (the sidebar has no Health/Update/Device links), and the two Airline editor phone flows (Airlines is a bar cell, so one tap, A8 is 4 on a phone). All adapted in place without weakening; the step-count document was corrected for A8.

## Part B

- **Frame actions in the detail header:** `fleet_page.detail_header_html` renders the selected frame's name, owner line and an actions menu (Open personal view, Manage access, Reassign, Retire; no Retire on the served frame). The list of live rows is gone (the strip tiles are the list). Pending and retired frames are in a collapsed "Other frames (n)" block (retired rows keep Re-activate). Dialogs are unchanged; frame dialogs dismiss to `/fleet?frame=<id>`. Phone flows A4, A5, A7 no longer scroll (see 61-STEP-COUNTS.md; the counts include one tile tap because the frame selected on landing is not Kitchen).
- **Results return to the frame:** the Device form save and the update install/cancel (and their failures) redirect 303 to `/fleet?frame=<id>[&flash=<key>]` (`companion/fleet_moves.py`); the Fleet page resolves the `?flash=` toast for the selected frame (`console_fleet_view.query_flash_html`). The frame for an update action is the Referer's frame if it is one of the principal's frames of that hardware type, else the first such frame. An update action on a hardware type with no frame still lands on `/update?type=...` (that page stays served for it).
- **Co-manager change:** an inline change redirects to `/fleet?frame=<id>` (the list dialog is not reopened; `?access=` still opens it, Account is unchanged).
- **freshness.js:** new page key `fleet` (health rows, anomaly and source-fault regions, `a[href$="/fleet"]`), the Health key's nav selector now targets the Fleet link, and the Fleet page loads `freshness.js`. Every tick is a full 200 (no token), so each tick renders the whole Fleet view.
- **Product bug found and fixed:** the strip tile's status dot ignored overdue, screen-off and battery-empty signals (the old list row used them), so a frame could read "Up to date" in the strip and "Overdue" on its Home. `ui_shell._switcher_status_row` now uses `console_pairing.frame_signals`.
- **Current flight in State (item 5):** not added. The Health snapshot carries the last detection only; a current flight needs new backend.
- **Strings:** `admin_fleet.other_frames_n` added; `retired_frames_n`, `menu_health`, `menu_device`, `n_frames`, `one_frame`, `n_need_attention`, `one_needs_attention` removed (count line gone).
- **Tests adapted in place:** `test_console_fleet_page`, `test_co_managers_page`, `test_update_actions`, `test_device_settings`, `test_companion_app_04`, `test_console_audit_page`, `test_console_pairing`, `test_console_lifecycle`, `test_status_pages_04`, `test_device_links`, `test_browser_fleet_page`, `test_browser_fleet_dialogs`, `test_browser_co_managers`, `test_browser_admin_personal_scope`, `test_browser_overhaul_steps`, `test_browser_update`; three tests added to `test_console_fleet_view`. `61-UI-SPEC.md` (revision 3 note, part 2) and `61-STEP-COUNTS.md` updated. No render baselines or digests moved.

## Not done (left for a follow-up)

- **303 redirects of the old `/health`, `/device`, `/update` GET routes.** I implemented them and ran the suite: 325 tests failed (about 60 files that exercise the Health, Device and Update page content through those URLs: health drawings and resolve dialog, charging pill, freshness tokens, update chooser, device-page cards). The content lives under `/fleet?frame=<id>` and `/fleet?view=system`, but re-pointing those tests is a separate job; the redirects were reverted so the suite stays green. `fleet_moves.health_target` and the route lambdas are described here for the follow-up: `/health` -> `/fleet?view=system` (scoped: `/fleet?frame=<id>`), `/device` and `/update` -> `/fleet?frame=<id>`; `/update?type=<type with no frame>` must stay served.
- The Manage access dialog's Done link still returns to `/fleet` (the whitelisted return path), not to the selected frame.

## Self-Check: PASSED

Full suite after the last code change: 7795 passed, 4 skipped, 1 failed (a test pinning the dismiss href, adapted afterwards and re-run green alone); gates ruff, mypy, comment-history, function-size and the freeze test are green.
