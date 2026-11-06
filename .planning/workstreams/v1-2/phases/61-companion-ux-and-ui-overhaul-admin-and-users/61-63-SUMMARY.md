# Phase 61 Plan 63: Manage access sheet, drawn frame picture, Account relationship Summary

Owner round 6 (W61 to W63) is answered: the Manage access dialog is rebuilt as a proper phone sheet on the grouped-list components, the small frame picture is a portrait frame again everywhere, and Account shows who owns and who co-manages.

## What changed

- **W62 Manage access sheet** (`co_managers_card.py`, `style.css`). Reproduced at 390x844 (EN/FR, light/dark). Real defects found: the title sat only 22px under the sheet edge with the drag handle on top (tight against the 28px corners), the body was a nested white card inside the sheet with a long purpose paragraph, the Remove action was a heavy grey pill, the add form was a loose label/field/hint/button stack, Done floated under a lot of empty space, the sheet did not scroll inside (the whole dialog scrolled, head included) and the scrim is the shared 50% black (kept: the stylesheet rules allow a backdrop blur only inside the glass `@supports` block). Now: `dialog.modal.access-sheet` (head fixed, 28px top padding on a phone, `max-height: 85dvh`, the body scrolls inside, the shared safe-area bottom padding), the body is ONE labelled glass group ("Co-managers") of rows: owner (Owner pill), each co-manager (You/Disabled pills, trailing quiet Remove in the danger colour, 44px target) and a stacked add row (field or the administrator's select, one hint line, full-width primary Add co-manager), then a full-width secondary Done. The Fleet Access block shares the rows, so it gets the same quiet Remove. The old card builders (`access_section_html` and helpers) and the `.co-manager__row`/`__who` rules are gone. Every form, route, CSRF field, validation, permission rule, the no-script hash path, `aria-labelledby` and the focus return are unchanged.
  - Finding: a co-manager of a frame cannot open Manage access (the Account row offers Leave frame; that rule is untouched). The owner's screenshot was of an owner or administrator viewer, which is what the tests use.
- **W63 drawn frame** (`style.css`). Cause: `.frame-row__pic` (28x38) and `.account-frame__pic` (40x52) used `--radius-control` (14px), half the 28px width, so the box was a capsule. New token `--radius-frame-pic: 5px` (inner screen 2px/3px) used by both. The Home hero and Console Fleet use the same popover rows; no other user of the helper exists.
- **W61 Account** (`account_page.py`, `i18n_fr/account.py`, `style.css`). Each frame row has an Owner / Co-manager pill (FR Propriétaire / Co-gestionnaire); the Role row keeps "User" and gains "Co-manager of 1 frame" / "of N frames" (FR de 1 cadre / de N cadres). No other address is shown.

## Tests

New `companion/test_browser_access_sheet.py` (18 tests): sheet geometry at 390x844 and 360x640, EN/FR, both themes (title top at least sheet top plus corner radius, sheet inside the viewport, nothing overflows sideways, every control at least 44px and reachable inside the sheet, one group and no inner card, Remove is borderless with a transparent fill, Done closes and focus returns to the opener); add and remove flows in the sheet (390 EN light, 360 FR dark); the drawn frame measured in the popover and on Account at 360/390/1440 in both themes (aspect 0.65-0.8, radius at most 8px, bezel 2-6px; verified red with the old 14px radius); Account marks in EN/FR for a co-manager and an owner. New served-HTML tests in `test_co_managers_page.py` (marks, Role line, FR, plural).

Updated in place (none weakened, none removed): `test_co_managers_page.py` (rows are now `ul.group > li.row`; the dialog test asserts one group, the section label and no inner card; the token test now accepts the extra tokens the Remove rule uses and checks every `var()` against an allow-list; frame names are read without the new pill), `test_account_page.py` (same name helper), `test_browser_co_managers.py` (containment script now walks the new rows, so it is not vacuous; the removed-address check reads the address spans, since the add select lists every address), `test_browser_account_frames.py` (row selector). `test_sign_in_surfaces` digests and the render baseline were regenerated deliberately where the stylesheet moved.

## Step counts

No count moved; see `61-STEP-COUNTS.md`. UI-SPEC revision 6 added.

## Screenshots

`/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots63/` (`dialog|popover|account-rows-{en,fr}-{light,dark}-{before,after}.png`, 390x844). The popover shots set the theme before navigation, so the popover itself renders in the light theme in the dark runs.

## Deviations

- The first focus of the sheet is still the e-mail field (the existing test pins it); on iOS the keyboard may open with the sheet, but the body scrolls inside the 85dvh sheet so the Add button stays reachable.

## Verification

ruff, mypy, comment-history, function-size and `test_phase47_freeze` green; `companion/app.py` unchanged (1473 lines). Full suite `companion test-support stub-server -n 4`: 8441 passed, 4 skipped (root-permission skips), 0 failed (a first run showed two stylesheet-structure failures from a duplicated selector and a backdrop blur outside the glass block; both fixed).
