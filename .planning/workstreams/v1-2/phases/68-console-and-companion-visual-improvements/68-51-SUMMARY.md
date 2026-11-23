# Phase 68 Plan 51: Remove the legacy web-UI routes, equal dialog buttons, Account rename pencil Summary

Owner decisions of 2026-11-23: (A) delete the old redirect-only routes, (B) Save and Cancel of compact dialogs exactly as wide as each other, (C) a Rename pencil on every Account frame row, (D) no "Rename this frame" link in access management.

## A. Route inventory (companion web UI only)

| Address | What it was | Decision |
|---|---|---|
| `GET /health`, `GET /devices/<id>/health` | 303 to the frame's Battery view (System view with no frame) | Removed (route, access row, `retired_frame_page`, `health_target`) |
| `GET /device`, `GET /devices/<id>/device` | 303 to the frame's Settings tab | Removed |
| `GET /fleet?view=health` | 303 to Battery / System (`retired_health_view`, called from `handle_fleet_get`) | Removed; the query is now an unknown view and the Fleet page renders normally |
| `GET /devices/<id>/update` | 303 to the frame's Versions page (special case in `routes.match`) | Removed (404) |
| `GET /history`, `GET /preview` (+ prefixed) | 303 to Flights | Removed, with the `HISTORY_LEGACY_ROUTE`/`PREVIEW_PAGE_ROUTE` constants |
| `GET /display/screen`, `GET /display/layout` (+ prefixed) | 303 to Style (`RETIRED_VIEW_ROUTES`) | Removed, with `DISPLAY_SCREEN_ROUTE`/`DISPLAY_LAYOUT_ROUTE` |
| Non-admin "retired admin page" moves for `/health`, `/device` (`legacy_pages.RETIRED_ADMIN_PAGES`), Health/Device nav-tab entries, console nav entries, icon/slug maps, `nav.health` FR string, page_styles `/history` | Supporting code of the above | Removed (the table keeps `/update` only) |
| `GET /update` | 303 to the frame's Versions page, **but** also serves the Update page itself for a firmware type with no frame (`_update_flash_url` sends install/cancel results there) | **Kept**: live fallback, not a pure redirect |
| `GET /settings` | 303 to Style; it is the GET twin of `POST /settings`, so `reopen_address` offers the "open the page again" link after a refused (CSRF) settings form | **Kept**: CSRF reopen mechanism |
| `GET /devices/<id>/frame/name` | Rename address: 303 to the page with the dialog fragment; GET twin of `POST .../frame/name` for the CSRF reopen link of the Rename dialog | **Kept**: CSRF reopen mechanism (owner decision: drop the GET route and its two matrix rows if the reopen link may stay broken for Rename) |
| `POST /quick/led` | Returned to `/device`; the form's `return_to` value `/device` is also the settings form's scope identifier | Kept; the redirect now goes to the frame's Fleet settings tab (`/fleet?frame=<id>&tab=settings`), whatever `return_to` says |
| Settings-form `return_to=/device` identifier, `DEVICE_ROUTE` constant, `device` fold slug | Not a route: names the Device form scope and its refused-save redraw (needs a title and the Fleet space) | Kept |
| Overflow link of the Airlines gap line (was `/health`) | A live link to a removed route | Re-pointed to `/fleet?view=system` |

Not touched, by the hard limits: BYOS, OTA, display, setup/pairing endpoints, `/login`, `/login/auth0`, `/callback`, `/logout`, static assets, exports, all POST routes, the CSRF reopen mechanism. Deploy probes (`deploy/activate.sh`, `deploy/README.md`, Caddyfile, units) only use the device protocol path `/device/v1/display`, which is not a companion route and is unchanged; no probe uses a removed route. No docs outside the project skill reference mentioned the removed redirects (updated `.claude/skills/sketch-findings-skypane/references/page-patterns.md`).

### Rows and tests removed

- `companion/test_access_matrix.py` ROUTE_POLICY: GET `/display/layout`, `/display/screen`, `/device`, `/history`, `/preview`. DEVICE_SCOPED: the same five plus GET `/health`. `test-support/matrix_rows_admin_frame.py`: GET `/health`. `test-support/matrix_rows_landing.py` LEGACY_PAGE_TARGETS: `/history`, `/preview`, `/display/screen`, `/display/layout`, `/health`, `/device` (keeps `/settings`, `/update`). `test_device_routes.EXPECTED_DEVICE_SCOPED`: the same six (50 to 44). `test_route_table`: `/device` and `/health` expectations. Route table: six GET routes removed, nothing added; the matrix changed only by these rows.
- Deleted tests (behaviour removed on purpose): `test_a_retired_admin_page_moves_its_owner...` and `test_the_retired_update_page_under_a_prefix...` (access matrix), the `/health`/`/device` redirect, view=health and frame-prefix tests in `test_legacy_admin_page_redirects.py`, `test_preview_redirects_to_flights`, `test_preview_redirect_ignores_query_string`, `test_unauth_get_preview_redirects...`, the `/history` and `/preview` cases of the legacy-redirect and device-prefix tests, `test_the_retired_update_page_alone_answers_under_a_prefix`.
- Adapted to the new behaviour (404 instead of 303, or pointed at a live page): the same files plus `test_companion_app_01/02/04`, `test_co_manager_access`, `test_console_fleet_view`, `test_console_shell`, `test_device_dispatch`, `test_device_scope(_owner)`, `test_device_settings` (LED redirect), `test_account_page`, `test_auth0_login`, `test_fleet_connection_tile`, `test_frame_sheet`, `test_frame_switcher`, `test_freshness_token`, `test_nav_spaces`, `test_personalisation_*`, `test_request_connections`, `test_status_pages_05/06/07`, `test_system_route_sources`, `test_update_page`, `test_user_health`, `test_user_view_http`, `test_view_pages_04`, `stub-server/test_auth_independence.py`, `test_sign_in_surfaces` (shell digest recomputed: the Health and Device shells left the list; every remaining shell is byte-identical to HEAD, checked against a HEAD export), and the browser files that opened `/health`, `/device` or `/history` (they now open the frame's Battery or Settings view or `/flights`). New tests assert the removed addresses answer the ordinary 404 for every role, including under a frame prefix.
- `render_baseline.json` regenerated once at the end; `computed_style_snapshot.py` and `measure_efficiency.py` no longer visit the removed pages.

### Wording for ROADMAP criterion 5 (not edited)

Replace "...the retired Health and Update addresses still answer a 303 and now land on the frame's Battery and Versions pages." with: "...the retired Health, Device, History, Preview, Display Screen and Display Layout addresses, the Fleet `view=health` query and the frame-prefixed Update address are removed and answer the ordinary not-found page; only `/update` (live fallback for a type with no frame), `/settings` and the Rename address (twins of POST routes, kept for the CSRF reopen link) still answer a 303."

## B. Equal Save and Cancel

Cause: the submit button has a 1px border and the Cancel link had none on pages that do not load the admin sheet, so with equal flex basis the two differed by 2px. The shared compact-dialog rule in `style.css` now gives the dismiss link the same 1px border, glass background and radius on every page. Buttons stay side by side on phone and desktop (the existing sheet design; not stacked). Browser tests: Rename dialog (all entry points, 360 and 1280, EN/FR, tolerance now 0.5px) and a new Users invite dialog test at 1280 EN/FR.

## C and D. Account rename pencil

Each owned frame row on Account has a 44px pencil icon button (`icon-pencil`, aria-label "Rename: <frame>" / "Renommer : <frame>", new string `account.rename_frame_aria`) before the key; co-manager rows keep the door only (same rule as the Home pencil: owner or administrator, not co-managers). It is a hash link to the Rename dialog now rendered with the row's dialogs (works without script). The "Rename this frame" link and its CSS and strings (`co_managers.rename_frame`) are gone from the Manage access sheet; Remove this frame and Leave are unchanged. Tests: `test_browser_account_frames.py` (two icon buttons for an owner, one for a co-manager, tap size, no overlap, fits at 360/1280 EN/FR), `test_browser_frame_rename_dialog.py` (entry points: Home, Fleet, Account row pencil), `test_frame_rename_and_users_switch.py`. Captures: scratchpad `p51/{before,after}/` (Account at 390 and 1440, EN/FR, light; `after/` also shows the dialog opened from the pencil).

## Deviations

- Rule 1: the LED quick switch returned to `/device`; redirected to the Fleet settings tab instead. A refused device-settings save redraws under shell route `/device`, which needed a page title and the Fleet space (`_CHILD_PAGE_TITLES`, `_FLEET_FOLDED_SLUGS`); the Airlines overflow link pointed at `/health`.
- The baseline was regenerated once, after the Account change.

## Deferred

- `test_browser_page_opening.py::test_the_sections_of_a_frame_enter_in_order_on_a_phone` fails identically on the plan-50 HEAD (the anchors row enters with delay 0 instead of 60); not caused by this plan, left untouched.

## Verification

Core group run (`SKYPANE_TEST_GROUP=core`, 12385 passed, 6 failed, all six fixed afterwards and re-run: Account pencil expectations, owner route count 31 to 27, console space of the device-settings redraw), then the touched non-browser and browser files again; ruff, mypy, function-size, comment-history clean; `companion/app.py` 1491 lines.

## Owner decisions needed

- `/update`, `/settings` and `/devices/<id>/frame/name` kept (see inventory). Say whether to accept a broken reopen link after a CSRF-expired Rename or settings save, which would let the last two go too.
- Compact dialog buttons stay side by side on phones (not stacked).
