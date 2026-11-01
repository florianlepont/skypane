---
phase: 60-device-co-management
plan: 05
subsystem: companion-routes
tags: [co-management, csrf, audit, flash, i18n]
requires: [60-01, 60-02, 60-03]
provides:
  - POST /co-managers/add, /co-managers/remove, /co-managers/leave (device-scoped, CSRF)
  - one generic add refusal, audit rows for every add and removal path
  - co-management flash keys (EN/FR) and audit page labels
affects: [60-06, 60-07]
key-files:
  created:
    - companion/co_managers.py
    - companion/pages/co_managers_card.py
    - companion/i18n_fr/co_managers.py
    - companion/test_co_managers.py
  modified:
    - companion/routes.py
    - companion/flash.py
    - companion/pages/audit_page.py
    - companion/i18n_fr/admin_lifecycle.py
requirements-completed: [AUTH-08]
completed: 2026-11-01
---

# Phase 60 Plan 05: Co-manager management routes Summary

Add, remove and leave handlers behind CSRF and the owner-only gate, with one uniform add refusal, an audit row in the same transaction as every change, and the flash and audit-label strings in English and French.

## Tasks

| Task | Commit | Files |
|------|--------|-------|
| 1 Contracts module, flash registry, audit labels, French | 0028760 | companion/pages/co_managers_card.py, companion/flash.py, companion/pages/audit_page.py, companion/i18n_fr/co_managers.py, companion/i18n_fr/admin_lifecycle.py, companion/test_co_managers.py |
| 2 Add, remove, leave handlers and routes | 08aac42 | companion/co_managers.py, companion/routes.py, companion/test_co_managers.py |
| 2b Route inventory tests and baseline | d3b5e76 | companion/test_csrf.py, companion/test_device_routes.py, companion/test_route_table.py, companion/testdata/render_baseline.json |

## Touches Phase 55 code

Yes, minimally:

- `companion/pages/audit_page.py::ACTION_LABELS`: two new labels (co-manager added and removed).
- `companion/i18n_fr/admin_lifecycle.py`: two new French strings.
- `companion/routes.py`: three Route entries, three `_ACTION_KEYS` entries, the `OWNER_ONLY_DEVICE` export and the device-scoped route count comment.

`companion/flash.py` (registry entries and one extra glyph mapping) is also edited.

## Behaviour

- Add reads one `email` field (typed for an owner, a select value for an admin). Every failure (unknown, disabled, the owner, already a co-manager, malformed, empty, over 254 characters, control character, stale candidate) gives the same 303 to the frame Home with `co_manager_add_refused`, and writes a `denied` audit row whose detail is a reason code (malformed, unknown, ineligible, duplicate) and never the address.
- Remove reads `user_id` (digits only, at most 9 characters) and deletes only a co-manager row, so the owner cannot be removed; a miss flashes `co_manager_failed`.
- Leave ignores the form, acts on the caller's own row, audits via "self", redirects to `/account?flash=co_manager_left`; without a row it changes nothing, writes no audit row and flashes `co_manager_leave_noop`.
- A store error rolls the change and its audit row back, writes a best-effort standalone `failed` row and flashes `co_manager_failed`.
- French uses "cadre" and "propriétaire" as the existing catalogue does; "co-gestionnaire" for co-manager.

## Verification

- `pytest companion/test_co_managers.py companion/test_suite_guards.py companion/test_i18n.py`: 257 passed.
- `pytest companion/test_co_managers.py companion/test_i18n.py companion/test_console_lifecycle.py` after Task 1: 91 passed.
- ruff (repo), mypy (28 source files), `check_function_size.py check --max 80 server stub-server` (921 functions, none over 80), `check_comment_history.py check`: clean.
- `grep` for routes/app imports in `companion/co_managers.py`: empty.
- Wider run (`companion` without browser tests, `server/test_fleet_schema4.py`, `stub-server/test_phase47_freeze.py`, access matrix deselected): 3428 passed; the only failures were the seven route-inventory cases fixed in the next section; the Phase 47 freeze test passed, unedited.
- After the fix: `test_csrf.py`, `test_device_routes.py`, `test_route_table.py`, `test_suite_guards.py`: 387 passed.

## Expected failure: access matrix completeness

`companion/test_access_matrix.py` fails by design until plan 07 adds the matrix rows: `test_every_route_has_a_policy_row_and_every_row_has_a_route`, `test_the_device_scoped_set_is_exactly_the_hand_written_one`, and the parametrized cases for the three new routes (29 failures in total, all naming `co-managers` or those two completeness tests). The matrix was not edited here.

## Deviations from Plan

- **[Rule 3 - Blocking] Route inventory tests.** Adding routes broke tests that list every route by hand (`test_csrf`, `test_device_routes`, `test_route_table`) and the committed unauthenticated baseline, none of which a later plan covers. The expected sets and counts gain the three new routes (device-scoped 28 to 31, owner-device 26 to 27, plus an explicit owner-only set of add and remove), and `companion/testdata/render_baseline.json` gains three `POST /co-managers/*` entries (303 to `/login`, the same as every other gated POST). No assertion was loosened.
- A typed address with a control character is refused as malformed instead of having the characters stripped, so the input is never silently altered into a different valid address.
- The refusal test uses a genuinely unknown address in place of "not invited": the matching rule for "invited" is a user row, and the session helper creates one for every signed-in user.
- The `/account?flash=co_manager_left` toast is not rendered by this plan; the Account flash wiring belongs to plan 06 (listed in its files).
- The stale "14 GET and 15 POST" comment now reads "14 GET and 17 POST" (14 existing action keys plus three).

## Known Stubs

None. The card markup is intentionally absent from `co_managers_card.py` (plan 06).

## Self-Check: PASSED (files and commits 0028760, 08aac42, d3b5e76 exist)
