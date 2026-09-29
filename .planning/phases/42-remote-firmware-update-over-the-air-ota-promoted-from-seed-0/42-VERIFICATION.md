---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
verified: 2026-09-29T00:00:00Z
status: passed
score: 6/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: false
gaps: []
human_verification:

  - test: "Trigger one more update while the display is OFF (or inside quiet hours) and watch the glass"
    expected: "The UPDATING screen is drawn before the download, then the next normal poll redraws what the mode calls for (hold screen when display is off)"
    why_human: "H42-11 proved an OTA runs with the display off (offered 17:42:13, trial 17:43:50, installed 17:44:52) but the developer did not look at the glass, and no serial capture exists. The code path has no mode gate (draw_updating_screen() runs unconditionally in the FP_OTA_START branch of state_machine.c), but D-14 says 'always, at night and with the display off', and only a look at the panel proves it."

  - test: "After a third failed attempt, confirm the failure push arrived on the phone in English or French"
    expected: "'Update failed, back on fw-v1.0.1' (or the French text), sent through the configured topic"
    why_human: "H42-08/09a/09b/10 each reached 'failed after 3 attempts' on the server, and the poll journal shows no notification error, but the developer never saw the failure push. The success push was seen (H42-00a, H42-06), which proves the topic and sender; the failure body/route is proven only by host tests."
deferred: []
---

# Phase 42: Remote firmware update over the air (OTA) Verification Report

**Phase Goal:** A firmware release reaches the frame on the wall without a USB cable. The server offers it, the device downloads it into the inactive slot, boots it on trial and keeps it only after a successful poll, and a bad image rolls back on its own.
**Verified:** 2026-09-29
**Status:** human_needed
**Re-verification:** No, initial verification

The goal is achieved. A signed release went from a git tag, through the gated pipeline and the VPS store, onto the real frame twice (`fw-v1.0.0` by USB, `fw-v1.0.1` over the air). Unsigned, tampered, wrongly signed and crashing images were all refused or rolled back, and three of those runs ended in a "failed" release with the frame still on the previous image. No eFuse changed. Two smaller observations were never made by a human (see Human Verification), and both are recorded in the session as "not observed".

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The offer is in `/device/v1/display` only for a scheduled release that differs from `X-Fw-Version`, is at or above the floor, and the battery-low alert is off; quiet hours and display off do not hold it | VERIFIED | `server/firmware_registry.py:compute_offer` takes no quiet-hours or display-off parameter, and checks battery, schedule, same-version, floor, reporting-device floor, and failure count. byos serves it under `registry_lock` then `_device_report_lock` (`stub-server/byos_server.py:730`). `stub-server/test_ota_offer.py` and `server/test_firmware_registry.py` pass (172 tests run here). Hardware: an offer was served with the display OFF (H42-11) |
| 2 | Device downloads with `esp_https_ota` over the existing trust store into the inactive slot, checks size and SHA-256, accepts only an image signed with the project key; no eFuse burned | VERIFIED | `firmware/main/ota.c`: `esp_https_ota_begin/perform/finish` with `esp_crt_bundle_attach`, image-length check against `offer->size`, read-back hash. `sdkconfig.defaults` has `SECURE_SIGNED_APPS_NO_SECURE_BOOT`, `SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT`, RSA scheme. Hardware: signed `fw-v1.0.1` installed (H42-06); unsigned refused at `step=finish` `ESP_ERR_OTA_VALIDATE_FAILED` (H42-08); tampered refused (H42-09a); wrong-key refused, "image valid, signature bad" (H42-09b); eFuse before/after byte-identical, no `burn_*` run (H42-02, H42-12) |
| 3 | Rollback enabled; a new image confirms itself after its first successful poll and before that wake's deep sleep; a forced crash on a trial image rolls back on real hardware | VERIFIED (capture gaps noted) | `sdkconfig.defaults:22` `BOOTLOADER_APP_ROLLBACK_ENABLE=y`. `app_main.c:395` calls `fp_ota_confirm_if_pending()` after `poll ok` and immediately before `enter_deep_sleep`; every failure exit precedes it. Hardware: the ordering line was not captured on serial (H42-06 had USB unplugged), but H42-07 is behavioural proof: had confirmation been missed, the bootloader would have rolled back at the next wake, yet the frame reported `fw-v1.0.1` over many deep-sleep wakes with no rollback event. Crash: `fw-v1.0.1-crash` (dev profile, `SKYPANE_FAULT=panic`, real-key signed) produced device-reported rollback events at 17:22:54, 17:29:31, 17:32:32, the companion showed the rollback banner, and the frame stayed on `fw-v1.0.1`. The panic line and `ota boot outcome=rollback` fell into the USB re-enumeration window; the rollback token is itself emitted by the device from its boot classification, so it is not inferred |
| 4 | "Updating..." screen for every update; three failed attempts mark the release failed and send a notification | UNCERTAIN (WARNING, human decision requested) | Screen seen on glass in normal mode (H42-00a, H42-06, developer). Three-attempt failure: reached four times on the server (H42-08, 09a, 09b, 10). Not seen by a human: the screen with the display off or in quiet hours (H42-11), and the failure push (sent, not seen). The success push was seen. See Human Verification |
| 5 | A git tag produces a signed release the reviewer-gated deploy copies to the VPS; the Update page shows version, state, rollback, history, and installs or cancels with confirmation | VERIFIED | H42-01: tag `fw-v1.0.0`, release run 36575555701 (guard then gated signing job), 5 assets, sha256 equals `release.json`, signature verifies with the committed public key, deploy run 36575975888 imported it (same-sha redeploy, the SRV-CR-01 case), visible in the companion with generated notes. `fw-v1.0.1` repeated it (runs 36581150646, 36581557153). Install with confirmation exercised on real hardware from the companion (H42-11). Cancel and no-JS confirmation are covered by `companion/test_update_page.py` (passes); cancel was not used on the real frame |
| 6 | Release images hold no device credentials | VERIFIED | `git grep` finds no `secrets.h`, `SKYPANE_WIFI_SSID` or `SKYPANE_API_BASE` in `firmware` sources beyond a `.gitignore` line and a comment in `sdkconfig.defaults`; credentials load from the `secret` partition via `fp_device_creds_load`. Hardware: the CI-built `fw-v1.0.0` joined Wi-Fi and polled after `provision.sh` (H42-03/04). No private key in the tree (`git grep "BEGIN .*PRIVATE KEY"` matches only planning text) |
| 7 | A CI check fails when the production chain no longer leads to a root in the trust store | VERIFIED | `scripts/check_cert_chain.py`, `.github/workflows/firmware-chain-check.yml`, offline tests in `deploy/tests/test_cert_chain_check.py`. Hardware/CI: dispatch run 36578611110 green, served chain leaf, YE2, Root YE, Root X2, Root X1 (H42-05) |

**Score:** 6/7 truths verified, 1 uncertain (human decision), 0 failed, 0 behavior-unverified.

### Requirements Coverage

Every ID OTA-01..OTA-12 is claimed by at least one PLAN (union of the `requirements:` fields of 42-01..42-16); none is orphaned.

| Requirement | Plans | Status | Evidence |
|---|---|---|---|
| OTA-01 offer gate | 01, 07 | SATISFIED | SC1 |
| OTA-02 esp_https_ota, size/SHA-256, signature before switch | 02, 08, 13, 16 | SATISFIED | SC2; H42-00a, 06, 08, 09a, 09b |
| OTA-03 rollback, confirm after one good poll | 02, 03, 08, 13, 16 | SATISFIED | SC3; H42-07, H42-10 |
| OTA-04 signed images, no eFuse, key in CI secret | 03, 11, 12, 16 | SATISFIED | SC2 and SC5; H42-02, H42-12 identical |
| OTA-05 version floor, both sides | 01, 02, 03, 08 | SATISFIED | `compute_offer` floor and reporting-device floor; firmware floor in `ota_policy.c`; host tests pass |
| OTA-06 battery refusal, attempts, three strikes | 01, 02, 07, 08, 10, 13 | SATISFIED | SC4 (failed after 3 attempts, four times on hardware) |
| OTA-07 UPDATING screen every update | 04, 13, 16 | SATISFIED for normal mode; display-off/quiet-hours unconfirmed by eye | Human Verification 1 |
| OTA-08 Update page | 07, 09, 14 | SATISFIED | SC5 (already marked Complete) |
| OTA-09 EN/FR notifications | 10 | SATISFIED for "installed"; "failed" sent but not seen | Human Verification 2 |
| OTA-10 tag to store | 01, 03, 06, 11, 15, 16 | SATISFIED | SC5, SC6; H42-01 |
| OTA-11 chain guard | 05, 16 | SATISFIED | SC7; H42-05 |
| OTA-12 one hardware session, four proofs | 16 | SATISFIED | signed install (H42-06), unsigned/tampered refused (H42-08/09a/09b), crash rollback (H42-10), factory recovery (H42-11) |

**Bookkeeping gap (not a code gap):** `.planning/REQUIREMENTS.md` still shows OTA-01..07 and OTA-09..12 unchecked and "Pending" in the traceability table; only OTA-08 is Complete. Update it when the phase is closed (OTA-07 and OTA-09 after the two human checks).

### Review fixes spot-checked in the code

| Finding | Where | Status |
|---|---|---|
| FW-CR-01 second `fp_wifi_connect()` aborts | `firmware/main/wifi.c:255-257` destroys the netif and NULLs `s_sta_netif`; `:112` guards create | Present. Proven on hardware: H42-00a cycle 01 stop, reconnect, fresh `sta ip:`, HTTPS, `ota switched`, no assert |
| SRV-CR-01 same-SHA deploy drops firmware | `deploy/activate.sh:136-146` moves `firmware-releases` to its own dir before staging, imports from it | Present. Hardware: deploy run 36575975888 "added fw-v1.0.0" on a same-sha redeploy |
| SRV-CR-02 cancel vs byos race | `stub-server/byos_server.py:730` `registry_lock` then `_device_report_lock`, registry loaded inside | Present |
| SRV-CR-03 result stamped with wrong schedule | `byos_server.py:780` `event_schedule_id = schedule_id if result_version == schedule_version else None`; `reconcile()` treats a foreign id as stale | Present |
| SRV-CR-04 lock with no recovery | `byos_server.py` floors `next_seq` against `reconciled_seq` and all event seqs; `compute_offer` withholds from a reporting device below the floor | Part (b) fully fixed. Part (a) fixed for the pre-OTA-build case only (see follow-ups) |
| PR #158 `firmware_cli --state-dir` | `server/firmware_cli.py` accepts it before and after the subcommand; test added | Present; the sheet's `FWCLI` form worked after the session correction |
| PR #159 `flash.sh` refuses unsigned images | `firmware/flash.sh:105-125` verifies with `espsecure.py verify_signature` in both profiles, exits 1 otherwise | Present. It was found by the session (unsigned image boot-loops with `secure_boot_v2: No signatures were found`) |

### Behavioral Spot-Checks and Probes

| Behavior | Command | Result | Status |
|---|---|---|---|
| Firmware pure-logic suites (OTA policy, updating screen, wake deadline, panel guard, and so on) | `sh firmware/tests/run_host_tests.sh` | 13 suites, all pass | PASS |
| Registry, CLI, byos offer, Update page | `server/.venv/bin/python -m pytest server/test_firmware_registry.py server/test_firmware_cli.py stub-server/test_ota_offer.py companion/test_update_page.py` | 172 passed | PASS |
| Probes | none declared by this phase | not applicable | SKIPPED |

The full pytest suite was not re-run; the pre-existing macOS-only failures logged in `deferred-items.md` (`mv -T`, `/proc`) are sandbox limits and were not touched.

### Anti-Patterns

No `TBD`, `FIXME` or `XXX` in the source files this phase changed. No private key in the repository. No stubs found in the OTA path. The one deferred-items entry that is still relevant (the trailing `__main__` runner in `stub-server/test_ota_offer.py`) is not a goal issue.

### The "not observed" items, and whether they leave a criterion unproven

| Not observed | Effect on the criteria |
|---|---|
| H42-04 `ota boot outcome=none` on first boot | None. The server shows the first poll as `fw-v1.0.0` and the next wake polls OK |
| H42-06 `ota confirmed` before `sleep enter` on serial; battery after OTA | None for SC3. Behavioural proof by H42-07 (no rollback across many wakes); the exact ordering is also guaranteed by the code at `app_main.c:395` |
| H42-07 `reset reason=deepsleep`, `outcome=none` | None. Same proof |
| H42-08 failure push not seen | Leaves SC4 partly unproven, human item 2 |
| H42-10 panic line and `outcome=rollback` boot | None. The rollback events are emitted by the device and the companion banner showed it; only the console line is missing |
| H42-11 UPDATING screen with display off | Leaves SC4 ("every update") partly unproven, human item 1 |
| Free heap; stack high-water mark (H42-00b, FW-WR-09) | None. Not measurable without a code change; no overflow or fault in any capture, including full signature-verifying downloads. Track as a follow-up |

### Known follow-ups: gap or not

| Follow-up | Classification | Why |
|---|---|---|
| UPDATING screen stays on the glass after a refused attempt | Non-blocking follow-up | SC4 requires the screen to appear for every update, and it does. The stale screen is cleared by the next successful poll, and after the third failure the offer is withdrawn, so the next poll is a normal one. It is misleading for the wake interval or backoff (300 to 1200 s) but does not break install, refusal, rollback or recovery. Recommend fixing soon: redraw the previous frame, or an error line, when the attempt fails |
| After a panic rollback the device backs off before reporting | Non-blocking follow-up | The rollback and the three-attempt rule still work (H42-10 reached "failed"); the report arrives one backoff step (300 to 1200 s) late, so the companion banner and the counter lag. No criterion states a reporting latency. The session pressed RESET to skip waits, which hid the delay in normal use. Consider reporting the rollback before backing off |
| Update page UX: current-version badge, "Installed" column semantics, collapsible notes | Non-blocking follow-up | SC5 lists running version, state, rollback and history, and the developer saw all of them in the companion. These are presentation clarity issues, not missing data or actions |
| SRV-CR-04(a) remainder: a compatible device that never reports still leaves the schedule un-cancellable; no operator "force clear" | Non-blocking follow-up (WARNING) | Reachable only by a device that is above the floor yet ignores an offer. It did not occur in four failure modes on hardware, all of which produced result events. Worth a force-clear action or an N-offers-without-result counted attempt |
| SRV-WR-01 resend over-counting; device does not send an attempt counter | Accepted trade-off (documented in REVIEW-FIX) | Safe direction: a release may fail one attempt early and can be rescheduled |

## Human Verification Required

### 1. UPDATING screen with the display off or in quiet hours

**Test:** Turn the display off in the companion (or wait for quiet hours), schedule an install, watch the panel at the frame's next wake.
**Expected:** UPDATING appears before the download; after the install the next poll redraws the hold screen or normal view.
**Why human:** Only the panel shows it; H42-11 had no serial capture and no eyes on the glass.

### 2. Failure push on the phone

**Test:** Schedule a known-bad release (for example a stored `fw-v1.0.1-unsigned`) and let it reach three attempts.
**Expected:** A push "Update failed, back on fw-v1.0.1" (French text in French) arrives on the configured topic.
**Why human:** The phone is outside the repository; the session recorded "sent, not seen".

Both checks are cheap and can run in one sitting; neither is a code defect. They keep SC4 and the OTA-07/OTA-09 checkboxes from being fully closed.

## Gaps Summary

No gaps against the seven success criteria. Six are verified against the code and the real-device evidence; criterion 4 has two unobserved sub-claims (UPDATING with the display off, the failure push) that need a human look. The pending work is bookkeeping (`REQUIREMENTS.md` checkboxes and traceability) plus the non-blocking follow-ups above.

---

_Verified: 2026-09-29_
_Verifier: Claude (gsd-verifier)_
