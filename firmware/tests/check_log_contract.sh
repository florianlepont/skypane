#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# Proves two things every push touching firmware/main/ or firmware/VENDOR.md
# must keep true (T-34-10-01):
#
#   1. The five Log Line Contract format strings are still present, byte
#      for byte, in the C sources that emit them.
#   2. Every `poll fail step=<token>` value the firmware can actually emit
#      is documented in VENDOR.md's Log Line Contract table.
#
# Either one breaking silently invalidates every captured hardware log a
# past or future plan reasons about — VENDOR.md's own Log Line Contract
# section says as much. Run standalone or from .github/workflows/firmware.yml.
#
# Usage: ./check_log_contract.sh   (no arguments; self-locating)
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FW_DIR=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)

APP_MAIN="${FW_DIR}/main/app_main.c"
STATE_MACHINE="${FW_DIR}/main/state_machine.c"
VENDOR="${FW_DIR}/VENDOR.md"

fail() {
    echo "log-contract: FAIL - $1" >&2
    exit 1
}

[ -f "${APP_MAIN}" ] || fail "missing ${APP_MAIN}"
[ -f "${STATE_MACHINE}" ] || fail "missing ${STATE_MACHINE}"
[ -f "${VENDOR}" ] || fail "missing ${VENDOR}"

# --- 1. The five contract format strings, byte for byte, tag `skypane` ---
grep -qF 'wake reason=%s boot_count=%' "${APP_MAIN}" \
    || fail "wake reason= format string missing from app_main.c"
grep -qF 'poll ok sleep_s=%' "${APP_MAIN}" \
    || fail "poll ok sleep_s= format string missing from app_main.c"
grep -qF 'hash_skip=%u' "${APP_MAIN}" \
    || fail "hash_skip=%u missing from app_main.c's poll ok line"
grep -qF 'poll fail step=%s backoff_n=%u sleep_s=%' "${APP_MAIN}" \
    || fail "poll fail format string missing from app_main.c"
grep -qF 'sleep enter sleep_s=%' "${APP_MAIN}" \
    || fail "sleep enter format string missing from app_main.c"
grep -qF 'blit ok bytes=960000 sha256_ok=1' "${STATE_MACHINE}" \
    || fail "blit ok line missing from state_machine.c"

# --- 2. Every step= token the code can emit must be documented in ---
#        VENDOR.md's poll fail step= row. Extracted three ways:
#          a) state_machine.c step_for()'s switch-case return literals
#          b) state_machine.c's other direct *fail_step_out assignments
#             (covers the ternary "verify"/"download" line, and "wifi"/
#             "blit")
#          c) the literal steps app_main.c's fail_and_sleep() is called
#             with ("reset", "deadline", "json")
TOKENS=$(
    {
        grep -oE 'return "[a-z]+"' "${STATE_MACHINE}" | grep -oE '"[a-z]+"'
        grep 'fail_step_out =' "${STATE_MACHINE}" | grep -oE '"[a-z]+"'
        grep -oE 'fail_and_sleep\("[a-z]+"\)' "${APP_MAIN}" | grep -oE '"[a-z]+"'
    } | tr -d '"' | sort -u
)

[ -n "${TOKENS}" ] || fail "no step= tokens extracted - check the extraction patterns"

VENDOR_ROW=$(grep 'poll fail step=' "${VENDOR}" || true)
[ -n "${VENDOR_ROW}" ] || fail "VENDOR.md has no 'poll fail step=' line"

for token in ${TOKENS}; do
    case "${VENDOR_ROW}" in
        *"${token}"*) ;;
        *) fail "step token '${token}' is not documented in VENDOR.md's poll fail step= row" ;;
    esac
done

# --- 3. The five contract line shapes must still appear in VENDOR.md's ---
#        table (placeholders, not the raw printf format).
grep -qF 'wake reason=<rtc' "${VENDOR}" \
    || fail "VENDOR.md is missing the wake reason= line shape"
grep -qF 'poll ok sleep_s=<n> hash_skip=<0' "${VENDOR}" \
    || fail "VENDOR.md is missing the poll ok line shape"
grep -qF 'poll fail step=<' "${VENDOR}" \
    || fail "VENDOR.md is missing the poll fail line shape"
grep -qF 'blit ok bytes=960000 sha256_ok=1' "${VENDOR}" \
    || fail "VENDOR.md is missing the blit ok line shape"
grep -qF 'sleep enter sleep_s=<n>' "${VENDOR}" \
    || fail "VENDOR.md is missing the sleep enter line shape"

echo "log-contract: PASS"
