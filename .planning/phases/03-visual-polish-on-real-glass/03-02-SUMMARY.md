---
phase: 03-visual-polish-on-real-glass
plan: 02
subsystem: ui
tags: [pillow, dithering, floyd-steinberg, palette, e-ink]

# Dependency graph
requires:
  - phase: 03-visual-polish-on-real-glass
    provides: "03-01's padded_palette(), the four Zilla Slab typographic role constants, and the D-13 interim PALETTE_RGB triples the mood hue is derived from"
provides:
  - "server/plane/dither.py: build_mood_background(state) - a deterministic, memoized, Floyd-Steinberg-dithered two-tone gradient in the state's own hue, containing only {IDX_WHITE, state's index}"
  - "dither_to_full_panel_palette() - the no-remap full-6-color quantize helper 03-03's illustration path will consume"
  - "write_calibration_preview() - the three-PNG calibration tool 03-04's on-glass pass needs"
  - "render.py: draw_quiet_zone() + the spatially-scoped _assert_palette_contract() (with an illustration_bbox hook ready for 03-03), replacing the old whole-canvas 'exactly 2 indices' guard rail"
affects: [03-03-illustration-livery, 03-04-hardware-calibration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-tone sub-palette quantization (throwaway [White, state_base_rgb] target palette + .point() remap) for the mood background, kept structurally distinct in the same module from the full-6-color no-remap illustration path, with an in-line docstring explaining why they must never be unified"
    - "Row-scoped bytes.translate() LUTs instead of a per-pixel Python random loop for generating a jittered gradient at full canvas scale - ~3.7s -> ~100ms"
    - "Quiet-zone flat plate drawn before text on a dithered background (draw_quiet_zone()), replacing the old flat-background assumption"
    - "Spatially-scoped palette contract (_assert_palette_contract()) with a C-speed sentinel-rectangle fill instead of a whole-canvas getdata() loop"

key-files:
  created:
    - server/plane/dither.py
    - server/test_dither.py
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "Rejected the UI-SPEC's original full-6-color-palette mood recipe after measuring it at real scale during planning: the arriving (green) mood produced six-colour static (23% Yellow+Red, 17% stray Black), not a green field, because the D-13 interim Green has no near palette neighbour. Replaced with quantization against a throwaway two-entry [White, state_base_rgb] sub-palette, which is hue-pure by construction and requires a .point() remap (the illustration path, wired in 03-03, is the opposite: no remap, because it targets PALETTE_RGB directly in canvas index order)."
  - "MOOD_LIGHT_TINT_MIX finalized at 0.40 (not the UI-SPEC draft's 0.35) - measured to produce 80.3% state-hue / 19.7% White for both states, comfortably clearing the hue-dominance and gradient-visibility thresholds"
  - "MOOD_NOISE_AMPLITUDE = 10, MOOD_NOISE_SEED = 1380 - both starting points explicitly flagged for 03-04's on-glass calibration pass, not asserted final"
  - "Jitter generation uses one bulk Random.randbytes() call per channel plane plus row-scoped bytes.translate() LUTs, not a per-pixel Random.randint() loop - measured directly: the naive per-pixel loop took 3.7s (would have blown the <2s full-render budget on its own), the translate-based approach takes ~100ms"
  - "draw_state_label()/draw_route_line()/draw_airline_line() now measure their full geometry before drawing anything, draw one combined quiet-zone rectangle, then draw glyph/text on top - draw_route_line() covers the prefix+city pair with a single plate, not two"
  - "Guard rail replaced: _assert_palette_contract() checks (1) whole-canvas indices are a subset of the 6 legal ones, (2) every quiet zone is exactly {bg_idx, IDX_WHITE} with both present, (3) the region outside illustration_bbox (None this plan) is exactly {bg_idx, IDX_WHITE} via a C-speed sentinel fill, (4) bg_idx pixel count exceeds IDX_WHITE's - not a raised index-count ceiling, which 03-RESEARCH.md Pitfall 1 explicitly warned would let a stray Yellow/Red caption bug through"

patterns-established:
  - "Any future full-canvas procedural image generation in this codebase should use the row-scoped bytes.translate() LUT technique rather than a per-pixel Python loop with a Random call - the latter is ~35x slower at 1200x1600 scale on this hardware"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "build_mood_background() produces a deterministic, memoized, Floyd-Steinberg-dithered two-tone gradient per state (departing: {IDX_WHITE, IDX_BLUE} Blue-majority; arriving: {IDX_WHITE, IDX_GREEN} Green-majority), byte-identical across repeated and interleaved calls, raising ValueError for an unknown state"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_dither.py - 15/15 checks (index-set exactness, hue-dominance thresholds, determinism, interleaving, palette parity, ValueError, packed-nibble contract, fresh-copy-per-call, MOOD_BASE_RGB/PALETTE_RGB tracking)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The active states' background is a real dithered gradient, not a flat fill - both the state's dominant index and White are present outside every quiet zone and the silhouette band"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py - 'departing background is a real dithered gradient ... not a flat fill'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every text-bearing zone (state label, flight-number caption, route line, airline line, bottom tag) sits on a flat quiet-zone plate of the state's colour, sized to the text bbox plus 8px padding, clamped to SAFE_BOX, containing only {bg_idx, IDX_WHITE}"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py - 'each of the 5 quiet-zone rectangles the departing render path actually draws contains only {IDX_BLUE, IDX_WHITE}, lies entirely inside SAFE_BOX, and fully contains the text bbox it backs'"
        status: pass
    human_judgment: false
  - id: D4
    description: "The whole-canvas palette contract holds outside the (not-yet-existing) illustration zone: departing is exactly {IDX_WHITE, IDX_BLUE}, arriving exactly {IDX_WHITE, IDX_GREEN}, empty unaffected at exactly {IDX_BLACK, IDX_WHITE}; no stroke_width/stroke_fill usage anywhere in render.py; rendering stays byte-deterministic including across an interleaved other-state build"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py - checks 12-13 (re-expressed), the stroke_width/stroke_fill source-grep check, and the interleaved-build determinism check; 37/37 total"
        status: pass
      - kind: other
        ref: "grep -v '^ *#' server/plane/render.py | grep -c 'stroke_width\\|stroke_fill' == 0; grep -v '^ *#' server/plane/render.py | grep -c 'new_canvas' == 1"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full render_panel() completes well under the 2-second budget (measured ~0.36-0.46s including a cold build_mood_background() call, against a ~31.5s hardware full-refresh) and write_calibration_preview() ships the three PNGs 03-04's on-glass pass needs"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_dither.py 'write_calibration_preview() writes exactly three PNG files...'; manual timing measurement recorded in this SUMMARY"
        status: pass
    human_judgment: false
  - id: D6
    description: "Visual sanity check: departing/arriving preview PNGs show a genuinely photographic, gently-graded dithered mood field with legible quiet-zone captions and no visible artifacts"
    verification: []
    human_judgment: true
    rationale: "Preview colours are explicitly nominal render-internal RGB triples (D-P2-03), not colour-accurate - the real on-glass legibility judgment (whether the quiet-zone plates read as clean caption plates vs. visually awkward boxes, and whether the illustration-vs-background figure-ground separation still works) is 03-04's checkpoint, not this plan's. This plan's own preview inspection (visually confirmed during execution - see below) is a sanity check only."

# Metrics
duration: 30min
completed: 2026-08-26
status: complete
---

# Phase 3 Plan 2: Dithered Mood Background & Quiet-Zone Captions Summary

**Replaced the flat saturated Blue/Green background with a code-generated, Floyd-Steinberg-dithered two-tone mood gradient per state (80.3% state hue / 19.7% White), with every caption now sitting on a flat quiet-zone plate and a spatially-scoped palette contract replacing the old whole-canvas guard rail.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-08-26T14:35:00+02:00 (approx.)
- **Completed:** 2026-08-26T15:05:00+02:00
- **Tasks:** 2 completed
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments

- `server/plane/dither.py` ships `build_mood_background(state)`: a deterministic, memoized, two-tone Floyd-Steinberg-dithered gradient quantized against a throwaway `[White, state_base_rgb]` sub-palette - measured 80.3% state-hue / 19.7% White for both departing (Blue) and arriving (Green), zero cross-hue pixels, matching the D-13 interim palette derived directly from `panel_format.PALETTE_RGB` (no re-typed literals)
- Also ships `dither_to_full_panel_palette()` (the no-remap, full-6-color path 03-03's illustration zone will consume) and `write_calibration_preview()` (the three-PNG tool 03-04's on-glass pass needs)
- `render.py`'s `_build_active_canvas()` now composites the mood background with five quiet-zone-backed text elements (state label, flight-number caption, route line, airline line, bottom tag) - each measured, quiet-zoned, then drawn - replacing the flat `pf.new_canvas(bg_idx)` fill
- The whole-canvas "exactly 2 palette indices" guard rail is replaced by `_assert_palette_contract()`: a spatially-scoped check (legal-index subset, per-quiet-zone `{bg_idx, IDX_WHITE}`, whole-canvas-minus-illustration exactness via a C-speed sentinel fill, hue-dominance) with an `illustration_bbox` hook already wired for 03-03
- `server/test_dither.py` (new, 15/15 checks) and `server/test_render.py` (32 -> 37 checks) both green, alongside `test_pipeline_e2e.py`, `test_enrich.py`, `test_runway_config.py`, `test_plane_detection.py`

## Task Commits

Each task was committed atomically:

1. **Task 1: server/plane/dither.py - mood background generator, full-palette dither helper, calibration preview** - `e8d3136` (feat)
2. **Task 2: Composite mood background with quiet-zone captions, replace guard rail** - `76d58a8` (feat)

## Files Created/Modified

- `server/plane/dither.py` - `build_mood_background()`, `dither_to_full_panel_palette()`, `panel_palette_image()`, `write_calibration_preview()`, `MOOD_BASE_RGB`/`MOOD_LIGHT_TINT_MIX`/`MOOD_NOISE_AMPLITUDE`/`MOOD_NOISE_SEED`
- `server/test_dither.py` - 15 checks covering the full `<behavior>` contract plus nibble/palette/determinism pins
- `server/plane/render.py` - `QUIET_ZONE_PAD`, `draw_quiet_zone()`, `_assert_palette_contract()`; `draw_state_label()`/`draw_route_line()`/`draw_airline_line()` now quiet-zone before drawing and return their rectangle(s); `_build_active_canvas()` sources its canvas from `dither.build_mood_background()`
- `server/test_render.py` - checks 12-13 re-expressed to the exact `{bg_idx, IDX_WHITE}` set; checks 16-19 (silhouette shape/bbox) re-expressed to diff against the un-silhouetted background instead of testing `pixel == IDX_WHITE` directly; 5 new checks (33-37); `EXPECTED_CHECK_COUNT` 32 -> 37

## Measured Values for 03-04's Calibration Pass

Recorded here per this plan's `<output>` instruction - 03-04 tunes these against real glass and needs to know where they started:

| Constant | Value | Status |
|---|---|---|
| `MOOD_LIGHT_TINT_MIX` | 0.40 | Starting point, not asserted final |
| `MOOD_NOISE_AMPLITUDE` | 10 | Starting point, not asserted final |
| `MOOD_NOISE_SEED` | 1380 | Fixed (must never be re-seeded per-render) |

**Measured per-state index distribution** (`build_mood_background()`, real installed Pillow 12.3.0):

| State | State-hue index share | White share |
|---|---|---|
| departing (Blue) | 80.3% | 19.7% |
| arriving (Green) | 80.3% | 19.7% |

**Measured wall time:** a cold-process `render_panel()` call (first `build_mood_background()` build, uncached) completed in 0.36s; a warm in-process call in ~0.15s. Both comfortably clear the acceptance criterion's <2s ceiling and are negligible against the panel's ~31.5s hardware full-refresh.

## Decisions Made

- Rejected the UI-SPEC's original "quantize the full gradient against the full 6-color palette" recipe after measuring it at real scale during planning: the arriving (green) mood produced six-colour static (23.4% Yellow+Red, 17.4% stray Black), not a green field - the D-13 interim Green `(96, 128, 80)` has no near neighbour in a 6-entry palette whose entries are far apart, so Floyd-Steinberg error diffusion mixed in Black/Yellow/Blue. Replaced with quantization against a throwaway two-entry `[White, state_base_rgb]` sub-palette (hue-pure by construction, requires a `.point()` remap) - documented in-line in `dither.py`'s module docstring so a later reader doesn't "fix" this into the full-palette path the illustration zone (03-03) correctly uses instead.
- The literal per-pixel-per-channel `random.Random.randint()` loop the plan's `<action>` describes, implemented naively, measured at 3.7 seconds for one background - would have blown the full-render `<2s` acceptance criterion on its own. Replaced with one bulk `Random.randbytes()` call per RGB channel plane plus a row-scoped `bytes.translate()` LUT (both C-speed operations) - measured at ~100ms, a ~35x improvement, while still deriving all randomness from the same module-local `Random(MOOD_NOISE_SEED)` instance and remaining fully deterministic.
- `draw_route_line()` returns `(quiet_rect, bbox)` (per the plan's explicit "alongside the existing composite bbox" instruction); `draw_state_label()`/`draw_airline_line()` return just their quiet-zone rectangle, since no other caller needs their pre-padding bbox.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Naive per-pixel jitter loop blew the render-time budget by ~9x**
- **Found during:** Task 1, while implementing `_build_mood_source_rgb()`
- **Issue:** A literal interpretation of the plan's jitter description (`random.Random.randint()` called once per channel per pixel, ~5.76M calls) measured at 3.7 seconds for a single background build - alone exceeding the Task 2 acceptance criterion's <2s full-render ceiling, and wildly out of line with the plan's own "~44ms per background" planning-time measurement.
- **Fix:** Replaced with one bulk `Random.randbytes()` call per RGB channel plane (still the same module-local, seeded `Random` instance - no change to determinism or the "never use the reseedable global `random` module" requirement) plus a row-scoped 256-entry `bytes.translate()` lookup table applying the gradient-plus-jitter transform at C speed. Measured at ~100ms for the noise/gradient build, ~150ms total including quantization.
- **Files modified:** `server/plane/dither.py`
- **Verification:** `server/test_dither.py`'s determinism/index-set/hue-dominance checks all pass unchanged; a full `render_panel()` call measured at 0.36s cold, well under the 2s ceiling.
- **Committed in:** `e8d3136` (Task 1 commit)

**2. [Rule 1 - Bug] Silhouette shape/bbox checks (16-19) broke against the new dithered background**
- **Found during:** Task 2, first `test_render.py` run after wiring the mood background
- **Issue:** Three pre-existing checks isolated the aircraft silhouette by testing `pixel == IDX_WHITE` directly - correct only because the old flat background contained zero White pixels outside text/silhouette. Once the background became a dithered mood gradient (which legitimately contains ~19.7% White everywhere), this check's `getbbox()` on a `pixel == IDX_WHITE` mask returned a spurious full-canvas-width bounding box `(0, 288, 1200, 932)`, failing the safe-box assertion even though the actual render was correct.
- **Fix:** Re-expressed all three checks to diff the fully-composited canvas's silhouette band against the *same state's* un-silhouetted mood background (`dither.build_mood_background()`, deterministic and memoized, so a stable ground truth) - any pixel differing from that reference is unambiguously something `draw_silhouette()` painted, immune to background dither noise. Same root cause and same "may need to re-express" allowance the plan explicitly gave checks 12-13.
- **Files modified:** `server/test_render.py`
- **Verification:** All three checks pass again with the diff-based isolation; visually confirmed against the departing/arriving preview PNGs that the silhouette's actual bounding box is correctly computed.
- **Committed in:** `76d58a8` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - bugs surfaced by this plan's own changes, not pre-existing issues)
**Impact on plan:** Both fixes were necessary for the plan's own acceptance criteria (render-time budget, silhouette geometry checks) to actually hold. No scope creep - no files touched beyond `dither.py` and `test_render.py`, which the plan already scoped for this work.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required. `write_calibration_preview()` is a local developer tool (writes three PNGs to a caller-supplied directory), not a runtime dependency.

## Next Phase Readiness

- `dither.dither_to_full_panel_palette()` and the `illustration_bbox` parameter on `_assert_palette_contract()` are wired and ready for 03-03's per-airline illustration work - no further signature changes needed on that function.
- `dither.write_calibration_preview()` ships the three PNGs (`palette-swatches.png`, `mood-departing.png`, `mood-arriving.png`) 03-04's on-glass calibration pass needs; `MOOD_LIGHT_TINT_MIX`/`MOOD_NOISE_AMPLITUDE`/`MOOD_NOISE_SEED` are explicitly flagged starting points for that checkpoint to tune.
- Open item carried forward from 02-05 (A-02-02-01, the real-departure threshold) is unaffected by this plan and remains open for the phase.
- The fresh on-glass legibility checkpoint 03-CONTEXT.md requires before phase close (Zilla Slab + dithered background + quiet-zone captions, none of which are covered by Phase 2's flat-background finding) has not yet run - still pending a later plan/checkpoint in this phase.

---
*Phase: 03-visual-polish-on-real-glass*
*Completed: 2026-08-26*

## Self-Check: PASSED

All 4 claimed files found on disk (`server/plane/dither.py`, `server/test_dither.py`, `server/plane/render.py`, `server/test_render.py`). Both claimed commit hashes (`e8d3136`, `76d58a8`) found in git log.
