# Phase 65 TRK-02: live sessions on scratch devices, 2026-11-17

Setup: scratch state roots (option A), one simulated device per runway, the unchanged fleet cycle polled every 30 s (adsb.fi and adsb.lol; adsb.lol failed on most polls). The owner watched Flightradar24 and named each movement. Data: `data/live-2026-11-17/{nantes,lyon,cdg}/` (per-device export, raw provider payloads, `owner_log.csv`). Times below are UTC (Paris is UTC+1). The live frame was not touched. **[observed]** = read in the data; **[hypothesis]** = interpretation.

## Movements

| Airport | Aircraft | Sense | Runway (source) | Result | Route on the device | Owner |
|---|---|---|---|---|---|---|
| Nantes | EJU9040 | arrival | 21 (owner, track 207) | detected 06:02:44 | MXP > BER | from Bordeaux |
| Lyon | AFR65MZ | departure | 17R (geometry, owner screenshot) | detected 06:10:47, confirmed 06:11:17 | LYS > CDG | correct |
| Lyon | EJU67BQ | departure | 17R | detected 06:12:16 on the ground | LYS > AGA | correct |
| Lyon | EJU9790 | departure | 17R (owner) | detected 06:13:47 on the ground | CDG > MXP | to Nantes |
| Lyon | ITI21KZ | arrival | 17L (owner) | detected 06:15:46 | none (callsign prefix "miss") | from Strasbourg |
| Lyon | EJU74TA | departure | 17R (owner) | NOT detected: first report 3775 ft at 06:23:16 | n/a | to Tangier |
| Roissy | AFR357K | arrival | 27R (geometry) | NOT detected: last real fix 2125 ft at 5.7 km, then stale | n/a | from Toronto |
| Roissy | EJU78AN | departure | 27L (geometry) | NOT detected: first report 3300 ft | n/a | to London |
| Roissy | HOP56LF | arrival | 26L (geometry) | NOT detected: last real fix 1700 ft at 3.7 km, then stale | n/a | from Turin |
| Roissy | SIA336 | arrival | 27R (geometry) | NOT detected: last real fix 1800 ft at 3.9 km, then stale | n/a | from Singapore |
| Roissy | AFR57NL | departure | 26R (geometry, owner screenshot) | detected 06:28:41 at 2800 ft | CDG > FLR | to Florence, correct |

Totals: 11 movements, 6 detected (Nantes 1 of 1, Lyon 4 of 5, Roissy 1 of 5). Every detected movement was on the expected runway; at Lyon the two parallel runways (349 m apart) were told apart correctly (departures 17R, arrival 17L). No departure ever came from the wrong runway.

Not covered: Nantes has 1 movement (3 arrivals and 3 departures were the target); Lyon has 1 arrival and no movement on 35R/35L; Roissy's north pair was never detected; Orly 06/24 and 02/20 were not observed. Coverage target not achieved, and an untested runway is not a passed one.

## Findings (TRK-02, owner decision pending for each)

### G-01 The data source stops reporting low aircraft at some airports
- Evidence [observed]: at Roissy, three arrivals (AFR357K, HOP56LF, SIA336) were reported down to 1700 to 2100 ft and then repeated with a position age (`seen_pos`) of 33 to 40 s: the feed went silent 3.7 to 5.7 km before the threshold, outside the corridor, which starts 2.5 km out. Two departures (EJU78AN at Roissy, EJU74TA at Lyon) were first reported above the 3000 ft ceiling (3300 ft and 3775 ft). At Lyon three departures were reported on the ground and were detected.
- Cause [hypothesis]: adsb.fi receiver coverage near the ground differs by airport. Not a defect of the detection geometry (the same code chose the right runway whenever a position existed).
- Consequence: an airport with weak low-altitude coverage cannot be followed with this source. Remedy options (owner decision, none started): a second source, a per-airport coverage check at pairing time, or accepting and documenting it.

### G-02 A stale route that does not mention the watched airport is shown (F-03 confirmed on three airports)
- Evidence [observed]: EJU69MC at Orly (CAG > BER, real Milan), EJU9040 at Nantes (MXP > BER, real Bordeaux), EJU9790 at Lyon (CDG > MXP, real Lyon to Nantes). All three easyJet, all from adsbdb, none containing the watched airport.
- Cause: `route_sanity.route_contradicts()` only rejects a route that has the watched airport in the wrong role (see F-03).

### G-03 No route and no airline for an unknown callsign prefix
- Evidence [observed]: ITI21KZ at Lyon (from Strasbourg): route source "miss". This differs from F-02's "airline only": here even the airline is unknown.

### G-04 Departures at 3000 ft with a 30 s poll
- Evidence [observed]: AFR57NL at Roissy was caught at 2800 ft, 200 ft under the ceiling; EJU78AN and EJU74TA first appeared above it. [hypothesis] With a climb of about 3000 ft/min the aircraft crosses the 3000 ft ceiling about 20 s after the last useful fix; detection of departures at an airport without ground reports depends on one poll landing in that window.

## Not done in these sessions
No fix was made and no detection code changed. Nothing under `server/`, `stub-server/`, `companion/`, `deploy/` or `firmware/` changed.
