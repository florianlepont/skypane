# Phase 2: Plane View — End-to-End Slice - Context

**Gathered:** 2026-08-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the first complete, user-visible capability: a live plane view wired end-to-end from ADS-B detection through server rendering to the physical e-ink display. This includes provisioning the real Hetzner VPS (deferred here from Phase 1 per D-09) and building the real rendering pipeline that replaces Phase 1's local stub server. Firmware built in Phase 1 (01-05) is already flashable and largely complete for this phase — Phase 2 is primarily server-side work plus pointing the device at the real server URL instead of the local stub.

This phase does not cover the RER view (Phase 3) or the physical view-switching button (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Superseded prior framing (carried forward from Phase 1)
- **D-01:** Phase 1's plan 01-04 resolved the "local ADS-B vs. aggregator API" question with a validated result: **aggregator-sufficient**. Both adsb.fi and airplanes.live cleared coverage comfortably (38/37 distinct aircraft ≤3000ft, 2/2 on-ground detections) over a ~92-minute real sample at the runway-3 geofence; only update-cadence missed a pre-committed threshold, judged immaterial given the device's multi-minute refresh cycle. **No RTL-SDR hardware, no local receiver.** Plane detection for this phase is built entirely on the free aggregator APIs.
- **Note for downstream agents:** `.planning/PROJECT.md` and `.planning/ROADMAP.md` still contain stale wording ("local ADS-B receiver" as primary, aggregator as "documented fallback") — this is known, tracked doc-drift from Phase 1 (see `adsb-test/RESULTS.md` § Downstream Actions), not a live decision. Treat D-01 above as the actual locked decision regardless of what those files currently say until they're corrected at Phase 1 close.

### Flight enrichment (airline + destination/origin)
- **D-02:** Raw ADS-B data (as sampled in Phase 1 — see `adsb-test/samples/*.jsonl`) gives position, altitude, ground speed, and callsign (e.g. `AFR56XX`) — it does **not** include airline name or destination/origin airport. PLANE-01 needs destination for departures; PLANE-02 needs origin for arrivals. Decision: add a supplementary, free lookup keyed by callsign/ICAO hex to resolve airline name + route (origin/destination). This is a real external dependency beyond the Phase 1 aggregator calls — research should evaluate concrete free options (e.g. hexdb.io-style lookups, or whatever the chosen aggregator additionally exposes) and confirm one actually returns route data for the callsigns seen at Orly before committing.
- **Specific API choice:** left to research/planner — evaluate coverage and reliability for real callsigns like the ones in Phase 1's sample data before locking a provider.

### Runway configuration detection (departure vs. arrival)
- **D-03:** Whether runway 3 is currently in departure or arrival configuration (wind-dependent) is inferred directly from the ADS-B track data already being collected — climbing altitude + track heading away from the runway = departure; descending altitude + track heading toward the runway = arrival. No external NOTAM/config feed. Chosen because it needs no new dependency and the position/altitude data needed is already being captured (see Phase 1's `adsb-test/query_aggregator.py` fields: `altitude`, `on_ground`, `vertical_rate`).

### Between-flights display state
- **D-04:** When no aircraft is currently in the runway-3 geofence, the display keeps showing the last detected flight rather than switching to an explicit "waiting" state. Consistent with the already-locked project decision to skip a freshness/staleness indicator in v1 (see PROJECT.md Key Decisions). No artificial expiry/timeout on a displayed flight — it persists until the next aircraft is detected, however long that takes (Phase 1's data shows real gaps of several minutes between detections even during active daytime traffic, and Orly has curfew-restricted overnight hours per 01-RESEARCH.md).

### Visual rendering / layout
- **Explicitly deferred to `/gsd-ui-phase 2`** — user confirmed this phase's discussion should stay on data/logic decisions; visual design (layout, typography, how airline/destination/time are composed on the 13.3" 6-color panel) goes through the dedicated UI design-contract workflow before planning.

### Claude's Discretion
- Exact enrichment API/provider selection (per D-02) — left to research.
- Specific thresholds for "climbing/descending" and "toward/away" in the runway-configuration inference (D-03) — left to planner, informed by Phase 1's real sample data.
- Real VPS provisioning specifics (OS image, deployment method, secrets management, TLS) — standard infra choices, no user preference expressed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 outputs this phase builds on
- `adsb-test/RESULTS.md` — the aggregator-sufficient decision, per-provider metrics, and explicit Downstream Actions (including the PROJECT.md/REQUIREMENTS.md doc-drift note)
- `adsb-test/query_aggregator.py`, `adsb-test/sample_window.py`, `adsb-test/runway3.json` — working aggregator client and geofence definition, directly reusable as the starting point for the real server's plane-detection module
- `adsb-test/samples/*.jsonl` — real sampled data (not committed, local only) useful for testing enrichment lookups and runway-config inference logic against real callsigns/tracks
- `stub-server/byos_server.py`, `stub-server/VENDOR.md` — the vendored flightportrait reference protocol server; the real Phase 2 server implements the same 3-endpoint contract, hosted on the real VPS instead of localhost
- `firmware/` (all of Phase 1's 01-03/01-05 work) — flashable firmware already implements the device side of the protocol against a configurable server URL; Phase 2 shouldn't need firmware changes beyond pointing at the real server

### Project planning docs
- `.planning/PROJECT.md` — VPS-not-home-server hosting constraint (D-09 origin), €300 hardware ceiling (already satisfied by Phase 1's BOM, not reopened here), no-freshness-indicator decision (informs D-04 above)
- `.planning/REQUIREMENTS.md` — PLANE-01, PLANE-02, PLANE-03 (this phase's requirements)
- `.planning/ROADMAP.md` — Phase 2 success criteria (4 criteria); note criterion 3's "local ADS-B receiver" wording is stale per D-01 above
- `.claude/CLAUDE.md` — Server stack recommendations (Python/FastAPI or Flask + Pillow, Hetzner CX22 hosting)

[No other external specs/ADRs exist yet.]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `stub-server/byos_server.py`: vendored flightportrait reference protocol server (bearer auth, SHA-256 hashing, hash-skip logic) — Phase 2's real server extends this rather than rewriting the protocol layer
- `adsb-test/query_aggregator.py`: working, tested aggregator query client (adsb.fi + airplanes.live, geofenced) — direct starting point for the plane-detection module
- `adsb-test/runway3.json`: sourced geofence bbox + altitude ceiling for runway 3 — reuse as-is

### Established Patterns
- Phase 1 vendored/trimmed rather than reimplemented from scratch wherever a working reference existed (flightportrait's server and firmware code) — same approach recommended for Phase 2's server buildout
- Config/state kept out of git (secrets.h pattern in firmware, `.gitignore`'d sample data) — same discipline expected for VPS secrets/API keys

### Integration Points
- New server code integrates with the existing `stub-server/` protocol implementation (likely evolves into the real server rather than living alongside it)
- Firmware's existing server-URL configuration point (from 01-05) is where the real VPS URL gets wired in — no new firmware integration point needed

</code_context>

<specifics>
## Specific Ideas

- No specific visual/UX examples given — visual design intentionally deferred to `/gsd-ui-phase 2`.

</specifics>

<deferred>
## Deferred Ideas

- Updating `.planning/PROJECT.md` / `.planning/REQUIREMENTS.md` / `.planning/ROADMAP.md` wording to reflect the aggregator-sufficient decision — tracked since Phase 1's 01-04 plan, still pending at Phase 1 close (waves 3-5 not yet done). Not done in this discussion; downstream agents should treat D-01 above as authoritative in the meantime.
- Visual rendering/layout of the plane view — belongs to `/gsd-ui-phase 2`, not this discussion.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 2-Plane View — End-to-End Slice*
*Context gathered: 2026-08-05*
