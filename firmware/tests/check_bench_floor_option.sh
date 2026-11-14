#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# The bench-only floor override of build.sh must be refused for a production
# build and for a malformed version, before any container starts. Needs no
# ESP-IDF and no Docker: both refusals are usage errors raised up front.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD="${SCRIPT_DIR}/../build.sh"
fail=0

expect_refused() {
    label="$1"
    shift
    set +e
    out=$(env "$@" sh "${BUILD}" 2>&1)
    status=$?
    set -e
    if [ "${status}" -ne 2 ]; then
        echo "FAIL: ${label}: exit ${status}, expected 2"
        fail=1
    elif ! printf '%s' "${out}" | grep -q 'SKYPANE_BENCH_FLOOR'; then
        echo "FAIL: ${label}: refusal does not name SKYPANE_BENCH_FLOOR"
        fail=1
    fi
}

expect_refused "production profile" SKYPANE_PROFILE=prod SKYPANE_BENCH_FLOOR=fw-v1.0.5
expect_refused "default profile" SKYPANE_BENCH_FLOOR=fw-v1.0.5
expect_refused "malformed version" SKYPANE_PROFILE=dev SKYPANE_BENCH_FLOOR=1.0.5
expect_refused "version with a suffix" SKYPANE_PROFILE=dev SKYPANE_BENCH_FLOOR=fw-v1.0.5-x

[ "${fail}" -eq 0 ] || exit 1
echo "PASS: SKYPANE_BENCH_FLOOR is refused outside the dev profile and for a malformed version"
