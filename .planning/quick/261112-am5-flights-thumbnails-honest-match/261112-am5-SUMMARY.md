---
status: complete
---
# Quick task 261112-am5: Flights thumbnails that belong to the flight

- `companion/pages/history_page.py`: `matching_gallery_entry()` (window `GALLERY_MATCH_BEFORE_S`=90 / `GALLERY_MATCH_AFTER_S`=10), `_stand_in_thumb_html()`; the earliest-render fallback is gone.
- `companion/static/style-flights.css`: `.history-card__thumb--illustration` and `--none`.
- Tests: `test_view_pages_02.py` (window, no fallback, stand-ins), `test_flights_cards.py`, `test_view_pages_01/03/04.py` adjusted to renders stamped near their flights, `test_browser_flights_stand_in.py` (new), shared fixture now archives one render per flight.
- `render_baseline.json` regenerated.

Findings:
- Not every airline has an illustration (Pegasus has none), so the plane icon is a required second fallback.
- The window is a heuristic on timestamps; a render of another event stamped inside the window would still match. Exactness would need the server to store the render name with the flight (`server/poll_cycle.py`, out of scope here).
