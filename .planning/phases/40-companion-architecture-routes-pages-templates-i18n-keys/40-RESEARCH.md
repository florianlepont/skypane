# Phase 40: Companion architecture — routes, pages, templates, i18n keys - Research

**Researched:** 2026-09-27
**Domain:** Structural refactor of a stdlib-only Python HTTP application (`companion/`) — route dispatch, static-file serving, per-request context, HTML templating, function/file decomposition, CSS deduplication, i18n key migration, plus three developer-confirmed feature additions (CFG-39, CFG-52, CFG-34).
**Confidence:** HIGH for everything measured directly against the live code (all Standard Stack / Architecture / most Pitfalls claims below); MEDIUM for the CSS-duplication exact count (regex-measured, needs the project's own parser to confirm); LOW/none for anything requiring a new external library (there is none — this phase adds no dependency).

## Summary

This phase is codebase archaeology, not new-technology research: the audit that spawned it
(`2026-09-23-code-audit.md`) has stale line numbers because Phases 32–38 already reshaped
`companion/app.py` (now 2849 lines), `companion/layout.py` (2597) and moved
`companion/pages/config_page.py` (3384). Every CMP-01..09 finding below was re-measured
directly against the current code in this session. The mechanisms Phase 38 built —
`history_db.connection_scope()` (one SQLite connection per request), `_LazyContext` (lazy,
memoize-once `page_context()`), `_PAGE_SCRIPTS` (per-page script sets, guarded by
`test_page_scripts.py`), the in-memory static-file cache with ETags/304, and the
`_page_freshness_token()` conditional-GET on the four refresh pages — are all still exactly
where Phase 38 left them, and every CMP-01..09 change must preserve them byte-for-byte.

The nine CMP items are a shape refactor with almost no behaviour change: a route table
replacing ~40 hand-repeated `if path == X: if not self.require_session(): ...` branches
across `_dispatch_get()`/`_dispatch_post()`; a `{route: (path, content_type, cache_control)}`
allowlist replacing 18 near-identical static-file constants/methods/branches (17 script
routes + the stylesheet route — three *other* image-serving routes, gallery/runway/
illustration/theme-preview, are NOT pure static-file lookups and do not belong in this
allowlist, see Pitfalls); a typed successor to `_LazyContext`'s 15 eager + 13 lazy keys;
named placeholders replacing `page_shell()`'s ~20-argument positional `%`-template; function
extraction on 12 production functions currently over 80 code lines (down from the audit's
stale 41 — most of that shrinkage is real prior cleanup, not measurement noise); one shared
body-drain helper behind `read_form()`/`_read_upload_body()`; one shared cookie-builder behind
the near-identical `_handle_theme_post()`/`_handle_lang_post()`; CSS deduplication (one real
stray hex literal found, `background: #ffffff` outside every token block, plus a handful of
selectors — `.preview-frame__image` chief among them — declared in 3-4 separate top-level
rule blocks); and a stable-message-ID migration of `companion/i18n_fr/`'s English-keyed
`CATALOG`.

The three feature items are smaller in code but each has a concrete, previously-undocumented
obstacle this research surfaced: CFG-39's battery chart migration onto `draw.py` is
mathematically a drop-in (`health_page.sparkline_point_y()` and `draw.percent_y()` are the
identical formula), but the audit's own suggested target (`draw.label_grid()`) no longer
exists — it was deleted as dead code in Phase 35 (HYG-05). CFG-52's artwork drop zone lives on
the **Airlines** page (`companion/pages/airlines_page.py`), not `config_page.py` as the task
brief assumed, and its control is a native `<input type="file">`, whose keyboard path was
already scoped and left unmeasured in Phase 25 with a concrete recipe recorded in
`REQUIREMENTS.md`'s CFG-52 row. CFG-34's three conversions are pinned to exact call sites, and
two of the three currently pass their text through a function that unconditionally
`escape_html()`s it (`history_page._merged_cell()`, `layout.status_row()`) — dropping
`relative_time_html()`'s pre-escaped `<time>` markup through either unmodified would render
literal `&lt;time&gt;` tags on the page.

Finally, this phase's new structural guard tests (route-table coverage, file length, function
length, i18n completeness) must be written under a hard constraint discovered in
`companion/test_suite_guards.py`: any `companion/test_*.py` module (or `conftest.py`) that
imports `ast`, `inspect`, `tokenize` or `linecache` fails guard rule **G2**. The project's own
established escape hatch — used by `test_draw_module_imports_no_page_and_no_server()` — is to
introspect via a **subprocess and runtime object state** (e.g. `sys.modules`), never by
parsing source text in a scanned test file. For the file-length/function-length guards, the
only compliant shape is to put any `ast`-based measurement in a non-`test_`-prefixed helper
module (which `test_suite_guards.py`'s `scanned_files()` never scans) and have a thin
`test_*.py` import and assert on its output.

**Primary recommendation:** Treat CMP-01..09 as nine independent, behaviour-preserving shape
changes verified by "render every page before and after, assert equality" plus the existing
Phase-38 test suites (`test_page_scripts.py`, `test_page_context.py`, `test_static_cache.py`,
`test_freshness_token.py`, `test_request_connections.py`) re-run unmodified as regression
proof; keep all new structural/introspection logic for CMP-01/03/06/09 in helper modules
outside `test_suite_guards.py`'s scan, exactly like `companion/test_browser_ux_helpers.py`
already does for browser instruments.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CMP-01 | Route table `(method, matcher, handler, auth_required)` | `_dispatch_get()`/`_dispatch_post()` fully mapped below: exact route list, which are public today, exact `require_session()` call sites (Architecture Patterns, Code Examples) |
| CMP-02 | One `{route: path}` allowlist | 18 static routes (1 CSS + 17 JS) confirmed 1:1 with path constant + `_serve_*` method + branch; `_serve_static()`/`_static_entry()`/`_not_modified()` cache mechanism to preserve verbatim; 3 dynamic image routes flagged as NOT belonging in the allowlist (Pitfalls) |
| CMP-03 | Split by settings group / by responsibility | Current sizes measured: `config_page.py` 3384, `layout.py` 2597, plus `app.py` 2849 and `health_page.py` 2516 also exceed the ~1500-line ceiling (Open Questions — scope beyond the two named files) |
| CMP-04 | Typed per-page context | `_LazyContext` (dict subclass, `__getitem__`/`get`/`__contains__` override) and `page_context()`'s exact 15 eager + 13 lazy keys fully quoted below; laziness/one-resolve/shared-loader invariants documented for the typed successor to preserve |
| CMP-05 | Named templates | `page_shell()`'s current ~20-positional-arg `%`-template quoted in full; stdlib `string.Template`/`str.format_map` both viable, no literal `$`/`{`/`}` collision found in the skeleton |
| CMP-06 | Broken down; `handle_post` per settings group | 12 production functions over 80 code lines measured directly (list below), matching the audit's own named examples exactly |
| CMP-07 | Shared helpers | `read_form()`/`_read_upload_body()` byte-drain duplication and `_handle_theme_post()`/`_handle_lang_post()` cookie-string duplication both quoted in full |
| CMP-08 | Merged; colours → tokens | Measured: 45 hex-literal occurrences (all but one are the light/dark token-block definitions themselves); exactly one real stray literal (`background: #ffffff` at style.css:3978); `.preview-frame__image` selector genuinely fragmented across 3 top-level rule blocks |
| CMP-09 | Stable message IDs | `i18n.t()`/`i18n_fr.CATALOG` keyed by literal English sentence confirmed; catalogue built by `pkgutil.iter_modules()` merge across 12 per-page modules; the ast-based i18n-call scanner referenced in code comments does not exist as a shipped test yet |
| CFG-34(a-c) | Live relative ages: Flights "When", Calendar "refreshed Xm ago", Health unresolved-prefix | Three exact call sites pinned (`history_page.py:743`, `config_page.py:2304/2307`, `health_page.py:1965`); the double-escaping obstacle in two of three documented with the exact functions responsible (`_merged_cell()`, `status_row()`) |
| CFG-39 | Battery chart onto `draw.py`'s shared drawing contract | `sparkline_point_y()` vs `draw.percent_y()` shown mathematically identical; existing chart-contract tests in `test_companion_app_02.py` (`_DRAWING_CONTRACT_SAMPLES`, colour-literal scan, class-resolves-in-CSS scan) ready to extend to the chart; `draw.label_grid()` confirmed deleted (Phase 35) — audit's suggested target is stale |
| CFG-52 | Artwork drop zone keyboard measurement | Located on Airlines (`airlines_page.py`), not config; `_operate_with_keyboard()` cannot drive a native `<input type="file">`'s picker; existing test (`test_the_artwork_drop_zone_meets_its_floors_at_360px_in_both_themes`) has no keyboard assertion today; REQUIREMENTS.md's CFG-52 row already records the exact Tab+Enter+`expect_file_chooser()` recipe |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Route dispatch / session gating (CMP-01) | API / Backend (`companion/app.py`, single process, stdlib `http.server`) | — | The whole companion app is one `BaseHTTPRequestHandler`; there is no separate frontend-server tier |
| Static asset serving (CMP-02) | API / Backend | CDN / Static (Caddy in front, per `deploy/Caddyfile`) | Caddy adds `encode zstd gzip` and TLS termination only; ETag/304/in-memory cache logic lives entirely in `companion/app.py` |
| Per-request context (CMP-04) | API / Backend | Database / Storage (SQLite via `history_db.connection_scope()`) | `_LazyContext` mediates between the request and both SQLite reads and JSON-file reads; it is backend-only, never serialized to the client |
| HTML templating (CMP-05) | API / Backend | Browser / Client (the served HTML itself) | Server-rendered only; no client templating engine exists or is being introduced |
| CSS (CMP-08) | Browser / Client (`companion/static/style.css`, served as-is) | — | Hand-written, zero-build-step, no CSS-in-JS or preprocessor |
| i18n (CMP-09) | API / Backend (`companion/i18n.py`, resolved per-request via `prefs` ContextVar) | — | Purely server-side string resolution; no client-side i18n library |
| Battery chart drawing (CFG-39) | API / Backend (server-rendered SVG in `companion/pages/health_page.py` via `companion/draw.py`) | — | No client-side charting library; SVG is fully built in Python and shipped as markup |
| Artwork drop zone (CFG-52) | Browser / Client (drag-and-drop JS enhancement) | API / Backend (`POST` still works with scripts blocked via the underlying `<input type="file">`) | Progressive enhancement over a plain file input; the keyboard path is native browser behaviour, not app script |
| Live relative ages (CFG-34) | API / Backend (initial server-rendered text) | Browser / Client (`relative-time.js` ticks the same element client-side) | `layout.relative_time_html()` renders a `<time data-relative>` element server-side; the existing ticker script re-reads it client-side — no new script needed for these three sites |

## Standard Stack

**Not applicable in the conventional sense.** This phase introduces no new library, framework
or package. Per `CLAUDE.md`, the server stack is stdlib + Pillow + requests only, and this
phase's own decisions (CMP-05: "stdlib only") stay inside that constraint. The only "stack"
question is which **stdlib** templating primitive backs `page_shell()`:

| Option | Verdict | Why |
|--------|---------|-----|
| `string.Template` (`$name` substitution) | Viable | No literal `$` found in `page_shell()`'s HTML skeleton (verified by reading the full template below); requires `$$`-escaping only if a literal `$` is ever added later |
| `str.format_map()` (`{name}` substitution) | Viable | No literal `{`/`}` found in the skeleton either; substituted **values** (translated strings, escaped HTML) can safely contain `{`/`}` since only the template string itself is parsed for placeholders |
| f-strings | Not viable | `page_shell()` builds its template once as a module-level format string reused across many calls with named args computed in a specific order (some values, e.g. `SITE_TITLE`, appear 3 times) — an f-string can't be defined once and reused, and CMP-05's own wording is "named templates" |

No installation step, no version to verify, no package-legitimacy audit applies — **Package
Legitimacy Audit section is intentionally omitted** for this reason.

## Architecture Patterns

### Current request-dispatch shape (CMP-01)

`companion/app.py`'s `Handler.do_GET()`/`do_POST()` each open one
`history_db.connection_scope(self.args.state_dir)` for the whole request (Phase 38's
one-connection-per-request invariant — **must be preserved**), then delegate to
`_dispatch_get()`/`_dispatch_post()`, which are `if path == X:` chains:

```python
# companion/app.py — current shape (verified live, line numbers approximate)
def do_GET(self):
    with history_db.connection_scope(self.args.state_dir):
        return self._dispatch_get()

def _dispatch_get(self):
    parsed = urlsplit(self.path)
    path = parsed.path
    if path == LOGIN_ROUTE:
        ...                                   # public
    if path == STYLE_ROUTE:
        return self._serve_stylesheet()        # public
    if path == SCRIPT_ROUTE:                    # ... 16 more identical *_SCRIPT_ROUTE branches, all public
        return self._serve_battery_trend_script()
    if path == HOME_ROUTE:
        return self._render_tab(HOME_ROUTE, home_page.render)   # session-gated INSIDE _render_tab()
    ...
    if path == SETTINGS_ROUTE:
        if not self.require_session():
            return None
        return self.redirect(DISPLAY_ROUTE)      # legacy 303 redirect, gated
    if path.startswith(GALLERY_ROUTE_PREFIX):
        if not self.require_session():
            return None
        return self._serve_gallery_image(...)
    ...
    return self.send_html(404, self._not_found_page())
```

`_dispatch_post()` runs `auth.post_origin_ok(self.headers)` as its unconditional first
statement (before any routing — this must stay the route table's own first gate, not a
per-route concern), then repeats the same `if path == X: if not self.require_session(): ...`
shape roughly 15 times.

**Exact current route inventory** (re-measured, GET + POST):

- **Public (no session) — GET:** `LOGIN_ROUTE`, `STYLE_ROUTE`, and 16 further
  `*_SCRIPT_ROUTE` constants (17 static-file routes total including the stylesheet). All are
  pre-auth by explicit design comment ("a static asset carries no per-user or sensitive data,
  so gating it would add a session round-trip for zero benefit").
- **Public (no session) — POST:** `LOGIN_ROUTE` only.
- **Session-gated — GET:** the six live tabs (`HOME_ROUTE`, `DISPLAY_ROUTE`, `DEVICE_ROUTE`,
  `FLIGHTS_ROUTE`, `HEALTH_ROUTE`, `AIRLINES_ROUTE`, gated *inside* `_render_tab()`'s own
  `require_session()` call, not in `_dispatch_get()`'s if-chain), plus `SETTINGS_ROUTE`,
  `HISTORY_LEGACY_ROUTE`, `PREVIEW_PAGE_ROUTE` (three legacy-redirect routes),
  `GALLERY_ROUTE_PREFIX`, `RUNWAY_IMAGE_ROUTE_PREFIX`, `ILLUSTRATION_IMAGE_ROUTE_PREFIX`,
  `THEME_PREVIEW_ROUTE_PREFIX` (four dynamic image routes).
- **Session-gated — POST:** `SETTINGS_ROUTE`, `POLL_ROUTE`, `QUICK_DISPLAY_ROUTE`,
  `QUICK_QUIET_HOURS_ROUTE`, `QUICK_LED_ROUTE`, `THEME_ROUTE`, `LANG_ROUTE`, `LOGOUT_ROUTE`,
  `airlines_page.RESOLVE_ROUTE`, `airlines_page.MANUAL_DELETE_ROUTE_PREFIX`,
  `ILLUSTRATION_IMAGE_ROUTE_PREFIX` (POST variant, upload), `RULES_ADD_ROUTE`,
  `CALENDAR_DISCONNECT_ROUTE`, `CALENDAR_CONNECT_ROUTE`, `NOTIFICATIONS_TEST_ROUTE`,
  `RULES_DELETE_ROUTE_PREFIX`.

**There is no dedicated health-probe route in `companion/app.py` today** — `/health` is the
authenticated Health *tab*, gated like every other tab. CONTEXT.md's "static assets, health
probe — whatever is public today" should be read as "static assets and `/login` only"; there
is no unauthenticated probe endpoint to add to the allowlist.

A route table naturally holds `(method, matcher, handler, auth_required)` tuples where
`matcher` is either an exact string or a `(prefix, suffix)` pair for the seven prefix/suffix
routes (`GALLERY_ROUTE_PREFIX`, `RUNWAY_IMAGE_ROUTE_PREFIX`, `ILLUSTRATION_IMAGE_ROUTE_PREFIX`,
`THEME_PREVIEW_ROUTE_PREFIX`, `airlines_page.MANUAL_DELETE_ROUTE_PREFIX`/`_SUFFIX`,
`RULES_DELETE_ROUTE_PREFIX`/`_SUFFIX`). The `RULES_DELETE_ROUTE` case additionally splits its
captured middle segment on `/` once — the table's `handler` for that entry needs to stay a
thin wrapper doing that split, not a second matcher primitive.

### Current static-file serving shape (CMP-02)

Every one of the 18 static routes (`STYLE_ROUTE` + 17 `*_SCRIPT_ROUTE`) follows the identical
four-part pattern: a route constant (`app.py:96-118`), a path constant built with
`os.path.join(_HERE, "static", "<file>")` (`app.py:423-440`), a one-line `_serve_*` delegate
method (`app.py:1778-1827`) calling `_serve_script_file(path)` → `_serve_static(path,
content_type, cache_control)`, and one `if path == X: return self._serve_*()` branch in
`_dispatch_get()`. This is mechanically a perfect `{route: (path, content_type,
cache_control)}` dict — collapsing it removes 17 near-identical one-line methods and 17
near-identical dispatch branches with zero behaviour change.

**Must preserve verbatim** (Phase 38, EFF-01/38-02): `_serve_static()`'s body — the
`_static_entry()` in-memory cache (`_StaticEntry` namedtuple: `payload, etag, last_modified,
mtime_s`, read once per process, mtime-invalidated), `_not_modified()`'s RFC 9110 §13.2.2
conditional evaluation, and the exact `Cache-Control` values per route (`"public, no-cache"`
for CSS/JS, `"private, max-age=300"` for `_serve_runway_image()`).

**Do NOT fold into the same allowlist:** `_serve_gallery_image()`, `_serve_illustration_image()`
and `_serve_theme_preview_image()` are session-gated, membership-tested against a
per-request-computed set (not a fixed file path), and in the theme-preview case can render a
*live* raster from the latest runway event (`?live=1`). These three are dynamic image
endpoints, not static files — CMP-02's `{route: path}` allowlist should cover exactly the 18
pre-auth static routes and leave these three as their own route-table entries with their own
handlers.

### Current `page_context()` / `_LazyContext` shape (CMP-04)

`_LazyContext(dict)` overrides `__getitem__`, `get()` and `__contains__` so a loader in its
`loaders` dict resolves at most once, on first read, and a loader may read another
already-resolved key of the same `ctx` via closure. `page_context()` builds it with:

**Eager keys (15):** `state_dir`, `ui_theme`, `lang`, `device_config`, `screen_id`,
`last_checkin_ts`, `battery_critical`, `wake_interval_env_default`, `flash`, `flash_role`,
`runway_images`, `now`, `resolve_prefix`, `flights_limit`.

**Lazy loaders (13):** `_health_signals` (shared snapshot, zero markup), `health_state`
(markup, only Home/Health read it), `health_severity` (nav-dot, every tab reads it — reuses
`health_state` if already resolved, else derives straight from the signals snapshot so it
never pays twice), `gallery_entries`, `manual_resolutions`, `colour_rules`,
`calendar_configured` (its own file-mode read, cheaper than the full registry),
`_calendar_registry` (shared), `calendar_last_synced_at`/`calendar_last_attempt_at`/
`calendar_entry_count` (all three read the shared `_calendar_registry` loader once),
`calendar_drift`, `poll_cooldown_remaining`.

A typed successor (dataclass or similar) for CMP-04 must reproduce every one of these
laziness/sharing relationships exactly — the invariant under test in
`companion/test_page_context.py` is specifically "every tab pays for exactly one
`health_signals()` read; only Home/Health additionally pay for one markup build;
`_calendar_registry`'s three dependents share one registry load." A naive dataclass with
`@cached_property`-style per-field memoization would reproduce single-resolution per field but
must still route `health_severity`/`calendar_last_synced_at`/etc. through the *same shared*
underlying call, not recompute it — i.e. the shared shared-internal-key pattern
(`_health_signals`, `_calendar_registry`) needs an explicit equivalent (e.g. two internal
`@cached_property`s that public fields delegate to), not one per public field.

### Current `page_shell()` template shape (CMP-05)

`layout.page_shell(title, active, body, ui_theme="auto", flash=None, banner=None,
health_alert=None, lang=None, device_config=None, scripts=(), refresh_token=None)` builds one
`%`-format string with roughly 20 positional substitutions (some values — e.g. `SITE_TITLE` —
appear three times) covering `<html lang>`, `data-ui-theme`, `<title>`, favicon link, the
computed `body_class_attr` (itself built by ~6 sequential string concatenations for
`REFRESH_PAUSED_ATTR`/`REFRESH_RECONNECTING_ATTR`/`REFRESH_PAGE_ATTR`/`REFRESH_TOKEN_ATTR`/
`QUICK_SWITCH_FAILED_ATTR`/nine `relative_copy_attrs()` pairs), skip-link, icon defs, sidebar,
sidebar footer, mobile nav, flash/banner/body (with a `FLASH_SLOT_MARKER` splice point), tab
bar, quick-toast div, and the script tags. `scripts` is validated against
`SHELL_SCRIPT_ORDER` (raises `ValueError` on an unknown src) before assembly — this validation
must survive the CMP-05 migration unchanged.

Migrating to `str.format_map()` is the lower-friction stdlib option: build one `dict` of ~20
named values (several already computed as locals before the final `return`), keep the
skeleton as one `"..." .format_map(values)` call. No value being substituted needs its own
`{`/`}` escaped (only the template needs escaping, and there is no literal `{`/`}` in the
skeleton); this is simpler than `string.Template`'s `$$`-escaping rule, which existing string
constants (e.g. any future price/monetary text) could accidentally trip.

### Current CMP-06 oversized functions (measured directly, non-test production code only)

Measured via `ast` (line count excludes blank and `#`-comment-only lines; docstrings still
count as code since AST doesn't cheaply distinguish them — true counts are somewhat lower):

| Lines | File:line | Function |
|-------|-----------|----------|
| 184 | `companion/pages/config_page.py:2773` | `render` |
| 166 | `companion/pages/config_page.py:3190` | `handle_post` |
| 139 | `companion/pages/health_page.py:740` | `battery_sparkline_svg` |
| 126 | `companion/pages/config_page.py:2268` | `_calendar_connection_html` |
| 126 | `companion/pages/config_page.py:1018` | `_aspect_card_html` |
| 125 | `companion/layout.py:1888` | `page_shell` |
| 123 | `companion/pages/airlines_page.py:456` | `_airline_card_html` |
| 111 | `companion/layout.py:2267` | `frame_strip_html` |
| 103 | `companion/pages/history_page.py:931` | `_history_cards_html` |
| 95 | `companion/pages/config_page.py:2116` | `notifications_group` |
| 93 | `companion/app.py:2281` | `_dispatch_get` |
| 90 | `companion/app.py:2643` | `_dispatch_post` |

Twelve functions today (the audit's "41" is stale — real prior cleanup, not a
measurement-methodology difference; both counts were taken the same way: production code
only, tests excluded). `_dispatch_get`/`_dispatch_post` themselves are on this list and will
shrink naturally once CMP-01's route table lands; `page_shell` will shrink once CMP-05 lands.
`config_page.render`/`handle_post` are the two the CONTEXT.md decision explicitly names for
splitting "per settings group."

### Current CMP-07 duplication

`read_form()` and `_read_upload_body()` (both `Handler` methods) share an identical
read-with-cap-then-drain-remainder loop, differing only in the byte cap
(`MAX_FORM_BYTES` vs `MAX_ILLUSTRATION_UPLOAD_BYTES`) and the over-cap/undecodable return
value (`{}` vs `None`). A shared `_drain_capped_body(cap)` returning `(raw_bytes_or_None,
truncated: bool)` (or similar) lets each caller keep its own degrade-value contract.

`_handle_theme_post()` and `_handle_lang_post()` build a `Set-Cookie` header with the identical
format string (`"%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"`), differing only in
cookie name, allowed-values set, and max-age constant. A shared
`_choice_cookie_header(name, value, choices, max_age_s)` collapses both.

### CFG-39: battery chart / `draw.py` contract

`companion/pages/health_page.py`'s `battery_sparkline_svg()` still builds its own scale
(`sparkline_point_y()`), its own axis chrome (raw `<rect>` string literals), its own class
vocabulary (`SPARKLINE_*_CLASS` constants) and its own CSS (22 `.sparkline*` selectors beside
26 `.drawing*` ones in `style.css`) — confirmed still true today, not just at Phase 24's
close.

`sparkline_point_y(value)` and `draw.percent_y(value, domain_min, domain_max,
inset_percent=0.0)` are the **identical formula** (clamp into domain, invert for SVG's
downward axis, apply an inset percent) — `sparkline_point_y` is exactly `percent_y(value,
SPARKLINE_Y_MIN_MV, SPARKLINE_Y_MAX_MV, _SPARKLINE_VERTICAL_INSET_PERCENT)`. `health_page.py`
already imports `companion.draw as draw` (for the ring gauge), so migrating costs no new
import.

**The audit's own suggested rewiring target no longer exists**: `draw.label_grid()` was
deleted as dead code in Phase 35 (`HYG-05`). Any CFG-39 plan referencing it needs to instead
build the chart's axis/tick markup from `draw.rect()`/`draw.line()`/`draw.circle()` (the
primitives the four other drawings already use) rather than assuming a grid-label helper
exists to call.

The chart-contract machinery CFG-39 asks to extend already exists and already covers
`draw.py` plus every `companion/pages/*.py` module (comment/docstring-stripped literal scan,
so `health_page.py`'s own docstrings mentioning `<polyline>` don't false-positive):
`companion/test_companion_app_02.py::test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route`,
`test_every_drawing_class_resolves_in_the_served_stylesheet`,
`test_draw_module_imports_no_page_and_no_server` (subprocess + `sys.modules`, explicitly
**not** via `ast`/`inspect` — see Common Pitfalls), `test_draw_module_emits_no_script_and_no_external_reference`,
`test_draw_module_escapes_every_interpolated_value`, `test_draw_module_scales_clamp_and_never_raise`.
Extending these to cover `battery_sparkline_svg()`'s own emitted markup (once it routes
through `draw.py`) is the "chart contract is enforced by a machine" half of CFG-39.

### CFG-52: artwork drop zone

Lives on **Airlines** (`companion/pages/airlines_page.py`, `_upload_drop_html()`,
`UPLOAD_DROP_*` constants), reused at two call sites (`REPLACE_INPUT_ID` and a second upload
input). It writes into the form's own `<input type="file" accept="image/png" required>` via
`DataTransfer` on drop; the file bytes still travel the same POST as always, so the no-JS path
is already sound (proven by
`test_dropped_and_picked_files_are_stored_identically`). `_operate_with_keyboard()`
(`companion/test_browser_ux_helpers.py:819`) explicitly documents that it works by dispatching
real keyboard events to a *focused* element and reading back application state — it cannot
drive a native file chooser dialog (an OS-level, not DOM-level, surface), and refuses to run
scripts-blocked. There is currently **no** keyboard-only measurement of this control anywhere
in the suite (`test_the_artwork_drop_zone_meets_its_floors_at_360px_in_both_themes` measures
hit-area/theme-paint/aspect-ratio only). `REQUIREMENTS.md`'s own CFG-52 traceability row
already records the buildable recipe: focus the input via Tab, press Enter inside Playwright's
`expect_file_chooser()` context manager, and submit by pressing Enter on the focused submit
button (never `.click()`) — proving the platform's native file-chooser affordance rather than
attempting to synthesize one.

### CFG-34: three live-age conversions

All three call sites use `layout.age_seconds(ts, now)` → `layout.relative_age_text(age)` (a
plain string, "5m ago"/"5 min ago" style) today; all three already have the raw ISO `ts` and
`now` in scope, so switching to `layout.relative_time_html(ts, now)` (which internally calls
`age_seconds()`/`relative_age_text()` itself and wraps the result in an escaped `<time
datetime="..." data-relative>...</time>`) needs no new data threaded through.

1. **Flights "When" cell** — `history_page.py:743`, inside a function building `secondary =
   layout.relative_age_text(age)` then `html = _merged_cell(clock_text, secondary)`.
   `_merged_cell(primary, secondary)` (`history_page.py:517`) calls `escape_html(secondary)`
   **unconditionally** — passing `relative_time_html()`'s pre-escaped markup through it would
   double-escape the `<time>` tag into literal text.
2. **Calendar "refreshed Xm ago"** — `config_page.py:2304`/`2307`, inside
   `_calendar_connection_html()`, which builds `detail = i18n.t(TEMPLATE) % (...,
   layout.relative_age_text(age))` and passes `detail` to `layout.status_row("", verdict,
   detail, state)`. `status_row()` (`layout.py:2435`) calls `escape_html(detail)`
   **unconditionally** (its own docstring: "`verdict`/`detail`/`label` are escaped here") —
   same double-escaping trap.
3. **Health unresolved-prefix "First seen"/"Last seen"** — `health_page.py:1965`, inside
   `_registry_seen_cell_html()`, which builds
   `html += '<span class="cell-secondary">%s</span>' % escape_html(layout.relative_age_text(age))`
   directly (no shared escaping helper in the way) — this one is a straightforward swap:
   drop the `escape_html()` wrapper and call `layout.relative_time_html(raw_ts, now)` in its
   place.

`companion/pages/home_page.py`'s existing (already-shipped) live-age cell shows the
established pattern for the two harder sites: it builds the primary/secondary halves as two
separately-escaped fragments and concatenates them itself
(`cell_html += '<span ...>(%s)</span>' % layout.relative_time_html(ts, now)`), explicitly
**not** routing the composite through `layout.concise_timestamp_html()` "which bundles the
clock and the relative age into one already-escaped span — the single-element shape this cell
exists to avoid." The same restructuring (build-and-concatenate rather than
pass-through-an-escaping-helper) is the template for sites 1 and 2 above. See Common Pitfalls
for the concrete obstacle this creates for `_merged_cell()`/`status_row()`'s other callers.

The fourth relative age that stays static by design (`health_page.py:718`,
`_battery_reading_parts()`'s `when` text) feeds `battery_sparkline_svg()`'s per-point `<title>`
tooltip — an SVG `<title>` element has no live DOM binding `relative-time.js` could tick, which
is exactly the "unowned without changing battery-trend.js's transport" blocker
`REQUIREMENTS.md` already records. Nothing to build here; CFG-34's job is to enumerate it, not
convert it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Named string templating | A custom `{name}`/`$name` mini-parser | `str.format_map()` or `string.Template` (stdlib) | CMP-05 explicitly requires stdlib-only; both handle this template's needs with zero new code |
| Source-code structural metrics (CMP-03/06 file/function length) | A regex-based line counter in a `test_*.py` file | `ast.parse()` in a **non-`test_`-prefixed helper module**, imported by a thin test | `companion/test_suite_guards.py` guard rule G2 fails any scanned test module that imports `ast`/`inspect`/`tokenize`/`linecache` at all — this is a hard constraint, not a style preference |
| i18n completeness checking (CMP-09) | Grepping `.py` source for `i18n.t("...")` call literals | Import `companion.i18n_fr.CATALOG` and the (to-be-built) stable-ID registry directly, assert on the **runtime dict**, not source text | Matches the project's own G2/G3 "introspect runtime objects, not source text" convention; also sidesteps the documented false-positive risk of literal-scanning docstrings (Phase 24's own health_page.py docstring/`<polyline>` example) |

**Key insight:** every "don't hand-roll" item in this phase is really the same rule stated
three ways: `companion/test_suite_guards.py` already forbids source-text/AST introspection
inside any scanned test module, so every new structural guard this phase adds must go through
runtime objects (imported modules, `sys.modules`, dict contents) or a helper module the guard
never scans — never a fresh grep/regex/ast pass living inside a `test_*.py` file.

## Common Pitfalls

### Pitfall 1: G2 blocks `ast`/`inspect` use inside any `test_*.py`/`conftest.py` file
**What goes wrong:** A new `test_route_table_covers_every_route.py` or
`test_no_function_over_80_lines.py` that does `import ast; tree = ast.parse(...)` directly
fails `test_suite_guards.py`'s own G2 check the moment it's added to the suite.
**Why it happens:** `test_suite_guards.py`'s `_Scanner.visit_Attribute()` flags any
`<name>.<attr>` where `<name>` resolves to `inspect`, `ast`, `tokenize` or `linecache`, scanned
across every `companion/test_*.py`/`conftest.py` file except the guard module itself.
**How to avoid:** Put the `ast`-based measurement logic in a module that does **not** start
with `test_` (e.g. `companion/structure_metrics.py` or a `test-support/` module) — such a
module is invisible to `test_suite_guards.py`'s `scanned_files()` (which only lists
`os.listdir()` entries starting with `test_` or named `conftest.py`) — then have a thin
`test_*.py` file `import` it and assert on its return value. This is the same shape
`test_draw_module_imports_no_page_and_no_server()` already uses (subprocess + `sys.modules`
instead of `ast`) for its own "prove no forbidden import" check, and its docstring says so
explicitly: *"never by reading its source (guard G2 bans ast/tokenize introspection of
production code)"*.
**Warning signs:** Any new guard test file failing collection or failing with a
`test_module_obeys_behaviour_over_source_rules` violation naming `G2` at the new file's own
path.

### Pitfall 2: double-escaping `relative_time_html()`'s markup at two of the three CFG-34 sites
**What goes wrong:** `history_page._merged_cell()` and `layout.status_row()` both
unconditionally `escape_html()` the "secondary"/"detail" argument they're given. Passing
`relative_time_html()`'s return value (already-escaped `<time>` markup) through either
produces visible literal `&lt;time datetime=...&gt;` text on the rendered page instead of a
live element.
**Why it happens:** Both helpers were written when every caller's secondary text was always
plain text, so they escape defensively and correctly for that contract — CFG-34 is the first
caller that needs to hand them markup instead.
**How to avoid:** Follow `home_page.py`'s already-shipped pattern: build the composite HTML
directly at the call site (concatenate an escaped primary fragment with
`relative_time_html()`'s pre-escaped fragment) rather than routing through
`_merged_cell()`/`status_row()` unchanged. This likely means either (a) giving
`_merged_cell()`/`status_row()` a `secondary_is_markup=`/`detail_html=` opt-in parameter that
skips the escape for that one argument, or (b) restructuring the two call sites to build their
own markup inline the way `home_page.py` already does, and no longer route through the shared
helper for this one field. Either choice needs a decision recorded in the plan — this is real
plan-shaping work, not a mechanical rename.
**Warning signs:** A browser test or served-HTML assertion for Flights/Calendar showing the
literal string `<time` inside a `<span>`'s text content instead of a real element; or, if
missed entirely, a "no live tick" bug report despite the code appearing to call
`relative_time_html()`.

### Pitfall 3: `draw.label_grid()` no longer exists
**What goes wrong:** A CFG-39 plan that follows the audit/REQUIREMENTS.md's own suggested
fix literally ("rewires `battery_sparkline_svg()` onto `draw.percent_*` + `draw.label_grid()`")
will fail at import time.
**Why it happens:** `draw.label_grid` was flagged as dead code and deleted in Phase 35
(HYG-05), after the CFG-39 traceability note in `REQUIREMENTS.md` was written (2026-09-23,
same day, but the deletion is a later phase's work landing after that note).
**How to avoid:** Build the chart's axis chrome and tick labels from the primitives that
currently exist and that the other four drawings already use — `draw.rect()`, `draw.line()`,
`draw.circle()`, `draw.percent_canvas()`, `draw.label_span()`, `draw.title()`. Confirm current
`draw.py` exports before planning against any named helper.
**Warning signs:** `AttributeError: module 'companion.draw' has no attribute 'label_grid'` at
plan-execution time.

### Pitfall 4: the ~1500-line ceiling is wider than the two files CONTEXT.md names
**What goes wrong:** A plan that only splits `config_page.py` and `layout.py` (the two files
CONTEXT.md's CMP-03 bullet explicitly names) leaves `app.py` (2849 lines) and `health_page.py`
(2516 lines) both still over the "no companion file over ~1500 lines" success criterion the
same bullet states unconditionally.
**Why it happens:** CMP-03's decision text names two files by way of example (matching the
audit's own two named files), but the success criterion is phrased as a project-wide ceiling.
**How to avoid:** Flagged in Open Questions below — either confirm the ceiling is meant
project-wide (in which case `app.py`/`health_page.py` need their own split plans, noting
`app.py` will shrink substantially once CMP-01/02 land, which may bring it under 1500 without
a dedicated split) or get explicit confirmation the ceiling only binds the two named files.
**Warning signs:** A structural guard test asserting file length project-wide would fail on
`app.py`/`health_page.py` even after config_page.py/layout.py are split, if this isn't
addressed.

### Pitfall 5: not every "static-looking" image route belongs in CMP-02's allowlist
**What goes wrong:** Folding `_serve_gallery_image()`, `_serve_illustration_image()` or
`_serve_theme_preview_image()` into the same `{route: path}` allowlist as the 18 pure static
files loses their membership tests (404 on an unrecognised id/key/theme), their session gate,
and — for theme-preview — the `?live=1` dynamic-render branch.
**Why it happens:** They look superficially similar ("serve an image at a route") but are
semantically request handlers with validation and business logic, not file lookups.
**How to avoid:** Scope CMP-02's allowlist to exactly the 18 pre-auth static-file routes;
give the three dynamic image routes their own route-table entries with their existing handler
methods, `auth_required=True`.
**Warning signs:** A 404-on-unknown-id test starting to leak a raw filesystem error, or an
image route losing its session gate.

## Runtime State Inventory

Not applicable in the migration/rename sense — none of CMP-01..09 or CFG-34/39/52 renames a
persisted identifier, external config key, cookie name, session-token format, or route path.
Verified explicitly:
- **Route paths** (`/login`, `/health`, `/settings`, etc.) are unchanged — only the dispatch
  mechanism inside `companion/app.py` changes.
- **Cookie names** (`auth.SESSION_COOKIE_NAME`, `auth.UI_THEME_COOKIE_NAME`,
  `auth.UI_LANG_COOKIE_NAME`) are unchanged — CMP-07 only shares the *header-building* code.
- **i18n keys** move from "the literal English sentence" to "a stable message ID" (CMP-09),
  but this is an in-process Python dict key with no external persistence — no database, JSON
  file, or client-visible value is keyed by an English sentence today (`i18n_fr.CATALOG` is
  rebuilt fresh at import time from the `companion/i18n_fr/*.py` source modules, never
  round-tripped through disk).
- **`config_page.py`'s module path** (`companion/pages/config_page.py`) was already moved in
  an earlier phase (32-38); this phase splits its *contents* into multiple files, which is an
  internal `import` graph change only — no runtime state references the module by name (no
  pickle, no dynamic `importlib` string lookup found in this codebase for `config_page`).

**Nothing found requiring a data migration or external re-registration.**

## Code Examples

### `_LazyContext` (companion/app.py) — the mechanism CMP-04 must preserve

```python
class _LazyContext(dict):
    def __init__(self, values, loaders):
        super().__init__(values)
        self._loaders = dict(loaders)

    def __getitem__(self, key):
        if key in self._loaders:
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

### `draw.percent_y()` (companion/draw.py) — the scale CFG-39 migrates the chart onto

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

`health_page.sparkline_point_y(value)` today is exactly
`draw.percent_y(value, SPARKLINE_Y_MIN_MV, SPARKLINE_Y_MAX_MV,
_SPARKLINE_VERTICAL_INSET_PERCENT)`.

### `relative_time_html()` (companion/layout.py) — the element CFG-34 threads through three sites

```python
def relative_time_html(ts, now_ts, fallback="no reading yet", lang=None,
                       countdown=False, static_text=None):
    if not ts:
        return escape_html(fallback)
    parsed = parse_iso(ts)
    age = age_seconds(ts, now_ts)
    if parsed is None or age is None:
        return escape_html(ts)
    instant = _machine_instant(parsed)
    if not instant:
        return escape_html(ts)
    if static_text is not None:
        text = static_text
    elif countdown and age >= 0:
        text = i18n.t_lang(RELATIVE_WAITING_TEXT, lang if lang is not None else prefs.current_lang())
    elif age < 0:
        text = relative_future_text(-age, lang=lang)
    else:
        text = relative_age_text(age, lang=lang)
    marker = " " + RELATIVE_COUNTDOWN_ATTR if countdown else ""
    return '<time datetime="%s" data-relative%s>%s</time>' % (
        escape_html(instant), marker, escape_html(text))
```

Note the return value is already fully escaped markup — every caller "interpolates the return
value verbatim, never re-escaping it" (own docstring). This is the contract `_merged_cell()`
and `status_row()` currently violate for any caller that would hand them this value (Pitfall
2).

### Existing chart-contract test shape to extend for CFG-39 (companion/test_companion_app_02.py)

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

CFG-39 needs `battery_sparkline_svg()`'s own emitted samples added to this tuple (or an
equivalent chart-specific test using the same `_SHAPE_ELEMENT`/`_COLOUR_LITERAL` regex
already defined in that file) once the chart routes through `draw.py`'s primitives.

## State of the Art

Not applicable — this phase makes no external-facing protocol, library, or standard change.
`http.server`/`BaseHTTPRequestHandler` remains the deliberate stdlib-only choice (per
`CLAUDE.md`); nothing here supersedes an older approach with a newer one from the wider
ecosystem. The only "old → new" shifts are entirely internal to this codebase and are each
already covered under their own CMP-* item above (if-chain → route table; positional `%s` →
named template; English-keyed catalogue → stable-ID catalogue).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `str.format_map()` is the lower-friction stdlib templating choice for CMP-05 versus `string.Template` | Standard Stack, Architecture Patterns | Low — both are viable per this research; a planner preferring `string.Template` loses nothing but needs to add `$$`-escaping discipline if a literal `$` is ever introduced to the skeleton |
| A2 | The CSS-duplication figures in the Summary/CMP-08 row (49 distinct duplicated selectors from a naive regex scan) are noisy and include legitimate `@keyframes from`/`to` repeats and `:root`/`*` appearing once per theme block — only `.preview-frame__image`'s 3-4 top-level (non-`@media`) declarations were manually confirmed as genuine fragmentation | Standard Stack / CMP-08 rows | Medium — the planner should re-run the count through `test-support/companion_markup.py`'s `css_rules()`/`rules_with_selector()` (the project's own CSS parser) before writing CMP-08's task list, not trust the regex figure for scope-sizing |
| A3 | No dedicated health-probe route exists in `companion/app.py`, so CMP-01's public allowlist is exactly `LOGIN_ROUTE` + the 18 static routes | Architecture Patterns | Low — directly grepped and confirmed absent; if a probe is added by a different in-flight phase (39, server-side) before this phase executes, re-verify |

**All other claims in this research were verified directly against the live code in this
session (file reads, `ast`-based measurement, `grep`) or are internal-only observations
requiring no external verification.**

## Open Questions

1. **Does the ~1500-line ceiling (CMP-03 success criterion 2) bind every companion file, or
   only the two files CONTEXT.md names?**
   - What we know: `config_page.py` (3384) and `layout.py` (2597) are named explicitly.
     `app.py` (2849) and `health_page.py` (2516) also exceed 1500 today and are not named.
   - What's unclear: whether `app.py`'s natural shrinkage from CMP-01/02 (removing ~40
     dispatch branches and 17 near-identical `_serve_*` methods) is expected to bring it under
     1500 without a dedicated split plan, and whether `health_page.py` (which CFG-39 also
     touches) needs its own split.
   - Recommendation: measure `app.py`'s post-CMP-01/02 line count before deciding whether it
     needs an explicit split task; treat `health_page.py` as in-scope for the ~1500 ceiling
     unless the plan explicitly descopes it with a stated reason.

2. **How should `_merged_cell()`/`status_row()` be changed to carry a markup fragment without
   double-escaping it (Pitfall 2)?**
   - What we know: `home_page.py`'s existing live-age cell avoids the shared helper entirely
     and builds its composite markup inline.
   - What's unclear: whether the plan should add an opt-in "this argument is pre-escaped
     markup" parameter to the two shared helpers (risk: every other existing caller of
     `_merged_cell()`/`status_row()` must be re-verified to still pass plain text, i.e. still
     get escaped) or bypass the helpers at just these two call sites.
   - Recommendation: bypass the shared helper at the two CFG-34 call sites (matches the
     already-shipped `home_page.py` precedent exactly, touches no other caller) rather than
     widening the helpers' contract.

3. **Exact CSS selector-duplication count for CMP-08's task sizing.**
   - What we know: one real stray hex literal (`style.css:3978`); `.preview-frame__image` is
     genuinely declared across (at least) 3 non-`@media` top-level rule blocks.
   - What's unclear: the full authoritative list of duplicated selectors project-wide (this
     research's regex-based count is too noisy to use directly, see A2).
   - Recommendation: re-run via `test-support/companion_markup.py`'s existing `css_rules()`
     parser at plan-execution time, scoped to exclude `@keyframes`/`@media`-qualified
     re-declarations of the same selector (those are legitimate responsive/theme overrides,
     not duplication).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-xdist + pytest-cov + pytest-playwright 0.9.0 (dev deps, `server/requirements-dev.txt`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["server", "stub-server", "companion", "test-support", "deploy"]`) |
| Quick run command | `pytest companion/test_<module>.py -x` |
| Full suite command | `./scripts/run-all-tests.sh` (wraps `pytest -n auto --cov`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CMP-01 | Route table dispatch; every non-public route answers unauthenticated identically to today | integration | `pytest companion/test_route_table.py -x` | ❌ Wave 0 (new file; existing `require_session()` behaviour already covered ad hoc across `test_companion_app_*.py`, reusable as a baseline) |
| CMP-02 | Static allowlist preserves ETag/304/Cache-Control byte-for-byte | integration | `pytest companion/test_static_cache.py -x` | ✅ (Phase 38, extend for the new dispatch shape) |
| CMP-03 | No companion file over ~1500 lines | structural | `pytest companion/test_file_length_guard.py -x` | ❌ Wave 0 (new; must live behind a non-`test_`-prefixed `ast` helper, see Pitfall 1) |
| CMP-04 | Typed context preserves laziness/one-resolve/shared-loader invariants | unit | `pytest companion/test_page_context.py -x` | ✅ (Phase 38, extend for the typed successor) |
| CMP-05 | `page_shell()` output byte-identical after named-template migration | integration | `pytest companion/test_companion_app_01.py::test_page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme -x` plus a new before/after equality snapshot | ✅ partial / ❌ equality harness Wave 0 |
| CMP-06 | No production function over ~80 code lines | structural | `pytest companion/test_function_length_guard.py -x` | ❌ Wave 0 (new; same helper-module constraint as CMP-03) |
| CMP-07 | Shared drain helper / cookie helper preserve existing behaviour | unit | existing `test_companion_app_01.py`/`test_companion_app_05.py` upload/cookie tests | ✅ (re-run unmodified as regression proof) |
| CMP-08 | No duplicated selector; no stray hex outside tokens; computed styles unchanged in both themes | browser + structural | `pytest companion/test_status_pages_07.py -k contrast` plus a new selector-dedup structural test | ✅ partial / ❌ dedup guard Wave 0 |
| CMP-09 | Every message ID has both languages | unit | `pytest companion/test_i18n.py -x` (extend) | ✅ partial — needs a completeness assertion added |
| CFG-34 | Three sites render live `<time data-relative>`, fourth stays static and enumerated | browser | `pytest companion/test_browser_ux_03.py -k relative` (extend) | ✅ partial (ticker itself tested; the three new sites need their own assertions) |
| CFG-39 | Chart routes through `draw.py`; SVG equivalent before/after | unit + integration | `pytest companion/test_companion_app_02.py -k drawing` (extend `_DRAWING_CONTRACT_SAMPLES`) | ✅ partial |
| CFG-52 | Drop zone keyboard-operable, no pointer event | browser | new test using `_operate_with_keyboard()`'s sibling recipe (Tab + `expect_file_chooser()` + Enter-submit) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the touched module's own `pytest companion/test_X.py -x`
- **Per wave merge:** `./scripts/run-all-tests.sh`
- **Phase gate:** full suite green before `/gsd:verify-work`, coverage ≥ 93% (current `fail_under` in `pyproject.toml`)

### Wave 0 Gaps
- [ ] `companion/test_route_table.py` — CMP-01 coverage (route-table introspection + unauthenticated-response equality)
- [ ] A non-`test_`-prefixed structural-metrics helper module (e.g. `companion/structure_metrics.py` or under `test-support/`) providing `ast`-based file/function length measurement, imported by thin `test_file_length_guard.py`/`test_function_length_guard.py` files — required by CMP-03/CMP-06, constrained by guard rule G2 (Pitfall 1)
- [ ] A rendered-HTML before/after equality harness for the CMP-05 template migration (snapshot every page, both languages/themes where relevant, before the `page_shell()` change; assert equality after)
- [ ] A CSS selector-dedup structural test built on `test-support/companion_markup.py`'s existing parser (CMP-08)
- [ ] An i18n completeness test asserting every stable message ID resolves in both `en`/`fr` (CMP-09) — runtime-dict-based, not source-text-based
- [ ] A keyboard-only measurement test for the artwork drop zone using Playwright's `expect_file_chooser()` (CFG-52)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (unchanged) | `auth.verify_session_token()`/`auth.is_revoked()` via `Handler.require_session()` — CMP-01 must preserve every existing gate exactly, not loosen any route |
| V3 Session Management | yes (unchanged) | Session cookie (`auth.SESSION_COOKIE_NAME`), `SameSite=Strict`, revocation list — untouched by this phase |
| V4 Access Control | yes (CMP-01's core risk surface) | The route table's `auth_required` field is the single source of truth for every route's gate; CMP-01's own acceptance test (iterate the table, request every non-public route with no cookie, assert identical unauthenticated response to today) is this control's verification |
| V5 Input Validation | yes (unchanged) | `read_form()`/`_read_upload_body()` byte caps and degrade-to-empty/`None` contracts must survive CMP-07's shared-helper extraction unchanged |
| V6 Cryptography | n/a | No cryptographic code touched by this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A route accidentally added to the public allowlist during CMP-01/02's refactor (e.g. a session-gated image route folded into the pure-static allowlist by mistake) | Elevation of Privilege | The route-table coverage test (already specified in CONTEXT.md's Specific Ideas) must enumerate every route and assert unauthenticated behaviour matches today's, run as a hard gate before the phase is considered done |
| Reflected/stored XSS via the CFG-34 markup-passthrough change (Pitfall 2) — if the fix to `_merged_cell()`/`status_row()` is done carelessly (e.g. a blanket "trust this argument" flag applied to the wrong call site) | Tampering | Keep the "pre-escaped markup" opt-in (if added) scoped to the exact CFG-34 call sites only, never as a default; prefer the bypass-the-helper approach (Open Question 2) since it touches no other caller's contract at all |
| CSRF via the theme/lang POST routes losing their `require_session()` gate during CMP-01's table migration | Tampering | Same route-table coverage test as above; these two routes are explicitly called out in existing code comments as "gated like every other state-changing route" and must stay gated |

## Sources

### Primary (HIGH confidence — read directly from the live repository in this session)
- `companion/app.py` (2849 lines) — full route dispatch, static serving, `_LazyContext`,
  `page_context()`, `read_form()`/`_read_upload_body()`, cookie-building, freshness token
- `companion/layout.py` (2597 lines) — `page_shell()`, `status_row()`, `relative_time_html()`
  and siblings
- `companion/pages/config_page.py` (3384 lines), `companion/pages/health_page.py` (2516
  lines), `companion/pages/history_page.py` (1144 lines), `companion/pages/airlines_page.py`
  (1293 lines) — CMP-03/06 measurement, CFG-34/39/52 call sites
- `companion/draw.py` (857 lines) — CFG-39's shared drawing primitives
- `companion/i18n.py`, `companion/i18n_fr/__init__.py` and its 12 sibling modules — CMP-09
  mechanism
- `companion/test_suite_guards.py` (777 lines) — the G1-G12 behaviour-over-source rules
  binding every new structural guard test this phase adds
- `companion/test_companion_app_02.py` — existing chart-contract test shapes for CFG-39
- `companion/test_browser_ux_helpers.py` — `_operate_with_keyboard()`/`_hit_area()`/
  `_assert_hit_target()` instruments for CFG-52
- `companion/test_browser_ux_04.py` — the artwork drop zone's existing (non-keyboard) test
- `companion/static/style.css` (4793 lines) — measured hex-literal and selector-duplication
  counts
- `.planning/audits/2026-09-23-code-audit.md`, `.planning/REQUIREMENTS.md` (CMP-01..09,
  CFG-34, CFG-39, CFG-52 rows and traceability notes), `.planning/phases/38-*/38-*-SUMMARY.md`
  (all 13 plans) — mechanisms this phase must preserve
- `.planning/config.json` — `nyquist_validation: true`, `security_enforcement: true`
- `pyproject.toml` — pytest/coverage configuration

### Secondary (MEDIUM confidence)
- CSS duplicate-selector count (Assumption A2) — a naive regex pass, cross-checked by hand for
  `.preview-frame__image` only; needs re-verification via the project's own parser before
  task-sizing CMP-08

### Tertiary (LOW confidence)
- None — this phase required no web search; every claim traces to the live codebase or
  `.planning/` documents already checked into the repository.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new dependency; stdlib templating choice is HIGH confidence (both
  options directly verified against the current template's content)
- Architecture: HIGH — every pattern above was read directly from current source, not
  inferred from the (stale) audit
- Pitfalls: HIGH — each pitfall traces to a specific line/function read in this session, not
  a general concern

**Research date:** 2026-09-27
**Valid until:** This research is tied to one specific commit of a fast-moving, actively
multi-phase codebase (Phase 39 runs in parallel on `server/`). Treat as valid only until the
next merge from `origin/main` or `claude/plan-phase-38`; re-measure file sizes/line counts
immediately before planning if more than a few days have passed or a merge has landed.
