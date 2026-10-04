---
quick_id: 261004-ffd
subsystem: companion
tags: [flights, home, dedup]
key-files:
  modified:
    - companion/flight_card.py
    - companion/pages/home_page.py
    - companion/pages/history_page.py
    - companion/test_flights_cards.py
    - companion/test_browser_flights_cards.py
completed: 2026-10-04
---

# Quick 261004-ffd: Flights folds a repeated pass

`flight_card.fold_repeated_passes()` is the one fold both pages use; Home's
behaviour is unchanged. On Flights the fold runs on the fetched rows before the
limit slice and the day grouping. A pass straddling Paris midnight folds into the
newer row, so it is listed once under the later day. Storage is untouched.

## Verification

Full suite 3799 passed, 8 skipped (root-only permission skips); one load-only flake in
test_browser_ux_01 passed on rerun. Render baseline unchanged. ruff, mypy, function-size
and comment-history gates clean.
