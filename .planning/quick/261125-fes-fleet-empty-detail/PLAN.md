# Quick 261125-fes: Fleet neutral detail pane

Owner decision (2026-11-25, mockup mk63 approved): on /fleet, from 1200px, the pane beside the list
no longer auto-selects the first frame; it shows a neutral "Select a frame" state until a row is chosen.
Phone unchanged (list only).

## Tasks
1. `console_fleet_view.empty_detail_html()` replaces the auto-shown first frame on the landing view;
   the list title is the single `h1` (the narrow/wide heading pair and `first_to_watch` go away).
2. CSS: centred pane in the 1200px+ block, 64px halo with a border (dark legibility).
3. i18n EN/FR (`admin_fleet.select_frame`, `admin_fleet.select_frame_hint`).
4. Tests: served-HTML tests, Playwright desktop (light/dark) and phone; fix the tests that expected frame
   content on bare /fleet.
5. Design-system skill page patterns.
