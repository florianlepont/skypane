---
phase: 67-project-and-code-optimisation
plan: 25
requirements: [QUAL-01]
completed: 2026-11-28
---

# Phase 67 Plan 25: SPDX headers Summary

`# SPDX-License-Identifier: AGPL-3.0-only` added to 906 tracked Python files by a stdlib gate/stamper (`scripts/check_spdx_headers.py`, check and write modes), with a CI lint step so a new file without an SPDX line fails.

## Commits (branch worktree-agent-a471e8546ddbbb19f, based on origin/main ed9d0ddc)

1. `2eb93a36` script, 23 tests (`test-support/test_check_spdx_headers.py`), CI step after the comment-history guard, shard weight entry, CONTRIBUTING line.
2. `e4173350` mechanical stamp: 906 files changed, 906 insertions, 0 deletions, no mode changes.

## Rules

- Header after a shebang and after a PEP 263 cookie (line 1 or 2), before docstring and `from __future__`; file's own line ending; BOM kept first; zero-byte file becomes header plus newline.
- Headed means an SPDX comment in the leading comment block (first 10 lines, before any statement); SPDX text inside a docstring does not count.
- Excluded: `firmware/` (Apache-2.0), `stub-server/byos_server.py` (Apache-2.0), `.planning/`, `.claude/`.

## Counts (910 tracked non-excluded files)

Already carrying an SPDX line (kept): 4 (all Apache-2.0): server/test_fault_screen_mask.py, server/test_updating_screen.py, server/test_updating_screen_mask.py, stub-server/fleet_cli.py. Stamped: 906 (plain 702, shebang 178, encoding cookie 25, empty 1; first statement a docstring in 898, other 7, empty 1; none start with `from __future__`).

## Verification

- AST identity (`ast.dump`) and module docstring identical for all 906 files; byte check: new file minus the header line equals the old file.
- `git diff --numstat`: 1 added, 0 deleted per file; compileall clean; ruff, mypy, function-size gate, comment-history guard, exposure scan (148 lines before and after) unchanged; gate exits 0 on the tree and a second write changes 0 files.
- Collected test ids identical apart from the 23 new tests; core group of the suite (run-all-tests.sh, SKYPANE_TEST_GROUP=core): 12968 passed, 7 skipped (root/openssl skips).
- No golden or snapshot hashes a .py file.

## Deviations

- Gate is wired in commit 1, so that commit alone fails the gate until commit 2 stamps the tree.
- Rule 1: first draft counted SPDX text inside a docstring as a header; fixed and tested before stamping.
