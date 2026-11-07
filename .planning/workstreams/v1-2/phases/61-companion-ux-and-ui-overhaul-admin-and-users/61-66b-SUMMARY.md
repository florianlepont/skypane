# Phase 61 Plan 66b: Force the Health, Device and Update pages onto the Fleet page Summary

`/health`, `/device`, `/update` and `/devices/<id>/health` now redirect (303) to the Fleet page of the frame they named, keeping `?frame=` and the one-shot `flash`; the retired page renderer, its route glue, its swap-registry entry and its script set are gone, and the roughly 230 tests that pinned those pages were migrated or, where they pinned only the retired page, deleted (list below).

**Requirements:** owner decision D44 (answered explicitly: force the redirect now); builds on plan 66 (P02 part) and its saved patch.

## What changed

- **Redirects.** `companion/fleet_moves.py` (`retired_frame_page`, `retired_update_page`) and `companion/routes.py`:
  - Administrator: `/health`, `/device`, `/devices/<id>/health` go to `/fleet?frame=<id>` (the frame named by `?frame=` among their own, else the one the request resolved to, else the System view). `/update` goes to the frame named by `?frame=`, else the first frame of the requested firmware type, with `flash` carried when it is shaped like a registered key. A firmware type with no frame is still served by the Update page, so the install confirmation and a type with no frame keep working.
  - Everyone else: `companion/legacy_pages.py` (`RETIRED_ADMIN_PAGES`, `retired_page_target`) and `Handler._frame_page_redirect` move an owner, co-manager or user to the replacement page of the named frame when it is one of their own (`/health` and `/update` to Home, `/device` to Display), else of their default frame, else the account page. A frame id that is not theirs stays the uniform 404. Anonymous visitors are unchanged (sign-in). The access matrix rows were updated honestly: those cells now assert the 303 and its target, not a 404.
- **Behaviour built on or kept on Fleet** (instead of losing it):
  - The Diagnostic LED quick switch script now loads on the Fleet page (the in-place switch with its error toast was a Device-page feature).
  - The System view shows the toast of a `?flash=` result (the resolved-airline results arrive there).
  - The airline resolve dialog's return target is now the System view (`/fleet?view=system`, `resolve_dialog.with_query` joins the `resolve=`/`flash=` parameters), so naming an airline, the artwork step, refusals that reopen the dialog and the stale-prefix flash all end where the dialog lives. The "See Health" toast link points at the System view.
  - The install confirmation page's Cancel link goes back to the Fleet view of the frame (not through a redirect).
  - Release rows lay out in columns by their own list width (`@container update-rows`) instead of the viewport, so they fit the narrow Fleet block at 1024 and 1280 px.
  - `.fleet-group .data-cards > .data-card` stacks its children (the registry card's "More details" disclosure was pushed past the right edge at 360 px in French on the System view).
- **Dead code removed.** `health_page.render` (the retired page's composition), the Health entry of `app._PAGE_SCRIPTS` and `_CONSOLE_FRAME_ROUTES`, the `health` swap registry entry (Python `ui_nav`, `layout.REFRESH_PAGE_HEALTH`, and `static/freshness.js`), the Health branches of the freshness token (`companion/freshness.py`), `health_page._NAV_HEALTH_TEXT`. `health_page.REFRESH_SWAP_SELECTORS` now resolves from the Fleet entry. The composition moved to `test-support/health_page_composition.py` so the render-level tests of the row, banner, registry and dialog builders (which the Fleet page still uses) keep their assertions unchanged; about 150 calls were re-pointed to it. No i18n string became unused: Health, Device and Update text is all rendered inside the Fleet blocks.
- **Kept on purpose.** `update_page.render` (fallback for a type with no frame, and the confirm page shell), `config_page` device scope (embedded in Fleet and the rejected-save re-render), the nav labels (`nav.health`, `nav.device`, `nav.update`) and `NAV_TABS`/`NAV_GROUPS` entries (still the vocabulary of titles, the referer allow-list and the tab-bar pinned by tests), the `/quick/led` POST redirect target `/device` (it now lands on Fleet through the redirect). `app.py` is 1477 lines.
- **Render baseline** regenerated (`test-support/companion_render_snapshot.py --write`, whose page list now samples `/fleet`, `/fleet?view=system`, `/fleet?flash=saved`).

## Tests

New: `companion/test_legacy_admin_page_redirects.py` (24 cases: each legacy URL for administrator, owner and user with `?frame=` kept, flash carried, other people's frames never targeted, unknown frame id a 404, anonymous to sign-in).

Re-pointed to `/fleet` (frame view, System view, or `/fleet?frame=<id>`), assertions unchanged unless listed below: test_admin_personal_scope, test_airline_manage_routes, test_battery_profile, test_brand_logo, test_browser_console, test_browser_console_shell (unchanged, passes through redirects), test_browser_frame_menu, test_browser_health_resolve, test_browser_phase44_walkthrough, test_browser_toasts, test_browser_update, test_browser_ux_01/02/03/04/quiet_wake/health_drawings, test_browser_charging_pill, test_browser_origin, test_browser_device_led_switch, test_browser_home_state_card, test_companion_app_03/04/04b/05, test_config_page_05, test_console_fleet_view, test_console_shell, test_device_dispatch/links/pages/routes/selector/scope_owner, test_display_detection_card, test_empty_state_scale, test_freshness_token, test_health_connection_row, test_health_fleet_status, test_health_resolve_dialog, test_i18n, test_nav_personal_console, test_page_context, test_page_scripts, test_poll_removal, test_place_map_assets, test_request_connections, test_retired_notifications, test_sessions_http, test_status_pages_04/07, test_toasts, test_update_actions, test_update_page, test_user_view_http, test_access_matrix (+ `matrix_rows_landing`), test_account_page, test_auth0_login, test_co_manager_access, test_device_actions, test_legacy_redirects, and the status-page render tests via the composition helper.

### Deleted or reduced tests

Deleted (file::test, reason):

- `companion/test_browser_update.py::test_js_confirm_dismiss_sends_no_request_registry_unchanged`: the native `confirm()` prompt on the Install button belonged to the Update page. The console design (UI-SPEC: no confirm dialogs) has the server confirmation page as the gate, and the Fleet page never carried the prompt script; the install flow tests still pin the confirmation page and the scheduled result, and the standalone fallback page (a type with no frame) keeps its prompt, pinned by `test_switching_type_shows_that_types_schedule_and_scheduling_is_independent`.
- `companion/test_device_pages.py::test_never_seen_device_has_no_health_nav_dot`: the per-frame Health navigation dot existed on the Health page only; the Fleet navigation dot is fleet-wide and the frame button's own status dot has different semantics (a never-seen frame shows a warning status).
- `companion/test_access_matrix.py::test_other_unprefixed_pages_are_not_redirected_for_a_user[/device]`: the opposite is now the rule; `/device` is a row of `LEGACY_PAGE_TARGETS` and is covered by the matrix cells and the new redirect tests.

Assertions removed inside migrated tests (purely about the retired page's layout or transport):

- `test_freshness_token.py`: Health halves of `test_new_device_health_row_changes_*`, `test_staleness_threshold_crossed_*`, `test_pipeline_run_meta_advance_*` (Home halves kept); the charging-pill token test now pins the Home token and the Fleet page's pill (the Fleet page is refetched whole on every tick, it carries no ETag, pinned by `test_fleet_and_airlines_carry_neither_etag_nor_refresh_token`); the off-box marker and language-cookie token tests now run on Home.
- `test_status_pages_07.py::test_both_tabs_ok_end_to_end`: the nested-section, prose-table, `desc` cell count and stats ordering assertions of the Health page layout.
- `test_browser_ux_health_drawings.py::test_every_health_row_aligns_in_the_fleet_state_block` (was `..._cards_share_one_width_...`): the "all cards share one column width" part; row alignment kept; row count floor 5 to 3 (the State block has three rows).
- `test_user_view_http.py`: the "Server & data" heading (the System view groups by topic).
- `test_page_context.py::test_health_markup_builds_only_on_the_fleet_page`: `/fleet` builds two page contexts (shell and selected frame), so two `health_signals()` calls instead of one; the other tab routes still assert exactly one.

## Deviations from Plan

**1. [Rule 2 - missing critical behaviour] Fleet page lacked the quick-switch script.** Found when migrating the quick-switch error-toast test; added to `console_fleet_view.page_scripts`. The confirm-prompt script was deliberately not added (UI-SPEC), see the deleted test above.

**2. [Rule 1 - layout bugs on the Fleet blocks]** Update release rows overflowed the narrow Fleet block at 1024 to 1280 px (viewport media query); the registry card's disclosure overflowed at 360 px in French. Both fixed in `style.css`.

**3. Non-administrator behaviour.** The plan said non-admins land on their equivalent page; `/devices/<id>/health` and `/devices/<id>/device` therefore also move an owner or co-manager of that frame (no longer a 404). Frames that are not theirs remain the byte-identical unknown-path 404.

**4. Remaining Health-only builders.** `_server_group_html` and the `SCREEN_SECTION_*`/`SERVER_DATA_SECTION_*` constants are now used only to compose the old arrangement in the test helper (the System view uses the topic builders). Removing them means rewriting about 15 render-level tests; left as a follow-up.

## Verification

Gates: ruff, mypy, comment-history, function-size (931 functions, none over 80), `stub-server/test_phase47_freeze.py` (21 passed). Full companion + test-support + stub-server suite with `-n auto`: 8475 passed, 4 skipped (root permission skips), 0 failed.

## Known Stubs

None.
