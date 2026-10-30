---
phase: 51
slug: per-device-config-image-and-state
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-30
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. The test map lives in `51-RESEARCH.md` (section "Validation Architecture"); the planner binds each task to it.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + xdist + cov + socket guard + playwright |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `server/.venv/bin/python3 -m pytest stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py -x -q` plus the touched module's tests |
| **Full suite command** | `./scripts/run-all-tests.sh`, then `ruff check .`, `mypy`, `scripts/check_comment_history.py check`, `scripts/check_function_size.py check --max 80 server stub-server` |
| **Estimated runtime** | quick ~30 s, full several minutes |

## Sampling Rate

- **After every task commit:** quick run command
- **After every plan wave:** full suite command
- **Before `/gsd:verify-work`:** full suite green; `test_phase47_freeze.py` and `test_image_negotiation.py` unmodified and green
- **Max feedback latency:** 60 s for the quick command

## Per-Task Verification Map

Populated by the planner from `51-RESEARCH.md` (Phase Requirements -> Test Map). Every task carries an automated command. Plan 13 fills the Result column.

| Task | Plan | Wave | Requirement | Automated command | Result |
|------|------|------|-------------|-------------------|--------|
| 51-01-T1 | 01 | 1 | FLT-01 | `pytest server/test_device_dirs.py` + `mypy` | pending |
| 51-01-T2 | 01 | 1 | FLT-01 | `pytest server/test_fleet_db.py stub-server/test_fleet_cli.py` | pending |
| 51-01-T3 | 01 | 1 | FLT-01 | `pytest test-support/test_test_support.py` | pending |
| 51-02-T1 | 02 | 1 | FLT-02 | `pytest server/test_config_history.py server/test_retired_notifications.py` | pending |
| 51-02-T2 | 02 | 1 | FLT-02 | `pytest server/test_device_policy.py stub-server/test_poll_cycle.py` + `mypy` | pending |
| 51-03-T1 | 03 | 1 | FLT-01 | `pytest deploy/tests/test_backup.py -k devices` | pending |
| 51-03-T2 | 03 | 1 | FLT-01 | `pytest deploy/tests/test_docs.py` | pending |
| 51-04-T1 | 04 | 2 | FLT-01, FLT-02 | `pytest stub-server/test_device_fleet.py stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py` | pending |
| 51-04-T2 | 04 | 2 | FLT-01 | `pytest stub-server/test_device_fleet.py -k "img or health"` | pending |
| 51-05-T1 | 05 | 2 | FLT-01, FLT-02 | `pytest companion/test_device_routes.py companion/test_route_table.py` | pending |
| 51-05-T2 | 05 | 2 | FLT-01, FLT-02 | `pytest companion/test_device_scope.py` | pending |
| 51-06-T1 | 06 | 3 | FLT-01 | `pytest companion/test_device_dispatch.py companion/test_render_baseline.py` | pending |
| 51-06-T2 | 06 | 3 | FLT-02 | `pytest companion/test_device_poll.py companion/test_poll_now_lock.py` | pending |
| 51-06-T3 | 06 | 3 | FLT-02 | `pytest companion/test_device_settings.py` | pending |
| 51-07-T1 | 07 | 4 | FLT-01 | `pytest companion/test_device_actions.py -k "illustration or resolve or rename or manual"` | pending |
| 51-07-T2 | 07 | 4 | FLT-01, FLT-02 | `pytest companion/test_device_actions.py` | pending |
| 51-08-T1 | 08 | 5 | FLT-01, FLT-02 | `pytest companion/test_device_links.py companion/test_render_baseline.py` | pending |
| 51-08-T2 | 08 | 5 | FLT-01 | `pytest companion/test_device_links.py companion/test_airline_sheet.py` | pending |
| 51-09-T1 | 09 | 5 | FLT-01 | `pytest companion/test_device_selector.py test-support/test_i18n_ids.py` | pending |
| 51-09-T2 | 09 | 5 | FLT-01 | `SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_browser_device_selector.py` | pending |
| 51-10-T1 | 10 | 6 | FLT-02 | `pytest companion/test_device_settings.py -k timezone` | pending |
| 51-10-T2 | 10 | 6 | FLT-02 | `pytest companion/test_device_poll.py -k "caption or unsupported or prefix or cooldown"` | pending |
| 51-11-T1 | 11 | 5 | FLT-01 | `pytest companion/test_device_pages.py -k "health or history"` | pending |
| 51-11-T2 | 11 | 5 | FLT-01 | `pytest companion/test_device_pages.py -k home` | pending |
| 51-12-T1 | 12 | 7 | FLT-01, FLT-02 | `pytest companion/test_device_routes.py companion/test_device_isolation.py` | pending |
| 51-12-T2 | 12 | 7 | FLT-01, FLT-02 | `pytest companion/test_device_routes.py` + inventory count check | pending |
| 51-13-T1 | 13 | 8 | FLT-01, FLT-02 | `./scripts/run-all-tests.sh` + ruff, mypy, guards, freeze tests | pending |
| 51-13-T2 | 13 | 8 | FLT-01, FLT-02 | bookkeeping diff check (human-check: owner steps) | pending |

## Wave 0 Requirements

- [ ] `test-support/skypane_two_device_fleet.py` — two simulated devices fixture
- [ ] `server/test_device_dirs.py`, `stub-server/test_device_fleet.py`
- [ ] `companion/test_device_routes.py`, `test_device_poll.py`, `test_device_settings.py`, `test_device_pages.py`, `test_device_selector.py`, `test_browser_device_selector.py`
- [ ] mypy file list gains `server/device_dirs.py`

## Manual-Only Verifications

All phase behaviours have automated verification. No production deploy is performed.

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] No 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
