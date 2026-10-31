---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 01
subsystem: companion
tags: [auth, roles, reduced-user-view, navigation, health]
requires: []
provides:
  - companion/user_view.py role helpers (is_user_view, platform_visible, sanitise_settings_form, frame_only_severity, frame_only_anomalies, reduce_signals)
  - role-conditional Display, Home, Health and user navigation, ready for the route flip in plan 04
affects: [55-04, 55-06]
tech-stack:
  added: []
  patterns:
    - role read at render time from prefs.current_principal(); no new route-lambda parameters
    - health signals reduced once in the page-context loader so nav dot, banner, Home row and freshness token agree
key-files:
  created:
    - companion/user_view.py
    - companion/test_user_view.py
    - companion/test_user_health.py
    - companion/test_user_nav.py
  modified:
    - companion/app.py
    - companion/page_context.py
    - companion/freshness.py
    - companion/pages/config_page.py
    - companion/pages/home_page.py
    - companion/pages/health_page.py
    - companion/ui_nav.py
    - companion/ui_shell.py
    - companion/i18n_fr/nav.py
key-decisions:
  - "User nav links are emitted only for GET routes whose min_role is at most user, so nothing changes until plan 04 flips the routes."
  - "Platform health is neutralised once in the _health_signals loader (user_view.reduce_signals) instead of per call site."
requirements-completed: [AUTH-05]
duration: ~1h
completed: 2026-10-31
---

# Phase 55 Plan 01: Reduced user view (render and form policy) Summary

A user principal's Display, Home, Health and navigation now carry no wake interval, LED, runway, platform health or admin links in the served markup, and the settings POST refuses those fields server-side. Admin rendering is unchanged. Routes stay `ADMIN_ONLY`.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | b6f4b56 | `companion/user_view.py`; `_handle_settings_post` runs the form through `sanitise_settings_form` (drops `wake_interval_s`, `led_enabled`, `tracked_runway`, forces scope to display) |
| 2 | 907caa7 | Display (no runway group, Device scope empty, non-display scope coerced to display), Health (no server/data group, source-fault block, registry, resolve dialog), Home attention row frame-only, freshness token and nav dot frame-only |
| 3 | 5f0d7be | User sidebar, phone tab bar, wordmark derived from the route table and request scope; `nav.locations` string (French "Lieux") |

## Verification

- `pytest companion test-support scripts -m "not browser" -n 4 --no-cov`: 3503 passed, 3 skipped (root-permission skips, pre-existing); the one failure on the way (guard G6 on a literal in `test_user_nav.py`) was fixed and `test_suite_guards.py` re-run green (169 passed with the nav tests).
- New tests: `test_user_view.py` (7 incl. crafted `wake_interval_s=60, led_enabled=on, tracked_runway=06-24, scope=all` leaving device config untouched), `test_user_health.py` (9, English and French), `test_user_nav.py` (9). Existing admin tests (`test_companion_app_01/02`, `test_account_page`, `test_sign_in_surfaces`, `test_i18n`, `test_page_scripts`) pass unchanged.
- `ruff check .`: clean. `mypy`: 23 files, no issues. `scripts/check_comment_history.py check`: exit 0. `scripts/check_function_size.py check --max 80 server stub-server`: none over 80.
- `git diff --stat` for the two shared pages (Task 2): `health_page.py` 34 insertions, 15 deletions (the platform rows, registry and dialog moved behind two small helpers `_server_group_html` / `_registry_block_html` plus a `platform_visible()` gate); `home_page.py` 11 insertions, 4 deletions (`_attention_states()`).

## Deviations from Plan

1. **[Rule 2 - Missing critical] `companion/page_context.py` modified** (not in `files_modified`). The nav dot on every tab page is drawn from `ctx.health_severity`, which reads the `_health_signals` loader; reducing the signals there (`user_view.reduce_signals`) is the single place that makes the dot, Health banner, Home row and freshness token agree. Four-line change.
2. **[Rule 2 - Security] `_health_alert_for_admin` left returning `None` for users** instead of adding a frame-only branch. It serves error pages (404/403) with `self.args.state_dir`, i.e. the live frame, with no device scope; a frame-only dot there would show a user the health of a frame that may not be theirs. Only a docstring note was added. The tab pages draw the user's dot correctly through the page context.
3. **Home "Refresh now" / LED quick control**: already absent from Home before this plan (poll trigger removed earlier, Home switches are screen and quiet hours only), so Home needed only the attention-row change. The LED quick control exists only on the Device scope, which is now empty for users.
4. **User nav links gated on route reachability** (min_role at most user), so with routes still `ADMIN_ONLY` a user sees Account only and the existing "every link on a user page is reachable" tests stay green. The pages appear automatically when plan 04 flips the routes. Calendar has no standalone GET route, so no Calendar link was added (plan Test 1 does not list it either).
5. `user_view.sanitise_settings_form` imports `config_page` lazily (the page module imports `user_view`; a top-level import would cycle).

## Known Stubs

None.

## Notes for the owner / later plans

- Plan 04 flipping routes: no further nav or render work is needed for Home/Flights/Display/Airlines/Health links; plan 06 should prove the reductions over HTTP (the crafted POST, Health markup, nav).
- The Health registry/stats reads still run for a user (their output is not rendered); cheap, left to keep the diff to `health_page.py` small.
- The `Update`, `Device`, and admin pages are untouched; the "Administration" group is plan 08.

## Self-Check: PASSED

Files verified present: `companion/user_view.py`, `companion/test_user_view.py`, `companion/test_user_health.py`, `companion/test_user_nav.py`. Commits b6f4b56, 907caa7, 5f0d7be exist in `git log`.
