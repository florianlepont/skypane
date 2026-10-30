---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 04
subsystem: battery-policy
tags: [battery, device_policy, byos, hardware-profile]
requires: [56-01]
provides:
  - device_policy functions with optional curve/threshold keyword parameters (legacy defaults)
  - DeviceContext.recover_mv populated from the hardware profile
affects: [56-05]
key-files:
  modified:
    - server/device_policy.py
    - server/test_device_policy.py
    - stub-server/byos_server.py
    - stub-server/test_device_fleet.py
requirements-completed: [HWR-01]
completed: 2026-10-30
---

# Phase 56 Plan 04: Profile-driven battery policy Summary

Battery hysteresis, critical hysteresis, critical-pin, fraction and percent functions take optional keyword overrides defaulting to the unchanged module constants, and BYOS pins/releases the critical park using the device profile's `critical_recover_mv`.

## Commits
- aff52b6c device_policy parameters and identity/difference tests
- e83e7722 byos commit (DeviceContext.recover_mv, battery_critical_sleep_s(recover_mv=), fleet tests)

## Verification
- Identity sweeps (mV -1..4300 plus boundaries, both latch states, None) pass for all five functions; a synthetic curve changes clamps and percent.
- Fleet test: profile recover 3600 releases at 3650 mV where the legacy 3700 pins; live context keeps the legacy value.
- stub-server suite: 316 passed, 1 skipped (root permission test) before the final test fix; test_device_fleet + freeze re-run green. mypy, ruff, function-size, comment-history clean.
- No `BATTERY_*` constant line changed.

## Deviations from Plan
None of substance. Tests were added alongside the implementation rather than strictly before it. The fleet test exercises `_device_context` in-process with a patched profile (the BYOS server runs in a subprocess in the harness).

## Self-Check: PASSED
