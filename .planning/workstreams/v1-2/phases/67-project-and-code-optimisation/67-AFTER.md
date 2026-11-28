# Phase 67 After record

Measured 2026-11-28 on `origin/main` at commit e44c55a9. The last commit that touches code or CI is a51c2457 (SPDX headers); e44c55a9 only edits two files under `.planning/` (`git diff --stat a51c2457 e44c55a9`). The numbers are taken with the same commands as `67-BASELINE.md` (baseline commit ace564b), so each row has a before, an after and a delta.

Environment: local runs use Python 3.13.18 (as in the baseline), CI uses Python 3.14.10. Browser tests run only in CI (no Chromium locally). Pull requests run with `SKYPANE_COVERAGE=off`; the coverage floor applies only to pushes to `main` and manual dispatch.

Where a number could not be measured the row says so. Nothing below is estimated.

## Metrics, before and after

Scope: `git ls-files`, `.planning/` excluded unless stated. The per-file counts of lines include the one SPDX line added to 906 Python files (plan 25), so line deltas contain +906 mechanical lines.

| Metric | Before (ace564b, 2026-11-27) | After (e44c55a9, 2026-11-28) | Delta |
|--------|------------------------------|------------------------------|-------|
| Python lines, tracked, outside `.planning` | 277,257 | 279,521 | +2,264 (+1,358 without the 906 SPDX lines) |
| Python files, tracked, outside `.planning` | not recorded in the baseline | 913 | n/a |
| `server/` lines | 68,498: 27,646 production in 82 modules, 40,852 tests in 108 files | 70,082: 27,832 production in 97 modules, 42,250 tests in 115 files | +1,584 lines, +15 production modules, +7 test files |
| `server/` flat top level | 34 production modules, 13,841 lines | 36 production modules, 10,856 lines | -2,985 lines in the top level, +2 modules (11 are alias shims, see below) |
| `companion/` | 166,963: 45,856 production in 166 modules, 121,107 tests in 380 files | 167,136: 45,739 production in 166 modules, 121,397 tests in 380 files | +173 lines; no module or file count change |
| `stub-server/` | 11,146: 2,666 production in 4 modules, 8,480 tests in 21 files | 10,778: 2,351 production in 3 modules, 8,427 tests in 22 files | -368 lines; `devices_cli.py` removed |
| `scripts/` | 6,629: 5,324 production in 21 modules, 1,305 tests in 8 files | 6,868: 5,555 production in 22 modules, 1,313 tests in 8 files | +239 lines; `check_spdx_headers.py` added |
| `deploy/` | 6,765: 940 production in 3 modules, 5,825 tests in 22 files | 7,025: 942 production in 3 modules, 6,083 tests in 22 files | +260 lines |
| `test-support/` | 7,887: 5,364 production in 35 modules, 2,523 tests in 12 files | 8,239: 5,528 production in 36 modules, 2,711 tests in 13 files | +352 lines |
| `hardware/` | 6,886: 4,387 production in 3 modules, 2,499 tests in 6 files | 6,895: 4,390 production in 3 modules, 2,505 tests in 6 files | +9 lines (SPDX only) |
| CSS / JS in `companion/static` | 20,225 lines in 10 files / 12,727 lines in 34 files | 20,225 lines in 10 files / 12,727 lines in 34 files | none |
| Tracked files / under `.planning` | 3,139 / 1,710 | 3,199 / 1,745 | +60 / +35 (outside `.planning`: 1,429 to 1,454, +25) |
| Twelve largest production files | `byos_server.py` 1,891; `poll_cycle.py` 1,841; `fleet_db.py` 1,611; `companion/app.py` 1,446; `airlines_page.py` 1,375; `history_db.py` 1,342; `illustrations.py` 1,253; `firmware_registry.py` 1,245; `ui_base.py` 1,244; `plane/enrich.py` 1,162; `history_page.py` 1,121; `plane/detect.py` 1,091 | `poll_cycle.py` 1,842; `byos_server.py` 1,757; `fleet_db.py` 1,659; `companion/app.py` 1,448; `airlines_page.py` 1,345; `history_db.py` 1,358; `illustrations.py` 1,254; `firmware/registry.py` 1,247 (moved); `ui_base.py` 1,248; `plane/enrich.py` 1,163; `history_page.py` 1,122; `plane/detect.py` 1,092 | Not improved: the same twelve files remain the largest. Only `byos_server.py` (-134) and `airlines_page.py` (-30) shrank; `fleet_db.py` grew by 48 (schema 5 step), `history_db.py` by 16; the rest differ by the one SPDX line |
| Five largest functions, gate scope (max 80) | 76 `history_db.init_schema`; 70 `build_canvas`; 66 `draw_previous_text_block`; 65 `fetch_ics`; 65 `Handler._handle_display` | 74 `history_db._create_initial_schema` (the schema code moved out of `init_schema`); 70 `build_canvas`; 66 `draw_previous_text_block`; 65 `fetch_ics`; 65 `Handler._handle_display` | -2 for the largest; the other four unchanged; none over 80 |
| Five largest functions outside the gate | 89 `scripts/check_comment_history.py::_js_chunks`; 85 `adsb-test/analyze_samples.py::render_report`; 78 `companion/ui_shell.page_shell`; 77 `hardware/logtools.build_run_report`; 75 `companion/page_context.build_page_context` | 85 `adsb-test/analyze_samples.py::render_report`; 78 `companion/ui_shell.page_shell`; 77 `hardware/logtools.build_run_report`; 75 `companion/page_context.build_page_context`; 74 `hardware/logtools.build_parser` | `_js_chunks` split (plan 10); `companion` and `scripts` are now inside the gate, `adsb-test`, `hardware`, `test-support` are not |
| Function-size gate scope and result | `server stub-server`, max 80 | `server stub-server companion deploy scripts`, max 80: 3,401 functions scanned, none over 80 | scope widened from 2 to 5 roots |
| mypy | no issues in 51 source files, of 251 production modules (server 82, stub-server 4, companion 165) | no issues in 57 source files, of 265 production modules (server 97, stub-server 3, companion 165) | +6 files checked (20.3 % to 21.5 % of production modules) |
| mypy strict override list | 30 module entries | 43 module entries | +13 |
| Function annotation coverage (production, all parameters and the return annotated, `self`/`cls` excluded) | server 589 of 1,141 (51.6 %); companion 18 of 1,856 (1.0 %); stub-server 0 of 129 (0.0 %); overall 607 of 3,126 (19.4 %) | server 622 of 1,133 (54.9 %); companion 18 of 1,839 (1.0 %); stub-server 0 of 111 (0.0 %); overall 640 of 3,083 (20.8 %) | overall +1.4 points; companion and stub-server did not move |
| ruff | All checks passed | All checks passed | none |
| Tests collected | 17,598 | 17,717 | +119 (90 ids removed, 209 added) |
| Last green main CI run | run 45993237674 (code commit df9b781) | run 46180225838 (push, commit a51c2457, success) | n/a |
| Executed / skipped (that run) | 17,598 executed, 0 failures, 0 errors, 0 skipped (browser 1084, 777, 796, 690, 719, 676; core 5938, 6918) | 17,717 executed, 0 failures, 0 errors, 0 skipped (browser 1084, 777, 796, 690, 719, 676; core 6207, 6768) | +119 executed; browser shards identical (4,742); core +119 (12,856 to 12,975) |
| Coverage TOTAL (that run) | `TOTAL 30488 1174 96%` (96.15 %); `fail_under = 93` | `TOTAL 30083 1143 96%` (96.20 %); `fail_under` per the ratchet section below | -405 statements (retired code), -31 missed lines, +0.05 points |
| Wall time (that run) | whole workflow 10 min 24 s; static 0:39; non-browser shards 3:43 and 3:30; browser shards 7:04, 7:24, 6:21, 6:54, 7:09, 9:49; final job 0:29 | whole workflow 8 min 33 s; static 0:36; non-browser shards 4:22 and 4:48; browser shards 0 to 5: 5:54, 6:23, 6:02, 6:09, 7:29, 8:02 (shard 5 slowest at 8:02); final job 0:25 | whole workflow -1 min 51 s. The non-browser shards got slower (+39 s and +78 s); the previous main run (ed9d0ddc, 17,694 tests) had 4:32 and 3:34 for the same shards, so the spread between runs is of the order of a minute and one run each is not enough to call a trend. Run-to-run variance was not measured further |
| Local freeze and golden fast check | 115 passed in about 7.5 s | 114 passed in 13.6 s | -1 test (the previous-release reader test, see removed ids); the time is not comparable: this run shared the machine with other work, not re-measured quietly |
| Non-main remote branches | 40 | 1 (`claude/` agent session branch, not a phase branch) | -39. The owner deleted the 40 branches (R7); the one that remains was not read further |
| CI checks (steps of the `ci.yml` workflow) | 46 named steps in `ci.yml`; static job gates: ruff, mypy, function size (2 roots), comment-history | 47 named steps; new static gate: SPDX header check; function-size step names 5 roots | +1 step (SPDX gate). Workflow files unchanged in number (5 in `.github/workflows`) |

### Not measured

- Local collection time: not re-taken, the baseline value (3.4 s of pytest time) depends on machine load.
- Local coverage: see the ratchet section; the full suite with browser tests cannot run here, so no local total is reported as the floor basis.
- The CI run for the docs-only commit e44c55a9 was not finished when this record was written; it is not needed because nothing under code or CI changed.
- Wall time variance across several runs: only the runs named above were read.

## Gates: none decreased

| Gate | At phase start | Now | Change |
|------|----------------|-----|--------|
| `MIN_EXECUTED` (`scripts/ci_gates.py`) | 12,821 | 17,591 | Raised to 17,598 by plan 01, lowered once by 7 to 17,591 by plan 24 (owner decision R4: four test-only functions and the seven tests that exercised only them). Net +4,770 over the phase start. It is 126 below the 17,717 tests CI executes now and 7 below the 17,598 of the baseline: this is the single lowering the owner approved. Left unchanged by plan 16 (see below) |
| `MAX_SKIPPED` | 0 | 0 | unchanged |
| Coverage `fail_under` | 93 | see ratchet section | never lowered |
| Function-size gate | max 80 over `server stub-server` | max 80 over `server stub-server companion deploy scripts` | wider |
| mypy files list | 51 | 57 | +6; strict list 30 to 43 |
| ruff | `ruff check .` clean | clean | rule set unchanged (rule set `B` deferred, R6) |
| Comment-history guard | in CI | in CI | unchanged; `scripts/check_comment_history.py check` passes |
| SPDX header gate | none | `scripts/check_spdx_headers.py check` in `ci.yml` | new |

## Collected-id comparison

`before.ids` regenerated from the commit named in the baseline (`git archive ace564b`, then `pytest --collect-only -q --no-cov -p no:cacheprovider`, `grep '::'`, `LC_ALL=C sort`): 17,598 ids, sha256 96b64df5aab477e27ed49cb8862b9dbb3bfa9a640c61955a2996fbdf7122b65c, identical to the baseline hash. `after.ids` from e44c55a9: 17,717 ids.

- `comm -23 before.ids after.ids` (ids that vanished): 90 lines. Every one is a test removed together with retired code under an owner decision, listed below. No rename was found among them (a replaced test got a new id, which counts as one removed and one added).
- `comm -13 before.ids after.ids` (ids added): 209. 17,598 - 90 + 209 = 17,717.
- By source: plan 24 removed 7, plan 19 removed 40, plan 20 removed 43; this sums to 90, and each file group matches the plan summaries (plan 21's one renamed id existed only after plan 17, so it is not in the diff against the baseline).

### Removed test ids (90)

Plan 24, four test-only functions with no test that also covered other behaviour (7): the five ids of `companion/` and the two of `server/test_fleet_cycle.py`, for `geofence_resolver`, `sightings_across`, `step_b_trigger_html`, `regularity_grid`.

Plan 19, device identity from `fleet.db` only, `devices_cli.py` and the legacy fallbacks (40): the ids under `stub-server/`. Where the behaviour has a successor test, the plan 19 summary names it (for example `test_corrupt_fleet_db_fails_closed_and_logs_once`, `test_fleet_db_without_marker_refuses`, `test_unavailable_fleet_db_refuses_every_device`).

Plan 20, per-frame registry and artwork merges (43): `server/test_fleet_artwork.py` (20 ids, file deleted with the module), `server/test_fleet_migrate.py` (8), `server/test_fleet_registries.py` (15).

The full list, sorted, from `comm -23`:

```
companion/test_airline_collection.py::test_sightings_across_frames_are_merged_newest_first_and_counted_together
companion/test_device_links.py::test_step_b_trigger_addresses_stay_in_the_device_and_return_stays_plain
companion/test_status_pages_02.py::test_regularity_grid_cells_are_sized_from_the_360px_floor
companion/test_status_pages_02.py::test_regularity_grid_has_four_states_and_never_conflates_them
companion/test_status_pages_02.py::test_regularity_grid_is_bounded_and_keeps_the_newest_buckets
server/test_fleet_artwork.py::test_a_dry_run_plan_writes_nothing
server/test_fleet_artwork.py::test_a_second_archived_version_gets_a_numeric_suffix_and_never_overwrites
server/test_fleet_artwork.py::test_a_second_run_changes_nothing_and_a_removed_picture_stays_removed
server/test_fleet_artwork.py::test_a_symlinked_fleet_directory_is_not_written_through
server/test_fleet_artwork.py::test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order[order0]
server/test_fleet_artwork.py::test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order[order1]
server/test_fleet_artwork.py::test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order[order2]
server/test_fleet_artwork.py::test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order[order3]
server/test_fleet_artwork.py::test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order[order4]
server/test_fleet_artwork.py::test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order[order5]
server/test_fleet_artwork.py::test_a_tie_with_the_fleet_file_keeps_the_fleet_file
server/test_fleet_artwork.py::test_a_write_failure_raises_and_writes_no_marker
server/test_fleet_artwork.py::test_hostile_or_invalid_candidates_are_skipped_reported_and_never_deleted
server/test_fleet_artwork.py::test_identical_bytes_are_neither_a_conflict_nor_copied_nor_archived
server/test_fleet_artwork.py::test_merge_without_conflict_keeps_bytes_and_times_and_touches_no_frame_file
server/test_fleet_artwork.py::test_the_byte_cap_merges_the_latest_first
server/test_fleet_artwork.py::test_the_file_cap_merges_the_latest_first_and_leaves_the_rest_pending
server/test_fleet_artwork.py::test_the_latest_file_time_wins_and_every_loser_is_archived
server/test_fleet_artwork.py::test_the_live_frames_own_directory_is_never_a_device_source
server/test_fleet_artwork.py::test_the_upload_cap_equals_the_companion_upload_cap
server/test_fleet_cycle.py::test_default_resolver_gives_every_device_the_geofence_zone
server/test_fleet_cycle.py::test_default_resolver_with_missing_geofence_raises_oserror
server/test_fleet_migrate.py::test_a_registry_write_failure_exits_1
server/test_fleet_migrate.py::test_an_artwork_write_failure_exits_1
server/test_fleet_migrate.py::test_artwork_merge_dry_run_writes_nothing_then_real_run_applies_then_is_idempotent
server/test_fleet_migrate.py::test_artwork_merge_is_silent_without_per_frame_pictures
server/test_fleet_migrate.py::test_registry_and_artwork_merges_share_one_report_and_work_alone
server/test_fleet_migrate.py::test_registry_merge_dry_run_writes_nothing_then_real_run_applies_then_is_idempotent
server/test_fleet_migrate.py::test_registry_merge_is_reported_when_fleet_db_is_already_migrated
server/test_fleet_migrate.py::test_registry_merge_is_silent_without_per_frame_files
server/test_fleet_registries.py::test_a_frame_file_changed_since_is_merged_again_once
server/test_fleet_registries.py::test_a_second_run_changes_nothing_and_a_deleted_name_is_not_brought_back
server/test_fleet_registries.py::test_a_symlinked_frame_directory_or_registry_file_and_bad_names_are_ignored
server/test_fleet_registries.py::test_a_tie_goes_to_the_root_then_to_the_lowest_frame_id
server/test_fleet_registries.py::test_a_write_failure_raises_and_leaves_no_marker
server/test_fleet_registries.py::test_an_invalid_or_oversized_frame_file_counts_as_no_entries_and_is_reported
server/test_fleet_registries.py::test_an_unparsable_stamp_loses_to_any_valid_one
server/test_fleet_registries.py::test_default_types_root_wins_then_lowest_frame_id
server/test_fleet_registries.py::test_distinct_names_from_two_frames_all_reach_the_root_and_frame_files_are_untouched
server/test_fleet_registries.py::test_hostile_entries_never_reach_the_root_file
server/test_fleet_registries.py::test_overrides_may_not_take_a_built_in_airlines_name_or_another_airlines_override
server/test_fleet_registries.py::test_the_cap_merges_exactly_the_free_room_and_deletes_nothing
server/test_fleet_registries.py::test_the_live_frames_own_files_are_never_a_source
server/test_fleet_registries.py::test_the_newest_stamp_wins_and_the_losers_are_logged_and_recorded
server/test_fleet_registries.py::test_the_result_does_not_depend_on_the_frame_listing_order
stub-server/test_byos_hardening.py::test_save_registry_leaves_devices_json_mode_0600
stub-server/test_byos_hardening.py::test_save_state_and_save_battery_state_leave_no_temp_and_valid_json
stub-server/test_byos_hardening.py::test_save_state_concurrent_threads_no_exception
stub-server/test_device_fleet.py::test_corrupt_fleet_db_still_serves_the_live_frame
stub-server/test_device_fleet.py::test_unavailable_fleet_db_refuses_a_non_live_device[_corrupt_fleet_db]
stub-server/test_device_fleet.py::test_unavailable_fleet_db_refuses_a_non_live_device[_remove_fleet_db]
stub-server/test_device_fleet.py::test_unavailable_fleet_db_with_an_unreadable_live_record_refuses_everyone
stub-server/test_device_fleet.py::test_unavailable_fleet_db_without_the_live_record_refuses_everyone
stub-server/test_devices_registry.py::test_corrupt_registry_file_refuses_every_enrolment
stub-server/test_devices_registry.py::test_devices_cli_add_list_remove_round_trip
stub-server/test_devices_registry.py::test_devices_cli_add_over_existing_mac_without_replace_exits_nonzero
stub-server/test_devices_registry.py::test_devices_cli_add_rejects_a_malformed_mac_or_non_hex_hash
stub-server/test_devices_registry.py::test_devices_cli_remove_drops_only_that_macs_token
stub-server/test_devices_registry.py::test_devices_cli_remove_without_a_token_leaves_the_state_file_untouched
stub-server/test_devices_registry.py::test_devices_cli_revoke_token_removes_only_that_macs_token
stub-server/test_devices_registry.py::test_devices_json_never_contains_the_plaintext_secret
stub-server/test_devices_registry.py::test_missing_registry_file_refuses_every_enrolment
stub-server/test_devices_registry.py::test_non_dict_registry_file_refuses_every_enrolment
stub-server/test_fleet_auth.py::test_corrupt_fleet_db_falls_back_and_logs_once
stub-server/test_fleet_auth.py::test_devices_cli_does_not_mirror_a_second_frame_onto_the_live_state
stub-server/test_fleet_auth.py::test_devices_cli_ignores_unmigrated_fleet_db
stub-server/test_fleet_auth.py::test_devices_cli_mirror_failure_warns_and_exits_1
stub-server/test_fleet_auth.py::test_devices_cli_mirrors_into_migrated_fleet_db
stub-server/test_fleet_auth.py::test_devices_cli_without_fleet_db_creates_none
stub-server/test_fleet_auth.py::test_enrolment_dual_writes_and_old_readers_accept
stub-server/test_fleet_auth.py::test_failed_fleet_token_write_gives_503_and_leaves_legacy_state
stub-server/test_fleet_auth.py::test_fleet_db_without_marker_is_ignored
stub-server/test_fleet_auth.py::test_legacy_file_names_agree_with_byos
stub-server/test_fleet_auth.py::test_removed_device_token_is_rejected_after_migration
stub-server/test_fleet_auth.py::test_too_new_fleet_db_is_fault_and_not_written
stub-server/test_fleet_auth.py::test_unmigrated_state_is_silent_and_unchanged
stub-server/test_fleet_cli.py::test_devices_add_auto_rollback_removes_directory
stub-server/test_fleet_cli.py::test_devices_add_mirrors_to_legacy_and_remove_restores_bytes
stub-server/test_fleet_cli.py::test_devices_add_rolls_back_when_legacy_write_fails
stub-server/test_fleet_cli.py::test_devices_remove_clears_registry_and_token
stub-server/test_fleet_cli.py::test_remove_pending_mirrors_when_legacy_knows_the_mac
stub-server/test_ota_fleet_regression.py::test_legacy_frame_without_a_fleet_row_keeps_working_when_fleet_db_is_faulted
stub-server/test_ota_offer.py::test_hardware_fallback_serves_the_legacy_device_and_refuses_a_fleet_only_one
stub-server/test_pending_pairing.py::test_legacy_mirror_refuses_a_pending_mac
stub-server/test_phase47_freeze.py::test_previous_release_readers_still_accept_the_migrated_state
```

## Retained `sys.modules` alias shims (11)

Verified by `grep -l 'sys.modules\[__name__\]' server/*.py`: eleven files, each replaces itself at import by the real module in a subpackage, so importers, `monkeypatch` and `mock.patch` sites keep working under the old names.

| Old path | New location |
|----------|--------------|
| `server/firmware_cli.py` | `server/firmware/cli.py` |
| `server/firmware_image.py` | `server/firmware/image.py` |
| `server/firmware_registry.py` | `server/firmware/registry.py` |
| `server/request_budget.py` | `server/polling/request_budget.py` |
| `server/zone_fetch.py` | `server/polling/zone_fetch.py` |
| `server/http_fetch.py` | `server/polling/http_fetch.py` |
| `server/fleet_zones.py` | `server/polling/fleet_zones.py` |
| `server/fleet_cycle.py` | `server/polling/fleet_cycle.py` |
| `server/pairings.py` | `server/pairing/pairings.py` |
| `server/pairing_code.py` | `server/pairing/code.py` |
| `server/pairing_image.py` | `server/pairing/image.py` |

Every outside importer (companion, stub-server, other server modules, tests, scripts, `deploy/activate.sh`, docs) still uses the old names; removing a shim is a later owner decision. Each shim has a test (`server/test_module_shims_firmware.py` 14 ids, `..._polling.py` 18, `..._pairing.py` 11).

## Test-only API outcome (R4)

`67-TEST-ONLY-API.md` lists 27 functions that only tests call (the research estimate was about 30). Owner outcome: DELETE the 4 without a test that also covers other behaviour (`geofence_resolver`, `regularity_grid`, `sightings_across`, `step_b_trigger_html`), done by plan 24 with their 7 tests; KEEP the other 23 as test seams. No name flagged AUDITED (Phase 66 review scope) was touched.

## Owner decisions (R1 to R22)

The full register is section 5 of `67-OWNER-DECISIONS.md`. Outcome at the end of the phase:

- Applied: R1, R2, R4, R6 (nothing to apply), R7 to R21 as the register states, with the deletion of 40 remote branches done by the owner.
- R3 (coverage floor): applied by this plan, see the ratchet section.
- R5 (SPDX): applied by plan 25, see below.
- R22 stays OPEN (see the defer list).

### Retirement gate results (D-12, `67-RETIREMENT-GATE.md`)

| Item | Result | Plan |
|------|--------|------|
| G1 identity mirror (`devices.json`, `byos_state.json`) | APPROVED by the owner 2026-11-28, production check SAFE | 19: device server fails closed on `fleet.db` only; `devices_cli.py` removed; `fleet_cli devices register-pending` and `replace-secret` replace it; owner-run `server.retire_legacy_state` quarantines the files |
| G2 per-frame registry and artwork copies | APPROVED, production check SAFE (no per-frame copy, 0 pictures, both markers absent) | 20: merge code removed, quarantine step added |
| G3 `legacy-admin` principal | APPROVED (after G6) | 21: `fleet.db` schema 5, step `sessions-user-principal-only`, `PRINCIPAL_LEGACY_ADMIN` removed |
| G4 `wake_epochs` table | KEPT, final | 22: not dropped |
| G5 leftovers (`META_LAST_POLL_TRIGGER`, `delete_location_if_unused`, `count_locations_owned`, `location_usage_counts`) | APPROVED | 22: removed |
| G6 end of the rollback period | APPROVED | schema 5 accepted: the previous release cannot open a schema 5 file, recovery is the nightly backup |

Final schema versions: `fleet.db` 5 (`SCHEMA_VERSION = len(MIGRATIONS)`, was 4), `history.db` 1 (unchanged). The one shared migration module is `server/sqlite_migrations.py` (plan 17, policies `immediate/refuse` for `fleet.db` and `idempotent/keep` for `history.db`, read-only `report` command, exit codes 0 current, 3 pending, 2 unreadable).

`MIN_EXECUTED` through the retirements: plans 19 and 20 removed 83 ids but the collected count stayed above 17,591, so only plan 24's single lowering (to 17,591) happened.

### D-14 results

- Plan 24: names approved or kept as above; 7 removed test ids; `MIN_EXECUTED` 17,598 to 17,591 (the only lowering).
- Plan 25 (SPDX): `# SPDX-License-Identifier: AGPL-3.0-only` stamped on 906 tracked Python files (verified: `grep -l` finds the AGPL line in 906 files outside `.planning`). Four Apache-2.0 headers kept (`server/test_fault_screen_mask.py`, `server/test_updating_screen.py`, `server/test_updating_screen_mask.py`, `stub-server/fleet_cli.py`). Excluded from the gate: `firmware/` (Apache-2.0), `stub-server/byos_server.py` (Apache-2.0), `.planning/`, `.claude/`. The 11 tracked files in `design-exploration/` carry the line (the owner wanted that directory included; the exclusion list does not name it). The gate is `scripts/check_spdx_headers.py check`, a step in `ci.yml`, and passes on the current tree. Stamping changed no AST and no docstring (plan 25 evidence).

## Defer list (not done in this phase, with reasons)

1. Naming and layout of `stub-server/` and `companion/`: not regrouped; the filenames and the 380 companion test files stay as they are (a rename changes collected ids and every importer).
2. Slow or redundant tests: no further removal beyond the items already listed in the phase; deferred.
3. Test files named after a phase (`stub-server/test_phase47_freeze.py`, `companion/test_browser_phase44_walkthrough.py`): not renamed, because a rename changes every collected test id of the file and the before/after id comparison; to do together with a deliberate id re-baseline.
4. Ruff rule set `B` (R6): not adopted; the `B023` candidates stay listed for a later review.
5. `LocationInUse` (`server/fleet_db.py:98`): the class is still defined and no code or test references it any more (verified by grep); it was not in the plan 22 list.
6. `companion/resolve_dialog.py`: `_return_query` (line 44) and `_trigger_attrs_html` (line 49) have no caller after plan 24 (verified by grep, only the definitions).
7. `companion/draw.py` grid helpers: `grid_columns`, `grid_cell_size`, `cell_class` and their constants have no use outside `draw.py` itself after `regularity_grid` was removed (grep: only definitions and a comment); not removed.
8. The nine names under "Considered and not listed" in `67-TEST-ONLY-API.md` (rated by vulture, no call from production code): `resolve_login`, `check_in_gaps`, `getcode`, `theme_label`, `next_wake_at_iso`, `draw_frame`, `runway_label`, `_build_no_connection_canvas`, `_build_updating_canvas`. Not added; the owner can ask for them.
9. Three pure dead-code items with no reference anywhere (verified by grep: definition only): `airport_label` (`companion/detection_summary.py:39`), `battery_dropped` (`companion/health_signals.py:469`), the property `FleetResult.live_outcome` (`server/polling/fleet_cycle.py:327`).
10. A pre-existing race: two processes that open a brand-new `history.db` at the same instant can lose with `sqlite3.OperationalError: database is locked` at `PRAGMA journal_mode=WAL` despite the busy timeout (seen once in about 20 runs under load; line not touched by plan 17). The next open succeeds; the process test starts from a file already in WAL mode.
11. `wake_epochs` table: kept by owner decision G4.
12. The shims: all eleven stay; retiring them means rewriting every importer and patch site.
13. The 23 KEEP names of the test-only list.
14. Plan 04 (flaky lightbox test fix): the code change is in; its 30-consecutive-CI-pass checkpoint was never recorded in a summary, so it is not verified here.

### OPEN owner question (R22)

The drag-release velocity in `companion/static/modal.js` and `companion/static/toast.js` is stale when the release event arrives after a pause; this is a product observation, nothing was changed in this phase, and it needs its own pull request if the owner wants it fixed.

## Owner-side steps still to do

These need the owner's hand on the VPS; nothing in this phase was deployed by an agent, and production still runs a release older than plan 17.

1. Manual deploy of the current `main` (`workflow_dispatch` of `deploy.yml`, reviewer-gated). The deploy installs schema 5; the previous release cannot open a schema 5 file, so a rollback after the first start means restoring the nightly backup (`deploy/README.md`, "Schema v5 and rollback").
2. Then run the report: `python3 -m server.sqlite_migrations report` (skip it before the deploy: the command does not exist on the old release) and check that both databases say `ok`.
3. Then the quarantine dry run: `python3 -m server.retire_legacy_state --state-dir DIR` and read its output.
4. Only after reading the dry run: the same command with `--apply`, which renames the legacy files and any per-frame copies into `retired-legacy/<date>/` (never deletes, never overwrites; the nightly backup archives that directory).
5. Verify, and keep the restore step of the runbook at hand (`deploy/README.md`, "Retiring the legacy files (owner runbook)").

## Coverage ratchet

Pull requests run without coverage tracing, so the floor can only be taken from a push to `main` (or a manual dispatch of `ci.yml`).

- Source of the value: the job "Lint, test, coverage, attribution" of CI run 46180225838 (push to `main`, commit a51c2457, the last commit that touches code), Python 3.14.10, all eight shards including the six browser shards: `TOTAL 30083 1143 96%`, that is (30083 - 1143) / 30083 = 96.20 %. The same job reports `total: 17717 tests, 0 failures, 0 errors, 0 skipped, 17717 executed`. The previous green main run (46175941432, commit ed9d0ddc, 17,694 executed) gave `TOTAL 30083 1141 96%`, 96.21 %: the two runs differ by two missed lines, so the value is stable to about 0.01 points.
- Floor: the whole-number part of 96.20 is 96. `fail_under` goes from 93 to 96 in `pyproject.toml` (never below 93, never below the previous value, never above the measured 96.20; no margin subtracted, as the plan says; the actual distance to the measured value is 0.20 points).
- No test and no document states the floor as a number (`grep -rn fail_under` finds only the `pyproject.toml` entry and the comments in `scripts/run-all-tests.sh` that name the key), so nothing else needed an edit.
- `MIN_EXECUTED` left at 17,591: plan 16 lists only `pyproject.toml` for modification, and the gate is a count of executed tests, not a coverage value. The count CI executes is 17,717 and 17,717 ids are collected locally, so raising it to 17,717 would be safe on today's tree; it is left as a follow-up for the owner.
- Local run, informational only: the local environment has no Chromium, so a local total cannot equal CI's and was not used. See the summary of this plan for the local non-browser figure.
- Whether the new floor passes on `main` is shown by the first push CI run after this change; it could not be run before the change is on `main`. A local `coverage report --fail-under=96` on the core data only says nothing about the browser shards.
