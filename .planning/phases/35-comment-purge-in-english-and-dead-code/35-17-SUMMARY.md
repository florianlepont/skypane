---
phase: 35-comment-purge-in-english-and-dead-code
plan: 17
subsystem: comment-hygiene
tags: [comment-hygiene, hyg-01, companion, test-support, group-close]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 14
    provides: "companion/test_browser_*.py family purged, same-code-proven, 0 hits (9 files, 636 hits)"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 15
    provides: "companion/test_status_pages_*.py and test_view_pages_*.py families purged, same-code-proven, 0 hits (14 files, 921 hits)"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 16
    provides: "every remaining companion/test_*.py + companion/conftest.py + test-support/*.py purged, same-code-proven, 0 hits (29 files, 1048 hits); flagged the two --allow files needed for the group-level same-code sweep"
provides:
  - "Group 5 (companion tests + test-support, 52 files) is closed: group-level same-code proves the AST unchanged against base 8a8b8b4 for every changed file (with the two documented --allow flags for test_companion_app_02.py/test_suite_guards.py module docstrings), check reports 0 history hits across all 52 files, every group-5 path is removed from scripts/comment-history-pending.txt so the argument-less CLI check now enforces them, and the group's before/after ratios (25.7% -> 20.7%, 2605 -> 0 history hits) are recorded in 35-COMMENT-RATIO.md"
  - "origin/main (Phase 35 groups 2-4, Phase 34 firmware completion, Phase 36 planning, Phase 42 roadmap entry) merged into claude/plan-phase-35 with a merge commit; confirmed the merge touches no companion/ or test-support/ file, so group 5's same-code base (8a8b8b4) is still valid post-merge"
  - "Full suite (2691 passed, 5 skipped, SKYPANE_REQUIRE_BROWSER=1, browser tests actually executed not skipped) and ruff are green after the merge"
affects: [35-18, 35-21]

tech-stack:
  added: []
  patterns:
    - "Group-close proof for a group whose files were already purged file-by-file across sibling plans (14/15/16): re-run same-code/check at the GROUP level (all 47 files changed since base, in one command) rather than trusting the per-file proofs individually, because a group-level run is the only thing that catches a file one sibling plan's own file-scoped same-code run missed listing."
    - "When same-code's own base commit sits behind origin/main by several merged PRs, diff origin/main against that base scoped to the group's own paths first (`git diff <base> origin/main --stat -- <group-paths>`) before merging — an empty diff proves the merge cannot invalidate the group's already-completed same-code proof, so the merge can be done first (picking up main's STATE.md/ROADMAP.md drift) without re-doing any file's purge."

key-files:
  created: []
  modified:
    - scripts/comment-history-pending.txt
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md
    - .planning/STATE.md

key-decisions:
  - "Merged origin/main before running the group-5 same-code proof, not after, per the orchestrator's own instruction — confirmed first with `git diff 8a8b8b4 origin/main --stat -- companion test-support` (empty output) that main's four merged PRs since base (Phase 35 groups 2-4, the Phase 34 firmware NVS fix, Phase 36 planning, the Phase 42 roadmap entry) touch no companion or test-support file, so the group's same-code base (8a8b8b4, literal, matching the group base the three source plans already proved against) needed no adjustment after the merge."
  - "STATE.md's merge conflict (three separate hunks: frontmatter progress counters, Current Position, Session Continuity) was resolved by combining both sides' information rather than picking one, per the orchestrator's explicit instruction to never drop the other side's entries: kept this branch's more-advanced plan position (Plan: 17 of 22, not main's stale 14 of 22) and its later last_updated timestamp, added main's new Phase 34-complete status line (not present on this branch) and its Phase 42 context-gathering note into stopped_at/Session Continuity prose, and merged the frontmatter progress counters to the combination that is internally consistent with both sides' own edits (total_phases/total_plans from main, which added Phase 42 to the roadmap; completed_plans from this branch, which is 2 higher than main's snapshot because it completed 35-15 and 35-16 after main's own last update). ROADMAP.md's conflict-free auto-merge was verified by grep for leftover conflict markers (none)."
  - "The group-level same-code run needs exactly the same two --allow flags 35-16 already documented and flagged for this plan (test_companion_app_02.py, test_suite_guards.py) — both for a module-docstring-only false positive in same-code's own `keep_module_doc` heuristic (the literal substring `__doc__` appearing anywhere in the file, regardless of whether it's the module docstring's own content) — confirmed unchanged at group-close time: the aggregate same-code command over all 47 changed files exits 0 with only these two flags, no others."
  - "The 35-COMMENT-RATIO.md group-5 section uses a per-family prose summary for the 30 files still above its own ~20% per-file guideline (group 5's plans used 20%, stricter than groups 2-4's 35%, because test files have proportionally less code to dilute a why-comment against), rather than one table row with justification per file as groups 2-3-4 did — with 30 of 52 files above threshold (vs. groups 2-4's single-digit counts), a full per-file table would mostly repeat the same handful of reasons (dense multi-branch test assertions, small fixture-dense helper modules) already stated once per family in the three source plans' own SUMMARYs; the section cites and condenses those rather than re-deriving new justification text."
  - "Did not mark HYG-01 complete in REQUIREMENTS.md, and did not push or open the group-5 PR — both explicitly reserved for the orchestrator per this plan's own dispatch instructions. HYG-01 remains 'In progress (server group done)' in REQUIREMENTS.md; that line is stale (three more groups are now closed) but updating it is out of this plan's scope by explicit instruction."

requirements-completed: []

duration: ~10min
completed: "2026-09-25"
---

# Phase 35 Plan 17: Close group 5 (companion tests + test-support) Summary

**Group 5 (companion/test_*.py, companion/conftest.py, test-support/*.py — 52 files) is closed: group-level same-code proves the AST unchanged against base 8a8b8b4 for all 47 files 35-14/15/16 edited (2 documented --allow flags for a module-docstring `__doc__`-substring false positive), check reports 0 hits across all 52 files, every group-5 path is removed from the CLI's pending list, the group's ratios (25.7% -> 20.7%, 2605 -> 0 hits) are recorded, and the full suite (2691 passed, browser tests actually run) plus ruff are green after merging origin/main.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-09-25T21:22:05Z
- **Tasks:** 2 planned, both executed
- **Files modified:** 3 (scripts/comment-history-pending.txt, 35-COMMENT-RATIO.md, STATE.md) plus the merge commit's own files (none touched by hand beyond conflict resolution)

## Accomplishments

- Fetched and merged `origin/main` into `claude/plan-phase-35` (merge commit `de2e8b1`), bringing in Phase 35 groups 2-4 (server/, stub-server/, companion production), the Phase 34 firmware NVS fix and hardware session, Phase 36 planning, and the Phase 42 roadmap entry — confirmed beforehand with `git diff 8a8b8b4 origin/main --stat -- companion test-support` (empty) that none of it touches a companion test or test-support file, so group 5's same-code base needed no adjustment.
- Resolved STATE.md's three-hunk merge conflict by combining both sides (see key-decisions); confirmed no conflict markers remain in STATE.md or ROADMAP.md.
- Ran the group-level same-code proof over all 47 files changed since base `8a8b8b4`: `same-code --base 8a8b8b4 --allow companion/test_companion_app_02.py --allow companion/test_suite_guards.py <47 files>` exits 0 — the same two `--allow` flags 35-16 flagged in advance for exactly this group-level sweep, no others needed.
- Ran `check --paths` over all 52 group-5 files (including the 5 that 35-16 found already clean and left untouched): 0 history hits.
- Measured group-5's before/after ratios with the `ratio` tool against `35-BASELINE/ratio-before.tsv` and appended a `## Group 5` section to `35-COMMENT-RATIO.md`: 52 files, 50312 lines before / 47119 after, 25.7% -> 20.7% comment ratio, 2605 -> 0 history hits (matching the sum of 35-14/15/16's own family totals: 636 + 921 + 1048 = 2605).
- Removed all 46 group-5 lines (`companion/test_`, `companion/conftest`, `test-support/`) from `scripts/comment-history-pending.txt`; the argument-less `check` (no `--paths`) now exits 0, meaning group 5 is enforced by the CI guard going forward.
- Ran the full suite with `SKYPANE_REQUIRE_BROWSER=1`: 2691 passed, 5 skipped (expected root-permission skips), 0 failed, 259.17s, coverage 93.22% (floor 93%) — browser tests actually executed against the Playwright headless shell at `/opt/pw-browsers`, not skipped.
- Ran `server/.venv/bin/ruff check .`: all checks passed.
- Re-ran `check` (no args) after the full suite run: still 0 hits, working tree unchanged by the test run.

## Task Commits

1. **Task 1: Group-5 proof and ratchet** - `09a08d5` (docs) — same-code/check proof, `35-COMMENT-RATIO.md` group-5 section, `scripts/comment-history-pending.txt` ratchet. Preceded by merge commit `de2e8b1` (merges `origin/main`, resolves STATE.md conflicts).
2. **Task 2: Full proof after merge** - verification-only, no additional file changes (full suite + ruff + guard check all pass against the state Task 1's commit already produced); no separate commit needed beyond this plan's own metadata commit.

**Plan metadata:** this commit (docs: complete plan)

## Files Created/Modified

- `scripts/comment-history-pending.txt` - removed all 46 `companion/test_*`, `companion/conftest.py` and `test-support/*` lines; the guard's argument-less `check` now covers group 5.
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` - appended the `## Group 5 — companion tests + test-support` section (per-file table, group total, above-guideline justifications, same-code/check evidence).
- `.planning/STATE.md` - merge-conflict resolution combining this branch's plan position with main's Phase 34-complete status and Phase 42 context note (see key-decisions); further updated below by the standard state-update commands.

## Decisions Made

See `key-decisions` in the frontmatter above. In short: (1) merged `origin/main` before the group-5 proof, verified safe by an empty pathspec-scoped diff; (2) STATE.md's conflict resolved by combining both sides' information, never dropping either; (3) the group-level same-code run needs exactly the same two `--allow` flags 35-16 already flagged, confirmed unchanged; (4) the ratio table's above-guideline section uses condensed per-family prose rather than 30 individual justification rows, citing the three source plans; (5) HYG-01 was deliberately left unmarked and the PR deliberately not opened, both reserved for the orchestrator.

## Deviations from Plan

None beyond the STATE.md merge-conflict resolution described above, which is inherent to the orchestrator's own instruction to merge `origin/main` (not a Rule 1-4 deviation from the plan's own tasks — the plan's task list and verification commands were followed as written, with the merge ordered before Task 1's proof per the orchestrator's notes rather than as `close_procedure`'s own step 6, also per those notes).

## Issues Encountered

None. The merge's only conflict was in STATE.md (three hunks, all frontmatter/position/session-continuity metadata, no code or test file involved); ROADMAP.md auto-merged cleanly with no conflict markers.

## User Setup Required

None - no external service configuration required.

## Verification Results

- **`git diff 8a8b8b4 origin/main --stat -- companion test-support`:** empty — confirmed the merge touches no group-5 file before merging.
- **Merge commit `de2e8b1`:** created via `git merge origin/main --no-edit`; STATE.md's three-hunk conflict resolved by hand (both sides' information kept, see key-decisions); no conflict markers remain in STATE.md or ROADMAP.md (`grep -n '^<<<<<<<\|^=======\|^>>>>>>>'` empty on both files).
- **`same-code --base 8a8b8b4 --allow companion/test_companion_app_02.py --allow companion/test_suite_guards.py <47 changed files>`:** exit 0.
- **`check --paths <52 group-5 files>`:** 0 history hits, exit 0.
- **`grep -cE '^(companion/test_|companion/conftest|test-support/)' scripts/comment-history-pending.txt`:** 0 (post-edit).
- **`check` (no args, full pending-list sweep):** exit 0.
- **`SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`:** 2691 passed, 5 skipped (expected root-permission skips), 0 failed, 259.17s, coverage 93.22% (floor 93.0% reached), exit 0. Browser tests confirmed actually executed (not skipped) against the Playwright headless shell at `/opt/pw-browsers`.
- **`server/.venv/bin/ruff check .`:** "All checks passed!"
- **`check` (no args) re-run after the full suite:** still exit 0; `git status --short` confirmed the test run left the working tree unchanged.
- **TDD gate compliance:** not applicable — this plan's tasks are `type="auto"`, not `tdd="true"`; no RED/GREEN/REFACTOR gate sequence is required.

## Next Phase Readiness

Group 5 is fully closed and CI-enforced. Per this plan's own dispatch instructions, the group-5 branch is not pushed and no PR is opened here — that, along with marking HYG-01's progress in `REQUIREMENTS.md`, is left to the orchestrator. `origin/main` is now merged into `claude/plan-phase-35`, so the branch carries Phase 35 groups 2-5 together with Phase 34's completion and Phase 36/42 planning context. Remaining Phase 35 work (groups 6+, per `ROADMAP.md`'s wave plan) can build on this branch's now-current base.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*
