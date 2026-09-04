# SkyPane

## What This Is

An e-ink wall/desk frame that shows real-time departure info for flights taking off from Paris-Orly (ORY) runway 3. Built on the same "wake → poll → display → deep sleep" architecture as the flightportrait reference project, running on battery power, with a small always-on cloud server generating the display images. v1 ships as a single-view (plane-only) device; the next RER trains from Orly-Ville station and the physical button to switch between views are deferred to v2 (2026-08-11 scope decision — see Key Decisions).

## Core Value

Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.

## Requirements

### Validated

- [x] User can see flight number, airline, and destination for the next plane departing from Orly runway 3 (Phase 2, 02-05 Task 3 — on-glass verified 2026-08-26)
- [x] User can see flight number, airline, and origin for the next plane landing on runway 3 (Phase 2, 02-05 Task 3 — on-glass verified 2026-08-26 with a real flight, DAH1112 from Béjaïa)
- [x] Plane view updates one flight at a time, as real aircraft use runway 3, detected via free public ADS-B aggregator APIs — not a fixed schedule (Phase 2, 02-05 Task 3 — real end-to-end pipeline confirmed against the live OVH deployment)

### Active

- [ ] (v2/later) User can see line, destination, and minutes-until-departure for the next 2+ RER trains from Orly-Ville
- [ ] (v2/later) User can see a "leave by" cue combining the next RER train's countdown with a fixed walk-time buffer
- [ ] (v2/later) User can see a disruption banner on the RER view during a service disruption on the line
- [ ] (v2/later) Physical button on the device switches between the plane view and the RER view
- [ ] (v2/later) Switching views (button press) triggers a fresh poll for that view's data
- [ ] Device wakes on a schedule, polls the server over HTTPS, downloads a new image if one is available, displays it, then returns to deep sleep (mirrors flightportrait's wake/poll/backoff model)
- [ ] User can see a low-battery indicator on the frame when the battery is running low
- [ ] Device runs on battery power for v1 (no wall power, no solar)
- [ ] Server (small cloud VPS) ingests local ADS-B data for runway-3 detection, fetches RER data, renders display images, and serves them via a poll protocol the device calls
- [ ] (v2/later) Companion phone app can push a short message that appears on the frame

### Out of Scope

- Solar charging — deferred until real battery life and frame placement are known; indoor solar is unreliable without a well-lit window
- Public flight-data/schedule API (e.g. AeroDataBox) as the plane-detection source — reversed after scoping: the actual goal is "the specific plane using runway 3 right now," which schedule APIs don't expose (no runway/operational data); local ADS-B detects real aircraft directly
- Wall power — battery-only for v1, to force realistic power-budget decisions early
- Freshness timestamp / graceful stale-offline handling on the display — explicitly deferred by user for v1 despite research flagging it as a risk (frame could show stale data without indicating it); revisit if staleness becomes a real problem
- Additional views beyond plane/RER (weather, other transit lines, etc.) — stay two-view (long-term) to preserve focus
- RER view and physical button view-switching — deferred to v2 (2026-08-11); v1 ships as a single-view (plane-only) device
- Status LEDs, on-device settings/menu UI, gate/terminal/check-in fields, push notifications to phone, animated transitions — anti-features that would make the frame read as a gadget rather than ambient art

## Context

- **Reference project**: [flightportrait/frame](https://github.com/flightportrait/frame) — 13.3" E Ink Spectra 6 display (1200×1600, color), ESP32-S3 (reTerminal E1004 or XIAO ESP32-S3 Plus + EE02 driver board), microSD for offline images, BLE Security 2 provisioning, exponential-backoff polling (caps at 6h), SHA-256 verified downloads, persistent error logging, 3-endpoint HTTPS polling protocol (`docs/PROTOCOL.md`), reference Python server included. The device never accepts incoming connections — poll-only, no open ports.
- **Plane detection approach**: free public ADS-B aggregator APIs, geofenced to runway 3's flight path, detect real aircraft directly (one plane at a time, departure or arrival depending on current wind-driven runway configuration), rather than pulling a schedule from a public flight-data API. Originally planned around a local RTL-SDR receiver; Phase 1 plan 01-04 validated the aggregators clear the coverage bar (~92min real traffic, 38/37 distinct aircraft, 2/2 on-ground) with no RTL-SDR hardware needed — corrected here 2026-08-26 at Phase 1 close, see Key Decisions. **Correction (2026-08-27):** adsb.fi is now the sole default provider — airplanes.live discontinued its free API tier that day; see Key Decisions. **Correction (2026-08-27, later the same day):** adsb.lol was added as a second default provider alongside adsb.fi, so a production poll now cross-validates two independent sources instead of running single-source; see Key Decisions.
- **Address / reception feasibility**: <street-address> — this commune borders/partially contains Orly airport itself; runway 3 (the 08/26 runway, ~3,320m) is close by. Low-altitude ADS-B coverage at this range was validated early with real traffic against the two aggregators above, confirming reception is reliable without needing dedicated RTL-SDR hardware.
- **Airport**: Paris-Orly (ORY), specifically runway 3
- **RER station**: Orly-Ville
- **Motivation**: equal parts satisfying hardware build / ambient art piece, and genuinely useful daily tool (e.g. checking whether you'll make the next RER before leaving the house)

## Constraints

- **Budget**: Hardware ≤ €300 total (display + compute) — user-set ceiling, roughly matches flightportrait-class hardware cost
- **Power**: Battery-only for v1, no solar, no wall power — indoor solar placement is unreliable, and the user wants real battery-life data before considering solar
- **Server hosting**: Small always-on cloud VPS, not a home server — a home server/Raspberry Pi is only reachable while powered and networked; the device should always find a reachable server

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Free public ADS-B aggregator APIs (airplanes.live primary, adsb.fi secondary), geofenced to runway 3, instead of a public flight-data/schedule API or a local RTL-SDR receiver | The real goal is "the specific plane using runway 3 right now" (departure or arrival) — schedule APIs don't expose runway/operational data; ADS-B detects real aircraft directly. Originally planned around a local RTL-SDR receiver, but Phase 1 plan 01-04 validated the free aggregators clear the coverage bar with no dedicated hardware needed | Validated 2026-08-05 (01-04): ~92min real traffic, 38/37 distinct aircraft ≤3000ft, 2/2 on-ground; no RTL-SDR ordered. Superseded 2026-08-27 — the provider-ordering half only, see row below. |
| Hardware mirrors flightportrait (13.3" E Ink Spectra 6 + ESP32-S3-class board) | Proven reference design, fits the €300 budget | — Pending |
| Battery-only power for v1, defer solar | Indoor solar reliability is unknown until placement and battery life are validated | — Pending |
| Physical button switches plane/RER view and triggers a fresh poll | Matches flightportrait's wake/poll/deep-sleep model while giving on-demand refresh on interaction | Superseded 2026-08-11 — deferred to v2, see below |
| Server on a small cloud VPS, not a home server | Reliability — the device should always find a reachable server, not one that depends on home power/network uptime | — Pending |
| No freshness timestamp / stale-data indicator in v1 | User explicitly chose to keep v1 simpler and accept the risk, despite research flagging this as a common pitfall (device could show stale data with no indication) | — Pending, revisit if staleness becomes a real problem |
| Defer RER view and physical button view-switching to v2; v1 ships single-view (plane-only) | User-requested scope reduction to focus v1 on shipping the plane view well rather than two views at once; ROADMAP.md's Phase 3 (RER View) removed, old Phase 4 renumbered to Phase 3 and trimmed to just the low-battery indicator (DEVICE-04) | Decided 2026-08-11 |
| OVH VPS-1 instead of Hetzner CX22 for hosting | Same spec/price class; user explicit redirect after a live price/locale comparison; D-P2-06 already left infrastructure specifics to discretion | Deployed and live-verified 2026-08-25/26 (`<public-host>`) |
| Device NVS partition is never cleared by a normal app-region firmware flash | Discovered live during 02-05 Task 3: after repointing firmware at the real server, the device kept sending a bearer token issued by the Phase 1 local-stub server, since only the app region (not the `nvs` partition at 0x9000) is rewritten by `flash.sh`. The firmware also never detects/clears a stale token on a 401 — it just retries with the same one forever under backoff | Fixed by erasing the NVS region directly (`esptool erase-region 0x9000 0x6000`); worth remembering for any future backend/secret rotation on already-flashed hardware |
| adsb.fi promoted to sole default ADS-B provider; the airplanes.live entry retained in `server/plane/detect.py` as an explicit `--provider` opt-in but never queried by an automated poll | airplanes.live discontinued its free API tier on 2026-08-27, gating access behind running a feeder, a paid sponsorship, or a commercial licence — all three declined. adsb.fi independently cleared the same Phase 1 coverage bar (see `adsb-test/RESULTS.md`: 38 vs 37 distinct aircraft ≤3000ft, 2/2 on-ground, both PASS), and staying on a free source preserves the original reason for choosing free aggregators over a paid schedule API. adsb.fi's median position-update gap (36.2s) is slower than airplanes.live's (22.4s), and RESULTS.md also recorded one sample error for adsbfi against zero for airplaneslive over that window; RESULTS.md's own verdict already judged the cadence miss immaterial against the device's multi-minute refresh cycle — this is not a claim that adsb.fi is the better provider, only that it independently clears the same bar | Decided 2026-08-27 and live-verified the same day — the production airplanes.live endpoint returns HTTP 403, adsb.fi returns HTTP 200. Tradeoff accepted: one default provider, no automatic fallback, so an adsb.fi outage renders the Empty state. Superseded 2026-08-27 (later the same day) — the single-default-provider half only, see the row below. |
| adsb.lol registered as the second default ADS-B provider behind adsb.fi | The runway3-false-positive fix built per-poll cross-source validation that could never run with one default source; adsb.lol is CC0, drop-in compatible with the existing provider abstraction, and live-verified — with the disclosed future-API-key caveat named honestly | Decided 2026-08-27. Tradeoffs accepted: two requests per cycle instead of one, and a genuinely reachable disagreement branch that holds the panel rather than guessing (D-04's "leave the panel alone") |
| Device wake interval (`SKYPANE_SLEEP_S`) made web-configurable, delivered via the existing `/device/v1/display` poll response, layered underneath Phase 10's quiet-hours `sleep_s` extension rather than replacing it | `SEED-002`'s own recommended delivery mechanism; avoids SSH-only edits + a service restart for a setting the developer already needed to change by hand during Phase 5's battery run | Decided and shipped 2026-09-04 (Phase 11, 4/4 plans). Bounds locked to 60-3600s — the 60s floor reuses `firmware/main/Kconfig.projbuild`'s existing `FP_MIN_REFRESH_SPACING_S` engineering margin, corrected live from an initial ungrounded "10s" auto-guess. Settings-page pre-fill reads `SKYPANE_SLEEP_S` from the process environment (same pattern as the companion password), not by parsing `skypane.env`. Real consequence: the deployed `SKYPANE_SLEEP_S=30` is now below the form's own floor and can no longer be re-entered through the web UI (shows the placeholder instead). Verified 22/22 automated + 1/1 human must-haves; 0 open security threats (`11-SECURITY.md`) |
| Scheduled quiet hours (curfew) pauses the wake/poll/display cycle by extending the server-computed `sleep_s` past the window's end, instead of keeping the normal wake cadence and only skipping the display refresh | `SEED-001`'s own premise assumed the fuller pause needed firmware changes; corrected live during `/gsd-discuss-phase 10` — `sleep_s` is already a fully server-controlled, per-response value the firmware just deep-sleeps for, so the bigger battery win needed zero firmware changes. Promoted ahead of its original trigger (Phase 5's still-pending real battery-discharge verdict) at the developer's direct request | Decided and shipped 2026-09-03 (Phase 10, 5/5 plans). One recurring Europe/Paris start/end window + independent enabled flag, set on the companion Settings page; a dedicated "QUIET HOURS / Back at HH:MM" panel screen at window entry, no symmetric screen at exit. DST-safe window arithmetic duplicated byte-for-byte across `server/device_config.py` and the vendored, stdlib-only `stub-server/byos_server.py`. Verified 27/28 automated + 2/2 human must-haves; 0 open security threats (`10-SECURITY.md`) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-04 after Phase 11 completion (Web-configurable wake interval — unmapped backlog phase promoted from SEED-002, no Requirements-list change; verified 22/22 automated + 1/1 human must-haves, `11-VERIFICATION.md`; 0 open security threats, `11-SECURITY.md`). No requirement wording changed; see Key Decisions for the delivery/pre-fill decisions. Note: Phase 11 is the highest-numbered phase, but the v1.0 milestone is NOT complete — `06.6.4.1-09-PLAN.md`, a mandatory developer-sign-off closing checkpoint, has never been executed. See STATE.md Blockers/Concerns.*
