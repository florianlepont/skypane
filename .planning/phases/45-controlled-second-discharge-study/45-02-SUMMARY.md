---
phase: 45-controlled-second-discharge-study
plan: 02
subsystem: hardware-tooling
tags: [battery, logtools, discharge-study, pytest]
requires: []
provides:
  - "logtools.py run-report subcommand (separate continuity / voltage_validity / baseline verdicts, three-way cycle reconciliation, raw export sha256)"
  - "hardware/run2-params.example.json schema example (refused by run-report)"
  - "hardware/ collected by default pytest discovery"
affects: [45-03, 45-04]
tech-stack:
  added: []
  patterns: ["stdlib-only CLI tested as a subprocess with synthetic rows in tmp_path"]
key-files:
  created:
    - hardware/test_logtools_run2.py
    - hardware/run2-params.example.json
  modified:
    - hardware/logtools.py
    - pyproject.toml
key-decisions:
  - "Thresholds fixed at 0.95 / 3 / 100 / 3400 (plus 1 day minimum span); no flags to retune them"
  - "Normal-cadence window ends at the first reading at or below park_mv; continuity judged there, voltage validity and boot reconciliation on the full window"
  - "disconnect_time_utc is recorded in the report but is not used as a refusal bound; the optional end_time_utc is"
requirements-completed: [BAT-01, BAT-02]
duration: ~45min
completed: 2026-10-03
---

# Phase 45 Plan 02: run-report tooling Summary

`logtools.py run-report` turns a raw device_health JSON-Lines export plus an owner params file into a JSON report with three separate verdicts, a three-way cycle reconciliation (boot witness "not computable", never estimated, when a count is missing), cadence, endpoints, baseline, restore record and the export sha256. It refuses (exit 2, no report file) on missing/null required params, empty or all-dropped rows, naive or out-of-order timestamps, or rows predating the pre-registration time.

## Tasks and commits

| Task | Commit |
|------|--------|
| 1 RED: failing behaviour tests | 732fd75d |
| 1 refactor: `history_row_to_line`, `parse_battery_lines` (from-history-db output verified byte-identical against the previous version) | 2215c766 |
| 1+2 GREEN: report core, CLI, refusal guards, params example | 8dc06d95 |
| 3 pytest testpaths includes `hardware` | 986742e0 |

## Verification

- `pytest hardware/test_logtools_run2.py`: 32 passed.
- `logtools.py selftest`: all 8 PASS lines.
- Example params file refused with exit 2.
- ruff check hardware, scripts/check_comment_history.py check: clean.
- Full `./scripts/run-all-tests.sh` (SKYPANE_REQUIRE_BROWSER=1): 3513 passed, 8 skipped (root permission-bit skips), coverage gate satisfied.
- mypy not applicable: hardware is not in the mypy module list, left untouched by design.

## Deviations from Plan

None - plan executed as written. The tests passed on first implementation run, so the RED commit (tests only, no implementation) is separate from the refactor and GREEN commits.

## Known Stubs

None.

## Self-Check: PASSED

Files and commits listed above exist.
