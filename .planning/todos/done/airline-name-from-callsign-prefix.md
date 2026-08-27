---
title: Resolve airline name directly from the ADS-B callsign's ICAO prefix
date: 2026-08-27
priority: medium
---

## What

`server/plane/enrich.py`'s `_parse_route()` currently requires adsbdb.com to
successfully resolve ALL of airline name + origin + destination, or the
entire lookup is treated as a miss (`None`) — even when the airline is
trivially knowable from the callsign's 3-letter ICAO prefix alone (e.g.
`TVF` = Transavia France), independent of whether the specific flight's
route is in adsbdb's crowdsourced database.

For carriers with per-tail rotating callsigns (Transavia France measured
at 2/20 = 10% adsbdb hit rate — see `.planning/phases/02-plane-view-end-to-end-slice/02-RESEARCH.md`
and the sibling note `adsbdb-callsign-lookup-legacy-vs-rotating.md`), this
means the airline identity — and therefore the correct illustration — is
lost on ~90% of detections, even though it never depended on adsbdb in the
first place.

## Why now

Explored 2026-08-27 (user: "la majorité des avions qui passent au-dessus de
la maison sont des avions Transavia" — most flights the user actually sees
are exactly the carrier this affects worst). This is the quick, free,
no-external-dependency half of the fix; the harder half (recovering the
actual destination) needs a paid schedule lookup and is captured separately
in the seed `aerodatabox-destination-lookup-rotating-callsigns.md`.

## Shape of the fix

1. A static, open ICAO-airline-code -> airline-name table (ICAO/IATA
   airline designators are stable reference data, not a per-flight lookup —
   e.g. a small vendored table or a well-known open dataset like
   OpenFlights' airline list), keyed on the callsign's first 3 letters.
2. Decouple `illustrations.select_illustration()`'s airline-name input (and
   the caption text) from requiring a full adsbdb hit: when adsbdb misses,
   fall back to the callsign-prefix-derived airline name instead of the
   generic "Route unavailable" state, and only show the destination/origin
   as genuinely unknown.
3. Needs care around: airlines whose callsign prefix differs from their
   IATA/IATA IATA public name (03.1's earlier stale-brand-name findings —
   ASL Airlines France resolves as "Europe Airpost", Corsair International
   as "Corsairfly" — the *airline table itself* needs the real ICAO-to-
   current-brand-name mapping, not just any table), and what UI text to
   show when destination is unknown but airline is known (a new
   intermediate state between "full route" and "Route unavailable").

## Scope note

Confirmed in this exploration this affects low-cost carriers generally
(not just Transavia) — any carrier using per-tail-rotating callsigns will
benefit from this fix, not a Transavia-specific patch.
