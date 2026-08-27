---
phase: 05-low-battery-indicator
plan: 260827-vq3
subsystem: infra
tags: [journald, systemd, battery-measurement, DEVICE-05, logtools]

requires:
  - phase: 05-low-battery-indicator (05-01 Task 1)
    provides: check-battery checker, BATTERY-RUN.md pre-registered protocol, battery fixtures
provides:
  - "from-journal subcommand bridging journalctl -o short-iso output into check-battery's bracketed-timestamp format"
  - "hardware/BATTERY-RUN.md amended (## Protocol Amendment) to the production skypane-byos.service observation channel, thresholds/ceiling/pack-handling unchanged"
  - "05-01-PLAN.md Tasks 2-3 re-scoped to the production server, interval_s recorded rather than hardcoded"
affects: [05-01-Task-2, 05-01-Task-3, hardware/logtools.py, hardware/BATTERY-RUN.md]

tech-stack:
  added: []
  patterns:
    - "journalctl -o short-iso -> from-journal -> check-battery pipeline reused unchanged by the existing analysis"

key-files:
  created:
    - hardware/fixtures/battery-journal.log
  modified:
    - hardware/logtools.py
    - hardware/BATTERY-RUN.md
    - stub-server/README.md
    - .planning/phases/05-low-battery-indicator/05-01-PLAN.md

key-decisions:
  - "The DEVICE-05 discharge run's observation channel moves from a locally-run stub server to the already-running production skypane-byos.service on the VPS - no Mac has to stay awake, on one address, or running for the run's duration"
  - "The checker's --interval-s stops being a remembered 300s constant and becomes interval_s, read off SKYPANE_SLEEP_S on the VPS at run start and recorded in BATTERY-RUN.md ## Measured Inputs"
  - "Daily check-ins regenerate hardware/logs/battery-run-server.log from the whole journald window (redirect, not append) to avoid duplicated-poll coverage inflation, with git-committed history as the journald-rotation repair path"

requirements-completed: [DEVICE-05]

coverage:
  - id: D1
    description: "from-journal subcommand converts journalctl short-iso lines into check-battery's [ISO-8601] bracketed format, dropping journal markers with a stderr count"
    verification:
      - kind: unit
        ref: "hardware/logtools.py selftest (battery-journal.log case)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Converted battery-journal.log telemetry messages are byte-identical to battery-good.log's, and the converted output passes the identical gated check-battery run"
    verification:
      - kind: unit
        ref: "hardware/logtools.py selftest (battery-journal.log message-equality assertion)"
        status: pass
    human_judgment: false
  - id: D3
    description: "check-battery handles timezone-offset-carrying timestamps safely in --status mode, and rejects mixed aware/naive timestamp input with a stated reason instead of raising"
    verification:
      - kind: unit
        ref: "manual verify command in 260827-vq3-PLAN.md Task 1 (mixed-log rejection + --status age computation)"
        status: pass
    human_judgment: false
  - id: D4
    description: "hardware/BATTERY-RUN.md amended with a dated ## Protocol Amendment section; all four thresholds, the 21-day ceiling, and the physical pack-handling steps remain byte-for-byte"
    verification:
      - kind: other
        ref: "260827-vq3-PLAN.md Task 2 automated verify (literal threshold-table grep + token checks)"
        status: pass
    human_judgment: false
  - id: D5
    description: "05-01-PLAN.md Tasks 2 and 3 re-scoped to the production server (skypane-byos.service, journalctl, from-journal, recorded interval_s) with every physical battery step and threshold intact and no hardcoded --interval-s 300 remaining"
    verification:
      - kind: other
        ref: "260827-vq3-PLAN.md Task 3 automated verify (task-block token/structure assertions)"
        status: pass
    human_judgment: false

duration: 26min
completed: 2026-08-27
status: complete
---

# Quick Task 260827-vq3: Adapt Phase 5's Battery Discharge Run to the Production Server Summary

**Bridged journalctl output into `check-battery`'s existing parser via a new `from-journal` subcommand, then amended the pre-registered `BATTERY-RUN.md` protocol and 05-01's hardware tasks to run the DEVICE-05 discharge measurement against the already-running `skypane-byos.service` production VPS instead of a laptop-run stub — with zero changes to any threshold, ceiling, or physical pack-handling step.**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-08-27T20:47:00Z
- **Completed:** 2026-08-27T21:13:00Z
- **Tasks:** 3
- **Files modified:** 5 (1 new fixture, 4 modified)

## Accomplishments

- Added `hardware/logtools.py from-journal`: converts `journalctl -o short-iso` output into the bracketed `[ISO-8601]` shape `check-battery` already parses, normalizing timestamp offsets (`Z`, colon-less `+HHMM`) for cross-Python-version `fromisoformat()` safety, dropping journal markers/unparseable lines with a `from-journal: dropped N` stderr summary, and validating every emitted line against the existing `parse_timestamp()` before emission.
- Fixed two latent timezone-awareness gaps in `check-battery` that the new offset-carrying timestamps would otherwise have hit: the `--status` age computation now takes `now()` in the poll's own timezone when one is present, and `check_timestamps_and_min_polls` now explicitly rejects a log mixing aware and naive timestamps (a `stamp`-produced log concatenated with a `from-journal`-converted one) with a stated reason instead of raising.
- Proved the bridge against the existing battery fixtures: `hardware/fixtures/battery-journal.log` (battery-good.log's telemetry re-rendered as realistic journalctl short-iso output, interleaved with a journal-begins header, a boot separator, and a bare request-line print) converts and passes the identical gated `check-battery` run, with telemetry messages byte-identical to `battery-good.log`'s. `selftest` now covers 7 fixtures (6 original + battery-journal), all green.
- Amended `hardware/BATTERY-RUN.md`: added a dated `## Protocol Amendment` section and an `### Observation channel` subsection describing the move to `skypane-byos.service`; the four thresholds (0.95 coverage / 3 max-gap / 100 mV drop / 3400 mV cutoff), the 21-day ceiling, the D-07 division, and the physical pack-handling requirements (full charge, polarity re-check, protection-circuit confirmation) all remain byte-for-byte. `interval_s` is now documented as a recorded value read off `SKYPANE_SLEEP_S` at run start, not a remembered 300s constant.
- Re-scoped `.planning/phases/05-low-battery-indicator/05-01-PLAN.md`'s Tasks 2 and 3 (still not autonomously executable - both remain blocking checkpoints) to the production channel: preflight now confirms `skypane-byos.service` is active and sets/records `SKYPANE_SLEEP_S`; the daily check-in regenerates the log via `journalctl -u skypane-byos.service | from-journal` over SSH instead of tailing a local file; every `check-battery` invocation in both tasks now takes the recorded `interval_s` instead of a hardcoded `300`. Task 1 (already executed) was untouched. No physical battery step, threshold, or ceiling moved.

## Task Commits

Each task was committed atomically:

1. **Task 1: Bridge journalctl output into the format check-battery already parses, and prove it against the fixtures that already exist** - `f215e77` (feat)
2. **Task 2: Amend the pre-registered protocol to the production observation channel, and say plainly what was amended and what was not** - `259dd2c` (docs)
3. **Task 3: Re-scope 05-01's two hardware tasks to the server that is already running, without moving a physical step** - `682acdc` (docs)

## Files Created/Modified

- `hardware/logtools.py` - Added `JOURNAL_RE`, `normalize_journal_timestamp()`, `cmd_from_journal()`, `from-journal` CLI subcommand; timezone-aware-safe `--status` age computation; mixed-awareness rejection in `check_timestamps_and_min_polls`; updated coverage-failure wording, `load_battery_polls` docstring, and `check-battery` help text
- `hardware/fixtures/battery-journal.log` - New fixture: `battery-good.log`'s telemetry re-rendered as journalctl short-iso output, plus dropped marker/request lines
- `hardware/BATTERY-RUN.md` - `## Protocol Amendment` section, `### Observation channel` subsection, `interval_s` promoted to a recorded value, `## Run Conditions`/`## Daily Check-Ins`/`## Measured Inputs` notes updated to the production channel
- `stub-server/README.md` - Two forward-reference pointers added (to `deploy/README.md` and `hardware/logtools.py from-journal`), local-run instructions left intact
- `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` - Tasks 2-3, `<objective>`, `must_haves`, `<threat_model>` (T-05-01-02, two trust-boundary rows), and the artifacts table re-scoped to the production channel

## Decisions Made

- Kept `battery_common`'s `--capacity-mah 3000` convention (matching the existing `selftest` fixtures) for the new `battery-journal.log` case rather than introducing a new capacity value, so the fixture is judged under exactly the same flags as `battery-good.log`.
- Journalctl fixture uses a `+0200` (colon-less) offset deliberately, to exercise both the timestamp-normalization path and the parity with `battery-good.log`'s naive timestamps under the mixed-awareness rejection check.
- Chose to update the module docstring's subcommand table (not strictly required by the plan) alongside the required `check-battery` help-text edit, for internal consistency now that a fourth subcommand exists.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria and automated verify blocks for all three tasks passed on first implementation; no auto-fixes (Rule 1/2/3) were needed.

## Issues Encountered

The plan's own verify commands use unquoted multi-flag shell variables (e.g. `$B` expanding to `--interval-s 3600 --min-days 1 --capacity-mah 3000`), which zsh does not word-split by default (unlike bash). Running the verify blocks directly in this environment's default zsh shell produced a misleading `argparse` error ("the following arguments are required: --capacity-mah") even though the implementation was correct. Resolved by running the verify blocks under `bash -c '...'` explicitly, which is the shell dialect the blocks are written for. No code or plan changes were needed - this was purely a local verification-environment quirk, not a defect in the deliverables.

## User Setup Required

None - no external service configuration required. The DEVICE-05 discharge run itself (Tasks 2-3 of 05-01-PLAN.md) remains a blocking `checkpoint:human-action`/`checkpoint:human-verify` pair requiring real hardware and a multi-day unattended window; this quick task only removed the Mac-availability constraint from that future run, it did not execute it.

## Next Phase Readiness

05-01-PLAN.md's Tasks 2 and 3 are ready to execute against the real EE02 board and the already-running production VPS whenever the developer chooses to start the multi-day discharge run - no laptop-availability blocker remains. `hardware/logtools.py`'s `from-journal` bridge and the updated `check-battery` are proven on fixtures only; the first real-world exercise of the pipeline happens when Task 2 of 05-01 actually runs the check-in command against a live `skypane-byos.service` journal.

---
*Phase: 05-low-battery-indicator (quick task 260827-vq3)*
*Completed: 2026-08-27*

## Self-Check: PASSED

All claimed files found on disk (`hardware/logtools.py`, `hardware/fixtures/battery-journal.log`, `hardware/BATTERY-RUN.md`, `stub-server/README.md`, `.planning/phases/05-low-battery-indicator/05-01-PLAN.md`, this SUMMARY). All claimed commit hashes (`f215e77`, `259dd2c`, `682acdc`) found in `git log --oneline --all`.
