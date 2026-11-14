#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# provision.sh must not write a secret partition to the declared live frame
# and must require the chip MAC typed back. Runs the real script against stub
# esptool and docker executables on a private PATH: no hardware, no network,
# no container. The docker stub exits 99 (or, in generate mode, writes a
# zero-filled secret.bin) so a case can tell that the guard let the run
# through to the generation step.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROVISION="${SCRIPT_DIR}/../provision.sh"
TMP=$(mktemp -d)
trap 'rm -rf "${TMP}"' EXIT INT TERM
STUBS="${TMP}/bin"
CALLS="${TMP}/esptool.calls"
mkdir -p "${STUBS}"

cat > "${STUBS}/esptool" <<'EOF'
#!/bin/sh
echo "$*" >> "${STUB_CALLS}"
case "$*" in
    *read-mac*) echo "MAC: ${STUB_MAC}" ;;
esac
exit 0
EOF

# Generate mode: find the "-v <dir>:/work" mount and the trailing partition
# size in the sh -c command, and write a secret.bin of exactly that size.
cat > "${STUBS}/docker" <<'EOF'
#!/bin/sh
if [ "${STUB_DOCKER_MODE:-}" = "generate" ]; then
    dir=""
    prev=""
    for a in "$@"; do
        [ "${prev}" = "-v" ] && dir="${a%%:*}"
        prev="${a}"
    done
    size=$(printf '%s' "$prev" | sed 's/.* //')
    head -c "${size}" /dev/zero > "${dir}/secret.bin"
    exit 0
fi
exit 99
EOF
chmod +x "${STUBS}/esptool" "${STUBS}/docker"

fail=0
LIVE_MAC="AA:BB:CC:DD:EE:01"
OTHER_MAC="11:22:33:44:55:66"

# run_case <label> <expected-exit> <stdin> <calls-expected-empty:0|1> -- VAR=value ... <provision args>
run_case() {
    label="$1"
    want="$2"
    answer="$3"
    empty="$4"
    shift 5
    : > "${CALLS}"
    set +e
    printf '%s\n' "${answer}" | env PATH="${STUBS}:${PATH}" STUB_CALLS="${CALLS}" \
        SKYPANE_WIFI_PASS="correct-horse" "$@" >/dev/null 2>&1
    got=$?
    set -e
    if [ "${got}" -ne "${want}" ]; then
        echo "FAIL: ${label}: exit ${got}, expected ${want}"
        fail=1
        return
    fi
    if [ "${empty}" -eq 1 ] && [ -s "${CALLS}" ]; then
        echo "FAIL: ${label}: esptool was called"
        fail=1
        return
    fi
    echo "PASS: ${label}"
}

COMMON="--wifi-ssid testnet --api-base https://example.invalid"

# shellcheck disable=SC2086  # COMMON is a fixed word list
run_case "live port refused before any esptool call" 3 "" 1 -- \
    STUB_MAC="${OTHER_MAC}" SKYPANE_LIVE_FRAME_PORT=/dev/ttyUSB7 \
    sh "${PROVISION}" /dev/ttyUSB7 ${COMMON}

# shellcheck disable=SC2086
run_case "live MAC refused (upper case reported)" 3 "${LIVE_MAC}" 0 -- \
    STUB_MAC="${LIVE_MAC}" SKYPANE_LIVE_FRAME_MAC="${LIVE_MAC}" \
    sh "${PROVISION}" /dev/ttyUSB1 ${COMMON}

# shellcheck disable=SC2086
run_case "wrong typed MAC refused" 3 "11:22:33:44:55:67" 0 -- \
    STUB_MAC="${OTHER_MAC}" SKYPANE_LIVE_FRAME_MAC="${LIVE_MAC}" \
    sh "${PROVISION}" /dev/ttyUSB1 ${COMMON}

# shellcheck disable=SC2086
run_case "empty stdin refused" 3 "" 0 -- \
    STUB_MAC="${OTHER_MAC}" SKYPANE_LIVE_FRAME_MAC="${LIVE_MAC}" \
    sh "${PROVISION}" /dev/ttyUSB1 ${COMMON}

# shellcheck disable=SC2086
run_case "no live variables: typed MAC still required" 3 "" 0 -- \
    STUB_MAC="${OTHER_MAC}" \
    sh "${PROVISION}" /dev/ttyUSB1 ${COMMON}

# shellcheck disable=SC2086
run_case "correct typed MAC reaches the docker stub" 99 "11:22:33:44:55:66" 0 -- \
    STUB_MAC="${OTHER_MAC}" SKYPANE_LIVE_FRAME_MAC="${LIVE_MAC}" \
    sh "${PROVISION}" /dev/ttyUSB1 ${COMMON}

# shellcheck disable=SC2086
run_case "correct typed MAC in upper case accepted" 99 "11:22:33:44:55:66" 0 -- \
    STUB_MAC="${OTHER_MAC}" \
    sh "${PROVISION}" /dev/ttyUSB1 ${COMMON}

# shellcheck disable=SC2086
run_case "dry-run with the live MAC refused" 3 "" 1 -- \
    SKYPANE_LIVE_FRAME_MAC="${LIVE_MAC}" \
    sh "${PROVISION}" --dry-run "aa:bb:cc:dd:ee:01" ${COMMON}

# shellcheck disable=SC2086
run_case "dry-run with another MAC needs no prompt" 0 "" 1 -- \
    STUB_DOCKER_MODE=generate SKYPANE_LIVE_FRAME_MAC="${LIVE_MAC}" \
    sh "${PROVISION}" --dry-run "${OTHER_MAC}" ${COMMON}

[ "${fail}" -eq 0 ] || exit 1
echo "PASS: provision.sh refuses the declared live frame and requires the typed MAC"
