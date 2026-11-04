---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 28
subsystem: companion
tags: [personalisation, look, radio-cards, wake-interval, access]
requires: [61-27, 61-33, 61-34]
provides: [Personalisation page with four cards, Look radio cards, wake-interval access decision point]
key-files:
  created:
    - companion/pages/personalisation_cards.py
    - companion/test_personalisation_page.py
    - companion/test_browser_personalisation.py
  modified:
    - companion/pages/config_page.py
    - companion/settings/theme.py
    - companion/screens.py
    - companion/user_view.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/look.py
    - companion/i18n_fr/nav.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 28: Personalisation

`/display` is now Personalisation: an "On this page" list and four cards in a fixed order (Look, Special looks, Calendar, Screen), each with a title and a muted "Current: ..." line, identical for an administrator and a user. A look is changed in three actions (Personalisation tab, tap a look card, Save). Three commits.

## What changed

- **Wake-interval access decision point** (`screens.py`, `user_view.py`): `screens.WAKE_INTERVAL_PLACEMENT` is set to the administrator-only value (D23); `DISPLAY_ALL` stays defined so a later change is one line. `user_view.can_change_wake_interval(role)` reads it; the group tuples (`EVERYDAY_GROUPS`, `ADVANCED_GROUPS`, the screen type's lists) and `sanitise_settings_form` follow it. A user's posted `wake_interval_s` is dropped server-side whatever the scope; LED and runway are still always dropped; the resolver bounds are unchanged. Personalisation has no Refresh card; the Console Device page keeps it. Ledger row R2-20 recorded as "owner answered (D23): administrators only".
- **Page** (`pages/personalisation_cards.py`, new, called from `config_page._render_display_scope`): nav, four section cards carrying `data-dirty-section` (Look, Special looks, Calendar, Screen; the save bar names them). Special looks and Calendar hold their existing markup unchanged (the rules list in card 2, the calendar row in card 3; the old shared list was split and the card-2 heading is visually hidden since the card title names it).
- **Look radio cards** (`settings/theme.py`): `look_pick_html` renders the departures look as one look target: large live picture, read-back, "Customise look" opener (hidden until the picker script runs, opens the existing look sheet) and a `role=radiogroup` grid of one native radio card per offered look (name `theme`, `form=settings-form`, small preview with alt text, name, check plus visually hidden "Selected", accent ring from the existing runway-card selection styling). The Arrivals picture keeps its own Change control and table; one shared look sheet. 2, 3 and 4 columns at 360, 700 and 1280 px.
- **Screen card**: the instant display switch (same `/quick/display` route, `return_to=/display`); its muted line is the switch's own state text so it flips with the switch.
- **Display post**: `config_page._resolve_timezone` still refuses an invalid zone but never writes one on a Display post, so saving Personalisation cannot change the time zone (R21).
- **CSS**: additive, existing tokens; rail of 14rem from 960 px, cards at most 56rem; on a phone the large picture is smaller with its read-back beside it so the first row of looks is on the first screen (needed for the 3-action count); look sheets inside a card open under their picture from 700 px.
- **Pins**: `render_baseline.json` moved for the 8 Display entries only (diff reviewed); sign-in digests did not move.

## Tests

- New `test_personalisation_page.py` (11): title, nav, four cards and current lines for administrator and user, French, look radios (one per theme, selected word, previews), save of a look, Screen switch, no Refresh/place/quiet/LED control, a user's wake interval refused for each scope, R21 both directions over HTTP.
- New `test_browser_personalisation.py` (17): 360 and 1280 px, EN and FR, light and dark: no overflow, every look card, nav link, Customise look and the Screen switch at least 44x44 and owning its centre, grid column counts; tap a look, bar names Look, Save persists after reload; nav links reach their cards; Customise look opens the sheet and Escape returns focus; a sheet choice checks the matching card.
- `test_user_view.py` / `test_user_view_http.py`: placement rule, user wake interval dropped for display/device/all scopes, administrator change within bounds on the Device page (below the minimum refused), no Refresh card on /display for either role.
- Moved in place (subject changed): config-page 01/03/04/04b/05 tests and helper (new card order, departures as radio cards, three tables instead of four, dirty sections), display-looks and detection-card tests, i18n and app-04 page-title cases, browser display-looks / ux_01 / ux_02 / ux_03 / ux_04 and the U4-look step test (now 3 actions, `MEASURED_U4_LOOK = 3`). The ux_04 card-title test now expects Display's four cards to share the Device cards' title style.
- CI fix requested by the orchestrator: `test_u4_change_a_setting` (Home quiet-hours dialog) waited for `quiet_window_saved` in `location.search`, which flash-cleanup removes; it now wraps Save in `expect_navigation()` and waits for the closed dialog and the stored start time. Own commit 4c79f62; 3 runs in a row plus 4 parallel runs green; step counting unchanged.

## Deviations from Plan

1. **Card titles keep the existing settings-card title style** (serif `text-heading`), not "16px sans semibold" from UI-SPEC 11: `test_a_settings_card_title_renders_identically_on_both_settings_pages` pins one title style across Display and Device and the plan forbids weakening tests. The orchestrator may want to decide whether both pages should move to the spec voice.
2. **Quiet-hours group stays registered** in the Display scope's group tuple and the legacy whole-page tuple: the invariant test (live scopes disjoint, union equals the full set) needs it and no live page renders it. The Display scope renders no quiet-hours control either way.
3. **Time zone**: the plan only named quiet hours, place and detection, but R21 also requires the time zone to be untouched; `_resolve_timezone` (above) was added. An invalid zone is still refused (an existing test pins it).
4. **`data-preview-src` on look cards** is the large picture the look shows once selected (not the small card image), so existing preview tests keep their meaning.
5. Departures radio cards reuse the runway card's selection styling (class `runway-card look-pick__card`); the "no runway card on /display" guard in `test_browser_ux_03` now excludes `.look-pick__card`.
6. Removed the orphan French `nav.display` entry (the page title now reuses `nav.personalisation`); new ids are under `display.*` (the i18n area guard requires an existing module).
7. `app.py` untouched.

## Known Stubs

None.

## Gates

ruff, mypy (29 modules), comment-history, function size (931, none over 80), Phase 47 freeze (21 passed): clean. Full `companion test-support stub-server -n auto --no-cov` after the final code state: 7261 passed, 4 skipped (root-only permission-bit tests), 0 failed. New and moved browser tests stressed with 4 parallel runs (40 passed each) and 3 sequential runs.

## Self-Check: PASSED
