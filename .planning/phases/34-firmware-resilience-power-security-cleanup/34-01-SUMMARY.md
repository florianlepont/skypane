---
phase: 34-firmware-resilience-power-security-cleanup
plan: 01
subsystem: firmware
tags: [validate, host-tests, esp-idf, sleep_s, https-only, hex-dedup, cmake]

requires: []
provides:
  - "firmware/main/validate.c/.h — pure, ESP-IDF-free module covering every display-response field rule (image hash, url, sleep_s, led_enabled, token) and the download size/SHA gate, host-tested in firmware/tests/test_validate.c"
  - "firmware/tests/run_host_tests.sh — discovers test_*.c by naming convention (test_<name>.c -> main/<name>.c) instead of a hand-maintained run_suite list, with a HOST_TEST_DEPS: comment for extra implementation files and a loud MISSING failure for an unresolvable suite"
  - "firmware/main/CMakeLists.txt — SRC_DIRS \".\" instead of an explicit SRCS list, so any new main/*.c compiles into the image with no CMake edit"
affects: [34-06]

tech-stack:
  added: []
  patterns:
    - "Pure-logic module split (no ESP-IDF includes), copying the existing backoff.c/panel_guard.c/api_base.c template: #pragma once header explaining why the module is separated from its I/O-driving caller, only stdint.h/stdbool.h/stddef.h/string.h/stdio.h, one narrow function or enum-returning decision per rule, a matching tests/test_<name>.c compiled by the system cc"
    - "Convention-based host-test discovery (test_<name>.c -> main/<name>.c) replacing a hand-maintained run_suite registration list; an optional single-line HOST_TEST_DEPS: comment in the test source pulls in extra implementation files for suites that need more than their one matching module"

key-files:
  created:
    - firmware/main/validate.h
    - firmware/main/validate.c
    - firmware/tests/test_validate.c
  modified:
    - firmware/tests/run_host_tests.sh
    - firmware/main/CMakeLists.txt

key-decisions:
  - "sleep_s upper bound changed from the prior 4294967295.0 (UINT32_MAX-class) ceiling to FP_SLEEP_S_MAX = 86400 (one day); the value 4294967295.0 is now simply out of range rather than needing a separate overflow check, since the day cap already excludes it (FW-04)."
  - "fp_url_scheme_allowed(url, allow_http) takes allow_http as a parameter rather than reading a Kconfig macro directly, so the same compiled function is exercised in both modes from one host-test binary (FW-07/D-34-04's proof requirement) — the CONFIG_SKYPANE_ALLOW_HTTP wiring itself is plan 34-06's job (api_client.c is not touched this plan)."
  - "One fp_hex_lower_valid(s, expected_len) helper replaces the two hand-written hex loops api_client.c currently has separately for image_hash and token checks (FW-14); fp_image_hash_valid and fp_token_valid are both thin wrappers over it."
  - "fp_download_verdict() fails closed to HASH_MISMATCH (not a separate error) when either hash pointer is NULL, matching the plan's explicit behavior spec, rather than treating a NULL hash as a transfer-layer problem."
  - "run_host_tests.sh's HOST_TEST_DEPS: extraction uses grep + sed only (POSIX sh, no bash-isms), matching the existing script's set -eu / TMP_DIR-trap / CC-override structure exactly; a suite with no matching main/<module>.c prints '<name>: MISSING main/<module>.c' and fails the run rather than being silently skipped."

requirements-completed: [FW-04, FW-06, FW-07, FW-14]

coverage:
  - id: T1
    description: "validate.c/.h created with zero ESP-IDF includes; every rule listed in the plan's interfaces block (image hash, url scheme/shape with allow_http both modes, sleep_s 1..86400, led_enabled resolution, token shape, download verdict, sha256-to-image-hash render) implemented as one exported pure function, following RED (test written and confirmed failing to compile with validate.c absent) then GREEN (implemented, test passes)"
    requirement: "FW-06, FW-04, FW-07"
    verification:
      - kind: unit
        ref: "cc -Wall -Wextra -Werror -std=c11 firmware/main/validate.c firmware/tests/test_validate.c -> 'validate: all cases pass', exit 0"
        status: pass
      - kind: other
        ref: "grep -nE '#include \"(esp_|freertos|nvs|cJSON)' firmware/main/validate.c firmware/main/validate.h -> no matches"
        status: pass
      - kind: other
        ref: "grep -c 'FP_SLEEP_S_MAX 86400u' firmware/main/validate.h -> 1; grep -c 'allow_http' firmware/tests/test_validate.c -> 6 (>= 4); grep -c '86401' -> 1; grep -c '4294967295' -> 1"
        status: pass
      - kind: other
        ref: "grep -nE 'D-[0-9]|FW-[0-9]|PLAN|Phase [0-9]' firmware/main/validate.c firmware/main/validate.h firmware/tests/test_validate.c -> no matches (D-A3)"
        status: pass
    human_judgment: false
  - id: T2
    description: "run_host_tests.sh rewritten to discover suites by convention; main/CMakeLists.txt switched to SRC_DIRS \".\"; verified against the real espressif/idf:v5.3.1 container build, not just the host cc path"
    requirement: "FW-06 (CI wiring precondition), FW-13-adjacent tooling"
    verification:
      - kind: integration
        ref: "sh firmware/tests/run_host_tests.sh -> lists test_api_base, test_backoff, test_battery_math, test_panel_guard, test_validate; '== summary: 5 suites, all hardware-free firmware suites passed =='; exit 0"
        status: pass
      - kind: integration
        ref: "temporarily created firmware/tests/test_zz_missing.c (no matching main/zz_missing.c) -> runner printed 'test_zz_missing: MISSING main/zz_missing.c', exit 1; file removed afterward, not committed"
        status: pass
      - kind: other
        ref: "grep -c 'run_suite \"test_' firmware/tests/run_host_tests.sh -> 0 (no hand-listed suites remain); grep -c HOST_TEST_DEPS -> >=1; sh -n run_host_tests.sh -> exit 0; grep -c '\\[\\[' -> 0"
        status: pass
      - kind: other
        ref: "grep -c 'SRC_DIRS \".\"' firmware/main/CMakeLists.txt -> 1; grep -c '\"app_main.c\"' -> 0"
        status: pass
      - kind: integration
        ref: "./firmware/build.sh (real espressif/idf:v5.3.1 container) -> validate.c compiled into esp-idf/main/CMakeFiles/__idf_main.dir/validate.c.obj via SRC_DIRS with no edit, full build succeeded, skypane.bin produced"
        status: pass
    human_judgment: false

duration: ~50m
completed: 2026-09-23
status: complete
---

# Phase 34 Plan 01: Pure Validator Module + Convention-Based Host Tests Summary

**Extracted every display-response validation rule (image hash, URL scheme, `sleep_s` range, `led_enabled`, token shape) and the download size/SHA gate out of `api_client.c`'s inline checks into a new pure, host-tested `validate.c/.h` module — fixing the `sleep_s` bound to one day (86400 s) and parameterizing the https-only rule on `allow_http` along the way — and made `run_host_tests.sh` discover suites by naming convention instead of a hand-maintained list, verified against both the host `cc` and the real ESP-IDF container build.**

## Performance

- **Duration:** ~50m
- **Completed:** 2026-09-23
- **Tasks:** 2/2 completed
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- Created `firmware/main/validate.h`/`.c`: nine pure functions (`fp_hex_lower_valid`, `fp_image_hash_valid`, `fp_token_valid`, `fp_url_scheme_allowed`, `fp_url_valid`, `fp_sleep_s_parse`, `fp_led_enabled_resolve`, `fp_download_verdict`, `fp_sha256_to_image_hash`) covering every rule currently inlined in `api_client.c`, with zero ESP-IDF includes — confirmed by grep and by a clean `cc -Wall -Wextra -Werror -std=c11` build. `sleep_s`'s upper bound moved from the prior `4294967295.0`-class ceiling to `FP_SLEEP_S_MAX = 86400` (FW-04); the URL scheme check takes `allow_http` as a parameter so one compiled function proves both the production (https-only) and dev (`CONFIG_SKYPANE_ALLOW_HTTP=y`) modes (FW-07/D-34-04); the two hand-written hex-check loops collapsed into one `fp_hex_lower_valid` helper (FW-14).
- Wrote `firmware/tests/test_validate.c` following the RED/GREEN TDD cycle: the test was written and confirmed to fail to compile with `validate.c` temporarily absent, then `validate.c`/`validate.h` were restored and the suite passed (`validate: all cases pass`). All nine behavior groups from the plan's `<behavior>` block are asserted, including every explicit boundary (63/65-char hex, `86401`/`0`/`-5`/`1.5`/`4294967295`/NaN for `sleep_s`, cap-exact URL lengths, NULL hashes in the download gate).
- Rewrote `firmware/tests/run_host_tests.sh` to discover `test_*.c` files by convention (`test_<name>.c -> main/<name>.c`) instead of four hand-listed `run_suite` calls, added a one-line `HOST_TEST_DEPS:` comment convention for suites needing extra implementation files, made a missing implementation file a loud, non-zero-exit failure (verified live with a throwaway `test_zz_missing.c`), and added the suite count to the summary line. All five current suites (`test_api_base`, `test_backoff`, `test_battery_math`, `test_panel_guard`, `test_validate`) are discovered automatically with no suite-specific code left in the script.
- Switched `firmware/main/CMakeLists.txt` from an explicit `SRCS` list to `SRC_DIRS "."`, then ran the real `espressif/idf:v5.3.1` containerized build (`./firmware/build.sh`) to confirm `validate.c` compiles into the firmware image with no CMake edit — the build succeeded end to end, producing `skypane.bin`.

## Task Commits

1. **Task 1: Pure validator module validate.c/.h with host test** - `09ccb39` (test, RED) + `9e912bd` (feat, GREEN)
2. **Task 2: Convention-based host-test runner and SRC_DIRS component registration** - `ef0e3e6` (refactor)

**Plan metadata:** (this commit)

## Files Created/Modified

- `firmware/main/validate.h` - Pure validator API declarations, `FP_SLEEP_S_MIN`/`FP_SLEEP_S_MAX`/`FP_IMAGE_HASH_BUF`, no ESP-IDF includes
- `firmware/main/validate.c` - Implementation of all nine functions, `<stdio.h>`/`<string.h>` only beyond the header's set
- `firmware/tests/test_validate.c` - Host test covering both `allow_http` modes and every stated boundary
- `firmware/tests/run_host_tests.sh` - Convention-based `test_*.c` discovery, `HOST_TEST_DEPS:` support, loud MISSING failure, suite-count summary
- `firmware/main/CMakeLists.txt` - `SRC_DIRS "."` replacing the explicit `SRCS` list

## Decisions Made

- **`fp_sleep_s_parse` checks the day-cap range before the exact-integer check**, so `4294967295.0` and `86401.0` are rejected by the range comparison rather than needing a dedicated "still fits `uint32_t`" branch — simpler than the original `api_client.c` code, which compared against `UINT32_MAX` and relied on a separate exact-integer check to catch fractions.
- **`fp_download_verdict` treats a NULL `computed_hash` or `expected_hash` as `FP_DOWNLOAD_HASH_MISMATCH`, not a third verdict value** — matching the plan's explicit behavior spec and keeping the enum at exactly the three states the transfer-then-hash gate needs (fail closed, never a silent pass).
- **`fp_sha256_to_image_hash` keeps the existing `snprintf(out + 7 + i*2, 3, "%02x", digest[i])` idiom from `api_client.c`'s inline hex-render loop** rather than switching to a lookup-table approach, since the plan explicitly allows `<stdio.h>` for this and matching the existing style keeps plan 34-06's later rewire of `api_client.c` a closer diff.
- **`run_host_tests.sh`'s `HOST_TEST_DEPS:` line is extracted with `grep -m1` + `sed`, stopping at the first `*` after the marker** (the comment's closing `*/`) rather than a more general parser — sufficient for the one documented use case (extra `.c` filenames, no `*` characters expected in a filename list) and keeps the script POSIX `sh`, no bash-isms, as the plan requires.

## Deviations from Plan

None - plan executed exactly as written. Task 1 followed the RED-first sequence literally (validate.c was moved aside, the test's compile failure was confirmed, then restored) rather than skipping straight to a passing state.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. `firmware/main/secrets.h` (gitignored, copied from `secrets.example.h`) was already present in this environment for the container build; no new file needed.

## Next Phase Readiness

- `validate.c/.h` is ready for plan 34-06 to rewire `api_client.c` onto it (this plan deliberately did not touch `api_client.c` — see the plan's own objective note). The nine exported functions map 1:1 onto `api_client.c`'s current inline checks (`image_hash_valid`, `url_valid`, `sleep_ok`, the setup-response token check, `led_enabled` resolution, the download gate's status/length/oversize/hash checks, and the SHA-256-to-hex render), so 34-06 should be a mechanical call-site swap plus deleting the now-dead inline copies.
- `run_host_tests.sh`'s convention-based discovery means the upcoming wave-2 plans that add `reset_reason.c`/`wake_deadline.c`/`sleep_decision.c` (per `34-RESEARCH.md`'s recommended file layout) need only add their `test_<name>.c` file — no edit to the runner itself.
- `main/CMakeLists.txt`'s `SRC_DIRS "."` means every future `main/*.c` this phase adds (`secret_provision.c`, etc.) compiles automatically; confirmed live against the real container build, not assumed.
- No open blockers for wave 2.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: `firmware/main/validate.h`
- FOUND: `firmware/main/validate.c`
- FOUND: `firmware/tests/test_validate.c`
- FOUND: `firmware/tests/run_host_tests.sh` (modified)
- FOUND: `firmware/main/CMakeLists.txt` (modified)
- FOUND commit `09ccb39` (Task 1, RED)
- FOUND commit `9e912bd` (Task 1, GREEN)
- FOUND commit `ef0e3e6` (Task 2)
