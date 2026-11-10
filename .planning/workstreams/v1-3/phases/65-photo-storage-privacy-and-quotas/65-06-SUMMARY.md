---
phase: 65-photo-storage-privacy-and-quotas
plan: 06
subsystem: auth
tags: [companion, access, route-matrix, photos, privacy]
requires: []
provides:
  - MANAGER_DEVICE route access kind (owner and co-manager only, no admin shortcut)
  - allow_admin flag on access.authorized_device_id
  - route-matrix vocabulary and guard for photo routes
affects: [67]
tech-stack:
  added: []
  patterns: [access flag derived from the route kind inside decide]
key-files:
  created: []
  modified:
    - companion/access.py
    - companion/route_types.py
    - companion/routes.py
    - companion/test_access.py
    - companion/test_access_matrix.py
key-decisions:
  - "decide derives allow_admin from the kind (device_arg != DEVICE_MANAGER_ARG), so a route cannot opt in by accident"
  - "Matrix policy name is manager-device; the matrix admin owns and co-manages nothing, so its expected outcome is not-found"
requirements-completed: [PRIV-01]
duration: 15min
completed: 2026-11-10
---

# Phase 65 Plan 06: Manager-only route access kind Summary

`MANAGER_DEVICE` gives future photo routes a route-level wall that refuses a pure admin (same NOT_FOUND as an unknown path), and the route matrix now fails any route containing "photo" that is not on that kind.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1. Access kind in the pure layer | 2961022 | `DEVICE_MANAGER_ARG`, `allow_admin=True` keyword on `authorized_device_id`, `decide` passes `allow_admin = device_arg != DEVICE_MANAGER_ARG`; `MANAGER_DEVICE` in `route_types` (and re-exported from `routes`); 8 new pure tests |
| 2. Matrix vocabulary and guard | deae506 | `MANAGER_DEVICE` policy in the outcome, role-requirement and prefix-parity tables; `test_every_photo_route_is_manager_only` (vacuous today), a bite test with dummy `/photos` routes on OWNER_DEVICE and ADMIN_DEVICE removed by monkeypatch teardown, a manager-route-never-public guard, and a per-principal check of the policy row against `decide` |

## Deviations from Plan

**1. [Rule 3 - Blocking] Re-export in companion/routes.py.** The plan lists four files; `companion/routes.py` re-exports every `route_types` name and the matrix reaches kinds through `routes`, so one line `MANAGER_DEVICE = route_types.MANAGER_DEVICE` was added there. No other change.

Tests were written alongside the implementation in each task rather than as a separate failing commit first.

## Verification

- `pytest companion/test_access_matrix.py companion/test_access.py --no-cov -q -n auto`: 1939 passed (includes the existing route/ownership matrix cells, unchanged).
- `ruff check companion`: clean. `mypy`: no issues in 50 source files. `check_comment_history.py check`: clean.

## Hand-off to Phase 67

Every photo route must be declared with `MANAGER_DEVICE` and get its `ROUTE_POLICY` rows using the `manager-device` policy name (the outcome, role and prefix-parity tables already know it). The request body size cap must apply while reading the body, not after.

## Known Stubs

None.

## Threat Flags

None. T-65-06 to T-65-08 mitigated: admins refused through `decide` (tested through decide, not only the helper), foreign, unknown and malformed ids all give NOT_FOUND, and the flag is derived from the kind.

## Self-Check: PASSED
