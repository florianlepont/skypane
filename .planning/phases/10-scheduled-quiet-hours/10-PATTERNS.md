# Phase 10: Scheduled Quiet Hours - Pattern Map

**Mapped:** 2026-09-03
**Files analyzed:** 9 (0 new files — all modifications to existing modules, per RESEARCH.md's "Recommended Project Structure")
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `server/device_config.py` (+3 registry fields + window-arithmetic helper) | config/model | CRUD | same file's existing `led_enabled` field (lines 53, 333-345, 348-421) | exact (in-file precedent) |
| `stub-server/byos_server.py` (+`read_quiet_hours()` + `quiet_hours_sleep_s()`) | service (vendored, stdlib-only) | request-response | same file's `read_led_enabled()` (lines 85-107) + the `/display` handler's `sleep_s` field (line 254) | exact (in-file precedent) |
| `server/plane/render.py` (+`_build_quiet_hours_canvas()` + `build_canvas()` dispatch branch) | component/transform | transform (data → raster canvas) | same file's `_build_empty_canvas()` (lines 1740-1798) + `build_canvas()` dispatch (lines 1987+) | exact (in-file precedent) |
| `server/poll_loop.py` (+quiet-hours gate near top of `run_once()` + `poll_state["quiet_hours_active"]`) | controller/orchestrator | event-driven (poll cycle) | same file's existing battery-hysteresis gate pattern (lines 711-718, `battery_low_active`/`battery_changed`) | exact (in-file precedent) |
| `companion/pages/config_page.py` (+`quiet_hours_group()`) | component (server-rendered HTML fragment) | request-response | same file's `led_group()` (lines 348-400) | exact (in-file precedent) |
| `companion/pages/config_page.py` (`handle_post()` extension) | controller (form handler) | CRUD | same file's `handle_post()` (lines 674-750), specifically the `submitted_led`/`led_enabled` absent-means-False branch (lines 731, 737-742) | exact (in-file precedent) |
| `companion/static/style.css` (+`color-scheme` blocks, `.settings-checkbox`/`.led-checkbox` reuse) | config (CSS) | n/a | existing `html[data-ui-theme="light"/"dark"]` blocks (~lines 175-191) and `.led-checkbox` rule | exact (in-file precedent) |
| `server/test_config_history.py` / `server/test_poll_loop.py` / `server/test_render.py` / `stub-server/test_poll_cycle.py` / `companion/test_config_page.py` | test | CRUD/transform verification | each file's own existing `led_enabled`/empty-canvas/`sleep_s` checks + `EXPECTED_CHECK_COUNT` guard | exact (in-file precedent) |
| `stub-server/VENDOR.md` | config/doc | n/a | existing "Local modifications" 3-entry log | exact (in-file precedent) |

Every touched file already contains the exact structural precedent this phase needs — no cross-file analog search was needed; the closest analog for each piece of new code is a sibling block within the *same* file. This matches RESEARCH.md's own "No new files" structure section.

## Pattern Assignments

### `server/device_config.py` — registry fields + DST-safe window helper

**Analog:** `DEFAULT_LED_ENABLED` / `normalise_led_enabled()` / `load_device_config()` / `save_device_config()` (same file, lines 53, 333-421)

**Constant + normaliser pattern** (lines 333-345):
```python
DEFAULT_LED_ENABLED = True  # D-02: matches the LED's current hardcoded always-on behaviour

def normalise_led_enabled(value):
    """Return `value` unchanged only when `isinstance(value, bool)` is true -
    otherwise return `DEFAULT_LED_ENABLED`. Never raises. Deliberately no
    registry/membership test... an int such as `0` or `1` is NOT a bool
    under `isinstance` in Python and therefore degrades to the default -
    this is intentional, not an oversight.
    """
    if isinstance(value, bool):
        return value
    return DEFAULT_LED_ENABLED
```
Copy this exact shape for `normalise_quiet_hours_enabled()`. For the two "HH:MM" string fields, add a compiled `_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")` and a shared `normalise_quiet_hours_time(value, default)` (RESEARCH.md Pattern 1) — same "never raises, degrade to default" contract, membership test replaced by a regex match since there is no fixed registry of valid times.

**Load pattern** (lines 348-369):
```python
def load_device_config(state_dir):
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return {
        "theme": normalise_theme_id(data.get("theme")),
        "tracked_runway": normalise_runway_id(data.get("tracked_runway")),
        "led_enabled": normalise_led_enabled(data.get("led_enabled")),
    }
```
Add three more dict keys (`quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`) via the new normalisers, in the same return dict — no change to the try/except shape.

**Save/validate pattern** (lines 372-421, esp. 394-399, 401-406):
```python
def save_device_config(state_dir, theme=None, tracked_runway=None, led_enabled=None):
    if theme is not None and theme not in THEMES:
        raise ValueError("unknown theme id %r (expected one of %r)" % (theme, THEME_IDS))
    ...
    if led_enabled is not None and not isinstance(led_enabled, bool):
        raise ValueError("led_enabled must be a bool, got %r" % (led_enabled,))

    current = load_device_config(state_dir)
    new_config = {
        "theme": theme if theme is not None else current["theme"],
        ...
        "led_enabled": led_enabled if led_enabled is not None else current["led_enabled"],
    }
    os.makedirs(state_dir, exist_ok=True)
    path = device_config_path(state_dir)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(new_config, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
```
Add `quiet_hours_enabled=None, quiet_hours_start=None, quiet_hours_end=None` params, each with its own explicit pre-write validation (`isinstance(..., bool)` for enabled, `_HHMM_RE.match(...)` for the two time strings), following the exact "validate before touching the file, carry-forward when None" contract. The tmp-write-then-`os.replace()` block itself is untouched — no new atomicity code needed.

**New DST-safe window-arithmetic helper** (net-new code, not adapted from an existing analog — RESEARCH.md Pattern 2 is the reference implementation):
```python
from datetime import timedelta
from zoneinfo import ZoneInfo

QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")

def seconds_until_quiet_hours_end(now_utc, start_hm, end_hm):
    """Return None if `now_utc` is outside the [start_hm, end_hm) window
    (Europe/Paris wall-clock, wraps midnight when end <= start), else the
    whole seconds remaining until the window's local end time."""
    local_now = now_utc.astimezone(QUIET_HOURS_TZ)
    start_h, start_m = (int(x) for x in start_hm.split(":"))
    end_h, end_m = (int(x) for x in end_hm.split(":"))
    start_today = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_today = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if (start_h, start_m) <= (end_h, end_m):
        if not (start_today <= local_now < end_today):
            return None
        end_dt = end_today
    else:
        if local_now >= start_today:
            end_dt = end_today + timedelta(days=1)
        elif local_now < end_today:
            end_dt = end_today
        else:
            return None
    return max(0, int((end_dt - local_now).total_seconds()))
```
This lives in `server/device_config.py` (imported by `poll_loop.py`); a byte-for-byte duplicate must also exist inside `stub-server/byos_server.py` since that file cannot import project modules (see next section) — RESEARCH.md Pitfall 1 flags this drift risk explicitly; keep a cross-reference comment in both copies.

---

### `stub-server/byos_server.py` — `read_quiet_hours()` + `quiet_hours_sleep_s()`

**Analog:** `read_led_enabled()` (same file, lines 85-107) and the `/display` handler's `"sleep_s": self.args.sleep` line (line 254)

**Imports pattern** (top of file — confirm current imports before adding; `zoneinfo` is stdlib so it does not violate the file's "stdlib only" docstring contract):
```python
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # stdlib since 3.9 — does NOT violate "stdlib only"
```

**Fail-open read pattern** (lines 85-107, the direct template):
```python
def read_led_enabled(state_dir):
    """Best-effort read of the shared device_config.json's led_enabled
    field. Never raises.
    ...every failure mode here (missing file, unreadable file, malformed
    JSON, a non-dict document, or a present-but-non-bool led_enabled
    value) degrades to enabled...
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return True
    if not isinstance(data, dict):
        return True
    value = data.get("led_enabled")
    if isinstance(value, bool):
        return value
    return True
```
`read_quiet_hours(state_dir)` follows this exact shape but degrades to `None` ("not in effect") on every failure mode instead of a fixed boolean — see RESEARCH.md Pattern 4 for the full reference body (validates `quiet_hours_enabled is True` plus both HH:MM strings against a local `_HHMM_RE` before returning `(start, end)`).

**Core `sleep_s` computation — the field currently being replaced** (line 254):
```python
"sleep_s": self.args.sleep,
```
Becomes:
```python
"sleep_s": quiet_hours_sleep_s(self.args.sleep, self.args.state_dir),
```
where `quiet_hours_sleep_s()` reads the window via `read_quiet_hours()`, computes remaining seconds via the duplicated `seconds_until_quiet_hours_end()` (Pattern 2 above), and returns `max(base_sleep_s, remaining)` — never shorter than the configured base, per Claude's Discretion in `10-CONTEXT.md`.

**Error handling / fail-open discipline:** identical to `read_led_enabled()` — every branch that could raise (`OSError`, `ValueError` from `json.load`, malformed dict) returns the safe default (`None` → unmodified `sleep_s`) rather than propagating, keeping the single always-on `/device/v1/display` service from ever going down due to a corrupted config file (RESEARCH.md's V5/DoS threat table).

**Vendor discipline (critical constraint — anti-pattern to avoid):** this file must never `import server.device_config` or any `server.*` module. All quiet-hours logic needed here (regex, window arithmetic, JSON read) must be self-contained duplicates, documented in `stub-server/VENDOR.md`'s "Local modifications" log with a cross-reference to `server/device_config.py`'s copy (same style already used for `read_led_enabled()`/`parse_battery_mv()`).

---

### `server/plane/render.py` — `_build_quiet_hours_canvas()` + dispatch branch

**Analog:** `_build_empty_canvas()` (same file, lines 1740-1798) and `build_canvas()`'s dispatch (lines 1987+)

**Core canvas-building pattern to copy** (lines 1754-1798, condensed to the load-bearing shape):
```python
canvas = pf.new_canvas(IDX_WHITE)
draw = ImageDraw.Draw(canvas)
body_font = _font(EMPTY_BODY_FONT)
center_x = WIDTH // 2
safe_width = SAFE_BOX[2] - SAFE_BOX[0]

heading_font = fit_text_size(PT_SERIF_BOLD, EMPTY_HEADING_FONT[1], heading_text, safe_width, EMPTY_HEADING_MIN_SIZE)
heading_ascent, heading_descent = heading_font.getmetrics()
heading_height = heading_ascent + heading_descent

body_lines = _wrap_text(body_font, BODY_TEXT, safe_width)
body_ascent, body_descent = body_font.getmetrics()
body_line_height = body_ascent + body_descent

total_height = heading_height + SPACE_SM + len(body_lines) * body_line_height
start_y = (HEIGHT - total_height) // 2

heading_bbox = draw.textbbox((center_x, start_y), heading_text, font=heading_font, anchor="ma")
_assert_in_safe_box(heading_bbox, "quiet-hours heading")
draw.text((center_x, start_y), heading_text, font=heading_font, fill=EMPTY_INK, anchor="ma")

y = start_y + heading_height + SPACE_SM
for line in body_lines:
    line_bbox = draw.textbbox((center_x, y), line, font=body_font, anchor="ma")
    _assert_in_safe_box(line_bbox, "quiet-hours body line")
    draw.text((center_x, y), line, font=body_font, fill=EMPTY_INK, anchor="ma")
    y += body_line_height

if source_fault:
    draw_source_fault_badge(canvas, EMPTY_INK, weight="bold")
if battery_low:
    draw_battery_icon(canvas, draw, EMPTY_INK)

return canvas
```
`_build_quiet_hours_canvas(quiet_hours_until, source_fault=False, battery_low=False)` should be a near-verbatim copy of `_build_empty_canvas()` with `heading_text = "QUIET HOURS"` (fixed, not runway-dependent) and `body_lines` built from `"Back at %s" % quiet_hours_until` — per UI-SPEC.md's locked default (mirror the empty state exactly; do not invent new drawing primitives).

**Dispatch pattern** (`build_canvas()`, RESEARCH.md Pattern 3 citing line ~2034):
```python
def build_canvas(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False,
):
```
Add a `quiet_hours_until=None` param and, as the *first* branch inside the function body (before the existing `if flight is None or state == "empty":` check):
```python
if state == "quiet_hours":
    return _build_quiet_hours_canvas(
        quiet_hours_until=quiet_hours_until, battery_low=battery_low, source_fault=source_fault)
```
`theme_id`/`runway_id` are ignored for this state, exactly as the empty state ignores `theme_id`.

**Testing pattern:** `server/test_render.py` already has a 119-check harness with `EXPECTED_CHECK_COUNT`; add checks mirroring however empty-canvas legality/safe-box/palette assertions are currently structured there, and bump the count by exactly the number of new `check(...)` calls.

---

### `server/poll_loop.py` — quiet-hours gate in `run_once()`

**Analog:** the existing battery-hysteresis "compute once before any branching" pattern (same file, lines 711-718) and the general `poll_state[...]` read/write idiom used throughout `run_once()` (lines 688-696, 877-884)

**Pattern to copy — compute-before-branch, single flag in `poll_state`** (lines 711-718):
```python
was_battery_low = bool(poll_state.get("battery_low_active", False))
battery_low = apply_battery_hysteresis(load_battery_state(state_dir), was_battery_low)
battery_changed = battery_low != was_battery_low
poll_state["battery_low_active"] = battery_low
```
The quiet-hours gate should follow this exact shape: read `poll_state.get("quiet_hours_active", False)`, compute the current in-window status via `device_config.seconds_until_quiet_hours_end(...)` against the freshly-loaded `device_cfg` (already read once per cycle at lines 661-663 — reuse that same single read, do not re-read config mid-cycle), and set `poll_state["quiet_hours_active"]`.

**Config read-once-per-cycle pattern** (lines 655-663 — directly reusable, no new read call needed):
```python
device_cfg = device_config.load_device_config(state_dir)
theme_id = device_cfg["theme"]
tracked_runway_id = device_cfg["tracked_runway"]
```
Add `quiet_hours_enabled = device_cfg["quiet_hours_enabled"]` etc. to this same block.

**Insertion point (per RESEARCH.md Pitfall 4):** the quiet-hours check must be an early return near the very top of `run_once()`, **before** `detect.load_geofence()`/`detect.poll_current_aircraft()` (i.e., before line 665), not woven into the later flight-detection branching — skip ADS-B polling entirely for the whole cycle when inside the window, and render the quiet-hours canvas via `render.build_canvas(None, "quiet_hours", quiet_hours_until=..., battery_low=battery_low)` (battery_low/source_fault still computed independently, matching `_build_empty_canvas()`'s own precedent). On the *first* cycle detecting entry, render once; on subsequent cycles still inside the window, hold (no re-render) — same "render once, then hold" discipline the existing `battery_changed`-gated re-render logic already uses elsewhere in this file.

**Testing pattern:** `server/test_poll_loop.py` has a 44-check harness; extend with quiet-hours-active/held/exit transition checks, injecting a fixed `now` (mirroring the file's own `now_s()` seam) per RESEARCH.md's Wave 0 Gaps note.

---

### `companion/pages/config_page.py` — `quiet_hours_group()` fieldset

**Analog:** `led_group()` (same file, lines 348-400)

**Exact structural pattern to copy** (lines 386-400):
```python
def led_group(current_led_enabled):
    checked = " checked" if current_led_enabled else ""
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<label class="led-checkbox">'
        '<input type="checkbox" name="led_enabled" value="%s"%s> Enable diagnostic LED'
        "</label>"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(LED_SECTION_HEADING),
        escape_html(LED_SECTION_HEADING),
        escape_html(LED_SECTION_CAPTION),
        escape_html(LED_CHECKBOX_VALUE), checked,
    )
```
`quiet_hours_group(current_enabled, current_start, current_end)` follows this exact shape (per UI-SPEC.md's locked field order/copy), adding two `<label><input type="time" ...></label>` lines after the checkbox `<label>`, each value routed through `escape_html()` — matching the file's universal escaping discipline for every interpolated current-value.

**`LED_CHECKBOX_VALUE` constant pattern** (line 47):
```python
LED_CHECKBOX_VALUE = "on"
```
Reuse verbatim as `QUIET_HOURS_CHECKBOX_VALUE = "on"` (UI-SPEC.md confirms same literal).

**`handle_post()` extension — analog for the absent-checkbox / validate-before-use pattern** (lines 728-750, esp. 731, 737-742):
```python
state_dir = ctx["state_dir"]
submitted_theme = form.get("theme")
submitted_runway = form.get("tracked_runway")
submitted_led = form.get("led_enabled")

if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
    return FLASH_SAVE_FAILED
if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
    return FLASH_SAVE_FAILED
if submitted_led is None:
    led_enabled = False
elif submitted_led == LED_CHECKBOX_VALUE:
    led_enabled = True
else:
    return FLASH_SAVE_FAILED

try:
    device_config.save_device_config(
        state_dir, theme=submitted_theme, tracked_runway=submitted_runway,
        led_enabled=led_enabled)
except (ValueError, OSError):
    return FLASH_SAVE_FAILED
return FLASH_SAVED
```
Add `submitted_qh_enabled = form.get("quiet_hours_enabled")` resolved the same absent→False way as `led_enabled`, plus `submitted_qh_start`/`submitted_qh_end` validated via `device_config._HHMM_RE.match(...)` (or a public `normalise_quiet_hours_time`-adjacent check) before being passed to `save_device_config(...)`. **Per UI-SPEC.md's locked "Unchecked-checkbox semantics"**, unlike `led_enabled`'s single-field case, the two time fields must persist independently of the checkbox's checked state — pass them through even when `qh_enabled` resolves to `False`, resolving RESEARCH.md's Open Question 2 / Assumption A1 explicitly in the checked direction ("yes, times save independently").

**Error handling:** identical `except (ValueError, OSError): return FLASH_SAVE_FAILED` — no new error branch/copy per UI-SPEC.md's Copywriting Contract (reuses `FLASH_SAVE_FAILED` verbatim, no quiet-hours-specific error message).

**Testing pattern:** `companion/test_config_page.py` has a 64-check harness; extend with fieldset-render + handle_post validation/persistence checks for the three new fields.

---

### `companion/static/style.css` — `color-scheme` blocks

**Analog:** existing `html[data-ui-theme="light"]` / `html[data-ui-theme="dark"]` blocks (~lines 175-191)

**Pattern (net-new declaration inside existing selectors, per UI-SPEC.md):**
```css
html[data-ui-theme="light"] { color-scheme: light; }
html[data-ui-theme="dark"] { color-scheme: dark; }
:root { color-scheme: light dark; }
```
Add alongside the existing theme-attribute blocks, not as new selectors. Optionally generalize `.led-checkbox` → `.settings-checkbox` (UI-SPEC.md's recommended, not mandatory, refactor) and reuse it for the new checkbox; acceptable fallback is duplicating the 4-declaration rule under a new class name if the rename is judged too invasive.

---

## Shared Patterns

### Fail-open / never-raise config reads
**Source:** `server/device_config.py`'s `load_device_config()` (lines 348-369) and `stub-server/byos_server.py`'s `read_led_enabled()` (lines 85-107)
**Apply to:** `device_config.py`'s new `load_device_config()` additions, `byos_server.py`'s new `read_quiet_hours()`
```python
try:
    with open(device_config_path(state_dir)) as fh:
        data = json.load(fh)
except (OSError, ValueError):
    data = {}   # or `return True` / `return None` depending on the caller's safe default
if not isinstance(data, dict):
    data = {}
```
Every new read of `device_config.json` in this phase must follow this exact "never raise, degrade to a documented default" contract — a hostile or corrupted config file must never take down either the companion service or `byos_server.py`'s single always-on `/display` handler.

### Write-path-is-strict / read-path-is-forgiving asymmetry
**Source:** `server/device_config.py`'s `save_device_config()` (lines 394-399) vs. its `normalise_*()` read helpers; `companion/pages/config_page.py`'s `handle_post()` docstring (lines 683-693)
**Apply to:** all three new quiet-hours fields
A submitted (write-path) value that fails validation raises `ValueError` (server) / returns `FLASH_SAVE_FAILED` (companion) — it is never silently coerced. A stored (read-path) value that fails validation silently degrades to the documented default. Do not blur this line for the new HH:MM/boolean fields.

### Absent-HTML-checkbox-means-False
**Source:** `companion/pages/config_page.py`'s `handle_post()` (lines 704-711, 737-742)
**Apply to:** `quiet_hours_enabled` form handling
An unchecked checkbox is omitted from the POST body entirely; absence must resolve to `False`, never "leave unchanged" (unlike `theme`/`tracked_runway`, where absence means "this page didn't render that control").

### Compute-once-per-cycle, gate near the top
**Source:** `server/poll_loop.py`'s battery-hysteresis block (lines 711-718) and its single `device_cfg = device_config.load_device_config(state_dir)` read (lines 655-663)
**Apply to:** the new quiet-hours gate in `run_once()`
Read config and compute derived state (in-window? seconds remaining?) exactly once per cycle, before any flight-detection branching, and store the result in `poll_state` for the next cycle to compare against (render-once-then-hold).

### "Render once, then hold" — no unnecessary re-render
**Source:** `server/poll_loop.py`'s existing hold-cycle discipline (implied throughout `run_once()`'s branching, e.g. the `battery_changed`-gated re-render) and `render.py`'s general "no unnecessary refresh" ethos
**Apply to:** the D-05 quiet-hours screen — draw once on window entry, hold (no-op) for every subsequent in-window cycle, resume normal detection silently on exit (D-07, no transition screen).

### DST-safe local time via `zoneinfo`, never a hand-rolled UTC offset
**Source:** RESEARCH.md Pattern 2 (net-new; no existing codebase analog — `server/history_db.py`'s `datetime.now(timezone.utc)` is the only pre-existing timestamp convention, and it is UTC-only)
**Apply to:** both `server/device_config.py`'s and `stub-server/byos_server.py`'s window-arithmetic helpers
Always construct/compare via `ZoneInfo("Europe/Paris")`-aware datetimes; never a fixed `+1`/`+2` offset.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| DST-safe window-arithmetic helper (`seconds_until_quiet_hours_end()`, in both `server/device_config.py` and `stub-server/byos_server.py`) | utility | transform | Genuinely new domain logic — no existing timezone-aware or window/schedule arithmetic anywhere in the codebase (`server/history_db.py` is UTC-only). Use RESEARCH.md's Pattern 2 reference implementation verbatim (already verified against the project's pinned interpreter) rather than searching for a codebase precedent that does not exist. |

## Metadata

**Analog search scope:** `server/device_config.py`, `server/poll_loop.py`, `server/plane/render.py`, `stub-server/byos_server.py`, `companion/pages/config_page.py`, `companion/static/style.css`, plus each file's paired `test_*.py` harness — all read live during this mapping session (line numbers re-verified against current file state, not trusted blindly from RESEARCH.md's citations; a few line numbers had drifted slightly, e.g. `_build_empty_canvas()` starts at line 1740 as cited, `build_canvas()` at 1987 not exactly 2034, `read_led_enabled()` at 85 as cited).
**Files scanned:** 9 source files + 5 test harnesses
**Pattern extraction date:** 2026-09-03
