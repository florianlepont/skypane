---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 09
subsystem: companion
tags: [detection, companion, display, device, i18n]
requires: [53-06, 53-08]
provides:
  - companion/detection_summary.py (one saved-setting sentence and frame-text builder)
  - read-only Detection card on Display and Device (config_page.detection_card_html)
affects: [53-10, 53-12]
key-files:
  created:
    - companion/detection_summary.py
    - companion/test_display_detection_card.py
  modified:
    - companion/pages/config_page.py
    - companion/pages/detection_page.py
    - companion/screens.py
    - companion/settings/form_post.py
    - companion/settings/runway_led.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/registry.py
    - companion/detection_actions.py
    - companion/app.py
    - companion/routes.py
    - companion/test_config_page_01.py
    - companion/test_config_page_02.py
    - companion/test_config_page_03.py
    - companion/test_config_page_04.py
    - companion/test_config_page_04b.py
    - companion/test_config_page_05.py
    - companion/test_config_page_helpers.py
    - companion/testdata/render_baseline.json
requirements-completed: [DET-01]
completed: 2026-10-31
---

# Phase 53 Plan 09: Remove the Display Runway card, add the read-only Detection card Summary

The Display page no longer has a Runway card for any device, a Display save never reads, changes or resets `tracked_runway` or `detection`, and Display and Device now show a read-only Detection card that links to the device-scoped `/detection`.

## Commits

- f8ab9c3 remove the Runway group, fieldset, resolver and French strings; config-page tests describe the new behaviour
- 7955ebd Detection card on Display and Device, summary module, location wiring, new behaviour tests, regenerated baseline

## Behaviour

- Display: the Runway card is gone. Its slot (after the Aspect section, before Quiet hours) holds a `.theme-status detection-card` with an `h2` "Detection", a caption sentence for the saved setting and a 44 px link "Change airport, runway or position". It has no input, select or button and no `data-dirty-section`, so the dirty-section list no longer contains "Runway".
- Device: the same card is the first card, before Diagnostic LED. Device stays admin-only (matrix unchanged, owners get 404).
- Wording lives in one place: `companion/detection_summary.py` (moved out of `detection_page.py`, same message ids) builds the "Runway 08L/26R at ... (CDG)" / "Aircraft within 9 km of Home" sentence; the Detection page and both cards call it. A position setting without a usable location reads as the Orly sentence, as the frame behaves.
- A position setting names its location: `GET /display`, `GET /device` and the rejected-settings re-render pass the device's usable location name (read from fleet.db only when the saved mode is position) through `config_page.render(..., location_name=)`.
- `/settings` no longer has a runway resolver: a forged `tracked_runway` is never read (no field error, config untouched). `ADMIN_ONLY_SETTING_FIELDS` in `user_view.py` was left as it was (defensive strip, harmless).
- `GROUP_RUNWAY`, `runway_fieldset`, `RUNWAY_*` captions and ids, and the three orphaned French strings (`display.runway`, `display.which_orly_runway_the_device_watches`, `display.airport_diagram_for`, `registry.runway_*`) are removed. `RUNWAY_IMAGE_ROUTE_PREFIX` stays (the admin runway image route still exists).
- History: the history and gallery pages never printed `tracked_runway`; a test inserts rows with `3`, `LFPG:08L/26R`, `position:9`, an unknown id and a markup id and checks Flights, Home and Airlines render with the rows and no raw markup.
- Baseline: only the Display and Device keys changed (`/pages//display` and `/pages//device`, each with and without `?flash=saved`, en/fr, light/dark).

## Verification

- Config-page tests (six files plus helpers): 260 passed. New `test_display_detection_card.py`: 17 passed. Plan verify set (render baseline, i18n, access matrix, route table, suite guards, detection page and position tests): 1334 passed.
- `pytest companion -m "not browser"`: 3806 passed, 3 skipped, 5 failed (all in plan 12's list, below).
- Browser suite (`PLAYWRIGHT_BROWSERS_PATH` scratch dir with `chromium*-1248` symlinks to the 1243 builds): 545 passed, 12 failed (all in plan 10's files, below).
- ruff clean, mypy clean (28 files), function-size gate (905 functions, none over 80), comment-history check exit 0, `stub-server/test_phase47_freeze.py` 21 passed. `git diff --stat` for the first commit shows no change to `detection_page.py`, `detection_actions.py` or `routes.py`.

## Tests left failing on purpose (they assert the old Runway card)

Plan 12 (non-browser):
- `companion/test_companion_app_04.py::test_scoped_settings_save_carries_other_page_forward` (expects a Device save to persist `tracked_runway=06-24`)
- `companion/test_companion_app_04.py::test_display_and_device_pages_split_the_groups` (expects the runway group on Display)
- `companion/test_user_health.py::test_user_display_keeps_everyday_controls_and_drops_admin_ones[en]` and `[fr]` (reference `RUNWAY_GROUP_HEADING_ID`, now removed)
- `companion/test_user_view_http.py::test_user_display_has_no_runway_wake_interval_or_led_control` (a user-view control check expects `name="tracked_runway"` on the admin Display page)

Plan 10 (browser):
- `test_browser_phase44_walkthrough.py::test_display_setting_saves_and_reports_a_keyboard_focusable_control[chromium-en]` and `[chromium-fr]`
- `test_browser_ux_01.py::test_the_leave_guard_re_arms_after_a_new_edit_following_cancel`, `::test_display_reveal_and_persist_across_all_field_kinds`, `::test_three_runway_cards_share_one_line_at_390px`
- `test_browser_ux_03.py::test_the_bars_save_persists_every_field_never_only_the_touched_one`, `::test_the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor`
- `test_browser_ux_04.py::test_section_naming_reflects_the_fields_actually_changed_in_document_order`, `::test_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies`, `::test_the_bar_settles_the_field_disk_agree_and_the_bar_hides`, `::test_the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end`, `::test_a_settings_card_title_renders_identically_on_both_settings_pages`

`test_companion_app_05`, `test_airline_sheet`, `test_device_dispatch`, `test_device_pages`, `test_display_looks`, `test_freshness_token`, `test_user_view`, `test_view_pages_*` and the test-support helpers named in the plan pass unchanged.

## Deviations from Plan

**1. [Rule 3 - Blocking] Files outside the plan's list**
- `companion/detection_summary.py` (new) and `companion/pages/detection_page.py`: `detection_page` imports `config_page`, so `config_page` cannot import the page's summary builder. The sentence and frame-text logic moved to a neutral module with the same message ids; `detection_page` keeps its behaviour and calls it.
- `companion/detection_actions.py`, `companion/app.py`, `companion/routes.py`: a small `card_location_name` / `_detection_card_location` hook so the cards can name a position setting's location. The plan's "no change to routes.py" criterion applies to task 1 and held for that commit.
- `companion/i18n_fr/registry.py`: removed the three runway label translations that no Message declares any more (`test_i18n` fails on orphans) and updated its docstring.
- `companion/test_config_page_04.py`: the calendar code-isolation check removes the Detection card first (it prints the watched airport code ORY, which is the saved setting, not calendar data).

**2. [Design] Test rewrites rather than deletions**
- Tests for `runway_fieldset` and the runway captions were deleted with the function; the guards on other behaviour were kept and re-pointed (rules segment boundary is now the end of the Aspect section, the Current badge and its French text are checked on the Detection page's runway cards, the save round trip asserts the posted runway is ignored).
- The `section-caption` floor minimum became 4 on Display and 3 on Device (the card's caption counts).

**3. [Fix] Docstring of `config_page.render`** lost its line break before the closing quotes in the first commit; repaired in the second.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register: T-53-41 (forged `tracked_runway` ignored, handle_post and HTTP tests), T-53-42 (sentence and location name escaped; hostile location name and hostile history ids tested), T-53-43 (Device remains admin-only, owner gets 404), T-53-44 (Display save leaves `detection` and `tracked_runway` unchanged, tested for runway and position settings).

## Self-Check: PASSED

Files exist (`companion/detection_summary.py`, `companion/test_display_detection_card.py`); commits f8ab9c3 and 7955ebd present. STATE.md and ROADMAP.md were not touched.
