# Phase 19: Companion Audit Follow-Through — Pattern Map

**Mapped:** 2026-09-11
**Files analyzed:** 27 (2 new, 19 modified production, 6 test harnesses)
**Analogs found:** 27 / 27 — every file lands in an existing, well-precedented pattern; there is no "no analog" bucket this phase (RESEARCH.md's Decision Implementation Map already did most of the file:line legwork — this document adds verified code excerpts and the exact copy-paste-and-adapt shape for each).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `companion/battery.py` (new) | utility (shared, non-page) | transform | `companion/pages/home_page.py`'s `battery_percent()` (the function being moved) | exact (verbatim move) |
| `companion/static/poll-cooldown.js` (new) | static asset (browser behaviour) | event-driven (DOM) | `companion/static/dirty-state.js` / `companion/static/copy-button.js` | exact |
| `companion/pages/health_page.py` | page module (controller-ish, server-rendered) | request-response + CRUD-read | itself (extending 6 existing sections) — cross-ref `companion/pages/home_page.py` for the text-verdict/tile idiom | exact |
| `companion/pages/config_page.py` | page module | request-response (form CRUD) | itself — cross-ref `companion/app.py:_render_login_page`/`_handle_login_post` for the 200-on-error precedent | exact |
| `companion/pages/history_page.py` | page module | request-response (read-only table) | itself | exact |
| `companion/pages/airlines_page.py` | page module | request-response (read + resolve-write) | itself | exact |
| `companion/pages/home_page.py` | page module | request-response (read) | itself (donor of `battery_percent()`, consumer of `companion/battery.py`) | exact |
| `companion/layout.py` | shared view helper / shell | transform (HTML assembly) | itself (`page_shell()`, `local_clock_text()`) | exact |
| `companion/app.py` | HTTP controller (`BaseHTTPRequestHandler`) | request-response + routing | itself (`_render_login_page`/`_handle_login_post`, `_send_hardening_headers`, `redirect`, `do_POST`, the 7-tuple `_serve_*_script` family) | exact |
| `companion/auth.py` | service (stateless crypto/session) | transform + in-memory state | itself (`LoginThrottle`, `issue_session_token`/`verify_session_token`) | exact |
| `companion/screens.py` | registry / config module | CRUD-read (static data) | itself (`SCREEN_TYPES`, `current_screen_id()`) — cross-ref `server/device_config.py`'s `RUNWAYS`/`THEMES` registries for the "id -> dict of display fields" idiom | exact |
| `companion/static/freshness.js` | static asset (browser behaviour) | event-driven, now fetch+swap | itself (full rewrite) — cross-ref `companion/static/list-filter.js`'s `userIsInteracting()`-style guard, `companion/static/copy-button.js` for the no-`innerHTML` discipline | exact |
| `companion/static/dirty-state.js` | static asset | event-driven (DOM) | itself | exact |
| `companion/static/copy-button.js` | static asset | event-driven (DOM + Clipboard API) | itself | exact |
| `companion/static/battery-trend.js` | static asset | transform (render on hover/tap) | itself | exact |
| `companion/static/panel-lookup.js` | static asset | event-driven (DOM) | itself | exact |
| `companion/static/style.css` | config/presentation | transform | itself | exact |
| `server/device_config.py` | model / registry + persistence | CRUD | itself (`RUNWAYS`, `THEMES`, `load_device_config()`/`save_device_config()`, `normalise_*()` family) | exact |
| `deploy/skypane.env.example` | config | file-I/O (documentation) | itself (`SKYPANE_COMPANION_PASSWORD`/`SKYPANE_COMPANION_HOST` entries) | exact |
| `companion/test_companion_app.py` | test harness | batch (self-executing check list) | itself (`check()`, the 4-static-route "cross-file agreement" checks, the ES5-safe-source checks) | exact |
| `companion/test_config_page.py` | test harness | batch | itself | exact |
| `companion/test_status_pages.py` | test harness | batch | itself | exact |
| `companion/test_view_pages.py` | test harness | batch | itself | exact |
| `companion/test_contrast_check.py` | test harness | batch | itself (unaffected, listed for completeness) | exact |
| `server/test_config_history.py` | test harness | batch | itself (`check()`, `EXPECTED_CHECK_COUNT`) | exact |
| `server/test_runway_config.py` | test harness | batch | itself | exact |

## Pattern Assignments

### `companion/battery.py` (new file) — utility, transform

**Analog:** `companion/pages/home_page.py:106-124` (the function being moved verbatim)

**Current code to move** (`companion/pages/home_page.py:106-124`):
```python
# A rough state-of-charge estimate for a single-cell LiPo: 4.2V full,
# 3.3V empty, linear in between. It is an estimate, and labelled as one
# ("≈") — the frame's own low-battery warning still uses the exact
# millivolt thresholds in server/poll_loop.py.
BATTERY_FULL_MV = 4200
BATTERY_EMPTY_MV = 3300


def battery_percent(mv):
    """A clamped 0-100 estimate for `mv`, or None for a non-numeric or
    non-positive reading. Never raises."""
    try:
        value = float(mv)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    ratio = (value - BATTERY_EMPTY_MV) / float(BATTERY_FULL_MV - BATTERY_EMPTY_MV)
    return int(round(max(0.0, min(1.0, ratio)) * 100))
```
**Module docstring precedent to follow** — `companion/auth.py:1-8` shows this codebase's convention for a shared, page-independent module: state why it exists and what it must never import/depend on:
```python
"""companion/auth.py — the shared-password session gate for the SkyPane
companion service ...
```
`companion/pages/__init__.py`'s own documented boundary ("no page module imports another page module") is *why* this file must exist — `companion/battery.py` sits beside `companion/auth.py`, `companion/layout.py`, `companion/screens.py` (all non-page shared modules imported by page modules), not inside `companion/pages/`. Both `home_page.py` and `health_page.py` become `import companion.battery as battery` consumers; `home_page.py` keeps its own `battery_percent` name gone (retarget the two call sites at `home_page.py:191`/`197` to `battery.battery_percent(...)`).

---

### `companion/static/poll-cooldown.js` (new file) — static asset, event-driven

**Analog:** `companion/static/dirty-state.js` (full file, guard-clause idiom) and `companion/static/copy-button.js` (data-attribute-driven, ES5-safe, `setTimeout`-based transient state — directly structurally closest to the countdown+disable-on-submit behaviour being externalized).

**Header-comment convention** (`companion/static/copy-button.js:1-26`, `companion/static/dirty-state.js:1-39`) — every static file in this project opens with: which decision introduced it, the ES5-safe-subset constraint, the exact `*_SCRIPT_ROUTE` it is served from, and the standing "no `innerHTML`, no other HTML-writing sink" constraint. Copy this shape verbatim for the new file's header, naming D-18 and `POLL_COOLDOWN_SCRIPT_ROUTE`.

**Guard-clause idiom to reuse** (`companion/static/dirty-state.js:40-53`):
```javascript
(function () {
  "use strict";

  var form = document.querySelector("form[data-dirty-form]");
  if (!form) {
    return;
  }

  var bar = document.querySelector("[data-dirty-bar]");
  var countEl = document.querySelector("[data-dirty-count]");
  var cancelBtn = document.querySelector("[data-dirty-cancel]");
  if (!bar || !countEl) {
    return;
  }
  ...
```
Apply the same shape: look up the poll button by id, read `data-cooldown`/etc. attributes off it (`button.getAttribute("data-cooldown")`), and `return` immediately if the button is absent — matching this file's own load-bearing-not-defensive-noise convention (every static script is served to every page; only one page renders the relevant markup).

**The exact logic to port unmodified** — the two inline scripts being externalized, `companion/pages/config_page.py:1192-1290` (`_poll_cooldown_script()` and `_poll_submit_script()`), already contain the full, ES5-safe, `_js_literal()`-escaped countdown + disable-on-submit logic:
```python
# companion/pages/config_page.py:1213-1242 (_poll_cooldown_script body, decoded)
var remaining = <cooldown_remaining>;
var btn = document.getElementById(<POLL_TRIGGER_BUTTON_ID>);
var text = document.getElementById(<POLL_COOLDOWN_TEXT_ID>);
if (!btn || !text || remaining <= 0) { return; }
var template = <POLL_COOLDOWN_HELPER_TEXT template>;
var token = <POLL_COOLDOWN_TEMPLATE_TOKEN>;
var timer = setInterval(function () {
  remaining -= 1;
  if (remaining <= 0) {
    clearInterval(timer);
    btn.removeAttribute("disabled");
    text.textContent = "";
    return;
  }
  text.textContent = template.replace(token, String(remaining));
}, 1000);
```
```python
# companion/pages/config_page.py:1273-1290 (_poll_submit_script body, decoded)
var btn = document.getElementById(<POLL_TRIGGER_BUTTON_ID>);
if (!btn) { return; }
var form = btn.form;
if (!form) { return; }
form.addEventListener("submit", function () {
  btn.disabled = true;
  btn.textContent = <POLL_SUBMIT_PENDING_TEXT>;
});
```
Port both IIFEs into the one new file, reading their previously-Python-injected values (`remaining`, the template text, the button id) off `data-cooldown`, `data-cooldown-text-id`... attributes added to the button markup in `poll_trigger_section()`, per D-18's own text. Do not re-derive the countdown math or the disable-on-submit affordance — both must survive byte-for-byte in behaviour (RESEARCH.md Assumption A3: only moving the countdown and forgetting the submit-affordance script silently breaks a second feature).

**Test harness pattern to extend** — `companion/test_companion_app.py:2543-2565` (`_static_script_public()`), `2600-2626` (`_panel_lookup_script_es5_safe_and_no_html_write()` — the ES5/forbidden-token check), and `2671-2679` (route/src agreement check) are the three checks every new static script gets; write the same three for `poll-cooldown.js`.

---

### `companion/pages/health_page.py` (page module, request-response)

**Analog:** itself; cross-reference `companion/pages/home_page.py` for the text-verdict tile idiom D-03 imports.

**D-01 — shared battery %:**
```python
# companion/pages/home_page.py:189-201 (the pattern health_page._device_section()/
# tile builder must mirror, substituting battery.battery_percent for the
# in-module battery_percent once it moves)
reading = _safe_query(ctx.get("state_dir"), _latest_battery)
if reading and reading.get("battery_mv"):
    pct = battery_percent(reading["battery_mv"])
    pct_text = ("≈ %d%%" % pct) if pct is not None else ""
    battery_html = (
        '<p class="text-body widget-verdict">%s</p>'
        '<p class="text-label widget-detail">%s · %s mV · %s</p>'
    ) % (
        escape_html(pct_text or BATTERY_STATE_TEXT.get(battery_state, "")),
        ...
    )
```

**D-03 — text verdict beside colour (WCAG 1.4.1):** `companion/pages/home_page.py:89-104, 183-208` is the exact dict-plus-`<p class="text-body widget-verdict">` idiom to copy into `health_page.py`'s tile builders (`_device_section()`/`_pipeline_section()` around line 1403-1476, 2423-2441):
```python
FRAME_STATE_TEXT = {
    "ok": "Checking in normally",
    "warn": "Has not checked in for a while",
    "error": "Has not checked in for a long time",
}
...
frame_body = '<p class="text-body widget-verdict">%s</p>' % escape_html(
    FRAME_STATE_TEXT.get(device_state, FRAME_STATE_TEXT["warn"]))
```
And the tile wrapper both pages share, `companion/layout.py:1218-1256` (`stat_tile()`):
```python
def stat_tile(caption, content_html, status=None, icon=None):
    css_class = "stat-tile " + _STAT_TILE_BORDER_CLASSES.get(
        status, _DEFAULT_STAT_TILE_CLASS)
    ...
```
`status` already drives the border colour; the verdict text is purely inside `content_html` — no `stat_tile()` change needed, only what each caller passes in.

**D-04 — fixed sparkline range + width-aware density:** lands in `battery_sparkline_svg()` (`health_page.py:776+`) and `_SPARKLINE_DENSE_POINT_THRESHOLD = 39` (`health_page.py:637`). No close in-file analog for "width-aware density" exists yet — this is genuinely new logic (derive threshold from rendered width in px / points-per-pixel), but the fixed-range change is a one-line swap: replace `lo, hi = min(values), max(values)` with the locked constants `3000, 4200` (clamped).

**D-05 — wake-interval-derived staleness:** `STALE_DEVICE_WARN_S = 3600` / `STALE_DEVICE_ERROR_S = 21600` (`health_page.py:91-92`) become functions of `wake_interval_s`, mirroring how `config_page.py:1644-1646` already reads the same env-fallback chain:
```python
# companion/pages/config_page.py:1644-1646 — the fallback-chain idiom to copy
current_wake_interval_s = device_cfg.get("wake_interval_s")
if current_wake_interval_s is None:
    current_wake_interval_s = ctx.get("wake_interval_env_default")
```
`battery_status()` (`health_page.py:1023-1041`) demotes its `"error"` return to `"warn"` — the function's shape is otherwise unchanged (single early-return scan over chronological pairs).
`overall_severity()` (`health_page.py:1100-1128`) already folds three states plus a boolean flag through a documented precedence table — extending it to also read `coverage_status()`/source-fault is the same shape, one more input, same three-line precedence body:
```python
def overall_severity(device_state, pipeline_state, battery_state, disagreement_warn):
    states = (device_state, pipeline_state, battery_state)
    if "error" in states:
        return "error"
    if "warn" in states or disagreement_warn:
        return "warn"
    return "ok"
```

**D-06 — plain language + `title` tooltip:** `_CORROBORATION_ROWS` (`health_page.py:136-149`) is a tuple-of-tuples `(stored_value, label, status, explanation)` — the label string is what changes ("Agreement" → "Both agree"), and the *technical* term moves into a `title="Corroboration"`-style attribute wherever the row renders (find the render call at `health_page.py:1787-1816`). `PIPELINE_FRESHNESS_LABEL`/`RESOLUTION_RATE_LABEL` (lines 195, 319) are simple string constants — edit in place, add a `title=` attribute at the one call site each feeds.

**D-02 — fetch-and-swap freshness (paired with `companion/static/freshness.js` below):** the freshness pill block in `render()` (`health_page.py:1773`, near the existing `<script src="%s" defer></script>` splice for `BATTERY_TREND_SCRIPT_SRC`) is the server-side half — it must keep computing `"Updated HH:MM"` server-side per `layout.local_clock_text()`, and must NOT gain any new client-computed state. No new pattern needed here beyond what already exists; the change is confined to the copy string and (RESEARCH.md Pitfall 5) making sure the nav-dot severity class and `.dashboard-grid`/`.battery-readout`/anomaly-banner markup are all inside whatever region gets fetched-and-swapped.

**Health check() harness pattern** (`companion/test_status_pages.py`) mirrors `test_companion_app.py`'s `check(name, fn)` (see Shared Patterns below) — every new/retargeted assertion in this file follows that same `def _x(): ... return True/False, reason` + `check("...", _x)` shape.

---

### `companion/pages/config_page.py` (page module, request-response form CRUD)

**Analog:** itself, plus `companion/app.py:_render_login_page`/`_handle_login_post` (`app.py:1246-1249`, `2000-2020`) as the *cross-file* precedent D-07 explicitly mirrors.

**D-07 — field-level errors via signature widening, not a rewrite.** This is the highest-risk file in the phase (75 pinned `handle_post()` calls, 46 pinned `render()` calls in `companion/test_config_page.py`). The existing 200-on-failure precedent already lives in `companion/app.py`:
```python
# companion/app.py:1246-1249 — _render_login_page(), the exact precedent D-07 mirrors
def _render_login_page(self, error=None, lockout_seconds=None, next_route=None):
    body = self._login_body(
        error=error, lockout_seconds=lockout_seconds, next_route=next_route)
    return layout.login_shell(body, ui_theme=self._resolved_ui_theme())
```
```python
# companion/app.py:2018-2020 — _handle_login_post()'s failure branch: re-render
# at a non-303 status with the error carried in, never a redirect-with-flash
LOGIN_THROTTLE.record_failure()
return self.send_html(401, self._render_login_page(
    error="Incorrect password. Try again.", next_route=next_route))
```
Apply the identical shape to Settings: `render(ctx, scope=SCOPE_ALL, errors=None, submitted=None)` — both new params fully defaulted so all 46 existing call sites are untouched (`render()`'s current signature is at `config_page.py:1617`). Each field builder (e.g. `quiet_hours_group()`, `runway_fieldset()`) needs the same `errors=None, submitted=None` threading and must read `submitted.get(field, <today's ctx-sourced value>)` — see the existing fallback-chain idiom at `config_page.py:1644-1646` for the "no `or`, explicit `is None`/`.get()` with a documented default" convention this codebase always uses for a value that has a legitimate falsy/None state.
`handle_post(form, ctx, errors=None)` (current signature `config_page.py:1888`) gets a tiny `_note_error(errors, field, message)` no-op-when-`None` helper, called at each of its validation-failure `return FLASH_SAVE_FAILED` sites (the membership-test pattern already established, e.g. the runway-id/theme-id checks documented in `handle_post()`'s own docstring at `config_page.py:1909-1922`).
`companion/app.py`'s `_handle_settings_post()` (`app.py:2022-2114+`) is the sole call site that passes `errors={}` and branches to a direct 200 render (mirroring `_handle_login_post()`'s shape above) instead of `self.redirect(...)` when `errors` comes back non-empty.

**D-08 — dedicated calendar disconnect.** Current inline checkbox to remove, `config_page.py:1109-1128`:
```python
disconnect_checkbox_html = ""
if configured or drift:
    disconnect_checkbox_html = (
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="calendar_disconnect" '
        'id="calendar-disconnect" value="%s"> %s'
        "</label>"
    ) % (
        escape_html(CALENDAR_DISCONNECT_CHECKBOX_VALUE),
        escape_html(CALENDAR_DISCONNECT_CHECKBOX_LABEL),
    )
```
`submitted_calendar_signal(form)` (`config_page.py:1824-1885`) is the single shared resolver both `handle_post()` and the new dedicated route call — its 6-gate docstring is itself the analog for how a new, simpler dedicated-route call should be shaped: call the SAME function (never reimplement), gates 1-3 (the in-form checkbox interpretation) simply become dead-but-harmless for the `/settings` POST body once the checkbox is gone from that form's markup (RESEARCH.md Pitfall 7 — do not delete gates 1-3 without grepping every caller first).
The new route's own confirm-page pattern has no exact analog in this codebase yet (this is genuinely the first two-step server-rendered confirm flow) — closest structural cousin is the login page's own `self.send_html(200, ...)` / `self.redirect(...)` branching in `_handle_login_post()` above: render a small intermediate page when `confirm=yes` is absent, act + redirect when present.

**D-09/D-10 — dirty-ready gating + beforeunload.** Full existing file is `companion/static/dirty-state.js` (read in full above) — D-09 adds one line near the top-level IIFE body (after `bar`/`countEl` are confirmed present):
```javascript
document.documentElement.classList.add("dirty-ready");
```
mirroring `nav-dropdown.js`'s own unconditional `.js` class-add this file's header comment already references (`dirty-state.js:31-34`). D-10's `beforeunload` guard is a new `window.addEventListener` beside the existing `form.addEventListener("change", updateBar)` / `("input", updateBar)` pair at `dirty-state.js:172-173`, gated on `countDifferences() > 0` (already a defined function, reuse directly — do not reimplement the diff count) and cleared inside the existing Save (`form="{SETTINGS_FORM_ID}"` native submit — no JS hook needed since the page navigates away) and Cancel handlers (the existing `cancelBtn.addEventListener("click", ...)` at `dirty-state.js:175-180`).

**D-11 — runway labels.** Purely a data change in `server/device_config.py`, see that file's section below; `config_page.py` needs no code change — `runway_fieldset()` already calls `device_config.runway_label(...)`.

**D-12 — fieldset/aria groups — CRITICAL PRE-EXISTING TENSION.** This codebase deliberately *removed* every `<fieldset>`/`<legend>` from this exact page in an earlier phase, and multiple pinned checks assert **zero** `<fieldset>` elements anywhere on the rendered page:
```python
# companion/test_config_page.py:457-458, 612-613, 855-856, 2825-2826 (four separate pinned checks)
if "<fieldset" in rendered:
    return False, "expected zero <fieldset> elements anywhere on the page, found one"
```
`config_page.py`'s own docstrings name the reason (`config_page.py:560-565, 711-712, 835-839`): "a `<legend>` only has accessible-name semantics inside a `<fieldset>`, which these sibling groups deliberately do not have." **Implementing D-12 with a literal `<fieldset>`/`<legend>` will fail four existing pinned checks by name.** D-12's own text offers the escape hatch: `role="radiogroup"` + `aria-labelledby` pointing at the group's existing `<h2>` — this is the version to build, since it adds zero `<fieldset>`/`<legend>` elements and is compatible with every existing pinned check. Apply it to `_theme_chip_grid_html()` (`config_page.py:489-543`, wrap the returned `<div class="theme-chip-grid">` with `role="radiogroup" aria-labelledby="<id-of-sibling-h2>"`) and the runway row inside `runway_fieldset()` (`config_page.py:673-763`) the same way. Every hint `<p class="section-caption">` needs an `id` and its control an `aria-describedby` pointing at it — `quiet_hours_group()`'s caption (`config_page.py:830-884`) is a template for adding an `id` to an existing `<p class="text-label section-caption">` without otherwise touching its markup.

**D-13 — next-wake countdown.** Genuinely new logic; closest analog for the *time-formatting* half is `companion/layout.py:641-660` (`local_clock_text()`, already required by name in CONTEXT.md):
```python
def local_clock_text(parsed, now_parsed=None):
    ...
    local = parsed.astimezone(LOCAL_TZ)
    clock = local.strftime("%H:%M")
    ...
```
Compute `last_checkin + effective_wake_interval_s`, feed the result through this exact function. The "effective interval" fallback chain to copy is `config_page.py:1644-1646` (`wake_interval_s` -> env default -> `DISPLAY_OFF_SLEEP_S` while off, same `.get()`-chain idiom, no `or`).

**D-14 — quiet-hours presets.** Client-only, no server change. `quiet_hours_group()` (`config_page.py:830-884`) is the analog for the markup being extended — add three `<button type="button">` elements above the existing two `<input type="time">` elements; no existing inline-script precedent should be copied here (D-18 forbids new inline scripts) — the fill logic must live in a `<script>`-free `data-preset-start`/`data-preset-end` attribute pair read by a *tiny* addition to an already-served static script (or its own new one) that sets the two time inputs' `.value` and dispatches a `change` event so `dirty-state.js`'s existing `form.addEventListener("change", ...)` picks it up for free — reuse, never reimplement, the dirty-marking.

---

### `companion/auth.py` (service, D-15/D-16/D-17)

**Analog:** itself — this is the module already carrying every relevant precedent (constant-time compare, stateless HMAC tokens, the `LoginThrottle` class).

**D-15 — reset the failure counter when the lockout window has elapsed.** Current buggy method:
```python
# companion/auth.py:187-190 (current)
def record_failure(self):
    self._failures += 1
    if self._failures >= self._limit:
        self._locked_until = time.time() + self._lockout_s
```
Fix (RESEARCH.md's own Code Example, verified against the live file):
```python
def record_failure(self):
    if self._failures >= self._limit and time.time() >= self._locked_until:
        self._failures = 0  # the previous window fully elapsed; start counting fresh
    self._failures += 1
    if self._failures >= self._limit:
        self._locked_until = time.time() + self._lockout_s
```
Pinned test to leave passing, extend with a sibling: `companion/test_companion_app.py:798-815` (`_login_throttle_allows_locks_and_resets`) exercises only the `record_success()` reset path — follow its exact shape (`throttle = auth.LoginThrottle(limit=3, lockout_s=60)`, drive it via `record_failure()`/`locked_out()`/`seconds_remaining()`) for the new "fails again immediately after window elapses only counts once" check, using a `time.time()`-patched or a `lockout_s=0`-style trick to avoid a real sleep in the harness.

**D-16 — signing-key derivation + revocation set.** Current unkeyed-derivation call sites to change:
```python
# companion/auth.py:92-97 (current issue_session_token — signs with the raw password)
def issue_session_token():
    expiry = str(int(time.time()) + SESSION_TTL_S)
    signature = hmac.new(
        configured_password(), expiry.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (expiry, signature)
```
New shape (module-level salt, one `_signing_key()` indirection, same call sites otherwise unchanged) — matches this file's own top-level-constant convention (`PASSWORD_ENV_VAR`, `SESSION_TTL_S` etc. at `auth.py:45-50`):
```python
_PROCESS_SALT = secrets.token_bytes(32)

def _signing_key():
    return hmac.new(configured_password(), _PROCESS_SALT, hashlib.sha256).digest()

def issue_session_token():
    expiry = str(int(time.time()) + SESSION_TTL_S)
    signature = hmac.new(_signing_key(), expiry.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (expiry, signature)
```
`verify_session_token()` (`auth.py:100-125`) gets the identical `configured_password()` -> `_signing_key()` substitution inside its existing try/except shape — no control-flow change.
Revocation set: per the orchestrator's resolution, lives in `companion/auth.py`. Model it on this file's own `LoginThrottle` class (`auth.py:169-201`) — a small class or module-level state with the same "process-global, not per-session" framing already documented there, e.g. a `_REVOKED_TOKENS = {}` dict plus a `threading.Lock()`, consulted from a new `is_revoked(token)` and mutated by a new `revoke(token, expiry_int)`, pruning on each check (RESEARCH.md Pitfall 3's own code sketch). `companion/app.py`'s existing `_POLL_LOCK` (grepped, a plain `threading.Lock()` guarding `_handle_poll_now()`) is the cross-file precedent for "a lock around small shared mutable state in this codebase," even though the lock itself now lives in `auth.py` instead.
`_is_authenticated()`/`require_session()` (`app.py:916-942` per RESEARCH.md) is the sole call site that must additionally check `not auth.is_revoked(token)` — do not duplicate the check at any of the 9+ `require_session()` call sites in `do_POST()`/`do_GET()`.
The `LOGOUT_ROUTE` handler (`app.py:2255-2256`, currently `return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())`) must extract the token from the request's cookie *before* building the logout response and call `auth.revoke(token, ...)`.

**D-17 — conditional `Secure` cookie.** Current unconditional flag:
```python
# companion/auth.py:128-139 (session_set_cookie_header, current)
def session_set_cookie_header(token):
    return (
        "%s=%s; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=%d"
        % (SESSION_COOKIE_NAME, token, SESSION_TTL_S))
```
Both this function and `logout_set_cookie_header()` (`auth.py:142-149`) need `Secure` swapped for a value computed once from `os.environ.get("SKYPANE_COMPANION_INSECURE_COOKIES") != "1"` — follow `configured_password()`'s own `os.environ.get(...)` idiom (`auth.py:69`) for reading the new var, and document it with the same "never silently defaults to insecure" framing `AuthNotConfigured`'s docstring already uses (`auth.py:53-61`).
Pinned test to extend: `companion/test_companion_app.py:763-771` (`_session_cookie_header_carries_security_flags`) stays valid unmodified (env var unset in the harness); add a sibling that sets the env var and asserts `Secure` is absent.

---

### `companion/app.py` (D-16/D-18 route gating, D-18 headers)

**Analog:** itself — `_send_hardening_headers()`, `send_html()`, `redirect()`, `do_POST()`'s existing gated-route branches are all in this one file.

**D-18a — gate `/ui-theme` and `/logout`.** Current ungated branches:
```python
# companion/app.py:2252-2256 (current, ungated)
if path == THEME_ROUTE:
    return self._handle_theme_post()

if path == LOGOUT_ROUTE:
    return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())
```
Every other state-changing route in the same function already follows the gate-then-dispatch shape to copy verbatim, e.g.:
```python
# companion/app.py:2232-2235 (the pattern to copy)
if path == SETTINGS_ROUTE:
    if not self.require_session():
        return None
    return self._handle_settings_post()
```

**D-18b — hardening headers + CSP on every response, including redirects.** Current `_send_hardening_headers()` (`app.py:855-867`) sets three headers but no CSP, and `redirect()` (`app.py:906-912`) never calls it at all:
```python
# companion/app.py:855-867 (current)
def _send_hardening_headers(self):
    self.send_header("X-Content-Type-Options", "nosniff")
    self.send_header("X-Frame-Options", "DENY")
    self.send_header("Referrer-Policy", "same-origin")
```
```python
# companion/app.py:906-912 (current redirect — no hardening headers at all)
def redirect(self, location, set_cookie=None):
    self.send_response(303)
    self.send_header("Location", location)
    if set_cookie:
        self.send_header("Set-Cookie", set_cookie)
    self.send_header("Content-Length", "0")
    self.end_headers()
```
Add the locked CSP string as a fourth `send_header` call inside `_send_hardening_headers()` (the amended D-18 CSP: `style-src 'self' 'unsafe-inline'` per the orchestrator's resolution — the swatch `style="background:..."` attributes stay, no CSS-class refactor), then add one `self._send_hardening_headers()` call inside `redirect()`, matching `send_html()`'s/`send_bytes()`'s existing call to the same method (`app.py:878`, `902`).
Pinned tests to extend: none currently assert CSP presence or redirect-headers (RESEARCH.md's Wave 0 Gaps) — new checks follow `companion/test_companion_app.py`'s own `check()` shape (see Shared Patterns).

**D-18c — the duplicated-not-imported static-script contract (for `poll-cooldown.js`).** This is the exact mechanical recipe to follow, verified live across three files:
1. `companion/app.py` route + path constants, alongside the seven existing ones (`app.py:110-135`):
```python
STYLE_ROUTE = "/static/style.css"
SCRIPT_ROUTE = "/static/battery-trend.js"
...
FLASH_CLEANUP_SCRIPT_ROUTE = "/static/flash-cleanup.js"
# NEW: POLL_COOLDOWN_SCRIPT_ROUTE = "/static/poll-cooldown.js"
```
```python
_BATTERY_TREND_JS_PATH = os.path.join(_HERE, "static", "battery-trend.js")
...
_FLASH_CLEANUP_JS_PATH = os.path.join(_HERE, "static", "flash-cleanup.js")
# NEW: _POLL_COOLDOWN_JS_PATH = os.path.join(_HERE, "static", "poll-cooldown.js")
```
2. A thin delegate method, identical in shape to every sibling (`app.py:1322-1333`):
```python
def _serve_copy_button_script(self):
    """Serve companion/static/copy-button.js, pre-auth. Thin delegate
    onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
    ...
    """
    return self._serve_script_file(_COPY_BUTTON_JS_PATH)
# NEW: def _serve_poll_cooldown_script(self): return self._serve_script_file(_POLL_COOLDOWN_JS_PATH)
```
3. One dispatch line in `do_GET()` (`app.py:1915-1921` shows the existing pattern; add a matching `elif path == POLL_COOLDOWN_SCRIPT_ROUTE: return self._serve_poll_cooldown_script()`).
4. `companion/layout.py`'s matching `*_SCRIPT_SRC` constant, with the "duplicated rather than imported... same duplicated-not-imported contract" comment every sibling constant already carries (`layout.py:113-137`):
```python
# NEW, alongside FLASH_CLEANUP_SCRIPT_SRC:
POLL_COOLDOWN_SCRIPT_SRC = "/static/poll-cooldown.js"
```
5. `page_shell()`'s script-tag list and its trailing tuple both grow by one (`layout.py:1110-1116` the format-string list, `layout.py:1132-1146` the value tuple) — copy the exact pattern of the seventh entry (`FLASH_CLEANUP_SCRIPT_SRC`) for the eighth.
6. The cross-file "route equals src" test, `companion/test_companion_app.py:2567-2591` (`_four_new_static_routes_dom_contract_guard`) and `2671-2679` (`_panel_lookup_script_route_src_agree`, the single-constant variant) — write the single-constant variant for `poll-cooldown.js`.

---

### `companion/pages/history_page.py` (D-19/D-20)

**Analog:** itself.

**D-19 — drop Runway column, shorten timestamp, scroller a11y.** Current 7-header tuple:
```python
# companion/pages/history_page.py:132-135 (current)
_HEADERS = (
    "Timestamp", "Callsign", "Type", "Route", "State", "Corroboration",
    "Runway",
)
```
Drop the last element (→ 6 headers); the `<td>` emitting the tracked-runway value inside `_history_table_html()` (`history_page.py:668-719`) is removed in the same pass, and its content is folded into the row's `title=` attribute instead (find the `<tr>` open tag in the same function and add `title="%s"`). The scroller wrapper needing `tabindex="0"` + `aria-label` is the `.data-table-wrap` div emitted around the `<table>` in the same function — a `tabindex`/`aria-label` pair addition, no structural change.
Timestamp shortening: `layout.concise_timestamp_html(row["raw_ts"], now)` (called at `history_page.py:689`, `779`) currently includes a relative-age suffix; the shorter clock-only rendering should call `layout.local_clock_text(parsed, now_parsed=now)` directly instead (verified analog at `layout.py:641-660`, shown above under D-13) rather than inventing a new formatter.

**D-20 — visible copy feedback + accessible per-row names + real success check.** Current feedback write (visually-hidden only):
```javascript
// companion/static/copy-button.js:55-64 (current)
function showFeedback(button) {
  var feedbackEl = button.nextElementSibling;
  if (!feedbackEl || !feedbackEl.hasAttribute("data-copy-feedback")) {
    return;
  }
  feedbackEl.textContent = FEEDBACK_TEXT;
  window.setTimeout(function () {
    feedbackEl.textContent = "";
  }, FEEDBACK_RESET_MS);
}
```
The `data-copy-feedback` span already exists and is already `aria-live="polite"` (`history_page.py:539-553`, `_copy_button_html()`) — D-20's "visible" requirement is a CSS change (`companion/static/style.css`: drop `visually-hidden` from that span's class list or swap it for a visible transient badge class) plus keeping the exact same `textContent` write; no JS structural change needed for visibility.
Success-gating: `fallbackCopy()` (`copy-button.js:38-53`) calls `document.execCommand("copy")` and discards its boolean return; `handleClick()` (`copy-button.js:66-83`) must only call `showFeedback(button)` when that boolean (or the Clipboard-API promise resolving) is true — restructure `fallbackCopy` to `return document.execCommand("copy");` and gate the `showFeedback` call on it, matching the existing `.then(resolve, reject)` split already present for the Clipboard-API branch.
Per-row accessible name: `_copy_button_html(value, label)` (`history_page.py:539-553`) already takes a `label` parameter — the call sites (inside `_callsign_hex_cell()`, `history_page.py:556+`, and the Timestamp column's own copy button) need the row's callsign folded into the `label` string they pass, e.g. `_COPY_HEX_LABEL % callsign` instead of the bare constant — no new escaping path, `escape_html(label)` already runs inside `_copy_button_html()`.

---

### `companion/pages/airlines_page.py` (D-21/D-22)

**Analog:** itself.

**D-21 — "Unidentified airlines" strip + resolve-panel back link.** Current gap-card assembly with no heading:
```python
# companion/pages/airlines_page.py:1760, 1836 (render()'s call site, current)
gap_cards_html = "".join(_gap_card_html(i, row) for i, row in enumerate(gap_shown))
...
+ _gallery_grid_html(pairs, state_dir, gap_cards_html, manual_info_by_name)
```
Wrap `gap_cards_html` in a heading+sentence block before it is passed into `_gallery_grid_html()` — the plain-sentence copy convention to match is `health_page.py`'s `SOURCE_FAULT_BODY`/`ANOMALY_BANNER_TEXT` style (a module-level string constant, escaped once at its single render call site).
Back link, current:
```python
# companion/pages/airlines_page.py:1540 (current)
back_link = '<a class="text-label" href="/health">%s</a>' % RESOLVE_BACK_LINK_TEXT
```
Change `href="/health"` to `href="/airlines"` — a one-line data change; `RESOLVE_BACK_LINK_TEXT` constant (`airlines_page.py:299`) can stay as-is or be reworded ("← Back to Airlines"), Claude's Discretion per CONTEXT.md's copy latitude.

**D-22 — illustration forms only on `?edit=1`.** `_lightbox_replace_form_html()` (`airlines_page.py:505+`) is called unconditionally today inside the shared dialog builder (call site `airlines_page.py:1129`). Gate that call (and the sibling resolve-upload/delete form calls the same builder makes, per `panel-lookup.js`'s own comment confirming 3 `setAttribute("action"...)` writes total) behind a new `ctx`/query-param check, e.g. `edit_mode = ctx.get("query", {}).get("edit") == "1"` — follow `submitted_scope(form)`'s existing query/form-reading idiom in `config_page.py` for how this codebase already reads a query-string flag into a plain boolean. The Device-page "Edit artwork" link is a one-line addition to `config_page.py`'s Device-page assembly, `<a href="/airlines?edit=1">Edit artwork</a>`, styled like any other `text-label` link already in that file.

---

### `server/device_config.py` (D-11, D-23)

**Analog:** itself — `THEMES`/`RUNWAYS` are sibling registries with an identical shape; `normalise_*()` functions are the established validation idiom.

**D-11 — runway labels**, current registry (self-verifying against `test_view_pages.py`, no test edit needed — see RESEARCH.md's own Code Example):
```python
# server/device_config.py:416-432 (current)
RUNWAYS = {
    "3": {
        "label": "Piste 3",
        "tag_text": "ORY · RWY 3",
        "empty_heading": "Watching Runway 3",
    },
    "06-24": {
        "label": "Piste 4",
        "tag_text": "ORY · RWY 06/24",
        "empty_heading": "Watching Runway 06/24",
    },
    "02-20": {
        "label": "Piste 2",
        "tag_text": "ORY · RWY 02/20",
        "empty_heading": "Watching Runway 02/20",
    },
}
```
Change only the three `"label"` values to `"Runway 3 (07/25)"`, `"Runway 4 (06/24)"`, `"Runway 2 (02/20)"` (D-11's exact wording — note the "3" runway's parenthetical is "07/25", not derivable from its own key "3", so it must be typed by hand, not templated from the dict key). `runway_label()` (`server/device_config.py:960-961`) needs no change:
```python
def runway_label(runway_id):
    return RUNWAYS[runway_id]["label"]
```

**D-23 — `screen_id` seam.** `companion/screens.py`'s `SCREEN_IDS`/`DEFAULT_SCREEN_ID` (`screens.py:41, 61`) are the values to normalise against — model the new `normalise_screen_id()` on any existing `normalise_*()` in this file (grep for the pattern; `runway_label`'s sibling read-helpers and the `RUNWAY_IDS` membership check at `device_config.py:716` — `raise ValueError("unknown tracked_runway id %r (expected one of %r)" % (tracked_runway, RUNWAY_IDS))` — show the exact "membership test, raise/normalise on the write path, degrade to default on the read path" split this codebase uses everywhere). `load_device_config()`/`save_device_config()` need one more key added to their existing default-fill and validation logic, following the same shape every other key (`tracked_runway`, `led_enabled`, ...) already uses.
**Every dict-equality check in `server/test_config_history.py`** (multiple, e.g. lines ~100, 116, 131, 144, 193, 225 per RESEARCH.md) will need `"screen_id": "plane-frame"` added to its expected literal — this is the single highest-count mechanical retarget in the phase; grep `server/test_config_history.py` for `{` dict literals containing `"tracked_runway"` to find every one.

---

## Shared Patterns

### `check(name, fn)` test-harness convention
**Source:** `companion/test_companion_app.py:681-690` (identical shape in every one of the 6 harnesses touched this phase, including `server/test_config_history.py:73`)
```python
def check(name, fn):
    try:
        ok, reason = fn()
    except Exception as exc:  # never let an exception be swallowed into a pass
        ok, reason = False, "exception: %r" % (exc,)
    results.append((name, ok))
    if ok:
        print("PASS %s" % name)
    else:
        print("FAIL %s - %s" % (name, reason))
```
**Apply to:** every new/retargeted assertion in all 6 test files — always a nested `def _x(): ... return True/False, "reason"` immediately followed by `check("human-readable description", _x)`. Never write a bare `assert`.

### `EXPECTED_CHECK_COUNT` re-derivation
**Source:** `companion/test_companion_app.py:5457` (`return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1`) and the append-only historical trail of `EXPECTED_CHECK_COUNT = N` reassignments at lines 77-269 in the same file.
**Apply to:** every one of the 6 harnesses. After editing a file's checks, run `server/.venv/bin/python3 <path/to/test_file>.py`, read the printed `N/M checks pass` line, and set the file's **last** `EXPECTED_CHECK_COUNT = M` assignment (append a new one with a comment citing this phase/plan — never edit an old comment's narration in place, never compute M by arithmetic on old comments).

### Duplicated-not-imported static-route contract
**Source:** `companion/app.py:110-135` (route+path constants), `companion/layout.py:113-146` (mirrored `*_SCRIPT_SRC` constants + `page_shell()`'s script-tag tuple), `companion/test_companion_app.py:2567-2591` (the cross-file equality test).
**Apply to:** `companion/static/poll-cooldown.js` (new) — six mechanical touch points, enumerated in full under D-18c above. `companion/app.py` cannot import `companion/layout.py`'s constant (would-be import cycle; `layout.py` imports nothing from `app.py`), so the route string is retyped in both files and pinned equal by a dedicated test — never attempt to collapse this into a single shared constant module, that is a deliberate, tested, existing design choice, not an oversight.

### `_render_login_page()` / `_handle_login_post()` 200-on-failure precedent
**Source:** `companion/app.py:1246-1249, 2000-2020`.
**Apply to:** D-07's `_handle_settings_post()` failure branch (render 200 with errors/submitted instead of redirecting with a flash key) — this is the ONLY existing precedent in the codebase for "render the same page at a non-303 status instead of redirecting," and D-07's own text names it explicitly.

### Signature-widening over return-type change
**Source:** `companion/pages/config_page.py:1617` (`render`), `:1888` (`handle_post`) — 46 and 75 pinned call sites respectively (RESEARCH.md Pitfall 6, confirmed).
**Apply to:** any function in this phase with more than a handful of existing callers (`config_page.render()`/`handle_post()` above all others, but also `screens.current_screen_id(ctx)` for D-23, already built to accept an optional `ctx` with a `.get()` fallback). Add new parameters as fully-defaulted keywords placed last; never change a return type; never make an existing positional parameter's meaning conditional on a new one's presence.

### ES5-safe / no-HTML-writing-sink discipline for every static `.js` file
**Source:** header comments in `companion/static/copy-button.js:1-26`, `companion/static/dirty-state.js:1-39`, `companion/static/freshness.js:1-100`; enforced by `companion/test_companion_app.py:2600-2626` (`_panel_lookup_script_es5_safe_and_no_html_write`, the token-ban list: `let `, `const `, `=>`, `` ` ``, `fetch(`, `XMLHttpRequest`, `setTimeout`, `setInterval`, `innerHTML`, `document.write`, `eval(`).
**Apply to:** `poll-cooldown.js` (new) and every edit to `freshness.js`, `dirty-state.js`, `copy-button.js`. Note `freshness.js`'s D-02 rewrite is the one deliberate, reviewed exception this phase introduces to the `fetch`/timer bans (RESEARCH.md Pitfall 5) — if the fetch-and-swap implementation needs `fetch(...)`/`setTimeout`/an HTML-writing sink, get it reviewed against `_FORBIDDEN_SCRIPT_SINKS`-style guards explicitly rather than silently exempting the file; `setInterval`/`window.location.reload()` are already used by the *current* `freshness.js` and already pass every existing guard (confirmed: those guards are scoped to `nav-dropdown.js`/`panel-lookup.js`/`flash-cleanup.js` by name, not to `freshness.js`).

### Universal escaping choke point
**Source:** every page module's own docstring (e.g. `companion/pages/history_page.py:539-553`'s `_copy_button_html()` comment: "escaped once here... built only from the same already-escaped row values"); the single function is `companion.layout.escape_html`.
**Apply to:** every new dynamic markup builder this phase adds — the field-level error `<p class="field-error">` spans (D-07), the screen-selector `<select>` (D-23), the calendar-disconnect confirm page (D-08), the "Unidentified airlines" strip heading (D-21) — route every interpolated value through `escape_html()` with zero exceptions.

## No Analog Found

None. Every file in this phase's scope lands inside an existing, already-precedented module or an existing sibling static asset; the two genuinely new files (`companion/battery.py`, `companion/static/poll-cooldown.js`) are both verbatim extractions/externalizations of code that already exists elsewhere in the codebase today (see their sections above).

## Critical Cross-Cutting Warning for the Planner

**D-12's `<fieldset>`/`<legend>` wording, read literally, breaks 4 pinned tests** (`companion/test_config_page.py:457-458, 612-613, 855-856, 2825-2826`, each asserting zero `<fieldset>` elements anywhere on the rendered Settings page, following a documented earlier decision to remove them). D-12's own text offers the compatible alternative (`role="radiogroup"` + `aria-labelledby`) — the plan for D-12 must use that path, not the `<fieldset>` path, or must explicitly retarget all four pinned checks with the plan author's eyes open to why they existed. This is the single highest-risk "looks simple, isn't" item in the phase beyond what RESEARCH.md's own Pitfall 2 (CSP vs. inline styles, already resolved by the orchestrator) and Pitfall 6 (D-07 signature widening) already flagged.

## Metadata

**Analog search scope:** `companion/`, `companion/pages/`, `companion/static/`, `server/device_config.py`, `server/test_config_history.py`, `server/test_runway_config.py`, `deploy/skypane.env.example`
**Files scanned (Read/Grep):** `companion/auth.py` (full), `companion/screens.py` (full), `companion/app.py` (targeted: routing table, hardening headers, redirect, login page/handler, do_POST, static-script serving family, settings-post handler), `companion/layout.py` (targeted: script constants, `page_shell()`, `local_clock_text()`, `stat_tile()`), `companion/pages/health_page.py` (targeted: constants, `battery_status()`, `corroboration_status()`, `overall_severity()`, `_CORROBORATION_ROWS`), `companion/pages/home_page.py` (targeted: `battery_percent()`, state-text dicts, tile assembly), `companion/pages/config_page.py` (targeted: `render()`, `submitted_calendar_signal()`, `handle_post()` docstring, `_poll_cooldown_script()`/`_poll_submit_script()`, `_theme_chip_grid_html()`, calendar disconnect checkbox, `quiet_hours_group()`), `companion/pages/history_page.py` (targeted: `_HEADERS`, `_copy_button_html()`), `companion/pages/airlines_page.py` (targeted: back link, gap-card/gallery call sites), `server/device_config.py` (targeted: `RUNWAYS`, `runway_label()`), `companion/static/copy-button.js` (full), `companion/static/dirty-state.js` (full), `companion/static/freshness.js` (partial, header/rationale), `companion/test_companion_app.py` (targeted: `check()`, static-script test family, login-throttle test, session-cookie test), `server/test_config_history.py` (targeted: `check()`/`EXPECTED_CHECK_COUNT` locations), `deploy/skypane.env.example` (full), plus `companion/test_config_page.py`'s `<fieldset>`-zero pinned-check grep.
**Pattern extraction date:** 2026-09-11
