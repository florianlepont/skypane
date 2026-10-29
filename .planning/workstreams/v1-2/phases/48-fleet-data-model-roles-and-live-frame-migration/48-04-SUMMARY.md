---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 04
subsystem: byos device auth
tags: [byos, fleet.db, auth, migration, devices_cli]
requires: [48-02, 48-03]
provides:
  - byos fleet.db identity bridge with legacy fallback
  - dual-written enrolment tokens
  - mirror_to_fleet for the legacy devices_cli
  - reusable byos subprocess harness
affects: [stub-server/byos_server.py, stub-server/devices_cli.py]
key-files:
  created:
    - stub-server/test_fleet_auth.py
    - test-support/skypane_frame_server.py
  modified:
    - stub-server/byos_server.py
    - stub-server/devices_cli.py
    - stub-server/test_ota_offer.py
requirements: [DATA-02, DATA-01]
metrics:
  completed: 2026-10-29
  tasks: 3
---

# Phase 48 Plan 04: byos on fleet.db Summary

byos now authenticates the live frame from a migrated fleet.db, read per request, and falls back to devices.json/byos_state.json whenever fleet.db is absent, unmigrated, corrupt or too new; enrolment tokens are written to both stores.

## What was built

- Bridge in `byos_server.py`: `_fleet_view`, `effective_registry`, `effective_tokens`, `issue_token`, `_enrol`, `_note_fleet_status`, `mirror_to_fleet`. One identity source per call, never a union. Fault is logged once per change (`fleet.db: fault (<ExceptionClass>)`) and recorded in `fleet_status.json`; absent is silent.
- Enrolment writes fleet.db first (transaction); a failed write returns 503 and leaves `byos_state.json` untouched. `devices.json` is not modified.
- `_resolve_device_id` returns None for an unmatched token; `_record_device_report_and_offer` then returns no offer and writes nothing. A legacy `default` bucket is left alone.
- `devices_cli` add/replace/remove/revoke-token mirror into a migrated fleet.db; a failed mirror prints `warning: fleet.db not updated: ...` and exits 1 after the legacy change is applied.
- `test-support/skypane_frame_server.py` harness (start/restart/stop/setup/display/stdout_text); `stub-server/test_fleet_auth.py` covers every behaviour bullet with real subprocesses.

## Verification

`pytest stub-server server/test_fleet_migrate.py` 218 passed, 1 skipped (root permission test); ruff, mypy, function-size and comment-history gates clean. Poll response keys, headers, battery/poll state and sleep_s composition untouched (key-set equality test).

## Deviations from Plan

1. **[Rule 1 - test expectation]** The plan asked for a pre-existing `default` bucket to be byte-identical after a valid-token poll. `firmware_registry.load_device_report` fills default fields (`fw_version`, `reported_at`) on any rewrite, which is existing behaviour, so the tests assert the bucket gains no event or version and keeps its events (and, in `test_ota_offer.py`, is equal to its legacy content when already normalised).
2. Tasks 1-3 were committed together in one commit (0e3988a): the bridge, default removal and `mirror_to_fleet` all live in `byos_server.py`, which could not be split without interactive staging.

## Known Stubs

None.

## Self-Check: PASSED

Files exist (`test_fleet_auth.py`, `skypane_frame_server.py`); commit 0e3988a present.
