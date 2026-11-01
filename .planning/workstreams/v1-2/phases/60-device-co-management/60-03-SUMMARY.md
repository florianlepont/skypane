---
phase: 60-device-co-management
plan: 03
subsystem: companion-access
tags: [co-management, access-gate, default-deny]
requires: [60-01]
provides:
  - ownership gate admits a co-manager on OWNER_DEVICE routes
  - OWNER_ONLY_DEVICE access kind (owner or admin only)
  - Handler._co_manager_lookup, read per request, fails closed
affects: [60-04, 60-05]
key-files:
  created: [companion/test_co_manager_gate.py]
  modified: [companion/access.py, companion/route_types.py, companion/app.py, companion/test_access.py]
requirements-completed: [AUTH-08]
completed: 2026-11-01
---

# Phase 60 Plan 03: Co-manager ownership gate Summary

The pure gate takes an injected `is_co_manager` callable: a co-manager passes for exactly the frames they co-manage, the new `OWNER_ONLY_DEVICE` kind (`device-owner`) refuses them, and the dispatcher wires a per-request, uncached membership lookup.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Gate accepts a co-manager; owner-only kind | be51e94 | companion/access.py, companion/route_types.py, companion/test_access.py |
| 2 Dispatcher passes the membership lookup | 10bc8e3 | companion/app.py, companion/test_co_manager_gate.py |

## Touches Phase 55 code

This plan touches Phase 55 code:

- `companion/app.py`: the `_dispatch` call to `access.decide` gains the extra argument, and `Handler._co_manager_lookup` sits beside `_owner_lookup`.
- `companion/route_types.py`: new `OWNER_ONLY_DEVICE`, `OWNER_DEVICE` now uses `access.DEVICE_ARG`, comment updated.

`companion/access.py` (Phase 54 code) is edited in a bounded, backward compatible way. `routes.py` is untouched (plan 05 exports the new kind).

## Verification

- `pytest companion/test_access.py companion/test_co_manager_gate.py companion/test_access_matrix.py`: 1050 passed.
- `stub-server/test_phase47_freeze.py`: 21 passed, unedited.
- ruff on the five files, mypy (28 source files), `check_function_size.py check --max 80 server stub-server` (921 functions, none over 80), `check_comment_history.py check`: clean. `access.py` has no sqlite3 or fleet_db import.

## Deviations from Plan

The HTTP tests use the seeded-session helpers (`user_cookie`, `seed_fleet`) with the in-process server, not a fake Auth0 sign-in; the gate only needs a valid session. The missing-table test drops the owner-exclusion trigger on `devices` before the table. No other deviations.

## Known Stubs

None.

## Self-Check: PASSED
