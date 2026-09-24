---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 19
subsystem: testing
tags: [pytest, pytest-playwright, chromium, browser-tests, companion, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's guarded browser/new_context/page fixtures, the loopback-only route guard, and test-support/companion_app_server.py's LegacyHarness/TEST_PASSWORD — this plan's helper conversion and health-drawings rewrite build directly on them"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "companion/test_suite_guards.py's TST-10/12/13/14 guard (G9/G10 rules) and skypane_test_support.py's disk-derived legacy set, which this plan's helper conversion removes itself from (ALWAYS_EXEMPT, LEGACY_HELPER_MODULES)"
provides:
  - "companion/test_browser_ux_helpers.py: pytest-usable (__test__ = False), no dependency on companion.test_companion_app, and every context-opening helper (_no_js_page/_persist_without_js/_upload_without_js/_persist_once/_assert_js_gate/_display_page_height) takes a make_context factory argument instead of a raw browser object"
  - "companion/test_browser_ux_health_drawings.py: 11 legacy checks rewritten as 13 native pytest-playwright test node ids (parametrized over Home/Health for the two ring checks), 3 module-scoped read-only servers replacing 3 per-check isolated Harness() instances"
  - "test_browser_ux.py / test_browser_ux_quiet_wake.py repointed onto companion_app_server.LegacyHarness, with every shared-helper call site updated to pass browser.new_context instead of a bare browser object"
  - "LEGACY_HELPER_MODULES emptied and test_browser_ux_helpers.py removed from test_suite_guards.py's ALWAYS_EXEMPT — the guard now scans it"
affects: [33-20, 33-21, 33-22, 33-23, 33-24]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared browser-context-opening helpers take a make_context factory parameter (pytest-playwright's guarded new_context fixture, or a still-legacy harness's bound browser.new_context method) instead of a raw browser object, so one helper module serves both a fully-migrated pytest caller and a not-yet-migrated legacy script harness with the same call shape"
    - "A browser-test module with several read-only checks against DIFFERENT seeded datasets (ring/chart vs. one day's check-ins vs. three days with distinct verdicts) gets one module-scoped server fixture PER DATASET, not one shared fixture with the union of all seed data — keeps each fixture's seeding code exactly as specific as the checks that read it, and keeps a change to one dataset from silently perturbing an unrelated check's bucket counts"
    - "A legacy check's loop over independent, non-cross-comparing cases becomes @pytest.mark.parametrize; a loop whose final assertion compares values ACROSS iterations (theme-differs, width-parity between languages) stays a single test, because splitting it would need each parametrized invocation to reconstruct data another invocation depends on, which xdist's 'no test depends on another' rule forbids without extra plumbing"

key-files:
  created: []
  modified:
    - companion/test_browser_ux_helpers.py
    - companion/test_browser_ux_health_drawings.py
    - companion/test_browser_ux.py
    - companion/test_browser_ux_quiet_wake.py
    - test-support/skypane_test_support.py
    - companion/test_suite_guards.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux_health_drawings.md

key-decisions:
  - "Only the two RING_PAGES checks (ring paint, ring viewBox) were split via @pytest.mark.parametrize into per-page ([chromium-Home]/[chromium-Health]) node ids, because their per-page assertions (including the light-vs-dark comparison) are fully self-contained per page. The remaining 9 checks keep an internal Python loop over theme/language/width rather than being further parametrized, because each one's final assertion compares a value ACROSS loop iterations (both themes differ, both languages agree on width) — correctly splitting those would require re-deriving one iteration's data inside another parametrized test's own run, which is exactly the cross-test dependency 33-MIGRATION-RULES.md section 2 forbids under xdist. 13 node ids clears the plan's 'at least 11' acceptance bar without that risk."
  - "The day-band and hero checks (6, 7, 10, 11) share ONE module-scoped band_server fixture instead of two, since the hero checks used to call the legacy _band_harness() a second time purely to get the same one-day seeded dataset the day-band checks already had — deduplicating the seed function removes a second subprocess start with no behaviour change."
  - "Checks that originally opened `browser.new_context()` with no extra kwargs (checks 4, 6, 8) now use pytest-playwright's plain `page` fixture directly instead of calling the guarded `new_context` factory by hand — one less manual context/close pair per test, with identical behaviour."

requirements-completed: []

# Metrics
duration: 37min
completed: 2026-09-24
---

# Phase 33 Plan 19: Browser Helpers Conversion and Health-Drawings Migration Summary

**Converted the shared browser-test helper module to pytest (dropping its `companion.test_companion_app` dependency and its direct `browser.new_context()` calls), and rewrote all 11 health-drawings checks as 13 native pytest-playwright test node ids running under xdist in ~12.5s (down from 21.6s serial).**

## Performance

- **Duration:** ~37 min (commit-to-commit, previous plan's last commit to this plan's last commit)
- **Started:** 2026-09-24T11:43:05Z
- **Completed:** 2026-09-24T12:20:31Z
- **Tasks:** 3/3 completed
- **Files modified:** 7

## Accomplishments

- `companion/test_browser_ux_helpers.py` is now a pytest-usable module: `__test__ = False`, `TEST_PASSWORD` imported from `companion_app_server` instead of the still-legacy `companion.test_companion_app`, `test-support/` added to `sys.path` the same way `companion/conftest.py` does (so the two still-legacy script harnesses that import this module directly still find it), and every one of its six context-opening helpers (`_no_js_page`, `_persist_without_js`, `_upload_without_js`, `_persist_once`, `_assert_js_gate`, `_display_page_height`) takes a `make_context` factory parameter instead of a raw `browser` object — removing all three direct `browser.new_context()` calls the guard's G10 rule flagged (33-03's `ALWAYS_EXEMPT` entry for this file is gone).
- `companion/test_browser_ux.py` and `companion/test_browser_ux_quiet_wake.py` (the two still-legacy browser harnesses) import `Harness`/`TEST_PASSWORD` from `companion_app_server.LegacyHarness` instead of `companion.test_companion_app`, with every one of their ~27 call sites into the shared helpers updated to pass `browser.new_context` (a bound method, matching the new `make_context` shape) instead of the bare `browser` object — no check behaviour changed, verified by running both harnesses through the shim with `SKYPANE_REQUIRE_BROWSER=1` (0 skipped, same PASS counts as their 75/9 baselines).
- `companion/test_browser_ux_health_drawings.py` rewritten in place: `main()`/`check()`/`EXPECTED_CHECK_COUNT`/`sync_playwright()`/the two `SKIP` gates are gone. Three module-scoped read-only server fixtures (`server`, `band_server`, `grid_server`) replace the three per-check isolated `Harness()` instances the legacy file spun up; 11 checks become 13 pytest-playwright test node ids (the two ring checks parametrized over `RING_PAGES`, since each page's own theme comparison is fully independent). Every `return False, reason` became a raised `AssertionError`; every `browser.new_context(...)` / `_no_js_page(browser, ...)` call now goes through the guarded `new_context`/`page` fixtures. `SKYPANE_REQUIRE_BROWSER=1 pytest -n auto` reports 13/13 passed in 12.49s with 0 skipped.
- The migration ledger fragment's 11 rows all flipped to `ported`, pointing at real collected node ids (`33-ledger-check.py` confirms 11/11 mapped, 0 pending). `LEGACY_HELPER_MODULES` is now `()` and `test_browser_ux_helpers.py` is gone from `test_suite_guards.py`'s `ALWAYS_EXEMPT` — the guard scans it like any other companion module (40/40 guard tests pass).
- Full-suite sanity beyond this plan's own scoped verification: `pytest -n auto companion test-support server stub-server` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium) — 1048 passed, 1 failed, 5 skipped. The one failure is `test_status_pages`'s pre-existing `anomaly_active("/nonexistent/...")` root-sandbox artifact, already classified in `33-BASELINE/INDEX.md` and explicitly out of scope for this plan (33-25's job).

## Task Commits

1. **Task 1: Convert test_browser_ux_helpers.py and repoint the legacy importers** - `c9fad86` (test)
2. **Task 2: Rewrite test_browser_ux_health_drawings.py as pytest-playwright tests** - `3ec7393` (feat)
3. **Task 3: Ledger, guard, commit** - `ac3280e` (docs)

## Files Created/Modified

- `companion/test_browser_ux_helpers.py` - pytest-usable helper module, `make_context` factory parameter replacing raw `browser` in 6 functions
- `companion/test_browser_ux_health_drawings.py` - rewritten in place as 13 pytest-playwright test node ids
- `companion/test_browser_ux.py` / `companion/test_browser_ux_quiet_wake.py` - `Harness` import repointed to `companion_app_server.LegacyHarness`, call sites updated to pass `browser.new_context`
- `test-support/skypane_test_support.py` - `LEGACY_HELPER_MODULES` emptied
- `companion/test_suite_guards.py` - `test_browser_ux_helpers.py` removed from `ALWAYS_EXEMPT`
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux_health_drawings.md` - 11 rows flipped to `ported`, Part 01 note added

## Decisions Made

See `key-decisions` in the frontmatter: which loops got parametrized (only the two fully page-independent RING_PAGES checks) and why the rest did not (cross-iteration invariants that would need extra plumbing to split safely under xdist), the single shared `band_server` fixture for the day-band and hero check groups, and using the plain `page` fixture directly for the three checks that used to call `browser.new_context()` with no extra arguments.

## Deviations from Plan

### Auto-fixed Issues

None — no bugs or missing critical functionality were found.

### Noted, not fixed (out of this plan's scope)

**1. Task 1's own literal `<verify>` command's `-k` filter substring-matches `test_browser_ux_health_drawings` too**
- **Found during:** Task 1's own verification step, before Task 2 had converted `test_browser_ux_health_drawings.py`
- **Issue:** The plan's `<verify>` command `-k "test_browser_ux or quiet_wake"` also matches the shim's `test_browser_ux_health_drawings` parametrize id (it contains the substring `test_browser_ux`), which at that point in the plan was still the pre-Task-2 legacy file and failed with `TypeError("'Browser' object is not callable")` once the helpers' `_no_js_page` signature changed — an expected, anticipated intermediate state per the plan's own task ordering (Task 1's `files_modified` list deliberately excludes `test_browser_ux_health_drawings.py`, which Task 2 rewrites completely).
- **Resolution:** Re-ran the same intent with an explicit exclusion, `-k "(test_browser_ux or quiet_wake) and not health_drawings"`, confirming both still-legacy harnesses pass with 0 skipped — the actual property Task 1's acceptance criteria asks for. By the time Task 2 finished, the unscoped shim run (Task 3's full-suite sanity check) passed with `test_browser_ux_health_drawings` correctly no longer even appearing in the shim's parametrize list (it lost its `EXPECTED_CHECK_COUNT` marker).
- **Files modified:** None — this was a verification-command scoping adjustment only, not a code change.

## Issues Encountered

None beyond the verification-scoping note above.

## User Setup Required

None.

## Next Phase Readiness

- `companion/test_browser_ux_helpers.py`'s `make_context` factory parameter is now the established shape for 33-20 (`test_browser_ux.py`'s own migration) and 33-21 (`test_browser_ux_quiet_wake.py`'s own migration) to reuse when they convert their own remaining `browser.new_context()` call sites.
- `companion_app_server.LegacyHarness` now has exactly two remaining importers (`test_browser_ux.py`, `test_browser_ux_quiet_wake.py`) — once 33-20/33-21 finish, nothing outside `companion_app_server.py` itself needs `LegacyHarness`.
- The three module-scoped server fixtures (`server`/`band_server`/`grid_server`) and the seed functions (`seed_state_dir`/`_seed_band`/`_seed_grid`) in `test_browser_ux_health_drawings.py` are a working precedent for 33-20's own read-only browser-test groups.
- No blockers for 33-20/33-21 (the two remaining browser harnesses) or the companion_app migration chain.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 7 claimed created/modified files found on disk (`companion/test_browser_ux_helpers.py`,
`companion/test_browser_ux_health_drawings.py`, `companion/test_browser_ux.py`,
`companion/test_browser_ux_quiet_wake.py`, `test-support/skypane_test_support.py`,
`companion/test_suite_guards.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux_health_drawings.md`)
plus this summary, and all 3 commit hashes (`c9fad86`, `3ec7393`, `ac3280e`) found in
`git log --oneline --all`.
