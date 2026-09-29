---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
fixed_at: 2026-09-29
review_path: .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-REVIEW.md
iteration: 1
fix_scope: critical_warning
findings_in_scope: 34
fixed: 34
skipped: 0
status: all_fixed
---

# Phase 42: Code Review Fix Report

All 5 critical and 29 warning findings in `42-REVIEW.md` are fixed. Each fix is its own `fix(42): <ID> …` commit. The info findings were left for later.

The fixes were made slice by slice (firmware, then server, then companion) on the phase branch, never two agents at once. After each slice the orchestrator re-verified the work independently.

## Orchestrator corrections

- **SRV-WR-01.** The fixer's first fix (48f9691d) skipped any result identical to the previous one. That also swallowed genuine retries that fail the same way every time: an unsigned or tampered image is refused with the same token on every attempt. MAX_ATTEMPTS was then never reached, and the bad image was re-offered and re-downloaded on every wake.
  - It was reverted in 99f0c5d3, so every reported result counts again.
  - A resend caused by a lost response can't be told apart from a real retry on the server side, because both arrive between two offers. Over-counting is the accepted, safe side: a release fails one attempt early and can be rescheduled.
  - The attempt-limit test now sends identical reports on purpose.
  - The real fix would have the device send an attempt counter in `X-Ota-Result`. That is a protocol change and is left as a follow-up.
- **88de3b13.** Removed a duplicated comment block in `compute_offer`. De-flaked `test_apply_reconcile_writes_only_when_changed`, which compared `st_mtime_ns` and now compares inodes.
- **Independent checks.**
  - FW-CR-01 and SRV-CR-01 were read against the code.
  - The server slice was run from a real clone in a Linux `python:3.14` container: 319 passed.
  - The regenerated UPDATING mask was checked in a `python:3.14` container with libraqm: the mask drift tests pass.
  - The 375px companion screenshots were looked at.

## Still needs the hardware session

- **FW-CR-01.** A real stop → connect → HTTPS cycle within one wake. It is the first bench check before `fw-v1.0.0` is tagged.
- **FW-WR-09.** Measure `uxTaskGetStackHighWaterMark` during an OTA wake.

# Slice report: firmware


# Phase 42: Firmware Slice Code Review Fix Report

**Fixed at:** 2026-09-29
**Source review:** 42-REVIEW.md, "Slice: Firmware" section only
**Iteration:** 1
**Scope:** FW-CR-01 and FW-WR-01 .. FW-WR-09 (critical + warning, firmware slice only). SRV-* and CMP-* findings are explicitly out of scope for this pass.

**Summary:**
- Findings in scope: 10 (1 critical, 9 warning)
- Fixed: 10
- Skipped: 0

All fixes are committed individually on `claude/roadmap-phase-42-8ca05e`. No signing key was generated, used, or touched; no device, eFuse tool, or physical hardware was contacted at any point.

## Fixed Issues

### FW-CR-01: The second `fp_wifi_connect()` on the OTA path aborts the device

**Files modified:** `firmware/main/wifi.c`
**Commit:** `4f39798c`
**Applied fix:** `fp_wifi_stop()` now destroys `s_sta_netif` via `esp_netif_destroy_default_wifi()` and resets the pointer to `NULL`, mirroring exactly what a fresh boot does (no netif exists until `fp_wifi_platform_init()` creates one). `fp_wifi_platform_init()` also guards the create call with `if (!s_sta_netif)` for defense in depth against any future double-init path that doesn't go through `fp_wifi_stop()` first. This makes the OTA path's stop -> connect -> HTTPS cycle within one wake safe instead of hitting ESP-IDF's `assert(netif)` abort.
**Verification:** Tier 1 (re-read) + a real container build (`firmware/build.sh`, `espressif/idf:v5.3.1`) compiled cleanly, confirming `esp_netif_destroy_default_wifi()` resolves via the existing includes. `wifi.c` has no host-compilable path (ESP-IDF-only headers: `esp_wifi.h`, `esp_netif.h`, FreeRTOS), so no host test was added for this fix — the review itself calls out that "the host tests cannot catch this" and requires a hardware bench cycle (a full stop -> connect -> HTTPS cycle) before tagging `fw-v1.0.0`, which remains mandatory and unperformed here (no hardware was touched, per instructions).

### FW-WR-01: In-wake OTA failure leaves `FP_NVS_OTA_TRY` set, overwritten as `fail-interrupted`

**Files modified:** `firmware/main/state_machine.c`, `firmware/main/ota.h`
**Commit:** `4a9350aa`
**Applied fix:** Added `fp_nvs_erase_key(FP_NVS_OTA_TRY)` right after `fp_ota_record_result(...)` on both in-wake OTA failure exits (the reconnect failure and the `fp_ota_apply()` failure) in the `FP_OTA_START` branch, since the attempt is now fully classified. The early `fp_ota_mark_try()` call is untouched, so a power loss or deadline expiry still reports `fail-interrupted` correctly. Also corrected `ota.h`'s `fp_ota_mark_try()` doc comment, which incorrectly claimed the call happens after a successful `fp_ota_apply()` rather than before it.
**Verification:** Tier 1 (re-read) + `firmware/tests/check_log_contract.sh` PASS + real container build. Not host-testable as glue code (state_machine.c/ota.c pull in ESP-IDF's `nvs`, `esp_system`, `esp_heap_caps` headers with no host-compilable path); the pure-logic side of "an empty try marker classifies as NONE" is already covered by `test_ota_policy.c`'s existing `fp_ota_boot_classify("", ...)` / `fp_ota_boot_classify(NULL, ...)` assertions.

### FW-WR-02: An offer arriving during a pending trial rolls back a healthy trial

**Files modified:** `firmware/main/ota_policy.h`, `firmware/main/ota_policy.c`, `firmware/tests/test_ota_policy.c`, `firmware/main/state_machine.c`
**Commit:** `78ebc2ff`
**Applied fix:** `fp_ota_decide()` gained a `trial_pending` parameter and a new `FP_OTA_REFUSE_TRIAL_PENDING` decision, checked immediately after the same-version check and before battery/floor. `state_machine.c` passes `fp_ota_trial_pending()` into the call and handles the new case by logging and doing nothing — critically, it never touches `FP_NVS_OTA_RESULT`, since `fp_ota_boot_check()` may have already recorded `"trial;<version>"` earlier the same wake.
**Verification:** Host-tested. `test_ota_policy.c`'s `decide_cases()` gained 4 new assertions (same-version-during-trial stays SKIP; different-version-during-trial with favourable and unfavourable battery/floor both resolve to `REFUSE_TRIAL_PENDING`). Proved the test fails without the fix: reverted just the `if (trial_pending) return FP_OTA_REFUSE_TRIAL_PENDING;` lines and re-ran the suite standalone — assertion failure confirmed, then restored and re-verified the full 13-suite run passes.

### FW-WR-03: "Confirmed but not yet reported" is classified NONE and the install is lost

**Files modified:** `firmware/main/ota_policy.h`, `firmware/main/ota_policy.c`, `firmware/main/ota.c`, `firmware/tests/test_ota_policy.c`
**Commit:** `d04ce558`
**Applied fix:** Added `FP_OTA_BOOT_INSTALLED` to `fp_ota_boot_outcome_t`. `fp_ota_boot_classify()` now returns it (instead of `FP_OTA_BOOT_NONE`) when `ota_try == running` and the running image is no longer pending verification. `fp_ota_boot_check()` handles the new outcome by recording `FP_OTA_RESULT_INSTALLED` and erasing the try marker, catching up on a confirm whose own result was previously lost (crash between confirm and recording, or rollback support absent).
**Verification:** Host-tested. Updated the existing `boot_classify_cases()` assertion for this exact state to expect `FP_OTA_BOOT_INSTALLED`. Proved the test fails without the fix: reverted the one-line `fp_ota_boot_classify()` change and re-ran standalone — `Assertion failed` confirmed at the updated line, then restored and re-verified the full suite.

### FW-WR-04: `esp_restart()` resets the RTC panel-guard state

**Files modified:** `firmware/main/state_machine.c`
**Commit:** `9536d04f`
**Applied fix:** Before calling `esp_restart()` on a successful OTA apply, the code now waits out any panel-guard spacing still owed (`fp_panel_wait_seconds()` + `fp_wake_light_sleep_s()`) — safe at that point since the radio is already down (`draw_updating_screen()` already called `fp_wifi_stop()`) and the panel is already powered off after its own blit, the same precondition `fp_panel_draw()`'s own `AFTER_WAIT` branch relies on. This makes the spacing hold in real elapsed time, independent of the RTC_DATA_ATTR counter surviving the soft reset (it doesn't — ESP-IDF re-runs `.rtc.data` init on `esp_restart()`, unlike deep sleep).
**Verification:** Tier 1 (re-read) + real container build. Not host-testable at the call site (state_machine.c is ESP-IDF-only), but the underlying arithmetic it calls (`fp_panel_guard_after_awake`, `fp_panel_guard_plan`) is already host-tested via `firmware/tests/test_panel_guard.c` (unchanged, still passing).

### FW-WR-05: Provisioning/credential errors misreported as step=wifi

**Files modified:** `firmware/main/state_machine.c`
**Commit:** `6443807e`
**Applied fix:** The primary `fp_wifi_connect()` call site now maps `FP_ERR_CONFIG` to step token `"config"` and everything else to `"wifi"`, matching `wifi.h`'s documented behaviour and the Log Line Contract's intended meaning.
**Verification:** `firmware/tests/check_log_contract.sh` PASS (still recognises `"config"` as a valid token from other call sites) + real container build.

### FW-WR-06: Nothing ensures the USB-flashed image is signed

**Files modified:** `firmware/flash.sh`, `firmware/SIGNING.md`
**Commit:** `d36e608d`
**Applied fix:** `flash.sh`'s `prod` profile (the default) now runs `espsecure.py verify_signature --version 2 --keyfile firmware/signing/skypane-signing-pubkey.pem <build-dir>/skypane.bin` before writing anything to the device, and refuses to flash if the check fails or `espsecure.py`/the public key is missing. The `dev` profile is exempt (bench-only images never expected to self-update). SIGNING.md documents the new gate and the local-signing procedure it enforces. No signing key was generated or used — only the already-committed public key.
**Verification:** Ran the real `espsecure.py` (installed via the `esptool` PyPI package on this machine) against the real unsigned `firmware/build-ee02/skypane.bin` produced by `firmware/build.sh` in this session: `verify_signature` exits non-zero ("Signature could not be verified with the provided key"), confirming the gate rejects exactly the artifact that would otherwise strand a device. `sh -n flash.sh` and `shellcheck -S warning flash.sh` both clean (one pre-existing SC1007 warning on an unrelated, unmodified line).

### FW-WR-07: `provision.sh` accepts values the device mangles or rejects

**Files modified:** `firmware/provision.sh`
**Commit:** `dbb9a72a`
**Applied fix:** `reject_comma_or_newline()` (shared by `--wifi-ssid`, the Wi-Fi password, and `--api-base`) now also rejects a leading `"`, since `nvs_partition_gen`'s CSV reader silently mangles such values. `validate_api_base()` now rejects a value over 127 bytes, matching `FP_API_BASE_MAX` (128 including the NUL).
**Verification:** `sh -n provision.sh` clean. Manually confirmed the CSV-mangling failure mode with Python's `csv` module locally (`"abc"defgh` -> `abcdefgh` under default `DictReader` quoting), matching the review's own repro. No dedicated host test harness exists for `provision.sh` (not covered by `run_host_tests.sh`, which only exercises `test_*.c` against `main/*.c`).

### FW-WR-08: eFuse guard misses `sdkconfig.dev.defaults`; built-mode checks were log-only

**Files modified:** `firmware/tests/check_production_config.sh`
**Commit:** `2bf3b3a7`
**Applied fix:** Split the static-mode scan into two loops: the existing `defaults`+`ee02` loop (ALLOW_HTTP/FAULT_INJECT checks, which `sdkconfig.dev.defaults` deliberately violates by design) stays as-is, and a new loop covering `defaults`+`ee02`+`dev` checks the eFuse-burning options on all three files. Built-mode's required-lines list now includes `# CONFIG_NVS_ENCRYPTION is not set`, `# CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK is not set`, and `# CONFIG_EFUSE_VIRTUAL is not set` as hard assertions (previously only logged).
**Verification:** `sh tests/check_production_config.sh static` PASS. `sh tests/check_production_config.sh built firmware/build-ee02` PASS against a real, from-scratch container build performed at the end of this session (all three new required lines present in the resolved sdkconfig).

### FW-WR-09: 4 KiB stack buffer live through the TLS/signature path

**Files modified:** `firmware/main/ota.c`
**Commit:** `bd8d50b5`
**Applied fix:** Made the `chunk[HASH_CHUNK_BYTES]` read-back buffer in `fp_ota_apply()` `static` instead of a local, removing it from the function's stack frame (which Xtensa reserves in full on entry, so it was live through `esp_https_ota_begin()/perform()/finish()` regardless of its lexical position). Safe because `fp_ota_apply()` is single-threaded and runs at most once per wake.
**Verification:** Tier 1 (re-read) + real container build compiled cleanly. Not host-testable (`ota.c` needs ESP-IDF's `mbedtls`/`esp_https_ota`/`esp_ota_ops` headers). Actual stack high-water-mark measurement remains hardware-session work per the review, unaffected by this fix.

## Skipped Issues

None — all 10 in-scope findings were fixed.

## Verification performed (final, on the fully committed state)

- `sh firmware/tests/run_host_tests.sh` — 13 suites, all pass.
- `sh firmware/tests/check_log_contract.sh` — PASS.
- `sh firmware/tests/check_production_config.sh static` — PASS.
- `./firmware/build.sh` (real `espressif/idf:v5.3.1` container, from a clean `build-ee02/`) — succeeds.
- `sh firmware/tests/check_production_config.sh built firmware/build-ee02` — PASS, including the new FW-WR-08 assertions.
- `server/.venv/bin/python3 scripts/check_comment_history.py check` — exit 0.
- Full project `fullcheck.sh` (ruff, comment-history, mypy, function-size, shellcheck, full pytest suite): all lint lines `ok`; `NEW FAILURES:` empty (pre-existing environment-only pytest failures unaffected, since no server/companion code was touched).
- `git status --short` — clean.
- No signing key generated or used. No device, eFuse tool, or physical hardware contacted.

## Notes for the mandatory hardware bench session (unperformed here, by instruction)

- FW-CR-01: run a full stop -> connect -> HTTPS cycle on the bench before tagging `fw-v1.0.0` (explicitly called out as mandatory in the review; host tests cannot catch this class of bug).
- FW-WR-09: measure `uxTaskGetStackHighWaterMark(NULL)` after `esp_https_ota_finish()` to confirm the margin the static-buffer fix restores.
- FW-WR-06: sign a real bench/release image per `SIGNING.md` and confirm `flash.sh` accepts it (the gate's negative path — rejecting an unsigned image — was proven in this session against the real unsigned build artifact; the positive path needs a signed image, which requires the private key and is out of scope here).

# Slice report: server


# Phase 42: Code Review Fix Report -- server slice (continuation)

**Fixed at:** 2026-09-29
**Source review:** 42-REVIEW.md, "Slice: Server, byos, release pipeline and deploy"
**Iteration:** 1 (this run continues a prior fixer that stopped on an API rate
limit after committing SRV-CR-01..04, SRV-WR-05, SRV-WR-06, SRV-WR-07 and
SRV-WR-09; those 8 commits were verified intact before this run started --
`git status --short` was clean, `git diff HEAD` was empty, and each fixed
file matched its commit's own diff, so nothing was left mid-revert)

**Summary (all 14 SRV findings):**
- Findings in scope: 14 (4 critical, 10 warning)
- Fixed: 14
- Skipped: 0

## Fixed Issues

### SRV-CR-01: A same-SHA deploy drops the newly published firmware
**Files modified:** `deploy/activate.sh`, `deploy/tests/conftest.py`
**Commit:** `2bce20b4` (prior run)
**Applied fix:** Firmware is pulled into its own per-deploy directory before
the release tree is either moved into place or discarded, and imported from
there regardless of whether this SHA was already staged.

### SRV-CR-02: The cancel/replace-until-acknowledged rule races with byos
**Files modified:** `stub-server/byos_server.py`, `stub-server/test_ota_offer.py`
**Commit:** `92728efc` (prior run)
**Applied fix:** byos now takes `firmware_registry.registry_lock()` first,
then its own `_device_report_lock`, and loads the registry inside both, so
the offer decision is atomic with `cancel_schedule()`/`schedule_release()`.

### SRV-CR-03: Result events are stamped with the current schedule id, not the schedule the device ran
**Files modified:** `stub-server/byos_server.py`, `stub-server/test_ota_offer.py`
**Commit:** `b443ccb5` (prior run)
**Applied fix:** A result event is now tagged with the current schedule's id
only when the header's own version matches it; otherwise `schedule_id=None`,
which `reconcile()`'s existing stale-id branch already handles safely.

### SRV-CR-04: The Update page can lock with no recovery
**Files modified:** `server/firmware_registry.py`, `server/test_firmware_registry.py`,
`stub-server/byos_server.py`, `stub-server/test_ota_offer.py`
**Commit:** `4021556a` (prior run)
**Applied fix:** byos floors the next assigned seq against
`reconciled_seq` and every recorded event seq (never regresses); `compute_offer()`
also withholds the offer when the device's own reported version is below
the floor (a pre-OTA build that could never confirm/rollback/report).

### SRV-WR-05: `import-dir` did not cross-check the directory tag against `manifest["version"]`
**Files modified:** `server/firmware_cli.py`, `server/test_firmware_cli.py`
**Commit:** `5a771f0c` (prior run)

### SRV-WR-06: `import-bench` accepted plain release-tag versions and could not work on the VPS
**Files modified:** `server/firmware_cli.py`, `server/firmware_registry.py` (via prior context)
**Commit:** `f73ac814` (prior run)

### SRV-WR-07: `_resolve_device_id` iterated the shared token dict without a snapshot
**Files modified:** `stub-server/byos_server.py`, `stub-server/test_ota_offer.py`
**Commit:** `bfde8397` (prior run)

### SRV-WR-09: `publish_release` never re-verified an image already on disk
**Files modified:** `server/firmware_registry.py`, `server/test_firmware_registry.py`
**Commit:** `438f6476` (prior run)

### SRV-WR-01: A resent X-Ota-Result was counted as a new attempt
**Files modified:** `stub-server/byos_server.py`, `stub-server/test_ota_offer.py`
**Commit:** `48f9691d`
**Applied fix:** Skip recording a new "result" event when it is identical in
(token, version, schedule_id) to the most recent "result" event already on
record for that device -- the firmware only clears its pending result once
some later response's body has actually parsed
(`api_client.c`'s `fp_ota_result_clear()`), so an identical repeat is the
same telling arriving twice, not a second attempt. This deliberately
under-counts (never over-counts) a device that genuinely fails the same way
twice in separate real attempts, since over-counting is what closes a
schedule or fails it a poll early on a lost response.
Updated `test_third_counted_failure_withdraws_offer_in_the_same_response`
to use three distinct failure tokens (it previously encoded three identical
resends as three counted attempts -- the exact ambiguity this fix
resolves) and added `test_resent_identical_result_is_not_double_counted`.
A pre-existing miswritten comment in this same code (mentioning a finding
ID) was reworded in a small follow-up commit (`9406fb2a`).

### SRV-WR-02: The environment gate ran before the tag/ancestor guard
**Files modified:** `.github/workflows/firmware-release.yml`
**Commit:** `886b29bb`
**Applied fix:** Split the guard ("tag shape + is on main") into its own
job with no `environment:` and no secret access; the signing job now
`needs: guard`, so the reviewer-gated `firmware-signing` environment
approval is only ever requested for a tag that already passed the guard.
Validated with `actionlint` (clean) and `deploy/tests/test_ci_secrets.py`
(passes; it still finds `FW_SIGNING_KEY` reaching the signing step only via
`env:`).

### SRV-WR-03: The signing key was mounted into a mutable-tag image with network enabled
**Files modified:** `.github/workflows/firmware-release.yml`
**Commit:** `0122e40e`
**Applied fix:** Both the sign and verify `docker run` invocations are now
pinned to the digest resolved with
`docker inspect --format '{{index .RepoDigests 0}}' espressif/idf:v5.3.1`
(`espressif/idf@sha256:55ab243e87584859c9af3acc124b0b9423a9d8b44fc99a5d5055d7bd7312722d`,
re-confirmed with a fresh `docker pull` at fix time), both get
`--network none`, and both jobs' `actions/checkout` now set
`persist-credentials: false`. Validated with `actionlint` and
`deploy/tests/test_ci_secrets.py`.

### SRV-WR-04: One sha conflict or one bad GitHub Release blocked every future deploy
**Files modified:** `server/firmware_cli.py`, `server/test_firmware_cli.py`,
`.github/workflows/ci.yml`
**Commit:** `f756edb7`
**Applied fix:** `import-dir` now snapshots which versions are already
registered before the loop; a tag genuinely new to this deploy keeps the
strict rule (its own failure blocks activation), but a tag already
registered whose re-import now conflicts (or otherwise fails) only produces
a loud warning, never a blocked deploy. Added
`test_import_dir_stale_release_sha_conflict_alone_does_not_block_deploy`
and `test_import_dir_new_tag_failure_still_blocks_despite_unrelated_stale_release`.
Also hardened the CI "Download firmware releases" step: it now checks each
release's assets with `gh release view` first and skips (with a
`::warning::`) one missing either asset, instead of letting `gh release
download` abort the whole step under `set -e`.

### SRV-WR-08: A corrupt `registry.json` was wiped by the next write
**Files modified:** `server/firmware_registry.py`, `server/firmware_cli.py`,
`server/test_firmware_registry.py`
**Commit:** `cbf86f52`
**Applied fix:** Added `RegistryCorruptError` (an `OSError` subclass, so
it's already caught wherever `schedule_release()`/`cancel_schedule()`'s
existing `except (OSError, TimeoutError)` treats an incomplete write as "no
change made") and `_load_registry_for_write()`, now used by every locked
writer (`publish_release`, `schedule_release`, `cancel_schedule`,
`apply_reconcile`) instead of the tolerant `load_registry()`. A missing file
still resolves to the empty document; a file that exists and fails to
parse (or isn't a JSON object) is moved aside intact under a timestamped
`registry.json.corrupt-<epoch>` name and raises, rather than being silently
replaced. `firmware_cli`'s import commands now also catch
`RegistryCorruptError` alongside `ValueError` so this reports a clean
per-item error instead of an unhandled traceback. Added
`test_load_registry_for_write_missing_file_returns_defaults`,
`test_load_registry_for_write_refuses_non_json_and_moves_it_aside`,
`test_load_registry_for_write_refuses_wrong_top_level_shape`,
`test_publish_release_refuses_to_overwrite_a_corrupt_registry`,
`test_schedule_release_refuses_a_corrupt_registry`.

### SRV-WR-10: No test covered the new failure modes; one test only proved import-before-restart, not before-swap
**Files modified:** `deploy/tests/conftest.py`, `deploy/tests/test_activate.py`
**Commit:** `6d685da1`
**Applied fix:** The other four CR paths already gained their own
behavioural tests in the prior run's commits (`test_cancel_cannot_race_the_offer_decision`
for SRV-CR-02, `test_stale_resent_result_does_not_close_a_different_schedule`
for SRV-CR-03, `test_next_seq_stays_monotonic_against_a_reset_device_report`
plus the `reporting_device_below_floor` offer-eligibility case for
SRV-CR-04, and `test_same_sha_redeploy_imports_freshly_streamed_firmware`
for SRV-CR-01) -- confirmed present and passing rather than re-added. The
one still-named gap was closed here: the fake `firmware_cli` stand-in now
also records what `current` points to at invocation time, and
`test_firmware_import_runs_before_swap_when_present` was reworked around a
real prior release so the recorded value can be checked against the
*previous* release's target, proving the import precedes the `current`
symlink swap itself, not merely the later `systemctl restart` (moving the
import after `mv -T` now fails this test, where it previously would not
have).

## Skipped Issues

None -- every in-scope finding was fixed.

## Verification

- `server/.venv/bin/python3 scripts/check_comment_history.py check`: pass
- `server/.venv/bin/mypy`: pass (12 source files)
- `server/.venv/bin/ruff check .`: pass
- `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server`: pass (460 functions, none over 80)
- `actionlint .github/workflows/*.yml`: pass
- `deploy/tests/test_ci_secrets.py`: pass
- Real Linux container run (`python:3.14`, real `mv -T`, hash-locked
  `server/requirements-dev.txt`) of `deploy/tests`,
  `server/test_firmware_registry.py`, `server/test_firmware_cli.py`,
  `server/test_firmware_reconcile.py`, `stub-server/test_ota_offer.py`: all
  green except one pre-existing, unrelated flake --
  `server/test_firmware_registry.py::test_apply_reconcile_writes_only_when_changed`
  intermittently fails on a fast filesystem because two consecutive writes
  can land in the same mtime tick (`st_mtime_ns` collision); reproduced the
  same intermittent failure against the base commit (`438f6476`, before any
  commit from this run) in the same container, confirming it predates and
  is unrelated to every fix in this report.
- `fullcheck.sh`'s macOS full-suite run reported one "NEW FAILURES" entry:
  `deploy/tests/test_activate.py::test_same_sha_redeploy_imports_freshly_streamed_firmware`.
  This is the same pre-existing "macOS BSD `mv` has no `-T`" environment gap
  every other `deploy/tests/test_activate.py` test already carries in
  `known-env-fail.txt` -- this particular test just postdates that
  baseline list (it was added by the SRV-CR-01 commit from the prior run).
  Confirmed: fails locally with `mv: illegal option -- T` (not any
  assertion in the test body), and passes cleanly (`1 passed`) in the same
  Linux container used for the required validation above. Not a
  regression from anything in this report.
- `git status --short` clean; no uncommitted or reverted changes.

## Notes for the caller

- Only `SRV-*` findings were touched, per this run's scope. `FW-*` and
  `CMP-*` findings from the same 42-REVIEW.md are out of scope for this
  fixer and untouched.
- One small ancillary commit (`9406fb2a`) reworded a code comment left by
  the SRV-WR-01 commit that named a finding ID, to satisfy
  `check_comment_history.py`; it is not a fix for any numbered finding.
- SRV-CR-04's `compute_offer()` has a duplicated comment block (the same
  paragraph appears twice back to back, lines ~626-636 and ~639-649 of
  `server/firmware_registry.py`) left over from that earlier commit --
  cosmetic only, not touched here since it is outside this run's scope and
  not one of the 14 SRV findings, but worth a follow-up cleanup.

---

_Fixed: 2026-09-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

# Slice report: companion


# Phase 42: Code Review Fix Report (companion slice, CMP-WR-01 to CMP-WR-10)

**Branch:** claude/roadmap-phase-42-8ca05e (worked directly in the tree, no separate worktree)

## Fixed Issues

### CMP-WR-01: Update page leaked the English "no reading yet" fallback
**Commit:** 61094c7b (plus follow-up 26006cf8)
**Files:** companion/pages/update_page.py, companion/test_update_page.py, companion/testdata/render_baseline.json
**Applied fix:** the timestamp detail line is dropped when there is no timestamp, instead of rendering the hard-coded English fallback (in either language).
**Follow-up 26006cf8:** the change broke `companion/test_render_baseline.py::test_rendered_pages_match_the_baseline` (the committed baseline still contained the leaked line for /update, en/fr, dark/light). Baseline regenerated with `companion_render_snapshot.py --write`; only those four entries changed.

### CMP-WR-02: state row did not say which version is scheduled, in progress or failed
**Commit:** 96f782c3 (companion/pages/update_page.py, companion/test_update_page.py, server/firmware_registry.py, server/test_firmware_registry.py)

### CMP-WR-03: Install offered while an update is in progress
**Commit:** 3397e7a4 (companion/app.py, companion/flash.py, companion/i18n_fr/update.py, companion/pages/update_page.py, tests)

### CMP-WR-04: promised a next-wake time that has already passed
**Commit:** 73e10ea5 (companion/app.py, companion/i18n_fr/update.py, companion/pages/update_page.py, companion/test_update_page.py)

### CMP-WR-05: Version history table did not stack on narrow screens
**Commit:** 50efc44d (companion/pages/update_page.py, companion/static/style.css, companion/test_browser_update.py)

### CMP-WR-06: bench builds not marked on the Update page
**Commit:** dbd80527 (companion/app.py, companion/i18n_fr/update.py, companion/pages/update_page.py, tests)

### CMP-WR-07: UPDATING glyph did not read as a refresh mark
**Commit:** 22dde158 (server/plane/render/glyphs.py, server/plane/render/__init__.py, firmware/main/updating_screen_mask.h regenerated, server tests)

### CMP-WR-08: hostile install version echo not proven absent
**Commit:** a7472387 (companion/test_update_actions.py)

### CMP-WR-09: "newest first" history test could not fail
**Commit:** 17ae7382
**Files modified:** companion/test_update_page.py
**Applied fix:** the two fixture releases now have distinct `published_at` values, the older inserted first, and the test asserts the newer release's row comes before the older one (plus the Install form / Installed column checks, now scoped to the right row).
**Non-vacuity proof:** in `server/firmware_registry.py` line 893, `reverse=True` changed to `reverse=False`: test FAILED. Sort removed entirely (`list(...)`): test FAILED. Restored with `git checkout --`, test passes.

### CMP-WR-10: per-state timestamp assertion satisfied by the history table
**Commit:** 7a224e88
**Files modified:** companion/test_update_page.py
**Applied fix:** `data-relative` is now asserted inside the Status section slice (first `<section` to its `</section>`) for each of the five states.
**Non-vacuity proof:** with the state row's timestamp removed in `_status_state_row_html`, the test FAILED on the "available" case (the old whole-page assertion would still have passed). Restored with `git checkout --`.
**Note on the suggested empty-registry case:** already covered by `test_empty_registry_never_leaks_the_hard_coded_no_reading_yet_fallback` (added with CMP-WR-01, asserts absence in EN and FR), so no duplicate was added.

## Skipped Issues

None.

## Verification

`fullcheck.sh`: ruff ok, comment-history ok, mypy ok, function-size ok, shellcheck ok; full suite parallel run with serial rerun of failures leaves "NEW FAILURES:" empty (only known environment-only failures remain). `git status --short` clean.

## Screenshots (375x812, full page, real running companion, three releases, fw-v1.1.0 scheduled)

Note: the fixed bottom tab bar appears mid-page in full-page captures; that is a capture artifact.

- /private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-unidentified-airlines-flights-a4ce95/4840a370-ce78-4678-8f31-9c57b90f640e/scratchpad/update-scheduled-en-375.png
- /private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-unidentified-airlines-flights-a4ce95/4840a370-ce78-4678-8f31-9c57b90f640e/scratchpad/update-scheduled-fr-375.png

(Earlier update-en-375.png / update-fr-375.png in the same directory are from before and show no scheduled release.)

_Fixer: Claude (gsd-code-fixer)_
