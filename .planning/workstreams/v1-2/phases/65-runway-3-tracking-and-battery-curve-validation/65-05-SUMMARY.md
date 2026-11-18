---
phase: 65-runway-3-tracking-and-battery-curve-validation
plan: 05
subsystem: tracking-validation
tags: [trk-01, fixes]
requires: ["65-04"]
requirements: [TRK-01]
status: complete
completed: 2026-11-18
---

# Phase 65 Plan 05: TRK-01 agreed fixes, test-first Summary

F-03 (a route without the watched airport): fixed test-first in #457. F-01 and F-06 (an aircraft detected but not drawn, or waiting in the queue): the screen keeps its pace, and an aircraft dropped unseen now keeps its route and direction in the recent-flights list (#458). F-04 was already covered by `test_departure_on_take_off_roll_does_not_inherit_arriving`. F-02 (routes missing): the VRS standing data is now asked before adsbdb (#468, 80 % to 94 % right on 155 flights, `65-ROUTE-SOURCES-MEASURE.md`) and six airline names were added (#461). F-05 is deferred (no touch-down time and identifier).

