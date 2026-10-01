---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 10
subsystem: companion-device-settings
tags: [companion, device, i18n, refresh]
requires: [44-04]
provides: [focused-device-controls, truthful-refresh-feedback]
affects: [device-page, settings-form, poll-action]
tech-stack:
  added: []
  patterns: [native-settings-form, server-confirmed-flash-feedback]
key-files:
  modified:
    - companion/pages/config_page.py
    - companion/settings/wake_interval.py
    - companion/settings/runway_led.py
    - companion/settings/rules.py
    - companion/flash.py
    - companion/test_config_page_05.py
decisions:
  - Keep the Device route and label while removing screen metadata and generic framing.
  - Describe refresh completion as a completed server check, never as a confirmed frame image.
metrics:
  tasks_completed: 2
status: complete
---

# Phase 44 Plan 10: Focused Device Controls Summary

Device now presents only Wake interval, Diagnostic LED, and Refresh now with concise bilingual explanations. The existing native form, validation, dirty-save feedback, and poll handler remain unchanged.

## Completed Tasks

1. Removed Device screen metadata, next-wake header, repeated supersection copy, battery-duration text, and unsupported cadence promises. Kept accessible native Wake interval and LED controls, and made Refresh now a direct action.
2. Added coverage for the bilingual reduced structure, native input persistence contract, and refresh acknowledgement wording.

## Validation

- `./scripts/run-all-tests.sh -- companion/test_config_page_05.py companion/test_i18n.py companion/test_route_table.py` — 133 passed.
- `server/.venv/bin/python3 -m pytest -n 0 -q companion/test_retired_notifications.py` — 5 passed.
- The prescribed browser suite was started with `SKYPANE_REQUIRE_BROWSER=1`; the local shared browser runner reported failures in stale Display/browser coverage before a final result. The focused Device browser persistence test started successfully, and no Device-specific failure was reported before the runner stopped returning final output.

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 2 - Truthful feedback] Updated the existing poll button and flash message outside the original file list.
   - **Found during:** Task 1
   - **Issue:** The existing button said “Trigger poll now” and the success flash promised an unobserved frame image within seconds.
   - **Fix:** Changed the action to Refresh now and described only the completed server-side check plus the possible later frame wake.
   - **Files modified:** `companion/settings/rules.py`, `companion/flash.py`, `companion/i18n_fr/common.py`
   - **Commit:** `244d9124`

## Commits

- `244d9124 feat(44-10): focus device controls and refresh feedback`
- `5a977e38 test(44-10): cover focused device controls`

## Self-Check: PASSED

- Device source, translations, and focused test coverage are present.
- Both task commits are present in the current branch history.
