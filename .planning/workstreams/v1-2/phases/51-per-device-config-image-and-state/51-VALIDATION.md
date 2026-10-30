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

Populated by the planner from `51-RESEARCH.md` (Phase Requirements -> Test Map). Every task carries an automated command.

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
