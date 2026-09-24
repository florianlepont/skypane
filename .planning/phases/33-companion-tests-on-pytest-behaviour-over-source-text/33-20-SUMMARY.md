---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 20
subsystem: testing
tags: [pytest, pytest-playwright, chromium, browser-tests, companion, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "19"
    provides: "companion/test_browser_ux_helpers.py's make_context factory-parameter shape (every context-opening helper takes a make_context callable instead of a raw browser object), companion_app_server.LegacyHarness as the still-legacy import this file dropped, and the module-scoped/function-scoped server fixture precedent from test_browser_ux_health_drawings.py"
provides:
  - "companion/test_browser_ux_quiet_wake.py: all 9 legacy checks (D17's quiet-hours dial series plus D18's wake-interval slider series) rewritten as 9 native pytest-playwright test node ids, each with its own function-scoped make_app_server(seed=seed_state_dir, fake_providers=True) server since every one of them saves a real setting"
  - "main(), check(), EXPECTED_CHECK_COUNT, sync_playwright() and the LegacyHarness import are gone from this file — it leaves the disk-derived ORIGINAL_COMPANION_HARNESSES legacy set and companion/test_legacy_harness_shim.py's parametrize list"
  - "the migration ledger fragment for this harness closed: 9/9 rows ported, 0 pending"
affects: [33-21, 33-22, 33-23, 33-24, 33-33]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A mutating browser check (one that saves a real setting through the UI) gets its own function-scoped make_app_server fixture rather than sharing a module-scoped one — this file's all-9-checks-mutate shape is the first full precedent for 33-MIGRATION-RULES.md section 2's isolation rule applied to an entire browser harness, not just a subset of its checks"
    - "A closure-captured on-disk-state reader (`_quiet_hours_on_disk()`, `_wake_interval_on_disk()`) that used to close over a single shared Harness instance is promoted to a plain module-level function taking an explicit state_dir parameter, so every test's own server.tmpdir threads through it explicitly instead of through a name only one shared harness used to bind"
    - "A helper's read_back callback (`_persist_without_js(..., read_back, ...)`) must be a zero-argument closure over the CURRENT test's own server.tmpdir, never a bare reference to a state-reader function that itself now takes an explicit argument — passing the bare function fails at call time with a missing-argument error, not at import time, so it does not show up until the check actually runs"

key-files:
  created: []
  modified:
    - companion/test_browser_ux_quiet_wake.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux_quiet_wake.md

key-decisions:
  - "None of the file's nine checks were parametrized: every one either drives a single named interaction (drag, held-press, floors-at-360px) or an internal loop whose final assertion compares values ACROSS iterations (both themes must differ, both languages must agree on width, the caption's SAME reference shape must survive four different interaction kinds) — splitting any of these into independent parametrized cases would need one parametrized run to re-derive data another run depends on, which 33-MIGRATION-RULES.md section 2 forbids under xdist. This mirrors 33-19's own decision for the 9 non-ring health-drawings checks."
  - "Task 1's intermediate commit removes only the five quiet-hours-dial checks it ports from main(), leaving main() itself, its Harness-based checks 6-9, and their own internal (unchanged, closure-based) copies of the dial preamble completely untouched and still self-consistent — proven by running the shrunk legacy file directly as a script and getting '4/4 checks pass'. The new pytest tests get their OWN, separately-defined module-level QUIET_DIAL_SEL/_quiet_hours_on_disk/_set_window/_SETTLE_DIAL; Python's normal name resolution (nested-function-in-main() shadows module level) means both copies coexist without collision, so Task 1's diff never has to touch code it is not yet porting. Task 2 replaces both copies at once when it deletes main()."
  - "The module-level EXPECTED_CHECK_COUNT = 9 line (and the three now-unused sibling selector constants QUIET_ARC_SEL/QUIET_HANDLES_SEL/QUIET_READOUT_SEL inside main()'s own local scope) were removed already in Task 1's commit, one task ahead of main()'s own deletion in Task 2 — required so pytest's disk-derived legacy-file detection (`skypane_test_support.legacy_companion_harnesses()`, keyed on the literal EXPECTED_CHECK_COUNT = source line) stops collect-ignoring the whole file after Task 1, which is what lets Task 1's own <verify> command (a plain `pytest companion/test_browser_ux_quiet_wake.py`) actually collect and run the five new tests instead of reporting 'no tests collected'. main()'s own final return statement was reworded to compare passed against total rather than against the now-gone name."

requirements-completed: [TST-10, TST-11, TST-12, TST-13, TST-14, TST-15]

# Metrics
duration: 27min
completed: 2026-09-24
---

# Phase 33 Plan 20: Quiet-Hours Dial and Wake-Interval Slider Browser Migration Summary

**Rewrote `companion/test_browser_ux_quiet_wake.py` in place — all 9 legacy quiet-hours-dial/wake-interval-slider checks are now native pytest-playwright tests, each with its own function-scoped server, and the file's `main()`/`check()`/`EXPECTED_CHECK_COUNT`/`LegacyHarness` scaffolding is gone.**

## Performance

- **Duration:** ~27 min (commit-to-commit, previous plan's last commit `281d9f5` at 14:39:03Z to this plan's last commit `56e4e77` at 15:05:53Z)
- **Started:** 2026-09-24T14:39:03Z
- **Completed:** 2026-09-24T15:05:53Z
- **Tasks:** 3/3 completed
- **Files modified:** 2

## Accomplishments

- `companion/test_browser_ux_quiet_wake.py` is a pytest-playwright module: `pytestmark = pytest.mark.browser`, no more `EXPECTED_CHECK_COUNT`/`check()`/`main()`/`sync_playwright()`/`LegacyHarness` import, no more manual `sys.path` bootstrap (pytest's own `companion/conftest.py` covers it). Every one of the nine checks (D17's quiet-hours dial: save-with-scripts-blocked, drag/keyboard, arc/handles/caption agreement, caption-form-after-every-interaction-kind, floors-at-360px, held-press-stays-on-ring; D18's wake-interval slider: save-with-scripts-blocked, drag/keyboard, floors-at-360px) is its own `test_` function with the old check's label as its docstring, taking `new_context` and a fresh, function-scoped `server` fixture (`make_app_server(seed=seed_state_dir, fake_providers=True)`) — every check saves a real setting through the real UI, so none of them may share a server across xdist workers.
- Every `browser.new_context(...)` call site (and every bare `browser.new_context` passed as a `make_context` callable into the shared helpers from `test_browser_ux_helpers.py`) is now the guarded `new_context` fixture from `companion/conftest.py`. Every `return False, (...)` became a raised `AssertionError`; every `return True, ""` was dropped in favour of a plain fall-through return.
- The two closures that used to read on-disk state through a single shared `Harness` (`_quiet_hours_on_disk()`, `_wake_interval_on_disk()`, plus `_set_window()`/`_set_interval()`) are now plain module-level functions taking an explicit `state_dir` parameter, called with each test's own `server.tmpdir`. One real bug this surfaced during the rewrite: `_persist_without_js()`'s `read_back` parameter is a zero-argument callback, and the wake-interval save check used to pass the bare (zero-argument, closure-based) `_wake_interval_on_disk` reference directly — after promoting that function to take `state_dir`, the bare reference would have failed at call time with a missing-argument error the moment the check actually ran. Fixed by wrapping it in a local `read_back()` closure over the test's own `server.tmpdir` before it is ever passed in (both call sites, in `test_the_wake_interval_still_saves_with_scripts_blocked_through_the_slider`).
- Task 1's own intermediate commit (5 of 9 checks ported) proved out cleanly at both ends: `pytest companion/test_browser_ux_quiet_wake.py` collected and passed the 5 new tests, and running the shrunk legacy file directly as a script (`python3 companion/test_browser_ux_quiet_wake.py`) still printed `4/4 checks pass` for the four checks Task 1 deliberately left in `main()` untouched — confirming the module-level and main()-local copies of the shared dial preamble coexist correctly under Python's normal name shadowing.
- The migration ledger fragment (`33-ledger/companion__test_browser_ux_quiet_wake.md`) has all 9 rows flipped to `ported`, each pointing at a real `[chromium]` node id; `33-ledger-check.py` confirms `9/9 baseline checks mapped (9 ported, 0 deleted, 0 pending)`. Two narrative mentions of `EXPECTED_CHECK_COUNT` inside a docstring/comment (referring to a past planning decision, not a live declaration) were reworded so the file carries zero occurrences of the legacy markers the plan's own acceptance grep checks for.
- Full-suite sanity beyond this plan's own scoped verification: `SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server` — **1382 passed, 5 skipped (all pre-existing root-permission skips), 0 failed**, in 261.73s. `ruff check .` is clean across the whole tree. The 57 warnings reported are all pre-existing Pillow `Image.getdata` deprecations in `server/test_panel_preview.py` and `server/test_render.py`, neither of which this plan touched.

## Task Commits

1. **Task 1: First half of the quiet-wake checks** - `a645616` (test)
2. **Task 2: Remaining checks; remove the legacy runner** - `d309853` (test)
3. **Task 3: Ledger, commit and push** - `56e4e77` (docs)

## Files Created/Modified

- `companion/test_browser_ux_quiet_wake.py` - rewritten in place as 9 pytest-playwright test node ids; `main()`/`check()`/`EXPECTED_CHECK_COUNT`/`sync_playwright()`/`LegacyHarness` removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux_quiet_wake.md` - 9 rows flipped to `ported`, Part 01 note added

## Decisions Made

See `key-decisions` in the frontmatter: why none of the nine checks were parametrized (every internal loop's final assertion compares values across iterations), why Task 1's intermediate commit could safely leave `main()`'s own four remaining checks completely untouched (module-level vs. main()-local name shadowing), and why `EXPECTED_CHECK_COUNT` had to be removed a task earlier than `main()` itself (pytest's disk-derived collect-ignore is keyed on that one literal source line).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_persist_without_js()`'s `read_back` callback for the wake interval was a stale bare function reference after promoting `_wake_interval_on_disk` to take an explicit parameter**
- **Found during:** Task 2, while porting `test_the_wake_interval_still_saves_with_scripts_blocked_through_the_slider`
- **Issue:** The mechanical harness-to-server rename left `_persist_without_js(new_context, base_url, "/device", "wake_interval_s", "900", _wake_interval_on_disk, ...)` passing the bare `_wake_interval_on_disk` function object as the zero-argument `read_back` callback. Once that function was promoted to module level with an explicit `state_dir` parameter, calling it with zero arguments (which `_persist_without_js()` does internally) would raise `TypeError: missing 1 required positional argument: 'state_dir'` the first time either of the two calls in this check actually ran — a failure that would only surface at test-run time, not at import or collection time.
- **Fix:** Added a local `read_back()` closure (`return _wake_interval_on_disk(server.tmpdir)`) inside the test function and passed `read_back` instead of the bare `_wake_interval_on_disk` reference at both of this check's `_persist_without_js()` call sites.
- **Files modified:** `companion/test_browser_ux_quiet_wake.py`
- **Verification:** `SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion/test_browser_ux_quiet_wake.py -q -rs` — 9/9 passed, including this check.
- **Committed in:** `d309853` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — without the fix this check would fail every time it actually ran (not merely on collection), which the plan's own acceptance criteria (9/9 passed) would have caught immediately. No scope creep.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None.

## Next Phase Readiness

- `companion/test_browser_ux_quiet_wake.py` is fully migrated: gone from `ORIGINAL_COMPANION_HARNESSES`'s legacy subset, gone from `companion/test_legacy_harness_shim.py`'s parametrize list, and its ledger fragment closed with 0 pending rows.
- `companion_app_server.LegacyHarness` now has exactly one remaining importer: `companion/test_browser_ux.py` (33-21's own job, per 33-19's "Next Phase Readiness" note — this plan's number in that note was written before 33-20/33-21's final numbering settled, but the remaining-importer count it predicted is unaffected).
- The "module-level function-scoped-server-per-mutating-check" pattern this plan establishes (as opposed to per-check `Harness()` instances or a shared module-scoped server) is available as precedent for 33-21's own migration of the much larger `test_browser_ux.py` (75 checks at last baseline), which will likely need a mix of function- and module-scoped servers depending on which of its checks mutate.
- No blockers for 33-21 (the last remaining browser harness) or the companion_app migration chain. Full suite verified green (1382 passed, 5 skipped, 0 failed) with `SKYPANE_REQUIRE_BROWSER=1` and a real Chromium.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 3 claimed created/modified files found on disk (`companion/test_browser_ux_quiet_wake.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux_quiet_wake.md`,
plus this summary), and all 3 commit hashes (`a645616`, `d309853`, `56e4e77`) found in
`git log --oneline --all`.
