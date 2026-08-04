# Ink Frame

## What This Is

An e-ink wall/desk frame that shows real-time departure info: flights taking off from Paris-Orly (ORY) and the next RER trains from Orly-Ville station, switchable via a physical button. Built on the same "wake → poll → display → deep sleep" architecture as the flightportrait reference project, running on battery power, with a small always-on cloud server generating the display images.

## Core Value

Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can see the next flights departing from Paris-Orly (ORY) on the frame
- [ ] User can see the next RER departures from Orly-Ville station on the frame
- [ ] Physical button on the device switches between the plane view and the RER view
- [ ] Switching views (button press) triggers a fresh poll for that view's data
- [ ] Device wakes on a schedule, polls the server over HTTPS, downloads a new image if one is available, displays it, then returns to deep sleep (mirrors flightportrait's wake/poll/backoff model)
- [ ] Device runs on battery power for v1 (no wall power, no solar)
- [ ] Server (small cloud VPS) fetches flight + RER data, renders display images, and serves them via a poll protocol the device calls
- [ ] (v2/later) Companion phone app can push a short message that appears on the frame

### Out of Scope

- Solar charging — deferred until real battery life and frame placement are known; indoor solar is unreliable without a well-lit window
- Local ADS-B receiver / SDR antenna — using a public flight-data API instead, since the use case is scheduled airport departures, not overhead flyovers
- Wall power — battery-only for v1, to force realistic power-budget decisions early

## Context

- **Reference project**: [flightportrait/frame](https://github.com/flightportrait/frame) — 13.3" E Ink Spectra 6 display (1200×1600, color), ESP32-S3 (reTerminal E1004 or XIAO ESP32-S3 Plus + EE02 driver board), microSD for offline images, BLE Security 2 provisioning, exponential-backoff polling (caps at 6h), SHA-256 verified downloads, persistent error logging, 3-endpoint HTTPS polling protocol (`docs/PROTOCOL.md`), reference Python server included. The device never accepts incoming connections — poll-only, no open ports.
- **Key difference from the reference project**: flightportrait renders any plane detected overhead via a local ADS-B receiver. This project instead tracks scheduled/live departures from a specific airport (Orly), so it uses a public flight-data API rather than an SDR antenna — no local RF hardware needed.
- **Airport**: Paris-Orly (ORY)
- **RER station**: Orly-Ville
- **Motivation**: equal parts satisfying hardware build / ambient art piece, and genuinely useful daily tool (e.g. checking whether you'll make the next RER before leaving the house)

## Constraints

- **Budget**: Hardware ≤ €300 total (display + compute) — user-set ceiling, roughly matches flightportrait-class hardware cost
- **Power**: Battery-only for v1, no solar, no wall power — indoor solar placement is unreliable, and the user wants real battery-life data before considering solar
- **Server hosting**: Small always-on cloud VPS, not a home server — a home server/Raspberry Pi is only reachable while powered and networked; the device should always find a reachable server

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Public flight-data API instead of local ADS-B receiver | Airport-departures use case doesn't need an overhead-flyover antenna; simpler build, no RF hardware | — Pending |
| Hardware mirrors flightportrait (13.3" E Ink Spectra 6 + ESP32-S3-class board) | Proven reference design, fits the €300 budget | — Pending |
| Battery-only power for v1, defer solar | Indoor solar reliability is unknown until placement and battery life are validated | — Pending |
| Physical button switches plane/RER view and triggers a fresh poll | Matches flightportrait's wake/poll/deep-sleep model while giving on-demand refresh on interaction | — Pending |
| Server on a small cloud VPS, not a home server | Reliability — the device should always find a reachable server, not one that depends on home power/network uptime | — Pending |

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
*Last updated: 2026-08-04 after initialization*
