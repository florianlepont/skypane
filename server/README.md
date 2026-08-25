# server — Ink Frame Phase 2 plane-view server

The always-on backend that turns real ADS-B traffic over Orly runway 3 into
the 960,000-byte Spectra 6 panel image the device downloads and displays
(PLANE-01/02/03). This is the real server referenced in `.claude/CLAUDE.md`
and `.planning/phases/02-plane-view-end-to-end-slice/02-RESEARCH.md` —
`stub-server/byos_server.py` (still vendored, unchanged this plan) implements
the device-facing protocol; the modules in this directory feed it a freshly
rendered panel on a schedule.

## Setup

Create the virtualenv and install the two pinned dependencies:

```bash
python3 -m venv server/.venv
server/.venv/bin/pip install -r server/requirements.txt
```

`Pillow==12.3.0` and `requests==2.34.2` are the only two dependencies
(pinned versions re-verified against PyPI at execution time — see
`server/fixtures/README.md` and `02-RESEARCH.md`'s Package Legitimacy Audit
for why no third-party package needed a human-verify gate). Any additional
package must go through the same legitimacy check before entering
`requirements.txt`.

## Running the tests

Every `server/test_*.py` is a stdlib-only, directly-executable harness (no
pytest — see `stub-server/test_poll_cycle.py` for the established project
convention). Run each from the repository root so relative fixture/geofence
paths resolve:

```bash
server/.venv/bin/python3 server/test_plane_detection.py
server/.venv/bin/python3 server/test_pipeline_e2e.py
```

Both harnesses import Pillow (transitively, via the render pipeline) and so
must run under `server/.venv`'s interpreter, not the bare system `python3`.

## Poll cadence

`server/poll_loop.py` runs on a **30-second** cadence, matching Phase 1's
validated sampler interval (`adsb-test/RESULTS.md`) and comfortably inside
both aggregators' 1 req/s limit given one call per cycle. It is invoked as a
systemd-timer oneshot script — the timer unit itself lands in plan 02-05, not
this plan.

## Fixture provenance

`server/fixtures/` holds real ADS-B/enrichment records extracted from Phase
1's gitignored raw sample data, committed here so tests stay runnable on a
fresh clone. See `server/fixtures/README.md` for exactly which fields are
real vs. synthetic in each fixture.

## Deployment

This directory (plus `stub-server/`) runs on a real always-on Hetzner CX22
in production, driven by systemd units and fronted by Caddy for automatic
HTTPS — see `deploy/README.md` for the full runbook (provisioning,
shipping code, verifying TLS, reading logs, rolling back).

**Firmware-side change (configuration only, no C source changes):** once
the server is deployed, `firmware/main/secrets.h`'s `INK_API_BASE` moves
from the Phase 1 LAN address (`http://192.168.1.42:8642`) to the real
`https://<public-host>` base recorded in `deploy/README.md`, and
`INK_SETUP_SECRET` moves to the server's `INK_BYOS_SECRET` value. This is
a configuration change only — `firmware/main/api_client.c`'s ESP-TLS
`crt_bundle_attach` path is already compiled in and reachable on every
request (see `firmware/VENDOR.md`), so pointing it at a real HTTPS base
requires no firmware code changes, only rebuilding and reflashing with the
new `secrets.h` values (`firmware/build.sh`).
