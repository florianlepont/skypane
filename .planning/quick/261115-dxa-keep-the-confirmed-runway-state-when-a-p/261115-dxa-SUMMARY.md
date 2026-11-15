---
status: complete
---
# Quick 261115-dxa summary

An aircraft on the ground (`on_ground` or altitude 0) whose vertical rate gives
no direction is deferred in the display queue instead of being promoted with an
empty state. The frame keeps showing the current flight; the aircraft is shown
once it climbs or descends, and dropped after the staleness limit otherwise.

Files: `server/poll_cycle.py`, `server/plane/runway_config.py`,
`server/test_flight_state_and_stale_route.py`, `server/test_runway_config.py`.

Checks: server and stub-server suites (3993 passed), ruff, mypy, function-size
gate, comment-history guard.

Not changed: an airborne aircraft inside the deadband with no held state still
draws the empty screen.
