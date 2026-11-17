---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
plan: 10
subsystem: server
tags: [firmware-registry, fleet, ota, reconcile]
requires: ["64-01"]
provides: ["apply_reconcile_other_types", "type-level reconcile once per run_fleet"]
key-files:
  modified:
    - server/firmware_registry.py
    - server/fleet_cycle.py
    - server/test_firmware_reconcile.py
    - server/test_fleet_cycle.py
requirements-completed: [HW2-03]
completed: 2026-11-14
---

# Phase 64 Plan 10: Type-level firmware reconcile Summary

`run_fleet` now reconciles every available non-legacy hardware type that has a registry file once per run, before the device loops, so a second type's OTA result is recorded even when the live frame's cycle raises PollBusy or fails early.

## Changes
- `firmware_registry.apply_reconcile_other_types(state_dir, now)`: skips the legacy type and types without a registry file, calls `apply_reconcile` per type, logs a failure by type name only and continues.
- `fleet_cycle._reconcile_other_types` called at the start of `run_fleet`, broad except logging the exception class only. `reconcile_firmware=device.is_live` is unchanged.

## Tests (TDD)
RED confirmed (AttributeError on the missing helper) before implementation. New tests: install recorded and legacy bytes identical, idempotent second call; failure records attempts with no installed_at; closed switch and missing file touch nothing; one type raising is logged by type only and others continue; run_fleet records the result when the live runner raises PollBusy; run_fleet survives a reconcile error.

Results: `pytest server stub-server/test_ota_offer.py stub-server/test_phase47_freeze.py` 3653 passed, 3 skipped (root-permission skips); function-size gate, comment-history guard, ruff, mypy clean.

## Deviations from Plan
- Tests enable the second type via the simulation flag (`SKYPANE_SIM_HARDWARE`, sim clone type) rather than `SECOND_ENV_VAR`, since the only registry-capable non-legacy type in tests is simulated. The closed case deletes both flags.
- The helper logs the type key; the fleet wrapper logs the exception class name (same shape as poll_cycle). No error text or device ids are logged.

## Self-Check: PASSED
Commit 2908057 exists; no change under stub-server/ or Phase 47/47.1 files.
