# Phase 68: candidate items for the owner's list

Items raised during other work, kept here so discuss-phase can offer them. Nothing here is selected yet: per the phase's success criterion 1, the phase takes only what the owner selects.

## Airlines page: show the airlines known by name only
- Raised: 2026-11-17, after Phase 65's evening comparison, when `THY`, `KLM`, `FDX`, `FIN`, `KAL` and `UAE` were added to `_ICAO_AIRLINE_NAMES_WITHOUT_ARTWORK` (`server/plane/enrich.py`, PR #461).
- Owner's decision (2026-11-17): handle it in this phase, not in Phase 65.
- Today: the Airlines page lists the 36 airlines that have artwork, plus the unidentified prefixes to resolve. An airline known by name only (no artwork) has no row: it is shown in the recent-flights list and on the screen with a generic illustration, but it cannot be seen or renamed on that page.
- Candidate: show those airlines as read-only rows ("name known, no artwork"), with the option to add artwork later. It touches companion files owned by Phase 64 and the Airlines page design: a mockup first.
- Other prefixes left for the owner's manual registry on purpose (name unverified or conflicting): `OCN`, `ITI`, `CMA`, `FAF`.
