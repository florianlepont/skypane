---
phase: 35-comment-purge-in-english-and-dead-code
plan: 06
subsystem: server-comment-hygiene
tags: [comment-hygiene, ci-guard, ratchet, server, stub-server-drift-guard]

requires:
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 02
    provides: "server/plane/{render,illustrations,colour_rules,dither,runway_config}.py purged"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 03
    provides: "server/plane/{calendar_rules,enrich,detect,manual_resolutions}.py purged"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 04
    provides: "server/poll_loop.py, device_config.py, history_db.py, wake.py, notify.py, panel_format.py, panel_preview.py, requirements(-dev).in purged"
  - phase: 35-comment-purge-in-english-and-dead-code
    plan: 05
    provides: "every server/test_*.py purged"
provides:
  - "server/ fully purged of plan/ticket/decision/review/phase-ID history (0 hits across 36 files) and CI-enforced (removed from scripts/comment-history-pending.txt)"
  - "35-COMMENT-RATIO.md server section with per-file before/after ratios, group total, and justifications for files above the 35% guideline"
  - "group 2 branch merged with origin/main and verified green"
affects: [35-07, 35-08, 35-09]

tech-stack:
  added: []
  patterns:
    - "Group-close plans re-verify same-code/check after merging main, not just before, in case the merge reintroduces history or code drift"
    - "A vendored byte-for-byte duplicate function (stub-server/byos_server.py mirroring server/device_config.py, enforced by a drift-guard test) must be updated in lockstep with any purge of its origin — the purge plan that touches the origin file can miss this because the drift-guard test lives outside the file it edits and outside pytest's default `server` scope"

key-files:
  created:
    - .planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md
  modified:
    - scripts/comment-history-pending.txt
    - stub-server/byos_server.py

key-decisions:
  - "Used the group base ee2737a literally (as instructed) rather than recomputing merge-base at Task-1 time; confirmed it already equalled `git merge-base HEAD origin/main`, so no divergence to reconcile."
  - "Allow list for the group-level same-code proof: server/plane/render.py, server/plane/illustrations.py, server/poll_loop.py, server/test_render.py, server/test_config_history.py, server/test_illustrations.py — one --allow per file, matching the precedents already established and verified in 35-02/35-04/35-05 (argparse description=__doc__ files, and 35-05's source-text-assertion replacements). The plan's own Task 1 verify command only lists illustrations.py and is stale; ran the corrected command instead."
  - "Fixed a full-suite failure caused by 35-04's device_config.py docstring purge going out of sync with stub-server/byos_server.py's byte-for-byte vendored copy of seconds_until_quiet_hours_end(), which a dedicated drift-guard test enforces. Copied the new docstring into the vendored copy (function body was already identical, no logic change) rather than leaving stub-server/'s later purge plan to discover it, since it blocked this plan's own close_procedure step 5 (full suite must be green)."

requirements-completed: []

duration: ~20min
completed: "2026-09-25"
---

# Phase 35 Plan 06: Close group 2 (server/) Summary

Closed PR group 2: proved every changed `server/` file is code-unchanged against base `ee2737a` with only the six established runtime-`__doc__`/source-text-replacement files allowed to differ, confirmed `check` reports 0 history hits across all 36 scanned `server/` files, removed all 32 `server/` lines from `scripts/comment-history-pending.txt` (so CI now enforces `server/` directly), recorded the group's per-file and total comment-ratio deltas (37.2% -> 24.1%) in a new `35-COMMENT-RATIO.md`, fixed a full-suite regression the group's earlier purge work introduced in a vendored duplicate outside `server/`, and merged `origin/main` with the suite still green.

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-25T09:35Z
- **Completed:** 2026-09-25T09:44Z
- **Tasks:** 2 completed
- **Files modified:** 3 (`scripts/comment-history-pending.txt`, `35-COMMENT-RATIO.md` created, `stub-server/byos_server.py`)

## Accomplishments
- Group-level `same-code --base ee2737a` passes for all 32 changed `server/` files with a 6-file allow list, and `check --paths` reports 0 history hits across all 36 scanned `server/` files.
- `scripts/comment-history-pending.txt` shrunk from 211 to 179 lines (all `^server/` lines removed); `check` with no args stays green, so CI's guard now covers `server/` unconditionally.
- `35-COMMENT-RATIO.md` created with the group's full 36-file before/after table, a group-total row matching the baseline's group-2 row exactly (30940 -> 25606 lines, 37.2% -> 24.1%, 1689 -> 0 history hits), and justifications for the 11 files still above the ~35% review-trigger guideline.
- Merged `origin/main` (one commit ahead, docs-only, no `server/` touch) and re-verified same-code/check/full-suite/ruff green afterward.

## Task Commits

1. **Task 1: Group proof and ratchet for server/** - `881cc90` (docs)
2. **Task 2 (deviation, Rule 1): fix stub-server drift-guard regression** - `d334184` (fix)
3. **Task 2: Full proof, merge main** - `2348179` (merge commit, no separate proof commit needed — merge was clean, verification re-run produced no further file changes)

## Files Created/Modified
- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` - new file: group 2 (server/) per-file ratio table, group total, and above-35% justifications
- `scripts/comment-history-pending.txt` - removed all 32 `^server/` lines (211 -> 179 lines)
- `stub-server/byos_server.py` - `seconds_until_quiet_hours_end()` docstring re-synced to match `server/device_config.py`'s tightened text (function body unchanged; drift-guard test now passes)

## Decisions Made
- Used the literal group base `ee2737a` per the executor's instructions; confirmed it equals `git merge-base HEAD origin/main` at Task-1 time (no divergence).
- Ran the corrected same-code allow list (6 files, one `--allow` per file) rather than the plan's own stale Task 1 verify command, which predates 35-04's `poll_loop.py` and 35-05's three test-file allow requirements.
- Group total in `35-COMMENT-RATIO.md` reconciles exactly against `35-BASELINE/INDEX.md`'s group-2 row, confirming no file was missed or double-counted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] stub-server's vendored `seconds_until_quiet_hours_end()` docstring drifted from server/device_config.py after 35-04's purge**
- **Found during:** Task 2, running `./scripts/run-all-tests.sh` for the first time in this plan.
- **Issue:** `stub-server/test_poll_cycle.py::test_quiet_hours_helpers_drift_guard_matches_device_config` asserts `server/device_config.py`'s and `stub-server/byos_server.py`'s copies of `seconds_until_quiet_hours_end()` are byte-for-byte identical (a deliberate vendor-boundary duplication, per a comment at the top of the function in `byos_server.py`). 35-04 tightened `device_config.py`'s docstring as part of the comment purge but did not update the vendored copy — outside that plan's `server/`-only `files_modified` scope and outside pytest's default `server` test-collection root, so the drift wasn't caught until this plan ran the full multi-directory suite.
- **Fix:** Copied `device_config.py`'s new (purged) docstring verbatim into `stub-server/byos_server.py`'s copy of the function. The function body was already byte-identical; only the docstring text changed, so no logic changed on either side.
- **Files modified:** `stub-server/byos_server.py`
- **Commit:** `d334184`

---

**Total deviations:** 1 auto-fixed (1 bug, cross-file drift caused by a prior plan in this group)
**Impact on plan:** Required to satisfy this plan's own close_procedure step 5 (full suite must be green). No scope creep — the fix only restores byte-identical duplication the project's own drift-guard test already requires; `stub-server/` remains otherwise untouched (group 3, not yet purged).

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Verification Results

- **Group-level same-code:** `same-code --base ee2737a --allow server/plane/render.py --allow server/plane/illustrations.py --allow server/poll_loop.py --allow server/test_render.py --allow server/test_config_history.py --allow server/test_illustrations.py <32 changed files>` -> exit 0
- **Group check:** `check --paths $(git ls-files server/)` (124 files, 36 with comment-syntax support) -> 0 history hits
- **Pending list:** `grep -c '^server/' scripts/comment-history-pending.txt` -> 0; `check` (no args) -> exit 0
- **Ratio table:** `35-COMMENT-RATIO.md` server section — group total 30940 -> 25606 lines, 37.2% -> 24.1%, 1689 -> 0 history hits (matches `35-BASELINE/INDEX.md`'s group-2 row exactly)
- **Full suite (post-merge):** `./scripts/run-all-tests.sh` -> 2564 passed, 132 skipped (pre-existing Playwright-environment skips, unrelated to this plan), 0 failed
- **ruff:** `server/.venv/bin/ruff check .` -> "All checks passed!"
- **shellcheck:** not installed in this environment; per the plan's own instruction, CI is the gate for `deploy/*.sh`
- **Merge with origin/main:** `e8d293c` (docs-only, no `server/` touch) merged cleanly via `ort` strategy, no manual conflict resolution needed; same-code/check/full-suite/ruff all re-verified green afterward
- **PR:** not opened by this executor — per the orchestrator's instructions, this plan stayed on `claude/plan-phase-35` and did not push or open a PR; the orchestrator handles push/PR after this plan returns

## Next Phase Readiness
`server/` is fully purged, code-unchanged, and CI-enforced (0 pending-list lines, 0 history hits). The group's ratio evidence is recorded for the phase's closing report. Remaining pending-list groups (`stub-server/`, companion production/tests/JS/CSS, `deploy/`+`scripts/`+`.github/`+..., `firmware/`) are unaffected and untouched, aside from the one-function drift-guard fix in `stub-server/byos_server.py` needed to keep the full suite green — that file's own comment-history purge remains a later group's (group 3) job. HYG-01/HYG-03 in `REQUIREMENTS.md` intentionally left unmarked, per the executor's instructions, since they span groups not yet closed.

---
*Phase: 35-comment-purge-in-english-and-dead-code*
*Completed: 2026-09-25*

## Self-Check: PASSED

- `.planning/phases/35-comment-purge-in-english-and-dead-code/35-COMMENT-RATIO.md` — FOUND
- `scripts/comment-history-pending.txt` — FOUND
- `stub-server/byos_server.py` — FOUND
- Commit 881cc90 (Task 1: group proof and ratchet) — FOUND
- Commit d334184 (deviation fix: stub-server drift-guard resync) — FOUND
- Commit 2348179 (merge origin/main) — FOUND
