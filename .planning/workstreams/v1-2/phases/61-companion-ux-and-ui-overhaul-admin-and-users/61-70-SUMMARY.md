# Phase 61 Plan 70: One toast, one sheet, errors once, focus trap, no time auto-focus Summary

Every action result is the single floating toast above the tab bar, every dialog is a bottom sheet on a phone, a refused pairing code is shown once, Tab loops inside an open dialog, and the Quiet hours dialog opens on its title with 12-hour times fully visible.

**Requirements:** owner decision D42 P08; audit findings F07, F12, F19, F20

## What changed

- One toast: the cookie flash (Users invited, pairing, etc.; `companion/console_flash.py`) was a bare toast in page flow. It is now wrapped in the existing `.toast-region--flash` region, so with scripts it floats above the tab bar (fixed, no layout shift) and without scripts it stays in flow (non-shifting fallback unchanged).
- One sheet: `dialog.calendar-sheet:modal` becomes a full-width bottom sheet with rounded top corners and grabber below 700 px (same padding/safe-area as `dialog.modal`); wide screens keep the centred dialog; the no-script in-page card is untouched.
- Errors once: a refused pairing code (admin Add frame dialog and the user Add a frame page) shows only the inline field error "Code not recognised. Check the code and try again." (`fleet_page.claim_refused_error()`); the docked toast is gone for refusals (kept for the lockout, which has no field error). Other forms already showed a single inline error.
- Focus: `companion/static/modal.js` traps Tab/Shift+Tab inside any open modal dialog (including the calendar sheet), Escape and focus return unchanged. `ui_modal.dialog_html(focus_title=True)` opens a dialog on its title (`data-focus-title`, `tabindex=-1` heading, no ring) unless a control is invalid; the Quiet hours dialog uses it, so the time field no longer takes focus. The two time tiles stack in one column below 700 px so "11:00 PM" is not clipped.
- Also fixed a pre-existing failure from the previous plan: a second `@supports selector(:has(*))` block in `style.css` (runway badge rule) broke `test_style_css_carries_exactly_one_has_feature_query_block`; the redundant wrapper was removed (an unsupported `:has` drops the rule anyway).

## Tests

New `companion/test_browser_one_toast_one_sheet.py` (9 tests): toast fixed above the tab bar and the Users list does not move at 360/390; no-script invite still shows the toast; calendar dialog is a bottom sheet at 390 and centred at 1280; refused code leaves one `.field-error`, no toast, message once; Tab/Shift+Tab never leave the invite dialog and Escape returns focus to the trigger; Quiet hours opens on the H2, not on an input, and times are not clipped at 360/1280. Adapted in place: Quiet hours browser tests (focus on title, Tab trap now rejects body), `test_quiet_hours_modal.py`, `test_ui_modal.py` (+2), `test_browser_user_pairing.py`, `test_browser_ux_quiet_wake.py`, `test_browser_home_state_card.py`. Render baseline regenerated (4 lines).

## Deviations

- The calendar sheet keeps its own `<dialog class="calendar-sheet">` (own JS) and was restyled to the shared sheet look rather than rebuilt on `dialog_html`, to avoid two scripts upgrading one dialog.
- `CLAIM_REFUSED_DETAIL` is no longer rendered anywhere (its text is dropped; the title plus the short instruction is shown).
- Removed the redundant `@supports` wrapper added by the previous plan (see above).

Screenshots: `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots70/` (toast_users_390, calendar_sheet_390, calendar_dialog_1280, quiet_hours_360).

## Known Stubs

None.
