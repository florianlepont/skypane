# Phase 61 Plan 78: Home signature animation (S1 Respiration + S3 Cycle) Summary

Content-neutral signature on Home (owner decision D-K): a ring around the picture shows the frame cycle until the next update, a glass glint crosses the picture every 12 s, and the picture glow and status dot breathe on a 6 s cycle.

## What changed
- `companion/pages/home_page.py`: `_cycle_ring_html` renders the ring server-side as inline SVG (pathLength 100, `stroke-dasharray`/`stroke-dashoffset` attributes, no style attribute) from the same next-update triple as "Next update in N min"; role img, aria-label "Frame cycle: next update in N min" (FR in `i18n_fr/home.py`); plus the glint overlay span.
- `companion/static/relative-time.js`: the existing 1 s ticker also repaints the ring (offset, aria-label); a swapped refresh whose cycle restarted plays one finite flourish (`is-ring-done`). No new timer.
- `companion/static/style.css`: tokens `--motion-breathe` (6 s) and `--motion-glint` (12 s), picture glow (`.hero__picture::before`), glint (`.hero__glass::after`), ring styles, dot breathing on `.home-state__dot--pulse` (the existing halo pulse is unchanged), reduced motion off in the existing reduce block. Transform/opacity/stroke-dashoffset only; absolute overlays, no layout shift. No transition on the ring bar (a transition would keep a running animation on the page forever and break the "settled" waits).
- Flaky guard fix: `skypane-shimmer` now runs 6 iterations instead of infinite, so it can no longer be an infinite animation while pictures load on /flights.
- Guards extended deliberately, in place: `AMBIENT_LOOPS` and the infinite-animation exemption in `test_browser_overhaul_sweep.py` (justification comment), token/spender contract in `test_companion_app_04.py`.
- New `companion/test_browser_home_signature.py` (11 tests): ring progress vs freshness data at 1/2/4 min, accessible name EN/FR, no-JS server render, glint and breathing on Home only and none under reduced motion, no layout shift and no overflow at 390/1280/360, ring geometry in both themes, refresh flourish.
- Render baseline regenerated.

## Deviations
- Ring progress cycle length is the effective wake interval from the same triple (not a fixed 5 min).
- The glint is pure CSS (infinite 12 s cycle, rests most of it) rather than the demo's JS timer, so no new timer.

## Screenshots
scratchpad `shots78/` (home 390/1280, light/dark).
