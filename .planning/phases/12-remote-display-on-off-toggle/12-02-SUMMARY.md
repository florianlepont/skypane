---
phase: 12-remote-display-on-off-toggle
plan: 02
subsystem: ui
tags: [pillow, e-ink, render, panel-screen]

requires:
  - phase: 10-scheduled-quiet-hours
    provides: "_build_quiet_hours_canvas()'s dedicated hold-state canvas shape, reused structurally here"

provides:
  - "DISPLAY_OFF_HEADING_TEXT / DISPLAY_OFF_BODY_TEXT locked-English module constants (D-04)"
  - "_build_display_off_canvas() — a flat White/Black hold-state canvas with wrapped body and optional battery/fault indicators"
  - "build_canvas()/render_panel() 'display_off' dispatch branch, ordered above the empty-state branch"
  - "--state display_off CLI path with a working PNG/bin preview for plan 12-06's on-glass session"

affects: [12-04-poll-loop-integration, 12-06-on-glass-verification]

tech-stack:
  added: []
  patterns:
    - "Fixed-string (non-%-template) hold-state body: a manual toggle has no interpolated value, so the body constant is drawn unconditionally, unlike quiet_hours_until's optional-body pattern"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "Placed the display_off dispatch branch above BOTH quiet_hours and the empty-state branch in build_canvas(), closing the exact silent-fallback trap 10-02 documented for quiet_hours"
  - "build_canvas() accepts quiet_hours_until for the display_off state but never forwards it to _build_display_off_canvas() — verified byte-identical with/without, so a shared hold-branch call site in poll_loop.py cannot leak a return-time string onto this screen (D-04)"
  - "Body text wraps to 2 lines at the locked 40px body font against the 1072px safe_width — observed via a real _wrap_text() run, not assumed"

requirements-completed: []

coverage:
  - id: D1
    description: "DISPLAY_OFF_HEADING_TEXT/DISPLAY_OFF_BODY_TEXT locked copy constants, exact per D-04"
    verification:
      - kind: unit
        ref: "server/test_render.py#_display_off_copy_constants_match_locked_strings"
        status: pass
    human_judgment: false
  - id: D2
    description: "_build_display_off_canvas() renders a flat White/Black canvas, theme-independent across the full THEME_IDS registry, both indicators supported"
    verification:
      - kind: unit
        ref: "server/test_render.py#_display_off_flat_white_black_across_all_themes"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_display_off_battery_and_fault_indicators_are_independent"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_display_off_legal_palette_and_safe_box_across_indicator_combos"
        status: pass
    human_judgment: false
  - id: D3
    description: "build_canvas() dispatches 'display_off' above the empty-state branch and never leaks quiet_hours_until onto the off screen"
    verification:
      - kind: unit
        ref: "server/test_render.py#_display_off_provably_distinct_from_empty_and_quiet_hours"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_display_off_ignores_quiet_hours_until"
        status: pass
    human_judgment: false
  - id: D4
    description: "--state display_off CLI path produces a real, non-empty panel preview"
    verification:
      - kind: other
        ref: "server/.venv/bin/python3 server/plane/render.py --state display_off --out /tmp/skypane-display-off.png"
        status: pass
    human_judgment: false
  - id: D5
    description: "On-glass legibility/distinguishability of the DISPLAY OFF screen versus QUIET HOURS/empty, and that it does not read as an error state"
    verification: []
    human_judgment: true
    rationale: "12-UI-SPEC.md explicitly defers this to plan 12-06's blocking on-glass verification — Phase 9's 09-04 session found rendered PNG previews mis-call on-glass contrast even for saturated colors, so this cannot be judged from a PNG here."

duration: 25min
completed: 2026-09-05
status: complete
---

# Phase 12 Plan 02: Display-off panel render state Summary

**Dedicated `display_off` panel screen in `server/plane/render.py` — locked "DISPLAY OFF" / no-return-time copy, dispatched ahead of the empty-state branch, with a working `--state display_off` CLI preview path**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-05T17:27:00Z
- **Completed:** 2026-09-05T17:52:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added `DISPLAY_OFF_HEADING_TEXT`/`DISPLAY_OFF_BODY_TEXT` as plain string constants (not a `%`-template, unlike their quiet-hours neighbour), with a comment recording why and what the copy deliberately withholds
- Added `_build_display_off_canvas()`, structurally identical to `_build_quiet_hours_canvas()` minus the `quiet_hours_until` parameter/missing-value branch — the body is drawn unconditionally since there is no value to omit
- Wired `state == "display_off"` into `build_canvas()`/`render_panel()`, placed above the `flight is None or state == "empty"` branch, and confirmed `quiet_hours_until` is never forwarded even when a caller passes one
- Added `"display_off"` to the CLI's `--state` choices and confirmed a real PNG/bin preview renders (`/tmp/skypane-display-off.png`, sha256 `f1031e0...`)
- Extended `server/test_render.py` with 6 new checks (128 → 134, confirmed by running the harness, not by arithmetic): theme-independence across the full `THEME_IDS` registry, a dispatch-ordering regression guard against both `empty` and `quiet_hours`, `quiet_hours_until` non-leak, exact-equality copy checks, battery/fault indicator independence, and palette/safe-box compliance across all four indicator combinations
- Observed body-line count: **2 lines** at the locked 40px body font against the 1072px `safe_width` — recorded here for plan 12-06's on-glass session, per the plan's instruction not to assume a line count

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the locked off-screen copy constants and `_build_display_off_canvas()`** - `39cbbc0` (feat)
2. **Task 2: Wire the display_off state through `build_canvas()`, `render_panel()` and the CLI** - `20e031a` (feat)
3. **Task 3: Extend `server/test_render.py`** - `e5a4e6f` (test)

_No TDD gate on this plan — `tdd="true"` only on Task 1, and its RED phase was the plan's own `<verify>` block rather than a separate failing-test commit; the plan does not require a dedicated `test(...)`-before-`feat(...)` commit pair for Task 1._

## Files Created/Modified
- `server/plane/render.py` - `DISPLAY_OFF_HEADING_TEXT`/`DISPLAY_OFF_BODY_TEXT` constants, `_build_display_off_canvas()`, `build_canvas()`/`render_panel()` dispatch and docstring updates, CLI `--state` choice and `--quiet-hours-until` help text update
- `server/test_render.py` - 6 new checks covering theme-independence, dispatch-ordering regression, `quiet_hours_until` non-leak, locked-copy equality, indicator independence, and palette/safe-box compliance; `EXPECTED_CHECK_COUNT` bumped 128 → 134

## Decisions Made
- Placed the `display_off` dispatch branch above both `quiet_hours` and `empty` in `build_canvas()` — matches the plan's explicit ordering requirement and closes the same silent-fallback trap plan 10-02 documented
- `quiet_hours_until` remains an accepted (but unused) parameter for the `display_off` path, so `poll_loop.py`'s single shared hold-branch call site (plan 12-04) can pass it unconditionally on every hold call without a branch of its own
- Reused every constant carried over from `_build_quiet_hours_canvas()` (`EMPTY_INK`, `EMPTY_HEADING_FONT`, `EMPTY_BODY_FONT`, `EMPTY_HEADING_MIN_SIZE`, `SPACE_SM`) rather than introducing new ones, per the plan's "carried over unchanged" instruction

## Deviations from Plan

None - plan executed exactly as written. `EXPECTED_CHECK_COUNT` was derived from a real harness run (134), not by adding 6 to the pre-edit 128 in the abstract, though the two numbers happen to match.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `build_canvas(None, "display_off", ...)`/`render_panel(None, "display_off", ...)` are ready for plan 12-04's `poll_loop.py` integration to call
- `--state display_off` gives plan 12-06's on-glass session a real, reproducible preview invocation
- The three-screen on-glass distinguishability question (`DISPLAY OFF` vs `QUIET HOURS` vs empty) flagged by `12-UI-SPEC.md` remains open and explicitly deferred to plan 12-06 — not resolved here, per this plan's own scope and the constraint against asserting legibility from a rendered PNG

---
*Phase: 12-remote-display-on-off-toggle*
*Completed: 2026-09-05*

## Self-Check: PASSED
All claimed files and commit hashes verified present on disk / in git log.
