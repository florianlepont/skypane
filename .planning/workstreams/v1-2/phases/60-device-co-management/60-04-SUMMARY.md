---
phase: 60-device-co-management
plan: 04
subsystem: companion-scope
tags: [co-management, device-list, detection, locations]
requires: [60-01, 60-02, 60-03]
provides:
  - co-managed frames in a user's device list, selector and redirect target
  - Detection page scoped to the owner's locations for a co-manager, with no location writes
  - HTTP proof of co-manager reach and exclusion
affects: [60-05]
key-files:
  created: [companion/test_co_manager_access.py]
  modified:
    - companion/device_scope.py
    - companion/detection_actions.py
    - companion/pages/detection_page.py
    - companion/i18n_fr/detection.py
    - companion/test_device_scope_owner.py
    - companion/test_detection_page.py
    - companion/test_console_locations.py
requirements-completed: [AUTH-08]
completed: 2026-11-01
---

# Phase 60 Plan 04: Co-manager device list, location scope and HTTP proof Summary

A user's device list now includes frames they co-manage through a separate guarded lookup, the Detection page gives a co-manager the owner's locations with every location write refused, and a new HTTP module proves a co-manager acts like the owner on `OWNER_DEVICE` routes and gets the uniform 404 everywhere else.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Device list includes co-managed frames, failing closed | ef35fe5 | companion/device_scope.py, companion/test_device_scope_owner.py |
| 2 Detection scoped to the owner's locations, no location writes | e7c0619 | companion/detection_actions.py, companion/pages/detection_page.py, companion/i18n_fr/detection.py, companion/test_detection_page.py, companion/test_console_locations.py |
| 3 HTTP proof | ad25fe8 | companion/test_co_manager_access.py |

## Touches Phase 55 code

Yes. `companion/device_scope.py` (Phase 51/53 code that Phase 55 commits #256/#259 also changed): the only change is a new private `_co_managed_ids(root, user_id)` helper (read-only connection, returns an empty set on `FleetDbError`, `sqlite3.Error` or `OSError`) and the user branch of `load_devices_for` keeping rows the user owns or whose id is in that set. `_fleet_rows`, `find_device`, the `Device` shape and the admin and no-principal branches are unchanged. `companion/console_locations.py` is untouched (read only); its co-manager behaviour is proven only by tests added to `companion/test_console_locations.py`. `companion/detection_actions.py` (Phase 53) is edited in a bounded way (`Subject`, `subject_for`, `scope_for`, `_save_location`).

## Decisions

- `Subject` gains a defaulted `may_write` field. A co-manager (non-admin, actor differs from owner, membership row present) gets `subject_id = owner_id` and `may_write = False`; `_save_location` refuses before any write via the existing `location_form` error path. The membership query is skipped for owners and admins, so a schema-3 database cannot affect them.
- `LocationScope` gains a defaulted `may_edit`. For a co-manager the page shows the owner's locations list with the owner title, no edit links, no create/edit form and no add link, plus the line "Locations are managed by the frame owner." (French: "Les lieux sont gérés par le propriétaire du cadre."). No CSS added.
- Position-mode selection is validated against the owner's list, so a co-manager's own or a third party's location is refused as unavailable. The location rule itself stays in `fleet_db` from plan 02 (`git diff -- server/fleet_db.py` is empty for this plan).

## Verification

- `pytest companion/test_device_scope_owner.py companion/test_device_scope.py`: 58 passed.
- `pytest companion/test_detection_page.py companion/test_console_locations.py companion/test_i18n.py`: 157 passed (before the final test edits; detection page alone 72 passed after).
- `pytest companion/test_co_manager_access.py companion/test_suite_guards.py`: 221 passed.
- ruff (whole repo), mypy (28 source files), `check_function_size.py check --max 80 server stub-server` (921 functions, none over 80), `check_comment_history.py check`: clean.
- Wider run (`companion` non-browser, `server/test_fleet_schema4.py`, `stub-server/test_phase47_freeze.py`): 4367 passed, 3 skipped (root-permission skips), including the Phase 47 freeze test unedited and green.

## Deviations from Plan

**1. Crafted location POST shows the generic failure toast, not the location error text.** The `location_form` error has no place to render because a co-manager's page has no location form, so the re-render (HTTP 200, nothing written) shows the page's generic "Couldn't change that" message. The refusal still goes through the existing location-form error path, as the plan asks; the test asserts status 200, that toast and that no location row changed.

**2. Selector test uses a second frame.** The device selector is only rendered with two or more frames, so that test gives the co-manager a second frame of their own.

No other deviations; no Rule 1-3 fixes were needed.

## Known Stubs

None.

## Self-Check: PASSED
