---
phase: 51-per-device-config-image-and-state
plan: 01
subsystem: fleet
tags: [fleet, device-dirs, state-path, test-fixture]
requires: []
provides:
  - server/device_dirs.py (single validated state_path to directory chokepoint)
  - fleet_db.add_device state_path validation
  - fleet_cli devices add --state-path auto
  - test-support/skypane_two_device_fleet.py
affects: [51-02 onward]
key-files:
  created:
    - server/device_dirs.py
    - server/test_device_dirs.py
    - test-support/skypane_two_device_fleet.py
    - .planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-BASE-REF.txt
  modified:
    - pyproject.toml
    - server/fleet_db.py
    - server/test_fleet_db.py
    - stub-server/fleet_cli.py
    - stub-server/test_fleet_cli.py
    - test-support/test_test_support.py
metrics:
  completed: 2026-10-30
---

# Phase 51 Plan 01: Device directories and two-device fixture Summary

`server/device_dirs.py` is now the only code that turns a fleet.db `state_path` ("." or `devices/d_xxxxxxxx`) into a directory, with regex shape check, realpath containment and symlink refusal; `add_device` only stores "." or the row's own generated id; the CLI can provision a device directory; one call builds the live frame plus two simulated devices.

Base ref (commit preceding all Phase 51 code changes): `17b6564b67034250654caec51fb6cc846a22ad9f`

## Commits

- 8dcd5be: record Phase 51 base ref
- e601061: device_dirs module, tests, mypy strict registration
- 736eb60: add_device state_path validation, `devices add --state-path auto`
- dacfea5: two-device fleet fixture and tests

## Verification

- pytest (device_dirs, fleet_db, fleet_cli, test_test_support, phase47 freeze, image negotiation): 157 passed
- mypy: no issues (18 files, device_dirs included in strict set); ruff check .: clean
- check_comment_history: clean; check_function_size --max 80: 612 functions, none over
- test_phase47_freeze.py untouched.

## Deviations from Plan

**1. [Rule 1 - Bug] CLI rollback also removes the directory.** A DB transaction rollback cannot undo the provisioned directory (also hit when the legacy write fails with "already registered"), so `cmd_devices_add` removes the newly created device directory on any failure. Test added.

**2. Live-frame untouched assertion excludes the legacy registries.** The plan requires the legacy dual write, which by design rewrites the live root's `devices.json` and `byos_state.json`. The test therefore asserts every other live root file is byte-identical, excluding those two plus fleet.db and `devices/`.

**3. device_headers carries Authorization plus the poll headers only.** The BYOS reads no ID header, so none is sent.

## Known Stubs

None.

## Notes

FLT-01 not marked complete: it is only partly delivered by this plan (later plans serve images and state per device). STATE.md and ROADMAP.md not edited, as the plan did not call for it.

## Self-Check: PASSED

Files and commits 8dcd5be, e601061, 736eb60, dacfea5 verified present.
