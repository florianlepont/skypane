---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 08
subsystem: fleet-migration
tags: [gap-closure, migration, tokens, devices_cli]
requires: []
provides:
  - "devices_cli remove drops the removed device's token"
  - "fleet_migrate skips and counts orphan tokens"
affects: [stub-server/devices_cli.py, server/fleet_migrate.py]
key-files:
  modified:
    - stub-server/devices_cli.py
    - server/fleet_migrate.py
    - server/test_fleet_migrate.py
    - stub-server/test_devices_registry.py
    - stub-server/test_fleet_auth.py
decisions:
  - "bearer_ok/effective_tokens unchanged; legacy-fallback orphan exposure accepted (revoke-token clears it)"
requirements-completed: [DATA-02]
metrics:
  tasks: 2 of 3 (task 3 is a non-blocking human check)
  completed: 2026-10-29
---

# Phase 48 Plan 08: Orphan token gap closure Summary

`devices_cli remove` now deletes the device's bearer token from byos_state.json, and `fleet_migrate` skips and counts tokens for unregistered MACs instead of aborting, so a leftover token no longer wedges the deploy.

## Tasks

1. Remove drops the token; migration skips orphans (commit 5e025f9). `LegacyState.skipped_tokens` added; `_read_tokens` returns (tokens, skipped) and still validates MAC and token shape for every entry. The report line "skipped N token(s) for unregistered device(s)" appears on the nothing-to-do, dry-run and applied paths via `_with_skipped`; it prints a count only. Tests cover remove with and without a token, orphan skip in dry-run and real runs, idempotent second run, remove-then-migrate, and malformed orphan entries still exiting 2. The old abort test was replaced.
2. Auth proof (second commit, test(48-08)). Three tests against a real byos subprocess: removed token before migration, pre-existing orphan, and remove after migration all return 401 while the live token returns 200. byos_server.py is unchanged.
3. Human checks (real-state dry-run replay, companion Chromium health tests): not run in the sandbox, deferred to phase UAT.

## Deviations from Plan

None. Plan executed as written.

## Verification

`pytest server stub-server deploy/tests`: 1606 passed, 5 environmental skips. ruff, mypy, function-size (max 80) and comment-history checks pass. Companion browser tests were not run.

## Known Stubs

None.

## Self-Check: PASSED
