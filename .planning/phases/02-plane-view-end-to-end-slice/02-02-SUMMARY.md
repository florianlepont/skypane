---
phase: 02-plane-view-end-to-end-slice
plan: 02
subsystem: api
tags: [pillow, ads-b, deadband, e-ink, python, lucide]

requires:
  - phase: 02-plane-view-end-to-end-slice
    plan: 01
    provides: server/panel_format.py (wire format + Pillow palette bridge), server/plane/detect.py's select_runway3_aircraft() (normalised flight dict with vertical_rate_fpm), server/plane/render.py's zone-stacking constants (FLIGHT_NUMBER_TOP_Y reserving zone 1/3), server/poll_loop.py's run_once()/poll_state.json atomic-swap skeleton, server/fixtures/track_arrival_440cb1.json (the real EJU84YF flare fixture)
provides:
  - server/plane/runway_config.py — D-03 runway-configuration inference with D-P2-04's +-200 ft/min deadband and hold-last-state behaviour (infer_runway_config(), infer_from_flight())
  - server/plane/render.py's STATE_BACKGROUND/STATE_INK/STATE_LABEL_TEXT/STATE_GLYPH_PATH dicts, draw_state_label(), load_binary_mask(), and the public build_canvas() helper
  - server/assets/icons/ — vendored Lucide plane-takeoff/plane-landing glyphs (SVG source + pre-rasterized PNG masks) with VENDOR.md provenance
  - server/poll_loop.py's real state-inference wiring (last_confirmed_state persisted in poll_state.json, replacing the 02-01 hardcoded "arriving" stub)
  - server/test_runway_config.py, server/test_render.py — green stdlib test harnesses (14/14, 15/15)
affects: [02-03-silhouette, 02-04-enrichment-route, 02-05-deploy-hardware-verify]

tech-stack:
  added: []
  patterns:
    - "Deadband + hold-last-state (not a zero-crossing) for a noisy quantised third-party numeric field - explicit isinstance() checks with bool rejected before the numeric comparison, holding the caller-supplied prior state rather than raising or guessing"
    - "Per-state colour dicts (STATE_BACKGROUND/STATE_INK) keyed by the producing module's own string constants (runway_config.STATE_*), never bare string literals, so two modules cannot silently drift apart"
    - "Vendor-time-only SVG rasterization (cairosvg + a one-off homebrew libcairo install) - the rasterizer is never a runtime dependency; only the pre-rasterized PNG masks ship"

key-files:
  created:
    - server/plane/runway_config.py
    - server/test_runway_config.py
    - server/test_render.py
    - server/assets/icons/plane-takeoff.svg
    - server/assets/icons/plane-takeoff.png
    - server/assets/icons/plane-landing.svg
    - server/assets/icons/plane-landing.png
    - server/assets/icons/VENDOR.md
  modified:
    - server/plane/render.py
    - server/poll_loop.py

key-decisions:
  - "D-P2-04's descent-side threshold (-200 ft/min) is real-data-backed by track_arrival_440cb1.json's flare artefact (-640 then two +48 readings, held as arriving); the climb-side threshold (+200 ft/min) is explicitly documented in code, test assertion messages, and this summary as provisional/symmetry-derived per A-02-02-01 - 02-05's hardware QA, not this plan's test suite, retires that assumption"
  - "A first-ever detection whose vertical rate sits inside the deadband (confirmed_state is None, nothing to hold) renders the Empty state rather than guessing a colour - an unknown runway configuration must never be shown as a confident Blue/Green field"
  - "Renamed render.py's private _build_canvas() to a public build_canvas() so test_render.py's anti-aliasing (exactly-two-palette-indices) assertions never reach into private module state"
  - "Vendored Lucide plane-takeoff/plane-landing at release tag 1.31.0 (ISC licence), pre-rasterized to PNG alpha masks via cairosvg at vendor time only (installed libcairo via homebrew for this one-time rasterization step, not added to server/requirements.txt or imported anywhere under server/)"
  - "Deferred requirements.mark-complete for PLANE-01/PLANE-02 - same rationale as 02-01: this plan supplies real departing/arriving inference and the full-bleed colour/label contract, but PLANE-01/02's requirement text also needs airline/destination-origin enrichment (02-04) and hardware-verified White-on-saturated-colour legibility (02-05's QA checkpoint) before the requirement text is fully true"

patterns-established:
  - "poll_state.json's last_confirmed_state field is the D-P2-02 cross-cycle memory the deadband's hold-last-state behaviour depends on - read before inference, written back atomically in the same tmp-write-then-os.replace() as last_flight"
  - "_classify_state_source() in poll_loop.py logs 'inferred' vs. 'held' per cycle by re-checking the same threshold constants runway_config exports, never duplicating the threshold values as literals"

requirements-completed: []

coverage:
  - id: D1
    description: "D-P2-04 deadband + hold-last-state proven against the real recorded EJU84YF flare sequence (-640 then two +48 readings never flip the confirmed arriving state), all four boundary values (+200/+199/-200/-199), and type-hostile inputs (None, string, bool, dict) that hold rather than raise"
    requirement: "PLANE-01, PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_runway_config.py (14/14 checks)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full-bleed departing/arriving colour field (Blue/Green background, White foreground, Black excluded) with the DEPARTING/ARRIVING glyph+label, proven anti-aliasing-free via Image.getcolors() returning exactly two distinct palette indices per active state"
    requirement: "PLANE-01, PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py (15/15 checks)"
        status: pass
    human_judgment: true
    rationale: "White-on-saturated-Blue/Green legibility remains unverified on real Spectra 6 hardware (02-UI-SPEC.md's own flagged open item, carried since 02-01) - only 02-05's physical-panel QA checkpoint can close this; rendered-byte correctness alone does not prove legibility."
  - id: D3
    description: "poll_loop.py's real state wiring: no hardcoded state string reaches render_panel() anywhere in the module; last_confirmed_state round-trips through poll_state.json across two consecutive oneshot cycles even when the second cycle's vertical rate sits inside the deadband"
    requirement: "PLANE-03"
    verification:
      - kind: integration
        ref: "server/test_pipeline_e2e.py (5/5 checks, no regression) plus a manual two-cycle round-trip check against a real fixture snapshot"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-08-10
status: complete
---

# Phase 2 Plan 2: Runway-Configuration Inference and the Full-Bleed State Poster Summary

**Real D-03 vertical-rate deadband inference (D-P2-04) replaces 02-01's hardcoded "arriving" stub, and the panel now becomes a full-bleed Blue/Green poster with an explicit DEPARTING/ARRIVING glyph+label per 02-UI-SPEC.md Revision 2.**

## Performance

- **Duration:** 18 min
- **Tasks:** 3 completed
- **Files modified:** 9 (7 created, 2 modified)

## Accomplishments
- Implemented `server/plane/runway_config.py`'s `infer_runway_config()`/`infer_from_flight()`, a `+-200 ft/min` deadband that holds the last confirmed state on anything inside the band or non-numeric - proven against the real recorded `EJU84YF` landing's flare artefact (`-640` then two `+48` readings, all held as `"arriving"`) so the display never flickers on the real Mode-S quantisation noise near touchdown
- Explicitly rejected `bool` before the numeric comparison (`isinstance(True, int)` is `True` in Python) so a stray boolean vertical-rate value can never be silently read as `0`/`1`
- Documented the departure-side threshold's real evidentiary status directly in code: the module docstring, every climb-side test assertion message, and this summary all state that `CLIMB_THRESHOLD_FPM` is provisional/symmetry-derived (A-02-02-01) pending 02-05's hardware QA - only the descent side is backed by real captured data
- Rewired `server/poll_loop.py` to read/write `poll_state.json`'s new `last_confirmed_state` field and call `runway_config.infer_from_flight()`, removing the last hardcoded state string from the pipeline; a first-ever detection whose vertical rate is ambiguous now renders the Empty state instead of guessing a colour
- Rebuilt `server/plane/render.py`'s active-state rendering around `STATE_BACKGROUND`/`STATE_INK` dicts keyed by `runway_config`'s own state constants (Blue/White for departing, Green/White for arriving, Black dropped entirely per UI-SPEC Revision 2's reservation rule) and added `draw_state_label()` - the bare glyph+text state label with no filled badge behind it
- Vendored Lucide's `plane-takeoff`/`plane-landing` glyphs (release `1.31.0`, ISC licence), pre-rasterized to PNG alpha masks at vendor time via `cairosvg` (installing `libcairo` via Homebrew for this one-off step only - `cairosvg` is not a runtime dependency and is not in `server/requirements.txt`)
- Verified the exactly-two-palette-indices anti-aliasing guarantee survives the resized/thresholded glyph composite: `Image.getcolors()` on both active-state canvases returns exactly 2 entries

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 — failing runway-config and render-state harnesses** - `0fe63d8` (test)
2. **Task 2: D-03 runway-configuration inference with a deadband and hold-last-state (D-P2-04)** - `64ca20b` (feat)
3. **Task 3: Full-bleed state colour field and the DEPARTING/ARRIVING label** - `03d5f62` (feat)

## Files Created/Modified
- `server/plane/runway_config.py` - `infer_runway_config()`, `infer_from_flight()`, `CLIMB_THRESHOLD_FPM`/`DESCEND_THRESHOLD_FPM`, `STATE_DEPARTING`/`STATE_ARRIVING`
- `server/plane/render.py` - `STATE_BACKGROUND`, `STATE_INK`, `STATE_LABEL_TEXT`, `STATE_GLYPH_PATH`, `ICON_DIR`, `build_canvas()` (renamed from private `_build_canvas`), `load_binary_mask()`, `draw_state_label()`
- `server/poll_loop.py` - `run_once()` now reads/writes `last_confirmed_state`, calls `runway_config.infer_from_flight()`, logs `confirmed_state`/`render_state`/`state_source` per cycle
- `server/assets/icons/plane-takeoff.{svg,png}`, `plane-landing.{svg,png}`, `VENDOR.md` - vendored Lucide glyphs + provenance
- `server/test_runway_config.py`, `server/test_render.py` - new green stdlib harnesses (14/14, 15/15)

## Decisions Made
- Kept the plan's Wave-0 convention: both new harnesses written and confirmed RED in Task 1's single commit, then each subsequent task turns one green - consistent with 02-01's established pattern and 02-VALIDATION.md.
- Chose to store the deadband's cross-cycle memory under a renamed `poll_state.json` field (`last_confirmed_state`, replacing 02-01's `last_state`) to match the plan's own `artifacts_this_phase_produces` spec exactly; verified nothing else in the repo referenced the old field name before renaming.
- Did not call `requirements.mark-complete` for PLANE-01/PLANE-02 this plan either (see key-decisions above) - the same reasoning 02-01 documented still applies until 02-04 (enrichment) and 02-05 (hardware legibility QA) land.

## Deviations from Plan

None - plan executed exactly as written. The only implementation-time decision beyond the plan's own text was installing `libcairo` via Homebrew to run `cairosvg` for the one-time vendor-time SVG rasterization step (the plan names "any tool: `rsvg-convert`, Inkscape, even a browser 'save as PNG'" as acceptable per 02-RESEARCH.md's Don't Hand-Roll table) - not a deviation from the plan's intent, just the specific tool choice among several explicitly sanctioned options.

## Issues Encountered
None. All three tasks' automated `<verify>` commands passed on first implementation; no auto-fixes were required under Rules 1-3.

## User Setup Required
None - no external service configuration required this plan. (The one-off local `brew install cairo` was a build-time convenience for generating vendored assets, not a runtime/production dependency - it does not need to be replicated on the deployment VPS.)

## Next Phase Readiness
- `server/plane/render.py`'s `STATE_BACKGROUND`/`STATE_INK` dicts and zone-stacking constants (`FLIGHT_NUMBER_TOP_Y`, the reserved zone-3 footprint) are stable for 02-03 to fill the silhouette centrepiece without moving anything this plan or 02-01 already renders.
- `server/plane/runway_config.py`'s `infer_from_flight()` is a stable API; 02-04's enrichment work does not need to touch it.
- A-02-02-01 (the unvalidated departure-side threshold) is carried forward explicitly for 02-05's hardware QA checklist: "observe at least one real runway-3 departure end to end and confirm the panel shows DEPARTING."
- No blockers. All four `server/test_*.py` harnesses and `stub-server/test_poll_cycle.py` (15/15) are green with no regressions. A live `poll_loop.py --once` run against real current traffic found no aircraft in the runway-3 geofence at check time (correctly rendered the Empty state per D-04) - this is expected variance in real-time air traffic, not a failure; the dominant-nibble-is-Blue/Green live-traffic check from this plan's phase-level `<verification>` section is otherwise fully covered by the fixture-driven `server/test_render.py`/`server/test_pipeline_e2e.py` assertions.

---
*Phase: 02-plane-view-end-to-end-slice*
*Completed: 2026-08-10*

## Self-Check: PASSED

All 8 created files verified present on disk; all 3 task commits (`0fe63d8`, `64ca20b`, `03d5f62`) verified present in git history.
