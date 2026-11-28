# Architecture

This document describes the system that actually shipped: the ADS-B to frame
data flow, the firmware state machine, the server render pipeline, the fleet
platform around it (companion, fleet database, pairing, OTA), the production
deployment topology and the persistent-state map. It is grounded in the files
that implement each piece, so every claim below can be checked against real
code.

`.planning/research/ARCHITECTURE.md` is a different document: generic
domain research written 2026-08-04, before any of this existed. It is
retained as a record of the thinking that preceded the build, not as a
description of the built system — this file supersedes it for that
purpose.

## End-to-end data flow

```
 Public ADS-B aggregators                   adsbdb.com
 (adsb.fi + adsb.lol by default;            (callsign -> airline/route,
  airplanes.live only as an explicit         hit+miss cache)
  opt-in)
        │ HTTPS, one query per zone               │ HTTPS, cache-first
        ▼                                         ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  server/poll_loop.py  (systemd oneshot, every 30 s)            │
 │    -> server/polling/fleet_cycle.py run_fleet(): devices from  │
 │       fleet.db, grouped by exact polling zone; each zone is    │
 │       fetched once (polling/zone_fetch.py) under the shared    │
 │       request ledger (polling/request_budget.py)               │
 │    -> per device, server/poll_cycle.py run_once():             │
 │         detect     server/plane/detect.py, server/detection.py │
 │         direction  server/plane/runway_config.py               │
 │         enrich     server/plane/enrich.py                      │
 │         render     server/plane/render/ (classic poster,       │
 │                    giant-lettering layouts, landscape card)    │
 │         pack       server/panel_format.py                      │
 │  writes, per device directory (the live frame uses the state   │
 │  root itself): panel.bin (atomic, only when the image changed),│
 │  poll_state.json, history.db                                   │
 └───────────────────────────┬──────────────────────────────────┘
                              │ read on every device request
                              ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  stub-server/byos_server.py  (device-facing protocol)          │
 │    POST /device/v1/setup    -> issues a bearer token           │
 │    GET  /device/v1/display  -> image_hash, sleep_s, optional   │
 │                                firmware offer                  │
 │    GET  /img/<sha>.bin      -> the panel bytes (other frames:  │
 │                                /img/<device id>/<sha>.bin)     │
 │    POST /device/v1/log      -> device telemetry/errors         │
 │  loopback only; Caddy is the only process that reaches it      │
 └───────────────────────────┬──────────────────────────────────┘
                              │ HTTPS, device-initiated only
                              ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  DEVICE (ESP32-S3, battery)                                    │
 │    wake (timer) -> Wi-Fi join -> ensure bearer token           │
 │    -> GET /device/v1/display -> optional OTA offer             │
 │    -> hash matches NVS?                                        │
 │       yes: skip the download, sleep                            │
 │       no:  download + SHA-256 verify -> Wi-Fi off ->           │
 │            full-refresh blit -> persist hash                   │
 │    -> deep sleep (sleep_s from the server, or a backoff        │
 │       interval on failure)                                     │
 └──────────────────────────────────────────────────────────────┘

 Alongside the device path, on the same host:
   companion/app.py        invited users configure frames (fleet.db,
                           device_config.json, registries); it never
                           runs a poll cycle and never serves a device
   deploy/backup/skypane_backup.py   nightly snapshot of the state root
   Caddy                   TLS for both public hostnames
```

## Device firmware

The firmware is a single wake → poll → display → deep-sleep cycle,
orchestrated by `firmware/main/state_machine.c`'s `fp_poll_once()` and
driven by `firmware/main/app_main.c` (which owns the sleep-duration decision
through `fp_sleep_decide()` in `firmware/main/sleep_decision.c` and the final
`esp_deep_sleep_start()` call on every branch). It is built with ESP-IDF
5.3.1 and derives from the flightportrait frame firmware; every deviation
from upstream is listed in `firmware/VENDOR.md`. Two panel drivers exist: the
13.3" panel (`firmware/main/epd13in3e.c`, 960,000-byte image) and the 7.3"
panel (`firmware/main/epd7in3e.c`, 192,000-byte image), selected at compile
time by `firmware/main/panel_driver.h`.

**What happens on each wake, in order:**

1. `app_main.c` brings up NVS, classifies the wake reason, arms the
   whole-wake budget (`firmware/main/wake_deadline.c`) and the task watchdog,
   and reads the battery before Wi-Fi starts. A previous wake that ended in a
   panic, watchdog reset or brownout goes straight to a failure sleep without
   starting the radio (step `reset`).
2. Connect Wi-Fi (`firmware/main/wifi.c`), 15-second timeout. Failure here is
   logged as `poll fail step=wifi` and the whole cycle counts as a failure.
3. If no bearer token is held yet (`fp_api_has_token()`), call
   `POST /device/v1/setup` with the per-device enrolment secret read from the
   dedicated `secret` NVS partition (`firmware/main/enrol_secret.c`). This
   happens once per device lifetime (or once per NVS erase), not on every
   wake. Wi-Fi credentials and the server base URL come from the same
   partition; the image carries no credential.
4. `GET /device/v1/display` (`firmware/main/api_client.c`). The response
   carries the current `image_hash`, the `sleep_s` the device should sleep for
   next (the server, not the device, decides the wake cadence), the LED
   preference and an optional `firmware` offer. The request carries the
   battery reading, the previous wake's timing record (`X-Wake-Stats`), the
   hardware type, and any pending OTA outcome (`X-Ota-Result`).
5. **OTA branch** (`firmware/main/ota.c`, `firmware/main/ota_policy.c`),
   before the hash check so an offer lands even on a wake where the picture is
   unchanged: `fp_ota_decide()` skips a same-version offer and refuses on low
   battery or a version below the floor (neither is a failure). On a start the
   device draws the on-device UPDATING screen, downloads the signed image,
   reboots into it as a trial, and confirms it as the last step of the first
   healthy wake (`fp_ota_confirm_if_pending()`); a trial that crashes is
   rolled back by the bootloader and reported on the next poll. A failed
   attempt records its result token and the same wake carries on with the
   normal image path.
6. **Image-hash short-circuit:** if the returned `image_hash` matches the hash
   already stored in NVS, the device skips the download entirely and logs
   `poll ok sleep_s=<n> hash_skip=1`. This keeps a wake cheap on every cycle
   where nothing changed on screen.
7. On a hash mismatch, the device downloads the image, verifying its SHA-256
   and its length before the buffer is handed back. Wi-Fi is deliberately
   turned off (`fp_wifi_stop()`) before the blit starts, since the blit is the
   longest part of the wake. The body is then parsed as either a raw image or
   the framed image container (`firmware/main/image_container.c`, format in
   `server/image_container.py`, CRC-32 checked); a parse failure latches the
   `imgfmt_bad` flag so later requests ask for the raw image only, and leaves
   the last picture on the glass.
8. `fp_panel_draw()` performs the full-refresh blit. Two outcomes are
   deliberately *not* treated as failures: `ESP_ERR_INVALID_STATE` (a blit is
   already running) and `ESP_ERR_TIMEOUT` (the panel's minimum refresh spacing
   outlasts this wake's awake budget) both return `FP_POLL_OK_DEFERRED`. The
   failure counter stays untouched, and because the image hash is
   deliberately left unrecorded on a deferred draw, the next wake fetches and
   draws the same picture instead of a healthy panel being punished with
   backoff. A short spacing wait is taken inside the wake
   (`firmware/main/panel_guard.c`); the spacing itself is
   `CONFIG_FP_MIN_REFRESH_SPACING_S` (default 60 s).
9. On a genuine successful blit, the new image hash is persisted to NVS
   **only after** the blit succeeds, so a blit that never happened can never
   cause a later wake to wrongly skip.

**Backoff on failure** (`firmware/main/backoff.c`): each consecutive failure
increments `FP_NVS_BACKOFF_N`; the next sleep interval is
`min(300 * 2^n, 21600)` seconds, a 5-minute base doubling on every failure,
saturating at a 6-hour ceiling once `n >= 7`. A success or a deferred draw
resets the counter to 0, so the device recovers to its normal (server-supplied)
cadence immediately once polling succeeds again. A `sleep_s` of 0 from the
server is treated as a failure, because a zero-second timer wake would
hot-loop the radio.

**What persists in NVS across a full power loss**
(`firmware/main/nvs_schema.h`, split across two partitions). On the default
`nvs` partition, in the `skypane` namespace: the bearer token
(`FP_NVS_DEVICE_TOKEN`), the last successfully blitted image hash
(`FP_NVS_IMAGE_HASH`, which can also hold a sentinel after an on-device
screen was drawn), the consecutive-failure counter (`FP_NVS_BACKOFF_N`), a boot
counter (`FP_NVS_BOOT_COUNT`), the OTA trial marker and pending OTA result
(`FP_NVS_OTA_TRY`, `FP_NVS_OTA_RESULT`), and the `imgfmt_bad` flag. On its own
dedicated `secret` partition (read-only from the application's side, written
once over USB by `firmware/provision.sh`): the per-device enrolment secret,
the Wi-Fi SSID and password, the API base URL and four optional static-IP
keys. Nothing about a "view" is stored because the firmware has no view
concept.

**The observable interface — the Log Line Contract** (`firmware/VENDOR.md`),
five fixed line shapes emitted with ESP log tag `skypane`, deliberately
frozen so hardware-verification tooling can grep a serial capture for an
exact shape:

| When | Line shape |
|---|---|
| Every wake | `wake reason=<rtc\|power-on\|button\|other> boot_count=<n>` |
| Successful poll | `poll ok sleep_s=<n> hash_skip=<0\|1>` |
| Failed poll | `poll fail step=<wifi\|http\|status\|json\|download\|verify\|blit\|auth\|enrol\|secret\|config\|reset\|deadline\|nvs\|ota> backoff_n=<n> sleep_s=<n>` |
| Successful blit | `blit ok bytes=<n> sha256_ok=1` (`960000` on the 13.3" panel) |
| Immediately before sleeping | `sleep enter sleep_s=<n>` |

No credential value — not the bearer token, not the Wi-Fi password, not
the setup secret — is ever a legal part of this contract. `firmware/VENDOR.md`
explains each `step` token, and `firmware/tests/check_log_contract.sh` proves
every token the code can produce is listed there. Further diagnostic lines
(wake timing, reset reason) sit outside the frozen five.

**Measured constraint:** a full panel refresh takes **~31.5 seconds**
(measured twice on the 13.3" panel, `hardware/BRINGUP-LOG.md`), well inside
the panel driver's 60-second busy-wait timeout but a real, visible cost —
any decision about how often it's worth refreshing has to budget for the
panel being visibly mid-redraw for roughly half a minute afterward.

## Server render pipeline

`server/poll_loop.py` is the single entrypoint, invoked as a systemd-timer
oneshot every 30 seconds (comfortably inside both aggregators' 1 req/s limit, which
`server/polling/request_budget.py` enforces). It
parses `argparse` arguments and hands the whole fleet to
`server/polling/fleet_cycle.py`'s `run_fleet()`, which lists the devices in
`fleet.db` (the live frame alone when there is none), drops devices that
cannot be rendered here or have not checked in for seven days, and groups
the rest by exact polling zone. Held devices (battery critical, display
off, quiet hours) join no zone and cost no request. Each zone is fetched
once through `server/polling/zone_fetch.py`: adsb.fi then adsb.lol, one after the
other, every request spending a slot from the shared
`server/polling/request_budget.py` ledger (`request_ledger.json` in the state
root: 1.1 s global spacing, a 60 s pause per failing provider, and each
zone's last-served time, all behind a `flock`). Zones holding the live
frame go first, then the oldest-served; no new zone or device starts
after 25 seconds, and the devices not reached keep their current image.
Each device then runs `server/poll_cycle.py`'s `run_once()` on its zone's
shared result, in its own try/except, so one failing zone or device never
stops the others. The poll process is the only consumer of the ADS-B
budget: the companion has no route that runs a cycle. Overlapping poll
processes cannot run a cycle concurrently, because `run_once()` opens
`state/poll.lock` (`poll_cycle.poll_cycle_lock()`, an `fcntl.flock`) for
the duration of the cycle and waits up to a bounded timeout for it. The
companion's calendar-connect sync takes the per-device poll lock
(`device_scope.poll_lock_for`) without blocking, so it never overlaps a
running cycle. The cycle itself has no in-process
memory of its own between
invocations — all cross-cycle state lives in `state/poll_state.json`,
owned by `server/state_store.py` (path, load, serialise, save,
persist-if-changed) and written with the same
tmp-write-then-`os.replace()` atomic pattern used throughout this
project.

**Module map.** Entry points and the cycle:

- `server/poll_loop.py`: the systemd-timer entrypoint (`argparse`/`main()`
  only).
- `server/polling/fleet_cycle.py`: `run_fleet()`, the per-zone fan-out described
  above. `server/polling/fleet_zones.py` holds the pure zone identity, capacity
  ordering and device activity rules (no I/O, no clock).
- `server/polling/zone_fetch.py` and `server/polling/http_fetch.py`: one zone's provider
  queries, and the bounded outbound HTTP they go through (total wall-clock
  deadline, byte cap, pinned public address).
- `server/polling/request_budget.py`: the shared ADS-B request ledger.
- `server/poll_cycle.py`: the cycle itself. `load_cycle_context` /
  `decide_hold` / `run_hold_cycle` or `detect_flight` / `load_display_slots` /
  `update_battery_low` / `advance_display_queue` / `render_and_publish` /
  `record` / `persist` / `log_cycle`, each a named step over one
  `CycleContext` dataclass, with one shared `publish_canvas()` for every
  render-pack-write-gallery copy.
- `server/state_store.py`: `poll_state.json`'s sole owner.
  `server/atomic_io.py`: atomic writes and `fcntl.flock` locks.
- `server/device_policy.py`: stdlib-only battery hysteresis, the discharge
  curve and quiet-hours arithmetic, shared unchanged by `server/`,
  `stub-server/byos_server.py` and `companion/battery.py`/`wake.py`.
- `server/wake.py` and `server/wake_stats.py`: the effective wake interval,
  derived staleness thresholds, and the strict parser of the device's
  `X-Wake-Stats` header. `server/check_interval.py`: the opt-in
  check-interval experiment.

Detection and rendering:

- `server/detection.py`: turns a device's stored runway or position
  configuration into a polling zone plus a geofence document.
  `server/airports.py` is the read-only France runway catalogue
  (`server/data/airports_fr.json`).
- `server/plane/detect.py`, `server/plane/runway_config.py`,
  `server/plane/enrich.py`, `server/plane/route_sanity.py`,
  `server/plane/shared_route_cache.py`: detection, direction, enrichment.
- `server/plane/render/`: the renderers. `layout.py` is the dispatcher
  (`build_canvas`), with `style`, `text`, `glyphs`, `hold_screens` and `cli`
  beside it; `landscape.py`, `landscape_card.py`, `landscape_common.py` and
  `landscape_hold.py` for the landscape family; `giant/` for the
  giant-lettering family (`lettering`, `aircraft`, `field`, `fonts`,
  `compose`, `compose_c`, `compose_landscape`, `geometry_landscape`,
  `status`, `split`, `icons`, `palette_check`). It is still importable as
  `server.plane.render`.
- `server/screen_layouts.py` (the layout ids and the default),
  `server/pairing/pairings.py` (the field/lettering pairings and the theme mapping),
  `server/themes.py` (theme registry), `server/visible_window.py` (drawing
  inside the part of a panel a mat leaves visible), `server/panel_format.py`
  and `server/image_container.py` (wire formats), `server/plane/dither.py`,
  `server/plane/illustrations.py`.
- `server/plane/calendar_rules/`: RFC 5545 parsing, registry and
  theme matching (`ics`/`registry`/`match`), importable as
  `server.plane.calendar_rules`; `server/net/safe_fetch.py` is the one
  SSRF-safety gate its feed fetch calls.
- `server/plane/colour_rules.py`, `server/plane/manual_resolutions.py`,
  `server/plane/name_overrides.py`, `server/plane/airline_default_types.py`:
  the per-airline registries; `server/plane/fleet_registries.py`,
  `fleet_artwork.py`, `fleet_default_types.py` and `fleet_set_defaults.py`
  merge them to the fleet root at deploy time.

Fleet data:

- `server/fleet_db.py`: the `fleet.db` schema, migrations and connections;
  `server/fleet_migrate.py`: the deploy-time import of the legacy identity
  files; `server/fleet_ops.py`: register, claim, retire, reassign;
  `server/fleet_sessions.py`: sessions and invite-only identity linking.
- `server/device_dirs.py`: the only code that turns a stored `state_path`
  into a directory. `server/device_config.py`: per-frame configuration.
- `server/history_db.py`: `history.db`.
- `server/hardware.py`: hardware profiles. `server/firmware/` (`registry.py`,
  `image.py`, `cli.py`): OTA.
- `server/pairing/` (`pairings.py`, `code.py`, `image.py`): the pairing flow
  and the field/lettering pairings.
- `server/polling/` (`fleet_cycle.py`, `fleet_zones.py`, `zone_fetch.py`,
  `http_fetch.py`, `request_budget.py`): the polling support described above.

**Compatibility shims.** The three groups above moved out of the flat
`server/` directory. The old flat paths (`server/firmware_registry.py`,
`server/firmware_image.py`, `server/firmware_cli.py`,
`server/request_budget.py`, `server/zone_fetch.py`, `server/http_fetch.py`,
`server/fleet_zones.py`, `server/fleet_cycle.py`, `server/pairings.py`,
`server/pairing_code.py`, `server/pairing_image.py`) are `sys.modules`
aliases of the moved modules, kept so existing importers, tests and
`monkeypatch` sites keep working. `server/poll_loop.py`, `server/poll_cycle.py`, `server/fleet_db.py`,
`server/history_db.py` and `server/device_config.py` stay in place.

Other processes: `stub-server/byos_server.py` (device protocol),
`stub-server/devices_cli.py` and `stub-server/fleet_cli.py` (operator CLIs),
`companion/app.py` (configuration web app; its single route table is
`companion/routes.py`, its pages are in `companion/pages/` and its form
handlers in `companion/settings/`), and `deploy/backup/skypane_backup.py`.

**Detection.** `server/plane/detect.py` queries a geofenced bounding box
around the watched runway (runway 3 at Orly for the original frame; see
"Fleet platform" for the other detection modes) against both default
sources, `adsb.fi` then `adsb.lol` (the second added 2026-08-27), and
cross-validates them rather than
returning on the first hit. **Corroboration is on each source's whole
candidate set, not on its final pick** (2026-08-28): the poll intersects
the sets of aircraft each source independently judged to be on the runway,
and selects one from that common set. A source that answered but saw nothing
on the runway is not a dissenting vote; only sources that saw traffic are
intersected. When at least one aircraft is common,
the returned selection is corroborated and carries `adsb.fi`'s own record —
ordering decides which source's record survives, since the first-queried
provider is the one selected from. When only one source answers (the other
unreachable, blocked, or gated behind a future feeder-contributed API key),
that source's selection is still returned, flagged uncorroborated rather
than suppressed — this is why an outage at either default source does not
blank the display. Only when **no aircraft at all is common to every
source that saw traffic** does the poll return nothing for that cycle, which the
pipeline already treats as the between-flights hold rather than an error.

Comparing sets rather than picks matters because the two feeds are
independent feeder networks that routinely hold overlapping-but-unequal
views: one has received an aircraft the other has not yet. Comparing only
the winners turned that into a fabricated disagreement and discarded the
cycle, freezing the panel while real traffic passed — and it did so all the
more often because the selection's tie-break used to be `seen_pos`, a
per-provider staleness value, which let two sources rank one identical
reality differently. The safety property is unchanged in both directions:
the displayed aircraft was always, and is still, one that every answering
source independently saw on runway 3. What narrowed is only the
suppression trigger. A source carrying a phantom the other lacks now yields
the corroborated real aircraft instead of a blank panel, because the
uncorroborated record is excluded from selection rather than merely losing
a comparison. What this still cannot detect is both sources being wrong the
same way — a shared phantom is in the intersection and is displayed as
corroborated.
`airplaneslive` remains in the code only as an explicit `--provider`
opt-in for a feeder operator, sponsor, or licensee, never queried
automatically. The bounding box is only a coarse pre-filter — it contains
most of Orly's two *other* runways — so a record becomes a candidate only
once it also passes a geometric gate derived from runway 3's own published
threshold coordinates: laterally inside a runway-aligned corridor, and
pointing along the runway's axis. An aircraft reporting itself **on the
ground** is held to a tighter version of that corridor, runway 3's actual
pavement, because every on-ground record scores effective altitude 0 below
and would otherwise let a taxiing aircraft outrank real runway-3 traffic
indefinitely. Among whatever survives that gate in the same poll,
`select_aircraft_for_runway()` picks exactly one by a deterministic total
order: lowest effective altitude first (an on-ground aircraft has
effective altitude 0), then lexicographically smallest ICAO hex as the
tie-break. Both terms are properties of the *aircraft*, which is what keeps
the display from flickering between two simultaneous aircraft and makes the
pick identical no matter which source answered. The rule used to tie-break
on the freshest position report first; that field (`seen_pos`) is a
property of the *feeder network* rather than of the aircraft, so it changed
the answer depending on who was asked and when — see the detection
paragraph above. It is still carried on the selection for diagnostics, just
no longer used to order anything.

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

That third outcome — neither adsbdb nor the prefix table resolving
anything — now leaves a durable trace (quick task 260827-oz9): the
callsign's 3-letter ICAO prefix is accumulated into `poll_state.json`
alongside the enrichment cache, under an `unresolved_prefixes` key carrying
an occurrence count, a first-seen and last-seen timestamp, and a recent
example callsign, with the same-cycle `unknown_prefix` log field acting as
the immediate, per-cycle view of the same fact. A persisted record exists
because journald's retention is time-bounded and rotates while the
question it answers — which carriers serving this airport this project
still cannot name — is a slow one, measured in weeks; the concrete
motivation is that the alternative is the manual cross-reference against
the official Paris Aéroport airline list that produced this session's five
prior additions. Three honest caveats apply: the count is poll cycles
rather than distinct flights, so one aircraft held on the runway inflates
it; the record is bounded in entry count and evicts the least-recurring
entry first, precisely so a spoofed or malformed callsign field cannot
displace a genuine finding; and only shape-valid callsigns whose prefix is
absent from the static table are ever recorded, so a covered airline can
never appear there. The remediation for a recorded prefix is to
live-verify it against adsbdb and add a row to the static table under that
table's own sourcing discipline — never to infer an airline name from the
three letters.

**Display pacing.** Detecting an aircraft and *showing* it are no longer the
same event (2026-08-28). The server re-renders every 30 seconds, but the
frame's own floor between two drawn images is roughly **90 seconds** — the
firmware's 60-second inter-refresh guard, re-armed after every blit, plus the
measured ~31.5s full refresh above. Advancing the "current" slot on every
distinct detection therefore overwrote `panel.bin` two or three times per
device redraw, and any aircraft whose turn fell entirely between two redraws
was never fetched, never drawn, and left no trace anywhere — the server's own
logs looked perfectly healthy throughout.

So `poll_cycle.py`'s `advance_display_queue` step keeps a small
**bounded-age FIFO queue** of distinct
selections in `poll_state.json` (`pending_flights`, each entry stamped with
the time it was *first* detected, plus a `last_advance_at` timestamp). The
"current" slot advances no more often than `MIN_ADVANCE_INTERVAL_S` (90s,
derived from the two firmware numbers above), and when it does it promotes
the **oldest still-fresh** entry rather than whatever was detected most
recently — so aircraft reach the glass in the order they actually flew.
Draining runs on every cycle including empty ones, since a burst followed by
a quiet sky is the common shape.

Two bounds keep this from becoming a backlog, which is the failure mode an
unbounded "never drop a flight" queue would have had: an entry more than
`MAX_STALENESS_S` (**150s**) old when its turn arrives is **discarded rather
than displayed**, and the queue is capped at `MAX_PENDING_FLIGHTS` (5 — the
most distinct aircraft that can legitimately be enqueued inside one 150s
window at a 30s poll cadence), evicting oldest-first. This is a **mitigation,
not a cure**: a burst severe enough to overflow both bounds still loses
flights, deliberately, because showing a two-minute-old departure as if it
were current would defeat the point of a real-time board. Those losses are at
least no longer silent — the poll line's `dropped=` field names every hex the
queue discarded, alongside `shown=` (what is actually on the panel, which on
a paced cycle differs from `hex=`, this cycle's detection) and `pending=`.

Because the pipeline is a systemd oneshot with no in-process memory, every
pacing and staleness decision is arithmetic over timestamps persisted in
`poll_state.json`; the clock itself is a module-level seam (`now_s()`) so the
harness can drive cadence deterministically instead of sleeping.

**Composition.** `server/plane/render/layout.py`'s `build_canvas()` is the
dispatcher. Each device carries a hardware profile (`server/hardware.py`) and
a stored screen layout id (`server/screen_layouts.py`); an unknown id
normalises to `DEFAULT_LAYOUT_ID`, currently the centred giant-lettering
layout `b`. Three renderer families sit behind the dispatcher:

- **Giant lettering** (`server/plane/render/giant/`): the layout ids `a`,
  `b`, `c` and `a_diagonal`. Oversized destination lettering set in Anton,
  with the aircraft placed over it, drawn in one of five colour pairings
  (`server/pairing/pairings.py`, mapped from the stored theme id at read time so no
  stored configuration is rewritten). Portrait and landscape canvases have
  their own compositors; a canvas size with none draws the classic picture.
  The hold states under a giant layout draw the calm status screens of
  `server/plane/render/giant/status.py`, which ignore the theme.
- **Landscape card** (`server/plane/render/landscape.py`): the native
  landscape family for a landscape hardware profile when the layout is not a
  giant one (including `classic`); a flight card at the profile's own size.
- **Classic poster** (layout id `classic` on a portrait profile, and the
  unchanged legacy path for a frame with no profile): the original
  two-flight poster. The current
  detection (large, upper-center) and the immediately-preceding one from
  `poll_state.json`'s two-deep history (smaller, lower-right) share one
  canvas. Since the pacing change above, "preceding" means the aircraft that
  previously occupied the current slot, which is not always the previous
  *detection*. Each card uses its own per-airline illustration
  (`server/plane/illustrations.py`, keyed off the resolved airline name,
  falling back to a generic silhouette), rendered full-color and
  Floyd-Steinberg-dithered to the panel's exact 6-color palette
  (`server/plane/dither.py`). The background is a flat single-color fill per
  state (blue for departing, green for arriving). Every text role uses PT
  Serif Regular.

A profile with a `visible_window` (the 7.3" frame behind a mat) draws the
whole screen at the window's size and pastes it into the panel-sized canvas,
so nothing is drawn behind the mat.

**Encoding.** `server/panel_format.py` is the single source of truth for
the wire format both `server/plane/render/` and the device agree on: a
1200×1600 canvas packed to exactly 960,000 bytes, two 4-bit pixels per
byte, six legal palette codes. `poll_cycle.py`'s `publish_canvas()`
writes the packed result to `state/panel.bin` only if its SHA-256 differs
from what's already being served, so `byos_server.py` never serves a
half-written file and the device's own image-hash short-circuit (above)
actually has something stable to compare against.

**Serving.** `stub-server/byos_server.py` derives from
`flightportrait/frame`'s protocol server and implements the device-facing
protocol in production, not just for local dev bring-up: `POST
/device/v1/setup` (issues a bearer token), `GET /device/v1/display`
(returns the current `image_hash`/`sleep_s`, computed by re-hashing the
device's `panel.bin` on every request, plus the optional firmware offer and
the LED preference), `GET /img/<sha>.bin` (the live frame's panel bytes;
other frames use `/img/<device id>/<sha>.bin`), and `POST /device/v1/log`
(device telemetry/error reports). Each request is resolved to a device
through its MAC and bearer token against `fleet.db` (see "Device
authentication" below); a registered but unclaimed (pending) or retired frame
is served its pairing or retired screen from `<state>/pairing/<pending id>/`.
The server is a pure reader of the panel files the poll process writes: it
never calls an upstream API itself, so a device poll's response time is
decoupled from aggregator or `adsbdb` latency entirely. It shares device
policy with the poll cycle through `server/device_policy.py` (quiet hours,
the battery-critical rule, the sleep/wake constants) and
`server/state_store.py` (the `poll_state.json` latch reader), both
stdlib-only so byos gains no third-party dependency; it reaches them through
the release's repo root on `sys.path` (`/opt/skypane/current`, root-owned,
read-only under `ProtectSystem=strict`). An invalid stored quiet-hours time
falls back to the same default 23:00-07:00 window on both sides.

**Hold screens and the `sleep_s` composition.** Three deliberate "resting
on purpose" screens can each replace the live board, in priority order:
BATTERY EMPTY, then DISPLAY OFF (the companion's manual toggle), then
QUIET HOURS (the companion's scheduled window). All three are drawn by
`server/plane/render/hold_screens.py`'s shared dimmed composition (a
dithered dark field, one glyph, a tracked label, a short rule, two body
sentences) so they read as one family; `poll_cycle.py`'s `run_hold_cycle()`
renders each once on entry (and, uniquely for BATTERY EMPTY, again on the
boundary crossing into or out of it from another hold) and is otherwise a
no-op — an e-ink refresh costs energy and time the device is asleep for
regardless.

BATTERY EMPTY is latched from the device's own `X-Battery-Mv` header:
`server/device_policy.py`'s `apply_battery_critical_hysteresis()` (called
from `poll_cycle.py`'s `load_cycle_context()`) enters the hold at 3300 mV
and clears it only at 3700 mV or above (a 400 mV re-arm buffer, wider
than the separate 3500/3600 mV low-battery *badge* hysteresis, which is
unaffected), persisting the decision as `poll_state.json`'s
`battery_critical_active` key — `server/state_store.py` is that file's
single writer. While parked, detection is skipped entirely (there is
nothing new to check for until the pack is recharged), and
`stub-server/byos_server.py` reads the same latch through
`server/state_store.py`'s `read_battery_critical()` — the one shared,
fail-open reader both processes now call — to pin `sleep_s` to a fixed
3600 seconds — composed as
`quiet_hours_sleep_s(battery_critical_sleep_s(display_off_sleep_s(base,
...), ..., fresh_battery_mv), ...)`, so a longer active quiet-hours
window can still extend the sleep beyond an hour, and a display-off pin
never outlasts the flatter-pack pin. `battery_critical_sleep_s()`
additionally anticipates recovery *within the same request that reports
it*: if that request's own `X-Battery-Mv` is already at or above 3700 mV,
it hands back the normal base value immediately rather than the stale
3600 seconds `poll_cycle.py`'s own latch clear (up to 30 seconds later)
would otherwise still imply.

The same latch feeds a monitoring mirror so a parked frame's slower
check-ins are never mistaken for silence: `server/wake.py`'s
`effective_wake_interval_s()`/`next_wake_status()` accept a
`battery_critical` flag that pins their own answer to the 3600-second
cadence ahead of every other consideration, and every caller that decides
whether the frame has "gone quiet" — the companion's Frame
strip/flash text (`companion/layout.py`, `companion/app.py`) — reads it
from the same persisted latch before computing its own staleness
threshold.

**NO CONNECTION — the fourth hold screen, drawn by the device, not the
server (DEVICE-06, quick task `260924-u7n`).** The three hold screens
above share one property that breaks down exactly when it matters most:
they are all server-rendered, so they need a successful poll to ever
reach the panel. If the device cannot reach the server at all, the
server can never bake an alert into anything. NO CONNECTION is the one
hold screen the firmware draws entirely on its own, with zero server
round-trip: `firmware/main/app_main.c`'s `fail_and_sleep()` calls
`fp_fault_screen_should_draw()` (`firmware/main/fault_screen.h`) after
its 2nd consecutive failure of an allow-listed comm/data step (`wifi`,
`http`, `status`, `json`, `secret`, `config`, `download`, `verify` — never
`blit`/`reset`/`deadline`, which would risk looping or overrunning the wake
budget, nor `auth`/`enrol`, which a server answer rather than a lost
connection causes), and, if it returns true, renders and blits the screen via a pure on-device integer
Floyd-Steinberg dither of the same dark field the other three hold
screens use, stamped with a small pre-baked ink mask
(`firmware/main/fault_screen_mask.h`). It is drawn once per outage — a
sentinel reusing `FP_NVS_IMAGE_HASH` (deliberately never shaped like a
real `sha256:<hex>` server hash) suppresses every subsequent failing
wake's redraw and guarantees the first healthy poll after recovery
always re-downloads and blits the real server picture, since its hash
can never match the sentinel. `server/plane/render/hold_screens.py`'s
`_build_no_connection_canvas()` is the artwork's one source of truth —
the same shared `_build_hold_canvas()` composition DISPLAY OFF/QUIET
HOURS/BATTERY EMPTY go through, with its own alert-triangle glyph
(`draw_alert_icon()`) — but `build_canvas()` never dispatches it; instead
`firmware/tools/gen_fault_screen.py` renders it flat, extracts its ink
mask, and generates the committed header, with a pytest drift test
(`server/test_fault_screen_mask.py`) proving the two can never silently
diverge.

## Fleet platform

The project grew from one frame at one runway into a small invited fleet.
This section names the pieces that make that work and the module that owns
each. The access and at-rest review of these pieces is the Phase 66 audit
(`66-AUDIT.md`); nothing here restates or extends its security conclusions.

**Frames, locations and detection modes.** Every frame is a row in
`fleet.db` (`server/fleet_db.py`) with an owner, a hardware type and a
`state_path` (`.` for the live frame, `devices/<id>` for every other one).
A frame detects in one of two modes (`server/detection.py`): runway mode,
for any runway in the France catalogue (`server/airports.py`), or position
mode, which polls the area around a rounded location (about 1 km). The three
legacy Orly runway ids keep a frozen bounding box taken from
`adsb-test/runway3.json`, so their decisions never change.

**Sign-in, roles and access.** The companion signs people in with Auth0
(`companion/oidc.py`: PKCE, the authorize and logout URLs, ID-token claim
validation; the flow itself is `companion/sign_in.py`). Sign-in is
invite-only: `server/fleet_sessions.py` never creates a user, it links a
login to a `users` row an administrator already created. A session cookie
carries an opaque token whose SHA-256 alone is stored in `fleet.db`; a session
is absolute for 30 days and idle for 7, and its role is read fresh from
`users` on every request. Roles are `admin` and `user`
(`server/fleet_db.py`). Access is default-deny and decided by pure functions
in `companion/access.py`: an administrator reaches any frame, a user the
frames they own or co-manage (`companion/co_managers.py`), and owner-only
actions exclude co-managers. Every route is declared once, with its access
class, in `companion/routes.py`. Invitations create the Auth0 database user
through the Management API client in `companion/auth0_management.py`. The
console writes an audit row for administrative actions
(`companion/audit.py`, table `audit_log`).

**Hardware profiles.** `server/hardware.py` is a committed registry of
hardware types: resolution, palette, layout family (portrait or landscape),
battery profile with recorded provenance, firmware target and, for a framed
panel, the visible window. The shipped real types are the 13.3" EE02 and the
7.3" EE04 (800x480, landscape); simulated types exist for development, and a
real type can stay gated behind `SKYPANE_ENABLE_SECOND_HARDWARE`. The server
assigns a frame its type; the `X-Hw-Type` a device sends is only a claim that
can withdraw an OTA offer, never select a type (`claim_contradicts()` in
`stub-server/byos_server.py`).

**Pairing.** A registered frame nobody has claimed shows a pairing code on its
panel (`server/pairing/image.py`). A signed-in person types the code on the
Add a frame page (`companion/user_pairing.py`); the claim is one
`BEGIN IMMEDIATE` transaction in `server/fleet_ops.py` that deletes the
pending row, creates the device, provisions its directory and writes the
audit row. Codes are stored only as salted hashes (`server/pairing/code.py`),
and wrong, expired and used codes give the same refusal. In-memory
failure-count lockouts bound guessing (`companion/throttle.py`). A
retired frame shows a FRAME RETIRED screen. Registration by MAC or enrolment
secret stays under the administrator-only Fleet routes
(`companion/console_pairing.py`).

**OTA.** `server/firmware/registry.py` is the one definition of what has
been published, what is scheduled for each hardware type and what the last
attempts reported (`registry.json` in the state root's `firmware/` directory, one
document per type, images content-addressed as `<sha256>.bin`). The device server composes the
offer from `compute_offer()`, the poll process reconciles device reports,
the companion's Update page schedules and cancels, and the deploy step
imports published releases (`server/firmware/cli.py`). `server/firmware/image.py`
parses and validates ESP application images; the RSA signature is checked
by the device at boot, and the committed public key is
`firmware/signing/skypane-signing-pubkey.pem` (key handling in
`firmware/SIGNING.md`). An offer is not subject to quiet hours or display-off.

**Wake interval.** Each frame has its own saved `wake_interval_s`
(`server/device_config.py`, edited by `companion/settings/wake_interval.py`),
and the device server turns it into the `sleep_s` of every display response.
The order of composition (saved interval or the check-interval experiment,
display off, battery empty, quiet hours) is documented at the call site in
`stub-server/byos_server.py`. `server/wake.py` derives the thresholds the
companion uses to decide that a frame has gone quiet.

**Request budget.** The fleet sends at most one ADS-B request per second in
total, whatever the provider, zone or process: `server/polling/request_budget.py`
keeps the spacing, the per-provider pause and the per-zone last-served times
in `request_ledger.json` behind a `flock`, and the lock is a leaf lock.

**Backup.** `deploy/backup/skypane_backup.py` snapshots the state root nightly;
the coverage and its gaps are listed under "Backup coverage" below, and the
off-box pull is described in `deploy/README.md`.

## Deployment topology

Production runs on a single always-on VPS (Ubuntu, provisioned once by
`deploy/provision.sh`, updated by `deploy/deploy.sh` and `deploy/activate.sh`;
see `deploy/README.md` for the full runbook). The host is referred to here
only as `<public-host>` for the device protocol and `<companion-host>` for the
configuration interface, never by a real address.

**Six systemd units** run the system (`deploy/*.service`, `deploy/*.timer`):

- **`skypane-byos.service`** runs `stub-server/byos_server.py` as a dedicated
  `skypane` user, `Restart=always`. It binds to `127.0.0.1` (`--bind`), its
  unit carries `IPAddressDeny=any` + `IPAddressAllow=localhost`, and `ufw deny
  8642/tcp` plus ufw's default-deny-incoming policy block any direct external
  connection. Caddy is the only process that can reach it.
- **`skypane-poll.service` / `skypane-poll.timer`**: a `Type=oneshot` unit
  invoking `server/poll_loop.py --once`, fired by the timer 30 seconds after
  boot and then every 30 seconds.
- **`skypane-companion.service`** runs `companion/app.py`, the configuration
  web interface, as its own process on its own loopback port, behind its own
  Caddy hostname (`<companion-host>`, its own Let's Encrypt certificate). It
  makes its own outbound calls (calendar feeds, Auth0), so it
  does not carry the device server's address allow-list. It never touches
  `stub-server/byos_server.py` and has no route that runs a poll cycle.
- **`skypane-backup.service` / `skypane-backup.timer`**: a nightly oneshot
  (03:15 UTC) running `deploy/backup/skypane_backup.py`.

**Caddy** terminates TLS (automatic Let's Encrypt) for both hostnames and
reverse-proxies each to its loopback port. The host's `/etc/caddy/Caddyfile`
is shared with other sites and is never written by SkyPane; SkyPane owns one
site file, `/etc/caddy/sites/skypane.caddy`, rendered by `activate.sh`
(`deploy/render_caddyfile.sh`, `deploy/Caddyfile`). Caddy's JSON access log on
the device-protocol site block is the durable source the poll process tails
for the `X-Battery-Mv` history.

**Who writes what.** The companion owns the writes of `fleet.db` (users,
roles, sessions, audit rows, co-managers, pairing and frame lifecycle), the
per-frame `device_config.json`, the fleet registries and the uploaded
artwork. It reads the state the poll process writes and writes the
runway-event rows of `history.db` that `companion/airline_fleet_world.py`
produces. The poll process writes `panel.bin`, `poll_state.json`, `history.db`
and the gallery. The device server writes the bearer-token and
enrolment-secret columns of `fleet.db`, `battery_state.json` (the single
latest `X-Battery-Mv`, overwritten every poll; the battery *history* comes
from the Caddy log) and `device_report.json` in that same directory. The full table, with
readers and backup coverage, is under "Persistent state" below.

**Device authentication** is per device, not a single shared secret.
`stub-server/byos_server.py` gates `/device/v1/setup` against the per-device
enrolment secret hash stored in `fleet.db` (`effective_registry`); a device
presents its MAC and its own secret (held read-only on its dedicated `secret`
NVS partition, provisioned once over USB by `firmware/provision.sh`) and, on a
match, receives a bearer token, sent as `Authorization: Bearer <token>` on
every subsequent `/display` and `/log` call. A wrong or unregistered secret
leaves any existing token untouched, so one compromised device's secret cannot
be used to hijack another's enrolment. `devices.json` and `byos_state.json`
are a legacy mirror kept in step so the previous release keeps working on the
same state (see "Duplicated or overlapping data" below); when `fleet.db` is
absent or not yet migrated the device server falls back to them. The device
never accepts inbound connections at any point: it is poll-only, with no
listening socket of its own.

**Shipping code is a manual, gated step.** `.github/workflows/deploy.yml` is
started by hand only (`workflow_dispatch`) on `main`, bound to the
`production` environment so a required reviewer gates the run and the deploy
secrets stay in that environment. A merge to `main` never deploys. The job
refuses to run unless the confirmation matches the tip of `main` and a green
CI run exists for the commit. Then:

1. `deploy/deploy.sh <ssh-target>` streams `git archive` of the committed
   tree (`server`, `stub-server`, `companion`, `deploy`,
   `adsb-test/runway3.json`, the firmware public key; never `server/state/`,
   a virtualenv or the env file) over ssh into
   `/opt/skypane/releases/.incoming-<sha>`, and optionally the published
   firmware releases beside it.
2. `deploy/activate.sh <sha>` runs on the VPS as root. It stages the release,
   reinstalls Python dependencies if their hash changed, byte-compiles and
   smoke-tests the release's own scripts, imports firmware, takes a state
   backup and runs the fleet database migration (`server/fleet_migrate.py`)
   as a dry run and then for real, all before the swap (any failure aborts
   with the old release still serving), renders and validates the Caddy site
   file, installs the units, and swaps the `current` link atomically
   (`ln -sfn` into a temporary link, then `mv -T`). It then restarts the
   services, reloads Caddy only if the site file changed, and probes every
   unit and both HTTPS surfaces.
3. **Rollback is built in.** A failed probe swaps `current` back to the
   previous release the same way, restarts, and exits non-zero so the CI job
   goes red while the previous release keeps serving. Old releases are pruned
   (the last five are kept). Re-running `activate.sh` for the SHA that is
   already current only restarts and re-probes.

State (`/opt/skypane/state`) lives on the VPS's local disk and is not part of
a release; the code of a release is fully reproducible from this repository,
the state from the nightly backup.

## Persistent state

Everything the system remembers lives under one state root on the VPS
(`<state-root>`, `/opt/skypane/state` in production, `server/state/` in a
checkout). The root is two things at once: the **fleet root** (files shared
by every frame) and the **live frame's own directory** (its `state_path` is
`"."`). Every other frame has its own directory, `devices/<id>/`, where
`<id>` is `d_` plus eight lowercase hex digits (`server/device_dirs.py`,
the only code that turns a stored `state_path` into a directory). The
section was checked against the code; the access and at-rest review of
these stores is the Phase 66 audit (`66-AUDIT.md`) and is not repeated here.

### Stores and owners

| Store | Where | Writers | Readers | Backed up | Notes |
|-------|-------|---------|---------|-----------|-------|
| `fleet.db` (SQLite, WAL, mode 0600, `user_version` 4) | root | companion (users, roles, sessions, audit, co-managers, pairing, frames); device server (token and enrolment-secret writes); `server/fleet_migrate.py` (deploy step) | companion; device server (read-only per request); poll process (`server/polling/fleet_cycle.py`) | yes: online copy through the sqlite3 backup API, then an integrity check | tables `users`, `locations`, `devices`, `meta`, `sessions`, `pending_devices`, `audit_log`, `device_co_managers` |
| `history.db` (SQLite, WAL, `user_version` 1) | root (live frame) and `devices/<id>/` | poll process (runway events, poll cycles, route lookups, meta, battery readings tailed from the Caddy log); companion for the few runway-event rows written by `companion/airline_fleet_world.py` | companion (Health, History, Home, export); poll process | yes, the root file and every per-frame file | tables `runway_events`, `device_health`, `meta`, `wake_epochs`, `poll_cycles`, `route_lookups` |
| `device_config.json`, `poll_state.json`, `battery_state.json` | root and `devices/<id>/` | companion (config); poll process (poll state); device server (latest battery reading) | all three processes | yes, root and per frame | atomic writes (`server/atomic_io.py`); the config has its own lock |
| Fleet registries: `manual_resolutions.json`, `airline_name_overrides.json`, `airline_default_types.json`, `airline_suggestions.json`, `airline_default_types_set.json`, `airline_default_types_cleared.json`, `colour_rules.json`, `calendar_rules.json` with `calendar_url.secret` | fleet root (colour and calendar rules also per frame) | companion | poll process, companion | yes | the per-frame copies of the first three are leftovers, see below |
| Migration markers: `airline_registry_migration.json`, `illustration_migration.json`, `airline_default_types_migration.json`, `airline_default_types_set_migration.json` | root | `server/fleet_migrate.py` and the `server/plane/fleet_*` merge modules | the same modules | yes | idempotency markers: restore them together with the data they guard |
| `devices.json`, `byos_state.json` | root | `stub-server/devices_cli.py`; device server (mirror of tokens and secrets) | device server when `fleet.db` is absent or not yet migrated; `server/fleet_migrate.py` | yes | legacy identity files, see "Duplicated or overlapping data" |
| `live_frame_macs.json` | root | `server/device_dirs.py` | device server | yes | the one record of which frame is the live one that survives an unreadable `fleet.db` |
| `firmware/` (`registry.json`, `device_report.json`, images) | root | `server/firmware/cli.py`; device server (`device_report.json` only) | device server; companion Update page | yes, the directory (lock files excluded) | `registry.lock` serialises registry writers |
| `illustration_overrides/`, `illustration_conflicts/`, `gallery/` | root (overrides and gallery also per frame) | companion (overrides); poll process (gallery) | poll process, companion | yes | the per-frame override directories are leftovers after the merge |
| Regenerable or short-lived: `panel.bin`, `fleet_status.json`, `request_ledger.json`, `adsbdb_shared_cache.json*`, `check_interval_experiment.json`, `pairing/`, `img/`, `theme_previews/`, `frame_previews/`, `*.lock`, `caddy-access*.log*` | root and per frame | various | various | no, by design | rebuilt by the next poll, or expire within hours |

### Migrations

There are two mechanisms, and the difference is deliberate.

- **`fleet.db`** (`server/fleet_db.py`) has an ordered tuple `MIGRATIONS`.
  Each step runs in one transaction together with its `PRAGMA user_version`
  bump. A file whose version is newer than the code is refused and never
  written (`FleetDbTooNew`), which is what keeps the previous release safe
  on migrated state. Foreign keys are enabled per connection and the file
  is created mode 0600. Migration runs as an explicit deploy step
  (`server/fleet_migrate.py`) and again on `connect()`.
- **`history.db`** (`server/history_db.py`) uses idempotent
  `CREATE TABLE IF NOT EXISTS` statements plus guarded `ALTER TABLE ... ADD
  COLUMN` steps that tolerate a "duplicate column name" race. They run once
  per process for a given file identity, and `user_version` is only ever
  raised. A newer file is not refused. The reason is concurrency: the poll
  oneshot and the companion can both open a fresh or older file at the same
  moment, so the upgrade has to be safe to run twice in parallel, which a
  transactional, order-enforcing scheme does not give for free.

Decision: **documented, not unified.** This is a provisional default: the
two contracts differ for a reason, and a shared mechanism would touch the
two most heavily used modules for no behavioural gain. The owner may
override it; if so, the only logic worth sharing is the 5000 ms busy
timeout, the WAL pragma and the `user_version` read.

### Duplicated or overlapping data

Each item below is kept on purpose or is data held for later. Retiring any
of them needs an owner decision on the end of the rollback period.
Provisional default: document, do not retire; no schema change.

1. **Legacy identity mirror** (rollback safety net). The enrolment-secret
   hash and the device token exist in `fleet.db` (`devices`,
   `pending_devices`) and in `devices.json` / `byos_state.json`. With a
   migrated `fleet.db` the device server reads `fleet.db`
   (`effective_registry`, `effective_tokens`); token issue writes both and
   leaves the legacy file untouched if the `fleet.db` write fails;
   `devices_cli` changes are mirrored to `fleet.db` one way; the migration
   reconcile lets the legacy file win on secret and token. This is what lets
   the previous release keep working on the same state.
2. **Per-frame registry leftovers** (rollback safety net). Per-frame
   `manual_resolutions.json`, `airline_name_overrides.json`,
   `airline_default_types.json` and `devices/<id>/illustration_overrides/`
   were merged into the fleet root. The runtime resolves the registries
   through `device_dirs.fleet_root_for` and no longer reads the copies; the
   backup still includes them.
3. **`history.db.meta` keys with no production writer** (leftover).
   `META_PROVIDER_LAST_CALL_PREFIX` and `META_LAST_POLL_TRIGGER` are only
   referenced by the status-key filter in `server/history_db.py`. The live
   record of ADS-B request spacing is `request_ledger.json`
   (`server/polling/request_budget.py`).
4. **`wake_epochs`** (planned data). Written by the poll cycle, read only by
   `history_db` itself for de-duplication. It accrues data that no screen
   uses yet; a test pins that no companion file reads it.
5. **`legacy-admin` principal** (rollback safety net). The `sessions` table
   still allows `principal = 'legacy-admin'` although the shared-password
   sign-in no longer exists. Removing the value needs a schema step and
   would break the rule that the previous release runs on migrated state.
6. **Location helpers with no production caller** (leftover). In
   `server/fleet_db.py`, `delete_location_if_unused`,
   `count_locations_owned` and `location_usage_counts` have no production
   caller since the Locations routes were removed; tests still use them.
7. **Same-named constants** (leftover). File-name constants are defined
   more than once (`CONFIG_FILENAME` in `server/device_dirs.py` and
   `DEVICE_CONFIG_FILENAME` in `server/device_config.py`;
   `REGISTRY_FILE` in the device server and `LEGACY_REGISTRY_FILE` in
   `server/fleet_migrate.py`; a MAC pattern defined several times, with one
   case-insensitive variant in the device server). The backup script
   duplicates the device-id pattern on purpose, so it runs without the
   `server` package.

### Backup coverage

`deploy/backup/skypane_backup.py` writes one checksummed archive per night.
Its lists are an allow-list: an entry that is neither included nor in
`KNOWN_EXCLUDED` is reported as drift on stdout rather than carried silently.

- **Covered:** `fleet.db` and every `history.db` (online copy plus
  integrity check); every JSON file in `INCLUDE_FILES` and
  `DEVICE_INCLUDE_FILES`; `firmware/`, `gallery/`, `illustration_overrides/`,
  `illustration_conflicts/`; the migration markers.
- **Excluded by design:** the environment file, the firmware signing key and
  the Caddy configuration and certificates are not under the state root and
  are never archived; regenerable or short-lived state (last row of the
  table above) is skipped because the next poll rebuilds it or it expires.
- **Two noted gaps.** `history.db.meta.caddy_log_offset` is archived while
  `caddy-access*.log*` is not. After a restore the stored offset can differ
  from the fresh log; the tailer resets to 0 when the file is smaller than
  the offset, and re-reading a range is harmless because battery readings
  are unique on timestamp and value. `check_interval_experiment.json` is not
  archived; it expires within 72 hours and is re-created with
  `python3 -m server.check_interval set`.

### Connections and locking

- `fleet_db.connect` opens a connection per call with a 5000 ms busy
  timeout, WAL and foreign keys on. Writes use the `transaction()` helper
  (`BEGIN IMMEDIATE`), so a check-then-write never runs without the write
  lock. The device server opens `connect_readonly` per request, which never
  creates or migrates the file.
- `history_db.connection_scope` shares one connection per thread inside the
  scope and opens per call outside it. Read paths open the file with
  `mode=ro` and `query_only`. Schema setup runs once per process per file
  identity.
- File locks use `fcntl.flock` through `atomic_io.exclusive_lock`:
  `poll.lock` (per frame directory), `calendar_rules.lock`,
  `device_config.lock`, `request_ledger.lock`, the route-cache lock and
  `registry.lock` (firmware). Documented order: in-process
  `threading.Lock`, then `poll.lock`, then `calendar_rules.lock`;
  `device_config.lock` is never taken while another is held. No deadlock
  was found by reading the code and nothing needs to change.

## Deliberate constraints

These are choices, not omissions:

- **Battery-only power, no wall power, no solar** (`.planning/PROJECT.md`).
  The user wants real battery-life data from the actual hardware
  combination before considering solar, and wall power was excluded
  specifically to force realistic power-budget decisions early in the
  build rather than defer them.
- **Poll-only device, no inbound pushes.** The device never accepts a
  connection; every interaction it has with the server is a request it
  initiates. This is a deliberate security posture (no open port on a
  battery-powered device sitting on a home network) inherited from the
  flightportrait reference design, not an accidental limitation. Changes made
  in the companion therefore reach a frame at its next wake.
- **One view.** The firmware and the server have no notion of "which view":
  the RER (Orly-Ville) view and the physical button that would switch views
  were dropped from the project on 2026-10-28
  (`.planning/workstreams/v1-2/REQUIREMENTS.md`, "Out of Scope"). Nothing in
  the firmware or server branches on a view.
- **No render-age stamp on the panel.** The device shows whatever the server
  last rendered, with no indication of how old that render is. This is an
  explicit tradeoff to keep the picture clean. As of 2026-11-27 two things
  soften it without adding a stamp: when no ADS-B source answers, the
  renderer draws an "ADS-B source unavailable" badge
  (`draw_source_fault_badge()` in `server/plane/render/layout.py`), and a
  frame that stops checking in is reported by the companion's health views
  (`server/wake.py`, `companion/health_signals.py`). The auto-refresh of
  `companion/static/freshness.js` is about the companion page staying current,
  not about the panel.
