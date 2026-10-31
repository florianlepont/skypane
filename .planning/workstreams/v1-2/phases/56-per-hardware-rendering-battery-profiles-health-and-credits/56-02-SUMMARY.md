---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 02
subsystem: server
tags: [hardware-profile, battery-provenance, themes]
requires: []
provides:
  - BatteryProvenance on BatteryProfile, inks and layout_family on HardwareProfile
  - PLANNED_BATTERY_SLOTS (empty EE04 slot, not in REGISTRY) and registry_problems()
  - theme_required_inks, themes_for_inks, theme_or_default
affects: [56-03, 56-04, 56-05]
key-files:
  modified:
    - server/hardware.py
    - server/themes.py
    - server/test_hardware.py
    - server/test_themes.py
requirements-completed: [HWR-01]
completed: 2026-10-30
---

# Phase 56 Plan 02: Hardware profile data model Summary

Battery values now carry provenance (all provisional), profiles declare inks and layout family, the EE04 battery slot exists with no numbers, and themes filter by available inks with fallback to white.

## Commits
- bc98e23e hardware.py provenance, inks, layout family, planned slot, validation
- 20bb1e11 themes.py ink accessors and tests

## Notes
- low_clear_mv date is 2026-10-05, the commit that introduced the constant (git log -S); the policy module's latest commit is unrelated.
- sim-landscape provenance is copied text, values unchanged; sim-ee02-clone shares the legacy battery object.
- `server/device_policy.py` untouched; 16 theme ids pinned by a snapshot test.

## Deviations from Plan
None. Registry validation is `registry_problems()` (returns a list); tests monkeypatch REGISTRY to exercise failures.

## Verification
test_hardware, test_themes, test_golden_render, phase47 freeze, companion suite guards pass (200 targeted); mypy, ruff, comment-history and function-size gates clean. Full suite not run (concurrent edits).

## Self-Check: PASSED
