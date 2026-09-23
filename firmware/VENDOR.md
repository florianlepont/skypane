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
| `partitions.csv` | `partitions.csv` | no | Plan `34-04` (FW-08/D-34-02) added one partition, `secret` (NVS type, offset `0x13000`, size `0x3000` — three 4 KB pages, the NVS partition-generator's practical minimum), in the existing free gap between `nvs_keys` and `factory`. Every other partition (`nvs`, `otadata`, `phy_init`, `nvs_keys`, `factory`, the `ota_0`/`ota_1` app slots) is byte-identical to upstream/the pre-phase-34 layout. |
| `sdkconfig.defaults` | `sdkconfig.defaults` | no | `CONFIG_FP_API_BASE` changed from upstream's production URL to the reserved placeholder `https://example.invalid` (quick `260923-9fe`; SkyPane never reads it — see `main/Kconfig.projbuild`). Bluetooth disabled (`CONFIG_BT_ENABLED=n`, `CONFIG_BT_NIMBLE_ENABLED=n`) — Phase 1 implements no BLE provisioning; hardcoded credentials in a gitignored `secrets.h` replace it for a device that talks only to a local stub, so carrying the BLE/NimBLE stack would inflate the image for no Phase 1 behaviour. Everything else (ESP32-S3 target, OPI PSRAM settings, the 12 KiB `app_main` stack, watchdog settings, bootloader app-rollback, and every `CONFIG_FP_*` value including the panel pin map) is untouched from upstream. **Phase 34 additions:** `CONFIG_ESP_TASK_WDT_PANIC=y` (a stuck main task now panics instead of only logging, so it turns into a classified `reset reason=task_wdt` and backoff, FW-01/FW-02); `CONFIG_SPIRAM_MEMTEST=n` (the PSRAM self-test cost is removed from every wake, FW-12); `CONFIG_LWIP_DHCP_RESTORE_LAST_IP=y` and `CONFIG_LWIP_DHCP_DOES_ARP_CHECK=n` (DHCP rejoin, D-34-03); the mbedtls default certificate bundle is replaced with a two-root custom bundle (`CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE=y`, `CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE=y`, path into `main/certs/`) containing only ISRG Root X1 and ISRG Root X2, the two roots the VPS's Let's Encrypt chain (`deploy/Caddyfile`) actually uses, replacing the full default trust store (D-34-04); `CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS=y` and `CONFIG_ESP_HTTP_CLIENT_ENABLE_CUSTOM_TRANSPORT=y` (best-effort TLS session persistence, FW-10); `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n` (no OTA exists yet — see "Operational notes" below, FW-13); a previously misleading comment about watchdog coverage was corrected. |
| `CMakeLists.txt` | `CMakeLists.txt` | no | `PROJECT_VER` changed from upstream's `"0.2.4"` to `"0.1.0-p1"` (this project has no release-tracking server yet, so it is just a human-readable phase marker) and `project(flightportrait)` renamed to `project(skypane)` (this project's own name), because the project name determines the build artifact's filename. Structure (the `cmake_minimum_required` version, the `IDF_PATH`-relative include of `project.cmake`) is otherwise the same shape as upstream. **Phase 34 (plan `34-05`, FW-15):** the hardcoded `set(PROJECT_VER "0.1.0-p1")` is gone; `PROJECT_VER` now falls back to `0.0.0-nogit` only when `firmware/build.sh` doesn't pass `-DPROJECT_VER` — `build.sh` itself resolves `git describe --tags --always --dirty` on the host (outside the container, which has no `.git` bind-mounted) and passes the result in, so every image reports the exact commit it was built from. |
| `main/epd13in3e.c` | `main/epd13in3e.c` | no | Plan `34-07` (FW-01, FW-05): `epd_init`'s GPIO/SPI setup no longer calls `ESP_ERROR_CHECK` — each failure now returns `ESP_FAIL` through the function's own `esp_err_t` path (freeing the SPI bus first if `spi_bus_add_device` failed after `spi_bus_initialize` succeeded), and `epd_sleep` tracks two independent "what actually got set up" flags so it can never touch an uninitialised SPI handle or an unconfigured GPIO regardless of which setup call failed. `busy_wait()`'s poll loop and `send_half()`'s periodic yield now feed the task watchdog (`fp_wake_feed()`, `wake_guard.h`). `epd_blit()` now checks its POF busy-wait's timeout and returns `ESP_FAIL` (mapping to `step=blit`) instead of silently ignoring it. The 800 µs per-row `esp_rom_delay_us` pacing is unchanged — see "Operational notes" below for why. |
| `main/epd13in3e.h` | `main/epd13in3e.h` | yes | none |
| `main/panel.c` | `main/panel.c` | no | Plan `34-07` (FW-12): the refresh-spacing wait (`FP_PANEL_DRAW_AFTER_WAIT`) now calls `fp_wake_light_sleep_s()` (`wake_guard.h`) instead of `vTaskDelay()`, so the device light-sleeps (radio and panel both already down at this point) instead of staying fully awake for up to `CONFIG_FP_MAX_GUARD_WAIT_S` seconds. |
| `main/panel.h` | `main/panel.h` | yes | none |
| `main/panel_guard.c` | `main/panel_guard.c` | yes | none |
| `main/panel_guard.h` | `main/panel_guard.h` | no | Doc comment only (commit `503e701`): the rationale for the refresh-spacing guard was rewritten to match the verified GDEP133C02 datasheet finding (no documented refresh-rate or endurance limit; refresh at least every 24 h). No declaration changed. |
| `tests/test_panel_guard.c` | `tests/test_panel_guard.c` | yes | none |
| `sdkconfig.ee02.defaults` | `sdkconfig.ee02.defaults` | no | Appended two SkyPane blocks after the upstream content, which is otherwise untouched: battery-sense pins (`CONFIG_FP_PIN_BATTERY_ADC`, `CONFIG_FP_PIN_BATTERY_ADC_EN`, plan `05-03`) and the bring-up LED (`CONFIG_FP_PIN_LED`, `CONFIG_FP_LED_ACTIVE_LOW`, plan `260827-wo4`). |
| `main/Kconfig.projbuild` | `main/Kconfig.projbuild` | no | Top-level menu renamed from "FlightPortrait" to "SkyPane", and `FP_API_BASE`'s default changed from upstream's production URL to the reserved placeholder `https://example.invalid`, with help text saying SkyPane never reads it (quick `260923-9fe`). Trimmed to the options this project actually compiles against: kept `FP_HW_REV`, the full 8-pin panel-pins menu, and the panel menu (`FP_MIN_REFRESH_SPACING_S`, `FP_MAX_GUARD_WAIT_S`). Removed `FP_PROVISION_TIMEOUT_S` (BLE provisioning timeout) and `FP_FACTORY_PREP` (factory-prep boolean) — neither has any code behind it in this project. Retained the "E1004 controls" menu (`FP_PIN_KEY0/1/2` plus the two hold-time options) with a new comment explaining why it stays without a compiled consumer this phase — the pin values are measured hardware fact from a real EE02 key-sweep (see `sdkconfig.ee02.defaults`), and losing them would mean re-deriving that measurement when Phase 4 (DEVICE-01) wires up the button handler. **Phase 34 (plan `34-04`, FW-02/FW-07/FW-10/FW-13):** the orphan `FP_API_BASE`/`FP_DEV_PROVISION_SECRET` options (no compiled reader) were removed; four new options were added to the top-level menu — `SKYPANE_ALLOW_HTTP` (dev-only https-off switch, default `n`), `SKYPANE_WAKE_BUDGET_S` (180–900 s, default 300, the whole-wake deadline), `SKYPANE_TLS_SESSION_PERSIST` (default `y`, depends on `ESP_TLS_CLIENT_SESSION_TICKETS`) and the `SKYPANE_FAULT_INJECT` choice (`NONE`/`PANIC`/`TASK_WDT`/`INT_WDT`/`SLOW_WAKE`, default `NONE`, bench-only — see `main/fault_inject.c` below). |
| `main/wifi.c` | `main/wifi.c` | no | Credential source changed from NVS (written by a BLE provisioning flow this project doesn't compile) to the `SKYPANE_WIFI_SSID`/`SKYPANE_WIFI_PASS` macros in the gitignored `secrets.h`. Dropped the "adopt a live Unified-Provisioning connection" early-return branch (no provisioning session exists to adopt) and the fast-connect AP-remember helper, since it wrote to NVS keys (`wifi_bssid`, `wifi_chan`) this project's trimmed `nvs_schema.h` no longer defines. Kept: the join/retry event-group logic, the SNTP time sync (a TLS prerequisite after any power loss — the device has no RTC battery), RSSI read, and `fp_wifi_stop()` (radio off before deep sleep). **Phase 34 (plan `34-08`, D-34-03):** an optional static-IP fallback, compiled in only when all four of `SKYPANE_STATIC_IP`/`_NETMASK`/`_GW`/`_DNS` are defined in `secrets.h` (a `#error` catches a partially-configured set) — stops the DHCP client, applies the fixed address/netmask/gateway/DNS via `esp_netif`, off by default since `CONFIG_LWIP_DHCP_RESTORE_LAST_IP` is the default join path. |
| `main/wifi.h` | `main/wifi.h` | no | Trimmed to the four functions the above still implements: `fp_wifi_platform_init`, `fp_wifi_connect`, `fp_wifi_rssi`, `fp_wifi_stop`. Removed the credential-store/-load and factory-reset declarations, since nothing in this project's compiled sources calls them. |
| `main/api_client.c` | `main/api_client.c` | no | Trimmed to the three endpoints and nothing more, per 01-05-PLAN.md Task 2. Removed: OTA firmware-offer handling and partition writing, pairing registration headers and signature computation, pairing acknowledgement validation, and the versioned target-blob (BYOS override) resolution chain — none of `target_contract.h`/`identity.h` is vendored. Base-URL resolution now reads `SKYPANE_API_BASE` from `secrets.h` directly instead of resolving an NVS target blob; the resolution point carries a comment recording that a plain-http base is a Phase-1-only allowance (PROTOCOL.md §5) that must not carry into the Phase 2 deployed server. Kept, with local re-implementations since `target_contract.h`'s validators aren't vendored: the display-response field validation (image hash `sha256:`+64 lowercase hex, `sleep_s` integer in 1..4294967295, `reset` boolean, non-empty http/https `image_url`), the streamed download with SHA-256 + exact-960000-byte verification before any buffer is returned to the caller, and the setup call's 64-lowercase-hex token-shape check. All four telemetry headers (`X-Battery-Mv`, `X-Rssi`, `X-Fw-Version`, `X-Boot-Reason`) are now sent unconditionally on every `/display` and `/log` call, rather than upstream's conditional `X-Rssi`; `X-Battery-Mv` now reports `fp_battery_mv()`'s real measured value — one cached `adc_oneshot` + `adc_cali` read per wake off the EE02 driver board's own factory battery-sense divider, gated by `CONFIG_FP_PIN_BATTERY_ADC_EN` and sampled on `CONFIG_FP_PIN_BATTERY_ADC`, converted through `battery_math_apply_divider()` (`main/battery_math.c`), with `0` retained as the unknown sentinel on any read failure (Phase 5's DEVICE-04, confirmed on real hardware in plan `05-03`). The ESP-TLS `crt_bundle_attach` path stays compiled in and reachable on every request, unchanged from upstream, so Phase 2's move to a real HTTPS base is a configuration change. Task 3 (01-05-PLAN.md) added the `FP_ERR_HTTP_TRANSPORT`/`FP_ERR_HTTP_STATUS`/`FP_ERR_HTTP_JSON`/`FP_ERR_IMAGE_VERIFY` sentinel returns so `state_machine.c` can log the exact Log Line Contract step token without re-deriving it from a single generic `ESP_FAIL` — a local addition upstream has no equivalent for, since upstream doesn't have a fixed log-line contract. Plan `260827-wo4` added a `led_enabled` boolean read off the `/device/v1/display` response — another local addition upstream has no equivalent for, since upstream carries no bring-up LED — parsed permissively (absent, null or wrong-typed all resolve to enabled) so an older or future server stays compatible without any risk of turning a cosmetic preference into a rejected poll. **Phase 34 (plans `34-06`/`34-09`, FW-03/FW-04/FW-05/FW-07/FW-08/FW-10/FW-13/FW-14):** every inline validation rule was deleted in favour of calling the pure `validate.c` functions (plan `34-01`) — `sleep_s`'s upper bound is now 86400 (one day, FW-04), the `reset` field is no longer read or required (FW-13), and every URL is checked against `s_allow_http` (`CONFIG_SKYPANE_ALLOW_HTTP`, FW-07). `api_base_get()` is now `esp_err_t`-returning through `fp_api_base_normalize()`, propagating `FP_ERR_CONFIG` on a rejected scheme (FW-07). `fp_api_setup()` takes no argument and reads this device's own enrolment secret via `fp_enrol_secret_load()` (`enrol_secret.h`) instead of the shared setup secret this file's macro used to hold (D-34-01/D-34-02); a 401/403 on `/display` or `/log` now erases `FP_NVS_DEVICE_TOKEN` so the next wake re-enrols with no reflash (FW-03). `fp_api_post_logs` (unused) was deleted (FW-13). One module-static `esp_http_client` handle (`session_client()`) is now reused for every request of a wake — setup, display and a same-origin download share one TCP+TLS connection instead of three — with header hygiene (`clear_request_headers()`) before each request, a retry-once-on-stale-connection rule gated on a real prior connect, and the download's read loop bounded by the wake budget (`fp_wake_checkpoint()`, FW-02/FW-10). `tls_session.c` (see "Original To This Repository") best-effort persists the TLS session across deep sleep. `esp_http_client_write`'s and `esp_http_client_fetch_headers`'s return values are now checked (FW-05). NVS access goes through `nvs_util.c` (one open→operate→commit→close helper set, FW-14) instead of hand-rolled sequences. |
| `main/api_client.h` | `main/api_client.h` | no | Trimmed to match: `fp_display_t` drops the OTA (`fw_*`) and pairing-ack fields; `fp_setup_result_t` and the pairing-registration parameter are removed from every function signature; `fp_api_base_get`/`fp_api_provisioning_target_set`/the departure-cleanup and target-phase functions are all removed, since they exist only to serve the target-blob/pairing machinery this project doesn't compile. Added `fp_api_has_token()`, a small local addition Task 3's wake loop uses to decide whether to call `fp_api_setup()` before the first `/display` poll, and the four `FP_ERR_*` step-classification sentinels described above. **Phase 34 (plans `34-06`/`34-09`):** `fp_display_t`'s `reset` field is gone (FW-13); `fp_api_setup()` no longer takes a secret argument (D-34-02); four new sentinels — `FP_ERR_HTTP_AUTH`, `FP_ERR_ENROL_REJECTED`, `FP_ERR_NO_SECRET`, `FP_ERR_CONFIG` — were added for the Log Line Contract's `auth`/`enrol`/`secret`/`config` tokens; `fp_api_release(void)` was added, torn down once per wake, logging the `http connects=…` diagnostic line and releasing the shared connection/custom TLS transport. |
| `main/nvs_schema.h` | `main/nvs_schema.h` | no | Trimmed from roughly thirty keys (BLE provisioning, possession pairing, OTA build-profile tracking, shipping mode, Security-2/QR state) to exactly the namespace plus four keys: `FP_NVS_DEVICE_TOKEN` (bearer token), `FP_NVS_IMAGE_HASH` (last blitted image hash), `FP_NVS_BACKOFF_N` (consecutive-failure counter), `FP_NVS_BOOT_COUNT` (boot counter). Carries a header comment, mirroring upstream's own, that a later phase reintroducing provisioning must migrate this namespace in place rather than renaming it. **Phase 34 (plan `34-06`, D-34-02):** gained `FP_NVS_SECRET_PARTITION` (`"secret"`) and `FP_NVS_ENROL_SECRET` (`"enrol_secret"`) — the per-device enrolment secret's key, on its own dedicated NVS partition (`partitions.csv`) rather than the default `nvs` partition, read-only from the application's side (`enrol_secret.c`, below) so neither a factory-reset of the default partition nor any application bug can erase the one copy of a device's credential. |
| `main/state_machine.c` | `main/state_machine.c` | no | Trimmed to the Phase 1 path only: connect Wi-Fi, ensure a bearer token exists (calls `fp_api_setup()` on the very first wake), poll `/device/v1/display`, hash-skip or download+verify+blit, persist the hash only after a successful blit. Removed the signed re-pair branch, the remote-reset (`disp.reset`) branch, the OTA-offer evaluation branch (`disp.has_fw`), the button-wake/QR branches, and the whole `fp_provision`/`fp_repair_*`/`fp_factory_reset_and_restart` surface — none of `buttons.h`, `errlog.h`, `identity.h`, `ota.h`, `pairing_contract.h`, `provisioning.h` or `qr_display.h` is vendored. Preserved: the deferred-vs-failed distinction on `ESP_ERR_INVALID_STATE`/`ESP_ERR_TIMEOUT` from `fp_panel_draw()`, and the ordering rule that the image hash is written to NVS only after a successful blit. **Phase 34 (plan `34-08`, FW-02/FW-10/FW-14):** `fp_wake_checkpoint()` (`wake_guard.h`) is now called after Wi-Fi connects, after setup, after the display fetch, and once more immediately before the panel draws (never after — the panel being powered is a hard exclusion); a single `step_for(esp_err_t)` table maps every `FP_ERR_*` to its Log Line Contract token, replacing two inline ternary chains (FW-14); per-stage wall-clock timings are written live into the caller's `fp_poll_timing_t` as each stage completes (see `state_machine.h` below); the hash-skip read/write goes through `nvs_util.c` instead of a hand-rolled `nvs_open`/`nvs_close` pair; one bench-only `fp_fault_inject_point()` call site sits right after Wi-Fi connects (`fault_inject.c`, below), compiled to nothing in production. |
| `main/state_machine.h` | `main/state_machine.h` | no | Trimmed to the one function this project's `app_main.c` calls, `fp_poll_once()`, with the `fp_wake_reason_t` enum and every provisioning/pairing/reset declaration removed. Added a `const char **fail_step_out` parameter — a local addition so the caller can emit the Log Line Contract's `poll fail step=` token without `state_machine.c` doing any logging of its own for that line. **Phase 34 (plan `34-08`, FW-10):** added `fp_poll_timing_t` (five `uint32_t` per-stage millisecond fields: `wifi_ms`/`setup_ms`/`display_ms`/`download_ms`/`draw_ms`) and a `timing_out` parameter on `fp_poll_once()` (NULL-safe) so `app_main.c` can log the `fp_diag`-tagged `wake timing …` diagnostic line. |
| `main/app_main.c` | `main/app_main.c` | no | Plan `01-05` (Task 3) replaces the minimal boot → NVS boot-counter → 60 s timer wake → deep-sleep body plan `01-03` shipped with the real Phase 1 wake dispatcher: init NVS, `fp_panel_on_boot()`, classify the wake reason, call `fp_poll_once()`, then either reset the failure counter and sleep for the server-supplied interval (success or deferred) or read-compute-increment the failure counter via `fp_backoff_seconds()` and sleep the backoff interval (failure) — every branch ends in `esp_deep_sleep_start()`. Follows upstream's structure (RESEARCH.md "Pattern 1") but strips the BLE provisioning dispatch, shipping-mode state machine, button actions, signed re-pair and factory-reset branches upstream's own `app_main.c` also has. The five Log Line Contract lines below are a local addition — upstream has no fixed, machine-checkable log-line contract. **Phase 34 (plan `34-08`, FW-01/FW-02/FW-06/FW-10/FW-11):** nine `_Static_assert`s tie `reset_reason.h`'s pure `FP_RST_*` mirror to the real `esp_reset_reason_t` at compile time; `fp_wake_guard_start()` (`wake_guard.h`) arms the whole-wake budget timer and the task watchdog before `nvs_flash_init()` — ahead of everything that could plausibly hang; an abnormal reset (`fp_reset_is_abnormal()`) now routes straight to a failure sleep *before* the radio ever starts (FW-01); `fp_battery_mv()` is called before Wi-Fi (FW-11); the old inline failure/success/deferred branch is replaced by two calls to `fp_sleep_decide()` (`sleep_decision.h`, FW-06); a new `fp_diag`-tagged `wake timing …` line (FW-10) and an `fp_boot`-tagged `reset reason=…` line are logged outside the frozen five-line contract, which is otherwise byte-for-byte unchanged. |

## Original To This Repository

Files in `firmware/` that are not vendored from upstream at all:

- `build.sh` — containerised `espressif/idf:v5.3.1` build invocation.
  Upstream has no equivalent single script; its README documents the
  underlying `docker run ... idf.py build` invocation and its own CI
  workflow, both of which this script is modelled on (see
  `## Re-verification` below). **Phase 34 (plan `34-05`, FW-15):** resolves
  `git describe --tags --always --dirty` on the host (the container has no
  `.git` bind-mounted) and passes it into the container build as
  `-DPROJECT_VER`; adds `SKYPANE_PROFILE=prod|dev` (selects
  `build-ee02`/`build-ee02-dev` and whether `sdkconfig.dev.defaults` is
  layered on) and `SKYPANE_FAULT=none|panic|task_wdt|int_wdt|slow_wake`
  (refused outside `dev` at exit 2, before Docker even starts); every
  `build` action wipes the local `sdkconfig` first so a stale file can
  never carry a dev/fault option into a production image.
- `tests/run_host_tests.sh` — discovers every `test_<name>.c` in
  `tests/` by naming convention (compiling it against the matching
  `main/<name>.c`) and runs it with the system `cc`, instead of a
  hand-maintained list of suites (plan `34-01`) — a suite whose
  `main/<name>.c` counterpart is missing fails loudly rather than being
  silently skipped, and a test needing more than its one matching
  implementation file names the extras in a `HOST_TEST_DEPS:` comment.
  Upstream instead lists the equivalent `cc` command per test file in a
  comment at the top of each test and runs them from a loop inside its
  own CI workflow; this script is this repository's single entry point
  for the same behaviour, now covering eight suites (`test_api_base`,
  `test_backoff`, `test_battery_math`, `test_panel_guard`,
  `test_reset_reason`, `test_sleep_decision`, `test_validate`,
  `test_wake_deadline`).
- `.gitignore` — this repository's own ignore rules.
- `main/CMakeLists.txt` — this task's own component registration; switched
  from a hand-maintained `SRCS` list to `SRC_DIRS "."` (plan `34-01`), so
  every new `main/*.c` file compiles into the image automatically on a
  CMake reconfigure, with no edit here. **Phase 34 (plan `34-09`, FW-10):**
  `tcp_transport` added to `REQUIRES` for `tls_session.c`'s and
  `api_client.c`'s `esp_transport_ssl_*` calls.
- `main/secrets.example.h` — a new file this project introduces; upstream
  has no equivalent because its credentials arrive at runtime through BLE
  provisioning rather than a compiled-in header. Committed template for
  `main/secrets.h` (gitignored — see `firmware/.gitignore`), defining the
  `SKYPANE_`-prefixed macros `wifi.c`/`api_client.c` read:
  `SKYPANE_WIFI_SSID`, `SKYPANE_WIFI_PASS`, `SKYPANE_API_BASE`, and the
  optional dev-only `SKYPANE_API_BASE_DEV`. The per-device enrolment
  secret is not one of these macros — it is written directly into the
  device's own `secret` NVS partition by `firmware/provision.sh`
  (`main/enrol_secret.h`), so the compiled image is identical for every
  device. **Phase 34 (plan `34-08`, D-34-03):** also documents, commented
  out by default, the four optional static-IP macros
  (`SKYPANE_STATIC_IP`/`_NETMASK`/`_GW`/`_DNS`) `wifi.c`'s DHCP fallback
  reads.
- `main/battery_math.h` / `main/battery_math.c` — SkyPane-original, not
  vendored; upstream has no equivalent battery-telemetry path at all. A
  pure, saturating divider-ratio conversion (no I/O, no ESP-IDF headers,
  host-compilable with plain `cc`), mirroring `backoff.c`'s structure.
  Introduced in plan `05-03` (Phase 5, DEVICE-04). **Phase 34 (plan
  `34-02`, FW-11):** gained `battery_math_average_mv()`, a rounded mean
  over the non-negative entries of a sample array (failed reads excluded,
  not averaged toward zero), used by `battery.c`'s 8-sample read.
- `main/battery.h` / `main/battery.c` — SkyPane-original, not vendored. The
  ESP-IDF `adc_oneshot`/`adc_cali` module that enables the EE02 driver
  board's factory battery-sense divider, performs one calibrated ADC1 read
  per wake, and releases the ADC unit/calibration handle/enable line on
  every path. Introduced in plan `05-03` (Phase 5, DEVICE-04), confirmed on
  real hardware — see `hardware/BRINGUP-LOG.md`'s "ADC Battery-Sense
  Bring-Up" section. **Phase 34 (plan `34-07`, FW-11):** now takes 8
  calibrated samples per wake (`FP_BATTERY_SAMPLES`) and averages them via
  `battery_math_average_mv()` instead of a single read; the `battery
  mv=… pin_mv=…` diagnostic line's shape is unchanged, `pin_mv` is now the
  mean.
- `main/led.h` / `main/led.c` — SkyPane-original, not vendored; upstream
  carries no bring-up LED. Drives the EE02 board's diagnostic LED, gated
  by the server's `led_enabled` flag. Introduced in plan `260827-wo4`.
- `main/validate.h` / `main/validate.c` — SkyPane-original, not vendored;
  upstream inlines every one of these checks directly in `api_client.c`
  with no equivalent standalone module. Pure (no ESP-IDF, no I/O,
  host-compilable) validators for every display-response field (image
  hash, URL scheme/shape, `sleep_s` range, `led_enabled` resolution, token
  shape), the download size/SHA verdict, the SHA-256-to-hex render, and an
  HTTP-status classifier (200→OK, 401/403→AUTH, else→OTHER). Introduced in
  plan `34-01` (FW-04/FW-06/FW-07/FW-14), extended in plan `34-06`
  (`fp_http_class_t`/`fp_http_status_classify`).
- `main/reset_reason.h` / `main/reset_reason.c` — SkyPane-original, not
  vendored; upstream has no reset-reason-driven backoff at all. A pure
  mirror of `esp_reset_reason_t` (asserted equal to the real enum by
  `app_main.c`'s `_Static_assert`s) with an abnormal/healthy split and the
  Log Line Contract's honest `wake reason=` token — "power-on" only for a
  genuine power-on reset, "other" for every abnormal or unrecognised one.
  Introduced in plan `34-02` (FW-01).
- `main/wake_deadline.h` / `main/wake_deadline.c` — SkyPane-original, not
  vendored; upstream has no whole-wake time budget. Pure deadline
  arithmetic (elapsed-microseconds-vs-budget-seconds expiry, light-sleep
  slice sizing) plus `FP_WAKE_WORST_CASE_S(guard_wait_s)`, which derives
  the worst-case legitimate wake length from the timeouts already coded in
  `api_client.c`/`panel.c`/`Kconfig.projbuild` so the two numbers cannot
  silently drift apart. Introduced in plan `34-02` (FW-02).
- `main/sleep_decision.h` / `main/sleep_decision.c` — SkyPane-original, not
  vendored; upstream inlines this branch directly in its own wake
  dispatcher. The sleep-plan decision extracted from `app_main.c` into one
  pure, tested function (failure → backoff; success → server `sleep_s`;
  deferred → panel wait + 5 s when shorter; a zero server `sleep_s` is
  always treated as a failure, under every outcome, so no path can arm a
  zero-second timer wake). Introduced in plan `34-02` (FW-06).
- `main/wake_guard.h` / `main/wake_guard.c` — SkyPane-original, not
  vendored; upstream has neither a whole-wake budget nor a task watchdog
  wired to one. The `esp_timer` + `esp_task_wdt` glue arming
  `wake_deadline.c`'s pure arithmetic and the task watchdog together: the
  budget timer's callback only sets a flag (no logging, no sleep, no NVS,
  since it runs in the `esp_timer` dispatch task's own context), and every
  side effect happens later, in the main task, at a `fp_wake_checkpoint()`
  call site the caller has chosen because it is safe to sleep there.
  Introduced in plan `34-07` (FW-01/FW-02).
- `main/nvs_util.h` / `main/nvs_util.c` — SkyPane-original, not vendored;
  upstream hand-rolls each `nvs_open()`/`nvs_close()` pair at its own call
  site. The one open→operate→commit(writes only)→close NVS helper set the
  whole project shares (`api_client.c`, `state_machine.c`,
  `enrol_secret.c`); none of the four functions call `ESP_ERROR_CHECK` —
  an NVS failure degrades to an `esp_err_t` return, never a crash.
  Introduced in plan `34-06` (FW-14).
- `main/enrol_secret.h` / `main/enrol_secret.c` — SkyPane-original, not
  vendored; upstream has no per-device secret (BLE provisioning instead).
  Read-only access to `skypane/enrol_secret` on the dedicated `secret` NVS
  partition — never writes or erases it, since that would destroy the one
  copy of the device's credential; a missing/invalid secret is a
  provisioning defect the caller logs guidance for
  (`firmware/provision.sh`), not something this module repairs by
  erasing. Introduced in plan `34-06` (D-34-01/D-34-02).
- `main/fault_inject.h` / `main/fault_inject.c` — SkyPane-original, not
  vendored; upstream has no fault-injection hook. Four bench-only fault
  triggers (`abort()`; a task-watchdog hang that never feeds the
  watchdog; an interrupt-watchdog spin with interrupts disabled; a
  past-budget slow wake that keeps checkpointing so only the wake budget,
  never the task watchdog, ends it) selected by
  `CONFIG_SKYPANE_FAULT_INJECT_*`; `fault_inject.c`'s entire body —
  including the `SKYPANE-FAULT-INJECT` marker string itself — is compiled
  out of the translation unit when `CONFIG_SKYPANE_FAULT_INJECT_NONE` is
  selected, the only production-legal value (`check_production_config.sh
  built` greps a finished binary for the marker and fails if found).
  Introduced in plan `34-08` (bench verification of FW-01/FW-02).
- `main/tls_session.h` / `main/tls_session.c` — SkyPane-original, not
  vendored; upstream reconnects fresh on every request. Best-effort TLS
  session persistence across deep sleep: serializes `esp_tls`'s session
  ticket into RTC memory via `mbedtls_ssl_session_save`/`_load`, reaching
  a private `tcp_transport` field through a struct mirror pinned to
  exactly ESP-IDF v5.3.1's layout — every public function is a no-op
  outside that exact pinned version plus
  `CONFIG_SKYPANE_TLS_SESSION_PERSIST`/`CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS`,
  so a device on that path just pays a full handshake every wake,
  unchanged from before this plan. Introduced in plan `34-09` (FW-10).
- `tests/test_battery_math.c` — SkyPane-original host test for
  `battery_math.c`, introduced in plan `05-03`; extended in plan `34-02`
  with `battery_math_average_mv()` cases.
- `tests/test_reset_reason.c`, `tests/test_wake_deadline.c`,
  `tests/test_sleep_decision.c` — SkyPane-original host tests for the
  three plan-`34-02` pure modules above, discovered automatically by
  `run_host_tests.sh`'s naming convention.
- `tests/test_validate.c` — SkyPane-original host test for `validate.c`,
  introduced in plan `34-01`, extended in plan `34-06` with the HTTP-status
  classifier cases.
- `provision.sh` — SkyPane-original, not vendored; upstream provisions
  credentials over BLE instead. Host script (Python `secrets` for random
  generation) that writes a per-device secret into the device's dedicated
  `secret` NVS partition over USB — parsing the partition's offset/size
  from `partitions.csv` at runtime, building the NVS image inside the
  pinned container, writing only that partition's byte range with host
  `esptool`, verifying by read-back `cmp` — then prints the MAC and
  `sha256(secret_hex)` registry line, never the secret itself.
  `--dry-run <mac>` previews the same output with no hardware access.
  Introduced in plan `34-05` (D-34-02).
- `sdkconfig.dev.defaults` — SkyPane-original, not vendored; upstream has
  one build profile. Dev-only sdkconfig overlay layered onto
  `sdkconfig.defaults` only under `SKYPANE_PROFILE=dev` — currently one
  line, `CONFIG_SKYPANE_ALLOW_HTTP=y` — never referenced by the production
  build invocation. Introduced in plan `34-04` (FW-07/D-34-04).
- `main/certs/isrg-root-x1.pem` / `main/certs/isrg-root-x2.pem` —
  SkyPane-original, not vendored; upstream uses the default mbedtls trust
  store. ISRG Root X1 and ISRG Root X2, the two roots the VPS's Let's
  Encrypt chain (`deploy/Caddyfile`) actually uses, downloaded from
  letsencrypt.org and fingerprint-verified against both that source and
  an independent second source (`curl.se/ca/cacert.pem`, Mozilla's own CA
  distribution) — the sole contents of `sdkconfig.defaults`'s custom
  mbedtls certificate bundle, replacing the full default trust store.
  Introduced in plan `34-04` (D-34-04). See "Operational notes" below for
  what a CA root rotation means operationally.
- `tests/check_production_config.sh` — SkyPane-original, not vendored;
  upstream has no equivalent single check. Two-mode checker: `static`
  (no Docker — checks the committed `sdkconfig.defaults`,
  `partitions.csv` and `main/certs/` before a build even runs) and
  `built <dir>` (checks a finished `idf.py build`'s generated `sdkconfig`
  and image — https-only, no `SKYPANE-FAULT-INJECT` marker in the binary,
  a real firmware version). Introduced in plan `34-04`, run in
  `.github/workflows/firmware.yml` before and after the build.
- `tests/check_log_contract.sh` — SkyPane-original, not vendored; upstream
  has no fixed log-line contract to check. Proves the five Log Line
  Contract format strings are still byte-identical in the C sources that
  emit them, and that every `poll fail step=` token the code can actually
  produce is documented in this file's Log Line Contract table below.
  Introduced in plan `34-10` (this plan), run in
  `.github/workflows/firmware.yml` before the build.

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
| Failed poll | `poll fail step=<wifi\|http\|status\|json\|download\|verify\|blit\|auth\|enrol\|secret\|config\|reset\|deadline> backoff_n=<n> sleep_s=<n>` |
| Successful blit | `blit ok bytes=960000 sha256_ok=1` |
| Immediately before sleeping | `sleep enter sleep_s=<n>` |

The contract deliberately contains **no credential values** — not the
bearer token, not the Wi-Fi password, not the per-device enrolment
secret. A credential appearing in a captured log is a firmware logging
defect to fix, not merely something to redact before committing.

The `poll fail step=` token list has grown twice since Phase 1's original
three values (`wifi`, `http`, `status`): plan `01-05` (Task 3) added the
image-verification/download/blit path, and this phase's device-side work
(plans `34-06` and `34-08`) added six more. The full set a device can emit
today, in the exact spelling the code uses, is
`wifi|http|status|json|download|verify|blit|auth|enrol|secret|config|reset|deadline`
(13 values; `firmware/tests/check_log_contract.sh` proves every one the
code can actually produce is listed here). What each of the six phase-34
additions means:

- **`auth`** — the server answered 401/403 on an authenticated call
  (`/display` or `/log`); the device erased its stored bearer token before
  sleeping and re-enrols on the next wake (FW-03, D-34-01).
- **`enrol`** — `POST /device/v1/setup` was refused (401/403): the
  presented per-device secret was wrong, or this MAC is not registered on
  the server. The device's existing token, if any, is left untouched
  (D-34-01).
- **`secret`** — no valid enrolment secret was found in this device's
  dedicated `secret` NVS partition. This is a provisioning defect, not a
  transient failure: run `firmware/provision.sh` against the device
  (D-34-02).
- **`config`** — the compiled or dev-override API base URL was rejected by
  this build's scheme policy — most commonly, an `http://` base compiled
  into a production image, which requires `https://` (FW-07, D-34-04).
- **`reset`** — the previous wake ended in a panic, a watchdog reset, a
  brownout, a power glitch or a CPU lockup instead of reaching deep sleep
  on its own; this wake backs off without the radio ever starting (FW-01).
- **`deadline`** — the whole-wake budget (`CONFIG_SKYPANE_WAKE_BUDGET_S`,
  default 300 s) expired before the poll finished — a hang the 60 s task
  watchdog either didn't catch or isn't the right mechanism for (FW-02).

## Diagnostic lines (outside the contract)

None of the lines below are part of the frozen five-line contract above —
`hardware/logtools.py` does not grep for any of them, and changing their
shape does not break a hardware verification plan. They are documented
here so a captured serial log can still be read without re-deriving what
each tag means, and so their tokens are never accidentally reused for
something the contract itself needs.

| Tag | Line shape | Meaning |
|---|---|---|
| `fp_boot` | `reset reason=<label>` | The classified reset reason (`fp_reset_label()`, `reset_reason.c`), logged once per boot immediately after the `wake reason=` contract line and before the abnormal-reset backoff check runs. Introduced in plan `34-08` (FW-01). |
| `fp_diag` | `wake timing total_ms=<n> wifi_ms=<n> setup_ms=<n> display_ms=<n> download_ms=<n> draw_ms=<n>` | Per-stage wall-clock breakdown of the whole wake, logged immediately before every `sleep enter` line. A stage this wake never reached (for example every field on a deadline-triggered sleep that never got past Wi-Fi) reads 0. Introduced in plan `34-08` (FW-10). |
| `fp_api` | `http connects=<n> first_connect_ms=<n> tls_offered=<0\|1> tls_saved_len=<n>` | Logged once per wake, in `fp_api_release()`: how many real TCP+TLS connects this wake made (`1` means the keep-alive connection held for the whole wake), how long the first one took, and whether a saved TLS session was offered to the transport / how large the session this wake saved was. Introduced in plan `34-09` (FW-10). |
| `fp_tls` | `offering a saved TLS session (<n> bytes)` | A session saved by a previous wake was handed to the transport before this wake's first connect (best effort — the server may still decline the resumption and fall back to a full handshake). Introduced in plan `34-09` (FW-10). |
| `fp_tls` | `TLS session saved (<n> bytes)` | This wake's TLS session was persisted to RTC memory for the next wake to offer. Introduced in plan `34-09` (FW-10). |
| `fp_batt` | `battery mv=<pack> pin_mv=<pin>` | The battery reading, taken before Wi-Fi starts (FW-11): `pack` is the divider-converted pack voltage sent as `X-Battery-Mv`; `pin_mv` is the rounded mean of 8 calibrated ADC samples (`battery_math_average_mv()`) as of plan `34-07`, not a single sample as it was through Phase 5. Introduced Phase 5 (DEVICE-04, plan `05-03`). `hardware/logtools.py`'s `check-battery` reads captured stub/production-server stdout, not this device-console line, so the two are deliberately distinct tokens — a device-console capture can never be confused for a server-log capture. |
| `fp_fault` | `SKYPANE-FAULT-INJECT <name>` | Bench-only: logged once, right after Wi-Fi connects, only when `CONFIG_SKYPANE_FAULT_INJECT_*` selects a non-`NONE` choice; `<name>` is one of `panic`, `task_wdt`, `int_wdt`, `slow_wake`. Compiled to nothing at all — not even this string — in a production build, the only build where `CONFIG_SKYPANE_FAULT_INJECT_NONE` is legal; `check_production_config.sh built` greps a finished binary for this exact string and fails the build if it is present. Introduced in plan `34-08`. |

The contract's own no-credential rule holds for every line above too: none
of them may ever carry a bearer token, a Wi-Fi password, or an enrolment
secret.

## Operational notes

- **The TLS trust store is ISRG-only, not the default mbedtls bundle.**
  `main/certs/isrg-root-x1.pem` and `isrg-root-x2.pem` — ISRG Root X1 and
  ISRG Root X2 — are the only two roots compiled into
  `sdkconfig.defaults`'s custom certificate bundle
  (`CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE`). This is deliberate (fewer
  roots, smaller image, no ambiguity about which CA a device trusts) but
  it is also a real operational risk: if Let's Encrypt ever moves the
  VPS's issuing chain (`deploy/Caddyfile`) to a root outside this pair,
  every already-flashed frame fails every TLS handshake from that point
  on — there is no OTA path to push an updated CA bundle to a device in
  the field. Update `main/certs/` (re-verify the new root's fingerprint
  against two independent sources, as plan `34-04` did) and reflash
  *before* rotating the VPS's issuing chain, never after.
- **The 800 µs per-row busy-wait in `epd13in3e.c` is kept, not
  shortened.** The GDEP133C02 panel datasheet documents no per-row timing
  at all (`panel_guard.h`'s own rationale comment records this finding),
  so this project has no authoritative faster number to replace the
  vendor reference driver's value with; shortening it without a datasheet
  basis risks a corrupted or ghosted refresh that would only surface on
  real hardware, never in CI or a host test.
- **App rollback stays disabled**
  (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n`, `sdkconfig.defaults`, plan
  `34-04`) until this project implements OTA, which no phase so far has
  built. A bootloader that can roll an image back has nothing to roll
  back to without an OTA path that writes a second app slot — enabling
  rollback now would just be dead configuration carrying its own attack
  surface for no benefit.

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
