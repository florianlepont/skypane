---
phase: 49-per-hardware-ota-registry
plan: 11
subsystem: ota
tags: [regression, end-to-end, live-frame, phase-gate]
requires: [49-06, 49-07, 49-08, 49-09]
provides:
  - stub-server/test_ota_fleet_regression.py (11 tests)
key-files:
  created:
    - stub-server/test_ota_fleet_regression.py
decisions:
  - "Polls are driven through byos_server._record_device_report_and_offer in process (the same entry the HTTP handler calls); /fw serving of a legacy-shaped registry is checked against a real byos subprocess"
metrics:
  tasks: 2
  completed: 2026-10-30
requirements: [OTA-01, OTA-02]
---

# Phase 49 Plan 11: End-to-end and live-frame regression Summary

One regression module proves the legacy-shaped registry still behaves as before and that two simulated hardware types publish, schedule, poll and reconcile independently. No production code changed and no earlier-plan defect was found.

## Task 1: tests (commit 2cced874)

- Legacy-shaped registry (no hardware_type, no build; fw-v1.0.0, 1.0.1, 1.0.2): load, rollback schedule (1.0.2 to 1.0.1), exact offer dict, no offer when the frame already runs the target, update_view fields, and /fw/<sha>.bin served by a real byos subprocess, all with explicit expected values.
- registry.json.pre-fleet: created on the first rewrite, byte-equal to the original, unchanged after schedule, cancel, reconcile and import-dir; the legacy file on disk carries no per-release hardware_type or build.
- Live-frame report entry: keys are exactly fw_version, reported_at, events (+ the added hardware_type = legacy).
- Two simulated types through firmware_cli import-dir (tags written out of order, imported in build order, fw-v1.10.0 after fw-v1.2.0): independent schedules, each frame offered only its own type's release, legacy frame offered nothing, offered schedule not cancellable per type, reconcile of a type's installed event moves only that type (legacy and other type bytes unchanged).
- Refusals through the CLI path (non-zero exit, firmware dir byte-identical afterwards): lower build, wrong chip id, wrong project_name, manifest type differing from file name. Re-running import-dir is idempotent. /fw membership covers both types.
- Corrupt fleet.db: the legacy (devices.json) frame still gets its offer; a fleet-only frame gets none and is stamped unresolved.

## Task 2: phase gate run (all executed in this session, after the Task 1 commit)

Environment: Python 3.13.17 in server/.venv (the shipped target is 3.14), running as root.

| Gate | Result |
|------|--------|
| pytest server stub-server deploy/tests test-support companion -n auto --no-cov, SKYPANE_REQUIRE_BROWSER=1 and the scratchpad Playwright browsers | 4608 passed, 8 skipped |
| ./scripts/run-all-tests.sh (coverage-gated, full suite incl. browser tests) | exit 0, 4752 passed, 8 skipped; coverage 95.59% against the 93.0% requirement |
| ruff check . | All checks passed |
| mypy | no issues in 16 source files |
| check_function_size.py check --max 80 server stub-server | 599 functions, none over |
| check_comment_history.py check | exit 0 |
| sh firmware/tests/run_host_tests.sh | 13 suites passed |
| sh firmware/tests/check_production_config.sh static | PASS |

The 8 skips are environment limits: root ignores permission bits (7) and local openssl cannot backdate a certificate (1). The earlier "207 baseline" subset is part of the full runs above; it was not run as a separate count.

## OTA-03 device-side verification is DEFERRED

Success criterion 3 (a running device accepts a correctly signed image and rejects a wrongly signed one with fail-image) was not verified: no bench unit exists (see 49-10-SUMMARY and firmware/SIGNING.md). OTA-03 stays open; requirements.mark-complete was not run. Nothing in this plan exercises a device.

## Production deploy

Nothing was deployed, tagged or triggered. Phase 47 still gates any production deploy. Operator step before the first deploy of this phase: run `firmware_cli list` on the VPS (with the VPS state directory) and confirm the three legacy releases and their schedule are listed as before; the first legacy rewrite will create registry.json.pre-fleet there.

## Deviations from Plan

None. The plan's "207-test baseline subset" was covered by the full suite rather than counted separately.

## Known Stubs

None.

## Self-Check: PASSED

Commit 2cced874 and stub-server/test_ota_fleet_regression.py exist.
