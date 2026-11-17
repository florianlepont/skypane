# Quick 261115-emt: infer the runway state from the altitude trend

## Problem
Production logs of 2026-11-15 show airborne aircraft at 575-625 ft promoted
with no state and the empty "Watching Runway 3" screen drawn, several times a
day. Their vertical rate is missing or inside the deadband, and a different
aircraft starts without a held state. The earlier fix only deferred aircraft
on the ground.

## Decision
- Tag each tracked aircraft with `altitude_ref_ft`, its altitude at first
  sighting, carried across the in-place refreshes of the queue and the
  current slot.
- With no vertical rate decision and no held state, a change of at least
  100 ft since the reference reads as arriving (down) or departing (up).
- An aircraft still without a direction waits in the queue (any aircraft, not
  only those on the ground) until it has one or goes stale.
- A detection queued with nothing on screen is now persisted.

## Not covered
Aircraft that wait longer than the 150 s staleness limit are dropped without
a history row; reported separately.
