---
phase: 01-foundation-hardware-bring-up-ads-b-validation
plan: 05
subsystem: firmware
tags: [esp-idf, esp32-s3, wifi, http-client, mbedtls, nvs, deep-sleep, spectra6, epaper]

# Dependency graph
requires:
  - phase: 01-foundation-hardware-bring-up-ads-b-validation
    provides: "01-03's ESP-IDF scaffold, host-testable backoff.c/api_base.c, VENDOR.md provenance format"
provides:
  - "A flashable inkframe.bin built against the EE02 board profile implementing DEVICE-03's full wake->poll->download->verify->blit->sleep loop"
  - "Vendored+trimmed panel stack (epd13in3e, panel, panel_guard) and EE02 sdkconfig overlay"
  - "Vendored+trimmed network stack (api_client, wifi) reading credentials from a gitignored secrets.h"
  - "Trimmed NVS schema (namespace + 4 keys) and the rewritten app_main.c/state_machine.c wake dispatcher"
  - "The frozen five-line Log Line Contract in firmware/VENDOR.md that plans 01-06/01-07/01-08 grep"
affects: [01-06-first-light-on-real-hardware, 01-07-repeatability-and-backoff-on-hardware, 01-08-battery-time-to-depletion]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vendor-then-trim from flightportrait/frame @ce3335fc rather than hand-rolling ESP-IDF driver/protocol code"
    - "NVS-persisted failure counter (never RTC memory) driving fp_backoff_seconds()"
    - "Verify-before-blit gate: SHA-256 + exact 960000-byte check before any buffer reaches panel.c"
    - "Deferred-vs-failed distinction: panel guard's ESP_ERR_INVALID_STATE/ESP_ERR_TIMEOUT never increments backoff"
    - "Fixed, greppable Log Line Contract (5 shapes) as the hardware verification channel"

key-files:
  created:
    - firmware/main/epd13in3e.c
    - firmware/main/epd13in3e.h
    - firmware/main/panel.c
    - firmware/main/panel.h
    - firmware/main/panel_guard.c
    - firmware/main/panel_guard.h
    - firmware/sdkconfig.ee02.defaults
    - firmware/tests/test_panel_guard.c
    - firmware/main/api_client.c
    - firmware/main/api_client.h
    - firmware/main/wifi.c
    - firmware/main/wifi.h
    - firmware/main/nvs_schema.h
    - firmware/main/secrets.example.h
    - firmware/main/state_machine.c
    - firmware/main/state_machine.h
  modified:
    - firmware/main/app_main.c
    - firmware/main/Kconfig.projbuild
    - firmware/main/CMakeLists.txt
    - firmware/build.sh
    - firmware/tests/run_host_tests.sh
    - firmware/VENDOR.md

key-decisions:
  - "Vendored epd13in3e/panel/panel_guard/sdkconfig.ee02.defaults verbatim; trimmed Kconfig.projbuild to the options this project compiles, retaining the E1004-controls block unused until Phase 4"
  - "Trimmed api_client.c/wifi.c to the three device endpoints and STA join, reading credentials from INK_-prefixed macros in a gitignored secrets.h instead of NVS/BLE provisioning"
  - "Trimmed nvs_schema.h from ~30 upstream keys to exactly 4: bearer token, image hash, failure counter, boot counter"
  - "Added FP_ERR_HTTP_TRANSPORT/STATUS/JSON/FP_ERR_IMAGE_VERIFY sentinel error codes to api_client.h so state_machine.c can emit the exact Log Line Contract step token without re-deriving it from a single generic ESP_FAIL"
  - "All four telemetry headers (X-Battery-Mv, X-Rssi, X-Fw-Version, X-Boot-Reason) are sent unconditionally on every poll, rather than upstream's conditional X-Rssi; X-Battery-Mv reports a placeholder 0 pending Phase 4's ADC/fuel-gauge work"

patterns-established:
  - "Log Line Contract: 5 fixed ESP_LOGx line shapes tagged 'inkframe', frozen in firmware/VENDOR.md, that later plans grep instead of parsing prose"
  - "Base-URL resolution reads INK_API_BASE from secrets.h directly (no NVS target-blob), with an explicit Phase-1-only plain-http comment at the resolution point"

requirements-completed: [DEVICE-03]

coverage:
  - id: D1
    description: "Panel driver + EE02 board profile vendored and building: epd13in3e/panel/panel_guard, sdkconfig.ee02.defaults with USB Serial/JTAG console and 8 distinct panel pins all backed by Kconfig options"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "firmware/tests/run_host_tests.sh (panel_guard suite)"
        status: pass
      - kind: other
        ref: "bash firmware/build.sh -> firmware/build-ee02/inkframe.bin"
        status: pass
    human_judgment: false
  - id: D2
    description: "Network stack (api_client.c/.h, wifi.c/.h) implementing the three device endpoints, all four telemetry headers, streamed download with SHA-256 + exact-960000-byte verification, and credentials moved to a gitignored secrets.h"
    requirement: "DEVICE-03"
    verification:
      - kind: other
        ref: "firmware/main/api_client.c contains literal '960000' size check; git check-ignore -q firmware/main/secrets.h; git status --porcelain firmware/main/secrets.h is empty"
        status: pass
      - kind: other
        ref: "bash firmware/build.sh -> firmware/build-ee02/inkframe.bin"
        status: pass
    human_judgment: false
  - id: D3
    description: "Phase 1 wake loop (app_main.c + state_machine.c): wake classification, setup-on-first-wake, poll/hash-skip/download/verify/blit, NVS-persisted exponential backoff, deferred-vs-failed handling, and the frozen five-line Log Line Contract"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "firmware/tests/run_host_tests.sh (all three suites: backoff, api_base, panel_guard)"
        status: pass
      - kind: other
        ref: "python3 log-token scan over app_main.c+state_machine.c for all 8 contract substrings; grep fp_backoff_seconds/esp_deep_sleep_start in app_main.c"
        status: pass
      - kind: other
        ref: "bash firmware/build.sh -> firmware/build-ee02/inkframe.bin"
        status: pass
    human_judgment: false

# Metrics
duration: ~50min (Task 1 completed in a prior session interrupted by a usage-limit reset; this execution resumed at Task 2 and completed Tasks 2-3)
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 05: Full EE02 Firmware — Panel Stack, Network Stack, Wake Loop Summary

**Flashable `inkframe.bin` for the EE02 board implementing DEVICE-03's complete wake→poll→hash-skip→download→verify→blit→sleep loop, with NVS-persisted exponential backoff and a frozen five-line Log Line Contract, vendored+trimmed from flightportrait/frame @ce3335fc.**

## Performance

- **Duration:** ~50 min total across two sessions (Task 1 in a prior session interrupted by a usage-limit reset, not a logic failure; Tasks 2-3 completed in this session)
- **Completed:** 2026-08-04T22:50:09+02:00
- **Tasks:** 3/3
- **Files modified:** 24 (6 new in Task 1, 8 new/modified in Task 2, 7 new/modified in Task 3, plus VENDOR.md updated in all three)

## Accomplishments
- Vendored the native ESP-IDF dual-controller Spectra 6 panel driver and the EE02 board profile (8 distinct panel pins, USB Serial/JTAG console with UART disabled to avoid the CS/power-enable-vs-UART0 pin collision)
- Vendored and trimmed the network stack: three device endpoints, all four telemetry headers, streamed download with SHA-256 + exact-960000-byte verification before any buffer reaches the panel — credentials moved out of git into a gitignored `secrets.h` generated from a committed template
- Rewrote `app_main.c` as the Phase 1 wake dispatcher and trimmed `state_machine.c` to the walking-skeleton path (connect, enrol-if-needed, poll, hash-skip/download/verify/blit, persist), with the NVS-persisted (not RTC) exponential-backoff counter and the deferred-vs-failed distinction preserved
- Froze the five-line Log Line Contract in `firmware/VENDOR.md` so plans 01-06/01-07/01-08 can verify hardware behaviour against a captured serial log rather than prose

## Task Commits

Each task was committed atomically:

1. **Task 1: Vendor the panel stack and the EE02 board profile** - `ae7e660` (feat)
2. **Task 2: Vendor and trim the network stack, and move credentials out of git** - `d06d08e` (feat)
3. **Task 3: The Phase 1 wake loop and its machine-checkable log contract** - `f55fe05` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `firmware/main/epd13in3e.c/.h`, `firmware/main/panel.c/.h`, `firmware/main/panel_guard.c/.h` - vendored verbatim panel driver + blit orchestration + refresh-spacing guard
- `firmware/sdkconfig.ee02.defaults`, `firmware/main/Kconfig.projbuild` - EE02 board profile and its trimmed Kconfig options
- `firmware/main/api_client.c/.h` - vendored+trimmed device-protocol client; added `FP_ERR_*` step-classification sentinels for the log contract
- `firmware/main/wifi.c/.h` - vendored+trimmed STA join from `secrets.h` macros; radio off before sleep
- `firmware/main/nvs_schema.h` - namespace + exactly 4 keys (bearer token, image hash, failure counter, boot counter)
- `firmware/main/secrets.example.h` - committed credential template (new file, no upstream equivalent)
- `firmware/main/state_machine.c/.h` - vendored+trimmed Phase 1 poll/hash-skip/download/verify/blit/persist path
- `firmware/main/app_main.c` - rewritten wake dispatcher: wake classification, backoff persistence, deep-sleep entry, log contract
- `firmware/main/CMakeLists.txt` - extended `SRCS`/`REQUIRES` for the panel and network components
- `firmware/build.sh`, `firmware/tests/run_host_tests.sh` - extended for the EE02 overlay and the third (panel_guard) test suite
- `firmware/VENDOR.md` - vendored-file table rows for every new/trimmed file, plus the `## Log Line Contract` section

## Decisions Made
- Vendored verbatim wherever upstream's code is board/panel-specific and load-bearing (epd13in3e, panel, panel_guard, sdkconfig.ee02.defaults); trimmed everywhere upstream carries production-only surface (BLE provisioning, OTA, pairing, QR) this phase doesn't compile
- Kept the E1004-controls Kconfig block (`FP_PIN_KEY0/1/2` + hold-time options) without a compiled consumer, since the values are measured hardware fact from a real EE02 key-sweep that Phase 4's button handler will need
- Base-URL resolution reads `INK_API_BASE` from `secrets.h` directly rather than resolving an NVS target blob, since this phase has no provisioning flow to write one; the resolution point carries an explicit "Phase-1-only, must not carry into Phase 2" comment
- All four telemetry headers are now sent unconditionally on every poll (upstream sends `X-Rssi` conditionally); `X-Battery-Mv` reports a placeholder `0` pending Phase 4's ADC/fuel-gauge wiring

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added distinct failure-classification sentinels to api_client.h/.c**
- **Found during:** Task 3 (implementing the Log Line Contract's `poll fail step=` token)
- **Issue:** Task 2's `api_client.c` (as I originally wrote it) returned a single generic `ESP_FAIL` for both non-200 HTTP responses and malformed JSON bodies, and for both image-download transport/size failures and SHA-256 mismatches. The plan's frozen Log Line Contract requires `state_machine.c` to log one of seven distinct step tokens (`wifi`, `http`, `status`, `json`, `download`, `verify`, `blit`) on a failed poll — without finer-grained return codes from `api_client.c`, `state_machine.c` could not distinguish `status` from `json`, or `download` from `verify`, which would make 01-07's hardware fault-injection verification unable to confirm the firmware backs off for the right reason.
- **Fix:** Added `FP_ERR_HTTP_TRANSPORT`, `FP_ERR_HTTP_STATUS`, `FP_ERR_HTTP_JSON` and `FP_ERR_IMAGE_VERIFY` sentinel `esp_err_t` values to `api_client.h`, and changed the five corresponding return statements in `api_client.c` (in `small_request()`, `fp_api_setup()`'s token-shape check, `fp_api_get_display()`'s two JSON-validation branches, and `fp_api_download()`'s hash-mismatch branch) to return the correct sentinel instead of a generic `ESP_FAIL`. `state_machine.c` maps these to the exact log-contract token per call site.
- **Files modified:** firmware/main/api_client.h, firmware/main/api_client.c (both already introduced by Task 2 earlier in this same execution; amended here rather than left with an unfaithful log contract)
- **Verification:** `bash firmware/tests/run_host_tests.sh` (all three suites green) and `bash firmware/build.sh` (produces `inkframe.bin`) both pass after the change; documented in `firmware/VENDOR.md`'s updated `api_client.c`/`.h` rows
- **Committed in:** `f55fe05` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical functionality)
**Impact on plan:** Necessary to make the Log Line Contract's failure-step token faithful to what actually failed, which is exactly what plans 01-07 (repeatability + backoff on hardware) needs to verify. No scope creep — touched only the two files (already introduced earlier in this same plan's execution) that needed the extra granularity, and only in the specific return statements that were previously ambiguous.

## Issues Encountered
None - both the containerised ESP-IDF build (`bash firmware/build.sh`) and the host-side test suite (`bash firmware/tests/run_host_tests.sh`) succeeded on the first attempt for every task, including the added component REQUIRES (`esp_wifi`, `esp_netif`, `esp_event`, `esp_http_client`, `esp-tls`, `mbedtls`, `json`, `esp_app_format`, `esp_hw_support`, `heap`) needed by the network stack and wake loop.

## User Setup Required
None - no external service configuration required. `firmware/main/secrets.h` was generated locally from `secrets.example.h` with placeholder values (sufficient to build; real LAN IP/Wi-Fi credentials are only needed for plan 01-06's actual hardware flash+poll cycle) and confirmed absent from git.

## Next Phase Readiness
- A complete, flashable `firmware/build-ee02/inkframe.bin` exists implementing every clause of DEVICE-03 against the EE02 board profile — ready for plan 01-06's first-light-on-real-hardware event.
- The frozen Log Line Contract in `firmware/VENDOR.md` is the verification channel plans 01-06, 01-07 and 01-08 depend on; no further firmware changes should alter its five line shapes without updating that section deliberately.
- Before plan 01-06: fill `firmware/main/secrets.h` with the real Wi-Fi SSID/password and the laptop's actual LAN IP (see `stub-server/README.md` "Point the device at it"), since the placeholder values committed to `secrets.example.h` are not real credentials.
- No blockers. The EE02 board profile's pin assignments remain unverified on real hardware per its own upstream comment block (preserved verbatim) — plan 01-06 is the verification event for that.

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 22 files listed in Key Files (created/modified) confirmed present on disk. All 3 task commit hashes (`ae7e660`, `d06d08e`, `f55fe05`) confirmed present in `git log`.
