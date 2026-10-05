---
phase: 45-controlled-second-discharge-study
status: planned (45-01 and 45-02 done; reference-interval rule confirmed and implemented 2026-10-05; 45-03 physical run pending, awaiting the owner)
nyquist_compliant: true
created: 2026-10-03
---

# Phase 45 Validation Ledger

## Source Audit

| Source | Item | Coverage | Plan |
|---|---|---|---|
| GOAL | Owner can reproduce a second discharge whose evidence is comparable to run one and usable for a two-run model | Covered | 45-01 to 45-04 |
| REQ | BAT-01 second controlled discharge, different cadence, same pack and workload | Covered | 45-01 (protocol), 45-03 (physical run) |
| REQ | BAT-02 cadence, baseline, window, endpoints, raw export, continuity and voltage-validity evidence | Covered | 45-02 (tool), 45-04 (results) |
| RESEARCH | Skipped by instruction | n/a | |
| CONTEXT | D-01 same pack, firmware family, workload | Covered | 45-01 item 1, 45-03 |
| CONTEXT | D-02 separate continuity and voltage-validity evidence | Covered | 45-02 verdicts, 45-04 Results |
| CONTEXT | D-03 reuse channel and pre-registered thresholds | Covered | 45-01 item 4, 45-02 fixed defaults |
| CONTEXT | D-04 interval via companion setting, value in force recorded | Covered | 45-01 item 2, 45-03 Task 1/2 |
| CONTEXT | D-05 cadence 60 s (CONFIRMED 2026-10-05) | Covered | 45-01, 45-03 Task 1 |
| CONTEXT | D-06 ceiling 21 days (CONFIRMED 2026-10-05) | Covered | 45-01, 45-03 Task 3 |
| CONTEXT | D-07 firmware/server baseline, invalid on change (CONFIRMED) | Covered | 45-01, 45-02 baseline verdict, 45-03 Task 3 |
| CONTEXT | D-08 three-way cycle reconciliation (CONFIRMED) | Covered | 45-02, 45-03 (boot_count_start), 45-04 |
| CONTEXT | D-09 restore production interval (CONFIRMED) | Covered | 45-03 Task 4/5 |
| PLANNER | D-10 park-window rule for the BATTERY EMPTY park at 3300 mV (CONFIRMED 2026-10-05) | Covered | 45-01, 45-02 |
| PLANNER | D-11 reference interval for the continuity gates at 60 s (was O-1; CONFIRMED 2026-10-05, option 3: mean gap of the first 48 h, gaps above 3x excluded, whole seconds, frozen before the verdict) | Covered; tool implemented, freeze pending the run | 45-01 protocol 4a, 45-03 Task 3 (48 h freeze), 45-04 Task 0 (implemented) |
| OWNER | D-12 accepted comparability limitations (post-Phase-34 firmware vs run one; unknown refresh share) | Recorded as known limitations; Phase 46 must carry them | 45-01 protocol, Phase 46 |

Deferred ideas (solar, image-download/refresh energy) are not planned.

## Per-Plan Verification Map

| Plan | Wave | Human checkpoint | Primary evidence |
|---|---|---|---|
| 45-01 | 1 | Yes (decision, answered 2026-10-05, including the reference-interval rule) | Run 2 Protocol present once, CONFIRMED with owner date including 4a, run-one text unchanged |
| 45-02 | 1 | No | `hardware/test_logtools_run2.py`, `logtools.py selftest`, ruff, comment-history guard, full suite |
| 45-04 Task 0 | 3 (done early) | No | `hardware/test_logtools_reference_interval.py` (absent field unchanged, 88 s at reference 88 passes with 60 s informational, bad runs still fail, helper first-48 h/exclusion/rounding/refusals, bad values exit 2), ruff, comment-history guard, function-size gate |
| 45-03 | 2 | Yes (4 human-action) | Params file and Start/Run Conditions records with owner-attributed values; export present |
| 45-04 | 3 | Yes (gate + review) | run-report output; Results with export sha256 |

## Anti-Fabrication Controls

- Values come only from owner replies (45-03) or from `run-report` output (45-04).
- `run-report` exits 2 on missing params, stale/non-chronological/empty rows; the example params file is refused.
- No retuning flags; thresholds fixed to the pre-registered values.
- The reference interval comes only from `logtools.py reference-interval` on the first 48 h of the export, is committed before any continuity verdict, and `run-report` FAILs continuity when the frozen value differs from the one recomputed from the first 48 h of the reported export.

## Manual-Only Verifications

| Behaviour | Why manual |
|---|---|
| Physical discharge, charge, polarity, protection, inspection | Real lithium cell |
| Reading boot_count off the console, reading Device page values, restoring production interval | Device/companion actions |
| Saving the VPS history.db export | Executor has no VPS access |
