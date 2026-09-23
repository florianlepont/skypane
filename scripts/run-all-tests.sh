#!/usr/bin/env bash
# SkyPane — the single entry point for the whole test suite.
#
# A thin wrapper over `pytest -n auto --cov`: pytest itself (via
# pytest-xdist) owns discovery, parallelism and reporting, and pytest-cov
# owns the coverage gate (`[tool.coverage.report] fail_under` in
# pyproject.toml). Phase 32 (32-13-PLAN.md) retired the prior hand-rolled
# Python orchestrator this script used to exec into (its own HARNESSES
# list, worker pool and hand-run `coverage combine`/`report` calls) now
# that pytest
# discovers every migrated server/stub-server test plus the legacy
# companion harnesses (still run as one pytest test per harness via
# companion/test_legacy_harness_shim.py, until Phase 33 migrates them
# too) — one command, no drift between what CI runs and what a
# contributor runs locally. This file still owns the stable
# PYTHON-interpreter contract CI and README both depend on.
#
# Usage:
#   scripts/run-all-tests.sh
#   PYTHON=/some/other/python3 scripts/run-all-tests.sh
#   JOBS=1 scripts/run-all-tests.sh              # old serial behaviour
#   HARNESS_TIMEOUT_S=120 scripts/run-all-tests.sh  # read by the legacy
#                                                    # companion pytest
#                                                    # shim until Phase 33
#   scripts/run-all-tests.sh -k dither -- -x     # extra args go to pytest
#                                                 # (e.g. -k, a path, -x)
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
# (byos_server.py, companion/app.py, the legacy companion harnesses),
# writes its own .coverage.* data file; pytest-cov combines them all at
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

exec "${PYTHON}" -m pytest -n "${JOBS:-auto}" --cov --cov-report=term-missing:skip-covered --durations=15 "$@"
