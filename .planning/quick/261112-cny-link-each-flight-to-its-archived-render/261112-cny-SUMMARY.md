---
status: complete
---
# Quick task 261112-cny: Link each flight to its archived render

- `server/history_db.py`: `runway_events.gallery_name` (CREATE, INSERT, `_add_missing_runway_event_columns`).
- `server/poll_cycle.py`: `_save_to_gallery()` returns the name, `CycleContext.gallery_name`, stored by `_record_history(gallery_name=...)`.
- `companion/pages/history_page.py` (`_picture_for`), `companion/flight_card.py` (fold carries the name).
- Tests: `server/test_poll_loop.py` (2), `server/test_config_history.py` (1), `companion/test_view_pages_02.py` (1), `companion/test_flights_cards.py` (1).

Notes:
- Rows written before this change keep NULL and use the 90 s window; they age out with the 25-render gallery cap.
- A flight whose cycle changed no panel stores "" and shows a stand-in, never a neighbouring render.
- Deploy order: the companion and the poll timer both open `history.db` through `init_schema()`, so whichever runs first adds the column; both tolerate the other adding it.
