# Phase 68 Plan 22 CI fix: failures of PR 483

Failures read from run 44510685947 (head 2519bef2) and run 44514806925 (head fe071191, whose
non-browser shard 1 failed with the same set and the other shards were cancelled).
Every one was introduced by phase 68 work. Nothing was skipped, disabled or loosened.

| # | Failure | Cause | Resolution | Test or code |
|---|---------|-------|------------|--------------|
| 1 | `test_icon_sprite_integrity`, `test_page_shell_emits_sprite_once_no_inline_styles` (55 expected) | Phase 68 added icon-fit (15), icon-departure and icon-arrival (20), icon-eye and icon-chevron-left (25). Before the phase the sprite had 54 symbols, now 59. All five are used (map button, history direction glyphs, foreign-frame marker). | Count and docstrings set to 59. | test updated to approved behaviour |
| 2 | `test_tab_bar_is_six_cells_...` | The sidebar assertion still pinned the old order. 68-24 made one order for bar and sidebar: Home, Flights, Airlines, Style, Location, Account. | Assertion now pins that order. | test (stale) |
| 3 | `test_theme_chip_preview_src_...`, `test_aspect_display_render_has_exactly_one_live_preview_figure_...` | `frame_preview_src` appends `&v=<signature>` (12 hex, content address). | Tests assert route prefix, state and size, then `&amp;v=[0-9a-f]{12}`. | test updated to approved behaviour |
| 4 | `test_panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard` (4 vs 3) | The artwork dialog type field (68-23) writes the upload form action on submit (`default_type=`). The write is legitimate: it is guarded by its own checks and sits outside the mandatory image/caption guard. | Expected count 4, reason in the docstring. | test updated |
| 5 | `test_error_pages_render_byte_identical_output`, `test_shell_without_a_principal_is_byte_identical_to_before` | Rendered both against a checkout of fb44d731 (pre-phase) and HEAD. Only byte changes: five new sprite symbols (icon-fit, eye, chevron-left, departure, arrival) and the nav entries (names Flights / Location, French Vols / Lieu / Compagnies, order Home, Flights, Airlines, Style, Location). No stylesheet hash is in these pages. All intended (68-15, 20, 24, 25). | Digests re-pinned (error pages `b6656326...`, `ac237b61...`, shell `c2957d35...`). | test updated |
| 6 | `test_glass_applies_only_inside_supports_and_keeps_a_solid_base` | `.airlines-table .airline-group` reset `backdrop-filter` outside `@supports`. No rule gives `.airline-group` a backdrop-filter (the glass block blurs only the sidebar, popover and the bounded surfaces), so the two declarations were no-ops. | Removed them; computed style is unchanged by construction (no other rule can set the property on that element), so no screenshot difference is possible. Not compared with screenshots. | code fix |
| 7 | `test_opened_event_is_a_tinted_label_and_value_panel[chromium-light]` (3.87) | `.audit-event__item dt` used 80% text mix on the tinted panel; thin 13 px strokes rendered at 3.87:1 on the CI runner. Locally the same test reads 5.8 (80%), 7.0 (90%), 7.6 (100%) at the weakest, so only 100% leaves margin for CI's lighter rendering. | Label colour is `var(--color-text)` in `style-admin.css`; light and dark pass. Hierarchy stays through the label size. | code fix (accessibility) |
| 8 | `test_console_renders_in_french[chromium]` ("Mon cadre" vs "Mes cadres") | Already corrected by 9f75c40f (68-25) after run 2519bef2. Passes on HEAD; no other stale assertion found (remaining hits are docstrings). | none needed | already fixed |
| 9 | Found locally under load: `test_the_live_preview_crossfade_settles_correct_through_its_own_listener` (opacity 0.50) | Test race: the reveal marker is absent both before the frame that adds it and after the animation, so a loaded runner read the opacity mid-fade. | Test waits two frames, then polls marker absent and opacity 1 (still asserts the settled state). | test race fixed |

Render baseline regenerated once at the end (20 entries, stylesheet `?v=` of the admin and Airlines style sheets).

## Final results (one run, `-n auto`, SKYPANE_REQUIRE_BROWSER=1, no coverage gate)

- companion non-browser: 7048 passed, 3 skipped, 1 failed (the render baseline, regenerated afterwards; now 2 passed).
- companion browser group 1: 913 passed. Group 2: 1994 passed. Group 3: 936 passed, 2 failed (below).
- server, stub-server, deploy, hardware, test-support, scripts, adsb-test, firmware: 5060 passed, 5 skipped.
- The two group 3 failures passed alone and twice again in a 4-worker run of their files: the crossfade race (fixed, item 9) and `test_browser_ux_quiet_wake.py::test_a_preset_reaches_disk_through_the_dialog` (10 s wait for the preset to fill the fields timed out under 4-worker load; not reproducible, cause not isolated, left as is).
- Gates: ruff, mypy, function size (1140 functions, none over 80), comment history, `app.py` 1490 lines, largest JS 1227 lines.

## Design-system divergences

None. The audit label now uses the existing text token at full strength (no new token). The sprite additions and the nav order follow plans 15, 20, 24 and 25.
