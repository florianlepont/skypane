---
phase: 42
slug: remote-firmware-update-over-the-air-ota-promoted-from-seed-0
status: verified
# threats_open = count of OPEN threats at or above block_on severity (the blocking gate)
threats_total: 74
threats_closed: 74
threats_open: 0
asvs_level: 1
block_on: high
created: 2026-09-29
---

# Phase 42 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Audited at commit `85faa81d` (main) plus the completed UAT, branch `claude/phase-42-close`.

**Result:** 74 threats in the register (T-42-01 .. T-42-73 and T-42-SC). 63 are `mitigate`, 11 are `accept`, 0 are `transfer`. All 74 are CLOSED. No open threat, blocking or non-blocking.

**Severity note.** The plan-time registers carry no Severity column. Severity below was assigned by the auditor (impact x likelihood, before mitigation). It is informational here because nothing is open; if any row is re-opened later, an unranked row would count as critical under the fail-closed rule, so keep the column.

**Depth.** ASVS level 1: each mitigation was verified as present in the cited file, and where the plan named a test or a hardware row that evidence was checked as well. Findings from `42-REVIEW.md` that moved a mitigation (all criticals and warnings fixed per `42-REVIEW-FIX.md`) were followed to the current code, not taken from the fix report.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| byos device report -> registry | Device-supplied X-Fw-Version / X-Ota-Result enter `device_report.json` (plan 01, 07) | Version strings and result tokens; attacker-influenced, bearer-authenticated |
| CI manifest/image -> registry | Release metadata and image bytes from the deploy import (plan 01, 15) | Signed firmware image, manifest (sha256, size, notes) |
| companion operator -> registry | Schedule/cancel requests from the browser (plan 01, 09, 14) | Version string, confirm flag; authenticated session |
| VPS response -> device | Offer fields arrive from the network and may come from a compromised VPS (plan 02, 08) | version, url, sha256, size |
| downloaded image -> device flash | Image header and bytes are untrusted until the signature verifies (plan 02, 08) | Firmware image |
| build machine -> signed image | Private key must never be on a build machine or the VPS (plan 03, 11, 12) | RSA-3072 signing key |
| sdkconfig -> bootloader/eFuse | A wrong option could burn eFuses irreversibly (plan 03, 16) | Kconfig options |
| build-time generator -> firmware flash | Committed mask data compiled into the image (plan 04) | Mask headers |
| CI runner -> production host TLS | Network fetch of the served chain (plan 05) | Certificate chain |
| developer shell -> device secret partition | Credentials entered once over USB (plan 06) | Wi-Fi SSID/password, api base, enrolment secret |
| release image -> GitHub / VPS / backups | Images must carry no credentials (plan 06, 11) | Firmware image |
| device -> byos, internet -> /fw/ | Telemetry headers and unauthenticated path requests (plan 07) | Headers, URL path |
| registry/device report -> HTML | CI notes and device-reported versions rendered to the operator (plan 09) | Untrusted strings in HTML |
| browser -> companion POST | Operator-initiated state change that eventually flashes the frame (plan 14) | Form POST |
| device report -> notifications, server -> push topic | Device-reported versions appear in push text; outbound HTTPS to the topic (plan 10) | Version string, topic URL |
| git tag push -> signing job, GitHub secret -> runner | Who can cause a signature; key on an ephemeral runner (plan 11, 12) | Tag, signing key |
| GitHub Releases -> CI runner -> VPS, root activate.sh -> service user | Signed images in transit; privilege boundary on the VPS (plan 15) | Images, manifests, tar stream |
| developer bench -> device flash/eFuse, captures -> repository | Physical USB access; logs may hold credentials (plan 16) | Serial captures, eFuse summary |

---

## Threat Register

Evidence paths are relative to the repository root. `reg` = `server/firmware_registry.py`, `byos` = `stub-server/byos_server.py`, `fw` = `firmware/main`.

| Threat ID | Category | Component | Severity | Disposition | Mitigation (verified evidence) | Status |
|-----------|----------|-----------|----------|-------------|--------------------------------|--------|
| T-42-01 | Tampering | publish_release | high | mitigate | Recomputes SHA-256 and size of the file bytes and raises on mismatch (`reg:554-562`); version, sha, size checked by anchored regexes and caps (`reg:59-72`, `:524-537`); a version cannot be re-bound to another sha (`reg:569-575`); an image already on disk is re-hashed and rewritten if wrong (`reg:576-589`). Tests: `test_publish_release_rejects_hash_mismatch`, `..._size_mismatch`, `..._different_sha_same_version` | closed |
| T-42-02 | Tampering | firmware_image_path | high | mitigate | Path built only from a `SHA256_HEX_RE` match, otherwise None (`reg:134-141`); byos route regex `\A/fw/([0-9a-f]{64})\.bin\Z` (`byos:494`). Tests: `test_publish_release_rejects_bad_sha256_shape`, `test_fw_route_404_for_malformed_or_unregistered_paths` | closed |
| T-42-03 | Tampering | registry.json concurrent writers | medium | mitigate | `registry_lock` delegates to `atomic_io.exclusive_lock` (`reg:123-131`); writes use `atomic_io.atomic_write` (`reg:375-377`); publish, schedule, cancel and apply_reconcile each run inside `with registry_lock` (`reg:566`, `:607`, `:644`, `:819`); byos takes the same lock first (`byos:730`). Helpers are the Phase 36 ones (`server/atomic_io.py:151`, `:174`) | closed |
| T-42-04 | Denial of Service | reconcile / load_device_report | medium | mitigate | Readers are tolerant and never raise (`reg:305-324`, `:442-454`); events processed once via `reconciled_seq` (`reg:696-703`, `:751-810`); events capped at 50 (`reg:91`, `:422`), notes at 60 x 200 chars (`reg:552`). Writer-side loader moves a corrupt file aside and raises `RegistryCorruptError` instead of wiping it (`reg:339-372`) | closed |
| T-42-05 | Elevation of Privilege | downgrade below floor | high | mitigate | `schedule_release` returns `below_floor` (`reg:612-613`); `compute_offer` re-checks the floor and the reporting device's own floor (`reg:679-680`, `:693`). Test: `test_schedule_release_below_floor` | closed |
| T-42-06 | Tampering | downgrade within allowed range | low | accept | Accepted, see AR-42-01 | closed |
| T-42-07 | Repudiation | outcome history | low | accept | Accepted, see AR-42-02. Supporting fact: `firmware` is in the nightly backup allow-list (`deploy/backup/skypane_backup.py:46-50`) | closed |
| T-42-08 | Tampering | offer fields | high | mitigate | `parse_fw_offer` gates version (`fp_fw_version_valid`), url (`fp_url_valid(..., false)`), sha256 (`fp_image_hash_valid`) and size (`fp_fw_size_parse`); any failure logs the field and yields no offer (`fw/api_client.c:508-553`, url check `:532`; `fw/validate.c:27`, `:51`, `:84`, `:104`). Size ceiling `FP_FW_MAX_IMAGE_BYTES` = 0x250000 = one OTA slot (`fw/validate.h:31`, `firmware/partitions.csv`). Host test `firmware/tests/test_validate.c` passes | closed |
| T-42-09 | Elevation of Privilege | downgrade below floor by compromised VPS | high | mitigate | `fp_ota_decide` refuses offers below the compiled floor (`fw/ota_policy.c:108-110`); `fp_ota_image_check` re-checks the signed descriptor version against the floor and the offer (`fw/ota_policy.c:119-137`, called at `fw/ota.c:79-81`) before any byte is written. Host test `test_ota_policy.c` passes | closed |
| T-42-10 | Denial of Service | battery drain from update attempts | medium | mitigate | `battery_mv <= FP_OTA_MIN_BATTERY_MV` (3500) refuses, including the unknown-battery 0 sentinel (`fw/ota_policy.c:105-107`, `fw/ota_policy.h:25`); the server also withholds offers while battery-low is active (`reg:669-670`) | closed |
| T-42-11 | Spoofing | result token injection into telemetry | low | mitigate | `fp_ota_result_format` emits only the fixed token set and only for a version that passes `fp_fw_version_valid` (no `;`) (`fw/ota_policy.c:161-205`); byos re-validates with an anchored regex and 64-byte cap (`byos:610-614`, `:636-646`) | closed |
| T-42-12 | Elevation of Privilege | eFuse-burning Kconfig | critical | mitigate | `check_production_config.sh` static mode scans defaults, ee02 and dev files for SECURE_BOOT, SECURE_FLASH_ENC, FLASH_ENCRYPTION, NVS_ENCRYPTION, ANTI_ROLLBACK, BUILD_SIGNED_BINARIES, EFUSE_VIRTUAL (`firmware/tests/check_production_config.sh:60-70`); built mode asserts each resolved `# ... is not set` (`:151-168`), run in the release workflow (`.github/workflows/firmware-release.yml:99`). Static mode PASSES on the tree; a mutation (appending `CONFIG_SECURE_BOOT=y` to a temp copy of `sdkconfig.dev.defaults`) makes it FAIL. Local `firmware/build-ee02/sdkconfig` resolves all of them unset. Hardware: eFuse before/after identical (H42-12) | closed |
| T-42-13 | Information Disclosure | signing key handling | critical | mitigate | `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES` off (`firmware/sdkconfig.defaults:39`, asserted by the guard). Key lives only as the `FW_SIGNING_KEY` secret of the `firmware-signing` environment: read-only GitHub API check today shows required reviewer `florianlepont`, custom deployment policy, only rule `fw-v*` type tag, secret `FW_SIGNING_KEY` present. `git grep` finds no private key material in tracked files. `~/skypane-signing` holds only the gpg-encrypted backup and the public key. Human-only procedure in `firmware/SIGNING.md` | closed |
| T-42-14 | Spoofing | release version string | medium | mitigate | Release mode requires HEAD to carry exactly the tag on a clean tree (`firmware/build.sh:105-116`); untagged builds use `git describe --match 'fw-v*' --always --dirty`, plus `-dev` and fault suffixes, so a dirty or later commit never prints a bare tag (`firmware/build.sh:123-131`). The tag is also re-validated in the `guard` job (`firmware-release.yml:59-70`). Signature verification remains the real gate | closed |
| T-42-15 | Tampering | unverified research assumption on Kconfig | high | mitigate | Resolved chain re-checked in the pinned container (recorded in `42-03-SUMMARY.md` and `firmware/SIGNING.md`); the built-mode guard asserts `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y` in the resolved sdkconfig on every release build (`check_production_config.sh:151-168`); local build-ee02 sdkconfig shows the full chain. Hardware: unsigned, tampered and wrong-key images refused (H42-08, H42-09a, H42-09b) | closed |
| T-42-16 | Tampering | hand-edited mask header | medium | mitigate | Byte-for-byte drift test `test_updating_screen_mask_header_matches_generator_output` (`server/test_updating_screen_mask.py:54`). CI on `85faa81d` is green (Linux with libraqm). Run locally on macOS the test fails on a same-size pixel drift, as does the pre-existing fault-mask test, which is the known missing-libraqm gap the test's own message describes; this is not a mitigation gap | closed |
| T-42-17 | Denial of Service | out-of-bounds mask stamp | medium | mitigate | `_Static_assert` bounds against the 1200x1600 screen (`fw/updating_screen.c:12-15`, `fw/fault_screen.c:15-18`); host suite `firmware/tests/test_updating_screen.c` passes (13/13 firmware suites pass locally) | closed |
| T-42-18 | Tampering | regression of NO CONNECTION output during refactor | low | mitigate | Golden digest `FP_FAULT_SCREEN_GOLDEN_DIGEST` asserted over the full render (`firmware/tests/test_fault_screen.c:195-202`); suite passes | closed |
| T-42-19 | Denial of Service | frame loses TLS after a CA change | medium | mitigate | Daily 06:17 UTC chain guard plus push and dispatch triggers (`.github/workflows/firmware-chain-check.yml:17`) fails with an actionable message naming `firmware/main/certs` and the signed-release remedy. Run 36578611110 green (H42-05, `hardware/logs/phase42/H42-05-chain-guard.txt`) | closed |
| T-42-20 | Tampering | command injection through host name | medium | mitigate | Host must match `_HOST_RE` before any subprocess call (`scripts/check_cert_chain.py:24`, `:45`); every `subprocess.run` takes an argument list and no call uses `shell=True`. Test: `test_fetch_rejects_a_malformed_host_name_before_touching_the_network` (`deploy/tests/test_cert_chain_check.py:182`). Workflow passes the host via `env:` | closed |
| T-42-21 | Information Disclosure | production host name in the workflow | low | accept | Accepted, see AR-42-03 | closed |
| T-42-22 | Spoofing | partial-chain acceptance | medium | mitigate | `openssl verify -x509_strict -CAfile <roots>` with no `-partial_chain` anywhere in the script (`scripts/check_cert_chain.py:121-125`). Test: `test_chain_under_a_foreign_root_fails_with_named_reason` (`deploy/tests/test_cert_chain_check.py:149`) | closed |
| T-42-23 | Information Disclosure | Wi-Fi password in published images | high | mitigate | No credential Kconfig symbol exists (`fw/Kconfig.projbuild`, `sdkconfig.*defaults`); the built sdkconfig has none; credentials load only from the `secret` NVS partition (`fw/creds.c`, `fw/enrol_secret.c:47-`, `fw/wifi.c:163-172`). `git grep` finds no `secrets.h` or credential macro in firmware sources (also `42-VERIFICATION.md` SC6). Hardware: the CI-built `fw-v1.0.0` joined Wi-Fi after `provision.sh` (H42-03, H42-04) | closed |
| T-42-24 | Information Disclosure | provision.sh output and shell history | medium | mitigate | Password from `SKYPANE_WIFI_PASS` or a `stty -echo` prompt, never argv (`firmware/provision.sh:328-342`); `--dry-run` redacts it (`:451`); working directory is `umask 077` and removed by `trap 'rm -rf "${WORK}"' EXIT INT TERM` (`:423-425`); `unset WIFI_PASS` after the CSV is written | closed |
| T-42-25 | Information Disclosure | plaintext credentials in NVS | low | accept | Accepted, see AR-42-04 | closed |
| T-42-26 | Denial of Service | missing/invalid credentials after provisioning mistakes | low | mitigate | `fp_device_creds_load` returns `FP_ERR_CONFIG` before any radio activity (`fw/enrol_secret.c:47-`, `fw/wifi.c:163-172`); `fp_poll_once` maps it to step `config` and the wake takes the normal failure and backoff path (`fw/state_machine.c:110-121`); `provision.sh` validators mirror the device rules (`:198-256`) | closed |
| T-42-27 | Tampering | http API base on a production build | medium | mitigate | `api_base_get` calls `fp_url_valid(out, cap, s_allow_http)` where `s_allow_http` is false unless `CONFIG_SKYPANE_ALLOW_HTTP` (`fw/api_client.c:43-46`, `:210-218`); the option is guarded off in prod defaults and unset in the built sdkconfig; `provision.sh` refuses `http://` without `--allow-http-base` (`:258-275`) | closed |
| T-42-28 | Tampering | X-Ota-Result / X-Fw-Version injection into state | medium | mitigate | Anchored regexes and 64-byte cap (`byos:603`, `:610-614`, `:626-646`); recording happens only after `bearer_ok()` (`byos:958-960`, call at `:989-995`); events capped at 50 (`byos:619`, `:807`). Tests: `test_malformed_ota_headers_are_ignored`, `test_unauthenticated_request_records_nothing_and_401` | closed |
| T-42-29 | Information Disclosure | path traversal via /fw/ | high | mitigate | Anchored regex on the raw path (`byos:494`, `:1048-1050`), registry membership check (`byos:1061-1065`), `firmware_image_path` (`byos:1066`), `stat.S_ISREG` check (`byos:1071`). Tests: `test_fw_route_404_for_malformed_or_unregistered_paths`, `test_fw_route_404_when_registered_image_file_is_missing` | closed |
| T-42-30 | Denial of Service | large file serving | medium | mitigate | `st_size > MAX_IMAGE_BYTES` returns 404 (`byos:1071`); chunked 64 KiB streaming (`byos:497`, `:1082-1086`). Test: `test_fw_route_never_serves_a_file_larger_than_max_image_bytes` | closed |
| T-42-31 | Spoofing | forged "installed" report | low | accept | Accepted, see AR-42-05 | closed |
| T-42-32 | Tampering | race between Cancel and a served offer | low | accept | Accepted, see AR-42-06. The review's SRV-CR-02 made the race narrower than the accepted text: byos now decides under `registry_lock` (`byos:730`) | closed |
| T-42-33 | Information Disclosure | firmware image readable without auth | low | accept | Accepted, see AR-42-07 | closed |
| T-42-34 | Tampering | malicious image from a compromised VPS | critical | mitigate | Only `esp_https_ota_finish` switches the boot partition, after descriptor, size and read-back SHA-256 checks (`fw/ota.c:79-89`, `:108-114`, `:117-169`, `:175`); signature enforced by `CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT` against the key in the running signed image (`sdkconfig.defaults:36-38`). USB flashing refuses an unsigned image (`firmware/flash.sh:94-121`). Hardware: unsigned refused at `step=finish` `ESP_ERR_OTA_VALIDATE_FAILED` (H42-08), tampered refused (H42-09a), wrong key refused with "image valid, signature bad" (H42-09b); all three ended in Failed after 3 attempts with the device still on `fw-v1.0.1` | closed |
| T-42-35 | Spoofing | TLS interception of the download | high | mitigate | `.crt_bundle_attach = esp_crt_bundle_attach` (`fw/ota.c:50`); custom ISRG-only bundle, guard asserts exactly two PEMs with pinned fingerprints (`check_production_config.sh:29-30`, `:108-122`); offer URL is https-only (`fw/api_client.c:532`, `allow_http=false`) | closed |
| T-42-36 | Elevation of Privilege | downgrade below floor | high | mitigate | `fp_ota_image_check(desc.project_name, desc.version, offer->version, CONFIG_SKYPANE_OTA_FLOOR_VERSION)` on the signed descriptor before download (`fw/ota.c:79-89`); `CONFIG_SKYPANE_OTA_FLOOR_VERSION` defaults to `fw-v1.0.0` (`fw/Kconfig.projbuild:34-36`) and is set in the built sdkconfig | closed |
| T-42-37 | Denial of Service | endless or oversized download | medium | mitigate | Size bound from the offer, capped at one OTA slot (`fw/validate.c:104`, `fw/validate.h:31`); `fp_wake_checkpoint()` after every `perform` iteration and every hash chunk (`fw/ota.c:98-101`, `:150`); `fp_ota_mark_try` before the attempt so a deadline exit is reported as interrupted (`fw/state_machine.c:201`) | closed |
| T-42-38 | Denial of Service | healthy update rolled back by deep sleep | medium | mitigate | `fp_ota_confirm_if_pending()` exists (`fw/ota.c:284-302`) and is called by `app_main` (see T-42-55) | closed |
| T-42-39 | Elevation of Privilege | eFuse change from firmware | critical | mitigate | No eFuse, secure-boot or flash-encryption API is called anywhere under `firmware/main` (grep for `efuse`, `esp_efuse`, `esp_secure_boot`, `esp_flash_encryption`, `esp_hmac` finds only the `FP_RST_EFUSE` reset-reason enum in `reset_reason.[ch]` and unrelated comment matches). Hardware: no fuse changed (H42-02 vs H42-12) | closed |
| T-42-40 | Tampering (XSS) | notes / versions in the page | medium | mitigate | Every dynamic value goes through `escape_html`, which is `html.escape(quote=True)` (`companion/ui_base.py:782-791`; uses throughout `companion/pages/update_page.py`, notes at `:328-350`). Tests inject `<script>alert(1)</script>` into notes and versions and assert only `&lt;script&gt;` appears (`companion/test_update_page.py:398-402`, `:598-603`; `companion/test_update_actions.py:238`) | closed |
| T-42-41 | Elevation of Privilege | /update without login | high | mitigate | `GET /update`, `POST /update/install`, `POST /update/cancel` are route-table entries with `auth_required=True` (`companion/routes.py:113-114`, `:182-187`); `_dispatch` runs `require_session()` for them (`companion/app.py:929`). Tests: `test_get_update_without_a_session_redirects_to_login` (`companion/test_update_page.py:638`), `test_both_routes_without_a_session_redirect_to_login` (`companion/test_update_actions.py:309`) | closed |
| T-42-42 | Information Disclosure | firmware versions | low | accept | Accepted, see AR-42-08 | closed |
| T-42-43 | Information Disclosure | topic URL in logs | medium | mitigate | Reuses `notify.send_notification`, which logs only the exception type and never the URL (`server/notify.py:114-135`); `_reconcile_firmware` logs only `type(exc).__name__` (`server/poll_cycle.py:403-407`) | closed |
| T-42-44 | Denial of Service | reconcile failure breaks polling | medium | mitigate | Step wrapped in `except Exception`, logs type, returns (`server/poll_cycle.py:390-407`), called from the poll cycle before the hold decision (`server/poll_cycle.py:1618`). Test: `test_reconcile_raising_does_not_break_the_cycle` (`server/test_firmware_reconcile.py:243`) | closed |
| T-42-45 | Spoofing | notification text injection via version string | low | mitigate | Versions pass the byos regex before storage (`byos:603`, `:610-614`); body is a fixed template with one `%s` (`server/notify.py:40-41`, used at `server/poll_cycle.py:421-423`) | closed |
| T-42-46 | Repudiation | duplicate or lost notifications | low | mitigate | `reconcile` advances `reconciled_seq` past every event it has seen and skips seq <= it (`reg:731`, `:751-756`, `:810`); `apply_reconcile` saves only when it moved (`reg:823`). Tests: `test_reconcile_replay_produces_no_new_notification` (`server/test_firmware_registry.py:747`), `test_installed_result_updates_registry_and_sends_one_notification`, `test_third_counted_failure_marks_failed_and_notifies_once` | closed |
| T-42-47 | Elevation of Privilege | signing arbitrary code via a tag on an unreviewed branch | critical | mitigate | Separate `guard` job with no environment checks tag shape and `git merge-base --is-ancestor "$GITHUB_SHA" origin/main` (`firmware-release.yml:27-70`); signing job `needs: guard` and declares `environment: firmware-signing` (`:72-77`). Live read-only GitHub API: that environment has required reviewer `florianlepont` and a deployment policy limited to tag pattern `fw-v*`. Run 36575555701 (H42-01) went guard then gated signing | closed |
| T-42-48 | Information Disclosure | key leakage in logs or workspace | critical | mitigate | Key reaches the step only through `env: FW_SIGNING_KEY` (`firmware-release.yml:118`); `umask 077`, temp file in `$RUNNER_TEMP` outside the workspace (`:121-123`); container mount `:ro`, `--network none`, image pinned by digest (`:129-133`); `if: always()` removal step with `shred -u` (`:139-143`); both checkouts `persist-credentials: false` (`:49`, `:89`). `deploy/tests/test_ci_secrets.py` (scans all workflows, and `test_firmware_release_passes_signing_key_through_env`) passes | closed |
| T-42-49 | Tampering | wrong key in the secret | medium | mitigate | `espsecure.py verify_signature --version 2` against the committed `firmware/signing/skypane-signing-pubkey.pem` before manifest and publish (`firmware-release.yml:148-165`, ahead of the manifest step at `:167` and the release step at `:188`). H42-01: "Signature block 0 verification successful" | closed |
| T-42-50 | Tampering | release notes forged by hand | low | mitigate | Notes come from `git log --no-merges --format=%s -- firmware/` only (`scripts/fw_release_manifest.py:89-101`); workflow generates them with `--notes-md` (`firmware-release.yml:172-176`) | closed |
| T-42-51 | Information Disclosure | public release assets | low | accept | Accepted, see AR-42-09 | closed |
| T-42-SC | Tampering | package installs | low | accept | Accepted, see AR-42-10 | closed |
| T-42-52 | Information Disclosure | private key pasted into chat | high | mitigate | Plan 12 Task 2 refuses any text containing `PRIVATE KEY` and requires rotation (`42-12-PLAN.md:93`); outcome verified: `git grep` for `BEGIN ... PRIVATE KEY` matches only planning text quoting the grep pattern, no base64 key body follows any match; `firmware/signing/` holds only the public key; `42-12-SUMMARY.md` records the pasted block began `BEGIN PUBLIC KEY` | closed |
| T-42-53 | Elevation of Privilege | key usable by any workflow run | high | mitigate | Environment secret, not repository secret: live check lists `FW_SIGNING_KEY` under `firmware-signing`, required reviewer set, deployment rule `fw-v*` of type tag only | closed |
| T-42-54 | Denial of Service | key loss | medium | mitigate | gpg AES256 symmetric backup `~/skypane-signing/skypane-signing-key.pem.gpg` exists on the developer machine; `42-12-SUMMARY.md` records decryption verified once with `cmp` and an iCloud copy; procedure in `firmware/SIGNING.md`. Plaintext key confirmed absent from `~/skypane-signing` and `~/skypane-ota-session` | closed |
| T-42-55 | Denial of Service | healthy update rolled back by deferred confirm | medium | mitigate | `fp_ota_confirm_if_pending()` is the statement immediately before `enter_deep_sleep(plan.sleep_s)` on the healthy path (`fw/app_main.c:395-396`). Hardware: `fw-v1.0.1` stayed the running version over many deep-sleep wakes with no rollback event (H42-07, `hardware/logs/phase42/server-evidence.txt`) | closed |
| T-42-56 | Denial of Service | broken image kept | high | mitigate | Confirm is reached only after `fp_poll_once` returns a non-failed result; `FP_POLL_FAILED` goes to `fail_and_sleep`, and the reset, nvs, json and deadline exits never reach it (`fw/app_main.c:323-326`, `:340-342`, `:374`, `:395`); `fp_ota_should_confirm` requires pending and poll OK (`fw/ota_policy.c:156-159`). Hardware: a trial image that panics was rolled back three times and the release ended Failed with the frame still on `fw-v1.0.1` (H42-10) | closed |
| T-42-57 | Denial of Service | battery drain / brownout mid-update | medium | mitigate | Device refuses at or below 3500 mV before drawing or downloading (`fw/ota_policy.c:105-107`, decision taken at `fw/state_machine.c:178-200`); server three-attempt cap (`reg:53`, `:707-708`, `:786-788`). After a crash or reset the device backs off (`fw/app_main.c:324-326`). Design note: since PR #161 a failed in-wake attempt continues the poll as a healthy wake (`fw/state_machine.c:239-253`), so retry spacing for that case is the wake interval bounded by the server cap, not device backoff; a failed re-join still ends the wake as a failure. Retries stay bounded | closed |
| T-42-58 | Denial of Service | wake overruns | low | mitigate | Compile-time `_Static_assert` that the wake budget exceeds the worst OTA wake and the refresh spacing fits the OTA stage (`fw/wake_guard.c:33-40`); checkpoints between stages (`fw/ota.c:98-101`, `:150`; `fw/state_machine.c:203`, `:208`). Hardware: about 62 s from wake to `ota switched` | closed |
| T-42-59 | Tampering | panel and radio drawing current together | low | mitigate | `draw_updating_screen()` calls `fp_api_release()` and `fp_wifi_stop()` before `fp_panel_draw` (`fw/state_machine.c:76-87`); radio is re-joined only after the blit (`fw/state_machine.c:205-208`). FW-CR-01's netif leak is fixed so the re-join works (`fw/wifi.c:106-113`, `:249-256`); H42-00a proves stop, connect and HTTPS in one wake with no abort | closed |
| T-42-60 | Spoofing (CSRF) | /update/install, /update/cancel | high | mitigate | `_dispatch` runs `auth.post_origin_ok(self.headers)` as its first statement for every POST, before routing (`companion/app.py:922-923`); both routes are in the origin-gate test list (`companion/test_post_origin.py:111-112`); session gate follows (T-42-41) | closed |
| T-42-61 | Elevation of Privilege | scheduling without confirmation | medium | mitigate | `_handle_update_install_post` renders the confirm page and touches nothing unless `form.get("confirm") == "yes"` (`companion/app.py:1140-1194`). Test: `test_install_without_confirm_renders_confirm_page_registry_unchanged` (`companion/test_update_actions.py:110`) | closed |
| T-42-62 | Tampering | arbitrary version string | medium | mitigate | `VERSION_MAX_LEN` and `VERSION_RE` checked before anything renders it (`companion/app.py:1156-1160`); `schedule_release` checks registry membership, floor and same-as-running (`reg:609-615`); output escaped (T-42-40). Tests: `test_install_implausible_version_treated_as_unknown_never_echoed`, `test_install_confirm_yes_unknown_version_flashes_failure`, `..._below_floor_...` | closed |
| T-42-63 | Tampering | cancel after the device started | low | mitigate | `cancel_schedule` decides inside `registry_lock` from `acknowledged()` and returns `not_cancellable` once an offer or result event exists (`reg:637-654`, `:475-491`); handler shows a failure flash (`companion/app.py:1196-1210`); byos's offer decision now shares that lock (`byos:730`) | closed |
| T-42-64 | Tampering | image altered between GitHub and the VPS | high | mitigate | `publish_release` recomputes SHA-256 and size against the manifest (T-42-01); `import-dir` refuses a manifest whose version differs from its directory (`server/firmware_cli.py:160`); the device independently verifies the signature (T-42-34) | closed |
| T-42-65 | Elevation of Privilege | import running as root | high | mitigate | Import runs as `runuser -u skypane` (`deploy/activate.sh:214-215`); firmware tar stream extracted with `--no-same-owner` (`deploy/deploy.sh:60`) and re-owned `root:root`, `go-w` (`deploy/activate.sh:164-165`); symlinked images refused (`server/firmware_cli.py:101-108`, applied at `:148`, `:203`) | closed |
| T-42-66 | Elevation of Privilege | deploy without review | high | mitigate | Deploy job runs for `workflow_dispatch` only on `refs/heads/main` (`.github/workflows/ci.yml:144`), under `environment: production` (`:157-158`, live check: required reviewer `florianlepont`) and after the moved-on guard step (`:163-`) | closed |
| T-42-67 | Denial of Service | failed import breaks the running service | medium | mitigate | Import runs before the `current` swap and a non-zero exit stops activation with the previous release serving (`deploy/activate.sh:211-222`). Tests: `test_firmware_import_runs_before_swap_when_present` (records what `current` points to during import), `test_firmware_import_failure_blocks_swap_previous_release_still_current` | closed |
| T-42-68 | Information Disclosure | GH token scope | medium | mitigate | Workflow-level `permissions: contents: read` (`ci.yml:46-47`); the firmware download step gets `GH_TOKEN: ${{ github.token }}` through `env:` only (`ci.yml:221`) | closed |
| T-42-69 | Denial of Service | firmware store lost with the VPS | low | mitigate | `"firmware"` in `INCLUDE_DIRS` of the nightly backup (`deploy/backup/skypane_backup.py:46-50`); test `test_firmware_directory_archived_no_drift_lock_excluded` (`deploy/tests/test_backup.py:167`); releases also remain on GitHub Releases | closed |
| T-42-70 | Elevation of Privilege | accidental eFuse burn | critical | mitigate | Hardware session ran only `espefuse.py summary`; `hardware/logs/phase42/efuse-before.txt` and `efuse-after.txt` are identical (H42-02, H42-12; BRINGUP-LOG "OTA hardware session"). Repo side: T-42-12 and T-42-39 | closed |
| T-42-71 | Information Disclosure | secrets in serial captures | high | mitigate | Re-scanned `hardware/logs/phase42/`: no 64-hex string, no `Authorization` or bearer text, no password, no `PRIVATE KEY`, no LAN address. Only the device's own station MAC (also recorded in BRINGUP-LOG "Measured facts") and `WPA2-PSK` mode strings appear | closed |
| T-42-72 | Information Disclosure | offline key used for bench signing | high | mitigate | Recipe in BRINGUP-LOG "Signing with the offline key" decrypts to a `umask 077` temp dir, signs in a `--network none` digest-pinned container, `rm -P` on exit trap; H42-09a records "no key left behind, verified"; today no plaintext key exists under `~/skypane-signing` or `~/skypane-ota-session`. `42-16-SUMMARY.md` Threat Flags: mitigations held | closed |
| T-42-73 | Tampering | bench images polluting the release list | low | accept | Accepted, see AR-42-11. Supporting fact: bench releases carry `"bench": true` (`reg:593`) and bench versions must carry a suffix (`reg:525`) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `block_on: high` count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Hardware evidence used (real device, 2026-09-29)

| Row | Threats it corroborates | Result |
|-----|-------------------------|--------|
| H42-00a | T-42-59, T-42-34 | Stop Wi-Fi, draw UPDATING, reconnect, HTTPS download, signature verified, restart in one wake; no assert |
| H42-01 | T-42-47, T-42-49, T-42-50, T-42-64 | Gated release run; signature verifies with the committed public key; import on the VPS |
| H42-02 / H42-12 | T-42-12, T-42-39, T-42-70 | eFuse summary before and after identical |
| H42-05 | T-42-19, T-42-22 | Chain guard run green |
| H42-07 | T-42-55 | Confirmed trial image survives deep sleep |
| H42-08 / H42-09a / H42-09b | T-42-15, T-42-34 | Unsigned, tampered and wrong-key images refused at `finish`; Failed after 3 attempts |
| H42-10 | T-42-56, T-42-57 | Panicking trial image rolled back; Failed after 3 attempts |
| H42-11 | T-42-56 | Erased otadata boots factory; install from factory works |

Two rows are recorded by the phase itself as not fully observed (UPDATING screen with the display off, failure push not seen by a human); neither is a security mitigation in this register.

---

## Accepted Risks Log

The rationale is the plan's own text. The plan register is the accepted-by record: every entry below was decided in the named plan's `<threat_model>` and executed under the single-operator workflow. It is re-logged here as required, dated the audit date.

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-42-01 | T-42-06 | Voluntary downgrade is a feature (D-06); only the authenticated operator can schedule, and the floor still applies. | Plan 42-01 (plan-time), logged by audit | 2026-09-29 |
| AR-42-02 | T-42-07 | `installed_at` and `last_outcome` are kept in the registry and backed up nightly; single-operator system, so repudiation has no second party. | Plan 42-01 (plan-time), logged by audit | 2026-09-29 |
| AR-42-03 | T-42-21 | The production host name is already public (it is a TLS endpoint); it lives in a secret only to avoid hard-coding it. | Plan 42-05 (plan-time), logged by audit | 2026-09-29 |
| AR-42-04 | T-42-25 | Plaintext credentials in NVS carry the same exposure as today's compiled-in flash copy; NVS encryption is rejected by D-A1 because it burns an eFuse. | Plan 42-06 (plan-time), logged by audit | 2026-09-29 |
| AR-42-05 | T-42-31 | A forged "installed" report needs the device bearer token; worst case it marks a release installed in the UI, and the running version shown is still the device's own X-Fw-Version. | Plan 42-07 (plan-time), logged by audit | 2026-09-29 |
| AR-42-06 | T-42-32 | The offered event is written before the response; a cancel landing in the same millisecond may still see the device install. The outcome is still recorded and visible. (Narrowed further by the SRV-CR-02 fix.) | Plan 42-07 (plan-time), logged by audit | 2026-09-29 |
| AR-42-07 | T-42-33 | Firmware images are signed and credential-free (plan 06), so serving them without auth exposes nothing secret; same exposure as `/img/`. | Plan 42-07 (plan-time), logged by audit | 2026-09-29 |
| AR-42-08 | T-42-42 | Firmware versions are not secret and the page sits behind the operator login. | Plan 42-09 (plan-time), logged by audit | 2026-09-29 |
| AR-42-09 | T-42-51 | Public release assets hold no credentials after plan 06, and firmware is not secret. | Plan 42-11 (plan-time), logged by audit | 2026-09-29 |
| AR-42-10 | T-42-SC | No new packages are installed; `espsecure.py` ships in the pinned `espressif/idf:v5.3.1` image (RESEARCH Package Legitimacy Audit: not applicable). | Plan 42-11 (plan-time), logged by audit | 2026-09-29 |
| AR-42-11 | T-42-73 | Bench entries are marked bench with a generated note; every release is kept (D-18). | Plan 42-16 (plan-time), logged by audit | 2026-09-29 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Flags

None. Only `42-16-SUMMARY.md` has a `## Threat Flags` section, and it reads "None" (T-42-70, T-42-71, T-42-72 held). The other summaries mention threats only to confirm delivery (`42-02-SUMMARY.md`, `42-08-SUMMARY.md`).

## Review Linkage and Residual Notes

`42-REVIEW.md` findings that touched a registered mitigation, and where each now sits (all fixed and re-verified in the code above):

| Review finding | Threat | Where verified |
|----------------|--------|----------------|
| SRV-CR-02 (cancel races byos) | T-42-32, T-42-63 | `byos:730` takes `registry_lock` first |
| SRV-CR-01 (same-sha deploy drops firmware), SRV-WR-04 | T-42-64, T-42-67 | `deploy/activate.sh:143-166`, `:211-222`; `server/firmware_cli.py:117-`; `ci.yml:207-237` |
| SRV-WR-02, SRV-WR-03 | T-42-47, T-42-48 | separate `guard` job, digest pin, `--network none`, `persist-credentials: false` |
| FW-WR-06 | T-42-34 | `firmware/flash.sh:94-121` |
| FW-WR-07 | T-42-26, T-42-27 | `firmware/provision.sh:198-256`, `:258-275` |
| FW-WR-08 | T-42-12 | `check_production_config.sh:60-70`, `:151-168` |
| FW-CR-01 | T-42-59 | `fw/wifi.c:106-113`, `:249-256` |

Residual notes that do not change a status (nothing here is a register threat, none is blocking):

- **Resent X-Ota-Result over-counts (SRV-WR-01).** Left as designed: identical results count as attempts, so a release can fail one attempt early after a lost response. Recorded in `42-REVIEW-FIX.md` as the safe side; a device-side attempt counter is a protocol follow-up.
- **Guard job lives in the tagged workflow file (SRV-WR-02).** The ancestor check cannot stop someone who can push a `fw-v*` tag from editing the workflow; the real controls are the environment's required reviewer and its tag-only deployment rule, both confirmed live today. A repository ruleset limiting who may create `fw-v*` tags was not checked and is not part of the declared mitigations.
- **`provision.sh --dry-run` prints the generated enrolment secret (FW-IN-05, info, not fixed).** The dry-run secret belongs to no device. T-42-24 covers the Wi-Fi password, which is redacted.
- **Chain guard checks trust, not host name (SRV-IN-07, info, not fixed).** The guard is a CA-change tripwire, not a boundary.
- **In-wake OTA failure no longer triggers device backoff** after PR #161 (see T-42-57).

## Verification Performed by This Audit

- `sh firmware/tests/check_production_config.sh static`: PASS. The same script fails on a temp copy with `CONFIG_SECURE_BOOT=y` appended to `sdkconfig.dev.defaults` (repo untouched).
- `sh firmware/tests/run_host_tests.sh`: 13 suites pass.
- pytest, 234 tests across `stub-server/test_ota_offer.py`, `server/test_firmware_registry.py`, `server/test_firmware_reconcile.py`, `server/test_firmware_cli.py`, `deploy/tests/test_ci_secrets.py`, `deploy/tests/test_cert_chain_check.py`, `companion/test_update_actions.py`, `companion/test_update_page.py`: pass. `companion/test_post_origin.py`, `deploy/tests/test_release_manifest.py`, `deploy/tests/test_backup.py`: pass.
- `server/test_updating_screen_mask.py` fails on this macOS host only (same byte count, pixel drift without libraqm, same as `test_fault_screen_mask.py`); CI on `85faa81d` is green on Linux.
- Read-only GitHub API: environments `firmware-signing` and `production` (required reviewer, tag rule), secret name list. No write call was made.
- No implementation file was modified.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-29 | 74 | 74 | 0 | gsd-security-auditor (Claude), ASVS L1, block_on high |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-29
