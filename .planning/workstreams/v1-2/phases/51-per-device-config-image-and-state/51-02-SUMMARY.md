---
phase: 51-per-device-config-image-and-state
plan: 02
subsystem: fleet
tags: [timezone, quiet-hours, device-config]
requires: []
provides:
  - device_config timezone key (normalise_timezone, _validate_timezone, save_device_config(timezone=None))
  - device_policy.timezone_for and tz keyword on seconds_until_quiet_hours_end
key-files:
  modified:
    - server/device_config.py
    - server/device_policy.py
    - server/test_device_policy.py
    - server/test_config_history.py
    - server/test_retired_notifications.py
    - companion/test_config_page_02.py
metrics:
  completed: 2026-10-30
---

# Phase 51 Plan 02: Per-device time zone Summary

Quiet hours are now evaluated in a per-device IANA zone (default Europe/Paris), validated on write against `zoneinfo.available_timezones()` and omitted from `device_config.json` when it equals the default, so the live frame's file bytes are unchanged.

## Commits

- 001b509: device_config timezone key
- 66f617f: companion config test expects the new loaded key
- b642761: device_policy tz-aware quiet-hours arithmetic

## Verification

- pytest server, companion, stub-server test_poll_cycle / test_phase47_freeze / test_image_negotiation: all passed (3582 passed, 546 skipped; browser tests skip, no Chromium in this sandbox)
- mypy clean, ruff clean, check_comment_history clean, check_function_size: 617 functions, none over 80
- tz database precondition: `len(available_timezones()) > 100` is True in the venv

## Deviations from Plan

**1. [Rule 3 - Blocking] Existing full-dict assertions updated.** `load_device_config` now returns eleven keys, so exact-dict assertions in `server/test_config_history.py` (several) and `companion/test_config_page_02.py` (`test_valid_save_writes_both_and_returns_saved_key`) gained `"timezone": "Europe/Paris"`. `companion/test_config_page_02.py` was outside the plan's files list.

## Known Stubs

None.

## Self-Check: PASSED
