# Phase 15: Per-direction themes, per-flight colour rules and roster-linked highlighting - Pattern Map

**Mapped:** 2026-09-06
**Files analyzed:** 9 (new + modified)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `server/plane/colour_rules.py` (new) | model / registry | CRUD (JSON file, atomic write) | `server/plane/manual_resolutions.py` | exact |
| `server/device_config.py` (modified: `theme_arriving`, `CLEAR_THEME_ARRIVING`, `normalise_theme_arriving()`) | config/model | CRUD (carry-forward-on-None contract) | `server/device_config.py`'s own `wake_interval_s` field (same file, sibling precedent) | exact |
| `server/poll_loop.py` (modified: `run_once()`, 2 call sites + 1 cache-prime) | controller / orchestrator | event-driven (one poll cycle) | `server/poll_loop.py`'s own existing `illustrations.set_override_state_dir()` / `manual_resolutions.set_manual_registry_state_dir()` priming calls, and its existing `theme_id` read | exact (self-extension) |
| `companion/pages/config_page.py` (modified: `theme_fieldset()` extended, new rules section functions, `render()`, `handle_post()`) | component (server-rendered HTML) | request-response | `theme_fieldset()` (chip grid), `quiet_hours_group()` (checkbox idiom), `display_group()` (absent-means-off semantics) — all in the same file | exact |
| Rules add/delete markup + list (new functions in `config_page.py` or a sibling, per D-10) | component | CRUD list + immediate POST | `companion/pages/airlines_page.py`'s `_manual_resolutions_section_html()` / `_manual_resolution_row_html()` / `_manual_resolution_table_html()` / `_manual_resolution_cards_html()` | exact |
| `companion/app.py` (modified: 2 new POST routes, `FLASH_MESSAGES`/`FLASH_ROLES`, `page_context()`) | route dispatch / controller | request-response | `companion/app.py`'s own `_handle_manual_resolve_post()` / `_handle_manual_resolution_delete()` and their dispatch branches | exact |
| `server/test_colour_rules.py` (new) | test | unit | `server/test_manual_resolutions.py` | exact |
| `server/test_poll_loop.py` (extended) | test | integration | existing file, extend in place | exact |
| `companion/test_config_page.py` (extended) | test | unit/integration | existing file, extend in place | exact |
| `scripts/run-all-tests.sh` (modified: register new harness) | config | batch | its own `HARNESSES` array | exact |

## Pattern Assignments

### `server/plane/colour_rules.py` (new registry module)

**Analog:** `server/plane/manual_resolutions.py` (full file read)

**Module docstring's import-cycle rule** (lines 27-30):
```python
This module imports `server.plane.illustrations` (for
`normalise_airline_key()` and `GENERIC_FALLBACK_FILENAME`) but must NEVER
import `server.plane.enrich` — that direction is reserved for
`enrich` to import *this* module (plan 13-03); the reverse would be an
import cycle.
```
Apply the equivalent rule for `colour_rules.py` (D-13, research-verified): it may import `server.device_config` (for `THEME_IDS` membership) plus stdlib only; it must NEVER import `server.plane.enrich`, `server.plane.detect`, `server.plane.illustrations`, `server.plane.manual_resolutions`, or `server.plane.render` — state this explicitly in the new module's own docstring, mirroring the paragraph above verbatim in structure.

**Allowlist regexes** (lines 76, 85, 99):
```python
_PREFIX_RE = re.compile(r"^[A-Z]{3}$")
_SAFE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_HOSTILE_NAME_RE = re.compile(r"[\\/]|\.\.")
```
Copy the *shape* (one compiled positive-allowlist regex per validated field), not these exact patterns — `colour_rules.py` needs its own three: callsign (`^[A-Z0-9]{2,8}$` after strip+upper, per RESEARCH.md Pattern 4/Open Question 1), hex (`^[0-9A-F]{6}$` after strip+upper), prefix (`^[A-Z]{3}$`, identical to `_PREFIX_RE` but duplicated locally per the leaf-import rule, not imported).

**`load_*`/`add_entry`/`delete_entry`/`entry_rows`/`set_*_state_dir` signatures:**
```python
def load_manual_resolutions(state_dir):                     # never raises; {} on any failure
def add_entry(state_dir, prefix, airline_name, now=None):   # returns ADD_* constant, never raises
def delete_entry(state_dir, prefix):                        # returns True/False, never raises
def entry_rows(registry):                                   # sorted defensive tuples for rendering
def set_manual_registry_state_dir(state_dir):                # process-global cache setter, poll-cycle only
def airline_name_for_prefix(prefix):                          # cache-only reader, never touches disk
```
`colour_rules.py`'s equivalents: `load_colour_rules(state_dir)`, `add_rule(state_dir, kind, key, theme_id, now=None) -> ADD_OK_NEW | ADD_OK_REPLACED | ADD_REJECTED_* | ADD_FAILED` (the **required deviation** — see below), `delete_rule(state_dir, kind, value) -> True/False`, `entry_rows(registry)` (or `rule_rows`), `set_colour_rules_state_dir(state_dir)`, `resolve_effective_theme_id(state, flight, device_cfg)` (reads the cache only, never touches disk — this is the D-13 resolver, not present in the manual_resolutions template at all, since that module has no resolution-order concept).

**`_WRITE_LOCK` usage** (lines 129-133, applied at every mutation site in `add_entry`/`delete_entry`):
```python
_WRITE_LOCK = threading.Lock()
...
with _WRITE_LOCK:
    registry = load_manual_resolutions(state_dir)
    if normalised_prefix not in registry and len(registry) >= MANUAL_RESOLUTION_MAX_ENTRIES:
        return ADD_REJECTED_FULL
    ...
```
Copy verbatim as the shape: one module-level `threading.Lock()`, wrapping the ENTIRE load-check-mutate-write sequence (not just the final `os.replace()`), in both `add_rule()` and `delete_rule()`. This is also where `colour_rules.py`'s added-vs-replaced check must happen (`(kind, value) in registry`, tested inside this same lock, before mutating) — see Pitfall 4 below.

**Result-code constants** (lines 103-109):
```python
ADD_OK = "ok"
ADD_REJECTED_PREFIX = "rejected_prefix"
ADD_REJECTED_NAME_EMPTY = "rejected_name_empty"
ADD_REJECTED_NAME_TOO_LONG = "rejected_name_too_long"
ADD_REJECTED_NAME_RESERVED = "rejected_name_reserved"
ADD_REJECTED_FULL = "rejected_full"
ADD_FAILED = "failed"
```
`colour_rules.py`'s vocabulary must extend this shape with `ADD_OK_NEW` / `ADD_OK_REPLACED` in place of the single `ADD_OK` (RESEARCH.md's named deliberate extension, needed for the `rule_added`/`rule_replaced` flash split in 15-UI-SPEC.md). Plus `ADD_REJECTED_KIND`, `ADD_REJECTED_KEY`, `ADD_REJECTED_THEME`, `ADD_REJECTED_FULL`, `ADD_FAILED` for the three-field validation ladder (kind, key/value, theme id). These are NOT flash keys themselves — the HTTP layer maps them (see `companion/app.py` pattern below).

**tmp-write-then-`os.replace()` block with `except` cleanup** (lines 375-390, inside `add_entry`):
```python
path = manual_resolutions_path(state_dir)
tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
try:
    os.makedirs(state_dir, exist_ok=True)
    with open(tmp, "w") as fh:
        json.dump(registry, fh, indent=1)
    os.replace(tmp, path)
except Exception:
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    return ADD_FAILED
```
Copy verbatim (the pid/thread-scoped temp filename is load-bearing under `ThreadingHTTPServer` — a single fixed `path + ".tmp"` would let two concurrent writers interleave). `delete_rule()` needs the identical block, returning `False` instead of `ADD_FAILED` on exception (mirrors `delete_entry()`, lines ~430-443).

**Never-raising `load_*()` shape** (docstring + body, lines 208-286): parse JSON with `except (OSError, ValueError): data = {}`; `if not isinstance(data, dict): data = {}`; rebuild every entry from scratch through its own `normalise_*()` gate, dropping (never coercing) anything that fails; hard `break` at `MANUAL_RESOLUTION_MAX_ENTRIES`-equivalent cap (never `continue`-scan the remainder); print (not raise) a drop-count warning when entries are silently dropped. Recommended nested-by-kind JSON shape (RESEARCH.md Pattern 3, Assumption A5, Claude's discretion):
```json
{"callsign": {"AFR1234": {"theme_id": "white", "created_at": "..."}},
 "hex": {"3944F2": {"theme_id": "blue", "created_at": "..."}},
 "prefix": {"AFR": {"theme_id": "red", "created_at": "..."}}}
```

**The resolver function** (new — no direct analog, but the shape is dictated by RESEARCH.md's Code Examples section verbatim):
```python
def resolve_effective_theme_id(state, flight, device_cfg):
    """Order (D-09/D-04): exact callsign rule > hex rule > prefix rule >
    arrivals override (only when state == "arriving") > base theme.
    Never raises; always returns a THEME_IDS member. Reads the process-
    global rules cache set once per cycle by set_colour_rules_state_dir()
    — never touches disk itself."""
```
See RESEARCH.md lines 318-352 for the full illustrative body (callsign/hex/prefix lookup chain, then arrivals override, then base `device_cfg["theme"]`).

---

### `server/poll_loop.py` (resolver seam — 2 call sites that display a flight, 4 that do not)

**Analog:** the file's own existing structure (verified line-by-line in this session).

**Cache-priming calls to extend** (existing, ~lines 732-733):
```python
illustrations.set_override_state_dir(state_dir)
manual_resolutions.set_manual_registry_state_dir(state_dir)
```
Add a third line beside these two: `colour_rules.set_colour_rules_state_dir(state_dir)`. This is the ONLY piece of the new feature safe to hoist to the top of `run_once()`.

**The existing once-per-cycle base-theme read** (~lines 741-742, do NOT model the resolver call on this):
```python
device_cfg = device_config.load_device_config(state_dir)
theme_id = device_cfg["theme"]
```

**Six `build_canvas()` call sites — exactly two need the resolver:**

| Approx. line | Branch | Displays a flight? | Resolver? |
|---|---|---|---|
| ~824 | Hold early-return (quiet_hours/display_off) | No | No — bare `theme_id` |
| ~1027 | Flight-detected, `confirmed_state is None` → `"empty"` | No | No — bare `theme_id` |
| **~1109** | **Flight-detected, `confirmed_state` resolved** | **Yes** | **Yes** |
| **~1188** | **Held/re-render branch, `confirmed_state is not None`** | **Yes** | **Yes** |
| ~1201 | Held/re-render branch, `confirmed_state is None` → `"empty"` | No | No — bare `theme_id` |
| ~1235 | Nothing ever detected → `"empty"` | No | No — bare `theme_id` |

**Insertion pattern at each of the two flagged sites** (immediately before the existing `render.build_canvas(...)` call, RESEARCH.md's illustrative diff):
```python
effective_theme_id = colour_rules.resolve_effective_theme_id(render_state, current_flight, device_cfg)
canvas = render.build_canvas(
    current_flight, render_state, route=route, ...,
    theme_id=effective_theme_id, ...,
)
```
Existing call site at ~1109 to modify (verified in this session):
```python
canvas = render.build_canvas(
    current_flight,
    render_state,
    ...
    previous_state=previous_confirmed_state,
    theme_id=theme_id,   # <-- change to theme_id=effective_theme_id
    ...
)
```
Existing call site at ~1188 (held branch, same change):
```python
held_canvas = render.build_canvas(
    current_flight,
    render_state,
    ...
    previous_state=previous_confirmed_state,
    theme_id=theme_id,   # <-- change to theme_id=effective_theme_id
    ...
)
```
The other four sites (~824, ~1027, ~1201, ~1235) keep `theme_id=theme_id` completely unchanged — do not touch them.

**Ordering trap (do not hoist):** `render_state`/`current_flight` are not settled until deep inside each branch (`runway_config.infer_from_flight()` at ~1016, or `poll_state.get("last_confirmed_state")` at ~1147/916). Compute `effective_theme_id` at the two call sites only, never near the top-of-function `device_cfg`/`theme_id` read.

---

### `server/device_config.py` (clearable `theme_arriving` field)

**Analog:** the file's own `wake_interval_s` field (same file, sibling precedent) — verified read of `normalise_wake_interval_s()`, `load_device_config()`, `save_device_config()`.

**`normalise_wake_interval_s()`** (the degrade-to-`None` shape to mirror, NOT the degrade-to-default shape `normalise_theme_id()` uses):
```python
def normalise_wake_interval_s(value):
    """... Unlike every sibling normaliser in this module, `None` here does NOT mean
    "degraded to the documented default" ... It means "never explicitly set" ..."""
    if isinstance(value, int) and not isinstance(value, bool) and WAKE_INTERVAL_MIN_S <= value <= WAKE_INTERVAL_MAX_S:
        return value
    return None
```
`normalise_theme_arriving(value)` follows this exact shape: `if isinstance(value, str) and value in THEMES: return value` else `return None` (never `DEFAULT_THEME_ID`, per D-04).

**`load_device_config()`'s all-keys-always-present contract** (lines 524-556): add `"theme_arriving": normalise_theme_arriving(data.get("theme_arriving"))` as a new dict entry — `load_device_config()` must keep returning every key unconditionally, this is just one more.

**`save_device_config()`'s carry-forward-on-`None` block** (line 631, the pattern every field follows):
```python
"wake_interval_s": wake_interval_s if wake_interval_s is not None else current["wake_interval_s"],
```
`theme_arriving` needs a THIRD state beyond this two-state contract — RESEARCH.md's recommended sentinel pattern (Pattern 2, verified against `companion/pages/health_page.py`/`history_page.py`'s existing `_DB_UNAVAILABLE = object()` idiom):
```python
CLEAR_THEME_ARRIVING = object()  # sentinel: "explicitly unset", distinct from
                                  # None ("caller didn't supply this parameter").
...
if (theme_arriving is not None and theme_arriving is not CLEAR_THEME_ARRIVING
        and theme_arriving not in THEMES):
    raise ValueError("unknown theme_arriving id %r (expected one of %r or None)" % (theme_arriving, THEME_IDS))
...
new_config["theme_arriving"] = (
    None if theme_arriving is CLEAR_THEME_ARRIVING
    else theme_arriving if theme_arriving is not None
    else current["theme_arriving"]
)
```
This sentinel is the ONLY place in the write path that needs to exist — `load_device_config()` never sees it.

---

### `companion/pages/config_page.py` (checkbox + second chip grid)

**Analog:** `theme_fieldset()` (lines 241-361, this same file) for the chip-grid markup to instantiate a second time; `quiet_hours_group()` (lines 521-575) for the `settings-checkbox` idiom; `display_group()` for the absent-means-off precedent (same shape as `quiet_hours_group`).

**Chip markup to duplicate as a second `<div class="theme-chip-grid theme-chip-grid--arrivals" data-arrival-grid>`** (lines 316-350, the per-theme-id `<label>` loop):
```python
chips.append(
    '<label class="%s">'
    '<input type="radio" name="theme" value="%s" class="visually-hidden"%s>'
    '<img class="theme-chip__preview" src="%s%s.png" alt="%s" '
    'width="320" height="120" loading="lazy" style="background:%s">'
    '<span class="theme-chip__body">...</span>'
    '<span class="theme-chip__check">%s<span class="visually-hidden">Selected</span></span>'
    "</label>"
    % (chip_class, escaped_id, checked, THEME_PREVIEW_ROUTE_PREFIX, escaped_id, ...)
)
```
The second grid uses `name="theme_arriving"` instead of `name="theme"`, `checked` computed against the *effective* arrivals theme (`theme_arriving` if set, else `theme`), otherwise byte-identical markup — same `/theme-preview/{id}.png` route, no per-direction preview variant.

**`settings-checkbox` idiom** (lines 557-575, `quiet_hours_group()`):
```python
checked = " checked" if current_enabled else ""
...
'<label class="settings-checkbox">'
'<input type="checkbox" name="quiet_hours_enabled" value="%s"%s> Enable quiet hours'
"</label>"
```
The new checkbox: `<label class="settings-checkbox"><input type="checkbox" id="theme-arriving-toggle" name="theme_arriving_enabled" value="on"%s> Use a different theme for arrivals</label>` — `id="theme-arriving-toggle"` is required by the UI-SPEC's `:has()` CSS reveal selector, unlike the three existing checkboxes which need no `id`.

**`render()`'s section-assembly list** (lines 962-991): `theme_fieldset(current_theme_id)` is the first call in the returned tuple — this call must now also receive `current_theme_arriving` (or the fieldset function reads it directly off `ctx`/`device_cfg`) to render the second grid inline within the SAME `.theme-status` card (per UI-SPEC's Section Anatomy §1 — do not make it a separate `<div>`/section). The new Rules `<section>` is appended per UI-SPEC's placement recommendation (immediately after `</form>` closes, in Poll's current slot, pushing Poll one section later) — see `render()`'s existing `+ '<section class="page-section">'... Poll ...` block (lines 973-976) as the template for the new Rules `<section class="page-section">` wrapper (no `data-dirty-section` attribute, matching Poll's own un-tracked status).

**`handle_post()`'s membership-check-then-explicit-branch shape** (lines 1110-1148, the pattern every field in this handler follows — reuse verbatim for the two new fields):
```python
if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
    return FLASH_SAVE_FAILED
...
if submitted_qh_enabled is None:
    quiet_hours_enabled = False
elif submitted_qh_enabled == QUIET_HOURS_CHECKBOX_VALUE:
    quiet_hours_enabled = True
else:
    return FLASH_SAVE_FAILED
```
New logic (per RESEARCH.md Pattern 2 / Pitfall 3 — branch on the CHECKBOX, never on `theme_arriving`'s presence, since the second grid is always rendered so `form.get("theme_arriving")` is always a valid theme id string):
```python
submitted_arriving_enabled = form.get("theme_arriving_enabled")
submitted_theme_arriving = form.get("theme_arriving")
if submitted_theme_arriving is not None and submitted_theme_arriving not in device_config.THEME_IDS:
    return FLASH_SAVE_FAILED
if submitted_arriving_enabled == ARRIVING_CHECKBOX_VALUE:
    theme_arriving = submitted_theme_arriving
else:
    theme_arriving = device_config.CLEAR_THEME_ARRIVING
...
device_config.save_device_config(..., theme_arriving=theme_arriving)
```
Then extend the existing `try: device_config.save_device_config(...) except (ValueError, OSError): return FLASH_SAVE_FAILED` call (lines 1140-1148) with this one extra kwarg — the all-or-nothing rejection contract is unchanged.

---

### Rules editor markup (add form + list + delete rows)

**Analog:** `companion/pages/airlines_page.py`'s manual-resolutions section (lines 956-1150+, `_manual_delete_action()`, `_manual_resolution_row_html()`, `_manual_resolution_table_html()`, `_manual_resolution_cards_html()`, `_manual_resolutions_section_html()`).

**Delete-action-URL builder** (line 956-961):
```python
def _manual_delete_action(prefix):
    return "%s%s%s" % (MANUAL_DELETE_ROUTE_PREFIX, escape_html(prefix), MANUAL_DELETE_ROUTE_SUFFIX)
```
Rules version needs TWO path segments (store keyed on `(kind, value)`, per D-09): `def _rule_delete_action(kind, value): return "%s%s/%s%s" % (RULES_ROUTE_PREFIX, escape_html(kind), escape_html(value), RULES_DELETE_SUFFIX)` — matching UI-SPEC's stated route shape `/settings/rules/{kind}/{value}/delete`.

**Route/flash-key constants** (lines 218-220, 265-273):
```python
RESOLVE_ROUTE = "/airlines/resolve"
MANUAL_DELETE_ROUTE_PREFIX = "/airlines/manual-resolutions/"
MANUAL_DELETE_ROUTE_SUFFIX = "/delete"
MANUAL_SECTION_HEADING = "Manually resolved prefixes"
MANUAL_RESOLUTION_HEADERS = ("Prefix", "Airline name", "Added", "Status", "Delete")
```
Rules equivalents: `RULES_ADD_ROUTE = "/settings/rules/add"`, `RULES_DELETE_ROUTE_PREFIX = "/settings/rules/"`, `RULES_DELETE_ROUTE_SUFFIX = "/delete"`, `RULES_SECTION_HEADING = "Per-flight colour rules"`, `RULE_HEADERS = ("Kind", "Key", "Theme", "Added", "")` (per UI-SPEC's copy deck — trailing empty `<th>` for delete, matching `MANUAL_RESOLUTION_HEADERS`'s own trailing "Delete" text convention, though UI-SPEC specifies no header text for that column).

**Table/card pairing (desktop `>=960px` table, mobile `<960px` cards, in DOM order cards-then-table)** — `_manual_resolutions_section_html()`'s own documented load-bearing order (its own comment): `.data-cards` must render BEFORE `.data-table-wrap` in the DOM because `.data-cards ~ .data-table-wrap`'s sibling-combinator CSS toggle depends on exactly that order. Copy this ordering verbatim for the rules list — UI-SPEC's own "Rules List Shape" section states the identical requirement.

**Swatch dot reuse** (`_palette_hex()` from `config_page.py`, imported into whichever module renders the rules list): `'<span class="theme-swatch__chip" style="background:%s"></span>' % _palette_hex(theme["departing_index"])`.

**Empty state** (matches `layout.empty_state(MANUAL_EMPTY_HEADING, MANUAL_EMPTY_BODY)`'s call shape, lines ~1151): `layout.empty_state(RULES_EMPTY_HEADING, RULES_EMPTY_BODY)`.

---

### `companion/app.py` (immediate add/delete POST routes + dispatch + flash handling)

**Analog:** `_handle_manual_resolve_post()` (lines 1325-1424) and `_handle_manual_resolution_delete()` (lines 1426-1461), plus their dispatch branches (lines 1732-1747).

**Add-route handler shape** (validate → mutate → map result to flash → redirect, lines 1382-1424):
```python
form = self.read_form()
state_dir = self.args.state_dir
row = unresolved_row_for_prefix(state_dir, form.get("prefix"))
if row is None:
    return self.redirect("%s?flash=%s" % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_PREFIX_STALE)))
prefix = row[0]
result = manual_resolutions.add_entry(state_dir, prefix, form.get("airline_name"))
if result == manual_resolutions.ADD_OK:
    ...
    return self.redirect(...)
if result in (manual_resolutions.ADD_REJECTED_PREFIX, manual_resolutions.ADD_REJECTED_NAME_EMPTY):
    flash_key = FLASH_KEY_MANUAL_NAME_EMPTY
elif result == manual_resolutions.ADD_REJECTED_NAME_TOO_LONG:
    flash_key = FLASH_KEY_MANUAL_NAME_TOO_LONG
...
else:
    flash_key = FLASH_KEY_MANUAL_SAVE_FAILED   # unrecognised result must still speak
return self.redirect("%s?resolve=%s&flash=%s" % (...))
```
Rules add handler: read `rule_kind`/`rule_key`/`rule_theme_id` from `self.read_form()`, call `colour_rules.add_rule(state_dir, kind, key, theme_id)`, branch on `ADD_OK_NEW -> FLASH_KEY_RULE_ADDED`, `ADD_OK_REPLACED -> FLASH_KEY_RULE_REPLACED`, `ADD_REJECTED_* -> FLASH_KEY_RULE_KEY_INVALID` (or `_THEME_INVALID`/`_KIND_INVALID` collapsed to the same generic copy per UI-SPEC's stated asymmetry — a crafted kind/theme is a hostile-request shape, reuses `rule_save_failed`), `ADD_REJECTED_FULL -> FLASH_KEY_RULE_REGISTRY_FULL`, `ADD_FAILED -> FLASH_KEY_RULE_SAVE_FAILED`, `else -> FLASH_KEY_RULE_SAVE_FAILED` (never silently pass through). Redirect to `SETTINGS_ROUTE` (not `AIRLINES_ROUTE`), no `resolve=` query param equivalent needed (no two-step flow here).

**Delete-route handler shape** (lines 1426-1461, idempotent-delete-is-success pattern):
```python
prefix = manual_resolutions.normalise_prefix(key)
if prefix is None:
    return self.send_html(404, self._not_found_page())
state_dir = self.args.state_dir
existed = prefix in manual_resolutions.load_manual_resolutions(state_dir)
deleted = manual_resolutions.delete_entry(state_dir, prefix)
if not deleted and existed:
    return self.redirect("%s?flash=%s" % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_DELETE_FAILED)))
return self.redirect(airlines_page.AIRLINES_ROUTE)
```
Rules delete handler: normalise BOTH path segments (`kind`, `value`) before use — 404 if either fails its own kind-specific normaliser; `colour_rules.delete_rule(state_dir, kind, value)`; same existed/deleted/flash logic; redirect to `SETTINGS_ROUTE`.

**Dispatch branches to add** (mirrors lines 1732-1747 exactly):
```python
if path == airlines_page.RESOLVE_ROUTE:
    if not self.require_session():
        return None
    return self._handle_manual_resolve_post()

if path.startswith(airlines_page.MANUAL_DELETE_ROUTE_PREFIX) and path.endswith(
        airlines_page.MANUAL_DELETE_ROUTE_SUFFIX):
    if not self.require_session():
        return None
    key = path[len(airlines_page.MANUAL_DELETE_ROUTE_PREFIX):-len(airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)]
    return self._handle_manual_resolution_delete(key)
```
New: `if path == RULES_ADD_ROUTE: ... return self._handle_rule_add()`; then a startswith/endswith branch for `RULES_DELETE_ROUTE_PREFIX`/`RULES_DELETE_ROUTE_SUFFIX`, splitting the middle segment on `/` once to recover `(kind, value)` — UI-SPEC's stated `/settings/rules/{kind}/{value}/delete` shape needs one extra `.split("/", 1)` beyond the single-segment manual-resolutions precedent.

**`FLASH_MESSAGES`/`FLASH_ROLES` registration** (lines 187-206, 200+, 263+ — the constant-aliasing + dict-literal pattern):
```python
FLASH_KEY_MANUAL_RESOLVED = airlines_page.FLASH_MANUAL_RESOLVED
...
FLASH_MESSAGES = { ... FLASH_KEY_MANUAL_RESOLVED: "...", ... }
FLASH_ROLES = { ... FLASH_KEY_MANUAL_RESOLVED: "status", ... }
```
Add 7 new entries per UI-SPEC's Flash Messages table: `rule_added` (status), `rule_replaced` (status), `rule_key_invalid` (alert), `rule_registry_full` (alert), `rule_save_failed` (alert), `rule_deleted` (status), `rule_delete_failed` (alert).

**`page_context()` fresh-read pattern** (line 897):
```python
"manual_resolutions": manual_resolutions.load_manual_resolutions(state_dir),
```
Add: `"colour_rules": colour_rules.load_colour_rules(state_dir),` — read fresh per request, NEVER the poll-cycle cache (the module docstring's own caching warning, copied verbatim into `colour_rules.py`'s docstring per D-12).

---

### `server/test_colour_rules.py` (new test harness)

**Analog:** `server/test_manual_resolutions.py` (full file read).

**`check()`/`EXPECTED_CHECK_COUNT` ledger pattern** (lines 1-40 and the closing block):
```python
#!/usr/bin/env python3
"""Contract harness for server/plane/colour_rules.py ...
Stdlib-only, plus the module under test and its own dependency
(server.device_config). Every fixture is a tempfile.TemporaryDirectory(),
never a shared/real state dir. Exits 0 only when every check below
passes; any failure (or exception) exits 1.
"""
...
# Initial value for this file, introduced by phase 15. Re-derived by
# RUNNING the harness (not by arithmetic), per this repo's own documented
# discipline.
EXPECTED_CHECK_COUNT = <N>
...
results = []
def check(name, fn):
    ...
...
total = len(results)
passed = sum(1 for _, ok in results if ok)
print("colour_rules: %d/%d checks pass" % (passed, total))
return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1

if __name__ == "__main__":
    sys.exit(main())
```
The hostile-input-sweep check pattern (closing block of `test_manual_resolutions.py`) is directly reusable for D-08/T-13-02 coverage — one check iterating a list of hostile values per key kind, asserting `add_rule()` rejects every one and the registry stays empty afterward.

**Registration** (`scripts/run-all-tests.sh`'s `HARNESSES` array, lines 43-60):
```bash
HARNESSES=(
    server/test_config_history.py
    server/test_dither.py
    ...
    server/test_manual_resolutions.py
    ...
)
```
Add `server/test_colour_rules.py` as a new line in this array (alphabetical position after `server/test_config_history.py`, before `server/test_dither.py`, matching the array's existing sort order) — update the header comment's "17-file enumeration" note to the new count, following the same style as the existing "phase 13 plan 01 added server/test_manual_resolutions.py" annotation.

## Shared Patterns

### Atomic JSON registry writes under `ThreadingHTTPServer`
**Source:** `server/plane/manual_resolutions.py` lines 129-133 (`_WRITE_LOCK`) and 375-390 (tmp-write-then-`os.replace()`)
**Apply to:** `server/plane/colour_rules.py`'s `add_rule()`/`delete_rule()` — copy the pid/thread-scoped temp filename, the module-level lock wrapping the whole load-check-mutate-write sequence, and the except-cleanup-then-return-failure-code shape verbatim.

### Never-raising `normalise_*()` / never-raising `load_*()`
**Source:** `server/device_config.py`'s `normalise_wake_interval_s()`; `server/plane/manual_resolutions.py`'s `load_manual_resolutions()`
**Apply to:** every new normaliser in `colour_rules.py` (callsign/hex/prefix/theme-id-membership) and `device_config.py`'s new `normalise_theme_arriving()` — degrade to `None`/drop the entry, never raise, never a partial/coerced value.

### Membership-test-before-use, never trust a request value as a dict key or path
**Source:** `companion/pages/config_page.py`'s `handle_post()` (lines 1110-1148); `server/plane/manual_resolutions.py`'s `_SAFE_KEY_RE`/`_HOSTILE_NAME_RE` (T-13-02)
**Apply to:** `_handle_rule_add()`/`_handle_rule_delete()` in `companion/app.py`, and `add_rule()`/`load_colour_rules()` in `colour_rules.py` — validate before persisting AND re-validate on every read.

### Absent-checkbox-means-off / explicit-branch-per-field
**Source:** `companion/pages/config_page.py`'s `handle_post()`, the `submitted_qh_enabled`/`QUIET_HOURS_CHECKBOX_VALUE` three-way branch (absent → `False`; equals its own `*_CHECKBOX_VALUE` → `True`; anything else → reject whole submission)
**Apply to:** the new `theme_arriving_enabled` checkbox — but note the DIVERGENCE (RESEARCH.md Pitfall 2/3): unlike every existing checkbox, "unchecked" here must map to the `CLEAR_THEME_ARRIVING` sentinel, not to a plain `False`/`None`, and the branch must key off the checkbox field itself, never off `theme_arriving`'s presence (which is always present in the always-rendered second grid).

### Immediate POST outside the dirty-bar form, idempotent delete-is-success
**Source:** `companion/app.py`'s `_handle_manual_resolve_post()` / `_handle_manual_resolution_delete()`, and their dispatch branches
**Apply to:** the two new rules routes — same `require_session()` gate reused (no new auth mechanism), same "unrecognised result must still produce a flash, never silently pass through" discipline, same "deleting an already-absent key is success, not error" idempotence.

### Locked-English module constants, one caption per section
**Source:** `companion/pages/config_page.py`'s `THEME_SECTION_CAPTION`/`QUIET_HOURS_SECTION_CAPTION`/etc.; `companion/pages/airlines_page.py`'s `MANUAL_SECTION_CAPTION`/`MANUAL_EMPTY_HEADING`/etc.
**Apply to:** every new copy string this phase introduces — `RULES_SECTION_HEADING`, `RULES_SECTION_CAPTION`, `RULE_VALUE_HINT`, `RULES_EMPTY_HEADING`, `RULES_EMPTY_BODY`, the checkbox label, and all 7 flash message templates — verbatim text is already locked in `15-UI-SPEC.md`'s Copywriting Contract table; do not paraphrase it.

## No Analog Found

None — every file this phase touches has a direct, verified analog in the existing codebase (this phase adds zero new external dependencies and zero new render code, per RESEARCH.md's own Summary).

## Metadata

**Analog search scope:** `server/plane/`, `server/device_config.py`, `server/poll_loop.py`, `companion/pages/`, `companion/app.py`, `server/test_*.py`, `scripts/run-all-tests.sh` — all directly read in this session, not inferred.
**Files scanned:** `server/plane/manual_resolutions.py` (full), `server/device_config.py` (targeted sections), `server/poll_loop.py` (targeted grep + line ranges), `companion/pages/config_page.py` (targeted sections), `companion/pages/airlines_page.py` (targeted sections), `companion/app.py` (targeted sections), `server/test_manual_resolutions.py` (full), `scripts/run-all-tests.sh` (targeted).
**Pattern extraction date:** 2026-09-06
