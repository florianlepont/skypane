---
phase: 68-console-and-companion-visual-improvements
plan: 29
subsystem: companion
tags: [account, sign-in, credits, 404, i18n]
requirements: [CON-01]
key-files:
  modified:
    - companion/pages/account_page.py
    - companion/credits_page.py
    - companion/login_page.py
    - companion/ui_base.py
    - companion/static/style.css
    - companion/static/style-admin.css
    - companion/i18n_fr/account.py
    - companion/i18n_fr/common.py
    - companion/test_account_page.py
    - companion/test_sign_in_surfaces.py
    - companion/test_browser_account_frames.py
    - companion/test_browser_auth0.py
    - companion/test_companion_app_01.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-22
---

# Phase 68 Plan 29: Account, sign-in and 404 Summary

Account, the sign-in First visit line, Credits entry and the 404 page now follow the owner-approved `68-MOCKUP-account-signin-404.html` (R19 to R24).

## Commits

- d3d72d68 Credits way back opens with the header (found by shards)
- 30cc874f co-manager page tests read the icon actions by accessible name
- f9822f00 Account frame icon actions, no hardware line, Credits entry (R19, R20, R21, R23)
- 85a53dc5 sign-in First visit line under the button, livelier 404, baseline (R22, R24)

## What changed

- R19: Manage access (key) and Leave frame (door and arrow, existing `icon-sign-out`) are 44 px icon buttons at the right of the row, named by `aria-label` ("Manage access: Kitchen"); rows gain no height. New sprite symbol `icon-key`.
- R20: status is the dot with its accessible name plus the last-seen word; no percentage anywhere (test with a 5 % battery, EN and FR).
- R21: the hardware model is shown to nobody on the page (owner decision). `FrameSummary.hardware` is kept as an unused field to avoid touching `sign_in.py`.
- R23: new About group with a Credits row (user and administrator). `/credits` for any signed-in person shows a chevron "Back to Account" link above the title (done in `credits_page.py`; `app.py` untouched). Anonymous keeps "Back to sign in" at the bottom.
- R22: the First visit hint is one small, muted, centred line under Sign in, above Credits; only on the plain card.
- R24: 404 shows the approved "empty frame" inline SVG (decorative, `aria-hidden`, no image, no asset, no font) and "Nothing hangs on this wall." on a panel, same for every caller; status stays 404.
- The hand-built `banner__pill` is replaced by `ui_components.pill_html`.

## Deviations

- Account row CSS lives in `style-admin.css` (not `style.css` as the plan listed); 404/login/credits CSS is in `style.css`.
- Rule 3: pinned digests in `test_sign_in_surfaces.py` (404, 403, shell) and the sprite counts in `test_companion_app_01.py` were updated for the new markup and symbol.
- `account.leave_frame` message and its French entry removed (orphan after the change); `account.about`, `account.credits_detail`, `common.nothing_hangs_on_this_wall` added with French.
- Baseline `render_baseline.json` regenerated once; PR #515 also moves it, so expect regeneration after it merges.

## Remaining divergences from the mock

- Built uses the real shell (mock shell icons differ); the mock shows invented sample frames, the built page shows seeded ones.
- Dot colours and exact radii follow the product tokens rather than the mock's literal values.

## Verification

Run after the last code change (d3d72d68): ruff, mypy, function-size, comment-history clean; full core suite 12529 passed, 7 skipped; browser shards 0 and 1 passed in full (1204 and 765 tests). Shards 2 to 4 were stopped on the owner's instruction to run targeted tests only (CI runs them); an earlier run of shards 2 and 3 had failed only in the Credits page-opening and stand-alone-link tests, fixed in d3d72d68 and re-run.

Targeted run (3866 passed, 2 skipped): test_render_baseline, test_stylesheet_structure, test_suite_guards, test_structure_guards, test_i18n, test_access_matrix, test_browser_french_fit, test_browser_overhaul_sweep, test_browser_contrast_edges, test_browser_page_opening, test_browser_small_fit_fixes, test_browser_account_frames, test_browser_auth0, test_account_page, test_credits_page, test_co_managers_page, test_sign_in_surfaces, test_sign_in_messages, test_status_pages_04, test_server_error_page, test_landing, test_audit4_fixes, test_companion_app_01, test_companion_app_04.

Screenshots: scratchpad `p29/{mock,built}/`.
