---
phase: 67
slug: project-and-code-optimisation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-27
---

# Phase 67 — Validation Strategy

Source of truth: the "Validation Architecture" section of `67-RESEARCH.md` (per-cleanup proof table). This file is the contract summary.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest + xdist + cov + pytest-socket; pytest-playwright for browser tests (CI only) |
| Config file | `pyproject.toml`, root `conftest.py`, `companion/conftest.py` |
| Quick run command | `SKYPANE_COVERAGE=off JOBS=4 ./scripts/run-all-tests.sh -- stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py` |
| Full suite command | `./scripts/run-all-tests.sh` (CI: aggregate check "Lint, test, coverage, attribution") |
| Estimated runtime | quick ~8 s; full ~10 min in CI |

## Sampling Rate

- After every task commit: quick run command plus the PR's own targeted test
- After every plan wave: gates (`ruff check .`, mypy, function size, comment history) and full suite in CI
- Before verify-work: CI green on the draft PR; collected-id list unchanged (`comm -23 before.ids after.ids` empty)

## Per-Task Verification Map

Filled by the planner per task; every task names its automated command (see research proof table). Status: pending.

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements (new tests are additive: backup drift guard, shim `old is new` assertions).

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flaky test repeated 30x | QUAL-01 | browser tests do not run in this environment | CI repeated runs of the one test |
| Remote branch deletion | QUAL-01 | owner approval required | list branches, owner approves |

## Validation Sign-Off

- [ ] All tasks have an automated verify or a listed manual check
- [ ] No weakened CI gate; coverage floor ratcheted last
- [ ] `nyquist_compliant: true` set when the map is complete
