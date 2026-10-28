---
phase: 47-integrated-field-validation-and-decision-record
plan: 04
subsystem: hardware-validation
tags: [VAL-03, sleep-trend, voltage-trend]
requires: ["47-01", "47-02", "47-03"]
provides:
  - "Owner's 900 s export committed unmodified with the verbatim sleep-trend output and JSON"
  - "VAL-03 section of hardware/FIELD-VALIDATION.md filled; status row settled by the voltage trend (outcome (a))"
affects: [47-05, 47-06]
key-files:
  created:
    - hardware/logs/sleep-trend-900s-export.jsonl
    - hardware/logs/sleep-trend-900s-output.txt
    - hardware/logs/sleep-trend-900s-report.json
    - hardware/logs/sleep-trend-900s-10000mah-output.txt
  modified:
    - hardware/FIELD-VALIDATION.md
requirements-completed: [VAL-03]
completed: 2026-10-28
---

# Phase 47 Plan 04: VAL-03 from the voltage trend Summary

The tool's average-current estimate on the owner's 900 s export is 0.39 mA (3000 mAh, rated), band `at_or_below_allowance`, which maps to outcome (a); the record carries the caveats that limit how far that figure can be trusted.

## What ran

- Task 1 (owner checkpoint) was resolved before this run: the owner exported the history on 2026-10-28 and attached it. Original and committed copy both have sha256 `507e8cf70b75d9c8385813b75d5806d3fe6de981fdc084413d6f1643aaaf5980`; the same value is in the JSON.
- `python3 hardware/logtools.py sleep-trend hardware/logs/sleep-trend-900s-export.jsonl --capacity-mah 3000 --interval-s 900 --start-utc 2026-10-23T04:25:00Z --out hardware/logs/sleep-trend-900s-report.json` exited 0. Start median 4022.0 mV (2026-10-24T10:42:51Z, 47 polls), end median 4008.0 mV (2026-10-28T11:41:43Z, 47 polls), 97.0 h, 37.5 mAh, 0.39 mA, sensitivity 0.28 mA per 10 mV. Hypotheses 1.95 and 8.66 mA, allowance 0.69 mA. Band `at_or_below_allowance`.
- The same command with `--capacity-mah 10000` (allowance only, no `--out`): allowance 2.31 mA, band `not_applicable`; its 1.29 mA estimate is not used because the 10000 mAh pack was never in the frame.
- No rows were cut (0 dropped before the start instant); the two null-battery rows were tolerated by the tool.
- Gates: `pytest hardware` 139 passed (scratchpad venv, `--no-cov -n0`); `scripts/check_comment_history.py check` exit 0; `ruff check hardware` clean.

## Finding

Outcome (a), chosen strictly from the printed band. VAL-03 row: settled by the voltage trend, for the 900 s test on the current 3000 mAh pack only. Nothing is claimed about the new pack. The multimeter procedure stays optional. No interval is chosen here (47-05).

Honest caveats written into the record: curve and 3000 mAh are ratings; both end points are at the top of the curve, its least reliable part; the estimate rests on a 14 mV fall (about 3.46 mV per day, arithmetic by Claude), with 0.28 mA per 10 mV sensitivity, so a 14 mV error is as large as the estimate; the central model (8.66 mA) would imply roughly 326 mV fall (arithmetic by Claude, at average curve slope) against 14 mV observed, so the data do not support it; the favourable 1.95 mA is not matched either, the estimate being lower, stated without explanation.

## Deviations from Plan

- **Missing cross-reference.** The request said to cite `hardware/BATTERY-MODEL.md`, section 'Percentage calibration at the top of the curve'. That section does not exist in the file (nor anywhere on origin/main). The record states the top-of-curve caveat in its own words and says explicitly that the section does not exist; it does not cite it as support. I did not add the section (outside this plan's files). The orchestrator may want to add it or drop the reference.
- The plan's command omits `--start-utc`; it was added as the request specified (it dropped 0 rows).
- The "wake alone meets 2.31 mA" interval (about 759 s, arithmetic by Claude) is included as the (a) sentence requires; it is flagged as not the interval decision.
- Face-value note added to the record (not in the plan): 0.39 mA would mean about 323 days on 3000 mAh, which conflicts with the plan's "(a) means six months only with 10000 mAh" wording; the record shows both and relies on neither.

## Known Stubs

None.

## Commits

- `f6fefd04` feat(47-04): commit the owner's 900 s export and the sleep-trend run
- `72be8c8b` docs(47-04): record the VAL-03 finding from the voltage trend

## Self-Check: PASSED

All five files exist; both commits are in the branch log; export sha256 matches the JSON.
