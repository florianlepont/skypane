---
phase: 51
slug: per-device-config-image-and-state
status: complete
nyquist_compliant: true
wave_0_complete: true
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
| 51-01-T1 | 01 | 1 | FLT-01 | `pytest server/test_device_dirs.py` + `mypy` | green (in full suite) |
| 51-01-T2 | 01 | 1 | FLT-01 | `pytest server/test_fleet_db.py stub-server/test_fleet_cli.py` | green (in full suite) |
| 51-01-T3 | 01 | 1 | FLT-01 | `pytest test-support/test_test_support.py` | green (in full suite) |
| 51-02-T1 | 02 | 1 | FLT-02 | `pytest server/test_config_history.py server/test_retired_notifications.py` | green (in full suite) |
| 51-02-T2 | 02 | 1 | FLT-02 | `pytest server/test_device_policy.py stub-server/test_poll_cycle.py` + `mypy` | green (in full suite) |
| 51-03-T1 | 03 | 1 | FLT-01 | `pytest deploy/tests/test_backup.py -k devices` | green (in full suite) |
| 51-03-T2 | 03 | 1 | FLT-01 | `pytest deploy/tests/test_docs.py` | green (in full suite) |
| 51-04-T1 | 04 | 2 | FLT-01, FLT-02 | `pytest stub-server/test_device_fleet.py stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py` | green (in full suite) |
| 51-04-T2 | 04 | 2 | FLT-01 | `pytest stub-server/test_device_fleet.py -k "img or health"` | green (in full suite) |
| 51-05-T1 | 05 | 2 | FLT-01, FLT-02 | `pytest companion/test_device_routes.py companion/test_route_table.py` | green (in full suite) |
| 51-05-T2 | 05 | 2 | FLT-01, FLT-02 | `pytest companion/test_device_scope.py` | green (in full suite) |
| 51-06-T1 | 06 | 3 | FLT-01 | `pytest companion/test_device_dispatch.py companion/test_render_baseline.py` | green (in full suite) |
| 51-06-T2 | 06 | 3 | FLT-02 | `pytest companion/test_device_poll.py companion/test_poll_now_lock.py` | green (in full suite) |
| 51-06-T3 | 06 | 3 | FLT-02 | `pytest companion/test_device_settings.py` | green (in full suite) |
| 51-07-T1 | 07 | 4 | FLT-01 | `pytest companion/test_device_actions.py -k "illustration or resolve or rename or manual"` | green (in full suite) |
| 51-07-T2 | 07 | 4 | FLT-01, FLT-02 | `pytest companion/test_device_actions.py` | green (in full suite) |
| 51-08-T1 | 08 | 5 | FLT-01, FLT-02 | `pytest companion/test_device_links.py companion/test_render_baseline.py` | green (in full suite) |
| 51-08-T2 | 08 | 5 | FLT-01 | `pytest companion/test_device_links.py companion/test_airline_sheet.py` | green (in full suite) |
| 51-09-T1 | 09 | 5 | FLT-01 | `pytest companion/test_device_selector.py test-support/test_i18n_ids.py` | green (in full suite) |
| 51-09-T2 | 09 | 5 | FLT-01 | `SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_browser_device_selector.py` | green (in full suite) |
| 51-10-T1 | 10 | 6 | FLT-02 | `pytest companion/test_device_settings.py -k timezone` | green (in full suite) |
| 51-10-T2 | 10 | 6 | FLT-02 | `pytest companion/test_device_poll.py -k "caption or unsupported or prefix or cooldown"` | green (in full suite) |
| 51-11-T1 | 11 | 5 | FLT-01 | `pytest companion/test_device_pages.py -k "health or history"` | green (in full suite) |
| 51-11-T2 | 11 | 5 | FLT-01 | `pytest companion/test_device_pages.py -k home` | green (in full suite) |
| 51-12-T1 | 12 | 7 | FLT-01, FLT-02 | `pytest companion/test_device_routes.py companion/test_device_isolation.py` | green (in full suite) |
| 51-12-T2 | 12 | 7 | FLT-01, FLT-02 | `pytest companion/test_device_routes.py` + inventory count check | green (in full suite) |
| 51-13-T1 | 13 | 8 | FLT-01, FLT-02 | `./scripts/run-all-tests.sh` + ruff, mypy, guards, freeze tests | green (in full suite) |
| 51-13-T2 | 13 | 8 | FLT-01, FLT-02 | bookkeeping diff check (human-check: owner steps) | green (diff check); owner steps in 51-OWNER-CHECKS.md pending |

## Wave 0 Requirements

- [x] `test-support/skypane_two_device_fleet.py` — two simulated devices fixture
- [x] `server/test_device_dirs.py`, `stub-server/test_device_fleet.py`
- [x] `companion/test_device_routes.py`, `test_device_poll.py`, `test_device_settings.py`, `test_device_pages.py`, `test_device_selector.py`, `test_browser_device_selector.py`
- [x] mypy file list gains `server/device_dirs.py`

## Manual-Only Verifications

All phase behaviours have automated verification. No production deploy is performed.

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] No 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Full-suite run on the merged branch (main already merged, `git log HEAD..origin/main` empty):**

- `./scripts/run-all-tests.sh --basetemp=/tmp/pb --cov-fail-under=93` with `SKYPANE_REQUIRE_BROWSER=1`: 6432 passed, 8 skipped (root ignores permission bits, 7 tests; local openssl cannot backdate a certificate, 1 test), 0 failed, coverage 95.85% (floor 93%). A short `--basetemp` is needed here because Chromium's singleton socket path exceeds 107 characters under the default pytest temp dir.
- ruff: all checks passed. mypy: no issues in 19 source files. comment-history check: exit 0. function-size gate (max 80): 641 functions, none over.
- Frozen files (`stub-server/test_phase47_freeze.py`, `stub-server/test_image_negotiation.py`, `stub-server/measured_fields_freeze.json`), `hardware/`, `firmware/`, `deploy/deploy.sh`, `deploy/activate.sh`, `deploy/provision.sh`: empty diff against the base ref. `.planning/phases/47-*`: empty diff. Freeze and negotiation tests pass inside the full run.

**Approval:** automated gates green; the owner's plain-French steps (`51-OWNER-CHECKS.md`) remain a human check.
