# Phase 16: Calendar-linked flight highlighting — Pattern Map

**Mapped:** 2026-09-07
**Files analyzed:** 8 (2 new, 6 modified)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `server/plane/calendar_rules.py` (NEW) | service (leaf registry + parser + fetcher) | CRUD + streaming fetch | `server/plane/colour_rules.py` (registry/file contract) + `server/plane/manual_resolutions.py` (write idiom) + `server/plane/enrich.py::default_transport` (bounded HTTP) | role-match, composite |
| `server/test_calendar_rules.py` (NEW) | test | batch/unit | `server/test_colour_rules.py` | exact |
| `server/plane/fixtures/*.ics` (NEW) | config/fixture | file-I/O | none (new artifact) | n/a — no analog |
| `server/plane/colour_rules.py` (MODIFIED) | service (resolver seam) | request-response | itself, `resolve_effective_theme_id()` | exact — additive signature change only |
| `server/device_config.py` (MODIFIED) | model/config | CRUD | existing `theme_arriving` key precedent (same file) | exact |
| `server/poll_loop.py` (MODIFIED) | controller (oneshot orchestrator) | event-driven / batch | itself — existing priming-call block + both `resolve_effective_theme_id()` call sites | exact |
| `companion/pages/config_page.py` (MODIFIED) | component (settings page section) | request-response | Rules section (`_rule_add_form_html`, `_rules_section_html`) + Theme group's arrivals `<select>` | exact |
| `companion/app.py` (MODIFIED) | controller (env presence + POST validation) | request-response | `env_wake_interval_default()` + `handle_post()`'s theme membership checks | exact |
| `scripts/run-all-tests.sh` (MODIFIED) | config (test registration) | batch | `HARNESSES` array | exact |

## Pattern Assignments

### `server/plane/calendar_rules.py` (NEW — service, leaf)

**Analogs:** `server/plane/colour_rules.py` (module contract + file I/O), `server/plane/manual_resolutions.py` (write idiom precedent), `server/plane/enrich.py` (bounded HTTP + `resolve_route()`'s route shape), `server/poll_loop.py` (throttle-timestamp pattern)

**The leaf-import rule (copy verbatim into this module's own docstring, adapted)** — `server/plane/colour_rules.py:6-17`:
```python
"""... This module imports `server.device_config` ... plus stdlib only. It
must NEVER import `server.plane.enrich`, `server.plane.detect`,
`server.plane.illustrations`, `server.plane.manual_resolutions`, or
`server.plane.render` — `poll_loop.py` already imports all of those plus
this module, and the reverse direction would make
`poll_loop -> colour_rules -> X -> poll_loop` a real import cycle (D-13).
```
`calendar_rules.py` needs the identical clause naming itself: it must never import `colour_rules.py` (D-01/D-02's precedence is wired the other way, via a keyword argument `poll_loop.py` computes and passes in — see the resolver section below), and it may import `enrich`-shaped route dicts only as plain arguments (not via `import server.plane.enrich`), matching how `colour_rules.py` "deliberately DUPLICATE[s] small primitives ... rather than import them."

**Never-raising load** — `server/plane/colour_rules.py:207-238` (`load_colour_rules`):
```python
try:
    with open(colour_rules_path(state_dir)) as fh:
        data = json.load(fh)
except (OSError, ValueError):
    data = {}
if not isinstance(data, dict):
    data = {}
# ... rebuild every entry from scratch, never reuse parsed dict directly,
# drop anything malformed, cap at a max-entries constant, print (never
# raise) a one-line warning naming the drop count.
```
Copy this shape exactly for `load_calendar_registry(state_dir)`: missing/corrupt file -> empty shape (`{"entries": [], "last_attempt_at": None, "last_synced_at": None}`), never an exception.

**Allowlist regexes** (module-level, compiled once) — `server/plane/colour_rules.py:79-87`:
```python
_CALLSIGN_RULE_RE = re.compile(r"^[A-Z0-9]{2,8}$")
_HEX_RULE_RE = re.compile(r"^[0-9A-F]{6}$")
_PREFIX_RE = re.compile(r"^[A-Z]{3}$")
```
`calendar_rules.py` needs its own positive allowlist for whatever it parses out of `SUMMARY` (flight-number-shaped and IATA-airport-shaped tokens) before it is ever compared or persisted — same T-15-01/T-16-INPUT discipline, applied at parse time AND re-applied on every read of the persisted file (see `load_colour_rules()`'s own re-validation-on-read comment, lines 218-224).

**`_WRITE_LOCK` usage** — `server/plane/colour_rules.py:107-114`:
```python
# WR-02-style fix, applied from day one here (T-15-02): add_rule()/
# delete_rule() are both a load-modify-write whole-file cycle...
_WRITE_LOCK = threading.Lock()
```
Even though the research notes this file has a single writer (the poll oneshot), keep the lock as defence-in-depth exactly as recommended — same name, same scope (wraps the entire load-check-mutate-write sequence, not just `os.replace()`).

**tmp-write-then-`os.replace()` block with `except` cleanup** — `server/plane/colour_rules.py:340-353` (identical in `manual_resolutions.py:376-389`):
```python
path = colour_rules_path(state_dir)
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
Copy verbatim for the calendar registry's whole-file rewrite (D-03: replace, never merge — closer to a cache-replacement than `add_rule()`'s single-entry mutation, per RESEARCH.md Pattern 3).

**Result-code constants** — `server/plane/colour_rules.py:99-105`:
```python
ADD_OK_NEW = "ok_new"
ADD_OK_REPLACED = "ok_replaced"
ADD_REJECTED_KIND = "rejected_kind"
...
ADD_FAILED = "failed"
```
Mirror this shape for the fetch/parse outcome (e.g. a `FETCH_OK`/`FETCH_SKIPPED_THROTTLED`/`FETCH_FAILED` vocabulary) — these are NOT flash keys, exactly as this module's own comment insists (`colour_rules.py:89-91`); `poll_loop.py` only cares about the returned entries and timestamps, and nothing about a flash exists at this tier.

**`set_*_state_dir()` module-global wiring** — `server/plane/colour_rules.py:427-447`:
```python
_cached_rules = {kind: {} for kind in RULE_KINDS}

def set_colour_rules_state_dir(state_dir):
    global _cached_rules
    if state_dir:
        _cached_rules = load_colour_rules(state_dir)
    else:
        _cached_rules = {kind: {} for kind in RULE_KINDS}
```
`calendar_rules.py` does NOT need this pattern for a *read* cache the way `colour_rules.py` does — its match function (`match_calendar_theme()`) can simply be handed the already-loaded registry by `poll_loop.py` at the point it's needed, since (per RESEARCH.md's architecture diagram) the fetch+parse+persist step happens once per cycle near the other three priming calls, and the match happens later in the same cycle from the same loaded value. If a process-global cache is used anyway for symmetry with the other two priming calls, follow this exact shape.

**Bounded, never-raising fetch (copy `detect.py`'s per-provider try/except shape)** — `server/plane/detect.py:404-417`:
```python
def query_provider(name, lat, lon, radius_nm, timeout=10.0):
    """... Raises on any failure ... caller is responsible for catching
    this per-provider so one aggregator being down never aborts a poll ..."""
    spec = PROVIDERS[name]
    url = spec["url_template"].format(lat=lat, lon=lon, dist=radius_nm)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    aircraft = data.get(spec["aircraft_key"]) or []
    return aircraft
```
and the injectable-transport idiom to mirror instead for testability — `server/plane/enrich.py:163-182`:
```python
def default_transport(callsign, timeout=DEFAULT_TIMEOUT):
    """Thin `requests.get()` wrapper ... `lookup_route`'s injectable
    `transport` parameter exists specifically so tests can replace this
    with a hermetic fake that replays a committed fixture instead of
    making a live network call - see server/test_enrich.py."""
    url = ADSBDB_URL.format(callsign=callsign)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    try:
        body = response.json()
    except ValueError:
        body = None
    return response.status_code, body
```
**Critical divergence from both, per RESEARCH.md Pitfall 4**: the existing caller-catch idiom at `detect.py:950-958` does
```python
except (requests.RequestException, ValueError) as exc:
    print("detect: %s query failed: %s: %s" % (name, type(exc).__name__, exc), file=sys.stderr)
```
— **do not copy the `%s: %s` interpolation of `exc` itself** for the calendar fetch. Several `requests.exceptions.*` subclasses embed the request URL (which carries the secret token) in their default `__str__()`. Log only `type(exc).__name__` and a fixed string ("calendar fetch failed"), never `exc` interpolated, and never log the URL on success either.

**Throttle timestamp pattern (`now_s()` as the replaceable clock seam, and `advance_is_due()`'s shape)** — `server/poll_loop.py:126-140` and `:179-202`:
```python
def now_s():
    """Wall-clock epoch seconds, as a module-level seam. ... the test
    harness replaces this function to drive cadence deterministically."""
    return time.time()

def advance_is_due(last_advance_at, now, min_interval_s=None):
    if min_interval_s is None:
        min_interval_s = MIN_ADVANCE_INTERVAL_S
    if last_advance_at is None:
        return True
    elapsed = now - last_advance_at
    if elapsed < 0:
        return True
    return elapsed >= min_interval_s
```
Write `calendar_fetch_is_due(last_attempt_at, now, min_interval_s=CALENDAR_FETCH_INTERVAL_S)` of identical shape inside `calendar_rules.py`, and have `poll_loop.py` call `now_s()` (already imported/defined there) rather than `calendar_rules.py` inventing its own clock — keeps one clock seam in the codebase. Track two separate timestamps in the persisted file, per RESEARCH.md Pattern 2: `last_attempt_at` (updates on every attempt, gates the throttle) vs `last_synced_at` (updates only on success, drives the UI copy).

---

### `server/plane/calendar_rules.py` — Bounded/hardened HTTP (SSRF + size cap)

No existing analog for SSRF hardening exists in this codebase (RESEARCH.md: "no SSRF-class validation exists anywhere ... today"). Use RESEARCH.md's own vetted skeleton verbatim as the pattern to implement against — it already follows this codebase's `requests.get(..., headers={"User-Agent": USER_AGENT}, timeout=timeout)` idiom (matching `detect.py:413` / `enrich.py:177`) while adding the IP-validation and streaming-size-cap this is the first outbound call to need. See RESEARCH.md's "Bounded, IP-validated fetch skeleton" (lines 340-401) — do not re-derive; implement from that skeleton.

---

### `server/plane/colour_rules.py` (MODIFIED — resolver seam)

**Analog:** itself. **Current signature** (`server/plane/colour_rules.py:466-479`):
```python
def resolve_effective_theme_id(state, flight, device_cfg):
    """... Order: exact callsign rule, then hex rule, then prefix rule,
    then the arrivals override when and only when `state` equals
    `ARRIVING_STATE`, then `device_cfg["theme"]`.
    ...
    """
    cache = _cached_rules if isinstance(_cached_rules, dict) else {}
    ...
    rule_theme = _rule_theme_from_cache(cache, RULE_KIND_CALLSIGN, callsign)
    if rule_theme is None:
        rule_theme = _rule_theme_from_cache(cache, RULE_KIND_HEX, hex_value)
    if rule_theme is None:
        rule_theme = _rule_theme_from_cache(cache, RULE_KIND_PREFIX, prefix)
    if rule_theme is not None and rule_theme in device_config.THEMES:
        return rule_theme

    if isinstance(device_cfg, dict) and state == ARRIVING_STATE:
        arriving = device_cfg.get("theme_arriving")
        if isinstance(arriving, str) and arriving in device_config.THEMES:
            return arriving

    base_theme = device_cfg.get("theme") if isinstance(device_cfg, dict) else None
    if isinstance(base_theme, str) and base_theme in device_config.THEMES:
        return base_theme
    return device_config.DEFAULT_THEME_ID
```
**Recommended change (RESEARCH.md's own additive proposal, confirmed against the shipped signature above)** — add one new keyword-only, defaulted-to-`None` parameter, checked FIRST, with an `isinstance()` + `THEMES`-membership guard identical in shape to every other guard already in this function:
```python
def resolve_effective_theme_id(state, flight, device_cfg, calendar_theme_id=None):
    if isinstance(calendar_theme_id, str) and calendar_theme_id in device_config.THEMES:
        return calendar_theme_id
    # ... existing rule-lookup logic, unchanged from above ...
```
This is strictly additive — no import added, no existing call site broken, `colour_rules.py`'s leaf-import contract survives unmodified (the module still never imports `calendar_rules`). The membership check (`in device_config.THEMES`) is the same T-15-05-style tamper defence `normalise_rule_theme_id()` already applies elsewhere in this file (lines 195-204) — apply it to the calendar-sourced value too, per T-16-TAMPER in 16-VALIDATION.md.

---

### `server/poll_loop.py` (MODIFIED — controller/oneshot)

**Analog:** itself — the existing per-cycle priming block and both resolver call sites.

**Priming-call block to extend** — `server/poll_loop.py:737-749`:
```python
illustrations.set_override_state_dir(state_dir)
manual_resolutions.set_manual_registry_state_dir(state_dir)
# D-13 (phase 15, plan 15-03): prime the per-flight colour-rule registry
# cache from THIS cycle's own state_dir ...
colour_rules.set_colour_rules_state_dir(state_dir)
```
Add the calendar's throttled-fetch call as the natural fourth entry in this list (RESEARCH.md Pattern 2) — but note it is NOT a pure cache-priming call like the other three (it can perform network I/O), so it should be written and commented as its own distinct step, immediately after this block, not folded silently into it.

**Ordering trap this file already documents and applies unchanged to the calendar match** — `server/poll_loop.py:759-772`:
```python
# D-13: a DEFAULT ASSIGNMENT, not a resolution. ... Do NOT call
# colour_rules.resolve_effective_theme_id() here: `render_state` and
# `current_flight` are not settled at this point in the function ...
effective_theme_id = theme_id
```
The calendar match (`calendar_rules.match_calendar_theme(...)`) must be computed at the same point the resolver call already is (both call sites below), never hoisted to the top-of-cycle block — same trap, same reasoning, explicitly called out again in RESEARCH.md's own Anti-Patterns section.

**Both existing call sites (the both-branches invariant, D-13/T-15-10)** — `server/poll_loop.py:1152` and `:1237`:
```python
# call site 1 (flight-detected branch):
effective_theme_id = colour_rules.resolve_effective_theme_id(render_state, current_flight, device_cfg)

# call site 2 (held/repaint branch — same flight redrawn later must get the
# IDENTICAL effective theme id it got at call site 1):
effective_theme_id = colour_rules.resolve_effective_theme_id(render_state, current_flight, device_cfg)
```
Each becomes:
```python
calendar_theme_id = calendar_rules.match_calendar_theme(current_flight, route, ...)  # or current_route at site 2
effective_theme_id = colour_rules.resolve_effective_theme_id(
    render_state, current_flight, device_cfg, calendar_theme_id=calendar_theme_id)
```
computed identically at both sites — this is "the same shape Phase 15 itself used to keep both branches in lockstep" (RESEARCH.md).

---

### `server/device_config.py` (MODIFIED)

**Analog:** the existing `theme_arriving` key's own contract (same file — not separately excerpted here since RESEARCH.md confirms it is "mirroring `theme_arriving`'s exact contract" — an optional, `THEMES`-validated, `None`-defaultable key). Follow `theme_arriving`'s own load/save/validate treatment verbatim for the new `calendar_theme_id` key.

---

### `companion/app.py` (MODIFIED — controller)

**Analog:** `env_wake_interval_default()` — `companion/app.py:501-526`:
```python
def env_wake_interval_default():
    """Return the deployed SKYPANE_SLEEP_S as an int, or None.

    Read via `os.environ.get(SLEEP_ENV_VAR)` on every call — never
    captured at import time — so a redeployed env file takes effect on
    the next service restart with nothing cached in between, matching
    `auth.configured_password()`'s own per-call shape.

    Contract difference from `configured_password()`: that function is
    fail-closed and raises `AuthNotConfigured` ... This function is
    fail-open and returns `None` for every failure case ...
    """
```
Write the calendar env-var presence check the same way: `os.environ.get(CALENDAR_URL_ENV_VAR)` read fresh on every call (never cached at import time), fail-open, returning a presence boolean or a small status tuple — **never** the value itself, per the Copywriting Contract's "configured/not configured, never the value" requirement and RESEARCH.md's V14 finding that this is the project's first secret handled outside `companion/auth.py`.

**Auth precedent for the secret itself** — `companion/auth.py:45,64-75` (`PASSWORD_ENV_VAR` / `configured_password()`):
```python
PASSWORD_ENV_VAR = "SKYPANE_COMPANION_PASSWORD"
...
def configured_password():
    """Return the shared password as bytes, or raise AuthNotConfigured.
    Never include the environment value in the raised exception.
    """
    value = os.environ.get(PASSWORD_ENV_VAR)
    if not value:
        raise AuthNotConfigured(...)
    return value.encode()
```
Naming convention to reuse for the new env var: `SKYPANE_CALENDAR_ICS_URL` (per UI-SPEC and RESEARCH.md), but with `env_wake_interval_default()`'s fail-open shape, not `configured_password()`'s fail-closed shape — this variable's absence is a legitimate, designed empty state (not-configured), not an auth failure.

**POST validation precedent (membership check before persisting a theme id)** — `companion/pages/config_page.py:1544-1548`:
```python
if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
    ...
if (submitted_theme_arriving is not None
        and submitted_theme_arriving not in device_config.THEME_IDS):
    ...
```
Apply the identical `not in device_config.THEME_IDS` guard to the submitted `calendar_theme_id` field in `handle_post()`, reusing the existing generic settings-save-failed flash for a crafted out-of-range value (UI-SPEC's Flash messages section — no new flash constant).

---

### `companion/pages/config_page.py` (MODIFIED — component)

**Analog:** the Rules add-form's Theme field (`_rule_add_form_html`, lines 1087-1127) and the section-assembly list in `render()`.

**The exact `<select>` shape to reuse for `calendar_theme_id`** — `companion/pages/config_page.py:1097-1101, 1114-1117`:
```python
theme_options = "".join(
    '<option value="%s">%s</option>'
    % (escape_html(theme_id), escape_html(device_config.theme_label(theme_id)))
    for theme_id in device_config.THEME_IDS
)
...
'<div class="rule-add-form__field">'
'<label for="rule-theme">%s</label>'
'<select id="rule-theme" name="rule_theme_id" required>%s</select>'
"</div>"
```
UI-SPEC's Section Anatomy names this exact wrapper class (`.rule-add-form__field`) to reuse verbatim for the Calendar section's label+select+hint stack — copy this option-building loop and div structure, swap `name="rule_theme_id"` for `name="calendar_theme_id"` and the id/for pair for `calendar-theme`.

**Section-assembly list to append to** — `companion/pages/config_page.py:1379-1410` (`render()`'s return tuple):
```python
return (
    layout.page_header("Settings")
    + '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
    "%s" "%s" "%s" "%s" "%s" "%s"
    '<button type="submit" %s>Save settings</button>'
    "</form>"
    "%s"
    '<section class="page-section">'
    '<h2 class="text-heading">Poll</h2>'
    "%s"
    "</section>"
    "%s"
) % (
    SETTINGS_FORM_ID, SETTINGS_ROUTE,
    theme_fieldset(...), runway_fieldset(...), led_group(...),
    quiet_hours_group(...), wake_interval_group(...), display_group(...),
    STATIC_SAVE_FALLBACK_ATTR,
    rules_section_html,
    poll_trigger_section(cooldown_remaining),
    dirty_bar_html,
)
```
UI-SPEC recommends appending the new Calendar `<div class="page-section" data-dirty-section="Calendar">` as the LAST group inside `<form id="settings-form">`, i.e. one more `"%s"` slot immediately after `display_group(...)`'s output and before `STATIC_SAVE_FALLBACK_ATTR` — matching `display_group`'s own sibling-section precedent, not `rules_section_html`'s (Rules lives outside the form because it has its own nested `<form>`s; Calendar has none, so it belongs inside).

**Section caption constant precedent** — `companion/pages/config_page.py:126` (`THEME_SECTION_CAPTION`) and `:274` (`RULES_SECTION_CAPTION`): both are plain module-level string constants assigned once, escaped via `escape_html()` at render time. Define `CALENDAR_SECTION_HEADING`, `CALENDAR_SECTION_CAPTION`, `CALENDAR_STATUS_*`, `CALENDAR_THEME_HINT` the same way, using the exact locked copy from `16-UI-SPEC.md`'s Copywriting Contract table.

---

### `server/test_calendar_rules.py` (NEW — test)

**Analog:** `server/test_colour_rules.py` — header/setup pattern, lines 1-40:
```python
#!/usr/bin/env python3
"""Contract harness for server/plane/colour_rules.py - the phase 15
per-flight colour-rule registry and D-13 resolver
(15-VALIDATION.md Wave 0 item 1).

Stdlib-only, plus the module under test (server.plane.colour_rules) and
its own dependency (server.device_config). Every fixture is a
tempfile.TemporaryDirectory(), never a shared/real state dir. Exits 0
only when every check below passes; any failure (or exception - none is
ever swallowed into a pass) exits 1.

Because colour_rules.py keeps a process-global cache, every resolver
check primes it explicitly with set_colour_rules_state_dir() and resets
it unconditionally afterwards (via try/finally), so check order can never
leak state between checks.

Usage:
    server/.venv/bin/python3 server/test_colour_rules.py
"""
import json
import os
import string
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Initial value for this file, introduced by phase 15 plan 01. Re-derived
# by RUNNING the harness (not by arithmetic), per this repo's own
# documented discipline ...
EXPECTED_CHECK_COUNT = 27
```
Copy this exact preamble shape: `HERE`/`REPO_ROOT` sys.path bootstrap, `tempfile.TemporaryDirectory()` per fixture, an `EXPECTED_CHECK_COUNT` ledger **re-derived by running the harness** (do not compute it by hand), and if the module under test keeps a process-global cache (it will, for symmetry with `colour_rules.py`), the same try/finally reset-after-every-check discipline. Also mirror `enrich.py`'s injectable-`transport` pattern (`server/plane/enrich.py:163-182`, `lookup_route(callsign, cache, transport=None, ...)`) for the fetch-hardening checks — no live network call in the suite, exactly like every other harness in this codebase.

**`check(name, fn)` accumulator pattern**: use the same local helper every `server/test_*.py` file already defines (verified present at the top of `test_colour_rules.py`, standard across the suite) — do not introduce pytest/unittest.

---

### `scripts/run-all-tests.sh` (MODIFIED — registration)

**Analog:** the `HARNESSES` array, `scripts/run-all-tests.sh:34-52`:
```bash
HARNESSES=(
    server/test_config_history.py
    server/test_colour_rules.py
    server/test_dither.py
    ...
    companion/test_view_pages.py
)
```
Append `server/test_calendar_rules.py` to this array (alphabetically or logically near `test_colour_rules.py`, matching the file's own header comment convention of noting "phase 14 plan 01 added the new colour-rules harness below" — add a matching one-line note for phase 16). This is the single source of truth CI and README both defer to; an unregistered harness runs in no suite and is invisible to the coverage gate (per 16-VALIDATION.md Wave 0 Requirements).

## Shared Patterns

### Never-raising load + tmp-write-then-`os.replace()` (state_dir file contract)
**Source:** `server/plane/colour_rules.py:207-238` (load) and `:340-353` (write); `server/plane/manual_resolutions.py:208-293` (load) and `:376-389` (write)
**Apply to:** `server/plane/calendar_rules.py`'s registry file — this is the single most load-bearing pattern in the whole phase; every deviation (raising on malformed JSON, growing without a cap, merging instead of replacing) is exactly what T-16-INPUT/T-16-DOS in 16-VALIDATION.md test against.

### Bounded, per-call-exception outbound HTTP, never logging the raw exception string
**Source:** `server/plane/detect.py:404-417` (structure) + `server/plane/enrich.py:163-182` (injectable-transport testability) + RESEARCH.md's SSRF-hardened skeleton (lines 340-401, IP-validation + streaming size cap — no existing codebase analog for this half)
**Apply to:** `calendar_rules.py`'s fetch function only. **Deviation from `detect.py:950-958`'s existing `"%s: %s" % (type(exc).__name__, exc)` caller-catch idiom is mandatory here** — log `type(exc).__name__` and a fixed description only, never `exc` itself (T-16-SECRET).

### Env-var secret handling: fail-open presence check, never the value
**Source:** `companion/auth.py:45,64-75` (`PASSWORD_ENV_VAR`/`configured_password()` — fail-closed precedent for an auth secret) and `companion/app.py:501-526` (`env_wake_interval_default()` — fail-open precedent for a non-auth env default)
**Apply to:** the new `SKYPANE_CALENDAR_ICS_URL` handling in both `poll_loop.py` (reads the value to fetch) and `companion/app.py`/`config_page.py` (reads only *presence*, for the Settings status line). Use `env_wake_interval_default()`'s fail-open shape, not `configured_password()`'s fail-closed shape, since not-configured is a designed, legitimate state here.

### Additive, backward-compatible resolver extension via optional keyword
**Source:** `server/plane/colour_rules.py:466-479` (`resolve_effective_theme_id()`'s current signature and body)
**Apply to:** the one-line signature change adding `calendar_theme_id=None`, checked first, guarded by the same `isinstance(..., str) and ... in device_config.THEMES` idiom already used three times in this same function.

### THEME_IDS-driven `<select>` construction + membership-checked POST handling
**Source:** `companion/pages/config_page.py:1097-1101` (option-building loop), `:1544-1548` (POST membership guard)
**Apply to:** the new `calendar_theme_id` field on both the render side (`config_page.py`) and the validate-before-persist side (`companion/app.py`'s `handle_post()`).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `server/plane/fixtures/*.ics` (redacted CrewWebPlus-shaped fixture) | config/fixture | file-I/O | No existing `.ics`/calendar fixture anywhere in this codebase — RFC 5545 unfolding logic itself is also new (RESEARCH.md's own "new code" callout, cited against RFC text, not the codebase). Build from RESEARCH.md's `_unfold()` code example and the Wave 0 Requirements checklist in 16-VALIDATION.md (folded lines, `STATUS:CANCELLED` + 1899 junk pair, `FLT`/`OFFD`/`CAHC`/`CPBL` mix, escaped `DESCRIPTION`, bare-UTC `DTSTART`/`DTEND`). |
| SSRF/IP-range validation logic (`_host_is_safe`/`_url_is_safe` in `calendar_rules.py`) | — | — | Confirmed zero matches for `ipaddress`/`is_private`/`SSRF` anywhere in the codebase (RESEARCH.md). Use RESEARCH.md's own vetted skeleton (Code Examples section) directly — there is nothing in-repo to copy from. |

## Metadata

**Analog search scope:** `server/plane/`, `server/`, `companion/`, `companion/pages/`, `scripts/`
**Files scanned:** `colour_rules.py`, `manual_resolutions.py`, `enrich.py`, `detect.py`, `poll_loop.py`, `device_config.py` (referenced only), `companion/auth.py`, `companion/app.py`, `companion/pages/config_page.py`, `server/test_colour_rules.py`, `scripts/run-all-tests.sh`
**Pattern extraction date:** 2026-09-07
