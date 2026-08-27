---
title: Why adsbdb resolves legacy-carrier routes reliably but misses low-cost-carrier routes
date: 2026-08-27
context: Explore session on robustifying displayed flight data (see the sibling todo and seed on airline-name/destination resolution)
---

## The mechanism, not just the symptom

`server/plane/enrich.py`'s `adsbdb.com` lookup is fundamentally a
**crowdsourced callsign -> route cache**: someone, at some point, observed
a given callsign in the air and recorded what route it was flying, and
that association gets reused every time the same callsign string is seen
again.

This works reliably for legacy/full-service carriers (Air France, Iberia,
TAP - measured near-100% hit rate) because their ADS-B callsign **is**
their published commercial flight number (e.g. `AFR1380` = Air France
flight 1380). An airline flight number is assigned to a route and stays
stable for months at a time, so "callsign `AFR1380` = this route" is a
durable fact worth caching indefinitely.

It fails structurally for Transavia France (measured 2/20 = 10% hit rate)
and other carriers using **per-tail rotating callsigns**: their ADS-B
callsign is an ICAO ATC deconfliction code assigned to the aircraft's
rotation, not to a fixed route. The same callsign string can correspond to
a different route on a different day, because it rotates with the
airframe, not with the flight number. There is no stable "callsign X =
route Y" fact to observe once and cache forever - the cached association
that hexdb.io and adsbdb both rely on simply doesn't hold for this class of
carrier, which is why a second crowdsourced database (hexdb.io) was found
to miss the exact same callsigns adsbdb missed (see 02-RESEARCH.md) - and
why adsb.lol's own route endpoint (traced to `vrs-standing-data` on GitHub)
turned out to be the same kind of crowdsourced, callsign-keyed dataset
under a different name, not an independent source.

## Why this matters for any future fix

Any fix that tries to resolve these carriers' routes via ANOTHER
callsign-keyed lookup will hit the same wall, no matter how complete that
database claims to be - the problem isn't coverage, it's that the fact
being looked up ("this callsign means this route") isn't durably true for
this carrier type. A real fix needs a **live, same-day schedule source**
that can answer "what is flying under airline X around time T" instead of
"what has this exact callsign historically meant" - see the AeroDataBox
FIDS seed for the concrete direction that actually clears this bar.

The airline identity itself is a separate, much easier case: it's carried
directly in the callsign's ICAO 3-letter prefix (e.g. `TVF` = Transavia
France), which is stable, standardised reference data independent of any
per-flight schedule - see the sibling todo for the fix that exploits this.
