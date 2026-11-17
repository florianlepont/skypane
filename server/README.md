# server — SkyPane Phase 2 plane-view server

The always-on backend that turns real ADS-B traffic over Orly runway 3 into
the 960,000-byte Spectra 6 panel image the device downloads and displays
(PLANE-01/02/03). This is the real server referenced in `.claude/CLAUDE.md`
and `.planning/phases/02-plane-view-end-to-end-slice/02-RESEARCH.md` —
`stub-server/byos_server.py` (still vendored, unchanged this plan) implements
the device-facing protocol; the modules in this directory feed it a freshly
rendered panel on a schedule.

## Setup

Create the virtualenv and install the two pinned runtime dependencies,
with hashes enforced:

```bash
python3 -m venv server/.venv
server/.venv/bin/pip install --require-hashes -r server/requirements.txt
```

`Pillow==12.3.0` and `requests==2.34.2` are the only two runtime
dependencies (pinned versions re-verified against PyPI at execution time
— see `server/fixtures/README.md` and `02-RESEARCH.md`'s Package
Legitimacy Audit for why no third-party package needed a human-verify
gate). Any additional package must go through the same legitimacy check
before entering `requirements.in` (then re-locked with
`scripts/lock-deps.sh`).

## Running the tests

Tests run under pytest, from the repository root so relative
fixture/geofence paths resolve. Install the dev superset first (adds
pytest, pytest-xdist, pytest-cov and friends on top of the runtime pins):

```bash
server/.venv/bin/pip install --require-hashes -r server/requirements-dev.txt
server/.venv/bin/python3 -m pytest server/test_plane_detection.py
server/.venv/bin/python3 -m pytest server/test_pipeline_e2e.py
```

Or run the whole suite (server, stub-server, companion) the way CI does:
`./scripts/run-all-tests.sh`. Both harnesses above import Pillow
(transitively, via the render pipeline) and so must run under
`server/.venv`'s interpreter, not the bare system `python3`.

## Poll cadence

`server/poll_loop.py` runs on a **30-second** cadence, matching Phase 1's
validated sampler interval (`adsb-test/RESULTS.md`) and comfortably inside
both aggregators' 1 req/s limit given one call per cycle. It is invoked as a
systemd-timer oneshot script — the timer unit itself lands in plan 02-05, not
this plan.

## Check-interval experiment

An opt-in, self-expiring experiment that separates how often the frame
checks in from how often the flight image is replaced. While it runs, the
frame wakes every `check_interval_s` (at least 60 s) and the flight image
changes at most once per the device's saved `wake_interval_s`; between
changes the served image hash is the same, so the firmware leaves the panel
alone. Hold screens (display off, battery empty, quiet hours) are never
delayed, and those overrides keep their own `sleep_s`.

```
python3 -m server.check_interval set --check-interval-s 60 --hours 24
python3 -m server.check_interval set --state-dir server/state/devices/d_xxxxxxxx
python3 -m server.check_interval status
python3 -m server.check_interval clear
```

Without `--state-dir` the command acts on the live frame
(`server/state`). The experiment needs a `wake_interval_s` saved in the
companion that is longer than `check_interval_s`, lasts at most 72 hours
(`--hours`, default 24) and is ignored whenever the last battery reading is
unknown or at or below 3700 mV. With no experiment file nothing changes.

## Fixture provenance

`server/fixtures/` holds real ADS-B/enrichment records extracted from Phase
1's gitignored raw sample data, committed here so tests stay runnable on a
fresh clone. See `server/fixtures/README.md` for exactly which fields are
real vs. synthetic in each fixture.

## Screen layouts

The layouts, colour pairings, default and golden tests are described in
[`docs/plane-screen-layouts.md`](../docs/plane-screen-layouts.md).

## Deployment

This directory (plus `stub-server/`) runs on a real always-on OVH VPS-1
in production, driven by systemd units and fronted by Caddy for automatic
HTTPS — see `deploy/README.md` for the full runbook (provisioning,
shipping code, verifying TLS, reading logs, rolling back).

**Firmware-side change (provisioning only, no rebuild):** once the server
is deployed, a device's API base moves from the Phase 1 LAN address
(`http://192.168.1.42:8642`) to the real `https://<public-host>` base
recorded in `deploy/README.md` by re-running `firmware/provision.sh
<serial-port> --wifi-ssid <ssid> --api-base https://<public-host>` — the
API base lives in the device's own `secret` NVS partition
(`fp_device_creds_load`, `firmware/main/enrol_secret.c`), never compiled
into the image, so pointing a device at a real HTTPS base needs no
firmware rebuild or reflash. `firmware/main/api_client.c`'s ESP-TLS
`crt_bundle_attach` path is already compiled in and reachable on every
request regardless of which base is provisioned (see `firmware/VENDOR.md`).
