---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 01
subsystem: server
tags: [hardware, gate, production-switch]
requires: []
provides:
  - SECOND_ENV_VAR (SKYPANE_ENABLE_SECOND_HARDWARE) and extended available_types
affects: [fleet_ops, console_pairing, update_page, byos, firmware_registry, firmware_cli, fleet_cycle, device_scope]
key-files:
  modified:
    - server/hardware.py
    - server/test_hardware.py
    - deploy/skypane.env.example
decisions:
  - Switch name SKYPANE_ENABLE_SECOND_HARDWARE, true only for the exact string "1"; ships closed
requirements: [HW2-04]
completed: 2026-11-14
---

# Phase 64 Plan 01: Second-hardware production switch Summary

A dedicated switch, `SKYPANE_ENABLE_SECOND_HARDWARE` (exactly "1"), exposes only the real gated EE04 type through `available_types`. It never exposes a sim-* type, and it ships closed.

## What changed
- `server/hardware.py`: `SECOND_ENV_VAR`, a typed `_flag_enabled` helper, and an extended `available_types`. The profile's `gated` flag stays True. The module docstring is updated.
- `server/test_hardware.py`: new tests for the second switch alone, both switches together, the values 0/true/empty/11/" 1", and `gated` staying True. A new pin, `test_production_config_never_enables_second_type`, checks that no committed env or service file assigns the switch.
- `deploy/skypane.env.example`: a commented-out block only.

## Pinning tests extended on purpose
`test_evaluation_type_is_hidden_without_the_gate` was extended on purpose, with a why-comment, so it also covers the second switch. `test_production_config_never_enables_second_type` was added next to the existing sim pin, with a why-comment. The three original closed-state tests are unmodified.

## Deviations from Plan
None. The two tasks were committed separately (the pin test sits in the first commit).

## Verification
- pytest server/test_hardware.py, deploy/tests/test_units.py, stub-server/test_phase47_freeze.py and server/test_golden_render.py: 92 passed.
- mypy server/hardware.py: clean. ruff: clean. check_comment_history and check_function_size: see the final report.
- No Phase 47/47.1 file touched. The switch was not lifted.

## Self-Check: PASSED
