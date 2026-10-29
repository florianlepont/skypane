---
phase: 49-per-hardware-ota-registry
plan: 03
subsystem: ota
tags: [firmware, registry, per-type, reconcile]
requires: []
provides:
  - per-type registry_path/load_registry/_save_registry, schedule_release, cancel_schedule, publish_release, apply_reconcile (trailing hardware_type=LEGACY_KEY)
  - build_number, UNRESOLVED_TYPE, apply_reconcile_all, relevant_types
  - test-support/skypane_legacy_registry (legacy_shaped_registry, write_legacy_registry)
affects: [49-04 and later registry consumers, byos type stamp, poll_cycle]
tech-stack:
  added: []
  patterns: [default-argument additive change, validate key before path, read-time field defaults]
key-files:
  created:
    - test-support/skypane_legacy_registry.py
  modified:
    - server/firmware_registry.py
    - server/test_firmware_registry.py
    - server/test_firmware_reconcile.py
decisions:
  - "The legacy document is written without hardware_type or build on release entries and without a top-level hardware_type, so registry.json keeps its original shape; other types store the full entries"
  - "registry_path validates against hardware.available_types (shape regex first), so a simulated key with the gate off is rejected as unknown"
  - "apply_reconcile_all returns the concatenated outcomes, legacy first; legacy always runs, other types only when their document exists"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-01, OTA-02]
---

# Phase 49 Plan 03: Per-hardware registry documents Summary

Per-hardware-type registry documents (registry.json for the legacy type, registry.<key>.json otherwise) behind the one existing lock, with read-time hardware_type and build on releases, a write-once registry.json.pre-fleet copy, and reconcile/update_view scoped to the document's type.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 and 2 implementation, plus per-type, legacy-shape, pre-fleet, reconcile and view tests | b20ff243 | Both tasks touch the same module, so the implementation landed in one commit |
| 2 (apply_reconcile_all cycle-level test) | 9482f92c | test_firmware_reconcile.py |

## Deviations from Plan

- Tasks 1 and 2 were not committed separately for the implementation: the type-scoped reconcile/view changes and the per-type storage live in one file and were written together. The tests were written alongside the code rather than as a separate failing-first commit, so there is no RED commit for this plan.
- publish_release also gained a trailing hardware_type parameter (not listed in the plan interfaces) so a type's releases can be published into its own document.

## Verification run

- Existing registry, cli, reconcile, offer and manifest tests (207) passed unmodified before and after the change.
- `pytest server stub-server deploy/tests test-support -n auto --no-cov`: 1863 passed, 5 skipped (root-permission and openssl skips).
- ruff check (server, test-support, stub-server): clean. mypy: no issues in 16 source files. check_function_size (max 80): 568 functions, none over. check_comment_history: exit 0.
- The coverage-gated `scripts/run-all-tests.sh` was not run.

## Known Stubs

None.

## Self-Check: PASSED

Files and commits b20ff243, 9482f92c exist.
