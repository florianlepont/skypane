#!/bin/sh
# Panel safety check: against the last commit before the wake instrumentation,
# the changes to the panel driver (epd13in3e.c) and panel.c may only be
# added timer reads, the SPI time variable and its accessor, an esp_timer.h
# include, the panel_driver.h include that selects the driver at compile
# time, and bare braces or blank lines. Any removed line or any other
# added line fails, so the register sequence, delays, SPI writes, sleep
# logic and power rails stay exactly as they were.
#
# PANEL_DIFF_BASE overrides the base commit (it must exist in the clone).
# Usage: sh check_panel_diff.sh   (from any working directory)

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_DIR="${SCRIPT_DIR}/../.."
BASE="${PANEL_DIFF_BASE:-b404122e0df5f82fdfcd0496297a70bdafdb5e24}"

cd "${REPO_DIR}"
if ! git cat-file -e "${BASE}^{commit}" 2>/dev/null; then
    echo "panel-diff: FAIL: base commit ${BASE} not in this clone (needs full history)"
    exit 1
fi

DIFF=$(git diff -U0 "${BASE}" -- firmware/main/epd13in3e.c firmware/main/panel.c \
    | grep -E '^[-+]' | grep -Ev '^(\+\+\+|---) ' || true)

if [ -z "${DIFF}" ]; then
    echo "panel-diff: FAIL: no timer reads found in the panel files"
    exit 1
fi

READS=$(printf '%s\n' "${DIFF}" | grep -Ec 'esp_timer_get_time' || true)
if [ "${READS}" -lt 2 ]; then
    echo "panel-diff: FAIL: fewer than two timer reads (${READS})"
    exit 1
fi

BAD=$(printf '%s\n' "${DIFF}" | grep -Ev '^\+.*(esp_timer_get_time|spi_us|spi_ms)|^\+[[:space:]]*#include[[:space:]]+"(esp_timer|panel_driver)\.h"[[:space:]]*$|^\+[[:space:]]*[{}]?[[:space:]]*$' || true)
if [ -n "${BAD}" ]; then
    echo "panel-diff: FAIL: panel files changed beyond timer reads:"
    printf '%s\n' "${BAD}"
    exit 1
fi

echo "panel-diff: PASS (${READS} timer reads, no other panel change)"
