# Project Research Summary

**Project:** Ink Frame (e-ink Orly departure/RER board)
**Domain:** Battery-powered e-ink IoT ambient display (ESP32-S3 device + cloud render server + external flight/transit APIs)
**Researched:** 2026-08-04
**Confidence:** MEDIUM

## Executive Summary

Ink Frame is a battery-powered, wall-mounted e-ink "departure board" that shows Orly (ORY) flight departures and Orly-Ville RER-B next-departures, switching between two views on a physical button press. The domain has a strong direct precedent — flightportrait's open-source `frame` project — which supplies a proven hardware target (Seeed XIAO ESP32-S3 Plus + 13.3" E Ink Spectra 6 panel), a battle-tested device↔server poll protocol (3 HTTPS endpoints, SHA-256 image verification, exponential backoff, device-initiated-only connections), and a "device blits, server renders" architectural split that keeps firmware simple and puts all layout/rendering/color-quantization logic in a Python server. Recommended stack: ESP-IDF (not Arduino) firmware, Python + FastAPI/Flask + Pillow render server, AeroDataBox for ORY flight data ($5/mo Pro tier), IDFM's PRIM SIRI Lite API for RER-B next-departures (free), and a small always-on Hetzner CX22 VPS (~€4.35/mo) — all comfortably inside the stated €300 hardware / low-monthly-cost budget.

The single biggest risk across all four research areas is **battery-life estimation**: naive "deep sleep current only" math overstates battery life by 5-10x, because active WiFi/TLS/e-ink-refresh time dominates the real energy budget. This must be measured on real hardware early and used to set the wake/poll interval (recommended: 15-30 min scheduled poll + button-triggered on-demand refresh), not assumed. Secondary risks cluster around external API fragility: cheap flight/transit APIs have real rate limits and staleness windows that can make the device confidently show wrong information (a cancelled flight as on-time, a disrupted RER line as normal) unless the server enforces an explicit data-staleness gate and a "last known good, marked stale" fallback — never a silent stale display and never a blank/broken one.

The recommended architecture cleanly separates concerns: independent scheduled fetchers (flight, transit) write into a render cache; a stateless poll API serves only from that cache (never calling upstream APIs synchronously in response to a device request); and the device itself never accepts inbound connections, only polls out. This split lets device firmware and server backend be built and tested almost entirely in parallel, using `docs/PROTOCOL.md` as the sole contract between them — a structural decision with direct implications for phase sequencing (see below).

## Key Findings

### Recommended Stack

The stack mirrors flightportrait's reference implementation closely, deliberately, so its firmware/server code can be studied or adapted rather than re-derived from scratch.

**Core technologies:**
- **ESP-IDF (C), ≥5.3** on Seeed XIAO ESP32-S3 Plus + 13.3" Spectra 6 (EE02 kit, ~€152) — matches the reference firmware exactly, gives full control over sleep-current tuning (the top risk factor); avoid the Arduino framework for shipped firmware.
- **ESP-IDF `wifi_provisioning` (BLE, Security 2)** — built-in, audited provisioning stack; don't roll a custom one.
- **Python 3.12 + FastAPI/Flask + Pillow** — server render pipeline; Pillow handles 6-color quantization/dithering (Floyd-Steinberg; validate output against real hardware — LOW confidence on dithering quality).
- **APScheduler (or cron)** — decoupled scheduled fetch/render jobs, independent of device poll requests.
- **AeroDataBox (Pro, $5/mo)** — ORY flight FIDS data; reject OpenSky (no scheduled-flight data), AviationStack/FlightAware (too expensive for a single-airport hobby use case).
- **IDFM PRIM SIRI Lite API (free)** — RER-B Orly-Ville next-departures; official RATP/IDFM-endorsed source.
- **Hetzner CX22 VPS (~€4.35/mo)** — always-on hosting; explicitly avoid scale-to-zero platforms (Fly.io free tier) since the project requires the server to always be reachable.

### Expected Features

**Must have (table stakes) — v1:**
- Plane view: flight number, destination, scheduled time, delay/cancelled status
- RER view: line, destination, minutes-until-next (≥2 upcoming departures)
- Physical single-button: switch view + force a genuinely fresh poll (not stale cache)
- Freshness indicator ("as of HH:MM") on both views
- Graceful stale/unreachable-server state — never blank, never silently stale
- Wake/poll/display/deep-sleep cycle with exponential backoff
- Ambient-first, chrome-free visual layout (no status LEDs, no menus)

**Should have (differentiators) — v1.x:**
- "Will I make it?" framing — countdown + fixed walk-time buffer (pure render-layer logic, high value/low cost)
- Color-coded delay/disruption severity (hardware already supports 6-color)
- Per-view independent poll/backoff state (so a button press doesn't force-refetch the view being left)

**Defer (v2+):**
- RER disruption banner (separate RATP traffic-info feed) — only if disruptions on this specific line prove frequent enough to matter
- Companion phone-app push messaging — must respect poll-only security model (message waits in cache, device pulls it, never pushed to device)
- Additional views (weather, other lines) — explicitly resist; stay two-view to preserve focus
- Anti-features to actively avoid: live/streaming updates, partial-refresh-only, status LEDs, on-device settings UI, gate/terminal fields, push notifications, animations

### Architecture Approach

Device and server are fully independent codebases connected only by a shared `PROTOCOL.md` contract, enabling parallel build tracks. The device is poll-only and outbound-only (no listening socket); it downloads a pre-rendered, pre-quantized bitmap, verifies SHA-256 + exact size, blits it via full refresh, and returns to deep sleep for a server-specified interval. The server never renders synchronously in response to a device poll — independent scheduled fetchers (flight, transit) populate a render cache on their own cadences, and the poll API is a pure cache reader. A button press is not a separate protocol path: it just sets `active_view` in NVS and immediately triggers the same poll flow outside the timer schedule.

**Major components:**
1. **Device state machine** (ESP-IDF) — wake dispatch, poll orchestration, backoff, NVS-persisted view/hash state
2. **Server poll API** — stateless, cache-only HTTP handler for the 3 device endpoints (setup/display/log)
3. **Server fetchers** (flight, transit) — independent scheduled jobs, normalize external API data, trigger re-render
4. **Server render pipeline** — layout → 6-color quantize → pack to device binary format, shared packer across both views

### Critical Pitfalls

1. **Battery-life estimates 5-10x optimistic if based on deep-sleep current alone** — active WiFi/TLS/refresh time dominates; must bench-measure mAh/wake-cycle and size wake interval + battery from real numbers, not datasheet sleep current.
2. **E-ink refresh current spikes cause brownouts on battery**, especially at low charge — must test refresh reliability under battery load at low state of charge, not just bench power; add adequate decoupling capacitance and a firmware refresh-completion check.
3. **Flight/RER data staleness can show confidently wrong information** (cancelled flight as on-time, disrupted line as normal) — enforce an explicit staleness budget in the render pipeline before publishing any image; never render from data older than a defined threshold.
4. **PRIM/IDFM quota can be blown through fast with naive fixed-interval polling** — cache with TTL tied to actual device wake frequency, monitor the quota dashboard from day one, don't hardcode assumptions from tutorials.
5. **Ghosting and multi-second refresh flash have direct UX consequences** for a "glance and go" device — decide full-refresh-only vs. partial+periodic-full explicitly, and design the button-press interaction around real refresh latency (12-30s) rather than assuming near-instant feedback.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Device/Server Protocol + Hardware Bring-up
**Rationale:** The device↔server protocol is the sole coupling point between two otherwise-independent subsystems; establishing it first (mirroring flightportrait's `PROTOCOL.md`) unblocks fully parallel work afterward. Hardware bring-up (display driver, deep sleep, battery measurement) must start immediately because Pitfall 1 (battery life) is foundational and shapes every later UX/interval decision.
**Delivers:** Working display driver + deep sleep + wake-poll-sleep cycle against a minimal stub server; bench-measured mAh/wake-cycle number.
**Addresses:** Wake/poll/deep-sleep architecture (table stakes)
**Avoids:** Pitfall 1 (battery estimation gap), Pitfall 2 (refresh brownout) — both require early hardware validation before committing to a battery/interval choice.

### Phase 2: Server Data Pipeline (Flight + Transit Fetchers)
**Rationale:** Fetch/render/cache logic is independent of device firmware once the protocol contract exists; building it in parallel with Phase 1's later stages minimizes idle time. This phase also carries the highest external-integration risk (API selection, quotas, staleness).
**Delivers:** Independent scheduled fetchers for AeroDataBox (ORY) and PRIM (RER-B), normalized data models, render cache with staleness gating.
**Uses:** Python/FastAPI/Pillow/APScheduler from STACK.md
**Implements:** Fetcher → render cache → poll-API-reads-cache pattern (Architecture Pattern 3)
**Avoids:** Pitfall 4 (flight staleness), Pitfall 5 (PRIM quota exhaustion), Pitfall 6 (disruption gaps deferred but staleness gate must exist from the start)

### Phase 3: Rendering + Device Display Integration
**Rationale:** Once both the device poll client and server render cache exist independently, join them: implement the actual plane/RER view layouts, 6-color quantization, and validate the full loop end-to-end on real hardware (not a stub).
**Delivers:** Two working views (plane, RER) rendered server-side, packed, verified, and blitted on-device; freshness timestamp; graceful stale/offline states.
**Addresses:** Table-stakes feature set (flight/RER fields, freshness indicator, graceful degradation)
**Avoids:** Pitfall 3 (ghosting/refresh-latency UX) — decide full-refresh-only strategy here.

### Phase 4: Button Interaction + Backoff Hardening
**Rationale:** Button-triggered view switch + forced poll is architecturally "the same flow, forced" (Pattern 2) — building it after the base poll loop is proven avoids creating a second, divergent code path. Backoff/security hardening (token rotation, image-hash verification enforcement, no plaintext fallback) belongs here as a pre-ship gate.
**Delivers:** Physical button wired to view-switch + forced poll; exponential backoff fully wired; security checklist closed (hash verification, HTTPS-only release builds, token rotation).
**Addresses:** Physical button (table stakes), per-view backoff state (differentiator)
**Avoids:** Pitfall Anti-Pattern 3 (button bypassing backoff state); security mistakes table (hash verification, token rotation, no logged secrets)

### Phase 5: Polish / Differentiators (v1.x)
**Rationale:** Deferred until the core two-view loop is validated as genuinely useful day-to-day, per the MVP-then-validate structure in FEATURES.md.
**Delivers:** "Leave by" walk-buffer framing, color-coded delay/disruption severity, low-battery on-device indication (once real battery data exists).

### Phase Ordering Rationale

- Hardware/protocol bring-up must come first because battery-life and refresh-reliability findings (Pitfalls 1-2) are foundational constraints that shape the wake-interval and UX decisions every later phase depends on.
- Server data pipeline and device firmware can run largely in parallel once the protocol contract (`PROTOCOL.md`) is fixed in Phase 1 — this mirrors the architecture's explicit design intent (device/server as independent codebases).
- Rendering/display integration is sequenced after both halves exist independently, since it's the join point requiring both a working device poll client and a working server render cache.
- Button interaction is deliberately sequenced after the base poll loop is proven, since research warns against building it as a divergent second code path (Anti-Pattern 3).
- Differentiators are explicitly deferred to a v1.x phase per FEATURES.md's "add after validation" structure — this avoids scope creep into the MVP.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Server Data Pipeline):** AeroDataBox exact per-endpoint unit cost/tier and PRIM's exact quota figures were not independently confirmed (both flagged MEDIUM confidence) — verify against live account dashboards before finalizing poll cadence.
- **Phase 3 (Rendering):** Spectra 6 dual-chip display driver has no confirmed off-the-shelf library for the ESP-IDF path (flightportrait uses a custom driver, not GxEPD2) — budget research/dev time to port or hand-roll this.
- **Phase 1 (Hardware Bring-up):** No publicly confirmed enclosure design exists yet for the EE02 kit — budget design time or research alternatives.

Phases with standard patterns (skip research-phase):
- **Phase 4 (Button Interaction):** Well-documented pattern directly from flightportrait's reference protocol (Pattern 2) — implementation is largely "follow the reference."

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Cross-checked web sources; hardware pricing/VAT and the Spectra 6 dual-chip driver situation are LOW-confidence sub-points needing verification before purchase/commit |
| Features | MEDIUM | Cross-checked against TRMNL, RATP SIEL, and airport FIDS precedent, plus flightportrait's own marketing (single-source for some claims) |
| Architecture | HIGH (device/server protocol, power model) / MEDIUM (transit API specifics) | Primary source is flightportrait's own `docs/PROTOCOL.md`, fetched directly — strongest evidence in the whole research set |
| Pitfalls | MEDIUM | Primary source (flightportrait PROTOCOL.md) is strong; most other findings are cross-checked community/vendor sources, individually LOW but corroborated across 2+ sources |

**Overall confidence:** MEDIUM

### Gaps to Address

- **AeroDataBox exact endpoint tier/unit cost for ORY FIDS:** not confirmed against live docs — verify before finalizing poll frequency in Phase 2.
- **PRIM/IDFM exact quota figures:** community-sourced, not independently confirmed from the authoritative per-API quota table — sign up and check the account dashboard before finalizing RER poll interval.
- **Spectra 6 dual-chip ESP-IDF driver:** no confirmed off-the-shelf library exists for the production (non-Arduino) firmware path — flag as a Phase 1/3 research spike.
- **Enclosure design for the DIY EE02 kit:** unverified to exist publicly — budget design time in Phase 1.
- **Battery-life real-world figure for this exact hardware combo:** must be bench-measured in Phase 1, not assumed from datasheet or precedent (Inkplate 13SPECTRA's 40-50 days is a directional comparable, not a guarantee for this specific build).

## Sources

### Primary (HIGH confidence)
- flightportrait/frame `docs/PROTOCOL.md` (GitHub, direct fetch) — device↔server protocol, backoff, verification, OTA design
- flightportrait/frame repo overview (GitHub, direct fetch) — firmware module layout, reference server structure
- Espressif ESP-IDF official docs (sleep modes, wifi_provisioning) — deep sleep current, wake sources, provisioning stack

### Secondary (MEDIUM confidence)
- AeroDataBox pricing page (aerodatabox.com, direct fetch) — tier pricing
- PRIM API catalog pages (prim.iledefrance-mobilites.fr) — SIRI Lite scope, quota structure (page fetch partially blocked, community-sourced quota figures)
- Seeed Studio product pages (XIAO ePaper DIY Kit EE02, reTerminal E1004) — hardware pricing/specs
- TRMNL help docs + reviews — button refresh behavior, battery life precedent
- RATP/SIEL Wikipedia + official RATP site — real transit-board UX precedent
- Hetzner pricing roundups — VPS cost

### Tertiary (LOW confidence)
- GxEPD2 GitHub + community forum threads — Spectra 6 dual-chip driver specifics not independently confirmed
- ESP32 deep-sleep/battery community threads (Zbotic, deepbluembedded, lastminuteengineers) — cross-checked but community-sourced
- Inkplate 13SPECTRA real-world battery data — directional comparable only, not this exact hardware
- General smart-display/LED bedroom criticism — informs anti-feature stance, general commentary not a specific study

---
*Research completed: 2026-08-04*
*Ready for roadmap: yes*
