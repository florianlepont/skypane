# Technology Stack

**Project:** Ink Frame (e-ink Orly departure/RER board)
**Researched:** 2026-08-04
**Confidence:** MEDIUM (mostly web-search cross-checked; a few LOW-confidence spots flagged inline — verify against official docs before committing budget)

## Recommended Stack

### Device Hardware

| Component | Pick | Price (excl. EU VAT/shipping) | Purpose | Why |
|-----------|------|-------------------------------|---------|-----|
| Panel + driver kit | Seeed **XIAO ePaper DIY Kit EE02** (XIAO ESP32-S3 Plus driver board + 13.3" E Ink Spectra 6 panel, 1200×1600, 6-color) | ~$163.90 (~€152) as a bundle, or board $14.90 + panel $149 separately | Display + MCU | This is the exact reference hardware flightportrait targets — proven firmware compatibility, active community, and it's ~40% cheaper than the all-in-one option, leaving headroom in the €300 budget for a battery pack and enclosure |
| All-in-one alternative | Seeed **reTerminal E1004** (same panel/SoC, integrated 5000mAh battery, microSD, enclosure, quoted up to 6-month battery life) | $279.90 (~€258 before VAT) | Display + MCU + battery + case | The turnkey option flightportrait also supports. Confidence: MEDIUM — at ~19-21% EU VAT this can land near or over the €300 ceiling depending on shipping; budget the DIY kit first and treat this as the "buy convenience" upgrade if the build timeline is tight |
| Battery (DIY path) | Generic 18650/LiPo pack, 3.7V, 5000-6000mAh, with protection circuit (JST-PH connector to match EE02) | ~€10-15 | Power | XIAO ESP32-S3 Plus has onboard battery charge/monitoring circuitry (same family flightportrait uses); a 5000mAh pack roughly matches the reTerminal's stock capacity |
| Enclosure (DIY path) | 3D-printed or laser-cut frame (custom or community STL if published for EE02) | ~€10-30 | Housing | Not yet confirmed to exist publicly for EE02 — budget time to design one; Confidence: LOW (unverified) |

**Do NOT** default to a smaller/cheaper generic Waveshare panel (e.g. 7.5" 3-color) to save budget — the whole point of this build is the large-format 6-color Spectra departure-board look, and a smaller/fewer-color panel would require redesigning the render layout flightportrait already solved. Stick with the 13.3" Spectra 6 reference size.

**EU availability:** Seeed Studio operates an EU (Germany) warehouse, so both the kit and the reTerminal ship from within the EU — check applicable VAT is included at checkout rather than assuming the USD headline price. Confidence: MEDIUM (verify current landed price directly on seeedstudio.com/EU checkout before purchase, as pricing/VAT display shifted after a 2022 EU-warehouse rollout).

### Firmware

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|------------------|
| **ESP-IDF** | ≥ 5.3 (5.3.1 verified in the reference project) | Primary firmware framework, written in C | This is what flightportrait's firmware actually uses — matching it means you can study/fork its display driver, deep-sleep state machine, and provisioning code directly instead of re-deriving it. ESP-IDF also gives full control over sleep-mode power gating, which matters a lot for a battery-only device |
| **ESP-IDF `wifi_provisioning` component (BLE transport, Security 2)** | bundled with ESP-IDF | Wi-Fi/BLE provisioning | This is Espressif's own protocomm_ble stack (SRP6a key exchange + AES-GCM), exactly what flightportrait uses for factory-credential + runtime ECDSA auth. No third-party provisioning library needed — it's built into ESP-IDF |
| **esp_deep_sleep_start() + RTC timer wake** | ESP-IDF system API | Wake-poll-sleep cycle | ESP32-S3 deep sleep powers off CPU/RAM/peripherals, keeping only RTC memory + controller active; real-world ESP32-S3 e-paper projects report low-tens-of-µA sleep current, which is what makes weeks/months of battery life plausible for this device |
| **GxEPD2** (or Seeed's `Seeed_GxEPD2` fork) | latest | E-paper display driver | flightportrait's Arduino-path reference (`arduino-sd-demo`) drives the 13.3" Spectra 6 dual-chip panel through this fork. Confidence: MEDIUM — the base GxEPD2 repo (ZinggJM/GxEPD2) has broad Waveshare/GoodDisplay panel support, but the 13.3" Spectra 6 needs the dual-SSD-chip variant; the ESP-IDF (C) path in flightportrait uses a **custom** dual-chip driver instead of GxEPD2, meaning production-grade ESP-IDF firmware will likely need a hand-rolled or ported driver rather than an off-the-shelf library |

**Framework choice — Arduino vs ESP-IDF vs PlatformIO:** Use **ESP-IDF directly** (not the Arduino framework, and not PlatformIO's Arduino wrapper) for the shipped firmware. Arduino-as-a-component is fine for early prototyping and bring-up of the display driver (it's what Seeed's own demo uses), but flightportrait's production firmware — the thing this project is deliberately mirroring — is native ESP-IDF C, and that's also the framework with the most direct low-level control over sleep-current tuning, which is the single biggest risk for a battery-only device. PlatformIO can still be used as the *build tool/IDE integration* on top of ESP-IDF (`platform = espressif32`, `framework = espidf`) if you prefer its workflow over `idf.py` directly — that's a tooling preference, not a framework change.

### Server — Flight Data

| API | Pricing (hobby-relevant tier) | Provides | Verdict |
|-----|-------------------------------|----------|---------|
| **AeroDataBox** (via RapidAPI or api.market) | Free trial: 600 units/7 days. Pro: **$5/mo, 6,000 units, 1 req/s**. Pro 2: $15/mo, 24,000 units. Direct-subscribe Starter: $19/mo, 40,000 units, 5 req/s | Airport **FIDS** (Flight Information Display System) — scheduled *and* live departures/arrivals for a single airport (exactly what's needed for "next flights from ORY") | **Recommended.** This is the only one of the three commercial options that's realistically priced for a single-airport hobby project. A departure-board poll every 5-15 min for one airport easily fits in the $5-15/mo tier |
| AviationStack | Free: 100 req/month (too low to poll on any useful cadence). Paid: **$49.99/mo minimum** for 10,000 calls, up to $499.99/mo for 250,000 | Airport timetable (`/timetable`) and future schedules; free-tier schedule endpoints are additionally rate-limited to 1 req/60s | Reject for this project's budget — cheapest usable paid tier is 10x AeroDataBox's cost for a single-airport use case |
| FlightAware AeroAPI | Personal: $5 free usage/month, then pay-per-call. Standard: **$200/mo minimum**. Premium: much higher | Most authoritative/enterprise-grade flight data | Reject — overkill and overpriced for a hobby device; the $200/mo floor alone blows well past any reasonable server budget |
| OpenSky Network | Free (with registration for higher limits) | Real-time aircraft **state vectors** (ADS-B position/altitude/velocity), and airport arrivals/departures *derived from ADS-B contact*, not published schedules | **Reject as primary source.** Explicitly does not provide commercial flight-schedule data — an aircraft only shows up once it's transmitting ADS-B, so it can't show a flight that's scheduled-but-not-yet-departed, which a departure board needs. Could be a secondary enrichment source later (e.g., cross-checking live position) but not the core data feed |

**Verdict:** Use **AeroDataBox's Pro tier ($5/mo via RapidAPI/api.market)** as the flight-data source. It's the only option purpose-built for "give me the FIDS board for one airport" at a price that makes sense next to a €300 hardware budget and a few-euro/month VPS. Confidence: MEDIUM — pricing tiers verified from AeroDataBox's own pricing page and RapidAPI listing; the exact per-endpoint unit cost for the specific airport-FIDS/scheduled-departures call was not confirmed (endpoints are billed at Tier 1/2/3 = 1/2/6 units each) — check the live API docs for the specific endpoint's tier before committing to a poll frequency, since that determines how many airport polls/month the $5 Pro plan actually supports.

### Server — Transit Data

| Source | Auth | Format | Rate Limit | Verdict |
|--------|------|--------|------------|---------|
| **Île-de-France Mobilités PRIM platform** (`prim.iledefrance-mobilites.fr`) — "Next Departures" / `requete_globale` (StopMonitoring) API | Free PRIM account + API key sent via `apiKey` header | **SIRI Lite** (JSON) | Varies by API; real-time passage APIs commonly quoted around **20,000 requests/day**; new accounts get a lower default quota and must request an increase via the account's "My Consumption API" page | **Recommended.** This is the official, RATP/SNCF-endorsed open-data platform for Île-de-France public transit real-time data, purpose-built for exactly this ("next passages" at a specific stop). Query by the Orly-Ville RER-B `StopPointRef`/`monitoringRef` (look this up in PRIM's stop-point referential/GTFS export) |
| SNCF Open Data API | API key | JSON | Varies | Not recommended as primary — SNCF's public API is more oriented at long-distance/TGV and general Transilien schedule data; PRIM is the IDFM-native source specifically for RER/metro/bus/tram real-time next-departures and is the one the RATP/IDFM ecosystem steers third-party developers toward |

At a poll cadence of "once when the device wakes, once again if the user presses the physical view-switch button," daily request volume for a single household device will be a tiny fraction of the ~20,000/day quota — this is comfortably free-tier territory. Confidence: MEDIUM — the exact quota figure is a commonly-cited value from community sources, not independently confirmed from PRIM's authoritative per-API quota table; sign up for a PRIM account and check the specific StopMonitoring API's quota page before finalizing the poll interval.

### Server — Application Stack

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Python 3.12** | current stable | Server runtime | flightportrait ships a **reference Python server** implementing its 3-endpoint protocol — starting from/adapting that reference implementation is far less work than reimplementing the protocol (bearer-token auth, `X-Battery-Mv` header handling, SHA-256 image hashing, exponential-backoff-aware responses) from scratch in another language |
| **Flask** or **FastAPI** | Flask 3.x / FastAPI 0.11x | HTTP server for the 3-endpoint poll protocol | Either is fine at this traffic volume (one household device polling every few minutes to hours); FastAPI is the slightly more modern pick (async, auto-validated request/response models via Pydantic) if starting fresh rather than adapting flightportrait's reference server verbatim |
| **Pillow (PIL)** | 11.x | Render departure-board images (text layout, 6-color dithering) | The standard Python imaging library; `Image.quantize(palette=..., dither=Image.FLOYDSTEINBERG)` handles mapping a rendered RGB composition down to the Spectra 6 6-color palette. Confidence: LOW on the specific dithering-quality tradeoff — Pillow only implements Floyd-Steinberg (not more advanced options like Atkinson), which may need tuning for a 6-color panel; validate output quality against actual Spectra 6 hardware early |
| **APScheduler** or plain **cron** | APScheduler 3.x | Scheduled polling of AeroDataBox + PRIM to refresh cached data ahead of device wake-ups | Keeps the server pre-fetching/pre-rendering on its own schedule so the device's poll is always answered from a warm cache rather than blocking on upstream API latency during the device's short awake window (important for battery life — minimize time the device's radio is on) |
| **requests** | 2.32.x | HTTP client for AeroDataBox/PRIM API calls | Standard, boring, reliable choice for a small polling service |

**Why not Node.js + node-canvas:** It's a perfectly valid alternative (and `@napi-rs/canvas`, the modern Skia-backed successor to `node-canvas`, is faster and easier to install than the Cairo-based original) — but Python is the stronger default here specifically *because* flightportrait's reference server is Python, and reusing/adapting that reference implementation directly de-risks getting the poll protocol (headers, backoff semantics, hash verification) exactly right on the first try. If the builder is already a Node.js shop, `@napi-rs/canvas` + Express/Fastify is a reasonable substitute — just budget extra time to re-derive the protocol details from `docs/PROTOCOL.md` rather than reusing example code.

### Server — Hosting

| Technology | Version/Tier | Purpose | Why |
|------------|--------------|---------|-----|
| **Hetzner Cloud CX22** | 2 vCPU, 4GB RAM, 40GB NVMe, 20TB traffic | VPS hosting | ~€4.35/mo (~$4.59) post the mid-2026 Hetzner price adjustment — this workload (scheduled API polling, occasional Pillow rendering, serving small poll-protocol responses to one device) needs essentially none of a CX22's capacity, so it's comfortably oversized-for-cheap rather than tight. Hetzner's Falkenstein/Nuremberg datacenters are also low-latency to both the French transit/flight APIs and the device's home network in Paris |

Fly.io's free/hobby tier is an alternative if the builder wants zero fixed monthly cost and is comfortable with its always-on-app quirks (app can idle/sleep on the free tier, which would break "always reachable" — the project's own stated hosting requirement). Given the explicit "must always be reachable, not dependent on a machine's uptime" constraint, a small always-on Hetzner VPS is the safer default over a scale-to-zero platform.

## Installation

```bash
# --- Firmware toolchain (ESP-IDF) ---
git clone -b v5.3.1 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && ./install.sh esp32s3 && . ./export.sh
# (optional) build via PlatformIO instead of idf.py:
# platformio.ini: platform = espressif32, framework = espidf, board = seeed_xiao_esp32s3

# --- Server (Python) ---
python3.12 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pillow requests apscheduler python-dotenv
# or, if adapting flightportrait's reference server directly:
# pip install -r requirements.txt  (from the flightportrait/frame repo's server/ dir)
```

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|--------------------------|
| Hardware kit | XIAO ESP32-S3 Plus + EE02 (DIY) | reTerminal E1004 (all-in-one) | You want a finished enclosure + battery out of the box and don't mind the higher price eating more of the €300 budget |
| Firmware framework | ESP-IDF (C) | Arduino framework (via `Seeed_GxEPD2`) | Early bring-up/prototyping of the display driver only — not recommended for the shipped firmware since it gives less control over sleep-current tuning |
| Flight API | AeroDataBox | AviationStack | You need broader global airline-route/statistics data beyond a single airport's FIDS board, and $50+/mo is acceptable |
| Server language | Python + Pillow | Node.js + `@napi-rs/canvas` | The builder strongly prefers a JS/TS stack and is willing to re-derive the poll protocol from `docs/PROTOCOL.md` rather than adapting the reference Python server |
| Hosting | Hetzner CX22 | Fly.io | You want zero fixed monthly cost and can tolerate risk around "always reachable" (free tier can idle) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| OpenSky Network as the flight-data source | ADS-B-only; explicitly does not surface scheduled/commercial flight-timetable data, so it cannot show a flight that hasn't taken off yet — breaks the "departure board" use case | AeroDataBox (Airport FIDS) |
| FlightAware AeroAPI for a hobby budget | $200/mo minimum on the paid Standard tier — roughly 40x the monthly VPS cost for this whole project | AeroDataBox |
| A local ADS-B/SDR antenna | Already correctly excluded in PROJECT.md — scheduled-departures use case doesn't need overhead-flyover detection, and it adds RF hardware complexity for no benefit here | Public flight-data API (AeroDataBox) |
| Arduino framework for the shipped/production firmware | Loses fine-grained control over ESP32-S3 sleep-current tuning, which is the top risk factor for a battery-only device; also diverges from the ESP-IDF codebase flightportrait actually ships | ESP-IDF (C), directly or via PlatformIO's `framework = espidf` |
| A scale-to-zero / idle-capable hosting tier (e.g. bare Fly.io free tier) | Project constraint is explicitly "device should always find a reachable server" — an app that sleeps between requests can miss a device's poll window | Hetzner CX22 (always-on, ~€4.35/mo) |
| Custom BLE provisioning protocol/library | ESP-IDF already ships an audited, Security-Level-2 provisioning stack (`wifi_provisioning` + `protocomm_ble`) that flightportrait itself uses — reinventing this adds security risk for no benefit | ESP-IDF's built-in `wifi_provisioning` (BLE transport, Security 2) |

## Stack Patterns by Variant

**If prioritizing fastest path to a working prototype:**
- Start with the Arduino framework + `Seeed_GxEPD2` to get the display driver and basic rendering working, since that's Seeed's own documented demo path
- Migrate the shipped firmware to native ESP-IDF once the display pipeline is validated, to get proper sleep-current control before relying on it for real battery-life numbers

**If prioritizing hitting the €300 hardware ceiling comfortably:**
- Use the XIAO ESP32-S3 Plus + EE02 DIY kit (~€152) over the reTerminal E1004 (~€258+VAT), leaving ~€100-150 for a battery pack, enclosure materials, and shipping/customs buffer

**If the builder is already fluent in Node.js rather than Python:**
- Swap Flask/FastAPI + Pillow for Express/Fastify + `@napi-rs/canvas`, but budget extra implementation time to hand-derive the poll protocol from flightportrait's `docs/PROTOCOL.md` instead of adapting its reference server

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| ESP-IDF 5.3.x | ESP32-S3 (XIAO ESP32-S3 Plus, reTerminal E1004) | Version pinned to match flightportrait's verified development target; later 5.x releases are likely fine but haven't been specifically confirmed against the Spectra 6 dual-chip driver code |
| GxEPD2 / Seeed_GxEPD2 fork | Arduino-ESP32 core (bundled via Arduino framework or PlatformIO's `framework = arduino`) | Only relevant if using the Arduino bring-up path, not the ESP-IDF production path |
| Pillow 11.x | Python 3.9+ | No known issues at 3.12 |
| FastAPI 0.11x | Python 3.9+, Pydantic v2 | Standard current pairing as of 2026 |

## Sources

- flightportrait.com and GitHub search (websearch, MEDIUM) — protocol/architecture details, cross-checked via direct WebFetch of the repo
- AeroDataBox pricing page (aerodatabox.com/pricing, WebFetch of official page, MEDIUM-HIGH) — direct and marketplace tier pricing
- RapidAPI AeroDataBox listing (websearch, MEDIUM) — marketplace-tier corroboration
- AviationStack pricing/FAQ pages (websearch, MEDIUM)
- FlightAware AeroAPI product page (websearch, MEDIUM)
- OpenSky Network official docs (openskynetwork.github.io, websearch, MEDIUM)
- PRIM (prim.iledefrance-mobilites.fr) API catalog pages (websearch, MEDIUM — direct page fetch was blocked by a 403, so quota figures are community-sourced and should be re-verified against the account dashboard)
- Hetzner pressroom + third-party 2026 pricing roundups (websearch, MEDIUM-HIGH)
- Seeed Studio product pages for reTerminal E1004 and XIAO ePaper DIY Kit EE02 (websearch, MEDIUM)
- CNX Software / Hackster.io coverage of the XIAO ePaper DIY Kit EE02 (websearch, MEDIUM)
- GxEPD2 GitHub repo and community forum threads on Waveshare/ESP32 wiring (websearch, LOW-MEDIUM — Spectra 6 dual-chip specifics not independently confirmed)
- ESP32/ESP32-S3 deep sleep power-consumption threads (Espressif forum, esp-idf GitHub issues) (websearch, MEDIUM)
- ESP-IDF Wi-Fi provisioning docs (docs.espressif.com) (websearch, MEDIUM)
- Pillow vs Node canvas rendering comparisons (websearch, MEDIUM)

---
*Stack research for: e-ink flight/transit departure board (ESP32-S3 device + cloud VPS server)*
*Researched: 2026-08-04*
