---
phase: 04-low-battery-indicator
plan: 01
subsystem: hardware-bringup
tags: [battery, deep-sleep, stdlib-python, log-verification, d-07, pre-registration]

# Dependency graph
requires:
  - phase: 01-07
    provides: hardware/logtools.py's stamp/check-backoff/selftest pattern and house style (one PASS/FAIL line per check, a summary line, meaningful exit code) - check-battery extends the same file rather than starting a new one
provides:
  - "hardware/logtools.py check-battery subcommand - gated discharge-run analysis (7 possible validity gates, depending on which optional flags are supplied) plus an ungated --status daily check-in mode that never fails"
  - "hardware/fixtures/{battery-good,battery-gap,battery-flat-mv}.log - proven-against fixtures: a healthy ~30h discharge (accepted), the same discharge with a 6h sleeping-host hole punched in (rejected on coverage + max-gap), and a full-cadence run whose millivolts never fall (rejected on the mv-drop gate)"
  - "hardware/logtools.py selftest, extended to prove all six fixtures (3 backoff + 3 battery) before any hardware use"
  - "hardware/BATTERY-RUN.md ## Run Protocol (pre-registered) - thresholds, ceiling, capacity and D-07's exact division, committed before the battery pack was ever connected"
affects: ["04-01 Task 2 (battery connection + multi-day unattended run - not started this session, gated on explicit human action) and Task 3 (post-mortem readout and write-up)"]

tech-stack:
  added: []
  patterns:
    - "check-battery's optional gates (expect-depleted, boot reconciliation) are appended to the results list only when their governing flag/arguments are supplied, so the summary line's N/N denominator legitimately varies by invocation - same shape as check-backoff's --expect-persist/--expect-reset optional checks in 01-07."
    - "Windowed opening/closing means (first/last tenth of samples) rather than single first/last readings, because one instantaneous voltage sample taken mid-radio-transmission is noisy enough to mislead on its own."
    - "--status mode is a structurally separate code path from gated mode, not gated-mode-with-suppressed-exit-code: it never constructs a CheckResult, so no PASS/FAIL substring can appear in its output even by accident, and it degrades gracefully (a one-line notice, still exit 0) when there isn't yet enough data to compute derived figures."
    - "Projection band computed as sorted(pair) rather than a fixed (lower, upper) assignment, since which model (per-wake vs standing-leakage) predicts the smaller number depends on whether the candidate interval is shorter or longer than the run's own interval - this fixture set uses a 3600s run interval with 300s/900s/3600s candidates, so two of the three bands have the per-wake model on the low side."

key-files:
  created:
    - hardware/fixtures/battery-good.log
    - hardware/fixtures/battery-gap.log
    - hardware/fixtures/battery-flat-mv.log
    - hardware/BATTERY-RUN.md
  modified:
    - hardware/logtools.py

key-decisions:
  - "Used a 3.7V/3000mAh capacity figure transcribed directly from hardware/BOM.md's Kubii LiPo pack line, not a rounder number, since Task 1's own point is that the pre-registered protocol cites the real purchased-pack rating rather than a remembered one."
  - "Fixture cadence set to 3600s (hourly) over a ~30h span (31 samples) rather than the run's real 300s cadence, per the plan's own instruction, keeping each fixture around thirty lines instead of several thousand while still exercising every gate identically via --interval-s 3600 --min-days 1 at check time."
  - "battery-flat-mv.log's millivolts were given a small sawtooth oscillation (4180-4190, formula 4180 + i%11) rather than a perfectly flat constant, to prove the mv-drop gate catches noise-sized non-decline and not just a literal unchanging value - the windowed-mean drop still comes out negative (-6mV), well under the 100mV threshold."

patterns-established:
  - "A checker's optional gates are proven both ways (present-and-triggered, absent-and-skipped) before the checker is ever pointed at a real run - continuing the discipline plan 01-02 set for its integrity gate and 01-07 set for its backoff-curve gate."

requirements-completed: []

# DEVICE-05 is not yet complete - only Task 1 (pre-registration + checker)
# of this 3-task plan has run. Requirements will be marked complete when
# Task 3 (post-mortem readout + Verdict) closes the plan.

coverage:
  - id: D1
    description: "check-battery, proven on fixtures, correctly accepts a healthy discharge and rejects both a sleeping-host gap and a phantom-USB-power (flat-millivolt) run, before ever being pointed at real hardware"
    verification:
      - kind: other
        ref: "python3 hardware/logtools.py selftest - exits 0, PASS on all 6 fixtures (3 backoff carried over from 01-07 + 3 new battery fixtures)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The D-07 run protocol (rated capacity, 300s interval, validity thresholds, 21-day ceiling, exact division) is committed to git before the battery pack is connected"
    verification:
      - kind: other
        ref: "hardware/BATTERY-RUN.md ## Run Protocol (pre-registered) exists, cites D-07, names 3000 mAh (transcribed from hardware/BOM.md), names the 300s interval and the 21-day ceiling; committed in c54024c prior to any battery connection"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-08-26
status: in-progress
---

# Phase 4 Plan 01 Task 1: Battery Checker Pre-Registration Summary

**Before the battery pack was ever connected, `hardware/logtools.py check-battery` was built and proven on three fixtures to accept a healthy discharge and reject both a sleeping-host gap and a phantom-USB-power run, and `hardware/BATTERY-RUN.md` now carries the D-07 protocol's thresholds, ceiling and exact division, committed to git while the answer was still unknown.**

**This SUMMARY covers Task 1 of 3 only.** Task 2 (charging the pack, pulling the USB cable, and running the device unattended for days) is a `checkpoint:human-action` gated on explicit human action and real elapsed time — it was deliberately not started this session, per this session's own instructions. Task 3 (post-mortem readout and the `## Verdict` write-up) depends on Task 2 having actually run. `DEVICE-05` and the plan's overall success criteria are **not yet met**; ROADMAP.md and REQUIREMENTS.md are intentionally left unmarked for this plan.

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-26 (this session)
- **Completed (Task 1 only):** 2026-08-26
- **Tasks:** 1 of 3 complete
- **Files modified:** 5 (hardware/logtools.py + 3 new fixtures + hardware/BATTERY-RUN.md)

## Accomplishments

- `hardware/logtools.py` gained a `check-battery` subcommand: parses the stub server's `X-Battery-Mv` telemetry out of a stamped stdout capture (regex `X-Battery-Mv\D*(\d+)`, matched against the real format captured in `hardware/logs/backoff-baseline-server.log`), computes span, coverage, max gap, windowed opening/closing millivolt means and drop, cycle counts (nominal/observed/device-boot-delta), mAh/day, mAh/cycle, and a two-ended projection band for 300/900/3600s candidate wake intervals - never a point estimate, since a single-cadence run cannot separate per-wake energy from standing leakage.
- Seven possible validity gates implemented, five always active (timestamps+min-polls, min-days span, min-coverage, max-gap-intervals, min-mv-drop) and two conditional on flags (`--expect-depleted`'s cutoff-mv check; the boot-counter reconciliation check when both `--boot-start`/`--boot-end` are supplied).
- A fully separate `--status` code path: no `CheckResult` objects are ever constructed, so no PASS/FAIL line can appear in its output even by accident; it degrades to a one-line notice (still exit 0) if there isn't yet enough data.
- Three new fixtures under `hardware/fixtures/`, at an hourly cadence over a ~30h span (~31 lines each): `battery-good.log` (smooth 4150mV->3150mV decline, accepted under every gate including `--expect-depleted`), `battery-gap.log` (same decline with hours 14-18 removed, producing a 6h hole - rejected on both the coverage gate and the max-gap gate), `battery-flat-mv.log` (full cadence, millivolts oscillating 4180-4190 with a net *negative* windowed drop - rejected on the mv-drop gate and, since it's clearly not depleted, also on `--expect-depleted`).
- `selftest` extended from 3 to 6 fixture assertions (3 backoff carried over unchanged from 01-07, 3 new battery cases), exits 0 only when all six outcomes match expectation.
- No import added beyond the six `hardware/logtools.py` already allowed (`argparse`, `datetime`, `os`, `re`, `subprocess`, `sys`) - verified by re-running 01-07's AST import scan unchanged.
- `hardware/BATTERY-RUN.md` created with all nine required section headings; `## Run Protocol (pre-registered)` is filled in now (capacity 3000mAh transcribed from `hardware/BOM.md`, 300s server interval, the four gate thresholds, a 21-day ceiling, D-07's exact division, and an explicit statement that both a MEASURED and a CENSORED outcome are valid results). The remaining eight sections are stubbed with a one-line pointer to the task (2 or 3) that fills them.

## Task Commits

1. **Task 1: Pre-register the measurement, and build a checker that rejects a sleeping host and a phantom USB cable - before the battery is connected** - `c54024c` (feat)

Tasks 2 and 3 not started this session (Task 2 is a blocking human-action checkpoint requiring a multi-day real-time unattended run).

**No plan-metadata commit yet** - this SUMMARY and the STATE.md update below are committed separately since the plan itself is not complete.

## Files Created/Modified

- `hardware/logtools.py` - added `check-battery` subcommand (constants, `BatteryPoll`, `load_battery_polls`, `compute_battery_stats`, seven check functions, `print_battery_derived`, `cmd_check_battery`), extended `cmd_selftest` and `build_parser`/`main` dispatch
- `hardware/fixtures/battery-good.log` - synthetic healthy ~30h discharge, hourly cadence, must be accepted
- `hardware/fixtures/battery-gap.log` - same discharge with a 6h sleeping-host hole, must be rejected
- `hardware/fixtures/battery-flat-mv.log` - full-cadence run whose millivolts never fall, must be rejected
- `hardware/BATTERY-RUN.md` - new file; `## Run Protocol (pre-registered)` filled, 8 remaining sections stubbed for Tasks 2/3

## Decisions Made

See `key-decisions` in frontmatter above. The central decision this session: transcribe the real 3000mAh pack rating from `hardware/BOM.md` into the pre-registered protocol rather than a placeholder, and pre-register all four validity thresholds and the 21-day ceiling before the battery is ever connected, so none of them can be tuned once the run's outcome is known.

## Deviations from Plan

None. Task 1 was executed exactly as written: no import added beyond the allowed six, the millivolt parser was written against the real captured server-log format rather than an imagined one, all three fixtures were written at the specified hourly/~30h cadence, `selftest` was extended rather than replaced, and `hardware/BATTERY-RUN.md`'s pre-registered protocol section states plainly that both a MEASURED and a CENSORED outcome are valid results.

## Issues Encountered

None. All automated verification commands from the plan's `<verify>` block pass end-to-end under bash (the interactive shell in this environment is zsh, which does not word-split an unquoted `$B` variable the way the verify script's own multi-flag `$B` pattern assumes - re-running the identical commands via `bash -c '...'` confirms this is a shell-flavor artifact of ad hoc testing, not a defect in `logtools.py` or the verify script itself, which the orchestrator will run under bash).

## User Setup Required

None for Task 1 (fully autonomous, no hardware or battery involved).

**Before Task 2 can start**, per this plan's own `<how-to-verify>` steps: confirm the laptop can stay awake and on the LAN for up to 21 days, consider a DHCP reservation, set Energy Saver to never sleep, confirm the battery pack's integrated protection circuit from the BOM listing, and re-check polarity against `hardware/BOM.md`'s `## Battery Connector Verification` section before the pack is ever connected for the first time in this plan (01-06/01-07 deliberately left it disconnected).

## Next Phase Readiness

**Task 1 of 04-01 is complete and committed (`c54024c`).** `check-battery` is proven on fixtures and `hardware/BATTERY-RUN.md`'s protocol is pre-registered. **Tasks 2 and 3 remain** - Task 2 is a `checkpoint:human-action` (gate: `blocking-human`) requiring the developer to charge the pack, disconnect USB, and let the device run unattended for days to weeks; Task 3 depends on Task 2 having produced a real captured log. This plan, and therefore `DEVICE-05` and Phase 4's battery-measurement success criterion, remain open until both later tasks execute. Moved here from Phase 1 (was 01-08) on 2026-08-26 per user request - see STATE.md's Roadmap Evolution note. No other plan is blocked on this one continuing immediately.

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Task 1 completed: 2026-08-26 - plan remains open (2 tasks outstanding)*
