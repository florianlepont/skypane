# Ledger: server/test_colour_rules.py

Baseline: 32-BASELINE/server__test_colour_rules.txt (33 checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | load_colour_rules() on a nonexistent state dir returns the empty registry shape without raising | ported | server/test_colour_rules.py::test_missing_state_dir_returns_empty_registry_shape |
| 2 | load_colour_rules() on a file containing invalid JSON returns the empty registry shape | ported | server/test_colour_rules.py::test_invalid_json_returns_empty_registry_shape |
| 3 | load_colour_rules() on a JSON list (non-dict top level) returns the empty registry shape | ported | server/test_colour_rules.py::test_non_dict_top_level_returns_empty_registry_shape |
| 4 | load_colour_rules() on {'callsign': 5} (non-dict kind value) returns the empty registry shape | ported | server/test_colour_rules.py::test_non_dict_kind_value_returns_empty_registry_shape |
| 5 | load_colour_rules() normalises a lowercase callsign key to uppercase and round-trips a valid entry | ported | server/test_colour_rules.py::test_lowercase_callsign_key_normalised_on_read_and_round_trips |
| 6 | load_colour_rules() normalises a lowercase hex key to uppercase on read | ported | server/test_colour_rules.py::test_lowercase_hex_key_normalised_on_read |
| 7 | load_colour_rules() drops a path-traversal-shaped callsign key, a 4-letter prefix, a non-hex hex key, and an unregistered theme_id | ported | server/test_colour_rules.py::test_malformed_entries_dropped_on_read |
| 8 | add_rule() returns ADD_OK_NEW and round-trips through load_colour_rules() with a non-empty created_at | ported | server/test_colour_rules.py::test_add_rule_round_trips_with_non_empty_created_at |
| 9 | add_rule() rejects an unrecognised kind with ADD_REJECTED_KIND | ported | server/test_colour_rules.py::test_add_rule_rejects_unrecognised_kind |
| 10 | add_rule() rejects a 4-letter prefix and a 5-character hex value with ADD_REJECTED_KEY | ported | server/test_colour_rules.py::test_add_rule_rejects_bad_key |
| 11 | add_rule() rejects an unregistered theme id with ADD_REJECTED_THEME | ported | server/test_colour_rules.py::test_add_rule_rejects_unregistered_theme |
| 12 | delete_rule() returns True once then False on a repeated call, without raising | ported | server/test_colour_rules.py::test_delete_rule_returns_true_once_then_false |
| 13 | rule_rows() returns (kind, value, theme_id, created_at) tuples ordered by kind then value, skipping a malformed entry | ported | server/test_colour_rules.py::test_rule_rows_ordered_and_skips_malformed_entry |
| 14 | set_colour_rules_state_dir(None) clears the cache and resolve_effective_theme_id() falls through to the base theme | ported | server/test_colour_rules.py::test_cache_reset_to_none_falls_through_to_base_theme |
| 15 | add_rule() rejects every hostile value in the sweep (write-side) and load_colour_rules() drops the same shapes written directly to disk (read-side), for all three kinds (T-15-01) | ported | server/test_colour_rules.py::test_hostile_input_sweep_rejected_write_and_read |
| 16 | add_rule() distinguishes ADD_OK_NEW from ADD_OK_REPLACED (a replace is not growth) and enforces COLOUR_RULE_MAX_ENTRIES only against new keys (D-09) | ported | server/test_colour_rules.py::test_add_rule_distinguishes_new_from_replaced_and_enforces_cap |
| 17 | no colour_rules.json.tmp file remains after a successful add_rule() or delete_rule() (atomicity proof) | ported | server/test_colour_rules.py::test_no_stray_tmp_file_after_add_and_delete |
| 18 | 20 concurrent add_rule() calls for 20 distinct prefixes (ThreadingHTTPServer's real concurrency shape) all persist durably with no lost update and no stray .tmp file left behind (T-15-02) | ported | server/test_colour_rules.py::test_concurrent_add_rule_calls_lose_no_updates |
| 19 | resolver truth table row 1: no rule, theme_arriving is None, state 'arriving' -> base theme | ported | server/test_colour_rules.py::test_resolver_row1_no_rule_no_override_arriving |
| 20 | resolver truth table row 2: no rule, theme_arriving set, state 'arriving' -> the override | ported | server/test_colour_rules.py::test_resolver_row2_no_rule_override_arriving |
| 21 | resolver truth table row 3: no rule, theme_arriving set, state 'departing' -> base theme | ported | server/test_colour_rules.py::test_resolver_row3_no_rule_override_departing |
| 22 | resolver truth table row 4: a matching prefix rule, no override -> the rule's theme | ported | server/test_colour_rules.py::test_resolver_row4_prefix_rule_no_override |
| 23 | resolver truth table row 5: a matching hex rule and a matching prefix rule -> the hex rule's theme | ported | server/test_colour_rules.py::test_resolver_row5_hex_beats_prefix |
| 24 | resolver truth table row 6: a matching callsign rule and a matching hex rule -> the callsign rule's theme | ported | server/test_colour_rules.py::test_resolver_row6_callsign_beats_hex |
| 25 | resolver truth table row 7: a matching rule of any kind AND theme_arriving set with state 'arriving' -> the rule's theme (a rule beats the override, D-09) | ported | server/test_colour_rules.py::test_resolver_row7_rule_beats_override |
| 26 | resolve_effective_theme_id() never raises for flight=None/{}/non-dict, a None callsign/hex, or a device_cfg with no theme_arriving key, falling through to the base theme | ported | server/test_colour_rules.py::test_resolver_never_raises_on_defensive_inputs |
| 27 | resolve_effective_theme_id() ignores a cached entry whose theme_id is not a member of device_config.THEMES rather than returning it (T-15-05) | ported | server/test_colour_rules.py::test_resolver_ignores_tampered_cache_theme_id |
| 28 | resolve_effective_theme_id() D-02: a calendar_theme_id beats even a matching exact-callsign rule (the accepted consequence) | ported | server/test_colour_rules.py::test_calendar_beats_exact_callsign_rule |
| 29 | resolve_effective_theme_id() D-02: a calendar_theme_id beats a matching hex rule | ported | server/test_colour_rules.py::test_calendar_beats_hex_rule |
| 30 | resolve_effective_theme_id() D-02: a calendar_theme_id beats a matching prefix rule | ported | server/test_colour_rules.py::test_calendar_beats_prefix_rule |
| 31 | resolve_effective_theme_id() D-02: a calendar_theme_id beats the arrivals override (theme_arriving) on an arriving state | ported | server/test_colour_rules.py::test_calendar_beats_arrivals_override |
| 32 | resolve_effective_theme_id() is byte-for-byte identical whether calendar_theme_id is omitted or passed explicitly as None, across a matrix of rule/override configurations | ported | server/test_colour_rules.py::test_backward_compatible_three_positional_call |
| 33 | resolve_effective_theme_id() ignores a calendar_theme_id that is not a member of device_config.THEMES, falling through to the matching rule rather than returning it or the base theme (T-16-TAMPER) | ported | server/test_colour_rules.py::test_tampered_calendar_theme_id_ignored |
