# Phase 61 Plan 81: Delete user and owner removes a frame Summary

Owner decisions D-I (W103) and D-J (W91): an administrator can delete a user from the Users "..." menu, and a frame's owner can remove their own frame from the Manage access dialog, each behind a confirmation dialog.

## What changed

- **Delete user (D-I):** `Delete user` / `Supprimer l'utilisateur` sits below "Reset sign-in" in the Users "..." menu as a quiet danger item; every row now has the menu. It opens a confirmation dialog (`dlg-delete-user-<id>`, opaque, sticky actions) stating what happens. `POST /users/<id>/delete` is admin-only with CSRF. `fleet_db.delete_user_guarded` refuses the signed-in administrator and the last active administrator (same guard messages as role/disable) and refuses with `UserOwnsFrame` while the person owns a frame (the flash names the frame and says to reassign or retire it). Otherwise, in one transaction: sessions deleted, co-manager rows deleted (one audit row per frame, reason "Person was deleted"), locations they created become unowned (the foreign key would otherwise block), the user row deleted. No schema change. The audit row `user.delete` uses the e-mail as its target id (the id means nothing afterwards); a refusal is audited as a denied row with the same target.
- **Owner removes a frame (D-J):** the owner of a non-live frame sees a quiet danger link `Remove this frame` / `Retirer ce cadre` under the people group of the Manage access dialog (a link, not a second surface), opening a stacked confirmation. `POST /devices/<id>/frame/remove` (owner-or-admin at the gate, owner only in the handler; CSRF) reuses `fleet_ops.retire_frame` with a new `owner_user_id` check performed inside the retire transaction (a frame reassigned meanwhile gives 404-style refusal). The frame is parked as a retired pending row keeping its history, co-managers lose access (audited), the audit row `device.retire` carries `via: owner`. The live frame is refused and audited by `retire_frame`, and the button is never offered for it. Co-managers keep "Leave frame". An administrator who is not the owner is refused with a flash. Flashes: `frame_removed`, `frame_remove_refused`, `frame_remove_live` (Account page).
- **Phone card layout:** with the menu now on every row, the Users card puts the status pill under the email (as the desktop table already did) so a short address is not truncated at 360px.
- EN/FR strings in `i18n_fr/admin_users.py`, `co_managers.py`, `admin_lifecycle.py`; audit labels for `user.delete` and the `user_deleted` removal reason.

## Tests

New: `companion/test_console_users_delete.py`, `companion/test_owner_remove_frame.py`, `server/test_fleet_delete_user.py`, `companion/test_browser_delete_user_remove_frame.py` (23 browser tests at 360 and 1280, both themes and languages). Updated in place: access matrix rows (users delete, frame remove), route table, CSRF and device-route lists, audit reason labels, flash tests, Users page tests (menu on every row), render baseline, and the overhaul sweep (the removed delete-resolution dialog surface is replaced by the Delete user and Remove this frame dialogs).

Screenshots: scratchpad `shots81/` (delete-user, access, remove-frame at 360 and 1280).

## Deviations from Plan

- The remove-frame action is a plain link under the people group rather than a row in a second group, because the access sheet is pinned to a single surface by an existing test.
- Plan 61-80's removed delete-resolution dialog surface in the overhaul sweep was fixed here (coordinator request).

## Known Stubs

None.

## Self-Check: PASSED
