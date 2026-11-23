# Phase 68 Plan 50: Rename frame as a dialog (a sheet on phones) Summary

Rename is no longer a page: it is one compact dialog (a centred card on a desktop, a bottom sheet on a phone) opened from the Home pencil, the Fleet header pencil and the "Rename this frame" link of Manage access on Account, built with the shared `ui_modal.dialog_html` (variant `compact-top`), with the POST route, authorization and CSRF unchanged. Owner decision of 2026-11-23, follow-up of 68-49 item (a).

Captures: `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p50/{before,after}/` (390 and 1440 px; EN/FR; light and dark). `before/` is the old Rename page opened from each entry point (`home-`, `fleet-`, `access-`); `after/` is the open dialog from each entry point, plus `home-error-*` (refused name reopened).

## What changed

- `companion/pages/frame_name_page.py`: the page renderer is replaced by `dialog_html(device_id, name, return_to)`. Title, one labelled name field (`maxlength=40`, no standing help; the limit shows only as the validation error), Save and Cancel (the compact variant's side by side buttons), field focused, close cross absent (compact), `return_on_close`, and the new `scrim_close`. It renders open, with the error and the typed value, when the request carries the refused-name query (`rename`, `rename_error`, `rename_value`, read from the request query, so no host page was edited to plumb it). `opener_href`/`opener_html` give the entry points their hash link (`#dlg-rename-<id>`, `data-modal-open`).
- `companion/frame_rename.py`: POST success is unchanged (303 to `return_to`, flash/console toast). A refused or failed name is now a 303 back to the page the person was on with the refused-name query (was a 400/500 Rename page). GET `/devices/<id>/frame/name[?return_to=]` no longer renders a page: it 303s to the allow-listed `return_to` (or the default Account / Fleet settings) with `#dlg-rename-<id>`, so old links, bookmarks and the CSRF "reopen" link still work. Same route table: no new route, access matrix and route table tests untouched.
- Entry points: `home_title.rename_dialog_html` (rendered after Home's blocks so the staggered reveal is unaffected, added in `home_page.render`), `fleet_frames_list.head_html` (dialog after the head), `co_managers_card.manage_access_dialog_html` (link opens the dialog, which stacks over the sheet like Remove this frame).
- `ui_modal.dialog_html(scrim_close=True)` and `modal.js`: a dialog holding a field ignored a tap on the scrim; a one-field dialog where cancelling discards now closes on it (`data-scrim-close`). Two focus/target fixes found by the new tests, general to every dialog the page opens on load: (1) a server-rendered open or hash-targeted dialog had spent its autofocus, so the browser parked the focus on the dialog; for one second the focus is sent on to its autofocus control (the invalid field after a refusal). (2) closing a dialog the address opened left it shown through the stale `:target` (scripts-blocked in-page card); it is now hidden through the CSSOM and cleared on the next open.
- Removed: the unsaved-changes guard and Save bar for Rename (a one-field dialog; cancelling discards), `frame_name.back` (EN source and FR), the `/frame/name` entry of `page_styles`, the page-only `render`/`FORM_ID`.
- No new strings (title, label, error, failed, action reuse existing ids; Save/Cancel reuse `look.save`/`display.cancel`).

## Tests

Replaced or adapted (each, all to the new intended behaviour):
- `companion/test_frame_rename_and_users_switch.py`: invalid names now assert the 303 reopen with the field error, typed value and nothing stored (was a 400 page); the "rename page shows name/save bar/French" test became the dialog equivalent (equal buttons, EN/FR); the no-help test reads the dialog; the default-name, never-translated and hostile-name tests read the dialog on Home; the Manage access / Fleet header test asserts hash links and dialogs; the hostile/unknown `return_to`, normal-user-never-console, return-target-cannot-open and carry-return_to tests assert the GET route's redirect target; refused-name-keeps-origin asserts the reopen target and the dialog's own `return_to`/Cancel. New: refused name comes back as typed, a page without the query has no error.
- `companion/test_home_title.py`: pencil is a hash link to a dialog with the right form action and `return_to`; the "frame name row is gone" test now ignores the dialog's own "Frame name" label.
- `companion/test_audit3_fixes.py` (rename link is the hash link), `companion/test_console_fleet_page.py` (header Rename is the hash link), `companion/test_page_structure.py` (page-title test replaced by "the rename route opens the dialog on the page it came from"), `companion/test_device_routes.py` (the prefix crawl allows a `return_to` that is the frame's own Home, the Rename dialog's field).
- Browser: `test_browser_home_title.py` (pencil, cancel/Escape/scrim, save, refused name, hostile `return_to`, no-script and admin-from-Fleet rewritten for the dialog; the "browser back from the rename page" test removed with the page), `test_browser_audit4_fixes.py` (the rename cases of the form-page bar tests moved to the Special look page; "back link sits the same on the rename and special look pages" removed, `.form-back` now exists on one page only), `test_browser_fleet_users_fixes.py` (three rename-page tests removed, replaced by the new file), `test_browser_leave_dialog_pages.py` (the rename leave-dialog test removed: no Save bar there any more), `test_browser_components_page.py` (field fills its dialog and Save is tall enough), `test_browser_fleet_page.py` (no-script header link opens the targeted dialog).
- New `companion/test_browser_frame_rename_dialog.py` (86 tests): per entry point (Home, Fleet header, Manage access) at 360 and 1280 px, EN/FR, light/dark: sheet vs card geometry, field focused, equal Save/Cancel, 44 px targets, no sideways scroll; keyboard lift (`--keyboard-inset`); Save returns to the page with the new name; Cancel, Escape and scrim discard; refused name reopens with error then saves; closed refusal leaves a clean address; scripts blocked: link opens the dialog, Save and Cancel, refused name shows the error; old rename address opens the dialog and Cancel closes it.

Results: all non-browser `companion` and `server` tests 11311 passed (one failure fixed, see deviations); browser files above and every browser file using dialogs plus focus (34 files) passed; ruff, mypy, function-size, comment-history clean. `companion/app.py` is 1497 lines, `modal.js` 745. Render baseline regenerated once (`companion/testdata/render_baseline.json`).

## Deviations

- [Rule 1 - Bug] The new tests exposed the two `modal.js` defects above (focus after a reopen or hash open; stale `:target` after closing); fixed generally, covered by the new file.
- The refusal response is a 303 to the host page (the pattern of the other sheets), not a 400/500 page, so the typed value travels in the query (cut to 40 characters).
- Save and Cancel are the compact variant's equal-flex buttons; their rendered widths differ by 2 px (the border), the same as the Users page dialogs; the test allows 2.5 px.

## Owner decisions needed

- The Account page has no frames-list pencil: its Rename is only the link inside Manage access (as before). Say if the Account row should get its own pencil.
- Stale bookmarks to the old Rename page now redirect (GET stays on the route table). If you prefer a 404, the GET route and its access-matrix rows can be dropped.
- Equal widths to the pixel would mean changing the shared compact-dialog CSS (affects the Users dialogs).

## Self-Check: PASSED
