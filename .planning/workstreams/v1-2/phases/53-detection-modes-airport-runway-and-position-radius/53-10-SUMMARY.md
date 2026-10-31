---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 10
subsystem: companion-tests
tags: [detection, playwright, browser-tests, dirty-bar, leave-guard]
requires: [53-08, 53-09]
provides:
  - companion/test_browser_detection.py (20 browser tests for /detection)
  - legacy browser tests re-pointed at the Detection card and page
key-files:
  created:
    - companion/test_browser_detection.py
  modified:
    - companion/test_browser_phase44_walkthrough.py
    - companion/test_browser_ux_01.py
    - companion/test_browser_ux_03.py
    - companion/test_browser_ux_04.py
requirements-completed: [DET-01, DET-03]
completed: 2026-10-31
---

# Phase 53 Plan 10: Detection page browser tests Summary

Real-browser proof of the Detection page: the scripts-blocked search, pick and save flow, the hidden-panel submit rule for each mode, measured layout and hit targets, the quiet Search button against the accent Save, and the scripts-on dirty bar, Cancel and leave-guard behaviour. The twelve legacy browser tests that clicked the removed Display Runway card now describe the new Display page.

## Commits

- 93014ed test(53-10): browser checks for the Detection page (tasks 1 and 2, one module)
- 1891784 test(53-10): point the legacy browser tests at the Detection card and page (task 3)

## What the tests cover

- No-JS at 360 px in English and French: search "cdg", pick Charles de Gaulle, check 08L/26R, save; stored `detection` read from disk.
- Hidden-panel rule, one test per mode: runway saves while the hidden radius holds 99; position saves while the hidden runway panel lists runways with none checked; four refused cases (runway missing, airport missing, radius empty, radius 99) answer HTTP 200 with the exact inline message and leave the stored file byte-identical.
- Layout at 360 and 390 px: no horizontal overflow, result rows and runway cards at least 44 px in both axes (bounding box of the label or link itself), French mode segments neither clipped nor under 44 px.
- Search button: computed background differs from the accent Save fill, at least 44 px tall at 360 and 1280 px. Accent budget: elements painted with the Save fill are only the Save buttons, the selected mode segment and the skip link.
- Scripts on: toggle reveals "Detection changed" (English and French), inactive panel out of the layout, Cancel restores the saved mode; search and pick navigations raise no prompt and the typed radius 12 survives with the carried bar and armed guard; Cancel in the carried state returns to plain `/detection` and the stored radius; a real leave to another page still prompts; after a page-local navigation and `go_back` the guard is armed again and a later leave prompts.

## Legacy tests updated (none deleted, no assertion weakened)

- Display tests now assert the Runway card, `.runway-map`, photographs and `tracked_runway` radios are absent and that the Detection card links to `/detection`.
- Tests that only used the runway radio as "a field to change" now use the theme chips (leave-guard re-arm, bar settle, section naming, form-associated path, bar-save-every-field, no-JS floor save) or the quiet-hours time input where a keyboard-focusable control is required (walkthrough).
- `test_three_runway_cards_share_one_line_at_390px` became `test_three_runway_cards_stack_in_one_full_width_column_at_390px` and measures the LFPO cards on `/detection` (one-column grid below 600 px: equal left edges, equal widths, no overlap, border total 2.0, exactly one scaled card, 44 px).
- `test_the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor` became `test_the_map_is_gone_and_the_detection_runway_cards_meet_their_floor`: zero map, card and radio on Display; per-runway cards on `/detection` without overflow and with a 44 px hit area in both themes.
- `test_the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end` became `test_a_form_associated_radio_path_reaches_the_bar_and_disk_end_to_end` (theme radios, same cross-tree `form=` path).
- Settings card title cardinality test now also allows the Detection card title on Device.

## Results

- `pytest companion -m browser` (Chromium via a scratch `PLAYWRIGHT_BROWSERS_PATH` of 1248 symlinks to the installed 1243 builds, outside the repo): 577 passed, 0 failed, including the 20 new tests and the 12 legacy ones.
- `test_suite_guards.py` + `test_structure_guards.py`: 173 passed. ruff clean, mypy clean (28 files), comment-history check exit 0.

## Deviations from Plan

1. **[Data] No ten-runway airport exists.** The catalogue's maximum is four runways (LFPG, LFPE, LFMY, LFPK). The overflow test picks the airport with the most runways from `server.airports` at run time and asserts one card per runway; it fails if the largest airport has fewer than three.
2. **[Rule 3] Position saves need a device row.** A legacy server with no `devices` row answers `save_failed` to a position save, so the browser fixture seeds a live frame (state path ".") owned by the signed-in administrator, plus the Home location.
3. **[Naming] Three legacy tests renamed** because the old names asserted facts that are no longer true (see above).
4. **Tasks 1 and 2 share one commit** since both live in one new module written together.
5. The hidden-position-valid test starts from `?airport=LFPG&mode=position` to get a hidden runway panel with cards and none checked.

## Known Stubs

None.

## Self-Check: PASSED

`companion/test_browser_detection.py` exists; commit 93014ed and the legacy-test commit exist; STATE.md and ROADMAP.md untouched.
