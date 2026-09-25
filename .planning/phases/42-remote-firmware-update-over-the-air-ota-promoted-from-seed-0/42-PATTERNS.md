# Phase 42: Remote firmware update over the air (OTA) - Pattern Map

**Mapped:** 2026-09-25
**Files analyzed:** ~28 (new + modified, across firmware/byos/server/companion/CI/deploy)
**Analogs found:** 22 / 28 (the rest depend on Phases 35-41 landing first — see "No Analog Found")

**G-41 reminder (binding on every plan this file feeds):** line numbers below are from `main` as read on 2026-09-25, before Phases 35-41 land. RESEARCH.md's own verification table confirms `atomic_write`/`exclusive_lock` (Phase 36), the content-addressed `/img/<sha>.bin` route (INT-05), byos `--bind 127.0.0.1` (37-11), and a third `companion/layout.py` NAV_GROUPS Advanced entry (39/40) **do not exist on `main` yet**. Every plan must re-read the files it edits on current `main` before writing code — this file gives shape and analogs, not literal line numbers to trust blindly.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `firmware/main/ota.c` / `ota.h` (new) | service (device-side OTA orchestration) | streaming (HTTPS download + flash write) | `firmware/main/fault_screen.c`/`.h` (pure-C, host-testable design) + upstream pinned `main/ota.c` (re-derivable, see RESEARCH.md Sources) | role-match (structure) / exact (mechanics, from upstream) |
| `firmware/main/validate.c`/`.h` (extend) | utility (input validation) | transform | itself — extend `fp_image_hash_valid`/`fp_url_valid`/`fp_sleep_s_parse` family with firmware-offer fields (`version`, `sha256`, `size`) | exact |
| `firmware/main/api_client.c` (extend `fp_api_get_display`) | controller-ish (HTTP client parse) | request-response | itself — the ignored `firmware` field at `firmware/main/api_client.c` (search `firmware` is out of scope) sits right where the new object must be parsed, following the `image_url`/`image_hash`/`sleep_s` cJSON-extract-then-validate-then-strlcpy shape | exact |
| `firmware/main/state_machine.c` (extend `fp_poll_once`) | controller (wake state machine) | event-driven | itself — insert OTA apply between the `disp.led_enabled` handling and the hash-skip check, matching upstream's own "OTA before hash-skip" ordering (RESEARCH.md Pattern 2) | exact |
| `firmware/main/app_main.c` (extend) | controller (wake dispatcher) | event-driven | itself — `fail_and_sleep()`/`maybe_draw_fault_screen()`/`enter_deep_sleep()` show exactly where a new `fp_ota_confirm_if_pending()` call must land: after the healthy-poll NVS commit, before `enter_deep_sleep()` (mirrors upstream's app_main.c ordering, RESEARCH.md Pattern 3) | exact |
| `firmware/main/updating_screen.c`/`.h` (new, or `fault_screen.c` generalised) | component (on-device hold screen) | transform (dither render) | `firmware/main/fault_screen.c`/`.h` — same mask-stamp-on-dithered-field technique, same `_Static_assert` buffer-size contract, same `tick` callback for watchdog feeding | exact |
| `firmware/tools/gen_fault_screen.py` (extend, or sibling script) | utility (build-time mask generator) | transform | itself — the Python port that produces `fault_screen_mask.h`; UI-SPEC explicitly leaves "extend vs. twin script" to the executor | exact |
| `server/plane/render.py` (extend: `draw_updating_icon`, `UPDATING_*` constants, `_build_updating_canvas`) | service (canvas composition) | transform | itself — `_build_dimmed_hold_canvas()` plus sibling `draw_power_icon()`/`draw_moon_icon()`/`draw_alert_icon()` | exact |
| `firmware/sdkconfig.defaults` (extend) | config | n/a | itself — the existing `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n` line and its comment is the exact spot to flip, plus new `CONFIG_SECURE_SIGNED_*` lines in the same file | exact |
| `firmware/build.sh` / `firmware/CMakeLists.txt` (extend `PROJECT_VER`) | config/build | batch | itself — `VER=$(git describe --tags --always --dirty ...)` and `-DPROJECT_VER="${VER}"` is the exact mechanism D-16 must special-case for tagged release builds | exact |
| `firmware/tests/test_ota_verify.c` (new) | test | transform | `firmware/tests/test_validate.c` — host-side `cc ... && run`, `assert()`-based, one function-family per test | exact |
| `firmware/tests/test_updating_screen_mask.c` / reuse `test_fault_screen.c` pattern | test | transform | `firmware/tests/test_fault_screen.c` — determinism/bounds checks against the dither recipe | exact |
| `stub-server/byos_server.py` (`GET /device/v1/display`, extend to compose `"firmware"`) | route/controller (byos) | request-response | itself — `quiet_hours_sleep_s(battery_critical_sleep_s(display_off_sleep_s(...)))` composition at lines ~582-588 is the exact precedent for composing a firmware offer as one more pure function layered onto the same response dict | exact |
| `stub-server/byos_server.py` (new `/fw/<sha>.bin` or mirrored `/img/<sha>.bin` route) | route (file serving) | file-I/O | itself — the existing `self.path.startswith("/img/")` branch (`do_GET`, ~line 598) serves the single configured image; **NOT yet content-addressed on `main`** (RESEARCH.md verification table) — re-derive from whatever INT-05 ships, not this scout | role-match (today) — expected exact after INT-05 lands |
| `server/firmware_registry.py` (new, name/location per Claude's Discretion) | model/store (release registry) | CRUD | **no analog on `main` today** — must use Phase 36's `atomic_write`/`exclusive_lock` helpers, which do not exist on `main` yet (G-41). Closest *shape* precedent: `server/device_config.py`'s load/save-JSON-document pattern | none today — expected role-match after Phase 36 lands |
| `server/notify.py` (extend `_BODY_FR`, add OTA success/failure strings) | service (push notification) | event-driven | itself — `BATTERY_LOW_BODY`/`FRAME_SILENT_BODY` + their `_BODY_FR` keys is the exact template for `"Firmware %s installed"` / `"Update failed, back on %s"` | exact |
| `server/poll_loop.py` (read battery-low-active flag for the offer gate) | service (poll cycle) | batch | itself — `BATTERY_LOW_THRESHOLD_MV`/`BATTERY_LOW_CLEAR_MV`/`apply_battery_hysteresis()` is the exact gate D-12 reuses, no new threshold | exact |
| `companion/layout.py` (`NAV_GROUPS`, `ICON_DEFS_HTML`, `ICON_IDS`, `_NAV_ICON_BY_SLUG`) | config/component (nav) | n/a | itself — `HEALTH_ROUTE`/`DEVICE_ROUTE` tuple in `NAV_GROUPS`'s Advanced group (~line 61-72), the `icon-nav-health`/`icon-nav-device` `<symbol>` pattern (~line 531-574), and the slug→icon map (~line 662-667) | exact (mechanism) — **NAV_GROUPS on `main` today has only 2 Advanced entries, not 3** (RESEARCH.md verification table); re-verify exact tuple shape at plan time |
| `companion/pages/update_page.py` (new) | component (page builder) | request-response | `companion/pages/health_page.py` (card-per-concern grammar, `stat_tile()`/`_tile_body()`, `status_dot()`) + `companion/pages/config_page.py` (`calendar_disconnect_confirm_page()`, two-step no-JS confirm) | role-match — no existing page has all four ingredients (status card + confirm flow + history table), so it composites three separate analogs |
| `companion/app.py` (new routes: `GET /update`, `POST /update/install`, `POST /update/cancel`) | route/controller | request-response | `companion/app.py` `_handle_calendar_disconnect_post()` (~line 1589) for the Install confirm flow; `_handle_quick_toggle()`/`_handle_poll_now()` (~line 1935-1969) for Cancel's plain-POST-no-confirm shape | exact |
| `companion/i18n_fr/nav.py` (add "Update"/"Mise à jour") | i18n data | transform | itself — existing `HEALTH_ROUTE`/`DEVICE_ROUTE` label entries | exact |
| `companion/i18n_fr/` (new module or extend `health.py`/`nav.py` for Update-page strings) | i18n data | transform | `companion/i18n_fr/health.py` — same `{English: French}` dict-literal shape | exact |
| `companion/static/confirm-submit.js` (reuse, no changes expected) | utility (client JS) | event-driven | itself — the `data-confirm` misclick-guard UI-SPEC names explicitly for the Install button | exact (reuse as-is) |
| `companion/test_update_page.py` (new) | test | request-response | `companion/test_config_page_*.py` / `companion/test_status_pages_*.py` — behaviour-over-source, plain-request + pytest-playwright split | role-match |
| `server/test_firmware_registry.py` (new) | test | CRUD | `server/test_config_history.py` — JSON-document load/save round-trip test shape | role-match |
| `server/test_ota_battery_gate.py` (new) | test | transform | `server/test_colour_rules.py` / the existing `apply_battery_hysteresis()` unit-test pattern (search `server/` for its test file at plan time — not directly located in this pass) | role-match |
| `stub-server/test_ota_offer.py` (new) | test | request-response | mirrors whatever `stub-server/`'s existing `/device/v1/display` test module is named on `main` at plan time (not located in this pass — byos test file naming should be re-checked) | role-match — verify exact file at plan time |
| `.github/workflows/firmware.yml` (new tag-triggered signed-build job) | CI config | batch | itself — the existing two-job shape (`host-tests`, `build`), `permissions: contents: read` header, and `firmware/build.sh` invocation is the exact skeleton to extend with an `on: push: tags:` trigger, `espsecure.py` sign step, `upload-artifact` | exact |
| `.github/workflows/ci.yml` (extend `deploy` job to copy firmware into state dir) | CI config | batch | itself — the `Deploy` step's `env:`-not-`run:`-interpolated secrets pattern (`DEPLOY_SSH_TARGET`/`DEPLOY_HOST_KEY`) is the exact convention any new secret-adjacent step must follow | exact |
| `.github/workflows/firmware-chain-check.yml` (new, OTA-11) | CI config | batch | `.github/workflows/ci.yml`'s job/step shape (name, `runs-on: ubuntu-latest`, `timeout-minutes`) — no existing scheduled/network-checking workflow to copy the trigger shape from; `on: schedule:` + `on: push:` is new territory in this repo | none for the trigger shape — role-match for job/step conventions |
| `deploy/deploy.sh` / `deploy/activate.sh` (extend to stage `/opt/skypane/state/firmware/`) | deploy script | file-I/O | itself — `deploy/deploy.sh`'s `git archive`-based "ship only committed tree" contract and `activate.sh`'s atomic `current` symlink swap-and-rollback pattern | exact |

## Pattern Assignments

### `firmware/main/ota.c` / `ota.h` (new)

**Analogs:** `firmware/main/fault_screen.c`/`.h` (structure/testability), pinned upstream `main/ota.c`/`api_client.c`/`state_machine.c`/`app_main.c` at commit `ce3335fc` (mechanics — RESEARCH.md's Sources section gives the exact `raw.githubusercontent.com` fetch path; do not re-fetch, RESEARCH.md already quotes the load-bearing excerpts in its Pattern 2/3 and Common Pitfalls sections).

**Testability pattern** (`firmware/main/fault_screen.c` lines 1-19):
```c
/* Quick task 260924-u7n (DEVICE-06) - see fault_screen.h for the full
 * design rationale. Pure C11, no ESP-IDF dependency at all (buildable and
 * testable standalone, firmware/tests/test_fault_screen.c) ...
 */
#include "fault_screen.h"
#include <string.h>
#include "fault_screen_mask.h"
```
`ota.c`'s pure-decision logic (should-I-confirm, should-I-attempt-given-battery, size/hash verdict) should be extracted into ESP-IDF-independent functions the same way, so `firmware/tests/test_ota_verify.c` can host-test them without the real bootloader/crypto stack (RESEARCH.md's own Validation Architecture table: OTA-02/OTA-05/OTA-06 device-side logic is host-testable, OTA-03's actual rollback and OTA-04's signature check are not).

**Apply-before-hash-skip ordering** (RESEARCH.md Pattern 2, upstream `state_machine.c`):
```c
if (disp.has_fw) {
    ESP_LOGI(TAG, "OTA offered: %s", disp.fw_version);
    if (fp_ota_apply(disp.fw_url, disp.fw_sha256) == ESP_OK) {
        esp_restart();   /* NOT deep sleep — reboots straight into the trial image */
    }
    ESP_LOGW(TAG, "OTA failed, continuing this wake normally");
}
```
Adapt for `esp_https_ota` instead of upstream's raw `esp_http_client_read` loop; insert the D-14 Updating-screen draw and the D-12 battery self-check before this call, per RESEARCH.md's own adaptation notes.

**Rollback confirmation ordering — the single highest-risk detail** (RESEARCH.md Pattern 3, upstream `app_main.c`):
```c
fp_poll_result_t result = fp_poll_once(poll_boot_reason(wake, action), &sleep_s);
if (result == FP_POLL_FAILED) {
    sleep_after_failure(nvs);   /* does not return */
}
nvs_set_u8(nvs, FP_NVS_BACKOFF_N, 0);
nvs_commit(nvs);
nvs_close(nvs);
fp_ota_confirm_if_pending();    /* <-- must run before the deep sleep below */
fp_deep_sleep(sleep_s);
```
SkyPane's own `app_main.c` equivalent insertion point: between the existing `nvs_set_u8(nvs, FP_NVS_BACKOFF_N, plan.next_backoff_n); nvs_commit(nvs); nvs_close(nvs);` block (line ~395-399) and `enter_deep_sleep(plan.sleep_s)` (line ~405) — call `fp_ota_confirm_if_pending()` there, unconditionally, on the healthy-poll path only. Do not defer to any later wake (Common Pitfalls #1 in RESEARCH.md).

### `firmware/main/validate.c`/`.h` (extend)

**Analog:** itself.

**Existing validator shape to extend** (`firmware/main/validate.c` lines 27-33, 67-82):
```c
bool fp_image_hash_valid(const char *hash)
{
    if (!hash || strncmp(hash, "sha256:", 7) != 0) {
        return false;
    }
    return fp_hex_lower_valid(hash + 7, 64);
}

bool fp_sleep_s_parse(double value, uint32_t *out)
{
    if (value != value) { return false; } /* NaN never equals itself */
    if (value < (double)FP_SLEEP_S_MIN || value > (double)FP_SLEEP_S_MAX) {
        return false;
    }
    if (value != (double)(uint32_t)value) { return false; }
    if (out) { *out = (uint32_t)value; }
    return true;
}
```
The firmware offer's `sha256`/`size`/`version`/`url` fields need siblings of this exact shape (bounded, `NaN`-safe, hex-shape, no allocation) — this is also RESEARCH.md's V5 Input Validation guidance: "extend that module, don't inline new checks in `api_client.c`."

### `firmware/main/api_client.c` (extend `fp_api_get_display`)

**Analog:** itself, lines 525-575 (parse → validate → `strlcpy` shape).

```c
const cJSON *url = cJSON_GetObjectItem(json, "image_url");
const cJSON *hash = cJSON_GetObjectItem(json, "image_hash");
...
fp_display_t parsed = {0};
if (!cJSON_IsString(url) ||
    !fp_url_valid(url->valuestring, sizeof(parsed.image_url), s_allow_http) ||
    !cJSON_IsString(hash) || !fp_image_hash_valid(hash->valuestring) ||
    ...) {
    cJSON_Delete(json);
    memset(resp, 0, sizeof(resp));
    return FP_ERR_HTTP_JSON;
}
strlcpy(parsed.image_url, url->valuestring, sizeof(parsed.image_url));
...
/* `firmware` is out of scope (OTA is not implemented); no field of
 * it is read or stored regardless of what the server sends. */
*out = parsed;
```
Replace the last comment's premise: parse an optional `firmware` object (`version`, `url`, `sha256`, `size`) into a new `fp_display_t` member, using the same "absent object → treat as no offer" permissive-but-bounded pattern the `led_enabled` field already demonstrates (`fp_led_enabled_resolve`, lines 556-567) — a malformed/missing offer must degrade to "no OTA this wake," never a rejected poll.

### `firmware/main/updating_screen.c`/`.h` (new) and `_build_updating_canvas` (`server/plane/render.py`)

**Analog:** `firmware/main/fault_screen.c`/`.h` in full — reuse `DITHER_TARGET_LEVEL = 102`, the two-row Floyd-Steinberg accumulator technique, the `_Static_assert` buffer-size contract (`fault_screen.c`/`app_main.c` line 68), and the `tick` callback for watchdog feeding (`fp_wake_feed`, `app_main.c` line 223). UI-SPEC (Surface 2) is explicit that this is a **new mask**, not new dither machinery — do not introduce a second dither implementation.

```c
_Static_assert(FP_FAULT_SCREEN_BYTES == EPD_BYTES, "fault screen buffer size must match EPD_BYTES");
```
mirror this assertion for whatever new `FP_UPDATING_SCREEN_BYTES` constant the new header defines.

### `stub-server/byos_server.py` (`GET /device/v1/display`, offer composition)

**Analog:** itself, lines 574-597 (composition chain) and module docstring (lines 27-35).

```python
"sleep_s": quiet_hours_sleep_s(
    battery_critical_sleep_s(
        display_off_sleep_s(
            read_wake_interval_s(self.args.state_dir, self.args.sleep),
            self.args.state_dir),
        self.args.state_dir, battery_mv),
    self.args.state_dir),
"firmware": None,
```
The `"firmware": None` literal at line 589 is the exact hook D-01/D-06's offer object replaces. Follow the same "pure function of state, composed outermost-to-innermost, comment documents composition order" convention RESEARCH.md's Pattern 1 already names — `battery_low_active` (D-12) gates the offer the same way `battery_critical_sleep_s` gates `sleep_s`, but the withhold logic must NOT thread through `quiet_hours_sleep_s`/`display_off_sleep_s` (D-13 says quiet hours/display-off must never withhold the offer, unlike `sleep_s`).

**Existing image-serving route to mirror** (`byos_server.py` `do_GET`, lines 598-609):
```python
if self.path.startswith("/img/"):
    try:
        with open(self.args.image, "rb") as fh:
            image = fh.read()
    except OSError:
        return self.send_json(503, {"detail": "image unreadable"})
    self.send_response(200)
    self.send_header("Content-Type", "application/octet-stream")
    self.send_header("Content-Length", str(len(image)))
    self.end_headers()
    self.wfile.write(image)
    return None
```
**Not yet content-addressed on `main`** (confirms RESEARCH.md's verification table) — today it always serves `self.args.image`, no `<sha>` in the path at all. The new firmware-image route must mirror whatever INT-05 actually lands as (strict regex, 404 otherwise), re-read at plan time — this excerpt shows only the shape to extend from, not a route to copy verbatim.

**Telemetry logging to extend** (`byos_server.py` lines 493-501):
```python
def log_telemetry(self):
    parts = []
    for h in ("X-Fw-Version", "X-Boot-Reason", "X-Rssi", "X-Battery-Mv"):
        v = self.headers.get(h)
        if v:
            parts.append("%s=%s" % (h, v))
    if parts:
        print("  telemetry:", " ".join(parts))
```
Whichever new header/field reports OTA outcome (Claude's Discretion — new header vs. `X-Boot-Reason` + version-change inference) slots into this same allow-listed-header-name loop.

### `server/notify.py` (extend for OTA success/failure)

**Analog:** itself, lines 20-44 (body constants + `_BODY_FR` table).

```python
BATTERY_LOW_BODY = "Battery low — %s mV (≈ %d%%)"
BATTERY_OK_BODY = "Battery back to normal"
FRAME_SILENT_BODY = "The frame has not checked in for %s"
FRAME_RECOVERED_BODY = "The frame is back"
ALERT_TITLE = "SkyPane"

_BODY_FR = {
    "Battery low — %s mV (≈ %d%%)": "Batterie faible — %s mV (≈ %d %%)",
    "Battery back to normal": "Batterie revenue à la normale",
    ...
}


def body_for_lang(text, lang):
    if lang == "fr":
        return _BODY_FR.get(text, text)
    return text
```
Add `FIRMWARE_INSTALLED_BODY = "Firmware %s installed"` / `FIRMWARE_UPDATE_FAILED_BODY = "Update failed, back on %s"` plus their `_BODY_FR` entries, same key-is-the-English-string convention. `send_notification()` itself (never raises, one attempt, `_url_is_safe()` gate, no-redirect opener) needs no change — call it exactly as `server/poll_loop.py`'s `_notify_battery_transition()` already does.

### `server/poll_loop.py` (battery-low gate reuse, D-12)

**Analog:** itself, lines 171-176, 264-274.

```python
BATTERY_LOW_THRESHOLD_MV = 3500
BATTERY_LOW_CLEAR_MV = 3600

def apply_battery_hysteresis(battery_mv, was_active):
    if was_active:
        return battery_mv < BATTERY_LOW_CLEAR_MV
    return battery_mv <= BATTERY_LOW_THRESHOLD_MV
```
D-12's "an update is deferred while the existing battery-low alert is active ... no new threshold or setting" means the OTA offer-gating code should call/consume this exact function's result (`poll_state["battery_low_active"]`), not reimplement a threshold.

### `companion/layout.py` (`NAV_GROUPS`, nav icons)

**Analog:** itself.

```python
HEALTH_ROUTE = "/health"
DEVICE_ROUTE = "/device"
ADVANCED_GROUP_LABEL = "Advanced"

NAV_GROUPS = (
    ...
    (ADVANCED_GROUP_LABEL, (
        (HEALTH_ROUTE, "Health"),
        (DEVICE_ROUTE, "Device"),
    )),
)
```
Add `UPDATE_ROUTE = "/update"` and a third tuple member `(UPDATE_ROUTE, "Update")`. **Verify the exact tuple shape on `main` at plan time** — RESEARCH.md's verification table confirms only 2 Advanced entries exist today; Phases 39/40 may have changed this by execution time (G-41).

```python
ICON_IDS = [
    ...
    "icon-nav-health",
    "icon-nav-device",
    ...
]
```
and the `<symbol>` definitions (`companion/layout.py` lines ~538-543, ~569-574):
```python
'<symbol id="icon-nav-health" viewBox="0 0 20 20" fill="none" '
...
'<symbol id="icon-nav-device" viewBox="0 0 20 20" fill="none" '
```
Add `icon-nav-update` following the identical `fill="none" stroke="currentColor" stroke-width="1.5"` convention (UI-SPEC already gives the exact path data suggestion). Then extend the slug→icon map (`companion/layout.py` lines ~662-667):
```python
"health": "icon-nav-health",
"device": "icon-nav-device",
```
with `"update": "icon-nav-update"`. **One edit point** — `NAV_TABS`, `sidebar_nav()`, `_mobile_nav_html()`, `_tab_bar_html()` all derive from `NAV_GROUPS`, per CONTEXT.md D-02's own note; do not hand-list the new route anywhere else.

### `companion/pages/update_page.py` (new)

**Analogs:** `companion/pages/health_page.py` (status card grammar), `companion/pages/config_page.py` (confirm-page pattern).

**Confirm-page pattern to copy verbatim in shape** (`companion/pages/config_page.py` lines 2410-2436):
```python
def calendar_disconnect_confirm_page(ctx):
    """Two-step disconnect confirmation, rendered whenever the posted
    confirm field does not exactly match the expected value ...
    This page is the actual security control: it works with JavaScript
    disabled ...
    """
    return (
        layout.page_header(i18n.t(CALENDAR_DISCONNECT_CONFIRM_HEADING))
        + '<p class="text-body">%s</p>'
        '<form method="post" action="%s">'
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
        '<p><a class="text-label" href="%s">%s</a></p>'
    ) % (
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_SENTENCE)),
        CALENDAR_DISCONNECT_ROUTE,
        CALENDAR_DISCONNECT_CONFIRM_FIELD, escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT)),
        layout.DISPLAY_ROUTE, escape_html(i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT)),
    )
```
This is the direct model for `update_install_confirm_page(ctx, version, next_wake_text)` (UI-SPEC's own name): heading, body sentence, a form re-posting with the hidden fields pre-filled (here: `version` + `confirm=yes`), and a plain cancel **link** (never a second form).

**Status-dot / stat-tile grammar to reuse** (`companion/layout.py`, referenced by `health_page.py`):
```python
_STATUS_DOT_CLASSES = { ... }  # layout.py line ~399
def status_dot(state, label, title=None, visually_hide_label=False):
    ...
    css_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
```
Use `layout.status_dot(state, label)` for the five OTA states exactly as UI-SPEC's colour-mapping table specifies (`dot--off`/`dot--warn`/`dot--ok`/`dot--error`, no new class).

**Table component to reuse for version history** (`companion/layout.py`):
```python
def data_table(headers, rows, mono_columns=(), raw_columns=(), desc_columns=(), prose=False, ...):
```
Call with `mono_columns=(0,)` (version tag) and `desc_columns=(2,)`, `prose=True` (commit-notes column), per UI-SPEC's Card 2 table.

### `companion/app.py` (new `/update`, `/update/install`, `/update/cancel` routes)

**Analog:** itself, `_handle_calendar_disconnect_post()` (lines 1589-1608) for Install's two-step confirm; `_handle_poll_now()`/`_handle_quick_toggle()` (lines 1935-1969) for Cancel's plain-POST-no-confirm shape.

```python
def _handle_calendar_disconnect_post(self):
    """POST /settings/calendar/disconnect. Two-step confirmation,
    server-side: a bare or non-matching confirm value renders the
    confirm page at 200 without touching anything — the client-side
    `confirm()` dialog is a misclick guard only, never the security
    control. Only an exact confirm match proceeds to clear the URL.
    """
    form = self.read_form()
    confirm = form.get(config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD)
    if confirm != config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE:
        ctx = self.page_context()
        body = config_page.calendar_disconnect_confirm_page(ctx)
        return self.send_html(200, self._page_shell_for(DISPLAY_ROUTE, body, ctx))
    state_dir = self.args.state_dir
    if calendar_rules.save_calendar_url(state_dir, calendar_rules.CLEAR_CALENDAR_URL):
        return self.redirect("%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_DISCONNECTED)))
    return self.redirect("%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))
```
`_handle_update_install_post()` follows this exact shape: `confirm != "yes"` (or absent) → render `update_install_confirm_page(ctx, version, next_wake_text)` at 200; `confirm == "yes"` → write to the release registry, redirect with a flash key. Error redirects use the same `"%s?flash=%s" % (route, quote(FLASH_KEY_...))` convention with new `FLASH_KEY_UPDATE_SCHEDULE_FAILED`/`FLASH_KEY_UPDATE_CANCEL_FAILED` keys added to the existing `FLASH_MESSAGES` dict (`companion/app.py` lines ~219-253), matching `FLASH_KEY_QUICK_FAILED`'s wording style ("Couldn't change that — please try again." → "Couldn't schedule that update — please try again.").

## Shared Patterns

### Authentication / access control
**Source:** device side — the existing bearer-token gate already covering `/device/v1/display` (`stub-server/byos_server.py` `bearer_ok()`, lines 488-491). The OTA offer rides this same authenticated channel; no new device auth needed.
**Apply to:** `stub-server/byos_server.py`'s new firmware-offer composition and firmware-image route.

Companion side — existing session-cookie auth (`companion/auth.py`) already gates every page/POST; no new auth mechanism for the Update page or its routes.
**Apply to:** `companion/pages/update_page.py`, the new `/update*` routes in `companion/app.py`.

### No-JS-first confirmation
**Source:** `companion/pages/config_page.py::calendar_disconnect_confirm_page()` + `companion/app.py::_handle_calendar_disconnect_post()` (excerpts above).
**Apply to:** `companion/pages/update_page.py::update_install_confirm_page()` and its POST handler. D-04 explicitly requires this to work without JS; the `<dialog>`/`panel-lookup-dialog` pattern is optional sugar only (UI-SPEC's own resolution, not the security gate).

### Flash-message error reporting
**Source:** `companion/app.py` `FLASH_MESSAGES` dict (~lines 219-253) and the `"%s?flash=%s" % (route, quote(FLASH_KEY_...))` redirect convention used throughout `_handle_*_post()` methods.
**Apply to:** every new `/update*` POST handler's failure paths.

### Push notification, EN/FR
**Source:** `server/notify.py` (excerpt above) — one-attempt, never-raises, `_BODY_FR` dict keyed by the English string.
**Apply to:** the new firmware-installed/failed notification call sites (wherever the server records OTA outcome — likely `server/poll_loop.py` or the release registry module, per Claude's Discretion in CONTEXT.md).

### On-device dithered hold screen
**Source:** `firmware/main/fault_screen.c`/`.h` in full (excerpts above) — `DITHER_TARGET_LEVEL`, the two-row Floyd-Steinberg accumulator, the mask-stamp technique, the `_Static_assert` buffer-size contract, the `tick` watchdog-feed callback.
**Apply to:** the new "Updating…" screen (`firmware/main/updating_screen.c`/`.h` or a generalised `fault_screen.c`), and `server/plane/render.py`'s `_build_updating_canvas`/`draw_updating_icon` (built on the existing `_build_dimmed_hold_canvas()` template, `DIMMED_LABEL_FONT`/`DIMMED_RULE_WIDTH_PX`/`DIMMED_BODY_FONT` constants reused verbatim per UI-SPEC).

### CI secret handling (never interpolated into `run:` text)
**Source:** `.github/workflows/ci.yml`'s existing `Deploy`/`Trust the production host key` steps:
```yaml
env:
  DEPLOY_HOST_KEY: ${{ secrets.DEPLOY_HOST_KEY }}
run: |
  install -d -m 700 ~/.ssh
  printf '%s\n' "$DEPLOY_HOST_KEY" >> ~/.ssh/known_hosts
```
**Apply to:** the new firmware-signing step in `.github/workflows/firmware.yml` (D-10's `FW_SIGNING_KEY` secret) — RESEARCH.md's own Code Examples section already gives the adapted signing step following this exact convention; do not deviate to `${{ }}`-interpolated `run:` text.

### Host-testable pure-C validation/logic
**Source:** `firmware/tests/test_validate.c` (`cc -Wall -Wextra -std=c11 main/validate.c tests/test_validate.c -o /tmp/tv && /tmp/tv`, `assert()`-based, one function-family per test block) and `firmware/tests/run_host_tests.sh`'s naming-convention discovery.
**Apply to:** `firmware/tests/test_ota_verify.c` (size/hash-check helper, OTA-02/OTA-05/OTA-06 device-side decision logic).

### Atomic file writes for server-side state
**Source:** not yet on `main` (Phase 36's `atomic_write`/`exclusive_lock` — confirmed absent by RESEARCH.md's own verification pass). Closest present-day shape: `stub-server/byos_server.py::save_state()`/`save_registry()`/`save_battery_state()` (write-to-`.tmp`-then-`os.replace()` pattern, e.g. lines 461-465).
**Apply to:** the new release registry (`server/firmware_registry.py` or wherever Claude's Discretion places it) — **must switch to Phase 36's real helpers once landed (G-41)**; the `.tmp` + `os.replace()` idiom shown here is the fallback shape only if the plan somehow executes before Phase 36 lands, which G-41 is designed to prevent.

## No Analog Found

Files/behaviors with no close match in the codebase today — planner should follow RESEARCH.md's patterns and Claude's Discretion resolutions instead of an existing file:

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `server/firmware_registry.py` (or equivalent) | model/store | CRUD | No release/version registry concept exists yet; nearest shape is `server/device_config.py`'s single JSON document, not a multi-entry, appendable registry. Also blocked on Phase 36's atomic-write/lock helpers (G-41). |
| Signed-app verification Kconfig + `espsecure.py` CI signing step | config / CI | batch | No signing of any kind exists in this codebase today (RESEARCH.md: "Not present" in `firmware/sdkconfig*.defaults`). Follow RESEARCH.md's Code Examples section (Kconfig block, CI signing step) verbatim as the starting point — there is no local precedent to extract instead. |
| `.github/workflows/firmware-chain-check.yml` (OTA-11, Let's Encrypt chain guard) | CI config | batch | No scheduled or network-reaching CI workflow exists in this repo today; every existing workflow (`ci.yml`, `firmware.yml`) triggers on push/PR only. New territory — mirror only the job/step *conventions* (name, `runs-on`, `permissions: contents: read` header) from `firmware.yml`/`ci.yml`, not a trigger shape. |
| Content-addressed `/img/<sha>.bin` or `/fw/<sha>.bin` byos route | route | file-I/O | Confirmed absent on `main` (RESEARCH.md verification table) — INT-05 has not landed. Do not invent this route's exact shape; re-derive from INT-05's actual landed code at plan time (G-41). |
| `firmware/main/ota.c`'s ESP-IDF-specific OTA API calls (`esp_https_ota_*`, `esp_ota_*`) | service | streaming | No OTA code exists anywhere in this codebase (deliberately excluded at Phase-1 vendoring, per VENDOR.md). The mechanical skeleton is re-derivable from the pinned upstream commit (RESEARCH.md Sources), not from anything currently in `main`. |

## Metadata

**Analog search scope:** `firmware/main/`, `firmware/tests/`, `firmware/tools/`, `stub-server/`, `server/` (top level + `server/plane/`), `companion/` (`app.py`, `layout.py`, `pages/`, `i18n_fr/`, `static/`), `.github/workflows/`, `deploy/`.
**Files scanned (read in full or via targeted grep+read):** `firmware/main/{fault_screen.c,fault_screen.h,state_machine.c,app_main.c,api_client.c,validate.c}`, `firmware/{partitions.csv,sdkconfig.defaults,build.sh,CMakeLists.txt}`, `firmware/tests/test_validate.c`, `stub-server/byos_server.py`, `server/{notify.py,poll_loop.py}`, `companion/{app.py,layout.py}`, `companion/pages/config_page.py`, `.github/workflows/{firmware.yml,ci.yml}`, `deploy/deploy.sh`.
**Pattern extraction date:** 2026-09-25.
