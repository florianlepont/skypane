---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 01
subsystem: testing
tags: [pytest, pytest-xdist, pytest-cov, pytest-socket, ruff, network-isolation, fixtures]

# Dependency graph
requires: []
provides:
  - pytest + pytest-xdist + pytest-cov + pytest-socket as dev-only dependencies, configured in pyproject.toml
  - ruff target-version moved py311 -> py314 (D-A4)
  - test-support/skypane_test_support.py: shared test contracts (NetworkAccessBlocked, guarded_resolvers(),
    install_child_network_guard(), FakeResponse/FakeProviders, child_env(), LEGACY_COMPANION_HARNESSES,
    LEGACY_COMPANION_COLLECT_IGNORE, requires_non_root)
  - test-support/sitecustomize.py: child-interpreter hook installing the network guard and/or fake provider
  - repo-root conftest.py: collect_ignore for the 9 legacy companion harnesses, autouse non-loopback DNS
    guard, fake_providers fixture
  - companion/test_legacy_harness_shim.py: one pytest test per legacy companion harness (subprocess + exit
    code), plus a drift guard proving the hard-coded list matches disk
affects: [32-02, 32-03, 32-04, 32-05, 32-06, 32-07, 32-08, 32-09, 32-10, 32-11, 32-12, 32-13, 32-14, 32-15]

# Tech tracking
tech-stack:
  added: [pytest==9.1.1, pytest-xdist==3.8.0, pytest-cov==7.1.0, pytest-socket==0.8.1]
  patterns:
    - "Non-loopback network guard split across two layers: pytest-socket's --allow-hosts (connect()
       only) plus a hand-rolled guarded_resolvers() for DNS (getaddrinfo/gethostbyname/gethostbyname_ex),
       because --allow-hosts mode never patches DNS resolution on its own."
    - "The same guard is installed in a child interpreter via a PYTHONPATH-injected sitecustomize.py,
       gated by one env var (SKYPANE_TEST_NO_NETWORK), mirroring the project's existing
       auth.PASSWORD_ENV_VAR / app_module.SLEEP_ENV_VAR env-var-gated subprocess convention."
    - "Fake ADS-B/adsbdb provider is a single monkeypatch of the shared requests.get attribute
       (the seam server/test_plane_detection.py already used), routed by hostname, reused in-process
       via a pytest fixture and cross-process via to_file()/from_file() + a JSONL calls log."
    - "Legacy (not-yet-migrated) companion harnesses stay reachable through pytest via a
       subprocess-launched shim, collect-ignored as modules so pytest never imports them directly."

key-files:
  created:
    - test-support/skypane_test_support.py
    - test-support/sitecustomize.py
    - test-support/test_test_support.py
    - companion/test_legacy_harness_shim.py
  modified:
    - server/requirements-dev.txt
    - pyproject.toml
    - .gitignore
    - conftest.py (new file at repo root)

key-decisions:
  - "guarded_resolvers() allows None/empty host, 'localhost', any '*.localhost' name, and any IP literal
     (ipaddress.ip_address after stripping IPv6 zone/brackets) - everything else raises
     NetworkAccessBlocked before any real lookup happens."
  - "install_child_network_guard() calls pytest_socket.socket_allow_hosts() only, never disable_socket() -
     disable_socket() would also block socket CREATION, breaking a child ThreadingHTTPServer's own bind()."
  - "FakeProviders.get() falls through to the real requests.get captured at install time for any URL whose
     host is not one of the four known provider hosts, so an unexpected URL still hits the socket guard
     instead of silently succeeding."
  - "sitecustomize.py has zero exception handling by design - a guard that fails to install must crash the
     child interpreter loudly, not fail open."

patterns-established:
  - "Every future companion-harness migration (Phase 33) reuses the same fake_providers fixture and the
     same child_env()/sitecustomize.py mechanism this plan built, rather than reinventing per-file stubs."

requirements-completed: [TST-01, TST-03, TST-04]

# Metrics
duration: 55min
completed: 2026-09-23
---

# Phase 32 Plan 01: Test foundation infrastructure Summary

**pytest 9.1.1 + xdist + cov + socket wired into pyproject.toml with ruff on py314, a two-layer non-loopback network guard (pytest-socket connect() + a hand-rolled DNS guard) proven in-process and across a subprocess boundary, an injectable fake ADS-B/adsbdb provider fixture reused the same way, and a subprocess shim that makes all 9 still-hand-rolled companion harnesses reachable through `pytest -n auto` without being collected as test modules.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-23T14:32:00Z
- **Completed:** 2026-09-23T15:27:00Z
- **Tasks:** 3 (Task 2 executed as an explicit RED -> GREEN TDD cycle)
- **Files modified:** 8 (server/requirements-dev.txt, pyproject.toml, .gitignore, conftest.py,
  test-support/skypane_test_support.py, test-support/sitecustomize.py, test-support/test_test_support.py,
  companion/test_legacy_harness_shim.py)

## Accomplishments
- pytest + pytest-xdist + pytest-cov + pytest-socket installed into the existing `server/.venv` and
  configured via `[tool.pytest.ini_options]`; ruff `target-version` moved to `py314`; both green
  (`ruff check .` clean, `pytest --version` reports 9.1.1).
- A non-loopback network guard that closes the exact DNS-leak gap `--allow-hosts` mode leaves open
  (verified against the installed `pytest_socket` 0.8.1 source: it only patches `connect()`, never
  `getaddrinfo`/`gethostbyname` when hosts are allowed), proven both in-process and inside a real child
  Python interpreter launched via `child_env()`.
- An injectable `FakeProviders` fixture that serves canned/default/failure responses to
  `detect.query_provider()` and `enrich.default_transport()`, both in-process (pytest fixture) and across a
  process boundary (JSON spec file + JSONL calls log, reloaded via `sitecustomize.py`).
- A pytest shim (`companion/test_legacy_harness_shim.py`) that runs each of the 9 legacy companion harnesses
  as one subprocess-launched test asserted on exit code, with a drift guard proving the hard-coded harness
  list still matches `companion/test_*.py` on disk.

## Task Commits

Each task was committed atomically:

1. **Task 1: Dev dependencies, pytest configuration, ruff py314** - `531822d` (feat)
2. **Task 2: test-support contracts, child-process hook, root conftest, guard self-tests** - `89af78b` (test, RED) + `4f29a7f` (feat, GREEN)
3. **Task 3: Legacy companion harness shim** - `3073465` (feat)

**Plan metadata:** (this commit, docs: complete plan)

_Note: Task 2 is `tdd="true"` and produced two commits - the test file confirmed failing at collection
(`ModuleNotFoundError: No module named 'skypane_test_support'`) before the implementation files existed on
disk, then the implementation landed and all 12 tests passed, both under `-n 0` and `-n 4`._

## Files Created/Modified
- `server/requirements-dev.txt` - added `pytest==9.1.1`, `pytest-xdist==3.8.0`, `pytest-cov==7.1.0`, `pytest-socket==0.8.1`
- `pyproject.toml` - `[tool.pytest.ini_options]` (importlib mode, strict markers/config, socket-guard
  addopts, testpaths, pythonpath, `legacy_harness`/`slow` markers, `xfail_strict`); ruff `target-version`
  `py311` -> `py314`
- `.gitignore` - `.pytest_cache/`
- `test-support/skypane_test_support.py` (new) - the shared test contracts
- `test-support/sitecustomize.py` (new) - child-interpreter hook
- `conftest.py` (new, repo root) - `collect_ignore`, autouse DNS guard, `fake_providers` fixture
- `test-support/test_test_support.py` (new) - 12 self-tests proving the guard trips (connect + DNS,
  in-process and cross-process), loopback stays usable, and the fake provider fixture works both
  in-process and cross-process
- `companion/test_legacy_harness_shim.py` (new) - one test per legacy companion harness + a disk-drift guard

## Decisions Made
- `guarded_resolvers()`'s allow-list logic (None/empty, `localhost`/`*.localhost`, any IP literal) lives in
  `test-support/skypane_test_support.py` rather than being duplicated between the in-process conftest
  fixture and the child-process `sitecustomize.py` hook - both call the same function.
- `FakeProviders.install()` takes a `setattr_fn` parameter (defaulting to plain `setattr`) specifically so
  a pytest fixture can pass `monkeypatch.setattr` for automatic teardown, while a child interpreter with no
  `monkeypatch` fixture available still works with the plain default (its patch is discarded at process
  exit anyway).
- The legacy-harness shim mirrors `scripts/run_all_tests.py`'s own `_run_one()` subprocess shape exactly
  (real file for stdout/stderr rather than a pipe, `start_new_session=True`, `os.killpg` with a
  `ProcessLookupError`/`PermissionError` fallback to `proc.kill()`) so its timeout/kill behaviour is a
  known-good pattern, not a new one.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' automated verification and acceptance criteria
passed without needing a Rule 1/2/3 auto-fix.

## Issues Encountered

While proving Task 3's shim end-to-end (beyond the plan's own required verification, which deliberately
scopes the harness run down to `contrast_check` via a `-k` filter), running the shim against
`companion/test_status_pages.py` surfaced a pre-existing failure unrelated to this plan's changes:
`anomaly_active() runs on every page render and must never raise` fails standalone
(`server/.venv/bin/python3 companion/test_status_pages.py` -> `status-pages: 316/317 checks pass`) with
**no code from this plan imported or exercised** - this sandbox executes as `uid=0` (root), and STATE.md's
own session history repeatedly documents an identical "5-check root-sandbox baseline (4 x WR-11, 1 x
`anomaly_active()`)" across many unrelated prior plans, confirming this is a known, pre-existing,
root-execution-environment condition rather than a regression this plan introduced. Per the scope boundary
("only auto-fix issues directly caused by the current task's changes"), this was left as-is - the shim
correctly propagated the harness's real non-zero exit code, which is exactly the behaviour Task 3 requires.

## Next Phase Readiness
- The shared contracts (`fake_providers` fixture, `child_env()`, the network guard) are ready for plan
  32-02 onward to consume for the 15 server-side harness migrations.
- `scripts/run-all-tests.sh` and `scripts/run_all_tests.py` are untouched, as planned - the legacy runner
  keeps working until plan 32-13 retires it.
- No blockers. The one noted pre-existing `anomaly_active()`/root-sandbox flake is environment-specific and
  orthogonal to this plan's scope; it is not expected to affect any later plan's own verification since
  every later plan's automated checks target files this plan did not touch.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 8 created/modified files confirmed present on disk; all 4 task commit hashes
(`531822d`, `89af78b`, `4f29a7f`, `3073465`) confirmed present in `git log --oneline --all`.
