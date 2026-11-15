---
status: complete
---
# Quick 261115-emt summary

`runway_config.altitude_trend_state()` gives a direction from the altitude
change since first sighting; `infer_from_flight()` uses it only when the
vertical rate and the held state decide nothing. `poll_cycle` tags the flight
with `altitude_ref_ft` on every detection and defers any aircraft without a
direction instead of drawing the empty screen. `awaits_state()` now applies to
every aircraft, not only those on the ground; `is_on_ground()` is gone.

Also fixed: a detection queued while nothing was on screen was never written to
`poll_state.json`, so it was lost on the next cycle.

Checks: server and stub-server suites (4013 passed), ruff, mypy, function-size
gate, comment-history guard.

Risk noted: waiting aircraft count against the 150 s staleness limit, so more
of them can be dropped while the redraw spacing is long.
