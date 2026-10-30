---
quick_id: 261030-sfs
status: complete
commit: f377583
---

# Quick Task 261030-sfs: Harden flaky direction-chips Clear test

**Result:** `test_direction_chips_filter_count_and_clear` now waits for the phone
search animation and chip re-wrap to settle before clicking the empty state's
Clear, then waits for the empty state to hide. All assertions are unchanged; no
retry or skip.

**Root cause (inferred, not reproduced):** the failure never reproduced locally
(6/6 plain, 12/12 with forced refreshes, 15/15 under 20x CPU throttle), and the
live-refresh theory was ruled out (45 s interval, swap re-applies the filter in
the same task). The CSS shows a real layout shift: `fill()` sets
`data-filter-active`, the search animates open (`flex-basis` transition) and the
chips wrap, moving the empty state's Clear button during the click.

**Verification:** ruff and mypy clean, comment-history guard passes; flights
browser file 8/8 passes with `-n auto` under 4 CPU busy loops; the single test
15/15 passes.

**Caveat:** because the original flake was not reproduced, passing runs cannot
prove it is gone; the next CI runs are the real test.
