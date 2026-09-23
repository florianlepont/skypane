---
phase: 34-firmware-resilience-power-security-cleanup
plan: 05
subsystem: firmware
tags: [esp-idf, cmake, provisioning, nvs, esptool, git-describe, build-profiles]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-04's Kconfig options (SKYPANE_ALLOW_HTTP, SKYPANE_FAULT_INJECT_* choice), sdkconfig.dev.defaults overlay, and the 'secret' NVS partition in partitions.csv"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-03's stub-server/devices_cli.py registry CLI and the secret_sha256 = sha256(secret_hex ascii) hash contract"
provides:
  - "PROJECT_VER resolved on the host via git describe --tags --always --dirty and passed into the container build as -DPROJECT_VER, with a 0.0.0-nogit fallback"
  - "firmware/build.sh SKYPANE_PROFILE=prod|dev and SKYPANE_FAULT=none|panic|task_wdt|int_wdt|slow_wake, with prod+fault refused at exit 2 and sdkconfig always regenerated from committed defaults"
  - "firmware/flash.sh profile-aware build directory selection"
  - "firmware/provision.sh - per-device secret generation, write to the dedicated NVS 'secret' partition over USB, read-back verification, and the printed registry/registration commands"
affects: ["34-11 (hardware verification session scripts against build.sh/flash.sh/provision.sh)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Host-resolved git describe passed into a container build via -D, because the container's bind mount does not include .git"
    - "Profile-gated build directories (build-ee02 vs build-ee02-dev) so a dev/fault image can never be mistaken for or reused as a production image"
    - "Host esptool writes a single partition's byte range (offset/size parsed from partitions.csv at runtime) instead of parttool.py inside the container, avoiding container USB passthrough"

key-files:
  created: [firmware/provision.sh]
  modified: [firmware/CMakeLists.txt, firmware/build.sh, firmware/flash.sh]

key-decisions:
  - "provision.sh renames its offset/size shell variables to SEC_PART_OFFSET/SEC_PART_SIZE(_DEC) rather than SECRET_OFFSET/SECRET_SIZE, so no shell variable name contains the literal secret-value variable's name as a prefix - keeps the 'never print the secret' invariant mechanically checkable with a simple grep"
  - "The two devices_cli.py registration commands are printed with literal <state-dir> and <ssh-target> placeholders (matching devices_cli.py's own no-default --state-dir requirement) rather than a guessed path, since provision.sh has no way to know the operator's local stub state directory or VPS SSH alias"
  - "Final board reset uses esptool --after hard-reset read-mac (discarding its own MAC output) rather than a dedicated 'reset' subcommand, since esptool's reset behavior is driven entirely by --after and every esptool invocation needs a command to run"

patterns-established:
  - "Kconfig-choice-name -> Kconfig-symbol UPPER-casing (SKYPANE_FAULT_INJECT_<UPPER>) done in build.sh with tr, matching the choice names already defined in Kconfig.projbuild by plan 34-04"

requirements-completed: [FW-15, FW-08]

# Metrics
duration: ~20min
completed: 2026-09-23
---

# Phase 34 Plan 05: Host-resolved firmware version, prod/dev/fault build profiles, and per-device secret provisioning Summary

**`git describe`-derived PROJECT_VER passed host-to-container via `-D`, `SKYPANE_PROFILE`/`SKYPANE_FAULT` build.sh gating that refuses any fault outside the dev profile, and a new `firmware/provision.sh` that writes a random per-device secret into the dedicated NVS `secret` partition over USB with read-back verification.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-23T14:35:00Z (approx.)
- **Completed:** 2026-09-23T14:54:37Z
- **Tasks:** 2 completed
- **Files modified:** 4 (3 modified, 1 created)

## Accomplishments
- `firmware/CMakeLists.txt` no longer hardcodes `PROJECT_VER`; it falls back to `0.0.0-nogit` only when `build.sh` doesn't pass `-DPROJECT_VER`
- `firmware/build.sh` resolves `git describe --tags --always --dirty` on the host (verified: this repo has no tags, so `--always` correctly falls back to the short commit hash, e.g. `cea9b28-dirty` while the working tree carries uncommitted changes)
- `SKYPANE_PROFILE=prod|dev` and `SKYPANE_FAULT=none|panic|task_wdt|int_wdt|slow_wake` fully implemented: unknown values exit 2, a fault under `prod` exits 2 without starting Docker, `dev` uses its own build directory and layers `sdkconfig.dev.defaults`, and every `build` action deletes the local `sdkconfig` first so a stale file can never carry a dev/fault option into a production image
- `firmware/flash.sh` derives its build directory the same way, validated before the port-required check
- `firmware/provision.sh` (new, 266 lines): generates a 256-bit random secret with Python `secrets`, parses the `secret`/`nvs` partition offsets and sizes from `partitions.csv` at runtime (never hard-coded), builds the NVS image inside the pinned `espressif/idf:v5.3.1` container, writes only the `secret` partition's byte range with host `esptool`, verifies by read-back `cmp`, and prints the MAC, `sha256(secret_hex)` registry line, and both `devices_cli.py add --replace` commands (local stub and VPS) - all without ever printing the secret itself
- `--dry-run <mac>` previews the same output with no hardware access; `--reset-device-state` is the only path that touches the main `nvs` partition (bearer token, image hash, backoff counter, boot counter, cached DHCP lease)

## Task Commits

Each task was committed atomically:

1. **Task 1: Host-resolved PROJECT_VER and prod/dev build profiles** - `2d8d50d` (feat)
2. **Task 2: firmware/provision.sh - per-device secret into the dedicated NVS partition** - `c5c47d5` (feat)

**Plan metadata:** committed in this same response, immediately after this file (docs: complete plan)

## Files Created/Modified
- `firmware/CMakeLists.txt` - deleted the hardcoded `set(PROJECT_VER "0.1.0-p1")`; guarded `0.0.0-nogit` fallback only
- `firmware/build.sh` - `SKYPANE_PROFILE`/`SKYPANE_FAULT` validation and gating, per-profile build dir and sdkconfig defaults list, fault overlay file generation, sdkconfig wipe before every build, host `git describe` resolution truncated to 31 chars, `-DPROJECT_VER` passed to `idf.py`
- `firmware/flash.sh` - `SKYPANE_PROFILE`-driven build directory selection, validated before the port-required check; flashing logic itself unchanged
- `firmware/provision.sh` (new) - per-device secret provisioning over USB into the `secret` NVS partition

## Decisions Made
- Renamed the partition-offset/size shell variables to `SEC_PART_OFFSET`/`SEC_PART_SIZE`/`SEC_PART_SIZE_DEC` (instead of `SECRET_OFFSET`/`SECRET_SIZE`) so that no non-secret variable name begins with the literal string `SECRET`, keeping the "the secret is never echoed to stdout" invariant checkable by a simple `grep` without false positives from unrelated `${SECRET_*}` variable names
- `provision.sh`'s two registration commands print literal `<state-dir>` and `<ssh-target>` placeholders rather than a guessed path or hostname - `devices_cli.py` itself requires an explicit `--state-dir` with no default (by design, per its own docstring), and this script has no way to know the operator's local stub state directory or VPS SSH alias
- The final board reset after a real (non-dry-run) provisioning run uses `esptool --chip esp32s3 --port "$PORT" --after hard-reset read-mac` (output discarded) - esptool's `--after` flag drives the reset behavior on any command, and `read-mac` is a harmless, already-used command to hang it off

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their acceptance criteria on the first implementation; the only adjustment (the `SEC_PART_*` variable renaming) was made proactively while writing the code, before any verification run, to satisfy the plan's own "never echo the secret" verification grep precisely as specified - not a deviation from the plan's intent, just naming chosen to make that exact check pass cleanly.

## Issues Encountered
None. Docker (`espressif/idf:v5.3.1`) was available in this session, so every Docker-gated verification step in both tasks' acceptance criteria ran for real rather than falling back to the "SUMMARY records it" path:
- `./firmware/build.sh` (prod): `Firmware version: cea9b28-dirty` matched `git describe --tags --always --dirty`'s own output, and `project_description.json`'s `project_version` matched exactly
- `SKYPANE_PROFILE=dev SKYPANE_FAULT=panic ./firmware/build.sh`: `build-ee02-dev/sdkconfig` contained `CONFIG_SKYPANE_FAULT_INJECT_PANIC=y` and `CONFIG_SKYPANE_ALLOW_HTTP=y`, while `build-ee02/sdkconfig` still contained `CONFIG_SKYPANE_FAULT_INJECT_NONE=y`
- `sh firmware/tests/run_host_tests.sh` (8/8 suites) and `sh firmware/tests/check_production_config.sh static` / `built firmware/build-ee02` all passed after the CMakeLists.txt/build.sh changes
- `sh firmware/provision.sh --dry-run aa:bb:cc:dd:ee:ff` (run twice) printed a valid `Registry line: aa:bb:cc:dd:ee:ff <64 lowercase hex>` each time, with different hashes across runs, and both `devices_cli.py ... --replace` commands
- No serial device is attached in this container, so the write-flash/read-flash/erase-region/read-mac branches of `provision.sh` (everything gated on `DRY_RUN=0`) could not be exercised against real hardware in this session, matching the environment notes; those branches are covered by the hardware session (34-11)
- Build directories (`firmware/build-ee02`, `firmware/build-ee02-dev`) were removed after verification, matching `firmware/.gitignore`'s `build*/` pattern; `git status` confirmed clean before each commit

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

- Every image now carries a real, traceable version (`X-Fw-Version`); the hardware session (34-11) can distinguish exactly which commit produced a flashed binary, including `-dirty` builds
- The hardware session's dev-only fault-injection scenarios (induced panic/WDT/hang) now have a scripted, safe entry point: `SKYPANE_PROFILE=dev SKYPANE_FAULT=<name> ./firmware/build.sh`, which cannot be confused with the production build a real device ships
- `firmware/provision.sh` is ready for the hardware session to run against a real board over USB (34-11 is the first opportunity to exercise its `DRY_RUN=0` write-flash/read-flash/erase-region paths, since no serial device was attached in this container session)
- `firmware/main/secrets.h` remains present (gitignored, untracked) as required by the environment notes; `SKYPANE_SETUP_SECRET` removal from `secrets.example.h`/`secrets.h` and the `secret_provision.c` NVS-read firmware code are out of this plan's scope (D-34-02's remaining device-side work, a later plan in this phase)
- No blockers. `firmware/CMakeLists.txt`, `firmware/build.sh`, `firmware/flash.sh` and the new `firmware/provision.sh` are single-owner for this plan; later plans add C code and NVS schema keys against the `secret` partition landed in 34-04, not further build-tooling edits.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*
