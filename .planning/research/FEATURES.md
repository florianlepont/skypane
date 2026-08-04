# Feature Research

**Domain:** Battery-powered e-ink departure board / ambient smart frame (flight + transit info)
**Researched:** 2026-08-04
**Confidence:** MEDIUM (cross-checked web sources on RATP/SIEL, airport FIDS standards, TRMNL, ESP32 power patterns, FlightPortrait's own marketing; no primary vendor docs or code inspected — treat exact numeric claims like battery-life figures as directional, not guaranteed)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unreliable for a daily-glance tool.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Flight number + destination on plane view | Every real-world FIDS (airport board) and consumer flight tracker leads with these two fields — without them a departure entry is unidentifiable | LOW | ORY departures API gives IATA flight number + destination airport/city name directly |
| Scheduled departure time | Baseline field on every airport board; without it "next flights" has no ordering the user trusts | LOW | Sort list by this field |
| Delay / status indicator (on-time, delayed, cancelled, boarding) | Real FIDS boards always separate "scheduled" from "estimated/actual" and show status text — this is the single most-glanced-at field at an airport ("am I delayed?") | MEDIUM | Needs estimated/actual time from API, not just schedule; delta between scheduled and estimated is the "delay" the user cares about |
| RER line + destination + minutes-until-departure | SIEL (RATP's real platform display system) is the direct UX precedent — riders orient by line + destination + countdown, not by clock time | LOW-MEDIUM | RATP open data (`prim.iledefrance-mobilites.fr`) exposes next-departure times; convert absolute time → "in N min" at render time |
| Physical button that switches view AND forces a fresh poll | Explicit MVP requirement; matches TRMNL's own "button = refresh + advance" precedent, so it's a well-worn interaction users already understand from that product category | LOW-MEDIUM | Button on ESP32 wakes device from deep sleep, polls server, server must actually re-fetch (not serve a stale cached image) or the "genuinely useful" value proposition breaks |
| Clear "data as of HH:MM" / freshness indicator | Because the device polls on a schedule (not live-streaming), a stale board with no timestamp is actively misleading for a "will I make my train" decision | LOW | One small line of text on the rendered image; airport/RATP boards are always live so they don't need this, but a poll-based ambient device does |
| Wake → poll → display → deep-sleep cycle with backoff | Direct requirement from the flightportrait reference architecture; this is what makes multi-month battery life possible at all | HIGH | Already scoped as an explicit requirement; complexity lives in firmware, not in "features" per se |
| Graceful "no data" / server unreachable state | Devices that poll over WiFi will occasionally fail to reach the server (WiFi drop, VPS blip); silently showing stale data without indication erodes trust fast | LOW-MEDIUM | Show last-known-good data with a visibly stale timestamp, or a small "couldn't refresh" glyph — never a blank/broken screen |
| Legible at-a-glance typography sized for the viewing distance | This is a wall/desk object glanced at from a few feet away, not a phone screen read up close — real departure boards use very large, high-contrast type for exactly this reason | LOW | Design decision more than a "feature," but it gates whether the device is actually useful vs decorative |

### Differentiators (Competitive Advantage)

Features that set the product apart from generic e-ink dashboards (TRMNL-style) or from FlightPortrait. Not required, but align tightly with the stated Core Value ("tells you whether you'll make the next RER").

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "Will I make it?" framing — combine next-RER countdown with an implicit walk/prep buffer | This is the actual daily decision the user described in PROJECT.md motivation, not just "list of times" — a highlighted "leave by" cue is more useful than a raw timetable | LOW-MEDIUM | Pure render-layer logic on the server (fixed walk-time offset), no new data source needed; big UX win for little engineering cost |
| Disruption/incident banner on RER view (mirroring SIEL's yellow banner) | RATP's own SIEL system treats disruption messaging as a first-class element, not an afterthought — matching that convention makes the transit view feel authentically "real departure board," not a toy | MEDIUM | RATP open data includes traffic/disruption info feeds separate from next-departure feeds; only worth the API-integration cost if disruptions are common enough on this RER line to matter |
| Color use for status/delay severity (e.g., E Ink Spectra 6 color) | Reference hardware (13.3" Spectra 6) supports color — a red/amber accent on a delayed or cancelled flight, or a red RER disruption banner, reads instantly at a glance the way monochrome text can't | LOW | Already have color-capable hardware per PROJECT.md reference design; just a rendering choice, no new engineering |
| Per-view independent poll/backoff state | Only the currently-displayed view needs fresh data; when the device wakes for a scheduled flight-view refresh, don't also force an RER fetch (or vice versa) | MEDIUM | Saves server load and keeps device power budget tight; the button-press view-switch is the one place a fresh poll for the *other* view is deliberately triggered |
| Companion-app pushed message overlay (v2) | Turns the frame from read-only signage into a two-way ambient object (e.g., "running 5 min late" note to household) — genuinely differentiates from every departure-board clone | HIGH | Already scoped as v2/later; requires the server to accept authenticated pushes and the device's poll protocol to surface a "message pending" state — significant addition, correctly deferred |
| Ambient-first visual design (paper-like typography/layout, no chrome, no UI decoration) | This is the single biggest differentiator vs. generic "gadget" IoT dashboards — FlightPortrait's whole positioning is "reads as paper, not a screen"; matching that bar is what keeps this from looking like a Raspberry Pi project stuck to the wall | MEDIUM | Design/layout work, not code complexity — treat as a design requirement, not an engineering one |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this specific "ambient object first, gadget never" device.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Live/streaming updates (constant refresh, "always current to the second") | Feels more "real-time" and impressive | Kills battery life (defeats the entire wake/poll/deep-sleep architecture), and forces frequent full e-ink refreshes which cause visible flash/ghosting-cleanup cycles — the opposite of calm ambient art | Scheduled poll + backoff (already scoped) + button-triggered on-demand refresh for the moment it's actually needed |
| Partial-refresh-only updates to avoid the visible flash | Full refresh flash looks "jarring" for a wall-art object | E-ink accumulates ghosting without periodic full refreshes; skipping them degrades image quality and eventually looks worse, not calmer, than an occasional clean flash | Full refresh on every scheduled wake (which is infrequent by design — hours apart), so the flash itself becomes a rare, expected "the board just updated" cue rather than a jarring frequent event |
| Status LEDs / blinking indicators for "updating," "low battery," "WiFi connected" etc. | Feels like useful diagnostic feedback, common in IoT gear | Directly conflicts with the "ambient art, not obviously a gadget" goal — any light source on a wall-mounted piece (especially anywhere near a bedroom/living space) reads as tech, not art, and is exactly the kind of thing PROJECT.md explicitly wants to avoid | Communicate state entirely through the e-ink content itself (freshness timestamp, "couldn't refresh" glyph on the image) — no separate light source at all |
| On-device settings UI / multi-button menu navigation | Feels flexible — configure refresh interval, add more views, etc. on-device | Adds visible "chrome" (menus, icons, nav affordances) to what should read as printed information; also complicates a single-button interaction that's meant to be dead simple | Push all configuration to the server/companion app (v2); the physical device keeps exactly one interaction: press button → switch view + refresh |
| Gate numbers / detailed airport-operations fields (terminal, check-in desk, baggage belt) | Real FIDS boards show these, so it "feels complete" to include them | ORY departures aren't something the household is walking through security for — gate/terminal is operationally useful to a *traveler at the airport*, not to someone glancing at a wall in their home deciding whether to leave for the RER; adds visual clutter for zero decision value in this use case | Show only decision-relevant fields: flight #, destination, scheduled/estimated time, delay/cancelled status. Drop gate/terminal/check-in entirely |
| Push notifications / alerts (buzz phone when a flight is delayed) | Feels "smart," proactive | This is an ambient *glance* device by design — introducing push/alerting turns it into an attention-demanding gadget and duplicates what a phone app already does well; also out of scope (no phone app until v2, and even then it's push-to-frame, not frame-to-phone) | Keep it purely pull/glance-based: the information is there when you look, and says nothing when you don't |
| Animations / transitions between views | Feels more polished, "app-like" | E-ink can't do smooth animation cheaply, and any attempt reads as a slideshow gadget rather than as art; also burns power redrawing | Instant cut on button press (single refresh cycle for the new view) — matches how a printed sign "changes" (it doesn't, until someone swaps it) |
| Weather / news / other TRMNL-style bolt-on widgets alongside flights/RER | TRMNL-class devices thrive on "one display, many plugins"; tempting to add value | Dilutes the single clear purpose stated in PROJECT.md's Core Value ("will I make the next RER") and turns a focused tool into a generic dashboard, the exact category this project is deliberately differentiating from | Stay two-view only (plane, RER) for v1; if more views are wanted later, treat each as a deliberate, evaluated addition, not a default "why not" |

## Feature Dependencies

```
Wake/poll/deep-sleep architecture (already required)
    └──requires──> Server poll protocol (3-endpoint HTTPS, per flightportrait reference)
                       └──requires──> Server-side data fetch (ORY flight API + RATP RER API)

Physical button (view switch + forced poll)
    └──requires──> Wake/poll/deep-sleep architecture (button-triggered wake is a variant of the scheduled wake)
    └──requires──> Per-view poll/backoff state (so a button press only re-fetches the relevant view)

Delay/status indicator (plane view)
    └──requires──> Scheduled time AND estimated/actual time both present in the flight data source
    └──enhances──> "Will I make it?" framing differentiator

Disruption banner (RER view)
    └──requires──> RATP disruption/traffic data feed (separate from next-departure feed)

Color-coded delay/disruption severity
    └──enhances──> Delay/status indicator
    └──enhances──> Disruption banner
    └──requires──> Color-capable hardware (already selected: E Ink Spectra 6)

Companion app push message (v2)
    └──requires──> Server accepts authenticated inbound pushes
    └──requires──> Device poll protocol surfaces a "message pending" flag
    └──conflicts with──> Pure poll-only / no-open-ports security model (needs care: device still only *polls*, message is just data waiting to be pulled, not a push to the device)

Freshness timestamp / "couldn't refresh" glyph
    └──requires──> Nothing else — pure render-layer addition, no data dependency

Status LEDs / on-device settings UI (anti-features)
    └──conflicts with──> Ambient-first visual design differentiator
    └──conflicts with──> Single-button-only interaction model
```

### Dependency Notes

- **Physical button requires per-view poll/backoff state:** without tracking backoff state independently per view (plane vs RER), a button press to switch views could either force an unnecessary refetch of the view you're leaving, or fail to refresh the view you're switching to if the global backoff timer hasn't elapsed. This should be designed into the polling protocol from the start, not retrofitted.
- **Delay/status indicator requires both scheduled AND estimated/actual time:** many flight-data APIs only return a schedule unless you pay for or specifically request live/estimated data — confirm the chosen ORY data source actually returns an estimated/actual field before committing to this as table stakes; if it doesn't, the "delay" feature degrades to "scheduled time only," which is a materially weaker product.
- **Disruption banner conflicts (in priority, not architecture) with MVP scope:** RATP's SIEL disruption handling is a real UX precedent worth matching, but pulling a second RATP data feed (disruptions, separate from next-departures) adds integration surface. Treat as a fast-follow differentiator, not core MVP, unless disruptions on this specific RER line are frequent enough to matter for the "will I make it" use case.
- **Companion-app push (v2) must not violate the poll-only security posture:** PROJECT.md's reference architecture explicitly never accepts incoming connections to the device. A pushed message should land on the server and simply be picked up on the device's next scheduled or button-triggered poll — "push" is a server-side concept, not a device-side one.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept (already mirrors PROJECT.md's Active requirements, mapped to specific fields/behaviors).

- [ ] Plane view: flight number, destination, scheduled time, delay/cancelled status — the minimum FIDS-equivalent field set for a decision-useful board
- [ ] RER view: line, destination, minutes-until-next (at least 2 upcoming departures) — mirrors SIEL's minimum useful set
- [ ] Physical single-button: switch view + force fresh poll for that view
- [ ] Freshness indicator ("as of HH:MM") on both views
- [ ] Graceful stale/unreachable-server state (show last-known-good data, marked stale — never blank)
- [ ] Wake/poll/display/deep-sleep with exponential backoff (already scoped)
- [ ] Ambient-first, chrome-free visual layout (no status icons beyond the necessary freshness/stale glyph)

### Add After Validation (v1.x)

Features to add once core is working and real usage (does the user actually check it daily, does battery life hold up) validates the concept.

- [ ] "Leave by" / walk-time-buffer framing on RER view — trigger: once real usage confirms the raw countdown is being used to make the "should I leave now" decision, make that decision one glance easier
- [ ] Color-coded severity for delays/disruptions — trigger: once monochrome status text is confirmed legible/sufficient at a glance, layer in color as a polish pass rather than an MVP dependency
- [ ] Low-battery on-device indication (dedicated screen state) — trigger: once real battery-life data exists (a stated project goal) and a genuine low-battery threshold can be set with confidence

### Future Consideration (v2+)

Features to defer until the core two-view device has been validated as genuinely useful day-to-day.

- [ ] RER disruption banner (separate RATP data feed) — defer until it's clear disruptions are frequent enough on this line to justify the extra integration
- [ ] Companion phone app pushing short messages onto the frame — already explicitly scoped as v2 in PROJECT.md
- [ ] Additional views beyond plane/RER (weather, other transit lines, etc.) — explicitly resist per the anti-feature analysis above unless a specific validated need emerges

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Flight number/destination/time/status (plane view) | HIGH | LOW | P1 |
| RER line/destination/minutes (transit view) | HIGH | LOW | P1 |
| Physical button view-switch + forced poll | HIGH | MEDIUM | P1 |
| Freshness timestamp | HIGH | LOW | P1 |
| Graceful stale/offline state | MEDIUM | LOW | P1 |
| Wake/poll/deep-sleep + backoff | HIGH | HIGH | P1 (already required) |
| Ambient-first visual design (no chrome/LEDs) | HIGH | MEDIUM | P1 |
| "Leave by" buffer framing | MEDIUM-HIGH | LOW | P2 |
| Color-coded delay/disruption severity | MEDIUM | LOW | P2 |
| Low-battery on-device indicator | MEDIUM | LOW-MEDIUM | P2 |
| RER disruption banner (SIEL-style) | MEDIUM | MEDIUM | P2/P3 |
| Companion app push message | MEDIUM | HIGH | P3 (v2, already scoped) |
| Gate/terminal/check-in fields | LOW | LOW | Do not build (anti-feature) |
| Status LEDs | LOW | LOW | Do not build (anti-feature) |
| On-device settings/menu UI | LOW | MEDIUM | Do not build (anti-feature) |
| Push notifications to phone | LOW (for this device's purpose) | MEDIUM | Do not build (anti-feature) |
| Additional dashboard widgets (weather/news) | LOW (dilutes focus) | MEDIUM | Do not build (anti-feature) |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor / Precedent Feature Analysis

| Feature | FlightPortrait (direct reference) | TRMNL (general e-ink dashboard) | RATP SIEL (real transit board) | Our Approach |
|---------|-----------------------------------|----------------------------------|----------------------------------|--------------|
| Core content | Overhead planes crossing your sky (ADS-B derived), art-first | Any of 850+ plugins: calendar, weather, news, etc. | Next 2-4 train times + destination per platform | Two fixed, purpose-built views: ORY departures + Orly-Ville RER — narrower and more decision-useful than either precedent |
| Physical button | Not documented on marketing site (may not have one) | Button = refresh + advance to next playlist screen, but may show stale cached content on manual press | N/A (fixed public display, no user interaction) | Button = switch view + force genuinely fresh poll (server must re-fetch, not serve cache) — a deliberate improvement on TRMNL's documented caveat |
| Status/disruption handling | N/A (art content, no "delay" concept) | Plugin-dependent | Dedicated yellow disruption banner + train-position-instead-of-time during incidents | Borrow SIEL's disruption-banner pattern as a P2/P3 differentiator for the RER view; borrow FIDS status conventions for the plane view |
| Power/refresh model | Charges "every few months," positioned as near-zero-maintenance art | 2-6 months per charge depending on refresh interval | Mains-powered, always-on, real-time | Battery-only per PROJECT.md constraint; scheduled wake/poll/backoff (hours-scale) rather than TRMNL's more frequent typical intervals, to protect battery life given no solar/wall power |
| Visual identity | Explicitly "reads as paper, not a screen" — zero UI chrome | Widget/dashboard aesthetic, more visibly "smart display" | Institutional signage — functional, not art-directed | Aim closer to FlightPortrait's paper-like restraint than to TRMNL's dashboard aesthetic, while keeping FIDS/SIEL's information discipline (right fields, no more) |

## Sources

- [FlightPortrait — flightportrait.com](https://flightportrait.com/) — direct reference project's own positioning, battery life, display philosophy (MEDIUM confidence, single-source vendor claims)
- [TRMNL on-demand plugin refresh — help.trmnl.com](https://help.trmnl.com/en/articles/15123293-on-demand-plugin-refresh) — button-triggered refresh behavior and its cached-content caveat
- [TRMNL X review — the-gadgeteer.com](https://the-gadgeteer.com/2025/07/21/trmnl-e-ink-dashboard-display-review-better-than-onscreen-widgets/) and [TechBloat TRMNL X review](https://www.techbloat.com/trmnl-x-e-ink-display-review-2026.html) — battery life figures (2-6 months), zero-flicker refresh
- [SIEL (RER d'Île-de-France) — Wikipédia](https://fr.wikipedia.org/wiki/SIEL_(RER_d'%C3%8Ele-de-France)) and [SIEL (métro de Paris) — Wikipédia](https://fr.wikipedia.org/wiki/SIEL_(m%C3%A9tro_de_Paris)) — real RATP platform display behavior: wait times for next 2-4 trains, disruption banner, position-based fallback during incidents
- [RATP — real-time arrival/departure info](https://www.ratp.fr/en/where-can-i-find-arrival-and-departure-times-real-time) — official channel confirmation
- [Flight Information Display System (FIDS) — airlabs.co](https://airlabs.co/flight-information-display-system) and [linsnled.com FIDS guide](https://www.linsnled.com/flight-information-display.html) — canonical FIDS field set (airline, flight number, destination, gate, terminal, scheduled/estimated time, status, delay)
- [ESP32 Deep Sleep Guide — SolderHub](https://solderhub.com/articles/esp32-deep-sleep-battery-life-guide) and [Zbotic ESP32 deep sleep](https://zbotic.in/esp32-deep-sleep-long-battery-life-for-remote-sensors/) — battery life estimates by wake interval, low-battery display handling pattern
- [E-Paper Refresh Technology — Geniatech](https://www.geniatech.com/solution/e-paper-refresh-technology/) and [Core Electronics forum on e-ink ghosting](https://forum.core-electronics.com.au/t/e-ink-display-integration-ghosting-and-refresh-challenges/23151) — full vs. partial refresh tradeoffs, ghosting causes
- [Calm Technology — calmtech.com](https://calmtech.com/) and [Calm Tech: A New Era in HCI Philosophy — numberanalytics.com](https://www.numberanalytics.com/blog/calm-tech-hci-philosophy) — ambient/peripheral-attention design principles underlying the anti-features analysis
- General web search on smart-display bedroom/LED criticism — informs the anti-feature stance against status LEDs (LOW confidence, general commentary rather than a specific study)

---
*Feature research for: battery-powered e-ink departure board (flights + RER transit)*
*Researched: 2026-08-04*
