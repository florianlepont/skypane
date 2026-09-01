---
phase: 09-diagonal-band-theme
plan: 01
subsystem: config
tags: [python, device-config, theme-registry, panel-format]

# Dependency graph
requires:
  - phase: 08-panel-theme-rework
    provides: "The 11-entry THEMES registry shape (departing_index/arriving_index/ink_index/label/dithered/weight) and its theme_dithered()/theme_weight() accessor pattern, extended (not replaced) by this plan."
provides:
  - "5 new THEMES entries (band_blue, band_blue_light, band_green_light, band_red, band_black), each with White-base canvas fields plus band_index/band_dithered"
  - "theme_is_band()/theme_band_index()/theme_band_dithered() accessors for the render-side port"
affects: [09-02, 09-03, render, plane]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Band-theme entries carry 2 extra keys (band_index, band_dithered) beyond the standard 6-key theme contract; theme_is_band() distinguishes by key presence, not a hardcoded id list"

key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py

key-decisions:
  - "Used shape 2 from 09-PATTERNS.md (5 separate theme ids, not a nested band-colour picker within one 'band' theme) - matches the registry's established one-entry-per-variant convention"
  - "Every band entry's base-canvas fields are byte-identical to White's own values - band colour is never a base-canvas property, matching exactly how the validated spike always called build_canvas(theme_id='white') with the band colour as a separate function parameter"

patterns-established:
  - "theme_is_band(theme_id) tests key presence ('band_index' in THEMES[theme_id]) rather than an id allowlist, so a future band entry is automatically detected without touching this accessor"

requirements-completed: [PHASE9-2, PHASE9-7]

coverage:
  - id: D1
    description: "THEMES gains 5 new band theme entries (band_blue, band_blue_light, band_green_light, band_red, band_black), each with White-base canvas fields (departing/arriving=IDX_WHITE, ink=IDX_BLACK, dithered=False, weight=regular) and its own label/band_index/band_dithered"
    requirement: "PHASE9-2"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_theme_registry_shape_is_correct, #_ink_contrast_pairing_is_correct, #_dithered_and_weight_contract_is_correct, #_default_theme_and_labels_are_correct"
        status: pass
      - kind: other
        ref: "server/.venv/bin/python3 -c \"from server import device_config as dc; assert len(dc.THEMES) == 16\""
        status: pass
    human_judgment: false
  - id: D2
    description: "theme_is_band()/theme_band_index()/theme_band_dithered() accessors let a caller determine band membership and band colour/dithering purely through device_config functions, never by inspecting THEMES directly"
    requirement: "PHASE9-2"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_theme_is_band_matches_registry_band_ids, #_theme_band_index_matches_registry_or_none, #_theme_band_dithered_matches_registry_or_false"
        status: pass
    human_judgment: false
  - id: D3
    description: "The 11 pre-existing THEMES entries are byte-identical to their pre-phase values; every pre-existing contract check still fails loudly on a mismatch for any of the 11"
    verification:
      - kind: unit
        ref: "server/test_config_history.py (full run, 29/29 checks pass)"
        status: pass
      - kind: other
        ref: "git diff --stat -- server/device_config.py (insertions only, confirmed manually)"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-09-01
status: complete
---

# Phase 9 Plan 01: Diagonal Band Theme Registry Summary

**5 new device_config.THEMES band entries (band_blue/band_blue_light/band_green_light/band_red/band_black) plus theme_is_band()/theme_band_index()/theme_band_dithered() accessors, each band entry carrying White's exact base-canvas fields per the validated spike**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-01T21:55Z (approx.)
- **Completed:** 2026-09-01T22:07:39Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `THEMES` widened from 11 to 16 entries: the 5 new band ids each reuse White's own `departing_index`/`arriving_index`/`ink_index`/`dithered`/`weight` values verbatim (spike 003 round 15's validated finding that band colour was always a separate function parameter, never a base-canvas property), varying only `label`, `band_index` (the spike-confirmed `IDX_*` per colour), and `band_dithered`.
- 3 new presentation accessors — `theme_is_band()`, `theme_band_index()`, `theme_band_dithered()` — mirror the existing `theme_dithered()`/`theme_weight()` one-line-body, never-raises-for-a-valid-id contract, giving plans 09-02/09-03's render-side port a stable data contract that never needs to touch `THEMES` directly.
- `server/test_config_history.py`'s 4 exact-membership THEMES checks (`_theme_registry_shape_is_correct`, `_ink_contrast_pairing_is_correct`, `_dithered_and_weight_contract_is_correct`, `_default_theme_and_labels_are_correct`) extended additively to cover all 16 ids without weakening any of the 11 pre-existing ids' expected values; 3 new checks cover the accessors themselves, derived from `device_config.THEMES` rather than a hardcoded id list. `EXPECTED_CHECK_COUNT` 26 → 29; full harness green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 5 band THEMES entries and 3 accessor functions** - `1d7b47c` (feat)
2. **Task 2: Extend server/test_config_history.py's THEMES contract checks and cover the 3 new accessors** - `8a20564` (test)

**Plan metadata:** (pending — final docs commit follows this summary)

## Files Created/Modified
- `server/device_config.py` - 5 new `THEMES["band_*"]` entries + `theme_is_band()`/`theme_band_index()`/`theme_band_dithered()` accessors (insertions only, no existing entry/accessor touched)
- `server/test_config_history.py` - 4 exact-membership checks extended to the 16-id registry; 3 new checks for the band accessors; `EXPECTED_CHECK_COUNT` 26 → 29

## Decisions Made
- Followed 09-PATTERNS.md's recommended "shape 2" (5 separate theme ids) over a single `"band"` theme with a nested colour picker — matches the registry's established one-entry-per-visual-variant convention (`yellow`/`yellow_light`, `red`/`red_light`, etc.) and lets `THEME_IDS = tuple(THEMES)` keep auto-deriving the CFG-01 picker list with no special-casing.
- No change to `_every_theme_is_single_colour` — band entries' `departing_index`/`arriving_index` are both `IDX_WHITE`, so the existing single-colour assertion already covered them without modification (confirmed by inspection per the plan's own instruction not to add unneeded special-casing).

## Deviations from Plan

None - plan executed exactly as written. Both tasks' automated verification commands and acceptance criteria passed as specified, including the plan's own spot-check requirement (temporarily deleting `band_black`'s `band_dithered` field in a throwaway in-process mutation — never touching the file on disk — confirmed `_theme_registry_shape_is_correct` genuinely fails, then the registry was left untouched since no file edit occurred).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `device_config.theme_is_band()`/`theme_band_index()`/`theme_band_dithered()` are ready for plans 09-02/09-03's `render.py` port (`draw_diagonal_band()` and the theme-conditional `draw_top_labels()`/`draw_main_text_block()`/`draw_previous_text_block()` edits per 09-PATTERNS.md).
- No blockers. The 11 pre-existing themes remain byte-identical, so no other call site in the codebase (render pipeline, companion web page, poll loop) is affected by this plan.

---
*Phase: 09-diagonal-band-theme*
*Completed: 2026-09-01*
