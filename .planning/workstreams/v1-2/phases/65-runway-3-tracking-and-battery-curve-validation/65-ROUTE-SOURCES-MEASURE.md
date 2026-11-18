# Phase 65: which free source gives the right route (measured 2026-11-18)

Question: for the flights of the evening of 2026-11-17 (16:30 to 18:30 UTC) at Nantes, Lyon, Roissy and Orly, how often does each free route source give the route Flightradar24 gave?

Method. The 155 flights of `65-TRACKING-MULTI-EVENING.md` that were drawn and matched to a Flightradar24 flight (time, direction, aircraft type) form the truth table (`data/route-sources-2026-11-18/truth.json`; the reference lists of Lyon and Nantes are in the same folder, those of Roissy and Orly in `data/live-2026-11-17-evening/reference-lists/`). Each callsign was asked to adsbdb, hexdb and the VRS standing data (adsb.lol mirror), as written and with the leading zero of the flight number removed (answers in `results.json`; the two throw-away scripts that built the truth table and asked the sources are not kept, they hard-coded the paths of the session). Answers are those of 2026-11-18, not of the day of the flight. A route is **right** when it links the watched airport to the true other airport in the right direction (multi-leg routes by adjacent airports); **dropped** when it does not include the watched airport (the rule of #457 drops it); **wrong** otherwise.

## Results (148 flights with a callsign; 7 have none)

| Strategy | Right | Wrong | No route |
|---|---|---|---|
| adsbdb alone (before this change) | 118 (80 %) | 8 | 22 |
| VRS alone | 133 (90 %) | 8 | 7 |
| adsbdb then VRS as a fallback | 138 (93 %) | 9 | 1 |
| **VRS then adsbdb as a fallback (shipped)** | **139 (94 %)** | **8** | **1** |
| both must agree when both answer | 132 | 6 | 10 |

On the 33 flights that had no route on the screen (26 with a callsign), VRS gave the right route for 24, a wrong one for 1 and none for 1. hexdb gave the right route for 9, adsbdb for 3 or 4.

Leading zero: it only helps VRS (24 right with it, 22 without). For adsbdb it gains nothing and can give a wrong route (`IBE05RR` returned nothing, `IBE5RR` a route that excludes the watched airport), so it is applied to the VRS key only.

Where adsbdb and VRS both answer with different airport lists (9 flights), VRS is right in 7 and adsbdb in 6; both are right in 4 of them (different lists, same leg at the watched airport).

## Limits
- One evening, 155 flights, and a truth table matched by time and type, not flight by flight. The answers are those of the day after.
- adsbdb and VRS share a lineage (VRS standing data): their agreement is not an independent check.
- 7 flights have no callsign and no source here can be asked.
- The wrong routes (5 % of flights) are not reduced by any combination.
- The VRS update rhythm is not verified.

## What changed
`server/plane/enrich.py` (`resolve_route(leg=...)`, `route_leg()`, the VRS lookup and cache) and `server/poll_cycle.py` (the leg context). Tests: `server/test_vrs_routes.py`. `COMPLIANCE.md` has the VRS entry (CC0).
