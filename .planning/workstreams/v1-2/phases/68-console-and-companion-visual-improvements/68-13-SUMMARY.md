---
phase: 68-console-and-companion-visual-improvements
plan: 13
subsystem: companion-home
tags: [home, layout, pills, statistics, strip, i18n, browser-tests]
requires: ["68-01", "68-08", "68-33"]
provides:
  - "Home assembled from the approved mockup in its online, sleeping and offline states"
  - "companion/pages/home_state.py, home_flight_card.py, home_pills.py"
affects: ["68-22"]
key-files:
  created:
    - companion/pages/home_state.py
    - companion/pages/home_flight_card.py
    - companion/pages/home_pills.py
  modified:
    - companion/pages/home_page.py
    - companion/pages/home_battery_row.py
    - companion/pages/home_notice.py
    - companion/pages/home_recent_strip.py
    - companion/pages/home_stats.py
    - companion/detection_summary.py
    - companion/static/style-home.css
    - companion/static/freshness.js
    - companion/ui_nav.py
    - companion/i18n_fr/home.py
    - companion/i18n_fr/detection.py
requirements: [CON-01]
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 13: Home assembled from the approved mockup Summary

Home is now one column of blocks that look like `68-HOME-MOCKUP.html` on the real app: a title block (name with its rename pencil, the state dot and word, the next update with the "i" at the end of the sentence), the flight card, the pills (Screen switch, 44 px quiet-hours link, place, battery), the statistics card and the recent-flights strip from plan 33. The hero, the ring and glint, the Frame group, the Detection group and the battery dial are gone. CON-01 is not ticked (the phase is not finished).

## What was built

- `home_state.py`: title block as the `home-frame-state` section (h1 + pencil from `home_title`, shared status dot and word, next-update line or "Last contact 3h ago" for a frame that lost contact, ending with the cadence "i" button inside the sentence).
- `home_flight_card.py`: picture (newest archived render, alt text carries the flight line) beside a direction badge, callsign, airline, route and type, and a live "Detected 4m ago" `<time data-relative>`; empty-picture box kept; landscape frames stack the picture over the text on a phone.
- `home_pills.py`: Screen pill (shared native-POST `role="switch"`, whole pill is the target, quick-refresh region), Quiet hours link pill (opens the existing dialog), place pill (`detection_summary.home_place_text`), battery pill (`home_battery_row.pill_html`, with the shared hedged charging pill and a word for a low level).
- `home_page.py` (775 -> 243 lines): one `history_db` scope for rows (folded by `flight_card.fold_repeated_passes`), `home_day_timeline`, `home_week_totals`, `home_airline_highlights` and the latest battery reading; frame zone Europe/Paris, `ctx.now`, `now_hour`, quiet window as `(start, end)` float hours (only while the schedule is on); the old recent-flights group removed (the strip's heading id `home-flights` replaces it).
- `style-home.css`: `.home*`, `.home-state*`, `.home-flight*`, `.home-pill*`, `.home-stats*` (the `:has(#home-stats-week:checked)` panel switch), `.home-strip*` (3:4 frame, `object-fit: contain`, `figcaption span {display:block}`, scroll-snap row, landscape 5:3 modifier). No duration literal, no colour literal, `style.css` untouched.
- Refresh registry (`ui_nav.py` + `freshness.js`, kept in agreement): Home swaps the title block, the flight card, the pills, the strip and the notification container.
- `detection_summary.py`: the legacy runway pill uses `ui_components.pill_html` (D-14); the Detection group builder is replaced by the pill text; the five `detection.card_*` ids are removed.
- French: 6 ids added (`home.pill_quiet_off`, `home.flight_heading`, `home.flight_detected`, `detection.pill_runway`, `detection.pill_position`, `detection.pill_no_place`), 17 orphan `home.*` and 5 `detection.card_*` ids removed; `test_i18n.py` green.

## Plan 33 follow-ups

- Tile ages (divergence 3 of plan 33): the strip section carries `aria-labelledby="home-flights"`, which is a Home swap target, so `freshness.js` repaints it from the server every 45 s and the wording "Arrival · 12 min" stays as in the mockup. The `data-relative` ticker was not used for tiles because it would rewrite the text to "12m ago" / "il y a 12 min" and overflow the 112 px tile in French. The "Detected" age in the flight card is a real `<time data-relative>`. Tested (`test_the_strip_is_a_region_the_background_refresh_swaps`, in both the served-markup and browser suites).
- Landscape frame profiles: handled. The flight card stacks (picture full width) on a phone and the strip tile becomes 168 px at 5:3 (`recent_strip_html(..., landscape=)`); browser-tested in `test_browser_home_header_landscape.py` with a seeded landscape device.
- Class names, `:has()` switch and token names from plan 33 are used as built.

## Design-system divergences

1. **On state of the Screen switch is green** (mockup `.pill.on .mini`), not the system's graphite/ivory accent; the thumb stays the shared white thumb and the shared switch markup is untouched. Done in `style-home.css` only. Owner may prefer the accent.
2. **Quiet-hours pill shows the range behind the moon with no word** ("23:00 – 06:00"), while the mockup reads "Veille 23 h – 6 h". The word does not fit next to the Screen pill at 342 px; the accessible name is "Edit quiet hours (23:00 – 06:00)". While the schedule is off it reads "Quiet hours · Off". The quiet on/off switch is gone from Home (the dialog presets turn it on and off; `/quick/quiet-hours` is kept for other callers).
3. **Place pill text is ink, not the browser-default blue** the mockup's bare `<a>` shows; it is "ORY · runway 4" (airport code plus the legacy runway number), position mode "Maison · 9 km radius", no place "No place set".
4. **State words are the shared frame-status words** ("Online", "Resting", "No contact") not the mockup's "En ligne / En veille / Hors ligne"; the next-update sentence is the shared template ("Next refresh in 6m", "Next wake around 00:35 · quiet hours · in 2 h"), not "Prochaine mise à jour 0:22" / "Reprise dans 2 h 10".
5. **Flight card text is data the history holds**: "ORY → TLS · A320" instead of "vers Toulouse" / "Airbus A320 · 2 400 ft" (no city name or altitude is stored). English wording is mine ("Detected %s", "Latest flight").
6. **Day/Week switch stays the shared radios** (plan 33), restyled pill-shaped in `style-home.css` to match the mockup.
7. **Offline notice keeps the shared docked toast** (restyled: tone border, plain title, small tip, warning triangle) and its "Contact an administrator" action; for "no contact" its "Last contact" line is not repeated (the title block says it). The notice is one title plus a tip, as in the mockup, plus the action.
8. **Dropped, by the mockup**: the ring around the picture and the glint, the sentence under a held state, the battery dial and autonomy estimate ("battery life ~3 weeks"), the Frame and Detection groups. The battery is a static pill ("Battery 75 %", plus "Low" or the charging pill). `relative-time.js`'s ring code and the `.hero*` rules in `style.css` are now dead (not touched: `style.css` is out of this plan).
9. **Title size** 32 px (phone) / 44 px (desktop) per the design system (was 28/48).
10. A greyed picture and strip tiles for a frame with no contact follow the mockup.

## Deviations from Plan

**1. [Rule 3 - Blocking] `ui_nav.py` edited.** The Home swap registry lives in `companion/ui_nav.py` and must agree with `freshness.js` (guarded by `test_status_pages_04/05`); the regions changed, so it changed. Not in the plan's file list.

**2. [Rule 1 - Test follow-ups outside the listed files]** Tests that used Home's old markup were updated: `test_battery_charging`, `test_companion_app_04/04b`, `test_freshness_token`, `test_quiet_hours_modal`, `test_status_pages_05`, `test_ui_groups`, `test_view_pages_03/04`, and browser tests `audit3/4`, `charging_pill`, `detection`, `display_time_zone`, `motion_sheets`, `navigation_assist`, `one_toast_one_sheet`, `overhaul_steps`, `overhaul_sweep`, `quiet_hours_modal`, `round8_fixes`, `surfaces`, `ux_02`, `ux_quiet_wake`. Only selectors and Home-specific expectations changed.

**3. Tests deleted because the approved layout removed the behaviour:** the six ring tests of `test_browser_home_signature.py` (progress, accessible name, no-script render, flourish, outside the picture, glint) and `test_the_hero_picture_leaves_room_for_its_ring` (replaced by a flight-card padding check); the quiet on/off switch tests (Enter on the quiet switch, scripts-blocked quiet switch; the Screen equivalents were kept or added); the Battery-row bar and autonomy tests (replaced by battery-pill tests); the recent-flight row tests (replaced by tile tests). `test_surfaces`'s two list-group checks moved from Home to `/account` (Home has no list group any more; the focus-ring test adds a link row itself).

**4. Strip is a scroll-snap row** so the shared "disclosure sweep" carve-out for deliberate horizontal scrollers applies (`test_browser_ux_02`).

## Verification

- Served-markup and unit: all Home tests, `test_i18n`, `test_structure_guards`, `test_suite_guards`, `test_page_structure`, `test_stylesheet_structure`, `test_companion_app_04` (motion budget), status/view pages, charging, freshness: pass.
- Browser (`SKYPANE_REQUIRE_BROWSER=1`): all 8 `test_browser_home_*` files (218 tests) and every other browser file that renders Home (overhaul sweep, surfaces, ux_02/quiet_wake, quiet-hours modal, motion sheets, audit3/4, charging pill, navigation, detection, display time zone, round8, one-toast): pass, except the pre-existing failure below.
- `server/test_golden_render.py`, `stub-server/test_phase47_freeze.py`: 25 passed. ruff, mypy (46 files), `check_function_size.py check --max 80 server stub-server`, `check_comment_history.py check`: clean. `companion/app.py` 1490 lines (unchanged), `home_page.py` 243, `freshness.js` 714.
- Failing on this branch **and on a clean copy of HEAD** (not caused by this plan, not touched): `test_sign_in_surfaces` (2), `test_config_page_03`, `test_config_page_05`, `test_companion_app_01` (2), `test_sky_contrast` glass test, `test_browser_ux_02::test_the_live_preview_crossfade...` (Display page).
- `test_render_baseline.py` fails on HEAD already (first differing key `/airlines|en|dark`, a stylesheet hash) and still fails; Home's `/` captures also differ now. The baseline and `update_page_one_type_golden.json` were NOT regenerated (plan 22).
- Not run: the full browser suite.

## Visual check (owner rules)

Mockup, built page and previous page were rendered with Playwright (390 and 1280, English and French, light and dark, online, sleeping and offline) and compared side by side; phone captures are full-screen (menu, title, content, tab bar). Differences fixed along the way: pills wrapping (shortened the quiet pill), invisible badge and quiet band in dark (tinted surface), near-invisible pencil and "i" (white/ink surface with a border), strip not aligned with the content edge (`scroll-padding-inline`), alert icon and weight, switch colour, offline greying. Text centring in every pill, 44 px targets and opaque round buttons are asserted in browser tests.

Captures (all in `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p13/`):
- `mock_<on|sleep|off>_ph_fr_<light|dark>.png` (+ `mock_on_ph_fr_<light|dark>_week.png`)
- `after_<on|sleep|off>_ph_<en|fr>_<light|dark>_full.png` (390 px, whole page with tab bar) and `after_<on|sleep|off>_dk_<en|fr>_<light|dark>.png` (1280 px)
- `before_<on|sleep|off>_ph_<en|fr>_<light|dark>_full.png`, `before_..._dk_...png` (old Home from HEAD)
- `cmp_<on|sleep|off>_<light|dark>.png` (mock left, built right), `after_on_ph_<fr|en>_<dark|light>_week_full.png`, `..._quiet_dialog.png`, `..._info_tip.png`

## Known stubs

None.

## Threat flags

None. Threat register items hold: the strip and stats builders escape every dynamic part (plan 33 tests; hostile name tests kept), and every query reads only the signed-in frame's own `history_db` scope (`ctx.state_dir`).

## Commits

- 6d40e6de feat(68-13): assemble Home in the approved online, sleeping and offline states
- 2d7de781 test(68-13): rewrite the Home tests for the approved layout

## Self-Check: PASSED
