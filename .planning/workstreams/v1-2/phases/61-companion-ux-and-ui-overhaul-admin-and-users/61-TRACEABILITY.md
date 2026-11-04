# Phase 61 — traceability

What closes each friction, audit note and requirement, and which test proves
it. Sources: `61-WALKTHROUGH.md`, `61-VISUAL-AUDIT-NOTES.md`,
`61-OWNER-DECISIONS.md`, the SUMMARY of each plan. Status words: **closed**
(changed and tested), **closed with a stated limit** (the limit is named),
**owner confirm** (implemented on the spec default, the owner may overrule).

Note on numbering: `61-WALKTHROUGH.md` defines F1 to F11 (F1 to F11 appear in
the document; there is no F12 in it, although `61-CONTEXT.md` and plan 61-12
speak of F1-F12). Decisions D1 to D10 from the walkthrough, D11 to D15 from
the context file are traced after the frictions.

## Frictions F1-F11

| F | Friction | Closed by | Where | Proof |
|---|----------|-----------|-------|-------|
| F1 | FR "Cadres" for the fleet confuses | 61-04 (nav label), 61-06 (page) | `companion/i18n_fr/nav.py` (`nav.fleet` = "Flotte"), `companion/pages/fleet_page.py` | `test_nav_spaces.py`, `test_console_fleet_page.py`, FR title check in `test_browser_overhaul_sweep.py` |
| F2 | Admin console is one tab of the everyday app | 61-04, 61-05 | `companion/ui_nav.py` (Console and My views spaces, space switch), `companion/access.py` (`home_for`) | `test_nav_spaces.py`, `test_browser_nav_spaces.py`, `test_landing.py`, `test_browser_auth0.py` (admin lands on `/fleet`) |
| F3 | Fleet table unreadable | 61-03, 61-06 | `companion/ui_entity_list.py`, `companion/pages/fleet_page.py`, `style.css` | `test_ui_entity_list.py`, `test_browser_fleet_page.py`, no-table and overflow checks in `test_browser_overhaul_sweep.py` |
| F4 | Emails and frame names in large monospace | 61-03, 61-06, 61-08 | entity-list CSS (no monospace), `users_page.py`, `fleet_page.py` | `test_ui_entity_list.py`, `test_browser_users_page.py`, monospace check in the sweep |
| F5 | Invite form at the page bottom | 61-02, 61-08 | `companion/ui_modal.py`, `users_page.py` ("+ Invite a user" dialog) | `test_ui_modal.py`, `test_browser_users_page.py`, `test_browser_overhaul_steps.py` (A2 = 4) |
| F6 | "Register a frame" form always open | 61-06 | form removed from the page; `POST /fleet/register` kept | `test_console_fleet_page.py`, `test_console_pairing.py` (route tests unchanged) |
| F7 | Pairing should be an "Add a frame" button | 61-06 | `fleet_page.py` header action + Add dialog | `test_browser_fleet_dialogs.py`, step test A3 = 4 |
| F8 | Retire / Reassign / Re-activate as inline disclosures | 61-06 | row menu + confirm dialogs | `test_browser_fleet_dialogs.py`, step tests A4 = 3 and 4 |
| F9 | Co-managers card on Home | 61-07 | `co_managers` dialog on Fleet; Home card removed | `test_co_managers_page.py`, `test_browser_co_managers.py` (Home has none), step test A5 = 4 |
| F10 | Co-managers card on the frame page is wrong for users | 61-10 | My frames card on Account: Manage access (owned) or Leave (shared) | `test_account_page.py`, `test_browser_account_frames.py` |
| F11 | Landing on Account after sign-in | 61-05, 61-09 | `access.home_for`, `device_scope.default_frame_for`, 303 from un-prefixed pages | `test_landing.py`, `test_access_matrix.py` (landing rows), step tests U1, U2 |

## Decisions D1-D15

| D | Decision | Closed by | Proof / note |
|---|----------|-----------|--------------|
| D1 | Admin space, link to own views, no Admin tab | 61-04, 61-14 | `test_nav_spaces.py`, `test_browser_nav_spaces.py` |
| D2 | Fleet row: name, owner, one status dot | 61-01, 61-06 | `test_frame_status.py`, `test_console_fleet_page.py` |
| D3 | Forms open from a "+" / action button in a dialog | 61-02, 61-06, 61-07, 61-08, 61-10 | `test_ui_modal.py`, dialog browser tests; dialog sweep in `test_browser_overhaul_sweep.py` |
| D4 | "cadre" is the device; fleet page named otherwise | 61-06 | FR strings in `i18n_fr/admin_fleet.py`; ledger row 1 |
| D5, D6 | Manage access per frame (Fleet, My frames) | 61-07, 61-10 | `test_co_managers_page.py`, `test_browser_co_managers.py`, `test_browser_account_frames.py` |
| D7 | User lands on frame Home; switcher on multi-frame | 61-05, 61-09 | `test_landing.py`, `test_frame_switcher.py`, step test U2 |
| D8 | One status dot for a user | 61-01, 61-09 | `test_frame_status.py`, `test_home_state_card.py`, `test_browser_home_state_card.py`, step test U3 |
| D9 | All display settings stay; location and detection merge. **Superseded by D16, D20 and D8-style moves of revision 2:** the merged card, the location picker and the time zone select left Display (plan 61-33), quiet hours left Display (plans 61-27 and 61-34); the place and zone live on the Location and detection page (see D16-D20 below) | 61-10 | `test_display_detection_card.py`. The time zone select is in the merged "Location and detection" card (61-16, owner confirmed); the Quiet hours card keeps a sentence and a link to it. The select has its own dirty section "Time zone" (FR "Fuseau horaire") and posts through the same settings form: `test_display_time_zone_card.py`, `test_browser_display_time_zone.py` (360 and 1280 px, EN/FR, both themes, save bar naming, save, scripts blocked), `test_device_settings.py` (validation and storage unchanged). |
| D10 | Architecture and visual style unchanged | all | no new runtime dependency; `modal.js` is the only new static script |
| D11 | Fleet page named "Fleet" / "Flotte" | 61-04, 61-06 | ledger row 1; FR title check in the sweep |
| D12 | Fleet list shows no last image | 61-06 | ledger row 2 |
| D13 | User on an un-prefixed page gets a 303 to their frame | 61-05 | `test_landing.py`, `test_access_matrix.py` |
| D14 | Health leaves the user tab bar, reached from the Home dot. **Superseded by D16 and D21:** a user has no Health page at all and the Home dot with its notification is enough; Health is a Console page | 61-04, 61-09 | `test_user_nav.py`, `test_home_state_card.py` (first round); `test_nav_personal_console.py`, `test_airline_manage_routes.py`, `test_home_notice.py` (revision 2) |
| D15 | Three audit items in scope | 61-15 | section below |


## Visual audit notes (`61-VISUAL-AUDIT-NOTES.md`)

| Item | Status | Closed by / note |
|------|--------|------------------|
| User view is one page; tab bar offers tabs that 404 | closed | 61-04 (user bar), 61-05 (303 redirects) |
| Fleet desktop table clipped | closed | 61-06 (entity list) |
| Fleet phone cards long; console tabs wrap on two lines | closed | 61-06; 61-04 and 61-14 (one bottom bar, no chip row) |
| Phone nav: Admin tab, More | closed | 61-04 |
| Users phone: email breaks mid-word, wrong "INVITED" badge, role select + Save role per user | closed | 61-08 |
| Pair and Register forms always open | closed | 61-06 |
| Fixed tab bar overlaps content in full-page captures | capture artefact | sweep takes viewport (not full-page) measurements |
| Sidebar has 3 groups / 12 entries; Account missing for admin | closed | 61-04 |
| Device / Update / Releases three names | closed | 61-04, 61-06 (title "Releases") |
| "Detection" on both Display and Device | closed | 61-10 |
| Console section tabs wrap; Audit stacks a second chip row | closed | 61-04, 61-14 |
| "Frame" picker even with a single frame | closed | 61-09 (switcher only with two or more frames) |
| Users: "Invited" badge on signed-in users; truncated last-admin text | closed | 61-08 |
| Locations inputs/selects overflow at 360 px | closed, then **removed by D20** | 61-04 (`max-width: 100%`); the Locations page and its 360 px test no longer exist as a page (a refused POST still renders the legacy form; `/locations` GET is a redirect to Fleet) |
| Owner/co-manager actions on Home far from Fleet | closed | 61-07 |
| Home: persistent attention bar | closed with a limit | admin Home keeps the attention bar by design; a plain user's Home has none (61-09) |
| Home: empty states large serif blocks; Current frame card empty | closed | 61-15 (Home), 61-16 (every remaining page); see "Audit items" below |
| Device: LED switch drawn with an orange box | closed | 61-15 |
| Health: "Has not checked in" three ways | closed | 61-15 |
| User view: serif name + hardware, no frame state | closed | 61-10 (My frames rows with dot) |
| Login card; error and invitation states to capture | closed | 61-11 (outcome pages) |

## Audit items brought into scope on 2026-11-03 (plan 61-15)

| Row | Item | Files | Tests | Status |
|-----|------|-------|-------|--------|
| A | Device page Diagnostic LED switch drawn with an orange box (the primary button fill outranked the `.switch` rule) | `companion/static/style.css` (`button.switch` rules) | `companion/test_browser_device_led_switch.py` (both themes, EN/FR, 360 and 1280 px, keyboard focus ring, click toggling) | closed |
| B | Health Frame connection row says "Has not checked in" three ways | `companion/pages/health_page.py` (`_connection_row`) | `companion/test_health_connection_row.py`, `companion/test_user_health.py` | closed |
| C | Empty states drawn as large serif blocks | `companion/static/style.css` (`.empty-state--compact` padding), the `empty_state` callers on Home, Health, Audit, Locations, Update | `companion/test_empty_state_scale.py`, `companion/test_browser_empty_state_scale.py`, `companion/test_status_pages_02.py` | closed (61-16 finished the remaining pages) |

Row C, completed by plan 61-16. Plan 61-15 converted Home (no panel, no
flights), Health (device empty, no gaps), Audit (no events), Locations and
Update. Plan 61-16 converted the last two large-form callers: History (no
flights, device empty) and the `data_table` empty fallback in
`companion/ui_components.py`. The Detection page's three empty states and the
My frames empty state in `account_page.py` were already compact when plan
61-16 was written (the earlier note that they were large was stale). No
empty state outside the filter form is large now: `ui_filter.py`'s
`empty-state--filter` and the Audit filtered-result block keep the large
filter form by design, as filter results and not empty pages. Proof:
`companion/test_empty_state_scale.py` (served markup, EN/FR, Home, Health,
Audit, Locations, Update, Flights, device Flights, Detection, Account, the
table fallback) and `companion/test_browser_empty_state_scale.py` (computed
heading size and face, both themes, 360 and 1280 px), and the sweep's
structure check flags any large empty state on the pages it loads.

## Cross-page sweep (`companion/test_browser_overhaul_sweep.py`)

204 cases: 22 page and dialog cases (Fleet and its four dialogs, Users and its
two dialogs, Locations, Audit log, Releases, admin Account, admin Home, Display,
Device and Health, a user's Home, Display and Account, the owner's and a
co-manager's Account dialogs) at 360 and 1280 px, EN and FR, light and dark,
plus a French-versus-English text comparison per case, the French Fleet title,
and Locations fields inside their card at 360 px.

Defects the sweep found and plan 61-12 fixed: the skip link had no French text;
an administrator's Account page rendered no tab bar on a phone; the Fleet name
link, Account language/theme/Sign out controls, the phone toast action, the
quiet-hours presets and the special-look Remove button were under 44 px.

Stated limits of the sweep (not claimed closed):

- The 44 px floor is asserted on the whole page, the header and the tab bar at
  360 px, and in dialogs. At 1280 px it is asserted for dialogs, list rows and
  page headers, and, since plan 61-16, for the desktop sidebar links, its
  language and theme segments, Sign out, the brand link and the Home "See
  Health" pill (hit-tested resolved boxes, EN/FR, both themes; admin and user
  sidebars). UI-SPEC section 8 item 2 holds at both widths for these controls.
- The sweep's empty-state check covers the pages it loads; History and the
  other pages converted in 61-16 are asserted in `test_empty_state_scale.py`
  and `test_browser_empty_state_scale.py`.
- Untranslated-text detection compares the French and English renders and
  ignores product, hardware and seeded data names, identifiers and a short list
  of words French shares with English. It is not a catalogue lookup:
  `test-support/i18n_ids.py` is a migration helper, and catalogue completeness is
  already asserted by `companion/test_i18n.py`.
- `companion/test_browser_phase44_walkthrough.py` needed no edit: its routes,
  headings, active-navigation and Display-save assertions pass unchanged against
  the new labels.

## Requirements to plans

| Requirement | Plans | Evidence |
|-------------|-------|----------|
| UX-01 (walkthrough, ranked frictions, reworked navigation and structure) | 61-01 to 61-05, 61-09, 61-14 and the walkthrough record | this file; `61-STEP-COUNTS.md` |
| UX-02 (admin tasks) | 61-02, 61-03, 61-06, 61-07, 61-08, 61-14 | `test_browser_fleet_dialogs.py`, `test_browser_users_page.py`, `test_browser_co_managers.py`, step tests A1-A6. Owner validation on the deployed companion is plan 61-13, not done here. |
| UX-03 (user sees own frames, state at a glance, changes settings) | 61-04, 61-05, 61-09, 61-10 | `test_browser_account_frames.py`, `test_browser_home_state_card.py`, step tests U2-U4. **U4 misses its step target** (4 and 5 against 3): see `61-STEP-COUNTS.md`. Owner validation on a phone is plan 61-13. |
| UX-04 (sign-in clarity) | 61-11 | `test_sign_in_messages.py`, `test_browser_auth0.py` |
| Audit items A-C (D15) | 61-15, 61-16 | section above |

## Owner-decision ledger state (`61-OWNER-DECISIONS.md`)

All 14 open items and audit rows A-C: no owner answer has been recorded in the
ledger, so rows 1-14 are **defaulted** (the spec default was applied), and rows
A-C are **answered** ("yes, in scope", 2026-11-03). Rows 1, 2, 5 and 10 are
also fixed by D11, D12, D14 and D13. Owner-confirm items beyond the ledger:

| Item | Detail |
|------|--------|
| Time zone select placement | Moved into the merged Location and detection card by 61-16 (owner answered yes). |
| Display page length / U4 | Changing one display setting takes 4 actions (5 for a look), one or two over the target of 3, because the settings sit below the first screen or in a sheet. Not addressed in this phase. |
| Remaining large empty states | Converted by 61-16 (History, table fallback; Detection and My frames were already compact). |
| Desktop 44 px targets | Done by 61-16: sidebar, footer controls, brand link and the Home "See Health" pill. |


## Revision 2 (owner validation of 2026-11-03; plans 61-17 to 61-34)

Status words as above. Every test below was opened and exists by that name in
the module named. Where a V, D or R item is only partly met, the status says
which part.

### Issues V0-V10

| V | Issue | Status | Closed by | Where | Proof |
|---|-------|--------|-----------|-------|-------|
| V0 | The administrator's frame view differs from the user's | closed | 61-17, 61-19, 61-21, 61-22 | `companion/ui_nav.py` (one personal navigation), `companion/device_scope.py` and the dispatch redirect (an administrator's un-prefixed personal pages follow the frame rule), `companion/pages/home_page.py` (Home parity, owner decision option A), `companion/ui_shell.py` (`frame_notice_html`) | `test_personal_space_parity.py::test_a_personal_page_is_identical_for_an_administrator_and_a_user`, `test_nav_personal_console.py::test_the_personal_navigation_is_identical_for_an_administrator_and_a_user`, `test_landing.py::test_an_admin_is_moved_to_their_default_frame_like_a_user`, `test_browser_overhaul_sweep.py::test_an_administrators_personal_page_equals_a_users` (headings, navigation and controls equal at 360 and 1280 px; the switch and the foreign-frame notice are the whole difference) |
| V1 | "Mes vues" unclear | closed | 61-21, 61-22 | `companion/i18n_fr/nav.py` (`nav.my_frame`: "My frame" / "Mon cadre") | `test_nav_personal_console.py::test_the_old_space_name_and_group_are_gone_from_every_served_page`, `test_space_switch.py::test_the_switch_labels_and_names_are_french_in_french` |
| V2 | Switch not visible enough | closed | 61-22 | `ui_nav.space_switch_html`, `.space-strip` and the sidebar top in `style.css` | `test_space_switch.py`, `test_browser_space_switch.py::test_the_switch_shows_both_spaces_and_marks_the_current_one` and `::test_one_tap_moves_between_the_two_spaces` |
| V3 | "All frames (Fleet)" in the switcher | closed | 61-23 | `ui_shell.frame_switcher_html` | `test_frame_sheet.py::test_the_personal_page_of_an_administrator_has_no_console_list`, `test_browser_frame_sheet.py::test_the_personal_sheet_of_an_administrator_has_no_fleet_entry` |
| V4 | "Flights" named "Flight history" | closed | 61-21 | `ui_base.py` labels (`nav.flight_history`) | `test_nav_personal_console.py::test_flight_history_is_the_navigation_label_and_the_page_title` |
| V5 | Health and Device only reachable from the Console | closed | 61-17, 61-19, 61-21 | `route_types.ADMIN_DEVICE`, `console_routes.py`, `pages/fleet_page.py` (name link to the Console Health) | `test_airline_manage_routes.py` (access), `test_access_matrix.py::test_http_outcome_matches_the_policy_table`, `test_nav_personal_console.py::test_console_frame_pages_render_in_the_console_chrome_for_each_frame`, step test A7 |
| V6 | Frame switcher is a drop-down | closed | 61-23 | `ui_shell.frame_switcher_html` (chip and card sheet on the shared modal) | `test_frame_sheet.py`, `test_browser_frame_sheet.py` (focus, Esc, no-script hash path, geometry) |
| V7 | Location and detection with a real map, no saved locations | closed with stated limits | 61-18, 61-20, 61-24, 61-25, 61-26, 61-33 | `fleet_db.save_frame_position`, `detection_actions` (`save_place`), `page_policy.py`, `pages/place_page.py`, `static/place-map.js`, vendored Leaflet | `server/test_fleet_frame_position.py`, `server/test_poll_position_parity.py`, `test_place_save.py`, `test_place_page.py`, `test_page_policy_headers.py`, `test_vendored_leaflet.py`, `test_browser_place_map.py`, `test_browser_place_search.py`. Limits: choosing an airport navigates to the server-side `?airport=` page instead of flying in place; the step counts L1, L2 and L4 miss their targets by one (`61-STEP-COUNTS.md`) |
| V8 | Quiet hours in a modal on Home | closed | 61-27, 61-33, 61-34 | `settings/quiet_hours.py`, `post_actions.py` (`POST /quick/quiet-hours/window`), `pages/home_page.py` | `test_quiet_hours_modal.py`, `test_browser_quiet_hours_modal.py::test_saving_in_three_taps_changes_only_the_three_keys_and_home_follows`, `test_display_time_zone_card.py::test_display_has_no_quiet_hours_or_time_zone_and_home_dialog_links_to_the_details_card` |
| V9 | Display becomes Personalisation | closed with a stated deviation | 61-28, 61-29 | `pages/personalisation_cards.py`, `settings/theme.py`, `settings/rules.py`, `settings/calendar.py` | `test_personalisation_page.py`, `test_browser_personalisation.py`, `test_personalisation_special_looks.py`, `test_browser_personalisation_cards.py`. Deviation: four cards, not five (D23), and the card titles keep the serif settings-card style instead of the spec's 16 px sans (see limits) |
| V10 | Airline collection, editing only for the administrator | closed | 61-30, 61-31 | `airline_collection.py`, `pages/airline_collection_page.py`, `pages/airlines_page.py`, `pages/airline_resolutions.py` | `test_airline_collection.py`, `test_airline_collection_page.py`, `test_browser_airline_collection.py`, `test_airline_editor.py`, `test_browser_airline_editor.py` |

### Decisions D16-D25

| D | Decision | Closed by | Proof / note |
|---|----------|-----------|--------------|
| D16 | Same personal pages for administrator and user; Health, Device, airline editing, Fleet, Users, Audit, Releases in the Console | 61-17, 61-19, 61-21, 61-22 | the V0 proofs; `test_nav_personal_console.py`. Supersedes D9 (partly), D14 |
| D17 | All of V1-V10 in this phase | 61-17 to 61-34 | this section |
| D18 | Real OpenStreetMap map; tile host in the CSP, map script vendored, attribution | 61-24, 61-26 | `test_page_policy_headers.py`, `test_vendored_leaflet.py`, `test_browser_place_map.py::test_the_attribution_is_visible_inside_the_map_and_links_to_the_copyright_page`, `::test_every_tile_request_carries_the_page_origin_as_referer`. Leaflet 1.9.4 was fetched as a tarball and accepted only after its SHA-256 matched the pinned values |
| D19 | Pin on the map, airports list, search, "my position" | 61-25, 61-26 | `test_browser_place_map.py`, `test_browser_place_search.py`, `test_place_page.py` |
| D20 | Saved locations removed; the frame carries its own position; expand-only for the live frame | 61-17, 61-18, 61-20, 61-25, 61-33 | `server/test_poll_position_parity.py` (the poll's reading and the schema unchanged), `test_console_locations.py::test_the_list_page_is_gone_an_administrator_is_sent_to_fleet`, `test_place_page.py::test_no_saved_locations_interface_remains`. The Locations nav, page and 360 px sweep test are removed; the POST routes and the table remain (expand-only) |
| D21 | A user has no Health page; the dot is enough; the amber dot has a notification | 61-17, 61-19, 61-34 | `test_airline_manage_routes.py`, `test_access_matrix.py`, `test_home_notice.py`, `test_browser_home_notice.py` |
| D22 | Contact an administrator by a mailto link, no server-side sending | 61-34 | `test_home_notice.py::test_mail_subject_and_body_name_the_frame_and_the_known_figures`, `::test_address_is_percent_encoded_and_shape_checked`, `::test_no_route_was_added_and_nothing_new_is_requested`, `test_browser_home_notice.py::test_the_mailto_names_the_frame_and_the_state` |
| D23 | Only administrators change the wake interval, in the Console Device page | 61-28 | `test_user_view.py::test_only_administrators_may_change_the_wake_interval`, `test_personalisation_page.py::test_a_users_posted_wake_interval_is_refused_and_the_interval_stays`, step test U4c |
| D24 | The notification also shows for the red state | 61-34 | `test_home_notice.py::test_amber_and_red_statuses_show_one_notification`, `test_browser_home_notice.py` (the no-contact cases) |
| D25 | The notification says what the server knows (figures, tip, "cannot tell Wi-Fi from server") | 61-34 | `test_home_notice.py::test_english_lines_and_tips_per_status_key`, `::test_french_lines_and_tips_per_status_key`; `test_browser_overhaul_sweep.py::test_the_home_notification_holds_the_layout_rules` (figures per state, no console words, the contact link a 44 px mailto anchor, plain text without an administrator) |

### Assertions R1-R28

| R | Status | Proof |
|---|--------|-------|
| R1 | met | `test_personal_space_parity.py::test_a_personal_page_is_identical_for_an_administrator_and_a_user` (links, control names, normalised body over HTTP), `test_browser_overhaul_sweep.py::test_an_administrators_personal_page_equals_a_users` (headings, navigation, controls at 360 and 1280 px; Account is compared by `test_personal_space_parity.py::test_account_navigation_and_controls_match_for_both_principals`) |
| R2 | met (stronger than asked: "Name this airline" is absent for everyone) | `test_personal_space_parity.py::test_no_personal_page_offers_an_admin_control`, `::test_flight_history_keeps_the_unidentified_wording_without_a_link`, the forbidden-word check of `test_browser_overhaul_sweep.py::test_reworked_pages_hold_the_layout_rules` (user pages and administrator personal pages, extended by Health and Airline editor) |
| R3 | met | `test_nav_personal_console.py`, `test_browser_nav_spaces.py::test_console_bar_has_five_equal_cells_at_360`, `::test_personal_bar_has_five_equal_cells_at_360`, `::test_desktop_personal_sidebar_lists_the_spec_links`. Language, theme and Sign out stay in the gear panel and sidebar footer, not the More sheet |
| R4 | met | `test_airline_manage_routes.py`, `test_access_matrix.py`, `test_console_locations.py::test_the_list_page_is_gone_an_administrator_is_sent_to_fleet`, `stub-server/test_phase47_freeze.py` |
| R5 | met | `test_nav_personal_console.py::test_the_old_space_name_and_group_are_gone_from_every_served_page`, `test_space_switch.py` |
| R6 | met | `test_space_switch.py`, `test_browser_space_switch.py::test_the_switch_shows_both_spaces_and_marks_the_current_one`, `::test_a_user_never_sees_the_switch` |
| R7 | met | `test_browser_space_switch.py::test_one_tap_moves_between_the_two_spaces`, step test S1 |
| R8 | met | `test_frame_sheet.py`, `test_browser_frame_sheet.py::test_the_personal_sheet_of_an_administrator_has_no_fleet_entry` |
| R9 | met | `test_nav_personal_console.py::test_flight_history_is_the_navigation_label_and_the_page_title`. The page keeps its route and navigation id `display` while it reads "Personalisation" (page title and sidebar) and "Style" (phone bar, ledger R2-15), so the page-title and bar words differ by design |
| R10 | met | `test_nav_personal_console.py::test_console_frame_pages_render_in_the_console_chrome_for_each_frame`, `test_frame_sheet.py::test_console_pages_list_every_frame_with_the_owner_email`, step test A7 |
| R11 | met | `test_browser_frame_sheet.py` (focus and Esc, page kept, no-script path, geometry), `test_frame_sheet.py::test_the_chip_opens_the_sheet_through_the_hash_link` |
| R12 | met | `test_place_page.py`, `test_place_save.py` (the refused save is 400 with the error beside the field; the legacy actions keep 200) |
| R13 | met, with one addition | `test_page_policy_headers.py`. The Permissions-Policy header did not exist before and is now sent on every response (`geolocation=()` by default) |
| R14 | met | `test_vendored_leaflet.py`, `test_place_map_assets.py`, `test_browser_place_map.py` (no image request from the library) |
| R15 | met | `test_browser_place_map.py` |
| R16 | met | `test_browser_place_search.py` |
| R17 | met | `test_browser_place_map.py::test_geolocation_is_called_only_on_a_tap_and_moves_the_pin`, `::test_a_blocked_permission_shows_the_denied_sentence`, `::test_the_button_is_hidden_when_the_browser_has_no_geolocation` |
| R18 | met | `test_browser_place_map.py::test_with_the_tile_host_down_the_notice_shows_and_the_pin_still_saves`, `::test_with_the_library_blocked_the_plain_form_shows_and_saves`, `test_browser_place_page.py` (scripts off, both hosts aborted) |
| R19 | met | `server/test_poll_position_parity.py`, `server/test_fleet_frame_position.py`, `test_place_save.py::test_first_save_creates_a_private_row_then_updates_it_in_place_then_repeats_quietly`, `::test_a_row_shared_with_another_frame_is_copied_not_moved` |
| R20 | met | `test_quiet_hours_modal.py`, `test_browser_quiet_hours_modal.py`, `test_display_time_zone_card.py` |
| R21 | met | `test_config_page_02.py::test_a_display_save_changes_no_quiet_hours_zone_place_or_detection_key`, `test_personalisation_page.py::test_saving_personalisation_changes_only_the_look`, `::test_saving_quiet_hours_or_the_place_changes_no_look_rule_calendar_or_interval`, `test_place_save.py::test_a_place_save_writes_no_look_rule_calendar_interval_or_quiet_key`, `test_quiet_hours_modal.py::test_a_valid_save_writes_only_the_three_keys` |
| R22 | **partly met** | `test_personalisation_page.py::test_the_title_the_nav_and_the_four_cards_come_in_order`, `::test_the_look_cards_are_native_radios_with_a_preview_and_a_selected_word`. The page has four cards, not the five of the assertion (the Refresh card is not on Personalisation, D23) |
| R23 | **partly met** | `test_browser_overhaul_steps.py` and `61-STEP-COUNTS.md`: U4a 3, U4b 3, S1 1 and A7 1 meet their targets; **L1 measures 5 (target 4), L2 5 (target 4) and L4 4 (target 3)**; L3 6 and the other rows meet theirs |
| R24 | met | `test_airline_collection_page.py::test_every_role_gets_the_same_read_only_collection`, `::test_a_sheet_per_card_is_read_only_and_reached_by_a_hash_link`, `test_personal_space_parity.py::test_the_airline_collection_is_read_only_and_counts_the_same_history` |
| R25 | met, refined | `test_airline_collection.py`, `test_airline_collection_page.py::test_counts_rarity_and_new_come_from_the_seeded_history`. A flight stored twice for one pass counts once (the same fold Home and Flights use), so "seen n times" counts flights, not stored events |
| R26 | met | `test_airline_editor.py`, `test_browser_airline_editor.py`, `test_airline_manage_routes.py` |
| R27 | met for the pages and dialogs listed, with the sweep's stated limits | `test_browser_overhaul_sweep.py` (`test_reworked_pages_hold_the_layout_rules`, `test_every_visible_string_has_a_french_translation`, `test_the_home_notification_holds_the_layout_rules`, `test_the_home_notification_has_a_french_translation`), `test_i18n.py::test_every_message_id_has_english_and_french` |
| R28 | met | `test_companion_app_04.py::test_style_css_honours_the_motion_budget`, `::test_motion_tokens_are_two_durations_plus_the_documented_exceptions`, `test_stylesheet_structure.py`, `test_contrast_check.py`, `test_browser_detection.py::test_accent_budget`, the function-size and comment-history scripts |

### Revision 2 sweep (`companion/test_browser_overhaul_sweep.py`)

The sweep now holds 455 cases at the final run: 35 page and dialog cases (the
earlier 22 plus Flight history, Location and detection, Personalisation's
remove-special-look dialog, Airline collection, the Airline editor and its
delete-resolution dialog, the frame sheet and the quiet-hours dialog, for
an administrator, an owner and a co-manager) at 360 and 1280 px, English and
French, light and dark; 12 Home-notification cases (not seen, low battery,
no contact with and without an administrator, overdue; owner, co-manager and
administrator) at the same 8 combinations; a French-versus-English comparison
of every case and every notification case; and an administrator-versus-user
shape comparison of the five personal pages at both widths.

What it found and fixed in this plan: the desktop filter chips of Flight
history were 43 px high (now 44 px); the sweep's 1280 px 44 px check had
looked only at list rows and page headers and now covers the whole page
content (`main`) for every case. No other defect surfaced.

Stated limits of the sweep:

- The desktop sidebar's own 44 px check stays in
  `test_the_desktop_sidebar_controls_have_44px_hit_areas`; the page check at
  1280 px covers `main` and open dialogs, not the sidebar.
- The map's pan area and the OpenStreetMap attribution link are not 44 px
  targets (the attribution link is inline, which the check exempts, and the
  pan area is not an interactive element); the map's zoom buttons are
  hit-tested.
- Catalogue names (airlines, airports with their codes), the frame's own
  heading ("Watching Runway 3"), "Ryanair" and the seeded history's pass state
  ("Confirmed", a value the detector never writes) are exempt from the
  untranslated-text comparison; the exemption is by element class for the
  catalogue lists and by a short pattern for the rest.
- The "no text clipped in a list row" check covers entity rows, airport rows,
  collection cards, special-look rows and manual-resolution rows, but not the
  inline look editor of the calendar row (its closed sheet extends past the
  row box by design).
- The notification is swept for the overdue state only as an administrator on
  the live frame (a non-live frame past its overdue point already reads as no
  contact).
- The Locations case remains in the sweep, reached through a refused add
  submission (the legacy form), but its dedicated 360 px test and the
  "Admin / Administration" word test were removed with the concept.

### Revision 2 limits and deviations

- **Language, theme and Sign out** stay in the gear panel and the sidebar footer, not the
  More sheet (plan 61-21).
- **Name this airline** is removed for everyone, administrators included (UI-SPEC 1.1 and
  R1 over 12.2; ledger R2-17, still "owner to confirm").
- **No Edit affordance on a special look**: no edit route exists; the path is Remove, then
  "+ New special look" (plan 61-29).
- **Co-managers may save a frame's place** (ledger R2-19, "owner to confirm").
- **Refresh is administrator-only**, on the Console Device page, not on Personalisation
  (D23; ledger R2-20). Personalisation therefore has four cards, not five.
- **Card titles**: the settings cards on Personalisation keep the serif settings-card title
  style instead of the spec's 16 px sans semibold, because one pinned test requires the same
  title style on Display and Device (plan 61-28). The owner may decide to move both pages.
- **The Display page keeps its route and internal id `display`** while it reads
  "Personalisation" in the page title and sidebar and "Style" on the phone bar (ledger
  R2-15). The message id of the page title is the same as the sidebar label
  (`nav.personalisation`); only the phone-bar word differs.
- **Apply on the Airline collection stays always visible** (plan 61-30): the spec hides it
  once a script submits on change; that needs a new global script, so the filter, chips and
  sort apply through a visible button, and only the text filter is instant.
- **Per-flight counting** in the Airline collection (a flight stored twice counts once), not
  one per stored event.
- **Airline editor page height**: `test_browser_ux_01`'s page-height ceiling for the
  Airline editor at 390 px went from 3900 to 4100 px, because the manual-resolutions list
  adds about 120 px for the seeded registry (plan 61-31).
- **Manual-resolutions list** on the Airline editor was added (plan 61-31) so the
  "Delete this resolution?" dialog has a row to open from; it can be dropped without
  touching the handlers.
- **Audit log is two taps** (More, Audit log) in the Console, one over the first-round
  target (A6).
- **Step-count targets missed**: L1 (5 against 4), L2 (5 against 4), L4 (4 against 3); see
  `61-STEP-COUNTS.md`. The first-round U4 misses were closed (U4a and U4b measure 3).
- **`/detection` refused saves answer 400**; the legacy detection and location actions keep
  200 (plan 61-20/25).
- **Choosing an airport navigates** to the server's `?airport=` page instead of moving the
  map in place (plan 61-26).
- **Leaflet 1.9.4** was fetched as a tarball and accepted only after its SHA-256 matched the
  pinned values (plan 61-24); it is vendored unmodified, with no manifest or lockfile.
- **Permissions-Policy** is now sent on every response (`geolocation=()`), `geolocation=(self)`
  on the map page only.
- **Contact of an administrator** is a mailto link only, no server-side sending (D22); the
  notification shows for the amber (warn) and the red (error, frame without contact) states
  alike (D24), for owner, co-manager and administrator.
- **Home parity** (owner decision option A): the battery pill, the charging pill and the
  "Something needs attention" toast left the personal Home for everyone; the Battery row and
  the charging pill live on the Console Health page. The Home battery code is dead in
  production and left for a cleanup plan.
- **Quiet-hours dial** builders, CSS and script remain for the legacy all-scope render and
  its tests; no served page uses them (plan 61-34).
- **Caption floors** were lowered where the removed Display cards were the subject (Display
  4 to 2, site total 18 to 14).
- **Locations POST routes and the `locations` table are kept** (expand-only, ledger R2-16).
- **Sweep-data note**: the sweep's seed adds a special look and a manual resolution to the
  live frame and a second frame for the owner, so the earlier cases run with a frame chip.

### Owner-decision ledger state, revision 2

`61-OWNER-DECISIONS.md` rows R2-1 to R2-20: R2-10 and R2-20 are answered (D21, D23); R2-17,
R2-18 and R2-19 were raised by the planner and are marked "owner to confirm"; every other row
is applied on its default. Plan 61-13 (owner validation on the deployed companion) is not done
here.
