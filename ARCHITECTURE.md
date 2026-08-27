# Architecture

This document describes the system that actually shipped — the firmware
state machine, the server render pipeline, and the production deployment
topology — grounded in the files that implement each piece, so every claim
below can be checked against real code.

`.planning/research/ARCHITECTURE.md` is a different document: generic
domain research written 2026-08-04, before any of this existed. It is
retained as a record of the thinking that preceded the build, not as a
description of the built system — this file supersedes it for that
purpose.

## End-to-end data flow

```
 Public ADS-B aggregators                adsbdb.com
 (adsb.fi, sole default -                (callsign -> airline/route,
  airplanes.live opt-in/unused)           hit+miss cache)
        │                                       │
        │ HTTPS, geofenced query                │ HTTPS, cache-first
        ▼                                       ▼
 ┌─────────────────────────────────────────────────────────┐
 │  server/poll_loop.py  (systemd oneshot, every 30s)       │
 │    detect.py   -> select the one aircraft "using         │
 │                    runway 3 right now"                   │
 │    runway_config.py -> departing/arriving from vertical  │
 │                         rate, with a deadband             │
 │    enrich.py   -> airline + route, an airline-only         │
 │                    fallback from the callsign's ICAO      │
 │                    prefix, or a designed miss              │
 │    render.py   -> two-flight poster, packed to the        │
 │                    960,000-byte panel_format.py wire       │
 │                    format                                  │
 │  writes state/panel.bin (atomic, only if the image        │
 │  actually changed) + state/poll_state.json (cross-cycle   │
 │  history + enrichment cache)                               │
 └───────────────────────────┬───────────────────────────────┘
                              │ reads panel.bin on every request
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │  stub-server/byos_server.py  (device-facing protocol)     │
 │    POST /device/v1/setup    -> issues a bearer token      │
 │    GET  /device/v1/display  -> current image_hash/sleep_s │
 │    GET  /img/<sha>.bin      -> the panel bytes            │
 │    POST /device/v1/log      -> device telemetry/errors    │
 │  bound to loopback in production; Caddy is the only       │
 │  process that can reach it (see Deployment topology)      │
 └───────────────────────────┬───────────────────────────────┘
                              │ HTTPS, device-initiated only
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │  DEVICE (ESP32-S3, battery)                               │
 │    wake (timer) -> Wi-Fi join -> ensure bearer token       │
 │    -> GET /device/v1/display -> hash matches NVS?          │
 │       yes: skip download, sleep                            │
 │       no:  download + SHA-256 verify -> Wi-Fi off ->       │
 │            full-refresh blit (~31.5s) -> persist hash      │
 │    -> deep sleep (sleep_s from server, or a                 │
 │       backoff interval on failure)                          │
 └─────────────────────────────────────────────────────────┘
```

## Device firmware

The firmware is a single wake → poll → display → deep-sleep cycle,
orchestrated by `firmware/main/state_machine.c`'s `fp_poll_once()` and
driven by `app_main.c` (which owns the sleep-duration decision and the
final `esp_deep_sleep_start()` call on every branch).

**What happens on each wake, in order:**

1. Connect Wi-Fi (`wifi.c`), 15-second timeout. Failure here is logged as
   `poll fail step=wifi` and the whole cycle counts as a failure.
2. If no bearer token is held yet (`fp_api_has_token()`), call
   `POST /device/v1/setup` with the setup secret from the gitignored
   `secrets.h` — this happens once per device lifetime (or once per NVS
   erase), not on every wake.
3. `GET /device/v1/display` (`api_client.c`). The response carries the
   current `image_hash` and the `sleep_s` the device should sleep for next
   — the server, not the device, decides the wake cadence.
4. **Image-hash short-circuit:** if the returned `image_hash` matches the
   hash already stored in NVS, the device skips the download entirely and
   logs `poll ok sleep_s=<n> hash_skip=1`. This is the mechanism that
   keeps a wake cheap (and battery cost low) on every cycle where nothing
   changed on screen.
5. On a hash mismatch, the device downloads the image, verifying its
   SHA-256 and exact 960,000-byte size before ever handing the buffer back
   (`state_machine.c`). Wi-Fi is deliberately turned off
   (`fp_wifi_stop()`) before the blit starts — the blit is the longest
   part of the wake, and holding a Wi-Fi association through it buys
   nothing.
6. `fp_panel_draw()` performs the full-refresh blit. Two outcomes are
   deliberately *not* treated as failures: `ESP_ERR_INVALID_STATE` (a
   blit is already running) and `ESP_ERR_TIMEOUT` (the panel's minimum
   refresh-spacing outlasts this wake's awake budget) both return
   `FP_POLL_OK_DEFERRED` — the failure counter stays untouched, and
   because the image hash is deliberately left unrecorded on a deferred
   draw, the next wake fetches and draws the same picture instead of a
   healthy panel being punished with backoff.
7. On a genuine successful blit, the new image hash is persisted to NVS
   **only after** the blit succeeds — a blit that never happened can never
   cause a later wake to wrongly skip.

**Backoff on failure** (`backoff.c`): each consecutive failure increments
`FP_NVS_BACKOFF_N`; the next sleep interval is
`min(300 * 2^n, 21600)` seconds — a 5-minute base doubling on every
failure, saturating at a 6-hour ceiling once `n >= 7`. A success or a
deferred draw resets the counter to 0, so the device recovers to its
normal (server-supplied) cadence immediately once polling succeeds again.

**What persists in NVS across a full power loss** (`nvs_schema.h`, trimmed
from upstream's ~30 keys to exactly four): the bearer token
(`FP_NVS_DEVICE_TOKEN`), the last successfully-blitted image hash
(`FP_NVS_IMAGE_HASH`), the consecutive-failure counter
(`FP_NVS_BACKOFF_N`), and a boot counter (`FP_NVS_BOOT_COUNT`). Nothing
about which view is active is stored, because v1 has only one view.

**The observable interface — the Log Line Contract** (`firmware/VENDOR.md`),
five fixed line shapes emitted with ESP log tag `skypane`, deliberately
frozen so hardware-verification tooling can grep a serial capture for an
exact shape:

| When | Line shape |
|---|---|
| Every wake | `wake reason=<rtc\|power-on\|button\|other> boot_count=<n>` |
| Successful poll | `poll ok sleep_s=<n> hash_skip=<0\|1>` |
| Failed poll | `poll fail step=<wifi\|http\|status\|json\|download\|verify\|blit> backoff_n=<n> sleep_s=<n>` |
| Successful blit | `blit ok bytes=960000 sha256_ok=1` |
| Immediately before sleeping | `sleep enter sleep_s=<n>` |

No credential value — not the bearer token, not the Wi-Fi password, not
the setup secret — is ever a legal part of this contract.

**Measured constraint:** a full panel refresh takes **~31.5 seconds**
(measured twice on real hardware, `hardware/BRINGUP-LOG.md`), well inside
the panel driver's 60-second busy-wait timeout but a real, visible cost —
any decision about how often it's worth refreshing has to budget for the
panel being visibly mid-redraw for roughly half a minute afterward.

## Server render pipeline

`server/poll_loop.py` is the single entrypoint, invoked as a systemd-timer
oneshot every 30 seconds (matching Phase 1's validated aggregator sampler
interval, and comfortably inside both aggregators' 1 req/s limit). It has
no in-process memory of its own between invocations — all cross-cycle
state lives in `state/poll_state.json`, written with the same
tmp-write-then-`os.replace()` atomic pattern used throughout this
project.

**Detection.** `server/plane/detect.py` queries a geofenced bounding box
around runway 3 against `adsb.fi`. There is no automatic fallback provider
— since 2026-08-27, `adsb.fi` is the sole default (`airplaneslive` remains
in the code only as an explicit `--provider` opt-in for a feeder operator,
sponsor, or licensee, never queried automatically); an `adsb.fi` failure
yields no detection for that cycle, which the pipeline already handles as
the Empty state. When more than one aircraft is inside the geofence in the
same poll,
`select_runway3_aircraft()` picks exactly one by a deterministic total
order: lowest effective altitude first (an on-ground aircraft has
effective altitude 0), then the freshest position report, then
lexicographically smallest ICAO hex as a final tie-break — this is what
keeps the display from flickering between two simultaneous aircraft.

**Departing vs. arriving.** `server/plane/runway_config.py` infers the
runway's current configuration directly from the selected aircraft's
vertical rate, not from an external schedule or NOTAM feed:
`>= +200 ft/min` is climbing (departing), `<= -200 ft/min` is descending
(arriving), and anything strictly between those thresholds — or a
missing/non-numeric reading — **holds the last confirmed state** rather
than re-inferring from one ambiguous sample. A first-ever detection whose
reading falls inside that deadband renders the Empty state rather than
guessing a colour.

**Enrichment.** `server/plane/enrich.py` resolves the selected aircraft's
callsign to an airline and route via `adsbdb.com`, through a persistent,
callsign-keyed cache stored in `poll_state.json` that records **both hits
and misses** — a callsign already seen, resolved or not, is never
re-queried. The fallback is not a rare edge case: `adsbdb` resolves only
about 52.6% of this airport's real traffic mix (strong on legacy/full-
service carriers, weak on low-cost carriers that rotate callsigns per
tail) — this measurement stands unchanged and the miss path remains a
first-class, designed render state, not an error path bolted on
afterward.

What an adsbdb miss now means changed, however: a miss no longer implies
the panel has to give up on the airline's identity. `enrich.resolve_route()`
layers a second, independent source above the miss — the callsign's ICAO
3-letter prefix (e.g. `TVF` = Transavia France) resolved against a static,
in-repo table, with no additional network call and no additional cache
entry. The result is a three-outcome table: a full adsbdb hit renders the
route as before; an adsbdb miss whose prefix resolves renders the airline
name (and the airline's own illustration) with the destination honestly
left unknown (the bare callsign, no `to`/`from` clause); only when
*neither* source resolves anything does the panel fall all the way to the
**"Route unavailable" caption**, which is correspondingly rarer than the
52.6% figure alone would suggest, though still a first-class, designed
state rather than an error path.

**Composition.** `server/plane/render.py` builds a two-flight poster: the
current detection (large, upper-center) and the immediately-preceding
detection from `poll_state.json`'s two-deep history (smaller, lower-right)
— both share one canvas. Each flight card uses its own real per-airline
illustration (`server/plane/illustrations.py`, keyed off the resolved
airline name, falling back to a generic silhouette when no per-airline art
exists or the airline is unresolved), rendered full-color and
Floyd-Steinberg-dithered to the panel's exact 6-color palette
(`server/plane/dither.py`) rather than simplified to a flat silhouette.
The background is a flat single-color fill per state (blue for departing,
green for arriving) — no dithered gradient. Every text role uses PT Serif
Regular.

**Encoding.** `server/panel_format.py` is the single source of truth for
the wire format both `render.py` and the device agree on: a 1200×1600
canvas packed to exactly 960,000 bytes, two 4-bit pixels per byte, six
legal palette codes. `poll_loop.py` writes the packed result to
`state/panel.bin` only if its SHA-256 differs from what's already being
served, so `byos_server.py` never serves a half-written file and the
device's own image-hash short-circuit (above) actually has something
stable to compare against.

**Serving.** `stub-server/byos_server.py` — vendored from
`flightportrait/frame`, unchanged in logic — implements the device-facing
protocol in production, not just for local dev bring-up: `POST
/device/v1/setup` (issues a bearer token), `GET /device/v1/display`
(returns the current `image_hash`/`sleep_s`, computed by re-hashing
`panel.bin` on every request), `GET /img/<sha>.bin` (the panel bytes
themselves), and `POST /device/v1/log` (device telemetry/error reports).
It is a pure reader of `state/panel.bin` — it never calls an upstream API
itself, so a device poll's response time is decoupled from aggregator or
`adsbdb` latency entirely.

## Deployment topology

Production runs on a single always-on VPS (Ubuntu, provisioned by
`deploy/provision.sh`, updated by `deploy/deploy.sh` — see
`deploy/README.md` for the full runbook; the host is referred to here only
as `<public-host>`, never by its real address).

- **Caddy** terminates TLS (automatic Let's Encrypt) and reverse-proxies
  the public hostname to the app's loopback address on port 8642. This is
  the only process that can reach the app port — `byos_server.py` itself
  binds every interface (unpatched, vendored behaviour), so the loopback
  restriction is enforced at the network layer instead: `ufw deny
  8642/tcp` plus ufw's own default-deny-incoming policy block any direct
  external connection.
- **`skypane-byos.service`** runs `stub-server/byos_server.py` as a
  dedicated `skypane` user, `Restart=always`.
- **`skypane-poll.service` / `skypane-poll.timer`** is a `Type=oneshot`
  unit invoking `server/poll_loop.py --once`, fired every 30 seconds by
  the timer.
- **Device authentication** is a bearer token, issued at
  `/device/v1/setup` in exchange for a shared setup secret
  (`SKYPANE_BYOS_SECRET`, set once in a hand-written, gitignored
  `skypane.env` that is never rsynced and never committed) and then sent
  as `Authorization: Bearer <token>` on every subsequent `/display` and
  `/log` call. The device never accepts inbound connections at any point
  — it is poll-only, with no listening socket of its own.
- **State** — `state/panel.bin` and `state/poll_state.json` — lives on the
  VPS's local disk only, fully reproducible from this repository's
  `server/` and `stub-server/` trees plus the one hand-written env file;
  there is no separate database.
- **Shipping code** (`deploy/deploy.sh`) rsyncs `server/`, `stub-server/`,
  and the runway-3 geofence config, conditionally reinstalls Python
  dependencies, and restarts the two service units — no separate rollback
  mechanism exists beyond re-running the script against a working commit.

## Deliberate constraints

These are choices, not omissions:

- **Battery-only power, no wall power, no solar** (`.planning/PROJECT.md`).
  The user wants real battery-life data from the actual hardware
  combination before considering solar, and wall power was excluded
  specifically to force realistic power-budget decisions early in the
  build rather than defer them.
- **Poll-only device, no inbound pushes.** The device never accepts a
  connection — every interaction it has with the server is a request it
  initiates. This is a deliberate security posture (no open port on a
  battery-powered device sitting on a home network) inherited from the
  flightportrait reference design, not an accidental limitation.
- **Single view in v1.** The RER (Orly-Ville) view and the physical
  button that would switch between views are both deferred to v2
  (`.planning/REQUIREMENTS.md`) — a scope reduction so v1 could ship the
  plane view well rather than two views at once. Nothing in the firmware
  or server currently branches on "which view," because there is only
  one.
- **No freshness or stale-data indicator.** The device shows whatever the
  server last rendered with no on-screen indication of how old that
  render is. This is an explicit user tradeoff to keep v1 simpler,
  accepted despite research flagging it as a common pitfall for this
  class of device — revisit if staleness becomes a real problem in
  practice.
