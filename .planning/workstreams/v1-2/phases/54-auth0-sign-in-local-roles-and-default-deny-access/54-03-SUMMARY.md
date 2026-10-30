---
phase: 54-auth0-sign-in-local-roles-and-default-deny-access
plan: 03
subsystem: companion-ui
tags: [login, account, shell, i18n, css]
requires: []
provides:
  - login_page.render_login_page(auth0_enabled, legacy_enabled, notice), not_invited_page, sign_in_error_page, interstitial_page
  - companion/pages/account_page.py (Identity, render)
  - prefs.set_request_principal / current_principal (request-scoped, inert until set)
  - layout.ACCOUNT_ROUTE, USER_NAV, is_user_principal
affects: [phase-54 plans 04-06 call these surfaces]
tech-stack:
  added: []
  patterns: [request-scoped contextvar mirrored from the language holder, byte-identical defaults pinned by golden digests]
key-files:
  created: [companion/pages/account_page.py, companion/i18n_fr/account.py, companion/test_sign_in_surfaces.py]
  modified: [companion/login_page.py, companion/prefs.py, companion/ui_nav.py, companion/ui_shell.py, companion/layout.py, companion/static/style.css]
key-decisions:
  - "Sign in link path is /login/auth0 everywhere (the UI-SPEC text said /login/start)"
  - "Generic toast errors use a separate notice argument; wrong-password and lockout stay in-form via the error argument"
  - "Legacy pill is emitted inside the logout form, directly before the button"
  - "Wordmark of a user shell is wrapped in an inner link, and the shell template slots became brand_inner_sidebar / brand_inner_header with unchanged default output"
requirements-completed: []
duration: 40min
completed: 2026-10-30
---

# Phase 54 Plan 03: Sign-in surfaces and user shell Summary

All UI-SPEC surfaces 1-7 exist as pure markup functions with EN and FR copy, plus a request-scoped principal hook the shell reads. No routing, session or Handler change.

## Tasks
1. Login card, not-invited refusal, generic error pages, script-free interstitial, scoped CSS, FR strings: commit 8e4a3a2
2. Account page body, user-role shell (one Account link, no tab bar, no Health dot, wordmark to /account), legacy pill before Sign out: commit 99930ee

## Behaviour notes for later plans
- `render_login_page` keeps its original signature and output byte-for-byte when called without the new keyword-only arguments (golden digests for login, 404 and 403 in the tests). Legacy-only (the default) renders today's form, open, with no disclosure.
- With Auth0 on the Sign in link is a plain GET anchor with the page's single autofocus; `next` is added only for a same-site path. The legacy block is a collapsed `<details>` that opens itself when it carries a wrong-password or lockout message.
- With both methods off the card shows one docked "Sign-in is not configured" toast and no control.
- `sign_in_error_page(kind, ...)` takes the closed set `SIGN_IN_ERROR_*`; an unknown kind reads as the incomplete case, so no caller text reaches the page.
- `interstitial_page(kind, target, target_label, ui_theme)` requires a same-site path or an http(s) URL (ValueError otherwise) and `target_label` must be a Message (`CONTINUE_TARGET_ACCOUNT/HOME/SIGN_IN`). Cache-Control: no-store is for the handler to set.
- `prefs.set_request_principal(kind, role)` with kind in user / admin / legacy-admin; anything else clears it. Role "user" gives the one-link shell; kind "legacy-admin" gives the pill. Callers must set it once per request before rendering.
- Account page `render(identity, ui_theme="auto")`; the preference forms still post to /ui-lang and /ui-theme, so the return-to-/account behaviour belongs to the route plan.
- 404/403 "Back to Account" and the user-aware error pages are not in this plan.

## Deviations from Plan
- `companion/i18n_fr/registry.py` was not edited: the French catalogue modules are discovered automatically, so `account.py` needed no registration.
- Plan task 1 said the `error` argument path renders the docked toast; the wrong-password path must stay an in-form message, so the toast uses a separate `notice` argument.
- `prefs.py` was committed with Task 1 (the Task 1 tests reset the principal), not Task 2.

## Verification
- `pytest companion` full run: 2200 passed, 543 skipped. Browser tests skip here because Chromium is not installed in this environment, so the 360px layout of the new CSS is untested in a browser (the plan assigns that to plan 06).
- ruff, mypy, comment-history gate, `stub-server/test_phase47_freeze.py` pass. No added hex colour or token in style.css. byos_server.py, firmware and the freeze file are untouched.

## Known Stubs
None. The Frames card on the Account page is the intended empty state.

## Self-Check: PASSED
Files and commits 8e4a3a2, 99930ee exist.
