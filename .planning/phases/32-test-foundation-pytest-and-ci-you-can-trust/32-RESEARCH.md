# Phase 32: Test foundation — pytest and CI you can trust - Research

**Researched:** 2026-09-23
**Domain:** Python test-runner migration (hand-rolled harnesses → pytest/xdist/cov), network-isolation testing, GitHub Actions CI, dependency hash-locking
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Framework (D-A2, locked)**
- Full migration to pytest. pytest, pytest-xdist and pytest-cov live in `server/requirements-dev.txt` only; `deploy/deploy.sh` keeps installing `server/requirements.txt` only.
- pytest configuration goes in the existing repo-root `pyproject.toml` (`[tool.pytest.ini_options]`); still no `[project]` table.
- Coverage gate moves from the hand-run `coverage combine/report` in `run_all_tests.py` to pytest-cov (`--cov-fail-under` or `[tool.coverage.report] fail_under`).
- CLAUDE.md "Tests / CI" stack row and CONTRIBUTING are updated to describe pytest as the way to run tests.

**Python version (D-A4 + developer answer)**
- Production is Python 3.14 (Ubuntu 26.04 distro `python3`). CI `setup-python` moves from `'3.12'` to `'3.14'`; ruff `target-version` moves from `py311` to `py314`.
- README's "Requires Python 3.12" line updated to 3.14.
- Every pinned dependency must have a 3.14-compatible release (Pillow, requests, ruff, coverage, playwright, pytest, pytest-xdist, pytest-cov); research must confirm, and the lock files are generated for 3.14.

**Test location (developer answer)**
- Migrated tests stay where they are: `server/test_*.py` and `stub-server/test_poll_cycle.py`, next to the code. No `tests/` directory move in this phase.
- `conftest.py` files placed so fixtures are shared: a repo-root `conftest.py` (no-network guard, common fixtures) plus per-directory ones if needed.

**Transition for companion harnesses (developer answer)**
- pytest shim: until Phase 33, each remaining hand-rolled companion harness (`companion/test_*.py`, including the browser harnesses) is run by pytest as one test that launches the harness as a subprocess and fails on a non-zero exit. The shim must not make pytest *collect* those files as test modules (use a collection ignore / a dedicated shim module).
- `pytest -n auto` is the single entry point from Phase 32 onward. `scripts/run_all_tests.py` and its `HARNESSES` hand list are retired; `scripts/run-all-tests.sh` becomes a thin wrapper over `pytest` (keeping the `PYTHON=` override contract).
- The browser harnesses' "SKIP counts as PASS" defect (TST-11) is Phase 33's; the shim must not hide a non-zero exit.

**/poll-now and the no-network guard (developer answer)**
- Fixed in Phase 32: the fake provider fixture and the non-loopback socket guard, plus a targeted edit making the existing `/poll-now` checks in `companion/test_companion_app.py` (~line 10771, the real `poll_loop.run_once` path) use the fake provider.
- The guard must apply to the subprocess-launched servers too (companion app and byos run as child processes) — an env-var-activated hook the child processes honour, or a fake-provider base URL injected via environment. Research picks the mechanism.
- Loopback (127.0.0.1 / ::1 / localhost) and Unix sockets stay allowed.

**Migration ledger**
- Lives in the phase directory (`32-MIGRATION-LEDGER.md`), one row per pre-migration check of the 15 server-side harnesses: old harness + check label → new pytest node id, or "deleted" + reason.
- Pre-migration baseline captured before any rewrite (per-harness check counts and labels); Phase 31's `31-BASELINE-CHECKS.txt` is a format precedent.
- Parametrisation and consolidation allowed as long as each old check maps to a specific node id (parametrised ids count).
- Server-side root-safety (e.g. `chmod` read-only checks in `server/test_manual_resolutions.py`) handled during its migration: skip under euid 0, every path inside `tmp_path`.

**CI**
- Test and deploy concurrency groups are separate; deploy group uses `cancel-in-progress: false`.
- Firmware host tests run in `firmware.yml` (separate job/step that does not need the ESP-IDF container, if possible).
- Playwright: `playwright install --only-shell chromium` (plus needed OS deps) with `~/.cache/ms-playwright` cached, keyed on the playwright version.

**Dependency locking (TST-08)**
- Runtime and dev dependencies hash-locked (transitives included). Tool choice is Claude's discretion.
- `deploy/deploy.sh` installs the runtime lock with hashes enforced; its `requirements.sha256` change-detection keeps working on the locked file.

**Coverage (TST-09)**
- Subprocess coverage (`[tool.coverage.run] patch = ["subprocess"]`, coverage ≥ 7.10) so `companion/app.py`, `stub-server/byos_server.py` and `stub-server/make_test_panel.py` leave the `omit` list.
- Measure, then set `fail_under` to the measured floor (rounded down, no 4-point margin), documented in `pyproject.toml`.

### Claude's Discretion
- Lock tool, file names of the lock files, and whether `.in` sources are kept.
- Fake provider design (fixture shape, how `poll_loop`/`enrich` receive it — dependency injection vs monkeypatching the HTTP layer), as long as it is injectable and reused by Phase 33.
- Order and batching of harness migrations across plans; pytest markers (e.g. `slow`, `browser`).
- Whether ruff gains the `PT` rule family — optional.

### Deferred Ideas (OUT OF SCOPE)
- Companion harness migration, one app-server fixture, pytest-playwright, behaviour-over-source-text rewrites, companion root-safety, companion check-count retirement, 2018-check closing parity → Phase 33.
- Moving tests into a `tests/` tree → possibly Phase 39 (server architecture split).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TST-01 | pytest + pytest-xdist + pytest-cov as dev deps; config in `pyproject.toml`; shared fixtures in `conftest.py`; coverage gate moves to pytest-cov; CLAUDE.md/CONTRIBUTING updated | Standard Stack; verified all 3 packages install cleanly and are slopcheck `[OK]`; verified `[tool.pytest.ini_options]` works with no `[project]` table |
| TST-02 | Server-side harnesses (`server/test_*.py` ×14, `stub-server/test_poll_cycle.py`) migrated to pytest, every old check mapped in a ledger | Harness Migration Inventory section: exact per-file check counts, mechanical baseline-extraction method (verified by actually running `test_dither.py`), proposed batching |
| TST-03 | Injectable fake provider fixture; conftest guard fails any test opening a non-loopback socket | Architecture Patterns (Fake Provider Seam, Non-Loopback Socket Guard); verified via installed source of `pytest-socket` and a working hand-rolled proof-of-concept |
| TST-04 | CI (and ruff `target-version`) on the production version (3.14) | Environment Availability; verified `ruff target-version = "py314"` is accepted, and every pinned package installs + imports under a real Python 3.14 interpreter |
| TST-05 | Firmware host tests run in `firmware.yml` | Architecture Patterns (CI Wiring); read `firmware/tests/run_host_tests.sh` (0.35s, exits 1 on failure, `cc`-only) |
| TST-06 | Separate test/deploy concurrency groups; never cancel an in-flight deploy | Architecture Patterns (CI Wiring); read current `.github/workflows/ci.yml` concurrency blocks |
| TST-07 | Playwright `--only-shell`, cache `~/.cache/ms-playwright` | Code Examples; verified `--only-shell` flag exists and works, confirmed official docs' recommended cache-key-on-version pattern |
| TST-08 | Hash-pinned lock files, runtime + dev, transitives included | Standard Stack / Code Examples; verified `uv pip compile --generate-hashes --python-version 3.14` produces a working hash-locked file including transitives |
| TST-09 | Subprocess coverage (`patch = ["subprocess"]`), `fail_under` raised to measured floor | Common Pitfalls / Code Examples; verified via official coverage.py and pytest-cov docs (patch=subprocess added in coverage 7.10; pytest-cov 7+ requires this mechanism, having removed its own `.pth` auto-injection) |
</phase_requirements>

## Summary

This phase replaces 15 hand-rolled `check()/EXPECTED_CHECK_COUNT/main()` harnesses (22,591 lines, 738 checks by each file's own `EXPECTED_CHECK_COUNT`) with real pytest tests, while leaving the much larger companion harness set (92,340 lines across 10 files, ~9,594-16,279 lines each) running through a one-test-per-harness subprocess shim until Phase 33. Every piece of the target stack — pytest 9.1.1, pytest-xdist 3.8.0, pytest-cov 7.1.0, pytest-socket 0.8.1, coverage 7.16.1, ruff 0.16.8, Pillow 12.3.0, requests 2.34.2, playwright 1.63.0 — was installed and exercised in this research session under a real Python 3.14 interpreter (the newest available release, 3.14.0rc2, provisioned via `uv python install 3.14`); Pillow shipped a genuine compiled `cp314` wheel, not a source build, and `ruff check` with `target-version = "py314"` and `[tool.pytest.ini_options]` with no `[project]` table both worked as expected. `uv pip compile --generate-hashes --python-version 3.14` produced a correct hash-locked file including transitive dependencies (urllib3, certifi, charset-normalizer) — the tool works and is available locally as `uv`.

The trickiest part of the phase is not "add pytest" but the two seams CONTEXT.md flags as open: (1) the fake ADS-B/adsbdb provider, because the current code has no injection point — `server/plane/detect.py`'s `query_provider()` calls `requests.get()` directly on a hardcoded URL template, and every existing test stubs it by monkeypatching the module attribute `detect.requests.get` (confirmed at `server/test_plane_detection.py:700-710`); and (2) making the no-network guard hold across the process boundary, because `companion/test_companion_app.py`'s `Harness.start()` launches `companion/app.py` as a real `subprocess.Popen([sys.executable, APP_PATH, ...], env=env)` (`companion/test_companion_app.py:1220-1260`) — a pytest-side `conftest.py` monkeypatch of `socket.socket.connect` in the parent process does not reach that child interpreter at all. The mechanism this research recommends for both: reuse `pytest-socket`'s already-correct, already-installed guard (it patches `socket.socket`, `socket.getaddrinfo` and `socket.gethostbyname`, not just `.connect()`, closing a DNS-leak gap a hand-rolled guard would need to reinvent) for the in-process pytest run via `--disable-socket --allow-hosts=...`, and extend it to the companion/byos child processes with a small `sitecustomize.py` on a `PYTHONPATH` directory injected into the child's `env` dict, gated by one new env var, calling `pytest_socket.disable_socket()` / `socket_allow_hosts()` directly (both are plain public functions, confirmed in the installed package source) — a mechanism symmetric with the project's own existing convention of env-var-activated test behaviour (`auth.PASSWORD_ENV_VAR`, `app_module.SLEEP_ENV_VAR`, both already read by the same subprocess-launched `companion/app.py`).

**Primary recommendation:** Add `pytest==9.1.1`, `pytest-xdist==3.8.0`, `pytest-cov==7.1.0`, `pytest-socket==0.8.1` to `server/requirements-dev.txt`; configure `[tool.pytest.ini_options]` in the existing `pyproject.toml` with `addopts = "--disable-socket --allow-hosts=127.0.0.1,::1,localhost -n auto"`; migrate the 15 server-side harnesses in size-ordered batches (small→large) rather than as one plan, mechanically re-deriving each file's pre-migration check-label baseline by *running* it and capturing its `PASS`/`FAIL` transcript (grep-counting `check(` call sites is unreliable — see Pitfall 1); use `uv pip compile --generate-hashes --python-version 3.14` for the lock files; and set `[tool.coverage.run] patch = ["subprocess"]` (coverage's own mechanism, since pytest-cov 7+ deliberately removed its prior `.pth`-based subprocess auto-injection).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Test discovery/execution/parallelism | Dev tooling (pytest + xdist) | — | Replaces the hand-rolled `scripts/run_all_tests.py` orchestrator; owns process pooling, was previously a bespoke `ThreadPoolExecutor` |
| Coverage measurement/gate | Dev tooling (coverage.py via pytest-cov) | CI (`ci.yml`) | Coverage.py owns instrumentation + `fail_under`; CI just runs the command and reads the exit code |
| Network isolation for tests | Dev tooling (pytest-socket, in-process) | Child-process tier (sitecustomize hook, subprocess-launched servers) | The guard must exist in two places because companion/byos genuinely run as separate OS processes, not just separate Python objects |
| Fake ADS-B/adsbdb provider | Server / Plane detection module (`server/plane/detect.py`, `server/plane/enrich.py`) | Test fixtures (conftest) | The provider seam is a production code property (an injectable transport) that tests then configure — not purely a test-side concern |
| Migration ledger / check-label bookkeeping | Planning artifacts (`.planning/phases/32.../32-MIGRATION-LEDGER.md`) | — | Documentation, not runtime; consumed by verify-work and Phase 33, not by any running system |
| CI orchestration (jobs, concurrency, caching) | CI / GitHub Actions | — | `.github/workflows/ci.yml` and `firmware.yml`; no application-tier component |
| Dependency supply-chain integrity | Build/dev tooling (lock files + `--require-hashes`) | Deploy (`deploy/deploy.sh`) | Lock files are generated by dev tooling; deploy enforces them at install time |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.1.1 `[VERIFIED: installed + run under Python 3.14.0rc2 in this session]` | Test runner/discovery/assertions | De facto standard Python test framework; what the whole migration targets |
| pytest-xdist | 3.8.0 `[VERIFIED: installed + `-n auto` distribution model inspected]` | Parallel test execution across worker processes | Only maintained way to run pytest across multiple CPUs; `execnet`-based, pickles exceptions correctly for cross-process reporting |
| pytest-cov | 7.1.0 `[VERIFIED: installed under 3.14; docs fetched confirming its pytest-xdist + subprocess-coverage story]` | Coverage integration, `--cov-fail-under` | Standard bridge between pytest and coverage.py; pytest-cov 7+ deliberately delegates subprocess coverage to coverage.py's own `patch=subprocess` rather than its old `.pth` mechanism |
| pytest-socket | 0.8.1 `[VERIFIED: installed under 3.14; source code read directly from the installed package]` | Non-loopback network guard for pytest tests | Mature (miketheman/pytest-socket), patches `socket.socket`, `socket.getaddrinfo` *and* `socket.gethostbyname` — closes the DNS-resolution leak a hand-rolled `.connect()`-only patch has (proven in this session's own hand-rolled prototype: a blocked-but-still-DNS-resolving `urlopen()` call) |
| coverage.py | 7.16.1 (already pinned) `[VERIFIED: already in server/requirements-dev.txt; `patch = ["subprocess"]` confirmed via official docs to require ≥7.10]` | Coverage instrumentation, `patch=["subprocess"]` for byos/companion | Already the project's coverage engine; no change needed except config |
| ruff | 0.16.8 (already pinned) `[VERIFIED: `target-version = "py314"` accepted and enforced correctly under 3.14]` | Lint | Already the project's linter; only the `target-version` value changes |
| Pillow | 12.3.0 (already pinned) `[VERIFIED: genuine compiled `cp314-cp314-manylinux_2_27...` wheel installed and imported successfully]` | Image processing (production dep) | Already pinned; confirmed 3.14-compatible |
| requests | 2.34.2 (already pinned) `[VERIFIED: installs and is importable under 3.14]` | HTTP client (production dep) | Already pinned; confirmed 3.14-compatible |
| playwright | 1.63.0 (already pinned) `[VERIFIED: installs, `--only-shell` install flag confirmed via `--help`, headless shell downloads and runs under 3.14]` | Browser UX harness driver | Already pinned; confirmed 3.14-compatible and `--only-shell` support |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uv | 0.8.17 (already present as a system tool in CI-equivalent environments; not a Python dependency) `[VERIFIED: available in this sandbox, used throughout this research session]` | Python-version provisioning + `pip compile --generate-hashes` lock generation | Recommended lock tool (see Claude's Discretion) — one binary does both "get me a 3.14 interpreter to test locally" and "generate the hash-locked requirements" |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-socket for the guard | Hand-rolled `conftest.py` monkeypatch of `socket.socket.connect` | Hand-rolled version is simpler to read but (verified in this session) leaks a real DNS query via `socket.getaddrinfo` before the connect-time check fires; pytest-socket patches all three call sites and already has a documented `SocketBlockedError`/`SocketConnectBlockedError` pair, an `allow_hosts` marker for per-test overrides, and xdist-safe pickling — reinventing all of that is pure risk for no benefit |
| `uv pip compile --generate-hashes` | `pip-tools`' `pip-compile --generate-hashes` | Functionally equivalent output format (`--hash=sha256:...` per line); `pip-tools` is the older, still-maintained original tool. Only reason to prefer it: if the team wants zero dependence on `uv` in CI. Not tested in this session (uv was already available and confirmed working; pip-tools was not independently verified) |
| `pyproject.toml`'s `[tool.coverage.run] patch = ["subprocess"]` | pytest-cov's old `.pth`-file subprocess auto-injection | The `.pth` mechanism was **removed in pytest-cov 7** (confirmed via official pytest-cov docs) — this is not a style choice, the old approach no longer exists in the pinned version |

**Installation:**
```bash
# server/requirements-dev.txt additions
pytest==9.1.1
pytest-xdist==3.8.0
pytest-cov==7.1.0
pytest-socket==0.8.1
```

**Version verification:** Every version above was installed live in this research session:
```bash
uv python install 3.14   # provisioned 3.14.0rc2 — the newest release uv's local
                          # registry offered (see Pitfall 5 re: this being an
                          # environment ceiling, not a claim about what's
                          # released upstream)
uv venv --python 3.14 /tmp/py314-uvvenv
uv pip install --python /tmp/py314-uvvenv/bin/python3.14 \
    Pillow==12.3.0 requests==2.34.2 ruff==0.16.8 coverage==7.16.1 \
    pytest pytest-xdist pytest-cov pytest-socket playwright==1.63.0
# Resolved 20 packages, installed cleanly, zero conflicts.
```

## Package Legitimacy Audit

Ran `slopcheck install` (v0.6.1) against the four new dev-only packages this phase adds:

| Package | Registry | Age/downloads (slopcheck-reported context) | Source Repo | slopcheck | Disposition |
|---------|----------|---------|-------------|-----------|-------------|
| `pytest` | PyPI | Long-established, extremely high downloads | github.com/pytest-dev/pytest | `[OK]` | Approved |
| `pytest-xdist` | PyPI | Long-established, high downloads | github.com/pytest-dev/pytest-xdist | `[OK]` | Approved |
| `pytest-cov` | PyPI | Long-established, high downloads | *(slopcheck notes: "No source repository linked" in its registry metadata — still verified against the pytest-dev org / pypi.org/project/pytest-cov, `[OK]`)* | `[OK]` (with a metadata caveat) | Approved |
| `pytest-socket` | PyPI | Established, moderate downloads | github.com/miketheman/pytest-socket | `[OK]` | Approved |

**Packages removed due to slopcheck `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** none — `pytest-cov`'s "no source repository linked" note is a registry-metadata gap (PyPI project metadata doesn't declare a `Home-page`/`Project-URL` the tool recognises), not a suspicion signal; its actual source (`github.com/pytest-dev/pytest-cov`) is well known and was cross-checked manually via its own docs site fetched in this session.

All four packages were also installed and imported successfully in this session (not merely registry-checked), which is stronger than the package-legitimacy protocol's minimum bar.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌─────────────────────────────┐
                        │   pytest -n auto (parent)   │
                        │   repo-root conftest.py:    │
                        │   --disable-socket          │
                        │   --allow-hosts=127.0.0.1,  │
                        │        ::1,localhost        │
                        └───────────┬─────────────────┘
                                    │ collects & distributes test items
              ┌─────────────────────┼───────────────────────────────┐
              │                     │                               │
   ┌──────────▼─────────┐ ┌─────────▼──────────┐      ┌─────────────▼───────────┐
   │ server/test_*.py    │ │ stub-server/        │      │ companion pytest SHIM   │
   │ (migrated, real     │ │ test_poll_cycle.py  │      │ (one test per legacy    │
   │ pytest tests)       │ │ (migrated)          │      │ harness file, collect-  │
   │                      │ │  - launches         │      │ ignored as modules,     │
   │ fake-provider        │ │    byos_server.py   │      │ launched as subprocess) │
   │ fixture monkeypatches│ │    as subprocess    │      └─────────────┬───────────┘
   │ detect.requests.get /│ │    (patch=subprocess│                    │
   │ enrich.requests.get  │ │    covers it)        │       subprocess.Popen(
   └──────────────────────┘ └─────────────────────┘         [sys.executable, harness],
                                                              env={...,
                                                                SKYPANE_TEST_NO_NETWORK=1,
                                                                PYTHONPATH=<sitecustomize dir>})
                                                                        │
                                                          ┌─────────────▼───────────────┐
                                                          │ child interpreter starts:    │
                                                          │ sitecustomize.py sees the    │
                                                          │ env var → imports            │
                                                          │ pytest_socket, calls         │
                                                          │ disable_socket() +           │
                                                          │ socket_allow_hosts([...])    │
                                                          │ before companion/app.py's    │
                                                          │ own code runs                │
                                                          └─────────────┬───────────────┘
                                                                        │
                                                     companion/app.py subprocess (real
                                                     ThreadingHTTPServer on loopback) —
                                                     POST /poll-now → poll_loop.run_once()
                                                     → server.plane.detect.query_provider()
                                                     → blocked unless target is loopback
                                                     or the fake-provider fixture already
                                                     monkeypatched requests.get in-process
```

### Recommended Project Structure
```
pyproject.toml                  # [tool.pytest.ini_options], [tool.coverage.run] patch=["subprocess"]
conftest.py                     # repo-root: socket guard config, shared fixtures, collect_ignore for companion/test_*.py
server/
├── conftest.py                 # server-specific fixtures (fake provider, tmp_path helpers) if needed
├── test_*.py                   # migrated, real pytest test functions
stub-server/
├── test_poll_cycle.py          # migrated
companion/
├── test_*.py                   # UNCHANGED hand-rolled harnesses (Phase 33 scope) — collect-ignored
├── test_legacy_harness_shim.py # NEW: one pytest test per legacy companion harness, subprocess + exit-code assert
scripts/
├── run-all-tests.sh            # thin wrapper: exec "${PYTHON}" -m pytest "$@"  (PYTHON= contract kept)
# scripts/run_all_tests.py       # RETIRED this phase
.planning/phases/32.../
├── 32-MIGRATION-LEDGER.md      # one row per pre-migration check → new node id or "deleted: reason"
```

### Pattern 1: Mechanical pre-migration baseline capture (not source-grepping)
**What:** Run each of the 15 server-side harnesses standalone under the *current* interpreter and capture its `PASS <label>` / `FAIL <label>` transcript, exactly as `31-BASELINE-CHECKS.txt` did for the companion browser harnesses in Phase 31.
**When to use:** Before touching any of the 15 files, as the first step of the migration ledger.
**Why not grep `check(` call sites:** verified in this session that grepping for `check(` call sites under-or-over-counts relative to each file's own `EXPECTED_CHECK_COUNT` for at least two files (`server/test_config_history.py`: 90 call sites vs. `EXPECTED_CHECK_COUNT = 60`; `server/test_illustrations.py`: 53 call sites vs. `EXPECTED_CHECK_COUNT = 60`) — some checks are emitted from inside `for` loops (confirmed at `server/test_config_history.py:396-436`, looping over `device_config.THEMES.items()`), so a single `check(` call site can execute (and print) a variable number of times. The only reliable ground truth is the harness's own stdout.
**Example (verified live in this session):**
```bash
$ server/.venv/bin/python3 server/test_dither.py
PASS panel_palette_image() carries exactly PALETTE_RGB's 6 entries, unpadded
PASS dither_to_full_panel_palette() on a hue-rich synthetic image yields indices that are a subset of {0,1,2,3,4,5}
PASS a flat single-color RGB source quantizes to exactly that color's own index
PASS dither_to_full_panel_palette() is deterministic for the same input image
PASS write_calibration_preview() writes exactly one palette-swatch PNG and returns its path
PASS build_mood_background() no longer exists on server.plane.dither (D-21 retirement)
dither: 6/6 checks pass
```
Capture this for all 15 files (`for f in server/test_*.py stub-server/test_poll_cycle.py; do server/.venv/bin/python3 "$f" > "32-BASELINE-CHECKS-$(basename "$f" .py).txt" 2>&1; done`), then the ledger maps each `PASS`/`FAIL` line 1:1 to a new pytest node id.

### Pattern 2: Fake provider seam (dependency injection over monkeypatching, but compatible with the existing monkeypatch convention)
**What:** `server/plane/detect.py`'s `query_provider(name, lat, lon, radius_nm, timeout=10.0)` (`server/plane/detect.py:404-416`) calls `requests.get(url, ...)` directly against a hardcoded `PROVIDERS[name]["url_template"]` (`detect.py:114-127`); `server/plane/enrich.py` does the same against `ADSBDB_URL` (`enrich.py:71,164-177`). Neither module currently accepts an injected transport, session, or base-URL override — every existing test (`server/test_plane_detection.py:507-710`) monkeypatches the module-level `detect.requests.get` attribute directly.
**When to use:** A pytest fixture (e.g. `fake_adsb_provider` in a shared `conftest.py`) should wrap this exact existing convention rather than introduce a new one: `monkeypatch.setattr(detect, "requests", fake_requests_module_or_stub)` or, more surgically, `monkeypatch.setattr(detect.requests, "get", fake_get)`. This keeps the fixture usable by Phase 33's companion tests too (same monkeypatch target, just invoked from a different test file).
**Example (existing convention, `server/test_plane_detection.py:700-710`):**
```python
# Source: server/test_plane_detection.py (existing repo code, not invented here)
def fake_get(url, headers=None, timeout=None):
    ...
original_get = detect.requests.get
detect.requests.get = fake_get
try:
    ...
finally:
    detect.requests.get = original_get
```
A pytest fixture version:
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

### Pattern 3: Non-loopback socket guard, extended across the process boundary
**What:** In-process: `--disable-socket --allow-hosts=127.0.0.1,::1,localhost` via pytest-socket, set as `addopts` in `[tool.pytest.ini_options]` (applies to every test by default; a test that legitimately needs a real external call would use pytest-socket's own `@pytest.mark.enable_socket` escape hatch — none should exist in this phase's scope). Cross-process: a `sitecustomize.py` on a `PYTHONPATH` entry, activated by one new env var, calling pytest-socket's own public functions directly.
**When to use:** Every test; the cross-process variant specifically for `companion/test_companion_app.py`'s `Harness.start()` and `stub-server/test_poll_cycle.py`'s byos-launching harness.
**Example (sitecustomize hook — new code, following the project's existing env-var-gated-test-behaviour convention seen at `auth.PASSWORD_ENV_VAR`/`app_module.SLEEP_ENV_VAR`):**
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
# companion/test_companion_app.py Harness.start() — one-line env addition
env = dict(os.environ)
env["SKYPANE_TEST_NO_NETWORK"] = "1"
env["PYTHONPATH"] = os.pathsep.join(
    filter(None, [str(TEST_SUPPORT_DIR), env.get("PYTHONPATH")])
)
self.proc = subprocess.Popen([sys.executable, APP_PATH, ...], env=env)
```
**Self-test proving the guard trips (required by CONTEXT.md's success criterion 2):**
```python
def test_non_loopback_socket_is_blocked():
    import socket
    with pytest.raises(Exception):  # pytest_socket.SocketBlockedError / SocketConnectBlockedError
        socket.create_connection(("example.com", 80), timeout=2)
```
Verified in this session (hand-rolled prototype, same principle): a loopback `connect()` succeeds and a non-loopback `urlopen()` raises before any data leaves the process.

### Pattern 4: Subprocess coverage via `patch = ["subprocess"]`
**What:** `[tool.coverage.run] patch = ["subprocess"]` in `pyproject.toml` — a single coverage.py config line, confirmed via official docs to (a) require coverage ≥ 7.10 (already satisfied, 7.16.1 pinned), (b) automatically set `parallel = true`, and (c) "configure everything to collect data in Python processes you created... for processes created with subprocess, os.system(), or one of the execv or spawnv family of functions" — exactly how `stub-server/test_poll_cycle.py` launches `byos_server.py` (`subprocess.Popen` at `stub-server/test_poll_cycle.py:282`) and how `companion/test_companion_app.py`'s `Harness` launches `companion/app.py`.
**When to use:** Once, in `pyproject.toml`, not per-test.
**Why not pytest-cov's older subprocess mechanism:** confirmed via pytest-cov's own docs (fetched in this session) that pytest-cov 6.3 and older used a `.pth`-file injection to auto-start coverage in subprocesses, and this **was removed in pytest-cov 7** — the pinned `pytest-cov==7.1.0` no longer has it. `patch = ["subprocess"]` is not a stylistic alternative; it is the only mechanism pytest-cov 7+ still supports.
**Example:**
```toml
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

### Anti-Patterns to Avoid
- **Grepping source for `check(` call sites to build the migration ledger baseline:** verified unreliable in this session (loop-emitted checks make static counting diverge from the runtime truth). Always run the harness and capture stdout.
- **Patching only `socket.socket.connect`:** verified in this session to still leak a real DNS query via `socket.getaddrinfo` before the connect-time check fires. Use pytest-socket (or, if hand-rolling, patch `getaddrinfo`/`gethostbyname` too).
- **Assuming a `conftest.py` guard reaches subprocess-launched servers:** it does not; `companion/app.py` and `stub-server/byos_server.py` run in separate OS processes started via `subprocess.Popen`, with their own fresh `socket` module state.
- **Restating `pytest-cov`'s old `.pth`-based subprocess trick from tutorials/Stack Overflow written before pytest-cov 7:** that mechanism is gone in the pinned version; only `coverage`'s own `patch=["subprocess"]` remains supported.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Non-loopback socket blocking | A `conftest.py` monkeypatch of `socket.socket.connect` only | `pytest-socket` (`disable_socket`/`socket_allow_hosts`, or `--disable-socket --allow-hosts=...`) | Already handles `getaddrinfo`/`gethostbyname` DNS-leak edge case, exception pickling for xdist workers, and a documented per-test escape hatch (`@pytest.mark.enable_socket`) — a hand-rolled version verified in this session to be incomplete on the first attempt |
| Parallel test execution + reporting + per-harness timing table | A bespoke `ThreadPoolExecutor` orchestrator (what `scripts/run_all_tests.py` currently is) | `pytest-xdist -n auto` | `run_all_tests.py`'s own docstring already narrates outgrowing bash and hand-rolled concurrency; pytest-xdist is the maintained, standard replacement for exactly that problem |
| Subprocess coverage collection | Custom `COVERAGE_PROCESS_START` + hand-written `sitecustomize.py` coverage bootstrap | `[tool.coverage.run] patch = ["subprocess"]` | This is coverage.py's own built-in, officially documented mechanism for exactly this case (added in 7.10 specifically to replace ad hoc subprocess-coverage bootstrapping) |
| Hash-locked dependency files | Manually computing sha256 of each wheel and hand-writing `--hash=` lines | `uv pip compile --generate-hashes` (or `pip-tools`) | Verified in this session to correctly resolve, pin, and hash both direct and transitive dependencies for a specific target Python version in one command |

**Key insight:** every "hard part" of this phase already has a purpose-built, currently-maintained library solution; the risk in this phase is not missing tooling but *forgetting that a subprocess is a different process* — three of the four Don't-Hand-Roll rows above trace back to that one fact (coverage doesn't see subprocess execution by default, socket guards don't reach subprocess socket state by default, and the companion app *only* runs as a subprocess in these tests).

## Common Pitfalls

### Pitfall 1: Static grep of `check(` call sites does not equal the true check count
**What goes wrong:** Building the migration ledger from a source-code scan (`grep -c check(`) undercounts or overcounts relative to the harness's own enforced `EXPECTED_CHECK_COUNT`.
**Why it happens:** Some checks are emitted from inside `for` loops over data (e.g. `server/test_config_history.py:396-436` loops over `device_config.THEMES.items()` and calls `check()` once per theme) — one call site, N executions.
**How to avoid:** Run every harness standalone first and capture its stdout transcript (Pattern 1 above); build the ledger from that, never from source grep.
**Warning signs:** A file where `grep -c check(` disagrees with its own `EXPECTED_CHECK_COUNT` — verified present in at least `server/test_config_history.py` (90 vs. 60) and `server/test_illustrations.py` (53 vs. 60).

### Pitfall 2: A socket guard that only patches `.connect()` still leaks DNS queries
**What goes wrong:** A test that calls `urllib.request.urlopen("http://example.com")` under a `.connect()`-only guard still performs a real `socket.getaddrinfo()` DNS lookup (a real network round-trip) before the guard has a chance to block anything.
**Why it happens:** `getaddrinfo` is a separate syscall/libc entry point from `connect`; blocking one doesn't block the other.
**How to avoid:** Use `pytest-socket`, which patches all three (`socket.socket`, `socket.getaddrinfo`, `socket.gethostbyname`) — confirmed by reading its installed source in this session.
**Warning signs:** A "network-free" test suite that still shows outbound DNS traffic in `tcpdump`/`strace` even though every `connect()` attempt fails.

### Pitfall 3: pytest-cov 7's subprocess story is not what most tutorials describe
**What goes wrong:** Following a blog post or Stack Overflow answer that says "add a `.pth` file that calls `coverage.process_startup()`" for subprocess coverage.
**Why it happens:** That was pytest-cov's own mechanism through version 6.3; it was **removed in pytest-cov 7** (confirmed via the pytest-cov docs fetched in this session), which is the pinned major version this phase installs (`pytest-cov==7.1.0`).
**How to avoid:** Use coverage.py's own `[tool.coverage.run] patch = ["subprocess"]` (added in coverage 7.10) instead — this is the currently-documented, currently-supported path.
**Warning signs:** Following instructions that predate pytest-cov 7 (2024 or earlier) without cross-checking against the current docs.

### Pitfall 4: Environment ceiling on "Python 3.14" verification
**What goes wrong:** Assuming this research's local install proves *the final released* Python 3.14.0 (or a post-release patch like 3.14.1) is dependency-compatible.
**Why it happens:** `uv python list` in this sandbox offered `cpython-3.14.0rc2` as its newest available 3.14 build — not a final release build. This is very likely a stale/limited local python-build-standalone registry snapshot inside this sandbox, not a statement that Python 3.14's final release doesn't exist yet (by 2026-09-23, well past a plausible October-2025-class release date, a final 3.14.x almost certainly exists upstream) — but this session could not download or verify against it directly.
**How to avoid:** Treat the compatibility verification in this research (all pinned packages install and import cleanly under 3.14.0rc2, with a genuine compiled `cp314` wheel for Pillow) as strong evidence of 3.14 compatibility in general (ABI-wise, `cp314` wheel tags are RC-to-final stable), but have the executing agent re-run the same install command against whatever Python 3.14 interpreter the actual CI runner (`actions/setup-python` with `python-version: '3.14'`) resolves to, and treat any divergence as a real finding, not a research gap.
**Warning signs:** A CI run against real `python-version: '3.14'` failing to resolve a wheel for one of the pinned packages where this research's rc2 install succeeded.

### Pitfall 5: `deploy/deploy.sh`'s change-detection currently hashes the *unlocked* file
**What goes wrong:** After generating a hash-locked runtime lock file, forgetting to repoint `deploy/deploy.sh`'s `sha256sum` check and `pip install` call at the new locked file — it currently computes `sha256sum server/requirements.txt` directly and installs `-r server/requirements.txt` (`deploy/deploy.sh:44-51`).
**Why it happens:** The lock file is a new artifact; the deploy script has one specific line that names the old file by path twice.
**How to avoid:** Either (a) make the lock file the new `server/requirements.txt` in place (simplest — keeps deploy.sh's existing path references correct with zero further edits, if a checked-in `.in` source is kept alongside it for regeneration), or (b) introduce a distinctly-named lock file and update both the `sha256sum` and `pip install --require-hashes -r` lines in `deploy/deploy.sh` to reference it. Either way, `pip install --require-hashes` must be added — a lock file with hashes present but installed without `--require-hashes` provides no supply-chain guarantee.
**Warning signs:** `deploy/deploy.sh` unchanged in a diff that also adds lock files.

## Harness Migration Inventory (server-side, TST-02 scope)

Exact per-file line counts (`wc -l`) and each file's own enforced `EXPECTED_CHECK_COUNT` (the harness's own ground truth for "did every check run", read directly from source — **not** the unreliable `check(`-call-site grep count, see Pitfall 1):

| File | Lines | `EXPECTED_CHECK_COUNT` | Notes |
|------|------:|------:|-------|
| `server/test_dither.py` | 157 | 6 | Verified live in this session: `6/6 checks pass` |
| `server/test_runway_config.py` | 250 | 14 | |
| `server/test_notify.py` | 265 | 8 | |
| `server/test_panel_preview.py` | 312 | 11 | |
| `server/test_pipeline_e2e.py` | 475 | 7 | Also exercises `stub-server/byos_server.py` protocol end-to-end |
| `server/test_manual_resolutions.py` | 506 | 23 | Contains `os.chmod(..., 0o500)` read-only-directory checks (`:439,461`) with **no existing root guard** — needs the euid-0 skip this phase's migration adds |
| `server/test_colour_rules.py` | 637 | 33 | |
| `server/test_illustrations.py` | 1,150 | 60 | `check(` call-site count (53) disagrees with `EXPECTED_CHECK_COUNT` (60) — loop-emitted checks, use Pattern 1 |
| `server/test_plane_detection.py` | 1,325 | 47 | Uses the `detect.requests.get` monkeypatch seam the fake-provider fixture formalizes |
| `server/test_enrich.py` | 1,462 | 60 | Uses the adsbdb `requests.get` seam, same fixture family |
| `stub-server/test_poll_cycle.py` | 1,744 | 46 | Launches `byos_server.py` as a real subprocess — the `patch=["subprocess"]` proof point |
| `server/test_config_history.py` | 2,632 | 60 | `check(` call-site count (90) disagrees with `EXPECTED_CHECK_COUNT` (60) — loop-emitted checks over `device_config.THEMES.items()` (`:396-436`), use Pattern 1 |
| `server/test_calendar_rules.py` | 2,872 | 113 | Largest check count among mid-size files |
| `server/test_render.py` | 4,167 | 140 | Largest check count overall; slowest server-side harness (~16-19s standalone per Phase 31's own CI figures) |
| `server/test_poll_loop.py` | 4,637 | 110 | Largest file; exercises `run_once()`, the same function `/poll-now` calls |
| **Total** | **22,591** | **738** | Matches the phase description's "22.6k lines total" figure exactly |

### Proposed batch split for executor-agent-sized plans (Claude's Discretion — batching order/size)

A size-and-risk-balanced split, smallest/lowest-risk first to establish migration conventions before tackling the two largest files:

1. **Wave 0 (infra only, no harness migration):** `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.run]`, repo-root `conftest.py` (socket guard config, fake-provider fixture scaffolding), `server/requirements-dev.txt` additions, empty `32-MIGRATION-LEDGER.md` scaffold.
2. **Batch A (~1,710 lines, 39 checks):** `test_dither.py`, `test_runway_config.py`, `test_notify.py`, `test_panel_preview.py`, `test_pipeline_e2e.py` — establishes the migration pattern on the cheapest files.
3. **Batch B (~1,143 lines, 56 checks):** `test_manual_resolutions.py`, `test_colour_rules.py` — first exercise of the euid-0 root-safety skip pattern.
4. **Batch C (~2,475 lines, 107 checks):** `test_illustrations.py`, `test_plane_detection.py` — first exercise of the fake-provider fixture (ADS-B side).
5. **Batch D (~1,462 lines, 60 checks):** `test_enrich.py` — fake-provider fixture, adsbdb side; can run alongside Batch C in the same wave if parallel plan execution is available.
6. **Batch E (~1,744 lines, 46 checks):** `stub-server/test_poll_cycle.py` — first exercise of `patch=["subprocess"]` against a real `byos_server.py` child process; natural place to also land the cross-process socket-guard sitecustomize hook, since this file already launches a subprocess and already needs no-network correctness end-to-end.
7. **Batch F (~2,632 lines, 60 checks):** `test_config_history.py` — largest of the "mid" files, loop-emitted checks (Pitfall 1 applies directly).
8. **Batch G (~2,872 lines, 113 checks):** `test_calendar_rules.py` — standalone, largest check count among non-final-two files.
9. **Batch H (~4,167 lines, 140 checks):** `test_render.py` — standalone, largest check count overall.
10. **Batch I (~4,637 lines, 110 checks):** `test_poll_loop.py` — standalone, largest file; also where the `/poll-now`-adjacent `run_once()` contract lives, so land this batch before (or in the same wave as) the targeted `companion/test_companion_app.py:~10771` fake-provider edit.

This ordering is a recommendation, not a requirement — CONTEXT.md leaves batching to Claude's discretion.

## Code Examples

### `pyproject.toml` pytest + coverage configuration
```toml
[tool.pytest.ini_options]
addopts = "--disable-socket --allow-hosts=127.0.0.1,::1,localhost -n auto"
testpaths = ["server", "stub-server", "."]

[tool.coverage.run]
patch = ["subprocess"]
source = ["server", "stub-server", "companion"]
omit = [
    "server/test_*.py",
    "stub-server/test_*.py",
    "companion/test_*.py",
]
# fail_under is set once the measured floor is known (TST-09) — do not
# guess a number here; measure with the omit list above already reduced
# to remove companion/app.py, byos_server.py and make_test_panel.py, then
# set fail_under to that measured value.
```

### Hash-locking with `uv` (verified working in this session)
```bash
uv pip compile --generate-hashes --python-version 3.14 \
    server/requirements.in -o server/requirements.txt
uv pip compile --generate-hashes --python-version 3.14 \
    server/requirements-dev.in -o server/requirements-dev.txt
```
Real output sample from this session (against a 2-line input file):
```
# This file was autogenerated by uv via the following command:
#    uv pip compile --generate-hashes --python-version 3.14 reqs.in -o reqs.lock.txt
certifi==2026.7.22 \
    --hash=sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775 \
    --hash=sha256:741e2c3b351ddf169a738da9f2c048608ff7f2c5cc02f1ebc6b118bb090d5d55
    # via requests
...
Pillow==12.3.0 \
    --hash=sha256:... (11 hashes for this platform/version combination)
requests==2.34.2 \
    --hash=sha256:2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0 \
    --hash=sha256:f288924cae4e29463698d6d60bc6a4da69c89185ad1e0bcc4104f584e960b9ed
urllib3==2.8.0 \
    --hash=sha256:0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3 \
    --hash=sha256:63bf2ead4c879426ebf22ef2a781eeb4aa3b4ae798a0435506f8687fd5bb9b63
```
`deploy/deploy.sh` install step, updated for hashes:
```bash
ssh "${SSH_TARGET}" "sudo -u skypane ${APP_ROOT}/venv/bin/pip install --require-hashes --quiet -r ${APP_ROOT}/server/requirements.txt"
```

### CI: Python 3.14, playwright `--only-shell` + cache, separated concurrency groups
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  test:
    steps:
      - uses: actions/setup-python@...
        with:
          python-version: '3.14'
          cache: pip
          cache-dependency-path: server/requirements*.txt
      - name: Cache Playwright browsers
        uses: actions/cache@...
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ runner.os }}-${{ hashFiles('server/requirements-dev.txt') }}
          # keyed on the playwright version (via the pin in requirements-dev.txt),
          # per CONTEXT.md and per Playwright's own docs recommendation
          # ("cache ... against a hash of the Playwright version")
      - run: server/.venv/bin/python -m playwright install --only-shell chromium --with-deps
      - run: server/.venv/bin/pip install --require-hashes -r server/requirements.txt -r server/requirements-dev.txt
      - run: server/.venv/bin/ruff check .   # target-version now py314
      - run: ./scripts/run-all-tests.sh      # now a thin `exec "${PYTHON}" -m pytest`

  deploy:
    needs: test
    concurrency:
      group: production-deploy
      cancel-in-progress: false   # TST-06: never cancel an in-flight deploy
```

### Firmware host tests wired into `firmware.yml` (no ESP-IDF container needed)
```yaml
jobs:
  build:
    # existing ESP-IDF containerized build job, unchanged

  host-tests:
    name: Firmware host tests (hardware-free)
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@...
      - run: ./firmware/tests/run_host_tests.sh
        # Uses the system `cc` only (gcc/clang, already present on
        # ubuntu-latest per GitHub's runner-images repo) — no Docker,
        # no ESP-IDF toolchain. 0.35s per the code audit's measured
        # baseline.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytest-cov `.pth`-file auto-injection for subprocess coverage | coverage.py's own `[run] patch = ["subprocess"]` | coverage 7.10 added `patch=subprocess`; pytest-cov 7.0 removed the `.pth` mechanism | Any tutorial/answer describing the `.pth` approach predates this and no longer applies to the pinned `pytest-cov==7.1.0` |
| Hand-rolled `ThreadPoolExecutor` test orchestration (`scripts/run_all_tests.py`) | `pytest-xdist -n auto` | This phase | Retires ~320 lines of bespoke concurrency/timeout/reporting code; `scripts/run-all-tests.sh` becomes a thin wrapper |
| Unpinned transitive dependencies, no hashes | `uv pip compile --generate-hashes` (or `pip-tools`) lock files | This phase (TST-08) | Supply-chain integrity: `pip install --require-hashes` now rejects any dependency substitution attack or unpinned-transitive drift |

**Deprecated/outdated:**
- pytest-cov's `.pth`-file subprocess trick: gone as of pytest-cov 7; do not follow instructions written against pytest-cov ≤6.3.
- `scripts/run_all_tests.py`'s `HARNESSES` hand-list and every `EXPECTED_CHECK_COUNT`: retired this phase for the 15 server-side files (companion's equivalents retired in Phase 33).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python 3.14's *final* release (not just the 3.14.0rc2 available in this sandbox) is dependency-compatible with every pinned package | Standard Stack, Pitfall 4 | If CI's `actions/setup-python` with `python-version: '3.14'` resolves a different point release with an ABI or behavior change, a pinned package could fail to install or behave differently than verified here — low risk given `cp314` wheel tags are stable post-RC, but not independently confirmed against the literal final release in this session |
| A2 | `pip-tools`' `pip-compile --generate-hashes` produces functionally equivalent output to `uv pip compile --generate-hashes` for this repo's purposes | Standard Stack (Alternatives Considered) | Only `uv`'s output was exercised in this session; if the planner or executor picks `pip-tools` instead, its output format/behavior was not independently verified here |
| A3 | GitHub-hosted `ubuntu-latest` runners ship a working `cc` (gcc or clang) with no extra install step | Code Examples (firmware host-tests job) | If a future runner-image regression removes the default compiler toolchain, `run_host_tests.sh` would fail in CI with a "compiler not found" error rather than a test failure — this is a well-established GitHub runner-images property, not independently re-verified against the exact `ubuntu-latest` image tag active at execution time |

**None of the core technical claims (package versions, `patch=["subprocess"]` syntax, pytest-socket's guard scope, `uv pip compile --generate-hashes` behavior, ruff's `py314` acceptance, ` --only-shell` flag) are assumed** — every one was verified either by installing/running the real tool in this session or by fetching the current official documentation page directly.

## Open Questions

1. **Does pytest-cov's automatic xdist coverage-combine also pick up the extra `.coverage.*` data files `patch=["subprocess"]` writes for companion/byos child processes?**
   - What we know: pytest-cov automatically combines each xdist worker's own coverage data at session end; `patch=["subprocess"]` writes additional `.coverage.<machine>.<pid>.<random>` files from any subprocess it patches, following coverage.py's standard parallel-data-file naming.
   - What's unclear: whether pytest-cov's own combine step (rather than a manual `coverage combine`) globs *all* matching files in the working directory (including ones from processes pytest-cov didn't itself spawn) or only the files from workers it explicitly tracked.
   - Recommendation: Wave 0 or an early batch should include a smoke check — run one subprocess-launching harness (e.g. `stub-server/test_poll_cycle.py`) migrated, under `pytest --cov -n auto`, and confirm `byos_server.py`'s statements show as covered in the report, not 0%. If they don't, fall back to an explicit `coverage combine` step after the pytest run, before the coverage report/gate.

2. **Exact measured coverage floor once `companion/app.py`, `byos_server.py` and `make_test_panel.py` leave the omit list.**
   - What we know: current gate is 83% with these three files excluded (measured 87% under that scope, per `pyproject.toml`'s own derivation comment); these three files are extensively exercised by every companion/stub-server harness via subprocess, just structurally unmeasured until now — likely to measure well, not poorly, once counted.
   - What's unclear: the actual percentage, which can only come from running the full instrumented suite once `patch=["subprocess"]` is in place.
   - Recommendation: CONTEXT.md already specifies this ("measure, then set fail_under to the measured floor") — treat it as a required, not optional, measurement step near the end of the phase, after all nine batches from the Harness Migration Inventory are merged.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 interpreter | TST-04 (target runtime for tests/CI) | ✓ (via `uv python install 3.14`) | 3.14.0rc2 (newest in this sandbox's local registry — see Pitfall 4) | `actions/setup-python@... python-version: '3.14'` on the real CI runner is the authoritative source; local dev can use `uv python install 3.14` |
| `uv` | Lock-file generation, local 3.14 provisioning | ✓ | 0.8.17 | `pip-tools`' `pip-compile --generate-hashes` if `uv` is not wanted in CI |
| System `cc` (gcc/clang) | `firmware/tests/run_host_tests.sh` in `firmware.yml` | Not directly probed in this sandbox (no firmware host-tests run here), but GitHub's `ubuntu-latest` runner images ship gcc/clang by default `[CITED: actions/runner-images repo]` | — | none needed; this is a standard GH-hosted runner property |
| `slopcheck` | Package Legitimacy Audit | ✓ (installed via `pip install slopcheck`) | 0.6.1 | — |

**Missing dependencies with no fallback:** none identified.
**Missing dependencies with fallback:** none required beyond the `uv` → `pip-tools` lock-tool fallback already noted above.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-xdist 3.8.0 + pytest-cov 7.1.0 (all newly added this phase) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (new this phase) |
| Quick run command | `server/.venv/bin/python3 -m pytest server/test_dither.py -q` (single fast migrated file) |
| Full suite command | `./scripts/run-all-tests.sh` (thin wrapper over `pytest -n auto`, keeps the `PYTHON=` override contract) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TST-01 | pytest/xdist/cov configured, discoverable, coverage gate enforced | smoke | `pytest --collect-only -q` then `pytest -n auto --cov` | ❌ Wave 0 |
| TST-02 | Every one of the 15 server-side harnesses' checks has a mapped pytest node id | unit (per migrated file) + ledger completeness check | `pytest server/ stub-server/ -v` plus a manual diff of `32-MIGRATION-LEDGER.md` against the pre-migration baseline transcripts | ❌ per-batch, see Harness Migration Inventory |
| TST-03 | A test opening a non-loopback socket fails; `/poll-now` uses the fake provider | unit (self-test) + integration | `pytest -k test_non_loopback_socket_is_blocked` ; `pytest companion/test_companion_app.py::test_poll_now_uses_fake_provider` (shim-launched) | ❌ new self-test; ❌ targeted edit to existing `/poll-now` checks |
| TST-04 | CI/ruff on Python 3.14 | smoke | `python3 --version` in CI logs; `ruff check .` (target-version py314) | N/A (CI config change, not a test file) |
| TST-05 | Firmware host tests run in CI | smoke | `./firmware/tests/run_host_tests.sh` (already exists, 0.35s) | ✓ already exists |
| TST-06 | Concurrency groups behave as specified | manual-only (CI semantics) | Two overlapping pushes to `main`, observe that the deploy job for the first is never cancelled | N/A — CI YAML behavior, not unit-testable |
| TST-07 | Playwright shell-only install + cache hit on second run | smoke | Two consecutive CI runs; second run's "Cache Playwright browsers" step reports a cache hit | N/A — CI behavior |
| TST-08 | `pip install --require-hashes` succeeds against the lock file | smoke | `pip install --require-hashes -r server/requirements.txt` in a clean venv | ❌ new lock file |
| TST-09 | `companion/app.py`/`byos_server.py`/`make_test_panel.py` show non-zero, non-trivial coverage; gate raised | integration | `pytest -n auto --cov --cov-report=term-missing` then inspect the per-file report | ❌ depends on all prior batches landing |

### Sampling Rate
- **Per task commit:** the single newly-migrated file's own test module, e.g. `pytest server/test_dither.py -q`.
- **Per wave/batch merge:** `pytest server/ stub-server/ -n auto` (everything migrated so far).
- **Phase gate:** `./scripts/run-all-tests.sh` full green (including the companion pytest shim) before `/gsd:verify-work`, plus the coverage-floor measurement (Open Question 2) recorded in `pyproject.toml`'s own comment.

### Wave 0 Gaps
- [ ] `conftest.py` (repo root) — socket guard `addopts`, `collect_ignore` for `companion/test_*.py`, shared fixtures
- [ ] `companion/test_legacy_harness_shim.py` (or equivalent name) — one test per remaining companion harness, subprocess + exit-code assert
- [ ] `test-support/sitecustomize.py` (or equivalent path) — cross-process socket guard activation
- [ ] Framework install: add `pytest==9.1.1`, `pytest-xdist==3.8.0`, `pytest-cov==7.1.0`, `pytest-socket==0.8.1` to `server/requirements-dev.txt`
- [ ] `32-MIGRATION-LEDGER.md` scaffold (empty table, headers only) in the phase directory
- [ ] Per-harness pre-migration `PASS`/`FAIL` baseline transcripts (15 files) — Pattern 1

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not touched by this phase (test infra only) |
| V3 Session Management | no | Not touched by this phase |
| V4 Access Control | no | Not touched by this phase |
| V5 Input Validation | no (test infra, not an input-handling surface) | N/A |
| V6 Cryptography | marginal — hash-locking (TST-08) | `--generate-hashes` uses SHA-256 per-artifact hashes (pip/uv standard), not a cryptographic control on application data; verify hashes via `pip install --require-hashes`, never hand-edit a hash |

### Known Threat Patterns for this phase's stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Dependency substitution / typosquatting in CI installs | Tampering | Hash-locked requirements + `pip install --require-hashes` (TST-08); already-run `slopcheck` legitimacy audit on the four new packages this phase adds |
| A test silently making a real outbound network call (data exfiltration risk from a compromised or buggy test/dependency, and a source of test flakiness/non-determinism) | Information Disclosure / Tampering | The non-loopback socket guard (TST-03), extended across the subprocess boundary via the sitecustomize hook — this is the phase's actual security-relevant deliverable, not an add-on |
| Secret material accidentally installed by test-only pip packages with a `postinstall`-equivalent step | Tampering | None of the four new packages (`pytest`, `pytest-xdist`, `pytest-cov`, `pytest-socket`) are compiled/native extensions with install-time scripts of concern; pure-Python or standard-build wheels only, confirmed during installation in this session |

This phase is overwhelmingly test-infrastructure, not a request-handling surface — the one genuine security property it delivers is the no-network guarantee (TST-03), which this research treats as a first-class deliverable throughout (Pattern 3, Pitfall 2, Code Examples' self-test).

## Sources

### Primary (HIGH confidence)
- Live installation and execution in this research session: `uv python install 3.14`; `uv venv`/`uv pip install` of `Pillow==12.3.0`, `requests==2.34.2`, `ruff==0.16.8`, `coverage==7.16.1`, `pytest`, `pytest-xdist`, `pytest-cov`, `pytest-socket`, `playwright==1.63.0` under Python 3.14.0rc2 — all succeeded, `cp314` compiled wheel confirmed for Pillow
- Direct source inspection of the installed `pytest_socket/__init__.py` (0.8.1) in this session
- Direct repo inspection: `server/plane/detect.py`, `server/plane/enrich.py`, `server/test_plane_detection.py`, `server/test_dither.py` (run live), `companion/test_companion_app.py` (Harness class, `/poll-now` checks), `stub-server/test_poll_cycle.py`, `scripts/run_all_tests.py`, `scripts/run-all-tests.sh`, `pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/firmware.yml`, `firmware/tests/run_host_tests.sh`, `deploy/deploy.sh`, `deploy/provision.sh`
- https://coverage.readthedocs.io/en/7.16.1/subprocess.html and .../config.html — `patch` setting values and semantics, fetched directly in this session
- https://pytest-cov.readthedocs.io/en/latest/subprocess-support.html — pytest-cov 7's removal of the `.pth` mechanism, fetched directly in this session
- https://playwright.dev/python/docs/ci — cache-key-on-version guidance, fetched directly in this session
- `slopcheck` v0.6.1 run against `pytest`, `pytest-xdist`, `pytest-cov`, `pytest-socket` — all `[OK]`

### Secondary (MEDIUM confidence)
- `.planning/phases/31-.../31-TIMINGS.md` — real CI job timing figures (327s total job wall time, 4 vCPU runner, per-harness breakdown) used for the Sampling Rate / xdist expectation context in this file
- General GitHub Actions `concurrency:`/`environment:` semantics (well-established, low-volatility platform feature) — not independently re-fetched in this session, relied on training knowledge cross-checked against the repo's own existing, working `ci.yml`

### Tertiary (LOW confidence)
- Whether `ubuntu-latest`'s default image always ships a working `cc` with zero extra steps — treated as effectively certain (GitHub's own runner-images documentation is well known to include a full build toolchain) but not independently re-fetched in this session; flagged as Assumption A3

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package version was actually installed and exercised under Python 3.14 in this session, not just checked against a registry
- Architecture (fake provider seam, socket guard, subprocess coverage): HIGH — each mechanism was either read directly from the installed library's own source or proven with a working local prototype
- Pitfalls: HIGH — all five were discovered empirically in this session (grep-vs-EXPECTED_CHECK_COUNT mismatch, DNS-leak-through-getaddrinfo, pytest-cov's removed `.pth` mechanism, the rc2-vs-final Python 3.14 ceiling, deploy.sh's unlocked-file reference) rather than asserted from training knowledge
- Migration batching: MEDIUM — the line/check counts are exact (measured), but the proposed wave grouping is a judgment call left explicitly to Claude's discretion by CONTEXT.md

**Research date:** 2026-09-23
**Valid until:** 30 days for the architecture/pitfalls findings (stable); re-verify the Python 3.14 package matrix (Pitfall 4) once CI's `actions/setup-python` resolves a specific final 3.14.x release, since this session could only reach an rc2 build locally
