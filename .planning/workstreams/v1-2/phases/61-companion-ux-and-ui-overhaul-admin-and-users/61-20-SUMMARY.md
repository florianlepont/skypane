---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 20
subsystem: companion
tags: [save-place, detection, frame-position, live-frame-safety]
requires: [61-18, 61-19]
provides: [POST /detection action save_place, place-saved flash, ledger R2-19]
key-files:
  created:
    - companion/test_place_save.py
    - test-support/matrix_rows_place.py
  modified:
    - companion/detection_actions.py
    - companion/pages/detection_page.py
    - companion/flash.py
    - companion/page_context.py
    - companion/i18n_fr/detection.py
    - companion/test_access_matrix.py
    - companion/test_companion_app_02.py
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 20: save_place Summary

`POST /detection` with `action=save_place` is now the single validated write path for a frame's own place: it stores the position row (through `fleet_db.save_frame_position`), the detection setting and, only when it changed, the time zone, for runway and position mode, with or without scripts.

## Commits

- fb0baaf: handler, flash, page error list, tests, matrix module, ledger row (one green commit). Summary in its own docs commit.

## What changed

- **Handler** (`detection_actions.py`): `parse_place` (split into small functions) validates mode, airport and runway (existing messages), the pin (position mode: parsed, France box; runway mode: optional moved pin, range check only, airport coordinates otherwise; a catalogue airport is accepted anywhere), the radius, the label (trimmed, at most 60 characters, blank falls back to the airport name or "Frame position") and the time zone through `form_post.resolve_timezone`. `_store_place` writes position row, then detection, then a forwarded zone; if a later write fails the previous `location_id` is restored and the save-failed flash is used. A refusal re-renders the page at 400 with nothing written; the older actions still answer 200 and are untouched.
- **Toast**: new flash key `place_saved` ("Location saved — Detection now follows {place}." / FR). `resolve_flash_text` takes `place_name`; `page_context` reads the stored position label from fleet.db on the render (the query string is never echoed; output is escaped).
- **Page**: `place_errors_html` shows the messages of a refused place save for fields the page has no control for yet (label, latitude, longitude, time zone, and radius when no radius field renders), so a refusal is never silent. Plans 61-25/26 move these beside real fields.
- **Matrix**: `test-support/matrix_rows_place.py` (empty `ROWS`, `EXPECTED_STATUS` per caller) registered in `test_access_matrix.py`; POST /detection was already an owner-device route, so no route row is added.
- **Ledger**: R2-19 appended (a co-manager may save the frame's place; supersedes the earlier saved-location rule).

## Tests (companion/test_place_save.py, 38 tests, over real HTTP)

Both modes, 16 refusal cases (nothing written, 400, message shown, entered values escaped), toast in EN and FR and not injectable, empty label fallbacks, zone stored / absent left alone, legacy Orly runway save leaves `device_config.json` bytes identical, a place save changes only `detection` and `timezone` (look, interval, quiet-hours keys untouched), poll read (`device_coordinates` + `spec_for`) unchanged by a sibling's save, first save creates a private row / second updates in place / repeat writes nothing, a shared row is copied and the sibling keeps its coordinates, failed config write restores the link, old actions still work, missing csrf 403, owner / co-manager / admin 303, stranger 404, anonymous to /login.

## Deviations from Plan

1. **[Rule 1] Control characters in the label are stripped (by `clean_form`), not refused**, as the threat model T-61-20-01 says; the plan's behaviour line said "refused". A label over 60 characters is refused.
2. **[Rule 2] Page error list** (above) added so refusals of fields with no control yet are visible (plan only said the page re-renders with errors).
3. **Flash placeholder is `{place}`** (like the calendar keys), and `test_companion_app_02.py::test_flash_manual_keys_complete_and_byte_identical` now lists `place_saved` among the deliberately interpolated keys (updated in place, not weakened). `test_toasts` needed no edit.
4. A time zone other than the curated list is refused with the existing "Pick a time zone from the list." message (`resolve_timezone` behaviour, not the page's `ERROR_TIMEZONE`).
5. A failed config write after an in-place row update restores only `location_id`; the row's own values are not rolled back (the copy-on-write and first-save paths leave only an unlinked row).

## Gates

- ruff, mypy (28 modules), `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server`: clean. `stub-server/test_phase47_freeze.py`: 21 passed, unchanged.
- Full `companion test-support stub-server -n auto --no-cov` (before the two fixes in deviation 3): 6759 passed, 4 skipped (root permission-bit, pre-existing), 3 failed (`test_flash_manual_keys_complete_and_byte_identical`, `test_toasts::test_every_flash_key_splits_into_title_and_detail_in_both_languages[en|fr]`), all caused by the new interpolated key; fixed, then `test_companion_app_02`, `test_toasts`, `test_place_save`, i18n, access matrix, detection page and position files re-run green (1659 + 128 passed). No full re-run after that fix.
- Render baseline, sign-in digests and goldens did not move.
- No edit to stub-server/, hardware/, server/detection.py, server/fleet_cycle.py.

## Known Stubs

None.

## Threat Flags

None. T-61-20-01..05 are covered by the tests above.

## Self-Check: PASSED
