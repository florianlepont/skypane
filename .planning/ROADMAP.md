# Roadmap: Ink Frame

## Overview

Ink Frame ships as four vertical slices. Phase 1 is a foundation spike that de-risks the two things everything else depends on — real ADS-B reception at the install address and real on-battery wake/poll/sleep viability — by proving the core device protocol loop against a stub server. Phase 2 then delivers the first complete, user-visible capability: the plane view, wired end-to-end from ADS-B detection through server rendering to the physical display. Phase 3 adds the RER view as a second independent vertical slice, reusing the same device/server loop. Phase 4 closes out v1 by wiring the physical button to switch between the two now-working views, guaranteeing fresh data on every switch, and surfacing a low-battery indicator — completing the full device experience end to end.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation — Hardware Bring-up & ADS-B Validation** - Validate ADS-B reception and battery/wake-cycle viability on real hardware, with the core wake/poll/backoff loop proven against a stub server
- [ ] **Phase 2: Plane View — End-to-End Slice** - First complete vertical slice: real runway-3 plane data flowing from ADS-B detection through server rendering to the physical display
- [ ] **Phase 3: RER View — End-to-End Slice** - Second vertical slice: live next-RER-departure data, reusing the proven device/server loop
- [ ] **Phase 4: View Switching, Fresh Polls & Low Battery** - Physical button ties both views together with guaranteed-fresh polls and a low-battery indicator, completing the v1 device experience

## Phase Details

### Phase 1: Foundation — Hardware Bring-up & ADS-B Validation

**Goal**: The two highest-risk technical unknowns — ADS-B reception at the install site and real on-battery wake/poll/sleep viability — are validated on real hardware, with the core device protocol loop (wake, poll, download, display, deep sleep, backoff) working end-to-end against a stub server. This is a foundation/spike phase: it de-risks Phases 2-4 rather than shipping a user-facing view.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: DEVICE-03, DEVICE-05
**Success Criteria** (what must be TRUE):

  1. Device completes a full wake → HTTPS poll → download → display → deep-sleep cycle against a stub server, repeatably and without manual intervention.
  2. When the stub server is unreachable, the device backs off exponentially instead of retrying at a fixed interval, matching the flightportrait reference model.
  3. A local ADS-B receiver (RTL-SDR) placed at the install address (<street-address>) reliably detects real aircraft transiting runway 3's flight path, confirming the plane-detection approach is viable without needing the ADS-B Exchange fallback. This validates the groundwork for PLANE-03, fully delivered in Phase 2.
  4. The device completes multiple wake/poll/sleep cycles running on battery power alone, producing a measured mAh-per-cycle figure that supports a realistic wake-interval and battery-life plan.

**Plans**: 5/8 plans executed

- [x] 01-01-PLAN.md
- [x] 01-02-PLAN.md
- [x] 01-03-PLAN.md
- [x] 01-04-PLAN.md
- [x] 01-05-PLAN.md
- [ ] 01-06-PLAN.md
- [ ] 01-07-PLAN.md
- [ ] 01-08-PLAN.md

### Phase 2: Plane View — End-to-End Slice

**Goal**: A user can glance at the frame and see live runway-3 plane data — the first complete vertical slice, wired end-to-end from ADS-B detection through server rendering to the physical display.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: PLANE-01, PLANE-02, PLANE-03
**Success Criteria** (what must be TRUE):

  1. User can see flight number, airline, and destination for the next plane departing Orly runway 3, rendered on the physical frame.
  2. When runway 3 is in arrival configuration, user instead sees flight number, airline, and origin for the next landing plane.
  3. As real aircraft use runway 3, the plane view updates to reflect the new flight as detected by the local ADS-B receiver — not a fixed schedule.
  4. The full pipeline (ADS-B detection → server render → device poll → display) runs end-to-end on real hardware, replacing the Phase 1 stub server.

**Note on criterion 3's wording**: "local ADS-B receiver" is stale. Phase 1 plan 01-04 resolved this with a validated `aggregator-sufficient` verdict — detection is built on the free adsb.fi / airplanes.live aggregators, no RTL-SDR. See 02-CONTEXT.md D-01; the doc correction is tracked for Phase 1 close.

**Plans**: 5 plans
**Wave 1**

- [ ] 02-01-PLAN.md — Slice 1: live runway-3 flight number reaches the panel (detection, selection rule, minimal render, poll loop)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 02-02-PLAN.md — Slice 2: departing vs. arriving (D-03 deadband inference, full-bleed state colour, state label)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 02-03-PLAN.md — Slice 3: aircraft silhouette centrepiece (vendored CC0 asset, hard-edged compositing, state mirroring)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 02-04-PLAN.md — Slice 4: airline and route captions (adsbdb enrichment, persistent cache, "Route unavailable" fallback)

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 02-05-PLAN.md — Slice 5: real HTTPS deployment (scheme fix, Hetzner CX22 + Caddy + systemd, on-glass verification)

**UI hint**: yes

### Phase 3: RER View — End-to-End Slice

**Goal**: A user can glance at the frame and see live next-RER-departure data — the second vertical slice, reusing the device/server loop proven in Phase 2 to serve a second, independently useful view.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: RER-01, RER-02, RER-03
**Success Criteria** (what must be TRUE):

  1. User can see line, destination, and minutes-until-departure for the next 2+ RER trains from Orly-Ville.
  2. User can see a "leave by" cue combining the next train's countdown with a fixed walk-time buffer.
  3. User can see a disruption banner on the RER view during a service disruption on the line.
  4. The RER view renders end-to-end (server fetch → render → device poll → display) using the same protocol loop validated for the plane view.

**Plans**: TBD
**UI hint**: yes

### Phase 4: View Switching, Fresh Polls & Low Battery

**Goal**: Users can switch between the two working views with a single physical button, always see freshly polled data on switch, and see a clear low-battery warning — completing the full v1 device experience.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: DEVICE-01, DEVICE-02, DEVICE-04
**Success Criteria** (what must be TRUE):

  1. User can press a physical button on the frame to switch between the plane view and the RER view.
  2. Pressing the button triggers a fresh poll for the newly selected view's data — never a stale cached image.
  3. User can see a low-battery indicator on the frame when the battery is running low.

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation — Hardware Bring-up & ADS-B Validation | 5/8 | In Progress|  |
| 2. Plane View — End-to-End Slice | 0/5 | Planned | - |
| 3. RER View — End-to-End Slice | 0/TBD | Not started | - |
| 4. View Switching, Fresh Polls & Low Battery | 0/TBD | Not started | - |
