# Phase 32: Test foundation — pytest and CI you can trust - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning
**Source:** Audit ledger `.planning/audits/2026-09-23-code-audit.md` (decisions D-A1..D-A6) + developer answers in this planning session

<domain>
## Phase Boundary

Phase 32 builds the pytest infrastructure and migrates the **server-side** harnesses:

- pytest + pytest-xdist + pytest-cov as dev-only dependencies (production stays stdlib + Pillow + requests), configured in `pyproject.toml`, shared fixtures in `conftest.py` (TST-01).
- `server/test_*.py` (14 files) and `stub-server/test_poll_cycle.py` rewritten as real pytest tests, with a migration ledger mapping every old check to a new test id or to a deletion with a reason (TST-02).
- An injectable fake ADS-B / adsbdb provider fixture and a conftest guard that fails any test opening a non-loopback socket (TST-03).
- CI and ruff `target-version` on the production Python version (TST-04).
- Firmware host tests (`firmware/tests/run_host_tests.sh`) run in `firmware.yml` (TST-05).
- Separate test and deploy concurrency groups; an in-flight deploy is never cancelled (TST-06).
- Playwright installs the Chromium headless shell only, and `~/.cache/ms-playwright` is cached (TST-07).
- Hash-pinned lock files for runtime and dev dependencies (TST-08).
- Subprocess coverage so `companion/app.py` and `stub-server/byos_server.py` are measured; `fail_under` raised to the measured floor (TST-09).

**Not in this phase:** rewriting the companion harnesses (`companion/test_*.py`) as pytest tests, the single app-server fixture, pytest-playwright, source-text assertion cleanup, root-safety of companion tests, retiring companion `EXPECTED_CHECK_COUNT`s, and the closing 2018-check parity (TST-10..TST-15 → Phase 33).

</domain>

<decisions>
## Implementation Decisions

### Framework (D-A2, locked)
- Full migration to pytest. pytest, pytest-xdist and pytest-cov live in `server/requirements-dev.txt` only; `deploy/deploy.sh` keeps installing `server/requirements.txt` only.
- pytest configuration goes in the existing repo-root `pyproject.toml` (`[tool.pytest.ini_options]`); still no `[project]` table.
- Coverage gate moves from the hand-run `coverage combine/report` in `run_all_tests.py` to pytest-cov (`--cov-fail-under` or `[tool.coverage.report] fail_under`).
- CLAUDE.md "Tests / CI" stack row and CONTRIBUTING are updated to describe pytest as the way to run tests.

### Python version (D-A4 + developer answer)
- **Production is Python 3.14 (Ubuntu 26.04 distro `python3`).** CI `setup-python` moves from `'3.12'` to `'3.14'`; ruff `target-version` moves from `py311` to `py314`.
- README's "Requires Python 3.12" line updated to 3.14.
- Every pinned dependency must have a 3.14-compatible release (Pillow, requests, ruff, coverage, playwright, pytest, pytest-xdist, pytest-cov); research must confirm, and the lock files are generated for 3.14.

### Test location (developer answer)
- **Migrated tests stay where they are**: `server/test_*.py` and `stub-server/test_poll_cycle.py`, next to the code. No `tests/` directory move in this phase (Phase 39's server split may relocate them later).
- `conftest.py` files placed so fixtures are shared: a repo-root `conftest.py` (no-network guard, common fixtures) plus per-directory ones if needed.

### Transition for companion harnesses (developer answer)
- **pytest shim**: until Phase 33 migrates them, each remaining hand-rolled companion harness (`companion/test_*.py`, including the browser harnesses) is run by pytest as one test that launches the harness as a subprocess and fails on a non-zero exit. The shim must not make pytest *collect* those files as test modules (use a collection ignore / a dedicated shim module).
- Consequence: `pytest -n auto` is the single entry point from Phase 32 onward. `scripts/run_all_tests.py` and its `HARNESSES` hand list are retired in this phase; `scripts/run-all-tests.sh` becomes a thin wrapper over `pytest` (keeping the `PYTHON=` override contract CI/README rely on). This pulls the runner half of TST-14 forward; the companion `EXPECTED_CHECK_COUNT`s stay until Phase 33 retires them with the harnesses.
- The browser harnesses' "SKIP counts as PASS" defect (TST-11) is Phase 33's; the shim does not have to fix it, but must not hide a non-zero exit.

### /poll-now and the no-network guard (developer answer)
- **Fixed in Phase 32**: besides shipping the fake provider fixture and the non-loopback socket guard, Phase 32 makes the existing `/poll-now` checks in `companion/test_companion_app.py` (around line 10771, the real `poll_loop.run_once` path) use the fake provider — a targeted edit of that harness, not its migration.
- The guard must apply to the subprocess-launched servers too (the companion app and byos run as child processes) — e.g. an env-var-activated hook that the child processes honour, or a fake-provider base URL injected via environment — so the "no test touches the network" claim holds end-to-end. Research picks the mechanism.
- Loopback (127.0.0.1 / ::1 / localhost) and Unix sockets stay allowed: the harnesses run real `ThreadingHTTPServer`s on free local ports.

### Migration ledger
- Lives in the phase directory (`32-MIGRATION-LEDGER.md`), one row per pre-migration check of the 15 server-side harnesses: old harness + check label → new pytest node id, or "deleted" + reason.
- Pre-migration baseline captured before any rewrite (per-harness check counts and labels from the current suite; Phase 31's `31-BASELINE-CHECKS.txt` is a format precedent).
- Parametrisation and consolidation are allowed as long as each old check maps to a specific node id (parametrised ids count).
- Server-side root-safety (e.g. `chmod` read-only checks in `server/test_manual_resolutions.py`) is handled during its migration: skip under euid 0, every path inside `tmp_path`.

### CI
- Test and deploy concurrency groups are separate; the deploy group uses `cancel-in-progress: false` (a queued stale deploy may be superseded only if the mechanism never kills a running rsync).
- Firmware host tests run in `firmware.yml` (a separate job/step that does not need the ESP-IDF container, if possible).
- Playwright: `playwright install --only-shell chromium` (plus the OS deps it needs) with `~/.cache/ms-playwright` cached, keyed on the playwright version.

### Dependency locking (TST-08)
- Runtime and dev dependencies hash-locked (transitives included: urllib3, certifi, idna, charset-normalizer…). Tool choice is Claude's discretion (pip-tools `pip-compile --generate-hashes` or `uv pip compile --generate-hashes`), generated for Python 3.14 / Linux.
- `deploy/deploy.sh` installs the runtime lock with hashes enforced; its `requirements.sha256` change-detection keeps working on the locked file.

### Coverage (TST-09)
- Subprocess coverage (`[tool.coverage.run] patch = ["subprocess"]`, coverage ≥ 7.10) so `companion/app.py`, `stub-server/byos_server.py` and `stub-server/make_test_panel.py` leave the `omit` list.
- Measure, then set `fail_under` to the measured floor (rounded down, no 4-point margin), and document the measurement in `pyproject.toml`.

### Claude's Discretion
- Lock tool, file names of the lock files, and whether the `.in` sources are kept.
- Fake provider design (fixture shape, how `poll_loop` / `enrich` receive it — dependency injection vs monkeypatching the HTTP layer), as long as it is injectable and reused by Phase 33.
- Order and batching of harness migrations across plans; pytest markers (e.g. `slow`, `browser`).
- Whether `ruff` gains the pytest-style rule family (`PT`) — optional.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit and requirements
- `.planning/audits/2026-09-23-code-audit.md` — ledger: TST-01..TST-09 findings, evidence, remediation; D-A1..D-A6; measured baseline (2018 checks, 93 % coverage, gate 83)
- `.planning/REQUIREMENTS.md` — "Audit remediation" section, TST-01..TST-09
- `.planning/ROADMAP.md` — Phase 32 goal and success criteria; Phase 33 scope boundary

### Current test and CI machinery
- `scripts/run-all-tests.sh`, `scripts/run_all_tests.py` — current runner, HARNESSES list, coverage combine/report
- `pyproject.toml` — ruff config, `[tool.coverage.*]`, omit list and gate derivation
- `server/requirements.txt`, `server/requirements-dev.txt`
- `.github/workflows/ci.yml`, `.github/workflows/firmware.yml`
- `firmware/tests/run_host_tests.sh`
- `deploy/deploy.sh` (pip install + requirements hash), `deploy/provision.sh:62-71` (distro python3)
- `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/` — previous CI speed work (timings, baseline-checks format)

### Harnesses to migrate
- `server/test_*.py` (14) and `stub-server/test_poll_cycle.py`
- `companion/test_companion_app.py` (~line 10771, `/poll-now` → real `poll_loop.run_once`) — targeted fake-provider edit only

</canonical_refs>

<specifics>
## Specific Ideas

- Success criterion 2 wording: "A test opening a non-loopback socket fails" — include a self-test proving the guard trips.
- `pytest -n auto` must pass both as root and non-root for the migrated server tests.

</specifics>

<deferred>
## Deferred Ideas

- Companion harness migration, one app-server fixture, pytest-playwright, behaviour-over-source-text rewrites, companion root-safety, companion check-count retirement, 2018-check closing parity → Phase 33.
- Moving tests into a `tests/` tree → possibly Phase 39 (server architecture split).

</deferred>

---

*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Context gathered: 2026-09-23 from the audit ledger + developer answers*
