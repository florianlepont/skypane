---
phase: 67-project-and-code-optimisation
plan: 20
subsystem: fleet-migration
tags: [fleet-migrate, registries, artwork, retirement, quarantine, backup]
requires: ["67-19"]
provides: ["fleet_migrate without the per-frame merges", "per-frame copy quarantine in server/retire_legacy_state.py"]
affects: ["server/fleet_migrate.py", "server/plane/fleet_registries.py", "deploy/backup/skypane_backup.py"]
key-files:
  created: [server/test_fleet_root_characterisation.py]
  modified: [server/fleet_migrate.py, server/plane/fleet_registries.py, server/plane/fleet_default_types.py, server/plane/fleet_set_defaults.py, server/retire_legacy_state.py, server/test_retire_legacy_state.py, server/test_fleet_migrate.py, server/test_fleet_registries.py, deploy/backup/skypane_backup.py, deploy/tests/test_backup.py, pyproject.toml, scripts/ci_shard_weights.json]
  deleted: [server/plane/fleet_artwork.py, server/test_fleet_artwork.py]
metrics:
  tasks: 2
  completed: 2026-11-28
---

# Phase 67 Plan 20: Retire the per-frame registry and artwork copies (G2) Summary

The code that folded `devices/<id>/manual_resolutions.json`, `airline_name_overrides.json`, `airline_default_types.json` and `devices/<id>/illustration_overrides/` into the fleet root is gone, and the owner-run quarantine tool moves any leftover copy aside. Gate: G2 APPROVED in 67-RETIREMENT-GATE.md (owner, 2026-11-28, production check SAFE: no per-frame copy file, 0 pictures, both markers absent).

## Commits (branch phase-67-20-retire-frame-copies)

- 95e10f67 test: characterisation tests `server/test_fleet_root_characterisation.py` (5 ids), green on the unmodified code and unchanged after the removal. They pin the `fleet_migrate` output and written files for a fresh and an already migrated state (dry run and apply), and that the three registry readers and the artwork path resolve a frame directory to the fleet root and ignore files left in a frame directory.
- b111fb4d feat: quarantine CLI extension (Task 2).
- a204c758 refactor: merge code removal, backup list, tests (Task 1).

## Exact behaviour change

None for an install without per-frame copies (the owner's production). The characterisation tests prove the same lines, exit code and written files before and after: `fleet_migrate` prints the import lines, the two default-type steps and nothing starting `airline names:` or `artwork:`, and writes no `airline_registry_migration.json`, `illustration_migration.json`, `illustration_overrides/` or `illustration_conflicts/`.

For an install that still has per-frame copies: `fleet_migrate` no longer merges them (no `airline names:` / `artwork:` lines, nothing written to the root registries or artwork from them), and the nightly backup no longer archives them; the backup prints its usual `not in include list: devices/<id>/<name>` drift line for each until the owner runs the quarantine tool, which moves them into `retired-legacy/<date>/devices/<id>/` (archived). The runtime never read them.

Runtime readers (`manual_resolutions`, `name_overrides`, `airline_default_types`, `illustrations.override_dir_for_state_dir`) are untouched. `fleet_migrate.migrate()` order is unchanged: fleet.db import, `fleet_default_types` clearing, `fleet_set_defaults`. The clearing plan is now computed once instead of twice (it was re-planned after the merges only because the merges could bring in a picture or default); with no merge the two plans are identical.

## Runtime-reader proof (grep before removal)

`git grep` over `server`, `companion`, `stub-server` (non-test) for `MANUAL_RESOLUTIONS_FILENAME`, `NAME_OVERRIDES_FILENAME`, `DEFAULT_TYPES_FILENAME`, `ILLUSTRATION_OVERRIDE_DIRNAME`: every runtime path goes through `device_dirs.fleet_root_for(state_dir)`. The only users of the per-frame location were `fleet_registries` and `fleet_artwork` (the merges). `fleet_registries.frame_state_dirs` is kept: `fleet_set_defaults.fleet_sightings` uses it to add up every frame's `history.db`. No other code writes the per-frame names, so they left `DEVICE_INCLUDE_FILES` / `DEVICE_INCLUDE_DIRS`.

## Quarantine CLI

`python3 -m server.retire_legacy_state --state-dir DIR [--apply]` now has a second, independent step after the identity step (the identity output is byte-identical when no per-frame copy exists).
- Looks only at valid frame ids under a real `devices/` directory; symlinked frame directory, registry file or artwork directory, non-regular files and `devices/` entries not named like a frame id are skipped and reported (ids and counts), never followed.
- Dry run by default: lists per frame the file name and size in bytes, or the picture count of `illustration_overrides`.
- `--apply` renames each item into `retired-legacy/<UTC date>/devices/<id>/` (directory mode 0700), never deletes, never overwrites (every target is checked first, exit 2), idempotent (second run prints `nothing to do`). Root registries, root artwork, markers and other frame files are never touched.
- Refused (exit 2, nothing moved, also in dry run) when the root marker for a kind of copy present is missing: `airline_registry_migration.json` for registry files, `illustration_migration.json` for pictures.
- The exit code is the worst of the identity step and the frame step; the two steps do not block each other.
- Backup: `retired-legacy` was already in `INCLUDE_DIRS`; a new test proves quarantined per-frame copies reach the archive with no drift line.

## Deviations from Plan

- [Marker rule, refinement] The plan says both root markers must exist before `--apply`. I require the marker of each kind of copy that is present (registry marker only if a registry file exists, artwork marker only if a picture exists; an empty `illustration_overrides` directory needs none). Requiring both would make the tool unusable on an install that only ever had registry copies, because the artwork merge writes no marker when there are no pictures. Both markers are still required when both kinds exist.
- [Scope] `server/plane/fleet_default_types.py` and `server/plane/fleet_set_defaults.py` docstrings mentioned the removed merges; edited the text only.
- [Tooling] `scripts/ci_shard_weights.json`: removed the deleted test file and added the new one (weight 1).
- MIN_EXECUTED left at 17,591: collected ids 17,665 after (17,692 before), so the count did not drop below it.

## Test accounting

Collected ids: 17,692 before (with the 5 characterisation ids), 17,665 after: 43 removed, 16 added. Removed (all exercised only the retired merge code; D-05 relaxed for these only):

server/test_fleet_artwork.py (file deleted with the artwork merge module, 20 ids): test_a_dry_run_plan_writes_nothing, test_a_second_archived_version_gets_a_numeric_suffix_and_never_overwrites, test_a_second_run_changes_nothing_and_a_removed_picture_stays_removed, test_a_symlinked_fleet_directory_is_not_written_through, test_a_tie_goes_to_the_fleet_file_then_the_lowest_device_id_whatever_the_order[order0..order5] (6 ids), test_a_tie_with_the_fleet_file_keeps_the_fleet_file, test_a_write_failure_raises_and_writes_no_marker, test_hostile_or_invalid_candidates_are_skipped_reported_and_never_deleted, test_identical_bytes_are_neither_a_conflict_nor_copied_nor_archived, test_merge_without_conflict_keeps_bytes_and_times_and_touches_no_frame_file, test_the_byte_cap_merges_the_latest_first, test_the_file_cap_merges_the_latest_first_and_leaves_the_rest_pending, test_the_latest_file_time_wins_and_every_loser_is_archived, test_the_live_frames_own_directory_is_never_a_device_source, test_the_upload_cap_equals_the_companion_upload_cap (compared the merge's own cap constant with the upload cap).

server/test_fleet_migrate.py (8 ids, they asserted the merge lines, files or failures): test_registry_merge_dry_run_writes_nothing_then_real_run_applies_then_is_idempotent, test_registry_merge_is_silent_without_per_frame_files (silent case is now pinned by test_fresh_apply_imports_sets_the_defaults_and_creates_no_merge_file), test_registry_merge_is_reported_when_fleet_db_is_already_migrated, test_a_registry_write_failure_exits_1, test_artwork_merge_dry_run_writes_nothing_then_real_run_applies_then_is_idempotent, test_artwork_merge_is_silent_without_per_frame_pictures (same), test_registry_and_artwork_merges_share_one_report_and_work_alone, test_an_artwork_write_failure_exits_1.

server/test_fleet_registries.py (15 ids, the merge: conflict rule, markers, caps, hostile input): test_distinct_names_from_two_frames_all_reach_the_root_and_frame_files_are_untouched, test_the_newest_stamp_wins_and_the_losers_are_logged_and_recorded, test_a_tie_goes_to_the_root_then_to_the_lowest_frame_id, test_an_unparsable_stamp_loses_to_any_valid_one, test_the_result_does_not_depend_on_the_frame_listing_order, test_a_second_run_changes_nothing_and_a_deleted_name_is_not_brought_back, test_a_frame_file_changed_since_is_merged_again_once, test_overrides_may_not_take_a_built_in_airlines_name_or_another_airlines_override, test_default_types_root_wins_then_lowest_frame_id, test_the_cap_merges_exactly_the_free_room_and_deletes_nothing, test_hostile_entries_never_reach_the_root_file, test_a_symlinked_frame_directory_or_registry_file_and_bad_names_are_ignored (the `frame_state_dirs` part is kept in the new test of the same area below), test_an_invalid_or_oversized_frame_file_counts_as_no_entries_and_is_reported, test_the_live_frames_own_files_are_never_a_source, test_a_write_failure_raises_and_leaves_no_marker.

Added (16): server/test_fleet_root_characterisation.py (5), server/test_fleet_registries.py (3, the surviving `frame_state_dirs` behaviour: order, root only, symlink and bad names skipped), server/test_retire_legacy_state.py (11 ids: 8 test functions, one parametrised over 2 markers and 2 flags), deploy/tests/test_backup.py (`test_a_per_frame_copy_is_reported_as_drift_and_not_archived`, `TestQuarantineBackup::test_quarantined_per_frame_copies_reach_the_archive_without_drift`).

Changed, same id, new body: deploy/tests/test_backup.py `TestAirlineFiles::test_every_airline_state_file_is_classified` (per-frame names are no longer in the device include list), `test_airline_files_reach_the_archive_without_drift` (device copies no longer seeded), `TestArtworkMergeBackup::test_fleet_artwork_directories_and_marker_reach_the_archive_without_drift` (no per-frame picture), `TestDeviceDirectories::test_devices_include_list_and_exclusions` (no per-frame registry file or picture among the kept names).

## Checks

- Non-browser core group (`SKYPANE_TEST_GROUP=core`, coverage off): 12,916 tests; the one failure (`TestDeviceDirectories::test_devices_include_list_and_exclusions`, it still expected the per-frame names in the archive) was fixed in the last commit, then `deploy/tests` re-run: 406 passed, 1 skipped.
- `stub-server/test_phase47_freeze.py` (freeze) unchanged and green (20 passed); goldens, fleet/registry/artwork/default-type tests, `server/test_fleet_migrate.py`, access-matrix tests and the backup drift guard are in the core group and green.
- mypy (module list, fleet_artwork removed): no issues in 57 files. ruff: all checks passed. Function-size gate (max 80): none over. Comment-history check: clean. Exposure scan of the changed files: no address, token or e-mail other than the example domains already in the tests.
- Browser tests (companion Playwright) not run here; CI is the check.

## Lines plan 23 must update (not edited here)

- ARCHITECTURE.md lines 285 to 286 (module list names `fleet_registries.py` and `fleet_artwork.py` as the merges), 743 (per-frame vs fleet registries), 818 to 825 (state map: markers `airline_registry_migration.json` and `illustration_migration.json` are now only read by the quarantine tool and kept in the backup when present; `illustration_overrides/` "overrides also per frame" is no longer true), 889 to 893 (item 2, "Per-frame registry leftovers (rollback safety net)": now retired, moved by `retire_legacy_state`), 929 (backup list).
- deploy/README.md lines 337 and 357 (retirement text and read-only checks), 780 to 862 (the whole "airline registry merge" and "artwork merge" runbook sections: `airline names:` and `artwork:` lines, markers, expand-only, idempotence), 889 (default-type text about "still pending in the per-frame merge"), 910 to 911 (backup list text: per-frame registry and picture entries removed, `retired-legacy`), 948 and 956 to 960 (rollback caveats about per-frame files and pictures).

## Known Stubs

None.

## Threat Flags

None. The CLI reads and renames only under the state directory; it uses `lstat`, never follows a link, and prints ids, sizes and counts.
