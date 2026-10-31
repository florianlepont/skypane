---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 05
subsystem: fleet-ops
tags: [pairing, claim, transaction, audit, reassign, retire]
requires: [55-02, 55-03]
provides:
  - server/fleet_ops.py (register_frame, claim_pairing_code, record_claim_failure, reassign_frame, retire_frame, reactivate_frame, pairing_dir, ClaimResult, BusyGuard, exceptions, FAIL_INVALID/FAIL_THROTTLED, ACTION_* keys)
affects: [55-07, 55-09, 55-10]
tech-stack:
  added: []
  patterns:
    - single BEGIN IMMEDIATE claim; directory provisioned inside the transaction and removed on any exception
    - denied and failed audit rows written in their own short transaction
    - poll lock injected as busy_guard (context manager yielding False when busy)
key-files:
  created:
    - server/fleet_ops.py
    - server/test_fleet_ops.py
  modified:
    - pyproject.toml
key-decisions:
  - "Retire does not take busy_guard (it wipes nothing); reassign and re-activate do."
  - "Re-activate skips the wipe when previous_state_path is missing or '.', never touching the live root."
  - "Claim records live-frame MACs (live_frame_macs.json) before the first devices/ directory, as cmd_devices_add does."
requirements-completed: [AUTH-04, AUTH-05]
duration: ~35min
completed: 2026-10-31
---

# Phase 55 Plan 05: Frame operations Summary

`server/fleet_ops.py` holds the atomic pairing claim (one BEGIN IMMEDIATE transaction, identical `ClaimRefused` for wrong, expired, used and malformed codes after the same constant-time scan, guess never audited) and the register, reassign, retire and re-activate operations with the live-frame guard, wipe-inside-transaction rollback and an injectable poll guard.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | d21c53b | Whole `fleet_ops.py` (all five operations), Task 1 tests (14), mypy file and strict-override entries |
| 2 | 6c24740 | Task 2 tests (10): reassign, live-frame snapshot, retire, re-activate, busy guard, rollback, owner check |

## Verification

- `pytest server stub-server/test_phase47_freeze.py`: 1720 passed, 3 skipped (root-only permission skips).
- `pytest server/test_fleet_ops.py`: 24 passed; the two-thread claim race passed 5 of 5 repeated runs.
- ruff, mypy (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (796 functions): clean.

## Deviations from Plan

- The implementation of Task 2's three operations was written together with Task 1's module, so commit d21c53b contains the whole module and 6c24740 only the Task 2 tests (the tests passed against the code at that point). Not split further to avoid an artificial commit.
- [Rule 2] `claim_pairing_code` calls `device_dirs.record_live_macs` before provisioning, copying `cmd_devices_add`, so a corrupt fleet.db cannot leave per-device state without the live-frame record.

## Notes for the owner

- A crash after the wipe but before COMMIT rolls the database back while old-owner files are already gone; this was the accepted trade-off (the reverse order would leak data).
- `record_claim_failure` is called by the handler (plan 09 adds the throttle); `claim_pairing_code` itself raises and does not audit failures, so the guess never reaches this layer's audit.

## Known Stubs

None.

## Self-Check: PASSED

server/fleet_ops.py, server/test_fleet_ops.py present; commits d21c53b and 6c24740 exist.
