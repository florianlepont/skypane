# Roadmap: Ink Frame

## Overview

Ink Frame v1 ships as a single-view device in four phases. Phase 1 is a foundation spike that de-risks the thing everything else depends on — real ADS-B reception at the install address — by proving the core device protocol loop (including exponential backoff and NVS persistence) against a stub server. Phase 2 then delivers the first complete, user-visible capability: the plane view, wired end-to-end from ADS-B detection through server rendering to the physical display, built and verified against digital previews since real hardware isn't flashed yet. Phase 3 revisits that same visual design once real hardware exists — refining it against actual Spectra 6 E-ink output rather than a monitor preview. Phase 4 closes out v1 by measuring real on-battery wake/poll/sleep viability (an unattended multi-day discharge run, deliberately scheduled for the end of the project) and building the low-battery indicator that figure informs, completing the device experience.

**v2 scope note**: The RER view (originally Phase 3) and the physical-button view-switching work (originally part of Phase 4, requirements DEVICE-01/DEVICE-02) were deferred out of v1 — v1 ships as a single-view (plane-only) device. See git history for the removed Phase 3 (RER View — End-to-End Slice) content; it and the switching work are v2 candidates once a second view exists to switch to.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation — Hardware Bring-up & ADS-B Validation** - Validate ADS-B reception on real hardware, with the core wake/poll/backoff loop proven against a stub server (completed 2026-08-26)
- [x] **Phase 2: Plane View — End-to-End Slice** - First complete vertical slice: real runway-3 plane data flowing from ADS-B detection through server rendering to the physical display (completed 2026-08-26)
- [ ] **Phase 3: Visual Polish on Real Glass** - Refine the plane view's visual design against real Spectra 6 E-ink output, resolving legibility/balance items that a digital preview can't settle
- [ ] **Phase 3.1: Procedural Per-Airline Livery Rendering** (INSERTED) - Replace Phase 3's hand-generated, representative-type-per-airline static illustrations with a server-side engine that overlays real per-flight livery colors onto the correct aircraft-type SVG, scaling to any airline/type without manual image generation
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
  3. Free public ADS-B aggregator APIs (airplanes.live primary, adsb.fi secondary), geofenced to the install address (<street-address>), reliably detect real aircraft transiting runway 3's flight path — validated over ~92min of real traffic (38/37 distinct aircraft, 2/2 on-ground) against the coverage bar, with no RTL-SDR hardware needed. This validates the groundwork for PLANE-03, fully delivered in Phase 2.

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

**Note on criterion 3's wording**: corrected 2026-08-26 at Phase 1 close (was stale, said "local ADS-B receiver / RTL-SDR"; see 02-CONTEXT.md D-01 and PROJECT.md/REQUIREMENTS.md, corrected the same day).

**Plans**: 5/5 plans executed
**Wave 1**

- [x] 02-01-PLAN.md — Slice 1: live runway-3 flight number reaches the panel (detection, selection rule, minimal render, poll loop)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Slice 2: departing vs. arriving (D-03 deadband inference, full-bleed state colour, state label)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Slice 3: aircraft silhouette centrepiece (vendored CC0 asset, hard-edged compositing, state mirroring)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 02-04-PLAN.md — Slice 4: airline and route captions (adsbdb enrichment, persistent cache, "Route unavailable" fallback)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 02-05-PLAN.md — Slice 5: real HTTPS deployment (scheme fix, OVH VPS-1 + Caddy + systemd, on-glass verification)

**UI hint**: yes

### Phase 3: Visual Polish on Real Glass

**Goal**: The plane view's visual design is refined against real Spectra 6 E-ink output, not a rendered-PNG preview — closing out the hardware-verified-legibility items that every Phase 2 plan explicitly carried forward rather than guessed at, and replacing the generic flat-fill aircraft silhouette with a richer, per-airline generated illustration now that dithered/photographic rendering is confirmed viable on this exact panel (see Note on scope below).

**Note on scope (2026-08-26, discuss-phase):** Widened during `/gsd-discuss-phase 3` from a pure hardware-verification pass into also including a real visual upgrade to the aircraft artwork. The user confirmed via SenseCraft (Seeed's official companion app) that this panel renders dithered/photographic content well — the flat, no-dither rendering rule from 02-UI-SPEC.md Revision 2 was a deliberate Phase 2 style choice, not a hardware limit. This unlocks a per-airline illustration approach that was explicitly rejected in Phase 2 (D-02/02-UI-SPEC.md) only because no CC0/licensable per-airline livery art existed — the user will generate the illustrations themselves (AI image generation), sidestepping that licensing constraint. A personal photo as the panel's *background* was discussed and explicitly deferred to v2 (see REQUIREMENTS.md v2 backlog) — this phase's scope is the aircraft illustration only, not the background.

**Mode:** mvp
**Depends on**: Phase 1 (hardware flashed via 01-06/01-07) and Phase 2 (deployed via 02-05)
**Requirements**: PLANE-01, PLANE-02 (hardware-verified legibility closure, and a richer visual treatment of the "airline" element both requirements already call for — not new requirement scope)
**Success Criteria** (what must be TRUE):

  1. The aircraft silhouette's flat-fill detail level still reads recognisably as a passenger jet at typical wall-viewing distance on real glass. *(Superseded in intent by criterion 5 below if the per-airline illustration replaces the flat-fill silhouette — kept here as the floor: even the fallback illustration must still read as a passenger jet.)*
  2. The route/airline captions (White text on saturated Blue/Green) are legible on real Spectra 6 output, including `fit_text_size()`'s shrunk-overflow case for a long city/airline name — validated via a deliberately forced long-name render, not left to chance.
  3. A-02-02-01's unvalidated departure-side deadband threshold (02-02's `runway_config.py`) is validated visually via a forced synthetic departure render (no real departure exists in Phase 1's captured sample data — confirmed 0 climbing readings across 217 real vertical-rate samples, max observed +48 ft/min). This validates the *visual* DEPARTING state only, not the real +200 ft/min threshold value itself, which remains unvalidated against real sensor data until a genuine runway-3 departure is observed.
  4. Overall poster composition reads as ambient art on the wall, not a data dump — a judgment call made with the frame in its current desk/temporary location as a provisional check; a final check once wall-mounted remains an open item.
  5. Each detected flight renders a dithered, per-airline-generated aircraft illustration (not the current flat-White CC0 silhouette) for airlines covered by the generated set, with a single dithered generic illustration (same style, no specific livery) as the fallback for uncovered airlines and for the "Route unavailable" enrichment-failure state — both still readable as a passenger jet and still correctly mirrored by departing/arriving state.

**Plans**: 2/4 plans executed

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Serif typography (Zilla Slab) and the co-equal flight-number/destination hierarchy, plus D-13's interim panel RGB values

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Dithered two-tone mood background per state, with flat quiet-zone plates behind every caption and a spatially-scoped palette contract

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 03-03-PLAN.md — Per-airline dithered livery illustrations with a dithered generic fallback, gated on the developer's illustration hand-off

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 03-04-PLAN.md — On-glass verification battery (RGB calibration, fresh legibility, forced departure, long names, composition) and the 02-UI-SPEC.md Colour addendum

**UI hint**: yes

### Phase 03.1: Procedural Per-Airline Livery Rendering (INSERTED)

**Goal:** Replace Phase 3's necessarily-bounded, hand-generated per-airline illustration set (one representative-type static file per airline, per `03-CONTEXT.md` D-19) with a server-side rendering pipeline that composites the real airline's livery colors onto the correct aircraft-type SVG shape for the *actual* detected flight — scaling to any airline and type combination without further manual AI-image-generation work, and without depending on an external image-generation tool at all.

**Note on origin (2026-08-26):** Raised by the user during Phase 3's discuss/plan work as an alternative architecture to D-09's static-file hand-off (SVG template + programmatic per-airline color overlay, computed server-side at render time, instead of one pre-generated raster image per airline). Deliberately deferred out of Phase 3 rather than decided inline, because it depends on an unverified prerequisite — whether real ADS-B aircraft-type data (the `t`/ICAO-type-designator field, standard in the readsb/tar1090 JSON schema both `airplanes.live` and `adsb.fi` are built on, per `03-RESEARCH.md`) is actually present in this project's live aggregator responses; this project's own `server/plane/detect.py` does not currently extract it, and a live check could not be completed from the development sandbox (network-restricted). Confirming this from a real network connection is this phase's first task before any rendering work.

**Depends on:** Phase 3 (its static-file approach and illustration-zone rendering path, which this phase replaces) and a confirmed source of real aircraft-type data

**Requirements**: PLANE-01, PLANE-02 (same "airline" element both requirements already call for, now at real per-flight type accuracy rather than Phase 3's representative-type approximation)

**Success Criteria** (what must be TRUE):

  1. Real aircraft-type data (ICAO type designator) is confirmed available and reliably present in this project's live ADS-B aggregator responses — or, if genuinely unavailable, this phase is descoped/re-planned around that finding rather than proceeding on an unverified assumption.
  2. `server/plane/detect.py` extracts and surfaces the aircraft-type field alongside the existing callsign/altitude/vertical-rate fields already captured.
  3. A server-side rendering step composites the correct airline's livery colors onto the correct aircraft-type SVG shape for the actual detected flight, replacing Phase 3's static per-airline file lookup.
  4. The result is at least as visually legible on real Spectra 6 glass as Phase 3's static-file approach, verified via the same `checkpoint:human-verify` on-glass pattern established in prior phases.
  5. Coverage gracefully degrades (a sensible fallback, not a crash or a blank illustration) for any airline/type combination not yet defined in the livery/shape mapping — mirroring D-08's existing generic-fallback discipline from Phase 3.

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 03.1 to break down)

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
| 1. Foundation — Hardware Bring-up & ADS-B Validation | 7/7 | Complete    | 2026-08-26 |
| 2. Plane View — End-to-End Slice | 5/5 | Complete    | 2026-08-26 |
| 3. Visual Polish on Real Glass | 2/4 | In Progress|  |
| 4. Battery Life & Low-Battery Indicator | 0/1+ | In Progress | - |
