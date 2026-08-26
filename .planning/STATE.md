---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 02
current_phase_name: plane-view-end-to-end-slice
status: executing
stopped_at: 02-05 Task 3 in progress — firmware rebuilt with real OVH base URL, awaiting device USB reconnection to flash and verify on physical glass
last_updated: "2026-08-26T09:15:00.000Z"
last_activity: 2026-08-26
last_activity_desc: "Phase 1 formally verified and closed (01-VERIFICATION.md: 3/3 truths, one stale-documentation gap found and fixed same session, not a real engineering gap). Active work remains 02-05 Task 3."
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 13
  completed_plans: 11
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.
**Current focus:** Phase 02 — plane-view-end-to-end-slice (02-05 Task 3)

## Current Position

Phase: 02 (plane-view-end-to-end-slice) — EXECUTING
Plan: 5 of 5 (02-05 Task 3 of 3 — point firmware at real OVH deployment, verify on physical glass)
Status: Phase 1 formally verified and closed (7/7 plans, 01-VERIFICATION.md passed 3/3 after fixing a stale-documentation gap, not an engineering gap). 02-05's Tasks 1-2 complete and live-verified against the OVH VPS; Task 3 in progress — firmware rebuilt with the real base URL, needs the device reconnected via USB to flash and verify real plane data renders correctly on glass.
Last activity: 2026-08-26 — Phase 1 verified and closed; 02-05 Task 3 remains the active work

Progress: [█████████░] 92%

## Performance Metrics

**Velocity:**

- Total plans completed: 7
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 7 | - | - |

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
| Phase 01 P07 | 136min | 3 tasks | 8 files |
| Phase 01 P08 | 35min | 1 tasks | 5 files |

## Accumulated Context

### Roadmap Evolution

- Phase 4 added (2026-08-25), then renumbered to Phase 3 — "Visual Polish on Real Glass": user asked to split Phase 2 into a functional pass and a design-polish pass; since Phase 2 already built up from basic to polished internally across its 5 plans (02-01 bare flight number → 02-04 route/airline captions) and its only remaining plan (02-05) is pure deployment infra with no visual work, the agreed split instead adds a new phase after real hardware exists, dedicated to refining the already-built design against actual Spectra 6 output — closing the hardware-verified-legibility items every Phase 2 SUMMARY.md carried forward rather than guessed at. Old Phase 3 (Low-Battery Indicator) renumbered to Phase 4.
- 01-08 (battery-life measurement, DEVICE-05) moved from Phase 1 to Phase 4 (2026-08-26), becoming 04-01: user wants the unattended multi-day (up to 21-day) discharge run scheduled at the end of the project, once other phases no longer need this Mac to stay awake continuously, rather than mid-Phase-1. Phase 1's goal/success-criteria trimmed to drop the on-battery-viability criterion (now Phase 4's job); Phase 1 is now 7/7 plans executed. Phase 4 renamed "Battery Life & Low-Battery Indicator", gained requirement DEVICE-05 alongside DEVICE-04 and a new success criterion for the measured mAh-per-cycle figure. Task 1 (checker + pre-registered protocol) was already done under the old numbering and carries over unchanged; only the phase/plan numbers and cross-references were updated. REQUIREMENTS.md's DEVICE-05 checkbox corrected from a stale pre-existing `[x] Complete` (predating this move, predating the actual measurement) to `[ ]` — only Task 1 of 3 is done.

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
- [Phase 01]: 01-07 Task 1/2 complete - hardware/logtools.py (stdlib-only stamp/check-backoff/selftest) proven on 3 fixtures before hardware use; real doubling curve (300/600/1200/2400/4800s across backoff_n=0..4) captured on real hardware over an ~80min unattended run and machine-verified. Known low-severity finding: the WiFi SSID leaks into backoff-run.log via ESP-IDF's own wifi component debug line (not the project's Log Line Contract, not the bearer token/password/setup secret) - documented in 01-07-SUMMARY.md, not yet fixed (would need a reflash+recapture).
- [Phase 01]: 01-07 Task 3 (power-cycle persistence proof) deliberately deferred overnight at explicit user request - device left connected (USB) with battery still disconnected, holding backoff_n=5 in NVS; stub server left stopped (Task 3 needs it down through its own step 6); capture loop + caffeinate stopped so the Mac can sleep normally.
- [Phase 01]: 01-07 Task 3 complete: NVS failure counter proven to survive three real physical power cycles (no battery) - backoff_n continued 7->8 across a power-cycle where the wall-clock gap (12m37s vs a 6h/21600s armed sleep) makes an external interruption mathematically certain; recovery poll + follow-up failure proved a success resets to backoff_n=0/sleep_s=300. The literal 'wake reason=power-on' console line could not be captured on any of 3 cold power-ons (diagnosed via macOS kernel USB log as a genuine USB re-enumeration delay on this board's marginal connection, not a capture-script bug or firmware defect); corroborated instead via the device's own X-Boot-Reason=power-on HTTP telemetry header. Full diagnosis in hardware/BACKOFF-OBSERVATION.md. DEVICE-03 marked complete.
- [Phase 04]: 04-01 Task 1 (formerly 01-08, moved 2026-08-26): check-battery checker + BATTERY-RUN.md protocol pre-registered (thresholds, 21-day ceiling, 3000mAh capacity from BOM.md) before the battery pack was connected - proven on 3 new fixtures (battery-good accepted; battery-gap/battery-flat-mv rejected). Tasks 2 (multi-day unattended run) and 3 (post-mortem verdict) remain, deliberately deferred to end of project.

### Pending Todos

None yet.

### Blockers/Concerns

- Research flagged as unverified before commit: exact AeroDataBox tier/cost is not needed (project uses local ADS-B, not AeroDataBox, per PROJECT.md's reversed decision) — but PRIM/IDFM's exact SIRI Lite quota figures are community-sourced only; not a v1 blocker (RER deferred to v2 as of 2026-08-11) — verify against the live account dashboard before finalizing RER poll cadence when v2 planning starts.
- Spectra 6 dual-chip display driver — RESOLVED 2026-08-25 (01-06): EE02 board profile verified against real hardware with zero corrections needed, first light achieved (all 5 visual checks passed), Log Line Contract captured live.
- No publicly confirmed enclosure design exists for the EE02 kit — budget design time in Phase 1 or plan around an off-the-shelf enclosure.
- Battery-life real-world figure for this exact hardware combo is unmeasured — 04-01's Task 1 (check-battery checker + pre-registered protocol) is done; Tasks 2 (multi-day unattended discharge run, needs the Mac to stay awake continuously) and 3 (post-mortem readout) are deliberately deferred to the end of the project (user decision, 2026-08-26) rather than done now.
- 02-05 Task 3 (on-glass verification with real OVH data) is IN PROGRESS: firmware repointed at the real base URL and rebuilt, waiting on the device being reconnected via USB to flash and verify.
- Device wake interval (how often the physical frame polls the server, decoupled from the server's own 30s ADS-B poll) is currently 300s in the test/bring-up config — NOT yet a tuned production value. Real tradeoff: shorter interval = fresher plane-departure info but faster battery drain; longer = more autonomy but a departure could be several minutes stale by the time it's shown. Decision deliberately deferred until Phase 4's 04-01 produces a real mAh-per-cycle figure — tune this once actual battery-life data exists, not before.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none — first milestone)* | | | |

## Session Continuity

Last session: 2026-08-26T08:45:00.000Z
Stopped at: 02-05 Task 3 in progress — firmware rebuilt with real OVH base URL, awaiting device USB reconnection to flash and verify on physical glass

Resume file: `.planning/phases/02-plane-view-end-to-end-slice/02-05-PLAN.md` — resume at Task 3. (Phase 4's `.planning/phases/04-low-battery-indicator/04-01-PLAN.md` resumes at Task 2 whenever the multi-day battery run is scheduled, per user decision to defer it to end of project.)

**State at end of this session:**

- Device: connected via USB, battery still disconnected (Task 1 was fully autonomous, no hardware/battery involved). Stub server not running.
- `hardware/logtools.py check-battery` is built and proven on 3 fixtures (`battery-good` accepted; `battery-gap`, `battery-flat-mv` rejected); `hardware/BATTERY-RUN.md`'s `## Run Protocol (pre-registered)` section is committed with the D-07 thresholds, 21-day ceiling and the pack's real 3000mAh rating from `hardware/BOM.md`.
- 01-07's DEVICE-03 backoff observation is complete and machine-checked, with one disclosed capture-tooling limitation (see `hardware/BACKOFF-OBSERVATION.md`'s "Capture-Timing Limitation" section) — the underlying persistence property is proven via a decisive wall-clock argument and independent HTTP-telemetry corroboration, not merely a clean automated-checker exit code.
- Before Task 2 connects the battery for the first time, `hardware/BRINGUP-LOG.md`'s deferred polarity check (JST connector orientation against the board's silkscreen) is still an outstanding blocking prerequisite, and Task 2's own `<how-to-verify>` steps require confirming the pack's protection circuit and the laptop's ability to stay awake/networked for up to 21 days before starting.
