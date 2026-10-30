---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 01
subsystem: auth
tags: [sqlite, sessions, auth0, migration]
requires: []
provides:
  - fleet.db schema v2 (sessions table, hash-only ids)
  - race-free migrate_schema and fleet_migrate pending-schema upgrade
  - server/fleet_sessions.py (sessions, invite-only identity linking)
  - fleet_db.get_device_owner
  - fleet_cli users unlink-identity
affects: [phase-54 later plans]
tech-stack:
  added: []
  patterns: [expand-only migrations, fresh role/disabled read per lookup]
key-files:
  created: [server/fleet_sessions.py, server/test_fleet_sessions.py]
  modified: [server/fleet_db.py, server/fleet_migrate.py, stub-server/fleet_cli.py, pyproject.toml, server/test_fleet_db.py, server/test_fleet_migrate.py, stub-server/test_fleet_cli.py]
key-decisions:
  - "unlink_identity opens its own transaction; delete_sessions_for_user joins the caller's"
  - "A disabled user's session row is kept (lookup refuses it); the CLI disable deletes it"
requirements-completed: [AUTH-01, AUTH-02, AUTH-06]
duration: 25min
completed: 2026-10-30
---

# Phase 54 Plan 01: Sessions foundation Summary

fleet.db schema v2 with a hash-only `sessions` table, a race-free upgrade path (connect and deploy-time fleet_migrate), and a typed `fleet_sessions` module doing session lifetime checks and invite-only identity linking.

## Tasks
1. Schema v2 + migration fixes: commit 17d16cb
2. fleet_sessions module: commit 5e466ee
3. fleet_cli unlink-identity and disable drops sessions: commit c0e09e0

## Deviations from Plan
None - plan executed as written. `resolve_login` accepts `now` per the plan but does not use it.

## Verification
pytest for touched modules, freeze, fleet_auth and backup tests pass; mypy, ruff, function-size and comment-history gates pass. byos_server.py, firmware and measured_fields_freeze.json untouched.

## Known Stubs
None.

## Self-Check: PASSED
