---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 08
subsystem: companion-auth
tags: [csrf, auth, forms, calendar, ssrf]
requires: [55-04]
provides:
  - auth.csrf_token / auth.csrf_ok (token derived from the raw session cookie, no schema change)
  - routes.Route.csrf (trailing defaulted field), routes.CSRF_FIELD, routes.CSRF_ROUTE_KEYS
  - prefs.set_request_csrf / current_csrf, ui_components.csrf_field (re-exported by layout)
  - Handler.read_form cached per request; dispatcher CSRF check after ALLOW
  - calendar_rules.calendar_url_is_acceptable and form_post.resolve_calendar_url
affects: [55-10, 55-11, 55-12, 55-13]
key-files:
  created:
    - companion/test_csrf.py
    - companion/test_calendar_url_gate.py
  modified:
    - companion/auth.py
    - companion/prefs.py
    - companion/routes.py
    - companion/app.py
    - companion/login_page.py
    - companion/ui_components.py
    - companion/layout.py
    - companion/i18n_fr/common.py
    - companion/pages/airline_sheet.py
    - companion/pages/airlines_page.py
    - companion/pages/update_page.py
    - companion/settings/calendar.py
    - companion/settings/rules.py
    - companion/settings/form_post.py
    - companion/pages/config_page.py
    - server/plane/calendar_rules/__init__.py
    - test-support/companion_app_server.py
    - test-support/companion_render_snapshot.py
    - companion/testdata/render_baseline.json
requirements-completed: [AUTH-05]
completed: 2026-10-31
---

# Phase 55 Plan 08: Per-session CSRF and calendar-URL gate Summary

Per-session CSRF token (hex sha256 of `csrf-v1:` + raw session cookie, constant-time compare) enforced in `_dispatch` for flagged POST routes, with the six existing destructive and release forms retrofitted; plus the combined settings form now applies the connect route's address gate.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | 8c7bab0 | `csrf_token`/`csrf_ok`, `Route.csrf`, `CSRF_FIELD`, `CSRF_ROUTE_KEYS`, prefs holder, `csrf_field()`, cached `read_form()`, dispatcher check after `_apply_principal` (403 "This page expired", French added), matrix rig sends the token on every POST |
| 2 | 3f3b0f1 | Hidden field in the rule-delete, calendar-disconnect (sheet and confirm page), manual-resolution delete, rename-reset, `/update` install, install-confirm and cancel forms; shared `with_csrf` test helper; render snapshot normalises the per-session value and posts the token |
| extra | a8131dc, 554c7be, 2d0702a | Calendar-URL gap closure (below) and its test follow-ups |

## Calendar-URL gap (additional task)

`POST /devices/<id>/settings` and `POST /settings` stored a private/loopback `calendar_url` into `calendar_url.secret` while `/settings/calendar/connect` refused it. Fix: `calendar_rules.calendar_url_is_acceptable()` (non-empty, https after webcal normalisation, SSRF host gate) is now the single gate used by `connect_calendar_url` and by a new `form_post.resolve_calendar_url` step in `handle_post`, evaluated before any write, so a refused link rejects the whole save (200 re-render, field error `calendar_url`, nothing stored, stored link kept). New file `companion/test_calendar_url_gate.py` (own rig, real handlers, 12 tests incl. prefixed and un-prefixed forms, stored link kept, and a positive control); 11 of 12 fail with the gate disabled. The existing "never fetched" test was left as is.

## Verification

- `ruff check .`, mypy (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (812 functions, none over): clean.
- Full non-browser suite (`companion server test-support scripts stub-server -m "not browser"`): 5809 passed, 7 skipped (root-permission skips, pre-existing), after one fix (test_suite_guards G12) that was then re-run green.
- Browser suite (`companion -m browser`, 557 tests) passed, using a symlink dir outside the repo in the scratchpad for the chromium 1243 vs 1248 headless-shell mismatch.

## Deviations from Plan

1. **[Rule 3] Plan's Task 1 filled `CSRF_ROUTE_KEYS` empty, Task 2 fills it.** I filled it with the six keys in Task 1 (same commit as the mechanism), so between 8c7bab0 and 3f3b0f1 the six forms lacked the token; the tree is green from 3f3b0f1.
2. **[Rule 1] Existing tests that POSTed bare to the six routes** now send the token (they test handler behaviour, not CSRF): `test_i18n`, `test_calendar_sheet`, `test_companion_app_05`, `test_airline_sheet`, `test_device_helpers.post`, `test_update_actions._post`, via `with_csrf` in `test-support/companion_app_server.py`. Malformed rule-delete paths that match the route now need the token to reach the handler's 404 (otherwise 403).
3. **[Rule 3] `companion_render_snapshot.py` and `render_baseline.json`** (unlisted): the baseline gained the hidden field; the value is normalised and session POSTs carry the token. Verified every baseline difference is exactly the added input.
4. **[Rule 3] `login_page.forbidden_page` gained an optional `purpose`** and `Handler._forbidden_page(purpose=None)`, to render the expired-page text on the existing 403 shell.
5. Plan-listed `companion/test_access_matrix.py` is the only matrix file changed; `access_matrix_support.py` needed no change.
6. Two existing settings-save tests (`test_config_page_04`, `test_config_page_05`) save a placeholder host that cannot resolve; they now stub `safe_fetch.host_is_safe` to True. Not a weakening: they test the save, the gate has its own file.
7. `test-support/` helper `with_csrf` returns no token for an anonymous caller so anonymous-redirect tests keep their meaning.

## Notes for the owner

- The field error shown for a refused calendar link on the combined form reuses `ERROR_CALENDAR_URL_INVALID` ("That link is too long, or conflicts with the disconnect option below."), which is inaccurate wording for an address refusal. The sheet's connect route has its own clearer message. A dedicated string (EN/FR) would be a small follow-up; the combined form no longer renders a calendar field, so it is rarely visible.
- A save of a hostname that does not resolve at all is now refused by the combined form (same as connect); previously it was stored.
- Plans 10 to 13: set `csrf=True` on new admin and pairing POST `Route`s and emit `layout.csrf_field()` in their forms.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (T-55-08-01 to -05 covered by `test_csrf.py`; the calendar fix closes an SSRF-adjacent storage gap).

## Self-Check: PASSED

Commits 8c7bab0, 3f3b0f1, a8131dc, 554c7be, 2d0702a exist; `companion/test_csrf.py` and `companion/test_calendar_url_gate.py` present.
