---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 03
current_phase_name: visual-polish-on-real-glass
status: executing
stopped_at: Phase 3 context gathered
last_updated: "2026-08-26T10:22:00.789Z"
last_activity: 2026-08-26
last_activity_desc: "Phase 3 discuss-phase complete: scope widened to include per-airline generated aircraft illustrations (SenseCraft confirmed dithering viable on real hardware). 03-CONTEXT.md and 03-DISCUSSION-LOG.md written; ROADMAP.md Phase 3 section updated with a new success criterion; REQUIREMENTS.md gained v2 VIS-01 (deferred photo background). Next: /gsd-plan-phase 3."
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 13
  completed_plans: 12
  percent: 92
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.
**Current focus:** Phase 03 — visual-polish-on-real-glass (not yet planned)

## Current Position

Phase: 02 (plane-view-end-to-end-slice) — COMPLETE (5/5 plans)
Plan: 02-05 Task 3 of 3 complete — physical frame verified on real glass against the live OVH deployment
Status: Phase 1 and Phase 2 both formally complete. Phase 2's last gate (02-05 Task 3, on-glass human verification) passed this session: firmware flashed with the real OVH base URL, a stale-NVS-bearer-token bug found and fixed live (device was sending a Phase-1-local-stub token to the real server), and the developer confirmed legibility, edge quality, layout, a real-flight cross-check (DAH1112 from Béjaïa), and a forced enrichment-fallback caption, all on real Spectra 6 glass. A-02-02-01's real-departure threshold check is explicitly deferred (every real detection so far has been an arrival) — carried forward as an open item for Phase 3. Next: `/gsd-plan-phase 3` to plan Visual Polish on Real Glass.
Last activity: 2026-08-26 — 02-05 Task 3 completed, Phase 2 closed

Progress: [██████████] 100% (Phase 2)

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
- [Phase 02]: 02-05 Task 3 complete (2026-08-26): firmware flashed with the real OVH base URL. Found and fixed a real bug live - the device's NVS partition still held a bearer token from Phase 1 local-stub testing (NVS is untouched by an app-region-only flash), so the first poll against the real server 401'd; fixed by erasing just the NVS region (0x9000/0x6000), forcing re-enrollment. Confirmed end-to-end via server logs (setup 200 -> display 200 -> img 200, hash-matched 960,000 bytes) and developer sign-off on real glass: legibility "clearly legible", edges "hard, flat", layout correct (left-facing arrival, no clipping), real-flight cross-check (DAH1112 from Béjaïa), and a forced enrichment-fallback caption (EJU84YF, via the real render code path) both confirmed. Step 6 (real-departure threshold, A-02-02-01) explicitly deferred by developer choice - every real detection so far has been an arrival; carried forward as an open item for Phase 3. PLANE-01/02/03 now marked complete in REQUIREMENTS.md. Phase 2 closed (5/5 plans).
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
- Device wake interval (`sleep_s`, how often the physical frame polls the server) is currently **30s** on the live OVH deployment (`inkframe.env`'s `INK_SLEEP_S=30`, verified directly on the VPS 2026-08-26 — same cadence as the server's own ADS-B poll timer, not yet distinguished) — NOT yet a tuned production value, this is the bring-up/test default. Real tradeoff: shorter interval = fresher plane-departure info but faster battery drain; longer = more autonomy but a departure could be several minutes stale by the time it's shown. Decision deliberately deferred until Phase 4's 04-01 produces a real mAh-per-cycle figure — tune this once actual battery-life data exists, not before.
- A-02-02-01 (departure-side D-03 threshold, +200 ft/min) has never been observed against a real runway-3 departure — every real detection so far (Phase 1's sample and 02-05 Task 3's on-glass check) has been an arrival. Not a known defect, just unvalidated. Scoped to close in Phase 3 (success criterion 3 already names it); check `journalctl -u inkframe-poll` on the VPS for `confirmed_state=departing` whenever it's convenient before or during Phase 3 planning.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none — first milestone)* | | | |

## Session Continuity

Last session: 2026-08-26T10:22:00.785Z
Stopped at: Phase 3 context gathered

Resume file: .planning/phases/03-visual-polish-on-real-glass/03-CONTEXT.md

**State at end of this session (2026-08-26, ~09:25):**

- Device: flashed with production firmware pointed at the real OVH server, running on battery power (JST connector repinned and verified against the board's silkscreen `+` marking earlier this session — correct polarity confirmed before connecting). Currently on its normal wake/poll/sleep cycle against the live deployment.
- Phase 2 fully closed: all 5 plans complete, ROADMAP success criterion 4 satisfied, PLANE-01/02/03 marked complete in REQUIREMENTS.md.
- The OVH VPS's `inkframe-poll.timer` is running normally (restarted after the Task 3 forced-fallback test); live ADS-B detection has resumed.
- Open item carried into Phase 3: A-02-02-01's real-departure threshold has never been observed (see Blockers/Concerns above).
- Prior-session battery-measurement context (`hardware/logtools.py check-battery`, `hardware/BATTERY-RUN.md`'s pre-registered protocol) is unchanged and still deliberately deferred to end-of-project per Phase 4's scope note — Tasks 2/3 of 04-01 not started.
- Next step: `/gsd-plan-phase 3` to plan Visual Polish on Real Glass.
