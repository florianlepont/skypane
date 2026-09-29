---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 02
subsystem: firmware
tags: [ota, firmware, c, tdd, host-tests]

# Dependency graph
requires:
  - phase: 42-01
    provides: server/firmware_registry.py's RESULT_TOKENS wire format, which
      fp_ota_result_token's strings must match exactly
provides:
  - "fp_fw_version_valid / fp_fw_size_parse: pure offer-field validators for
    the firmware version and image-size fields (validate.c)"
  - "ota_policy.c/.h: every device-side OTA decision as pure, host-tested C
    - version parse/floor, start/refuse decision, downloaded-image check,
    boot-outcome classification, the confirm rule, result token/format"
affects: [42-08 (api_client.c OTA download/session wiring), 42-13
  (state_machine.c wake-loop integration), firmware.yml CI]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-decision C module (no ESP-IDF, no I/O), following the
      sleep_decision.c / fault_screen.c / nvs_boot.c shape: decide.c owns
      the logic, api_client.c/state_machine.c will own the I/O and call it"
    - "TDD RED/GREEN per tdd=true task: failing test + declared header
      committed first, implementation committed second"

key-files:
  created:
    - firmware/main/ota_policy.h
    - firmware/main/ota_policy.c
    - firmware/tests/test_ota_policy.c
  modified:
    - firmware/main/validate.h
    - firmware/main/validate.c
    - firmware/tests/test_validate.c

key-decisions:
  - "fp_ota_decide checks same-version before battery before floor, in that
    fixed order, so a same-version offer never trips a spurious battery or
    floor refusal"
  - "A voluntary downgrade is allowed: fp_ota_decide only compares the
    offered version against the floor, never against the running version"
  - "fp_ota_image_check re-derives project/version/floor from the signed
    app descriptor independently of the offer, so a compromised VPS cannot
    bypass the floor by lying only in the offer"
  - "NULL/malformed inputs to fp_ota_decide and fp_ota_image_check fail
    closed (never START, never OK) rather than crashing on a NULL strcmp"
  - "fp_ota_result_token has a defensive default-return after an exhaustive
    switch, to keep -Werror clean without weakening -Wswitch's protection
    against a future unhandled enum value"

requirements-completed: [OTA-02, OTA-03, OTA-05, OTA-06]

coverage:
  - id: D1
    description: "Firmware offer's version and size fields are validated
      by pure, host-tested functions (fp_fw_version_valid,
      fp_fw_size_parse); a malformed field can only ever mean no update
      this wake, never a rejected poll"
    requirement: "OTA-02"
    verification:
      - kind: unit
        ref: "firmware/tests/test_validate.c#fw_version_valid_cases"
        status: pass
      - kind: unit
        ref: "firmware/tests/test_validate.c#fw_size_parse_cases"
        status: pass
    human_judgment: false
  - id: D2
    description: "The confirm rule (mark the running image valid only when
      pending verification and this wake's poll succeeded) and boot-outcome
      classification (trial / rolled back / interrupted / none) are pure,
      host-tested functions"
    requirement: "OTA-03"
    verification:
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#should_confirm_cases"
        status: pass
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#boot_classify_cases"
        status: pass
    human_judgment: false
  - id: D3
    description: "The device refuses an offered or downloaded image whose
      version is below the compiled-in floor, or whose descriptor version
      does not match the offer"
    requirement: "OTA-05"
    verification:
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#decide_cases"
        status: pass
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#image_check_cases"
        status: pass
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#version_at_or_above_floor_cases"
        status: pass
    human_judgment: false
  - id: D4
    description: "The device refuses to start an update when its own
      measured battery is at or below 3500 mV, or unknown (the 0 sentinel)"
    requirement: "OTA-06"
    verification:
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#decide_cases"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 02: OTA device-side pure decisions Summary

**Every OTA decision the device makes — offer-field validation, start/refuse, image check, boot-outcome classification, the confirm rule, and result tokens — as pure, host-tested C with no ESP-IDF dependency.**

## Performance

- **Duration:** ~15min
- **Completed:** 2026-09-28T09:36:00Z
- **Tasks:** 3 (1 gate check, 2 TDD implementation tasks)
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments
- Gate G-41 confirmed: Phase 41 is complete on `origin/main` (VERIFICATION.md `status: passed`, ROADMAP Phase 41 section fully checked, `origin/main` is an ancestor of this branch's HEAD) before any edit was made.
- `validate.c/.h` gained `fp_fw_version_valid` and `fp_fw_size_parse`, the two new offer-field validators the OTA offer needs (sha256 and URL reuse the existing `fp_image_hash_valid` / `fp_url_valid`).
- New `ota_policy.c/.h` module: version parsing (`fw-vX.Y.Z[-suffix]`) and floor comparison, the start/skip/refuse decision (`fp_ota_decide`), the downloaded-image check against the signed descriptor (`fp_ota_image_check`), post-restart boot-outcome classification (`fp_ota_boot_classify`), the confirm rule (`fp_ota_should_confirm`), and the result token/format the device reports (`fp_ota_result_token` / `fp_ota_result_format`).
- All ten host-test suites (including the two new ones) pass via `firmware/tests/run_host_tests.sh`; `ota_policy.c` compiles clean under `cc -Wall -Wextra -Werror -std=c11`; `scripts/check_comment_history.py check` is clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: Gate G-41** - read-only check, no commit (verified against `origin/main`, no edits made)
2. **Task 2: Offer-field validators in validate.c** (TDD):
   - `6d51dc73` test(42-02): add failing tests for firmware offer size/version validators (RED)
   - `a5026a4d` feat(42-02): offer-field validators for firmware version and size (GREEN)
3. **Task 3: ota_policy pure decisions** (TDD):
   - `9b3d76dd` test(42-02): add failing tests for ota_policy pure OTA decisions (RED)
   - `9da7234a` feat(42-02): implement ota_policy pure OTA decisions (GREEN)

**Plan metadata:** commit follows below (this SUMMARY + STATE.md/ROADMAP.md update)

## Files Created/Modified
- `firmware/main/ota_policy.h` - Public contract for every OTA decision: version parse/floor, decide, image check, boot classify, should-confirm, result token/format
- `firmware/main/ota_policy.c` - Pure implementation of the above, no ESP-IDF includes
- `firmware/tests/test_ota_policy.c` - Host test covering every `ota_policy.c` function
- `firmware/main/validate.h` - Adds `FP_FW_VERSION_BUF`, `FP_FW_URL_BUF`, `FP_FW_MAX_IMAGE_BYTES`, and the two new validator declarations
- `firmware/main/validate.c` - Implements `fp_fw_version_valid` and `fp_fw_size_parse`
- `firmware/tests/test_validate.c` - Adds `fw_version_valid_cases` and `fw_size_parse_cases`

## Decisions Made
- `fp_ota_decide`'s check order is fixed: same-version first (so a same-version offer is never mistaken for a battery/floor refusal), then battery, then floor. A downgrade is compared only against the floor, never against the running version, per D-06.
- `fp_ota_image_check` re-derives project name, version and floor from the signed app descriptor independently of the offer string, so the floor holds even if a compromised VPS lies in the offer (T-42-09).
- Malformed/NULL inputs to `fp_ota_decide` and `fp_ota_image_check` fail closed (`FP_OTA_REFUSE_FLOOR` / `FP_OTA_IMAGE_WRONG_PROJECT`) rather than dereferencing NULL through `strcmp`.
- `fp_ota_result_token`'s switch is exhaustive over the enum (so `-Wswitch` still catches a future unhandled value) with a defensive trailing `return` to keep `-Werror` clean without a `default:` case masking that protection.
- Did not touch `firmware/VENDOR.md` for the two new original files (`ota_policy.h/.c`) — this project's established pattern (see Phase 34 plan 34-10) is to batch `VENDOR.md` provenance entries in a dedicated later plan, not on every file's introducing commit, and `VENDOR.md` is outside this plan's `files_modified` list.

## Deviations from Plan

None - plan executed exactly as written. All `must_haves` truths and artifacts delivered; all four threat-register mitigations (T-42-08..T-42-11) implemented as specified.

## Issues Encountered
- The `parse_version_component` helper's original doc comment used the literal sequence `*p/*out`, which Clang parsed as an accidental nested-comment start (`-Wcomment`) and would have failed the task's own `-Werror` acceptance check. Reworded the comment to avoid the `*/`-lookalike sequence; no functional change.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `ota_policy.c`'s pure decisions and `validate.c`'s new offer-field validators are ready for plan 42-08 (api_client.c OTA download/session wiring) and plan 42-13 (state_machine.c wake-loop integration) to call.
- `fp_ota_result_token`'s exact strings must stay byte-identical to `server/firmware_registry.py`'s `RESULT_TOKENS` (established in plan 42-01) — any future edit to either side needs to keep both in sync.
- No blockers for the next plan in this phase.

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 6 created/modified source files and 4 task commit hashes (6d51dc73, a5026a4d, 9b3d76dd, 9da7234a) verified present on disk / in git log.
