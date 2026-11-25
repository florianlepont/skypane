---
phase: 70-private-repository-and-ci
plan: 08
subsystem: security-hygiene
tags: [exposure-scan, inventory, PRV-03]
requires: []
provides:
  - scripts/exposure_scan.py value-free tree and history scan
  - 70-INVENTORY.md draft with owner decision table
affects: [70-10]
tech-stack:
  added: []
  patterns: [stdlib CLI with subcommands, tests on throwaway git repositories]
key-files:
  created:
    - scripts/exposure_scan.py
    - scripts/test_exposure_scan.py
    - .planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-INVENTORY.md
metrics:
  completed: 2026-11-25
---

# Phase 70 Plan 08: Exposure scan and inventory Summary

Stdlib exposure scan (tree and history, nine pattern classes, rows carry type, file, commit and count only) with 27 tests, plus a draft inventory of what has been public with a blank owner decision table. Status: Tasks 1 and 2 complete; Task 3 (owner mirror scan and decisions) is an open checkpoint, not performed.

## Commits

- `cbbf767` feat(70-08): exposure scan and tests
- `77a9ab4` docs(70-08) draft inventory

## Results

- `pytest scripts/test_exposure_scan.py`: 27 passed. Ruff clean. `check_comment_history.py check` exit 0. No `shell=True`; the PEM marker is assembled from fragments in the tests.
- Sandbox scan (shallow clone, 101 commits visible): tree 145 rows (assigned-secret 15, bearer-literal 1, email 105, public IPv4 24); no PEM, AWS, GitHub, Slack or sk- hits. History rows equal the tree plus a few removed addresses; all secret-class rows sit in commit `7611000`, the shallow boundary.

## Deviations from Plan

- The repo venv `server/.venv` does not exist in the worktree; the main checkout's venv (read only use of its python and ruff) ran the tests.
- Branch name follows the orchestrator's instruction (`phase-70-08-exposure-inventory`), not the `worktree-agent-*` pattern.
- Email validator also drops `noreply`/`no-reply` local parts and asset-style names such as `icon@2x.png`; not in the plan, reduces noise.
- mypy list in `pyproject.toml` not extended: the scripts are untyped and not in the typed core.

## Open checkpoint (owner)

Task 3: mirror scan on the owner's machine, per-row decisions, any rotation. The inventory's "decided by the owner" and "Follow-ups" content are not yet filled; the plan's Task 3 acceptance (`decided by the owner` grep) will not pass until then. No value was printed, copied or stored.
