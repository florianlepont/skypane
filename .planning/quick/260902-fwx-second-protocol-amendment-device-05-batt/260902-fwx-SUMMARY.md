---
phase: 05-low-battery-indicator
plan: 260902-fwx
subsystem: infra
tags: [sqlite, history_db, ssh, hardware-observation, device-05]

requires:
  - phase: 06 (06-11)
    provides: "server/history_db.py's device_health table, filled every 30s by skypane-poll.timer -> poll_loop.run_once() -> history_db.ingest_caddy_battery_log(), already running in production"
provides:
  - "hardware/logtools.py from-history-db subcommand bridging device_health JSON-Lines rows into check-battery's bracketed format"
  - "hardware/BATTERY-RUN.md's second dated Protocol Amendment moving the primary DEVICE-05 observation channel to history.db"
  - "05-01-PLAN.md's Tasks 2/3 re-scoped to the history.db channel with the daily check-in downgraded to optional"
affects: ["05-low-battery-indicator (Tasks 2/3, still deferred to end of project)"]

tech-stack:
  added: []
  patterns:
    - "Read-only SQLite URI (file:...?mode=ro) for an external reader against a continuously-written production database, with busy_timeout matching the writer's own discipline"
    - "JSON-Lines-in, bracketed-timestamp-out converter siblinged against an existing from-journal converter, sharing normalize_journal_timestamp() and parse_timestamp() unchanged"

key-files:
  created:
    - hardware/fixtures/battery-history-db.jsonl
  modified:
    - hardware/logtools.py
    - hardware/BATTERY-RUN.md
    - .planning/phases/05-low-battery-indicator/05-01-PLAN.md

key-decisions:
  - "Regenerating the whole device_health window on every read is unconditionally safe (keep-forever retention + INSERT OR IGNORE on UNIQUE(ts, battery_mv)), so no rotation-repair path was built for from-history-db, unlike from-journal's committed-history repair path"
  - "The daily check-in is downgraded from required to optional: under history.db nothing between check-ins is at risk, so a check-in is now purely for visibility, never for data preservation"
  - "from-journal is retained in full as the documented fallback rather than removed, so a history.db outage degrades the run instead of ending it"

requirements-completed: []

coverage:
  - id: D1
    description: "from-history-db subcommand converts device_health JSON-Lines rows into check-battery's bracketed format, proven against a committed fixture"
    verification:
      - kind: unit
        ref: "hardware/logtools.py selftest (battery-history-db case)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Converted output round-trips through the real server/history_db.py schema (init_schema + record_device_health) and matches battery-good.log byte-for-byte"
    verification:
      - kind: integration
        ref: "Task 1 <verify> block's round-trip subprocess check"
        status: pass
    human_judgment: false
  - id: D3
    description: "hardware/BATTERY-RUN.md amended a second time; pre-registered section and first amendment proven byte-identical to their committed selves"
    verification:
      - kind: other
        ref: "Task 2 <verify> block's against-HEAD diff comparison"
        status: pass
    human_judgment: false
  - id: D4
    description: "05-01-PLAN.md's Tasks 2/3 re-scoped to history.db while every physical step, threshold, gate attribute and resume-signal survives structurally"
    verification:
      - kind: other
        ref: "Task 3 <verify> block's per-task-block token/regex assertions"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-02
status: complete
---

# Phase 5 Quick Task 260902-fwx: Second Protocol Amendment (history.db Channel) Summary

**Bridged history.db's device_health table into check-battery's parser via a new from-history-db subcommand, amended BATTERY-RUN.md a second time to make it the primary DEVICE-05 observation channel, and re-scoped 05-01-PLAN.md's still-deferred Tasks 2/3 to it with the daily check-in downgraded from required to optional.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3
- **Files modified:** 3 (1 created, 3 modified — `hardware/fixtures/battery-history-db.jsonl` is new; `hardware/logtools.py`, `hardware/BATTERY-RUN.md`, `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` are edits)

## Accomplishments

- `hardware/logtools.py` gained a `from-history-db` subcommand that converts JSON-Lines `device_health` rows (as printed by a documented read-only SQLite query run over SSH on the VPS) into the exact bracketed `[ISO-8601]   telemetry: ...` shape `check-battery` already parses — proven twice: against a committed fixture (`hardware/fixtures/battery-history-db.jsonl`, `battery-good.log`'s telemetry re-rendered as device_health rows with four kinds of interleaved noise that must be dropped and counted) and via a round-trip through the real `server/history_db.py` schema (`init_schema()` + `record_device_health()`, read back through the documented `mode=ro` URI and SQL).
- `hardware/BATTERY-RUN.md` now carries a second dated `## Protocol Amendment` (2026-09-02, below the untouched 2026-08-27 first amendment) moving the primary observation channel from journald to `history.db`'s keep-forever `device_health` table, with journald retained as a documented fallback. The pre-registered section above `### Observation channel` and the entire first amendment are proven byte-identical to their committed selves by diffing against `HEAD`, not by review.
- `.planning/phases/05-low-battery-indicator/05-01-PLAN.md`'s Tasks 2 and 3 (both still deferred, unexecuted — Task 1 was already executed and untouched) are re-scoped throughout to the history.db channel: read_first, what-built, how-to-verify steps, action and acceptance_criteria all updated, while every physical pack-handling step, the four validity thresholds, the 21-day ceiling, the literal `SKYPANE_SLEEP_S=300`, and both checkpoint tasks' `type`/`gate` attributes and `<resume-signal>` bodies survive unchanged — verified structurally by the plan's own `<verify>` scripts, not by eye.

## Task Commits

Each task was committed atomically:

1. **Task 1: Bridge history.db's device_health rows into the format check-battery already parses** - `3e6c99b` (feat)
2. **Task 2: Amend the pre-registered protocol a second time, and prove mechanically that nothing about validity moved** - `cab01ac` (docs)
3. **Task 3: Re-scope 05-01's two hardware tasks to the channel that cannot lose the record** - `9a3ad09` (docs)

_No plan-metadata commit yet — STATE.md/ROADMAP.md updates and the final docs commit are handled by the orchestrator after this summary is written, per this quick task's constraints._

## Files Created/Modified

- `hardware/logtools.py` - Added `from-history-db` subcommand (with its module-comment-block-documented canonical remote SSH query and safety reasoning), extended `cmd_selftest()` with an eighth fixture case via a shared `_run_converted_battery_case()` helper, widened the AST-checked import allowlist to seven stdlib modules (`json` added; `sqlite3` deliberately not imported), and updated three docstrings/messages to name the third conversion path
- `hardware/fixtures/battery-history-db.jsonl` - New fixture: `battery-good.log`'s 31 telemetry readings re-rendered as `device_health` JSON-Lines rows (one with a `Z`-suffixed timestamp to exercise that normalization branch), interleaved with a blank line, a non-JSON shell-warning-shaped line, valid-JSON-but-not-an-object, and a null-`battery_mv` row — all four must be dropped and counted
- `hardware/BATTERY-RUN.md` - Rewrote `### Observation channel` into primary (history.db) + fallback (journald) paths with the canonical SSH query and its reasoning; added the second dated `## Protocol Amendment`; updated `## Daily Check-Ins` and `## Run Conditions` notes for the now-optional check-in and channel-availability reporting
- `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` - Re-scoped Tasks 2/3 (frontmatter's `must_haves.artifacts`, the objective's interruption paragraph, the artifacts table, the threat model's trust-boundary row and two mitigation entries, both tasks' read_first/what-built/how-to-verify/action/acceptance_criteria) to the history.db channel; Task 1 and both tasks' `<verify>` blocks, `<resume-signal>` bodies and gate attributes left untouched

## Decisions Made

- Regenerating the whole `device_health` window on every read is unconditionally safe (keep-forever retention, D-13, plus `INSERT OR IGNORE` on `UNIQUE(ts, battery_mv)`), so `from-history-db` deliberately has no rotation-repair path, unlike `from-journal`'s committed-history-plus-concatenation repair
- The daily check-in moves from required (data-preservation mechanism under journald's bounded retention) to optional (pure visibility under a keep-forever table) — a run with zero check-ins still yields a complete, gateable record
- `from-journal` is retained in full, not replaced, as the documented fallback for when `history.db` is unreachable — proven by the same selftest infrastructure that proves the primary path

## Deviations from Plan

None - plan executed exactly as written. All three tasks' `<verify>` blocks were run verbatim (wrapped in `bash -c`-equivalent execution to avoid zsh word-splitting differences on the unquoted multi-flag `$B` variable, per this project's established precedent from `260827-vq3-SUMMARY.md`) and passed without needing any correction to the plan's own verify commands.

## Issues Encountered

None. The plan's own verify scripts required running under `bash` rather than the default `zsh` shell (unquoted `$B="--interval-s 3600 ..."` word-splitting into separate argv tokens is a bash-ism zsh does not perform identically by default) — anticipated and handled per the constraints, not a defect in the plan.

The materialized `260902-fwx-PLAN.md` file (fetched from the git object store per this session's setup instructions, since it was absent from the working tree at agent start) carries two trailing stray lines (`</content>` and `</invoke>`) after its closing `</output>` tag. Confirmed via `git show <commit>:<path>` that these are genuinely part of the committed blob, not an artifact of the materialization step. They carry no directives and were treated as inert formatting noise, not acted upon.

## User Setup Required

None - no external service configuration required. The next physical action (charging the pack, connecting it, and running the still-deferred 05-01 Tasks 2/3) remains a manual, blocking, end-of-project step by design (DEVICE-05's deliberate deferral, per `.planning/STATE.md`).

## Next Phase Readiness

- `hardware/logtools.py`'s `from-history-db` bridge and `hardware/BATTERY-RUN.md`'s second amendment are ready for whenever the developer performs the still-deferred DEVICE-05 discharge run; the run itself remains unexecuted, unchanged from before this quick task, deliberately deferred to end-of-project per `.planning/STATE.md`.
- No blockers. `python3 hardware/logtools.py selftest` exits 0 covering all eight fixtures (three backoff, five battery — including both `battery-journal` and `battery-history-db`), confirming the tool the deferred run depends on is unbroken by this change.

---
*Phase: 05-low-battery-indicator (quick task 260902-fwx)*
*Completed: 2026-09-02*

## Self-Check: PASSED

All claimed files confirmed present on disk (`hardware/logtools.py`, `hardware/fixtures/battery-history-db.jsonl`, `hardware/BATTERY-RUN.md`, `.planning/phases/05-low-battery-indicator/05-01-PLAN.md`, this SUMMARY.md) and all three task commit hashes (`3e6c99b`, `cab01ac`, `9a3ad09`) confirmed present in `git log --oneline --all`.
