#!/usr/bin/env bash
# SkyPane — the single entry point for the whole test suite.
#
# This is a thin wrapper: the harness list, concurrency, per-harness
# timeout and reporting logic now live in run_all_tests.py alongside this
# script — that logic outgrew what bash could do cleanly, so it moved to
# Python (stdlib only) while this file kept owning the stable
# PYTHON-interpreter contract CI and README both depend on. Plan 04-04's
# CI workflow calls this script rather than restating the file list, and
# plan 04-05's README tells contributors to run the same thing — one list,
# one place, no drift between local and CI.
#
# Usage:
#   scripts/run-all-tests.sh
#   PYTHON=/some/other/python3 scripts/run-all-tests.sh
#   JOBS=1 scripts/run-all-tests.sh              # old serial behaviour
#   HARNESS_TIMEOUT_S=120 scripts/run-all-tests.sh
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

exec "${PYTHON}" "${HERE}/run_all_tests.py" "$@"
