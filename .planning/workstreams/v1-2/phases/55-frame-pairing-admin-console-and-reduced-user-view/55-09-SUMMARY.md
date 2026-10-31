---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 09
subsystem: companion-console
tags: [throttle, audit, flash, routes, navigation, access-matrix]
requires: [55-02, 55-04, 55-08]
provides:
  - companion/throttle.py LockoutThrottle
  - companion/audit.py actor_for, record_in, record_standalone
  - companion/console_flash.py register_flash, queue_flash, take_flash, clear_cookie_header
  - companion/route_types.py (Route, Access, Exact, PrefixSuffix, RouteMatch, policy constants)
  - companion/console_routes.py (path constants, ROUTES aggregator, CONSOLE_NAV_ENTRIES, section_subnav_html)
  - four skeleton route modules and four matrix row seams
  - Handler._console_page, Administration sidebar group, phone Admin tab
affects: [55-10, 55-11, 55-12, 55-13]
tech-stack:
  added: []
  patterns:
    - console route modules import companion.route_types, never companion.routes (which imports the aggregator)
    - nav links derive from routes.match("GET", path), so a link exists only while its page does
key-files:
  created:
    - companion/throttle.py
    - companion/audit.py
    - companion/console_flash.py
    - companion/route_types.py
    - companion/console_routes.py
    - companion/console_pairing.py
    - companion/console_lifecycle.py
    - companion/console_users.py
    - companion/console_locations.py
    - companion/i18n_fr/admin_shell.py
    - test-support/matrix_rows_pairing.py
    - test-support/matrix_rows_lifecycle.py
    - test-support/matrix_rows_users.py
    - test-support/matrix_rows_locations.py
    - companion/test_console_utils.py
    - companion/test_console_shell.py
    - companion/test_browser_console_shell.py
  modified:
    - companion/routes.py
    - companion/app.py
    - companion/ui_nav.py
    - companion/pages/update_page.py
    - companion/static/style.css
    - companion/test_access_matrix.py
    - companion/test_i18n.py
    - companion/test_user_nav.py
    - companion/testdata/render_baseline.json
key-decisions:
  - "layout.py was not touched: NAV_TABS is unchanged and no concrete need arose."
  - "Admin phone tab rule: the Admin tab replaces the last frame tab (Airlines), which moves to the front of the More sheet, so the bar keeps its five cells."
requirements-completed: [AUTH-04, AUTH-05]
duration: ~2h
completed: 2026-10-31
---

# Phase 55 Plan 09: Console seams Summary

Throttle, audit and flash helpers, the console route aggregator with four empty route modules, the page shell method, admin navigation (Administration group, Admin tab, section sub-nav, Releases entry) and per-plan access-matrix row seams are in place; no console page or action exists yet.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | f41a8ca | `LockoutThrottle`, `audit` helpers, `console_flash`, 22 tests (real 8-thread race) |
| 2a | 60da8ef | `route_types`, `console_routes`, four skeleton modules, `routes.py` wiring, matrix row seams and merge, sub-nav CSS, French strings |
| 2b | f1ae9d0 | `Handler._console_page`, Administration group, Admin tab, `/update` sub-nav, shell tests, browser test, baseline regeneration |

Task 2 was split into 2a and 2b as the plan checker allowed.

## Verification

- Full non-browser suite (`companion server test-support scripts stub-server -m "not browser"`): 5917 passed, 7 skipped (root-permission skips, pre-existing).
- Browser suite (`companion -m browser`, chromium symlink dir in the scratchpad for the 1243/1248 mismatch): 562 passed, including the 5 new console-shell tests (390 and 360 px: five tab cells, each at least 44 px, no sideways scroll; sub-nav at most two lines with 44 px chips; 1280 px: sub-nav hidden, Administration group visible).
- `ruff check .`, `mypy` (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (814 functions): clean.
- `git diff` of `companion/layout.py` across the plan: empty (`NAV_TABS` unchanged).

## Deviations from Plan

1. **[Rule 3 - Blocking] New `companion/route_types.py`.** `routes.py` imports `console_routes`, and plans 10 to 13 need `Route`, `Exact`, `ADMIN_ONLY` in their route modules; importing `routes` from them would be a cycle that breaks depending on import order. The route vocabulary moved verbatim into `route_types.py`; `routes.py` re-exports every name, so `routes.Route`, `routes.Exact`, `routes.ADMIN_ONLY` and the rest behave as before. Plans 10 to 13 must import `companion.route_types`.
2. **[Rule 1] Test file rename.** `companion/test_console_helpers.py` became `companion/test_console_utils.py`: guard G9 rejects a `*_helpers.py` test module.
3. **Matrix tests placed in `test_access_matrix.py`.** The shell test module cannot import another test module (guard G12), so the dummy-route-without-a-row and row-module-merge tests live in `test_access_matrix.py`.
4. **Small CSS block (`.section-subnav`, `.filter-chip--current`).** The sub-nav needs links (it must work without a script, unlike the radio chips, which `.js-gate` hides) and must be hidden from 960px; neither exists in the stylesheet. Only existing tokens and the existing chip classes are reused: no new token, no new accent consumer.
5. **Sub-nav needs two pages.** `section_subnav_html` returns "" while fewer than two console pages exist, so `/update` is unchanged until Fleet exists (one chip is not navigation). With the skeleton, the sub-nav does not render anywhere.
6. **Administration group with only Releases changes every admin page today.** The plan requires the group to list only Releases while the console pages are missing. This adds the group to 44 captures in `render_baseline.json` (checked: every difference is exactly that one `<div class="nav-group">` block, English and French) and `test_user_nav.py::test_admin_navigation_is_unchanged` became `test_admin_navigation_only_gains_the_administration_group`. Releases is not marked current in the group when the Advanced group's Update link already is, so a page never has two `aria-current` links.
7. **`LockoutThrottle` extras.** Partial failure counts lapse after `lockout_s` without a new failure; a failure while locked does not extend the lockout; `key_count()` exists for tests. `locked_for` rounds up to whole seconds.
8. **Flash API shape.** `queue_flash(key, **params)` returns the `Set-Cookie` value (pass it to `Handler.redirect(set_cookie=...)`); `take_flash(cookie_header)` returns `(markup, clear_cookie_or_None)`; `Handler._console_page(route, title_msg, body_html, purpose_msg=None)` already calls it and sets the clearing cookie. Parameters use `{name}` placeholders filled with a regex substitution (no format-string evaluation) and are capped at 8 parameters of 120 characters.
9. `test_i18n.py` allowlist gained `nav.administration` and `nav.admin` (French cognates identical to English).

## Notes for plans 10 to 13

- Console route modules: `from companion import route_types`; `ROUTES = (route_types.Route("POST", route_types.Exact(...), handler, route_types.ADMIN_ONLY, csrf=True), ...)`. Handlers are `handler(h, m)`; pages call `h._console_page(console_routes.FLEET_ROUTE, None, body, purpose_msg)`. The page header comes from `_console_page`, so a page body must not add its own `layout.page_header`.
- Register flash keys at import with `console_flash.register_flash(key, tone, title_msg, detail_msg)`.
- Fill only your own `test-support/matrix_rows_<name>.py` (`ROWS` keyed `(method, template)` to `public`, `signed-in`, `admin-only` or `owner-device`; `SAMPLES` for templated paths). Console routes are not device-scoped.
- The throttle is in memory and per process: a companion restart clears every count and lockout (to state in the hand-off).

## Known Stubs

None (the four route modules are intentional empty skeletons, filled by plans 10 to 13).

## Threat Flags

None beyond the plan's threat model (T-55-09-01 to -06 covered by the flash, audit, throttle, matrix and nav tests).

## Self-Check: PASSED

Files present: companion/throttle.py, companion/audit.py, companion/console_flash.py, companion/route_types.py, companion/console_routes.py, companion/test_console_shell.py, companion/test_browser_console_shell.py. Commits f41a8ca, 60da8ef, f1ae9d0 exist.
