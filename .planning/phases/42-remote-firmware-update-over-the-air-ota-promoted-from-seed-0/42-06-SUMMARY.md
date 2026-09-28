---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 06
subsystem: firmware
tags: [esp-idf, nvs, provisioning, wifi, credentials, ota-enabler]

requires:
  - phase: 41-docs-repository-hygiene-and-closing-re-audit
    provides: "Phase 36/37 INT/SEC baseline re-verified clean, satisfying gate G-41"
provides:
  - "firmware/main/creds.h / creds.c: pure validators for the provisioned Wi-Fi SSID/password, a dotted-quad IPv4 address, and the all-or-nothing static-IP set"
  - "firmware/main/enrol_secret.c's fp_device_creds_load: reads every provisioned device credential from the secret NVS partition, returns FP_ERR_CONFIG on any missing/invalid value"
  - "firmware/main/wifi.c and api_client.c read credentials from fp_device_creds_load instead of compiled-in secrets.h macros"
  - "firmware/provision.sh writes the Wi-Fi SSID/password, API base and optional static-IP set into the secret NVS partition over USB"
  - "secrets.h/secrets.example.h retired from the build and CI entirely — a CI-built release image carries no credential"
affects: [42-firmware-ota-remaining-plans, hardware-session]

tech-stack:
  added: []
  patterns:
    - "Device credentials live only in the device's own NVS 'secret' partition, written by provision.sh over USB — never compiled into the image, matching the existing enrolment-secret pattern"
    - "Provisioning-script-side validation mirrors the on-device pure validator (creds.c / provision.sh's shell functions), so a value the script accepts is a value the device will accept"

key-files:
  created:
    - firmware/main/creds.h
    - firmware/main/creds.c
    - firmware/tests/test_creds.c
  modified:
    - firmware/main/enrol_secret.c
    - firmware/main/enrol_secret.h
    - firmware/main/nvs_schema.h
    - firmware/main/wifi.c
    - firmware/main/wifi.h
    - firmware/main/api_client.c
    - firmware/main/api_client.h
    - firmware/provision.sh
    - firmware/VENDOR.md
    - .github/workflows/firmware.yml
    - README.md
    - SECURITY.md
    - server/README.md
    - stub-server/README.md

key-decisions:
  - "D-20 (device credentials move out of the firmware image) implemented as specified: NVS 'secret' partition, provision.sh, no compile-time credential macros anywhere"
  - "wifi.h and api_client.h were edited even though only their .c siblings were in this task's own <files> list, because Task 2's own verify grep scans every firmware/main/*.h and both headers' doc comments still named the removed secrets.h macros"
  - "api_base_get() now calls fp_device_creds_load() directly rather than caching credentials across calls, matching the plan's documented interface contract (api_client.c -> enrol_secret.c via fp_device_creds_load)"

requirements-completed: []

coverage:
  - id: D1
    description: "Pure validators (fp_wifi_ssid_valid/fp_wifi_pass_valid/fp_ipv4_valid/fp_static_ip_set_valid) matching the plan's exact behavior table"
    verification:
      - kind: unit
        ref: "firmware/tests/test_creds.c (13 suites via firmware/tests/run_host_tests.sh)"
        status: pass
    human_judgment: false
  - id: D2
    description: "fp_device_creds_load reads every provisioned credential from the secret NVS partition and fails closed (FP_ERR_CONFIG, zeroed struct) on any missing/invalid value, without ever logging a value"
    verification:
      - kind: integration
        ref: "./firmware/build.sh (container build, no firmware/main/secrets.h present) — compiles and links cleanly"
      - kind: other
        ref: "grep -c 'ESP_LOG.*pass\\|ESP_LOG.*ssid' firmware/main/enrol_secret.c firmware/main/wifi.c -> 0 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "wifi.c and api_client.c read credentials at runtime instead of compile-time secrets.h macros; no firmware source references secrets.h or the removed SKYPANE_* macros"
    verification:
      - kind: other
        ref: "grep -rn 'secrets\\.h|SKYPANE_WIFI_SSID|SKYPANE_WIFI_PASS|SKYPANE_API_BASE\\b|SKYPANE_API_BASE_DEV|SKYPANE_STATIC_IP' firmware/main/*.c firmware/main/*.h -> empty"
        status: pass
    human_judgment: false
  - id: D4
    description: "provision.sh writes --wifi-ssid/--api-base (required) and the optional static-IP set into secret.csv, password via env or no-echo prompt, never printed"
    verification:
      - kind: other
        ref: "sh firmware/provision.sh --dry-run aa:bb:cc:dd:ee:ff --wifi-ssid test-net --api-base https://example.invalid (prints wifi_ssid/api_base/<redacted>, no leaked password)"
        status: pass
      - kind: other
        ref: "sh firmware/provision.sh --dry-run ... --api-base http://10.0.0.2:8642 (no --allow-http-base) exits 2"
        status: pass
    human_judgment: false
  - id: D5
    description: "CI builds without a compile-only credentials header; secrets.example.h retired; docs no longer describe the secrets.h flow"
    verification:
      - kind: integration
        ref: "./firmware/build.sh + sh firmware/tests/check_production_config.sh built firmware/build-ee02 (container run, no secrets.h) -> PASS"
        status: pass
      - kind: other
        ref: "grep -rn 'secrets\\.h' README.md SECURITY.md server/README.md stub-server/README.md .github/workflows/firmware.yml -> empty; test ! -e firmware/main/secrets.example.h"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 06: Provisioned device credentials over the secret NVS partition Summary

**Wi-Fi SSID/password, API base and optional static-IP set move out of the compiled firmware image into the device's `secret` NVS partition, written by an extended `firmware/provision.sh`, so a CI-built release image carries no credential and is identical for every device (D-20).**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-28
- **Tasks:** 3 (Task 1 read-only gate check, Tasks 2-3 implementation)
- **Files modified:** 18 (3 created, 14 modified, 1 deleted)

## Accomplishments
- New `firmware/main/creds.h`/`creds.c`: pure validators for the Wi-Fi SSID, Wi-Fi password, a dotted-quad IPv4 address, and the all-or-nothing static-IP set — TDD RED (stub rejecting everything, test fails) then GREEN (real rules, `firmware/tests/test_creds.c` passes as one of 13 host suites).
- `firmware/main/enrol_secret.c`'s new `fp_device_creds_load()` reads the Wi-Fi SSID/password, API base and optional static-IP set from the same `secret` NVS partition the enrolment secret already lives on, validates each with `creds.c`, and fails closed (`FP_ERR_CONFIG`, zeroed output, no crash) on any missing or invalid value — logging only which key was at fault, never a value.
- `firmware/main/wifi.c`'s `fp_wifi_connect()` loads credentials before any radio activity and applies the static-IP set as a runtime branch instead of a compile-time `#ifdef`; `firmware/main/api_client.c`'s `api_base_get()` reads the provisioned API base the same way, dropping the `SKYPANE_API_BASE`/`_DEV` compile-time split (a dev board's `http://` base is now provisioned data, still gated by `CONFIG_SKYPANE_ALLOW_HTTP`).
- `firmware/provision.sh` gains `--wifi-ssid`/`--api-base` (required in both real and `--dry-run` modes), the optional `--static-ip`/`--static-mask`/`--static-gw`/`--static-dns` set (all four or none), and `--allow-http-base`. The Wi-Fi password comes from `$SKYPANE_WIFI_PASS` or a no-echo prompt with a trap restoring the terminal — never on the command line, never echoed, never logged. `--dry-run` never prompts and shows the generated CSV with the password redacted.
- `firmware/main/secrets.example.h` is deleted, `.github/workflows/firmware.yml`'s "Create compile-only credentials header" step is removed, and every mention of the old `secrets.h` flow in `VENDOR.md`, `README.md`, `SECURITY.md`, `server/README.md` and `stub-server/README.md` is rewritten to describe the provisioned-credential flow.
- Proved end-to-end with a real container build (`./firmware/build.sh`, no `firmware/main/secrets.h` present anywhere on disk) followed by `firmware/tests/check_production_config.sh built`, both green — the exact scenario CI's `build` job will run once this branch merges.

## Task Commits

Each task was committed atomically:

1. **Task 1: Gate G-41 (Phase 41 complete on main)** - read-only check, no edits, no commit (all four checks against `origin/main` passed: `41-VERIFICATION.md` status passed, 0 unchecked Phase 41 ROADMAP boxes, `origin/main` an ancestor of HEAD, and 42-CONTEXT.md's D-20 confirmed on `origin/main`).
2. **Task 2: Provisioned credentials in firmware (validators, loader, Wi-Fi, API base)** - TDD, two commits:
   - `1a77779f` (test) RED phase: `creds.h` declared, `creds.c` stubbed to reject everything, `test_creds.c` added and confirmed failing.
   - `fc375d04` (feat) GREEN phase: real validator rules, `fp_device_creds_load`, `wifi.c`/`api_client.c` integration, `wifi.h`/`api_client.h` doc-comment fixes.
3. **Task 3: Provisioning, CI build and documentation** - `cb1feb91` (feat): `provision.sh` extension, `firmware.yml` step removal, `secrets.example.h` deletion, doc updates across five files.

**Plan metadata:** (this commit, docs: complete plan)

_Note: Task 2 is a TDD task (RED -> GREEN); Task 3 had no separate REFACTOR commit since no cleanup was needed after GREEN._

## Files Created/Modified
- `firmware/main/creds.h` / `creds.c` - pure Wi-Fi SSID/password/IPv4/static-IP-set validators, host-tested
- `firmware/tests/test_creds.c` - host test suite for creds.c, discovered by `run_host_tests.sh`'s naming convention
- `firmware/main/enrol_secret.c` / `.h` - `fp_device_creds_load()`: reads and validates every provisioned credential from the secret NVS partition
- `firmware/main/nvs_schema.h` - seven new `FP_NVS_*` key names (wifi_ssid, wifi_pass, api_base, static_ip/mask/gw/dns) on the existing secret partition
- `firmware/main/wifi.c` / `.h` - runtime credential load replaces compiled-in `SKYPANE_WIFI_*`/`SKYPANE_STATIC_*` macros
- `firmware/main/api_client.c` / `.h` - `api_base_get()` reads the provisioned API base; `SKYPANE_API_BASE`/`_DEV` macros and `secrets.h` include dropped
- `firmware/provision.sh` - `--wifi-ssid`/`--api-base`/optional static-IP set/`--allow-http-base`, no-echo password prompt, dry-run CSV preview
- `firmware/VENDOR.md` - wifi.c/api_client.c/nvs_schema.h/sdkconfig.defaults/Kconfig.projbuild rows updated; secrets.example.h entry replaced with a new creds.c entry; provision.sh/enrol_secret.c descriptions extended
- `.github/workflows/firmware.yml` - "Create compile-only credentials header" step removed
- `README.md`, `SECURITY.md`, `server/README.md`, `stub-server/README.md` - every `secrets.h` mention rewritten to describe `firmware/provision.sh`
- `firmware/main/secrets.example.h` - deleted (no longer used; `secrets.h` stays gitignored)

## Decisions Made
- D-20 implemented exactly as specified in 42-CONTEXT.md: credentials live only in the device's own NVS `secret` partition, written by `firmware/provision.sh` over USB; no compile-time credential macro survives anywhere in `firmware/main/`.
- `api_base_get()` calls `fp_device_creds_load()` directly on every call (setup and display) rather than caching credentials across the wake, matching the plan's own documented interface contract (`api_client.c -> enrol_secret.c via fp_device_creds_load`) rather than threading a loaded-once struct through more of the call chain.
- Static-IP application moved from `fp_wifi_platform_init()` (compile-time `#ifdef`, ran once per netif creation) to `fp_wifi_connect()` (runtime, after credentials load) — `fp_wifi_platform_init()` is internal-only (not called from outside `wifi.c`), so this stayed a same-file refactor with no public signature change.
- `provision.sh`'s CSV writer refuses any credential value containing a comma or newline rather than implementing `nvs_partition_gen.py`'s CSV quoting rules — the plan explicitly offered this as the simpler alternative, and no legitimate SSID/password/URL/IP value needs either character.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Edited `wifi.h` and `api_client.h`, outside Task 2's own `<files>` list**
- **Found during:** Task 2
- **Issue:** Task 2's `<files>` tag lists only `wifi.c`/`api_client.c`, but its own `<verify>` grep (`firmware/main/*.c firmware/main/*.h`) scans every header too, and both `wifi.h` and `api_client.h` carried doc comments naming the removed `secrets.h`/`SKYPANE_WIFI_SSID`/`SKYPANE_WIFI_PASS`/`SKYPANE_API_BASE` macros — leaving them would fail the plan's own verify command.
- **Fix:** Rewrote the stale doc comments in both headers to describe the provisioned-NVS credential flow; no declaration changed.
- **Files modified:** `firmware/main/wifi.h`, `firmware/main/api_client.h`
- **Verification:** `grep -rn 'secrets\.h|SKYPANE_...' firmware/main/*.c firmware/main/*.h` returns empty
- **Committed in:** `fc375d04` (Task 2 GREEN commit)

**2. [Rule 1 - Bug] Removed `D-20` decision-ID citations from two comments**
- **Found during:** Task 2 (pre-commit `check_comment_history.py check`)
- **Issue:** Initial doc comments in `enrol_secret.h` and `nvs_schema.h` cited "(D-20)" — forbidden by the project's no-decision-IDs-in-comments rule, which `scripts/check_comment_history.py check` enforces and blocks the commit on.
- **Fix:** Reworded both comments to keep the rationale (credentials leave the image, image is identical for every device) without the decision-ID citation.
- **Files modified:** `firmware/main/enrol_secret.h`, `firmware/main/nvs_schema.h`
- **Verification:** `server/.venv/bin/python3 scripts/check_comment_history.py check` exits 0
- **Committed in:** `fc375d04` (Task 2 GREEN commit)

**3. [Rule 1 - Bug] Fixed a pre-existing `shellcheck` warning (SC1007) on `provision.sh`'s unrelated `SCRIPT_DIR` line**
- **Found during:** Task 3, while satisfying the plan's own "shellcheck firmware/provision.sh is clean if shellcheck is installed" acceptance criterion
- **Issue:** `CDPATH= cd -- ...` (pre-existing, unrelated to this plan's changes) triggers SC1007; the file was not shellcheck-clean before this plan touched it.
- **Fix:** Changed to `CDPATH='' cd -- ...`, behaviorally identical, no warning.
- **Files modified:** `firmware/provision.sh`
- **Verification:** `shellcheck firmware/provision.sh` exits 0
- **Committed in:** `cb1feb91` (Task 3 commit)

**4. [Rule 1 - Bug] Grouped `secret.csv` appends to satisfy `shellcheck` SC2129**
- **Found during:** Task 3, same shellcheck pass
- **Issue:** Seven sequential `>> "${WORK}/secret.csv"` redirects (up from the original two) triggered shellcheck's SC2129 style warning.
- **Fix:** Wrapped the writes in a single `{ ...; } > "${WORK}/secret.csv"` block — same output, one redirect.
- **Files modified:** `firmware/provision.sh`
- **Verification:** `shellcheck firmware/provision.sh` exits 0
- **Committed in:** `cb1feb91` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (1 blocking/verify-required header edit, 1 comment-history bug, 2 shellcheck style fixes)
**Impact on plan:** All four were required to satisfy this plan's own verify commands and acceptance criteria. No scope creep — no file outside the plan's stated intent (docs currently describing the credential flow, or code this plan's own verify grep touches) was edited.

## Issues Encountered
None beyond the deviations above.

## User Setup Required
None - no external service configuration required. (The real frame's re-provisioning over USB with real Wi-Fi credentials happens during the hardware session, per 42-CONTEXT.md D-20; this plan does not touch or require a physical device.)

## Next Phase Readiness
- The firmware image no longer carries any credential, unblocking the rest of Phase 42's OTA work (CI can now build and publish a release image that is safe to store on the VPS and in backups, per D-17/D-18).
- `firmware/provision.sh` is ready for the hardware session's real re-provisioning step (D-20's "the real frame is re-provisioned over USB during the hardware session").
- No blockers for subsequent 42-* plans.

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

All created files present on disk (`firmware/main/creds.h`, `firmware/main/creds.c`,
`firmware/tests/test_creds.c`, `firmware/main/enrol_secret.c`, `firmware/provision.sh`,
this SUMMARY.md); all three task commits (`1a77779f`, `fc375d04`, `cb1feb91`) found in
`git log --oneline --all`.
