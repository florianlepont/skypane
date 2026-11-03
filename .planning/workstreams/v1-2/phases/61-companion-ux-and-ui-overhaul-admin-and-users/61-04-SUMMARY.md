---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 04
subsystem: companion
tags: [navigation, console, my-views, space-switch]
requires: [61-03, 61-14]
provides: [Console and My views navigation spaces, admin space switch, user bar without Health, Locations 360px fix]
key-files:
  created:
    - companion/test_nav_spaces.py
    - companion/test_browser_nav_spaces.py
  modified:
    - companion/ui_nav.py
    - companion/ui_shell.py
    - companion/layout.py
    - companion/static/style.css
    - companion/i18n_fr/nav.py
    - companion/i18n_fr/admin_shell.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 04: Navigation spaces Summary

Navigation is now two admin spaces chosen from the page being rendered (`ui_nav.current_space`): the Console (Fleet, Users, Locations, Audit, More with Releases, My views, Account) and My views (Home, Display, Flights, Health, More with Airlines, Device, Account, Console). Users get Home, Flights, Display, Account with no Health and no admin words. The Admin tab, the unexplained More marker and the Update link in the frame sidebar are gone.

## Commit

- e8c5252: single atomic commit for the three tasks (nav model, CSS and header, tests are entangled and the suite must stay green per commit).

## What changed

- `ui_nav.py`: `_Entry` model, `current_space`, per-space bar, More sheet and sidebar builders, `space_switch_html` (admin principals only, label names the destination, aria-label states the intent, plain GET to `/` or `/fleet`). Health severity dot only on the Health bar cell (My views) and Health sidebar link. User sidebar: frame pages, Locations, Account last.
- `ui_shell.py`: `{space_switch}` slot in the phone header between wordmark and gear.
- `style.css`: `.space-switch` rules (44px, accent, header gap tightened with `:has`), `.fleet-form` / `.fleet-confirm__form` inputs and selects `max-width: 100%`, `.section-subnav` rules removed (`.filter-chip--current` kept, the audit filters use it).
- FR: `nav.fleet` is "Flotte"; new `nav.audit_short`, `nav.my_views`, `nav.console`, `nav.switch_to_my_views`, `nav.switch_to_console`; `nav.admin` removed.
- Owner ledger rows 1, 5, 6: defaults applied (no owner answers recorded).

## Deviations from Plan

1. **[Scope] Language, theme and Sign out are not repeated in the More sheet.** Existing pinned tests require exactly two theme/language forms per page (sidebar plus gear panel), and the phone gear panel already carries all three. The More sheet holds the link entries only.
2. **[Rule 1 - Test fallout] Pinned outputs moved deliberately:** `render_baseline.json` regenerated; the four no-principal shell/error-page digests in `test_sign_in_surfaces.py` updated (their sidebar now follows My views: Account added, Update removed). Tests that iterated `NAV_TABS` or asserted the old Advanced group/Admin tab/Update link (`test_companion_app_01/02`, `test_update_page`, `test_device_links`, `test_user_view_http`, `test_user_nav`, `test_console_shell`, browser update/console/auth0 tests) were rewritten in place to the new structure; none disabled.
3. **Principal-less renders** (login-adjacent pages, unit tests) follow the My views layout without the switch, or the Console layout for console slugs.
4. Admin `/account` is treated as My views (personal route), so Console's Account link lands in the My views bar.
5. The `/update` page title stays "Update" (comes from `ui_base.NAV_TABS`, outside this plan's files); the Console nav entry reads "Releases" / "Versions".
6. `NAV_GROUPS`/`NAV_TABS` in `ui_base.py` are untouched (still used by routing and device scoping); only the renderers stopped using them. `layout._nav_groups` and `_nav_links` re-exports were removed.

## Known stubs
None.

## Gates
ruff, mypy (28 modules), check_comment_history, check_function_size, test_phase47_freeze (21 passed) clean. Companion plus test-support suite with `-n auto`: 5777 passed, 3 skipped (the pre-existing root-permission skips; no browser skips). The Locations browser test was confirmed to fail without the CSS fix.

## Self-Check: PASSED
