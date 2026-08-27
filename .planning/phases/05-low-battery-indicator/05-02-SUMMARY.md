---
phase: 05-low-battery-indicator
plan: 02
subsystem: rendering, api, infra
tags: [pillow, http.server, panel-rendering, hysteresis, telemetry]

# Dependency graph
requires:
  - phase: 05-low-battery-indicator (05-01)
    provides: check-battery checker + BATTERY-RUN.md protocol (3400 mV "genuinely depleted" convention this plan's 3500 mV threshold sits with margin above)
provides:
  - draw_battery_icon() + eight BATTERY_ICON_* geometry constants in server/plane/render.py, conditionally drawn in all three states (departing/arriving/empty)
  - battery_low kwarg threaded through render_panel/build_canvas/_build_active_canvas/_build_empty_canvas, plus a --battery-low CLI preview flag
  - parse_battery_mv()/save_battery_state() in stub-server/byos_server.py - strict ASCII-digit validation and single-writer persistence of battery_state.json, gated strictly behind bearer_ok()
  - BATTERY_LOW_THRESHOLD_MV/BATTERY_LOW_CLEAR_MV/load_battery_state()/apply_battery_hysteresis() in server/poll_loop.py - the 3500/3600 mV hysteresis decision, persisted cross-cycle in poll_state.json
  - a guarded re-render on the D-04 hold branch (and the never-detected branch) so a battery-status flip reaches the display even with no new aircraft detection
affects: [05-03 (device slice - real ADC bring-up replaces the hardcoded X-Battery-Mv=0, closing the loop this plan's server-side path opens)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-writer state file discipline: byos_server.py writes battery_state.json, poll_loop.py only ever reads it - avoids a lost-update race between two independently-scheduled systemd units with no lock/IPC"
    - "Hysteresis computed once per cycle before any branching (mirrors quick task 260827-oz9's unknown_prefix pattern), so every branch - including both no-detection branches - can thread it into a render call or a guarded re-render decision"
    - "Strict ASCII-digit-set validation (not str.isdigit()) for any hostile numeric header - str.isdigit() admits non-ASCII decimal/superscript digits that int() then misparses or raises on"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py
    - stub-server/byos_server.py
    - stub-server/VENDOR.md
    - stub-server/test_poll_cycle.py
    - server/poll_loop.py
    - server/test_poll_loop.py
    - server/test_pipeline_e2e.py

key-decisions:
  - "Empty-state ink is IDX_BLACK (named EMPTY_INK) - a battery reading is a device-health fact independent of whether an aircraft is detected, and the empty state is the single most common real-world case for discovering a low pack overnight"
  - "Terminal-nub height changed from 14px to 16px (SPACE_SM) for grid alignment - resolved in 05-02-PLAN.md, total bounding box unchanged at (64,1504,136,1536)"
  - "BATTERY_MV_MIN=1 rejects the '0' PROTOCOL.md unknown sentinel from being persisted as a real reading; BATTERY_MV_MAX=10000 is a sanity ceiling far above any single-cell LiPo"
  - "battery_state.json is read-only from poll_loop.py's side - single-writer discipline avoids a two-process JSON read-modify-write race"
  - "A reading strictly between 3500 and 3600 mV deliberately holds the previous hysteresis decision in BOTH directions (Pitfall 5) - it can neither newly arm nor newly clear the warning"
  - "The D-04 hold branch (no new detection, a flight already on screen) gets a guarded re-render scoped only to a genuine battery-decision flip - closes a real gap the planner found: without this, a battery flip during a held-flight window would never reach the display"

patterns-established:
  - "Battery-icon geometry derives entirely from the existing spacing scale (SPACE_LG/MD/XS/SM, MARGIN) - no ad hoc magic numbers, per 05-UI-SPEC.md's sign-off"
  - "Pillow rectangle drawing uses inclusive corner coordinates (matching draw_frame()'s existing convention) - a nominal 72x32 box renders a 73x33px footprint; this is intentional and must not be 'corrected' to exclusive bounds"

requirements-completed: [DEVICE-04]

coverage:
  - id: D1
    description: "A bottom-left battery-low icon draws conditionally in the panel's own ink for all three states (departing/arriving/empty), with zero pixel change anywhere when battery_low is False or omitted"
    requirement: "DEVICE-04"
    verification:
      - kind: unit
        ref: "server/test_render.py#build_canvas() with no battery kwarg is pixel-identical to battery_low=False"
        status: pass
      - kind: unit
        ref: "server/test_render.py#battery_low=True differs from battery_low=False only inside the icon bounding box"
        status: pass
      - kind: unit
        ref: "server/test_render.py#with battery_low=True, the body outline corner/fill/nub read as the state's own ink"
        status: pass
      - kind: unit
        ref: "server/test_render.py#battery icon geometry derives from the existing spacing scale"
        status: pass
    human_judgment: false
  - id: D2
    description: "An authenticated device poll carrying a plausible X-Battery-Mv persists battery_state.json atomically; every malformed/hostile/out-of-range/non-ASCII-digit/'0'-sentinel value is silently ignored while the poll still returns 200; an unauthenticated poll writes nothing"
    requirement: "DEVICE-04"
    verification:
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#an authenticated poll carrying a plausible X-Battery-Mv persists {battery_mv, received_at}"
        status: pass
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#10 hostile/malformed X-Battery-Mv values all return 200 and persist nothing"
        status: pass
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#a display poll with a bogus bearer token returns 401 and never writes battery_state.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "A reading persisted by byos_server.py is read each cycle, turned into a hysteretic battery_low decision that survives the oneshot's process boundary, and threaded into every render path including a guarded re-render on hold cycles when the decision genuinely flips"
    requirement: "DEVICE-04"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py#apply_battery_hysteresis()'s truth table"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#apply_battery_hysteresis(None, was_active) holds was_active unchanged"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py#load_battery_state() returns None for a missing file, invalid JSON, ..."
        status: pass
      - kind: integration
        ref: "server/test_poll_loop.py#the battery decision survives run_once()'s process boundary ... and the D-04 hold branch re-renders panel.bin"
        status: pass
      - kind: e2e
        ref: "server/test_pipeline_e2e.py#a real authenticated poll carrying X-Battery-Mv:3400, followed by a run_once() cycle, changes the served panel.bin only inside the icon's byte columns/rows"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-08-27
status: complete
---

# Phase 5 Plan 2: Server-Side Battery-Low Path (DEVICE-04) Summary

**A real `X-Battery-Mv` telemetry value arriving on the wire is validated, persisted, turned into a 3500/3600 mV hysteresis decision, and drawn as a battery icon glyph in the panel's bottom-left corner — proven end to end against the real `byos_server.py` device protocol.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-27T22:07:00+02:00 (approx.)
- **Completed:** 2026-08-27T22:23:17+02:00
- **Tasks:** 3 (each executed as an explicit RED/GREEN TDD cycle, 6 commits)
- **Files modified:** 8

## Accomplishments

- `draw_battery_icon()` plus eight `BATTERY_ICON_*` geometry constants (all derived from the existing spacing scale) draw a bottom-left battery glyph in `server/plane/render.py`, threaded through `render_panel`/`build_canvas`/`_build_active_canvas`/`_build_empty_canvas` via a `battery_low=False` kwarg — renders in every one of the three states (departing, arriving, empty), with zero pixel change anywhere when it's off.
- `parse_battery_mv()`/`save_battery_state()` in `stub-server/byos_server.py` validate the `X-Battery-Mv` header (strict ASCII-digit-only, 1..10000 mV inclusive, rejecting the `"0"` PROTOCOL.md unknown sentinel) and persist it atomically to `battery_state.json`, gated strictly behind the pre-existing `bearer_ok()` auth check.
- `BATTERY_LOW_THRESHOLD_MV`/`BATTERY_LOW_CLEAR_MV`/`load_battery_state()`/`apply_battery_hysteresis()` in `server/poll_loop.py` turn that reading into a hysteretic decision each cycle, persisted in `poll_state.json` across the oneshot's process boundary, and threaded into every render call site — including a new guarded re-render on the D-04 hold branch so a battery-status flip reaches the display even on a cycle with no new aircraft detection.

## Task Commits

Each task was executed as an explicit RED → GREEN TDD cycle:

1. **Task 1: Draw the battery icon on the panel** - `d710ec7` (test, RED) → `20bd128` (feat, GREEN)
2. **Task 2: Validate and persist the reported battery millivolts** - `c18e8ce` (test, RED) → `2c60979` (feat, GREEN)
3. **Task 3: Decide, render, and serve the low-battery panel** - `f6e9ba0` (test, RED) → `7f850a0` (feat, GREEN)

_No refactor commits were needed - each GREEN step passed cleanly on the first implementation pass (after one test-harness self-correction per task, documented below)._

## Files Created/Modified

- `server/plane/render.py` - `draw_battery_icon()`, `BATTERY_ICON_*` constants, `EMPTY_INK`, `battery_low` kwarg threading, `--battery-low` CLI flag
- `server/test_render.py` - four new checks (42→46), fixed the RED-step diff helper to use Pillow's inclusive rectangle-corner convention
- `stub-server/byos_server.py` - `parse_battery_mv()`, `save_battery_state()`, `battery_state_path()`, `BATTERY_MV_MIN`/`BATTERY_MV_MAX`, persistence hook in `do_GET`
- `stub-server/VENDOR.md` - third local-modifications entry documenting the new file/schema/single-writer rule
- `stub-server/test_poll_cycle.py` - three new checks (17→20), fixed a client-side Unicode-header encoding issue in the hostile-value test
- `server/poll_loop.py` - `BATTERY_LOW_THRESHOLD_MV`/`BATTERY_LOW_CLEAR_MV`, `load_battery_state()`, `apply_battery_hysteresis()`, battery_low threading, guarded hold-branch re-render, `battery_low=%s` log field
- `server/test_poll_loop.py` - four new checks (8→12), fixed a pre-existing test spy's signature to accept the new `battery_low` kwarg
- `server/test_pipeline_e2e.py` - one new end-to-end check (5→6)

## Decisions Made

See `key-decisions` in the frontmatter above. All decisions were resolved in `05-02-PLAN.md` itself (empty-state ink, nub height, mV bounds, single-writer discipline, hysteresis symmetry, hold-branch re-render) - none required a new decision during execution.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test helper used exclusive pixel-diff bounds against an inclusive drawing convention**
- **Found during:** Task 1 (draw the battery icon)
- **Issue:** The RED-step `_diff_inside_outside()` helper in `server/test_render.py` treated the icon's bounding box as a half-open crop region (`col < right`), but `draw_battery_icon()` (matching `draw_frame()`'s existing convention) draws with Pillow's inclusive rectangle corners - the nub's right edge and the body's bottom edge land exactly ON the box's own right/bottom coordinate, which the exclusive check false-flagged as "outside".
- **Fix:** Changed the helper's containment check from `<` to `<=` on both bounds, matching the documented inclusive-corner convention.
- **Files modified:** `server/test_render.py`
- **Verification:** `render: 46/46 checks pass`
- **Committed in:** `20bd128` (Task 1 GREEN commit)

**2. [Rule 3 - Blocking] Python's http.client cannot send a raw non-ASCII header value as a str**
- **Found during:** Task 2 (validate and persist X-Battery-Mv), Check B's Arabic-Indic-digit hostile value
- **Issue:** `http.client.putheader()` latin-1-encodes a `str` header value and raises `UnicodeEncodeError` for the Arabic-Indic `"٣٥٠٠"` case before the request ever reaches the server - a client-side encode failure, not the server-side rejection the check was meant to exercise.
- **Fix:** Sent the hostile value as pre-encoded UTF-8 `bytes` instead of `str` for that header - bytes header values pass through `putheader()` unmodified, so the raw hostile bytes actually reach the server and exercise `parse_battery_mv()`'s real rejection path.
- **Files modified:** `stub-server/test_poll_cycle.py`
- **Verification:** `poll-cycle: 20/20 checks pass`
- **Committed in:** `2c60979` (Task 2 GREEN commit)

**3. [Rule 1 - Bug] Pre-existing test spy didn't accept the new battery_low kwarg**
- **Found during:** Task 3 (decide, render, and serve the low-battery panel)
- **Issue:** `server/test_poll_loop.py` check 5 (pre-existing, from the D-25 two-deep-history plan) monkeypatches `render.render_panel` with a spy whose signature didn't include `battery_low` - once `run_once()` started passing `battery_low=battery_low` to every render call site, the spy raised `TypeError` on an unexpected keyword argument.
- **Fix:** Added `battery_low=False` to the spy's signature and its pass-through call to the original function.
- **Files modified:** `server/test_poll_loop.py`
- **Verification:** `poll-loop: 12/12 checks pass`
- **Committed in:** `7f850a0` (Task 3 GREEN commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs in test helpers, 1 Rule 3 blocking client-encoding fix)
**Impact on plan:** All three were test-harness-only corrections required to make the plan's own specified checks actually exercise what they were written to prove. No production code behavior was changed by any of these fixes, and no scope creep occurred.

## Issues Encountered

None beyond the three auto-fixed deviations above.

## User Setup Required

None - no external service configuration required. No deploy/ change was needed (`SKYPANE_STATE_DIR` and its `ReadWritePaths` already cover the new `battery_state.json` file); confirmed via `git diff --exit-code deploy/`.

## Next Phase Readiness

- The server-side half of DEVICE-04 is complete and proven end-to-end: `render.py` draws the icon, `byos_server.py` validates/persists real telemetry, `poll_loop.py` decides and re-renders. The device currently sends the hardcoded `X-Battery-Mv=0` unknown sentinel per PROTOCOL.md, so this path is fully built and tested but not yet exercised by real hardware.
- Plan 05-03 (device slice: real ADC bring-up on the EE02 driver board's factory battery-sense circuit, A0/GPIO1 + D5/GPIO6, no soldering) replaces that hardcoded `0` with a real reading, closing the loop this plan opens. It has its own blocking `checkpoint:human-verify` hardware task (flash-and-observe) and is not autonomously executable.
- No blockers for 05-03 from this plan's side - the wire contract, persistence schema, and rendering path are all already in place and tested against real protocol traffic.

---
*Phase: 05-low-battery-indicator*
*Completed: 2026-08-27*
