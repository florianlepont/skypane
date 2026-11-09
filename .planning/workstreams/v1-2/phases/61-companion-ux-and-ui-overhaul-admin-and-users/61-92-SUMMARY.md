---
phase: 61
plan: 92
subsystem: companion Fleet and Users
tags: [fleet, users, access, versions, rename, owner-W149, owner-W150, owner-W151, audit-F08-F11, audit-F15, audit-F29, audit-F30, audit-F33]
key-files:
  created:
    - companion/frame_rename.py
    - companion/pages/frame_name_page.py
    - companion/i18n_fr/frame_name.py
    - companion/test_frame_rename_and_users_switch.py
    - companion/test_browser_fleet_users_fixes.py
  modified:
    - companion/pages/fleet_page.py
    - companion/console_fleet_view.py
    - companion/pages/co_managers_card.py
    - companion/pages/update_page.py
    - companion/pages/users_page.py
    - companion/console_users.py
    - companion/static/quick-switch.js
    - companion/static/style.css
    - companion/routes.py
    - companion/testdata/render_baseline.json
---

# Phase 61 Plan 92: Fleet and Users Summary

Reassigning a frame is a button beside the owner, versions are a table with the action always in view, a frame can be renamed (owner and administrators) through the common Save bar, and the Users Active switch acts in place.

## What changed

- **Access (W150, F08).** The owner row carries a quiet "Reassign" button that opens one confirmation dialog (picker of the new owner, the sentence saying what is erased, "Keep current owner"). "Add co-manager" is one row that opens its own dialog (picker of invited people for an administrator, typed address for an owner). The two stacked form rows are gone from Fleet. The Manage access sheet on Account keeps its inline add form. A person row wraps its action under a long address on a phone. Reassign is still an administrator-only server action (Fleet is the administrator console); the owner-facing equivalent stays "remove frame / ask an administrator". After a reassign or a co-manager change the redirect lands on the frame's Access tab (workflow K4).
- **Versions (W149, F09).** The Fleet "All versions" disclosure is replaced by a table (Version | Released | action). Install and "Roll back" (accessible name "Roll back to <version>") are visible on every row; the running row has the Running badge and no action; notes sit behind one optional disclosure. The standalone Releases page keeps its existing list. New strings EN/FR (`update.col_*`, `update.notes_n`, `update.roll_back`).
- **No "unknown time" (workflow R1).** With no clock time to name, the scheduled card and the install confirmation use sentences without a time ("installs at the next wake") instead of "around an unknown time"; the string is removed.
- **Aircraft-type rows (W151, F10).** A type that shows its airline's picture says so as a tooltip and to assistive technology instead of a second wrapped line, so type rows keep the airline row's height.
- **Users (F11).** Column widths rebalanced (action columns sized for 44px targets, role select no longer truncated, frames cell wraps), emails wrap with the full value as title instead of an ellipsis. The Active switch is now a quick switch: it flips in place over fetch (the two routes are named in `data-quick-action-on/off`, the Disabled/Active mark flips with it, the CSRF token is sent, a refusal rolls back with the existing toast); without script it still posts and redirects. "Delete user" is no longer offered on the signed-in administrator's own row (nor its dialog).
- **System view (F15).** One centred column (no masonry hole), outcome counts right-aligned ("Both agree ... 86"), and the identification percentage is never "100.0%" beside a to-resolve count.
- **Pending and retired frames on a phone.** The Other frames section moves to the State tab (the landing tab) so it is reachable without hunting; the section layout is unchanged.
- **Rename a frame.** New page `/devices/<id>/frame/name` (owner or administrator; co-manager and strangers get the unknown-path page): one name field, the common tracked Save bar, validation (trimmed, blanks collapsed, 1 to 40 printable characters), error in place, `device.rename` audit row ("from"/"to") in the same transaction as the update. Expand-only: it writes the existing `devices.name` column through `fleet_db.rename_device`; nothing the frame reads changes. Entry points: the Fleet header "Rename" link and a "Rename this frame" link in the owner's Manage access sheet. Bilingual (`i18n_fr/frame_name.py`), audit label "Frame renamed / Cadre renomme".
- **F29.** The Fleet frame header is two visible link buttons ("Open personal view", "Rename") instead of a one-item menu, and no longer repeats the frame name.
- **F30.** An Account frame row that carries an action link shows no chevron.
- **F33.** `/devices/<id>/update` moves an administrator to `/fleet?frame=<id>` (a person who is not an administrator is moved like from `/update` itself).
- **Workflow findings.** Pairing, reassign and retire messages name an unnamed frame "Unnamed frame" (never its id); the wake slider's native range has `step="any"` so a typed 700 s keeps the thumb at 700 (dragging and keys still use the 60 s step).

## Tests

- New: `companion/test_frame_rename_and_users_switch.py` (16: rename by owner/administrator, audit, validation cases, access refusals, page markup EN/FR, hostile name, switch 204 vs redirect, own-row delete, pairing name) and `companion/test_browser_fleet_users_fixes.py` (switch in place at 360/1280 EN/FR, own-row delete, rename page bar/save/cancel/error at 360/1280 EN/FR, typed wake interval, System view column). Added to `test_update_page.py` (versions table, no unknown time) and `test_co_manager_access.py` / `test_access_matrix.py` (the Update address under a prefix).
- Updated in place (their subject changed, none weakened): `test_browser_update.py` (table instead of disclosure rows), `test_browser_fleet_sections/tabs/page/dialogs.py`, `test_browser_console_fleet_view.py`, `test_browser_co_managers.py`, `test_browser_users_cards/page.py`, `test_browser_airline_table.py`, `test_co_managers_page.py`, `test_console_fleet_page.py`, `test_console_users.py`, `test_console_lifecycle.py`, `test_console_wording_sweep.py`, `test_config_page_05.py`, `test_device_routes.py`, `test_route_table.py`, `test_csrf.py`, `test_i18n.py`, `test_access_matrix.py`. Render baseline regenerated (new `/frame/name` unauthenticated rows added to the snapshot script).
- Screenshots: `scratchpad/shots92/` (`before_*`, `after_*` at 360 and 1280, light and dark).

## Deviations

- Reassign stays administrator-only (the server permission is unchanged; owners cannot reassign by design, "They cannot retire or reassign it"). The button therefore appears on Fleet only.
- The rename page is a dedicated page with the page's own tracked Save bar rather than a field inside the Fleet Settings form (a second tracked form on Fleet would fight the settings bar for the single floating bar).
- `/devices/<id>/update` is matched in `routes.match()` by a narrow special case (the retired page stays a global route) rather than made device-scoped, which would have changed the route-table contract; the "global routes do not match under a prefix" test carves it out explicitly.
- A co-manager visiting `/devices/<id>/update` is now moved (303 to the frame Home, like `/update`) instead of seeing the unknown-path page.

## Known Stubs

None.
