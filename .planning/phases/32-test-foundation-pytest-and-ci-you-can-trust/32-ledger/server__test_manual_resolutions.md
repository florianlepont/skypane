# Ledger: server/test_manual_resolutions.py

Baseline: 32-BASELINE/server__test_manual_resolutions.txt (23 checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | load_manual_resolutions() on a nonexistent state dir returns {} without raising | ported | server/test_manual_resolutions.py::test_missing_state_dir_returns_empty_dict_without_raising |
| 2 | load_manual_resolutions() on a file containing invalid JSON returns {} | ported | server/test_manual_resolutions.py::test_invalid_json_returns_empty_dict |
| 3 | load_manual_resolutions() on a JSON list (non-dict top level) returns {} | ported | server/test_manual_resolutions.py::test_non_dict_top_level_returns_empty_dict |
| 4 | load_manual_resolutions() drops an entry whose value is not a dict | ported | server/test_manual_resolutions.py::test_non_dict_entry_value_dropped |
| 5 | load_manual_resolutions() normalises a lowercase key to uppercase and round-trips a valid entry | ported | server/test_manual_resolutions.py::test_lowercase_key_normalised_on_read_and_round_trips |
| 6 | load_manual_resolutions() drops a path-traversal-shaped key and a 4-letter key | ported | server/test_manual_resolutions.py::test_malformed_keys_dropped |
| 7 | load_manual_resolutions() drops a hand-edited entry whose airline_name slugs to a reserved key | ported | server/test_manual_resolutions.py::test_reserved_name_dropped_on_read |
| 8 | add_entry() returns ADD_OK and round-trips through load_manual_resolutions() with a non-empty created_at | ported | server/test_manual_resolutions.py::test_add_entry_round_trips_with_non_empty_created_at |
| 9 | add_entry() rejects a 2-letter prefix with ADD_REJECTED_PREFIX | ported | server/test_manual_resolutions.py::test_add_entry_rejects_2letter_prefix |
| 10 | add_entry() rejects a whitespace-only name with ADD_REJECTED_NAME_EMPTY | ported | server/test_manual_resolutions.py::test_add_entry_rejects_whitespace_only_name |
| 11 | add_entry() rejects a 101-char name with ADD_REJECTED_NAME_TOO_LONG | ported | server/test_manual_resolutions.py::test_add_entry_rejects_101char_name |
| 12 | add_entry() rejects 'Generic Fallback' and 'Generic A320' with ADD_REJECTED_NAME_RESERVED | ported | server/test_manual_resolutions.py::test_add_entry_rejects_reserved_names |
| 13 | add_entry() rejects a new prefix at MANUAL_RESOLUTION_MAX_ENTRIES (ADD_REJECTED_FULL) but allows overwriting an existing one | ported | server/test_manual_resolutions.py::test_add_entry_rejects_new_prefix_at_cap_but_allows_overwrite |
| 14 | delete_entry() returns True once then False on a repeated call, without raising | ported | server/test_manual_resolutions.py::test_delete_entry_returns_true_once_then_false |
| 15 | set_manual_registry_state_dir()/airline_name_for_prefix() cache round-trips and clears on reset to None | ported | server/test_manual_resolutions.py::test_state_dir_cache_round_trips_and_clears_on_reset |
| 16 | entry_rows() returns (prefix, airline_name, created_at) tuples sorted by prefix, skipping a malformed entry | ported | server/test_manual_resolutions.py::test_entry_rows_sorted_and_skips_malformed_entry |
| 17 | delete_entry() leaves the override PNG on disk untouched (D-08), pinned to illustrations.override_path_for_key() | ported | server/test_manual_resolutions.py::test_delete_entry_leaves_override_png_untouched |
| 18 | no manual_resolutions.json.tmp file remains after a successful add_entry() (atomicity proof) | ported | server/test_manual_resolutions.py::test_no_stray_tmp_file_after_successful_add |
| 19 | 20 concurrent add_entry() calls for 20 distinct prefixes (ThreadingHTTPServer's real concurrency shape) all persist durably with no lost update and no stray .tmp file left behind (WR-02) | ported | server/test_manual_resolutions.py::test_concurrent_add_entry_calls_lose_no_updates |
| 20 | load_manual_resolutions() prints a one-line drop-count message whenever it silently rejects an entry or truncates at the cap (naming the real count in both cases) and prints nothing when nothing is dropped (WR-03) | ported | server/test_manual_resolutions.py::test_load_prints_drop_count_for_rejected_and_capped_entries |
| 21 | add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created because the parent directory is read-only — CR-01's exact reproduction case (WR-11) | ported | server/test_manual_resolutions.py::test_add_entry_on_uncreatable_state_dir_returns_failed |
| 22 | delete_entry() returns False (never raises) when the state dir goes read-only mid-write, and the existing entry survives untouched since the write never happened — CR-01's mirror case for delete (WR-11) | ported | server/test_manual_resolutions.py::test_delete_entry_on_unwritable_state_dir_returns_false |
| 23 | add_entry() rejects every name in the hostile-input sweep, leaving the registry empty | ported | server/test_manual_resolutions.py::test_add_entry_rejects_hostile_input_sweep |

Notes: rows 21/22 were the baseline's two root-sandbox FAILs (32-BASELINE/INDEX.md's
"## Notes" - both a pre-existing root-euid environment condition, not a regression). Both are
ported unchanged (same assertion, `tmp_path` in place of `tempfile.TemporaryDirectory()`) with
`@requires_non_root` added (MR-8): under euid 0 they are skipped with an explicit reason
(root ignores read-only directory permission bits, so the write the check expects to fail would
silently succeed instead); under a non-root euid they run and pass, confirmed here with
`runuser -u nobody`.
