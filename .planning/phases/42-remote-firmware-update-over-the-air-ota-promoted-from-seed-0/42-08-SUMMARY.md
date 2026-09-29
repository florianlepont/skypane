---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 08
subsystem: firmware
tags: [ota, firmware, c, esp-idf, esp_https_ota, esp_ota_ops]

# Dependency graph
requires:
  - phase: 42-02
    provides: "ota_policy.c/.h's pure OTA decisions (fp_ota_image_check,
      fp_ota_boot_classify, fp_ota_should_confirm, fp_ota_result_format)
      and validate.c's fp_fw_version_valid/fp_fw_size_parse, which this
      plan's ota.c/api_client.c call rather than re-derive"
  - phase: 42-03
    provides: "the signed-app Kconfig chain (CONFIG_SECURE_SIGNED_*_NO_SECURE_BOOT,
      CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y) and CONFIG_SKYPANE_OTA_FLOOR_VERSION,
      which ota.c relies on esp_https_ota_finish()/the bootloader to enforce"
  - phase: 42-06
    provides: "the provisioned-credentials api_client.c/nvs_schema.h this
      plan extends"
provides:
  - "ota.c/.h: fp_ota_apply (download+verify+switch), fp_ota_boot_check
    (post-restart outcome classification), fp_ota_confirm_if_pending
    (the rollback-safety call site), fp_ota_result_pending/record/clear,
    fp_ota_running_version — the full OTA glue contract plan 13's
    state_machine.c/app_main.c wiring will call"
  - "api_client.c: fp_api_get_display parses an optional 'firmware'
    object into fp_display_t.fw (fp_fw_offer_t), permissively; sends
    X-Ota-Result while a result is pending and clears it only after a
    200 display response"
  - "FP_NVS_OTA_TRY/FP_NVS_OTA_RESULT in nvs_schema.h"
affects: [42-13 (state_machine.c/app_main.c wake-loop wiring), firmware.yml CI]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ota.c is glue only: every OTA decision (image check, boot
      classification, confirm rule, result token) is a call into
      ota_policy.c, never re-implemented locally"
    - "esp_https_ota_finish() is the single commit point — every earlier
      check (descriptor/floor, size, read-back hash) can only abort via
      esp_https_ota_abort(), never switch the boot partition itself"
    - "Read-back hash: esp_partition_read() re-reads the bytes
      esp_https_ota just wrote to the inactive slot and hashes them
      independently, before the signature check inside finish() — the
      cheaper gate runs first"

key-files:
  created:
    - firmware/main/ota.c
    - firmware/main/ota.h
  modified:
    - firmware/main/api_client.c
    - firmware/main/api_client.h
    - firmware/main/nvs_schema.h
    - firmware/main/CMakeLists.txt

key-decisions:
  - "The firmware offer's url field is validated with fp_url_valid(url, FP_FW_URL_BUF, false) — https-only unconditionally, ignoring CONFIG_SKYPANE_ALLOW_HTTP — unlike image_url/api_base, which follow the build's own allow-http policy"
  - "A malformed-but-present firmware object logs one 'ota offer ignored field=<name>' line naming the first field that failed; an absent or JSON-null object logs nothing, since that is the normal shape of most polls"
  - "fp_ota_confirm_if_pending() calls fp_ota_should_confirm(pending, true) rather than re-deriving the pending check itself — poll_ok is hardcoded true because this function's own contract is that callers only invoke it on the already-known-successful-poll path; the false branch is exercised only by ota_policy's own host test"
  - "fp_ota_apply() does not call fp_ota_record_result() itself on failure — it returns *fail_out for the caller (plan 13's state_machine.c) to record with whatever context it has, keeping this file glue rather than a second place that decides what gets reported"
  - "FP_NVS_OTA_TRY is left set (not erased) when fp_ota_boot_check() classifies a fresh TRIAL — it is erased only once fp_ota_confirm_if_pending() confirms it later the same wake, so a wake that classifies TRIAL and then fails before confirming still has the version to report as interrupted on the next boot"

requirements: [OTA-02, OTA-03, OTA-05, OTA-06]
requirements-completed: []  # OTA-02/03/05/06 are shared with plan 13's wake-loop
                            # wiring (the confirm-before-sleep call site, the
                            # battery/backoff decision at the call site) and the
                            # hardware session (OTA-12's signature/rollback proof) —
                            # REQUIREMENTS.md is left Pending per this phase's
                            # established convention (see 42-01/42-03/42-07's
                            # precedent); only the phase's own close-out plan
                            # flips these to Complete.

coverage:
  - id: D1
    description: "fp_ota_apply downloads an offered image with esp_https_ota over the same ISRG-only certificate bundle api_client.c already uses, into the inactive OTA slot"
    requirement: "OTA-02"
    verification:
      - kind: integration
        ref: "bash firmware/build.sh (real espressif/idf:v5.3.1 container build; esp_crt_bundle_attach wired into esp_http_client_config_t.crt_bundle_attach, confirmed compiling and linking clean)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Before the boot partition is switched, the image descriptor is checked against the offer and the compiled-in floor, the byte count equals the offered size, and a read-back SHA-256 of the written slot equals the offered sha256; any mismatch aborts without switching"
    requirement: "OTA-02"
    verification:
      - kind: other
        ref: "grep -vE '^[[:space:]]*(/\\*|\\*|//)' firmware/main/ota.c | grep -c 'esp_ota_set_boot_partition(' == 0 (never called directly); grep -c 'esp_partition_read(' firmware/main/ota.c == 2 (>= 1 required)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Signature verification happens inside esp_https_ota_finish (esp_ota_end + set_boot_partition under the signed-on-update Kconfig); its failure is reported as fail-image and never switches the boot partition"
    requirement: "OTA-03"
    verification:
      - kind: other
        ref: "grep -vE '^[[:space:]]*(/\\*|\\*|//)' firmware/main/ota.c | grep -c 'esp_https_ota_finish(' == 1; ESP_ERR_OTA_VALIDATE_FAILED mapped to FP_OTA_RESULT_FAIL_IMAGE in fp_ota_apply()"
        status: pass
    human_judgment: false
  - id: D4
    description: "fp_ota_confirm_if_pending marks the running image valid only when it is pending verification, via fp_ota_should_confirm; it is the call app_main makes after the first successful poll and before that same wake's deep sleep (wiring itself is plan 13's scope)"
    requirement: "OTA-03"
    verification:
      - kind: other
        ref: "grep -vE '^[[:space:]]*(/\\*|\\*|//)' firmware/main/ota.c | grep -c 'esp_ota_mark_app_valid_cancel_rollback(' == 1"
        status: pass
    human_judgment: false
  - id: D5
    description: "After a restart the device classifies the previous attempt (trial, rolled back, interrupted) once and stores exactly one result to report"
    requirement: "OTA-05"
    verification:
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#boot_classify_cases (fp_ota_boot_classify, plan 02) — fp_ota_boot_check glues this into ota.c, proven by the container build compiling it"
        status: pass
    human_judgment: false
  - id: D6
    description: "The display response's optional firmware object is parsed permissively: a missing or malformed offer means no update this wake, never a rejected poll"
    requirement: "OTA-06"
    verification:
      - kind: other
        ref: "sh firmware/tests/run_host_tests.sh (13 suites incl. test_validate.c's fw_version_valid_cases/fw_size_parse_cases from plan 02, unaffected); api_client.c's parse_fw_offer() returns without rejecting the poll for every non-object/absent/null firmware value"
        status: pass
    human_judgment: false
  - id: D7
    description: "X-Ota-Result is sent while a result is pending and cleared only after a 200 display response"
    requirement: "OTA-06"
    verification:
      - kind: other
        ref: "grep -c 'X-Ota-Result' firmware/main/api_client.c == 3 (set in telemetry_headers, deleted in clear_request_headers, cleared via fp_ota_result_clear() after a 200+parsed display response)"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 08: OTA device mechanics (ota.c, api_client.c offer parsing) Summary

**New ota.c/.h glue over esp_https_ota/esp_ota_ops (download, image-descriptor/floor check, read-back SHA-256, boot-outcome classification, rollback confirm) plus api_client.c parsing the display response's optional firmware offer and reporting X-Ota-Result telemetry — proven by a real espressif/idf:v5.3.1 container build.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-09-28
- **Tasks:** 2
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- `api_client.c`'s `fp_api_get_display()` now parses an optional `"firmware"` object into `fp_display_t.fw` (`fp_fw_offer_t`), validated field-by-field with `fp_fw_version_valid`/`fp_fw_size_parse`/`fp_image_hash_valid`/`fp_url_valid` (forced https regardless of `CONFIG_SKYPANE_ALLOW_HTTP`); any missing, null, or malformed shape degrades to `fw.present = false` and never rejects the poll, logging one `ota offer ignored field=<name>` line only when a present object actually failed.
- `telemetry_headers()` sends `X-Ota-Result` whenever `fp_ota_result_pending()` has one queued; `clear_request_headers()` deletes it between requests; `fp_ota_result_clear()` runs only once a display response has actually parsed at 200, so a result is never dropped before the server has seen it.
- New `ota.c`/`ota.h`: `fp_ota_apply()` downloads the offered image with `esp_https_ota` over the same certificate bundle and TLS policy `api_client.c` already uses, checks the signed descriptor against the offer and `CONFIG_SKYPANE_OTA_FLOOR_VERSION` (`fp_ota_image_check`) before writing a byte, feeds the wake budget on every download/hash-read iteration, verifies the exact byte count, re-hashes the written OTA slot straight from flash via `esp_partition_read()` and compares it against the offered SHA-256 — all before `esp_https_ota_finish()`, the single call where `esp_ota_end()` verifies the signature and the boot partition is switched. Any earlier failure calls `esp_https_ota_abort()` and returns without switching.
- `fp_ota_boot_check()` classifies a restart against `FP_NVS_OTA_TRY` and the bootloader's own rollback state (`fp_ota_boot_classify`, from plan 02) and records exactly one result. `fp_ota_confirm_if_pending()` is the rollback-safety call site: it marks a pending trial valid (via `fp_ota_should_confirm`) only on the already-known-good-poll path a later plan wires it into.
- Added `esp_https_ota`/`app_update`/`esp_partition` to `main`'s component `REQUIRES`; a real `espressif/idf:v5.3.1` container build (`bash firmware/build.sh`) compiled and linked the whole tree including the new files, and `firmware/tests/check_production_config.sh built firmware/build-ee02` confirmed the resolved signed-app/rollback Kconfig chain shipped in the built image.

## Task Commits

Each task was committed atomically:

1. **Task 1: Offer parsing and the X-Ota-Result header in api_client** - `63dc2152` (feat)
2. **Task 2: ota.c on esp_https_ota with read-back hash, boot check and confirm** - `68be6f6c` (feat)

**Plan metadata:** committed as part of this final docs commit (STATE.md/ROADMAP.md).

## Files Created/Modified

- `firmware/main/ota.c` - Device-side OTA glue: apply, boot check, confirm, result storage
- `firmware/main/ota.h` - The OTA contract state_machine.c/app_main.c (plan 13) will call
- `firmware/main/api_client.c` - Offer parsing (`parse_fw_offer`), X-Ota-Result header, result-clear on a successful display response
- `firmware/main/api_client.h` - `fp_fw_offer_t`, `fp_display_t.fw`
- `firmware/main/nvs_schema.h` - `FP_NVS_OTA_TRY`, `FP_NVS_OTA_RESULT`
- `firmware/main/CMakeLists.txt` - `esp_https_ota`/`app_update`/`esp_partition` added to `REQUIRES`

## Decisions Made

See `key-decisions` in the frontmatter above — the url-field https-only-unconditionally rule, the malformed-vs-absent-offer logging split, `fp_ota_confirm_if_pending()`'s use of `fp_ota_should_confirm()` with poll_ok hardcoded true, `fp_ota_apply()` not self-recording a failure result, and `FP_NVS_OTA_TRY`'s stay-set-until-confirmed lifetime for a fresh trial are the five decisions with real behavioural consequences.

## Deviations from Plan

None - plan executed exactly as written. All `must_haves` truths and artifacts delivered; both threat-register mitigations this plan's files touch (T-42-34..T-42-38) are implemented as specified: signature verified inside `esp_https_ota_finish()` against the running app's embedded key, TLS via the ISRG-only bundle with an https-only offer URL, the floor re-derived from the signed descriptor (not just the offer), size-bounded download with `fp_wake_checkpoint()` on every iteration so an over-budget wake still ends cleanly and reports interrupted, and `fp_ota_confirm_if_pending()` ready for plan 13 to call before deep sleep.

## Issues Encountered

None. `esp_https_ota.h`/`esp_ota_ops.h`/`esp_partition.h`'s exact function signatures for this pinned IDF version were confirmed by reading the headers directly inside the `espressif/idf:v5.3.1` container before writing `ota.c`, rather than from training-data recall, which avoided any signature mismatch on the first container build attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `ota.c`/`ota.h`'s full contract (`fp_ota_apply`, `fp_ota_boot_check`, `fp_ota_trial_pending`, `fp_ota_confirm_if_pending`, `fp_ota_record_result`, `fp_ota_mark_try`, `fp_ota_result_pending`/`fp_ota_result_clear`, `fp_ota_running_version`) and `api_client.c`'s parsed `fp_display_t.fw` are ready for plan 13 to wire into `state_machine.c` (apply before the hash-skip check) and `app_main.c` (confirm before deep sleep, `fp_ota_mark_try()` before `esp_restart()`).
- `REQUIREMENTS.md` deliberately left untouched: OTA-02/03/05/06 are each shared with plan 13's wake-loop wiring and the hardware session's OTA-12 proof, so this plan does not call `requirements mark-complete` for them — matching this phase's own established convention (see 42-01/42-03/42-07's precedent).
- No blockers for plan 13. One open item worth flagging for the hardware session per 42-RESEARCH.md's own Open Question 2: this plan used `esp_https_ota`'s default (non-partial) buffering rather than `partial_http_download`, on the assumption the ~1.05 MB image fits comfortably in available heap alongside the framebuffer cycle — not yet measured on real hardware.

---

*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 6 created/modified source files and 2 task commit hashes (63dc2152, 68be6f6c) verified present on disk / in git log.
