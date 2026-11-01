---
phase: quick-261101-hk2
plan: 01
subsystem: detection
tags: [position-mode, overhead, radius, altitude]
requirements-completed: [DET-03]
key-files:
  modified:
    - server/detection.py
    - server/plane/detect.py
    - server/plane/runway_config.py
    - server/poll_cycle.py
    - server/themes.py
    - server/plane/render/style.py
    - server/plane/render/layout.py
    - server/plane/render/landscape.py
    - server/plane/render/landscape_card.py
    - companion/pages/home_page.py
    - companion/pages/history_page.py
    - companion/pages/detection_page.py
    - companion/detection_summary.py
    - companion/i18n_fr/home.py
    - companion/i18n_fr/detection.py
completed: 2026-11-01
---

# Quick 261101-hk2: position mode without ceiling, 2 km minimum, OVERHEAD state

Position mode now admits any airborne altitude, accepts radii from 2 to 28 km, and draws a level aircraft as OVERHEAD (frame only, position mode only, persisted state unchanged).

## Tasks and commits

1. `ded28e60` Position docs carry `alt_ceiling_ft: None`; `position_candidates` treats it as no upper bound (floor of -1500 ft and the ground, bool, string and NaN rejections kept). `RADIUS_KM_MIN = 2`, with a comment on the up to 0.7 km centre rounding offset.
2. `05660223` Hint, error, caption and summary detail in EN and FR; test constants updated; D-29 added to 53-CONTEXT.md; 53-UI-SPEC.md copy updated.
3. `6d98306f` `runway_config.STATE_OVERHEAD` and `display_state()`. `poll_cycle` uses it in `_render_promoted`, `_render_held` and the previous-card state only. `last_confirmed_state` and `previous_confirmed_state` still hold only departing/arriving/None, and `poll_state` gains no key. Tables in themes, style, layout (band label joins non-empty parts, so "OVERHEAD NEARBY"), landscape and landscape card accept the state.
4. `023cce61` Home tile and Flights row labels ("Overhead" / "Au-dessus"); overhead rows count under All only.
5. Gate: no source changes, no commit.

## Verification

- Full suite with browsers: `PLAYWRIGHT_BROWSERS_PATH=.../scratchpad/pw SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` gave 8173 passed, 8 skipped (root-permission skips), coverage 96.26% against the unchanged 93% floor.
- ruff, mypy (28 files), function size (919 functions, none over 80) and comment-history are clean.
- Orly replay, kill switch, pipeline equality, golden render, poll state writes and render baseline tests are green and unmodified. `render_baseline.json` was not regenerated, since no diff appeared.

## Mockups (not committed)

In `/tmp/claude-0/-home-user-skypane/35128d4b-9517-5708-a757-26023530ab20/scratchpad/maquettes`: `overhead_default.png`, `overhead_band_band_blue.png`, `arriving_default.png`.

## Deviations

None. Existing tests that hard-coded the old bounds (radius 3 as refused, 4 km boundary) were updated as the plan directed.
