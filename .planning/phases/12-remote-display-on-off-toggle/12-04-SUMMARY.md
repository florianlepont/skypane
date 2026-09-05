---
phase: 12-remote-display-on-off-toggle
plan: 04
subsystem: server
tags: [poll-loop, e-ink, state-machine, display-toggle, quiet-hours]

# Dependency graph
requires:
  - phase: 12-01
    provides: "server/device_config.py's display_enabled registry field, DEFAULT_DISPLAY_ENABLED, DISPLAY_OFF_SLEEP_S, normalise_display_enabled()"
  - phase: 12-02
    provides: "server/plane/render.py's display_off canvas dispatch and DISPLAY_OFF_HEADING_TEXT/DISPLAY_OFF_BODY_TEXT constants"
provides:
  - "poll_state['hold_state'] tri-valued latch (None/'quiet_hours'/'display_off') with a legacy-aware read (_hold_state())"
  - "A single shared hold branch in run_once(), gated on display_enabled AND quiet-hours status, ahead of detect.load_geofence()/detect.poll_current_aircraft()"
  - "Render-once-on-entry guarded by was_hold is None, so a move between two hold states never triggers an e-ink refresh"
  - "Generalised exit path (hold_exited) that repaints the live board exactly once when the last hold condition clears, from either mechanism"
affects: [12-03, 12-05, any future phase touching server/poll_loop.py's run_once() or its hold-state contract]

tech-stack:
  added: []
  patterns:
    - "Tri-valued hold-state latch (None / kind-string) instead of per-mechanism booleans - 'am I holding' collapses to `was_hold is None` and stays correct for a future third hold mechanism with no code changes at the call sites"
    - "Legacy-aware state migration: a helper reads an old boolean shape when the new key is absent, and the first write retires the stale key - a pattern reusable for any future poll_state.json schema change on a live deployed device"

key-files:
  created: []
  modified:
    - server/poll_loop.py
    - server/test_poll_loop.py

key-decisions:
  - "Widened the existing quiet_hours_active latch into one tri-valued hold_state key rather than adding a sibling boolean (D-07-factoring, binding per 12-CONTEXT.md/12-04-PLAN.md) - keeps 'entering a hold' a single test that generalises to a third mechanism without touching a line"
  - "The display-off gate and the quiet-hours gate share one branch, computed from a single per-cycle device_cfg read, and sit before detect.load_geofence()/detect.poll_current_aircraft() (D-06) - an off period has no scheduled end, so this placement matters more than it did for quiet hours alone"
  - "Render guard is was_hold is None, never was_hold != hold_kind, so a hold-to-hold transition in either direction costs zero e-ink refreshes (D-07) - proven by an executed negative control"
  - "12-04-PLAN.md's check-5 'direction two' as literally worded (window ending while the toggle stays off) cannot change hold_kind under D-05's display-axis precedence, so it cannot exercise the was_hold-is-None guard; replaced with the true reverse transition (toggle switched back on while a window is already active, display_off -> quiet_hours) so the negative control's 'both cases must fail' requirement is genuinely satisfied - see Deviations"

requirements-completed: []

coverage:
  - id: D1
    description: "Display-off gate sits before detect.load_geofence()/poll_current_aircraft() - an off period issues zero upstream ADS-B queries"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#Task 1 AST-order assertion (structural) + check 40 (behavioural: detect stubs fail the check if called)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The display toggle wins on what the panel shows, even during an active quiet-hours window (D-05 display axis)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#check 41 (the overlap - toggle off AND active window renders DISPLAY OFF, canvas byte-identity asserted)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A hold is entered with exactly one render, held silently thereafter, and a hold-to-hold transition in either direction costs zero refreshes (D-07)"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#checks 38-39, 42-43 (entry-renders-once, hold-is-noop across a battery transition, both hold-to-hold directions) + executed negative control (was_hold != hold_kind makes checks 42/43 fail with a changed panel.bin)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Clearing all hold conditions repaints the live board exactly once, with no intermediate transition screen"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#check 44 (display-side mirror of the Phase 10 window-exit regression guard)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A Phase-10-shaped poll_state.json (legacy quiet_hours_active boolean, no hold_state key) upgrades without a spurious repaint and loses its stale key on disk"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#check 45 (asserts on-disk JSON, not just in-memory state)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The 30-second systemd cadence is unchanged; deploy/ is untouched"
    verification:
      - kind: other
        ref: "git diff --quiet deploy/"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-09-05
status: complete
---

# Phase 12 Plan 04: Display-Off Gate + Hold-State Generalisation Summary

**Widened poll_loop.py's Phase 10 quiet-hours latch into a tri-valued `hold_state` (`None`/`"quiet_hours"`/`"display_off"`) shared by one hold branch ahead of detection, so the manual display toggle and the scheduled window can never both refresh the panel for a silent transition between them.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-05
- **Tasks:** 3
- **Files modified:** 2 (`server/poll_loop.py`, `server/test_poll_loop.py`)

## Accomplishments
- `_hold_state(poll_state)` helper: reads the generalised `hold_state` key, falls back to the legacy `quiet_hours_active` boolean for exactly one cycle per upgraded install, never raises on an unrecognised shape
- One shared hold branch in `run_once()`, computed from a single per-cycle `device_cfg` read, gated `if hold_kind is not None:` and still sitting before `detect.load_geofence()`/`detect.poll_current_aircraft()` (D-06)
- Render-once-on-entry guarded by `was_hold is None` (not `was_hold != hold_kind`), making a move between two hold states silent in both directions (D-07) - proven by an executed negative control
- Generalised exit path: `hold_exited` replaces the quiet-hours-specific carrier at all five use sites (the held branch's re-render gate, two save-state conditions, and the shared log line), and clears/retires the legacy key on the normal path too
- `server/test_poll_loop.py` extended from 51 to 60 checks: two Phase 10 checks retargeted to the generalised key, nine new checks covering display-off entry/hold/detection-skip/overlap/both hold-to-hold directions/exit/migration/inert-toggle

## Task Commits

1. **Task 1: Generalise the latch and rewrite the gate as one shared hold branch, ahead of detection** - `96786f2` (feat)
2. **Task 2: Generalise the exit path and rename the quiet-hours-specific carrier** - `41c9782` (refactor)
3. **Task 3: Extend server/test_poll_loop.py, including the overlap and hold-to-hold transitions** - `86db828` (test)

**Plan metadata:** committed separately by the orchestrator (SUMMARY.md/STATE.md/ROADMAP.md excluded from this plan's per-task commits per the constraints).

## Files Created/Modified
- `server/poll_loop.py` - `_hold_state()` helper; the gate now computes `hold_kind` from `display_enabled` and `quiet_remaining` off a single `device_cfg` read; the hold branch renders `hold_kind` via `render.build_canvas()`, persists it to `poll_state["hold_state"]`, and retires the legacy key; the normal-path exit reads `_hold_state()` into `hold_exited` and clears the latch; `run_once()`'s docstring rewritten to describe both hold mechanisms
- `server/test_poll_loop.py` - checks 31/35 retargeted to assert `hold_state` instead of the retired `quiet_hours_active` boolean; nine new checks (38-46) for the display-off gate, the overlap, both D-07 hold-to-hold directions, the exit repaint, the legacy migration, and the inert-toggle no-op; `EXPECTED_CHECK_COUNT` bumped 51 -> 60 with a tally comment

## Decisions Made
- **D-07-factoring honored as binding:** widened the existing latch into one tri-valued key rather than adding a sibling boolean, per 12-CONTEXT.md's explicit reasoning (a two-boolean design makes "am I holding?" a compound test every future mechanism must remember to extend).
- **Gate ordering (D-06) preserved and extended:** both gate decisions come from the single `device_cfg` read at the top of `run_once()`, and the shared hold branch stays ahead of any `detect.*` call. The plan's own AST-order verification script (Task 1) enforces this structurally, and check 40 enforces it behaviourally by failing if `detect.poll_current_aircraft`/`detect.load_geofence` are ever called during a display-off hold.
- **Migration is legacy-aware, not merely tolerant:** `_hold_state()` explicitly branches on `"hold_state" in poll_state` before falling back to the boolean, so an absent key (fresh install) and a present-but-unrecognised key (hand-edit/crash) both correctly degrade to `None`, while a genuinely legacy Phase 10 file is read as `"quiet_hours"` for exactly one cycle.
- **Check-5 "direction two" redesigned (see Deviations below).**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test bug] Redesigned check 43 ("D-07 hold-to-hold, direction two") to actually exercise the negative control**
- **Found during:** Task 3, while running the required negative control (plan action text: "confirm both check-5 cases fail with a changed `panel.bin`")
- **Issue:** The plan's literal wording for direction two - "toggle off with a window also active (off screen up), then the window ends while the toggle is still off" - cannot, by construction of D-05's display-axis precedence, ever change `hold_kind`. Because `display_enabled=False` always resolves `hold_kind` to `"display_off"` regardless of whether a quiet-hours window is active, starting or ending, a window ending while the toggle stays off is not a hold-to-hold *transition* at all - `hold_kind` is `"display_off"` on both the cycle before and the cycle after. I verified this empirically: with the check implemented exactly as worded, forcing the render guard from `was_hold is None` to `was_hold != hold_kind` left it passing unchanged (only the direction-one check failed, 59/60 not the required both-fail-58/60).
- **Fix:** Replaced the check with the true reverse transition that actually exists in the state space: `display_off -> quiet_hours`, produced by switching the toggle back on while a quiet-hours window is simultaneously active (rather than by a window edge with the toggle held constant). This is the real second direction the `was_hold is None` guard has to hold for, and it correctly fails under the negative control (confirmed: both direction-one and direction-two checks fail, 58/60, with `panel.bin` changed in each case).
- **Files modified:** `server/test_poll_loop.py` (check 43 only; no `poll_loop.py` change - the gate logic itself was already correct per D-05/D-07, only the test scenario was unable to observe it)
- **Verification:** Negative control run twice - once against the original (as-worded) direction-two scenario (did not fail, confirming the gap), once against the corrected scenario (failed as required, 58/60, both hold-to-hold checks in the failure list). Reverted to the correct guard afterward; harness green at 60/60.
- **Committed in:** `86db828` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 test-design bug caught by the plan's own required negative control)
**Impact on plan:** No production code changed as a result - the deviation is confined to the test file. The corrected check is a stronger, more accurate proof of D-07 than the originally-worded one would have been, since it actually demonstrates the guard is load-bearing in both directions rather than passing vacuously.

## Issues Encountered
None beyond the deviation above - the plan's design and code guidance (D-05/D-06/D-07, the `_hold_state()` migration contract, the exact dispatch-name reuse between `hold_kind` and `render.build_canvas()`'s state argument) all held up exactly as specified.

## User Setup Required
None - no external service configuration required. This plan touches only `server/poll_loop.py` and its test harness; no new dependencies, no config surface beyond what 12-01/12-02 already added.

## Next Phase Readiness
- `poll_loop.py`'s hold-state contract (`poll_state["hold_state"]`, `_hold_state()`, `hold_kind`/`hold_exited` naming) is stable and ready for 12-05 (companion Settings toggle) to write `display_enabled` through the existing `device_config.save_device_config()` path with no further poll-loop changes needed.
- `stub-server/byos_server.py`'s sleep-duration axis (plan 12-03, `max(300, quiet_hours_remaining)`) is fully independent of this plan's display-axis gate and was not touched here, matching D-05's explicit two-axis separation.
- No blockers. The self-check below confirms every file and commit hash claimed above actually exists.

---
*Phase: 12-remote-display-on-off-toggle*
*Completed: 2026-09-05*

## Self-Check: PASSED

All claimed files exist (`server/poll_loop.py`, `server/test_poll_loop.py`,
this SUMMARY.md) and all claimed commit hashes (`96786f2`, `41c9782`,
`86db828`) are present in `git log --oneline --all`.
