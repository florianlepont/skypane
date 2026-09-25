---
phase: 35-comment-purge-in-english-and-dead-code
plan: 05
subsystem: testing
tags: [comments, hygiene, guard, pytest, server]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    provides: "scripts/check_comment_history.py (check/ratio/same-code), 35-01's source-read audit finding on server/test_illustrations.py"
provides:
  - "Every server/test_*.py file with 0 check --paths hits"
  - "Four source-text tests replaced with behaviour tests or deleted (orchestrator's TST-12 precedent addition)"
affects: [35-06 (group PR/close)]

tech-stack:
  added: []
  patterns:
    - "delete a docstring-content assertion outright when it asserts wording, not behaviour"
    - "replace inspect.getsource()/source-grep tests with a direct behaviour assertion (compare canvas bytes, monkeypatch the underlying table) when an equivalent check is not already present"

key-files:
  created: []
  modified:
    - server/test_poll_loop.py
    - server/test_render.py
    - server/test_calendar_rules.py
    - server/test_config_history.py
    - server/test_colour_rules.py
    - server/test_dither.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - server/test_manual_resolutions.py
    - server/test_notify.py
    - server/test_panel_preview.py
    - server/test_pipeline_e2e.py
    - server/test_plane_detection.py
    - server/test_runway_config.py
    - server/test_fault_screen_mask.py

key-decisions:
  - "test_fault_screen_mask.py (added to main since 35-05 was planned) was purged in Task 2, per the plan's own git-ls-files reconciliation instruction, and is recorded here as an addition beyond the plan's files_modified list."
  - "The extra source-text-tests task touched actual code (not just comments/docstrings) in test_render.py, test_config_history.py and test_illustrations.py, so those three files needed --allow on the same-code check; every other file passed same-code with no --allow."
  - "A ruff F401/F811 pair in test_render.py (module-level `import inspect` plus a redundant local `import inspect` inside test_illustration_functions_have_no_mirror_param) was exposed once the two inspect.getsource() removals left the local import as the module import's only real user; fixed by deleting the now-redundant local import (Rule 1 - lint bug caused by this plan's own edit)."

requirements-completed: [HYG-01]

duration: ~55min
completed: 2026-09-25
---

# Phase 35 Plan 05: Server test comment/docstring purge Summary

Purged every `server/test_*.py` file (15 files, 719 collected tests) of plan/ticket/decision/phase-history references in comments and docstrings, replaced four source-text tests (one docstring-content assertion, three `inspect.getsource()` greps) with behaviour assertions or deletions per the orchestrator's TST-12 precedent addition, and confirmed `pytest server` and `same-code` against `ee2737a` both stay green throughout.

## Performance

- **Duration:** ~55 min
- **Tasks:** 2 plan tasks + 1 orchestrator-added extra task (4 sub-items)
- **Files modified:** 15 (all of `server/test_*.py`)

## Accomplishments

- `server/.venv/bin/python scripts/check_comment_history.py check --paths <every server/test_*.py file>` exits 0.
- `git grep -n "inspect.getsource\|__doc__" -- 'server/test_*.py'` returns nothing.
- `pytest server -q -n auto`: 716 passed, 3 skipped, 719 collected - unchanged from the pre-purge baseline.
- `same-code --base ee2737a` passes for every file; `test_render.py`, `test_config_history.py` and `test_illustrations.py` needed `--allow` (the extra source-text-tests task's legitimate code changes); the other twelve files pass with no `--allow`.
- `ruff check server/test_*.py`: all checks passed.

## Task Commits

Task 1 "Purge the large server test files" and Task 2 "Purge the remaining server test files" are each a single commit; the orchestrator's extra source-text-tests task is four separate commits, one per test, landed **before** the purge commits touched those files, per its own instruction:

1. `0293325` - test(35-05): delete docstring-content assertion from test_config_history
2. `65c8838` - test(35-05): replace source-grep test with a behaviour assertion for quiet_hours dispatch
3. `d94504e` - test(35-05): replace source-grep test with a behaviour assertion for no-connection dispatch
4. `54138fb` - test(35-05): replace source-grep test with a behaviour assertion for target_variants_by_airline
5. **Task 1** - `12b1926` - docs(35-05): purge comment/docstring history from the large server test files
6. **Task 2** - `3e5bbab` - docs(35-05): purge comment/docstring history from the remaining server tests

## Files Created/Modified

- `server/test_poll_loop.py` - Task 1, purged
- `server/test_render.py` - Task 1, purged; also the extra task's items 2/3 (behaviour tests) and the ruff-exposed local-import fix
- `server/test_calendar_rules.py` - Task 1, purged
- `server/test_config_history.py` - Task 1, purged; also the extra task's item 1 (deletion)
- `server/test_colour_rules.py`, `test_dither.py`, `test_enrich.py`, `test_manual_resolutions.py`, `test_notify.py`, `test_panel_preview.py`, `test_pipeline_e2e.py`, `test_plane_detection.py`, `test_runway_config.py` - Task 2, purged
- `server/test_illustrations.py` - Task 2, purged; also the extra task's item 4 (behaviour test)
- `server/test_fault_screen_mask.py` - Task 2, purged (added to main since planning, per Task 2's own reconciliation instruction)

## Source-text tests (orchestrator addition, Phase 33 TST-12 precedent)

| Node id | Action | Reason |
|---|---|---|
| `server/test_config_history.py::test_check_in_gaps_docstring_states_what_it_cannot_know` | Deleted | Asserted substrings of `history_db.check_in_gaps.__doc__`; no behaviour under test. Docstrings are documentation, not a contract (D-A3/TST-12). |
| `server/test_render.py::test_quiet_hours_branch_precedes_empty_branch_in_source` | Replaced (renamed) with `test_quiet_hours_state_wins_over_empty_when_flight_is_none` | The original used `inspect.getsource(render.build_canvas)` to check dispatch-branch text order. Replaced with a behaviour assertion: `build_canvas(None, "quiet_hours")` must not equal `build_canvas(None, "empty")` in bytes - proves the quiet_hours branch actually wins for the same `flight is None` input, without reading source text. |
| `server/test_render.py::test_build_canvas_never_dispatches_no_connection_canvas` | Replaced (renamed) with `test_build_canvas_never_produces_the_no_connection_canvas` | The original greped `inspect.getsource(render.build_canvas)` for the private function name `_build_no_connection_canvas`. Replaced with a behaviour assertion: for every state `build_canvas()` accepts (battery_empty, display_off, quiet_hours, empty, departing, arriving), its output bytes never match `render._build_no_connection_canvas()`'s output bytes. |
| `server/test_illustrations.py::test_variants_derived_from_targets_no_second_table` | Replaced (same name) | The original used `inspect.getsource(ill.target_variants_by_airline)` to grep for the identifier `_ILLUSTRATION_TARGETS`. Replaced with a behaviour assertion: monkeypatch `ill._ILLUSTRATION_TARGETS` with a small four-row fake table and assert `target_variants_by_airline()` returns exactly the expected `(name, [shapes])` pairs derived from it - proves the function is actually derived from the table's live contents, not merely that the identifier appears in source. |

After these four commits, `git grep -n "inspect.getsource\|__doc__" -- 'server/test_*.py'` returns nothing.

## Decisions Made

- Test docstrings compressed to the "one line stating what behaviour is checked" convention throughout; narrative "Plan X, Task Y", "Quick task NNNNNN-xxx", "Phase N", `.planning/` paths and decision-history parentheticals were dropped or rewritten as a short *why* where the surrounding setup was non-obvious (e.g. `test_render.py`'s 124 numbered `# N. Plan ...` comment-block preambles removed wholesale since each preceding docstring already restated the same behaviour in one line).
- Assertion-message string literals (`pytest.fail("... (D-XX)" % ...)`) were left untouched everywhere, even where the same ID also appeared in a now-purged neighbouring docstring or comment - confirmed the `check` tool itself never scans code string literals, only comments and docstrings, so this boundary was mechanically verifiable at every step.
- `server/test_render.py`'s module docstring, top-of-file constant comments (`TEST_ROUTE`/`TEST_PREVIOUS_ROUTE`/`TEST_LONG_ROUTE`, `IDX_TO_NIBBLE`) and the illustration-crop-text-margin debug-session comment block were rewritten to keep the *why* (real fixtures vs. synthetic values, spread-vs-absolute-position rationale) while dropping every plan/decision/phase reference.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff F401/F811 pair in test_render.py exposed by the extra task's own edits**
- **Found during:** Task 1 (ruff check after purging `test_render.py`)
- **Issue:** `test_illustration_functions_have_no_mirror_param()` had a local `import inspect` shadowing the module-level `import inspect`. Before this plan, the module-level import was also used by the two `inspect.getsource()` calls the extra task removed; once those were gone, the module-level import became genuinely unused (F401) and the local import became a pointless redefinition (F811).
- **Fix:** Deleted the local `import inspect` inside the function; the module-level import (still used by `inspect.signature()` at the same call site) covers it.
- **Files modified:** `server/test_render.py`
- **Verification:** `ruff check server/test_*.py` passes; `pytest server/test_render.py` still 146 passed.
- **Committed in:** `12b1926` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1).
**Impact on plan:** No scope creep - a lint regression caused directly by the extra task's own code changes, fixed in the same file before that file's purge commit.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Server test group (directory group 2, per `35-CONTEXT.md`) is fully purged: `server/plane/*` (35-02/35-03/35-04) and every `server/test_*.py` (35-05) all report 0 `check --paths` hits.
- `35-01`'s deferred class (b) source-read finding for `server/test_illustrations.py` is resolved (item 4 of the extra task).
- The next plan in this phase (35-06, per the orchestrator) handles push/PR for group 2; no blockers.

## Self-Check: PASSED

All 15 modified `server/test_*.py` files exist on disk; all 6 commit hashes (`0293325`, `65c8838`, `d94504e`, `54138fb`, `12b1926`, `3e5bbab`) are present in `git log --oneline --all`.
