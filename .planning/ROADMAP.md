# Roadmap: Ink Frame

## Overview

Ink Frame v1 ships as a single-view device in four phases. Phase 1 is a foundation spike that de-risks the thing everything else depends on — real ADS-B reception at the install address — by proving the core device protocol loop (including exponential backoff and NVS persistence) against a stub server. Phase 2 then delivers the first complete, user-visible capability: the plane view, wired end-to-end from ADS-B detection through server rendering to the physical display, built and verified against digital previews since real hardware isn't flashed yet. Phase 3 revisits that same visual design once real hardware exists — refining it against actual Spectra 6 E-ink output rather than a monitor preview. Phase 4 closes out v1 by measuring real on-battery wake/poll/sleep viability (an unattended multi-day discharge run, deliberately scheduled for the end of the project) and building the low-battery indicator that figure informs, completing the device experience.

**v2 scope note**: The RER view (originally Phase 3) and the physical-button view-switching work (originally part of Phase 4, requirements DEVICE-01/DEVICE-02) were deferred out of v1 — v1 ships as a single-view (plane-only) device. See git history for the removed Phase 3 (RER View — End-to-End Slice) content; it and the switching work are v2 candidates once a second view exists to switch to.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation — Hardware Bring-up & ADS-B Validation** - Validate ADS-B reception on real hardware, with the core wake/poll/backoff loop proven against a stub server
- [ ] **Phase 2: Plane View — End-to-End Slice** - First complete vertical slice: real runway-3 plane data flowing from ADS-B detection through server rendering to the physical display
- [ ] **Phase 3: Visual Polish on Real Glass** - Refine the plane view's visual design against real Spectra 6 E-ink output, resolving legibility/balance items that a digital preview can't settle
- [ ] **Phase 4: Battery Life & Low-Battery Indicator** - Measure real on-battery wake/poll/sleep viability via an unattended multi-day discharge run, then build the low-battery warning it informs, completing the v1 single-view device experience

## Phase Details

### Phase 1: Foundation — Hardware Bring-up & ADS-B Validation

**Goal**: The highest-risk technical unknown — ADS-B reception at the install site — is validated on real hardware, with the core device protocol loop (wake, poll, download, display, deep sleep, backoff) working end-to-end against a stub server and proven byte-for-byte, including exponential backoff and NVS persistence across a full power loss. This is a foundation/spike phase: it de-risks Phases 2-4 rather than shipping a user-facing view.

**Note on scope (2026-08-26)**: Real on-battery wake/poll/sleep viability — originally this phase's second named risk, with its own success criterion and a DEVICE-05 plan (01-08) — was moved to Phase 4 at the user's request, to run the unattended multi-day discharge test at the end of the project rather than mid-Phase-1. See STATE.md's Roadmap Evolution note.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: DEVICE-03
**Success Criteria** (what must be TRUE):

  1. Device completes a full wake → HTTPS poll → download → display → deep-sleep cycle against a stub server, repeatably and without manual intervention.
  2. When the stub server is unreachable, the device backs off exponentially instead of retrying at a fixed interval, matching the flightportrait reference model.
  3. A local ADS-B receiver (RTL-SDR) placed at the install address (<street-address>) reliably detects real aircraft transiting runway 3's flight path, confirming the plane-detection approach is viable without needing the ADS-B Exchange fallback. This validates the groundwork for PLANE-03, fully delivered in Phase 2.

**Plans**: 7/7 plans executed

- [x] 01-01-PLAN.md
- [x] 01-02-PLAN.md
- [x] 01-03-PLAN.md
- [x] 01-04-PLAN.md
- [x] 01-05-PLAN.md
- [x] 01-06-PLAN.md
- [x] 01-07-PLAN.md

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

**Plans**: 4/5 plans executed
**Wave 1**

- [x] 02-01-PLAN.md — Slice 1: live runway-3 flight number reaches the panel (detection, selection rule, minimal render, poll loop)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Slice 2: departing vs. arriving (D-03 deadband inference, full-bleed state colour, state label)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Slice 3: aircraft silhouette centrepiece (vendored CC0 asset, hard-edged compositing, state mirroring)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 02-04-PLAN.md — Slice 4: airline and route captions (adsbdb enrichment, persistent cache, "Route unavailable" fallback)

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 02-05-PLAN.md — Slice 5: real HTTPS deployment (scheme fix, Hetzner CX22 + Caddy + systemd, on-glass verification)

**UI hint**: yes

### Phase 3: Visual Polish on Real Glass

**Goal**: The plane view's visual design is refined against real Spectra 6 E-ink output, not a rendered-PNG preview — closing out the hardware-verified-legibility items that every Phase 2 plan explicitly carried forward rather than guessed at.
**Mode:** mvp
**Depends on**: Phase 1 (hardware flashed via 01-06/01-07) and Phase 2 (deployed via 02-05)
**Requirements**: PLANE-01, PLANE-02 (hardware-verified legibility closure — not new requirement scope, the final verification step on requirements Phase 2 already implemented informationally)
**Success Criteria** (what must be TRUE):

  1. The aircraft silhouette's flat-fill detail level still reads recognisably as a passenger jet at typical wall-viewing distance on real glass.
  2. The route/airline captions (White text on saturated Blue/Green) are legible on real Spectra 6 output, including `fit_text_size()`'s shrunk-overflow case for a long city/airline name.
  3. A-02-02-01's unvalidated departure-side deadband threshold (02-02's `runway_config.py`) is confirmed or corrected against real observed climb-rate data.
  4. Overall poster composition reads as ambient art on the wall, not a data dump — a judgment call only possible once it's actually mounted and glanced at, not eyeballed on a monitor.

**Plans**: TBD
**UI hint**: yes

### Phase 4: Battery Life & Low-Battery Indicator

**Goal**: Real on-battery wake/poll/sleep viability is measured on real hardware (not estimated), producing a mAh-per-cycle figure a wake-interval and battery-life plan can be built on; users can then see a clear low-battery warning on the frame — completing the v1 device experience for the single-view (plane-only) device.

**Note on scope (2026-08-26)**: The battery-measurement plan (04-01, formerly Phase 1's 01-08) was moved here at the user's request — the unattended multi-day (up to 21-day) discharge run is deliberately scheduled for the end of the project, once other phases no longer need this Mac to stay awake continuously. Task 1 (pre-registered protocol + `check-battery` checker, proven on fixtures) is already complete; Tasks 2-3 (the actual run and its verdict) remain.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: DEVICE-04, DEVICE-05
**Success Criteria** (what must be TRUE):

  1. The device completes multiple wake/poll/sleep cycles running on battery power alone, producing a measured mAh-per-cycle figure — not an estimate — that supports a realistic wake-interval and battery-life plan.
  2. User can see a low-battery indicator on the frame when the battery is running low.

**Plans**: 0/1+ plans executed (04-01 in progress; a second plan to build the low-battery indicator UI itself is still TBD)
**Wave 1**

- [ ] 04-01-PLAN.md — Battery-life measurement: pre-registered D-07 protocol + check-battery checker (Task 1 done), unattended multi-day discharge run and verdict (Tasks 2-3 pending)

**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation — Hardware Bring-up & ADS-B Validation | 7/7 | Complete |  |
| 2. Plane View — End-to-End Slice | 4/5 | In Progress|  |
| 3. Visual Polish on Real Glass | 0/TBD | Not started | - |
| 4. Battery Life & Low-Battery Indicator | 0/1+ | In Progress | - |
