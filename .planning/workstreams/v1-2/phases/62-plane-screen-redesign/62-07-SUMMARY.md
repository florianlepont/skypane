---
phase: 62-plane-screen-redesign
plan: 07
subsystem: render
tags: [layout-c, landscape, giant-lettering, dispatch]
requires: [62-06]
provides:
  - "giant layout c in portrait (compose_c.compose_c)"
  - "native 800x480 compositors for a, b, c, a_diagonal (compose_landscape.COMPOSERS)"
  - "giant.supports true for portrait and landscape sizes; giant.build_canvas picks the table by orientation"
key-files:
  created:
    - server/plane/render/giant/compose_c.py
    - server/plane/render/giant/compose_landscape.py
    - server/plane/render/giant/geometry_landscape.py
    - server/test_giant_layout_c.py
    - server/test_giant_landscape.py
  modified:
    - server/plane/render/giant/__init__.py
    - server/plane/render/giant/compose.py
    - server/test_giant_dispatch.py
    - server/test_giant_compose.py
key-decisions:
  - "Landscape reuses the portrait destination-text resolver (compose.lettering_split) through a new orientation argument; no second copy"
  - "Landscape geometry is fractions of the 800x480 mock, held in geometry_landscape.SPECS"
requirements-completed: [PSR-05]
completed: 2026-11-09
---

# Phase 62 Plan 07: Layout C and the landscape family Summary

Layout C (lettering compressed at the top, whole aircraft at the bottom, no band) and native 800x480 versions of A, B, C and A+diagonal with the destination on one stretched line. Four layouts x two orientations are now reachable through `layout.build_canvas`.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Layout C portrait | e371531 | `compose_c.py`; lettering box 138-888 px of 1600, whole aircraft 1116 px wide centred at y 1072; `compose.py` helpers parameterised (orientation, whole/halves placement fractions, `paint_text_mask`) |
| 2 Landscape family and dispatch | 04588b5 | `geometry_landscape.py` (specs per layout), `compose_landscape.py`, dispatch tables in `giant/__init__.py` |

## Notes

- `layout.py` untouched: plan 06's forwarding picks the landscape table because `giant.supports` now accepts any non-square size.
- Landscape small text follows the mocks: B and C footer bottom-left, A footer at x=430, A+diagonal footer right-aligned with the direction word top-left. Only the diagonal mock shows a direction word, so landscape A, B and C do not draw one (the lettering box starts 24 px from the top).
- Landscape status marks use the existing landscape card glyphs (battery-low, source-fault); on layouts with a bottom-left footer the footer moves right while a mark is shown so they never overlap.
- Threat T-62-10: the landscape line is one split-destination line, bounded by the splitter's length cap; squeeze is just the stretch of one capped line.
- Landscape holds still follow the existing path (plan 08).

## Deviations from Plan

**1. [Rule 1 - Bug] Two obsolete tests updated.** `test_giant_dispatch.py` asserted a giant layout on the landscape profile equals classic; `test_giant_compose.py` used layout "c" as the example of a layout with no compositor. Both now test the new behaviour (native landscape; an unknown id falls back to the default).

**2. [Rule 2] Status marks in landscape.** The portrait glyph functions use absolute portrait coordinates, which fall off an 800x480 canvas, so the landscape card's size-derived glyphs are reused.

## Verification

- New: `test_giant_layout_c.py`, `test_giant_landscape.py` (61 tests) pass: packed length 192000 for every layout, one ink band for long, 3-letter, airline-only and unknown routes, airline-only and "UNKNOWN FLIGHT" wording, Pau on one line, legal palette for every pairing, classic landscape bytes unchanged.
- ruff, mypy (31 files plus the four new modules), function-size gate, comment-history check clean; `test_render.py`, `test_golden_render.py`, giant compose/dispatch/profile-dispatch tests pass.
- No Phase 47/47.1, hardware/ or golden fixture touched.

## Visual comparison (scratchpad renders, fake Air France Paris to Marseille / Clermont-Ferrand)

Files: `/tmp/claude-0/-home-user-skypane/2e32b3fc-5099-5923-b87b-8baec7f1d443/scratchpad/out/sheet-land.png` (rows Marseille, Clermont-Ferrand; columns A, B, C, A+diagonal), `.../out/sheet-portrait-c.png`, individual `land-*.png` and `portrait-c-*.png` in the same folder.

- Landscape A, B, C match landscape-800x480.png closely (nose top-right, rear bottom-left, whole plane centred, C plane bottom-right, footers where the mock has them). The A+diagonal render matches the diagonal mock in structure.
- Visible differences: the aircraft height and the A rear half sit a few px off the mock (placement derived from fractions); the lettering uses the Pillow Anton stretch, so glyph edges are slightly different; Clermont-Ferrand renders as "CLERMONT FERRAND" (hyphen becomes a space, as the splitter specifies).
- Portrait C: Clermont-Ferrand splits into 2 lines (CLERMONT / FERRAND), whereas the long-names mock hand-split it into 3 (CLER / MONT / FERRAND); Marseille splits MARS / EILLE. The splitter (plan 04) calibrates to the full-height box, so in the shorter C box it picks fewer lines. Aircraft placement and size match the mock's third column.

## Known Stubs

None.

## Self-Check: PASSED

Files exist; commits e371531 and 04588b5 present.
