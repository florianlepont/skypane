---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 16
subsystem: companion
tags: [display, time-zone, a11y, empty-state, css]
requires: [61-12]
provides: [time zone in the merged card, 44 px desktop targets, compact empty states everywhere outside the filter form]
key-files:
  created:
    - companion/test_display_time_zone_card.py
    - companion/test_browser_display_time_zone.py
  modified:
    - companion/settings/quiet_hours.py
    - companion/pages/config_page.py
    - companion/i18n_fr/display.py
    - companion/static/style.css
    - companion/pages/history_page.py
    - companion/ui_components.py
    - companion/test_browser_overhaul_sweep.py
    - companion/test_empty_state_scale.py
    - companion/test_browser_empty_state_scale.py
    - companion/test_device_settings.py
    - companion/test_display_detection_card.py
    - companion/test_companion_app_01.py
    - companion/test_status_pages_02.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 16: Owner-approved follow-ups Summary

The time zone select now lives in the merged Location and detection card with its own "Time zone" save-bar section, the desktop sidebar, brand link and Home Health pill resolve to 44 px hit boxes, and no empty state outside the filter form is large.

## Commits

- fb8ccf0: the plan.
- 5ea3d74: time zone into the merged card.
- bf7d7a7: 44 px desktop targets.
- c5875f7: compact empty states (History, table fallback), traceability.

## What changed

- **Time zone.** `detection_card_html` takes the field html; `timezone_field_html(..., dirty_section=True)` wraps it in `data-dirty-section="Time zone"` (FR "Fuseau horaire") so the save bar names it. Same `name="timezone"`, same `form="settings-form"`, same route and `resolve_timezone`: no server change. `quiet_hours_group(zone_card_href=...)` replaces the field with a sentence and a `#location-detection` link (new FR string). The legacy all-scope render keeps the field inside the Quiet hours card, unchanged.
- **44 px.** `.sidebar-link` is `min-height: 44px` (rows touch, `gap: 0`, so the sidebar grows by 12 px per link instead of 16), footer segments 44 px, Sign out 44 px, brand link 44 px, and the 32 px desktop override of the Health pill is gone. The sweep hit-tests the resolved boxes for admin and user sidebars and the pill (EN/FR, both themes) and checks the sidebar still fits the 900 px viewport.
- **Empty states.** History (no flights, device empty) and `data_table`'s fallback are compact.

## Deviations from Plan

1. **[Stale premise] Detection (3) and My frames were already compact.** Only History (2) and the table fallback were large. The traceability said otherwise; it now states the truth. No code change was needed for those.
2. **Task 1 dirty wrapper only in the merged card.** Putting the wrapper on the field everywhere broke two legacy all-scope tests (`test_config_page_02/03`, "exactly three dirty sections"); the wrapper is now opt-in, so those tests are unchanged.
3. **Tests updated deliberately:** `test_device_settings.py` (field location), `test_display_detection_card.py` (card now holds Location and Time zone), `test_companion_app_01.py` (sidebar link is `min-height: 44px`, was `height: 32px`), `test_status_pages_02.py` (`data_table` fallback is compact).
4. **Render baseline:** only the Display pages moved (time zone); the 44 px CSS and the History change do not change it.
5. 61-STEP-COUNTS.md untouched: no counts changed (the time zone move does not alter the measured quiet-hours path).

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
ruff, mypy (28 files), comment history, function size (922 functions) and the Phase 47 freeze test (21 passed) clean. `./scripts/run-all-tests.sh`: 9346 passed, 8 skipped (root-permission and openssl skips, no browser skips), coverage 96.21% against the 93.0% floor. Commits fb8ccf0, 5ea3d74, bf7d7a7, c5875f7 exist.
