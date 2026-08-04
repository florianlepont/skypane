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
| `CMakeLists.txt` | `CMakeLists.txt` | no | `PROJECT_VER` changed from upstream's `"0.2.4"` to `"0.1.0-p1"` (this project has no release-tracking server yet, so it is just a human-readable phase marker) and `project(flightportrait)` renamed to `project(inkframe)` (this project's own name), because the project name determines the build artifact's filename. Structure (the `cmake_minimum_required` version, the `IDF_PATH`-relative include of `project.cmake`) is otherwise the same shape as upstream. |
| `main/epd13in3e.c` | `main/epd13in3e.c` | yes | none |
| `main/epd13in3e.h` | `main/epd13in3e.h` | yes | none |
| `main/panel.c` | `main/panel.c` | yes | none |
| `main/panel.h` | `main/panel.h` | yes | none |
| `main/panel_guard.c` | `main/panel_guard.c` | yes | none |
| `main/panel_guard.h` | `main/panel_guard.h` | yes | none |
| `tests/test_panel_guard.c` | `tests/test_panel_guard.c` | yes | none |
| `sdkconfig.ee02.defaults` | `sdkconfig.ee02.defaults` | yes | none |
| `main/Kconfig.projbuild` | `main/Kconfig.projbuild` | no | Trimmed to the options this project actually compiles against: kept `FP_API_BASE`, `FP_DEV_PROVISION_SECRET`, `FP_HW_REV`, the full 8-pin panel-pins menu, and the panel menu (`FP_MIN_REFRESH_SPACING_S`, `FP_MAX_GUARD_WAIT_S`). Removed `FP_PROVISION_TIMEOUT_S` (BLE provisioning timeout) and `FP_FACTORY_PREP` (factory-prep boolean) — neither has any code behind it in this project. Retained the "E1004 controls" menu (`FP_PIN_KEY0/1/2` plus the two hold-time options) with a new comment explaining why it stays without a compiled consumer this phase — the pin values are measured hardware fact from a real EE02 key-sweep (see `sdkconfig.ee02.defaults`), and losing them would mean re-deriving that measurement when Phase 4 (DEVICE-01) wires up the button handler. |

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
- `main/app_main.c` — the current minimal boot → NVS boot-counter → 60 s
  timer wake → deep-sleep body proves the toolchain and the deep-sleep API
  work end to end. It is **replaced** by plan `01-05` with the real
  poll → hash-skip → download → verify → blit loop; upstream's own
  `app_main.c` implements that full loop already (plus BLE provisioning
  dispatch this project does not carry), and is a read-only reference for
  that later plan rather than something copied verbatim now.
- `main/CMakeLists.txt` — this task's own component registration, with a
  `SRCS`/`REQUIRES` list trimmed to exactly what compiles today; upstream's
  equivalent file lists its full, larger source set.

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
