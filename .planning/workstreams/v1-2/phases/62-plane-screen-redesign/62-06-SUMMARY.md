---
phase: 62-plane-screen-redesign
plan: 06
subsystem: render
tags: [layout, giant-lettering, dispatch, poll-cycle]
requires: [62-02, 62-04, 62-05]
provides:
  - "giant.build_canvas(size, layout, flight, state, route, pairing|theme_id, ...)"
  - "giant.supports(size, layout)"
  - "layout.build_canvas(..., layout=None)"
  - "poll_cycle passes the stored layout to every render call"
key-files:
  created:
    - server/plane/render/giant/compose.py
    - server/test_giant_compose.py
    - server/test_giant_dispatch.py
  modified:
    - server/plane/render/giant/__init__.py
    - server/plane/render/giant/fonts.py
    - server/plane/render/layout.py
    - server/poll_cycle.py
    - server/test_golden_render.py
    - server/test_poll_loop.py
key-decisions:
  - "DEFAULT_LAYOUT_ID stays the single constant (b); poll_cycle reads the stored value through screen_layouts.normalise_layout_id"
  - "Layout c has no compositor yet and renders as the default layout until plan 07; landscape canvases keep the classic picture (giant.supports is portrait-only)"
requirements-completed: [PSR-01, PSR-03, PSR-04, PSR-05, PSR-06]
completed: 2026-11-09
---

# Phase 62 Plan 06: Portrait layouts and dispatch Summary

Portrait giant layouts A, B and A+diagonal now render from the poll cycle: `layout.build_canvas` takes a new trailing `layout` kwarg (None or "classic" keeps the legacy bytes) and the poll cycle passes the frame's stored layout on every render call.

## LIVE-FRAME IMPACT (owner, please read)

Because the stored default is B, a frame that never chose a layout will change its picture at the first poll cycle after this code is deployed: it goes from the classic poster to the giant destination lettering with the whole aircraft in front, flight number bottom-right. Phase 47 measures that frame, so a deploy of this plan alters what it measures. To keep the old picture, save the layout "classic" for that frame before deploying. Nothing was merged or deployed by this plan. Hold screens (empty, quiet hours, display off, battery empty) are unchanged. A landscape profile still shows the classic landscape picture.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Portrait compositors | 60d6d28 | `compose.py` (B, A, A+diagonal), `giant.build_canvas`, Inter Bold loader |
| 2 Dispatch and poll-cycle threading | 03f615e | `layout=` kwarg, lazy giant import, 8 poll-cycle call sites, dispatch tests |

## What was built

- Compose order: field, band (diagonal only, not for the white pairing), lettering, aircraft with white halo, small text, status glyphs. Geometry is fractions of the canvas size.
- Lettering text: destination city (origin when arriving, destination for overhead), else the airline name (D-10), else "UNKNOWN FLIGHT". Accent-free spelling is tried when Anton lacks a glyph. A squeezed split shrinks the box to 85%.
- Small text in Inter Bold: direction word top-left, flight number (route IATA callsign) right-aligned bottom-right, airline name below it (omitted when the airline is already the lettering). Yellow small text is dithered toward black; on the diagonal, small text inside the band takes the field shade. No previous-flight card.
- Colour: the effective theme (rules, arrivals override, calendar) maps to a pairing at render time through `pairing_for_theme`; stored ids are never rewritten.
- Threat T-62-08: the layout id goes through `normalise_layout_id`; unknown values fall back to the default. T-62-09: a test asserts all three layouts render well under 10 s (about 0.5 s each measured).

## Deviations from Plan

**1. [Rule 3 - Blocking] Classic-baseline tests pin the classic layout.** `server/test_golden_render.py::_end_to_end_panel` (the `run_once_panel_bin` case) and `server/test_poll_loop.py::test_default_config_byte_identity` run a full poll cycle with no stored layout, which now renders the default giant layout and changed their hashes. Both now save layout "classic" in their state dir first. `legacy_render_baseline.json`, the golden fixtures and the pinned digest are untouched, and every classic hash still matches.

**2. [Rule 2 - Missing critical] Status glyphs.** The plan did not mention the battery-low icon and source-fault badge; dropping them would hide real faults on the live frame, so the giant layouts draw them (pairing ink, black for yellow) via the existing glyph functions.

**3. Layout c** has no compositor in this plan, so it renders as B until plan 07 (stated in `giant.build_canvas`). `giant.supports` (portrait-only) is the hook plan 07 extends for landscape.

## Verification

- New tests: `server/test_giant_compose.py` (36) and `server/test_giant_dispatch.py` (26) pass.
- Full run of server, stub-server, companion and deploy tests: 9490 passed, 1 failed (the poll-loop digest above, fixed and re-run: 102 passed). Browser tests skipped (no Playwright browser in this sandbox).
- ruff clean, mypy (31 files) clean, mypy clean on the two new giant modules, function-size gate (none over 80), comment-history check clean.
- No Phase 47/47.1, hardware/, golden fixture or classic render code touched. `state.advance-plan` not called.

## Known Stubs

None.

## Self-Check: PASSED

Files exist; commits 60d6d28 and 03f615e present.
