---
phase: 60-device-co-management
plan: 02
subsystem: fleet-db
tags: [co-management, audit, cascades, locations]
requires: [60-01]
provides:
  - reassign, retire, hard delete and mirror delete are co-manager safe and audited per user
  - location assignment is relative to the device owner
affects: [60-03, 60-04, 60-05]
key-files:
  created: [server/test_fleet_co_manager_cascades.py]
  modified: [server/fleet_db.py, server/fleet_ops.py]
requirements-completed: [AUTH-08]
completed: 2026-11-01
---

# Phase 60 Plan 02: Co-manager cascades and location rule Summary

Reassign, retire, hard delete and the legacy-registry mirror now clear co-manager rows in the same transaction and audit one `device.co_manager_remove` row per user; a co-manager may assign only the device owner's location.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Cascades with per-user audit | e9692b2 | server/fleet_db.py, server/fleet_ops.py, server/test_fleet_co_manager_cascades.py |
| 2 Location rule against the device owner | f9f5821 | server/fleet_db.py, server/test_fleet_co_manager_cascades.py |

## Touches Phase 55 code

- `server/fleet_ops.py::reassign_frame`: inside the transaction, after the second owner check and before either UPDATE, deletes the new owner's membership row and audits one removal (via "reassign") when a row existed.
- `server/fleet_ops.py::retire_frame`: reads co-manager ids before `park_retired`, then audits one removal per user (via "retire") before the existing retire audit row, all in the same transaction.
- `server/fleet_db.py::park_retired`: calls `clear_co_managers` immediately before `DELETE FROM devices`; signature and return value unchanged.
- `server/fleet_db.py::remove_device`: new optional `actor` keyword; inside one atomic block it looks up the device by MAC, clears and audits co-managers (via "delete", actor system by default), then runs the original DELETE and returns the same boolean.

Also changed (not in the original list): `set_device_location_checked` (permission block and docstring), plus new helper `audit_co_manager_removals` and re-exported `ACTION_CO_MANAGER_ADD/REMOVE` in `fleet_ops`.

## Visible consequence (D-03)

A non-live reassign wipes the previous owner's data, location and name but keeps the other co-managers, so they now manage the new owner's fresh frame.

## Verification

- `pytest server stub-server companion/test_console_locations.py -n auto`: 2744 passed, 4 skipped (root-permission skips).
- ruff on `server/`, mypy `server/fleet_db.py server/fleet_ops.py`, `check_function_size.py` (921 functions, none over 80), `check_comment_history.py check`: clean.
- `stub-server/test_phase47_freeze.py` green and unedited; `git diff` empty for `stub-server/`, `hardware/`, `firmware/`.

## Deviations from Plan

**1. Ownerless-location test**: the plan's behaviour list said an owner can still link an ownerless location "as before". The original code refused it for non-admins (location owner None differs from the actor), so the new rule keeps that refusal and the test asserts PermissionError. Behaviour for owners and admins is unchanged.

No other deviations. No fix attempts exceeded.

## Known Stubs

None.

## Self-Check: PASSED
