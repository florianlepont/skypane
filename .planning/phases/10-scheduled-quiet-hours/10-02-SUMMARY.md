---
phase: 10-scheduled-quiet-hours
plan: 02
subsystem: rendering
tags: [pillow, e-ink, panel-render, cli]

requires:
  - phase: 10-scheduled-quiet-hours (plan 01)
    provides: "device_config.py's DEFAULT_QUIET_HOURS_END, normalise_quiet_hours_time(), seconds_until_quiet_hours_end() and the quiet-hours device_config.json registry fields"
provides:
  - "server/plane/render.py's _build_quiet_hours_canvas() render state (D-05/D-06), dispatched before the empty-state branch"
  - "build_canvas()/render_panel()'s quiet_hours_until parameter"
  - "the --state quiet_hours / --quiet-hours-until CLI preview path"
affects: [10-04-poll-loop-quiet-hours-gate]

tech-stack:
  added: []
  patterns:
    - "New non-flight render states are copied verbatim from _build_empty_canvas()'s structure (flat White/Black, fit_text_size()-shrunk heading, _wrap_text()-wrapped body) rather than inventing new drawing primitives"
    - "A new build_canvas() dispatch branch for a flight-less state must be inserted BEFORE the `flight is None or state == \"empty\"` check, since flight is always None for such states"
    - "CLI synthetic-flight guards should test positive membership against runway_config's STATE_* constants, not a negative list against every real state, so a future non-flight state doesn't have to be remembered into an ever-growing exclusion list"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "Missing/empty/non-string quiet_hours_until omits the body line entirely (heading-only screen) rather than raising or drawing the literal text 'Back at None' - T-10-02-01"
  - "theme_id and runway_id are both ignored for the quiet_hours state, exactly like the empty state - the screen is always flat White/Black"
  - "Deferred visual-review checkpoint (10-UI-SPEC.md's open item): resolved as option (1), no visual change beyond the differing copy - see Deviations/Manual Review section below"

patterns-established:
  - "Non-flight render states (empty, quiet_hours) share one structural template: pf.new_canvas(IDX_WHITE) -> fit_text_size()-shrunk heading -> _wrap_text()-wrapped body -> centred as one block via the total_height/start_y formula -> optional battery/source-fault indicators -> _assert_in_safe_box() on every drawn bbox"

requirements-completed: []

coverage:
  - id: D1
    description: "_build_quiet_hours_canvas() renders the locked 'QUIET HOURS' / 'Back at HH:MM' English copy on a flat White canvas in Black ink, dispatched before the empty-state branch"
    verification:
      - kind: unit
        ref: "server/test_render.py#_quiet_hours_packs_white_dominant_with_black"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_quiet_hours_branch_precedes_empty_branch_in_source"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every pixel on the quiet-hours canvas is a legal Spectra 6 palette index, and the screen ignores theme_id"
    verification:
      - kind: unit
        ref: "server/test_render.py#_quiet_hours_only_legal_indices"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_quiet_hours_ignores_theme_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "Missing/empty quiet_hours_until degrades to a heading-only screen without raising and without drawing 'Back at None'"
    verification:
      - kind: unit
        ref: "server/test_render.py#_quiet_hours_missing_until_omits_body_without_raising"
        status: pass
    human_judgment: false
  - id: D4
    description: "Battery-low icon and source-fault badge render on the quiet-hours screen when their flags are set"
    verification:
      - kind: unit
        ref: "server/test_render.py#_quiet_hours_battery_low_changes_canvas"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_quiet_hours_source_fault_changes_canvas"
        status: pass
    human_judgment: false
  - id: D5
    description: "render.py's CLI can render the quiet-hours state to a real .bin/.png artifact via --state quiet_hours / --quiet-hours-until, without breaking the two aircraft states or the --state choices validation"
    verification:
      - kind: unit
        ref: "server/test_render.py#_cli_renders_quiet_hours_state"
        status: pass
      - kind: other
        ref: "server/.venv/bin/python3 server/plane/render.py --state quiet_hours --quiet-hours-until 07:00 --preview /tmp/skypane-quiet-hours-preview.png --out /tmp/skypane-quiet-hours.bin"
        status: pass
    human_judgment: false
  - id: D6
    description: "Deferred visual-review checkpoint: whether 'QUIET HOURS' reads as meaningfully distinct from 'Watching Runway 3' at a glance, given both screens share the identical flat-White/Black/centred-heading structure"
    verification:
      - kind: manual_procedural
        ref: "side-by-side comparison of /tmp/skypane-quiet-hours-preview.png and /tmp/skypane-empty-preview.png"
        status: pass
    human_judgment: true
    rationale: "10-UI-SPEC.md deliberately left this open as a real-preview judgment call, not a fixed pixel spec. Executor made the call per the 'this spec's job is to hand the executor a concrete option (1) to build and test' framing; a human on-glass/on-screen sign-off before shipping to the real device remains the project's own established discipline for this class of change (05-CONTEXT.md's battery-icon precedent, 03-CONTEXT.md's poster redesign precedent)."

duration: 15min
completed: 2026-09-03
status: complete
---

# Phase 10 Plan 02: Quiet-Hours Panel Render State Summary

**`_build_quiet_hours_canvas()` renders the locked "QUIET HOURS" / "Back at HH:MM" copy on a flat White/Black panel, dispatched before the empty-state branch, plus a `--state quiet_hours` preview CLI path**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-03T19:14:00Z
- **Completed:** 2026-09-03T19:29:36Z
- **Tasks:** 2/2 completed
- **Files modified:** 2 (`server/plane/render.py`, `server/test_render.py`)

## Accomplishments

- Added `QUIET_HOURS_HEADING_TEXT`/`QUIET_HOURS_BODY_TEMPLATE` locked English copy constants (D-05/D-06) and `_build_quiet_hours_canvas()`, structurally a near-verbatim copy of `_build_empty_canvas()`: flat White background, `EMPTY_INK` (Black) text, `fit_text_size()`-shrunk heading, `_wrap_text()`-wrapped body, identical vertical-centring formula, and the same battery-icon/source-fault-badge precedent.
- Inserted `build_canvas()`'s `state == "quiet_hours"` dispatch branch as the FIRST statement of the function body, before the existing `flight is None or state == "empty"` check, so a quiet-hours call (which always has `flight=None`) doesn't silently fall through to the empty state. Threaded `quiet_hours_until=None` through `build_canvas()` and `render_panel()`.
- A missing, empty, or non-string `quiet_hours_until` omits the body line entirely (heading-only screen) rather than ever drawing the literal text "Back at None" (T-10-02-01) — verified for both `None` and `""`.
- Exposed the new state through `render.py`'s preview CLI: added `"quiet_hours"` to `--state`'s choices and a `--quiet-hours-until` flag (default `device_config.DEFAULT_QUIET_HOURS_END`), and fixed `main()`'s synthetic-flight guard to test positive membership against `(runway_config.STATE_DEPARTING, runway_config.STATE_ARRIVING)` instead of `!= "empty"`, so a quiet-hours preview no longer drags in the fake-flight/route machinery.
- Extended `server/test_render.py` with 8 new checks (dispatch-order source assertion, legal-palette membership, theme-ignored, missing-until degradation, battery-low/source-fault indicator differencing, and a CLI-driven `render.main()` check); bumped `EXPECTED_CHECK_COUNT` from 119 to 127. Full harness passes 127/127.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `_build_quiet_hours_canvas()` and the `build_canvas()` dispatch branch** - `49b2277` (feat)
2. **Task 2: Expose the quiet-hours state through render.py's preview CLI** - `92e2bae` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE.md/ROADMAP.md)

## Files Created/Modified

- `server/plane/render.py` - `QUIET_HOURS_HEADING_TEXT`/`QUIET_HOURS_BODY_TEMPLATE` constants; `_build_quiet_hours_canvas()`; `build_canvas()`'s new dispatch branch and `quiet_hours_until` parameter; `render_panel()`'s passthrough; `build_parser()`'s `"quiet_hours"` choice and `--quiet-hours-until` flag; `main()`'s reworked synthetic-flight guard and `build_canvas()` call
- `server/test_render.py` - `import inspect`; 8 new `check(...)` calls covering the quiet-hours render state and its CLI path; `EXPECTED_CHECK_COUNT` 119 → 127

## Decisions Made

- Body line omission (not a `None`-string fallback) for a missing/empty/non-string `quiet_hours_until` — matches 03-CONTEXT.md D-25's "an element exists visually only when it has real information to show" discipline, already reused for the battery icon (05-CONTEXT.md D-06).
- `theme_id`/`runway_id` ignored for this state (always flat White/Black) — matches the empty state's own precedent exactly, per 10-UI-SPEC.md's locked default.
- CLI synthetic-flight guard rewritten to a positive `STATE_DEPARTING`/`STATE_ARRIVING` membership test rather than adding `quiet_hours` to a growing negative-exclusion list, so a future third non-flight state doesn't have to be remembered into it.
- Deferred visual-review checkpoint (10-UI-SPEC.md's explicitly-open item) resolved in favor of option (1) — no additional visual differentiation beyond the copy itself. See "Manual Review" below for the reasoning.

## Deviations from Plan

None — plan executed exactly as written. Both tasks' acceptance criteria and verification commands passed without requiring any Rule 1/2/3 auto-fixes.

## Manual Review (Task 2's deferred human-check)

10-UI-SPEC.md deliberately left one question open for this plan: does "QUIET HOURS" read as meaningfully distinct from "Watching Runway 3" at a glance, given both screens share the identical flat-White/Black/centred-heading structure?

Rendered both previews and compared them side by side:
- `/tmp/skypane-quiet-hours-preview.png` — "QUIET HOURS" (2 words, all-caps, short) / "Back at 07:00"
- `/tmp/skypane-empty-preview.png` — "Watching Runway 3" (3 words, title-case, longer) / "No aircraft detected yet — the display updates the moment one is."

**Finding:** the two screens read as clearly distinct at a glance. The heading shapes differ meaningfully (short all-caps vs. longer title-case phrase) and the body copy differs completely in both length and content — there is no risk of confusing "quiet hours" for "no aircraft yet, still watching." Per the spec's own ordering (least to most invasive), **option (1) — change nothing — is sufficient.** No heading-treatment change or distinct fill colour was applied.

This finding is recorded as `human_judgment: true` in the coverage block (D6) per the project's established discipline (05-CONTEXT.md's battery icon, 03-CONTEXT.md's poster redesign) that this class of "does it read right at a glance" call gets a real on-glass/on-screen look before being treated as final, even when an autonomous plan makes the initial call.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. No new dependencies (`server/requirements.txt` untouched, per the plan's own T-10-SC threat-register entry).

## Next Phase Readiness

`server/poll_loop.py` (plan 10-04) can now call `render.build_canvas(None, "quiet_hours", quiet_hours_until=<HH:MM>, battery_low=..., source_fault=...)` — the only production caller of this render state per this plan's `key_links`. No blockers for plan 10-04.

---
*Phase: 10-scheduled-quiet-hours*
*Completed: 2026-09-03*

## Self-Check: PASSED

- FOUND: server/plane/render.py
- FOUND: server/test_render.py
- FOUND: .planning/phases/10-scheduled-quiet-hours/10-02-SUMMARY.md
- FOUND commit: 49b2277
- FOUND commit: 92e2bae
- FOUND commit: 83a1013
