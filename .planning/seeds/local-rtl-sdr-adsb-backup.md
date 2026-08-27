---
title: Local RTL-SDR receiver as a backup/redundant ADS-B data source
trigger_condition: >
  Revisit if adsb.fi (current sole default provider) and adsb.lol (best
  current software alternative) both become unavailable, rate-limited, or
  gated behind a feeder/sponsorship/commercial-license requirement — the
  same fate that already hit airplanes.live (2026-08-27) and apparently
  adsb.one (GitHub repo archived April 2026). Also revisit if the user
  decides they want genuine independence from any third-party aggregator's
  policy risk for the project's core detection function, even before a
  third source dies.
planted_date: 2026-08-27
---

## Context

Explored 2026-08-27 (see `.planning/debug/resolved/runway3-false-positive.md`'s
follow-ups and this session's ADS-B backup-source research) after the user
asked whether local reception should be reconsidered, given free public
aggregators have now demonstrated a real, recurring sustainability risk
(2 of 4 candidate software sources already destabilized within one project's
lifetime). PROJECT.md's original Phase 1 decision to skip RTL-SDR assumed
free aggregators would keep being free and available; that assumption has
now failed twice.

Explicitly **not needed now** — the user framed this as insurance for a
future scenario where no free aggregator database remains available, not
an immediate requirement. Captured here so the technical shape doesn't need
re-deriving when/if the trigger condition fires.

## What was established (technical feasibility)

**Not a simple "add a provider" change.** adsb.lol slots into the existing
`server/plane/detect.py` `PROVIDERS` dict trivially because it's just
another outbound HTTPS GET to a public REST API, reachable from the same
cloud VPS that already does the rendering. RTL-SDR is architecturally
different:

- **Reception must be physically local to Orly** (1090MHz radio, not an
  internet API) — the cloud VPS (Hetzner/OVH, not near Paris) cannot host
  the receiver. This requires a new always-on host **at the user's home**
  running a decoder (`readsb` or `dump1090-fa`, free) fed by an RTL-SDR
  USB dongle + antenna (~$40 RTL-SDR Blog V4 kit, or ~$100 FlightAware
  FlightFeeder Basic prebuilt, prices checked 2026-08-27).
- **Ruled out: running the decoder directly on the Frame's own XIAO
  ESP32-S3 board.** Two independent, non-negotiable blockers (see the
  companion note `rtl-sdr-not-feasible-on-frame-board.md`): the deep-sleep
  battery architecture is incompatible with the always-on operation ADS-B
  decoding needs, and the sustained DSP workload (2.4 Msps IQ sample
  correlation/demodulation) is a Pi-class compute job, not a microcontroller
  one.
- **The real remaining engineering question is the home-to-VPS bridge**,
  since home networks aren't directly reachable from the internet (no
  inbound port without router config). Two candidate approaches surfaced:
  1. **Push-based** (recommended direction) — the home decoder host POSTs
     its current runway-3 selection (or raw geofenced snapshot) to a new
     authenticated endpoint on the existing cloud server every poll cycle,
     mirroring the project's existing "device never accepts inbound
     connections, always initiates" philosophy (the e-ink device itself
     already works this way against the cloud server).
  2. **Tunnel-based** (Tailscale/WireGuard) — lets the VPS pull data from
     the home host on demand, more flexible but adds an always-maintained
     tunnel service as a dependency.
- **Host options the user already has, without buying new hardware**: a
  Raspberry Pi, or their Freebox (Delta/Pop) — see the companion research
  question on whether the specific Freebox model can run `readsb` directly
  via its app/VM platform, which would avoid dedicating a separate Pi.
- Once local data reaches the server, it would plug into `detect.py` as a
  new provider-like adapter (reading the most-recently-pushed local cache
  instead of doing a live outbound GET) — conceptually the same shape as
  today's `PROVIDERS`/`poll_current_aircraft()` cross-validation logic
  added by the runway3-false-positive fix, extended to a third source.

## Why this matters enough to seed (not just drop)

Two of the four viable-looking free aggregator options from this session's
research have already died or destabilized within this project's own
lifetime (airplanes.live: policy change 2026-08-27; adsb.one: repo archived
April 2026, live API now 403s). adsb.lol's own documentation pre-announces
it intends to do the same. A local receiver is the only option in the
comparison that is structurally immune to any third party's future policy
decision — worth remembering as a real fallback, not a novelty, if the
remaining software options keep failing at the current rate.
