#!/usr/bin/env bash
# SkyPane — the single entry point for the whole test suite.
#
# A thin wrapper over `pytest -n auto --cov`: pytest itself (via
# pytest-xdist) owns discovery, parallelism and reporting, and pytest-cov
# owns the coverage gate (`[tool.coverage.report] fail_under` in
# pyproject.toml). pytest discovers every test: server/, stub-server/,
# deploy/tests/, test-support/ and the companion suite, including its
# pytest-playwright browser tests — one command, no drift between what CI
# runs and what a contributor runs locally. This file owns the stable
# PYTHON-interpreter contract CI and README both depend on.
#
# Usage:
#   scripts/run-all-tests.sh
#   PYTHON=/some/other/python3 scripts/run-all-tests.sh
#   JOBS=1 scripts/run-all-tests.sh              # serial run
#   scripts/run-all-tests.sh -k dither -- -x     # extra args go to pytest
#                                                 # (e.g. -k, a path, -x)
#   SKYPANE_REQUIRE_BROWSER=1 scripts/run-all-tests.sh
#                                                 # a missing Chromium fails
#                                                 # instead of skipping
#
# Coverage gate: `fail_under` is a whole-suite floor, so it is enforced
# only on a run with NO extra arguments (what CI runs). Any extra argument
# (-k, a path, -x, ...) adds `--cov-fail-under=0` before your arguments:
# a subset still reports coverage but never fails on the gate. To enforce
# a floor on a run with arguments anyway, pass it explicitly, e.g.
# `scripts/run-all-tests.sh -x --cov-fail-under=88` (the later flag wins).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="${PYTHON:-${REPO_ROOT}/server/.venv/bin/python3}"
if [ ! -x "${PYTHON}" ]; then
    echo "ERROR: interpreter not found or not executable: ${PYTHON}" >&2
    echo "       Create the venv first: python3 -m venv server/.venv && server/.venv/bin/pip install --require-hashes -r server/requirements-dev.txt" >&2
    echo "       Or set PYTHON to point at a provisioned interpreter (e.g. CI's own venv)." >&2
    exit 1
fi

echo "==> Clearing stale coverage data files from any previous run"
rm -f "${REPO_ROOT}"/.coverage "${REPO_ROOT}"/.coverage.*

# coverage.py reads [tool.coverage.run] from pyproject.toml, including
# `patch = ["subprocess"]` (which implies `parallel = true`) — each
# pytest-xdist worker, and every subprocess a test itself launches
# (byos_server.py, companion/app.py), writes its own .coverage.* data file; pytest-cov combines them all at
# the end of the session.
if [ -z "${COVERAGE_CORE:-}" ]; then
    py_minor="$("${PYTHON}" -c 'import sys; print(1 if sys.version_info >= (3, 12) else 0)')"
    if [ "${py_minor}" = "1" ]; then
        # Measured by the prior hand-rolled runner (retired 32-13): tracing
        # overhead essentially vanishes on 3.12+'s sysmon core. Left alone on older
        # interpreters where sysmon doesn't exist; an explicit
        # COVERAGE_CORE from the caller always wins over this default.
        export COVERAGE_CORE=sysmon
    fi
fi

gate_args=()
if [ "$#" -gt 0 ]; then
    echo "==> Extra pytest arguments given: coverage gate disabled for this run (full-suite floor)"
    gate_args=(--cov-fail-under=0)
fi

exec "${PYTHON}" -m pytest -n "${JOBS:-auto}" --cov --cov-report=term-missing:skip-covered --durations=15 ${gate_args[@]+"${gate_args[@]}"} "$@"
