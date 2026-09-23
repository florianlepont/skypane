---
phase: 34-firmware-resilience-power-security-cleanup
plan: 06
subsystem: firmware
tags: [api-client, nvs, https-only, enrolment, tdd, esp-idf, dedup]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-01's validate.c/.h pure validators (fp_url_valid, fp_image_hash_valid, fp_token_valid, fp_sleep_s_parse, fp_led_enabled_resolve, fp_download_verdict, fp_sha256_to_image_hash) and convention-based host-test discovery"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-04's CONFIG_SKYPANE_ALLOW_HTTP Kconfig option and the dedicated 'secret' NVS partition in partitions.csv"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-03's byos per-device registry (401 wrong secret, 403 unregistered) and plan 34-05's provision.sh, which writes the secret into skypane/enrol_secret on the 'secret' partition"
provides:
  - "nvs_util.c/.h — fp_nvs_get_str, fp_nvs_get_str_from, fp_nvs_set_str, fp_nvs_erase_key: the one open->operate->commit->close NVS helper set for the whole project"
  - "enrol_secret.c/.h — fp_enrol_secret_load, reading skypane/enrol_secret from the dedicated 'secret' NVS partition, never writing or erasing it"
  - "validate.h's fp_http_class_t/fp_http_status_classify — pure HTTP-status classifier (200 OK, 401/403 AUTH, else OTHER), host-tested"
  - "api_client.c/.h rewired onto the pure validators, an https-only gate (s_allow_http from CONFIG_SKYPANE_ALLOW_HTTP), a normalized base URL (fp_api_base_normalize), one http_client_new() helper, and four new FP_ERR_* sentinels (FP_ERR_HTTP_AUTH, FP_ERR_ENROL_REJECTED, FP_ERR_NO_SECRET, FP_ERR_CONFIG)"
  - "fp_api_setup(void) reading its own per-device secret via fp_enrol_secret_load, and fp_api_get_display erasing FP_NVS_DEVICE_TOKEN on a 401/403 so the next wake re-enrols with no reflash"
affects: ["34-07", "34-08", "34-09"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure HTTP-status classifier (fp_http_status_classify) kept in validate.c alongside the other host-tested rules, so api_client.c's small_request compares an enum instead of re-deriving AUTH-vs-other from a raw status code inline"
    - "Secret-partition read-only access: fp_enrol_secret_load never calls nvs_flash_erase_partition on any init/read failure, matching enrol_secret.c/nvs_util.c's project-wide 'never ESP_ERROR_CHECK, never crash on an NVS failure' convention"
    - "esp_err_t-returning api_base_get() propagating FP_ERR_CONFIG unchanged through every caller, replacing the old void-returning strlcpy-only resolver"

key-files:
  created:
    - firmware/main/nvs_util.h
    - firmware/main/nvs_util.c
    - firmware/main/enrol_secret.h
    - firmware/main/enrol_secret.c
  modified:
    - firmware/main/nvs_schema.h
    - firmware/main/secrets.example.h
    - firmware/main/validate.h
    - firmware/main/validate.c
    - firmware/tests/test_validate.c
    - firmware/main/api_client.h
    - firmware/main/api_client.c
    - firmware/main/state_machine.c
    - firmware/VENDOR.md

key-decisions:
  - "fp_api_setup's HTTP-client construction and api_base_get error propagation were rewired in Task 2 (using http_client_new so esp_http_client_init has exactly one call site project-wide), while the function's secret-loading/token-storage body was left for Task 3's full esp_err_t fp_api_setup(void) rewrite - both tasks touch the same function, matching the plan's own task boundary rather than front-loading Task 3's work into Task 2"
  - "fp_api_download computes the SHA-256 digest only after the transfer itself passes (status/length/oversize), then calls fp_download_verdict once uniformly for both the BAD_TRANSFER and HASH_MISMATCH paths - avoids hashing 960000 bytes when the transfer already failed, while keeping exactly one call site for the verdict decision (FW-14-adjacent dedup)"
  - "fp_api_release() ships as an intentionally empty function now, called from state_machine.c immediately before fp_wifi_stop() - the call site exists so a later connection-reuse body needs no caller change"

requirements-completed: [FW-03, FW-04, FW-05, FW-07, FW-08, FW-13, FW-14]

# Metrics
duration: ~15min
completed: 2026-09-23
---

# Phase 34 Plan 06: api_client hardening — token erase, per-device enrolment, https gate, dedup Summary

**A 401/403 on `/display` now erases the device's bearer token so the next wake re-enrols with no reflash; enrolment reads a per-device secret from its own NVS partition instead of a shared compiled-in one; `CONFIG_SKYPANE_ALLOW_HTTP` gates every URL through the same validator in both build modes; every HTTP call's return value is checked; and NVS access, HTTP-client construction and hex validation each exist exactly once.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-09-23
- **Tasks:** 3/3 completed (Task 2 followed RED/GREEN TDD for `fp_http_status_classify`)
- **Files modified:** 13 (4 created, 9 modified, including one deviation-driven doc fix)

## Accomplishments

- **`nvs_util.c/.h`** (new): `fp_nvs_get_str`/`fp_nvs_get_str_from`/`fp_nvs_set_str`/`fp_nvs_erase_key` centralize every open→operate→commit→close NVS sequence the project needs, replacing three separate hand-rolled copies in `api_client.c` (and the two in `state_machine.c`, left for plan 34-08 to rewire). `fp_nvs_erase_key` treats `ESP_ERR_NVS_NOT_FOUND` as success. None of the four call `ESP_ERROR_CHECK`.
- **`enrol_secret.c/.h`** (new): `fp_enrol_secret_load` initializes the dedicated `secret` NVS partition, reads `skypane/enrol_secret` through `nvs_util`, validates the value's shape with `fp_token_valid`, and deinitializes the partition — on any init or read failure it returns the error untouched and **never erases the partition**, since that would destroy the one copy of the device's credential. Never logs the value.
- **`nvs_schema.h`**: gained `FP_NVS_SECRET_PARTITION "secret"` / `FP_NVS_ENROL_SECRET "enrol_secret"` (matching `firmware/provision.sh`'s own partition/key names exactly) and an updated header comment describing five keys over two partitions, keeping the migrate-in-place warning.
- **`secrets.example.h`**: `SKYPANE_SETUP_SECRET` deleted — the firmware image is now identical for every device (D-34-02). `SKYPANE_API_BASE`'s example switched to `https://your-server.example`; the optional `SKYPANE_API_BASE_DEV` documents the dev-only LAN-stub override. `firmware/main/secrets.h` (gitignored) refreshed to match so the container build keeps working.
- **`validate.h`/`.c` + `test_validate.c`** (TDD): added `fp_http_class_t`/`fp_http_status_classify` — 200→OK, 401/403→AUTH, everything else→OTHER — following RED (declared in the header, asserted in the test, confirmed as a link failure with no implementation) then GREEN (implemented, `validate: all cases pass`, `sh firmware/tests/run_host_tests.sh` 8/8).
- **`api_client.c`/`.h`** rewired onto the pure validators end to end: the local `nvs_get_string`/`image_hash_valid`/`url_valid` helpers and the old base-URL history comment are gone; `api_base_get` is now `esp_err_t`-returning, normalizing via `fp_api_base_normalize` (a trailing slash no longer produces `//device...`) and rejecting a disallowed scheme with `FP_ERR_CONFIG`, which every caller propagates unchanged; one `http_client_new()` is the only `esp_http_client_init` call site for setup, display and download alike; `small_request` checks `esp_http_client_write`'s and `esp_http_client_fetch_headers`'s return values (`FP_ERR_HTTP_TRANSPORT` on either failure) and classifies the status with `fp_http_status_classify` *before* the generic non-200 branch; `fp_api_get_display` parses `sleep_s` with `fp_sleep_s_parse` (rejecting anything above 86400) and no longer reads or requires the ignored `reset` field, which is removed from `fp_display_t`; `fp_api_download` checks `fetch_headers`'s return value and defers the final verdict to `fp_download_verdict`; `fp_api_post_logs` is deleted (unused, FW-13).
- **Token erase + per-device enrolment (FW-03, D-34-01, D-34-02)**: `api_client.h` gained `FP_ERR_HTTP_AUTH`/`FP_ERR_ENROL_REJECTED`/`FP_ERR_NO_SECRET`/`FP_ERR_CONFIG` (`0x00600005`..`0x00600008`) and `fp_api_release(void)`; `fp_api_setup` is now `fp_api_setup(void)` — it loads its own secret via `fp_enrol_secret_load` before any network activity (logging clear provisioning guidance and returning `FP_ERR_NO_SECRET` if none is present), sends it as `provision_secret`, zeroes the secret and JSON body on every exit path, and turns a 401/403 into `FP_ERR_ENROL_REJECTED` without erasing anything. `fp_api_get_display` now erases `FP_NVS_DEVICE_TOKEN` and logs a re-enrol notice on `FP_ERR_HTTP_AUTH` instead of just propagating the error.
- **`state_machine.c`**: calls `fp_api_setup()` with no argument (the `#include "secrets.h"` is dropped — nothing else in the file used it); setup failures map to `"secret"`/`"enrol"`/`"config"`/`"status"`/`"json"`/`"http"`; display failures gain `"auth"` and `"config"` ahead of the existing `"status"`/`"json"`/`"http"`; `fp_api_release()` is called immediately before `fp_wifi_stop()`.
- Verified against the real `espressif/idf:v5.3.1` container: both `./firmware/build.sh` (production) and `SKYPANE_PROFILE=dev ./firmware/build.sh` (dev, `CONFIG_SKYPANE_ALLOW_HTTP=y`) build clean end to end, and `sh firmware/tests/check_production_config.sh static`/`built firmware/build-ee02` both `PASS`.

## Task Commits

1. **Task 1: NVS helper module, enrolment-secret reader, schema keys, credential template** - `be427ef` (feat)
2. **Task 2: rewire api_client onto the pure validators, https gate, dedup** - `053aa9c` (test, RED) + `52278e7` (feat, GREEN)
3. **Task 3: token rejection handling, secret-based enrolment, state-machine call site** - `85a240b` (feat)
4. **Deviation: correct a stale VENDOR.md macro list** - `72dea00` (docs)

**Plan metadata:** committed in this same response, immediately after this file.

## Files Created/Modified

- `firmware/main/nvs_util.h`/`.c` - new: `fp_nvs_get_str`/`fp_nvs_get_str_from`/`fp_nvs_set_str`/`fp_nvs_erase_key`
- `firmware/main/enrol_secret.h`/`.c` - new: `fp_enrol_secret_load`, reading the `secret` partition read-only
- `firmware/main/nvs_schema.h` - `FP_NVS_SECRET_PARTITION`/`FP_NVS_ENROL_SECRET` added; header comment updated
- `firmware/main/secrets.example.h` - `SKYPANE_SETUP_SECRET` removed; `SKYPANE_API_BASE` example is now `https://`; `SKYPANE_API_BASE_DEV` added
- `firmware/main/validate.h`/`.c` - `fp_http_class_t`/`fp_http_status_classify` added
- `firmware/tests/test_validate.c` - `http_status_classify_cases()` added (RED then GREEN)
- `firmware/main/api_client.h` - four new `FP_ERR_*` sentinels; `fp_api_setup(void)`; `fp_api_release(void)`; `reset` removed from `fp_display_t`; `fp_api_post_logs` removed
- `firmware/main/api_client.c` - full rewire described above
- `firmware/main/state_machine.c` - `fp_api_setup()` call, new step-token mapping, `fp_api_release()` call site, `secrets.h` include dropped
- `firmware/VENDOR.md` - stale `SKYPANE_SETUP_SECRET` reference in the `secrets.example.h` vendoring entry corrected (deviation, Rule 1)

## Decisions Made

- `fp_api_setup`'s HTTP-client construction (`http_client_new`) and `api_base_get` error propagation were updated in Task 2, but its secret-loading/token-storage body was deliberately left untouched until Task 3's `fp_api_setup(void)` rewrite — both tasks edit the same function, matching the plan's own task boundary rather than front-loading Task 3's logic into Task 2's commit.
- `fp_api_download` computes the SHA-256 digest only once the transfer itself passes (status/length/oversize all correct), then always calls `fp_download_verdict` once for the final decision — `fp_download_verdict`'s own status/length/oversize re-check makes a `BAD_TRANSFER` verdict correct regardless of what `hex` contains, so there's no need for two separate decision branches.
- `fp_api_release()` ships as an intentionally empty function, wired into `state_machine.c`'s call sequence now so a later connection-reuse implementation needs no caller change.

## Deviations from Plan

**1. [Rule 1 - Bug] Corrected a stale macro list in `firmware/VENDOR.md`**
- **Found during:** final tree-wide verification (`grep -rn "SKYPANE_SETUP_SECRET" firmware/`)
- **Issue:** `VENDOR.md`'s "Original To This Repository" entry for `secrets.example.h` still listed the now-deleted `SKYPANE_SETUP_SECRET` macro and was missing the new `SKYPANE_API_BASE_DEV` macro, contradicting the plan's own verification command and leaving the authoritative vendor-tracking doc factually wrong about what the file currently defines.
- **Fix:** Updated the one paragraph describing `secrets.example.h`'s macro set to the current list and added a sentence noting the per-device secret is not compiled in. The Log Line Contract section (which the environment notes explicitly defer to plan 34-10) was left untouched.
- **Files modified:** `firmware/VENDOR.md`
- **Commit:** `72dea00`

No other deviations — the rest of the plan executed as written.

## Issues Encountered

None. Docker (`espressif/idf:v5.3.1`) was available throughout, so every build-gated verification step ran for real:
- `sh firmware/tests/run_host_tests.sh` — 8/8 suites pass after each task.
- `rm -rf firmware/build-ee02 && ./firmware/build.sh` (production) — succeeds end to end (`skypane.bin`, 59% free).
- `SKYPANE_PROFILE=dev ./firmware/build.sh` (dev, `CONFIG_SKYPANE_ALLOW_HTTP=y`) — succeeds end to end.
- `sh firmware/tests/check_production_config.sh static` and `built firmware/build-ee02` — both `PASS`.
- Confirmed the intentional intermediate break between Task 2 and Task 3 (`FP_ERR_CONFIG`/`FP_ERR_HTTP_AUTH` referenced in `api_client.c` before being declared in `api_client.h`, and `state_machine.c`'s still-unedited `SKYPANE_SETUP_SECRET` reference) via a real container build — those were the only two error messages, exactly matching what Task 3 fixes.
- Build directories (`firmware/build-ee02`, `firmware/build-ee02-dev`) removed after verification, matching `firmware/.gitignore`.

## User Setup Required

None — no external service configuration required. `firmware/main/secrets.h` (gitignored) was refreshed in place to match the new template; a real device still needs a real Wi-Fi SSID/password and server base URL filled in by hand, as before.

## Next Phase Readiness

- `fp_api_setup(void)`, `fp_api_get_display`, `fp_api_download` and `fp_api_release(void)` are the exact public surface plan 34-09 (connection reuse / TLS session persistence) needs — this plan deliberately kept that surface stable so 34-09 only changes internals.
- `nvs_util.c/.h` is ready for plan 34-08 to rewire `state_machine.c`'s own two remaining hand-rolled NVS sequences (`FP_NVS_IMAGE_HASH` read/write) onto the same helpers.
- The Log Line Contract's new step tokens (`auth`, `enrol`, `secret`, `config`) are live in `state_machine.c` now but **not yet documented in `firmware/VENDOR.md`'s Log Line Contract table** — that documentation update is plan 34-10's job, per the environment notes ("new values will be documented by plan 34-10; spellings fixed here"). The spellings used here (`auth`, `enrol`, `secret`, `config`) are final and must not change in 34-10.
- No open blockers. `firmware/main/api_client.c`/`.h`, `nvs_util.*`, `enrol_secret.*`, `nvs_schema.h`, `secrets.example.h` and the touched slice of `state_machine.c` are single-owner for this plan.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*
