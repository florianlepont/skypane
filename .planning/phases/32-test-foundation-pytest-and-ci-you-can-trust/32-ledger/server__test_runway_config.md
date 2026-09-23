# Ledger: server/test_runway_config.py

Baseline: 32-BASELINE/server__test_runway_config.txt (15 checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | real fixture track_arrival_440cb1: -640 seeded with no prior state -> arriving | ported | server/test_runway_config.py::test_real_track_first_observation_arriving |
| 2 | real fixture track_arrival_440cb1: first +48 flare reading holds arriving (real landing, not a bug) | ported | server/test_runway_config.py::test_real_track_first_flare_holds |
| 3 | real fixture track_arrival_440cb1: second +48 flare reading still holds arriving (real landing, not a bug) | ported | server/test_runway_config.py::test_real_track_second_flare_holds |
| 4 | +48 seeded with no prior confirmed state returns None (nothing to hold) | ported | server/test_runway_config.py::test_no_prior_state_inside_deadband_returns_none |
| 5 | SYNTHETIC (A-02-02-01, no real departure observed): +200 seeded None -> departing (inclusive boundary) | ported | server/test_runway_config.py::test_synthetic_climb_threshold_departs |
| 6 | SYNTHETIC (A-02-02-01, no real departure observed): +199 holds last confirmed state (just inside deadband) | ported | server/test_runway_config.py::test_synthetic_just_below_climb_threshold_holds |
| 7 | real-data-backed boundary: -200 seeded None -> arriving (inclusive boundary) | ported | server/test_runway_config.py::test_descend_threshold_arrives |
| 8 | real-data-backed boundary: -199 holds last confirmed state (just inside deadband) | ported | server/test_runway_config.py::test_just_above_descend_threshold_holds |
| 9 | None vertical_rate holds last confirmed state and never raises | ported | server/test_runway_config.py::test_none_vertical_rate_holds_last_confirmed_state_and_never_raises |
| 10 | 'ground' string vertical_rate holds last confirmed state and never raises | ported | server/test_runway_config.py::test_string_vertical_rate_holds_last_confirmed_state_and_never_raises |
| 11 | True (bool) vertical_rate holds last confirmed state, not read as int 1 | ported | server/test_runway_config.py::test_bool_vertical_rate_holds_last_confirmed_state_not_read_as_int_1 |
| 12 | dict vertical_rate holds last confirmed state and never raises | ported | server/test_runway_config.py::test_dict_vertical_rate_holds_last_confirmed_state_and_never_raises |
| 13 | SYNTHETIC (A-02-02-01, no real departure observed): +2400 large climb -> departing | ported | server/test_runway_config.py::test_synthetic_large_climb_departs |
| 14 | infer_from_flight() delegates on the flight dict's vertical_rate_fpm key | ported | server/test_runway_config.py::test_infer_from_flight_delegates_on_the_flight_dicts_vertical_rate_fpm_key |
| 15 | device_config.runway_label() returns an English label containing 'Runway ' and no 'Piste' for every RUNWAY_IDS member (D-11/A-29) | ported | server/test_runway_config.py::test_runway_labels_are_english_with_no_piste_vocabulary |
