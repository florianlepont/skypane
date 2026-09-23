---
phase: 32
slug: test-foundation-pytest-and-ci-you-can-trust
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-23
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-xdist 3.8.0 + pytest-cov 7.1.0 + pytest-socket 0.8.1 (installed by Wave 0) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + repo-root `conftest.py` (Wave 0) |
| **Quick run command** | `server/.venv/bin/python3 -m pytest <migrated file> -q` |
| **Full suite command** | `./scripts/run-all-tests.sh` (thin wrapper over `pytest -n auto --cov`) |
| **Estimated runtime** | quick ~5 s; full ~250 s (companion browser harnesses via the shim dominate) |

---

## Sampling Rate

- **After every task commit:** run the migrated file's own module (`pytest server/test_<name>.py -q`) and, while the legacy runner still exists, its old harness baseline transcript for comparison
- **After every plan wave:** `pytest server/ stub-server/ -n auto`
- **Before `/gsd:verify-work`:** `./scripts/run-all-tests.sh` full green (shim included), coverage floor recorded in `pyproject.toml`
- **Max feedback latency:** 60 seconds for per-task checks

---

## Per-Task Verification Map

Filled by the planner/executor per task; requirement-level map:

| Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|-----------------|-----------|-------------------|-------------|--------|
| TST-01 | N/A | smoke | `pytest --collect-only -q` ; `pytest -n auto --cov` | ❌ W0 | ⬜ pending |
| TST-02 | N/A | unit per file + ledger completeness | `pytest server/ stub-server/ -v` ; ledger row count == baseline check count per harness | ❌ per batch | ⬜ pending |
| TST-03 | no test reaches the network (in-process and child processes) | unit self-test + integration | `pytest -k non_loopback` ; `/poll-now` checks in `companion/test_companion_app.py` pass with the fake provider and the guard env var set | ❌ W0 | ⬜ pending |
| TST-04 | N/A | smoke | `grep "python-version: '3.14'" .github/workflows/ci.yml` ; `ruff check .` with `target-version = "py314"` | N/A | ⬜ pending |
| TST-05 | N/A | smoke | `./firmware/tests/run_host_tests.sh` ; `grep run_host_tests .github/workflows/firmware.yml` | ✅ | ⬜ pending |
| TST-06 | an in-flight deploy is never cancelled | config assertion | parse `ci.yml`: deploy concurrency group ≠ test group, `cancel-in-progress: false` on deploy | N/A | ⬜ pending |
| TST-07 | N/A | config assertion | `grep -- "--only-shell" ci.yml` ; cache step on `~/.cache/ms-playwright` keyed on playwright version | N/A | ⬜ pending |
| TST-08 | dependency tampering rejected | smoke | clean venv `pip install --require-hashes -r <runtime lock>` and `<dev lock>` | ❌ | ⬜ pending |
| TST-09 | N/A | integration | `pytest -n auto --cov --cov-report=term-missing` shows `companion/app.py`, `stub-server/byos_server.py` measured; `fail_under` == measured floor | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/requirements-dev.txt` — pytest, pytest-xdist, pytest-cov, pytest-socket
- [ ] `pyproject.toml` — `[tool.pytest.ini_options]`
- [ ] `conftest.py` (repo root) — socket guard, `collect_ignore` for legacy companion harnesses, fake provider fixture
- [ ] cross-process guard hook (`sitecustomize.py` on an injected `PYTHONPATH`, env-var gated)
- [ ] companion legacy-harness shim test module
- [ ] per-harness pre-migration baseline transcripts (15 server-side harnesses) + `32-MIGRATION-LEDGER.md` scaffold

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Deploy never cancelled by a newer push | TST-06 | GitHub Actions scheduling semantics | Two pushes to `main` in quick succession; first deploy completes (or waits), never shows "cancelled" mid-rsync |
| Playwright cache hit | TST-07 | Needs two real CI runs | Second CI run's cache step reports a hit and no browser download |
| CI actually runs on 3.14 | TST-04 | Real runner | `python --version` line in the CI log reads 3.14.x |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
