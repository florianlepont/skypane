---
phase: 67-project-and-code-optimisation
plan: 11
subsystem: docs
tags: [docs, owner-decisions, dependency-review]
requires: ["67-05"]
provides:
  - corrected README, server README, CONTRIBUTING and deploy provider note
  - 67-OWNER-DECISIONS.md (branches, planning-note candidates, decisions, dependency review)
affects: [server/README.md, README.md, CONTRIBUTING.md, deploy/README.md]
key-files:
  modified: [server/README.md, README.md, CONTRIBUTING.md, deploy/README.md]
  created: [.planning/workstreams/v1-2/phases/67-project-and-code-optimisation/67-OWNER-DECISIONS.md]
decisions:
  - D-12 and D-13 owner answers recorded as answered in section 0 of the decisions document
metrics:
  tasks: 2
  completed: 2026-11-27
---

# Phase 67 Plan 11: Docs drift and owner decisions Summary

Docs now match the repository (pillow 13.0.0 via requirements.txt, no Phase 2 title, real Python versions, OVH as the deploy target), and one owner decision document lists 40 non-main branches, planning-note candidates with reference counts, open decisions with defaults, and a read-only dependency review. Nothing deleted.

## Tasks

1. Docs corrections (commit 33a9c990): server/README.md retitled, version statement deferred to requirements.txt, pointer to ARCHITECTURE.md, stale plan references and LAN address removed; deploy/README.md provider note rewritten (OVH is the statement, earlier provider is history); CONTRIBUTING.md gate list adds mypy, function-size, comment-history and the small-change rule; README.md Python statement corrected.
2. 67-OWNER-DECISIONS.md (commit 914ef752).

## Findings

- Branches: 40 non-main (plan said 39), 0 open PRs; 4 marked likely live.
- Dependency review: 6 runtime and 29 total pinned packages, all hash-locked; OSV lookup found no known advisory for any of them. pip-audit not installed.
- Pre-existing: `pyproject.toml` comment says the local venv is 3.11 (listed as open decision 9, not edited: not a docs file). README says the repository is private (decision 8).

## Deviations from Plan

None in substance. The branch count is 40, not 39. The local worktree has no venv, so tools ran from the main checkout's virtualenv.

## Verification

deploy/tests/test_docs.py and scripts/test_exposure_scan.py pass (50 tests); exposure scan clean for the changed files; comment-history check clean. requirements files unchanged.

## Self-Check: PASSED
