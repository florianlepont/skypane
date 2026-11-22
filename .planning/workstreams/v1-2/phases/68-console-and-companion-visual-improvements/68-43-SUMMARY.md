---
phase: 68-console-and-companion-visual-improvements
plan: 43
subsystem: companion
tags: [users, phone, sheets, keyboard, sidebar, i18n]
requirements: []
key-files:
  created:
    - companion/test_browser_sheet_keyboard.py
  modified:
    - companion/pages/users_page.py
    - companion/ui_modal.py
    - companion/ui_nav.py
    - companion/static/modal.js
    - companion/static/style.css
    - companion/static/style-admin.css
    - companion/static/style-c-console.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-22
---

# Phase 68 Plan 43: Users page-level differences 14 to 17 and the keyboard lift for every sheet

There was no PLAN file: the owner's brief was the plan. It closes the "page-level differences"
14, 15, 16 and 17 of `68-28-SUMMARY.md` (against the owner-approved `68-MOCKUP-users.html`) and
extends the on-screen-keyboard lift from the compact dialogs to every bottom sheet with a field.

## What changed

1. **Phone header (difference 14).** The full-width "+ Invite a user" bar is a 44 px square dark
   "+" button beside the title, as drawn. The link carries an icon span and a label span; a phone
   hides the label by clipping (it stays the accessible name, "+ Invite a user" / "+ Inviter un
   utilisateur"), a wide screen hides the icon. Same invite dialog, no new string. The stacked
   header rules (`page-header__actions--stack`) are gone.
2. **Phone list (difference 15).** Below 79.5 rem the table is one card and each person is one row
   with a divider: avatar, address, status pill, then a single "Role · frames" line, the Active
   switch and the "..." menu. The role select, the frames cell and the last-sign-in cell are not
   shown there (the mock shows none of them on a phone); the switch stays, as drawn. The role is
   changed from the person's menu: a new item, "Make administrator" or "Remove rights" (the existing
   confirmation strings, so no new i18n id), that posts the other role without the confirmed mark
   and lands on the existing role-confirm dialog. It is absent for the signed-in administrator and
   the last active administrator. When the confirmation closes, focus goes to the select if it is
   on screen and to the person's menu button otherwise (`data-modal-return-focus` now accepts
   several ids, the first one on screen wins). The guard sentences moved from the (hidden) role
   cell into the person's cell, so the disabled self switch still has a visible description target.
   Reset sign-in stays hidden for never-signed-in rows (owner decision).
3. **Desktop role select (difference 16).** A bordered chip with a chevron (`icon-chevron-down`,
   no new sprite symbol) around the same native `<select>`: still a real, keyboard-operable control
   with the no-script Save button.
4. **Sidebar (difference 17).** The space switch is now "My frames | Console" in that order, as
   drawn (`ui_nav._SPACE_SEGMENTS`; tests updated). The mock's missing System item is a mock
   artefact: the real shell keeps every item the role needs (Fleet, Users, Editor, Audit log,
   System, Account), so no navigation was removed. The Fleet attention dot and the sample time
   wording ("just now" is data) are real data, not a layout requirement.
5. **Keyboard lift.** `modal.js` sets `--keyboard-inset` on every open `dialog.modal` (was
   `.modal--compact` only), and the focus handler scrolls the focused field into view in every
   dialog. CSS: the shared phone sheet rule (`inset: auto 0 var(--keyboard-inset, 0px)` and the
   matching `max-height`) and the Fleet/Account detail sheets (`dialog.access-sheet`, whose own
   `max-height` rule used to override the phone rule). Sheets with a field (found by reading every
   `ui_modal` call site and opening each dialog): invite a user, add a frame, reassign a frame, add
   a co-manager, manage access (owner inline add form), quiet hours, rename an airline.

## Tests

- New `companion/test_browser_sheet_keyboard.py`: one test per sheet (7), each opens the sheet from
  its address at 390 px with an emulated keyboard (layout viewport unchanged, visual viewport at
  60 %), focuses the sheet's first field and asserts the field and the whole sheet sit above the
  keyboard's top edge, then that closing the keyboard puts the sheet back on the bottom edge. A
  probe with the old compact-only selector confirms the add-frame test fails without the change.
- Updated for the new behaviour (assertions changed, none loosened or skipped): the role-change
  helper of `test_browser_users_page.py` (select on a table, person's menu on a card; focus return
  now parametrised for both), the no-script flow (both layouts), the invite-button geometry (one row,
  44 px square on a phone, the words on a wide screen, accessible name in both), the 44 px test, the
  menu one-line test (skips the hidden phone-only item); `test_browser_users_rows.py` (a card's
  detail line replaces the frames and last-sign-in cells, whose one-line rules still hold for the
  table); `test_browser_audit4_fixes.py` (a card shows its whole role name in the detail line;
  the select-width check lives on in `test_browser_french_fit.py`); `test_console_users.py` (header
  markup); the space-switch order in `test_nav_spaces.py`, `test_space_switch.py`,
  `test_browser_space_switch.py`, `test_browser_nav_spaces.py`; the phone role-change step count
  in `test_browser_overhaul_steps.py` (A9: Users tab, person's menu, menu item, confirmation = 4;
  it was 3 with the select).
- The render baseline was regenerated once at the end; the stylesheet structure rules and the
  symbol-count pin pass unchanged.
- Counts and gates: see "Verification" below.

## Deviations and findings (Rules 1-3)

- A pre-existing rule (`dialog.access-sheet[open]`, specificity above the phone sheet rule) kept
  the Manage access sheet from being lifted; its `max-height` now also subtracts the keyboard inset.
- The solid card colour on a phone is kept deliberately (the off-switch track must hold 3:1 against
  a flat surface, `test_browser_contrast_edges`): the card does not take the translucent glass fill.
- The card's first row keeps a transparent divider so all cards are as tall as they need.
- On a narrow card the status pill ("Invited, not signed in yet") may wrap to two lines instead of
  running under the switch.

## Remaining divergences from the mock (honest list)

- Phone: an address wraps at "@" and "." (the earlier owner-reviewed rule: never cut a word) where
  the mock cuts it with an ellipsis; the card is 24 px from the screen edge (shell padding) against
  16 px in the mock; the "..." menu icon is the shared vertical one (the mock draws horizontal
  dots; a new symbol would change every page's markup); the signed-in administrator's switch stays
  aligned with the others instead of moving to the right edge; on a very narrow card "Role · frames"
  can break after the dot ("Administrator · / 1 frame").
- Desktop: the role chip is 44 px tall (the 44 px hit-area rule, mock 40 px) and as wide as the
  longest role name (a native select cannot size to its selected option without `field-sizing`, which
  made the French "Administrateur" 1 px too narrow); the row is 65 px against the mock's 68 px; the
  row menu is the shared vertical-dots one.
- The sidebar keeps System, the Fleet attention dot and the real Account order.
- Token radius (22 vs 24 px) and the dialog title size are untouched (Phase 68.1).

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p43/mock/` and
`.../p43/built/` (separate images, 390 px phone and 1440 px desktop, EN and FR, light and dark,
device scale factor 1): `users-*`, `menu-*`, `invite-*`, `confirm-*` (the mock has no phone
menu or role-confirm figure; the built phone confirm is the delete sheet, as the mock's phone
figure), and `built/keyboard-<sheet>-phone-<lang>-<scheme>.png` for the seven sheets with the
emulated keyboard.

## Verification

- Full core suite (`SKYPANE_REQUIRE_BROWSER=1 SKYPANE_TEST_GROUP=core ./scripts/run-all-tests.sh`):
  12524 passed, 7 skipped (the skips are the suite's existing ones), 0 failed.
- Browser shards 0 to 4 of 5: 1204, 765 (1 skipped), 753, 663 and 747 passed = 4132 passed, 0
  failed. Shard 3 was re-run in full after one more test (`test_browser_console.py`: the phone role
  control and the French space-switch order) was adapted; the first pass of shards 0 to 2 and 4 was
  made on the same code.
- ruff, mypy (49 source files), function-size gate (1221 functions, none over 80),
  comment-history guard: all pass. `companion/app.py` is unchanged at 1497 lines; no JS file is
  near 1500 lines.
