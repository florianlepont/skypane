# Phase 34: Firmware — resilience, power, security, cleanup - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning
**Source:** Audit ledger `.planning/audits/2026-09-23-code-audit.md` (FW-01..FW-15, decisions D-A1..D-A6) + four decisions taken with the developer at plan time (D-34-01..D-34-04)

<domain>
## Phase Boundary

Firmware track of the 2026-09-23 audit remediation (`firmware/`, ESP-IDF 5.3.1, built with `firmware/build.sh` in `espressif/idf:v5.3.1`), plus the byos enrolment change FW-08 needs (`stub-server/byos_server.py` setup handler + a device registry) and the CI job that runs the firmware host tests.

The frame must recover on its own from every failure the audit found (crash/brownout/WDT reset, hung wake, rejected token, absurd `sleep_s`), wake for less time, read its battery honestly and enrol with a per-device secret. Every requirement FW-01..FW-15 is in scope; nothing is deferred (D-A5: 100 % of findings, low severity included).

Independent of phases 32–33 and run in parallel with them. Phase 32 owns `.github/workflows/ci.yml` and the Python test framework; this phase does NOT touch `ci.yml` — firmware host tests go into `.github/workflows/firmware.yml`. byos tests for FW-08 must be written so they survive Phase 32's pytest migration (see Claude's Discretion).

All hardware verification is batched into ONE session on the real device, performed by the developer, planned as a single `checkpoint:human-verify` plan at the end of the phase with a precise script (what to flash, what to trigger, what to capture, where to store the logs).
</domain>

<decisions>
## Implementation Decisions

### Inherited from the audit (locked)
- **D-A1** — Per-device enrolment secret; byos refuses re-enrolment of a known MAC by anyone not holding that MAC's secret. **No flash encryption, no NVS encryption** (burns eFuses, irreversible).
- **D-A3** — Everything written in this phase (code, comments, commit messages, docs) is in English; comments keep only the *why* and invariants, no plan/ticket history (Phase 35 purges the rest — do not add new history comments).
- **D-A6** — No git history rewrite.

### D-34-01 — Re-enrolment rule (resolves the FW-03 ↔ FW-08 conflict)
- byos keeps a device registry: MAC → hash of that device's enrolment secret (never the secret itself).
- `POST /device/v1/setup` for a MAC:
  - MAC in the registry AND the presented secret matches that MAC's hash → issue a NEW token, revoke the MAC's previous token, 200.
  - MAC in the registry, secret wrong (including the old shared secret, or another device's secret) → refused (401/403), existing token untouched.
  - MAC not in the registry → refused. Enrolment is only possible for devices the operator has registered.
- Comparison with `hmac.compare_digest`. The old shared `--secret` / `SKYPANE_BYOS_SECRET` path is retired (migration documented in `deploy/README.md` / `skypane.env.example`).
- Consequence for FW-03: a 401/403 on `/display` (or `/log`) makes the device erase `FP_NVS_DEVICE_TOKEN`; the next wake re-enrols with its own secret and heals with no reflash and no operator action.

### D-34-02 — Secret provisioning: NVS via a serial script
- A host script (e.g. `firmware/provision.sh`, name at planner's discretion) generates a random per-device secret, writes it into the device's NVS over USB (NVS partition image via `nvs_partition_gen.py` + `esptool`/`parttool`, or equivalent inside the `espressif/idf:v5.3.1` container), and prints the registry line (MAC + secret hash) to add on the server.
- New NVS key in `firmware/main/nvs_schema.h` for the enrolment secret, in the existing `skypane` namespace (migrate in place, never rename the namespace).
- `SKYPANE_SETUP_SECRET` is removed from `secrets.example.h`/`secrets.h`; the firmware image becomes identical for every device. A device with no secret in NVS logs a clear error and backs off (it cannot enrol).
- Provisioning must not erase the existing token/hash/backoff keys unless explicitly asked.

### D-34-03 — DHCP (FW-09)
- `CONFIG_LWIP_DHCP_RESTORE_LAST_IP=y` and the DHCP ARP check disabled (`CONFIG_LWIP_DHCP_DOES_ARP_CHECK=n`), measured on hardware.
- Fallback: optional static IP (address, gateway, netmask, DNS) from `secrets.h`, compiled in only when defined, **disabled by default**. Used only if the measured gain of the default path is insufficient — the hardware session measures both where possible.

### D-34-04 — https-only (FW-07)
- New Kconfig option `CONFIG_SKYPANE_ALLOW_HTTP`, default `n`. With `n`, URL validation rejects `http://` for the API base and image URLs. Setting it to `y` is an explicit dev-build opt-in for the laptop stub.
- The production build is proven to have it off (host test of the pure validator in both modes + a check that `sdkconfig.defaults` does not enable it).
- CA bundle: `CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE` (or CMN→custom) with a custom bundle containing only the ISRG roots (ISRG Root X1, ISRG Root X2) the VPS's Let's Encrypt chain uses (Caddy — `deploy/Caddyfile`).

### Per-requirement remediation (from the ledger — locked)
- **FW-01** `esp_reset_reason()` checked at boot; `ESP_RST_PANIC`, `ESP_RST_INT_WDT`, `ESP_RST_TASK_WDT`, `ESP_RST_WDT`, `ESP_RST_BROWNOUT` (planner confirms the list) → increment `FP_NVS_BACKOFF_N` and deep-sleep for the backoff duration instead of polling at once; the boot reason label stops lying (`power-on`). `epd_init` returns `esp_err_t` instead of `ESP_ERROR_CHECK` (`epd13in3e.c:167,172,185,192`).
- **FW-02** Whole-wake deadline: one-shot `esp_timer` armed at boot; on expiry → record failure (backoff) and deep sleep. A real task watchdog (`CONFIG_ESP_TASK_WDT_PANIC=y`, main task subscribed via `esp_task_wdt_add`, fed at safe points) so a hang panics → FW-01 backoff. Wrong comment in `sdkconfig.defaults:21-23` corrected. The deadline must exceed the legitimate worst-case wake (panel spacing wait + blit) — planner derives the number from `panel.c`/`panel_guard` budgets.
- **FW-03** 401/403 on authenticated calls → erase `FP_NVS_DEVICE_TOKEN`, distinct error code (e.g. `FP_ERR_HTTP_AUTH`) and distinct `step=` value; next wake re-enrols (D-34-01).
- **FW-04** `sleep_s` > 86400 → JSON error (`step=json`), not accepted.
- **FW-05** `esp_http_client_write` / `esp_http_client_fetch_headers` returns checked (`api_client.c:154-156`), `busy_wait("POF")` checked (`epd13in3e.c:265`), each mapped to the correct `step=`.
- **FW-06** Pure helpers (no ESP-IDF includes) for: response validation (image hash format, URL, `sleep_s` range, `led_enabled` type, token format), download size/SHA gate, and the sleep decision (which sleep duration given result/backoff/`sleep_s`/reset reason). Host tests in `firmware/tests/`, wired into `run_host_tests.sh`, and `run_host_tests.sh` run in CI (`firmware.yml`) — success criterion 3.
- **FW-07** see D-34-04.
- **FW-08** see D-34-01 / D-34-02.
- **FW-09** see D-34-03.
- **FW-10** One keep-alive `esp_http_client` reused for `/display` + image download; TLS session ticket/session reuse kept in RTC memory across deep sleep (`esp_tls` client session); a diagnostic wake-duration line logged **without changing any line of the Log Line Contract** (`firmware/VENDOR.md`); the ~28 s per-cycle overhead in `hardware/BATTERY-RUN.md:333-345` explained (in research or in the hardware session results).
- **FW-11** Battery read once, before Wi-Fi starts, as an 8-sample average; the value is carried to the `X-Battery-Mv` header.
- **FW-12** `CONFIG_SPIRAM_MEMTEST=n`; the 800 µs per-row busy-wait (`epd13in3e.c:234`) shortened only if the panel datasheet/driver reference allows (else keep and document why); timed light sleep instead of fully-awake waiting during the refresh-spacing wait (`panel.c:97`).
- **FW-13** `api_base.c`: use `fp_api_base_normalize` (trailing slash → no `//device`) or delete it with its test; delete `fp_api_post_logs` if still unused; stop requiring the ignored `reset` field (`api_client.c:330`); drop orphan `CONFIG_FP_PROVISION_TIMEOUT_S` / `FP_FACTORY_PREP`; disable app rollback (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`) until OTA exists. Update `firmware/VENDOR.md` accordingly.
- **FW-14** One helper each for: hex check (`api_client.c:66-71,235-240`), NVS open/read/close (×3), HTTP client config (×3).
- **FW-15** `PROJECT_VER` derived from `git describe` in `firmware/CMakeLists.txt` (with a fallback when git is unavailable in the build container).

### Hardware verification (locked format)
- ONE final plan, `autonomous: false`, a single `checkpoint:human-verify` the developer performs, with a step-by-step script: build command, flash command, provisioning command, registry step on the VPS, then each trigger (induced panic/brownout or WDT via a dev-only trigger, forced hang for the deadline, token revoked server-side → 401 → re-enrol, `sleep_s` > 86400 from a stub, no-change wake timed before/after, battery reading compared to a multimeter), what to capture (serial log via `firmware/monitor.sh`, server log), and where to commit the captures (`hardware/logs/…` + a results section in a hardware doc).
- The "before" no-change wake baseline is the existing ≈ 4.4 s / ≈ 3.0 s DHCP measurement (`hardware/logs/backoff-run.log`) unless the developer re-measures it on the old image at the start of the session.
- Any dev-only fault-injection hook must be compiled out of production builds (Kconfig, default off).

### Claude's Discretion
- Plan split/waves, helper file names, exact error-code names and `step=` spellings (must stay compatible with the Log Line Contract; any NEW step value documented in `firmware/VENDOR.md`).
- Registry storage format (e.g. `state/devices.json` MAC → `sha256`/`scrypt` hash) and the operator command to add/remove a device (a small CLI in `stub-server/` is fine).
- byos tests for the new setup rules: follow the existing byos test harness, written as plain functions/asserts that migrate trivially to pytest (Phase 32 runs in parallel).
- Whether TLS reuse uses session tickets or session IDs — whichever the VPS (Caddy) and `esp_tls` support.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit and scope
- `.planning/audits/2026-09-23-code-audit.md` — ledger: FW-01..FW-15 findings with file:line evidence, D-A1..D-A6, measured baseline
- `.planning/ROADMAP.md` § "Phase 34" — goal and 5 success criteria
- `.planning/REQUIREMENTS.md` § "Audit remediation" — FW-01..FW-15

### Firmware
- `firmware/VENDOR.md` — upstream derivation, local modifications list, **Log Line Contract** (must stay byte-compatible)
- `firmware/main/app_main.c`, `state_machine.c`, `api_client.c`, `panel.c`, `panel_guard.c`, `epd13in3e.c`, `wifi.c`, `battery.c`, `backoff.c`, `api_base.c`, `nvs_schema.h`, `Kconfig.projbuild`
- `firmware/sdkconfig.defaults`, `firmware/sdkconfig.ee02.defaults`, `firmware/partitions.csv`, `firmware/CMakeLists.txt`
- `firmware/tests/run_host_tests.sh` + existing `test_*.c` — host-test pattern
- `firmware/build.sh`, `firmware/flash.sh`, `firmware/monitor.sh` — build/flash/monitor tooling
- `.github/workflows/firmware.yml` — firmware CI (host tests to be added here)

### Server side of enrolment
- `stub-server/byos_server.py` — `/device/v1/setup` (≈ :580-593), `bearer_ok`, `--secret`
- `deploy/skypane-byos.service`, `deploy/skypane.env.example`, `deploy/README.md` — secret plumbing to migrate

### Hardware evidence
- `hardware/logs/backoff-run.log` — the 4.4 s / 3.0 s DHCP baseline
- `hardware/BATTERY-RUN.md` (:333-345) — the ~28 s unexplained per-cycle overhead
- `hardware/BACKOFF-OBSERVATION.md`, `hardware/BRINGUP-LOG.md` — prior hardware-session format
</canonical_refs>

<specifics>
## Specific Ideas

- Cross-phase touchpoints on `byos_server.py`: Phase 36 (INT-05 content-addressed images, INT-06 input validation / `hmac.compare_digest` for bearer tokens), Phase 37 (SEC-06 loopback bind, SEC-07 secret via env) and Phase 39 edit the same file later. Keep the FW-08 change confined to the setup handler + registry so those phases merge cleanly; SEC-07's "secret via env" becomes moot for the shared secret this phase retires — note it in the SUMMARY for Phase 37.
- The firmware host tests are currently NOT run in CI (no reference to `run_host_tests.sh` in `.github/`), even though success criterion 3 requires it.
</specifics>

<deferred>
## Deferred Ideas

None — every FW finding is v1.0 scope (D-A5). Flash/NVS encryption is rejected, not deferred (D-A1).
</deferred>

---

*Phase: 34-firmware-resilience-power-security-cleanup*
*Context gathered: 2026-09-23 from the audit ledger + plan-time decisions with the developer*
