---
phase: 09-diagonal-band-theme
plan: 03
subsystem: rendering
tags: [pillow, e-ink, panel-rendering, typography]

# Dependency graph
requires:
  - phase: 09-diagonal-band-theme (plan 09-02)
    provides: draw_diagonal_band(), band geometry constants, band-aware draw_top_labels(), is_band_theme/band_idx/band_dithered_flag threading in _build_active_canvas()
provides:
  - "_band_center_x(canvas_y, w) - the band trapezoid's own horizontal centre at a given canvas y, computed once per text block"
  - "Band-conditional draw_main_text_block(..., band_idx=None) - three-tier hierarchy (big identifier / dash / tracked route line / airline·type line) centred inside the band, band-aware ink (white on band_black, plain ink_idx elsewhere)"
  - "Band-conditional draw_previous_text_block(..., band_idx=None) - identical hierarchy, right-aligned at the card's existing ~57% scale, never ink-swapped"
  - "Completed _build_active_canvas() band_idx wiring into both text-block call sites"
  - "server/test_render.py coverage: 112 -> 118 checks (non-band regression, tier-split content reuse, centring-once guard, black-band ink swap, previous-card clearance, full palette-legality sweep)"
affects: [rendering, plane-theme-config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "band_idx=None kwarg wrapping an entire function body in `if band_idx is None: <verbatim original body> else: <new band branch>` - guarantees every non-band caller (band_idx always None) is byte-identical to before the plan, with zero risk of the new branch's logic leaking into the old path"
    - "Compute a per-block shared geometry value (center_x via _band_center_x()) exactly once, before any line is measured, and thread that single value through every subsequent draw call in the block - never recompute a shared anchor per line"
    - "Diff a real render against a text-suppressed render (same theme, draw function monkeypatched to a no-op) to isolate newly-painted ink pixels from a background fill that can legitimately share the same palette index (band_black's own fill is IDX_BLACK)"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "Ported the spike's _band_center_x()/patched_draw_main_text_block()/patched_draw_previous_text_block() verbatim in logic, per the plan's own explicit instruction not to re-derive - only naming/location changed (module-level constants instead of monkeypatch-local ones)."
  - "Previous card's band branch never swaps ink to white, even for band_black - the spike's round-6 finding (band's rightmost extent ~45% width at this card's height vs. this card's own ~89%-width text) means there is nothing for this card to contrast against, so ink override was deliberately omitted here."
  - "Task 3's black-band ink-swap check samples a diff between a real render and a text-suppressed render of the same canvas, rather than a bare 'any IDX_BLACK pixel inside the bbox' probe - band_black's own band FILL is itself IDX_BLACK, so the naive version would misfire on the background, not on missing ink."
  - "Task 3's previous-card clearance check discriminates the previous card's bboxes from the main card's via anchor ('ra' vs 'ma'), not a y-coordinate midpoint heuristic - the main card's own band-centred text legitimately sits below the canvas's vertical midpoint too, which the first attempt at this check got wrong before being corrected during this same session."

requirements-completed: [PHASE9-4, PHASE9-5, PHASE9-6, PHASE9-7]

coverage:
  - id: D1
    description: "Main flight card shows the three-tier hierarchy (big identifier / dash rule / tracked route line / airline·type line) centred inside the band, with one center_x shared across all three lines"
    requirement: "PHASE9-4"
    verification:
      - kind: unit
        ref: "server/test_render.py#_band_main_card_tier_split_reuses_real_content"
        status: pass
      - kind: unit
        ref: "server/test_render.py#_band_center_x_computed_once_not_recomputed_per_line"
        status: pass
    human_judgment: false
  - id: D2
    description: "band_black's main-card text renders in white ink; every other band theme's main-card text renders in black ink, resolved per-call"
    requirement: "PHASE9-5"
    verification:
      - kind: unit
        ref: "server/test_render.py#_band_black_main_card_ink_swaps_to_white"
        status: pass
    human_judgment: false
  - id: D3
    description: "Previous (secondary) card shows the identical three-tier hierarchy, right-aligned at its existing ~57% scale, unchanged position, never colliding with the band, never ink-swapped"
    requirement: "PHASE9-6"
    verification:
      - kind: unit
        ref: "server/test_render.py#_previous_card_never_collides_with_the_band"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every one of the 11 pre-band themes' main and previous card text is byte-identical to before this phase (band_idx=None preserves the existing centred/right-aligned two-line block exactly)"
    requirement: "PHASE9-7"
    verification:
      - kind: unit
        ref: "server/test_render.py#_non_band_text_blocks_unaffected_by_band_idx_kwarg"
        status: pass
      - kind: integration
        ref: "server/test_render.py full suite (118/118)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full band composition (three-tier text on both cards, palette legality, source-fault badge) holds across all 5 band themes, both active states"
    requirement: "PHASE9-4"
    verification:
      - kind: unit
        ref: "server/test_render.py#_band_themes_full_composition_stays_palette_legal"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-09-02
status: complete
---

# Phase 9 Plan 03: Diagonal Band Text Hierarchy Summary

**Three-tier flight-identifier text (big identifier / dash / tracked route / airline·type line) ported verbatim from spike round 15 onto both flight cards, with band-aware ink and a single computed centre-x, closing out the diagonal-band theme's visual composition.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3
- **Files modified:** 2 (`server/plane/render.py`, `server/test_render.py`)

## Accomplishments
- Added `_band_center_x()`, a verbatim port of spike round 12/15's fix: the band trapezoid's own horizontal centre at a given canvas y, computed once per text block and reused for every line in it - never recomputed per line (the confirmed round-12 bug).
- `draw_main_text_block()` and `draw_previous_text_block()` both gained a `band_idx=None` kwarg wrapping their entire pre-existing body in an `if band_idx is None:` branch, guaranteeing every one of the 11 pre-band themes is byte-identical to before this phase.
- Band themes now render the full validated three-tier hierarchy on both cards: main card centred inside the band with the band's own contrast ink (white on `band_black`, per round 13's fix), previous card right-aligned at its existing ~57% scale with no ink override (the band never reaches that card's position, per round 6's finding).
- Completed `_build_active_canvas()`'s `band_idx` wiring into both text-block call sites, finishing what plan 09-02 started.
- `server/test_render.py` grew from 112 to 118 checks, covering the non-band regression guarantee, tier-split content reuse against the real content ladder, the centring-once regression guard (demonstrated live to catch a reintroduced round-12 bug), the black-band ink swap (via pixel diffing, not exception absence), previous-card band clearance, and a full 5-theme x 2-state x source-fault palette-legality sweep.

## Task Commits

Each task was committed atomically:

1. **Task 1: `_band_center_x()` and the band-conditional main-card three-tier hierarchy** - `ac4d4e0` (feat)
2. **Task 2: Band-conditional previous-card hierarchy and completed `_build_active_canvas()` wiring** - `f352898` (feat)
3. **Task 3: `server/test_render.py` coverage for the full band composition, plus full-suite reconciliation** - `d2d17e2` (test)

**Plan metadata:** committed separately below (docs: complete plan)

## Files Created/Modified
- `server/plane/render.py` - `_band_center_x()`, `BAND_MAIN_*`/`BAND_PREV_*` font/geometry constants, band-conditional `draw_main_text_block()`/`draw_previous_text_block()`, completed `_build_active_canvas()` wiring
- `server/test_render.py` - 6 new checks (112 -> 118), `EXPECTED_CHECK_COUNT` updated

## Decisions Made
- Ported the spike's `_band_center_x()`/`patched_draw_main_text_block()`/`patched_draw_previous_text_block()` verbatim in logic per the plan's explicit instruction - only the constants' names/locations changed (module-level rather than monkeypatch-local).
- Left the previous card's ink un-overridden even on `band_black`, matching the spike's round-6 finding that the band never reaches this card's position at any candidate geometry.
- Corrected the previous-card clearance check's own discriminator mid-session: an initial y-coordinate-midpoint filter incorrectly captured the main card's own band-centred text (which legitimately sits below the canvas's vertical midpoint); switched to filtering on `anchor="ra"` vs `"ma"`, which unambiguously separates the two cards' draws.
- Corrected the black-band ink-swap check mid-session: a bare "any `IDX_BLACK` pixel inside the text bbox" probe misfired on `band_black`'s own background fill (which is legitimately `IDX_BLACK`); switched to diffing a real render against a text-suppressed render of the identical canvas so only genuinely newly-painted ink pixels are sampled.

## Deviations from Plan

None - plan executed exactly as written. The two check-implementation corrections above (ink-swap sampling method, previous-card discriminator) were made during Task 3's own authoring, before any commit - not deviations from committed, verified work, but iteration on the test implementation itself while developing it, consistent with the plan's own instruction to demonstrate the centring-once check catches a real regression before committing.

## Issues Encountered
- The centring-once check (#115) required an actual live demonstration per the plan's acceptance criteria: `center_x` was temporarily recomputed inside the `plain_text` branch to reproduce the round-12 bug, the check was confirmed to fail (117/118, with the exact expected failure message naming two distinct x-coordinates), and the change was reverted before any commit. `git diff` and the full 118/118 pass confirm no trace of the temporary change remains.
- `server/test_poll_loop.py`'s pinned `panel.bin` digest check failed during the full-suite run (`scripts/run-all-tests.sh`), as expected and flagged in this plan's own objective: root-caused as the pre-existing macOS/Linux Pillow font-rendering difference, unrelated to this phase's additive-only band changes. Not re-pinned, per the objective's explicit instruction.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 9's diagonal-band theme composition is now fully implemented and verified: geometry (09-01/09-02), band drawing + top-label split (09-02), and the full three-tier text hierarchy on both cards (this plan).
- `server/test_render.py` is 118/118 green; `scripts/run-all-tests.sh` is green except the pre-existing, unrelated `test_poll_loop.py` digest quirk.
- Remaining phase work is plan 09-04 (not part of this plan's scope).

---
*Phase: 09-diagonal-band-theme*
*Completed: 2026-09-02*
