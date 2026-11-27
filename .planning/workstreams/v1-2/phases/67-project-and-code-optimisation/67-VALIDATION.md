---
phase: 67
slug: project-and-code-optimisation
status: draft
nyquist_compliant: true
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

| Task | Plan | Wave | Requirement | Automated command | Status |
|------|------|------|-------------|-------------------|--------|
| 01-1 baseline doc | 01 | 1 | QUAL-01 | grep checks on 67-BASELINE.md (commit line, sha256, no IP) | pending |
| 01-2 MIN_EXECUTED | 01 | 1 | QUAL-01 | `pytest test-support/test_ci_gates.py` | pending |
| 02-1 state map | 02 | 2 | QUAL-01 | backticked-path resolution script over ARCHITECTURE.md | pending |
| 02-2 deploy README link | 02 | 2 | QUAL-01 | `pytest deploy/tests/test_docs.py deploy/tests/test_backup.py server/test_fleet_migrate.py` | pending |
| 03-1 backup drift guard | 03 | 2 | QUAL-01 | `pytest deploy/tests/test_backup.py` | pending |
| 03-2 leftover constants | 03 | 2 | QUAL-01 | freeze + goldens + history tests, ruff, mypy | pending |
| 04-1 flaky fix | 04 | 2 | QUAL-01 | ruff + collect-only id check; 30 CI runs (manual) | pending |
| 05-1 ARCHITECTURE rewrite | 05 | 3 | QUAL-01 | path-resolution and stale-claim script | pending |
| 05-2 CLAUDE.md pointer | 05 | 3 | QUAL-01 | grep assertions, comment-history check | pending |
| 06-1, 06-2 dead code | 06 | 2 | QUAL-01 | ruff, name grep, i18n and golden tests, mypy | pending |
| 07-1, 07-2 server duplicates | 07 | 3 | QUAL-01 | fleet registry tests, goldens, mypy | pending |
| 08-1, 08-2 companion duplicates | 08 | 3 | QUAL-01 | non-browser companion suite, ruff, mypy | pending |
| 09-1, 09-2 types | 09 | 4 | QUAL-01 | `mypy`, core suite | pending |
| 10-1, 10-2 gates | 10 | 4 | QUAL-01 | check_function_size over five roots, workflow tests | pending |
| 11-1, 11-2 docs and owner list | 11 | 4 | QUAL-01 | docs tests, comment-history, grep checks | pending |
| 12-1..3 owner decisions | 12 | 5 | QUAL-01 | checkpoints; branch list vs approved names (manual) | pending |
| 13-1, 13-2 firmware move | 13 | 6 | QUAL-01 | shim tests, import boundaries, units, mypy, core suite | pending |
| 14-1, 14-2 polling move | 14 | 7 | QUAL-01 | shim tests, poll_loop --help, units, mypy, core suite | pending |
| 15-1..3 pairing move and doc | 15 | 8 | QUAL-01 | shim tests, `-k pairing`, path-resolution script | pending |
| 17-1..3 unify migrations | 17 | 9 | QUAL-01 | `pytest server/test_sqlite_migrations.py deploy/tests/test_backup.py` plus freeze, goldens, fleet_migrate | pending |
| 18-1..3 owner retirement gate | 18 | 10 | QUAL-01 | grep checks on 67-RETIREMENT-GATE.md (read-only commands, decisions, no IP/hash); owner checkpoint (manual) | pending |
| 19-1..3 identity mirror | 19 | 11 | QUAL-01 | `pytest stub-server server/test_retire_legacy_state.py`, freeze unchanged (skips if G1 not approved) | pending |
| 20-1..2 per-device copies | 20 | 12 | QUAL-01 | `pytest server stub-server deploy/tests`, quarantine CLI tests (skips if G2 not approved) | pending |
| 21-1..2 legacy-admin, schema 5 | 21 | 13 | QUAL-01 | `pytest server/test_fleet_schema5.py -k "access_matrix or backup"` (skips if G3 not approved) | pending |
| 22-1..3 leftovers, history schema 2 | 22 | 14 | QUAL-01 | `pytest server/test_history_schema2.py server/test_config_history.py`, ci_gates tests (task parts skip per G4/G5) | pending |
| 23-1..2 docs and runbook | 23 | 15 | QUAL-01 | path-resolution script, `pytest deploy/tests/test_docs.py` | pending |
| 24-1..4 test-only API deletion | 24 | 5 | QUAL-01 | collected-id diff equals listed removed ids, freeze, goldens, ruff, mypy, ci_gates tests; owner review of 67-TEST-ONLY-API.md (manual) | pending |
| 25-1..4 SPDX headers and gate | 25 | 16 | QUAL-01 | `check_spdx_headers.py check`, numstat 1/0 per file, compileall, collected-id equality, workflow tests; owner sample review (manual) | pending |
| 16-1..3 after record, ratchet | 16 | 17 | QUAL-01 | collected-id comm, CI TOTAL (manual checkpoint), comment-history | pending |

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements (new tests are additive: backup drift guard, shim `old is new` assertions).

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flaky test repeated 30x | QUAL-01 | browser tests do not run in this environment | CI repeated runs of the one test |
| Remote branch deletion | QUAL-01 | owner approval required | list branches, owner approves |
| Rollback period over; each retirement G1-G6 | QUAL-01 | production DB not visible to the executor | owner runs read-only commands from 67-RETIREMENT-GATE.md and pastes counts |

## Validation Sign-Off

- [ ] All tasks have an automated verify or a listed manual check
- [ ] No weakened CI gate; coverage floor ratcheted last
- [ ] `nyquist_compliant: true` set when the map is complete
