---
phase: 47
slug: integrated-field-validation-and-decision-record
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-23
---

# Phase 47 — Validation Strategy

> Per-phase validation contract. Style follows `46-VALIDATION.md`. No separate RESEARCH.md exists for this phase; the strategy derives from `47-CONTEXT.md`.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ xdist, cov) in `server/.venv`; `hardware/` and `stub-server/` are in `testpaths` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `server/.venv/bin/python3 -m pytest hardware stub-server/test_wake_interval_delivery.py -q --no-cov -n0` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Estimated runtime** | ~15 s quick, ~12 min full |

## Sampling Rate

- **After every task commit:** quick run command plus `python3 scripts/check_comment_history.py check`
- **After every plan wave:** quick run command and `python3 hardware/logtools.py selftest`; full suite after the last code-bearing wave (wave 2) and at the end (47-06)
- **Before `/gsd:verify-work`:** full suite green; selftest passes; ruff and `scripts/check_function_size.py` clean
- **Max feedback latency:** 60 s for the quick run

## Per-Task Verification Map

| Plan / Task | Requirement | Behaviour | Test Type | Automated Command | File Exists | Status |
|-------------|-------------|-----------|-----------|-------------------|-------------|--------|
| 47-01 T1 | VAL-03 | Constant-current synthetic fall recovered within 2 %; first 24 h ignored; median resists a glitch; quiet-hours polls excluded; refusals; hypotheses 1.95 / 8.66 mA at 900 s from the committed JSON | unit | `server/.venv/bin/python3 -m pytest hardware/test_logtools_trend.py -q --no-cov -n0` | ❌ W0 (created by this task) | ⬜ pending |
| 47-01 T2 | VAL-03 | `sleep-trend` CLI prints `rated, not measured`, hypotheses, allowance, a `band:` key (four keys plus not_applicable, one fixture each) and the band sentence and `What this estimate does not measure`; exit 2 on short or rising export; deterministic `--out`; input unchanged | CLI | `server/.venv/bin/python3 -m pytest hardware -q --no-cov -n0` | ❌ W0 | ⬜ pending |
| 47-02 T1 | VAL-01 | `checkin-gaps` gates reuse RUN_THRESHOLDS; hole fails the max-gap gate; quiet gaps set aside (explicit 23:30-06:00 default); `--skip-first-gaps` excludes the old-interval gap; patched RUN_THRESHOLDS flips the verdict (tool has no thresholds of its own); wrong expected interval fails | unit + CLI | `server/.venv/bin/python3 -m pytest hardware/test_logtools_gaps.py -q --no-cov -n0` | ❌ W0 | ⬜ pending |
| 47-02 T2 | VAL-01 | Park evidence from committed run-two export at 3600 s; existing precedence tests green | CLI output + integration | `server/.venv/bin/python3 -m pytest stub-server/test_wake_interval_delivery.py server/test_pipeline_e2e.py hardware -q --no-cov -n0` | ✅ (tests) / ❌ (evidence file) | ⬜ pending |
| 47-03 T1-T2 | VAL-01, VAL-02, VAL-03 | Checklist, French steps and record skeleton exist with required headings | document grep | verify commands in 47-03 | ❌ | ⬜ pending |
| 47-04 T2 | VAL-03 | Export committed unmodified, sha256 matches tool JSON, caveat heading present | document/sha check | verify command in 47-04 | ❌ | ⬜ pending |
| 47-04 T3 | VAL-03 | Finding recorded from the printed band key by the fixed mapping (a/b/c); (c) leaves VAL-03 open | document grep | verify command in 47-04 | ❌ | ⬜ pending |
| 47-05 T3 | VAL-01 | Cadence verdicts for the chosen interval and display-off recorded verbatim | CLI output + grep | verify command in 47-05 | ❌ | ⬜ pending |
| 47-06 T2 | VAL-02 | No `pending (owner)`; decision table cites pack status; no requirement left pending | document grep | verify command in 47-06 | ❌ | ⬜ pending |
| 47-06 T3 | VAL-01, VAL-02 | Final interval present in the safety-pins, wake-mirror and saved-interval tuples (collect-only check); ROADMAP criterion 4 and VAL-03 wording amended; gates green | integration + guards | verify command in 47-06 | ✅ | ⬜ pending |
| All | All | Hygiene | lint/guards | `python3 scripts/check_comment_history.py check`; `server/.venv/bin/ruff check hardware stub-server server`; `python3 scripts/check_function_size.py` | ✅ | ⬜ pending |

## Wave 0 Requirements

- [ ] `hardware/test_logtools_trend.py` for the `sleep-trend` estimator and CLI (synthetic known-answer data, no real export committed)
- [ ] `hardware/test_logtools_gaps.py` for `checkin-gaps`
- `hardware/logtools.py` stays out of the mypy file list; tests assert behaviour (printed output, exit codes), never source text or `.planning/`

## Manual-Only Verifications

| Behaviour | Requirement | Why Manual | Test Instructions |
|-----------|-------------|------------|-------------------|
| The 900 s export and its conditions (USB, reset) | VAL-03 | Only the owner can export and report; due about 2026-10-28 19:00 Paris | 47-04 checkpoint; French steps Partie A |
| Final wake interval choice | VAL-02 | The choice is the owner's | 47-05 decision checkpoint |
| Applying the interval on the live Device page; 24 h trial; display-off window starting at the first check-in after the switch | VAL-01 | Production settings are changed by the owner; Claude never deploys; the frame learns display-off only at its next check-in | 47-05 checkpoint; French steps Parties B and C |
| Pack arrival and the four acceptance checks (label, polarity by multimeter, free area, charge behaviour) | VAL-02 | Physical; pack not yet received | 47-06 checkpoint; `hardware/PACK-ACCEPTANCE.md`; French steps Partie D |

## Validation Sign-Off

- [ ] All tasks have an automated verify or Wave 0 dependencies
- [ ] No 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending plan check
