---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 108
subsystem: companion
tags: [audit-4, csrf, ux, workflow, visual]
requires: [61-107]
provides: [audit-4 visual findings W01-W23, audit-4 workflow partials]
key-files:
  created:
    - companion/quiet_server.py
    - companion/test_quiet_server.py
    - companion/test_audit4_fixes.py
    - companion/test_browser_audit4_fixes.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/frame_rename.py
    - companion/page_context.py
    - companion/post_actions.py
    - companion/static/style.css
    - companion/static/dirty-state.js
    - companion/static/list-filter.js
    - companion/static/motion.js
decisions:
  - "Sidebar and tab bar name the airline editor with the same one word (Editor / Éditeur); the page keeps the full name as its title"
  - "An illustration upload carries its anti-forgery token in the action URL's query (its multipart body is read by the handler); the server never logs query strings"
  - "A form page's Save bar is in the page without script and appears with script only once a field changed; a page redrawn with a refused value keeps it visible"
  - "A refused special-look key is a redirect to the New special look form carrying the typed kind, key and look in the query (known kind and look, key capped at 80 characters, validated again on save)"
---

# Phase 61 Plan 108: Audit 4 (D54), visual and workflow findings

Every visual finding W01-W23 and the five workflow partials of audit 4 are treated (fixed, or
shown not to be a defect). Performance findings R01-R28 are **not** part of this plan (see the
end).

## Workflow rows

| Row | Result | Test |
|---|---|---|
| A1 CSRF gap | Fixed. `/settings/rules/add`, `/settings/calendar/connect`, `/airlines/resolve`, `/airlines/rename`, `/illustration/*.png` (upload) and `/logout` are in `CSRF_ROUTE_KEYS`; their forms carry the hidden field (rules, calendar connect, both resolve forms, the three logout forms; rename already did). The upload forms and the dialog's `data-view-panel-*-action` addresses carry `csrf_token` in the query (`ui_components.csrf_query`, checked by `routes.submitted_csrf`). No in-page `fetch` posts to these routes. Every test that posted without a token was moved to the token helpers (`with_csrf`, new `csrf_url`). | `test_csrf.py` (tokenless POST is 403 and changes nothing for the four new form routes, logout needs the token, upload token in the URL, a token of another session is refused, forms/actions served with the session's token) |
| RN6 return_to | Fixed. `frame_rename._return_to` refuses `/devices/<id>/...` of a frame the viewer cannot reach and `/components` for a non-admin (falls back to the default, so Cancel/Save never land on a 404). A `/frame/name` POST without a token answers 403 (the route is `csrf=True`; no redirect to `/login`). | `test_frame_rename_and_users_switch.py` (three new tests) |
| NF-note history | Fixed in `list-filter.js`: the entry is "base", "draft" or "committed"; live typing rewrites a base/draft entry but starts a new entry after a settled search; Enter on live-typed text settles the entry. Back after two searches returns to the first. | `test_browser_audit3_fixes.py::test_back_after_two_typed_and_entered_searches_returns_to_the_first` (and the existing sort/typing test still passes) |
| NF-load no-JS images | Partly by design, evidence below. All below-the-fold pictures (airline thumbs, collection cards, layout/look pickers, calendar special rows, history thumbs) now carry `loading="lazy" decoding="async" fetchpriority="low"` plus width/height; the first-screenful pictures stay eager. Measured in Chromium with scripting off: `loading=lazy` is **ignored** (36 of 72 airline images were still requested), because browsers only honour lazy loading when scripting is enabled. So with JS off the pictures cannot be deferred by markup; `fetchpriority="low"` keeps them behind CSS and the first paint. | `test_audit4_fixes.py::test_pictures_below_the_first_screen_...` |
| LOG-brokenpipe | Fixed. `companion/quiet_server.py` (`QuietHTTPServer.handle_error`) drops `BrokenPipeError`, `ConnectionResetError`, `ConnectionAbortedError`; everything else is reported as before. `app.py` and the test server use it (app.py net +2 lines, 1488). | `test_quiet_server.py` |
| Refused special-look key | Fixed with Post/Redirect/Get: 303 to the New special look form with `rule_refused=1&rule_kind&rule_key&rule_theme_id`; `page_context.rule_draft` keeps only a known kind and look and an 80-character key. Reload does not resubmit. | `test_companion_app_05.py::test_rules_add_route_rejection_paths` (updated), `test_audit4_fixes.py::test_the_refused_key_query_only_carries_...` |

## Visual findings

| # | Result | Test / evidence |
|---|---|---|
| W01 | Fixed: `status_of` is Invited only with no identity link **and** no recorded sign-in | `test_audit4_fixes.py::test_a_recorded_sign_in_...`, browser `test_the_user_status_follows_the_last_sign_in` |
| W02 | Fixed: `<wbr>` after `@` and `.` in the address, `overflow-wrap: anywhere` as the fallback, full address in `title` (already) | browser `test_user_cards_wrap_addresses_at_separators_...` (every line break falls after `@` or `.`) |
| W03 | Fixed: at 26rem and below the card grid is 9fr/4fr, the Active label is dropped (the status pill already says it), the select takes its cell; the self row's fixed role has the select's 44px height | same browser test (select wider than its widest option + padding, no page overflow, EN and FR at 360) |
| W04 | Decided: one full name per page, the nav a word of it. The sidebar now says Editor / Éditeur like the tab bar; the page title stays Airline editor / Éditeur de compagnies. Tests that pinned the long sidebar label were updated in place | browser `test_every_sidebar_item_is_one_line_of_the_same_height` (EN/FR) |
| W05 | Fixed: `.fleet-blocks--system` starts at the page column (no centring margin) | browser `test_system_cards_start_at_the_page_column` |
| W06 | Fixed: form pages (special look new/edit, calendar connect and look, Rename) use the page bar with `reveal_on_change`: hidden until a field differs from its loaded value, hidden again when undone, visible without script and when redrawn with a refused value (`data-dirty-keep`). The Cancel link stays in the bar and the page's back link is always there. Added to the Components page (new state) | browser `test_a_form_page_bar_appears_only_once_a_field_changed`, `test_a_form_page_bar_is_in_the_page_without_script` |
| W07 | Measured: the caret was 11px inside the bar, not on its border (the audit's reading came from the screenshot scale); moved down 2px for clearance and tested | browser `test_the_phone_tab_bar_caret_sits_clear_of_the_bar_edge` |
| W08 | Fixed: the hero picture has a 6px margin (the ring sits 5px outside + 2px stroke) so the ring's outer edge is on the column, grid column 212px so the picture keeps 200px | browser `test_the_hero_picture_leaves_room_for_its_ring_...` |
| W09 | Fixed: `.sidebar-link:focus-visible { outline-offset: -2px }`, ink-coloured ring on the active pill | browser `test_the_sidebar_focus_ring_hugs_its_item` |
| W10 | Caption fixed (body font: the `mono` class removed from the Flights picture dialog). The loading state exists: the picture's thumbnail gets the `is-loading` shimmer while it loads and the dialog opens only once the picture arrived (`panel-lookup.js`), so the dialog never shows an empty tile | existing `test_browser_picture_loading.py`; caption in `test_the_picture_dialog_caption_uses_the_body_font` |
| W11 | Fixed: name box no longer wraps (badge inline, row one line tall), the non-editable name sits where the editable names put their text, the placeholder uses the theme-aware token | browser `test_a_hand_named_airline_keeps_its_row_one_line_tall` |
| W12 | Fixed: new token `--picture-placeholder` (a tint of the ink, light and dark) replaces the constant white backdrop behind look, layout, special-row, collection and placeholder pictures; the small pictures fade in when they arrive (`motion.js`, no shimmer on their container) | browser `test_pictures_that_have_not_arrived_show_a_tint_of_the_ink` (light and dark) |
| W13 | Fixed with W12 (same placeholder and the same fade; the blank card for an airline with no illustration is the same tinted tile) | same |
| W14 | Fixed: Credits offers Back to Home / Back to Account for a signed-in person, Back to sign in otherwise | `test_audit4_fixes.py::test_credits_offers_a_way_back_...` |
| W15 | Fixed: at 360 the phone labels had 1px padding, so the first and last pills sat 1px from the track; now 3px on both ends. Thumb edges are rounded as edges (left, right) rather than left plus width so both ends keep the same inset | browser `test_the_first_and_last_choice_of_a_tab_strip_keep_the_same_inset` (360 and 1280, FR) |
| W16 | Fixed: the swatches were `disabled` radios made grey by `filter: grayscale(1)`; they now keep their real colours dimmed (opacity .55, not-allowed cursor) and the group is tied to its reason with `aria-describedby` | browser `test_the_pending_colour_dots_keep_their_colours` |
| W17 | Fixed: the segmented track has a 5% ink tint over the secondary surface (solid base kept for the contrast rule) | `test_sky_contrast.py`, `test_stylesheet_structure.py` |
| W18 | Fixed in CSS: one 2px ring on the pill (`:focus-within`), none on the inner field; the native clear glyph is greyed like the search button. Not covered by a pixel test (the map needs tile mocking); the existing place-page tests pass | `test_browser_place_*` |
| W19 | Already done: the Flights chips are labelled with the direction only; Airlines chips fit at 360 (measured 294px, no clipping) | `test_audit4_fixes.py::test_the_flights_direction_chips_carry_a_label_and_no_count` |
| W20 | Fixed: every component family ends with "Back to the index" (index has an id); the page is long by design (a reference page) | `test_components_page.py` |
| W21 | Fixed: the pending count is the standard pill (`ui_components.pill_html`), the identification ring (and `health_rows.ring_html`) is gone, the rate stays in the verdict text | `test_status_pages_03.py` (updated) |
| W22 | Standardised: the Rename page now wraps its back link and card in the same `form-view` as the special-look forms, so the back link has the same gap to the form and the same left edge | browser `test_the_back_link_sits_the_same_way_...` |
| W23 | Info only (no defect): nothing to fix | n/a |

## Deviations

- [Rule 3] The upload CSRF token travels in the URL query because the handler reads the multipart
  body itself; query strings are stripped from the server log.
- Native lazy loading does not work with scripting off (measured), so NF-load is mitigated rather
  than eliminated for the no-JS case.
- W07 was measured as not defective (11px clearance); a small clearance increase was applied.

## Not done

- Performance findings of D54 (R01-R28) were not part of this plan's brief and were not touched.

## Self-Check
See the hand-back for the list of tests run.
