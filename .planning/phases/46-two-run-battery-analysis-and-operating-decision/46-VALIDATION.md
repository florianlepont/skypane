---
phase: 46
slug: two-run-battery-analysis-and-operating-decision
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-12
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from the Validation Architecture section of `46-RESEARCH.md`.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ xdist, cov) in `server/.venv`; `hardware/` is already in `testpaths` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `server/.venv/bin/python3 -m pytest hardware -q --no-cov -n0` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Estimated runtime** | ~10 s quick, ~12 min full |

## Sampling Rate

- **After every task commit:** quick run command plus any touched POL-03 test file
- **After every plan wave:** full suite command
- **Before `/gsd:verify-work`:** full suite green; `python3 hardware/logtools.py selftest` passes; the committed model JSON is reproduced byte-identically from the committed inputs
- **Max feedback latency:** 60 s for the quick run

## Per-Task Verification Map

| Requirement | Behaviour | Test Type | Automated Command | File Exists | Status |
|-------------|-----------|-----------|-------------------|-------------|--------|
| BAT-03 | Solver recovers known E, P, Q from synthetic cycle counts and elapsed times; autonomy ceiling formula; non-positive standing draw reported, never dropped | unit | `pytest hardware/test_logtools_model.py -q --no-cov -n0` | ❌ W0 | ⬜ pending |
| BAT-03 | Run one is cut at 3300 mV by the raw rule; the smoothed rule differs on a synthetic dip; a run that never reaches the cut exits 2 | unit | same file | ❌ W0 | ⬜ pending |
| BAT-03 | Committed logs reproduce the committed model JSON exactly | reproducibility | same file | ❌ W0 | ⬜ pending |
| BAT-04 | Output always carries the assumptions block, the rated-not-measured label, the continuity FAIL carry-over and "What this model does not measure"; table for 300/600/900/1800 s with min/central/max | CLI output | same file | ❌ W0 | ⬜ pending |
| POL-01 | Document lists the four intervals with spread and an owner-decision block; no interval pre-selected | manual review + tool test | see Manual-Only | — | ⬜ pending |
| POL-02 | Each criterion has a source or "owner to verify" | manual review | see Manual-Only | — | ⬜ pending |
| POL-03 | A saved interval reaches the HTTP `sleep_s`; battery-critical park, display-off and quiet hours keep precedence; `wake.effective_wake_interval_s` agrees with the HTTP reply | integration (real handler) | `pytest stub-server/test_poll_cycle.py server/test_pipeline_e2e.py -q --no-cov -n0 -k "wake_interval or sleep_s"` | partial; new chained test W0 | ⬜ pending |
| All | Hygiene | lint/guards | `python3 scripts/check_comment_history.py check`; `ruff check` | ✅ | ⬜ pending |

## Wave 0 Requirements

- [ ] `hardware/test_logtools_model.py` for BAT-03 and BAT-04 (synthetic known-answer data and committed-log reproduction)
- [ ] A chained save-to-HTTP-`sleep_s` test with the precedence matrix and the `wake.py` parity check (POL-03)
- `hardware/logtools.py` stays out of the mypy file list

## Manual-Only Verifications

| Behaviour | Requirement | Why Manual | Test Instructions |
|-----------|-------------|------------|-------------------|
| The chosen interval and its freshness/autonomy rationale | POL-01 | The choice is the owner's (CONTEXT D-02) | Owner reads the autonomy table with its spread and records one interval in the decision block |
| Retain-or-replace pack decision | POL-02 | Needs facts only the owner can verify (enclosure fit, protection IC, charger limits, price) | Owner completes the checklist in the pack document |
| Applying the interval in production | POL-03 | Saving on the live Device page is an owner action | Owner saves the interval; the next healthy check-in returns it as `sleep_s` (confirmed on the real frame in Phase 47) |

## Validation Sign-Off

- [ ] All tasks have an automated verify or Wave 0 dependencies
- [ ] No 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
