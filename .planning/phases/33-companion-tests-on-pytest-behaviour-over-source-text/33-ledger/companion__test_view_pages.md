# Ledger: companion/test_view_pages.py

Baseline: `companion__test_view_pages.txt`, 169 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | an empty database renders the flight-history empty-state copy and no <table | ported | companion/test_view_pages_01.py::test_empty_database_renders_empty_state_no_table |
| 2 | three seeded runway events render one row each, newest first | ported | companion/test_view_pages_01.py::test_three_events_render_newest_first |
| 3 | a known aircraft-type designator renders its friendly label (case-insensitive) | ported | companion/test_view_pages_01.py::test_known_aircraft_type_friendly_label |
| 4 | an aircraft type absent from the display-label table renders the raw designator, not an empty cell | ported | companion/test_view_pages_01.py::test_unknown_aircraft_type_raw_designator |
| 5 | a row with no airline and no route renders the same fallback wording server.plane.render.py uses (read from the module) | ported | companion/test_view_pages_01.py::test_no_airline_no_route_matches_render_fallback |
| 6 | timestamp, callsign and hex columns carry monospace CSS classes | ported | companion/test_view_pages_01.py::test_mono_columns_present |
| 7 | a callsign containing angle brackets renders escaped | ported | companion/test_view_pages_01.py::test_hostile_callsign_escaped |
| 8 | a state directory that cannot hold a database renders the health-unavailable copy without raising | ported | companion/test_view_pages_01.py::test_unreadable_db_degrades_without_raising |
| 9 | companion/pages/history_page.py never imports the stdlib html module directly | ported | companion/test_view_pages_01.py::test_history_page_never_imports_html_module_directly |
| 10 | companion/pages/history_page.py never redefines _TYPE_DISPLAY_LABELS locally | ported | companion/test_view_pages_01.py::test_history_page_never_redefines_type_display_labels_locally |
| 11 | History opens with the shared layout.page_header() component, not a bare <h1> | ported | companion/test_view_pages_01.py::test_history_opens_with_shared_page_header |
| 12 | History's flight table gains the .data-table-wrap horizontal-scroll wrapper Airlines/Health already have, without disturbing the Corroboration status dot | ported | companion/test_view_pages_01.py::test_history_table_wrapped_for_horizontal_scroll_dot_survives |
| 13 | History renders exactly the 5 data headers in history_page._HEADERS plus a sixth, visually-hidden 'Details' toggle-column header, all in order, with no standalone Hex/Airline/Runway/Type/Callsign/Timestamp column (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_six_columns_named_and_ordered |
| 14 | the runway value the dropped desktop Runway column used to show survives in the <tr title="..."> attribute and, unchanged, in the mobile card's More details (A-36/D-19) | ported | companion/test_view_pages_01.py::test_runway_survives_in_row_title_and_mobile_details |
| 15 | the .data-table-wrap scroller is focusable (tabindex="0") and carries a non-empty aria-label naming what it scrolls (A-36/D-19) | ported | companion/test_view_pages_01.py::test_scroller_focusable_and_named |
| 16 | the desktop When cell shows a local clock primary line plus a STACKED relative-age secondary line, with no title attribute carrying the full ISO string any more (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_desktop_when_cell_clock_primary_relative_age_secondary |
| 17 | the Flight cell's callsign and its airline/aircraft-type secondary line both appear inside the same <td>, and the hex value is not visible in the desktop table (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_merged_flight_cell_carries_callsign_airline_and_type |
| 18 | the merged Callsign/Hex and Type/Airline cells stay on one line - no <br>, no block-level child | ported | companion/test_view_pages_01.py::test_merged_cells_stay_one_line |
| 19 | hostile values in both merged cells (Callsign/Hex, Type/Airline) render escaped | ported | companion/test_view_pages_01.py::test_merged_cell_hostile_values_escaped |
| 20 | history_page's CELL_PRIMARY_CLASS/CELL_SECONDARY_CLASS/CELL_SEPARATOR_CLASS all appear in style.css and in the rendered page | ported | companion/test_view_pages_01.py::test_merged_cell_classes_agree_with_stylesheet |
| 21 | History's Timestamp column/mobile primary line read through layout.concise_timestamp_html(), format_event_row() degrades gracefully with one argument or a missing timestamp, and render() falls back when ctx carries no 'now' key | ported | companion/test_view_pages_01.py::test_timestamp_column_absolute_and_relative |
| 22 | History's Timestamp cells carry layout.concise_timestamp_html()'s new <time data-relative> element through data_table()'s raw_columns — as real markup, never double-escaped — with its text and its instant both intact (23-03, D14/CFG-34) | ported | companion/test_view_pages_01.py::test_history_timestamps_carry_a_relative_time_element |
| 23 | history_page._CORROBORATION_LABELS agrees with health_page._CORROBORATION_ROWS on status key-by-key and on visible label for True/False; History's shortened 'None' label is the documented short form and its _CORROBORATION_TITLES tooltip equals Health's own full label exactly; the single-source 'None' state is pinned by name on each side (History 'ok', Health the neutral 'off'), is never a failure in either table, and carries a visible label distinct from 'Both agree' (quick task 260902-w4t UIR-04, retargeted by 22-12-PLAN.md Task 1's X8) | ported | companion/test_view_pages_01.py::test_corroboration_copy_agrees_with_health_page |
| 24 | layout.status_dot()'s 2-arg output is unchanged, an explicit title=None is byte-identical to omitting it, and a truthy title renders as an escaped title attribute (quick task 260902-w4t, UIR-04) | ported | companion/test_view_pages_01.py::test_status_dot_title_backward_compatible_and_escaped |
| 25 | layout.status_dot()'s visually_hide_label keyword defaults to False with a byte-identical return value, and True adds the visually-hidden class to the label span while leaving its text/title unchanged (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_status_dot_visually_hide_label_defaults_false_byte_identical |
| 26 | a 'None' (single-source) row's Corroboration cell shows the short visible label with the long form only in a title attribute, in both the desktop and mobile renderings (quick task 260902-w4t, UIR-04) | ported | companion/test_view_pages_01.py::test_corroboration_none_row_shows_short_label_with_tooltip |
| 27 | the desktop Corroboration cell renders the dot only, with the visible word hidden via visually-hidden (not deleted); the mobile card's own Corroboration <dd> still shows the word (21-03-PLAN.md Task 1, D-15/D-16) | ported | companion/test_view_pages_01.py::test_desktop_corroboration_cell_dot_only_no_visible_word |
| 28 | the desktop When and Flight cells each carry exactly one cell-primary span and one cell-secondary span (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_when_and_flight_cells_each_carry_one_primary_one_secondary |
| 29 | .data-table-wrap declares both background-attachment values (local covers, scroll shadows) and style.css introduces no pointer-events-blocking overlay (quick task 260902-w4t, UIR-04) | ported | companion/test_view_pages_01.py::test_data_table_wrap_scroll_edge_affordance_css |
| 30 | History's filter bar carries exactly one data-filter-input/-count/-clear/-empty marker each | ported | companion/test_view_pages_01.py::test_filter_bar_markers_present_once |
| 31 | History's search filter input carries autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression) | ported | companion/test_view_pages_01.py::test_filter_input_carries_safari_autofill_suppression_attributes |
| 32 | History's filter bar carries data-filter-count-template="%d of %d shown" under the default language and the French "%d sur %d affichés" under lang='fr' (D-06) | ported | companion/test_view_pages_01.py::test_filter_count_template_attribute_english_and_french |
| 33 | History's filter count and Clear control render as siblings inside one .filter-bar__meta group whose page-agnostic rule declares flex/centre/nowrap/auto-left-margin, with no page-scoped fork of the converged [data-filter-clear] rule anywhere (B11, 22-09-PLAN.md Task 3 — a regression of Phase 18's A-18) | ported | companion/test_view_pages_01.py::test_filter_bar_count_and_clear_wrap_as_one_group |
| 34 | the Clear control's shared [data-filter-clear] contract holds: History renders the attribute, style.css styles it by attribute, and no class-keyed rule competes | ported | companion/test_view_pages_01.py::test_clear_control_shared_attribute_contract |
| 35 | a real flight's data-filter-text attribute (lowercased escaped callsign+hex) appears on both the desktop <tr> and the mobile <li> | ported | companion/test_view_pages_01.py::test_filter_text_attribute_on_both_representations |
| 36 | the desktop Flight cell contains zero copy buttons (21-03-PLAN.md Task 1, D-15 - they move into the Task 2 detail row instead) | ported | companion/test_view_pages_01.py::test_desktop_flight_cell_carries_no_copy_buttons |
| 37 | each summary row gets exactly one sibling detail row, matched by aria-controls/id, with no hidden attribute and no inline style (the no-JS floor), and every row-toggle starts aria-expanded="false" (21-03-PLAN.md Task 2, D-15/R-12) | ported | companion/test_view_pages_01.py::test_detail_row_pairs_with_summary_row_by_aria_controls_and_id |
| 38 | the rendered Flights table carries zero visible More/Plus/Less/Moins button labels and exactly one icon-only toggle button per row, each carrying a translated aria-label that swaps with its state and names the picture reachable inside (22-09-PLAN.md Task 1, X5) | ported | companion/test_view_pages_02.py::test_row_toggle_is_icon_only_and_named_in_both_languages |
| 39 | in the RENDERED Flights page no <tr> carries aria-expanded and every aria-expanded occurrence sits on a <button> (22-09-PLAN.md Task 1, X5 — the state never moves onto the row element) | ported | companion/test_view_pages_02.py::test_aria_expanded_sits_only_on_buttons_never_on_a_tr |
| 40 | style.css's new .row-toggle rule block reuses .copy-btn's icon-only pattern verbatim (same 22x22 box, same radius, the same ::before inset synthesizing 44x44, the same 14px glyph) and introduces no new size literal; the pointer cursor is keyed only on the class flight-rows.js adds at load (22-09-PLAN.md Task 1, X5) | ported | companion/test_view_pages_02.py::test_row_toggle_css_reuses_the_copy_btn_icon_only_pattern |
| 41 | companion/static/flight-rows.js reads every attribute name history_page.py renders, swaps aria-label instead of a visible label, returns early for an interactive click target (T-22-32) and uses no markup-writing sink; the server still renders every detail row visible with no collapsing class, no hidden and no inline style (22-09-PLAN.md Task 1, X5/D-09) | ported | companion/test_view_pages_02.py::test_flight_rows_js_swaps_the_name_and_delegates_the_row_click |
| 42 | the hex, the raw ISO timestamp and the runway render inside the detail row and NOT in the summary row's own slice (21-03-PLAN.md Task 2, D-15) | ported | companion/test_view_pages_02.py::test_detail_row_carries_hex_iso_runway_not_in_summary_row |
| 43 | a rendered Flights page contains no inline <script> and no on*= handler attribute (21-03-PLAN.md Task 2, D-15/R-12) | ported | companion/test_view_pages_02.py::test_flights_render_has_no_inline_script_or_handler_attribute |
| 44 | style.css's table.data-table--flights padding rule uses var(--space-sm) on both axes, never a literal px value (21-03-PLAN.md Task 3, D-15) | ported | companion/test_view_pages_02.py::test_flights_table_padding_rule_uses_space_sm_token_both_axes |
| 45 | the rendered Flights table's <thead> carries exactly six <th> cells in both en and fr (21-03-PLAN.md Task 3, D-15) | ported | companion/test_view_pages_02.py::test_flights_thead_carries_exactly_six_cells_in_both_languages |
| 46 | the mobile card's details region contains exactly 3 copy buttons (callsign, hex, full timestamp), each immediately followed by its data-copy-feedback sibling | ported | companion/test_view_pages_02.py::test_mobile_details_three_copy_buttons |
| 47 | a Flights render's copy buttons carry data-copied-text="Copied" under the default language and data-copied-text="Copié" under lang='fr' (D-06) | ported | companion/test_view_pages_02.py::test_copy_button_carries_data_copied_text_english_and_french |
| 48 | the desktop copy-button reveal rule lives inside the shared 960px block, is scoped by [data-copy-value] (never the bare .copy-btn class), reveals via opacity + pointer-events (never visibility: hidden or display: none) on both tr:hover and tr:focus-within (quick task 260903-peo, UIR-17) | ported | companion/test_view_pages_02.py::test_desktop_copy_reveal_stylesheet_contract |
| 49 | a real rendered desktop History summary row carries zero copy buttons (21-03-PLAN.md Task 1, D-15) and no picture control at all (22-09-PLAN.md Task 2, X5 — it moved into the detail row), and that control still never carries data-copy-value — the discriminator the desktop reveal rule depends on (quick task 260903-peo, UIR-17) | ported | companion/test_view_pages_02.py::test_desktop_row_copy_buttons_and_eye_button_discriminator |
| 50 | with two differently-named rows, at least two distinct copy-button aria-label values render on the page — the '50 identical names' defect closed (A-37/D-20) | ported | companion/test_view_pages_02.py::test_copy_buttons_no_longer_share_one_aria_label |
| 51 | each row's mobile-card callsign copy button carries an aria-label naming that row's own callsign, not a shared/generic name (A-37/D-20, retargeted off the desktop row by 21-03-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_each_copy_button_aria_label_names_its_own_row |
| 52 | copy-button.js propagates fallbackCopy()'s real document.execCommand(...) result instead of discarding it, and stays ES5-safe/sink-free (A-37/D-20) | ported | companion/test_view_pages_02.py::test_copy_button_script_propagates_execcommand_success |
| 53 | every rendered copy button carries exactly one copy-btn__icon span and one empty copy-btn__label span, and its data-copy-feedback sibling still immediately follows the button (D-20) | ported | companion/test_view_pages_02.py::test_copy_button_markup_carries_icon_and_label_spans |
| 54 | copy-button.js references the copy-btn__label/copy-btn--copied class names and the 1.5s (1500ms) feedback window (D-20) | ported | companion/test_view_pages_02.py::test_copy_button_script_references_label_class_and_1500ms |
| 55 | style.css styles both copy-btn__label and copy-btn--copied (D-20) | ported | companion/test_view_pages_02.py::test_style_css_styles_both_copy_feedback_classes |
| 56 | confirmed_state/tracked_runway presentation labels (Task 1's format_event_row() fixture) also appear correctly through the full render() output | ported | companion/test_view_pages_02.py::test_presentation_labels_in_full_render |
| 57 | a French Flights render translates the tracked_runway cell's registry label ('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), with no English label leaking in (Polish fix 5, D-05) | ported | companion/test_view_pages_02.py::test_french_render_translates_the_runway_cell_label |
| 58 | with 3 gallery entries and one seeded flight row, the rendered page carries zero <h2, zero page-section, zero gallery-grid/gallery-tile elements and zero occurrences of the retired heading/empty-state text, WHILE the per-row View-panel mechanism (a trigger, exactly one lightbox dialog) and History's own card disclosures survive in the same render | ported | companion/test_view_pages_02.py::test_history_render_gallery_section_absent_with_content |
| 59 | with gallery_entries=[], the same absences hold (the section is gone, not merely emptied) and, as before, zero View-panel triggers and zero lightbox dialogs render | ported | companion/test_view_pages_02.py::test_history_render_gallery_section_absent_when_empty |
| 60 | the rendered picture control is a LABELLED text control carrying the translated "View picture" text and no aria-label, with "View panel near this time" surviving as its title, on both the desktop detail row and the mobile card (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_02.py::test_view_panel_trigger_is_a_labelled_control_with_the_long_form_as_title |
| 61 | the colour caveat sentence appears exactly once in the rendered page, and that single occurrence lies inside the lightbox__note element (the caveat's new, and only, home after the render-gallery section's removal) | ported | companion/test_view_pages_02.py::test_colour_caveat_rehomed_into_lightbox_note |
| 62 | with a real panel.bin on disk and gallery entries seeded, the rendered output contains zero occurrences of /preview.png, preview-frame, preview-image, and the old no-panel caption sentence - a present panel file changes nothing about the markup any more (this check's real subject is quick task 260903-c4o's /preview.png route retirement, not the render-gallery section retired by this task; kept in place rather than dropped) | ported | companion/test_view_pages_02.py::test_render_gallery_no_preview_apparatus_even_with_panel_file |
| 63 | the rendered History page carries no data-stale-banner and no Refresh link — D-18's retired apparatus stays retired — while carrying exactly one data-loaded-at marker, built by layout.freshness_line_html(), because D7/CFG-37 puts this page on the refresh loop and freshness.js returns at its first guard without one (retargeted in place by 23-08-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_now_showing_no_preview_freshness_apparatus |
| 64 | history_page._gallery_name_to_iso() reverses a well-formed gallery filename and returns None (never raising) on a missing 'T' separator or a malformed time+offset portion | ported | companion/test_view_pages_02.py::test_gallery_name_to_iso_fixtures |
| 65 | a rendered History page's picture control carries no icon glyph at all and reuses .calendar-disconnect-btn's small-grey-secondary treatment — that component's second consumer, with no .btn family started (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_02.py::test_view_panel_trigger_reuses_the_small_grey_secondary_treatment |
| 66 | nearest_gallery_entry() matches the latest at-or-before entry (inclusive boundary), skips an entry with an unrecoverable filename timestamp, and returns None for an empty entry list, an empty/unparseable row_ts, or when every recoverable entry is strictly after row_ts | ported | companion/test_view_pages_02.py::test_nearest_gallery_entry_behaviour |
| 67 | for three gallery entries and three interleaved rows, each row's desktop and mobile View-panel trigger carries byte-identical, correctly-targeted data-view-panel-src/-caption attributes matching its own nearest gallery entry, and exactly one lightbox dialog is emitted | ported | companion/test_view_pages_02.py::test_view_panel_triggers_per_row_full_render |
| 68 | with an empty gallery entry list, History renders zero View-panel triggers and zero lightbox dialog elements, never a disabled or broken control | ported | companion/test_view_pages_02.py::test_view_panel_empty_gallery_zero_triggers_zero_dialog |
| 69 | the shared, Airlines-only and render-only lightbox token tuples each appear (or, for Airlines-only, are absent from History) exactly where their own classification says they must, across companion/static/panel-lookup.js and both pages' rendered markup | ported | companion/test_view_pages_02.py::test_lightbox_dom_contract_three_file_guard |
| 70 | every airlines_page._VIEW_PANEL_*_ATTR constant's value is classified in exactly one of the three lightbox token tuples, discovered by reflection over dir(airlines_page) rather than a hand-copied name list | ported | companion/test_view_pages_02.py::test_view_panel_attr_constants_all_classified |
| 71 | panel-lookup.js never sets image.src to the empty string anywhere in its comment-stripped source - D-02/RESEARCH.md Pitfall 1's single riskiest line, the exact cross-browser spurious-request bug this phase's imageless-open branch exists to avoid | ported | companion/test_view_pages_02.py::test_panel_lookup_never_sets_image_src_to_empty_string |
| 72 | panel-lookup.js's image.removeAttribute("src") call is nested inside a conditional branch (the src-absent case), never written unconditionally at module scope | ported | companion/test_view_pages_02.py::test_panel_lookup_remove_attribute_src_is_conditional |
| 73 | panel-lookup.js's shared populate-and-open function (openFromTrigger) is defined exactly once and referenced from at least two call sites - the click listener and the load-time auto-open (RESEARCH.md Pitfall 2's mandatory factoring) | ported | companion/test_view_pages_02.py::test_panel_lookup_shared_populate_function_two_call_sites |
| 74 | panel-lookup.js reads location.search exactly once in its own code, at script init, outside openFromTrigger (the one function reachable from a click) and after the click listener is already wired | ported | companion/test_view_pages_02.py::test_panel_lookup_location_search_read_once_outside_click_only_function |
| 75 | every one of the eleven new data-view-panel-* attribute name literals 14-02 added to the vocabulary appears at least once in panel-lookup.js's own source | ported | companion/test_view_pages_02.py::test_panel_lookup_eleven_new_attrs_present_in_source |
| 76 | the mode-governed elements' (resolveNameForm/resolveUploadZone/replaceForm) hidden assignments all occur, textually, before openFromTrigger's own dialog.showModal() call (RESEARCH.md Pitfall 3 - showModal()'s one-time autofocus placement must see the final, already-toggled subtree) | ported | companion/test_view_pages_02.py::test_panel_lookup_mode_hidden_toggles_before_showmodal |
| 77 | panel-lookup.js's evt.preventDefault() appears exactly once, inside the click listener, positioned after the trigger-null-check and before the showModal()-reaching openFromTrigger() call (D-12's <a> interception) | ported | companion/test_view_pages_02.py::test_panel_lookup_prevent_default_once_correctly_positioned |
| 78 | panel-lookup.js still contains exactly one document.getElementById("panel-lookup-dialog") and exactly one document.addEventListener("click", ...) - this plan extended the existing single mechanism rather than adding a second one (D-03's own rejected alternative) | ported | companion/test_view_pages_02.py::test_panel_lookup_single_dialog_lookup_single_click_listener |
| 79 | panel-lookup.js's contextCallsign.textContent is assigned exactly once, gated on the same `count` that gates resolveContext.hidden, so an ordinary illustration's own caption can never be printed under the 'Example callsign' label (quick task 260921-n2n Task 2) | ported | companion/test_view_pages_02.py::test_panel_lookup_context_callsign_write_gated_on_count |
| 80 | airlines_page's LIGHTBOX_DIALOG_ID and its three _VIEW_PANEL_*_ATTR constants each equal history_page's own values (the duplicated-not-imported shared-lightbox contract) | ported | companion/test_view_pages_02.py::test_airlines_lightbox_constants_match_history |
| 81 | a real, seeded history_page.render() call (real gallery entry, real runway event) renders its lightbox dialog exactly once, and carries zero occurrences of airlines_page's replace-form class, replace-action attribute, <form>, file input, enctype, or the framed zone's three class constants (quick task 260903-df3) anywhere (quick task 260903-btu) | ported | companion/test_view_pages_02.py::test_history_lightbox_carries_zero_replace_markup |
| 82 | airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR and airlines_page.LIGHTBOX_REPLACE_FORM_CLASS each appear in companion/static/panel-lookup.js's source and in a real airlines_page.render({}) call, the exact '.lightbox__replace' selector (not merely a substring, which the newer '.lightbox__replace-zone' selector could otherwise satisfy) appears in companion/static/style.css standalone or as the head of the phase-14 three-way group, and neither token appears in a real, seeded history_page.render() call (quick task 260903-btu; these two constants have no history_page counterpart by design and must never join _airlines_lightbox_constants_match_history()'s pairs tuple; pattern retargeted in place by phase 14 plan 14-03 Task 2) | ported | companion/test_view_pages_02.py::test_replace_lightbox_names_appear_in_three_files_never_in_history |
| 83 | airlines_page.render({}) with a literal empty dict still succeeds and its output still contains the gallery grid (quick task 260902-v26's ctx.get("state_dir") tolerance) | ported | companion/test_view_pages_02.py::test_airlines_render_empty_ctx_still_contains_gallery_grid |
| 84 | a render with an eligible gap emits the "Unidentified airlines" strip with its exact heading and sentence after the filter bar and the gallery grid, and the curated artwork grid holds no gap card (D-21/A-38, 19-08-PLAN.md Task 1, order superseded by CFG-82, 29-02-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_gap_strip_renders_after_the_gallery_with_heading_and_no_grid_placeholder |
| 85 | a render with no eligible gaps emits no "Unidentified airlines" strip and no empty section (D-21, 19-08-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_airlines_gap_strip_absent_with_no_gaps |
| 86 | on a render with both an eligible gap and at least one curated gallery card, the page's own sections chain title < filter bar < gallery grid < "Unidentified airlines" strip < the lightbox dialog, each literal occurring exactly once (CFG-82, 29-02-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_section_order_is_title_then_filter_then_gallery_then_gapstrip_then_lightbox |
| 87 | the reorder does not touch render()'s own no-chrome gate: a render with gap cards but no curated pairs still shows the filter bar, and a render with neither shows no filter bar at all (CFG-82, 29-02-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_no_chrome_gate_survives_the_reorder |
| 88 | the resolve panel's back link renders exactly once, named "← Back to Airlines" and targeting airlines_page.AIRLINES_ROUTE, superseding the Phase 13 Copy Deck's "Back to Health" (D-21, A-38, 19-08-PLAN.md Task 2) | ported | companion/test_view_pages_02.py::test_airlines_resolve_panel_back_link_names_and_targets_airlines |
| 89 | a default airlines_page.render({}) call (no query parameter involved) carries exactly one each of the dialog's replace form, delete form and upload zone — the page-wide editing mode that used to gate replace/delete behind an exact ?edit=1 is deleted (CFG-81, 29-01-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_default_render_always_has_the_dialogs_forms |
| 90 | a render of a Step-B entry (name saved, no artwork yet) contains exactly two upload zones and two manual-delete forms (the no-JS fallback panel's own copy plus the lightbox's, both unconditional per CFG-81), and exactly one replace form (the dialog's own copy — this no-JS fallback panel has none of its own) (D-19, 21-06-PLAN.md Task 1; retargeted by 29-01-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_default_render_step_b_upload_zone_unconditional |
| 91 | a default airlines_page.render({}) call still contains exactly one lightbox__resolve-name form - naming a prefix stays the everyday action (D-22, 19-08-PLAN.md Task 3) | ported | companion/test_view_pages_02.py::test_airlines_default_render_keeps_exactly_one_resolve_name_form |
| 92 | the deleted page-wide editing toggle (its class literal) and the deleted ?edit= query parameter (its literal form) never render again, in either language, whether the query string is absent or carries an arbitrary unrelated value (CFG-81, 29-01-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_no_page_wide_editing_mode_survives |
| 93 | a French render of Airlines shows the French page title, filter label and lightbox aria-label, while a real airline name ('Air France') stays untranslated data (D-05, 20-10-PLAN.md Task 2; the toggle-text needle retired by 29-01-PLAN.md/CFG-81) | ported | companion/test_view_pages_02.py::test_airlines_french_render_translates_headings_not_data |
| 94 | a fully-seeded Airlines render under lang='fr' shows the French gap-strip heading/sentence and resolve-panel copy with no English leaking in, the seeded example callsign stays untranslated data, and the identical seeded render under the default language still carries every pre-existing English needle (D-05, 20-10-PLAN.md Task 2; the toggle-label needle retired by 29-01-PLAN.md/CFG-81) | ported | companion/test_view_pages_02.py::test_airlines_full_seeded_render_french_end_to_end |
| 95 | every key in companion/i18n_fr/airlines.py's own CATALOG is also a key of the merged companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up (20-10-PLAN.md Task 2) | ported | companion/test_view_pages_02.py::test_airlines_catalog_keys_all_present_in_merged_catalog |
| 96 | the resolve dialog's data-view-panel-first-seen/-last-seen carry FORMATTED Europe/Paris text byte-identical to the no-JS path's own rendered <dd> text for the same row (15:49 UTC reading 17:49), and neither render carries a single ISO-8601 timestamp anywhere (B5/D-05, 22-11-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_resolve_dialog_seen_attributes_carry_formatted_paris_local_text |
| 97 | companion/static/panel-lookup.js contains no date-parsing or date-formatting API at all (new Date/Date.now/toISOString/toLocale*/getHours/getMinutes/getTime/Intl.DateTimeFormat) and assigns the first-seen/last-seen attribute values straight to textContent — the property that keeps D-05's Paris-local rule enforceable server-side (B5, 22-11-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_panel_lookup_js_does_no_date_math_of_any_kind |
| 98 | the resolve dialog's Save and Close share ONE .lightbox__actions row — quiet Close first, primary Save second and re-attached to its form by the native form= attribute — while the no-JS fallback keeps its own submit inside its own form, and the row's rule declares flex/centre/space-between with no shared height (C4) and no .btn-- family (B5, 22-11-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_resolve_dialog_save_and_close_share_one_action_row |
| 99 | a normal Airlines render carries no Editing badge and no per-card Replace control anywhere (both deleted outright, CFG-81) — while every airline-card__zoom trigger still carries the SAME full data-view-panel-* vocabulary, its size derived from the module's own _VIEW_PANEL_*_ATTR constants rather than a hardcoded number (29-01-PLAN.md) | ported | companion/test_view_pages_03.py::test_airlines_cards_carry_no_badge_or_per_card_control_but_full_vocabulary |
| 100 | the manual-resolution count renders as a real filter control INSIDE the Airlines filter bar wearing .airline-card__chip's label voice — the 12px bare link and its copied [data-filter-clear] property list are retired, leaving only a hover-additive rule — and one entry reads '1 manual resolution' (FR '1 resolution manuelle') while two read '2 manual resolutions' (X7 + D-06/B16, 22-11-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_airlines_manual_count_is_a_filter_control_in_the_filter_bar |
| 101 | below 960px .illustration-grid takes a FIXED repeat(2, minmax(0, 1fr)) template — two cards per row with a zero column minimum — while the desktop auto-fill idiom above 960px is left untouched (X7, 22-11-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_airlines_grid_is_two_fixed_columns_below_960px |
| 102 | a formatted row with a resolved airline produces a Flight cell (desktop) and a phone card (mobile) carrying neither a one-hop resolve link nor the retired two-hop Health route (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_unresolved_link_absent_for_resolved_airline |
| 103 | a formatted row whose airline is unresolved produces exactly one ONE-HOP resolve anchor in the desktop Flight cell and exactly one on the phone card, both naming the prefix derived from that row's own callsign (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_unresolved_link_present_once_each_for_unresolved_airline |
| 104 | a row whose route is unresolved but whose airline IS resolved produces no unresolved-airline link - the link is keyed on the airline label, not on the route label | ported | companion/test_view_pages_03.py::test_unresolved_link_keyed_on_airline_not_route |
| 105 | a no-airline row renders AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT as two distinct strings in two distinct columns, and the unresolved-link's spacing class is styled in style.css and present in the rendered anchor (quick task 260902-w4t, UIR-05) | ported | companion/test_view_pages_03.py::test_airline_fallback_distinct_from_route_fallback |
| 106 | a callsign-less row's desktop Flight cell is empty with zero copy buttons and no visible hex (21-03-PLAN.md Task 1, D-15); the mobile card still promotes the hex to its primary slot with a no-copy-button 'no callsign' note (D-16); a callsign+hex row is unaffected; a row with neither renders without raising (quick task 260902-w4t, UIR-06) | ported | companion/test_view_pages_03.py::test_hex_only_row_promotes_hex_to_primary |
| 107 | history_page.RESOLVE_LINK_HREF_TEMPLATE is built from airlines_page.AIRLINES_ROUTE and RESOLVE_QUERY_PARAM (never a re-typed literal), the retired two-hop Health constant is gone, and resolve_prefix_for_callsign() derives a prefix only for a callsign the registry writer's own shape gate would accept (22-09-PLAN.md Task 2, X5/T-22-30) | ported | companion/test_view_pages_03.py::test_resolve_link_template_matches_the_airlines_resolve_view |
| 108 | the rendered Flights table carries exactly one day-separator row per EUROPE/PARIS calendar day present in the rows — Today / Yesterday / an absolute date, translated in both languages — and a row whose UTC day differs from its Paris day is grouped by the Paris one (22-09-PLAN.md Task 2, X5/D-05) | ported | companion/test_view_pages_03.py::test_day_separators_group_rows_by_europe_paris_calendar_day |
| 109 | the day separator's absolute label is the day portion of layout.local_clock_text()'s own cross-day output in both languages, history_page.py contains zero strftime calls, paris_day() degrades to None rather than raising, and the separator's CSS rule declares no positioning (22-09-PLAN.md Task 2, X5/D-05/T4) | ported | companion/test_view_pages_03.py::test_day_label_is_the_paris_day_formatters_own_output_and_never_sticky |
| 110 | every rendered Flights row carries a non-empty, unique event identity in BOTH representations, the table and the card list name the same event set, and a newer detection arriving at the top leaves every existing row's identity unchanged — the property the row's position does not have and the whole basis of the new-row highlight (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_every_flights_row_carries_a_stable_event_identity |
| 111 | the rendered Flights page carries exactly one data-loaded-at marker and a witness for every one of its REFRESH_SWAP_SELECTORS_BY_PAGE regions, and no region names the filter input list-filter.js captured at load (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_flights_declares_its_refresh_regions_and_never_the_filter_input |
| 112 | the Flights detail row animates open through a grid reveal wrapper inside its own <td> (grid-template-rows 0fr, var(--motion-fast), an @starting-style entry, scoped to the class flight-rows.js adds to <html>), neither interpolate-size nor calc-size() appears, and the collapsed end state is still display: none — the one state that takes a closed row out of both the tab order and the accessibility tree (D3/CFG-32, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_detail_row_height_animates_and_a_closed_row_is_unreachable |
| 113 | the row-toggle chevron transitions TRANSFORM on var(--motion-fast) and adds no per-rule reduced-motion block — the global override already covers a plain transform for free, and the stylesheet's live prefers-reduced-motion count is unmoved at 3 (D3/CFG-32, references/control-density.md:78, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_the_chevron_turns_and_carries_no_reduced_motion_block_of_its_own |
| 114 | the phone card's own face IS the native disclosure's <summary> — the primary line, the secondary line, the time and 22-09's thumbnail and airline name all inside it, so a tap anywhere opens the card with no script at all — while the one-hop resolve link stays on the card and OUT of the summary, and the disclosure body still holds exactly the three copy buttons (D7/CFG-37, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_the_phone_cards_own_face_is_its_disclosure_summary |
| 115 | the phone summary card's .history-card__primary line is a two-track CSS grid (minmax(0, 1fr) then auto, no justify-content) with a non-wrapping .history-card__time (white-space: nowrap, no margin-left: auto), and all three primary_value_html branches — callsign, hex-plus-note, empty — produce a child set the grid can place with no third, unclassified top-level child (2026-09-17 audit P1, 29-03-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_history_card_primary_grid_pins_the_timestamp_track |
| 116 | two renders of a 36-row fixture at the SAME ?limit= value produce byte-identical pagination state (standing in for freshness.js's own re-fetch of the unchanged window.location.href), '.flights-more' is a declared swap region, and freshness.js carries exactly one fetch( call targeting window.location.href verbatim — the structural half of the refresh-survival property this harness can prove without a browser (29-RESEARCH.md, 29-03-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_reveal_state_reproduces_from_the_url_alone |
| 117 | the Show-more anchor renders with an href and no onclick/data- attribute and is never a <button> or <form>, and zero companion/static/*.js files mention its 'flights-more' class (scanned-file floor >= 17, printed on failure) — a no-JS control proof, not merely a render (29-03-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_reveal_control_is_a_plain_anchor_no_script_mentions |
| 118 | the Show-more anchor's rendered tag agrees with a REAL CSS selector match (rightmost compound's tag qualifier, if any) — not merely a class-string substring shared between the markup and style.css (CR-01, 29-REVIEW.md) | ported | companion/test_view_pages_03.py::test_flights_reveal_anchor_has_a_matching_css_selector |
| 119 | history_page.flights_limit() clamps all 19 hostile inputs into [15, 50] without raising, render() calls it exactly once and never reads ctx['flights_limit'] directly, companion/app.py performs no arithmetic or comparison on the raw threaded value, and HISTORY_ROW_LIMIT is the literal ceiling flights_limit()'s own source uses (T-29-03-01, T-29-03-02, 29-03-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_render_defers_entirely_to_flights_limit_for_hostile_ctx_values |
| 120 | the filter count animates its ELEMENT and never its number: the template-driven text production is untouched, the text is written before the class is added, the class is removed and re-added across a forced reflow so a second change restarts it, and it fires only when the rendered value actually differs (D7/CFG-37, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_the_count_animates_without_its_text_production_moving |
| 121 | the phone card's "ORY → JFK Departing" line carries the module's EXISTING cell-inline-sep middle dot between the route and the state, reused rather than reinvented (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_phone_card_route_and_state_carry_the_existing_middle_dot |
| 122 | the raw ISO timestamp appears only inside a data-copy-value attribute, while the visible full timestamp is the Europe/Paris local clock in the .time-value role on both the desktop detail row and the phone card (22-09-PLAN.md Task 2, X5/D-05/C5) | ported | companion/test_view_pages_03.py::test_raw_iso_survives_only_behind_the_copy_control |
| 123 | a phone card carries the airline name and, when real artwork exists for it, the Airlines gallery's own served frame as a thumbnail joining the shared white-backing/hairline/radius rule in a contain-fitted 56px box — and no <img> at all when no artwork file exists (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_phone_cards_carry_the_airline_name_and_artwork_thumbnail |
| 124 | the rendered History page contains no prefix-registry table and no element carrying the registry table's own headers | ported | companion/test_view_pages_03.py::test_no_prefix_registry_duplicated_on_history |
| 125 | a French render of Flights shows the French page title, column headers and filter label, while a seeded callsign stays untranslated data (D-05, 20-10-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_french_render_translates_headings_not_data |
| 126 | a fully-seeded Flights render under lang='fr' shows every new French string (column headers, direction words, the unresolved-airline fallback, the no-callsign note, the disclosure summary and the filter's Clear button) with no English leaking in, the seeded callsign stays untranslated data, and the identical seeded render under the default language still carries every pre-existing English needle (D-05, 20-10-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_full_seeded_render_french_end_to_end |
| 127 | every key in companion/i18n_fr/flights.py's own CATALOG is also a key of the merged companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up (20-10-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_catalog_keys_all_present_in_merged_catalog |
| 128 | home_page.render() with seeded flights, a battery reading and a gallery entry renders the hero picture, the battery percentage estimate, escaped recent flights, and the Next-update headline, with .preview-frame before .recent-flight in document order (D-04) | ported | companion/test_view_pages_03.py::test_home_page_render_with_seeded_state |
| 129 | Home's Battery tile draws exactly one ring, inside that tile, whose drawn fraction equals the '≈ NN%' it still prints beside its own millivolt detail and verdict; the ring is SMALLER than Health's yet identical to it in radius-over-box and stroke-over-box, proving one emitter at two sizes rather than two components; the frame verdict still appears exactly once; and a device with no reading draws no ring at all (CFG-40) | ported | companion/test_view_pages_03.py::test_home_battery_ring_is_the_same_drawing_at_a_smaller_size |
| 130 | Home's recent-flight relative age is a <time data-relative> element carrying the ROW's own instant, reading exactly what it reads today in both languages, with C5's .time-value/.cell-inline-sep/.time-value__age split and its parentheses intact (23-03, D14/CFG-34) | ported | companion/test_view_pages_03.py::test_home_recent_flight_age_is_an_element_reading_exactly_as_before |
| 131 | Home's rendered-picture caption carries concise_timestamp_html()'s <time data-relative> element THROUGH its i18n template's own %s — as markup, never double-escaped — with the caption's wording and the age's text unchanged in both languages (23-03, D14/CFG-34) | ported | companion/test_view_pages_03.py::test_home_rendered_caption_carries_the_element_through_the_template |
| 132 | a recent-flight row whose airline resolves to a real illustration file renders exactly one lazily-loaded /illustration/ thumbnail <img>; a null/unrecognised airline AND an airline whose normalised key resolves to no file on disk anywhere (override or vendored) both render the dashed placeholder span with no <img> at all (D-17 fix) | ported | companion/test_view_pages_03.py::test_recent_flight_thumb_resolved_vs_placeholder |
| 133 | the hero's flight one-liner (callsign in .mono, then airline, then the route) appears when the current flight is known and is absent otherwise, and the page reads header -> .frame-strip -> .home-status-grid -> .home-picture-row (.preview-frame before .recent-flight inside it) (D-04) | ported | companion/test_view_pages_03.py::test_hero_figure_precedes_status_card_with_flight_one_liner_when_known |
| 134 | under a French request Home's headings ('Vols récents'/'Voir tous les vols') and a thumbnail's alt text translate while the callsign/airline name stay untranslated data (D-05) | ported | companion/test_view_pages_03.py::test_home_page_french_render_translates_headings_and_alt_text_not_data |
| 135 | a fully-seeded Home render under lang='fr' shows the French page title, section headings, status-row labels and next-update headline with no English string leaking in (while the callsign/airline data stays untranslated), and the identical seeded render under the default language still carries every pre-existing English needle | ported | companion/test_view_pages_04.py::test_home_full_seeded_render_localises_to_french_without_leaking_english |
| 136 | Home's status card, fed a REAL health_page.compute_health_state() result computed under lang='fr', fully localises the Frame/Flight-data rows' timestamps (no English month abbreviation or ' ago' survives) and the Flight-data row's detail is now a single, verdict-free clause — never joined with ' · ', never repeating Health's own verdict wording (Polish fix 2 / 22-07-PLAN.md Task 1 B2 retarget) | ported | companion/test_view_pages_04.py::test_home_status_card_localises_real_health_state_timestamps_under_french |
| 137 | the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris): Home's Frame tile and the strip render the SAME clock string, and zero warn/error tokens appear anywhere on the page (X2, D-03/CFG-26) | ported | companion/test_view_pages_04.py::test_home_frame_tile_matches_strip_for_the_nightly_held_regression |
| 138 | a late frame flips the strip to 'Expected since'/dot--warn and Home's Frame tile to its own late verdict/stat-tile--warn together, at the same threshold — they cannot disagree because neither computes anything the other does not (X2) | ported | companion/test_view_pages_04.py::test_home_frame_tile_flips_to_late_together_with_the_strip |
| 139 | Home's Flight-data tile renders exactly one verdict (its own DATA_STATE_TEXT) with Health's verdict-free pipeline_detail_html beneath it, never Health's own PIPELINE_STATE_TEXT verdict sentence a second time (B2) | ported | companion/test_view_pages_04.py::test_home_flight_data_tile_one_verdict_verdict_free_detail |
| 140 | a recent-flight row whose stored airline is an alias ("CCM Airlines") renders the SAME display name ("Air Corsica") Flights shows via display_airline_name(), never the raw upstream string (X4) | ported | companion/test_view_pages_04.py::test_home_recent_flights_use_display_airline_name_matching_flights |
| 141 | exactly one element on a rendered Home page is named 'Frame' (the shared strip's own heading) — Home's tile caption is renamed to resolve the X4 collision | ported | companion/test_view_pages_04.py::test_home_exactly_one_element_named_frame |
| 142 | the recent-flight time cell markup carries no monospace class, and reads the clock (.time-value), the existing .cell-inline-sep middle dot and the relative age (.time-value__age) as one line (B18) | ported | companion/test_view_pages_04.py::test_home_recent_flight_time_one_line_no_mono_class |
| 143 | .home-status-grid's own CSS rule declares align-items: stretch (B2) | ported | companion/test_view_pages_04.py::test_home_status_grid_declares_align_items_stretch |
| 144 | .recent-flight__time's own CSS rule declares white-space: nowrap so the clock/age pair can never wrap onto a second line (B18) | ported | companion/test_view_pages_04.py::test_recent_flight_time_declares_white_space_nowrap |
| 145 | the real recent-flight thumbnail joins the shared white-backing/hairline/radius rule and the placeholder's own rule reuses .airline-card__placeholder's exact dashed/canvas-fill values (never a new literal, never sharing that pinned selector), so a missing thumbnail matches the real ones in weight (B18) | ported | companion/test_view_pages_04.py::test_recent_flight_thumbnails_share_the_shipped_treatments |
| 146 | companion/static/style.css still carries exactly one @supports selector(:has(*)) block — this plan opens no second one | ported | companion/test_companion_app_03.py::test_style_css_carries_exactly_one_has_feature_query_block |
| 147 | every key in companion/i18n_fr/home.py's own CATALOG is also a key of the merged companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up | ported | companion/test_view_pages_04.py::test_home_catalog_keys_all_present_in_merged_catalog |
| 148 | a rendered Home page carries no status-card__rows/home-hero markup, quick-action markup only inside .frame-strip (exactly two cells) and nowhere else, exactly three stat-tile elements labelled Frame/Battery/Flight data, and the Frame verdict sentence exactly once (D-04/D-05) | ported | companion/test_view_pages_04.py::test_home_full_render_has_quick_action_only_inside_strip_and_three_tiles |
| 149 | the Frame strip's headline reads 'Next update ≈ HH:MM' for a future next-update, 'Expected since HH:MM' in the warn treatment for a past one, and renders no headline at all when either the check-in or the wake interval is unknown (D-01, moved from the deleted _status_card_html()) | ported | companion/test_view_pages_04.py::test_home_status_card_headline_next_update_or_expected_since |
| 150 | a default Home render always carries the status tiles section's 'See details on Health' link (D-17) | ported | companion/test_view_pages_04.py::test_home_status_card_always_shows_health_link |
| 151 | home_page.render({}) degrades to its empty states without raising, battery.battery_percent() clamps and rejects bad input, and the gallery filename parser round-trips or returns None | ported | companion/test_view_pages_04.py::test_home_page_render_degrades_with_nothing |
| 152 | battery_percent() no longer exists on home_page after moving to companion/battery.py (D-01) | ported | companion/test_view_pages_04.py::test_battery_percent_moved_out_of_home_page |
| 153 | draw.percent_time() is a TIME scale and not the index scale beside it: midnight/midday/the day's final instant land at 0/50/100%, an hour is 1/24 of the band however many other instants are on it (so an outage draws as an outage), a DST day's own length is a parameter rather than a hardcoded 86400, and an instant outside the day is REJECTED rather than clamped onto an edge where it would invent a check-in (CFG-42, T-24-06-A, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_time_scale_places_by_when_not_by_index |
| 154 | the day band renders a wrapping night window (22:00-07:00) as TWO shaded spans covering nine hours, one flush to 00:00 and one flush to 24:00 with midday left clear — never one inverted span that would shade the middle of the day — while a daytime window stays one span and an absent/zero-width/out-of-day/malformed window shades nothing at all (CFG-42, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_night_window_shades_the_night_as_two_spans |
| 155 | the day band collapses marks closer than its own stated minimum spacing and returns EXACTLY how many it hid — 48 marks at a 30-minute cadence with nothing collapsed, a 60-second and a 1-second cadence both bounded by the band's width rather than the row count (T-24-06-C), no two kept marks under the minimum apart, and an unplaceable instant counted too so a caption built from the number can never claim a total the drawing does not reach (T-24-06-B, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_collapses_crowded_marks_and_reports_exactly_how_many |
| 156 | every class the day band emits is one of companion/draw.py's own named constants and is registered in DRAWING_CLASSES (so the stylesheet-resolution guard can see it), the markup carries no colour literal, no url() reference and no inline style, and a band supplied with a label announces itself as a named group rather than being hidden (CFG-39/CFG-42, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_emits_only_registered_classes_and_no_colour |
| 157 | Home's day band draws one mark per check-in at its PARIS clock position, captions the Paris day it shows and states the count as text; a day with no check-ins still renders the band and its frame with a caption naming the day (an absent section would read as an unbuilt feature, an empty band reads as no activity); and with history.db unreadable the page renders with no band at all rather than an empty one claiming no check-ins (CFG-42, T-24-06-D, 24-06-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_home_day_band_renders_the_day_and_says_what_it_shows |
| 158 | Home's day band shades the CONFIGURED quiet-hours window — the default 23:00-07:00 wrapping night window as two spans covering its eight hours, named in the caption — and with quiet hours disabled shades nothing and says nothing about them, while still drawing the day's check-ins (CFG-42/D-03, 24-06-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_home_day_band_shades_quiet_hours_only_when_configured |
| 159 | Home's day band buckets check-ins by the PARIS day — a 22:30Z check-in (Paris 00:30 today) is on the band and a 2026-08-27T22:30Z one (Paris 00:30 tomorrow) is not, the mirror of the boundary 24-06-PLAN.md Task 2 named since Paris is never behind UTC — and spans a real 25-hour Paris day so midday lands at 52.00% rather than the 54.17% a hardcoded 86400 would give; it costs render() exactly one history.db read more than the two it made before, measured, and the frame verdict still appears exactly once (CFG-42/D-20, 24-06-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_home_day_band_buckets_by_paris_day_and_costs_one_read |
| 160 | Home's top is ONE composition: a single hero container holds the shared Frame strip (rendered once, unforked), the three status tiles carrying the battery ring, and the day band — the picture row stays outside it, the ring and the band each appear exactly once and both inside the hero, home_page.py carries no ring geometry and no second battery estimate (an unqualified battery_percent( is refused by a boundary regex), and the frame verdict still appears exactly once in BOTH languages (CFG-44, 24-08-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_home_top_is_one_composition_holding_the_ring_and_the_band |
| 161 | the hero's battery ring is the same emitter Health's ring is — the two pages' rings carry one class vocabulary, computed from the markup rather than listed; the hero's day band draws three different shapes and not one; every class either of them emits is a constant companion/draw.py itself names; and neither companion/pages/home_page.py nor this check writes any of those strings down, because a literal goes on passing against a forked copy that still uses the old one (CFG-44, 24-08-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_the_heros_ring_is_the_emitter_healths_ring_is |
| 162 | breaking a shared emitter breaks the hero WITH the page it borrowed it from: one class constant inside companion/draw.py's ring emitter is replaced at check time and both Home's hero and Health's readout change, neither keeping the original string (a hero built from its own copy would); the band emitter's own mutation reaches the hero and leaves Health byte-identical, proving the mutation is targeted rather than a global perturbation; and both pages return to their pre-mutation markup (CFG-44, 24-08-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from |
| 163 | wake.next_wake_at_iso()/next_wake_status() return None/(None, None, None) for a falsy/unparseable ts or an unknown interval, last_checkin + wake_interval_s for a screen-on config, last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config (D-13's screen-off rule), and — 22-02-PLAN.md Task 1, D-03/CFG-26 — the quiet-hours-active fixtures: a window opening during the base interval wins over the naive candidate, an enabled-but-nowhere-near-active window changes nothing, an active window beats a 300s screen-off cadence, and the richer accessor carries the same effective interval and hold reason for every fixture above | ported | companion/test_view_pages_04.py::test_wake_next_wake_at_iso_contract |
| 164 | companion.frame_state.resolve_state() resolves due/held/late/unknown from a (next_wake_iso, effective_interval_s, hold_reason, now) tuple with an invisible grace window and a held frame that cannot escalate by elapsed time alone, headline_template()/delay_sentence_template() return the matching three-branch copy constants, and the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris) resolves to STATE_HELD end to end through wake.next_wake_status() (D-03/D-04, 22-02-PLAN.md Task 2, 22-UI-SPEC.md §3.3 binding rule 6) | ported | companion/test_view_pages_04.py::test_frame_state_resolve_state_contract |
| 165 | companion/frame_state.py names no dot--warn class and imports no layout module (view-free, D-03), and each of its six copy constants round-trips through companion.i18n's French catalogue unchanged in English (22-02-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_frame_state_is_view_free_and_localises_its_own_copy |
| 166 | companion/battery.py imports neither companion.pages nor server, preserving its shared, page-independent boundary (D-01) | ported | companion/test_companion_app_03.py::test_battery_module_imports_neither_a_page_module_nor_the_server_package |
| 167 | GET /history returns 200 with its own heading, GET /preview redirects (303) to /history, GET /preview.png now returns 404 (the route is retired), and GET /gallery/{name}.png returns 200 image/png with a real PNG signature — proving the route the per-row View-panel lightbox now links to genuinely serves full-resolution bytes, against a real running service | ported | companion/test_view_pages_04.py::test_history_preview_and_gallery_round_trip_over_http |
| 168 | a real authenticated GET of /airlines renders the dialog's replace, delete and upload-zone forms with no query string at all, and a leftover ?edit=1 in a bookmark renders identically — against a real running service, proving the removed query parameter has no reader anywhere in the real request path (CFG-81, 29-01-PLAN.md) | ported | companion/test_view_pages_04.py::test_airlines_dialog_forms_render_unconditionally_over_real_http |
| 169 | both <dialog>s arrive through ONE @starting-style entrance on .lightbox[open] — fading and zooming from opacity 0 over var(--motion-fast), reaching History's lightbox and the Airlines gallery's wide variant from a single rule, with `display`/`allow-discrete` deliberately absent so close() ends the dialog outright rather than leaving an invisible click-swallowing sheet over the page (T-23-36), and with ::backdrop unanimated because the global reduced-motion override cannot reach it (D3/CFG-32, 23-10-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_both_dialogs_arrive_through_one_starting_style_entrance |


### Part 01 (plan 33-05)

37 checks migrated to `companion/test_view_pages_01.py` (helpers in
`companion/test_view_pages_helpers.py`). Rubric codes: B x 10 (render()
calls and their output, or pure-Python behaviour with no rendering at
all), D x 21 (structural regex-over-rendered-HTML rewritten as
`companion_markup.parse_html()`/`select()`/`find_all()`, several through
the shared `row_block()` helper), C x 4 (checks that opened
`companion/static/style.css` from disk rewritten over
`served_stylesheet()` + `css_rules()`/`declarations_for()`), S x 2
(source-text scans - "never imports html", "never redefines
_TYPE_DISPLAY_LABELS" - rewritten as `getattr()`/`hasattr()` identity
checks with no file read). 0 deleted - every check in this slice had a
direct behavioural or parsed-DOM equivalent. New module:
`companion/test_view_pages_01.py` (37 tests). Legacy
`companion/test_view_pages.py` shrinks from `EXPECTED_CHECK_COUNT = 169`
to `EXPECTED_CHECK_COUNT = 132` (132/132 still pass standalone).

### Part 02 (plan 33-06)

59 checks migrated to `companion/test_view_pages_02.py` (helpers added to
`companion/test_view_pages_helpers.py`: `detail_row_block()`,
`table_markup()`, `seed_gallery()`, `seed_unresolved_prefixes()`,
`write_panel_file()`, `strip_js_line_and_block_comments()`). Rubric
codes: D x 33 (structural/substring regex over RENDERED output —
`history_page.render()`/`airlines_page.render()` return values, never a
file opened from disk), J x 14 (checks that opened
`companion/static/panel-lookup.js`, `flight-rows.js` or `copy-button.js`
from disk rewritten over `served_asset()` — the served text is scanned
with the same string/regex assertions as before, since it is now
behaviour, not source; the one check needing an unstripped-of-strings
comment pass, `image.src = ""`, uses the new local
`strip_js_line_and_block_comments()` rather than
`companion_markup.strip_js_comments_and_strings()`, which would also
erase the empty-string literal it looks for), C x 5 (checks that opened
`companion/static/style.css` from disk rewritten over
`served_stylesheet()` + `declarations_for()`, including the two at-rule
checks scoped to `@media (min-width: 960px)`), B x 7 (pure-Python
behaviour with no rendering, or a production function call asserted on
its output — `nearest_gallery_entry()`, `_gallery_name_to_iso()`,
`manual_resolutions.add_entry()`, the `airlines_page`/`history_page`
lightbox-constant-equality and reflection-driven attribute-classification
checks, the merged-i18n-catalogue-key checks). 0 deleted - every check
in this slice had a direct behavioural, served-asset or parsed-structure
equivalent; the one source-text check in the slice (row 40's
"`history_page.py` never renders the script's own clickable marker
class") is rewritten as a `history_page.render()` assertion instead of
an `open()` of `history_page.py`. New module:
`companion/test_view_pages_02.py` (59 tests). Legacy
`companion/test_view_pages.py` shrinks from `EXPECTED_CHECK_COUNT = 132`
to `EXPECTED_CHECK_COUNT = 73` (73/73 still pass standalone and through
the shim); the three lightbox token tuples
(`_LIGHTBOX_SHARED_TOKENS`/`_LIGHTBOX_AIRLINES_ONLY_TOKENS`/
`_LIGHTBOX_RENDER_ONLY_TOKENS`), `_NEW_VIEW_PANEL_ATTR_NAMES` and
`_read_panel_lookup_source()` are deleted from the legacy file (only
this slice's checks used them); `_strip_js_comments()` stays (still used
by later, still-legacy sections).

### Part 03 (plan 33-07)

38 checks migrated to `companion/test_view_pages_03.py` — the slice
holding most of this harness's JS-source contracts (panel-lookup.js's
date-math ban, flight-rows.js's live-script class, list-filter.js's
count-animation contract, freshness.js's single fetch() target),
Airlines' resolve-dialog action row and manual-count filter chip
(22-11-PLAN.md), the one-hop unresolved-airline link (22-09-PLAN.md
Task 2), Flights' day separators/row-identity/refresh-regions/detail-
reveal/Show-more contracts (23-08/29-03-PLAN.md), and Home's battery
ring, relative-age elements and French render (22-11/23-03/20-10-PLAN.md).
No new shared helpers were needed beyond what 33-06 already added to
`companion/test_view_pages_helpers.py`; this slice's one module-local
addition is a raw-string `_row_block()` (the summary-row sibling of
`vp.row_block()`'s Node contract, kept module-local like
`test_view_pages_02.py`'s own precedent) and `_all_static_script_routes()`
(enumerates every `companion/app.py` `*_SCRIPT_ROUTE` constant, replacing
a `glob.glob()` over `companion/static/*.js` with a non-hardcoded,
self-updating floor derived from the production module's own registered
route names — TST-12 forbids reading a production source file as text,
not introspecting an already-imported module's public constants).

Rubric codes: B x 25 (render()/production-function calls and their
output, or pure-Python behaviour with no rendering), C x 9 (checks that
opened `companion/static/style.css` from disk rewritten over
`served_stylesheet()` + `css_rules()`/`declarations_for()`/
`rules_with_selector()`, including two at-rule-scoped lookups —
`@media (max-width: 959.98px)` and `@starting-style`), J x 5 (checks
that opened a served JS asset from disk rewritten over `served_asset()`,
one of which — the flight-rows.js live-script-class check — uses the
existing `vp.strip_js_line_and_block_comments()` rather than
`companion_markup.strip_js_comments_and_strings()`, because the class
name it searches for is itself a JS string literal that the toolkit
stripper would erase). 0 checks deleted outright — every check in this
slice had a direct behavioural, served-asset, or parsed-structure
equivalent — but 2 partial S-rubric deletions inside otherwise-ported
checks:

- row 109 (`test_day_label_is_the_paris_day_formatters_own_output_and_never_sticky`):
  the legacy check's `"strftime" not in open(history_page.py).read()`
  clause is dropped. The behavioural equivalence the same check already
  asserts (the day label equals the day PORTION of
  `layout.local_clock_text()`'s own cross-day output) already proves the
  label comes from the shared Paris-local formatter rather than a second
  date-formatting path; the source-text grep added no behaviour beyond
  that comparison.
- row 119 (split into `test_flights_limit_clamps_every_hostile_input_into_bounds`
  parametrized ×19 and `test_flights_render_defers_entirely_to_flights_limit_for_hostile_ctx_values`,
  the ledger's primary target): the legacy check's
  `ast.parse(inspect.getsource(history_page.render))` proof that
  `render()` calls `flights_limit()` exactly once and never reads
  `ctx['flights_limit']` directly, and its `inspect.getsource(app_module)`
  line-count proof that `app.py` performs no arithmetic on the raw
  threaded value, are both dropped (guard G2 bans `inspect`/`ast`
  introspection of production source outright). Replaced by a strictly
  stronger behavioural proof: `render()` is called directly with the
  same 11 hostile `ctx['flights_limit']` values against a 60-row seeded
  fixture, and the rendered card count must equal `flights_limit()`'s
  own clamp for every one of them — if `render()` had any second,
  unvalidated path onto the raw value, the observed count would diverge
  from `flights_limit()`'s clamp for at least one hostile input.

New module: `companion/test_view_pages_03.py` (57 pytest node ids: 37
non-parametrized tests + the 19-way `test_flights_limit_clamps_every_hostile_input_into_bounds`
parametrization, covering the 38 baseline rows above). Legacy
`companion/test_view_pages.py` shrinks from `EXPECTED_CHECK_COUNT = 73`
to `EXPECTED_CHECK_COUNT = 35` (35/35 still pass standalone and through
the shim); the module-local `_row_block()` closure, the module-level
`_strip_js_comments()`/`_detail_row_block()`/`_table_markup()`/
`_seed_unresolved_prefixes()` helpers and the `glob`/`math`/
`server.plane.illustrations`/`server.plane.manual_resolutions`/
`server.poll_loop` imports are deleted from the legacy file (confirmed
by grep to be used exclusively by this slice); two nested functions
further down the still-legacy file (`_home_top_is_one_composition_holding_the_ring_and_the_band`,
`_the_heros_ring_is_the_emitter_healths_ring_is`) had their own
redundant local `import ast`/`import inspect` removed as a Rule 1 fix —
deleting this slice's own top-level `ast.parse(inspect.getsource(...))`
usage (row 119, now replaced above) left those two nested shadow-imports
as the only remaining uses of the module-level `ast`/`inspect` bindings
in file order, which `ruff` (F811) correctly flagged as a
redefinition-of-unused regression once the earlier top-level usage was
gone.

### Part 04 (plan 33-08) — chain closed

35 checks migrated to `companion/test_view_pages_04.py` (33 new pytest
node ids; 2 rows consolidated into pre-existing, identical coverage
already ported by a different harness's own migration —
`companion/test_companion_app_03.py`'s `@supports selector(:has(*))`
count and its `companion.battery` import-boundary check — rather than
duplicated, per 33-MIGRATION-RULES.md section 3). This is the chain's
LAST slice: Home's fully-seeded French render and localised health-state
timestamps, the Frame/Flight-data tile verdict contracts, four CSS-only
checks (one consolidated), the i18n catalogue membership check, Home's
quick-action/headline/health-link/degrade/battery-move contracts,
`companion/draw.py`'s day-band time-scale/night-window/crowding/class
contracts, Home's own day-band integration (Paris-day bucketing,
quiet-hours shading, one extra `history.db` read), the hero composition
(CFG-44), `companion.wake`/`companion.frame_state`'s resolution
contracts, `companion/frame_state.py`'s view-free boundary (one
consolidated), and two real HTTP round trips plus the shared
`@starting-style` lightbox entrance.

Rubric codes: B x 15 (render()/production-function calls and their
output, or pure-Python behaviour with no rendering — the day-band unit
checks, `wake`/`frame_state`'s own contracts, the two real HTTP round
trips), D x 3 (structural checks over rendered/parsed HTML — the hero
composition's containment assertions, the `.lightbox`/`.lightbox--wide`
dialog-class proof via `companion_markup.parse_html().select()`), C x 5
(checks that opened `companion/static/style.css` from disk rewritten
over `served_stylesheet()` + `companion_markup.declarations_for()`/
`rules_with_selector()` — the status-grid/recent-flight-time/thumbnail
checks and the `@starting-style` entrance, the last of which replaces
every substring/regex assertion the legacy check made over raw CSS text
with parsed `Rule.declarations` lookups), S x 4 (source-text scans
rewritten or consolidated): the hero composition's `inspect.getsource()`
forbidden-literal/required-call scan (row 160) and the ring/band
vocabulary check's `ast.parse()` restated-literal scan (row 161) are
each a PARTIAL deletion inside an otherwise-fully-ported check — their
surviving structural/vocabulary assertions stay, and the source-scan
clause is dropped because
`test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_
borrowed_it_from` (row 162) already proves the identical "no forked
copy" property strictly more strongly, by mutation rather than static
analysis (guard G2 bans `inspect`/`ast` over production source outright
regardless). `companion/frame_state.py`'s own "never imports layout"
half (row 165) is rewritten as a subprocess-import + `sys.modules`
check (the same technique `companion/test_companion_app_03.py`'s own
`battery`/`draw` import-boundary checks already established), and its
"never names a CSS dot class" half is rewritten against the module's own
already-imported public string constants. `companion/battery.py`'s
identical "never imports pages or server" check (row 166) is a full S
consolidation: `companion/test_companion_app_03.py` already ports the
exact same claim with the exact same subprocess technique, so the
ledger row points there instead of creating a second copy. 0 checks
fully deleted with no replacement.

New module: `companion/test_view_pages_04.py` (33 pytest node ids).
Legacy `companion/test_view_pages.py` is deleted outright (`git rm`) —
this is the chain's closing plan. `EXPECTED_CHECK_COUNT`/`check()`/
`main()` and every helper/fixture the file owned (`Harness`,
`http_request`, `_NoRedirectHandler`, `_mkstate()`,
`_seed_runway_events()`, `_write_panel_file()`, `_write_gallery_png()`,
`_seed_gallery()`, `_history_ctx()`, `_login()`) leave the tree with it.
`companion/test_view_pages.py` also drops out of
`skypane_test_support.legacy_companion_harnesses()`'s disk-derived set
and `companion/test_legacy_harness_shim.py`'s parametrize list the
moment the file is gone — no hand list needed editing. Baseline total:
169/169 view-pages checks accounted for across all four parts (37 + 59 +
38 + 33 = 167 new pytest node ids across `test_view_pages_01.py`/`_02.py`/
`_03.py`/`_04.py`, plus 2 consolidated into `test_companion_app_03.py`'s
pre-existing identical coverage) — 0 pending.
