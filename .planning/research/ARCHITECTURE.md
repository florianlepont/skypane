# Architecture Research

**Domain:** Battery-powered e-ink IoT display + polling server + external data APIs
**Researched:** 2026-08-04
**Confidence:** HIGH (device/server protocol patterns, ESP32-S3 power model) / MEDIUM (transit API specifics)

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│  DEVICE (ESP32-S3, battery)                                           │
│  ┌────────────┐   ┌───────────────┐   ┌────────────────────────────┐ │
│  │ Wake source │──▶│ State machine │──▶│ HTTPS poll client (outbound │ │
│  │ timer|button│   │ (app_main)    │   │ only, no listening socket)  │ │
│  └────────────┘   └───────┬───────┘   └──────────────┬─────────────┘ │
│                            │                          │               │
│                            ▼                          ▼               │
│                    ┌───────────────┐        ┌──────────────────────┐ │
│                    │ NVS: active   │        │ SHA-256 verify +      │ │
│                    │ view, backoff,│        │ e-ink blit (full      │ │
│                    │ image hash    │        │ refresh, 12-30s)      │ │
│                    └───────────────┘        └──────────────────────┘ │
│                            │                                          │
│                            ▼                                          │
│                    ┌───────────────┐                                  │
│                    │ Deep sleep    │  (~10 µA, ext1 GPIO armed        │
│                    │ (sleep_s from │   for button wake)               │
│                    │ server resp)  │                                  │
│                    └───────────────┘                                  │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │ HTTPS (device-initiated only)
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│  SERVER (small always-on VPS)                                         │
│  ┌────────────────────┐        ┌────────────────────────────────┐    │
│  │ Poll API            │◀──────▶│ Render cache (per view)         │    │
│  │ (device/v1/setup,   │  read  │ - latest .bin image + SHA-256   │    │
│  │  /display, /log)    │        │ - rendered_at timestamp         │    │
│  └────────────────────┘        └───────────────▲──────────────────┘    │
│                                                  │ write                │
│                    ┌─────────────────────────────┴─────────────┐      │
│                    │ Render pipeline (per view)                 │      │
│                    │ normalized data → layout → 6-color quantize│      │
│                    │ → pack to device .bin format                │      │
│                    └───────────────▲─────────────────────────────┘      │
│                                     │ normalized data                    │
│         ┌───────────────────────────┴───────────────────────────┐      │
│         │                                                        │      │
│  ┌──────┴────────┐                                    ┌──────────┴────┐│
│  │ Flight fetcher │  scheduled poll, own cadence       │ Transit fetcher││
│  │ (Orly/ORY)     │  (e.g. every 5-10 min)             │ (Orly-Ville RER)││
│  └───────┬────────┘                                    └────────┬───────┘│
│          │ HTTPS                                                │ HTTPS  │
└──────────┼───────────────────────────────────────────────────────┼───────┘
           ▼                                                       ▼
   Public flight-data API                              PRIM / Île-de-France
   (e.g. AeroDataBox, Aviationstack,                    Mobilités SIRI Lite API
   Paris Aéroport open data)                            (next-departures endpoint)
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|-------------------------|
| Device state machine | Wake dispatch, poll orchestration, backoff, view selection | ESP-IDF C, mirrors flightportrait's `app_main.c` / `state_machine.c` / `backoff.c` |
| Device poll client | Outbound-only HTTPS calls to 3 endpoints, SHA-256 verify | `api_client.c` pattern; TLS with pinned/rooted CA bundle |
| Device panel driver | Full-refresh blit of pre-packed 4bpp bitmap | `panel.c` pattern; no on-device layout/font rendering |
| Server poll API | Stateless HTTP handler serving cached renders per view | Any lightweight web framework (Flask/FastAPI, Express, Go net/http) |
| Server render cache | Holds latest rendered bitmap + hash per view, decoupled from poll requests | In-memory dict + file on disk, or SQLite row per view |
| Flight fetcher (scheduled) | Poll flight API on its own cadence, normalize, trigger re-render | Cron/APScheduler/systemd timer job, independent of transit fetcher |
| Transit fetcher (scheduled) | Poll transit API on its own (faster) cadence, normalize, trigger re-render | Same scheduler infra, separate job/interval |
| Render pipeline | Data → layout → 6-color quantized bitmap → device binary format | Pillow/node-canvas/etc. producing exact 960,000-byte packed format |

## Recommended Project Structure

```
device/                        # ESP32-S3 firmware (ESP-IDF)
├── main/
│   ├── app_main.c              # boot, wake-reason dispatch
│   ├── state_machine.c         # poll -> verify -> blit -> sleep orchestration
│   ├── api_client.c            # HTTPS client, 3 endpoints, SHA-256 verify
│   ├── panel.c                 # e-ink driver, full-refresh blit
│   ├── backoff.c               # exponential backoff (persisted in NVS)
│   ├── nvs_schema.h            # active_view, last_hash, fail_count, device token
│   └── button.c                # ext1 GPIO wake + view-toggle + force-poll flag
├── sdkconfig.defaults
└── docs/PROTOCOL.md            # device<->server contract (source of truth)

server/                        # small VPS backend
├── api/
│   └── device_routes.*         # /device/v1/{setup,display,log} — reads cache only
├── fetchers/
│   ├── flight_fetcher.*         # polls flight API on its own schedule
│   └── transit_fetcher.*        # polls PRIM/transit API on its own schedule
├── render/
│   ├── plane_view.*             # layout for flight departures
│   ├── rer_view.*               # layout for next RER trains
│   └── packer.*                 # shared: quantize to 6 colors, pack to .bin
├── cache/                       # latest per-view .bin + hash + rendered_at
├── scheduler.*                  # cron/interval registration for fetchers
└── config.*                     # API keys, station/airport IDs, cadences

companion-app/                  # v2, independent subsystem
└── ...                          # pushes short text -> becomes 3rd view/overlay
```

### Structure Rationale

- **device/ and server/ are fully independent codebases** communicating only through `docs/PROTOCOL.md` as a contract — this lets them be built, tested, and iterated in parallel (see Build Order below).
- **fetchers/ separated from render/ separated from api/** on the server so the device-facing HTTP handler never touches upstream APIs directly — it only ever reads the render cache. This is the single most important boundary in the system (see Anti-Patterns).
- **render/packer.* is shared** across both views because the device binary format (1200×1600, 4bpp packed, 6-color palette) is identical regardless of which view is being rendered — don't duplicate packing logic per view.

## Architectural Patterns

### Pattern 1: View-parameterized single poll endpoint (not two endpoints, not dual-payload)

**What:** The device tells the server which view it wants via a query parameter or header on `GET /device/v1/display` (e.g. `?view=plane|rer`), and the device — not the server — is the source of truth for "which view is currently active." The server always keeps both views freshly rendered in its cache and simply returns whichever one was requested.

**When to use:** Any time a single device displays alternate "screens" of otherwise-independent data and only ever needs one bitmap per wake.

**Trade-offs:**
- (+) Server logic stays trivial — it never needs to guess device state or push both images.
- (+) Only one ~960 KB image is downloaded per wake, not two — matters for both power and mobile-adjacent bandwidth costs.
- (+) Matches the reference protocol shape almost exactly (one extra query param on an existing endpoint) — no new endpoint, no protocol version bump needed.
- (−) Device must persist "active view" in NVS across sleep cycles and must default sensibly on first boot (recommend: plane view).
- Avoid the alternative of "server always returns both images" — doubles per-wake data transfer and TLS/download time for no benefit, since e-ink can only show one view at a time anyway.

**Example (conceptual):**
```
GET /device/v1/display?view=rer HTTP/1.1
Authorization: Bearer <token>
X-Battery-Mv: 3950
X-Wake-Reason: button        # or "timer"
```

### Pattern 2: Button wake = "same flow, forced immediate, view-switched"

**What:** A button press is not a special protocol path — it's the *same* poll flow as a scheduled wake, but with two differences: (1) it wakes the device outside the timer schedule via `ext1` GPIO interrupt, and (2) it flips `active_view` in NVS *before* calling `/display`, and sets a `force=true`/`X-Wake-Reason: button` marker so the server-side minimum-refresh-spacing logic (if any) treats it as user-initiated rather than routine.

**When to use:** Any battery device where a physical control should produce an "instant" response without disturbing the normal scheduled cadence.

**Trade-offs:**
- (+) No separate state machine branch needed on device or server — one code path, one set of tests.
- (+) Button press always concludes with a redraw (matches reference project's stated guarantee), even if delayed slightly by minimum refresh-spacing.
- (−) Must guard against rapid double-presses causing back-to-back full e-ink refreshes (~12-30 s each, real wear/power cost) — debounce in firmware and consider a minimum-refresh-spacing floor (reference project defaults to 60 s) that a button-triggered request can wait out but not bypass entirely.
- After the button-triggered poll, resume the *server-provided* `sleep_s` for the next scheduled wake — don't let the interrupt permanently alter the timer schedule.

### Pattern 3: Fetch/render decoupled from poll-serving (cache-fronted backend)

**What:** The server runs independent scheduled jobs (one per upstream API) that fetch, normalize, and render into a cache. The device-facing poll endpoint is a pure cache reader — it never calls an upstream API synchronously in response to a device request.

**When to use:** Any time device response latency must be bounded and predictable but upstream data sources have unpredictable/slow response times, rate limits, or occasional outages.

**Trade-offs:**
- (+) Poll endpoint response time is near-constant (cache read + optional file send), independent of upstream API health.
- (+) Upstream API rate limits are respected by design — call cadence is controlled centrally by the scheduler, not driven by device wake frequency (which can spike, e.g. multiple button presses).
- (+) A single upstream outage degrades gracefully — serve the last-known-good render with its `rendered_at` age, rather than failing the device poll.
- (−) Requires a staleness policy: how old is "too old" to serve (e.g. flight data > 30 min old should probably be flagged/hidden vs RER data, which is only useful if under ~2-5 min old).

## Data Flow

### Fetch/render flow (server-internal, independent of device)

```
[Flight fetcher: every 5-10 min]
    ↓
[Flight API response] → [normalize to internal schedule model]
    ↓
[plane_view render] → [6-color quantize] → [pack 4bpp .bin] → [cache: plane.bin + sha256 + rendered_at]

[Transit fetcher: every 60-90 s, independent schedule]
    ↓
[PRIM/SIRI Lite response] → [normalize to internal departure model]
    ↓
[rer_view render] → [6-color quantize] → [pack 4bpp .bin] → [cache: rer.bin + sha256 + rendered_at]
```

### Device poll flow

```
[Wake: timer or button(ext1)]
    ↓
[Read NVS: active_view, backoff state, last image hash]
    ↓
[HTTPS GET /device/v1/display?view=<active_view>]  (server reads cache only — no live API call here)
    ↓
[image_hash matches NVS?] --yes--> [skip download, go to sleep(sleep_s)]
    │no
    ↓
[Download .bin, verify SHA-256 + exact size] --fail--> [backoff, sleep]
    │pass
    ↓
[Full-refresh blit to panel] → [store new hash in NVS] → [deep sleep(sleep_s from server)]
```

### Key Data Flows

1. **Upstream-to-cache (server, scheduled):** Two independent poll loops (flight, transit) never block each other and never block the device-facing API — this is the flow that must be robust to upstream flakiness.
2. **Cache-to-device (on-demand, device-initiated):** Purely a cache read behind auth/telemetry — must stay fast (well under the device's 15-20 s request timeout) regardless of upstream state.
3. **Button-to-refresh (device-local, then device-to-server):** View switch happens locally in NVS first, then the *existing* poll flow runs immediately instead of waiting for the timer — no protocol branching required.

## Scaling Considerations

This is a single-device (or small-fleet), low-QPS system — scaling in the traditional sense is not a real concern. The more relevant axis is **request cadence vs upstream API budget**.

| Scale | Architecture Adjustments |
|-------|---------------------------|
| 1 device (v1) | Simplest possible: scheduler + in-memory/file cache + stateless poll handler on one small VPS. No queue, no DB needed beyond maybe SQLite for the cache. |
| Few devices (v2, companion app fleet) | Cache stays shared (same rendered views serve every device) — only the poll endpoint's auth/token bookkeeping needs to be per-device. Fetch/render cadence does *not* need to scale with device count, since it's decoupled from device polls. |
| Many devices / public product | At that point, split render cache into a proper KV store (Redis) and consider per-region rendering if serving multiple airports/stations — but this is far beyond current scope. |

### Scaling Priorities

1. **First real constraint: upstream API rate limits, not device load.** A departure-board use case needs data refreshed every few minutes at most — design fetch cadence around the API's free/cheap tier limits, not around device poll frequency.
2. **Second: e-ink panel wear from full refreshes.** Full refresh (no partial refresh on Spectra 6-class panels) has a real physical cost; button-mashing is the practical limit to guard, not server throughput.

## Anti-Patterns

### Anti-Pattern 1: Calling the upstream API synchronously inside the device's poll request

**What people do:** Wire the `/device/v1/display` handler directly to "fetch flight data live, render, respond" for simplicity during a prototype.

**Why it's wrong:** Upstream flight/transit APIs are outside your control — latency spikes, rate limits, or outages directly translate into device HTTPS timeouts, which trigger exponential backoff (up to 6 h per the reference model) and a frame that silently goes stale for hours. It also means every device wake (including button presses) consumes upstream API quota unpredictably.

**Do this instead:** Decouple as in Pattern 3 — scheduled background fetch/render into a cache, device poll only reads the cache.

### Anti-Pattern 2: Rendering on-device from structured JSON

**What people do:** Ship flight/RER data as JSON to the ESP32-S3 and do text layout, font rendering, and color quantization on-device to "save bandwidth."

**Why it's wrong:** ESP32-S3 has limited RAM/CPU for font rendering and layout engines; e-ink full refresh already costs 12-30 s and dominates the active-current power budget, so the incremental "savings" from not sending a pre-rendered bitmap are marginal, while the firmware complexity (font libraries, layout logic, color dithering for a 6-color Spectra panel) is substantial and duplicates work the server can do trivially with mature libraries (Pillow, node-canvas, etc.). The reference project's whole design point is "device blits, server renders."

**Do this instead:** Server pre-renders the full 1200×1600 6-color packed bitmap exactly as the reference protocol specifies; device does verify + blit only.

### Anti-Pattern 3: Letting a button press bypass or corrupt the scheduled backoff/sleep state

**What people do:** Treat button press as a totally separate code path that resets backoff counters or ignores `sleep_s` bookkeeping.

**Why it's wrong:** Creates two poll implementations to maintain and test, and can cause runaway wake cycles or backoff-state corruption if the button path forgets to persist the same NVS fields the scheduled path does.

**Do this instead:** Button press only (a) sets `active_view` and (b) triggers the *same* poll routine immediately, outside the timer; all NVS/backoff bookkeeping stays identical to the scheduled path (Pattern 2).

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|----------------------|-------|
| Public flight-data API (ORY departures) | Scheduled poll (5-10 min), server-side only | Candidates: AeroDataBox, Aviationstack, or Paris Aéroport / ADP open data — confirm actual departures-board coverage and rate limits during phase-specific research; MEDIUM confidence pending that check |
| PRIM / Île-de-France Mobilités (Orly-Ville RER) | Scheduled poll (60-90 s), server-side only | SIRI Lite "next departures" endpoint via the PRIM platform; requires an account/API key; GTFS static data updates 3x/day for schedule structure, real-time layer for live next-passage times — HIGH confidence on existence/shape, MEDIUM on exact field mapping until implementation |
| Device HTTPS poll protocol | Device-initiated only, 3 endpoints (`setup`, `display`, `log`) | Mirrors flightportrait `docs/PROTOCOL.md` almost verbatim — HIGH confidence, direct source |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|----------------|-------|
| Device firmware ↔ Server | HTTPS, device-initiated poll only, no open ports on device | Contract lives in a shared `PROTOCOL.md`; this is the only coupling between the two subsystems — enables fully parallel build tracks |
| Server: fetchers ↔ render cache | In-process function call / shared cache store, one-way write | Fetchers never talk to the API handler directly |
| Server: API handler ↔ render cache | Read-only | Never triggers a fetch; if cache is cold/stale beyond threshold, serve stale data with a flag or a "no data" fallback image rather than blocking |
| Companion app (v2) ↔ Server | New push-style endpoint or a 3rd cached "message" view, same cache-fronted pattern | Should reuse the same device-poll-reads-cache pattern — app writes a short-lived message into the cache, device sees it on next poll like any other view; do not create a fundamentally different (e.g. push-to-device) mechanism, since device never accepts inbound connections |

## Sources

- [flightportrait/frame — docs/PROTOCOL.md](https://github.com/flightportrait/frame/blob/main/docs/PROTOCOL.md) — HIGH confidence, direct source, protocol shape, backoff formula, SHA-256/size verification, sleep_s semantics, refresh spacing
- [flightportrait/frame — repo overview](https://github.com/flightportrait/frame) — HIGH confidence, direct source, firmware module layout, server reference implementation (`byos_server.py`), repo structure
- [Espressif ESP-IDF Sleep Modes documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/sleep_modes.html) — HIGH confidence, official docs, deep sleep + ext0/ext1 wake current draw
- [Random Nerd Tutorials — ESP32 Deep Sleep Wake Sources](https://randomnerdtutorials.com/esp32-deep-sleep-arduino-ide-wake-up-sources/) — MEDIUM confidence, community reference, corroborates ext1 multi-GPIO wake pattern
- [PRIM (Île-de-France Mobilités) — Next Departures API catalog](https://prim.iledefrance-mobilites.fr/en/apis/idfm-ivtr-requete_globale) — MEDIUM confidence, official platform docs, SIRI Lite format, real-time next-departures scope
- [PRIM — GTFS Datahub dataset](https://prim.iledefrance-mobilites.fr/en/jeux-de-donnees/offre-horaires-tc-gtfs-idfm) — MEDIUM confidence, official, static schedule data cadence (3x/day)
- General e-ink client/server rendering split rationale (patent literature on rasterized-content delivery to display clients) — LOW/MEDIUM confidence, corroborating but non-primary source; the flightportrait reference project itself is the primary evidence for this architecture choice

---
*Architecture research for: battery-powered e-ink departure board (ESP32-S3 + cloud render server)*
*Researched: 2026-08-04*
