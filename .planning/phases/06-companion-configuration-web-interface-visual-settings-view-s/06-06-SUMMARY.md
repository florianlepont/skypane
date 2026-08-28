---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 06
subsystem: rendering
tags: [python, pillow, e-ink, theming, cfg-01, cfg-05, cfg-12]

# Dependency graph
requires:
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s (plan 01)
    provides: "server/device_config.py's THEMES/RUNWAYS registries, normalise_theme_id()/normalise_runway_id(), and their presentation accessors"
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s (plan 02)
    provides: "server/plane/detect.py's per-runway geometry and poll_current_aircraft()'s diagnostics dict (the eventual CFG-05 fault signal source)"
provides:
  - "server/plane/render.py reads DEPARTING/ARRIVING colours from device_config.THEMES via theme_id, never a hardcoded constant"
  - "server/plane/render.py reads the top-right tag and empty-state heading from device_config.RUNWAYS via runway_id"
  - "draw_source_fault_badge() - a small, palette-safe alert badge, drawable on any canvas via a source_fault=False keyword on build_canvas()/render_panel()"
  - "build_canvas()/render_panel() theme_id/runway_id/source_fault keyword contract, ready for plan 06-10's poll_loop.py wiring"
affects: [poll-loop-wiring, companion-config-form, device-health-fault-icon]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registry-id normalisation contract: an unrecognised theme_id/runway_id silently degrades to the module default via device_config.normalise_*_id() before any dict lookup; an unrecognised state string still raises ValueError, kept deliberately loud as a caller-bug detector (T-06-06-01)"
    - "Retained-constant compatibility shim: STATE_BACKGROUND/STATE_INK/TOP_RIGHT_TAG_TEXT/EMPTY_HEADING_TEXT stay as module constants (now derived from the default registry entry) solely because test_render.py's pre-existing checks read them directly - new code must call the function form"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "EMPTY_HEADING_MIN_SIZE floor (48px) chosen by matching the ~64-75% shrink-floor ratio the module's existing MAIN_LINE1/MAIN_LINE2/PREVIOUS_LINE1/PREVIOUS_LINE2 floors already use, since no plan-specified value was given and all three registry headings are short enough that the floor is not expected to bind in practice"
  - "draw_source_fault_badge() is a hand-drawn triangle+stroke glyph (ImageDraw.polygon/line) rather than a bundled icon asset - keeps the badge dependency-free and trivially provable to use only ink_idx, with no new palette index risk"
  - "Task 3 executed as a genuine RED/GREEN pair (test commit before feat commit) since it uniquely owns test_render.py's extension in this plan; Tasks 1-2 (render.py-only) each landed as a single feat commit, matching this repository's established tdd=true precedent (06-02/06-03) for single-file behavior-threading tasks"

patterns-established:
  - "Small-badge dominance discipline: any future on-panel indicator must stay small enough that _assert_legal_palette()'s bg_idx-is-dominant assertion still holds - proven here by running the assertion (via build_canvas()) rather than re-implementing it in the test"

requirements-completed: [CFG-01, CFG-05, CFG-12]

coverage:
  - id: D1
    description: "Panel DEPARTING/ARRIVING background and ink colours resolve through device_config.THEMES via a theme_id keyword; an unrecognised theme degrades to the default rather than raising, while an unrecognised state still raises ValueError naming all three legal states"
    requirement: CFG-01
    verification:
      - kind: unit
        ref: "server/test_render.py#build_canvas(theme_id='sky') and build_canvas() with no theme produce identical canvases"
        status: pass
      - kind: unit
        ref: "server/test_render.py#build_canvas(theme_id='not-a-theme') produces the default theme's canvas rather than raising"
        status: pass
      - kind: unit
        ref: "server/test_render.py#build_canvas(flight, 'nonsense-state') still raises ValueError naming departing/arriving/empty"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_assert_legal_palette() passes for every registered theme"
        status: pass
    human_judgment: false
  - id: D2
    description: "The top-right runway tag and empty-state heading follow the tracked runway_id via device_config.RUNWAYS, including the longest registry heading passing the safe-box assertion via fit_text_size()"
    requirement: CFG-12
    verification:
      - kind: unit
        ref: "server/test_render.py#runway_tag_text('06-24')/('02-20') return the strings from device_config.RUNWAYS"
        status: pass
      - kind: unit
        ref: "server/test_render.py#build_canvas(None, 'empty', runway_id=...) draws that runway's heading, including the longest of the three, and passes the safe-box assertion"
        status: pass
      - kind: unit
        ref: "server/test_render.py#build_canvas(flight, 'departing', runway_id='06-24') draws that runway's tag, passing the within-canvas assertion"
        status: pass
    human_judgment: false
  - id: D3
    description: "A small palette-safe source-fault alert badge is drawable on both active and empty canvases via source_fault=True, absent by default, and never breaks the legal-palette or background-dominance guard rails across every theme"
    requirement: CFG-05
    verification:
      - kind: unit
        ref: "server/test_render.py#the source-fault badge is drawn on both the active canvas and the empty canvas (visible in every state)"
        status: pass
      - kind: unit
        ref: "server/test_render.py#the badge caption text is absent from a normal render (source_fault defaults to False)"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_assert_legal_palette() passes with the badge drawn, in both active states, the empty state, and every theme"
        status: pass
      - kind: unit
        ref: "server/test_render.py#draw_source_fault_badge()'s bounding box stays inside the drawn frame"
        status: pass
      - kind: manual_procedural
        ref: "server/.venv/bin/python3 server/plane/render.py --state arriving --callsign AF1380 --source-fault --out /tmp/fault.bin (exits 0, writes 960000 bytes)"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-08-28
status: complete
---

# Phase 6 Plan 06: Theme, Runway & Source-Fault Render Wiring Summary

**`server/plane/render.py` now resolves colours by theme (CFG-01) and text by tracked runway (CFG-12) through `server/device_config.py`'s registries, plus a new palette-safe `draw_source_fault_badge()` (CFG-05) that only ever fires on a genuine all-sources-down signal — `server/test_render.py` grew from 42 to 60 checks, all passing.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3/3 (Tasks 1-2 each `type="auto" tdd="true"`, single feat commit; Task 3 `type="auto" tdd="true"`, genuine RED/GREEN pair since it owns the test-harness extension)
- **Files modified:** 2 (`server/plane/render.py`, `server/test_render.py`)

## Accomplishments

- `state_background_index()`/`state_ink_index()` resolve DEPARTING/ARRIVING colours from `device_config.THEMES` via a normalised `theme_id`; `STATE_BACKGROUND`/`STATE_INK` are retained as module constants (redefined from the default theme) only because `test_render.py`'s pre-existing checks read them directly. `build_canvas()`/`render_panel()`/`_build_active_canvas()` gained a trailing `theme_id` keyword, default path byte-identical, unknown theme degrades silently, unknown state still raises `ValueError` naming all three legal states.
- `runway_tag_text()`/`empty_heading_text()` resolve the top-right tag and empty-state heading from `device_config.RUNWAYS` via a normalised `runway_id`. `draw_top_labels()`/`_build_empty_canvas()` gained a trailing `runway_id` keyword; the empty heading now runs through `fit_text_size()` (new `EMPTY_HEADING_MIN_SIZE` floor) instead of a bare font lookup, so a longer runway label shrinks rather than tripping the safe-box assertion.
- `draw_source_fault_badge()` draws a small outlined triangle + exclamation stroke plus `SOURCE_FAULT_TEXT` ("ADS-B source unavailable — check the companion page"), bottom-centre inside the frame, using only the caller's `ink_idx` — never a new palette index. `_build_active_canvas()`/`_build_empty_canvas()`/`build_canvas()`/`render_panel()` gained a trailing `source_fault=False` keyword; the badge is absent by default and provably never breaks `_assert_legal_palette()`'s guard rails, across every theme and both active states.
- `render_panel()`'s docstring documents the rule that makes CFG-05 correct rather than a false-alarm trap: `source_fault` must be driven only by `poll_loop.py`'s all-providers-failed classification of `detect.poll_current_aircraft()`'s diagnostics dict (plan 06-02), never by an empty selection — matching `.planning/seeds/on-device-fault-icon.md`'s explicit scoping.
- `--theme`/`--runway`/`--source-fault` CLI flags added for manual QA. `server/test_render.py` grew from 42 to 60 checks (18 new: 5 theme, 5 runway, 8 badge), all 42 pre-existing checks unmodified and still passing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Make the panel's background and ink colours a function of the selected theme** - `45733bb` (feat)
2. **Task 2: Make the runway tag and empty-state heading follow the tracked runway** - `7febdf4` (feat)
3. **Task 3: Add CFG-05's source-fault badge and widen server/test_render.py** - `a966e3d` (test, RED: 8 new badge checks fail against pre-badge code, 10 new theme/runway checks already pass) → `1214d04` (feat, GREEN: 60/60 checks pass)

**Plan metadata:** commit pending (this file + STATE.md/ROADMAP.md/REQUIREMENTS.md update)

## Files Created/Modified

- `server/plane/render.py` - `state_background_index()`, `state_ink_index()`, `runway_tag_text()`, `empty_heading_text()`, `draw_source_fault_badge()`, `SOURCE_FAULT_TEXT`, `SOURCE_FAULT_GLYPH_PX`, `EMPTY_HEADING_MIN_SIZE`; `theme_id`/`runway_id`/`source_fault` keyword parameters threaded through `build_canvas()`/`render_panel()`/`_build_active_canvas()`/`_build_empty_canvas()`/`draw_top_labels()`; `--theme`/`--runway`/`--source-fault` CLI flags
- `server/test_render.py` - `EXPECTED_CHECK_COUNT` raised 42 → 60; 18 new checks covering the theme/runway/fault-badge matrix

## Decisions Made

- `EMPTY_HEADING_MIN_SIZE` set to 48px (66.7% of the 72px initial size), matching the ~64-75% shrink-floor ratio the module's other four `fit_text_size()` roles already use — no plan-specified value existed, and all three registry headings are short enough that this floor is not expected to bind in practice.
- `draw_source_fault_badge()` hand-draws its glyph (`ImageDraw.polygon`/`line`) rather than compositing a bundled icon asset, keeping the badge dependency-free and trivially provable (by source inspection and a grep-based acceptance check) to use only the caller's `ink_idx`.
- Task 3 was executed as a genuine RED (test commit, 8 badge checks failing with `TypeError`/`AttributeError`) then GREEN (feat commit, 60/60 passing) pair, since it is the task that actually owns `test_render.py`'s extension. Tasks 1 and 2 (render.py-only tasks) each landed as a single `feat` commit — matching this repository's established `tdd="true"` precedent from plans 06-02/06-03, where single-file behavior-threading tasks were not further split into RED/GREEN pairs.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria (grep counts, CLI exit codes, hash-match checks, safe-box assertions) were verified via ad-hoc commands before each commit, in addition to the widened `test_render.py` harness.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `build_canvas()`/`render_panel()`'s `theme_id`/`runway_id`/`source_fault` keyword contract is ready for plan 06-10's `poll_loop.py` wiring to consume `device_config.load_device_config()`'s `theme`/`tracked_runway` fields and the all-providers-failed diagnostics classification.
- `device_config.THEMES` still holds exactly one entry (`"sky"`) — CFG-01's picker is functionally live end-to-end in the render path, but its second theme option arrives in Phase 7's real on-glass calibration session, per this module's own extension procedure (one dict entry in `server/device_config.py`, no `render.py` change).
- Full `scripts/run-all-tests.sh` (all 9 harnesses), `ruff check .`, and `git diff --stat` (confined to `server/plane/render.py`/`server/test_render.py`) all confirmed clean.

---

*Phase: 06-companion-configuration-web-interface-visual-settings-view-s*
*Completed: 2026-08-28*

## Self-Check: PASSED

- FOUND: server/plane/render.py
- FOUND: server/test_render.py
- FOUND: .planning/phases/06-companion-configuration-web-interface-visual-settings-view-s/06-06-SUMMARY.md
- FOUND commit: 45733bb (Task 1)
- FOUND commit: 7febdf4 (Task 2)
- FOUND commit: a966e3d (Task 3 RED)
- FOUND commit: 1214d04 (Task 3 GREEN)
