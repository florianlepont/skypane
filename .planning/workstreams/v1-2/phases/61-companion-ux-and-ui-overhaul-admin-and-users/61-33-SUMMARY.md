---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 33
subsystem: companion
tags: [display, location-page, time-zone, cleanup]
requires: [61-25, 61-27]
provides: [Display without location card, picker or time zone select]
key-files:
  modified:
    - companion/pages/config_page.py
    - companion/pages/locations_page.py
    - companion/console_locations.py
    - companion/detection_actions.py
    - companion/settings/quiet_hours.py
    - companion/app.py
    - companion/routes.py
    - companion/static/place-map.js
    - companion/static/style.css
    - companion/i18n_fr/display.py
    - companion/i18n_fr/admin_locations.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 33: Display loses the place and the time zone

Display no longer renders the Location and detection card, the location picker or the time zone select. The Quiet hours card keeps its controls and ends with one sentence, linked device-scoped to `/detection#details`. Saving Display never reaches the location assignment. Single commit 6eab4c3 (the plan says both tasks commit together).

## What changed

- `config_page`: the merged card, its constants and the picker call are gone; `handle_post` no longer calls the assignment/undo helpers (so a crafted `location_id` is simply not read) and no longer takes `handler`; `render` no longer takes `location_name`. `resolve_timezone` stays in the post: absent means unchanged, an unchanged value is not rewritten, an invalid zone is refused as before (200 re-render with the "Time zone not saved" toast, nothing written).
- `quiet_hours`: the time zone select (`timezone_field_html`) and its ids/helper string are deleted; `quiet_hours_group` always ends with the note linking to the details card.
- Deleted leftovers nothing imports any more: `console_locations.display_picker_html`, `apply_device_location`, `undo_device_location` and helpers; `locations_page.picker_html` and its strings; `detection_actions.card_location_name`; `App._detection_card_location` (app.py is now 1492 lines); dead French strings and the dead `.quiet-timezone*` / `.detection-card` CSS. `detection_page.py` needed no change: it had no leftovers nothing imports.
- The note link had to be a 44 px target on Display too: the rule that was `.modal .quiet-timezone-note a` now applies to `.quiet-timezone-note a`.

## Tests (moved in place)

`test_display_detection_card.py`, `test_display_time_zone_card.py`, `test_location_picker.py` rewritten for absence on Display, presence on the Location page, a crafted `location_id` moving nothing (user and admin, no audit row), absent fields leaving zone, position and detection unchanged, and the legacy invalid zone still refused. `test_device_settings.py` zone tests now read the select on the Location page (options, FR, unlisted stored zone) while the post-side tests (valid, Paris never adds the key, atomic refusal) are kept. `test_browser_display_time_zone.py` rewritten (360/1280, EN/FR, both themes: absence, 44 px by hit-testing, no overflow, link lands on the open details card). Also updated: `test_browser_detection.py` (the user Display section), `test_browser_ux_01/04.py`, `test_browser_phase44_walkthrough.py`, `test_companion_app_04/05.py`, `test_config_page_05.py`, `test_user_health.py`, `test_user_view_http.py`, `test_console_locations.py`.

## Deviations

1. **[Rule 1] `place-map.js` closed the details card even for a `#details` link**, so the note's link could not land on an open card. It now keeps the card open when the URL hash names it.
2. **[Rule 3] CSS**: the note link needed the 44 px rule outside the dialog; dead zone/card rules removed.
3. Section-caption floors lowered where the removed card was the subject: Display 4 to 3 (`test_companion_app_05`, `test_config_page_05`), site total 18 to 16 (measured: the card's caption is gone; the floor guards against an empty selector, not a count of the removed card).
4. An invalid-zone post answers 200 (existing behaviour), not 400; the test pins that.
5. Render baseline moved for the eight Display page entries only (verified by diffing keys); sign-in digests did not move.

## Gates

ruff, mypy (29), comment-history, function size (931, none over 80), Phase 47 freeze (21 passed): clean. Browser tests stressed 4 parallel runs, 25 each: 0 failures. Full `companion test-support stub-server -n auto --no-cov` after the final code commit: 7150 passed, 4 skipped (root permission bits), 0 failed.

## Known Stubs

None.

## Self-Check: PASSED
