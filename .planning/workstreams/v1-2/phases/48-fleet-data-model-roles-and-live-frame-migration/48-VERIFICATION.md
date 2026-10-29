---
phase: 48-fleet-data-model-roles-and-live-frame-migration
verified: 2026-10-29T00:00:00Z
status: gaps_found
score: 3/4 roadmap truths verified (SC1 and SC2 partial on CR-01)
gaps:
  - truth: "Migration of the live state is safe and re-runnable (SC1/SC2: no observable change, previous release keeps working, deploy path not wedged)"
    status: partial
    reason: "CR-01 confirmed. devices_cli remove deletes the registry entry but leaves the token in byos_state.json. fleet_migrate._read_tokens then raises on the orphan token, so dry-run and real run exit 2 and activate.sh refuses to swap. In the legacy fallback the orphan token still passes bearer_ok."
    artifacts:
      - path: "stub-server/devices_cli.py"
        issue: "cmd_remove (lines 65-77) never removes state['tokens'][mac]"
      - path: "server/fleet_migrate.py"
        issue: "_read_tokens (line 140-141) aborts on a token for an unregistered MAC instead of skipping it"
    missing:
      - "cmd_remove drops the token (as fleet_cli._mirror_remove does)"
      - "_read_tokens skips and counts orphan tokens instead of raising"
      - "regression test: remove a device, then migrate dry-run and real run succeed"
---

# Phase 48 Verification

**Goal:** Owner can record users, devices, hardware types and locations in one fleet database; the live frame is migrated with no observable change.
**Status:** gaps_found. Re-verification: No.

## Requirement accounting

All five IDs appear in PLAN frontmatter and REQUIREMENTS.md; none are orphaned.
DATA-04: plan 01. DATA-01 and DATA-03: plans 02, 03. DATA-02: plans 03, 04, 05, 06, 07. DATA-05: plans 05, 06.

## Observable truths

| # | Roadmap success criterion | Status | Evidence |
|---|---|---|---|
| 1 | Same image hash and wake interval after migration, credentials kept | VERIFIED for the normal path, with a caveat | test_phase47_freeze.py replay tests (identical response, kept credentials, sleep_s) pass. The replay uses a synthetic fixture, not the real prod state (disclosed). |
| 2 | Previous release still runs on the migrated state; re-run changes nothing | PARTIAL | Migration is expand-only and idempotent (tests pass). CR-01 breaks it when the legacy state holds an orphan token. |
| 3 | Users with role admin or user, one owner per device, hardware profiles including simulated, role stored locally | VERIFIED | `users.role` has CHECK IN ('admin','user') in server/fleet_db.py. Role is read through get_user_role. Hardware gate and simulated types are covered in test_fleet_cli and test_fleet_auth. |
| 4 | fleet.db in backup with tested restore; freeze test on Phase 47 fields | VERIFIED | The backup module snapshots fleet.db through the online backup API (test_backup). The freeze test is in test_phase47_freeze.py. |

## CR-01 independent check: real

I reproduced it in a scratch state dir. The dir held two devices and two tokens. I ran `devices_cli remove --mac ...02`, which printed "removed" but left `byos_state.json` unchanged, token t2 included. Both `fleet_migrate --dry-run` and the real run then printed "error: byos_state.json has a token for unregistered device ..." and exited 2.

Weighing:
- In fleet mode the DB is authoritative and the DB-side remove deletes the token. The leak into authentication happens only on the legacy fallback path. The token was already left behind by the pre-phase CLI, so this is not a new regression.
- The migration abort is new and is Phase 48's own. It fails safe: nothing is swapped and the live frame keeps polling on the old release. It still wedges every deploy until someone hand-edits `byos_state.json`.
- The live frame is unaffected. If the production `byos_state.json` has an orphan token from an earlier removal, the migration, which is the point of the phase, cannot complete. I could not inspect production state. Treat this as a blocker before the production deploy.
- The fix is small, and the review's proposed patch is adequate.

## Tests run

`server/.venv/bin/python3 -m pytest server stub-server deploy/tests companion/test_health*.py -n 4 --no-cov`: 1684 passed, 5 skipped. The skips are environmental (root euid, openssl). No failures. No test covers the CR-01 sequence.

## Warnings (non-blocking, from the review, not individually re-verified)

- WR-01: the dry-run does not exercise the apply path.
- WR-02 and WR-03: token write ordering between fleet.db and the legacy file, and stale in-memory state in byos.
- WR-04: an empty new fleet.db reports as a fault.
- WR-05: the pre-deploy backup shares the retention pool with nightly archives, and a corrupt fleet.db blocks deploy.
- WR-06: archive file mode depends on umask while fleet.db holds plaintext tokens.
- WR-07: an existing non-admin or disabled bootstrap owner is accepted.

## Human verification required

1. Run the migration dry-run against a copy of the real production state (D-04 real-state replay). Expected: exit 0, and the frame's next poll returns the same hash and `sleep_s`. This also shows whether production holds orphan tokens.
2. Run the companion Chromium browser tests (the Health fleet-fallback signal) in an environment with a browser. They could not run in the sandbox.

## Gaps summary

One gap: CR-01. The core deliverables (schema, roles, hardware profiles, migration, auth bridge, backup and restore, freeze test) exist, are wired and pass tests. Fix CR-01, add the regression test, and run the two human checks. The warnings are worth scheduling.
