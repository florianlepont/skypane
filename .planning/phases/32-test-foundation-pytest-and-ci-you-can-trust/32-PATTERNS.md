# Phase 32: Test foundation — pytest and CI you can trust - Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 20 (15 server-side harnesses to migrate to pytest, plus conftest/fixture/CI/lock/companion-shim infra named in CONTEXT.md/RESEARCH.md)
**Analogs found:** 20 / 20 — this phase's "analog" for the migrated files is overwhelmingly the file's own pre-migration self (same repo, same behaviour, new runner); infra files (`conftest.py`, sitecustomize hook, companion shim) have same-repo precedents cited below.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]` edits) | config | n/a | itself — existing `[tool.ruff]`/`[tool.coverage.*]` tables (lines 1-116) | exact (in-place edit, same file) |
| `conftest.py` (NEW, repo root) | config/fixture (socket guard, `collect_ignore`, fake-provider fixture) | request-response (test setup) | `server/test_plane_detection.py`'s `_with_stubbed_providers` helper (lines ~507-520) for the fixture body; no existing repo-root `conftest.py` to copy structurally — this is genuinely new plumbing | role-match (fixture logic has an exact analog; the file itself is new) |
| `server/conftest.py` (NEW, optional per-directory fixtures) | config/fixture | request-response | same `_with_stubbed_providers`/`fake_get` convention, server-scoped | role-match |
| `server/test_dither.py` → pytest | test (unit/contract) | transform (image pipeline, no I/O beyond `tempfile`) | itself, pre-migration (this exact file, 157 lines, 6 checks — smallest, run first per Batch A) | exact (self) |
| `server/test_runway_config.py` → pytest | test (unit/contract) | CRUD (config load/validate) | itself, pre-migration | exact (self) |
| `server/test_notify.py` → pytest | test (unit/contract) | request-response (notification dispatch) | itself, pre-migration | exact (self) |
| `server/test_panel_preview.py` → pytest | test (unit/contract) | file-I/O (writes preview images) | itself, pre-migration | exact (self) |
| `server/test_pipeline_e2e.py` → pytest | test (integration) | event-driven (exercises `stub-server/byos_server.py` protocol end-to-end) | itself, pre-migration; subprocess-launch shape shared with `stub-server/test_poll_cycle.py`'s `Harness` | exact (self); shares subprocess pattern with Batch E file |
| `server/test_manual_resolutions.py` → pytest | test (unit/contract, CRUD) | CRUD | itself, pre-migration — root-safety `os.chmod` checks at lines 439, 461 need the new euid-0 skip | exact (self) |
| `server/test_colour_rules.py` → pytest | test (unit/contract, CRUD) | CRUD | itself, pre-migration | exact (self) |
| `server/test_illustrations.py` → pytest | test (unit/contract) | transform | itself, pre-migration — loop-emitted checks (Pitfall 1), use runtime baseline not grep | exact (self) |
| `server/test_plane_detection.py` → pytest | test (unit/contract) | event-driven (ADS-B polling, `requests.get` seam) | itself, pre-migration — carries the canonical `detect.requests.get` monkeypatch convention (lines ~507-520, 700-710) that the new fake-provider fixture formalizes | exact (self) |
| `server/test_enrich.py` → pytest | test (unit/contract) | request-response (adsbdb `requests.get` seam) | `server/test_plane_detection.py`'s monkeypatch convention, same seam family (`enrich.requests.get`) | role-match (same convention, sibling module) |
| `stub-server/test_poll_cycle.py` → pytest | test (integration) | event-driven (real subprocess, real HTTP) | itself, pre-migration — its `Harness` class (lines 235-315) is the direct structural ancestor `companion/test_companion_app.py`'s `Harness` says it mirrors | exact (self); also the `patch=["subprocess"]` proof point (TST-09) |
| `server/test_config_history.py` → pytest | test (unit/contract) | CRUD | itself, pre-migration — loop-emitted checks over `device_config.THEMES.items()` (lines 396-436), Pitfall 1 applies directly | exact (self) |
| `server/test_calendar_rules.py` → pytest | test (unit/contract) | CRUD | itself, pre-migration | exact (self) |
| `server/test_render.py` → pytest | test (unit/contract) | transform (image rendering) | itself, pre-migration — slowest server-side harness, largest check count | exact (self) |
| `server/test_poll_loop.py` → pytest | test (integration) | event-driven (`run_once()`, the same function `/poll-now` calls) | itself, pre-migration — land at/after the targeted `companion/test_companion_app.py` fake-provider edit (they share the `run_once()` contract) | exact (self) |
| `companion/test_companion_app.py` (TARGETED EDIT only, ~line 10771 `/poll-now` checks) | test (integration, subprocess-launched) | event-driven (real subprocess hitting real `run_once()`) | its own `Harness` class (lines 1220-1300) and `_poll_trigger_*` checks (lines ~10765-10850) — edit in place, do not migrate the rest of the file | exact (self, scoped edit) |
| `companion/test_legacy_harness_shim.py` (NEW) | test (shim — one pytest test per legacy harness, subprocess + exit-code assert) | event-driven (subprocess) | `stub-server/test_poll_cycle.py`'s `Harness.start_server()`/`stop_server()` subprocess-launch-and-wait shape (lines 272-310), simplified to "run to completion, assert exit code" rather than "start a long-lived server" | role-match |
| `test-support/sitecustomize.py` (NEW) | middleware (cross-process test hook) | event-driven (activated by env var in a child interpreter) | project's existing env-var-gated test-behaviour convention: `companion/auth.py`'s `PASSWORD_ENV_VAR` and `companion/app.py`'s `SLEEP_ENV_VAR`, both already read by the same subprocess-launched `companion/app.py` | role-match (same convention family, new mechanism) |
| `server/requirements-dev.txt` (MODIFIED — add pytest/xdist/cov/socket) | config | n/a | itself — existing `ruff`/`coverage`/`playwright` pinned-version lines | exact (in-place edit) |
| `scripts/run-all-tests.sh` (MODIFIED — thin `pytest` wrapper) | utility (CI entry point) | batch | itself, pre-migration (currently execs `run_all_tests.py`; keep the `PYTHON=` contract, change the exec target) | exact (self) |
| `scripts/run_all_tests.py` (RETIRED — deleted this phase) | utility (orchestrator) | batch | n/a — being removed, not migrated; `HARNESSES` list (lines 62-90) and `_run_one()` subprocess-with-timeout shape (lines 141-176) are what `pytest -n auto` replaces | n/a (deletion) |
| `.github/workflows/ci.yml` (MODIFIED — Python 3.14, separate concurrency groups, playwright `--only-shell` + cache) | config (CI) | n/a | itself — existing `concurrency:` blocks (workflow-level lines 43-45, job-level lines 108-115) and `setup-python`/playwright install steps (lines 77-91) | exact (in-place edit) |
| `.github/workflows/firmware.yml` (MODIFIED — add host-tests job) | config (CI) | n/a | itself — existing single `build` job (lines 34-58) is the template for a sibling `host-tests` job | exact (in-place edit) |
| `server/requirements.txt` + `server/requirements-dev.txt` → hash-locked variants (NEW lock files) | config | n/a | itself — the two existing flat pinned-version files are the `.in`-equivalent source | role-match (new artifact type, same source files) |
| `deploy/deploy.sh` (MODIFIED — `--require-hashes`, point at locked file) | utility (deploy) | file-I/O (rsync + pip install) | itself — existing `sha256sum`/`pip install -r` block (lines 63-70) | exact (in-place edit) |
| `.planning/phases/32.../32-MIGRATION-LEDGER.md` (NEW) | config (planning artifact) | n/a | `.planning/phases/31.../31-BASELINE-CHECKS.txt` — format precedent for a per-check `PASS <label>` transcript this ledger's baseline half reuses | exact (format precedent) |

## Pattern Assignments

### The 15 server-side harnesses (test, various data flows) — the check()/EXPECTED_CHECK_COUNT/main() idiom

**Analog:** every migrated file is its own analog — this is a runner migration, not a rewrite of test logic. `server/test_dither.py` (157 lines, smallest, 6 checks) is the cleanest specimen of the idiom every sibling file shares.

**The idiom to translate** (`server/test_dither.py:36-56, 150-157`):
```python
EXPECTED_CHECK_COUNT = 6

def main():
    results = []

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

    try:
        from server.plane import dither
        from server import panel_format as pf
    except ImportError as exc:
        print("FAIL import server.plane.dither / server.panel_format - %r" % (exc,))
        print("dither: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    # 1. ...
    def _palette_image_is_unpadded():
        img = dither.panel_palette_image()
        ...
        if palette != expected:
            return False, "panel_palette_image()'s palette is %r, expected exactly PALETTE_RGB %r (unpadded)" % (
                palette, expected,
            )
        return True, ""
    check("panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded", _palette_image_is_unpadded)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("dither: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1

if __name__ == "__main__":
    sys.exit(main())
```

**Mechanical translation rule (each `check(name, fn)` call becomes one pytest test function):**
```python
# Before (hand-rolled):
def _palette_image_is_unpadded():
    img = dither.panel_palette_image()
    palette = img.getpalette()
    expected = list(pf.PALETTE_RGB)
    if palette != expected:
        return False, "..."
    return True, ""
check("panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded", _palette_image_is_unpadded)

# After (pytest):
def test_panel_palette_image_carries_exactly_palette_rgbs_6_entries_unpadded():
    """panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded."""
    img = dither.panel_palette_image()
    palette = img.getpalette()
    expected = list(pf.PALETTE_RGB)
    assert palette == expected, (
        "panel_palette_image()'s palette is %r, expected exactly PALETTE_RGB %r (unpadded)" % (palette, expected)
    )
```
Key translation notes for the migration ledger:
- The old label string becomes the test's docstring (verbatim) so the ledger's "old check label -> new node id" mapping is auditable by reading the test file alone — the docstring IS the traceability link.
- `return False, "reason"` becomes `assert cond, "reason"` (or an explicit `pytest.fail("reason")` where there is no single boolean).
- Loop-emitted checks (Pitfall 1 — `server/test_config_history.py:396-436` over `device_config.THEMES.items()`, `server/test_illustrations.py`) become `@pytest.mark.parametrize`, with each parametrized id itself counting as one ledger row (CONTEXT.md explicitly allows this: "parametrised ids count").
- `tempfile.mkdtemp()` + manual `shutil.rmtree(..., ignore_errors=True)` in a `finally` (e.g. `test_dither.py:124-136`) becomes the `tmp_path` fixture — pytest owns cleanup, no `finally` needed.
- The `try/except ImportError` "can't even import the module" guard at the top of `main()` is subsumed by pytest's own collection-error reporting — do not port it forward as a test.
- The trailing `"%s: %d/%d checks pass" % (...)` line and `EXPECTED_CHECK_COUNT` self-check are subsumed by pytest's own summary line and exit code — do not port forward; the migration ledger's baseline transcript is what proves nothing was silently dropped instead.

### Fake provider fixture seam (server-side ADS-B/adsbdb `requests.get` monkeypatch)

**Analog:** `server/test_plane_detection.py` — the existing, already-working convention every provider test uses.

**Existing monkeypatch convention** (`server/test_plane_detection.py:507-520`):
```python
def _with_stubbed_providers(responses, fn):
    """Run fn() with detect.query_provider replaced by a lookup into
    `responses` ({provider_name: aircraft_list_or_Exception}), and the
    inter-call sleep zeroed so the harness stays fast.
    """
    real_query, real_sleep = detect.query_provider, detect.MIN_SECONDS_BETWEEN_CALLS

    def fake_query(name, lat, lon, radius_nm, timeout=10.0):
        value = responses[name]
        if isinstance(value, Exception):
            raise value
        return value

    detect.query_provider = fake_query
    detect.MIN_SECONDS_BETWEEN_CALLS = 0
    try:
        return fn()
    finally:
        detect.query_provider = real_query
        detect.MIN_SECONDS_BETWEEN_CALLS = real_sleep
```

**Lower-level HTTP-layer stub (the transport seam itself, `server/test_plane_detection.py:673-700`):**
```python
class _FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return payload

def fake_get(url, headers=None, timeout=None):
    captured_urls.append(url)
    return _FakeResponse()

original_get = detect.requests.get
detect.requests.get = fake_get
try:
    lol_result = detect.query_provider("adsblol", 48.1, 2.2, 5)
finally:
    detect.requests.get = original_get
```

**adsbdb sibling seam** (`server/plane/enrich.py:71,164-177`):
```python
ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"
...
url = ADSBDB_URL.format(callsign=callsign)
response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
```
Same convention applies: `monkeypatch.setattr(enrich.requests, "get", fake_get)`.

**pytest fixture version (new code, per RESEARCH.md Pattern 2 — put in `conftest.py`, reused by `server/test_plane_detection.py`, `server/test_enrich.py`, and by Phase 33's companion tests later):**
```python
@pytest.fixture
def fake_adsb_provider(monkeypatch):
    responses = {}  # test fills this in, keyed by provider name
    def fake_get(url, headers=None, timeout=None):
        for name, spec in detect.PROVIDERS.items():
            if url.startswith(spec["url_template"].split("{")[0]):
                result = responses.get(name)
                if isinstance(result, Exception):
                    raise result
                return _FakeResponse(result)
        raise AssertionError("unexpected URL in a test: %r" % url)
    monkeypatch.setattr(detect.requests, "get", fake_get)
    monkeypatch.setattr(enrich.requests, "get", fake_get)  # same seam, adsbdb
    return responses
```
This is the fixture the targeted `companion/test_companion_app.py` `/poll-now` edit must also reach, but only across the process boundary — see the sitecustomize pattern below, since that fixture's `monkeypatch.setattr` lives in the parent pytest process and never crosses into the `companion/app.py` subprocess.

### Non-loopback socket guard, in-process and cross-process

**Analog (in-process):** none in-repo yet — this is genuinely new plumbing (`pytest-socket`, a new dependency); the closest existing convention is the project's own already-working env-var-gated test behaviour, cited below for the cross-process half.

**In-process config (`pyproject.toml` `[tool.pytest.ini_options]`, new):**
```toml
[tool.pytest.ini_options]
addopts = "--disable-socket --allow-hosts=127.0.0.1,::1,localhost -n auto"
testpaths = ["server", "stub-server", "."]
```

**Required self-test proving the guard trips (CONTEXT.md success criterion 2 — new file, e.g. `test_no_network_guard.py`):**
```python
def test_non_loopback_socket_is_blocked():
    import socket
    with pytest.raises(Exception):  # pytest_socket.SocketBlockedError / SocketConnectBlockedError
        socket.create_connection(("example.com", 80), timeout=2)
```

**Cross-process half — analog is the project's OWN existing env-var-gated subprocess convention**, not a new invention:
```python
# companion/test_companion_app.py Harness.start() (lines 1249-1263) already does this
# for auth — the SAME env dict is where the new no-network var gets added:
def start(self):
    env = dict(os.environ)
    env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
    ...
    self.proc = subprocess.Popen(cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
```
`companion/app.py`'s own `SLEEP_ENV_VAR` is the second precedent for "a child process reads one new env var to change test-only behaviour." The new `test-support/sitecustomize.py` follows the identical shape:
```python
# test-support/sitecustomize.py — a directory added to PYTHONPATH only in
# subprocess envs the test harness controls, never in production.
import os

if os.environ.get("SKYPANE_TEST_NO_NETWORK"):
    from pytest_socket import disable_socket, socket_allow_hosts
    disable_socket(allow_unix_socket=True)
    socket_allow_hosts(["127.0.0.1", "::1", "localhost"], allow_unix_socket=True)
```
```python
# Harness.start() — one-line env addition, same dict `auth.PASSWORD_ENV_VAR` already uses:
env["SKYPANE_TEST_NO_NETWORK"] = "1"
env["PYTHONPATH"] = os.pathsep.join(
    filter(None, [str(TEST_SUPPORT_DIR), env.get("PYTHONPATH")])
)
```

### Subprocess launch pattern (`Harness` class) — for `stub-server/test_poll_cycle.py` migration and the companion shim

**Analog:** `stub-server/test_poll_cycle.py:235-315`'s `Harness` — the class `companion/test_companion_app.py`'s own `Harness` docstring says it "structurally mirrors."

```python
class Harness:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ink-poll-cycle-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "server.stdout.log")
        self.proc = None

    @staticmethod
    def _pick_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def start_server(self, sleep_s=300, image_url_scheme=None):
        stdout_fh = open(self.stdout_path, "w")
        cmd = [sys.executable, SERVER_PATH, "--image", self.image_path,
               "--port", str(self.port), "--sleep", str(sleep_s), "--state-dir", self.tmpdir]
        try:
            self.proc = subprocess.Popen(cmd, stdout=stdout_fh, stderr=subprocess.STDOUT)
        finally:
            stdout_fh.close()  # child holds its own duplicated fd

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("byos_server.py exited early (code %s) before accepting "
                                    "connections:\n%s" % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("server did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop_server(self):
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
As a pytest fixture, this becomes a `yield`-based fixture that calls `start_server()` before yield and `stop_server()`/`cleanup()` after — `patch = ["subprocess"]` (below) is what makes coverage see inside it.

### Companion legacy-harness pytest shim (subprocess + exit-code assert, NOT collected as a test module)

**Analog:** the same `Harness`/subprocess-launch-and-wait shape above, simplified — the shim runs a harness to completion rather than keeping a server alive.

```python
# companion/test_legacy_harness_shim.py — collected by pytest as ONE test
# module with N test functions; the companion/test_*.py files themselves
# must be excluded from collection (see conftest.py's collect_ignore below)
# so pytest never tries to import them as test modules in their own right.
import subprocess
import sys

import pytest

LEGACY_HARNESSES = [
    "companion/test_companion_app.py",
    "companion/test_config_page.py",
    "companion/test_contrast_check.py",
    "companion/test_i18n.py",
    "companion/test_status_pages.py",
    "companion/test_view_pages.py",
    "companion/test_browser_ux.py",
    "companion/test_browser_ux_health_drawings.py",
    "companion/test_browser_ux_quiet_wake.py",
]

@pytest.mark.parametrize("harness_path", LEGACY_HARNESSES)
def test_legacy_companion_harness_exits_zero(harness_path):
    result = subprocess.run([sys.executable, harness_path], capture_output=True, text=True)
    assert result.returncode == 0, (
        "%s exited %d:\n%s" % (harness_path, result.returncode, result.stdout + result.stderr)
    )
```
`LEGACY_HARNESSES` is a direct structural analog of `scripts/run_all_tests.py`'s own `HARNESSES` list (lines 62-90) — same list-of-paths idea, now scoped to only the companion files this phase does not migrate.

**`conftest.py` collection-ignore (new, repo root), so the shim doesn't double-collect the harnesses it subprocess-launches:**
```python
collect_ignore = [
    "companion/test_companion_app.py",
    "companion/test_config_page.py",
    "companion/test_contrast_check.py",
    "companion/test_i18n.py",
    "companion/test_status_pages.py",
    "companion/test_view_pages.py",
    "companion/test_browser_ux.py",
    "companion/test_browser_ux_health_drawings.py",
    "companion/test_browser_ux_quiet_wake.py",
]
```

### Root-safety skip pattern (server-side, `server/test_manual_resolutions.py`)

**Analog:** the file's own existing `os.chmod` read-only-directory checks (`server/test_manual_resolutions.py:437-450, 456-474`) — these have NO existing root guard today (they silently pass under euid 0 because root ignores the read-only permission bit) and this phase's migration must add one.

**Existing checks to migrate (note: currently unguarded):**
```python
def _add_entry_on_uncreatable_state_dir_returns_failed():
    with tempfile.TemporaryDirectory() as parent:
        os.chmod(parent, 0o500)
        try:
            result = m.add_entry(os.path.join(parent, "state"), "ABC", "Test Air")
        finally:
            os.chmod(parent, 0o700)
    if result != m.ADD_FAILED:
        return False, "expected ADD_FAILED for an uncreatable state dir, got %r" % (result,)
    return True, ""
```
**pytest translation with the new root-safety skip (CONTEXT.md: "skip under euid 0, every path inside `tmp_path`"):**
```python
import os
import pytest

requires_non_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores read-only directory permissions; this check needs a non-root euid",
)

@requires_non_root
def test_add_entry_on_uncreatable_state_dir_returns_failed(tmp_path):
    os.chmod(tmp_path, 0o500)
    try:
        result = m.add_entry(tmp_path / "state", "ABC", "Test Air")
    finally:
        os.chmod(tmp_path, 0o700)
    assert result == m.ADD_FAILED, "expected ADD_FAILED for an uncreatable state dir, got %r" % (result,)
```
This is the pattern for both flagged checks (lines 439 and 461) and any future root-safety-sensitive check this migration surfaces.

### `pyproject.toml` pytest + coverage configuration (in-place edit)

**Analog:** the file's own existing `[tool.ruff]`/`[tool.coverage.*]` tables (lines 1-116) — same file, same documentation-heavy commenting convention (every derived number gets a comment explaining its derivation; follow this style for the new `addopts`/`fail_under` lines).

```toml
[tool.pytest.ini_options]
addopts = "--disable-socket --allow-hosts=127.0.0.1,::1,localhost -n auto"
testpaths = ["server", "stub-server", "."]

[tool.coverage.run]
patch = ["subprocess"]
parallel = true   # implied by patch=subprocess, but harmless/documenting to state explicitly
source = ["server", "stub-server", "companion"]
omit = [
    "server/test_*.py",
    "stub-server/test_*.py",
    "companion/test_*.py",
    # make_test_panel.py, byos_server.py and companion/app.py are REMOVED
    # from this list once patch=["subprocess"] is proven to measure them —
    # do not remove them from omit until that measurement exists.
]
```
`target-version` also moves in this same file: `[tool.ruff] target-version = "py311"` (line 10) → `"py314"` (D-A4).

### CI: Python 3.14, separated concurrency groups, playwright `--only-shell` + cache

**Analog:** `.github/workflows/ci.yml` itself — existing `concurrency:` blocks and `setup-python`/playwright steps are the in-place edit targets.

**Existing workflow-level concurrency (lines 43-45, KEEP as-is — this is the "test" group, already separate from deploy):**
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```
**Existing job-level deploy concurrency (lines 108-115) — ALREADY has `cancel-in-progress: true`; TST-06 requires flipping this to `false` so an in-flight deploy is never cancelled (the CI header comment at lines 32-35 currently justifies the opposite; that comment needs updating alongside the flip):**
```yaml
concurrency:
  group: production-deploy
  cancel-in-progress: true   # <- TST-06 changes this to false
```
**Existing setup-python + playwright install (lines 77-91) — version and flag both change:**
```yaml
      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.12'   # -> '3.14'
          cache: pip
          cache-dependency-path: server/requirements*.txt
      ...
      - name: Download the Chromium browser companion/test_browser_ux.py drives
        run: server/.venv/bin/python -m playwright install --with-deps chromium
        # -> --only-shell chromium --with-deps, plus a new actions/cache step
        # keyed on the playwright version pin in requirements-dev.txt
```
Note the project's pinned-action-SHA + trailing version-tag-comment convention (`uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`) — any new action added (e.g. `actions/cache` for the Playwright browser cache) MUST follow this exact style: full commit SHA, `#` comment with the human-readable tag.

### Firmware host tests wired into `firmware.yml`

**Analog:** `.github/workflows/firmware.yml`'s own existing single `build` job (lines 34-58) — the template for a new sibling `host-tests` job, same file.

```yaml
jobs:
  build:
    # existing, unchanged
    ...
  host-tests:
    name: Firmware host tests (hardware-free)
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - run: ./firmware/tests/run_host_tests.sh
```
`firmware/tests/run_host_tests.sh` itself (already exists, unmodified) shows the "no framework, just `cc` + a shell loop, non-zero exit on any suite failure" idiom:
```sh
run_suite() {
    name="$1"; test_src="$2"; impl_src="$3"; bin="${TMP_DIR}/${name}"
    if ! "${CC}" -Wall -Wextra -std=c11 "${impl_src}" "${test_src}" -o "${bin}"; then
        echo "${name}: COMPILE FAILED"; FAIL=1; return
    fi
    if ! "${bin}"; then echo "${name}: FAILED"; FAIL=1; fi
}
run_suite "test_backoff" "${SCRIPT_DIR}/test_backoff.c" "${MAIN_DIR}/backoff.c"
```

### `scripts/run-all-tests.sh` — thin wrapper (in-place edit)

**Analog:** the file itself, pre-migration (24 lines, already a thin `exec` wrapper over `run_all_tests.py`).

**Existing shape (lines 20-27):**
```bash
PYTHON="${PYTHON:-${REPO_ROOT}/server/.venv/bin/python3}"
if [ ! -x "${PYTHON}" ]; then
    echo "ERROR: interpreter not found..." >&2
    exit 1
fi
exec "${PYTHON}" "${HERE}/run_all_tests.py" "$@"
```
**New shape — same guard clause, new exec target (per CONTEXT.md: "keeping the `PYTHON=` override contract"):**
```bash
exec "${PYTHON}" -m pytest "$@"
```
`scripts/run_all_tests.py` is retired (deleted) this phase — its `HARNESSES` list (lines 62-90) is superseded by pytest's own auto-discovery via `testpaths`, and its per-harness `subprocess.run([python, "-m", "coverage", "run", harness], ...)` shape (lines 141-158) is superseded by `pytest-xdist`.

### Hash-locking (`uv pip compile --generate-hashes`)

**Analog:** none in-repo (first lock files this project generates) — the existing flat `server/requirements.txt` / `server/requirements-dev.txt` are the direct `.in`-equivalent sources to compile from.

```bash
uv pip compile --generate-hashes --python-version 3.14 \
    server/requirements.in -o server/requirements.txt
uv pip compile --generate-hashes --python-version 3.14 \
    server/requirements-dev.in -o server/requirements-dev.txt
```

**`deploy/deploy.sh` change (existing block, lines 63-70, in-place edit):**
```bash
echo "==> Checking whether requirements.txt changed"
LOCAL_HASH="$(sha256sum "${REPO_ROOT}/server/requirements.txt" | awk '{print $1}')"
REMOTE_HASH="$(ssh "${SSH_TARGET}" "sudo cat ${APP_ROOT}/.requirements.sha256 2>/dev/null || true")"
if [ "${LOCAL_HASH}" != "${REMOTE_HASH}" ]; then
    echo "    requirements.txt changed - reinstalling into the venv"
    ssh "${SSH_TARGET}" "sudo -u skypane ${APP_ROOT}/venv/bin/pip install --quiet -r ${APP_ROOT}/server/requirements.txt && echo '${LOCAL_HASH}' | sudo -u skypane tee ${APP_ROOT}/.requirements.sha256 >/dev/null"
```
Only the `pip install` line changes — add `--require-hashes` (per Pitfall 5, the `sha256sum`/path references are already correct if the lock file replaces `server/requirements.txt` in place):
```bash
ssh "${SSH_TARGET}" "sudo -u skypane ${APP_ROOT}/venv/bin/pip install --require-hashes --quiet -r ${APP_ROOT}/server/requirements.txt && ..."
```

### Migration ledger baseline format

**Analog:** `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-BASELINE-CHECKS.txt` — one `PASS <label>`/`FAIL <label>` line per check, captured by actually running the harness, not by grepping source. This exact format is what `32-MIGRATION-LEDGER.md`'s baseline column reuses per CONTEXT.md ("Phase 31's `31-BASELINE-CHECKS.txt` is a format precedent").

```
PASS panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded
PASS dither_to_full_panel_palette() on a hue-rich synthetic image yields indices that are a subset of {0,1,2,3,4,5}
...
dither: 6/6 checks pass
```
Capture command (per RESEARCH.md Pattern 1):
```bash
for f in server/test_*.py stub-server/test_poll_cycle.py; do
    server/.venv/bin/python3 "$f" > "32-BASELINE-CHECKS-$(basename "$f" .py).txt" 2>&1
done
```

## Shared Patterns

### Env-var-gated subprocess test behaviour
**Source:** `companion/auth.py` `PASSWORD_ENV_VAR` and `companion/app.py` `SLEEP_ENV_VAR`, both consumed at `companion/test_companion_app.py:1250-1251` (`env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD`)
**Apply to:** the new `SKYPANE_TEST_NO_NETWORK` var and `test-support/sitecustomize.py` — same "one new env var, read once at child-process startup" shape, not a new convention.

### `Harness` class (pick free port, subprocess.Popen, poll-until-listening, terminate-then-kill teardown)
**Source:** `stub-server/test_poll_cycle.py:235-315`, mirrored by `companion/test_companion_app.py:1220-1300`
**Apply to:** any migrated harness that launches a real subprocess (`server/test_pipeline_e2e.py`, `stub-server/test_poll_cycle.py` itself) and the new companion shim — port-picking and readiness-polling logic must not be reinvented per file.

### `check(name, fn)` → `assert`/docstring translation
**Source:** `server/test_dither.py` (canonical minimal example), same shape in all 14 other `server/test_*.py` files and `stub-server/test_poll_cycle.py`
**Apply to:** every one of the 15 files in TST-02 scope — see "The 15 server-side harnesses" pattern above for the exact before/after.

### Pinned-SHA + version-tag-comment GitHub Actions convention
**Source:** `.github/workflows/ci.yml:75, 78, 126, 129` and `.github/workflows/firmware.yml:41` — `uses: owner/action@<full-sha> # vX.Y.Z`
**Apply to:** any new action step added for TST-05/06/07 (e.g. `actions/cache` for the Playwright browser cache) — never a bare version tag or branch ref.

### Documentation-heavy derivation-comment style in `pyproject.toml`
**Source:** `pyproject.toml:96-116` (`fail_under = 83` derivation) and `:46-58` (`parallel = true` rationale)
**Apply to:** the new `addopts`, the `patch = ["subprocess"]` line, and especially the new `fail_under` value once TST-09's measurement lands — state the measured percentage and date, same as the existing 83 derivation does.

## No Analog Found

None — every file in this phase's scope either has itself as the pre-migration analog (the 15 harnesses, `pyproject.toml`, both CI YAML files, `deploy/deploy.sh`, `scripts/run-all-tests.sh`) or a same-repo structural precedent (fake-provider seam, `Harness` subprocess pattern, env-var-gated subprocess convention, pinned-action-SHA style, baseline-transcript format). The two genuinely new mechanisms this phase introduces — `pytest-socket`'s in-process guard and the `sitecustomig.py` cross-process hook — have no in-repo analog by definition (they don't exist yet), but RESEARCH.md's Pattern 3 already supplies verified, ready-to-use code for both; treat that as the working substitute for an analog.

## Metadata

**Analog search scope:** `server/`, `stub-server/`, `companion/`, `scripts/`, `.github/workflows/`, `deploy/`, `pyproject.toml`, `firmware/tests/`, `.planning/phases/31-.../31-BASELINE-CHECKS.txt` and `31-PATTERNS.md` (format precedent only)
**Files scanned:** `server/test_dither.py` (full read), `server/test_plane_detection.py` (targeted reads: header + lines 480-720), `server/plane/detect.py` / `server/plane/enrich.py` (grep + targeted reads), `stub-server/test_poll_cycle.py` (header + `Harness` class lines 225-330), `companion/test_companion_app.py` (`Harness` class lines 1220-1300, `/poll-now` section lines 10700-10850), `server/test_manual_resolutions.py` (lines 420-474), `pyproject.toml` (full), `.github/workflows/ci.yml` (full), `.github/workflows/firmware.yml` (full), `firmware/tests/run_host_tests.sh` (head), `deploy/deploy.sh` (head + requirements-hash block), `scripts/run_all_tests.py` (head + HARNESSES/EXPECTED_SLOWEST/`_run_one` sections), `scripts/run-all-tests.sh` (full), `server/requirements.txt` / `server/requirements-dev.txt` (full), README.md (Python version line), `.planning/phases/31-.../31-BASELINE-CHECKS.txt` and `31-PATTERNS.md` (format precedent)
**Pattern extraction date:** 2026-09-23
