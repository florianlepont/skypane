# Phase 65 external tracking comparison

**Status:** NEEDS-OWNER-REFERENCE
**Reference coverage of the sample:** 0 of 150 sampled events (0 percent; threshold 50 percent)
**Comparison run:** not possible yet (no reference rows exist). Totals below are placeholders until the owner file arrives.

## Sample design

- Tool: `scripts/runway_external_compare.py` (stdlib, tested, never fetches).
- Events: the 5031 snapshot rows collapse to 4221 events (rows of one hex and state with gaps under 30 minutes are one event).
- Sample: 150 events, seed 65, stratified by day, state, UTC six-hour band and airline family (legacy versus low-cost). One event per day is drawn first, then strata round-robin. All 15 days are covered (6 to 14 events per day); 90 departing, 59 arriving, 1 stateless.
- Match window: 15 minutes; match needs hex or callsign, and direction. Route disagreement is a separate verdict.
- Sample files: `data/external/sample_list.jsonl` and `data/external/sample_list.csv` (same rows).

## Sources tried from the sandbox

| Source | URL | Outcome |
|--------|-----|---------|
| ORY timetable (Groupe ADP / Paris Aéroport) | https://www.parisaeroport.fr/passagers/vols/departs | blocked: the page returns an Incapsula bot-protection challenge (no timetable content, robots meta noindex). Not worked around. Also a live board, so it would not hold 2026-11-01..11-14 anyway. |
| Flightradar24 history | https://www.flightradar24.com/data/airports/ory/departures | blocked: HTTP 403 through the proxy. Not retried. |
| FlightAware airport page | https://www.flightaware.com/live/airport/LFPO | reachable, but the public page lists current flights only; history needs an account, and its robots/terms disallow automated scraping. Not used. |
| OpenSky flights API | https://opensky-network.org/api/flights/departure | blocked: "You cannot access historical flights" without an account. No API key used. |
| adsb.fi | https://adsb.fi | blocked: HTTP 403 (also a live-position source, no history). |

`reference_sample.jsonl` is empty on purpose: nothing was obtainable, and no reference row was inferred from the system's own data.

## Request to the owner

Provide reference rows for the sampled days (ideally all 15 days; a reduced set such as three named days is acceptable and will be reported as reduced). Open `data/external/sample_list.csv` for the times and aircraft sampled. Per day, export ORY departures and arrivals on runway 3 (the tool ignores other runways) from a flight-tracking site you have an account with, or note the ORY timetable rows, in this CSV format (header in `data/external/owner_reference_template.csv`):

`callsign,ts,direction,runway,hex,origin,destination,source`

- `ts`: UTC take-off or landing time, ISO 8601 (for example `2026-11-03T06:12:00Z`); `direction`: `departing` or `arriving`; `runway`: `3` if known; `hex`, `origin`, `destination` optional; `source`: the site host (for example `flightradar24.com`), required on every row.
- Cover whole days, not only the sampled flights: aircraft the system never showed can only be found from complete lists.
- Remove account columns and identifiers before committing; keep only flight rows.
- Save as `data/external/owner_reference.csv` (or `.jsonl`) in this phase directory.

Then re-run: `server/.venv/bin/python3 scripts/runway_external_compare.py --events data/runway_events.jsonl --reference data/external/owner_reference.csv --json-out data/external/verdicts.json` and complete the sections below.

## Totals

Not yet computed (blocked on reference).

| Verdict | Count |
|---------|-------|
| match | pending |
| direction-mismatch | pending |
| route-mismatch | pending |
| unverifiable-no-reference | 150 (until a reference exists) |
| missed-aircraft | pending |

## Mismatches and Area hypothesis

Area hypothesis: none yet. Candidate areas to test once mismatches exist (all hypothesis until plan 04 confirms): runway box, held vertical-rate state, direction, enrichment (D-05).

## What the reference cannot prove

Timetable times are scheduled or block times, not wheels-up or touchdown; ADS-B callsigns can differ from timetable flight numbers (hex matching mitigates this when a tracker supplies it); the system records only flights that reached the display, so a missed-aircraft candidate may be a flight that was legitimately never shown.
