---
phase: 67-project-and-code-optimisation
plan: 16
subsystem: quality-gates
tags: [after-record, coverage-ratchet]
requirements: [QUAL-01]
key-files:
  created:
    - .planning/workstreams/v1-2/phases/67-project-and-code-optimisation/67-AFTER.md
  modified:
    - pyproject.toml
metrics:
  completed: 2026-11-28
  tasks: 2
---

# Phase 67 Plan 16: After record and coverage ratchet Summary

`67-AFTER.md` records the measured after state next to the baseline (same commands, 17,598 to 17,717 collected tests, 90 removed ids listed), and `fail_under` goes from 93 to 96 from a real main CI total of 96.20 %.

## Commits (branch `worktree-agent-afeba99e1961a9c07`, based on origin/main e44c55a9)

- 86dccfa6 docs: the after record
- 7af469ac test: coverage floor 93 to 96
- a third small docs commit adds the local informational coverage figure to the after record and this summary

## Coverage value and source

CI run 46180225838 (push to `main`, commit a51c2457, the last commit touching code; e44c55a9 changes only two planning documents), job "Lint, test, coverage, attribution", Python 3.14.10, all eight shards including the six browser shards: `TOTAL 30083 1143 96%` = 96.20 %; 17,717 executed, 0 skipped. Read through the public GitHub REST API (job log), because the GitHub MCP tools were not available to this agent and the `gh` token in the environment is invalid. The previous green main run (46175941432, ed9d0ddc) gave 30083 / 1141, 96.21 %. Floor = 96, no margin, never above the measured value.

Local value (informational, not used): core group with coverage, Python 3.13, no browser tests: `TOTAL 30235 1223 96%` = 95.95 %.

## Not changed on purpose

- `MIN_EXECUTED` stays 17,591: the plan lists only `pyproject.toml`; CI executes 17,717, so 17,717 would be safe as a follow-up.
- No test pins the floor and no document states it as a number.

## Checks run

ruff, mypy (57 files), `check_comment_history.py check`, `check_spdx_headers.py check`, `check_function_size.py check --max 80 server stub-server companion deploy scripts` (3,401 functions, none over 80), exposure scan (148 lines, same as before; pre-existing placeholders), `test-support/test_ci_gates.py` (14 passed), `deploy/tests/test_ci_runner.py` and `test_docs.py` (36 passed), freeze and golden check (114 passed), core group (12,968 passed, 7 skipped).

## Deviations

- The after record is a document-only change with the ratchet figures inside it; the floor change is a separate commit as asked.
- Commits are on the worktree branch (the commit guard allows `worktree-agent-*` only), to be pushed as `phase-67-16-after`.
- Not verified: whether the new floor passes on `main`; only the first push run after the merge shows it. The e44c55a9 CI run had not finished when read.

## Known Stubs

None.

## Self-Check: PASSED
