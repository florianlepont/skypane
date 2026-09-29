---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
reviewed: 2026-09-28
depth: standard
diff_base: origin/main
status: issues_found
files_reviewed: 91
findings:
  critical: 5
  warning: 29
  info: 27
  total: 61
slices: [firmware, server-deploy, companion]
---

# Phase 42: Code Review Report

Three reviewers each took one slice of `git diff origin/main` (93 source files; generated mask headers, render baselines and the public key were left out). None of them edited code.

Finding IDs carry the slice's prefix so they don't collide: `FW-` (firmware), `SRV-` (server, byos, release pipeline, deploy) and `CMP-` (companion). The orchestrator re-checked FW-CR-01 and SRV-CR-01 against the code, and both are real.

| Slice | Critical | Warning | Info |
|-------|----------|---------|------|
| Firmware | 1 | 9 | 7 |
| Server / byos / release / deploy | 4 | 10 | 8 |
| Companion (+ UPDATING composition) | 0 | 10 | 12 |


# Slice: Firmware


# Phase 42: Code Review Report (firmware slice)

**Reviewed:** 2026-09-28
**Depth:** standard. I also checked cross-file behavior against the ESP-IDF v5.3.1 sources inside the pinned `espressif/idf:v5.3.1` container.
**Status:** issues_found

## Summary

Most of the design holds up:
- A trial image is confirmed only on the healthy exit of `app_main()`. Every failure exit (`fail_and_sleep`, deadline, reset, `nvs`, `json`) skips the confirm, and any reset before the confirm makes the bootloader roll back.
- `esp_https_ota_finish()` is the only place the boot partition switches. Every earlier check can only abort.
- The checks run in the right order: descriptor/floor, then size, then read-back SHA-256, then signature (in `finish`).
- Offer parsing is bounded and NUL-safe. No credential is logged.

One defect blocks the release: the OTA path can never succeed on hardware. The wake stops Wi-Fi to draw the "Updating..." screen, then reconnects. That reconnect creates a second default Wi-Fi netif, which ESP-IDF rejects with `assert()`, so the device aborts on every OTA attempt. `fw-v1.0.0` is both the floor version and the first USB-flashed release. If it ships with this bug, every frame is stuck on it and only a USB flash can fix that.

The warnings cover:
- OTA outcome bookkeeping that loses or misreports results.
- A healthy trial being rolled back when an offer lands on the trial wake.
- The panel refresh-spacing guard being wiped by `esp_restart()`.
- Nothing ensuring the USB-flashed image is signed.
- Provisioning values the device mangles or rejects.
- Gaps in the eFuse guard.

---

## Critical Issues

### FW-CR-01: The second `fp_wifi_connect()` on the OTA path aborts the device, so no OTA can ever complete

**File:** `firmware/main/state_machine.c:79,190` → `firmware/main/wifi.c:106,226-242`
**Severity:** BLOCKER

**Issue:** When the decision is `FP_OTA_START`, `draw_updating_screen()` calls `fp_wifi_stop()` (state_machine.c:79). That function runs `esp_wifi_deinit()` and sets `s_platform_ready = false`, but it never destroys `s_sta_netif`. The OTA branch then calls `fp_wifi_connect(15000)` again (state_machine.c:190). That call goes through `fp_wifi_platform_init()`, which calls `esp_netif_create_default_wifi_sta()` a second time (wifi.c:106).

In ESP-IDF v5.3.1 (checked in the pinned container):
- `esp_netif_new_api()` rejects a duplicate `if_key` ("WIFI_STA_DEF") and returns NULL (`esp_netif_lwip.c:692-697`).
- `esp_netif_create_default_wifi_sta()` then runs `assert(netif)` (`wifi_default.c:388`).

Assertions are on in the built config (`CONFIG_COMPILER_OPTIMIZATION_ASSERTIONS_ENABLE=y` in `build-ee02/sdkconfig`). So `abort()` fires and the chip resets with PANIC.

**Failure scenario:**
1. The server schedules an update.
2. The frame draws "Updating..." (a 30-70 s blit), then aborts.
3. On the next boot, `ota_try` is set but the old image is running, so `fp_ota_boot_check` reports `fail-interrupted`.
4. The reset reason is PANIC, so the frame backs off.
5. The next healthy poll carries the same offer and the loop repeats (a full-panel blit plus a crash each time) until the server reaches `MAX_ATTEMPTS`.

The download code is never reached, so OTA cannot work at all. The host tests cannot catch this.

Because `CONFIG_SKYPANE_OTA_FLOOR_VERSION` is `fw-v1.0.0`, which is also the first release flashed over USB, shipping this means every frame needs a USB reflash before it can ever update remotely.

**Fix:** Create the netif only once. Or keep the radio up for the OTA download and only stop it when the panel runs.
```c
/* wifi.c fp_wifi_platform_init() */
if (!s_sta_netif) {
    s_sta_netif = esp_netif_create_default_wifi_sta();
    if (!s_sta_netif) {
        return ESP_FAIL;
    }
}
```
You could instead call `esp_netif_destroy_default_wifi(s_sta_netif); s_sta_netif = NULL;` in `fp_wifi_stop()`. Then run a full stop → connect → HTTPS cycle on the bench before tagging `fw-v1.0.0`.

The same bug points to a design risk. The confirm rule is "one successful poll", so a release that breaks only the OTA path still gets confirmed. That strands the frame on it. The OTA path should be tested on hardware for every release. For the floor release there is no fallback, so this test is mandatory.

---

## Warnings

### FW-WR-01: A failed OTA in the same wake leaves `FP_NVS_OTA_TRY` set, so the next boot overwrites the real failure with `fail-interrupted`

**File:** `firmware/main/state_machine.c:186,192-194,204-206`; `firmware/main/ota.c:250-254`
**Severity:** WARNING

**Issue:**
1. `fp_ota_mark_try()` runs before the download (state_machine.c:186).
2. On an in-wake failure, the specific result (`fail-hash`, `fail-size`, `fail-image`, `fail-floor`, `fail-download`) is recorded, but `FP_NVS_OTA_TRY` is never erased. This happens after the display 200 that could have reported it.
3. On the next boot, `fp_ota_boot_check()` sees `ota_try` ≠ running with no matching invalid partition. It classifies the boot as INTERRUPTED and `fp_ota_record_result(FAIL_INTERRUPTED)` overwrites the pending specific token (ota.c:252).

So every in-wake failure reaches the server as `fail-interrupted`. The companion's `last_result` and failure notification never show the real reason.

This also contradicts `ota.h:86-90`, which says `fp_ota_mark_try` is called "once `fp_ota_apply()` returns ESP_OK".

**Fix:** After the in-wake failure is recorded, erase the try marker, because the attempt is now fully classified. Keep the early `mark_try` so that a power loss or deadline expiry is still reported as interrupted.
```c
fp_ota_record_result(ota_fail, disp.fw.version);
fp_nvs_erase_key(FP_NVS_OTA_TRY);   /* attempt fully classified */
*fail_step_out = "ota";
return FP_POLL_FAILED;
```
Do the same on the `ota_wifi_err` branch at line 192. Also correct the `ota.h` doc comment.

### FW-WR-02: An offer arriving on the trial wake rolls back a healthy trial and misreports it

**File:** `firmware/main/state_machine.c:170-207`; `firmware/main/app_main.c:395`
**Severity:** WARNING

**Issue:** The confirm happens at the very end of `app_main()`, but OTA offers are handled inside `fp_poll_once()`. On a trial wake (image still PENDING_VERIFY), a display response can carry an offer for a *different* version. This happens if the operator replaced the schedule while the frame was downloading, or schedules a newer release before the trial wake runs. `compute_offer` only suppresses offers for the version the device is running.

Then:
- `fp_ota_mark_try(new)` overwrites the trial's `ota_try`.
- The "Updating..." screen is drawn.
- `esp_https_ota_perform` → `esp_ota_begin` refuses with `ESP_ERR_OTA_ROLLBACK_INVALID_STATE` because the running app is PENDING_VERIFY (`esp_ota_ops.c:137-143`).
- The poll returns FAILED, so the trial is never confirmed and the bootloader rolls back a healthy image on the next wake.
- Because `ota_try` is now the new version, the rollback is reported as `fail-interrupted;<new>` instead of `rollback;<trial>`.

**Fix:** Skip starting an OTA while a trial is pending. This fits `fp_ota_decide()` as a new input, which keeps it host-tested.
```c
if (disp.fw.present && !fp_ota_trial_pending()) { ... }
```
Alternatively, confirm the trial right after the display 200 and before the OTA branch. That still satisfies "after a successful poll, before this wake's deep sleep".

### FW-WR-03: The "confirmed but not yet reported" state is classified NONE, so `installed` is lost and the server schedule never resolves

**File:** `firmware/main/ota_policy.c:138-139`; `firmware/main/ota.c:255-260,274-281`
**Severity:** WARNING

**Issue:** `fp_ota_boot_classify(ota_try == running, pending == false)` returns NONE, and `fp_ota_boot_check` then erases `ota_try`. The device can reach that state with no `installed` result stored:
- Power is lost between `esp_ota_mark_app_valid_cancel_rollback()` and `fp_ota_record_result(INSTALLED)` / `fp_nvs_erase_key` (ota.c:274-281).
- The NVS write of the result fails.
- The device was flashed with a bootloader that does not have rollback enabled, so the image never enters PENDING_VERIFY.

In all three cases the server never gets `installed`. `compute_offer` returns None because `fw_version` equals the schedule version, and `reconcile` only resolves on a `result` event. The companion shows the update as scheduled forever, and no success notification is sent.

**Fix:** Treat "the recorded try is the image now running and it is no longer pending" as an install.
```c
if (strcmp(ota_try, running) == 0) {
    return running_pending_verify ? FP_OTA_BOOT_TRIAL : FP_OTA_BOOT_INSTALLED;
}
```
In `fp_ota_boot_check`, record `FP_OTA_RESULT_INSTALLED` for that case and erase the try. Add a host test for it.

### FW-WR-04: `esp_restart()` resets the RTC panel-guard state, so the trial wake can blit inside the minimum refresh spacing

**File:** `firmware/main/state_machine.c:187,202`; `firmware/main/panel.c:24-25,45-53`
**Severity:** WARNING

**Issue:** After a non-deep-sleep reset (including `esp_restart()`), the bootloader reloads the `RTC_DATA_ATTR` segments. So `s_guard_remaining_s` comes back as 0 on the trial boot, even though the "Updating..." blit just set it to `CONFIG_FP_MIN_REFRESH_SPACING_S`.

The trial wake always redraws, because `FP_UPDATING_SCREEN_HASH` never matches a server hash. The sequence is:
1. The "Updating..." blit.
2. A fast LAN/VPS download (seconds).
3. `finish`, then restart.
4. The trial wake's full 960 KB download and blit.

That can easily land inside the 60 s spacing the panel guard exists to enforce (Spectra 6 panel protection).

**Fix:** Before `esp_restart()`, carry the guard state across the reset. One option is to store `s_guard_remaining_s` plus a timestamp in `RTC_NOINIT_ATTR` with a magic value. Another is to have `fp_panel_on_boot()` apply the full spacing on an `ESP_RST_SW` boot. The simplest option is to light-sleep for the remaining spacing (`fp_panel_wait_seconds()`) before `esp_restart()`.

### FW-WR-05: A provisioning or credential error is reported as step `wifi`, which contradicts `wifi.h` and draws NO CONNECTION for a config defect

**File:** `firmware/main/state_machine.c:110-117` (and 190-195); `firmware/main/wifi.c:157-165`; `firmware/main/wifi.h:22-27`
**Severity:** WARNING

**Issue:** `fp_wifi_connect()` now returns `FP_ERR_CONFIG` when the secret-partition credentials are missing or invalid. The comment at wifi.c:157-160 says this is "the same FP_ERR_CONFIG the caller already maps to the 'config' step". But `fp_poll_once` sets `*fail_step_out = "wifi"` for *any* `fp_wifi_connect` error.

An unprovisioned or badly provisioned frame therefore logs `poll fail step=wifi` forever. This breaks the Log Line Contract meaning, and the operator's diagnosis will point at radio or AP issues instead of `provision.sh`.

**Fix:**
```c
if (wifi_err != ESP_OK) {
    *fail_step_out = wifi_err == FP_ERR_CONFIG ? "config" : "wifi";
    return FP_POLL_FAILED;
}
```

### FW-WR-06: Nothing ensures the USB-flashed image is signed, and an unsigned running image strands the frame (every OTA fails `fail-image`)

**File:** `firmware/sdkconfig.defaults:36-39`; `firmware/flash.sh:92-111`; `firmware/SIGNING.md:69-74,171-184`
**Severity:** WARNING

**Issue:** With `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT` and the RSA scheme, the trusted key digests come *only* from the running app's own signature block (`secure_boot_signatures_app.c:126-149`). `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES` is off, so `build.sh` always produces an unsigned `build-ee02/skypane.bin`, and `flash.sh` flashes exactly that file with no check.

A frame flashed that way boots normally but rejects every OTA at `esp_https_ota_finish` (ESP_ERR_OTA_VALIDATE_FAILED, reported as `fail-image`). The only recovery is USB. SIGNING.md documents manual signing, but nothing in the tooling enforces it.

**Fix:** Make `flash.sh` refuse to flash an image without a valid signature block, or at least warn loudly. Use `espsecure.py verify_signature --version 2 --keyfile firmware/signing/skypane-signing-pubkey.pem <bin>` in the pinned container, or add a `--signed <bin>` argument that is required for the production profile. Optionally, log at boot whether the running app carries a signature block (`esp_secure_boot_get_signature_blocks_for_running_app`), so a stranded device is easy to spot.

### FW-WR-07: `provision.sh` accepts values the device mangles or rejects (CSV quoting, `api_base` length)

**File:** `firmware/provision.sh:195-263,412-425`
**Severity:** WARNING

**Issue:**
1. `nvs_partition_gen` reads the CSV with `csv.DictReader` using default quoting. A password or SSID that starts with `"` is silently rewritten. I checked: `"abc"defgh` becomes `abcdefgh`. The validators reject commas and newlines but not a leading double quote, which is printable ASCII and legal in WPA passphrases. The device then stores the wrong password and fails `wifi` every wake, or fails `config` if the length drops below 8.
2. `--api-base` has no length check. The device reads it into `api_base[128]` (`creds.h:22`, `FP_API_BASE_MAX` 128). `nvs_get_str` returns `ESP_ERR_NVS_INVALID_LENGTH` for a value of 128 bytes or more, so the frame fails closed with `config`, even though the script says it "mirrors creds.c's rules exactly".

**Fix:** Quote every CSV value properly. For example, generate the CSV with Python's `csv.writer` (`quoting=csv.QUOTE_ALL`) instead of `printf`. Or reject a leading `"` in `reject_comma_or_newline`. Also add `[ "${#base}" -le 127 ]` in `validate_api_base`.

### FW-WR-08: The eFuse-burning guard does not cover `sdkconfig.dev.defaults`, and the built check does not assert NVS encryption or anti-rollback are off

**File:** `firmware/tests/check_production_config.sh:48-63,144-164`
**Severity:** WARNING

**Issue:**
- The forbidden-option scan loops over `sdkconfig.defaults` and `sdkconfig.ee02.defaults` only. `build.sh` layers `sdkconfig.dev.defaults` into dev builds, and those are USB-flashed together with their bootloader. A `CONFIG_SECURE_BOOT=y` or `CONFIG_NVS_ENCRYPTION=y` in the dev overlay would pass CI and burn eFuses on a bench board.
- In `built` mode the resolved `CONFIG_NVS_ENCRYPTION`, `CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK` and `CONFIG_EFUSE_VIRTUAL` are only printed, not asserted. On ESP32-S3, NVS encryption with the HMAC key scheme burns an HMAC key into eFuse on first boot, even without flash encryption. So "resolved and unset" should fail the build if violated, not just be logged.

**Fix:** Add `${FIRMWARE_DIR}/sdkconfig.dev.defaults` to the loop. Add `'# CONFIG_NVS_ENCRYPTION is not set'`, `'# CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK is not set'` and `'# CONFIG_EFUSE_VIRTUAL is not set'` to the built-mode required lines.

### FW-WR-09: A 4 KiB stack buffer in `fp_ota_apply()` is live during the TLS handshake and signature verification on the 12 KiB main task (usage not measured)

**File:** `firmware/main/ota.c:128`; `firmware/sdkconfig.defaults:74`
**Severity:** WARNING

**Issue:** `uint8_t chunk[HASH_CHUNK_BYTES]` (4096 bytes) sits in the function frame, and Xtensa allocates the whole frame on entry. So it is reserved throughout:
- `esp_https_ota_begin()` (mbedTLS handshake)
- `esp_https_ota_perform()`
- `esp_https_ota_finish()` (`esp_image_verify` plus RSA-3072 verify)

Those calls stack on top of `app_main` → `fp_poll_once` (`fp_display_t` of about 1.2 KB). With `esp_app_desc_t` (256 B), `http_config` and the SHA context, this path is roughly 3 KB heavier than the heaviest existing TLS path (`fp_api_get_display` with its 2 KB `resp`). `sdkconfig.defaults` itself notes the TLS path already overflowed the default stack. A canary hit here panics, and the attempt is reported as interrupted every time.

**Fix:** Make the buffer `static` (single-threaded, one OTA per wake) or allocate it with `heap_caps_malloc` only for the read-back loop. Measure `uxTaskGetStackHighWaterMark(NULL)` after `finish` during the hardware session.

---

## Info

### FW-IN-01: `esp_ota_get_last_invalid_partition()` fully re-validates the invalid image on every boot after any rollback

**File:** `firmware/main/ota.c:221-229`
**Issue:** `fp_ota_boot_check()` calls it without any condition. In IDF 5.3.1 it runs `image_validate(..., ESP_IMAGE_VERIFY_SILENT)`, which hashes the whole slot and checks its signature (`esp_ota_ops.c:827`). After one rollback, every wake pays for that until the slot is overwritten. This battery-only device takes the cost on every wake.
**Fix:** Only query the invalid partition when `ota_try[0] != '\0'`.

### FW-IN-02: No watchdog feed between `esp_https_ota_begin()` and the first `perform()`

**File:** `firmware/main/ota.c:59-79`
**Issue:** Connect (30 s timeout), header fetch (30 s) and `get_img_desc` (reads 1 KB, 30 s) can add up to more than the 60 s TWDT with no `fp_wake_feed()` in between. On a stalling link this becomes a watchdog panic instead of a clean `fail-download`. It is recoverable, but the attempt gets misreported as interrupted and the frame backs off as if it had reset abnormally.
**Fix:** Call `fp_wake_feed()` after `begin` and after `get_img_desc`. Or lower `timeout_ms` so that the sum stays under the TWDT.

### FW-IN-03: Comments that no longer match the code

**Files / lines:**
- `firmware/main/ota_policy.h:74-78`: `fp_ota_image_check` says it runs "after signature and hash verification have already passed". In ota.c:79 it runs *before* the download. That is still safe, because the signature covers those descriptor bytes.
- `firmware/main/ota_policy.h:122`: `FP_OTA_RESULT_FAIL_SIZE` is described as "offer's size field failed fp_fw_size_parse", but it is only used for a mismatch in the downloaded length (ota.c:108-113). A malformed size just drops the offer.
- `firmware/main/wake_deadline.h:43-51`, `Kconfig.projbuild:26-29`, `tests/test_wake_deadline.c`: they say "a second Wi-Fi join after the trial-image reboot". The second join happens in the *same* wake, before the download. The trial reboot starts a fresh budget.
- `firmware/main/ota.h:21-23`: "(a later plan)" is planning history in a code comment, against the CLAUDE.md comment convention.
- `firmware/main/ota.h:86-90`: see FW-WR-01.

### FW-IN-04: The OTA wake budget assumes about 1.05 MB, but the offer allows up to 2.3 MB

**File:** `firmware/main/wake_deadline.h:25-30`; `firmware/main/validate.h:28-31`
**Issue:** `FP_WAKE_STAGE_OTA_S` (90 s) is derived from a 1.05 MB image at 12 KB/s. `FP_FW_MAX_IMAGE_BYTES` accepts 0x250000 bytes, and nothing links the two. As the image grows, a slow link makes every attempt fail on the deadline until the schedule is marked failed. The budget also leaves out the read-back hash and the two full-image verifications (`esp_ota_end` and `set_boot_partition`).
**Fix:** Add a `_Static_assert` or CI check tying the release image size to the throughput assumption, or derive the OTA stage budget from `FP_FW_MAX_IMAGE_BYTES`.

### FW-IN-05: `provision.sh --dry-run` prints the generated enrolment secret in plaintext, next to `--replace` registration commands

**File:** `firmware/provision.sh:427-432,497-501`
**Issue:** The redaction `sed` only masks `wifi_pass`. The `enrol_secret` line is printed as is, even though the header promises it is "never echoed". The dry run also prints ready-to-run `--replace` commands for a hash that no device holds. Pasting them de-registers a real, already-provisioned frame at its next re-enrolment.
**Fix:** Redact `enrol_secret` as well, and prefix the dry-run commands with a clear "DRY RUN - do not run" marker, or leave them out.

### FW-IN-06: OTA offer URLs are https-only even on dev builds

**File:** `firmware/main/api_client.c:529-530`
**Issue:** `fp_url_valid(url, ..., false)` ignores `s_allow_http`. A dev board provisioned against the http stub server will always log `ota offer ignored field=url`, so the OTA path cannot be tried on the bench without TLS. If this is intended, document it in PROTOCOL.md or VENDOR.md. Otherwise pass `s_allow_http`.

### FW-IN-07: Host-test gaps in `test_ota_policy.c`

**File:** `firmware/tests/test_ota_policy.c:107-114`
**Issue:**
- The ROLLED_BACK and INTERRUPTED cases pass `running_pending_verify=true`, which cannot happen after a real rollback (the old image is valid).
- No case pins the `ota_try == running && !pending` mapping (FW-WR-03).
- No case covers "trial pending plus a new offer" (FW-WR-02).

The policy functions ignore the flag on those branches, so the tests pass without exercising the real state.
**Fix:** Use `false` for the rollback and interrupted cases, and add cases for FW-WR-02 and FW-WR-03 once they are fixed.

---

_Reviewed: 2026-09-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

# Slice: Server, byos, release pipeline and deploy


# Phase 42: Code Review Report (server / byos / release pipeline / deploy)

**Reviewed:** 2026-09-28
**Depth:** standard (diff vs origin/main)
**Files Reviewed:** 27
**Status:** issues_found

## Summary

The path-handling side holds up. `/fw/<sha>.bin` is anchored to a 64-hex
regex on the raw path, gated on registry membership, checked with
`S_ISREG` and a size cap, and streamed in chunks. `firmware_image_path()`
never builds a path from an unvalidated string. The X-Fw-Version and
X-Ota-Result parsers are anchored and length-capped. No secret appears
in any `run:` text. The signing key is written 0600 under `$RUNNER_TEMP`
and removed by an `always()` step.

The problems are in the pipeline's main path and in the
state-machine invariants:

- The first real release never reaches the VPS: a re-deploy of an
  already-staged SHA throws away the new firmware (SRV-CR-01).
- The cancel-until-acknowledged rule can be broken, because byos and the
  companion decide on different snapshots and share no lock (SRV-CR-02).
- Device results are credited to whatever schedule is current, not the
  one the device actually ran. A late or resent "installed" can close a
  schedule that was never installed (SRV-CR-03).
- An offer the device never acts on locks the Update page with no way
  to recover, and so does a device-report `next_seq` that falls below
  the registry's `reconciled_seq` (SRV-CR-04).

The tests pass, but none of them covers these paths.

The live CA-chain guard was run once against `cortege.algernon.ovh` and
passed (rc=0).

## Critical Issues

### SRV-CR-01: A same-SHA deploy drops the newly published firmware, so the first release never reaches the VPS

**File:** `deploy/activate.sh:136-146` (with `:189-199`), `.github/workflows/firmware-release.yml:171-179`, `.github/workflows/ci.yml` deploy job
**Issue:** The firmware-release workflow ends with
`gh workflow run ci.yml --ref main`. That deploys **main's HEAD SHA**,
and in the normal flow this SHA was already deployed by the push to
main that came before the tag. `deploy.sh` streams the new
`firmware-releases/` into `.incoming-<sha>`. `activate.sh` then sees
that `releases/<sha>` already exists and runs `rm -rf "${INCOMING}"`,
which discards the fresh firmware. Line 189 then imports from
`${RELEASE_DIR}/firmware-releases`, which is the stale copy from the
first deploy of that SHA (empty, if no release existed then). The import
succeeds and prints nothing new, so the deploy goes green, but the
release is never published on the VPS.

Concrete failure: merge the phase-42 PR (push deploy of X ships 0
releases) → tag `fw-v1.0.0` on X → release job → dispatched deploy of X
→ the new release is silently dropped. It stays that way until some
unrelated commit lands on main. The same thing happens after a manual
rollback followed by a re-deploy of an older SHA.

`deploy/tests/test_activate.py` never re-runs activate for the same SHA
with new firmware, so the suite cannot catch this.
**Fix:** Treat firmware as per-deploy input, not part of the immutable
release dir. For example, keep the incoming firmware apart before the
staging branch and import from it:
```bash
FIRMWARE_RELEASES_DIR="${SKYPANE_ROOT}/releases/.firmware-${SHA}-$$"
if [ -d "${INCOMING}/firmware-releases" ]; then
    mv -T "${INCOMING}/firmware-releases" "${FIRMWARE_RELEASES_DIR}"
    chown -R root:root "${FIRMWARE_RELEASES_DIR}"; chmod -R go-w "${FIRMWARE_RELEASES_DIR}"
fi
# ... existing staging (mv -T / rm -rf INCOMING) ...
# import from FIRMWARE_RELEASES_DIR, then rm -rf it (trap on EXIT)
```
Add a test: activate SHA X with no firmware, then activate X again with
`firmware-releases/fw-v1.0.0/` in the incoming dir, and assert that the
import saw the new tag.

### SRV-CR-02: The cancel/replace-until-acknowledged rule races with byos; a cancelled schedule can still be offered and installed

**File:** `stub-server/byos_server.py:711-715` (registry read outside any lock) vs `server/firmware_registry.py:570-587` (`cancel_schedule`) and `:550-555` (`schedule_release`)
**Issue:** byos reads `registry.json` without `registry_lock`. It then
takes only its in-process `_device_report_lock`, computes the offer from
that snapshot and writes the `"offered"` event. `cancel_schedule()`
holds the flock on `registry.lock`, reads `device_report.json`, sees no
"offered" event and clears the schedule. The two processes share no
lock, so this interleaving is possible:
1. byos: `load_registry()` → schedule S (v1.3.0) present.
2. companion: `cancel_schedule()` → no offered event yet → returns
   `"cancelled"`, schedule cleared.
3. byos: `compute_offer()` on the stale snapshot → offer served,
   `"offered"` written for S.

The operator was told "cancelled", but the frame flashes v1.3.0. D-05
("cancellable until the device starts") is broken, and the VENDOR.md
claim that "a schedule the device has just been offered is no longer
cancellable from that instant" does not hold. `schedule_release()` has
the same race when it replaces an unacknowledged S1 with S2: the device
installs S1, and the Update page shows S2 as scheduled and cancellable.
**Fix:** Make the byos decision atomic with respect to registry
writers. In `_record_device_report_and_offer`, take
`firmware_registry.registry_lock(state_dir)` first (then
`_device_report_lock`, keeping one order everywhere), and load the
registry inside it:
```python
with firmware_registry.registry_lock(state_dir), _device_report_lock:
    registry = firmware_registry.load_registry(state_dir)
    ... compute_offer / write offered event ...
```
Catch `atomic_io.LockBusy` (a `TimeoutError`, so already an `OSError`)
as "no offer", which is what the existing handler does. Add a test that
interleaves cancel with a display poll (for example, patch
`compute_offer` to call `cancel_schedule` before it returns) and asserts
that no offer is served once cancel has returned "cancelled".

### SRV-CR-03: Result events are stamped with the current schedule id, not the schedule the device ran; stale or resent "installed" closes the wrong schedule

**File:** `stub-server/byos_server.py:715,736-741`, `server/firmware_registry.py:683-711`
**Issue:** byos tags every `X-Ota-Result` event with `schedule_id` from
the registry *as it is now*. It never checks the header's version
component against `schedule["version"]`. `reconcile()` then trusts that
id: on `token == "installed"` it clears the schedule, appends
`installed_at` to the *schedule's* release and sends "Firmware
<schedule version> installed". The event's own `version` is ignored.
The firmware resends X-Ota-Result on every poll until a 200 response
parses (`firmware/main/api_client.c:635-640`), so late and duplicate
deliveries are part of the protocol, not an edge case.

Concrete failure: S1 = v1.3.0 installs. The device reports
`installed;fw-v1.3.0`, byos records it, but the response is lost. The
poll loop reconciles and S1 is cleared. The operator schedules S2 =
v1.4.0. At the next wake the device resends `installed;fw-v1.3.0`, and
byos stamps it with S2's id. Reconcile then clears S2, records v1.4.0 as
installed and pushes "Firmware fw-v1.4.0 installed". If v1.4.0 then
fails on the device, those results carry `schedule_id = None`, so no
attempt is counted, no failure notification is sent and the Update page
reports success. The SRV-CR-02 race produces the same misattribution.
**Fix:** In byos, attribute a result to the current schedule only when
its version matches:
```python
sid = schedule_id if (schedule is not None and result_version == schedule.get("version")) else None
```
In `reconcile()`, check the same thing defensively before moving
attempts or clearing (`event.get("version") == schedule["version"]`).
Better still, have the firmware echo the offer's schedule id (or an
attempt nonce) in X-Ota-Result so a resend can be deduplicated; see
SRV-WR-01.

### SRV-CR-04: The Update page can lock with no recovery: an offer the device never acts on, or a `next_seq` below `reconciled_seq`

**File:** `server/firmware_registry.py:419-435` (`acknowledged`), `:596-626` (`compute_offer`), `:621`/`:649` (`seq <= reconciled_seq` filters), `stub-server/byos_server.py:724` (`next_seq = device_report["next_seq"]`)
**Issue (a) — an offer the device ignores:** byos appends a new
`"offered"` event on *every* poll while an offer is outstanding.
`acknowledged()` is true whenever the newest event is "offered". If the
device never produces an X-Ota-Result, `cancel_schedule()` returns
`not_cancellable` and `schedule_release()` returns `busy` forever. The
attempt counter never moves, because only result events count. Ways the
device ends up never reporting:
- The frame runs a pre-OTA build. Its `git describe` version such as
  `a1b2c3d` is not even checked by `compute_offer`, which floors only
  the *target* version.
- The firmware's permissive offer parser rejects a field and "only logs
  which field failed".

The only way out is to edit the registry JSON by hand on the VPS.

**Issue (b) — sequence regression:** byos takes `next_seq` from
`device_report.json`, and the tolerant loader resets it to 0 when the
file is missing or corrupt. The same happens after a restore where the
tarball captured `device_report.json` just before a reconcile and
`registry.json` just after (tar reads them at different moments with no
lock). New events then get seq 1, 2, … while `reconciled_seq` is still,
say, 40:
- `reconcile()` ignores them.
- `compute_offer()` stops counting failures, so the frame retries
  without limit and D-15's three-attempt rule is gone.
- An "installed" result is never reconciled. The schedule stays
  "in_progress" and, per (a), cannot be cancelled or replaced until seq
  climbs past 40, which after a successful install never happens because
  no more events are produced.
**Fix:**
- (b) In byos, compute
  `next_seq = max(doc["next_seq"], max(all event seqs), registry["reconciled_seq"])`
  before assigning, so seq is monotonic against the registry.
- (a) Do not offer to a device whose own `fw_version` is not
  `at_or_above_floor`. Emit "offered" only on the first offer per
  schedule and per device, or count N offers with no following result as
  a counted attempt (a synthetic `fail-ignored`), so the schedule
  eventually reaches "failed" and becomes replaceable. Consider an
  operator "force clear" for a stuck in-progress schedule.
- Add tests for both.

## Warnings

### SRV-WR-01: A resent X-Ota-Result is counted as a new attempt

**File:** `stub-server/byos_server.py:733-741`, `server/firmware_registry.py:617-624,696-711`
**Issue:** The firmware sends the pending result on every poll until a
200 response parses. If the response is lost after byos has written the
event, the same `fail-*;v` or `rollback;v` is recorded again with a new
seq and counted again. One real failure plus two lost responses marks
the release "failed" and fires the failure push.
`test_third_counted_failure_withdraws_offer_in_the_same_response` sends
three identical headers and expects three attempts. It encodes this
ambiguity as correct instead of testing for it.
**Fix:** Deduplicate on the server. Ignore a result whose (token,
version) equals the device's previous result event for the same
schedule unless an `"offered"` event *acted on by the device* lies in
between. Or, preferably, include an attempt nonce or schedule id in
X-Ota-Result on the firmware side and deduplicate on it.

### SRV-WR-02: The environment gate runs before the tag/ancestor guard, so the workflow comment is false

**File:** `.github/workflows/firmware-release.yml:31,52-66`
**Issue:** `environment: firmware-signing` is job-level. The reviewer
approval therefore happens **before any step**, including the "Guard the
tag shape and that it is on main" step. Its comment says a bad tag
"fails here -- before … the firmware-signing environment gate is ever
reached". That is wrong, and a reviewer relying on it would approve an
unchecked tag.

A tag-push workflow also runs the workflow file *from the tagged
commit*. Anyone who can push a `fw-v*` tag on an unmerged branch commit
can delete the guard, or add a step that reads `FW_SIGNING_KEY`. The
in-file ancestor check is therefore not a control against unreviewed
code, and the human approval is the only one.
**Fix:** Move the guard into a separate job with no environment and
make the signing job depend on it (`needs: guard`), so approval is only
requested for tags that pass. Add a repository ruleset restricting who
can create `fw-v*` tags. Restrict the `firmware-signing` environment's
deployment refs to `fw-v*` tags. Document that the approver must confirm
the tag's commit is on main. Correct the comment.

### SRV-WR-03: The signing key is mounted into a container pulled by a mutable tag, with network enabled

**File:** `.github/workflows/firmware-release.yml:99-106`
**Issue:** `docker run -v "$KEY_PATH:/key.pem:ro" espressif/idf:v5.3.1`
resolves a mutable Docker Hub tag at run time and gives the container
default networking. If that tag is ever compromised or re-pointed, the
private key can be exfiltrated. This undermines D-10 ("never stored
anywhere but the secret").
**Fix:** Pin the image by digest (`espressif/idf@sha256:…`) and add
`--network none` to the signing (and verify) `docker run`. Or sign with
a hash-pinned `esptool` installed on the host from a `--require-hashes`
requirements file. Also set `persist-credentials: false` on
`actions/checkout`, so the `contents: write` / `actions: write` token is
not left in `.git/config` through the build and signing steps.

### SRV-WR-04: One sha conflict or one bad GitHub Release blocks every future deploy

**File:** `server/firmware_cli.py:135-140`, `deploy/activate.sh:190-196`, `.github/workflows/ci.yml` "Download firmware releases"
**Issue:** The deploy imports *every* published release on *every*
deploy, and any per-item failure aborts activation. Two cases:
- A release whose assets change after they were first imported gives
  "already registered with a different sha256". This happens when a
  release is deleted and the workflow re-run (RSA-PSS signatures are
  randomized, so re-signing always changes the sha), or after
  `gh release upload --clobber`.
- A manually created `fw-v*` release without `release.json` makes
  `gh release download` fail under `set -e`.

From then on, every ordinary code deploy fails until someone performs
registry surgery on the VPS. Firmware bookkeeping should not be able to
block unrelated server deploys.
**Fix:** Import only releases that are not yet registered, and report
an unchanged-version sha conflict loudly but do not fail on it (or fail
only for tags that are new in this deploy). In the release workflow,
refuse to run if a release for the tag already exists. In the download
loop, skip releases that lack either asset, with a warning.

### SRV-WR-05: `import-dir` does not cross-check the directory tag against `manifest["version"]`

**File:** `server/firmware_cli.py:117-136`
**Issue:** The tag in the subdirectory name picks
`skypane-<tag>.bin`, but the version that gets published is whatever
`release.json` says. `fw-v1.3.0/release.json` with
`"version": "fw-v1.4.0"` publishes the v1.3.0 image as v1.4.0.
`compute_offer`'s same-version check and the floor check then run
against the wrong label.
**Fix:**
```python
if manifest.get("version") != name:
    print("firmware_cli: %s: release.json version %r does not match directory" % (name, manifest.get("version")), file=sys.stderr)
    ok = False; continue
```

### SRV-WR-06: `import-bench` accepts plain release-tag versions and cannot work on the VPS

**File:** `server/firmware_cli.py:147-192`, `server/firmware_registry.py:469`
**Issue:**
- `bench=True` selects `VERSION_RE`, which also matches `fw-v1.3.0`
  with no suffix. A bench image can therefore squat a future release
  version. The real CI release then fails import with a sha conflict and
  triggers SRV-WR-04's deploy block.
- `_current_commit()` needs a git checkout. `/opt/skypane/current` is
  `git archive` output with no `.git`, so on the only host the real
  frame polls, `import-bench` always exits 1 with "could not resolve a
  git commit".
- In a checkout, the recorded commit is the checkout's HEAD, not the
  commit the bench image was built from.
**Fix:**
- Require a suffix for bench versions:
  `VERSION_RE.match(v) and not RELEASE_TAG_RE.match(v)`.
- Accept `--commit` explicitly, or allow a documented placeholder, so
  the command can run on the VPS.
- Document where the command is meant to run.

### SRV-WR-07: `_resolve_device_id` iterates the shared token dict without a snapshot

**File:** `stub-server/byos_server.py:671`
**Issue:** `for mac, stored in state["tokens"].items():` runs on a
`ThreadingHTTPServer` worker while `/setup` can insert into the same
dict (`:873`). That raises `RuntimeError: dictionary changed size during
iteration`. The caller catches only `OSError` (`:935-942`), so the
display poll returns 500 and the device backs off. `bearer_ok()` already
uses `list(...)` for exactly this reason.
**Fix:** Iterate over `list(state["tokens"].items())`. Consider widening
the caller's `except OSError` to `except Exception` (logged by type
name), in line with the "never a 500" intent in its own comment.

### SRV-WR-08: A corrupt `registry.json` is wiped by the next write

**File:** `server/firmware_registry.py:304-316,732-743`
**Issue:** `load_registry()` maps any `ValueError` or unexpected shape
to the empty default document, and does the same *inside* the
read-modify-write paths. With a corrupt file, the next poll cycle's
`apply_reconcile()` sees `reconciled_seq` move from 0 to the device's
highest seq and saves the default document. Every release, the
`installed_at` history, the schedule and the floor are lost. `/fw/`
returns 404 until the next deploy re-imports, and a download in
progress fails. Unknown fields and a future `schema` are also silently
dropped on every rewrite.
**Fix:** In the locked writers, use a strict loader that treats only
`FileNotFoundError` as empty. On a parse error, refuse to write (raise
and log) and move the file aside as `registry.json.corrupt-<ts>`. Keep
the tolerant loader for readers only.

### SRV-WR-09: `publish_release` never re-verifies an image that is already on disk

**File:** `server/firmware_registry.py:520-522`
**Issue:** `if not os.path.exists(target): atomic_write(...)`. A
`<sha>.bin` that exists with the wrong bytes is kept forever, and every
re-deploy re-imports "idempotently" without noticing: a hand-copied
partial file, disk corruption, or a restore of a truncated archive.
byos serves it, and the device fails with `fail-hash` three times.
**Fix:** When the target exists, hash it (with `_hash_and_size`). If
the digest differs, rewrite it atomically from the verified
`image_bytes`.

### SRV-WR-10: No test covers the new failure modes; one test only proves import-before-restart, not before-swap

**File:** `deploy/tests/test_activate.py:450-466`, `stub-server/test_ota_offer.py`, `server/test_firmware_registry.py`
**Issue:**
- `test_firmware_import_runs_before_swap_when_present` asserts that the
  import runs before `systemctl restart`, not before the `current` swap.
  Moving the import after `mv -T` would still pass.
- There is no test for: same-SHA re-deploy with new firmware (SRV-CR-01),
  cancel racing a display poll (SRV-CR-02), a result whose version differs
  from the current schedule (SRV-CR-03), a `next_seq` reset or a never-acting
  device (SRV-CR-04), or a duplicate X-Ota-Result (SRV-WR-01).
**Fix:** Have the fake `ln`/`mv` log the swap, or record
`readlink current` inside the fake `firmware_cli`, and assert that it
still points at the previous release during import. Add the regression
tests listed with each finding above.

## Info

### SRV-IN-01: The README's `firmware_cli list` command cannot import `server`

**File:** `deploy/README.md:386`
**Issue:** `sudo -u skypane …/python3 -m server.firmware_cli …` runs
from the ssh user's home directory, so `server` is not importable
(`ModuleNotFoundError`). The CLI docstring itself says to run it from a
release directory.
**Fix:** `ssh … "cd /opt/skypane/current && sudo -u skypane /opt/skypane/venv/bin/python3 -m server.firmware_cli --state-dir /opt/skypane/state list"`.

### SRV-IN-02: Plan references and a stale comment in the release workflow

**File:** `.github/workflows/firmware-release.yml:148-149,172-174`
**Issue:** "(plan 15)" and "(plan 16)" break the no-plan-IDs-in-comments
convention. `check_comment_history.py`'s `plan \d-\d{2}` pattern misses
this form. The trigger-step comment still says "ci.yml gains a
workflow_dispatch trigger in a later plan; until then this step fails",
which is no longer true. `server/firmware_registry.py:87` and
`stub-server/VENDOR.md` refer to "the interfaces block", which is a plan
artifact.
**Fix:** Reword these comments without the history, and consider
widening the guard's regex.

### SRV-IN-03: `publish_release` reads the whole image into memory before comparing it with the capped size

**File:** `server/firmware_registry.py:438-455,498-506`
**Issue:** The manifest size is capped at `MAX_IMAGE_BYTES`, but
`_hash_and_size` reads the whole file, whatever its size, and keeps it
all in `chunks` before the `actual_size != size` check. The
"never … whole file" wording is also inaccurate: it returns
`b"".join(chunks)`.
**Fix:** Stop reading once the byte count exceeds `size` (raise), or use
`staged_write` to stream-copy and hash in one pass.

### SRV-IN-04: An unexpected exception in `cmd_import_dir` aborts the whole import with a traceback

**File:** `server/firmware_cli.py:135-140`
**Issue:** Only `ValueError` is caught. `LockBusy` (a `TimeoutError`)
or `PermissionError` from `publish_release` produces a traceback, and
the remaining tags are not reported.
**Fix:** Also catch `OSError` per item, print `type(exc).__name__`, and
set `ok = False`.

### SRV-IN-05: The failure push can read "back on None"

**File:** `server/poll_cycle.py:423-424`, `server/firmware_registry.py:702-711`
**Issue:** `back_on` is the reporting device's current `fw_version`,
which is `None` if the device never sent a valid X-Fw-Version. The push
then reads "Update failed, back on None". It is also the version at
reconcile time, not at the time of the event.
**Fix:** Fall back to a neutral body ("Update failed") when `back_on` is
None.

### SRV-IN-06: The backup filter now also drops nested files in the other allow-listed directories

**File:** `deploy/backup/skypane_backup.py:107-118,216`
**Issue:** `_no_symlinks_or_known_excluded` applies `KNOWN_EXCLUDED`
(which includes `img`, `history.db`, `panel.bin` and `*.tmp`) to the
basename of every nested entry in `gallery/` and `illustration_overrides/`
as well as `firmware/`. The patterns were meant for top-level names.
Nothing breaks today, but a future nested `img/` directory would vanish
from backups without any sign.
**Fix:** Apply the basename filter to `firmware/` only, or use a
dedicated per-directory exclusion list such as `("*.lock", "*.tmp")`.

### SRV-IN-07: The chain guard checks no hostname and ignores the `s_client` exit status

**File:** `scripts/check_cert_chain.py:47-66`
**Issue:** Whatever certificate the endpoint returns is verified for
trust only, not checked against the host name. A default-vhost or wrong
certificate issued under ISRG would pass. The "has expired" branch also
reports the *leaf* as expired when the expired certificate is an
intermediate.
**Fix:** Add `-verify_hostname host` to `openssl verify`, or check the
leaf's SAN. Word the expiry message as "a certificate in the chain has
expired".

### SRV-IN-08: A source-text test

**File:** `deploy/tests/test_release_manifest.py:227-229`
**Issue:** `test_no_shell_true_in_the_script` greps the script's source
text, which goes against the project's behaviour-over-source rule. It
proves nothing about runtime (for example, `shell=bool(1)` would pass),
and the other tests already show the script works with argument lists.
**Fix:** Drop it, or replace it with a behavioural test (a tag holding
shell metacharacters is rejected, or `subprocess.run` is monkeypatched
and asserted to be called with a list and no `shell`).

---

_Reviewed: 2026-09-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

# Slice: Companion Update page and UPDATING screen


# Phase 42: Code Review Report (companion Update page + UPDATING hold screen)

**Reviewed:** 2026-09-28
**Depth:** standard (diff vs `origin/main`)
**Files Reviewed:** 21
**Status:** issues_found

## Summary

**Security holds up.** Both new POST routes go through `routes.ROUTES` with
`auth_required=True`, so `_dispatch()` checks `auth.post_origin_ok()` first
and then `require_session()`. This is the same gate the Settings actions use.
`test_post_origin.py` and the render snapshot list both routes. Every value
that comes from the registry passes through `html.escape(quote=True)`:
version strings in text and in the `value=`/`data-confirm=` attributes, notes
via `data_table()`, dates via `concise_timestamp_html()`, and the rollback
versions. The version posted to `/update/install` is checked against
`VERSION_RE` and `VERSION_MAX_LEN` before anything renders it. Every redirect
target is a literal `UPDATE_ROUTE` plus a fixed flash key, so there is no open
redirect. Displayed timestamps are in Europe/Paris, because
`local_clock_text()` converts to `LOCAL_TZ`. I found no blocker.

**The problems are correctness, state display and UI.**
- A French leak: the default fallback of `concise_timestamp_html()` shows untranslated English.
- The page never names the version that is scheduled, in progress or failed.
- Install buttons are still shown during an in-progress update, and clicking one ends on a flash that says "please try again" when retrying cannot work.
- The next-wake sentence can print a time that is already past.
- At 375 px the history table is about twice the viewport width. I measured this in a real Chromium: the Install button sits off-screen.
- Bench builds look the same as tagged releases.
- The UPDATING glyph's arrowheads do not show a direction, and its ink overflows its declared footprint. This matters because the glyph gets baked into the firmware mask.
- Three tests pass vacuously.

I checked these by rendering `update_page()` in-process under EN and FR, and by
driving the real `companion/app.py` with Playwright at 375 px (EN and FR).
Screenshots are in the scratchpad (`update-en-375.png`, `update-fr-375.png`,
`glyph.png`, `updating.png`).

## Warnings

### CMP-WR-01: The update-state timestamp shows the untranslated English "no reading yet" (also wrong in English)

**File:** `companion/pages/update_page.py:143` (also `:135`, `:218`, `:225`)
**Issue:** `_status_state_row_html()` calls
`layout.concise_timestamp_html(view.get("state_at"), ctx.now)` with no
`fallback`. The helper's default fallback is the hard-coded English literal
`"no reading yet"` (`companion/ui_time.py:398`), which is not a translated
Message. `state_at` is `None` in the most common day-one state: no release
published yet, so `update_view()` returns `state="available"` and
`state_at=_newest_release_published_at()`, which is `None`. It can also be
`None` in `in_progress` when no event matches.
Result: a French operator on a fresh install sees
`Disponible` / `no reading yet`. An English operator sees "Available / no
reading yet", which is battery-reading vocabulary under an update state.
Rendered output:
```
<span class="dot-label">Disponible</span></p><div class="widget-detail">no reading yet</div>
```
The same default applies to the Date and Installed cells. They are safe today
only because `_normalise_release` forces `released_at` to be a string.
**Fix:** Pass `fallback=""` and leave out the detail `<div>` when it would be
empty. Otherwise pass a translated Message:
```python
ts = view.get("state_at")
timestamp_html = layout.concise_timestamp_html(ts, ctx.now, fallback="") if ts else ""
detail = '<div class="widget-detail">%s</div>' % timestamp_html if timestamp_html else ""
```
Add a FR test for the empty-registry state that asserts `"no reading yet"`
is not in the page.

### CMP-WR-02: The page never says WHICH version is scheduled, in progress or failed

**File:** `companion/pages/update_page.py:139-155`, `:228-240`
**Issue:** The Status card shows only the state word and a timestamp:
"Scheduled — installs at the next wake, around 14:00." No version appears in
the Scheduled, In progress or Failed states. The history table does not mark
the target row either. The scheduled release keeps its normal **Install**
button, which looks exactly like every other row (confirmed in the rendered
`scheduled` state).
Failure scenario: the operator schedules `fw-v1.1.0`, comes back later, and
cannot tell from the page what is about to install. After a Failed outcome
they cannot tell which release failed. The UI-SPEC's Surface 2 relies on this
exact affordance ("the version is visible in the companion Update page
instead"), and it does not exist. `update_view()` does not expose
`schedule.version` either. The fix needs one view field, not a rule
re-derived in the page.
**Fix:** Add `"target_version": schedule.get("version") if schedule else None`
to `update_view()`'s return value. Render it in the state row as a mono span,
e.g. "Scheduled: fw-v1.1.0", with EN/FR strings. On the matching history row,
replace Install with a quiet "Scheduled" label, or at least tag the row.

### CMP-WR-03: Install stays offered during In progress and fails with a misleading "please try again"

**File:** `companion/pages/update_page.py:228-229`; `companion/app.py:1176-1178`
**Issue:** `installable` in the view ignores the schedule state. While the
device has acknowledged an offer (`state == "in_progress"`), every row other
than the running one still renders an **Install** form. This includes the
version being installed at that moment (verified by render). Clicking one
goes through the confirm page. `schedule_release()` then returns `"busy"`, and
the handler maps every non-`"scheduled"` result to
`FLASH_UPDATE_SCHEDULE_FAILED_TEXT`: "Couldn't schedule that update — please
try again." Trying again can never succeed until the install finishes. The
copy tells the operator to do the one thing that cannot work.
**Fix:** Hide the Install forms when `view["state"] == "in_progress"`. This
reads the view's own state and re-derives no rule. Add a separate busy flash,
e.g. "An update is already installing — wait for it to finish.", and route
`result == "busy"` to it in `_handle_update_install_post()`.

### CMP-WR-04: The next-wake time can already be in the past, and it bypasses `frame_state`

**File:** `companion/pages/update_page.py:303-320` (used by `:150-155` and by the confirm page from `companion/app.py:1163`)
**Issue:** `compute_next_wake_text()` formats `last_checkin + interval`
without checking it against `now`. When the frame is overdue (offline, flat
battery, Wi-Fi down), the Scheduled sentence and the confirm page both say
"installs at the next wake, around 09:05" even though 09:05 was hours ago.
`companion/frame_state.py` exists to resolve DUE/HELD/LATE from
`wake.next_wake_status()`, and its docstring says every consumer resolves
from that triple "so they can never disagree". Home shows "Expected since
09:05" while Update promises an install "around 09:05".
There is a second disagreement. This function passes `battery_critical=...`
and Home (`home_page.py:328`) does not, so the two pages can show different
next-wake times.
Also, under D-12 the device defers while battery-low is active. The sentence
still promises an install at the next wake.
**Fix:** Call `wake.next_wake_status()` and `frame_state.resolve_state()`. On
`STATE_LATE` or `STATE_UNKNOWN`, return `""` so the existing
`UNKNOWN_TIME_TEXT` path is used, or use a "when the frame next checks in"
string. On `STATE_HELD`, use the quiet-hours wording. Pass the same arguments
Home passes so the two pages cannot drift.

### CMP-WR-05: At phone width the Version history table is about twice the viewport, and Install is off-screen

**File:** `companion/pages/update_page.py:255-257`; no `data-table--firmware-history` rule in `companion/static/style.css`
**Issue:** I measured this in real Chromium at 375×812 with three releases and
two realistic notes each:

| | `.data-table-wrap` clientWidth | scrollWidth | Install button x-range | row height |
|---|---|---|---|---|
| EN | 293 px | 580 px | 539–605 px | 363 px |
| FR | 293 px | 596 px | 542–621 px | 315 px |

The row's only primary action is more than a full screen-width to the right,
behind a horizontal scroll with nothing pointing to it. With `prose=True`
(`min-width: 0`), the Notes column wraps one or two characters per line, so
the notes cannot be read (see `update-en-375.png`). The fixed tab bar also
covers the middle of the tall first row. `modifier="firmware-history"`
emits a class with no rule behind it. `test_browser_update.py`'s "mobile-fit
gate" measures only the nav sheet and never the page's own content.
`_install_submit(page).click()` passes only because Playwright scrolls the
button into view. The project's own lesson
(`feedback_real_device_ui_verification`) is that this kind of check misses
real phone defects.
**Fix:** Below 960 px, render each release as a stacked card: version and
date on one line, notes as a list, Install underneath. Otherwise, move Notes
into a full-width second row or a `<details>`. Add a
`data-table--firmware-history` rule for the layout. Add a browser check at
375/390 px in EN/FR asserting that the first Install button's
`getBoundingClientRect().right <= innerWidth` without horizontal scrolling,
and that the notes cell is at least some minimum width.

### CMP-WR-06: Bench builds look the same as tagged releases and can be installed

**File:** `companion/pages/update_page.py:211-240`
**Issue:** `update_view()` exposes `release["bench"]`. `publish_release(...,
bench=True)` exists precisely to admit non-tag versions such as
`fw-v1.2.0-bench1`. The page drops the flag. A bench image appears in the
history table and gets an accent **Install** button just like a CI-signed
tagged release. The only hint is the version suffix, and the operator has to
know that convention.
**Fix:** Render a label-voice "Bench" chip next to the version when
`release.get("bench")` is true (EN/FR string). Consider also a line on the
confirm page ("This is a bench build").

### CMP-WR-07: The UPDATING glyph's arrowheads show no direction, and its ink overflows the declared 76 px footprint

**File:** `server/plane/render/glyphs.py:297-330`
**Issue:**
1. `_draw_updating_arrowhead()` puts both wings at `tip_angle ± 18°` on the
   same inner radius. That makes a V that is symmetric about the radial line
   and points outward, not along the arc's tangent, so it does not show a
   rotation direction. Rendered at 3× (`glyph.png`), each arc ends in a
   notched "W"-like spike rather than an arrow.
2. The tip sits on the outer bounding radius. `ImageDraw.arc(width=8)` draws
   inward from the box edge, so the stroke's centreline is at `r - 4`. The
   8 px-wide chevron line is centred on `r`, so it sticks 4 px outside the
   ring. Measured: drawn at `top_y=60` with a declared height of 76 (bottom
   136), the ink bbox is `(62, 57, 139, 139)`. That is 3 px above and 3 px
   below the returned height, which `_build_hold_canvas()` uses to space the
   label.
   The docstring's "never exceeding its radius" is false.
   `test_draw_updating_icon_height_and_stroke_budget` checks only the
   *returned* number and never the ink extent, so it cannot catch this.

This glyph is baked into `firmware/main/updating_screen_mask.h` and ships in
the image flashed over USB. Any fix needs a new firmware release.
**Fix:** Put the tip on the stroke centreline (`r - stroke/2`). Point the
chevron along the tangent: wings at the tip, offset backwards along the arc
by about 20° and ±`k` px radially. Add a test asserting the ink bbox lies
within `[top_y, top_y + returned_height]`. Then regenerate the mask in the
CI-equivalent container (python:3.14 + libraqm0).

### CMP-WR-08: `test_install_implausible_version_treated_as_unknown_never_echoed` asserts against an empty 303 body

**File:** `companion/test_update_actions.py:242`
**Issue:** The request returns a 303 from `Handler.redirect()`, which always
sends `Content-Length: 0`. `assert hostile not in body.decode(...)` is
therefore always true, whatever the handler does with the value. The test's
headline claim, "never echoed", is not tested. A regression that rendered
the confirm page (200) with an escaped hostile value would fail the
`status == 303` line instead. A regression that put the value into the
`Location` header would pass.
**Fix:** Assert on what can actually carry the value:
```python
assert hostile not in headers.get("Location", "")
assert headers["Location"] == "%s?flash=%s" % (layout.UPDATE_ROUTE, update_page.FLASH_UPDATE_SCHEDULE_FAILED)
```
Add a follow-up GET of that location, asserting that neither `hostile` nor
its escaped form appears in the served page.

### CMP-WR-09: The "newest first" ordering test cannot fail

**File:** `companion/test_update_page.py:80-96`
**Issue:** Both fixture releases share `published_at=_NOW`, so
`sorted(..., key=published_at, reverse=True)` keeps insertion order. The test
passes with any sort direction, and with no sort at all. The assertion
message ("expected newest-published-first ordering to still put fw-v1.0.0
first here") even admits that the *older* release comes first.
**Fix:** Give the releases distinct `published_at` values, with the older
release inserted first. Assert that the newer one's row comes first.

### CMP-WR-10: The per-state timestamp assertion is always satisfied by the history table

**File:** `companion/test_update_page.py:176`
**Issue:** `assert "data-relative" in html` is meant to prove that each state
row renders "a timestamp element". Every case in the loop has at least one
release, though, and every release row's Date cell already emits
`<time ... data-relative>`. The assertion holds even if the state row renders
no timestamp. The CMP-WR-01 fallback defect went unnoticed partly because of
this.
**Fix:** Slice the Status `<section>` (from the first `<section` to its
`</section>`) and assert `data-relative` inside that slice only. Add an
empty-registry case that asserts the English/French fallback text is absent.

## Info

### CMP-IN-01: The confirm page renders for versions that cannot be installed

**File:** `companion/app.py:1149-1165`
**Issue:** Any string that matches `VERSION_RE` gets "Install firmware fw-v9.9.9?"
at 200, even when it is unknown, the running version, below the floor, or the
target of an in-progress update. The rejection only comes after the second
POST. This is not a security issue: the value is escaped and the registry is
untouched. It does waste a step and misleads.
**Fix:** Before rendering, compute `update_view()` once and look the version
up in `view["releases"]`. If it is missing or `installable` is false, redirect
to the failure flash. This reuses the view's own flag and re-derives nothing.

### CMP-IN-02: The JS `data-confirm` text leaves out the wake time D-04 asks for

**File:** `companion/pages/update_page.py:68-70`, `:198-208`
**Issue:** D-04 says "The dialog names the version and the next expected wake
time". The `window.confirm()` text is "Install %s now? It will apply at the
next wake." The server confirm page does include the time, so D-04 is met on
the no-JS path only.
**Fix:** Pass `next_wake_text` into `_install_form_html()` and add
"…around %s." (EN/FR).

### CMP-IN-03: The FR card heading "État" is the same word as the Health nav label

**File:** `companion/i18n_fr/update.py:21`
**Issue:** `update.status` maps to "État", which is also `nav.health`. On the
French Update page, the first card is titled with the name of a different
page in the same Advanced group.
**Fix:** Use "Statut", or "État de la mise à jour".

### CMP-IN-04: The FR rollback wording "Firmware rétabli" reads as "firmware restored"

**File:** `companion/i18n_fr/update.py:35-37`
**Issue:** "rétabli" suggests something was repaired or restored, not that the
frame fell back to the previous image.
**Fix:** e.g. "Retour à la version précédente — la mise à jour vers %s a échoué
au démarrage d’essai ; le cadre est revenu à %s."

### CMP-IN-05: The Cancel-failure flash blames the device when the lock times out

**File:** `companion/app.py:1188-1195`
**Issue:** An `OSError` or a `LockBusy` after 10 s both show "Couldn't cancel —
the frame may have already started." Neither case means the frame has
started.
**Fix:** Map `None` (the exception path) to a generic "please try again" key,
and keep the current copy for `"not_cancellable"` only.

### CMP-IN-06: The Action column's `<th>` is empty

**File:** `companion/pages/update_page.py:252-254`
**Issue:** The fifth header is `""`. Screen readers announce an unnamed column
for every Install cell.
**Fix:** Use a visually-hidden "Action"/"Action" header. `data_table()` escapes
headers, so it needs a small raw-header option or a CSS-hidden text label.

### CMP-IN-07: The new controls are below the 44 px hit-target register and were not measured

**File:** `companion/pages/update_page.py:158-165`, `:198-208`, `:298-299`
**Issue:** The Install button measured 66×36 at 375 px. The Cancel button uses
`button.calendar-disconnect-btn` (`min-height: 30px`, 12 px). The confirm
page's Cancel is a bare `.text-label` link. The design system says "Hit
targets are MEASURED, never declared". None of these controls goes through
`_assert_hit_target()`.
**Fix:** Add `_assert_hit_target()` checks for all three, or record an
explicit exemption with a reason.

### CMP-IN-08: "Scheduled" appears twice in a row

**File:** `companion/pages/update_page.py:57-59`
**Issue:** The dot label says "Scheduled" and the sentence directly below
starts "Scheduled — installs at…" (FR: "Planifiée" twice).
**Fix:** Drop the leading word: "Installs at the next wake, around %s."

### CMP-IN-09: Leftover test names, plan-task headers and a debug print

**File:** `companion/test_companion_app_01.py:489` (`..._exactly_six_links_...` now asserts 7); `companion/test_update_page.py:65,313` ("Task 2:", "Task 1:" section headers); `companion/test_browser_update.py:304-306` (`print("D-02 mobile-fit: ...")`)
**Issue:** The CLAUDE.md comment convention forbids plan and decision IDs. The
guard scans comments, not a `print()` string or a banner header, so these slip
through. The added "then to 24" and "23 -> 24" lines in
`test_companion_app_01.py` continue change-history narration in comments.
**Fix:** Rename the test, drop "Task N"/"D-02", and remove the print or turn it
into an assertion message.

### CMP-IN-10: `test_build_canvas_never_produces_the_updating_canvas` is close to vacuous

**File:** `server/test_updating_screen.py:160-173`
**Issue:** Four fixed dithered canvases with different glyphs and text can
never be byte-equal to the UPDATING canvas. The test cannot fail unless one of
those four states were rewired to this exact composition.
**Fix:** Assert that `build_canvas()` rejects or never accepts an
`"updating"` state. Alternatively, drop the test in favour of the
dispatch-table test that already exists.

### CMP-IN-11: The mask-drift failure message tells you to regenerate on the host venv

**File:** `server/test_updating_screen_mask.py:46-60`
**Issue:** The message tells the developer to run
`server/.venv/bin/python3 firmware/tools/gen_fault_screen.py --screen updating`.
On macOS, without libraqm, that output drifts by 1 px from CI's, so following
the hint produces a header that fails CI.
**Fix:** Point the message at the CI-equivalent container command
(python:3.14 + libraqm0).

### CMP-IN-12: The Update page does not auto-refresh, so Cancel outlives its window

**File:** `companion/app.py:305-315` (the `_PAGE_SCRIPTS`/freshness registration); `companion/pages/update_page.py:158-165`
**Issue:** `/update` is not a freshness page. After the device acknowledges,
the Cancel button stays until a manual reload. Clicking it then gives the
cancel-failed flash. It is also the only place the operator learns the update
has started. The Installed column shows only `installed_at[-1]`, while D-03
asks for "which were installed when".
**Fix:** Consider registering `/update` as a freshness page keyed on
(registry mtime, device-report mtime). Consider listing every install date in
the cell's `title`, or as a list.

---

_Reviewed: 2026-09-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
