# Phase 62 Plan 08 Fix: direction word on every layout Summary

Landscape A, B and C now draw the direction word (DEPARTING / ARRIVING / OVERHEAD) small at the top-left, as A+diagonal already did; implements D-15.

## Changes
- `server/plane/render/giant/geometry_landscape.py`: removed the per-layout `direction` flag; all four landscape lettering boxes now start at y = 52/480 (`LETTERING_TOP`), below the 24 px label.
- `server/plane/render/giant/compose_landscape.py`: the direction word is always drawn, with the same wording table (`style.STATE_LABEL_TEXT`) and pairing small-text ink as portrait.
- `server/test_giant_direction.py` (new, 61 tests): for portrait and landscape, all four layouts, departing / arriving / overhead, with Clermont-Ferrand and Pau: the word is ink pixels in its zone, and the zone is untouched by the lettering mask and by the aircraft mask. Each state draws a distinct word. A hyphenated name is lettered without a hyphen in both orientations.

Portrait already showed the word on A, B, C and A+diagonal; no portrait code changed. Hyphen handling already worked (splitter replaces it with a space).

## Verification
ruff, mypy, function-size gate, comment-history guard clean; giant tests plus `server/test_render.py`: 769 passed. Classic output untouched.

Contact sheets (via `layout.build_canvas`, top row departing, bottom row arriving, columns A, B, C, A+diagonal), in `/tmp/claude-0/-home-user-skypane/2e32b3fc-5099-5923-b87b-8baec7f1d443/scratchpad/`:
- `landscape_blue_light_Cler.png`, `landscape_blue_light_Pau.png`, `landscape_red_light_Cler.png`, `landscape_red_light_Pau.png`
- `portrait_blue_light_Cler.png`, `portrait_blue_light_Pau.png`, `portrait_red_light_Cler.png`, `portrait_red_light_Pau.png`

Viewed blue_light Clermont-Ferrand and red_light Pau in both orientations: the word is visible and clean, no hyphen, no overlap.

## Deviations
None.

## Commits
- 4db354d fix(62-08): show the direction word on every landscape giant layout
