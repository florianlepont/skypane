# Ledger: server/test_plane_detection.py

Baseline: 32-BASELINE/server__test_plane_detection.txt (47 checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | filter_in_geofence drops out-of-bbox and position-less records | ported | server/test_plane_detection.py::test_filter_in_geofence_drops_out_of_bbox_and_positionless |
| 2 | select_runway3_aircraft picks 39d300 (450ft beats 800ft) | ported | server/test_plane_detection.py::test_select_runway3_aircraft_picks_lowest_altitude |
| 3 | select_runway3_aircraft: on-ground beats 800ft airborne | ported | server/test_plane_detection.py::test_select_runway3_aircraft_on_ground_beats_airborne |
| 4 | select_runway3_aircraft returns None for an empty snapshot | ported | server/test_plane_detection.py::test_select_runway3_aircraft_empty_returns_none |
| 5 | selected record's callsign is stripped of trailing padding | ported | server/test_plane_detection.py::test_selected_record_callsign_is_stripped |
| 6 | select_runway3_aircraft is deterministic under input reordering | ported | server/test_plane_detection.py::test_select_runway3_aircraft_deterministic_under_shuffle |
| 7 | select_runway3_aircraft: multi-aircraft winner's aircraft_type is B738 | ported | server/test_plane_detection.py::test_multi_aircraft_winner_has_aircraft_type |
| 8 | select_runway3_aircraft: on-ground winner's aircraft_type is A320 | ported | server/test_plane_detection.py::test_on_ground_winner_has_aircraft_type |
| 9 | select_runway3_aircraft: a record with no t key yields aircraft_type None | ported | server/test_plane_detection.py::test_no_type_key_yields_none |
| 10 | select_runway3_aircraft: malformed type values all yield aircraft_type None without raising | ported | server/test_plane_detection.py::test_malformed_type_values_never_raise |
| 11 | real wrong-runway record 39de4a is in-bbox and below-ceiling (the pre-fix accept condition) | ported | server/test_plane_detection.py::test_wrong_runway_fixture_reproduces_the_precondition |
| 12 | select_runway3_aircraft rejects the real runway-20 departure 39de4a (the reported false positive) | ported | server/test_plane_detection.py::test_wrong_runway_is_rejected |
| 13 | select_runway3_aircraft still selects the real runway-25 arrival 347288 (no over-tightening) | ported | server/test_plane_detection.py::test_real_runway3_arrival_is_still_selected |
| 14 | with both real aircraft present, only the genuine runway-3 arrival is a candidate | ported | server/test_plane_detection.py::test_wrong_runway_loses_to_real_one |
| 15 | runway_axis/along_cross_track_m are derived from the published thresholds | ported | server/test_plane_detection.py::test_axis_is_derived_from_published_thresholds |
| 16 | track_axis_deviation_deg is bidirectional and rejects bools/non-numerics | ported | server/test_plane_detection.py::test_track_deviation_is_bidirectional_and_type_safe |
| 17 | runway 06/24's published thresholds are rejected by the corridor gate, not the track gate | ported | server/test_plane_detection.py::test_corridor_is_what_rejects_runway_06_24 |
| 18 | runway 02/20's centreline crossing is rejected by the track gate, not the corridor gate | ported | server/test_plane_detection.py::test_track_gate_is_what_rejects_runway_02_20 |
| 19 | a record with no track is corridor-gated rather than rejected outright | ported | server/test_plane_detection.py::test_missing_track_does_not_disqualify |
| 20 | default poll (no providers arg) queries adsb.fi then adsb.lol | ported | server/test_plane_detection.py::test_default_poll_queries_adsbfi_then_adsblol |
| 21 | airplaneslive remains a selectable opt-in, absent from the default order | ported | server/test_plane_detection.py::test_airplaneslive_still_opt_in |
| 22 | poll_current_aircraft: two agreeing providers yield corroborated=True | ported | server/test_plane_detection.py::test_agreeing_providers_are_corroborated |
| 23 | poll_current_aircraft: disagreeing providers select nothing (doubt -> D-04 hold) | ported | server/test_plane_detection.py::test_disagreeing_providers_yield_nothing |
| 24 | poll_current_aircraft: an unreachable provider is not scored as disagreement | ported | server/test_plane_detection.py::test_single_reachable_provider_is_uncorroborated_not_suppressed |
| 25 | poll_current_aircraft (default order): adsb.fi and adsb.lol agreeing yields corroborated=True with adsb.fi's record | ported | server/test_plane_detection.py::test_default_order_corroborates |
| 26 | poll_current_aircraft (default order): adsb.fi and adsb.lol disagreeing select nothing | ported | server/test_plane_detection.py::test_default_order_disagreement_yields_nothing |
| 27 | poll_current_aircraft (default order): adsb.lol unreachable degrades to single-source, not suppressed | ported | server/test_plane_detection.py::test_default_order_degrades_to_single_source |
| 28 | query_provider: adsb.fi and adsb.lol response keys are never interchanged (proven through the transport) | ported | server/test_plane_detection.py::test_provider_keys_are_not_interchanged |
| 29 | the taxiing masking record is in-bbox, track-aligned, inside the airborne corridor and outranks the real arrival (the pre-fix accept condition) | ported | server/test_plane_detection.py::test_masking_fixture_reproduces_the_precondition |
| 30 | select_runway3_aircraft: a taxiing aircraft off the pavement no longer masks a real runway-3 movement | ported | server/test_plane_detection.py::test_taxiing_aircraft_no_longer_masks_real_runway3_traffic |
| 31 | the on-ground gate keeps the real runway-3 ground record (+31m) and rejects the documented 150m residual | ported | server/test_plane_detection.py::test_ground_gate_keeps_real_runway3_ground_traffic |
| 32 | the pavement pair ties at effective altitude 0.0, is identical across both feeds except seen_pos, and the pre-fix key still splits them (the manufactured-disagreement precondition) | ported | server/test_plane_detection.py::test_pavement_pair_reproduces_the_precondition |
| 33 | select_runway3_aircraft: two feeds differing only in seen_pos select the SAME aircraft | ported | server/test_plane_detection.py::test_selection_is_provider_independent |
| 34 | poll_current_aircraft (default order): two feeds differing only in seen_pos are corroborated, not suppressed | ported | server/test_plane_detection.py::test_identical_sets_are_not_manufactured_into_disagreement |
| 35 | poll_current_aircraft (default order): unequal candidate sets corroborate the common aircraft instead of suppressing (a stable tie-break alone would not have) | ported | server/test_plane_detection.py::test_asymmetric_sets_corroborate_the_common_aircraft |
| 36 | poll_current_aircraft: genuinely disjoint candidate sets still suppress the cycle (D-04 intact) | ported | server/test_plane_detection.py::test_genuinely_disjoint_sets_still_suppress |
| 37 | poll_current_aircraft: the disagreement line names every candidate each feed saw, not just the winners | ported | server/test_plane_detection.py::test_disagreement_line_names_every_candidate |
| 38 | runways['3'] duplicates the legacy runway/corridor blocks exactly (drift guard) | ported | server/test_plane_detection.py::test_runways_3_matches_legacy_blocks |
| 39 | runway_axis(geofence) matches runway_axis(geofence, runway_id='3') | ported | server/test_plane_detection.py::test_default_runway_id_matches_explicit_default |
| 40 | runway_axis: 06-24/02-20 computed bearings match their published true headings | ported | server/test_plane_detection.py::test_neighbouring_runway_bearings_match_published_headings |
| 41 | runway_axis(runway_id='totally-unknown') falls back to the default runway's axis (T-06-02-01) | ported | server/test_plane_detection.py::test_unknown_runway_id_falls_back_to_default_axis |
| 42 | corridor_params(runway_id='02-20') matches the file, negative entries fall back to the default | ported | server/test_plane_detection.py::test_corridor_params_for_02_20_and_malformed_fallback |
| 43 | select_aircraft_for_runway positively tracks 06-24 and 02-20 on their own centrelines | ported | server/test_plane_detection.py::test_positive_tracking_on_neighbouring_runways |
| 44 | the real runway-3 fixture is excluded from runway 06-24's gate (exclusive both ways) | ported | server/test_plane_detection.py::test_real_runway3_fixture_excluded_from_06_24 |
| 45 | selected_runway equals the requested id, or the default id on an unrecognised request | ported | server/test_plane_detection.py::test_selected_runway_key_reports_effective_id |
| 46 | filter_in_geofence tags carry on_runway and the deprecated on_runway3 alias correctly | ported | server/test_plane_detection.py::test_on_runway_and_deprecated_alias_tags |
| 47 | poll_current_aircraft diagnostics distinguishes all-providers-failed from a real selection | ported | server/test_plane_detection.py::test_diagnostics_distinguishes_all_failed_from_no_selection |
