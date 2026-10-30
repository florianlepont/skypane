---
quick_id: 261030-sfs
description: Harden flaky direction chips Clear test
files: [companion/test_browser_flights_cards.py]
---

# Quick Task 261030-sfs: Harden flaky direction-chips Clear test

## Problem
`test_direction_chips_filter_count_and_clear` failed once in CI with
"expected the empty state's Clear to show every flight". On a phone the search
field animates open after `fill()` and the chips re-wrap, so the empty state's
Clear button can move between Playwright's actionability check and the click.

## Task 1: wait for layout to settle, then for the empty state to hide
- files: companion/test_browser_flights_cards.py
- action: add a `_wait_until_still(page, *selectors)` helper that resolves once
  every selector's bounding box is unchanged for several consecutive animation
  frames. Call it before clicking the empty state's Clear, and wait for the
  empty state to be hidden right after the click. No assertion is removed,
  weakened, skipped or retried.
- verify: the test and the whole flights browser file pass repeatedly under
  `-n auto` with CPU load; ruff and mypy clean.
- done: flake removed at its cause; assertions unchanged.
