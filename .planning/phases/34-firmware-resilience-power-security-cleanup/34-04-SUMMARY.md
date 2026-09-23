---
phase: 34-firmware-resilience-power-security-cleanup
plan: 04
subsystem: infra
tags: [kconfig, sdkconfig, tls, mbedtls, nvs-partition, ci, esp-idf]

# Dependency graph
requires: []
provides:
  - "CONFIG_SKYPANE_ALLOW_HTTP, CONFIG_SKYPANE_WAKE_BUDGET_S, CONFIG_SKYPANE_TLS_SESSION_PERSIST and the CONFIG_SKYPANE_FAULT_INJECT choice in firmware/main/Kconfig.projbuild"
  - "firmware/sdkconfig.dev.defaults, the dev-only http overlay"
  - "a dedicated 12 KB secret NVS partition at 0x13000 in firmware/partitions.csv"
  - "firmware/main/certs/isrg-root-x1.pem and isrg-root-x2.pem, an ISRG-only mbedtls custom CA bundle wired via sdkconfig.defaults"
  - "production hardening in sdkconfig.defaults: TWDT panic-on-timeout, PSRAM memtest off, DHCP restore-last-IP, TLS session tickets + custom transport, app rollback off"
  - "firmware/tests/check_production_config.sh (static + built modes)"
  - "firmware host tests + production-config checks wired into .github/workflows/firmware.yml"
affects: [phase-34-plan-05-provision-script, phase-34-plan-06-firmware-nvs-secret, phase-34-plan-07, phase-34-plan-08-fault-injection, phase-34-plan-09-tls-session-reuse, phase-34-plan-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Production-configuration proof as a static (no Docker) check plus a built (post idf.py build) check, both run in CI before/after the image build"
    - "Dev-only Kconfig opt-ins (SKYPANE_ALLOW_HTTP, SKYPANE_FAULT_INJECT_*) default off, enabled only by a separate overlay file (sdkconfig.dev.defaults) never referenced by build.sh's production invocation"
    - "New NVS-type partitions are added only inside an already-verified free flash gap, never by regenerating an existing partition"

key-files:
  created:
    - firmware/sdkconfig.dev.defaults
    - firmware/main/certs/isrg-root-x1.pem
    - firmware/main/certs/isrg-root-x2.pem
    - firmware/tests/check_production_config.sh
  modified:
    - firmware/main/Kconfig.projbuild
    - firmware/sdkconfig.defaults
    - firmware/partitions.csv
    - .github/workflows/firmware.yml

key-decisions:
  - "Secret partition sized 0x3000 (three 4 KB pages, the NVS partition-generator minimum) rather than RESEARCH.md's earlier 0x1000 estimate - the plan's locked task text supersedes the research note, and 0x3000 still fits inside the 0xD000 free gap without moving factory"
  - "check_production_config.sh hard-codes both pinned ISRG fingerprints rather than reading them from a shared file, so the check has no dependency on the certs directory being trustworthy at check time"
  - "static mode ignores comment lines (including Kconfig's own \"# CONFIG_X is not set\" convention) when scanning for a bad CONFIG_SKYPANE_ALLOW_HTTP=y / CONFIG_SKYPANE_FAULT_INJECT_*=y match, so a disabled option's own auto-generated comment can never trip the check"

requirements-completed: [FW-02, FW-06, FW-07, FW-09, FW-10, FW-12, FW-13]

# Metrics
duration: ~25min
completed: 2026-09-23
---

# Phase 34 Plan 04: Kconfig, ISRG-only CA bundle, secret partition, CI production check Summary

**New SkyPane Kconfig options (https-only switch, wake budget, TLS session persist, fault-injection choice), a two-root ISRG CA bundle replacing the full mbedtls trust store, a dedicated secret NVS partition, and a two-mode production-configuration checker wired into firmware CI before and after the image build.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-23T14:20:00Z (approx.)
- **Completed:** 2026-09-23T14:44:15Z
- **Tasks:** 3
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments
- `firmware/main/Kconfig.projbuild`: deleted the unused `FP_API_BASE`/`FP_DEV_PROVISION_SECRET` orphans; added `SKYPANE_ALLOW_HTTP` (default `n`), `SKYPANE_WAKE_BUDGET_S` (180-900 s, default 300), `SKYPANE_TLS_SESSION_PERSIST` (default `y`, depends on `ESP_TLS_CLIENT_SESSION_TICKETS`) and the `SKYPANE_FAULT_INJECT` choice (default `NONE`) to the top-level menu
- `firmware/sdkconfig.dev.defaults`: new dev-only overlay, exactly one line (`CONFIG_SKYPANE_ALLOW_HTTP=y`), never referenced by `build.sh`'s production invocation
- `firmware/partitions.csv`: added the `secret` NVS partition (0x13000, 0x3000) in the existing free gap between `nvs_keys` and `factory`; `nvs`, `otadata`, `phy_init`, `nvs_keys` and `factory` byte-identical to before
- `firmware/main/certs/isrg-root-x1.pem` and `isrg-root-x2.pem`: downloaded from letsencrypt.org, SHA-256 fingerprints verified against the pinned values, then cross-checked against `curl.se/ca/cacert.pem` (Mozilla's own CA store distribution) — both the certificate bytes and the fingerprints match across both independent sources
- `firmware/sdkconfig.defaults`: custom mbedtls bundle restricted to those two roots (`MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE` + `MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE` + path), TWDT panic-on-timeout, PSRAM memtest off, DHCP restore-last-IP with ARP check off, TLS session tickets + custom transport on, app rollback off (no OTA yet), and the misleading "watchdog on everything" comment corrected
- `firmware/tests/check_production_config.sh`: `static` mode (no Docker) checks defaults files, partitions.csv and the certs directory; `built <dir>` mode checks a finished `idf.py build`'s generated sdkconfig, `skypane.bin` (absence of the `SKYPANE-FAULT-INJECT` marker) and `project_description.json`'s `project_version`
- `.github/workflows/firmware.yml`: `fetch-depth: 0` on checkout, host tests + static check before the build, built check after it; `.github/workflows/ci.yml` untouched
- Verified the full chain on real hardware toolchain: `rm -rf firmware/build-ee02 && ./firmware/build.sh` (ESP-IDF v5.3.1 container) succeeded, and `check_production_config.sh built firmware/build-ee02` printed `PASS` against the actual generated sdkconfig and image

## Task Commits

Each task was committed atomically:

1. **Task 1: Kconfig options, dev overlay and the secret partition** - `fe68d00` (feat)
2. **Task 2: sdkconfig.defaults changes and the ISRG-only CA bundle** - `334b3ef` (feat)
3. **Task 3: Production-configuration checker and CI wiring** - `ade7e2f` (feat)

**Plan metadata:** committed in this same response, immediately after this file (docs: complete plan)

## Files Created/Modified
- `firmware/main/Kconfig.projbuild` - orphan `FP_API_BASE`/`FP_DEV_PROVISION_SECRET` removed; `SKYPANE_ALLOW_HTTP`, `SKYPANE_WAKE_BUDGET_S`, `SKYPANE_TLS_SESSION_PERSIST`, `SKYPANE_FAULT_INJECT` choice added to the top-level menu
- `firmware/sdkconfig.defaults` - rollback off, TWDT panic on, PSRAM memtest off, DHCP restore-last-IP/no-ARP-check, ISRG-only custom cert bundle, TLS session tickets + custom transport, orphan `CONFIG_FP_*` lines removed
- `firmware/sdkconfig.dev.defaults` - new dev-only overlay enabling `CONFIG_SKYPANE_ALLOW_HTTP`
- `firmware/partitions.csv` - `secret` NVS partition added at 0x13000/0x3000
- `firmware/main/certs/isrg-root-x1.pem` - ISRG Root X1, fingerprint-verified
- `firmware/main/certs/isrg-root-x2.pem` - ISRG Root X2, fingerprint-verified
- `firmware/tests/check_production_config.sh` - new static + built production-configuration checker
- `.github/workflows/firmware.yml` - host tests, static check, build, built check wired in order; `fetch-depth: 0` added

## Decisions Made
- Secret partition sized `0x3000` per the plan's locked task text (three 4 KB pages, the NVS partition-generator's practical minimum), superseding RESEARCH.md's earlier `0x1000` estimate; still fits cleanly inside the `0xD000` free gap with `factory` unmoved
- `check_production_config.sh` hard-codes both pinned ISRG fingerprints directly in the script rather than reading them from `main/certs/` itself, so the fingerprint check has no dependency on the very files it is verifying
- Second independent source for the fingerprint cross-check was `curl.se/ca/cacert.pem` (Mozilla's own CA distribution) rather than a browser trust store screenshot — both the SHA-256 fingerprints and the raw certificate bytes matched exactly against the letsencrypt.org download

## Deviations from Plan

None — plan executed exactly as written. `project_description.json`'s `project_version` is still the hardcoded `"0.1.0-p1"` (not yet `git describe`-derived — that is FW-15, out of this plan's scope), which the built check's non-empty/`!= "1"` assertion correctly accepts as valid.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

- All config-level symbols the later waves compile against now exist with safe defaults: `SKYPANE_ALLOW_HTTP`, `SKYPANE_WAKE_BUDGET_S`, `SKYPANE_TLS_SESSION_PERSIST`, `SKYPANE_FAULT_INJECT_*`, the `secret` NVS partition, and the ISRG-only cert bundle.
- `firmware/tests/check_production_config.sh` is available for plans 34-08 (fault injection) and 34-09 (TLS session reuse) to self-check against without re-deriving the fingerprint/partition logic.
- Firmware CI (`firmware.yml`) now proves both "http is off" and "fault injection is off" on every push/PR touching `firmware/**`, closing success criterion 3 (host tests in CI) and the D-34-04 production-proof requirement.
- No blockers. `firmware/sdkconfig.defaults`, `firmware/main/Kconfig.projbuild` and `firmware/partitions.csv` remain single-owner for this plan; later plans in the phase add C code against the symbols landed here, not further Kconfig/partition edits.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 9 created/modified files (Kconfig.projbuild, sdkconfig.defaults,
sdkconfig.dev.defaults, partitions.csv, the two ISRG PEMs,
check_production_config.sh, firmware.yml, this SUMMARY.md) confirmed
present on disk; all 3 task commit hashes (`fe68d00`, `334b3ef`,
`ade7e2f`) confirmed in `git log`.
