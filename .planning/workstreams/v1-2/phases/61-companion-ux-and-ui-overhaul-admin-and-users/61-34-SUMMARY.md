---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 34
subsystem: companion
tags: [home, notification, mailto, display, quiet-hours]
requires: [61-27, 61-33]
provides: [Home amber and red notification with administrator mailto, Display without quiet hours]
key-files:
  created:
    - companion/pages/home_notice.py
    - companion/test_home_notice.py
    - companion/test_browser_home_notice.py
  modified:
    - companion/pages/home_page.py
    - companion/pages/config_page.py
    - companion/i18n_fr/home.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 34: Home notification for amber and red, Display without quiet hours

Display no longer renders the Quiet hours card and a Display save never touches a quiet-hours key. Home shows one notification, in the region the refresh swaps, whenever the dot is amber (not seen yet, overdue, low battery) or red (no contact), for owner, co-manager and administrator alike. One code commit (the plan says all three tasks commit together).

## What changed

- `home_notice.py` (new): `administrator_contact(conn)` picks the first row of `fleet_db.list_users` with role admin and not disabled, by id, and returns its address only when it passes a conservative shape check (single `@`, no whitespace, comma, angle bracket, quote, `?`, `&`; at most 254 characters); any database error gives None. `contact_for_state_dir` opens a short-lived read-only handle. `notification_html` builds the docked warning or error toast: explanation as title, the known figures, one tip, then the help lead-in and the "Contact an administrator" link (or the plain-text fallback with no link and no address). The href is `mailto:` plus the address percent-encoded (safe set `@`) plus subject and body percent-encoded with an empty safe set; the toast action escapes the attribute.
- `home_page`: `render` reads the frame summary and the frame-status verdict once and passes both to `_frame_state_html` and to the notification, so the dot and the notification cannot disagree. The `.home-facts` region now sits directly under the state card (it was after the picture row, below the fold on a phone). When the status is amber or red the notification replaces the old docked "Something needs attention" toast; for an administrator whose frame is green but whose pipeline is warning, the old toast still renders as before.
- Copy (EN in `home_notice.py`, FR in `i18n_fr/home.py`, ids `home.notice_*`): per status key an explanation, a figure line when the datum is known (battery percent, "may be charging" when the voltage trend says so, "Last check-in 50m ago", "Last contact 5h ago"), a tip, and for no contact the sentence "SkyPane cannot tell a Wi-Fi, an internet or a server problem apart". The no-contact wording names no cause, never says amber, and none of the notification text contains Health, Device or Console.
- `config_page`: the Display scope no longer renders the Quiet hours card and ignores `quiet_hours_*` fields on a Display post (`_resolve_quiet_hours`). The legacy all-scope render and post path (never served by a live route) keep the group, so its helper functions and the tests of them stay.
- `style.css`: two small rules for the figure and tip lines; the link reuses the 44 px toast action.
- `render_baseline.json`: 12 entries moved (Home and Display, 2 languages x 2 themes, plus Display with the saved flash); sign-in digests did not move.

## Tests

- `test_home_notice.py` (30): every status key in EN and FR (exact lines and tips), the other statuses showing nothing, dropped lines for unknown data, contact choice (lowest id, disabled admin skipped, user skipped, none, missing database, unreadable database), hostile stored addresses (fake connection rows the real insert refuses), hostile frame name escaped in markup and encoded in the href, mail subject and body, no route added and no non-mailto link, recovery removing the notification, and real requests for owner, administrator and co-manager.
- `test_browser_home_notice.py` (36): not seen, low battery, no contact, overdue at 360 and 1280 px, EN and FR, both themes: visible, no overflow, nothing clipped, link at least 44x44 by hit-testing and after the tip in reading order, mailto address and decoded subject, plain text without an administrator, and the next refresh after a check-in removing the notification without a reload. Stressed 4 parallel runs: 0 failures.
- Moved in place: `test_browser_ux_quiet_wake.py` (the five dial tests on Display become three Home-dialog tests: scripts-blocked save in EN/FR, a preset reaching disk, 44 px floors at 360 px in both themes; the wake-slider tests are unchanged), `test_browser_display_time_zone.py` (Display absence, dialog note link at 44 px), `test_browser_detection.py`, `test_browser_overhaul_steps.py` (U4 is now the Home flow, three actions), `test_browser_phase44_walkthrough.py`, `test_browser_ux_01/02/03/04.py`, and the config-page, device-settings, user-view, location-picker, display-card, status-page and parity tests. R21 isolation is `test_a_display_save_changes_no_quiet_hours_zone_place_or_detection_key` (whole stored config compared before and after).

## Deviations from Plan

1. **[Rule 3] `.home-facts` moved up** under the state card; at its old place the notification was below the fold at 1280x900, which the plan's "next to the state card" requires.
2. **Tip height**: the plan's browser behaviour says the tip and the link are each at least 44 px high. The tip is a text line; the browser test pins the notification and the link at 44 px and the tip as visible, unclipped and before the link. On wide screens the link sits beside the text column, not under it, so the test accepts below or beside.
3. **Dial tests removed rather than ported one by one**: the quiet dial (arc, handles, held press, caption forms) has no Display page to live on and the Home dialog has no dial; their intents (scripts-blocked save, presets, 44 px floors, save to disk) are covered by the three Home-dialog tests. The dead dial builders in `settings/quiet_hours.py` and the dial CSS/JS remain (still exercised by the legacy all-scope render tests); removing them is left for a cleanup plan.
4. `test_browser_ux_04`: section-naming lost its two-section join (Display has one dirty section now); the cancel test lost its dial half; `test_quiet_hours_fields_and_presets_lead_the_ring_and_save` was removed (its subject, the Display card, is gone). Caption floors lowered where the card was the subject (Display 3 to 2, site total 16 to 14).
5. `test_browser_ux_03` dirty-form check now uses an unsaved theme pick as the uncommitted edit (the typed field it used left Display).
6. The notification does not use `battery_life_estimate` (it needs a daily series the page does not hold); it uses the existing charging estimate through `health_signals.charging_likely`.
7. `app.py` untouched (1492 lines).

## Known Stubs

None.

## Resume note

A container restart interrupted the first executor with all work uncommitted. At resume the working tree held the complete implementation, the tests and this summary; each plan task was verified against the code and nothing needed completing or changing.

## Gates

ruff, mypy (29 modules), comment-history, function size (931 functions, none over 80), Phase 47 freeze (21 passed): clean. The new and moved browser tests passed 3 runs in a row (42 passed each) and 4 parallel runs of the notice browser module (36 passed each). Full companion + test-support + stub-server run with -n auto after the final code state: 7223 passed, 4 skipped (root-only permission-bit tests, not browser tests).
