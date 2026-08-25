---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 01
current_phase_name: foundation-hardware-bring-up-ads-b-validation
status: executing
stopped_at: Completed 01-06-PLAN.md
last_updated: "2026-08-25T20:28:15.657Z"
last_activity: 2026-08-25
last_activity_desc: Phase 01 execution started
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 13
  completed_plans: 10
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.
**Current focus:** Phase 01 — foundation-hardware-bring-up-ads-b-validation

## Current Position

Phase: 01 (foundation-hardware-bring-up-ads-b-validation) — EXECUTING
Plan: 2 of 8
Status: Ready to execute
Last activity: 2026-08-25 — Phase 01 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P02 | 15min | 3 tasks | 6 files |
| Phase 01 P03 | 25min | 3 tasks | 15 files |
| Phase 01 P05 | 50min | 3 tasks | 22 files |
| Phase 01 P01 | 12min | 2 tasks | 1 files |
| Phase 01 P04 | 25min | 3 tasks | 1 files |
| Phase 02 P01 | 14min | 3 tasks | 21 files |
| Phase 02 P02 | 18min | 3 tasks | 9 files |
| Phase 02 P03 | 40min | 2 tasks | 5 files |
| Phase 02 P04 | 45min | 3 tasks | 3 files |
| Phase 01 P06 | 74min | 3 tasks | 5 files |

## Accumulated Context

### Roadmap Evolution

- Phase 4 added (2026-08-25), then renumbered to Phase 3 — "Visual Polish on Real Glass": user asked to split Phase 2 into a functional pass and a design-polish pass; since Phase 2 already built up from basic to polished internally across its 5 plans (02-01 bare flight number → 02-04 route/airline captions) and its only remaining plan (02-05) is pure deployment infra with no visual work, the agreed split instead adds a new phase after real hardware exists, dedicated to refining the already-built design against actual Spectra 6 output — closing the hardware-verified-legibility items every Phase 2 SUMMARY.md carried forward rather than guessed at. Old Phase 3 (Low-Battery Indicator) renumbered to Phase 4.

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Local ADS-B receiver (geofenced to runway 3) chosen over public flight-data/schedule APIs — validate reception early in Phase 1
- Battery-only power for v1, solar deferred — Phase 1 must produce a real mAh/wake-cycle measurement
- Server on a small always-on cloud VPS, not a home server
- No freshness timestamp / stale-data indicator in v1 (explicit user tradeoff, despite research flagging it as a pitfall)
- [Phase 01]: Vendored byos_server.py byte-for-byte from flightportrait/frame @ ce3335fc, adding only a --state-dir flag so the harness's isolated test tokens never collide with the long-running stub instance the hardware plans keep alive
- [Phase 01]: make_test_panel.py's quadrants pattern splits left/right exactly on a byte-pair boundary (column 600 of 1200) so no byte mixes two colours except the two intentional border-edge bytes
- [Phase 01]: Disabled Bluetooth in firmware/sdkconfig.defaults (only functional delta from upstream) - Phase 1 has no BLE provisioning, hardcoded secrets.h credentials replace it
- [Phase 01]: Containerised build (espressif/idf:v5.3.1), native flash - build.sh runs the whole ESP-IDF toolchain in Docker as the invoking user; USB flashing stays on the host for plan 01-06 because Docker Desktop's macOS USB passthrough is unreliable
- [Phase 01]: Vendored+trimmed api_client.c/wifi.c to the three device endpoints and STA join, reading credentials from a gitignored secrets.h
- [Phase 01]: Trimmed nvs_schema.h from ~30 upstream keys to exactly 4: bearer token, image hash, failure counter, boot counter
- [Phase 01]: Added FP_ERR_HTTP_TRANSPORT/STATUS/JSON/FP_ERR_IMAGE_VERIFY sentinels so state_machine.c can emit the exact Log Line Contract step token
- [Phase 01]: Froze the five-line Log Line Contract in firmware/VENDOR.md for plans 01-06/01-07/01-08 to grep
- [Phase 01]: Hardware orders placed — Seeed EE02 kit (order <seeed-order-ref>) and Kubii battery+cable (order <kubii-order-ref>); Unblock Date 2026-08-26 gates only 01-06/01-07, not 01-05 (already complete)
- [Phase 01]: aggregator-sufficient (2026-08-05): both adsb.fi and airplanes.live cleared the coverage bar over ~92min real traffic (38/37 distinct aircraft <=3000ft, 2/2 on-ground); update-cadence miss (36.2s/22.4s vs 15s) judged immaterial given the device's multi-minute refresh cycle. No RTL-SDR hardware ordered; D-02 fallback not invoked.
- [Phase 01]: airplanes.live preferred as primary aggregator provider (tighter update gap, zero sample errors); adsb.fi retained as secondary given near-total hex overlap.
- [Phase 02]: D-P2-01 multi-aircraft selection rule implemented as (effective_altitude_ft, seen_pos, hex) total order, proven deterministic under shuffled input
- [Phase 02]: poll_loop.py hardcodes state=arriving for every detected flight - deliberate stub, marked in code, 02-02 replaces with real D-03 inference
- [Phase 02]: Deferred marking PLANE-01/02/03 complete in REQUIREMENTS.md - this slice only satisfies detect->render->serve mechanics, not the full requirement text (enrichment is 02-04, real state inference is 02-02, hardware-verified legibility is 02-05)
- [Phase 02]: D-P2-04 deadband (+-200 ft/min) implemented with explicit bool rejection; descent side backed by the real EJU84YF flare fixture, climb side documented as provisional/symmetry-derived per A-02-02-01 (02-RESEARCH.md Open Question 2, closed in 02-05's hardware QA)
- [Phase 02]: A first-ever detection whose vertical rate sits inside the deadband (confirmed_state is None) renders the Empty state rather than guessing a colour
- [Phase 02]: aircraft-silhouette source SVG is detailed 3/4-view line-art (evenodd multi-subpath), not a flat silhouette - cleaned via a from-scratch Pillow dilate/flood-fill/erode pipeline rather than a vector editor — no rsvg-convert/Inkscape/numpy/scipy available in this environment; the flood-fill approach turns any traced line-art into a flat solid mask without hand-editing vector paths
- [Phase 02]: Silhouette sized by fitting within both the 900px width cap and 02-02's existing 260px height cap while preserving the vendored asset's own ~2.22:1 aspect ratio - height cap binds first, leaving 02-02's zone-3 reservation and FLIGHT_NUMBER_TOP_Y untouched
- [Phase 02]: adsbdb.com live-verified at 52.6% real-world hit rate for this airport's traffic mix (worst on low-cost per-tail-rotating callsigns like Transavia's TVF*) - the "Route unavailable" fallback is a designed first-class state (N-02-04-01), not a rare edge case; enrichment cache persists hit *and* miss results in poll_state.json so a rotating callsign is never re-queried
- [Phase 02]: Airline-line Y position computed from fixed font-metric constants only, never from a rendered route line's bbox - guarantees the fallback caption lands at the exact same position as a resolved-route render, no doubled gap
- [Phase 02]: 02-05: deployment target switched from Hetzner CX22 to OVH VPS-1 (same spec, price parity) per explicit user redirect — D-P2-06 explicitly leaves infrastructure specifics to discretion, so treated as a provider substitution, not an architectural change; deploy/ scripts needed zero functional edits since they were already provider-agnostic
- [Phase 02]: 02-05 Task 2 complete: OVH VPS-1 (<public-host>, Ubuntu 26.04) live-provisioned and fully verified - TLS, auth gate, firewall, and real ADS-B pipeline all confirmed against the live host. Fixed 4 live-discovered deploy bugs: sudo-user support, generic python3 packaging, missing adsb-test/runway3.json geofence config, missing Caddy access logging.
- [Phase 02]: 02-05 Task 3 (on-glass verification) remains blocked on Phase 1 plan 01-06 hardware flash/first boot - unblock date 2026-08-26, not yet reached.
- [Phase 01]: EE02 board profile verified against real hardware with zero pin/config corrections needed - firmware/sdkconfig.ee02.defaults stays byte-identical to upstream
- [Phase 01]: 'Device appears then disappears on USB' during 01-06 was diagnosed as esp_deep_sleep_start() correctly powering off USB Serial/JTAG outside the RTC domain, not a boot loop/brownout - documented in hardware/BRINGUP-LOG.md
- [Phase 01]: measured panel full-refresh duration ~31.5s (two independent captures) - input for Phase 2 rendering-cadence UX

### Pending Todos

None yet.

### Blockers/Concerns

- Research flagged as unverified before commit: exact AeroDataBox tier/cost is not needed (project uses local ADS-B, not AeroDataBox, per PROJECT.md's reversed decision) — but PRIM/IDFM's exact SIRI Lite quota figures are community-sourced only; not a v1 blocker (RER deferred to v2 as of 2026-08-11) — verify against the live account dashboard before finalizing RER poll cadence when v2 planning starts.
- Spectra 6 dual-chip display driver — RESOLVED 2026-08-25 (01-06): EE02 board profile verified against real hardware with zero corrections needed, first light achieved (all 5 visual checks passed), Log Line Contract captured live.
- No publicly confirmed enclosure design exists for the EE02 kit — budget design time in Phase 1 or plan around an off-the-shelf enclosure.
- Battery-life real-world figure for this exact hardware combo is unmeasured — 01-08 (queued, wave 5) will produce this via a real unattended discharge run.
- 02-05: live provisioning complete (OVH VPS-1, <public-host>, Ubuntu 26.04). Task 3 (on-glass verification) is now UNBLOCKED — 01-06 hardware flash/first boot is done, hardware confirmed working. Re-run 02-05's executor to complete Task 3 whenever convenient.
- Device wake interval (how often the physical frame polls the server, decoupled from the server's own 30s ADS-B poll) is currently 300s in the test/bring-up config — NOT yet a tuned production value. Real tradeoff: shorter interval = fresher plane-departure info but faster battery drain; longer = more autonomy but a departure could be several minutes stale by the time it's shown. Decision deliberately deferred (2026-08-25) until 01-08 produces a real mAh-per-cycle figure — tune this once actual battery-life data exists, not before.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none — first milestone)* | | | |

## Session Continuity

Last session: 2026-08-25T20:28:15.652Z
Stopped at: Completed 01-06-PLAN.md
Resume file: None
