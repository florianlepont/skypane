# Phase 61 Plan 43: Console Users as a table, manage modal removed

Owner decision D32 and feedback W19 (mockup U1): the Users page is a table; the per-user "Manage user" modal (Role / Access / Sign-in) is removed.

- **Page (`companion/pages/users_page.py`):** one `<table class="users-table">`; each row has the avatar initial and email (with Invited / Disabled / You pills), a Role select, the frame count, the last sign-in (relative time, "Never signed in"), an Active switch and a "..." menu. From 70rem (1120px) it is a table, below it every row is a card (role select, Active switch and menu kept).
- **Role:** a normal form posting to the existing role route; `data-autosubmit` makes it submit on change (list-filter.js now wires `[data-autosubmit]` even on a page without a filter input, and the Users page loads it). Without script a `<noscript>` "Save role" button shows per row.
- **Active:** a `role="switch"` submit button posting to the existing disable (when on) or enable (when off) route. No confirmation, as the old Manage dialog had none.
- **"..." menu:** native `<details class="row-menu">` (Escape closes and refocuses via modal.js); holds only "Unlink identity" (shown when an identity is linked). Re-invite and delete do not exist as routes, so they were not added.
- **Guards kept:** the signed-in administrator and the last active administrator show "This is you." / "The last active administrator cannot be changed." in place of the select and get a locked switch; the server guards, flash messages and audit rows are unchanged.
- **Strings:** new `admin_users.col_*`, `never_signed_in`, `role_of_aria`, `active_aria`, `more_actions_aria`, `table_note` (EN/FR); the Manage user, section and sentence strings were removed.
- **Tests (adapted in place):** `test_console_users.py`, `test_browser_users_page.py` (role saves on change, switch, menu incl. keyboard, no-script, 360/1280 x EN/FR x light/dark geometry and 44px), `test_browser_console.py` tap target, `test_browser_overhaul_sweep.py` (manage-dialog case dropped), new step-count test A9 in `test_browser_overhaul_steps.py` (4 steps down to 2).
- **Docs:** `61-UI-SPEC.md` and `61-STEP-COUNTS.md` updated. The render baseline was regenerated (no Users page is pinned in it, so it did not change).

## Deviations / notes

- Re-invite and delete from the mockup's menu are not built: no such routes exist (expand-only, no new backend actions).
- The invite dialog and flow are unchanged. `ui_modal.sections_dialog_html` is still used by other pages; the `.modal__section` CSS was removed with its only user.
