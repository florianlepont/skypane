---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 05
subsystem: companion
tags: [battery, hardware-profile, companion]
requires: []
provides:
  - battery percent on console rows, pending rows, frame switcher and account summary uses the frame's profile curve
affects: [companion/console_pairing.py, companion/ui_shell.py, companion/sign_in.py]
key-files:
  created: [companion/test_battery_curve_call_sites.py]
  modified: [companion/console_pairing.py, companion/ui_shell.py, companion/sign_in.py]
decisions:
  - Pending rows read the stored type's curve straight from hardware.REGISTRY so display does not depend on the production switch
metrics:
  tasks: 1
  completed: 2026-11-14
requirements: [HW2-04]
---

# Phase 64 Plan 05: Battery curve call sites Summary

Battery percent now follows the frame's own profile curve at every companion surface that still used the legacy curve.

## What changed
- `console_pairing`: device rows use `page_context.device_curve(device)`; pending rows use the curve of the stored type from `hardware.REGISTRY` (unknown type: legacy). `page_context` is imported on use inside `_device_rows` to avoid an import cycle.
- `ui_shell._switcher_status_row`: `battery.percent(mv, page_context.device_curve(device))`.
- `sign_in._frame_summary`: uses the registry profile already looked up for the label, legacy when absent.
- `grep battery_percent(` in the three modules prints nothing.

## Tests
`companion/test_battery_curve_call_sites.py` (6 tests): a test-only registry with a shifted curve gives a different percent than legacy at device rows, pending rows (gate open and closed), switcher row and account summary; legacy frames show the legacy percent; unknown stored type reads legacy without raising. RED before migration (2 failed, shifted-curve cases), GREEN after.

Verification: `pytest companion -k "battery or console_pairing or sign_in or ui_shell"`: 375 passed, 156 skipped (browser tests, no Chromium); plan's listed files: 91 passed; ruff and comment-history clean.

## Deviations from Plan
- [Rule 3] First migration imported `page_context` at module level in `console_pairing`, causing a circular import; moved to an on-use import.
- Tests call the row builders and handler method directly rather than parsing served HTML.

## Notes
`companion/test_battery_profile.py` run alone fails at collection with a circular import (`battery_chart`); this also happens on the untouched HEAD and is not caused by this plan. It passes when collected with the other companion tests.

## Self-Check: PASSED
