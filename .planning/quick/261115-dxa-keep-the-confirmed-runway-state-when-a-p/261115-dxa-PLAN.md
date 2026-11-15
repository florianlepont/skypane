# Quick 261115-dxa: do not blank the frame for an aircraft on the ground

## Problem
On 2026-11-15 at 09:43 UTC the frame showed "Watching Runway 3" for about five
minutes. An A320 reported at altitude 0 (on the pavement) was promoted from
the pacing queue; the state reset added for a different aircraft left it with
no direction, so the empty screen was drawn and held until the next flight.

## Decision
Keeping the previous state for such an aircraft would bring back the bug the
reset fixed (a take-off roll after an arrival shown as "arriving"). Instead an
aircraft on the ground with no inferable direction waits in the queue until it
climbs or descends, or is dropped as stale.

## Tasks
1. `runway_config.awaits_state()` + `is_on_ground()`.
2. `pop_fresh_pending(defer=...)` keeps deferred entries queued; the bootstrap
   branch of `advance_display_queue()` queues a deferred aircraft too.
3. Regression tests (rendered state via `poll_state.json`, history rows) and
   unit tests for the helpers; correct the comment on the empty branch.
