---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 03
subsystem: firmware
tags: [esp-idf, ota, secure-boot-v2, signed-app-verification, bootloader-rollback, kconfig, ci]

# Dependency graph
requires:
  - phase: 42-01
    provides: server-side firmware release registry (schedule/publish/offer decision layer) that the device-side OTA Kconfig chain will eventually be offered against
  - phase: 42-02
    provides: firmware/main/ota_policy.c + validate.c pure OTA decision/validator functions this plan's Kconfig floor (SKYPANE_OTA_FLOOR_VERSION) and rollback config will be consumed by
provides:
  - CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y and signed-app verification (CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT / CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT, RSA-3072 scheme) confirmed inside the pinned ESP-IDF v5.3.1 container with zero eFuse-burning options on
  - firmware/tests/check_production_config.sh static+built modes now assert the OTA/signing chain and fail on any eFuse-burning option (mutation-proven)
  - SKYPANE_OTA_FLOOR_VERSION Kconfig symbol (compiled-in version floor) and SKYPANE_WAKE_BUDGET_S default raised 300->360s for an OTA wake
  - firmware/build.sh SKYPANE_RELEASE_TAG release mode: a release build's PROJECT_VER can only ever be the exact fw-vX.Y.Z tag on a clean, tagged HEAD; non-release builds stay distinguishable via --match 'fw-v*'
  - firmware/SIGNING.md: resolved Kconfig chain record, human-only key-generation/backup/rotation procedure, release tag convention, forbidden list
affects: [42-04, 42-05, 42-hardware-session, ci-firmware-signing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Confirm-before-relying: any Kconfig/toolchain claim from research is re-verified against a clean `idf.py reconfigure` inside the pinned container before it is committed, not trusted from documentation summaries alone"
    - "Out-of-band CI signing: CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES stays off; the private key never touches a build machine, only a GitHub Actions environment secret with a required reviewer"

key-files:
  created:
    - firmware/SIGNING.md
  modified:
    - firmware/sdkconfig.defaults
    - firmware/main/Kconfig.projbuild
    - firmware/build.sh
    - firmware/tests/check_production_config.sh

key-decisions:
  - "Confirmed via a clean (not incremental) idf.py reconfigure that CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES defaults to y once signed apps are enabled and must be explicitly turned off with '# ... is not set' in sdkconfig.defaults -- an incremental reconfigure against an already-resolved build dir silently carries over the old value and would have masked this"
  - "CONFIG_SECURE_SIGNED_ON_BOOT_NO_SECURE_BOOT genuinely does not exist for the RSA-3072 scheme this project uses (its Kconfig entry depends on the ECDSA scheme specifically) -- confirmed absent even as a commented-out line in the resolved sdkconfig, matching the plan's expected finding exactly"
  - "Real container build+sign-refusal+production-config-check pipeline run end to end (not just idf.py reconfigure) to prove the built-mode CI check will actually pass on the pushed branch"

requirements-completed: []

coverage:
  - id: D1
    description: "G-41 gate re-verified against origin/main before any edit (Phase 41 complete, ROADMAP clean, HEAD an ancestor)"
    verification:
      - kind: other
        ref: "git fetch origin main && git show origin/main:.../41-VERIFICATION.md | grep '^status: passed'; git merge-base --is-ancestor origin/main HEAD"
        status: pass
    human_judgment: false
  - id: D2
    description: "Signed-app Kconfig chain (rollback + signed-app-verification-without-secure-boot, RSA-3072, zero eFuse) confirmed inside the pinned espressif/idf:v5.3.1 container against both a scratch copy and the real committed sdkconfig.defaults"
    verification:
      - kind: other
        ref: "docker run espressif/idf:v5.3.1 idf.py reconfigure (clean build dir) against firmware/sdkconfig.defaults;sdkconfig.ee02.defaults"
        status: pass
    human_judgment: false
  - id: D3
    description: "check_production_config.sh static mode requires the new OTA/signing lines and fails on any eFuse-burning option in a committed defaults file"
    verification:
      - kind: other
        ref: "sh firmware/tests/check_production_config.sh static"
        status: pass
      - kind: other
        ref: "mutation proof: CONFIG_SECURE_BOOT=y appended to a scratch sdkconfig.defaults copy makes the static check exit 1"
        status: pass
    human_judgment: false
  - id: D4
    description: "check_production_config.sh built mode passes against a real container-built image and prints the resolved OTA/signing chain"
    verification:
      - kind: other
        ref: "./firmware/build.sh (real espressif/idf:v5.3.1 container build) then sh firmware/tests/check_production_config.sh built firmware/build-ee02"
        status: pass
    human_judgment: false
  - id: D5
    description: "SKYPANE_OTA_FLOOR_VERSION Kconfig symbol added; SKYPANE_WAKE_BUDGET_S default raised 300->360 for an OTA wake"
    verification:
      - kind: other
        ref: "grep -c SKYPANE_OTA_FLOOR_VERSION firmware/main/Kconfig.projbuild"
        status: pass
    human_judgment: false
  - id: D6
    description: "firmware/build.sh SKYPANE_RELEASE_TAG release mode: malformed tag exits 2 before Docker; untagged/mismatched HEAD exits 2; non-release builds restrict git describe to --match 'fw-v*'"
    verification:
      - kind: other
        ref: "sh -n firmware/build.sh; SKYPANE_RELEASE_TAG=fw-vbad sh firmware/build.sh (exit 2); SKYPANE_RELEASE_TAG=fw-v9.9.9 sh firmware/build.sh (exit 2, HEAD not tagged); grep -c \"match 'fw-v\\*'\" firmware/build.sh"
        status: pass
    human_judgment: false
  - id: D7
    description: "firmware/SIGNING.md documents the resolved config, key-generation/backup/rotation human procedure (FW_SIGNING_KEY, firmware-signing environment, encrypted offline backup, public key path), forbidden list, and local bench-image signing; no private key material committed"
    verification:
      - kind: other
        ref: "grep FW_SIGNING_KEY / generate_signing_key / firmware-signing / firmware/signing/skypane-signing-pubkey.pem firmware/SIGNING.md; grep -c 'BEGIN ... PRIVATE KEY' -r firmware/ == 0; server/.venv/bin/python3 scripts/check_comment_history.py check"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 03: OTA Kconfig chain, release tagging and signing procedure Summary

**Confirmed-in-container rollback + signed-app-verification-without-secure-boot (RSA-3072, zero eFuse), a mutation-proven CI guard against every eFuse-burning option, tag-exact release versioning in build.sh, and the human-only signing-key procedure in firmware/SIGNING.md**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-28
- **Tasks:** 3 (Task 1 read-only, no commit; Tasks 2-3 each one commit)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Re-verified gate G-41 against `origin/main` (all checks passed, read-only, no edits) before touching anything
- Confirmed the entire signed-app Kconfig chain by running a clean `idf.py reconfigure` inside the pinned `espressif/idf:v5.3.1` container, first against a scratch copy of `firmware/`, then again against the real committed defaults -- byte-identical resolved lines both times
- Discovered and corrected a real gap between the plan's assumption and actual ESP-IDF behavior: `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES` defaults to `y` once signed apps are on, and only a *clean* reconfigure (not incremental) proves an explicit "not set" line actually turns it off
- Confirmed `CONFIG_SECURE_SIGNED_ON_BOOT_NO_SECURE_BOOT` is genuinely absent from the resolved sdkconfig for the RSA-3072 scheme (its Kconfig entry depends on the ECDSA scheme), matching the plan's expected finding
- Extended `check_production_config.sh`: static mode now requires the new rollback/signed-app lines and fails on any eFuse-burning option in a committed defaults file (mutation-proven with a real scratch-copy failure run); built mode requires the resolved chain and logs it
- Ran a full real container build (`./firmware/build.sh`, prod profile) end to end and confirmed both that it succeeds and that it correctly reports "App built but not signed. Sign app before flashing" -- proving the out-of-band CI signing model works as designed -- then ran the built-mode production-config check against the real artifact (PASS)
- Added `SKYPANE_OTA_FLOOR_VERSION` (compiled-in version floor) to Kconfig and raised `SKYPANE_WAKE_BUDGET_S`'s default from 300 to 360 for an OTA wake's extra stages
- `firmware/build.sh` gained `SKYPANE_RELEASE_TAG` release mode (tag-exact `PROJECT_VER` on a clean, tagged HEAD, validated before Docker starts) and an optional `SKYPANE_VERSION_LABEL` for bench images; non-release builds now restrict `git describe` to `--match 'fw-v*'` so they can never print a bare release tag
- Completed `firmware/SIGNING.md`: resolved-configuration record, what is signed and why, release tag convention, the human-only key-generation/backup/rotation procedure, a forbidden list, and local bench-image signing

## Task Commits

Each task was committed atomically:

1. **Task 1: Gate G-41 (Phase 41 complete on main)** - read-only, no commit (all four checks passed against `origin/main`)
2. **Task 2: Confirm the Kconfig chain in the container, then set rollback, signed apps, floor and wake budget** - `24bdd684` (feat)
3. **Task 3: Release-tag PROJECT_VER and the signing-key procedure** - `88df2ba4` (feat)

_No TDD tasks in this plan._

## Files Created/Modified
- `firmware/SIGNING.md` - new: resolved Kconfig chain record, key-generation/backup/rotation procedure, release tag convention, forbidden list, local bench-image signing
- `firmware/sdkconfig.defaults` - rollback + signed-app-verification-without-secure-boot enabled, RSA scheme pinned, build-time signing explicitly off, CA-bundle comment updated for the OTA delivery channel
- `firmware/main/Kconfig.projbuild` - `SKYPANE_OTA_FLOOR_VERSION` added, `SKYPANE_WAKE_BUDGET_S` default raised 300->360
- `firmware/build.sh` - `SKYPANE_RELEASE_TAG`/`SKYPANE_VERSION_LABEL` release mode, `git describe --match 'fw-v*'` restriction outside release mode
- `firmware/tests/check_production_config.sh` - static mode requires the new lines and fails on any eFuse-burning option (mutation-proven); built mode requires the resolved chain and logs it

## Decisions Made
- Ran a **clean** `idf.py reconfigure` (fresh build dir), not an incremental one, after discovering the incremental form silently carries over a previously-resolved `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=y` even when the defaults file is edited to turn it off -- documented in `firmware/SIGNING.md` so a future re-confirmation doesn't repeat the mistake
- Went beyond the plan's minimum verification and ran a real end-to-end container build plus the built-mode check against the real artifact, not just `idf.py reconfigure`, to have direct evidence the firmware.yml CI job will pass rather than inferring it

## Deviations from Plan

None - plan executed exactly as written. The one correction (clean vs. incremental reconfigure) was discovered and resolved entirely within Task 2's own "confirm before relying" verification step, not a deviation from the plan's instructions.

## Issues Encountered

An incremental `idf.py reconfigure` against an already-resolved scratch build directory initially reported `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=y` even after adding an explicit `# CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES is not set` line to the scratch defaults file, because the existing `build-kconfig/sdkconfig` from the prior run took precedence over the new default. Deleting the build directory and reconfiguring clean resolved it correctly to "not set", which then matched on a second confirmation run against the real committed defaults. This is recorded in `firmware/SIGNING.md`'s "Resolved configuration" section for anyone re-confirming this chain later.

## User Setup Required

None - no external service configuration required. The private signing key is generated by a human-run procedure documented in `firmware/SIGNING.md`; no key material was generated or touched during this plan.

## Next Phase Readiness
- The Kconfig chain OTA-02/OTA-03/OTA-04 depend on is now committed, container-confirmed, and CI-guarded; later device-side OTA-apply plans in this phase can build against it directly
- `SKYPANE_OTA_FLOOR_VERSION` exists for plan 42-02's `ota_policy.c`/`validate.c` (already landed) to eventually read against
- `firmware/build.sh`'s release mode is ready for the tag-triggered CI signing job a later plan will add to `firmware.yml`; `firmware/SIGNING.md` documents the exact secret name (`FW_SIGNING_KEY`) and environment (`firmware-signing`) that job should assume
- The one-time key-generation ceremony itself remains a human checkpoint in a later plan, as the phase context specifies -- no key exists yet

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*
