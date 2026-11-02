#!/bin/sh
# Compiles and runs the host test of the 7.3" trial driver with the system
# cc, using the same warning flags as firmware/tests/run_host_tests.sh.
# No ESP-IDF, no Docker, no hardware.
#
# Usage: ./run-spike-host-test.sh   (from any working directory)

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

CC="${CC:-cc}"

"${CC}" -Wall -Wextra -std=c11 -I "${SCRIPT_DIR}/main" \
    "${SCRIPT_DIR}/test_epd7in3e_trial.c" \
    "${SCRIPT_DIR}/main/epd7in3e_trial.c" \
    -o "${TMP_DIR}/test_epd7in3e_trial"
"${TMP_DIR}/test_epd7in3e_trial"
