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

2. **Added an `--image-url-scheme` flag.** Upstream hardcodes the scheme
   of the `image_url` field returned by `GET /device/v1/display` to the
   literal `"http://"`, built from the request's `Host` header. Phase 2
   of this project deploys this script behind Caddy, which terminates
   TLS in front of it (`docs/PROTOCOL.md`'s deployment guidance and
   `.planning/phases/02-plane-view-end-to-end-slice/02-RESEARCH.md`'s
   Common Pitfall 2 both flag that an unconditional `http://` here means
   the frame's metadata poll travels over TLS but its 960,000-byte panel
   download — and the telemetry headers riding on that request — travel
   in plaintext, a silent downgrade). This repository adds an
   `--image-url-scheme` CLI flag, `choices=["http", "https"]`, that
   selects the scheme used to build `image_url` in that response.

   The default is **`http`**, unchanged from upstream's effective
   behaviour, deliberately — not `https` — because Phase 1 plans
   01-06/01-07/01-08 still drive a real device against this script
   running locally, unproxied, on the LAN, and an unconditional `https`
   default would break that flow the moment hardware exists. The Phase 2
   systemd unit (`deploy/skypane-byos.service`) passes
   `--image-url-scheme https` explicitly for the Caddy-fronted
   production deployment, closing the downgrade gap where it actually
   matters.

   Concretely: the `do_GET` `/device/v1/display` branch builds
   `image_url` from `self.args.image_url_scheme` instead of the
   hardcoded `"http://"` string literal. No other endpoint, response
   field, status code, or telemetry print statement was touched — the
   host portion of `image_url`, the `/img/*.bin` digest path, and every
   other field in the response are byte-identical to before this change
   for any given scheme.

3. **Added DEVICE-04 `X-Battery-Mv` validation/persistence** (plan 05-02).
   Upstream's `log_telemetry()` already echoes the `X-Battery-Mv` header to
   stdout, but never validates or persists it — nothing downstream ever
   read a real battery reading. This repository adds `parse_battery_mv()`
   (strict ASCII-digit-only, 1–5 chars, `BATTERY_MV_MIN..BATTERY_MV_MAX`
   = `1..10000` inclusive — the `"0"` PROTOCOL.md unknown sentinel and
   every other malformed/hostile value return `None` and are silently
   ignored, never persisted, never fatal) and `save_battery_state()`
   (atomic tmp-write-then-`os.replace()`, mirroring `save_state()`'s own
   pattern) writing a new file, `<state_dir>/battery_state.json`
   (`{"battery_mv": int, "received_at": float}`). The persistence hook
   sits in the `do_GET` `/device/v1/display` branch, immediately after
   `log_telemetry()` and therefore strictly after the pre-existing
   `bearer_ok()` gate, so an unauthenticated poll can never write it.
   This file is written **only** by this script — `server/poll_loop.py`
   reads it and never writes it (single-writer discipline, avoiding a
   lost-update race between the two independently-scheduled processes).
   No existing endpoint, response field, status code, or telemetry print
   statement was touched by this change.

4. **Added a read-only `led_enabled` lookup against the shared
   `device_config.json` document** (phase 06.2). Upstream has no concept of
   a per-device bring-up-LED setting at all; this repository's own
   pre-06.2 state hardcoded the `GET /device/v1/display` response's
   `led_enabled` field to the literal `True`, with a comment documenting
   that there was no store, endpoint, or web control behind it (DEVICE-05).
   Phase 06.2 closed that gap on the companion side — `companion/app.py`'s
   Config page now writes a genuine, user-settable `led_enabled` value via
   `server/device_config.py`'s `save_device_config()` — and this change is
   this vendored file's read half of that same feature.

   Concretely: this repository adds `device_config_path(state_dir)` (mirrors
   `state_path()`/`battery_state_path()`) and `read_led_enabled(state_dir)`
   (a best-effort, never-raising read: a missing file, an unreadable file,
   a malformed document, a non-dict document, or a present-but-non-bool
   `led_enabled` value all degrade to `True`, matching the firmware's own
   fail-open contract in `firmware/main/api_client.c`). The `do_GET`
   `/device/v1/display` branch is the single call site — it now assigns
   `read_led_enabled(self.args.state_dir)` to the response dict's
   `led_enabled` key instead of the hardcoded literal. The shared channel
   is the same `--state-dir` this file already accepts (local modification
   1) — both processes must be pointed at the same directory for a saved
   value to be observed, exactly like `battery_state.json`'s existing
   producer/consumer relationship with `server/poll_loop.py`.

   A deliberate decision **not** made here: this file does not import
   `server.device_config` (the project's own module that defines the JSON
   key's shape and default) to read or validate that key. The read logic
   above is a small, self-contained, independent reimplementation of just
   the `led_enabled` half of `server.device_config.normalise_led_enabled()`.
   This keeps the module docstring's stdlib-only claim true and avoids
   coupling a deliberately-frozen vendored file to actively-changing
   project internals — the same reasoning that already kept local
   modifications 1-3 free of any project-package import.

   No other endpoint, response field, status code, or telemetry print
   statement was touched by this change.

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
recorded here, re-apply all **four** local modifications (`--state-dir`,
`--image-url-scheme`, the DEVICE-04 `X-Battery-Mv` validation/persistence,
and this LED read), update the pinned commit hash above, and re-run
`stub-server/test_poll_cycle.py` to confirm the contract — including both
scheme checks — still holds.
