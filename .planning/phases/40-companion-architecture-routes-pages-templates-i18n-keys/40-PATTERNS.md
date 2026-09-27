# Phase 40: Companion architecture — Pattern Map

**Mapped:** 2026-09-27
**Files analyzed:** 19 (9 CMP structural changes + 3 CFG feature changes, several touching
multiple existing files, plus ~8 new test/helper files)
**Analogs found:** 16 / 19 (3 are pure extractions with no closer analog than the code being
extracted itself — noted in "No Analog Found")

This phase is almost entirely **refactor-in-place**: nearly every "new" file is a split or
extraction from an existing file that already IS the best analog for its own successor. Where
that is true, the table below still names the current file as the analog because the extracted
function/class bodies must move verbatim (or near-verbatim) — the "pattern" to copy is the
existing code's own shape, not a foreign one.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `companion/routes.py` (new — CMP-01 route table) | route/config | request-response | `companion/app.py` `_dispatch_get()`/`_dispatch_post()` (lines 2281-2629, 2643-2849) | exact (extraction source) |
| `companion/app.py` `do_GET`/`do_POST` (modified — dispatch via table) | controller | request-response | same file, current `do_GET()`/`do_POST()` (lines 2270-2280, 2631-2643) | exact (in-place) |
| static allowlist module/dict (new or in `routes.py` — CMP-02) | config | file-I/O | `companion/app.py` static-route constants (96-118, 423-440) + `_serve_*` delegates (1774-1827) + `_serve_static()`/`_static_entry()`/`_not_modified()` (450-517, 1724-1772) | exact (extraction source) |
| `companion/pages/config_page.py` split by settings group (CMP-03) | page/controller | request-response, CRUD | current `config_page.py` itself — `render()` (2773-2957), `handle_post()` (3190-3356), `_calendar_connection_html()` (2268-2320+), `_aspect_card_html()` (1018+) as the group boundaries to split along | exact (in-place split) |
| `companion/layout.py` split by responsibility (CMP-03) | component/utility | request-response | current `layout.py` itself — `page_shell()` (1888-2073+), `frame_strip_html()` (2267+), `status_row()` (2435-2460), `relative_time_html()` (1032+) as candidate responsibility clusters | exact (in-place split) |
| typed per-page context module (new — CMP-04, successor to `_LazyContext`) | model/provider | CRUD (SQLite + JSON reads) | `companion/app.py` `_LazyContext` class (1159-1204) + `page_context()` (1427+) + its lazy loaders `_lazy_health_state`/`_lazy_health_severity`/`_safe_poll_cooldown_remaining` (899-969) | exact (extraction source) |
| template helper for `page_shell()` (CMP-05, named templates) | utility | transform | `companion/layout.py` `page_shell()`'s current `%`-positional skeleton (1888-2073+) and `SHELL_SCRIPT_ORDER`/`GLOBAL_PAGE_SCRIPTS` validation (1858-1925) | exact (in-place) |
| shared body-drain helper (new — CMP-07) | utility | file-I/O (request body) | `companion/app.py` `read_form()` (1367-1398) and `_read_upload_body()` (1400-1425) — near-identical drain loops to merge | exact (extraction source) |
| shared cookie-builder helper (new — CMP-07) | utility | transform | `companion/app.py` `_handle_theme_post()` (2603-2614) and `_handle_lang_post()` (2616-2629) — identical `Set-Cookie` format string to merge | exact (extraction source) |
| `companion/static/style.css` dedup (CMP-08) | config/style | transform | the file itself — token block header (`companion/static/style.css:1-40`) is the canonical token source; `.preview-frame__image` (lines 176, 3970, 4181, 4186, 4197) is the fragmented selector to merge; the stray `background: #ffffff` (line ~3978, inside the 3970 block) is the literal to token-ize | exact (in-place) |
| i18n stable-ID catalog (CMP-09) | i18n module | transform | `companion/i18n.py` (`t()`/`t_lang()`, full file, 29 lines) + `companion/i18n_fr/__init__.py` (`CATALOG` merge-by-`pkgutil`, full file, 34 lines) + one sibling module for shape, `companion/i18n_fr/health.py` (English-keyed `CATALOG` dict, lines 18-40+) | role-match (mechanism must be preserved, key scheme changes) |
| `companion/draw.py` battery chart primitives (CFG-39) | utility/drawing | transform (SVG emission) | `companion/draw.py` `percent_y()` (research-quoted, ~line 556) + `rect()`/`line()`/`circle()`/`path()`/`percent_canvas()`/`label_span()`/`title()` (369-418, 269) — the four other drawings' emitter vocabulary | exact |
| `companion/pages/health_page.py` `battery_sparkline_svg()` call site (CFG-39) | page/component | transform | same file, `sparkline_point_y()` (628-639) — mathematically identical to `draw.percent_y()`, to be replaced by a call to it | exact (in-place) |
| `companion/pages/history_page.py` "When" cell (CFG-34a) | page/component | transform | `companion/pages/home_page.py` `_recent_flight_time_html()` (433-463) — the already-shipped build-and-concatenate live-age pattern | exact (cross-file behavioural analog) |
| `companion/pages/config_page.py` `_calendar_connection_html()` (CFG-34b) | page/component | transform | same as above (`home_page._recent_flight_time_html()`) for the restructuring shape; `status_row()` (`layout.py:2435-2460`) for the escaping trap being worked around | exact (cross-file behavioural analog) |
| `companion/pages/health_page.py` `_registry_seen_cell_html()` (CFG-34c) | page/component | transform | `home_page._recent_flight_time_html()` (462) — direct `layout.relative_time_html()` call, simplest of the three sites (no shared-helper escaping trap) | exact |
| `companion/pages/airlines_page.py` keyboard test (CFG-52) | test (browser) | event-driven | `companion/test_browser_ux_helpers.py` `_operate_with_keyboard()` (819-873) + `_upload_drop_html()` (357-391+, the control under test) | exact |
| `companion/structure_metrics.py` (new, non-`test_`-prefixed helper — CMP-03/06) | utility (test-support) | transform (AST measurement) | no direct analog exists yet — closest shape is `test-support/companion_markup.py`'s existing parser-based measurement approach (CSS rules) and `test_suite_guards.py`'s own `_Scanner(ast.NodeVisitor)` (183+) for the AST-walking style, kept OUT of any `test_`-prefixed file | role-match (pattern for "measure via AST in a non-scanned module") |
| `companion/test_route_table.py` (new — CMP-01 coverage test) | test (integration) | request-response | `companion/test_companion_app_02.py::test_draw_module_imports_no_page_and_no_server()` (1149-1171) — subprocess + `sys.modules`/runtime-object introspection, never source text | exact (the mandated shape) |
| `companion/test_i18n.py` extension (CMP-09 completeness) | test (unit) | transform | `companion/i18n_fr/__init__.py`'s own `_build_catalog()` (16-31) — assert against the runtime `CATALOG` dict and a new stable-ID registry, never grep source | exact |

## Pattern Assignments

### `companion/routes.py` (new, CMP-01 route table)

**Analog:** `companion/app.py` `_dispatch_get()`/`_dispatch_post()`

**Current dispatch shape to replace** (`companion/app.py:2281-2360`, GET side):
```python
def do_GET(self):
    """One `history_db.connection_scope()` for the whole request..."""
    with history_db.connection_scope(self.args.state_dir):
        return self._dispatch_get()

def _dispatch_get(self):
    parsed = urlsplit(self.path)
    path = parsed.path

    if path == LOGIN_ROUTE:
        if self._is_authenticated():
            return self.redirect(HOME_ROUTE)
        next_route = _validated_next_route(
            parse_qs(parsed.query).get("next", [None])[0])
        return self.send_html(200, self._render_login_page(next_route=next_route))

    if path == STYLE_ROUTE:
        return self._serve_stylesheet()

    # Pre-auth, matching /static/style.css: a static asset carries no
    # per-user or sensitive data, so gating it would add a session
    # round-trip for zero benefit. Every other *_SCRIPT_ROUTE branch
    # below shares this same reasoning.
    if path == SCRIPT_ROUTE:
        return self._serve_battery_trend_script()
    # ... 16 more identical *_SCRIPT_ROUTE branches, all public ...

    # The six live tabs, each through _render_tab() above.
    if path == HOME_ROUTE:
        return self._render_tab(HOME_ROUTE, home_page.render)
```

**POST side, gate-then-dispatch shape to replace** (`companion/app.py:2643-2718`):
```python
def _dispatch_post(self):
    if not auth.post_origin_ok(self.headers):
        return self.send_html(403, self._forbidden_page())

    parsed = urlsplit(self.path)
    path = parsed.path

    if path == LOGIN_ROUTE:
        return self._handle_login_post()

    if path == SETTINGS_ROUTE:
        if not self.require_session():
            return None
        return self._handle_settings_post()
    # ... repeated ~15 times, always `if not self.require_session(): return None`
    #     immediately before the real handler call ...

    if path.startswith(airlines_page.MANUAL_DELETE_ROUTE_PREFIX) and path.endswith(
            airlines_page.MANUAL_DELETE_ROUTE_SUFFIX):
        if not self.require_session():
            return None
        key = path[
            len(airlines_page.MANUAL_DELETE_ROUTE_PREFIX):
            -len(airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)]
```

**What the route table must reproduce exactly:**
- `_dispatch_post()`'s `auth.post_origin_ok(self.headers)` check stays the FIRST statement,
  run before any table lookup — it is not a per-route concern (see `companion/app.py:2640-2645`'s
  own comment: "Runs as the first statement... so it covers every route uniformly").
- `do_GET`/`do_POST`'s `history_db.connection_scope(self.args.state_dir)` wrapper stays exactly
  where it is (`companion/app.py:2270-2279`, `2631-2638`) — one connection per request,
  opened around the whole dispatch, not per-route.
- Every `if not self.require_session(): return None` becomes the table's `auth_required=True`
  field; `require_session()` itself (`companion/app.py:1325-1340`) is unchanged.
- Prefix/suffix routes (7 of them — `GALLERY_ROUTE_PREFIX`, `RUNWAY_IMAGE_ROUTE_PREFIX`,
  `ILLUSTRATION_IMAGE_ROUTE_PREFIX`, `THEME_PREVIEW_ROUTE_PREFIX`,
  `airlines_page.MANUAL_DELETE_ROUTE_PREFIX`/`_SUFFIX`, `RULES_DELETE_ROUTE_PREFIX`/`_SUFFIX`)
  need a `(prefix, suffix)` matcher variant, not a second matcher primitive — `RULES_DELETE_ROUTE`
  additionally splits its captured middle segment on `/` once inside its own thin handler wrapper.
- **Public allowlist is exactly:** `LOGIN_ROUTE` (GET+POST) + the 18 static routes (GET only,
  `STYLE_ROUTE` + 17 `*_SCRIPT_ROUTE`). Nothing else. There is no dedicated health-probe route
  today (verified: `/health` is the authenticated Health tab).

---

### static allowlist (CMP-02)

**Analog:** `companion/app.py` static-route constants + `_serve_*` delegates + cache mechanism

**Route constant + path constant + delegate pattern to collapse** (`companion/app.py:96-118`,
`423-440`, `1774-1827`):
```python
SCRIPT_ROUTE = "/static/battery-trend.js"
# ...
_BATTERY_TREND_JS_PATH = os.path.join(_HERE, "static", "battery-trend.js")
# ...
def _serve_battery_trend_script(self):
    return self._serve_script_file(_BATTERY_TREND_JS_PATH)
```

**Cache mechanism to preserve byte-for-byte** (`companion/app.py:450-517`):
```python
_StaticEntry = collections.namedtuple(
    "_StaticEntry", "payload etag last_modified mtime_s")
_STATIC_CACHE = {}
_STATIC_CACHE_LOCK = threading.Lock()

def _static_entry(abs_path):
    """The cached `_StaticEntry` for `abs_path`, reading the file at most
    once per process. Raises the underlying `OSError` (never caught
    here) when the file is missing or unreadable; the caller maps that
    to a 404.
    """
    with _STATIC_CACHE_LOCK:
        entry = _STATIC_CACHE.get(abs_path)
    if entry is not None:
        return entry
    payload = _read_static_bytes(abs_path)
    mtime_s = int(os.stat(abs_path).st_mtime)
    etag = '"%s"' % hashlib.sha256(payload).hexdigest()[:32]
    last_modified = email.utils.formatdate(mtime_s, usegmt=True)
    entry = _StaticEntry(payload, etag, last_modified, mtime_s)
    with _STATIC_CACHE_LOCK:
        _STATIC_CACHE[abs_path] = entry
    return entry

def _not_modified(headers, etag, mtime_s):
    """RFC 9110 13.2.2 evaluation order: If-None-Match decides outright
    when present; If-Modified-Since is consulted only in its absence."""
    match = _if_none_match_matches(headers, etag)
    if match is not None:
        return match
    ims = headers.get("If-Modified-Since")
    if not ims:
        return False
    try:
        return mtime_s <= email.utils.parsedate_to_datetime(ims).timestamp()
    except (TypeError, ValueError, OverflowError, IndexError):
        return False
```

**Do NOT fold into this allowlist:** `_serve_gallery_image()`, `_serve_illustration_image()`,
`_serve_theme_preview_image()` (`companion/app.py:1829+`) — session-gated, membership-tested
against a per-request set, and theme-preview has a live `?live=1` branch. These stay their own
route-table entries with `auth_required=True`, not `{route: path}` entries.

---

### typed per-page context (CMP-04)

**Analog:** `companion/app.py` `_LazyContext` + `page_context()`

**The mechanism to preserve exactly** (`companion/app.py:1159-1204`):
```python
class _LazyContext(dict):
    def __init__(self, values, loaders):
        super().__init__(values)
        self._loaders = dict(loaders)

    def __getitem__(self, key):
        if key in self._loaders:
            # Popped only AFTER loader() returns - a loader that raises
            # must leave its key exactly as it found it (still lazy, not
            # half-resolved), so a second read retries the loader instead
            # of falling through to dict.__getitem__() and raising KeyError.
            value = self._loaders[key]()
            del self._loaders[key]
            dict.__setitem__(self, key, value)
            return value
        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        if key in self._loaders:
            return self[key]
        return dict.get(self, key, default)

    def __contains__(self, key):
        return key in self._loaders or dict.__contains__(self, key)
```

**Shared-loader pattern to reproduce** (`companion/app.py:953-970`, `health_severity` reusing
`health_state`'s already-resolved value without recomputing):
```python
def _lazy_health_severity(ctx):
    if dict.__contains__(ctx, "health_state"):
        health_state = dict.__getitem__(ctx, "health_state")
        return health_state["severity"] if health_state else "ok"
    signals = ctx["_health_signals"]
    return signals["severity"] if signals is not None else "ok"
```

**Fail-closed degrade pattern for a page-render-only value** (`companion/app.py:917-931`):
```python
def _safe_poll_cooldown_remaining(state_dir):
    try:
        return poll_cooldown_remaining(state_dir)
    except (sqlite3.Error, OSError):
        return 0
```

A typed successor (dataclass or similar) must reproduce these three shapes: lazy-resolve-once
per field, an explicit shared-internal-key equivalent (e.g. two `@cached_property`s that public
fields both delegate to, mirroring `_health_signals`/`_calendar_registry`), and the same
fail-closed-to-a-decorative-default contract on page-render-only reads. The exact 15 eager +
13 lazy keys are documented in full in `companion/pages/__init__.py`'s own contract docstring
(read there for field-by-field description) — this is the authoritative shape to type.

---

### named templates for `page_shell()` (CMP-05)

**Analog:** `companion/layout.py` `page_shell()` (1888-2073+), current shape

**Signature and validation to preserve** (`companion/layout.py:1888-1925`):
```python
def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=None, lang=None, device_config=None, scripts=(),
        refresh_token=None):
    unknown_scripts = set(scripts) - set(SHELL_SCRIPT_ORDER)
    if unknown_scripts:
        raise ValueError(
            "page_shell(): scripts=%r is not in SHELL_SCRIPT_ORDER"
            % (sorted(unknown_scripts),))
    wanted_scripts = set(GLOBAL_PAGE_SCRIPTS) | set(scripts)
    script_tags_html = "".join(
        '<script src="%s" defer></script>\n' % src
        for src in SHELL_SCRIPT_ORDER if src in wanted_scripts)
```

No literal `$`/`{`/`}` was found anywhere in the skeleton (verified by reading the full
function), so both `str.format_map()` and `string.Template` are viable; `str.format_map()`
needs no escaping discipline for substituted values that themselves contain `{`/`}` (only the
template string is parsed for placeholders), which is the lower-friction choice per RESEARCH.md.
The `ValueError` raise above (a fail-fast contract on an unknown script src) must survive the
migration unchanged.

---

### shared body-drain helper (CMP-07)

**Analog:** `companion/app.py` `read_form()` / `_read_upload_body()`

**The two near-identical loops to merge** (`companion/app.py:1367-1425`):
```python
def read_form(self):
    try:
        length = int(self.headers.get("Content-Length", "0"))
    except ValueError:
        length = 0
    if length <= 0:
        return {}
    try:
        raw = self.rfile.read(min(length, MAX_FORM_BYTES + 1))
        if length > MAX_FORM_BYTES:
            remaining = length - len(raw)
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)
            return {}
    except socket.timeout:
        return {}
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    parsed = parse_qs(text, keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items() if values}

def _read_upload_body(self):
    try:
        length = int(self.headers.get("Content-Length", "0"))
    except (TypeError, ValueError):
        return None
    if length <= 0:
        return None
    try:
        raw = self.rfile.read(min(length, MAX_ILLUSTRATION_UPLOAD_BYTES + 1))
        if length > MAX_ILLUSTRATION_UPLOAD_BYTES:
            remaining = length - len(raw)
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)
            return None
    except socket.timeout:
        return None
    return raw
```

Extract a `_drain_capped_body(cap)` returning `(raw_bytes_or_None, truncated: bool)` (or
equivalent); each caller keeps its own degrade-value contract (`{}` vs `None`) and its own
decode/parse step on top.

---

### shared cookie-builder helper (CMP-07)

**Analog:** `companion/app.py` `_handle_theme_post()` / `_handle_lang_post()`

**The identical format string to merge** (`companion/app.py:2603-2629`):
```python
def _handle_theme_post(self):
    form = self.read_form()
    submitted = form.get("ui_theme")
    cookie_header = None
    if submitted in layout.UI_THEME_CHOICES:
        cookie_header = (
            "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
            % (auth.UI_THEME_COOKIE_NAME, submitted, auth.secure_cookie_flag(),
               THEME_COOKIE_MAX_AGE_S))
    return self.redirect(self._referring_tab(), set_cookie=cookie_header)

def _handle_lang_post(self):
    """POST /ui-lang — byte-for-byte sibling of _handle_theme_post() above."""
    form = self.read_form()
    submitted = form.get("ui_lang")
    cookie_header = None
    if submitted in prefs.LANG_CHOICES:
        cookie_header = (
            "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
            % (auth.UI_LANG_COOKIE_NAME, submitted, auth.secure_cookie_flag(),
               LANG_COOKIE_MAX_AGE_S))
    return self.redirect(self._referring_tab(), set_cookie=cookie_header)
```

Extract `_choice_cookie_header(name, value, choices, max_age_s)`; both call sites then differ
only by cookie name/choices/max-age constant and which form field they read.

---

### CSS token dedup (CMP-08)

**Analog:** `companion/static/style.css`'s own `:root` token block

**Token block to extend from** (`companion/static/style.css:16-40`):
```css
:root {
  /* Spacing scale, multiples of 4. */
  --space-xs: 4px;
  --space-sm: 8px;
  /* ... */
  --font-label-size: 14px;
  --font-body-size: 16px;
  /* ... */
}
```

**Stray literal to tokenize** — `background: #ffffff` inside the `.preview-frame__image,
img.recent-flight__thumb, img.history-card__thumb` rule block (`companion/static/style.css`,
grep-confirmed at the block starting line 3970):
```css
.preview-frame__image,
img.recent-flight__thumb,
img.history-card__thumb {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  background: #ffffff;
}
```

**Fragmented selector to merge** — `.preview-frame__image` is declared as a top-level rule (not
inside `@media`/`@keyframes`) at four separate line numbers: 176, 3970 (in the block above),
4181, and again at 4186 inside a further grouped selector; 4197 is inside a `@media` override
and is a legitimate responsive re-declaration, not duplication. Re-verify the authoritative,
non-noisy list via `test-support/companion_markup.py`'s own `css_rules()`/`rules_with_selector()`
parser before finalizing scope (RESEARCH.md Assumption A2) — a naive text scan over-counts.

---

### i18n stable-ID catalog (CMP-09)

**Analog:** `companion/i18n.py` + `companion/i18n_fr/__init__.py` (mechanism), one sibling
module for the current English-keyed shape

**Current lookup mechanism to preserve** (`companion/i18n.py`, full file):
```python
import companion.i18n_fr as i18n_fr
import companion.prefs as prefs

def t(text):
    if prefs.current_lang() == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text

def t_lang(text, lang):
    if lang == "fr":
        return i18n_fr.CATALOG.get(text, text)
    return text
```

**Current merge-at-import-time mechanism to preserve** (`companion/i18n_fr/__init__.py`,
full file):
```python
def _build_catalog():
    catalog = {}
    for module_info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(
            "%s.%s" % (__name__, module_info.name))
        module_catalog = getattr(module, "CATALOG", None)
        if not isinstance(module_catalog, dict):
            continue
        for key, value in module_catalog.items():
            if key in catalog:
                raise ValueError(
                    "companion.i18n_fr: duplicate catalogue key %r found "
                    "in %s..." % (key, module.__name__))
            catalog[key] = value
    return catalog

CATALOG = _build_catalog()
```

**Current English-keyed shape to migrate off of** (`companion/i18n_fr/health.py:18-23`):
```python
CATALOG = {
    "just now": "à l'instant",
    "%s ago": "il y a %s",
    "in a moment": "dans un instant",
    "in %s": "dans %s",
}
```

A stable-ID migration keeps the `pkgutil`-merge/duplicate-detection mechanism and the
`t()`/`t_lang()` signatures unchanged; only the dict key changes from "the literal English
sentence" to a stable message ID, with the English source string moving to its own value
position (e.g. a per-key `{id: {"en": ..., "fr": ...}}` shape, or a separate `EN_CATALOG`
mirroring `i18n_fr.CATALOG`'s structure — Claude's Discretion per CONTEXT.md). The completeness
test must assert against the runtime dict, never grep `.py` source for `i18n.t("...")` literals
(this project's own G2/G3 convention, see below).

---

### CFG-39: battery chart onto `draw.py`

**Analog:** `companion/draw.py` `percent_y()` (the scale) and its primitive emitters

**The identical formula already in `draw.py`** (RESEARCH.md, quoted from `companion/draw.py`):
```python
def percent_y(value, domain_min, domain_max, inset_percent=0.0):
    if not is_number(value) or not is_number(domain_min) or not is_number(domain_max):
        return 0.0
    if not is_number(inset_percent):
        inset_percent = 0.0
    span = domain_max - domain_min
    if span == 0:
        return inset_percent
    clamped = max(domain_min, min(domain_max, value))
    return inset_percent + (
        1 - (clamped - domain_min) / span
    ) * (100 - 2 * inset_percent)
```

**The chart's own current formula to replace** (`companion/pages/health_page.py:628-639`):
```python
def sparkline_point_y(value):
    inset = _SPARKLINE_VERTICAL_INSET_PERCENT
    clamped = max(SPARKLINE_Y_MIN_MV, min(SPARKLINE_Y_MAX_MV, value))
    return inset + (
        1 - (clamped - SPARKLINE_Y_MIN_MV) / _SPARKLINE_Y_SPAN_MV
    ) * (100 - 2 * inset)
```
This is exactly `draw.percent_y(value, SPARKLINE_Y_MIN_MV, SPARKLINE_Y_MAX_MV,
_SPARKLINE_VERTICAL_INSET_PERCENT)` — `health_page.py` already does `import companion.draw as
draw` (line 23), so migrating costs no new import.

**Primitive vocabulary to build axis/tick chrome from** (`companion/draw.py:369-418`, since
`draw.label_grid()` was deleted in Phase 35): `rect()`, `line()`, `circle()`, `path()`,
`percent_canvas()` (269), `label_span()` (418), `title()` (410) — the same set the existing
chart-contract test samples already exercise (`companion/test_companion_app_02.py:1100-1108`):
```python
_DRAWING_CONTRACT_SAMPLES = (
    lambda: draw.rect(draw.DRAWING_AXIS_CLASS, 0, "100%", 1, 4),
    lambda: draw.line(draw.DRAWING_LINE_CLASS, "0.00%", "1.00%", "2.00%", "3.00%"),
    lambda: draw.circle(draw.DRAWING_MARK_CLASS, "50.00%", "50.00%", 3),
    lambda: draw.path(draw.DRAWING_LINE_CLASS, "M0 0 L10 10", attrs={"fill": "none"}),
    lambda: draw.percent_canvas(draw.DRAWING_CANVAS_CLASS, "", label="chart"),
    lambda: draw.unit_canvas(draw.DRAWING_FIGURE_CLASS, "", 48, 48, hidden=True),
    lambda: draw.ring_gauge(0.5, 72),
)
```
Add `battery_sparkline_svg()`'s own emitted samples to this tuple once it routes through
`draw.py`'s primitives — this is the same test the CSS-class-resolves and
no-colour-literal/no-script/escapes-every-value guards already run against.

---

### CFG-34: three live-age conversions

**Analog (the pattern to copy):** `companion/pages/home_page.py` `_recent_flight_time_html()`
— the already-shipped build-and-concatenate shape

```python
# companion/pages/home_page.py:433-463
def _recent_flight_time_html(ts, now):
    """...Does not use `layout.concise_timestamp_html()`, which bundles the
    clock and the relative age into one already-escaped `<span
    class="mono">` — the single-element shape this cell exists to avoid.
    The clock and the age are built and escaped separately instead...
    """
    if not ts:
        return escape_html(i18n.t(_TIME_CELL_FALLBACK_TEXT))
    parsed = layout.parse_iso(ts)
    if parsed is None:
        return '<span class="time-value">%s</span>' % escape_html(ts)
    clock_text = layout.local_clock_text(parsed, now_parsed=layout.parse_iso(now))
    cell_html = '<span class="time-value">%s</span>' % escape_html(clock_text)
    age = layout.age_seconds(ts, now)
    if age is not None:
        cell_html += (
            '<span class="cell-inline-sep">·</span>'
            '<span class="time-value__age">(%s)</span>'
        ) % layout.relative_time_html(ts, now)
    return cell_html
```

`layout.relative_time_html()`'s contract (`companion/layout.py:1032+`, quoted in RESEARCH.md):
returns already-escaped `<time datetime="..." data-relative>...</time>` markup — every caller
"interpolates the return value verbatim, never re-escaping it."

**Site 1 — Flights "When" cell**, `companion/pages/history_page.py:723-745`:
```python
def _when_cell_html(raw_ts, now):
    if not raw_ts:
        html = _merged_cell(i18n.t(_CLOCK_CELL_FALLBACK), "")
    else:
        parsed = layout.parse_iso(raw_ts)
        if parsed is None:
            html = _merged_cell(raw_ts, "")
        else:
            now_parsed = layout.parse_iso(now)
            clock_text = layout.local_clock_text(parsed, now_parsed)
            age = layout.age_seconds(raw_ts, now)
            secondary = layout.relative_age_text(age) if age is not None else ""
            html = _merged_cell(clock_text, secondary)   # <-- goes through _merged_cell()
    return html
```
`_merged_cell()` (`history_page.py:517-532`) `escape_html()`s `secondary` unconditionally —
passing `relative_time_html()`'s pre-escaped markup through it double-escapes the `<time>` tag.
**Fix, following the `home_page.py` analog:** bypass `_merged_cell()` at this one call site;
build `'<td><span class="%s">%s</span>%s</td>'`-shaped markup inline, escaping the primary half
and splicing `relative_time_html()`'s pre-escaped half in unescaped, matching
`_recent_flight_time_html()`'s own inline-concatenation shape.

**Site 2 — Calendar "refreshed Xm ago"**, `companion/pages/config_page.py:2294-2315`:
```python
if entry_count == 1:
    detail = i18n.t(CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE) % (
        layout.relative_age_text(age),)
else:
    detail = i18n.t(CALENDAR_STATUS_DETAIL_TEMPLATE) % (
        entry_count, layout.relative_age_text(age))
    state = "ok"
# ...
status_html = layout.status_row("", verdict, detail, state)   # <-- goes through status_row()
```
`status_row()` (`companion/layout.py:2435-2460`) `escape_html()`s `detail` unconditionally
(own docstring: "verdict/detail/label are escaped here"). Same double-escaping trap. **Fix:**
same bypass-the-helper approach — build the calendar row's markup inline at this call site
rather than widening `status_row()`'s contract for one caller (RESEARCH.md Open Question 2's
recommendation).

**Site 3 — Health unresolved-prefix cells**, `companion/pages/health_page.py:1941-1966`
(simplest of the three — no shared escaping helper in the way):
```python
def _registry_seen_cell_html(raw_ts, now):
    if not raw_ts:
        return ""
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return '<span class="cell-primary">%s</span>' % escape_html(raw_ts)
    clock_text = layout.local_clock_text(parsed, layout.parse_iso(now))
    age = layout.age_seconds(raw_ts, now)
    html = '<span class="cell-primary" title="%s">%s</span>' % (
        escape_html(_full_local_timestamp_text(raw_ts)), escape_html(clock_text))
    if age is not None:
        html += (
            '<span class="cell-inline-sep">%s</span>'
            '<span class="cell-secondary">%s</span>'
        ) % (
            escape_html(_REGISTRY_CELL_SEPARATOR_TEXT),
            escape_html(layout.relative_age_text(age)))   # <-- drop this escape_html() wrapper
    return html
```
**Fix:** drop the `escape_html()` wrapper around the age text and call
`layout.relative_time_html(raw_ts, now)` directly in its place — a straightforward swap, no
restructuring needed.

**The fourth age, left static by design:** `health_page.py:718` (`_battery_reading_parts()`'s
`when` text) feeds the sparkline's SVG `<title>` tooltip — no live DOM binding possible. Nothing
to change; CFG-34's job is to enumerate this exception, not convert it.

---

### CFG-52: artwork drop zone keyboard measurement

**Analog:** `companion/test_browser_ux_helpers.py` `_operate_with_keyboard()` (819-873) — the
instrument; `companion/pages/airlines_page.py` `_upload_drop_html()` (357-391+) — the control

```python
# companion/test_browser_ux_helpers.py:819-838 (the instrument's own contract)
def _operate_with_keyboard(page, selector, keys):
    """Drive a control with the keyboard alone and report what it did, having
    measured that not one pointer event fired while doing it... Focus is taken
    with `el.focus()`, never a click... Keys are pressed through `page.keyboard`,
    not dispatched as synthetic KeyboardEvents...
    """
    page.evaluate(_POINTER_RECORDER_ARM)
    focus = page.evaluate(_FOCUS_PROBE, {"selector": selector})
    if focus.get("error") == "no-element":
        raise AssertionError(...)
    if not focus["focused"]:
        raise AssertionError(...)
    for key in keys:
        page.keyboard.press(key)
    # ... reads back pointer-event count and asserts zero fired ...
```

This instrument **cannot** drive a native `<input type="file">`'s OS-level picker dialog (its
own docstring implicitly assumes a focusable DOM control whose state changes on keypress). The
new CFG-52 test needs its own recipe, not a call into `_operate_with_keyboard()`: focus the
input via `page.keyboard.press("Tab")` to the right position, open
`with page.expect_file_chooser() as fc_info:` then `page.keyboard.press("Enter")` on the focused
file input, set the chooser's file, then submit by pressing `"Enter"` on the focused submit
button (never `.click()`, matching the whole file's "prove the platform's native affordance"
convention). `_upload_drop_html()`'s markup (`airlines_page.py:357-391`) confirms the control's
actual id attribute (`UPLOAD_DROP_INPUT_ATTR`) to target.

**Existing (non-keyboard) test to extend or sit beside:**
`test_the_artwork_drop_zone_meets_its_floors_at_360px_in_both_themes` in
`companion/test_browser_ux_04.py` — measures hit-area/theme-paint/aspect-ratio only, no keyboard
assertion today.

---

### Structural guard tests (CMP-01/03/06/09) — the G2 escape hatch

**Analog:** `companion/test_companion_app_02.py::test_draw_module_imports_no_page_and_no_server()`
(1149-1171) — the project's own established shape for "introspect the running system, never
source text":
```python
def test_draw_module_imports_no_page_and_no_server():
    """...proven by importing it fresh in a subprocess and inspecting
    sys.modules, never by reading its source (guard G2 bans
    ast/tokenize introspection of production code)"""
    script = (
        "import json, sys\n"
        "import companion.draw\n"
        "banned = sorted(\n"
        "    m for m in sys.modules\n"
        "    if m == 'companion.layout' or m.startswith('companion.pages')\n"
        "    or m.startswith('server')\n"
        ")\n"
        "print(json.dumps(banned))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=child_env(), cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    banned = json.loads(result.stdout.strip().splitlines()[-1])
    assert banned == []
```

**The hard constraint this pattern works around** (`companion/test_suite_guards.py:1-57`):
```python
"""...inspects source with `inspect`/`ast`/`tokenize`/`linecache`..."""
import ast
# ...
def scanned_files():
    """Every `companion/test_*.py` module plus `companion/conftest.py`,
    minus this guard module..."""
    return sorted(
        os.path.join("companion", name)
        for name in os.listdir(_COMPANION_DIR)
        if name == "conftest.py" or (name.startswith("test_") and name.endswith(".py"))
        if os.path.join("companion", name) != _GUARD_MODULE
    )
_G2_MODULES = frozenset({"inspect", "ast", "tokenize", "linecache"})
```

**Applies to every new structural guard this phase adds:**
- `companion/test_route_table.py` (CMP-01 coverage) — enumerate the route table via its own
  Python object (imported from `routes.py`), issue real HTTP requests with no cookie, assert
  response codes/locations — no source-text scanning needed here at all, this one is naturally
  runtime-object-based.
- File-length/function-length guards (CMP-03/CMP-06) — the ONLY compliant shape is: put the
  `ast.parse()`-based measurement in a **non-`test_`-prefixed** helper module (e.g.
  `companion/structure_metrics.py`, invisible to `scanned_files()` since it doesn't start with
  `test_`), then a thin `companion/test_file_length_guard.py`/`test_function_length_guard.py`
  imports that helper and asserts on its return value.
- i18n completeness (CMP-09) — import `companion.i18n_fr.CATALOG` and the new stable-ID
  registry directly in the test, assert on the **runtime dict**, never grep `.py` source for
  `i18n.t("...")` call literals.

---

## Shared Patterns

### One-connection-per-request scope (preserve verbatim)
**Source:** `companion/app.py:2270-2279`, `2631-2638`
**Apply to:** the route-table's `do_GET`/`do_POST` entry points
```python
def do_GET(self):
    with history_db.connection_scope(self.args.state_dir):
        return self._dispatch_get()
```
The route table replaces what happens *inside* `_dispatch_get()`/`_dispatch_post()`; this outer
wrapper and the POST-only `auth.post_origin_ok()` pre-check stay exactly where they are.

### `require_session()` / session gate (unchanged, referenced by every gated route)
**Source:** `companion/app.py:1317-1340`
**Apply to:** every route table entry with `auth_required=True`
```python
def _is_authenticated(self):
    cookies = auth.parse_cookies(self.headers.get("Cookie"))
    token = cookies.get(auth.SESSION_COOKIE_NAME)
    return bool(token) and auth.verify_session_token(token) and not auth.is_revoked(token)

def require_session(self):
    if self._is_authenticated():
        return True
    requested_path = urlsplit(self.path).path
    next_route = _validated_next_route(requested_path)
    if next_route:
        self.redirect("%s?next=%s" % (LOGIN_ROUTE, quote(next_route, safe="")))
    else:
        self.redirect(LOGIN_ROUTE)
    return False
```

### `escape_html()` discipline — escape once, at the one place that builds the final string
**Source:** `companion/pages/history_page.py:517-532` (`_merged_cell()`), `companion/layout.py`
`status_row()` (2435-2460), `home_page.py`'s inline-concatenation pattern (433-463)
**Apply to:** every CFG-34 site, and any new markup builder — this project's standing rule is
"both arguments go through `escape_html()` here and nowhere else — do not pre-escape at the call
site too, or values would double-encode" (verbatim from `_merged_cell()`'s own docstring). The
CFG-34 fix follows the *other* half of the same rule: when a value is markup, not text (i.e.
`relative_time_html()`'s pre-escaped `<time>` element), it must never be passed through a helper
that unconditionally escapes.

### Page module isolation — no page imports another
**Source:** `companion/pages/__init__.py` (module docstring, e.g. its own note "each page module
duplicates the inline-compact convention rather than importing it" — see `history_page.py:96`,
`home_page.py` duplicating the pattern independently)
**Apply to:** any split of `config_page.py`/`layout.py`/`health_page.py` — shared helpers that
several page modules need go in `layout.py` (or a new shared module), never in one page module
imported by a sibling page module.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `companion/structure_metrics.py` (CMP-03/06 AST helper) | utility | transform | No existing non-`test_`-prefixed AST-measurement module exists in `companion/`; nearest shape is `test_suite_guards.py`'s own `_Scanner(ast.NodeVisitor)` class, which is itself a `test_`-prefixed module that the new helper must NOT resemble in placement (it must live outside the scanned set) |
| Rendered-HTML before/after equality harness (CMP-05 migration proof) | test (integration) | request-response | No existing "snapshot every page, assert byte-equality after a refactor" harness exists yet; nearest partial precedent is `test_companion_app_01.py::test_page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme`, which asserts shape, not a full byte-snapshot |
| CSS selector-dedup structural test (CMP-08) | test (structural) | transform | No existing test asserts "no selector is declared more than once outside `@media`"; must be built fresh on top of `test-support/companion_markup.py`'s `css_rules()` parser (an existing tool, not an existing test of this shape) |

## Metadata

**Analog search scope:** `companion/app.py`, `companion/layout.py`, `companion/draw.py`,
`companion/i18n.py`, `companion/i18n_fr/` (all 12 sibling modules), `companion/pages/*.py` (all
page modules), `companion/static/style.css`, `companion/test_suite_guards.py`,
`companion/test_browser_ux_helpers.py`, `companion/test_companion_app_02.py`,
`companion/test_browser_ux_04.py`
**Files scanned:** ~30 (direct reads) + grep sweeps across the full `companion/` tree
**Pattern extraction date:** 2026-09-27
