---
phase: 65-runway-3-tracking-and-battery-curve-validation
verified: 2026-11-18T08:00:00Z
status: complete
score: 4/4 criteria met; Orly 06/24 left untested by the owner's decision
verdict: complete; the one runway not observed is recorded, and the owner chose not to test it
re_verification: false
open_points_owner_action: []
---

# Phase 65: Detection Robustness - Verification Report

**Phase goal:** The owner can trust that the detection follows the right aircraft, on Paris-Orly runway 3 first and then on the other Orly runways and on other French airports.
**Verified:** 2026-11-18 against `main` after #468. Evidence is in `65-EVIDENCE.md`, `65-TRACKING-MULTI-EVENING.md` and `65-TRACKING-REPLAY.md`.

## Per-criterion result

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Runway 3: every mismatch explained, fixed or written down | MET | Recorded period and live sessions (`65-TRACKING-INTERNAL.md`, `65-TRACKING-LIVE.md`); F-01 to F-06 decided on 2026-11-17 (`65-DECISIONS-TO-TAKE.md`); fixes #457, #458, #468; Orly runway 3 arrivals of 2026-11-17: 16 of 19 drawn, the 3 missing were dropped by the queue |
| 2 | Other runways and airports: observed live on simulated devices and compared | MET, with one runway left untested by decision | Nantes 18 of 18, Lyon 22 of 24, Roissy 88 of 102, Orly 02/20 15 of 22 departures, against Flightradar24; every miss explained. **Orly 06/24 was not in use and is not tested; the owner decided on 2026-11-18 that it need not be** (recorded as such) |
| 3 | Any fix is agreed, test-first, keeps the golden hashes and the freeze | MET | #457, #458, #461, #466, #468: tests that failed first; owner agreement quoted in `65-DECISIONS-TO-TAKE.md`; full suites green with the golden hashes and `stub-server/test_phase47_freeze.py` |
| 4 | The live frame's configuration is not changed during any session | MET | Isolated scratch roots; the live export was read only |

## Requirements
TRK-01 met. TRK-02 met; Orly 06/24 was not in use during the sessions and the owner decided on 2026-11-18 not to test it.

## What is written down, not fixed
F-02 routes missing (remaining: 7 flights without a callsign), H-04 wrong routes (about 5 % of flights), G-01 and H-03 coverage of the ADS-B source, H-01 the pace of the screen, F-05, F-06, G-04. OpenSky was ruled out by its terms (`COMPLIANCE.md`); paid route APIs were not tested by the owner's decision of 2026-11-18, the free sources reaching 94 % right.

## Deployed
The owner deployed `main` to production on 2026-11-18 (the VRS routes and the state fixes are live). Nothing is open for the owner in this phase.

## Raised for Phase 68
Phase 68 candidates raised during this phase: airlines known by name only on the Airlines page, a route sources card, and a status of the route directories (`68-CANDIDATE-ITEMS.md`).
