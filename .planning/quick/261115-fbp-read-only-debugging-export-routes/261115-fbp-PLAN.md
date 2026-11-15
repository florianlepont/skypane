# Quick 261115-fbp: read-only debugging export routes

## Problem
Explaining a missed flight or a blank screen meant pasting journal lines from
the VPS by hand. The only remote reader was `/api/export/battery-history`.

## Decision
Extend the bearer-token export with routes that answer the questions asked in
practice, reading `history.db`, `poll_state.json` and `device_config.json`
read-only:
- `flights`: `runway_events` since a time.
- `poll-cycles`: a new bounded trace, one row per cycle that saw, queued,
  dropped or drew an aircraft, kept 14 days, written inside the existing
  single history transaction.
- `status`: one JSON object with the flight on the panel, the display queue and
  its ages, pacing state, a few settings, the check-interval experiment and
  the pipeline heartbeat; fixed field list, no location.

Left out on purpose: a `wake-epochs` route (the epoch table is reserved by a
guard test for a later phase) and any route that returns whole files.
