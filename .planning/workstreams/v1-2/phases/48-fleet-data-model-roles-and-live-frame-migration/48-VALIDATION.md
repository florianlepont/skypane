---
phase: 48
slug: fleet-data-model-roles-and-live-frame-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-28
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (+ xdist, cov, pytest-socket loopback guard) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `server/.venv/bin/python3 -m pytest server/test_fleet_db.py server/test_hardware.py server/test_fleet_migrate.py stub-server/test_fleet_auth.py stub-server/test_phase47_freeze.py deploy/tests/test_backup.py deploy/tests/test_activate.py -x -q --cov-fail-under=0` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched area
- **After every plan wave:** Run `./scripts/run-all-tests.sh`
- **Before `/gsd:verify-work`:** Full suite plus ruff, mypy, `scripts/check_function_size.py`, `scripts/check_comment_history.py check` green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 48-01-xx | 01 | 1 | DATA-01, DATA-03 | — | one owner per device; role CHECK; FK on | unit | `pytest server/test_fleet_db.py -x` | ❌ W0 | ⬜ pending |
| 48-01-xx | 01 | 1 | DATA-04 | — | legacy profile equals existing constants | unit | `pytest server/test_hardware.py -x` | ❌ W0 | ⬜ pending |
| 48-02-xx | 02 | 2 | DATA-02 | — | idempotent migration; dry-run writes nothing | unit | `pytest server/test_fleet_migrate.py -x` | ❌ W0 | ⬜ pending |
| 48-03-xx | 03 | 3 | DATA-02 | — | old-style readers authenticate after new enrolment; fallback to legacy | integration | `pytest stub-server/test_fleet_auth.py -x` | ❌ W0 | ⬜ pending |
| 48-04-xx | 04 | 4 | DATA-02, DATA-05 | — | backup includes fleet.db; restore tested; activate order | deploy | `pytest deploy/tests/test_backup.py deploy/tests/test_activate.py -x` | extend | ⬜ pending |
| 48-05-xx | 05 | 5 | DATA-02, DATA-05 | — | Phase 47 fields frozen | integration | `pytest stub-server/test_phase47_freeze.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/test_fleet_db.py`, `server/test_hardware.py`, `server/test_fleet_migrate.py`
- [ ] `stub-server/test_fleet_auth.py`, `stub-server/test_phase47_freeze.py`
- [ ] Sanitised live-shaped state fixture generator (shared helper)
- [ ] Extend `deploy/tests/conftest.py` with a fake `fleet_migrate` call logger
- [ ] Add new typed modules to `pyproject.toml` mypy lists

---

## Manual-Only Verifications

All phase behaviors have automated verification. (No production deploy in this phase.)

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
