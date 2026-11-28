---
phase: 67-project-and-code-optimisation
plan: 19
subsystem: device-server-identity
tags: [byos, fleet-db, identity, retirement, quarantine]
requires: ["67-18"]
provides: ["device server reads identity from fleet.db only", "server/retire_legacy_state.py", "fleet_cli devices replace-secret", "test-support/skypane_fleet_identity.py"]
affects: ["stub-server/byos_server.py", "stub-server/fleet_cli.py", "test-support/skypane_live_state.py"]
key-files:
  created: [server/retire_legacy_state.py, server/test_retire_legacy_state.py, stub-server/test_byos_fleet_only.py, test-support/skypane_fleet_identity.py]
  modified: [stub-server/byos_server.py, stub-server/fleet_cli.py, test-support/skypane_live_state.py, test-support/skypane_two_device_fleet.py, deploy/backup/skypane_backup.py, firmware/provision.sh, stub-server/README.md, deploy/skypane.env.example, deploy/skypane-byos.service, pyproject.toml]
  deleted: [stub-server/devices_cli.py]
metrics:
  tasks: 3
  completed: 2026-11-28
---

# Phase 67 Plan 19: Retire the identity mirror (G1) Summary

The device server now takes MAC, secret hash and token from fleet.db only and fails closed when fleet.db cannot answer. The legacy files `devices.json` and `byos_state.json` are neither read nor written by the release; an owner-run CLI quarantines them. Gate: G1 and G6 APPROVED in 67-RETIREMENT-GATE.md (owner, 2026-11-28, production check SAFE).

## Commits (branch worktree-agent-67-19, pushed as phase-67-19-retire-identity-mirror)

- 656d5582 test: characterisation tests (registered, pending, live, unknown frames; enrol, authenticate, fleet status) with identity in fleet.db only. Green on the unmodified server, and still green after.
- a2854fff test: the shared seeder `seed_live_like_state` also imports the legacy files into a migrated fleet.db (same `fleet_migrate` import); `migrated=False` keeps the pre-import state. New helper `skypane_fleet_identity.register_device`.
- 2fc66f98 feat: fleet-only device server, `devices_cli.py` removed, `fleet_cli` legacy writes removed, provisioning texts, tests rewritten.
- 54bf7749 feat: `server/retire_legacy_state.py`, backup allow-list, tests.

## Exact behaviour change

Before: `effective_registry`/`effective_tokens` used the fleet.db view when it was migrated and readable, otherwise fell back to `devices.json`/`byos_state.json`. Enrolment also wrote the token to `byos_state.json` (dual write). `resolve_hardware_type` resolved a legacy-registry MAC to the legacy type while fleet.db was unavailable.

After:
- fleet.db absent, unmigrated (no marker), corrupt, unreadable or too new: registry and tokens are empty. Setup answers 403 `device not registered` (the status an unregistered MAC already got), display answers 401 `unknown token`, `/device/v1/log` answers 401. Never 200, never allow-all. `fleet_status.json` and the one-line `fleet.db: fault (<ExceptionName>)` log are unchanged. No secret or token appears in the log (tested).
- Enrolment writes the token to fleet.db only (registered frame row, else pending/retired row; 503 `enrolment unavailable` on a failed write, unchanged). No legacy file is created or touched.
- `resolve_hardware_type` returns None while fleet.db is unavailable (no firmware offer), instead of the legacy type; only reachable after authentication, so a race at most.
- Unchanged: `_authenticate_device` (hmac.compare_digest loop, no early exit), `secret_matches`, `normalize_mac`, `_MAC_RE`, `_note_fleet_status`, every access rule, the live-frame and `live_frame_macs.json` handling (`_context_without_fleet_db` kept; it is only reachable through a race now), wake cadence, battery telemetry and poll-state fields.
- Removed from `byos_server.py`: `state_path`, `load_state`, `save_state`, `REGISTRY_FILE`, `registry_path`, `load_registry`, `save_registry`, `register_device`, `mirror_to_fleet`, `_apply_mirror`, `Handler.state`, and the `state`/`legacy_state` parameters of `_enrol`, `_authenticate_device`, `_device_context`, `_record_device_report_and_offer`, `issue_token`, `effective_tokens`.
- `devices_cli.py` is deleted. Everything it did exists in `fleet_cli.py` (list, remove, revoke-token) except replacing a secret hash, which is now `fleet_cli devices replace-secret --mac M --secret-sha256 H` (registered frames only; a pending frame is told to remove then register-pending). `fleet_cli` writes fleet.db only and no longer prints the restart caution (the server re-reads fleet.db on every request).
- `fleet_migrate` is untouched: its expand-only import of the legacy files stays as a tool and `server/test_fleet_migrate.py` is green.

## Quarantine CLI (owner-run)

`python3 -m server.retire_legacy_state --state-dir DIR [--apply]` (run from a release directory like `fleet_migrate`).
- Dry run by default: prints which legacy files exist, counts (legacy devices/tokens, devices fleet.db lacks, values that differ) and what it would do. A read-only open of fleet.db may create SQLite's own -wal/-shm files; nothing else changes.
- `--apply` renames the files (mode kept) into `retired-legacy/<UTC date>/`; never deletes, never overwrites (a pre-existing target refuses before anything moves). Idempotent: with no legacy file left it prints `nothing to do`.
- Refuses with exit 2 unless fleet.db is migrated and readable, the legacy files parse (`fleet_migrate.read_legacy`) and `plan_migration` shows no `add_device` action (every legacy device is in fleet.db). Output names files and counts only (grep for the seeded MAC, secret, hash and token is empty in the tests).
- Design decision: a legacy secret or token that differs from fleet.db is reported but does not block. Since this release only fleet.db is written, a difference means fleet.db is newer (re-enrolment, `replace-secret`, `revoke-token`); blocking on it would make the quarantine impossible after the first re-enrolment.
- Backup: `retired-legacy` is added to `INCLUDE_DIRS`; `devices.json` and `byos_state.json` stay in `INCLUDE_FILES`. The drift guard needed no classification change beyond that; a new test proves the nested quarantine files reach the archive with no drift line. The CLI is in the mypy module list.

## Provisioning texts (rule 3)

How a frame really gets into fleet.db (from `server/fleet_ops.register_frame`, `fleet_cli`, `byos_server._enrol`, deploy/README "Pairing, retiring and re-activating a frame"): `provision.sh` prints the MAC and the SHA-256 of the secret; the operator runs `fleet_cli.py devices register-pending --mac M --secret-sha256 H` on the VPS (the SHA-256 is still passed, only the hash is accepted); the frame enrols with its secret (setup works for pending frames), shows a pairing code, and the owner pairs it in the console. On a local stub server the state directory first needs `python3 -m server.fleet_migrate --state-dir D --owner-email E` (it creates the owner and the migrated marker; `fleet_cli` never marks migrated), then `fleet_cli devices add ... --owner-email E`. Re-provisioning generates a new secret: registered frame `devices replace-secret`, pending frame `devices remove` then `register-pending`. Updated: `firmware/provision.sh` (final block and header comment), `stub-server/README.md` ("Enrol a device"), `deploy/skypane.env.example`, the comment in `deploy/skypane-byos.service`. `bash -n firmware/provision.sh` and `firmware/tests/check_provision_guard.sh` pass.

For plan 23 (not edited here): `deploy/README.md` lines about 244 to 281 ("Device enrolment (per-device secret)": registry file `devices.json`, steps 2 to 4 with `devices_cli.py`), 302 to 305 ("Expand only", legacy files stay valid and rollback works), 324 to 326 ("`devices_cli.py` still works and mirrors"), and about 940 (the retirement runbook text on `devices.json`/`byos_state.json`); `ARCHITECTURE.md` lines about 316, 761, 822, 882 to 886 and 914. `stub-server/VENDOR.md` lines 23, 28 and 360 to 378 describe the historical changes against upstream and still name `devices_cli.py`.

## Test accounting

Collected ids: 17683 before, 17687 after (40 removed, 44 added). `MIN_EXECUTED` (17591) is left as it is: the count did not drop below it.

Removed (exercised only retired code; each with its reason):
- stub-server/test_byos_hardening.py::test_save_registry_leaves_devices_json_mode_0600 (save_registry removed)
- stub-server/test_byos_hardening.py::test_save_state_and_save_battery_state_leave_no_temp_and_valid_json (replaced by test_save_battery_state_leaves_no_temp_and_valid_json: battery half kept)
- stub-server/test_byos_hardening.py::test_save_state_concurrent_threads_no_exception (save_state removed)
- stub-server/test_device_fleet.py::test_corrupt_fleet_db_still_serves_the_live_frame (live frame no longer authenticates without fleet.db)
- stub-server/test_device_fleet.py::test_unavailable_fleet_db_refuses_a_non_live_device[_corrupt_fleet_db] and [_remove_fleet_db] (replaced by test_unavailable_fleet_db_refuses_every_device[...]: now 401 for every device)
- stub-server/test_device_fleet.py::test_unavailable_fleet_db_with_an_unreadable_live_record_refuses_everyone and test_unavailable_fleet_db_without_the_live_record_refuses_everyone (they reached the live-record path through the legacy fallback; covered by the new refuses-every-device test)
- stub-server/test_devices_registry.py::test_corrupt_registry_file_refuses_every_enrolment, test_missing_registry_file_refuses_every_enrolment, test_devices_json_never_contains_the_plaintext_secret (kept in meaning as test_corrupt_fleet_db_..., test_missing_fleet_db_..., test_fleet_db_never_contains_the_plaintext_secret), test_non_dict_registry_file_refuses_every_enrolment (devices.json shape; replaced by test_unmigrated_fleet_db_refuses_every_enrolment)
- stub-server/test_devices_registry.py::test_devices_cli_add_list_remove_round_trip, ..._add_over_existing_mac_without_replace_exits_nonzero, ..._add_rejects_a_malformed_mac_or_non_hex_hash, ..._remove_drops_only_that_macs_token, ..._remove_without_a_token_leaves_the_state_file_untouched, ..._revoke_token_removes_only_that_macs_token (devices_cli removed; fleet_cli equivalents already tested in test_fleet_cli.py)
- stub-server/test_fleet_auth.py::test_corrupt_fleet_db_falls_back_and_logs_once (now test_corrupt_fleet_db_fails_closed_and_logs_once), test_fleet_db_without_marker_is_ignored (now test_fleet_db_without_marker_refuses), test_too_new_fleet_db_is_fault_and_not_written (now ..._is_fault_refused_and_not_written), test_unmigrated_state_is_silent_and_unchanged (now test_unmigrated_state_refuses_and_is_silent), test_enrolment_dual_writes_and_old_readers_accept (now test_enrolment_writes_fleet_db_only), test_failed_fleet_token_write_gives_503_and_leaves_legacy_state (renamed ..._keeps_the_existing_token): the fallback or dual-write outcome became the fail-closed or fleet-only outcome
- stub-server/test_fleet_auth.py::test_devices_cli_does_not_mirror_a_second_frame_onto_the_live_state, test_devices_cli_ignores_unmigrated_fleet_db, test_devices_cli_mirror_failure_warns_and_exits_1, test_devices_cli_mirrors_into_migrated_fleet_db, test_devices_cli_without_fleet_db_creates_none, test_removed_device_token_is_rejected_after_migration (devices_cli mirror removed; the orphan-token case stays in test_orphan_token_is_skipped_by_migration_and_rejected), test_legacy_file_names_agree_with_byos (constants removed)
- stub-server/test_fleet_cli.py::test_devices_add_auto_rollback_removes_directory, test_devices_add_rolls_back_when_legacy_write_fails (the failure they injected was the legacy write; replaced by test_devices_add_refuses_a_mac_that_is_already_registered), test_devices_add_mirrors_to_legacy_and_remove_restores_bytes (now test_devices_add_and_remove_touch_fleet_db_only), test_devices_remove_clears_registry_and_token (now ..._clears_the_row_and_its_token), test_remove_pending_mirrors_when_legacy_knows_the_mac
- stub-server/test_ota_fleet_regression.py::test_legacy_frame_without_a_fleet_row_keeps_working_when_fleet_db_is_faulted (legacy fallback)
- stub-server/test_ota_offer.py::test_hardware_fallback_serves_the_legacy_device_and_refuses_a_fleet_only_one (legacy fallback)
- stub-server/test_pending_pairing.py::test_legacy_mirror_refuses_a_pending_mac (mirror removed)
- stub-server/test_phase47_freeze.py::test_previous_release_readers_still_accept_the_migrated_state (reads the retired previous-release files through `load_registry`/`load_state`)

Changed, same id, new body (register frames in fleet.db instead of the legacy files, or new signatures): every test of test_ota_offer.py, test_ota_fleet_regression.py, test_byos_hardening.py, test_check_interval_delivery.py, test_wake_interval_delivery.py, test_poll_cycle.py (harness registration), test_devices_registry.py (setup rules, now fleet.db), test_byos_bind_secret.py (docstring), test_fleet_auth.py (`test_migrated_state_authenticates_pre_migration_token`, `test_default_bucket_untouched_by_valid_poll`, `test_bearer_compare_visits_every_candidate`, `test_remove_after_migration_leaves_no_row_and_no_token`; the legacy-file fixture is now `migrated=False`), test_device_fleet.py (`test_mac_without_a_row_is_401_while_fleet_db_is_usable`, `test_authenticate_device_visits_every_candidate`, `test_fleet_device_recover_threshold_comes_from_its_profile`, `test_live_context_keeps_the_legacy_recover_threshold`: `_device_context` and `_authenticate_device` lost the state parameter), test_co_manager_live_frame.py (`test_co_managers_do_not_change_what_the_byos_loaders_read`: reads the fleet.db view), test_fleet_cli.py (list/revoke/auto-provision/second-default/pending removal: no legacy assertions), server/test_pipeline_e2e.py (harness), server/test_fleet_migrate.py (`test_remove_then_migrate_succeeds_in_both_modes` writes the legacy files as an earlier removal left them instead of running devices_cli; the other tests pass `migrated=False`), test-support/test_test_support.py (two tests), stub-server/test_pairing_freeze.py (seeder now migrates).

Added: stub-server/test_byos_fleet_only.py (11 ids, including the fail-closed test over absent, corrupt and unmarked fleet.db with valid legacy files present), server/test_retire_legacy_state.py (13), TestQuarantineBackup in deploy/tests/test_backup.py (1), fleet_cli replace-secret (2), plus the renamed replacements listed above.

## Freeze test

`stub-server/measured_fields_freeze.json` is byte-identical. `stub-server/test_phase47_freeze.py` is not byte-identical: it differs only by the deletion of `test_previous_release_readers_still_accept_the_migrated_state` (11 lines), the one test whose subject is the retired previous-release reader. The other 20 freeze tests, including the four replay tests, pass unchanged against the new seeder with the same frozen values (wake cadence, battery telemetry, poll state fields). The four replay tests now replay a fleet.db that was imported by the seeder before the first process and re-imported before the second (same response, same sleep_s, same credentials, legacy files unchanged); the legacy-only first leg they used to test is the retired fallback.

## Deviations from the plan

1. **[Owner decision, rule 1/2 conflict] freeze file edited by one deletion.** The coordinator asked both for a byte-identical freeze test and for the five replay/previous-release tests to be rewritten or removed. Only the previous-release test cannot survive; the four replay tests pass as they are. I removed that one test and left every other byte of the file.
2. **[Rule 2] `fleet_cli devices replace-secret` added.** Retiring `devices_cli add --replace` would otherwise leave no way to swap the hash of an already registered frame after re-running `provision.sh` (`register-pending` refuses an existing MAC). It reuses `fleet_db.set_device_secret`; tested.
3. **Parity semantics** of the quarantine CLI (differing values do not block), see above.
4. `devices_cli.py` is deleted outright (nothing of it still made sense next to `fleet_cli`).
5. Plan file list said `deploy/skypane-byos.service` only if needed: one comment line changed; `deploy/tests/test_units.py` passes.
6. The branch `phase-67-19-retire-identity-mirror` could not be used locally (commit guard allows `worktree-agent-*`); commits are on `worktree-agent-67-19` and are pushed to `phase-67-19-retire-identity-mirror`.

## Known Stubs

None.

## Threat flags

None new. T-67-19-01 (fail closed) is covered by test_unreadable_fleet_db_refuses_even_with_valid_legacy_files and test_fleet_auth.py; T-67-19-02 by the parity refusal; T-67-19-03 by the seeded-value grep tests; T-67-19-04 by rename-only moves and the backup allow-list; T-67-19-05 by the dry-run default.
