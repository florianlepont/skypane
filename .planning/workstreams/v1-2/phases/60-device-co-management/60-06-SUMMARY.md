---
phase: 60-device-co-management
plan: 06
subsystem: companion-ui
tags: [co-management, home-card, account, i18n, css]
requires: [60-04, 60-05]
provides:
  - Co-managers card on the frame's Home page (manage, read-only and leave shapes)
  - Account "Shared" pill with the owner's address, own-and-co-managed frame filter, leave toast
  - English and French strings for the card and the Account additions
affects: [60-07, 60-08]
key-files:
  created:
    - companion/test_co_managers_page.py
  modified:
    - companion/pages/co_managers_card.py
    - companion/co_managers.py
    - companion/pages/home_page.py
    - companion/routes.py
    - companion/static/style.css
    - companion/i18n_fr/co_managers.py
    - companion/pages/account_page.py
    - companion/sign_in.py
    - companion/i18n_fr/account.py
requirements-completed: [AUTH-08]
completed: 2026-11-01
---

# Phase 60 Plan 06: Co-managers card and Account additions Summary

The Co-managers card on a frame's Home page, built from existing components in three shapes over one `CardView`, with the Account "Shared" mark, the leave toast and French strings, all per the approved UI contract.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Pure card markup, scoped CSS, French | 7397d73 | companion/pages/co_managers_card.py, companion/static/style.css, companion/i18n_fr/co_managers.py, companion/test_co_managers_page.py |
| 2 View builder and Home wiring | 9c6e02c | companion/co_managers.py, companion/pages/home_page.py, companion/routes.py, companion/test_co_managers_page.py |
| 3 Account Shared mark, filter, leave toast | 1bd6aef | companion/pages/account_page.py, companion/sign_in.py, companion/i18n_fr/account.py, companion/test_co_managers_page.py |

## Touches Phase 55 code

Yes, minimally:

- `companion/pages/home_page.py`: `render` takes an optional `co_managers_html` (default empty, so existing output is byte-identical) appended after the `.home-facts` block.
- `companion/static/style.css`: one appended block (`.co-manager__row`, `.co-manager__who`, `.co-manager__email`, `.co-manager__remove`) built from `--space-xs`/`--space-sm`; no colour literal, token, keyframes or media block.
- `companion/pages/account_page.py`: defaulted `FrameSummary.shared` and `owner_email`; Shared pill and owner line only for a shared frame.
- `companion/sign_in.py`: `_own_frame_summaries` keeps owned or co-managed frames, a guarded helper reads the co-managed ids and owner address, and the Account GET renders the toast for exactly one flash key.
- `companion/i18n_fr/account.py`: two French strings.
- `companion/routes.py`: only the Home route entry changed.

## Behaviour

- Variant is chosen from `can_manage` (role is admin, or the viewer is the frame's owner), `is_admin_viewer` and `viewer_is_member`; the add control is a typed e-mail for an owner and a `<select>` posting the same `email` field for an admin, decided by role and never by the candidate list being empty.
- `card_html` fails closed (renders nothing) for a frame with no fleet row, no owner, an unknown viewer, a viewer who neither manages nor belongs, or any store error. Candidates are filled for an administrator only, so a non-admin page never contains an invited-only address.
- The card sits after `.home-facts`, outside every freshness swap selector and every form.
- Leave posts no id; `details.fleet-confirm` is closed by default. `grep fleet-confirm style.css` finds no rule: the 44 px summary height comes from the global `summary` rule (`min-height: 44px`). The browser measurement belongs to plan 08 (Chromium is not installed in this environment).
- Account: an admin now lists only frames they own or co-manage; `/account?flash=co_manager_left` shows the success toast, every other flash value shows none.

## Verification

- `companion/test_co_managers_page.py` (35 tests), `test_co_managers.py`, `test_co_manager_access.py`, `test_account_page.py` (unmodified), `test_i18n.py`, `test_suite_guards.py`: pass.
- ruff (whole repo), mypy (28 files), `check_function_size.py` (921 functions, none over 80), `check_comment_history.py`: clean.
- `companion` without browser tests plus `stub-server/test_phase47_freeze.py`: 4432 passed, 30 failed (see below); the Phase 47 freeze test passed.
- Home, snapshot and freshness tests pass unmodified.

## Failures outside this plan

- 29 `companion/test_access_matrix.py` failures: expected until plan 07 adds the matrix rows (matrix not edited).
- `companion/test_render_baseline.py::test_unauthenticated_responses_match_the_baseline`: the committed baseline (`companion/testdata/render_baseline.json`, edited in plan 05 commit d3b5e76) holds `POST /co-managers/add|remove|leave`, but the capture list `UNAUTH_REQUESTS` in `test-support/companion_render_snapshot.py` has no sample for them, so the key sets differ ("only in baseline"). Not caused by this plan (nothing here touches the capture list or the baseline) and not fixed here: either the three samples are added to the capture list or the baseline entries are removed. Needs an owner decision, naturally in plan 07 or a plan 05 follow-up.

## Deviations from Plan

- **Account French strings added in Task 3, not Task 1.** Adding them earlier left orphan catalogue ids, which `test_i18n` rejects.
- The CSS test reads the stylesheet through the running app instead of opening the file, because the suite guard forbids opening source-suffixed paths.
- Shared "Owner" line uses `.co-manager__email` for wrapping; the card rules add two layout classes (`.co-manager__row`, `.co-manager__who`, `.co-manager__remove`) beyond the email rule because `.status-row` has different alignment and padding and cannot give the 4 px pill gap the contract names.
- Home flash toasts needed no change (device pages already render them).

## Known Stubs

None.

## Self-Check: PASSED (commits 7397d73, 9c6e02c, 1bd6aef and the files above exist)
