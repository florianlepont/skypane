# firmware — Vendor Provenance

## Upstream

- **Repository:** https://github.com/flightportrait/frame
- **Pinned commit:** `ce3335fc5e566bcc6ccd29966ec39bf5c5318f12`
- **Commit authored:** 2026-07-30T21:34:28Z
- **Licence:** Apache-2.0. Required attribution, copied verbatim from the
  upstream `NOTICE` file:
  ```
  FlightPortrait firmware
  Copyright (c) 2026 YODE PTE LTD
  ```
  Full licence text: https://github.com/flightportrait/frame/blob/ce3335fc5e566bcc6ccd29966ec39bf5c5318f12/LICENSE

This is a pin to an exact commit, not a branch. A future phase intending to
pick up upstream changes must re-pin deliberately — update the hash in this
file, diff every vendored file in the table below against the new commit,
re-apply any local changes it still needs, and re-run the host tests
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
| `partitions.csv` | `partitions.csv` | yes | none |
| `sdkconfig.defaults` | `sdkconfig.defaults` | no | Bluetooth disabled (`CONFIG_BT_ENABLED=n`, `CONFIG_BT_NIMBLE_ENABLED=n`) — Phase 1 implements no BLE provisioning; hardcoded credentials in a gitignored `secrets.h` replace it for a device that talks only to a local stub, so carrying the BLE/NimBLE stack would inflate the image for no Phase 1 behaviour. Everything else (ESP32-S3 target, OPI PSRAM settings, the 12 KiB `app_main` stack, watchdog settings, bootloader app-rollback, and every `CONFIG_FP_*` value including the panel pin map) is untouched from upstream. |
| `CMakeLists.txt` | `CMakeLists.txt` | no | `PROJECT_VER` changed from upstream's `"0.2.4"` to `"0.1.0-p1"` (this project has no release-tracking server yet, so it is just a human-readable phase marker) and `project(flightportrait)` renamed to `project(skypane)` (this project's own name), because the project name determines the build artifact's filename. Structure (the `cmake_minimum_required` version, the `IDF_PATH`-relative include of `project.cmake`) is otherwise the same shape as upstream. |
| `main/epd13in3e.c` | `main/epd13in3e.c` | yes | none |
| `main/epd13in3e.h` | `main/epd13in3e.h` | yes | none |
| `main/panel.c` | `main/panel.c` | yes | none |
| `main/panel.h` | `main/panel.h` | yes | none |
| `main/panel_guard.c` | `main/panel_guard.c` | yes | none |
| `main/panel_guard.h` | `main/panel_guard.h` | yes | none |
| `tests/test_panel_guard.c` | `tests/test_panel_guard.c` | yes | none |
| `sdkconfig.ee02.defaults` | `sdkconfig.ee02.defaults` | yes | none |
| `main/Kconfig.projbuild` | `main/Kconfig.projbuild` | no | Trimmed to the options this project actually compiles against: kept `FP_API_BASE`, `FP_DEV_PROVISION_SECRET`, `FP_HW_REV`, the full 8-pin panel-pins menu, and the panel menu (`FP_MIN_REFRESH_SPACING_S`, `FP_MAX_GUARD_WAIT_S`). Removed `FP_PROVISION_TIMEOUT_S` (BLE provisioning timeout) and `FP_FACTORY_PREP` (factory-prep boolean) — neither has any code behind it in this project. Retained the "E1004 controls" menu (`FP_PIN_KEY0/1/2` plus the two hold-time options) with a new comment explaining why it stays without a compiled consumer this phase — the pin values are measured hardware fact from a real EE02 key-sweep (see `sdkconfig.ee02.defaults`), and losing them would mean re-deriving that measurement when Phase 4 (DEVICE-01) wires up the button handler. |
| `main/wifi.c` | `main/wifi.c` | no | Credential source changed from NVS (written by a BLE provisioning flow this project doesn't compile) to the `SKYPANE_WIFI_SSID`/`SKYPANE_WIFI_PASS` macros in the gitignored `secrets.h`. Dropped the "adopt a live Unified-Provisioning connection" early-return branch (no provisioning session exists to adopt) and the fast-connect AP-remember helper, since it wrote to NVS keys (`wifi_bssid`, `wifi_chan`) this project's trimmed `nvs_schema.h` no longer defines. Kept: the join/retry event-group logic, the SNTP time sync (a TLS prerequisite after any power loss — the device has no RTC battery), RSSI read, and `fp_wifi_stop()` (radio off before deep sleep). |
| `main/wifi.h` | `main/wifi.h` | no | Trimmed to the four functions the above still implements: `fp_wifi_platform_init`, `fp_wifi_connect`, `fp_wifi_rssi`, `fp_wifi_stop`. Removed the credential-store/-load and factory-reset declarations, since nothing in this project's compiled sources calls them. |
| `main/api_client.c` | `main/api_client.c` | no | Trimmed to the three endpoints and nothing more, per 01-05-PLAN.md Task 2. Removed: OTA firmware-offer handling and partition writing, pairing registration headers and signature computation, pairing acknowledgement validation, and the versioned target-blob (BYOS override) resolution chain — none of `target_contract.h`/`identity.h` is vendored. Base-URL resolution now reads `SKYPANE_API_BASE` from `secrets.h` directly instead of resolving an NVS target blob; the resolution point carries a comment recording that a plain-http base is a Phase-1-only allowance (PROTOCOL.md §5) that must not carry into the Phase 2 deployed server. Kept, with local re-implementations since `target_contract.h`'s validators aren't vendored: the display-response field validation (image hash `sha256:`+64 lowercase hex, `sleep_s` integer in 1..4294967295, `reset` boolean, non-empty http/https `image_url`), the streamed download with SHA-256 + exact-960000-byte verification before any buffer is returned to the caller, and the setup call's 64-lowercase-hex token-shape check. All four telemetry headers (`X-Battery-Mv`, `X-Rssi`, `X-Fw-Version`, `X-Boot-Reason`) are now sent unconditionally on every `/display` and `/log` call, rather than upstream's conditional `X-Rssi`; `X-Battery-Mv` reports a placeholder `0` because no ADC/fuel-gauge driver is wired up this phase (Phase 4's DEVICE-04). The ESP-TLS `crt_bundle_attach` path stays compiled in and reachable on every request, unchanged from upstream, so Phase 2's move to a real HTTPS base is a configuration change. Task 3 (01-05-PLAN.md) added the `FP_ERR_HTTP_TRANSPORT`/`FP_ERR_HTTP_STATUS`/`FP_ERR_HTTP_JSON`/`FP_ERR_IMAGE_VERIFY` sentinel returns so `state_machine.c` can log the exact Log Line Contract step token without re-deriving it from a single generic `ESP_FAIL` — a local addition upstream has no equivalent for, since upstream doesn't have a fixed log-line contract. |
| `main/api_client.h` | `main/api_client.h` | no | Trimmed to match: `fp_display_t` drops the OTA (`fw_*`) and pairing-ack fields; `fp_setup_result_t` and the pairing-registration parameter are removed from every function signature; `fp_api_base_get`/`fp_api_provisioning_target_set`/the departure-cleanup and target-phase functions are all removed, since they exist only to serve the target-blob/pairing machinery this project doesn't compile. Added `fp_api_has_token()`, a small local addition Task 3's wake loop uses to decide whether to call `fp_api_setup()` before the first `/display` poll, and the four `FP_ERR_*` step-classification sentinels described above. |
| `main/nvs_schema.h` | `main/nvs_schema.h` | no | Trimmed from roughly thirty keys (BLE provisioning, possession pairing, OTA build-profile tracking, shipping mode, Security-2/QR state) to exactly the namespace plus four keys: `FP_NVS_DEVICE_TOKEN` (bearer token), `FP_NVS_IMAGE_HASH` (last blitted image hash), `FP_NVS_BACKOFF_N` (consecutive-failure counter), `FP_NVS_BOOT_COUNT` (boot counter). Carries a header comment, mirroring upstream's own, that a later phase reintroducing provisioning must migrate this namespace in place rather than renaming it. |
| `main/state_machine.c` | `main/state_machine.c` | no | Trimmed to the Phase 1 path only: connect Wi-Fi, ensure a bearer token exists (calls `fp_api_setup()` on the very first wake), poll `/device/v1/display`, hash-skip or download+verify+blit, persist the hash only after a successful blit. Removed the signed re-pair branch, the remote-reset (`disp.reset`) branch, the OTA-offer evaluation branch (`disp.has_fw`), the button-wake/QR branches, and the whole `fp_provision`/`fp_repair_*`/`fp_factory_reset_and_restart` surface — none of `buttons.h`, `errlog.h`, `identity.h`, `ota.h`, `pairing_contract.h`, `provisioning.h` or `qr_display.h` is vendored. Preserved: the deferred-vs-failed distinction on `ESP_ERR_INVALID_STATE`/`ESP_ERR_TIMEOUT` from `fp_panel_draw()`, and the ordering rule that the image hash is written to NVS only after a successful blit. |
| `main/state_machine.h` | `main/state_machine.h` | no | Trimmed to the one function this project's `app_main.c` calls, `fp_poll_once()`, with the `fp_wake_reason_t` enum and every provisioning/pairing/reset declaration removed. Added a `const char **fail_step_out` parameter — a local addition so the caller can emit the Log Line Contract's `poll fail step=` token without `state_machine.c` doing any logging of its own for that line. |
| `main/app_main.c` | `main/app_main.c` | no | Plan `01-05` (Task 3) replaces the minimal boot → NVS boot-counter → 60 s timer wake → deep-sleep body plan `01-03` shipped with the real Phase 1 wake dispatcher: init NVS, `fp_panel_on_boot()`, classify the wake reason, call `fp_poll_once()`, then either reset the failure counter and sleep for the server-supplied interval (success or deferred) or read-compute-increment the failure counter via `fp_backoff_seconds()` and sleep the backoff interval (failure) — every branch ends in `esp_deep_sleep_start()`. Follows upstream's structure (RESEARCH.md "Pattern 1") but strips the BLE provisioning dispatch, shipping-mode state machine, button actions, signed re-pair and factory-reset branches upstream's own `app_main.c` also has. The five Log Line Contract lines below are a local addition — upstream has no fixed, machine-checkable log-line contract. |

## Original To This Repository

Files in `firmware/` that are not vendored from upstream at all:

- `build.sh` — containerised `espressif/idf:v5.3.1` build invocation. Upstream
  has no equivalent single script; its README documents the underlying
  `docker run ... idf.py build` invocation and its own CI workflow, both of
  which this script is modelled on (see `## Re-verification` below).
- `tests/run_host_tests.sh` — compiles and runs both vendored test suites
  with the system `cc`. Upstream instead lists the equivalent `cc` command
  per test file in a comment at the top of each test and runs them from a
  loop inside its own CI workflow; this script is this repository's single
  entry point for the same behaviour.
- `.gitignore` — this repository's own ignore rules.
- `main/CMakeLists.txt` — this task's own component registration, with a
  `SRCS`/`REQUIRES` list trimmed to exactly what compiles today; upstream's
  equivalent file lists its full, larger source set.
- `main/secrets.example.h` — a new file this project introduces; upstream
  has no equivalent because its credentials arrive at runtime through BLE
  provisioning rather than a compiled-in header. Committed template for
  `main/secrets.h` (gitignored — see `firmware/.gitignore`), defining the
  four `SKYPANE_`-prefixed macros this phase's `wifi.c`/`api_client.c` read:
  `SKYPANE_WIFI_SSID`, `SKYPANE_WIFI_PASS`, `SKYPANE_API_BASE`, `SKYPANE_SETUP_SECRET`.

## Deliberately Not Vendored

Upstream `main/` sources this project does not carry, and why:

- **BLE Security-2 provisioning** (`provisioning.c` and its protocol
  contract) — Phase 1's requirements are DEVICE-03 and DEVICE-05 only.
  Hardcoded credentials in a gitignored `secrets.h` replace provisioning for
  a device that talks only to a local stub server the developer controls.
- **Runtime identity and pairing** (`identity.c`, `target_contract.c`, the
  pairing bundle/ack transaction) — these exist to support re-pairing a
  device against a changing cloud identity, which this project's Phase 1
  local-stub target does not need.
- **OTA firmware update** — out of scope for Phase 1; the partition table's
  `ota_0`/`ota_1` slots are nonetheless retained unchanged (an unused
  partition costs only flash address space, and changing the layout later
  would be a migration).
- **QR display** — pulls in a component-registry dependency for a
  provisioning flow this project does not implement in Phase 1.
- **Button handler and view switching** — belongs to Phase 4's
  view-switching requirement (DEVICE-01), not Phase 1's walking skeleton.
  Note: the upstream `Kconfig.projbuild` controls block (`FP_PIN_KEY0..2`,
  the reprovision/factory-reset hold-time options) is nonetheless retained
  when plan `01-05` introduces `Kconfig.projbuild`, so the hardware-verified
  EE02 key-to-GPIO mapping is not lost before Phase 4 needs it.
- **Error-log ring** (`errlog.c`, `errlog_contract.c`) — persistent
  error-log draining to `/device/v1/log` is not one of Phase 1's success
  criteria; the log-line contract (`01-SKELETON.md`) covers Phase 1's
  observability needs via the serial console instead.

## Log Line Contract

Five fixed line shapes, emitted with the ESP log tag `skypane` from
`main/app_main.c` and `main/state_machine.c`. Their token spelling is a
**contract, not a style choice** — plans `01-06`, `01-07` and `01-08`
grep a captured serial log for these exact shapes. Changing a token here
silently breaks every hardware verification plan downstream (see
01-SKELETON.md's Invariant 8).

| When | Line shape |
|---|---|
| Every wake | `wake reason=<rtc\|power-on\|button\|other> boot_count=<n>` |
| Successful poll (refreshed, unchanged, or a deferred draw — see `state_machine.c`'s deferred-≠-failed rule) | `poll ok sleep_s=<n> hash_skip=<0\|1>` |
| Failed poll | `poll fail step=<wifi\|http\|status\|json\|download\|verify\|blit> backoff_n=<n> sleep_s=<n>` |
| Successful blit | `blit ok bytes=960000 sha256_ok=1` |
| Immediately before sleeping | `sleep enter sleep_s=<n>` |

The contract deliberately contains **no credential values** — not the
bearer token, not the Wi-Fi password, not the setup secret. A credential
appearing in a captured log is a firmware logging defect to fix, not
merely something to redact before committing.

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
