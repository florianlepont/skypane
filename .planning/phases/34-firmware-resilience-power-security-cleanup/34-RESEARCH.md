# Phase 34: Firmware — resilience, power, security, cleanup - Research

**Researched:** 2026-09-23
**Domain:** ESP-IDF 5.3.1 C firmware (ESP32-S3), device-protocol server (`stub-server/byos_server.py`), firmware CI
**Confidence:** MEDIUM-HIGH — code paths and ESP-IDF Kconfig/API facts are verified against the current tree and the pinned ESP-IDF v5.3.1 sources; a handful of items (TLS-session-over-deep-sleep, the per-row busy-wait minimum, the exact ~28 s cause) can only be closed on real hardware, which is this phase's own final step.

## Summary

Every FW-01..FW-15 finding maps to a specific, small, already-isolated file in `firmware/main/`. The codebase is unusually well-factored for this kind of change: pure logic (backoff, panel_guard, api_base, battery_math) is already split from ESP-IDF-dependent I/O, host tests already exist for the pure modules, and the Log Line Contract is a hard, textual grep contract documented in `firmware/VENDOR.md`. The main technical risk in this phase is **not** "will the code compile" but three specific ESP-IDF constraints that the CONTEXT.md decisions don't yet reflect:

1. **`CONFIG_ESP_TASK_WDT_TIMEOUT_S` has a hard Kconfig range of 1-60 seconds** (verified against `components/esp_system/Kconfig` at the v5.3.1 tag). The phase's own worst-case-legitimate-wake budget (computed below) is ~250 s. The task watchdog **cannot** be the FW-02 "whole-wake deadline" by itself — it must stay a short (≤60 s) *hang* detector, separate from a longer one-shot `esp_timer`-based *budget* that gracefully deep-sleeps with backoff. CONTEXT.md's wording ("a real task watchdog... AND... a one-shot esp_timer") already implies two mechanisms; this research confirms why that split is structurally required, not just tidy.
2. **`esp_tls_client_session_t` wraps `mbedtls_ssl_session` by value, containing internal pointers/buffers** — it is not a flat, `memcpy`-safe struct, so "TLS session tickets in RTC memory across deep sleep" (FW-10) needs `mbedtls_ssl_session_save()`/`_load()` to flatten it into a byte buffer first; `esp_tls` exposes no first-party serialize-for-storage API for this. The *in-wake* reuse (one keep-alive client across `/display` + the image download, same wake) is fully documented and low-risk; the *across-deep-sleep* persistence is a real, undocumented integration and should be scoped as a stretch task with an explicit fallback, not a blocking success criterion.
3. **`nvs_partition_gen.py` only emits whole-partition images — it has no "patch one key into an existing partition" mode.** Regenerating the `nvs` partition (where `dev_token`, `image_hash`, `backoff_n`, `boot_count` already live) to add the enrolment secret and flashing it would erase those keys. The clean fix — confirmed against `partitions.csv`'s free flash gap — is a **second, dedicated NVS partition** for the enrolment secret only, written independently via `parttool.py write_partition --partition-name=secret`, which never touches the main `nvs` partition.

**Primary recommendation:** Implement FW-01..FW-15 largely as CONTEXT.md already specifies (it is well-informed), but size the FW-02 deadline as two numbers (a ≤60 s TWDT hang backstop + a ~250-300 s `esp_timer` wake-budget), scope FW-10's RTC-persisted TLS session as best-effort with a documented fallback, and implement FW-08/D-34-02's secret provisioning via a dedicated NVS partition + `parttool.py`, not a partition regenerate-and-reflash of the whole `nvs` partition.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reset-reason classification, backoff persistence | Device (firmware, `app_main.c`/`backoff.c`) | — | NVS-backed counter must survive brownout/power-loss; RTC memory does not (documented in `app_main.c`'s own header comment) |
| Whole-wake deadline / hang detection | Device (firmware, new module + `esp_task_wdt`) | — | Only the device knows its own wall-clock budget; no network round trip can enforce this |
| Token validation / rejection handling | Device (firmware, `api_client.c`/`state_machine.c`) | Server (`byos_server.py` issues/revokes) | Device must react locally to a 401 without waiting on a server push (there is none — the device only polls) |
| Enrolment secret issuance & registry | Server (`byos_server.py` + new registry) | Device (NVS-stored per-device secret) | Server is the trust anchor deciding which MAC may re-enrol; device only presents its own secret |
| Response/field validation, sleep-duration decision | Device (firmware, pure helpers, host-testable) | — | Must reject a hostile/buggy server response before any I/O touches it; kept ESP-IDF-free so it is host-testable (FW-06) |
| DHCP/TLS/memtest wake-time reduction | Device (firmware, Kconfig + `api_client.c`) | — | Pure device-local configuration; no server involvement |
| Battery telemetry | Device (firmware, `battery.c`) | Server (`byos_server.py` persists `battery_state.json`) | ADC read is device-local; server only records what it's told |
| CI test execution | CI (`.github/workflows/firmware.yml`) | — | Phase 32 owns `ci.yml`; firmware host tests get their own workflow, already scaffolded |

## User Constraints (from CONTEXT.md)

<user_constraints>
### Locked Decisions

**Inherited from the audit:**
- D-A1 — Per-device enrolment secret; byos refuses re-enrolment of a known MAC by anyone not holding that MAC's secret. No flash encryption, no NVS encryption (burns eFuses, irreversible).
- D-A3 — Everything written in this phase (code, comments, commit messages, docs) is in English; comments keep only the *why* and invariants, no plan/ticket history.
- D-A6 — No git history rewrite.

**D-34-01 — Re-enrolment rule:** byos keeps a device registry (MAC → hash of that device's enrolment secret, never the secret itself). `POST /device/v1/setup`: MAC registered + secret matches its hash → new token issued, previous token revoked, 200. MAC registered + secret wrong → refused (401/403), existing token untouched. MAC not registered → refused. `hmac.compare_digest` for comparison. Old shared `--secret`/`SKYPANE_BYOS_SECRET` path retired (migration documented in `deploy/README.md`/`skypane.env.example`). A 401/403 on `/display` (or `/log`) makes the device erase `FP_NVS_DEVICE_TOKEN`; next wake re-enrols with no reflash, no operator action.

**D-34-02 — Secret provisioning: NVS via a serial script:** A host script (`firmware/provision.sh`, name at planner's discretion) generates a random per-device secret, writes it into the device's NVS over USB, prints the registry line (MAC + secret hash) to add on the server. New NVS key in `firmware/main/nvs_schema.h` for the enrolment secret, in the existing `skypane` namespace (migrate in place, never rename). `SKYPANE_SETUP_SECRET` removed from `secrets.example.h`/`secrets.h`; firmware image identical for every device. A device with no secret in NVS logs a clear error and backs off. **Provisioning must not erase the existing token/hash/backoff keys unless explicitly asked.**

**D-34-03 — DHCP (FW-09):** `CONFIG_LWIP_DHCP_RESTORE_LAST_IP=y` and DHCP ARP check disabled (`CONFIG_LWIP_DHCP_DOES_ARP_CHECK=n`), measured on hardware. Fallback: optional static IP from `secrets.h`, compiled in only when defined, disabled by default, used only if the measured gain is insufficient.

**D-34-04 — https-only (FW-07):** New Kconfig `CONFIG_SKYPANE_ALLOW_HTTP`, default `n`. With `n`, URL validation rejects `http://` for the API base and image URLs. `y` is an explicit dev-build opt-in for the laptop stub. Production build proven off (host test of the pure validator in both modes + a check that `sdkconfig.defaults` does not enable it). CA bundle: `CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE` (or CMN→custom) with a custom bundle containing only the ISRG roots (ISRG Root X1, ISRG Root X2) the VPS's Let's Encrypt chain uses.

**Per-requirement remediation (locked, from the ledger):** FW-01..FW-15 as itemized in `.planning/audits/2026-09-23-code-audit.md` and `34-CONTEXT.md` — see that file for the full per-requirement text; not re-copied here verbatim to avoid drift between two sources of truth. This research cites file:line evidence for each below.

**Hardware verification (locked format):** ONE final plan, `autonomous: false`, a single `checkpoint:human-verify`, with a step-by-step script (build, flash, provision, register on VPS, then each trigger scenario), what to capture (serial log via `firmware/monitor.sh`, server log), where to commit captures (`hardware/logs/…` + a results section). "Before" baseline is the existing ≈4.4 s/≈3.0 s DHCP measurement (`hardware/logs/backoff-run.log`) unless re-measured at session start. Any dev-only fault-injection hook must be compiled out of production builds (Kconfig, default off).

### Claude's Discretion
- Plan split/waves, helper file names, exact error-code names and `step=` spellings (must stay compatible with the Log Line Contract; any NEW step value documented in `firmware/VENDOR.md`).
- Registry storage format (e.g. `state/devices.json` MAC → hash) and the operator command to add/remove a device (a small CLI in `stub-server/` is fine).
- byos tests for the new setup rules: follow the existing byos test harness, written as plain functions/asserts that migrate trivially to pytest.
- Whether TLS reuse uses session tickets or session IDs — whichever the VPS (Caddy) and `esp_tls` support.

### Deferred Ideas (OUT OF SCOPE)
None — every FW finding is v1.0 scope (D-A5). Flash/NVS encryption is rejected, not deferred (D-A1).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FW-01 | Reset reason checked at boot → backoff; `epd_init` returns errors | Code-path confirmed at `app_main.c:106-136` (no `esp_reset_reason()` call today) and `epd13in3e.c:158-220` (`epd_init` returns `esp_err_t` already via `ESP_ERROR_CHECK`-free accumulation — see drift note below); `esp_reset_reason_t` values verified via web search cross-checked against ESP-IDF source |
| FW-02 | Whole-wake deadline (`esp_timer`) + real TWDT | TWDT Kconfig verified (`CONFIG_ESP_TASK_WDT_TIMEOUT_S` range 1-60s — a hard constraint the CONTEXT decision doesn't state); `esp_timer` callback-context research; deadline sizing table below |
| FW-03 | 401/403 → erase token, distinct `step=` | `api_client.c:165-171` (`small_request` collapses all non-200 into `FP_ERR_HTTP_STATUS`/`"status"`) — needs a 401/403-specific branch |
| FW-04 | `sleep_s` > 86400 → JSON error | `api_client.c:320-323` (`sleep_ok` bound is currently `1..4294967295`, not `1..86400`) |
| FW-05 | Checked returns for `esp_http_client_write`/`fetch_headers`, `busy_wait("POF")` | `api_client.c:154,156` and `epd13in3e.c:265` confirmed unchecked |
| FW-06 | Pure validation/sleep-decision helpers + host tests, wired into CI | Existing pattern in `firmware/tests/test_backoff.c`, `test_panel_guard.c`, `test_api_base.c`, `test_battery_math.c` + `run_host_tests.sh`; `firmware.yml` currently has no host-test step |
| FW-07 | https-only production, custom ISRG-only CA bundle | `api_client.c:78-88` (`url_valid` accepts `http://` unconditionally); Kconfig facts for `MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE*` verified against v5.3.1 source |
| FW-08 | Per-device enrolment secret, byos registry | `byos_server.py:579-594` (setup handler, confirmed live at this line range, contra the ledger's stale `:140-157` citation — see drift note) |
| FW-09 | DHCP restore/no-ARP-check, measured | Kconfig names verified against `components/lwip/Kconfig` at v5.3.1 |
| FW-10 | Keep-alive client, TLS session reuse, diagnostic wake line, ~28s explained | `esp_http_client`/`esp_tls` API research; `hardware/BATTERY-RUN.md:333-345` read in full — see hypothesis below |
| FW-11 | Battery read pre-Wi-Fi, 8-sample average | `battery.c:31-130` (single-sample, called lazily from `telemetry_headers()` which runs after Wi-Fi connect) |
| FW-12 | `CONFIG_SPIRAM_MEMTEST=n`, row-wait justified, light sleep during spacing | `epd13in3e.c:234` (800us busy-wait, no cited datasheet minimum); `panel.c:97` (`vTaskDelay`, not light sleep) — confirmed the panel is NOT powered during this wait, simplifying the fix |
| FW-13 | Dead code, orphan Kconfig, rollback disabled | `api_base.c`/`api_client.c:330` confirmed; `CONFIG_FP_PROVISION_TIMEOUT_S`/`FP_FACTORY_PREP` confirmed absent from `Kconfig.projbuild` already (drift note) |
| FW-14 | Dedup: hex check, NVS open/read/close, HTTP client config | `api_client.c:66-71` (hash) and `232-241` (token) hex-check duplication confirmed; NVS/HTTP-config duplication confirmed across `fp_api_setup`/`fp_api_get_display`/`fp_api_post_logs` |
| FW-15 | `PROJECT_VER` from `git describe` | `CMakeLists.txt:13` confirmed hardcoded; ESP-IDF's built-in git-describe fallback behavior verified |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Firmware: ESP-IDF 5.3.1 (C), built in the `espressif/idf:v5.3.1` container via `firmware/build.sh`; Apache-2.0, derived from flightportrait/frame (`firmware/VENDOR.md`).
- Tests/CI: stdlib test harnesses, ruff, coverage gate, Playwright; GitHub Actions with a reviewer-gated production deploy. `firmware.yml` is its own workflow — do not touch `ci.yml` (Phase 32 owns it, per `34-CONTEXT.md`'s explicit boundary).
- GSD workflow enforcement: file-changing tool use must go through a GSD command (`/gsd-execute-phase` etc.) — informational for the planner, not something this research file needs to act on.
- Server: Python 3.12, stdlib + Pillow + requests only for `server/`; `stub-server/byos_server.py` is explicitly "stdlib only" per its own docstring — the registry/CLI addition must stay stdlib (no new pip dependency).

## Ledger Drift Notes (code has moved since the audit)

The audit ledger (`2026-09-23-code-audit.md`) cites `byos_server.py:140-157` as FW-08's evidence. That line range **today** holds `state_path()`/`load_state()`/`save_state()` — unrelated helper functions, not the setup handler. The actual `/device/v1/setup` handler is at **`byos_server.py:579-594`**, which matches `34-CONTEXT.md`'s own `canonical_refs` citation (`≈ :580-593`). This is expected: the audit was taken at commit `2808f8a`, and unrelated additions (the quiet-hours/battery-critical `sleep_s` composition chain, documented in the file's own module docstring) have shifted line numbers since. **Trust the CONTEXT.md citation, not the ledger's, for `byos_server.py`.** All other FW-01..FW-15 file:line citations in the ledger were spot-checked against the current tree in this research and hold (± a handful of lines from unrelated comment growth), except:

- `sdkconfig.defaults:21-23` — confirmed current: lines 21-23 are exactly the "Watchdog on everything" comment + `CONFIG_ESP_TASK_WDT_INIT=y` + `CONFIG_ESP_TASK_WDT_TIMEOUT_S=60`. The comment is misleading (implies the watchdog already causes a reset→backoff cycle; it does not, because `CONFIG_ESP_TASK_WDT_PANIC` is unset and no task ever calls `esp_task_wdt_add()`) — FW-02's fix target is correct as specified.
- `Kconfig.projbuild`'s orphan symbols (`CONFIG_FP_PROVISION_TIMEOUT_S`, `FP_FACTORY_PREP`) named in FW-13 are **already absent** from the current `main/Kconfig.projbuild` (confirmed by direct read) — `firmware/VENDOR.md`'s own vendoring table says they were already "removed" during initial vendoring. The audit likely caught them in `sdkconfig.defaults`, where `CONFIG_FP_PROVISION_TIMEOUT_S=600` and `CONFIG_FP_FACTORY_PREP=n` **do** still appear (lines ~34-35) even though no `Kconfig.projbuild` entry defines them anymore. FW-13's actual remaining work for this item is: delete those two orphan lines from `sdkconfig.defaults`.

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|---------------|
| ESP-IDF | v5.3.1 (pinned, `espressif/idf:v5.3.1` container) | Firmware framework | Already the project's pinned toolchain; do not upgrade mid-phase |
| `esp_task_wdt` | built into `esp_system` component (no extra `REQUIRES`) | Hang detection | First-party ESP-IDF component, already partially configured |
| `esp_timer` | built into IDF, already `REQUIRES`d in `main/CMakeLists.txt` | Whole-wake deadline | Already used by `panel.c` (`esp_timer_get_time()`) |
| `mbedtls` (vendored inside ESP-IDF) | matches v5.3.1 pin | Custom CA bundle, TLS session save/load | Already `REQUIRES`d; `gen_crt_bundle.py` embedding is Kconfig-driven, no new dependency |
| Python 3 stdlib (`hashlib`, `hmac`, `secrets`, `json`, `os`) | system Python on dev machine + VPS | Registry hash compare, provisioning script | `byos_server.py` is explicitly stdlib-only; keep it that way |

No new third-party packages (npm/pip/cargo) are introduced by this phase — see Package Legitimacy Audit below.

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `nvs_partition_gen.py` | ships with ESP-IDF v5.3.1 (`components/nvs_flash/nvs_partition_generator/`) | Generate a small NVS partition image from CSV | Provisioning script, to build the new dedicated "secret" partition image |
| `parttool.py` | ships with ESP-IDF v5.3.1 (`components/partition_table/`) | Write ONE named partition over serial without touching others | Flashing the generated "secret" partition image onto a device without disturbing the main `nvs` partition's existing token/hash/backoff keys |
| `esptool` | already used by `flash.sh` | Full-image flash + read-back verify | Unchanged — full image flash still writes `factory`/`ota_0` etc; the secret partition is provisioned as a *separate* step, not part of the app image |

### Alternatives Considered

| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| Dedicated "secret" NVS partition + `parttool.py` | Regenerate the whole `nvs` partition via `nvs_partition_gen.py`, reflash at the `nvs` offset | Simpler tooling, but **erases** `dev_token`/`image_hash`/`backoff_n`/`boot_count` on re-provisioning of an already-running device — violates D-34-02's explicit "must not erase" constraint. Only acceptable if provisioning always strictly precedes first boot, which cannot be guaranteed for the ONE physical devkit reused across this phase's own hardware session. |
| Dedicated "secret" NVS partition | Compiled-in serial console command (ESP-IDF `console` component) that accepts a `provision_secret <hex>` line over UART and calls `nvs_set_str()` at runtime | Also non-destructive, and matches "or an equivalent inside the container" wording — but adds a permanently-compiled runtime listener/command-parser to every production image for a one-time bench operation, and the additional_context explicitly says "prefer host-side tooling." Rejected as higher-risk/lower-payoff than the partition approach. |
| SHA-256 for secret-hash storage | scrypt/bcrypt | The per-device secret is machine-generated high-entropy (`secrets.token_hex(32)`-class), not a human password — unsalted SHA-256 is standard practice for storing a hash of a high-entropy random token (no brute-force/rainbow-table risk the way a low-entropy password has). scrypt adds a stdlib dependency violation (not in Python stdlib) for no real security gain here. Recommend plain `hashlib.sha256` + `hmac.compare_digest`, matching `companion/auth.py`'s existing style. |

**Version verification:**
```
$ docker run --rm espressif/idf:v5.3.1 idf.py --version
```
Not run in this research session (no Docker execution performed) — `firmware/build.sh` already pins this image; the planner should trust the existing pin rather than re-verify per-phase. `[ASSUMED: image tag `espressif/idf:v5.3.1` still resolves to the same toolchain version as when the project pinned it]` — low risk, Docker image tags for Espressif's official images are not known to be mutated after publication, but this was not independently re-pulled and hashed in this session.

## Package Legitimacy Audit

Not applicable — this phase adds no new npm/PyPI/cargo packages. The two "new" dependencies are:
1. Two PEM certificate files (ISRG Root X1, ISRG Root X2) — these are Let's Encrypt's own public root certificates, not installable packages. Source them directly from `https://letsencrypt.org/certs/isrgrootx1.pem` and `https://letsencrypt.org/certs/isrgrootx2.pem` (or the CA/Browser Forum's published root store) at implementation time, and diff their fingerprints against a second independent source (e.g., Mozilla's `certdata.txt` or `curl`'s `cacert.pem`) before committing — this is a supply-chain-sensitive file even though it isn't a "package."
2. `parttool.py`/`nvs_partition_gen.py` — both ship inside the already-pinned `espressif/idf:v5.3.1` container; nothing new to install.

**Packages removed due to slopcheck [SLOP] verdict:** none (n/a — no packages evaluated).
**Packages flagged as suspicious [SUS]:** none (n/a).

## ESP-IDF v5.3.1 Technical Findings

### Reset reason classification (FW-01)

`esp_reset_reason_t` (ESP-IDF core, unchanged across recent versions) includes: `ESP_RST_UNKNOWN`, `ESP_RST_POWERON`, `ESP_RST_EXT`, `ESP_RST_SW`, `ESP_RST_PANIC`, `ESP_RST_INT_WDT`, `ESP_RST_TASK_WDT`, `ESP_RST_WDT`, `ESP_RST_DEEPSLEEP`, `ESP_RST_BROWNOUT`, `ESP_RST_SDIO`, `ESP_RST_USB`, `ESP_RST_JTAG`, `ESP_RST_EFUSE`, `ESP_RST_PWR_GLITCH`, `ESP_RST_CPU_LOCKUP`. `[CITED: docs.espressif.com ESP-IDF system API + cross-checked enum against multiple IDF version docs]`

For FW-01, the abnormal-boot set to treat as "the previous wake failed, apply backoff" is: `ESP_RST_PANIC`, `ESP_RST_INT_WDT`, `ESP_RST_TASK_WDT`, `ESP_RST_WDT`, `ESP_RST_BROWNOUT` — exactly the CONTEXT.md list, with "planner confirms the list." Recommend also treating `ESP_RST_PWR_GLITCH` and `ESP_RST_CPU_LOCKUP` the same way if the planner's target chip revision exposes them (both are newer additions to the enum on some chip targets) — a device that reset abnormally for *any* non-deliberate reason should never resume polling at full speed. `ESP_RST_DEEPSLEEP` is the *normal* wake path and must NOT trigger backoff (it's what every healthy timer wake reports). `[ASSUMED: ESP_RST_PWR_GLITCH/ESP_RST_CPU_LOCKUP are available on the ESP32-S3 target at v5.3.1 — not independently confirmed against the S3-specific enum subset in this session]`.

`app_main.c`'s current `wake_reason_string()` switches on `esp_sleep_wakeup_cause_t` (why the device *woke*, e.g. timer vs. button), which is a **different, unrelated enum** from `esp_reset_reason_t` (why the *chip* reset). FW-01 needs a **second**, new classification call (`esp_reset_reason()`) alongside the existing `esp_sleep_get_wakeup_cause()` call — both are needed simultaneously; one does not substitute for the other. This is a common ESP-IDF confusion point worth flagging as a pitfall.

`epd13in3e.c`'s `epd_init()` (lines 158-220) already accumulates `err |= cmd_to(...)` across every register write and returns `ESP_OK`/`ESP_FAIL` — it does **not** currently call `ESP_ERROR_CHECK` internally. The `ESP_ERROR_CHECK` calls the ledger cites at `epd13in3e.c:167,172,185,192` are the **GPIO/SPI setup calls inside `epd_init()`** (`gpio_config`, `spi_bus_initialize`, `spi_bus_add_device`), which abort on failure today. FW-01's fix is to replace those four `ESP_ERROR_CHECK` calls with checked returns that propagate up through `epd_init()`'s existing `esp_err_t` return path, so a GPIO/SPI setup failure degrades to a backoff-and-retry instead of an unconditional abort/reboot loop.

### Task watchdog vs. whole-wake deadline (FW-02) — the critical sizing constraint

Verified against `components/esp_system/Kconfig` at the `v5.3.1` git tag:

```
config ESP_TASK_WDT_PANIC
    bool "Invoke panic handler on Task Watchdog timeout"
    depends on ESP_TASK_WDT_INIT
    default n
config ESP_TASK_WDT_TIMEOUT_S
    int "Task Watchdog timeout period (seconds)"
    depends on ESP_TASK_WDT_INIT
    range 1 60
    default 5
```
`[VERIFIED: raw.githubusercontent.com/espressif/esp-idf v5.3.1 tag, components/esp_system/Kconfig]`

**`CONFIG_ESP_TASK_WDT_TIMEOUT_S` cannot exceed 60 seconds.** `sdkconfig.defaults` already sets it to `60` (the max). A task subscribes via `esp_task_wdt_add(NULL)` (for the calling/current task) and must call `esp_task_wdt_reset()` periodically or the watchdog fires; with `CONFIG_ESP_TASK_WDT_PANIC=y` a timeout triggers `esp_reset_reason() == ESP_RST_TASK_WDT` on the next boot (exactly what FW-01 needs to detect). `[CITED: esp-idf docs, wdts.rst + esp_task_wdt.h doc comments]`

Deadline sizing — worst-case *legitimate* single wake, using the timeouts already coded in `api_client.c`/`panel.c`/`Kconfig.projbuild`:

| Stage | Budget | Source |
|-------|--------|--------|
| Wi-Fi connect | 15 s | `state_machine.c:31` `fp_wifi_connect(15000)` |
| SNTP sync (only if RTC clock lost, e.g. after a brownout — the exact FW-01 scenario, so it can stack with a recovery wake) | 10 s | `wifi.c:94` `pdMS_TO_TICKS(10000)` |
| Setup call (first-ever wake, or immediately after a 401 re-enrol) | 15 s | `api_client.c:208` `.timeout_ms = 15000` |
| Display GET | 20 s | `api_client.c:284` `.timeout_ms = 20000` |
| Image download | 30 s | `api_client.c:406` `.timeout_ms = 30000` |
| Panel-guard spacing wait | up to 90 s | `CONFIG_FP_MAX_GUARD_WAIT_S` default, `Kconfig.projbuild` |
| Blit (`epd_init` + two `send_half` + PON/DRF/POF busy-waits) | ~68.7 s | `epd13in3e.c`: `send_half` ≈2.56 s (1600 rows × 800us × 2 halves) + PON wait ≤3 s + DRF wait ≤60 s (`busy_wait("DRF", 60000)`) + POF wait ≤3 s |
| **Sum (fully stacked, pessimistic)** | **≈248.7 s** | — |

This is deliberately pessimistic (not every stage occurs on every wake — SNTP only fires post-brownout, setup only fires on first-ever/re-enrol wakes — but a re-enrol wake *after* a 401, which is exactly what success criterion 2 tests, legitimately stacks setup+display+download in one wake). **Recommend a deadline in the 270-300 s range**, with the 60 s TWDT staying a separate, short hang backstop. Document both numbers and their separate purposes in a comment, since a future reader will otherwise assume one number governs both. `[MEDIUM confidence — derived from code-declared per-call timeouts, not measured wall-clock; the hardware session's before/after wake-duration measurement is the only way to confirm these numbers are realistic rather than a napkin sum]`

**`esp_timer` callback context (why the one-shot deadline timer cannot call `esp_deep_sleep_start()` directly from its own callback, safely, without care):** by default, `esp_timer` callbacks dispatch from a dedicated, single, high-priority `esp_timer` FreeRTOS task (`ESP_TIMER_TASK` dispatch method; `ESP_TIMER_ISR` is the lower-latency alternative but is not the default and pulls in extra Kconfig). `CONFIG_ESP_TIMER_TASK_STACK_SIZE` sizes that task's stack. `[CITED: docs.espressif.com esp_timer.html v5.3.1 doc + esp-idf Kconfig defaults]` `esp_deep_sleep_start()` is a `noreturn` function; nothing in the ESP-IDF esp_timer docs prohibits calling blocking/heavy functions from a timer-task callback, but the docs explicitly warn that a long-running callback delays *other pending timer callbacks* (there aren't likely to be any others active in this firmware, so this is a low risk) and recommend deferring heavy work to another task in general. **Recommend:** rather than calling `esp_deep_sleep_start()` directly inside the timer callback (which works, since `app_main`'s own task isn't waiting on anything the timer task would starve), the simplest and most auditable pattern is to have the callback **set a `volatile` flag + notify `app_main`'s task** (e.g. `xTaskNotifyGive` on a saved `TaskHandle_t` for the main task), and have `app_main()` check that flag/notification at each blocking-call boundary (the same boundaries where `esp_task_wdt_reset()` is fed) — this keeps the actual `enter_deep_sleep()` call in the existing, single, well-understood exit path in `app_main.c`, rather than adding a second `noreturn` exit point that has to independently replicate `fp_wifi_stop()`/`fp_panel_before_sleep()`/`fp_led_off()` ordering. `[ASSUMED: calling esp_deep_sleep_start() directly from the esp_timer task is not itself unsafe — undocumented either way; the task-notify pattern above sidesteps the question entirely and is the lower-risk implementation regardless of the answer]`

### DHCP (FW-09)

Verified against `components/lwip/Kconfig` at the `v5.3.1` tag:

```
config LWIP_DHCP_DOES_ARP_CHECK
    bool "DHCP: Perform ARP check on any offered address"
    default y
    depends on LWIP_IPV4
config LWIP_DHCP_RESTORE_LAST_IP
    bool "DHCP: Restore last IP obtained from DHCP server"
    default n
    depends on LWIP_IPV4
    help
        When this option is enabled, DHCP client tries to re-obtain
        last valid IP address obtained from DHCP server. Last valid
        DHCP configuration is stored in nvs and restored after
        reset/power-up.
```
`[VERIFIED: raw.githubusercontent.com/espressif/esp-idf v5.3.1 tag, components/lwip/Kconfig]`

Both are exactly the Kconfig names D-34-03 names — no drift. `LWIP_DHCP_RESTORE_LAST_IP`'s own help text confirms it persists into **NVS**, which is worth noting as an interaction: it adds its own small NVS writes into the default `nvs` partition on every successful DHCP lease, distinct from — and not a conflict with — the new dedicated "secret" NVS partition recommended above (different partition, different namespace).

### https-only + custom CA bundle (FW-07)

Verified against `components/mbedtls/Kconfig` at the `v5.3.1` tag:

```
config MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE
    depends on MBEDTLS_CERTIFICATE_BUNDLE
    default n
    bool "Add custom certificates to the default bundle"
config MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE_PATH
    depends on MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE
    string "Custom certificate bundle path"
    help
        Name of the custom certificate directory or file. This path is
        evaluated relative to the project root directory.
choice MBEDTLS_DEFAULT_CERTIFICATE_BUNDLE
    default MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_FULL
    config MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_FULL
    config MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_CMN
    config MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE
        bool "Do not use the default certificate bundle"
```
`[VERIFIED: raw.githubusercontent.com/espressif/esp-idf v5.3.1 tag, components/mbedtls/Kconfig]`

To ship a bundle containing **only** the ISRG roots (not the full/CMN Mozilla set plus the ISRG roots appended), set `CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE=y` (selects the "none" choice arm) **and** `CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE=y` with `CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE_PATH` pointing at a project-relative directory (e.g. `firmware/main/certs/`) containing the two ISRG PEM files. `gen_crt_bundle.py` runs automatically as part of the mbedtls component's build integration when these options are set — no manual script invocation is required by the developer or CI. `[CITED: docs.espressif.com esp_crt_bundle.html + gen_crt_bundle.py source, cross-referenced]`. `esp_crt_bundle_attach` (already used unchanged at every `esp_http_client_config_t.crt_bundle_attach` site in `api_client.c`) needs no C code change — the bundle *contents* are entirely a Kconfig + committed-PEM-files change.

`CONFIG_SKYPANE_ALLOW_HTTP` (new, D-34-04) belongs in the top-level `menu "SkyPane"` block of `main/Kconfig.projbuild` (not nested under the E1004/panel/battery submenus), `default n`. `url_valid()` (`api_client.c:78-88`) and `fp_api_base_normalize()` (`api_base.c`) both currently accept `http://` unconditionally — both need the same `#if !CONFIG_SKYPANE_ALLOW_HTTP` (or a runtime `#ifdef`-derived flag passed in) gate. Recommend a single shared pure function (`bool fp_scheme_allowed(const char *url)`) so both call sites and the host test agree on one definition — this also satisfies part of FW-14 (dedup).

### TLS session reuse (FW-10)

**In-wake keep-alive (low risk, well-documented):** `esp_http_client` supports issuing multiple `esp_http_client_perform()`/`esp_http_client_open()` calls against the same `esp_http_client_handle_t` with `esp_http_client_set_url()` between them, keeping the underlying TCP+TLS connection open if the server allows it; `esp_http_client_close()` ends the connection but preserves the handle for reuse, `esp_http_client_cleanup()` fully tears it down. `[CITED: docs.espressif.com esp_http_client.html v5.3.1]` The current code creates a **fresh `esp_http_client_handle_t`** (and thus a fresh TCP+TLS connection) for each of `fp_api_setup()`, `fp_api_get_display()`, and `fp_api_download()` (`api_client.c:210,286,408`). FW-10's "one keep-alive client for display + image" means: init one handle, call `esp_http_client_set_url()` + `esp_http_client_open()` for `/device/v1/display`, read the response, then `esp_http_client_set_url()` to the image URL and repeat on the **same handle**, `esp_http_client_cleanup()` only at the end. This is a same-host, same-process, single-wake change with no cross-boot persistence concerns.

**Cross-deep-sleep persistence (higher risk, partially undocumented — see Summary's finding #2):** `esp_tls_client_session_t` is:
```c
#ifdef CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS
typedef struct esp_tls_client_session {
    mbedtls_ssl_session saved_session;
} esp_tls_client_session_t;
#endif
```
`[VERIFIED: raw.githubusercontent.com/espressif/esp-idf v5.3.1 tag, components/esp-tls/esp_tls.h]` — a **value-type wrapper around `mbedtls_ssl_session`**, which itself is a variable-size struct containing dynamically-populated fields (ticket bytes, peer certificate data, etc. depending on TLS version/config). It is not safe to `memcpy` this struct into `RTC_DATA_ATTR`/`RTC_NOINIT_ATTR` memory and expect it to be valid after a fresh boot's heap is re-initialized — any internal pointers it holds would dangle. `esp_tls_get_client_session()`/`esp_tls_free_client_session()` are documented only for **same-boot** reuse ("This can be passed again in the `esp_tls_cfg_t` structure... for session resumption" — no mention of storage/serialization). `[CITED: esp_tls.h doc comments]`

mbedtls itself exposes exactly the serialization API this needs — `mbedtls_ssl_session_save()`/`mbedtls_ssl_session_load()` — designed specifically for persisting a session across a connection loss/process restart into a flat byte buffer. `[CITED: mbedtls project docs + forum threads describing this as the standard pattern for exactly this use case]` Since `esp_tls_client_session_t` is *only* a one-field wrapper around `mbedtls_ssl_session`, calling `mbedtls_ssl_session_save(&wrapper.saved_session, buf, buf_len, &out_len)` directly on that field should work — but this reaches past `esp_tls`'s public API into its internal struct layout, which is not a contract ESP-IDF guarantees stable across even patch releases. **Recommend:** implement the in-wake keep-alive (guaranteed win, FW-10's main ask) first; treat cross-deep-sleep session persistence as a **separate, explicitly best-effort task** with a hardware-verified go/no-go, sized generously in RTC memory (reserve 1-2 KB in `RTC_DATA_ATTR`, and print the actual `mbedtls_ssl_session_save(NULL, ..., &out_len)`-reported size on first connect during the hardware session to confirm the reservation is enough — TLS 1.2 session tickets are typically small, hundreds of bytes to ~1-2 KB depending on the server's ticket format; TLS 1.3 tickets can run larger). If it doesn't pan out cleanly in the one hardware session, document it as a known gap rather than blocking the phase — CONTEXT.md's "Claude's Discretion" note ("whichever the VPS and esp_tls support") already anticipates this might not land cleanly.

**Caddy-side support:** Go's standard `crypto/tls` (what Caddy is built on) supports session resumption via both stateless session tickets (RFC 5077) and, depending on TLS version negotiated, session IDs, by default with no special Caddy configuration. `[ASSUMED — not independently verified against Caddy's current TLS config surface in this session; standard Go TLS server behavior is session-ticket support enabled by default, but Caddy could theoretically disable it]`. Recommend the hardware session simply observe (via a packet capture or mbedtls debug log) whether the handshake actually resumes (abbreviated handshake, no full certificate exchange) rather than assuming it will.

### The ~28 s unexplained per-cycle overhead (FW-10)

Read in full: `hardware/BATTERY-RUN.md`'s 12.34-day production run measured a **mean inter-poll interval of 328.0 s against a nominal 300 s** (`SKYPANE_SLEEP_S=300` on the VPS during that run), i.e. ~28 s of real overhead per cycle that `check-battery`'s nominal formula doesn't model. Critically, **this measurement is from the deployed run served by `skypane-byos.service` over HTTPS on the real VPS** (confirmed: `BATTERY-RUN.md` states "the run is served by `skypane-byos.service`... `--image-url-scheme https`"), **not** the LAN-local plaintext stub server that produced the ≈4.4 s/≈3.0 s baseline in `hardware/logs/backoff-run.log`. These are two different network paths, not two measurements of the same thing.

**Leading hypothesis (MEDIUM-HIGH confidence, directly consistent with FW-10's own diagnosis in the ledger):** the dominant contributor is **TLS handshake cost that the LAN/plaintext baseline never paid** — two full mbedtls (software crypto, no hardware TLS accelerator engaged for the handshake's asymmetric operations on this chip/IDF combination) handshakes per wake (one for `/display`, one for the image download, per the current fresh-client-per-call code), each paying real internet round-trip time to the VPS (not LAN latency) plus ESP32-S3 software RSA/ECDHE computation time. This is exactly what FW-10's own keep-alive + session-reuse remediation targets, which is a strong internal-consistency signal that this is the right hypothesis rather than a coincidence. Secondary, smaller contributors worth ruling in/out on hardware: (a) DHCP full-handshake cost on every wake against the VPS's actual network path (mitigated by FW-09, but FW-09's own baseline was measured on the LAN stub, not the VPS path — the hardware session should re-measure DHCP timing specifically against whatever network the production device actually uses); (b) occasional full blits (image *does* change during a live 300 s-cadence run tracking real flights, and a full blit costs many seconds — DRF alone allows up to 60 s — while hash-skip cycles cost near-zero; an average blended across both would inflate the mean above what a hash-skip-only baseline shows).

**Recommend for the hardware session:** measure wake duration in at least three configurations — (1) hash-skip cycle against the LAN stub (should reproduce the existing ~4.4 s baseline), (2) hash-skip cycle against the real VPS over HTTPS with the *current* fresh-TLS-per-call code (isolates the TLS-over-internet cost), (3) the same VPS run *after* FW-10's keep-alive change (shows the improvement). This three-way comparison is what actually explains the ~28 s, rather than asserting a hypothesis without measuring it — the phase's own success criterion 4 already asks for a before/after measurement; structuring it this way gets the explanation "for free" from the same data.

### PSRAM memtest, row busy-wait, light sleep during spacing (FW-12)

`CONFIG_SPIRAM_MEMTEST` exists as a standard ESP-IDF SPIRAM Kconfig option (default `y`); disabling it (`n`) skips the ~446 ms full-memory-pattern test on every boot. `[ASSUMED — the exact Kconfig file location (`components/esp_hw_support/Kconfig.spiram` at v5.3.1) could not be fetched in this session (404 on the exact path guessed); the option's existence and default-on behavior is well-established ESP-IDF knowledge and the ~446ms figure is already cited as measured in the audit ledger itself, but the precise help text was not re-verified against source in this session]`. Recommend the planner confirm the exact Kconfig symbol name compiles (`idf.py menuconfig` search, or a grep of the container's Kconfig tree) as a first task step rather than trusting this citation blindly.

The 800 us per-row busy-wait (`epd13in3e.c:234`, `esp_rom_delay_us(800)`) has **no cited minimum in the Good Display GDEP133C02 datasheet** — confirmed by reading `Kconfig.projbuild`'s own `FP_MIN_REFRESH_SPACING_S` help text, which already documents (with a source citation and retrieval date) that the datasheet's only refresh-related guidance is a *minimum* refresh frequency (every ≤24h, against ghosting), never a maximum rate or per-row timing spec. The 800us figure is a carried-over pacing value from the Waveshare reference driver's comment ("Reference paces ~1 ms/row"), not a datasheet-derived constant. **Recommend: do not experimentally shorten this value during the one hardware session.** The panel has no rollback if a shortened per-row wait corrupts a real color e-ink refresh (unlike a software bug, a bad refresh isn't obviously visible as "wrong" versus "the art just looks like that," and the datasheet's reliability section doesn't rate row-timing risk at all) — this satisfies FW-12's own stated fallback ("shortened only if the datasheet allows; else keep and document why") cleanly: keep it, and point this research's citation trail (Kconfig.projbuild's own sourced note) as the "why."

**Light sleep during the panel-guard spacing wait — simpler than it first appears.** Tracing `panel.c:67-113` and `state_machine.c:100-104`: `fp_wifi_stop()` is called **before** `fp_panel_draw()`, and within `fp_panel_draw()`, the `FP_PANEL_DRAW_AFTER_WAIT` branch's `vTaskDelay(wait_s * 1000)` runs **before** `epd_init()` is ever called (`s_drawing = true; epd_init(); epd_blit(buf);` all happen strictly after the wait). This means **the panel is not yet powered (`PIN_EN` not yet asserted) during the spacing wait**, and Wi-Fi is already down. There is no GPIO-hold concern for this specific wait (GPIO hold matters for retaining an already-asserted output level through a sleep transition; nothing is asserted yet here). The fix is a straightforward substitution: replace `vTaskDelay(pdMS_TO_TICKS(wait_s * 1000U))` with `esp_sleep_enable_timer_wakeup((uint64_t)wait_s * 1000000ULL); esp_light_sleep_start();`. Light sleep preserves RAM/task state across the call (unlike deep sleep) and has sub-millisecond wake latency, so control returns to the same point in `fp_panel_draw()` afterward. `[CITED: docs.espressif.com sleep_modes.html — light sleep preserves CPU/RAM state, only clock-gates; deep sleep powers off digital domain]`

**Interaction to verify on hardware:** if FW-02's task watchdog subscribes the main task for the *entire* wake (not just the network-bound portions), a 90 s light sleep inside the spacing wait could itself trip the ≤60 s TWDT unless the main task either (a) is unsubscribed for the duration of the light sleep, or (b) FreeRTOS tick suspension during light sleep means the TWDT's own timeout tracking doesn't advance during the sleep (plausible, since TWDT timing is tick-based, but not independently confirmed in this session). **Recommend the planner treat this as an explicit interaction to test in the hardware session** (scenario: guard-wait light sleep occurring while the whole-wake deadline / TWDT are both armed), not something to assume away.

### `PROJECT_VER` from `git describe` (FW-15)

ESP-IDF's build system already has a **built-in fallback chain** for `PROJECT_VER`: if `CONFIG_APP_PROJECT_VER_FROM_CONFIG` is unset and the project's `CMakeLists.txt` does not explicitly `set(PROJECT_VER ...)`, the build system tries `${PROJECT_PATH}/version.txt`, then `git describe`, then falls back to `"1"`. `[CITED: docs.espressif.com build-system.html v5.3.1-era docs, cross-checked against IDF_VER's own well-known git-describe behavior]` **The current `CMakeLists.txt:13` explicitly sets `PROJECT_VER "0.1.0-p1"`, which short-circuits this entire mechanism** — simply **deleting** that `set()` line is likely sufficient to make the build fall through to `git describe`, rather than needing custom CMake logic. The one thing to verify: `firmware/build.sh` runs the build **inside a Docker container** with the repo bind-mounted (`-v "${SCRIPT_DIR}:/project"`) — `git describe` requires a `.git` directory to be reachable from the working directory (`/project`), and the mount is `${SCRIPT_DIR}` (i.e., `firmware/`), **not the repo root**, so `.git` (which lives at the repo root, one level up) is **not present inside the container's mounted path**. `git describe` will fail inside this container as currently configured. CONTEXT.md already anticipates this ("a fallback when git is unavailable in the build container") — confirmed necessary, not hypothetical. **Recommend:** either (a) mount the repo root instead of `firmware/` in `build.sh` (larger change, touches an already-working script), or (b) resolve `git describe` **on the host**, outside the container, and pass it in as a `-D` CMake define (`idf.py -DPROJECT_VER=$(git describe --always --dirty) ...`) from `build.sh` itself — this keeps the container mount unchanged and matches the "wrap the working script" principle `.github/workflows/firmware.yml`'s own comment already cites (D-12). Option (b) is the lower-risk change.

## Architecture Patterns

### Recommended Project Structure (new files only; existing structure unchanged)

```
firmware/
├── main/
│   ├── validate.c / validate.h        # FW-06: pure response-field validators (image_hash, url, sleep_s range, led_enabled, token shape) — no ESP-IDF includes
│   ├── sleep_decision.c / .h          # FW-06: pure "what sleep_s given result/backoff/reset-reason" decision
│   ├── wake_deadline.c / .h           # FW-02: pure deadline-math (given elapsed_us, budget_us -> expired bool) kept separate from the esp_timer plumbing so it's host-testable
│   ├── secret_provision.c / .h        # D-34-02: reads the enrolment secret from the new NVS partition; logs+backs off cleanly if absent
│   └── certs/isrg-root-x1.pem, isrg-root-x2.pem   # FW-07: custom CA bundle source files
├── tests/
│   ├── test_validate.c
│   ├── test_sleep_decision.c
│   └── test_wake_deadline.c
├── provision.sh                       # D-34-02: generates secret, builds+writes the dedicated NVS partition, prints the registry line
└── partitions.csv                     # + one new "secret" nvs-type partition entry in the existing free gap

stub-server/
├── byos_server.py                     # FW-08: registry check replaces the shared --secret check in the setup handler
├── devices_cli.py                     # new: add/remove/list registered devices (MAC -> secret hash)
└── test_devices_registry.py (or appended to test_poll_cycle.py)  # FW-08 tests, plain check()/assert pattern matching the existing harness
```

### `partitions.csv` — where the new "secret" partition fits

Current layout (`firmware/partitions.csv`):
```
nvs,        data, nvs,      0x9000,  0x6000    # ends at 0xF000
otadata,    data, ota,      0xf000,  0x2000    # ends at 0x11000
phy_init,   data, phy,      0x11000, 0x1000    # ends at 0x12000
nvs_keys,   data, nvs_keys, 0x12000, 0x1000    # ends at 0x13000
factory,    app,  factory,  0x20000, 0x250000
```
There is a **free gap from `0x13000` to `0x20000`** (0xD000 = 52 KB) between `nvs_keys` and `factory`. Recommend adding:
```
secret,     data, nvs,      0x13000, 0x1000
```
(4 KB is generous for a single string key; NVS's own page-size minimum is 4 KB per page regardless of content size, so this is effectively the smallest usable NVS partition). This keeps `factory` at its existing `0x20000` offset unchanged — **verify with `idf.py partition-table` (or the build's generated `partition-table.bin`) that the tool doesn't flag an alignment/gap warning**, though NVS-type partitions have no alignment requirement beyond flash sector boundaries (4 KB), which `0x13000`/`0x1000` already satisfy. `[MEDIUM confidence — arithmetic verified by hand against the committed partitions.csv; not verified by an actual `idf.py partition-table` run in this session]`

### Anti-Patterns to Avoid

- **Regenerating the whole `nvs` partition to add one key** — erases `dev_token`/`image_hash`/`backoff_n`/`boot_count` on any device that has already booted once. Use the dedicated "secret" partition instead (see above).
- **Treating the TWDT timeout and the whole-wake deadline as the same number** — the TWDT is capped at 60 s by Kconfig; the deadline needs to be ~4-5x that. Two separate constants, two separate purposes, documented as such.
- **Calling `mbedtls_ssl_session_save`/`_load` against `esp_tls`'s internal struct as if it were public API** without a documented fallback if the internal layout ever shifts — scope as best-effort, not a hard requirement.
- **Adding a runtime serial console command for provisioning** — works, but is unnecessary complexity given `parttool.py` already solves the "write one partition without touching others" problem from the host side, matching CONTEXT's own "prefer host-side tooling" steer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Patch one NVS key without erasing others | A custom NVS-partition-diffing tool | `parttool.py write_partition --partition-name=secret` against a **separate, dedicated** partition | First-party tool, already in the pinned container; the "separate partition" framing avoids needing the diff/patch capability at all |
| Constant-time secret comparison | Hand-rolled loop compare | Python `hmac.compare_digest`, already used identically in `companion/auth.py` | Existing project convention; timing-attack-safe by construction |
| Custom CA trust store | Hand-parsed PEM list at runtime | ESP-IDF's `gen_crt_bundle.py` + `esp_crt_bundle_attach` (already wired) | Build-time embedding, binary-search bundle lookup at runtime — reinventing this in application code would be materially worse (larger, slower, easier to get wrong) |
| TLS session persistence format | A custom binary session-cache format | `mbedtls_ssl_session_save`/`_load` (mbedtls's own serialization, built for exactly this) | Don't invent a wire format for something the TLS library already solves — even though wiring it through `esp_tls`'s wrapper is nontrivial, the serialization primitive itself should not be reimplemented |

**Key insight:** every "don't hand-roll" item in this phase already has a first-party ESP-IDF or Python-stdlib primitive; the actual engineering work is wiring existing primitives into this project's specific (deep-sleep, single-wake, battery-constrained) shape, not inventing new mechanisms.

## Runtime State Inventory

> Included because FW-08/D-34-01/D-34-02 retire a shared-secret enrolment scheme in favor of a per-device one — a real provisioning-scheme migration, not a pure code refactor.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `stub-server/byos_state.json`'s `{"tokens": {mac: token}}` — unaffected; existing issued tokens remain valid and the setup handler's token-issuance line (`self.state["tokens"][body["mac"]] = token`) is unchanged. A **new** `state/devices.json` (or similar) registry (`{mac: secret_hash}`) must be created and populated **before** any device can pass the new gate. | Code edit (new registry file/module) + a one-time manual data-population step per already-provisioned device — see next row |
| Live service config | `deploy/skypane-byos.service`'s `ExecStart` line hardcodes `--secret ${SKYPANE_BYOS_SECRET}`. Once the shared-secret CLI flag is retired from `byos_server.py`, this line will either error (unknown flag) or silently pass a now-ignored argument, depending on how the argparse change is made. `deploy/skypane.env.example`'s `SKYPANE_BYOS_SECRET=` documentation becomes stale. | Code edit: remove `--secret ${SKYPANE_BYOS_SECRET}` from the systemd unit's `ExecStart`, remove/repurpose the env var from `skypane.env.example`, update `deploy/README.md`'s provisioning instructions (already flagged in `34-CONTEXT.md`'s own `specifics` section as needing a note for Phase 37 too, since SEC-07 targeted this same variable). |
| OS-registered state | None found specific to firmware. The ONE physical devkit used in the hardware session has **no prior registry entry** under the new scheme — if the session's FW-03 re-enrolment test (revoke token → expect 401 → re-enrol) runs before that device's MAC is added to the new registry, re-enrolment will legitimately fail with "MAC not registered," which would be misdiagnosed as a bug rather than a missing precondition. | **Hardware-session script must register the devkit's MAC in the registry as an explicit, early, separate step** — before any trigger scenario that depends on re-enrolment succeeding. |
| Secrets/env vars | `firmware/main/secrets.example.h`'s `SKYPANE_SETUP_SECRET` macro is removed per D-34-02; `state_machine.c:42`'s call site (`fp_api_setup(SKYPANE_SETUP_SECRET)`) must change to read the secret from the new NVS partition instead of the macro — this is a required code change, not just a header cleanup, since the current call site directly references the macro by name. The developer's own local (gitignored) `firmware/main/secrets.h` will need the macro removed too, or the build breaks once the macro is deleted from `secrets.example.h` and the call site stops referencing it — self-resolving once the code change lands, flagged here only so the planner doesn't forget the call site itself needs to change, not just the header. | Code edit (call site) + no data migration (macro simply stops being read) |
| Build artifacts | None additional — the app partition table changes (new "secret" entry) will show up in the next `idf.py build`'s generated `partition-table.bin`; no stale artifact risk since this is a from-scratch container build every time (`build.sh`). | None |

## Common Pitfalls

### Pitfall 1: TWDT range assumed to cover the whole wake
**What goes wrong:** Implementer sets `CONFIG_ESP_TASK_WDT_TIMEOUT_S` to some large number (e.g. 200) expecting the TWDT itself to be the "whole-wake deadline," and the build either clamps/rejects the value or `menuconfig` refuses it.
**Why it happens:** The Kconfig `range 1 60` isn't obvious without reading the Kconfig source directly; `sdkconfig.defaults` already has it at exactly the max (60), which looks like "the biggest reasonable number" rather than "the ceiling."
**How to avoid:** Keep TWDT ≤60 s as a hang backstop only; implement the actual multi-minute budget as a separate `esp_timer`.
**Warning signs:** `idf.py menuconfig` or a `sdkconfig` diff shows the value silently clamped to 60, or a build warning about an out-of-range Kconfig value.

### Pitfall 2: Assuming `esp_tls_client_session_t` is a flat, storable struct
**What goes wrong:** Code `memcpy`s the struct into `RTC_DATA_ATTR` memory and reads it back after deep sleep, appearing to work in a quick test (because the memory *region* survives) but crashing or silently failing to resume the session under real conditions, because the struct's `mbedtls_ssl_session` field may reference session-ticket bytes or other data by pointer depending on the mbedtls configuration/version.
**Why it happens:** The type name ("session ticket") suggests a small, self-contained blob; the actual struct layout isn't obvious without reading `esp_tls.h`.
**How to avoid:** Use `mbedtls_ssl_session_save()`/`_load()` explicitly to flatten to a byte buffer before storing; verify the actual required buffer size on real hardware before sizing the RTC reservation.
**Warning signs:** The "resumed" handshake doesn't actually abbreviate (still does a full certificate exchange) — the surest sign the session data didn't survive intact.

### Pitfall 3: `git describe` silently failing inside the build container
**What goes wrong:** `PROJECT_VER` falls back to `"1"` (ESP-IDF's own final fallback) instead of an actual git-derived version, and this is easy to miss because the build still succeeds — there's no error, just a wrong/generic version string reported to the server as `X-Fw-Version`.
**Why it happens:** `firmware/build.sh` bind-mounts `firmware/` as `/project`, not the repo root, so `.git` isn't visible inside the container at the path `git describe` would look from.
**How to avoid:** Resolve `git describe` on the host inside `build.sh` (which already runs outside Docker at that point) and pass it into the container build as a CMake `-D` define, rather than relying on the container to find `.git` itself.
**Warning signs:** Every built image reports `X-Fw-Version: 1` regardless of what commit produced it.

### Pitfall 4: 401 handling accidentally swallowed by the generic status-error branch
**What goes wrong:** `small_request()`'s existing generic `if (status != 200) return FP_ERR_HTTP_STATUS;` branch runs before a new 401/403-specific check is added, so the new "erase token" logic never triggers because the function already returned.
**Why it happens:** The natural place to add the 401/403 check is *after* the existing generic status check, which is exactly the wrong order.
**How to avoid:** Special-case `status == 401 || status == 403` **before** the generic `status != 200` branch inside `small_request()` (or have callers inspect the status code directly, since `small_request()` currently discards it after classification).
**Warning signs:** Host test for FW-03 passes (since it can test the classification function in isolation) but the hardware session's revoke-token scenario shows `step=status` in the log instead of the new `step=auth` token.

## Code Examples

### Reset reason check (FW-01), fitting the existing `app_main.c` structure

```c
// Source: esp_system.h (ESP-IDF, unchanged core API across recent versions);
// pattern follows app_main.c's existing wake_reason_string() shape.
static bool boot_was_abnormal(esp_reset_reason_t reason)
{
    switch (reason) {
    case ESP_RST_PANIC:
    case ESP_RST_INT_WDT:
    case ESP_RST_TASK_WDT:
    case ESP_RST_WDT:
    case ESP_RST_BROWNOUT:
        return true;
    default:
        return false;
    }
}
```

### Deadline vs. hang detector, two separate mechanisms (FW-02)

```c
// esp_task_wdt: short hang backstop, ~60s ceiling (Kconfig range 1..60).
// Fed at each blocking-call boundary (after wifi connect, after each HTTP
// call, after the blit) so a genuine infinite loop inside any one of them
// panics -> ESP_RST_TASK_WDT -> FW-01's backoff branch on next boot.
esp_task_wdt_add(NULL);
...
esp_task_wdt_reset();  // call after each blocking stage completes

// esp_timer: whole-wake budget, sized above the worst-case legitimate
// wake (~250s computed in RESEARCH.md) with margin. On expiry, notifies
// app_main's task rather than calling esp_deep_sleep_start() directly
// from the timer-task context, so the existing single exit path in
// enter_deep_sleep() stays the only place that sequences
// fp_wifi_stop()/fp_panel_before_sleep()/fp_led_off().
static TaskHandle_t s_main_task;
static void IRAM_ATTR deadline_cb(void *arg) {
    xTaskNotifyGive(s_main_task);
}
```

### `hmac.compare_digest` registry check (FW-08), matching `companion/auth.py`'s existing style

```python
# Source: existing pattern in companion/auth.py (hmac.new + hmac.compare_digest)
import hashlib
import hmac

def secret_ok(mac, presented_secret, registry):
    """registry: {mac: sha256_hex_of_that_device_secret}"""
    stored_hash = registry.get(mac)
    if stored_hash is None:
        return False  # MAC not registered -> refused, per D-34-01
    presented_hash = hashlib.sha256(presented_secret.encode()).hexdigest()
    return hmac.compare_digest(presented_hash, stored_hash)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Shared setup secret (`SKYPANE_SETUP_SECRET`/`SKYPANE_BYOS_SECRET`), any device with the value can (re-)enrol any MAC | Per-device secret, server-side registry gates re-enrolment by MAC | This phase (D-34-01/02) | A leaked secret from one device no longer compromises every device; a stolen/cloned MAC alone (MACs are visible on the wire, not secret) is insufficient without the paired secret |
| Fresh TLS handshake per HTTP call | Keep-alive client within a wake; session-ticket reuse across wakes (best-effort) | This phase (FW-10) | Removes redundant handshake cost — the leading hypothesis for the measured ~28s/cycle production overhead |
| Reset-reason-blind boot (`power-on` label regardless of actual cause) | `esp_reset_reason()` classified at boot, feeding backoff | This phase (FW-01) | A crash-looping device now backs off exponentially instead of hot-looping at the normal poll cadence, which is a real battery-drain and (on a metered/rate-limited server) availability risk |

**Deprecated/outdated:**
- `CONFIG_FP_PROVISION_TIMEOUT_S`/`CONFIG_FP_FACTORY_PREP` in `sdkconfig.defaults` — orphaned since the initial vendoring stripped their `Kconfig.projbuild` definitions; harmless (unused symbols with no code reading them) but should be deleted per FW-13.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `espressif/idf:v5.3.1` Docker tag still resolves to the same pinned toolchain build as when the project adopted it | Standard Stack | Low — build would simply reflect whatever that tag currently points to; not independently re-pulled/hashed this session |
| A2 | `ESP_RST_PWR_GLITCH`/`ESP_RST_CPU_LOCKUP` are available on the ESP32-S3 target at IDF v5.3.1 | ESP-IDF Technical Findings, reset reason | Low — worst case, the planner includes them in the abnormal-boot switch and the compiler flags an undefined enum member, an easy build-time catch, not a silent runtime bug |
| A3 | Calling `esp_deep_sleep_start()` directly from an `esp_timer` callback (task-dispatch context) is not itself documented-unsafe | ESP-IDF Technical Findings, FW-02 | Low — the recommended task-notify pattern sidesteps needing this to be true at all |
| A4 | `CONFIG_SPIRAM_MEMTEST`'s exact Kconfig file location/help text at v5.3.1 (the fetch 404'd; existence/default inferred from general ESP-IDF knowledge + the ledger's own measured ~446ms figure) | ESP-IDF Technical Findings, FW-12 | Low — planner should re-confirm the symbol name via `idf.py menuconfig` search before relying on it in `sdkconfig.defaults` |
| A5 | Caddy (Go `crypto/tls`) supports TLS session resumption by default with no extra Caddyfile directive | FW-10, Caddy-side support | Medium — if false, the cross-deep-sleep RTC persistence work would have no server-side counterpart to resume against, wasting the effort; the hardware session's own handshake observation step is the direct check for this |
| A6 | `0x13000`-`0x20000` in `partitions.csv` is genuinely free and a new 0x1000 "secret" NVS partition there won't trip an `idf.py partition-table` validation warning | Architecture Patterns, partitions.csv | Low — caught immediately at build time if wrong, before any flashing occurs |

## Open Questions

1. **Exact `mbedtls_ssl_session_save()` buffer size against the VPS's actual TLS 1.2/1.3 negotiation and Caddy's ticket format**
   - What we know: the API exists and is designed for this; typical sizes are hundreds of bytes to a few KB.
   - What's unclear: the concrete number for this specific server/cert-chain/TLS-version combination.
   - Recommendation: measure it directly during the hardware session (call the save function with a generous scratch buffer and log the reported length) before finalizing the RTC memory reservation size.

2. **Whether the FreeRTOS tick suspends (and therefore TWDT timing pauses) during `esp_light_sleep_start()`**
   - What we know: light sleep clock-gates the CPU but the mechanism's interaction with an *armed, subscribed* TWDT during a ~90s light sleep wasn't independently confirmed in this session.
   - What's unclear: whether a long light sleep inside the panel-guard wait could itself trip the 60s TWDT if the main task stays subscribed throughout.
   - Recommendation: either unsubscribe the main task from TWDT for the duration of that specific wait, or test it explicitly as its own hardware-session scenario.

3. **Whether `firmware/build.sh`'s container mount should change to include the repo root (for `git describe`), or whether resolving the version on the host is preferable**
   - What we know: the current mount (`firmware/` only) cannot see `.git`.
   - What's unclear: whether changing the mount has any side effect on the rest of the (already-working) build invocation.
   - Recommendation: resolve on the host and pass via `-D`, per this research's recommendation — lower blast radius than changing the mount.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | `firmware/build.sh` (containerised ESP-IDF build) | Not probed this session (research is code/doc analysis only, no build was run) | — | None if missing — build cannot proceed without it; this is a pre-existing project dependency, not new to this phase |
| `esptool`, `parttool.py`, `nvs_partition_gen.py` | `firmware/flash.sh`, new `firmware/provision.sh` | `parttool.py`/`nvs_partition_gen.py` ship inside the pinned container image; `esptool` is a host-side dependency `flash.sh` already requires (`command -v esptool`) | — | None documented — `flash.sh` already exits with an install hint if missing |
| Real EE02 hardware + USB serial | The entire hardware-verification plan | Only available to the developer during the single hardware session | — | None — this is why the phase batches everything into one session |
| Network path to the real VPS (`skypane-byos.service`) | FW-10's TLS-over-internet measurement, FW-09's production DHCP re-measurement | Assumed available (existing deployed service per `deploy/README.md`) | — | If unreachable during the session, fall back to measuring against the LAN stub only and note the TLS-over-internet comparison as deferred |

**Missing dependencies with no fallback:** none identified beyond the pre-existing Docker/hardware dependencies this project already has.

**Missing dependencies with fallback:** VPS network path (falls back to LAN-stub-only measurement, with the production comparison explicitly deferred rather than silently skipped).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Plain C, `assert()`-based, compiled with the system `cc` — no test framework dependency (matches `test_backoff.c`/`test_panel_guard.c`/`test_api_base.c`/`test_battery_math.c`'s existing pattern) |
| Config file | none — `firmware/tests/run_host_tests.sh` is itself the runner/config |
| Quick run command | `bash firmware/tests/run_host_tests.sh` (currently ~0.35s per the audit ledger's measured baseline) |
| Full suite command | same command — the host suite is already the full suite; the containerised `firmware/build.sh` build is a separate, slower (Docker pull + full compile) signal, not part of "quick" |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FW-01 | Abnormal reset reasons map to "treat as failure" | unit (host) | new `tests/test_reset_reason.c` (pure classification function) | ❌ Wave 0 |
| FW-02 | Deadline-expiry decision is pure and correct at boundary values | unit (host) | new `tests/test_wake_deadline.c` | ❌ Wave 0 |
| FW-03 | 401/403 classification is distinct from generic status error | unit (host) | extend `tests/test_validate.c` or a small `tests/test_http_classify.c` | ❌ Wave 0 |
| FW-04 | `sleep_s` > 86400 rejected | unit (host) | extend/replace validation logic once extracted per FW-06; covered by `tests/test_validate.c` | ❌ Wave 0 (currently untested — validation lives inline in `api_client.c`, not host-testable as-is) |
| FW-06 | Response validators + sleep decision, pure and host-tested | unit (host) | `tests/test_validate.c`, `tests/test_sleep_decision.c` | ❌ Wave 0 |
| FW-07 | `http://` rejected when `CONFIG_SKYPANE_ALLOW_HTTP=n`, accepted when `y`; `sdkconfig.defaults` doesn't enable it | unit (host) + static check | `tests/test_validate.c` (both Kconfig states, compiled twice) + a small shell/grep check of `sdkconfig.defaults` (can run inside `run_host_tests.sh` or as a separate CI step) | ❌ Wave 0 |
| FW-08 | Registry gates re-enrolment correctly (registered+match, registered+mismatch, unregistered) | integration (subprocess + real HTTP, matching `test_poll_cycle.py`'s existing pattern) | new checks appended to `stub-server/test_poll_cycle.py` or a sibling file, run via `python3 stub-server/test_poll_cycle.py` (or its sibling) | ❌ Wave 0 |
| FW-09 | DHCP config present, correct Kconfig keys | build-only (no automated behavioral test possible for wall-clock DHCP timing) | n/a — hardware-only for the actual timing claim; a static grep-for-Kconfig-key check is possible and cheap | manual-only for the timing; trivial for presence |
| FW-10 | Keep-alive reduces handshake count within a wake | integration (LAN stub, count TCP connections opened) | possible via `stub-server/test_poll_cycle.py` counting `do_GET`/`do_POST` invocations against distinct sockets, though this only proves "the stub saw fewer connections," not wall-clock savings | manual-only for wall-clock; partially automatable for connection-count |
| FW-11 | 8-sample average, read-before-Wi-Fi ordering | unit (host, if the averaging math is extracted as a pure function) | extend `tests/test_battery_math.c` | ❌ Wave 0 (ordering itself — "before Wi-Fi" — is not unit-testable, only the averaging math is) |
| FW-12 | `CONFIG_SPIRAM_MEMTEST=n` present; light-sleep substitution compiles | build-only + hardware for actual timing | grep-based sdkconfig check | manual-only for the actual power/latency impact |
| FW-13/14/15 | Dead code removed, helpers deduplicated, `PROJECT_VER` resolves | build-only (compiles clean, `X-Fw-Version` header reflects a real git describe on a real build) | `firmware/build.sh` + inspect `esp_app_get_description()->version` in a captured boot log | hardware-only to observe the final reported string |

### Sampling Rate
- **Per task commit:** `bash firmware/tests/run_host_tests.sh` (sub-second, run after every pure-logic file change)
- **Per wave merge:** `bash firmware/tests/run_host_tests.sh` + `bash firmware/build.sh` (containerised compile, proves the ESP-IDF-dependent code still builds) + `python3 stub-server/test_poll_cycle.py` (or its FW-08 sibling)
- **Phase gate:** All of the above green, **plus** the single `checkpoint:human-verify` hardware-session plan, before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `firmware/tests/test_reset_reason.c` — covers FW-01's classification
- [ ] `firmware/tests/test_wake_deadline.c` — covers FW-02's deadline-math boundary conditions
- [ ] `firmware/tests/test_validate.c` — covers FW-04, FW-06, FW-07 (both `CONFIG_SKYPANE_ALLOW_HTTP` states)
- [ ] `firmware/tests/test_sleep_decision.c` — covers FW-06's sleep-duration decision
- [ ] New device-registry test coverage in `stub-server/` (name at planner's discretion) — covers FW-08's three registry outcomes (registered+match, registered+mismatch, unregistered)
- [ ] `firmware/tests/run_host_tests.sh` — extend with `run_suite` lines for each new `tests/test_*.c` file added above
- [ ] `.github/workflows/firmware.yml` — add a `bash firmware/tests/run_host_tests.sh` step (fast, should run before the slower Docker build step for fail-fast ordering); do **not** touch `.github/workflows/ci.yml`

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | Yes | Per-device secret + server-side registry gate (D-34-01); bearer token issuance unchanged (already 64 lowercase-hex, already validated on the device side in `api_client.c:229-249`) |
| V3 Session Management | Yes (device "session" = bearer token) | Token revocation-on-401/403 with clean re-enrolment (FW-03); server-side, a re-enrol replaces (revokes) the prior token for that MAC |
| V4 Access Control | Yes | Registry membership check gates who may (re-)enrol a given MAC — an unregistered MAC cannot obtain a token at all, closing the "anyone holding the old shared secret" hole FW-08 exists to fix |
| V5 Input Validation | Yes | FW-06's pure validators (`sleep_s` bound, hash format, URL scheme, token shape) already exist and are being extended, not introduced from scratch |
| V6 Cryptography | Yes | `hmac.compare_digest` for constant-time secret comparison (never hand-rolled `==`); TLS via ESP-IDF's mbedtls with a scoped custom CA bundle, never a hand-rolled cert check; no flash/NVS encryption per D-A1's explicit rejection (irreversible eFuse burn is out of scope, not a v1.0 gap) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Attacker knows a victim device's MAC (visible on the wire in every Wi-Fi frame, not a secret) and attempts to re-enrol/hijack it | Spoofing | Registry gate requires the paired per-device secret, not just the MAC, to succeed (D-34-01) — MAC alone is insufficient by design |
| Timing side-channel on the secret-hash comparison, letting an attacker binary-search a valid secret | Information Disclosure | `hmac.compare_digest` (constant-time), matching existing project convention in `companion/auth.py` |
| Registry/state file (`byos_state.json`/new registry file) leaks (backup, misconfigured permissions, etc.) | Information Disclosure | Only secret **hashes** stored, never the plaintext secret (D-34-01 explicit); a leaked hash cannot re-derive the device's actual secret given it's a machine-generated high-entropy token |
| Flood of setup requests against one MAC with wrong secrets (no rate limiting in the stub server today) | Denial of Service | Accepted gap consistent with `byos_server.py`'s own "reference, not a product" framing; full rate limiting is Phase 37 (SEC) scope, not this phase's — flag as an explicit non-goal rather than silently absent |
| Downgrade to plaintext HTTP in production if `CONFIG_SKYPANE_ALLOW_HTTP` is accidentally left on | Tampering / Information Disclosure | Default `n`, host-tested in both states, plus a static check that `sdkconfig.defaults` doesn't set it to `y` (FW-07/D-34-04) |
| A dev-only fault-injection hook (for the hardware session's panic/hang triggers) accidentally shipping enabled in a production image | Elevation of Privilege / Tampering | Kconfig-gated, default off (CONTEXT.md's own locked constraint); recommend the same static `sdkconfig.defaults`-doesn't-enable-it host-test pattern used for `CONFIG_SKYPANE_ALLOW_HTTP` |
| Custom ISRG-only CA bundle becomes stale if Let's Encrypt ever rotates root CAs and Caddy's chain changes | Denial of Service (device can no longer connect at all until reflashed) | Not a coding fix — an operational risk to document explicitly (e.g., in `firmware/VENDOR.md` or a deploy note) so a future operator knows *why* a device might suddenly fail TLS validation and that the fix is a firmware update, not a server-side one |

## Hardware-Session Script Outline

(For the planner's single `checkpoint:human-verify` plan — this is an outline, not the final task list.)

1. **Pre-flight:** re-measure the "before" no-change wake baseline on the *old* (pre-phase) image if not reusing `hardware/logs/backoff-run.log` as-is (CONTEXT.md's stated fallback).
2. **Build:** `firmware/build.sh` (ee02 profile).
3. **Provision:** `firmware/provision.sh <port>` — generates the per-device secret, writes the dedicated "secret" NVS partition via `nvs_partition_gen.py` + `parttool.py write_partition --partition-name=secret`, prints the MAC + secret-hash registry line.
4. **Register:** add that MAC/hash to the registry — **on whichever server the session's later scenarios target** (local stub first for most scenarios; the real VPS only for the FW-10/FW-09 production-path measurements) — before any scenario that depends on enrolment succeeding.
5. **Flash:** `firmware/flash.sh <port>` (includes its own read-back verification).
6. **Monitor:** `firmware/monitor.sh <port> hardware/logs/<UTC-timestamp>-phase34.log` running throughout.
7. **Trigger scenarios** (each captured in the same or a fresh monitor log, plus the server-side log tail):
   - **Panic/brownout → backoff:** use the Kconfig-gated dev-only fault-injection hook to force an `ESP_RST_PANIC` (or physically interrupt power briefly, no battery attached, mirroring `hardware/BACKOFF-OBSERVATION.md`'s existing power-cycle method) — confirm the reset-reason log line and that the next sleep is a backoff interval, not the server's normal cadence.
   - **Hung wake bounded by the deadline:** fault-injection hook spins forever inside a representative blocking stage — confirm either the TWDT panics within ≤60s (if the hang is inside a TWDT-subscribed stage) or the `esp_timer` deadline gracefully deep-sleeps-with-backoff within the sized ~270-300s budget (if simulating "slow but technically still executing").
   - **Token revoked → 401 → re-enrol, no reflash:** delete/revoke the device's token server-side, confirm the device's next `/display` poll logs the new `step=auth` (or chosen token), then confirm the wake *after that* successfully re-enrols using the same on-device secret with no reflash.
   - **`sleep_s` > 86400 rejected:** point the device at a stub response with an oversized `sleep_s`, confirm `step=json`.
   - **No-change wake timed before/after:** compare against the pre-flight baseline, both against the LAN stub (isolates DHCP/memtest) and the real VPS (isolates TLS), per the three-way comparison recommended above.
   - **Battery reading vs. multimeter:** read the device's `battery mv=` diagnostic serial line, compare directly against a multimeter reading at the pack/JST connector.
8. **Capture and commit:** serial logs under `hardware/logs/`, server-side log excerpts, and a results write-up in a new or extended hardware doc (mirroring `hardware/BACKOFF-OBSERVATION.md`'s existing verdict-first structure) — disclose any partial/failed sub-check honestly, as that document's own precedent already does.

## Sources

### Primary (HIGH confidence)
- `raw.githubusercontent.com/espressif/esp-idf` at the `v5.3.1` git tag — `components/lwip/Kconfig`, `components/esp_system/Kconfig`, `components/mbedtls/Kconfig`, `components/esp-tls/esp_tls.h`, `components/esp_http_client/include/esp_http_client.h` (fetched directly, quoted verbatim above)
- This repository's own source: `firmware/main/*.c/.h`, `firmware/*.csv/.sh/.defaults`, `firmware/VENDOR.md`, `stub-server/byos_server.py`, `stub-server/test_poll_cycle.py`, `deploy/*`, `hardware/BATTERY-RUN.md`, `hardware/BACKOFF-OBSERVATION.md`, `hardware/logs/backoff-run.log`, `.github/workflows/firmware.yml`

### Secondary (MEDIUM confidence)
- `docs.espressif.com` ESP-IDF v5.3.1/latest programming guide pages: `esp_timer.html`, `esp_http_client.html`, `esp_crt_bundle.html`, `sleep_modes.html`, `build-system.html` (fetched/searched; cross-checked against the primary GitHub source where the claim was load-bearing)
- mbedtls project documentation and forum discussion of `mbedtls_ssl_session_save`/`_load` as the standard session-persistence pattern (web search, not independently fetched from a single canonical mbedtls doc page)

### Tertiary (LOW confidence)
- `CONFIG_SPIRAM_MEMTEST`'s exact Kconfig source location/help text (the specific file guessed 404'd; existence/default inferred from general knowledge + the audit ledger's own measured figure) — flagged in the Assumptions Log (A4)
- Caddy/Go `crypto/tls` default session-resumption behavior (not independently verified against this project's actual `deploy/Caddyfile` or a live handshake capture) — flagged in the Assumptions Log (A5)

## Metadata

**Confidence breakdown:**
- Standard stack / tooling (parttool.py, nvs_partition_gen.py, mbedtls session-save API existence): HIGH — verified against primary ESP-IDF source and documented mbedtls API
- Architecture (deadline sizing, partition layout, keep-alive pattern): MEDIUM-HIGH — derived from code-declared constants and verified Kconfig ranges, but the deadline number and the ~28s hypothesis are not yet hardware-confirmed (that confirmation is this phase's own final step, by design)
- Pitfalls (TWDT range, esp_tls struct layout, git-describe-in-container, 401-branch-ordering): HIGH — each is grounded in a specific, cited source-code or Kconfig fact, not speculation

**Research date:** 2026-09-23
**Valid until:** ~30 days (ESP-IDF 5.3.1 is a pinned, stable toolchain; the Kconfig/API facts here are unlikely to drift, but the firmware source line numbers will drift again as soon as unrelated commits land — re-grep before trusting exact line citations if this research is consumed more than a few weeks after this date)
