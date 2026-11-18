# Phase 68: candidate items for the owner's list

Items raised during other work, kept here so discuss-phase can offer them. Nothing here is selected yet: per the phase's success criterion 1, the phase takes only what the owner selects.

## Airlines page: show the airlines known by name only
- Raised: 2026-11-17, after Phase 65's evening comparison, when `THY`, `KLM`, `FDX`, `FIN`, `KAL` and `UAE` were added to `_ICAO_AIRLINE_NAMES_WITHOUT_ARTWORK` (`server/plane/enrich.py`, PR #461).
- Owner's decision (2026-11-17): handle it in this phase, not in Phase 65.
- Today: the Airlines page lists the 36 airlines that have artwork, plus the unidentified prefixes to resolve. An airline known by name only (no artwork) has no row: it is shown in the recent-flights list and on the screen with a generic illustration, but it cannot be seen or renamed on that page.
- Candidate: show those airlines as read-only rows ("name known, no artwork"), with the option to add artwork later. It touches companion files owned by Phase 64 and the Airlines page design: a mockup first.
- Other prefixes left for the owner's manual registry on purpose (name unverified or conflicting): `OCN`, `ITI`, `CMA`, `FAF`.

## Route sources: a comparison card and a status for the directories
- Raised: 2026-11-18, while the VRS standing data was added before adsbdb for routes (PR #468). The owner asked for a card like "Data sources: the sources agree" but for the route directories, and for a status of the directories.
- Today: the companion shows nothing about the route directories. The Health page counts how many routes were found (fresh lookup, cached, airline only, miss) and does not tell adsbdb from VRS: both are recorded as the same kinds of hit. The "sources agree" card compares adsb.fi and adsb.lol, the two witnesses that see the aircraft; it does not move with the route directories.
- Candidate 1, a "Route sources" card: for each aircraft, whether adsbdb and VRS give the same route, only one answers, or they differ. Measured on 2026-11-17 (155 flights): they differ on 9 of 148 flights, and VRS is right in 7 of them (`65-ROUTE-SOURCES-MEASURE.md`). It needs the server to record which directory answered (a new `route_source` value or a new column) and the other directory's answer for the comparison, which costs a second request per new callsign.
- Candidate 2, a status of each directory: reachable or not, time of the last answer, share of lookups that failed in the last hours, share that found a route. Today the server does not record a lookup that failed for a transient reason (it neither caches nor counts it), so the status needs new counters in the history database, written by the poll cycle.
- Both touch the Health page and the server's history writes, and companion files owned by Phase 64: a mockup first, as for the other items. Nothing is selected yet.
