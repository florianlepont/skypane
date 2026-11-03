---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 10
subsystem: companion
tags: [account, my-frames, display, detection, dialogs]
requires: [61-07, 61-09]
provides: [account_page My frames card, Account Manage access and Leave frame triggers, Account co-manager toasts, merged Location and detection card, co_manager_browser_support]
key-files:
  created:
    - companion/test_browser_account_frames.py
    - test-support/co_manager_browser_support.py
  modified:
    - companion/pages/account_page.py
    - companion/sign_in.py
    - companion/console_pairing.py
    - companion/pages/config_page.py
    - companion/pages/locations_page.py
    - companion/routes.py
    - companion/i18n_fr/account.py
    - companion/i18n_fr/display.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 10: Account My frames and merged Location and detection Summary

Account now opens with a My frames card (dot, name link, hardware or "Shared by" line, Manage access or Leave frame in dialogs), and Display carries one "Location and detection" card while the Device page no longer repeats Detection.

## Commits

- 0486972: My frames on Account (page, handler wiring, French, unit and browser tests).
- 91c6baa: merged card, Device page without Detection, render baseline, browser tests. Tasks 2 and 3 share one commit because the browser tests cover the merged card and the pinned tests could not be green separately.

## What changed

- `account_page`: `FrameSummary` now carries the id, the status-dot signals (`last_seen`, `battery_percent`, `offline`, `state`, `screen_off`) and, for owned frames, the Manage access view. Rows are `ui_entity_list` rows (dot through `frame_status`, name link to the frame Home, line 2, one `a.entity-row__button` trigger). Owned frame: Manage access dialog (`return_to=/account`, reopened by `?access=<id>`); co-managed frame (any role, including admin): Leave dialog. Card order: My frames, Identity, Preferences, Sign out. No battery or last-contact text.
- `sign_in`: builds the summaries with `console_pairing.frame_signals` (now public) and `co_managers.access_view` (owned frames only), so Home, Fleet and Account derive one dot. Account renders every co-manager flash key as a toast and reads `?access=`; only an id that matches one of the caller's own frames opens anything, the value is never echoed.
- `config_page`/`locations_page`: Display renders one `section.theme-status.theme-status--nested.detection-card` titled "Location and detection": sentence, Location fields (the same `location_id` select with the same `data-dirty-section="Location"` wrapper, so dirty tracking is unchanged), change link. Device no longer gets the card; `routes.py` stops passing `location_name` there.
- FR: My frames, Shared by, Leave frame, Manage access aria, new empty-state body (spec wording), Lieu et détection. Orphan keys removed.
- Test infrastructure: `test-support/co_manager_browser_support.py` (Rig, `_open`, overflow helper) shared by the co-manager and account browser modules (the guard forbids importing another test module).
- Updated tests deliberately: Account section of `test_co_managers_page.py` (entity rows, all co-manager flash keys now render, the old "only the leave flash" test became "only the co-manager flashes"), `test_sign_in_surfaces.py` (card order, empty body), `test_config_page_04.py` (card regex), `test_config_page_05.py` (Device editorial floor minimum 3 to 2, the Device page lost the detection caption), `test_browser_ux_04.py` (title-voice probe: the merged card is a second nested tier, Device allows only LED and wake titles), `test_browser_co_managers.py` (Account row selectors), `test_display_detection_card.py` (one card, none on Device).

## Deviations from Plan

1. **Time zone stays in the Quiet hours card.** The spec text says the merged card holds "location and time zone fields", but the time zone select belongs to the Quiet hours card (helper text "Quiet hours follow this time zone", its own dirty section). Moving it would change the save bar's dirty tracking, which the plan says must stay unchanged, so the merged card holds the sentence, the Location fields and the link. Owner may want to confirm.
2. **Tasks 2 and 3 in one commit** (see Commits).
3. **Out-of-plan files:** `console_pairing.py` (rename `_frame_signals` to `frame_signals`), `test_sign_in_surfaces.py`, `test_config_page_04/05.py`, `test_browser_ux_04.py`, `test_browser_co_managers.py`, `test-support/co_manager_browser_support.py`, `i18n_fr`.
4. **Browser flows** use the signed-in session helpers (`fx.user_cookie`) as the co-manager tests do, not a fake-Auth0 login; the Auth0 path is covered elsewhere.

## Gates

ruff, mypy (28 files), check_comment_history, check_function_size (922 functions) clean; Phase 47 freeze green. Render baseline regenerated (Display and Device pages moved); no digest pin or golden moved. Full `companion` + `test-support` + freeze run with `-n auto`: 5970 passed, 3 skipped (root-permission tests), no browser skips.

## Known Stubs

None.

## Threat Flags

None. T-61-10-01: the Manage access trigger and dialog exist only for frames whose `access_view` is non-None and whose owner is the caller; tests assert a co-manager (and an admin who only co-manages) gets no access dialog even with `?access=<id>`, and a co-manager POST to add is refused (403/404). T-61-10-02: the list is built from the principal's own ownership and membership rows; tests cover another user's and an admin's account.

## Self-Check: PASSED
