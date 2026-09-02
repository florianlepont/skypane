---
phase: 09-diagonal-band-theme
plan: 02
subsystem: rendering
tags: [pillow, e-ink, panel-render, theming]

# Dependency graph
requires:
  - phase: 09-diagonal-band-theme (plan 01)
    provides: 5 band THEMES registry entries and theme_is_band()/theme_band_index()/theme_band_dithered() accessors in server/device_config.py
provides:
  - "draw_diagonal_band(canvas, band_idx, dithered=False) - the diagonal trapezoid band drawing primitive, ported verbatim from spike 003"
  - "BAND_SHIFT_FRAC/BAND_TOP_LEFT_FRAC/BAND_TOP_RIGHT_FRAC/BAND_BOT_LEFT_FRAC/BAND_BOT_RIGHT_FRAC module-level geometry constants"
  - "draw_top_labels(..., band_theme=False) - the band-aware top-label split (merged state-label/airport-code left run + standalone runway-tag right run)"
  - "_build_active_canvas()'s band dispatch: draws the band right after the background fill for band themes, threads band_theme=is_band_theme into draw_top_labels()"
affects: [09-diagonal-band-theme plan 03 (three-tier text hierarchy port, depends on this plan)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Theme-conditional drawing dispatch resolved once in _build_active_canvas() (is_band_theme/band_idx/band_dithered_flag), mirroring the existing theme_dithered/weight resolution pattern"
    - "Text-role splitting derived from the real runway_tag_text().partition(' · ') output rather than hardcoded literals, so future runway ids split correctly automatically"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "Ported spike 003's draw_reference_band()/patched_draw_top_labels() verbatim (geometry and split logic unchanged) rather than re-deriving - the spike's round-15 developer-confirmed values are the source of truth"
  - "band_theme defaults to False on draw_top_labels() so every pre-Phase-9 call site (and any future direct caller) is byte-identical to before this phase unless a caller explicitly opts in"
  - "draw_main_text_block()/draw_previous_text_block() deliberately left untouched - band themes render with the band + split labels but the old centred two-line text block on top, an expected intermediate state until plan 09-03"

patterns-established:
  - "Band-drawing calls happen immediately after the background canvas is created and before any other draw call, so the band always sits behind subsequent illustrations/text"

requirements-completed: [PHASE9-1, PHASE9-3]

coverage:
  - id: D1
    description: "draw_diagonal_band() paints the exact measured trapezoid in the requested colour, flat or dithered toward White, using only legal panel indices"
    requirement: "PHASE9-1"
    verification:
      - kind: unit
        ref: "server/test_render.py#draw_diagonal_band() paints only {IDX_WHITE, band_idx} on a fresh White canvas, flat and dithered"
        status: pass
      - kind: unit
        ref: "server/test_render.py#every registered band theme (PHASE9-1) renders via build_canvas() in both departing and arriving states without exception"
        status: pass
    human_judgment: false
  - id: D2
    description: "_build_active_canvas() draws the diagonal band for every band theme (and only band themes), immediately after the background fill and before top labels/illustrations/text"
    requirement: "PHASE9-1"
    verification:
      - kind: unit
        ref: "server/test_render.py#the default (white) theme's canvas is byte-identical to before this phase (getdata()/getcolors() computed fresh, and 'white' itself is confirmed not a band theme)"
        status: pass
    human_judgment: false
  - id: D3
    description: "draw_top_labels() splits the top row into a merged state-label/airport-code run and a standalone runway-tag run for band themes, derived from runway_tag_text().partition(' · '); non-band themes keep today's unsplit pair"
    requirement: "PHASE9-3"
    verification:
      - kind: unit
        ref: "server/test_render.py#a band theme's top labels are genuinely split into a merged state-label/airport-code run (e.g. 'DEPARTING FROM ORY') and a standalone runway-tag run (e.g. 'RWY 3'), both derived from runway_tag_text().partition(' · ') (PHASE9-3)"
        status: pass
      - kind: unit
        ref: "server/test_render.py#a non-band theme's (white, the default) top labels remain exactly STATE_LABEL_TEXT and the FULL runway tag, unsplit - both draw_top_labels()'s own default (called with no band_theme argument) and _build_active_canvas()'s wiring genuinely preserve today's behaviour"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-01
status: complete
---

# Phase 9 Plan 02: Diagonal Band Primitive and Top-Label Split Summary

**`draw_diagonal_band()` trapezoid primitive and band-aware `draw_top_labels()` split, wired into `_build_active_canvas()` for the 5 Phase-9 band themes, with all 11 pre-existing themes byte-identical to before this phase**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-01
- **Tasks:** 3
- **Files modified:** 2 (`server/plane/render.py`, `server/test_render.py`)

## Accomplishments
- Ported spike 003's `draw_reference_band()` verbatim into production `render.py` as `draw_diagonal_band(canvas, band_idx, dithered=False)`, plus the 5 measured `BAND_*_FRAC` geometry constants
- Extended `draw_top_labels()` with a `band_theme=False` kwarg: band themes get a merged "DEPARTING FROM ORY"/"ARRIVING TO ORY" left label plus a standalone "RWY 3" right tag (both derived from `runway_tag_text().partition(" · ")`, never hardcoded); every other theme is unaffected by default
- Wired `_build_active_canvas()` to resolve `is_band_theme`/`band_idx`/`band_dithered_flag` via `device_config.theme_is_band()`/`theme_band_index()`/`theme_band_dithered()`, draw the band immediately after the background fill (before any other element), and thread `band_theme=is_band_theme` into `draw_top_labels()`
- Added 5 new `server/test_render.py` checks (107 -> 112) covering band-theme render success, `draw_diagonal_band()`'s palette legality (flat and dithered), the genuine top-label split, the non-band-theme default's genuine preservation (spot-checked by temporarily flipping the default and confirming the guard trips), and the default White canvas's byte-identity to before this phase

## Task Commits

Each task was committed atomically:

1. **Task 1: draw_diagonal_band() and the band geometry constants** - `c703960` (feat)
2. **Task 2: Band-aware draw_top_labels() and the _build_active_canvas() band/label dispatch** - `4bd8e51` (feat)
3. **Task 3: server/test_render.py coverage for the band primitive and the split top labels** - `0c91ec7` (test)

**Plan metadata:** commit pending (docs: complete plan)

## Files Created/Modified
- `server/plane/render.py` - Added `draw_diagonal_band()`, 5 `BAND_*_FRAC` constants, `_BAND_TOP_LABEL_DIRECTION`, extended `draw_top_labels()` with `band_theme=False`, and `_build_active_canvas()`'s band dispatch
- `server/test_render.py` - 5 new checks; `EXPECTED_CHECK_COUNT` 107 -> 112

## Decisions Made
- Ported the spike's geometry and split-label logic verbatim (no re-derivation) - round 15 is the developer-confirmed source of truth, and any deviation would silently regress a decision already validated on-glass-adjacent (screen preview)
- Left `draw_main_text_block()`/`draw_previous_text_block()` untouched per the plan's own scope note - band themes currently render band + split labels with the OLD centred two-line text block still on top, an expected, deliberately incomplete intermediate state that plan 09-03 completes
- Strengthened the non-band-theme regression check to call `draw_top_labels()` directly with no `band_theme` argument (not just through `build_canvas()`'s explicit `band_theme=is_band_theme` wiring), because the wiring always passes the argument explicitly and would mask a wrong parameter default - confirmed this actually catches a flipped default via a manual spot-check before committing

## Deviations from Plan

None - plan executed exactly as written. The one addition beyond the plan's literal Task 3 checklist (item 4, "non-band-theme top labels are unaffected") was strengthening that check to also call `draw_top_labels()` directly without a `band_theme` argument, which the plan's own acceptance criteria implicitly required ("the new split-label check demonstrably fails if `band_theme` defaults to `True` instead of `False`, spot-checked...") - a build_canvas()-only check could not have satisfied that acceptance criterion, since `_build_active_canvas()` always passes the argument explicitly regardless of the parameter's own default.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The diagonal band primitive and band-aware top-label split are production-ready and fully wired for all 5 band themes
- Plan 09-03 can now proceed: it depends on this plan's `_build_active_canvas()` band dispatch and will replace the old centred two-line text block with the three-tier hierarchy (PHASE9-4/5/6) for band themes, passing `band_idx=` through to `draw_main_text_block()`/`draw_previous_text_block()`
- `server/test_render.py`'s "every registered theme genuinely differs from White" check now passes for all 5 band themes (previously expected-failing per this plan's own objective note, since 09-01 only added registry entries reusing White's base-canvas fields) - the band is now visibly wired in
- `server/test_poll_loop.py`'s pinned panel.bin digest check remains at 42/43 (pre-existing macOS/Linux Pillow font-rendering platform quirk, unrelated to Phase 9, untouched)

---
*Phase: 09-diagonal-band-theme*
*Completed: 2026-09-01*

## Self-Check: PASSED

- FOUND: server/plane/render.py
- FOUND: server/test_render.py
- FOUND: .planning/phases/09-diagonal-band-theme/09-02-SUMMARY.md
- FOUND commit: c703960 (Task 1)
- FOUND commit: 4bd8e51 (Task 2)
- FOUND commit: 0c91ec7 (Task 3)
