---
phase: 34-firmware-resilience-power-security-cleanup
verified: 2026-09-25T16:20:00Z
status: passed
score: 5/5 success criteria verified; 15/15 requirements (FW-01..FW-15) satisfied
overrides_applied: 0
re_verification: null
warnings:
  - id: W-1
    concern: "Persistent NVS failure at boot is a panic loop with no backoff"
    detail: "app_main.c still uses ESP_ERROR_CHECK on nvs_flash_init()/nvs_open(). Both run before the abnormal-reset check, so an NVS partition that keeps failing with a code other than NO_FREE_PAGES/NEW_VERSION_FOUND panics on every boot (~0.3 s apart) and never reaches fail_and_sleep(). The radio never starts on that path, but the chip hot-loops until the battery is flat. This is outside the audit's FW-01 evidence (which named epd13in3e.c) and outside every success criterion, so it is not a blocker."
  - id: W-2
    concern: "Hardware doc cites a capture file that is not committed"
    resolved: "Fixed after verification: the H-04 and H-18 rows now cite H-05-revoke-server.log."
    detail: "PHASE34-HARDWARE-SESSION.md cites hardware/logs/phase34/H-04-vps-after-server.log for H-04 and H-18 (prod X-Fw-Version). The file is not in the repo or in git history. The production X-Fw-Version=e8d293c telemetry is still shown by H-05-revoke-server.log (6 lines), so FW-15 is proven. Only the citation is wrong."
  - id: W-3
    concern: "Host test build warning"
    resolved: "Fixed after verification: api_base.c includes <strings.h>; host tests build without the warning. Header-only change, no behaviour change against the e8d293c image tested on hardware."
    detail: "test_api_base compiles main/api_base.c with an implicit declaration of strncasecmp (missing <strings.h> under -std=c11). It is a warning with GCC 13 (the CI runner), but GCC 14+ makes it an error by default, so the host-test job will break when ubuntu-latest moves to GCC 14."
---

# Phase 34: Firmware — resilience, power, security, cleanup — Verification Report

**Phase Goal:** The frame recovers on its own from every failure the audit found (crash/brownout reset, hang, rejected token, absurd `sleep_s`), wakes for less time, reads its battery honestly and enrols with a per-device secret — all validated in ONE hardware session.
**Verified:** 2026-09-25T16:20:00Z
**Status:** passed (with 3 non-blocking warnings)
**Re-verification:** No — initial verification

Firmware under test on hardware: `e8d293c`. `git diff e8d293c HEAD -- firmware/ .github/workflows/firmware.yml` is empty, so the hardware captures apply to the current firmware tree unchanged. `stub-server/byos_server.py` changed after `e8d293c` (the Phase 35 comment purge). I checked the non-comment diff: only docstrings and comments changed, and the registry tests still pass.

## Local checks run by the verifier

| Check | Command | Result |
|---|---|---|
| Firmware host tests | `sh firmware/tests/run_host_tests.sh` | PASS — 9 suites (api_base, backoff, battery_math, fault_screen, panel_guard, reset_reason, sleep_decision, validate, wake_deadline); exit 0; one compiler warning (W-3) |
| Log Line Contract | `sh firmware/tests/check_log_contract.sh` | `log-contract: PASS` |
| Production config (source mode) | `sh firmware/tests/check_production_config.sh static` | `production-config static: PASS` |
| Stub-server tests (registry + poll cycle) | `server/.venv/bin/python -m pytest stub-server -q -p no:cacheprovider` | `33 passed` (includes the 14 `test_devices_registry.py` cases) |
| Comment-history guard | `python3 scripts/check_comment_history.py check` | exit 0 |
| Docker firmware build | not run (no Docker, as instructed) | the session doc records `production-config built: PASS` on the real build (H-01) |

## Goal Achievement — ROADMAP success criteria

| # | Success criterion | Status | Evidence (code + capture) |
|---|---|---|---|
| 1 | Simulated brownout/panic → backoff sleep, not an immediate retry; a hung wake is bounded by the global deadline | VERIFIED | Code: `app_main.c` classifies `esp_reset_reason()` with `fp_reset_is_abnormal()` (panic, int/task/other WDT, brownout, pwr_glitch, cpu_lockup) and calls `fail_and_sleep("reset")` before Wi-Fi. `fail_and_sleep()` persists `FP_NVS_BACKOFF_N` and sleeps `fp_backoff_seconds()`. `wake_guard.c` arms a one-shot `esp_timer` (`CONFIG_SKYPANE_WAKE_BUDGET_S`=300), subscribes the main task to the TWDT (`CONFIG_ESP_TASK_WDT_PANIC=y`, 60 s), and a `_Static_assert` keeps the budget above the worst legitimate wake. Captures: `H-12-fault-panic.log` has `reset reason=panic` → `poll fail step=reset backoff_n=1 sleep_s=600`, then `backoff_n=2 sleep_s=1200`. `H-13`/`H-14` have `reset reason=task_wdt` / `reset reason=int_wdt` → `step=reset`. `H-15-fault-slow_wake.log` has `wake budget of 300s exceeded` → `poll fail step=deadline` with `wake timing total_ms=300744`. Brownout was not induced (H-16 N/A), but it takes the same code branch (host-tested in `test_reset_reason.c`), so this does not block. |
| 2 | A 401 from the server leads to re-enrolment on the next wake, with no reflash | VERIFIED | Code: `fp_http_status_classify()` maps 401/403 to `FP_ERR_HTTP_AUTH`. `fp_api_get_display()` then calls `fp_nvs_erase_key(FP_NVS_DEVICE_TOKEN)`, which maps to `step=auth`. On the next wake `fp_poll_once()` sees `!fp_api_has_token()` → `fp_api_setup()` with the per-device secret. Capture `H-05-revoke.log`: `device token rejected; erased, re-enrolling on the next wake` → `poll fail step=auth backoff_n=0 sleep_s=300` → `setup accepted; device credential stored` → `poll ok`. The same recovery repeats in H-19 (`H-19-restore.log`: `step=auth`, then `setup accepted`). |
| 3 | Validation helpers and the sleep decision covered by host tests that run in CI | VERIFIED | Pure helpers: `validate.c` (hash, token, URL/scheme, `sleep_s` 1..86400, `led_enabled`, download verdict, HTTP class), `sleep_decision.c`, `reset_reason.c`, `wake_deadline.c`, `battery_math.c`. Tests: `test_validate.c` (74 asserts, including 86400 accepted and 86401 rejected), `test_sleep_decision.c`, `test_reset_reason.c`, `test_wake_deadline.c`. The runner discovers `test_*.c` automatically (9 suites run locally). CI: the `.github/workflows/firmware.yml` `host-tests` job runs `./firmware/tests/run_host_tests.sh`. The `build` job runs the static/built production-config checks and the log-contract check. |
| 4 | No-change wake duration measured before/after on real hardware (DHCP, TLS, memtest) and logged | VERIFIED | The `fp_diag wake timing total_ms=… wifi_ms=…` line and the `fp_api http connects=… first_connect_ms=… tls_offered=…` line are both in code and in the captures. Measured: no-change wake 6.34 s → 1.65 s (VPS) and 4.4 s → 1.57 s (LAN, n=53). Wi-Fi+DHCP ~3.0 s → 1.15 s. TLS connect 1938 ms → 97 ms median with resumption. `H-04-vps-after.log` shows `connects=1` on 10/10 wakes and `tls_offered=1`. Memtest: `H-12` captures the `octal_psram` init block with no `SPI SRAM memory test` line, and `CONFIG_SPIRAM_MEMTEST=n` is enforced by `check_production_config.sh`. The ~28 s per-cycle overhead is explained in `hardware/PHASE34-HARDWARE-SESSION.md`. The VPS samples are weak (before n=3, after n=2), but the LAN sample (n=53) is robust and the direction and size of the change agree across all three. |
| 5 | byos refuses to re-enrol a known MAC; each device has its own secret | VERIFIED | Code: `byos_server.py` `do_POST /device/v1/setup` loads `devices.json` fresh on each request. An unregistered MAC gets 403. A known MAC without its own secret gets 401 (`secret_matches()` uses `hmac.compare_digest` on SHA-256). Only the hash is stored. A missing or corrupt registry refuses everyone. The phase decision D-A1/D-34-01 reads "refuses re-enrolment of a known MAC by anyone not holding that MAC's secret", which is what lets SC2 self-heal. Firmware: `enrol_secret.c` reads the secret from the dedicated `secret` NVS partition (`partitions.csv` 0x13000), written by `firmware/provision.sh`. `devices_cli.py` manages the registry. Tests: `test_devices_registry.py` (14 cases, passing). Capture `H-06-curl.txt`: wrong secret → 401, unregistered MAC → 403, old shared secret → 401. |

**Score:** 5/5 success criteria verified

## Requirements Coverage

| Req | Expected (audit ledger) | Status | Evidence |
|---|---|---|---|
| FW-01 | Reset reason at boot → backoff + sleep; `epd_init` returns errors | SATISFIED | `app_main.c` reset branch (above). `epd13in3e.c` `epd_init()` returns `ESP_FAIL` on each GPIO/SPI setup failure (no `ESP_ERROR_CHECK` left in the driver). `fp_panel_draw()` propagates it as `step=blit`. H-12/13/14. See W-1 for the remaining `ESP_ERROR_CHECK` on NVS init in `app_main.c`. |
| FW-02 | Whole-wake deadline (one-shot `esp_timer`) + real WDT; comment corrected | SATISFIED | `wake_guard.c` (timer + `esp_task_wdt_add`), checkpoints in `state_machine.c` and in the download loop in `api_client.c`, `CONFIG_ESP_TASK_WDT_PANIC=y`, corrected comment in `sdkconfig.defaults`. H-13, H-15. |
| FW-03 | 401/403 clears the token; next wake re-enrols; distinct error code | SATISFIED | `FP_ERR_HTTP_AUTH` → `step=auth`. `FP_ERR_ENROL_REJECTED` → `step=enrol` for setup. H-05, H-19. |
| FW-04 | `sleep_s` capped at 86400; above → JSON error | SATISFIED | `FP_SLEEP_S_MAX 86400u`, `fp_sleep_s_parse()` rejects NaN, fractions and out-of-range values → `FP_ERR_HTTP_JSON`. Host-tested. H-09: `poll fail step=json` with `--sleep 86401`. |
| FW-05 | Unchecked returns checked and mapped to the right `step=` | SATISFIED | `small_request()` checks `esp_http_client_write` length and `fetch_headers < 0` (→ http). Download checks `fetch_headers` (→ download). `epd_blit()` checks the PON/DRF/POF busy-waits (→ blit). |
| FW-06 | Response validation, size/SHA gate and sleep decision as pure helpers with host tests | SATISFIED | `validate.c`, `sleep_decision.c`, `fp_download_verdict()`; `test_validate.c`, `test_sleep_decision.c` pass. |
| FW-07 | https-only in production; ISRG-only bundle | SATISFIED | `s_allow_http` only under `CONFIG_SKYPANE_ALLOW_HTTP` (set only in `sdkconfig.dev.defaults`). `fp_url_valid()` gates the API base, `image_url` and download. `main/certs/` holds only ISRG X1/X2, fingerprint-checked by `check_production_config.sh`. H-07: `API base URL rejected` → `step=config`. |
| FW-08 | Per-device enrolment secret; byos refuses re-enrolment of a known MAC | SATISFIED | See SC5. |
| FW-09 | `DHCP_RESTORE_LAST_IP`, no ARP check (or static IP); measured | SATISFIED | Both set in `sdkconfig.defaults` and enforced by the static check. Optional static-IP path in `wifi.c` (`SKYPANE_STATIC_*`). `wifi_ms` 3.0 s → 1.15 s measured. H-10 (static IP) was skipped, which D-34-03 explicitly allows. |
| FW-10 | One keep-alive client; TLS tickets in RTC memory; wake duration logged; overhead explained | SATISFIED | `session_client()` shares one handle across setup/display/same-origin download. `tls_session.c` uses `RTC_DATA_ATTR` blob plus origin. `fp_diag` timing line sits outside the contract. H-04 shows `connects=1` and `tls_offered=1`. Overhead explained in the session doc. |
| FW-11 | Battery read once before Wi-Fi, 8-sample average | SATISFIED | `app_main.c` calls `fp_battery_mv()` before `fp_poll_once()`. `battery.c` takes `FP_BATTERY_SAMPLES 8`, averages with `battery_math_average_mv`, and caches the result for the wake. H-17: one multimeter reading, Δ ≈ 8 mV, against a 60 mV threshold. Only 1 of the 3 pre-registered readings was taken. The code-level requirement does not depend on the reading count, so this is not a blocker. |
| FW-12 | Memtest off; shorter row wait if the datasheet allows; light sleep during the spacing wait | SATISFIED | `CONFIG_SPIRAM_MEMTEST=n`. The 800 µs row wait is kept deliberately: the datasheet gives no per-row timing, which the ledger's "if the datasheet allows" condition covers, and the reason is documented. `fp_panel_draw()` → `fp_wake_light_sleep_s()` in slices below the TWDT. H-11: `holding 26s for the panel's refresh spacing`, no TWDT line. |
| FW-13 | Use `fp_api_base_normalize` or delete; delete dead code; drop orphan symbols; rollback off | SATISFIED | `api_base_get()` calls `fp_api_base_normalize()`. `fp_api_post_logs`, `FP_PROVISION_TIMEOUT_S`, `FP_FACTORY_PREP`, `FP_API_BASE` and `FP_DEV_PROVISION_SECRET` are gone (grep finds none). The `reset` field is no longer read. `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n`. The KEY pin/hold options stay in Kconfig with no consumer; VENDOR.md documents this as deliberate, pending the button work. |
| FW-14 | One helper each (hex check, NVS open/read/close, HTTP client config) | SATISFIED | `fp_hex_lower_valid()` is the single hex check. `nvs_util.c` (`fp_nvs_get_str[_from]`/`set_str`/`erase_key`). HTTP config went from 3 sites to 2: `session_client()` for the shared handle, and `http_client_new()` only for cross-origin downloads, which deliberately get no shared headers. `app_main.c` still opens NVS directly for the u8/u32 counters (minor). |
| FW-15 | Version derived from `git describe` | SATISFIED | `build.sh`: `git describe --tags --always --dirty` → `-DPROJECT_VER`, with `-dev`/`-<fault>` suffixes. `CMakeLists.txt` falls back to `0.0.0-nogit`. Telemetry `X-Fw-Version=e8d293c` (`H-05-revoke-server.log`) and `e8d293c-dev` (`H-08-lan-dev-server.log`). |

No orphaned requirements: FW-01..FW-15 are all claimed by plans 34-01..34-11. The REQUIREMENTS.md checkboxes and the traceability rows still read "Pending", and the ROADMAP still shows 34-11 unchecked. The orchestrator should update these on phase close.

## Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| `app_main.c` | `reset_reason.c` | `fp_reset_is_abnormal(esp_reset_reason())` → `fail_and_sleep("reset")` before Wi-Fi | WIRED |
| `app_main.c` | `wake_guard.c` | `fp_wake_guard_start(on_wake_deadline)` as the 2nd statement; `on_wake_deadline` → `fail_and_sleep("deadline")` | WIRED |
| `state_machine.c` / `api_client.c` download loop | `wake_guard.c` | `fp_wake_checkpoint()` (5 sites) | WIRED |
| `api_client.c` | NVS token | `FP_ERR_HTTP_AUTH` → `fp_nvs_erase_key(FP_NVS_DEVICE_TOKEN)` → `fp_api_has_token()` false next wake → `fp_api_setup()` | WIRED |
| `fp_api_setup()` | `secret` partition | `fp_enrol_secret_load()` → `nvs_flash_init_partition("secret")` | WIRED |
| `app_main.c` | `sleep_decision.c` | `fp_sleep_decide()` on both the failure and success paths | WIRED |
| `api_client.c` | `tls_session.c` | `fp_tls_session_offer()` before the first connect, `maybe_save_tls_session()` after the first response | WIRED |
| `byos_server.py` setup | `devices.json` | `load_registry()` per request → 403/401/200 | WIRED |
| CI | host tests / config checks | `firmware.yml` `host-tests` and `build` jobs | WIRED |

## Behavioral Spot-Checks and Probe Execution

| Behavior | Command | Result | Status |
|---|---|---|---|
| Pure helpers behave (sleep_s cap, https rule, reset classification, sleep decision, deadline) | `sh firmware/tests/run_host_tests.sh` | 9/9 suites pass | PASS |
| Production config is https-only, fault-free, ISRG-only, memtest off, rollback off | `sh firmware/tests/check_production_config.sh static` | PASS | PASS |
| Contract step tokens match the code | `sh firmware/tests/check_log_contract.sh` | PASS | PASS |
| Registry refuses an unknown MAC or a wrong secret; the CLI round-trips | pytest `stub-server` | 33 passed | PASS |

No `scripts/*/tests/probe-*.sh` probes are declared for this phase.

## Hardware capture spot-checks (`grep -a`)

| Claim | File | Found |
|---|---|---|
| `reset reason=panic` → backoff doubling | `H-12-fault-panic.log` | `reset reason=panic` / `step=reset backoff_n=1 sleep_s=600`, then `backoff_n=2 sleep_s=1200` |
| `step=deadline` with total_ms in 300000–360000 | `H-15-fault-slow_wake.log` | `wake budget of 300s exceeded`, `step=deadline`, `total_ms=300744` |
| Token erased → `setup accepted` | `H-05-revoke.log` | both lines present, in that order |
| `connects=1` / `tls_offered` | `H-04-vps-after.log` | 10× `connects=1`, `tls_offered=1 tls_saved_len=1167` |
| task_wdt / int_wdt resets | `H-13`, `H-14` | `reset reason=task_wdt`, `reset reason=int_wdt` |
| sleep_s 86401 rejected | `H-09-sleep86401.log` | `poll fail step=json` |
| http base refused in prod | `H-07-http-refused.log` | `API base URL rejected (this build requires https)`, `step=config` |
| per-device secret enforcement | `H-06-curl.txt` | 401 / 403 / 401 |
| No PSRAM memtest | all captures | 0 matches for `SPI SRAM memory test`; the `octal_psram` init block is captured in H-12 |

## Hardware deviations — impact on success criteria

| Deviation | Affects | Blocks an SC? | Reason |
|---|---|---|---|
| H-10 static IP skipped | FW-09 | No | The requirement is "restore last IP, no ARP check (or static IP)". The default path is in place and measured. D-34-03 makes the static-IP fallback optional. |
| H-16 brownout N/A | SC1, FW-01 | No | Brownout uses the same `fp_reset_is_abnormal()` → `fail_and_sleep("reset")` branch that H-12/13/14 exercised on hardware. `test_reset_reason.c` asserts that BROWNOUT is abnormal. |
| H-17 one multimeter reading (of 3) | FW-11 | No | No SC covers battery accuracy. The code requirement (8 samples, read before Wi-Fi) is verified in source. The one reading is 8 mV off, well inside the 60 mV threshold. |
| VPS no-change samples weak (n=3 / n=2) | SC4 | No | The LAN before/after (n=53) and the per-stage `wifi_ms` and `first_connect_ms` numbers carry the measurement. The VPS figures agree in direction and size. |
| First ~0.5 s of each boot lost on the USB-CDC console (fp_batt ordering, boot_count) | FW-11 | No | The ordering is guaranteed by `app_main.c` source order. |

No new human verification is requested. The 34-11 session covered every hardware behaviour tied to a success criterion.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `firmware/main/app_main.c` | 257-265 | `ESP_ERROR_CHECK` on `nvs_flash_init`/`nvs_open`, before the reset-backoff check | Warning (W-1) | A persistent NVS fault gives a panic loop with no backoff. The radio stays off, but the battery drains. |
| `firmware/main/api_base.c` | 26 | `strncasecmp` without `<strings.h>` | Warning (W-3) | Host tests break once CI moves to GCC 14. |
| `hardware/PHASE34-HARDWARE-SESSION.md` | H-04/H-18 rows | cites the non-existent `H-04-vps-after-server.log` | Info (W-2) | Evidence citation only. The claim is proven by `H-05-revoke-server.log`. |
| `firmware/main/*.c`, `firmware/tests/*.sh` | many (≈52) | FW-/D-34/T-34/DEVICE-/plan IDs in comments | Info | Against the CLAUDE.md comment convention, but the firmware purge is Phase 35 plan 35-21, gated on 34-11. Deferred, not a Phase 34 gap. |

No TBD/FIXME/XXX debt markers found in the phase's firmware files.

## Deferred Items

| # | Item | Addressed In | Evidence |
|---|---|---|---|
| 1 | Plan/requirement IDs in firmware comments | Phase 35 (35-21) | "G-34 — 35-21 (firmware, last purge wave) stops unless 34-11 is complete on `main`"; SC2 "No plan/ticket reference in any comment" |

## Gaps Summary

No blocking gaps. The code delivers each of the five success criteria, the committed hardware captures confirm them on the real EE02, and the local test and config gates pass. Three non-blocking warnings are worth a quick follow-up:

1. **W-1:** replace the `ESP_ERROR_CHECK` on NVS init/open in `app_main.c` with a path that deep-sleeps with a fixed backoff, so a failed NVS cannot hot-loop.
2. **W-3:** add `#include <strings.h>` to `api_base.c`.
3. **W-2:** point the session doc's H-04/H-18 citations at `H-05-revoke-server.log`, or commit the missing server log.

---

_Verified: 2026-09-25T16:20:00Z_
_Verifier: Claude (gsd-verifier)_
