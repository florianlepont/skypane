# Phase 53: Detection Modes (Airport/Runway and Position/Radius) - Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

A device can follow traffic on any French runway from a committed catalogue, or the aircraft around a chosen position inside France, in addition to today's Orly runway 3 behaviour. Devices sharing a zone keep sharing one upstream request set (Phase 52 zones and 1 req/s budget); no second upstream path.

Requirements: DET-01, DET-02, DET-03. Depends on Phase 52.

Not in this phase: pairing, admin console and user view (55), Auth0 and the route gate itself (54, only extended with the new route), per-hardware rendering (56), presence-adaptive cadence, production deploy. Phase 47 files and `hardware/` are untouched; `stub-server/test_phase47_freeze.py` stays green; expand-only (the previous release still runs on the state this phase writes).

</domain>

<decisions>
## Implementation Decisions

### Owner-fixed (not to be reopened)
- **D-01:** Two per-device detection modes: (1) airport + runway from a committed catalogue built from OurAirports; (2) aircraft around the device's position. The catalogue is produced by a reproducible, committed script and never downloaded at run time.
- **D-02:** Reuse the Phase 52 zone mechanism and budget; adsb.fi stays at 1 req/s in total and is cited. OurAirports is already on the credits page (`companion/credits.json`, public domain, courtesy credit): verified.
- **D-03:** No production deploy; code, tests and CI only.

### Catalogue (owner choice)
- **D-04:** Include every French aerodrome runway row from OurAirports (`LF*` and overseas rows present in the dump) with both thresholds and `closed=0`. Measured on the 2026-10-31 dump: 548 `LF*` rows, 288 with both thresholds, 11 closed. Rows without both thresholds are absent. Real designators kept (e.g. `08L/26R`).
- **D-05:** A catalogue runway is the full pair, both directions (departures and arrivals either way), like Orly 3 (07/25) today.
- **D-06:** Image tag for runway mode uses the IATA code when the airport has one, else the ICAO ident, then the real designator (e.g. `CDG · 08L/26R`). Legacy Orly ids keep their exact current tag text.

### Parallel runways (owner choice)
- **D-07:** The corridor half-width is `min(500 m, half the distance to the nearest parallel runway of the same airport)`; the default 500 m, 2500 m extension, 30 deg axis tolerance and 75 m ground half-width are unchanged. Orly keeps exactly 500 m. Tests cover LFPG (08L/26R vs 08R/26L, 09L/27R vs 09R/27L) and at least one other parallel-runway airport.

### Current Orly frame (owner choice, 2026-10-31)
- **D-08 (owner chose switching):** The live Orly frame moves onto the generic catalogue logic in this phase, with one condition kept from the owner's standing constraint: its observable behaviour (selected aircraft, tag text, image, interval) must not change. This holds only if the replay of recorded Orly traffic through the new logic gives decisions strictly identical to the hand-tuned runway-3 geofence, and `test_phase47_freeze.py` stays green. If the replay is not identical, the switch is not made and the frame stays on the existing geofence; the owner is told. The legacy `tracked_runway` ids (`3`, `06-24`, `02-20`) stay valid and map to the catalogue's LFPO rows (expand-only).
- **D-09:** Nothing is deployed; the switch ships in code with the deploy decision left to the owner.

### Position mode (owner choice)
- **D-10:** The centre is the device's location (Phase 48 `locations`: name, latitude, longitude, timezone) plus a radius stored with the device. No free-form coordinates.
- **D-11:** Shown aircraft: airborne only, altitude at or below 10,000 ft, lowest first (existing selection ordering). Radius bounds 2 to 15 NM.
- **D-12:** Coordinates sent to third parties are rounded to 2 decimals (about 1 km); the zone centre received by Phase 52 is the rounded position, so neighbours share zones naturally. Runway mode does not round (public airport coordinates).
- **D-13:** Country bounds: a bounding box around metropolitan France including Corsica; positions outside are refused with a clear message, in the setting form and again server side.

### Settings interface (owner choice)
- **D-14:** A new dedicated page for detection settings, not the existing Runway card. It is a new route and must be added to the route x role x owner matrix (default-deny, per-device protected route of Phases 51/54); wrong role or other owner's device answers 404.
- **D-15:** Airport selection by a search field (ICAO, IATA, name, city) filtering the committed catalogue, then one card per runway with the real designator and orientation. The form works without JavaScript. All strings bilingual in `companion/i18n_fr/`; load `Skill("sketch-findings-skypane")` before any interface work.

### Claude's Discretion
- Catalogue JSON shape and script name, module names, storage keys in `device_config.json`, how legacy ids map, how replay fixtures are recorded, plan split, empty-state texts, exact orientation display.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone
- `.planning/workstreams/v1-2/ROADMAP.md` (Phase 53), `.planning/workstreams/v1-2/REQUIREMENTS.md` (DET-01..03)
- `.planning/workstreams/v1-2/research/PITFALLS.md` C17 (runway geometry), M12; `STACK.md` OurAirports section; `FEATURES.md`; `ARCHITECTURE.md` detection modes
- `.planning/workstreams/v1-2/phases/52-fleet-poll-cycle-zones-and-request-budget/52-CONTEXT.md` (D-12 exact zone key, budget)
- `.planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-CONTEXT.md`, `54-*/54-HANDOFF.md` (route gate)

### Code
- `server/plane/detect.py`, `adsb-test/runway3.json`, `adsb-test/RUNWAY-GATE-VERIFICATION.md`, `server/fixtures/geofence_*.json`
- `server/fleet_zones.py`, `server/fleet_cycle.py` (`geofence_resolver`), `server/zone_fetch.py`
- `server/device_config.py` (RUNWAYS, tracked_runway), `companion/settings/runway_led.py`, `server/fleet_db.py` (locations)
- `companion/credits.json`, `COMPLIANCE.md`, `stub-server/test_phase47_freeze.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `detect.runway_axis`, `corridor_params`, `filter_in_geofence`, `select_aircraft_for_runway`: already per-runway; generalise from a geofence document
- `fleet_zones.Zone`/`geofence_resolver`: one resolver for all devices today; becomes per-device
- Phase 48 `locations` table and `device_dirs`/`device_config` per-device config

### Established Patterns
- Pure functions with injected clock; behaviour tests, pytest-socket guard, 80-line function cap, English comments without phase IDs

### Integration Points
- Per-device resolver in `fleet_cycle`; render tag text via `device_config.runway_tag_text`; new companion route in the access matrix

</code_context>

<specifics>
## Specific Ideas

- OurAirports LFPO rows are 02/20, 06/24, 07/25 (07/25 is the project's "runway 3"); LFPG has four parallel pairs plus a grass runway.
- Recorded Orly traffic for the replay: `server/fixtures/`, `adsb-test/`.

</specifics>

<deferred>
## Deferred Ideas

- Free-form coordinates per device; single-direction runway following; IATA-less aerodrome naming refinements; overseas bounds for position mode.

</deferred>

---

*Phase: 53-Detection Modes (Airport/Runway and Position/Radius)*
*Context gathered: 2026-10-31*
