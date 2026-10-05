---
quick_id: 261004-fla
type: quick
autonomous: true
branch: claude/flights-load-all
---

# 261004-fla: Flights loads the whole list at once

## Objective

Flights rendered 15 rows and a "Show more (N remaining)" link driven by `?limit=`.
The owner wants every flight (up to HISTORY_ROW_LIMIT = 50) in the first response
with no paging step.

## Tasks

1. Remove the page size, the `?limit=` parsing and clamping, the page-context
   field, the Show-more markup, its swap region, its CSS and its EN/FR strings;
   the filter bar always counts every rendered flight.
2. Tests: served-HTML checks (50 cards, no Show more, legacy `?limit=` ignored,
   folded duplicates, chip counts) and a browser check at 390 px; delete the
   Show-more tests; regenerate the render baseline.
