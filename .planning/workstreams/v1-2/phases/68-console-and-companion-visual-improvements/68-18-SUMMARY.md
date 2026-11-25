---
phase: 68-console-and-companion-visual-improvements
plan: 18
subsystem: frame-screens
tags: [retired-screen, e-ink, cache]
requires: [68-01, 68-11]
provides: [retired frame screen with the Reset line, revisioned retired panel cache]
key-files:
  modified:
    - server/plane/render/giant/status.py
    - server/pairing_image.py
    - server/test_pairing_image.py
    - server/test_giant_status.py
    - stub-server/byos_server.py
  created:
    - stub-server/test_byos_retired_screen.py
requirements: [CON-01]
completed: 2026-11-18
---

# Phase 68 Plan 18: Retired frame screen Summary

The retired frame screen now reads "This frame was removed from SkyPane." / "Press Reset to set it up again." (English only, EE02 and EE04), through a new `status.build_retired(size)`; already-retired frames pick it up at their next wake through a revisioned panel cache name.

## What changed

- `status.py`: `build_status` body moved into private `_build` with an optional body override (pure refactor); new `build_retired(size)` and `RETIRED_RESET_BODY_LINES`. `RETIRED_BODY_LINES`, `_LINES`, `_BODIES` untouched.
- `pairing_image.py`: `RETIRED_SCREEN_REVISION = 2`; `render_retired_image` uses `build_retired` (landscape variant and portrait reference). Signature unchanged (no code argument).
- `byos_server.py` (10 added / 1 changed lines): `RETIRED_PANEL = "retired-r<rev>.bin"`, `LEGACY_RETIRED_PANEL`, a small `_remove_quietly` helper, and removal of the legacy `retired.bin` after a fresh write in the existing retired branch. `RETIRED_SLEEP_S` and the `(image, sleep)` shape untouched.
- Goldens: `RETIRED_GOLDEN_SHA256` changed on purpose (`7222f198...` to `7251991e...`); new `RETIRED_LANDSCAPE_GOLDEN_SHA256` (`f6fd51ea...`). Giant manifest (`status_retired_portrait`/`status_retired_landscape`, which cover `build_status("retired")`), `test_golden_giant_render.py`, `test_golden_render.py`, `pairing_code.py`, `test_phase47_freeze.py` and the companion are not edited.

## Text as rendered (all hardware types, same)

1. This frame was removed from SkyPane.
2. Press Reset to set it up again.

The plan 27 messages (confirmation: code at next wake, up to 24 h, press Reset to see it at once) use the same "Press Reset" gesture wording.

## Verification

Focused run: pairing image, giant status, both golden render suites, byos retired/pending/freeze/pairing-freeze tests, pairing_code: 225 passed. ruff clean, function size (max 80) clean, comment history clean, mypy shows only the 13 pre-existing PIL errors. `companion/app.py` still 1490 lines.

Real-renderer full-screen captures (before and after), looked at: portrait fits with no overflow, landscape fits; text sits flush left like every calm status screen. In `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p18/`: `before_ee02.png`, `after_ee02.png`, `before_ee04.png`, `after_ee04.png`.

## Deviations from Plan

None beyond the owner-approved header overriding the plan wording.

## Design-system divergences

None (frame e-ink screen, no companion UI; the companion design system does not apply).

Owner-header override noted, not a design-system divergence: the plan's per-hardware `reset_hint` mapping was not built because the owner approved one identical English line for EE02 and EE04 with no Reset location; `build_retired(size)` therefore takes no hint.

## Self-Check: PASSED
