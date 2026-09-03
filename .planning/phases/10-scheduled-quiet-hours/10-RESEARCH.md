# Phase 10: Scheduled quiet hours - Research

**Researched:** 2026-09-03
**Domain:** Server-side wall-clock scheduling (Python stdlib `zoneinfo`) + existing config-registry/render-dispatch patterns
**Confidence:** HIGH

## Summary

This phase needs no new dependency, no new service, and no firmware change. Everything
it touches already exists as an established pattern in this codebase: a config-registry
field (`server/device_config.py`), a companion-page fieldset (`companion/pages/config_page.py`),
a render-dispatch branch (`server/plane/render.py`'s `build_canvas()`), and a
best-effort local-modification read inside the vendored `stub-server/byos_server.py`
(`read_led_enabled()`'s exact shape). The one genuinely new piece of domain knowledge
this phase requires is DST-safe local-wall-clock arithmetic in Python, and that is
solved by the stdlib `zoneinfo` module (3.9+) with no third-party package — confirmed
both by official documentation and by executing it directly against this project's own
pinned interpreter and production OS during this research session.

The most important finding is architectural, not library-related: **the two decisions
this phase implements (D-01's `sleep_s` computation and D-05's "draw the quiet screen
once" logic) do NOT live in the same place**, even though `10-CONTEXT.md`'s Integration
Points section describes both as hooking into "`byos_server.py`'s `/display` handler."
`byos_server.py` only ever serves whatever bytes are already sitting in `panel.bin` —
it has no rendering capability and, being a stdlib-only vendored script, must not
import `server.plane.render` or `server.device_config` at all. The render decision
(D-05) belongs in `server/poll_loop.py` (the process that actually calls
`render.build_canvas()` and writes `panel.bin`, on its own independent 30-second
cadence); only the `sleep_s` computation (D-01) belongs in `byos_server.py`'s
`/display` handler. Both independently read the same `device_config.json` quiet-hours
fields, exactly the way `read_led_enabled()` (in `byos_server.py`) and
`load_device_config()` (in `poll_loop.py`) already independently read the same file for
their own separate purposes today.

**Primary recommendation:** add three registry fields to `server/device_config.py`
(`quiet_hours_enabled`/`_start`/`_end`, "HH:MM" strings) following the exact
`led_enabled` pattern; add a DST-safe window-arithmetic helper there using stdlib
`zoneinfo.ZoneInfo("Europe/Paris")`; call it from `poll_loop.py` to gate a new,
once-per-entry "quiet hours" render branch; and duplicate a small, self-contained,
stdlib-only version of the same arithmetic directly inside `byos_server.py` (mirroring
`read_led_enabled()`'s own local-modification discipline) to compute the extended
`sleep_s`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Quiet-hours config storage (enabled + start/end) | API/Backend (`server/device_config.py`) | — | Single source of truth for every user-settable device setting; same registry `theme`/`tracked_runway`/`led_enabled` already live in |
| Quiet-hours config UI (companion web form) | Frontend Server (`companion/pages/config_page.py`) | — | Server-rendered HTML form, no client framework; mirrors the existing Theme/Runway/LED fieldset pattern in the same file |
| "Are we in the window right now" / DST-safe arithmetic | API/Backend (`server/device_config.py`, stdlib `zoneinfo`) | — | Pure server-side wall-clock computation; the device has no clock awareness and needs none (D-01) |
| Extended `sleep_s` computation | API/Backend (`stub-server/byos_server.py`'s `/display` handler) | — | `sleep_s` is a fully server-controlled per-response field already (confirmed in CONTEXT.md and re-confirmed below); this is the sole place that decides how long the device sleeps |
| "Quiet hours" screen render (D-05) | API/Backend (`server/poll_loop.py` + `server/plane/render.py`) | — | `poll_loop.py` is the only process that renders and writes `panel.bin`; `byos_server.py` never renders anything, only serves bytes |
| Device wake/poll/sleep behavior | Device/Firmware | — | Unaffected — the device blindly deep-sleeps for whatever `sleep_s` it receives (D-01), confirmed unchanged this phase |

## Package Legitimacy Audit

Not applicable — this phase introduces zero new packages. `zoneinfo` is part of the
Python standard library since 3.9 (`server/requirements.txt` stays unchanged: Pillow +
requests only). No `npm view`/`pip index versions`/`cargo search` verification is
needed because nothing new is installed.

**Packages removed due to [SLOP] verdict:** none — no new packages proposed.
**Packages flagged as suspicious [SUS]:** none.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `zoneinfo` (stdlib) | bundled since Python 3.9 | IANA timezone-aware datetime arithmetic for the Europe/Paris quiet-hours window | [VERIFIED: local execution] `python3 -c "from zoneinfo import ZoneInfo; ZoneInfo('Europe/Paris')"` succeeds with exit 0 both on this dev machine and is expected on the deploy target — confirmed via `deploy/provision.sh` targeting **Ubuntu 26.04 LTS**, which ships the `tzdata` system package by default, and via GitHub Actions' `ubuntu-latest` CI runner, which also ships it. No `pip install tzdata` fallback is needed for either environment. [CITED: docs.python.org/3/library/zoneinfo.html] — "Datetimes constructed with ZoneInfo are compatible with datetime arithmetic and handle daylight saving time transitions with no further intervention." |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `datetime` (stdlib) | bundled | Wraps `zoneinfo` for aware-datetime construction/subtraction | Already imported project-wide (`server/history_db.py`'s `utc_now_iso()`); this phase adds `timezone`/`ZoneInfo`-aware usage alongside the existing UTC-only convention, not a replacement of it |
| `re` (stdlib) | bundled | Validating the "HH:MM" shape of submitted start/end times before they ever reach a `datetime()` constructor | Not currently imported by `server/device_config.py` (only `json`/`os`/`sys` today) — a one-line addition, same "stdlib only" leaf-module contract the module's own docstring already states |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `zoneinfo` | `pytz` | Third-party dependency for a solved-by-stdlib problem; would also be the project's first ever addition beyond Pillow/requests to `server/requirements.txt`, which `06-CONTEXT.md` explicitly kept minimal. No reason to add it — `zoneinfo` is strictly sufficient and already proven to work in this exact deployment |
| `zoneinfo` | `dateutil.tz` | Same rejection as `pytz` — a real, well-regarded library, but an unnecessary dependency for one IANA zone lookup this project already has stdlib access to |
| Hard-coded `Europe/Paris` | A per-installation configurable timezone setting | Out of scope: this device has exactly one fixed physical location (the developer's home in Paris — see `PROJECT.md`), and no other phase or seed proposes a second install site. Adding a timezone picker would be speculative generality for a single-tenant, single-location device |

**Installation:**
No install step — `zoneinfo` ships with the Python interpreter this project already
pins (`target-version = "py311"` in `pyproject.toml`; CI's `actions/setup-python@v5`
pins `python-version: '3.12'`; the local dev venv is 3.11.15). `server/requirements.txt`
is unchanged by this phase.

**Version verification:** N/A — stdlib module, not a registry package.

<phase_requirements>
## Phase Requirements

No requirement IDs are mapped to this phase — it is an unmapped backlog phase promoted
directly from `.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md`, matching
every prior `06.6.x` decimal phase's own precedent (confirmed: `.planning/REQUIREMENTS.md`
has no `QUIET-*`/curfew-related requirement ID, and `10-CONTEXT.md`'s own
`<canonical_refs>` section states this explicitly).
</phase_requirements>

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────┐
                     │   companion/pages/           │
                     │   config_page.py (Settings)  │
                     │   - renders quiet-hours       │
                     │     fieldset (checkbox +      │
                     │     2 time inputs)             │
                     │   - handle_post() validates    │
                     │     + calls save_device_config │
                     └───────────────┬─────────────┘
                                     │ writes
                                     ▼
                     ┌─────────────────────────────┐
                     │ server/device_config.py      │
                     │ device_config.json            │
                     │  quiet_hours_enabled: bool    │
                     │  quiet_hours_start: "23:00"   │
                     │  quiet_hours_end:   "07:00"   │
                     └───────┬───────────────┬───────┘
                read (every 30s)        read (per device poll,
                             │           independent process)
                             ▼                       ▼
     ┌──────────────────────────────┐   ┌───────────────────────────────┐
     │ server/poll_loop.py (systemd  │   │ stub-server/byos_server.py     │
     │ timer, 30s oneshot)            │   │ (long-running HTTP service)    │
     │                                │   │                                 │
     │ 1. read device_config          │   │ On GET /device/v1/display:      │
     │ 2. compute "in window now?"    │   │  1. read_quiet_hours() — a       │
     │    via zoneinfo (Europe/Paris) │   │     local, stdlib-only,          │
     │ 3. transition into window ->   │   │     best-effort JSON read        │
     │    render QUIET HOURS screen   │   │     (mirrors read_led_enabled()) │
     │    ONCE, persist               │   │  2. if inside window: sleep_s =  │
     │    poll_state["quiet_hours     │   │     max(--sleep, seconds until   │
     │    _active"]=True              │   │     window end) — D-01           │
     │ 4. holding inside window ->    │   │  3. else: sleep_s = --sleep       │
     │    skip render (no-op, like    │   │     unchanged                     │
     │    D-04's existing hold branch)│   │  4. serve panel.bin bytes exactly │
     │ 5. window ends -> clear flag,  │   │     as before (no rendering        │
     │    resume normal flight        │   │     capability here — D-05's       │
     │    detection/render next cycle │   │     screen was already written     │
     │    (D-07: no "waking" screen)  │   │     into panel.bin by poll_loop.py)│
     └───────────┬────────────────────┘   └───────────────┬─────────────────┘
                 │ writes panel.bin                        │ serves via
                 ▼ (atomic swap)                            │ GET /img/<hash>.bin
     ┌──────────────────────────────┐                       │
     │ server/plane/render.py        │───────────────────────┘
     │ build_canvas(None,             │  (byos_server.py reads panel.bin
     │   "quiet_hours",                │   from disk on every device poll —
     │   quiet_hours_until="07:00")    │   whatever poll_loop.py last wrote)
     │ -> _build_quiet_hours_canvas() │
     └────────────────────────────────┘
                                                    ▲
                                                    │ deep-sleeps for sleep_s,
                                                    │ wakes once, polls
                                          ┌─────────┴─────────┐
                                          │  Device (ESP32-S3) │
                                          │  no clock/quiet-   │
                                          │  hours awareness   │
                                          │  needed (D-01)      │
                                          └────────────────────┘
```

### Recommended Project Structure

No new files. Every change lands inside existing modules:
```
server/
├── device_config.py     # + quiet_hours_enabled/_start/_end registry fields,
│                         #   normalise_*() functions, and the DST-safe
│                         #   window-arithmetic helper (new import: re, datetime, zoneinfo)
├── poll_loop.py          # + quiet-hours gate near the top of run_once(),
│                         #   + poll_state.json "quiet_hours_active" flag
├── plane/
│   └── render.py         # + "quiet_hours" branch in build_canvas()'s dispatch,
│                         #   + _build_quiet_hours_canvas()
├── test_config_history.py  # + quiet-hours registry checks (bump EXPECTED_CHECK_COUNT)
├── test_poll_loop.py       # + quiet-hours gate checks (bump EXPECTED_CHECK_COUNT)
└── test_render.py          # + quiet-hours canvas checks (bump EXPECTED_CHECK_COUNT)

stub-server/
├── byos_server.py        # + read_quiet_hours() (local, stdlib-only, best-effort —
│                         #   mirrors read_led_enabled()'s exact shape),
│                         #   + quiet-hours-aware sleep_s computation in
│                         #   the /device/v1/display GET handler
├── VENDOR.md              # + one new "Local modifications" entry documenting
│                         #   this addition (matches the existing 3-entry log shape)
└── test_poll_cycle.py     # + quiet-hours sleep_s checks (bump EXPECTED_CHECK_COUNT)

companion/
├── pages/
│   └── config_page.py    # + quiet_hours_group() fieldset (checkbox + 2 time
│                         #   inputs), + 3 fields in render()/handle_post()
└── test_config_page.py   # + quiet-hours fieldset/handle_post checks (bump
                          #   EXPECTED_CHECK_COUNT)
```

### Pattern 1: Config registry field addition (follow `led_enabled` exactly)

**What:** A boolean flag plus two validated "HH:MM" strings, added to
`server/device_config.py`'s existing registry pattern.
**When to use:** Any time this phase needs to persist a new user-settable value.
**Example:**
```python
# Source: server/device_config.py (existing led_enabled pattern, lines 333-421),
# adapted — this is this project's own established pattern, not third-party docs.
import re

DEFAULT_QUIET_HOURS_ENABLED = False
DEFAULT_QUIET_HOURS_START = "23:00"
DEFAULT_QUIET_HOURS_END = "07:00"

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def normalise_quiet_hours_enabled(value):
    """Same contract as normalise_led_enabled(): isinstance(value, bool) or
    degrade to the default. No registry test needed for a boolean."""
    if isinstance(value, bool):
        return value
    return DEFAULT_QUIET_HOURS_ENABLED


def normalise_quiet_hours_time(value, default):
    """A string matching _HHMM_RE (24h "HH:MM", zero-padded) or the
    documented default. Never raises. Shared by start/end so the two
    fields cannot silently drift on validation strictness."""
    if isinstance(value, str) and _HHMM_RE.match(value):
        return value
    return default
```
`load_device_config()`/`save_device_config()` extend the same way `led_enabled` did:
each new field gets its own explicit check in `save_device_config()` (raising
`ValueError` on an invalid submitted value, per the *write*-path-is-strict /
*read*-path-is-forgiving asymmetry `config_page.py`'s own `handle_post()` docstring
already documents), and `load_device_config()` always returns all keys via the
`normalise_*()` functions so a hostile or stale on-disk value never reaches a caller.

### Pattern 2: DST-safe window arithmetic (the one genuinely new piece)

**What:** Given "now" (a UTC-aware `datetime`) and a `[start_hm, end_hm)` window in
Europe/Paris local time (wrapping midnight when `end <= start`, e.g. `23:00`-`07:00`),
determine whether "now" falls inside it, and if so, how many seconds remain until it
ends.
**When to use:** Both `server/device_config.py` (for `poll_loop.py`'s render gate) and,
duplicated in stdlib-only form, `stub-server/byos_server.py` (for the `sleep_s`
computation).
**Why this is DST-safe:** Subtracting two `zoneinfo`-aware `datetime` objects in Python
always computes the true elapsed wall-clock duration, because the subtraction happens
via each datetime's absolute UTC instant, not its local-time numerals — no manual
offset bookkeeping is needed even when a DST transition falls between "now" and the
window's end. [CITED: docs.python.org/3/library/zoneinfo.html]
**Example:**
```python
# New code for this phase — not yet in the codebase. Verified interactively
# against this project's own pinned interpreter during this research session
# (ZoneInfo("Europe/Paris") resolves without error).
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")


def _parse_hm(hhmm):
    h, m = hhmm.split(":")
    return int(h), int(m)


def seconds_until_quiet_hours_end(now_utc, start_hm, end_hm):
    """Return None if `now_utc` is outside the [start_hm, end_hm) window
    (in Europe/Paris wall-clock time; wraps midnight when end <= start),
    else the whole seconds remaining until the window's local end time.

    `now_utc` must be timezone-aware (e.g. datetime.now(timezone.utc)).
    `start_hm`/`end_hm` are "HH:MM" strings already validated by
    normalise_quiet_hours_time().
    """
    local_now = now_utc.astimezone(QUIET_HOURS_TZ)
    start_h, start_m = _parse_hm(start_hm)
    end_h, end_m = _parse_hm(end_hm)
    start_today = local_now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_today = local_now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

    if (start_h, start_m) <= (end_h, end_m):
        # Same-day window (e.g. a daytime "do not disturb" range).
        if not (start_today <= local_now < end_today):
            return None
        end_dt = end_today
    else:
        # Wraps midnight (e.g. 23:00-07:00, the curfew case).
        if local_now >= start_today:
            end_dt = end_today + timedelta(days=1)
        elif local_now < end_today:
            end_dt = end_today
        else:
            return None

    return max(0, int((end_dt - local_now).total_seconds()))
```
This same function (or a byte-for-byte duplicate — see Pitfall 1 below) also answers
"is now inside the window" (`seconds_until_quiet_hours_end(...) is not None`) and
"what local HH:MM should the screen say" (`end_dt.strftime("%H:%M")`, computed once
inside the function and returned alongside, or recomputed by the caller from the same
inputs) — `poll_loop.py`'s render gate needs both; `byos_server.py`'s `sleep_s`
computation needs only the seconds-remaining value.

### Pattern 3: Render-dispatch extension (follow the "empty" state exactly)

**What:** `server/plane/render.py`'s `build_canvas()` already dispatches on a `state`
string (`"empty"` vs. everything else); this phase adds one more branch.
**When to use:** Adding the D-05 quiet-hours screen.
**Example:**
```python
# Source: server/plane/render.py, existing dispatch at line 2034 —
# "if flight is None or state == 'empty': return _build_empty_canvas(...)"
def build_canvas(
    flight, state, route=None, previous_flight=None, previous_route=None, previous_state=None,
    theme_id=device_config.DEFAULT_THEME_ID, runway_id=device_config.DEFAULT_RUNWAY_ID,
    source_fault=False, battery_low=False, quiet_hours_until=None,
):
    if state == "quiet_hours":
        return _build_quiet_hours_canvas(
            quiet_hours_until=quiet_hours_until, battery_low=battery_low)
    if flight is None or state == "empty":
        return _build_empty_canvas(
            runway_id=runway_id, source_fault=source_fault, battery_low=battery_low)
    return _build_active_canvas(...)  # unchanged
```
`_build_quiet_hours_canvas()` should follow `_build_empty_canvas()`'s exact body shape
(`server/plane/render.py` lines 1740-1798): a flat `IDX_WHITE` canvas, `EMPTY_INK`
(`IDX_BLACK`) text, a centered heading ("QUIET HOURS") + body ("Back at 07:00") built
from `quiet_hours_until`, using the same `fit_text_size()`/`_wrap_text()`/
`_assert_in_safe_box()` machinery already proven there — this state is, structurally,
the same "flat informational screen, always White/Black regardless of theme" shape the
empty state already establishes, so no new drawing primitive is needed. Whether the
battery-low icon and/or source-fault badge should also render on this screen is left to
planning/the developer's real-preview review (see Claude's Discretion in
`10-CONTEXT.md`) — `_build_empty_canvas()`'s existing precedent is to show both, since
they are device-health facts independent of what's on screen.

### Pattern 4: Vendored stdlib-only local modification (follow `read_led_enabled()` exactly)

**What:** `stub-server/byos_server.py` is a **pinned, vendored, stdlib-only** file
(`stub-server/VENDOR.md`). It must never import `server.device_config` or any other
project module — not just as a style preference, but because doing so would require
adding a `sys.path` bootstrap this file has never needed, would blur the vendor
provenance boundary `VENDOR.md` exists to track, and would break the file's own
docstring's "Stdlib only" claim.
**When to use:** Reading `device_config.json`'s new quiet-hours fields from inside
`byos_server.py`'s `/display` handler.
**Example:**
```python
# Source: stub-server/byos_server.py, existing read_led_enabled() (lines 85-105) —
# this phase's read_quiet_hours() follows the identical fail-open shape.
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # stdlib since 3.9 — does NOT violate "stdlib only"

QUIET_HOURS_TZ = ZoneInfo("Europe/Paris")
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def read_quiet_hours(state_dir):
    """Best-effort read of device_config.json's quiet-hours fields. Never
    raises. Returns None (== "not in effect") on: a missing/unreadable
    file, malformed JSON, a non-dict document, quiet_hours_enabled not
    literally True, or either time string failing _HHMM_RE - mirroring
    read_led_enabled()'s fail-open contract (a bad config must never
    block a normal poll response).
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("quiet_hours_enabled") is not True:
        return None
    start, end = data.get("quiet_hours_start"), data.get("quiet_hours_end")
    if not (isinstance(start, str) and _HHMM_RE.match(start)
            and isinstance(end, str) and _HHMM_RE.match(end)):
        return None
    return start, end


def quiet_hours_sleep_s(base_sleep_s, state_dir, now=None):
    """D-01: return base_sleep_s unchanged unless `now` falls inside the
    configured window, in which case return the value spanning past the
    window's end - never shorter than base_sleep_s (Claude's Discretion
    item in 10-CONTEXT.md). `now` is an injectable seam for tests,
    mirroring poll_loop.py's own now_s() pattern.
    """
    window = read_quiet_hours(state_dir)
    if window is None:
        return base_sleep_s
    now = now or datetime.now(timezone.utc)
    remaining = seconds_until_quiet_hours_end(now, window[0], window[1])  # Pattern 2
    if remaining is None:
        return base_sleep_s
    return max(base_sleep_s, remaining)
```
Then in the `/device/v1/display` GET handler, replace the literal
`"sleep_s": self.args.sleep` with
`"sleep_s": quiet_hours_sleep_s(self.args.sleep, self.args.state_dir)`.

### Anti-Patterns to Avoid

- **Importing `server.device_config` (or anything under `server.*`) into
  `stub-server/byos_server.py`:** breaks the vendored/stdlib-only contract
  `stub-server/VENDOR.md` exists to enforce, and there is no `sys.path` bootstrap in
  this file to make the import even resolve today.
- **Putting the D-05 render decision inside `byos_server.py`'s `/display` handler:**
  this file has no rendering capability (no Pillow import, no `render.py` access) and
  must not gain one — the correct owner is `poll_loop.py`, which already renders and
  writes `panel.bin` on its own independent cadence.
- **Re-rendering the quiet-hours screen every 30-second `poll_loop.py` cycle for the
  whole duration of the window:** violates the project's established "no unnecessary
  refresh" ethos (the exact same discipline `run_once()`'s existing D-04 hold branch
  and the CFG-05/battery-changed-transition-only re-render already apply) and would
  keep the e-ink panel refreshing all night for zero new information. Render once on
  entry, then hold, exactly like the existing hold branches.
- **Naive local-time arithmetic** (e.g. `datetime.utcnow() + timedelta(hours=1)` to
  "approximate" Paris time, or hardcoding a fixed UTC offset like `+1`/`+2`): silently
  wrong for half the year across the March/October DST transitions. Always go through
  `ZoneInfo("Europe/Paris")`-aware datetimes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Europe/Paris local-time + DST conversion | A manual UTC-offset table, or a `+1`/`+2` hardcoded seasonal switch | stdlib `zoneinfo.ZoneInfo("Europe/Paris")` | France's DST transition dates shift slightly year to year and are defined by EU directive, not a fixed calendar rule simple enough to hand-roll correctly; the IANA tzdata `zoneinfo` reads from is the canonical, continuously-maintained source |
| "HH:MM" input validation | A hand-rolled string-split-and-`int()`-with-try/except | A single compiled regex (`_HHMM_RE`), checked with `isinstance(value, str) and _HHMM_RE.match(value)` before ever calling `int()` on user input | Matches this project's own established pattern (`server/device_config.py`'s membership-test-before-dict-lookup discipline, `T-06-01-01`/ASVS V5) — untrusted input must never reach a parser call it could make raise before its shape is checked |

**Key insight:** Every piece of this phase's genuinely new logic (window membership,
seconds-remaining, HH:MM validation) is under ~30 lines of pure, deterministic
arithmetic with zero external I/O — exactly the kind of code this project already
covers with a stdlib-only `check()`-harness unit test rather than any new testing
infrastructure.

## Common Pitfalls

### Pitfall 1: Duplicating window arithmetic across the vendor boundary can drift

**What goes wrong:** `server/device_config.py`'s window-arithmetic helper and
`stub-server/byos_server.py`'s duplicated copy (Pattern 4) could be edited
independently over time and silently diverge — e.g. one gets an off-by-one fix the
other doesn't.
**Why it happens:** The vendor/stdlib-only boundary makes a shared import impossible
(Pattern 4's Anti-Pattern above); duplication is the only option, same as this
project's existing precedent (`read_led_enabled()` duplicates JSON-read logic rather
than importing `device_config.load_device_config()`).
**How to avoid:** Keep the duplicated function byte-for-byte identical (copy-paste, not
"reimplemented from memory"), and add a one-line comment in each copy pointing at the
other (`stub-server/VENDOR.md`'s existing modification-log entries already model this
cross-reference style for `read_led_enabled()`/`parse_battery_mv()`). Cover both copies
with their own test harness (`server/test_config_history.py` and
`stub-server/test_poll_cycle.py` respectively) so a regression in either is caught
independently.
**Warning signs:** A quiet-hours behavior bug report that only reproduces in one of the
two processes (e.g. the screen shows the wrong "Back at" time but `sleep_s` is correct,
or vice versa) is the tell that the two copies have drifted.

### Pitfall 2: DST transition falling inside the configured window boundary

**What goes wrong:** France's DST transitions happen at 02:00->03:00 (spring, last
Sunday in March) and 03:00->02:00 (autumn, last Sunday in October) local time. If a
configured quiet-hours start or end time lands inside that exact 1-hour transition
window on the transition date, `datetime.replace(hour=..., minute=...)` on a
`zoneinfo`-aware datetime can construct a "nonexistent" (spring) or "ambiguous"
(autumn) local time. Per PEP 495, Python does not raise for either case — a
nonexistent spring-forward time resolves using the pre-transition offset (silently
off by up to an hour for that one specific instant), and an ambiguous autumn time
resolves via the `fold` attribute (defaulting to `fold=0`, the pre-transition
occurrence). [CITED: docs.python.org/3/library/zoneinfo.html]
**Why it happens:** A curfew-style window (e.g. `23:00`-`07:00`) makes this essentially
never triggerable in practice — Orly-area curfews are evening/overnight, and the
transition itself happens at 2-3am, so only a window boundary configured inside that
specific hour on that specific one-or-two-nights-a-year date is affected.
**How to avoid:** Document the caveat rather than engineering around it (Pattern 2's
subtraction-based arithmetic is already correct for every other case, including the
window merely *spanning* a DST transition — only a boundary *landing inside* the
transition hour itself is affected). Given D-01's safety net ("never make sleep_s
shorter than it would otherwise be"), the worst realistic outcome is the device staying
asleep up to one hour longer or shorter than intended, twice a year, only if the
window's exact boundary sits inside the transition hour — low severity, not worth a
defensive `fold=1` override for a curfew feature.
**Warning signs:** None expected in normal use; if it ever surfaces, it will be a
report of the frame waking up "an hour early/late" specifically on the last Sunday of
March or October.

### Pitfall 3: Forgetting `poll_loop.py` keeps running every 30 seconds during quiet hours

**What goes wrong:** Assuming `poll_loop.py`'s systemd timer pauses or should pause
during the quiet-hours window, the way the *device* does. It does not, and should not —
`poll_loop.py` runs on the always-on VPS, not the battery-powered device, so there is no
battery-conservation reason to stop it, and stopping it would actually work against
D-07 (the window-exit transition needs `poll_loop.py` to already be running normally by
the time the device next wakes, so the very first post-window poll gets the live board,
not a stale one).
**Why it happens:** The two "sleep" concepts in this phase's name are easy to conflate
— the *device's* sleep (extended, via `sleep_s`) and the *server's* poll cadence
(unchanged, still 30s).
**How to avoid:** Keep `poll_loop.py`'s systemd timer/cadence completely untouched.
Only gate what it *renders* during the window (Pattern 3's dispatch), not whether it
*runs*.
**Warning signs:** If `poll_loop.py`'s systemd unit were ever modified to skip
cycles during quiet hours, the symptom would be a stale (pre-window) board showing
briefly on the very first device poll after the window ends, before the next 30s
cycle catches up — visibly violating D-07's "no intermediate transition state" intent
via a different mechanism than the one D-07 explicitly rejected.

### Pitfall 4: Rendering the flight-detection pipeline unnecessarily during the window

**What goes wrong:** If `poll_loop.py`'s quiet-hours gate is inserted *after* the
existing ADS-B detection call rather than before it, every 30-second cycle during an
up-to-8-hour overnight window still queries the free-tier ADS-B aggregators
(`detect.poll_current_aircraft()`) for a result that gets thrown away.
**Why it happens:** The most surgical-looking insertion point (right before the
existing `if flight is not None:` branching, since that's where every other state
decision already happens) is technically after detection has already run.
**How to avoid:** Not a locked decision (10-CONTEXT.md leaves this to discretion), but
the research recommendation is: insert the quiet-hours check as an early return near
the very top of `run_once()`, before `detect.poll_current_aircraft()`/`geofence`
loading — when currently in the window (whether newly entered or continuing), skip
detection entirely for that cycle. This both avoids wasted ADS-B calls and keeps the
"render once, then hold" logic simple (no detection result to reconcile against the
pending-flight queue while quiet hours are active).
**Warning signs:** Elevated ADS-B aggregator request counts overnight with zero
corresponding panel changes in the gallery/history log.

## Code Examples

### Companion Settings fieldset (mirrors `led_group()` exactly)

```python
# Source: companion/pages/config_page.py's existing led_group() (lines 348-400) —
# this project's own established pattern, adapted for two time inputs alongside
# the enabled checkbox. Exact copy text/spacing is left to planning's real-preview
# review (10-CONTEXT.md Claude's Discretion), matching sketch-findings-skypane's
# documented "one caption per section" rule (Settings Page Patterns reference).
QUIET_HOURS_CHECKBOX_VALUE = "on"  # same literal LED_CHECKBOX_VALUE already uses

def quiet_hours_group(current_enabled, current_start, current_end):
    checked = " checked" if current_enabled else ""
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<label class="led-checkbox">'
        '<input type="checkbox" name="quiet_hours_enabled" value="%s"%s> Enable quiet hours'
        "</label>"
        '<label>Start <input type="time" name="quiet_hours_start" value="%s"></label>'
        '<label>End <input type="time" name="quiet_hours_end" value="%s"></label>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html("Quiet hours"),
        escape_html("Quiet hours"),
        escape_html(QUIET_HOURS_SECTION_CAPTION),
        escape_html(QUIET_HOURS_CHECKBOX_VALUE), checked,
        escape_html(current_start), escape_html(current_end),
    )
```
`<input type="time">` submits an "HH:MM" string natively (or is omitted if left
genuinely empty by the browser) — this is the first `type="time"` input anywhere in
`companion/static/style.css`; confirm it inherits the existing global `input, select`
touch-target/sizing rule cleanly during a real-browser check (`references/
control-density.md`'s touch-target floor register does not yet have an entry for this
input type).

### `handle_post()` extension — absent-checkbox semantics matching `led_enabled`

```python
# Source: companion/pages/config_page.py's existing handle_post() (lines 674-751) —
# the LED field's "absent means False" rule (an unchecked HTML checkbox is omitted
# from the POST body entirely) applies identically to quiet_hours_enabled.
submitted_qh_enabled = form.get("quiet_hours_enabled")
qh_enabled = submitted_qh_enabled == QUIET_HOURS_CHECKBOX_VALUE  # False if absent/anything else... but see note below
submitted_qh_start = form.get("quiet_hours_start")
submitted_qh_end = form.get("quiet_hours_end")
if submitted_qh_start is not None and not device_config._HHMM_RE.match(submitted_qh_start):
    return FLASH_SAVE_FAILED
if submitted_qh_end is not None and not device_config._HHMM_RE.match(submitted_qh_end):
    return FLASH_SAVE_FAILED
```
Note: unlike `led_enabled` (a checkbox with no accompanying data fields), an
*unchecked* quiet-hours checkbox should probably still accept and save valid start/end
edits (so a user can pre-configure a window before ever enabling it) — this exact
absent-vs-reject semantics for the two time fields relative to the checkbox is left to
planning to decide explicitly (it is not the same shape as `led_enabled`'s single-field
case, and `10-CONTEXT.md` does not address it).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `sleep_s` is a fixed CLI value (`--sleep`, `SKYPANE_SLEEP_S=30` in production) | `sleep_s` becomes conditionally computed per-request, extended during quiet hours | This phase | `deploy/skypane.env`'s `SKYPANE_SLEEP_S` env var remains the *base* value (used whenever quiet hours are inactive or disabled) — no deployment/env change needed, only code inside `byos_server.py` |

**Deprecated/outdated:** Nothing in this phase deprecates prior work — this is a pure
additive change layered on top of the existing config-registry/render-dispatch/
local-modification patterns.

## Runtime State Inventory

Not applicable — this is a net-new feature addition (new config fields, new render
state, new sleep_s branch), not a rename/refactor/migration. No existing stored data,
live service config, OS-registered state, secret/env-var names, or build artifacts
reference "quiet hours" or any prior name for this concept anywhere in the repo
(confirmed via `grep -rn "quiet.hours\|curfew" --include="*.py" --include="*.json"
--include="*.service"` returning zero hits outside `.planning/`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | An *unchecked* quiet-hours checkbox should still accept and persist edited start/end times (rather than the whole submission being treated as "disable and ignore the time fields") | Code Examples — `handle_post()` extension | Low — if wrong, the fix is a one-line semantics change in `handle_post()`, no data-shape change; flagged explicitly as undecided so planning makes this call deliberately rather than by accident |
| A2 | The quiet-hours screen should show both the battery-low icon and the source-fault badge when applicable (matching `_build_empty_canvas()`'s existing precedent), rather than a bare informational screen | Architecture Pattern 3 | Low — purely visual; `10-CONTEXT.md` already flags the exact pixel layout as pending a real-preview review, so this is easily adjusted then |
| A3 | Europe/Paris is correctly hardcoded (not a per-device/user setting) | Standard Stack — Alternatives Considered | Very low — the device has exactly one fixed physical location per `PROJECT.md`; would only be wrong if the project ever supported multiple simultaneous installs in different timezones, which no seed or roadmap phase proposes |

**Confidence:** All three assumptions are LOW risk, and none blocks planning — each has
a stated, cheap correction path.

## Open Questions

1. **Should quiet hours be visually distinguishable from the empty state at a glance,
   or is "flat White/Black + centered heading/body" (identical structural treatment,
   different copy) sufficient?**
   - What we know: `10-CONTEXT.md` D-05/D-06 lock the copy shape ("QUIET HOURS" / "Back
     at HH:MM") and the language (English), and explicitly defer exact pixel
     layout/typography to a real-preview review, the same discipline `05-CONTEXT.md`
     used for the battery icon.
   - What's unclear: whether reusing `_build_empty_canvas()`'s exact visual structure
     (as Pattern 3 recommends) reads as "confusingly similar to the empty state" on
     real glass, or whether a distinct visual treatment (e.g. a different flat color,
     matching `05-CONTEXT.md`'s "deliberate exception" framing more visibly) is
     warranted.
   - Recommendation: build the simplest version first (Pattern 3's empty-state-shaped
     reuse) and validate it against a real on-glass or on-screen preview before
     locking the final layout — exactly the workflow `05-CONTEXT.md`'s battery icon
     and `03-CONTEXT.md`'s two-flight poster redesign both already used successfully.

2. **Does an *unchecked* quiet-hours checkbox still save edited start/end times?**
   - What we know: `led_enabled`'s existing pattern has no analogous "accompanying
     data fields" case to copy from directly.
   - What's unclear: the developer's actual intent — this was not raised during
     `/gsd-discuss-phase 10`.
   - Recommendation: default to "yes, time fields save independently of the enabled
     checkbox" (Assumption A1) since it lets a user pre-configure a window before
     toggling it on, and is the less surprising behavior of the two options; confirm
     with the developer if the planner wants certainty before committing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `zoneinfo` stdlib module | Window arithmetic (both `device_config.py` and `byos_server.py`) | Yes | Bundled since Python 3.9; project pins 3.11/3.12 | None needed |
| System IANA tzdata (`/usr/share/zoneinfo`) | `zoneinfo.ZoneInfo("Europe/Paris")` resolution | Yes | Confirmed present on this dev machine (`ZoneInfo('Europe/Paris')` resolved with exit 0) and expected on both the Ubuntu 26.04 LTS deploy target (`deploy/provision.sh`) and GitHub Actions' `ubuntu-latest` CI runner — both ship system tzdata by default | If ever absent: `pip install tzdata` (PyPI fallback package `zoneinfo` itself documents) would be the only new dependency this phase could ever need, and only in that failure case |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none currently missing — tzdata's PyPI fallback
is documented here defensively but is not expected to be needed.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Custom stdlib-only `check(name, fn)` harness convention (no pytest/unittest anywhere in this repo) — every test file defines its own `EXPECTED_CHECK_COUNT` guard and exits non-zero if the actual pass count doesn't match it exactly |
| Config file | `pyproject.toml`'s `[tool.coverage.*]` sections (coverage threshold: 83%, `fail_under = 83`); no pytest config exists |
| Quick run command | `server/.venv/bin/python3 <harness>.py` (e.g. `server/.venv/bin/python3 server/test_config_history.py`) |
| Full suite command | `scripts/run-all-tests.sh` (runs all 16 harnesses under `coverage`, combines, enforces the threshold) |

### Phase Requirements -> Test Map

No requirement IDs are mapped to this phase (see `<phase_requirements>` above). Test
coverage is instead mapped directly to this phase's decisions:

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01 (sleep_s extension) | Inside the window, `/display`'s `sleep_s` reflects the remaining window time and is never shorter than `--sleep` | unit + integration | `server/.venv/bin/python3 stub-server/test_poll_cycle.py` | ✅ (extend existing 23-check harness) |
| D-01 (fail-open) | A missing/malformed/hostile `device_config.json` degrades `sleep_s` to the unchanged base value | unit | same file as above | ✅ |
| D-03/D-04 (registry) | `normalise_quiet_hours_enabled/start/end()` degrade hostile values to documented defaults; `save_device_config()` rejects invalid submitted values with `ValueError` and leaves the file untouched | unit | `server/.venv/bin/python3 server/test_config_history.py` | ✅ (extend existing 30-check harness) |
| D-05 (render once) | Entering the window renders the quiet-hours canvas exactly once and sets `poll_state["quiet_hours_active"]`; remaining inside the window on a later cycle is a no-op (no re-render); exiting the window resumes normal detection on the very next cycle with no transition screen (D-07) | unit + integration | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ (extend existing 44-check harness) |
| D-05/D-06 (screen content) | `build_canvas(None, "quiet_hours", quiet_hours_until="07:00")` produces a legal-palette, in-safe-box canvas with the correct heading/body text | unit | `server/.venv/bin/python3 server/test_render.py` | ✅ (extend existing 119-check harness) |
| Settings UI | The new fieldset renders with correct pre-filled values and correct `checked` state; `handle_post()` validates/rejects malformed HH:MM strings and persists correctly | unit | `server/.venv/bin/python3 companion/test_config_page.py` (note: despite the path, this harness is run via the server venv per `scripts/run-all-tests.sh`) | ✅ (extend existing 64-check harness) |

### Sampling Rate
- **Per task commit:** run the single harness touched by that task (e.g.
  `server/.venv/bin/python3 server/test_config_history.py` after editing
  `device_config.py`).
- **Per wave merge:** `scripts/run-all-tests.sh` (all 16 harnesses + coverage
  threshold).
- **Phase gate:** Full suite green, plus `server/.venv/bin/python3 -m ruff check .`
  (blocking lint per CI), before `/gsd-verify-work`.

### Wave 0 Gaps

None — every harness this phase touches already exists and already has the
`EXPECTED_CHECK_COUNT` convention in place. The only mechanical requirement is
incrementing each touched file's `EXPECTED_CHECK_COUNT` constant by exactly the number
of new `check(...)` calls added (current counts, for reference: `test_config_history.py`
= 30, `test_poll_cycle.py` = 23, `test_poll_loop.py` = 44, `test_render.py` = 119,
`test_config_page.py` = 64) — a mismatch fails the harness by design (a deliberate
guard against a silently-skipped check), so this must be updated in the same commit as
the new checks, not left for later.

An injectable `now` seam should be added to both `quiet_hours_sleep_s()` (in
`byos_server.py`) and whatever `poll_loop.py`-side helper computes "in window now" — the
same testable-seam discipline `poll_loop.py`'s own `now_s()` already establishes —
specifically so the new tests can drive DST-crossing and window-boundary scenarios
deterministically rather than depending on real wall-clock timing during a test run.

## Security Domain

`security_enforcement` is enabled (`.planning/config.json`, `security_asvs_level: 1`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | No new auth surface — the companion Settings page's existing single shared-password gate (`06-CONTEXT.md` D-01/D-02) already covers the new fieldset; `byos_server.py`'s existing bearer-token gate on `/device/v1/display` is unchanged |
| V3 Session Management | No | Unchanged |
| V4 Access Control | No | Unchanged — same single-password gate covers every Settings-page field uniformly, new or old |
| V5 Input Validation | Yes | The two new HH:MM strings and the enabled boolean are untrusted POST input, same trust boundary as `theme`/`tracked_runway`/`led_enabled` already cross. Validate with `_HHMM_RE.match()` (membership-test-before-use, matching `normalise_theme_id()`'s registry-membership discipline) before ever passing a value to `datetime.replace()` or persisting it — never pass a raw submitted string into a `datetime()` constructor without the regex gate first, since a malformed value there raises `ValueError` deep inside a request handler rather than failing the documented, controlled way `handle_post()`'s existing fields already do |
| V6 Cryptography | No | No cryptographic operation in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Malformed/hostile `quiet_hours_start`/`_end` strings crashing a request handler (e.g. `"25:99"`, `"'; DROP"`, a huge string) reaching `datetime.replace(hour=..., minute=...)` uncaught, which raises `ValueError` | Denial of Service | Gate every use behind `_HHMM_RE.match()` first (Pattern 1/Pattern 2) — exactly the same "membership test before dict/constructor use" discipline `T-06-01-01` already established project-wide for `theme`/`tracked_runway` |
| A read-path config value (`device_config.json` hand-edited or corrupted on disk) reaching `byos_server.py`'s `/display` handler and raising, taking down the single always-on device-protocol service for every future poll until manually restarted | Denial of Service | `read_quiet_hours()`'s fail-open contract (Pattern 4): any failure mode degrades to `None` ("quiet hours not in effect," i.e. the pre-existing unmodified `sleep_s` behavior) — never raises, matching `read_led_enabled()`'s existing fail-open precedent exactly |
| Companion-page time inputs used as an information-disclosure or injection vector (e.g. reflecting the raw submitted string back into an error page without escaping) | Tampering / Information Disclosure | Route every rendered value through `escape_html()`, exactly as `led_group()`/`theme_fieldset()` already do for their own current-value interpolations |

## Sources

### Primary (HIGH confidence)
- Direct codebase reads (`server/device_config.py`, `server/poll_loop.py`,
  `server/plane/render.py`, `stub-server/byos_server.py`, `stub-server/VENDOR.md`,
  `companion/pages/config_page.py`, `companion/app.py`, `deploy/*.service`,
  `deploy/skypane.env.example`, `deploy/provision.sh`, `.github/workflows/ci.yml`,
  `pyproject.toml`) — read live during this research session.
- [VERIFIED: local execution] `python3 -c "from zoneinfo import ZoneInfo;
  ZoneInfo('Europe/Paris')"` — exit 0, this dev machine, confirming the stdlib module
  and system tzdata both resolve correctly.

### Secondary (MEDIUM confidence)
- [CITED: docs.python.org/3/library/zoneinfo.html] — `zoneinfo`'s DST-arithmetic and
  `fold`/ambiguous-time semantics (WebSearch, cross-referencing official Python
  documentation).

### Tertiary (LOW confidence)
- None — every claim in this document is either a direct codebase read, a locally
  executed verification, or an official-documentation citation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib-only, verified by direct execution against this
  project's own pinned interpreter and deploy target OS
- Architecture: HIGH - every pattern this phase needs already exists in the codebase
  as a directly-read, working precedent (`led_enabled`, `read_led_enabled()`,
  `_build_empty_canvas()`'s dispatch, `battery_low_active`-style hysteresis flags)
- Pitfalls: MEDIUM-HIGH - the DST-transition-inside-boundary edge case (Pitfall 2) is
  a real, documented Python behavior but has genuinely low practical impact for a
  curfew-shaped window; every other pitfall is derived directly from this codebase's
  own established conventions

**Research date:** 2026-09-03
**Valid until:** No expiry driver — stdlib behavior and this codebase's own established
patterns are both stable; re-verify only if Phase 11 (web-configurable wake interval)
lands first and changes `byos_server.py`'s `/display` handler's `sleep_s` computation
shape before this phase does.
