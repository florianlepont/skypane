# Phase 13: Add an illustration for an unidentified flight from the companion web interface - Pattern Map

**Mapped:** 2026-09-06
**Files analyzed:** 9 (2 new, 7 modified) + 5 test harnesses gaining checks
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `server/plane/manual_resolutions.py` (NEW) | model / storage module | CRUD (file-backed) | `server/device_config.py` | exact (load/save contract) |
| `server/test_manual_resolutions.py` (NEW) | test | batch/check-harness | `server/test_enrich.py` | exact (harness shape) |
| `server/plane/enrich.py` (MODIFIED) | service / pure-function module | transform, request-response | itself (existing `airline_from_callsign`/`resolve_route`) | exact (same file, extend in place) |
| `server/poll_loop.py` (MODIFIED) | orchestrator / batch cycle | event-driven (poll cycle) | itself (existing `illustrations.set_override_state_dir()` call site + `unresolved_prefixes` block) | exact |
| `companion/app.py` (MODIFIED) | controller (HTTP routes) | request-response, file-I/O (upload) | itself (`_handle_illustration_replace()`, `_illustration_filenames()`, `POST /settings` urlencoded handler) | exact |
| `companion/pages/airlines_page.py` (MODIFIED) | component (SSR page module) | request-response | itself (`_lightbox_replace_form_html()`) + `companion/pages/health_page.py` (`_registry_table_html()`/`_registry_cards_html()` pairing) | exact / role-match |
| `companion/pages/health_page.py` (MODIFIED) | component (SSR page module) | request-response | itself (`_registry_row_html()`, `_READ_ONLY_NOTE`, `_SOURCE_ROWS`) | exact |
| `scripts/run-all-tests.sh` (MODIFIED) | config (CI harness list) | batch | itself (the `HARNESSES` array) | exact |
| `companion/test_status_pages.py`, `companion/test_companion_app.py`, `server/test_enrich.py`, `server/test_poll_loop.py` (MODIFIED) | test | batch/check-harness | themselves (`EXPECTED_CHECK_COUNT` + `check()` calls) | exact |

## Pattern Assignments

### `server/plane/manual_resolutions.py` (NEW — model/storage, CRUD)

**Analog:** `server/device_config.py` (lines 524-648, read via `sed -n '500,650p'`)

**Never-raising loader pattern** (`device_config.py:524-556`):
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
        ...
    }
```
Copy this shape exactly for `load_manual_resolutions(state_dir)`: missing/unreadable/malformed/non-dict file → `{}`; every per-entry field passes through a `normalise_*` gate; entries not shaped like `{"airline_name": str, "created_at": str}` are dropped (mirrors `note_unresolved_prefix()`'s own defensive-entry discipline, `enrich.py:796`, not `device_config`'s scalar shape — this registry is a dict-of-dicts, not fixed keys).

**Validate-before-write + tmp/replace pattern** (`device_config.py:583-648`):
```python
if theme is not None and theme not in THEMES:
    raise ValueError("unknown theme id %r (expected one of %r)" % (theme, THEME_IDS))
...
current = load_device_config(state_dir)
new_config = { ... current[k] if arg is None else arg ... }

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
Use this verbatim for `add_entry()`/`delete_entry()`'s write body (D-05 explicitly requires "following `device_config.json`'s contract exactly"). Difference from `device_config`: validate BEFORE touching the file and raise `ValueError` on read (same as here) but `add_entry`/`delete_entry` should return a result/flash-key rather than raise, since callers are `companion/app.py` route handlers that need a flash key, not an exception — mirror `manual_resolutions.py`'s own docstring plan from RESEARCH.md Pattern 5 instead of `device_config`'s raise-on-invalid style for the companion-facing entry points.

**Entry cap precedent** — reuse `enrich.py`'s `UNRESOLVED_PREFIX_MAX_ENTRIES = 200` naming convention (`enrich.py`, "T-oz9-01" comment block) for `MANUAL_RESOLUTION_MAX_ENTRIES = 200`.

---

### `server/test_manual_resolutions.py` (NEW — test)

**Analog:** `server/test_enrich.py` (lines 1-90, `sed -n '1,60p'` + grep for `EXPECTED_CHECK_COUNT`)

**Harness skeleton to copy**:
```python
#!/usr/bin/env python3
"""Contract harness for ... Exits 0 only when every check below passes;
any failure (or exception - none is ever swallowed into a pass) exits 1.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = <N>

def main():
    results = []
    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:
            ok, reason = False, "raised %r" % (exc,)
        results.append((name, ok, reason))
    ...
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    ...
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1

if __name__ == "__main__":
    sys.exit(main())
```
This is the exact `check()`/`EXPECTED_CHECK_COUNT`/`main()` shape used by every harness in this repo (`test_enrich.py:1128`: `return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1`). Use `tempfile.TemporaryDirectory()` for `state_dir` fixtures the way `test_enrich.py`'s own fixture loader (`load_fixture`/`FIXTURES_DIR`) or `server/test_illustrations.py`'s tmp-dir tests do (grep `tempfile` there for the exact idiom if state-dir fixtures are needed).

---

### `server/plane/enrich.py` (MODIFIED — service, pure transform)

**Analog:** itself, `airline_from_callsign()` / `resolve_route()` / `note_unresolved_prefix()` (`enrich.py:615-800`)

**Existing pure lookup to extend without breaking its signature** (`enrich.py:615-636`):
```python
def airline_from_callsign(callsign):
    """... Never raises (T-hyy-02). ... Pure, no I/O, no network ..."""
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None
    if not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None
    return _ICAO_AIRLINE_PREFIXES.get(normalised[:3])
```
Keep this signature/behavior additive per RESEARCH.md Pattern 1: add a sibling `airline_source_from_callsign(callsign) -> (name, source)` that checks `_ICAO_AIRLINE_PREFIXES` first (source `"static"`), then the manual registry (source `"manual"`) via a read-only accessor into a process-cached dict (mirroring `illustrations.py`'s `_override_state_dir`/`set_override_state_dir()` pattern below). `airline_from_callsign()` becomes a one-line wrapper: `return airline_source_from_callsign(callsign)[0]`.

**Existing route-shape builder to reuse unchanged** (`enrich.py:639-661`):
```python
def airline_only_route(airline_name):
    if not isinstance(airline_name, str) or not airline_name:
        return None
    return {
        "airline_name": airline_name,
        "origin_iata": None, "origin_city": None,
        "destination_iata": None, "destination_city": None,
        "callsign_iata": None,
    }
```
D-02's `"manual"` source produces this exact same shape — no new route dict shape needed.

**`resolve_route()`'s existing four-way branch to extend to five** (`enrich.py:663-695`):
```python
def resolve_route(callsign, cache, transport=None, timeout=DEFAULT_TIMEOUT):
    normalised = normalise_callsign(callsign)
    was_cached = normalised is not None and normalised in cache
    route = lookup_route(callsign, cache, transport=transport, timeout=timeout)
    if route is not None:
        return route, ("cache_hit" if was_cached else "fresh_hit")
    airline_name = airline_from_callsign(callsign)
    if airline_name:
        return airline_only_route(airline_name), "airline_only"
    return None, "miss"
```
Change the fallback branch to call `airline_source_from_callsign(callsign)` and map `"static"` → `"airline_only"` (unchanged string, preserves Health's existing gloss), `"manual"` → `"manual"` (new source string, D-02).

**Never-raising registry-mutation pattern to mirror for `clear_resolved_unresolved_prefix()`** (`enrich.py:754-800`, `note_unresolved_prefix()`):
```python
def note_unresolved_prefix(callsign, registry, now=None):
    if not isinstance(registry, dict):
        return None
    normalised = normalise_callsign(callsign)
    if normalised is None:
        return None
    if not _AIRLINE_PREFIX_SHAPE_RE.match(normalised):
        return None
    if airline_from_callsign(callsign) is not None:
        return None
    prefix = normalised[:3]
    if now is None:
        ...
```
D-14's `clear_resolved_unresolved_prefix(callsign, registry)` is the structural inverse of this function — same shape-gate order, same `isinstance(registry, dict)` guard, same never-raises discipline (see RESEARCH.md Pattern 6 for the exact recommended body).

---

### `server/poll_loop.py` (MODIFIED — orchestrator, event-driven cycle)

**Analog:** itself, the existing `illustrations.set_override_state_dir(state_dir)` call site (`poll_loop.py:717`) and the existing `unresolved_prefixes` bookkeeping block (`poll_loop.py:1017-1051`, `sed -n '1010,1060p'`)

**Setter-call site to mirror** (`poll_loop.py:706-717`):
```python
os.makedirs(state_dir, exist_ok=True)
# D-01/D-02 (quick task 260902-v26): configure the illustration override
# resolver from THIS cycle's own state_dir, here rather than in main() -
# run_once() is the single entry point both the systemd oneshot AND
# companion/app.py's POST /poll-now in-process trigger go through ...
illustrations.set_override_state_dir(state_dir)
```
Add `manual_resolutions.set_manual_registry_state_dir(state_dir)` immediately beside this line, same reasoning (single entry point for both the systemd oneshot and companion's in-process trigger).

**Existing `unresolved_prefixes` block to extend** (`poll_loop.py:1017-1044`):
```python
route, route_source = enrich.resolve_route(current_flight.get("callsign"), cache)
enrich.trim_cache(cache)
poll_state["enrichment_cache"] = cache
unresolved_prefixes = poll_state.get("unresolved_prefixes")
if not isinstance(unresolved_prefixes, dict):
    unresolved_prefixes = {}
if route_source == "miss":
    unknown_prefix = enrich.note_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)
enrich.trim_unresolved_prefixes(unresolved_prefixes)
poll_state["unresolved_prefixes"] = unresolved_prefixes
```
D-14 inserts `enrich.clear_resolved_unresolved_prefix(current_flight.get("callsign"), unresolved_prefixes)` unconditionally, BEFORE the `if route_source == "miss":` line and before `trim_unresolved_prefixes()`/the write-back, per RESEARCH.md Pattern 6's exact ordering.

---

### `companion/app.py` (MODIFIED — controller, request-response + file-I/O)

**Analog:** itself, `_illustration_filenames()` (`app.py:450-461`), `_handle_illustration_replace()` (`app.py:1082-1198` per docstring numbering; verified body at the read range above), `parse_single_uploaded_file()` (`app.py:464-542`)

**Import-time frozenset to widen to a per-request function** (`app.py:450-461`):
```python
def _illustration_filenames():
    """... `target_filenames()` performs no I/O, but materialising it
    once at import time ... makes the "one closed, server-controlled
    list" property visible at a glance."""
    return frozenset(illustrations.target_filenames())

_ILLUSTRATION_FILENAMES = _illustration_filenames()
```
Per RESEARCH.md Pattern 4, change to `_illustration_filenames(state_dir=None)` taking a per-request union of `illustrations.target_filenames()` and `manual_resolutions.load_manual_resolutions(state_dir)`'s keys (each converted via `illustrations.normalise_airline_key()`). Every call site (`_serve_illustration_image()`, `_handle_illustration_replace()`) switches from reading the module constant to calling `self._illustration_filenames(self.args.state_dir)` (or a bound helper) per request — same cost class as `device_config.load_device_config()`'s already-unconditional per-request read in `page_context()`.

**Upload handler's exact docstring-ordered security steps to reuse verbatim for Step B** (`app.py`, `_handle_illustration_replace()`):
```python
filename = key + ".png"
if filename not in _ILLUSTRATION_FILENAMES:
    return self.send_html(404, self._not_found_page())

raw = self._read_upload_body()
if raw is None:
    return self.redirect("/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

payload = parse_single_uploaded_file(self.headers.get("Content-Type"), raw)
if payload is None or len(payload) > MAX_ILLUSTRATION_UPLOAD_BYTES:
    return self.redirect("/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

state_dir = self.args.state_dir
override_dir = illustrations.override_dir_for_state_dir(state_dir)
try:
    os.makedirs(override_dir, exist_ok=True)
except OSError:
    return self.redirect("/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))

raw_tmp_path = os.path.join(override_dir, ".%s.%d.upload.tmp" % (key, os.getpid()))
encoded_tmp_path = os.path.join(override_dir, ".%s.%d.encoded.tmp" % (key, os.getpid()))
try:
    with open(raw_tmp_path, "wb") as fh:
        fh.write(payload)
    problems = illustrations.validate_illustration_file(raw_tmp_path)
    if problems:
        ...
        return self.redirect("/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))
    with Image.open(raw_tmp_path) as img:
        rgba = img.convert("RGBA")
        rgba.save(encoded_tmp_path, format="PNG")
    override_path = illustrations.override_path_for_key(key, state_dir)
    os.replace(encoded_tmp_path, override_path)
    return self.redirect("/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACED))
except Exception:
    return self.redirect("/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))
finally:
    for tmp_path in (raw_tmp_path, encoded_tmp_path):
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
```
Per RESEARCH.md Pattern 3, this is reused **unmodified in logic** for Step B — only its membership check (`filename not in _ILLUSTRATION_FILENAMES`) needs the widened, per-request-union version above, because by the time Step B runs the key has already been persisted server-side by Step A.

**New Step A route (`POST /airlines/resolve`) — pattern from `POST /settings`'s urlencoded handler.** Grep `companion/app.py` for its `read_form()` dispatch (`Handler.read_form()` — same never-raising byte-decode discipline as `parse_single_uploaded_file()`) and its `page_context` module-boundary/flash-key contract (`companion/pages/__init__.py`'s documented `handle_post(form, ctx) -> str` contract, quoted in RESEARCH.md's Code Examples section). Body: re-validate `prefix` against the unresolved-prefix registry server-side (never trust the hidden field alone — same discipline `save_device_config()` uses), normalise/bound `airline_name`, call `manual_resolutions.add_entry()`, branch on `illustrations.resolved_illustration_path(key, state_dir) is not None` to pick the redirect target (per UI-SPEC.md's Step A/Step B routing).

**New delete route (`POST /airlines/manual-resolutions/{prefix}/delete`)** — same `SameSite=Strict`-only CSRF posture, same idempotent-delete discipline as `manual_resolutions.delete_entry()` (no-op if already absent).

---

### `companion/pages/airlines_page.py` (MODIFIED — component, SSR)

**Analog 1 (form shape):** `_lightbox_replace_form_html()` (`airlines_page.py:270-345`)
```python
def _lightbox_replace_form_html():
    icon_html = layout.icon_html("icon-upload", extra_class=REPLACE_ICON_CLASS)
    return (
        '<form class="%s" method="post" enctype="multipart/form-data" action="">'
        '<div class="%s">'
        "%s"
        '<label for="%s">%s</label>'
        '<p class="%s">%s</p>'
        '<input type="file" id="%s" name="image" accept="image/png" required>'
        '<button type="submit">%s</button>'
        "</div>"
        "</form>"
    ) % ( ... )
```
No JS submit logic, `%`-formatted string templates, constants (`REPLACE_HINT_TEXT`, `REPLACE_INPUT_ID`, etc.) declared module-level, `layout.icon_html()` for glyphs. The new resolve form (Step A, urlencoded) and Step B's upload form (`action="/illustration/{key}.png"`, reusing `REPLACE_HINT_TEXT` verbatim per UI-SPEC.md) both copy this exact `%`-template-with-module-constants style. Every interpolated value not from a fixed module constant (prefix, airline name, callsign) MUST go through `escape_html()` — this function's docstring calls out precisely why it currently skips escaping (nothing external interpolated); the new forms do interpolate external values and must not skip it.

**Analog 2 (list shape):** `companion/pages/health_page.py`'s `_registry_table_html()`/`_registry_cards_html()`/`_registry_row_html()` (`health_page.py:1975-2110`) — the `.data-table`/`.data-cards` sibling pairing UI-SPEC.md explicitly directs the management list to mirror:
```python
_REGISTRY_HEADERS = ("Prefix", "Count", "First seen", "Last seen", "Example callsign")

def _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now):
    ...

def _registry_table_html(rows, now):
    ...
    header_cells = "".join("<th>%s</th>" % escape_html(h) for h in _REGISTRY_HEADERS)
    rows_html = "".join(
        _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now)
        for index, (prefix, count, first_seen, last_seen, example_callsign) in enumerate(rows)
    )
    ...

def _registry_cards_html(rows, now):
    ...
```
Copy this desktop-table/mobile-cards split structurally for the manual-resolutions management list: a `_MANUAL_RESOLUTION_HEADERS` tuple, a `_manual_resolution_row_html()`, paired `_manual_resolution_table_html()`/`_manual_resolution_cards_html()`. Empty state uses `layout.empty_state(...)` exactly as `health_page.py` does elsewhere (see `_NO_GAPS_HEADING`/`_NO_GAPS_BODY` pattern at `health_page.py:349-351`).

**Data source for the resolve section's context block** — reuse `health_page.unresolved_rows(state_dir)` (`health_page.py:1843-1879`) directly (cross-page-module function import is sanctioned per CLAUDE.md's "no page imports another page module" rule being about page *rendering* modules calling each other — but confirm via `companion/pages/__init__.py`'s boundary doc before importing `health_page` from `airlines_page`; if disallowed, `airlines_page.py` should call `poll_loop.load_poll_state(state_dir)` directly and re-implement the same tuple shape as a local `_unresolved_row_for_prefix(state_dir, prefix)` single-entry lookup, per RESEARCH.md's structure note "a new local `unresolved_rows(state_dir)`-style single-entry lookup mirroring `health_page.py`'s").

---

### `companion/pages/health_page.py` (MODIFIED — component, SSR, presentation-only)

**Analog:** itself — `_READ_ONLY_NOTE` (`health_page.py:352-354`), `_SOURCE_ROWS` (`health_page.py:368-380`), `_REGISTRY_HEADERS`/`_registry_row_html()`/`_registry_cards_html()` (`health_page.py:1975-2110`)

**Constant to reword** (`health_page.py:352-354`):
```python
_READ_ONLY_NOTE = (
    "This list is read-only by design — resolving a prefix is a manual "
    "step done elsewhere, following the existing coverage-gap runbook.")
```
→ per UI-SPEC.md's Copywriting Contract, replace string body only; rendering call site (`<p class="text-body section-caption">{escaped}</p>`) is unchanged.

**Tuple to extend** (`health_page.py:368-380`):
```python
_SOURCE_ROWS = (
    ("fresh_hit", "Fresh lookup", "..."),
    ("cache_hit", "Cached hit", "..."),
    ("airline_only", "Airline only", "..."),
    ("miss", "Miss", "..."),
)
```
Append the fifth tuple `("manual", "Manual", "The operator resolved this callsign's prefix by hand, from the companion web interface.")` per D-02/UI-SPEC.md — renders through the existing `_stats_table_html()`/`_stats_cards_html()` machinery with zero new code (`resolution_stats()` at `health_page.py:1889-1918` already iterates `_SOURCE_ROWS` generically).

**Row/card functions to extend with a sixth column / new block** — `_registry_row_html()`/`_registry_cards_html()`/`_REGISTRY_HEADERS` (`health_page.py:1975` onward): append `"Resolve"` to `_REGISTRY_HEADERS`, add a sixth `<td>` with a plain `<a href="/airlines?resolve={escaped-prefix}" aria-label="Resolve prefix {escaped-prefix}">Resolve</a>` (desktop) and a `.data-card__action` block (mobile) per UI-SPEC.md's exact markup — no `<form>`, no `<button>` (D-10).

---

### `scripts/run-all-tests.sh` (MODIFIED — config, CI harness list)

**Analog:** itself, the `HARNESSES` array (full file read above):
```bash
HARNESSES=(
    server/test_config_history.py
    server/test_dither.py
    server/test_enrich.py
    server/test_illustrations.py
    ...
    companion/test_status_pages.py
    companion/test_view_pages.py
)
```
Add `server/test_manual_resolutions.py` to this array. This is the single source of truth CI and README both defer to (per its own header comment) — a new test file omitted here silently never runs in CI, matching the orchestrator's warning.

---

### Test harnesses gaining checks (`companion/test_status_pages.py`, `companion/test_companion_app.py`, `server/test_enrich.py`, `server/test_poll_loop.py`)

**Analog:** `server/test_enrich.py`'s own `check()`/`EXPECTED_CHECK_COUNT` harness (lines 1-90, 1128):
```python
EXPECTED_CHECK_COUNT = 52
...
def check(name, fn):
    try:
        ok, reason = fn()
    except Exception as exc:
        ok, reason = False, "raised %r" % (exc,)
    results.append((name, ok, reason))
...
return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1
```
Every one of the four harnesses above follows this identical shape (verified: `EXPECTED_CHECK_COUNT` mismatches are a deliberate safety net per RESEARCH.md Pitfall 5, not a bug to suppress). Each new `check("name", fn)` call added for this phase's new behavior must be paired with incrementing that file's own `EXPECTED_CHECK_COUNT` in the same edit — never add a check without bumping the constant, never bump the constant without adding a check.

## Shared Patterns

### Never-raising registry read/write (device_config.py family)
**Source:** `server/device_config.py:524-648` (`load_device_config()`/`save_device_config()`)
**Apply to:** `server/plane/manual_resolutions.py` (new module) — the entire load/validate/tmp-write/`os.replace()` contract, per D-05's explicit instruction to copy it "exactly."

### Process-scoped state-dir setter for a deep, render-agnostic call chain
**Source:** `server/plane/illustrations.py:606-635` (`set_override_state_dir()`/`override_dir_for_state_dir()`)
**Apply to:** `server/plane/manual_resolutions.py`'s `set_manual_registry_state_dir()` (called once per cycle from `poll_loop.py`, mirrors the existing `illustrations.set_override_state_dir(state_dir)` call at `poll_loop.py:717`) and `server/plane/enrich.py`'s registry-read accessor.

### Validate-then-join over a closed, server-controlled set (never sanitise-then-join)
**Source:** `companion/app.py`'s `_serve_illustration_image()`/`_handle_illustration_replace()` (membership test against `_ILLUSTRATION_FILENAMES` BEFORE any path construction)
**Apply to:** Step A's prefix re-validation against the unresolved-prefix registry (D-11), and the widened `_illustration_filenames()` membership set (D-09) — same shape, different set, per RESEARCH.md's explicit framing of D-11 as "the same validate-then-join shape the existing route uses."

### Never-raising, shape-gated registry mutation
**Source:** `server/plane/enrich.py`'s `note_unresolved_prefix()` (`enrich.py:754-800`)
**Apply to:** `enrich.clear_resolved_unresolved_prefix()` (D-14) — structural inverse, same `isinstance(registry, dict)` guard, same `_AIRLINE_PREFIX_SHAPE_RE` gate, same never-raises discipline.

### `.data-table`/`.data-cards` desktop/mobile sibling pairing
**Source:** `companion/pages/health_page.py`'s `_registry_table_html()`/`_registry_cards_html()` (`health_page.py:1975-2110`)
**Apply to:** the new manual-resolutions management list in `airlines_page.py` (D-07) — same breakpoint, same sibling-combinator toggle mechanism, same `row-alt` convention, per UI-SPEC.md's explicit instruction to mirror this pairing.

### JS-free native `<form method="post">` state changes, no CSRF token
**Source:** `companion/app.py`'s `_handle_illustration_replace()` docstring (`SameSite=Strict` posture, `companion/auth.py:132`) and `_lightbox_replace_form_html()`'s plain multipart form
**Apply to:** every new state-changing control this phase adds (resolve form, delete forms) — no per-form token, no JS submit logic, matching the site's single established CSRF posture.

### Single-escaping choke point
**Source:** `companion.layout.escape_html()`, used throughout `health_page.py`/`airlines_page.py` at every interpolation site
**Apply to:** every new interpolated value in this phase's markup (prefix, airline name, callsign, `<datalist>` option values) — exactly once, at the point of interpolation, per UI-SPEC.md's Accessibility & JS-Free Degradation Notes.

## No Analog Found

None — every file this phase touches has a strong, verified in-repo analog (see table above). No file requires falling back to RESEARCH.md's code examples in place of a real codebase precedent.

## Metadata

**Analog search scope:** `server/`, `server/plane/`, `companion/`, `companion/pages/`, `scripts/` — read directly via `Read`/`Bash sed -n` ranges, no broad `Glob`/`Grep` sweep needed since CONTEXT.md/RESEARCH.md/UI-SPEC.md already named every analog file and line range precisely.
**Files scanned:** 9 source files read directly (`device_config.py`, `enrich.py`, `illustrations.py`, `poll_loop.py`, `app.py`, `airlines_page.py`, `health_page.py`, `test_enrich.py`, `run-all-tests.sh`)
**Pattern extraction date:** 2026-09-06
