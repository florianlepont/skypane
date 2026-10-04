---
quick_id: 261004-ffd
type: quick
autonomous: true
branch: claude/flights-fold-duplicates
---

# 261004-ffd: Flights folds a repeated pass the way Home does

## Objective

The poll loop stores a second event when only the corroboration flag changes, so
one pass could appear twice on Flights while Home already showed it once. Storage
stays as it is; the display folds.

## Tasks

1. Move the Home de-dup (same hex, callsign, route and direction, under 60 s
   apart, newest row kept) into `companion/flight_card.py` as
   `fold_repeated_passes(rows, limit=None)`; Home calls it with its limit.
2. `history_page.history_rows()` folds before anything else, so chip counts, the
   status count, day headers, the `?limit=` slice and "Show more (N remaining)"
   all count flights.
3. Tests: served HTML (59 s folded, 90 s kept, direction change kept, counts and
   day headers, a pass straddling Paris midnight, Show more) and a browser check
   that each chip's count equals the cards shown under it.
