# Pitfalls Research

**Domain:** Battery-powered e-ink IoT "departure board" (ESP32-S3-class device + Spectra 6 color e-paper, poll-only server architecture, French transit + flight data)
**Researched:** 2026-08-04
**Confidence:** MEDIUM (primary source: flightportrait/frame's own `docs/PROTOCOL.md` and flightportrait.com, fetched directly — treat as the strongest source available; most other findings are cross-checked web search on hardware/API vendor pages and community forums, individually LOW confidence but corroborated across 2+ independent sources where noted)

## Critical Pitfalls

### Pitfall 1: Battery life is dominated by radio wake time, not sleep current — and naive estimates are 5-10x optimistic

**What goes wrong:**
Teams calculate battery life from the deep-sleep datasheet current alone (ESP32 deep sleep is ~10µA) and conclude a small battery will last "over 11 years." In reality, active WiFi (join network + DNS + TLS handshake + HTTP request/response) draws 80–240mA, and that active window — not sleep current — dominates the energy budget once you wake more than a few times a day. Deep sleep is typically under 2% of total consumption in a periodic-poll design; battery life scales almost linearly with wake frequency, not with sleep current. Real deployments with an EPD (e-ink) refresh added on top land in the 40–150 day range on a 3000–5000mAh cell at hourly-ish update cadences, not "months to years."

**Why it happens:**
Datasheet current figures are cited without accounting for: WiFi association time (can be 1-3s before a single packet moves), TLS handshake cost (worse without session resumption), DNS lookup, and the e-ink refresh itself (a multi-second, higher-current operation, see Pitfall 2). Each of these adds tens to hundreds of milliamp-seconds per wake that deep-sleep-only math ignores entirely.

**How to avoid:**
- Budget power in mAh **per wake cycle**, not just µA at rest: WiFi connect + TLS + HTTP + (optional) e-ink refresh + reconnect overhead, measured on the actual hardware (a $20 USB power meter or INA219/INA226 inline sensor pays for itself immediately).
- Enable TLS session resumption / cached session tickets to cut handshake cost on repeat wakes.
- Pre-compute everything possible before turning the radio on; use a strict wake → transmit → sleep pattern.
- Pick the wake interval as the dominant lever: the flightportrait reference design's own default minimum refresh spacing is 60s per wake, but its steady-state schedule is a much longer interval (poll cadence, not display refresh cadence) — for this project's "check before I leave the house" use case, a poll interval in the 15–30 minute range (not every minute) is the right order of magnitude, with the physical button providing on-demand refresh for the "I need this right now" case.
- Size the battery from a measured mAh/wake number × wakes/day × target days, with ≥20% margin for LiPo usable-capacity derating (4.2V→3.4V cutoff plus regulator losses is roughly 80% usable).

**Warning signs:** Any battery-life claim derived only from a deep-sleep datasheet number; no bench measurement of an actual wake-to-sleep cycle; wake interval chosen without a corresponding mAh/day budget.

**Phase to address:** Early hardware bring-up / power-budget phase, before committing to a battery capacity or a final wake-interval default — this is a foundational constraint that shapes UX (Pitfall 6) and hardware selection.

---

### Pitfall 2: E-ink refresh current spikes cause brownouts, and refresh itself is a battery cost people forget to budget

**What goes wrong:**
E-ink panels draw negligible current while holding a static image, but the refresh operation pulls a significant current spike (full-color refresh on a large panel like Spectra 6 is slower and higher-draw than monochrome, since each color plane redraws independently). On weak power rails — small batteries, thin traces, missing decoupling — this spike causes brownout resets during the refresh itself, which is especially bad because a brownout mid-refresh can leave the panel in a half-updated, visually broken state. Community sources on this class of failure describe it as very common in DIY EPD builds.

**Why it happens:** Reference designs and driver boards work fine on a bench power supply, then fail intermittently on battery once trace/regulator margins get tight — a "works in the demo, fails randomly in the field" pattern. Insufficient bulk capacitance near the panel's VCC pin, and Li-ion/LiPo cells that sag under load (especially as they discharge below ~3.5V), make this worse over the battery's life, not just at day one.

**How to avoid:**
- Use a driver board/regulator combination sized for the panel's documented peak refresh current, not just its average.
- Add bulk decoupling (electrolytic + ceramic) close to the panel's power pins per the panel vendor's guidance; use adequately wide VCC/GND traces or a dedicated power plane.
- Test refresh reliability at the battery's *low* end of charge (e.g. 3.4-3.5V), not just when freshly charged — this is the condition most likely to brown out.
- Include a "refresh confirmed complete" check in firmware so a partial/failed refresh due to brownout is detected and retried on next wake rather than silently leaving a corrupted image.

**Warning signs:** Refresh works reliably on USB/bench power but glitches intermittently on battery; failures cluster as the battery discharges rather than being uniformly random; occasional half-rendered/torn images reported after weeks of otherwise normal operation.

**Phase to address:** Hardware bring-up / display-driver integration phase — verify under battery load and low-charge conditions, not just bench power, before considering the display pipeline done.

---

### Pitfall 3: Color e-ink ghosting and slow, visible refreshes have direct UX consequences for a "glance and go" device

**What goes wrong:**
Two related issues: (1) partial refreshes accumulate ghosting (faint remnants of prior content) over repeated updates — common guidance is a full refresh is needed roughly every 5-10 partial refreshes to clear it — and color panels show this more visibly than monochrome because the color layer is lower-resolution and more complex to drive; (2) a full refresh on a panel this size takes on the order of 12-30 seconds with a visible flash as the pigments rearrange. For a device whose entire value proposition is "glance at the wall, know if you'll make the train," a many-second flashing refresh on every button press (view switch / on-demand poll) is a jarring, slow interaction if not designed around explicitly.

**Why it happens:** Refresh time and ghosting behavior are treated as an implementation detail rather than a UX constraint, discovered only once real hardware is in hand — often after committing to an interaction model (e.g. "button press = instant view swap") that the panel physically cannot deliver.

**How to avoid:**
- Design the button-press interaction around the actual refresh latency from day one: e.g., an immediate cheap visual acknowledgment (if feasible) or explicit expectation-setting (this is inherent to e-ink and shouldn't be fought), rather than assuming near-instant feedback.
- Track a refresh counter in firmware/NVS and force a full refresh after N partial refreshes (or on every wake, if partial refresh isn't used at all — full-refresh-only is a legitimate simplification for a low-frequency-update device like this one, trading a few extra seconds for zero ghosting-management complexity).
- Decide early whether this device even needs partial refresh — given a 15-30 minute poll interval, full refresh on every update may be simpler and more robust than managing a partial-refresh ghosting budget for marginal speed gain.
- Test dithered color rendering (6-color native palette, dithering needed for anything beyond flat colors/text) against real flight-board-style layouts before finalizing the image renderer on the server.

**Warning signs:** Visible shadow/ghost of previous screen content behind new content after several updates; user-perceived "the button doesn't do anything" during the multi-second refresh window; color banding/incorrect colors in rendered images that looked fine in a design mockup but were never tested against real dithering output.

**Phase to address:** Display rendering/firmware phase (refresh strategy decision) and UX/interaction-design phase (button press feedback model) — these should be decided together since the panel's physical refresh time constrains the button UX.

---

### Pitfall 4: Free/cheap flight-data APIs have rate limits and staleness windows that don't match a "will I make my train" use case

**What goes wrong:**
Cheap/free flight-data tiers (e.g., aviationstack free tier: 100 requests/month, and its scheduling endpoints rate-limited to 1 request/minute even on paid plans; general pattern across providers) are not built for frequent single-airport polling. Combined with a public VPS server architecture (server polls the airport source, not the device polling the airport source directly), staleness compounds: if the server's own poll of the flight API is infrequent to conserve API quota, a flight that gets delayed, gate-changed, or cancelled after the last server-side fetch will show stale information on the device until the next server poll — which the device then displays as if current. For a single small airport (Orly) with a limited number of daily departures, this is more forgiving than a major hub, but the failure mode (showing a cancelled/departed flight as upcoming) directly undermines the "will I make it" value proposition.

**Why it happens:** Rate limits are budgeted around request count without separately budgeting for *data freshness* — the two are related but distinct constraints, and a demo built during a burst of testing (frequent manual polls) doesn't reveal how stale the data gets under the actual production polling cadence.

**How to avoid:**
- Choose a flight-data provider based on real update latency for schedule/status changes (some vendors advertise 30-60s propagation from airline-reported changes; verify for the specific provider chosen, don't take marketing claims at face value), not just on price.
- Cache flight data server-side with an explicit staleness budget (e.g., "never show flight data older than N minutes"), and separately track API quota consumption so the server backs off gracefully (wider poll interval, not silent failure) as it approaches rate limits.
- Design the rendered image (or a simple staleness indicator) to reflect data age or at minimum ensure the render loop refuses to publish images built from data older than the staleness budget — this keeps a "wrong" answer from ever reaching the device even if the API itself lags.
- Prefer providers/endpoints scoped to real-time status (not just schedule/timetable) for the imminent-departure window that matters for this device's use case; timetable endpoints are typically the most rate-limited and least real-time.

**Warning signs:** Server-side cache/poll interval was chosen purely to stay under a quota number, without checking whether that interval is fast enough relative to how quickly gate/delay/cancellation info can change; no "data age" concept anywhere in the render pipeline; device has shown a flight as on-time when it had, in fact, already been cancelled or departed.

**Phase to address:** Server/data-pipeline phase — flight API selection and server polling/caching strategy should be designed together with an explicit staleness SLA, not chosen independently.

---

### Pitfall 5: French transit (IDFM/PRIM) API quotas are easy to blow through with naive polling, and quotas have changed on short notice

**What goes wrong:**
IDFM's PRIM platform quota has reportedly been reduced for new/default API users (community reports cite a much lower default quota than older documentation implied, with users needing to actively request higher quota via a "My Consumption" self-service page). A polling pattern that seems modest per-device (e.g., a fixed interval regardless of actual demand) can multiply out fast: one documented case saw ~2 requests every 3 minutes per polling instance blow through a reduced daily quota with only a handful of tracked stations. For this project, if the server polls RER Orly-Ville on a fixed short interval independent of whether any device is actually awake/asking, the same trap applies.

**Why it happens:** Quota assumptions get hardcoded from initial documentation/testing and never revisited; polling cadence is chosen for "freshness" without checking it against the account's actual quota ceiling, and PRIM's real-time layer (SIRI Lite based, on Navitia/SNCF-derived tech) is a different quota bucket than the static schedule (GTFS/NeTEx) data, which is easy to conflate.

**How to avoid:**
- Only poll the RER real-time endpoint from the server when actually needed (e.g., server-side cache with a short TTL matched to actual device wake frequency, not a fixed independent timer running regardless of device activity).
- Register for and monitor an IDFM/PRIM developer account's quota dashboard from day one; treat the quota as a hard constraint in the server's polling design, not an afterthought.
- Build quota exhaustion into the error-handling design explicitly (see Pitfall 6) — decide upfront what the device shows when the server can't get fresh RER data because the day's quota is spent, rather than discovering this live.
- Keep static schedule data (which line runs, station structure) separately cached/refreshed rarely, and only hit the real-time layer for "next departure" queries, to avoid conflating the two quota pools.

**Warning signs:** No dashboard/alerting on remaining API quota; poll interval was copied from a tutorial/example rather than derived from the account's actual quota ÷ desired freshness; quota exhaustion has no defined behavior (page shows a raw error, blank data, or an old cached value indistinguishable from fresh data).

**Phase to address:** Server/data-pipeline phase, alongside the flight-API integration (Pitfall 4) — both external data sources need the same discipline: explicit staleness budget, quota monitoring, and graceful degradation.

---

### Pitfall 6: Real-time transit disruptions are frequently absent or delayed in the API feed relative to reality

**What goes wrong:**
RER/SNCF/RATP disruption information (service alerts, line closures, unscheduled gaps) is served through a separate "traffic info" layer from the schedule/next-departure layer, and disruption propagation into the real-time feed can lag behind the disruption itself or be reported at a route/line level that doesn't clearly translate to "will the next train shown actually come." A device showing "next RER in 4 minutes" sourced from schedule data, with no disruption cross-check, can confidently show an on-time departure that then simply doesn't happen.

**Why it happens:** It's easy to integrate only the "next departures" endpoint (the immediately useful data) and treat disruption/traffic-info as a nice-to-have added later, or never, because it's a separate API surface with separate data modeling.

**How to avoid:**
- Treat disruption/traffic info as a first-class input to the RER view render, not an optional layer — at minimum, surface a "service disrupted" indicator on the device when the line-level traffic info API reports an active disruption for the relevant line, even if the specific next-departure time still looks normal.
- Accept and design for the fact that "no disruption reported" is not the same guarantee as "will definitely run" — avoid implying more certainty than the data supports (see UX Pitfalls below).

**Warning signs:** No traffic-info/disruption API call anywhere in the render pipeline; product copy/design implies certainty ("Next RER: 4 min") without any disruption caveat path.

**Phase to address:** Server/data-pipeline phase (RER view) — decide the disruption-info integration alongside the base next-departures integration, not as a later addition.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Full-refresh-only (skip partial refresh entirely) | Simpler firmware, zero ghosting-management code | Slightly longer per-wake refresh time, marginally more battery per refresh | Acceptable for v1 given a 15-30 min+ poll interval — the battery/UX cost of partial refresh complexity likely isn't worth it at this update cadence |
| Hardcoded fixed poll interval (no server-side backoff) | Faster to ship | Wastes API quota and battery when nothing has changed; no graceful degradation under API outages | Never beyond an early prototype — flightportrait's own reference design treats exponential backoff as core, not optional |
| No data-staleness check before rendering an image | Simpler server code | Device can display confidently wrong information (departed/cancelled flight, disrupted line) as if current | Never — this directly undermines the core value proposition |
| Self-signed/no TLS verification during early dev | Faster local testing against a dev server | Ships insecure by accident, or requires a separate "prod" auth path that's never tested until launch | Only behind an explicit build-time flag that cannot ship in a release firmware build |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| Flight data API (aviationstack-class free/cheap tier) | Polling schedule/timetable endpoints at the same low limit as status endpoints, then hitting rate limits mid-development | Separate real-time-status calls (needed frequently) from schedule/timetable calls (needed rarely); budget each against its own limit |
| IDFM/PRIM (RER real-time) | Fixed polling interval independent of device wake cadence, ignoring quota dashboard | Server-side cache with TTL tied to actual device polling need; monitor quota, back off automatically as it's consumed |
| flightportrait-style poll protocol (device → server) | Treating the 3-endpoint poll protocol as a place to bolt on ad hoc extra fields without keeping strict backoff/verification semantics | Reuse the reference protocol's exponential backoff, SHA-256 + exact-size image verification, and min-refresh-spacing guardrails rather than reinventing simpler-but-weaker versions |
| E-ink display driver board | Assuming a driver board that works on USB power will work identically on battery | Bench-test refresh reliability specifically on battery, at low state of charge, before finalizing driver board choice |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Wake interval chosen for "freshness" without a power budget | Battery drains faster than expected once out of the lab | Derive wake interval from measured mAh/wake × target battery life, not from a "feels responsive" guess | Becomes visible within the first 1-2 weeks of real battery-only operation |
| Fixed-interval server-side polling of external APIs regardless of device activity | API quota exhausted well before month-end | Cache with TTL matched to device polling need; poll externally only when a device wake actually needs fresh data | Breaks as soon as the account's quota is smaller than assumed, or usage grows past a single test device |
| No image-render staleness gate | Device shows outdated flight/RER info with no way to tell it's outdated | Explicit "max data age" check before an image is published to the poll endpoint | Breaks silently — nothing crashes, the device just becomes quietly wrong, often discovered only when a user acts on bad info |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Skipping image hash/size verification on the device (trusting the HTTPS channel alone) | A compromised/MITM'd CDN, misconfigured server, or transport downgrade could deliver a corrupted or spoofed image the device blits without checking | Verify SHA-256 (and exact expected size) of every downloaded image before display, exactly as flightportrait's protocol does — treat any mismatch as a failed wake, not a partial success |
| Allowing plain HTTP fallback "just for local testing" to leak into shippable firmware | Bearer token and data travel in cleartext if that code path is ever reachable in production | Compile-time-enforce strict HTTPS against a public CA bundle for release builds; keep any HTTP dev path behind a flag that cannot be present in a release image |
| Logging sensitive material (tokens, pairing nonces, provisioning secrets) for debugging | Log exfiltration (device compromise, or debug logs shipped somewhere) leaks credentials that grant control of the device's data feed | Never log bearer tokens, QR/provisioning payloads, or signing material; wipe temporary buffers holding this data after use |
| No token rotation on re-provisioning / factory reset | A previously-provisioned party (e.g., after resale, or after a lost/returned unit) retains a working token indefinitely | Rotate the bearer token server-side on every re-setup for a given device identity, immediately invalidating the old one — mirrors flightportrait's "re-setup is a factory reset server-side too" design |
| Long-lived, hardcoded root CA trust with no update path | A root CA rotation/expiration (this has happened industry-wide, e.g. AddTrust External CA Root in 2020) silently breaks all HTTPS connectivity on deployed devices with no user-visible explanation | Ship firmware with a CA bundle that can be updated via the same OTA mechanism as firmware; don't assume a single embedded root will outlive the device's field life without a way to refresh it |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Implying real-time certainty ("Next RER: 4 min") when the underlying data is schedule-based or disruption info is stale/missing | User makes a "will I make it" decision on data that's confidently wrong, undermining the core value proposition | Distinguish scheduled vs. real-time-confirmed data visually if the source allows it; surface disruption state explicitly rather than omitting it when unknown |
| No visible indication of *when* the shown data was last refreshed | User can't tell whether they're looking at current info or an hour-old cached image (especially relevant given a 15-30 min+ poll interval) | Render a small "as of HH:MM" timestamp into the image itself — cheap to add, directly addresses the staleness-trust problem inherent to a periodic-poll device |
| Treating the multi-second refresh flash as a bug to hide rather than an expected interaction cost | Users perceive the button as unresponsive or broken during refresh | Set expectations in physical/product design (e.g., a natural pause before the display settles) rather than trying to fight the panel's inherent refresh time |
| No behavior defined for "server unreachable" or "no data available" | Device either shows a broken/blank render or silently keeps showing arbitrarily old data with no distinction from "fresh" | Explicit last-resort screen or overlay (e.g., a small persistent "offline since HH:MM" indicator) distinct from the normal display, following the flightportrait pattern of treating a failed wake as retry-with-backoff rather than blitting a broken image |
| Assuming e-ink "holds image with no power" means an old image is a safe fallback | A confidently-wrong stale image (e.g., a flight shown as on-time when it already departed) sitting on the wall indefinitely because the server has been down for hours is worse than a visible "no data" state | Once staleness exceeds a defined threshold, actively render and push a "data unavailable / stale" state rather than passively leaving the last successful render up forever |

## "Looks Done But Isn't" Checklist

- [ ] **Battery life claim:** Often based on deep-sleep datasheet current alone — verify with a bench-measured mAh/wake-cycle figure × intended wake frequency × real usable battery capacity (not nameplate mAh).
- [ ] **E-ink refresh reliability:** Often only tested on bench/USB power — verify refresh succeeds reliably at low battery state of charge, not just at full charge.
- [ ] **Flight/RER data freshness:** Often only tested during active development (frequent manual polling) — verify actual staleness under the real production server-poll interval and API quota constraints.
- [ ] **Error/offline state:** Often entirely unimplemented in early builds ("happy path only") — verify the device has a defined, tested behavior for: server unreachable, API data stale beyond threshold, image hash mismatch, and OTA failure, not just the successful-poll path.
- [ ] **Security of the poll protocol:** Often "HTTPS is enough" — verify image hash/size verification, token rotation on re-provisioning, and that no dev-mode HTTP/plaintext path can reach a release build.
- [ ] **API quota headroom:** Often chosen once during setup and never re-verified — verify the chosen poll intervals stay comfortably under both the flight-data API's and IDFM/PRIM's quotas at intended device-fleet scale (even a fleet of 1, plus dev/test traffic).

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|------------------|
| Battery life far short of expectations after shipping v1 | MEDIUM | Re-measure actual mAh/wake on hardware; lengthen wake interval (with UX tradeoff); consider a larger battery within the €300 budget ceiling before considering solar (already deferred by design) |
| Brownout/corrupted refresh discovered after battery-only field use | MEDIUM | Add/upgrade decoupling capacitance near panel VCC; verify with load testing at low charge; add a firmware refresh-completion check with retry |
| Flight/RER data staleness causing visibly wrong info | LOW-MEDIUM | Add a data-age gate to the render pipeline and an "as of" timestamp to the image; tighten server poll interval within quota limits |
| API quota exhausted mid-month (flight or transit API) | LOW | Implement/adjust server-side caching TTL and backoff; if persistent, evaluate a paid tier for the specific rate-limited endpoint actually needed |
| Discovered missing image-hash verification or plaintext fallback path post-launch | MEDIUM-HIGH | Firmware update (OTA) to add verification; if OTA channel itself was affected, may require physical/USB recovery — underscores why this must be right before first ship |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Battery life estimation gap (Pitfall 1) | Power-budget / hardware bring-up phase | Bench-measured mAh/wake-cycle number exists and battery capacity is sized from it, not from datasheet sleep current alone |
| E-ink refresh brownout risk (Pitfall 2) | Display-driver integration phase | Refresh reliability verified under battery power at low state of charge, not just bench/USB power |
| Ghosting / refresh-latency UX (Pitfall 3) | Display rendering + interaction-design phase | Refresh strategy (full-only vs. partial+periodic-full) decided explicitly; button-press UX designed around real refresh latency, not assumed near-instant response |
| Flight-data staleness/rate limits (Pitfall 4) | Server/data-pipeline phase (flight view) | Explicit staleness budget enforced before image publish; provider chosen against real update-latency, not just price |
| IDFM/PRIM quota exhaustion (Pitfall 5) | Server/data-pipeline phase (RER view) | Server-side caching TTL tied to device polling need; quota monitored/alerted, not assumed |
| Disruption info gaps (Pitfall 6) | Server/data-pipeline phase (RER view) | Disruption/traffic-info API integrated alongside next-departures, not deferred indefinitely |
| Security of poll-only protocol | Device-server protocol design phase | Image hash+size verification, token rotation, HTTPS-only release builds, no sensitive-data logging — all present before first hardware ship |
| "Looks done, breaks in production" gaps | Cuts across all phases; explicit hardening pass before any unattended multi-month deployment | Defined, tested behavior exists for: unreachable server, stale-beyond-threshold data, failed image verification, and failed OTA — not just the happy path |

## Sources

- flightportrait/frame `docs/PROTOCOL.md` (GitHub, fetched directly) — primary source for the reference project's own security model, backoff, verification, and OTA design. https://github.com/flightportrait/frame/blob/main/docs/PROTOCOL.md
- flightportrait.com (product site) — corroborates poll-only/no-incoming-connections design and general battery-life framing. https://flightportrait.com/
- ESP32 deep sleep / power consumption community references (Zbotic, deepbluembedded, lastminuteengineers) — cross-checked across multiple independent sources for deep-sleep current and active-WiFi current figures.
- Inkplate 13SPECTRA (Soldered/Crowd Supply, CNX Software) — real-world battery-life data point (40-50 days at hourly full-refresh) for a comparable ESP32-S3 + Spectra 6 panel combination.
- E-ink ghosting/refresh-cadence guidance (Zbotic, Geniatech, peterhinch/micropython-epaper GHOSTING.md, community forum discussion) — cross-checked full-refresh-every-5-to-10-partial-refreshes guidance.
- E Ink Spectra 6 dithering (Adafruit blog / myembeddedstuff.com) — 6-color native palette and dithering-to-13-colors technique.
- aviationstack pricing/FAQ/Trustpilot — free-tier limits (100 req/month, 1 req/min on schedule endpoints) and accuracy complaints (Trustpilot "Poor" rating), cross-checked across vendor docs and a third-party comparison (thunderbit.com).
- FlightAware AeroAPI commercial pricing page — per-query cost reference for a paid-tier alternative.
- IDFM/PRIM official docs (prim.iledefrance-mobilites.fr) and Home Assistant France community forum thread on quota exhaustion — cross-checked official quota documentation against a real-world quota-exhaustion report.
- General IoT root-CA-expiration incident reporting (The Register/2020 AddTrust root expiry; ssl2buy.com) — cross-checked industry-wide precedent for embedded long-lived CA trust failures.
- ESP-IDF OTA / rollback documentation (Espressif docs, circuitlabs.net, makergearlab.com) — dual-partition rollback pattern cross-checked against flightportrait's own described OTA gating (battery threshold, staged rollout, opt-out).

---
*Pitfalls research for: Battery-powered e-ink departure-board frame (ESP32-S3 + Spectra 6, poll-only architecture, flight + RER data)*
*Researched: 2026-08-04*
