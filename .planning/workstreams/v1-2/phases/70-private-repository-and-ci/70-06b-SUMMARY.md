---
phase: 70-private-repository-and-ci
plan: 06b
subsystem: ci
tags: [ci, paths-filter, github-actions]
requires: [70-06]
provides:
  - workflow-level paths exclusion of 3D model files under hardware/cad
  - scripts/ci_path_filter.py (decide, measure)
affects: [70-10]
key-files:
  created:
    - scripts/ci_path_filter.py
    - scripts/test_ci_path_filter.py
    - deploy/tests/test_ci_paths.py
  modified:
    - .github/workflows/ci.yml
    - .github/workflows/deploy.yml
    - deploy/tests/test_ci_runner.py
    - deploy/tests/test_docs.py
    - deploy/README.md
    - CONTRIBUTING.md
    - .planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-MEASUREMENTS.md
decisions:
  - Exclusion by file type, not directory; no job-level change detection; gates untouched.
metrics:
  completed: 2026-11-26
---

# Phase 70 Plan 06b: CI path splitting Summary

Workflow-level `paths` exclusion of `.stl`, `.blend`, `.glb` and `.3mf` files under `hardware/cad` in both `push` and `pull_request`, with a stdlib matcher that reads the list from `ci.yml` and proof tests that fail if anything other than inert files could skip the suite.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 matcher (decide, measure) | e14ce260 | 27 tests, GitHub semantics (last match wins) |
| 2 ci.yml exclusions and proof tests | see git log (feat 70-06b paths filter) | 8 exclusion lines, test_ci_paths.py, runner test renamed and tightened |
| 3 docs and measurement | see git log (docs 70-06b) | README section, CONTRIBUTING, measurement section, `D-07 delivered:` line |

## Proof greps (task 2)

- `git ls-files hardware/cad`: 6 .stl, 2 .blend, 1 .glb, 1 .3mf, 1 .md. No code file.
- Reference grep over tracked .py/.sh/.yml/.yaml/.toml/.js/.json/.jsonl/.cfg/.ini (outside .claude, .planning) for `hardware/cad` in any spelling: hits only in this plan's own test files. Walk/glob grep over `hardware`: no hits.

## Measurement (last 100 first-parent commits, base 2188a9e1)

Would skip: 39 before, 51 after (12 skipped only because of this plan). Estimate about 4,300 billable minutes a month in a busy period; see 70-MEASUREMENTS.md for inputs and caveats.

## Deviations from Plan

None in scope. One test-structure choice: the matcher tests in task 1 append the model exclusions to the workflow list when absent, so task 1 commits green before ci.yml changes; the real list is asserted in task 2 tests.

`deploy/runner/README.md` and `COMPLIANCE.md` were grepped for "docs-only", "path" and "whole suite": no statement about path splitting, so not edited.

## Verification

- `pytest deploy scripts`: 498 passed, 1 skipped. The skip is pre-existing and environmental (`deploy/tests/test_cert_chain_check.py:164`: this sandbox's OpenSSL 3.0.13 cannot backdate a certificate); unrelated to this plan.
- ruff, comment-history guard, function-size gate (80) and `ci_shards.py check` (554 files, 5+2 shards) pass.
- `scripts/ci_gates.py`, `scripts/ci_shards.py`, `scripts/ci_shard_weights.json`, `pyproject.toml`: empty diff.
- `deploy.yml`: comment and input-description lines only.

## Not verified

- An actual GitHub run on a model-only commit (after merge, push one .stl and confirm no run starts).
- The full browser suite and the CI gates were not run locally; they run in CI because the change touches code.

## Self-Check: PASSED
