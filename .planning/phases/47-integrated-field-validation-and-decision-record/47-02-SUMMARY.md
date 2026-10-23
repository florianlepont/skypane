---
phase: 47-integrated-field-validation-and-decision-record
plan: 02
subsystem: hardware-analysis
tags: [logtools, checkin-gaps, park-override, field-validation]
requires: ["47-01", "47-03"]
provides:
  - "python3 hardware/logtools.py checkin-gaps: check-in cadence of an export window judged with the Phase 45 continuity gates"
  - "hardware/logs/val01-run2-parked-checkins.txt: verbatim tool output over the run-two parked window"
affects: [47-05]
tech-stack:
  added: []
  patterns: ["gate stats built from judged gaps with compute_battery_stats definitions; thresholds read from RUN_THRESHOLDS at call time"]
key-files:
  created: [hardware/test_logtools_gaps.py, hardware/logs/val01-run2-parked-checkins.txt]
  modified: [hardware/logtools.py, hardware/FIELD-VALIDATION.md]
key-decisions:
  - "No threshold constant in the new code; check_coverage and check_max_gap are called with RUN_THRESHOLDS values read at call time"
  - "Default quiet window is the owner's 23:30-06:00 (the existing TREND_QUIET constants), not device_policy's 23:00-07:00"
requirements-completed: [VAL-01]
duration: n/a
completed: 2026-10-23
---

# Phase 47 Plan 02: checkin-gaps and park-override evidence Summary

`checkin-gaps` measures the gaps between consecutive check-ins in a window of an owner export and judges them with the same coverage (0.95) and largest-gap (3 intervals) gates as `run-report`. It was run on the committed run-two export over the parked window.

## Tasks and commits

| Task | Commit |
|---|---|
| 1 RED: failing tests | a60faf02 |
| 1 GREEN: `checkin-gaps` subcommand | 72a6aa1d |
| 2 evidence file and FIELD-VALIDATION.md section | 82a23fc6 |

## Real results

Run-two history, real frame, 2026-10-10T20:33:30 to 2026-10-12T16:22:02 UTC, export sha256 540d8f56...efdb (matches battery-model.json). Full verbatim output and commands: `hardware/logs/val01-run2-parked-checkins.txt`.

- `--expect-s 3600 --no-quiet-hours`: 46 rows, 45 gaps, min/median/max 98 / 3582 / 3613 s, 0 gaps above 3 x expected, both gates PASS, `cadence verdict: PASS` (exit 0).
- `--expect-s 60` on the same window: coverage 0.017, largest gap 60.22 intervals, `cadence verdict: FAIL` (exit 1). The frame was not running at 60 s while parked.
- `--expect-s 3600 --skip-first-gaps 1`: the 98 s first gap set aside, 44 gaps between 3573 and 3613 s, PASS.

Observations to read with the numbers:

- The 98 s gap is the gap from the 3300 mV row to the next row; it is the gap before the park took effect (inferred, not logged). The plan's literal command includes it and still passes, because a short gap cannot fail either gate.
- The median parked gap is 3582 s, 18 s under 3600. As a result the information-only line `gaps within expected to 1.5 x expected` prints 2.2 percent, which looks alarming but only reflects gaps being a few seconds under the nominal hour. No cause for the 18 s is claimed.
- Automated precedence tests re-run: `stub-server/test_wake_interval_delivery.py` plus `server/test_pipeline_e2e.py`, 60 passed. Cited by name in FIELD-VALIDATION.md. They are server-side tests, labelled as such.
- Display-off has no real-frame evidence in run-two history; the section `Display-off: no real-frame evidence yet` says so and points to plan 47-05.

## Gates

- `pytest hardware stub-server/test_wake_interval_delivery.py server/test_pipeline_e2e.py` (venv in scratchpad with pytest, requests, pillow, `--no-cov -n0`): 199 passed (12 new tests).
- `ruff check hardware`: passed (one unused import in the new test file fixed before the feature commit).
- `scripts/check_comment_history.py check`: rc 0.
- `python3 hardware/logtools.py selftest`: no FAIL line.
- `scripts/check_function_size.py check --max 80 server stub-server`: none over 80 (the new functions are in `hardware/`, outside that gate; all are under 80 lines anyway).
- Not run: the full `scripts/run-all-tests.sh` (coverage gate, mypy, playwright), and no mypy on hardware.

## Deviations from Plan

None in behaviour. Notes on the plan's claims about existing code:

- The plan's interface note says `server/.venv/bin/python3` is the test interpreter; the worktree has no `server/.venv`, so a scratchpad venv was used as the task instructions said. Nothing under `server/requirements*` was touched.
- The plan says BATTERY-MODEL.md gives "a hourly check-in span with 41 check-ins". That figure covers only the span after the voltage peak (2026-10-11T00:34 on); the plan's window has 46 rows. Not a contradiction, but the two numbers will differ if compared.
- The test-name list in the plan names "recovery returns the saved value" in `server/test_pipeline_e2e.py` as a "recovery assertion"; the real test is `test_full_pipeline_end_to_end_through_the_real_device_protocol` (check 7 inside it). Recovery in the parametrised `test_safety_pins_win_over_saved_interval` is the case `latched-recovering`.
- `check_function_size.py` requires `check --max 80 <roots>`; it cannot be run without arguments.

## Known Stubs

None.

## Self-Check: PASSED

Files found: hardware/logtools.py (`checkin-gaps`), hardware/test_logtools_gaps.py, hardware/logs/val01-run2-parked-checkins.txt, hardware/FIELD-VALIDATION.md. Commits a60faf02, 72a6aa1d, 82a23fc6 exist on the branch.
