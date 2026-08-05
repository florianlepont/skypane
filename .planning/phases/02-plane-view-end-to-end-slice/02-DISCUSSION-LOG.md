# Phase 2: Plane View — End-to-End Slice - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-05
**Phase:** 2-Plane View — End-to-End Slice
**Areas discussed:** Flight enrichment (airline + destination/origin), Runway configuration detection, Between-flights display state, Visual rendering sequencing

---

## Flight enrichment (airline + destination/origin)

| Option | Description | Selected |
|--------|-------------|----------|
| Add a supplementary source | Free lookup by callsign (e.g. hexdb.io-style) to resolve airline + destination — adds a light external dependency but actually fulfills PLANE-01/02 | ✓ |
| Airline only, no destination | ICAO callsign prefix (e.g. AFR = Air France) gives airline with no external lookup; destination stays unresolved — scope reduction | |
| Other approach | User has a different idea | |

**User's choice:** Add a supplementary source.
**Notes:** Raw ADS-B (per Phase 1's `adsb-test/samples/*.jsonl`) gives callsign but not route — a real gap that needs a secondary lookup. Specific provider left to research.

---

## Runway configuration detection (departure vs. arrival)

| Option | Description | Selected |
|--------|-------------|----------|
| Inferred from ADS-B data | Altitude/heading trend (climbing+away = departure, descending+toward = arrival) computed from data already being captured | ✓ |
| Official external source | Look for a free NOTAM/config-piste feed — more authoritative but existence/availability unconfirmed | |

**User's choice:** Inferred from ADS-B data.
**Notes:** No new dependency needed; the fields required (altitude, vertical_rate, position) are already captured by Phase 1's aggregator client.

---

## Between-flights display state

| Option | Description | Selected |
|--------|-------------|----------|
| Keep last flight displayed | Persists last detection with no timeout, consistent with the already-locked no-freshness-indicator decision | ✓ |
| Explicit "waiting" state | Neutral placeholder screen instead of a potentially old flight shown without indication | |

**User's choice:** Keep last flight displayed.
**Notes:** Aligns with PROJECT.md's existing decision to skip a staleness indicator in v1.

---

## Visual rendering sequencing

**User's choice:** Finalize this (implementation) context now, then run `/gsd-ui-phase 2` separately for visual design before planning.
**Notes:** User asked when visual layout gets discussed; clarified discuss-phase covers data/logic decisions only, and Phase 2 carries a "UI hint: yes" flag in ROADMAP.md pointing at the dedicated UI workflow.

---

## Claude's Discretion

- Exact enrichment API/provider selection — left to research, evaluate against real Phase 1 sample callsigns before locking.
- Specific numeric thresholds for climbing/descending and toward/away in runway-config inference — left to planner.
- Real VPS provisioning specifics (OS, deployment method, secrets management, TLS) — standard infra choices, no user preference expressed.

## Deferred Ideas

- Correcting stale "local ADS-B primary" wording in PROJECT.md/REQUIREMENTS.md/ROADMAP.md — tracked from Phase 1's 01-04 plan, still pending at Phase 1 close (waves 3-5 incomplete). Not addressed in this session.
- Visual rendering/layout of the plane view — routed to `/gsd-ui-phase 2`.
