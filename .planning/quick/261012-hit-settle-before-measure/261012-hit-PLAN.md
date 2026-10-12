---
quick_id: 261012-hit
slug: settle-before-measure
date: 2026-10-12
type: quick
---

# Quick 261012-hit: hit-area measurement waits for animations to settle

`test_the_row_opens_a_usable_sheet_in_both_themes[chromium-390-fr]` failed CI three times
with a 43.x px input against the 44 px floor.

## Task

Make `_hit_area` (and so `_assert_hit_target`) measure only after finite animations and
transitions on the element, its ancestors and descendants have finished. Keep the floor,
add no tolerance, no sleep. Add a helper test with a deliberately transitioning container.

## Verification

Repeated runs of the failing parametrisation under CPU load, every browser file that calls
the helper, ruff, comment-history guard, suite guards.
