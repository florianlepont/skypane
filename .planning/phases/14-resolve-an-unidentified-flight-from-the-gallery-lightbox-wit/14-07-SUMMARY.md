---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
plan: 07
subsystem: ui
tags: [flask-free-http, flash-messages, validation, python]

requires:
  - phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
    provides: "plan 14-02 declared FLASH_MANUAL_NAME_UNUSABLE in airlines_page.py and deferred wiring it to this plan"
provides:
  - "companion/app.py FLASH_KEY_MANUAL_NAME_UNUSABLE rebinding, FLASH_MESSAGES/FLASH_ROLES entries"
  - "a narrowed branch in _handle_manual_resolve_post() distinguishing a genuinely typed but unusable name from an empty field"
affects: []

tech-stack:
  added: []
  patterns:
    - "presentation-layer distinction of a single validation-ladder result code, made by re-reading the same raw form value already passed downstream — never a second read_form() call, never a duplicate of the validated module's own regex logic"

key-files:
  created: []
  modified:
    - companion/app.py
    - companion/test_companion_app.py

key-decisions:
  - "The distinguishing check is `form.get(\"airline_name\")` truthy after .strip(), matching add_entry()'s own docstring's step-2/step-3 split, without importing manual_resolutions.py's regex/validation logic"
  - "ADD_REJECTED_PREFIX stays mapped to FLASH_KEY_MANUAL_NAME_EMPTY unchanged — that branch is already defensive/unreachable since unresolved_row_for_prefix() validates the prefix moments earlier"

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "A rejected name the operator genuinely typed (path-shaped, or a slug that collapses to nothing usable) now redirects with flash=manual_name_unusable, distinct from a genuinely empty field's flash=manual_name_empty"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_manual_resolve_post_rejection_mapping_and_d03_branch"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#_flash_manual_keys_complete_and_byte_identical"
        status: pass
    human_judgment: false
  - id: D2
    description: "Neither rejected name is ever persisted to the registry; add_entry()'s own validation ladder and server/plane/manual_resolutions.py are completely untouched"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_manual_resolve_post_rejection_mapping_and_d03_branch"
        status: pass
      - kind: other
        ref: "git diff --name-only server/ (empty)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 07: Distinct flash key for a supplied-but-unusable manual airline name Summary

**A path-shaped or slug-collapsing airline name posted to `POST /airlines/resolve` now redirects with `flash=manual_name_unusable` instead of the misleading `flash=manual_name_empty`, closing Phase 13's UAT gap G-01.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-06T14:58:33Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- `FLASH_KEY_MANUAL_NAME_UNUSABLE` rebound from `airlines_page.FLASH_MANUAL_NAME_UNUSABLE` (declared by plan 14-02), with its own `FLASH_MESSAGES`/`FLASH_ROLES` entries matching the file's established voice and role conventions
- `_handle_manual_resolve_post()`'s `ADD_REJECTED_NAME_EMPTY` branch split: a raw posted `airline_name` that is non-empty after `.strip()` now maps to `manual_name_unusable`; a genuinely empty/whitespace-only field still maps to `manual_name_empty`, byte-identical to before
- `ADD_REJECTED_PREFIX` left mapped to `FLASH_KEY_MANUAL_NAME_EMPTY` exactly as before (out of this task's scope — already defensive/unreachable)
- Two existing test checks extended in place (`_flash_manual_keys_complete_and_byte_identical`, `_manual_resolve_post_rejection_mapping_and_d03_branch`) to prove the new key exists and that a hostile path-shaped name (`../../etc/passwd`) now diverges from the empty-field case
- `companion/test_companion_app.py` reports 159/159 checks pass (no count change, as required — two checks extended, none added)

## Task Commits

TDD task, two commits (RED then GREEN):

1. **Task 1 RED: failing test for the distinct flash key** - `9e553fa` (test)
2. **Task 1 GREEN: implement the flash-key rebinding and branch narrowing** - `48748b2` (feat)

## Files Created/Modified
- `companion/app.py` - `FLASH_KEY_MANUAL_NAME_UNUSABLE` rebinding + `FLASH_MESSAGES`/`FLASH_ROLES` entries; `_handle_manual_resolve_post()`'s rejection-mapping branch narrowed to distinguish empty vs. unusable
- `companion/test_companion_app.py` - extended `_flash_manual_keys_complete_and_byte_identical()`'s `manual_keys` tuple and `_manual_resolve_post_rejection_mapping_and_d03_branch()`'s `rejection_cases` tuple

## Decisions Made
- The distinguishing check re-reads `form.get("airline_name")` — the exact same raw value already passed to `add_entry()` two lines above — rather than calling `read_form()` again or re-deriving `manual_resolutions.py`'s own regex/validation logic (mirrors, at the presentation layer only, the distinction `add_entry()`'s own docstring already draws between its step 2 and step 3)
- `ADD_REJECTED_PREFIX` was left bundled with `FLASH_KEY_MANUAL_NAME_EMPTY`, unchanged — the plan explicitly scoped narrowing that branch further as out of bounds, since `unresolved_row_for_prefix()` already validates the prefix moments earlier in the same handler

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

`scripts/run-all-tests.sh`'s first run reported a failure in `server/test_pipeline_e2e.py` (a file this plan never touches). Running that harness directly (`server/.venv/bin/python3 server/test_pipeline_e2e.py`) passed 6/6, and a full re-run of `scripts/run-all-tests.sh` immediately after also passed cleanly (`==> Result: PASS`) — confirming the first failure was a parallel-test-runner flake (likely port contention in the harness's own subprocess server), not caused by this plan's changes. Out of scope per the deviation rules' scope boundary (only `companion/app.py`/`companion/test_companion_app.py` were touched); not fixed, not re-investigated further.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 13's UAT gap G-01 is closed; `add_entry()`'s validation ladder, return-code contract, and `server/plane/manual_resolutions.py` remain completely untouched
- No blockers for the remaining phase-14 plans (14-06/14-08), which do not share files with this plan

---
*Phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: companion/app.py
- FOUND: companion/test_companion_app.py
- FOUND: .planning/phases/14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit/14-07-SUMMARY.md
- FOUND: 9e553fa (test commit)
- FOUND: 48748b2 (feat commit)
