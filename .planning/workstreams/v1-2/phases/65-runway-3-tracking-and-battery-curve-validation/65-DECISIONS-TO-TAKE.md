# Phase 65: decisions the owner has to take (draft, 2026-11-17)

One line per finding, with the evidence, the proposal and a recommendation. Nothing below is started. Reply per finding with **agree**, **refuse** or **defer**; a finding not named is recorded as deferred. Rule (D-04): no detection or enrichment change without the owner's agreement; every fix starts from a failing test built from the recorded case; golden hashes and `stub-server/test_phase47_freeze.py` stay green.

| Id | Finding | Evidence | Proposal | Recommendation |
|---|---|---|---|---|
| F-01 | Real landings detected but never drawn | 3 of 7 aircraft in the 2026-11-15 live session; 27 cycles with a drop against 36 promoted over 3 h 35 | keep and document (the frame is a "right now" board, a 300 s wake cannot show every aircraft); optionally show dropped aircraft as "not shown" in the companion | **agree to document; defer the companion change** |
| F-02 | No route when adsbdb does not know the callsign | 12.4 % of 5031 events over 15 days; TVF18BM (Beirut) | a second route source (needs a terms check) or accept the airline-only display | **defer** (product and terms decision) |
| F-03 / G-02 | A stale route without the watched airport is shown | 410 of 4409 complete routes over 15 days (about 50 a day before 2026-11-12, 1 to 3 after); EJU69MC (Orly), EJU9040 (Nantes), EJU9790 (Lyon) | in `route_sanity.route_contradicts()`, also reject a complete route that has no watched airport in the matching role, then show the airline only | **agree to a test-first fix** (cases: TVF47HR, VLG6VM, IBE05KY, AFR78KG, EJU69MC, EJU9040, EJU9790). Risks to cover in tests: diversions and position mode |
| F-04 | Carried-over arrival/departure state of 2026-11-11 | not reproducible (no `poll_cycles` before 11-15); a guard exists since 2026-11-13 | add a test: an arrival followed by a take-off roll inside the +/-200 ft/min deadband | **agree to a test only** |
| F-05 | DAH1109 possibly not detected | unresolved; needs touch-down time and hex | none | **defer** unless the owner has the details |
| F-06 | A queued aircraft is invisible in "recent flights" | a row is written at display or drop; up to about 150 s later | document | **agree to document** |
| G-01 | The data source loses low aircraft at some airports | Roissy: 1 of 5 movements detected; arrivals silent 3.7 to 5.7 km out (position age 33 to 40 s); departures first seen above 3000 ft | document; later: a coverage check when a frame is set to an airport, or a second source | **defer** (product decision; commercial terms of the other sources apply) |
| G-03 | Unknown callsign prefix: no airline, no route | ITI21KZ (Lyon) | add the prefix to the airline table after checking the ICAO designator | **agree** (small data change, test with the recorded case) |
| G-04 | Departures near the 3000 ft ceiling | AFR57NL seen at 2800 ft; EJU78AN and EJU74TA first seen above 3000 ft | collect more departures before touching the ceiling; no change now | **defer** |

## Coverage not achieved (recorded, not passed)
Nantes: 1 movement of the 3 arrivals and 3 departures targeted. Lyon: 1 arrival, nothing on 35R/35L. Roissy: no detection on the north pair. Orly 06/24 and 02/20: not observed (depends on the wind). An untested runway is not a passed one.

## What would close TRK-02
The owner decisions above, the fixes marked "agree" (plan 65-14, test first), and either more sessions on the uncovered runways or their recording as "coverage not achieved" with the cause.

## Decisions taken by the owner on 2026-11-17

| Finding | Decision | Where |
|---|---|---|
| G-02 (route without the watched airport) | Fix, test first | PR #457, merged |
| H-02 (landing roll-out drawn as a departure) | Fix, test first | PR #458 |
| H-01 (aircraft detected but not drawn) | Keep the screen pace; enrich the recent-flights row with route and direction | PR #458 |
| H-04 and the 25 % of flights with no route | OpenSky ruled out: its terms need a written licence for operational REST API use. The seed and the phase inserted for it were deleted the same evening. Six airlines added by name; the rest is the owner's choice | `COMPLIANCE.md` (OpenSky entry), PR #461 |
| F-01..F-06, G-01, G-03, G-04, H-03 | Still open: decision pending | this file |

Evidence for H-01..H-04: `65-TRACKING-MULTI-EVENING.md`.
