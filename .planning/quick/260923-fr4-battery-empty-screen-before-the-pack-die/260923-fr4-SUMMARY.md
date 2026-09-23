---
phase: quick-260923-fr4
plan: 01
subsystem: firmware-server-integration
tags: [battery, e-ink, hysteresis, byos-protocol, poll-loop, wake-monitoring, ntfy]

requires:
  - phase: "12 (display-off / quiet-hours hold screens)"
    provides: "_build_dimmed_hold_canvas() shared composition, _HOLD_KINDS latch, byos display_off_sleep_s()/quiet_hours_sleep_s() composition chain"
provides:
  - "BATTERY EMPTY hold screen (render.py), drawn through the same dimmed composition as DISPLAY OFF / QUIET HOURS"
  - "server/poll_loop.py battery-critical latch (3300 mV enter / 3700 mV recover), top hold priority, single park render"
  - "server/wake.py battery_critical-aware effective_wake_interval_s()/next_wake_status()/next_wake_at_iso(), read_battery_critical()"
  - "stub-server/byos_server.py battery_critical_sleep_s() sleep_s pin with recovery anticipation"
  - "companion frame strip / flash text no longer false-alarms 'late' while parked"
affects: [poll_loop, byos_server, companion_layout, companion_app, render, wake, device_config]

tech-stack:
  added: []
  patterns:
    - "Latch computed once per cycle from a single load_battery_state() read, persisted in poll_state.json, read fail-open by every downstream consumer (poll_loop, byos, wake, companion)"
    - "Recovery anticipation: a sleep_s composer reads the SAME request's fresh signal (X-Battery-Mv) to avoid handing out a stale long sleep before the writer's own up-to-30s-delayed latch clear lands"

key-files:
  created:
    - .planning/quick/260923-fr4-battery-empty-screen-before-the-pack-die/battery-empty-preview.png
    - .planning/quick/260923-fr4-battery-empty-screen-before-the-pack-die/hold-screens-side-by-side.png
  modified:
    - server/plane/render.py
    - server/poll_loop.py
    - server/wake.py
    - server/device_config.py
    - stub-server/byos_server.py
    - companion/app.py
    - companion/layout.py
    - companion/wake.py
    - ARCHITECTURE.md
    - hardware/BATTERY-RUN.md

key-decisions:
  - "Hold priority is battery_empty, then display_off, then quiet_hours — a flat pack overrides both the operator's toggle and any standing schedule"
  - "BATTERY EMPTY ignores theme_id/source_fault/battery_low entirely so the parked image's bytes (and hash) never change for the whole episode"
  - "byos anticipates recovery within the SAME request that reports it (fresh X-Battery-Mv >= 3700), rather than waiting for poll_loop's own up-to-30s-delayed latch clear"
  - "Companion fix scoped to the frame strip and flash text only (companion/app.py, companion/layout.py), matching the plan's declared file list — Home's Frame tile and Health's Device tile were deliberately left untouched"

requirements-completed: [QUICK-260923-fr4]

coverage:
  - id: D1
    description: "BATTERY EMPTY hold screen: locked copy, upright hollow-battery glyph, shared dimmed composition, byte-stable across badges/theme"
    verification:
      - kind: unit
        ref: "server/test_render.py (140/140, +6 new checks)"
        status: pass
      - kind: manual_procedural
        ref: "battery-empty-preview.png, hold-screens-side-by-side.png (visually confirmed sibling of DISPLAY OFF / QUIET HOURS)"
        status: pass
    human_judgment: false
  - id: D2
    description: "poll_loop latches the park from X-Battery-Mv (3300 enter / 3700 recover hysteresis), top hold priority, single render on entry and on the battery_empty boundary crossing, parked cycles are no-ops"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py (110/110, +11 new checks)"
        status: pass
    human_judgment: false
  - id: D3
    description: "server/wake.py mirrors the latch into effective_wake_interval_s()/next_wake_status()/next_wake_at_iso() so poll_loop's own silence notifier never raises a false frame-silent push while parked"
    verification:
      - kind: unit
        ref: "server/test_config_history.py (90/90, +3 new checks); server/test_poll_loop.py silence-notifier parked/unparked control pair"
        status: pass
    human_judgment: false
  - id: D4
    description: "byos_server.py pins sleep_s to 3600s while parked, anticipates recovery within the same request, composed correctly between display_off_sleep_s() and quiet_hours_sleep_s()"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py (46/46, +6 new checks)"
        status: pass
      - kind: e2e
        ref: "server/test_pipeline_e2e.py (7/7, +1 new end-to-end check: real byos subprocess + run_once() park/hash-skip/recovery cycle)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Companion frame strip / flash text no longer shows a false 'late' state or push while parked"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py (317/317, +1 new parked-vs-unparked control pair)"
        status: pass
    human_judgment: false
  - id: D6
    description: "On-glass behaviour is unverified until the next real depletion run"
    verification: []
    human_judgment: true
    rationale: "No physical device has reached 3300 mV against this code yet; the park's real-world timing and the panel's legibility at actual e-ink refresh can only be confirmed on real hardware, not in this harness suite."

duration: 55min
completed: 2026-09-23
status: complete
---

# Quick Task 260923-fr4: BATTERY EMPTY Screen Before the Pack Dies Summary

**Server-side battery-critical hold: poll_loop latches a "BATTERY EMPTY" screen at 3300 mV, byos pins the device to an hourly hash-skip check-in with same-request recovery anticipation, and the companion's monitoring never mistakes the parked cadence for silence.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-23T11:40:00+02:00 (approx.)
- **Completed:** 2026-09-23T12:40:00+02:00 (approx.)
- **Tasks:** 3
- **Files modified:** 15 (2 created: preview PNGs)

## Accomplishments

- A dedicated BATTERY EMPTY hold screen — a hollow, upright battery glyph on the same dimmed field/typography as DISPLAY OFF and QUIET HOURS — replaces whatever mid-refresh freeze the 2026-09-14 depletion run produced.
- `poll_loop.py` latches the park from the device's own `X-Battery-Mv` reading (3300 mV enter, 3700 mV recover — a 400 mV re-arm buffer, sourced from the actual BATTERY-RUN.md discharge curve), outranks both the display-off toggle and any quiet-hours window, and renders exactly once per entry/exit boundary — every other parked cycle is a byte-identical no-op.
- `stub-server/byos_server.py` pins the device's check-in cadence to 3600 s while parked and anticipates recovery within the very request that reports it, so a recovering device is never told to sleep for another hour on stale information.
- `server/wake.py`'s critical-aware mirror keeps `poll_loop.py`'s own frame-silent push and the companion's frame strip from raising a false alarm about a device that is deliberately, safely resting on a flat battery.

## Task Commits

Each task was committed atomically:

1. **Task 1: BATTERY EMPTY hold screen and glyph in render.py, render checks, preview PNGs** - `061571f` (feat)
2. **Task 2: poll_loop critical latch and battery_empty hold, critical-aware wake mirror, silence-notifier fix** - `bf5ada3` (feat)
3. **Task 3: byos sleep pin, companion monitoring call sites, end-to-end check, docs, full suite** - `08eedbc` (feat)

**Plan metadata:** committed separately by the orchestrator (this executor does not commit docs artifacts).

## Files Created/Modified

- `server/plane/render.py` - `BATTERY_EMPTY_*` copy constants, `draw_empty_battery_icon()`, `_build_battery_empty_canvas()`, `build_canvas` dispatch, CLI `--state battery_empty`
- `server/test_render.py` - 6 new checks (140/140)
- `server/poll_loop.py` - `BATTERY_CRITICAL_MV`/`BATTERY_CRITICAL_RECOVER_MV`, `apply_battery_critical_hysteresis()`, `"battery_empty"` in `_HOLD_KINDS`, top-priority hold decision, widened D-07 render boundary, single poll_state/battery_state read per cycle
- `server/test_poll_loop.py` - 11 new checks (110/110); six pre-existing 3000 mV battery fixtures migrated to 3400 mV
- `server/wake.py` - `BATTERY_CRITICAL_STATE_KEY`, `read_battery_critical()`, `battery_critical` kwarg on `effective_wake_interval_s()`/`next_wake_status()`/`next_wake_at_iso()`
- `server/device_config.py` - `BATTERY_CRITICAL_SLEEP_S = 3600`
- `server/test_config_history.py` - 3 new wake.py checks (90/90)
- `stub-server/byos_server.py` - `BATTERY_CRITICAL_SLEEP_S`/`BATTERY_CRITICAL_RECOVER_MV`, `read_battery_critical()`, `battery_critical_sleep_s()`, composed sleep_s chain
- `stub-server/test_poll_cycle.py` - 6 new checks (46/46), one new `server.wake` import for the behaviour-parity check
- `stub-server/VENDOR.md` - local modification 8 documented
- `server/test_pipeline_e2e.py` - 1 new end-to-end check (7/7)
- `companion/wake.py` - re-exports `read_battery_critical`/`BATTERY_CRITICAL_STATE_KEY`
- `companion/app.py` - `page_context()` reads the latch once, threads `ctx["battery_critical"]` and `_resolve_flash_text(battery_critical=...)`
- `companion/layout.py` - frame strip's `wake.next_wake_status()` call threads `battery_critical=ctx.get("battery_critical", False)`
- `companion/test_status_pages.py` - 1 new parked-vs-unparked control pair (317/317)
- `ARCHITECTURE.md` - new "Hold screens and the sleep_s composition" section
- `hardware/BATTERY-RUN.md` - "Follow-up: BATTERY EMPTY park" note
- `.planning/quick/260923-fr4-battery-empty-screen-before-the-pack-die/battery-empty-preview.png` - single-screen preview
- `.planning/quick/260923-fr4-battery-empty-screen-before-the-pack-die/hold-screens-side-by-side.png` - DISPLAY OFF / QUIET HOURS / BATTERY EMPTY side by side

## Decisions Made

- **Hold priority**: `battery_empty` > `display_off` > `quiet_hours` — a flat pack overrides both the operator's own toggle and any standing schedule, since detection and the operator's wishes are both moot if the device is about to lose power.
- **Byte-stability over completeness**: BATTERY EMPTY ignores `source_fault`/`battery_low`/`theme_id` entirely (not merely "doesn't use them differently") so the parked image's SHA-256 stays constant for the whole episode and every hourly check-in is a hash-skip.
- **Recovery anticipation lives in byos, not poll_loop**: `poll_loop.py`'s latch is the single source of truth for the *state*, but `byos_server.py`'s `battery_critical_sleep_s()` additionally reads the current request's own fresh `X-Battery-Mv` to avoid handing out a stale 3600 s sleep to a device that is reporting recovery in that very request — poll_loop's own latch clear can lag by up to 30 s.
- **Companion fix scoped narrowly**: only `companion/app.py` (flash text) and `companion/layout.py` (frame strip) were changed, matching the plan's own declared file list and its `key_links` entry ("companion frame strip / flash"). Home's Frame tile and Health's Device tile also call `wake.next_wake_status()` and were deliberately left untouched — extending the fix there would have gone beyond the plan's stated scope and touched files with test surfaces this task did not audit.
- **Six pre-existing tests renumbered from 3000 mV to 3400 mV**: `off`, `d13`, `b2`, `cal1`, `cal4`, `cal7` in `server/test_poll_loop.py` all used 3000 mV as a "battery low" reading to force a badge transition; 3000 mV now parks the frame, so each was moved to 3400 mV (still below the 3500 badge threshold, above the 3300 critical one), keeping each check's original intent and assertions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used the session scratchpad instead of a bare /tmp path for the CLI preview render**
- **Found during:** Task 1
- **Issue:** The plan's action text used a generic `<scratchpad>` placeholder path for the intermediate `.bin` file
- **Fix:** Wrote to the environment's actual scratchpad directory instead of `/tmp` directly, per this session's own tooling conventions
- **Files modified:** none (only an intermediate file outside the repo)
- **Verification:** preview PNG generated and visually confirmed
- **Committed in:** n/a (not a repo file)

No other deviations — the plan's six numbered issues, its decisions, and its threat register were all implemented as written.

---

**Total deviations:** 1 auto-fixed (1 blocking, purely tooling-path), 1 deliberate scope-narrowing decision (documented above, not a deviation from an explicit instruction — the plan's own file list already excluded Home/Health)
**Impact on plan:** None on functional scope. No architectural changes, no scope creep.

## Issues Encountered

- **Pre-existing, unrelated test failure discovered during full-suite verification:** `companion/test_browser_ux.py` fails one check — "a value the server's own validation rejects (wake_interval_s below its floor) ... expected the field to echo back the user's own rejected input '30', got '301800'" — reproduced twice, deterministically. This quick task touches neither `companion/pages/config_page.py` (the page this check exercises) nor any file under `companion/static/`, and `git diff --stat` confirms both are byte-identical to the base commit. This is a pre-existing bug or flake unrelated to BATTERY EMPTY, out of scope per the executor's own scope-boundary rule ("only auto-fix issues directly caused by the current task's changes"), and left unfixed. `browser-ux: 73/75 checks pass`; every other harness in `./scripts/run-all-tests.sh` passes, coverage 93%.

## User Setup Required

None - no external service configuration required. No flash, no deploy — firmware/ is byte-identical to `4b530aa` (confirmed via `git diff --quiet`).

## Next Phase Readiness

- The park is fully implemented and tested end to end (real byos subprocess + real `run_once()`), but **on-glass behaviour is unverified** until the pack genuinely reaches 3300 mV on a real device — flagged in `hardware/BATTERY-RUN.md`'s new follow-up note as the next real depletion run's job.
- No blockers for further work. `stub-server/byos_server.py`'s local modification count is now 8 (`VENDOR.md` updated); a future re-pin of that vendored file must re-apply all eight.
- The pre-existing `companion/test_browser_ux.py` failure (see Issues Encountered) is unrelated to this task and remains open for whoever owns that page's wake-interval validation UX.

---
*Phase: quick-260923-fr4*
*Completed: 2026-09-23*

## Self-Check: PASSED

All created files (both preview PNGs, this SUMMARY.md) and all touched source files confirmed present on disk; all three task commits (`061571f`, `bf5ada3`, `08eedbc`) confirmed present in `git log`.
