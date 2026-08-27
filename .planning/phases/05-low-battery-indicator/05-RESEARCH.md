# Phase 05: Low-Battery Indicator (05-02 plan) - Research

**Researched:** 2026-08-27
**Domain:** ESP32-S3 ADC hardware bring-up (firmware) + cross-process state plumbing (Python server) + minimal Pillow icon rendering
**Confidence:** MEDIUM overall — HIGH on the server/render plumbing and ESP-IDF adc_oneshot/adc_cali API shape (official docs), LOW-MEDIUM on the exact battery-sense GPIO for this specific board combination (no official Seeed documentation exists; findings are triangulated from a Seeed forum thread and this repo's own already-claimed pin map)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (threshold):** Lock a concrete threshold now: **3500 mV**. Sits with real margin above `hardware/logtools.py`'s existing `--cutoff-mv 3400` convention (used with `--expect-depleted` to mean "genuinely depleted"), so the warning fires with days of runway left. Trivially adjustable once 05-01 Tasks 2-3 produce a real discharge curve — do not block this plan on that data.
- **D-02 (basis):** Trigger is based on **raw millivolts**, not a derived percentage. No real discharge curve exists yet for this pack, so a percentage would be fabricated precision. Consistent with how `check-battery`/`hardware/logtools.py` already reasons about this pack.
- **D-03 (firmware scope):** This plan includes the real hardware bring-up, not just server-side plumbing against a fake value. `firmware/main/api_client.c`'s `telemetry_headers()` currently sends `X-Battery-Mv: "0"` unconditionally. Scope: identify the XIAO ESP32-S3 Plus's battery-voltage-sense circuit/GPIO (unresearched — no ADC pin was documented anywhere in `hardware/` before this research), wire a real ADC read, and verify the reported mV against a real multimeter reading on the already-flashed device — same `checkpoint:human-verify` pattern Phase 1's bring-up used.
- **D-04 (visual — supersedes 03-CONTEXT.md's D-12):** The indicator is a **battery icon glyph**, not text — outline (body + terminal nub, partial fill), **White/Ivory, not Yellow**. This is the poster's first and only icon — a deliberate, confirmed exception to the project's text-only visual language.
- **D-05 (placement):** Own dedicated zone, **bottom-left** — the one area with no existing element in the locked two-flight layout. Visually balances the previous-flight card (bottom-right).
- **D-06 (conditional):** The zone is **conditionally rendered** — present only when the battery is actually low, invisible/absent otherwise, same principle as the previous-flight card (`03-CONTEXT.md` D-25).
- **D-07 (state-color unaffected):** The existing Blue (`departing`)/Green (`arriving`) state background is **completely unaffected**. The two signals (state = background color, battery = bottom-left icon) coexist independently.

### Claude's Discretion

- Exact final pixel position/size of the battery icon within "bottom-left, moderate size" — **resolved by `05-UI-SPEC.md`**: total bounding box `(64, 1504, 136, 1536)`, 72×32px.
- Exact battery-glyph line weight, corner style, and fill-level rendering — **resolved by `05-UI-SPEC.md`**: `BATTERY_ICON_STROKE_PX=3`, square corners, single fixed `BATTERY_ICON_FILL_FRAC=0.22` (not a live gauge).
- Hysteresis/debounce on the threshold crossing — **resolved by `05-UI-SPEC.md`**: `BATTERY_LOW_THRESHOLD_MV=3500` / `BATTERY_LOW_CLEAR_MV=3600` (100mV re-arm buffer).
- How the mV value threads from the HTTP header through `poll_loop.py`/`poll_state.json` into `render.py`'s active-canvas builder — **open**, this document's Architecture Patterns section below is the answer the planner should use.
- Exact GPIO/ADC approach on the XIAO ESP32-S3 Plus (voltage divider ratio, `esp_adc` calibration) — **this document's primary research question**, see below.

### Deferred Ideas (OUT OF SCOPE)

- A live/proportional battery gauge (icon fill reflecting the actual mV reading, percentage, or days-remaining) — not requested. DEVICE-04's plain wording is satisfied by a single fixed low-battery glyph. A future richer battery UI belongs to the deferred companion web interface (CFG-03).
- Exact tuned threshold from real discharge data — D-01's 3500 mV is a reasoned estimate; revisit once 05-01 Tasks 2-3 (deliberately parked until end of project) produce real data. A one-line constant change, not a replan.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEVICE-04 | User can see a low-battery indicator on the frame when the battery is running low | This document identifies (a) the ADC read path on the exact XIAO ESP32-S3 Plus + EE02 hardware combo, including a real GPIO conflict that must be resolved before wiring anything, (b) the cross-process state-plumbing design needed because the HTTP-serving process and the rendering process are two separate systemd units, and (c) the ESP-IDF driver API shape for a correct, calibrated raw-to-mV conversion. `05-UI-SPEC.md` already resolves the visual contract; this document resolves the data path that feeds it. |
</phase_requirements>

---

## Summary

**Correction (2026-08-27, after the developer flatly rejected any soldering/external-resistor work):** this section originally concluded, based only on a bare-XIAO-module forum thread, that no factory battery-sense circuit exists and that a hand-soldered external divider was required. That conclusion was wrong for this project's actual hardware. **The EE02 driver board itself — not the bare XIAO module — has a factory-populated battery-voltage divider already wired to `A0 (GPIO1)`, with an ADC-enable line at `D5 (GPIO6)`.** This is documented on Seeed's own wiki, explicitly listed as applicable to the EE02/EE03/EE04/EE05 family [CITED: wiki.seeedstudio.com/ee04_with_platformio/ — "Applicable to EE02 / EE03 / EE04 / EE05", pin table `A0 (GPIO1)` measurement / `D5 (GPIO_6)` enable, `VOLTAGE_DIVIDER_RATIO 2.0`, reference `readBatteryVoltage()` function]. **No soldering, no external resistors, no continuity check before wiring anything — the circuit already exists on the board the developer already owns.** GPIO10 ("ADC_BAT" on the bare module, per the original forum thread) was never the right pin for this hardware stack in the first place and is irrelevant now — it remains correctly claimed by the e-paper panel's DC line (`firmware/sdkconfig.ee02.defaults`: `CONFIG_FP_PIN_EPD_DC=10`), which is a real fact worth keeping on record, just not the reason GPIO1 is the answer. One residual gap: the cookbook page's applicability banner names all four EE0x boards, but its own worked example and prose specifically say "EE04" — high confidence, not 100% certainty, that EE02 shares the identical circuit. The plan's hardware task should confirm this the cheap, solder-free way: flash firmware that enables GPIO6 and reads GPIO1, and check the reported millivolts look like a real battery voltage (roughly 3000-4200mV) rather than 0 or noise — no tool, no risk, no purchase required either way.

Architecturally, the value's journey is more involved than the UI-SPEC's data-contract section implies: the device sends `X-Battery-Mv` as an HTTP header on every `/device/v1/display` poll, received by `stub-server/byos_server.py` — a **long-running HTTP-serving systemd unit** (`skypane-byos.service`) — but the panel image is produced by a **completely separate, independently-triggered oneshot process** (`server/poll_loop.py`, run every 30s by `skypane-poll.timer`) that has no HTTP request context at all. These two processes only share a filesystem directory (`SKYPANE_STATE_DIR`). Today, `byos_server.py` only prints the battery header to stdout (`log_telemetry()`) — it persists nothing. This plan must add a small, single-writer state file that `byos_server.py` writes and `poll_loop.py` reads before each render, plus the hysteresis "is the warning currently armed" bit, which belongs in `poll_state.json` since that is already `poll_loop.py`'s own cross-cycle state.

On the firmware side, the correct ESP-IDF 5.3 API is the modern `esp_adc` component (`adc_oneshot` + `adc_cali`, ADC1 unit, `ADC_ATTEN_DB_12`, curve-fitting calibration) — not the older `adc1_get_raw()`/`esp_adc_cal_characterize()` API that dominates older tutorials and is deprecated as of this project's pinned IDF version. The pure "raw mV → real battery mV" divider-ratio math should be split into its own hardware-independent function so it can be host-tested with the project's existing `cc`-only test harness pattern (`firmware/tests/run_host_tests.sh`), the same way `backoff.c`/`panel_guard.c` already are. The ADC peripheral read itself still cannot be host-tested, but the human-verify step is now a plain flash-and-observe check (does the reported mV look like a real battery voltage?), not a pre-soldering continuity/isolation check — there is no soldering step in this plan at all.

**Primary recommendation:** Drive `D5 (GPIO6)` high to enable the EE02's onboard divider, read `A0 (GPIO1)` (ADC1 channel 0) via `adc_oneshot`+`adc_cali` (curve-fitting scheme, `ADC_ATTEN_DB_12`), apply the board's documented 2:1 divider ratio to recover real battery mV in a pure, host-testable function; persist the reading server-side in a new single-writer `battery_state.json` written by `byos_server.py` and read by `poll_loop.py`, with the D-01/D-06 threshold-and-hysteresis decision computed in `poll_loop.py` and stored as a boolean in `poll_state.json`; `render.py` gains one new conditional draw call per `05-UI-SPEC.md`'s already-locked geometry. No new hardware, no soldering, no external components.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Battery voltage sensing (ADC read + calibration) | Device firmware (ESP32-S3) | — | Only the device has physical access to the battery voltage; must happen on-device, once per wake, before the HTTP poll |
| Telemetry transport (mV → server) | Device firmware → API/Backend | — | Already-existing wire contract (`X-Battery-Mv` header, PROTOCOL.md §2); this plan fills in a real value, doesn't change the contract |
| Telemetry receipt + persistence | API/Backend (`byos_server.py`, the HTTP-serving process) | — | Only process with the HTTP request/header in scope; must persist to disk since it does not render |
| Threshold + hysteresis decision | API/Backend (`poll_loop.py`, the render-triggering process) | — | This process already owns `poll_state.json` (the project's only precedent for cross-cycle decision state); keeps the decision co-located with the state it's derived from |
| Visual rendering (icon draw) | API/Backend (`render.py`, Pillow raster pipeline) | — | Not a browser/client tier in this project — "frontend" is server-side raster generation (per `05-UI-SPEC.md`'s scope note); `render.py` is the sole compositor |
| Panel display | Device firmware (e-paper blit) | — | Firmware blits whatever 960,000-byte image the server serves; no rendering logic of its own |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `esp_adc` (ESP-IDF built-in component: `adc_oneshot` + `adc_cali`) | Bundled with ESP-IDF 5.3.1 (this project's pinned toolchain, `firmware/build.sh`'s `espressif/idf:v5.3.1`) [CITED: docs.espressif.com/projects/esp-idf/en/v5.3] | Read the battery-sense GPIO's raw ADC value and convert it to calibrated millivolts | This is Espressif's own current (non-deprecated) ADC driver as of IDF 5.x — the same "use the platform's own audited component, don't hand-roll" principle this project already follows for BLE/TLS/HTTP |

No new external package is installed for this plan on either side (firmware or server) — `esp_adc` is part of the already-vendored ESP-IDF toolchain (`REQUIRES` addition to `firmware/main/CMakeLists.txt` only, no new dependency fetch), and the server-side plumbing is Python stdlib `json`/file I/O, matching every existing state-file pattern in this codebase (`byos_server.py`'s `save_state()`, `poll_loop.py`'s `save_poll_state()`/`write_panel_atomic()`).

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow `ImageDraw.rectangle()` | Already vendored (`server/requirements.txt`) | Draw the icon's outline/nub/fill rectangles | Already the project's only drawing primitive (`05-UI-SPEC.md`'s Rendering Rules) — no new dependency |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `adc_oneshot` + `adc_cali` (ESP-IDF 5.x current API) | Legacy `driver/adc.h` (`adc1_get_raw()` + `esp_adc_cal_characterize()`) | Deprecated as of ESP-IDF 5.x; still compiles (with warnings) but is the API most tutorials/forum posts reference since training-data-era content predates the 5.x migration — do not use it, it is exactly the kind of stale-API trap this project's own ESP-IDF 5.3.1 pin is meant to avoid [CITED: github.com/espressif/esp-idf adc_types.h deprecation] |
| Hand-built external voltage divider on a free GPIO | Adding a dedicated fuel-gauge IC (e.g. MAX17048) | Rejected — no evidence such a chip exists on this board (see Package Legitimacy / hardware notes below); would be new hardware not in `hardware/BOM.md`, disproportionate for a threshold-only (not fuel-gauge-accuracy) requirement per D-02's own "raw millivolts, not a fabricated percentage" reasoning |
| A single shared `poll_state.json` written by both processes | Two separate single-writer files (`battery_state.json` for the HTTP process, `poll_state.json` unchanged for the render process) | The two-file split is recommended — see Architecture Patterns below; a shared file written by two independent OS processes risks a lost update between `byos_server.py`'s and `poll_loop.py`'s own read-modify-write cycles, since neither currently coordinates with the other via a lock |

**Installation:** No new install step. `esp_adc` is enabled by adding `"esp_adc"` to the existing `REQUIRES` list in `firmware/main/CMakeLists.txt` (currently: `"nvs_flash" "esp_timer" "driver" "heap" "esp_wifi" "esp_netif" "esp_event" "esp_http_client" "esp-tls" "mbedtls" "json" "esp_app_format" "esp_hw_support"`).

**Version verification:** `esp_adc` is not a registry package — it ships inside the pinned `espressif/idf:v5.3.1` Docker image this project's `firmware/build.sh` already uses (verified: this is the same toolchain version used for every other firmware plan in this project; no separate lookup applies). The `adc_oneshot_get_calibrated_result()` convenience call and `ADC_ATTEN_DB_12` constant (superseding deprecated `ADC_ATTEN_DB_11`) are both present as of IDF 5.1+ and confirmed still current at 5.3 [CITED: docs.espressif.com/projects/esp-idf/en/v5.3/esp32s3/api-reference/peripherals/adc_oneshot.html].

---

## Package Legitimacy Audit

Not applicable — this plan installs **no new external package** in either ecosystem. Firmware adds only a built-in ESP-IDF component (`esp_adc`, already vendored inside the pinned `espressif/idf:v5.3.1` image) to its `CMakeLists.txt` `REQUIRES` list. The server side uses only Python stdlib (`json`, `os`) for the new state file, matching every existing state-persistence pattern in this codebase. No `npm view`/`pip index`/`cargo search` check applies.

**Packages removed due to [SLOP] verdict:** none (none proposed).
**Packages flagged as suspicious [SUS]:** none.

---

## Architecture Patterns

### System Architecture Diagram

```
                          DEVICE (firmware, one wake cycle)
  ┌──────────────────────────────────────────────────────────────────┐
  │  app_main.c wakes                                                  │
  │    -> fp_battery_read_mv()   [NEW: battery.c]                      │
  │         adc_oneshot_read(ADC1, ch0/GPIO1) -> raw                   │
  │         adc_cali curve-fit  -> divider_mv                          │
  │         battery_math_apply_divider(divider_mv) -> real_mv [pure]   │
  │    -> fp_poll_once() -> fp_api_get_display()                       │
  │         telemetry_headers(): X-Battery-Mv = real_mv (was "0")      │
  └───────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS GET /device/v1/display
                               │ (header X-Battery-Mv: "3487")
                               v
  ┌──────────────────────────────────────────────────────────────────┐
  │  skypane-byos.service  (stub-server/byos_server.py, long-running)  │
  │    do_GET("/device/v1/display")                                    │
  │      log_telemetry()        [existing: stdout print only]          │
  │      save_battery_state()   [NEW: persist X-Battery-Mv + ts]        │
  │        -> <STATE_DIR>/battery_state.json   (single writer: this    │
  │           process only — poll_loop.py never writes this file)      │
  │      serves whatever panel.bin is currently on disk (unchanged)    │
  └───────────────────────────┬──────────────────────────────────────┘
                               │  same STATE_DIR, filesystem only
                               │  (no IPC, no shared memory — two
                               │   independent OS processes)
                               v
  ┌──────────────────────────────────────────────────────────────────┐
  │  skypane-poll.timer -> skypane-poll.service (server/poll_loop.py,  │
  │  oneshot, every 30s, NO HTTP request context of its own)            │
  │    run_once():                                                     │
  │      load_poll_state()  [existing]                                 │
  │      load_battery_state()  [NEW: read-only]                        │
  │        -> battery_mv (or None if never yet reported)               │
  │      battery_low = apply_hysteresis(battery_mv,                    │
  │            poll_state.get("battery_low_active", False))  [NEW]     │
  │        -> True/False, persisted back into poll_state["battery_low_ │
  │           active"] so the 100mV re-arm buffer (D-UI-SPEC's         │
  │           BATTERY_LOW_CLEAR_MV) survives across 30s cycles          │
  │      render.render_panel(..., battery_low=battery_low)  [NEW arg]  │
  │        -> render.py draws the icon only if battery_low is True     │
  │      write_panel_atomic()  [existing, unchanged shape]              │
  └──────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
firmware/main/
├── battery.c / battery.h     # NEW — ADC peripheral read + calibration (fp_battery_read_mv())
├── battery_math.c / .h       # NEW — pure divider-ratio math, host-testable (no ESP-IDF headers)
firmware/tests/
├── test_battery_math.c       # NEW — host-compiled with plain `cc`, same pattern as test_backoff.c
server/
├── plane/render.py           # MODIFIED — new draw_battery_icon(), battery_low param on _build_active_canvas()/_build_empty_canvas()
├── poll_loop.py               # MODIFIED — load_battery_state(), apply_hysteresis(), pass battery_low into render_panel()
stub-server/
├── byos_server.py             # MODIFIED — persist X-Battery-Mv to battery_state.json alongside existing log_telemetry()
```

### Pattern 1: Split hardware-dependent code from pure logic (existing project convention)

**What:** Separate the ESP-IDF peripheral call (cannot be host-tested) from the arithmetic that converts a raw calibrated ADC millivolt reading into "real battery millivolts" via the divider ratio (pure integer/float math, fully host-testable).

**When to use:** Any new firmware module this project adds — this is the exact shape `backoff.c` (pure), `panel_guard.c` (pure), vs `wifi.c`/`api_client.c` (ESP-IDF-dependent, never host-tested) already establish.

**Example:**
```c
/* battery_math.h — no ESP-IDF includes, host-testable */
#pragma once
#include <stdint.h>

/* divider_mv: what the ADC (after adc_cali) measured at the GPIO, i.e.
 * the battery voltage AFTER the EE02's onboard resistor divider has halved it.
 * Returns the real battery millivolts (divider_mv * 2 for a 1:2 divider). */
uint32_t battery_math_apply_divider(uint32_t divider_mv);
```
```c
/* battery.c — the ESP-IDF-dependent half, not host-tested (VENDOR.md/BRINGUP-LOG.md
 * pattern: verified via checkpoint:human-verify + real multimeter instead) */
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "battery_math.h"

esp_err_t fp_battery_read_mv(uint32_t *out_mv)
{
    adc_oneshot_unit_handle_t adc1;
    adc_oneshot_unit_init_cfg_t init_cfg = { .unit_id = ADC_UNIT_1 };
    esp_err_t err = adc_oneshot_new_unit(&init_cfg, &adc1);
    if (err != ESP_OK) return err;

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    /* GPIO1 == ADC1_CHANNEL_0 on ESP32-S3 */
    err = adc_oneshot_config_channel(adc1, ADC_CHANNEL_0, &chan_cfg);
    if (err != ESP_OK) { adc_oneshot_del_unit(adc1); return err; }

    adc_cali_handle_t cali;
    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    err = adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali);
    if (err != ESP_OK) { adc_oneshot_del_unit(adc1); return err; }

    int divider_mv = 0;
    err = adc_oneshot_get_calibrated_result(adc1, cali, ADC_CHANNEL_0, &divider_mv);
    adc_oneshot_del_unit(adc1); /* cali handle intentionally leaked for this
                                    one-shot-per-wake call — deep sleep frees
                                    it anyway; matches the project's other
                                    single-call-per-wake peripheral usage */
    if (err != ESP_OK) return err;

    *out_mv = battery_math_apply_divider((uint32_t)divider_mv);
    return ESP_OK;
}
```
Source: adapted from [CITED: docs.espressif.com/projects/esp-idf/en/v5.3/esp32s3/api-reference/peripherals/adc_oneshot.html] against this project's own module-per-responsibility convention (`firmware/VENDOR.md`'s vendored-file table).

### Pattern 2: Single-writer state files for cross-process plumbing (new to this project, but matches its existing atomic-write discipline)

**What:** Any value that must cross from one systemd unit to another goes through a file with exactly one writer process. `byos_server.py` already uses `save_state()`'s tmp-write-then-`os.replace()` pattern for `byos_state.json`; `poll_loop.py` already does the same for `poll_state.json` and `panel.bin`. This plan adds a third such file, `battery_state.json`, owned exclusively by `byos_server.py`.

**When to use:** Any time two independently-scheduled systemd units (one long-running HTTP server, one 30s-cadence oneshot) need to share a value neither one can compute alone.

**Example:**
```python
# stub-server/byos_server.py — same shape as the existing save_state()
def battery_state_path(state_dir):
    return os.path.join(state_dir, "battery_state.json")

def save_battery_state(state_dir, mv):
    tmp = battery_state_path(state_dir) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"battery_mv": mv, "received_at": time.time()}, fh)
    os.replace(tmp, battery_state_path(state_dir))

# inside do_GET's /device/v1/display branch, after self.log_telemetry():
raw = self.headers.get("X-Battery-Mv")
if raw and raw.isdigit() and raw != "0":  # "0" is the documented "unknown" sentinel
    save_battery_state(self.args.state_dir, int(raw))
```
```python
# server/poll_loop.py — read-only consumer, never writes this file
def load_battery_state(state_dir):
    try:
        with open(os.path.join(state_dir, "battery_state.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None  # never-yet-reported is a legitimate, non-error state
```

### Anti-Patterns to Avoid

- **Writing `battery_mv` directly into `poll_state.json` from `byos_server.py`:** two independent OS processes doing read-modify-write on the same JSON file is a real lost-update race (neither currently uses a file lock); keep the HTTP-received value in its own single-writer file and let `poll_loop.py` (the sole writer of `poll_state.json`) merge it in.
- **Reading the battery ADC pin more than once per wake, or continuously:** this is a battery-powered, deep-sleep device — the whole architecture (DEVICE-05, `hardware/BATTERY-RUN.md`) is built around minimizing awake time; one read per wake, before the HTTP call, is correct.
- **Using `ADC_UNIT_2` (ADC2) for this reading:** ADC2 shares hardware with the Wi-Fi driver on ESP32-S3 and produces unreliable readings whenever Wi-Fi is active [CITED: docs.espressif.com adc_oneshot.html "Key Caveats"] — this device's wake cycle always has Wi-Fi active around the same time as any HTTP-triggered telemetry read, so ADC1 is the only safe choice regardless of which specific free GPIO is chosen.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ADC nonlinearity correction near the low/high end of the 0-3.3V range | A hand-fitted lookup table or manual multi-point calibration curve | `adc_cali_create_scheme_curve_fitting()` (ESP-IDF's own factory-eFuse-backed curve-fitting scheme, supported on ESP32-S3) | The ESP32-S3's ADC is documented as non-linear enough that Espressif ships and recommends its own calibration scheme specifically to correct it — reinventing this is exactly the kind of "not standard" firmware code this project has otherwise avoided (it vendors `esp_crt_bundle_attach`, `wifi_provisioning`, etc. rather than hand-rolling) |
| Cross-process state sharing between the HTTP server and the render loop | A new IPC mechanism (socket, shared memory, signal) | A single-writer JSON file in the already-shared `SKYPANE_STATE_DIR`, same tmp-write+`os.replace()` pattern already used three times in this codebase | Matches the project's own established, already-tested pattern; introducing a new IPC primitive for one boolean-ish value is disproportionate |

**Key insight:** every piece of this plan has a close precedent already living in this codebase (ADC calibration → Espressif's own component; cross-process state → the existing atomic-write pattern; host-testable-vs-not module split → `backoff.c` vs `wifi.c`). The research task was almost entirely "find the precedent," not "invent a new approach."

---

## Common Pitfalls

### Pitfall 1 (corrected 2026-08-27): GPIO10 is a red herring — the real battery-sense pin is A0 (GPIO1), already wired by the EE02 board

**What goes wrong:** Trusting the bare-XIAO-module forum thread that labels GPIO10 as "ADC_BAT" and either wiring anything to GPIO10 (which this project's EE02 profile already claims for the e-paper panel's DC line, `CONFIG_FP_PIN_EPD_DC=10`) or concluding — as this document originally, wrongly did — that no on-board battery-sense circuit exists at all and a hand-soldered divider is required.
**Why it happens:** GPIO10's "ADC_BAT" label describes the bare XIAO ESP32-S3 Plus module in isolation; it says nothing about the EE02 carrier board this project actually uses, which adds its own battery-sense circuit on different pins. Researching the module alone, without checking the EE0x driver-board family's own documentation, misses this entirely.
**How to avoid:** Use the EE02 driver board's own documented circuit: `A0 (GPIO1)` for the ADC read, `D5 (GPIO6)` as the enable line (drive high before sampling, matching the reference `readBatteryVoltage()` pattern) [CITED: wiki.seeedstudio.com/ee04_with_platformio/]. No wiring to GPIO10 required or wanted. Full claimed-pin list for cross-reference: `SCK=7, MOSI=9, CS_M=44, CS_S=41, DC=10, RST=38, BUSY=4, EN=43, KEY0=5, KEY1=3, KEY2=2` (`sdkconfig.ee02.defaults`) — GPIO1 and GPIO6 are both clear of this list, consistent with (not just coincidentally near) the EE02's own design.
**Warning signs:** Panel garbling or a "busy forever" refresh timeout would indicate GPIO10 got touched by mistake; a battery reading of exactly 0 or a wildly implausible value would indicate GPIO6 was never driven high (divider left un-powered) before the GPIO1 read.

### Pitfall 2 (corrected 2026-08-27): This is not "no divider exists" — it's "the divider is on the EE02 board, not the bare module"

**What goes wrong:** Assuming, because the bare XIAO ESP32-S3/S3 Plus module genuinely has no on-module divider, that the fully assembled device (module + EE02 driver board) has none either — and budgeting time/parts for a hand-built external divider that isn't needed.
**Why it happens:** Most XIAO ADC-pin research (forum threads, the module's own getting-started wiki) is scoped to the bare module, since XIAO modules are sold and documented standalone; this project's actual hardware is the module soldered onto Seeed's own EE02 carrier board, which adds circuitry the module-only docs don't mention. The EE0x driver-board family's own cookbook page is the correct source, not the module's page.
**How to avoid:** Confirm empirically, cheaply, and safely: flash firmware that drives GPIO6 high and reads GPIO1 via `adc_oneshot`, apply the documented 2:1 ratio, and check the result is in a plausible battery-voltage range (~3000-4200mV for this pack). No purchase, no soldering iron, no risk either way — a wrong or absent circuit just reads back an implausible number, it does not damage anything.
**Warning signs:** A reading that pegs at 0 or at the ADC's max value regardless of actual battery charge would indicate the enable pin wasn't driven, or (lower probability) that EE02 doesn't share EE04's exact circuit after all.

### Pitfall 3: Legacy `adc1_get_raw()`/`esp_adc_cal_characterize()` API surfaces in most search results and tutorials

**What goes wrong:** Copying a well-upvoted StackOverflow/forum snippet that uses the pre-5.0 ADC driver API, which still compiles under IDF 5.3.1 (with deprecation warnings) but is not the maintained path and lacks the newer curve-fitting calibration scheme.
**Why it happens:** Most publicly available ESP32 ADC code predates the IDF 4.x→5.x driver migration.
**How to avoid:** Use only `esp_adc/adc_oneshot.h` + `esp_adc/adc_cali_scheme.h`, matching this project's own "use the current, non-deprecated ESP-IDF surface" discipline already visible in `wifi.c` (uses `esp_netif`/`esp_event`, not legacy Wi-Fi APIs).
**Warning signs:** A build that emits `'adc1_get_raw' is deprecated` or references `esp_adc_cal_characterize()`.

### Pitfall 4: Two independent processes racing on one JSON file

**What goes wrong:** If `battery_mv` is written into the same `poll_state.json` that `poll_loop.py` also reads-modifies-writes every 30 seconds, an HTTP poll landing mid-cycle can have its write clobbered by `poll_loop.py`'s own next save, or vice versa — a real, timing-dependent bug that would not show up in any single-process test.
**Why it happens:** `byos_server.py` (event-driven, any time) and `poll_loop.py` (timer-driven, every 30s) are two separate OS processes with no lock or coordination today.
**How to avoid:** Keep the HTTP-received value in its own single-writer file (`battery_state.json`, written only by `byos_server.py`) per Architecture Pattern 2 above; let `poll_loop.py` remain the sole writer of `poll_state.json`, merging in a read-only load of the battery file each cycle.
**Warning signs:** An intermittently "stuck" or "reverted" battery reading that doesn't correlate with real device behaviour — a classic race-condition symptom.

### Pitfall 5: Hysteresis state forgotten between poll cycles

**What goes wrong:** Implementing the 3500/3600mV hysteresis (`05-UI-SPEC.md`'s `BATTERY_LOW_THRESHOLD_MV`/`BATTERY_LOW_CLEAR_MV`) as a stateless per-poll comparison (`if mv <= 3500: draw icon`) defeats its own purpose — a reading oscillating between 3490 and 3510 across consecutive polls would still flicker the icon on/off, exactly what the hysteresis buffer exists to prevent.
**Why it happens:** The threshold comparison is easy to write as a pure function of the current reading alone, forgetting it needs the *previous* armed/disarmed state as an input too.
**How to avoid:** Persist a `battery_low_active` boolean in `poll_state.json` (the only place with cross-cycle memory in this architecture) and implement the hysteresis as: armed stays armed until reading ≥ `BATTERY_LOW_CLEAR_MV`; disarmed stays disarmed until reading ≤ `BATTERY_LOW_THRESHOLD_MV`.
**Warning signs:** A test that only checks the threshold-crossing case and never checks "reading recovers to 3550 mV, between the two constants" — that case must NOT clear the warning.

---

## Code Examples

### Hysteresis (pure function, easy to unit test in `server/test_poll_loop.py`)

```python
# server/poll_loop.py
BATTERY_LOW_THRESHOLD_MV = 3500  # 05-CONTEXT.md D-01
BATTERY_LOW_CLEAR_MV = 3600      # 05-UI-SPEC.md hysteresis resolution

def apply_battery_hysteresis(battery_mv, was_active):
    """battery_mv: int or None (never yet reported). was_active: the
    previous poll's persisted battery_low_active value. Returns the new
    battery_low_active value — None input is treated as 'no signal yet',
    never as 'low', so a device that has not reported a battery reading
    at all does not spuriously show the icon."""
    if battery_mv is None:
        return was_active  # hold last-known state rather than guessing
    if was_active:
        return battery_mv < BATTERY_LOW_CLEAR_MV
    return battery_mv <= BATTERY_LOW_THRESHOLD_MV
```

### render.py integration point (matches `05-UI-SPEC.md`'s already-locked geometry)

```python
# server/plane/render.py
def draw_battery_icon(canvas, draw, ink_idx):
    """05-UI-SPEC.md geometry: body (64,1504,128,1536), nub (128,1513,136,1527),
    fill (67,1507,80,1533). Square corners, flat integer-index fills only."""
    body = (64, 1504, 128, 1536)
    nub = (128, 1513, 136, 1527)
    fill = (67, 1507, 80, 1533)
    _assert_within_canvas(body, "battery icon body")
    draw.rectangle(body, outline=ink_idx, width=3)
    draw.rectangle(nub, fill=ink_idx)
    draw.rectangle(fill, fill=ink_idx)

# _build_active_canvas(..., battery_low=False) and _build_empty_canvas(battery_low=False)
# each gain one new conditional call after their existing draw calls:
#     if battery_low:
#         draw_battery_icon(canvas, draw, fg_idx)   # active states: STATE_INK[state]
#         # empty state: IDX_BLACK, per 05-UI-SPEC.md's Color section
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `driver/adc.h` legacy API (`adc1_get_raw()`, `esp_adc_cal_characterize()`) | `esp_adc` component (`adc_oneshot` + `adc_cali`) | ESP-IDF v5.0 (deprecation), current in v5.3 (this project's pin) | Legacy API still compiles with warnings but should not be used in new ESP-IDF 5.3.1 code — most training-data-era tutorials reference the old API |
| `ADC_ATTEN_DB_11` | `ADC_ATTEN_DB_12` | ESP-IDF ~5.0-5.1 rename | Same behaviour, `DB_11` is a deprecated alias; use `DB_12` directly to avoid a compiler warning |

**Deprecated/outdated:** the legacy ADC driver header and its two-step `esp_adc_cal_characterize()`+`esp_adc_cal_raw_to_voltage()` calibration flow — replaced by the single `adc_cali_create_scheme_curve_fitting()` handle used directly by `adc_oneshot_get_calibrated_result()` or a manual `adc_cali_raw_to_voltage()` call.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 (corrected) | The EE02 driver board (not the bare XIAO module) has a factory battery-voltage divider wired to `A0 (GPIO1)`, enabled via `D5 (GPIO6)` | Summary, Pitfall 1/2 | Sourced from Seeed's own EE0x driver-board wiki cookbook [CITED: wiki.seeedstudio.com/ee04_with_platformio/], an official first-party source — materially stronger than the original single-forum-thread basis. Residual risk: the page's applicability banner names EE02/03/04/05 together but its worked example/prose specifically say "EE04" — treat as high-confidence, not certain, until confirmed by an actual flash-and-read on this project's real board (the plan's Task 2/3 does this) |
| A2 (corrected) | GPIO10 ("ADC_BAT" on the bare module per the original forum thread) is irrelevant to this project's actual battery-sense circuit and was never the right pin | Pitfall 1 | Low risk — independent of A1's residual uncertainty, since GPIO10 stays correctly claimed by the panel's DC line regardless of which pin turns out to be the real EE02 battery-sense pin |
| A3 | A 2:1 divider ratio (`VOLTAGE_DIVIDER_RATIO = 2.0` in Seeed's own reference code) is the correct ratio for this pack's ~3.0-4.2V range against the ESP32-S3's ADC ceiling | Common Pitfalls, Standard Stack | Sourced directly from Seeed's own reference `readBatteryVoltage()` function, not community-derived — comfortable headroom either way (4.2V/2=2.1V, well under the ADC's ~3.1V effective ceiling) |
| A4 | No dedicated fuel-gauge IC (e.g. MAX17048) exists on the XIAO ESP32-S3 Plus or EE02 board | Alternatives Considered | Based on absence of evidence in product pages/forum search, not an explicit "confirmed absent" statement from Seeed — if wrong, a fuel-gauge-based SOC% read would be a strictly better data source, but D-02 already locked "raw millivolts, not a percentage" as the basis regardless, so this assumption does not block the plan even if later found incomplete; also now moot in practice since the raw-mV divider circuit already exists on-board with zero extra cost |

---

## Open Questions

1. **(Resolved 2026-08-27) Is there a factory battery-sense circuit on this hardware, and does it require soldering?** No soldering required — `A0 (GPIO1)` + `D5 (GPIO6)` enable, per Seeed's own EE0x cookbook. See A1 above for the one residual (low-risk) uncertainty: whether EE02 specifically shares EE04's exact circuit, resolved cheaply by the plan's own flash-and-read verification step rather than by further research.

2. **(Resolved 2026-08-27) What resistor values are actually on hand / need ordering?** Moot — no external resistors or soldering setup needed. `hardware/BOM.md` does not need a new line item for this plan.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `espressif/idf:v5.3.1` Docker toolchain | Firmware build (`esp_adc` component) | Yes (already used by every prior firmware plan, `firmware/build.sh`) | v5.3.1 | — |
| Physical XIAO ESP32-S3 Plus + EE02 + battery pack | ADC bring-up, real-hardware verification | Yes — already flashed and bring-up-verified per `hardware/BRINGUP-LOG.md` (2026-08-25) | — | — |
| Multimeter | Voltage cross-check (D-03's own required verification step) | Assumed available — `hardware/BOM.md`'s battery-polarity section already assumes and requires one | — | Used only to sanity-check the reported mV against a real reading once firmware is flashed — not for a pre-work continuity/isolation check, since nothing is being soldered |

**Missing dependencies:** none. **Correction (2026-08-27):** the previous version of this table listed two ~200kΩ resistors and a soldering setup as an unconfirmed dependency — this was based on the (wrong) conclusion that no factory divider exists. The EE02 board's own onboard circuit (A1 above) makes this moot; no new hardware, no BOM addition, no soldering.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (server) | `pytest`-via-`coverage run` — `scripts/run-all-tests.sh`'s canonical 9-harness list, `server/test_poll_loop.py`/`server/test_render.py` are the relevant existing files |
| Framework (firmware, pure-logic only) | Plain `cc -std=c11`, no test framework — `firmware/tests/run_host_tests.sh`'s `run_suite()` pattern (compiles+runs a `.c` test file against its matching pure-logic `.c` implementation) |
| Config file | `pyproject.toml` (server coverage config, `fail_under=75`); `firmware/tests/run_host_tests.sh` (no separate config, a fixed script) |
| Quick run command (server) | `server/.venv/bin/python3 -m pytest server/test_poll_loop.py server/test_render.py -x` |
| Quick run command (firmware) | `sh firmware/tests/run_host_tests.sh` (runs all host-testable suites; a new `test_battery_math` entry gets appended to its `run_suite` call list) |
| Full suite command | `scripts/run-all-tests.sh` (server) + `sh firmware/tests/run_host_tests.sh` (firmware) — the project already runs both independently, never one combined command |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEVICE-04 | `battery_math_apply_divider()` correctly converts a divider-reduced mV reading back to real battery mV | unit (firmware, host `cc`) | `sh firmware/tests/run_host_tests.sh` | ❌ Wave 0 — new `firmware/tests/test_battery_math.c` |
| DEVICE-04 | `apply_battery_hysteresis()` correctly arms/holds/clears across the 3500/3600 boundary, including the `None`-reading (never-reported) case | unit (server) | `pytest server/test_poll_loop.py -k hysteresis -x` | ❌ Wave 0 — new test cases in `server/test_poll_loop.py` |
| DEVICE-04 | `render.py` draws the icon only when `battery_low=True`, at the exact `05-UI-SPEC.md` geometry, in the correct per-state ink color, and the panel stays pixel-identical to today when `battery_low=False` | unit (server, `_assert_within_canvas`-backed) | `pytest server/test_render.py -k battery -x` | ❌ Wave 0 — new test cases in `server/test_render.py` |
| DEVICE-04 | `byos_server.py` persists a valid `X-Battery-Mv` header to `battery_state.json`, and ignores/does not persist the `"0"` (unknown) sentinel | unit (stub-server) | `pytest stub-server/test_poll_cycle.py -k battery -x` | ❌ Wave 0 — new test cases in `stub-server/test_poll_cycle.py` (the fixture already references `"X-Battery-Mv": "3941"` at line 386, so a real telemetry-header fixture already exists to build from) |
| DEVICE-04 | Real ADC reading on physical hardware matches a real multimeter reading within a reasonable tolerance | manual-only (`checkpoint:human-verify`) | n/a — real hardware, no automated command | n/a — matches Phase 1's `hardware/BRINGUP-LOG.md` precedent exactly |

### Sampling Rate

- **Per task commit:** the relevant quick-run command above (server pytest subset, or firmware host-test script) for whichever side that task touches.
- **Per wave merge:** `scripts/run-all-tests.sh` (server, full 9-harness suite) + `sh firmware/tests/run_host_tests.sh` (firmware).
- **Phase gate:** both full suites green, plus the one `checkpoint:human-verify` real-hardware ADC-vs-multimeter cross-check, before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `firmware/tests/test_battery_math.c` — covers the pure divider-ratio conversion (DEVICE-04)
- [ ] `firmware/main/battery.c`/`battery.h`/`battery_math.c`/`battery_math.h` — new module pair, following the `backoff.c`/`panel_guard.c` (pure) vs `wifi.c` (ESP-IDF-dependent) split convention
- [ ] New test cases appended to `server/test_poll_loop.py`, `server/test_render.py`, `stub-server/test_poll_cycle.py` — no new test *files* needed, these three harnesses already exist and are already in `scripts/run-all-tests.sh`'s `HARNESSES` array
- [ ] `firmware/main/CMakeLists.txt`'s `SRCS`/`REQUIRES` — add the two new `.c` files and the `"esp_adc"` component

*(No new server-side test framework or fixture scaffolding needed — every relevant harness file already exists in the codebase.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Unchanged — this plan adds a telemetry value to an already-authenticated (`Authorization: Bearer`) endpoint, doesn't touch auth |
| V3 Session Management | No | Not applicable — stateless bearer-token model, unchanged |
| V4 Access Control | No | The new `battery_state.json` file is read/written only by the two already-privileged local processes (`skypane-byos.service`/`skypane-poll.service`), both already running as the unprivileged `skypane` system user per `deploy/skypane-*.service`'s existing hardening (`ProtectSystem=strict`, `ReadWritePaths=/opt/skypane/state`) — no new access-control surface |
| V5 Input Validation | **Yes** | The `X-Battery-Mv` header is attacker-influenceable input (any client that has a valid bearer token, or — since `/device/v1/display` is a GET with header-based telemetry, not body-validated — potentially any client, since this project's PROTOCOL.md sends all four telemetry headers unconditionally without re-validating their content server-side today). New validation: reject/ignore non-numeric, negative, or implausibly large values (e.g. cap sanity-check at some high bound like 10,000mV) before persisting or before it can influence the hysteresis decision — matches the existing defensive-parsing precedent in `firmware/main/api_client.c`'s own strict field validation on the client-received side (`image_hash_valid()`, `url_valid()`, `sleep_ok` bounds) |
| V6 Cryptography | No | Not applicable — no new cryptographic operation |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Malformed/out-of-range `X-Battery-Mv` header value (e.g. non-numeric, negative, or absurdly large) causing a crash or corrupt persisted state | Tampering / Denial of Service | Strict server-side parsing before persistence: `raw.isdigit()` + a sane upper bound (see V5 above) — reject anything else silently (log, don't persist, don't crash), same defensive posture `byos_server.py`'s existing `read_body_json()` already uses for malformed JSON bodies |
| A stuck/never-clearing low-battery warning if `battery_state.json` becomes unreadable/corrupted mid-write | Availability (not a STRIDE attack, but a real reliability risk) | `load_battery_state()` treats any read/parse failure as "no signal" (returns `None`), never as a crash — mirrors every other state-load function in this codebase (`load_poll_state()`, `load_state()` in `byos_server.py`) which already follow "malformed/missing state file degrades to empty, never crashes" |

---

## Sources

### Primary (HIGH confidence)
- `docs.espressif.com/projects/esp-idf/en/v5.3/esp32s3/api-reference/peripherals/adc_oneshot.html` [CITED] — `adc_oneshot`/`adc_cali` API shape, `ADC_ATTEN_DB_12`, ADC2/Wi-Fi caveat
- This repository's own `firmware/sdkconfig.ee02.defaults`, `firmware/main/api_client.c`, `firmware/VENDOR.md`, `stub-server/byos_server.py`, `server/poll_loop.py`, `server/plane/render.py`, `server/panel_format.py`, `deploy/skypane-*.service`, `deploy/skypane.env.example` [VERIFIED: direct file read] — the actual pin map, telemetry contract, and two-process architecture this plan must fit into

### Secondary (MEDIUM confidence)
- `forum.seeedstudio.com/t/xiao-esp32s3-plus-adc-bat-on-gpio10/291965` [CITED] — GPIO10 "ADC_BAT" schematic label, no populated divider on the real board, 1:2 divider workaround reports
- `wiki.seeedstudio.com/ee04_with_platformio/` [CITED, added 2026-08-27 correction] — the authoritative source for this project's actual hardware: EE0x driver-board family cookbook, explicitly "Applicable to EE02 / EE03 / EE04 / EE05", documents `A0 (GPIO1)` battery-ADC pin, `D5 (GPIO6)` enable pin, `VOLTAGE_DIVIDER_RATIO = 2.0`, and a reference `readBatteryVoltage()` function
- `wiki.seeedstudio.com/getting_started_with_ee02/` [CITED] — confirms EE02's JST 2.0mm battery connector and built-in charging IC (consistent with a board designed for real battery operation), though this particular page does not itself list the ADC pin table
- `wiki.seeedstudio.com/xiao_esp32s3_getting_started/` [CITED] — confirms the *bare* XIAO ESP32-S3 module has no free GPIO for battery sensing ("all GPIO pins... are assigned their own functions") — this is why the circuit has to live on the EE02 carrier board, not the module, and explains why researching the module alone (the original research's mistake) missed it
- `wiki.seeedstudio.com/check_battery_voltage/` [CITED] — confirms XIAO ESP32C3 has no factory divider either (a hand-built workaround is documented there) — cited only to show this is a real per-board-family difference, not directly applicable to this project's EE02 hardware
- `www.espboards.dev/esp32/xiao-esp32s3-plus/` [CITED] — 14-pin breakout table for the base XIAO pin numbering, used to cross-check ADC1-capable GPIOs
- `github.com/espressif/esp-idf` `adc_types.h` deprecation notes [CITED, via WebSearch aggregation] — `ADC_ATTEN_DB_11` → `ADC_ATTEN_DB_12` rename

### Tertiary (LOW confidence)
- General forum/community reports of XIAO ESP32-S3 battery-charging behaviour (no confirmed fuel-gauge IC found) — flagged in Assumptions Log A4, does not block the plan since D-02 already committed to a raw-mV (not fuel-gauge-percentage) approach regardless

---

## Metadata

**Confidence breakdown:**
- Standard stack (ESP-IDF `esp_adc` API shape): HIGH — official Espressif documentation, cross-checked against this project's already-pinned IDF version
- Battery-sense GPIO identification for this exact hardware combo: MEDIUM-HIGH (revised 2026-08-27, up from LOW-MEDIUM) — now sourced from Seeed's own official EE0x driver-board documentation (`A0`/`GPIO1` + `D5`/`GPIO6`), not an unofficial forum thread; held at MEDIUM-HIGH rather than HIGH only because the cookbook page's worked example specifically names "EE04" rather than confirming EE02 by name in that exact sentence, even though its applicability banner lists EE02 explicitly
- Cross-process state-plumbing architecture: HIGH — directly derived from reading this project's own deployed systemd units and existing state-file code, not from external research
- Pitfalls: HIGH (revised 2026-08-27) — the real pitfall (researching the bare module instead of the EE02 carrier board) is now well-understood and documented; the divider ratio (A3) is sourced from Seeed's own reference code, not community forums

**Research date:** 2026-08-27 (corrected same day after the developer rejected any soldering/external-component work — see Summary)
**Valid until:** 30 days for the ESP-IDF API guidance (stable, versioned); the EE02 battery-pin finding does not expire (it's a fact about Seeed's own product design) but the plan's own flash-and-read verification step should still confirm it empirically before being treated as certain, per the one residual gap noted in A1
