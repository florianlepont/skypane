---
title: AeroDataBox FIDS cross-reference to recover destination for rotating-callsign carriers
trigger_condition: >
  Revisit once the free callsign-prefix airline-name fix (todo
  airline-name-from-callsign-prefix.md) is shipped and the user decides the
  remaining gap (destination still unknown for Transavia-class carriers) is
  worth a paid API. Also revisit if AeroDataBox's pricing/terms change, or
  if any new free alternative emerges (unlikely per this session's
  exhaustive check, but worth a quick re-verify before committing spend).
planted_date: 2026-08-27
---

## Context

Explored 2026-08-27 after the user pushed hard on finding a free way to
resolve destination for carriers whose ADS-B callsigns rotate per-aircraft-
tail rather than mapping 1:1 to a fixed published flight number (Transavia
France measured at 2/20 = 10% hit rate against adsbdb.com; see the sibling
note `adsbdb-callsign-lookup-legacy-vs-rotating.md` for why this is
structural, not a database-completeness problem).

Five free avenues were genuinely investigated and each confirmed a dead
end, not just assumed:

1. **ADS-B/Mode-S message content itself** — no standard 1090ES/Comm-B
   register (BDS 4,0/5,0/6,0/6,2) carries destination or flight-plan data;
   confirmed against real register definitions (mode-s.org). Destination
   is airline-side flight-plan data (FAA SWIM), never broadcast over the
   air, confirmed via an ADS-B Exchange developer forum thread stating
   destination "does not know... can be deduced after landing, but not
   before."
2. **OpenSky Network's historical `/flights/*` endpoints** — double dead
   end: their Terms of Use require a written license for automated use of
   ANY REST endpoint (not just live state vectors, already ruled out
   separately for the runway3-false-positive backup-source research), AND
   the endpoints are only populated by an overnight batch job ("only
   flights from the previous day or earlier"), useless for live enrichment
   regardless of licensing.
3. **Registration/route-history databases** (planespotters.net, adsb.lol's
   own route endpoint) — traced adsb.lol's actual GitHub source: its route
   lookup is a cache over `vrs-standing-data` (github.com/vradarserver/
   standing-data), itself a user-submitted, callsign-keyed CSV dataset —
   structurally identical to adsbdb, not an independent resolution path.
   planespotters.net has no documented public API, scraping-only.
4. **Deriving the commercial flight number from the callsign directly** —
   genuinely impossible, not just undocumented: the alphanumeric suffix
   (e.g. `TVF16VB`) is ICAO's per-rotation ATC deconfliction scheme,
   assigned to avoid two aircraft sharing a callsign, with no formula back
   to the published flight number.
5. **FlightAware AeroAPI v4** — same paid category as AeroDataBox: a
   $5/month *usage credit* (not a fixed free tier), personal/non-commercial
   only, pay-per-query beyond that.

## What's actually viable

**AeroDataBox's FIDS endpoint** (`GET /flights/airports/icao/{icao}?offsetMinutes=X&durationMinutes=Y&direction=Departure`),
Pro tier $5/mo / 6,000 units / 1 req/s (aerodatabox.com/pricing, confirmed
current 2026-08-27) — already evaluated in this project's own tech-stack
research, previously rejected only as a *primary detection* source (no
real-time runway assignment). For this narrower *enrichment* role that
limitation doesn't matter, since ADS-B has already told us which runway
and which airline (from the callsign prefix, once the sibling todo ships).

The endpoint genuinely supports the needed query shape: a relative time
window (e.g. ±5-10 min around the ADS-B detection timestamp) plus a
departure/arrival direction filter. There's no server-side airline-code
filter, but the response includes IATA/ICAO airline codes per flight, so
the (typically short) result list is filtered client-side for the target
airline. Low query volume (a handful of lookups/day, only on adsbdb
misses) comfortably fits the $5/mo tier.

## Shape of the integration (not yet designed in detail)

- Only call AeroDataBox when adsbdb's route lookup misses AND the
  callsign-prefix airline-name fix has already identified a known airline
  (no point burning a query on an unrecognised airline).
- Cache per-callsign like the existing adsbdb cache (same
  `poll_state.json`-persisted, hit-and-miss-cached pattern already
  established in `enrich.py`), to respect the 1 req/s / 6,000-unit budget.
- Needs its own COMPLIANCE.md entry (terms of use, attribution
  requirements) alongside the project's existing adsb.fi/adsbdb.com/PRIM
  entries, following the same due-diligence pattern already used for every
  other third-party data source in this project.
