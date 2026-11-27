# Phase 67 plan 24: functions that only tests call

Status: DRAFT FOR OWNER REVIEW. Nothing has been deleted or changed. The Owner column is empty on purpose: it is filled at the plan 24 checkpoint (Task 2), and only names marked DELETE are acted on.

## Summary (plain English)

The plan estimated "about thirty". On the current tree the real count is **27 functions** that production code never calls but tests do. Production code means every tracked file outside `.planning/`, the test files (`test_*.py`, `conftest.py`) and `test-support/`: code, scripts, systemd units, deploy files, JavaScript, HTML, workflows and documents. A name is listed only when no production file mentions it outside its own definition, not even in a comment or a document.

| Group | Names |
|-------|-------|
| A. Fleet state: fleet database (4), sessions (1), device directories (1) | 6 |
| B. Server: hardware registry (2), image container (1), request budget (1), fleet cycle (1), device config (1) | 6 |
| C. Render: giant renderer (4), landscape hold screens (2) | 6 |
| D. Companion app: `draw` (4), throttle, device scope, airline collection, resolve dialog | 8 |
| E. Scripts: firmware release manifest | 1 |
| **Total** | **27** |

What would go if you answered DELETE for everything:

- **Tests that are only about these functions (ONLY): 30 test functions, which are 60 collected test ids** (some are parametrized: for example the image-container decoder test alone is 22 ids). Of these, 7 functions (11 ids) are in Phase 66 audited modules.
- **6 more collected ids** disappear without any test function being deleted: the landscape hold test table has one parameter each for the two `build_*_canvas` builders, in three parametrized tests. The tests themselves stay.
- So the expected drop of the collected-test count is **at most 66 ids** (this bounds the plan 24 floor change; it is smaller if you keep some names).
- **MIXED: 23 of the 27 names** also have at least one test that covers other behaviour. 76 such test functions would be kept and edited (only the assertion or setup line that calls the deleted name goes), plus 17 fixtures or helpers in test files and 6 import or constant lines. The 4 names with no MIXED test are `geofence_resolver`, `regularity_grid`, `sightings_across` and `step_b_trigger_html`.
- **AUDITED (Phase 66 modules): 8 names**: `assign_owner`, `clear_pending_code`, `connect_memory`, `dump_logical`, `create_session`, `wipe_device_dir` (fleet database, sessions, device directories), `selector_value` (`companion/device_scope.py`, in the Phase 66 review scope) and `size_bound` (`scripts/fw_release_manifest.py`, same). They need your explicit tick per name.
- **REWRITE: 1 name**, `create_session`: two files under `test-support/` and ten companion or stub-server fixtures call it; deleting it means replacing the session setup helper of the whole session test suite.

Things worth knowing before you decide:

1. Three names are not "dead helpers" but quiet safety nets: `registry_problems` (the only check of hardware registry invariants), `assert_giant_palette` (the legal-palette check behind 15 render tests and the golden render test helper) and `wipe_device_dir` (its four tests are refusal and symlink-safety tests of an audited module). Deleting the function deletes the check.
2. `connect_memory`, `create_session`, `dump_logical`, `decode_container` and `assert_giant_palette` are used as setup or comparison helpers by many tests. They are listed because production never calls them, but deleting them is a test-suite rewrite, not a clean-up.
3. Cleanest candidates (no audited module, no MIXED test, no fixture role): `geofence_resolver`, `regularity_grid`, `sightings_across`, `step_b_trigger_html`, and the four `day_band` tests.

## Scope and exclusions

Excluded on purpose (plan 22 owns them, they are not in the table):

- excluded: `fleet_db.delete_location_if_unused`, `fleet_db.count_locations_owned`, `fleet_db.location_usage_counts`
- excluded: everything about `wake_epochs`, including `record_wake_epoch` and `META_LAST_POLL_TRIGGER`
- excluded by rule: constants and i18n labels, signature-required overrides (`log_message`, `do_HEAD`, `do_POST`, `handle_error`) and anything read by reflection or a catalogue scan, for example `components_page.catalogued_helpers` (its tests scan the module by reflection).

Also left out because they are not production code: `companion/airline_fleet_world.py` (`artwork_png`, `World`) is a test world builder that lives in the `companion/` directory; it is only used by tests.

## Table

Legend:

- `PS name` is the production search defined in the reproduction section below. The result "only the definition line" was checked for every row.
- **ONLY**: the test is about this function alone; it would be deleted. MIXED: the test also covers other behaviour; it is kept and edited. Parametrized tests list the function; the count of ids is in the summary.
- AUDITED: module in Phase 66 scope; needs your explicit tick. REWRITE: used by a non-test file under `test-support/`; deleting needs a fixture rewrite.
- Owner: DELETE or KEEP, to be filled by the owner.

| # | Name | Module and line | Production references | Calling tests | Flags | Notes | Owner |
|---|------|-----------------|-----------------------|---------------|-------|-------|-------|
| 1 | `assign_owner` | `server/fleet_db.py:1170` | `PS assign_owner`: only the definition line | `server/test_fleet_co_manager_cascades.py::test_assign_owner_to_a_co_manager_fails_closed` **ONLY**<br>`server/test_fleet_db.py::test_single_owner_column_and_reassignment` MIXED | AUDITED | Owner reassignment goes through fleet_ops in production; this raw DB call is only exercised by two tests. The co-manager test checks a database integrity trigger through it. | |
| 2 | `clear_pending_code` | `server/fleet_db.py:1530` | `PS clear_pending_code`: only the definition line | `server/test_fleet_schema3.py::test_pending_code_touch_and_delete` MIXED | AUDITED | One lifecycle test uses it as one step among many pending-code operations. | |
| 3 | `connect_memory` | `server/fleet_db.py:397` | `PS connect_memory`: only the definition line | `server/test_fleet_db.py::test_connect_memory_is_migrated` **ONLY**<br>`server/test_fleet_db.py::test_transaction_commits_and_rolls_back` MIXED<br>`server/test_fleet_db.py::conn` MIXED (helper or fixture used by other tests)<br>`server/test_fleet_db.py::test_sessions_principal_user_id_check` MIXED<br>`server/test_fleet_db.py::test_get_device_owner` MIXED<br>`server/test_fleet_frame_position.py::conn` MIXED (helper or fixture used by other tests)<br>`server/test_fleet_sessions.py::conn` MIXED (helper or fixture used by other tests) | AUDITED | The in-memory database used as the `conn` fixture of three whole test files; deleting it means every test in those files needs a replacement fixture. | |
| 4 | `dump_logical` | `server/fleet_db.py:1315` | `PS dump_logical`: only the definition line | `deploy/tests/test_backup.py::test_restore_carries_pending_audit_and_location_owner` MIXED<br>`server/test_fleet_db.py::test_tokens_registry_and_removal` MIXED<br>`server/test_fleet_migrate.py::_logical` MIXED (helper or fixture used by other tests)<br>`server/test_fleet_ops.py::test_busy_guard_blocks_every_wipe` MIXED<br>`server/test_fleet_ops.py::test_failure_during_wipe_rolls_back_reassign` MIXED<br>`server/test_fleet_ops.py::test_failed_commit_restores_the_directory_and_the_database` MIXED<br>`server/test_fleet_ops.py::test_reactivate_failure_before_commit_restores_the_directory` MIXED<br>`server/test_fleet_schema3.py::test_old_databases_upgrade_in_place_keeping_rows` MIXED<br>`server/test_fleet_schema4.py::test_migrating_again_is_a_noop_and_concurrent_upgraders_agree` MIXED | AUDITED | Logical dump used as the comparison helper in backup, migration and wipe tests; no test is about it alone. | |
| 5 | `create_session` | `server/fleet_sessions.py:69` | `PS create_session`: only the definition line | `companion/test_account_page.py::_seed_session` MIXED (helper or fixture used by other tests)<br>`companion/test_account_page.py::fleet_server` MIXED (helper or fixture used by other tests)<br>`companion/test_console_shell.py::served` MIXED (helper or fixture used by other tests)<br>`companion/test_console_shell.py::test_the_console_sidebar_lists_the_console_pages_for_the_frame_in_view` MIXED<br>`companion/test_csrf.py::probe` MIXED (helper or fixture used by other tests)<br>`companion/test_device_scope_owner.py::http_fleet` MIXED (helper or fixture used by other tests)<br>`companion/test_nav_personal_console.py::served` MIXED (helper or fixture used by other tests)<br>`companion/test_nav_personal_console.py::test_a_user_with_no_frame_has_no_bar_and_an_account_only_sidebar` MIXED<br>`companion/test_personal_space_parity.py::parity` MIXED (helper or fixture used by other tests)<br>`companion/test_sessions_http.py::_seed_user_session` MIXED (helper or fixture used by other tests)<br>`companion/test_space_switch.py::served` MIXED (helper or fixture used by other tests)<br>`server/test_fleet_sessions.py::test_create_stores_hash_and_lookup_by_hash_only` MIXED<br>`server/test_fleet_sessions.py::test_legacy_admin_row_never_authenticates_and_is_deleted` MIXED<br>`server/test_fleet_sessions.py::test_absolute_lifetime` MIXED<br>`server/test_fleet_sessions.py::test_idle_timeout` MIXED<br>`server/test_fleet_sessions.py::test_last_seen_is_throttled` MIXED<br>`server/test_fleet_sessions.py::test_role_and_disabled_are_read_fresh` MIXED<br>`server/test_fleet_sessions.py::test_missing_user_row_refuses` MIXED<br>`server/test_fleet_sessions.py::test_rotation_delete_and_prune` MIXED<br>`server/test_fleet_sessions.py::test_unlink_identity_clears_link_and_sessions` MIXED<br>`server/test_fleet_sessions.py::test_sessions_and_linking_do_not_touch_devices` MIXED<br>`server/test_fleet_sessions.py::test_lookup_works_on_an_immutable_read_only_store` MIXED<br>`server/test_fleet_sessions.py::test_expired_sessions_read_as_none_on_a_read_only_store` MIXED<br>`server/test_fleet_sessions.py::test_sign_in_user_rolls_the_link_back_when_the_session_cannot_be_stored` MIXED<br>`server/test_fleet_sessions.py::test_session_creation_prunes_dead_sessions_at_most_hourly` MIXED<br>`server/test_fleet_sessions.py::test_sign_in_prunes_dead_sessions_too` MIXED<br>`stub-server/test_fleet_cli.py::_link_and_session` MIXED (helper or fixture used by other tests)<br>`test-support/access_matrix_support.py::session_cookie_for` MIXED (helper or fixture used by other tests)<br>`test-support/companion_app_server.py::session_cookie_for_state_dir` MIXED (helper or fixture used by other tests) | AUDITED, REWRITE | Setup call of the 15 tests of `test_fleet_sessions.py`, 3 more tests and of two test-support fixtures (`test-support/access_matrix_support.py`, `test-support/companion_app_server.py`) plus 10 companion/stub-server fixtures. Production writes sessions through `_insert_session` / `sign_in_user`. Deleting it deletes the setup of the Phase 66 session security tests. | |
| 6 | `wipe_device_dir` | `server/device_dirs.py:163` | `PS wipe_device_dir`: only the definition line | `server/test_device_dirs.py::test_wipe_removes_the_whole_tree_and_allows_reprovision` **ONLY**<br>`server/test_device_dirs.py::test_wipe_refuses_the_live_path_and_keeps_root_files` **ONLY**<br>`server/test_device_dirs.py::test_wipe_refuses_bad_shapes` **ONLY**<br>`server/test_device_dirs.py::test_wipe_refuses_a_symlinked_directory_and_spares_the_target` **ONLY**<br>`server/test_fleet_ops.py::test_reassign_live_frame_changes_only_owner` MIXED<br>`server/test_fleet_ops.py::test_unavailable_new_owner_before_any_wipe` MIXED | AUDITED | The four tests in `test_device_dirs.py` are the refusal tests (bad shapes, live path, symlink) of a safety check, so they are security tests of the audited module. Two `test_fleet_ops.py` tests monkeypatch the name and would fail with AttributeError once it is gone. | |
| 7 | `provenance_for` | `server/hardware.py:84` | `PS provenance_for`: only the definition line | `server/test_hardware.py::test_legacy_provenance_covers_every_value_as_provisional` **ONLY**<br>`server/test_hardware.py::test_provenance_for_unknown_name_raises` **ONLY**<br>`server/test_hardware.py::test_sim_landscape_provenance_says_copied_and_keeps_values` MIXED<br>`server/test_hardware.py::test_planned_slot_has_no_numbers_and_provisional_registration` MIXED<br>`server/test_hardware.py::test_evaluation_battery_is_copied_and_provisional` MIXED | - | Lookup of a battery value provenance entry; the `provenance` data itself stays. | |
| 8 | `registry_problems` | `server/hardware.py:388` | `PS registry_problems`: only the definition line | `server/test_hardware.py::test_every_profile_has_six_inks_and_a_valid_layout` MIXED<br>`server/test_hardware.py::test_validation_rejects_bad_layout_and_portrait_size` **ONLY**<br>`server/test_hardware.py::test_validation_rejects_final_without_measurement_source` **ONLY**<br>`server/test_hardware.py::test_evaluation_battery_is_copied_and_provisional` MIXED<br>`server/test_visible_window.py::test_only_the_evaluation_profile_has_a_window` MIXED | - | Hardware registry validator that no production code runs: deleting it removes the only check of registry invariants (inks, layout, final-needs-source). | |
| 9 | `decode_container` | `server/image_container.py:98` | `PS decode_container`: only the definition line | `server/test_image_container.py::test_decoder_agrees_with_manifest` **ONLY**<br>`server/test_image_container.py::test_encoder_reproduces_committed_valid_fixture` MIXED<br>`server/test_image_container.py::test_full_size_container_matches_manifest` MIXED<br>`server/test_image_container.py::test_every_truncated_prefix_is_rejected` **ONLY**<br>`server/test_image_container.py::test_odd_pixel_count_rounds_payload_up` MIXED<br>`server/test_image_container.py::test_zero_panel_size_is_an_argument_error` MIXED<br>`stub-server/test_device_fleet.py::test_negotiation_announcing_device_gets_container_with_profile_size` MIXED<br>`stub-server/test_device_fleet.py::test_negotiation_announcing_clone_gets_full_size_container` MIXED<br>`stub-server/test_device_fleet.py::test_polled_landscape_image_is_served_raw_and_as_container` MIXED<br>`stub-server/test_image_negotiation.py::test_announce_serves_the_container` MIXED<br>`stub-server/test_pending_pairing.py::test_container_is_served_when_announced` MIXED | - | Inverse of the container encoder; HTTP tests use it to verify served bodies. The encoder (production) keeps its own tests. | |
| 10 | `paused_until` | `server/request_budget.py:220` | `PS paused_until`: only the definition line | `server/test_request_budget.py::test_pause_is_honoured_by_another_instance` MIXED<br>`server/test_request_budget.py::test_unknown_provider_failure_is_ignored` MIXED<br>`server/test_zone_fetch.py::test_failing_provider_is_paused_and_other_still_answers` MIXED | - | Read accessor of the pause state; all three tests use it as the observation point of pause behaviour. | |
| 11 | `geofence_resolver` | `server/fleet_cycle.py:249` | `PS geofence_resolver`: only the definition line | `server/test_fleet_cycle.py::test_default_resolver_gives_every_device_the_geofence_zone` **ONLY**<br>`server/test_fleet_cycle.py::test_default_resolver_with_missing_geofence_raises_oserror` **ONLY** | - | Default resolver factory; both tests exercise only it. | |
| 12 | `runway_empty_heading` | `server/device_config.py:537` | `PS runway_empty_heading`: only the definition line | `server/test_render.py::test_empty_canvas_draws_selected_runways_heading` MIXED<br>`server/test_render.py::test_runway_tag_text_legacy_ids_keep_their_exact_text` MIXED | - | Both tests use it as a helper inside a wider rendering or text test. | |
| 13 | `assert_giant_palette` | `server/plane/render/giant/palette_check.py:16` | `PS assert_giant_palette`: only the definition line | import or constant at `server/test_giant_compose.py:13` (MIXED, needs an edit)<br>`server/test_giant_compose.py::test_layout_renders_legally_with_lettering` MIXED<br>`server/test_giant_compose.py::test_each_state_renders` MIXED<br>`server/test_giant_compose.py::test_unknown_route_renders` MIXED<br>import or constant at `server/test_giant_dispatch.py:15` (MIXED, needs an edit)<br>`server/test_giant_dispatch.py::test_stored_theme_resolves_to_its_pairing` MIXED<br>`server/test_giant_dispatch.py::test_a_calendar_theme_reaches_the_giant_canvas` MIXED<br>import or constant at `server/test_giant_landscape.py:10` (MIXED, needs an edit)<br>`server/test_giant_landscape.py::test_renders_legally_at_the_profile_size` MIXED<br>`server/test_giant_landscape.py::test_name_of_three_letters_is_one_line` MIXED<br>`server/test_giant_landscape.py::test_status_marks_change_the_picture` MIXED<br>import or constant at `server/test_giant_layout_c.py:10` (MIXED, needs an edit)<br>`server/test_giant_layout_c.py::test_renders_legally_for_every_pairing` MIXED<br>`server/test_giant_lettering.py::test_yellow_light_field_passes_the_giant_check_but_not_the_legacy_one` MIXED<br>`server/test_giant_lettering.py::test_every_pairing_field_passes_the_giant_check` **ONLY**<br>`server/test_giant_lettering.py::test_out_of_palette_index_is_rejected` **ONLY**<br>`server/test_giant_lettering.py::test_dominant_index_must_be_field_ink_or_white` **ONLY**<br>import or constant at `server/test_giant_status.py:8` (MIXED, needs an edit)<br>`server/test_giant_status.py::test_every_kind_renders_with_legal_palette` MIXED<br>import or constant at `server/test_golden_giant_render.py:32` (MIXED, needs an edit)<br>`server/test_golden_giant_render.py::_flight` MIXED (helper or fixture used by other tests) | - | Palette-legality assertion used by 15 render tests and by the golden render test helper (`test_golden_giant_render.py::_flight`; the golden fixtures are not touched, but the test file would be edited). Deleting it removes the legal-palette check of every giant render. | |
| 14 | `fuselage_median` | `server/plane/render/giant/aircraft.py:78` | `PS fuselage_median`: only the definition line | `server/test_giant_aircraft.py::test_cut_goes_through_bare_fuselage` MIXED<br>`server/test_giant_aircraft.py::test_cut_avoids_a_wide_wing_in_synthetic_art` MIXED | - | Helper used as the last assertion of two cut-position tests. | |
| 15 | `whole_aircraft` | `server/plane/render/giant/aircraft.py:231` | `PS whole_aircraft`: only the definition line | `server/test_giant_aircraft.py::test_whole_aircraft_fits_and_centres_in_the_box` **ONLY**<br>`server/test_giant_aircraft.py::test_whole_aircraft_paints_clean_palette` MIXED | - | Layout-fit helper; `paint_aircraft` has its own path in production. | |
| 16 | `line_mask` | `server/plane/render/giant/lettering.py:81` | `PS line_mask`: only the definition line | `server/test_giant_lettering.py::test_line_mask_is_exact_size_and_strictly_binary` **ONLY**<br>`server/test_giant_lettering.py::test_line_fills_the_slot_edge_to_edge` **ONLY**<br>`server/test_giant_lettering.py::test_empty_and_oversized_lines_are_rejected` MIXED | - | Single-line lettering mask; production paints via `paint_lines`. One of the three tests also checks `paint_lines` rejection. | |
| 17 | `build_no_connection_canvas` | `server/plane/render/landscape_hold.py:156` | `PS build_no_connection_canvas`: only the definition line | `server/test_render_landscape_hold.py::test_size_packing_palette[no_connection]` MIXED (the parameter goes, the test stays)<br>`server/test_render_landscape_hold.py::test_deterministic[no_connection]` MIXED (same)<br>`server/test_render_landscape_hold.py::test_other_even_size[no_connection]` MIXED (same) | - | Two entries of the `BUILDERS` table of `test_render_landscape_hold.py`; deleting both builders removes parametrized ids, not test functions (see summary). | |
| 18 | `build_updating_canvas` | `server/plane/render/landscape_hold.py:164` | `PS build_updating_canvas`: only the definition line | `server/test_render_landscape_hold.py::test_size_packing_palette[updating]` MIXED (the parameter goes, the test stays)<br>`server/test_render_landscape_hold.py::test_deterministic[updating]` MIXED (same)<br>`server/test_render_landscape_hold.py::test_other_even_size[updating]` MIXED (same) | - | Same table as above. | |
| 19 | `percent_y` | `companion/draw.py:249` | `PS percent_y`: only the definition line | `companion/test_companion_app_02.py::test_draw_module_scales_clamp_and_never_raise` MIXED | - | One assertion group inside a test that covers all the `draw` scale helpers. | |
| 20 | `label_span` | `companion/draw.py:493` | `PS label_span`: only the definition line | `companion/test_companion_app_02.py::test_draw_module_emits_no_script_and_no_external_reference` MIXED<br>`companion/test_companion_app_02.py::test_draw_module_escapes_every_interpolated_value` MIXED | - | One sample in two `draw`-wide tests (no script, escaping). | |
| 21 | `day_band` | `companion/draw.py:668` | `PS day_band`: only the definition line | `companion/test_view_pages_04.py::test_day_band_time_scale_places_by_when_not_by_index` **ONLY**<br>`companion/test_view_pages_04.py::test_day_band_night_window_shades_the_night_as_two_spans` **ONLY**<br>`companion/test_view_pages_04.py::test_day_band_collapses_crowded_marks_and_reports_exactly_how_many` **ONLY**<br>`companion/test_view_pages_04.py::test_day_band_emits_only_registered_classes_and_no_colour` **ONLY**<br>comment mention only in `test-support/computed_style_snapshot.py:197` (no code use) | - | Four tests, all about the day band; `test-support/computed_style_snapshot.py` only mentions it in a comment (the comment would go stale, no code use). | |
| 22 | `regularity_grid` | `companion/draw.py:854` | `PS regularity_grid`: only the definition line | `companion/test_status_pages_02.py::test_regularity_grid_has_four_states_and_never_conflates_them` **ONLY**<br>`companion/test_status_pages_02.py::test_regularity_grid_cells_are_sized_from_the_360px_floor` **ONLY**<br>`companion/test_status_pages_02.py::test_regularity_grid_is_bounded_and_keeps_the_newest_buckets` **ONLY** | - | Three tests, all about the regularity grid. | |
| 23 | `key_count` | `companion/throttle.py:93` | `PS key_count`: only the definition line | `companion/test_console_utils.py::test_success_clears_the_counter_and_reset_clears_everything` MIXED<br>`companion/test_console_utils.py::test_table_never_exceeds_max_keys_and_a_locked_key_outlives_idle_ones` MIXED<br>`companion/test_console_utils.py::test_idle_keys_are_evicted_before_least_recently_seen_locked_ones` MIXED | - | Observation point (table size) of three throttle tests whose subject is the bounded table. | |
| 24 | `selector_value` | `companion/device_scope.py:443` | `PS selector_value`: only the definition line | `companion/test_device_scope_owner.py::test_a_user_who_owns_the_live_frame_gets_real_id_urls` MIXED<br>`companion/test_device_scope_owner.py::test_an_admin_addresses_a_live_frame_with_a_fleet_row_by_its_id` MIXED<br>`companion/test_device_scope_owner.py::test_a_live_frame_without_a_fleet_row_stays_unprefixed` MIXED | AUDITED | Last assertion in three device-scope URL tests. `device_scope.py` was in the Phase 66 review scope. | |
| 25 | `sightings_across` | `companion/airline_collection.py:250` | `PS sightings_across`: only the definition line | `companion/test_airline_collection.py::test_sightings_across_frames_are_merged_newest_first_and_counted_together` **ONLY** | - | One test about merging history across frames; the second half re-tests `collection_from_events` on its result. | |
| 26 | `step_b_trigger_html` | `companion/resolve_dialog.py:65` | `PS step_b_trigger_html`: only the definition line | `companion/test_device_links.py::test_step_b_trigger_addresses_stay_in_the_device_and_return_stays_plain` **ONLY** | - | One test. | |
| 27 | `size_bound` | `scripts/fw_release_manifest.py:200` | `PS size_bound`: only the definition line | `deploy/tests/test_release_manifest.py::test_size_bound_is_the_legacy_slot_and_the_profile_bound` MIXED<br>`deploy/tests/test_release_manifest.py::test_evaluation_type_size_bound_is_its_profile_bound` **ONLY** | AUDITED | Firmware size bound per hardware profile. `scripts/fw_release_manifest.py` was in the Phase 66 review scope. | |

## Considered and not listed

- Names that vulture rates 60 percent but that have a production reference: `ring_gauge`, `safe_health_state`, `classify_check_in_gap`, `render_panel`, `lookup_route` (called from code or other modules), and `resolve_login`, `check_in_gaps`, `getcode`, `theme_label`, `next_wake_at_iso`, `draw_frame`, `runway_label`, `_build_no_connection_canvas`, `_build_updating_canvas`. For the second group the only non-definition mentions found by a line-kind check are comments, docstrings, documents, re-export or import lines. By the strict rule (no mention at all in production) they do not qualify; they would qualify under a relaxed rule "no call from production code". Say so at the checkpoint if you want them added.
- Names with no reference anywhere (not even in tests): `airport_label` (`companion/detection_summary.py`), `battery_dropped` (`companion/health_signals.py`), the property `FleetResult.live_outcome` (`server/fleet_cycle.py`). These are dead code, not test-only API, and belong to the plain dead-code work, not to this list.
- Throwaway design scripts under `design-exploration/` (`fit_font`, `v05` to `v10`): not production, no tests.
- Method names shared with unrelated code (`reset`, `take`) are never counted as unique references.

## Reproduce

All commands are run from the repository root. Vulture is only a cross-check; the list comes from the scan below, which counts every word-boundary mention in tracked text files.

```bash
# 1. Vulture cross-check (installed in the untracked server/.venv only; never added to a requirements file)
server/.venv/bin/vulture server stub-server companion scripts deploy hardware \
  --min-confidence 60 --exclude '*/.venv/*,*/test_*.py,*/conftest.py'

# 2. Production search used in the table (tracked files only; tests, test-support and .planning excluded)
PS() { git grep -nw -e "$1" -- . ':!.planning' ':!**/test_*.py' ':!**/conftest.py' ':!test-support'; }

# 3. Full derivation: every def in a production .py file whose name has no mention outside its own
#    definition in any production tracked text file; then the test and test-support mentions.
git ls-files > files.txt
server/.venv/bin/python derive.py files.txt cands.json   # derive.py is reproduced below
```

`derive.py`:

```python
import ast, re, json, sys, os
from collections import defaultdict
ROOT = os.getcwd()
files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
TEXT = ('.py', '.sh', '.service', '.timer', '.js', '.html', '.yml', '.yaml', '.md', '.toml', '.cfg', '.txt', '.c', '.h', '.json', '.css', '.conf', '.ini', '.in', '.sample')
files = [f for f in files if not f.startswith('.planning/') and f.endswith(TEXT) and os.path.isfile(f)]


def is_test(f):
    b = os.path.basename(f)
    return (b.startswith('test_') or b.endswith('_test.py') or b == 'conftest.py'
            or f.startswith('test-support/') or '/testdata/' in f or '/fixtures/' in f
            or b.startswith('test_'))


def is_support(f):
    return f.startswith('test-support/') and not os.path.basename(f).startswith('test_')


text = {}
for f in files:
    try:
        text[f] = open(f, encoding='utf-8').read()
    except Exception:
        pass
prod = [f for f in text if not is_test(f)]
tests = [f for f in text if is_test(f)]

defs = []  # (name, file, line, end, kind, cls)
for f in prod:
    if not f.endswith('.py'):
        continue
    try:
        tree = ast.parse(text[f])
    except SyntaxError:
        continue

    def walk(node, cls=None):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.append((ch.name, f, ch.lineno, ch.end_lineno, 'method' if cls else 'function', cls))
                walk(ch, cls)
            elif isinstance(ch, ast.ClassDef):
                walk(ch, ch.name)
            else:
                walk(ch, cls)
    walk(tree)

by_name = defaultdict(list)
for d in defs:
    by_name[d[0]].append(d)
W = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
idx = defaultdict(lambda: defaultdict(list))  # name -> file -> [lines]
for f, t in text.items():
    for i, line in enumerate(t.splitlines(), 1):
        for w in set(W.findall(line)):
            if w in by_name:
                idx[w][f].append(i)
res = []
for name, ds in sorted(by_name.items()):
    if name.startswith('__') and name.endswith('__'):
        continue
    prodrefs = []
    trefs = {}
    for f, lines in idx[name].items():
        if is_test(f):
            trefs[f] = lines
        else:
            for i in lines:
                if not any(d[1] == f and d[2] <= i <= d[3] for d in ds):
                    prodrefs.append((f, i))
    if prodrefs:
        continue
    res.append(dict(name=name, defs=[(d[1], d[2], d[5]) for d in ds], tests=trefs))
json.dump(res, open(sys.argv[2], 'w'), indent=1)
print(len(res), 'zero-prod-ref names;', sum(1 for r in res if r['tests']), 'with test refs')
```

Calling test ids were obtained by mapping each mention line to its enclosing function with `ast`, then reading the test bodies to decide ONLY versus MIXED. The collected-id counts come from `pytest --collect-only -q` on the affected files.
