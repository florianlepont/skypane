---
phase: 35-comment-purge-in-english-and-dead-code
plan: 15
subsystem: companion-comment-hygiene
tags: [comment-hygiene, hyg-01, companion, status-pages, view-pages]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 13
    provides: "HYG-05 dead code deleted (health_severity, anomaly_active, usable_pairs, label_grid); group 4 (companion Python production) closed, 0 comment-history hits"
provides:
  - "The 14 companion/test_status_pages*.py and test_view_pages*.py files (test_status_pages_01..07.py, _05b.py, _helpers.py, test_view_pages_01..04.py, _helpers.py) purged of plan/ticket/decision/phase IDs, change narration and stale references to deleted functions — 0 check-tool hits, same-code proves the AST is unchanged against base 8a8b8b4"
  - "Comment lines cut across the family (3850 -> 3223, 16%), with test docstrings collapsed to one behaviour-stating sentence and comment blocks trimmed to the why; history-check hits cut from 921 to 0"
  - "The status_pages family's collected node count is unchanged (484 before and after) and the view_pages family's is unchanged (186 before and after); the combined 670 tests all pass"
affects: [35-17]

tech-stack:
  added: []
  patterns:
    - "Two-stage purge per file: a mechanical first pass (a scratch Python script stripping every history-id pattern the guard's own PATTERNS list matches, plus a curated COMPOUND_PATTERNS list for 'quick task NNNNNN-xxx' and 'rubric X' phrases) followed by a manual diff review that rewrote every mechanically-mangled sentence into plain English and re-shortened any docstring/comment block still over the purge_bar's 6-line/5-line caps"
    - "The mechanical script never touches leading indentation and only cleans punctuation artifacts (stray parens, doubled slashes, dangling commas) on a line where it actually removed a match, so a real function call's own '()' is never mistaken for a stripped ID's empty parenthetical"
    - "Every module docstring in the family was rewritten from a multi-paragraph migration-chain narrative (30-70 lines, restating check-by-check history) to a single what-this-module-tests-plus-non-obvious-setup paragraph pair, at or under the 6-line cap"
    - "Two references to functions deleted in 35-13 (health_severity(), anomaly_active()) were found in comments still describing them as live and rewritten to describe the current code path instead, per the deleted-function-mention rule"

key-files:
  created: []
  modified:
    - companion/test_status_pages_01.py
    - companion/test_status_pages_02.py
    - companion/test_status_pages_03.py
    - companion/test_status_pages_04.py
    - companion/test_status_pages_05.py
    - companion/test_status_pages_05b.py
    - companion/test_status_pages_06.py
    - companion/test_status_pages_07.py
    - companion/test_status_pages_helpers.py
    - companion/test_view_pages_01.py
    - companion/test_view_pages_02.py
    - companion/test_view_pages_03.py
    - companion/test_view_pages_04.py
    - companion/test_view_pages_helpers.py

key-decisions:
  - "Committed per file (or small group) as each was finished — 11 commits instead of the plan's 2 tasks — after a mid-plan rate-limit interruption; smaller commits meant the interruption lost only in-progress work on one file, not the whole family."
  - "Ownership followed the plan's own scope note (glob `git ls-files 'companion/test_status_pages*.py' 'companion/test_view_pages*.py'`), which already matched files_modified exactly (14 files) — no drift to reconcile, unlike 35-14's browser family."
  - "test_view_pages_helpers.py had 0 guard hits already; only its module docstring's stray plan-chain reference was trimmed. Its comment ratio (39.1% after, down from 42.6%) stays above the ~35% review-trigger guideline because it is a 115-line file of eight short helper functions, each needing a one-paragraph why-docstring (e.g. why strip_js_line_and_block_comments() exists instead of companion_markup's stricter stripper) — there is no narration left to cut without dropping a load-bearing behavioural contract."

requirements-completed: []

duration: ~4h
completed: "2026-09-25"
---

# Phase 35 Plan 15: status_pages + view_pages test family comment purge Summary

**Purged plan/ticket/decision-ID history from all 14 `companion/test_status_pages*.py` and `test_view_pages*.py` files (15.9k lines), cutting history-check hits from 921 to 0 and comment lines from 3850 to 3223 (16%), with same-code proving the code itself is byte-for-byte unchanged and all 670 tests still passing.**

## Performance

- **Duration:** ~4h (interrupted once by an API rate limit mid-plan; resumed from the last completed file)
- **Completed:** 2026-09-25T20:21:00Z
- **Tasks:** 2 planned (status_pages family, view_pages family), executed as 11 per-file/per-group commits (see Task Commits)
- **Files modified:** 14

## Accomplishments

- Purged `test_status_pages_01.py` through `_07.py` (including `_05b.py`) and `test_status_pages_helpers.py` — the full status_pages family, 484 tests — to 0 history-check hits each.
- Purged `test_view_pages_01.py` through `_04.py` and `test_view_pages_helpers.py` — the full view_pages family, 186 tests — to 0 history-check hits each.
- Removed two stale references to functions deleted in 35-13 (`health_severity()`, `anomaly_active()`) found in comments still describing them as callable; rewrote each to describe the current code path (`health_page.safe_health_state()`) instead.
- Rewrote every module docstring in the family (14 of them) from a multi-paragraph "Part NN of the migration chain, check() calls #X-#Y..." narrative to a concise what/why paragraph pair at or under the purge_bar's 6-line cap.
- Built and iterated a scratch mechanical-purge script (`/tmp/.../purge.py`, not committed) that strips every `check_comment_history.py` pattern plus `quick task NNNNNN-xxx`/`rubric X` phrases from flagged lines only, preserving indentation and never touching a genuine `func()` call's parentheses — then hand-reviewed every diff to restore plain English where the mechanical pass left a dangling fragment (`"(Task 2, D-15)"` -> stripped; `"(demoted from error, D-05)"` -> `"(demoted from error)"`).
- Ran `same-code --base 8a8b8b4` on every file individually and on the full 14-file family together: exit 0, no `--allow`, on every run.
- Confirmed the collected test count is unchanged: 484 for status_pages (matching the plan's own recorded baseline) and 186 for view_pages (matching), 670 combined, both via `pytest --collect-only -q`.
- Ran `pytest companion/test_status_pages*.py companion/test_view_pages*.py -q -n auto`: 670 passed, 0 skipped, 0 failed.
- Ran `ruff check` on the full 14-file set: clean.

## Task Commits

Executed as eleven commits, one per file or small natural file group, rather than the plan's two large tasks (see Decisions Made — split for interruption resilience):

1. **status_pages_01, 02, 03** - `d08bb1c` (test)
2. **status_pages_04 + helpers** - `451ce96` (test)
3. **status_pages_05** - `243c912` (test)
4. **status_pages_05b** - `6860f0e` (test)
5. **status_pages_06** - `768eb85` (test)
6. **status_pages_07** - `abe1a05` (test)
7. **view_pages_01** - `51f7593` (test)
8. **view_pages_02** - `87ce9ba` (test)
9. **view_pages_03** - `eda7ed9` (test)
10. **view_pages_04** - `e5c4b1e` (test)
11. **test_view_pages_helpers** - `a642d89` (test)

**Plan metadata:** this commit (docs: complete plan)

## Per-File Ratios (before -> after)

Measured with `server/.venv/bin/python scripts/check_comment_history.py ratio` at group base `8a8b8b4` and again after all eleven commits.

| File | Lines before | Comment lines before | Ratio before | Comment lines after | Ratio after | Hits before -> after |
|---|---:|---:|---:|---:|---:|---:|
| companion/test_status_pages_01.py | 949 | 233 | 24.6% | 182 | 20.3% | 53 -> 0 |
| companion/test_status_pages_02.py | 1726 | 455 | 26.4% | 388 | 23.4% | 124 -> 0 |
| companion/test_status_pages_03.py | 1836 | 463 | 25.2% | 371 | 21.3% | 139 -> 0 |
| companion/test_status_pages_04.py | 1357 | 240 | 17.7% | 168 | 13.1% | 6 -> 0 |
| companion/test_status_pages_05.py | 797 | 225 | 28.2% | 167 | 22.6% | 77 -> 0 |
| companion/test_status_pages_05b.py | 803 | 207 | 25.8% | 152 | 20.3% | 31 -> 0 |
| companion/test_status_pages_06.py | 1540 | 418 | 27.1% | 357 | 24.1% | 117 -> 0 |
| companion/test_status_pages_07.py | 1406 | 398 | 28.3% | 338 | 25.1% | 74 -> 0 |
| companion/test_status_pages_helpers.py | 179 | 56 | 31.3% | 43 | 25.9% | 1 -> 0 |
| companion/test_view_pages_01.py | 637 | 99 | 15.5% | 92 | 14.6% | 44 -> 0 |
| companion/test_view_pages_02.py | 1431 | 322 | 22.5% | 292 | 20.8% | 121 -> 0 |
| companion/test_view_pages_03.py | 1464 | 211 | 14.4% | 192 | 13.3% | 74 -> 0 |
| companion/test_view_pages_04.py | 1699 | 471 | 27.7% | 436 | 26.2% | 60 -> 0 |
| companion/test_view_pages_helpers.py | 122 | 52 | 42.6% | 45 | 39.1% | 0 -> 0 |
| **Family total** | **15946** | **3850** | **24.1%** | **3223** | **21.0%** | **921 -> 0** |

The family total's "before" figures (14 files, 15946 lines, 921 history hits) match the plan's own scope description (`~15.9k lines, 24% comments, 921 history hits`) exactly.

### Files still above the ~20%-per-file guideline

`test_status_pages_02.py` through `_07.py`, `test_status_pages_helpers.py`, `test_view_pages_02.py` and `test_view_pages_04.py` sit above the ~20% per-file target the purge_bar states as "where possible." These are the dense CSS/JS-contract and multi-branch-behaviour test files in the family (declaration-by-declaration stylesheet assertions, per-language render sweeps, corroboration/anomaly state matrices), where most of the surviving comments are genuine why-content — root-safety notes (`tmp_path` vs a root-owned path), paint-order/geometry rationale, or a one-sentence explanation of why a fixture value was chosen — that the purge_bar's own "keep" list protects. `test_view_pages_helpers.py` (39.1%) is the extreme case: an eight-function, 115-line helper module where the ratio is inherent to the file's shape (short bodies, one why-paragraph each), not unpurged history; see key-decisions for detail.

### Purge Bar Exceptions (docstrings/blocks over the 6-line/5-line cap)

None retained over cap. Every module docstring in the family was rewritten to at or under 6 lines; every multi-paragraph comment block that needed to stay long enough to carry a real why (e.g. the root-unsafe degrade-safely rationale in `test_status_pages_01.py`, the tab-bar pill audit-measurement derivation in `test_status_pages_07.py`) was condensed to fit within the 5-line cap rather than granted an exception.

## Files Created/Modified

- `companion/test_status_pages_01.py` through `_07.py` (including `_05b.py`) — the status_pages test family; comments purged, code unchanged.
- `companion/test_status_pages_helpers.py` — shared fixture-seeding/formatting helpers for the status_pages family; comments purged, code unchanged.
- `companion/test_view_pages_01.py` through `_04.py` — the view_pages test family; comments purged, code unchanged.
- `companion/test_view_pages_helpers.py` — shared seeding/render helpers for the view_pages family; module docstring trimmed, code unchanged.

## Decisions Made

See `key-decisions` in the frontmatter above. In short: (1) eleven commits instead of the plan's two, split per file/small-group so a mid-plan rate-limit interruption (which occurred once) lost only in-progress work on one file rather than the whole family; (2) file ownership matched the plan's own scope glob exactly, no drift to reconcile; (3) `test_view_pages_helpers.py`'s comment ratio stays above the review-trigger guideline for structural reasons (many short functions, each needing its own why-paragraph), not unpurged history — it already had 0 guard hits before this plan touched it.

## Deviations from Plan

None beyond the commit-granularity change above (not a deviation rule — an execution-continuity adjustment requested by the orchestrator mid-plan after an interruption). No Rule 1-4 auto-fixes were needed: the purge is comment/docstring-only, and every file's code was already correct.

## Issues Encountered

- Mid-plan, the session was interrupted by an API rate limit after committing `status_pages_01-03`, `04+helpers`, `05`, and `05b` (four commits). Resumed from the coordinator's status report, which correctly identified the last-committed state; verified `same-code`/`check` still passed for the four already-committed files before continuing to `06`.
- An early version of the scratch mechanical-purge script had a bug: its "collapse an emptied `()`" cleanup regex also matched a genuine, pre-existing empty function call like `` `check()` `` inside prose, turning it into `` `check` `` (missing parens). Fixed by requiring at least one whitespace/separator character between the parens before collapsing, and by never touching a line the script didn't actually modify.

## User Setup Required

None - no external service configuration required.

## Verification Results

- **`same-code --base 8a8b8b4`, per file and as a 14-file set:** exit 0, no `--allow`, in every case.
- **`check --paths`, per file and as a 14-file set:** 0 history hits, exit 0, in every case.
- **`pytest --collect-only -q`:** 484 tests for the status_pages family, 186 for view_pages — both matching the plan's own recorded baselines.
- **`pytest companion/test_status_pages*.py companion/test_view_pages*.py -q -n auto`:** 670 passed, 0 skipped, 0 failed.
- **`ruff check` on the 14-file set:** "All checks passed!"
- **TDD gate compliance:** not applicable — this plan's tasks are `type="auto"`, not `tdd="true"`; no RED/GREEN/REFACTOR gate sequence is required.

## Next Phase Readiness

The status_pages and view_pages test families (group 5's second- and third-largest slices) are purged, same-code-proven and fully green. Group 5 (companion tests + test-support) is not yet closed — `companion/test_suite_guards.py` and the rest of group 5's non-status/view/browser files remain for sibling plans before 35-17 can close the group, append its `35-COMMENT-RATIO.md` section, and remove the group-5 paths from `scripts/comment-history-pending.txt`. Neither of those group-close artifacts was touched by this plan, per the orchestrator's own instruction that 35-17 owns them. HYG-01 remains open in `REQUIREMENTS.md`, correctly, since it spans groups not yet fully closed.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `companion/test_status_pages_01.py` — FOUND
- `companion/test_status_pages_02.py` — FOUND
- `companion/test_status_pages_03.py` — FOUND
- `companion/test_status_pages_04.py` — FOUND
- `companion/test_status_pages_05.py` — FOUND
- `companion/test_status_pages_05b.py` — FOUND
- `companion/test_status_pages_06.py` — FOUND
- `companion/test_status_pages_07.py` — FOUND
- `companion/test_status_pages_helpers.py` — FOUND
- `companion/test_view_pages_01.py` — FOUND
- `companion/test_view_pages_02.py` — FOUND
- `companion/test_view_pages_03.py` — FOUND
- `companion/test_view_pages_04.py` — FOUND
- `companion/test_view_pages_helpers.py` — FOUND
- Commit `d08bb1c` (status_pages_01-03) — FOUND
- Commit `451ce96` (status_pages_04 + helpers) — FOUND
- Commit `243c912` (status_pages_05) — FOUND
- Commit `6860f0e` (status_pages_05b) — FOUND
- Commit `768eb85` (status_pages_06) — FOUND
- Commit `abe1a05` (status_pages_07) — FOUND
- Commit `51f7593` (view_pages_01) — FOUND
- Commit `87ce9ba` (view_pages_02) — FOUND
- Commit `eda7ed9` (view_pages_03) — FOUND
- Commit `e5c4b1e` (view_pages_04) — FOUND
- Commit `a642d89` (test_view_pages_helpers) — FOUND
