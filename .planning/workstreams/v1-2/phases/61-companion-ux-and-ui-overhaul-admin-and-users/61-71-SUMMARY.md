# Phase 61 Plan 71: Fleet sub-tabs on a phone, Other frames padding, empty frame picture Summary

On a phone the Fleet page is three server-rendered sub-tabs (State, Settings, Access) in the existing segmented control; desktop keeps the full single page; the Other frames card is evenly padded, a pending frame offers pairing, and a frame with no picture shows a designed empty state while an overdue Home says it once.

**Requirements:** owner decision D42 (P10), audit findings F27, F14, F28.

## What changed

- **F27 (`console_fleet_view.py`, `style.css`, `i18n_fr/admin_fleet.py`):** `/fleet?frame=<id>&tab=state|settings|access` (default and any unknown value: State; an old `access=` link: Access). The control reuses the `personalisation-nav` track (plain links, `aria-current`, 44px, no sideways scroll, no script). State holds State plus Device and version (model, firmware), Settings the settings form, Access co-managers plus the Other frames card. All blocks are rendered; below 960px the stylesheet shows only the current tab's blocks (`data-fleet-tab` on the container, per-block classes), from 960px the control is hidden and every block shows as before. The System view is unchanged. The unsaved-changes dock lives after the blocks and works on Settings.
- **Redirects (`fleet_moves.py`):** `/health` stays on the default State tab, `/device` (and `/devices/<id>/device`) lands on `tab=settings`, `/update` and the update-install result stay on State (the firmware group). A device-settings save now returns to `tab=settings`. Access rules and the 404/redirect matrix are untouched.
- **F14 (`fleet_page.py`, `style.css`):** the Other frames summary no longer carries an extra top margin when alone in its card (17px above and below at 390). A pending frame row now has an actions menu with "Pair frame", which opens the existing pairing dialog.
- **F28 (`home_page.py`, `style.css`):** a frame with no picture shows in the hero a token-coloured dashed box with the frame glyph and "No picture yet" (explanation as a visually hidden caption) instead of the white image backdrop or a separate empty group; one wording for the live frame and the others (`home.nothing_rendered_yet` and `home.current_frame` removed). When the notification already says the frame is overdue, the hero keeps the amber "Overdue" word and drops the "Update overdue · expected at" line.

## Tests

New `companion/test_browser_fleet_tabs.py` (10 tests: three tabs at 360/390 in EN and FR fit and show only their groups, no-JS link navigation, desktop shows all groups and no tabs, dock on Settings, empty picture in light and dark, Other frames padding and the pending action), plus a served-HTML test of the tab query in `test_console_fleet_view.py`. Updated in place (subject changed): `test_home_state_card.py`, `test_browser_home_state_card.py` (overdue said once; the helper-level checks of the expected-at line and date now call the next-update row directly), `test_console_fleet_page.py`, `test_console_fleet_view.py`, `test_device_settings.py`, `test_companion_app_04.py`, `test_legacy_admin_page_redirects.py`, `test_view_pages_04.py`, and the phone browser tests that read settings or the other frames now open `?tab=settings` / `?tab=access` (`test_browser_device_led_switch.py`, `test_browser_ux_quiet_wake.py`, `test_browser_fleet_dirty_bar.py`, `test_browser_fleet_page.py`, `test_browser_console.py`, `test_browser_overhaul_steps.py`). U4c stays 3 steps (the tab tap replaces the scroll). Render baseline regenerated.

## Deviations from Plan

- The Home "blank white panel" came from a fixture picture that is genuinely white, so it cannot be told from a real white render; the designed empty state covers the no-picture case (which previously showed a separate group), and the white image backdrop is unchanged.
- Device and version sits on the State tab (as in the mockup), so `/update` lands on State.

- CI fix carried in this commit: the two top-level `.place-sheet .runway-card` rules in `style.css` (runway badge, from 61-69/61-70) are merged into one with the same cascade result (`test_stylesheet_structure.py`, `test_place_page.py`, `test_browser_place_clusters.py` green).

## Screenshots

`scratchpad/shots71/` (fleet_state/settings/access in light and dark at 390, fleet_other_frames, home_light/dark).

## Self-Check: PASSED
