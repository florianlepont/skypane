# Phase 17: Connect a calendar from the companion instead of over SSH - Pattern Map

**Mapped:** 2026-09-09
**Files analyzed:** 5 (2 modified extensively, 3 with targeted edits)
**Analogs found:** 5 / 5

**Divergence note (tree moved since RESEARCH.md):** `claude/t-16-priv-retention` merged (commit
862425e) before this mapping. `load_calendar_registry(state_dir, now=None)`,
`write_calendar_registry(state_dir, entries, last_attempt_at, last_synced_at, now=None)` and
`_rebuild_capped_entries(raw_entries, context, now)` now all take a `now` parameter that RESEARCH.md's
excerpts (written pre-merge) do not show — confirmed by reading `server/plane/calendar_rules.py` at
HEAD directly (lines 699, 769, 630). `server/test_calendar_rules.py` is at 80 checks (38 —not
26 as RESEARCH.md estimated— `CALENDAR_URL_ENV_VAR` references, confirmed via `grep -c`), not 76.
VALIDATION.md's baseline (80/80, measured 2026-09-09 after the merge) is correct and is what the
planner should target; RESEARCH.md's "76" and "~26 references" are both stale. Any new secret-file
function the plan adds to `calendar_rules.py` that touches retention (none should — D-01's file
holds only the URL, not entries) would need to thread `now` the same way; the disconnect/replace
path (D-04/D-05) calls `write_calendar_registry(state_dir, [], None, None, now=...)` to erase
entries, and `now` must be supplied there too, not omitted.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog (same file, different function) | Match Quality |
|---|---|---|---|---|
| `server/plane/calendar_rules.py` — new `save_calendar_url()` / `calendar_secret_path()` / `CLEAR_CALENDAR_URL` | service (file I/O) | file-I/O, CRUD | `write_calendar_registry()` §769 (structure) + `device_config.py` `CLEAR_THEME_ARRIVING` §111 (sentinel) | role-match, deliberate divergence on one line |
| `server/plane/calendar_rules.py` — `calendar_is_configured()` / `configured_calendar_url()` rewritten | service (accessor) | file-I/O, request-response | `companion/auth.py` `configured_password()` §64 (fail-closed accessor shape) | role-match |
| `server/plane/calendar_rules.py` — `refresh_calendar_registry()` gains `min_interval_s` | service (orchestration) | request-response | itself, pre-existing `calendar_fetch_is_due()` §842 which already accepts the parameter | exact (same function, additive) |
| `companion/pages/config_page.py` — `calendar_group()` + copy constants | component (server-rendered form) | request-response | `theme_fieldset()` §421 (checkbox-gated clear signal) | exact (D-07 explicitly models this) |
| `companion/pages/config_page.py` — `handle_post()` branch | controller (form validation) | CRUD | its own `theme_arriving_enabled` branch §1733-1738 | exact |
| `companion/app.py` — POST `/settings` D-06 sync trigger | controller (request-response, in-process trigger) | event-driven / request-response | `_handle_poll_now()` §1912 | exact |
| `deploy/skypane.env.example` | config | — | itself (line removal) | n/a — no analog needed |
| `server/test_calendar_rules.py` fixture rewrite | test | CRUD | its own `_secret_never_reaches_the_file_or_the_log` env-fixture pattern §742 | exact (same file) |

## Pattern Assignments

### `server/plane/calendar_rules.py` — the secret file writer (D-01)

**Analog:** `write_calendar_registry()`, lines 769-812 (current tmp-write block, post-merge — the
`now` parameter is already present at HEAD and must stay).

**Current idiom to structurally copy** (tmp-write-then-replace shape, minus the registry-specific
rebuild/lock logic which does not apply to a one-line secret file):

```python
path = calendar_rules_path(state_dir)
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
    return False
```

**The one line that must differ, and why (impossible to miss on purpose):**

```python
# COPY THIS SHAPE VERBATIM (tmp-naming, makedirs, os.replace, cleanup-on-
# exception) — but the file-open call is NOT `open(tmp, "w")` like every
# other state write in this codebase. It is:
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as fh:
    fd = None  # fdopen() now owns the fd; do not close it again in except
    fh.write(value.strip())
# ^ THIS LINE IS THE ENTIRE REASON THIS FUNCTION EXISTS SEPARATELY FROM
# write_calendar_registry(). `open(tmp, "w")` creates at the process umask
# (0644 in practice) — deploy/provision.sh:76-77 makes files in state_dir
# group-readable by `caddy`, the internet-facing reverse proxy. `os.open()`
# with an explicit mode is the ONLY point in this codebase's history where
# a file's mode is a security property rather than a umask default. Setting
# it via `os.chmod()` after the write, instead of at `os.open()`, is the
# exact anti-pattern D-01 forbids: it leaves a window where the file exists
# at 0644. Never copy this file's writer without re-deriving this line.
```

`CLEAR_CALENDAR_URL` sentinel — copy `device_config.CLEAR_THEME_ARRIVING`'s shape exactly
(`server/device_config.py:111`, `object()`, compared by `is`, never seen by any loader):

```python
CLEAR_CALENDAR_URL = object()  # identity-compared; save_calendar_url()'s write path only
```

`save_calendar_url()` branches on `value is CLEAR_CALENDAR_URL` → `os.remove(path)` (tolerating
`OSError`/absence) vs. the write-with-0600 path above. Never raises; returns `True`/`False`,
matching `write_calendar_registry()`'s own contract.

---

### `server/plane/calendar_rules.py` — the secret file reader + D-02's mode guard

**Analog 1 — never-raising loader shape:** `load_calendar_registry()`, lines 699-767. Copy the
`try: ... except (OSError, ValueError): data = {}` never-raise discipline, not the JSON-specific
rebuild logic (the secret file is plain text, one line, no entries/cap/window concept applies).

**Analog 2 — the accessor pair being replaced:** `configured_calendar_url()`, lines 527-543
(current HEAD, env-backed):

```python
def configured_calendar_url():
    raw = os.environ.get(CALENDAR_URL_ENV_VAR)
    if not isinstance(raw, str):
        return None
    stripped = raw.strip()
    return stripped or None
```

New shape swaps the source and adds D-02's mode check, matching Pattern 4 verified in RESEARCH.md:

```python
def _calendar_secret_mode_is_safe(path):
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return None  # doesn't exist — not a permission problem, "not configured"
    return not (mode & (stat.S_IRWXG | stat.S_IRWXO))

def configured_calendar_url():
    path = calendar_secret_path(state_dir)  # NOTE: needs state_dir now — every
    # call site of configured_calendar_url()/calendar_is_configured() must be
    # audited for this new required argument; the env-backed version took none.
    if _calendar_secret_mode_is_safe(path) is not True:
        return None  # refuse silently — D-02: never read the value when the
                      # mode has drifted, whether absent or too permissive
    try:
        with open(path) as fh:
            raw = fh.read()
    except OSError:
        return None
    stripped = raw.strip()
    return stripped or None
```

**D-08 — `calendar_is_configured()` keeps a plain `bool`; a second, narrow accessor answers "off
because the mode drifted":**

```python
def calendar_is_configured(state_dir):
    return configured_calendar_url(state_dir) is not None

def calendar_secret_mode_is_unsafe(state_dir):
    """Narrowly-scoped: True only when the file exists AND its mode is
    too permissive. Consulted by config_page.calendar_group() alone for
    the fourth status branch — never widens calendar_is_configured()'s
    bool contract (D-08)."""
    path = calendar_secret_path(state_dir)
    return _calendar_secret_mode_is_safe(path) is False
```

**Every existing call site of `calendar_is_configured()` / `configured_calendar_url()` changes
signature from zero-arg to `(state_dir)`** — this is new work RESEARCH.md's excerpt (pre-signature-
change) does not show; grep `companion/app.py:1023`, `config_page.py:928` and
`server/poll_loop.py`'s call into `refresh_calendar_registry()` (which itself calls
`configured_calendar_url()` internally) for every site that needs the new argument threaded through.

---

### The disconnect checkbox (D-07)

**Analog — direction to invert:** `theme_arriving_enabled`'s branch, `companion/pages/config_page.py`
lines 1733-1738 (current HEAD):

```python
if submitted_theme_arriving_enabled is None:
    theme_arriving = device_config.CLEAR_THEME_ARRIVING
elif submitted_theme_arriving_enabled == ARRIVING_CHECKBOX_VALUE:
    theme_arriving = submitted_theme_arriving
else:
    return FLASH_SAVE_FAILED
```

That checkbox is rendered **checked** when a theme-arriving override is set, and its **absence**
(unchecked) means clear. Phase 17's checkbox must be the mirror image — rendered **unchecked** by
default, and its **presence** (checked) means disconnect:

```python
submitted_calendar_url = form.get("calendar_url")
submitted_calendar_disconnect = form.get("calendar_disconnect")  # checkbox name

if submitted_calendar_disconnect is not None and submitted_calendar_url:
    # D-07 contradiction: a non-empty URL together with the disconnect
    # box checked. Reject the whole save — same shape as the existing
    # else: branch above, not a new flash constant.
    return FLASH_SAVE_FAILED
if submitted_calendar_disconnect is not None:
    calendar_url = calendar_rules.CLEAR_CALENDAR_URL
elif submitted_calendar_url:
    calendar_url = submitted_calendar_url
else:
    calendar_url = None  # "carry forward" — untouched field, unrelated save
```

Note the three-way branch is genuinely different from `theme_arriving`'s two-way one: an *empty*
`calendar_url` with the box *unchecked* must mean "no change" (this is D-07's whole point — it
corrects D-04's original defect), not "clear". Only the checkbox triggers the clear branch.

**Server-side accessor divergence to also carry:** `server/device_config.py:111`'s
`CLEAR_THEME_ARRIVING` sentinel is consumed by `save_device_config()`. This phase's
`CLEAR_CALENDAR_URL` sentinel is consumed by the **new** `save_calendar_url()` in
`calendar_rules.py`, a separate call from `save_device_config()` — the calendar URL is not a
`device_config.json` key (RESEARCH.md Pitfall 4, still correct at HEAD: do not add a
`calendar_url_configured` key to `device_config.json`).

---

### The write-only field's markup and status states

**Analog:** `calendar_group()`, `companion/pages/config_page.py` lines 876-950+, and the locked
copy constants, lines 321-349 (current HEAD — confirms RESEARCH.md's line numbers are still
accurate for this file, unlike `calendar_rules.py`'s post-merge shift).

Current three-branch status resolution to extend to four branches (D-02's permission-drift state):

```python
if not configured:
    status_html = escape_html(CALENDAR_STATUS_NOT_CONFIGURED)
else:
    usable = (
        bool(last_synced_at)
        and layout.parse_iso(last_synced_at) is not None
        and layout.age_seconds(last_synced_at, now) is not None)
    if usable:
        timestamp_html = layout.concise_timestamp_html(last_synced_at, now, fallback="")
        status_html = "%s%s." % (
            escape_html(CALENDAR_STATUS_CONFIGURED_SYNCED_PREFIX), timestamp_html)
    else:
        status_html = escape_html(CALENDAR_STATUS_CONFIGURED_PENDING)
```

New shape: check `calendar_secret_mode_is_unsafe(state_dir)` **first**, before the `not configured`
branch (a mode-drifted file makes `calendar_is_configured()` return `False`, so without a first
check the drift state would be indistinguishable from genuine absence — exactly what D-02
requires be avoided).

**Copy constants to rewrite, not re-point (D-03):** lines 333-337 currently interpolate the env var
name —

```python
# Interpolates calendar_rules.CALENDAR_URL_ENV_VAR rather than retyping
# the literal, so this copy and the env var name can never drift apart.
CALENDAR_STATUS_NOT_CONFIGURED = (
    "Not configured. Set `%s` in `skypane.env` on the server to connect "
    "a calendar." % calendar_rules.CALENDAR_URL_ENV_VAR)
```

This entire string must be rewritten to describe pasting the URL into the field on this page — the
`%`-interpolation itself must be deleted (there is no longer an env var name to interpolate), and
per the phase's Specifics section, the copy must never name a file. A new fourth constant for the
permission-drift status (D-02) is new work with no existing constant to extend — it is the one
copy string permitted to reference "the server," since D-02 is explicitly the case where the
operator must act there.

---

### The save-triggered sync (D-06/D-09)

**Analog:** `_handle_poll_now()`, `companion/app.py` lines 1912-1941 (current HEAD, line numbers
match RESEARCH.md/CONTEXT.md's citations exactly — this function was not touched by the
`t-16-priv-retention` merge):

```python
def _handle_poll_now(self):
    if not _POLL_LOCK.acquire(blocking=False):
        return self.redirect(
            "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_ALREADY_RUNNING)))
    try:
        state_dir = self.args.state_dir
        remaining = poll_cooldown_remaining(state_dir)
        if remaining > 0:
            return self.redirect(
                "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_COOLDOWN)))
        try:
            poll_loop.run_once(state_dir=state_dir, geofence=self.args.geofence)
        except Exception:
            return self.redirect(
                "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_FAILED)))
        mark_poll_triggered(state_dir)
        return self.redirect(
            "%s?flash=%s" % (SETTINGS_ROUTE, quote(FLASH_KEY_POLL_TRIGGERED)))
    finally:
        _POLL_LOCK.release()
```

D-06/D-09's sync reuses `_POLL_LOCK` (D-09 — not a second lock) with the same non-blocking-acquire
→ "already running" flash shape, but calls `calendar_rules.refresh_calendar_registry(state_dir,
time.time(), min_interval_s=0)` directly — **not** `poll_loop.run_once()`, which runs a full
detection/render cycle this save does not need. On lock contention, the honest "already running"
answer is exactly `_handle_poll_now()`'s own, reused rather than reinvented. This call happens
**inside** the Settings POST handler, after `save_calendar_url()` succeeds, not as a separate route
— unlike `/poll-now`, which is its own endpoint.

**The failure message must be built from the classified `result_code`, never `str(exc)`:** consume
`refresh_calendar_registry()`'s `(result_code, registry)` return only. It is contractually
never-raising (verified by its own top-level `try/except Exception` at line ~1237), so no
`try/except` should ever wrap this call on the companion side — doing so and touching the exception
would reintroduce exactly the leak T-16-SECRET closed.

---

### The throttle-bypass parameter (D-06)

**Analog — the parameter already exists one level down:** `calendar_fetch_is_due(last_attempt_at,
now, min_interval_s=None)`, line 842 (confirmed present at HEAD, unchanged by the merge).

**Exact call site that must change:** `refresh_calendar_registry()`, line 1181 (current HEAD;
RESEARCH.md's `:1155` internal-call line number has drifted post-merge — re-locate via grep, not
by trusting the cited line number):

```python
def refresh_calendar_registry(state_dir, now, transport=None):
    ...
    if not calendar_fetch_is_due(registry["last_attempt_at"], now):
        return FETCH_SKIPPED_THROTTLED, registry
```

Becomes:

```python
def refresh_calendar_registry(state_dir, now, transport=None, min_interval_s=None):
    ...
    if not calendar_fetch_is_due(registry["last_attempt_at"], now, min_interval_s):
        return FETCH_SKIPPED_THROTTLED, registry
```

`server/poll_loop.py`'s existing call must remain byte-for-byte unchanged (no `min_interval_s`
argument passed, defaulting to `None`, which `calendar_fetch_is_due()` already resolves to
`CALENDAR_FETCH_INTERVAL_S`). Only `companion/app.py`'s new D-06 call site passes
`min_interval_s=0`. This is genuinely new work, not a call-site option — confirmed by grep: no
caller anywhere threads a third positional/keyword argument today.

---

### The test-fixture rewrite (D-03)

**Current fixture shape** — `server/test_calendar_rules.py`, e.g. lines 742-778 (38 total
`CALENDAR_URL_ENV_VAR` references across the file, confirmed via `grep -c` at HEAD — RESEARCH.md's
estimate of "26 lines... roughly 13 distinct test functions" is stale; VALIDATION.md's 80/80
baseline already reflects the post-merge state and is the number to plan against):

```python
old_value = os.environ.get(cr.CALENDAR_URL_ENV_VAR)
os.environ[cr.CALENDAR_URL_ENV_VAR] = "https://example.invalid/feed.ics?token=%s" % token
try:
    ...  # test body
finally:
    if old_value is None:
        os.environ.pop(cr.CALENDAR_URL_ENV_VAR, None)
    else:
        os.environ[cr.CALENDAR_URL_ENV_VAR] = old_value
```

**What it must become** — a shared helper writing the secret file directly at the fixture's own
`tmp` state dir (no env save/restore dance needed at all, since each test already gets an isolated
`tempfile.TemporaryDirectory()`):

```python
def _write_calendar_secret(state_dir, url):
    """Test-only fixture helper — bypasses save_calendar_url()'s public
    contract to set up state directly, mirroring how other harnesses in
    this file seed calendar_rules.json directly via write_calendar_registry()
    rather than going through a public write API for setup."""
    cr.save_calendar_url(state_dir, url)
    # or, if a lower-level fixture is wanted: write the file directly at
    # cr.calendar_secret_path(state_dir) with mode 0600, to keep D-02's
    # mode check satisfied by every test that isn't specifically testing D-02.
```

Every one of the 38 references' surrounding `try/finally os.environ` dance is deleted — since the
secret now lives inside each test's own `tempfile.TemporaryDirectory()`, there is no cross-test
leakage to guard against and no restore-old-value step needed, unlike the environment variable
which was process-global. `EXPECTED_CHECK_COUNT` must land on exactly what VALIDATION.md's
per-task table implies (existing 80 plus new D-01/D-02/D-03/D-06/D-08 checks) — edit the count only
after every new `check(...)` call is registered, per this harness's fail-on-mismatch design.

## Shared Patterns

### Never-raising, fail-open accessor shape
**Source:** `server/plane/calendar_rules.py` `configured_calendar_url()` (existing shape, source
swapped) and `companion/auth.py:64` `configured_password()` (the fail-**closed** counterpart, for
contrast — do not copy its fail-closed behavior, only its per-call-no-caching shape).
**Apply to:** `configured_calendar_url()`, `calendar_is_configured()`, `calendar_secret_mode_is_unsafe()`.

### Identity-compared clear sentinel
**Source:** `server/device_config.py:111` `CLEAR_THEME_ARRIVING`.
**Apply to:** `CLEAR_CALENDAR_URL` in `calendar_rules.py`. Compared only by `is`, never surfaced to
any loader, never risked colliding with a crafted value.

### Non-blocking lock + honest "already running" redirect
**Source:** `companion/app.py:1912` `_handle_poll_now()`, `_POLL_LOCK`.
**Apply to:** the D-06 sync call inside the Settings POST handler — same lock object, same
`blocking=False` acquire, same flash-key redirect shape on contention.

### Opaque flash key, never the raw value
**Source:** `companion/app.py:449` `_resolve_flash_text()` and its `FLASH_MESSAGES` dict (line 224).
**Apply to:** D-06's outcome report — a new flash key per outcome bucket (connected-with-count,
generic-failure, disconnected), resolved server-side from fresh disk state
(`len(load_calendar_registry(...)["entries"])`), never carrying the URL or `str(exc)` through the
redirect's query string.

### Tmp-write-then-`os.replace()`, with the one deliberate exception
**Source:** `write_calendar_registry()` (`calendar_rules.py:769-812`).
**Apply to:** `save_calendar_url()` — copy everything except the `open(tmp, "w")` call, which
becomes the `os.open(..., 0o600)` + `os.fdopen()` pair (see Pattern Assignments above). This is the
one analog in this phase that must NOT be copied verbatim, flagged per the task brief.

## No Analog Found

None — every file this phase touches has a same-file or same-project analog covering its role and
data flow.

## Metadata

**Analog search scope:** `server/plane/calendar_rules.py`, `server/device_config.py`,
`companion/pages/config_page.py`, `companion/app.py`, `companion/auth.py`,
`server/test_calendar_rules.py`, `deploy/*.example`, `deploy/*.service`, `deploy/provision.sh`
**Files scanned:** 8 (all named in `<canonical_refs>`; no broader search needed — every analog was
specified by the phase's own context/research documents and confirmed against HEAD)
**Pattern extraction date:** 2026-09-09
