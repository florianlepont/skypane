---
phase: 46-two-run-battery-analysis-and-operating-decision
plan: 01
subsystem: hardware-tooling
tags: [battery, logtools, two-run-model, pytest]
requires: []
provides:
  - "logtools.py battery-model subcommand (like-for-like two-run solve, 108-scenario envelope, sweeps, mandatory text blocks, deterministic JSON)"
  - "hardware/test_logtools_model.py (known-answer, refusal, printed-block, determinism and committed-log tests)"
affects: [46-02, 46-03]
tech-stack:
  added: []
  patterns: ["closed-form 2x2 solve plus a fixed scenario grid instead of a fitted interval", "stdlib-only CLI tested as a subprocess with synthetic inputs in tmp_path"]
key-files:
  created:
    - hardware/test_logtools_model.py
  modified:
    - hardware/logtools.py
key-decisions:
  - "Both runs are cut at the first raw reading at or below 3300 mV; the rolling-median cuts (5 and 49 readings) are carried as named sensitivities in the envelope"
  - "The cut voltage, the envelope grid and the sweeps are module constants with no CLI flag"
  - "Inputs are recorded by basename and sha256 only, so the JSON regenerates byte-identically from any directory"
  - "The tool selects no interval and no pack; it prints that the choice is the owner's"
requirements-completed: [BAT-03, BAT-04]
duration: ~40min
completed: 2026-10-12
---

# Phase 46 Plan 01: battery-model tooling Summary

`logtools.py battery-model` reproduces the two-run battery model from the committed run-one log, the run-two export and the run-two report. It cross-checks the export against the report (sha256, polls to the cut, cut timestamp, first timestamp), counts both runs to the first reading at or below 3300 mV, separates per-wake energy from standing consumption with the closed-form solve, and prints autonomy to the BATTERY EMPTY park for 300, 600, 900 and 1800 s with central, minimum and maximum from a 108-scenario envelope. Every run prints the assumptions, the rated-not-measured capacity label, the continuity FAIL carry-over, the extrapolation warning and "What this model does not measure".

## Tasks and commits

| Task | Commit |
|------|--------|
| 1 RED: failing known-answer tests for the pure functions | 6a0337c5 |
| 1 GREEN: solve, cut rules, ratio and ceiling, autonomy, envelope, sweeps | 48ae1190 |
| 2 RED: failing tests for the subcommand | 8034d5e1 |
| 2 GREEN: `battery-model` subcommand, cross-checks, refusals, text blocks, JSON | aa4e4e97 |

## Verification

- `pytest hardware -q --no-cov -n0`: 88 passed (26 in `test_logtools_model.py`: 8 pure-function tests, 18 subcommand tests including the parametrised refusals).
- `logtools.py selftest`, `ruff check hardware`, `scripts/check_comment_history.py check`: clean.
- Committed inputs: exit 0. Copy of the report with an altered `export.sha256`: exit 2, `battery-model: refused:` on stderr, no `--out` file written.
- Two runs on the committed inputs wrote byte-identical `--out` files.
- `battery-model --help` lists no option for the cut voltage or the envelope grid; `hardware/logtools.py` is not in the mypy list.

## Deviations from Plan

**1. [Rule 3 - Blocking] Test interpreter path.** The worktree has no `server/.venv`, so the pytest runs used the main checkout's `server/.venv/bin/python3` interpreter with the worktree as working directory. No file outside the worktree was modified.

**2. [Interface detail] `build_envelope` run-two entries.** The plan describes `run2_counts` as `(label, n2)` entries "sharing T2" without a way to pass T2. Entries are `(label, n2, t2)` tuples so the function stays pure.

**3. [Test correction] Charge-scaling check.** The first version of the "charge cancels" test scaled wake and standing by 3 and compared autonomy in unscaled units, which is not the same quantity. It now compares two synthetic drains of a pack with three times the charge, which give identical counts and autonomy. Fixed in the GREEN commit 48ae1190.

## Known Stubs

None.

## Threat Flags

None. The tool reads local files only and adds no network, auth or write surface beyond the optional `--out` file.

## Self-Check: PASSED

Files and commits listed above exist.
