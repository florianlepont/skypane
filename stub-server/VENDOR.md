# stub-server — Vendor Provenance

## `byos_server.py`

- **Upstream repository:** https://github.com/flightportrait/frame
- **Pinned commit:** `ce3335fc5e566bcc6ccd29966ec39bf5c5318f12`
- **Upstream path:** `examples/byos_server.py`
- **Licence:** Apache-2.0. Original copyright/SPDX headers preserved verbatim
  at the top of the file:
  ```
  # SPDX-FileCopyrightText: 2026 YODE PTE LTD
  # SPDX-License-Identifier: Apache-2.0
  ```
  Full licence text: https://github.com/flightportrait/frame/blob/ce3335fc5e566bcc6ccd29966ec39bf5c5318f12/LICENSE

### Local modifications

The file was copied byte-for-byte from the pinned commit first, then exactly
one local change was made — everything else (endpoint behaviour, argument
names, response shapes, telemetry printing) is untouched:

1. **Added a `--state-dir` flag.** Upstream hardcodes the persisted-token
   state file (`byos_state.json`) next to the script
   (`os.path.dirname(os.path.abspath(__file__))`). This repository adds a
   `--state-dir` CLI flag (default: unchanged — the script's own directory)
   so `stub-server/test_poll_cycle.py` can point the state file at its own
   temporary directory. This isolates the harness's issued tokens from the
   `byos_state.json` the long-running instance used by the hardware bring-up
   plans (01-05, 01-06, 01-07) depends on, so a test run never rewrites state
   a real device is relying on.

   Concretely: `STATE_PATH` (a module-level constant upstream) became a
   `state_path(state_dir)` function, and `load_state()` / `save_state()`
   gained a `state_dir` parameter threaded through from `args.state_dir`.
   The docstring was extended to mention the new flag and to note this
   modification; no endpoint, response field, status code, or telemetry
   print statement was touched.

**Everything else is verbatim**, including: the three endpoint
implementations (`POST /device/v1/setup`, `GET /device/v1/display`,
`POST /device/v1/log`, `GET /img/*`), the `--image`/`--port`/`--secret`/
`--sleep` flags, the bearer-token issuance and check logic, the
`X-Fw-Version`/`X-Boot-Reason`/`X-Rssi`/`X-Battery-Mv` telemetry stdout
print (`log_telemetry()` — this is the measurement channel plan 01-07
depends on and was not reformatted, suppressed, or removed), and the
960,000-byte panel-size check.

### Disagreements with PROTOCOL.md

None found. The vendored server's field shapes (`image_hash` as
`"sha256:" + hex`, `sleep_s`, `reset`, `firmware: null`, the 422/401 status
codes on `/setup`, the 401 gate on `/display` and `/log`) match
`docs/PROTOCOL.md` §2 at the pinned commit exactly — verified directly by
`stub-server/test_poll_cycle.py`, which asserts every field rule in that
section and passes 15/15 against this file unmodified in behaviour.

## `make_test_panel.py`

Original to this repository — **not vendored**. Implements the
`docs/PROTOCOL.md` §1 panel byte format (960,000 bytes, 1600×600-byte rows,
2 px/byte with the left pixel in the high nibble, the six legal Spectra 6
nibble codes) as a deterministic generator with no upstream analog.

## `test_poll_cycle.py`

Original to this repository — **not vendored**. A host-side end-to-end
contract harness asserting the full device-protocol contract described in
`docs/PROTOCOL.md` §§1, 2, 3 and 5 at the pinned commit above. No upstream
equivalent exists (flightportrait/frame's own contract test is a closed-source
reference simulator, per `docs/PROTOCOL.md`'s own text).

## Re-pinning

A future re-pin of `byos_server.py` to a newer upstream commit is a
deliberate, reviewable act: diff the new upstream file against the version
recorded here, re-apply the `--state-dir` modification, update the pinned
commit hash above, and re-run `stub-server/test_poll_cycle.py` to confirm the
contract still holds.
