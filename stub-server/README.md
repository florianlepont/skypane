# stub-server

## What this is

A throwaway local stub implementing the three device endpoints from the
flightportrait device protocol (`POST /device/v1/setup`, `GET
/device/v1/display`, `POST /device/v1/log`, plus `GET /img/<sha>.bin`),
vendored from `flightportrait/frame` at a pinned commit (see
`stub-server/VENDOR.md`). It exists to validate the Phase 1 device loop
before any hardware has arrived.

Per **D-09**, this never runs on the Hetzner VPS. It is a local-only
developer tool. Phase 2 replaces it with the real rendering server, deployed
on the real cloud host.

## Generate a panel image

```bash
python3 stub-server/make_test_panel.py --pattern palette --out /tmp/panel.bin
python3 stub-server/make_test_panel.py --pattern quadrants --out /tmp/panel-alt.bin
```

`palette` produces six full-height vertical stripes (black, white, yellow,
red, blue, green) — a correct blit shows six clean bands, and a swapped
nibble order or a wrong master/slave chip-select split is instantly visible
on the glass. `quadrants` produces four coloured quadrants inside a
one-pixel black border, used as a second, distinct image to prove the
server's hash-change behaviour. Both are exactly 960,000 bytes and
deterministic — running the same pattern twice produces the same file.

## Run the server

Serve the palette image on port 8642 with a sleep value of 300 (used by
plan 01-06's repeatability run and plan 01-07's battery run, so a battery
depletion result arrives in days rather than months):

```bash
python3 stub-server/byos_server.py --image /tmp/panel.bin --port 8642 --sleep 300
```

For a longer-lived server that isn't tied to a short test cadence, use a
sleep value of 3600 instead:

```bash
python3 stub-server/byos_server.py --image /tmp/panel.bin --port 8642 --sleep 3600
```

`sleep_s` is what the device is told to sleep for after a successful poll —
it isn't a server-side setting, it's the number the device receives and
obeys on its next `esp_deep_sleep_start()`. A smaller value means shorter,
more frequent wake cycles, which is exactly what a repeatability or battery
test needs to see many cycles quickly.

## Point the device at it

Print the laptop's LAN IPv4 address on macOS:

```bash
ipconfig getifaddr en0 || ipconfig getifaddr en1
```

The firmware's server base is the `http` scheme followed by that address
and the port — e.g. `http://192.168.1.42:8642`. This value is set in
`firmware/main/secrets.example.h` (copy it to `firmware/main/secrets.h`,
which is gitignored, and fill in the real address there).

The laptop must stay awake and on the same network for the device to reach
it. macOS sleep is the single most common cause of an unexplained device
backoff during the hardware plans — if the frame appears to be backing off
for no reason, check whether the laptop went to sleep first.

## Transport

The device protocol permits a hand-set BYOS server target to be plain
`http` — only the compiled-in production default requires strict HTTPS.
This stub therefore serves plain HTTP and needs no certificate.

**Accepted consequence:** the bearer token travels in cleartext on the
local network. **Hard boundary:** this applies only to this throwaway
Phase 1 stub. The Phase 2 VPS uses real HTTPS; the ESP-TLS and public CA
bundle code path stays compiled into the firmware and reachable the whole
time, so that later move is a configuration change, not a code change.

## Run the contract harness

```bash
python3 stub-server/test_poll_cycle.py
```

Exit code `0` means the full poll contract holds — setup, the bearer-token
auth gate, the display-response shape, download, SHA-256 and exact-size
integrity verification, hash-skip, a served-image change, telemetry, the
log endpoint, two hand-built malformed-response rejections, and failure
classification against a stopped server. Any non-zero exit means some part
of that contract broke; the printed `PASS`/`FAIL` lines say which check.

The harness picks its own free port (by binding port 0 and reading back
the assignment), so it can be run at any time — including while the
long-lived server from the section above is still up on its own port.

## Capturing telemetry

Every poll to `GET /device/v1/display` and `POST /device/v1/log` prints the
device's `X-Battery-Mv`, `X-Rssi`, `X-Fw-Version` and `X-Boot-Reason`
telemetry headers to stdout. Plan 01-07 consumes this stdout stream as its
battery measurement channel. For any long run, redirect the server's output
to a file so that record isn't lost when the terminal closes:

```bash
python3 stub-server/byos_server.py --image /tmp/panel.bin --port 8642 --sleep 300 \
  > /tmp/byos_server.log 2>&1 &
```
