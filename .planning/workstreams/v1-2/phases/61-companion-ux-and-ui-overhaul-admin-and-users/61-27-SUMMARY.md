---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 27
subsystem: companion
tags: [home, quiet-hours, modal, dialog, csrf]
requires: [61-26]
provides: [Quiet hours dialog on Home, POST /quick/quiet-hours/window, ui_modal focus_id]
key-files:
  created:
    - companion/test_quiet_hours_modal.py
    - companion/test_browser_quiet_hours_modal.py
  modified:
    - companion/pages/home_page.py
    - companion/settings/quiet_hours.py
    - companion/ui_modal.py
    - companion/routes.py
    - companion/post_actions.py
    - companion/flash.py
    - companion/app.py
    - companion/i18n_fr/home.py
    - companion/i18n_fr/common.py
    - companion/static/style.css
    - companion/static/dirty-state.js
    - companion/static/modal.js
    - test-support/matrix_rows_place.py
    - test-support/companion_render_snapshot.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 27: Quiet hours dialog on Home

Home's schedule row is now the unchanged instant switch plus a 44 px link with a chevron that opens the Quiet hours dialog; the dialog saves through the new csrf-protected `POST /quick/quiet-hours/window`, which writes only `quiet_hours_enabled`, `quiet_hours_start` and `quiet_hours_end`. Same markup for an administrator and a user. One code commit (0e38616): the plan said Tasks 2 and 3 commit together, and Task 1's refusal path needs the Home render parameters from Task 2, so all three tasks are one green commit.

## What changed

- **Route** (`routes.py`, `post_actions.py`): `QUICK_QUIET_HOURS_WINDOW_ROUTE`, `Route(POST, OWNER_DEVICE, csrf=True)`, device-scoped. The handler runs the existing `resolve_quiet_hours_times` / `resolve_quiet_hours_enabled`, requires both times (the shared resolvers treat an absent time as unchanged), treats an unchecked box as off, and passes only the three keywords to `save_device_config`. A refusal re-renders Home through `home_page.render(ctx, quiet_errors, quiet_submitted)` with status 400 and writes nothing; echoed values are capped at 16 characters and escaped. Success redirects 303 to the device-scoped Home with `flash=quiet_window_saved`; a failed write redirects with the existing quick-failed flash.
- **Toast** (`flash.py`, `i18n_fr/common.py`): new key, tone pending (it applies at the next wake, like the other quiet-hours toasts); the times are read from the config that render loaded, EN and FR.
- **Dialog** (`settings/quiet_hours.py`, `home_page.py`): `quiet_hours_dialog_body_html` (checkbox "Use quiet hours" in the existing 44 px `.settings-checkbox` row, Start and End as `type=time step=300`, the three existing presets, the time-zone sentence with a device-scoped link to `/detection#details`). The preset row markup was extracted into `quiet_preset_row_html()` and is shared with the Display card. The dialog is rendered after `.home-facts`, outside every freshness swap region.
- **Modal** (`ui_modal.py`): `dialog_html(..., focus_id=)` puts the initial focus on the named control (Start time) and adds no other autofocus; an invalid control still wins, an unknown id is a ValueError.
- **Scripts**: `dirty-state.js` now runs its preset buttons on a page with no dirty-tracked form (each preset fills its own form via `button.form`), and is added to Home's scripts. `modal.js` remembers the opener's hash and finds the link again if a background refresh replaced it, so Esc returns focus to the schedule link after a swap.
- **CSS**: additive, existing tokens only (inline-flex window link with chevron, dialog row gap, 44 px target for the link inside the sentence).
- **Pins moved by the intended diff**: `render_baseline.json` (the four Home page digests, plus the new unauthenticated route `POST /quick/quiet-hours/window` -> 303 /login), access matrix (row in `matrix_rows_place.py`, DEVICE_SCOPED set), device route list (33), csrf flagged set, route table (22 owner-device routes), flash interpolation allow-list. Sign-in digests did not move.

## Tests

- `test_quiet_hours_modal.py` (29): served dialog for owner, administrator and co-manager, presets, single autofocus on Start, helper sentence and link, French, dialog outside every swap region, row structure; valid save for the three roles with the rest of the config byte-identical, off by unchecked box, Home sentence and EN/FR toast, quick switch route unchanged, seven refusal shapes (400, nothing written, dialog open, aria-invalid, describedby, autofocus on the invalid field), escaped echo, 403 without csrf, outcome per caller from the matrix rows.
- `test_browser_quiet_hours_modal.py` (14, 3 runs in a row green): at 360 and 1280 px, EN and FR: open, focus on Start (waited), Tab/Shift+Tab never reach the page behind, Esc closes and focus returns to the link; both themes: no overflow, dialog inside the viewport, every control at least 44x44 by hit-testing; presets; U4a in three actions (tap the schedule, choose the start, Save) with exactly one key changing; off via the switch; refused value (400, dialog reopened, error below the field, focus on it); background refresh with a half-typed time (virtual clock, the status card and link really replaced, dialog node and typed value intact, Esc returns to the new link); scripts blocked (hash link shows the form, submit posts). Mutation check: removing the modal.js re-query fails the refresh test.
- Updated in place: `test_home_state_card.py` and `test_browser_home_state_card.py` (the window link now opens the dialog), `test_browser_ux_02.py` (the keyboard-focus sweep covers visible Home links; the closed dialog's links cannot take focus).

## Deviations from Plan

1. **[Rule 3] One commit for all three tasks** (see above).
2. **[Rule 3] Preset script**: the existing preset code in `dirty-state.js` returned early without a dirty form; it was restructured rather than adding a new script, so no new static asset or script count moved.
3. **[Rule 2] modal.js opener re-query**: needed because the status card, which holds the trigger, is swapped by the refresh.
4. **Time field `step=300`** is as the spec says; a stored time that is not on a five-minute mark will make the browser's own validation ask for a correction before Save.
5. `app.py` gained one line (Home's script tuple), now 1499 lines.

## Gates

ruff, mypy (29 modules), comment-history, function size (931, none over 80), Phase 47 freeze (21 passed): clean. Full `companion test-support stub-server -n auto --no-cov`: 7161 passed, 4 skipped (root permission bits), 0 failed after the final code commit (a first run before the pins were updated found 10 failures, all pins for the new route, flash key or the dialog's hidden links).

## Known Stubs

None.

## Self-Check: PASSED
