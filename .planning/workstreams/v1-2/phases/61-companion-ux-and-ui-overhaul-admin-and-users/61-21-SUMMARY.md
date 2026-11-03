---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 21
subsystem: companion
tags: [navigation, console, personal-space, i18n, sprite]
requires: [61-19, 61-20]
provides: [one personal nav builder, one Console nav builder, Frame tools group, Health/Device/Airline editor in the Console, new nav labels EN/FR, four sprite glyphs]
key-files:
  created:
    - companion/test_nav_personal_console.py
  modified:
    - companion/ui_nav.py
    - companion/ui_base.py
    - companion/console_routes.py
    - companion/app.py
    - companion/device_dispatch.py
    - companion/layout.py
    - companion/i18n_fr/nav.py
    - companion/pages/history_page.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 21: Two navigation sets

An administrator and a user now see one personal navigation (bar Home, History, Location, Style, More; sidebar Home, Flight history, Location and detection, Personalisation, Airline collection, Account), and the Console holds Fleet, Users, Health, Device and the Airline editor, with Health, Device and the editor scoped to the frame in view.

## Commit

- 2235454: all three tasks together, one green commit (as the plan requires). This summary follows in its own docs commit.

## What changed

- **ui_base.** Labels: Flight history, Location and detection, Personalisation, Airline collection (own message ids, see deviation 1), short bar labels in `NAV_SHORT_LABELS` (History, Location, Style), `FRAME_TOOLS_LABEL`, `AIRLINE_EDITOR_LABEL`/`ROUTE`, `DETECTION_ROUTE`. `NAV_TABS` is Home, Flight history, Location and detection, Personalisation, Airline collection, Health, Device, Releases (so `page_routes()` and the `?device=` redirect cover /detection). Sprite gains icon-shield, icon-locate, icon-star, icon-chevron-down (46 glyphs). `NAV_ICON_IDS["detection"]` is icon-locate. The "Advanced" group label is gone.
- **console_routes.** Entries Fleet, Users, Health, Device, Airline editor, Audit log, Releases.
- **ui_nav.** `_personal_bar`, `_personal_sidebar_parts`, `_console_bar`, `_console_sidebar_parts` replace the user, My views and old Console builders; `MY_VIEWS_SPACE` is now `PERSONAL_SPACE`. `current_space` returns the Console for fleet, users, audit, update, health, device, airlines/manage. The Health dot renders only on the Console Health cell and link. A signed-in principal sees personal frame pages only while the scope holds a frame (a user with none: no bar, Account-only sidebar; an administrator with none: a bar with More only). Console frame hrefs use `device_scope.scoped`. The More-sheet switch row carries `mobile-nav__link--space`.
- **app.py / device_dispatch.** /detection and /airlines/manage use their own nav slug (`detection`, `airlines/manage`) instead of a parent tab; the airline editor tab title reads "Airline editor"; the editor is accepted as a Referer return target.
- **i18n.** FR entries for the new labels; `nav.my_views`, `nav.advanced`, `nav.switch_to_my_views`, `nav.flights` removed; new `nav.my_frame`, `nav.switch_to_personal`.
- **style.css.** `.tab-bar__more-panel` gets `width: max-content` and a viewport cap so the longest French row ("Éditeur de compagnies") stays on one line.

## Tests

New `companion/test_nav_personal_console.py` (21 tests, real in-process requests, EN and FR): personal bar, More sheet and sidebar equal for administrator and user except the switch row; Console bar, sheet and sidebar lists for fleet/users/audit/update; Console frame pages render in the Console chrome un-prefixed and under `/devices/<id>/`; no Console links, Locations or dot in the personal navigation; no admin words in a user's navigation; "My views", "Mes vues", "Advanced", "Avancé" absent from every served page; Flight history label and title; frameless user.

Browser (`test_browser_nav_spaces.py`, 42 tests, Chromium, not skipped, run 3 times in a row green): both bars have five equal cells (within 1px, 44px minimum, no wrapped or clipped label, no overflow) at 360px in EN and FR, light and dark; desktop sidebars list the spec links with 44px hit boxes.

Existing tests changed in place (intent kept, expectations moved to the new sets): test_companion_app_01/02/04/04b, test_status_pages_05/07, test_nav_spaces, test_user_nav, test_console_shell, test_update_page, test_device_links, test_device_pages, test_device_routes, test_device_selector, test_page_context, test_access_matrix, test_user_view_http, test_view_pages_01/03/04, test_i18n (identical-in-French allow-list gains `nav.display_short`), and the browser files test_browser_console, test_browser_console_shell, test_browser_update, test_browser_overhaul_steps, test_browser_overhaul_sweep (shared-word list gains "Style"), test_browser_detection, test_browser_auth0. `render_baseline.json` regenerated (diff reviewed: only navigation markup, sprite, titles, the `/login?next=%2Fdetection` redirect and the dot-suffix text moved) and the two sign-in digests (`nf`, `nf2` now equal because the personal chrome has no dot, `forb`, shell digest) moved in the same commit. `update_page_one_type_golden.json` did not move.

## Deviations from Plan

1. **[Rule 3] Own message ids for the changed labels.** `nav.flights`, `nav.display`, `nav.airlines` are also the page headings (`config_page`, `airlines_page`, outside this plan's files) and `i18n.msg` refuses one id with two English texts. The nav labels use new ids `nav.flight_history`, `nav.personalisation`, `nav.airline_collection`; the page headings of Display and Airlines are left for their own plans. Consequence: the tab title of /display now reads "Personalisation" and of /airlines "Airline collection" while their headings still read "Display" and "Airlines" until those plans land.
2. **A6 step count.** The spec puts Audit log in the Console More sheet (UI-SPEC 1.3) while section 14 says A6 stays at 1. The bar cannot hold both, so A6 is now 2 taps (More, Audit log); the step test target moved from 1 to 2 and `61-STEP-COUNTS.md` notes it. The orchestrator may want to reconcile the spec.
3. **Language, theme and Sign out stay in the gear panel and sidebar footer** (carried deviation from the plan text); the More sheet lists link rows only.
4. **No new `.nav-group` CSS.** The existing `.nav-group` and `.nav-group__label` rules already style the Frame tools group.
5. **Frame requirement.** The "personal pages only while a frame is in scope" rule applies to signed-in principals; a bare render with no principal (unit tests, pre-auth shells) lists the personal pages unscoped as before.
6. **Test helper exemptions.** The space switch leads to "/" (resolved by the server to the administrator's own frame), so the prefix crawl tests in test_device_links and test_device_routes skip `.space-switch` and `.mobile-nav__link--space` nodes.
7. **Health dot on a 404.** An authenticated 404 uses personal chrome, so it no longer carries the dot; the three tests that asserted it now assert the personal navigation has none and that a Console page shows it.

## Gates

- ruff, mypy (28 modules), `check_comment_history.py check`, `check_function_size.py` (none over 80): clean. `stub-server/test_phase47_freeze.py`: 21 passed.
- Full `companion test-support stub-server -n auto --no-cov` after the final code edit: 6802 passed, 4 skipped (root permission-bit tests, pre-existing), 0 failed.
- Not run: `./scripts/run-all-tests.sh` (not the last code plan).

## Known Stubs

None.

## Threat Flags

None. T-61-21-01 (a user's navigation lists only routes a user can open; forbidden-word tests in EN and FR), -02 (frame hrefs from `device_scope.scoped`, labels escaped), -03 (dot only in the Console bar and sidebar) are covered by test_nav_personal_console.py.

## Self-Check: PASSED
