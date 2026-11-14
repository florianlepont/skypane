---
phase: 64
slug: second-hardware-in-production-build-release-deploy-and-parit
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-14
---

# Phase 64 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-xdist + pytest-cov (Python); POSIX shell checks; C host tests via `firmware/tests/run_host_tests.sh`; Playwright for companion browser tests |
| **Config file** | `pyproject.toml` (`testpaths = server stub-server companion test-support deploy hardware`) |
| **Quick run command** | `server/.venv/bin/python3 -m pytest server/test_hardware.py server/test_firmware_cli.py server/test_fleet_cycle.py server/test_render_landscape_hold.py deploy/tests -x -q` |
| **Full suite command** | `./scripts/run-all-tests.sh`, then `sh firmware/tests/run_host_tests.sh`, `python3 scripts/check_function_size.py`, `python3 scripts/check_comment_history.py check`, ruff, mypy |
| **Estimated runtime** | quick ~60 s; full ~9 min (CI median) |

---

## Sampling Rate

- **After every task commit:** the quick command for the touched area (see map below)
- **After every plan wave:** full suite plus host C tests, function-size and comment-history checks, ruff, mypy, and the must-not-break list
- **Before `/gsd:verify-work`:** full suite green plus must-not-break list
- **Max feedback latency:** 120 seconds for a task-level command

**Must-not-break (every wave):** `pytest stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py`; `sh firmware/tests/check_panel_diff.sh`; `git diff --name-only` shows no file of Phase 47 / 47.1 (`.planning/phases/47*`, `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json`); legacy production image identity at section level (resolved sdkconfig, size, `nm`, section dumps; procedure of 58-05-SUMMARY.md) rerun in plans 64-12 and 64-13; `.github/workflows/firmware-release.yml` untouched by every plan except 64-13.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 64-01-01 | 01 | 1 | HW2-04 | T-64-01 | switch accepts only "1", sim types stay hidden | unit | `pytest server/test_hardware.py -x -q` | extend | pending |
| 64-01-02 | 01 | 1 | HW2-04 | T-64-02/03 | no committed file assigns either switch | unit | `pytest server/test_hardware.py deploy/tests/test_units.py -x -q` | extend | pending |
| 64-02-01 | 02 | 1 | HW2-03 | T-64-05 | built check distinguishes boards, empty key fails | shell + pytest | `pytest deploy/tests/test_production_config_board.py -x -q` | W0 | pending |
| 64-02-02 | 02 | 1 | HW2-03 | T-64-06/07 | no `${{` in run:, size bound = ota_0 | unit | `pytest server/test_firmware_partition_bound.py deploy/tests/test_ci_secrets.py -q` | W0 | pending |
| 64-03-01 | 03 | 1 | HW2-05 | T-64-08 | live port/MAC refused before any write | shell (stubs) | `sh firmware/tests/check_provision_guard.sh` | W0 | pending |
| 64-03-02 | 03 | 1 | HW2-05 | T-64-08 | typed MAC required | shell | `sh firmware/tests/run_host_tests.sh` | extend | pending |
| 64-04-01 | 04 | 1 | HW2-04 | T-64-11/12 | profile in cache key, legacy bytes unchanged | unit | `pytest companion/test_theme_preview_profile.py companion/test_preview_cache.py -q` | W0 | pending |
| 64-04-02 | 04 | 1 | HW2-04 | T-64-11 | img dimensions follow profile | route/HTML | `pytest companion/test_theme_preview_profile.py companion/test_battery_profile.py -q` | W0 | pending |
| 64-05-01 | 05 | 1 | HW2-04 | T-64-14 | frame's own curve, unknown type safe | HTML | `pytest companion/test_battery_curve_call_sites.py companion/test_battery_profile.py -q` | W0 | pending |
| 64-06-01 | 06 | 1 | HW2-04 | T-64-16/17 | marks on three holds, battery_empty byte-stable, goldens intact | pixel | `pytest server/test_render_landscape_hold.py server/test_golden_render.py -q` | extend | pending |
| 64-07-01 | 07 | 1 | HW2-05 | T-64-18 | second-profile pins fail first | C host | `sh firmware/tests/run_host_tests.sh` | W0 | pending |
| 64-07-02 | 07 | 1 | HW2-05 | T-64-18/19 | static asserts hold, ee02 unchanged | C host + shell | `sh firmware/tests/run_host_tests.sh && sh firmware/tests/check_panel_diff.sh` | extend | pending |
| 64-08-01 | 08 | 2 | HW2-03 | T-64-21/23 | unknown/unavailable type skipped, bad shape fails | unit | `pytest server/test_firmware_cli.py server/test_firmware_registry.py -q` | extend | pending |
| 64-08-02 | 08 | 2 | HW2-03 | T-64-22 | tool accepts real type without switch, refuses sim | unit | `pytest deploy/tests/test_release_manifest.py -q` | extend | pending |
| 64-09-01 | 09 | 2 | HW2-03 | T-64-24 | hostile asset names never selected | unit | `pytest deploy/tests/test_release_assets.py -q` | W0 | pending |
| 64-09-02 | 09 | 2 | HW2-03 | T-64-25/26 | switch forwarded only when exactly 1, env file never sourced | pytest (stand-in cli) | `pytest deploy/tests/test_activate.py deploy/tests/test_ci_secrets.py -q` | extend | pending |
| 64-10-01 | 10 | 2 | HW2-03 | T-64-29/31 | reconcile independent of live cycle; failure keeps previous firmware | unit | `pytest server/test_firmware_reconcile.py server/test_fleet_cycle.py -q` | extend | pending |
| 64-11-01 | 11 | 3 | HW2-05 | T-64-32/33 | runbook owner-only, placeholders only | doc-claim | `pytest deploy/tests/test_docs.py -q` | extend | pending |
| 64-11-02 | 11 | 3 | HW2-05 | T-64-34 | guard limit documented | doc-claim | `pytest deploy/tests/test_docs.py hardware -q` | extend | pending |
| 64-12-01 | 12 | 4 | HW2-05 | T-64-35 | measured values only; sheet empty until owner | file check | `test -s hardware/SECOND-HARDWARE-MEASUREMENTS.md` | W0 | pending |
| 64-12-03 | 12 | 4 | HW2-05 | T-64-36/37 | budget above measured worst case, ee02 unchanged | C host + pytest | `sh firmware/tests/run_host_tests.sh && pytest server/test_hardware.py -q` | extend | pending |
| 64-13-03 | 13 | 4 | HW2-03 | T-64-38..40 | additions-only diff, key hygiene, dispatch last | pytest + git diff | `pytest deploy/tests/test_ci_secrets.py deploy/tests/test_release_manifest.py -q` | extend | pending |
| 64-14-* | 14 | 5 | HW2-03/04 | T-64-43..46 | owner lift, release, OTA, failure case | owner only | n/a (checkpoints) | - | pending |
| 64-15-* | 15 | 6 | HW2-04 | T-64-47/48 | EN/FR, admin and invited | owner only | n/a (checkpoints) | - | pending |

*Status: pending, green, red, flaky*

---

## Wave 0 Requirements

- [ ] `firmware/tests/fixtures/production_config/{ee02,second}/sdkconfig` and `deploy/tests/test_production_config_board.py` (64-02)
- [ ] `server/test_firmware_partition_bound.py` (64-02)
- [ ] `firmware/tests/check_provision_guard.sh` wired into `run_host_tests.sh` (64-03)
- [ ] `companion/test_theme_preview_profile.py`, `companion/test_battery_curve_call_sites.py` (64-04, 64-05)
- [ ] second-profile marker in `firmware/tests/test_wake_deadline.c` and `test_panel_guard.c` (64-07)
- [ ] `deploy/tests/test_release_assets.py` for `scripts/fw_release_assets.py` (64-09)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Written confirmation, then lift of the production switch | HW2-04 | Owner-only by decision; never done by the agent | Plan 64-14, decision checkpoint; record in `64-OWNER-VALIDATION.md` |
| First signed typed release published and deployed | HW2-03 | Reviewer-gated signing environment and deploy approval belong to the owner; also blocked on the live-frame release | Plan 64-13 checkpoints, plan 64-14 |
| Real signed https OTA on a second-type frame; failing update keeps previous firmware | HW2-03 | Needs the physical unit and production VPS | Plan 64-14 sections C and D |
| Measured refresh time, busy waits, flash size, battery sense, LED, keys | HW2-05 | Needs the physical unit; battery numbers stay provisional until measured | Plan 64-12, `hardware/SECOND-HARDWARE-MEASUREMENTS.md` |
| Companion walk-through as admin and invited user, EN and FR; landscape chip crop and hold marks look | HW2-04 | Real frame, deployed companion, visual judgement | Plan 64-15, `64-WALKTHROUGH.md` |

---

## Validation Sign-Off

- [x] All automated tasks have an `<automated>` verify or a Wave 0 dependency
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (owner checkpoints sit in plans 12, 13, 14, 15 and are bracketed by automated tasks)
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency under 120 s per task
- [ ] `wave_0_complete: true` set after Wave 1 lands

**Approval:** pending
