---
phase: 45-controlled-second-discharge-study
plan: 01
subsystem: hardware-protocol
tags: [battery, discharge-study, protocol, pre-registration]
requires: []
provides:
  - "Owner-confirmed Run 2 Protocol in hardware/BATTERY-RUN.md (60 s cadence, 21-day ceiling)"
  - "Re-derived labelled predictions at the effective gap, with the mixed-case formula"
  - "A PROPOSED rule for the reference interval of the continuity gates (O-1)"
affects: [45-03, 45-04]
key-decisions:
  - "D-05 cadence 60 s (owner amendment of the proposed 900 s), D-06 ceiling 21 days (amended from 45)"
  - "D-07, D-09, D-10 confirmed as proposed; thresholds unchanged (0.95 / 3 / 100 / 3400)"
  - "30 s deferred: below the Device setting's 60 s minimum, a production cadence change"
requirements-completed: []
completed: 2026-10-05
---

# Phase 45 Plan 01: Run 2 Protocol Summary

Owner confirmation: given in chat on 2026-10-05 and recorded verbatim in substance in `45-CONTEXT.md` (D-05..D-10). Docs only: no Python changed, no measurement or result written.

## What was confirmed

- Cadence 60 s (the effective cadence is the measured mean gap, expected about 62 to 100 s, headline 88 s), ceiling 21 days, same pack and firmware family, firmware frozen during the run, display enabled and no quiet hours, `boot_count_start` recorded before unplugging, production interval restored and recorded, park-window rule (continuity judged up to the first reading at or below 3300 mV, full window informational, boot witness on the full window), thresholds unchanged.
- Written in `hardware/BATTERY-RUN.md` `## Run 2 Protocol` (status CONFIRMED by the owner 2026-10-05) and `45-CONTEXT.md`.

## What stays PROPOSED

O-1, the interval the continuity gates are judged against (Protocol section 4a). With the real `run-report` on synthetic exports at `interval_s=60`, coverage is 0.682 for a constant 88 s gap and 0.701 for run one's refresh mix, so the pre-registered 0.95 gate fails structurally. Recommended option 3: configured interval plus overhead measured over the first 48 hours, frozen in the params file and committed before any verdict. The tool change it needs is a conditional task (45-04 Task 0), not implemented.

## Also found (not decisions)

- Run one predates the Phase 34 firmware; the no-change wake went from about 6.3 s to about 1.65 s, so per-wake energy may differ between the runs.
- Run one's BATTERY-RUN.md says the image never changed, while the Phase 34 hardware session attributes the 28 s overhead to about 60 % refresh wakes. Recorded as an unresolved disagreement in the protocol.
- A 60 s ceiling tolerance (one interval) means a ceiling end needs `end_time_utc`; the gap gate (3 intervals = 180 s) is far stricter in seconds than run one's 900 s.

## Verification

- Run-one text of BATTERY-RUN.md byte-identical (diff touches only the Run 2 section).
- `pytest hardware`: 32 passed; `logtools.py selftest` passes; ruff and `scripts/check_comment_history.py check` clean. Markdown-only change, so the full suite was not rerun.

## Deviations from Plan

The plan's proposed 900 s / 45 days were replaced by the owner's 60 s / 21 days. The plan's Task 3 verify strings were adjusted to the owner's wording of the status line. One item (O-1) deliberately remains PROPOSED.

## Self-Check: PASSED

## Update 2026-10-05 (after the owner's decisions on O-1)

O-1 is closed: the owner confirmed option 3 (D-11) and accepted the two comparability limitations (D-12). Protocol section 4a is CONFIRMED with the exact rule, the helper command and where the value is recorded, and the limitations sit under "Known limitations carried to Phase 46". The tool change (45-04 Task 0) was implemented ahead of the run, with tests on synthetic data only. The "What stays PROPOSED" section above is the record as of this plan's execution.
