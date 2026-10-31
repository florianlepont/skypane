---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 13
subsystem: companion-console
tags: [locations, ownership, quota, rate-limit, display-picker, audit]
requires: [55-02, 55-09, 55-11, 55-12]
provides:
  - companion/pages/locations_page.py (LocationRow, FormState, LocationsView, render, picker_html)
  - companion/console_locations.py (GET /locations; POST add, edit, delete; display_picker_html; apply_device_location)
  - companion/i18n_fr/admin_locations.py
  - Location picker on the Display page
  - audit keys location.add, location.update, location.delete (numeric target_id); location.update with target type device for an assignment
affects: [55-14]
tech-stack:
  added: []
  patterns:
    - one page for both roles, scoped by row-level ownership; foreign, ownerless and unknown ids answer the unknown-path 404 with the frame scope cleared so the bytes are identical
    - a user's mutation attempts counted by a module-level LockoutThrottle(limit=20, lockout_s=600) keyed by user id
key-files:
  created:
    - companion/pages/locations_page.py
    - companion/i18n_fr/admin_locations.py
    - companion/test_console_locations.py
    - companion/test_location_picker.py
  modified:
    - companion/console_locations.py
    - companion/pages/config_page.py
    - companion/app.py
    - test-support/matrix_rows_locations.py
    - test-support/companion_render_snapshot.py
    - companion/test_route_table.py
    - companion/test_console_shell.py
    - companion/test_user_nav.py
    - companion/test_i18n.py
    - companion/test_account_page.py
    - companion/test_sign_in_surfaces.py
    - companion/testdata/render_baseline.json
    - companion/testdata/update_page_one_type_golden.json
key-decisions:
  - "Admin-created locations are ownerless ('Platform'); a user's are owned by them. Admins are neither capped nor throttled; a user holds at most 10."
  - "Every create, edit or delete attempt by a user counts toward the throttle before any other check (including ids that turn out foreign), so the 21st attempt inside ten minutes is refused with a warning flash and no change. A locked attempt writes no audit row, so the throttle also bounds audit growth."
  - "Ownership is checked before the input is validated on edit, so a foreign id never gets a validation answer."
  - "A location an admin assigned to a user's frame stays selected in that user's picker under the generic label 'Assigned by an administrator' (value kept, name never shown), so saving Display unchanged never clears it and no foreign name leaks."
  - "An admin sees no picker at all while no location exists (Display unchanged); a user always sees either the select or the 'No location chosen.' note."
requirements-completed: [AUTH-05]
duration: ~2h
completed: 2026-10-31
---

# Phase 55 Plan 13: Locations for both roles and the Display picker Summary

Locations page for both roles (an admin manages all, a user only their own, with quota 10, validation, rate limit and audit) and a per-frame Location picker on Display whose assignment goes through `fleet_db.set_device_location_checked`; zones and detection modes are untouched.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 | 256bf57 | `locations_page`, `console_locations` (GET plus three CSRF POST routes, signed-in access, row-level ownership), French, matrix rows, route-table sample, render baselines, 79 HTTP tests |
| fix | 90f2ab5 | `test_account_page` and `test_sign_in_surfaces` expect the user sidebar's new Locations link |
| 2 | fb1cc35 | picker markup in `config_page` (bounded: one call in the Display scope, one helper), `apply_device_location` inside `handle_post`, one-line `app.py` change, 20 HTTP tests |

## Verification

- Full non-browser suite (`companion server test-support scripts stub-server -m "not browser"`): 6298 passed, 7 skipped (root-permission skips), 4 failures (`test_account_page` x2, `test_sign_in_surfaces` x2) that described the user sidebar without Locations; fixed in 90f2ab5 and re-run green (49 passed). The fix touches only those two test files, so the suite was not re-run in full afterwards.
- Browser suite (`companion -m browser`, chromium symlink dir in the scratchpad): 567 passed. No Locations-specific browser tests exist (the plan lists none).
- As `nobody` (the five brief files, the suite guards, `test_console_locations.py`, `test_location_picker.py`): 464 passed, 4 skipped (the Chromium 1243/1248 launch skips of the sandbox).
- `ruff check .`, `mypy` (26 files), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` (814 functions): clean.

## Behaviour proven by the tests

- Page: an admin sees every row with Owner (email or "Platform"), Used-by counts, Edit and Delete; a user sees only their own rows, no Owner column, and neither ownerless rows, other users' rows nor their email appear in the bytes; both empty states; Europe/Paris selected by default; every form has the CSRF field; stored names are escaped; a user's page has no administration sub-nav.
- Create: owned row for a user, ownerless for an admin, coordinates rounded to 4 decimals, negative zero stored as 0.0, control characters stripped, `location.add` audit with numeric target id and the actor; the 11th location is refused with "Location limit reached" and one denied audit row; another user is unaffected.
- Validation (18 cases on add and edit): empty, control-only or over-long name; NaN, inf, text, empty, exponent, out-of-range latitude and longitude; unknown, path-shaped and empty time zone each give the UI-SPEC field error at 400 and write nothing (no audit row); typed values are kept.
- Edit and delete: own rows; delete of a location used by a frame refused ("This location is used by a frame.", denied audit, row and assignment kept); admin acts on any row including ownerless ones; an edit keeps the owner.
- Cross-owner: for edit and delete, a foreign id, an ownerless id, unknown, zero, over-long, non-digit and negative ids all return status and body identical to the unknown-path 404 (also for an invalid submission), with locations, audit_log and devices unchanged. GET on the action paths is the unknown-path 404 too.
- Rate limit: the 21st mutation by one user is refused with "Too many changes" (add, edit and delete alike), another user and admins are unaffected.
- Gates: missing CSRF is 403 with no state or audit change; anonymous is redirected.
- Picker: a user's select lists only their own locations with the current one selected plus "Manage locations"; no location gives the note and "Add a location"; an admin lists all (ownerless too) and sees nothing while none exists; the select belongs to the settings form; French.
- Assignment: own location assigned and cleared through the Display save; a save without the field or with an unchanged value changes nothing and writes no audit; the audit row is `location.update`, target type device, detail the location id, and `device_config` is otherwise identical; foreign, ownerless, unknown, non-numeric, negative and exponent-shaped values are refused with the save-failed flash, nothing changed, a denied audit row each; a user posting to another user's frame gets the unknown-path 404; the unprefixed live-frame form is 404 for a user; an admin may assign any location; the field is ignored on the Device scope.
- Reassignment: after an admin reassigns a frame its location is cleared, the new owner's picker shows only their own locations, and the previous owner's location id is refused for the new owner.

## Deviations from Plan

1. **[Rule 3 - Blocking] `companion/app.py` touched (one line).** `config_page.handle_post(form, ctx, errors)` receives neither the principal nor the handler, which the plan assumed; the audit actor and the acting user id need the handler. `_handle_settings_post` now passes `handler=self` (`git diff` of `app.py` is that single line). `handle_post` takes an optional `handler=None` and skips the location step without it, so direct callers are unchanged. The plan's "`git diff companion/app.py` is empty" criterion therefore does not hold.
2. **Picker is its own block next to the Quiet hours card, not inside it.** The time zone field lives in the Quiet hours card (`companion/settings/quiet_hours.py`, not a file of this plan). The picker is appended after that card in the same dirty-tracked form; it uses the existing `theme-status`, `text-heading`, `text-link` classes and `data-dirty-section`.
3. **[Rule 2] Foreign current location handled.** An admin may assign a location the user does not own; without care the user's next Display save would have cleared it (the select would not contain it). It stays selected under "Assigned by an administrator" (not in the plan's copy list).
4. **[Rule 3] Existing tests described the pre-Locations state** and were updated: `test_route_table` (signed-in and non-admin route sets, a sample per templated route), `test_console_shell` (nav order now Fleet, Users, Locations, Audit log, Releases), `test_user_nav` (user sidebar gains Locations; "no Locations route" cases drop the real routes first; admin group gains Locations), `test_account_page` and `test_sign_in_surfaces` (user shell links), `test_i18n` allowlist (French "Actions", "Latitude", "Longitude", "Latitude, longitude" equal the English).
5. **Baselines regenerated.** `render_baseline.json`: 44 pages gain the Locations sidebar link or section chip, four new unauthenticated entries (`GET /locations`, `POST /locations/add`, `/locations/1/edit`, `/locations/1/delete`); `update_page_one_type_golden.json`: 12 pages gain the Locations chip. Both checked by script (old versus new): every difference is exactly the inserted Locations link or chip, nothing else. `companion_render_snapshot.py` gained the four paths.
6. **User page does not use `_console_page`.** That helper always adds the administration section sub-nav, whose links are 404 for a user, so a user's page is assembled with `layout.page_shell` (like the Account page); admins use `_console_page`.
7. **Coordinates shown with 4 decimals**, the stored precision (UI-SPEC says 5).
8. **Task 1 and the fix:** the first full-suite run happened after both tasks; the four sidebar-link failures it found belong to Task 1's nav change and have their own commit.

## Notes for the owner and plan 14

- The mutation throttle is in memory and per process (a companion restart forgets it), like the pairing throttle. A refused-while-locked attempt writes no audit row by design.
- Quota (10 per user) and the throttle numbers are in `console_locations.py` (`USER_LOCATION_LIMIT`, `MUTATION_LIMIT`, `MUTATION_LOCKOUT_S`).
- Phase 52 code does not read the `locations` table (only `server/fleet_db.py` and `server/fleet_migrate.py` do); nothing shared was changed apart from the optional `handler` argument above.
- Hand-off for Phase 53: stored coordinates are rounded to 4 decimals (about 11 m) on store; outbound sharing rules and any coarser rounding for third parties belong to that phase. France-only bounds are not enforced.
- The time zone select offers every IANA zone with a region (`Etc/` and `posix/` excluded) plus Europe/Paris; validation accepts any zone `ZoneInfo` can load.
- Tests use obviously generic fake places only.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (T-55-13-01 to -07 covered by `test_console_locations.py` and `test_location_picker.py`).

## Self-Check: PASSED

Files present: companion/pages/locations_page.py, companion/console_locations.py, companion/i18n_fr/admin_locations.py, companion/test_console_locations.py, companion/test_location_picker.py. Commits 256bf57, 90f2ab5 and fb1cc35 exist.
