# Ledger: companion/test_status_pages.py

Baseline: `companion__test_status_pages.txt`, 317 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | render() shows two distinct, separately-labelled freshness signals | ported | companion/test_status_pages_01.py::test_render_shows_two_distinct_freshness_labels |
| 2 | staleness_status() returns ok/warn/error at the right boundaries, warn for a never-seen signal | ported | companion/test_status_pages_01.py::test_staleness_status_boundaries |
| 3 | wake.device_staleness_thresholds() floors at (300, 1200), multiplies at a 5-minute cadence, and falls back to the floors for None (19-05-PLAN.md D-05/A-23) | ported | companion/test_status_pages_01.py::test_device_staleness_thresholds_floors_and_multipliers |
| 4 | wake.device_staleness_thresholds() guarantees warn_s < error_s for every input | ported | companion/test_status_pages_01.py::test_device_staleness_thresholds_warn_always_under_error |
| 5 | wake.env_sleep_s() reads SKYPANE_SLEEP_S unclamped (no [60, 3600] range check) and degrades to None for unset/empty/non-numeric/non-positive values | ported | companion/test_status_pages_01.py::test_env_sleep_s_reads_unclamped_and_degrades |
| 6 | wake.effective_wake_interval_s() prefers the screen-off cadence, otherwise a configured wake_interval_s, and degrades to None for a missing config | ported | companion/test_status_pages_01.py::test_effective_wake_interval_s_precedence |
| 7 | companion/wake.py's source never mentions the pages package or app.py | ported | companion/test_status_pages_01.py::test_wake_module_never_imports_pages_or_app |
| 8 | layout.absolute_and_relative() covers every documented case: ordering, Z-suffix parsing, default/explicit fallback, unparseable-timestamp degradation, missing now_ts | ported | companion/test_status_pages_01.py::test_layout_absolute_and_relative_covers_every_documented_case |
| 9 | health_page's private timestamp helpers are gone (a move, not a copy) and the Device row still renders the absolute-plus-relative format, now as a parenthesised <time data-relative> element | ported | companion/test_status_pages_01.py::test_health_page_timestamp_helpers_promoted_not_duplicated |
| 10 | a stale device and a fresh pipeline read as independent per-tile modifiers (error vs ok) on their own wrappers, not a blended verdict, with only the dots that legitimately remain still healthy | ported | companion/test_status_pages_01.py::test_independent_thresholds_one_warn_one_ok |
| 11 | the Device and Pipeline tiles carry their freshness label exactly once (caption only) plus exactly one Emphasis-role verdict and exactly one muted detail slot holding the mono timestamp, with zero stat-tile__value and no leftover dot-label (quick task 260901-tsa finding C, retargeted by 22-12-PLAN.md Task 1's X8 anatomy) | ported | companion/test_status_pages_01.py::test_device_pipeline_tiles_have_no_duplicated_label |
| 12 | zero battery rows render the good-news empty state and no sparkline | ported | companion/test_status_pages_01.py::test_battery_empty_state_no_sparkline |
| 13 | Health's battery section draws exactly one ring whose drawn fraction — recovered from its own emitted radius and dash array — equals the percentage the readout beside it PRINTS; the <h2> still carries no glyph, battery_sparkline_svg()'s own output carries no ring class, and a device with no reading renders no ring at all rather than an empty one (CFG-40) | ported | companion/test_status_pages_01.py::test_battery_ring_agrees_with_its_own_readout |
| 14 | three battery rows render the full trend (not just the latest value) and exactly one <svg> with exactly n - 1 trend-line segments (260902-ep7: retargeted from the retired single-<polyline> marker) | ported | companion/test_status_pages_01.py::test_battery_trend_shows_all_readings_and_one_sparkline |
| 15 | Battery Trend's Timestamp column shows the D-09 concise format (full ISO demoted to title), matching the Device/pipeline rows, and _battery_section() stays single-argument | ported | companion/test_status_pages_01.py::test_battery_trend_timestamps_show_concise_format |
| 16 | the readings table is collapsed behind a closed-by-default disclosure, and the chart precedes it (D-08) | ported | companion/test_status_pages_01.py::test_battery_readings_collapsed_behind_closed_disclosure_after_chart |
| 17 | the Battery trend heading shows the default 3-month window framing on an empty render (260902-l0b, retargeted from the retired D-10 'Latest 20 readings' label) | ported | companion/test_status_pages_01.py::test_battery_trend_heading_shows_d10_window_label |
| 18 | a multi-day seeded render plots the three DAILY AVERAGES (never any raw reading value) as points, keeps every raw reading visible in the disclosure table, and names the 3-month window (260902-l0b) | ported | companion/test_status_pages_01.py::test_battery_chart_plots_daily_averages_not_raw_readings |
| 19 | a same-day (fewer than two calendar days) seeded render still produces a chart and a readout, captioned honestly as readings rather than the 3-month window — the day-1 regression guard (260902-l0b) | ported | companion/test_status_pages_01.py::test_battery_chart_falls_back_to_raw_series_on_day_one |
| 20 | the Battery trend caption is mode-honest across three renders — empty (3-month default), multi-day (3-month, daily average), and same-day (readings count) (260902-l0b) | ported | companion/test_status_pages_01.py::test_battery_caption_is_mode_honest_across_renders |
| 21 | the anomaly banner names the real failing category (a disagreement), not only the generic fallback text (UXA-06) | ported | companion/test_status_pages_01.py::test_anomaly_banner_names_real_categories_not_generic_only |
| 22 | _anomaly_category_text() lower-cases ordinary mid-sentence phrases but never a leading acronym (no 'aDS-B') | ported | companion/test_status_pages_01.py::test_anomaly_categories_never_lowercase_a_leading_acronym |
| 23 | _anomaly_category_labels() returns one period-stripped label per anomaly, distinct from collect_anomalies()'s own full literal sentences (D-07) | ported | companion/test_status_pages_01.py::test_anomaly_category_labels_are_pill_text_not_full_sentences |
| 24 | _anomaly_banner_html() reproduces layout.anomaly_banner()'s exact severity-to-class/role mapping, and carries one banner__pill per anomaly plus the accessible ANOMALY_BANNER_TEXT tail (D-07) | ported | companion/test_status_pages_01.py::test_anomaly_banner_html_matches_layout_anomaly_banner_severity_mapping |
| 25 | a two-anomaly fixture renders exactly two banner__pill elements inside one banner element on the real page (D-07) | ported | companion/test_status_pages_01.py::test_anomaly_banner_renders_one_pill_per_anomaly_on_the_page |
| 26 | Corroboration's three rows stay compact (dot/label/count only) and their explanations move into a closed-by-default disclosure (D-08) | ported | companion/test_status_pages_01.py::test_corroboration_rows_compact_explanations_in_closed_disclosure |
| 27 | _corroboration_section()'s second return value (the disagreement flag) is unchanged by the D-08 disclosure rewrite | ported | companion/test_status_pages_01.py::test_corroboration_section_disagreement_flag_unchanged |
| 28 | no corroboration row's explanation leaks a bare decision-ID parenthetical (UXA-05) | ported | companion/test_status_pages_01.py::test_corroboration_copy_has_no_decision_id_leak |
| 29 | the Device check-in and ADS-B pipeline rows render via the D-09 concise timestamp format | ported | companion/test_status_pages_01.py::test_device_and_pipeline_rows_use_concise_timestamp_format |
| 30 | Health's D-12 reversal: a live data-loaded-at timestamp survives, page_header() is called exactly once, and the retired stale-view banner marker/copy and manual Refresh-link class are gone from both the rendered page and the module itself (260902-chc) | ported | companion/test_status_pages_01.py::test_health_pill_reversal_guard |
| 31 | Battery trend renders a healthy status-coloured card border on a normal trend, in place of the retired status_dot() badge (D-01 reversal, quick task 260902-gjj) | ported | companion/test_status_pages_01.py::test_battery_section_healthy_card_border_on_normal_trend |
| 32 | an empty/single-reading battery trend renders an ok badge and no anomaly banner (Assumption A1 regression guard) | ported | companion/test_status_pages_01.py::test_battery_empty_history_ok_badge_no_anomaly_banner |
| 33 | a real battery drop drives both the card's own error border (retargeted from the retired badge, quick task 260902-gjj) and the banner; the detail copy is no longer rendered | ported | companion/test_status_pages_01.py::test_battery_drop_drives_badge_and_banner_detail_copy_not_rendered |
| 34 | an unhealthy fixture renders the anomaly banner with zero <ul/<li list markup inside its own element slice (retargeted from a page-wide ban by quick task 260903-ghy, to stop it colliding with a legitimate .data-cards list elsewhere on the page) | ported | companion/test_status_pages_01.py::test_anomaly_detail_list_markup_is_gone |
| 35 | with all four D-14 signals unhealthy, none of collect_anomalies()'s four item strings is rendered | ported | companion/test_status_pages_01.py::test_none_of_the_four_anomaly_item_strings_render |
| 36 | battery_sparkline_svg() emits no url(, <image, or <script — no external reference at all | ported | companion/test_status_pages_01.py::test_sparkline_has_no_external_reference |
| 37 | battery_sparkline_svg() emits per-point interactive hit targets with data-mv/data-ts/<title>, in chronological order, with roving tabindex on the latest point only | ported | companion/test_status_pages_01.py::test_sparkline_svg_has_per_point_interactive_markup |
| 38 | battery_sparkline_svg() emits exactly four aria-hidden axis-label text nodes carrying the FIXED SPARKLINE_Y_MIN_MV/SPARKLINE_Y_MAX_MV values (not the fixture's own real min/max), with every prior no-external-reference guarantee intact (D-09, retargeted by 19-05-PLAN.md Task 2/D-04) | ported | companion/test_status_pages_02.py::test_sparkline_axis_labels_present_with_fixed_range |
| 39 | battery_sparkline_svg() draws a flat series (every value identical) at one consistent y level, never pinned to the canvas edge by a collapsed min==max range (19-05-PLAN.md Task 2/D-04, A-22) | ported | companion/test_status_pages_02.py::test_sparkline_flat_series_draws_flat_not_pinned_to_bottom |
| 40 | battery_sparkline_svg() draws a small (15mV) wiggle as a small y movement, well under a tenth of the fixed range's full excursion — not a cliff spanning the whole canvas (19-05-PLAN.md Task 2/D-04, A-22) | ported | companion/test_status_pages_02.py::test_sparkline_small_wiggle_stays_small_not_a_cliff |
| 41 | battery_sparkline_svg() clamps out-of-range values (2500mV, 4500mV) to the canvas edge rather than escaping it or rescaling the fixed axis labels (19-05-PLAN.md Task 2/D-04) | ported | companion/test_status_pages_02.py::test_sparkline_out_of_range_values_clamp_not_rescale |
| 42 | _sparkline_dense_threshold() derives a different threshold for different canvas widths, proving the density rule is width-derived rather than a typed constant (19-05-PLAN.md Task 2/D-04) | ported | companion/test_status_pages_02.py::test_sparkline_dense_threshold_is_width_derived |
| 43 | battery_sparkline_svg()'s <svg> carries no viewBox/preserveAspectRatio (no scale factor exists), every cx/cy is a percentage inside [0, 100] with strictly increasing chronological marker x-positions, marker/hit-target radii stay the unchanged absolute 3/8, and style.css declares the canvas height exactly once for this selector and never inside a @media block (quick task 260902-ep7 BUG 4, rewritten in place from 260902-dng's retired scale-bound mechanism) | ported | companion/test_status_pages_02.py::test_sparkline_scale_bounded_at_one_across_real_container_widths |
| 44 | battery_sparkline_svg() fills an area under the trend line from a NESTED viewBox'd <svg> (percentages are illegal in a points list) whose vertices land on the exact coordinates the chart's own marks did, closed at the axis minimum rather than the canvas edge, painted before the line, in currentColor at a translucent fill-opacity, with the outer canvas still carrying no viewBox, no url(/image/script reference, no colour literal, no rule of its own for the layer, and nothing at all below two points (CFG-41/CFG-45, 24-05-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_sparkline_area_sits_under_the_line_in_its_own_nested_viewbox |
| 45 | the battery chart marks the newest PLOTTED point (never the newest raw row, which may carry no battery_mv at all) with its own non-dot class at a named radius that fits the canvas's vertical inset, last in document order, carrying the same timestamp its hit target does, leaving the roving-tabindex path byte-identical, and surviving the density rule that suppresses cosmetic dots (CFG-41, 24-05-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_sparkline_marks_the_newest_plotted_point_not_the_newest_row |
| 46 | the chart's low-battery threshold is a full-width rect placed by the same sparkline_point_y() the readings are, its value READ from companion/battery.py and never re-typed, labelled by meaning in a non-aria-hidden <span> outside the canvas in both languages, painted with the status-warn token the legend's own swatch shares, and absent entirely — line and label — when the value falls outside the chart's fixed range (CFG-41, T-24-05-A/B, 24-05-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_sparkline_low_battery_threshold_is_read_from_battery_py_and_labelled |
| 47 | draw.cell_class() maps the classifier's four verdicts to four DISTINCT classes, all of them in DRAWING_CLASSES, and falls to the no-observation class for anything else — so a bucket with no observation can never emit the on-cadence or the missing class — and regularity_grid() raises rather than emitting a cell with no <title> (CFG-43, T-24-07-A, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_regularity_grid_has_four_states_and_never_conflates_them |
| 48 | the regularity grid sizes its cells DOWN from the measured 278px card width at the 360px floor: grid_columns() returns the most columns whose cells still clear the 24px minimum and one more column would not, a narrower card reduces the columns rather than the cells, every cell is square, inside the viewBox, spread across every column and row with exactly CELL_GAP_PX of clear ground, and no colour literal is emitted (CFG-43, CFG-45, T-24-07-D, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_regularity_grid_cells_are_sized_from_the_360px_floor |
| 49 | the regularity grid's element count is bounded by its own geometry and never by the caller's window — at capacity it keeps the NEWEST buckets, reports exactly how many it dropped, and paints none of the dropped verdicts — while one cell still draws one full-size cell and no cells draw nothing (CFG-43, T-24-07-D, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_regularity_grid_is_bounded_and_keeps_the_newest_buckets |
| 50 | draw.CELL_STATE_CLASSES is keyed on EXACTLY wake.classify_check_in_gap()'s own four CHECK_IN_* values — the one coupling a stdlib-only geometry module cannot express as an import (CFG-43, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_draw_cell_vocabulary_is_the_classifiers_own |
| 51 | CLAUSE 1 — Health's regularity caption says what the grid SHOWS: one cell is one day of OBSERVED check-in regularity (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_caption_says_what_the_grid_shows |
| 52 | CLAUSE 2 — Health's regularity caption names the cadence the grid was judged against, by its value and in this app's own duration form, and says that cadence is the one configured NOW rather than the one in force on an earlier day (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_caption_names_the_cadence_it_judged_against_and_says_it_is_todays |
| 53 | CLAUSE 3 — Health's regularity caption says a day with no record is NOT proof the frame did not wake, naming the log rotation that leaves the same gap (CFG-43, T-24-07-A, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_caption_says_a_gap_is_not_proof_of_a_missed_wake |
| 54 | with a config yielding no cadence at all, Health's regularity caption says the grid is judged against the fallback staleness floors and does NOT name a configured value (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_with_no_determinable_cadence_the_caption_names_the_floors |
| 55 | every cell's verdict equals wake.classify_check_in_gap()'s own output for that day's longest observed gap — computed in this check from the classifier, never hard-coded — every unobserved day carries the no-observation class, and the page's own regularity builders call the classifier while referencing no threshold constant and containing no interval arithmetic of their own (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_every_cell_verdict_is_the_classifiers_own_output |
| 56 | with no observations at all the regularity section still renders — a full grid of no-observation cells, none of them on-cadence or missing, under its own caption saying there is nothing recorded yet (CFG-43, T-24-07-A, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_with_no_observations_the_section_still_renders_its_grid |
| 57 | the rendered Health page contains neither 'honoured' nor 'punctual' (nor 'punctualité') in EITHER language while carrying the full grid in both, and the section heading has a real French sibling rather than an English string inside a French page (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_rendered_page_never_claims_punctuality_in_either_language |
| 58 | for all four check-in-card cases (observed x cadence-known), the visible caption carries EXACTLY CHECK_IN_CAPTION_OBSERVED and every other clause that case renders moves, byte-identical, into the card's own <details class="readings-disclosure"> — 'moved, not cut' proven as a relationship, case and clause named on failure (29-06-PLAN.md Task 2, CFG-79) | ported | companion/test_status_pages_02.py::test_check_in_disclosure_moved_clauses_render_across_all_four_cases[observed, cadence known] |
| 59 | battery_sparkline_svg() draws real axis chrome — at least one full-height vertical axis <rect>, at least one full-width horizontal axis <rect>, and at least two tick <rect> elements, all carrying SPARKLINE_AXIS_CLASS and aria-hidden="true" on their own tags (quick task 260902-ep7 BUG 4) | ported | companion/test_status_pages_02.py::test_sparkline_axis_chrome_present |
| 60 | battery_sparkline_svg(daily=True) renders day-plus-month date endpoint labels ('31 Aug'/'2 Sep'), never the clock-format labels a day string would otherwise silently print (260902-l0b) | ported | companion/test_status_pages_02.py::test_sparkline_daily_mode_shows_date_endpoints_not_clock |
| 61 | each daily chart point's data-when names its day, says it is a daily average, and gives the singular/plural-correct contributing reading count (260902-l0b) | ported | companion/test_status_pages_02.py::test_sparkline_daily_point_label_names_day_and_average_count |
| 62 | the density rule suppresses cosmetic dots only at/above the derived threshold (every hit target still reachable, at the reduced radius), survives untouched just below it, and a below-threshold non-daily call stays byte-for-byte what it is today (260902-l0b) | ported | companion/test_status_pages_02.py::test_sparkline_density_rule_suppresses_dots_only_above_threshold |
| 63 | the battery readout's initial markup equals the humanised (value, when) pair the latest reading's own helper builds, split across its value/detail spans, and the retired placeholder prompt no longer appears (D-09, quick task 260901-uzi finding 3) | ported | companion/test_status_pages_02.py::test_battery_readout_seeded_with_latest_reading_not_placeholder |
| 64 | _battery_reading_parts()'s value text leads with a '≈ NN%' estimate ahead of the exact millivolt figure, for a numeric reading battery.battery_percent() can estimate (D-01/A-19) | ported | companion/test_status_pages_02.py::test_battery_reading_parts_value_carries_the_percentage_estimate |
| 65 | _battery_reading_parts()'s value text stays a bare millivolt figure, with no ≈ marker, when battery.battery_percent() cannot estimate the reading (D-01/A-19) | ported | companion/test_status_pages_02.py::test_battery_reading_parts_value_has_no_estimate_when_percent_is_none |
| 66 | _axis_clock_label() renders Europe/Paris local time, not the unconverted UTC clock (D-05, B4): 22:30 UTC in September prints '00:30', not '22:30' | ported | companion/test_status_pages_02.py::test_axis_clock_label_is_paris_local_not_utc |
| 67 | _axis_day_label() names the Europe/Paris calendar day an instant falls on, not its UTC day (D-05, D-12.3) | ported | companion/test_status_pages_02.py::test_axis_day_label_names_the_paris_day |
| 68 | a sparkline point's <title>, aria-label and data-when carry the SAME string — one formatted value, never three independently-derived ones (D-05, B4) | ported | companion/test_status_pages_02.py::test_sparkline_point_title_aria_data_when_are_one_string |
| 69 | a seeded Health page renders zero occurrences of the literal ' UTC' in either English or French (D-05, B4) | ported | companion/test_status_pages_02.py::test_health_page_has_zero_utc_literal_in_either_language |
| 70 | battery-trend.js contains no client-side date parsing or formatting (new Date(), toISOString, getHours, getMinutes), sets title to the pre-formatted 'when' text rather than the raw ts, and its fallback no longer shows a raw ISO string (D-05, B4) | ported | companion/test_status_pages_02.py::test_battery_trend_js_has_no_client_side_date_math |
| 71 | concise_timestamp_html()'s title is a full Europe/Paris local timestamp ('D Mon HH:MM'), never the raw ISO string and never a 'UTC' suffix (D-05, B4) | ported | companion/test_status_pages_02.py::test_concise_timestamp_html_title_is_a_full_local_timestamp_not_raw_iso |
| 72 | a seeded health_page.render() call's battery-readout__value span carries both the '≈' estimate and the ' mV' millivolt figure (D-01/A-19) | ported | companion/test_status_pages_02.py::test_seeded_render_shows_both_the_estimate_and_the_millivolt_figure |
| 73 | the Device tile's widget-verdict paragraph matches DEVICE_STATE_TEXT at each of the three severities a real health_page.render() call can produce (D-03/A-21) | ported | companion/test_status_pages_02.py::test_device_tile_verdict_matches_state_at_each_severity[ok] |
| 74 | the Pipeline tile's widget-verdict paragraph matches PIPELINE_STATE_TEXT at each of the three severities a real health_page.render() call can produce (D-03/A-21) | ported | companion/test_status_pages_02.py::test_pipeline_tile_verdict_matches_state_at_each_severity[ok] |
| 75 | the Corroboration tile's widget-verdict paragraph matches CORROBORATION_STATE_TEXT for both the agreement and disagreement states a real health_page.render() call can produce (D-03/A-21) | ported | companion/test_status_pages_02.py::test_corroboration_tile_verdict_matches_disagreement_state[agree] |
| 76 | the Resolution-rate tile deliberately carries no widget-verdict paragraph (D-03/A-21) | ported | companion/test_status_pages_02.py::test_resolution_rate_tile_carries_no_verdict |
| 77 | every .stat-tile on a rendered Health page — seeded and on a fresh install alike — carries exactly one label, exactly one Emphasis-role element, exactly one muted detail slot, in that fixed order, and no 22px serif heading anywhere inside it (X8/C1, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_one_tile_anatomy_across_every_health_tile[seeded] |
| 78 | Health's 'Only one saw it' corroboration row renders the neutral dot--off with its own distinct visible dot-label while 'Both agree' keeps dot--ok — in both languages, and never a warn dot — so the two states are readable with colour vision entirely absent (X8 / 22-UI-SPEC.md §5 contract 4, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_only_one_saw_it_is_neutral_and_still_distinct[en-Both agree-Only one saw it] |
| 79 | layout.empty_state()'s two-argument output is byte-identical to its pre-compact form (proven against the literal markup AND against data_table()'s own real no-rows caller), an explicit compact=False matches it, and compact=True renders its own modifier plus the 16px sans / 14px muted pair through the empty state's own class names, still escaped (C1/T-22-44, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_empty_state_default_form_is_byte_identical_and_compact_is_opt_in |
| 80 | on a fresh install Health's two IN-TILE empty states (Corroboration, Resolution rate) use the compact form while its two full-width card empty states (Battery trend, Unresolved prefixes) keep the default 22px serif one (C1/X8, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_health_in_tile_empty_states_are_compact_and_card_ones_are_not |
| 81 | the Resolution-rate tile's detail line has a singular form, so a window holding exactly one detection never reads '1 events' / '1 événements', in both languages, and both templates carry their own French catalogue entry (D-06/B16/CFG-29, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_resolution_detail_line_has_a_singular_form[total=1-en] |
| 82 | DEVICE_STATE_TEXT has exactly ok/warn/error/off (widened by 22-04-PLAN.md Task 3 for the frame's own held state), PIPELINE_STATE_TEXT has exactly ok/warn/error/off (B2, 22-03-PLAN.md Task 1) and CORROBORATION_STATE_TEXT has exactly ok/warn (it has no error state) (D-03/A-21) | ported | companion/test_status_pages_02.py::test_state_text_dicts_have_expected_key_sets |
| 83 | a genuinely never-ran pipeline (no META_LAST_PIPELINE_RUN, no META_LAST_DETECTION) renders the neutral verdict with the existing dot--off class, zero dot--warn, zero battery-fallback text, no second detail line, and no anomaly banner when the device is healthy (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_pipeline_never_ran_renders_neutral_no_warn_no_banner |
| 84 | the same never-ran pipeline tile reads in French — 'Aucune détection pour l’instant.', dot--off, zero dot--warn, zero French battery-fallback text (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_pipeline_never_ran_renders_neutral_in_french |
| 85 | compute_health_state()'s pipeline_detail_html key, for a never-ran pipeline, is the bare PIPELINE_NEVER_RAN_DETAIL_TEXT sentence — no widget-verdict class, no PIPELINE_STATE_TEXT verdict text — embedded once inside pipeline_html (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_compute_health_state_carries_pipeline_detail_html_never_ran |
| 86 | compute_health_state()'s pipeline_detail_html key, once the pipeline has run at least once, is verdict-free and embedded once inside pipeline_html, mirroring device_detail_html (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_03.py::test_compute_health_state_carries_pipeline_detail_html_has_run |
| 87 | collect_anomalies()/overall_severity() treat pipeline_state='off' (never ran) exactly like 'ok' — never an anomaly, never a warn — while a genuinely stale pipeline_state still is (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_03.py::test_collect_anomalies_and_overall_severity_treat_pipeline_off_as_healthy |
| 88 | battery_sparkline_svg() still returns '' for fewer than two numeric readings, and the page emits neither a readout element nor a chart script tag (D-09 regression guard) | ported | companion/test_status_pages_03.py::test_single_reading_still_no_chart_no_readout_no_script |
| 89 | a chart-bearing page emits exactly one scoped <script src> and zero inline event-handler attributes | ported | companion/test_status_pages_03.py::test_page_allows_exactly_one_scoped_script_no_inline_handlers |
| 90 | the empty-history battery path stays script-free — no <script, no <svg, no readout element | ported | companion/test_status_pages_03.py::test_empty_battery_history_stays_script_free |
| 91 | a hostile timestamp reaching data-ts/<title> is escaped, never interpolated raw | ported | companion/test_status_pages_03.py::test_hostile_timestamp_is_escaped_in_chart_markup |
| 92 | the Python/CSS/JS three-file contract (route + DOM literals) is guarded against silent drift | ported | companion/test_status_pages_03.py::test_cross_file_contract_drift_guard |
| 93 | a large consecutive-reading drop flags a battery warning (demoted from error, D-05); a gentle monotonic decline does not | ported | companion/test_status_pages_03.py::test_battery_drop_flags_anomaly_gentle_decline_does_not |
| 94 | overall_severity()'s widened 6-input precedence table: source_fault wins outright, error states win next, then warn states/disagreement_warn/coverage_state=='warn', with the 4-argument call staying byte-for-byte backward compatible (19-05-PLAN.md Task 3/D-05) | ported | companion/test_status_pages_03.py::test_overall_severity_widened_precedence_table |
| 95 | overall_severity()'s plan-cited acceptance triple: ('ok', 'error', 'warn') (19-05-PLAN.md Task 3) | ported | companion/test_status_pages_03.py::test_overall_severity_acceptance_criteria_literal |
| 96 | compute_health_state() folds an active source_fault_raw alone into error severity, a non-empty registry alone into warn severity, and stays ok when both are clear (19-05-PLAN.md Task 3/D-05) | ported | companion/test_status_pages_03.py::test_source_fault_alone_produces_error_registry_alone_produces_warn |
| 97 | collect_anomalies()'s two new items (source_fault, coverage_state) appear only when their own input is unhealthy, and a fully healthy 4-argument call still returns none (19-05-PLAN.md Task 3) | ported | companion/test_status_pages_03.py::test_collect_anomalies_two_new_items |
| 98 | a device last seen 400 seconds ago is 'warn' at a 30s wake cadence but 'ok' at a 3600s cadence, pinned from both directions through the real compute_health_state() pipeline (19-05-PLAN.md Task 3/D-05, A-23) | ported | companion/test_status_pages_03.py::test_device_staleness_pinned_from_both_directions_by_cadence |
| 99 | corroboration counts made only of the unknown state produce no error status class | ported | companion/test_status_pages_03.py::test_corroboration_unknown_only_no_error_or_warn |
| 100 | a fully-healthy fixture renders no anomaly banner at all | ported | companion/test_status_pages_03.py::test_no_anomaly_banner_when_all_healthy |
| 101 | a stale ADS-B pipeline shows the anomaly banner copy exactly once | ported | companion/test_status_pages_03.py::test_stale_pipeline_shows_banner_exactly_once |
| 102 | a state directory that cannot hold a database renders the health-unavailable copy without raising | ported | companion/test_status_pages_03.py::test_unreadable_database_degrades_without_raising |
| 103 | with the source-fault meta key set, the CFG-05 landing explanation appears | ported | companion/test_status_pages_03.py::test_source_fault_set_shows_landing_explanation |
| 104 | with the source-fault meta key unset, the CFG-05 landing explanation is absent | ported | companion/test_status_pages_03.py::test_source_fault_unset_hides_landing_explanation |
| 105 | companion/pages/health_page.py never imports the stdlib html module directly | ported | companion/test_status_pages_03.py::test_health_page_never_imports_html_module |
| 106 | Health opens with the shared layout.page_header() component, not a bare <h1> | ported | companion/test_status_pages_03.py::test_health_page_opens_with_shared_page_header |
| 107 | Health's .page-header carries a one-sentence purpose after the auto-refresh pill (quick task 260901-tsa, finding A; retargeted in place by 260902-chc) | ported | companion/test_status_pages_03.py::test_health_page_purpose_sentence_present_after_refresh |
| 108 | Health's body is two id-anchored sections (Screen, then Server & data), and the old 'Overview' heading is gone (D-10) | ported | companion/test_status_pages_03.py::test_health_page_two_id_anchored_sections_correct_order_no_overview |
| 109 | each of Health's two section headings is paired, in its own baseline-aligned .section-intro wrapper, with its own muted description (quick task 260901-tsa, finding B) | ported | companion/test_status_pages_03.py::test_health_page_section_intros_pair_heading_with_description |
| 110 | the Screen section's dashboard-grid holds exactly one tile, the Server & data dashboard-grid holds exactly three, the two migrated cards render as nested page-section elements outside both, and the source-fault block never carries that modifier (D-11/finding E, quick task 260901-uzi finding 4) | ported | companion/test_status_pages_03.py::test_server_data_grid_holds_three_tiles_migrated_cards_outside_grid |
| 111 | the Resolution-rate tile renders the resolved percentage and the window/event-count line for a seeded fixture, and the no-stats empty state for an empty one (D-10/D-11) | ported | companion/test_status_pages_03.py::test_resolution_rate_tile_renders_percentage_and_window |
| 112 | the migrated Unresolved-prefixes card keeps its filter bar, read-only note, and non-button Clear control (D-12) | ported | companion/test_status_pages_03.py::test_registry_card_keeps_filter_bar_note_and_non_button_clear |
| 113 | the read-only note is reworded to name Airlines as the resolution surface, no longer points at the manual runbook (phase 13 D-10), no longer says 'prefix' in either half (19-06-PLAN.md Task 3, D-06), and (29-06-PLAN.md Task 2, CFG-79) is now split into a short visible sentence plus its moved instruction inside a readings-disclosure | ported | companion/test_status_pages_03.py::test_read_only_note_reworded_to_point_at_airlines_not_the_runbook |
| 114 | _SOURCE_ROWS has a fifth 'manual' entry, resolution_stats() folds a seeded 'manual' route_source count into the total and a labelled row, and render() shows a 'Manual' row (phase 13 D-02) | ported | companion/test_status_pages_03.py::test_source_rows_gains_fifth_manual_entry |
| 115 | resolution_stats() counts a NULL and an unrecognised route_source into one 'Other' bucket, the total equals every row in the window, and render() shows the 'Other' row (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_resolution_stats_counts_unknown_route_source_as_other |
| 116 | resolution_stats() with only known route_source values renders exactly the five _SOURCE_ROWS rows and no 'Other' row — byte-identical to before this task (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_resolution_stats_known_sources_alone_gain_no_other_row |
| 117 | the empty 'How well we name flights' section is entirely absent from the rendered page in both English and French — never a heading over an empty body (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_stats_section_absent_when_empty_both_languages |
| 118 | with 36 seeded rows (30 known, 6 with a NULL route_source) the resolution-rate tile shows a non-zero count for all 36, never the empty-state copy (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_resolution_rate_tile_shows_36_rows_never_no_events |
| 119 | _NO_STATS_HEADING is an unformatted %d template with no hard-coded window literal, and interpolates RESOLUTION_WINDOW_DAYS at its one call site (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_no_stats_heading_derives_from_window_constant_not_hard_coded |
| 120 | the registry's per-row Resolve link is paired identically (href/aria-label) across the desktop table and mobile card, with distinct visible text per representation, and a hostile prefix renders fully escaped in both (phase 13 D-10, T-13-05) | ported | companion/test_status_pages_03.py::test_registry_resolve_link_pairs_desktop_and_mobile_and_escapes_hostile_input |
| 121 | companion/pages/health_page.py still contains zero HTML form elements and exactly one '<button' literal (the pre-existing D-16 docstring mention only) — Health still gains no state-changing (form-submitting) control (phase 13 D-10, T-13-13; retargeted in place by 21-02-PLAN.md Task 1, D-18) | ported | companion/test_status_pages_03.py::test_health_still_has_no_form_and_no_button_in_any_state[normal] |
| 122 | the battery heading's sibling caption <p> (retargeted from the retired trailing <span>, 29-06-PLAN.md Task 1/CFG-84) and the Unresolved-prefixes read-only note both compose section-caption with their existing sizing class, and style.css's .section-caption still declares exactly one property at the file's single 70% muted strength (quick task 260902-gjj, ISSUE 1) | ported | companion/test_status_pages_03.py::test_quick_260902_gjj_muted_captions_compose_section_caption |
| 123 | corrupting only the database leaves the registry card rendering while the stats card degrades, and vice versa (D-11) | ported | companion/test_status_pages_03.py::test_migrated_cards_have_independent_failure_isolation |
| 124 | _read_health_inputs() carries exactly nine keys — device_config and registry_rows now join it for severity's sake (19-05-PLAN.md Task 3/D-05) — while the stats read alone stays a separate call in render() (D-11) | ported | companion/test_status_pages_03.py::test_read_health_inputs_keeps_stats_separate |
| 125 | the battery-trend section keeps its own status modifier (retargeted from the retired badge, quick task 260902-gjj), readout, and single script tag after moving out of the grid | ported | companion/test_status_pages_03.py::test_battery_section_keeps_everything_after_the_move |
| 126 | the battery-trend heading carries ONLY its short fixed text (no inline precision span), immediately followed by a sibling <p class="text-label section-caption"> carrying _battery_trend_caption()'s own text, itself followed by the chart/table body — index(h2) < index(caption) < index(body) (29-06-PLAN.md Task 1, CFG-84) | ported | companion/test_status_pages_03.py::test_battery_heading_is_short_and_precision_lives_in_a_sibling_caption |
| 127 | the battery-trend heading's rendered text equals i18n.t_lang(BATTERY_SECTION_HEADING_TEMPLATE, lang) % (BATTERY_TREND_WINDOW_DAYS // 30) in both English and French — a relationship against the real constants, not a typed literal (29-06-PLAN.md Task 1, CFG-84) | ported | companion/test_status_pages_03.py::test_battery_heading_equals_template_times_window_in_both_languages |
| 128 | all three _battery_trend_caption() branches (usable daily series, no rows at all, sub-two-day raw series) render their own exact text inside the sibling caption <p>, never inside the heading (29-06-PLAN.md Task 1, CFG-84) | ported | companion/test_status_pages_03.py::test_battery_trend_caption_all_three_branches_render_in_sibling_caption |
| 129 | the battery readout precedes the chart and the script tag inside the battery-trend section, carries its single expected class plus role="status" plus both value/detail spans, and battery-trend.js still looks it up by id (quick task 260901-tsa finding D, retargeted by quick task 260901-uzi finding 3) | ported | companion/test_status_pages_03.py::test_battery_readout_precedes_chart_class_list_and_live_region |
| 130 | health_page.BATTERY_SECTION_CLASS is guarded against silent drift from companion/static/style.css | ported | companion/test_status_pages_03.py::test_battery_section_class_is_styled_in_stylesheet |
| 131 | the battery-trend and Unresolved-prefixes cards each carry the status modifier layout.card_status_class() derives from battery_status()/coverage_status()'s own real return value on the same rows, the Resolution-statistics card carries none, and style.css declares all three doubled-form status rules for both card components (quick task 260902-gjj, ISSUE 2) | ported | companion/test_status_pages_03.py::test_quick_260902_gjj_card_status_borders_render_correct_modifiers |
| 132 | every card-status modifier selector (battery-trend-section, page-section, and — quick task 260902-gjj Task 3 — stat-tile) sits after that component's own :hover/:focus-within rule in style.css's source order, so the status border survives hover and keyboard focus rather than losing to the hover shorthand | ported | companion/test_status_pages_03.py::test_card_status_modifiers_survive_hover_source_order |
| 133 | the battery-trend and Unresolved-prefixes cards render no dot-label anywhere inside their own boundaries, the Corroboration tile's three dots survive untouched (proving the removal is scoped, not global), and BATTERY_STATUS_LABEL/_battery_badge_block are both gone via hasattr, never a source grep (quick task 260902-gjj, ISSUE 2) | ported | companion/test_status_pages_03.py::test_quick_260902_gjj_dot_removal_scoped_not_global |
| 134 | style.css's .section-intro / .section-intro > p / .stat-tile__value .mono / .battery-readout rules each carry their load-bearing declaration, and .mono precedes .battery-readout in source order (quick task 260901-tsa) | ported | companion/test_status_pages_03.py::test_quick_260901_tsa_css_dom_contract_guard |
| 135 | style.css's .dashboard-grid declares an explicit cross-axis stretch (the UXA-06 reversal) and no longer declares start, and .dashboard-shell's own separate start-aligned declaration (D-21's sticky sidebar) is the file's only remaining one (quick task 260901-uzi finding 1) | ported | companion/test_status_pages_03.py::test_dashboard_grid_stretches_same_row_tiles |
| 136 | style.css's .data-table th declares a symmetric, non-zero vertical padding via the two-value shorthand (quick task 260902-dng bug 2, closes 260901-uzi Finding 5 candidate (a)) | ported | companion/test_status_pages_03.py::test_data_table_th_has_symmetric_nonzero_padding |
| 137 | exactly the two migrated cards carry page-section--nested (located by their own heading constants), the source-fault block never carries it even when it renders, both .section-intro headings are untouched, and style.css's nested-heading rule — promoted by 06.6.4.1.1 D-09's deliberate second reversal — declares the sans family, the Body size (16px) and the semibold weight explicitly (plus its retained 260902-bl2 bottom margin), sitting below a .text-heading section-heading tier confirmed still 22px/regular at the token level too (quick task 260901-uzi finding 4, Check 2; reverted by quick task 260902-iag; re-promoted by 06.6.4.1.1 plan 02 Task 2) | ported | companion/test_status_pages_03.py::test_nested_heading_tier_promoted_to_sans_semibold_emphasis_role |
| 138 | style.css's .stat-tile__caption converges on the one unified 12px uppercase label voice (D-13) — sans family, 12px size, semibold weight, uppercase transform and 0.06em tracking all declared explicitly, with no serif token named anywhere in its rule body — while .stat-tile__value keeps its own untouched D-09 Emphasis-role size/weight, the nested card title stays on its own D-09-second-reversal sans-semibold Body-size declarations, the shared h1/h2/h3/legend/.text-heading serif rule keeps its regular weight, and the token table reads 14/16/22px (supersedes quick task 260902-dng Task 3's semibold promotion and quick task 260902-iag Task 2's reversal of it — 06.6.4.1.1 plan 02 Task 3) | ported | companion/test_status_pages_03.py::test_stat_tile_caption_joins_the_unified_label_voice |
| 139 | Health's two-tier hierarchy (D-10 section headings vs. the cards nested inside them) still reads apart with no font-size or font-weight distinction between the tiers: every level-2 heading (Battery trend, Unresolved prefixes, Resolution statistics) sits inside a bordered card <section>, both level-1 headings (Screen, Server & data) sit inside the plain .section-intro row with no card class, a .dashboard-grid always intervenes between a level-1 heading and the first level-2 card in its own section, and the four spacing tiers that now carry the distinction stay strictly ordered against their real :root token values — in both the empty and seeded state (quick task 260902-iag Task 3) | ported | companion/test_status_pages_03.py::test_two_tier_hierarchy_carried_by_layout_not_type |
| 140 | all three nested Health cards (Battery trend, Unresolved prefixes, Resolution statistics) show one heading-to-content rhythm in both the empty and seeded state — the element after </h2> is either rhythm-governed p.text-body or a member of the verified no-top-margin allowlist — and style.css's demotion rule/prose rhythm rule carry the sketch's two margin values in the right source order (quick task 260902-bl2 Task 3, Check 2) | ported | companion/test_status_pages_04.py::test_nested_card_heading_rhythm_holds_for_every_allowed_element |
| 141 | exactly the Resolution-statistics table carries data-table--prose, neither the battery readings table nor the unresolved-prefix registry table does, and style.css's .data-table--prose sits after .data-table with the shared max-content floor still intact on the base rule (quick task 260901-uzi finding 2, Check 3) | ported | companion/test_status_pages_04.py::test_resolution_statistics_table_is_the_only_data_table_prose |
| 142 | the Description column is the only muted column end to end — markup (exactly len(_SOURCE_ROWS) desc cells, all inside Resolution-statistics), builder (data_table()'s desc_columns contract: inert default, byte-identical mono-only output, additive-only desc-only output, both-roles joining mono first) and stylesheet (.data-table td.desc's 70% muted colour, no min-width, no opacity, no muted token anywhere in the file) (quick task 260902-bl2 Task 3, Check 1) | ported | companion/test_status_pages_04.py::test_description_column_is_the_only_muted_column |
| 143 | the Resolution-statistics table has a complete mobile .data-cards representation — one item per _SOURCE_ROWS entry, every label/full-gloss/count present, positioned before its unchanged desktop table (quick task 260903-ghy Task 1, Check A / UIR-10) | ported | companion/test_status_pages_04.py::test_stats_cards_list_is_complete_and_precedes_the_table |
| 144 | the .data-cards mobile toggle contract exists at both breakpoints, .data-card__label mirrors .data-table th's label tier by value, .data-table-wrap's scroll-edge shadow is untouched, and the three literal selectors this harness indexes by elsewhere are all still present (quick task 260903-ghy Task 1, Check B) | ported | companion/test_status_pages_04.py::test_data_cards_toggle_contract_and_untouched_rules |
| 145 | the registry's mobile .data-cards representation is exactly paired with its table by (data-filter-text, data-filter-group), carries concise_timestamp_html()'s own First/Last seen markup exactly once each while the desktop table carries the stacked cell built from the same two formatters over the same now (retargeted by 22-12-PLAN.md Task 2's B12), positioned between the filter bar and the table wrap, and every column (prefix, count, both timestamps, example callsign) is reachable in the card slice (quick task 260903-ghy Task 2, Check C / UIR-11) | ported | companion/test_status_pages_04.py::test_registry_mobile_cards_paired_with_the_desktop_table |
| 146 | the unresolved-prefix table fits by the two levers headless measurement selected — the Flights stacked-cell precedent scoped to its own data-table--registry modifier (the base no-crop floor kept), plus two shortened French headers with the retired long forms gone and the English sources untouched — and never by a 1100px card fallback (B12, 22-12-PLAN.md Task 2) | ported | companion/test_status_pages_04.py::test_registry_table_fits_by_stacked_cells_and_short_french_headers |
| 147 | no card chrome renders for an empty registry (filter bar and .data-cards both absent, empty_state() present instead); both migrated tables together render exactly two .data-cards lists; History and Airlines carry zero occurrences of the new card class names (quick task 260903-ghy Task 2, Check D) | ported | companion/test_status_pages_04.py::test_no_chrome_for_empty_registry_and_no_cross_page_leak |
| 148 | the battery readout carries its id, role="status", both value/detail spans and a humanised visible detail with the machine-precise ISO only in the tooltip, every chart hit target carries data-when, and battery-trend.js's shipped source still reads that attribute, both span classes, and the readout's id literal (quick task 260901-uzi finding 3, Check 4) | ported | companion/test_status_pages_04.py::test_humanised_battery_readout_end_to_end |
| 149 | style.css's .mono reach-through covers both .stat-tile__value and .battery-readout in one rule, and .battery-readout__detail carries the Label size, the regular weight and the file's existing 70% muted strength (quick task 260901-uzi finding 3, Check 5) | ported | companion/test_status_pages_04.py::test_readout_typographic_split_stylesheet_guard |
| 150 | anomaly_active() and the anomaly banner's presence agree in both directions, across healthy and unhealthy fixtures | ported | companion/test_status_pages_04.py::test_anomaly_active_agrees_with_the_banner_both_directions |
| 151 | anomaly_active() runs on every page render and must never raise — missing/empty/file/corrupt-db inputs all degrade safely - expected False for a non-existent state_dir path | ported | companion/test_status_pages_01.py::test_anomaly_active_never_raises_on_hostile_inputs |
| 152 | battery and corroboration section-builder markup (dot, table, svg) survives the stat-tile reframe untouched | ported | companion/test_status_pages_04.py::test_section_builder_markup_survives_the_stat_tile_reframe |
| 153 | Health's three Health-signal icons are tile-only (device, pipeline, corroboration, all whitelisted and tile-tinted) and no Health <h2> — empty or seeded render — carries a glyph any more; health_page.ICON_BATTERY is gone from the module namespace (quick task 260902-j8w) | ported | companion/test_status_pages_04.py::test_health_tile_icons_are_tile_only_and_no_heading_carries_a_glyph |
| 154 | the D-12 reversal (260902-chc) is written down at both prose sites it touches — freshness.js's own header and D-12's own CONTEXT.md entry — each carrying the house SUPERSEDED token and naming this quick task, with D-12's original wording intact | deleted | P: asserted plan-history prose in a freshness.js header comment and in a .planning CONTEXT.md; no behaviour |
| 155 | freshness.js's shipped source carries the loop's own contract — a named interval constant inside the 30-60s band, both halves of pause (setInterval+clearInterval) and visibility (visibilitychange+document.hidden), the double-start guard, and (19-09-PLAN.md, D-02) the retired reload form gone entirely while fetch(/DOMParser/replaceChild/importNode are now required present as this file's own reviewed exception to the forbidden-sink/no-URL-taking-navigation-form/ES5-safe-subset disciplines, which otherwise still hold unchanged | ported | companion/test_status_pages_04.py::test_freshness_js_carries_the_refresh_loop_contract |
| 156 | the auto-refresh pill's markup contract (marker attribute, inline element, hidden-by-default, live data-loaded-at exactly once page-wide, the pill-copy constant's own value, inside .page-header, preceding the purpose sentence) holds on a real render both seeded and on a fresh state directory with no readings at all — proven unconditional, not coupled to the battery chart's own render branch | ported | companion/test_status_pages_04.py::test_auto_refresh_pill_markup_contract_holds_seeded_and_fresh |
| 157 | style.css's .refresh-pill / .refresh-pill[hidden] / pill-scoped icon rules each carry their load-bearing declaration — the [hidden] override hides by visibility with no display value at all — .banner__pill still precedes .refresh-pill in source order, and the pill is taken out of .page-header's block flow entirely via a .page-header-scoped absolute-position rule rather than kept in flow with a reserved line box (260902-ep7) | ported | companion/test_status_pages_04.py::test_refresh_pill_stylesheet_contract |
| 158 | the pipeline tile's new second line renders META_LAST_DETECTION's timestamp byte-identically to concise_timestamp_html(), reusing the existing muted text-label/section-caption tier — never battery-readout__detail, whose class name would collide with the BATTERY_READOUT_ID absence guards (quick task 260903-peo, UIR-14) | ported | companion/test_status_pages_04.py::test_pipeline_tile_second_line_renders_last_detection_timestamp |
| 159 | the pipeline tile's second line renders its honest no-reading-yet fallback when META_LAST_DETECTION is absent, never an empty element or a dangling label (quick task 260903-peo, UIR-14) | ported | companion/test_status_pages_04.py::test_pipeline_tile_second_line_falls_back_honestly_when_no_detection |
| 160 | Health's header renders an honest 'Updated HH:MM' clock — server-rendered as the text of a <time data-relative> element, never the ladder's zero bucket, so the value is true with scripts blocked and live with them (23-06-PLAN.md) — (no relative-age suffix, the full Europe/Paris local timestamp — never the raw ISO — in the clock span's title, retargeted by 22-16 for D-05/CFG-28) beside the unchanged hidden refresh pill and NO Pause/Resume toggle (zero data-refresh-toggle/data-pause-text/data-resume-text, zero <button>), all inside one block-level .page-header__freshness wrapper that is the .page-header's next child right after the <h1>, in prefix/clock/pill source order (21-02-PLAN.md Task 1, D-18; supersedes 19-09-PLAN.md Task 1's Pause/Resume-toggle contract, itself superseding quick task 260903-peo/UIR-18's 'Live — refreshed (Ns ago)' contract) | ported | companion/test_status_pages_04.py::test_health_header_renders_the_persistent_freshness_note |
| 161 | the four UIR-03/07/12/13 one-line fixes hold together: .banner wraps with a nowrap .banner__label rendered on the anomaly banner's lead span, .banner__pill gains min-width: 0 while keeping flex: none and its source position before .refresh-pill, .airline-card__image gains height: auto alongside its surviving aspect-ratio, the .data-table--prose first-column nowrap rule exists after the base rule, and the rendered Battery trend heading's sibling caption follows immediately with no leading em dash of its own (UIR-12, retargeted by 29-06-PLAN.md Task 1/CFG-84; quick task 260902-v2v) | ported | companion/test_status_pages_04.py::test_uir_03_07_12_13_one_line_fixes_hold_together |
| 162 | the two-role spacing split holds as a pair: .dashboard-grid's margin-bottom equals .page-section's own same-section card-to-card value (var(--space-lg)), while .battery-trend-section's section-transition margin-bottom stays the larger, untouched var(--space-2xl) (260902-ep7 BUG 2) | ported | companion/test_status_pages_04.py::test_dashboard_grid_and_battery_trend_section_keep_their_two_role_spacing_split |
| 163 | the desktop-padding/mobile-density pair holds together: .page-section, .theme-status and .battery-trend-section all still declare padding: var(--space-md) in their own base rules, and one shared rule inside the @media (min-width: 960px) block raises all three to padding: var(--space-lg) (06.6.4.1.1-03 D-15) | ported | companion/test_status_pages_04.py::test_desktop_padding_and_mobile_density_pair_holds_together |
| 164 | the bare summary rule declares var(--color-accent), and style.css's own exhaustive accent-reservation list explicitly names the summary's label text (not just its ::marker) — the broadening is recorded, not silent (260902-ep7 BUG 3) | ported | companion/test_status_pages_04.py::test_bare_summary_rule_declares_the_accent_colour |
| 165 | the interaction-skip guard's cross-file contract: a fixture rich enough to actually render a disclosure, a filter input and a chart hit target, and freshness.js's shipped source still checks for a focused INPUT/SUMMARY and health_page.SPARKLINE_HIT_CLASS's own literal value but no longer checks for an open <details> at all (19-09-PLAN.md, D-02: a targeted swap never touches one, so the silent-suspension clause is gone, not merely unused) — this guard's failure mode is silence, so this check is the only thing that would notice a drift | ported | companion/test_status_pages_04.py::test_interaction_skip_guard_cross_file_contract |
| 166 | every layout.REFRESH_SWAP_SELECTORS_BY_PAGE entry, on every page key, appears verbatim in freshness.js, and freshness.js never carries a .sparkline-hit selector literal, a [data-filter-input] reference, or a details[...] selector — the three regions Pitfall 5 names as fatal to swap (19-09-PLAN.md Task 3, generalised in place from the one-tuple form by 23-06-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_swap_selectors_pinned_both_directions |
| 167 | the swap registry has ONE definition site (health_page.REFRESH_SWAP_SELECTORS resolves from layout.REFRESH_SWAP_SELECTORS_BY_PAGE and is that same object, with Health's five regions in their existing order, and no second tuple literal survives in health_page.py) and ONE key set (the script's registry keys equal the Python's, in both directions), with every selector appearing exactly once per registry entry in the script's comment-stripped code and the registry actually read (D1/CFG-35, 23-06-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_swap_registry_has_one_definition_site_and_one_key_set |
| 168 | the swap registry is selected by a page key the SERVER renders on <body> — present for every registry key and for a page with no entry at all — and freshness.js reads that attribute and resolves it with an own-property test, so an unknown key is a no-op rather than an inherited Object property (D1/CFG-35, 23-06-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_page_key_is_server_rendered_and_gates_the_loop |
| 169 | freshness.js knows three things it must not repaint: swapNodes() keeps 22-15's unchanged-region and focused-region skips and gains a per-region pending skip, and tick() stands the whole cycle down while dirty-state.js's own window.SkyPaneDirtyState.hasUncommittedEdits() reports unsaved edits — with the interval, ladder, ceiling, in-flight guard and redirect:manual all untouched (D1/CFG-35, 23-06-PLAN.md Task 1; retargeted from the retired save bar by 27-04-PLAN.md, CFG-63) | ported | companion/test_status_pages_04.py::test_freshness_loop_knows_three_things_it_must_not_repaint |
| 170 | Flights' swap registry entry covers the phone card list, the desktop table, the live count and the freshness line, EXCLUDES every element list-filter.js captures once at load (the input, Clear, the empty state and the set hooks), nests no entry inside another, is keyed by nav_slug()'s own value, and the registry's own comment states the exclusion's reason (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_flights_swap_registry_entry_covers_and_excludes_the_right_regions |
| 171 | freshness.js's new-row highlight is a DIFF over server-rendered row identity: its two cross-file literals equal layout.REFRESH_ROW_ID_ATTR/REFRESH_NEW_ROW_CLASS, the known set is populated from the page as first rendered rather than empty, the diff runs from applySwap() and from nowhere else, resolves the set with an own-property test, applies one class through classList and never removes it, and writes no markup (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_freshness_new_row_highlight_is_a_diff_never_a_first_paint |
| 172 | Health's and Home's freshness lines are layout.freshness_line_html()'s own output verbatim — ONE definition site, the markup gone from health_page.py entirely — each page renders exactly one data-loaded-at and one data-refresh-pill, and the builder emits the dot, the prefix, the clock element and the pill in that order with exactly one <time data-relative> (D1/CFG-35, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_the_freshness_line_has_one_builder_and_three_call_sites |
| 173 | Home declares the four regions that actually change between polls (the strip, the status tiles, the picture, the recent-flights list) plus its freshness line, every literal in every one of its selectors appears in the rendered page, and the Display scope declares exactly the strip and the freshness line — everything else there is a form (D1/CFG-35, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_home_declares_the_regions_it_actually_renders |
| 174 | the Frame strip's next-update cell carries a marked <time data-relative-countdown> over companion/wake.py's OWN resolved instant, reading the ladder's future form, beside a state word that stays frame_state.resolve_state()'s — and no script in companion/static names a state or a headline template at all (D1/D-03/CFG-26, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_the_strip_countdown_formats_and_never_decides |
| 175 | the refreshed picture fades through a named keyframes block spending var(--motion-fast) with no bare literal, the class is applied only after freshness.js compares the image's own src (a fade on every swap would flash the page every 45s for no information), and the server renders it never (D1+D3/CFG-32, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_the_picture_fades_only_when_the_picture_changed |
| 176 | layout.stat_tile()'s new caption_title parameter is byte-identical to the pre-existing output when omitted, None, or '' (19-06-PLAN.md Task 1, D-06) | ported | companion/test_status_pages_05.py::test_stat_tile_caption_title_byte_identical_when_unused |
| 177 | layout.stat_tile()'s caption_title renders as a title attribute on the caption <p> element, and nowhere else (19-06-PLAN.md Task 1, D-06) | ported | companion/test_status_pages_05.py::test_stat_tile_caption_title_renders_as_tooltip_on_caption_only |
| 178 | layout.stat_tile()'s caption_title is escaped through escape_html(), matching every other attribute value this module emits (19-06-PLAN.md Task 1, D-06/T-19-08) | ported | companion/test_status_pages_05.py::test_stat_tile_caption_title_is_escaped |
| 179 | Health's stat tiles and corroboration rows read in plain language: 'Corroboration', 'Single-source (uncorroborated)' and 'pipeline last ran' are all absent from visible text, and the Pipeline/Corroboration/Resolution-rate tiles' caption elements each carry a title attribute equal to their matching technical constant (19-06-PLAN.md Task 2, D-06) | ported | companion/test_status_pages_05.py::test_health_tiles_and_rows_read_in_plain_language |
| 180 | a full Health render with a non-empty unresolved registry and stats rows (every branch rendered) contains no 'adsbdb' and no CFG-\d requirement id outside a title attribute (19-06-PLAN.md Task 3, D-06/T-19-24) | ported | companion/test_status_pages_05.py::test_health_registry_and_stats_prose_has_no_adsbdb_or_requirement_id |
| 181 | all 52 vendored illustrations normalize to the exact same pixel dimensions (illustration_normalize.ILLUSTRATION_TARGET_SIZE) | ported | companion/test_status_pages_05.py::test_all_illustrations_normalize_to_identical_pixel_dimensions[air-algerie.png] |
| 182 | all 52 vendored illustrations normalize and serve well under 65536 bytes per file, the UIR-08 weight fix — a regression that got the dimensions right but left the served bytes unchanged would defeat this check | ported | companion/test_status_pages_05.py::test_all_illustrations_serve_well_under_the_byte_ceiling[air-algerie.png] |
| 183 | all 52 vendored illustrations normalize with their painted content centred within 1px on both axes and never clipped | ported | companion/test_status_pages_05.py::test_all_illustrations_are_centred_and_unclipped[air-algerie.png] |
| 184 | a source image whose opaque bbox is None (nothing painted) falls back to the source image instead of raising, and still normalizes to the target output size | ported | companion/test_status_pages_05.py::test_none_opaque_bbox_falls_back_to_source_image_without_raising |
| 185 | no module anywhere under companion/ defines its own alpha-threshold constant — the threshold is only ever imported from server.plane.render | deleted | S: asserted source text (a companion-wide scan for a second ALPHA_THRESHOLD constant definition); no behavior beyond what this module's own centred/unclipped-bbox checks already prove by calling server.plane.render._opaque_bbox() directly |
| 186 | page_shell() renders <html lang="fr" under prefs.set_request_prefs(lang='fr') and <html lang="en" otherwise (D-03) | ported | companion/test_status_pages_05.py::test_page_shell_html_lang_follows_prefs |
| 187 | login_shell() renders <html lang="fr" under prefs.set_request_prefs(lang='fr') and <html lang="en" otherwise (D-03) | ported | companion/test_status_pages_05.py::test_login_shell_html_lang_follows_prefs |
| 188 | a rendered shell contains exactly two aria-labelled theme-form forms per footer copy, actions /ui-lang, /ui-theme in that document order, and zero /ui-mode forms (D-02/D-17, 21-UI-SPEC.md §G) | ported | companion/test_status_pages_05.py::test_shell_has_two_ordered_theme_forms_each_with_aria_label |
| 189 | under lang='fr' the nav reads Accueil/Affichage/Vols/Compagnies/Avancé/État/Appareil (D-09) | ported | companion/test_status_pages_05.py::test_french_shell_nav_reads_the_locked_french_labels |
| 190 | the Advanced group (Health, Device) and the nav status dot always render, in both the sidebar and the bottom tab bar, on a plain request (D-17; retargeted from the dropdown by 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_advanced_group_always_renders_in_both_nav_copies |
| 191 | the sidebar and the mobile dropdown each contain exactly one .nav-status link, with no <form> or <button> inside it, sitting after the brand and before the primary nav list in document order (D-03) | ported | companion/test_status_pages_05.py::test_nav_status_appears_once_in_each_nav_copy_after_the_brand |
| 192 | nav_status_html()'s two dots follow all four Screen/Quiet-hours on/off combinations (dot--ok for on, dot--off for off) (D-03) | ported | companion/test_status_pages_05.py::test_nav_status_dot_classes_follow_the_four_on_off_combinations |
| 193 | under lang='fr' the reminder reads 'Écran allumé' and 'Heures calmes désactivées' — fully French, never 'Heures calmes off' (R-04) | ported | companion/test_status_pages_05.py::test_french_nav_status_reads_ecran_allume_heures_calmes_desactivees |
| 194 | nav_status_html(None) and nav_status_html({}) both return '', and page_shell(..., device_config=None) — the default, used by login/404/error pages — renders no .nav-status at all (D-03) | ported | companion/test_status_pages_05.py::test_nav_status_html_none_or_falsy_device_config_renders_nothing |
| 195 | login_shell() — which never takes a device_config parameter — carries no .nav-status markup, unchanged by this task (D-03) | ported | companion/test_status_pages_05.py::test_login_shell_carries_no_nav_status_and_is_unchanged |
| 196 | status_row('Frame', 'Checking in normally', 'Last check-in 2m ago', 'ok') carries status-row--ok, dot--ok, all three texts and exactly one status-row__label (D-21) | ported | companion/test_status_pages_05.py::test_status_row_renders_dot_label_verdict_detail |
| 197 | status_row('', ..., 'warn') omits the status-row__label span entirely, not merely its text (D-21, 20-UI-SPEC.md Section Anatomy A) | ported | companion/test_status_pages_05.py::test_status_row_empty_label_omits_the_label_span |
| 198 | status_row(..., state='nonsense') falls back to the default dot class and emits no status-row--nonsense class (T-20-18) | ported | companion/test_status_pages_05.py::test_status_row_unrecognised_state_falls_back_safely |
| 199 | status_row() with a hostile <script>-shaped verdict/detail comes back escaped, never raw markup (T-20-03) | ported | companion/test_status_pages_05.py::test_status_row_escapes_hostile_verdict_and_detail |
| 200 | layout.section_intro_html() emits the byte-identical markup health_page.py's own former private _section_intro_html() rendered before the promotion (20-UI-SPEC.md Section Anatomy C) | ported | companion/test_status_pages_05.py::test_section_intro_html_is_byte_identical_to_the_promoted_markup |
| 201 | layout.section_intro_html() escapes a hostile section_id argument, never writing it raw into the id="..." attribute (WR-03, 20-REVIEW.md) | ported | companion/test_status_pages_05.py::test_section_intro_html_escapes_hostile_section_id |
| 202 | health_page no longer defines its own _section_intro_html — layout.section_intro_html is the one definition | ported | companion/test_status_pages_05.py::test_health_page_no_longer_defines_section_intro_html |
| 203 | _device_timestamp_only() emits no widget-verdict class and no DEVICE_STATE_TEXT value, while _device_section() still carries exactly one (D-17) | ported | companion/test_status_pages_05.py::test_device_timestamp_only_carries_no_verdict_text |
| 204 | compute_health_state()'s returned dict carries a device_detail_html key holding the verdict-free fragment also embedded (once) inside device_html (D-17) | ported | companion/test_status_pages_05.py::test_compute_health_state_carries_device_detail_html |
| 205 | under lang='fr', relative_age_text(30) reads 'à l’instant' and relative_age_text(90000) reads 'il y a 1\u00a0j' (D-07) | ported | companion/test_status_pages_05.py::test_relative_age_text_french_seconds_bucket_reads_a_linstant |
| 206 | under lang='en' (the default), relative_age_text()'s English output is byte-for-byte unchanged — '30s ago'/'1d ago' (D-07) | ported | companion/test_status_pages_05.py::test_relative_age_text_english_unchanged_under_default_lang |
| 207 | local_clock_text() on a September timestamp reads 'sept.' under fr and 'Sep' under en, with an identical HH:MM in both (D-07) | ported | companion/test_status_pages_05.py::test_local_clock_text_french_month_abbreviation |
| 208 | relative_age_text()'s positional signature (age_seconds first) is untouched — lang is a trailing keyword only | ported | companion/test_status_pages_05.py::test_relative_age_text_first_positional_argument_is_age_seconds |
| 209 | layout.relative_time_html() renders a <time datetime=... data-relative> element whose own text EQUALS layout.relative_age_text()'s output for all four buckets in BOTH languages, and whose instant names the same moment that text describes (23-03, D14) | ported | companion/test_status_pages_05b.py::test_relative_time_html_wraps_the_one_ladder_in_both_languages |
| 210 | layout.relative_time_html() degrades to escaped plain text — never a raise, never a <time> element carrying an empty or invented instant — for a falsy, None, unparseable or mismatched timestamp (23-03) | ported | companion/test_status_pages_05b.py::test_relative_time_html_degrades_without_an_invented_instant |
| 211 | layout.relative_future_text() reads the SAME s/m/h/d bucket boundaries the past ladder reads (asserted at and around all three), is never negative, is never the past form, and clamps an already-elapsed instant to the zero bucket, in both languages (23-03) | ported | companion/test_status_pages_05b.py::test_future_form_shares_the_past_ladders_own_buckets |
| 212 | layout.relative_time_html() reads a FUTURE instant through the future form and a past one through the past form — one function, both directions, bounded and non-negative one second either side of now, in both languages (23-03, for 23-06's countdown) | ported | companion/test_status_pages_05b.py::test_relative_time_html_reads_a_future_instant_forwards |
| 213 | layout.concise_timestamp_html()'s parenthesised relative half is now a <time data-relative> element, its text unchanged, with its outer mono span, its title, its absolute-first ordering and its no-raw-ISO rule all untouched (23-03, D-09/D-05) | ported | companion/test_status_pages_05b.py::test_concise_timestamp_htmls_relative_half_is_now_an_element |
| 214 | health_page.render() under lang='fr' carries the French page title and at least three other French strings, and none of a short list of English source strings with distinct French forms (D-05) | ported | companion/test_status_pages_05b.py::test_health_page_renders_in_french |
| 215 | health_page.render() under lang='en' (the default) is byte-for-byte unchanged for a seeded state — pinned representative substrings (D-05) | ported | companion/test_status_pages_05b.py::test_health_page_renders_byte_identical_in_english |
| 216 | compute_health_state()'s device_html/device_detail_html/pipeline_html fields (and health_page.render()'s own page) fully localise their timestamps under lang='fr' — no English month abbreviation or ' ago' survives — proving the request-language ContextVar is resolved at the correct point relative to when this state is computed (Polish fix 2) | ported | companion/test_status_pages_05b.py::test_health_page_device_and_pipeline_timestamps_fully_localise_under_french |
| 217 | every key of companion/i18n_fr/health.py's own CATALOG is a non-empty str mapping to a non-empty str | ported | companion/test_status_pages_05b.py::test_health_catalog_every_key_and_value_is_a_nonempty_str |
| 218 | Airlines opens with the shared layout.page_header() component, not a bare <h1> | ported | companion/test_status_pages_05b.py::test_airlines_page_opens_with_shared_page_header |
| 219 | the gallery renders exactly one .airline-card per illustrations.target_airline_names() entry (36 against today's data) | ported | companion/test_status_pages_05b.py::test_gallery_renders_one_card_per_target_airline |
| 220 | every rendered card image source, with the route prefix stripped, is a member of illustrations.target_filenames() — every rendered URL provably passes the route's own membership test | ported | companion/test_status_pages_05b.py::test_every_card_image_source_passes_route_membership_test |
| 221 | the Air Caraïbes card renders exactly three chips (A330, A350-1000, ATR72) — the A350-1000 shape-slug-validation trap is not fallen into | ported | companion/test_status_pages_05b.py::test_air_caraibes_card_has_three_upper_cased_chips_including_a350_1000 |
| 222 | an airline with no variant entries (Air France) renders no .airline-card__chips container at all | ported | companion/test_status_pages_05b.py::test_primary_only_airline_renders_no_chips_container |
| 223 | variant_chip_label() upper-cases every alphanumeric type code verbatim and word-cases the Embraer/Beechcraft manufacturer forms | ported | companion/test_status_pages_05b.py::test_variant_chip_label_covers_both_domains |
| 224 | airlines_page.ILLUSTRATION_ROUTE_PREFIX equals app.ILLUSTRATION_IMAGE_ROUTE_PREFIX (the duplicated-not-imported route-prefix contract) | ported | companion/test_status_pages_05b.py::test_illustration_route_prefix_matches_app_constant |
| 225 | every rendered card image carries width/height attributes matching illustration_normalize.ILLUSTRATION_TARGET_WIDTH/HEIGHT exactly | ported | companion/test_status_pages_05b.py::test_every_card_image_carries_matching_intrinsic_dimensions |
| 226 | the gallery filter bar carries exactly one each of data-filter-input/-count/-clear/-empty | ported | companion/test_status_pages_05b.py::test_gallery_filter_bar_carries_all_four_contract_markers_exactly_once |
| 227 | the gallery filter bar's Clear control is a real <button type="button"> (D-16 retired) | ported | companion/test_status_pages_05b.py::test_gallery_filter_clear_control_is_a_real_button |
| 228 | the gallery filter label's for attribute equals the search input's id, and that id is the hyphen-free value quick task 260921-p2w Task 1 pins (superseding the now-stale 06.6.4.1-UI-SPEC.md §7.2 row) | ported | companion/test_status_pages_05b.py::test_gallery_filter_label_for_matches_input_id |
| 229 | Compagnies' gallery filter input and Health's registry filter input both carry autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression) | ported | companion/test_status_pages_05b.py::test_compagnies_and_health_filter_inputs_carry_safari_autofill_suppression_attributes |
| 230 | every <input type="search"> this app can render, across companion/pages/*.py and companion/app.py (an ast-based source scan excluding docstrings, 3 occurrences found at plan time — history_page.py, airlines_page.py, health_page.py, one builder each), carries autocomplete=off/spellcheck=false/autocapitalize=characters — a fourth filter bar added later cannot reintroduce the Safari contact-autofill defect with nothing to catch it (quick task 260921-n2n Task 4) | ported | companion/test_status_pages_05b.py::test_every_rendered_search_input_carries_safari_autofill_suppression_attributes |
| 231 | no *_FILTER_INPUT_ID constant value and no hardcoded <input type="search"> id literal, across companion/pages/*.py and companion/app.py (enumerated from disk, 3 constants found at plan time, a >= 3 vacuity floor so deleting the constants cannot make this pass trivially), contains a hyphen — the documented WebKit/Safari trigger that offers the user's own Contacts phone numbers on a name-less type="search" field even with autocomplete="off" set (quick task 260921-p2w Task 2, closing the gap Task 1's three hand-fixed values left open) | ported | companion/test_status_pages_05b.py::test_no_filter_input_id_anywhere_in_the_app_contains_a_hyphen |
| 232 | the gallery filter bar's count text and empty-state body both name the real (36) card total | ported | companion/test_status_pages_05b.py::test_gallery_filter_count_and_empty_body_name_the_real_total |
| 233 | every card carries a data-filter-text equal to its own lower-cased airline name, and the set of data-filter-group values has the same size as the card count | ported | companion/test_status_pages_05b.py::test_every_card_carries_distinct_filter_text_and_group |
| 234 | companion/pages/airlines_page.py imports no history-database module and no sqlite module (D-17 non-goal: no detection-history cross-reference), and imports poll_loop exactly the way phase 13's D-11 membership test deliberately supersedes the OLDER half of that same non-goal | ported | companion/test_status_pages_05b.py::test_airlines_page_imports_no_history_db_or_sqlite_but_does_import_poll_loop |
| 235 | the rendered Airlines gallery contains none of the migrated unresolved-prefix registry or resolution-statistics table column headers (D-13 non-goal) | ported | companion/test_status_pages_05b.py::test_airlines_page_no_longer_renders_registry_or_stats_headers |
| 236 | the rendered Health page still contains both migrated header sets — the content moved, it was not lost | ported | companion/test_status_pages_05b.py::test_health_page_still_renders_both_migrated_header_sets |
| 237 | importing companion.pages.airlines_page raises no error, and the module exposes none of the deleted diagnostics symbols | ported | companion/test_status_pages_05b.py::test_airlines_page_module_exposes_no_deleted_diagnostics_symbol |
| 238 | every card wraps its image in exactly one .airline-card__zoom button whose data-view-panel-src is byte-identical to that same card's <img src>, whose data-view-panel-caption equals CARD_IMAGE_ALT_TEMPLATE %% name, and whose aria-label equals ZOOM_LABEL_TEMPLATE %% name | ported | companion/test_status_pages_05b.py::test_airline_card_zoom_button_attrs_match_expected |
| 239 | the shared lightbox dialog is emitted exactly once, carries both the lightbox and lightbox--wide classes plus all three lightbox__* elements and the close attribute, and its note element renders empty (LIGHTBOX_NOTE is deliberately '' after two rounds of live developer feedback rejected both the original and the reworded copy; the element still exists for panel-lookup.js's shared guard clause) — quick task 260902-tli | ported | companion/test_status_pages_05b.py::test_lightbox_dialog_renders_once_wide_with_own_note_text |
| 240 | .airline-card__zoom neutralizes the base button rule's height/padding/border/background and declares the zoom cursor, and declares no pointer-events property anywhere — the retired orientation gate (a misreading of the developer's original request, corrected on the same live test) must not silently return | ported | companion/test_status_pages_05b.py::test_airline_card_zoom_stylesheet_contract |
| 241 | the mobile-only button override exists as the file's @media (max-width: 959.98px) block, declares a bare `button` rule with height: 36px and font-size: 14px, sits AFTER the base `button` rule in source order (the mechanism that lets it win at equal specificity), and the base rule's own desktop values (height: 30px, font-size: 13px) are untouched (06.6.4.1.1-03 D-18b) | ported | companion/test_status_pages_05b.py::test_mobile_button_override_block_and_source_order |
| 242 | .lightbox--wide's max-width equals illustration_normalize.ILLUSTRATION_TARGET_WIDTH — a future change to the normalized frame size cannot silently leave the dialog capped at a stale width | ported | companion/test_status_pages_05b.py::test_lightbox_wide_max_width_matches_illustration_target_width |
| 243 | exactly one lightbox replace form is rendered, and every card's zoom trigger carries a data-view-panel-replace-action attribute (one per illustrations.target_airline_names() entry) whose value, with the route prefix stripped, is a member of illustrations.target_filenames() — mirroring the existing image-source membership check | ported | companion/test_status_pages_05b.py::test_replace_form_action_matches_trigger_attribute_membership |
| 244 | the single lightbox replace form declares method="post", enctype="multipart/form-data" — a missing enctype would silently send the file as a filename string, a real failure mode, not a formality — and a literally present action="" placeholder for panel-lookup.js to overwrite | ported | companion/test_status_pages_05b.py::test_replace_form_declares_post_multipart_enctype_and_present_action |
| 245 | the whole rendered page carries exactly one <input type="file"> whose id equals airlines_page.REPLACE_INPUT_ID and is the target of a label's for attribute, and both the label and the file input live inside the framed zone wrapper (quick task 260903-df3) — the accessibility contract the move from per-card to shared must not lose | ported | companion/test_status_pages_06.py::test_replace_form_file_input_id_is_unique_and_labelled |
| 246 | render() with no effective state_dir produces no cache-busting query string anywhere; with a state_dir whose override directory holds Air France's override file, exactly one URL is busted, keyed on that file's own mtime, identically in both the <img src> and the zoom trigger's data-view-panel-src, every other card's URL stays unbusted, and Air France's own data-view-panel-replace-action stays the UN-busted URL while no replace-action value anywhere carries a cache buster | ported | companion/test_status_pages_06.py::test_cache_buster_absent_with_no_state_dir_and_keyed_on_mtime_with_an_override |
| 247 | a hostile airline name reaching the rendered page is escaped, never interpolated raw, including in its own data-view-panel-replace-action attribute; the now-airline-agnostic replace form's own markup (REPLACE_LABEL_TEXT and REPLACE_HINT_TEXT, quick task 260903-df3) carries no trace of the hostile name at all (extends T-06.6.4.1-05's existing discipline) | ported | companion/test_status_pages_06.py::test_replace_control_escapes_hostile_airline_name |
| 248 | the lightbox replace form's own markup offers no restoring or resetting of the original image (D-04, explicitly out of scope) - checked both within the form's own markup and as a membership test over this feature's surviving copy constants (REPLACE_LABEL_TEXT/REPLACE_BUTTON_TEXT/REPLACE_HINT_TEXT) | ported | companion/test_status_pages_06.py::test_replace_form_contains_no_revert_or_reset_control |
| 249 | the retired per-card replace disclosure left no dead markup (a real render() call), no dead stylesheet rule (companion/static/style.css read from disk), and no dead module surface (_replace_control_html/REPLACE_SUMMARY_TEMPLATE/REPLACE_LABEL_TEMPLATE) behind | ported | companion/test_status_pages_06.py::test_replace_control_retired_from_every_surface |
| 250 | the framed zone's upload glyph comes from layout.ICON_DEFS_HTML via layout.icon_html() — 'icon-upload' is a member of ICON_IDS, the rendered page carries exactly one matching <use> reference, companion/pages/airlines_page.py's own source contains no hand-written glyph-element token, and REPLACE_ICON_CLASS appears in the rendered icon's class attribute | ported | companion/test_status_pages_06.py::test_replace_zone_icon_comes_from_the_shared_sprite |
| 251 | exactly one .lightbox__replace-zone <div> is rendered, nested inside the single lightbox replace form; within it, the icon, label, hint, file input and Upload button appear in that order; the hint element's text equals REPLACE_HINT_TEXT; and companion/static/style.css (read from disk) contains LIGHTBOX_REPLACE_ZONE_CLASS, REPLACE_HINT_CLASS, REPLACE_ICON_CLASS and a '::file-selector-button' rule | ported | companion/test_status_pages_06.py::test_replace_zone_markup_and_styling_contract |
| 252 | all three upload-form renderings (the no-JS fallback's, the dialog's copy, and the lightbox replace form) keep their <input type="file" ... accept="image/png" required>, their single bare <button type="submit">, their hint paragraph, their method/enctype/action and exactly one <form> byte-identical to their pre-25-07 output — each now also carrying its own id and, as the form's LAST child after the submit button, a drop zone naming the very input it writes into (CFG-51/D19, 25-07-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_upload_forms_native_controls_are_unchanged_by_the_drop_zone |
| 253 | on a Step-B edit-mode Airlines render (the fallback panel's upload form, the dialog's copy and the replace form all at once) every emitted id is document-unique, every one of the three elements carrying data-upload-drop also carries layout.JS_GATE_CLASS ON ITSELF (boundary-anchored, so data-upload-drop-input cannot satisfy it), and with those three <section> subtrees excised the rest of the document contains zero preview, image, note, message, input-hook or --upload-preview-ratio markup (CFG-51/D-09, 25-07-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_drop_zone_ids_are_unique_and_no_drop_markup_escapes_the_js_gate |
| 254 | the framing preview reserves companion/illustration_normalize.py's OWN output frame (read from ILLUSTRATION_TARGET_SIZE, never a retyped ratio) through an inline --upload-preview-ratio that style.css reads with NO fallback value; every .upload-drop class and the [data-upload-drop-active] state resolve to real selectors on a selector boundary; and not one .upload-drop rule uses :hover, declares a colour literal or introduces animation (CFG-51/CFG-52, 25-07-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_preview_box_reserves_illustration_normalize_s_own_frame |
| 255 | _gap_rows_for_grid() thresholds at >= GAP_BLOCK_THRESHOLD (3), sorts eligible rows (-count, prefix), caps at GAP_BLOCK_CAP (12), and reports the exact overflow count for the rest (D-05/D-06) | ported | companion/test_status_pages_06.py::test_gap_block_threshold_sort_cap_and_overflow |
| 256 | _gap_card_html() renders the whole card as a real <a class="airline-card" href="/airlines?resolve={prefix}"> trigger with zero <img> tags and no nested .airline-card__zoom button, carrying every data-view-panel-* attribute UI-SPEC's Gap-card markup shape names, non-empty where that snippet shows a value (D-01/D-02/D-12) | ported | companion/test_status_pages_06.py::test_gap_card_markup_shape_and_attribute_vocabulary |
| 257 | a gap card's data-filter-group value is always a string-prefixed "gap{index}" (never a bare integer) and never collides, as a bare string, with any curated card's own data-filter-group value on the same render (RESEARCH.md Pitfall 4, T-14-17) | ported | companion/test_status_pages_06.py::test_gap_card_filter_group_never_collides_with_curated_integer_groups |
| 258 | _gap_overflow_html() returns the empty string when the cap does not bite, and otherwise the exact templated line naming the overflow count, with <a href="/health"> wrapping only MANUAL_OVERFLOW_LINK_TEXT and the trailing period sitting outside the anchor (D-07) | ported | companion/test_status_pages_06.py::test_gap_overflow_html_renders_only_when_the_cap_bites |
| 259 | an example_callsign containing '<', '>', '&' and '"' reaching a gap card renders fully escaped, both in data-view-panel-caption and in the visible callsign paragraph, exactly once per interpolation site (T-06.6.4.1-05, T-14-16) | ported | companion/test_status_pages_06.py::test_gap_card_escapes_hostile_example_callsign |
| 260 | _airline_card_html(index, airline_name, shapes, state_dir, manual_info=None) renders byte-identically to the default-omitted call, and a plain curated card with no manual history still wraps a real <button> (never an <a>), with mode="art" and every manual/resolve-prefix attribute empty (14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_manual_info_none_matches_todays_plain_card_and_keeps_button |
| 261 | an active manual_info triple renders the real <a href> trigger, the correct mode/heading/upload-action for both the has-artwork and needs-artwork cases, the delete-action attribute from _manual_delete_action(), an empty manual-note, and the 'Resolved by hand' chip (14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_active_manual_states_render_expected_attributes_and_chip |
| 262 | a needs-artwork manual card's first-seen/last-seen/count attributes are populated from unresolved_row_for_prefix() only when a live gap still exists for that prefix, fall back to empty once D-14 clears it, and stay empty on an art-mode card regardless of manual_info (14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_needs_artwork_sighting_context_conditional_on_live_gap |
| 263 | a superseded card never shows the operator's own orphaned upload: data-view-panel-src points at the built-in Air France illustration key (never a key derived from the entry's own stored name), the Superseded chip renders, and the manual-note interpolates the prefix, the built-in name, AND the operator's own originally-stored name (not the built-in name a second time) (D-10, 14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_superseded_shows_built_in_state_never_operator_upload |
| 264 | render()'s grid-injection step adds exactly one card for a genuinely novel active manual airline name not already among the curated pairs, and adds none for a superseded entry or for an active entry whose name is already curated (D-08, UI-SPEC's Grid injection, 14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_render_grid_injection_adds_exactly_one_novel_card_and_none_for_superseded_or_curated |
| 265 | the resolve section renders all four server-derived states and only the right controls in each: absent-from-registry (stale sentence, no form at all), seeded-gap-no-entry (Step A heading, name input, no file input), seeded-gap-with-artless-entry (Step B heading naming the stored airline, upload form action ending /{key}.png, a file input), and seeded-gap-with-resolved-entry (the already-resolved sentence, no file input) — D-03/D-11 | ported | companion/test_status_pages_06.py::test_resolve_section_four_states_render_correctly |
| 266 | Step A's rendered datalist carries exactly len(illustrations.target_airline_names()) (36 against today's data) <option> elements, the datalist's id matches the name input's list attribute, every airline name appears as an escaped <option value=...> exactly once (D-13), and the shared _resolve_name_form_html() output also carries an empty <p class="lightbox__resolve-scope"></p> for panel-lookup.js to write into on open (14-06-PLAN.md external gap-closure) | ported | companion/test_status_pages_06.py::test_resolve_section_datalist_contract |
| 267 | a stored airline name and example callsign both containing an angle bracket, a double quote and an ampersand render fully escaped everywhere they appear (including inside an attribute value), and a resolve_prefix differing from the stored registry key only in case or surrounding whitespace normalises to the identical prefix and renders the identical resolve section (WR-04/D-12) | ported | companion/test_status_pages_06.py::test_resolve_section_escapes_hostile_values_and_distrusts_query_string |
| 268 | CR-02: once D-14 clears a resolved prefix from the live gap registry, the resolve section still reaches Step B for a manual entry with no artwork yet (heading, file input, Skip link, no sighting-context <dl>), still reaches the already-resolved state once artwork exists under the re-added name (D-07's delete-and-re-add path), and still renders the stale sentence only once neither a live gap nor a manual entry exists for the prefix | ported | companion/test_status_pages_06.py::test_resolve_section_step_b_reachable_after_gap_cleared |
| 269 | the page's own top-to-bottom order is filter-bar, then illustration-grid, then the shared dialog's opening tag, then its closing tag, then (last) the resolve section's own back-link text — proving UI-SPEC's new page composition (resolve section moved to the bottom, behind the shared dialog) shipped for real | ported | companion/test_status_pages_06.py::test_page_composition_order_matches_ui_spec |
| 270 | with an empty manual-resolutions registry, render() emits no .manual-summary element and none of the retired management table's own copy; with two entries seeded (one superseded, one active), .manual-summary renders exactly once with text matching MANUAL_SUMMARY_TEMPLATE's total/superseded count (D-11, 14-06-PLAN.md Task 2 item 1) | ported | companion/test_status_pages_06.py::test_manual_summary_line_replaces_retired_management_table_copy |
| 271 | the retired D-06 supersession machinery's own symbols (SUPERSEDED_MARKER_TITLE, SUPERSEDED_CAPTION, SUPERSEDED_STATUS_CLASS) are gone, and the Superseded chip itself still renders end to end via render() — the card-level attribute/note contract is Task 1's own check's job, not re-tested here (14-06-PLAN.md Task 2 item 2) | ported | companion/test_status_pages_06.py::test_manual_section_supersession_symbols_retired_and_chip_still_renders |
| 272 | importing companion.pages.airlines_page raises no error, and the module exposes none of the six retired management-table rendering functions or eight now-orphaned copy/class constants (14-06-PLAN.md Task 2 item 3) | ported | companion/test_status_pages_06.py::test_retired_management_table_symbols_are_gone |
| 273 | _seed_manual_resolutions() seeds through manual_resolutions.add_entry() alone; both seeded airline names render on the Airlines page, and _manual_resolution_rows() reports superseded=True for exactly the static-table prefix (AFR) and False for the novel one (XQZ) (phase 14 plan 14-01 Task 3) | ported | companion/test_status_pages_06.py::test_manual_section_seed_helper_end_to_end |
| 274 | health_page.RESOLVE_LINK_HREF_TEMPLATE equals the template derived from airlines_page.AIRLINES_ROUTE and airlines_page.RESOLVE_QUERY_PARAM — the cross-module equality check airlines_page.py's own comment already claims exists (WR-06) | ported | companion/test_status_pages_06.py::test_health_resolve_link_template_matches_airlines_route_constants |
| 275 | the D-09 amendment's permanent regression proof: rendering ?resolve={prefix} for a prefix with a manual entry produces exactly one _manual_delete_form_html() output inside the shared dialog (action="") and exactly one inside the no-JS fallback section (the real delete action) — one shared function, two call sites (14-06-PLAN.md Task 2 item 4) | ported | companion/test_status_pages_06.py::test_manual_delete_form_renders_in_both_dialog_and_no_js_fallback |
| 276 | companion/static/list-filter.js gains an optional, guarded [data-filter-set] lookup whose click handler sets the filter input's value from the clicked element's own attribute and calls the file's one existing applyFilter() — the file still has exactly one [data-filter-text] query, stays ES5-safe, and introduces no network call or timer (phase 14 plan 14-03 Task 1, RESEARCH.md Pitfall 5, D-11's summary-line mechanism) | ported | companion/test_status_pages_06.py::test_list_filter_js_gains_data_filter_set_hook |
| 277 | style.css declares the new/extended selectors UI-SPEC's Component Inventory enumerates (a.airline-card, .airline-card__placeholder, .lightbox__heading:empty, .lightbox__manual-note:empty) with their exact declaration values, .manual-summary's own base rule is GONE with only its hover surviving on the chip's own 12% wash (X7, 22-11-PLAN.md Task 2 — the copied [data-filter-clear] property list is replaced by reuse of .airline-card__chip, whose label-voice declarations are pinned here instead), .airline-card__placeholder's aspect-ratio string-equals .airline-card__image's, .lightbox__replace's selector is extended to a three-way group with .lightbox__resolve-name/.lightbox__delete in exactly one declaration block (never duplicated), the header accent-reservation list mentions none of the new selectors, none of the new/extended rule bodies declares a new custom property, and .manual-resolution__status--superseded is gone now that plan 14-06 has retired it (phase 14 plan 14-03 Task 2, retargeted in place by 14-06 Task 2) | ported | companion/test_status_pages_06.py::test_phase14_task2_new_css_selectors_exhaustive |
| 278 | the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris): the Frame strip renders the held copy with the neutral dot--off and zero warn/error tokens anywhere, including no 'Expected since'/'Attendu depuis' (X2, D-03/CFG-26) | ported | companion/test_status_pages_06.py::test_frame_strip_nightly_regression_held_is_neutral_never_warn |
| 279 | a due result renders byte-identical copy and classes whether 'now' is before next_wake or up to 2x the effective interval past it — the grace window is invisible (22-UI-SPEC.md §3.3 rule 3) — with the countdown present in both renderings, marked, pointed at the same instant, and neither rendering carrying a warn/late/overdue token anywhere (retargeted in place by 23-06-PLAN.md Task 2, which added the one element in that cell that is a function of `now` by construction) | ported | companion/test_status_pages_06.py::test_frame_strip_due_is_identical_inside_and_outside_the_grace_window |
| 280 | a late result renders the warn dot and 'Expected since HH:MM', with the headline's own text-colour class staying the plain status-card__headline--warn hook (never a status colour as text, 22-UI-SPEC.md §3.3 rule 2) | ported | companion/test_status_pages_06.py::test_frame_strip_late_result_carries_warn_dot_and_plain_text_colour_class |
| 281 | with a parked frame (ctx['battery_critical']=True), wake_interval_s 300 and a 20-minute-old check-in, the frame strip does NOT show the late state - the identical setup without the park does (quick task 260923-fr4) | ported | companion/test_status_pages_06.py::test_frame_strip_parked_suppresses_late_state |
| 282 | the Frame strip renders no update headline and claims no state when there is no check-in recorded at all (frame_state.STATE_UNKNOWN) | ported | companion/test_status_pages_06.py::test_frame_strip_no_checkin_renders_no_update_cell_and_claims_no_state |
| 283 | all three Frame-strip cells share one wrapper and one three-row internal grid (identical row-class lists), while only the two switch cells' outer wrapper keeps the quick-action--on/off control-state left edge (B13) | ported | companion/test_status_pages_06.py::test_frame_strip_three_cells_share_one_row_structure_switch_cells_keep_left_edge |
| 284 | a rendered Frame strip contains exactly 2 occurrences of the literal attribute data-quick-switch, one on each strip switch form (D-04 handshake with plan 22-05) | ported | companion/test_status_pages_06.py::test_frame_strip_both_switch_forms_carry_data_quick_switch_exactly_twice |
| 285 | companion/layout.py no longer computes an age_seconds(next_wake...) >= 0 warn trigger — the strip consumes frame_state.resolve_state(), it never re-derives lateness (CFG-26) | deleted | S: asserted source text (companion/layout.py grepped for a retired age_seconds(next_wake...) re-derivation); redundant with the frame-strip behaviour checks in this module (rows 278-284), which already prove every late/due/parked/grace-window scenario against frame_state.resolve_state()'s own output |
| 286 | the .frame-strip__cells block declares align-items: stretch and zero align-items: center (B13) — a block-scoped check, since a line-wise grep pipe would already read 0 on the unmodified file (the selector and declaration sit on different lines) and pass vacuously | ported | companion/test_status_pages_06.py::test_frame_strip_cells_stretch_not_center |
| 287 | the .frame-strip__cell button quiet-button rule (C2) appears at a later line than button[type="submit"], carries no !important and no id selector, and reuses the base quiet wash (4.5%/9%) verbatim — never a new wash value (T-22-13) | ported | companion/test_status_pages_06.py::test_frame_strip_cell_button_quiet_rule_after_submit_no_important_no_id |
| 288 | the .stat-tile hover/focus-within block declares zero border-color: transparent and both border-inline-color and border-block-end-color (T9: the top status/accent rail survives hover), and the whole reveal is :not(.frame-strip)-scoped so the strip never lifts | ported | companion/test_status_pages_06.py::test_stat_tile_hover_three_edge_frame_strip_excluded |
| 289 | the Phase 21 .frame-strip__cell--update .status-card__headline heading-size override is gone — the line returns to its own 16px semibold Emphasis base (C6) | ported | companion/test_status_pages_06.py::test_frame_strip_update_headline_no_heading_size_override |
| 290 | the one .time-value role (C5) declares --font-ui and tabular-nums, with a --primary modifier stepping up to body-size + semibold — no new token, no new family, no new size | ported | companion/test_status_pages_06.py::test_time_value_role_defined_once |
| 291 | the style.css header comment's accent-reservation list is edited to record C2's delta (the Frame strip's two switch buttons are no longer accent-filled) — the arithmetic is written into the comment, not merely asserted (22-UI-SPEC.md §1) | deleted | C: asserted a stylesheet comment (the header's own accent-reservation-list prose recording the C2 delta); no rendered behaviour |
| 292 | the tab bar is display:none until the 959.98px boundary, then fixed to the viewport bottom at 56px plus the safe-area inset on the nav surface with a top hairline, the resting overlay shadow and NO border radius (it is edge-anchored); its cells are `flex: 1 1 0`; its active state reuses the app's one 12%-accent-wash pill idiom byte-for-byte with a :not()-scoped hover placed after it; its label is 11px regular with no label voice; and .has-tab-bar clears the bar at the page foot (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_tab_bar_css_geometry_surface_and_active_idiom |
| 293 | the .tab-bar__pill's horizontal margin, resolved from style.css's own --space-xs/--space-sm tokens, leaves at least the longest NAV_GROUPS label's own required width (a measured 6.5px/character advance derived from the 2026-09-17 audit's real 'Compagnies' figure, floored at that audit's own 65px) inside the tab cell at the app's 360px floor viewport, while `.tab-bar__link`'s own 56px height and `flex: 1 1 0` width basis stay byte-identical (CFG-82, 29-02-PLAN.md) | ported | companion/test_status_pages_07.py::test_tab_bar_pill_horizontal_margin_lets_the_longest_label_fit |
| 294 | the More sheet opens upward from the fixed bar (absolute, bottom: 100%, right: 0) on the nav surface with the overlay shadow, reuses .mobile-nav__link's 44px/16px geometry rather than restating it, leaves .mobile-nav's in-flow flex-basis push-down untouched, and the stylesheet itself records why this absolute positioning is not a reversal of the rejected-overlay verdict (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_tab_bar_more_sheet_opens_upward_and_reuses_the_dropdown_row |
| 295 | under lang='fr' every tab-bar label reads French — Accueil / Affichage / Vols / Compagnies / Plus, with État and Appareil inside the More sheet — and the landmark name is 'Navigation principale' (B16/CFG-29, 22-14-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_french_tab_bar_labels_and_landmark |
| 296 | the nav state reminder renders as a <span> with no href on Home, announcing ONLY the state, and stays an <a href="/" > with its destination-naming label everywhere else — in both nav copies, each with its two nowrap segments (B10/D-04, 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_nav_status_is_a_span_on_home_and_a_link_everywhere_else |
| 297 | exactly ONE open-state max-height governs the dropdown (320px, pinned against a measured 165px of reduced French content at 390px — both the 420px and 640px values are gone, not re-tuned), the dropdown's dead nav selectors are deleted while .mobile-nav__link survives for the tab bar's sheet, and .nav-status is a wrapping flex row of nowrap segments whose hover underline is anchor-scoped (T11/B10, 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_one_open_dropdown_max_height_and_no_dead_dropdown_nav_rule |
| 298 | companion/static/style.css carries zero stray comment terminators and ends outside a comment — the structural guard for a real parse-error class that drops whole rules while leaving the source text a string-comparison harness reads as correct (22-14-PLAN.md Task 2, Rule 1) | ported | companion/test_status_pages_07.py::test_style_css_carries_no_stray_comment_terminator |
| 299 | every <details> carries an explicit summary::before chevron that rotates on [open] through a child combinator — including the bottom tab bar's More summary, where it is taken out of flow so a marker cannot narrow the cell, and with its own inverted rotation because that sheet opens upward — with the prefers-reduced-motion block count unchanged at two; and no .data-table-wrap th rule survives to claim sticky positioning a wrapper with no height could never provide (T3/T4, 22-15-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_every_disclosure_has_a_marker_and_no_header_claims_to_stick |
| 300 | freshness.js no longer stops dead on a failure: stopLoop() survives only as its definition and its two deliberate background-tab teardowns, a bounded exponential ladder starting AT the normal cadence (so a failing server sees a strictly decreasing rate) replaces it, a success resets the backoff, an in-flight guard stops two fetches racing, the swap skips unchanged regions and any region holding focus, the state badge is .banner__pill with the NEUTRAL .dot--off and no warn token anywhere in the file, style.css carries the .banner__pill[hidden] display guard the badge depends on, and both strings render onto <body> in both languages matching the script's own English fallbacks byte for byte (T13, 22-15-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_refresh_loop_retries_with_backoff_and_says_so_neutrally |
| 301 | style.css declares .resolve-context[hidden] { display: none; } after the base rule — without it, an author display declaration beats the UA [hidden] rule and every ordinary illustration's resolve-context block renders empty instead of hidden (quick task 260921-n2n Task 2) | ported | companion/test_status_pages_07.py::test_resolve_context_hidden_guard_present_after_base_rule |
| 302 | style.css's .flight-detail-row__grid margin-bottom is at least 2x .copy-btn::before's own inset magnitude — CFG-70's measured 22px hit-target floor made executable rather than a comment; this is the check that would have failed had this quick task's own source data's 'reduce to var(--space-md)' suggestion been taken (quick task 260921-n2n Task 5) | ported | companion/test_status_pages_07.py::test_flight_detail_row_grid_margin_never_shrinks_below_cfg70_floor |
| 303 | the hamburger toggle's accessible name describes the preferences panel it now opens ("Account and preferences" / "Compte et préférences"), and the retired "Open menu" translation is deleted rather than orphaned (X9/D-10/B16, 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_nav_toggle_label_now_describes_the_preferences_panel |
| 304 | the save bar's own sub-960px geometry and its z-index: 30 at both breakpoints are RESTORED — the .dirty-ready marker class is not (this restoration's own clearance mechanism is :has(.dirty-bar), which works with scripts blocked) — while the tab bar's own stacking value (20) and its own content clearance are unmoved (D-10/T7, 22-14-PLAN.md Task 3; retired by 27-04-PLAN.md/CFG-63, restored by 28-08-PLAN.md Task 3/CFG-77/CFG-78) | ported | companion/test_status_pages_07.py::test_save_bar_geometry_is_restored_and_the_tab_bar_stacking_survives |
| 305 | the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris), pinned as ONE named check: the strip renders the held copy with the neutral dot, Health's Frame tile renders the SAME clock time, the nav notification dot is unlit, and the rendered Health HTML carries zero warn/error dots, zero warn tile/headline modifiers and neither 'Expected since' nor 'Attendu depuis' (X2, D-03/CFG-26) | ported | companion/test_status_pages_07.py::test_health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn |
| 306 | inside the grace window with no hold, the tile reports the normal ('ok') state and the strip reports the due copy — they agree (22-UI-SPEC.md §3.3 rule 3) | ported | companion/test_status_pages_07.py::test_health_inside_grace_window_tile_and_strip_agree_normal |
| 307 | past the grace window with no hold, both the tile ('warn') and the strip ('Expected since') report late, and the nav notification dot lights | ported | companion/test_status_pages_07.py::test_health_past_grace_window_both_report_late_dot_lights |
| 308 | a frame whose (non-held) next wake has passed and whose own grace has since elapsed is reported late by both the tile and the strip — held cannot suppress lateness forever | ported | companion/test_status_pages_07.py::test_health_held_window_ended_and_grace_elapsed_both_report_late |
| 309 | companion/static/style.css's own dot--* class-name occurrence count is unchanged by this plan (9 before, 9 after) — this plan adds no dot class | ported | companion/test_status_pages_07.py::test_dot_modifier_classes_are_exactly_four_no_new_class_added |
| 310 | the quiet cell's caption link is present on BOTH Home's and Display's own real render() output, with the IDENTICAL href on both — asserted as one check whose failure names the page missing the link or the two hrefs when they differ, never two separate per-page checks (CFG-69, D-23, 27-08-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_the_quiet_schedule_link_is_one_write_site_reaching_both_pages |
| 311 | layout.frame_strip_html() renders exactly two role=switch controls whose aria-checked is the SAVED value in both directions, named by the setting through aria-labelledby and described by the state span, over the unchanged <form>/state/return_to/data-quick-switch the server already acts on — with the retired action wording gone, both state wordings present with exactly one hidden, and one pending-marker region per switch (D2/CFG-36, X1/D-04, 23-07-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_the_strip_renders_two_server_rendered_switches |
| 312 | the optimistic switch's failure copy is the app's own generic flash sentence, translated on <body> in both languages and carrying no status code, URL or server internal, and the shell renders exactly one EMPTY assertive live region for it — a transient toast, never a permanent banner (D2/CFG-36, V7/T-23-27, 23-07-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_the_failure_toast_is_transient_translated_and_carries_no_internal |
| 313 | Health's freshness line carries exactly one neutral, aria-hidden live dot — the app's own off dot with no status or accent token and no breathing class at render time, because the motion belongs to the loop that knows whether it is listening (D22, 23-05-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_health_freshness_line_carries_a_neutral_live_dot |
| 314 | Health's freshness line is a <time data-relative> over the same instant data-loaded-at carries whose SERVER text is the clock — never the ladder's zero bucket, which is the frozen age A-20 removed — with the absolute timestamp still in the element's tooltip, exactly one data-loaded-at and one data-refresh-pill page-wide, and the wrapper still a swap target (D22's remainder, 23-05-PLAN.md Task 2; the no-JS half retargeted in place by 23-06-PLAN.md) | ported | companion/test_status_pages_07.py::test_health_freshness_clock_is_a_ticking_age_over_the_loaded_at_instant |
| 315 | freshness.js DERIVES the breathing class from its own interval handle and state badge in one function, called from exactly the four places its state already changes, carries no status vocabulary, leaves 22-15's retry ladder/ceiling/in-flight guard/targeted swap untouched, and agrees with both the Python hook and the CSS rule (T-23-15, 23-05-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_freshness_js_breathes_only_from_the_loops_own_state |
| 316 | GET /health, GET /airlines and GET /history all return 200 with their own page heading against a real running service, /health's real HTTP response body carries the page purpose, both section descriptions, no duplicated freshness label, the auto-refresh pill (hidden) and zero stale-banner markers, the nested modifier twice, the prose modifier once, both readout spans, no raw ISO in the readout's own slice, and the desc-class cells at their expected count after the Resolution-statistics heading, /airlines' real HTTP response body carries zero occurrences of the retired per-card replace class, exactly one lightbox replace form and one action="" and one file input, and at least one un-busted replace-action trigger attribute, /history's real HTTP response body carries zero occurrences of the replace-form class, replace-action attribute, enctype or file input (quick task 260903-btu Task 5a), and the real served stylesheet (STYLE_ROUTE) carries the description-column rule, the demotion rule's new bottom margin and the prose rhythm rule's selector, and the real served freshness script (FRESHNESS_SCRIPT_ROUTE) carries the interval constant, the visibility-change listener, the [data-loaded-at]/[data-refresh-pill] attribute hooks, carries zero occurrences of the deleted data-pause-text/wireToggle pause-branch hooks (D-18), and every health_page.REFRESH_SWAP_SELECTORS entry verbatim (quick task 260901-tsa; extended in place by quick task 260901-uzi finding 1/2/3/4, quick task 260902-bl2 Task 3, quick task 260902-chc, quick task 260903-btu Task 5a, 19-09-PLAN.md Task 3, and 21-02-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_both_tabs_ok_end_to_end |
| 317 | GET /illustration/{key}.png against a real running service serves normalized bytes that differ from the raw vendored file and decode to illustration_normalize.ILLUSTRATION_TARGET_SIZE, and an unknown key still 404s | ported | companion/test_status_pages_07.py::test_illustration_route_serves_normalized_bytes_end_to_end |


### Part 01 (plan 33-25)

Rows 1-37 (part 01, original `check()` calls #1-#37) plus one out-of-order
row (151, `anomaly_active()`'s root-unsafe degrade-safely check, pulled forward
per 33-MIGRATION-RULES.md rubric T) are `ported` to
`companion/test_status_pages_01.py`.

Rubric codes: 34 B/D (calls `companion.pages.health_page`/`companion.wake`/
`companion.layout` directly and asserts on the return value or the rendered
HTML — battery ring/chart/hit-target checks parse the SVG structurally via
`companion_markup.parse_html()` instead of regex over the raw string), 1 S
(row 7, `companion/wake.py`'s import boundary — rewritten as a `child_env()`
subprocess `sys.modules` probe instead of a source grep), 1 T (row 151, the
pulled-forward `anomaly_active()` check — every "missing state_dir" input now
uses a `tmp_path` subpath instead of a fixed absolute path outside the repo
production code could create as root, closing T-33-25-01 and the status-pages
half of 32-REVIEW.md IN-05). No deletions in this slice.

New module: `companion/test_status_pages_01.py` (38 tests: 37 ported part-01
checks plus the 1 pulled-forward `anomaly_active()` check).
`companion/test_status_pages_helpers.py` is new too (seeding helpers this
part barely uses beyond `seed_device_health`/`seed_meta`/`seed_runway_events`
and `stat_tile_slices` — front-loaded for 33-26..33-31's later sections, same
precedent as 33-14's `test_companion_app_helpers.py`).

### Part 02 (plan 33-26)

Rows 38-85 (part 02, original `check()` calls #38-#85) are `ported` to
`companion/test_status_pages_02.py`.

Rubric codes: 44 B/D (calls `companion.pages.health_page`/`companion.draw`/
`companion.wake`/`companion.layout` directly and asserts on the return value
or the rendered SVG/HTML, in the legacy harness's own substring/regex style
per 33-25's precedent), 3 C (rows 43, 44, 46 — `.battery-trend-section
svg:not(.icon)`, `.sparkline-area`/`.sparkline__area` and
`.sparkline-threshold`/`.sparkline-swatch` raw `style.css` reads, rewritten
against a served stylesheet via `companion_markup.declarations_for()`/
`rules_with_selector()`/`css_rules()`), 1 J (row 70, `battery-trend.js`'s raw
disk read, rewritten as a `served_asset()` fetch). No deletions in this
slice; two partial S-rubric trims inside otherwise-ported checks (not
counted as separate rows — the check's remaining assertions are still
`ported`):

- Row 46 dropped `open(health_page.__file__).read()`'s "the millivolt
  threshold is never re-typed into health_page.py's own source" assertion
  (no observable rendered consequence — the check's remaining assertions,
  that the threshold's VALUE and placement come from `companion/battery.py`,
  are unaffected).
- Row 55 dropped `inspect.getsource(fn)`'s sweep for forbidden interval-
  arithmetic tokens (banned outright by `test_suite_guards.py`'s G2 rule,
  same precedent as 33-25's `_battery_section()` arity fix; the check's own
  `fn.__code__.co_names` reuse sweep, not a source-text read, is kept).

Seven old checks (rows 58, 73, 74, 75, 77, 78, 81) each contained a
per-case/per-severity loop and became `@pytest.mark.parametrize` tests per
this plan's own Task 1 instruction; the ledger row for each points at its
PRIMARY parametrized node id, with the sibling ids listed in the plan's
SUMMARY (33-MIGRATION-RULES.md section 3, "one old check splits into
several tests"):

- Row 58: primary `test_check_in_disclosure_moved_clauses_render_across_all_four_cases[observed, cadence known]`; siblings `[observed, cadence unknown]`, `[not observed, cadence known]`, `[not observed, cadence unknown]`.
- Row 73: primary `test_device_tile_verdict_matches_state_at_each_severity[ok]`; siblings `[warn]`, `[error]`.
- Row 74: primary `test_pipeline_tile_verdict_matches_state_at_each_severity[ok]`; siblings `[warn]`, `[error]`.
- Row 75: primary `test_corroboration_tile_verdict_matches_disagreement_state[agree]`; sibling `[disagree]`.
- Row 77: primary `test_one_tile_anatomy_across_every_health_tile[seeded]`; sibling `[fresh]`.
- Row 78: primary `test_only_one_saw_it_is_neutral_and_still_distinct[en-Both agree-Only one saw it]`; sibling `[fr-Les deux concordent-Une seule l'a vu]`.
- Row 81: primary `test_resolution_detail_line_has_a_singular_form[total=1-en]`; siblings `[total=1-fr]`, `[total=2-en]`, `[total=2-fr]`, plus the trailing French-catalogue-entry assertion split into its own
  `test_resolution_detail_templates_have_french_catalogue_entries`.

New module: `companion/test_status_pages_02.py` (62 pytest node ids
covering the 48 baseline rows in this slice: 41 rows ported 1:1 to a single
node id, 7 rows ported to a parametrized test totalling 20 node ids across
them, plus 1 extra split-off test — 41 + 20 + 1 = 62). A `_module_server`/
`css_text`/`battery_trend_js` module-scoped read-only server fixture set is
new in this module, for the 3 C/J-rubric checks above — no test in this
part mutates server state, so a shared read-only server is safe
(33-MIGRATION-RULES.md section 2).

### Part 03 (plan 33-27)

Rows 86-139 (part 03, original `check()` calls #86-#139) are `ported` to
`companion/test_status_pages_03.py`.

Rubric codes: 43 B/D (calls `companion.pages.health_page`/`companion.layout`/
`companion.i18n`/`companion.prefs`/`companion.wake` directly and asserts on
the return value or the rendered HTML, in the legacy harness's own
substring/regex-over-rendered-markup style per 33-25/33-26 precedent), 9 C
(rows 122, 130, 131, 132, 134, 135, 136, 137, 138 — the `.section-caption`/
`BATTERY_SECTION_CLASS`/doubled-form-status/hover-source-order/`.section-
intro`+`.stat-tile__value .mono`+`.battery-readout`/`.dashboard-grid`/
`.data-table th`/nested-heading-tier/`.stat-tile__caption` raw `style.css`
reads, all rewritten against the served stylesheet via
`companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`/
`custom_properties()` — never a regex/substring probe over the served text,
per 33-FOLLOWUPS.md F-01), 1 J (row 92, `battery-trend.js`'s raw disk read,
rewritten as a `served_asset()` fetch), 1 S (row 105, the `health_page.py`
"never imports the stdlib html module" grep, rewritten as `not hasattr(
health_page, "html")` — a bare `import html` binds the name directly into
the module's own namespace, so this is a real behavioural proof).

One `deleted`-free but fully rewritten S-rubric row, and the plan's own
named hotspot: row 121 (the legacy "companion/pages/health_page.py still
contains zero HTML form elements and exactly one '<button' literal" check)
read `health_page.py`'s own source text, where the "one `<button`" was a
docstring mention, never rendered markup. `ported`, not `deleted`, because
the check DOES have observable rendered consequences — rewritten as
`test_health_still_has_no_form_and_no_button_in_any_state`, parametrized
over four seeded Health render states (`normal`, `anomaly`, `source_fault`,
`empty`): each is rendered, parsed with `companion_markup.parse_html()`,
and asserted to contain zero `<form>` and zero `<button>` elements —
`health_page.render()` returns a content fragment only, with no shared nav
chrome, so the true rendered contract carries none of the legacy check's
"exactly one" exception at all. Per 33-MIGRATION-RULES.md section 3 ("one
old check splits into several tests"), the ledger row points at the primary
parametrized node id, with the sibling ids listed here:

- Row 121: primary `test_health_still_has_no_form_and_no_button_in_any_state[normal]`; siblings `[anomaly]`, `[empty]`, `[source_fault]`.

New module additions: `companion/test_status_pages_03.py` extends part 02's
module-split convention with 57 pytest node ids covering the 54 baseline
rows in this slice (53 rows ported 1:1 to a single node id, 1 row ported to
a 4-case parametrized test — 53 + 4 = 57). Reuses part 02's exact
`_module_server`/`css_text`/`battery_trend_js` module-scoped read-only
server fixtures (no test in this part mutates server state either) — no new
fixture family was needed for this slice's 9 CSS checks.

`companion/test_status_pages.py` (the legacy harness) shrinks from
`EXPECTED_CHECK_COUNT = 231` to `EXPECTED_CHECK_COUNT = 177` (231 - 54);
part 03's 54 checks and their own closures are removed from `main()`.
`_battery_section_heading()`/`_tile_slice_by_caption()`/`_stat_tile_slices()`
(module-scope helpers this part used, alongside still-pending later
sections) are left in place — `_battery_section_heading()` is still called
by pending rows well past this slice's boundary (confirmed live: the
shrunk harness runs 177/177 green standalone).

### Part 04 (plan 33-28)

Rows 140-171 (part 04, original `check()` calls #140-#171, minus row 151
which 33-25 already pulled forward) are `ported` to
`companion/test_status_pages_04.py`, except row 154 which is `deleted`.

Rubric codes: 20 B/D (rows 140-141 partial structural halves aside, mostly
calls `companion.pages.health_page`/`companion.layout`/`companion.i18n_fr.
health` directly and asserts on the return value or the rendered HTML, in
the legacy harness's own substring/regex-over-rendered-markup style per
33-25/33-26/33-27 precedent), 9 C (rows 140 partial, 141 partial, 142
partial, 144, 146 partial, 149, 157, 161 partial, 162, 163, 164 partial —
the nested-card heading/prose rhythm rules, the `data-table--prose`/
`.data-table td.desc` pair, the `.data-cards` toggle contract, the
`.data-table--registry` stacked-cell selectors, `.mono`/`.battery-readout__
detail`, the `.refresh-pill` family, the UIR-03/07/12/13 rule set, the
`.dashboard-grid`/`.battery-trend-section` spacing pair, the desktop-
padding/mobile-density pair, and the bare `summary` rule — all rewritten
against the served stylesheet via `companion_markup.css_rules()`/
`declarations_for()`/`rules_with_selector()`, never a regex/substring probe
over the served text, per 33-FOLLOWUPS.md F-01), 8 J (rows 148, 155, 165,
166, 167 partial, 168 partial, 169 partial, 171 — `battery-trend.js`/
`freshness.js` fetched via `served_asset()` instead of a raw disk read;
several of these need the file's own quoted string literals intact, so
they strip comments with this chain's own new
`strip_js_line_and_block_comments()` helper rather than
`companion_markup.strip_js_comments_and_strings()`, which erases string
literals too), 2 S (rows 167 and 170, each a partial drop — see below), 1
P/J deletion (row 154).

Row 154 (the legacy "the D-12 reversal (260902-chc) is written down at both
prose sites it touches ..." check) is `deleted`, reason: `P: asserted
plan-history prose in a freshness.js header comment and in a .planning
CONTEXT.md; no behaviour` — it opened `companion/static/freshness.js` for a
quick-task identifier and the house "SUPERSEDED" token, and separately
opened a phase context document under the planning tree for the same pair
beside the original decision's wording. No rendered or served behaviour
sat behind either assertion.

Two rows are `ported` with one clause of their original legacy check
dropped in place, rather than carried forward verbatim (TST-12 rubric S):

- Row 167 (the swap registry's one-definition-site/one-key-set check) used
  to grep `companion/pages/health_page.py`'s own source for the literal
  `"REFRESH_SWAP_SELECTORS = ("` (to prove no second tuple is defined
  there) and for the bare substring `"REFRESH_SWAP_SELECTORS"` (to prove
  the name still exists). The first is dropped as redundant: the identity
  check right beside it (`health_page.REFRESH_SWAP_SELECTORS is registry[
  layout.REFRESH_PAGE_HEALTH]`) already fails if a second tuple literal
  shadowed the import, since Python never interns two distinct tuple
  literals defined in different modules as the same object. The second
  becomes `hasattr(health_page, "REFRESH_SWAP_SELECTORS")`, a direct
  behavioural equivalent.
- Row 170 (Flights joining the swap loop) used to grep
  `companion/layout.py`'s own source for a comment paragraph explaining,
  in prose, why the filter-input elements are excluded from Flights' swap
  regions. Dropped: a served page or script cannot disagree with a
  comment's wording, and the check's structural half (which elements
  Flights' registry entry names, and which it excludes) is unchanged and
  fully ported.

New module: `companion/test_status_pages_04.py` (30 pytest node ids
covering the 31 non-deleted baseline rows in this slice: 30 rows ported
1:1 to a single node id — one fewer node id than rows because none of this
part's checks needed splitting). Reuses part 02/03's exact
`_module_server`/`css_text`/`battery_trend_js` module-scoped read-only
server fixtures, plus a new `freshness_js` fixture of the same shape (no
test in this part mutates server state, so a shared read-only server
stays safe per 33-MIGRATION-RULES.md section 2).

`companion/test_status_pages.py` (the legacy harness) shrinks from
`EXPECTED_CHECK_COUNT = 177` to `EXPECTED_CHECK_COUNT = 146` (177 - 31);
part 04's 31 checks and the one closure only they used
(`_js_code_without_comments()`) are removed from `main()`. This part's
own slice contains the audit's `.planning`/ticket-ID evidence sites (the
deleted row 154): after this plan, no status-pages check reads a
`.planning/` file, and `grep -c '"\.planning"' companion/test_status_
pages.py` is 0.

### Part 05 (plan 33-29)

72 rows `ported` (73 baseline rows minus 1 `deleted`), one row `deleted`.
Three rows (181-183, the 52-vendored-illustration checks) each map to a
single primary parametrized node id — `[air-algerie.png]`, the first
sorted vendored filename — out of 52 ids each: `pytest --collect-only`
confirms all 156 instances collect; the SUMMARY lists the other 51 ids
per row.

- Row 185 (`no module anywhere under companion/ defines its own
  alpha-threshold constant`) is `deleted` (TST-12 rubric S): a companion-
  package-wide grep for a second `ALPHA_THRESHOLD` assignment, with no
  behaviour beyond what rows 183's own centred/unclipped-bbox checks
  already prove by calling `server.plane.render._opaque_bbox()` directly
  — a stray, unused constant elsewhere in the package would never change
  what those checks observe.
- Row 172 (the freshness-line check) is `ported` with two source-text
  sub-clauses dropped in place (rubric S): its own grep of `companion/
  pages/health_page.py`/`companion/layout.py` for the literal
  `class="page-header__freshness` substring is redundant with the SAME
  check's rendered-equality proof (`built in rendered` against `layout.
  freshness_line_html()`'s own output, for both Health and Home) —  a
  second, unused definition of that markup could exist in health_page.py
  and never be observed unless it were actually rendered, which the
  equality check already rules out.
- Row 208 (`relative_age_text()`'s positional signature) is `ported` with
  its `inspect.getsource()` call (rubric S) rewritten as a behaviour
  proof: a positional call in the pinned order (`age_seconds`, `lang`)
  compared against the same call spelled out with both keyword names — a
  signature that quietly swapped the two would satisfy the keyword call
  but not the positional one.
- Row 174 (the strip countdown) and row 175 (the picture fade) are
  `ported` with their `companion/static/*.js` source scans (rubric J)
  rewritten to fetch every served script through `companion/app.py`'s own
  `*_SCRIPT_ROUTE` registry (enumerated from the live module's attributes,
  never a `companion/static` directory listing) and strip only comments
  with this chain's `strip_js_line_and_block_comments()`. Row 175's
  stylesheet half goes through `companion_markup.keyframes()`/
  `declarations_for()` against the served stylesheet instead of a disk
  read (33-FOLLOWUPS.md F-01).
- Rows 230 and 231 (the Safari autofill-suppression sweep and the
  hyphen-free-filter-id sweep) are `ported` with their `ast`-based
  module-wide source scans (rubric S) rewritten to rendered-page
  behaviour: every `<input type="search">` this app renders today —
  Compagnies' gallery filter, Health's registry filter (seeded so it
  appears) and Flights' history filter — is parsed structurally
  (`companion_markup.parse_html()`) and checked for the three suppression
  attributes and a hyphen-free id; row 231's `*_FILTER_INPUT_ID` half is
  ported as a direct check of the three real production constants (never
  source text). Guard G2 bans `ast`/`inspect` introspection of production
  source in this suite, so the legacy checks' forward guard against a
  hypothetical FOURTH filter bar not covered by these three renders is a
  known, narrower scope than the static analysis provided — there is no
  forward-guarding mechanism available under TST-12 that does not itself
  read production source as text.
- Row 234 (`airlines_page.py` imports no history-database/sqlite module)
  is `ported`, rewritten from a source grep to a runtime check of
  `airlines_page`'s own module namespace (`vars(airlines_page)`): which
  name IS bound there is a fact about `airlines_page.py`'s own import
  statements. Deliberately NOT a `sys.modules`-membership check (33-25's
  own `test_wake_module_never_imports_pages_or_app()` pattern): `poll_
  loop`, which this module is required to import, itself imports
  `sqlite3`/`server.history_db`, so `sys.modules` would carry both
  regardless of what `airlines_page.py`'s own source says.
- Every CSS check in this part (rows 240-242, the zoom stylesheet
  contract, the mobile button override's source order, and the lightbox's
  max-width) fetches the stylesheet `companion/app.py` actually serves and
  asserts on it structurally via `companion_markup.css_rules()`/
  `declarations_for()`/`rules_with_selector()` (33-FOLLOWUPS.md F-01).

New modules: `companion/test_status_pages_05.py` (37 baseline rows,
checks #172-#208, 190 pytest node ids — the three 52-illustration checks
each parametrized per vendored file so xdist spreads them) and
`companion/test_status_pages_05b.py` (36 baseline rows, checks #209-#244,
36 pytest node ids — no splitting needed in this half).

`companion/test_status_pages.py` (the legacy harness) shrinks from
`EXPECTED_CHECK_COUNT = 146` to `EXPECTED_CHECK_COUNT = 73` (146 - 73);
part 05's 73 checks and the closures only they used are removed from
`main()`.

### Part 06 (plan 33-30)

Rows 245-292 (part 06, original `check()` calls #245-#292, 48 checks) are
flipped: 46 `ported` to `companion/test_status_pages_06.py`, 2 `deleted`.

Rubric codes: 40 B/D (calls `companion.pages.airlines_page`/`companion.
pages.health_page`/`companion.layout` directly, or renders a real page and
asserts on the returned/rendered HTML — the legacy harness's own substring/
regex style over rendered markup, per 33-25's precedent, since TST-12 only
bans reading production SOURCE files, not asserting on a page's own
rendered HTTP/in-process output), 6 C (rows 249, 251, 254, 277, 286-290's
seven style.css checks collapse to six ported rows since two share one
check each: `.frame-strip__cells`/`.frame-strip__cell button`/`.stat-tile:
not(.frame-strip):hover`/`.frame-strip__cell--update .status-card__
headline`/`.time-value`/`.tab-bar`, all rewritten against a served
stylesheet via `companion_markup.css_rules()`/`declarations_for()`/
`rules_with_selector()`, iterating parsed `Rule.selectors`/`Rule.
declarations` rather than a regex/substring probe over the raw served
text), 1 J (row 276, `list-filter.js`'s raw disk read, rewritten as a
`served_asset()` fetch through `strip_js_line_and_block_comments()`), 1 S
(row 271, the retired D-06 supersession machinery's own symbols, rewritten
as `not hasattr(airlines_page, name)`). 2 deletions: row 285 (S — a
`companion/layout.py` source grep for a retired `age_seconds(next_wake...)`
re-derivation, redundant with the frame-strip behaviour checks this same
part already carries), row 291 (C — a served-stylesheet header COMMENT
assertion, no rendered behaviour per guard G1).

Two more rows keep their ported status but drop one now-redundant
source-text sub-clause each, noted in the new module's own docstring and
at each test's own docstring (not counted as separate deletions — the
check's remaining assertions are still `ported`): row 250 (a `companion/
pages/airlines_page.py` source scan for a hand-written glyph token,
redundant with the rendered `<use>` count/class assertions kept) and row
257 (a source scan for the `'data-filter-group="gap%d"'` format-string
literal, redundant with the rendered-attribute regex match kept).

New module: `companion/test_status_pages_06.py` (46 pytest node ids, one
per ported row — no row in this slice needed parametrization or a
one-to-many split). A `_module_server`/`css_text` module-scoped read-only
server fixture pair is new in this module, for the 6 C-rubric checks and
the 1 J-rubric check above — no test in this module mutates that server's
state, so every CSS/JS-reading test shares it safely under xdist.

`companion/test_status_pages.py` shrunk further: `EXPECTED_CHECK_COUNT`
dropped from 73 to 25; part 06's 48 checks removed from `main()`. Four
closures/constants (`_frame_strip_ctx`, `_css_source`, `_block`,
`_TAB_BAR_BANNER`) that used to sit beside their own first use inside part
06's checks are relocated (not deleted), right after the check() closure
definition, because later, not-yet-migrated checks (part 07) still call
them.

### Part 07 (plan 33-31) — chain closed

Rows 293-317 (part 07, original `check()` calls #293-#317, the LAST 25
checks in the file) are flipped: all 25 `ported` to `companion/
test_status_pages_07.py`, 0 `deleted`.

Rubric codes: 12 B/D (renders a real page — `layout.page_shell()`/
`layout.frame_strip_html()`/`health_page.render()`/`health_page.
compute_health_state()`/`home_page.render()`/`config_page.render()` — and
asserts on the returned/rendered HTML, per 33-25's precedent), 9 C (rows
293, 294, 297, 298, 299, 301, 302, 304, 309's nine style.css checks,
rewritten against a served stylesheet via `companion_markup.css_rules()`/
`declarations_for()`/`rules_with_selector()`, iterating parsed `Rule.
selectors`/`Rule.declarations` rather than a regex/substring probe over
the raw served text), 2 J (rows 300 and 315, `freshness.js`'s two raw
disk reads, rewritten as `served_asset()` fetches through this chain's
`strip_js_line_and_block_comments()`), 2 B/end-to-end (rows 316-317, a
real `companion/app.py` subprocess via `make_app_server`, logged in
through `companion_app_server.login()`). 0 deletions — every one of the
final 25 checks maps onto observable behaviour with no source-text read
needed.

Two rows keep their `ported` status but replace a legacy sub-clause that
had no structural equivalent, noted in the new module's own docstring and
at each test's own docstring (not counted as separate deletions, per the
same precedent 33-30 set for rows 250/257):
- Row 299 drops the legacy check's own
  `css_source.count("@media (prefers-reduced-motion: reduce)") != 2`
  literal count (`css_rules()` records each rule's ENCLOSING at-rule
  context, not a raw count of top-level at-rule block occurrences in the
  source — there is no structural equivalent for "exactly N block
  occurrences"). The replacement asserts the two SPECIFIC things that
  count actually protected: the one global `*, *::before, *::after`
  override exists under that media query, the one `.js .mobile-nav`
  opt-out exists under it too, and `summary::before` (this task's own
  subject) carries no THIRD, redundant per-rule override under the same
  at-rule.
- Row 309 drops the legacy check's own `css_source.count("dot--") != 9`
  literal count. Of the raw served text's 9 substring occurrences, 5 are
  prose inside COMMENTS (guard G1 already rules out comment text as a
  source of behaviour) and only 4 are real selectors. The replacement
  asserts the actual invariant the comment-polluted count stood in for:
  exactly four `.dot--*` modifier classes exist (ok/warn/error/off) and
  no fifth has been added — a stronger, comment-immune version of the
  same acceptance criterion.

Row 298 (the stray-comment-terminator structural guard) is `ported`
scanning the SERVED stylesheet's raw character stream rather than
`css_rules()`'s parsed structure: the defect it guards against (an
unterminated `/* */` comment silently swallowing the next rule) is
exactly the shape a real CSS parser cannot see through either, so no
`css_rules()`-based rewrite is possible without losing the property under
test. It still never reads the file from disk — only the bytes
`companion/app.py`'s STYLE_ROUTE actually serves, fetched over HTTP.

Rows 316-317 (the file's final two checks, a real running-service
end-to-end round trip) move from the legacy harness's own local `Harness`/
`http_request`/`_NoRedirectHandler` to `companion/conftest.py`'s
`make_app_server` fixture and `test-support/companion_app_server.py`'s
`login()`/`get()`. Row 316's STYLE_ROUTE assertions (previously a
substring probe over the raw served CSS text) are rewritten structurally
against `companion_markup.rules_with_selector()`/`declarations_for()`
over that SAME real subprocess's own served bytes (33-FOLLOWUPS.md F-01);
its FRESHNESS_SCRIPT_ROUTE assertions stay a comment-stripped served-text
scan (JS delivery contracts are the named exception in this chain's own
convention), fetched fresh from the running service and passed through
`strip_js_line_and_block_comments()` rather than left raw.

New module: `companion/test_status_pages_07.py` (25 pytest node ids, one
per ported row — no row in this slice needed parametrization or a
one-to-many split). Reuses this chain's `_module_server`/`css_text`
module-scoped read-only server fixture pair (33-26) for the 9 C-rubric
checks, adds a `freshness_js` module-scoped fixture for the 2 J-rubric
checks, and uses `companion/conftest.py`'s function-scoped
`make_app_server` fixture (never the module-scoped one) for the two
end-to-end checks, since they seed real per-test fixture state and log in.

**Chain closed.** `companion/test_status_pages.py` — the LAST legacy
companion harness — is deleted outright (`git rm`), after confirming no
importer remains anywhere in the repo (grepped imports, `open(`/`ast`/
`Path(`/string mentions across companion, test-support, conftest, the
shim, and every other test module — only prose comments and the frozen
`ORIGINAL_COMPANION_HARNESSES` history tuple in `test-support/
skypane_test_support.py` survive, used only to bound a guard's own
exemption set, never opened). All 317 of this harness's baseline checks
are now accounted for (313 ported, 4 deleted — rows 285/291 from part 06
plus 2 earlier deletions from prior parts — 0 pending).
`33-ledger-check.py companion/test_status_pages.py` **WITHOUT**
`--allow-pending` confirms **317/317 baseline checks mapped, 0 pending**.

`skypane_test_support.legacy_companion_harnesses()` now returns `()` —
the disk-derived legacy set is EMPTY, since every companion harness chain
(33-04, 33-08, 33-13, 33-18, 33-20, 33-24, and now this one) has finished.
`companion/test_legacy_harness_shim.py`'s own parametrize list collapses
to an empty set, which pytest reports as a clean SKIP
("got empty parameter set for (harness)"), never an error or a failure —
confirmed by running the shim module directly.
