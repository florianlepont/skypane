# Phase 65: multi-airport comparison against Flightradar24, evening of 2026-11-17

Requirement: TRK-02. Method: simulated fleet devices on an isolated scratch state root (never the live frame), polling adsb.fi every 30 s, compared line by line with the airport lists the owner pasted from the Flightradar24 pages. Times below are UTC (Paris time minus one hour). The comparison window is 17:30 to 19:30 Paris time (16:30 to 18:30 UTC). The relevé ran with the Phase 65 fixes already merged (G-02) except where stated.

Data: `data/live-2026-11-17-evening/` (events per device, the live frame's events for Orly runway 3, and the reference lists). Matching of a Flightradar24 flight to a detected event is by time (within 4 minutes), direction and aircraft type. It is reliable for the totals, not proven flight by flight.

## Result per airport

| Airport | Devices | Flightradar24 flights | Shown | Not shown | Shown but not in the list | Routes right | Wrong other end | No route |
|---|---|---|---|---|---|---|---|---|
| Nantes LFRS (simple) | 03/21 | 18 | 18 | 0 | 0 | 17 | 0 | 1 |
| Lyon LFLL (parallel) | 17R/35L, 17L/35R | 24 | 22 | 2 (queue) | 0 | 18 of 24 rows | 0 | 6 |
| Roissy LFPG (four runways) | 08L/26R, 08R/26L, 09L/27R, 09R/27L | 102 | 88 | 14 | 2 (H-02) | 62 | 2 | 24 |
| Orly, runways 02/20 | 02/20 (06/24 saw nothing) | 22 departures | 15 | 7 | 0 | 13 | 0 | 2 |
| Orly, runway 3 (live frame, read from the export) | the live frame | 19 arrivals | 16 | 3 (queue) | 0 | most | 1 (TAR634 DJE>ORY for MIR) | several |

Roissy and Orly are measured on the flights seen between 17:30 and 19:30 Paris time; one departure at each airport at 19:30 (end of the relevé) is left out. Nantes in the morning (before G-02) is the earlier session of the same day: 23 of 23 shown, 8 of 24 routes did not contain Nantes.

Reading: the detection finds the aircraft at the three airport types (simple, parallel runways, four runways). What is missed comes from coverage of the source and from the pace of the screen, not from the runway logic. The one algorithm defect found is H-02.

## Findings

### H-01 An aircraft detected but not drawn (queue pace)
- Evidence [observed]: Lyon EJU12NE (U24413 to FCO) and AFR68YL (AF7369 to CDG): three departures in two minutes while RAM721P was on screen; the queue dropped two after 150 s. Orly runway 3: CE8105, TU724, TO7061 each arrived 60 to 90 s after another aircraft already on screen. About 10 flights of 190.
- Cause: the display advances at most every 90 s (`MIN_ADVANCE_INTERVAL_S`) and a waiting aircraft older than 150 s is dropped (`MAX_STALENESS_S`). A deliberate property of an e-ink screen.
- Decision (owner, 2026-11-17): the aircraft must still appear in the recent-flights list with what is known. They were already recorded, but without route or direction. Fixed in PR #458: an adsbdb lookup for the dropped aircraft, kept only if it fits the watched airport, and the direction the route gives when the aircraft had none. Test first (4 tests).

### H-02 A landing roll-out is drawn as a departure
- Evidence [observed]: Roissy, KAL901 (B777) at 17:20:56 and UAE7V (A380) at 18:21:26: an arrival, then one minute later `departing` on the same runway. The pavement record reported +320 ft/min.
- Cause [observed in the cycle trace]: on the ground the held state `arriving` was overridden by any vertical rate at or above +200 ft/min.
- Decision (owner, 2026-11-17): fix, test first. PR #458: an aircraft on the ground whose held state is `arriving` keeps it. A real take-off (airborne, climbing) still gives `departing`. The test replays the recorded KAL901 sequence and failed before the change.
- The only wrong display in 93 at Roissy; none at Lyon, Nantes or Orly.

### H-03 Coverage of the source at Roissy and at Orly departures
- Evidence [observed]: Roissy, 12 flights with no event at all (arrivals FX5048, AFR363V, FX6092, AF7413, OS367; departures AH1529, AH1545, AF1048, U23812, AT789, AF7314, AF7440). Orly 02/20, 6 departures with no event (AH1287, VY8082, TP437, AT771, TO4060, U24851).
- Cause [hypothesis]: the feed does not report these aircraft at low altitude, as in G-01 (same airport, morning). Not a detection logic defect: the same code detected 88 of the other flights.
- Decision: none now. A second source is the open option (G-01).

### H-04 Routes that keep the watched airport but have the wrong other end
- Evidence [observed]: AF6733 (ORD>CDG shown, real PIK), FDX3 (CDG>EWR, real FRA), TAR634 (DJE>ORY, real MIR). About 2 % of routes.
- Cause: adsbdb stores one route per callsign and a rotating callsign returns another leg. G-02 cannot see these (the watched airport is present).
- Measured: the rule "the same aircraft's earlier sighting must match the route" cannot be tested at four airports: 1 aircraft of 196 was seen at two watched airports (that single case agreed). It would not have caught any of the three.
- Decision: none now. Recorded as SEED-020 (OpenSky first), with the 20 % of flights that have no route.

## Not covered in these sessions
- Orly runway 06/24: no movement observed, not in use that evening. Untested is not passed. Roissy's runway side cannot be checked: the lists have no runway column. At Lyon every arrival was drawn by the 17L/35R device and every departure by the 17R/35L one (as in the morning); TK1810 was drawn by both devices 30 s apart, the one ambiguity.
- The relevé of Roissy and Orly had a gap of about one minute around 18:22 UTC (restart); no flight fell in it.
- The Lyon morning session (before the evening) ran with the code before G-02 for 17 minutes; not used in the table.

## Evidence of the fixes
- G-02, PR #457 (merged): Nantes morning 8 of 24 routes without Nantes; Nantes evening, Lyon and Orly departures 0.
- H-02 and H-01, PR #458: tests first, then the change. `server`, `stub-server`, `scripts` and `companion` (non-browser) suites pass; golden hashes of the legacy render and `stub-server/test_phase47_freeze.py` unchanged.

## Nantes lists (short)
Nantes evening, Paris time. ARR: AT716 17:30, KL1423 17:41, AF6146 17:48, IB1221 17:54, AF7504 17:59, XK321 18:46, FR3982 19:09, U24710 19:14, TO8047 19:24. DEP: TO7398 17:35, V72552 18:02, U24703 18:21, AF6147 18:37, KL1424 18:40, AT717 18:51, IB1222 18:54, AF7505 19:15, XK321 19:21. All 18 detected, matched by time and direction.

Lyon evening, Paris time. ARR (13): KL1433 17:34, TK1809 17:37, AF7368 17:46, TP472 17:48, 4Y624 17:52, 4Y612 18:22, AH1080 18:30, IB1183 19:12, AF6137 19:21, AF6147 19:23, ITI2915 19:25, AF6277 19:27, AF6027 19:29. DEP (11): AH1461 17:58, TO8776 18:07, KL1434 18:31, T75417 18:40, AT721 18:45, U24413 18:50, AF7369 18:51, TK1810 18:53, TP473 18:55, 4Y625 18:56, 4Y613 19:20. U24413 and AF7369 were detected and dropped (H-01).

One possible go-around, not confirmed: OCN71Q (4Y612) at Lyon was seen arriving at 17:08 UTC, climbing at 17:09 and arriving again at 17:21; Flightradar24 gives it landed at 18:22 Paris time.
