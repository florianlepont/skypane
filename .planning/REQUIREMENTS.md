# Requirements: SkyPane

**Defined:** 2026-08-04
**Core Value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Plane (Runway 3)

- [x] **PLANE-01**: User can see flight number, airline, and destination for the next plane departing from Orly runway 3
- [x] **PLANE-02**: User can see flight number, airline, and origin for the next plane landing on runway 3 (when the runway is in arrival configuration, wind-dependent)
- [x] **PLANE-03**: Plane view updates one flight at a time, as real aircraft use runway 3, detected via free public ADS-B aggregator APIs (adsb.fi, adsb.lol) geofenced to the runway's flight path — not a fixed timetable

### Device

- [x] **DEVICE-03**: Device wakes on a schedule, polls the server over HTTPS, downloads and displays a new image if available, then returns to deep sleep, with exponential backoff on failure
- [ ] **DEVICE-04**: User can see a low-battery indicator on the frame when the battery is running low
- [ ] **DEVICE-05**: Device runs on battery power only (no wall power, no solar) for v1

### Companion Configuration Web Interface

Promoted 2026-08-27 from the v2 backlog to Phase 6 (see ROADMAP.md) — selected by the user over four sibling seeds (AeroDataBox destination lookup, local RTL-SDR backup, presence-adaptive poll cadence, and the standalone device-local fault-icon fallback DEVICE-06, which stays deferred in v2 below). Originated 2026-08-26 (`/gsd-discuss-phase 3`) as an unscoped seed idea, then expanded across two 2026-08-27 explore sessions to also cover view switching, device health/battery status, airline-coverage monitoring, and a server-side fault icon — rather than three separate mechanisms (a button, a push channel, and manual log-grepping).

**Scope widened again during `/gsd-discuss-phase 6` (2026-08-27):** CFG-02 (view switching) was removed from this phase — there's still nothing to switch to until a second view exists, so it moved back to v2's "View Switching" section below. In its place, the user asked to add seven new capabilities to this same phase: a flight-history log, a manual poll trigger, airline-resolution statistics, a dark/light theme for the page itself, a live render preview, a gallery of recent renders, and runway selection (CFG-06 through CFG-12 below — CFG-12 was raised mid-discussion, after the rest of this section was already written). See `06-CONTEXT.md` for the full discussion record.

- [x] **CFG-01**: User can configure the frame's settings (background colors/style, tracked airport, other display preferences) via a web interface, instead of every visual choice being fixed at build time. For v1, background-color configuration is scoped to choosing among DEPARTING/ARRIVING theme variants validated on real glass during Phase 7 — see `06-CONTEXT.md`.
- [x] **CFG-03**: User can see the device's last-known health status (last successful poll time, battery voltage once wired per Phase 5's DEVICE-04) via the web interface — deliberately not a phone push notification, to avoid reintroducing a phone dependency for an ambient device
- [x] **CFG-04**: User can see which ADS-B callsign ICAO prefixes have gone unrecognized in production, backed directly by `enrich.py`'s unresolved-prefix registry (`poll_state.json`'s `unresolved_prefixes`, added 2026-08-27) — surfaces airline-coverage gaps from real traffic instead of requiring another manual research audit
- [x] **CFG-05**: When the server's ADS-B data source itself is failing (not the normal "no aircraft right now" Empty state), the next successfully-rendered image includes a small alert icon prompting the user to check the web interface (CFG-03) for details — full design rationale in `.planning/seeds/on-device-fault-icon.md`
- [x] **CFG-06**: User can see a log of recently detected flights (not just the current one), via the web interface
- [x] **CFG-07**: User can manually trigger an immediate detection/render cycle from the web interface, for debugging without waiting for the next scheduled cycle — rate-limited (short cooldown) to avoid abusing the free ADS-B aggregator APIs
- [x] **CFG-08**: User can see airline/route resolution statistics over time via the web interface, beyond CFG-04's raw unresolved-prefix registry
- [x] **CFG-09**: User can toggle a dark/light theme for the web interface itself, independent of the colors rendered on the physical frame
- [x] **CFG-10**: User can see a live preview of what the physical panel is currently displaying, via the web interface, without needing SSH access to the server
- [x] **CFG-11**: User can see a gallery of the most recently rendered panel images via the web interface, for quick visual QA without SSH
- [x] **CFG-12**: User can select which of Orly's three runways the device tracks (currently hardcoded to runway 3; the two neighboring runways, 06/24 and 02/20, already have corridor geometry in `server/plane/detect.py` — added by the runway3-false-positive fix, currently used only to *exclude* their traffic). Generalizes PLANE-01/02/03's runway-3-specific detection to be parameterized by the selected runway. One runway tracked at a time, applied on the device's next scheduled poll (same timing as CFG-01).

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### RER (Orly-Ville)

Deferred 2026-08-11 — user-requested scope reduction so v1 ships single-view (plane-only). Was Phase 3; that phase was removed from ROADMAP.md (see git history) and its full RER context is recoverable there when v2 planning starts.

- **RER-01**: User can see line, destination, and minutes-until-departure for the next 2+ RER trains from Orly-Ville
- **RER-02**: User can see a "leave by" cue combining the next train's countdown with a fixed walk-time buffer
- **RER-03**: User can see a disruption banner on the RER view during a service disruption on the line

### View Switching

Deferred 2026-08-11 alongside RER — meaningless in v1 with only one view. Revisit once a second view (RER or otherwise) exists in v2.

Superseded 2026-08-27 (explore session): the frame is meant to stay wall-mounted, so a physical button is impractical for routine interaction. View switching moves to the companion web interface (see CFG-01/CFG-02 below) instead. The physical button — not yet wired to any hardware (`firmware/main/app_main.c`'s wake-reason switch has a "button" case solely to exercise the log contract; the comment there states plainly "No button is wired up in Phase 1") — is reserved for debug/maintenance functions only (e.g. forcing an immediate poll, resetting Wi-Fi provisioning), not user-facing view control.

- **DEVICE-01**: User can switch between the plane view and the RER view via the companion web interface (CFG-02) — not a physical button
- **DEVICE-02**: Switching views triggers a fresh data poll for the newly selected view, not a stale cached image
- **CFG-02**: User can switch between available views (plane/RER) via the web interface, superseding the physical-button view-switch concept in DEVICE-01. **Moved back here from v1 (2026-08-27, `/gsd-discuss-phase 6`)** — inert with nothing to switch to until a second view exists; revisit once RER (or another view) is actually built.

### Messaging

- **MSG-01**: User can send a short message from a companion phone app that appears on the frame, delivered via the frame's next poll — the device never accepts inbound pushes, matching the poll-only security model

### Personal Photo Background

Deferred 2026-08-26 (Phase 3 discuss-phase) — user confirmed via SenseCraft that this panel renders dithered/photographic content well, so this is technically viable, but the user chose to keep Phase 3's scope to the aircraft illustration only and defer the background itself to v2.

- **VIS-01**: User can set a personal photo (e.g. of the install location) as the plane view's background, rendered with dithering instead of the current full-bleed solid state-color field

### On-Device Fault Fallback

Seed idea, deferred 2026-08-27 (explore session) — the device-local half of the fault-icon idea explored alongside the Companion Configuration Web Interface (CFG-05, now promoted to Phase 6 — see v1 Requirements above). This half stays deferred: it's technically independent of the web interface (no dependency on CFG-03 existing) and covers the harder case where the device can't reach the server at all, so no server-rendered image can carry an alert. Full design rationale in `.planning/seeds/on-device-fault-icon.md`.

- **DEVICE-06**: When the device has failed to reach the server for 2+ consecutive poll attempts (`backoff_n >= 2`), it renders a small local fallback screen (solid fill + pre-baked alert icon) directly in firmware via the existing `fp_panel_draw()` call, without needing a successful server round-trip

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
| ADS-B Exchange specifically (as opposed to adsb.fi/adsb.lol) | Considered as a possible aggregator but not the one validated/used — adsb.fi and adsb.lol are the two default providers in production |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLANE-01 | Phase 2 | Complete |
| PLANE-02 | Phase 2 | Complete |
| PLANE-03 | Phase 2 | Complete |
| DEVICE-03 | Phase 1 | Complete |
| DEVICE-04 | Phase 5 | Pending |
| DEVICE-05 | Phase 5 | In Progress (05-01 Task 1 of 3 done) |
| CFG-01 | Phase 6 | Complete (06-07) |
| CFG-03 | Phase 6 | Complete (06-08, deployed 06-11) |
| CFG-04 | Phase 6 | Pending (not yet planned) |
| CFG-05 | Phase 6 | Pending (not yet planned) |
| CFG-06 | Phase 6 | Pending (not yet planned) |
| CFG-07 | Phase 6 | Complete (06-07) |
| CFG-08 | Phase 6 | Pending (not yet planned) |
| CFG-09 | Phase 6 | Pending (not yet planned) |
| CFG-10 | Phase 6 | Pending (not yet planned) |
| CFG-11 | Phase 6 | Pending (not yet planned) |
| CFG-12 | Phase 6 | Complete (06-07) |

RER-01/02/03 and DEVICE-01/02 moved to v2 Requirements (2026-08-11) — no longer mapped to a v1 phase. CFG-01/03/04/05 (and now CFG-06..11) moved the other direction: promoted from v2 Requirements to Phase 6 (2026-08-27, briefly Phase 7 for a few minutes before the Phase 6/7 renumbering). CFG-02 was promoted alongside them but moved back to v2 during `/gsd-discuss-phase 6` (2026-08-27) — still nothing to switch to. DEVICE-06 stays in v2 Requirements, not promoted.

**Coverage:**

- v1 requirements: 17 total
- Mapped to phases: 17 (Phase 1: 1, Phase 2: 3, Phase 5: 2, Phase 6: 11)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-04*
*Last updated: 2026-08-04 after roadmap creation*
