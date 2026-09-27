---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 16
subsystem: ui
tags: [companion, structure-guard, requirements-traceability, health-page, refactor]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: "Plans 40-01..40-15's route table, static allowlist, page/context split, named templates, app.py decomposition, CFG-34/CFG-39/CFG-52 work and the stable i18n IDs migration — this closing plan re-measures all of it against the live tree rather than trusting any plan's own self-report"
provides:
  - "companion/health_sections.py: the registry, resolution-statistics and check-in-regularity markup builders extracted out of companion/pages/health_page.py, the last production file over the structural guard's line ceiling"
  - "companion/test_structure_guards.py with no pending allowlist: PENDING_OVERSIZED_FILES and PENDING_LONG_FUNCTIONS both deleted, only the tracked style.css exception remains"
  - "REQUIREMENTS.md recording CFG-34, CFG-39 and CFG-52's Phase 40 outcomes clause by clause (all three now ticked) and CMP-01..09's traceability rows naming their satisfying plans"
affects: [companion-health-page, companion-structure-guard, requirements-traceability]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A markup-heavy sub-feature shared by exactly one page module still lives at companion/ level (never companion/pages/), matching companion/battery_chart.py and companion/health_signals.py's own precedent, since a page module may not import another page module"
    - "A frozen-clock test harness that patches a module's own datetime name must follow that name to wherever the function using it actually lives, not the page module that merely re-exports it"

key-files:
  created:
    - companion/health_sections.py
  modified:
    - companion/pages/health_page.py
    - companion/test_structure_guards.py
    - test-support/companion_render_snapshot.py
    - stub-server/test_poll_cycle.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Moved resolution_stats(), the registry table/cards/filter-bar builders, the stats table/cards builders, the check-in-regularity grid builders and _unavailable_block()/_resolution_rate_tile_html() (needed to break a circular re-export) into companion/health_sections.py, shrinking health_page.py from 1787 to 1111 lines — comfortably under the 1500-line ceiling, so no TRACKED_FILE_EXCEPTIONS entry was needed for it"
  - "health_page.py re-exports every moved name its own render() and remaining tile builders still call as bare names, or that a test reads as health_page.X — discovered iteratively by running the full suite rather than by static grep alone, since one test file accesses _FILTER_INPUT_ID through a variable, not a literal attribute"
  - "_DB_UNAVAILABLE and battery_chart._full_local_timestamp_text are read directly by health_sections.py from their own owning modules (health_signals, battery_chart), never re-exported through health_page.py, keeping the new module's only inbound dependency direction health_page.py -> health_sections.py"

requirements-completed: [CMP-01, CMP-02, CMP-03, CMP-04, CMP-05, CMP-06, CMP-07, CMP-08, CMP-09, CFG-34, CFG-39, CFG-52]

# Metrics
duration: ~40min
completed: 2026-09-27
---

# Phase 40 Plan 16: Close Phase 40 — empty the structural guard, full-suite gate, honest requirement outcomes Summary

**Extracted health_page.py's registry/stats/check-in-regularity markup into a new companion/health_sections.py (1787 -> 1111 lines), emptied the structural guard's pending allowlists, fixed one unrelated pre-existing full-suite failure, and ticked CFG-34/CFG-39/CMP-01..09 in REQUIREMENTS.md with the tests and plan IDs that prove each clause.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-09-27
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `companion_structure.oversized_files(limit=1500)` now reports only the tracked `companion/static/style.css` exception; `companion_structure.long_functions(limit=80)` reports none. `companion/pages/health_page.py`, the phase's own last named offender (1787 lines, tracked in `PENDING_OVERSIZED_FILES` since 40-06), is now 1111 lines.
- New `companion/health_sections.py` (767 lines) holds the registry ("Airlines we could not name"), the resolution-statistics breakdown ("How well we name flights") and the check-in-regularity grid — a pure, behaviour-preserving extraction, proven by `companion/test_render_baseline.py`'s two tests passing byte-for-byte against the regenerated-in-40-10 baseline once `test-support/companion_render_snapshot.py`'s clock-freezing patch target followed `resolution_stats()` to its new module.
- `companion/test_structure_guards.py`'s `PENDING_OVERSIZED_FILES` and `PENDING_LONG_FUNCTIONS` allowlists, and every reference to them, are deleted; `grep -c "PENDING_" companion/test_structure_guards.py` is 0.
- Fixed one unrelated, pre-existing failure the full-suite gate surfaced: `stub-server/test_poll_cycle.py`'s hostile-quiet-hours-config integration step still asserted the pre-D-4 fail-open value (`sleep_s == 300`), stale since Phase 39's `39-06` shipped the fallback-to-default-window behaviour; the assertion now computes its expectation from `device_policy.seconds_until_quiet_hours_end()` against the same default window, so it holds regardless of when the test runs.
- `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` exits 0: 3211 passed, 0 failed, 7 skipped (all pre-existing root-euid permission-bit skips), 94.86% coverage (>= 93% floor), no browser test skipped. `scripts/check_comment_history.py check` and `ruff check .` both exit 0.
- `.planning/REQUIREMENTS.md`: CFG-34 and CFG-39 each gained a dated Phase 40 paragraph naming every clause, whether it now holds, and the test(s) proving it, and are now ticked (`[x]`); CFG-52 already carried its own Phase 40 paragraph from `40-07` and was verified, not re-written. CMP-01..09's traceability rows now name the specific plan(s) satisfying each, replacing a bare "Phase 40 | Complete".

## Task Commits

Each task was committed atomically:

1. **Task 1: Final structural guard and full-suite gate** - `a4a2f79` (feat)
2. **Task 2: Record requirement outcomes clause by clause** - `51d0319` (docs)

**Plan metadata:** committed together with this SUMMARY (see the closing `docs` commit).

## Files Created/Modified

- `companion/health_sections.py` - New module: `resolution_stats()`, the registry table/cards/filter-bar builders, the stats table/cards builders, the check-in-regularity grid builders, `_unavailable_block()` and `_resolution_rate_tile_html()`
- `companion/pages/health_page.py` - Narrowed to 1111 lines; imports and re-exports every moved name `render()` and the remaining tile builders still call as bare names
- `companion/test_structure_guards.py` - `PENDING_OVERSIZED_FILES`/`PENDING_LONG_FUNCTIONS` and their use deleted; both structural tests now compare only against `TRACKED_FILE_EXCEPTIONS`
- `test-support/companion_render_snapshot.py` - `frozen_clock()`'s `datetime` patch target moved from `health_page` to `health_sections`, following `resolution_stats()`
- `stub-server/test_poll_cycle.py` - Step 22's hostile-quiet-hours-config assertion now computes its expected `sleep_s` from the D-4 default-window fallback instead of asserting the stale pre-D-4 fail-open value
- `.planning/REQUIREMENTS.md` - CFG-34/CFG-39 ticked with dated Phase 40 paragraphs; CMP-01..09 traceability rows name their satisfying plans

## Decisions Made

- Kept `_unavailable_block()`/`HEALTH_UNAVAILABLE_TEXT`/`_resolution_rate_tile_html()`/`_TILE_DETAIL_CLASS` moving into `health_sections.py` alongside the three named groups (registry/stats/check-in), rather than leaving them in `health_page.py`: `_check_in_regularity_section_html()` and `_resolution_rate_tile_html()` both call `_unavailable_block()`, and moving only the three named groups while leaving that one shared helper behind would have required `health_sections.py` to import `health_page.py` back — circular, since `health_page.py` imports `health_sections.py` at load time. Moving the shared helper too (and re-exporting it back into `health_page.py` for its other six call sites) keeps the dependency one-directional, exactly mirroring how `health_signals.py` already owns `_DB_UNAVAILABLE` despite `health_page.py` using it far more.
- `_DB_UNAVAILABLE` and `battery_chart._full_local_timestamp_text` are read directly from their owning modules inside `health_sections.py` (not re-exported through `health_page.py`), so `health_sections.py`'s only dependency on another companion module already in `health_page.py`'s own import list stays a direct one, never a reach-through.
- Fixed `stub-server/test_poll_cycle.py`'s stale assertion in place rather than reverting Phase 39's D-4 behaviour or skipping the test: D-4 was a developer-approved, already-shipped decision; the test's own expectation had simply not been updated when that decision landed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale test assertion predating Phase 39's D-4 quiet-hours fallback change**
- **Found during:** Task 1's full-suite verification run (`SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`)
- **Issue:** `stub-server/test_poll_cycle.py::test_device_protocol_end_to_end_over_real_http`'s step 22 asserted `sleep_s == 300` (fail-open to disabled) for a corrupted `quiet_hours_start` value. Phase 39's `39-06` shipped D-4 (developer-approved): an invalid stored quiet-hours time now falls back to the default 23:00-07:00 window instead of disabling quiet hours. This integration test's step 22 was never updated to match, so it failed whenever "now" happened to fall inside that default window (as it did on this run: got `sleep_s == 24252`).
- **Fix:** Replaced the fixed `== 300` assertion with a computed expectation, using `device_policy.seconds_until_quiet_hours_end()` against the same default window the production code falls back to, so the test holds correctly regardless of when it runs.
- **Files modified:** `stub-server/test_poll_cycle.py`
- **Verification:** `pytest stub-server/test_poll_cycle.py::test_device_protocol_end_to_end_over_real_http` passes; full suite re-run green afterward.
- **Committed in:** `a4a2f79` (Task 1 commit)

**2. [Rule 3 - Blocking] Frozen-clock harness patched the wrong module after the extraction**
- **Found during:** Task 1's full-suite verification run, immediately after the `health_sections.py` extraction
- **Issue:** `test-support/companion_render_snapshot.py`'s `frozen_clock()` patched `health_page.datetime` to freeze `resolution_stats()`'s clock fallback — `resolution_stats()` had just moved to `companion/health_sections.py`, so `health_page` no longer imports `datetime` at all, and both render-baseline tests failed with `AttributeError`.
- **Fix:** Retargeted the patch (and its docstring) to `health_sections.datetime`, and dropped the now-unused `health_page` import from that harness module.
- **Files modified:** `test-support/companion_render_snapshot.py`
- **Verification:** `companion/test_render_baseline.py`'s two tests pass byte-for-byte against the existing baseline.
- **Committed in:** `a4a2f79` (Task 1 commit)

**3. [Rule 3 - Blocking] Several moved constants/functions needed re-export back into health_page.py**
- **Found during:** Task 1, iteratively via full-suite test runs after the initial extraction
- **Issue:** A handful of constants and functions moved to `health_sections.py` were still needed in `health_page.py` — either called as a bare name inside `render()`/`_corroboration_details_html()`/`_tile_body()` (which resolve bare names against `health_page.py`'s own module globals, not the defining module's), or read directly by a test as `health_page.X` (including one test that resolves the attribute through a loop variable, invisible to a static grep for the literal `health_page.` prefix).
- **Fix:** Added re-export bindings (`NAME = health_sections_module.NAME`) in `health_page.py` for every name found missing, confirmed by running the full suite to convergence rather than trusting a single static scan.
- **Files modified:** `companion/pages/health_page.py`
- **Verification:** Full suite green (3211 passed, 0 failed) with no `AttributeError`.
- **Committed in:** `a4a2f79` (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 Rule 1, 2 Rule 3)
**Impact on plan:** All three were necessary to make the plan's own full-suite gate pass without weakening any contract or changing rendered output. No scope creep — the stub-server fix is a one-assertion test correction, not a behaviour or production-code change.

## Issues Encountered

None beyond the three auto-fixed deviations above.

## Known Stubs

None.

## Threat Flags

None — this plan is verification and documentation only, per its own threat model (T-40-30, discharged: every CFG-34/CFG-39 tick above cites the test(s) that prove each clause).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 40 is closed: all four ROADMAP success criteria hold and are machine-enforced (route table coverage, no oversized file/function outside the one tracked exception, no duplicated CSS selector, stable i18n IDs with completeness tests).
- CMP-01..09, CFG-34, CFG-39 and CFG-52 are all ticked in `REQUIREMENTS.md`, each with the plan IDs or clause-by-clause test evidence that earned the tick.
- No blockers for the next phase.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 7 key files confirmed present on disk; all 3 commit hashes
(`a4a2f79`, `51d0319`, `d8d8cb4`) confirmed in `git log`.
