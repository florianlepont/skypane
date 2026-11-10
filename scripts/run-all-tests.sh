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
# Running part of the suite (for parallel CI jobs); all unset by default:
#   SKYPANE_TEST_GROUP=core|browser   run only that group's test files
#                                     (scripts/ci_shards.py defines the groups)
#   SKYPANE_TEST_SHARD=INDEX/COUNT    run shard INDEX (0-based) of COUNT within
#                                     the group; default 0/1 = the whole group
#   SKYPANE_JUNIT_XML=path            also write a JUnit report there
# A partial run selects whole files by path (nothing is deselected), writes
# coverage data only and enforces no floor: the floor applies to the
# combined data of all partial runs, never to one shard. It fails when the
# selection is empty or the group name is unknown.
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

group="${SKYPANE_TEST_GROUP:-all}"
shard="${SKYPANE_TEST_SHARD:-0/1}"
selection=()
partial_args=()
case "${group}" in
    all) ;;
    core|browser)
        if ! [[ "${shard}" =~ ^[0-9]+/[0-9]+$ ]]; then
            echo "ERROR: SKYPANE_TEST_SHARD must look like INDEX/COUNT, got '${shard}'" >&2
            exit 2
        fi
        while IFS= read -r selected_file; do
            [ -n "${selected_file}" ] && selection+=("${selected_file}")
        done < <("${PYTHON}" "${HERE}/ci_shards.py" files "${group}" "${shard%/*}" "${shard#*/}") || exit 2
        if [ "${#selection[@]}" -eq 0 ]; then
            echo "ERROR: group '${group}' shard '${shard}' selects no test files" >&2
            exit 2
        fi
        echo "==> Partial run: group ${group}, shard ${shard}, ${#selection[@]} test files; coverage data only, no floor"
        partial_args=(--cov-fail-under=0 --cov-report=)
        ;;
    *)
        echo "ERROR: SKYPANE_TEST_GROUP must be all, core or browser, got '${group}'" >&2
        exit 2
        ;;
esac

junit_args=()
if [ -n "${SKYPANE_JUNIT_XML:-}" ]; then
    junit_args=(--junitxml "${SKYPANE_JUNIT_XML}")
fi

gate_args=()
if [ "$#" -gt 0 ]; then
    echo "==> Extra pytest arguments given: coverage gate disabled for this run (full-suite floor)"
    gate_args=(--cov-fail-under=0)
fi

report_args=(--cov-report=term-missing:skip-covered)
if [ "${#partial_args[@]}" -gt 0 ]; then
    report_args=()
fi

exec "${PYTHON}" -m pytest -n "${JOBS:-auto}" --cov ${report_args[@]+"${report_args[@]}"} --durations=15 ${gate_args[@]+"${gate_args[@]}"} ${partial_args[@]+"${partial_args[@]}"} ${junit_args[@]+"${junit_args[@]}"} ${selection[@]+"${selection[@]}"} "$@"
