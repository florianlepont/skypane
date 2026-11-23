---
phase: 68-console-and-companion-visual-improvements
plan: 45
subsystem: companion Fleet page, Battery view, System view
tags: [battery, fleet-tiles, system-cards, redirects, dead-code]
requires: [68-31]
requirements: [CON-01]
---

# Phase 68 Plan 45: Battery page instead of Health Summary

The per-frame Health view is replaced by a Battery view (administrators only, reached from the Fleet battery tile); the connection detail moves into the Connection tile; the platform rows leave Health and the route cards of plan 31 join the System view.

## What was built

- **Connection tile** (`fleet_tiles.py`, `health_page._connection_tile`): verdict plus two lines, "Last check-in <live age>" and "Next wake <clock>" (existing `_age_html` and `next_wake_clock`). The tile is a plain block, not a link, no Details mark. Tiles stay equal height, 44 px or more, nothing overflows at 360/390/1440, EN/FR (new browser test).
- **Battery view**: `/fleet?frame=<id>&view=battery`, the battery row only (`health_page.battery_view`, `console_fleet_view.battery_html`). Title "Battery" / "Batterie". It sits under the admin-only `/fleet` route, so a plain user gets the same refusal as for `/fleet` (tested). The user's own Home battery row is untouched.
- **Fleet tiles**: Battery tile links to the Battery view; Flight data tile links to `/fleet?view=system#system-topic-flight-data` (see decisions).
- **System view**: the two plan 31 topics ("Route directories", "Answered by") now render as system cards (`route_sources_card.py` rewritten on `system_cards._card`), after Identification and before the backup. States, counters and schema unchanged. The two directories are two cards in one topic (role in the small line, name in bold, Reachable / Not reachable / No request yet at the right), as in the route-sources mock.
- **Redirects (303)**: `/health`, `/devices/<id>/health` -> the frame's Battery view (System view with no frame); new: `/fleet?view=health[&frame=<own id>][&flash=..]` -> Battery view of that frame if it is one of the caller's, else `/fleet?view=system` (`fleet_moves.retired_health_view`, called from `handle_fleet_get`). Owners and users keep the existing routing of the legacy paths.
- **Nav dot / severity targets**: the dot already sits on the Fleet link (`/fleet`), which exists; the live-refresh swap selectors (`.health-row__summary`, `.sys-card__head`, `div.health-anomaly`, `a[href$="/fleet"]`) all still match. Nothing to retarget.

## Platform content check (Health "Server and data" vs System)

Everything the platform section showed is on the System view: flight data (last run, last detection), data sources, identification (rate, window, breakdown), off-box backup, source-fault notice, warnings banner. Plan 31's route rows were Health-only and moved. Nothing missing. Not carried over: the "Last check-in" fact now lives in the tile; the one-line help sentence "This is when the frame last contacted the server" is gone.

## Removed

- Code: `_connection_row`, `_flight_data_row`, `_sources_row`, `_identification_row`, `_backup_row`, `_server_group_html`, `_server_topics`, `_device_unreachable_html`, `_anomaly_banner_html`, `_anomaly_category_text`, `_starts_with_acronym`, `_corroboration_outcomes_html`, `health_sections()`/`HealthSections`, `_fact`, `_concise`, Screen/Server and data heading constants, `ROW_CONNECTION_NAME`, `SOURCE_FAULT_BODY`, the unreachable and connection-help texts; `health_rows.group_html/facts_html/note_html`; `health_sections._stats_table_html/_stats_cards_html` and the resolution detail templates.
- CSS: `.health-rows__group` (3 rules), `.health-row__facts/note/outcomes/outcome` (+ container rule), `.toast__pills`, `.toast__pill`.
- i18n (FR entries removed with their messages): `admin_fleet.health_admin_only`, `admin_fleet.health_frame_section`, `health.device_connection_help`, `health.device_unreachable`, `health.row_connection`, `health.row_identified`, `health.server_data`, `health.over_the_last_days_events`, `health.over_the_last_days_event`. Reworded (EN and FR) `health.device_empty_body` for the Battery page.
- Kept on purpose: `layout.data_table(prose=, desc_columns=)` and their CSS (generic component, now unused by any page); the per-source gloss strings in `resolution_stats` rows (still part of its return value); `_gap_overflow_html` in `airlines_page.py` links to `/health` and is unused outside its own test (pre-existing, not touched).

## Tests

Deleted because the behaviour was removed on purpose (Health connection/flight/sources/identification/backup rows, Health banner and unreachable toast, group bands, stats cards list):
- `test_status_pages_01`: render_shows_two_distinct_freshness_labels, independent_thresholds_one_warn_one_ok, connection_and_flight_data_rows_have_no_duplicated_label, anomaly_banner_names_real_categories_not_generic_only, anomaly_categories_never_lowercase_a_leading_acronym, anomaly_banner_html_matches_layout_anomaly_banner_severity_mapping, anomaly_banner_renders_one_pill_per_anomaly_on_the_page, sources_row_keeps_the_verdict_in_the_summary..., device_and_pipeline_rows_use_concise_timestamp_format, anomaly_detail_list_markup_is_gone, none_of_the_four_anomaly_item_strings_render.
- `test_status_pages_03`: health_page_opens_with_shared_page_header, health_page_header_carries_no_purpose_sentence_or_freshness_line, health_page_two_id_anchored_groups_correct_order_no_overview, server_rows_form_one_card_with_no_registry_card_below, identification_row_renders_percentage_and_window.
- `test_status_pages_02`: resolution_detail_templates_have_french_catalogue_entries. `test_status_pages_04`: stats_cards_list_is_complete_and_precedes_the_table.
- `test_fleet_tiles`: health_page_does_not_link_to_the_unresolved_airlines (System equivalent exists in `test_system_tiles`); `test_device_pages`: online/silent device unreachable toast tests (replaced, see below).
- `test_browser_ux_health_drawings`: every_health_row_aligns_in_the_fleet_state_block (only one row remains).

Ported to the new surface (same intent): row verdict tests -> Connection tile / flight data tile and card / sources card / identification card; never-ran, French never-ran, last-detection, singular window, 36 rows, failure isolation, manual/other rows, backup card (`test_health_offbox`), user principal (`test_user_health`), freshness and Battery page tests; `test_health_route_sources` -> `test_system_route_sources`, `test_browser_health_route_sources` -> `test_browser_system_route_sources`, `test_health_connection_row` -> `test_fleet_connection_tile`. Counts updated in system tile browser tests (6 topic labels, 7 card chips), fleet anchors (3 Details links), console fleet view (5 System blocks). New: legacy `view=health` redirect and plain-user refusal tests, connection tile browser fit test, silent device tile test.

Run (all with `SKYPANE_REQUIRE_BROWSER=1`):
- `pytest companion test-support -k "not browser"`: 7615 passed, 1 failed before the last deletion (the test deleted above), then green; plus `test_render_baseline`, `test_stylesheet_structure`, `test_suite_guards`, `test_structure_guards`, `test_i18n` green.
- 23 browser files (Fleet, System, Battery, Home state/battery, console, surfaces, ux, charging pill, nav spaces, update, overhaul, motion live, walkthrough, title phone, personal scope): 1337 passed, 25 failed on first run (counts of tiles/cards/rows); fixed, re-run of the 5 affected files 119 passed.
- `ruff check .`, `mypy` (49 files), `check_function_size.py check --max 80 server stub-server`, `check_comment_history.py check`: clean. `companion/app.py` 1497 lines; `health_page.py` 1268 -> 988.
- Full core group (`SKYPANE_TEST_GROUP=core ./scripts/run-all-tests.sh`, after both commits): 12550 passed, 7 skipped (root permission skips), exit 0.

## Deploy-time effects

- `/health`, `/devices/<id>/health` and `/fleet?...&view=health` bookmarks keep working through 303. `view=health` is new in this series; the redirect is for any saved link.
- No schema, route-table or access-matrix change. No new strings beyond the reworded empty-state body. Fleet pages with an open tab auto-refresh as before.

## Divergences from the mocks and decisions needed

- Battery view has no "Frame" section label above the card (h1, label and row name would all read "Battery"); the mock kept the label.
- Flight data tile now links to the System flight data card (platform data). Alternative: make it a plain block like Connection.
- No new System tiles for the two route topics (cards only); the tile row keeps its four tiles.
- The Battery view shows no warnings banner or no-signal toast any more (connection state is in the tile, platform banner in System). Say if a battery-only banner is wanted.

## Known Stubs

None.

## Self-Check: PASSED

## Addendum: System tiles for the route topics

Owner decision: the two route topics ("Route directories", "Answered by") also have tiles in the System tile row (six tiles, each linking to its card; `route_sources_card.tiles`). Tile tests updated, baseline regenerated, captures in `scratchpad/p45/after2/`.

## Addendum: no Flight data tile on the frame

Owner decision: flight data is platform data, so the frame State tiles are Connection, Battery, Firmware (the Flight data tile, its System link and `FrameTiles.flight` are removed). The System view keeps its own Flight data tile and card. No warning banner on the Battery view. Tests adapted (three tiles, two Details links), baseline regenerated, captures in `scratchpad/p45/after3/`.
