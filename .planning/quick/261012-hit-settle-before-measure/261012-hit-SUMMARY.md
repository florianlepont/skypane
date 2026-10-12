---
quick_id: 261012-hit
slug: settle-before-measure
date: 2026-10-12
type: quick
---

# Quick 261012-hit: summary

## Root cause

`.lightbox` (the shared `<dialog>`) enters with `transform: scale(0.96)` to `none` and an
opacity fade over `--motion-fast` (180 ms) through `@starting-style`. The test waits for
`[open]`, not for the entrance to end, and the probe read the input mid-transition: 287.8 x
43.4 px locally, 290.0 x 43.7 px in CI, about 0.99 of the 290 x 44 settled box (width and
height shrink together, which is why the failure only appears in the y axis against the
floor). The test does not use reduced motion. A quiet machine usually finishes the 180 ms
before the probe runs; a loaded one does not. It reproduced on the first local run on this
machine.

## Fix

`companion/test_browser_ux_helpers.py`: `_hit_area` first awaits every finite animation or
transition whose target is the element, an ancestor or a descendant (infinite ambient
animations and unrelated ones such as toast dwell are not waited for), then two animation
frames. Floor unchanged, no tolerance, no sleep.

`companion/test_browser_hit_area_settle.py`: a control inside a container transitioning from
`scale(0.5)` is reported at its settled 200 x 60, with a mid-flight sanity check that the
transition really was running; an infinite animation elsewhere does not block the helper.

## Verification

- Without the settle step both the new helper test and the airline-sheet test fail (the
  latter with the CI message); with it both pass.
- 12 consecutive runs of the failing parametrisation passed with four busy loops on 4 cores.
- All browser files calling the helper plus `test_suite_guards.py`: 314 passed (`-n4`).
- ruff and `scripts/check_comment_history.py check` clean.
