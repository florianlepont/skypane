# Quick task 261112-cny: Link each flight to its archived render

Problem: the Flights page matched a flight to a render by timestamp window (90 s before, 10 s after). Nothing stored which render a flight was shown with, so the match was a heuristic.

Decision (owner allowed touching `server/poll_cycle.py`):
- `runway_events.gallery_name TEXT`, added by a guarded ALTER (no schema version). NULL = row written before the column; "" = the cycle that recorded the flight archived no render; else the gallery file name.
- `_save_to_gallery()` returns the archived name; `publish_canvas()` keeps it on `ctx.gallery_name`; `_record_history()` stores it with the flight in the same cycle (same `now_iso`, so the name is exact).
- Flights page: a row that stores a name links that file (none if the gallery pruned it, none for ""); only NULL rows use the 90 s window. `fold_repeated_passes` lets the kept (newest) row inherit the name of the older sighting it folds away.

Out of scope: frame protocol, intervals, phase 47/47.1, `hardware/`, `server/plane/*`.

Tasks:
1. `history_db.py`: column in CREATE, INSERT, guarded ALTER.
2. `poll_cycle.py`: name returned, carried on ctx, stored with the event.
3. `history_page.py`, `flight_card.py`: use the stored name.
4. Tests: poll cycle stores the name, empty name, old-database migration, page behaviour, fold carry.
