---
phase: 10-scheduled-quiet-hours
plan: 04
subsystem: poll-loop
tags: [python, systemd-oneshot, quiet-hours, render-gating]

# Dependency graph
requires:
  - phase: 10-scheduled-quiet-hours (plan 01)
    provides: "device_config.py's quiet_hours_status()/load_device_config() six-key registry"
  - phase: 10-scheduled-quiet-hours (plan 02)
    provides: "render.py's build_canvas(None, 'quiet_hours', quiet_hours_until=...) render state"
provides:
  - "server/poll_loop.py's quiet-hours early-return gate in run_once() (render once at entry, hold, exit-repaint)"
  - "poll_state.json's quiet_hours_active flag and the quiet_hours_exited window-exit signal"
affects: [11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Once-per-cycle device_cfg read reused for the quiet-hours decision, never a second load_device_config() call"
    - "now_s() (the module's existing clock seam) threaded into device_config.quiet_hours_status(), not datetime.now()"
    - "Render-once-then-hold state machine driven entirely by one poll_state.json boolean, since the oneshot has no in-process memory"

key-files:
  created: []
  modified:
    - server/poll_loop.py
    - server/test_poll_loop.py

key-decisions:
  - "The in-window early return sits BEFORE detect.load_geofence()/detect.poll_current_aircraft() - a cycle inside the window never touches the ADS-B aggregators (10-RESEARCH.md Pitfall 4)"
  - "Source fault is carried forward via _last_source_fault() rather than re-classified during the window, since no provider was queried this cycle to classify"
  - "Battery hysteresis is still computed every in-window cycle (so the icon can appear on the QUIET HOURS screen), but a battery transition mid-window never forces a repaint - nothing rendered mid-window can reach the glass anyway"
  - "_record_history() is still called on every in-window cycle so history_db.META_LAST_PIPELINE_RUN keeps advancing, preventing a false companion-Health 'pipeline stale' anomaly across an overnight window"
  - "Window exit is detected as a side effect of reaching the normal (non-early-return) path with poll_state['quiet_hours_active'] still True - not a separate timer or explicit state - and forces exactly one repaint from whichever branch (held or flight-detected) would otherwise decide the panel"

patterns-established:
  - "quiet_hours_exited threaded into every branch that doesn't already repaint unconditionally, as one more OR term on both the re-render gate and the save-state gate - never a separate code path"

requirements-completed: []

coverage:
  - id: D1
    description: "The first poll cycle inside an enabled quiet-hours window renders the QUIET HOURS canvas exactly once and sets poll_state['quiet_hours_active'] to True"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#window entry renders the QUIET HOURS canvas exactly once and persists quiet_hours_active=True"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#the rendered panel is exactly render.build_canvas(None, 'quiet_hours', quiet_hours_until='07:00')"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every subsequent cycle still inside the window is a no-op for the panel"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#a second in-window cycle is a no-op - panel_changed is False and panel.bin's bytes are unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "A cycle inside the window never calls detect.poll_current_aircraft() or detect.load_geofence()"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#an in-window cycle on the live path never calls detect.poll_current_aircraft or detect.load_geofence"
        status: pass
    human_judgment: false
  - id: D4
    description: "The first cycle after the window ends resumes normal detection and repaints the live board with no intermediate transition screen, including from the held branch"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#REGRESSION GUARD: the first cycle after window exit repaints the held live board and clears quiet_hours_active"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#the exit cycle's returned state is the ordinary held value, never 'quiet_hours' and never a new third state"
        status: pass
      - kind: other
        ref: "Negative control: temporarily removing 'or quiet_hours_exited' from the held branch's re-render gate drops the harness from 51/51 to 50/51, failing with the expected 'panel_changed=False, expected True' message on the regression-guard check"
        status: pass
    human_judgment: false
  - id: D5
    description: "A disabled quiet_hours_enabled flag makes the whole feature inert regardless of stored start/end times"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#quiet_hours_enabled=False takes the ordinary detection path regardless of stored start/end times"
        status: pass
    human_judgment: false
  - id: D6
    description: "poll_loop.py's own 30-second systemd cadence and deploy/ are completely unchanged - only what a cycle renders is gated, never whether it runs"
    verification:
      - kind: other
        ref: "git diff --quiet deploy/ confirmed no change after both task commits"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-03
status: complete
---

# Phase 10 Plan 04: Quiet-Hours Poll-Loop Render Gate Summary

**`server/poll_loop.py`'s `run_once()` now takes an early-return branch that renders the QUIET HOURS screen exactly once at window entry, holds silently for the rest of the window without ever querying the ADS-B aggregators, and forces one repaint of the live board on the first cycle after the window ends.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-03T21:55Z (approx.)
- **Completed:** 2026-09-03T22:22Z
- **Tasks:** 2/2 completed
- **Files modified:** 2 (`server/poll_loop.py`, `server/test_poll_loop.py`)

## Accomplishments

- Added the in-window early-return gate to `run_once()`: the once-per-cycle `device_cfg` read now also binds `device_config.quiet_hours_status(device_cfg, now_s())`, and when the cycle falls inside an enabled window, the function returns before `detect.load_geofence()`/`detect.poll_current_aircraft()` are ever called (10-RESEARCH.md Pitfall 4). The branch renders `render.build_canvas(None, "quiet_hours", quiet_hours_until=..., ...)` exactly once on entry (`poll_state["quiet_hours_active"]` flips False→True), holds silently on every later in-window cycle, carries the battery-low icon via the same hysteresis computation the main path uses, carries the previously-persisted source-fault flag forward (never re-classified, since nothing was queried), and still calls `_record_history()` every cycle so `history_db.META_LAST_PIPELINE_RUN` keeps advancing.
- Added window-exit detection to the normal path: reaching `poll_state = load_poll_state(state_dir)` with `quiet_hours_active` still `True` means the window just ended. The flag is cleared immediately, and `quiet_hours_exited` is threaded into the held branch's re-render gate (`... or quiet_hours_exited`), both branches' save-state gates, and the shared per-cycle log line, so the first post-window cycle always forces one repaint of the real live board - never a new "waking up" transition screen (D-07) - and the cleared flag survives the systemd oneshot's process boundary.
- Extended `server/test_poll_loop.py` with 7 new checks (`EXPECTED_CHECK_COUNT` 44 → 51) covering: entry renders once and persists the flag; a second in-window cycle is a byte-identical no-op; the rendered panel exactly matches `render.build_canvas(None, "quiet_hours", quiet_hours_until="07:00")`; the live path never touches `detect.poll_current_aircraft`/`detect.load_geofence` while in-window; the window-exit regression guard (detect a flight before the window, enter the window, exit with nothing newly detected, assert the stale QUIET HOURS image is replaced and the flag clears); the exit cycle's returned `state` is the ordinary held value, never `"quiet_hours"`; and a disabled `quiet_hours_enabled` flag takes the ordinary detection path regardless of stored times.
- Ran the required negative control: temporarily dropping `or quiet_hours_exited` from the held branch's re-render gate drops the harness from 51/51 to 50/51, failing exactly the regression-guard check with `"panel_changed=False, expected True"` - proving the guard actually exercises the fix rather than passing vacuously.
- Full suite: `server/.venv/bin/python3 server/test_poll_loop.py` → 51/51; `scripts/run-all-tests.sh` → `Result: PASS` (16/16 harnesses); the only non-zero note is the pre-existing, already-documented macOS Pillow/FreeType `panel.bin` digest mismatch (Linux/CI-authoritative, unrelated to this plan).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the in-window early-return gate to run_once()** - `f3bd3f3` (feat)
2. **Task 2: Repaint the live board on window exit, and cover the whole gate** - `e506caf` (feat)

**Plan metadata:** this SUMMARY + STATE.md/ROADMAP.md commit follows separately per the final_commit step.

## Files Created/Modified

- `server/poll_loop.py` - `run_once()`'s new quiet-hours early-return branch (before `detect.load_geofence()`); the `quiet_hours_exited` window-exit binding, threaded into the held branch's re-render gate, both branches' save-state conditions, and the shared log line; docstring paragraph naming the new gate's "render once at entry, then hold" rule
- `server/test_poll_loop.py` - 7 new `check(...)` calls covering entry, hold, canvas byte-identity, detection-skip, the exit-repaint regression guard, no-transition-screen, and the disabled-flag case; `EXPECTED_CHECK_COUNT` 44 → 51

## Decisions Made

- The quiet-hours decision is computed from the SAME `device_cfg` read the main path already makes once per cycle - never a second `load_device_config()` call - for the identical mid-cycle-save race reason that read's own existing comment documents.
- `now_s()` (not `datetime.now()`) is passed into `device_config.quiet_hours_status()`, so the poll-loop test harness's fake clock drives the quiet-hours arithmetic deterministically, exactly like every other pacing/staleness decision in this module.
- Source fault is carried forward via `_last_source_fault()` during the window rather than re-classified, since no provider was queried this cycle - classifying "no fault" from an empty diagnostics dict would silently clear a real ongoing outage overnight, and inventing a fault from nothing queried would be equally wrong.
- A battery transition mid-window updates the persisted hysteresis state but never triggers a repaint - nothing rendered mid-window can ever reach the glass, unlike the held branch's source-fault/battery re-render gate on the normal path.
- Window exit is detected implicitly (reaching the normal path with the flag still `True`) rather than via a separate timer or explicit "just closed" event - simpler and consistent with this module's existing "state lives in poll_state.json, derived from a diff against the prior cycle" style (e.g. `battery_changed`, `queue_dirty`).

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria commands were run verbatim and all passed; `git diff --name-only` after each commit matched the plan's declared file list exactly. One in-flight self-correction during Task 1: the docstring paragraph originally added referenced `device_config.quiet_hours_status()` by name, which caused `grep -n 'quiet_hours_status'` to match twice instead of the required exactly-once (the acceptance criterion's own count). Reworded the docstring to describe the same behaviour without repeating the literal function name before committing - not a plan deviation, just a self-caught acceptance-criterion violation fixed before the commit landed.

## Issues Encountered

Mid-session tooling mistake (self-caught, no lasting effect): while performing Task 2's required negative-control run, `git checkout -- server/poll_loop.py` was used to restore the file after temporarily mutating it - this reverted to the last COMMIT (Task 1's), silently discarding the not-yet-committed Task 2 edits. Caught immediately via `grep -c quiet_hours_exited` returning 0 instead of the expected count; all Task 2 edits were reapplied from the already-reviewed diff, re-verified (51/51, ruff clean, acceptance criteria re-run), and the negative control was redone using a file-copy backup/restore instead of `git checkout` to avoid the same mistake twice. No incorrect state was ever committed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10's server-side quiet-hours mechanism (config registry, render state, byos_server sleep extension, and now the poll-loop gate) is complete across plans 10-01 through 10-04. Plan 10-05 (companion `config_page.py` checkbox UI) is the only remaining plan in this phase and has no dependency on this plan's internals beyond the already-landed `device_config.py` registry fields.
- `10-CONTEXT.md`'s Integration Points named `byos_server.py`'s `/display` handler as a shared touchpoint with Phase 11; this plan does not touch that file. Plan 10-03 (byos_server.py's vendored sleep extension) landed before this plan, confirmed via `git log`.

## Self-Check: PASSED

- FOUND: server/poll_loop.py
- FOUND: server/test_poll_loop.py
- FOUND: .planning/phases/10-scheduled-quiet-hours/10-04-SUMMARY.md
- FOUND commit: f3bd3f3
- FOUND commit: e506caf

---
*Phase: 10-scheduled-quiet-hours*
*Completed: 2026-09-03*
