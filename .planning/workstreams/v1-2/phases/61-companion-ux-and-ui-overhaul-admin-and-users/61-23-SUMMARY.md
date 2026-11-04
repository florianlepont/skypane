---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 23
subsystem: companion
tags: [frame-picker, modal, navigation, console]
requires: [61-22]
provides: [frame chip and card sheet, Console all-frames list, no Fleet entry in the personal sheet]
key-files:
  created:
    - companion/test_frame_sheet.py
    - companion/test_browser_frame_sheet.py
  modified:
    - companion/ui_shell.py
    - companion/ui_modal.py
    - companion/device_scope.py
    - companion/static/style.css
    - companion/static/modal.js
    - companion/i18n_fr/nav.py
    - companion/test_frame_switcher.py
    - companion/test_device_selector.py
    - companion/test_browser_device_selector.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 23: Frame chip and card sheet

The `<details>` frame drop-down is replaced by a 48px frame chip that opens a card sheet built on the shared modal. Nothing is rendered with fewer than two frames.

## What changed

- **Chip and sheet** (`ui_shell.frame_switcher_html`): the chip is `ui_modal.trigger_html` (`href="#dlg-frames"`, `data-modal-open`, aria-label "Switch frame, current: name"); the sheet is `sections_dialog_html` with a new optional `extra_class` (`dialog.modal.frame-sheet`), title "Choose a frame" / "Choisir un cadre", footer link "Manage my frames" / "Gérer mes cadres" to `/account#account-frames`, dismiss "Close". Cards are whole-card anchors to `device_scope.target_path(page, device)`: dot, name, second line (hardware label for an owned frame, "Shared by <email>" for a co-managed one, owner email for a foreign or Console frame). The current card has `aria-current`, a check icon and a hidden "Current" / "Actuel".
- **Lists**: personal pages keep the existing rule (owned or co-managed, plus the viewed foreign frame for an administrator). Console pages (selected by `current_space(active) == CONSOLE_SPACE`) use the new `device_scope.console_frame_entries()` (every frame with owner emails from one query; an admin-only branch, a non-admin only gets their own scope with no emails), ordered in `ui_shell` by severity (error, warn, rest) then name.
- **Airline editor**: `device_scope.page_routes()` now includes `/airlines/manage`, so the chip works there and the `?device=` redirect covers it.
- **Removed**: "All frames (Fleet)" key and text, the Fleet footer link, `.frame-switcher*` CSS, the `details.frame-switcher` branch of `modal.js` (row menus still close on outside tap and Esc).
- **CSS**: `.frame-chip` (full width on phone, 24rem max from 700px), `.frame-card` (min 64px, 2px accent ring on the current card), two columns from 700px, wider dialog on desktop; tokens only; the accent list in the stylesheet header names the current card.

## Tests

New: `test_frame_sheet.py` (10: chip and sheet markup, EN/FR, current marks, no foreign email for a user, escaping, Console lists for Health / Device / editor with owner emails, severity order, personal admin list) and `test_browser_frame_sheet.py` (15, Chromium, not skipped, 3 runs green in a row: focus inside the sheet and Tab containment, Esc returns focus to the chip, page kept on Personalisation / Flight history / Home with aria-current, no-script hash path, cards at least 64px, close at least 44x44, no overflow at 360 and 1280 px in EN/FR and light/dark, bottom sheet below 700px, admin personal sheet without Fleet, Console sheet lists all frames with emails).

Rewritten in place: `test_frame_switcher`, `test_device_selector`, `test_browser_device_selector`, `test_ui_modal` (modal.js no longer mentions the switcher), `test_device_links` and `test_device_routes` (the sheet is exempt from the "links stay under the prefix" crawl, as the switcher was), `test_user_view_http`, `test_co_manager_access`, `test_browser_home_state_card`, `test_browser_overhaul_steps` (U2 with several frames: chip is one tap; new U2-switch test records chip then card as 2 taps; `61-STEP-COUNTS.md` not edited, left to the later step plan).

`render_baseline.json` regenerated: no change (no pinned page carries the chip); sign-in digests unchanged.

## Gates

ruff, mypy (29 modules), comment-history, function size (931 functions, none over 80): clean. Phase 47 freeze: 21 passed. Full `companion test-support stub-server -n auto --no-cov` after the last edit: 6911 passed, 4 skipped, 1 failed: `companion/test_personal_space_parity.py::test_a_personal_page_is_identical_for_an_administrator_and_a_user` (a file this plan does not touch). The diff is a one-second difference in a timestamp attribute between the user and the administrator render; it is a second-boundary flake from plan 61-22 (passes 5 of 7 reruns, failing only when the two renders straddle a second). Not fixed here. `./scripts/run-all-tests.sh` not run (not the last code plan).

## Deviations

1. The severity ordering lives in `ui_shell` (needs the status dot resolver) rather than in `device_scope.console_frame_entries()`, which returns the frames in scope order with owner emails.
2. `ui_modal.sections_dialog_html` gained an optional `extra_class` parameter (needed for `dialog.modal.frame-sheet`).
3. `page_routes()` includes the airline editor (needed by the chip on that page).

## Known Stubs

None.

## Self-Check: PASSED
