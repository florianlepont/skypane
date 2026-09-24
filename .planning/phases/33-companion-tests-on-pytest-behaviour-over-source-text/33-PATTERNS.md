# Phase 33: Companion tests on pytest — behaviour over source text - Pattern Map

**Mapped:** 2026-09-24
**Files analyzed:** 9 companion harnesses to migrate + 1 helper module (not itself collected) + `companion/conftest.py` (NEW) + `33-ledger-check.py` (NEW, copied from Phase 32)
**Analogs found:** 11 / 11 — every migrated harness's primary analog is Phase 32's own already-migrated `server/test_dither.py` (the `check()` → pytest translation, proven and shipped); the shared fixture's analog is the 5 in-repo `Harness`/`_InProcessHarness` copies plus Phase 32's `child_env`/`FakeProviders`; the browser harnesses' analog is `test_browser_ux_helpers.py`'s already-correct computed-style helpers plus Phase 32's verified pytest-playwright fixture-override pattern.

Read `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-PATTERNS.md` first — this map does not repeat what that one already proved (the `check(name, fn)` → `assert`/docstring mechanics, `pyproject.toml` conventions, the pinned-SHA CI style, the hash-locking commands). It only adds what is new for companion: the shared app-server fixture, source-text → behaviour/DOM/computed-style rewrites, pytest-playwright wiring, and the ledger's `SUMMARY_RE` fix.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `companion/conftest.py` (NEW) | config/fixture (shared app-server + browser-required override) | request-response (subprocess lifecycle) | `companion/test_companion_app.py`'s `Harness`/`_InProcessHarness` classes (5 copies to collapse) + `conftest.py` root's `fake_providers` fixture (Phase 32) | exact — logic already exists 5x in-repo, needs consolidation not invention |
| `companion/test_contrast_check.py` → pytest | test (unit, pure numeric) | transform (WCAG math, no server) | `server/test_dither.py` (post-migration, 100 lines) — same `check(name,fn)`→`assert`+docstring shape, no server involved either | exact |
| `companion/test_i18n.py` → pytest | test (unit + a few in-process HTTP) | transform (AST/regex source scan of `i18n_fr.py`/JS) + request-response (few `_InProcessHarness` checks) | `server/test_dither.py` for the pure-transform checks; `companion/test_companion_app.py`'s `_InProcessHarness` for the handful of server-touching ones it currently imports | role-match (two data flows in one file) |
| `companion/test_view_pages.py` → pytest (split optional) | test (integration, subprocess) | request-response (HTTP against a real `companion/app.py`) | `companion/test_companion_app.py`'s `Harness`+`http_request` (own copy, to be replaced by the new fixture) | exact (self, minus the duplicated plumbing) |
| `companion/test_config_page.py` → pytest (split encouraged, 13.6k lines) | test (integration, subprocess) | request-response + CRUD (config POST/save) | same as above; also contains the `_ASPECT_REPIN_LEDGER` self-referential source-read (delete candidate, see below) | exact (self) |
| `companion/test_companion_app.py` → pytest (split encouraged, 12.3k lines) | test (integration, subprocess + in-process) | request-response + CRUD + event-driven (`/poll-now`) | itself — the ONE file whose `Harness` already has `fake_providers`/`child_env` (Phase 32 32-11); this is the reference implementation the new shared fixture should generalize | exact (self) |
| `companion/test_status_pages.py` → pytest (split encouraged, 16.3k lines) | test (integration, subprocess) | request-response (history/health/anomaly pages) | same `Harness` copy pattern; also the root-unsafe `anomaly_active("/nonexistent/...")` site (TST-13) and the dozens of `style.css`-as-text reads (TST-12) | exact (self) |
| `companion/test_browser_ux.py` → pytest-playwright | test (browser, one shared browser for 75 checks today) | request-response + rendered-DOM | `companion/test_browser_ux_helpers.py`'s `_login`/`_computed_paint`/`_resolved_property`/`_no_js_page` — already the correct end-state idiom, just needs per-test `page`/`browser` fixtures instead of one shared `sync_playwright()` block | exact (helpers already correct; only the harness wrapper is legacy) |
| `companion/test_browser_ux_health_drawings.py` → pytest-playwright | test (browser) | request-response + rendered-DOM | same as above | exact |
| `companion/test_browser_ux_quiet_wake.py` → pytest-playwright | test (browser) | request-response + rendered-DOM | same as above | exact |
| `companion/test_browser_ux_helpers.py` (MODIFIED — becomes a plain importable helper module, no `main()`/`check()` of its own) | utility (test helper) | n/a | itself — 41 functions already written in the target idiom; only the surrounding two files (`test_browser_ux.py` etc.) need to change how they call in | exact (self) |
| `.planning/phases/33-.../33-ledger-check.py` (NEW) | utility (migration ledger checker) | batch | `.planning/phases/32-.../32-ledger-check.py` (737 lines) — copy verbatim, change `HARNESSES` (9 companion files), widen `SUMMARY_RE`, update phase-dir constants | exact (copy + 2 edits) |

## Pattern Assignments

### The shared app-server fixture (TST-10) — `companion/conftest.py` (NEW)

**Analog:** the 5 existing lifecycle classes already in `companion/test_companion_app.py` (the most current/complete of the 4 `Harness` copies, plus the lighter-weight `_InProcessHarness`), and the repo-root `conftest.py` / `test-support/skypane_test_support.py`'s `child_env`/`FakeProviders` (Phase 32, already shipped, reuse verbatim — do not reinvent).

**`Harness` — the subprocess-lifecycle body to generalize** (`companion/test_companion_app.py:1233-1326`):
```python
class Harness:
    def __init__(self, extra_args=()):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-companion-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None
        self.extra_args = list(extra_args)

    def start(self):
        # 32-11-PLAN.md Task 1 (TST-03): every companion/app.py child runs
        # under the no-network guard and serves ADS-B/adsbdb from a fresh
        # FakeProviders() (default empty-traffic responses).
        env = child_env(
            dict(os.environ), fake_providers=FakeProviders(), state_dir=self.tmpdir)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        stdout_fh = open(self.stdout_path, "w")
        cmd = [sys.executable, APP_PATH, "--port", str(self.port),
               "--state-dir", self.tmpdir] + self.extra_args
        try:
            self.proc = subprocess.Popen(cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        finally:
            stdout_fh.close()
        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("companion/app.py exited early (code %s):\n%s"
                                    % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("companion/app.py did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None
```
This is the ONLY one of the 4 copies with `fake_providers=FakeProviders()`; `test_config_page.py`/`test_status_pages.py`/`test_view_pages.py`'s copies do plain `env = dict(os.environ)` because they never exercise `/poll-now` (RESEARCH.md's Pitfall 4 — do not force fake-providers onto every test, offer both as fixture variants).

**`_NoRedirectHandler` + `http_request` (all 4 copies identical) — `companion/test_companion_app.py:1163-1220`:**
```python
class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return None from redirect_request() so a 303 (or any redirect) is
    surfaced as an HTTPError instead of being silently followed — needed
    to see the raw status code and Set-Cookie header, not the redirect target.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

# Deliberately NOT urllib.request.HTTPCookieProcessor: the session cookie
# always carries `Secure`, and http.cookiejar silently drops a Secure
# cookie over plain HTTP — cookies are threaded through explicitly instead.
_OPENER = urllib.request.build_opener(_NoRedirectHandler)

def http_request(url, method="GET", data=None, cookie=None, timeout=10,
                  content_type=None, extra_headers=None):
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if content_type is not None:
        headers["Content-Type"] = content_type
    elif data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()
```

**`_login` helper (`companion/test_companion_app.py:1507-1520`):**
```python
def _login(harness, password=TEST_PASSWORD):
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie
```

**`_InProcessHarness` (lighter-weight variant, `companion/test_companion_app.py:1329-1384`)** — a real `ThreadingHTTPServer` running `companion.app.Handler` in a background thread of the test process itself, used where a check needs to monkeypatch a module the subprocess boundary would otherwise hide (e.g. `calendar_rules.default_calendar_transport`). Offer this as a second fixture (`app_server_in_process` or similar) alongside the subprocess one — do not force every check through the (slower) subprocess path.

**Target pytest fixture shape (new code — RESEARCH.md's sketch, cross-checked against the classes above, now with concrete field names):**
```python
# companion/conftest.py
import os, socket, subprocess, sys, time
import pytest
from skypane_test_support import child_env, FakeProviders, TEST_SUPPORT_DIR
from companion import auth

APP_PATH = os.path.join(os.path.dirname(__file__), "app.py")
TEST_PASSWORD = "companion-test-password-please-ignore"
STARTUP_DEADLINE_S = 10.0

class AppServer:
    def __init__(self, port, tmpdir, fake_providers):
        self.port = port
        self.tmpdir = tmpdir
        self.fake_providers = fake_providers
    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

@pytest.fixture
def app_server(tmp_path, request):
    fake = None if request.node.get_closest_marker("no_fake_providers") else FakeProviders()
    env = child_env(dict(os.environ), fake_providers=fake, state_dir=str(tmp_path)) if fake \
        else child_env(dict(os.environ))
    env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
    proc = subprocess.Popen(
        [sys.executable, APP_PATH, "--port", "0", "--state-dir", str(tmp_path)],
        env=env, start_new_session=True)
    ...  # port discovery + poll-until-listening, then yield AppServer(...)
    # teardown: proc.terminate() -> wait(5) -> kill() -> wait(5)
```
Note: unlike the legacy `Harness`, the new fixture should pick the free port itself (still needed) but MUST NOT leak state across xdist workers/tests — one fixture instance per test function is the safe default (CONTEXT.md's own discretion note); promote to module scope with an explicit state-reset helper only if profiling later shows it matters.

### `check(name, fn)` → pytest translation for companion (extends 32-PATTERNS.md's server-side example with the HTTP/cookie idiom)

**Analog:** `server/test_dither.py` (Phase 32, post-migration, canonical minimal shape) for the mechanics; `companion/test_companion_app.py:1567+`'s own `main()`/`check()` (still legacy) for the companion-specific shape being replaced:
```python
# BEFORE (companion/test_companion_app.py, still legacy):
def main():
    results = []
    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        print("PASS %s" % name if ok else "FAIL %s - %s" % (name, reason))
    harness = Harness()
    harness.start()
    try:
        def _login_redirects_on_success():
            cookie = _login(harness)
            if not cookie:
                return False, "expected a cookie"
            return True, ""
        check("login succeeds and sets a cookie", _login_redirects_on_success)
    finally:
        harness.stop()
        harness.cleanup()
```
```python
# AFTER (pytest, using the new companion/conftest.py app_server fixture):
def test_login_succeeds_and_sets_a_cookie(app_server):
    """login succeeds and sets a cookie"""
    cookie = _login(app_server)
    assert cookie, "expected a cookie"
```
Translation notes specific to companion (beyond 32-PATTERNS.md's generic rule):
- `Harness()` / `harness.start()` / `finally: harness.stop(); harness.cleanup()` is entirely replaced by requesting the `app_server` fixture — no manual teardown code survives in the test body.
- `_login(harness)` keeps working unchanged as a plain helper function once `harness` is swapped for `app_server` (same `.base_url()` interface) — this is why the fixture's returned object should keep a `base_url()` method rather than a bare string, minimizing the diff for the ~2,000 call sites that already say `harness.base_url()`.
- `_InProcessHarness`-based checks translate the same way but request an `app_server_in_process`-style fixture instead.

### Behaviour-over-source-text rewrites (TST-12)

**1. Deletable pattern — self-referential test-file / `.planning` reads.**

Before (`companion/test_status_pages.py:8388-8423`, reading a JS file's source AND a `.planning/phases/.../CONTEXT.md` file to check prose wording survived a plan-history reversal):
```python
js_path = os.path.join(HERE, "static", "freshness.js")
with open(js_path) as fh:
    js_source = fh.read()
if "260902-chc" not in js_source:
    return False, "expected freshness.js to name this quick task"
...
context_path = os.path.join(
    REPO_ROOT, ".planning", "phases",
    "06.6.3-companion-per-page-redesign-config-health-history-airlines-p",
    "06.6.3-CONTEXT.md")
with open(context_path) as fh:
    context_source = fh.read()
d12_start = context_source.index("- **D-12:**")
...
check("the D-12 reversal (260902-chc) is written down at both prose sites it touches ...",
      _quick_260902_chc_reversal_recorded_in_both_places)
```
After: **DELETED.** Ledger reason: "asserts plan-history prose wording in a `.js` header comment and a `.planning/` CONTEXT.md entry; no product behaviour; TST-12 forbids opening `.planning/` or grepping source text." (Same disposition for `test_config_page.py:1652`'s and `test_browser_ux.py`'s `_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()` — self-referential `open(THIS_FILE)` regex scans over plan-ID-tagged ledger rows; delete with reason "self-referential CFG-85 aspect-repin bookkeeping; opens a `.py` file to grep text, which TST-12 forbids.")

**2. `style.css`-as-text → served-stylesheet structural parse (non-browser harnesses).**

Before (`companion/test_status_pages.py:1036-1049`, `2879-2925`):
```python
def _css_without_comments():
    with open(os.path.join(HERE, "static", "style.css"), encoding="utf-8") as handle:
        return re.sub(r"/\*.*?\*/", " ", handle.read(), flags=re.DOTALL)

# ... later, a check:
css = open(os.path.join(HERE, "static", "style.css")).read()
if ".battery-trend-section svg:not(.icon)" not in css:
    return False, "expected a `.battery-trend-section svg:not(.icon)` rule in style.css"
```
After — fetch the SAME bytes the app actually serves, then parse structurally rather than substring-search:
```python
import re

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

def declarations_for_selector(css_text, selector):
    """{property: value} for the FIRST `selector { ... }` block. Covers
    every current check's need (one declaration block per selector); does
    not handle @media-nested rules or comma-separated selector lists.
    """
    stripped = _COMMENT_RE.sub(" ", css_text)
    needle = selector + " {"
    start = stripped.index(needle) + len(needle)
    end = stripped.index("}", start)
    body = stripped[start:end]
    return {
        prop.strip(): value.strip()
        for prop, _, value in (decl.partition(":") for decl in body.split(";") if decl.strip())
    }

def test_battery_trend_section_svg_has_a_rule(app_server, http_get):
    css = http_get(app_server.base_url() + "/static/style.css").text
    # a structural presence check, e.g. the selector parses at all:
    assert declarations_for_selector(css, ".battery-trend-section svg:not(.icon)") is not None
```
Never keep `open(os.path.join(HERE, "static", "style.css"))` in a migrated test — the on-disk file is an implementation detail; the served response at `/static/style.css` is the thing under test (RESEARCH.md Pitfall 1).

**3. Same CSS-token check, browser variant (preferred where a `page` fixture is already in play).**

Analog: `companion/test_browser_ux_helpers.py:562-615`'s `_computed_paint()` (already the correct end-state idiom, do not reimplement):
```python
def _computed_paint(page, selector, props=("fill", "stroke", "color")):
    """Read the RESOLVED paint the browser computed for the first element
    matching `selector` — never the attribute, never the class. Raises
    when the selector matches nothing (never returns a swallow-able None).
    """
    props = tuple(props)
    seen = page.evaluate(_PAINT_PROBE, {"selector": selector, "props": list(props)})
    if seen is None:
        raise AssertionError("_computed_paint: no element matched %r on %s" % (selector, page.url))
    ...
```
And `_login(page, base_url)` (`companion/test_browser_ux_helpers.py:179-187`):
```python
def _login(page, base_url):
    """Drive the real login form through the UI (never a bare HTTP POST —
    this file exists specifically to exercise the browser)."""
    page.goto(base_url + "/login")
    page.fill("#password", TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
```
Migrated browser test:
```python
def test_section_caption_colour_reads_muted(page, app_server):
    _login(page, app_server.base_url())
    page.goto(app_server.base_url() + "/health")
    colour = page.eval_on_selector(".section-caption", "el => getComputedStyle(el).color")
    assert colour
```
Use this path (not the stdlib tokenizer) for checks that are already conceptually about rendering/cascade; use the served-stylesheet tokenizer (pattern 2) for the ~40-47 raw text reads in files that don't otherwise need a browser (`test_status_pages.py`, `test_companion_app.py`, `test_view_pages.py`), per RESEARCH.md's "Alternatives Considered."

**4. Root-unsafe literal host path → `tmp_path`-scoped absent path (TST-13).**

Before (`companion/test_status_pages.py:~8201`, confirmed live to `mkdir` on the host filesystem as root):
```python
health_page.anomaly_active("/nonexistent/definitely-not-here")
```
After:
```python
def test_anomaly_active_on_a_nonexistent_state_dir_returns_false(tmp_path):
    missing = tmp_path / "does-not-exist" / "nested"
    assert health_page.anomaly_active(str(missing)) is False
```
Same fix for the `os.chmod` WR-11 pair (`companion/test_companion_app.py:10336-10392`) — analog is Phase 32's own `server/test_manual_resolutions.py` translation (see `32-PATTERNS.md`'s "Root-safety skip pattern" section verbatim):
```python
from skypane_test_support import requires_non_root

@requires_non_root
def test_add_entry_on_uncreatable_state_dir_returns_failed(tmp_path):
    os.chmod(tmp_path, 0o500)
    try:
        result = m.add_entry(tmp_path / "state", "ABC", "Test Air")
    finally:
        os.chmod(tmp_path, 0o700)
    assert result == m.ADD_FAILED
```
`requires_non_root` already exists at `test-support/skypane_test_support.py:410-413` — import it, do not redefine it.

### Browser tests — pytest-playwright wiring (TST-11)

**Analog:** `companion/test_browser_ux.py:1213-1250`'s current hand-rolled `sync_playwright()`/`chromium.launch()` try/except-SKIP idiom (the pattern to retire) vs. the fixture-override replacement:
```python
# BEFORE (companion/test_browser_ux.py, current, one shared browser for 75 checks):
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        probe = p.chromium.launch()
        probe.close()
except Exception as exc:
    print("SKIP ...")
    return 0
with sync_playwright() as p:
    browser = p.chromium.launch()
    ...  # 75 checks share this one browser instance
```
```python
# AFTER — companion/conftest.py overrides pytest-playwright's own `browser`
# fixture (Phase 32/RESEARCH.md Pattern 2, verified live in this sandbox):
import os
import pytest

def _browser_required():
    return (os.environ.get("SKYPANE_REQUIRE_BROWSER") == "1"
            or os.environ.get("CI", "").lower() == "true")

@pytest.fixture(scope="session")
def browser(playwright):
    try:
        b = playwright.chromium.launch()
    except Exception as exc:
        if _browser_required():
            pytest.fail("Chromium could not launch (SKYPANE_REQUIRE_BROWSER=1): %r" % (exc,))
        pytest.skip("Chromium could not launch: %r" % (exc,))
    yield b
    b.close()

# Each of the 75 checks becomes its own test function taking `page` (the
# pytest-playwright function-scoped fixture, built on the session-scoped
# `browser` above) — xdist then distributes them across workers instead of
# running all 75 serially inside one process (RESEARCH.md Pattern 3,
# verified: 4 workers, each launching its own browser instance).
def test_home_page_has_no_horizontal_overflow(page, app_server):
    page.goto(app_server.base_url() + "/")
    ...
```
Do not pass `--browser-channel chromium` explicitly — verified live to resolve to the WRONG revision path vs. the default (no-flag) resolution that matches `--only-shell`'s installed binary (RESEARCH.md Pattern 3 note).

### Migration ledger tool (TST-15) — `33-ledger-check.py`

**Analog:** `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger-check.py` (737 lines) — copy verbatim, change exactly 3 things:
```python
# 1. HARNESSES list (32-ledger-check.py:57-73) becomes the 9 companion files:
HARNESSES = [
    "companion/test_contrast_check.py",
    "companion/test_i18n.py",
    "companion/test_view_pages.py",
    "companion/test_config_page.py",
    "companion/test_companion_app.py",
    "companion/test_status_pages.py",
    "companion/test_browser_ux_health_drawings.py",
    "companion/test_browser_ux_quiet_wake.py",
    "companion/test_browser_ux.py",
]

# 2. BASELINE_DIR/LEDGER_DIR/LEDGER_FILE (32-ledger-check.py:50-52) get the
#    33- prefix instead of 32-:
BASELINE_DIR = os.path.join(PHASE_DIR, "33-BASELINE")
LEDGER_DIR = os.path.join(PHASE_DIR, "33-ledger")
LEDGER_FILE = os.path.join(PHASE_DIR, "33-MIGRATION-LEDGER.md")

# 3. SUMMARY_RE (32-ledger-check.py:88) widened — test_i18n.py's own
#    summary line has NO "<name>: " prefix, unlike all 8 siblings:
SUMMARY_RE = re.compile(r"^(?:(?P<name>.+): )?(?P<passed>\d+)/(?P<total>\d+) checks pass\s*$")
```
`harness_key()`, `parse_baseline`, `parse_fragment_rows`, `validate_fragment`, `--capture`/`--assemble`/`--self-test` argparse plumbing are all format-driven — copy unchanged (RESEARCH.md's Migration Ledger section already verified this).

### Legacy shim retirement (TST-14)

**Analog:** `companion/test_legacy_harness_shim.py` (116 lines, current) and `test-support/skypane_test_support.py:388-405`'s `LEGACY_COMPANION_HARNESSES`/`LEGACY_COMPANION_COLLECT_IGNORE` tuples, plus `conftest.py:25`'s `collect_ignore = list(skypane_test_support.LEGACY_COMPANION_COLLECT_IGNORE)`. Each migration plan removes the file it just converted from `LEGACY_COMPANION_HARNESSES` (which `test_legacy_harness_list_matches_disk()` — `test_legacy_harness_shim.py:108-116` — verifies against `os.listdir("companion/")` every run, so the list and the disk never drift silently). Once the tuple is empty, delete `test_legacy_harness_shim.py`, the two tuples, and the `collect_ignore` wiring in one closing commit.

## Shared Patterns

### `check(name, fn)` → `assert` + docstring
**Source:** `server/test_dither.py` (Phase 32, canonical, already shipped) — see `32-PATTERNS.md`'s "The 15 server-side harnesses" section for the full generic rule (docstring = old label, loop-emitted checks → `@pytest.mark.parametrize`, `tempfile.mkdtemp()`+`finally` → `tmp_path`).
**Apply to:** all 9 companion files, layered with this document's HTTP/`app_server`-fixture specifics above.

### `child_env()` / `FakeProviders` / no-network guard
**Source:** `test-support/skypane_test_support.py` (Phase 32, unchanged) — `child_env(base, fake_providers=None, state_dir=None)` at lines 355-383, `FakeProviders` class at lines 211-352.
**Apply to:** the new `app_server` fixture in `companion/conftest.py` — every subprocess it launches must go through `child_env()`, exactly as the existing `Harness.start()` already does.

### `requires_non_root` marker
**Source:** `test-support/skypane_test_support.py:410-413`.
```python
requires_non_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores permission bits; needs a non-root euid",
)
```
**Apply to:** the 3 root-unsafe checks named in RESEARCH.md's Root-Safety Inventory (`test_companion_app.py:10336,10344,10386,10392`) plus any others the migration surfaces.

### Served-stylesheet fetch, never `open()`
**Source:** this document's Pattern 2 above (new code, no in-repo precedent since every existing check does the wrong thing today).
**Apply to:** every migrated CSS/contrast check that stays in a non-browser file; the ~309 source-text-reading checks and ~77 style.css-as-text checks the audit counted.

### Computed-style via a real page
**Source:** `companion/test_browser_ux_helpers.py`'s `_computed_paint`/`_resolved_property`/`_login`/`_no_js_page` (already correct, reuse directly, do not reimplement).
**Apply to:** the 3 browser harnesses once converted to pytest-playwright `page`/`browser` fixtures.

### pytest-playwright `browser` fixture override (CI-fail / local-skip)
**Source:** this document's Browser Tests section above, verified live in RESEARCH.md (Pattern 2 and Pattern 3).
**Apply to:** `companion/conftest.py`, once, shared by all 3 browser files.

## No Analog Found

None. Every file in this phase's scope has either itself as the pre-migration analog (all 9 harnesses — a runner migration, not new logic), an in-repo structural precedent for the new plumbing (the 5 `Harness`/`_InProcessHarness` copies for the shared fixture; `test_browser_ux_helpers.py` for computed-style; Phase 32's `child_env`/`FakeProviders`/`requires_non_root` for the cross-cutting guards), or a direct copy-and-edit source (`32-ledger-check.py` → `33-ledger-check.py`). The one genuinely new mechanism — pytest-playwright's `browser`/`page` fixtures themselves — has no in-repo analog by definition, but Phase 32's own research already verified the exact override code live in this sandbox; treat RESEARCH.md's Pattern 2/3 as the working substitute for an analog, reproduced above.

## Metadata

**Analog search scope:** `companion/` (all 9 `test_*.py` harnesses + `test_browser_ux_helpers.py` + `test_legacy_harness_shim.py`), `test-support/skypane_test_support.py`, repo-root `conftest.py`, `server/test_dither.py` (post-migration reference), `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-PATTERNS.md` and `32-ledger-check.py`
**Files scanned:** `server/test_dither.py` (full read, post-migration), `test-support/skypane_test_support.py` (full read), `conftest.py` (full read), `companion/test_companion_app.py` (targeted reads: `_NoRedirectHandler`/`http_request`/`Harness`/`_InProcessHarness`/`_login`/`main()` sections, lines 1163-1600ish; grep for `check(`/`EXPECTED_CHECK_COUNT`/class defs), `companion/test_legacy_harness_shim.py` (full read), `companion/test_status_pages.py` (targeted reads: `_css_without_comments()` lines 1030-1105, the `.planning`-reading check lines 8388-8423, grep for `style.css`/`.planning` hits), `companion/test_browser_ux_helpers.py` (targeted reads: `_login` lines 170-214, `_computed_paint` lines 560-630), `companion/test_browser_ux.py` (grep for `sync_playwright`/`SKIP` lines), `.planning/phases/32-.../32-ledger-check.py` (targeted reads: header docstring, `HARNESSES`/`SUMMARY_RE`/path-constant lines)
**Pattern extraction date:** 2026-09-24
