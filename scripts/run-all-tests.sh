#!/usr/bin/env bash
# SkyPane — the single entry point for the whole test suite.
#
# Runs all 16 harnesses under coverage, aggregates the result, and enforces
# the coverage threshold configured in pyproject.toml. Plan 04-04's CI
# workflow calls this script rather than restating the file list, and
# plan 04-05's README tells contributors to run the same thing — one list,
# one place, no drift between local and CI.
#
# Usage:
#   scripts/run-all-tests.sh
#   PYTHON=/some/other/python3 scripts/run-all-tests.sh
#
# Deliberately does NOT use `set -e`: a single failing harness must not
# abort the run before the rest have had a chance to report — a
# contributor fixing a broken change wants the full picture in one run,
# not a report that stops at the first failure. `set -u`/`pipefail` still
# apply so an unset variable or a broken pipe is caught.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="${PYTHON:-${REPO_ROOT}/server/.venv/bin/python3}"
if [ ! -x "${PYTHON}" ]; then
    echo "ERROR: interpreter not found or not executable: ${PYTHON}" >&2
    echo "       Create the venv first: python3 -m venv server/.venv && server/.venv/bin/pip install -r server/requirements.txt -r server/requirements-dev.txt" >&2
    echo "       Or set PYTHON to point at a provisioned interpreter (e.g. CI's own venv)." >&2
    exit 1
fi

echo "==> Clearing stale coverage data files from any previous run"
rm -f .coverage .coverage.*

# Canonical 16-file enumeration (M1, measured live during 04-02 planning;
# phase 6 added 6 harnesses — see 06-11-PLAN.md Task 3; 06.6.2-01 added
# companion/test_contrast_check.py). 04-CONTEXT.md's D-07 list is 7 files
# and is known-stale — do NOT "correct" this list back down to match it.
# This array is the single source of truth CI (04-04) and README.md
# (04-05) both defer to.
HARNESSES=(
    server/test_config_history.py
    server/test_dither.py
    server/test_enrich.py
    server/test_illustrations.py
    server/test_panel_preview.py
    server/test_pipeline_e2e.py
    server/test_plane_detection.py
    server/test_poll_loop.py
    server/test_render.py
    server/test_runway_config.py
    stub-server/test_poll_cycle.py
    companion/test_companion_app.py
    companion/test_config_page.py
    companion/test_contrast_check.py
    companion/test_status_pages.py
    companion/test_view_pages.py
)

FAILED=()
for harness in "${HARNESSES[@]}"; do
    echo "==> Running ${harness}"
    # coverage.py reads [tool.coverage.run] from pyproject.toml, including
    # `parallel = true` — each process below writes its own .coverage.*
    # data file. Do NOT also pass --append here: M2 confirmed parallel
    # mode and append are mutually exclusive and coverage.py rejects the
    # combination on every single run.
    "${PYTHON}" -m coverage run "${harness}"
    status=$?
    if [ "${status}" -ne 0 ]; then
        FAILED+=("${harness}")
    fi
done

echo "==> Combining parallel coverage data files"
"${PYTHON}" -m coverage combine

echo "==> Coverage report (threshold enforced from pyproject.toml, not restated here)"
"${PYTHON}" -m coverage report
COVERAGE_STATUS=$?

echo "==> Clearing coverage data files (report already produced)"
rm -f .coverage .coverage.*

if [ "${#FAILED[@]}" -ne 0 ]; then
    echo "==> FAILED harnesses (${#FAILED[@]}):"
    for f in "${FAILED[@]}"; do
        echo "    - ${f}"
    done
fi

if [ "${#FAILED[@]}" -ne 0 ] || [ "${COVERAGE_STATUS}" -ne 0 ]; then
    echo "==> Result: FAIL"
    exit 1
fi

echo "==> Result: PASS"
exit 0
