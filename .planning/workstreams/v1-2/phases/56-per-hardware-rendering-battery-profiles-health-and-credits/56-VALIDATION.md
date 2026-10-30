---
phase: 56
slug: per-hardware-rendering-battery-profiles-health-and-credits
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-30
---

# Phase 56 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 with xdist, cov, pytest-socket (`pyproject.toml`) |
| **Quick run command** | `server/.venv/bin/python3 -m pytest <paths> -q -n 0 --no-cov` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Static gates** | `ruff check .`; `mypy`; `scripts/check_function_size.py check --max 80 server stub-server`; `scripts/check_comment_history.py check` |

## Sampling Rate

- **After every task commit:** golden test + the touched module's tests (quick command)
- **After every plan wave:** `pytest server stub-server companion -q -n auto --no-cov` plus the static gates
- **Before verify-work:** `./scripts/run-all-tests.sh` green (coverage floor 93)

## Per-Requirement Verification Map

| Req | Behaviour | Type | Command | Plan |
|-----|-----------|------|---------|------|
| HWR-01a | Legacy render byte-identical (golden manifest) | golden | `pytest server/test_golden_render.py` | 56-01 |
| HWR-01b | Live responses unchanged | freeze | `pytest stub-server/test_phase47_freeze.py` | all |
| HWR-01c | Simulated landscape renders natively (800x480, 192000 packed bytes, all states/themes) | unit | `pytest server/test_render_landscape.py` | 56-06, 08, 09 |
| HWR-01d | `run_once(profile=...)` and BYOS serve the landscape device; dither cache not poisoned | integration | `pytest server/test_poll_cycle_profile.py stub-server/test_device_fleet.py` | 56-10 |
| HWR-01e | Themes filtered by profile inks, fallback to default | unit | `pytest server/test_themes.py server/test_hardware.py` | 56-02, 11 |
| HWR-01f | Battery identity for legacy; profile thresholds change decisions; health views | unit | `pytest server/test_device_policy.py companion/test_battery_profile.py` | 56-04, 07 |
| HWR-01g | Provenance complete per value; EE04 slot number-free and unregistered | unit | `pytest server/test_hardware.py` | 56-02 |
| HWR-02a | Anonymous `/credits` EN/FR with four sources and adsb.fi link | HTTP | `pytest companion/test_access_matrix.py companion/test_credits_page.py` | 56-03 |
| HWR-02b | `load_credits` rejects broken data files | unit | `pytest companion/test_credits_page.py` | 56-03 |
| HWR-02c | French catalogue complete | unit | `pytest companion/test_i18n.py` | 56-03 |

## Wave 0

- [ ] `server/test_golden_render.py` + `server/fixtures/golden/legacy_render_baseline.json` (generated from a clean worktree of the pre-phase commit)
- [ ] `server/test_render_landscape.py`

## Manual-Only Verifications

| Behaviour | Requirement | Why manual | Instructions |
|-----------|-------------|------------|--------------|
| Provider contact draft recorded with status `to-send` | HWR-02 | Suite guards forbid tests reading `.planning/` | Verifier opens `56-PROVIDER-CONTACT.md` |
| Owner reviews landscape preview PNGs | HWR-01 | Visual design | Plan 09 checkpoint |
| Owner glances at the credits page at phone width | HWR-02 | Visual design | End-of-phase verification |

## Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Golden manifest never regenerated after plan 01
- [ ] `nyquist_compliant: true` set after execution
