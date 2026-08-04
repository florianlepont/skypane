---
phase: 01-foundation-hardware-bring-up-ads-b-validation
plan: 03
subsystem: infra
tags: [esp-idf, esp32-s3, firmware, docker, backoff, nvs, deep-sleep, flightportrait]

# Dependency graph
requires:
  - phase: 01-foundation-hardware-bring-up-ads-b-validation (plan 02)
    provides: "Protocol contract proven by stub-server/test_poll_cycle.py — the shape firmware/main/api_client.c will implement in plan 01-05"
provides:
  - "firmware/ ESP-IDF v5.3.1 project root that builds a real ESP32-S3 binary (build-ee02/inkframe.bin) from a container, no host toolchain install"
  - "firmware/main/app_main.c minimal boot -> NVS boot-counter -> 60s timer wake -> deep-sleep body, already emitting two of the five frozen log-line-contract shapes"
  - "firmware/main/backoff.{c,h} vendored verbatim - fp_backoff_seconds(n) = min(2^n * 5min, 6h), proven by assertion across n=0..8 and n=255"
  - "firmware/main/api_base.{c,h} vendored verbatim - fp_api_base_normalize BYOS server-URL normaliser"
  - "firmware/tests/run_host_tests.sh - one command that compiles and runs both hardware-free suites with plain cc"
  - "firmware/VENDOR.md - upstream pin, per-file vendored table, trim log, deliberately-not-vendored list, re-verification commands"
affects: [01-05-full-ee02-firmware, 01-06-first-light, 01-07-repeatability-and-backoff, 01-08-battery-time-to-depletion]

# Tech tracking
tech-stack:
  added: ["ESP-IDF v5.3.1 (containerised via espressif/idf:v5.3.1)"]
  patterns:
    - "Vendor-at-pinned-commit with a VENDOR.md delta log (flightportrait/frame @ ce3335fc5e566bcc6ccd29966ec39bf5c5318f12) - same pattern stub-server/VENDOR.md already established"
    - "Containerised build, native flash: build.sh runs the whole ESP-IDF toolchain inside espressif/idf:v5.3.1 as the invoking user (no root-owned artifacts); USB flashing stays on the host for plan 01-06 because Docker Desktop's macOS USB passthrough is unreliable"
    - "Hardware-free firmware test suites compile pure-C sources with the system cc, independent of ESP-IDF, Docker, or hardware"

key-files:
  created:
    - firmware/CMakeLists.txt
    - firmware/partitions.csv
    - firmware/sdkconfig.defaults
    - firmware/build.sh
    - firmware/.gitignore
    - firmware/VENDOR.md
    - firmware/main/CMakeLists.txt
    - firmware/main/app_main.c
    - firmware/main/backoff.c
    - firmware/main/backoff.h
    - firmware/main/api_base.c
    - firmware/main/api_base.h
    - firmware/tests/test_backoff.c
    - firmware/tests/test_api_base.c
    - firmware/tests/run_host_tests.sh
  modified: []

key-decisions:
  - "sdkconfig.defaults vendored verbatim except one change: Bluetooth disabled (CONFIG_BT_ENABLED=n, CONFIG_BT_NIMBLE_ENABLED=n) because Phase 1 carries no BLE provisioning - hardcoded secrets.h credentials replace it, and the BLE/NimBLE stack would inflate the image for no Phase 1 behaviour"
  - "CMakeLists.txt's PROJECT_VER set to \"0.1.0-p1\" (a phase marker, not a release number - no server-side release tracking exists yet) and project() renamed from upstream's flightportrait to inkframe, since the project name determines the build artifact filename (build-ee02/inkframe.bin)"
  - "app_main.c's two log lines (wake reason=... boot_count=..., sleep enter sleep_s=...) already match the frozen Log Line Contract from 01-SKELETON.md, even though this is a throwaway boot-and-sleep body plan 01-05 will replace - the contract's token spelling is load-bearing for every later hardware-verification plan, so it costs nothing to get right now"
  - "Docker Desktop needed a manual `open -a Docker` during execution (was not running) and the first espressif/idf:v5.3.1 pull failed mid-transfer with \"unexpected EOF\"; a retry completed cleanly - no code or plan change required, this is Rule 3 territory but resolved by retry rather than a fix"

requirements-completed: [DEVICE-03]

coverage:
  - id: D1
    description: "Real ESP32-S3 firmware compiles from a container with no host ESP-IDF install"
    requirement: "DEVICE-03"
    verification:
      - kind: integration
        ref: "bash firmware/build.sh -> firmware/build-ee02/inkframe.bin (245248 bytes, owned by invoking user)"
        status: pass
    human_judgment: false
  - id: D2
    description: "build.sh works identically from the repository root and from inside firmware/, and passes through an idf.py subcommand (fullclean)"
    requirement: "DEVICE-03"
    verification:
      - kind: integration
        ref: "cd firmware && bash build.sh fullclean && bash build.sh (both exit 0, artifact regenerated)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The exponential backoff curve is proven by assertion across its whole domain, including the six-hour saturation point and the maximum counter value"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "firmware/tests/test_backoff.c (n=0..8, 255; asserts 300/600/1200/2400/4800/9600/19200/21600)"
        status: pass
      - kind: unit
        ref: "cc firmware/main/backoff.c firmware/tests/test_backoff.c -o /tmp/ink_tb && /tmp/ink_tb"
        status: pass
    human_judgment: false
  - id: D4
    description: "One command compiles and runs both firmware unit-test suites (backoff, api_base) with no ESP-IDF and no hardware"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "bash firmware/tests/run_host_tests.sh (names both suites, exits 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Vendored firmware sources record their upstream provenance and every local delta"
    requirement: "DEVICE-03"
    verification:
      - kind: other
        ref: "firmware/VENDOR.md (all 5 required sections present; commit hash ce3335fc5e566bcc6ccd29966ec39bf5c5318f12 present; backoff.c byte-diffed identical against a fresh upstream fetch)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 3: ESP-IDF Scaffold + Host-Testable Firmware Behaviours Summary

**A containerised ESP-IDF v5.3.1 build producing a real ESP32-S3 binary with zero host toolchain, plus the vendored exponential-backoff curve proven by assertion across its whole domain on a laptop with no hardware.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-04T17:43:00Z (approx, first upstream fetch)
- **Completed:** 2026-08-04T17:52:00Z
- **Tasks:** 3
- **Files modified:** 15 created

## Accomplishments
- `firmware/` ESP-IDF project root builds `firmware/build-ee02/inkframe.bin` via `bash firmware/build.sh`, using the pinned `espressif/idf:v5.3.1` container image with no local ESP-IDF install - retiring RESEARCH.md's Pitfall 4 (a broken host Python env silently blocking hardware day) before the EE02 kit arrives
- `fp_backoff_seconds` and `fp_api_base_normalize` vendored byte-identical from `flightportrait/frame` and proven correct by `firmware/tests/run_host_tests.sh`, which compiles and runs both suites with plain `cc` - no ESP-IDF, no Docker, no hardware
- `firmware/VENDOR.md` records the upstream pin, a per-file table of every vendored file and its local deltas, what this repository's own files are, what upstream firmware was deliberately left out (and why), and the exact commands to re-verify all of it later

## Task Commits

Each task was committed atomically:

1. **Task 1: ESP-IDF project skeleton that builds an ESP32-S3 binary from a container** - `409db54` (feat)
2. **Task 2: Vendor the two host-testable firmware behaviours and prove them** - `3358a36` (test)
3. **Task 3: Record firmware provenance and the local trim log** - `bfe908d` (docs)

_Note: Task 2 vendors both the implementation and its pre-existing upstream test in a single commit - the tests already existed upstream and assert every value in the plan's behavior list, so there was no separate RED phase to capture._

## Files Created/Modified
- `firmware/CMakeLists.txt` - ESP-IDF project root; `PROJECT_VER "0.1.0-p1"`, `project(inkframe)`
- `firmware/partitions.csv` - vendored verbatim; factory + ota_0/ota_1 + nvs + nvs_keys
- `firmware/sdkconfig.defaults` - vendored + Bluetooth disabled; ESP32-S3, OPI PSRAM, 12 KiB app_main stack, watchdog, bootloader rollback retained
- `firmware/build.sh` - containerised `espressif/idf:v5.3.1` build; resolves its own directory; runs as invoking user; optional idf.py subcommand passthrough
- `firmware/.gitignore` - build dirs, generated sdkconfig, `main/secrets.h` (added before plan 01-05 introduces the credential file)
- `firmware/main/CMakeLists.txt` - component registration; `SRCS "app_main.c" "backoff.c" "api_base.c"`; `REQUIRES nvs_flash esp_timer driver`
- `firmware/main/app_main.c` - minimal boot -> NVS boot-counter -> 60s timer wake -> deep sleep; emits the frozen `wake reason=...` and `sleep enter sleep_s=...` log lines
- `firmware/main/backoff.c` / `backoff.h` - vendored verbatim; `fp_backoff_seconds(uint8_t n)` returning `uint32_t`
- `firmware/main/api_base.c` / `api_base.h` - vendored verbatim; `fp_api_base_normalize`, `FP_API_BASE_MAX` (128)
- `firmware/tests/test_backoff.c` / `test_api_base.c` - vendored verbatim, pure-C, plain `cc`
- `firmware/tests/run_host_tests.sh` - compiles and runs both suites, prints per-suite name and a summary line
- `firmware/VENDOR.md` - upstream pin, vendored-file table, trim log, deliberately-not-vendored list, re-verification commands

## Decisions Made
- Disabled Bluetooth in `sdkconfig.defaults` (Phase 1 has no BLE provisioning; hardcoded `secrets.h` credentials replace it) - the only functional delta from the upstream `sdkconfig.defaults`
- Renamed the CMake project from upstream's `flightportrait` to `inkframe` and set a phase-marker `PROJECT_VER` of `0.1.0-p1`, since the project name fixes the build artifact's filename
- Kept `app_main.c`'s two emitted log lines in the exact frozen Log Line Contract shape from `01-SKELETON.md`, even though this whole file is a throwaway placeholder for plan 01-05 - the contract's token spelling is what later hardware plans grep for, so getting it right costs nothing now and avoids a silent mismatch later

## Deviations from Plan

None - plan executed exactly as written. One environmental hiccup (Docker Desktop was not running, and the first image pull failed mid-transfer with "unexpected EOF") was resolved by starting Docker and retrying the pull; no plan or code change was needed.

## Issues Encountered
None beyond the Docker Desktop / image-pull hiccup noted above under Decisions Made, which resolved on retry with no code impact.

## User Setup Required

None - no external service configuration required. (Docker Desktop must be running for `firmware/build.sh` to work; it was started during this plan's execution and is now running.)

## Next Phase Readiness
- Plan 01-05 has a working ESP-IDF project to extend: `firmware/main/CMakeLists.txt`'s `REQUIRES` and `SRCS` lists are intentionally trimmed and ready to grow, `app_main.c`'s boot-and-sleep body is a known placeholder to replace with the full poll loop, and `Kconfig.projbuild`/`sdkconfig.ee02.defaults` (referenced but not yet created) are the next files that plan introduces.
- `fp_backoff_seconds` and `fp_api_base_normalize` are proven correct and ready to be called from the real state machine plan 01-05 builds.
- No blockers. `firmware/build.sh` and `firmware/tests/run_host_tests.sh` are both green and are the two automated feedback signals available until hardware arrives.

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 15 created files verified present on disk (firmware/CMakeLists.txt, partitions.csv,
sdkconfig.defaults, build.sh, .gitignore, VENDOR.md, main/CMakeLists.txt, main/app_main.c,
main/backoff.{c,h}, main/api_base.{c,h}, tests/test_backoff.c, tests/test_api_base.c,
tests/run_host_tests.sh). All 3 task commits (409db54, 3358a36, bfe908d) verified present
in `git log --oneline --all`.
