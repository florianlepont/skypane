---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 07
subsystem: companion
tags: [co-managers, fleet, dialogs, home]
requires: [61-06, 61-09]
provides: [co_managers_card.manage_access_dialog_html, co_managers_card.leave_dialog_html, co_managers.access_view, return_to whitelist, Fleet Manage access]
key-files:
  modified:
    - companion/pages/co_managers_card.py
    - companion/co_managers.py
    - companion/pages/fleet_page.py
    - companion/console_pairing.py
    - companion/pages/home_page.py
    - companion/routes.py
    - companion/ui_modal.py
    - companion/device_scope.py
    - companion/static/style.css
    - companion/i18n_fr/co_managers.py
    - companion/test_co_managers_page.py
    - companion/test_browser_co_managers.py
    - companion/test_browser_fleet_page.py
    - companion/test_console_fleet_page.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 07: Manage access dialog Summary

Co-management left Home: an admin opens "Manage access" from a Fleet row menu, picks a person and adds them in four actions, and the dialog reopens after every change.

## Commits

- 48deccf: dialog builders, return_to handling, Fleet wiring, Home card removal, unit and browser tests (tasks 1-3 in one green commit, because the Home card removal and the test rewrites cannot be split without a red state).

## What changed

- `co_managers_card`: the Home card is replaced by `manage_access_dialog_html(view, device_id, frame_name, return_to, open_)` (sections dialog: owner row, co-managers with a destructive Remove form each, the empty state, the Add form; admin gets a select of candidates, owner a typed e-mail; dismiss "Done") and `leave_dialog_html(device_id, frame_name, return_to)` (confirm-only, destructive, initial focus on "Stay on this frame"; for plan 61-10). Forms post to the explicit `/devices/<id>/co-managers/...` routes, so the host page need not be device-scoped. `safe_return_to` accepts only the exact strings `/fleet` and `/account`.
- `co_managers`: add/remove read an optional `return_to`; with a valid one they redirect to `/fleet?access=<id>` (result shown as the console toast through `console_flash`, same texts) or `/account?access=<id>&flash=<key>`; otherwise unchanged (frame Home with `?flash=`). Leave still never reads the form. `_card_view` became `access_view` (owner or admin only); `card_html` is gone. Server rules (owner or admin add/remove, co-manager leaves) and the route policy rows are untouched.
- Fleet: "Manage access" item in every live row menu whose frame has an owner; one dialog per frame; `?access=<id>` renders that frame's dialog open (only a matching id opens anything; the value is never echoed).
- Home: `home_page.render(ctx)` and the `routes.py` call no longer take or build the Co-managers card.
- One status dot per frame: Fleet rows now carry `state` (resolved with `wake.next_wake_status` + `frame_state.resolve_state`), `screen_off`, and a battery-empty hold counts as 0 percent, exactly as Home derives them (`console_pairing._frame_signals`, new `device_scope.last_check_in_ts`). Tests compare the Home and Fleet words for an overdue served frame, a silent paired frame and a battery-empty frame.
- `ui_modal.sections_dialog_html` gained `open_`. CSS: the select width cap now targets `.modal__body select` instead of the removed `#co-manager-person`.
- FR: new keys for the dialog title, menu label, Done, Leave title; "Remove" now reads "Retirer" (UI-SPEC) instead of "Enlever"; orphan `purpose_read_only` removed.

## Deviations from Plan

1. **Matrix rows for return_to variants not added.** `ROWS` is keyed by (method, route) and cannot express form variants; the variants are covered by behaviour tests in `test_co_managers_page.py` (valid, external, protocol-relative, unlisted, header-injection, no return_to). `matrix_rows_co_managers.py` unchanged.
2. **One commit for tasks 1-3.** See Commits.
3. **Leave browser flows dropped.** The old Home-card Leave tests (native details, scripts blocked, stay) have no host until plan 61-10 puts "Leave frame" on Account; the leave HTTP flow (`test_leaving_lands_on_account...`) stays. 61-10 must add browser coverage for the Leave dialog.
4. **Existing tests changed:** `test_browser_fleet_page` row menu now has 4 items; `test_console_fleet_page` asserts the Manage access link.
5. **Account toasts.** `/account?access=<id>&flash=<key>` is produced for `return_to=/account`, but Account still renders only the leave flash (existing test pins that). 61-10 must render the co-manager keys and reopen `?access=` when it adds the Account trigger.
6. **Out-of-plan files:** `ui_modal.py`, `device_scope.py`, `console_pairing.py`, `static/style.css`, `routes.py`.

## Gates

ruff, mypy (28 files), check_comment_history, check_function_size (922 functions) and the Phase 47 freeze are clean. Full `companion` + `test-support` + freeze run with `-n auto`: 5901 passed, 3 skipped (root-permission tests), no browser skips. An earlier full run showed 5 `test_browser_console` failures under heavy `-n auto` load that passed in isolation and in the final full run. `render_baseline.json` regenerated: no change (Home bodies in the baseline carried no card); no digest pin moved.

## Known Stubs

None.

## Threat Flags

None. T-61-07-01: exact-match whitelist, tested with external, protocol-relative, header-injection and non-string values. T-61-07-02: route policy rows and handlers' gates unchanged, a co-manager's POST with `return_to` is refused. T-61-07-03: candidates built only when the viewer is an admin; the frame pages no longer carry any co-manager markup for owners or co-managers.

## Self-Check: PASSED
