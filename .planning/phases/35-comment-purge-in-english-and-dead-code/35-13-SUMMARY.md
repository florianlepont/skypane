---
phase: 35-comment-purge-in-english-and-dead-code
plan: 13
subsystem: companion-comment-hygiene
tags: [comment-hygiene, dead-code, hyg-05, companion, ci-guard, ratchet]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 08
    provides: "companion/app.py, auth.py and ten small companion modules purged of history"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 09
    provides: "companion/pages/config_page.py purged of history"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 10
    provides: "companion/pages/health_page.py, history_page.py purged of history (health_severity()/anomaly_active() deliberately left in place for this plan)"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 11
    provides: "companion/layout.py, draw.py purged of history (usable_pairs()/label_grid() deliberately left in place for this plan)"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 12
    provides: "companion/pages/airlines_page.py, home_page.py, pages/__init__.py, companion/i18n_fr/*.py purged of history"
provides:
  - "HYG-05 delivered: health_page.health_severity(), health_page.anomaly_active(), draw.usable_pairs(), draw.label_grid() deleted — confirmed dead against current main by git grep, together with the tests that existed only to exercise them"
  - "Three tests that used the deleted functions as a live-behaviour oracle re-pointed to health_page.safe_health_state() (the function app.py's page_context() actually calls), keeping their names and assertion intent"
  - "Group 4 (companion Python production) closed: same-code passes with a minimal 3-file allow list, 0 history-check hits, removed from scripts/comment-history-pending.txt, CI now enforces it directly"
  - "35-COMMENT-RATIO.md group-4 section: 33 files, 30353 -> 17371 lines, 64% -> 36% comments, 3620 -> 0 history hits, matching 35-BASELINE/INDEX.md's group-4 row exactly"
affects: [35-14, 35-15, 35-16, 35-17, 35-18, 35-19, 35-20, 35-21, 35-22]

tech-stack:
  added: []
  patterns:
    - "A group-close plan's own git-grep re-check can surface a planning-time-stale file reference: this plan's files_modified list named a companion/test_status_pages.py that Phase 33's harness migration had already retired; the real caller (test_status_pages_07.py) was found only by re-running git grep against current main rather than trusting the plan's recorded line numbers"
    - "When a deleted function's docstring made a factual claim about its own role ('this module's one public cross-page export'), re-checking that claim against the actual caller (app.py calls safe_health_state(), never anomaly_active()) confirmed the candidate really was dead, not just history-purged prose describing a still-live path"
    - "A test that mixes an assertion on the deleted function with unrelated live assertions (test_draw_module_scales_clamp_and_never_raise, which also exercises percent_x/percent_y/unit_circle_dash_array/is_number) is neither case (a) delete-whole-test nor (b) re-point-as-oracle — it needed a partial edit removing only the dead-function lines while the rest of the test and its name stay"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/draw.py
    - companion/test_companion_app_02.py
    - companion/test_status_pages_01.py
    - companion/test_status_pages_04.py
    - companion/test_status_pages_07.py
    - scripts/comment-history-pending.txt
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "health_page.py's app.py/auth.py/pages/__init__.py check (35-13's Task 1 action item 4) found nothing to fix: app.py is now 2258 lines (its ~3450/3514 line numbers from planning time no longer exist — 35-08 had already purged those comments), and auth.py's ~63 area was already clean. Recorded as verified-clean, not a no-op skip."
  - "Kept companion/draw.py's DRAWING_GRID_CLASS/DRAWING_Y_LABELS_CLASS/DRAWING_X_LABELS_CLASS constants (label_grid()'s former CSS-class arguments) rather than deleting them: they remain referenced inside the DRAWING_CLASSES tuple, which a harness test (test_every_drawing_class_resolves_in_the_served_stylesheet) still legitimately uses to assert every declared drawing class resolves to a real style.css selector — deleting them would touch companion/static/style.css (group 7, a different plan's scope) for no correctness gain, since a class existing in Python with no current emitter is not itself dead code the way an unreachable function is."
  - "Modified companion/test_status_pages_07.py even though it is not in the plan's files_modified list: git grep against current main found its call to health_page.health_severity() at line 702 (the plan's own planner_findings cited a stale companion/test_status_pages.py:~5982, a file retired by Phase 33's harness migration and absent from current main). Re-pointing it was required to complete the deletion cleanly (Rule 3, blocking issue) — deleting health_severity() without fixing this caller would have broken the suite."
  - "Left the module-level historical docstrings in test_status_pages_01.py/_04.py (Phase-33-migration narrative, plan-ID references) untouched: this plan's must_haves scope 'no comment describing a removed feature' to production code, and these test-file docstrings are group 5's (companion tests) purge scope, not group 4's — editing them here would risk conflicting with a later plan's own pass over the same file."

requirements-completed: [HYG-05]

duration: ~35min
completed: "2026-09-25"
---

# Phase 35 Plan 13: HYG-05 dead code + close group 4 (companion Python production) Summary

**Deleted four confirmed-dead functions (health_page.health_severity/anomaly_active, draw.usable_pairs/label_grid), re-pointed three oracle tests to the live severity path, then closed PR group 4 with a minimal 3-file same-code allow list, 0 remaining history-check hits, and HYG-05 marked complete.**

## Performance

- **Duration:** ~35 min (approximate — start time not captured at session start)
- **Completed:** 2026-09-25T15:53:38Z
- **Tasks:** 2 completed
- **Files modified:** 9 (6 in Task 1, 3 in Task 2)

## Accomplishments

- Re-checked all four HYG-05 candidates against current main with `git grep -nw`: none has a production caller (only test callers remained), confirming they were safe to delete.
- Deleted `health_page.health_severity()` and `health_page.anomaly_active()`; confirmed the live `ctx["health_severity"]` path (`app.py` calling `health_page.safe_health_state()`) is untouched. Updated the module docstring and two internal docstrings that named the deleted functions by name.
- Deleted `draw.usable_pairs()` and `draw.label_grid()`; retitled the section header that now covers only `is_number()`. Confirmed `DRAWING_GRID_CLASS`/`DRAWING_Y_LABELS_CLASS`/`DRAWING_X_LABELS_CLASS` (label_grid's own CSS-class constants) stay referenced by the `DRAWING_CLASSES` harness tuple and are out of this plan's scope.
- Re-pointed three tests that used the deleted functions as a live-behaviour oracle (`test_anomaly_active_never_raises_on_hostile_inputs`, `test_anomaly_active_agrees_with_the_banner_both_directions`, and one severity assertion inside `test_health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn`) to call `health_page.safe_health_state()` directly — the function `app.py`'s `page_context()` actually calls — keeping every test's name and assertion intent.
- Partially edited `test_draw_module_scales_clamp_and_never_raise()` (not a full a/b/c case: it exercises multiple `draw.py` helpers, only some of which involve `usable_pairs()`) to drop only the `usable_pairs()`-specific fixture and assertions.
- Group-4 `same-code` passes against base `059774e` for all 33 changed companion production files with a 3-file allow list (`app.py` for `__doc__`, `health_page.py`/`draw.py` for this plan's own deletions); re-running without the two dead-code allows confirmed exactly those two files (and no others) fail, proving the allow list is minimal.
- The four test files Task 1 changed pass their own separate group-5 `same-code` check.
- Removed all 33 companion production paths from `scripts/comment-history-pending.txt`; `check` (no args) and `check --paths` over the production files both exit 0 — CI now enforces companion production directly.
- Appended the group-4 section to `35-COMMENT-RATIO.md` (33 files, 30353 -> 17371 lines, 64% -> 36% comments, 3620 -> 0 history hits), matching `35-BASELINE/INDEX.md`'s group-4 row exactly, with above-~35%-guideline justifications summarized from 35-08/35-09/35-10/35-11/35-12's own SUMMARYs.
- Marked HYG-05 complete in `REQUIREMENTS.md` (checkbox and traceability table); HYG-01 left open per instructions, since it spans groups not yet closed.
- Full suite green (2564 passed, 132 skipped — pre-existing Playwright-environment skips) with coverage 93.07% against the 93.0% gate; `ruff check .` clean.

## Task Commits

1. **Task 1: Re-check the candidates and delete the dead code** - `24a1183` (refactor)
2. **Task 2: Group-4 proof, ratchet and PR** - `8fe06ea` (docs)

## Dead-Code Table

| Candidate | Production callers found | Test callers found | Action |
|---|---|---|---|
| `health_page.health_severity()` | None | `test_status_pages_07.py:702` | Deleted. Test re-pointed to `safe_health_state()`. |
| `health_page.anomaly_active()` | None | `test_status_pages_01.py:480/494/502`, `test_status_pages_04.py:666` | Deleted. Both tests re-pointed to `safe_health_state()`. |
| `draw.usable_pairs()` | None | `test_companion_app_02.py:1277/1288` | Deleted. Test's `usable_pairs`-only lines removed; rest of the (multi-purpose) test stays. |
| `draw.label_grid()` | None | None | Deleted outright — no test anywhere called it. |

`companion/pages/__init__.py`'s docstring mention of `ctx["health_severity"]` (the live dict key, not the deleted function) and `companion/app.py`'s two live reads of `health_state["severity"]`/`ctx["health_severity"]` are untouched — confirmed by re-reading both files.

## Test Node IDs Affected (per Task 1's a/b/c instruction)

| Test node id | File | Category | What changed |
|---|---|---|---|
| `test_anomaly_active_never_raises_on_hostile_inputs` | test_status_pages_01.py | (b) oracle, re-pointed | `health_page.anomaly_active(...)` calls replaced by a local `_anomaly_active()` helper wrapping `health_page.safe_health_state(...)`; name and assertion intent unchanged. |
| `test_anomaly_active_agrees_with_the_banner_both_directions` | test_status_pages_04.py | (b) oracle, re-pointed | Same re-point, inlined at the call site; name and assertion intent unchanged. |
| `test_health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn` | test_status_pages_07.py | (b) oracle, re-pointed | `health_page.health_severity(...)` call replaced with `health_page.safe_health_state(...)["severity"]` (fail-closed to `"ok"` on `None`, matching the deleted function's own semantics). Not in the plan's files_modified list — see key-decisions. |
| `test_draw_module_scales_clamp_and_never_raise` | test_companion_app_02.py | partial (neither a/b/c — see key-decisions) | Removed the `usable_pairs()` fixture rows and both `draw.usable_pairs(...)` assertion blocks; kept every other assertion in the same test (percent_x/percent_y/unit_circle_dash_array/is_number/etc.), which do not touch a deleted function. Docstring's `usable_pairs()` clause dropped. |

No test module was deleted outright (Task 1 action item 5 — not expected, did not happen).

## Files Created/Modified

- `companion/pages/health_page.py` — deleted `health_severity()`/`anomaly_active()`; rewrote the module docstring, `collect_anomalies()`'s docstring, `safe_health_state()`'s docstring, and `_read_health_inputs()`'s docstring to no longer name the deleted functions.
- `companion/draw.py` — deleted `usable_pairs()`/`label_grid()`; retitled the `is_number()` section header.
- `companion/test_companion_app_02.py` — partial edit to `test_draw_module_scales_clamp_and_never_raise()` (see table above).
- `companion/test_status_pages_01.py` — re-pointed `test_anomaly_active_never_raises_on_hostile_inputs()` via a new `_anomaly_active()` local helper.
- `companion/test_status_pages_04.py` — re-pointed `test_anomaly_active_agrees_with_the_banner_both_directions()` inline.
- `companion/test_status_pages_07.py` — re-pointed the severity assertion inside `test_health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn()`.
- `scripts/comment-history-pending.txt` — removed 33 companion production paths (177 -> 144 lines).
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` — appended the group-4 (companion production) section.
- `.planning/REQUIREMENTS.md` — HYG-05 checkbox and traceability-table status marked Complete.

## Decisions Made

See `key-decisions` in the frontmatter above. In short: (1) app.py/auth.py's "removed feature" comments were already gone by 35-08, verified rather than assumed; (2) draw.py's now-emitterless CSS-class constants were kept, since they're still referenced by a legitimate style.css-resolution harness test and touching them would reach into group 7's scope; (3) test_status_pages_07.py was fixed even though absent from the plan's files_modified list, because the plan's own planner_findings cited a file (`companion/test_status_pages.py`) that Phase 33 had already retired, and leaving the real caller unfixed would have broken the suite; (4) the two files' module-level historical docstrings (plan-ID narrative) were left alone as group 5's purge scope, not this plan's.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's files_modified list omitted the real caller of health_severity()**
- **Found during:** Task 1, running the read-first `git grep -nw` across the whole repo.
- **Issue:** The plan's `<planner_findings>` and frontmatter `files_modified` list `companion/test_status_pages.py:~5982` as a caller of `health_severity()`. That file does not exist on current main — Phase 33's harness migration split it into `test_status_pages_01.py` through `_07.py` and retired the original (confirmed via `git log --oneline --all -- companion/test_status_pages.py`, last touched by the Phase-33-completion commit). The actual caller is `companion/test_status_pages_07.py:702`, a file not in the plan's `<files>` or `files_modified` lists.
- **Fix:** Re-pointed `test_status_pages_07.py`'s severity assertion the same way as the other two oracle tests, keeping the test name and assertion intent.
- **Files modified:** `companion/test_status_pages_07.py`
- **Verification:** Full companion pytest run (1545 passed) and the full suite (2564 passed) both green; the group-5 same-code check for this file (run manually alongside the other three Task-1-changed test files) passes with `--allow companion/test_status_pages_07.py`.
- **Committed in:** `24a1183` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — a stale file reference in the plan's own planner_findings)
**Impact on plan:** Required to complete the HYG-05 deletion without breaking the suite. No scope creep beyond the one additional file the deletion itself made necessary.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required.

## Verification Results

- **Task 1 automated verify:** `git grep -nE "def (health_severity|anomaly_active|usable_pairs|label_grid)\b|[.](health_severity|anomaly_active|usable_pairs|label_grid)[(]|^from .* import .*\b(usable_pairs|label_grid|health_severity|anomaly_active)\b" -- companion ':!companion/test_suite_guards.py'` -> exit 1 (no matches, as required by the `!` negation) -> `pytest companion -q -n auto` -> 1545 passed, 129 skipped -> `ruff check companion` -> "All checks passed!"
- **Group-level same-code (production):** `same-code --base 059774e --allow companion/app.py --allow companion/pages/health_page.py --allow companion/draw.py <33 changed files>` -> exit 0. Without the two dead-code allows: exactly `companion/draw.py` and `companion/pages/health_page.py` fail, nothing else — confirming the allow list is minimal and exact.
- **Group-5 same-code (the four Task-1-changed test files):** `same-code --base 059774e --allow companion/test_companion_app_02.py --allow companion/test_status_pages_01.py --allow companion/test_status_pages_04.py --allow companion/test_status_pages_07.py <those 4 files>` -> exit 0.
- **Check --paths (production):** `check --paths <33 files>` -> 0 history hits.
- **Pending list:** all 33 `^companion/(pages/|i18n_fr/|app\.py|auth\.py|layout\.py|draw\.py|...)` production paths removed; `check` (no args) -> exit 0.
- **Ratio table:** `35-COMMENT-RATIO.md` group-4 section — 33 files, 30353 -> 17371 lines, 63.6% -> 36.4% comments, 3620 -> 0 history hits (matches `35-BASELINE/INDEX.md`'s group-4 row exactly: 33 files, 30353 lines, 64%, 3620 hits).
- **Full suite:** `./scripts/run-all-tests.sh` -> 2564 passed, 132 skipped (pre-existing Playwright-environment skips, unrelated to this plan), 0 failed; coverage 93.07% against the 93.0% `fail_under` gate (exit 0).
- **ruff:** `server/.venv/bin/ruff check .` -> "All checks passed!"
- **Base equals merge-base:** `git merge-base HEAD origin/main` -> `059774ec03b86073e97a7e0462fd4b224ab289d3`, matching the literal instructed base `059774e`; `git fetch origin main` found no new commits to merge, so no STATE/ROADMAP conflict resolution was needed.
- **PR:** not opened by this executor — per the orchestrator's instructions, this plan stayed on `claude/plan-phase-35` and did not push or open a PR; the orchestrator handles push/PR after this plan returns.

## Follow-ups for other maintainers (out of scope here)

- `.claude/skills/sketch-findings-skypane/references/data-density.md` mentions `usable_pairs`/`label_grid` by name (both now deleted from `companion/draw.py`). This file is explicitly out of this phase's scope (`.claude/skills/` is excluded per `35-CONTEXT.md`'s Deferred Ideas) and was not edited. Flagging for the skill maintainer to update the reference the next time that skill file is touched.

## Next Phase Readiness

HYG-05 is delivered and group 4 (companion Python production) is closed: `same-code`-proven code-unchanged (modulo the four HYG-05 deletions and `app.py`'s `__doc__`), 0 comment-history hits, and CI-enforced via the pending-list removal. Remaining pending-list groups (companion tests + test-support, companion static JS, `companion/static/style.css`, `deploy/`+`scripts/`+`.github/`+..., `firmware/`) are unaffected, aside from the one additional test file (`test_status_pages_07.py`) this plan's own dead-code deletion required touching. HYG-01/HYG-02/HYG-03/HYG-06 in `REQUIREMENTS.md` intentionally left unmarked, since they span groups not yet closed.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-13-SUMMARY.md` — FOUND
- Commit `24a1183` (Task 1: delete HYG-05 dead code) — FOUND
- Commit `8fe06ea` (Task 2: close group 4, mark HYG-05 complete) — FOUND
