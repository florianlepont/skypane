---
phase: quick-260831-njw
plan: 01
subsystem: server/plane (panel renderer)
tags: [render, typography, tracking, spike-002a]
dependency graph:
  requires: []
  provides:
    - "server/plane/render.py: LABEL_TRACKING_PX, draw_tracked_text(), _tracked_text_width(), _tracked_text_bbox()"
    - "server/plane/render.py: draw_top_labels() drawing both top-row roles tracked at 6px"
  affects:
    - "server/plane/render.py draw_top_labels() callers (_build_active_canvas())"
tech-stack:
  added: []
  patterns:
    - "glyph-by-glyph text compositing for tracked/letter-spaced text (Pillow has no native tracking API)"
key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py
decisions:
  - "6px tracking (LABEL_TRACKING_PX) applied to STATE_LABEL_FONT (20px) and TOP_TAG_FONT (18px) only - no size reduction, per spike 002a's tracked-6px validated variant"
  - "Runway tag positioned by pre-computed tracked width (WIDTH - MARGIN - tracked_width) instead of Pillow's anchor='ra', since tracked text has no native right-anchor equivalent"
  - "Deviation: plan's overflow-sweep example used the 'sky' theme as the dithered leg; Phase 8 retired 'sky' (11 pure/light themes replaced it) - substituted 'grey' (currently the bold/dithered theme)"
metrics:
  duration: "~35 minutes"
  completed: 2026-08-31
status: complete
---

# Phase quick-260831-njw Plan 01: Add 6px letter-spacing (tracking) to the top-row labels Summary

6px letter-spacing (tracking) added to the panel's two smallest top-row text roles - the state label ("DEPARTING"/"ARRIVING", 20px) and the runway tag ("ORY · RWY 3", 18px) - both drawn glyph-by-glyph via a resurrected `draw_tracked_text()` helper, at unchanged font sizes, per spike 002a's validated finding.

## What Shipped

**Task 1 (commit `22a13c7`):** Resurrected `LABEL_TRACKING_PX = 6`, `draw_tracked_text()` (public), `_tracked_text_width()` (private) and `_tracked_text_bbox()` (private) in `server/plane/render.py`, ported verbatim from commit `73a6eb2^` (deleted by the two-flight poster redesign because the zone changed, not because tracking failed - D-15). Nothing called them yet; `draw_top_labels()` was confirmed byte-unchanged via `git diff`. `server/test_render.py` grew from its real on-disk baseline of 101 checks to 104: constant/naming-split presence, `_tracked_text_width()` arithmetic (empty/single-char/multi-char/zero-tracking, derived from `font.getlength()`), and `draw_tracked_text()`'s per-glyph draw count/anchor/advance/return-value. The third check was demonstrated failing under a deliberate regression (tracking omitted from the advance) and restored before commit.

**Task 2 (commit `f0ed5df`):** Rewrote the drawing half of `draw_top_labels()` - both the state label and the runway tag now draw via `draw_tracked_text(..., tracking=LABEL_TRACKING_PX)`. The tag's start x is pre-computed as `WIDTH - MARGIN - _tracked_text_width(tag_font, tag_text, LABEL_TRACKING_PX)` (Pillow has no `anchor="ra"` equivalent for glyph-by-glyph tracked text), so its run still ends flush at `WIDTH - MARGIN`. Both `_assert_within_canvas()` guards now measure `_tracked_text_bbox()` geometry instead of the untracked `draw.textbbox()`, which would have silently under-reported a tracked run's width (T-njw-02).

`server/test_render.py` reconciliation:
- 3 broken checks rewritten (not deleted/weakened): the two D-26 top-row checks (numbered 14-15) and the runway-tag-selection check (numbered 65) now reconstruct each glyph run from consecutive single-character `_TextSpy` captures at `y == MARGIN`, relying on `draw_top_labels()`'s own fixed draw order (label first, then tag) rather than x-sorting.
- 2 stale docstrings corrected (module docstring + `_TextSpy` class docstring), which previously claimed the module's text-draw seam had no glyph-by-glyph compositing path.
- 3 new checks added: inter-glyph advance (every consecutive origin pair differs by exactly `font.getlength(previous_char) + LABEL_TRACKING_PX`, derived from the real font); an overflow sweep across every registered runway id x both active states x a flat and a dithered theme, asserting no `AssertionError` and a non-negative tag start x; and a tracking-containment check proving the main card's line 1, the previous card's line 1, and the source-fault caption are each still drawn as one whole-string call, with the total single-character draw count equal to exactly `len(label_text) + len(tag_text)`.
- `EXPECTED_CHECK_COUNT` bumped 101 -> 104 (Task 1) -> 107 (Task 2), each bump computed from the real on-disk count at execution time, not assumed from the plan's stated 101.
- The overflow sweep was demonstrated failing under a deliberately inflated `LABEL_TRACKING_PX` (90, pushing the longest tag well off the left edge) and restored to 6 before commit.

Final state: `server/test_render.py` passes 107/107.

## Deviation from Plan

**[Rule 1 - stale plan context] Substituted the "grey" theme for the plan's "sky" example in the overflow sweep and visual handoff artifacts.**
- **Found during:** Task 2, writing the overflow-sweep check.
- **Issue:** The plan's context section and its literal verification scripts use `"sky"` as the example dithered theme. Phase 8 (completed earlier the same day, per `.planning/STATE.md`) retired `"sky"` entirely, replacing it with 11 pure/light theme entries (`white`, `black`, `grey`, `yellow`, `yellow_light`, `red`, `red_light`, `green`, `green_light`, `blue`, `blue_light`). `render.device_config.THEME_IDS` has no `"sky"` member; using it raises `KeyError`.
- **Fix:** Substituted `"grey"` - confirmed via `device_config.theme_weight()` to currently be a bold/dithered theme, matching the plan's intent of exercising "a flat and a dithered theme" - in the overflow-sweep check, its inline adapted verification script, and the third preview PNG (`njw-tracked-grey-departing.png` in place of a `sky` variant).
- **Files modified:** `server/test_render.py` (the overflow-sweep check and its comment).
- **Commit:** `f0ed5df`

No other deviations - both tasks otherwise executed exactly as written, including the prior-art port (verbatim from `73a6eb2^`), the exact naming split, and the geometry the plan pre-measured (verified: regular-weight `tag_x = 974.0` for the default runway, matching the plan's own measured table exactly).

## Known, Pre-Existing Exception: `server/test_poll_loop.py` digest mismatch

`scripts/run-all-tests.sh` reports exactly one failure: `server/test_poll_loop.py`'s pinned `panel.bin` `_DEFAULT_CONFIG_DIGEST` check (`2c511df1...` locally vs. pinned `eb137945...`). This is expected and was **deliberately NOT re-pinned**:
- This change moves real render pixels (the top-row glyphs are now drawn with extra advance between them), so the digest mismatch is a real, expected consequence, not a bug.
- The digest must be re-pinned only from a real CI FAIL output - this Mac and the CI container render fonts differently (five prior re-pins in that file's history, most recently Phase 8's plan 08-05, confirmed the same way). A locally-computed value would be wrong for CI.
- A CI-based re-pin is a separate, heavier workflow (push + open a PR purely as a CI trigger) explicitly out of scope for this quick task.
- Confirmed this is the *only* failure: `bash scripts/run-all-tests.sh` output showed 15/15 other harnesses green, 90% coverage, before the single `FAILED harnesses (1): server/test_poll_loop.py` line.

## NOT VERIFIED ON REAL GLASS

**This change is screen-preview-validated only.** 6px tracking on the top-row labels has never been checked against real Spectra 6 ink at any point in this project's history - `hardware/BRINGUP-LOG.md` has no mention of tracking, even though this exact technique (glyph-by-glyph `draw_tracked_text()` at `LABEL_TRACKING_PX = 6`) shipped once before in Phase 2/3 before being removed by the D-25/D-26 two-flight-poster redesign (removed because the zone changed, not because tracking failed on real glass or on screen).

The on-glass check for this specific change remains **OPEN**, per this project's own D-13 precedent (every visual/typography change needs a real on-glass check before being considered final). This plan does not attempt it and does not claim it. The next natural session to reopen the panel over SSH against the real deployed VPS should hold these three preview PNGs up against the spike's own `tracked-6px` contact-sheet row and confirm by eye that neither label clips or collides on real ink, on both a flat and a dithered theme.

## Visual Handoff Artifacts (scratch, not committed)

- `/tmp/njw-tracked-white-departing.png` - White theme (flat/regular weight), DEPARTING state, runway 3 default tag
- `/tmp/njw-tracked-white-arriving.png` - White theme (flat/regular weight), ARRIVING state
- `/tmp/njw-tracked-grey-departing.png` - Grey theme (dithered/bold weight, substituted for the plan's retired "sky" example), DEPARTING state

Both reviewed by eye during this session: tracked all-caps top row reads cleanly on both themes, right-aligned tag ends flush at the margin, no clipping or collision at any registered runway/theme/state combination exercised by the overflow sweep.

## Self-Check: PASSED

- FOUND: server/plane/render.py
- FOUND: server/test_render.py
- FOUND: .planning/quick/260831-njw-add-6px-letter-spacing-tracking-to-the-t/260831-njw-SUMMARY.md
- FOUND: commit 22a13c7 (Task 1)
- FOUND: commit f0ed5df (Task 2)
