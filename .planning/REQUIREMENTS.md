# Requirements: Ink Frame

**Defined:** 2026-08-04
**Core Value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Plane (Runway 3)

- [x] **PLANE-01**: User can see flight number, airline, and destination for the next plane departing from Orly runway 3
- [x] **PLANE-02**: User can see flight number, airline, and origin for the next plane landing on runway 3 (when the runway is in arrival configuration, wind-dependent)
- [x] **PLANE-03**: Plane view updates one flight at a time, as real aircraft use runway 3, detected via free public ADS-B aggregator APIs (airplanes.live primary, adsb.fi secondary) geofenced to the runway's flight path — not a fixed timetable

### Device

- [x] **DEVICE-03**: Device wakes on a schedule, polls the server over HTTPS, downloads and displays a new image if available, then returns to deep sleep, with exponential backoff on failure
- [ ] **DEVICE-04**: User can see a low-battery indicator on the frame when the battery is running low
- [ ] **DEVICE-05**: Device runs on battery power only (no wall power, no solar) for v1

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### RER (Orly-Ville)

Deferred 2026-08-11 — user-requested scope reduction so v1 ships single-view (plane-only). Was Phase 3; that phase was removed from ROADMAP.md (see git history) and its full RER context is recoverable there when v2 planning starts.

- **RER-01**: User can see line, destination, and minutes-until-departure for the next 2+ RER trains from Orly-Ville
- **RER-02**: User can see a "leave by" cue combining the next train's countdown with a fixed walk-time buffer
- **RER-03**: User can see a disruption banner on the RER view during a service disruption on the line

### View Switching

Deferred 2026-08-11 alongside RER — meaningless in v1 with only one view. Revisit once a second view (RER or otherwise) exists in v2.

- **DEVICE-01**: User can press a physical button on the frame to switch between the plane view and the RER view
- **DEVICE-02**: Switching views (button press) triggers a fresh data poll for the newly selected view, not a stale cached image

### Messaging

- **MSG-01**: User can send a short message from a companion phone app that appears on the frame, delivered via the frame's next poll — the device never accepts inbound pushes, matching the poll-only security model

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Solar charging | Deferred until real battery life and frame placement are known; indoor solar is unreliable without a well-lit window |
| Public flight-data/schedule API (e.g. AeroDataBox) as the plane-detection source | Reversed after scoping — the goal is "the specific plane using runway 3 right now," which schedule APIs don't expose; ADS-B aggregators detect real aircraft directly |
| Wall power | Battery-only for v1, to force realistic power-budget decisions early |
| Freshness timestamp / graceful stale-offline display state | Explicitly deferred by user for v1 despite research flagging it as a common pitfall; revisit if staleness becomes a real problem |
| Additional views beyond plane/RER (weather, other transit lines, etc.) | Stay two-view to preserve focus on the core value |
| Status LEDs, on-device settings/menu UI, gate/terminal/check-in fields, push notifications to phone, animated transitions | Anti-features that would make the frame read as a gadget rather than ambient art |
| Local RTL-SDR ADS-B receiver | Originally the primary plan; Phase 1 plan 01-04 validated the free adsb.fi/airplanes.live aggregators clear the coverage bar (~92min real traffic, 38/37 distinct aircraft, 2/2 on-ground) with no dedicated hardware needed — no RTL-SDR ordered |
| ADS-B Exchange specifically (as opposed to adsb.fi/airplanes.live) | Considered as a possible aggregator but not the one validated/used — adsb.fi and airplanes.live are the two in production |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLANE-01 | Phase 2 | Complete |
| PLANE-02 | Phase 2 | Complete |
| PLANE-03 | Phase 2 | Complete |
| DEVICE-03 | Phase 1 | Complete |
| DEVICE-04 | Phase 4 | Pending |
| DEVICE-05 | Phase 4 | In Progress (04-01 Task 1 of 3 done) |

RER-01/02/03 and DEVICE-01/02 moved to v2 Requirements (2026-08-11) — no longer mapped to a v1 phase.

**Coverage:**

- v1 requirements: 6 total
- Mapped to phases: 6 (Phase 1: 1, Phase 2: 3, Phase 3: 1, Phase 4: 2)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-04*
*Last updated: 2026-08-04 after roadmap creation*
