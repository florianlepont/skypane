---
id: SEED-020
status: dormant
planted: 2026-11-17
planted_during: "v1.2, Phase 65: live comparison of four airports against Flightradar24 showed about 20 % of flights with no route."
trigger_when: "A milestone that works on flight data quality, or when the missing route on about one flight in five starts to bother the owner; surface it at /gsd-new-milestone."
scope: medium
---

# SEED-020: Route coverage and leg accuracy (about 20 % of flights have no route)

## Why This Matters

On 2026-11-17 the frames drew a route for about 80 % of the flights. The other 20 % show the airline only, and about 2 % of the routes shown have the right watched airport but the wrong other end. The owner finds the missing routes the more annoying of the two.

The route comes from adsbdb, which maps a callsign to one stored route. It has no entry for many easyJet (EZS, EJU), Ryanair and regional Air France callsigns, and a rotating callsign can return another leg of the same callsign.

## Measured on 2026-11-17 (against Flightradar24)

| Airport | Routes right | Wrong other end | No route |
|---|---|---|---|
| Nantes (evening) | 17 | 0 | 1 |
| Lyon | 18 | 0 | 6 |
| Roissy | 62 | 2 (AF6733 ORD>CDG for PIK, FDX3 CDG>EWR for FRA) | 24 |
| Orly, departures | 13 | 0 | 2 |
| Orly, arrivals (live frame) | most | 1 (TAR634 DJE>ORY for MIR) | several |

Routes that did not contain the watched airport at all (8 of 24 at Nantes that morning) are already dropped: Phase 65 finding G-02. Dropped aircraft now keep a route and a direction in the recent-flights list: Phase 65 finding H-01.

## Ideas, with what is known

- **OpenSky `/flights/arrival` and `/flights/departure`** per watched airport: the leg really observed, keyed on the aircraft's hex. A test on 2026-11-17 corrected AF6733 (EGPK>LFPG). It answered without an account. Limits seen: about a quarter of the departure airports are null, one test showed a delay of about 30 minutes, the anonymous quota is 400 credits a day. Its terms (research and non-commercial) were not read on the official page and `COMPLIANCE.md` has to be updated before any use.
- **hexdb.io and the VRS standing data** (`vrs-standing-data.adsb.lol`, CC0): they agree with each other and add no route that adsbdb lacks on the eight callsigns tested. They disagree with adsbdb on EZS1345 and nothing settles which is right.
- **Same-aircraft history** (the hex that arrived is the one that departs): measured on 2026-11-17 and useless at four airports. Only 1 aircraft of 196 was seen at two watched airports.
- Commercial APIs (FlightAware, AviationStack, AirLabs, AeroDataBox) need a key and their terms were not read. Not recommended.
- A measure first: replay a week of recorded flights through a candidate source and count the routes it adds and the routes it changes, before any code.

## Must not break

The golden hashes of the legacy render and `stub-server/test_phase47_freeze.py`. Any new source follows `COMPLIANCE.md` (non-commercial, no scraping, no key in the repository).

## Breadcrumbs

`server/plane/enrich.py` (adsbdb lookup, cache, airline prefix table), `server/plane/route_sanity.py`, `server/poll_cycle.py` (`_drop_contradicting_route`, `_unshown_route`), `.planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/` (comparison data of 2026-11-17).
