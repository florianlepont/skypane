# Phase 61 Plan 87: Fleet desktop as one column of section cards Summary

Owner decision D47 R9-6 (W135, W93), option 1: the Fleet page from 960px is one centred column of coherent section cards with everything inline and nothing repeated; the only dialog left on the selected frame is the confirmation for "Retire this frame". It replaces the 61-77 summary rows that opened dialogs.

## What changed

- **One column (>= 960px):** `.fleet-frame` (max 800px, centred in the main area) holds the frame name header and five section cards in this order: State (connection, battery, flight data), Device and version (model, the update card with the current firmware and its status, then the version history), Settings (the existing wake interval, LED, quiet hours and other device settings, edited inline with the existing docked unsaved-changes bar), Access (owner, co-managers, inline add form, inline Reassign form, the Retire row) and Other frames (compact list of pending and retired frames, whose row menus still open the pairing / re-activate confirmations). Every card uses the same pattern: section label, one glass group of rows.
- **Version history:** collapsed behind a native `<details class="update-all">` whose summary reads "All versions (N)" / "Toutes les versions (N)"; the running release is the update card's headline, so it is not repeated outside the disclosure. An empty history keeps the existing empty state.
- **Nothing repeated:** the owner line under the frame name is gone (the Access section names the owner once); the model was already a single row; the firmware version appears once in the update card; the "Versions" block that used to be separate on a phone is now part of Device and version; the summary rows (device, versions, wake interval, access, other frames) and their duplicate values are removed.
- **Retire this frame:** a danger row at the foot of the Access card ("Retirer ce cadre" / "Retire this frame", hint, outlined "Retire..." link). It opens the existing confirm-only retire dialog, the only dialog reachable from a frame's page. The no-script `:target` card and the Keep/Retire flow are unchanged; the dismiss link now returns to `?frame=<id>&tab=access`. The served (live) frame has no Retire row, as before.
- **Reassign:** an inline form row in the Access card (picker, button, and the sentence that says what is erased) posting to the unchanged reassign route; the actions menu of the header now holds only "Open personal view". The Manage access and Reassign dialogs are no longer rendered on the Fleet page.
- **Removed mechanism:** `companion/fleet_summary.py` (summary rows, dialog wrapper, wake/versions/access value helpers), its CSS (`.fleet-sum*`, `.fleet-dialog*`, `.fleet-block--sums`, the inline-dialog `display: contents` rules, the `details.fleet-other` rules), the `data-modal-submit` / `data-modal-reset-close` handlers in `modal.js`, the Other frames dialog, the `admin_fleet.sum_*` and unused reassign/retire strings.
- **Phone unchanged in structure:** State / Settings / Access sub-tabs with the same sections. The State tab now holds State and Device and version (the separate Versions block moved into Device and version); the Access tab holds Access and Other frames (a section instead of a collapsed disclosure).
- **i18n:** new `update.all_versions`, `admin_fleet.retire_this_frame`, `admin_fleet.retire_this_frame_hint`, `admin_fleet.retire_this_frame_action` (EN and FR). The render baseline and goldens were regenerated.

## Tests

- New `companion/test_browser_fleet_sections.py` (19 tests): the five sections present once each in order, same x and width, 640-840px wide and centred, at 1280 and 1440, EN/FR, light/dark, no overflow; no fact duplicated in the column (model, frame name, owner, versions, setting headings); the version history is a collapsed native disclosure (EN and FR labels, opens to 2 rows); settings edited inline open no dialog and the dock Save persists; Retire opens the only dialog, Escape closes it; the served frame offers no Retire row; no-script behaviour; phone keeps its three tabs with the same sections; 360px fit.
- Updated in place: Fleet view / page / tabs / dirty-bar / dialogs / co-managers / update browser tests, console groups, contrast edges, LED switch, motion, toasts, ux_01, ux_04; `test_console_fleet_view.py`, `test_console_fleet_page.py`, `test_co_managers_page.py`, `test_ui_modal.py`.
- Deleted tests and reasons: `companion/test_browser_fleet_rows.py` (all 17 tests: they pinned the summary rows, their chevrons, labels and the dialogs; the mechanism is removed and the new sections file covers the replacement); `test-support/fleet_rows_support.py` (helper for those dialogs); `test_keep_current_owner_dismisses_without_changing_anything` and the Reassign case of `test_dialogs_fit_and_every_control_is_44px` (the Reassign dialog no longer exists; `test_reassign_is_inline_and_needs_no_dialog` replaces them); `test_fleet_offers_manage_access_in_the_detail_menu_with_a_dialog_per_frame` and the Manage access dialog open-state tests (replaced by inline Access section tests); the Fleet "Other frames dialog" assertions.

## Deviations from Plan

- **Reassign has no confirmation:** the owner decision allows one dialog (Retire). Reassign is therefore an inline form with its consequence sentence shown above the button (for a frame that is not the served one, "settings, history and gallery on this frame are erased"). Flagged for owner review.
- **Other frames rows keep their row menus**, whose Re-activate / Pair items open the existing confirmation / pairing dialogs (they are not editing dialogs).
- **System view and the owner line:** the Other frames section is not shown on the System view; the owner line was dropped from the header to avoid repeating the Access section.

## Known Stubs

None.
