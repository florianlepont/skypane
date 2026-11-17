---
status: complete
---
# Quick summary

`pop_fresh_pending()` now returns the most recently seen fresh entry (new
`last_seen` on each entry, falling back to `first_seen` for entries saved
before it) and leaves the others queued. `enqueue_pending()` and
`pop_fresh_pending()` hand back the entries they drop; `poll_cycle` turns them
into `runway_events` rows (`history_db.record_unshown_event()`), written in
the one history transaction inside its own SAVEPOINT.

Tests: queue semantics rewritten for newest-first (including the burst
tests, with the depth cap now tested on the queue directly), new
`server/test_unshown_flights.py`, a Flights page check for rows stored without
direction, route or picture. Non-browser suites: 11255 passed; ruff, mypy,
function-size gate, comment-history guard, shard check pass. Browser tests not
run locally (no Chromium).

Not covered: aircraft the detector never selects.
