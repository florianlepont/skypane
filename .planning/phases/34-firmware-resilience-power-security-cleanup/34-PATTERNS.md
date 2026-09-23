# Phase 34: Firmware — resilience, power, security, cleanup - Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 33 (new + modified)
**Analogs found:** 33 / 33

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `firmware/main/reset_reason.c/.h` (new, FW-01) | utility (pure classifier) | transform | `firmware/main/backoff.c/.h` | exact |
| `firmware/main/wake_deadline.c/.h` (new, FW-02) | utility (pure decision) | transform | `firmware/main/panel_guard.c/.h` | exact |
| `firmware/main/validate.c/.h` (new, FW-06/FW-04/FW-07) | utility (pure validators) | transform | `firmware/main/api_base.c/.h` | exact |
| `firmware/main/sleep_decision.c/.h` (new, FW-06) | utility (pure decision) | transform | `firmware/main/panel_guard.c/.h` | exact |
| `firmware/main/secret_provision.c/.h` (new, D-34-02) | utility (ESP-IDF NVS I/O) | file-I/O | `firmware/main/battery.c/.h` (+ `api_client.c`'s `nvs_get_string` helper) | role-match |
| `firmware/main/nvs_schema.h` (modified) | config | — | itself (existing) | exact |
| `firmware/main/api_client.c/.h` (modified, FW-03/05/10/14) | service (HTTP client) | request-response | itself (existing) | exact |
| `firmware/main/app_main.c` (modified, FW-01/02) | controller (boot/wake dispatcher) | event-driven | itself (existing) | exact |
| `firmware/main/state_machine.c/.h` (modified, FW-03/D-34-01/02) | controller (poll orchestration) | request-response | itself (existing) | exact |
| `firmware/main/epd13in3e.c` (modified, FW-01/05/12) | driver (SPI/panel I/O) | event-driven | itself (existing) | exact |
| `firmware/main/panel.c` (modified, FW-12 light sleep) | driver (panel guard glue) | event-driven | itself (existing) | exact |
| `firmware/main/battery.c` (modified, FW-11) | service (ADC read) | request-response | itself (existing) | exact |
| `firmware/main/wifi.c` (reference only, no change expected) | service (Wi-Fi/SNTP) | event-driven | itself (existing) | exact |
| `firmware/main/Kconfig.projbuild` (modified, D-34-04/FW-13) | config | — | itself (existing) | exact |
| `firmware/sdkconfig.defaults` (modified, FW-02/07/12/13) | config | — | itself (existing) | exact |
| `firmware/partitions.csv` (modified, D-34-02) | config | — | itself (existing) | exact |
| `firmware/CMakeLists.txt` (modified, FW-15) | config | — | itself (existing) | exact |
| `firmware/build.sh` (modified, FW-15 `-DPROJECT_VER`) | config/tooling | batch | itself (existing) | exact |
| `firmware/provision.sh` (new, D-34-02) | tooling (host script) | file-I/O | `deploy/provision.sh` (idempotent bash provisioning) + `firmware/flash.sh` (esptool/serial-port host tooling) | role-match |
| `firmware/main/certs/isrg-root-x1.pem`, `isrg-root-x2.pem` (new, FW-07) | config (static data) | — | none (no analog; plain vendored PEM files) | no-analog |
| `firmware/main/secrets.example.h` (modified, D-34-02 remove secret macro) | config | — | itself (existing) | exact |
| `firmware/main/api_base.c/.h` (modified/possibly deleted, FW-13) | utility (pure) | transform | itself (existing) | exact |
| `firmware/tests/test_reset_reason.c` (new) | test | transform | `firmware/tests/test_backoff.c` | exact |
| `firmware/tests/test_wake_deadline.c` (new) | test | transform | `firmware/tests/test_panel_guard.c` | exact |
| `firmware/tests/test_validate.c` (new) | test | transform | `firmware/tests/test_api_base.c` | exact |
| `firmware/tests/test_sleep_decision.c` (new) | test | transform | `firmware/tests/test_panel_guard.c` | exact |
| `firmware/tests/run_host_tests.sh` (modified) | tooling (test runner) | batch | itself (existing) | exact |
| `.github/workflows/firmware.yml` (modified) | CI config | batch | itself (existing) | exact |
| `stub-server/byos_server.py` (modified, FW-08/D-34-01) | controller (HTTP handler) | request-response | itself (existing, `Handler.do_POST`/`bearer_ok`/`load_state`/`save_state`) | exact |
| `stub-server/devices_cli.py` (new, D-34-01 registry CLI) | tooling (stdlib CLI) | CRUD | `stub-server/make_test_panel.py` (argparse, stdlib-only CLI) + `byos_server.py`'s `state_path`/`load_state`/`save_state` | role-match |
| `stub-server/test_devices_registry.py` (new, or appended to `test_poll_cycle.py`) | test (integration harness) | request-response | `stub-server/test_poll_cycle.py` (`check()`/`Harness` pattern) | exact |
| `deploy/skypane-byos.service` (modified, remove `--secret`) | config | — | itself (existing) | exact |
| `deploy/skypane.env.example` / `deploy/README.md` (modified, secret migration) | config/docs | — | itself (existing) | exact |
| `firmware/VENDOR.md` (modified, FW-13 + new step tokens) | docs | — | itself (existing, "Log Line Contract" + vendoring table) | exact |
| `hardware/<new-or-extended-doc>.md` (new, hardware-session results) | docs | — | `hardware/BACKOFF-OBSERVATION.md` | exact |

## Pattern Assignments

### `firmware/main/reset_reason.c/.h` (utility, transform) — FW-01

**Analog:** `firmware/main/backoff.c` + `firmware/main/backoff.h`

Backoff is the project's template for a tiny, header-documented, pure-logic module with zero ESP-IDF includes:

```c
// firmware/main/backoff.h
#pragma once
#include <stdint.h>

/* min(2^n * 5 min, 6 h), in seconds. n = consecutive failures. */
uint32_t fp_backoff_seconds(uint8_t n);
```
```c
// firmware/main/backoff.c
#include "backoff.h"

#define BACKOFF_BASE_S (5u * 60u)
#define BACKOFF_MAX_S  (6u * 3600u)

uint32_t fp_backoff_seconds(uint8_t n)
{
    if (n >= 7) {
        return BACKOFF_MAX_S;
    }
    uint32_t s = BACKOFF_BASE_S << n;
    return s > BACKOFF_MAX_S ? BACKOFF_MAX_S : s;
}
```

**Apply this shape to `reset_reason.c/.h`:** a single pure function taking `esp_reset_reason_t` (the enum itself has no ESP-IDF *logic* dependency, only the type — RESEARCH.md already gives the exact body):

```c
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
Header doc comment style: copy `backoff.h`'s one-line contract comment above the declaration, and `nvs_schema.h`'s pattern of explaining *why* a value is classified the way it is (see below).

**Call site:** `app_main.c` already calls `esp_sleep_get_wakeup_cause()` right after `fp_panel_on_boot()` (line 128) — add the new `esp_reset_reason()` call and `boot_was_abnormal()` check immediately beside it, feeding the existing `backoff_n` increment path (lines 142-153) rather than adding a second backoff mechanism.

---

### `firmware/main/wake_deadline.c/.h` (utility, transform) — FW-02

**Analog:** `firmware/main/panel_guard.c` + `firmware/main/panel_guard.h`

`panel_guard.c` is the project's template for pure "given elapsed/remaining state, decide what happens next" arithmetic, ESP-IDF-free, with an enum result type and out-param details:

```c
// firmware/main/panel_guard.c (excerpt)
uint32_t fp_panel_guard_after_awake(uint32_t remaining_s, uint32_t elapsed_s)
{
    return elapsed_s >= remaining_s ? 0u : remaining_s - elapsed_s;
}
```
Header framing (`panel_guard.h` lines 32-47) documents *why* the module is separated from the I/O that drives it ("It lives apart from panel.c so it can be reasoned about and tested on a host: panel.c owns the retained state and the SPI, this owns the decisions.") — use the same framing for `wake_deadline.h`: the pure module answers "given `elapsed_us`/`budget_us`, expired?", and the `esp_timer` callback + `xTaskNotifyGive` wiring stays in `app_main.c` (or a small non-test-covered glue file), exactly like `panel.c` owns the SPI/RTC-memory side of `panel_guard.c`'s decisions.

Deadline vs. TWDT split (RESEARCH.md, already vetted against Kconfig `range 1 60`):
```c
esp_task_wdt_add(NULL);
...
esp_task_wdt_reset();  // after each blocking stage completes

static TaskHandle_t s_main_task;
static void IRAM_ATTR deadline_cb(void *arg) {
    xTaskNotifyGive(s_main_task);
}
```

---

### `firmware/main/validate.c/.h` (utility, transform) — FW-04, FW-06, FW-07

**Analog:** `firmware/main/api_base.c` + `firmware/main/api_base.h`

`api_base.c` is the exact precedent for "pure string/field validation, no ESP-IDF includes, so the host test can compile it with plain `cc`":

```c
// firmware/main/api_base.h (header doc pattern to copy)
/* BYOS server-URL normalization — pure string code, no ESP deps, so the
 * host test (tests/test_api_base.c) can compile it with plain cc. ...
 * Returns 0 on success (out valid), -1 on rejection (out untouched — ...) */
int fp_api_base_normalize(const char *raw, char *out, size_t cap);
```
```c
// firmware/main/api_base.c (excerpt — scheme-check idiom to reuse for
// fp_scheme_allowed() gating http:// under CONFIG_SKYPANE_ALLOW_HTTP)
size_t scheme = 0;
if (len >= 7 && !strncasecmp(raw, "http://", 7)) {
    scheme = 7;
} else if (len >= 8 && !strncasecmp(raw, "https://", 8)) {
    scheme = 8;
} else {
    return -1;
}
```

The validators FW-06 needs already exist inline in `api_client.c` and just need extraction (do not re-derive the logic, move it verbatim into the new pure module, adjusting only for a `bool CONFIG_SKYPANE_ALLOW_HTTP` compile-time gate on the scheme check):

- `image_hash_valid()` — `firmware/main/api_client.c:56-74` (exact `sha256:` + 64 lowercase-hex check)
- `url_valid()` — `firmware/main/api_client.c:78-88` (needs the `CONFIG_SKYPANE_ALLOW_HTTP` gate added, FW-07/D-34-04)
- `sleep_ok` inline expression — `firmware/main/api_client.c:320-323` (needs its upper bound changed from `4294967295.0` to `86400.0`, FW-04)
- token hex-check loop — `firmware/main/api_client.c:234-241` (duplicated once already; FW-14 dedup target — fold into one `fp_hex_token_valid(const char *s, size_t expected_len)` helper used by both the setup-response check and the NVS-read-back check)

Test file to copy from: `firmware/tests/test_api_base.c`'s structure (static `norm()` wrapper + a long list of `assert()` happy-path/rejection/boundary cases, one `printf("...: all cases pass\n")` at the end, `main()` returns 0/1 via the process exit).

---

### `firmware/main/sleep_decision.c/.h` (utility, transform) — FW-06

**Analog:** `firmware/main/panel_guard.c` + `firmware/main/panel_guard.h`

Same shape as `wake_deadline.c` above — reuse `fp_panel_guard_plan()`'s pattern of an enum-returning pure function plus an out-param for the derived numeric value:

```c
typedef enum {
    FP_PANEL_DRAW_NOW,
    FP_PANEL_DRAW_AFTER_WAIT,
    FP_PANEL_DRAW_BUSY,
} fp_panel_draw_plan_t;

fp_panel_draw_plan_t fp_panel_guard_plan(uint32_t remaining_s, bool drawing,
                                         uint32_t max_wait_s,
                                         uint32_t *wait_s);
```
Apply the same shape to the sleep-duration decision: a pure function taking `(result, backoff_n, reset_reason_was_abnormal, server_sleep_s)` and returning the seconds to sleep, mirroring how `app_main.c` currently branches between `fp_backoff_seconds(backoff_n)` (lines 142-153) and the server-supplied `sleep_s` (lines 156-177) — extracting that branch into a testable pure function is the FW-06 ask.

---

### `firmware/main/secret_provision.c/.h` (service, file-I/O) — D-34-02

**Analog:** `firmware/main/battery.c` (ESP-IDF I/O wrapper: open a resource, read, always release, degrade cleanly on any failure) + `api_client.c`'s `nvs_get_string()` helper for the NVS-read shape.

```c
// firmware/main/api_client.c:35-46 — the exact NVS-open/read/close idiom
// to reuse (and, per FW-14, deduplicate into one shared helper used by
// api_client.c AND secret_provision.c rather than copied a third time)
static esp_err_t nvs_get_string(const char *key, char *out, size_t cap)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open(FP_NVS_NAMESPACE, NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    size_t len = cap;
    err = nvs_get_str(nvs, key, out, &len);
    nvs_close(nvs);
    return err;
}
```
```c
// firmware/main/battery.c — degrade-to-sentinel-on-failure idiom to copy
// (no ESP_ERROR_CHECK; every failure path logs a warning and returns a
// safe default instead of aborting boot)
esp_err_t err = gpio_config(&en_cfg);
if (err != ESP_OK) {
    ESP_LOGW(TAG, "battery enable-line config failed: %d", err);
    s_cached_mv = 0;
    return 0;
}
```
D-34-02 requires reading from a **separate, dedicated NVS partition** (not the `skypane` namespace's own `nvs` partition) — the read call therefore needs its own `nvs_flash_init_partition("secret")` / `nvs_open_from_partition("secret", FP_NVS_NAMESPACE, NVS_READONLY, &nvs)` (per RESEARCH.md's partition-layout recommendation), not the shared `nvs_open()` used by `api_client.c`. Keep the *shape* (open → read → close → degrade-on-any-error) identical to `nvs_get_string()`.

A device with no secret in NVS "logs a clear error and backs off" — copy `state_machine.c`'s `fail_step_out` convention (`"wifi"`, `"http"`, `"status"`, `"json"`) and add a new step token (e.g. `"secret"`), documented in `firmware/VENDOR.md`'s Log Line Contract per CONTEXT.md's discretion note.

---

### `firmware/main/api_client.c/.h` (service, request-response) — FW-03, FW-05, FW-10, FW-14

**Analog:** itself — this is the file being modified, and its own existing structure is the pattern for its own new code.

**401/403 branch — insert BEFORE the generic status check** (RESEARCH.md Pitfall 4 — the existing branch at `api_client.c:165-171` would otherwise swallow the new one):
```c
// firmware/main/api_client.c:160-171 (current — the generic branch this
// new 401/403 check must precede, not follow)
if (n < 0) {
    return FP_ERR_HTTP_TRANSPORT;
}
resp[n] = 0;
*resp_len = n;
if (status != 200) {
    ESP_LOGW(TAG, "HTTP %d (%d-byte response)", status, n);
    return FP_ERR_HTTP_STATUS;
}
return ESP_OK;
```
Add a new `FP_ERR_HTTP_AUTH` sentinel next to the existing four in `api_client.h:37-40` (same `((esp_err_t)0x00600005)`-style pattern, outside any ESP-IDF error-base range, compared only for equality) and branch on `status == 401 || status == 403` ahead of the `status != 200` check. Caller (`state_machine.c:51-53`) already has the exact dispatch idiom to extend:
```c
*fail_step_out = err == FP_ERR_HTTP_STATUS ? "status"
    : err == FP_ERR_HTTP_JSON ? "json" : "http";
```
add `err == FP_ERR_HTTP_AUTH ? "auth" :` to that ternary chain, and have the auth branch erase `FP_NVS_DEVICE_TOKEN` from NVS before returning (mirrors the existing `nvs_set_str(nvs, FP_NVS_DEVICE_TOKEN, ...)` write in `fp_api_setup()` at `api_client.c:254`, but with `nvs_erase_key()` instead).

**Checked returns (FW-05):** `esp_http_client_write`/`fetch_headers` at `api_client.c:154,156` are currently unchecked calls inside `small_request()`; the file's own `esp_http_client_open()` two lines above (`api_client.c:149`) is the checked-return idiom already used in the same function — copy that exact `if (err != ESP_OK) { return FP_ERR_HTTP_TRANSPORT; }` shape for the two new checks.

**Keep-alive client (FW-10):** `fp_api_get_display()` (`api_client.c:273-358`) and `fp_api_download()` (`api_client.c:392-452`) currently each call `esp_http_client_init()`/`esp_http_client_cleanup()` independently. Restructure so one handle is created once, `esp_http_client_set_url()` retargets it between the `/device/v1/display` call and the image URL, and `esp_http_client_cleanup()` is called only once at the end — the existing per-call `esp_http_client_config_t` literals (`.crt_bundle_attach = esp_crt_bundle_attach`, per-call `.timeout_ms`) stay, just applied via `esp_http_client_set_url()`/a config-update call instead of a second `_init()`.

**Dedup (FW-14):** the hex-check loop duplicated at `api_client.c:66-71` (`image_hash_valid`) and `api_client.c:235-240` (token check inside `fp_api_setup`) — fold into one helper, e.g. `fp_hex_valid(const char *s, size_t len)`, called from both sites (and from `secret_provision.c`'s NVS-read-back check if it needs the same shape).

---

### `firmware/main/app_main.c` (controller, event-driven) — FW-01, FW-02

**Analog:** itself — existing file already has the exact wiring points documented.

```c
// firmware/main/app_main.c:128-153 — the existing wake-classification +
// backoff-branch structure the new reset-reason check and deadline
// check both extend, not replace
esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
const char *reason = wake_reason_string(cause);
...
if (result == FP_POLL_FAILED) {
    uint8_t backoff_n = 0;
    nvs_get_u8(nvs, FP_NVS_BACKOFF_N, &backoff_n);
    uint32_t backoff_s = fp_backoff_seconds(backoff_n);
    if (backoff_n < UINT8_MAX) {
        nvs_set_u8(nvs, FP_NVS_BACKOFF_N, backoff_n + 1);
    }
    ...
    enter_deep_sleep(backoff_s);
}
```
The single noreturn exit point (`enter_deep_sleep()`, lines 87-104) is the funnel every plan must keep using — RESEARCH.md's task-notify design for the `esp_timer` deadline exists specifically so a hang-detected sleep still goes through this same function rather than adding a second `esp_deep_sleep_start()` call site.

---

### `firmware/main/epd13in3e.c` (driver, event-driven) — FW-01, FW-05, FW-12

**Analog:** itself.

```c
// firmware/main/epd13in3e.c:158-220 — epd_init() already accumulates
// esp_err_t across every register write and returns ESP_OK/ESP_FAIL;
// only the FOUR ESP_ERROR_CHECK calls inside its GPIO/SPI setup need to
// change to propagate instead of abort:
ESP_ERROR_CHECK(gpio_config(&out));      // line 167
ESP_ERROR_CHECK(gpio_config(&in));       // line 172
ESP_ERROR_CHECK(spi_bus_initialize(...)); // line 185
ESP_ERROR_CHECK(spi_bus_add_device(...)); // line 192
```
Replace each with the same `err |= ...` accumulation idiom already used two lines below in the same function (`err |= cmd_to(...)`), changing the calls to their non-aborting forms and returning `ESP_FAIL` through the function's existing `return err == ESP_OK ? ESP_OK : ESP_FAIL;` tail (`epd13in3e.c:219`).

`busy_wait("POF", ...)` at `epd13in3e.c:265` is currently called without checking its return (`epd_blit`'s PON/DRF calls two lines above it already check — `if (err != ESP_OK || busy_wait("DRF", 60000) != ESP_OK)`, line 261 — copy that exact idiom for POF).

The 800 µs per-row busy-wait at `epd13in3e.c:234` (inside `send_half`) — per RESEARCH.md, do **not** shorten it; if anything changes here it is a comment citing `Kconfig.projbuild`'s own `FP_MIN_REFRESH_SPACING_S` help text as the "why we kept it" source (`Kconfig.projbuild:140-169` is the existing citation-with-provenance style to copy for that comment).

---

### `firmware/main/panel.c` (driver, event-driven) — FW-12 light sleep

**Analog:** itself.

```c
// firmware/main/panel.c:80-98 — the exact vTaskDelay call to replace
if (plan == FP_PANEL_DRAW_AFTER_WAIT) {
    ...
    ESP_LOGI(TAG, "holding %lus for the panel's refresh spacing",
             (unsigned long)wait_s);
    vTaskDelay(pdMS_TO_TICKS(wait_s * 1000U));
    account_awake_time();
}
```
Per RESEARCH.md's confirmed trace (Wi-Fi already stopped, panel not yet powered at this point — `s_drawing = true; epd_init();` happens strictly after), substitute:
```c
esp_sleep_enable_timer_wakeup((uint64_t)wait_s * 1000000ULL);
esp_light_sleep_start();
```
in place of the `vTaskDelay`, keeping the surrounding `ESP_LOGI`/`account_awake_time()` calls unchanged. Flag the TWDT interaction (RESEARCH.md Pitfall/Open Question 2) as an explicit hardware-session check, not an assumption.

---

### `firmware/main/battery.c` (service, request-response) — FW-11

**Analog:** itself.

```c
// firmware/main/battery.c:31-49 — current single-sample-with-cache
// structure; the 8-sample average replaces the single
// adc_oneshot_get_calibrated_result() call, keeping every surrounding
// gpio-enable/settle/cleanup step identical
static int s_cached_mv = -1;

uint32_t fp_battery_mv(void)
{
    if (s_cached_mv >= 0) {
        return (uint32_t)s_cached_mv;
    }
    ...
    gpio_set_level(PIN_BATT_EN, 1);
    vTaskDelay(pdMS_TO_TICKS(FP_BATTERY_SETTLE_MS));
    ...
}
```
Replace the single `adc_oneshot_get_calibrated_result()` call (`battery.c:107`) with an 8-iteration loop accumulating `pin_mv` and averaging before the `battery_math_apply_divider()` call at line 117 — the divider math itself (`battery_math.c`) does not change; only the sampling loop inside `battery.c` does. "Read once, before Wi-Fi starts" means moving the call site: `telemetry_headers()` in `api_client.c:129-143` currently calls `fp_battery_mv()` lazily on the first `/display`/`/log` call (which is after `fp_wifi_connect()` in `state_machine.c:31`); move the (now-cached) read to occur before that connect call, e.g. from `app_main.c` or the top of `fp_poll_once()`.

---

### `stub-server/byos_server.py` (controller, request-response) — FW-08, D-34-01

**Analog:** itself — `do_POST`'s existing `/device/v1/setup` branch and the existing `state_path()`/`load_state()`/`save_state()` trio are the direct templates for the new registry.

```python
# stub-server/byos_server.py:579-594 — current setup handler (shared-secret
# check to be replaced by the registry gate)
if self.path == "/device/v1/setup":
    body = self.read_body_json()
    if not isinstance(body, dict) or "mac" not in body:
        return self.send_json(422, {"detail": "bad body"})
    if (self.args.secret and
            body.get("provision_secret") != self.args.secret):
        return self.send_json(401, {"detail": "bad secret"})
    token = secrets.token_hex(32)
    self.state["tokens"][body["mac"]] = token
    save_state(self.args.state_dir, self.state)
    print("setup: %s enrolled (hw_rev=%s)"
          % (body["mac"], body.get("hw_rev", "?")))
    return self.send_json(200, {"device_token": token})
```
```python
# stub-server/byos_server.py:142-158 — state file load/save idiom to
# copy verbatim for the new registry file (state/devices.json or similar)
def state_path(state_dir):
    return os.path.join(state_dir, "byos_state.json")

def load_state(state_dir):
    try:
        with open(state_path(state_dir)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"tokens": {}}

def save_state(state_dir, state):
    tmp = state_path(state_dir) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, state_path(state_dir))
```
```python
# stub-server/byos_server.py:564-567 — bearer_ok()'s shape: the new
# registry check (secret_ok(mac, presented_secret, registry)) should
# mirror this same "read from self.state, compare, return bool" shape
def bearer_ok(self):
    auth = self.headers.get("Authorization", "")
    return (auth.startswith("Bearer ") and
            auth[7:] in self.state["tokens"].values())
```
New registry-check function (RESEARCH.md's own worked example, matching `companion/auth.py`'s `hmac.compare_digest` convention — see Shared Patterns below):
```python
import hashlib
import hmac

def secret_ok(mac, presented_secret, registry):
    stored_hash = registry.get(mac)
    if stored_hash is None:
        return False
    presented_hash = hashlib.sha256(presented_secret.encode()).hexdigest()
    return hmac.compare_digest(presented_hash, stored_hash)
```
`Handler.args.secret`/`--secret` argparse flag (`byos_server.py:741-742,584-586`) is retired per D-34-01 — remove the flag and the `self.args.secret and ...` branch, replacing it with the registry gate ahead of token issuance.

---

### `stub-server/devices_cli.py` (tooling, CRUD) — D-34-01 registry CLI

**Analog:** `stub-server/make_test_panel.py` (argparse, stdlib-only, `if __name__ == "__main__": main()` guard) for the CLI skeleton, plus `byos_server.py`'s `load_state`/`save_state` pair (above) for the registry file's read/write.

```python
# stub-server/make_test_panel.py:1-36 — the CLI skeleton shape (docstring,
# argparse, stdlib-only import list, main() function) to copy for
# devices_cli.py's add/remove/list subcommands
import argparse
...
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(...)
    args = ap.parse_args()
    ...

if __name__ == "__main__":
    main()
```
Use `argparse` subparsers (`add`, `remove`, `list`) rather than separate scripts, reading/writing the same registry JSON file `byos_server.py` reads (per RESEARCH.md's suggested `state/devices.json` MAC → sha256-hex format). Secret generation for `add`: `secrets.token_hex(32)` — same call already used for token issuance at `byos_server.py:587`.

---

### `stub-server/test_devices_registry.py` (test, request-response) — FW-08

**Analog:** `stub-server/test_poll_cycle.py`'s `Harness`/`check()` pattern.

```python
# stub-server/test_poll_cycle.py:329-338 — the check() harness shape:
# never let an exception silently pass, print PASS/FAIL per named check
def check(name, fn):
    try:
        ok, reason = fn()
    except Exception as exc:
        ok, reason = False, "exception: %r" % (exc,)
    results.append((name, ok))
    if ok:
        print("PASS %s" % name)
    else:
        print("FAIL %s - %s" % (name, reason))
```
`test_poll_cycle.py` already launches `byos_server.py` as a real subprocess on a free local port and drives it over real HTTP (see its module docstring, lines 1-59, and the "launches byos_server.py as a subprocess" description) — reuse that exact harness (or extend `test_poll_cycle.py` directly with new `check(...)` calls) for the three FW-08 registry outcomes: registered+match → 200 + new token + old token revoked, registered+mismatch → 401/403 + old token untouched, unregistered → 401/403.

---

### `firmware/tests/*` and `firmware/tests/run_host_tests.sh` — FW-01/02/04/06/07

**Analog:** `firmware/tests/test_backoff.c` (simplest), `firmware/tests/test_panel_guard.c` (enum-plan style), `firmware/tests/test_battery_math.c` (boundary/saturation style), `firmware/tests/test_api_base.c` (pure-string-validation style).

```c
// firmware/tests/test_battery_math.c:1-29 — the whole-file shape every
// new host test should copy: header doc with the one-line cc command,
// #include "../main/<module>.h", a flat main() of assert() lines each
// with an inline comment citing WHY that boundary matters, one final
// printf + return 0
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "../main/battery_math.h"

int main(void)
{
    assert(battery_math_apply_divider(0) == 0);
    ...
    printf("battery_math: all cases pass\n");
    return 0;
}
```
```sh
# firmware/tests/run_host_tests.sh:38-41 — the run_suite() registration
# line to add one of for each new test_*.c file
run_suite "test_backoff" "${SCRIPT_DIR}/test_backoff.c" "${MAIN_DIR}/backoff.c"
run_suite "test_api_base" "${SCRIPT_DIR}/test_api_base.c" "${MAIN_DIR}/api_base.c"
```
Add four more `run_suite` lines (`test_reset_reason`, `test_wake_deadline`, `test_validate`, `test_sleep_decision`), each `impl_src` pointing at the new pure `.c` file in `main/`.

---

### `.github/workflows/firmware.yml` — CI wiring (FW-06 success criterion 3)

**Analog:** itself — the existing single `build` job's step list is the template for where the new step goes.

```yaml
# .github/workflows/firmware.yml:39-58 — existing step order; the new
# host-test step goes BEFORE "Build firmware image" for fail-fast
# ordering (sub-second host tests vs. minutes-long Docker build)
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

      - name: Create compile-only credentials header
        run: cp firmware/main/secrets.example.h firmware/main/secrets.h

      - name: Build firmware image
        run: ./firmware/build.sh
```
Insert a `- name: Run firmware host tests` / `run: bash firmware/tests/run_host_tests.sh` step immediately after checkout, before the credentials-header/build steps. Do not touch `.github/workflows/ci.yml` (Phase 32's boundary, per CONTEXT.md).

---

### `firmware/partitions.csv`, `firmware/sdkconfig.defaults`, `firmware/main/Kconfig.projbuild`, `firmware/CMakeLists.txt`, `firmware/build.sh` — config-only changes

**Analog:** each file is its own pattern; these are small, additive edits, not new structures.

```
# firmware/partitions.csv (current) — new "secret" line goes in the free
# 0x13000-0x20000 gap, per RESEARCH.md's arithmetic, leaving factory's
# 0x20000 offset unchanged
nvs,        data, nvs,      0x9000,  0x6000
otadata,    data, ota,      0xf000,  0x2000
phy_init,   data, phy,      0x11000, 0x1000
nvs_keys,   data, nvs_keys, 0x12000, 0x1000
factory,    app,  factory,  0x20000, 0x250000
```
```
# firmware/sdkconfig.defaults:21-23 — the misleading comment FW-02
# corrects, and the value that stays capped at 60 (TWDT ceiling, not the
# whole-wake deadline)
# Watchdog on everything: any hang -> reset -> backoff sleep.
CONFIG_ESP_TASK_WDT_INIT=y
CONFIG_ESP_TASK_WDT_TIMEOUT_S=60
```
```
# firmware/sdkconfig.defaults:41-42 — the two orphan lines FW-13 deletes
CONFIG_FP_PROVISION_TIMEOUT_S=600
CONFIG_FP_FACTORY_PREP=n
```
```
# firmware/main/Kconfig.projbuild:7-32 — top-level "menu SkyPane" block;
# CONFIG_SKYPANE_ALLOW_HTTP goes here (not nested in a submenu), copying
# FP_DEV_PROVISION_SECRET's "DEV ONLY" bool/help-text style
menu "SkyPane"
    config FP_DEV_PROVISION_SECRET
        string "DEV ONLY: provision secret for POST /device/v1/setup"
        default ""
        help
            Bench-only seed copied once into the protected factory namespace.
            Production images MUST leave this blank; ...
```
```
# firmware/CMakeLists.txt:14 — the line FW-15 deletes (replaced by the
# host-resolved -DPROJECT_VER passed from build.sh, per RESEARCH.md's
# git-describe-in-container pitfall)
set(PROJECT_VER "0.1.0-p1")
```
```sh
# firmware/build.sh:26-36 — the docker run invocation FW-15 extends with
# a host-resolved -DPROJECT_VER (git describe run OUTSIDE the container,
# since .git is not visible inside it at the current mount)
docker run --rm \
    -v "${SCRIPT_DIR}:/project" \
    -w /project \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    "${IMAGE}" \
    idf.py \
        -B "${BUILD_DIR}" \
        -DSDKCONFIG="${BUILD_DIR}/sdkconfig" \
        -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.ee02.defaults" \
        "${ACTION}"
```

---

### `firmware/provision.sh` (tooling, file-I/O) — D-34-02

**Analog:** `deploy/provision.sh` (idempotent bash host script, hostname/arg validation, root-check pattern) + `firmware/flash.sh` (serial-port-required argument discipline, esptool invocation, no wildcard/guessed device).

```sh
# deploy/provision.sh:27-52 — idempotent host-script shape: set -euo
# pipefail, required-arg validation with a clear usage message, no silent
# defaults for anything destructive
set -euo pipefail
...
if [ "$(id -u)" -ne 0 ]; then
    echo "provision.sh must run as root (...)" >&2
    exit 1
fi
```
```sh
# firmware/flash.sh:22-40 — the "serial port is REQUIRED and never
# guessed" discipline to copy exactly for firmware/provision.sh's own
# port argument
PORT="${1:-}"
if [ -z "${PORT}" ]; then
    echo "Usage: $0 <serial-port>" >&2
    ...
    exit 1
fi
```
`firmware/provision.sh` generates the secret (`openssl rand -hex 32` or equivalent, matching `deploy/README.md`'s existing `openssl rand -hex 32` convention for `SKYPANE_BYOS_SECRET`), builds a small CSV → `nvs_partition_gen.py` → `parttool.py write_partition --partition-name=secret` sequence inside the same `espressif/idf:v5.3.1` container `build.sh` already pins, and prints the MAC + `sha256(secret)` registry line for the operator to hand to `stub-server/devices_cli.py add`.

**Note:** `deploy/provision.sh` already exists (VPS first-run setup) — the new `firmware/provision.sh` is a different script in a different directory serving a different purpose (per-device secret injection over USB vs. VPS bootstrap). No collision, but keep the name distinct in any cross-references to avoid confusing the two in docs.

---

## Shared Patterns

### Pure-logic module split (no ESP-IDF includes)
**Source:** `firmware/main/backoff.c/.h`, `firmware/main/panel_guard.c/.h`, `firmware/main/api_base.c/.h`, `firmware/main/battery_math.c/.h`
**Apply to:** `reset_reason.c/.h`, `wake_deadline.c/.h`, `validate.c/.h`, `sleep_decision.c/.h`
Every existing pure module: (1) `#pragma once` header with a doc comment explaining *why* it's separated from its I/O-driving caller, (2) zero ESP-IDF includes (only `<stdint.h>`/`<stdbool.h>`/`<string.h>`/`<ctype.h>`), (3) one narrow function or a tiny enum-returning decision function, (4) a matching `tests/test_<name>.c` compiled by the system `cc` and wired into `run_host_tests.sh`.

### esp_err_t sentinel step-classification
**Source:** `firmware/main/api_client.h:37-40`
```c
#define FP_ERR_HTTP_TRANSPORT ((esp_err_t)0x00600001)
#define FP_ERR_HTTP_STATUS    ((esp_err_t)0x00600002)
#define FP_ERR_HTTP_JSON      ((esp_err_t)0x00600003)
#define FP_ERR_IMAGE_VERIFY   ((esp_err_t)0x00600004)
```
**Apply to:** the new `FP_ERR_HTTP_AUTH` sentinel (FW-03) — same numeric range, same "compared for equality only, never passed to `ESP_ERROR_CHECK`" comment.

### `fail_step_out` dispatch ternary
**Source:** `firmware/main/state_machine.c:51-53`
```c
*fail_step_out = err == FP_ERR_HTTP_STATUS ? "status"
    : err == FP_ERR_HTTP_JSON ? "json" : "http";
```
**Apply to:** every new failure branch (FW-03's `"auth"`, D-34-02's `"secret"` no-secret-in-NVS case) — extend the same ternary chain; do not introduce a second dispatch mechanism. Any NEW `step=` token must be documented in `firmware/VENDOR.md`'s Log Line Contract table (CONTEXT.md's explicit discretion note).

### NVS single-writer-at-a-time namespace handling
**Source:** `firmware/main/app_main.c:131-134,144-160,172` and `firmware/main/state_machine.c:75-80,127-131`
```c
nvs_handle_t nvs;
ESP_ERROR_CHECK(nvs_open(FP_NVS_NAMESPACE, NVS_READWRITE, &nvs));
...
nvs_set_u8(nvs, FP_NVS_BACKOFF_N, backoff_n + 1);
nvs_commit(nvs);
nvs_close(nvs);
```
**Apply to:** `secret_provision.c` and the token-erase-on-401 branch — always `nvs_open` → mutate → `nvs_commit` → `nvs_close`, never leave a handle open across a function return.

### Constant-time secret comparison (`hmac.compare_digest`)
**Source:** `companion/auth.py:186` (`return hmac.compare_digest(submitted.encode(), configured_password())`)
**Apply to:** `stub-server/byos_server.py`'s new registry `secret_ok()` — same `hmac.compare_digest` call on a `hashlib.sha256(...).hexdigest()` comparison, matching the project's one existing convention for this exact problem.

### stdlib-only state file load/save (atomic write via temp+rename)
**Source:** `stub-server/byos_server.py:142-158` (`state_path`/`load_state`/`save_state`)
**Apply to:** the new device registry file (`devices_cli.py` + `byos_server.py`'s registry read) — same `os.path.join(state_dir, "<name>.json")`, same `try/except (OSError, ValueError): return <default>` fail-open read, same `tmp = path + ".tmp"; json.dump(...); os.replace(tmp, path)` atomic write.

### Host-only test harness (no framework, system `cc`)
**Source:** `firmware/tests/run_host_tests.sh` + any `test_*.c`
**Apply to:** every new `firmware/tests/test_*.c` — `assert()`-based, one `run_suite` line added to `run_host_tests.sh`, no new build dependency.

### Idempotent, root-checked, no-guessed-device host scripts
**Source:** `deploy/provision.sh:27-52`, `firmware/flash.sh:22-53`
**Apply to:** `firmware/provision.sh` — required positional args validated with a clear `Usage:` message on stderr and `exit 1`, no destructive operation ever defaults or guesses (matches D-34-02's "must not erase the existing token/hash/backoff keys unless explicitly asked").

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `firmware/main/certs/isrg-root-x1.pem`, `isrg-root-x2.pem` | config (static data) | — | No prior vendored certificate files in the tree; these are sourced directly from Let's Encrypt/ISRG's own published roots (per RESEARCH.md's Package Legitimacy Audit — verify fingerprints against a second independent source before committing), not derived from any existing project pattern. |
| `hardware/<new-or-extended-doc>.md` hardware-session results doc | docs | — | Format precedent exists (`hardware/BACKOFF-OBSERVATION.md`, verdict-first structure, disclosed partial/failed sub-checks) but the specific triggers (panic/brownout injection, hung-wake deadline, token-revoke re-enrolment, `sleep_s` overflow, DHCP/TLS timing three-way comparison, battery-vs-multimeter) are new content, not a structural gap — see the `hardware/BACKOFF-OBSERVATION.md` analog cited in the table above for the section shape to reuse (Verdict, Observed Sequence table, per-scenario write-up, Checker Output). |

## Metadata

**Analog search scope:** `firmware/main/`, `firmware/tests/`, `firmware/` root (build/flash/monitor scripts, Kconfig, sdkconfig, partitions.csv, CMakeLists.txt), `stub-server/`, `deploy/`, `.github/workflows/`, `hardware/`, `companion/auth.py` (for the `hmac.compare_digest` shared pattern)
**Files scanned:** ~30 read directly (full or targeted sections); `firmware/VENDOR.md`'s Log Line Contract and vendoring-table sections grepped for citation accuracy
**Pattern extraction date:** 2026-09-23
