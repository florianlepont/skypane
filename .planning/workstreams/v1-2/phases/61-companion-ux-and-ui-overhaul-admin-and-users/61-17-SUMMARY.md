---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 17
subsystem: companion
tags: [access, routes, console, locations, home]
requires: []
provides: [ADMIN_DEVICE access kind, GET /airlines/manage, admin-only Health and airline writes, /locations redirect, ledger R2-1..R2-18]
key-files:
  created:
    - companion/test_airline_manage_routes.py
    - test-support/matrix_rows_admin_frame.py
    - test-support/locations_page_support.py
  modified:
    - companion/route_types.py
    - companion/routes.py
    - companion/app.py
    - companion/pages/airlines_page.py
    - companion/pages/home_page.py
    - companion/pages/locations_page.py
    - companion/console_locations.py
    - companion/console_routes.py
    - companion/ui_nav.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 17: Admin-only Health and Airline editor Summary

Health, the new `/airlines/manage` editor and the five airline POST routes are now `ADMIN_DEVICE` (administrator only, reachable on any frame through `/devices/<id>/`); `/locations` is a redirect to Fleet; Home has no Health link; the ledger carries R2-1..R2-18.

## Commits

- 9cbbd24: all three tasks together (as the plan requires, one green commit).

## What changed

- **Access kind.** `route_types.ADMIN_DEVICE = Access(ADMIN, DEVICE_ARG)`, re-exported by `routes`; `access.py` is unchanged. Owner and co-manager get the unknown-path 404 before any device lookup; anonymous is sent to sign-in.
- **Routes.** `GET /health`, `GET /airlines/manage` (new, device-scoped, same body and scripts as the old `/airlines` editing page, `/airlines` stays the active tab), the resolve, rename, rename-reset, manual-delete and illustration-replace POSTs. The illustration image GET stays `OWNER_DEVICE`. `/airlines?resolve=<p>` is a 303 to the same frame's `/airlines/manage?resolve=<p>` for an administrator (value re-encoded with `urlencode`); for anyone else the parameter is ignored. The un-prefixed `/health` is no longer in `_USER_FRAME_PAGES`, so a user gets a 404 instead of a redirect to their frame.
- **Locations.** GET handler is a fixed 303 to `/fleet`, route access `ADMIN_ONLY` (user 404, anonymous sign-in). POST routes, csrf, audit and the refused-submission page are unchanged. The Console nav entry, title, bar key, icon and user-sidebar branch are removed.
- **Home.** The See Health pill (function, CSS, FR string) and the attention toast's Review status link (string) are gone for every role. The amber-dot notification is plan 61-34.
- **Ledger.** `61-OWNER-DECISIONS.md` has "Revision 2 open items (16)" with R2-1..R2-18; R2-10 reads "owner answered (D21)".

## Deviations from Plan

1. **[Rule 1 - Bug] Dead links to /locations.** The Display page's location picker linked to `/locations` ("Manage locations" / "Add a location"), which is now a 404 for users. Both links and their two strings (EN message and FR entry) are removed; the select and the "No location chosen." note stay. `test_location_picker.py` updated.
2. **[Rule 1 - Bug] Field errors of a refused location submission were not translated** (resolved before the request language was set). They are now stored as messages and translated at render. Exposed because the page is now reached only through a refused POST.
3. **Browser tests for the Locations page.** The page has no address, so `test-support/locations_page_support.py` opens it by submitting a blank add from Fleet, as a form would; the sweep, nav-space and console touch-target tests use it. The no-script Locations add flow in `test_browser_console.py::test_console_works_with_scripts_blocked` is replaced by an assertion that `/locations` lands on Fleet (there is no add UI to drive).
4. **Home pill hit-area test** (`test_the_home_health_pill_has_a_44px_hit_area_on_desktop`) is converted to assert the overdue Home card has no pill and no `/health` link (its subject was removed).
5. **Console bar is four cells**, not five (Fleet, Users, Audit, More): the two "five cells" browser tests now say four.
6. **Render snapshot harness.** `GET /airlines/manage` added to its unauthenticated route list. Baseline diff reviewed: only the four Releases pages lose the Locations nav entry, plus the new unauthenticated row. Home bodies did not change (the pill only rendered in warn states the baseline does not cover). The shell digest in `test_sign_in_surfaces.py` moved to `42f60119...` for the same reason (Locations link gone from the Console nav in the `update` shells; verified by diffing old and new shells).

## Files updated (tests and support)

test_access_matrix, test_route_table, test_console_locations, test_console_shell, test_nav_spaces, test_user_nav, test_sign_in_surfaces, test_empty_state_scale (Locations case now through a refused submission), test_toasts, test_device_links, test_device_routes, test_device_scope_owner, test_co_manager_access, test_user_view_http, test_home_state_card, test_view_pages_04, test_location_picker, test_browser_console, test_browser_console_shell, test_browser_nav_spaces, test_browser_overhaul_sweep, test_browser_home_state_card, test_browser_health_resolve, matrix_rows_landing, matrix_rows_locations, matrix_rows_admin_frame (new), companion_render_snapshot.

## Gates

- ruff, mypy (28 modules), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`: clean.
- `stub-server/test_phase47_freeze.py`: 21 passed, unchanged.
- Full `companion test-support stub-server -n auto --no-cov`: 6649 passed, 4 skipped (root permission-bit tests, pre-existing), 3 failed; the 3 (two picker French tests, one Home attention test) were fixed afterwards and re-run green together with the neighbouring files. No full re-run after those three test-only edits.

## Known Stubs

None.

## Threat Flags

None. T-61-17-01..03 are mitigated and covered by `test_airline_manage_routes.py` and the matrix rows.

## Self-Check: PASSED
