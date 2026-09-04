# Phase 11: Web-configurable wake interval - Pattern Map

**Mapped:** 2026-09-04
**Files analyzed:** 4 (no new files — all changes land in existing files, per 11-RESEARCH.md's "Recommended Project Structure")
**Analogs found:** 4 / 4 (all internal, same-file or same-repo siblings — no cross-codebase search needed since this is a pure pattern-extension phase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `server/device_config.py` (add `normalise_wake_interval_s()`, registry constants, `save_device_config()` param) | model / config registry | CRUD (validate + persist a field) | Same file: `normalise_led_enabled()` (bool shape) + `normalise_quiet_hours_time()` (bounded-value shape) | exact (same file, same function family) |
| `stub-server/byos_server.py` (add `read_wake_interval_s()`, change `/display` handler's `sleep_s` line) | service / request-response poll handler | request-response (best-effort read feeding an HTTP response) | Same file: `read_led_enabled()` (lines 105-127) | exact |
| `companion/pages/config_page.py` (add `wake_interval_group()`, wire into `render()`/`handle_post()`) | component (server-rendered HTML) + controller (POST handler) | CRUD (render form + validate/save submission) | Same file: `led_group()` (lines 365-420) for markup; `handle_post()`'s existing dict-building block for the int-conversion gate | exact (markup) / role-match (conversion gate is genuinely new — no prior int-typed field exists) |
| `companion/app.py` (env-var pre-fill wiring, if D-07's env-read path is implemented) | controller / config loader | request-response | `companion/auth.py`'s `configured_password()` (`PASSWORD_ENV_VAR` + `os.environ.get()`) | exact |
| `server/test_config_history.py` (extend 11 dict-equality assertions + new checks) | test | CRUD (regression) | Existing checks in same file | exact |
| `companion/test_config_page.py` (extend `theme-status` count assertion 3→4 + new checks) | test | CRUD (regression) | Existing checks in same file | exact |
| `stub-server/test_poll_cycle.py` (extend `EXPECTED_CHECK_COUNT`, add `read_wake_interval_s()`/handler checks) | test | request-response (regression) | Existing checks in same file | exact |

## Pattern Assignments

### `server/device_config.py` (model, CRUD)

**Analog:** same file's `normalise_led_enabled()` (lines 354-361) and `normalise_quiet_hours_time()` (lines 380-388), plus `save_device_config()`'s validation block (lines 421-484)

**Registry constants pattern** (lines 57-59, `DEFAULT_QUIET_HOURS_*` shape):
```python
DEFAULT_QUIET_HOURS_ENABLED = False  # D-04: an explicit boolean independent of the stored times...
DEFAULT_QUIET_HOURS_START = "23:00"
DEFAULT_QUIET_HOURS_END = "07:00"
```
New field copies this shape but with a **deliberate exception**: no `DEFAULT_WAKE_INTERVAL_S` constant. Instead:
```python
WAKE_INTERVAL_MIN_S = 60   # D-02
WAKE_INTERVAL_MAX_S = 3600  # D-02
```

**Normalise-function pattern** (`normalise_led_enabled()`, lines 354-361):
```python
def normalise_led_enabled(value):
    """Return `value` unchanged only when `isinstance(value, bool)` is true -
    otherwise return `DEFAULT_LED_ENABLED`. Never raises.
    """
```
adapted for `normalise_wake_interval_s(value)`: same "never raises, degrade on any invalid shape" contract, but degrades to `None` (not a default constant) per D-07/Pattern 1 in RESEARCH.md, and must explicitly exclude `bool` (`isinstance(value, int) and not isinstance(value, bool)`) since `isinstance(True, int)` is `True` in Python — this exact gotcha is called out in RESEARCH.md's Anti-Patterns section.

**Validation pattern in `save_device_config()`** (lines 421-484, verified live):
```python
def save_device_config(
    state_dir, theme=None, tracked_runway=None, led_enabled=None,
    quiet_hours_enabled=None, quiet_hours_start=None, quiet_hours_end=None,
):
    ...
    if led_enabled is not None and not isinstance(led_enabled, bool):
        raise ValueError("led_enabled must be a bool, got %r" % (led_enabled,))
    ...
    current = load_device_config(state_dir)
    new_config = {
        "theme": theme if theme is not None else current["theme"],
        ...
        "quiet_hours_end": quiet_hours_end if quiet_hours_end is not None else current["quiet_hours_end"],
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
New param `wake_interval_s=None` added to the signature; validation clause:
```python
if wake_interval_s is not None and not (
        isinstance(wake_interval_s, int) and not isinstance(wake_interval_s, bool)
        and WAKE_INTERVAL_MIN_S <= wake_interval_s <= WAKE_INTERVAL_MAX_S):
    raise ValueError(
        "wake_interval_s must be an int in [%d, %d], got %r"
        % (WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S, wake_interval_s))
```
and one new key in `new_config`: `"wake_interval_s": wake_interval_s if wake_interval_s is not None else current["wake_interval_s"]` — same carry-forward idiom, no change to the tmp-write/`os.replace()`/cleanup-on-exception mechanics.

**Error handling pattern:** `ValueError` raised before any file write (validate-then-write ordering) — reused verbatim, no new error type.

---

### `stub-server/byos_server.py` (service, request-response)

**Analog:** `read_led_enabled()` (lines 105-127, verified live)

**Imports/no-cross-import discipline:** This file never imports `server.device_config` (vendor-boundary discipline per its own docstring) — `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` must be **independently redefined** here, not imported, matching how `_HHMM_RE`/`QUIET_HOURS_TZ` are already duplicated rather than shared.

**Core read pattern** (copy of `read_led_enabled()`, lines 105-127):
```python
def read_led_enabled(state_dir):
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
New `read_wake_interval_s(state_dir, default)` follows this exact try/except and dict-shape-guard structure, but takes a `default` param (the caller's `self.args.sleep`) instead of a hardcoded `True`, and its final check is a bounded-int-excluding-bool test instead of `isinstance(value, bool)`:
```python
def read_wake_interval_s(state_dir, default):
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return default
    if not isinstance(data, dict):
        return default
    value = data.get("wake_interval_s")
    if (isinstance(value, int) and not isinstance(value, bool)
            and WAKE_INTERVAL_MIN_S <= value <= WAKE_INTERVAL_MAX_S):
        return value
    return default
```

**Call-site change** (verified live at line 415):
```python
"sleep_s": quiet_hours_sleep_s(self.args.sleep, self.args.state_dir),
```
becomes:
```python
"sleep_s": quiet_hours_sleep_s(
    read_wake_interval_s(self.args.state_dir, self.args.sleep),
    self.args.state_dir),
```
`quiet_hours_sleep_s(base_sleep_s, state_dir, now=None)`'s own signature/body is untouched — only the value passed as `base_sleep_s` changes. Also update the module docstring's local-modifications list and the inline comment at this line (matching the discipline Phase 10 used when it added the quiet-hours layer).

**Error handling pattern:** best-effort, never-raise, fail-open to `default` — identical shape to `read_led_enabled()`'s fail-open-to-`True`.

**No drift guard needed:** unlike `seconds_until_quiet_hours_end()`, this new function is NOT covered by `test_poll_cycle.py`'s existing `_quiet_hours_drift_guard` test — write it independently, no byte-for-byte pinning required.

---

### `companion/pages/config_page.py` (component + controller, CRUD)

**Analog:** `led_group()` (lines 365-420, verified live)

**Markup pattern** (`led_group()`, lines 405-420):
```python
def led_group(current_led_enabled):
    checked = " checked" if current_led_enabled else ""
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<label class="settings-checkbox">'
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
New `wake_interval_group(current_wake_interval_s)` follows the identical `.theme-status` / `<h2 class="text-heading">` / caption `<p>` shell (no `<fieldset>`/`<legend>`, matching this group's own documented rationale), swapping the checkbox `<label>` for a numeric `<label>` per 11-UI-SPEC.md's locked markup:
```python
def wake_interval_group(current_wake_interval_s):
    value_attr = (
        ' value="%d"' % current_wake_interval_s
        if current_wake_interval_s is not None else "")
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<label>Wake interval (seconds) '
        '<input type="number" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="Uses server default"%s></label>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(WAKE_INTERVAL_SECTION_HEADING),
        escape_html(WAKE_INTERVAL_SECTION_HEADING),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION),
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        value_attr,
    )
```
Placement: fifth `.theme-status` group, after `quiet_hours_group()`, per 11-UI-SPEC.md's locked order (Theme → Runway → Diagnostic LED → Quiet hours → Wake interval).

**Form-handling / int-conversion pattern (genuinely new — no prior int-typed field to copy):**
Every existing field in `handle_post()` passes form strings straight through (`quiet_hours_start`/`_end` are strings end-to-end; `led_enabled`/`quiet_hours_enabled` are presence-checked booleans). `wake_interval_s` is the **first field requiring an explicit str→int conversion gate** before `save_device_config()`:
```python
submitted_wake_interval = form.get("wake_interval_s")
if submitted_wake_interval is None or submitted_wake_interval == "":
    wake_interval_s = None  # leave unchanged / stays unset
else:
    try:
        wake_interval_s = int(submitted_wake_interval)
    except ValueError:
        return FLASH_SAVE_FAILED
```
then pass `wake_interval_s=wake_interval_s` into the single existing `save_device_config()` call site.

**Error handling pattern:** reuse the existing generic save-failed flash verbatim (`FLASH_KEY_SAVE_FAILED` / `FLASH_SAVE_FAILED`) — no field-specific error copy, matching every other field's `ValueError`-caught-by-`handle_post()`'s existing `except (ValueError, OSError): return FLASH_SAVE_FAILED` contract.

---

### `companion/app.py` (env-var pre-fill, controller)

**Analog:** `companion/auth.py`'s `configured_password()` (lines 45, 64-70, verified live)

```python
PASSWORD_ENV_VAR = "SKYPANE_COMPANION_PASSWORD"
...
def configured_password():
    """Return the shared password as bytes, or raise AuthNotConfigured.
    Never include the environment value in the raised exception.
    """
    value = os.environ.get(PASSWORD_ENV_VAR)
    if not value:
        ...
```
D-07 locks that `companion/app.py` should read `os.environ.get("SKYPANE_SLEEP_S")` the same way — but note the contract differs (fail-open to `None`/placeholder, not fail-closed/raise): parse to `int` with a bare fail-open fallback to `None` if absent or non-numeric, then pass into `config_page.render()`'s context for use only when the on-disk `wake_interval_s` value is `None`. Existing wiring precedent at `companion/app.py`'s `ctx["device_config"] = device_config.load_device_config(state_dir)` call site is where this new read slots in alongside.

---

## Shared Patterns

### Bool-vs-int validation gotcha
**Source:** RESEARCH.md Anti-Patterns (grounded in `normalise_led_enabled()`'s own deliberate-bool-only-check precedent, inverted)
**Apply to:** `normalise_wake_interval_s()`, `save_device_config()`'s new validation clause, `read_wake_interval_s()` — all three must use `isinstance(value, int) and not isinstance(value, bool)`, never a bare `isinstance(value, int)`.

### Validate-before-write / tmp-file-then-replace
**Source:** `server/device_config.py::save_device_config()` (lines 421-484)
**Apply to:** No change needed to this mechanism itself — the new `wake_interval_s` validation clause simply joins the existing sequential `if ...: raise ValueError(...)` block before `current = load_device_config(state_dir)` is read.

### Fail-open best-effort read in `byos_server.py`
**Source:** `read_led_enabled()` (lines 105-127)
**Apply to:** `read_wake_interval_s()` — same try/except `(OSError, ValueError)`, same dict-shape guard, same "any failure degrades to a safe default" contract, adapted to take a caller-supplied `default` instead of a hardcoded value.

### `.theme-status` group shell with no `<fieldset>`/`<legend>`
**Source:** `led_group()` / `quiet_hours_group()` (`companion/pages/config_page.py`)
**Apply to:** `wake_interval_group()` — identical wrapper div, `<h2 class="text-heading">` heading, single caption `<p>`, `DIRTY_SECTION_ATTR` on the wrapper.

### Generic save-failed flash
**Source:** `FLASH_KEY_SAVE_FAILED` / `FLASH_SAVE_FAILED` (`companion/pages/config_page.py`)
**Apply to:** Any `ValueError` from `save_device_config()` or the new int-conversion gate — no new error copy per 11-UI-SPEC.md's Copywriting Contract.

### Env-var read for a systemd-`EnvironmentFile`-injected value
**Source:** `companion/auth.py`'s `PASSWORD_ENV_VAR` / `os.environ.get()` pattern
**Apply to:** `companion/app.py`'s `SKYPANE_SLEEP_S` pre-fill read (D-07) — same `os.environ.get()` call shape, but fail-open (return `None`) rather than fail-closed (raise), since this is a UI pre-fill convenience, not an auth gate.

## No Analog Found

None — every touched file already has a directly-analogous sibling function/pattern in the same file, since this phase is a pure pattern-extension of an existing, well-established registry (`device_config.py`), poll handler (`byos_server.py`), and settings-page (`config_page.py`) family. The only genuinely novel elements (str→int form conversion, `None`-sentinel "unset" contract, first `<input type="number">`) are called out explicitly above with the closest available structural analog and the specific deltas from it — not "no pattern," but "adapt this pattern with these documented deltas."

## Metadata

**Analog search scope:** `server/device_config.py`, `stub-server/byos_server.py`, `companion/pages/config_page.py`, `companion/auth.py`, `companion/app.py` — all read live this session (2026-09-04), confirming 11-RESEARCH.md's cited line numbers are still accurate (led_group at 365-420, save_device_config at 421-484, read_led_enabled at 105-127, sleep_s call site at line 415).
**Files scanned:** 5 source files (no new files created by this phase) + 3 test files noted for required regression updates (`server/test_config_history.py`, `companion/test_config_page.py`, `stub-server/test_poll_cycle.py`)
**Pattern extraction date:** 2026-09-04
