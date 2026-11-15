# Quick: record every detected flight and draw the newest

## Problem
On 2026-11-15 flights reported by the owner (TAP43JD, TVF87XA) never reached
the frame or the companion. With the redraw spacing in force (~5 min) the
display queue is drained once per spacing and drops every entry older than the
150 s staleness bound; a dropped aircraft left no record anywhere. The queue
was also served oldest first, so the aircraft drawn was the one that had waited
longest.

## Decision
1. Every aircraft dropped from the queue (stale, or evicted by the depth cap)
   is recorded in `runway_events` in the same history transaction: ts = first
   sighting, airline from the callsign prefix, a direction only if the
   vertical rate or altitude trend gave one, no route lookup, no picture
   (`gallery_name` ""). One row per pass: a second row for the same hex within
   30 min before its timestamp is skipped.
2. When the display may advance, the most recently seen fresh aircraft is
   drawn (`last_seen`, kept on each pending entry). The other fresh entries
   stay queued until drawn or stale.

## Kept
The 150 s staleness bound (a real-time board, not a backlog) and the redraw
spacing itself. Aircraft waiting for a direction are still deferred.

## Not covered
An aircraft the detector never selects (one aircraft per cycle, lowest
altitude first) is not recorded: it is never seen by the poll cycle.
