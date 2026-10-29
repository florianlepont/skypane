---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 01
subsystem: server
tags: [hardware, registry, fleet]
requires: []
provides:
  - server/hardware.py registry (HardwareProfile, available_types, get_profile, is_known)
affects: [fleet database, OTA, rendering]
tech-stack:
  added: []
  patterns: [frozen dataclasses, MappingProxyType registry, call-time env gate]
key-files:
  created: [server/hardware.py, server/test_hardware.py]
  modified: [pyproject.toml]
key-decisions:
  - Simulated types visible only when SKYPANE_SIM_HARDWARE equals "1", read per call
requirements-completed: [DATA-04]
duration: 10min
completed: 2026-10-29
---

# Phase 48 Plan 01: Hardware Profile Registry Summary

Committed code registry of hardware types (legacy EE02 derived from existing panel_format/device_policy constants, plus two env-gated simulated types), with drift, gate, immutability and production-config tests.

## Tasks

1. Hardware registry module and tests: 064b49c
2. Production guard test (included in the Task 1 test file) and mypy registration: 17c5bb9

## Verification

- pytest server/test_hardware.py: 16 passed
- mypy: clean (13 files); ruff: clean
- check_function_size (max 80): clean
- check_comment_history: clean, exit 0 (pre-phase result: clean)
- companion/test_suite_guards.py: 134 passed

## Deviations from Plan

The production guard test was written together with Task 1's tests, so it landed in the first commit; Task 2's commit contains only the pyproject.toml change. `check_function_size.py` needs `--max 80 server stub-server` arguments.

## Known Stubs

None.

## Self-Check: PASSED
