#!/usr/bin/env bash
# SkyPane — the single entry point for the whole test suite.
#
# A thin wrapper over `pytest -n auto --cov`: pytest-xdist owns
# discovery/parallelism, pytest-cov owns the coverage gate
# (`[tool.coverage.report] fail_under` in pyproject.toml). Runs the same
# command CI runs, so there is no drift between CI and a local run.

# Usage: scripts/run-all-tests.sh [-- pytest-args]
#   PYTHON=/other/python3       use a different interpreter
#   JOBS=1                      serial run
#   SKYPANE_REQUIRE_BROWSER=1   missing Chromium fails instead of skipping
#
# fail_under is a whole-suite floor: enforced only when no extra pytest
# arguments are given (what CI runs). Any extra argument adds
# --cov-fail-under=0 first; pass an explicit --cov-fail-under=N after your
# own args to enforce a floor on a subset run too.
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

# coverage.py reads [tool.coverage.run] from pyproject.toml: `patch =
# ["subprocess"]` (implies parallel=true) makes each xdist worker and
# subprocess (byos_server.py, companion/app.py) write its own data file;
# pytest-cov combines them all at session end.
if [ -z "${COVERAGE_CORE:-}" ]; then
    py_minor="$("${PYTHON}" -c 'import sys; print(1 if sys.version_info >= (3, 12) else 0)')"
    if [ "${py_minor}" = "1" ]; then
        # Tracing overhead is negligible on 3.12+'s sysmon core (measured
        # by the prior hand-rolled runner). Left off older interpreters;
        # an explicit COVERAGE_CORE from the caller always wins.
        export COVERAGE_CORE=sysmon
    fi
fi

gate_args=()
if [ "$#" -gt 0 ]; then
    echo "==> Extra pytest arguments given: coverage gate disabled for this run (full-suite floor)"
    gate_args=(--cov-fail-under=0)
fi

exec "${PYTHON}" -m pytest -n "${JOBS:-auto}" --cov --cov-report=term-missing:skip-covered --durations=15 ${gate_args[@]+"${gate_args[@]}"} "$@"
