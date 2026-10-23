---
phase: 47-integrated-field-validation-and-decision-record
plan: 01
subsystem: hardware-analysis
tags: [logtools, battery, sleep-current, voltage-trend]
requires: []
provides:
  - "python3 hardware/logtools.py sleep-trend: average-current estimate from the voltage fall of an owner export"
affects: [47-04]
tech-stack:
  added: []
  patterns: ["device_policy.py loaded by file path so logtools stays stdlib-only and standalone"]
key-files:
  created: [hardware/test_logtools_trend.py]
  modified: [hardware/logtools.py]
key-decisions:
  - "Default quiet window 23:30-06:00 is a constant in logtools, not read from device_policy's 23:00-07:00 code default"
  - "Band comparison is strict numeric with no tolerance; an estimate equal to a reference falls in the lower band"
requirements-completed: [VAL-03]
duration: n/a
completed: 2026-10-23
---

# Phase 47 Plan 01: sleep-trend Summary

`hardware/logtools.py sleep-trend` estimates the frame's average current from the battery-voltage fall in an owner export, with no multimeter. It is read-only and tested on synthetic data only.

## What was built

- Pure functions in `hardware/logtools.py`: `select_trend_endpoints` (24 h cut, medians of mV and of timestamps over the first and last 12 h of non-quiet polls), `estimate_average_current_ma` (curve fraction fall x rated capacity / elapsed hours, plus mA per 10 mV sensitivity at each end), `trend_hypotheses` (favourable and central computed from `hardware/logs/battery-run2-report.json` and `battery-model.json`, allowance = capacity / 4320 h), `classify_current_band`.
- CLI `sleep-trend EXPORT --capacity-mah --interval-s [--ignore-hours --edge-hours --quiet-start --quiet-end --no-quiet-hours --start-utc --model --run2-report --out]`. It reads a file or stdin and prints the export sha256, `capacity: N mAh (rated, not measured)`, the ignore rule, end points with timestamps and poll counts, `average current: X mA`, sensitivity, the three reference values, one `band: <key>` line with its sentence, and `What this estimate does not measure` (six biases). It prints no finding letter and no statement about the six-month target. Refusals print `sleep-trend: refused: ...` and exit 2 (span under 48 h after the cut, fewer than 5 non-quiet polls at an end, non-positive fall with "no current is claimed", bad quiet time, unreadable input). `--out` is deterministic JSON including `export_sha256`, written only on success.
- Band-to-finding mapping is deliberately not in the tool or its help (band keys only); it belongs to the record in plan 47-04.

## Results (what ran)

All run from the worktree with a throwaway venv in the scratchpad (pytest, pytest-xdist, pytest-cov, pytest-socket, ruff, requests, pillow); no `server/requirements*` touched. The repo's `server/.venv` does not exist in this worktree, so commands used the scratchpad venv's python with `--no-cov -n0` as in the plan.

- `python -m pytest hardware/test_logtools_trend.py`: 38 passed (23 known-answer unit tests, 15 CLI/subprocess tests).
- `python -m pytest hardware -q --no-cov -n0`: 127 passed.
- `python3 hardware/logtools.py selftest`: all PASS lines (last: `PASS battery-history-db ...`).
- `python3 scripts/check_comment_history.py check`: exit 0.
- `ruff check hardware`: All checks passed.
- `python3 scripts/check_function_size.py check --max 80 server stub-server` (as CI runs it): 459 functions scanned, none over 80. The tool is not applied to `hardware/` by CI; the new functions are all well under 80 lines anyway.
- Not run: the full suite (`./scripts/run-all-tests.sh`), mypy (logtools is outside the mypy list), the Playwright browser tests. Those are outside this plan's scope.
- Hypotheses at 900 s from the committed JSON: favourable 1.95 mA, central 8.66 mA (asserted in tests); allowance 0.69 mA (3000 mAh) and 2.31 mA (10000 mAh).
- No file under `hardware/logs` changed; no real owner data used.

## Deviations from Plan

- Task 2's CLI tests were written in the same working session as the CLI and committed together with it, so there is no separate failing-test commit for Task 2 (Task 1 has the RED commit `21630b09`). The CLI tests were first run against the finished CLI.
- Two expectations in my own first-draft tests were wrong and were corrected, not the tool: a 2.0 mA synthetic fall at 900 s is above the 1.95 mA favourable value, so its band is `between_favourable_and_central`; and the quiet share for a 23:30-06:00 window is about 27 %.
- `--start-utc` is implemented as dropping polls before the instant before any other step, so the 24 h ignore starts at the first kept poll.

## Known limits

- Synthetic-data validation only: the estimator is proven to recover a known current within 2 % (and 5 % end to end through the CLI), not that real packs follow the repository curve.
- The first test of the glitch-resistance property uses a slow fall so a 200 mV outlier moves the median by at most 1 mV.

## Commits

- `21630b09` test(47-01): add failing tests for the sleep-trend estimator
- `1349940d` feat(47-01): add sleep-trend estimation functions
- `23f9e0f2` feat(47-01): add the sleep-trend subcommand

## Self-Check: PASSED

Files `hardware/logtools.py` and `hardware/test_logtools_trend.py` exist; the three commits above are in the branch log.
