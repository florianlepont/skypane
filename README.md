# SkyPane

An e-ink wall frame that shows real-time departure and arrival information
for aircraft using Orly (ORY) runway 3 — detected directly from public
ADS-B aggregator data, rendered server-side into a six-color panel image,
and pulled down by a battery-powered device on a wake → poll → display →
deep-sleep cycle.

**Core value:** glancing at the frame tells you, in real time, whether
you'll make the next RER — while also being a satisfying ambient piece on
the wall.

## v1 scope, honestly

What actually ships in v1: a **single view** showing the one aircraft
currently using runway 3 (departure or arrival, whichever the runway
configuration is doing right now), battery-only, no wall power, no solar.

What does **not** ship in v1, despite appearing in the core-value pitch
above: the RER (Orly-Ville) next-departures view, the "leave by" cue, and
the physical button that would switch between views. All three are
deferred to v2 (see `.planning/REQUIREMENTS.md`). There is also no
freshness/staleness indicator on the display — a deliberate v1 tradeoff,
not an oversight.

## What's here

| Directory | What it is | Read next |
|---|---|---|
| `firmware/` | ESP32-S3 device firmware (ESP-IDF, C) — the wake/poll/display/deep-sleep state machine that runs on the physical frame | This README's Firmware section, `firmware/VENDOR.md` |
| `server/` | The always-on render pipeline: ADS-B detection, route enrichment, panel rendering, and the poll-loop entrypoint | `server/README.md` |
| `stub-server/` | A throwaway local dev server implementing the same device protocol, used for firmware bring-up without a deployed backend | `stub-server/README.md` |
| `deploy/` | Scripts and unit files that turn `server/` + `stub-server/` into an always-on VPS deployment | `deploy/README.md` |
| `hardware/` | Bill of materials, physical bring-up log, and the battery-life measurement protocol | `hardware/BOM.md`, `hardware/BRINGUP-LOG.md` |
| `adsb-test/` | A Phase 1 spike that validated free public ADS-B aggregators can see low-altitude traffic near runway 3, before any of the above was built | `adsb-test/README.md` |

## Hardware

The bill of materials — a Seeed XIAO ePaper DIY Kit EE02 (XIAO ESP32-S3
Plus driver board + 13.3" E Ink Spectra 6 panel, 1200×1600, 6-color), a
3.7V LiPo battery pack, and a USB-C data cable — is at `hardware/BOM.md`,
including connector-polarity verification (a reversed-polarity battery
connection destroys the board and is not recoverable) and the full budget
breakdown against the project's €300 hardware ceiling.

**A real bring-up gotcha worth knowing before you flash anything:** after
a wake cycle finishes, the device disappears from the USB device list
within seconds. The first time this happens it looks exactly like a boot
loop or a brownout. It isn't — `esp_deep_sleep_start()` powers off the
USB Serial/JTAG peripheral along with everything else outside the RTC
domain, so the device correctly cutting power for deep sleep is
indistinguishable, at the USB-enumeration layer, from a crash. Full
diagnosis (including how to tell the two apart with a real serial
capture) is in `hardware/BRINGUP-LOG.md`.

## Server, locally

Create the virtualenv and install the two pinned dependencies:

```bash
python3 -m venv server/.venv
server/.venv/bin/pip install -r server/requirements.txt
```

Render a single panel image by hand (writes a packed 960,000-byte `.bin`
plus a viewable, non-color-accurate preview PNG):

```bash
server/.venv/bin/python3 server/plane/render.py --state departing --callsign AF1380 \
    --out /tmp/panel.bin --preview /tmp/panel.preview.png
```

Run one real poll cycle — detects the current runway-3 aircraft via the
live ADS-B aggregators, enriches it, and writes a fresh panel to a state
directory:

```bash
server/.venv/bin/python3 server/poll_loop.py --once --state-dir /tmp/skypane-state
```

In production this same script runs on a 30-second cadence as a systemd
timer's oneshot — see the Deployment section below.

## Tests

```bash
./scripts/run-all-tests.sh
```

This is the **exact same command CI runs** — a green local run means a
green pipeline. There is no pytest here by design: every
`server/test_*.py` / `stub-server/test_poll_cycle.py` harness is a
directly-executable, stdlib-only script that reports its own check count
and exit code (9 harnesses, currently 184 checks total), aggregated and
coverage-gated by the script above. Don't arrive expecting to invoke a
test collector — run each file, or run all of them via the script.

## Firmware

The firmware builds inside a pinned ESP-IDF container, so no host
toolchain install is required:

```bash
firmware/build.sh
```

Before your first build, copy the tracked credential template to the
gitignored real header the sources read from:

```bash
cp firmware/main/secrets.example.h firmware/main/secrets.h
# then edit secrets.h with your Wi-Fi credentials and server base URL/setup secret
```

Flashing over USB is a **separate, host-native step** (`firmware/flash.sh`)
— Docker Desktop's USB serial passthrough is unreliable on macOS, so the
container only ever does the build. For the flashing procedure itself,
the serial-port discovery steps, and the "appears then disappears" gotcha
above, see `hardware/BRINGUP-LOG.md` and `firmware/VENDOR.md` (the latter
also documents exactly which upstream files this firmware vendors from
[flightportrait/frame](https://github.com/flightportrait/frame), and
which are original to this project).

## Deployment

The server and stub-server run in production on an always-on VPS — Caddy
terminating TLS in front of the device protocol handler, a systemd timer
driving the poll loop every 30 seconds. The full runbook (provisioning a
fresh box, writing the one hand-set secrets file, shipping code, verifying
TLS, reading logs, rolling back) lives entirely in `deploy/README.md` —
this section intentionally doesn't restate any of it.

## Data sources

This project uses real-time ADS-B aircraft position data from
[adsb.fi](https://adsb.fi), queried first of two default aggregator
sources by every automated poll as of 2026-08-27. It is joined by
[adsb.lol](https://adsb.lol) as the second default source — two
independent feeds can corroborate or contradict a single reading, which
one feed alone cannot; adsb.lol's data is CC0-licensed and credited here
by choice, not because its licence requires it. Callsign/airline/route
enrichment is provided by [adsbdb.com](https://www.adsbdb.com), a free,
unauthenticated, crowdsourced lookup service.

[airplanes.live](https://airplanes.live) remains present in the code as an
explicit, opt-in `--provider` choice — for a feeder operator, sponsor, or
licensee — following its 2026-08-27 free-tier closure. It is documented but
not called by the default poll path; see [`COMPLIANCE.md`](./COMPLIANCE.md)
for the full detail.

No raw aggregator data is republished — what the device downloads is a
rendered panel image derived from a single selected flight, not a bulk
feed or dataset built from any of these sources. Full terms analysis and
citation text are in [`COMPLIANCE.md`](./COMPLIANCE.md).

## Licence and attribution

This project's own source code and documentation are licensed under the
[MIT License](./LICENSE). Vendored fonts, icons, and illustrations under
`server/assets/` carry their own, separate licences (SIL OFL 1.1 for
fonts, ISC for the Lucide-derived icons) — see the `VENDOR.md` file in
each asset subdirectory for the full per-file provenance, and `LICENSE`'s
own scope note before assuming the MIT grant covers an asset file.
