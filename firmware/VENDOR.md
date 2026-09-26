# firmware — Vendor Provenance

## Upstream

- **Repository:** https://github.com/flightportrait/frame
- **Pinned commit:** `ce3335fc5e566bcc6ccd29966ec39bf5c5318f12`
  (2026-07-30T21:34:28Z)
- **Licence:** Apache-2.0. Required attribution, copied verbatim from the
  upstream `NOTICE` file:
  ```
  FlightPortrait firmware
  Copyright (c) 2026 YODE PTE LTD
  ```
  Full licence text: https://github.com/flightportrait/frame/blob/ce3335fc5e566bcc6ccd29966ec39bf5c5318f12/LICENSE

## Licensing of this directory

All of `firmware/` is distributed under the Apache License 2.0 — a verbatim
copy of the upstream licence text is in [`LICENSE`](./LICENSE), and the
upstream `NOTICE` is reproduced in [`NOTICE`](./NOTICE). This satisfies the
four redistribution conditions of Apache-2.0 §4:

1. **Licence copy** — `firmware/LICENSE`.
2. **Modified files carry prominent notices** — every file marked "no" in
   the table below starts with a header naming both copyright holders and
   pointing back to this file for the list of changes.
3. **Upstream notices retained** — every vendored file keeps its original
   `SPDX-FileCopyrightText: 2026 YODE PTE LTD` line; verbatim files are
   byte-identical to the pinned commit.
4. **NOTICE** — `firmware/NOTICE`.

Files original to SkyPane (see "Original To This Repository" below) carry
`SPDX-FileCopyrightText: 2026 Florian Lepont` only. They are licensed under
Apache-2.0 as well, so the whole directory has one licence. The repository's
root AGPL-3.0 licence does **not** apply to `firmware/`.

This is a pin to an exact commit, not a branch. Picking up upstream changes
later means re-pinning deliberately: update the hash above, diff every
vendored file in the table below against the new commit, re-apply any local
changes it still needs, and re-run the host tests
(`firmware/tests/run_host_tests.sh`) before trusting the result.

## Vendored Files

| Local path | Upstream path | Verbatim? | Local changes |
|---|---|---|---|
| `main/backoff.c` | `main/backoff.c` | yes | none |
| `main/backoff.h` | `main/backoff.h` | yes | none |
| `main/api_base.c` | `main/api_base.c` | yes | none |
| `main/api_base.h` | `main/api_base.h` | yes | none |
| `tests/test_backoff.c` | `tests/test_backoff.c` | yes | none |
| `tests/test_api_base.c` | `tests/test_api_base.c` | yes | none |
| `partitions.csv` | `partitions.csv` | no | Added one partition, `secret` (NVS type, offset `0x13000`, size `0x3000`), in the existing free gap between `nvs_keys` and `factory`. Every other partition is byte-identical to upstream. |
| `sdkconfig.defaults` | `sdkconfig.defaults` | no | `CONFIG_FP_API_BASE` changed from upstream's production URL to a reserved placeholder (SkyPane never reads it — see `main/Kconfig.projbuild`). Bluetooth disabled (no BLE provisioning is compiled in; a gitignored `secrets.h` supplies credentials instead). Hardening added: task-watchdog panic on a stuck main task, the PSRAM self-test removed from every wake, DHCP rejoin tuning, a two-root ISRG-only mbedtls certificate bundle (replacing the full default trust store), best-effort TLS session tickets, and app rollback disabled (no OTA path exists to use it). Everything else (ESP32-S3 target, OPI PSRAM settings, the 12 KiB `app_main` stack, the panel pin map) is untouched from upstream. |
| `CMakeLists.txt` | `CMakeLists.txt` | no | `project(flightportrait)` renamed to `project(skypane)`. `PROJECT_VER` no longer hardcoded — `firmware/build.sh` resolves `git describe --tags --always --dirty` on the host and passes it in, so every image reports the exact commit it was built from. |
| `main/epd13in3e.c` | `main/epd13in3e.c` | no | `epd_init`'s GPIO/SPI setup no longer calls `ESP_ERROR_CHECK`; each failure now returns `ESP_FAIL` through the function's own `esp_err_t` path, freeing the SPI bus first if it was already initialised. `epd_sleep` tracks which setup steps actually completed so it can never touch an uninitialised handle. `busy_wait()`'s poll loop and `send_half()`'s periodic yield feed the task watchdog. `epd_blit()` now checks its busy-wait timeout and returns `ESP_FAIL` instead of silently ignoring it. The 800 µs per-row pacing is unchanged — see "Operational notes" below for why. |
| `main/epd13in3e.h` | `main/epd13in3e.h` | yes | none |
| `main/panel.c` | `main/panel.c` | no | The refresh-spacing wait now light-sleeps (radio and panel both already down at this point) instead of busy-waiting the full duration. |
| `main/panel.h` | `main/panel.h` | yes | none |
| `main/panel_guard.c` | `main/panel_guard.c` | yes | none |
| `main/panel_guard.h` | `main/panel_guard.h` | no | Doc comment only: the refresh-spacing guard's rationale was corrected to match the verified GDEP133C02 datasheet finding (no documented refresh-rate or endurance limit; refresh at least every 24 h). No declaration changed. |
| `tests/test_panel_guard.c` | `tests/test_panel_guard.c` | yes | none |
| `sdkconfig.ee02.defaults` | `sdkconfig.ee02.defaults` | no | Appended two SkyPane blocks after the upstream content, which is otherwise untouched: battery-sense pins and the bring-up LED pins/polarity. |
| `main/Kconfig.projbuild` | `main/Kconfig.projbuild` | no | Top-level menu renamed from "FlightPortrait" to "SkyPane", and the API base default changed to a reserved placeholder with help text saying this project never reads it. Trimmed to the options this project actually compiles against: the hardware revision choice, the full 8-pin panel-pins menu, and the panel-timing menu. Removed the BLE-provisioning timeout and factory-prep options, since neither has any code behind it. Retained the button-controls menu (pin values are measured hardware fact from a real EE02 key-sweep) with a comment explaining why it stays without a compiled consumer yet. Added four project-specific options: an HTTP-allowed dev-only switch, the whole-wake budget in seconds, TLS session persistence, and a bench-only fault-injection choice. |
| `main/wifi.c` | `main/wifi.c` | no | Credential source changed from NVS (written by a BLE provisioning flow this project doesn't compile) to macros in the gitignored `secrets.h`. Dropped the BLE-provisioning-adoption branch and the NVS-backed fast-connect helper, since this project's trimmed `nvs_schema.h` no longer defines those keys. Kept: the join/retry logic, the SNTP time sync (a TLS prerequisite after any power loss — the device has no RTC battery), RSSI read, and radio-off-before-sleep. Added an optional static-IP fallback, compiled in only when all four address macros are defined in `secrets.h`. |
| `main/wifi.h` | `main/wifi.h` | no | Trimmed to the four functions the above still implements: `fp_wifi_platform_init`, `fp_wifi_connect`, `fp_wifi_rssi`, `fp_wifi_stop`. Removed the credential-store/-load and factory-reset declarations, since nothing compiled here calls them. |
| `main/api_client.c` | `main/api_client.c` | no | Trimmed to the three endpoints this project uses. Removed: OTA firmware-offer handling and partition writing, pairing registration and signature computation, and the versioned target-blob (BYOS override) resolution chain. Base-URL resolution now reads a macro from `secrets.h` directly instead of resolving an NVS target blob. Kept, with local re-implementations since upstream's validators aren't vendored: display-response field validation, the streamed download with SHA-256 + exact-byte-count verification before any buffer is returned to the caller, and the setup call's token-shape check. All four telemetry headers are now sent unconditionally on every request, rather than upstream's conditional RSSI header; the battery header reports a real measured value. Every inline validation rule was replaced by calls to the pure `validate.c` functions, and every failure is classified into a Log Line Contract step token instead of a single generic error. One shared `esp_http_client` handle is reused for every request of a wake — setup, display and a same-origin download share one TCP+TLS connection — with header hygiene between requests, a retry-once-on-stale-connection rule, and the download bounded by the whole-wake budget. `tls_session.c` best-effort persists the TLS session across deep sleep. NVS access goes through `nvs_util.c` instead of hand-rolled sequences. A 401/403 on an authenticated call now erases the stored bearer token so the next wake re-enrols with no reflash. |
| `main/api_client.h` | `main/api_client.h` | no | Trimmed to match: OTA and pairing-ack fields, structs and functions are all removed, since they exist only to serve machinery this project doesn't compile. Added `fp_api_has_token()`, `fp_api_release()`, and error sentinels for every Log Line Contract step token an authenticated call can fail on. |
| `main/nvs_schema.h` | `main/nvs_schema.h` | no | Trimmed from roughly thirty keys (BLE provisioning, pairing, OTA tracking, shipping mode, QR state) to five: the bearer token, the last blitted image hash, the failure counter and the boot counter on the default `nvs` partition, plus the per-device enrolment secret on its own dedicated `secret` partition (read-only from the application's side, so neither a factory-reset nor an application bug can erase the one copy of a device's credential). |
| `main/state_machine.c` | `main/state_machine.c` | no | Trimmed to the walking-skeleton path only: connect Wi-Fi, ensure a bearer token exists, poll the display endpoint, hash-skip or download+verify+blit, persist the hash only after a successful blit. Removed the signed re-pair branch, the remote-reset branch, the OTA-offer evaluation branch, the button-wake/QR branches, and the whole provisioning/repair/factory-reset surface. Preserved the deferred-vs-failed distinction and the ordering rule that the image hash is written only after a successful blit. Added whole-wake budget checkpoints at each stage boundary, a table mapping every failure to its Log Line Contract token, per-stage wall-clock timing, and a bench-only fault-injection call site compiled to nothing in production. |
| `main/state_machine.h` | `main/state_machine.h` | no | Trimmed to the one function this project's `app_main.c` calls, `fp_poll_once()`. Added a `fail_step_out` parameter so the caller can emit the Log Line Contract's failure line without re-deriving the step token, and a `timing_out` parameter carrying five per-stage millisecond fields for the diagnostic wake-timing line. |
| `main/app_main.c` | `main/app_main.c` | no | Replaces upstream's BLE-provisioning dispatch, shipping-mode state machine, button actions, signed re-pair and factory-reset branches with the real wake dispatcher: init NVS, classify the wake reason, call `fp_poll_once()`, then either reset the failure counter and sleep for the server-supplied interval or back off on failure — every branch ends in `esp_deep_sleep_start()`. Added: nine compile-time assertions tying the local reset-reason mirror to the real ESP-IDF enum; the whole-wake budget timer and task watchdog armed before anything that could hang; an abnormal reset routes straight to a failure sleep before the radio starts; the battery is read before Wi-Fi; a diagnostic wake-timing line and a reset-reason line outside the frozen five-line contract; and, on the 2nd+ consecutive failure of an allow-listed step, a firmware-local NO CONNECTION hold screen drawn with zero server round-trip. The `poll fail step=…` contract line itself is byte-for-byte unchanged. |

## Original To This Repository

Files in `firmware/` that are not vendored from upstream at all:

- `build.sh` — containerised `espressif/idf:v5.3.1` build invocation.
  Resolves `git describe --tags --always --dirty` on the host (the
  container has no `.git` bind-mounted) and passes it in as
  `-DPROJECT_VER`; supports a dev build profile
  (`SKYPANE_PROFILE=dev`, layers `sdkconfig.dev.defaults`) and a
  bench-only fault-injection selector, refused outside the dev profile;
  every build wipes the local `sdkconfig` first so a stale file can
  never carry a dev/fault option into a production image.
- `tests/run_host_tests.sh` — discovers every `test_<name>.c` in
  `tests/` by naming convention (compiling it against the matching
  `main/<name>.c`) and runs it with the system `cc`; a suite whose
  `main/<name>.c` counterpart is missing fails loudly, and a test
  needing more than its one matching implementation file names the
  extras in a `HOST_TEST_DEPS:` comment.
- `.gitignore` — this repository's own ignore rules.
- `main/CMakeLists.txt` — this project's own component registration,
  using `SRC_DIRS "."` so every new `main/*.c` file compiles into the
  image automatically on a CMake reconfigure.
- `main/secrets.example.h` — committed template for `main/secrets.h`
  (gitignored), defining the Wi-Fi and API-base macros `wifi.c`/
  `api_client.c` read. The per-device enrolment secret is not one of
  these macros — it is written directly into the device's own `secret`
  NVS partition by `firmware/provision.sh`, so the compiled image is
  identical for every device.
- `main/battery_math.h` / `main/battery_math.c` — a pure, saturating
  divider-ratio conversion and sample-averaging helper (no I/O, no
  ESP-IDF headers, host-compilable with plain `cc`).
- `main/battery.h` / `main/battery.c` — the ESP-IDF `adc_oneshot`/
  `adc_cali` module that enables the EE02 driver board's factory
  battery-sense divider, takes several calibrated ADC1 samples per wake
  and averages them, and releases the ADC unit/calibration handle/
  enable line on every path.
- `main/led.h` / `main/led.c` — drives the EE02 board's built-in
  diagnostic LED, gated by the server's `led_enabled` flag; a bring-up
  and reflash aid, not a shipped indicator.
- `main/validate.h` / `main/validate.c` — pure (no ESP-IDF, no I/O,
  host-compilable) validators for every display-response field, the
  download size/SHA verdict, the SHA-256-to-hex render, and an
  HTTP-status classifier.
- `main/reset_reason.h` / `main/reset_reason.c` — a pure mirror of
  `esp_reset_reason_t` (asserted equal to the real enum at compile
  time) with an abnormal/healthy split and the Log Line Contract's
  honest `wake reason=` token.
- `main/wake_deadline.h` / `main/wake_deadline.c` — pure deadline
  arithmetic (elapsed-vs-budget expiry, light-sleep slice sizing) plus
  a macro deriving the worst-case legitimate wake length from the
  timeouts already coded elsewhere, so the two numbers cannot silently
  drift apart.
- `main/sleep_decision.h` / `main/sleep_decision.c` — the sleep-plan
  decision extracted from `app_main.c` into one pure, tested function
  (failure → backoff; success → server `sleep_s`; deferred → panel wait
  plus a small margin; a zero server `sleep_s` is always treated as a
  failure).
- `main/nvs_boot.h` / `main/nvs_boot.c` — the boot-time NVS decision
  extracted into pure, tested functions: erase and retry once only on
  the two partition-layout error codes, treat every other failure as
  unusable, and sleep a fixed interval with the radio off instead of
  aborting.
- `main/wake_guard.h` / `main/wake_guard.c` — the `esp_timer` +
  `esp_task_wdt` glue arming the whole-wake budget timer and the task
  watchdog together; the budget timer's own callback only sets a flag,
  and every side effect happens later, in the main task, at a
  checkpoint the caller has chosen because it is safe to sleep there.
- `main/nvs_util.h` / `main/nvs_util.c` — the one
  open→operate→commit(writes only)→close NVS helper set the whole
  project shares; none of its functions call `ESP_ERROR_CHECK` — an NVS
  failure degrades to an `esp_err_t` return, never a crash.
- `main/enrol_secret.h` / `main/enrol_secret.c` — read-only access to
  the per-device enrolment secret on its own dedicated NVS partition —
  never writes or erases it, since that would destroy the one copy of
  the device's credential.
- `main/fault_inject.h` / `main/fault_inject.c` — four bench-only fault
  triggers (panic, task-watchdog hang, interrupt-watchdog spin, a
  past-budget slow wake) selected by a Kconfig choice; the whole
  translation unit, including its log marker string, compiles to
  nothing when the production-only `NONE` choice is selected — a
  finished-binary check greps for the marker and fails if found.
- `main/tls_session.h` / `main/tls_session.c` — best-effort TLS session
  persistence across deep sleep: serializes `esp_tls`'s session ticket
  into RTC memory via the public mbedtls save/load functions, reaching
  a private `tcp_transport` field through a struct mirror pinned to
  exactly ESP-IDF v5.3.1's layout — every public function is a no-op
  outside that exact pinned version, so a device on that path just pays
  a full handshake every wake.
- `tests/test_battery_math.c`, `tests/test_reset_reason.c`,
  `tests/test_wake_deadline.c`, `tests/test_sleep_decision.c`,
  `tests/test_nvs_boot.c`, `tests/test_validate.c` — host tests for the
  modules above, discovered automatically by `run_host_tests.sh`'s
  naming convention.
- `provision.sh` — host script (Python `secrets` for random generation)
  that writes a per-device secret into the device's dedicated `secret`
  NVS partition over USB — parsing the partition's offset/size from
  `partitions.csv` at runtime, building the NVS image inside the pinned
  container, writing only that partition's byte range with host
  `esptool`, verifying by read-back `cmp` — then prints the MAC and a
  hash of the secret, never the secret itself. `--dry-run <mac>`
  previews the same output with no hardware access.
- `sdkconfig.dev.defaults` — a dev-only sdkconfig overlay layered onto
  `sdkconfig.defaults` only under the dev build profile — currently one
  line, `CONFIG_SKYPANE_ALLOW_HTTP=y` — never referenced by the
  production build invocation.
- `main/certs/isrg-root-x1.pem` / `main/certs/isrg-root-x2.pem` — ISRG
  Root X1 and ISRG Root X2, the two roots the VPS's Let's Encrypt chain
  actually uses, downloaded from letsencrypt.org and
  fingerprint-verified against an independent second source — the sole
  contents of the custom mbedtls certificate bundle, replacing the full
  default trust store.
- `tests/check_production_config.sh` — two-mode checker: `static` (no
  Docker — checks the committed `sdkconfig.defaults`, `partitions.csv`
  and `main/certs/` before a build even runs) and `built <dir>` (checks
  a finished `idf.py build`'s generated sdkconfig and image — https
  only, no fault-injection marker in the binary, a real firmware
  version). Run in `.github/workflows/firmware.yml` before and after
  the build.
- `tests/check_log_contract.sh` — proves the five Log Line Contract
  format strings are still byte-identical in the C sources that emit
  them, and that every `poll fail step=` token the code can actually
  produce is documented in this file's Log Line Contract table below.
  Run in `.github/workflows/firmware.yml` before the build.
- `main/fault_screen.c` / `main/fault_screen.h` — pure C11, no
  ESP-IDF dependency: renders the NO CONNECTION hold screen entirely in
  firmware — an on-device integer Floyd-Steinberg dither of the same
  field the server-rendered fallback screens use, stamped with a
  committed ink mask — plus the allow-listed step/counter/already-shown
  gate deciding whether to draw at all. Wired into `main/app_main.c`'s
  failure path.
- `main/fault_screen_mask.h` — generated (never hand-edited — a server
  test proves it matches its generator byte-for-byte) 1-bpp ink mask of
  the server's own NO CONNECTION composition, produced by
  `tools/gen_fault_screen.py`.
- `tools/gen_fault_screen.py` — renders the server's NO CONNECTION
  composition flat, extracts and packs the ink mask into
  `main/fault_screen_mask.h`, and implements a Python port of
  `fault_screen.c`'s exact integer Floyd-Steinberg dither spec (one
  spec, two implementations) to produce a firmware-equivalent
  side-by-side preview PNG.

## Deliberately Not Vendored

Upstream `main/` sources this project does not carry, and why:

- **BLE Security-2 provisioning** — this project talks only to a local
  server it controls; hardcoded credentials in a gitignored `secrets.h`
  replace provisioning.
- **Runtime identity and pairing** — exists to support re-pairing a
  device against a changing cloud identity, which this project's fixed
  server target does not need.
- **OTA firmware update** — not yet built; the partition table's
  `ota_0`/`ota_1` slots are nonetheless retained unchanged (an unused
  partition costs only flash address space, and changing the layout
  later would be a migration).
- **QR display** — pulls in a component-registry dependency for a
  provisioning flow this project does not implement.
- **Button handler and view switching** — not yet wired up. The
  upstream `Kconfig.projbuild` controls block is nonetheless retained,
  so the hardware-verified EE02 key-to-GPIO mapping is not lost before
  it is needed.
- **Error-log ring** — persistent error-log draining to a `/log`
  endpoint is not one of this project's success criteria; the Log Line
  Contract covers its observability needs via the serial console
  instead.

## Log Line Contract

Five fixed line shapes, emitted with the ESP log tag `skypane` from
`main/app_main.c` and `main/state_machine.c`. Their token spelling is a
**contract, not a style choice** — captured serial logs are read against
these exact shapes, and `firmware/tests/check_log_contract.sh` greps for
them on every push.

| When | Line shape |
|---|---|
| Every wake | `wake reason=<rtc\|power-on\|button\|other> boot_count=<n>` |
| Successful poll (refreshed, unchanged, or a deferred draw — deferred is never a failure) | `poll ok sleep_s=<n> hash_skip=<0\|1>` |
| Failed poll | `poll fail step=<wifi\|http\|status\|json\|download\|verify\|blit\|auth\|enrol\|secret\|config\|reset\|deadline\|nvs> backoff_n=<n> sleep_s=<n>` |
| Successful blit | `blit ok bytes=960000 sha256_ok=1` |
| Immediately before sleeping | `sleep enter sleep_s=<n>` |

The contract deliberately contains **no credential values** — not the
bearer token, not the Wi-Fi password, not the per-device enrolment
secret. A credential appearing in a captured log is a firmware logging
defect to fix, not merely something to redact before committing.

The full set of `poll fail step=` values a device can emit today, in the
exact spelling the code uses, is
`wifi|http|status|json|download|verify|blit|auth|enrol|secret|config|reset|deadline|nvs`
(14 values; `firmware/tests/check_log_contract.sh` proves every one the
code can actually produce is listed here). What each of the six values
beyond the original `wifi`/`http`/`status` set means:

- **`auth`** — the server answered 401/403 on an authenticated call; the
  device erased its stored bearer token before sleeping and re-enrols on
  the next wake.
- **`enrol`** — the setup call was refused (401/403): the presented
  per-device secret was wrong, or this MAC is not registered on the
  server. The device's existing token, if any, is left untouched.
- **`secret`** — no valid enrolment secret was found in this device's
  dedicated `secret` NVS partition. This is a provisioning defect, not a
  transient failure: run `firmware/provision.sh` against the device.
- **`config`** — the compiled or dev-override API base URL was rejected
  by this build's scheme policy — most commonly, an `http://` base
  compiled into a production image, which requires `https://`.
- **`reset`** — the previous wake ended in a panic, a watchdog reset, a
  brownout, a power glitch or a CPU lockup instead of reaching deep sleep
  on its own; this wake backs off without the radio ever starting.
- **`deadline`** — the whole-wake budget expired before the poll
  finished — a hang the task watchdog either didn't catch or isn't the
  right mechanism for.
- **`nvs`** — NVS could not be brought up at boot. The failure counter
  lives in NVS, so this line always reads `backoff_n=0` and the device
  sleeps a fixed interval without the radio starting and without the NO
  CONNECTION screen. It is logged before the `wake reason=` line, which
  needs NVS for `boot_count`.

## Diagnostic lines (outside the contract)

None of the lines below are part of the frozen five-line contract above —
changing their shape does not break a hardware verification. They are
documented here so a captured serial log can still be read without
re-deriving what each tag means.

| Tag | Line shape | Meaning |
|---|---|---|
| `fp_boot` | `nvs unusable err=<name>` | NVS could not be brought up at boot; `<name>` is `esp_err_to_name()` of the failing call. Logged immediately before the `poll fail step=nvs` contract line. |
| `fp_boot` | `reset reason=<label>` | The classified reset reason, logged once per boot immediately after the `wake reason=` contract line and before the abnormal-reset backoff check runs. |
| `fp_diag` | `wake timing total_ms=<n> wifi_ms=<n> setup_ms=<n> display_ms=<n> download_ms=<n> draw_ms=<n>` | Per-stage wall-clock breakdown of the whole wake, logged immediately before every `sleep enter` line. A stage this wake never reached reads 0. |
| `fp_api` | `http connects=<n> first_connect_ms=<n> tls_offered=<0\|1> tls_saved_len=<n>` | Logged once per wake: how many real TCP+TLS connects this wake made (`1` means the keep-alive connection held for the whole wake), how long the first one took, and the saved-TLS-session offer/save state. |
| `fp_tls` | `offering a saved TLS session (<n> bytes)` | A session saved by a previous wake was handed to the transport before this wake's first connect (best effort — the server may still decline the resumption). |
| `fp_tls` | `TLS session saved (<n> bytes)` | This wake's TLS session was persisted to RTC memory for the next wake to offer. |
| `fp_batt` | `battery mv=<pack> pin_mv=<pin>` | The battery reading, taken before Wi-Fi starts: `pack` is the divider-converted pack voltage sent as `X-Battery-Mv`; `pin_mv` is the mean of several calibrated ADC samples. Distinct from `hardware/logtools.py`'s server-log `check-battery` token, so a device-console capture can never be confused for a server-log capture. |
| `fp_fault` | `SKYPANE-FAULT-INJECT <name>` | Bench-only: logged once when a fault-injection choice is selected. Compiled to nothing at all in a production build, the only build where the `NONE` choice is legal; a finished-binary check greps for this exact string and fails if present. |
| `fp_diag` | `fault screen drawn step=<step> backoff_n=<n>` | The NO CONNECTION hold screen was successfully blitted and the sentinel hash was written. |
| `fp_diag` | `fault screen deferred err=<name>` | The panel guard deferred the draw (not a failure) — the sentinel is deliberately NOT written, so the next failing wake retries. |
| `fp_diag` | `fault screen failed err=<name>` | The blit failed for any other reason — no sentinel written, no extra backoff change. |
| `fp_diag` | `fault screen skipped: no PSRAM` | The fault-screen framebuffer allocation failed — the fault screen is skipped for this wake and sleep proceeds normally. |

The contract's own no-credential rule holds for every line above too: none
of them may ever carry a bearer token, a Wi-Fi password, or an enrolment
secret.

## Operational notes

- **The TLS trust store is ISRG-only, not the default mbedtls bundle.**
  `main/certs/isrg-root-x1.pem` and `isrg-root-x2.pem` are the only two
  roots compiled into the custom certificate bundle. This is deliberate
  (fewer roots, smaller image, no ambiguity about which CA a device
  trusts) but it is also a real operational risk: if Let's Encrypt ever
  moves the VPS's issuing chain to a root outside this pair, every
  already-flashed frame fails every TLS handshake from that point on —
  there is no OTA path to push an updated CA bundle to a device in the
  field. Update `main/certs/` (re-verify the new root's fingerprint
  against two independent sources) and reflash *before* rotating the
  VPS's issuing chain, never after.
- **The 800 µs per-row busy-wait in `epd13in3e.c` is kept, not
  shortened.** The GDEP133C02 panel datasheet documents no per-row
  timing at all, so this project has no authoritative faster number to
  replace the vendor reference driver's value with; shortening it
  without a datasheet basis risks a corrupted or ghosted refresh that
  would only surface on real hardware, never in CI or a host test.
- **App rollback stays disabled**
  (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n`, `sdkconfig.defaults`)
  until this project implements OTA. A bootloader that can roll an
  image back has nothing to roll back to without an OTA path that
  writes a second app slot — enabling rollback now would just be dead
  configuration carrying its own attack surface for no benefit.

## Re-verification

Commands a future reader runs to confirm the vendored files still match the
pinned commit, and that the firmware still builds and its host tests still
pass:

```sh
# Confirm a vendored file is still byte-identical to the pinned commit
# (repeat per file in the "Verbatim? = yes" rows above):
curl -fsSL \
  https://raw.githubusercontent.com/flightportrait/frame/ce3335fc5e566bcc6ccd29966ec39bf5c5318f12/main/backoff.c \
  | diff - firmware/main/backoff.c

# Host-side tests (no ESP-IDF, no Docker, no hardware):
bash firmware/tests/run_host_tests.sh

# Containerised ESP-IDF build (no host toolchain install):
bash firmware/build.sh
```

The containerised build above also runs automatically in CI
(`.github/workflows/firmware.yml`), path-restricted to `firmware/**` so a
change confined to this directory triggers it without waiting on the
unrelated server/documentation pipeline (`.github/workflows/ci.yml`).
