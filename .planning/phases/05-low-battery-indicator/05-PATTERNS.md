# Phase 5: Low-Battery Indicator (05-02) - Pattern Map

**Mapped:** 2026-08-27
**Files analyzed:** 9 (2 new firmware + 1 new firmware test + 3 modified + 3 modified w/ new test cases)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `firmware/main/battery_math.c` / `.h` | utility (pure math) | transform | `firmware/main/backoff.c` / `.h` | exact |
| `firmware/main/battery.c` / `.h` | service (hardware driver) | request-response (peripheral read) | `firmware/main/wifi.c` (ESP-IDF-dependent, not host-tested) | role-match |
| `firmware/tests/test_battery_math.c` | test | transform | `firmware/tests/test_backoff.c` | exact |
| `firmware/main/api_client.c` (modify `telemetry_headers()`) | controller (HTTP client) | request-response | itself (existing function, in-place edit) | exact |
| `firmware/main/CMakeLists.txt` | config | — | itself (existing file, in-place edit) | exact |
| `stub-server/byos_server.py` (add `save_battery_state()`, call in `do_GET`) | controller (HTTP handler) | event-driven / file-I/O | its own `save_state()` / `log_telemetry()` | exact |
| `server/poll_loop.py` (add `load_battery_state()`, `apply_battery_hysteresis()`) | service (oneshot orchestrator) | CRUD (state read-modify-write) | its own `load_poll_state()` / `save_poll_state()` | exact |
| `server/plane/render.py` (add `draw_battery_icon()`, `battery_low` param) | component (raster compositor) | transform | its own `draw_frame()` / `_build_active_canvas()` | exact |
| `stub-server/test_poll_cycle.py`, `server/test_poll_loop.py`, `server/test_render.py` | test | request-response / CRUD / transform | themselves (existing harnesses, new cases appended) | exact |

## Pattern Assignments

### `firmware/main/battery_math.c` / `battery_math.h` (utility, transform)

**Analog:** `firmware/main/backoff.c` / `firmware/main/backoff.h`

**Header pattern** (`firmware/main/backoff.h`, full file):
```c
/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Firmware-owned failure backoff (PROTOCOL.md §3). */
#pragma once
#include <stdint.h>

/* min(2^n * 5 min, 6 h), in seconds. n = consecutive failures. */
uint32_t fp_backoff_seconds(uint8_t n);
```
Copy this shape exactly for `battery_math.h`: `#pragma once`, only `<stdint.h>`, no ESP-IDF headers, one-line doc comment above the declaration, `fp_`-prefixed function name (`fp_` prefix matches `fp_battery_read_mv()` already used in RESEARCH.md's own example). Signature: `uint32_t battery_math_apply_divider(uint32_t divider_mv);` (RESEARCH.md's own proposed signature — reuse verbatim, it already follows this exact convention).

**Core pattern:** a single small pure integer function with no I/O, no globals, no ESP-IDF dependency — same as `backoff.c`'s `fp_backoff_seconds()` (2^n curve with a cap). `battery_math_apply_divider()` is the equivalent shape (multiply by the divider ratio, no branching needed for a fixed 1:2 ratio).

**Error handling:** none — pure math functions in this codebase never return an error code (see `backoff.c`); overflow is avoided by construction (documented in RESEARCH.md's "no overflow at max" test case for backoff — mirror that same discipline: assert/comment the max input range is safe for `uint32_t`).

---

### `firmware/tests/test_battery_math.c` (test, transform)

**Analog:** `firmware/tests/test_backoff.c`

**Full pattern** (copy structure directly):
```c
/* SPDX-FileCopyrightText: 2026 YODE PTE LTD
 * SPDX-License-Identifier: Apache-2.0 */
/* Host-side unit test for the one firmware behavior testable without
 * hardware: ... */
#include <assert.h>
#include <stdio.h>

#include "../main/battery_math.h"

int main(void)
{
    assert(battery_math_apply_divider(1500) == 3000);   /* nominal 1:2 */
    assert(battery_math_apply_divider(0) == 0);          /* zero edge */
    /* ... more boundary cases matching D-01/D-02's 3500mV threshold math ... */
    printf("battery_math: all cases pass\n");
    return 0;
}
```
Compile invocation matches `run_host_tests.sh`'s existing `run_suite` call convention exactly — no new script needed, just append one line:
```sh
run_suite "test_battery_math" "${SCRIPT_DIR}/test_battery_math.c" "${MAIN_DIR}/battery_math.c"
```
(`firmware/tests/run_host_tests.sh`, after the existing three `run_suite` calls, before the `if [ "${FAIL}" -eq 0 ]` block.)

---

### `firmware/main/battery.c` / `battery.h` (service, request-response)

**Analog:** `firmware/main/wifi.c` (ESP-IDF-dependent, never host-tested — same tier as this new file)

No direct excerpt read (out of scope for this pass — RESEARCH.md's own Pattern 1 code example already gives a concrete, ready-to-use `fp_battery_read_mv()` implementation using `adc_oneshot`/`adc_cali`, which should be used as-is rather than re-derived from `wifi.c`). The pattern to copy from `wifi.c` is structural only: ESP-IDF component headers at the top, one `fp_`-prefixed public entry point per `.h`, resource cleanup on every error path (`wifi.c`'s own defensive teardown on init failure is the same shape as RESEARCH.md's `adc_oneshot_del_unit(adc1)` cleanup calls).

**CMakeLists.txt integration** (`firmware/main/CMakeLists.txt`, full current file):
```
idf_component_register(
    SRCS "app_main.c" "backoff.c" "api_base.c" "epd13in3e.c" "panel.c" "panel_guard.c"
         "api_client.c" "wifi.c" "state_machine.c"
    INCLUDE_DIRS "."
    REQUIRES "nvs_flash" "esp_timer" "driver" "heap"
              "esp_wifi" "esp_netif" "esp_event" "esp_http_client" "esp-tls"
              "mbedtls" "json" "esp_app_format" "esp_hw_support"
)
```
Add `"battery.c" "battery_math.c"` to `SRCS` and `"esp_adc"` to `REQUIRES`.

---

### `firmware/main/api_client.c` — `telemetry_headers()` (controller, request-response)

**Analog:** itself, in-place edit (lines 123-136)

**Current pattern:**
```c
static void telemetry_headers(esp_http_client_handle_t http,
                              const char *boot_reason)
{
    char buf[16];
    int rssi = fp_wifi_rssi();
    snprintf(buf, sizeof(buf), "%d", rssi);
    esp_http_client_set_header(http, "X-Rssi", buf);

    esp_http_client_set_header(http, "X-Battery-Mv", "0");

    esp_http_client_set_header(http, "X-Fw-Version",
                               esp_app_get_description()->version);
    esp_http_client_set_header(http, "X-Boot-Reason", boot_reason);
}
```
**Change:** follow the exact `fp_wifi_rssi()` → `snprintf` → `esp_http_client_set_header` pattern already used for `X-Rssi` two lines above, substituting `fp_battery_read_mv()` (new) for the hardcoded `"0"` literal — same buffer-then-format-then-set idiom, no new pattern needed.

---

### `stub-server/byos_server.py` — new `save_battery_state()` + `do_GET` hook (controller, event-driven/file-I/O)

**Analog:** its own `save_state()` (lines 46-62) and `log_telemetry()` (lines 90-98)

**Imports** (top of file, already present — no new imports needed beyond stdlib already imported: `json`, `os`, plus `time` which is not yet imported — check before adding).

**Core atomic-write pattern** (lines 58-62, copy exactly):
```python
def save_state(state_dir, state):
    tmp = state_path(state_dir) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, state_path(state_dir))
```
New `save_battery_state(state_dir, mv)` follows this identically, writing to a new `battery_state.json` path (own `battery_state_path()` helper mirroring `state_path()` at line 46-47).

**Read/validate pattern** (lines 90-98, `log_telemetry`, for where to hook the new persistence call):
```python
def log_telemetry(self):
    parts = []
    for h in ("X-Fw-Version", "X-Boot-Reason", "X-Rssi",
              "X-Battery-Mv"):
        v = self.headers.get(h)
        if v:
            parts.append("%s=%s" % (h, v))
    if parts:
        print("  telemetry:", " ".join(parts))
```
Call `save_battery_state()` immediately after `self.log_telemetry()` inside `do_GET`'s `/device/v1/display` branch (line 135), reading `self.headers.get("X-Battery-Mv")` the same way `log_telemetry()` already does, with added `raw.isdigit()` + `raw != "0"` validation per RESEARCH.md's V5 input-validation note.

**Error handling:** `load_state()` (lines 50-55) is the model for the new `load_battery_state()` reader (used in `poll_loop.py`, not here) — `except (OSError, ValueError): return <safe default>`, never crash on missing/malformed file.

---

### `server/poll_loop.py` — `load_battery_state()` + `apply_battery_hysteresis()` (service, CRUD)

**Analog:** its own `load_poll_state()` / `save_poll_state()` (lines 82-115)

**Read pattern** (lines 86-95, copy shape exactly for new read-only `load_battery_state()`):
```python
def load_poll_state(state_dir):
    """Missing, unreadable, or malformed -> empty state (D-P2-02), never a
    crash.
    """
    try:
        with open(_poll_state_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
```
New `load_battery_state(state_dir)` reads `battery_state.json` (written only by `byos_server.py` — never call `save_` on this file from `poll_loop.py`, per RESEARCH.md's Pitfall 4 anti-pattern) and returns `None` on any failure (RESEARCH.md's own example already gives this exact function).

**Hysteresis function** — RESEARCH.md provides this ready-made; copy verbatim into `poll_loop.py`, near the top alongside the other module-level constants:
```python
BATTERY_LOW_THRESHOLD_MV = 3500  # 05-CONTEXT.md D-01
BATTERY_LOW_CLEAR_MV = 3600      # 05-UI-SPEC.md hysteresis resolution

def apply_battery_hysteresis(battery_mv, was_active):
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < BATTERY_LOW_CLEAR_MV
    return battery_mv <= BATTERY_LOW_THRESHOLD_MV
```

**Write pattern** (lines 98-115, `save_poll_state`, for persisting the new `battery_low_active` boolean):
```python
def save_poll_state(state_dir, state):
    """Atomic tmp-write-then-os.replace(), matching
    stub-server/byos_server.py's save_state() (T-02-01-03 / V12). ...
    """
    path = _poll_state_path(state_dir)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
```
`run_once()` (starts line 146) is where `load_battery_state()` + `apply_battery_hysteresis()` get called each cycle, storing the result into the same `state` dict already passed to `save_poll_state()`, and threading `battery_low=<bool>` into the existing `render.render_panel(...)` call (currently at lines 213/253/284 — three call sites, all need the new kwarg).

---

### `server/plane/render.py` — `draw_battery_icon()` + `battery_low` param (component, transform)

**Analog:** `draw_frame()` (lines 230-238) and `_build_active_canvas()` (lines 638-688)

**Constants location** (near line 90/127/131/147 — copy this block's style for the new `BATTERY_ICON_*` constants):
```python
MARGIN = SPACE_LG
...
STATE_BACKGROUND = { ... }
STATE_INK = { ... }
...
FRAME_STROKE_PX = 2
```
Add `BATTERY_ICON_LEFT = MARGIN`, `BATTERY_ICON_BOTTOM = HEIGHT - MARGIN`, `BATTERY_ICON_BODY_W = 64`, `BATTERY_ICON_BODY_H = 32`, `BATTERY_ICON_NUB_W = 8`, `BATTERY_ICON_NUB_H = 14`, `BATTERY_ICON_STROKE_PX = 3`, `BATTERY_ICON_FILL_FRAC = 0.22` alongside the existing constant block (05-UI-SPEC.md's Canvas and Geometry table has the exact values).

**Drawing-function pattern** (`draw_frame()`, lines 230-238, copy shape exactly):
```python
def draw_frame(canvas, ink_idx):
    """D-26: a thin `ink_idx`-coloured rectangle outline, `FRAME_STROKE_PX`
    wide, inset `FRAME_INSET_FRAC` of the canvas width from every edge.
    Returns the frame's own bounding box.
    """
    inset = round(WIDTH * FRAME_INSET_FRAC)
    box = (inset, inset, WIDTH - inset, HEIGHT - inset)
    ImageDraw.Draw(canvas).rectangle(box, outline=ink_idx, width=FRAME_STROKE_PX)
    return box
```
New `draw_battery_icon(canvas, draw, ink_idx)` follows the same "compute deterministic box(es) from module constants, call `ImageDraw.rectangle`, return/assert bbox" shape — RESEARCH.md's own Code Examples section already provides the full body:
```python
def draw_battery_icon(canvas, draw, ink_idx):
    body = (64, 1504, 128, 1536)
    nub = (128, 1513, 136, 1527)
    fill = (67, 1507, 80, 1533)
    _assert_within_canvas(body, "battery icon body")
    draw.rectangle(body, outline=ink_idx, width=3)
    draw.rectangle(nub, fill=ink_idx)
    draw.rectangle(fill, fill=ink_idx)
```

**Guard-rail pattern** (`_assert_within_canvas`, lines 195-206, copy exactly — do NOT use `_assert_in_safe_box`, per 05-UI-SPEC.md's explicit instruction):
```python
def _assert_within_canvas(bbox, label):
    left, top, right, bottom = bbox
    assert left >= 0 and top >= 0 and right <= WIDTH and bottom <= HEIGHT, (
        "%s bounding box %r falls outside the %dx%d canvas" % (label, bbox, WIDTH, HEIGHT)
    )
```

**Integration point** (`_build_active_canvas()`, lines 638-688 — add the conditional call near the end, before the `_assert_legal_palette` guard at line 686):
```python
def _build_active_canvas(flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None, battery_low=False):
    ...
    bg_idx = STATE_BACKGROUND[state]
    fg_idx = STATE_INK[state]
    ...
    if battery_low:
        draw_battery_icon(canvas, ImageDraw.Draw(canvas), fg_idx)
    _assert_legal_palette(canvas, bg_idx)
    return canvas
```
`_build_empty_canvas()` (lines 573-602) needs the same new `battery_low=False` param and conditional call, using `IDX_BLACK` (its existing ink color) instead of `STATE_INK[state]`, per 05-UI-SPEC.md's Color section resolution. `build_canvas()` (line 691) and `render_panel()` (line 725) both need `battery_low=False` threaded through as a pass-through kwarg to whichever of the two builders they call (lines 713-722).

**Error handling:** none new — Pillow drawing calls in this file never try/except; malformed geometry is caught by the `_assert_within_canvas`/`_assert_legal_palette` guard-rail asserts, consistent with every other drawing helper in this file.

---

### Test files (existing harnesses, append new cases only — no new test files)

**`stub-server/test_poll_cycle.py`** — analog is its own existing fixture at line 386 (`"X-Battery-Mv": "3941"`, already cited in RESEARCH.md) — build new cases from that fixture's existing header-dict shape.

**`server/test_poll_loop.py`** — analog is its own existing tests around `load_poll_state`/`save_poll_state` — add `-k hysteresis` cases exercising `apply_battery_hysteresis()`'s three branches (arm, hold-armed, clear) plus the `None`-reading case per RESEARCH.md's Pitfall 5.

**`server/test_render.py`** — analog is its own existing `_assert_within_canvas`-backed assertions on other conditional elements (e.g. the previous-flight card) — add `-k battery` cases checking: icon renders only when `battery_low=True`, exact geometry match, correct per-state ink color, and pixel-identical output when `battery_low=False`.

---

## Shared Patterns

### Atomic single-writer state files
**Source:** `stub-server/byos_server.py`'s `save_state()` (lines 58-62) and `server/poll_loop.py`'s `save_poll_state()` (lines 98-115)
**Apply to:** `byos_server.py`'s new `save_battery_state()`, `poll_loop.py`'s new `load_battery_state()` (read-only)
```python
tmp = path + ".tmp"
with open(tmp, "w") as fh:
    json.dump(state, fh, indent=1)
os.replace(tmp, path)
```
Critical constraint (RESEARCH.md Pitfall 4): `battery_state.json` has exactly one writer (`byos_server.py`); `poll_loop.py` only ever reads it, merging the value into its own separately-owned `poll_state.json`.

### Degrade-to-empty-state on read failure
**Source:** `server/poll_loop.py`'s `load_poll_state()` (lines 86-95), `stub-server/byos_server.py`'s `load_state()` (lines 50-55)
**Apply to:** the new `load_battery_state()`
```python
try:
    with open(path) as fh:
        data = json.load(fh)
except (OSError, ValueError):
    return {}  # or None for battery_state specifically — "never reported" is valid
```

### Pure-logic / hardware-dependent module split (firmware)
**Source:** `firmware/main/backoff.c` (pure, host-tested) vs `firmware/main/wifi.c` (ESP-IDF-dependent, never host-tested)
**Apply to:** `battery_math.c` (pure) vs `battery.c` (ESP-IDF `esp_adc` calls)

### `_assert_within_canvas` guard rail on every new draw call
**Source:** `server/plane/render.py` lines 195-206
**Apply to:** `draw_battery_icon()` — not `_assert_in_safe_box()`, per 05-UI-SPEC.md's explicit instruction that this element deliberately sits outside the old SAFE_BOX band like the frame and illustrations already do.

## No Analog Found

None — every file in this phase's Wave 0 gap list has a strong, same-codebase analog (see table above).

## Metadata

**Analog search scope:** `firmware/main/`, `firmware/tests/`, `stub-server/byos_server.py`, `server/poll_loop.py`, `server/plane/render.py`
**Files scanned:** `firmware/main/backoff.c`, `backoff.h`, `wifi.c`, `api_client.c`, `CMakeLists.txt`, `firmware/tests/test_backoff.c`, `run_host_tests.sh`, `stub-server/byos_server.py`, `server/poll_loop.py`, `server/plane/render.py`
**Pattern extraction date:** 2026-08-27
