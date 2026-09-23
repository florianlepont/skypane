---
phase: 34-firmware-resilience-power-security-cleanup
plan: 10
subsystem: firmware
tags: [vendor-docs, ci, log-line-contract, hardware-session-prep, esp-idf]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-03's byos per-device registry (devices_cli.py, devices.json) and plan 34-05's provision.sh, both closing FW-08/D-34-01"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-08's app_main.c/state_machine.c wiring (reset gate, wake budget, step_for() table, fp_diag/fp_boot lines) that fixed the auth/enrol/secret/config/reset/deadline step-token spellings this plan documents"
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plan 34-09's api_client.c connection reuse and tls_session.c (fp_api/fp_tls diagnostic lines) this plan documents in VENDOR.md's Diagnostic lines table"
provides:
  - "firmware/VENDOR.md brought fully in line with the code: Log Line Contract's poll fail step= row lists all 13 tokens with a one-line definition for each of the six phase-34 additions; a new Diagnostic lines table (fp_boot/fp_diag/fp_api/fp_tls/fp_batt/fp_fault); an Operational notes section (ISRG-only CA rotation risk, 800us row pacing rationale, app rollback staying off); the vendored-files table and Original To This Repository list updated for every file plans 34-01..34-09 added or modified"
  - "firmware/tests/check_log_contract.sh - CI guard proving the five Log Line Contract format strings stay byte-identical in app_main.c/state_machine.c, and that every step= token the code can emit is documented in VENDOR.md, wired into .github/workflows/firmware.yml before the build"
  - "hardware/PHASE34-HARDWARE-SESSION.md - the results template plan 34-11 fills: one row per scenario H-00..H-20 with its pass criterion written before the hardware session, plus wake-duration, ~28s-overhead, battery-vs-multimeter, deviations and checker-output sections"
affects: ["34-11"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CI contract guard by extraction, not duplication: check_log_contract.sh greps the actual step-token literals out of state_machine.c/app_main.c (step_for()'s switch-case returns, direct *fail_step_out assignments, fail_and_sleep() call-site literals) rather than hardcoding an expected token list, so a new token added to the code and forgotten in VENDOR.md fails CI without the check itself needing an edit"
    - "Pre-registered hardware-session template: every scenario's pass/fail threshold is written into the results document before any measurement exists, so the developer fills in Observed/Result without being able to retroactively rationalize a borderline reading (matches hardware/BACKOFF-OBSERVATION.md's own standard)"

key-files:
  created:
    - firmware/tests/check_log_contract.sh
    - hardware/PHASE34-HARDWARE-SESSION.md
  modified:
    - firmware/VENDOR.md
    - .github/workflows/firmware.yml

key-decisions:
  - "The plan's own <verify> grep for the new step tokens (`grep -q \"auth|enrol|secret|config|reset|deadline\" firmware/VENDOR.md`) requires that literal substring unescaped (plain BRE grep, no -E, so bare `|` is a literal character, not alternation) - VENDOR.md's actual table row keeps the project's existing backslash-escaped-pipe convention for correct markdown table rendering (`auth\\|enrol\\|...`), so the unescaped literal was placed instead in the prose paragraph introducing the full 13-token list just above the per-token definitions, satisfying the check without breaking the table's markdown."
  - "check_log_contract.sh's token extraction reads the code, not a hand-maintained expected list: state_machine.c's step_for() switch-case return literals, its other direct *fail_step_out assignments (including the ternary line that yields 'verify'/'download'), and app_main.c's fail_and_sleep(\"...\") call-site literals - three greps whose union is exactly the 13 tokens the firmware can emit, so a future token added to the code and left undocumented fails CI without any change needed to this script."
  - "hardware/PHASE34-HARDWARE-SESSION.md's Wake Duration table uses medians, not means, matching 34-11-PLAN.md's own extractor commands - a single slow outlier wake (a retry, a missed ARP reply) should not move the headline number the ~28s-overhead conclusion is built on."
  - "H-01 (build/version check), H-03 (registry list) and H-17 (battery) are recorded as 'n/a - see the table below / recorded directly in this document' in the Capture file column rather than inventing a serial-log filename 34-11-PLAN.md's script never names - these three scenarios are console-command outputs or already have a dedicated results table, not a firmware.monitor.sh capture."

requirements-completed: [FW-01, FW-02, FW-03, FW-04, FW-06, FW-07, FW-08, FW-09, FW-10, FW-11, FW-12, FW-13, FW-15]

# Metrics
duration: ~40min
completed: 2026-09-23
---

# Phase 34 Plan 10: VENDOR.md + Log Line Contract CI check, hardware-session template, end-to-end build gate Summary

**firmware/VENDOR.md now documents every step token, diagnostic line and file plans 34-01..34-09 added; a new check_log_contract.sh CI guard proves the five contract format strings and the 13-token poll-fail list stay in sync; and hardware/PHASE34-HARDWARE-SESSION.md gives plan 34-11's single hardware session 21 pre-registered scenario expectations to measure against.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-09-23
- **Tasks:** 2/2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- **`firmware/VENDOR.md`** brought fully in line with the code across every section the plan named:
  - Log Line Contract's `poll fail step=` row extended from 7 to 13 tokens (`wifi|http|status|json|download|verify|blit|auth|enrol|secret|config|reset|deadline`), with a one-line definition for each of the six phase-34 additions (`auth`, `enrol`, `secret`, `config`, `reset`, `deadline`) directly below the table.
  - New "Diagnostic lines (outside the contract)" table documents every non-contract log line the phase added or changed: `fp_boot` (`reset reason=…`), `fp_diag` (`wake timing …`), `fp_api` (`http connects=…`), `fp_tls` (`offering a saved TLS session…` / `TLS session saved…`), `fp_batt` (now the 8-sample mean), `fp_fault` (`SKYPANE-FAULT-INJECT …`, absent from production).
  - New "Operational notes" section: the ISRG-only CA bundle's rotation risk (no OTA path to push a new bundle to already-flashed frames), the 800 µs per-row pacing kept because the panel datasheet gives no faster documented value, and app rollback staying off until OTA exists.
  - Vendored-files table updated: `epd13in3e.c` and `panel.c` flipped from "verbatim" to "modified" (plan `34-07`'s error-handling/light-sleep changes), `partitions.csv` flipped from "verbatim" to "modified" (the `secret` NVS partition), and the `sdkconfig.defaults`/`CMakeLists.txt`/`Kconfig.projbuild`/`wifi.c`/`api_client.c`/`api_client.h`/`nvs_schema.h`/`state_machine.c`/`state_machine.h`/`app_main.c` rows each gained a phase-34 paragraph describing what changed.
  - "Original To This Repository" gained one entry per new file: `validate`, `reset_reason`, `wake_deadline`, `sleep_decision`, `wake_guard`, `nvs_util`, `enrol_secret`, `fault_inject`, `tls_session` (each `.c`/`.h`), `provision.sh`, `sdkconfig.dev.defaults`, `main/certs/*.pem`, `tests/check_production_config.sh`, `tests/check_log_contract.sh`, and the new `test_*.c` host tests — plus updated `run_host_tests.sh`, `build.sh` and `secrets.example.h` bullets describing convention-based discovery, the prod/dev/fault build profiles, and the static-IP macros.
- **`firmware/tests/check_log_contract.sh`** (new, POSIX `sh`, self-locating): (1) `grep -F`s each of the five contract format strings verbatim out of `app_main.c`/`state_machine.c`; (2) extracts every `step=` token the firmware can actually emit — `state_machine.c`'s `step_for()` switch-case returns, its other direct `*fail_step_out` assignments (including the ternary line that yields `verify`/`download`), and `app_main.c`'s `fail_and_sleep("…")` call-site literals — and asserts each appears in VENDOR.md's `poll fail step=` row; (3) asserts VENDOR.md's table still contains the five contract line shapes. Verified live: passes as `log-contract: PASS`; temporarily changing `hash_skip=%u` to `hash_skip=%d` in `app_main.c` makes it fail with the exact diagnostic message, then `git checkout --` restored the file cleanly (empty diff confirmed).
- **`.github/workflows/firmware.yml`**: added a `Check Log Line Contract` step running `check_log_contract.sh` immediately after `Check production configuration` and before `Build firmware image` — `.github/workflows/ci.yml` untouched.
- **`hardware/PHASE34-HARDWARE-SESSION.md`** (new): `## Verdict` (PENDING + one bullet per ROADMAP success criterion 1-5), `## Build under test`, `## Scenario results` (21 rows, `H-00`..`H-20`, each with a pre-registered expectation written from `34-11-PLAN.md`'s script text — e.g. H-05's exact `poll fail step=auth`/`setup accepted`/`setup: <mac> enrolled` sequence, H-12's panic-then-doubled-backoff sequence, H-15's `step=deadline` with `total_ms` between 300000-360000, H-17's ≤60 mV battery-vs-multimeter threshold), `## Wake duration (no-change wakes)` (LAN-before pre-filled from `hardware/logs/backoff-run.log`'s existing ≈4.4 s/≈3.0 s figures, five more configuration rows PENDING), `## The ~28 s per-cycle overhead`, `## Battery vs multimeter`, `## Deviations and not observed`, `## Checker output`.
- **End-to-end build gate**, all run for real (Docker/`espressif/idf:v5.3.1` available this session):
  - `sh firmware/tests/run_host_tests.sh` — 8/8 suites pass.
  - `sh firmware/tests/check_production_config.sh static` — `PASS`.
  - `sh firmware/tests/check_log_contract.sh` — `PASS`.
  - `python3 stub-server/test_devices_registry.py` — 14/14 checks pass.
  - `./firmware/build.sh` (production, from scratch) — succeeds; `Firmware version: cb776fd`; `sh firmware/tests/check_production_config.sh built firmware/build-ee02` — `production-config built: PASS`.
  - `SKYPANE_PROFILE=dev SKYPANE_FAULT=panic ./firmware/build.sh` — succeeds; `grep -a -c SKYPANE-FAULT-INJECT firmware/build-ee02-dev/skypane.bin` returns `1`; the same grep against the production binary (`firmware/build-ee02/skypane.bin`) returns `0`.
  - Build directories removed after verification (gitignored, `firmware/.gitignore`'s `build-*/` pattern); `git status` clean before each commit.

## Task Commits

1. **Task 1: VENDOR.md update and a CI guard for the Log Line Contract** - `cb776fd` (feat)
2. **Task 2: Hardware-session results template with pre-registered expectations, and the end-to-end build gate** - `37982d2` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `firmware/VENDOR.md` - Log Line Contract's 13-token `poll fail step=` row + per-token definitions, new Diagnostic lines table, new Operational notes section, vendored-files table and Original-To-This-Repository list updated for every phase-34 file
- `firmware/tests/check_log_contract.sh` - new: byte-identical contract format strings + step-token documentation CI guard
- `.github/workflows/firmware.yml` - `Check Log Line Contract` step added before the build
- `hardware/PHASE34-HARDWARE-SESSION.md` - new: 21-scenario results template with pre-registered expectations for plan 34-11

## Decisions Made

- The plan's own `<verify>` grep for the new step tokens requires the literal unescaped substring `auth|enrol|secret|config|reset|deadline` (plain BRE grep, bare `|` is a literal character). VENDOR.md's table row keeps the project's existing backslash-escaped-pipe convention for correct markdown rendering; the unescaped literal instead lives in the prose sentence introducing the full 13-token list, satisfying the check without breaking the table.
- `check_log_contract.sh` extracts its expected token set from the code itself (three greps whose union is the 13 real tokens) rather than hardcoding a list, so a future token added to `state_machine.c`/`app_main.c` and left undocumented in VENDOR.md fails CI without any edit to this script.
- The Wake Duration table uses medians (not means), matching `34-11-PLAN.md`'s own extractor commands, so a single outlier wake cannot skew the number the ~28 s overhead conclusion depends on.
- H-01/H-03/H-17's "Capture file" column reads "n/a — recorded directly in this document/table" rather than inventing a serial-log filename `34-11-PLAN.md`'s script never names for those three scenarios (a build/flash console transcript, a `devices_cli.py list` output, and battery readings that already have a dedicated table).

## Deviations from Plan

**1. [Rule 1 - Bug] Removed a literal `SKYPANE_SETUP_SECRET` occurrence introduced while drafting VENDOR.md's api_client.c row**
- **Found during:** Task 1's own self-verification (running the plan's exact `<verify>` command)
- **Issue:** The first draft of api_client.c's phase-34 paragraph described `fp_api_setup()`'s change as "instead of a shared compiled-in `SKYPANE_SETUP_SECRET`", which reintroduced the literal macro name the plan's acceptance criteria (and D-34-02 itself) requires VENDOR.md to contain zero occurrences of, since the macro was removed from the codebase in plan `34-06`.
- **Fix:** Reworded the sentence to describe the same fact without repeating the removed macro's literal name ("instead of the shared setup secret this file's macro used to hold").
- **Files modified:** `firmware/VENDOR.md`
- **Commit:** `cb776fd` (folded into Task 1's commit — caught before committing, not a follow-up fix)

No other deviations — both tasks executed as written.

## Issues Encountered

None. Docker (`espressif/idf:v5.3.1`) was available throughout, so every build-gated verification step in both tasks ran for real rather than falling back to a CI-run-URL record.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 34-11 (the phase's one hardware session, `autonomous: false`) has everything it needs: `hardware/PHASE34-HARDWARE-SESSION.md` with 21 pre-registered scenario expectations to fill in as the developer runs the script, and a fully green CI/local build gate (host tests, both production-config modes, the Log Line Contract check, the registry test harness, and a from-scratch container build) proving nothing in plans 34-01..34-10 regressed before hardware time is spent.
- `firmware/tests/check_log_contract.sh` is now a permanent CI gate — any future plan that adds a new `poll fail step=` token must add its one-line definition to `firmware/VENDOR.md`'s Log Line Contract section, or CI fails on the very next push touching `firmware/**`.
- No open blockers. `firmware/VENDOR.md`, `firmware/tests/check_log_contract.sh`, `.github/workflows/firmware.yml` and `hardware/PHASE34-HARDWARE-SESSION.md` are single-owner for this plan; plan 34-11 only fills in the template's PENDING fields and commits capture files under `hardware/logs/phase34/` — it does not edit this plan's four files' structure.

---
*Phase: 34-firmware-resilience-power-security-cleanup*
*Completed: 2026-09-23*

## Self-Check: PASSED

- FOUND: `firmware/VENDOR.md` (modified)
- FOUND: `firmware/tests/check_log_contract.sh`
- FOUND: `.github/workflows/firmware.yml` (modified)
- FOUND: `hardware/PHASE34-HARDWARE-SESSION.md`
- FOUND commit `cb776fd` (Task 1)
- FOUND commit `37982d2` (Task 2)
