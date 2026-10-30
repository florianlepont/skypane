---
phase: 51-per-device-config-image-and-state
plan: 14
subsystem: fleet
tags: [byos, fleet-db, fail-closed, gap-closure]
requires: [51-04, 51-01]
provides:
  - BYOS fails closed for non-live devices when fleet.db is unavailable
  - single live "." state_path row enforced at the DB helper and CLI
key-files:
  modified:
    - stub-server/byos_server.py
    - server/device_dirs.py
    - server/fleet_db.py
    - server/fleet_migrate.py
    - stub-server/fleet_cli.py
    - test-support/skypane_two_device_fleet.py
    - .planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-OWNER-CHECKS.md
metrics:
  completed: 2026-10-30
---

# Phase 51 Plan 14: Gap closure (BYOS fail-open, second live state path) Summary

Closes verification gaps 1 and 2: a non-live device can no longer be served
the live frame's image or overwrite its battery state when fleet.db is
unavailable, and a second device can no longer be created on the live
frame's state path.

## Gap 1 design

When fleet.db cannot answer (absent, unmigrated, corrupt), `_context_without_fleet_db`:

1. No `devices/` directory (true pre-fleet install, or migrated with only the
   live frame): every authenticated MAC is the live frame. Responses and files
   are exactly as before.
2. `devices/` exists: only a MAC listed in the new root file
   `live_frame_macs.json` (`{"macs": [...]}`) gets the live context. Any other
   MAC, a missing record, or an unreadable record gives 503 "device state
   unavailable". Nothing is written to the live state dir in that case.

Why: no existing file can tell the live MAC from a second frame's. Both are in
`devices.json` and `byos_state.json` (the CLI mirrors every device), and the
legacy migration imports every legacy MAC as a "." row. `devices/` presence is
a reliable signal that per-device rows exist, because `fleet_cli devices add
--state-path auto` is the only path that creates it. That same path now records
the MACs of the "." rows (read from fleet.db, while it is healthy) into the
record BEFORE provisioning the directory, and aborts the add if the record
cannot be written, so per-device state never exists without the record. The
record is a new small root file, expand-only: no existing live file changes, the
previous release ignores it, fleet_migrate is unchanged apart from the opt-in
below. The live frame with a corrupt fleet.db is still served on any install
where the record exists.

Residual: an install that already has `devices/` but no record (only dev
machines, since phase 51 is not deployed) fails closed for every MAC, live
frame included, when fleet.db is unavailable, until fleet.db is healthy or the
record is created by the next `devices add --state-path auto`. The backup
script (deploy/, out of scope here) does not list the record; a restore brings
back fleet.db too, so the record is only needed in the fault case.

Tests: `test_legacy_without_fleet_db_every_mac_is_the_live_frame` became
`test_pre_fleet_install_serves_the_live_frame_unchanged` (no fleet.db, no
`devices/`: live served, no `devices/` created). New: absent and corrupt
fleet.db with a non-live token give 503 and leave the live dir untouched
(battery_state.json unchanged); corrupt fleet.db with the live token is still
served; no record or an unreadable record gives 503 for everyone once
`devices/` exists.

## Gap 2

- `fleet_db.add_device` raises ValueError when a "." row exists and the new row
  also uses "."; `allow_shared_live=True` is set only by `fleet_migrate`, whose
  legacy import of several registered MACs mirrors what the previous release
  already did.
- `fleet_cli devices add` refuses a non-`auto` state path once a live row
  exists (exit 2, message names `--state-path auto`), before touching either
  store.
- `51-OWNER-CHECKS.md` carries a French warning.

## Deviations from Plan

- [Rule 1] The legacy `devices_cli add` mirror (`mirror_to_fleet`) also adds "."
  rows, so on a migrated install it now fails with the existing
  "warning: fleet.db not updated" (exit 1) for a second MAC rather than putting
  it on the live state; that MAC is then 401 while fleet.db is usable. The
  operator uses `fleet_cli devices add --state-path auto`. Test
  `test_devices_cli_mirrors_into_migrated_fleet_db` was adjusted (live row
  removed first) and a new test covers the refusal.
- Existing tests that inserted several default-path devices
  (`test_fleet_db`, `test_fleet_cli`, `test_ota_offer`, `test_ota_fleet_regression`)
  now use `state_path="auto"` for the extra rows. The two-device fixture records
  the live MAC as the CLI does.

## Self-Check: PASSED

Frozen files (test_phase47_freeze.py, test_image_negotiation.py,
measured_fields_freeze.json) and hardware/, firmware/, deploy/ untouched.
FLT-01/FLT-02 not ticked.
