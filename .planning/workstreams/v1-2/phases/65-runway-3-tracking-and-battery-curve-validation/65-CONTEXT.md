# Phase 65: Runway 3 Tracking Validation - Context

**Gathered:** 2026-11-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Check that the detection follows the right aircraft on Paris-Orly runway 3 (TRK-01). Not in this phase: anything about the battery (SEED-019, v1.4), the wake interval, a new detection mode, enclosure or hardware changes.

</domain>

<decisions>
## Implementation Decisions

### Tracking comparison (TRK-01)
- **D-01:** Independent source = a flight-tracking site's history plus the official ORY timetables.
- **D-02:** Period = 2026-11-01 to 2026-11-15, already recorded. The export API returned 5 019 `runway_events` rows (2 841 departing, 2 177 arriving, 1 without a state) and 38 `poll_cycles` rows. `poll_cycles` is kept for 14 days, so its export must be saved into the phase directory early.
- **D-03:** Read the history database first (`server/history_db.py`, `runway_events`, `poll_cycles`); the owner supplies nothing for the comparison.
- **D-04:** No change to detection logic without the owner's explicit agreement. Each proposal comes with evidence, and each fix with a test built from the recorded failing case. Golden hashes of the legacy render and `stub-server/test_phase47_freeze.py` must stay green.
- **D-05:** The comparison covers the runway box, the held vertical-rate state (`server/plane/runway_config.py`, deadband +/-200 ft/min), arrival versus departure direction, and callsign/route enrichment (`server/plane/enrich.py`, adsbdb, 30-day cache).

### Battery (moved out)
- **D-06:** On 2026-11-15 the owner removed everything about battery discharges, curves, thresholds and battery tests from this phase. It is planted as SEED-019 (a dedicated phase for v1.4, requirement BAT-01). This phase does not edit or plan any battery work. The earlier answers about the second frame's discharge and who runs the measurements now belong to SEED-019.

### Claude's Discretion
- Test layout, the export format kept in the phase directory, how mismatches are classified.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/workstreams/v1-2/ROADMAP.md` (Phase 65) and `REQUIREMENTS.md` (TRK-01)
- `server/plane/runway_config.py`, `server/plane/enrich.py`, `server/history_db.py`
- `.planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md`
- `deploy/README.md` (export API: `/api/export/flights`, `poll-cycles`, `battery-history`, `status`)
- `stub-server/test_phase47_freeze.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Integration Points
- Production export API (read-only, token injected by the proxy) is the source of recorded traffic.
- Phase 64 (release/companion files) runs in another session: avoid those files.

</code_context>

<specifics>
## Specific Ideas

Known issues of 2026-11-11: a held arrival/departure state carried to the next aircraft; a stale or rotating route.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 65-Runway 3 Tracking Validation*
*Context gathered: 2026-11-15*
