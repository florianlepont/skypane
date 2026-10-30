---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 07
subsystem: companion
tags: [battery, health, hardware-profile]
requires: [56-02, 56-04]
provides:
  - device_scope.profile_for(device), never raises, legacy fallback
  - battery.percent/fraction/low_display_mv/battery_life_estimate with optional curve
  - page_context.device_curve(device) feeding Home, Health and the chart
key-files:
  modified:
    - companion/battery.py
    - companion/battery_chart.py
    - companion/device_scope.py
    - companion/page_context.py
    - companion/pages/home_page.py
    - companion/pages/health_page.py
    - companion/health_signals.py
    - companion/test_battery_profile.py
    - companion/test_device_scope.py
requirements-completed: [HWR-01]
completed: 2026-10-30
---

# Phase 56 Plan 07: Companion battery and health read the hardware profile Summary

Home and Health percent, ring, readout, chart plot and low-mark line now use the device's profile curve; the legacy device renders byte-identical output and an unknown or gated-off hardware type falls back to the legacy profile.

## Commits
- 1e54952c profile_for, curve-aware battery arithmetic, global-heuristic comments, tests
- cd408dcb pages and chart pass the device curve, served-page tests

## Notes
- `battery.battery_fraction/battery_percent` stay the server policy's own objects (an existing test pins that identity). New `battery.fraction/percent(mv, curve=None)` wrappers carry the optional curve. `low_display_mv(None)` returns the module `LOW_BATTERY_DISPLAY_MV` (a test patches it).
- The curve is threaded explicitly (`curve=None` keyword) through battery_chart, health_page and `health_state_from_signals`; `page_context.device_curve` resolves it once per request in the lazy health-state loader. No new PageContext field.
- Charge heuristics (battery.py) and `BATTERY_DROP_WARN_MV` (health_signals.py) stay global with a comment that they are single-pack calibrations.
- No registered profile has a non-legacy curve yet, so different-curve behaviour is tested with a patched registry and synthetic curve; unknown hardware is tested through a served fleet row.

## Deviations from Plan
- The wake-interval life sentence on the Config page (`wake_interval.py`, outside this plan's file list) still uses the legacy curve; `battery_life_estimate` accepts a curve but Config does not pass one yet. Deferred.
- `poll_supported` untouched, as instructed. companion/testdata/render_baseline.json unchanged.

## Verification
`pytest companion -n auto --no-cov`: 3590 passed, 561 skipped (Chromium not installed locally, browser tests skipped). ruff, mypy, comment-history and function-size (max 80) clean.

## Self-Check: PASSED
