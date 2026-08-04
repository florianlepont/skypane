#!/bin/sh
# Compiles and runs every hardware-free firmware test with the system `cc`.
#
# No ESP-IDF, no Docker, no hardware required - that property is the whole
# point: it is the only automated feedback signal available in this phase
# before the EE02 kit arrives (01-RESEARCH.md, D-08).
#
# Usage: ./run_host_tests.sh   (from any working directory)

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MAIN_DIR="${SCRIPT_DIR}/../main"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

CC="${CC:-cc}"
FAIL=0

run_suite() {
    name="$1"
    test_src="$2"
    impl_src="$3"
    bin="${TMP_DIR}/${name}"

    echo "== ${name} =="
    if ! "${CC}" -Wall -Wextra -std=c11 "${impl_src}" "${test_src}" -o "${bin}"; then
        echo "${name}: COMPILE FAILED"
        FAIL=1
        return
    fi
    if ! "${bin}"; then
        echo "${name}: FAILED"
        FAIL=1
    fi
}

run_suite "test_backoff" "${SCRIPT_DIR}/test_backoff.c" "${MAIN_DIR}/backoff.c"
run_suite "test_api_base" "${SCRIPT_DIR}/test_api_base.c" "${MAIN_DIR}/api_base.c"

if [ "${FAIL}" -eq 0 ]; then
    echo "== summary: all hardware-free firmware suites passed =="
else
    echo "== summary: one or more suites FAILED =="
fi

exit "${FAIL}"
