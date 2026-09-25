# Ledger: companion/test_companion_app.py

Baseline: `companion__test_companion_app.txt`, 320 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | password_ok() accepts the correct password and rejects a wrong one | ported | companion/test_companion_app_01.py::test_password_ok_correct_and_wrong |
| 2 | password_ok() raises AuthNotConfigured when the password env var is unset | ported | companion/test_companion_app_01.py::test_password_ok_unconfigured_fails_closed |
| 3 | verify_session_token(issue_session_token()) is True | ported | companion/test_companion_app_01.py::test_issue_and_verify_round_trip |
| 4 | verify_session_token() returns False for five malformed inputs without raising | ported | companion/test_companion_app_01.py::test_verify_rejects_five_malformed_inputs |
| 5 | flipping a single hex character of a valid signature invalidates the token | ported | companion/test_companion_app_01.py::test_verify_rejects_flipped_signature |
| 6 | session_set_cookie_header() carries HttpOnly/Secure/SameSite=Strict/Path | ported | companion/test_companion_app_01.py::test_session_cookie_header_carries_security_flags |
| 7 | SKYPANE_COMPANION_INSECURE_COOKIES=1 drops Secure from both cookie builders while HttpOnly/SameSite=Strict/Path survive (A-34/D-17) | ported | companion/test_companion_app_01.py::test_insecure_cookies_flag_drops_secure_but_keeps_other_flags |
| 8 | SKYPANE_COMPANION_INSECURE_COOKIES="true" fails closed - Secure stays on (A-34/D-17) | ported | companion/test_companion_app_01.py::test_insecure_cookies_flag_fails_closed_on_other_values |
| 9 | deploy/skypane.env.example documents SKYPANE_COMPANION_INSECURE_COOKIES (A-34/D-17) | ported | companion/test_companion_app_01.py::test_env_example_documents_insecure_cookies_flag |
| 10 | logout_set_cookie_header() expires the cookie immediately | ported | companion/test_companion_app_01.py::test_logout_cookie_expires_immediately |
| 11 | parse_cookies() returns each cookie by name and never raises on a bad header | ported | companion/test_companion_app_01.py::test_parse_cookies_multi_and_malformed |
| 12 | LoginThrottle allows attempts up to its limit, locks out, then resets on success | ported | companion/test_companion_app_01.py::test_login_throttle_allows_locks_and_resets |
| 13 | LoginThrottle with a zero-length window releases itself and a post-window failure starts a fresh count (A-32/D-15) | ported | companion/test_companion_app_01.py::test_login_throttle_self_releases_with_zero_length_window |
| 14 | LoginThrottle with a real lockout_s releases itself once the window elapses and a post-window failure starts a fresh count (A-32/D-15) | ported | companion/test_companion_app_01.py::test_login_throttle_self_releases_with_real_window |
| 15 | a forged token signed with a different secret is rejected | ported | companion/test_companion_app_01.py::test_forged_token_different_secret_rejected |
| 16 | a hand-built token expired by one second is rejected despite a correct signature | ported | companion/test_companion_app_01.py::test_hand_built_expired_token_rejected |
| 17 | issued tokens verify within this process, but a raw-password-keyed signature (the old scheme) does not - the signing key is genuinely derived (A-33/D-16) | ported | companion/test_companion_app_01.py::test_tokens_signed_with_derived_key_not_raw_password |
| 18 | revoke(token) then is_revoked(token) is True, a never-issued token is False, and a malformed token passed to revoke() raises nothing (A-33/D-16) | ported | companion/test_companion_app_01.py::test_revoke_then_is_revoked_round_trip |
| 19 | a revoked token is pruned out of the revocation set once its own expiry passes (A-33/D-16, T-19-14: the set stays bounded) | ported | companion/test_companion_app_01.py::test_revoked_token_pruned_once_it_expires |
| 20 | AuthNotConfigured's message never contains the configured password value | ported | companion/test_companion_app_01.py::test_auth_not_configured_message_omits_password |
| 21 | escape_html() escapes all five HTML-special characters | ported | companion/test_companion_app_01.py::test_escape_html_all_special_chars |
| 22 | escape_html() coerces None to an empty string and non-strings to their string form | ported | companion/test_companion_app_01.py::test_escape_html_non_string_inputs |
| 23 | page_shell() renders one document with lang/viewport/stylesheet/title/a nav link for every NAV_TABS route | ported | companion/test_companion_app_01.py::test_page_shell_document_shape |
| 24 | the sub-960px nav link matching `active` carries a distinguishing class and aria-current, the others carry neither (retargeted from the retired dropdown nav onto the tab bar, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_01.py::test_page_shell_marks_only_the_active_sub960_nav_link |
| 25 | page_shell() splices the flash banner in directly below page_header()'s title, and FLASH_SLOT_MARKER never reaches the rendered document | ported | companion/test_companion_app_01.py::test_flash_banner_spliced_below_page_header_marker_never_leaks |
| 26 | page_shell() still renders the flash banner in its original slot for a body with no FLASH_SLOT_MARKER (the pre-page_header() fallback path) | ported | companion/test_companion_app_01.py::test_flash_banner_fallback_slot_when_body_has_no_marker |
| 27 | an anomaly banner (banner=) is unaffected by the flash-slot move and still renders in its existing pre-body slot | ported | companion/test_companion_app_01.py::test_anomaly_banner_unaffected_by_the_flash_slot_move |
| 28 | page_shell() reflects the supplied UI theme; ui_theme_from_cookie() falls back to auto | ported | companion/test_companion_app_01.py::test_theme_resolution |
| 29 | status_dot() encodes the state as a fixed class, escapes the label, falls back to warn | ported | companion/test_companion_app_01.py::test_status_dot_states |
| 30 | data_table() escapes every header/cell and emits the empty-state block for zero rows | ported | companion/test_companion_app_01.py::test_data_table_escapes_and_empty_state |
| 31 | data_table() wraps its <table> in a horizontally-scrollable container | ported | companion/test_companion_app_01.py::test_data_table_wrapped_for_horizontal_scroll |
| 32 | sidebar_nav() renders every NAV_TABS link with exactly one active | ported | companion/test_companion_app_01.py::test_sidebar_nav_renders_all_tabs_with_one_active |
| 33 | sidebar_nav() matches no tab and stays script-free for a hostile active value | ported | companion/test_companion_app_01.py::test_sidebar_nav_escapes_hostile_active |
| 34 | layout.NAV_TABS holds exactly 6 entries, in order home/display/flights/airlines/health/device | ported | companion/test_companion_app_01.py::test_nav_tabs_shrunk_to_four_settled_order |
| 35 | a rendered authenticated page contains exactly six sidebar nav links and exactly six tab-bar links, with exactly one marked active in each, and the hamburger dropdown holds zero destination links (retargeted from the dropdown onto the tab bar, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_01.py::test_sidebar_and_tab_bar_render_exactly_six_links_one_active_each |
| 36 | the eye glyph (icon-nav-preview) is still a whitelist member and icon_html() returns non-empty markup for it, even though its nav-slug mapping was removed | ported | companion/test_companion_app_01.py::test_eye_glyph_survives_nav_shrink |
| 37 | stat_tile() maps status to a fixed class with an accent fallback, escapes the caption, and passes content_html through unmodified | ported | companion/test_companion_app_01.py::test_stat_tile_status_classes_caption_escape_and_content_passthrough |
| 38 | card_status_class() maps status to base_class + a fixed suffix for the three whitelisted states, and falls back to the empty string (not an accent class) for None or an unrecognised status — the divergence from stat_tile()'s own fallback (quick task 260902-gjj, ISSUE 2) | ported | companion/test_companion_app_01.py::test_card_status_class_whitelist_and_empty_fallback |
| 39 | page_shell() wraps header+sidebar+main in .dashboard-shell with both nav landmarks (sidebar + tab bar, and exactly one when there is no tab bar) and both theme-form copies present | ported | companion/test_companion_app_01.py::test_page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme |
| 40 | page_shell()'s skip link target carries tabindex="-1" so it actually receives focus | ported | companion/test_companion_app_01.py::test_page_shell_skip_link_target_is_focusable |
| 41 | page_shell()'s output contains no unescaped script tag for an escaped hostile body | ported | companion/test_companion_app_01.py::test_page_shell_escapes_hostile_body |
| 42 | layout.ICON_IDS has exactly twenty-three unique members, each a symbol id in ICON_DEFS_HTML and vice versa | ported | companion/test_companion_app_01.py::test_icon_sprite_integrity |
| 43 | icon_html() returns markup for every whitelisted id and '' for an unknown/empty/None/hostile id | ported | companion/test_companion_app_01.py::test_icon_html_whitelist_enforcement |
| 44 | stat_tile() is byte-identical with icon omitted and places a valid icon before the caption text | ported | companion/test_companion_app_01.py::test_stat_tile_backcompat_and_icon_slot |
| 45 | page_shell() emits exactly one sprite (one <defs, twenty-three <symbol) before dashboard-shell, no inline styles | ported | companion/test_companion_app_01.py::test_page_shell_emits_sprite_once_no_inline_styles |
| 46 | the icon/icon-defs/STAT_TILE_ICON_CLASS class names all appear in companion/static/style.css | ported | companion/test_companion_app_01.py::test_icon_classes_styled_in_served_stylesheet |
| 47 | every heading role (h1/h2/h3/legend/.text-heading) shares one serif rule except the one named, asserted nested card-title sans exception (D-09), and `legend` does not override its weight | ported | companion/test_companion_app_01.py::test_heading_roles_share_one_serif_rule_with_named_nested_exception |
| 48 | --font-serif never reaches table, body, mono, nav-link or stat-tile-caption rules (D-03's headings-only boundary; D-13 retired the caption's own former serif exception) | ported | companion/test_companion_app_01.py::test_serif_never_reaches_dense_or_tabular_content |
| 49 | mobile dropdown nav link keeps its restored 44px/Body-size tap target while the desktop sidebar link stays at its D-05 32px/Label-size compaction (260902-qkm) | ported | companion/test_companion_app_01.py::test_mobile_nav_link_and_sidebar_link_geometries_stay_diverged |
| 50 | there is exactly one error-signal colour token (--color-status-error), no --color-destructive duplicate | ported | companion/test_companion_app_01.py::test_exactly_one_error_signal_colour_token |
| 51 | the Health notification dot appears inside the Health sidebar link and on the tab bar's More summary — one per nav renderer — when health_alert='error', nowhere when None/omitted, and never on another link (retargeted from the dropdown, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_health_nav_notification_dot_appears_in_sidebar_and_tab_bar |
| 52 | input.visually-hidden/select.visually-hidden clears the 44px touch-target floor off hidden form controls, and the global input/select rule still declares both 44px minimums for every other field | ported | companion/test_companion_app_02.py::test_hidden_form_control_floor_and_global_floor_both_survive |
| 53 | layout.page_shell(..., health_alert='warn') also renders the notification dot, using dot--warn rather than dot--error | ported | companion/test_companion_app_02.py::test_health_nav_notification_dot_warn_severity |
| 54 | nav-dropdown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/XHR/timers/innerHTML/document.write/eval) — standing constraints on the file | ported | companion/test_companion_app_02.py::test_nav_dropdown_script_es5_safe_and_side_effect_free |
| 55 | the hamburger toggle carries type=button/id/aria-expanded=false/aria-controls and the fixed accessible label (never a close-verb variant), and the panel never renders open | ported | companion/test_companion_app_02.py::test_toggle_aria_contract_and_fixed_label |
| 56 | the dropdown panel holds the state reminder, then the language and theme switches and Sign out, in that order — and zero destination links (retargeted in place from the retired six-link menu, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_dropdown_contents_and_order |
| 57 | companion.app.NAV_SCRIPT_ROUTE, layout's nav DOM-contract literals, nav-dropdown.js and style.css all agree with each other and with a rendered document | ported | companion/test_companion_app_02.py::test_three_file_nav_dom_contract_guard |
| 58 | with JavaScript disabled the dropdown panel stays unclipped in the DOM (the collapsed look is a CSS max-height constraint, not a hidden attribute or display:none), every nav link stays reachable in the tab bar with its Advanced group behind a native <details> needing no script, and the server-rendered <html> tag carries no .js marker class (retargeted onto the tab bar, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_dropdown_survives_with_javascript_disabled |
| 59 | nav-dropdown.js adds the .js marker class before its dropdown element lookup and implements the hidden-attribute/transitionend/reduced-motion state machine, matched by style.css's .js-scoped clipping rules | ported | companion/test_companion_app_02.py::test_nav_dropdown_js_progressive_enhancement_state_machine |
| 60 | the bottom tab bar renders five cells fed by the ONE shared _nav_links() iteration — its destinations equal the sidebar's in NAV_TABS order, the four everyday routes are tab links and the Advanced group is a native <details> sheet, exactly one aria-current="page" sits on the real link (never on the <summary>), the More summary wears the active pill on an Advanced page, it carries the shared Primary-navigation landmark name, and the whole bar carries no script hook (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_companion_app_02.py::test_tab_bar_is_five_cells_from_the_one_shared_nav_iteration |
| 61 | the tab bar renders from the authenticated shell only and only with a device config — never on the login shell, never on the 404 — and the <body> clearance marker appears exactly when the bar does (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_companion_app_02.py::test_tab_bar_is_absent_from_the_login_shell_and_the_404 |
| 62 | parse_single_uploaded_file() returns the payload for a well-formed single-part body, even when the part header declares a traversal-shaped filename (never read) | ported | companion/test_companion_app_02.py::test_parser_happy_path_ignores_traversal_filename |
| 63 | parse_single_uploaded_file() returns None for a two-part body — this route accepts exactly one file part and nothing else | ported | companion/test_companion_app_02.py::test_parser_two_parts_returns_none |
| 64 | parse_single_uploaded_file() returns None for a non-multipart media type | ported | companion/test_companion_app_02.py::test_parser_urlencoded_media_type_returns_none |
| 65 | parse_single_uploaded_file() returns None when the boundary parameter is missing | ported | companion/test_companion_app_02.py::test_parser_missing_boundary_returns_none |
| 66 | parse_single_uploaded_file() returns None for an empty body | ported | companion/test_companion_app_02.py::test_parser_empty_body_returns_none |
| 67 | parse_single_uploaded_file() returns None when the part has no header/body separator | ported | companion/test_companion_app_02.py::test_parser_missing_header_body_separator_returns_none |
| 68 | parse_single_uploaded_file() returns None for a None content_type | ported | companion/test_companion_app_02.py::test_parser_none_content_type_returns_none |
| 69 | parse_single_uploaded_file() returns None for an empty file part payload | ported | companion/test_companion_app_02.py::test_parser_empty_payload_returns_none |
| 70 | env_wake_interval_default() covers its whole input space (unset, empty, non-numeric, whitespace-padded, in-range and out-of-range including deploy/skypane.env.example's shipped below-floor SKYPANE_SLEEP_S=30) and never raises | ported | companion/test_companion_app_02.py::test_env_wake_interval_default_full_input_space |
| 71 | page_context() threads wake_interval_env_default from the real environment read: 900 when SKYPANE_SLEEP_S=900, and always present (never conditionally omitted) as None when unset | ported | companion/test_companion_app_02.py::test_page_context_threads_wake_interval_env_default |
| 72 | preview_png_bytes() returns a 320x120 PNG for every id in device_config.THEME_IDS | ported | companion/test_companion_app_02.py::test_theme_preview_bytes_open_as_320x120_rgb_png_for_every_theme |
| 73 | the 18 themes' previews have pairwise-distinct mean RGB at the crop/size used (proves the crop box discriminates themes, D-07) | ported | companion/test_companion_app_02.py::test_theme_preview_means_pairwise_distinct |
| 74 | THEME_PREVIEW_CROP_BOX keeps THEME_PREVIEW_SIZE's exact 8:3 ratio and cuts no ink band at either edge - every caption glyph is outside it and the main illustration band is inside it whole, measured against a real render (B6, 22-10-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_theme_preview_crop_keeps_8_3_and_excludes_every_caption_glyph |
| 75 | preview_png_bytes() returns byte-identical output across two calls for the same theme (the scene is fixed, D-06 — nothing time- or data-dependent leaks in) | ported | companion/test_companion_app_02.py::test_theme_preview_bytes_stable_across_calls |
| 76 | cache_path() returns None for a traversal-shaped id, an unknown id, and a falsy state_dir (boundary guard, T-v26-01-01 discipline) | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_rejects_unsafe_and_falsy_inputs |
| 77 | cached_preview_bytes() on a cold state dir creates the cache file and returns the same bytes preview_png_bytes() would | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_cold_cache_creates_file |
| 78 | a second cached_preview_bytes() call for the same theme is served from the file on disk, not re-rendered | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_second_call_serves_from_disk |
| 79 | preview_signature() changes when THEME_PREVIEW_CACHE_VERSION changes (the manual escape hatch for a render-geometry change the signature can't otherwise see) | ported | companion/test_companion_app_02.py::test_theme_preview_signature_changes_with_cache_version |
| 80 | cache_path() with no event returns a stable, deterministic filename that differs from the same theme's live-event filename (which contains the event id) — the existing 2-argument call site (the chip grid) keeps working unmodified, D-23 | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_no_event_is_stable_and_distinct_from_live |
| 81 | cache_path() gives two different event ids two different paths, and the same event id twice the same path (D-23/Pitfall 7) | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_distinct_event_ids_distinct_paths |
| 82 | cache_path() degrades a non-integer or hostile event id to the same sample path as no event at all, never reaching the filename (T-20-14) | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_hostile_event_id_degrades_to_sample |
| 83 | preview_png_bytes(theme_id, live_event=row) returns a well-formed PNG for a full runway_events row and for a row missing half its fields (partial rows never raise, D-23) | ported | companion/test_companion_app_02.py::test_theme_preview_png_bytes_live_event_full_and_partial_row |
| 84 | cached_preview_bytes() with no live_event still creates the cache file and returns exactly what preview_png_bytes(theme_id) returns, unchanged by this task (D-23) | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_no_event_unchanged |
| 85 | cached_preview_bytes() keys its cache on the live event's row id: a repeat request for the SAME event serves the on-disk file unchanged (no re-render), and a NEWER event is a cache miss rather than the stale first render (D-23/Pitfall 7) | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_live_event_keyed_by_id |
| 86 | _illustration_filenames() is the per-request union of the static target set and server-persisted manual keys: None and an empty state dir both equal the static set exactly, a seeded manual entry adds exactly one filename, and an entry whose stored name yields no usable key contributes nothing (D-09) | ported | companion/test_companion_app_02.py::test_illustration_filenames_union_contract |
| 87 | every FLASH_KEY_MANUAL_* constant is a FLASH_MESSAGES/FLASH_ROLES key; the six UI-SPEC deck strings resolve byte for byte through _resolve_flash_text(), an unknown key still resolves to None, and no FLASH_MESSAGES value carries a runtime placeholder except the cooldown, rule_replaced, calendar_connected and calendar_connect_ok keys (Phase 15 D-10 widened this in place, not loosened; Phase 17 plan 04 and 20-09-PLAN.md Task 2 each widen it again for the same reason) | ported | companion/test_companion_app_02.py::test_flash_manual_keys_complete_and_byte_identical |
| 88 | page_context() on a request carrying ?resolve=XYZ returns that raw value under resolve_prefix and a dict under manual_resolutions reflecting a seeded entry; every key companion/pages/__init__.py documents is actually present in ctx | ported | companion/test_companion_app_02.py::test_page_context_supplies_resolve_prefix_and_manual_resolutions |
| 89 | the battery millivolt constants are defined in exactly one companion module (companion/battery.py) plus server/poll_loop.py's documented private copy, no other module defines a second battery_percent()/battery_fraction(), and no module outside those two names either endpoint pair together — the legacy linear 4200/3300 pair or the SEED-006 curve's own 4112/2946 pair — with comments and docstrings stripped first, so the prose that explains the rule can neither satisfy nor break it (CFG-39, T-24-03, quick 260923-gaf) | deleted | S: asserted source text via a tokenize scan across every companion/server *.py file for a duplicate battery constant/function definition (banned, guard G2); the real failure mode this guards against — the two homes disagreeing about a percentage for the same reading — is covered behaviourally by row 91 (test_battery_estimate_parity_between_companion_and_server) |
| 90 | companion.battery.BATTERY_DISCHARGE_CURVE is strictly increasing in both columns, runs 0..100, every knot round-trips through battery_percent(), the end-knot clamps are exact, the SEED-006 anchor values hold, NaN is refused, and LOW_BATTERY_DISPLAY_MV is 3540 and sits strictly between the sparkline's fixed range and above BATTERY_LOW_THRESHOLD_MV (SEED-006, quick 260923-gaf) | ported | companion/test_companion_app_02.py::test_battery_discharge_curve_is_well_formed |
| 91 | companion.battery and server.poll_loop's independently-maintained battery-percentage copies (D-27) agree on their curve table, their FULL/EMPTY endpoints, and their output for every integer millivolt value from 2800 to 4400, a few non-integer floats, and a hostile input set — a drift here is exactly T-gaf-02 (SEED-006, quick 260923-gaf) | ported | companion/test_companion_app_02.py::test_battery_estimate_parity_between_companion_and_server |
| 92 | no string literal in companion/draw.py or any companion/pages/*.py module carries a colour value into emitted SVG markup — docstrings excluded, so a paragraph explaining the rule cannot break the scan (CFG-39 contract rule 3) | ported | companion/test_companion_app_02.py::test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route |
| 93 | every <rect>/<circle>/<line>/<path>/<polygon>/<polyline>/<ellipse> emitted by companion/draw.py or a page module carries a class attribute or an explicit fill/stroke — a shape with neither paints SVG-default black and is invisible in one of the two themes (CFG-39 contract rule 4) | ported | companion/test_companion_app_02.py::test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route |
| 94 | every class name companion/draw.py can emit (DRAWING_CLASSES, its own constants) resolves to at least one selector in companion/static/style.css, matched on a selector boundary so `.drawing-axis` is not reported as resolved by `.drawing-axis-label` (CFG-39) | ported | companion/test_companion_app_02.py::test_every_drawing_class_resolves_in_the_served_stylesheet |
| 95 | companion/draw.py imports no page module, nothing from the server package and not companion/layout.py — read off the module's abstract syntax tree, which carries no comment and no docstring at all, so the paragraph stating the rule cannot satisfy it and a dotted module name survives intact (CFG-39) | ported | companion/test_companion_app_02.py::test_draw_module_imports_no_page_and_no_server |
| 96 | every companion/draw.py emitter returns complete markup with no script tag, no external reference and no inline style, and refuses an attribute carrying one — the no-JS floor (D-09) is why this phase server-renders its SVG | ported | companion/test_companion_app_02.py::test_draw_module_emits_no_script_and_no_external_reference |
| 97 | companion/draw.py escapes every interpolated value through its one escape() helper — all five dangerous characters, in element content and in attribute values alike, with no 'this value is always safe' exception (T-24-01) | ported | companion/test_companion_app_02.py::test_draw_module_escapes_every_interpolated_value |
| 98 | companion/draw.py's scales clamp into their caller-supplied FIXED domain and pin at exactly the floor and ceiling positions, usable_pairs() drops a row's label with the row itself, and no helper raises on None/a bool/a negative/a string/a NaN (T-24-04, D-04/A-22) | ported | companion/test_companion_app_02.py::test_draw_module_scales_clamp_and_never_raise |
| 99 | draw.ring_gauge() is ONE size-parameterised emitter whose size moves the radius AND the stroke width (never a CSS-only small variant), draws no value arc at all at 0 and a complete dash-free circle at 1, draws half its own emitted circumference at 0.5, gives every arc an explicit fill route and a class with no colour literal, carries a viewBox plus intrinsic width/height and aria-hidden, and never raises (CFG-40, T-24-04-A) | ported | companion/test_companion_app_02.py::test_ring_gauge_is_one_emitter_whose_size_drives_the_geometry |
| 100 | unauthenticated GET / redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[home] |
| 101 | unauthenticated GET /display redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[display] |
| 102 | unauthenticated GET /flights redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[flights] |
| 103 | unauthenticated GET /airlines redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[airlines] |
| 104 | unauthenticated GET /health redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[health] |
| 105 | unauthenticated GET /device redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[device] |
| 106 | unauthenticated GET /settings (a retired page route) redirects to /login without ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_retired_page_route_redirects_to_login_without_next[settings] |
| 107 | unauthenticated GET /history (a retired page route) redirects to /login without ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_retired_page_route_redirects_to_login_without_next[history] |
| 108 | unauthenticated GET /preview (the retired Preview page's redirect source) redirects to /login without page content (D-22 removed it from NAV_TABS, so no ?next= is carried — it lands on /login, not /history, proving the redirect branch keeps its own session gate) | ported | companion/test_companion_app_02.py::test_unauth_get_preview_redirects_to_login_without_next |
| 109 | unauthenticated GET /preview.png now returns 404 (not a 303 to /login) — the route's session-gated branch is gone, so the request falls through to do_GET's deliberately ungated unknown-path handler | ported | companion/test_companion_app_02.py::test_preview_png_unauth_404_not_login_redirect |
| 110 | unauthenticated GET of a gallery image route redirects to /login without page content (not a NAV_TABS route, so no ?next= is carried) | ported | companion/test_companion_app_02.py::test_unauth_get_gallery_image_redirects_to_login_without_next |
| 111 | unauthenticated POST /settings redirects to /login (the write route is not a tab, so no ?next=) | ported | companion/test_companion_app_02.py::test_unauth_post_settings_redirects_to_login_without_next |
| 112 | unauthenticated POST /poll-now redirects to /login without page content (not a NAV_TABS route, so no ?next= is carried) | ported | companion/test_companion_app_02.py::test_unauth_post_poll_now_redirects_to_login_without_next |
| 113 | GET /static/style.css succeeds without a session, returns a CSS content type, and stays shared-cacheable (public, max-age=300) — this route is a deliberate D-02 gate exemption with no per-user content | ported | companion/test_companion_app_02.py::test_stylesheet_public |
| 114 | GET /static/battery-trend.js succeeds without a session and returns a JavaScript content type | ported | companion/test_companion_app_02.py::test_battery_trend_script_public |
| 115 | GET /static/nav-dropdown.js succeeds without a session, returns a JavaScript content type, and serves the real file | ported | companion/test_companion_app_02.py::test_nav_dropdown_script_public |
| 116 | GET /static/dirty-state.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[dirty-state.js] |
| 117 | GET /static/list-filter.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[list-filter.js] |
| 118 | GET /static/copy-button.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[copy-button.js] |
| 119 | GET /static/freshness.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[freshness.js] |
| 120 | companion.app.py's 4 new *_SCRIPT_ROUTE constants equal companion/layout.py's 4 new *_SCRIPT_SRC constants, and page_shell() emits a <script> tag for each | ported | companion/test_companion_app_02.py::test_four_new_static_routes_dom_contract_guard |
| 121 | copy-button.js stays ES5-safe (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), reads its on-success feedback text from each button's own data-copied-text attribute, and the removed hardcoded "Copied" literal survives only as the one documented fallback (D-06) | ported | companion/test_companion_app_02.py::test_copy_button_script_es5_safe_reads_data_copied_text |
| 122 | dirty-state.js stays ES5-safe (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/XHR), contains NO fetch( any more, reads all seven of the bar's own data-dirty-* attributes, and each restored hardcoded literal survives only as its own documented fallback (CFG-77/CFG-78, 28-08-PLAN.md Task 3) | ported | companion/test_companion_app_02.py::test_dirty_state_script_es5_safe_reads_seven_dirty_bar_attributes |
| 123 | dirty-state.js animates the restored bar's own count element and never its word: exactly one text write site, gated on the text having genuinely changed, written before the class is added, spending the stylesheet's existing .is-fading-in rule through a remove/reflow/re-add with no interval/rAF anywhere — so the role="status" bar announces each change once and never a partial word (CFG-77/CFG-78, 28-08-PLAN.md Task 3; retargets 27-04-PLAN.md Task 2's own status-region version back onto the count element, restoring 23-09-PLAN.md Task 1/D3/CFG-32's original subject) | ported | companion/test_companion_app_03.py::test_dirty_state_animates_the_bars_own_count_element_and_never_its_word |
| 124 | freshness.js stays ES5-safe and keeps the standing HTML-writing-sink ban (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/location.reload/XHR), while fetch(/setTimeout/setInterval are its own single, deliberate, reviewed exception to the sibling scripts' ban list (D-02) — and it actually uses the safe DOMParser/replaceChild/credentials-scoped mechanism this exception was granted for, not merely permitted to | ported | companion/test_companion_app_03.py::test_freshness_script_es5_safe_with_one_reviewed_sink_exception |
| 125 | freshness.js contains no URL-taking navigation form (an assignment to location.href, or a call to location.assign/location.replace/window.open) while still reading window.location.href as its fetch argument — the fetch target can never be influenced by injected markup (19-09-PLAN.md Task 3, D-02/T-19-33) | ported | companion/test_companion_app_03.py::test_freshness_script_no_url_taking_navigation_form |
| 126 | GET /static/panel-lookup.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_panel_lookup_script_public |
| 127 | panel-lookup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/XHR/timers/innerHTML/document.write/eval), and never decides whether to open the dialog from viewport dimensions or device orientation (no matchMedia/innerWidth) — that gate is CSS-only, on the Airlines trigger's own rule (quick task 260902-tli) | ported | companion/test_companion_app_03.py::test_panel_lookup_script_es5_safe_and_no_html_write |
| 128 | panel-lookup.js's drop handling names NO canvas API and no object URL, assigns the dropped file to the form's own <input type="file"> through exactly one `new DataTransfer()` (so dropped and picked bytes travel one path, with one size cap and one parser), routes BOTH the drop and the picker through exactly one shared uploadRefusal() called exactly twice, consults it BEFORE assigning, and refuses an untrusted drop event (CFG-51/D19, 25-07-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_panel_lookup_drop_handling_writes_the_forms_own_input_and_no_canvas |
| 129 | the mandatory three-element guard appears exactly once and never mentions the optional replace-form lookup on its own line, that lookup's first occurrence in the source comes after the guard's, it appears exactly once, and the action-attribute setAttribute write appears exactly 3 times (replace/resolve-upload/delete, phase 14 plan 14-05) — pinning the single line that keeps History's lightbox alive (quick task 260903-btu) | ported | companion/test_companion_app_03.py::test_panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard |
| 130 | layout.PANEL_LOOKUP_SCRIPT_SRC equals companion.app.PANEL_LOOKUP_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_panel_lookup_script_route_src_agree |
| 131 | GET /static/flash-cleanup.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_flash_cleanup_script_public |
| 132 | flash-cleanup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/XHR/timers/innerHTML/document.write/eval), and uses history.replaceState with location.search/location.pathname to strip a consumed ?flash= param (quick task 260903-peo, UIR-19) | ported | companion/test_companion_app_03.py::test_flash_cleanup_script_es5_safe_and_no_html_write |
| 133 | layout.FLASH_CLEANUP_SCRIPT_SRC equals companion.app.FLASH_CLEANUP_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_flash_cleanup_script_route_src_agree |
| 134 | GET /static/poll-cooldown.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_poll_cooldown_script_public |
| 135 | poll-cooldown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), and carries both the D-01 countdown (textContent/removeAttribute/setInterval/clearInterval) and the UXA-15 disable-on-submit affordance (addEventListener) | ported | companion/test_companion_app_03.py::test_poll_cooldown_script_es5_safe_and_no_html_write |
| 136 | layout.POLL_COOLDOWN_SCRIPT_SRC equals companion.app.POLL_COOLDOWN_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_poll_cooldown_script_route_src_agree |
| 137 | GET /static/confirm-submit.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_confirm_submit_script_public |
| 138 | confirm-submit.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/location.assign/location.replace), and carries the native confirm() step (addEventListener/preventDefault/confirm() all present) (D-08/A-26) | ported | companion/test_companion_app_03.py::test_confirm_submit_script_es5_safe_and_no_html_write |
| 139 | layout.CONFIRM_SUBMIT_SCRIPT_SRC equals companion.app.CONFIRM_SUBMIT_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_confirm_submit_script_route_src_agree |
| 140 | GET /static/theme-preview.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_theme_preview_script_public |
| 141 | theme-preview.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/timers/a page-wide single-grid lookup), and carries the row->chip src-swap contract (addEventListener/querySelector/getAttribute/data-preview-src/data-usage all present) (D-08/D-12/R-11, extended by 21-05-PLAN.md Task 3 from D-22..D-24's own original single-grid version) | ported | companion/test_companion_app_03.py::test_theme_preview_script_es5_safe_and_no_html_write |
| 142 | layout.THEME_PREVIEW_SCRIPT_SRC equals companion.app.THEME_PREVIEW_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_theme_preview_script_route_src_agree |
| 143 | a rendered authenticated page contains exactly one theme-preview.js <script> tag and no inline <script> without a src (D-32) | ported | companion/test_companion_app_03.py::test_theme_preview_script_tag_exactly_once_and_no_bare_inline_script |
| 144 | GET /static/flight-rows.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_flight_rows_script_public |
| 145 | flight-rows.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/timers), and carries the detail-row toggle contract (addEventListener/querySelectorAll/data-row-toggle/flight-detail-row--collapsed/aria-expanded/aria-controls all present) (D-15/R-12) | ported | companion/test_companion_app_03.py::test_flight_rows_script_es5_safe_and_no_html_write |
| 146 | layout.FLIGHT_ROWS_SCRIPT_SRC equals companion.app.FLIGHT_ROWS_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_flight_rows_script_route_src_agree |
| 147 | a rendered authenticated page contains exactly one flight-rows.js <script> tag and no inline <script> without a src (D-15/R-12) | ported | companion/test_companion_app_03.py::test_flight_rows_script_tag_exactly_once_and_no_bare_inline_script |
| 148 | a real GET of /static/flight-rows.js returns 200 with data-row-toggle and flight-detail-row--collapsed present, and none of innerHTML/document.write/=>/ let / const  (21-03-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_real_get_flight_rows_route_serves_expected_body |
| 149 | a rendered authenticated page contains exactly fifteen deferred <script src= tags before the closing body tag, including panel-lookup.js, flash-cleanup.js, poll-cooldown.js, confirm-submit.js, theme-preview.js, flight-rows.js, submit-guard.js, relative-time.js, quick-switch.js and value-controls.js — and NOT login-card.js, which login_shell() alone emits, nor submit-guard.js/relative-time.js/quick-switch.js/value-controls.js on that login shell, which still emits exactly one (retargeted in place by 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_fifteen_deferred_scripts_before_closing_body |
| 150 | a real GET of /static/submit-guard.js returns 200 with an ES5-safe, sink-free body that delegates a submit listener and disables the submitting control from a ZERO-DELAY TIMER (so the browser has already built the form data set, which is what keeps the named theme/language submit buttons working), stands down when another listener cancelled the submission, skips the control poll-cooldown.js already owns, writes no label at all, reuses the ONE existing button:disabled rule still ordered after button:active, and changes no CSP (T14, 22-15-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_submit_guard_script_serves_shared_disable_on_submit_guard |
| 151 | GET /static/relative-time.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_relative_time_script_public |
| 152 | relative-time.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/setTimeout), carries the ticker contract (setInterval+clearInterval, visibilitychange+document.hidden, textContent, data-relative, querySelectorAll, getAttribute) and no verdict vocabulary at all (D14/CFG-34, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_script_es5_safe_and_no_html_write |
| 153 | layout.RELATIVE_TIME_SCRIPT_SRC equals companion.app.RELATIVE_TIME_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_relative_time_script_route_src_agree |
| 154 | a rendered authenticated page contains exactly one relative-time.js <script> tag and no inline <script> without a src (D-32) | ported | companion/test_companion_app_03.py::test_relative_time_script_tag_exactly_once_and_no_bare_inline_script |
| 155 | a real GET of /static/relative-time.js returns 200 with the served ticker body — the data-relative hook present, the visibility gate present, and none of innerHTML/document.write/=>/ let / const  (23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_real_get_relative_time_route_serves_the_ticker |
| 156 | relative-time.js's BUCKET_BOUNDARIES equals layout._age_bucket()'s own three boundaries, in order, with each number appearing exactly once in the script's code and the array actually read (23-RESEARCH.md Pitfall 4, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_ladder_mirrors_layouts_own_boundaries |
| 157 | every one of relative-time.js's nine wordings, filled with the quantity layout._age_bucket() picks, EQUALS relative_age_text()/relative_future_text()'s own output for every bucket in both languages; the waiting phrase is translated; and every attribute name reaches both the rendered <body> and the script that reads it (D14/CFG-34, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_wordings_equal_the_ladders_own_output |
| 158 | every one of layout.DURATION_ATTRS' four wordings, filled with the quantity layout._age_bucket() picks, EQUALS layout.duration_text()'s own output for every bucket in both languages, and every attribute name reaches value-controls.js (CFG-73 Bug A, 28-03-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_duration_wordings_equal_the_ladders_own_output |
| 159 | layout.relative_time_html(countdown=True) marks the element, keeps the future form while the instant is ahead, reads the translated waiting wording once it has passed — never an age and never a warn/error/alert token — and the default rendering is byte-identical to the element 23-03 shipped (D14/CFG-34, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_html_countdown_keyword_is_marked_and_neutral |
| 160 | GET /static/quick-switch.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_quick_switch_script_public |
| 161 | quick-switch.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/XHR/setInterval and no URL-taking navigation), carries the optimistic-switch contract (aria-checked, preventDefault, stopPropagation, textContent, credentials same-origin, redirect manual, X-Requested-With, encodeURIComponent) and reaches its rollback from BOTH terminal branches through the ES3-safe bracket form (D2/CFG-36, 23-07-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_quick_switch_script_es5_safe_and_no_html_write |
| 162 | layout.QUICK_SWITCH_SCRIPT_SRC equals companion.app.QUICK_SWITCH_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_quick_switch_script_route_src_agree |
| 163 | a rendered authenticated page contains exactly one quick-switch.js <script> tag and no inline <script> without a src (D-32) | ported | companion/test_companion_app_03.py::test_quick_switch_script_tag_exactly_once_and_no_bare_inline_script |
| 164 | a real GET of /static/quick-switch.js returns 200 with the served optimistic-switch body — layout.REFRESH_PENDING_ATTR and layout.QUICK_SWITCH_FAILED_ATTR both named, and none of innerHTML/document.write/=>/ let / const  (23-07-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_real_get_quick_switch_route_serves_the_optimistic_switch |
| 165 | quick-switch.js's PENDING_ATTR, freshness.js's PENDING_ATTR and layout.REFRESH_PENDING_ATTR are the same attribute name — the setter, the skip and the Python that defines it, pinned in one place so a rename on any one side fails rather than silently disabling the D1-races-D2 rule (T-23-26, 23-07-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_quick_switch_pending_marker_is_layouts_own_name |
| 166 | GET /static/value-controls.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_value_controls_script_public |
| 167 | value-controls.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/XHR/fetch/timer and no URL-taking navigation), carries the steering contract (preventDefault, getAttribute, dispatchEvent, aria-valuenow, aria-valuetext, parseFloat and the three Math clamps) and NEVER holds the value — exactly one `.value` assignment, inside the one write helper, reached by exactly two callers (the native input the form posts, and the nameless MIRROR written only from inside paint(), strictly downstream of a read off that field), and at least one read of `field.value` back (CFG-46, 25-01-PLAN.md Task 1; the mirror clause 25-05-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_value_controls_script_es5_safe_and_never_holds_the_value |
| 168 | layout.VALUE_CONTROLS_SCRIPT_SRC equals companion.app.VALUE_CONTROLS_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_value_controls_script_route_src_agree |
| 169 | a rendered authenticated page contains exactly one value-controls.js <script> tag and no inline <script> without a src (D-32, 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_value_controls_script_tag_exactly_once_and_no_bare_inline_script |
| 170 | a real GET of /static/value-controls.js returns 200 with the served steering body — all FIFTEEN of layout's VALUE_CONTROL_* seam attributes named, and none of innerHTML/insertAdjacentHTML/document.write/eval/=>/ let / const /backtick (CFG-46, 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_real_get_value_controls_route_serves_the_registration_seam |
| 171 | value-controls.js wakes the save bar through the ONE public surface — a bubbling event constructed identically in both its branches, whose name is dirty-state.js's own delegated document-level listener, pinned from both sides together with that listener's e.target.form filter, because a control that changes a value without waking the save bar silently loses the user's edit (CFG-46, 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_value_controls_wakes_the_save_bar_through_dirty_states_own_listener |
| 172 | companion/static/style.css's `.js` gate hides by default (`.js-gate { display: none }` — out of the layout AND out of the tab order, never visibility or opacity) and reveals under `.js`, and no gate rule anywhere runs the reverse direction, which flashes a dead control on every load and shows it permanently when a script fails (D-09/CFG-46, 25-01-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_js_gate_hides_by_default_and_reveals_under_js |
| 173 | the shared control vocabulary reuses references/control-density.md's RELOCATED hit-area values VERBATIM from `.copy-btn` (every geometry declaration equal, the same ::before inset, and 44px recomputed from the declared box plus inset rather than restated), `.value-control`/`.value-control__handle` both carry `touch-action: none` so a touch drag is not claimed by the browser's own panning gesture, and not one added rule introduces a colour literal (CFG-46, 25-01-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_control_vocabulary_reuses_the_registered_hit_area_verbatim |
| 174 | companion/static/style.css still carries exactly ONE @supports selector(:has(*)) block, counted on COMMENT-STRIPPED source and on the opening brace — the raw five-line grep counts the four paragraphs that explain the rule (CFG-46, 25-01-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_style_css_carries_exactly_one_has_feature_query_block |
| 175 | companion.battery.battery_life_estimate() is TOTAL over six series shapes (empty, one row, two flat rows, falling, RISING, and a newest row with a None reading) and never states a figure the data cannot support: a charged device's rising slope returns days_remaining=None rather than a negative or infinite lifetime, a flat series returns None, a series at or below the curve's bottom knot floors at zero, a series above the curve's top knot with falling millivolts but no measurable state-of-charge drop reports FALLING with days_remaining=None, the 'no reading' and 'not enough history' states are DIFFERENT named values, the falling series' figure is recomputed in STATE-OF-CHARGE space via battery_fraction() (SEED-006, quick 260923-gaf) rather than by millivolt extrapolation, and the relative cadence factor is available in all six shapes and doubles exactly when the proposed cadence doubles (CFG-49, 25-01-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_battery_life_estimate_is_total_and_never_claims_what_it_cannot |
| 176 | companion/battery.py imports nothing from companion.pages and nothing from the server package — an ast scan of the real module, not its docstring's claim (D-27/CFG-49, 25-01-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_battery_module_imports_neither_a_page_module_nor_the_server_package |
| 177 | every control in _NO_JS_CONTROL_REGISTRY holds its value in a native <input>/<select> the server renders unconditionally, associated with the form that posts it, with EVERY element carrying its wrapper attribute also carrying the .js-gate class — and the machine that judges that is proven non-vacuous against four fixtures built from real group-builder output: one correct control it must accept, and three it must reject (a field name nothing renders, a wrapper rendered outside the gate, and a value held by a div instead of a native input) (CFG-46/D-09, 25-01-PLAN.md Task 4) | ported | companion/test_companion_app_03.py::test_no_js_control_contract_holds_for_every_registered_control |
| 178 | layout.JS_GATE_CLASS resolves to a real selector in companion/static/style.css on a SELECTOR BOUNDARY — the class a page module writes and the rule that hides it pinned as one name, because a rename on either side alone renders a script-only affordance permanently with scripts blocked (CFG-46/D-09, 25-01-PLAN.md Task 4) | ported | companion/test_companion_app_04.py::test_js_gate_class_resolves_to_a_real_selector_on_a_boundary |
| 179 | companion/static/style.css honours the phase's motion budget: every @keyframes name is defined exactly once, every animation reference resolves to a block in the same file, every animation duration comes from a var(--motion-*) token rather than a bare literal, the live prefers-reduced-motion reduce/no-preference block counts equal EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS/EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS, and neither interpolate-size nor calc-size() appears — all measured on COMMENT-STRIPPED source, because this stylesheet's comments quote every token the check counts (D3/CFG-32, 23-01-PLAN.md Task 2) | ported | companion/test_companion_app_04.py::test_style_css_honours_the_motion_budget |
| 180 | GET /static/login-card.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_04.py::test_login_card_script_public |
| 181 | login-card.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), carries the reveal contract (addEventListener/querySelector/getAttribute/data-login-reveal/aria-pressed/the class-at-load modifier) and duplicates no server-side throttling constant (X3, T-22-46/T-22-49) | ported | companion/test_companion_app_04.py::test_login_card_script_es5_safe_and_no_html_write |
| 182 | layout.LOGIN_CARD_SCRIPT_SRC equals companion.app.LOGIN_CARD_SCRIPT_ROUTE | ported | companion/test_companion_app_04.py::test_login_card_script_route_src_agree |
| 183 | a rendered login page contains exactly ONE <script occurrence, the deferred LOGIN_CARD_SCRIPT_SRC tag, with no inline script and no nonce — login_shell() emitted zero script tags before this plan (X3, 22-13-PLAN.md Task 2) | ported | companion/test_companion_app_04.py::test_login_page_emits_exactly_one_script_tag |
| 184 | the server-rendered show-password toggle carries the hidden attribute, type="button", aria-pressed="false", both translated accessible names and .copy-btn's own icon-only geometry — and the field's padding modifier is NOT server-rendered (X3, the no-JS floor by construction) | ported | companion/test_companion_app_04.py::test_login_reveal_toggle_is_server_hidden_and_named |
| 185 | a login POST with the wrong password re-renders the form with the exact copy and sets no cookie | ported | companion/test_companion_app_04.py::test_login_wrong_password |
| 186 | a login POST with the right password sets a cookie with HttpOnly/Secure/SameSite=Strict and redirects to / (Home) | ported | companion/test_companion_app_04.py::test_login_correct_password |
| 187 | an unauthenticated GET /health redirects with ?next=%2Fhealth, and logging in with that next value returns the user to /health, not /settings | ported | companion/test_companion_app_04.py::test_deep_link_return_round_trip |
| 188 | a login POST with the correct password and next='https://evil.example' redirects to the / (Home) fallback, never to the crafted value (T-06.6.2-12) | ported | companion/test_companion_app_04.py::test_open_redirect_rejected[https://evil.example] |
| 189 | a login POST with the correct password and next='//evil.example' redirects to the / (Home) fallback, never to the crafted value (T-06.6.2-12) | ported | companion/test_companion_app_04.py::test_open_redirect_rejected[//evil.example] |
| 190 | GET /login?next=/nonexistent-route (not a real NAV_TABS member) renders the plain login form with no hidden next input | ported | companion/test_companion_app_04.py::test_login_get_with_unrecognised_next_carries_no_hidden_field |
| 191 | GET /login (no session) is rendered by the dedicated login_shell(), not page_shell() — no sidebar/mobile-nav markup, autocomplete present | ported | companion/test_companion_app_04.py::test_login_page_uses_dedicated_login_shell |
| 192 | GET /login with no error renders the stacked card (a .login-form with a .login-form__input and a bare page-title brand mark, no glyph, no sprite) and carries NEITHER aria-invalid NOR aria-describedby — never aria-invalid="false" — with style.css carrying the field/primary/error-border rules it had none of before (X3, 22-13-PLAN.md Task 1) | ported | companion/test_companion_app_04.py::test_login_clean_render_carries_no_error_association |
| 193 | a wrong-password login render carries aria-invalid="true", aria-describedby="login-error" and a role="alert" message in the existing .field-error text-label treatment, rendered between the field and the primary (X3, 22-UI-SPEC.md §5 contract 5) | ported | companion/test_companion_app_04.py::test_login_error_render_is_programmatically_associated |
| 194 | a locked-out login render puts the server-computed lockout sentence in the SAME .field-error text-label role=alert treatment under the field, with aria-describedby but deliberately no aria-invalid (X3, one error voice) | ported | companion/test_companion_app_04.py::test_login_lockout_render_shares_the_one_error_voice |
| 195 | page_shell() and login_shell() both emit lang="en" (D-01/UXA-09 language-policy regression guard) | ported | companion/test_companion_app_04.py::test_both_shells_agree_on_document_language |
| 196 | authenticated GET / returns 200 and contains its own 'Home' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/-Home] |
| 197 | authenticated GET /display returns 200 and contains its own 'Display' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/display-Display] |
| 198 | authenticated GET /flights returns 200 and contains its own 'Flights' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/flights-Flights] |
| 199 | authenticated GET /airlines returns 200 and contains its own 'Airlines' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/airlines-Airlines] |
| 200 | authenticated GET /health returns 200 and contains its own 'Health' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/health-Health] |
| 201 | authenticated GET /device returns 200 and contains its own 'Device' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/device-Device] |
| 202 | authenticated GET /preview (the retired Preview page route) redirects to /flights (D-22, retargeted by phase 18) | ported | companion/test_companion_app_04.py::test_preview_redirects_to_flights |
| 203 | authenticated GET /settings (a pre-phase-18 page route) redirects to /display with a fixed literal target | ported | companion/test_companion_app_04.py::test_legacy_page_route_redirects_with_a_fixed_literal_target[/settings-/display] |
| 204 | authenticated GET /history (a pre-phase-18 page route) redirects to /flights with a fixed literal target | ported | companion/test_companion_app_04.py::test_legacy_page_route_redirects_with_a_fixed_literal_target[/history-/flights] |
| 205 | authenticated GET /preview carrying an arbitrary query string (including a next=-shaped and an https://evil.example-shaped value) still redirects to the identical /flights location — no request value influences the target | ported | companion/test_companion_app_04.py::test_preview_redirect_ignores_query_string |
| 206 | authenticated GET /config (the retired settings path) returns 404 — D-26 declines a redirect since this is a fresh URL at inception, not a deprecated bookmark | ported | companion/test_companion_app_04.py::test_old_settings_path_404s_authenticated |
| 207 | an authenticated POST /settings redirects to /display (the default return page) carrying a flash query | ported | companion/test_companion_app_04.py::test_settings_post_redirects_to_display_with_flash |
| 208 | a POST /settings with a valid theme change and an empty quiet_hours_start returns 200, shows the newly-picked theme still selected, shows the quiet-hours field error, carries no flash banner, and persists nothing on disk (D-07/A-25) | ported | companion/test_companion_app_04.py::test_rejected_settings_save_rerenders_200_with_input_and_error_persists_nothing |
| 209 | authenticated GET / renders the rebuilt Home page (D-01/D-04/D-05) with the Frame strip's two switch forms, three stat-tile elements, the picture/recent-flights row, and the recent-flights list under the grouped Advanced navigation, carrying none of the retired Quick-actions card or Poll form | ported | companion/test_companion_app_04.py::test_home_page_renders_widgets |
| 210 | POST /quick/display with state=off then state=on flips display_enabled on disk and redirects to Display (D-16) with the matching flash; a crafted state value redirects with quick_failed and writes nothing | ported | companion/test_companion_app_04.py::test_quick_display_toggle_round_trip |
| 211 | POST /quick/quiet-hours with state=on then state=off flips quiet_hours_enabled on disk, redirects to Display (D-16) with the matching flash, and never touches display_enabled | ported | companion/test_companion_app_04.py::test_quick_quiet_hours_toggle_round_trip |
| 212 | POST /quick/display honours return_to (/ or /display), falls back to Display for a hostile value (https://evil.example/, //evil.example, /flights) or an absent field, and the invalid-state early return honours return_to too (D-01/R-02) | ported | companion/test_companion_app_04.py::test_quick_display_honours_return_to |
| 213 | POST /quick/quiet-hours honours return_to (/ or /display), falls back to Display for a hostile value (https://evil.example/, //evil.example, /flights) or an absent field, and the invalid-state early return honours return_to too (D-01/R-02) | ported | companion/test_companion_app_04.py::test_quick_quiet_hours_honours_return_to |
| 214 | POST /quick/display and POST /quick/quiet-hours answer a form post with exactly today's 303-and-flash and a request carrying the fetch header with a 204, empty body and no Location — the same write either way, and a crafted state value is never a 204 (D2/CFG-36, T-23-26, 23-07-PLAN.md Task 1) | ported | companion/test_companion_app_04.py::test_quick_routes_answer_204_for_a_fetch_and_303_for_a_form |
| 215 | POST /quick/led stores one explicit led_enabled keyword and carries every other flag forward, redirects to /device with its own flash for a form post, answers 204 with an empty body for a fetch, redirects with the generic failure flash and writes nothing for a crafted state, falls back to /device for every non-member return_to, and is not reachable by GET at all (D2/CFG-36, T-23-23/T-23-24/T-23-25, 23-07-PLAN.md Task 2) | ported | companion/test_companion_app_04.py::test_quick_led_route_saves_redirects_and_negotiates |
| 216 | unauthenticated POST /quick/led redirects to /login without page content | ported | companion/test_companion_app_04.py::test_unauth_post_quick_led_redirects_to_login |
| 217 | unauthenticated POST /quick/display redirects to /login without page content | ported | companion/test_companion_app_04.py::test_unauth_post_quick_display_redirects_to_login |
| 218 | a scoped POST /settings (scope=display / scope=device) persists only its own page's groups, carries the other page's checkbox state forward instead of flipping it off, redirects to the page it came from, and never honours a crafted return_to | ported | companion/test_companion_app_04.py::test_scoped_settings_save_carries_other_page_forward |
| 219 | GET /display and GET /device split the settings groups per companion/screens.py (20-07 moved Runway/Calendar/the rules editor to Display, D-10/D-11), each carrying its hidden scope/return_to fields and the screen-type caption; Manual refresh lives on Device only | ported | companion/test_companion_app_04.py::test_display_and_device_pages_split_the_groups |
| 220 | every HTML response (an authenticated page and the login page alike) carries Cache-Control: no-store, so the back button and shared caches never replay a page after sign-out | ported | companion/test_companion_app_04.py::test_html_pages_are_no_store |
| 221 | an authenticated HTML response carries a Content-Security-Policy header equal (string equality, not substring) to companion.app.CONTENT_SECURITY_POLICY | ported | companion/test_companion_app_04.py::test_authenticated_html_carries_exact_csp |
| 222 | the CSP's script-src directive is 'self' with no 'unsafe-inline' anywhere in it (Task 1 removed the app's last two inline <script> elements, so no exception is needed) | ported | companion/test_companion_app_04.py::test_csp_script_src_strict_no_unsafe_inline |
| 223 | a 303 redirect response (the unauthenticated bounce to /login) carries all four hardening headers, including the CSP — before this plan redirect() sent none of them | ported | companion/test_companion_app_04b.py::test_redirect_carries_four_hardening_headers |
| 224 | the static CSS response (the send_bytes() path) also carries the CSP header | ported | companion/test_companion_app_04b.py::test_static_css_response_carries_csp |
| 225 | POST /ui-theme with no session cookie redirects to /login and does not set a ui_theme cookie (T-19-04: an unauthenticated caller cannot set another visitor's UI theme) | ported | companion/test_companion_app_04b.py::test_ui_theme_post_without_session_redirects_to_login |
| 226 | POST /logout with no session cookie redirects to /login (T-19-04: gating a logout costs a signed-out caller nothing) | ported | companion/test_companion_app_04b.py::test_logout_post_without_session_redirects_to_login |
| 227 | POST /ui-lang with ui_lang=fr/en sets the sp_ui_lang cookie (HttpOnly, SameSite=Strict) and redirects to the referring tab; ui_lang=de sets no cookie | ported | companion/test_companion_app_04b.py::test_ui_lang_post_round_trip |
| 228 | POST /ui-lang with no session cookie redirects to /login and does not set a sp_ui_lang cookie (T-20-01) | ported | companion/test_companion_app_04b.py::test_ui_lang_post_without_session_redirects_to_login |
| 229 | POST /ui-mode with a valid session now takes the unknown-route 404 path (D-17, the route/handler/dispatch line are deleted together) | ported | companion/test_companion_app_04b.py::test_post_to_the_deleted_display_mode_route_with_session_now_404s |
| 230 | a cookie-free GET (session cookie only, no sp_ui_lang) with Accept-Language: fr-FR,fr;q=0.9 renders <html lang="fr"; with Accept-Language: en-GB renders <html lang="en" (D-03) | ported | companion/test_companion_app_04b.py::test_accept_language_resolves_html_lang_with_no_cookie |
| 231 | the sp_ui_lang cookie beats Accept-Language when both are present (D-03) | ported | companion/test_companion_app_04b.py::test_ui_lang_cookie_beats_accept_language |
| 232 | #site-nav-toggle renders icon-gear (never icon-hamburger), its aria-label is NAV_TOGGLE_LABEL translated through i18n's real per-request path in both EN and FR, and the panel it opens still holds the language/theme switches and Sign out with zero page-navigation links (CFG-76) | ported | companion/test_companion_app_04b.py::test_the_nav_toggle_wears_the_gear_and_opens_the_same_panel |
| 233 | authenticated GET /device pre-fills Wake interval with SKYPANE_SLEEP_S=900 when nothing is stored, and a stored wake_interval_s=120 always wins over that environment value | ported | companion/test_companion_app_04b.py::test_wake_interval_env_prefill_and_on_disk_precedence |
| 234 | authenticated GET /device degrades a below-floor SKYPANE_SLEEP_S=30 (the shipped deploy/skypane.env.example value) to the placeholder empty state, never a value attribute the form could not submit | ported | companion/test_companion_app_04b.py::test_wake_interval_below_floor_env_degrades_to_placeholder |
| 235 | GET /login?next=/display (a real NAV_TABS member) renders a hidden next field carrying /display, surviving the round trip | ported | companion/test_companion_app_04b.py::test_login_get_with_settings_next_carries_hidden_field |
| 236 | app.SETTINGS_ROUTE and config_page.SETTINGS_ROUTE agree, NAV_TABS opens with HOME_ROUTE, and NAV_ICON_IDS' keys equal the nav route slugs one-to-one | ported | companion/test_companion_app_04b.py::test_settings_route_and_icon_map_cross_module_contract |
| 237 | the nav tuple, the page-titles dict, and the slug-to-icon map all agree in size and key set, and the settings page module's own route constant is the nav tuple's first route — a standing guard against silent drift when the route set changes again | ported | companion/test_companion_app_04b.py::test_nav_page_titles_icon_route_standing_contract_guard |
| 238 | POST /logout clears the session cookie (Max-Age=0) | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 239 | replaying the exact session cookie after Sign out is rejected (A-33: revoked server-side, not just cleared client-side) | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 240 | GET /logout no longer accepts the request (404) — D-11 closes the GET-triggered logout hole | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 241 | a tab request after logout (no cookie presented) is refused again | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 242 | an unknown path returns 404 with the exact 'Page not found.' copy | ported | companion/test_companion_app_04b.py::test_unknown_path_404 |
| 243 | an authenticated 404 opens with the shared page_header() (page-title, not text-heading) and shows the Health nav dot when state is seeded error | ported | companion/test_companion_app_04b.py::test_authenticated_404_uses_page_header_and_shows_health_dot |
| 244 | an UNAUTHENTICATED 404 renders no health-dot markup under the same seeded error state — the leak guard for the two pre-auth call sites (_serve_stylesheet, _serve_script_file) | ported | companion/test_companion_app_04b.py::test_unauthenticated_404_never_leaks_health_state |
| 245 | authenticated GET /preview.png returns 404 with the exact 'Page not found.' copy even with a real 960,000-byte panel.bin present — the route is gone, not empty | ported | companion/test_companion_app_04b.py::test_preview_png_404_even_with_real_panel |
| 246 | an authenticated gallery image is never advertised as storable by a shared/intermediary cache (WR-02) | ported | companion/test_companion_app_04b.py::test_gallery_response_is_never_shared_cacheable |
| 247 | a gallery request with parent-directory segments returns 404 | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 248 | a gallery request with an absolute path returns 404 | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 249 | a gallery request with a null byte returns 404 | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 250 | the canary file placed one level above the gallery directory never appears in any traversal response | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 251 | an authenticated GET /illustration/air-france.png returns 200, image/png, and a non-empty body | ported | companion/test_companion_app_04b.py::test_illustration_real_key_returns_png |
| 252 | an authenticated GET for an illustration key not in the membership set returns 404 | ported | companion/test_companion_app_04b.py::test_illustration_unknown_key_404 |
| 253 | authenticated GET requests for adversarial illustration paths (path traversal) all return 404 with no file content | ported | companion/test_companion_app_04b.py::test_illustration_traversal_key_404 |
| 254 | an unauthenticated GET /illustration/air-france.png redirects to /login, never returns image bytes | ported | companion/test_companion_app_04b.py::test_illustration_unauthenticated_redirects_to_login |
| 255 | GET /illustration/{key}.png for a manual key: 404 with no registry entry, 404 with an entry but no override file, and 200/image/png once both exist | ported | companion/test_companion_app_04b.py::test_illustration_manual_key_read_path_states |
| 256 | Pitfall 3's warning sign made executable: POST /illustration/{key}.png for a manual key that was never registered returns 404 and writes nothing to the override directory; once the key is registered via add_entry(), the identical POST succeeds | ported | companion/test_companion_app_04b.py::test_illustration_manual_key_post_unregistered_then_registered |
| 257 | an authenticated GET /theme-preview/{id}.png returns 200, image/png, and a real PNG body for every id in device_config.THEME_IDS — no theme is unreachable | ported | companion/test_companion_app_04b.py::test_theme_preview_real_key_returns_png_for_every_theme |
| 258 | an authenticated GET for a theme id not in the membership set returns the same 404 page an unknown runway/illustration id produces | ported | companion/test_companion_app_04b.py::test_theme_preview_unknown_key_404 |
| 259 | authenticated GET requests for adversarial theme-preview paths (path traversal) all return 404 with no file content | ported | companion/test_companion_app_04b.py::test_theme_preview_traversal_key_404 |
| 260 | an unauthenticated GET /theme-preview/white.png redirects to /login, never returns image bytes | ported | companion/test_companion_app_04b.py::test_theme_preview_unauthenticated_redirects_to_login |
| 261 | GET /theme-preview/white.png?live=1 with no runway_events row at all still returns 200/image/png (the sample-scene fallback, D-23) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 262 | GET /theme-preview/white.png?live=1 with a seeded runway_events row returns 200/image/png, and a second request for the same latest event is served from the cache without growing the cache directory (D-23/Pitfall 7) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 263 | inserting a NEWER runway_events row changes both the served live-preview bytes and the cache file it comes from — a newer flight is a cache miss, never a stale hit served forever (D-23/Pitfall 7) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 264 | GET /theme-preview/nope.png?live=1 returns the same 404 an unknown theme id always returns — the membership test still runs before any query is even parsed | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 265 | ?live=0 and a missing ?live query both serve the sample variant, never the live one, even with a runway_events row present (D-23) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 266 | uploading a real PNG over real HTTP to a real companion/app.py subprocess changes what GET /illustration/air-france.png serves, even with a traversal-shaped declared filename in the part header | ported | companion/test_companion_app_04b.py::test_illustration_upload_round_trip_replaces_served_bytes |
| 267 | the overridden air-france render and the vueling-airlines render (the same source image) come out of the identical illustration_normalize pipeline (D-03) | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 268 | the upload was written to {state_dir}/illustration_overrides/air-france.png, and nothing else was created in that directory | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 269 | the vendored server/assets/icons/illustrations/air-france.png file is provably byte-identical (hash, size, and mtime) after a successful upload | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 270 | select_illustration() given the harness's own state_dir resolves Air France to the override the real route just wrote; with no state_dir it still resolves to the vendored file | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 271 | POSTing a non-image payload is rejected with the rejection flash key and writes no override file | ported | companion/test_companion_app_05.py::test_illustration_non_image_upload_is_rejected |
| 272 | POSTing a body over MAX_ILLUSTRATION_UPLOAD_BYTES is rejected, writes no override file, and the drain leaves the service healthy for the next request | ported | companion/test_companion_app_05.py::test_illustration_oversized_upload_is_rejected_and_connection_stays_healthy |
| 273 | POSTing a valid payload to a key outside the membership set, and to three traversal-shaped paths, all 404 and write nothing to the override directory | ported | companion/test_companion_app_05.py::test_illustration_post_unknown_and_traversal_keys_returns_404 |
| 274 | an unauthenticated POST /illustration/tunisair.png redirects to /login and writes no override file | ported | companion/test_companion_app_05.py::test_illustration_unauthenticated_post_redirects_to_login_and_writes_nothing |
| 275 | unauthenticated POSTs to /airlines/resolve and /airlines/manual-resolutions/{prefix}/delete both redirect to /login and write no manual_resolutions.json — the state dir is unchanged, not only the status code | ported | companion/test_companion_app_05.py::test_manual_resolve_and_delete_routes_require_auth_and_write_nothing |
| 276 | POST /airlines/resolve re-validates the prefix against the live unresolved-prefix registry on write (D-11): a well-shaped but unregistered prefix writes nothing and gets the stale flash; the identical POST succeeds once the prefix is a live registry member | ported | companion/test_companion_app_05.py::test_manual_resolve_post_revalidates_prefix_against_live_registry |
| 277 | each add_entry() rejection reaches its own distinct flash key and persists nothing (empty/too-long/reserved names, and the registry cap); the D-03 branch: a brand-new name redirects with resolve= (Step B offered) while a name already covered by existing artwork redirects without it | ported | companion/test_companion_app_05.py::test_manual_resolve_post_rejection_mapping_and_d03_branch |
| 278 | POST /airlines/manual-resolutions/{prefix}/delete removes the registry entry, leaves the override PNG on disk (D-08), and redirects to /airlines with no flash; a second identical POST is a no-op that also redirects without an error flash; a malformed prefix 404s without touching the registry | ported | companion/test_companion_app_05.py::test_manual_resolution_delete_route_full_contract |
| 279 | POST /airlines/resolve redirects with the manual_save_failed flash key (never a dropped connection) when add_entry() cannot write because the state dir is read-only — the exact failure mode CR-01 fixed, exercised end to end (WR-11) - expected the manual_save_failed flash key when add_entry() fails to write, got '/airlines?resolve=FLD&flash=manual_resolved' | ported | companion/test_companion_app_01.py::test_resolve_post_redirects_manual_save_failed_when_state_dir_is_read_only |
| 280 | POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key, leaving the entry in place, when delete_entry() cannot write because the state dir is read-only (WR-11) - expected the manual_delete_failed flash key when delete_entry() fails to write, got '/airlines' | ported | companion/test_companion_app_01.py::test_delete_post_redirects_manual_delete_failed_when_state_dir_is_read_only |
| 281 | unauthenticated POSTs to /settings/rules/add and /settings/rules/{kind}/{value}/delete both redirect to /login and write no colour_rules.json — the state dir is unchanged, not only the status code | ported | companion/test_companion_app_05.py::test_rules_routes_require_auth_and_write_nothing |
| 282 | the rules add form and each delete form sit outside <form id=SETTINGS_FORM_ID> (D-10): neither carries the settings form's id nor a form= attribute pointing at it, and a rule add followed by an unrelated settings-form save leaves both the rule and every device-config setting intact (15-VALIDATION.md row 10) | ported | companion/test_companion_app_05.py::test_rules_add_and_delete_forms_sit_outside_settings_form |
| 283 | raw URL-encoded no-JS POSTs to the rules add route (15-VALIDATION.md row 11): a first add flashes rule_added, a second add for the same key (case-insensitive input) flashes rule_replaced and echoes the normalised key back, and the registry holds exactly one entry with the second theme | ported | companion/test_companion_app_05.py::test_rules_add_route_no_js_added_then_replaced |
| 284 | the rules add route's rejection paths: a malformed value for the selected kind flashes rule_key_invalid and writes nothing; a crafted kind and a crafted theme id each flash the generic rule_save_failed and write nothing; filling the registry to its cap and adding one more flashes rule_registry_full without persisting the at-cap entry | ported | companion/test_companion_app_05.py::test_rules_add_route_rejection_paths |
| 285 | POST /settings/rules/{kind}/{value}/delete removes the registry entry and flashes rule_deleted; a second identical delete of an already-absent entry is a no-op that redirects with no flash; a malformed kind segment and a malformed value segment each 404 without touching an unrelated existing entry | ported | companion/test_companion_app_05.py::test_rules_delete_route_full_contract |
| 286 | a rule written directly to state_dir between two GETs of the Settings page appears in the second render — proving page_context() reads colour_rules fresh per request rather than through any process-scoped cache | ported | companion/test_companion_app_05.py::test_rules_page_context_reads_fresh_per_request |
| 287 | a first poll trigger redirects with the poll_triggered flash key | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 288 | the first poll trigger's run_once() was served by the fake ADS-B providers (adsbfi and adsblol called, no live network) | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 289 | an immediate second poll trigger redirects with the poll_cooldown flash key | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 290 | a fresh second-opener session is refused by the same cooldown (server-global, not per-session) | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 291 | a genuine poll-trigger failure redirects with the distinct poll_failed flash key, never save_failed | ported | companion/test_companion_app_05.py::test_poll_trigger_failure_uses_distinct_flash_key |
| 292 | two genuinely overlapping POST /poll-now requests: exactly one gets the poll_already_running flash key, proving the server-side _POLL_LOCK serializes execution | ported | companion/test_companion_app_05.py::test_poll_now_concurrent_requests_serialize_on_the_lock |
| 293 | saving a calendar feed with three in-window flights performs exactly one refresh call and the rendered banner names the plural flight count (D-06) | ported | companion/test_companion_app_05.py::test_calendar_connect_reports_plural_count |
| 294 | saving a calendar feed with exactly one in-window flight pins the singular form ('1 flight', never '1 flights') | ported | companion/test_companion_app_05.py::test_calendar_connect_reports_singular_count |
| 295 | a syntactically valid feed with nothing in the frame's window reports success with a 0 count, distinguishable from a failure | ported | companion/test_companion_app_05.py::test_calendar_connect_zero_entries_still_succeeds |
| 296 | a failing fetch redirects with the single generic failure flash key, renders the exact failure copy, and the URL is saved regardless (D-06) | ported | companion/test_companion_app_05.py::test_calendar_sync_failure_reports_generic_message_and_still_saves |
| 297 | T-17-FLASH: a raised error whose message embeds the full URL never surfaces the token, path segment, query-parameter name, or whole URL in the Location header or any served response body — the served Settings page legitimately shows the masked host + ellipsis once connected (D-14/R-10, extended by 21-07-PLAN.md Task 2) | ported | companion/test_companion_app_05.py::test_calendar_sync_failure_never_leaks_the_url |
| 298 | checking the disconnect box redirects with the disconnected flash key, and the calendar's previously-fetched flights are actually erased from disk (D-04) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_reports_deletion_and_erases_entries |
| 299 | a bare authenticated POST /settings/calendar/disconnect with no confirm field returns 200 with the confirmation copy and leaves the calendar connected (D-08/A-26) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_bare_post_renders_confirmation_and_touches_nothing |
| 300 | an authenticated POST /settings/calendar/disconnect with confirm=maybe renders the confirmation page rather than disconnecting anything (D-08/A-26) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_confirm_maybe_renders_confirmation_and_touches_nothing |
| 301 | an authenticated POST /settings/calendar/disconnect with confirm=yes 303-redirects with the disconnected flash key and actually disconnects the calendar (D-08/A-26) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_confirm_yes_disconnects |
| 302 | an unauthenticated POST /settings/calendar/disconnect (even with confirm=yes) redirects to /login and writes nothing (D-08/A-26, T-19-41) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_unauthenticated_redirects_to_login |
| 303 | a valid POST /settings/calendar/connect 303-redirects to Display with the calendar_connect_ok flash key, persists the URL, triggers exactly one registry refresh, and leaves quiet_hours_enabled/display_enabled exactly as they were (D-14c, T-20-11 pinned regression) | ported | companion/test_companion_app_05.py::test_calendar_connect_route_valid_url_persists_syncs_once_and_leaves_other_settings_alone |
| 304 | an empty calendar_url on POST /settings/calendar/connect 303-redirects with the calendar_connect_invalid flash key and persists nothing (D-14c) | ported | companion/test_companion_app_05.py::test_calendar_connect_route_invalid_url_rejects_and_persists_nothing |
| 305 | an unauthenticated POST /settings/calendar/connect redirects to /login and writes nothing (D-14c, T-20-10) | ported | companion/test_companion_app_05.py::test_calendar_connect_route_unauthenticated_redirects_to_login |
| 306 | an unauthenticated POST /settings/notifications/test redirects to /login (D-26, T-20-10) | ported | companion/test_companion_app_05.py::test_notifications_test_route_unauthenticated_redirects_to_login |
| 307 | with no stored topic URL, POST /settings/notifications/test redirects with the notifications_test_failed flash key and never calls notify.send_notification() (D-26) | ported | companion/test_companion_app_05.py::test_notifications_test_route_unconfigured_flashes_failure_and_never_calls_sender |
| 308 | with a stored topic URL, POST /settings/notifications/test calls notify.send_notification() exactly once with the stored URL and redirects with the notifications_test_ok flash key (D-26) | ported | companion/test_companion_app_05.py::test_notifications_test_route_configured_calls_sender_once_and_flashes_success |
| 309 | a sender returning False redirects with the notifications_test_failed flash key (D-26) | ported | companion/test_companion_app_05.py::test_notifications_test_route_sender_returning_false_flashes_failure |
| 310 | a POST /settings/notifications/test carrying its own topic_url field is ignored in favour of the stored one — the field is never read from the request body (T-20-13) | ported | companion/test_companion_app_05.py::test_notifications_test_route_ignores_a_submitted_topic_url_field |
| 311 | a save-triggered sync against a calendar with a 60s-old last_attempt_at still fetches and reports success, and refresh_calendar_registry() is called with min_interval_s=0 explicitly - not omitted, which a call-shape spy is the only thing that can actually distinguish here, since config_page.handle_post()'s own save_calendar_url() (17-01) already resets last_attempt_at to None on every set before this handler's own refresh call runs | ported | companion/test_companion_app_05.py::test_calendar_sync_bypasses_the_throttle_via_min_interval_zero |
| 312 | server/poll_loop.py's own refresh_calendar_registry() call shape (no min_interval_s override) still honours the standard throttle against the identical seeded state - the bypass is scoped to the new call site alone | ported | companion/test_companion_app_05.py::test_poll_modules_own_refresh_call_site_still_throttles |
| 313 | a save arriving while the poll lock is already held redirects with the deferred flash key, performs no fetch, and still saves the URL (D-09) | ported | companion/test_companion_app_05.py::test_calendar_sync_lock_contention_is_honest |
| 314 | after a save whose immediate fetch fails, the poll lock is still free - one failure never wedges a later manual poll trigger | ported | companion/test_companion_app_05.py::test_calendar_sync_lock_is_released_after_a_failed_sync |
| 315 | a settings save that changes only the theme, against an already-connected calendar, redirects with the ordinary saved key, performs no fetch, and leaves the calendar and its fetched entries untouched | ported | companion/test_companion_app_05.py::test_unrelated_settings_save_never_reaches_the_refresh_call |
| 316 | a calendar save immediately followed by a manual poll trigger does not hit the poll cooldown - the two mechanisms are independent | ported | companion/test_companion_app_05.py::test_calendar_save_does_not_touch_the_manual_poll_cooldown |
| 317 | no *.py module or *.js static script anywhere under companion/ (test_*.py harnesses excluded) reintroduces any part of the deleted simple/full display-mode switch (D-17) — six modules' worth of removal, pinned by one mechanical scan | ported | companion/test_companion_app_05.py::test_no_companion_module_redefines_the_retired_display_mode_switch |
| 318 | every companion.app.FLASH_MESSAGES template and every _PAGE_TITLES value, plus the 404's and login shell's own <title> literals, round-trip to French under i18n.t_lang(..., 'fr') and to their original English text under i18n.t_lang(..., 'en') | ported | companion/test_companion_app_05.py::test_flash_and_title_strings_round_trip_to_french_and_back |
| 319 | the nav landmark's aria-label ("Primary navigation") and the theme picker's three segment labels ("Auto"/"Light"/"Dark") round-trip to French under i18n.t_lang(..., 'fr') and to their original English text under i18n.t_lang(..., 'en') (D-06/B16) | ported | companion/test_companion_app_05.py::test_nav_and_theme_labels_round_trip_to_french_and_back |
| 320 | the site-wide editorial floor (CFG-79): every non-exempt .section-caption element on all six authenticated routes, in both English and French, over a real running server, is at most 12 whitespace-split words; the route list is proven equal to test_browser_ux.py's own VIEW_TRANSITION_ROUTES; CAPTION_FLOOR_EXEMPTIONS (config_page.ASPECT_CAPTION_EXEMPTIONS, imported not re-listed) is skipped exactly its own length per language across the whole site; per-route and site-wide caption-count minimums guard against a narrowed selector passing vacuously; and the apply-timing sentence (read from frame_state.py's own DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN constants) never renders outside the Frame strip's own markup slice, proven to fire inside it at least once (29-06-PLAN.md Task 3) | ported | companion/test_companion_app_05.py::test_site_wide_editorial_floor_all_six_routes_both_languages |


### Part 01 (plan 33-14)

Rows 1-50 (part 01, original `check()` calls #1-#50) plus the two out-of-order
WR-11 rows (279-280, pulled forward per 33-MIGRATION-RULES.md rubric T) are
`ported` to `companion/test_companion_app_01.py`.

Rubric codes: 46 B (calls `companion.auth`/`companion.layout` directly and
asserts on the return value/HTTP outcome), 4 C (rows 46-49 fetch the served
stylesheet via `served_stylesheet()` and assert on `companion_markup.
css_rules()`/`declarations_for()`/`rules_with_selector()` instead of reading
`companion/static/style.css` from disk; row 50 asserts on `css_rules()`
directly). No deletions in this slice.

New modules: `companion/test_companion_app_01.py` (52 tests: 50 ported checks
plus the 2 WR-11 checks share this same part-01 module rather than a
separate file), `companion/test_companion_app_helpers.py` (calendar-
transport fakes, public-hostname fake, poll-state seeding helper — not yet
consumed by part 01's own tests except the WR-11 pair's seeding helper;
front-loaded for 33-15..33-18's calendar-sync and manual-resolution
sections).

### Part 02 (plan 33-15)

Rows 51-122 (part 02, original `check()` calls #51-#113 by the plan's own
source-line count — the loop-generated route checks each own a distinct
ledger row per iteration, which is why the ledger's own row range is 72
long rather than 63) are `ported` to `companion/test_companion_app_02.py`,
except row 89 which is `deleted`.

Rubric codes: 58 B (calls a production function/module directly, or makes
an HTTP request against a real `companion/app.py` server, and asserts on
the outcome), 3 C (rows 52, 94 fetch the served stylesheet and assert on
`companion_markup.declarations_for()`/`css_rules()`; row 51 also reads the
served stylesheet for two substring checks), 5 J (rows 54, 59 fetch
`nav-dropdown.js` via `served_asset()`; row 57 fetches both `nav-dropdown.js`
and the served stylesheet; rows 121-122 fetch `copy-button.js`/
`dirty-state.js`), 1 S rewritten as a subprocess-import check (row 95:
`companion/draw.py`'s import graph is now proven by importing it fresh in a
child process and asserting on `sys.modules`, per 33-MIGRATION-RULES.md's
own rubric-S technique, instead of `ast.parse()`-ing its source), 2 S
consolidated into one narrower behaviour test (rows 92-93: both point at
`test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route`,
which proves the same two properties — no colour literal, every shape
carries a fill route — over `companion/draw.py`'s own emitter output rather
than scanning every string literal in `companion/draw.py` **and every
`companion/pages/*.py` module** via `tokenize`; the narrower scope is a
deliberate reduction, recorded in this plan's SUMMARY), 1 deletion.

Row 89 (`_battery_estimate_has_exactly_one_home`) is `deleted`: it scanned
every `companion`/`server` `*.py` file's tokens (via `tokenize`, banned by
guard G2) for a second definition of the battery millivolt constants/
percentage functions — a structural anti-duplication guard with no directly
observable HTTP/DOM consequence of its own. The actual failure mode it
exists to prevent — `companion.battery` and `server.poll_loop`'s two
independently-maintained copies disagreeing about a percentage for the same
reading — is fully covered behaviourally by row 91
(`test_battery_estimate_parity_between_companion_and_server`), which this
plan also ports unchanged.

RESEARCH assumption A3 (row 87's flash-deck check): does `_resolve_flash_
text()` ever create a directory for a missing `state_dir`? No — reading
`companion/app.py`'s source directly (not as a test assertion, as part of
this plan's own investigation), the function only ever *reads* `state_dir`
(via `poll_cooldown_remaining()`'s `history_db.open_db()` and `calendar_
rules.load_calendar_registry()`), and only for two OTHER flash keys
(`FLASH_KEY_POLL_COOLDOWN` and `FLASH_KEY_CALENDAR_CONNECTED`/`FLASH_KEY_
CALENDAR_CONNECT_OK`) neither of which the six `FLASH_KEY_MANUAL_*` deck
keys or an unknown key ever reach (the per-key branch returns before either
is called). `companion/test_companion_app_02.py::test_flash_manual_keys_
complete_and_byte_identical` proves this by measurement: it asserts a
`tmp_path` absent subpath still does not exist after every
`_resolve_flash_text()` call in the test.

New module: `companion/test_companion_app_02.py` (70 tests: two of part
02's original 72 ledger rows, 92-93, consolidated into one test; six of the
72 rows are covered by two parametrized tests carrying more than one
original row each — rows 100-105 by `test_unauth_get_nav_tab_redirects_
to_login_with_next` (6 parametrize ids), rows 106-107 by `test_unauth_get_
retired_page_route_redirects_to_login_without_next` (2 ids), and rows
116-119 by `test_static_script_public_and_cacheable` (4 ids)).
`companion/test_companion_app_helpers.py` gains `encode_multipart()` (the
legacy harness's own `_encode_multipart()`, renamed without its leading
underscore — it is still used by several still-legacy checks later in
`companion/test_companion_app.py`, so the ORIGINAL definition stays there
too; this plan's own multipart-parser checks call the shared helpers-module
copy instead).

`companion/test_companion_app.py`'s Section 3 (`companion/app.py`) keeps
three pieces of shared plumbing that sat textually inside this plan's own
slice but are called by name from several still-legacy checks further down
`main()`: the main()-level `import companion.app as app_module`, and the
two closure factories `_unauth_redirects_to_login()`/`_static_script_
public()`. These are explicitly NOT "closures only this plan's checks
used" (33-MIGRATION-RULES.md section 1) and were restored verbatim after
the shrink; see this plan's SUMMARY.

### Part 03 (plan 33-16)

55 rows (123-177), all `ported`. Rubric-code split: 9 B (public-route
checks, layout/app.py route-constant agreements, the pure-Python battery
and countdown-wording checks), 27 J (served-JS ES5-safe/sink-free
contracts and served-body assertions, fetched via `served_asset()` — never
a disk read), 6 D (rendered-page `<script>`-tag-count and DOM-contract
checks, plus the `_NO_JS_CONTROL_REGISTRY` contract, which renders and
parses real markup), 3 C (the `.js` gate, the shared control vocabulary
and the `@supports selector(:has(*))` block count, all read off
`served_stylesheet()` and — except the last — parsed structurally via
`companion_markup.css_rules()`/`declarations_for()`), and 2 S (rewritten
rather than ported as-is; see below). No rows are `deleted`: every
original check's real behaviour survives, once, in the new module.

Two S-rubric rewrites, both because the original check read production
source with a technique guard G2 bans:

- Row 156 (`relative-time.js's BUCKET_BOUNDARIES equals layout.
  _age_bucket()'s own three boundaries...`) used to call `inspect.
  getsource(layout._age_bucket)` and regex the three numeric literals out
  of the returned source text. `test_relative_time_ladder_mirrors_layouts_
  own_boundaries` instead DISCOVERS those same three boundaries
  behaviourally: `_age_bucket_boundaries()` bisects over `layout.
  _age_bucket()`'s own return value (which unit — s/m/h/d — a given input
  maps to), since the function is monotonic. The boundaries are exactly as
  observable this way, and the check never reads a line of Python source.
- Row 176 (`companion/battery.py imports nothing from companion.pages and
  nothing from the server package...`) used `ast.parse()` over `companion/
  battery.py`'s own source and walked the tree for `Import`/`ImportFrom`
  nodes. `test_battery_module_imports_neither_a_page_module_nor_the_
  server_package` instead imports `companion.battery` fresh in a
  subprocess (`child_env()`, `cwd=REPO_ROOT`) and asserts the banned module
  names are absent from `sys.modules` — the exact technique
  33-15-PLAN.md's `test_draw_module_imports_no_page_and_no_server`
  established for the identical shape of check.

One check (row 150, the real GET of `/static/submit-guard.js`) used to
open BOTH `companion/static/style.css` and `companion/app.py` from disk.
The CSS half (button:disabled ordered after button:active) is now read
structurally off `css_rules(served_css)` — a source-order-preserving list,
so "AFTER" is an index comparison rather than a text-offset one. The CSP
half is now a real HTTP response header read (`GET /login`'s own
`Content-Security-Policy` header), additionally cross-checked against
`companion.app.CONTENT_SECURITY_POLICY` — strictly stronger than reading
the Python literal that builds the header, since it proves the header is
actually SENT, not merely defined.

One check (row 174, the `@supports selector(:has(*))` block count) is
kept as a documented exception to "parse structurally": distinguishing a
second, identically-nested feature-query block from the rules already
inside today's one block needs block-POSITION information no
`companion_markup.css_rules()` caller can recover (the parser records
each rule's at-rule PRELUDE TEXT, not where that prelude started in the
file). `test_style_css_carries_exactly_one_has_feature_query_block` keeps
a comment-stripped regex count, but over the SERVED (HTTP-fetched)
stylesheet — never a disk read — per F-01's own sanctioned carve-out for a
property genuinely inexpressible over `css_rules()`/`declarations_for()`.

New module: `companion/test_companion_app_03.py` (55 tests, one per
ledger row — no consolidation and no parametrization in this part).
`companion/test_companion_app_helpers.py` gains `strip_js_line_and_block_
comments()` (the same comment-preserving-strings JS helper `companion/
test_view_pages_helpers.py`/`companion/test_config_page_helpers.py`
already carry for their own chains — used by row 156's boundary-count
check).

`companion/test_companion_app.py` shrunk: `EXPECTED_CHECK_COUNT` 196 ->
141; part 03's 55 checks and their private closures removed from
`main()`. The module-level `_NO_JS_CONTROL_REGISTRY` tuple (and its
documenting comment block) is also removed — it was exclusively read by
this part's own last check, and nothing else in the file or the wider
codebase imports it by name. `_static_script_public()` — textually
adjacent to this part's slice but still called by `/static/login-card.js`'s
own still-legacy check further down `main()` — was confirmed present
(never touched) by re-running `ruff check` on the shrunk file (0 F821
undefined-name errors) before committing.

### Part 04 (plan 33-17)

89 rows (178-266), all `ported`, into two new modules:
`companion/test_companion_app_04.py` (rows 178-222, 45 tests) and
`companion/test_companion_app_04b.py` (rows 223-266, 34 tests — three
stateful/sequential check clusters consolidated into one atomic test
each, see below). Rubric-code split (one dominant code per row, since
several rows mix an HTTP/status assertion with a markup substring):
70 B (HTTP status/header/cookie/on-disk-config assertions — the large
majority: every login POST/GET flow, every NAV_TABS/redirect/settings/
quick-toggle/illustration/theme-preview check that reads a response's
status, headers or `device_config.load_device_config()`), 15 D (rendered-
HTML substring/structure assertions — the login card's markup, the split
Display/Device settings groups, the rebuilt Home page, the D-03 language-
resolution/nav-toggle-gear checks, the two 404 page-header/health-dot
checks), 3 C (`layout.JS_GATE_CLASS`'s selector-boundary check and the
motion budget, both read via `css_rules()`/regex over `served_stylesheet()`
rather than a disk read; the login-page clean-render check's three CSS-
rule-existence assertions, via `rules_with_selector()`), and 1 J
(login-card.js's ES5-safe/sink-free contract, via `served_asset()`). No
rows are `deleted`: every original check's real behaviour survives.

No S-rubric rewrites in this part — no check here used `inspect`/`ast`/
`tokenize` over production source. The one rename named in the plan's own
hotspot section: row 190 (`GET /login?next=/nonexistent-route...`) now
uses `next=/no-such-route` — behaviour unchanged (neither is a real
NAV_TABS member, so both take the "no hidden next field" branch), and the
new module carries no `/nonexistent` literal anywhere, including its own
docstring (`grep -cE "/nonexistent|open\(|tempfile"` on
`test_companion_app_04.py` is 0).

Three stateful/sequential clusters are consolidated (several old checks
map to one new node id, 33-MIGRATION-RULES.md section 3): rows 238-241
(logout clears the cookie; a replayed cookie is rejected; GET /logout
404s; a post-logout tab request with no cookie is refused) all land on
`test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward`,
since running them against the module's shared read-only server would
end that server's one shared session for every other test. Rows 247-250
(three gallery path-traversal payloads plus the canary-never-leaks check)
land on `test_gallery_traversal_and_canary_never_leaks`. Rows 261-265 (the
`?live=1` sample-fallback/cache-reuse/newer-event/unknown-theme/zero-or-
missing-query sequence) land on
`test_theme_preview_live_branch_cache_and_fallback_behaviour`, since each
step's assertion depends on the previous step's own mutation (no
`runway_events` row, then one, then a newer one) — the exact ordering
xdist gives no test the right to assume.

The upload round trip (row 266, the LAST anchor) and the two manual-
resolution-key checks (rows 255-256) each get their own fresh, function-
scoped `make_app_server(fake_providers=True)` server rather than the
module's shared one, per the plan's own hotspot note — they write real
files into `illustration_overrides/`.

`companion/test_companion_app.py` shrunk further: `EXPECTED_CHECK_COUNT`
141 -> 52; part 04's 89 checks, their private closures, and the now-
unused `_theme_cache_dir()` helper are removed from `main()`. The first
of the section's two logins (`session_cookie = _login(harness)`,
originally at the top of the authenticated block) is also removed as
dead code — every check that used to sit between it and the "re-
authenticate" login further down is gone, so nothing reads that first
session any more before the second login overwrites the same variable;
the second login's own comment is updated to say so, since it is now the
section's only login rather than a re-authentication. The illustration-
upload check's own setup (the pre-upload GET, the multipart POST, and
populating `_illustration_pre_upload_render`) stays as bare, un-checked
setup code — confirmed still read directly, by name, by the next still-
legacy check (`_illustration_override_uses_same_normalization_pipeline`,
row 267, 33-18/part 05's own territory) and by three more checks after it
that need the override file the upload just wrote. The stale-pipeline-run
seed and the `gallery/` directory `os.makedirs()` (both migrated-away
rows' own setup) are removed outright — confirmed by grep that no
still-legacy check past row 266 reads either. Re-verified: the shrunk
harness runs 52/52 standalone and through
`companion/test_legacy_harness_shim.py -k companion_app`, and `ruff
check` on the shrunk file is clean (0 F821 undefined-name errors).

### Part 05 (plan 33-18) — chain closed

Rows 267-320 (52 baseline checks, the LAST anchor of the whole
companion_app chain) ported into `companion/test_companion_app_05.py`'s
47 native pytest node ids — 52 `ported`, 0 `deleted`:

- **Illustration override effects (rows 267-270, consolidated into ONE
  node id):** the four checks all read state produced by the SAME real
  upload (never each other's mutations), matching 33-17-SUMMARY.md's own
  consolidation precedent for a fixed-order setup shared across several
  old checks — the normalization-pipeline identity, the exact-one-file
  write, the byte-identical vendored original, and
  `select_illustration()`'s override/vendored resolution.
- **Illustration upload rejection paths (rows 271-274):** non-image
  payload, oversized payload, unknown/traversal keys, unauthenticated
  POST — four independent node ids, each its own fresh
  `make_app_server`.
- **Manual-resolution routes (rows 275-278):** auth gate, live-registry
  revalidation, the four rejection-flash/D-03-branch/cap-fill checks
  consolidated as the legacy `main()` already grouped them, and the
  delete route's full contract.
- **Colour-rules routes (rows 281-286):** auth gate, form placement
  outside `SETTINGS_FORM_ID`, add/replace, the rejection paths plus
  registry cap, delete, and the fresh-per-request read.
- **Poll-trigger cooldown sequence (rows 287-290, consolidated into ONE
  node id):** first trigger + its fake-provider call-log proof,
  immediate cooldown, and a fresh second-opener session refused by the
  same server-global cooldown — the three steps share one mutable
  server in a fixed order, exactly 33-17-SUMMARY.md's own consolidation
  rule.
- **The `--geofence` hotspot (row 291, T-33-18-01):** the poll-trigger
  failure check now passes `make_app_server(extra_args=["--geofence",
  str(tmp_path / "absent" / "no-such-geofence.json")])` instead of the
  legacy literal `/nonexistent/no-such-geofence.json` string — the same
  startup-failure behaviour, no literal host path guard G6 would flag.
- **Concurrent `/poll-now` lock proof (row 292).**
- **Calendar save-triggered sync family (rows 293-316):** every check
  that used to build its own `_InProcessHarness()` now takes
  `companion/conftest.py`'s `app_server_in_process` fixture directly —
  connect/disconnect reporting, the dedicated disconnect/connect routes'
  full auth/confirm contracts, the notifications "send a test" route,
  the throttle-bypass spy, lock contention/release, and the two
  independence proofs (an unrelated save never reaches the refresh call;
  a calendar save never touches the manual poll cooldown). Row 312 (the
  poll_loop-side throttle control) needed no server at all and no longer
  uses `tempfile.TemporaryDirectory()` (guard G6): it takes pytest's own
  `tmp_path` fixture instead.
- **The retired display-mode-switch removal (row 317, rubric S):** the
  legacy check walked every `*.py`/`*.js` file under `companion/` for
  seven retired tokens as raw text. Rewritten as a `not hasattr()`
  battery across every `companion.*` module the removal touched
  (`app`, `auth`, `layout`, `prefs`, and every `companion.pages` module)
  — confirmed by grepping the WHOLE repo before writing the rewrite that
  none of the identifier-shaped tokens (`simple_mode`, `MODE_CHOICES`,
  `DEFAULT_MODE`, `_MODE_CTX`, `UI_MODE_COOKIE_NAME`, `MODE_ROUTE`,
  `sp_ui_mode`) remain anywhere in production code; the two
  non-identifier tokens (the `/ui-mode` route, the `sp_ui_mode` cookie
  name) are behavioural claims already covered by
  `test_companion_app_04b.py`'s own 404/Accept-Language tests, named in
  this test's own docstring.
- **i18n round trips (rows 318-319).**
- **The site-wide editorial floor (row 320, the LAST anchor, rubric S
  for its own cross-file counting-rule check, split into TWO node
  ids):** `test_caption_word_count_text_agrees_with_test_config_page_05s_own_copy`
  proves this module's own `_caption_word_count_text()` duplicate agrees
  with `companion.test_config_page_05`'s own copy across four fixtures,
  by a plain `import companion.test_config_page_05` and calling both
  functions directly — never the legacy check's disk-read + `ast.parse`
  + `ast.get_source_segment()` + `exec()` extraction (guard G2 bans
  `ast`/`tokenize`/`inspect`/`linecache` outright; 33-13-PLAN.md closed
  the config_page chain, and this plan's own sequential-execution brief
  required the cross-check be migrated as calling behaviour, never a
  source read). `test_site_wide_editorial_floor_all_six_routes_both_
  languages` carries the rest of the original check unchanged: the
  route-list parity check reads `companion.test_browser_ux_helpers.
  VIEW_TRANSITION_ROUTES` via a plain import (never the legacy check's
  own `ast.parse()` of that file's source), then fetches all six routes
  in both languages over a real server and re-applies every counting/
  exemption/anti-vacuity floor unchanged. The ledger row points at this
  primary node id; the split-off cross-check test is the second.

Rubric-code split across this part's 52 baseline rows: 44 B (HTTP
round-trip/module-call checks), 6 D (markup/regex-over-rendered-HTML
checks: the rules-form-placement check and the five sub-checks inside
the editorial floor's own measurement loop), 1 S rewritten as a
`not hasattr()` battery (row 317), 1 S rewritten as calling behaviour
(row 320's cross-check), 0 C, 0 J, 0 P, 0 R, 0 T, 0 deleted.

**Chain closed.** `companion/test_companion_app.py` deleted outright
(`git rm`): all 320 baseline checks are accounted for (319 `ported`
across `companion/test_companion_app_01.py`..`_05.py`, 1 `deleted` —
row 89, from an earlier plan in this chain — 0 `pending`).
`33-ledger-check.py companion/test_companion_app.py` **WITHOUT**
`--allow-pending` confirms 320/320.


### Closing sweep (plan 33-32): structural stylesheet checks

Rows 51, 52, 57, 59, 174 and 179 kept their node ids but no longer assert with a regex, `in`
test or str search over the served stylesheet's text (33-FOLLOWUPS.md F-01). "Class X is
styled" is now a selector match over `css_rules()`; the `.js .mobile-nav` rules and the
`input.visually-hidden` floor-clearing rule are read with `declarations_for()`; row 174 counts
`@supports selector(:has(*))` with `companion_markup.at_rule_blocks()`; row 179 counts
`@keyframes` and reduced-motion `@media` blocks with `at_rule_blocks()` and checks every
animation declaration outside those blocks through `css_rules()`, which retires the
module's own brace-matching text helper.

### Closing sweep (plan 33-32): one shared counting rule

Row 320's secondary node id
`test_caption_word_count_text_agrees_with_test_config_page_05s_own_copy` imported the sibling
test module `companion.test_config_page_05` to compare two copies of the editorial floor's
counting rule. The rule now lives once, as `caption_word_count_text()` in
`companion/test_config_page_helpers.py`, and both modules import it, so the agreement check
became a tautology. It is replaced by
`companion/test_companion_app_05.py::test_caption_word_count_text_strips_markup_entities_and_one_leading_dash`
(parametrised over the same four fixtures, with pinned expected outputs). Row 320 still points
at its primary node id, `test_site_wide_editorial_floor_all_six_routes_both_languages`, which is
unchanged. Guard rule G12 now forbids a test module importing another test module.

